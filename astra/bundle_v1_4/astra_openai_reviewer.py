"""Bounded OpenAI Responses transport for the mandatory semantic reviewer.

One request, no retries or tools. Credentials come only from OPENAI_API_KEY.
Running/importing the package never invokes this adapter automatically.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from astra_reference import Rejected, WIRE_LIMIT, bounded_json, canonical, digest, validate
from astra_host import ASSESSMENT_SCHEMA, REVIEW_RESPONSE_SCHEMA, SEMANTIC_POLICY

ENDPOINT = "https://api.openai.com/v1/responses"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def review(request, *, opener=None):
    if type(request) is not dict:
        raise Rejected("REVIEW_REQUEST_SHAPE")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise Rejected("REVIEWER_CREDENTIAL_MISSING")
    supplied = request.get("request_digest")
    unsigned = {k: v for k, v in request.items() if k != "request_digest"}
    if supplied != digest(unsigned):
        raise Rejected("REVIEW_REQUEST_DIGEST")
    if request.get("instructions") != SEMANTIC_POLICY or request.get("assessment_schema") != ASSESSMENT_SCHEMA:
        raise Rejected("REVIEW_POLICY_MISMATCH")
    if request.get("expected_model") != "gpt-6-astra" or request.get("expected_effort") not in {"low", "medium", "high", "xhigh", "max"}:
        raise Rejected("UNSUPPORTED_REVIEWER_CONFIGURATION")
    body = dict(model=request["expected_model"], reasoning={"effort": request["expected_effort"]},
                instructions=SEMANTIC_POLICY, input=canonical(request).decode("utf-8"),
                store=False, max_output_tokens=16384,
                text={"format": {"type": "json_schema", "name": "astra_semantic_review",
                                 "strict": True, "schema": ASSESSMENT_SCHEMA}})
    http_request = urllib.request.Request(ENDPOINT, data=canonical(body), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    if opener is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(http_request, timeout=45) as response:
            if response.status != 200:
                raise Rejected("REVIEW_PROVIDER_HTTP_STATUS")
            raw = response.read(WIRE_LIMIT + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        # Do not print request headers, credentials, or a provider error body.
        raise Rejected("REVIEW_PROVIDER_UNAVAILABLE") from exc
    data = bounded_json(raw)
    if type(data) is not dict or data.get("status") != "completed":
        raise Rejected("REVIEW_PROVIDER_INCOMPLETE")
    if data.get("model") != request["expected_model"]:
        raise Rejected("REVIEW_PROVIDER_MODEL_MISMATCH")
    if type(data.get("reasoning")) is not dict or data["reasoning"].get("effort") != request["expected_effort"]:
        raise Rejected("REVIEW_PROVIDER_EFFORT_UNVERIFIED")
    parts = []
    if type(data.get("output")) is not list:
        raise Rejected("REVIEW_PROVIDER_OUTPUT_SHAPE")
    for message in data["output"]:
        if type(message) is not dict or type(message.get("content", [])) is not list:
            raise Rejected("REVIEW_PROVIDER_OUTPUT_SHAPE")
        for content in message.get("content", []):
            if type(content) is not dict:
                raise Rejected("REVIEW_PROVIDER_OUTPUT_SHAPE")
            if content.get("type") == "refusal":
                raise Rejected("REVIEW_PROVIDER_REFUSAL")
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    if len(parts) != 1 or type(parts[0]) is not str:
        raise Rejected("REVIEW_PROVIDER_OUTPUT_SHAPE")
    assessment = bounded_json(parts[0].encode("utf-8"))
    validate(assessment, ASSESSMENT_SCHEMA)
    if type(data.get("id")) is not str or not data["id"].startswith("resp_"):
        raise Rejected("REVIEW_PROVIDER_RECEIPT_REQUIRED")
    result = dict(request_digest=supplied, reviewer_record_id="openai:" + data["id"],
                  provider_model=data["model"], provider_effort=data["reasoning"]["effort"],
                  assessment=assessment)
    validate(result, REVIEW_RESPONSE_SCHEMA)
    return result


def main():
    try:
        request = bounded_json(sys.stdin.buffer.read(WIRE_LIMIT + 1))
        result = review(request)
        sys.stdout.buffer.write(canonical(result))
        return 0
    except Rejected as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
