"""Local deterministic regression fixture; never calls an LLM."""
import json
import sys

envelope = json.load(sys.stdin)
mode = sys.argv[1]
scopes = envelope["scope_ids"]
emitted = scopes[:1] if mode == "missing_scope_card" else scopes
cards = [{
    "claim_id": f"c{i}", "proposition_id": f"p{i}", "scope_id": scope,
    "statement": f"The test condition holds for {scope}.",
    "label": "ÇIKARIM", "source_ids": [],
    "stance": "refute" if mode == "refute" else "support",
    "uncertainty": "low", "critical": True, "math": None,
} for i, scope in enumerate(emitted, 1)]
reply = {k: envelope[k] for k in
         ("protocol", "run_id", "phase_id", "worker_id", "nonce")}
reply.update(envelope_digest=envelope["digest"], status="READY",
             summary="Deterministic local fixture.", cards=cards,
             covered_scope_ids=scopes, unresolved_scope_ids=[],
             block_reason=None, next_safe_step=None)
print(json.dumps(reply))
