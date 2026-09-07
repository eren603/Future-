"""Bounded local comparison checks, not a factual truth or source-access oracle.

The host supplies actual source snapshots and their access records. This module
checks bindings, identical declared measurement contexts and exact observed
values. Whether an excerpt supports the declared interpretation still requires
semantic review. No HTTP request, LLM call, installation or production approval.
"""
from fractions import Fraction
import re
from astra_reference import (
    Rejected, ID, SOURCE_SCHEMA, array, bounded_json, canonical, digest,
    exact_math, obj, stamp, string, timestamp, unique, validate,
)

CONTEXT_KEYS = ("metric", "definition", "unit", "period", "population", "method")
ROW_SCHEMA = obj({
    "entity": ID, **{key: string(1000) for key in CONTEXT_KEYS},
    "source_id": ID, "quote": string(4000), "value": string(80, nullable=True),
})
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def compare_table(rows, sources, contents, *, direction, now=None):
    """Rank only comparable, observed values. Raise Rejected on incomplete input.

`contents` maps source IDs to the text snapshots actually captured by the host.
Their digest convention is astra_reference.digest(text), i.e. canonical JSON
UTF-8 string bytes. `now` is a trusted host clock override for reproducible tests.
This checker cannot authenticate a caller or replace a source/claim reviewer.
"""
    rows, sources, contents = [bounded_json(canonical(x)) for x in
                               (rows, sources, contents)]
    validate(rows, array(ROW_SCHEMA, 64, 2))
    validate(sources, array(SOURCE_SCHEMA, 320, 1))
    if type(contents) is not dict:
        raise Rejected("SOURCE_CONTENT_TYPE")
    if direction not in {"lower_is_better", "higher_is_better"}:
        raise Rejected("COMPARISON_DIRECTION_REQUIRED")
    unique([row["entity"] for row in rows])
    unique([source["source_id"] for source in sources])
    source_map = {source["source_id"]: source for source in sources}
    clock = timestamp(stamp() if now is None else now)
    context = {key: rows[0][key] for key in CONTEXT_KEYS}
    checked, values = [], []
    for row in rows:
        if any(row[key] != context[key] for key in CONTEXT_KEYS):
            raise Rejected("NOT_COMPARABLE")
        value = row["value"]
        if value is None:
            raise Rejected("COMPARISON_INCOMPLETE")
        if NUMBER.fullmatch(value) is None:
            raise Rejected("OBSERVED_NUMBER_REQUIRED")
        sid = row["source_id"]
        if sid not in source_map or sid not in contents:
            raise Rejected("SOURCE_SNAPSHOT_MISSING")
        source, content = source_map[sid], contents[sid]
        if type(content) is not str or not content.strip():
            raise Rejected("SOURCE_CONTENT_TYPE")
        if source["content_digest"] != digest(content):
            raise Rejected("SOURCE_CONTENT_DIGEST_MISMATCH")
        if not timestamp(source["as_of"]) <= timestamp(source["retrieved_at"]) <= clock <= timestamp(source["valid_until"]):
            raise Rejected("SOURCE_STALE_OR_TIME")
        if row["quote"] not in content:
            raise Rejected("QUOTE_NOT_IN_SNAPSHOT")
        # Do not mistake 10 inside 100 for support for the value 10.
        numeric_literal = r"(?<![\w.,+\-])" + re.escape(value) + r"(?![\w.,])"
        if re.search(numeric_literal, row["quote"]) is None:
            raise Rejected("VALUE_NOT_IN_QUOTE")
        proof = exact_math(value)
        values.append(Fraction(proof["exact"]))
        checked.append({**row, "source_kind": source["kind"],
                        "content_digest": source["content_digest"],
                        "access_record_id": source["access_record_id"],
                        "exact": proof["exact"]})
    optimum = min(values) if direction == "lower_is_better" else max(values)
    result = {
        "status": "LOCAL_COMPARISON_VALIDATED", "production_approval": False,
        "semantic_support_verified": False, "source_access_authenticated": False,
        "ranking_scope": "OBSERVED_VALUES_ONLY", "context": context,
        "direction": direction, "rows": checked,
        "observed_leaders": [row["entity"] for row, val in zip(rows, values)
                             if val == optimum],
    }
    result["comparison_digest"] = digest(result)
    return bounded_json(canonical(result))
