"""HTTP response fixtures verify parsing/bindings, not a live OpenAI call."""
import copy
import io
import json
import unittest
from unittest.mock import patch
from astra_host import ASSESSMENT_SCHEMA, SEMANTIC_POLICY
from astra_reference import Rejected, canonical, digest
from astra_openai_reviewer import review


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
        self.assertEqual(sent["text"]["format"]["schema"], ASSESSMENT_SCHEMA)
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


if __name__ == "__main__":
    unittest.main()
