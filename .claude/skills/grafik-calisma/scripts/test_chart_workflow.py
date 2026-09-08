"""Synthetic causal contracts and ledger behavior; no market accuracy claim."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import chart_workflow as cw

# A modern aligned UTC day, with all three intervals closing at C0.
C0 = 1_728_000_000_000 - 1


def candle(open_ms, step=900_000, o=100, h=101, l=99, c=100):
    return {"open_time": open_ms, "close_time": open_ms + step - 1,
            "open": o, "high": h, "low": l, "close": c, "volume": 10, "closed": True}


def case_job():
    frames = {}
    for tf, step in cw.TF_MS.items():
        frames[tf] = {"symbol": "BTCUSDT", "timeframe": tf,
                      "rows": [candle(C0 + 1 - step * (20-i), step) for i in range(20)]}
    return {"venue": "BINANCE_USDM", "symbol": "BTCUSDT", "cutoff": C0,
            "tick_size": "0.1", "source": "https://fapi.binance.com/fapi/v1/klines",
            "retrieved_at": C0 + 1, "timeframes": frames}


def observation(direction="LONG", confirmed=False):
    return {"first_leg": direction, "main_structure": "Yükseliş yapısı; ilk bacak ayrı görsel değerlendirme.",
            "direction_evidence": [{"reason": "C0 öncesi talep bölgesi gözlendi.", "timeframe": "15m", "bar_index": 18}],
            "entry": {"type": "limit", "zone": [98, 99] if direction == "LONG" else [101, 102],
                      "trigger_status": "confirmed" if confirmed else "conditional",
                      "trigger_model": "confirmed_at_cutoff" if confirmed else "price_touch",
                      "trigger_description": "15m giriş bölgesindeki temas/teyit koşulu izlenir.",
                      "trigger_evidence": [{"reason": "Kapanmış mum teyidi.", "timeframe": "15m", "bar_index": 19}] if confirmed else []},
            "stop": 95 if direction == "LONG" else 105,
            "targets": [105, 110] if direction == "LONG" else [95, 90]}


def future_job(rows):
    return {"symbol": "BTCUSDT", "timeframe": "15m", "rows": rows,
            "source": "synthetic-test", "retrieved_at": rows[-1]["close_time"] + 1}


def plan_record(obs=None):
    plan = cw.build_plan(cw.prepare(case_job()), obs or observation())
    return {"plan": plan, "recorded_at_ms": C0 + 1, "record_id": "test", "prospective_clock_eligible": False}


def evaluate(rows, obs=None):
    return cw.evaluate_future(plan_record(obs), future_job(rows), rows[-1]["close_time"] + 1)


class PreparationTests(unittest.TestCase):
    def test_all_hashes_and_c0(self):
        case = cw.prepare(case_job())
        self.assertEqual(case["cutoff_ms"], C0)
        self.assertEqual(case["timeframes"]["4h"]["count"], 20)
        self.assertEqual(case["timeframes"]["15m"]["normalized_sha256"], cw.digest(case["timeframes"]["15m"]["rows"]))

    def test_symbol_and_timeframe_mismatch(self):
        for field, value in (("symbol", "ETHUSDT"), ("timeframe", "5m")):
            job = case_job()
            job["timeframes"]["15m"][field] = value
            with self.assertRaises(ValueError):
                cw.prepare(job)

    def test_future_and_unclosed_explicitly_filtered_and_counted(self):
        for extra in (candle(C0 + 1), dict(candle(C0 + 1), closed=False)):
            job = case_job()
            job["timeframes"]["15m"]["rows"].append(extra)
            case = cw.prepare(job)
            frame = case["timeframes"]["15m"]
            self.assertEqual(frame["input_count"], 21)
            self.assertEqual(frame["retained_count"], 20)
            self.assertEqual(sum(frame["excluded_counts"].values()), 1)
            self.assertEqual(frame["raw_sha256"], cw.digest(job["timeframes"]["15m"]["rows"]))

    def test_invalid_gap_duplicate_and_unaligned(self):
        for mode in ("gap", "duplicate", "unaligned", "negative", "nan", "ohlc", "tick"):
            job = case_job()
            rows = job["timeframes"]["15m"]["rows"]
            if mode == "gap":
                rows.insert(0, candle(rows[0]["open_time"] - 2 * 900_000))
            elif mode == "duplicate":
                rows.insert(5, copy.deepcopy(rows[5]))
            elif mode == "unaligned":
                for row in rows:
                    row["open_time"] -= 1
                    row["close_time"] -= 1
            elif mode == "negative":
                rows[4].update(open=-2, high=-1, low=-3, close=-2)
            elif mode == "nan":
                rows[4]["close"] = float("nan")
            elif mode == "ohlc":
                rows[4]["high"] = 90
            else:
                rows[4]["close"] = 100.01
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                cw.prepare(job)

    def test_stale_final_candle_and_insufficient_history(self):
        for mode in ("stale", "short"):
            job = case_job()
            rows = job["timeframes"]["4h"]["rows"]
            if mode == "stale":
                step = cw.TF_MS["4h"]
                for row in rows:
                    row["open_time"] -= step
                    row["close_time"] -= step
            else:
                rows.pop(0)
            with self.assertRaises(ValueError):
                cw.prepare(job)

    def test_screenshot_is_hash_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.png"
            path.write_bytes(b"synthetic image fixture")
            job = case_job()
            job["screenshots"] = [{"path": str(path), "timeframe": "15m"}]
            case = cw.prepare(job)
            self.assertEqual(case["screenshots"][0]["bytes"], 23)
            self.assertEqual(len(case["screenshots"][0]["sha256"]), 64)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.case = cw.prepare(case_job())

    def test_direction_is_explicit_not_structure_inferred(self):
        obs = observation("SHORT")
        plan = cw.build_plan(self.case, obs)
        self.assertEqual(plan["first_leg"]["direction"], "SHORT")
        self.assertIn("Yükseliş", plan["main_structure"])
        self.assertIsNone(plan["first_leg"]["probability"])
        del obs["first_leg"]
        with self.assertRaises(ValueError):
            cw.build_plan(self.case, obs)

    def test_conditional_direction_remains_visible(self):
        plan = cw.build_plan(self.case, observation())
        self.assertEqual(plan["final_decision"]["status"], "conditional")
        self.assertEqual(plan["final_decision"]["direction"], "LONG")
        self.assertIsNone(plan["rr"]["net"])
        self.assertEqual(plan["rr"]["gross"][0]["entry_high"], "1.5")

    def test_missing_geometry_blocks_but_preserves_direction(self):
        obs = observation()
        del obs["stop"]
        plan = cw.build_plan(self.case, obs)
        self.assertEqual(plan["final_decision"]["status"], "blocked")
        self.assertEqual(plan["final_decision"]["direction"], "LONG")

    def test_invalid_geometry_prices_and_tick(self):
        for key, value in (("stop", 99), ("stop", 0), ("stop", -1), ("stop", "NaN"), ("stop", 95.01), ("targets", [98]), ("targets", [110, 105])):
            obs = observation()
            obs[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                cw.build_plan(self.case, obs)

    def test_future_anchor_rejected(self):
        for anchor in ({"reason": "lookahead", "timeframe": "15m", "bar_index": 20},
                       {"reason": "lookahead", "timeframe": "15m", "bar_index": 19, "time": C0+1}):
            obs = observation()
            obs["direction_evidence"] = [anchor]
            with self.assertRaises(ValueError):
                cw.build_plan(self.case, obs)

    def test_confirmed_needs_closed_bar_trigger_evidence(self):
        obs = observation(confirmed=True)
        plan = cw.build_plan(self.case, obs)
        self.assertEqual(plan["final_decision"]["status"], "confirmed")
        obs["entry"]["trigger_evidence"] = []
        with self.assertRaises(ValueError):
            cw.build_plan(self.case, obs)

    def test_net_rr_is_explicit_and_below_gross(self):
        obs = observation()
        obs["costs"] = {"fee_bps_per_side": 4, "slippage_bps_per_side": 1}
        plan = cw.build_plan(self.case, obs)
        self.assertLess(float(plan["rr"]["net"][0]["entry_high"]), 1.5)
        self.assertEqual(plan["rr"]["costs"]["status"], "explicit_assumption")

    def test_first_leg_barriers_require_tick_and_both_sides_of_c0(self):
        for spec in ({"up_price": 100, "down_price": 97}, {"up_price": 103, "down_price": 101},
                     {"up_price": 103.01, "down_price": 97}):
            obs = observation()
            obs["first_leg_test"] = spec
            with self.assertRaises(ValueError):
                cw.build_plan(self.case, obs)

    def test_conditional_visual_trigger_description_required_and_preserved(self):
        obs = observation()
        obs["entry"]["trigger_model"] = "analyst_confirmation"
        del obs["entry"]["trigger_description"]
        with self.assertRaises(ValueError):
            cw.build_plan(self.case, obs)
        obs["entry"]["trigger_description"] = "Talep bölgesinden 15m kapanış teyidi."
        plan = cw.build_plan(self.case, obs)
        self.assertEqual(plan["entry"]["trigger_description"], obs["entry"]["trigger_description"])
        self.assertIn(obs["entry"]["trigger_description"], plan["text_tr"])

    def test_uncertain_first_leg_allows_explicit_conditional_short_scenario(self):
        obs = observation("SHORT")
        obs["first_leg"] = "UNCERTAIN"
        obs["entry"]["direction"] = "SHORT"
        plan = cw.build_plan(self.case, obs)
        self.assertEqual(plan["first_leg"]["direction"], "UNCERTAIN")
        self.assertEqual(plan["final_decision"], {"status": "conditional", "direction": "SHORT",
                                               "cutoff_ms": C0, "reason": plan["final_decision"]["reason"]})
        self.assertEqual(plan["entry"]["direction"], "SHORT")
        self.assertEqual(plan["rr"]["gross"][0]["entry_low"], "1.5")
        obs["direction_evidence"] = []
        with self.assertRaises(ValueError):
            cw.build_plan(self.case, obs)

    def test_first_leg_long_and_later_short_trade_are_separate(self):
        obs = observation("SHORT")
        obs["first_leg"] = "LONG"
        obs["entry"]["direction"] = "SHORT"
        plan = cw.build_plan(self.case, obs)
        self.assertEqual(plan["first_leg"]["direction"], "LONG")
        self.assertEqual(plan["final_decision"]["direction"], "SHORT")
        rows = [candle(C0+1, o=101, h=102, l=100, c=101),
                candle(C0+1+900_000, o=101, h=102, l=94, c=95)]
        result = cw.evaluate_future({"plan": plan, "recorded_at_ms": C0+1}, future_job(rows), rows[-1]["close_time"]+1)
        self.assertEqual(result["status"], "TP")
        self.assertEqual(result["pnl"]["gross_R"], "1.5")

    def test_mutated_prepared_case_rejected(self):
        self.case["timeframes"]["15m"]["rows"][0]["close"] = 100.1
        with self.assertRaises(ValueError):
            cw.build_plan(self.case, observation())


class ForwardTests(unittest.TestCase):
    def test_target_before_entry_is_not_win(self):
        rows = [candle(C0+1, o=100, h=106, l=100, c=101)]
        result = evaluate(rows)
        self.assertEqual(result["status"], "unfilled")
        self.assertFalse(result["filled"])
        self.assertIsNone(result["pnl"])

    def test_unfilled_expiry_has_no_loss(self):
        rows = [candle(C0+1+i*900_000, o=100, h=104, l=100, c=102) for i in range(12)]
        result = evaluate(rows)
        self.assertEqual(result["status"], "expired")
        self.assertFalse(result["filled"])
        self.assertIsNone(result["pnl"])
        self.assertTrue(result["direction_outcome"]["correct"])

    def test_same_bar_target_entry_is_ambiguous(self):
        result = evaluate([candle(C0+1, o=100, h=106, l=98, c=101)])
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["pnl"])

    def test_tp_after_prior_bar_fill(self):
        rows = [candle(C0+1, o=100, h=101, l=98, c=100),
                candle(C0+1+900_000, o=100, h=106, l=99, c=105)]
        result = evaluate(rows)
        self.assertEqual(result["status"], "TP")
        self.assertEqual(result["pnl"]["gross_R"], "1.5")
        self.assertIsNone(result["pnl"]["net_pnl_per_unit"])

    def test_stop_and_target_same_bar_ambiguous(self):
        rows = [candle(C0+1, o=99, h=101, l=98, c=100),
                candle(C0+1+900_000, o=100, h=106, l=94, c=100)]
        self.assertEqual(evaluate(rows)["status"], "ambiguous")

    def test_stop_gap_conservative_loss(self):
        rows = [candle(C0+1, o=99, h=101, l=98, c=100),
                candle(C0+1+900_000, o=94, h=95, l=93, c=94)]
        result = evaluate(rows)
        self.assertEqual(result["status"], "SL")
        self.assertEqual(result["pnl"]["gross_R"], "-1.25")

    def test_unmodeled_visual_confirmation_not_assumed_from_touch(self):
        obs = observation()
        obs["entry"]["trigger_model"] = "analyst_confirmation"
        result = evaluate([candle(C0+1, o=100, h=106, l=98, c=101)], obs)
        self.assertEqual(result["status"], "unfilled")
        self.assertFalse(result["filled"])

    def test_invalidated_before_stop_entry(self):
        obs = observation()
        obs["entry"].update(type="stop", zone=[101, 102])
        result = evaluate([candle(C0+1, o=100, h=101, l=94, c=100)], obs)
        self.assertEqual(result["status"], "invalidated")
        self.assertFalse(result["filled"])

    def test_future_must_start_after_c0_record_and_be_contiguous(self):
        for rows in ([candle(C0+1-900_000)], [candle(C0+1+900_000)],
                     [candle(C0+1), candle(C0+1+2*900_000)]):
            with self.assertRaises(ValueError):
                evaluate(rows)

    def test_first_leg_first_barrier_touch_separate_from_horizon_close(self):
        obs = observation()
        obs["first_leg_test"] = {"up_price": 103, "down_price": 97}
        rows = [candle(C0+1, o=100, h=104, l=99, c=100)]
        rows.extend(candle(C0+1+i*900_000, o=100, h=101, l=98, c=99) for i in range(1, 12))
        result = evaluate(rows, obs)
        self.assertTrue(result["first_leg_outcome"]["correct"])
        self.assertFalse(result["direction_outcome"]["correct"])

    def test_first_leg_same_bar_both_ambiguous_and_untouched_unscored(self):
        obs = observation()
        obs["first_leg_test"] = {"up_price": 103, "down_price": 97}
        ambiguous = evaluate([candle(C0+1, o=100, h=104, l=96, c=100)], obs)
        self.assertEqual(ambiguous["first_leg_outcome"]["status"], "ambiguous")
        self.assertIsNone(ambiguous["first_leg_outcome"]["correct"])
        rows = [candle(C0+1+i*900_000) for i in range(12)]
        untouched = evaluate(rows, obs)
        self.assertEqual(untouched["first_leg_outcome"]["status"], "untouched")
        self.assertIsNone(untouched["first_leg_outcome"]["correct"])

    def test_unclosed_future_is_rejected(self):
        row = dict(candle(C0+1), closed=False)
        with self.assertRaises(ValueError):
            evaluate([row])

    def test_only_full_bars_after_registration_are_evaluated(self):
        record = plan_record()
        record["recorded_at_ms"] += 1000
        rows = [candle(C0+1+900_000)]
        result = cw.evaluate_future(record, future_job(rows), rows[-1]["close_time"]+1)
        self.assertEqual(result["record_delay_excluded_bars"], 1)
        with self.assertRaises(ValueError):
            cw.evaluate_future(record, future_job([candle(C0+1)]), C0+900_001)


class LedgerTests(unittest.TestCase):
    def test_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "forward.jsonl"
            cw.record_plan(ledger, plan_record()["plan"], C0+1)
            row = json.loads(ledger.read_text())
            row["plan"]["targets"][0] = "999"
            ledger.write_text(json.dumps(row)+"\n")
            with self.assertRaises(ValueError):
                cw.summarize_ledger(ledger)

    def test_unfilled_not_in_win_loss_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "forward.jsonl"
            event = cw.record_plan(ledger, plan_record()["plan"], C0+1)
            rows = [candle(C0+1+i*900_000, o=100, h=104, l=100, c=102) for i in range(12)]
            cw.resolve_record(ledger, event["record_id"], future_job(rows), rows[-1]["close_time"]+1)
            summary = cw.summarize_ledger(ledger)
            self.assertEqual(summary["status_counts"], {"expired": 1})
            self.assertEqual(summary["trade_support"], 0)
            self.assertIsNone(summary["gross_target_hit_rate"])
            self.assertEqual(summary["direction_support"], 1)
            self.assertEqual(summary["declared_clock_records"], 1)

    def test_duplicate_plan_and_pre_c0_registration_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "forward.jsonl"
            plan = plan_record()["plan"]
            with self.assertRaises(ValueError):
                cw.record_plan(ledger, plan, C0)
            cw.record_plan(ledger, plan, C0+1)
            with self.assertRaises(ValueError):
                cw.record_plan(ledger, plan, C0+1)

    def test_target_hit_with_negative_net_pnl_is_not_profitable(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "forward.jsonl"
            obs = observation(confirmed=True)
            obs["entry"]["zone"] = [99, 99]
            obs["targets"] = [99.1]
            obs["costs"] = {"fee_bps_per_side": 5, "slippage_bps_per_side": 2}
            plan = plan_record(obs)["plan"]
            event = cw.record_plan(ledger, plan, C0+1)
            rows = [candle(C0+1, o=99, h=99.2, l=98.8, c=99.1)]
            cw.resolve_record(ledger, event["record_id"], future_job(rows), rows[-1]["close_time"]+1)
            summary = cw.summarize_ledger(ledger)
            self.assertEqual(summary["gross_target_hit_rate"], 1)
            self.assertEqual(summary["net_profitable_trade_rate"], 0)
            self.assertEqual(summary["net_profit_support"], 1)
            self.assertNotIn("trade_win_rate", summary)

    def test_late_record_with_no_complete_bar_left_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "forward.jsonl"
            plan = plan_record()["plan"]
            with self.assertRaises(ValueError):
                cw.record_plan(ledger, plan, plan["horizon"]["end_ms"] - 1000)

    def test_resolution_extension_rejects_revised_past_prices(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "forward.jsonl"
            event = cw.record_plan(ledger, plan_record()["plan"], C0+1)
            rows = [candle(C0+1, o=100, h=101, l=100, c=100)]
            cw.resolve_record(ledger, event["record_id"], future_job(rows), rows[-1]["close_time"]+1)
            rows[0]["high"] = 106
            rows.append(candle(C0+1+900_000))
            with self.assertRaises(ValueError):
                cw.resolve_record(ledger, event["record_id"], future_job(rows), rows[-1]["close_time"]+1)

    def test_horizon_direction_can_extend_terminal_trade(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "forward.jsonl"
            event = cw.record_plan(ledger, plan_record()["plan"], C0+1)
            rows = [candle(C0+1, o=99, h=101, l=98, c=100),
                    candle(C0+1+900_000, o=100, h=106, l=99, c=105)]
            first = cw.resolve_record(ledger, event["record_id"], future_job(rows), rows[-1]["close_time"]+1)
            self.assertEqual(first["result"]["status"], "TP")
            self.assertIsNone(first["result"]["direction_outcome"]["correct"])
            rows.extend(candle(C0+1+i*900_000, o=105, h=107, l=104, c=106) for i in range(2, 12))
            final = cw.resolve_record(ledger, event["record_id"], future_job(rows), rows[-1]["close_time"]+1)
            self.assertEqual(final["result"]["status"], "TP")
            self.assertTrue(final["result"]["direction_outcome"]["correct"])
            self.assertEqual(cw.summarize_ledger(ledger)["trade_support"], 1)


if __name__ == "__main__":
    unittest.main()
