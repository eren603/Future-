# C0-VETO v2.7-PRAGMATIK — Beceri-1 (deep-scan) + Beceri-3 (mekanik) + Beceri-2 (SMC)
# Birincil yol: Decimal. İkinci yol: float64 bağımsız yeniden hesap + 15M->4H mutabakat.
import json, hashlib
from decimal import Decimal as D

SCRATCH = "/tmp/claude-0/-home-user-Future-/dd8980b7-319d-5ec4-b020-599136e15744/scratchpad"
CAPTURE_UTC_MS = 1784548920000  # ekran görüntüleri 15:01-15:02 UTC+3 => ~12:02 UTC 2026-07-20 (gözlemci zamanı)

def load(name):
    with open(f"{SCRATCH}/{name}") as f:
        raw = json.load(f)
    rows = []
    for r in raw:
        rows.append({
            "ot": int(r[0]), "o": D(r[1]), "h": D(r[2]), "l": D(r[3]), "c": D(r[4]),
            "v": D(r[5]), "ct": int(r[6]), "q": D(r[7]), "n": int(r[8]),
            "tbb": D(r[9]), "tbq": D(r[10]),
        })
    return rows

def profile(rows, step_ms, name):
    rep = {"name": name, "rows": len(rows), "issues": []}
    ts = [r["ot"] for r in rows]
    if len(set(ts)) != len(ts):
        rep["issues"].append("DUPLICATE_TS")
    for a, b in zip(rows, rows[1:]):
        if b["ot"] - a["ot"] != step_ms:
            rep["issues"].append(f"GRID_GAP:{a['ot']}->{b['ot']}")
    for r in rows:
        if not (r["h"] >= max(r["o"], r["c"]) and r["l"] <= min(r["o"], r["c"]) and r["h"] >= r["l"]):
            rep["issues"].append(f"OHLC_SANITY:{r['ot']}")
        if r["ct"] - r["ot"] != step_ms - 1:
            rep["issues"].append(f"CLOSETIME:{r['ot']}")
    # açık bar: kapanış zamanı gözlemci zamanından sonra ise bar açık
    rep["open_bars"] = [r["ot"] for r in rows if r["ct"] >= CAPTURE_UTC_MS]
    rep["first"], rep["last"] = ts[0], ts[-1]
    return rep

m15 = load("klines_15m.json")
h4 = load("klines_4h.json")
p15 = profile(m15, 900_000, "15M")
p4 = profile(h4, 14_400_000, "4H")

# açık barları dışla
m15c = [r for r in m15 if r["ct"] < CAPTURE_UTC_MS]
h4c = [r for r in h4 if r["ct"] < CAPTURE_UTC_MS]

# ---- İKİNCİ YOL 1: 15M -> 4H agregasyon mutabakatı (tam kapsanan 4H barları) ----
recon = []
for H in h4c:
    seg = [r for r in m15c if H["ot"] <= r["ot"] < H["ot"] + 14_400_000]
    if len(seg) == 16:
        agg = {
            "o": seg[0]["o"], "c": seg[-1]["c"],
            "h": max(r["h"] for r in seg), "l": min(r["l"] for r in seg),
            "v": sum(r["v"] for r in seg), "n": sum(r["n"] for r in seg),
        }
        ok = (agg["o"] == H["o"] and agg["c"] == H["c"] and agg["h"] == H["h"]
              and agg["l"] == H["l"] and agg["v"] == H["v"] and agg["n"] == H["n"])
        recon.append({"ot": H["ot"], "match": ok,
                      "diff": {k: str(agg[k] - H[k]) for k in ("o", "h", "l", "c", "v")} if not ok else None})

C0 = m15c[-1]

# ---- BECERİ-3: MEKANİK MOTOR ----
def tr_list(rows):
    out = []
    for prev, cur in zip(rows, rows[1:]):
        out.append(max(cur["h"] - cur["l"], abs(cur["h"] - prev["c"]), abs(cur["l"] - prev["c"])))
    return out

trs15 = tr_list(m15c)
ATR0 = sum(trs15[-14:]) / D(14)

closes4 = [r["c"] for r in h4c]
MA5 = sum(closes4[-5:]) / D(5)
MA20 = sum(closes4[-20:]) / D(20)
trs4 = tr_list(h4c)
ATR4 = sum(trs4[-14:]) / D(14)
# adaptif eşik (VARSAYIM: v2.6 tam formülü bu pencerede yok; eşik = 0.10 * ATR14(4H))
th = ATR4 * D("0.10")
diff = MA5 - MA20
trend_dir = "UP" if diff > th else ("DOWN" if diff < -th else "NEUTRAL")

