#!/usr/bin/env python3
"""degerleme.py öz-testi. Bilinen-değer doğrulaması. SELF_TEST_OK basar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import degerleme  # noqa: E402


def main() -> int:
    # 1) DCF — el ile doğrulanabilir kapalı-form:
    #    fcf=[100], wacc=0.10, g=0 => PV_fcf=90.909, TV=1000, PV_TV=909.09, EV=1000
    r = degerleme.run_job({"op": "dcf", "fcf": [100], "wacc": 0.10,
                           "terminal_growth": 0.0, "net_debt": 0, "shares": 1})
    assert abs(r["enterprise_value"] - 1000.0) < 1e-3, r
    assert abs(r["per_share"] - 1000.0) < 1e-3, r
    assert r["sensitivity"] is not None and len(r["sensitivity"]["grid"]) == 5, r

    # DCF WACC>g koruması
    try:
        degerleme.run_job({"op": "dcf", "fcf": [100], "wacc": 0.02,
                           "terminal_growth": 0.05})
        raise AssertionError("WACC<=g hata vermeliydi")
    except degerleme.DegerlemeError:
        pass

    # 2) WACC bileşenlerden: 0.8*0.12 + 0.2*0.06*0.75 = 0.105
    w = degerleme.run_job({"op": "wacc", "parts": {
        "equity": 800, "debt": 200, "cost_equity": 0.12,
        "cost_debt": 0.06, "tax": 0.25}})
    assert abs(w["wacc"] - 0.105) < 1e-9, w

    # 3) Comps — median(9,11)=10 => EV=1000, equity=1000-200=800, /50 = 16
    c = degerleme.run_job({"op": "comps",
                           "peers": [{"name": "A", "ev_ebitda": 9, "pe": 15},
                                     {"name": "B", "ev_ebitda": 11, "pe": 18}],
                           "target": {"ebitda": 100, "net_income": 40},
                           "net_debt": 200, "shares": 50})
    assert c["multiple_stats"]["ev_ebitda"]["median"] == 10.0, c
    assert abs(c["implied_value"]["ev_ebitda"]["mid"]["per_share"] - 16.0) < 1e-6, c
    # pe: median(15,18)=16.5 => equity=16.5*40=660, /50 = 13.2
    assert abs(c["implied_value"]["pe"]["mid"]["per_share"] - 13.2) < 1e-6, c

    # 4) Audit — tutarlı dönem geçer, tutarsız dönem düşer
    a = degerleme.run_job({"op": "audit", "periods": [
        {"label": "OK", "assets": 1000, "liabilities": 600, "equity": 400,
         "cash_begin": 50, "cash_end": 80, "cf_operating": 100,
         "cf_investing": -60, "cf_financing": -10},
        {"label": "BAD", "assets": 1000, "liabilities": 600, "equity": 350},
    ]})
    assert a["all_passed"] is False, a
    assert any(f["period"] == "BAD" and f["check"] == "balance_identity"
               for f in a["failed"]), a
    ok_bal = [c for c in a["checks"]
              if c["period"] == "OK" and c["check"] == "balance_identity"][0]
    assert ok_bal["ok"] is True, a
    ok_cash = [c for c in a["checks"]
               if c["period"] == "OK" and c["check"] == "cash_flow_tie"][0]
    assert ok_cash["ok"] is True, a

    # 5) Fail-closed: eksik veri "VERİ YOK"
    try:
        degerleme.run_job({"op": "dcf", "fcf": [100]})  # wacc yok
        raise AssertionError("wacc eksikken hata vermeliydi")
    except degerleme.DegerlemeError:
        pass

    print("SELF_TEST_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
