#!/usr/bin/env python3
# KAOS-UYUMLU v3.0-ADAPTIF — 4H stratejik + 15M taktik bölge/dönüş motoru (PAPER)
#
# Tasarım ilkeleri (kaos itirazına mühendislik cevabı):
#  1) SABİT MUTLAK EŞİK YOK: hacim/gövde/trend eşikleri her koşuda, yalnız o anki
#     geçmiş pencerenin KENDİ dağılımından (rolling quantile) yeniden hesaplanır.
#     Yapısal tanımlar (fraktal k=2, FVG geometrisi, close_location>=0.70) sabittir
#     ve "eşik" değil TANIM'dır; hepsi çıktıda listelenir.
#  2) LOOKAHEAD YOK: bar t'deki durum yalnız t ve öncesinden hesaplanır; fraktal
#     teyidi 2 bar gecikmeli kullanılır. --asof N ile geçmiş herhangi bir ana
#     gidilebilir; tam koşu ile önek koşusu aynı sinyali vermek ZORUNDADIR.
#  3) OLASILIK/İSABET İDDİASI YOK: çıktı SİNYAL/İZLE/YOK + VERİ-YETERSİZ üretir;
#     isabet, append-only defterde SONRADAN ölçülür (iddia edilmez, ölçülür).
#  4) REJİM KOŞULLAMASI: 15M sinyalleri 4H rejim etiketiyle birlikte verilir;
#     karşı-rejim sinyali "karşı-rejim" damgası taşır.
import json, sys, math

K = 2                 # fraktal kanat (yapısal tanım)
STRONG_CL = 0.70      # güçlü geri alım close_location eşiği (yapısal tanım, Ders Kitabı)
DONUS_PENCERE = 12    # sweep→displacement→BOS dizisinin tamamlanma penceresi (bar)
GECIKMELI_RECLAIM = 3 # sweep sonrası gecikmeli geri alım aranan bar sayısı
MIN_VOL_WIN = 30      # hacim yüzdeliği için asgari pencere
MIN_BODY_WIN = 30     # gövde quantile için asgari pencere

def yukle(path):
    with open(path) as f:
        raw = json.load(f)
    return [{"ot": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]),
             "c": float(r[4]), "v": float(r[5]), "ct": int(r[6])} for r in raw]