# 40-bar prl/prh (C0 hariç önceki 40 kapalı bar)
win = m15c[-41:-1]
prh = max(r["h"] for r in win)
prl = min(r["l"] for r in win)
close_loc = (C0["c"] - C0["l"]) / (C0["h"] - C0["l"])
if C0["c"] > prh:
    trigger_dir, trigger = "UP", "BREAKOUT_UP(C0 close > prh)"
elif C0["c"] < prl:
    trigger_dir, trigger = "DOWN", "BREAKOUT_DOWN"
elif C0["h"] > prh and C0["c"] < prh:
    trigger_dir, trigger = "DOWN", "SFP_UP(prh üstüne fitil, altında kapanış)"
elif C0["l"] < prl and C0["c"] > prl:
    trigger_dir, trigger = "UP", "SFP_DOWN"
else:
    trigger_dir, trigger = "NONE", "NONE"
if trigger_dir == trend_dir and trend_dir != "NEUTRAL":
    yon_M, grade_M = trend_dir, "STRONG"
elif trigger_dir == "NONE" and trend_dir != "NEUTRAL":
    yon_M, grade_M = trend_dir, "WEAK(trend-only)"
elif trend_dir == "NEUTRAL" and trigger_dir != "NONE":
    yon_M, grade_M = trigger_dir, "WEAK(trigger-only)"
elif trigger_dir != trend_dir:
    yon_M, grade_M = "NEUTRAL", "CONFLICT(trend vs trigger)"
else:
    yon_M, grade_M = "NEUTRAL", "NONE"
env = {"lo": C0["c"] - D("1.2") * ATR0, "hi": C0["c"] + D("1.2") * ATR0}

# ---- BECERİ-2: SMC ----
def swings(rows, k=2):
    sh, sl = [], []
    for i in range(k, len(rows) - k):
        w = rows[i - k:i + k + 1]
        if rows[i]["h"] == max(r["h"] for r in w) and sum(1 for r in w if r["h"] == rows[i]["h"]) == 1:
            sh.append((i, rows[i]["ot"], rows[i]["h"]))
        if rows[i]["l"] == min(r["l"] for r in w) and sum(1 for r in w if r["l"] == rows[i]["l"]) == 1:
            sl.append((i, rows[i]["ot"], rows[i]["l"]))
    return sh, sl

sh15, sl15 = swings(m15c)
sh4, sl4 = swings(h4c)

def fvgs(rows):
    out = []
    for i in range(1, len(rows) - 1):
        if rows[i + 1]["l"] > rows[i - 1]["h"]:  # boğa FVG
            gap = {"type": "BULL", "ot": rows[i]["ot"], "top": rows[i + 1]["l"], "bot": rows[i - 1]["h"]}
        elif rows[i + 1]["h"] < rows[i - 1]["l"]:  # ayı FVG
            gap = {"type": "BEAR", "ot": rows[i]["ot"], "top": rows[i - 1]["l"], "bot": rows[i + 1]["h"]}
        else:
            continue
        # doluluk: sonraki barlar boşluğun tamamından geçti mi
        fill = "OPEN"
        extreme = None
        for r in rows[i + 2:]:
            if gap["type"] == "BULL":
                if r["l"] <= gap["bot"]:
                    fill = "FULL_FILL"; break
                if r["l"] < gap["top"]:
                    extreme = min(extreme, r["l"]) if extreme is not None else r["l"]
            else:
                if r["h"] >= gap["top"]:
                    fill = "FULL_FILL"; break
                if r["h"] > gap["bot"]:
                    extreme = max(extreme, r["h"]) if extreme is not None else r["h"]
        if fill == "OPEN" and extreme is not None:
            fill = f"PARTIAL_to_{extreme}"
        gap["fill"] = fill
        out.append(gap)
    return out

fvg15 = fvgs(m15c)

def sweeps(rows, sl_list, sh_list):
    ev = []
    for i in range(len(rows)):
        r = rows[i]
        prior_sl = [s for s in sl_list if s[0] < i - 0]  # teyitli swing (fraktal k=2 -> i+2'de teyit)
        prior_sl = [s for s in prior_sl if s[0] + 2 < i]
        if prior_sl:
            lvl = prior_sl[-1][2]
            if r["l"] < lvl and r["c"] > lvl:
                cl = (r["c"] - r["l"]) / (r["h"] - r["l"]) if r["h"] != r["l"] else D(0)
                ev.append({"side": "SSL_SWEEP", "ot": r["ot"], "level": str(lvl),
                           "close_loc": float(cl), "strong": cl >= D("0.70")})
        prior_sh = [s for s in sh_list if s[0] + 2 < i]
        if prior_sh:
            lvl = prior_sh[-1][2]
            if r["h"] > lvl and r["c"] < lvl:
                cl = (r["h"] - r["c"]) / (r["h"] - r["l"]) if r["h"] != r["l"] else D(0)
                ev.append({"side": "BSL_SWEEP", "ot": r["ot"], "level": str(lvl),
                           "close_loc": float(cl), "strong": cl >= D("0.70")})
    return ev

