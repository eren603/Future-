#!/usr/bin/env python3
"""C0-VETO v2.6 deterministic calculation engine (manual deep-scan path).

scripts_available=false for the contract's skill zip (zip not uploaded);
this is an ad-hoc, fully shown calculation script — NOT the skill's scripts.

Input: user-pasted Binance-format 15M and 4H kline rows (transcribed below).
All price fields kept as Decimal for exact arithmetic where required;
float64 used only for tanh/log with explicit note.
"""
from decimal import Decimal as D
import math, json, hashlib

# ---- transcribed 15M klines: [openTime, O, H, L, C, baseVol] (closed bars only) ----
K15 = [
 (1784468700000,"64393.70","64497.90","64383.90","64453.00","676.453"),
 (1784469600000,"64453.00","64534.70","64446.20","64517.60","592.074"),
 (1784470500000,"64517.50","64533.20","64389.00","64437.00","544.861"),
 (1784471400000,"64437.10","64523.90","64421.40","64500.00","407.982"),
 (1784472300000,"64500.00","64633.00","64495.80","64561.10","910.925"),
 (1784473200000,"64561.00","64594.70","64500.00","64551.00","421.676"),
 (1784474100000,"64550.90","64569.80","64468.00","64480.00","507.840"),
 (1784475000000,"64480.10","64559.40","64466.60","64536.10","405.241"),
 (1784475900000,"64536.00","64560.00","64508.20","64545.20","281.622"),
 (1784476800000,"64545.30","64624.80","64474.20","64523.10","521.519"),
 (1784477700000,"64523.10","64603.10","64483.30","64582.50","396.596"),
 (1784478600000,"64582.60","64585.80","64498.70","64577.60","307.957"),
 (1784479500000,"64577.60","64585.00","64490.30","64510.70","244.137"),
 (1784480400000,"64510.70","64671.00","64365.70","64670.90","1891.448"),
 (1784481300000,"64671.00","64733.00","64599.90","64617.10","1083.016"),
 (1784482200000,"64617.20","64700.20","64572.10","64592.40","457.807"),
 (1784483100000,"64592.50","64592.50","64505.70","64520.00","524.863"),
 (1784484000000,"64520.00","64529.10","64262.90","64447.90","1784.912"),
 (1784484900000,"64447.90","64466.50","64366.00","64369.30","721.357"),
 (1784485800000,"64369.20","64420.00","64318.00","64400.00","405.915"),
 (1784486700000,"64400.10","64420.00","64336.50","64399.80","530.125"),
 (1784487600000,"64399.80","64440.00","64319.50","64428.70","411.481"),
 (1784488500000,"64428.70","64442.20","64392.00","64415.30","154.987"),
 (1784489400000,"64415.40","64436.80","64382.00","64391.30","167.590"),
 (1784490300000,"64391.20","64440.20","64359.50","64438.10","351.112"),
 (1784491200000,"64438.10","64534.30","64438.00","64480.30","523.701"),
 (1784492100000,"64480.20","64502.40","64443.30","64462.90","155.685"),
 (1784493000000,"64463.00","64510.60","64451.00","64475.50","144.900"),
 (1784493900000,"64475.50","64516.00","64446.00","64515.90","235.030"),
 (1784494800000,"64516.00","64539.00","64462.80","64511.00","293.995"),
 (1784495700000,"64510.90","64514.80","64430.00","64449.90","155.121"),
 (1784496600000,"64450.00","64450.00","64320.00","64324.10","541.757"),
 (1784497500000,"64324.10","64409.00","64305.00","64393.70","686.146"),
 (1784498400000,"64393.60","64660.00","64319.30","64633.50","2523.460"),
 (1784499300000,"64633.60","64874.90","64633.50","64726.50","2810.151"),
 (1784500200000,"64726.50","64790.00","64653.40","64777.30","787.914"),
 (1784501100000,"64777.20","64780.00","64635.00","64642.70","622.469"),
 (1784502000000,"64642.80","64685.90","64534.90","64669.60","863.774"),
 (1784502900000,"64669.70","64681.50","64606.00","64642.00","407.607"),
 (1784503800000,"64642.10","64743.70","64610.20","64720.00","463.562"),
 (1784504700000,"64720.00","64748.10","64625.60","64694.70","319.934"),
 (1784505600000,"64694.80","65039.80","64534.60","64987.50","4134.612"),
 (1784506500000,"64987.40","65084.60","64769.10","64843.80","2308.752"),
 (1784507400000,"64843.80","64911.80","64756.50","64785.50","1139.516"),
 (1784508300000,"64785.60","64785.60","64380.00","64526.00","2314.587"),
 (1784509200000,"64526.00","65011.00","64473.00","64775.20","2449.733"),
 (1784510100000,"64775.20","64923.60","64657.00","64820.70","1057.405"),
 (1784511000000,"64820.70","64903.80","64668.80","64736.70","682.909"),
 (1784511900000,"64736.80","64754.70","64470.00","64594.70","1288.686"),
 (1784512800000,"64594.70","64920.00","64588.80","64794.50","1700.473"),
 (1784513700000,"64794.60","64804.60","64551.60","64637.30","1243.541"),
 (1784514600000,"64637.30","64864.20","64626.10","64801.70","848.079"),
 (1784515500000,"64801.80","64940.00","64800.10","64800.10","970.225"),
 (1784516400000,"64800.10","64860.10","64742.90","64812.90","452.124"),
 (1784517300000,"64812.90","64860.10","64610.20","64650.40","819.000"),
 (1784518200000,"64650.30","64876.40","64628.50","64876.40","674.710"),
 (1784519100000,"64876.30","64887.00","64752.80","64839.40","632.794"),
 (1784520000000,"64839.30","64843.40","64670.00","64674.30","566.365"),
 (1784520900000,"64674.40","64757.00","64602.00","64733.60","737.777"),  # C0 04:15-04:30
]
K15_PARTIAL = (1784521800000,"64733.60","64735.90","64697.50","64697.50","17.541")  # OPEN bar, EXCLUDED