def quantile(xs, q):
    s = sorted(xs)
    if not s: return None
    i = (len(s) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (i - lo)

def atr(bars, n=14):
    if len(bars) < n + 1: return None
    trs = [max(b["h"]-b["l"], abs(b["h"]-a["c"]), abs(b["l"]-a["c"]))
           for a, b in zip(bars[-n-1:-1], bars[-n:])]
    return sum(trs) / n

def swingler(bars):
    """Teyitli fraktal swingler: i, ancak i+K bar kapandıktan sonra kullanılabilir."""
    sh, sl = [], []
    for i in range(K, len(bars) - K):
        w = bars[i-K:i+K+1]
        if bars[i]["h"] == max(b["h"] for b in w) and sum(1 for b in w if b["h"] == bars[i]["h"]) == 1:
            sh.append({"i": i, "ot": bars[i]["ot"], "lvl": bars[i]["h"], "teyit_i": i + K})
        if bars[i]["l"] == min(b["l"] for b in w) and sum(1 for b in w if b["l"] == bars[i]["l"]) == 1:
            sl.append({"i": i, "ot": bars[i]["ot"], "lvl": bars[i]["l"], "teyit_i": i + K})
    return sh, sl

def son_teyitli(swings, t, pred=lambda s: True):
    c = [s for s in swings if s["teyit_i"] <= t and pred(s)]
    return c[-1] if c else None

def close_loc(b, yon="up"):
    rng = b["h"] - b["l"]
    if rng == 0: return 0.5
    return (b["c"] - b["l"]) / rng if yon == "up" else (b["h"] - b["c"]) / rng

def vol_rank(bars, t):
    """bars[t] hacminin, önceki penceredeki yüzdelik sırası (0..1). Pencere yetersizse None."""
    win = [b["v"] for b in bars[max(0, t - 96):t]]
    if len(win) < MIN_VOL_WIN: return None
    return sum(1 for v in win if v < bars[t]["v"]) / len(win)

def govde_q90(bars, t):
    win = [abs(b["c"] - b["o"]) for b in bars[max(0, t - 48):t]]
    if len(win) < MIN_BODY_WIN: return None
    return quantile(win, 0.90)

def fvgler(bars, t):
    """t anına kadar oluşmuş FVG'ler + doluluk durumu (yalnız <=t barlarıyla)."""
    out = []
    for i in range(1, t):
        nb, pb = bars[i+1], bars[i-1]
        if i + 1 > t: break
        if nb["l"] > pb["h"]:
            g = {"tip": "BULL", "ot": bars[i]["ot"], "ust": nb["l"], "alt": pb["h"]}
        elif nb["h"] < pb["l"]:
            g = {"tip": "BEAR", "ot": bars[i]["ot"], "ust": pb["l"], "alt": nb["h"]}
        else:
            continue
        g["ce"] = round((g["ust"] + g["alt"]) / 2, 2)
        durum = "FRESH"
        for b in bars[i+2:t+1]:
            if g["tip"] == "BULL":
                if b["c"] < g["alt"] and b["o"] < g["alt"]: durum = "INVALID"; break
                if b["l"] <= g["alt"]: durum = "FULL_FILL"; break
                if b["l"] < g["ust"]: durum = "TESTED"
            else:
                if b["c"] > g["ust"] and b["o"] > g["ust"]: durum = "INVALID"; break
                if b["h"] >= g["ust"]: durum = "FULL_FILL"; break
                if b["h"] > g["alt"]: durum = "TESTED"
        g["durum"] = durum
        out.append(g)
    return out

def rejim_4h(b4):
    """Adaptif 4H rejimi. Eşik: |MA5-MA20| farkının kendi geçmiş dağılımının q60'ı;
    geçmiş < 10 örnekse fallback = 0.5 * ort(|4H getiri|) * MA20 (bayraklı)."""
    if len(b4) < 21:
        return {"durum": "VERI_YETERSIZ", "not": f"21 kapalı 4H gerekli, {len(b4)} var"}
    c = [b["c"] for b in b4]
    diffs = []
    for t in range(20, len(c)):
        diffs.append(sum(c[t-4:t+1])/5 - sum(c[t-19:t+1])/20)
    diff = diffs[-1]
    if len(diffs) >= 10:
        esik, esik_tipi = quantile([abs(d) for d in diffs[:-1]], 0.60), "rolling_q60"
    else:
        rets = [abs(c[i]/c[i-1] - 1) for i in range(len(c)-20, len(c))]
        esik, esik_tipi = 0.5 * (sum(rets)/len(rets)) * (sum(c[-20:])/20), "fallback_getiri(BAYRAK)"
    yon = "UP" if diff > esik else ("DOWN" if diff < -esik else "NEUTRAL")
    sh4, sl4 = swingler(b4)
    t = len(b4) - 1
    izle = None
    lsl, lsh = son_teyitli(sl4, t), son_teyitli(sh4, t)
    if lsl and b4[-1]["l"] < lsl["lvl"] and b4[-1]["c"] > lsl["lvl"]:
        izle = {"tip": "4H_SSL_SWEEP_RECLAIM", "seviye": lsl["lvl"], "kol": "LONG-dönüş"}
    if lsh and b4[-1]["h"] > lsh["lvl"] and b4[-1]["c"] < lsh["lvl"]:
        izle = {"tip": "4H_BSL_SWEEP_REJECT", "seviye": lsh["lvl"], "kol": "SHORT-dönüş"}
    return {"durum": yon, "ma_farki": round(diff, 2), "esik": round(esik, 2),
            "esik_tipi": esik_tipi, "donus_izleme": izle,
            "son_4h_swing_high": lsh and lsh["lvl"], "son_4h_swing_low": lsl and lsl["lvl"]}

def donus_taramasi(bars, t, sh, sl):
    """Sweep→karşı yön displacement(FVG)→BOS dizisi; DONUS_PENCERE içinde tamamlanırsa SİNYAL."""
    sonuc = {"long": {"asama": 0}, "short": {"asama": 0}}
    bq = govde_q90(bars, t)
    for yon in ("long", "short"):
        sw_list = sl if yon == "long" else sh
        op_list = sh if yon == "long" else sl
        for s_i in range(max(K, t - DONUS_PENCERE), t + 1):
            ref = son_teyitli(sw_list, s_i, lambda s: s["i"] < s_i - 0)
            ref = ref if (ref and ref["teyit_i"] <= s_i) else None
            if not ref: continue
            b = bars[s_i]
            swept = b["l"] < ref["lvl"] if yon == "long" else b["h"] > ref["lvl"]
            if not swept: continue
            recl_i, recl_tip = None, None
            same = (b["c"] > ref["lvl"]) if yon == "long" else (b["c"] < ref["lvl"])
            if same:
                recl_i = s_i
                cl = close_loc(b, "up" if yon == "long" else "down")
                recl_tip = "AYNI_BAR_GUCLU" if cl >= STRONG_CL else "AYNI_BAR_ZAYIF"
            else:
                for j in range(s_i + 1, min(s_i + 1 + GECIKMELI_RECLAIM, t + 1)):
                    ok = (bars[j]["c"] > ref["lvl"] and bars[j]["o"] > ref["lvl"] * 0) if False else \
                         (min(bars[j]["o"], bars[j]["c"]) > ref["lvl"] if yon == "long"
                          else max(bars[j]["o"], bars[j]["c"]) < ref["lvl"])
                    if ok: recl_i, recl_tip = j, "GECIKMELI"; break
            if recl_i is None:
                sonuc[yon] = max(sonuc[yon], {"asama": 1, "sweep_ot": b["ot"], "seviye": ref["lvl"],
                                              "not": "sweep var, geri alım YOK"}, key=lambda x: x["asama"])
                continue
            disp = None
            for j in range(recl_i, t + 1):
                d = bars[j]; body = d["c"] - d["o"]
                yonlu = body > 0 if yon == "long" else body < 0
                if not yonlu: continue
                if bq is None: break
                vr = vol_rank(bars, j)
                if abs(body) >= bq and (vr is None or vr >= 0.80):
                    disp = {"i": j, "ot": d["ot"], "govde": round(abs(body), 1),
                            "vol_rank": vr, "origin": d["l"] if yon == "long" else d["h"]}
                    break
            if not disp:
                sonuc[yon] = max(sonuc[yon], {"asama": 2, "sweep_ot": b["ot"], "seviye": ref["lvl"],
                                              "reclaim": recl_tip, "not": "displacement bekleniyor"},
                                 key=lambda x: x["asama"])
                continue
            bos = None
            opp = son_teyitli(op_list, disp["i"], lambda s: s["i"] < disp["i"])
            if opp:
                for j in range(disp["i"], t + 1):
                    d = bars[j]
                    kirdi = (min(d["o"], d["c"]) > opp["lvl"]) if yon == "long" else (max(d["o"], d["c"]) < opp["lvl"])
                    if kirdi: bos = {"i": j, "ot": d["ot"], "kirilan": opp["lvl"]}; break
            if bos:
                sonuc[yon] = {"asama": 3, "SINYAL": True, "sweep_ot": b["ot"], "sweep_seviye": ref["lvl"],
                              "reclaim": recl_tip, "displacement": disp, "bos": bos,
                              "iptal": b["l"] if yon == "long" else b["h"]}
            else:
                sonuc[yon] = max(sonuc[yon], {"asama": 2.5, "sweep_ot": b["ot"], "reclaim": recl_tip,
                                              "displacement": disp, "not": "BOS bekleniyor"},
                                 key=lambda x: x["asama"])
    return sonuc

def analiz(b15, b4):
    t = len(b15) - 1
    uyari = []
    a0 = atr(b15)
    if a0 is None: return {"durum": "VERI_YETERSIZ", "not": "15 kapalı 15M bar bile yok"}
    sh, sl = swingler(b15)
    r4 = rejim_4h(b4)
    vr_c0 = vol_rank(b15, t)
    if vr_c0 is None: uyari.append("hacim yüzdeliği penceresi yetersiz")
    if govde_q90(b15, t) is None: uyari.append("gövde q90 penceresi yetersiz")
    donus = donus_taramasi(b15, t, sh, sl)
    fv = [g for g in fvgler(b15, t) if g["durum"] in ("FRESH", "TESTED")][-4:]
    lsh, lsl = son_teyitli(sh, t), son_teyitli(sl, t)
    pusu = []
    for g in fv:
        pusu.append({"tip": f"FVG_{g['tip']}", "bolge": [g["alt"], g["ust"]], "ce": g["ce"],
                     "durum": g["durum"], "iptal": ("gövde kapanışı < " + str(g["alt"])) if g["tip"] == "BULL"
                     else ("gövde kapanışı > " + str(g["ust"]))})
    market = None
    c0 = b15[t]
    if lsh and c0["c"] > lsh["lvl"]:
        market = {"yon": "LONG", "teyit": f"sonraki 15M gövde kapanışı > {c0['h']} (C0 tepesi)",
                  "dayanak": f"C0 kapanışı {c0['c']} son teyitli swing {lsh['lvl']} üstünde"}
    elif lsl and c0["c"] < lsl["lvl"]:
        market = {"yon": "SHORT", "teyit": f"sonraki 15M gövde kapanışı < {c0['l']} (C0 dibi)",
                  "dayanak": f"C0 kapanışı {c0['c']} son teyitli swing {lsl['lvl']} altında"}
    sinyaller = []
    for yon in ("long", "short"):
        d = donus[yon]
        if d.get("SINYAL"):
            rejim_uyum = (r4.get("durum") == ("UP" if yon == "long" else "DOWN"))
            sinyaller.append({"tip": f"DONUS_{yon.upper()}", **d,
                              "rejim_uyumu": "uyumlu" if rejim_uyum else "KARŞI-REJİM"})
        elif d.get("asama", 0) >= 1:
            sinyaller.append({"tip": f"IZLE_{yon.upper()}", **d})
    esikler = {"atr0": round(a0, 2), "c0_vol_rank": vr_c0,
               "govde_q90": govde_q90(b15, t) and round(govde_q90(b15, t), 1),
               "yapisal_sabitler": {"fraktal_k": K, "guclu_close_loc": STRONG_CL,
                                    "donus_pencere": DONUS_PENCERE}}
    return {"asof_ot": c0["ot"], "c0": {"o": c0["o"], "h": c0["h"], "l": c0["l"], "c": c0["c"]},
            "rejim_4h": r4, "sinyaller": sinyaller, "pusu_bolgeleri": pusu,
            "market_durumu": market, "atr_zarf": [round(c0["c"] - 1.2*a0, 1), round(c0["c"] + 1.2*a0, 1)],
            "son_teyitli_swingler": {"high": lsh and lsh["lvl"], "low": lsl and lsl["lvl"]},
            "adaptif_esik_anlik": esikler, "veri_uyarilari": uyari,
            "not": "PAPER — olasılık/isabet iddiası yok; isabet defterde sonradan ölçülür"}

if __name__ == "__main__":
    p15, p4 = sys.argv[1], sys.argv[2]
    b15, b4 = yukle(p15), yukle(p4)
    if "--asof" in sys.argv:
        n = int(sys.argv[sys.argv.index("--asof") + 1])
        b15 = b15[:n]
        b4 = [b for b in b4 if b["ct"] <= b15[-1]["ct"]]
    print(json.dumps(analiz(b15, b4), indent=1, ensure_ascii=False))
