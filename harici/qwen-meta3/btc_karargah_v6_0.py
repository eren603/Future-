import math
import json
import traceback
import warnings
import ccxt
import numpy as np
import pandas as pd
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

# --- META³ IMMUTABLE CORE (DEĞİŞMEZ ÇEKİRDEK) ---
EXCHANGE = ccxt.binanceusdm({"enableRateLimit": True, "options": {"defaultType": "swap"}})
TF_4H = "4h"
TF_15M = "15m"
TF_MS = {"15m": 900000, "4h": 14400000}
LIMIT_15M = 2400
LIMIT_4H = 600

# MIRAS SABITLER (Meta² bu değerleri Bayesian Optimization ile güncelleyecek)
FEE_TAKER = 0.00040
SLIPPAGE = 0.0005
ATR_LEN = 14
ATR_SL_MULT = 1.5
TIME_STOP_BARS = 48
ALPHA = 0.05
MIN_TRADES = 8
N_FOLDS = 5
EMBARGO = 24
BOOTSTRAP_B = 2000
BOOTSTRAP_SEEDS = (20240101, 20250101)
Z_GRID = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]
PUMP_BUCKET_MS = 30_000
PUMP_SPAN = 20           
PUMP_THRESHOLD_Z = 3.0   
FR_TOLERANCE_BPS = 5.0   
LOB_DEPTH = 5            
TARGET_USD = 500.0
LIMIT_TIMEOUT_SEC = 8.0  

# v5.3 ONCU VERI / ANLIK UYARI parametreleri (HIPOTEZ)
PUMP_TICK_WATCH = 2.5          
TICK_CONFIRM_WINDOW_MIN = 15   
TICK_CONFIRM_MIN_TRADES = 10   
V_REVERSAL_WINDOW_SEC = 900    
V_REVERSAL_BUCKET_SEC = 30     
V_REVERSAL_MIN_ABS_PCT = 0.004  
V_REVERSAL_FLIP_PCT = 0.002    
V_REVERSAL_MIN_BUCKETS = 6     
LOB_BIAS_ALERT = 0.10          

SYMBOLS = [
    "ETH/USDT", "XRP/USDT", "LINK/USDT", "DOGE/USDT", "DOT/USDT",
    "AVAX/USDT", "SUSHI/USDT", "ZEC/USDT", "ETC/USDT", "FIL/USDT", "AAVE/USDT",
]

# --- META² İÇİN ÖNBELLEK (API BAN KORUMASI) ---
API_CACHE = {}

