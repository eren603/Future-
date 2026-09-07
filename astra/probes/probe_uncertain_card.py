"""Ölçüm sondası: kritik OLMAYAN 'uncertain' kart Controller.finalize'dan geçer mi, host neyle kapatır?"""
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "bundle_v1_3"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from astra_reference import Controller, canonical
from astra_host import SourceVault, TrustedHost
from host_fixture_support import fixture_reviewer

WORKER = '''
import json, sys
e = json.load(sys.stdin)
crit = e["worker_id"] != "b"
card = dict(claim_id="c1", proposition_id="p1" if crit else "p2", scope_id=e["scope_ids"][0],
  statement="Supported claim." if crit else "Uncertain non-critical note.",
  label="ÇIKARIM", source_ids=[], stance="support" if crit else "uncertain",
  uncertainty="low" if crit else "high", critical=crit, math=None)
r = {k: e[k] for k in ("protocol","run_id","phase_id","worker_id","nonce")}
r.update(envelope_digest=e["digest"], status="READY", summary="probe", cards=[card],
  covered_scope_ids=e["scope_ids"], unresolved_scope_ids=[], block_reason=None, next_safe_step=None)
print(json.dumps(r))
'''
tmp = Path(tempfile.mkdtemp(prefix="astra-probe-"))
w = tmp / "w.py"; w.write_text(WORKER)
src = tmp / "s.txt"; src.write_text("fixture evidence")
now = datetime.now(timezone.utc)


def host():
    vault = SourceVault([dict(source_id="s1", path=str(src), kind="TOOL",
                              as_of=(now - timedelta(seconds=2)).isoformat(),
                              valid_until=(now + timedelta(hours=1)).isoformat())])
    return TrustedHost(task="probe", scope_ids=["scope1"], source_vault=vault, comparisons=[],
                       comparison_exemption="probe", reviewer=fixture_reviewer())


workers = {wid: dict(role=role, argv=[sys.executable, str(w)])
           for wid, role in zip(("a", "b", "c"), ("model", "counterexample", "evidence"))}
decision = dict(action="Report.", owner="operator", guard_metric="g", kill_rule="k",
                user_cost="u", residual_risk="r", claim_ids=["a:c1", "b:c1", "c:c1"])
c = Controller(workers, ["scope1"], ["s1"], host=host(), max_restarts=0)
print("phase:", c.run("probe").status)
r = c.finalize(canonical(decision))
print("finalize (uncertain kart seçili):", r["status"], r.get("reason"))

decision["claim_ids"] = ["a:c1", "c:c1"]
c2 = Controller(workers, ["scope1"], ["s1"], host=host(), max_restarts=0)
c2.run("probe")
r2 = c2.finalize(canonical(decision))
print("finalize (uncertain kart seçilmedi):", r2["status"], r2.get("reason"))
