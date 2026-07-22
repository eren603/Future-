#!/usr/bin/env python3
"""Değerleme & model-denetim motoru (numpy — harici bağımlılık yok).

anthropics/financial-analysis eklentisindeki dcf-model / comps-analysis /
audit-xls mantığının hafif, çalışan karşılığı. Kullanıcı verisi yoksa "VERİ YOK"
(fail-closed) — hayalden sayı üretilmez.

Kullanım: python degerleme.py --job job.json   (ya da run_job'ı import et)
job.op alanına göre çalışır:

  # 1) DCF — Gordon terminal (varsayılan) veya exit-çarpanı
  {"op": "dcf",
   "fcf": [100, 110, 121, 133, 146],        # ya da: "fcf0"+"growth"+"years"
   "wacc": 0.10, "terminal_growth": 0.025,
   "net_debt": 200, "shares": 50}
  # exit-çarpanı ile terminal:
  {"op": "dcf", "fcf": [...], "wacc": 0.10,
   "exit_multiple": 8, "terminal_metric": 160, "net_debt": 200, "shares": 50}
  # WACC bileşenlerden (wacc verilmezse):
  {"op": "dcf", "fcf": [...], "terminal_growth": 0.02,
   "wacc_parts": {"equity": 800, "debt": 200, "cost_equity": 0.12,
                  "cost_debt": 0.06, "tax": 0.25}, ...}

  # 2) Comps — benzer şirket çarpanları → ima değer aralığı
  {"op": "comps",
   "peers": [{"name":"A","ev_ebitda":9,"pe":15},
             {"name":"B","ev_ebitda":11,"pe":18}],
   "target": {"ebitda": 100, "net_income": 40},
   "net_debt": 200, "shares": 50}

  # 3) Audit — 3-tablo tutarlılık denetimi (formül/denge kontrolü)
  {"op": "audit",
   "periods": [
     {"label":"2024","assets":1000,"liabilities":600,"equity":400,
      "cash_begin":50,"cash_end":80,"cf_operating":100,"cf_investing":-60,
      "cf_financing":-10}
   ]}
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np


class DegerlemeError(Exception):
    pass


def _need(job: dict, key: str):
    if key not in job or job[key] is None:
        raise DegerlemeError(f"VERİ YOK: '{key}' gerekli — hayalden üretilmez")
    return job[key]


# --------------------------------------------------------------------------- #
# WACC
# --------------------------------------------------------------------------- #
def compute_wacc(parts: dict) -> float:
    """WACC = E/V*Re + D/V*Rd*(1-T). Büyüklükler pozitif piyasa/def. değerleri."""
    e = float(_need(parts, "equity"))
    d = float(_need(parts, "debt"))
    re = float(_need(parts, "cost_equity"))
    rd = float(_need(parts, "cost_debt"))
    tax = float(parts.get("tax", 0.0))
    v = e + d
    if v <= 0:
        raise DegerlemeError("equity+debt sıfır/negatif olamaz")
    return (e / v) * re + (d / v) * rd * (1.0 - tax)


# --------------------------------------------------------------------------- #
# DCF
# --------------------------------------------------------------------------- #
def _project_fcf(job: dict) -> list[float]:
    if "fcf" in job and job["fcf"]:
        fcf = [float(x) for x in job["fcf"]]
        if len(fcf) == 0:
            raise DegerlemeError("VERİ YOK: 'fcf' boş")
        return fcf
    fcf0 = float(_need(job, "fcf0"))
    growth = float(_need(job, "growth"))
    years = int(_need(job, "years"))
    if years <= 0:
        raise DegerlemeError("'years' pozitif olmalı")
    return [fcf0 * (1.0 + growth) ** t for t in range(1, years + 1)]


def _dcf_value(fcf: list[float], wacc: float, job: dict) -> dict:
    if wacc <= -1.0:
        raise DegerlemeError("WACC geçersiz")
    n = len(fcf)
    disc = [(1.0 + wacc) ** t for t in range(1, n + 1)]
    pv_fcf = [f / d for f, d in zip(fcf, disc)]

    # Terminal değer
    if "exit_multiple" in job:
        tm = float(_need(job, "terminal_metric"))
        tv = float(job["exit_multiple"]) * tm
        terminal_method = "exit_multiple"
    else:
        g = float(_need(job, "terminal_growth"))
        if wacc <= g:
            raise DegerlemeError("Gordon: WACC > terminal_growth olmalı")
        tv = fcf[-1] * (1.0 + g) / (wacc - g)
        terminal_method = "gordon"
    pv_tv = tv / disc[-1]

    ev = float(sum(pv_fcf) + pv_tv)
    net_debt = float(job.get("net_debt", 0.0))
    equity = ev - net_debt
    out = {
        "enterprise_value": round(ev, 4),
        "pv_fcf_sum": round(float(sum(pv_fcf)), 4),
        "terminal_value": round(tv, 4),
        "pv_terminal": round(pv_tv, 4),
        "terminal_method": terminal_method,
        "equity_value": round(equity, 4),
        "wacc": round(wacc, 6),
    }
    if "shares" in job and float(job["shares"]) > 0:
        out["per_share"] = round(equity / float(job["shares"]), 6)
    return out


def dcf(job: dict) -> dict:
    fcf = _project_fcf(job)
    if "wacc" in job and job["wacc"] is not None:
        wacc = float(job["wacc"])
    elif "wacc_parts" in job:
        wacc = compute_wacc(job["wacc_parts"])
    else:
        raise DegerlemeError("VERİ YOK: 'wacc' ya da 'wacc_parts' gerekli")
    base = _dcf_value(fcf, wacc, job)

    # Duyarlılık: WACC × terminal_growth (Gordon ise) — merkez ± adım
    sens = None
    if "exit_multiple" not in job and "terminal_growth" in job:
        g0 = float(job["terminal_growth"])
        wacc_axis = [round(wacc + d, 4) for d in (-0.01, -0.005, 0.0, 0.005, 0.01)]
        g_axis = [round(g0 + d, 4) for d in (-0.01, -0.005, 0.0, 0.005, 0.01)]
        grid = []
        for w in wacc_axis:
            row = []
            for g in g_axis:
                try:
                    j2 = dict(job); j2["wacc"] = w; j2["terminal_growth"] = g
                    v = _dcf_value(fcf, w, j2)
                    row.append(v.get("per_share", v["equity_value"]))
                except DegerlemeError:
                    row.append(None)  # geçersiz (WACC<=g) → boş
            grid.append(row)
        sens = {"wacc_axis": wacc_axis, "growth_axis": g_axis,
                "metric": "per_share" if "shares" in job else "equity_value",
                "grid": grid}
    return {"op": "dcf", "fcf_projection": [round(x, 4) for x in fcf],
            **base, "sensitivity": sens,
            "esik_kaynagi": "kullanıcı girdisi (varsayımlar açık listelenmeli)"}


# --------------------------------------------------------------------------- #
# Comps
# --------------------------------------------------------------------------- #
_MULT_TO_METRIC = {  # çarpan adı -> hedef metrik alanı, değer tabanı
    "ev_ebitda": ("ebitda", "ev"),
    "ev_sales": ("sales", "ev"),
    "ev_ebit": ("ebit", "ev"),
    "pe": ("net_income", "equity"),
    "pb": ("book_value", "equity"),
}


def _quantiles(vals: list[float]) -> dict:
    a = np.array([v for v in vals if v is not None and np.isfinite(v)], dtype=float)
    if a.size == 0:
        return {"n": 0, "median": None, "q1": None, "q3": None,
                "min": None, "max": None}
    return {"n": int(a.size),
            "median": round(float(np.median(a)), 6),
            "q1": round(float(np.percentile(a, 25)), 6),
            "q3": round(float(np.percentile(a, 75)), 6),
            "min": round(float(a.min()), 6),
            "max": round(float(a.max()), 6)}


def comps(job: dict) -> dict:
    peers = _need(job, "peers")
    target = _need(job, "target")
    if not isinstance(peers, list) or len(peers) == 0:
        raise DegerlemeError("VERİ YOK: 'peers' boş")
    net_debt = float(job.get("net_debt", 0.0))
    shares = float(job["shares"]) if "shares" in job else None

    stats, implied = {}, {}
    for mult, (metric_key, base) in _MULT_TO_METRIC.items():
        vals = [p.get(mult) for p in peers if p.get(mult) is not None]
        if not vals:
            continue
        q = _quantiles([float(v) for v in vals])
        stats[mult] = q
        tv = target.get(metric_key)
        if tv is None or q["median"] is None:
            continue  # hedef metrik yoksa ima değer üretme (VERİ YOK)
        tv = float(tv)
        rng = {}
        for tag, mv in (("low", q["q1"]), ("mid", q["median"]), ("high", q["q3"])):
            if mv is None:
                continue
            gross = mv * tv  # EV ya da equity
            equity = gross - net_debt if base == "ev" else gross
            entry = {"multiple": round(mv, 6),
                     ("ev" if base == "ev" else "equity_value"): round(gross, 4),
                     "equity_value": round(equity, 4)}
            if shares and shares > 0:
                entry["per_share"] = round(equity / shares, 6)
            rng[tag] = entry
        implied[mult] = rng

    if not stats:
        raise DegerlemeError("VERİ YOK: peer'larda tanınan çarpan yok "
                             "(ev_ebitda/ev_sales/ev_ebit/pe/pb)")
    return {"op": "comps", "peer_count": len(peers),
            "multiple_stats": stats, "implied_value": implied,
            "esik_kaynagi": "peer medyan/çeyreklik (istatistik türetildi)"}


# --------------------------------------------------------------------------- #
# Audit — 3-tablo tutarlılık denetimi
# --------------------------------------------------------------------------- #
def audit(job: dict) -> dict:
    periods = _need(job, "periods")
    if not isinstance(periods, list) or len(periods) == 0:
        raise DegerlemeError("VERİ YOK: 'periods' boş")
    tol = float(job.get("tolerance", 1e-6))
    checks, all_ok = [], True

    for p in periods:
        label = str(p.get("label", "?"))
        # 1) Bilanço denkliği: Aktif = Pasif + Özkaynak
        if all(k in p for k in ("assets", "liabilities", "equity")):
            diff = float(p["assets"]) - (float(p["liabilities"]) + float(p["equity"]))
            ok = abs(diff) <= tol
            all_ok &= ok
            checks.append({"period": label, "check": "balance_identity",
                           "ok": ok, "residual": round(diff, 6),
                           "detail": "Aktif = Pasif + Özkaynak"})
        # 2) Nakit akışı bağlanması: cash_end = cash_begin + Σ akışlar
        cf_keys = ("cf_operating", "cf_investing", "cf_financing")
        if "cash_begin" in p and "cash_end" in p and any(k in p for k in cf_keys):
            net = sum(float(p.get(k, 0.0)) for k in cf_keys)
            diff = float(p["cash_end"]) - (float(p["cash_begin"]) + net)
            ok = abs(diff) <= tol
            all_ok &= ok
            checks.append({"period": label, "check": "cash_flow_tie",
                           "ok": ok, "residual": round(diff, 6),
                           "detail": "cash_end = cash_begin + Σ(op+inv+fin)"})
        # 3) İşaret sağlaması: özkaynak/aktif negatifse uyar (hata değil, bayrak)
        for fld in ("assets", "equity"):
            if fld in p and float(p[fld]) < 0:
                checks.append({"period": label, "check": f"sign_{fld}",
                               "ok": False, "residual": float(p[fld]),
                               "detail": f"{fld} negatif — gözden geçir"})
                all_ok = False

    if not checks:
        raise DegerlemeError("VERİ YOK: denetlenecek alan yok "
                             "(assets/liabilities/equity ya da cash_* gerekli)")
    return {"op": "audit", "all_passed": bool(all_ok),
            "failed": [c for c in checks if not c["ok"]], "checks": checks}


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
def run_job(job: dict) -> dict:
    op = str(job.get("op", "")).lower()
    if op == "dcf":
        return dcf(job)
    if op == "comps":
        return comps(job)
    if op == "audit":
        return audit(job)
    if op == "wacc":
        return {"op": "wacc", "wacc": round(compute_wacc(_need(job, "parts")), 6)}
    raise DegerlemeError(f"bilinmeyen op: '{op}' (dcf|comps|audit|wacc)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Değerleme & denetim motoru")
    ap.add_argument("--job", required=True, help="job.json yolu")
    args = ap.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    try:
        print(json.dumps(run_job(job), ensure_ascii=False, indent=2))
    except DegerlemeError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
