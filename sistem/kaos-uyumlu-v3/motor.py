#!/usr/bin/env python3
# KAOS-UYUMLU v3.1-ADAPTIF — 4H stratejik + 15M taktik bölge/dönüş motoru (PAPER)
# v3.0 → v3.1: adversarial doğrulama (wf_c13d5d60) bulgularının tamamı işlendi:
#   - market yönü: SHORT'u maskeleyen elif kaldırıldı; çift kırılımda YENİ swing kazanır, tazelik bayrağı eklendi
#   - rejim bilinmiyorken sinyale "KARŞI-REJİM" damgası basılmaz → "rejim_bilinmiyor"
#   - displacement hacim/gövde penceresi yetersizse filtre SESSİZCE atlanmaz; tespit devre dışı + uyarı
#   - bq/vol_rank displacement adayının KENDİ barının penceresinden hesaplanır (pencere-içi kayma giderildi)
#   - TÜM sabitler SABITLER sözlüğünde ve çıktıda beyan edilir; fiyat alanları referans-ölçekli yuvarlanır
#   - FVG INVALID tanımı ilan edilen iptal kuralıyla (gövde KAPANIŞI bölge dışına) hizalandı
#   - ölü kod/çift kontrol temizlendi; --asof sınır korumaları; asof'suz koşuda açık-bar uyarısı; 4H hizalama her koşuda
#
# Tasarım ilkeleri (kaos itirazına mühendislik cevabı):
#  1) SABİT MUTLAK EŞİK YOK: hacim/gövde/trend eşikleri her koşuda, o anki geçmiş pencerenin
#     KENDİ dağılımından (rolling quantile / rank) yeniden hesaplanır — ölçek-bağımsız.
#  2) Yapısal tanımlar (geometri) sabittir, "eşik" değildir; TAMAMI aşağıdaki SABITLER'de ve çıktıda.
#  3) LOOKAHEAD YOK: fraktal teyidi +2 bar gecikmeli; --asof N önek koşusu = tam koşu (doğrulandı).
#  4) OLASILIK/İSABET İDDİASI YOK: çıktı SİNYAL/İZLE/YOK + VERİ-YETERSİZ; isabet defterde ölçülür.
#  5) REJİM KOŞULLAMASI: sinyaller 4H rejim etiketi taşır; rejim bilinmiyorsa bu açıkça yazılır.
import json, sys, math

SABITLER = {
    "fraktal_k": 2,                # swing tanımı: bar, 2'şer komşusunun ekstremi
    "guclu_close_loc": 0.70,       # güçlü geri alım close_location eşiği (Ders Kitabı tanımı)
    "donus_pencere": 12,           # sweep→displacement→BOS dizisinin tamamlanma penceresi (bar)
    "gecikmeli_reclaim": 3,        # sweep sonrası gecikmeli gövde geri alımı aranan bar sayısı
    "atr_periyot": 14,
    "atr_zarf_carpan": 1.2,
    "vol_rank_penceresi": 96,      # hacim yüzdelik sırası geriye bakış
    "min_vol_penceresi": 30,       # bu kadar geçmiş yoksa hacim filtresi HESAPLANAMAZ (sinyal kilitlenir)
    "govde_penceresi": 48,         # displacement gövde quantile geriye bakış
    "min_govde_penceresi": 30,
    "govde_quantile": 0.90,        # displacement gövdesi >= bu quantile
    "disp_vol_rank_esigi": 0.80,   # displacement hacim rank şartı
    "fvg_rapor_limiti": 4,         # raporlanan açık FVG sayısı (en yeniler)
    "rejim_quantile": 0.60,        # 4H |MA5-MA20| eşiği: kendi geçmişinin q60'ı
    "rejim_min_ornek": 10,         # q60 için asgari örnek; azsa getiri-fallback (BAYRAKLI)
    "rejim_fallback_carpani": 0.5, # fallback eşik = 0.5 * ort|4H getiri| * MA20
}
K = SABITLER["fraktal_k"]
STRONG_CL = SABITLER["guclu_close_loc"]
DONUS_PENCERE = SABITLER["donus_pencere"]
GECIKMELI_RECLAIM = SABITLER["gecikmeli_reclaim"]

