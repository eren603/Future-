#!/usr/bin/env python3
"""Profile a local table without changing it and emit an auditable JSON report."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from typing import Any

import numpy as np
import pandas as pd

from data_core import DataContractError, environment_record, json_safe, load_table, write_json


DATE_NAME = re.compile(r"(?:^|_)(date|datetime|timestamp|time|tarih|zaman|created_at|updated_at|event_at)(?:$|_)", re.IGNORECASE)
ID_NAME = re.compile(r"(?:^|_)(id|uuid|guid|key|code|kod|number|no)(?:$|_)", re.IGNORECASE)


def _round(value: Any, digits: int = 12) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


def _display_value(value: Any, redact: bool) -> Any:
    safe = json_safe(value)
    if not redact:
        return safe
    token = "<NULL>" if safe is None else str(safe)
    return f"sha256:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:12]}"


def _numeric_profile(values: pd.Series) -> dict[str, Any]:
    finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if finite.empty:
        return {"finite_count": 0}
    q1, median, q3 = finite.quantile([0.25, 0.5, 0.75]).tolist()
    iqr = q3 - q1
    if iqr > 0:
        iqr_outliers = int(((finite < q1 - 1.5 * iqr) | (finite > q3 + 1.5 * iqr)).sum())
    else:
        iqr_outliers = 0
    abs_deviation = (finite - median).abs()
    mad = float(abs_deviation.median())
    if mad > 0:
        robust_z = 0.6744897501960817 * abs_deviation / mad
        mad_outliers = int((robust_z > 3.5).sum())
    else:
        mad_outliers = 0
    return {
        "finite_count": int(len(finite)),
        "min": _round(finite.min()),
        "q1": _round(q1),
        "median": _round(median),
        "q3": _round(q3),
        "max": _round(finite.max()),
        "mean": _round(finite.mean()),
        "std_ddof_1": _round(finite.std(ddof=1)) if len(finite) > 1 else None,
        "iqr": _round(iqr),
        "zero_count": int((finite == 0).sum()),
        "negative_count": int((finite < 0).sum()),
        "iqr_outlier_count": iqr_outliers,
        "mad_outlier_count": mad_outliers,
    }


def _datetime_profile(series: pd.Series) -> tuple[dict[str, Any] | None, pd.Series | None]:
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        parsed = pd.to_datetime(series, errors="coerce", utc=True)
    elif DATE_NAME.search(str(series.name)):
        parsed = pd.to_datetime(series, errors="coerce", utc=True, format="mixed")
    else:
        return None, None
    non_null = int(series.notna().sum())
    parsed_count = int(parsed.notna().sum())
    profile = {
        "parse_count": parsed_count,
        "parse_rate_of_non_null": _round(parsed_count / non_null) if non_null else None,
        "min_utc": parsed.min().isoformat() if parsed_count else None,
        "max_utc": parsed.max().isoformat() if parsed_count else None,
        "duplicate_timestamp_count": int(parsed.dropna().duplicated().sum()),
        "monotonic_increasing": bool(parsed.dropna().is_monotonic_increasing),
        "monotonic_decreasing": bool(parsed.dropna().is_monotonic_decreasing),
    }
    return profile, parsed


def profile_frame(
    frame: pd.DataFrame,
    provenance: dict[str, Any],
    *,
    top_n: int = 5,
    redact_values: bool = False,
    correlation_threshold: float = 0.7,
) -> dict[str, Any]:
    rows = len(frame)
    duplicate_rows = int(frame.duplicated().sum()) if rows else 0
    columns: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    correlation_candidates: dict[str, pd.Series] = {}

    if rows == 0:
        warnings.append({"code": "EMPTY_DATASET", "severity": "error", "detail": "No data rows were loaded"})
    if duplicate_rows:
        warnings.append({"code": "DUPLICATE_ROWS", "severity": "warning", "count": duplicate_rows})

    for position, name in enumerate(frame.columns):
        series = frame[name]
        non_null = int(series.notna().sum())
        missing = rows - non_null
        unique = int(series.nunique(dropna=True))
        unique_rate = unique / non_null if non_null else None
        probable_id = bool(non_null and unique_rate is not None and unique_rate >= 0.98 and ID_NAME.search(name))

        item: dict[str, Any] = {
            "name": name,
            "position": position,
            "dtype": str(series.dtype),
            "non_null_count": non_null,
            "missing_count": missing,
            "missing_rate": _round(missing / rows) if rows else None,
            "unique_non_null_count": unique,
            "unique_rate_of_non_null": _round(unique_rate) if unique_rate is not None else None,
            "probable_identifier": probable_id,
            "constant_non_null": bool(non_null > 0 and unique <= 1),
        }

        date_like = bool(pd.api.types.is_datetime64_any_dtype(series.dtype) or DATE_NAME.search(name))
        numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
        numeric_count = int(numeric.notna().sum())
        numeric_rate = numeric_count / non_null if non_null else 0.0
        item["numeric_parse_rate_of_non_null"] = _round(numeric_rate) if non_null else None
        if not date_like and (pd.api.types.is_numeric_dtype(series.dtype) or numeric_rate >= 0.95):
            item["numeric"] = _numeric_profile(numeric)
            if not probable_id and numeric_count >= 3:
                correlation_candidates[name] = numeric

        datetime_info, parsed_datetime = _datetime_profile(series)
        if datetime_info is not None:
            item["datetime"] = datetime_info
            if non_null and (datetime_info["parse_rate_of_non_null"] or 0) < 0.95:
                warnings.append({"code": "DATETIME_PARSE_LOSS", "severity": "warning", "column": name, "detail": datetime_info})
            if parsed_datetime is not None and datetime_info["duplicate_timestamp_count"]:
                warnings.append({"code": "DUPLICATE_TIMESTAMPS", "severity": "warning", "column": name, "count": datetime_info["duplicate_timestamp_count"]})
            if parsed_datetime is not None and not datetime_info["monotonic_increasing"]:
                warnings.append({"code": "TIME_NOT_ASCENDING", "severity": "info", "column": name})

        try:
            counts = series.value_counts(dropna=False).head(max(0, top_n))
        except TypeError:
            counts = series.map(lambda value: json.dumps(json_safe(value), ensure_ascii=False, sort_keys=True)).value_counts(dropna=False).head(max(0, top_n))
        item["top_values"] = [
            {"value": _display_value(index, redact_values), "count": int(count)}
            for index, count in counts.items()
        ]
        columns.append(item)

        if non_null == 0:
            warnings.append({"code": "ALL_MISSING", "severity": "warning", "column": name})
        elif unique <= 1:
            warnings.append({"code": "CONSTANT_COLUMN", "severity": "info", "column": name})
        if rows and missing / rows >= 0.5:
            warnings.append({"code": "HIGH_MISSINGNESS", "severity": "warning", "column": name, "rate": _round(missing / rows)})
        if probable_id and unique < non_null:
            warnings.append({"code": "PROBABLE_ID_NOT_UNIQUE", "severity": "warning", "column": name, "duplicates": non_null - unique})

    correlations: list[dict[str, Any]] = []
    candidate_names = list(correlation_candidates)[:40]
    if len(correlation_candidates) > 40:
        warnings.append({"code": "CORRELATION_PROFILE_CAPPED", "severity": "info", "columns_used": 40})
    for left_index, left in enumerate(candidate_names):
        for right in candidate_names[left_index + 1 :]:
            pair = pd.concat([correlation_candidates[left], correlation_candidates[right]], axis=1).dropna()
            if len(pair) < 3 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
                continue
            value = float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method="pearson"))
            if math.isfinite(value) and abs(value) >= correlation_threshold:
                correlations.append({"left": left, "right": right, "pearson_r": _round(value), "pairwise_n": int(len(pair))})
    correlations.sort(key=lambda item: (-abs(item["pearson_r"]), item["left"], item["right"]))

    return {
        "status": "PROFILED" if rows else "QUARANTINE",
        "provenance": provenance,
        "dataset": {
            "rows": int(rows),
            "columns": int(frame.shape[1]),
            "duplicate_row_count": duplicate_rows,
            "memory_bytes_deep": int(frame.memory_usage(index=True, deep=True).sum()),
        },
        "columns": columns,
        "strong_pearson_correlations": correlations,
        "warnings": warnings,
        "settings": {
            "top_n": top_n,
            "redact_values": redact_values,
            "correlation_threshold": correlation_threshold,
            "outlier_rules": {"iqr": "outside Q1-1.5*IQR or Q3+1.5*IQR", "mad": "modified z > 3.5"},
        },
        "environment": environment_record(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV/TSV/JSON/JSONL/XLSX/XLS/Parquet path")
    parser.add_argument("--sheet", help="Excel sheet name or zero-based index")
    parser.add_argument("--delimiter", help="Explicit delimiter for text input")
    parser.add_argument("--top-n", type=int, default=5, help="Most common values per column")
    parser.add_argument("--redact-values", action="store_true", help="Hash category labels in the profile")
    parser.add_argument("--correlation-threshold", type=float, default=0.7)
    parser.add_argument("--output", help="Write JSON to this path instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.top_n < 0:
            raise DataContractError("--top-n must be non-negative")
        if not 0 <= args.correlation_threshold <= 1:
            raise DataContractError("--correlation-threshold must be between 0 and 1")
        frame, provenance = load_table(args.input, sheet=args.sheet, delimiter=args.delimiter)
        report = profile_frame(
            frame,
            provenance,
            top_n=args.top_n,
            redact_values=args.redact_values,
            correlation_threshold=args.correlation_threshold,
        )
        write_json(report, args.output)
        return 0 if report["status"] == "PROFILED" else 2
    except DataContractError as exc:
        write_json({"status": "QUARANTINE", "error": str(exc)}, args.output)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
