#!/usr/bin/env python3
"""Kendi içinde çalışan vektörel backtest motoru (pandas/numpy — harici bağımlılık yok).

Girdi: JSON job.
  {
    "input": "ohlcv.csv",            # kolonlar: (timestamp?), open, high, low, close, volume?
    "strategy": {...},               # aşağıdaki tiplerden biri
    "fees_bps": 5.0, "slippage_bps": 2.0,
    "allow_short": true,
    "bars_per_year": 8760,           # saatlik kripto=8760, günlük=252
    "monte_carlo": {"runs": 1000},   # opsiyonel
    "walk_forward": {"train": 0.7}   # opsiyonel
  }
Strateji tipleri:
  {"type": "sma_cross", "fast": 20, "slow": 50}
  {"type": "rsi", "period": 14, "buy_below": 30, "sell_above": 70}
  {"type": "signal_column", "column": "signal"}   # 1=long 0=flat -1=short

Çıktı: metrikler + işlem özeti + Monte Carlo yüzdelikleri (JSON).
Determinist: Monte Carlo seed=job.get("seed", 7).
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


class BacktestError(Exception):
    pass


def load_ohlcv(source: str, base: Path | None) -> pd.DataFrame:
    path = Path(str(source)).expanduser()
    if base is not None and not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_file():
        raise BacktestError(f"OHLCV dosyası yok: {path}")
    suffix = path.suffix.lower()
    if suffix in (".csv", ".tsv", ".txt"):
        frame = pd.read_csv(path, sep=None, engine="python")
    elif suffix in (".json", ".jsonl"):
        frame = pd.read_json(path, lines=(suffix == ".jsonl"))
    else:
        raise BacktestError(f"Desteklenmeyen uzantı: {suffix}")
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    if "close" not in frame.columns:
        raise BacktestError("OHLCV en az 'close' kolonu içermeli")
    return frame


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(int(n), min_periods=int(n)).mean()


def rsi(series: pd.Series, n: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / int(n), min_periods=int(n), adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / int(n), min_periods=int(n), adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.fillna(50.0)


def build_signal(frame: pd.DataFrame, strategy: dict, allow_short: bool) -> pd.Series:
    kind = str(strategy.get("type", "")).lower()
    close = frame["close"].astype(float)
    if kind == "sma_cross":
        fast = sma(close, strategy.get("fast", 20))
        slow = sma(close, strategy.get("slow", 50))
        sig = np.where(fast > slow, 1.0, -1.0 if allow_short else 0.0)
        sig = pd.Series(sig, index=frame.index).where(fast.notna() & slow.notna(), 0.0)
        return sig
    if kind == "rsi":
        r = rsi(close, strategy.get("period", 14))
        buy_below = float(strategy.get("buy_below", 30))
        sell_above = float(strategy.get("sell_above", 70))
        raw = np.where(r < buy_below, 1.0, np.where(r > sell_above, (-1.0 if allow_short else 0.0), np.nan))
        sig = pd.Series(raw, index=frame.index).ffill().fillna(0.0)
        return sig
    if kind == "signal_column":
        col = str(strategy.get("column", "signal")).lower()
        if col not in frame.columns:
            raise BacktestError(f"signal_column: '{col}' kolonu yok")
        sig = frame[col].astype(float).clip(-1.0, 1.0)
        if not allow_short:
            sig = sig.clip(lower=0.0)
        return sig.fillna(0.0)
    raise BacktestError(f"Bilinmeyen strateji tipi: {kind}")


def run_backtest(frame: pd.DataFrame, strategy: dict, *, fees_bps=5.0, slippage_bps=2.0,
                 allow_short=True, bars_per_year=8760) -> dict:
    close = frame["close"].astype(float).reset_index(drop=True)
    if len(close) < 5:
        raise BacktestError("En az 5 bar gerekli")
    signal = build_signal(frame.reset_index(drop=True), strategy, allow_short).reset_index(drop=True)
    # Pozisyon bir sonraki barda uygulanır (lookahead engelleme)
    position = signal.shift(1).fillna(0.0)
    ret = close.pct_change().fillna(0.0)
    gross = position * ret
    # İşlem maliyeti: pozisyon değişiminde |Δpos| * (fee+slippage)
    cost_rate = (float(fees_bps) + float(slippage_bps)) / 10000.0
    turnover = position.diff().abs().fillna(position.abs())
    costs = turnover * cost_rate
    net = gross - costs
    equity = (1.0 + net).cumprod()

    # İşlem listesi (pozisyon 0-dışı segmentleri)
    trades = []
    pos_arr = position.to_numpy()
    entry_i = None
    entry_px = None
    side = 0
    for i in range(len(pos_arr)):
        p = pos_arr[i]
        if entry_i is None and p != 0:
            entry_i, entry_px, side = i, close.iloc[i], int(np.sign(p))
        elif entry_i is not None and (p == 0 or np.sign(p) != side or i == len(pos_arr) - 1):
            exit_px = close.iloc[i]
            raw_r = side * (exit_px / entry_px - 1.0)
            net_r = raw_r - 2 * cost_rate
            trades.append({"entry_i": entry_i, "exit_i": i, "side": side,
                           "entry": round(float(entry_px), 8), "exit": round(float(exit_px), 8),
                           "return": round(float(net_r), 6)})
            if p != 0 and np.sign(p) == side:
                pass
            entry_i = None if p == 0 else i
            entry_px = None if p == 0 else close.iloc[i]
            side = 0 if p == 0 else int(np.sign(p))

    trade_returns = np.array([t["return"] for t in trades], dtype=float)
    wins = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns < 0]

    total_return = float(equity.iloc[-1] - 1.0)
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_dd = float(drawdown.min())

    mean_r = float(net.mean())
    std_r = float(net.std(ddof=1)) if len(net) > 1 else 0.0
    ann = math.sqrt(float(bars_per_year))
    sharpe = float(mean_r / std_r * ann) if std_r > 0 else 0.0
    downside = net[net < 0]
    dstd = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sortino = float(mean_r / dstd * ann) if dstd > 0 else 0.0

    gross_win = float(wins.sum())
    gross_loss = float(-losses.sum())
    profit_factor = float(gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    win_rate = float(len(wins) / len(trade_returns)) if len(trade_returns) else 0.0
    expectancy = float(trade_returns.mean()) if len(trade_returns) else 0.0
    exposure = float((position != 0).mean())

    return {
        "bars": int(len(close)),
        "total_return": round(total_return, 6),
        "max_drawdown": round(max_dd, 6),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "num_trades": int(len(trade_returns)),
        "win_rate": round(win_rate, 4),
        "profit_factor": (round(profit_factor, 4) if math.isfinite(profit_factor) else None),
        "expectancy_per_trade": round(expectancy, 6),
        "avg_win": round(float(wins.mean()), 6) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 6) if len(losses) else 0.0,
        "exposure": round(exposure, 4),
        "final_equity": round(float(equity.iloc[-1]), 6),
        "_trade_returns": trade_returns.tolist(),
    }


def monte_carlo(trade_returns: list[float], runs: int, seed: int) -> dict:
    r = np.array(trade_returns, dtype=float)
    if len(r) < 3:
        return {"note": "Yetersiz işlem sayısı (Monte Carlo atlandı)", "runs": 0}
    rng = np.random.default_rng(int(seed))
    finals = np.empty(int(runs))
    max_dds = np.empty(int(runs))
    for k in range(int(runs)):
        shuffled = rng.permutation(r)
        eq = np.cumprod(1.0 + shuffled)
        finals[k] = eq[-1] - 1.0
        rollmax = np.maximum.accumulate(eq)
        max_dds[k] = float((eq / rollmax - 1.0).min())
    pct = lambda a, q: round(float(np.percentile(a, q)), 6)
    return {
        "runs": int(runs),
        "final_return_p5": pct(finals, 5), "final_return_p50": pct(finals, 50), "final_return_p95": pct(finals, 95),
        "max_dd_p5": pct(max_dds, 5), "max_dd_p50": pct(max_dds, 50), "max_dd_p95": pct(max_dds, 95),
        "prob_profit": round(float((finals > 0).mean()), 4),
    }


def run_job(job: dict, base: Path | None) -> dict:
    frame = load_ohlcv(job["input"], base)
    metrics = run_backtest(
        frame, job["strategy"],
        fees_bps=job.get("fees_bps", 5.0), slippage_bps=job.get("slippage_bps", 2.0),
        allow_short=bool(job.get("allow_short", True)), bars_per_year=job.get("bars_per_year", 8760),
    )
    trade_returns = metrics.pop("_trade_returns")
    report = {"metrics": metrics}

    mc = job.get("monte_carlo")
    if mc:
        report["monte_carlo"] = monte_carlo(trade_returns, mc.get("runs", 1000), job.get("seed", 7))

    wf = job.get("walk_forward")
    if wf:
        train_frac = float(wf.get("train", 0.7))
        n = len(frame)
        cut = int(n * train_frac)
        if cut >= 5 and (n - cut) >= 5:
            tr = run_backtest(frame.iloc[:cut], job["strategy"], fees_bps=job.get("fees_bps", 5.0),
                              slippage_bps=job.get("slippage_bps", 2.0), allow_short=bool(job.get("allow_short", True)),
                              bars_per_year=job.get("bars_per_year", 8760))
            te = run_backtest(frame.iloc[cut:], job["strategy"], fees_bps=job.get("fees_bps", 5.0),
                              slippage_bps=job.get("slippage_bps", 2.0), allow_short=bool(job.get("allow_short", True)),
                              bars_per_year=job.get("bars_per_year", 8760))
            report["walk_forward"] = {
                "train": {"total_return": tr["total_return"], "sharpe": tr["sharpe"], "num_trades": tr["num_trades"]},
                "test": {"total_return": te["total_return"], "sharpe": te["sharpe"], "num_trades": te["num_trades"]},
                "consistent": bool(tr["total_return"] > 0 and te["total_return"] > 0),
            }
        else:
            report["walk_forward"] = {"note": "Bölme için yetersiz veri"}
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Vektörel backtest motoru")
    ap.add_argument("--job", required=True, help="JSON job dosyası")
    args = ap.parse_args()
    job_path = Path(args.job).expanduser().resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    report = run_job(job, base=job_path.parent)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
