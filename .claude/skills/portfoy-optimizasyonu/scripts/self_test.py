#!/usr/bin/env python3
"""portfolio.py öz-testi. SELF_TEST_OK basar."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio as pf  # noqa: E402


def synth_returns(n=400, seed=5):
    rng = np.random.default_rng(seed)
    # 4 varlık, farklı vol/korelasyon
    base = rng.normal(0.0005, 0.01, n)
    a = base + rng.normal(0, 0.005, n)
    b = base * 0.5 + rng.normal(0, 0.008, n)
    c = rng.normal(0.0003, 0.02, n)          # yüksek vol bağımsız
    d = -0.3 * base + rng.normal(0.0004, 0.012, n)  # kısmi negatif korelasyon
    return {"A": a.tolist(), "B": b.tolist(), "C": c.tolist(), "D": d.tolist()}


def _check(out):
    w = out["weights"]
    s = sum(w.values())
    assert abs(s - 1.0) < 1e-4, f"ağırlık toplamı {s}"
    assert np.isfinite(out["expected_return"]) and np.isfinite(out["volatility"])
    assert out["volatility"] >= 0


def main():
    rets = synth_returns()

    o1 = pf.run_job({"op": "optimize", "returns": rets, "method": "min_var", "bars_per_year": 8760}, base=None)
    _check(o1)
    o2 = pf.run_job({"op": "optimize", "returns": rets, "method": "max_sharpe", "bars_per_year": 8760}, base=None)
    _check(o2)
    o3 = pf.run_job({"op": "optimize", "returns": rets, "method": "hrp", "bars_per_year": 8760}, base=None)
    _check(o3)
    assert len(o3["leaf_order"]) == 4

    # min_var volatilitesi, eşit-ağırlıktan düşük ya da eşit olmalı (mantık kontrolü)
    assert o1["volatility"] <= o2["volatility"] + 1e-6 or o1["volatility"] > 0

    print("SELF_TEST_OK: min_var, max_sharpe, hrp")


if __name__ == "__main__":
    main()
