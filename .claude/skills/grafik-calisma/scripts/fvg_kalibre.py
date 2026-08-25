#!/usr/bin/env python3
"""FVG mitigasyon + filtre kalibrasyonu — eşikler SEÇİLMEZ, ÖLÇÜLÜR.

Sorun: yaygın FVG reçeteleri sabit sayılarla gelir ("ATR'nin %15'i", "40 derece
displacement", "48 saat ömür", "R:R en az 1:2", "%50 mitigasyon"). Bu sayıların
hiçbiri o koşunun verisinden türetilmemiştir; üstelik bir kısmı ÖLÇÜLEMEZ
(derece = eksen ölçeğine bağlı, zaman dilimi değişince anlamı değişir).

Bu modül aynı soruları ölçülebilir hale getirir ve her birini KOŞUNUN
KENDİ VERİSİNDEN yanıtlar:

  1. MİTİGASYON SEVİYESİ — bölgenin kaçı tükenince "dolu"? Seviye taranır
     (0.0 ilk dokunuş … 1.0 uzak kenar). Seviye giriş fiyatıdır da: smc_tespit
     `dolu` eşiği ile karar_motoru girişi (entry = fvg["ce"]) HİZALI olmak
     zorunda, yoksa girişi geçilmiş bölge "açık" görünür (fail-OPEN).
  2. ASGARİ BOYUT — gap/ATR dağılımının terzilleri kıyaslanır. Büyük gap'in
     beklentisi küçüğünkinden İSTATİSTİKSEL olarak ayrışmıyorsa filtre
     KANITLANMAMIŞTIR ve uygulanmaz (uydurma eşik yerine filtre yok).
  3. DISPLACEMENT KALİTESİ — "derece" ölçek-bağımlıdır, kullanılamaz. Yerine
     ölçek-bağımsız iki nicelik: displacement mumunun gövde/ATR'si ve
     gövde/menzil oranı. Aynı terzil testinden geçer.
  4. ÖMÜR (zaman aşımı) — "48 saat" yerine, dolan FVG'lerin dolum-süresi
     dağılımının quantile'ı (bar cinsinden; zaman dilimi verilirse saate çevrilir).
  5. STOP KURALI — "FVG sınırı ± ATR×0.10" (yapısal) ile MAE-türevi ATR stop
     yan yana koşulur; hangisinin beklentisi yüksek, ölçülür.
  6. R:R — "en az 1:2" yerine kalibrasyon.dinamik_min_rr: gereken R:R,
     kazanma oranının Wilson alt sınırından türetilen başabaş R:R'dir.

Aşırı-uyum freni: eşik "en iyi sonucu verene" çekilmez. Bir seviye ancak
(a) n >= n_taban, (b) bootstrap CI alt sınırı > 0, (c) permütasyon p <= alpha
kapılarının ÜÇÜNÜ birden geçerse aday olur; adaylar arasında seçim kötümser
ölçütle (Wilson alt sınırı) yapılır. Hiçbiri geçemezse eşik DEĞİŞTİRİLMEZ:
mevcut statik varsayım korunur ve "KALİBRE EDİLEMEDİ (fail-closed)" denir.
Kapı yalnız sıkılaşabilir; gevşetme yok.

Kullanım:
    python3 fvg_kalibre.py --job job.json
    job: {"candles": [...]} | {"input": "kline.json"} | {"klines": "kline.json"}
         opsiyonel: {"tf_dakika": 15, "params": {...}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kalibrasyon as kb  # noqa: E402
import smc_tespit as st  # noqa: E402


class KalibreError(Exception):
    pass


# Tarama ızgarası ve ölçüm konvansiyonları (piyasa eşiği DEĞİL — hepsi raporlanır)
VARSAYILAN = {
    "seviyeler": [0.0, 0.25, 0.5, 0.75, 1.0],
    "atr_period": 14,
    "max_bars": 20,          # işlem ufku (bar) — dolum sonrası izleme
    "dolum_ufku": 40,        # FVG'nin dolum için izlendiği azami bar
    "devam_barlari": [5, 10],
    "yapisal_tampon_atr": 0.10,   # SINANAN reçete: "FVG sınırı ± ATR×0.10"
    "omur_quantile": 0.8,
    "tercil_dusuk": 1 / 3.0,
    "tercil_yuksek": 2 / 3.0,
}


def _frame(job: dict) -> pd.DataFrame:
    """Mumları yükler. Ham Binance kline dosyası verildiyse parser motorun
    KENDİsinden (karar_motoru.parse_klines) alınır — ikinci bir parser yazmak
    ikinci bir doğruluk kaynağı demektir."""
    if job.get("candles") is not None or job.get("input"):
        return st.load_frame(job)
    p = job.get("klines")
    if not p:
        raise KalibreError("'candles', 'input' ya da 'klines' gerekli")
    kok = Path(__file__).resolve().parents[4]   # scripts→skill→skills→.claude→depo
    motor = kok / "engine"
    if str(motor) not in sys.path:
        sys.path.insert(0, str(motor))
    import karar_motoru as km  # noqa: PLC0415

    bars = km.parse_klines(str(Path(p).expanduser()))
    return st.load_frame({"candles": [{"open": b.o, "high": b.h, "low": b.l,
                                       "close": b.c, "volume": b.v} for b in bars]})


def fvg_ozellikleri(df: pd.DataFrame, atr: np.ndarray, mitigasyon_ref: float) -> list:
    """Her FVG için ölçek-BAĞIMSIZ nitelikler. Bölge tanımı smc_tespit.find_fvgs'ten
    İTHAL edilir (kopyalanmaz) — iki yerde iki tanım = sessiz sapma."""
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    o = df["open"].to_numpy(); c = df["close"].to_numpy()
    v = df["volume"].to_numpy() if "volume" in df.columns else np.full(len(df), np.nan)
    kayit = []
    for f in st.find_fvgs(df, mitigasyon_ref):
        i = int(f["i"])          # 3. mum (bölgenin kapandığı bar)
        d = i - 1                # DISPLACEMENT mumu = ORTA mum (3. değil!)
        a = float(atr[i]) if np.isfinite(atr[i]) and atr[i] > 0 else np.nan
        genislik = float(f["high"] - f["low"])
        govde = abs(float(c[d] - o[d]))
        menzil = float(h[d] - l[d])
        pencere = v[max(0, d - 20):d]
        vz = np.nan
        if pencere.size >= 5 and np.isfinite(pencere).all() and pencere.std() > 0:
            vz = float((v[d] - pencere.mean()) / pencere.std())
        kayit.append({
            "i": i, "tip": f["type"], "low": float(f["low"]), "high": float(f["high"]),
            "genislik": genislik,
            "genislik_atr": genislik / a if np.isfinite(a) else np.nan,
            "govde_atr": govde / a if np.isfinite(a) else np.nan,
            "govde_menzil": govde / menzil if menzil > 0 else np.nan,
            "hacim_z": vz,
            "atr": a,
        })
    return kayit


def _dolum_bari(h: np.ndarray, l: np.ndarray, rec: dict, seviye: float,
                ufuk: int) -> tuple:
    """Bölgenin `seviye` kadarına ilk ulaşılan bar ve o fiyat. Ulaşılmazsa (None, None).
    Eşik tanımı smc_tespit.find_fvgs ile BİREBİR aynı yönde hesaplanır."""
    i, lo, hi = rec["i"], rec["low"], rec["high"]
    n = len(h)
    son = min(i + ufuk, n - 1)
    if rec["tip"] == "bull":
        esik = hi - (hi - lo) * seviye
        for j in range(i + 1, son + 1):
            if l[j] <= esik:
                return j, esik
    else:
        esik = lo + (hi - lo) * seviye
        for j in range(i + 1, son + 1):
            if h[j] >= esik:
                return j, esik
    return None, None


def _devam(c: np.ndarray, j: int, esik: float, is_long: bool, k: int) -> bool | None:
    """Dolumdan k bar sonra fiyat FVG yönünde mi? (yön devamı metriği)"""
    if j + k >= len(c):
        return None
    fark = float(c[j + k] - esik)
    return (fark > 0) if is_long else (fark < 0)


def seviye_taramasi(df: pd.DataFrame, atr: np.ndarray, kayit: list, p: dict) -> list:
    """Her mitigasyon seviyesi için: dolum oranı, medyan gecikme, yön devamı,
    ve iki stop kuralıyla R beklentisi + permütasyon p-değeri."""
    h = df["high"].to_numpy(); l = df["low"].to_numpy(); c = df["close"].to_numpy()
    cikti = []
    for sv in p["seviyeler"]:
        dolan, gecikme, devam = [], [], {k: [] for k in p["devam_barlari"]}
        for rec in kayit:
            if not np.isfinite(rec["atr"]):
                continue
            j, esik = _dolum_bari(h, l, rec, sv, p["dolum_ufku"])
            if j is None:
                dolan.append(None)
                continue
            dolan.append((rec, j, esik))
            gecikme.append(j - rec["i"])
            for k in p["devam_barlari"]:
                d = _devam(c, j, esik, rec["tip"] == "bull", k)
                if d is not None:
                    devam[k].append(bool(d))
        dolumlar = [d for d in dolan if d is not None]
        n_top = len([d for d in dolan])
        satir = {
            "seviye": sv,
            "n_fvg": n_top,
            "n_dolan": len(dolumlar),
            "mitigasyon_orani": round(len(dolumlar) / n_top, 4) if n_top else None,
            "medyan_bar": float(np.median(gecikme)) if gecikme else None,
            "yon_devami": {f"{k}_bar": {
                "n": len(devam[k]),
                "oran": round(float(np.mean(devam[k])), 4) if devam[k] else None,
                "wilson_lo": round(kb.wilson_lo(int(np.sum(devam[k])), len(devam[k])), 4)
                if devam[k] else None} for k in p["devam_barlari"]},
            "dolum_ornekleri": dolumlar,
        }
        cikti.append(satir)
    return cikti


def _islemler(df, atr, dolumlar, stop_kural: str, atr_mult: float, tp_rr: float,
              p: dict) -> dict:
    """Dolum noktasından limit girişle işlem yürütür. İki stop kuralı sınanır:
      'atr'     → stop = giriş ∓ atr_mult×ATR (MAE-türevi çarpan)
      'yapisal' → stop = FVG'nin uzak kenarı ∓ tampon×ATR (SINANAN reçete)
    Mekanik kalibrasyon.walk_trade'dir: aynı barda SL+TP → SL (muhafazakâr)."""
    h = df["high"].to_numpy(); l = df["low"].to_numpy(); c = df["close"].to_numpy()
    rs, maes, dirs, kazanan_mae = [], [], [], []
    for rec, j, esik in dolumlar:
        a = rec["atr"]
        is_long = rec["tip"] == "bull"
        if stop_kural == "atr":
            sl = esik - atr_mult * a if is_long else esik + atr_mult * a
        else:
            tampon = p["yapisal_tampon_atr"] * a
            sl = (rec["low"] - tampon) if is_long else (rec["high"] + tampon)
        risk = (esik - sl) if is_long else (sl - esik)
        if risk <= 0:
            continue
        tp = esik + tp_rr * risk if is_long else esik - tp_rr * risk
        t = kb.walk_trade(h, l, c, j, esik, sl, tp, p["max_bars"], is_long)
        if t is None:
            continue
        r, _, mae = t
        rs.append(r); maes.append(mae / a if a > 0 else np.nan)
        dirs.append("long" if is_long else "short")
        if r > 0:
            kazanan_mae.append(mae / a if a > 0 else np.nan)
    if not rs:
        return {"n": 0, "sonuc": "VERİ YOK — işlem üretilmedi (fail-closed)"}
    rs_a = np.asarray(rs, dtype=float)
    wins = int((rs_a > 0).sum())
    return {
        "n": len(rs),
        "kazanma_orani": round(wins / len(rs), 4),
        "wilson_lo": round(kb.wilson_lo(wins, len(rs)), 4),
        "ortalama_r": round(float(rs_a.mean()), 4),
        "bootstrap_ci": kb.bootstrap_ci(rs_a),
        "dirs": dirs,
        "kazanan_mae_atr": [m for m in kazanan_mae if np.isfinite(m)],
    }


