"""Explicit host fixture for migrating the v1.2 structural regression suite."""
import sys
import tempfile
import weakref
from datetime import datetime, timedelta, timezone
from pathlib import Path
from astra_reference import Controller as BaseController
from astra_host import SourceVault, TrustedHost, ReviewerEndpoint

REVIEWER = str(Path(__file__).with_name("semantic_reviewer_fixture.py").resolve())


def fixture_reviewer(mode="pass", timeout=2.0):
    return ReviewerEndpoint((sys.executable, REVIEWER, mode), "TEST_FIXTURE",
                            "fixture-model", "fixture-effort", timeout)


class Controller(BaseController):
    def run(self, task):
        if self._host is None:
            self._fixture_directory = tempfile.TemporaryDirectory(prefix="astra-host-fixture-")
            self._fixture_cleanup = weakref.finalize(self, self._fixture_directory.cleanup)
            now = datetime.now(timezone.utc)
            specs = []
            for index, sid in enumerate(self.source_ids):
                path = Path(self._fixture_directory.name) / f"source{index}.txt"
                path.write_text("fixture evidence", encoding="utf-8")
                specs.append(dict(source_id=sid, path=str(path), kind="USER", tool_call_record=None,
                                  as_of=(now-timedelta(seconds=2)).isoformat(),
                                  valid_until=(now+timedelta(hours=1)).isoformat()))
            self._host = TrustedHost(task=task, scope_ids=list(self.scope_ids),
                                    source_vault=SourceVault(specs), comparisons=[],
                                    comparison_exemption="Structural regression fixture; no comparison requested.",
                                    reviewer=fixture_reviewer())
            self._source_contents = self._host._vault.contents()
        return super().run(task)
