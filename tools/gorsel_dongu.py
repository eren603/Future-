#!/usr/bin/env python3
"""İteratif görsel/sinyal geri-besleme döngüsü — KAPALI LOOP.

Grafik OKUMA tek atış değil: sinyal üret → hedefe göre PUANLA → parametreyi
AYARLA → tekrar. Yakınsayana ya da max_iter'e kadar döner. Böylece "screenshot →
düzelt → tekrar" döngüsünün programatik (ölçülebilir) karşılığı olur.

numpy — harici bağımlılık yok. Serbest ayar (aşırı-uyum) DEĞİL: tek bir hedef
fonksiyonu + korkuluklu adım; her adım loglanır ve gerekçelenir.

Kullanım:
  python3 gorsel_dongu.py --job job.json
  job = {"high":[...], "low":[...], "close":[...],
         "target_rr": 2.0,            # hedef risk:ödül
         "max_iter": 12, "tol": 0.02}
  (ya da run_loop() import et)
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np


class DonguError(Exception):
    pass


def _atr(high, low, close, n=14):
    high, low, close = map(np.asarray, (high, low, close))
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    if len(tr) < n:
        return float(np.mean(tr))
    return float(np.mean(tr[-n:]))


def _signal_score(high, low, close, fib_level: float, atr_mult: float,
                  target_rr: float) -> dict:
    """Golden-zone girişini fib_level ile kur, ATR-stop ile R:R hesapla,
    hedef R:R'ye uzaklığı PUANLA (0 = tam isabet)."""
    close = np.asarray(close, dtype=float)
    swing_hi = float(np.max(high[-50:] if len(high) >= 50 else high))
    swing_lo = float(np.min(low[-50:] if len(low) >= 50 else low))
    rng = swing_hi - swing_lo
    if rng <= 0:
        raise DonguError("VERİ YOK: swing aralığı sıfır")
    entry = swing_lo + fib_level * rng          # long retracement girişi
    atr = _atr(high, low, close)
    stop = entry - atr_mult * atr
    risk = entry - stop
    if risk <= 0:
        raise DonguError("risk<=0")
    take = swing_hi                              # hedef: swing tepe
    reward = take - entry
    rr = reward / risk
    err = abs(rr - target_rr)
    return {"entry": round(entry, 6), "stop": round(stop, 6),
            "take": round(take, 6), "rr": round(rr, 4),
            "atr": round(atr, 6), "error": round(err, 6)}


def run_loop(job: dict) -> dict:
    for k in ("high", "low", "close"):
        if k not in job or not job[k]:
            raise DonguError(f"VERİ YOK: '{k}' gerekli")
    high = np.asarray(job["high"], dtype=float)
    low = np.asarray(job["low"], dtype=float)
    close = np.asarray(job["close"], dtype=float)
    target_rr = float(job.get("target_rr", 2.0))
    max_iter = int(job.get("max_iter", 12))
    tol = float(job.get("tol", 0.02))

    # başlangıç: golden zone ortası (0.618) + 1.0 ATR stop
    fib, atr_mult = 0.618, 1.0
    fib_lo, fib_hi = 0.50, 0.786          # OTE korkulukları (SMC golden zone)
    trace, best = [], None
    for it in range(1, max_iter + 1):
        s = _signal_score(high, low, close, fib, atr_mult, target_rr)
        step = {"iter": it, "fib_level": round(fib, 4),
                "atr_mult": round(atr_mult, 4), **s}
        trace.append(step)
        if best is None or s["error"] < best["error"]:
            best = step
        if s["error"] <= tol:
            step["converged"] = True
            break
        # geri-besleme: R:R hedeften düşükse girişi derinleştir (fib↑) ve stop'u
        # sıkılaştır (atr_mult↓); yüksekse tersi. Korkuluk içinde kal.
        if s["rr"] < target_rr:
            fib = min(fib_hi, fib + 0.02)
            atr_mult = max(0.5, atr_mult - 0.05)
        else:
            fib = max(fib_lo, fib - 0.02)
            atr_mult = min(2.0, atr_mult + 0.05)

    return {"op": "gorsel_dongu", "target_rr": target_rr,
            "iterations": len(trace), "converged": best.get("converged", False),
            "best": best, "trace": trace,
            "esik_kaynagi": "OTE golden-zone korkuluğu (0.50–0.786) + ATR-stop; "
                            "hedef R:R'ye kapalı-loop yakınsama"}


def main() -> int:
    ap = argparse.ArgumentParser(description="İteratif görsel/sinyal döngüsü")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    try:
        print(json.dumps(run_loop(job), ensure_ascii=False, indent=2))
    except DonguError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
