"""Measure (celiski-1): does a second finalize on the same phase pass with an identical request digest?"""
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / (sys.argv[1] if len(sys.argv) > 1 else "bundle_v1_4")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from astra_reference import Controller, canonical
from astra_host import SourceVault, TrustedHost
from host_fixture_support import fixture_reviewer

tmp = Path(tempfile.mkdtemp(prefix="astra-replay-"))
src = tmp / "s.txt"; src.write_text("fixture evidence")
now = datetime.now(timezone.utc)
vault = SourceVault([dict(source_id="s1", path=str(src), kind="USER", tool_call_record=None,
                          as_of=(now - timedelta(seconds=2)).isoformat(),
                          valid_until=(now + timedelta(hours=1)).isoformat())])
host = TrustedHost(task="probe", scope_ids=["scope1"], source_vault=vault, comparisons=[],
                   comparison_exemption="probe", reviewer=fixture_reviewer())
W = str(ROOT / "tests" / "worker_fixture.py")
workers = {w: dict(role=r, argv=[sys.executable, W, "ready"])
           for w, r in zip("abc", ("model", "counterexample", "evidence"))}
c = Controller(workers, ["scope1"], ["s1"], host=host, max_restarts=0)
c.run("probe")
d = dict(action="Report.", owner="operator", guard_metric="g", kill_rule="k",
         user_cost="u", residual_risk="r", claim_ids=["a:c1", "b:c1", "c:c1"])
r1 = c.finalize(canonical(d))
r2 = c.finalize(canonical(d))
print("first:", r1["status"], "| second:", r2["status"], r2.get("reason"))
h1 = r1.get("host_verification", {}).get("request_digest")
h2 = r2.get("host_verification", {}).get("request_digest")
print("request_digest equal:", h1 is not None and h1 == h2)
