"""Identical regressions can run against ASTRA 1.0 and the repair."""
import sys
import unittest
from pathlib import Path
from astra_reference import digest
from host_fixture_support import Controller
from test_astra import finish, inputs

FIXTURE = str(Path(__file__).with_name("goal_worker_fixture.py").resolve())


def make_controller(mode="complete", scopes=("scope1", "scope2")):
    workers = {wid: {"role": role, "argv": [sys.executable, FIXTURE, mode]}
               for wid, role in zip(("a", "b", "c"),
                                    ("model", "counterexample", "evidence"))}
    return Controller(workers, list(scopes), max_restarts=0)


class GoalRegressions(unittest.TestCase):
    def test_ready_cannot_claim_scope_without_a_card(self):
        c = make_controller("missing_scope_card")
        phase = c.run("Deliver scope1 and scope2.")
        self.assertEqual(phase.status, "FAIL_CLOSED")
        self.assertTrue(any("CARD_SCOPE_INCOMPLETE" in e for e in phase.errors))

    def test_final_selection_cannot_drop_required_scope(self):
        c = make_controller()
        self.assertEqual(c.run("Deliver both scopes.").status, "PHASE_VALIDATED")
        values = inputs(c)
        values[0]["claim_ids"] = ["a:c1"]
        values[1]["candidate_digest"] = digest(values[0])
        result = finish(c, values)
        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason"], "DECISION_SCOPE_INCOMPLETE")

    def test_refuted_statement_keeps_its_polarity_in_output(self):
        c = make_controller("refute", ("scope1",))
        c.run("Report the test's refuted proposition.")
        result = finish(c)
        self.assertEqual(result["status"], "LOCAL_CHECKS_PASSED")
        for claim in result["claims"]:
            self.assertEqual(claim.get("stance"), "refute")
            self.assertEqual(claim.get("scope_id"), "scope1")
            self.assertEqual(claim.get("uncertainty"), "low")
            self.assertEqual(claim.get("source_ids"), [])

    def test_complete_multiscope_local_result_still_passes(self):
        c = make_controller()
        c.run("Deliver both scopes.")
        result = finish(c)
        self.assertEqual(result["status"], "LOCAL_CHECKS_PASSED")
        self.assertFalse(result["production_approval"])
        self.assertEqual(len(result["claims"]), 6)


if __name__ == "__main__":
    unittest.main()
