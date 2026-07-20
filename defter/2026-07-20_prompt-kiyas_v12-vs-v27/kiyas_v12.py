# C0-VETO v1.2 (Kimi) deterministik katmanlarinin ayni C0 verisi uzerinde kosulmasi
# Amac: v2.7 PRAGMATIK ciktisiyla capraz kiyas. Birincil yol Decimal/float; ikinci yol bagimsiz yeniden hesap.
import json, math, statistics as st

SCRATCH = "/tmp/claude-0/-home-user-Future-/dd8980b7-319d-5ec4-b020-599136e15744/scratchpad"
CAPTURE = 1784548920000

def load(name):
    with open(f"{SCRATCH}/{name}") as f:
        raw = json.load(f)
    return [{"ot": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]),
             "c": float(r[4]), "v": float(r[5]), "ct": int(r[6])} for r in raw]

m = [r for r in load("klines_15m.json") if r["ct"] < CAPTURE]   # 59 kapali
h4 = [r for r in load("klines_4h.json") if r["ct"] < CAPTURE]   # 21 kapali
C = [r["c"] for r in m]; H = [r["h"] for r in m]; L = [r["l"] for r in m]; V = [r["v"] for r in m]
out = {"veri": {"kapali_15m": len(m), "kapali_4h": len(h4)}}

# o1 TR/ATR14
TR = [max(m[i]["h"]-m[i]["l"], abs(m[i]["h"]-C[i-1]), abs(m[i]["l"]-C[i-1])) for i in range(1, len(m))]
ATR = sum(TR[-14:])/14
# o2 mom1
mom1 = (C[-1]-C[-2])/ATR
# o3 volz (son 20 bar C0 haric) — populasyon ve ornek sapma ikisi de
vwin = V[-21:-1]
volz_p = (V[-1]-st.mean(vwin))/st.pstdev(vwin)
volz_s = (V[-1]-st.mean(vwin))/st.stdev(vwin)
# o4 ER10
er10 = abs(C[-1]-C[-11]) / sum(abs(C[i]-C[i-1]) for i in range(len(C)-10, len(C)))
# o5 mb
mb = math.tanh(((C[-1]-C[-6])/ATR)/2.0)
# o6 tb (4H)
c4 = [r["c"] for r in h4]
ma5, ma20 = st.mean(c4[-5:]), st.mean(c4[-20:])
rets4 = [abs(c4[i]/c4[i-1]-1) for i in range(len(c4)-20, len(c4))]
tb_esik = max(0.0008, 0.5*st.mean(rets4))
tb_rel = (ma5-ma20)/ma20
tb = 1 if tb_rel > tb_esik else (-1 if tb_rel < -tb_esik else 0)
# o7 rpos — 60 bar gerekir, 59 var -> EKSIK bayragiyla 59 uzerinden
rl, rh = min(L), max(H)
rpos = (C[-1]-rl)/(rh-rl)*2 - 1
# o8 prh/prl (son 40, C0 haric)
prl = min(r["l"] for r in m[-41:-1]); prh = max(r["h"] for r in m[-41:-1])
# o9 rrl/rrh (son 43'un son 3 haric dilimi)
seg = m[-43:-3]
rrl = min(r["l"] for r in seg); rrh = max(r["h"] for r in seg)
out["olcumler"] = {"ATR": round(ATR,4), "mom1": round(mom1,4), "volz_pop": round(volz_p,3),
                   "volz_sample": round(volz_s,3), "ER10": round(er10,4), "mb": round(mb,4),
                   "tb_rel": round(tb_rel,6), "tb_esik": round(tb_esik,6), "tb": tb,
                   "rpos_59bar_EKSIK60": round(rpos,4), "rl": rl, "rh": rh,
                   "prl": prl, "prh": prh, "rrl": rrl, "rrh": rrh}

