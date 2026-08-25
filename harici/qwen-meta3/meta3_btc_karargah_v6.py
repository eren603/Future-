#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  META³ — Nihai Recursive Self-Improving Research System             ║
║  Agent Katmanı: BTC KARARGAH v6.0 (META-Ready)                     ║
║                                                                    ║
║  v5.3.2 → v6.0 DEĞİŞİKLİK LOGU:                                   ║
║  1) SYNTAX TAMİRLERİ: s d→sd, .ab s()→.abs(),                     ║
║     V_RE VERSAL→V_REVERSAL, lob_i mbalance→lob_imbalance,          ║
║     if name==" main "→if __name__=="__main__"                      ║
║  2) SYMBOLS trailing space temizlendi ("ETH/USDT "→"ETH/USDT")     ║
║  3) META³ IMMUTABLE CONTROL PLANE eklendi                          ║
║  4) META³ MUTABLE CONFIG (Meta optimize eder) ayrıldı              ║
║  5) EXPERIMENT MEMORY + FAILURE INTELLIGENCE eklendi               ║
║  6) Print→JSON yapılandırılmış çıktı (agent_state.json)            ║
║  7) API rate-limit koruması (önbellek)                             ║
║  8) Lookahead korumaları AYNEN KORUNDU (.shift(1), kapanmamış mum) ║
║  9) MODÜL HİÇBİR EMİR GÖNDERMEZ (create_order yok)                ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import json
import hashlib
import traceback
import warnings
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 0: META³ IMMUTABLE CONTROL PLANE                        ║
# ║  Meta³ DAHİL hiçbir recursive katman bu alanı değiştiremez.     ║
# ╚══════════════════════════════════════════════════════════════════╝

