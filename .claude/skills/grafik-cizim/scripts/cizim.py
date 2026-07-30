#!/usr/bin/env python3
"""cizim.py — TradingView tarzı çizimli mum grafiği üretir (SVG, sıfır bağımlılık).

Kullanım:
    python3 cizim.py --job is.json          # iş dosyasından çiz
    python3 cizim.py --araclar              # desteklenen araçları listele

İş dosyası (job) şeması:
{
  "veri":   {"kline": "engine/girdi/h4.json"}      # Binance kline JSON/CSV
            | {"mumlar": [{"open":..,"high":..,"low":..,"close":..,"volume":..,"time":..}]},
  "son_bar": 200,                                   # yalnız son N mum
  "baslik": "BTCUSDT · 4H · Binance",
  "alt_baslik": "SMC + Fibonacci — ölçülen yapıdan çizildi",
  "tema": "koyu" | "acik",
  "genislik": 1600, "yukseklik": 900,
  "log_olcek": false, "sag_bosluk_bar": 30,
  "paneller": [{"tip":"hacim","yukseklik":0.14},{"tip":"rsi","period":14}],
  "cizimler": [ {"arac":"fib_retracement","p1":{"bar":-60,"fiyat":1.0}, ...} ],
  "otomatik": {"smc": true, "emir": {...}},         # otomatik_cizim.py katmanı
  "cikti": "grafik.svg"
}

Çıktı: SVG dosyası + stdout'a JSON özeti (çizilen araçlar, seviyeler, uyarılar).

DOĞRULUK: bu motor fiyat UYDURMAZ. Elle verilen çizimler kullanıcının/üst
motorun sayılarıdır; "otomatik" katmanı seviyeleri smc_tespit.py'nin ÖLÇTÜĞÜ
yapıdan alır. Okunamayan/eksik alan "VERİ YOK" olarak raporlanır.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
if str(BURASI) not in sys.path:
    sys.path.insert(0, str(BURASI))

import araclar as A  # noqa: E402
from tuval import Tuval  # noqa: E402

KOK = BURASI.parents[3] if len(BURASI.parents) >= 4 else Path.cwd()
MOTOR = KOK / "engine"


class CizimError(Exception):
    pass


# ------------------------------------------------------------------ veri
def _kline_yukle(yol: Path) -> tuple[list, str]:
    """Mum listesi + kaynak etiketi. Önce deponun KENDİ parser'ı denenir."""
    if MOTOR.exists() and str(MOTOR) not in sys.path:
        sys.path.insert(0, str(MOTOR))
    try:
        import karar_motoru as km  # noqa: PLC0415

        bars = km.parse_klines(str(yol))
        return ([{"open": b.o, "high": b.h, "low": b.l, "close": b.c,
                  "volume": b.v, "time": b.t} for b in bars],
                "engine/karar_motoru.parse_klines")
    except Exception:  # noqa: BLE001 — motor yoksa yedek parser
        pass
    ham = json.loads(yol.read_text(encoding="utf-8"))
    mumlar = []
    for r in ham:
        if isinstance(r, (list, tuple)) and len(r) >= 5:
            mumlar.append({"time": int(r[0]), "open": float(r[1]), "high": float(r[2]),
                           "low": float(r[3]), "close": float(r[4]),
                           "volume": float(r[5]) if len(r) > 5 else 0.0})
        elif isinstance(r, dict):
            # Eksik alanlı satır ATLANIR (S1): open/o ikisi de yoksa float(None)
            # TypeError ile TÜM motoru çökertirdi (satır bazlı atlama yoktu).
            o = r.get("open", r.get("o")); h = r.get("high", r.get("h"))
            l = r.get("low", r.get("l")); c = r.get("close", r.get("c"))
            if None in (o, h, l, c):
                continue
            mumlar.append({
                "time": int(r.get("time") or r.get("t") or 0) or None,
                "open": float(o), "high": float(h), "low": float(l),
                "close": float(c),
                "volume": float(r.get("volume", r.get("v", 0)) or 0)})
    return mumlar, "yedek parser (cizim.py)"


def mumlari_getir(job: dict, taban: Path) -> tuple[list, str]:
    veri = job.get("veri") or {}
    if veri.get("mumlar"):
        m = [{"open": float(c.get("open", c.get("o"))),
              "high": float(c.get("high", c.get("h"))),
              "low": float(c.get("low", c.get("l"))),
              "close": float(c.get("close", c.get("c"))),
              "volume": float(c.get("volume", c.get("v", 0)) or 0),
              "time": c.get("time", c.get("t"))} for c in veri["mumlar"]]
        kaynak = "job.veri.mumlar"
    elif veri.get("kline"):
        yol = Path(veri["kline"])
        if not yol.is_absolute():
            yol = (taban / yol) if (taban / yol).exists() else (KOK / yol)
        if not yol.exists():
            raise CizimError(f"kline dosyası yok: {veri['kline']}")
        m, kaynak = _kline_yukle(yol)
        kaynak = f"{yol} ({kaynak})"
    else:
        raise CizimError("veri.kline ya da veri.mumlar gerekli")
    if not m:
        raise CizimError("mum listesi boş")
    n = int(job.get("son_bar", 0) or 0)
    if n and len(m) > n:
        m = m[-n:]
    return m, kaynak


