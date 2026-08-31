#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SPESIFIKASYON TESTLERI — konsey_tek.py'den BAGIMSIZ referanslarla.

TDD kurali: bu testler KODA gore yazilmadi; tanimlardan (Wilder 1978 ATR,
3-bar FVG imbalans tanimi, Kelly cebiri, zaman-damgasi sozlesmesi) yazildi.
Her karsilastirma, testin ICINDE bagimsiz (naive/brute-force) bir referans
hesapla yapilir. FAIL cikarsa KOD duzeltilir, test DEGISTIRILMEZ; test ancak
spesifikasyonun kendisi yanlis yazilmissa duzeltilir ve bu ACIKCA raporlanir.
"""
import importlib.util, json, math, random, sys, time

spec = importlib.util.spec_from_file_location("kt", "konsey_tek.py")
kt = importlib.util.module_from_spec(spec); sys.modules["kt"] = kt
spec.loader.exec_module(kt)

SONUC = []
def kayit(ad, ok, detay=""):
    SONUC.append((ad, ok, detay))
    print("[%s] %s  %s" % ("PASS" if ok else "FAIL", ad, detay))

def bar(o, h, l, c, v=1000.0):
    return {"o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": float(v)}

def rasgele_seri(n, tohum, p0=100.0, sigma=0.8):
    rnd = random.Random(tohum); p = p0; out = []
    for _ in range(n):
        o = p; p = max(1.0, p + rnd.gauss(0, sigma))
        h = max(o, p) + abs(rnd.gauss(0, sigma * 0.5))
        l = max(0.5, min(o, p) - abs(rnd.gauss(0, sigma * 0.5)))
        out.append(bar(o, h, l, p, abs(rnd.gauss(1000, 200))))
    return out

# ---------------------------------------------------------------- S1: Wilder ATR
def ref_atr(barlar, n=14):
    """Wilder (1978) tanimindan bagimsiz hesap: TR = max(h-l,|h-pc|,|l-pc|);
    tohum = ilk n TR ortalamasi; sonra ATR = (ATR*(n-1)+TR)/n."""
    tr = []
    for i in range(1, len(barlar)):
        b, p = barlar[i], barlar[i-1]
        tr.append(max(b["h"]-b["l"], abs(b["h"]-p["c"]), abs(b["l"]-p["c"])))
    if len(tr) < n: return sum(tr)/len(tr) if tr else None
    a = sum(tr[:n])/n
    for x in tr[n:]: a = (a*(n-1)+x)/n
    return a

hata = 0
for t in range(10):
    s = rasgele_seri(120, t)
    r1, r2 = kt.wilder_atr(s, 14), ref_atr(s, 14)
    if r1 is None or abs(r1-r2) > 1e-9: hata += 1
kayit("S1 Wilder ATR = bagimsiz referans (10 seri, tol 1e-9)", hata == 0, f"hata={hata}")

# ------------------------------------------------------- S2: FVG (3-bar imbalans)
def ref_fvg(barlar, mg=0.5):
    """Tanimdan brute-force: bull FVG i'de low[i] > high[i-2]; bolge
    [high[i-2], low[i]]. Sonraki barlar bolgeye girdikce dolan kisim
    fiyatin girdigi taraftan olculur; kalan/genislik > 1-mg ise ACIK."""
    out = []
    for i in range(2, len(barlar)):
        h0, l0 = barlar[i-2]["h"], barlar[i-2]["l"]
        h2, l2 = barlar[i]["h"], barlar[i]["l"]
        if l2 > h0: alt, ust, yon = h0, l2, "bull"
        elif l0 > h2: alt, ust, yon = h2, l0, "bear"
        else: continue
        g = ust - alt
        if g <= 0: continue
        ka, ku = alt, ust
        for j in range(i+1, len(barlar)):
            hj, lj = barlar[j]["h"], barlar[j]["l"]
            if yon == "bull":
                if lj < ku: ku = max(ka, lj)      # yukaridan dolum
            else:
                if hj > ka: ka = min(ku, hj)      # asagidan dolum
        if (ku-ka)/g > (1.0-mg):
            out.append((i, round(ka, 8), round(ku, 8), yon))
    return out

hata, ornek = 0, ""
for t in range(60):
    s = rasgele_seri(80, 1000+t)
    m = {(f["bar"], f["alt"], f["ust"], f["yon"]) for f in kt.acik_fvgler(s)}
    r = set(ref_fvg(s))
    if m != r:
        hata += 1
        if not ornek: ornek = f"tohum={1000+t} kod={sorted(m)[:2]} ref={sorted(r)[:2]}"
kayit("S2 FVG = tanimdan brute-force (60 rastgele seri)", hata == 0, ornek or "60/60 ayni")

# --------------------------------------------- S3: rr_denetim cebir + monotonluk
ok3 = True; det3 = []
r = kt.rr_denetim("LONG", 100.0, 90.0, 115.0, 10.0)
if not (r["verdict"] == "TUTARLI" and abs(r["R_rapor"] - 1.5) < 1e-9):
    ok3 = False; det3.append(f"cebir: {r}")
onceki = 0.0
for hedef in (105.0, 110.0, 115.0, 118.0):
    rr = kt.rr_denetim("LONG", 100.0, 90.0, hedef, 10.0)
    if rr["R_rapor"] is None or rr["R_rapor"] < onceki:
        ok3 = False; det3.append(f"monotonluk bozuk @hedef={hedef}")
    onceki = rr["R_rapor"]
for rr in (kt.rr_denetim("LONG", 100.0, 99.9, 140.0, 10.0),):
    if not (rr["verdict"] == "SISIRILMIS" and rr["R_gercekci"] <= rr["R_rapor"]):
        ok3 = False; det3.append("sisirilmis R_ger > R_rap")
for kotu in (("LONG", 100.0, 110.0, 120.0), ("SHORT", 100.0, 90.0, 80.0),
             ("LONG", 100.0, 100.0, 110.0)):
    if kt.rr_denetim(kotu[0], kotu[1], kotu[2], kotu[3], 10.0)["verdict"] != "GECERSIZ":
        ok3 = False; det3.append(f"gecersiz gecti: {kotu}")
kayit("S3 rr_denetim: cebir, monotonluk, gecersiz geometri", ok3, "; ".join(det3))

# ------------------------------------------------- S4: h4_hizala sozlesmesi
def ref_hizala(m15, h4):
    """Sozlesme (v2 — SPEC DUZELTMESI, raporda beyan edildi): amac 'karar
    barini kapsayan EN GUNCEL 4H satiri'dir; dolayisiyla t4<=t15 olanlar
    icinde EN GEC ZAMANLI bar secilir; ayni zaman birden coksa en buyuk
    orijinal indeks. (v1 'en buyuk indeks' diyordu — sirasiz seride amaca
    aykiri.)"""
    out = []
    for b in m15:
        t = b["t"]; en, ent = -1, None
        for j, hb in enumerate(h4):
            if hb["t"] <= t and (ent is None or hb["t"] > ent or (hb["t"] == ent and j > en)):
                en, ent = j, hb["t"]
        out.append(en)
    return out

hata = 0
for t in range(30):
    rnd = random.Random(t)
    t0 = 1_700_000_000_000
    m15 = [{"t": t0 + i*900_000 + rnd.randint(0, 100), "o":1,"h":2,"l":0.5,"c":1} for i in range(rnd.randint(5, 60))]
    h4 = [{"t": t0 - rnd.randint(0, 3)*14_400_000 + j*14_400_000, "o":1,"h":2,"l":0.5,"c":1} for j in range(rnd.randint(1, 15))]
    if kt.h4_hizala(m15, h4) != ref_hizala(m15, h4): hata += 1
kayit("S4 h4_hizala = brute-force zaman sozlesmesi (30 vaka)", hata == 0, f"hata={hata}")

# ------------------------------------------------- S5: stake Kelly cebiri
g = kt.stake_kapisi(100, 55, 12.0, 60.5, -48.5)
p_, b_, a_ = 55/100, 60.5/55, 48.5/45
edge = 12.0/100
beklenen = min(edge/(a_*b_), 0.25)
kayit("S5 stake = edge/(a*b) bagimsiz cebir", g["acik"] and abs(g["stake"]-beklenen) < 1e-12,
      f"kod={g['stake']:.6f} ref={beklenen:.6f}")

# ------------------------------------------------- S6: yon_turet sinirlari
ok6, det6 = True, []
for h4t in ("bull", "bear", "notr"):
    for m15t in ("bull", "bear", "notr"):
        for rej in ("range", "trend"):
            y = kt.yon_turet({"trend": h4t, "rejim": "trend"}, {"trend": m15t, "rejim": rej}, None)
            if not (-1.0 - 1e-9 <= y["skor"] <= 1.0 + 1e-9): ok6 = False; det6.append("sinir")
            if y["yon"] == "LONG" and y["skor"] <= 0: ok6 = False; det6.append("isaret")
            if y["yon"] == "SHORT" and y["skor"] >= 0: ok6 = False; det6.append("isaret")
kayit("S6 yon_turet: skor [-1,1], yon-isaret tutarli (18 kombinasyon)", ok6, "; ".join(set(det6)))

# ------------------------------------------------- S7: SAGLAMLIK (bozuk girdi)
def coker(fn, *a):
    try:
        fn(*a); return None
    except Exception as e:
        return f"{type(e).__name__}"

ok7, det7 = True, []
for ad, sonuc in (("trend_oku BOS liste", coker(kt.trend_oku, [])),
                  ("trend_oku TEK bar", coker(kt.trend_oku, [bar(1, 2, 0.5, 1)])),
                  ("emir_plani BOS m15", coker(kt.emir_plani, [], [], "LONG")),
                  ("yapi_ozeti BOS", coker(kt.yapi_ozeti, [], [])),
                  ("ani_hareket BOS", coker(kt.ani_hareket, [], 10.0)),
                  ("tazelik BOS", coker(kt.tazelik, [], "15m"))):
    if sonuc is not None:
        ok7 = False; det7.append(f"{ad} -> {sonuc}")
kayit("S7 saglamlik: bos/yetersiz girdi COKERTMEZ (kontrollu sonuc)", ok7, "; ".join(det7))

# ------------------------------------------------- S8: kapi determinizmi + fuzz
r1 = kt.EvidenceRegistry(task_id="X"); r1.add_source("S1", "y", "d", "CURRENT", content="x")
r1.add_evidence("E1", "S1", "m", "d", "g"); r1.add_claim("C1", "s", "VERIFIED", ["E1"], "DONE")
a1, a2 = r1.audit(), r1.audit()
kayit("S8a registry.audit deterministik", a1.decision == a2.decision == "PUBLISH_FULL", a1.decision)

rnd = random.Random(7); cokme = 0
for _ in range(2000):
    v = {"claims": [{"claim_id": "C", "importance": rnd.choice(["CRITICAL", "NORMAL", None]),
                     "status": rnd.choice(["VERIFIED", "BOZUK", None, 7]),
                     "evidence_ids": rnd.choice([[], ["E"], ["YOK"], None])}],
         "sources": rnd.choice([[], [{"source_id": "S", "access_status": rnd.choice(["ACCESSIBLE", "X", None])}]]),
         "evidence": rnd.choice([[], [{"evidence_id": "E", "source_id": rnd.choice(["S", "YOK"])}]]),
         "counter_evidence_search": rnd.choice([{}, {"status": "COMPLETED"}, {"status": None}]),
         "conflicts": rnd.choice([[], ["x"]]), "decision": rnd.choice(["PUBLISH_FULL", "SACMA", None])}
    try:
        a = kt.independent_publication_gate(v)
        assert a.final_decision in kt.KAPI_YAYIN_KARARLARI
    except AssertionError:
        cokme += 1
    except Exception:
        cokme += 1
kayit("S8b kullanici kapisi fuzz: 2000 bozuk girdi, karar kumesi disina cikmaz/cokmez",
      cokme == 0, f"cokme={cokme}")
# evidence_ids=None coker mi ayri olcum (bilinen risk):
try:
    kt.independent_publication_gate({"claims": [{"claim_id": "C", "importance": "CRITICAL",
                                                 "status": "VERIFIED", "evidence_ids": None}],
                                     "sources": [], "evidence": [],
                                     "counter_evidence_search": {}, "conflicts": [],
                                     "decision": "PUBLISH_FULL"})
    kayit("S8c kullanici kapisi: evidence_ids=None kontrollu", True, "")
except Exception as e:
    kayit("S8c kullanici kapisi: evidence_ids=None kontrollu", False, type(e).__name__)

print()
h = sum(1 for _, ok, _ in SONUC if not ok)
print(f"{len(SONUC)-h}/{len(SONUC)} PASS")
sys.exit(1 if h else 0)
