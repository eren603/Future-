#!/usr/bin/env python3
"""Risk yönetimi & pozisyon boyutlandırma motoru (numpy/scipy — harici bağımlılık yok).

Kullanım: python risk.py --job job.json   (ya da fonksiyonları import et)
job.op alanına göre çalışır:

  {"op": "position_size", "method": "fixed_fractional",
   "equity": 10000, "risk_pct": 1.0, "entry": 100, "stop": 98}

  {"op": "position_size", "method": "kelly",
   "win_rate": 0.55, "avg_win": 0.02, "avg_loss": 0.01, "fraction": 0.5}

  {"op": "position_size", "method": "vol_target",
   "equity": 10000, "target_vol": 0.20, "asset_vol": 0.60, "bars_per_year": 8760}

  {"op": "var", "returns": [...], "alpha": 0.95}          # tarihsel VaR/CVaR

  {"op": "drawdown", "equity_curve": [...] }               # maks düşüş & süre
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


class RiskError(Exception):
    pass


def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Kelly = W - (1-W)/R, R = avg_win/avg_loss (pozitif büyüklükler)."""
    w = float(win_rate)
    aw, al = abs(float(avg_win)), abs(float(avg_loss))
    if al == 0:
        raise RiskError("avg_loss sıfır olamaz")
    r = aw / al
    k = w - (1.0 - w) / r
    return float(k)


def position_size(job: dict) -> dict:
    method = str(job.get("method", "")).lower()
    if method == "fixed_fractional":
        equity = float(job["equity"]); risk_pct = float(job["risk_pct"]) / 100.0
        entry = float(job["entry"]); stop = float(job["stop"])
        per_unit_risk = abs(entry - stop)
        if per_unit_risk == 0:
            raise RiskError("entry ve stop eşit olamaz")
        risk_amount = equity * risk_pct
        units = risk_amount / per_unit_risk
        notional = units * entry
        return {"method": method, "risk_amount": round(risk_amount, 4),
                "units": round(units, 8), "notional": round(notional, 4),
                "notional_pct_of_equity": round(notional / equity * 100.0, 2),
                "r_per_unit": round(per_unit_risk, 8)}
    if method == "kelly":
        k = kelly_fraction(job["win_rate"], job["avg_win"], job["avg_loss"])
        frac = float(job.get("fraction", 0.5))  # yarım-Kelly varsayılan (güvenlik)
        applied = max(0.0, k) * frac
        return {"method": method, "full_kelly": round(k, 4),
                "applied_fraction": round(applied, 4),
                "note": ("Negatif Kelly: kenar yok, pozisyon açma" if k <= 0
                         else f"{frac:g}x-Kelly uygulandı (aşırı kaldıraçtan kaçın)")}
    if method == "vol_target":
        equity = float(job["equity"]); target = float(job["target_vol"]); av = float(job["asset_vol"])
        if av == 0:
            raise RiskError("asset_vol sıfır olamaz")
        leverage = target / av
        notional = equity * leverage
        return {"method": method, "leverage": round(leverage, 4),
                "notional": round(notional, 4),
                "note": ("Kaldıraç>1: marjin/futures gerekir" if leverage > 1 else "Nakit-altı pozisyon")}
    raise RiskError(f"Bilinmeyen method: {method}")


def var_cvar(job: dict) -> dict:
    r = np.array(job["returns"], dtype=float)
    if r.size < 5:
        raise RiskError("VaR için en az 5 getiri gerekli")
    alpha = float(job.get("alpha", 0.95))
    q = np.percentile(r, (1.0 - alpha) * 100.0)   # sol kuyruk
    tail = r[r <= q]
    cvar = float(tail.mean()) if tail.size else float(q)
    return {"alpha": alpha, "n": int(r.size),
            "var": round(float(q), 6), "cvar": round(cvar, 6),
            "mean": round(float(r.mean()), 6), "std": round(float(r.std(ddof=1)), 6),
            "note": "VaR/CVaR negatif = kayıp; tarihsel (parametresiz) yöntem"}


def drawdown(job: dict) -> dict:
    eq = np.array(job["equity_curve"], dtype=float)
    if eq.size < 2:
        raise RiskError("En az 2 nokta gerekli")
    rollmax = np.maximum.accumulate(eq)
    dd = eq / rollmax - 1.0
    max_dd = float(dd.min())
    trough = int(dd.argmin())
    peak = int(rollmax[:trough + 1].argmax()) if trough > 0 else 0
    return {"max_drawdown": round(max_dd, 6), "peak_index": peak, "trough_index": trough,
            "drawdown_length_bars": int(trough - peak),
            "final_equity": round(float(eq[-1]), 6)}


def run_job(job: dict) -> dict:
    op = str(job.get("op", "")).lower()
    if op == "position_size":
        return position_size(job)
    if op == "var":
        return var_cvar(job)
    if op == "drawdown":
        return drawdown(job)
    raise RiskError(f"Bilinmeyen op: {op}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Risk yönetimi motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(run_job(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