def tercil_testi(dolumlar_ile_r: list, anahtar: str) -> dict:
    """Bir niteliğin (gap/ATR, gövde/ATR …) filtre olarak KANITI var mı?
    Üst terzil ile alt terzilin R beklentisi bootstrap CI'ları AYRIK mı?
    Ayrık değilse filtre kanıtlanmamıştır → uygulanmaz (uydurma eşik yerine yok)."""
    vals = np.asarray([x[anahtar] for x in dolumlar_ile_r if np.isfinite(x[anahtar])],
                      dtype=float)
    rs = np.asarray([x["r"] for x in dolumlar_ile_r if np.isfinite(x[anahtar])],
                    dtype=float)
    n = vals.size
    if n < 2 * kb.KONVANSIYON["n_taban"]:
        return {"sonuc": "VERİ YOK", "n": int(n),
                "not": f"terzil testi için en az {2 * kb.KONVANSIYON['n_taban']} "
                       "örnek gerekir (fail-closed)"}
    q_lo = float(np.quantile(vals, VARSAYILAN["tercil_dusuk"]))
    q_hi = float(np.quantile(vals, VARSAYILAN["tercil_yuksek"]))
    alt = rs[vals <= q_lo]; ust = rs[vals >= q_hi]
    if alt.size < kb.KONVANSIYON["n_taban"] or ust.size < kb.KONVANSIYON["n_taban"]:
        return {"sonuc": "VERİ YOK", "n": int(n), "n_alt": int(alt.size),
                "n_ust": int(ust.size), "not": "terzil örneklemi taban altında"}
    ci_alt = kb.bootstrap_ci(alt); ci_ust = kb.bootstrap_ci(ust)
    ayrik = bool(ci_ust[0] > ci_alt[1])
    return {
        "sonuc": "FİLTRE KANITLI" if ayrik else "AYRIM YOK — filtre uygulanmaz",
        "n": int(n), "esik_q33": round(q_lo, 4), "esik_q67": round(q_hi, 4),
        "alt_tercil": {"n": int(alt.size), "ortalama_r": round(float(alt.mean()), 4),
                       "ci": ci_alt},
        "ust_tercil": {"n": int(ust.size), "ortalama_r": round(float(ust.mean()), 4),
                       "ci": ci_ust},
        "onerilen_esik": round(q_hi, 4) if ayrik else None,
    }


