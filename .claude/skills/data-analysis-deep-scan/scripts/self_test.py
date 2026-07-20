#!/usr/bin/env python3
"""Synthetic end-to-end checks for the Data Analysis Deep Scan tools."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

from analyze_data import run_job
from data_core import DataContractError, json_safe, load_table
from join_data import run_join
from profile_data import profile_frame
from verify_data import run_contract


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fixture() -> pd.DataFrame:
    x = list(range(1, 13))
    noise = [0.2, -0.1, 0.3, -0.2, 0.1, -0.15, 0.25, -0.05, 0.18, -0.12, 0.08, -0.04]
    base = [f"{value / 10:.2f}" for value in range(1, 13)]
    fee = ["0.05"] * 12
    total = [f"{value / 10 + 0.05:.2f}" for value in range(1, 13)]
    return pd.DataFrame(
        {
            "id": x,
            "group": ["A"] * 6 + ["B"] * 6,
            "category": ["yes", "no", "yes", "no", "yes", "no"] * 2,
            "x": x,
            "y": [2 + 3 * value + error for value, error in zip(x, noise)],
            "value": [10, 12, 11, 15, 14, 13, 20, 22, 19, 24, 23, 21],
            "before": [5, 6, 5, 7, 8, 7, 9, 10, 9, 11, 12, 11],
            "after": [6, 7, 7, 8, 9, 9, 10, 12, 10, 12, 14, 12],
            "base": base,
            "fee": fee,
            "total": total,
            "date": pd.date_range("2026-01-01", periods=12, freq="D", tz="UTC").astype(str),
        }
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="data-analysis-deep-scan-") as temporary:
        root = Path(temporary)
        data_path = root / "fixture.csv"
        fixture().to_csv(data_path, index=False)

        frame, provenance = load_table(data_path)
        profile = profile_frame(frame, provenance, redact_values=True)
        require(profile["status"] == "PROFILED", "profile status")
        require(profile["dataset"]["rows"] == 12, "profile row count")
        require(any(column["name"] == "value" and column["numeric"]["max"] == 24 for column in profile["columns"]), "numeric profile")

        left_path = root / "left.csv"
        right_path = root / "right.csv"
        fixture()[["id", "group"]].to_csv(left_path, index=False)
        fixture()[["id", "value"]].to_csv(right_path, index=False)
        join_report = run_join(
            {
                "left": str(left_path),
                "right": str(right_path),
                "left_on": "id",
                "right_on": "id",
                "validate": "one_to_one",
                "how": "inner",
                "output": str(root / "joined.csv"),
            }
        )
        require(join_report["join"]["matched_rows"] == 12, "safe join matched rows")
        require(Path(join_report["output"]["path"]).exists(), "safe join output")
        duplicate_right = fixture()[["id", "value"]]
        duplicate_right.loc[11, "id"] = 1
        duplicate_right_path = root / "duplicate_right.csv"
        duplicate_right.to_csv(duplicate_right_path, index=False)
        try:
            run_join(
                {
                    "left": str(left_path),
                    "right": str(duplicate_right_path),
                    "left_on": "id",
                    "right_on": "id",
                    "validate": "one_to_one",
                    "audit_only": True,
                }
            )
            raise AssertionError("cardinality violation was not quarantined")
        except DataContractError:
            pass

        float_job = {
            "input": str(data_path),
            "seed": 20260720,
            "confidence": 0.95,
            "multiple_testing": {"method": "holm", "alpha": 0.05},
            "operations": [
                {"id": "group_totals", "type": "aggregate", "group_by": ["group"], "metrics": [{"column": "value", "agg": "sum", "name": "value_sum"}, {"agg": "size", "name": "rows"}]},
                {"id": "xy", "type": "correlation", "x": "x", "y": "y", "method": "pearson"},
                {"id": "groups", "type": "two_sample", "value": "value", "group": "group", "group_a": "A", "group_b": "B", "test": "welch_t", "bootstrap_repetitions": 300},
                {"id": "paired", "type": "paired_sample", "left": "after", "right": "before", "test": "paired_t", "bootstrap_repetitions": 300},
                {"id": "table", "type": "contingency", "row": "group", "column": "category"},
                {"id": "ols", "type": "regression", "y": "y", "x": ["x"], "covariance": "hc3"},
                {"id": "mean_ci", "type": "bootstrap", "column": "value", "statistic": "mean", "repetitions": 300},
                {"id": "changes", "type": "time_change", "time": "date", "value": "value", "group_by": ["group"], "method": "pct_change"},
            ],
        }
        analysis = run_job(float_job)
        require(analysis["status"] == "VERIFIED", "analysis status")
        aggregate = analysis["results"][0]
        require(aggregate["verification"][0]["passed"], "aggregate reconciliation")
        regression = next(result for result in analysis["results"] if result["type"] == "regression")
        slope = next(item for item in regression["coefficients"] if item["term"] == "x")
        require(abs(slope["estimate"] - 3) < 0.05, "regression slope")
        require(analysis["multiple_testing"]["tests_adjusted"] >= 4, "multiple testing adjustment")

        decimal_job = {
            "input": str(data_path),
            "operations": [
                {"type": "aggregate", "numeric_mode": "decimal", "group_by": ["group"], "metrics": [{"column": "total", "agg": "sum", "name": "total_sum"}, {"column": "total", "agg": "mean", "name": "total_mean"}]}
            ],
        }
        decimal_analysis = run_job(decimal_job)
        require(decimal_analysis["source_loaded_as_strings"], "per-operation decimal source preservation")
        require(str(decimal_analysis["results"][0]["rows"][0]["total_sum"]) == "2.40", "exact decimal aggregation")

        contract = {
            "input": str(data_path),
            "all_strings": True,
            "columns": {
                "id": {"required": True, "nullable": False, "unique": True, "type": "integer", "min": 1},
                "group": {"nullable": False, "allowed_values": ["A", "B"]},
                "total": {"nullable": False, "type": "numeric", "min": 0},
            },
            "checks": [
                {"kind": "row_count", "operator": "eq", "expected": 12},
                {"kind": "unique_key", "columns": ["id"]},
                {"kind": "sum", "column": "total", "numeric_mode": "decimal", "operator": "eq", "expected": "8.40"},
                {"kind": "relation", "left": "x", "operator": "lt", "right": {"column": "y"}, "numeric": True},
                {"kind": "linear_identity", "target": "total", "numeric_mode": "decimal", "terms": [{"column": "base"}, {"column": "fee"}], "rtol": 0, "atol": 0},
            ],
        }
        verification = run_contract(contract)
        require(verification["status"] == "VERIFIED", "valid contract")

        broken = fixture()
        broken.loc[11, "id"] = 1
        broken_path = root / "broken.csv"
        broken.to_csv(broken_path, index=False)
        broken_contract = dict(contract)
        broken_contract["input"] = str(broken_path)
        broken_verification = run_contract(broken_contract)
        require(broken_verification["status"] == "QUARANTINE", "duplicate ID quarantine")

        # Confirm every report is strict JSON: no NaN/Infinity serialization.
        json.dumps(json_safe({"profile": profile, "join": join_report, "analysis": analysis, "verification": verification}), allow_nan=False)

    print("SELF_TEST_OK: profile, safe join, analysis, exact decimals, inference, time order, and quarantine")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