# ------------------------------------------------------------------ çizim
def _normalize(spec: dict) -> dict:
    s = dict(spec)
    ham = str(s.get("arac", "")).strip().lower()
    if ham in ("ema", "sma"):
        s.setdefault("tip", ham)
    s["arac"] = A.coz(ham)
    return s


def uygula(job: dict, taban: Path) -> dict:
    mumlar, kaynak = mumlari_getir(job, taban)
    cizimler = [_normalize(c) for c in (job.get("cizimler") or [])]
    uyari: list[str] = []

    oto = job.get("otomatik")
    oto_rapor = None
    if oto:
        import otomatik_cizim as OC  # noqa: PLC0415

        oto_cizim, oto_rapor = OC.uret(mumlar, oto, taban=taban)
        cizimler = [_normalize(c) for c in oto_cizim] + cizimler
        uyari += oto_rapor.get("uyarilar", [])

    t = Tuval(
        mumlar,
        genislik=int(job.get("genislik", 1600)),
        yukseklik=int(job.get("yukseklik", 900)),
        tema=str(job.get("tema", "koyu")),
        log_olcek=bool(job.get("log_olcek", False)),
        sag_bosluk_bar=int(job.get("sag_bosluk_bar", 25)),
        baslik=str(job.get("baslik", "")),
        alt_baslik=str(job.get("alt_baslik", "")),
        paneller=job.get("paneller") or [],
        dipnot=str(job.get("dipnot", "")),
    )

    # 1. geçiş — ölçeğe rezerve (çizimler grafik dışına taşmasın)
    gecerli = []
    for s in cizimler:
        try:
            fiyat_fn, _ = A.arac(s["arac"])
            t.rezerve(fiyat_fn(t, s))
            gecerli.append(s)
        except Exception as e:  # noqa: BLE001
            uyari.append(f"{s.get('arac')}: atlandı — {e}")
    t.hazirla()

    # 2. geçiş — katman sırasına göre çiz (bölgeler mumun arkası, etiketler önü)
    arka, on, cizilen, seviyeler = [], [], [], []
    for s in sorted(gecerli, key=lambda x: (int(x.get("katman", A.katman(x["arac"]))),)):
        try:
            fiyat_fn, ciz_fn = A.arac(s["arac"])
            parca = ciz_fn(t, s)
            z = int(s.get("katman", A.katman(s["arac"])))
            (arka if z < 0 else on).append(parca)
            cizilen.append(s["arac"])
            seviyeler += [round(float(f), 8) for f in fiyat_fn(t, s)]
        except Exception as e:  # noqa: BLE001
            uyari.append(f"{s.get('arac')}: çizilemedi — {e}")
    uyari += t.uyarilar

    svg = t.render("".join(on), arka_svg="".join(arka))
    cikti = Path(job.get("cikti") or "grafik.svg")
    if not cikti.is_absolute():
        cikti = taban / cikti
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(svg, encoding="utf-8")

    rapor = {
        "cikti": str(cikti),
        "bicim": "svg",
        "veri_kaynagi": kaynak,
        "bar_sayisi": len(mumlar),
        "son_fiyat": mumlar[-1]["close"],
        "fiyat_araligi": {"alt": round(t.lo, 8), "ust": round(t.hi, 8)},
        "cizim_sayisi": len(cizilen),
        "araclar": sorted(set(cizilen)),
        "cizilen_seviyeler": sorted(set(seviyeler)),
        "uyarilar": uyari,
        "not": ("Seviyeler job'dan/ölçülen yapıdan gelir; bu motor fiyat üretmez. "
                "Grafik karar DEĞİL, karar-desteğidir."),
    }
    if oto_rapor:
        rapor["otomatik"] = {k: v for k, v in oto_rapor.items() if k != "uyarilar"}
    # PNG opsiyonel — kurulu değilse sessizce atlanır (SVG zaten görüntülenebilir)
    if job.get("png"):
        try:
            import cairosvg  # noqa: PLC0415

            png = cikti.with_suffix(".png")
            cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(png),
                             output_width=t.W * 2)
            rapor["png"] = str(png)
        except Exception as e:  # noqa: BLE001
            rapor["png"] = f"VERİ YOK — png üretilemedi ({type(e).__name__})"
    return rapor


def main() -> int:
    ap = argparse.ArgumentParser(description="TradingView tarzı çizimli grafik (SVG)")
    ap.add_argument("--job", help="iş dosyası (JSON)")
    ap.add_argument("--araclar", action="store_true", help="araç listesini yaz")
    a = ap.parse_args()
    if a.araclar:
        print(json.dumps({
            "araclar": sorted(A.ARACLAR),
            "takma_adlar": A.TAKMA_AD,
            "fib_varsayilan_seviyeler": A.FIB_VARSAYILAN,
            "fib_genisleme_seviyeleri": A.FIB_GENISLEME,
        }, ensure_ascii=False, indent=2))
        return 0
    if not a.job:
        ap.error("--job gerekli")
    yol = Path(a.job).expanduser().resolve()
    job = json.loads(yol.read_text(encoding="utf-8"))
    try:
        rapor = uygula(job, yol.parent)
    except CizimError as e:
        print(json.dumps({"hata": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(rapor, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