# ---- transcribed 4H klines (closed bars only) ----
K4H = [
 (1784217600000,"64677.70","64687.60","63958.00","64241.60","18183.263"),
 (1784232000000,"64241.70","64249.90","63712.60","63801.00","12576.221"),
 (1784246400000,"63801.10","64041.60","63358.00","63538.10","23701.404"),
 (1784260800000,"63538.00","63560.00","62655.00","62792.90","36223.336"),
 (1784275200000,"62792.80","63337.40","62611.00","63273.20","20640.395"),
 (1784289600000,"63273.10","63496.00","62505.10","63432.40","42264.100"),
 (1784304000000,"63432.40","64356.70","63272.40","64121.40","34857.577"),
 (1784318400000,"64121.40","64188.20","63860.00","63909.90","8166.001"),
 (1784332800000,"63909.90","64014.90","63859.60","63989.50","5338.834"),
 (1784347200000,"63989.50","64000.00","63894.30","63980.10","4328.088"),
 (1784361600000,"63980.00","64073.20","63912.00","64033.30","4092.098"),
 (1784376000000,"64033.20","64237.70","63925.20","64090.00","9810.671"),
 (1784390400000,"64090.00","64666.00","64054.50","64526.30","15262.257"),
 (1784404800000,"64526.40","64837.40","64467.20","64806.70","10394.790"),
 (1784419200000,"64806.70","64948.80","64594.60","64686.80","13515.109"),
 (1784433600000,"64686.80","64789.80","64580.40","64692.20","5846.715"),
 (1784448000000,"64692.10","64723.50","64415.00","64445.70","10691.700"),
 (1784462400000,"64445.70","64633.00","64259.50","64545.20","11251.478"),
 (1784476800000,"64545.30","64733.00","64262.90","64438.10","9954.822"),
 (1784491200000,"64438.10","64874.90","64305.00","64694.70","11535.206"),
 (1784505600000,"64694.80","65084.60","64380.00","64839.40","22717.146"),  # 00:00-04:00, last eligible
]
K4H_PARTIAL = (1784520000000,"64839.30","64843.40","64602.00","64691.00","1342.141")  # OPEN, EXCLUDED

def dd(x): return D(x)

# ================= STEP 3: PROFILE =================
profile = {}
for name, rows, step in (("K15", K15, 900000), ("K4H", K4H, 14400000)):
    times = [r[0] for r in rows]
    gaps = [ (t2-t1) for t1,t2 in zip(times, times[1:]) ]
    ohlc_ok = all( dd(r[2]) >= max(dd(r[1]),dd(r[4])) and dd(r[3]) <= min(dd(r[1]),dd(r[4])) for r in rows )
    dupes = len(times) != len(set(times))
    profile[name] = {
        "rows": len(rows),
        "time_monotonic": times == sorted(times),
        "grid_uniform": all(g == step for g in gaps),
        "duplicates": dupes,
        "ohlc_sanity_H>=max(O,C)_L<=min(O,C)": ohlc_ok,
        "first_open_ms": times[0], "last_open_ms": times[-1],
    }

