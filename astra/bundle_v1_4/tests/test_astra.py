import json
import sys
import tempfile
import time
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
from astra_reference import (MathRejected, Rejected, exact_math, canonical,
    bounded_json, digest, invoke, validate, REPLY_SCHEMA, MATH_SCHEMA, WIRE_LIMIT)
from host_fixture_support import Controller

FIXTURE = str(Path(__file__).with_name("worker_fixture.py").resolve())


def workers(modes=("ready", "ready", "ready")):
    return {wid: {"role": role, "argv": [sys.executable, FIXTURE, mode]}
            for wid, role, mode in zip(("a", "b", "c"), ("model", "counterexample", "evidence"), modes)}


def controller(modes=("ready", "ready", "ready"), **kwargs):
    return Controller(workers(modes), ["scope1"], max_restarts=0, **kwargs)


def inputs(c, sources=None):
    sources = c._host.sources() if sources is None else sources
    ids = []
    for raw in c._phase.replies:
        r = bounded_json(raw)
        ids += [r["worker_id"] + ":" + card["claim_id"] for card in r["cards"]]
    decision = {"action": "Review the proposal.", "owner": "user", "guard_metric": "Evidence remains valid.",
                "kill_rule": "Stop if evidence changes.", "user_cost": "Review effort.",
                "residual_risk": "Only local fixtures were tested.", "claim_ids": ids}
    review = {"phase_digest": c._phase.phase_digest, "candidate_digest": digest(decision),
              "source_registry_digest": digest(sources), "reviewer_record_id": "LOCAL_FIXTURE_ONLY",
              "reviewed_claim_ids": ids, "unresolved_claim_ids": [], "unresolved_contradictions": [],
              "candidate_review_passed": True, "coverage_review_passed": True,
              "source_review_passed": True, "numeric_inventory_complete": True}
    return decision, review, sources


def finish(c, values=None):
    return c.finalize(*(canonical(x) for x in (inputs(c) if values is None else values)))


class MathTests(unittest.TestCase):
    def test_exact_fraction(self):
        self.assertEqual(exact_math("1/3 + 1/6")["exact"], "1/2")
    def test_long_decimal_preserves_original_token(self):
        s = "0.1234567890123456789"
        self.assertEqual(exact_math(s)["exact"], str(Fraction(s)))
    def test_underflow_is_nonzero(self):
        self.assertEqual(Fraction(exact_math("1e-400")["exact"]), Fraction("1e-400"))
    def test_large_scientific_literal_is_exact(self):
        self.assertEqual(exact_math("1e309")["exact"], str(10 ** 309))
    def test_proof_records_source_and_python(self):
        p = exact_math(" 0.1 + 0.2 ")
        self.assertEqual(p["source"], "0.1 + 0.2")
        self.assertEqual(p["exact"], "3/10")
        self.assertTrue(p["python_version"])
        pid = p.pop("proof_id")
        self.assertEqual(pid, digest(p))
    def test_domain_and_unsupported_are_controlled(self):
        for s in ["0**-1", "0/0", "0**0", "__import__('os')", "True", "(1).__class__", "[1]", "4**0.5"]:
            with self.subTest(source=s), self.assertRaises(MathRejected):
                exact_math(s)
    def test_resource_limits_precede_large_operations(self):
        for s in ["1e1001", "2**21", "((((2**20)**20)**20)**20)", "1" * 513]:
            with self.subTest(source=s), self.assertRaises(MathRejected):
                exact_math(s)
    def test_comments_and_newlines_are_rejected(self):
        # kod_hata-2: ast.parse accepts comments, which then leak into the rendered proof.
        for s in ["1+1 # really 3", "1+1\n# note", "1+\\\n1", "1+1;"]:
            with self.subTest(source=s), self.assertRaises(MathRejected):
                exact_math(s)
    def test_negative_power_and_unary(self):
        self.assertEqual(exact_math("-(2**-3)")["exact"], "-1/8")
    def test_supported_fraction_fits_reply_value_schema(self):
        expression = "((1e100+1)/(1e100-1))**20"
        value = exact_math(expression)["exact"]
        self.assertGreater(len(value), 3000)
        validate({"expression": expression, "value": value}, MATH_SCHEMA)


