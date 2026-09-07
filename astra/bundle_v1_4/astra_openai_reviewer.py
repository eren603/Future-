"""Bounded OpenAI Responses transport for the mandatory semantic reviewer.

One request, no retries or tools. Credentials come only from OPENAI_API_KEY.
Running/importing the package never invokes this adapter automatically.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from astra_reference import Rejected, WIRE_LIMIT, bounded_json, canonical, digest, validate
from astra_host import (ASSESSMENT_SCHEMA, REVIEW_RESPONSE_SCHEMA, SEMANTIC_POLICY,
                        transport_schema)

ENDPOINT = "https://api.openai.com/v1/responses"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_opener():
    """Transport configuration comes from the host, never from the ambient environment."""
    proxy = os.environ.get("ASTRA_HTTPS_PROXY")
    handlers = [urllib.request.ProxyHandler({"https": proxy, "http": proxy} if proxy else {}),
                NoRedirect()]
    bundle = os.environ.get("ASTRA_CA_BUNDLE")
    if bundle:
        handlers.append(urllib.request.HTTPSHandler(
            context=ssl.create_default_context(cafile=bundle)))
    return urllib.request.build_opener(*handlers)


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
    if (request.get("instructions") != SEMANTIC_POLICY
            or request.get("assessment_schema") != ASSESSMENT_SCHEMA
            or request.get("wire_schema") != transport_schema(ASSESSMENT_SCHEMA)):
        raise Rejected("REVIEW_POLICY_MISMATCH")
    http_timeout = request.get("http_timeout")
    if type(http_timeout) not in (int, float) or not 0 < http_timeout <= 300:
        raise Rejected("REVIEW_TIMEOUT_CONFIGURATION")
    if request.get("expected_model") != "gpt-6-astra" or request.get("expected_effort") not in {"low", "medium", "high", "xhigh", "max"}:
        raise Rejected("UNSUPPORTED_REVIEWER_CONFIGURATION")
    body = dict(model=request["expected_model"], reasoning={"effort": request["expected_effort"]},
                instructions=SEMANTIC_POLICY, input=canonical(request).decode("utf-8"),
                store=False, max_output_tokens=16384,
                text={"format": {"type": "json_schema", "name": "astra_semantic_review",
                                 "strict": True, "schema": request["wire_schema"]}})
    http_request = urllib.request.Request(ENDPOINT, data=canonical(body), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    if opener is None:
        opener = build_opener()
    try:
        with opener.open(http_request, timeout=http_timeout) as response:
            if response.status != 200:
                raise Rejected("REVIEW_PROVIDER_HTTP_STATUS")
            raw = response.read(WIRE_LIMIT + 1)
    except urllib.error.HTTPError as exc:
        # The class is reported; the provider body is never read, logged, or raised.
        # 429 is separated from the other 4XX codes: it is transient, and lumping it in
        # with a permanent 400 hides that. There is still NO automatic retry.
        if exc.code == 429:
            raise Rejected("REVIEW_PROVIDER_HTTP_429") from None
        raise Rejected("REVIEW_PROVIDER_HTTP_4XX" if 400 <= exc.code < 500
                       else "REVIEW_PROVIDER_HTTP_5XX") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Do not print request headers, credentials, or a provider error body.
        raise Rejected("REVIEW_PROVIDER_UNAVAILABLE") from exc
    data = bounded_json(raw)
    if type(data) is not dict:
        raise Rejected("REVIEW_PROVIDER_OUTPUT_SHAPE")
    if data.get("status") != "completed":
        details = data.get("incomplete_details")
        reason = details.get("reason") if type(details) is dict else None
        raise Rejected("REVIEW_PROVIDER_INCOMPLETE:" + str(reason or "unknown"))
    served = data.get("model")
    expected = request["expected_model"]
    if type(served) is not str or not (served == expected or served.startswith(expected + "-")):
        raise Rejected("REVIEW_PROVIDER_MODEL_MISMATCH")
    if type(data.get("reasoning")) is not dict or data["reasoning"].get("effort") != request["expected_effort"]:
        raise Rejected("REVIEW_PROVIDER_EFFORT_UNVERIFIED")
    parts = []
    if type(data.get("output")) is not list:
        raise Rejected("REVIEW_PROVIDER_OUTPUT_SHAPE")
    for message in data["output"]:
        if type(message) is not dict:
            raise Rejected("REVIEW_PROVIDER_OUTPUT_SHAPE")
        if message.get("type") != "message":
            continue  # reasoning and tool items are not the assessment
        if type(message.get("content", [])) is not list:
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
