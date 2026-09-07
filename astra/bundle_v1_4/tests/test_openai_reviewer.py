"""HTTP response fixtures verify parsing/bindings, not a live OpenAI call."""
import copy
import io
import json
import unittest
from unittest.mock import patch
from astra_host import ASSESSMENT_SCHEMA, SEMANTIC_POLICY, transport_schema
from astra_reference import Rejected, canonical, digest
from astra_openai_reviewer import build_opener, review


class Response(io.BytesIO):
    status = 200


class Opener:
    def __init__(self, body):
        self.body, self.requests = body, []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return Response(canonical(self.body))


class OpenAIReviewerTransportTests(unittest.TestCase):
    def setUp(self):
        self.request = dict(instructions=SEMANTIC_POLICY, assessment_schema=ASSESSMENT_SCHEMA,
                            wire_schema=transport_schema(ASSESSMENT_SCHEMA),
                            http_timeout=55.0,
                            expected_model="gpt-6-astra", expected_effort="max")
        self.request["request_digest"] = digest(self.request)
        self.assessment = dict(claim_verdicts=[dict(claim_id="a:c1", verdict="supported",
            source_ids=[], excerpts=[], reason="HTTP fixture", conditions_preserved=True,
            counterevidence_checked=True)], comparison_verdicts=[], candidate_review_passed=True,
            coverage_review_passed=True, numeric_inventory_complete=True, comparison_inventory_complete=True,
            unresolved_contradictions=[], reason="HTTP fixture")
        self.body = dict(id="resp_fixture", status="completed", model="gpt-6-astra",
                         reasoning={"effort":"max"}, output=[dict(type="message", content=[
                             dict(type="output_text", text=json.dumps(self.assessment))])])

    def call(self, body=None, request=None):
        self.opener = Opener(self.body if body is None else body)
        with patch.dict("os.environ", {"OPENAI_API_KEY":"fixture-not-a-real-key"}, clear=True):
            return review(self.request if request is None else request, opener=self.opener)

    def test_request_uses_real_responses_contract_and_bound_receipt(self):
        result = self.call()
        sent = json.loads(self.opener.requests[0][0].data)
        self.assertEqual(sent["reasoning"], {"effort":"max"})
        self.assertEqual(sent["text"]["format"]["schema"], transport_schema(ASSESSMENT_SCHEMA))
        self.assertFalse(sent["store"])
        self.assertEqual(len(self.opener.requests), 1)
        self.assertEqual(result["request_digest"], self.request["request_digest"])
        self.assertEqual(result["reviewer_record_id"], "openai:resp_fixture")

    def test_missing_credential_never_calls_network(self):
        opener = Opener(self.body)
        with patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(Rejected, "CREDENTIAL_MISSING"):
            review(self.request, opener=opener)
        self.assertEqual(opener.requests, [])

    def test_changed_request_is_rejected_before_network(self):
        request = copy.deepcopy(self.request); request["extra"] = True
        with self.assertRaisesRegex(Rejected, "REQUEST_DIGEST"):
            self.call(request=request)
        self.assertEqual(self.opener.requests, [])

    def test_refusal_closes_gate(self):
        self.body["output"][0]["content"] = [dict(type="refusal", refusal="fixture refusal")]
        with self.assertRaisesRegex(Rejected, "PROVIDER_REFUSAL"):
            self.call()

    def test_incomplete_response_closes_gate(self):
        self.body["status"] = "incomplete"
        with self.assertRaisesRegex(Rejected, "PROVIDER_INCOMPLETE"):
            self.call()

    def test_unverified_model_and_effort_close_gate(self):
        for field, value in (("model", "different"), ("reasoning", {}), ("reasoning", None)):
            with self.subTest(field=field, value=value):
                body=copy.deepcopy(self.body); body[field]=value
                with self.assertRaises(Rejected):
                    self.call(body=body)

    def test_missing_provider_receipt_is_rejected(self):
        del self.body["id"]
        with self.assertRaisesRegex(Rejected, "PROVIDER_RECEIPT_REQUIRED"):
            self.call()

    def test_malformed_response_shapes_are_controlled(self):
        for value in (None, {}, [None], [{"content":None}], [{"content":[None]}]):
            with self.subTest(value=value):
                body=copy.deepcopy(self.body); body["output"]=value
                with self.assertRaises(Rejected):
                    self.call(body=body)

    def test_snapshot_model_name_is_accepted_and_recorded(self):
        # api_uyum-3: providers answer with a dated snapshot of the requested model.
        self.body["model"] = "gpt-6-astra-2026-09-01"
        self.assertEqual(self.call()["provider_model"], "gpt-6-astra-2026-09-01")

    def test_unrelated_model_is_rejected(self):
        self.body["model"] = "gpt-5"
        with self.assertRaisesRegex(Rejected, "MODEL_MISMATCH"):
            self.call()

    def test_http_error_classes_are_distinguished_without_body(self):
        # api_uyum-6 / K-13: the caller learns the class, never the provider body.
        import urllib.error
        for code, expected in ((400, "HTTP_4XX"), (429, "HTTP_429"), (503, "HTTP_5XX")):
            with self.subTest(code=code):
                class Failing:
                    def open(self, request, timeout):
                        raise urllib.error.HTTPError(request.full_url, code, "x", {},
                                                     io.BytesIO(b"secret body"))
                with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}, clear=True), \
                        self.assertRaisesRegex(Rejected, expected) as cm:
                    review(self.request, opener=Failing())
                self.assertNotIn("secret", str(cm.exception))

    def test_incomplete_reason_is_reported(self):
        self.body["status"] = "incomplete"
        self.body["incomplete_details"] = {"reason": "max_output_tokens"}
        with self.assertRaisesRegex(Rejected, "INCOMPLETE:max_output_tokens"):
            self.call()

    def test_reasoning_items_are_ignored(self):
        # api_uyum-8: Responses output interleaves reasoning items with messages.
        self.body["output"].insert(0, dict(type="reasoning", summary=[]))
        self.assertEqual(self.call()["provider_model"], "gpt-6-astra")

    def test_transport_schema_has_no_length_constraints(self):
        # api_uyum-1: server acceptance of length keywords under strict is unverified,
        # so they are not sent; enum/required/additionalProperties still are.
        wire = transport_schema(ASSESSMENT_SCHEMA)
        text = json.dumps(wire)
        for key in ("minLength", "maxLength", "minItems", "maxItems"):
            self.assertNotIn(key, text)
        self.assertIn("additionalProperties", text)
        self.assertIn("required", text)
        self.call()
        self.assertEqual(json.loads(self.opener.requests[0][0].data)["text"]["format"]["schema"], wire)

    def test_wire_schema_must_match_the_host_transport_schema(self):
        request = copy.deepcopy(self.request)
        request["wire_schema"] = {"type": "object"}
        request["request_digest"] = digest({k: v for k, v in request.items() if k != "request_digest"})
        with self.assertRaisesRegex(Rejected, "REVIEW_POLICY_MISMATCH"):
            self.call(request=request)

    def test_proxy_comes_only_from_config_env(self):
        # api_uyum-13: the ambient HTTPS_PROXY is never trusted; configuration is explicit.
        with patch.dict("os.environ", {"OPENAI_API_KEY": "k", "HTTPS_PROXY": "http://ignored:1",
                                       "ASTRA_HTTPS_PROXY": "http://cfg:2"}, clear=True):
            proxies = [h.proxies for h in build_opener().handlers if hasattr(h, "proxies")]
        self.assertEqual(proxies, [{"https": "http://cfg:2", "http": "http://cfg:2"}])

    def test_opener_without_config_uses_no_proxy(self):
        # urllib drops a ProxyHandler with no entries, so "no proxy handler" is the
        # observable form of "no proxy"; the ambient HTTPS_PROXY stays unused.
        with patch.dict("os.environ", {"OPENAI_API_KEY": "k", "HTTPS_PROXY": "http://ignored:1"},
                        clear=True):
            proxies = [h.proxies for h in build_opener().handlers if getattr(h, "proxies", None)]
        self.assertEqual(proxies, [])

    def test_http_timeout_comes_from_the_request(self):
        # kod_hata-10 / api_uyum-9: the adapter used a fixed 45s while the host used its
        # own deadline, so one of the two clocks was always wrong.
        self.call()
        self.assertEqual(self.opener.requests[0][1], 55.0)

    def test_missing_or_impossible_http_timeout_is_rejected(self):
        for value in (None, 0, -1, 301, "45"):
            with self.subTest(value=value):
                request = copy.deepcopy(self.request)
                request["http_timeout"] = value
                request["request_digest"] = digest(
                    {k: v for k, v in request.items() if k != "request_digest"})
                with self.assertRaisesRegex(Rejected, "REVIEW_TIMEOUT_CONFIGURATION"):
                    self.call(request=request)

    def test_non_error_non_200_response_is_rejected(self):
        # test_kapsam-11: an opener that returns a non-200 without raising HTTPError.
        class Odd(io.BytesIO):
            status = 204

        class OddOpener:
            requests = []

            def open(self, request, timeout):
                return Odd(b"{}")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "k"}, clear=True), \
                self.assertRaisesRegex(Rejected, "REVIEW_PROVIDER_HTTP_STATUS"):
            review(self.request, opener=OddOpener())


if __name__ == "__main__":
    unittest.main()
