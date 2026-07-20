#!/usr/bin/env python3
"""Validate a local table against a fail-closed JSON data contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data_core import (
    DataContractError,
    decimal_value,
    environment_record,
    json_safe,
    load_table,
    numeric_series,
    write_json,
)


def _round(value: Any, digits: int = 12) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


def _examples(mask: pd.Series, limit: int = 20) -> list[Any]:
    return [json_safe(value) for value in mask.index[mask.fillna(False)].tolist()[:limit]]


def _result(name: str, passed: bool, *, required: bool = True, **evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "required": bool(required), "evidence": evidence}


def _compare(actual: Any, operator: str, expected: Any, *, rtol: float, atol: float) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "lt":
        return actual < expected
    if operator == "le":
        return actual <= expected
    if operator == "gt":
        return actual > expected
    if operator == "ge":
        return actual >= expected
    if operator == "close":
        return bool(np.isclose(float(actual), float(expected), rtol=rtol, atol=atol))
    raise DataContractError(f"Unsupported comparison operator: {operator}")


def validate_column(frame: pd.DataFrame, name: str, rules: dict[str, Any]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    required_field = bool(rules.get("required", True))
    if name not in frame.columns:
        outputs.append(_result(f"column:{name}:exists", not required_field, required=required_field, missing=True))
        return outputs
    series = frame[name]
    outputs.append(_result(f"column:{name}:exists", True, required=required_field))

    if rules.get("nullable") is False:
        mask = series.isna()
        outputs.append(_result(f"column:{name}:not_null", not mask.any(), failures=int(mask.sum()), example_rows=_examples(mask)))
    if rules.get("unique") is True:
        mask = series.notna() & series.duplicated(keep=False)
        outputs.append(_result(f"column:{name}:unique_non_null", not mask.any(), failures=int(mask.sum()), example_rows=_examples(mask)))

    expected_type = rules.get("type")
    parsed_numeric: pd.Series | None = None
    if expected_type:
        expected_type = str(expected_type).lower()
        non_null = series.notna()
        if expected_type == "numeric":
            parsed_numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
            invalid = non_null & parsed_numeric.isna()
        elif expected_type == "integer":
            parsed_numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
            invalid = non_null & (parsed_numeric.isna() | ((parsed_numeric % 1) != 0))
        elif expected_type == "datetime":
            parsed = pd.to_datetime(series, errors="coerce", utc=True, format="mixed")
            invalid = non_null & parsed.isna()
        elif expected_type == "string":
            invalid = non_null & ~series.map(lambda value: isinstance(value, str))
        elif expected_type == "boolean":
            allowed = {True, False, 0, 1, "0", "1", "true", "false", "True", "False"}
            invalid = non_null & ~series.isin(allowed)
        else:
            raise DataContractError(f"column {name} has unsupported type rule {expected_type!r}")
        outputs.append(_result(f"column:{name}:type:{expected_type}", not invalid.any(), failures=int(invalid.sum()), example_rows=_examples(invalid)))

    if "min" in rules or "max" in rules:
        parsed_numeric = parsed_numeric if parsed_numeric is not None else numeric_series(frame, name)
        invalid_parse = series.notna() & parsed_numeric.isna()
        if invalid_parse.any():
            outputs.append(_result(f"column:{name}:range_numeric_parse", False, failures=int(invalid_parse.sum()), example_rows=_examples(invalid_parse)))
        if "min" in rules:
            mask = parsed_numeric.notna() & (parsed_numeric < float(rules["min"]))
            outputs.append(_result(f"column:{name}:min", not mask.any(), expected=rules["min"], failures=int(mask.sum()), example_rows=_examples(mask)))
        if "max" in rules:
            mask = parsed_numeric.notna() & (parsed_numeric > float(rules["max"]))
            outputs.append(_result(f"column:{name}:max", not mask.any(), expected=rules["max"], failures=int(mask.sum()), example_rows=_examples(mask)))

    if "allowed_values" in rules:
        allowed = rules["allowed_values"]
        if not isinstance(allowed, list):
            raise DataContractError(f"column {name} allowed_values must be a list")
        mask = series.notna() & ~series.isin(allowed)
        outputs.append(_result(f"column:{name}:allowed_values", not mask.any(), allowed=allowed, failures=int(mask.sum()), example_rows=_examples(mask)))
    if "regex" in rules:
        try:
            pattern = re.compile(str(rules["regex"]))
        except re.error as exc:
            raise DataContractError(f"column {name} has invalid regex: {exc}") from exc
        mask = series.notna() & ~series.astype(str).map(lambda value: bool(pattern.fullmatch(value)))
        outputs.append(_result(f"column:{name}:regex", not mask.any(), pattern=pattern.pattern, failures=int(mask.sum()), example_rows=_examples(mask)))
    return outputs


def scalar_check(frame: pd.DataFrame, check: dict[str, Any], index: int) -> dict[str, Any]:
    kind = str(check.get("kind", ""))
    required = bool(check.get("required", True))
    operator = str(check.get("operator", "eq"))
    if "expected" not in check:
        raise DataContractError(f"check {index} requires expected")
    expected = check["expected"]
    rtol, atol = float(check.get("rtol", 1e-9)), float(check.get("atol", 1e-12))
    column = check.get("column")
    if kind == "row_count":
        actual: Any = int(len(frame))
    elif kind in {"sum", "mean", "count", "nunique"}:
        if not column or column not in frame.columns:
            raise DataContractError(f"check {index} references missing column {column!r}")
        mode = str(check.get("numeric_mode", "float")).lower()
        if kind == "count":
            actual = int(frame[column].notna().sum())
        elif kind == "nunique":
            actual = int(frame[column].nunique(dropna=True))
        elif mode == "decimal":
            values = [value for value in (decimal_value(raw) for raw in frame[column].tolist()) if value is not None]
            if not values:
                raise DataContractError(f"check {index} has no decimal values")
            actual = sum(values, Decimal(0)) if kind == "sum" else sum(values, Decimal(0)) / Decimal(len(values))
            expected = decimal_value(expected)
            if expected is None:
                raise DataContractError(f"check {index} expected cannot be null")
            if operator == "close":
                tolerance = Decimal(str(atol)) + Decimal(str(rtol)) * abs(expected)
                passed = abs(actual - expected) <= tolerance
                return _result(str(check.get("name", f"check:{index}:{kind}")), passed, required=required, actual=actual, expected=expected, tolerance=tolerance)
        else:
            values = numeric_series(frame, str(column)).dropna()
            if values.empty:
                raise DataContractError(f"check {index} has no finite numeric values")
            actual = float(values.sum()) if kind == "sum" else float(values.mean())
    else:
        raise DataContractError(f"check {index} has unsupported scalar kind {kind!r}")
    if not isinstance(actual, Decimal):
        try:
            expected = float(expected)
        except (TypeError, ValueError) as exc:
            raise DataContractError(f"check {index} expected must be numeric") from exc
    passed = _compare(actual, operator, expected, rtol=rtol, atol=atol)
    return _result(str(check.get("name", f"check:{index}:{kind}")), passed, required=required, actual=actual, expected=expected, operator=operator, rtol=rtol, atol=atol)


def relation_check(frame: pd.DataFrame, check: dict[str, Any], index: int) -> dict[str, Any]:
    left_name = str(check.get("left", ""))
    if left_name not in frame.columns:
        raise DataContractError(f"relation check {index} references missing left column {left_name!r}")
    right_spec = check.get("right")
    if not isinstance(right_spec, dict) or ("column" in right_spec) == ("value" in right_spec):
        raise DataContractError(f"relation check {index} right must contain exactly one of column or value")
    operator = str(check.get("operator", "eq"))
    numeric = bool(check.get("numeric", operator in {"lt", "le", "gt", "ge", "close"}))
    if numeric:
        left = pd.to_numeric(frame[left_name], errors="coerce").replace([np.inf, -np.inf], np.nan)
    else:
        left = frame[left_name]
    if "column" in right_spec:
        right_name = str(right_spec["column"])
        if right_name not in frame.columns:
            raise DataContractError(f"relation check {index} references missing right column {right_name!r}")
        right = pd.to_numeric(frame[right_name], errors="coerce").replace([np.inf, -np.inf], np.nan) if numeric else frame[right_name]
    else:
        right = float(right_spec["value"]) if numeric else right_spec["value"]
    valid = left.notna() & (right.notna() if isinstance(right, pd.Series) else True)
    if operator == "eq":
        passed_rows = left == right
    elif operator == "ne":
        passed_rows = left != right
    elif operator == "lt":
        passed_rows = left < right
    elif operator == "le":
        passed_rows = left <= right
    elif operator == "gt":
        passed_rows = left > right
    elif operator == "ge":
        passed_rows = left >= right
    elif operator == "close":
        rtol, atol = float(check.get("rtol", 1e-9)), float(check.get("atol", 1e-12))
        passed_rows = pd.Series(np.isclose(left.astype(float), right.astype(float) if isinstance(right, pd.Series) else float(right), rtol=rtol, atol=atol), index=frame.index)
    else:
        raise DataContractError(f"relation check {index} has unsupported operator {operator!r}")
    require_complete = bool(check.get("require_complete", True))
    failures = valid & ~passed_rows.fillna(False)
    if require_complete:
        failures = failures | ~valid
    allowance = int(check.get("max_failures", 0))
    return _result(
        str(check.get("name", f"check:{index}:relation")),
        int(failures.sum()) <= allowance,
        required=bool(check.get("required", True)),
        failures=int(failures.sum()),
        max_failures=allowance,
        example_rows=_examples(failures),
        valid_rows=int(valid.sum()),
        operator=operator,
    )


def unique_key_check(frame: pd.DataFrame, check: dict[str, Any], index: int) -> dict[str, Any]:
    columns = [str(value) for value in check.get("columns", [])]
    if not columns:
        raise DataContractError(f"unique_key check {index} requires columns")
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataContractError(f"unique_key check {index} references missing columns: {missing}")
    null_policy = str(check.get("null_policy", "fail")).lower()
    if null_policy not in {"fail", "ignore"}:
        raise DataContractError("unique_key null_policy must be fail or ignore")
    null_mask = frame[columns].isna().any(axis=1)
    duplicate_mask = frame.duplicated(columns, keep=False)
    failures = duplicate_mask | null_mask if null_policy == "fail" else duplicate_mask & ~null_mask
    allowance = int(check.get("max_failures", 0))
    return _result(
        str(check.get("name", f"check:{index}:unique_key")),
        int(failures.sum()) <= allowance,
        required=bool(check.get("required", True)),
        columns=columns,
        null_policy=null_policy,
        null_key_rows=int(null_mask.sum()),
        duplicate_key_rows=int(duplicate_mask.sum()),
        failures=int(failures.sum()),
        max_failures=allowance,
        example_rows=_examples(failures),
    )


def linear_identity_check(frame: pd.DataFrame, check: dict[str, Any], index: int) -> dict[str, Any]:
    target = str(check.get("target", ""))
    terms = check.get("terms")
    if target not in frame.columns or not isinstance(terms, list) or not terms:
        raise DataContractError(f"linear_identity check {index} requires existing target and non-empty terms")
    term_columns = [str(term.get("column", "")) for term in terms]
    missing = [name for name in term_columns if name not in frame.columns]
    if missing:
        raise DataContractError(f"linear_identity check {index} references missing columns: {missing}")
    mode = str(check.get("numeric_mode", "float")).lower()
    failures = pd.Series(False, index=frame.index)
    valid_count = 0
    maximum_error: Any = Decimal(0) if mode == "decimal" else 0.0
    rtol, atol = float(check.get("rtol", 1e-9)), float(check.get("atol", 1e-12))
    for row_index, row in frame[[target, *term_columns]].iterrows():
        if mode == "decimal":
            actual = decimal_value(row[target])
            parsed_terms = [(decimal_value(row[column]), decimal_value(term.get("coefficient", 1))) for column, term in zip(term_columns, terms)]
            intercept = decimal_value(check.get("intercept", 0))
            if actual is None or intercept is None or any(value is None or coefficient is None for value, coefficient in parsed_terms):
                failures.loc[row_index] = bool(check.get("require_complete", True))
                continue
            expected = intercept + sum((value * coefficient for value, coefficient in parsed_terms if value is not None and coefficient is not None), Decimal(0))
            error = abs(actual - expected)
            tolerance = Decimal(str(atol)) + Decimal(str(rtol)) * abs(expected)
        else:
            actual = pd.to_numeric(pd.Series([row[target]]), errors="coerce").iloc[0]
            values = [pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0] for column in term_columns]
            if pd.isna(actual) or not math.isfinite(float(actual)) or any(pd.isna(value) or not math.isfinite(float(value)) for value in values):
                failures.loc[row_index] = bool(check.get("require_complete", True))
                continue
            expected = float(check.get("intercept", 0)) + sum(float(term.get("coefficient", 1)) * float(value) for term, value in zip(terms, values))
            error = abs(float(actual) - expected)
            tolerance = atol + rtol * abs(expected)
        valid_count += 1
        maximum_error = max(maximum_error, error)
        if error > tolerance:
            failures.loc[row_index] = True
    allowance = int(check.get("max_failures", 0))
    return _result(
        str(check.get("name", f"check:{index}:linear_identity")),
        int(failures.sum()) <= allowance,
        required=bool(check.get("required", True)),
        target=target,
        terms=terms,
        valid_rows=valid_count,
        failures=int(failures.sum()),
        max_failures=allowance,
        maximum_absolute_error=maximum_error,
        rtol=rtol,
        atol=atol,
        example_rows=_examples(failures),
    )


def run_contract(contract: dict[str, Any], *, input_override: str | None = None, contract_base: Path | None = None) -> dict[str, Any]:
    source = input_override or contract.get("input")
    if not source:
        raise DataContractError("contract requires input, or pass --input")
    source_path = Path(str(source)).expanduser()
    if not source_path.is_absolute() and contract_base is not None:
        source_path = contract_base / source_path
    frame, provenance = load_table(
        source_path,
        sheet=contract.get("sheet"),
        delimiter=contract.get("delimiter"),
        all_strings=bool(contract.get("all_strings", False)),
    )
    results: list[dict[str, Any]] = []
    columns = contract.get("columns", {})
    if not isinstance(columns, dict):
        raise DataContractError("columns must be an object keyed by column name")
    for name, rules in columns.items():
        if not isinstance(rules, dict):
            raise DataContractError(f"column rule for {name} must be an object")
        results.extend(validate_column(frame, str(name), rules))

    checks = contract.get("checks", [])
    if not isinstance(checks, list):
        raise DataContractError("checks must be a list")
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise DataContractError(f"check {index} must be an object")
        kind = str(check.get("kind", ""))
        if kind in {"row_count", "sum", "mean", "count", "nunique"}:
            results.append(scalar_check(frame, check, index))
        elif kind == "relation":
            results.append(relation_check(frame, check, index))
        elif kind == "unique_key":
            results.append(unique_key_check(frame, check, index))
        elif kind == "linear_identity":
            results.append(linear_identity_check(frame, check, index))
        else:
            raise DataContractError(f"check {index} has unsupported kind {kind!r}")

    if not results:
        raise DataContractError("contract must define at least one column rule or check")

    required_failures = [result for result in results if result["required"] and not result["passed"]]
    optional_failures = [result for result in results if not result["required"] and not result["passed"]]
    canonical = json.dumps(json_safe(contract), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "status": "QUARANTINE" if required_failures else "VERIFIED",
        "provenance": provenance,
        "contract_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "summary": {
            "checks": len(results),
            "passed": sum(result["passed"] for result in results),
            "required_failures": len(required_failures),
            "optional_failures": len(optional_failures),
        },
        "results": results,
        "environment": environment_record(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, help="JSON data contract")
    parser.add_argument("--input", help="Override contract input path")
    parser.add_argument("--output", help="Write JSON here instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        contract_path = Path(args.contract).expanduser().resolve()
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        if not isinstance(contract, dict):
            raise DataContractError("contract JSON root must be an object")
        report = run_contract(contract, input_override=args.input, contract_base=contract_path.parent)
        write_json(report, args.output)
        return 0 if report["status"] == "VERIFIED" else 2
    except (DataContractError, json.JSONDecodeError, OSError) as exc:
        write_json({"status": "QUARANTINE", "error": str(exc)}, args.output)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