sweep_ev = sweeps(m15c, sl15, sh15)

# BOS: bar kapanışı en son teyitli swing high üstünde / low altında
last_bos = None
for i in range(len(m15c)):
    r = m15c[i]
    psh = [s for s in sh15 if s[0] + 2 < i]
    psl = [s for s in sl15 if s[0] + 2 < i]
    if psh and r["c"] > psh[-1][2]:
        last_bos = {"dir": "UP", "ot": r["ot"], "level": str(psh[-1][2])}
    if psl and r["c"] < psl[-1][2]:
        last_bos = {"dir": "DOWN", "ot": r["ot"], "level": str(psl[-1][2])}
yon_Y = last_bos["dir"] if last_bos else "UNKNOWN"

# likidite havuzları: süpürülmemiş swing high/low (C0 kapanışına göre)
def unswept_high(sh_list, rows):
    out = []
    for idx, ot, lvl in sh_list:
        if not any(r["h"] > lvl for r in rows[idx + 1:]):
            out.append((ot, lvl))
    return out

def unswept_low(sl_list, rows):
    out = []
    for idx, ot, lvl in sl_list:
        if not any(r["l"] < lvl for r in rows[idx + 1:]):
            out.append((ot, lvl))
    return out

bsl15 = unswept_high(sh15, m15c); ssl15 = unswept_low(sl15, m15c)
bsl4 = unswept_high(sh4, h4c); ssl4 = unswept_low(sl4, h4c)
pools_up = sorted({str(l) for _, l in bsl15 + bsl4 if l > C0["c"]}, key=D)
pools_dn = sorted({str(l) for _, l in ssl15 + ssl4 if l < C0["c"]}, key=D, reverse=True)

# son swing low (stop adayı) — C0 öncesi teyitli son 15M fraktal dip
last_sl = [s for s in sl15 if s[0] + 2 <= len(m15c) - 1]
stop_ref = last_sl[-1] if last_sl else None

out = {
    "profil": {"15M": p15, "4H": p4,
               "closed_15m": len(m15c), "closed_4h": len(h4c),
               "recon_4h": recon},
    "C0": {k: str(C0[k]) for k in ("ot", "o", "h", "l", "c", "v")},
    "mekanik": {"ATR0": str(ATR0), "ATR4H": str(ATR4), "MA5_4H": str(MA5), "MA20_4H": str(MA20),
                "MA_diff": str(diff), "esik(0.10xATR4H)": str(th), "trend_dir": trend_dir,
                "prh40": str(prh), "prl40": str(prl), "trigger": trigger, "trigger_dir": trigger_dir,
                "yon_M": yon_M, "grade_M": grade_M, "C0_close_loc": float(close_loc),
                "atr_zarf": {"lo": str(env["lo"]), "hi": str(env["hi"])}},
    "smc": {"yon_Y": yon_Y, "last_bos": last_bos,
            "sweep_events": sweep_ev[-6:],
            "fvg15_son5": [{**g, "top": str(g["top"]), "bot": str(g["bot"])} for g in fvg15[-5:]],
            "sh15_son5": [(t, str(l)) for _, t, l in sh15[-5:]],
            "sl15_son5": [(t, str(l)) for _, t, l in sl15[-5:]],
            "pools_up": pools_up[:4], "pools_dn": pools_dn[:4],
            "stop_ref_swing_low": (stop_ref[1], str(stop_ref[2])) if stop_ref else None},
}
print(json.dumps(out, indent=1, ensure_ascii=False, default=str))

# ---- İKİNCİ YOL 2: float64 bağımsız yeniden hesap ----
import math
f = [[float(x["o"]), float(x["h"]), float(x["l"]), float(x["c"])] for x in m15c]
trsf = [max(f[i][1]-f[i][2], abs(f[i][1]-f[i-1][3]), abs(f[i][2]-f[i-1][3])) for i in range(1, len(f))]
atr0f = sum(trsf[-14:]) / 14
c4 = [float(x["c"]) for x in h4c]
ma5f, ma20f = sum(c4[-5:]) / 5, sum(c4[-20:]) / 20
assert abs(atr0f - float(ATR0)) < 1e-6, "ATR0 mutabakatsiz"
assert abs(ma5f - float(MA5)) < 1e-6 and abs(ma20f - float(MA20)) < 1e-6, "MA mutabakatsiz"
print("IKINCI_YOL: ATR0/MA5/MA20 float64 mutabakati OK ->",
      round(atr0f, 4), round(ma5f, 2), round(ma20f, 2))