# open(t) vs close(t-1) continuity (data-quality signal, Binance bars can gap slightly)
cont15 = [abs(dd(K15[i][1]) - dd(K15[i-1][4])) for i in range(1,len(K15))]
profile["K15"]["open_prevclose_max_abs_diff"] = str(max(cont15))
cont4 = [abs(dd(K4H[i][1]) - dd(K4H[i-1][4])) for i in range(1,len(K4H))]
profile["K4H"]["open_prevclose_max_abs_diff"] = str(max(cont4))

# ================= SECOND PATH: 15m -> 4h aggregation reconciliation =================
# 4H bars fully covered by K15 range: 16:00-20:00 (1784462400000), 20:00-00:00, 00:00-04:00
second_path = []
for start in (1784476800000, 1784491200000, 1784505600000):
    sub = [r for r in K15 if start <= r[0] < start + 14400000]
    agg = {
        "open": sub[0][1],
        "high": str(max(dd(r[2]) for r in sub)),
        "low":  str(min(dd(r[3]) for r in sub)),
        "close": sub[-1][4],
        "n_15m": len(sub),
    }
    ref = next(r for r in K4H if r[0] == start)
    match = (dd(agg["open"])==dd(ref[1]) and dd(agg["high"])==dd(ref[2])
             and dd(agg["low"])==dd(ref[3]) and dd(agg["close"])==dd(ref[4]) and len(sub)==16)
    second_path.append({"4h_open_ms": start, "aggregated_from_15m": agg,
                        "provider_4h_row": [str(x) for x in ref[1:5]], "exact_match": match})

# partial 4H cross-check (two separate captures; equality NOT required)
sub = [r for r in K15 if r[0] >= 1784520000000] + [K15_PARTIAL]
second_path.append({"4h_open_ms": 1784520000000, "note": "OPEN bar, two separate captures",
    "aggregated_high": str(max(dd(r[2]) for r in sub)), "provider_high": K4H_PARTIAL[2],
    "aggregated_low": str(min(dd(r[3]) for r in sub)), "provider_low": K4H_PARTIAL[3]})

# ================= RULE_SIGNAL_V1 (C0 = last closed 15M bar) =================
C0 = K15[-1]
c0_open_ms = C0[0]; c0_close_ms = C0[0] + 900000
O0,H0,L0,Cc0 = dd(C0[1]),dd(C0[2]),dd(C0[3]),dd(C0[4])
P0 = Cc0

# ATR0 = mean of last 14 completed 15M TR including C0  (needs prev close -> bars -15..-1)
trs = []
for i in range(len(K15)-14, len(K15)):
    H,L = dd(K15[i][2]), dd(K15[i][3])
    Cprev = dd(K15[i-1][4])
    tr = max(H-L, abs(H-Cprev), abs(L-Cprev))
    trs.append(tr)
ATR0 = sum(trs)/D(14)

# 4H trend inputs — eligible closes: all K4H rows close <= C0 close time
assert K4H[-1][0] + 14400000 <= c0_close_ms
closes4 = [dd(r[4]) for r in K4H]
ma5_4h  = sum(closes4[-5:])/D(5)
ma20_4h = sum(closes4[-20:])/D(20)
gap4h = (ma5_4h - ma20_4h)/ma20_4h
rets4 = [abs(math.log(float(closes4[i])/float(closes4[i-1]))) for i in range(1,len(closes4))]
n_ret = len(rets4)          # need >= 20 (uses last 20)
mean_abs_ret4 = sum(rets4[-20:])/20.0
thr4h = max(0.0008, 0.5*mean_abs_ret4)

C_5 = dd(K15[-6][4])   # close 5 bars before C0
C_4 = dd(K15[-5][4])   # close 4 bars before C0
mb = max(-1.0, min(1.0, math.tanh(float((P0 - C_5)/ATR0)/2.0)))

if float(gap4h) > thr4h: trend_dir = "UP"
elif float(gap4h) < -thr4h: trend_dir = "DOWN"
elif mb > 0.30: trend_dir = "UP"
elif mb < -0.30: trend_dir = "DOWN"
else: trend_dir = "NEUTRAL"

# prl/prh over previous 40 completed bars excluding C0
prev40 = K15[-41:-1]
assert len(prev40) == 40
prl = min(dd(r[3]) for r in prev40)
prh = max(dd(r[2]) for r in prev40)

range0 = H0 - L0
lower_wick = min(O0,Cc0) - L0
upper_wick = H0 - max(O0,Cc0)

