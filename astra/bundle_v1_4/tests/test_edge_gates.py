"""Task 14A: defects the plan left unassigned, each bound to a finding id."""
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from astra_reference import Rejected, invoke, string, validate
from astra_host import ReviewerEndpoint
from host_fixture_support import fixture_reviewer

WORKER = str(Path(__file__).with_name("exit_code_fixture.py").resolve())


class ValidatorGapTests(unittest.TestCase):
    """kod_hata-9: the validator crashed or mis-ordered checks on lawful schemas."""

    def test_numeric_schema_is_rejected_not_crashed(self):
        for kind in ("number", "integer"):
            with self.subTest(kind=kind):
                with self.assertRaises(Rejected):
                    validate(1, {"type": kind})

    def test_null_is_allowed_before_enum_is_checked(self):
        validate(None, string(80, values=["a"], nullable=True))
        with self.assertRaisesRegex(Rejected, "SCHEMA_ENUM"):
            validate("b", string(80, values=["a"], nullable=True))

    def test_negative_bounds_are_rejected(self):
        with self.assertRaises(Rejected):
            validate([], {"type": "array", "items": string(), "minItems": -1, "maxItems": 3})


class ProcessLifecycleTests(unittest.TestCase):
    """kod_hata-8: killpg ran after the child had been reaped, so a recycled PID could die."""

    def test_reaped_process_group_is_not_killed(self):
        seen = []
        real = os.killpg

        def spy(pid, signal_number):
            seen.append(pid)
            return real(pid, signal_number)
        with patch.object(os, "killpg", spy), self.assertRaises(Rejected):
            invoke([sys.executable, WORKER, "SOME_CODE"], b"{}", 5)
        self.assertEqual(seen, [])


class ReviewerIdentityTests(unittest.TestCase):
    """kod_hata-14: a fixture could declare the pinned external identity and echo it."""

    def test_fixture_cannot_claim_the_pinned_model(self):
        argv = fixture_reviewer().argv
        with self.assertRaisesRegex(Rejected, "REVIEWER_IDENTITY_SCOPE"):
            ReviewerEndpoint(argv, "TEST_FIXTURE", "gpt-6-astra", "fixture-effort")

    def test_fixture_cannot_claim_a_supported_effort(self):
        argv = fixture_reviewer().argv
        with self.assertRaisesRegex(Rejected, "REVIEWER_IDENTITY_SCOPE"):
            ReviewerEndpoint(argv, "TEST_FIXTURE", "fixture-model", "max")


class SourceCaptureGateTests(unittest.TestCase):
    """test_kapsam-13: five SourceVault read gates had no test at all."""

    def setUp(self):
        import tempfile
        from datetime import datetime, timedelta, timezone
        self.tmp = tempfile.TemporaryDirectory(prefix="astra-capture-")
        self.addCleanup(self.tmp.cleanup)
        self.now = datetime.now(timezone.utc)
        self.timedelta = timedelta

    def spec(self, path, **overrides):
        base = dict(source_id="s0", path=str(path), kind="USER", tool_call_record=None,
                    as_of=(self.now - self.timedelta(seconds=2)).isoformat(),
                    valid_until=(self.now + self.timedelta(hours=1)).isoformat())
        base.update(overrides)
        return base

    def test_directory_is_not_a_source(self):
        from astra_host import SourceVault
        with self.assertRaisesRegex(Rejected, "SOURCE_REGULAR_FILE_REQUIRED|SOURCE_READ_FAILED"):
            SourceVault([self.spec(Path(self.tmp.name))])

    def test_empty_file_is_rejected(self):
        from astra_host import SourceVault
        path = Path(self.tmp.name) / "empty.txt"
        path.write_text("", encoding="utf-8")
        with self.assertRaisesRegex(Rejected, "SOURCE_EMPTY"):
            SourceVault([self.spec(path)])

    def test_oversized_file_is_rejected(self):
        from astra_host import SourceVault
        from astra_reference import WIRE_LIMIT
        path = Path(self.tmp.name) / "big.txt"
        path.write_text("x" * (WIRE_LIMIT + 10), encoding="utf-8")
        with self.assertRaisesRegex(Rejected, "SOURCE_SIZE"):
            SourceVault([self.spec(path)])

    def test_source_read_before_its_own_as_of_is_rejected(self):
        from astra_host import SourceVault
        path = Path(self.tmp.name) / "future.txt"
        path.write_text("later", encoding="utf-8")
        with self.assertRaisesRegex(Rejected, "SOURCE_STALE_OR_TIME"):
            SourceVault([self.spec(path, as_of=(self.now + self.timedelta(hours=1)).isoformat())])

    def test_expired_source_is_rejected(self):
        from astra_host import SourceVault
        path = Path(self.tmp.name) / "old.txt"
        path.write_text("older", encoding="utf-8")
        with self.assertRaisesRegex(Rejected, "SOURCE_STALE_OR_TIME"):
            SourceVault([self.spec(path,
                                   valid_until=(self.now - self.timedelta(seconds=1)).isoformat())])

    def test_missing_file_is_rejected(self):
        from astra_host import SourceVault
        with self.assertRaisesRegex(Rejected, "SOURCE_READ_FAILED"):
            SourceVault([self.spec(Path(self.tmp.name) / "absent.txt")])


class ComparisonContractTests(unittest.TestCase):
    """test_kapsam-5: the ambiguous branch (both comparisons AND an exemption) was untested."""

    def test_comparisons_with_an_exemption_are_ambiguous(self):
        import tempfile
        from datetime import datetime, timedelta, timezone
        from astra_host import SourceVault, TrustedHost
        import astra_compare
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory(prefix="astra-contract-") as folder:
            path = Path(folder) / "s.txt"
            quote = "Candidate A: median completion latency 100 ms."
            path.write_text(quote, encoding="utf-8")
            vault = SourceVault([dict(source_id="s0", path=str(path), kind="USER",
                                      tool_call_record=None,
                                      as_of=(now - timedelta(seconds=2)).isoformat(),
                                      valid_until=(now + timedelta(hours=1)).isoformat())])
            context = dict(metric="latency", definition="median completion latency", unit="ms",
                           period="one fixed test", population="same queries",
                           method="same median harness")
            rows = [dict(context, entity=e, source_id="s0", quote=quote, value=v)
                    for e, v in (("A", "100"), ("B", "120"))]
            comparisons = [dict(requirement_id="latency", scope_id="comparison",
                                claim_ids=["a:c1"], direction="lower_is_better", rows=rows)]
            with self.assertRaisesRegex(Rejected, "COMPARISON_CONTRACT_AMBIGUOUS"):
                TrustedHost(task="t" * 30, scope_ids=["comparison"], source_vault=vault,
                            comparisons=comparisons,
                            comparison_exemption="No comparison is required.")


if __name__ == "__main__":
    unittest.main()