def yukle(path):
    with open(path) as f:
        raw = json.load(f)
    return [{"ot": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]),
             "c": float(r[4]), "v": float(r[5]), "ct": int(r[6])} for r in raw]

def prc(x, ref):
    """Fiyat alanı yuvarlama: referans fiyatın ölçeğine göre (8 anlamlı hane) — mutlak ondalık varsayımı yok."""
    if x is None: return None
    r = abs(ref) if ref else 1.0
    nd = max(0, 8 - (int(math.floor(math.log10(r))) + 1)) if r > 0 else 8
    return round(x, nd)

def quantile(xs, q):
    s = sorted(xs)
    if not s: return None
    i = (len(s) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (i - lo)

def atr(bars, n=SABITLER["atr_periyot"]):
    if len(bars) < n + 1: return None
    trs = [max(b["h"]-b["l"], abs(b["h"]-a["c"]), abs(b["l"]-a["c"]))
           for a, b in zip(bars[-n-1:-1], bars[-n:])]
    return sum(trs) / n

def swingler(bars):
    """Teyitli fraktal swingler: i, ancak i+K bar kapandıktan sonra kullanılabilir (teyit_i)."""
    sh, sl = [], []
    for i in range(K, len(bars) - K):
        w = bars[i-K:i+K+1]
        if bars[i]["h"] == max(b["h"] for b in w) and sum(1 for b in w if b["h"] == bars[i]["h"]) == 1:
            sh.append({"i": i, "ot": bars[i]["ot"], "lvl": bars[i]["h"], "teyit_i": i + K})
        if bars[i]["l"] == min(b["l"] for b in w) and sum(1 for b in w if b["l"] == bars[i]["l"]) == 1:
            sl.append({"i": i, "ot": bars[i]["ot"], "lvl": bars[i]["l"], "teyit_i": i + K})
    return sh, sl

def son_teyitli(swings, t):
    c = [s for s in swings if s["teyit_i"] <= t]
    return c[-1] if c else None

def close_loc(b, yon="up"):
    rng = b["h"] - b["l"]
    if rng == 0: return 0.5
    return (b["c"] - b["l"]) / rng if yon == "up" else (b["h"] - b["c"]) / rng

def vol_rank(bars, t):
    """bars[t] hacminin, KENDİ öncesindeki penceredeki yüzdelik sırası (0..1); pencere yetersizse None."""
    win = [b["v"] for b in bars[max(0, t - SABITLER["vol_rank_penceresi"]):t]]
    if len(win) < SABITLER["min_vol_penceresi"]: return None
    return sum(1 for v in win if v < bars[t]["v"]) / len(win)

def govde_q90(bars, t):
    win = [abs(b["c"] - b["o"]) for b in bars[max(0, t - SABITLER["govde_penceresi"]):t]]
    if len(win) < SABITLER["min_govde_penceresi"]: return None
    return quantile(win, SABITLER["govde_quantile"])

def fvgler(bars, t):
    """t anına kadar oluşmuş FVG'ler + doluluk. INVALID = ilan edilen iptal kuralı:
    gövde KAPANIŞI bölgenin arkasına geçti (BULL: c < alt; BEAR: c > üst)."""
    out = []
    for i in range(1, t):
        nb, pb = bars[i+1], bars[i-1]
        if nb["l"] > pb["h"]:
            g = {"tip": "BULL", "ot": bars[i]["ot"], "ust": nb["l"], "alt": pb["h"]}
        elif nb["h"] < pb["l"]:
            g = {"tip": "BEAR", "ot": bars[i]["ot"], "ust": pb["l"], "alt": nb["h"]}
        else:
            continue
        g["ce"] = (g["ust"] + g["alt"]) / 2
        durum = "FRESH"
        for b in bars[i+2:t+1]:
            if g["tip"] == "BULL":
                if b["c"] < g["alt"]: durum = "INVALID"; break
                if b["l"] <= g["alt"]: durum = "FULL_FILL"; break
                if b["l"] < g["ust"]: durum = "TESTED"
            else:
                if b["c"] > g["ust"]: durum = "INVALID"; break
                if b["h"] >= g["ust"]: durum = "FULL_FILL"; break
                if b["h"] > g["alt"]: durum = "TESTED"
        g["durum"] = durum
        out.append(g)
    return out

def rejim_4h(b4):
    """Adaptif 4H rejimi. Eşik: |MA5-MA20| geçmişinin q60'ı; örnek azsa getiri-fallback (BAYRAKLI)."""
    if len(b4) < 21:
        return {"durum": "VERI_YETERSIZ", "not": f"21 kapalı 4H gerekli, {len(b4)} var"}
    c = [b["c"] for b in b4]
    diffs = [sum(c[t-4:t+1])/5 - sum(c[t-19:t+1])/20 for t in range(20, len(c))]
    diff = diffs[-1]
    if len(diffs) - 1 >= SABITLER["rejim_min_ornek"]:
        esik, esik_tipi = quantile([abs(d) for d in diffs[:-1]], SABITLER["rejim_quantile"]), "rolling_q60"
    else:
        rets = [abs(c[i]/c[i-1] - 1) for i in range(len(c)-20, len(c))]
        esik = SABITLER["rejim_fallback_carpani"] * (sum(rets)/len(rets)) * (sum(c[-20:])/20)
        esik_tipi = "fallback_getiri(BAYRAK)"
    yon = "UP" if diff > esik else ("DOWN" if diff < -esik else "NEUTRAL")
    sh4, sl4 = swingler(b4)
    t = len(b4) - 1
    izle = None
    lsl, lsh = son_teyitli(sl4, t), son_teyitli(sh4, t)
    if lsl and b4[-1]["l"] < lsl["lvl"] and b4[-1]["c"] > lsl["lvl"]:
        izle = {"tip": "4H_SSL_SWEEP_RECLAIM", "seviye": lsl["lvl"], "kol": "LONG-dönüş"}
    if lsh and b4[-1]["h"] > lsh["lvl"] and b4[-1]["c"] < lsh["lvl"]:
        izle = {"tip": "4H_BSL_SWEEP_REJECT", "seviye": lsh["lvl"], "kol": "SHORT-dönüş"}
    ref = c[-1]
    return {"durum": yon, "ma_farki": prc(diff, ref), "esik": prc(esik, ref),
            "esik_tipi": esik_tipi, "donus_izleme": izle,
            "son_4h_swing_high": lsh and lsh["lvl"], "son_4h_swing_low": lsl and lsl["lvl"]}

def donus_taramasi(bars, t, sh, sl):
    """Sweep→geri alım→karşı yön displacement(gövde q90 + hacim rank)→BOS dizisi.
    Döndürür: (sonuç, uyarı kümesi). Filtre penceresi yetersizse tespit DEVRE DIŞI kalır ve uyarı yazılır."""
    sonuc = {"long": {"asama": 0}, "short": {"asama": 0}}
    uyarilar = set()
    for yon in ("long", "short"):
        sw_list = sl if yon == "long" else sh
        op_list = sh if yon == "long" else sl
        for s_i in range(max(K, t - DONUS_PENCERE), t + 1):
            ref = son_teyitli(sw_list, s_i)
            if not ref: continue
            b = bars[s_i]
            swept = b["l"] < ref["lvl"] if yon == "long" else b["h"] > ref["lvl"]
            if not swept: continue
            recl_i, recl_tip = None, None
            same = (b["c"] > ref["lvl"]) if yon == "long" else (b["c"] < ref["lvl"])
            if same:
                cl = close_loc(b, "up" if yon == "long" else "down")
                recl_i = s_i
                recl_tip = "AYNI_BAR_GUCLU" if cl >= STRONG_CL else "AYNI_BAR_ZAYIF"
            else:
                for j in range(s_i + 1, min(s_i + 1 + GECIKMELI_RECLAIM, t + 1)):
                    b2 = bars[j]
                    ok = (min(b2["o"], b2["c"]) > ref["lvl"]) if yon == "long" else \
                         (max(b2["o"], b2["c"]) < ref["lvl"])
                    if ok: recl_i, recl_tip = j, "GECIKMELI"; break
            if recl_i is None:
                sonuc[yon] = max(sonuc[yon], {"asama": 1, "sweep_ot": b["ot"], "seviye": ref["lvl"],
                                              "not": "sweep var, geri alım YOK"}, key=lambda x: x["asama"])
                continue
            disp, disp_engelli = None, False
            for j in range(recl_i, t + 1):
                d = bars[j]; body = d["c"] - d["o"]
                if (body > 0 if yon == "long" else body < 0) is False: continue
                bqj, vrj = govde_q90(bars, j), vol_rank(bars, j)
                if bqj is None or vrj is None:
                    disp_engelli = True
                    uyarilar.add("displacement tespiti devre dışı (gövde/hacim penceresi yetersiz)")
                    continue
                if abs(body) >= bqj and vrj >= SABITLER["disp_vol_rank_esigi"]:
                    disp = {"i": j, "ot": d["ot"], "govde": abs(body), "vol_rank": vrj,
                            "origin": d["l"] if yon == "long" else d["h"]}
                    break
            if not disp:
                nt = "displacement tespiti devre dışı (pencere yetersiz)" if disp_engelli else "displacement bekleniyor"
                sonuc[yon] = max(sonuc[yon], {"asama": 2, "sweep_ot": b["ot"], "seviye": ref["lvl"],
                                              "reclaim": recl_tip, "not": nt}, key=lambda x: x["asama"])
                continue
            bos = None
            opp = son_teyitli(op_list, disp["i"])
            if opp:
                for j in range(disp["i"], t + 1):
                    d = bars[j]
                    kirdi = (min(d["o"], d["c"]) > opp["lvl"]) if yon == "long" else (max(d["o"], d["c"]) < opp["lvl"])
                    if kirdi: bos = {"i": j, "ot": d["ot"], "kirilan": opp["lvl"]}; break
            if bos:
                sonuc[yon] = {"asama": 3, "SINYAL": True, "sweep_ot": b["ot"], "seviye": ref["lvl"],
                              "reclaim": recl_tip, "displacement": disp, "bos": bos,
                              "iptal": b["l"] if yon == "long" else b["h"]}
            else:
                sonuc[yon] = max(sonuc[yon], {"asama": 2.5, "sweep_ot": b["ot"], "seviye": ref["lvl"],
                                              "reclaim": recl_tip, "displacement": disp,
                                              "not": "BOS bekleniyor"}, key=lambda x: x["asama"])
    return sonuc, uyarilar

def analiz(b15, b4):
    if not b15:
        return {"durum": "VERI_YETERSIZ", "not": "hiç 15M bar yok"}
    t = len(b15) - 1
    uyari = []
    a0 = atr(b15)
    if a0 is None:
        return {"durum": "VERI_YETERSIZ", "not": f"{SABITLER['atr_periyot']+1} kapalı 15M bar gerekli, {len(b15)} var"}
    c0 = b15[t]
    R = c0["c"]  # yuvarlama referans ölçeği
    sh, sl = swingler(b15)
    r4 = rejim_4h(b4)
    if vol_rank(b15, t) is None: uyari.append("hacim yüzdeliği penceresi yetersiz")
    if govde_q90(b15, t) is None: uyari.append("gövde q90 penceresi yetersiz")
    donus, donus_uyari = donus_taramasi(b15, t, sh, sl)
    uyari += sorted(donus_uyari)
    fv = [g for g in fvgler(b15, t) if g["durum"] in ("FRESH", "TESTED")][-SABITLER["fvg_rapor_limiti"]:]
    lsh, lsl = son_teyitli(sh, t), son_teyitli(sl, t)
    pusu = [{"tip": f"FVG_{g['tip']}", "bolge": [prc(g["alt"], R), prc(g["ust"], R)],
             "ce": prc(g["ce"], R), "durum": g["durum"],
             "iptal": (f"gövde kapanışı < {prc(g['alt'], R)}" if g["tip"] == "BULL"
                       else f"gövde kapanışı > {prc(g['ust'], R)}")} for g in fv]
    # market durumu: iki kırılım koşulu da bakılır; ikisi de doğruysa DAHA YENİ teyitli swing kazanır
    long_k = bool(lsh and c0["c"] > lsh["lvl"])
    short_k = bool(lsl and c0["c"] < lsl["lvl"])
    if long_k and short_k:
        long_k = lsh["i"] > lsl["i"]
        short_k = not long_k
    market = None
    if long_k:
        taze = t == 0 or b15[t-1]["c"] <= lsh["lvl"]
        market = {"yon": "LONG", "teyit": f"sonraki 15M gövde kapanışı > {prc(c0['h'], R)} (C0 tepesi)",
                  "dayanak": f"C0 kapanışı {prc(c0['c'], R)} son teyitli swing {prc(lsh['lvl'], R)} üstünde",
                  "kirilim_taze": taze}
    elif short_k:
        taze = t == 0 or b15[t-1]["c"] >= lsl["lvl"]
        market = {"yon": "SHORT", "teyit": f"sonraki 15M gövde kapanışı < {prc(c0['l'], R)} (C0 dibi)",
                  "dayanak": f"C0 kapanışı {prc(c0['c'], R)} son teyitli swing {prc(lsl['lvl'], R)} altında",
                  "kirilim_taze": taze}
    sinyaller = []
    r4d = r4.get("durum")
    for yon in ("long", "short"):
        d = donus[yon]
        if d.get("SINYAL"):
            if r4d in ("UP", "DOWN"):
                uyum = "uyumlu" if r4d == ("UP" if yon == "long" else "DOWN") else "KARŞI-REJİM"
            else:
                uyum = "rejim_bilinmiyor"
            sinyaller.append({"tip": f"DONUS_{yon.upper()}", **d, "rejim_uyumu": uyum})
        elif d.get("asama", 0) >= 1:
            sinyaller.append({"tip": f"IZLE_{yon.upper()}", **d})
    return {"asof_ot": c0["ot"], "c0": {k: c0[k] for k in ("o", "h", "l", "c")},
            "rejim_4h": r4, "sinyaller": sinyaller, "pusu_bolgeleri": pusu,
            "market_durumu": market,
            "atr_zarf": [prc(c0["c"] - SABITLER["atr_zarf_carpan"]*a0, R),
                         prc(c0["c"] + SABITLER["atr_zarf_carpan"]*a0, R)],
            "son_teyitli_swingler": {"high": lsh and lsh["lvl"], "low": lsl and lsl["lvl"]},
            "adaptif_esik_anlik": {"atr0": prc(a0, R), "c0_vol_rank": vol_rank(b15, t),
                                   "govde_q90": prc(govde_q90(b15, t), R)},
            "yapisal_sabitler": SABITLER, "veri_uyarilari": uyari,
            "not": "PAPER — olasılık/isabet iddiası yok; isabet defterde sonradan ölçülür"}

if __name__ == "__main__":
    p15, p4 = sys.argv[1], sys.argv[2]
    b15, b4 = yukle(p15), yukle(p4)
    ana_uyari = []
    if "--asof" in sys.argv:
        n = int(sys.argv[sys.argv.index("--asof") + 1])
        if n < 1 or n > len(b15):
            n2 = max(1, min(n, len(b15))) if b15 else 0
            ana_uyari.append(f"--asof {n} aralık dışı → {n2} olarak kırpıldı")
            n = n2
        b15 = b15[:n]
    else:
        ana_uyari.append("--asof verilmedi: son barın KAPALI olduğu doğrulanamıyor; kapalı bar sayısıyla --asof kullanın")
    b4 = [b for b in b4 if b15 and b["ct"] <= b15[-1]["ct"]]
    out = analiz(b15, b4)
    if ana_uyari:
        out["veri_uyarilari"] = ana_uyari + out.get("veri_uyarilari", [])
    print(json.dumps(out, indent=1, ensure_ascii=False))
