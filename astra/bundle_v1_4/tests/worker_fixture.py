"""Deterministic test worker; not an LLM or an isolation attestation."""
import json
import sys
import time
from pathlib import Path

mode = sys.argv[1]
if mode == "never_read":
    time.sleep(30)
    raise SystemExit
e = json.load(sys.stdin)
if mode == "hang":
    time.sleep(30)
if mode == "flood":
    sys.stdout.write("x" * 150000)
    raise SystemExit
if mode == "count_block":
    count_file = Path(sys.argv[2])
    count_file.write_text(str(int(count_file.read_text()) + 1) if count_file.exists() else "1")
    mode = "blocked"
if mode == "invalid":
    print("{}")
    raise SystemExit
if mode == "retry":
    state = Path(sys.argv[2])
    if not state.exists():
        state.write_text(e["phase_id"] + "\n" + e["nonce"])
        print("{}")
        raise SystemExit
    previous = state.read_text().splitlines()
    if previous[0] == e["phase_id"] or previous[1] == e["nonce"]:
        raise SystemExit(2)
card = {"claim_id": "c1", "proposition_id": "p1", "scope_id": e["scope_ids"][0],
        "statement": "A bounded proposal is available.", "label": "ÇIKARIM", "source_ids": [],
        "stance": "support", "uncertainty": "low", "critical": True, "math": None}
r = {k: e[k] for k in ["protocol", "run_id", "phase_id", "worker_id", "nonce"]}
r.update({"envelope_digest": e["digest"], "status": "READY", "summary": "Scope checked.",
          "cards": [card], "covered_scope_ids": e["scope_ids"], "unresolved_scope_ids": [],
          "block_reason": None, "next_safe_step": None})
if mode == "blocked":
    r.update(status="BLOCKED", summary="", cards=[], covered_scope_ids=[],
             block_reason="PERMISSION_UNAVAILABLE", next_safe_step="Stop this run.")
elif mode == "wrong_nonce":
    r["nonce"] = "wrong"
elif mode == "forbidden":
    r["peer_results"] = []
elif mode == "math" or mode == "wrong_math":
    card["statement"] = "1/3 + 1/6"
    card["math"] = {"expression": card["statement"], "value": "999" if mode == "wrong_math" else "1/2"}
elif mode == "wrong_statement":
    card["statement"] = "The answer is 999"
    card["math"] = {"expression": "1/3 + 1/6", "value": "1/2"}
elif mode == "refute":
    card["stance"] = "refute"
elif mode == "sourced":
    card["label"] = "ARAÇ"
    card["source_ids"] = ["s1"]
elif mode == "empty_cards":
    r["cards"] = []
elif mode == "too_many_cards":
    r["cards"] = [dict(card, claim_id=f"c{i}") for i in range(65)]
elif mode == "coverage":
    r["covered_scope_ids"] = []
elif mode == "duplicate_claim":
    r["cards"].append(dict(card))
elif mode == "worker_invalid":
    r["status"] = "INVALID"
elif mode == "missing_block_reason":
    r.update(status="BLOCKED", summary="", cards=[], covered_scope_ids=[])
elif mode == "candidate_statement_leak":
    card["peer_results"] = "leak"
print(json.dumps(r))
