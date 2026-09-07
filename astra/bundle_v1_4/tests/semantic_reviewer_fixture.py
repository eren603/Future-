"""TEST FIXTURE ONLY: deterministic labels for the named regression cases.

This is deliberately not a general natural-language entailment algorithm.
It verifies the real reviewer transport and gate, not external-model quality.
"""
import json
import sys
import time

request = json.load(sys.stdin)
mode = sys.argv[1] if len(sys.argv) > 1 else "pass"
if mode == "timeout":
    time.sleep(30)
if mode == "flood":
    print("x" * 140000)
    raise SystemExit
if mode == "malformed":
    print("{}")
    raise SystemExit
verdicts = []
for cid, card in request["cards"].items():
    verdict = {"support": "supported", "refute": "refuted", "uncertain": "uncertain"}[card["stance"]]
    if mode == "reject":
        verdict = "uncertain"
    excerpts = [{"source_id": sid, "quote": request["source_snapshots"][sid]}
                for sid in card["source_ids"]]
    verdicts.append(dict(claim_id=cid, verdict=verdict, source_ids=card["source_ids"],
                         excerpts=excerpts, reason="Declared synthetic fixture label: " + mode,
                         conditions_preserved=True, counterevidence_checked=True))
assessment = dict(claim_verdicts=verdicts,
                  comparison_verdicts=[dict(requirement_id=r["requirement_id"],
                     passed=True, reason="Declared fixture label") for r in request["comparison_requirements"]],
                  candidate_review_passed=True, coverage_review_passed=True,
                  numeric_inventory_complete=True, comparison_inventory_complete=True,
                  unresolved_contradictions=[], reason="TEST_FIXTURE_ONLY")
if mode == "missing_claim":
    assessment["claim_verdicts"].pop()
elif mode == "missing_comparison":
    assessment["comparison_verdicts"] = []
elif mode == "comparison_reject":
    for verdict in assessment["comparison_verdicts"]:
        verdict["passed"] = False
elif mode == "false_quote":
    assessment["claim_verdicts"][0]["excerpts"][0]["quote"] = "Invented source passage."
elif mode == "missing_source":
    assessment["claim_verdicts"][0]["source_ids"] = []
elif mode == "conditions":
    assessment["claim_verdicts"][0]["conditions_preserved"] = False
elif mode == "counterevidence":
    assessment["claim_verdicts"][0]["counterevidence_checked"] = False
elif mode == "inventory":
    assessment["comparison_inventory_complete"] = False
elif mode == "numeric_inventory":
    assessment["numeric_inventory_complete"] = False
elif mode == "contradiction":
    assessment["unresolved_contradictions"] = ["Synthetic unresolved contradiction"]
elif mode == "modify_source":
    from pathlib import Path
    from urllib.parse import urlparse, unquote
    Path(unquote(urlparse(request["sources"][0]["locator"]).path)).write_text("Modified during review")
result = dict(request_digest="wrong" if mode == "replay" else request["request_digest"],
              reviewer_record_id="TEST_FIXTURE_ONLY", provider_model="fixture-model",
              provider_effort="fixture-effort", assessment=assessment)
if mode == "wrong_model":
    result["provider_model"] = "different-model"
elif mode == "external_like":
    result["provider_model"], result["provider_effort"] = "gpt-6-astra", "max"
elif mode == "external_snapshot":
    result["provider_model"], result["provider_effort"] = "gpt-6-astra-2026-09-01", "max"
print(json.dumps(result))