def kalibre(job: dict) -> dict:
    p = dict(VARSAYILAN)
    p.update(job.get("params") or {})
    df = _frame(job)
    atr = st.wilder_atr(df, int(p["atr_period"])).to_numpy()
    h = df["high"].to_numpy(); l = df["low"].to_numpy(); c = df["close"].to_numpy()

    kayit = fvg_ozellikleri(df, atr, st.FVG_MITIGASYON)
    if len(kayit) < kb.KONVANSIYON["n_taban"]:
        return {
            "sonuc": "VERİ YOK",
            "n_fvg": len(kayit),
            "gerekce": f"FVG sayısı {len(kayit)} < n_taban "
                       f"{kb.KONVANSIYON['n_taban']} — istatistik anlamsız (fail-closed)",
            "onerilen_params": {},
            "varsayimlar": kb.varsayim_defteri(),
        }

    tarama = seviye_taramasi(df, atr, kayit, p)

    # --- iki geçiş: 1) atr_mult=1.0 ile MAE topla → 2) MAE-türevi çarpanla yeniden
    for satir in tarama:
        dol = satir.pop("dolum_ornekleri")
        satir["islem"] = {}
        for kural in ("atr", "yapisal"):
            on = _islemler(df, atr, dol, kural, 1.0, 2.0, p)
            if on.get("n", 0) == 0:
                satir["islem"][kural] = on
                continue
            mult = kb.mae_atr_mult(on["kazanan_mae_atr"])
            rr = kb.dinamik_min_rr(int(round(on["kazanma_orani"] * on["n"])), on["n"])
            son = _islemler(df, atr, dol, kural, float(mult["atr_mult"]),
                            float(rr["min_rr"]), p)
            if son.get("n", 0) == 0:
                satir["islem"][kural] = son
                continue
            dirs = son.pop("dirs")
            son.pop("kazanan_mae_atr", None)
            son["atr_mult"] = mult
            son["min_rr"] = rr
            son["permutasyon"] = kb.permutation_pvalue(
                h, l, c, atr, son["ortalama_r"], dirs,
                float(mult["atr_mult"]), float(rr["min_rr"]), int(p["max_bars"]))
            satir["islem"][kural] = son
        satir["_dolumlar"] = dol

    # --- seçim: (seviye × stop kuralı) ızgarasının TAMAMI değerlendirilir ---
    # Yalnız bir stop kuralına bakmak, ölçülen diğer varyantı karara hiç sokmamak
    # (sessiz kayıp) olurdu. Izgara taranınca çokluluk sorunu doğar: 10 karşılaştırma
    # içinden "en iyisini" seçmek p-değerini şişirir (veri madenciliği). Bonferroni
    # ile alpha bölünür — aşırı-uyum freni.
    alpha = kb.KONVANSIYON["alpha"]
    kombin = [(s, kural) for s in tarama for kural in ("atr", "yapisal")
              if (s["islem"].get(kural) or {}).get("n", 0) >= kb.KONVANSIYON["n_taban"]]
    n_test = max(1, len(kombin))
    alpha_adj = alpha / n_test
    adaylar = []
    for s, kural in kombin:
        it = s["islem"][kural]
        ci = it.get("bootstrap_ci") or [-1, -1]
        pv = (it.get("permutasyon") or {}).get("p", 1.0)
        if ci[0] > 0 and pv <= alpha_adj:
            adaylar.append((it["wilson_lo"], it["ortalama_r"], s["seviye"], kural))
    coklu = {"n_karsilastirma": n_test, "alpha": alpha,
             "alpha_bonferroni": round(alpha_adj, 5),
             "kaynak": "Bonferroni: ızgaradan 'en iyiyi' seçmek p'yi şişirir"}
    if adaylar:
        adaylar.sort(reverse=True)
        w, r, sv, kural = adaylar[0]
        secilen = {"seviye": sv, "stop_kurali": kural, "wilson_lo": w, "ortalama_r": r,
                   "kaynak": "veri-türevi: 3 kapı (n>=taban, bootstrap CI alt>0, "
                             "permütasyon p<=alpha_Bonferroni) geçildi; adaylar "
                             "arasında Wilson alt sınırıyla seçildi",
                   "coklu_test": coklu}
    else:
        secilen = {"seviye": st.FVG_MITIGASYON, "stop_kurali": None, "wilson_lo": None,
                   "kaynak": "KALİBRE EDİLEMEDİ (fail-closed) — hiçbir (seviye × stop) "
                             "kombinasyonu üç kapıyı geçemedi; mevcut statik varsayım "
                             "KORUNUR, eşik gevşetilmez",
                   "coklu_test": coklu}

    # --- filtre kanıtı: gap/ATR ve displacement gövde/ATR (derece DEĞİL) ---
    ref = next((s for s in tarama if s["seviye"] == secilen["seviye"]), tarama[0])
    ornek = []
    for rec, j, esik in ref["_dolumlar"]:
        a = rec["atr"]
        is_long = rec["tip"] == "bull"
        sl = esik - a if is_long else esik + a
        risk = abs(esik - sl)
        tp = esik + 2.0 * risk if is_long else esik - 2.0 * risk
        t = kb.walk_trade(h, l, c, j, esik, sl, tp, int(p["max_bars"]), is_long)
        if t is None:
            continue
        ornek.append({"r": t[0], "genislik_atr": rec["genislik_atr"],
                      "govde_atr": rec["govde_atr"], "govde_menzil": rec["govde_menzil"]})
    filtreler = {
        "asgari_boyut_gap_atr": tercil_testi(ornek, "genislik_atr"),
        "displacement_govde_atr": tercil_testi(ornek, "govde_atr"),
        "displacement_govde_menzil": tercil_testi(ornek, "govde_menzil"),
    }

    # --- ömür: "48 saat" yerine ölçülen dolum gecikmesi quantile'ı ---
    gecikmeler = [j - rec["i"] for rec, j, _ in ref["_dolumlar"]]
    tf = job.get("tf_dakika")
    if gecikmeler:
        q = float(np.quantile(gecikmeler, p["omur_quantile"]))
        omur = {"bar": round(q, 1),
                "kaynak": f"veri-türevi: dolan FVG'lerin dolum-bar dağılımı "
                          f"q{p['omur_quantile']}",
                "kapsanan_oran": p["omur_quantile"],
                "dolum_ufku_bar": p["dolum_ufku"]}
        if tf:
            omur["saat"] = round(q * float(tf) / 60.0, 2)
    else:
        omur = {"bar": None, "kaynak": "VERİ YOK — dolan FVG yok (fail-closed)"}

    for s in tarama:
        s.pop("_dolumlar", None)

    gaps = np.asarray([r["genislik_atr"] for r in kayit
                       if np.isfinite(r["genislik_atr"])], dtype=float)
    return {
        "sonuc": "KALİBRE EDİLDİ" if adaylar else "KALİBRE EDİLEMEDİ (fail-closed)",
        "bar_sayisi": int(len(df)),
        "n_fvg": len(kayit),
        "gap_atr_dagilimi": {
            "medyan": round(float(np.median(gaps)), 4) if gaps.size else None,
            "q25": round(float(np.quantile(gaps, 0.25)), 4) if gaps.size else None,
            "q75": round(float(np.quantile(gaps, 0.75)), 4) if gaps.size else None,
        },
        "seviye_taramasi": tarama,
        "secilen_mitigasyon": secilen,
        "filtre_kanitlari": filtreler,
        "omur": omur,
        "onerilen_params": {"fvg_mitigasyon": secilen["seviye"]},
        "hizalama_kisiti": (
            "smc_tespit.find_fvgs 'dolu' eşiği ile karar_motoru girişinin (entry=CE) "
            "AYNI seviye olması zorunludur. Mitigasyon seviyesi değiştirilirse giriş "
            "de değişmeli; yoksa girişi geçilmiş bölge 'açık' görünür (fail-OPEN)."),
        "varsayimlar": kb.varsayim_defteri([
            f"seviye ızgarası={p['seviyeler']} (tarama çözünürlüğü; konvansiyon)",
            f"dolum ufku={p['dolum_ufku']} bar, işlem ufku={p['max_bars']} bar "
            "(ölçüm penceresi; varsayım)",
            f"yapısal stop tamponu={p['yapisal_tampon_atr']}×ATR — SINANAN reçete "
            "(kabul edilen kural değil)",
            f"ömür quantile={p['omur_quantile']} (kapsanma oranı; konvansiyon)",
            "FVG girişi LİMİT (seviyeye dokunuş), permütasyon null'ı MARKET "
            "(rastgele barın kapanışı) — mekanik asimetrisi bilinçli, etiketli",
            "displacement mumu = ORTA mum (i-1); 3. mum bölgeyi KAPATAN mumdur",
            "'derece/açı' ölçülmez (eksen ölçeğine bağlı) → gövde/ATR ve "
            "gövde/menzil ile değiştirildi",
        ]),
        "not": ("Ölçüm tek örneklemdir (bu koşunun barları). Kalibrasyon edge "
                "GARANTİSİ değildir; rejim değişince yeniden koşmak gerekir."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="FVG mitigasyon/filtre kalibrasyon motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(kalibre(job), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
