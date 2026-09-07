import copy
import unittest
from astra_reference import Rejected, digest
from astra_compare import compare_table

NOW = "2026-09-06T12:00:00+00:00"


def fixture(values=("100", "120")):
    rows, sources, contents = [], [], {}
    for i, value in enumerate(values):
        sid = f"s{i}"
        content = f"Measured latency: {value} ms. Test fixture, not a real benchmark."
        contents[sid] = content
        sources.append({
            "source_id": sid, "kind": "TOOL", "locator": f"fixture://{sid}",
            "content_digest": digest(content),
            "retrieved_at": "2026-09-06T11:00:00+00:00",
            "as_of": "2026-09-06T10:00:00+00:00",
            "valid_until": "2026-09-07T00:00:00+00:00",
            "access_record_id": f"LOCAL_FIXTURE_{i}",
        })
        rows.append({"entity": f"candidate{i}", "metric": "latency",
                     "definition": "median completion latency", "unit": "ms",
                     "period": "same fixed measurement window",
                     "population": "same fixed query set",
                     "method": "same harness, hardware and repeat count",
                     "source_id": sid, "quote": content, "value": value})
    return rows, sources, contents


def compare(data, direction="lower_is_better"):
    return compare_table(*data, direction=direction, now=NOW)


class ComparisonTests(unittest.TestCase):
    def test_same_context_orders_observed_values_without_truth_claim(self):
        result = compare(fixture())
        self.assertEqual(result["observed_leaders"], ["candidate0"])
        self.assertEqual(result["rows"][0]["exact"], "100")
        self.assertFalse(result["semantic_support_verified"])
        self.assertFalse(result["source_access_authenticated"])
        self.assertFalse(result["production_approval"])
        proof = result.pop("comparison_digest")
        self.assertEqual(proof, digest(result))

    def test_mismatched_measurement_context_is_rejected(self):
        for key in ("metric", "definition", "unit", "period", "population", "method"):
            with self.subTest(key=key):
                data = fixture()
                data[0][1][key] = "different"
                with self.assertRaisesRegex(Rejected, "NOT_COMPARABLE"):
                    compare(data)

    def test_missing_value_is_not_zero(self):
        data = fixture()
        data[0][1]["value"] = None
        with self.assertRaisesRegex(Rejected, "COMPARISON_INCOMPLETE"):
            compare(data)

    def test_missing_snapshot_cannot_be_an_opened_source(self):
        data = fixture()
        del data[2]["s1"]
        with self.assertRaisesRegex(Rejected, "SOURCE_SNAPSHOT_MISSING"):
            compare(data)

    def test_changed_source_snapshot_invalidates_binding(self):
        data = fixture()
        data[2]["s1"] += " Changed."
        with self.assertRaisesRegex(Rejected, "SOURCE_CONTENT_DIGEST_MISMATCH"):
            compare(data)

    def test_invented_excerpt_is_rejected(self):
        data = fixture()
        data[0][1]["quote"] = "Measured latency: 120 ms. This quotation is invented."
        with self.assertRaisesRegex(Rejected, "QUOTE_NOT_IN_SNAPSHOT"):
            compare(data)

    def test_number_substring_is_not_evidence(self):
        data = fixture()
        data[0][0]["value"] = "10"
        with self.assertRaisesRegex(Rejected, "VALUE_NOT_IN_QUOTE"):
            compare(data)

    def test_source_number_sign_cannot_be_dropped(self):
        for signed in ("-100", "+100"):
            with self.subTest(signed=signed):
                data = fixture((signed, "120"))
                data[0][0]["value"] = "100"
                with self.assertRaisesRegex(Rejected, "VALUE_NOT_IN_QUOTE"):
                    compare(data)

    def test_unicode_sign_and_separators_cannot_be_dropped(self):
        # kod_hata-6: only ASCII +/- were guarded; U+2212 and ratio separators slipped through.
        for quote in ("Measured latency: −100 ms.", "Measured latency: 100/200 ms.", "ratio 100:200"):
            with self.subTest(quote=quote):
                data = fixture()
                data[2]["s0"] = quote
                data[0][0]["quote"] = quote
                data[0][0]["value"] = "100"
                data[1][0]["content_digest"] = digest(quote)
                with self.assertRaisesRegex(Rejected, "VALUE_NOT_IN_QUOTE"):
                    compare(data)

    def test_stale_future_or_unzoned_sources_are_rejected(self):
        for key, value in (("valid_until", "2026-09-05T00:00:00+00:00"),
                           ("as_of", "2026-09-08T00:00:00+00:00"),
                           ("retrieved_at", "2026-09-06T11:00:00")):
            with self.subTest(key=key):
                data = fixture()
                data[1][0][key] = value
                with self.assertRaises(Rejected):
                    compare(data)

    def test_duplicate_candidate_is_not_independent_coverage(self):
        data = fixture()
        data[0][1]["entity"] = data[0][0]["entity"]
        with self.assertRaisesRegex(Rejected, "DUPLICATE_ID"):
            compare(data)

    def test_tie_does_not_invent_a_unique_leader(self):
        result = compare(fixture(("100", "100.0")))
        self.assertEqual(result["observed_leaders"], ["candidate0", "candidate1"])

    def test_decimal_and_direction_are_exact(self):
        data = fixture(("0.1234567890123456789", "0.1234567890123456790"))
        self.assertEqual(compare(data)["observed_leaders"], ["candidate0"])
        self.assertEqual(compare(data, "higher_is_better")["observed_leaders"], ["candidate1"])

    def test_formula_nonfinite_and_boolean_cannot_replace_observation(self):
        for value in ("2+2", "NaN", "Infinity", True):
            with self.subTest(value=value):
                data = fixture()
                data[0][0]["value"] = value
                with self.assertRaises(Rejected):
                    compare(data)

    def test_direction_must_be_explicit(self):
        with self.assertRaisesRegex(Rejected, "COMPARISON_DIRECTION_REQUIRED"):
            compare(fixture(), "guess")

    def test_input_mutation_does_not_change_result(self):
        data = fixture()
        result = compare(data)
        frozen = copy.deepcopy(result)
        data[0][0]["quote"] = "modified"
        data[1][0]["access_record_id"] = "modified"
        self.assertEqual(result, frozen)


if __name__ == "__main__":
    unittest.main()
