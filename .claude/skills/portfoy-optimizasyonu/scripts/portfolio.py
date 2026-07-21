#!/usr/bin/env python3
"""Portföy optimizasyonu motoru: Markowitz (min-var, max-Sharpe) + HRP.
numpy/scipy — harici bağımlılık yok.

job:
  {"op": "optimize", "returns_csv": "returns.csv", "method": "max_sharpe",
   "bars_per_year": 8760, "long_only": true, "rf": 0.0}
    method: "min_var" | "max_sharpe" | "hrp"
  ya da satır-içi:
  {"op": "optimize", "returns": {"A": [...], "B": [...]}, "method": "hrp", ...}
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform


class PortfolioError(Exception):
    pass


def load_returns(job: dict, base: Path | None) -> pd.DataFrame:
    if "returns_csv" in job:
        path = Path(str(job["returns_csv"])).expanduser()
        if base is not None and not path.is_absolute():
            path = base / path
        frame = pd.read_csv(path.resolve(), sep=None, engine="python")
    elif "returns" in job:
        frame = pd.DataFrame(job["returns"])
    else:
        raise PortfolioError("returns_csv veya returns gerekli")
    frame = frame.select_dtypes(include=[np.number]).dropna()
    if frame.shape[1] < 2:
        raise PortfolioError("En az 2 varlık gerekli")
    if frame.shape[0] < 5:
        raise PortfolioError("En az 5 gözlem gerekli")
    return frame


def _stats(w, mu, cov, ann):
    ret = float(w @ mu) * ann
    vol = float(np.sqrt(w @ cov @ w)) * np.sqrt(ann)
    return ret, vol


def markowitz(returns: pd.DataFrame, method: str, ann: float, long_only: bool, rf: float) -> dict:
    mu = returns.mean().to_numpy()
    cov = returns.cov().to_numpy()
    n = len(mu)
    w0 = np.repeat(1.0 / n, n)
    bounds = tuple((0.0, 1.0) for _ in range(n)) if long_only else tuple((-1.0, 1.0) for _ in range(n))
    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)

    if method == "min_var":
        obj = lambda w: w @ cov @ w
    elif method == "max_sharpe":
        def obj(w):
            ret = w @ mu * ann - rf
            vol = np.sqrt(w @ cov @ w) * np.sqrt(ann)
            return -ret / vol if vol > 0 else 1e9
    else:
        raise PortfolioError(f"Bilinmeyen markowitz method: {method}")

    res = minimize(obj, w0, method="SLSQP", bounds=bounds, constraints=cons,
                   options={"maxiter": 500, "ftol": 1e-10})
    w = res.x / res.x.sum()
    ret, vol = _stats(w, mu, cov, ann)
    sharpe = (ret - rf) / vol if vol > 0 else 0.0
    return {"method": method, "weights": _wdict(returns.columns, w),
            "expected_return": round(ret, 6), "volatility": round(vol, 6),
            "sharpe": round(float(sharpe), 4)}


def hrp(returns: pd.DataFrame, ann: float) -> dict:
    """Hierarchical Risk Parity (López de Prado)."""
    corr = returns.corr().to_numpy()
    cov = returns.cov().to_numpy()
    cols = list(returns.columns)
    dist = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")
    order = leaves_list(link)

    # Recursive bisection
    w = pd.Series(1.0, index=range(len(cols)))
    clusters = [list(order)]
    while clusters:
        clusters = [c[j:k] for c in clusters for j, k in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for i in range(0, len(clusters), 2):
            c0, c1 = clusters[i], clusters[i + 1]
            v0 = _cluster_var(cov, c0)
            v1 = _cluster_var(cov, c1)
            alpha = 1.0 - v0 / (v0 + v1)
            w[c0] *= alpha
            w[c1] *= (1.0 - alpha)
    weights = w.to_numpy()
    weights = weights / weights.sum()
    mu = returns.mean().to_numpy()
    ret, vol = _stats(weights, mu, cov, ann)
    sharpe = ret / vol if vol > 0 else 0.0
    return {"method": "hrp", "weights": _wdict(cols, weights),
            "expected_return": round(ret, 6), "volatility": round(vol, 6),
            "sharpe": round(float(sharpe), 4), "leaf_order": [cols[i] for i in order]}


def _cluster_var(cov, idx):
    sub = cov[np.ix_(idx, idx)]
    ivp = 1.0 / np.diag(sub)
    ivp = ivp / ivp.sum()
    return float(ivp @ sub @ ivp)


def _wdict(cols, w):
    return {str(c): round(float(x), 6) for c, x in zip(cols, w)}


def run_job(job: dict, base: Path | None) -> dict:
    returns = load_returns(job, base)
    method = str(job.get("method", "max_sharpe")).lower()
    ann = float(job.get("bars_per_year", 252))
    if method == "hrp":
        out = hrp(returns, ann)
    else:
        out = markowitz(returns, method, ann, bool(job.get("long_only", True)), float(job.get("rf", 0.0)))
    out["assets"] = list(map(str, returns.columns))
    out["observations"] = int(len(returns))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Portföy optimizasyonu")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    p = Path(args.job).expanduser().resolve()
    job = json.loads(p.read_text(encoding="utf-8"))
    print(json.dumps(run_job(job, base=p.parent), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
