#!/usr/bin/env python3
"""otomatik_cizim.py — ÖLÇÜLEN yapıdan otomatik TradingView katmanı.

Girdi mumlar → grafik-calisma/scripts/smc_tespit.py (deponun KENDİ tespit
motoru; ikinci bir tespit mantığı YAZILMAZ) → çizim listesi:

  · swing HH/HL/LH/LL etiketleri        · order block dikdörtgenleri
  · BOS / CHoCH kırılım çizgileri       · açık FVG bantları
  · likidite havuzu rayları             · impuls bacağından Fibonacci + altın bölge
  · trend çizgisi (son iki teyitli swing) · regresyon kanalı (opsiyonel)
  · ölçülen değerlerle bilgi paneli     · emir verilirse long/short pozisyon kutusu

Kural: buradaki HER sayı smc_tespit çıktısından ya da ham mumdan gelir.
Motor bir seviye ölçemezse o çizim ATLANIR ve uyarı yazılır — uydurulmaz.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
GRAFIK = BURASI.parents[1] / "grafik-calisma" / "scripts"
for _p in (str(BURASI), str(GRAFIK)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _smc(mumlar: list, params: dict | None = None) -> tuple[dict, object]:
    import smc_tespit as ST  # noqa: PLC0415

    job = {"candles": mumlar}
    if params:
        job["params"] = params
    return ST.detect(job), ST


def _swing_etiketleri(ST, mumlar, cikti_uyari, sinir=8):
    """HH/HL/LH/LL — smc_tespit'in KENDİ find_swings'i ile (tek doğruluk kaynağı)."""
    import pandas as pd  # noqa: PLC0415

    df = pd.DataFrame(mumlar)
    yuksek, alcak = ST.find_swings(df, 2, 2)
    ciz = []
    for dizi, tur in ((yuksek[-sinir:], "high"), (alcak[-sinir:], "low")):
        onceki = None
        for s in dizi:
            if onceki is None:
                etk = "H" if tur == "high" else "L"
            elif tur == "high":
                etk = "HH" if s["price"] > onceki else "LH"
            else:
                etk = "HL" if s["price"] > onceki else "LL"
            onceki = s["price"]
            ciz.append({"arac": "metin", "metin": etk,
                        "p1": {"bar": s["i"], "fiyat": s["price"]},
                        "renk": "olumlu" if etk in ("HH", "HL") else "olumsuz",
                        "hiza": "middle", "boyut": 11})
    return ciz


def uret(mumlar: list, cfg: dict, taban: Path | None = None) -> tuple[list, dict]:
    cfg = dict(cfg or {})
    uyari: list[str] = []
    ciz: list[dict] = []
    n = len(mumlar)
    try:
        out, ST = _smc(mumlar, cfg.get("params"))
    except Exception as e:  # noqa: BLE001
        return [], {"kaynak": "smc_tespit.py", "hata": f"tespit koşamadı: {e}",
                    "uyarilar": [f"otomatik katman VERİ YOK — {e}"]}

    trend = out.get("trend", "belirsiz")
    atr = out.get("atr")
    olaylar = out.get("olaylar") or []
    son = mumlar[-1]["close"]

    # --- order block'lar
    if cfg.get("ob", True):
        for ob in (out.get("order_blocks") or [])[-int(cfg.get("ob_sinir", 4)):]:
            talep = ob.get("type") == "demand"
            ciz.append({"arac": "dikdortgen", "fiyat1": ob["low"], "fiyat2": ob["high"],
                        "bar_baslangic": ob["i"],
                        "renk": "olumlu" if talep else "olumsuz",
                        "dolgu_saydam": 0.16,
                        "etiket": f"OB {'talep' if talep else 'arz'}"})

    # --- açık FVG'ler
    if cfg.get("fvg", True):
        for f in [x for x in (out.get("acik_fvgler") or []) if not x.get("dolu")][
                -int(cfg.get("fvg_sinir", 4)):]:
            boga = f.get("type") == "bull"
            ciz.append({"arac": "dikdortgen", "fiyat1": f["low"], "fiyat2": f["high"],
                        "bar_baslangic": f["i"], "renk": "vurgu" if boga else "notr",
                        "dolgu_saydam": 0.12, "kesik": "4 3",
                        "etiket": f"FVG {'boğa' if boga else 'ayı'}",
                        "etiket_hiza": "sol"})

    # --- likidite havuzları
    if cfg.get("likidite", True):
        havuz = sorted((out.get("likidite") or []),
                       key=lambda x: (-int(x.get("count", 1)), abs(x["price"] - son)))
        for h in havuz[:int(cfg.get("likidite_sinir", 4))]:
            ust = h.get("type") == "buyside"
            ciz.append({"arac": "yatay_ray", "fiyat": h["price"], "bar": 0,
                        "renk": "olumsuz" if ust else "olumlu", "kesik": "6 4",
                        "kalinlik": 1.1, "fiyat_etiketi": False, "etiket_hiza": "sag",
                        "etiket": f"likidite {h.get('kind', '')} ×{h.get('count', 1)}"})

    # --- BOS / CHoCH
    if cfg.get("yapi", True):
        for ev in olaylar[-int(cfg.get("yapi_sinir", 3)):]:
            boga = ev.get("direction") == "bull"
            b1 = ev.get("impulse_start_i")
            ciz.append({"arac": "yatay_cizgi", "fiyat": ev["kirilan_seviye"],
                        "bar_baslangic": b1 if b1 is not None else max(0, ev["i"] - 10),
                        "bar_bitis": min(n - 1, ev["i"] + 4),
                        "renk": "olumlu" if boga else "olumsuz", "kesik": "5 3",
                        "kalinlik": 1.4, "fiyat_etiketi": False,
                        "etiket": f"{ev['type']} {'↑' if boga else '↓'}"})
            ciz.append({"arac": "isaret", "yon": "yukari" if boga else "asagi",
                        "p1": {"bar": ev["i"], "fiyat": ev["kirilan_seviye"]},
                        "boyut": 6})

    # --- impuls bacağından Fibonacci (altın bölge dahil)
    if cfg.get("fib", True):
        ev = olaylar[-1] if olaylar else None
        if ev and ev.get("impulse_start_i") is not None:
            b1 = int(ev["impulse_start_i"])
            boga = ev.get("direction") == "bull"
            dilim = range(b1, n)
            if boga:
                b2 = max(dilim, key=lambda i: mumlar[i]["high"])
                f2 = mumlar[b2]["high"]
            else:
                b2 = min(dilim, key=lambda i: mumlar[i]["low"])
                f2 = mumlar[b2]["low"]
            ciz.append({"arac": "fib_retracement",
                        "p1": {"bar": b1, "fiyat": ev["impulse_start"]},
                        "p2": {"bar": b2, "fiyat": f2},
                        "altin_bolge": True,
                        # impuls sağda kaldıysa etiketler sıkışmasın
                        "tam_genislik": min(b1, b2) > 0.45 * n})
        else:
            uyari.append("fib: impuls bacağı ölçülemedi (olay/impulse_start yok)")

    # --- trend çizgisi: son iki teyitli aynı yönlü swing
    if cfg.get("trend_cizgisi", True):
        try:
            import pandas as pd  # noqa: PLC0415

            yuksek, alcak = ST.find_swings(pd.DataFrame(mumlar), 2, 2)
            dizi = alcak if trend == "bull" else yuksek
            if len(dizi) >= 2:
                a, b = dizi[-2], dizi[-1]
                ciz.append({"arac": "trend_cizgisi",
                            "p1": {"bar": a["i"], "fiyat": a["price"]},
                            "p2": {"bar": b["i"], "fiyat": b["price"]},
                            "uzat": "sag", "renk": "olumlu" if trend == "bull" else "olumsuz",
                            "kalinlik": 1.8})
            else:
                uyari.append("trend çizgisi: iki teyitli swing yok")
        except Exception as e:  # noqa: BLE001
            uyari.append(f"trend çizgisi: {e}")

    # --- swing etiketleri
    if cfg.get("swing_etiket", True):
        try:
            ciz += _swing_etiketleri(ST, mumlar, uyari)
        except Exception as e:  # noqa: BLE001
            uyari.append(f"swing etiketleri: {e}")

    # --- regresyon kanalı (istenirse)
    if cfg.get("regresyon"):
        r = cfg["regresyon"] if isinstance(cfg["regresyon"], dict) else {}
        ciz.append({"arac": "regresyon_kanali",
                    "bar_baslangic": r.get("bar_baslangic", max(0, n - int(r.get("bar", 120)))),
                    "bar_bitis": r.get("bar_bitis", n - 1),
                    "sapma": r.get("sapma", 2.0), "ileri_bar": r.get("ileri_bar", 0)})

    # --- hareketli ortalamalar
    for ma in (cfg.get("ma") or []):
        ciz.append({"arac": "ma", "tip": ma.get("tip", "ema"),
                    "period": ma.get("period", 50), "renk": ma.get("renk", "notr")})

    # --- emir kutusu (karar-motoru/emir_plani çıktısından)
    emir = cfg.get("emir")
    if isinstance(emir, str) or cfg.get("emir_dosya"):
        yol = Path(cfg.get("emir_dosya") or emir)
        if taban and not yol.is_absolute():
            yol = taban / yol
        try:
            emir = json.loads(yol.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            uyari.append(f"emir dosyası okunamadı: {e}")
            emir = None
    if isinstance(emir, dict):
        g, st, hd = emir.get("giris"), emir.get("stop"), emir.get("hedef", emir.get("t1"))
        if None in (g, st, hd):
            uyari.append("emir kutusu: giriş/stop/hedef eksik — çizilmedi (VERİ YOK)")
        else:
            yon = str(emir.get("yon", "long")).lower()
            yon = "short" if yon.startswith("s") else "long"
            spec = {"arac": f"{yon}_pozisyon", "giris": float(g), "stop": float(st),
                    "hedef": float(hd), "bar_baslangic": emir.get("bar", n - 1),
                    "uzunluk_bar": int(emir.get("uzunluk_bar", 25))}
            if emir.get("r") is not None:
                spec["r_etiketi"] = f"R {float(emir['r']):.2f}"
            ciz.append(spec)

    # --- ölçülen değerlerle bilgi paneli
    if cfg.get("panel", True):
        rejim = out.get("rejim") or {}
        satir = [
            {"ad": "Trend (yapı)", "deger": trend.upper(),
             "renk": "olumlu" if trend == "bull" else "olumsuz" if trend == "bear" else "notr"},
            {"ad": "Rejim (ADX)", "deger": f"{rejim.get('durum', 'VERİ YOK')} · "
                                           f"{rejim.get('adx', 'VERİ YOK')}"},
            {"ad": "ATR (Wilder)", "deger": f"{atr:.2f}" if atr else "VERİ YOK"},
            {"ad": "ATR %", "deger": f"{rejim.get('atr_pct', 0) * 100:.2f}%"
                                     if rejim.get("atr_pct") else "VERİ YOK"},
            {"ad": "Yüksek volatilite", "deger": "EVET" if rejim.get("yuksek_vol") else "hayır",
             "renk": "notr" if rejim.get("yuksek_vol") else "metin_soluk"},
            {"ad": "Son olay", "deger": (f"{olaylar[-1]['type']} "
                                         f"{olaylar[-1]['direction']}") if olaylar else "VERİ YOK"},
            {"ad": "Order block", "deger": str(len(out.get("order_blocks") or []))},
            {"ad": "Açık FVG", "deger": str(len([x for x in (out.get("acik_fvgler") or [])
                                                 if not x.get("dolu")]))},
            {"ad": "Likidite havuzu", "deger": str(len(out.get("likidite") or []))},
            {"ad": "Son fiyat", "deger": f"{son:,.2f}".replace(",", ".")},
        ]
        ciz.append({"arac": "bilgi_paneli", "baslik": cfg.get("panel_baslik", "ÖLÇÜLEN YAPI"),
                    "satirlar": satir, "konum": cfg.get("panel_konum", "oto"),
                    "genislik": int(cfg.get("panel_genislik", 260))})

    rapor = {
        "kaynak": "grafik-calisma/scripts/smc_tespit.py (detect)",
        "trend": trend,
        "atr": atr,
        "rejim": out.get("rejim"),
        "sayim": {
            "order_block": len(out.get("order_blocks") or []),
            "acik_fvg": len([x for x in (out.get("acik_fvgler") or []) if not x.get("dolu")]),
            "likidite": len(out.get("likidite") or []),
            "yapi_olayi": len(olaylar),
            "cizim": len(ciz),
        },
        "varsayimlar": out.get("varsayimlar"),
        "uyarilar": uyari,
    }
    return ciz, rapor


def main() -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(description="ölçülen yapıdan otomatik çizim listesi")
    ap.add_argument("--job", required=True, help="{'veri':{...},'otomatik':{...}}")
    a = ap.parse_args()
    yol = Path(a.job).resolve()
    job = json.loads(yol.read_text(encoding="utf-8"))
    import cizim as C  # noqa: PLC0415

    mumlar, kaynak = C.mumlari_getir(job, yol.parent)
    ciz, rapor = uret(mumlar, job.get("otomatik") or {}, taban=yol.parent)
    print(json.dumps({"veri_kaynagi": kaynak, "cizimler": ciz, "rapor": rapor},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
