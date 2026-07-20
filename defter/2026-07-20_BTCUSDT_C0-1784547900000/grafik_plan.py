# C0-VETO v2.7 — PLAN (R hesaplari, Decimal + float64 ikinci yol) ve CIZIM (yalniz kapali bar)
import json, hashlib
from decimal import Decimal as D
from datetime import datetime, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

SCRATCH = "/tmp/claude-0/-home-user-Future-/dd8980b7-319d-5ec4-b020-599136e15744/scratchpad"
OUT = "/home/user/Future-/defter/2026-07-20_BTCUSDT_C0-1784547900000"
import os; os.makedirs(OUT, exist_ok=True)
CAPTURE = 1784548920000

def load(name):
    with open(f"{SCRATCH}/{name}") as f:
        raw = json.load(f)
    return [{"ot": int(r[0]), "o": D(r[1]), "h": D(r[2]), "l": D(r[3]), "c": D(r[4]), "ct": int(r[6])} for r in raw]

m15 = [r for r in load("klines_15m.json") if r["ct"] < CAPTURE]
h4 = [r for r in load("klines_4h.json") if r["ct"] < CAPTURE]
C0 = m15[-1]

# --- PLAN sabitleri (analiz.py ciktisindan, Decimal) ---
ATR0 = D("180.7642857142857142857142857")
ENV_LO, ENV_HI = C0["c"] - D("1.2") * ATR0, C0["c"] + D("1.2") * ATR0
PRH40, PRL40 = D("64940.00"), D("63736.10")
FVG_TOP, FVG_BOT = D("64807.10"), D("64376.60")
CE = (FVG_TOP + FVG_BOT) / 2
DOL1 = D("65084.60")
T2_ATR = ENV_HI  # yapisal DOL2 veri icinde yok -> ATR fallback
STOP = D("64316.00")   # displacement origin (11:30 dibi); derin alternatif 64137.00
STOP_DEEP = D("64137.00")
MKT_IN = D("65048.30")  # teyit esigi (nominal; gercek kapanis >= bu olur)
PUSU_IN = CE            # nominal pusu girisi = FVG CE'si

def r_mult(entry, stop, tgt):
    return (tgt - entry) / (entry - stop)

plan = {
    "market": {"entry": str(MKT_IN), "stop": str(STOP),
               "R_T1": str(r_mult(MKT_IN, STOP, DOL1)), "R_T2": str(r_mult(MKT_IN, STOP, T2_ATR))},
    "pusu_CE": {"entry": str(CE), "stop": str(STOP),
                "R_T1": str(r_mult(CE, STOP, DOL1)), "R_T2": str(r_mult(CE, STOP, T2_ATR))},
    "pusu_fvg_ust": {"entry": str(FVG_TOP), "stop": str(STOP),
                     "R_T1": str(r_mult(FVG_TOP, STOP, DOL1)), "R_T2": str(r_mult(FVG_TOP, STOP, T2_ATR))},
    "T1": str(DOL1), "T2_ATR_FALLBACK": str(T2_ATR), "CE": str(CE), "stop_deep": str(STOP_DEEP),
}
# ikinci yol float64
for k, e in (("market", 65048.30), ("pusu_CE", float(CE)), ("pusu_fvg_ust", 64807.10)):
    for tk, t in (("R_T1", 65084.60), ("R_T2", float(T2_ATR))):
        f = (t - e) / (e - 64316.00)
        assert abs(f - float(D(plan[k][tk]))) < 1e-9
print("IKINCI_YOL R hesaplari OK")
print(json.dumps(plan, indent=1))

def ts(ms): return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

def candles(ax, rows, wsec):
    for r in rows:
        x = ts(r["ot"])
        up = r["c"] >= r["o"]
        col = "#1a9850" if up else "#d73027"
        ax.plot([x, x], [float(r["l"]), float(r["h"])], color=col, lw=0.7, zorder=2)
        ax.add_patch(Rectangle((matplotlib.dates.date2num(x) - wsec / 2 / 86400, float(min(r["o"], r["c"]))),
                               wsec / 86400, float(abs(r["c"] - r["o"])) or 0.5,
                               facecolor=col, edgecolor=col, zorder=3))
    ax.xaxis_date()

