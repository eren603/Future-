# C0-VETO v2.7 koşusu DENETİM-A: koşuda hesaplanmayan/karara girmeyen kalemlerin post-hoc hesabı
# Birincil yol Decimal; ikinci yol float64 + (taker için) quote-taban çapraz oran.
import json
from decimal import Decimal as D

SCRATCH = "/tmp/claude-0/-home-user-Future-/dd8980b7-319d-5ec4-b020-599136e15744/scratchpad"
CAPTURE = 1784548920000

def load(name):
    with open(f"{SCRATCH}/{name}") as f:
        raw = json.load(f)
    return [{"ot": int(r[0]), "o": D(r[1]), "h": D(r[2]), "l": D(r[3]), "c": D(r[4]),
             "v": D(r[5]), "ct": int(r[6]), "q": D(r[7]), "n": int(r[8]),
             "tbb": D(r[9]), "tbq": D(r[10])} for r in raw]

m15 = [r for r in load("klines_15m.json") if r["ct"] < CAPTURE]
h4 = [r for r in load("klines_4h.json") if r["ct"] < CAPTURE]
C0 = m15[-1]
DISP = [r for r in m15 if r["ot"] == 1784547000000][0]

rep = {}

# 1) TAKER-BUY ORANI (koşuda hiç hesaplanmadı)
def share(rows):
    return sum(r["tbb"] for r in rows) / sum(r["v"] for r in rows)
rep["taker_buy_share"] = {
    "displacement_1130": str(DISP["tbb"] / DISP["v"]),
    "C0_1145": str(C0["tbb"] / C0["v"]),
    "son6bar": str(share(m15[-6:])),
    "oturum_59bar": str(share(m15)),
}
# ikinci yol: quote-taban oran (bağımsız kolonlar) + float64
for k, rows in (("displacement_1130", [DISP]), ("C0_1145", [C0]), ("son6bar", m15[-6:]), ("oturum_59bar", m15)):
    qs = sum(r["tbq"] for r in rows) / sum(r["q"] for r in rows)
    fs = sum(float(r["tbb"]) for r in rows) / sum(float(r["v"]) for r in rows)
    assert abs(float(D(rep["taker_buy_share"][k])) - fs) < 1e-9
    rep["taker_buy_share"][k + "_quote_capraz"] = str(qs)

# delta (2*tbb - v) proxy
rep["delta_proxy_BTC"] = {"son6bar": str(sum(2 * r["tbb"] - r["v"] for r in m15[-6:])),
                          "oturum": str(sum(2 * r["tbb"] - r["v"] for r in m15))}

# 2) QUOTE-VOLUME MUTABAKATI (koşuda recon'a dahil edilmemişti)
qrec = []
for H in h4:
    seg = [r for r in m15 if H["ot"] <= r["ot"] < H["ot"] + 14_400_000]
    if len(seg) == 16:
        qrec.append({"ot": H["ot"], "diff_q": str(sum(r["q"] for r in seg) - H["q"]),
                     "diff_tbb": str(sum(r["tbb"] for r in seg) - H["tbb"])})
rep["quote_recon_4h"] = qrec

# 3) CLOSE->OPEN SÜREKLİLİĞİ (koşuda denetlenmedi)
rep["max_close_open_drift"] = {
    "m15": str(max(abs(b["o"] - a["c"]) for a, b in zip(m15, m15[1:]))),
    "h4": str(max(abs(b["o"] - a["c"]) for a, b in zip(h4, h4[1:]))),
}

# 4) EŞİT-TEPE / EŞİT-DİP KÜMELERİ (Beceri-2 tanımında var, koşuda kodlanmadı)
def clusters(vals, tol):
    vs = sorted(vals); out = []
    cur = [vs[0]]
    for v in vs[1:]:
        if v - cur[-1] <= tol:
            cur.append(v)
        else:
            out.append(cur); cur = [v]
    out.append(cur)
    return [c for c in out if len(c) >= 2]

highs_above = [r["h"] for r in m15 if r["h"] > C0["c"]]
for tol_bp in ("0.0002", "0.0005"):  # %0.02 ve %0.05
    tol = C0["c"] * D(tol_bp)
    rep[f"esit_tepe_kumeleri_tol_{tol_bp}"] = [
        {"seviyeler": [str(x) for x in c], "kume_ust": str(max(c))} for c in clusters(highs_above, tol)]
unswept_lows = [D(x) for x in ("64137.00", "63858.10", "63736.10")]
rep["esit_dip_kumesi_var_mi"] = bool(clusters(unswept_lows, C0["c"] * D("0.0005")))

# 5) RAPORDAKİ ELLE HESAPLARIN SCRIPT DOĞRULAMASI + KÜME KABULÜNDE R DEĞİŞİMİ
CE, STOP, STOP_D = D("64591.85"), D("64316.00"), D("64137.00")
T1, T1_KUME, T2 = D("65084.60"), D("65048.30"), D("65187.71714285714285714285714")
def r(e, s, t): return (t - e) / (e - s)
rep["R_dogrulama"] = {
    "pusu_CE_derin_stop_T1": str(r(CE, STOP_D, T1)),          # raporda elle 1.08 denmişti
    "pusu_CE_T1_kume_kabulunde": str(r(CE, STOP, T1_KUME)),   # koşuda hiç hesaplanmamıştı
    "pusu_CE_derin_stop_T1_kume": str(r(CE, STOP_D, T1_KUME)),
    "pusu_CE_derin_stop_T2": str(r(CE, STOP_D, T2)),
}
for k, v in rep["R_dogrulama"].items():
    pass
# float64 ikinci yol
assert abs(float(D(rep["R_dogrulama"]["pusu_CE_derin_stop_T1"])) - (65084.60-64591.85)/(64591.85-64137.00)) < 1e-9
assert abs(float(D(rep["R_dogrulama"]["pusu_CE_T1_kume_kabulunde"])) - (65048.30-64591.85)/(64591.85-64316.00)) < 1e-9

# 6) korunan iddiaların yeniden teyidi
assert max(r["v"] for r in m15) == DISP["v"]          # displacement hacmi oturum maksimumu
assert DISP["c"] - DISP["o"] == D("484.60")           # gövde
print(json.dumps(rep, indent=1, ensure_ascii=False))
