"""Worker fixture: 'b' emits a non-critical uncertain card; others emit support."""
import json
import sys

e = json.load(sys.stdin)
crit = e["worker_id"] != "b"
card = dict(claim_id="c1", proposition_id="p1" if crit else "p2", scope_id=e["scope_ids"][0],
            statement="Supported claim." if crit else "Uncertain non-critical note.",
            label="ÇIKARIM", source_ids=[], stance="support" if crit else "uncertain",
            uncertainty="low" if crit else "high", critical=crit, math=None)
r = {k: e[k] for k in ("protocol", "run_id", "phase_id", "worker_id", "nonce")}
r.update(envelope_digest=e["digest"], status="READY", summary="uncertain fixture", cards=[card],
         covered_scope_ids=e["scope_ids"], unresolved_scope_ids=[], block_reason=None,
         next_safe_step=None, attempts=[])
print(json.dumps(r))