# ---- GRAFIK 1: MEKANIK (15M + ATR zarfi + prh/prl) ----
fig, ax = plt.subplots(figsize=(14, 7), dpi=110)
candles(ax, m15, 600)
ax.axhline(float(PRH40), color="#4575b4", ls="--", lw=1, label=f"prh40 {PRH40}")
ax.axhline(float(PRL40), color="#4575b4", ls=":", lw=1, label=f"prl40 {PRL40}")
ax.axhspan(float(ENV_LO), float(ENV_HI), color="#fee090", alpha=0.35,
           label=f"ATR zarfi ±1.2×ATR0 [{ENV_LO:.1f} – {ENV_HI:.1f}]")
ax.axvline(ts(C0["ot"]), color="black", lw=0.8, ls="--", alpha=0.6)
ax.annotate("C0 11:45 UTC\nBREAKOUT_UP", xy=(ts(C0["ot"]), float(C0["h"])), xytext=(-90, 25),
            textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.set_title("BTCUSDT 15M (kapali barlar) — MEKANIK MOTOR: trend UP (4H MA5−MA20=+412.7), tetik BREAKOUT_UP, ATR0=180.76")
ax.legend(loc="lower right", fontsize=8); ax.grid(alpha=0.25)
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(f"{OUT}/grafik_mekanik_15M.png"); plt.close(fig)

# ---- GRAFIK 2: SMC HARITASI (15M + 4H iki panel) ----
fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 7), dpi=110, width_ratios=[3, 2])
candles(a1, m15, 600)
a1.add_patch(Rectangle((matplotlib.dates.date2num(ts(1784547000000)), float(FVG_BOT)),
                       (matplotlib.dates.date2num(ts(C0["ot"])) - matplotlib.dates.date2num(ts(1784547000000))) + 0.02,
                       float(FVG_TOP - FVG_BOT), facecolor="#91bfdb", alpha=0.4, zorder=1,
                       label=f"Acik boga FVG {FVG_BOT}–{FVG_TOP}"))
a1.axhline(float(DOL1), color="#d73027", lw=1.4, label=f"DOL1/T1 (BSL) {DOL1}")
a1.axhline(float(T2_ATR), color="#d73027", lw=1, ls="--", label=f"T2 ATR-fallback {T2_ATR:.1f}")
a1.axhline(float(CE), color="#4575b4", lw=1.2, ls="-.", label=f"PUSU giris (CE) {CE}")
a1.axhline(float(STOP), color="black", lw=1.2, ls=":", label=f"STOP referansi {STOP} (derin: {STOP_DEEP})")
a1.axhline(float(MKT_IN), color="#1a9850", lw=1.2, ls="--", label=f"MARKET teyit > {MKT_IN}")
a1.annotate("SSL sweep 63736.1\n(zayif geri alim 0.15)", xy=(ts(1784529000000), 63736.1),
            xytext=(-30, -38), textcoords="offset points", fontsize=8, arrowprops=dict(arrowstyle="->"))
a1.annotate("Displacement + BOS\n11:30", xy=(ts(1784547000000), 64915.4), xytext=(-110, 10),
            textcoords="offset points", fontsize=8, arrowprops=dict(arrowstyle="->"))
a1.set_title("15M SMC haritasi — yon_Y=UP (BOS>64393.2), AMD: birikim→SSL alimi→yukari displacement")
a1.legend(loc="lower left", fontsize=7); a1.grid(alpha=0.25)
candles(a2, h4, 8000)
a2.axhline(65084.6, color="#d73027", lw=1.4, label="BSL havuzu 65084.6")
for lvl, lab in ((62505.1, "4H SSL 62505.1"), (63736.1, "SSL 63736.1 (bu hafta dibi)")):
    a2.axhline(lvl, color="#74add1", lw=1, ls=":", label=lab)
a2.axhline(64638.60, color="#fdae61", lw=1, ls="--", label="4H MA5 64638.6")
a2.axhline(64225.93, color="#7b3294", lw=1, ls="--", label="4H MA20 64225.9")
a2.set_title("4H yapi — MA5>MA20 (UP); veri ustunde yapisal havuz yalniz 65084.6")
a2.legend(loc="lower right", fontsize=7); a2.grid(alpha=0.25)
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(f"{OUT}/grafik_smc_haritasi.png"); plt.close(fig)

for f in ("grafik_mekanik_15M.png", "grafik_smc_haritasi.png"):
    h = hashlib.sha256(open(f"{OUT}/{f}", "rb").read()).hexdigest()
    print("SHA256", f, h)