breakout_up   = Cc0 > prh
breakout_down = Cc0 < prl
reject_low  = (L0 <= prl + D("0.25")*ATR0) and (((lower_wick > D("0.45")*range0) and (Cc0 > L0 + D("0.50")*range0)) or (Cc0 > C_4))
reject_high = (H0 >= prh - D("0.25")*ATR0) and (((upper_wick > D("0.45")*range0) and (Cc0 < H0 - D("0.50")*range0)) or (Cc0 < C_4))
sfp_up   = (L0 <= prl) and (Cc0 > prl + D("0.15")*ATR0)
sfp_down = (H0 >= prh) and (Cc0 < prh - D("0.15")*ATR0)

up_trigger = breakout_up or reject_low or sfp_up
down_trigger = breakout_down or reject_high or sfp_down
if up_trigger and down_trigger: trigger_dir = "AMBIGUOUS"
elif up_trigger: trigger_dir = "UP"
elif down_trigger: trigger_dir = "DOWN"
else: trigger_dir = "NEUTRAL"

# decision policy
if trigger_dir in ("AMBIGUOUS","UNKNOWN"):
    direction, state, grade = "UNKNOWN","NO_CALL",None
elif trigger_dir in ("UP","DOWN") and trend_dir in ("UP","DOWN") and trigger_dir != trend_dir:
    direction, state, grade = "NEUTRAL","ABSTAIN_CONFLICT",None
elif trigger_dir in ("UP","DOWN") and trend_dir == trigger_dir:
    direction, state, grade = trigger_dir,"UNVALIDATED_RULE_CALL","A"
elif trigger_dir in ("UP","DOWN") and trend_dir == "NEUTRAL":
    direction, state, grade = trigger_dir,"UNVALIDATED_RULE_CALL","B"
elif trigger_dir == "NEUTRAL" and trend_dir in ("UP","DOWN"):
    direction, state, grade = trend_dir,"UNVALIDATED_RULE_CALL","B"
else:
    direction, state, grade = "NEUTRAL","ABSTAIN_NO_DIRECTIONAL_EVIDENCE",None
# observer saw ~30-45s of post-C0 bar (pasted open candle) -> nonblind downgrade
state_final = "RETROSPECTIVE_NONBLIND_DIAGNOSTIC" if state == "UNVALIDATED_RULE_CALL" else state
side = {"UP":"LONG","DOWN":"SHORT"}.get(direction)

# ATR fallback plan (tickSize unavailable -> raw values only)
plan = None
if direction in ("UP","DOWN") and grade in ("A","B") and ATR0 > 0:
    k = D("1.2")*ATR0
    if direction == "UP":
        plan = {"side":"LONG","entry_reference":str(P0),"target_reference":str(P0+k),"stop_reference":str(P0-k),
                "pusu_zone":[str(P0-D("0.25")*ATR0), str(P0-D("0.15")*ATR0)]}
    else:
        plan = {"side":"SHORT","entry_reference":str(P0),"target_reference":str(P0-k),"stop_reference":str(P0+k),
                "pusu_zone":[str(P0+D("0.15")*ATR0), str(P0+D("0.25")*ATR0)]}

out = {
 "profile": profile,
 "second_path_15m_to_4h": second_path,
 "c0": {"open_ms": c0_open_ms, "close_ms": c0_close_ms,
        "open_utc": "2026-07-20T04:15:00Z", "close_utc": "2026-07-20T04:30:00Z",
        "OHLC": [str(O0),str(H0),str(L0),str(Cc0)]},
 "atr0": {"value": str(ATR0), "n": 14, "tr_values": [str(t) for t in trs]},
 "trend4h": {"ma5": str(ma5_4h), "ma20": str(ma20_4h), "gap4h": str(gap4h),
             "n_4h_closes": len(closes4), "n_4h_returns": n_ret,
             "mean_abs_ret4_last20": mean_abs_ret4, "thr4h": thr4h,
             "C_5": str(C_5), "C_4": str(C_4), "mb": mb, "trend_dir": trend_dir},
 "levels": {"prl": str(prl), "prh": str(prh), "n_prev_bars": len(prev40),
            "range0": str(range0), "lower_wick": str(lower_wick), "upper_wick": str(upper_wick)},
 "predicates": {"breakout_up": breakout_up, "breakout_down": breakout_down,
                "reject_low": reject_low, "reject_high": reject_high,
                "sfp_up": sfp_up, "sfp_down": sfp_down, "trigger_dir": trigger_dir},
 "decision": {"direction": direction, "side": side, "support_grade": grade,
              "policy_state_if_blind": state, "state_final": state_final,
              "was_live_forecast": False},
 "atr_shadow_plan_v1": plan,
}
print(json.dumps(out, indent=1))
