#!/usr/bin/env python3
# NET-KARAR v1.0 — motor v3.1 üzerinde KARAR KATMANI (PAPER)
# Sözleşme: her koşuda TEK karar (LONG/SHORT/BEKLE), TEK plan, TEK iptal.
# Senaryo çatalı, "olursa... olursa..." dili ve çoklu alternatif YASAK.
# Karar sırası (ilk tutan kazanır, deterministik):
#   1) Tamamlanmış DONUS sinyali -> o yön
#   2) market_durumu var ve 4H rejimi karşı değil -> o yön
#   3) 4H rejimi UP/DOWN -> o yön (giriş: uygun bölgeden)
#   4) hiçbiri -> BEKLE (bu da bir karardır; gerekçesi tek satır yazılır)
# Plan: giriş = yön tarafındaki en taze bölgenin CE'si (yoksa ATR zarf kenarı);
#       stop = bölge arka kenarı (gövde kapanışı ötesi = iptal);
#       T1 = ilgili 4H swing / havuz, T2 = ATR zarf ucu. R iki hedef için yazılır.
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from motor import yukle, analiz, prc

def karar(b15, b4):
    a = analiz(b15, b4)
    if a.get("durum") == "VERI_YETERSIZ":
        return {"KARAR": "BEKLE", "NEDEN": a["not"], "PLAN": None}
    R = a["c0"]["c"]
    r4 = a["rejim_4h"].get("durum")
    donus = next((s for s in a["sinyaller"] if s["tip"].startswith("DONUS_")), None)
    yon, neden = None, None
    if donus:
        yon = "LONG" if donus["tip"] == "DONUS_LONG" else "SHORT"
        neden = f"tamamlanmış dönüş dizisi (sweep {donus['seviye']} -> displacement -> BOS)"
    elif a["market_durumu"] and not (
            (a["market_durumu"]["yon"] == "LONG" and r4 == "DOWN") or
            (a["market_durumu"]["yon"] == "SHORT" and r4 == "UP")):
        yon = a["market_durumu"]["yon"]
        neden = a["market_durumu"]["dayanak"] + (f"; 4H rejimi {r4}" if r4 in ("UP", "DOWN") else "")
    elif r4 in ("UP", "DOWN"):
        yon = "LONG" if r4 == "UP" else "SHORT"
        neden = f"4H rejimi {r4} (ma_farkı {a['rejim_4h']['ma_farki']})"
    if yon is None:
        return {"KARAR": "BEKLE", "NEDEN": "ne dönüş sinyali, ne yapı kırılımı, ne 4H rejimi var",
                "PLAN": None, "asof_ot": a["asof_ot"]}
    ist = "FVG_BULL" if yon == "LONG" else "FVG_BEAR"
    bolge = next((p for p in reversed(a["pusu_bolgeleri"]) if p["tip"] == ist), None)
    zarf = a["atr_zarf"]
    if bolge:
        giris, giris_tip = bolge["ce"], f"limit — {bolge['tip']} CE ({bolge['bolge'][0]}–{bolge['bolge'][1]})"
        stop = bolge["bolge"][0] if yon == "LONG" else bolge["bolge"][1]
    else:
        giris = zarf[0] if yon == "LONG" else zarf[1]
        giris_tip = "limit — ATR zarf kenarı (bölge yok)"
        stop = prc(giris - (zarf[1]-zarf[0]) * 0.25, R) if yon == "LONG" else prc(giris + (zarf[1]-zarf[0]) * 0.25, R)
    sw = a["rejim_4h"].get("son_4h_swing_high") if yon == "LONG" else a["rejim_4h"].get("son_4h_swing_low")
    t1 = sw if sw and ((sw > giris) if yon == "LONG" else (sw < giris)) else (zarf[1] if yon == "LONG" else zarf[0])
    t2 = zarf[1] if yon == "LONG" else zarf[0]
    if t1 == t2:
        t1 = prc((giris + t2) / 2, R)
    risk = abs(giris - stop)
    r1 = prc(abs(t1 - giris) / risk, 100) if risk else None
    r2 = prc(abs(t2 - giris) / risk, 100) if risk else None
    return {"KARAR": yon, "NEDEN": neden,
            "PLAN": {"GIRIS": giris, "GIRIS_TIPI": giris_tip, "STOP": stop,
                     "IPTAL": f"15M gövde kapanışı {'<' if yon=='LONG' else '>'} {stop}",
                     "T1": t1, "T2": t2, "R": [r1, r2]},
            "asof_ot": a["asof_ot"], "rejim_4h": r4,
            "not": "PAPER — yatırım tavsiyesi değildir"}

if __name__ == "__main__":
    b15, b4 = yukle(sys.argv[1]), yukle(sys.argv[2])
    if "--asof" in sys.argv:
        n = int(sys.argv[sys.argv.index("--asof") + 1])
        b15 = b15[:max(1, min(n, len(b15)))]
    b4 = [b for b in b4 if b15 and b["ct"] <= b15[-1]["ct"]]
    print(json.dumps(karar(b15, b4), indent=1, ensure_ascii=False))
