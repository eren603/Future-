"""Mandatory gate regressions; actual subprocess and source reads, no live LLM."""
import copy
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import astra_compare
import astra_host
from astra_reference import Controller, Rejected, bounded_json, canonical, digest
from astra_host import SourceVault, TrustedHost, ReviewerEndpoint
from host_fixture_support import fixture_reviewer

TASK = "Compare A and B using observed median completion latency in the same fixed test."
WORKER = str(Path(__file__).with_name("research_worker_fixture.py").resolve())


class HostIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="astra-integration-")
        self.addCleanup(self.tmp.cleanup)
        now = datetime.now(timezone.utc)
        self.specs, self.rows = [], []
        context = dict(metric="latency", definition="median completion latency", unit="ms",
                       period="one fixed test", population="same queries", method="same median harness")
        for i, value in enumerate(("100", "120")):
            path = Path(self.tmp.name) / f"source{i}.txt"
            quote = f"Candidate {('A', 'B')[i]}: median completion latency {value} ms."
            path.write_text(quote, encoding="utf-8")
            self.specs.append(dict(source_id=f"s{i}", path=str(path), kind="USER", tool_call_record=None,
                as_of=(now-timedelta(seconds=2)).isoformat(), valid_until=(now+timedelta(hours=1)).isoformat()))
            self.rows.append(dict(context, entity=("A", "B")[i], source_id=f"s{i}", quote=quote, value=value))

    def build(self, mode="pass", *, requirements=None, reviewer=True, task=TASK, worker=WORKER):
        self.vault = SourceVault(self.specs)
        self.requirements = [dict(requirement_id="latency", scope_id="comparison",
            claim_ids=["a:c1", "b:c1", "c:c1"], direction="lower_is_better", rows=self.rows)] if requirements is None else requirements
        host = TrustedHost(task=task, scope_ids=["comparison"], source_vault=self.vault,
            comparisons=self.requirements, comparison_exemption=None if self.requirements else "No comparison is required.",
            reviewer=fixture_reviewer(mode, .15 if mode == "timeout" else 2) if reviewer else None)
        workers = {wid: dict(role=role, argv=[sys.executable, worker])
                   for wid, role in zip(("a", "b", "c"), ("model", "counterexample", "evidence"))}
        self.controller = Controller(workers, ["comparison"], ["s0", "s1"], host=host,
                                     source_contents=self.vault.contents(), max_restarts=0)
        self.assertEqual(self.controller.run(TASK).status, "PHASE_VALIDATED")
        self.decision = dict(action="Use the observed comparison only.", owner="test_operator",
            guard_metric="Evidence supports the task", kill_rule="Stop if evidence changes",
            user_cost="Synthetic local test", residual_risk="No live LLM evaluation",
            claim_ids=["a:c1", "b:c1", "c:c1"])
        return self.controller

    def finish(self):
        return self.controller.finalize(canonical(self.decision))

    def fixture_invoke(self, mode):
        """Route the EXTERNAL_MODEL argv to the local fixture; no network is reachable."""
        from astra_reference import invoke as real_invoke
        argv = list(fixture_reviewer(mode).argv)

        def fake(_argv, request, timeout, *, environment=None):
            return real_invoke(argv, request, timeout)
        return fake

    def external_endpoint(self):
        adapter = str(Path(__file__).resolve().parents[1] / "astra_openai_reviewer.py")
        return ReviewerEndpoint((sys.executable, adapter), "EXTERNAL_MODEL", "gpt-6-astra",
                                "max", credential_env=("OPENAI_API_KEY",))

    def assert_closed(self, reason):
        result = self.finish()
        self.assertEqual(result, {"status": "FAIL_CLOSED", "reason": reason})

    def test_actual_finalize_invokes_comparison_and_reviewer(self):
        self.build()
        with patch.object(astra_compare, "compare_table", wraps=astra_compare.compare_table) as spy:
            result = self.finish()
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(result["status"], "LOCAL_CHECKS_PASSED")
        receipt = result["host_verification"]
        self.assertTrue(receipt["semantic_reviewer_executed"])
        self.assertFalse(receipt["semantic_support_verified"])
        self.assertFalse(receipt["production_approval"])
        self.assertFalse(receipt["source_access_authenticated"])
        self.assertEqual(receipt["comparisons"][0]["result"]["observed_leaders"], ["A"])
        rid = receipt.pop("host_receipt_id")
        self.assertEqual(rid, digest(receipt))

    def test_no_host_cannot_use_fabricated_review_flags(self):
        self.build()
        self.controller._host = None
        self.assert_closed("TRUSTED_HOST_REQUIRED")

    def test_missing_reviewer_fails_after_comparison_runs(self):
        self.build(reviewer=False)
        self.assert_closed("SEMANTIC_REVIEWER_REQUIRED")
        self.assertIn("COMPARISON_VALIDATED", [bounded_json(e)["kind"] for e in self.controller.events])

    def test_mismatched_measurement_rejects_in_real_finalize(self):
        self.rows[1]["method"] = "p95"
        self.build()
        self.assert_closed("NOT_COMPARABLE")

    def test_missing_value_rejects_in_real_finalize(self):
        self.rows[1]["value"] = None
        self.build()
        self.assert_closed("COMPARISON_INCOMPLETE")

    def test_noncritical_uncertain_card_outside_decision_is_published(self):
        # K-01 / celiski-2: an honest 'uncertain' card must not close the gate by itself.
        self.build(worker=str(Path(__file__).with_name("uncertain_worker_fixture.py").resolve()),
                   requirements=[])
        self.decision["claim_ids"] = ["a:c1", "c:c1"]
        result = self.finish()
        self.assertEqual(result["status"], "LOCAL_CHECKS_PASSED", result)
        verdicts = {v["claim_id"]: v["verdict"] for v in
                    result["host_verification"]["reviewer_response"]["assessment"]["claim_verdicts"]}
        self.assertEqual(verdicts["b:c1"], "uncertain")

    def test_uncertain_card_selected_by_decision_closes_gate(self):
        self.build(worker=str(Path(__file__).with_name("uncertain_worker_fixture.py").resolve()),
                   requirements=[])
        self.decision["claim_ids"] = ["a:c1", "b:c1", "c:c1"]
        self.assert_closed("SEMANTIC_CLAIM_UNSUPPORTED")

    def test_host_alone_does_not_detect_wrong_meaning(self):
        """Documents the limit: the host checks bindings, not meaning (test_kapsam-1)."""
        for spec, row in zip(self.specs, self.rows):
            row["quote"] = "Request count {} requests. Latency was not measured.".format(row["value"])
            Path(spec["path"]).write_text(row["quote"])
        self.build(mode="pass")
        self.assertEqual(self.finish()["status"], "LOCAL_CHECKS_PASSED")

    def test_fixture_uncertain_verdict_on_decision_claim_closes_gate(self):
        # Renamed from test_lexically_matching_wrong_meaning_rejects_reviewer_verdict: the
        # rejection comes from the fixture's unconditional 'uncertain' label, not from meaning.
        for quote in ("Request count {value} requests. Latency was not measured.",
                      "Median latency is not {value} ms; this is a timeout."):
            with self.subTest(quote=quote):
                for spec, row in zip(self.specs, self.rows):
                    row["quote"] = quote.format(value=row["value"])
                    Path(spec["path"]).write_text(row["quote"])
                self.build(mode="reject")
                with patch.object(astra_compare, "compare_table", wraps=astra_compare.compare_table) as spy:
                    self.assert_closed("SEMANTIC_CLAIM_UNSUPPORTED")
                self.assertEqual(spy.call_count, 1)

    def test_source_change_before_finalize_rejects(self):
        self.build()
        Path(self.specs[0]["path"]).write_text("Changed to 200 ms")
        self.assert_closed("SOURCE_CONTENT_DIGEST_MISMATCH")

    def test_source_change_during_reviewer_rejects(self):
        self.build(mode="modify_source")
        self.assert_closed("SOURCE_CONTENT_DIGEST_MISMATCH")

    def test_review_request_carries_fresh_nonce(self):
        """celiski-1: each review request is unique, so a cached response cannot be replayed."""
        self.build()
        receipt = self.finish()["host_verification"]
        self.assertRegex(receipt["review_nonce"], r"^[0-9a-f]{48}$")
        self.assertIn("issued_at", receipt)

    def test_two_hosts_never_issue_the_same_request_digest(self):
        self.build()
        first = self.finish()["host_verification"]["request_digest"]
        self.build()
        second = self.finish()["host_verification"]["request_digest"]
        self.assertNotEqual(first, second)

    def test_replayed_reviewer_digest_rejects(self):
        self.build(mode="replay")
        self.assert_closed("SEMANTIC_REVIEW_BINDING")

    def test_missing_review_coverage_rejects(self):
        self.build(mode="missing_claim")
        self.assert_closed("SEMANTIC_REVIEW_COVERAGE")

    def test_missing_comparison_review_rejects(self):
        self.build(mode="missing_comparison")
        self.assert_closed("SEMANTIC_COMPARISON_COVERAGE")

    def test_comparison_review_rejection_closes_gate(self):
        self.build(mode="comparison_reject")
        self.assert_closed("SEMANTIC_COMPARISON_UNSUPPORTED")

    def test_fabricated_reviewer_excerpt_rejects(self):
        self.build(mode="false_quote")
        self.assert_closed("SEMANTIC_QUOTE_NOT_IN_SNAPSHOT")

    def test_missing_reviewer_source_coverage_rejects(self):
        self.build(mode="missing_source")
        self.assert_closed("SEMANTIC_SOURCE_COVERAGE")

    def test_changed_conditions_or_unexamined_counterevidence_rejects(self):
        for mode in ("conditions", "counterevidence"):
            with self.subTest(mode=mode):
                self.build(mode=mode)
                self.assert_closed("SEMANTIC_CONDITIONS_UNVERIFIED")

    def test_missing_inventory_and_conflict_rejects(self):
        for mode in ("inventory", "numeric_inventory", "contradiction"):
            with self.subTest(mode=mode):
                self.build(mode=mode)
                self.assert_closed("SEMANTIC_REVIEW_FAILED")

    def test_timeout_is_bounded_and_closed(self):
        self.build(mode="timeout")
        self.assert_closed("REVIEWER_TIMEOUT")

    def test_flood_and_malformed_response_rejects(self):
        for mode, reason in (("flood", "OUTPUT_LIMIT"), ("malformed", "SCHEMA_FIELDS")):
            with self.subTest(mode=mode):
                self.build(mode=mode)
                self.assert_closed(reason)

    def test_reviewer_model_identity_must_match_host_config(self):
        self.build(mode="wrong_model")
        self.assert_closed("REVIEWER_CONFIGURATION_MISMATCH")

    def test_task_contract_cannot_be_reused_for_another_task(self):
        self.build(task="An unrelated task")
        self.assert_closed("HOST_TASK_BINDING")

    def test_comparison_claims_must_be_selected(self):
        self.build()
        self.decision["claim_ids"] = ["a:c1"]
        self.assert_closed("COMPARISON_CLAIM_BINDING")

    def test_contract_rows_are_immutable_snapshots(self):
        self.build()
        self.rows[1]["value"] = None
        self.assertEqual(self.finish()["status"], "LOCAL_CHECKS_PASSED")

    def test_source_getters_cannot_modify_host_capture(self):
        self.build()
        sources = self.vault.sources()
        sources[0]["access_record_id"] = "forged"
        self.assertNotEqual(self.vault.sources()[0]["access_record_id"], "forged")
        result = self.controller.finalize(canonical(self.decision), sources_raw=canonical(sources))
        self.assertEqual(result["reason"], "HOST_SOURCE_REGISTRY_BINDING")

    def test_empty_comparison_contract_needs_explicit_exemption(self):
        with self.assertRaises(Rejected):
            TrustedHost(task=TASK, scope_ids=["comparison"], source_vault=SourceVault([]),
                        comparisons=[], comparison_exemption=None)

    def test_general_superiority_rejected_by_concrete_candidate_review(self):
        self.build(mode="reject")
        self.decision["action"] = "A will always outperform B in every task."
        self.assert_closed("SEMANTIC_CLAIM_UNSUPPORTED")

    def test_envelope_carries_source_snapshots(self):
        # celiski-8: the evidence worker was told to inspect sources it never received.
        self.build()
        env = self.controller.envelope("a", TASK, "p")
        self.assertEqual(set(env["source_snapshots"]), {"s0", "s1"})
        self.assertIn("median completion latency", env["source_snapshots"]["s0"])
        d = env.pop("digest")
        self.assertEqual(d, digest(env))

    def test_tool_source_requires_binding_record(self):
        # eksiklik-6: a hand-written file labelled TOOL was accepted as tool output.
        spec = dict(self.specs[0], kind="TOOL", tool_call_record=None)
        with self.assertRaisesRegex(Rejected, "SOURCE_TOOL_BINDING"):
            SourceVault([spec])

    def test_tool_source_digest_must_match_record(self):
        rec = dict(tool_name="fixture_tool", args_digest=digest(["x"]), exit_status="0",
                   output_digest=digest("other"))
        spec = dict(self.specs[0], kind="TOOL", tool_call_record=rec)
        with self.assertRaisesRegex(Rejected, "SOURCE_TOOL_BINDING"):
            SourceVault([spec])
        rec["output_digest"] = digest(Path(self.specs[0]["path"]).read_text(encoding="utf-8"))
        vault = SourceVault([dict(spec, tool_call_record=rec)])
        self.assertEqual(vault.sources()[0]["kind"], "TOOL")
        self.assertEqual(vault.sources()[0]["tool_call_record"]["tool_name"], "fixture_tool")

    def test_user_source_cannot_carry_tool_record(self):
        rec = dict(tool_name="fixture_tool", args_digest=digest(["x"]), exit_status="0",
                   output_digest=digest(Path(self.specs[0]["path"]).read_text(encoding="utf-8")))
        with self.assertRaisesRegex(Rejected, "SOURCE_TOOL_BINDING"):
            SourceVault([dict(self.specs[0], kind="USER", tool_call_record=rec)])

    def test_fixture_reviewer_cannot_receive_credentials(self):
        # kod_hata-5: only the packaged EXTERNAL_MODEL adapter may receive the API key.
        fixture = fixture_reviewer()
        with self.assertRaisesRegex(Rejected, "REVIEWER_CREDENTIAL_SCOPE"):
            ReviewerEndpoint(fixture.argv, "TEST_FIXTURE", "fixture-model", "fixture-effort",
                             credential_env=("OPENAI_API_KEY",))

    def test_symlinked_source_is_rejected(self):
        # kod_hata-7: resolve() followed symlinks before O_NOFOLLOW could act.
        link = Path(self.tmp.name) / "link.txt"
        link.symlink_to(self.specs[0]["path"])
        self.specs[0]["path"] = str(link)
        with self.assertRaisesRegex(Rejected, "SOURCE_SYMLINK_REJECTED"):
            SourceVault(self.specs)

    def test_symlinked_parent_directory_is_rejected(self):
        """kod_hata-7 (second half): an intermediate symlink was still followed.

        O_NOFOLLOW only guards the last component and resolve() walks the rest, so a
        symlinked directory redirected the read while the declared path looked local.
        """
        real = Path(self.tmp.name) / "real_dir"
        real.mkdir()
        (real / "source.txt").write_text("Candidate A: median completion latency 100 ms.",
                                         encoding="utf-8")
        link_dir = Path(self.tmp.name) / "link_dir"
        link_dir.symlink_to(real, target_is_directory=True)
        self.specs[0]["path"] = str(link_dir / "source.txt")
        self.assertFalse(os.path.islink(self.specs[0]["path"]))  # last component is real
        with self.assertRaisesRegex(Rejected, "SOURCE_SYMLINK_REJECTED"):
            SourceVault(self.specs)

    def test_fixture_cannot_be_relabelled_as_external_model(self):
        fixture = fixture_reviewer()
        with self.assertRaisesRegex(Rejected, "EXTERNAL_REVIEWER_ADAPTER_REQUIRED"):
            ReviewerEndpoint(fixture.argv, "EXTERNAL_MODEL", "gpt-6-astra", "max",
                             credential_env=("OPENAI_API_KEY",))

    def test_worker_exit_code_is_carried_when_declared(self):
        # kod_hata-4: a worker's own rejection code was flattened into WORKER_EXIT.
        from astra_reference import invoke
        fixture = str(Path(__file__).with_name("exit_code_fixture.py").resolve())
        with self.assertRaisesRegex(Rejected, "^REVIEW_BUDGET_EXCEEDED$"):
            invoke([sys.executable, fixture, "REVIEW_BUDGET_EXCEEDED"], b"{}", 5)
        with self.assertRaisesRegex(Rejected, "^WORKER_EXIT$"):
            invoke([sys.executable, fixture, "free text, not a code"], b"{}", 5)

    def test_min_verdict_bytes_is_a_measurement(self):
        """The budget constant is re-derived here, so it cannot drift into a guess."""
        from astra_host import MIN_VERDICT_BYTES
        verdict = dict(claim_id="w:c1", verdict="supported", source_ids=["s0", "s1"],
                       excerpts=[dict(source_id="s0", quote="x" * 120),
                                 dict(source_id="s1", quote="y" * 120)],
                       reason="r", conditions_preserved=True, counterevidence_checked=True)
        self.assertEqual(MIN_VERDICT_BYTES, len(canonical(verdict)))

    def test_review_budget_precheck_stops_before_call(self):
        # api_uyum-12 / K-14: a card set too large for any lawful reply is refused early.
        self.build(requirements=[])
        many = {f"w:c{i}": dict(claim_id=f"c{i}", proposition_id="p", scope_id="comparison",
                                statement="x", label="ÇIKARIM", source_ids=[], stance="support",
                                uncertainty="low", critical=False, math=None) for i in range(300)}
        self.decision["claim_ids"] = list(many)[:3]
        with self.assertRaisesRegex(Rejected, "REVIEW_BUDGET_EXCEEDED"):
            self.controller._host.verify(self.controller, self.decision, many,
                                         self.vault.sources(), [], {})

    def test_external_model_rejects_fixture_model_identity(self):
        """No live provider is reachable here, so this path cannot end in success.

        The fixture answers as 'fixture-model' and the host refuses it. The accept
        branch is covered by test_external_like_response_sets_semantic_support_verified;
        neither test is evidence that an external model was actually consulted.
        """
        self.build()
        self.controller._host._reviewer = self.external_endpoint()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-not-a-real-key"}), \
                patch.object(astra_host, "invoke", self.fixture_invoke("pass")):
            self.assert_closed("REVIEWER_CONFIGURATION_MISMATCH")

    def test_external_like_response_sets_semantic_support_verified(self):
        """Host accept branch for EXTERNAL_MODEL, driven by a local fixture reply.

        This tests the host's acceptance logic only. It is NOT a live provider call
        and does not verify adapter transport against a real API.
        """
        self.build()
        self.controller._host._reviewer = self.external_endpoint()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-not-a-real-key"}), \
                patch.object(astra_host, "invoke", self.fixture_invoke("external_like")):
            result = self.finish()
        self.assertEqual(result["status"], "LOCAL_CHECKS_PASSED", result)
        self.assertTrue(result["host_verification"]["semantic_support_verified"])
        self.assertEqual(result["host_verification"]["reviewer_kind"], "EXTERNAL_MODEL")

    def test_dated_snapshot_model_is_accepted_by_the_host(self):
        # api_uyum-3: the host must tolerate the dated snapshot of the pinned model.
        self.build()
        self.controller._host._reviewer = self.external_endpoint()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-not-a-real-key"}), \
                patch.object(astra_host, "invoke", self.fixture_invoke("external_snapshot")):
            result = self.finish()
        self.assertEqual(result["status"], "LOCAL_CHECKS_PASSED", result)
        self.assertEqual(result["host_verification"]["reviewer_response"]["provider_model"],
                         "gpt-6-astra-2026-09-01")

    def test_review_request_carries_both_full_and_wire_schema(self):
        # api_uyum-1: the adapter sends the length-free schema, the host keeps the full one.
        self.build()
        captured = []

        def capture(argv, request, timeout, *, environment=None):
            captured.append(bounded_json(request))
            return self.fixture_invoke("pass")(argv, request, timeout)
        with patch.object(astra_host, "invoke", capture):
            self.finish()
        from astra_host import ASSESSMENT_SCHEMA, transport_schema
        self.assertEqual(captured[0]["assessment_schema"], ASSESSMENT_SCHEMA)
        self.assertEqual(captured[0]["wire_schema"], transport_schema(ASSESSMENT_SCHEMA))


if __name__ == "__main__":
    unittest.main()