# vol rejimi: ratio = ort3(TR)/medyan50(TR); 60 gecmis ratio YOK -> sabit esikler (damga)
ratio = st.mean(TR[-3:]) / st.median(TR[-50:])
vr = "EXTREME" if ratio >= 2.0 else ("EXPANDING" if ratio >= 1.4 else ("COMPRESSED" if ratio <= 0.6 else ("LOW" if ratio <= 0.85 else "NORMAL")))
# onceki barin rejimi (bekci b: tek adimda LOW/COMPRESSED->EXTREME)
ratio_prev = st.mean(TR[-4:-1]) / st.median(TR[-51:-1])
vr_prev = "EXTREME" if ratio_prev >= 2.0 else ("EXPANDING" if ratio_prev >= 1.4 else ("COMPRESSED" if ratio_prev <= 0.6 else ("LOW" if ratio_prev <= 0.85 else "NORMAL")))
out["vol_rejimi"] = {"ratio": round(ratio,4), "rejim": vr, "esik_tipi": "SABIT (60 gecmis ratio yok)",
                     "onceki_bar_ratio": round(ratio_prev,4), "onceki_rejim": vr_prev}

# K8 boyutlar
D1 = ("SU" if (er10 > 0.35 and mb > 0.20) else "WU") if tb > 0 else (("SD" if (er10 > 0.35 and mb < -0.20) else "WD") if tb < 0 else ("WU" if mb > 0.30 else ("WD" if mb < -0.30 else "RG")))
D2 = "SQUEEZE" if vr in ("COMPRESSED","LOW") else ("EXPANSION" if vr in ("EXPANDING","EXTREME") else "NORMAL")
D3 = "DIP" if rpos < -0.33 else ("TOP" if rpos > 0.33 else "MID")
D4 = "NEU (funding sayisal verisi yok)"
# yardimcilar (C0 uzerinde)
c0 = m[-1]; rng = c0["h"]-c0["l"]
tested_sup = (c0["l"]-rl) <= 0.25*ATR
tested_res = (rh-c0["h"]) <= 0.25*ATR
dip_rej = (((c0["c"]-c0["l"]) if False else (min(c0["o"],c0["c"])-c0["l"])) > 0.45*rng and c0["c"] > c0["l"]+0.5*rng) or (c0["c"] > C[-5])
top_rej = ((c0["h"]-max(c0["o"],c0["c"])) > 0.45*rng and c0["c"] < c0["h"]-0.5*rng) or (c0["c"] < C[-5])
# rejim zinciri
volx_proxy = (vr == "EXTREME" and abs(mom1) > 2.0)
if volx_proxy: rejim = (12, "VOL-PATLAMA(proxy)", "1")
elif D3 == "DIP" and (tested_sup and dip_rej): rejim = (8, "REVERSAL-BOTTOM", "2")
elif D3 == "TOP" and (tested_res and top_rej): rejim = (9, "REVERSAL-TOP", "3")
elif D2 == "EXPANSION" and (c0["c"] > prh or c0["c"] < prl): rejim = (7, "BREAKOUT-EXPANSION", "4")
elif D2 == "SQUEEZE" and D1 == "RG": rejim = (5, "RANGE-TIGHT", "5")
elif D1 == "SU": rejim = (1, "TREND-UP-STRONG", "6")
elif D1 == "WU": rejim = (2, "TREND-UP-PULLBACK", "6")
elif D1 == "SD": rejim = (3, "TREND-DOWN-STRONG", "6")
elif D1 == "WD": rejim = (4, "TREND-DOWN-BOUNCE", "6")
else: rejim = (6, "RANGE-WIDE", "7 (OI sayisal yok -> 10/11 uretilemez)")
# olaylar
ev = {}
ev["ev2_V_DIP"] = tested_sup and dip_rej
ev["ev3_V_TOP"] = tested_res and top_rej
ev["ev6_SFP"] = (c0["l"] <= prl and c0["c"] > prl + 0.15*ATR) or (c0["h"] >= prh and c0["c"] < prh - 0.15*ATR)
ev["ev4_PUMP"] = volz_p >= 1.8 and mom1 > 0.8
ev["ev5_DUMP"] = volz_p >= 1.8 and mom1 < -0.8
ev["ev7_FBO"] = any((b["c"] > rrh or b["c"] < rrl) for b in m[-4:-1]) and (rrl <= c0["c"] <= rrh)
ev["ev8_EXH"] = volz_p >= 2.0 and abs(mom1) < 0.4
ev["ev9_SQZ"] = D2 == "SQUEEZE"
ev["ev10_SH"] = (C[-2] >= rrl and C[-2] <= rrh) and ((c0["l"] <= rrl and c0["c"] < rrl) or (c0["h"] >= rrh and c0["c"] > rrh))
ev["ev11_FFLIP"] = False  # funding serisi sayisal yok
ev["ev12_VOLX"] = volx_proxy and not (ev["ev4_PUMP"] or ev["ev5_DUMP"] or ev["ev8_EXH"])
aktif = [k for k, v in ev.items() if v]
oncelik = ["ev2_V_DIP","ev3_V_TOP","ev6_SFP","ev4_PUMP","ev5_DUMP","ev8_EXH","ev9_SQZ","ev12_VOLX","ev11_FFLIP","ev7_FBO","ev10_SH"]
manset = next((k for k in oncelik if ev[k]), "ev1_BAZ")
olay_no = int(manset.split("_")[0][2:]) if manset != "ev1_BAZ" else 1
hucre = (rejim[0]-1)*12 + olay_no
aile = {1:"TREND-YUKARI",2:"TREND-YUKARI",3:"TREND-ASAGI",4:"TREND-ASAGI",5:"YATAY",6:"YATAY",
        7:"KIRILIM-VOL",12:"KIRILIM-VOL",8:"DONUS",9:"DONUS",10:"POZISYONLANMA",11:"POZISYONLANMA"}[rejim[0]]
