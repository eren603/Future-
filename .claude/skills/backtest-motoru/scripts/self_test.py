#!/usr/bin/env python3
"""backtest.py için uçtan uca öz-test. Sentetik veriyle çalışır; SELF_TEST_OK basar."""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest as bt  # noqa: E402


def synth_ohlcv(n=600, seed=3):
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0004, 0.01, n)
    close = 100.0 * np.cumprod(1.0 + ret)
    high = close * (1.0 + np.abs(rng.normal(0, 0.003, n)))
    low = close * (1.0 - np.abs(rng.normal(0, 0.003, n)))
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1, 1000, n)})


def _finite(d, keys):
    for k in keys:
        v = d.get(k)
        assert v is None or (isinstance(v, (int, float)) and np.isfinite(v)), f"{k}={v}"


def main():
    frame = synth_ohlcv()
    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "ohlcv.csv"
        frame.to_csv(csv, index=False)

        # 1) SMA cross + Monte Carlo + walk-forward
        job1 = {"input": str(csv), "strategy": {"type": "sma_cross", "fast": 10, "slow": 30},
                "fees_bps": 5, "slippage_bps": 2, "bars_per_year": 8760,
                "monte_carlo": {"runs": 300}, "walk_forward": {"train": 0.7}, "seed": 11}
        r1 = bt.run_job(job1, base=None)
        _finite(r1["metrics"], ["total_return", "max_drawdown", "sharpe", "sortino",
                                "win_rate", "expectancy_per_trade", "final_equity"])
        assert r1["metrics"]["num_trades"] >= 1
        assert r1["monte_carlo"]["runs"] == 300
        _finite(r1["monte_carlo"], ["final_return_p50", "max_dd_p50", "prob_profit"])
        assert "walk_forward" in r1

        # 2) RSI
        job2 = {"input": str(csv), "strategy": {"type": "rsi", "period": 14, "buy_below": 35, "sell_above": 65},
                "allow_short": True, "bars_per_year": 8760}
        r2 = bt.run_job(job2, base=None)
        _finite(r2["metrics"], ["total_return", "sharpe", "max_drawdown"])

        # 3) signal_column (harici sinyal)
        frame2 = frame.copy()
        frame2["signal"] = np.where(frame2["close"] > frame2["close"].rolling(20).mean(), 1, -1)
        csv2 = Path(td) / "sig.csv"
        frame2.to_csv(csv2, index=False)
        job3 = {"input": str(csv2), "strategy": {"type": "signal_column", "column": "signal"},
                "bars_per_year": 8760, "monte_carlo": {"runs": 100}}
        r3 = bt.run_job(job3, base=None)
        _finite(r3["metrics"], ["total_return", "profit_factor", "exposure"])
        assert 0.0 <= r3["metrics"]["exposure"] <= 1.0

        # 4) YÖN DOĞRULUĞU — işaret hatası olmadığının kanıtı.
        #    Kesin yükselen fiyatta: LONG kâr, SHORT zarar; düşende tam tersi.
        up = 100.0 * np.cumprod(np.full(80, 1.005))
        dn = 100.0 * np.cumprod(np.full(80, 0.995))

        def _dir_ret(prices, sig):
            d = pd.DataFrame({"open": prices, "high": prices, "low": prices, "close": prices})
            d["signal"] = float(sig)
            m = bt.run_backtest(d, {"type": "signal_column", "column": "signal"},
                                fees_bps=0, slippage_bps=0)
            return m["total_return"]

        assert _dir_ret(up, 1.0) > 0,  "long, yükselen piyasada kâr etmeli"
        assert _dir_ret(up, -1.0) < 0, "short, yükselen piyasada zarar etmeli"
        assert _dir_ret(dn, -1.0) > 0, "short, düşen piyasada kâr etmeli"
        assert _dir_ret(dn, 1.0) < 0,  "long, düşen piyasada zarar etmeli"

    print("SELF_TEST_OK: sma_cross, rsi, signal_column, monte_carlo, walk_forward, yon-isareti")


if __name__ == "__main__":
    main()
