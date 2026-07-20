#!/usr/bin/env python3
"""Join two local tables with explicit cardinality checks and an audit manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from data_core import DataContractError, environment_record, load_table, require_columns, sha256_file, write_json


VALIDATE_ALIASES = {
    "1:1": "one_to_one",
    "1:m": "one_to_many",
    "m:1": "many_to_one",
    "m:m": "many_to_many",
    "one_to_one": "one_to_one",
    "one_to_many": "one_to_many",
    "many_to_one": "many_to_one",
    "many_to_many": "many_to_many",
}


def _as_columns(value: Any, name: str) -> list[str]:
    if isinstance(value, str):
        columns = [value]
    elif isinstance(value, list):
        columns = [str(item) for item in value]
    else:
        raise DataContractError(f"{name} must be a column name or list of column names")
    if not columns or any(not column for column in columns):
        raise DataContractError(f"{name} cannot be empty")
    return columns


def _key_profile(frame: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    null_mask = frame[columns].isna().any(axis=1)
    complete = frame.loc[~null_mask, columns]
    duplicate_mask = complete.duplicated(columns, keep=False)
    return {
        "columns": columns,
        "rows": int(len(frame)),
        "null_key_rows": int(null_mask.sum()),
        "complete_key_rows": int((~null_mask).sum()),
        "distinct_complete_keys": int(complete.drop_duplicates().shape[0]),
        "duplicate_complete_key_rows": int(duplicate_mask.sum()),
        "maximum_complete_key_multiplicity": int(complete.value_counts(dropna=False).max()) if len(complete) else 0,
    }


def _write_table(frame: pd.DataFrame, output: Path) -> None:
    suffix = output.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(output, index=False)
    elif suffix == ".tsv":
        frame.to_csv(output, index=False, sep="\t")
    elif suffix in {".xlsx", ".xls"}:
        frame.to_excel(output, index=False)
    elif suffix == ".parquet":
        frame.to_parquet(output, index=False)
    elif suffix in {".jsonl", ".ndjson"}:
        frame.to_json(output, orient="records", lines=True, force_ascii=False, date_format="iso")
    else:
        raise DataContractError("join output must end in .csv, .tsv, .xlsx, .xls, .parquet, .jsonl, or .ndjson")


def run_join(spec: dict[str, Any], *, base: Path | None = None, output_override: str | None = None) -> dict[str, Any]:
    if not spec.get("left") or not spec.get("right"):
        raise DataContractError("join spec requires left and right inputs")

    def resolved(value: Any) -> Path:
        path = Path(str(value)).expanduser()
        return (base / path).resolve() if base is not None and not path.is_absolute() else path.resolve()

    all_strings = bool(spec.get("all_strings", False))
    left, left_meta = load_table(
        resolved(spec["left"]),
        sheet=spec.get("left_sheet"),
        delimiter=spec.get("left_delimiter"),
        all_strings=all_strings,
    )
    right, right_meta = load_table(
        resolved(spec["right"]),
        sheet=spec.get("right_sheet"),
        delimiter=spec.get("right_delimiter"),
        all_strings=all_strings,
    )
    left_on = _as_columns(spec.get("left_on"), "left_on")
    right_on = _as_columns(spec.get("right_on"), "right_on")
    if len(left_on) != len(right_on):
        raise DataContractError("left_on and right_on must contain the same number of fields")
    require_columns(left, left_on, context="left join key")
    require_columns(right, right_on, context="right join key")

    left_key = _key_profile(left, left_on)
    right_key = _key_profile(right, right_on)
    if left_key["null_key_rows"] or right_key["null_key_rows"]:
        raise DataContractError(
            "Join keys contain nulls. Filter, repair, or explicitly model null-key rows before joining; pandas null-to-null matching is not accepted."
        )
    for left_name, right_name in zip(left_on, right_on):
        if str(left[left_name].dtype) != str(right[right_name].dtype):
            raise DataContractError(
                f"Join key types differ ({left_name}:{left[left_name].dtype} vs {right_name}:{right[right_name].dtype}); normalize explicitly or set all_strings=true"
            )

    raw_validate = str(spec.get("validate", ""))
    validate = VALIDATE_ALIASES.get(raw_validate)
    if validate is None:
        raise DataContractError(f"validate is required and must be one of {sorted(VALIDATE_ALIASES)}")
    if validate == "many_to_many" and not bool(spec.get("allow_many_to_many", False)):
        raise DataContractError("many_to_many requires allow_many_to_many=true and an explicit reconciliation plan")
    how = str(spec.get("how", "inner")).lower()
    if how not in {"inner", "left", "right", "outer"}:
        raise DataContractError("how must be inner, left, right, or outer")
    suffixes = spec.get("suffixes", ["_left", "_right"])
    if not isinstance(suffixes, list) or len(suffixes) != 2:
        raise DataContractError("suffixes must be a two-item list")
    indicator = "__merge_status"
    if indicator in left.columns or indicator in right.columns:
        raise DataContractError(f"reserved indicator column already exists: {indicator}")

    try:
        joined = left.merge(
            right,
            how=how,
            left_on=left_on,
            right_on=right_on,
            suffixes=(str(suffixes[0]), str(suffixes[1])),
            indicator=indicator,
            validate=validate,
            sort=False,
        )
    except pd.errors.MergeError as exc:
        raise DataContractError(f"Join cardinality validation failed: {exc}") from exc

    max_rows = int(spec.get("max_output_rows", 1_000_000))
    if len(joined) > max_rows:
        raise DataContractError(f"join produced {len(joined)} rows, above max_output_rows={max_rows}")
    merge_counts = joined[indicator].value_counts(dropna=False).to_dict()
    output_value = output_override or spec.get("output")
    audit_only = bool(spec.get("audit_only", False))
    output_record = None
    if not audit_only:
        if not output_value:
            raise DataContractError("join spec requires output unless audit_only=true")
        output = resolved(output_value)
        if output.exists() and not bool(spec.get("overwrite", False)):
            raise DataContractError(f"output already exists; set overwrite=true to replace it: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        _write_table(joined, output)
        output_record = {"path": str(output), "sha256": sha256_file(output), "bytes": output.stat().st_size}

    return {
        "status": "VERIFIED",
        "left": left_meta,
        "right": right_meta,
        "join": {
            "how": how,
            "validate": validate,
            "left_key": left_key,
            "right_key": right_key,
            "output_rows": int(len(joined)),
            "output_columns": int(joined.shape[1]),
            "matched_rows": int(merge_counts.get("both", 0)),
            "left_only_rows": int(merge_counts.get("left_only", 0)),
            "right_only_rows": int(merge_counts.get("right_only", 0)),
            "row_expansion_vs_left": int(len(joined) - len(left)),
            "row_expansion_vs_right": int(len(joined) - len(right)),
        },
        "audit_only": audit_only,
        "output": output_record,
        "environment": environment_record(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="JSON join specification")
    parser.add_argument("--output", help="Override the joined-table output path")
    parser.add_argument("--manifest", help="Write audit JSON here instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        spec_path = Path(args.spec).expanduser().resolve()
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            raise DataContractError("join spec JSON root must be an object")
        report = run_join(spec, base=spec_path.parent, output_override=args.output)
        write_json(report, args.manifest)
        return 0
    except (DataContractError, json.JSONDecodeError, OSError) as exc:
        write_json({"status": "QUARANTINE", "error": str(exc)}, args.manifest)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
