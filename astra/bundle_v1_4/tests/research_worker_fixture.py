"""Deterministic worker used only by the v1.3 integration tests/demo."""
import json
import sys

e = json.load(sys.stdin)
claim = "A has lower observed median completion latency than B in the specified test."
reply = {key: e[key] for key in ("protocol", "run_id", "phase_id", "worker_id", "nonce")}
reply.update(envelope_digest=e["digest"], status="READY", summary="Synthetic comparison fixture.",
    cards=[dict(claim_id="c1", proposition_id="latency", scope_id=e["scope_ids"][0],
       statement=claim, label="ARAÇ", source_ids=e["source_ids"], stance="support",
       uncertainty="low", critical=True, math=None)], covered_scope_ids=e["scope_ids"],
    unresolved_scope_ids=[], block_reason=None, next_safe_step=None, attempts=[])
print(json.dumps(reply))
