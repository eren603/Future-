#!/usr/bin/env python3
"""risk.py öz-testi. SELF_TEST_OK basar."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import risk  # noqa: E402


def main():
    # 1) fixed fractional: 10k, %1 risk, 100->98 stop => risk 100$, 50 birim
    r = risk.run_job({"op": "position_size", "method": "fixed_fractional",
                      "equity": 10000, "risk_pct": 1.0, "entry": 100, "stop": 98})
    assert abs(r["risk_amount"] - 100.0) < 1e-6, r
    assert abs(r["units"] - 50.0) < 1e-6, r

    # 2) kelly: bilinen değer W=0.6, aw=al => K = 0.6-0.4 = 0.2
    r = risk.run_job({"op": "position_size", "method": "kelly",
                      "win_rate": 0.6, "avg_win": 0.01, "avg_loss": 0.01, "fraction": 0.5})
    assert abs(r["full_kelly"] - 0.2) < 1e-9, r
    assert abs(r["applied_fraction"] - 0.1) < 1e-9, r
    # negatif kenar
    rn = risk.run_job({"op": "position_size", "method": "kelly",
                       "win_rate": 0.4, "avg_win": 0.01, "avg_loss": 0.01})
    assert rn["applied_fraction"] == 0.0, rn

    # 3) vol target
    r = risk.run_job({"op": "position_size", "method": "vol_target",
                      "equity": 10000, "target_vol": 0.20, "asset_vol": 0.40})
    assert abs(r["leverage"] - 0.5) < 1e-9, r

    # 4) VaR/CVaR
    rng = np.random.default_rng(1)
    rets = rng.normal(0, 0.02, 500).tolist()
    r = risk.run_job({"op": "var", "returns": rets, "alpha": 0.95})
    assert r["var"] < 0 and r["cvar"] <= r["var"], r

    # 5) drawdown: bilinen eğri
    r = risk.run_job({"op": "drawdown", "equity_curve": [1.0, 1.2, 0.9, 1.1, 1.3]})
    assert abs(r["max_drawdown"] - (0.9 / 1.2 - 1.0)) < 1e-9, r
    assert r["peak_index"] == 1 and r["trough_index"] == 2, r

    print("SELF_TEST_OK: fixed_fractional, kelly, vol_target, var/cvar, drawdown")


if __name__ == "__main__":
    main()
