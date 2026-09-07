from dataclasses import replace
from pathlib import Path
import json
import unittest
from astra_plugin_router import Need, Provider, plan_routes, atlas_candidates

SESSION = "test-session"


def provider(name="Tool", caps=("x",), **overrides):
    values = dict(name=name, kind="plugin", verified_capabilities=frozenset(caps),
                  callable_names=frozenset({name + ".read"}), installed=True,
                  auth="NOT_REQUIRED", state="AVAILABLE", observed_session=SESSION,
                  evidence_id="fixture-manifest")
    values.update(overrides)
    return Provider(**values)


def route(needs, providers, **options):
    options.setdefault("session", SESSION)
    options.setdefault("available_callables", {name for p in providers for name in p.callable_names})
    return plan_routes(needs, providers, **options)


class PluginRouterTests(unittest.TestCase):
    def test_native_capability_needs_no_plugin(self):
        native = provider("Python", kind="native")
        result = route([Need("n", "C10", "x")], [provider(), native])
        self.assertEqual(result["actions"][0]["action"], "USE_NATIVE")
        self.assertEqual(result["topic_providers"]["C10"], [])
    def test_minimal_pair_covers_complementary_capabilities(self):
        ps = [provider("A", ("a", "b")), provider("B", ("c",)), provider("C", ("a",))]
        ns = [Need(k, "C01", k) for k in ("a", "b", "c")]
        result = route(ns, ps)
        self.assertEqual(result["topic_providers"]["C01"], ["A", "B"])
        self.assertEqual(result["status"], "PLAN_READY")
    def test_one_provider_is_preferred_when_sufficient(self):
        result = route([Need("a", "C01", "a"), Need("b", "C01", "b")],
                       [provider("A", ("a",)), provider("B", ("b",)), provider("Both", ("a", "b"))])
        self.assertEqual(result["topic_providers"]["C01"], ["Both"])
    def test_three_disjoint_providers_do_not_become_a_false_pair(self):
        result = route([Need(k, "C01", k) for k in ("a", "b", "c")],
                       [provider(k, (k,)) for k in ("a", "b", "c")])
        self.assertEqual(len(result["topic_providers"]["C01"]), 2)
        self.assertEqual(len(result["gaps"]), 1)
    def test_each_topic_has_its_own_pair(self):
        ns = [Need(k, t, k) for k, t in [("a", "C01"), ("b", "C01"), ("c", "C02")]]
        result = route(ns, [provider(k, (k,)) for k in ("a", "b", "c")])
        self.assertEqual(result["status"], "PLAN_READY")
        self.assertTrue(all(len(v) <= 2 for v in result["topic_providers"].values()))
    def test_current_manifest_must_expose_actual_tool(self):
        result = route([Need("n", "C01", "x")], [provider()], available_callables=())
        self.assertNotEqual(result["status"], "PLAN_READY")
    def test_snapshot_installed_flag_does_not_make_ready(self):
        result = route([Need("n", "C01", "x")], [provider(observed_session="old-atlas")])
        self.assertEqual(result["actions"][0]["action"], "DISCOVER_CAPABILITY")
    def test_catalog_advertisement_is_not_executable_capability(self):
        p = provider(caps=(), advertised_capabilities=frozenset({"training.execute"}))
        result = route([Need("n", "C09", "training.execute")], [p])
        self.assertNotEqual(result["status"], "PLAN_READY")
    def test_only_one_new_connection_suggestion_per_turn(self):
        ps = [provider(k, (), installed=False, advertised_capabilities=frozenset({k}), plugin_id="plugin_" + k) for k in ("a", "b")]
        result = route([Need(k, "C01", k) for k in ("a", "b")], ps)
        self.assertEqual(result["new_suggestion_count"], 1)
        self.assertEqual([a["action"] for a in result["actions"]], ["SUGGEST_ONE_CONNECTION", "QUEUE_CONNECTION"])
    def test_prior_suggestion_is_not_repeated(self):
        p = provider(installed=False, plugin_id="plugin_x")
        result = route([Need("n", "C01", "x")], [p], suggestion_already_used=True)
        self.assertEqual(result["actions"][0]["action"], "QUEUE_CONNECTION")
    def test_same_new_connection_is_reused_for_multiple_needs(self):
        p = provider("Combined", ("a", "b"), installed=False, plugin_id="plugin_combined")
        result = route([Need(k, "C01", k) for k in ("a", "b")], [p])
        self.assertEqual([a["action"] for a in result["actions"]],
                         ["SUGGEST_ONE_CONNECTION", "WAIT_EXISTING_CONNECTION"])
        self.assertEqual(result["new_suggestion_count"], 1)
    def test_no_id_means_search_not_invented_install(self):
        result = route([Need("n", "C01", "x")], [provider(installed=False, plugin_id=None)])
        self.assertEqual(result["actions"][0]["action"], "DISCOVER_CAPABILITY")
    def test_pending_is_not_suggested_again(self):
        result = route([Need("n", "C01", "x")], [provider(state="PENDING", installed=False)])
        self.assertEqual(result["actions"][0]["action"], "WAIT_EXISTING_CONNECTION")
    def test_installed_but_auth_required_requests_account_connection(self):
        result = route([Need("n", "C01", "x")], [provider(auth="REQUIRED")])
        self.assertEqual(result["actions"][0]["action"], "NEEDS_ACCOUNT_CONNECTION")
        self.assertEqual(result["new_suggestion_count"], 0)
    def test_coinmarketcap_decline_is_preserved(self):
        result = route([Need("n", "C14", "x", provider="CoinMarketCap")],
                       [provider("CoinMarketCap", installed=False, plugin_id="plugin_cmc")], declined=["CoinMarketCap"])
        self.assertEqual(result["actions"][0]["action"], "RESPECT_DECLINE")
        self.assertEqual(result["new_suggestion_count"], 0)
    def test_explicit_named_reversal_can_restore_eligibility(self):
        p = provider("CoinMarketCap")
        result = route([Need("n", "C14", "x", provider=p.name)], [p],
                       declined=[p.name], explicitly_reallowed=[p.name])
        self.assertEqual(result["status"], "PLAN_READY")
    def test_policy_block_does_not_trigger_permission_bypass(self):
        result = route([Need("n", "C01", "x")], [provider(state="POLICY_BLOCKED")])
        self.assertEqual(result["actions"][0]["action"], "REPORT_POLICY_BLOCK")
    def test_provider_and_private_account_cannot_be_substituted(self):
        need = Need("mail", "C41", "mail.read", provider="Gmail", account="work")
        ps = [provider("Gmail", ("mail.read",), account="personal"), provider("Web", ("mail.read",), kind="native")]
        result = route([need], ps)
        self.assertNotEqual(result["status"], "PLAN_READY")
    def test_external_write_requires_its_own_authorization(self):
        need = Need("send", "C41", "mail.send", effect="external_write")
        p = provider("Gmail", ("mail.send",))
        self.assertEqual(route([need], [p])["actions"][0]["action"], "PREPARE_AUTHORIZATION")
        self.assertEqual(route([replace(need, authorized=True)], [p])["status"], "PLAN_READY")
    def test_binance_public_data_is_not_order_execution(self):
        p = provider("Binance", ("market.futures.read",))
        result = route([Need("trade", "C14", "orders.live", effect="financial_trade", authorized=True)], [p])
        self.assertEqual(result["actions"][0]["action"], "DISCOVER_CAPABILITY")
    def test_skill_finder_is_not_gpu_training(self):
        p = provider("NVIDIA", ("skill.find",), kind="skill", skill_package="nvidia-finder",
                     advertised_capabilities=frozenset({"gpu.training"}))
        result = route([Need("train", "C09", "gpu.training")], [p], available_skills={"nvidia-finder"})
        self.assertNotEqual(result["status"], "PLAN_READY")
    def test_known_skill_is_read_not_an_external_model_call(self):
        p = provider("Riqor", ("prompt.review.workflow",), kind="skill", skill_package="prompt-engineer")
        result = route([Need("review", "C02", "prompt.review.workflow")], [p], available_skills={"prompt-engineer"})
        self.assertEqual(result["actions"][0]["action"], "READ_SKILL")
        self.assertFalse(result["executed"])
    def test_unlisted_topic_uses_open_capability_discovery(self):
        result = route([Need("n", "NEW_TOPIC", "unlisted.capability")], [])
        self.assertEqual(result["actions"][0]["action"], "DISCOVER_CAPABILITY")
    def test_no_useless_third_install_for_two_provider_limit(self):
        ps = [provider("A", ("a",)), provider("B", ("b",)),
              provider("C", ("c",), installed=False, plugin_id="plugin_C")]
        result = route([Need(k, "C01", k) for k in ("a", "b", "c")], ps)
        self.assertEqual(result["new_suggestion_count"], 0)
    def test_catalogue_is_complete_and_never_used_as_live_evidence(self):
        atlas = json.loads(Path(__file__).resolve().parents[1].joinpath("astra_plugin_atlas.json").read_text())
        self.assertEqual(len(atlas["topics"]), 66)
        self.assertEqual(len(atlas["entries"]), 306)
        self.assertEqual(len({e["name"] for e in atlas["entries"]}), 306)
        for topic in atlas["topics"]:
            entries = atlas_candidates(atlas, topic["id"])
            self.assertEqual(len(entries), topic["count"])
            self.assertTrue(set(topic["preferred"]).issubset(e["name"] for e in entries))
        self.assertEqual(atlas_candidates(atlas, "NEW_TOPIC"), [])


if __name__ == "__main__":
    unittest.main()