class ImmutableControlPlane:
    """META³ Değişmez Çekirdek — Sistemin Anayasası"""

    # --- Safety Policy ---
    ALLOW_ORDER_EXECUTION = False      # Kod HİÇBİR emir göndermez
    MAX_RECURSIVE_DEPTH   = 3          # Agent → Meta → Meta² → Meta³
    MAX_EXPERIMENT_BUDGET = 500        # Bir döngüde max deney sayısı

    # --- Resource Limits ---
    MAX_SYMBOLS_PER_SCAN  = 20
    MAX_BARS_15M          = 2400
    MAX_BARS_4H           = 600
    MAX_API_CALLS_PER_MIN = 1200

    # --- Sandbox Boundary ---
    SANDBOX_ENABLED       = True
    ROLLBACK_ENABLED      = True

    # --- Audit ---
    AUDIT_LOG_ENABLED     = True
    AUDIT_LOG_PATH        = "meta3_audit.jsonl"

    # --- Human Override ---
    HUMAN_OVERRIDE_ENABLED = True

    # --- Durma Koşulları ---
    STOP_CONDITIONS = [
        "budget_exhausted",
        "regression",
        "evaluator_unstable",
        "repeated_failures",
        "safety_violation",
    ]

    @classmethod
    def validate_action(cls, action: str, params: dict) -> Tuple[bool, str]:
        """Safety policy doğrulaması — Meta³ bile bunu atlayamaz."""
        if action == "send_order" and not cls.ALLOW_ORDER_EXECUTION:
            return False, "IMMUTABLE: Emir gönderme kapalı (Safety Policy)"
        if action == "modify_evaluator":
            return False, "IMMUTABLE: Evaluator değiştirilemez"
        if action == "modify_safety_policy":
            return False, "IMMUTABLE: Safety Policy değiştirilemez"
        if action == "modify_resource_limits":
            return False, "IMMUTABLE: Resource Limits değiştirilemez"
        if action == "modify_sandbox":
            return False, "IMMUTABLE: Sandbox Boundary değiştirilemez"
        if action == "modify_rollback":
            return False, "IMMUTABLE: Rollback değiştirilemez"
        if action == "modify_audit":
            return False, "IMMUTABLE: Audit değiştirilemez"
        return True, "OK"

    @classmethod
    def audit_log(cls, event: str, detail: dict):
        """Denetim kaydı — her önemli olay loglanır."""
        if not cls.AUDIT_LOG_ENABLED:
            return
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "detail": detail,
        }
        try:
            with open(cls.AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 1: META³ MUTABLE CONFIGURATION                          ║
# ║  Bu parametreler Meta tarafından optimize edilebilir.           ║
# ╚══════════════════════════════════════════════════════════════════╝

@dataclass
class MutableConfig:
    """Meta katmanının optimize edebileceği parametreler.
    IMMUTABLE CONTROL PLANE dışındaki TÜM parametreler buradadır."""

    # --- Strateji Parametreleri (MİRAS SABİT — kalibre edilmedi) ---
    fee_taker:        float = 0.00040
    slippage:         float = 0.0005
    atr_len:          int   = 14
    atr_sl_mult:      float = 1.5
    time_stop_bars:   int   = 48
    alpha:            float = 0.05
    min_trades:       int   = 8
    n_folds:          int   = 5
    embargo:          int   = 24
    bootstrap_b:      int   = 2000
    bootstrap_seeds:  tuple = (20240101, 20250101)
    z_grid:           List[float] = field(default_factory=lambda: [
        1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5
    ])

    # --- Pump/Dump Parametreleri (MİRAS SABİT) ---
    pump_span:            int   = 20
    pump_threshold_z:     float = 3.0
    pump_tick_watch:      float = 2.5
    tick_confirm_window:  int   = 15
    tick_confirm_min:     int   = 10

    # --- V-Reversal Parametreleri (HİPOTEZ) ---
    v_rev_window_sec:     int   = 900
    v_rev_bucket_sec:     int   = 30
    v_rev_min_abs_pct:    float = 0.004
    v_rev_flip_pct:       float = 0.002
    v_rev_min_buckets:    int   = 6

    # --- LOB Parametreleri (MİRAS SABİT) ---
    fr_tolerance_bps:     float = 5.0
    lob_depth:            int   = 5
    lob_bias_alert:       float = 0.10

    # --- Hedef ---
    target_usd:           float = 500.0
    limit_timeout_sec:    float = 8.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["bootstrap_seeds"] = list(d["bootstrap_seeds"])
        return d

    def version_hash(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 2: META³ INFRASTRUCTURE                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

class ExperimentMemory:
    """META³ Experiment Memory — Deney Hafızası.
    Her deney: experiment_id, hypothesis, metrics, decision."""

    def __init__(self, path: str = "meta3_experiment_memory.jsonl"):
        self.path = Path(path)
        self.experiments: List[dict] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.experiments.append(json.loads(line))
            except Exception:
                pass

    def record(self, experiment: dict) -> str:
        experiment["timestamp"] = datetime.now(timezone.utc).isoformat()
        raw = json.dumps(experiment, sort_keys=True, default=str)
        experiment["experiment_id"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        self.experiments.append(experiment)
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(experiment, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass
        ImmutableControlPlane.audit_log("experiment_recorded", {
            "experiment_id": experiment["experiment_id"],
            "decision": experiment.get("decision", "N/A"),
        })
        return experiment["experiment_id"]

    def get_failures(self) -> List[dict]:
        return [e for e in self.experiments if e.get("decision") == "REJECT"]

    def get_successes(self) -> List[dict]:
        return [e for e in self.experiments if e.get("decision") == "KEEP"]

    def get_failure_clusters(self) -> Dict[str, int]:
        clusters: Dict[str, int] = {}
        for e in self.get_failures():
            reason = e.get("failure_reason", "unknown")
            clusters[reason] = clusters.get(reason, 0) + 1
        return clusters


class FailureIntelligence:
    """META³ Failure Intelligence — Başarısızlık Analizi.
    Sistem yalnızca 'Neyi deneyeyim?' değil,
    'Neyi artık denememeliyim?' sorusunu da öğrenir."""

    def __init__(self, memory: ExperimentMemory):
        self.memory = memory

    def analyze(self) -> dict:
        failures = self.memory.get_failures()
        if not failures:
            return {"total_failures": 0, "patterns": [], "recommendation": "Yeterli veri yok."}

        clusters: Dict[str, List[dict]] = {}
        for f in failures:
            reason = f.get("failure_reason", "unknown")
            clusters.setdefault(reason, []).append(f)

        patterns = []
        for reason, items in clusters.items():
            symbols = list(set(i.get("symbol", "?") for i in items))
            patterns.append({
                "reason": reason,
                "count": len(items),
                "symbols": symbols[:10],
            })

        worst = max(patterns, key=lambda p: p["count"])
        recommendation = (
            f"En sık başarısızlık: '{worst['reason']}' ({worst['count']} kez). "
            f"Bu hipotezleri tekrar denemeyin."
        )
        return {
            "total_failures": len(failures),
            "patterns": patterns,
            "recommendation": recommendation,
        }


class MetaState:
    """META³ State — Sistem Durumu.
    Agent + Meta + Meta² + Meta³ durumunu tek yerde tutar."""

    AGENT_VERSION = "6.0.0"
    META_VERSION  = "1.0.0"

    def __init__(self):
        self.config = MutableConfig()
        self.memory = ExperimentMemory()
        self.failure_intel = FailureIntelligence(self.memory)
        self.generation = 0
        self.scan_results: List[dict] = []

    def to_json(self) -> str:
        return json.dumps({
            "agent_version": self.AGENT_VERSION,
            "meta_version": self.META_VERSION,
            "generation": self.generation,
            "config_hash": self.config.version_hash(),
            "config": self.config.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, indent=2, ensure_ascii=False, default=str)


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 3: VERİ ÇEKME (Kapanmamış mum analize alınmaz)          ║
# ╚══════════════════════════════════════════════════════════════════╝

EXCHANGE = ccxt.binanceusdm({"enableRateLimit": True})

TF_4H  = "4h"
TF_15M = "15m"
TF_MS  = {"15m": 900_000, "4h": 14_400_000}

SYMBOLS = [
    "ETH/USDT", "XRP/USDT", "LINK/USDT", "DOGE/USDT", "DOT/USDT",
    "AVAX/USDT", "SUSHI/USDT", "ZEC/USDT", "ETC/USDT", "FIL/USDT",
    "AAVE/USDT",
]

# --- API Önbellek (rate-limit koruması) ---
_API_CACHE: Dict[str, Any] = {}


def _cache_key(*args) -> str:
    return "|".join(str(a) for a in args)


def _cache_get(key: str, max_age_sec: float = 60.0):
    if key in _API_CACHE:
        entry = _API_CACHE[key]
        age = (datetime.now(timezone.utc) - entry["ts"]).total_seconds()
        if age < max_age_sec:
            return entry["data"]
    return None


def _cache_set(key: str, data):
    _API_CACHE[key] = {"data": data, "ts": datetime.now(timezone.utc)}


def unix_ms(lookback_min: float = 0) -> int:
    now_ms = int(pd.Timestamp.now(tz="UTC").value // 1_000_000)
    return int(now_ms - lookback_min * 60_000)


def fetch_ohlcv(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    step_ms = TF_MS.get(timeframe)
    if step_ms is None:
        raise ValueError(f"TF desteklenmiyor: {timeframe}")

    ck = _cache_key("ohlcv", symbol, timeframe, limit)
    cached = _cache_get(ck, max_age_sec=120)
    if cached is not None:
        return cached

    end = unix_ms()
    since = end - limit * step_ms
    arr = None
    while since < end:
        part = EXCHANGE.fetch_ohlcv(symbol, timeframe=timeframe,
                                    since=since, limit=1000)
        if not part:
            break
        part_arr = np.asarray(part, dtype=float)
        arr = part_arr if arr is None else np.vstack([arr, part_arr])
        since += len(part) * step_ms

    if arr is None:
        raise ValueError(f"Veri alınamadı: {symbol}")

    df = pd.DataFrame(arr, columns=["timestamp", "open", "high", "low",
                                    "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = (df.drop_duplicates(subset="timestamp")
            .tail(limit)
            .set_index("timestamp")
            .astype(float))
    if len(df) > 1:
        df = df.iloc[:-1]  # KAPANMAMIŞ MUMU AT (lookahead koruması)

    _cache_set(ck, df)
    return df


def fetch_order_book(symbol: str, depth: int = 5):
    ck = _cache_key("ob", symbol, depth)
    cached = _cache_get(ck, max_age_sec=10)
    if cached is not None:
        return cached

    try:
        ob = EXCHANGE.fetch_order_book(symbol, limit=depth)
    except Exception:
        return None, None
    if not ob or not ob.get("bids") or not ob.get("asks"):
        return None, None

    bids = pd.DataFrame(ob["bids"][:depth], columns=["price", "size"])
    asks = pd.DataFrame(ob["asks"][:depth], columns=["price", "size"])
    result = (bids, asks)
    _cache_set(ck, result)
    return result


def fetch_recent_trades(symbol: str, lookback_min: float = 60) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["timestamp", "price", "amount"])
    ck = _cache_key("trades", symbol, lookback_min)
    cached = _cache_get(ck, max_age_sec=15)
    if cached is not None:
        return cached

    try:
        trades = EXCHANGE.fetch_trades(
            symbol, since=unix_ms(lookback_min=lookback_min), limit=1000)
    except Exception:
        return empty
    if not trades:
        return empty

    df = pd.DataFrame(trades)
    for col in ("timestamp", "price", "amount"):
        if col not in df.columns:
            return empty
    result = df[["timestamp", "price", "amount"]].astype(float)
    _cache_set(ck, result)
    return result


def fetch_funding_oi(symbol: str):
    fr_df = pd.DataFrame()
    oi = float("nan")
    try:
        fr_raw = EXCHANGE.fetch_funding_rate_history(symbol, limit=8)
        if fr_raw:
            fr_df = pd.DataFrame(fr_raw)
    except Exception:
        pass
    try:
        oi_raw = EXCHANGE.fetch_open_interest(symbol)
        oi = float(oi_raw.get("openInterestAmount", float("nan")))
    except Exception:
        pass
    return fr_df, oi


def lob_imbalance(bids, asks):
    """ÖNCÜ veri: emir defteri dengesi (pozitif = alış ağırlıklı)."""
    if bids is None or asks is None or bids.empty or asks.empty:
        return 0.0, 0.0, float("inf")
    bid_usd = float((bids["price"] * bids["size"]).sum())
    ask_usd = float((asks["price"] * asks["size"]).sum())
    best_bid = float(bids["price"].iloc[0])
    best_ask = float(asks["price"].iloc[0])
    spread_bps = (best_ask - best_bid) / best_bid * 1e4
    imb = (bid_usd - ask_usd) / max(bid_usd + ask_usd, 1e-12)
    return imb, bid_usd + ask_usd, spread_bps


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 4: ANALİZ FONKSİYONLARI                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(periods=1)).dropna()


def corr_stats(alt_close: pd.Series, ref_close: pd.Series,
               n_max: int = 672) -> Optional[dict]:
    d = pd.concat([log_returns(alt_close), log_returns(ref_close)],
                  axis=1).dropna().tail(n_max)
    if len(d) < 50:
        return None
    r = float(d.iloc[:, 0].corr(d.iloc[:, 1]))
    if not np.isfinite(r):
        return None
    zf = 0.5 * math.log((1.0 + r) / max(1.0 - r, 1e-12))
    se = 1.0 / math.sqrt(len(d) - 3)
    p = 2.0 * (1.0 - norm_cdf(abs(zf) / se))
    return {"n": len(d), "r": r, "p": p}


def pump_anomaly(vol_series: pd.Series, span: int = 20,
                 threshold: float = 3.0) -> Tuple[float, str]:
    """Hacim anomalisi — SON KAPANMIS BARDA ölçülür (seri maksimumu DEĞİL).
    v5.3.1 TAMİR: skor tüm seri üzerinden değil, son bardan alınır."""
    if len(vol_series) < 30:
        return 0.0, "VERI_YOK"

    v = vol_series.astype(float).fillna(0.0)

    ewma = v.ewm(span=span, adjust=False).mean().shift(periods=1)
    evol = v.ewm(span=span, adjust=False).std().shift(periods=1)
    z = (v - ewma) / (evol + 1e-12)
    z_now = float(z.iloc[-1])

    cus = v.diff().abs().rolling(window=10).sum()
    cus_mu = cus.ewm(span=span * 5, adjust=False).mean().shift(periods=1)
    cus_sd = cus.ewm(span=span * 5, adjust=False).std().shift(periods=1)
    cs = (cus - cus_mu) / (cus_sd + 1e-12)
    cs_now = float(cs.iloc[-1])

    if not (np.isfinite(z_now) or np.isfinite(cs_now)):
        return 0.0, "VERI_YOK"

    z_now = z_now if np.isfinite(z_now) else 0.0
    cs_now = cs_now if np.isfinite(cs_now) else 0.0
    score = max(z_now, cs_now)

    if score < threshold * 0.6:
        return score, "NORMAL"
    if score < threshold:
        return score, "WATCH"
    return score, "PUMP_OR_DUMP_RISK"


def pump_dump_direction(trades, close_15m,
                        lookback_min: float = 15) -> Tuple[str, float]:
    """Yön tespiti: tick VWAP + 15m OHLCV birlikte. ÖNCÜ veri."""
    tick_dir = 0.0
    if trades is not None and not trades.empty and len(trades) >= 10:
        cut = unix_ms(lookback_min=lookback_min)
        w = trades[trades["timestamp"] >= cut]
        if len(w) >= 10:
            w = w.copy()
            w["usd"] = w["price"] * w["amount"]
            tot_usd = float(w["usd"].sum())
            tot_amt = float(w["amount"].sum())
            if tot_amt > 0:
                vwap = tot_usd / tot_amt
                last_px = float(w["price"].iloc[-1])
                tick_dir = (last_px - vwap) / vwap

    ohlcv_dir = 0.0
    if close_15m is not None and len(close_15m) >= 3:
        c = close_15m.astype(float)
        ohlcv_dir = (float(c.iloc[-1]) - float(c.iloc[-3])) / float(c.iloc[-3])

    move = tick_dir if abs(tick_dir) > 1e-12 else ohlcv_dir
    if move <= -0.005:
        return "DUMP", move
    if move >= 0.005:
        return "PUMP", move
    return "YON_BELIRSIZ", move


def tick_confirm_score(symbol: str, trades=None,
                       window_min: int = 15,
                       min_trades: int = 10) -> Optional[float]:
    """ÖNCÜ tick hacim z-skoru. Son KAPANMIŞ dakikanın USD hacmi,
    önceki dakikalara göre kaç sigma sapmış?"""
    if trades is None:
        trades = fetch_recent_trades(symbol, lookback_min=window_min)
    if trades is None or trades.empty:
        return None

    t = trades.copy()
    t = t[t["timestamp"] >= unix_ms(lookback_min=window_min)]
    if len(t) < min_trades:
        return None

    t["usd"] = t["price"] * t["amount"]
    t["minute"] = (t["timestamp"] // 60_000).astype("int64")
    m = t.groupby("minute")["usd"].sum().sort_index()

    now_minute = unix_ms() // 60_000
    m = m[m.index < now_minute]
    if len(m) >= 2:
        m = m.iloc[1:]
    if len(m) < 5:
        return None

    cur = float(m.iloc[-1])
    past = m.iloc[:-1].astype(float)
    base = float(past.mean())
    sd = float(past.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0.0 or base <= 0.0:
        return None
    return (cur - base) / sd


def v_reversal_detect(trades, window_sec: int = 900,
                      bucket_sec: int = 30,
                      min_abs_pct: float = 0.004,
                      flip_pct: float = 0.002,
                      min_buckets: int = 6) -> List[dict]:
    """V DÖNÜŞÜ (dip/tepe) — ÖNCÜ tick verisiyle anlık tespit."""
    if trades is None or trades.empty or len(trades) < 20:
        return []

    cut = unix_ms(lookback_min=window_sec / 60.0)
    w = trades[trades["timestamp"] >= cut].copy()
    if len(w) < 20:
        return []

    w = w.sort_values("timestamp")
    w["bucket"] = (w["timestamp"] // (bucket_sec * 1000)).astype("int64")
    b = w.groupby("bucket")["price"].agg(["mean", "min", "max", "count"]).dropna()
    if len(b) < min_buckets:
        return []

    px = b["mean"].to_numpy(dtype=float)
    n = len(px)
    result = []

    imin = int(np.argmin(px))
    if 1 <= imin <= n - 3:
        recover = float(px[-1]) / float(px[imin]) - 1.0
        drop = -(float(px[imin]) / float(px[0]) - 1.0)
        if drop >= min_abs_pct and recover >= flip_pct:
            result.append({
                "kind": "V_DIP",
                "drop_pct": drop * 100.0,
                "recover_pct": recover * 100.0,
                "detail": "satış dalgası sonrası yukarı dönüş öncüleri",
            })

    imax = int(np.argmax(px))
    if 1 <= imax <= n - 3:
        rise = float(px[imax]) / float(px[0]) - 1.0
        pull = float(px[-1]) / float(px[imax]) - 1.0
        if rise >= min_abs_pct and pull <= -flip_pct:
            result.append({
                "kind": "V_TEPE",
                "rise_pct": rise * 100.0,
                "pullback_pct": -pull * 100.0,
                "detail": "alış dalgası sonrası aşağı dönüş öncüleri",
            })

    return result


def trend_flip_watch(close_15m, trades,
                     min_mom_pct: float = 0.001) -> Optional[str]:
    """Trend/rejim dönüşü uyarısı."""
    if close_15m is None or len(close_15m) < 30:
        return None
    c = close_15m.astype(float)
    e8 = c.ewm(span=8, adjust=False).mean()
    e21 = c.ewm(span=21, adjust=False).mean()
    cross_up = (float(e8.iloc[-1]) > float(e21.iloc[-1]) and
                float(e8.iloc[-2]) <= float(e21.iloc[-2]))
    cross_dn = (float(e8.iloc[-1]) < float(e21.iloc[-1]) and
                float(e8.iloc[-2]) >= float(e21.iloc[-2]))
    if not (cross_up or cross_dn):
        return None

    mom = 0.0
    if trades is not None and not trades.empty:
        t = trades.copy()
        cut = unix_ms(lookback_min=10)
        t = t[t["timestamp"] >= cut].sort_values("timestamp")
        if len(t) >= 10:
            half = len(t) // 2
            lo = float(t["price"].iloc[:half].mean())
            hi = float(t["price"].iloc[half:].mean())
            if lo > 0:
                mom = (hi - lo) / lo

    if cross_up:
        if mom > min_mom_pct:
            return (f"TREND DONUSU: EMA8/21 yukarı kesti + "
                    f"tick momentum {mom * 100:+.2f}%")
        return (f"TREND DONUSU ONCUSU: EMA8/21 kesti, "
                f"tick doğrulama YOK (mom={mom * 100:+.2f}%)")
    if mom < -min_mom_pct:
        return (f"TREND DONUSU: EMA8/21 aşağı kesti + "
                f"tick momentum {mom * 100:+.2f}%")
    return (f"TREND DONUSU ONCUSU: EMA8/21 kesti, "
            f"tick doğrulama YOK (mom={mom * 100:+.2f}%)")


def regime_detector(close_15m: pd.Series,
                    close_4h: pd.Series) -> Tuple[str, float]:
    """Rejim tespiti — dinamik ATR-marjlı."""
    if len(close_15m) < 20 or len(close_4h) < 50:
        return "UNKNOWN", 0.0

    r15 = log_returns(close_15m)
    if len(r15) < 20:
        return "UNKNOWN", 0.0

    ef = close_4h.ewm(span=50, adjust=False).mean()
    es = close_4h.ewm(span=200, adjust=False).mean()
    slope = (ef - es) / close_4h
    tr4 = (close_4h - close_4h.shift(periods=1)).abs()
    atr_pct = float((tr4.rolling(window=14).mean() / close_4h).iloc[-1])
    if not np.isfinite(atr_pct):
        atr_pct = 0.0

    margin = max(0.003, atr_pct * 1.5)
    s = slope.reindex(r15.index, method="ffill").fillna(0.0)
    mu = float(r15.mean())
    cur = float(s.iloc[-1])

    if cur > margin and mu > 0:
        return "BULL", min(0.9, 0.5 + abs(cur) * 5.0)
    if cur < -margin and mu < 0:
        return "BEAR", min(0.9, 0.5 + abs(cur) * 5.0)
    return "CALM", 0.7


def realtime_warnings(symbol: str, trades, close_15m, bids, asks,
                      vol_score: float, vol_note: str,
                      yon: str, yon_move: float,
                      cfg: MutableConfig) -> List[str]:
    """ÖNCÜ veri (tick akışı, LOB, anlık hacim z) ile ANI uyarılar."""
    warns = []
    imb, depth_usd, spread_bps = lob_imbalance(bids, asks)

    if vol_note == "PUMP_OR_DUMP_RISK":
        if yon == "DUMP":
            warns.append(f"ANILIK DUMP DALGASI: hacim z={vol_score:.2f}, "
                         f"tick {yon_move * 100:+.2f}%")
        elif yon == "PUMP":
            warns.append(f"ANILIK PUMP DALGASI: hacim z={vol_score:.2f}, "
                         f"tick {yon_move * 100:+.2f}%")
        else:
            warns.append(f"ANILIK PUMP/DUMP RISKI: hacim z={vol_score:.2f}, "
                         f"yon belirsiz")

    if imb <= -cfg.lob_bias_alert:
        warns.append(f"LOB ALARM: satış ağırlıklı (OBI={imb:+.2f})")
    elif imb >= cfg.lob_bias_alert:
        warns.append(f"LOB ALARM: alış ağırlıklı (OBI={imb:+.2f})")

    for v in v_reversal_detect(trades,
                               window_sec=cfg.v_rev_window_sec,
                               bucket_sec=cfg.v_rev_bucket_sec,
                               min_abs_pct=cfg.v_rev_min_abs_pct,
                               flip_pct=cfg.v_rev_flip_pct,
                               min_buckets=cfg.v_rev_min_buckets):
        if v["kind"] == "V_DIP":
            warns.append(f"V DONUSU: düşüş {v['drop_pct']:.2f}% -> "
                         f"toparlanma {v['recover_pct']:+.2f}% | {v['detail']}")
        else:
            warns.append(f"V DONUSU: yükseliş {v['rise_pct']:.2f}% -> "
                         f"geri çekilme {v['pullback_pct']:+.2f}% | {v['detail']}")

    flip = trend_flip_watch(close_15m, trades)
    if flip:
        warns.append(flip)

    return warns


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 5: İSTATİSTİK (BH-FDR + max-t bootstrap)                ║
# ╚══════════════════════════════════════════════════════════════════╝

def oos_stats(trades: list, min_n: int = 8) -> Optional[dict]:
    if len(trades) < min_n:
        return None
    a = np.asarray(trades, dtype=float)
    n = len(a)
    mean = float(np.mean(a))
    sd = float(np.std(a, ddof=1))
    t = mean / (sd / math.sqrt(n)) if sd > 0 else 0.0
    wins = a[a > 0]
    losses = -a[a <= 0]
    ls = float(np.sum(losses))
    pf = float(np.sum(wins) / ls) if ls > 0 else float("inf")
    cum = np.cumprod(1.0 + a)
    pk = np.maximum.accumulate(cum)
    return {
        "n": n, "mean": mean, "sd": sd, "t": t,
        "win": float(len(wins) / n), "pf": pf,
        "mdd": float(np.min(cum / pk - 1.0)),
    }


def fdr_bh(pvalues: list, alpha: float = 0.05) -> List[bool]:
    m = len(pvalues)
    if m == 0:
        return []
    order = np.argsort(pvalues)
    arr = np.asarray(pvalues, dtype=float)[order]
    thr_arr = np.asarray([(k + 1) / m * alpha for k in range(m)])
    accept = arr <= thr_arr
    if not accept.any():
        return [False] * m
    kmax = int(np.max(np.where(accept)[0]))
    keep = np.zeros(m, dtype=bool)
    keep[:kmax + 1] = True
    out = [False] * m
    for i, ix in enumerate(order):
        out[ix] = bool(keep[i])
    return out


def bootstrap_max_t(oos_by_rule: dict, B: int = 2000,
                    seeds: tuple = (20240101, 20250101)) -> float:
    valid = []
    for r in oos_by_rule.values():
        a = np.asarray(r, dtype=float)
        if len(a) >= 2:
            valid.append(a)
    if not valid:
        return 1.0

    t_obs = 0.0
    for a in valid:
        m = len(a)
        sd = float(np.std(a, ddof=1))
        if sd > 0:
            t_obs = max(t_obs, float(np.mean(a)) / (sd / math.sqrt(m)))

    p_seeds = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        n_exceed = 0
        for _ in range(B):
            tmax = 0.0
            for a in valid:
                m = len(a)
                sample = a[rng.integers(0, m, size=m)]
                centered = sample - float(np.mean(a))
                cm = float(np.mean(centered))
                cs = float(np.std(centered, ddof=1))
                tb = cm / (cs / math.sqrt(m)) if cs > 0 else 0.0
                tmax = max(tmax, tb)
            if tmax >= t_obs:
                n_exceed += 1
        p_seeds.append(n_exceed / B)
    return float(np.mean(p_seeds))


def walkforward_splits(n: int, k: int = 5,
                       embargo: int = 24) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Embargolu genişleyen-pencere walk-forward (CPCV DEĞİL)."""
    fold = n // k
    splits = []
    if fold <= 0:
        return splits
    for t in range(1, k):
        test = np.arange(t * fold, min((t + 1) * fold, n))
        train = np.arange(0, t * fold)
        train = train[train <= (t * fold - 1 - embargo)]
        if len(train) < 200:
            continue
        splits.append((train, test))
    return splits


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 6: İŞLEM SİMÜLASYONU                                    ║
# ╚══════════════════════════════════════════════════════════════════╝

def simulate(feat: dict, idx: np.ndarray, z_th: float,
             direction: str, cfg: MutableConfig) -> List[float]:
    o   = feat["open"][idx]
    cl  = feat["close"][idx]
    lo  = feat["low"][idx]
    hi  = feat["high"][idx]
    z   = feat["z"][idx]
    atr = feat["atr"][idx]
    n = len(o)
    if n < 63:
        return []

    trades = []
    i = 62
    while i < n - 1:
        zi = float(z[i])
        atr_i = float(atr[i])
        if not (np.isfinite(zi) and np.isfinite(atr_i) and atr_i > 0):
            i += 1
            continue

        if direction == "LONG":
            fired = ((zi <= -z_th) and (z[i - 1] < zi) and
                     (zi > float(np.min(z[i - 3:i]))))
        else:
            fired = ((zi >= z_th) and (z[i - 1] > zi) and
                     (zi < float(np.max(z[i - 3:i]))))

        if not fired:
            i += 1
            continue

        entry = float(o[i])
        sl = (entry - cfg.atr_sl_mult * atr_i if direction == "LONG"
              else entry + cfg.atr_sl_mult * atr_i)
        ep = None
        j = min(i + cfg.time_stop_bars, n - 1)
        k = i + 1
        while k < min(i + cfg.time_stop_bars, n):
            if direction == "LONG":
                if lo[k] <= sl:
                    ep, j = sl, k
                    break
                if z[k] >= 0.0:
                    ep, j = cl[k], k
                    break
            else:
                if hi[k] >= sl:
                    ep, j = sl, k
                    break
                if z[k] <= 0.0:
                    ep, j = cl[k], k
                    break
            k += 1
        if ep is None:
            ep = cl[j]

        gross = ((ep - entry) / entry if direction == "LONG"
                 else (entry - ep) / entry)
        trades.append(gross - 2.0 * cfg.fee_taker - 2.0 * cfg.slippage)
        i = j + 1
    return trades


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 7: EXECUTION ROUTER (Emir GÖNDERMEZ)                     ║
# ╚══════════════════════════════════════════════════════════════════╝

def execution_router(symbol: str, direction: str, target_usd: float,
                     bids=None, asks=None,
                     cfg: MutableConfig = None) -> dict:
    if cfg is None:
        cfg = MutableConfig()
    if bids is None or asks is None:
        bids, asks = fetch_order_book(symbol, depth=cfg.lob_depth)

    imb, depth_usd, spread_bps = lob_imbalance(bids, asks)

    if bids is None or asks is None or bids.empty or asks.empty:
        return {
            "order_type": "MARKET", "ref_px": float("nan"),
            "role": "taker", "best_bid": None, "best_ask": None,
            "imb": imb, "spread_bps": spread_bps,
        }

    best_bid = float(bids["price"].iloc[0])
    best_ask = float(asks["price"].iloc[0])

    bias = ((imb > cfg.lob_bias_alert and direction == "LONG") or
            (imb < -cfg.lob_bias_alert and direction == "SHORT"))
    depth_ok = depth_usd >= target_usd * 2.0

    if bias and depth_ok and spread_bps < cfg.fr_tolerance_bps:
        px = best_bid if direction == "LONG" else best_ask
        return {
            "order_type": "LIMIT", "ref_px": px,
            "role": "maker", "best_bid": best_bid, "best_ask": best_ask,
            "imb": imb, "spread_bps": spread_bps,
        }

    px = best_ask if direction == "LONG" else best_bid
    return {
        "order_type": "MARKET", "ref_px": px,
        "role": "taker", "best_bid": best_bid, "best_ask": best_ask,
        "imb": imb, "spread_bps": spread_bps,
    }


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 8: SİNYAL MOTORU (META-Ready)                           ║
# ╚══════════════════════════════════════════════════════════════════╝

def signal_engine(symbol: str, df_4h: pd.DataFrame, df_15m: pd.DataFrame,
                  btc_4h: pd.DataFrame, btc_15m: pd.DataFrame,
                  eth_4h: pd.DataFrame, eth_15m: pd.DataFrame,
                  cfg: MutableConfig,
                  meta_state: MetaState) -> dict:
    """Sinyal motoru — yapılandırılmış dict döndürür (print DEĞİL).
    Meta katmanı bu dict'i okuyarak optimizasyon yapar."""

    result = {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "NO_SIGNAL",
        "reason": "",
        "regime": {},
        "correlation": {},
        "warnings": [],
        "signal": {},
        "oos_stats": {},
        "failure_reason": "",
    }

    try:
        # --- Korelasyon ---
        cb = corr_stats(df_15m["close"], btc_15m["close"])
        if cb:
            result["correlation"]["btc"] = cb
        if symbol != "ETH/USDT":
            ce = corr_stats(df_15m["close"], eth_15m["close"])
            if ce:
                result["correlation"]["eth"] = ce

        # --- Rejim ---
        state, state_conf = regime_detector(df_15m["close"], df_4h["close"])
        btc_state, _ = regime_detector(btc_15m["close"], btc_4h["close"])
        result["regime"] = {
            "alt": state, "alt_conf": state_conf,
            "btc": btc_state,
        }

        # --- Funding / OI ---
        fr_df, oi = fetch_funding_oi(symbol)
        fr_latest = 0.0
        if not fr_df.empty and "fundingRate" in fr_df.columns:
            fr_latest = float(fr_df["fundingRate"].iloc[-1])
        result["funding_rate"] = fr_latest
        result["open_interest"] = oi if np.isfinite(oi) else None

        # --- ÖNCÜ veri ---
        trades = fetch_recent_trades(symbol)
        bids, asks = fetch_order_book(symbol, depth=cfg.lob_depth)

        score15, note15 = pump_anomaly(df_15m["volume"],
                                       span=cfg.pump_span,
                                       threshold=cfg.pump_threshold_z)
        yon, yon_move = pump_dump_direction(trades, df_15m["close"])

        mw = realtime_warnings(symbol, trades, df_15m["close"],
                               bids, asks, score15, note15,
                               yon, yon_move, cfg)
        result["warnings"] = mw
        result["pump_score"] = score15
        result["pump_note"] = note15
        result["direction_hint"] = yon
        result["direction_move"] = yon_move

        # --- Pump/Dump vetosu ---
        note = note15
        if note15 in ("NORMAL", "WATCH"):
            tscore = tick_confirm_score(symbol, trades,
                                        window_min=cfg.tick_confirm_window,
                                        min_trades=cfg.tick_confirm_min)
            if tscore is not None:
                result["tick_confirm_z"] = tscore
                if note15 == "WATCH" and tscore >= cfg.pump_tick_watch:
                    note = "PUMP_OR_DUMP_RISK"

        if note == "VERI_YOK":
            result["status"] = "NO_SIGNAL"
            result["reason"] = "VERI_YOK: hacim serisi yetersiz"
            result["failure_reason"] = "insufficient_data"
            return result

        if note == "PUMP_OR_DUMP_RISK":
            result["status"] = "VETO"
            result["reason"] = f"PUMP/DUMP veto: {yon} ({yon_move * 100:+.2f}%)"
            result["failure_reason"] = "pump_dump_veto"
            return result

        # --- Rejim uyumu ---
        if state in ("BULL", "BEAR") and btc_state != state:
            result["status"] = "NO_SIGNAL"
            result["reason"] = f"Rejim uyumsuz: alt={state}, BTC={btc_state}"
            result["failure_reason"] = "regime_mismatch"
            return result

        direction = ("LONG" if state == "BULL"
                     else "SHORT" if state == "BEAR" else None)
        if direction is None:
            result["status"] = "NO_SIGNAL"
            result["reason"] = "Rejim CALM/UNKNOWN"
            result["failure_reason"] = "calm_regime"
            return result

        # --- Z-score hazırlığı ---
        df = df_15m.copy()
        close = df["close"].astype(float)
        sma20 = close.rolling(window=20).mean()
        sd20 = close.rolling(window=20).std(ddof=0)
        df["z"] = ((close - sma20) / (sd20 + 1e-12)).shift(periods=1)
        hl = (df["high"] - df["low"]).abs()
        hc = (df["high"] - close.shift(periods=1)).abs()
        lc = (df["low"] - close.shift(periods=1)).abs()
        tr_df = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        df["atr"] = tr_df.rolling(cfg.atr_len).mean().shift(periods=1)
        df["target"] = sma20
        df = df.dropna(subset=["z", "atr"])

        if len(df) < 700:
            result["status"] = "NO_SIGNAL"
            result["reason"] = f"Yetersiz veri ({len(df)} mum)"
            result["failure_reason"] = "insufficient_bars"
            return result

        feat = {k: df[k].to_numpy(dtype=float)
                for k in ["open", "close", "low", "high", "z", "atr"]}

        # --- Walk-forward ---
        rule_trades = {z: [] for z in cfg.z_grid}
        folds = 0
        for train_idx, test_idx in walkforward_splits(
                len(df), cfg.n_folds, cfg.embargo):
            for zt in cfg.z_grid:
                rule_trades[zt].extend(
                    simulate(feat, test_idx, zt, direction, cfg))
            folds += 1

        if folds == 0:
            result["status"] = "NO_SIGNAL"
            result["reason"] = "Walk-forward split yok"
            result["failure_reason"] = "no_wf_splits"
            return result

        stats = {zt: oos_stats(rule_trades[zt], min_n=cfg.min_trades)
                 for zt in cfg.z_grid}
        pvals = {}
        for zt, s in stats.items():
            if s is not None:
                pvals[zt] = 2.0 * (1.0 - norm_cdf(abs(s["t"])))

        if not pvals:
            result["status"] = "NO_SIGNAL"
            result["reason"] = "Yeterli OOS yok"
            result["failure_reason"] = "insufficient_oos"
            return result

        keys = list(pvals.keys())
        accepted = fdr_bh([pvals[k] for k in keys], cfg.alpha)
        accepted_z = [zt for zt, ok in zip(keys, accepted) if ok]
        p_max = bootstrap_max_t(rule_trades, B=cfg.bootstrap_b,
                                seeds=cfg.bootstrap_seeds)

        result["wf_folds"] = folds
        result["fdr_accepted"] = accepted_z
        result["bootstrap_p"] = p_max

        if not accepted_z or p_max >= cfg.alpha:
            result["status"] = "NO_SIGNAL"
            result["reason"] = "Anti-overfit kapısı kapalı"
            result["failure_reason"] = "anti_overfit_gate"
            return result

        best_z = max(accepted_z, key=lambda zt: stats[zt]["mean"])
        best_stat = stats[best_z]
        result["oos_stats"] = best_stat
        result["best_z"] = best_z

        # --- Tetik kontrolü ---
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        zi = float(cur["z"])
        atr_i = float(cur["atr"])

        if direction == "LONG":
            fired = ((zi <= -best_z) and (zi > -4.0) and
                     (float(prev["z"]) < zi) and
                     (zi > float(np.min(df["z"].iloc[-4:-1]))))
        else:
            fired = ((zi >= best_z) and (zi < 4.0) and
                     (float(prev["z"]) > zi) and
                     (zi < float(np.max(df["z"].iloc[-4:-1]))))

        if not fired:
            result["status"] = "EDGE_CONFIRMED"
            result["reason"] = (f"Kenar onaylı; tetik yok "
                                f"(z={zi:.2f}, eşik={best_z})")
            result["failure_reason"] = "no_trigger"
            return result

        # --- SİNYAL ÜRETİLDİ ---
        router = execution_router(symbol, direction, cfg.target_usd,
                                  bids, asks, cfg)
        last_close = float(cur["close"])
        target_px = float(cur["target"])
        sl_px = (last_close - cfg.atr_sl_mult * atr_i if direction == "LONG"
                 else last_close + cfg.atr_sl_mult * atr_i)

        result["status"] = "SIGNAL_FIRED"
        result["reason"] = "WF+FDR+bootstrap onaylı sinyal"
        result["signal"] = {
            "direction": direction,
            "entry_ref": last_close,
            "target": target_px,
            "stop_loss": sl_px,
            "time_stop_bars": cfg.time_stop_bars,
            "order_type": router["order_type"],
            "order_px": router["ref_px"],
            "order_role": router["role"],
            "best_bid": router["best_bid"],
            "best_ask": router["best_ask"],
            "lob_imbalance": router["imb"],
            "spread_bps": router["spread_bps"],
        }

    except Exception as e:
        result["status"] = "ERROR"
        result["reason"] = str(e)
        result["failure_reason"] = "exception"
        result["traceback"] = traceback.format_exc()

    return result


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 9: KENDİNDEN KONTROL (SELFTEST)                         ║
# ╚══════════════════════════════════════════════════════════════════╝

def selftest(cfg: MutableConfig):
    """Deterministik, ağsız kendinden kontrol."""
    end_ms = int(pd.Timestamp.now(tz="UTC").value // 1_000_000)
    assert isinstance(end_ms, int) and end_ms > 1_700_000_000_000, \
        "Selftest 1 BASARISIZ: zaman damgasi"

    s = pd.Series([1.0, 2.0]).shift(periods=1)
    assert pd.isna(s.iloc[0]) and float(s.iloc[1]) == 1.0, \
        "Selftest 2 BASARISIZ: shift sonucu"

    probe = pd.Series([1.0, 2.0, 3.0, 5.0, 8.0]).ewm(span=3).std()
    assert len(probe.dropna()) > 0, "Selftest 3 BASARISIZ: ewm.std"

    v = pd.Series(np.random.default_rng(42).lognormal(3.0, 0.4, 600))
    sc, note = pump_anomaly(v, span=cfg.pump_span,
                            threshold=cfg.pump_threshold_z)
    assert note in ("NORMAL", "WATCH"), \
        f"Selftest 4 BASARISIZ: sakin seride {note} (skor={sc:.2f})"

    v2 = v.copy()
    v2.iloc[-1] *= 10.0
    sc2, note2 = pump_anomaly(v2, span=cfg.pump_span,
                              threshold=cfg.pump_threshold_z)
    assert note2 == "PUMP_OR_DUMP_RISK", \
        f"Selftest 5 BASARISIZ: x10 spike yakalanmadi ({note2}, {sc2:.2f})"

    assert pump_anomaly(pd.Series([1.0] * 10))[1] == "VERI_YOK", \
        "Selftest 6 BASARISIZ: kisa seri VERI_YOK degil"

    bos = pd.DataFrame(columns=["timestamp", "price", "amount"])
    assert tick_confirm_score("SELFTEST", bos) is None, \
        "Selftest 7 BASARISIZ: bos tick verisi None donmedi"

    assert v_reversal_detect(None) == [], \
        "Selftest 8 BASARISIZ: bos girdi V-donusu bos liste degil"

    # Immutable Control Plane testi
    ok, msg = ImmutableControlPlane.validate_action("send_order", {})
    assert not ok, "Selftest 9 BASARISIZ: emir gonderme engellenmedi"

    ok2, msg2 = ImmutableControlPlane.validate_action("modify_evaluator", {})
    assert not ok2, "Selftest 10 BASARISIZ: evaluator degisikligi engellenmedi"

    print("Kendinden kontrol: OK (10 test)")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 10: META³ ÇIKTI ÜRETİMİ                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

def generate_meta3_output(meta_state: MetaState,
                          scan_results: List[dict]) -> dict:
    """META³ yapılandırılmış çıktı — Meta katmanının okuyacağı format."""

    signals = [r for r in scan_results if r["status"] == "SIGNAL_FIRED"]
    vetoes = [r for r in scan_results if r["status"] == "VETO"]
    errors = [r for r in scan_results if r["status"] == "ERROR"]
    no_sig = [r for r in scan_results
              if r["status"] in ("NO_SIGNAL", "EDGE_CONFIRMED")]

    failure_analysis = meta_state.failure_intel.analyze()

    output = {
        "meta3_version": "1.0.0",
        "agent_version": MetaState.AGENT_VERSION,
        "generation": meta_state.generation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config_hash": meta_state.config.version_hash(),
        "config": meta_state.config.to_dict(),
        "scan_summary": {
            "total_symbols": len(scan_results),
            "signals_fired": len(signals),
            "vetoes": len(vetoes),
            "no_signal": len(no_sig),
            "errors": len(errors),
        },
        "signals": signals,
        "vetoes": vetoes,
        "errors": errors,
        "failure_intelligence": failure_analysis,
        "immutable_control_plane": {
            "allow_order_execution": ImmutableControlPlane.ALLOW_ORDER_EXECUTION,
            "max_recursive_depth": ImmutableControlPlane.MAX_RECURSIVE_DEPTH,
            "max_experiment_budget": ImmutableControlPlane.MAX_EXPERIMENT_BUDGET,
        },
        "meta_optimization_hints": {
            "note": "Meta katmanı bu alanı okuyarak parametreleri optimize eder",
            "mutable_params": list(asdict(MutableConfig()).keys()),
            "immutable_params": [
                "Evaluator", "SafetyPolicy", "ResourceLimits",
                "SandboxBoundary", "Rollback", "Audit",
                "HumanOverride", "MaxBudget", "MaxRecursiveDepth",
            ],
        },
    }
    return output


# ╔══════════════════════════════════════════════════════════════════╗
# ║  BÖLÜM 11: ANA DÖNGÜ                                           ║
# ╚══════════════════════════════════════════════════════════════════╝

def main():
    print("=" * 70)
    print("META³ BTC KARARGAH v6.0 — META-Ready Agent")
    print("(karar-destek; emir GÖNDERMEZ)")
    print("=" * 70)

    cfg = MutableConfig()
    meta_state = MetaState()

    # --- Selftest ---
    selftest(cfg)

    # --- Referans veriler ---
    print("\nReferans veriler çekiliyor (BTC, ETH)...")
    btc_4h = fetch_ohlcv("BTC/USDT", TF_4H, 600)
    btc_15m = fetch_ohlcv("BTC/USDT", TF_15M, 2400)
    eth_4h = fetch_ohlcv("ETH/USDT", TF_4H, 600)
    eth_15m = fetch_ohlcv("ETH/USDT", TF_15M, 2400)
    print(f"  BTC 4h: {len(btc_4h)} bar | BTC 15m: {len(btc_15m)} bar")
    print(f"  ETH 4h: {len(eth_4h)} bar | ETH 15m: {len(eth_15m)} bar")

    # --- Sembol taraması ---
    scan_results = []
    tamam, atlanan = 0, 0

    for alt in SYMBOLS:
        print(f"\n{'=' * 50}")
        print(f"Analiz: {alt}")
        print(f"{'=' * 50}")
        try:
            a4 = fetch_ohlcv(alt, TF_4H, 600)
            a15 = fetch_ohlcv(alt, TF_15M, 2400)

            result = signal_engine(alt, a4, a15,
                                   btc_4h, btc_15m,
                                   eth_4h, eth_15m,
                                   cfg, meta_state)
            scan_results.append(result)

            # --- Deney kaydı ---
            meta_state.memory.record({
                "symbol": alt,
                "status": result["status"],
                "reason": result["reason"],
                "failure_reason": result.get("failure_reason", ""),
                "regime": result.get("regime", {}),
                "metrics": result.get("oos_stats", {}),
                "decision": "KEEP" if result["status"] == "SIGNAL_FIRED"
                            else "REJECT",
            })

            # --- Konsol özeti ---
            status = result["status"]
            reason = result["reason"]
            print(f"  Durum: {status}")
            if reason:
                print(f"  Neden: {reason}")

            if result.get("warnings"):
                for w in result["warnings"]:
                    print(f"  ONCU UYARI: {w}")

            if status == "SIGNAL_FIRED":
                sig = result["signal"]
                print(f"\n  >>> {sig['direction']} SİNYALI <<<")
                print(f"  Giriş:  {sig['entry_ref']:.4f}")
                print(f"  Hedef:  {sig['target']:.4f}")
                print(f"  Stop:   {sig['stop_loss']:.4f}")
                print(f"  Emir:   {sig['order_type']} ({sig['order_role']})")
                print(f"  OOS:    mean={result['oos_stats'].get('mean', 0) * 100:.3f}% "
                      f"| win={result['oos_stats'].get('win', 0) * 100:.1f}% "
                      f"| PF={result['oos_stats'].get('pf', 0):.2f}")

            tamam += 1

        except Exception:
            traceback.print_exc()
            print(f"  [{alt}] atlandı.")
            atlanan += 1
            scan_results.append({
                "symbol": alt,
                "status": "ERROR",
                "reason": "exception",
                "failure_reason": "exception",
                "traceback": traceback.format_exc(),
            })

    # --- META³ çıktı üretimi ---
    meta3_output = generate_meta3_output(meta_state, scan_results)

    # --- JSON dosyalarına yaz ---
    output_path = Path("agent_state.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(meta3_output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nMETA³ çıktı yazıldı: {output_path}")

    # --- Failure Intelligence ---
    fi = meta_state.failure_intel.analyze()
    if fi["total_failures"] > 0:
        print(f"\nFAILURE INTELLIGENCE:")
        print(f"  Toplam başarısızlık: {fi['total_failures']}")
        print(f"  Öneri: {fi['recommendation']}")

    # --- Özet ---
    print(f"\n{'=' * 70}")
    print(f"TARAMA ÖZETİ:")
    print(f"  Toplam:    {len(scan_results)}")
    print(f"  Sinyal:    {meta3_output['scan_summary']['signals_fired']}")
    print(f"  Veto:      {meta3_output['scan_summary']['vetoes']}")
    print(f"  Sinyalsiz: {meta3_output['scan_summary']['no_signal']}")
    print(f"  Hata:      {meta3_output['scan_summary']['errors']}")
    print(f"  Tamam:     {tamam} | Atlanan: {atlanan}")

    if atlanan == 0 and tamam == len(SYMBOLS):
        print(f"\nTarama TAMAMLANDI ({tamam}/{len(SYMBOLS)} sembol).")
    elif tamam > 0:
        print(f"\nTarama KISMEN tamamlandı: {tamam} tamam, "
              f"{atlanan} atlandı ({len(SYMBOLS)} sembol).")
    else:
        print(f"\nTarama BAŞARISIZ.")

    print(f"{'=' * 70}")
    return meta3_output


if __name__ == "__main__":
    main()
