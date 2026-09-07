"""CLI-level regressions: the run entry point must fail closed, never traceback."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RunCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="astra-cli-")
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "demo"
        subprocess.run([sys.executable, str(ROOT / "demo_local.py"), "--case", "valid",
                        "--output-dir", str(self.folder)], timeout=60, check=False,
                       capture_output=True)
        self.config_path = self.folder / "config.json"
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))

    def run_cli(self, output=None):
        self.config_path.write_text(json.dumps(self.config, ensure_ascii=False), encoding="utf-8")
        out = self.folder / "cli_result.json" if output is None else output
        done = subprocess.run([sys.executable, str(ROOT / "astra_run.py"), str(self.config_path),
                               "--output", str(out)], timeout=60, capture_output=True, text=True)
        return done, json.loads(done.stdout)

    def test_wildcard_claim_ids_expand_after_phase(self):
        # kacis_yolu-4: the operator cannot know worker-scoped card ids before the phase runs.
        self.config["decision"]["claim_ids"] = ["*"]
        done, printed = self.run_cli()
        self.assertEqual(printed["final_status"], "LOCAL_CHECKS_PASSED", done.stdout + done.stderr)
        result = json.loads((self.folder / "cli_result.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(result["claim_ids"]), ["a:c1", "b:c1", "c:c1"])

    def test_declared_task_status_in_config_is_rejected(self):
        # celiski-7: status is derived by the host; a configured status is a false claim.
        self.config["task_status"] = "COMPLETE"
        done, printed = self.run_cli()
        self.assertEqual(printed["final_status"], "FAIL_CLOSED")
        result = json.loads((self.folder / "cli_result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["reason"], "HOST_CONFIG_FIELDS")

    def test_task_status_is_reported_at_top_level_and_matches_the_receipt(self):
        # Madde 9 denetimi: plan `execute()` çıktısında task_status istiyordu.
        self.config["requirements"] = [dict(
            requirement_id="R1", basis_quote="compare A and B", delivery="comparison",
            acceptance_check="observed leaders", evidence_ids=["latency"],
            status="VERIFIED", depends_on=[])]
        done, printed = self.run_cli()
        result = json.loads((self.folder / "cli_result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["task_status"], "COMPLETE", done.stdout + done.stderr)
        self.assertEqual(result["result"]["host_verification"]["task_status"], "COMPLETE")

    def test_task_status_is_reported_even_when_a_gate_closes(self):
        self.config["requirements"] = [dict(
            requirement_id="R1", basis_quote="live model", delivery="none",
            acceptance_check="receipt", evidence_ids=[], status="BLOCKED", depends_on=[])]
        self.config["reviewer"] = None  # closes the gate before any receipt exists
        done, printed = self.run_cli()
        result = json.loads((self.folder / "cli_result.json").read_text(encoding="utf-8"))
        self.assertEqual(printed["final_status"], "FAIL_CLOSED")
        self.assertEqual(result["task_status"], "BLOCKED")

    def test_regenerated_summary_matches_expected_statuses(self):
        # Task 11: verification/cli_summary.json bir koşunun ÇIKTISIDIR, elle yazılmaz.
        summary = json.loads((ROOT / "verification" / "cli_summary.json").read_text(encoding="utf-8"))
        self.assertEqual({case: row["final_status"] for case, row in summary["cases"].items()},
                         {"valid": "LOCAL_CHECKS_PASSED", "method_mismatch": "FAIL_CLOSED",
                          "semantic_rejection": "FAIL_CLOSED", "reviewer_missing": "FAIL_CLOSED"})
        self.assertFalse(any(row["production_approval"] for row in summary["cases"].values()))

    def test_output_to_directory_path_is_fail_closed_not_traceback(self):
        # kod_hata-12: an unwritable --output raised OSError out of main().
        target = self.folder / "as_directory"
        target.mkdir()
        done, printed = self.run_cli(output=target)
        self.assertEqual(done.returncode, 1)
        self.assertEqual(printed["final_status"], "FAIL_CLOSED")
        self.assertIsNone(printed["output"])
        self.assertNotIn("Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main()
