"""Bounded integration regressions: real routing/time/consumer units, stub motors.

No full piramit run, live market request, historical learning, or repository state
write. Every fixture/snapshot is created under an explicit temporary directory.
Synthetic positive controls demonstrate routing, not market accuracy or edge.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import piramit as p

GRAPH = p.SKILLS / "grafik-calisma" / "scripts"
sys.path.insert(0, str(GRAPH))
import confluence
import setup_dogrulama


C0 = 1767321900000  # fixed 2026-01-02 02:45Z; no clock or market dependency


def response(output=None, ok=True):
    return {"ok": ok, "cikti": output, "metin": "fixture", "hata": None if ok else "fixture failure", "kod": 0 if ok else 1}


def bars(timeframe_ms, count=48):
    # Deliberately distinct starts/last closes across 15m/1h/4h.
    last_open = (C0 // timeframe_ms) * timeframe_ms
    return [{"open_time": last_open - (count - i - 1) * timeframe_ms,
             "close_time": last_open - (count - i - 1) * timeframe_ms + timeframe_ms - 1,
             "open": 101 + i / 10, "high": 103 + i / 10,
             "low": 100 + i / 10, "close": 102 + i / 10, "volume": 100}
            for i in range(count)]


def confluence_job():
    return {"structure": {"event": "BOS", "direction": "bull"},
            "impulse": {"start": 100, "end": 120}, "atr": 2,
            "htf_bias": "bull", "regime": {"durum": "trend"},
            "order_blocks": [{"type": "demand", "low": 104, "high": 109, "status": "active"}],
            "liquidity": [{"type": "buyside", "price": 140, "status": "active"}],
            "confirmation": {"confirmed": True}}


class GraphIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="piramit-integration-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.csv = self.base / "fixture.csv"
        self.csv.write_text("open,high,low,close,volume\n" + "100,103,99,102,10\n" * 48)
        self.job = {"state_dir": str(self.base / "state"), "veri": {"ohlcv_csv": str(self.csv)}}
        self.cal = {"sinyal_izni": True, "SONUC": "SYNTHETIC POSITIVE CONTROL",
                    "confluence_thresholds": {"atr_mult": 2.75, "min_rr": 4.5},
                    "thresholds_kaynak": {"method": "fixture", "train_end": 30, "holdout_start": 35},
                    "kalibrasyon": {"atr_mult": 2.75, "onerilen_min_rr": {"min_rr": 4.5}},
                    "evaluation": {"kind": "synthetic held-out producer stub"},
                    "gerekce": "fixture only"}

    def run_k2(self, calibration="normal", job=None):
        calls = []
        def run(script, args, girdi_job=None, **kwargs):
            name = Path(script).stem
            calls.append((name, copy.deepcopy(girdi_job), list(args)))
            if name == "setup_dogrulama":
                return response(self.cal, ok=calibration != "failure")
            if name == "smc_tespit":
                return response({"trend": "bull", "atr": 2,
                    "time_contract": {"status": "verified", "cutoff_ms": C0},
                    "confluence_job": confluence_job()})
            if name == "confluence":
                return response(confluence.synth(girdi_job))
            return response({}, ok=False)
        with patch.object(p, "_kos", side_effect=run):
            result = p.k2_ajan(job or self.job, self.base, {})
        return result, calls

    def test_producer_precedes_consumer_numeric_thresholds_affect_actual_stop(self):
        result, calls = self.run_k2()
        self.assertEqual([c[0] for c in calls], ["setup_dogrulama", "smc_tespit", "confluence"])
        cj = calls[2][1]
        self.assertEqual(cj["thresholds"], {"atr_mult": 2.75, "min_rr": 4.5})
        self.assertEqual(cj["thresholds_kaynak"], self.cal["thresholds_kaynak"])
        actual = result["motor_sonuclari"]["grafik-calisma"]
        baseline = confluence.synth(confluence_job())
        self.assertEqual(actual["gecersizlik_sl"], 94.5)
        self.assertNotEqual(actual["gecersizlik_sl"], baseline["gecersizlik_sl"])
        self.assertTrue(actual["validated_edge"])
        self.assertEqual(actual["kalibrasyon_koprusu"]["evaluation"], self.cal["evaluation"])

    def test_failed_and_disabled_calibration_keep_bias_without_signal(self):
        for mode in ("failure", "disabled", "negative"):
            with self.subTest(mode=mode):
                job = copy.deepcopy(self.job)
                if mode == "disabled":
                    job["setup_dogrulama"] = False
                if mode == "negative":
                    self.cal["sinyal_izni"] = False
                result, _ = self.run_k2(mode, job)
                gc = result["motor_sonuclari"]["grafik-calisma"]
                self.assertFalse(gc["validated_edge"])
                self.assertFalse(gc["sinyal_izni"])
                self.assertIn("BEKLE", gc["KARAR"])
                self.assertEqual(gc["structural_bias"], "bull")
                self.assertIsNotNone(gc["kosullu_senaryo"]["giris_orta"])

    def test_nested_or_unproven_thresholds_fail_closed(self):
        malformed = copy.deepcopy(self.cal)
        malformed["confluence_thresholds"]["min_rr"] = {"min_rr": 4.5}
        self.assertFalse(p._kalibrasyon_koprusu(malformed)["sinyal_izni"])
        malformed = copy.deepcopy(self.cal)
        malformed.pop("thresholds_kaynak")
        self.assertFalse(p._kalibrasyon_koprusu(malformed)["sinyal_izni"])
        malformed = copy.deepcopy(self.cal)
        malformed["sinyal_izni"] = "false"
        self.assertFalse(p._kalibrasyon_koprusu(malformed)["sinyal_izni"])

    def test_actual_small_calibration_producer_routes_numeric_descriptive_thresholds(self):
        self.cal = setup_dogrulama.simulate({"candles": bars(900000), "timeframe": "15m",
                                           "c0": C0, "params": {"mc_runs": 2}})
        result, calls = self.run_k2()
        actual = result["motor_sonuclari"]["grafik-calisma"]
        self.assertEqual(calls[-1][1]["thresholds"], self.cal["confluence_thresholds"])
        self.assertTrue(all(isinstance(value, (int, float))
                            for value in calls[-1][1]["thresholds"].values()))
        self.assertFalse(actual["validated_edge"])
        self.assertIn("BEKLE", actual["KARAR"])

    def test_missing_shuffle_probability_cannot_confirm_backtest(self):
        report = {"rapor": {"metrics": {"profit_factor": 8},
                             "monte_carlo": {"prob_profit": None,
                                  "valid_for_future_profit_probability": False}}}
        ok, reason = p._bt_dogrular(report)
        self.assertFalse(ok)
        self.assertIn("tanımlayıcı", reason)

    def test_explicit_c0_rejects_any_future_panel_not_staleness_tolerance(self):
        for minutes in (1 / 60000, 15, 239, 241):
            with self.subTest(minutes=minutes):
                accepted, reason = p._panel_tazeligi({"timestamp": C0 + round(minutes * 60000)},
                                                    "panel", C0, 240, C0)
                self.assertFalse(accepted)
                self.assertIn("C0 sonrası", reason)
        self.assertTrue(p._panel_tazeligi({"timestamp": C0}, "panel", C0, 240, C0)[0])
        self.assertTrue(p._panel_tazeligi({"timestamp": C0 - 239 * 60000}, "panel", C0, 240, C0)[0])
        self.assertFalse(p._panel_tazeligi({"timestamp": C0 - 241 * 60000}, "panel", C0, 240, C0)[0])

    def test_panel_timezone_and_conflicting_cutoff(self):
        equivalent = "2026-01-02T00:00:00+02:00"
        reference = p._c0_ms({"c0": equivalent})
        self.assertTrue(p._panel_tazeligi({"bar_utc": equivalent}, "panel", reference, 0, reference)[0])
        with self.assertRaises(ValueError):
            p._c0_ms({"c0": "2026-01-02T00:00:00"})
        with self.assertRaises(p.PiramitError):
            p._c0_ms({"c0": C0, "cutoff": C0 + 1})

    def three_timeframe_job(self):
        job = {"c0": C0, "state_dir": str(self.base / "state"), "veri": {}}
        for key, interval in (("m15", 900000), ("h1", 3600000), ("h4", 14400000)):
            data = bars(interval)
            # Latest higher-TF candle may have started before C0 but closes after it.
            self.assertGreater(data[-1]["close_time"], C0)
            path = self.base / f"{key}.json"
            path.write_text(json.dumps(data))
            job["veri"][key] = str(path)
        return job

    def test_actual_different_timeframes_share_c0_without_partial_htf(self):
        job = self.three_timeframe_job()
        aligned = p._aligned_price_job(job, self.base)
        closes = []
        for name in ("m15", "h1", "h4"):
            self.assertTrue(Path(aligned["veri"][name]).is_relative_to(self.base))
            original = json.loads(Path(job["veri"][name]).read_text())
            snapshot = json.loads(Path(aligned["veri"][name]).read_text())
            self.assertEqual(len(snapshot), len(original) - 1)
            self.assertTrue(all(r["close_time_ms"] <= C0 for r in snapshot))
            self.assertTrue(all(r["closed"] is True for r in snapshot))
            closes.append(snapshot[-1]["close_time_ms"])
        self.assertEqual(len(set(closes)), 3)
        result, calls = self.run_k2(job=job)
        self.assertTrue(result["timeframe_context"]["bridge_present"])
        self.assertEqual(result["timeframe_context"]["h1_vs_h4"], "aynı yön")
        smc_calls = [c[1] for c in calls if c[0] == "smc_tespit"]
        self.assertEqual([c["timeframe"] for c in smc_calls], ["15m", "1h", "4h"])
        main = smc_calls[0]
        self.assertEqual(main["bridge_timeframe"], "1h")
        self.assertEqual(main["htf_timeframe"], "4h")
        for key in ("candles", "htf_candles", "bridge_candles"):
            self.assertTrue(all(r["close_time_ms"] <= C0 for r in main[key]))
        self.assertTrue(all(c["c0"] == C0 for c in smc_calls))
        engine = next(c for c in calls if c[0] == "karar_motoru")
        self.assertTrue(all(Path(engine[2][i]).is_relative_to(self.base / "state") for i in (1, 3)))

    def test_untimed_explicit_cutoff_fails_before_any_engine(self):
        job = {**self.job, "c0": C0}
        with patch.object(p, "_kos") as motor:
            with self.assertRaises(ValueError):
                p.k2_ajan(job, self.base, {})
        motor.assert_not_called()

    def test_final_wait_and_missing_confirmation_cannot_become_clean_entry(self):
        k3 = {"seviyeler": {"x": {"yon": "long", "entry": 100, "stop": 95, "target": 115}}}
        k4 = {"rr_denetimi": {"x": {"verdict": "TUTARLI", "R_gercekci": 3}}, "verifier": {"x": {"confirmed": True}}}
        for decision, confirmation in (("NÖTR-BEKLE", True), ("LONG", None), ("LONG", False)):
            k4["verifier"]["x"]["confirmed"] = confirmation
            synth = {"YON_BIAS": "LONG", "KARAR": decision, "validated_edge": True}
            result = p._islem_kalitesi(k3, k4, synth)
            self.assertEqual(result["secilen"], {})
            self.assertEqual(result["seviyeler"], {})
            self.assertTrue(result["kosullu_senaryolar"])
            self.assertEqual(synth["YON_BIAS"], "LONG")
        k4["verifier"]["x"]["confirmed"] = True
        positive = p._islem_kalitesi(k3, k4, {"YON_BIAS": "LONG", "KARAR": "LONG", "validated_edge": True})
        self.assertEqual(positive["secilen"]["entry"], 100)
        k3["seviyeler"]["x"].update(entry=-2, stop=-3, target=-1)
        negative = p._islem_kalitesi(k3, k4, {"YON_BIAS": "LONG", "KARAR": "LONG", "validated_edge": True})
        self.assertEqual(negative["secilen"], {})

    def test_final_order_requires_same_levels_and_first_passage_confirmation(self):
        job = self.three_timeframe_job()
        synth = {"YON_BIAS": "LONG", "KARAR": "LONG", "validated_edge": True}
        quality = {"secilen": {"yon": "long", "entry": 100, "stop": 95, "target": 115, "confirmed": True}}
        def run(script, args, **kwargs):
            if Path(script).stem == "ilk_gecis":
                return response({"HAM": {"favori": "HEDEF", "p_hedef": .7, "p_stop": .3}})
            return response({"EMIR": "LIMIT LONG", "yon": "LONG", "adaylar": [copy.deepcopy(candidate)]})
        candidate = {"yon": "LONG", "giris": 100, "stop": 95, "hedef": 115}
        with patch.object(p, "_kos", side_effect=run):
            positive = p._emir_plani(job, self.base, {}, synth, quality)
            self.assertEqual(positive["adaylar"][0]["giris"], 100)
            candidate["giris"] = 101
            mismatch = p._emir_plani(job, self.base, {}, synth, quality)
            self.assertEqual(mismatch["EMIR"], "EMİR YOK")
            self.assertEqual(mismatch["adaylar"], [])
            self.assertTrue(mismatch["kosullu_senaryolar"])
        with patch.object(p, "_kos") as motor:
            blocked = p._emir_plani(job, self.base, {}, {**synth, "KARAR": "NÖTR-BEKLE"}, quality)
            self.assertEqual(blocked["EMIR"], "EMİR YOK")
            motor.assert_not_called()
        with patch.object(p, "_kos") as motor:
            invalidated = p._emir_plani(job, self.base, {}, {**synth, "invalidation_triggered": True}, quality)
            self.assertEqual(invalidated["EMIR"], "EMİR YOK")
            motor.assert_not_called()
        candidate["giris"] = 100
        with patch.object(p, "_kos", side_effect=run), patch.object(p, "_ilk_gecis_ekle", side_effect=lambda emir, _: emir):
            missing = p._emir_plani(job, self.base, {}, synth, quality)
            self.assertEqual(missing["EMIR"], "EMİR YOK")
            self.assertEqual(missing["adaylar"], [])

    def test_reordered_order_candidates_display_only_verified_levels(self):
        job = self.three_timeframe_job()
        synth = {"YON_BIAS": "LONG", "KARAR": "LONG", "validated_edge": True}
        quality = {"secilen": {"yon": "long", "entry": 100, "stop": 95, "target": 115, "confirmed": True}}
        first = {"yon": "LONG", "giris": 101, "stop": 95, "hedef": 116, "emir_tipi": "LIMIT"}
        verified = {"yon": "LONG", "giris": 100, "stop": 95, "hedef": 115, "emir_tipi": "LIMIT"}
        def run(script, args, **kwargs):
            return response({"EMIR": "LIMIT LONG @101", "yon": "LONG", "adaylar": [first, verified]})
        def passage(emir, _):
            return {**emir, "ilk_gecis": {"favori": "HEDEF", "p_hedef": .7, "p_stop": .3}}
        with patch.object(p, "_kos", side_effect=run), patch.object(p, "_ilk_gecis_ekle", side_effect=passage):
            result = p._emir_plani(job, self.base, {}, synth, quality)
        self.assertEqual(result["adaylar"], [verified])
        self.assertEqual(result["birincil"], verified)
        self.assertIn("@100", result["EMIR"])
        self.assertEqual(result["kosullu_senaryolar"], [first])

    def test_last_seal_clears_display_and_recorded_action_retaining_scenario(self):
        zirve = {"EMIR": "EMİR YOK — DENETİM", "YON_BIAS": "LONG", "sentez_karari": "LONG",
                 "validated_edge": True, "seviyeler": {"x": {"entry": 100}},
                 "emir_adaylari": [{"giris": 100}], "pozisyon_boyutu": 5}
        p._nihai_seviye_kapisi(zirve)
        self.assertEqual(zirve["seviyeler"], {})
        self.assertEqual(zirve["emir_adaylari"], [])
        self.assertEqual(zirve["YON_BIAS"], "LONG")
        self.assertTrue(zirve["kosullu_senaryolar"])
        record = p._anlik_goruntu({}, {}, {}, {"islem_kalitesi": {"secilen": {"entry": 100}}}, zirve)
        self.assertEqual(record["islem_seviyeleri"], {})

    def test_early_stop_never_uses_uncomputed_later_layers(self):
        with patch.object(p, "_sorusturma_kos", return_value={"ozet": "fixture"}), \
                patch.object(p, "_deftere_yaz") as write, \
                patch.object(p, "_atomik_yaz") as snapshot:
            result = p._durdur({"katmanlar": []}, "K1-LLM", "input unavailable")
        self.assertIn("DURDU", result["durum"])
        self.assertEqual(result["ZIRVE"]["seviyeler"], {})
        snapshot.assert_not_called()
        write.assert_called_once_with(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