out["K8"] = {"D1": D1, "D2": D2, "D3": D3, "D4": D4,
             "tested_res": tested_res, "top_rej": top_rej,
             "rejim": f"{rejim[0]} {rejim[1]} (zincir {rejim[2]})",
             "olaylar_aktif": aktif, "manset": manset, "hucre": hucre, "aile": aile}

# K4 bekci (hesaplanabilenler)
gaps = sum(1 for a, b in zip(m, m[1:]) if b["ot"]-a["ot"] != 900000)
bayat_kayit_aninda = False  # capture 12:02, C0 kapanis 11:59:59 -> taze
out["K4"] = {"a_bosluk": gaps, "a_bayat_kayit_aninda": bayat_kayit_aninda,
             "b_mom1_robustz": "HESAPLANAMAZ (96 bar gerekli, 58 mom1 var)",
             "b_rejim_sicramasi_LOWdanEXTREME": (vr_prev in ("LOW","COMPRESSED") and vr == "EXTREME"),
             "d_rpos_disi": abs(rpos) > 1, "d_ratio_ilk_kez_EXTREME": (vr == "EXTREME" and vr_prev != "EXTREME")}

# sonuc tanimi seviyeleri (C0+16 icin)
out["sonuc_seviyeleri"] = {"first_leg_bant": [round(C[-1]-0.25*ATR,1), round(C[-1]+0.25*ATR,1)],
                           "first_passage": {"hedef": round(C[-1]+1.2*ATR,1), "stop": round(C[-1]-1.2*ATR,1)},
                           "endpoint_esik": [round(C[-1]-0.10*ATR,1), round(C[-1]+0.10*ATR,1)],
                           "cozum_icin_gerekli": "C0+16 kapali 15M bar (12:00-15:45 UTC) — ELDE YOK"}

# ikinci yol: kilit metrikler bagimsiz tekrar
assert abs(mom1 - (64970.80-64807.10)/ATR) < 1e-12
assert abs(mb - math.tanh(((64970.80-64304.90)/ATR)/2)) < 1e-12  # C-5 = 10:30 kapanisi 64304.90
assert prh == 64940.00 and prl == 63736.10  # v2.7 ile ayni pencere -> ayni deger cikmali
print(json.dumps(out, indent=1, ensure_ascii=False))