class WireTests(unittest.TestCase):
    def test_json_rejects_duplicates_nonfinite_and_deep_input(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[' * 40 + b'0' + b']' * 40]:
            with self.subTest(raw=raw), self.assertRaises(Rejected):
                bounded_json(raw)
    def test_python_object_and_cycles_cannot_cross_boundary(self):
        p = {}; p["self"] = p
        with self.assertRaises(Rejected):
            bounded_json(p)
        with self.assertRaises(Rejected):
            canonical(p)
    def test_empty_payload_and_wrong_type_fail_schema(self):
        for value in [{}, "not an object"]:
            with self.subTest(value=value), self.assertRaises(Rejected):
                validate(value, REPLY_SCHEMA)
    def test_mutation_does_not_change_stored_bytes(self):
        c = controller(); phase = c.run("Review the task.")
        original = phase.replies[0]
        view = bounded_json(original); view["peer_results"] = "changed"
        self.assertEqual(phase.replies[0], original)
        self.assertNotIn("peer_results", bounded_json(phase.replies[0]))
        with self.assertRaises(FrozenInstanceError):
            phase.status = "APPROVED"
    def test_digest_binds_real_policy_and_role(self):
        a, b = controller(policy="Policy A"), controller(policy="Policy B")
        x = a.envelope("a", "Task", "p")
        y = b.envelope("a", "Task", "p")
        self.assertNotEqual(x["policy_digest"], y["policy_digest"])
        d = x.pop("digest")
        self.assertEqual(d, digest(x))
        self.assertIn("common", x["instructions"])
        self.assertIn("role", x["instructions"])
        self.assertIn("nonce", x["reply_schema"]["required"])


class RuntimeTests(unittest.TestCase):
    def test_bad_startup_config_rejected(self):
        for ws in [{"a": workers()["a"]}, dict(workers(), a={"role": "operator", "argv": ["x"]})]:
            with self.subTest(workers=ws), self.assertRaises(Rejected):
                Controller(ws, ["scope1"])
    def test_reference_cannot_claim_real_isolation(self):
        with self.assertRaisesRegex(Rejected, "ISOLATION_UNAVAILABLE"):
            Controller(workers(), ["scope1"], mode="REAL_ISOLATION")
    def test_bad_command_rejected_before_any_dispatch(self):
        ws = workers(); ws["c"]["argv"] = ["not-a-trusted-absolute-program"]
        with self.assertRaisesRegex(Rejected, "EXECUTABLE_REQUIRED"):
            Controller(ws, ["scope1"])
    def test_good_phase_is_not_final_approval(self):
        c = controller(); self.assertEqual(c.run("Review.").status, "PHASE_VALIDATED")
        r = finish(c)
        self.assertEqual(r["status"], "LOCAL_CHECKS_PASSED")
        self.assertFalse(r["production_approval"])
    def test_blocked_dominates_other_worker_error_without_retry(self):
        with tempfile.TemporaryDirectory() as t:
            path = str(Path(t) / "count")
            ws = workers(("count_block", "invalid", "ready")); ws["a"]["argv"].append(path)
            c = Controller(ws, ["scope1"], max_restarts=2)
            p = c.run("Review.")
            self.assertEqual(p.status, "BLOCKED")
            self.assertEqual(p.attempts, 1)
            self.assertEqual(Path(path).read_text(), "1")
            self.assertEqual(finish(c)["status"], "BLOCKED")
            with self.assertRaises(Rejected):
                c.run("Try again.")
    def test_errors_then_blocked_also_stop(self):
        c = controller(("invalid", "blocked", "ready"))
        self.assertEqual(c.run("Review.").status, "BLOCKED")
    def test_real_hanging_process_is_terminated(self):
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            invoke([sys.executable, FIXTURE, "hang"], b"{}", .15)
        self.assertLess(time.monotonic() - started, 2)
    def test_stdin_backpressure_has_deadline(self):
        with self.assertRaises(TimeoutError):
            invoke([sys.executable, FIXTURE, "never_read"], b"x" * WIRE_LIMIT, .15)
    def test_output_flood_is_bounded(self):
        with self.assertRaisesRegex(Rejected, "OUTPUT_LIMIT"):
            invoke([sys.executable, FIXTURE, "flood"], b"{}", 1)
    def test_fresh_phase_and_nonce_on_retry(self):
        with tempfile.TemporaryDirectory() as t:
            ws = workers(("retry", "ready", "ready")); ws["a"]["argv"].append(str(Path(t) / "state"))
            c = Controller(ws, ["scope1"], max_restarts=1)
            p = c.run("Review.")
            self.assertEqual(p.status, "PHASE_VALIDATED")
            self.assertEqual(p.attempts, 2)
    def test_budget_exhaustion_is_fail_closed(self):
        c = Controller(workers(("invalid", "ready", "ready")), ["scope1"], max_restarts=1)
        p = c.run("Review.")
        self.assertEqual(p.status, "FAIL_CLOSED")
        self.assertEqual(p.attempts, 2)
    def test_blocked_without_attempts_is_invalid(self):
        # K-03 / kacis_yolu-1: a BLOCKED reply must carry evidence of at least two attempts.
        c = controller(("blocked_no_attempts", "ready", "ready"))
        p = c.run("Review.")
        self.assertEqual(p.status, "FAIL_CLOSED")
        self.assertTrue(any("BLOCKED_ATTEMPTS_REQUIRED" in e for e in p.errors), p.errors)
    def test_ready_with_attempts_is_invalid(self):
        c = controller(("ready_with_attempts", "ready", "ready"))
        p = c.run("Review.")
        self.assertEqual(p.status, "FAIL_CLOSED")
        self.assertTrue(any("READY_SCHEMA" in e for e in p.errors), p.errors)
    def test_schema_binding_and_coverage_failures(self):
        for mode in ["wrong_nonce", "forbidden", "empty_cards", "too_many_cards", "coverage", "duplicate_claim", "worker_invalid", "missing_block_reason", "candidate_statement_leak", "wrong_statement"]:
            with self.subTest(mode=mode):
                c = controller((mode, "ready", "ready"))
                self.assertEqual(c.run("Review.").status, "FAIL_CLOSED")


class PublicationTests(unittest.TestCase):
    def test_genuine_math_proof_and_final_value(self):
        c = controller(("math", "ready", "ready")); c.run("Compute.")
        r = finish(c)
        self.assertEqual(r["status"], "LOCAL_CHECKS_PASSED")
        self.assertEqual(r["claims"][0]["statement"], "1/3 + 1/6 = 1/2")
        p = r["proofs"]["a:c1"]
        self.assertEqual(p["run_id"], c.run_id)
        pid = p.pop("proof_id"); self.assertEqual(pid, digest(p))
    def test_wrong_numeric_value_fails_publication(self):
        c = controller(("wrong_math", "ready", "ready")); c.run("Compute.")
        self.assertEqual(finish(c)["reason"], "MATH_VALUE_MISMATCH")
    def test_contradiction_cannot_be_voted_away(self):
        c = controller(("ready", "ready", "refute")); c.run("Review.")
        self.assertEqual(finish(c)["reason"], "CONTRADICTION")
    def test_unresolved_review_stays_closed(self):
        c = controller(); c.run("Review.")
        for key, value in [("unresolved_claim_ids", ["a:c1"]), ("unresolved_contradictions", ["Conflict"]), ("candidate_review_passed", False), ("numeric_inventory_complete", False)]:
            with self.subTest(key=key):
                values = inputs(c); values[1][key] = value
                self.assertEqual(finish(c, values)["status"], "FAIL_CLOSED")
    def test_review_binds_candidate_phase_sources(self):
        c = controller(); c.run("Review.")
        for key in ["phase_digest", "candidate_digest", "source_registry_digest"]:
            with self.subTest(key=key):
                values = inputs(c); values[1][key] = "wrong"
                self.assertEqual(finish(c, values)["reason"], "REVIEW_BINDING")
    def test_missing_decision_and_review_fields_fail(self):
        c = controller(); c.run("Review.")
        values = inputs(c); del values[0]["kill_rule"]
        self.assertEqual(finish(c, values)["status"], "FAIL_CLOSED")
        values = inputs(c); values[1]["reviewed_claim_ids"] = ["a:c1"]
        self.assertEqual(finish(c, values)["reason"], "REVIEW_COVERAGE")
    def test_placeholder_owner_fails(self):
        # K-06: 'owner must be a real responsible party' was enforced for two words only.
        c = controller(); c.run("Review.")
        for owner in ["n/a", "TBD", "-", "?", "x"]:
            with self.subTest(owner=owner):
                values = inputs(c); values[0]["owner"] = owner
                values[1]["candidate_digest"] = digest(values[0])
                self.assertEqual(finish(c, values)["reason"], "OWNER_REQUIRED")
    def test_second_finalize_is_locked(self):
        # celiski-1: a second finalize on the same phase must not silently succeed again.
        c = controller(); c.run("Review.")
        self.assertEqual(finish(c)["status"], "LOCAL_CHECKS_PASSED")
        self.assertEqual(finish(c)["reason"], "FINALIZE_ALREADY_DONE")
    def test_blank_action_and_unknown_owner_fail(self):
        c = controller(); c.run("Review.")
        for field, value in [("action", "   "), ("owner", "unknown")]:
            with self.subTest(field=field):
                values = inputs(c); values[0][field] = value
                values[1]["candidate_digest"] = digest(values[0])
                self.assertEqual(finish(c, values)["status"], "FAIL_CLOSED")
    def test_missing_source_fails(self):
        c = controller(("sourced", "ready", "ready"), source_ids=["s1"]); c.run("Review.")
        self.assertEqual(finish(c, inputs(c, []))["reason"], "SOURCE_MISSING")
    def test_valid_and_stale_source(self):
        c = controller(("sourced", "ready", "ready"), source_ids=["s1"]); c.run("Review.")
        now = datetime.now(timezone.utc)
        source = c._host.sources()[0]
        self.assertEqual(finish(c, inputs(c, [source]))["status"], "LOCAL_CHECKS_PASSED")
        # v1.4: finalize locks after success, so the stale case needs its own run.
        c2 = controller(("sourced", "ready", "ready"), source_ids=["s1"]); c2.run("Review.")
        source = c2._host.sources()[0]
        source["valid_until"] = (now - timedelta(seconds=1)).isoformat()
        self.assertEqual(finish(c2, inputs(c2, [source]))["reason"], "SOURCE_STALE_OR_TIME")


if __name__ == "__main__":
    unittest.main()