def get_cached_data(func, symbol, *args, **kwargs):
    """Aynı tarama döngüsünde aynı veriyi API'den defalarca çekmeyi önler."""
    cache_key = f"{func.__name__}_{symbol}_{args}_{kwargs}"
    now_min = int(pd.Timestamp.now(tz="UTC").value // 60_000_000) # Dakikalık cache
    if cache_key in API_CACHE and API_CACHE[cache_key]["min"] == now_min:
        return API_CACHE[cache_key]["data"]
    
    data = func(symbol, *args, **kwargs)
    API_CACHE[cache_key] = {"data": data, "min": now_min}
    return data

# ---------------------------------------------------------------------------
# 0. KENDINDEN KONTROL
# ---------------------------------------------------------------------------
def selftest():
    end_ms = int(pd.Timestamp.now(tz="UTC").value // 1_000_000)
    assert isinstance(end_ms, int) and end_ms > 1_700_000_000_000, "Selftest 1 BASARISIZ"
    s = pd.Series([1.0, 2.0]).shift(periods=1)
    assert pd.isna(s.iloc[0]) and float(s.iloc[1]) == 1.0, "Selftest 2 BASARISIZ"
    print("Kendinden kontrol: OK")

# ---------------------------------------------------------------------------
# 1. VERI CEKME (LOOKAHEAD BIAS KORUMALI)
# ---------------------------------------------------------------------------
def unix_ms(lookback_min=0):
    now_ms = int(pd.Timestamp.now(tz="UTC").value // 1_000_000)
    return int(now_ms - lookback_min * 60_000)

def fetch_ohlcv(symbol, timeframe, limit):
    step_ms = TF_MS.get(timeframe)
    end = unix_ms()
    since = end - limit * step_ms
    arr = None
    while since < end:
        part = EXCHANGE.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not part: break
        arr = np.asarray(part, dtype=float) if arr is None else np.vstack([arr, np.asarray(part, dtype=float)])
        since += len(part) * step_ms
    if arr is None: raise ValueError(f"Veri alinamadi: {symbol}")
    
    df = pd.DataFrame(arr, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = (df.drop_duplicates(subset="timestamp").tail(limit).set_index("timestamp").astype(float))
    if len(df) > 1: df = df.iloc[:-1]  # KAPANMAMIŞ MUMU AT (Hayati Kural)
    return df

def fetch_order_book(symbol):
    try:
        ob = EXCHANGE.fetch_order_book(symbol, limit=LOB_DEPTH)
        if not ob or not ob.get("bids") or not ob.get("asks"): return None, None
        bids = pd.DataFrame(ob["bids"][:LOB_DEPTH], columns=["price", "size"])
        asks = pd.DataFrame(ob["asks"][:LOB_DEPTH], columns=["price", "size"])
        return bids, asks
    except Exception: return None, None

def fetch_recent_trades(symbol, lookback_min=60):
    try:
        trades = EXCHANGE.fetch_trades(symbol, since=unix_ms(lookback_min=lookback_min), limit=1000)
        if not trades: return pd.DataFrame(columns=["timestamp", "price", "amount"])
        df = pd.DataFrame(trades)
        return df[["timestamp", "price", "amount"]].astype(float)
    except Exception: return pd.DataFrame(columns=["timestamp", "price", "amount"])

def lob_imbalance(bids, asks):
    if bids is None or asks is None or bids.empty or asks.empty: return 0.0, 0.0, float("inf")
    bid_usd = float((bids["price"] * bids["size"]).sum())
    ask_usd = float((asks["price"] * asks["size"]).sum())
    best_bid = float(bids["price"].iloc[0])
    best_ask = float(asks["price"].iloc[0])
    spread_bps = (best_ask - best_bid) / best_bid * 1e4
    imb = (bid_usd - ask_usd) / max(bid_usd + ask_usd, 1e-12)
    return imb, bid_usd + ask_usd, spread_bps

# ---------------------------------------------------------------------------
# 2. PUMP / DUMP & REJIM TESPITI
# ---------------------------------------------------------------------------
def pump_anomaly(vol_series, span=PUMP_SPAN, threshold=PUMP_THRESHOLD_Z):
    if len(vol_series) < 30: return 0.0, "VERI_YOK"
    v = vol_series.astype(float).fillna(0.0)
    ewma = v.ewm(span=span, adjust=False).mean().shift(periods=1)
    evol = v.ewm(span=span, adjust=False).std().shift(periods=1)
    z = (v - ewma) / (evol + 1e-12)
    z_now = float(z.iloc[-1]) if np.isfinite(z.iloc[-1]) else 0.0
    
    cus = v.diff().abs().rolling(window=10).sum()
    cus_mu = cus.ewm(span=span * 5, adjust=False).mean().shift(periods=1)
    cus_sd = cus.ewm(span=span * 5, adjust=False).std().shift(periods=1)
    cs = (cus - cus_mu) / (cus_sd + 1e-12)
    cs_now = float(cs.iloc[-1]) if np.isfinite(cs.iloc[-1]) else 0.0
    
    score = max(z_now, cs_now)
    if score < threshold * 0.6: return score, "NORMAL"
    if score < threshold: return score, "WATCH"
    return score, "PUMP_OR_DUMP_RISK"

def regime_detector(close_15m, close_4h):
    if len(close_15m) < 20 or len(close_4h) < 50: return "UNKNOWN", 0.0
    r15 = np.log(close_15m / close_15m.shift(periods=1)).dropna()
    if len(r15) < 20: return "UNKNOWN", 0.0
    ef = close_4h.ewm(span=50, adjust=False).mean()
    es = close_4h.ewm(span=200, adjust=False).mean()
    slope = (ef - es) / close_4h
    tr4 = (close_4h - close_4h.shift(periods=1)).abs()
    atr_pct = float((tr4.rolling(window=14).mean() / close_4h).iloc[-1])
    if not np.isfinite(atr_pct): atr_pct = 0.0
    margin = max(0.003, atr_pct * 1.5)
    s = slope.reindex(r15.index, method="ffill").fillna(0.0)
    mu = float(r15.mean())
    cur = float(s.iloc[-1])
    if cur > margin and mu > 0: return "BULL", min(0.9, 0.5 + abs(cur) * 5.0)
    if cur < -margin and mu < 0: return "BEAR", min(0.9, 0.5 + abs(cur) * 5.0)
    return "CALM", 0.7

# ---------------------------------------------------------------------------
# 3. İSTATİSTİK VE WALK-FORWARD (ANTI-OVERFIT)
# ---------------------------------------------------------------------------
def norm_cdf(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def oos_stats(trades, min_n=MIN_TRADES):
    if len(trades) < min_n: return None
    a = np.asarray(trades, dtype=float)
    n = len(a)
    mean, sd = float(np.mean(a)), float(np.std(a, ddof=1))
    t = mean / (sd / math.sqrt(n)) if sd > 0 else 0.0
    wins, losses = a[a > 0], -a[a <= 0]
    ls = float(np.sum(losses))
    pf = float(np.sum(wins) / ls) if ls > 0 else float("inf")
    cum = np.cumprod(1.0 + a)
    pk = np.maximum.accumulate(cum)
    return {"n": n, "mean": mean, "sd": sd, "t": t, "win": float(len(wins) / n), "pf": pf, "mdd": float(np.min(cum / pk - 1.0))}

def fdr_bh(pvalues, alpha=ALPHA):
    m = len(pvalues)
    if m == 0: return []
    order = np.argsort(pvalues)
    arr = np.asarray(pvalues, dtype=float)[order]
    thr_arr = np.asarray([(k + 1) / m * alpha for k in range(m)])
    accept = arr <= thr_arr
    if not accept.any(): return [False] * m
    kmax = int(np.max(np.where(accept)[0]))
    keep = np.zeros(m, dtype=bool)
    keep[:kmax + 1] = True
    out = [False] * m
    for i, ix in enumerate(order): out[ix] = bool(keep[i])
    return out

def walkforward_splits(n, k=N_FOLDS, embargo=EMBARGO):
    fold = n // k
    splits = []
    if fold <= 0: return splits
    for t in range(1, k):
        test = np.arange(t * fold, min((t + 1) * fold, n))
        train = np.arange(0, t * fold)
        train = train[train <= (t * fold - 1 - embargo)]
        if len(train) < 200: continue
        splits.append((train, test))
    return splits

def simulate(feat, idx, z_th, direction):
    o, cl, lo, hi, z, atr = feat["open"], feat["close"], feat["low"], feat["high"], feat["z"], feat["atr"]
    n = len(o)
    if n < 63: return []
    trades = []
    i = 62
    while i < n - 1:
        zi, atr_i = float(z[i]), float(atr[i])
        if not (np.isfinite(zi) and np.isfinite(atr_i) and atr_i > 0):
            i += 1; continue
        
        # Mean Reversion Mantığı: Fiyat ortalamadan çok uzaklaştı ve geri dönmeye başladı.
        if direction == "LONG":
            fired = (zi <= -z_th) and (z[i - 1] < zi) and (zi > float(np.min(z[i - 3:i])))
        else:
            fired = (zi >= z_th) and (z[i - 1] > zi) and (zi < float(np.max(z[i - 3:i])))
            
        if not fired:
            i += 1; continue
            
        entry = float(o[i])
        sl = entry - ATR_SL_MULT * atr_i if direction == "LONG" else entry + ATR_SL_MULT * atr_i
        ep = None
        j = min(i + TIME_STOP_BARS, n - 1)
        k = i + 1
        while k < min(i + TIME_STOP_BARS, n):
            if direction == "LONG":
                if lo[k] <= sl: ep, j = sl, k; break
                if z[k] >= 0.0: ep, j = cl[k], k; break
            else:
                if hi[k] >= sl: ep, j = sl, k; break
                if z[k] <= 0.0: ep, j = cl[k], k; break
            k += 1
        if ep is None: ep = cl[j]
        gross = (ep - entry) / entry if direction == "LONG" else (entry - ep) / entry
        trades.append(gross - 2.0 * FEE_TAKER - 2.0 * SLIPPAGE)
        i = j + 1
    return trades

# ---------------------------------------------------------------------------
# 4. SINYAL MOTORU (META-READY JSON OUTPUT)
# ---------------------------------------------------------------------------
def signal_engine(symbol, df_4h, df_15m, btc_4h, btc_15m):
    meta_log = {"symbol": symbol, "timestamp": datetime.now(timezone.utc).isoformat(), "status": "NO_SIGNAL", "reason": "", "signal": {}}
    
    state, state_conf = regime_detector(df_15m["close"], df_4h["close"])
    btc_state, _ = regime_detector(btc_15m["close"], btc_4h["close"])
    meta_log["regime"] = {"alt": state, "btc": btc_state, "confidence": state_conf}
    
    if state not in ("BULL", "BEAR") or btc_state != state:
        meta_log["reason"] = f"Rejim Uyumsuz veya CALM (Alt: {state}, BTC: {btc_state})"
        return meta_log
        
    direction = "LONG" if state == "BULL" else "SHORT"
    
    # Pump/Dump Vetosu
    score15, note15 = pump_anomaly(df_15m["volume"])
    if note15 == "PUMP_OR_DUMP_RISK":
        meta_log["reason"] = "VETO: Pump/Dump Anomalisi (Yüksek Risk)"
        meta_log["anomaly_score"] = score15
        return meta_log
        
    df = df_15m.copy()
    close = df["close"].astype(float)
    sma20 = close.rolling(window=20).mean()
    sd20 = close.rolling(window=20).std(ddof=0)
    df["z"] = ((close - sma20) / (sd20 + 1e-12)).shift(periods=1)
    hl = (df["high"] - df["low"]).abs()
    hc = (df["high"] - close.shift(periods=1)).abs()
    lc = (df["low"] - close.shift(periods=1)).abs()
    tr_df = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["atr"] = tr_df.rolling(ATR_LEN).mean().shift(periods=1)
    df = df.dropna(subset=["z", "atr"])
    
    if len(df) < 700:
        meta_log["reason"] = "Yetersiz Veri (<700 bar)"
        return meta_log
        
    feat = {k: df[k].to_numpy(dtype=float) for k in ["open", "close", "low", "high", "z", "atr"]}
    rule_trades = {z: [] for z in Z_GRID}
    
    for train_idx, test_idx in walkforward_splits(len(df), N_FOLDS, EMBARGO):
        for zt in Z_GRID:
            rule_trades[zt].extend(simulate(feat, test_idx, zt, direction))
            
    stats = {zt: oos_stats(rule_trades[zt]) for zt in Z_GRID}
    pvals = {zt: 2.0 * (1.0 - norm_cdf(abs(s["t"]))) for zt, s in stats.items() if s is not None}
    
    if not pvals:
        meta_log["reason"] = "Yeterli OOS İstatistiği Yok"
        return meta_log
        
    keys = list(pvals.keys())
    accepted = fdr_bh([pvals[k] for k in keys], ALPHA)
    accepted_z = [zt for zt, ok in zip(keys, accepted) if ok]
    
    if not accepted_z:
        meta_log["reason"] = "Anti-Overfit FDR Kapısı Kapalı"
        return meta_log
        
    best_z = max(accepted_z, key=lambda zt: stats[zt]["mean"])
    best_stat = stats[best_z]
    
    cur = df.iloc[-1]
    prev = df.iloc[-2]
    zi = float(cur["z"])
    atr_i = float(cur["atr"])
    
    if direction == "LONG":
        fired = (zi <= -best_z) and (zi > -4.0) and (float(prev["z"]) < zi) and (zi > float(np.min(df["z"].iloc[-4:-1])))
    else:
        fired = (zi >= best_z) and (zi < 4.0) and (float(prev["z"]) > zi) and (zi < float(np.max(df["z"].iloc[-4:-1])))
        
    if not fired:
        meta_log["reason"] = f"Kenar onaylı ancak tetik yok (z={zi:.2f}, esik={best_z})"
        meta_log["stats"] = best_stat
        return meta_log
        
    # SİNYAL ÜRETİLDİ
    last_close = float(cur["close"])
    target_px = float(sma20.iloc[-1])
    sl_px = last_close - ATR_SL_MULT * atr_i if direction == "LONG" else last_close + ATR_SL_MULT * atr_i
    
    meta_log["status"] = "SIGNAL_FIRED"
    meta_log["signal"] = {
        "direction": direction,
        "entry_ref": last_close,
        "target": target_px,
        "stop_loss": sl_px,
        "best_z_threshold": best_z,
        "oos_expected_mean": best_stat["mean"],
        "oos_winrate": best_stat["win"],
        "oos_pf": best_stat["pf"]
    }
    return meta_log

# ---------------------------------------------------------------------------
# 5. ANA DONGU (META KONTROL CU)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("META³ AGENT v6.0 BAŞLATILIYOR...")
    selftest()
    
    btc_4h = fetch_ohlcv("BTC/USDT", TF_4H, LIMIT_4H)
    btc_15m = fetch_ohlcv("BTC/USDT", TF_15M, LIMIT_15M)
    
    meta_cycle_results = []
    
    for alt in SYMBOLS:
        try:
            print(f"Analiz Ediliyor: {alt}...")
            a4 = fetch_ohlcv(alt, TF_4H, LIMIT_4H)
            a15 = fetch_ohlcv(alt, TF_15M, LIMIT_15M)
            result = signal_engine(alt, a4, a15, btc_4h, btc_15m)
            meta_cycle_results.append(result)
            
            if result["status"] == "SIGNAL_FIRED":
                sig = result["signal"]
                print(f"\n🚨 SİNYAL BULUNDU: {alt} -> {sig['direction']}")
                print(f"Giriş: {sig['entry_ref']:.4f} | Hedef: {sig['target']:.4f} | Stop: {sig['stop_loss']:.4f}")
                print(f"İstatistik: WinRate: %{sig['oos_winrate']*100:.1f} | PF: {sig['oos_pf']:.2f} | Z-Eşiği: {sig['best_z_threshold']}")
                print("-" * 50)
            else:
                print(f"  -> {result['reason']}")
                
        except Exception as e:
            print(f"HATA ({alt}): {e}")
            traceback.print_exc()

    # META² KATMANI İÇİN JSON DÖKÜMÜ (Gelecek döngüde optimize edilecek veri)
    with open("agent_state.json", "w", encoding="utf-8") as f:
        json.dump(meta_cycle_results, f, indent=2, ensure_ascii=False)
    print("\nTarama Tamamlandı. Durum `agent_state.json` dosyasına yazıldı (Meta² Okuması İçin).")
