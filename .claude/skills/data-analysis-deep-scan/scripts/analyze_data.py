#!/usr/bin/env python3
"""Run JSON-specified, auditable calculations on a local table."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy import stats

from data_core import (
    DataContractError,
    decimal_value,
    environment_record,
    json_safe,
    load_table,
    numeric_series,
    require_columns,
    write_json,
)


def _round(value: Any, digits: int = 12) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


def _confidence(op: dict[str, Any], job: dict[str, Any]) -> float:
    value = float(op.get("confidence", job.get("confidence", 0.95)))
    if not 0 < value < 1:
        raise DataContractError("confidence must be strictly between 0 and 1")
    return value


def _seed(op: dict[str, Any], job: dict[str, Any]) -> int:
    return int(op.get("seed", job.get("seed", 1729)))


def _iter_groups(frame: pd.DataFrame, group_by: list[str]) -> Iterable[tuple[tuple[Any, ...], pd.DataFrame]]:
    if not group_by:
        yield (), frame
        return
    grouper: str | list[str] = group_by[0] if len(group_by) == 1 else group_by
    for key, subset in frame.groupby(grouper, dropna=False, sort=True, observed=False):
        yield (key,) if len(group_by) == 1 else tuple(key), subset


def _decimal_values(series: pd.Series) -> list[Decimal]:
    values: list[Decimal] = []
    for raw in series.tolist():
        parsed = decimal_value(raw)
        if parsed is not None:
            values.append(parsed)
    return values


def _decimal_metric(subset: pd.DataFrame, metric: dict[str, Any]) -> Any:
    agg = str(metric.get("agg", "")).lower()
    column = metric.get("column")
    if agg == "size":
        return int(len(subset))
    if not column:
        raise DataContractError(f"aggregate metric {agg!r} requires column")
    require_columns(subset, [column], context="aggregate")
    if agg == "count":
        return int(subset[column].notna().sum())
    if agg == "nunique":
        return int(subset[column].nunique(dropna=True))
    values = _decimal_values(subset[column])
    if not values:
        return None
    if agg == "sum":
        return sum(values, Decimal(0))
    if agg == "min":
        return min(values)
    if agg == "max":
        return max(values)
    if agg == "mean":
        return sum(values, Decimal(0)) / Decimal(len(values))
    if agg == "median":
        ordered = sorted(values)
        middle = len(ordered) // 2
        return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    if agg == "std":
        if len(values) < 2:
            return None
        mean = sum(values, Decimal(0)) / Decimal(len(values))
        with localcontext() as context:
            context.prec = max(context.prec, 34)
            variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)
            return variance.sqrt()
    if agg == "weighted_mean":
        weight = metric.get("weight")
        if not weight:
            raise DataContractError("weighted_mean requires weight")
        require_columns(subset, [weight], context="weighted_mean")
        pairs: list[tuple[Decimal, Decimal]] = []
        for raw_value, raw_weight in zip(subset[column].tolist(), subset[weight].tolist()):
            value = decimal_value(raw_value)
            weight_value = decimal_value(raw_weight)
            if value is not None and weight_value is not None:
                pairs.append((value, weight_value))
        if not pairs:
            return None
        if not metric.get("allow_negative_weights", False) and any(weight_value < 0 for _, weight_value in pairs):
            raise DataContractError("Negative weights require allow_negative_weights=true")
        total_weight = sum((weight_value for _, weight_value in pairs), Decimal(0))
        if total_weight == 0:
            raise DataContractError("weighted_mean has zero total weight")
        return sum((value * weight_value for value, weight_value in pairs), Decimal(0)) / total_weight
    raise DataContractError(f"Unsupported decimal aggregation: {agg}")


def _float_metric(subset: pd.DataFrame, metric: dict[str, Any]) -> Any:
    agg = str(metric.get("agg", "")).lower()
    column = metric.get("column")
    if agg == "size":
        return int(len(subset))
    if not column:
        raise DataContractError(f"aggregate metric {agg!r} requires column")
    require_columns(subset, [column], context="aggregate")
    if agg == "count":
        return int(subset[column].notna().sum())
    if agg == "nunique":
        return int(subset[column].nunique(dropna=True))
    values = numeric_series(subset, column).dropna()
    if values.empty:
        return None
    if agg == "sum":
        return float(values.sum())
    if agg == "min":
        return float(values.min())
    if agg == "max":
        return float(values.max())
    if agg == "mean":
        return float(values.mean())
    if agg == "median":
        return float(values.median())
    if agg == "std":
        return float(values.std(ddof=1)) if len(values) > 1 else None
    if agg == "weighted_mean":
        weight = metric.get("weight")
        if not weight:
            raise DataContractError("weighted_mean requires weight")
        require_columns(subset, [weight], context="weighted_mean")
        pairs = pd.concat([numeric_series(subset, column), numeric_series(subset, weight)], axis=1).dropna()
        pairs.columns = ["value", "weight"]
        if pairs.empty:
            return None
        if not metric.get("allow_negative_weights", False) and (pairs["weight"] < 0).any():
            raise DataContractError("Negative weights require allow_negative_weights=true")
        total_weight = float(pairs["weight"].sum())
        if not math.isfinite(total_weight) or total_weight == 0:
            raise DataContractError("weighted_mean has zero or non-finite total weight")
        return float(np.average(pairs["value"], weights=pairs["weight"]))
    raise DataContractError(f"Unsupported floating aggregation: {agg}")


def _metric_audit(subset: pd.DataFrame, metric: dict[str, Any], numeric_mode: str) -> dict[str, Any]:
    agg = str(metric.get("agg", "")).lower()
    column = metric.get("column")
    if agg == "size":
        return {"input_rows": int(len(subset)), "usable_rows": int(len(subset)), "excluded_rows": 0}
    if not column:
        return {"input_rows": int(len(subset)), "usable_rows": 0, "excluded_rows": int(len(subset))}
    if agg in {"count", "nunique"}:
        usable = int(subset[column].notna().sum())
    elif agg == "weighted_mean":
        weight = str(metric.get("weight", ""))
        require_columns(subset, [weight], context="weighted_mean audit")
        if numeric_mode == "decimal":
            usable = 0
            for raw_value, raw_weight in zip(subset[column].tolist(), subset[weight].tolist()):
                if decimal_value(raw_value) is not None and decimal_value(raw_weight) is not None:
                    usable += 1
        else:
            usable = int(pd.concat([numeric_series(subset, column), numeric_series(subset, weight)], axis=1).dropna().shape[0])
    elif numeric_mode == "decimal":
        usable = len(_decimal_values(subset[column]))
    else:
        usable = int(numeric_series(subset, column).notna().sum())
    return {"input_rows": int(len(subset)), "usable_rows": usable, "excluded_rows": int(len(subset) - usable)}


def aggregate(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    group_by = [str(value) for value in op.get("group_by", [])]
    metrics = op.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise DataContractError("aggregate requires a non-empty metrics list")
    require_columns(frame, group_by, context="aggregate group_by")
    numeric_mode = str(op.get("numeric_mode", job.get("numeric_mode", "float"))).lower()
    if numeric_mode not in {"float", "decimal"}:
        raise DataContractError("numeric_mode must be float or decimal")

    names: list[str] = []
    for metric in metrics:
        if not isinstance(metric, dict):
            raise DataContractError("each aggregate metric must be an object")
        name = str(metric.get("name") or f"{metric.get('column', 'rows')}_{metric.get('agg', '')}")
        if name in names or name in group_by:
            raise DataContractError(f"duplicate or ambiguous output name: {name}")
        names.append(name)

    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for key, subset in _iter_groups(frame, group_by):
        row = {column: key[index] for index, column in enumerate(group_by)}
        audit_row = {column: key[index] for index, column in enumerate(group_by)}
        audit_row["metrics"] = {}
        for name, metric in zip(names, metrics):
            row[name] = _decimal_metric(subset, metric) if numeric_mode == "decimal" else _float_metric(subset, metric)
            audit_row["metrics"][name] = _metric_audit(subset, metric, numeric_mode)
        rows.append(row)
        audit_rows.append(audit_row)
    max_rows = int(op.get("max_rows", job.get("max_output_rows", 10000)))
    if len(rows) > max_rows:
        raise DataContractError(f"aggregate would emit {len(rows)} rows, above max_output_rows={max_rows}")

    verification: list[dict[str, Any]] = []
    if group_by:
        for name, metric in zip(names, metrics):
            if str(metric.get("agg", "")).lower() != "sum":
                continue
            source = _decimal_metric(frame, metric) if numeric_mode == "decimal" else _float_metric(frame, metric)
            outputs = [row[name] for row in rows if row[name] is not None]
            if source is None and not outputs:
                grouped = None
                passed = True
            else:
                grouped = sum(outputs, Decimal(0)) if numeric_mode == "decimal" else float(sum(outputs))
                passed = grouped == source if numeric_mode == "decimal" else bool(np.isclose(grouped, source, rtol=1e-10, atol=1e-12))
            verification.append({"metric": name, "grouped_total": grouped, "source_total": source, "passed": passed})
            if not passed:
                raise DataContractError(f"aggregate reconciliation failed for {name}")
    return {
        "type": "aggregate",
        "numeric_mode": numeric_mode,
        "group_by": group_by,
        "rows": rows,
        "audit_rows": audit_rows,
        "row_count": len(rows),
        "verification": verification,
    }


def correlation(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    x, y = str(op.get("x", "")), str(op.get("y", ""))
    require_columns(frame, [x, y], context="correlation")
    pair = pd.concat([numeric_series(frame, x), numeric_series(frame, y)], axis=1).dropna()
    pair.columns = [x, y]
    if len(pair) < 3 or pair[x].nunique() < 2 or pair[y].nunique() < 2:
        raise DataContractError("correlation needs at least 3 complete pairs and variation in both fields")
    method = str(op.get("method", "pearson")).lower()
    alternative = str(op.get("alternative", "two-sided"))
    if method == "pearson":
        result = stats.pearsonr(pair[x], pair[y], alternative=alternative)
    elif method == "spearman":
        result = stats.spearmanr(pair[x], pair[y], alternative=alternative)
    elif method == "kendall":
        result = stats.kendalltau(pair[x], pair[y], alternative=alternative)
    else:
        raise DataContractError("correlation method must be pearson, spearman, or kendall")
    coefficient = float(result.statistic)
    if not math.isfinite(coefficient):
        raise DataContractError("correlation returned a non-finite coefficient")
    confidence_interval = None
    confidence = _confidence(op, job)
    if method == "pearson" and len(pair) > 3 and abs(coefficient) < 1:
        z = np.arctanh(coefficient)
        critical = stats.norm.ppf(0.5 + confidence / 2)
        half = critical / math.sqrt(len(pair) - 3)
        confidence_interval = {"low": _round(np.tanh(z - half)), "high": _round(np.tanh(z + half)), "level": confidence, "method": "Fisher z"}
    return {
        "type": "correlation",
        "x": x,
        "y": y,
        "method": method,
        "alternative": alternative,
        "pairwise_n": int(len(pair)),
        "dropped_rows": int(len(frame) - len(pair)),
        "coefficient": _round(coefficient),
        "p_value": _round(result.pvalue),
        "confidence_interval": confidence_interval,
        "claim_limit": "association_not_causation",
    }


def _bootstrap_difference(
    left: np.ndarray,
    right: np.ndarray,
    statistic: str,
    repetitions: int,
    confidence: float,
    seed: int,
) -> dict[str, Any]:
    if not 200 <= repetitions <= 100000:
        raise DataContractError("bootstrap repetitions must be between 200 and 100000")
    function = np.mean if statistic == "mean" else np.median
    rng = np.random.default_rng(seed)
    estimates = np.empty(repetitions, dtype=float)
    for index in range(repetitions):
        estimates[index] = function(rng.choice(left, len(left), replace=True)) - function(rng.choice(right, len(right), replace=True))
    alpha = 1 - confidence
    return {
        "statistic": f"{statistic}_difference_a_minus_b",
        "low": _round(np.quantile(estimates, alpha / 2)),
        "high": _round(np.quantile(estimates, 1 - alpha / 2)),
        "standard_error": _round(estimates.std(ddof=1)),
        "confidence": confidence,
        "method": "percentile bootstrap",
        "repetitions": repetitions,
        "seed": seed,
    }


def _group_mask(series: pd.Series, label: Any) -> pd.Series:
    direct = series == label
    if bool(direct.fillna(False).any()):
        return direct.fillna(False)
    if label is None:
        return series.isna()
    return (series.astype("string") == str(label)).fillna(False)


def two_sample(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    value, group = str(op.get("value", "")), str(op.get("group", ""))
    require_columns(frame, [value, group], context="two_sample")
    if "group_a" not in op or "group_b" not in op:
        raise DataContractError("two_sample requires group_a and group_b")
    group_a, group_b = op["group_a"], op["group_b"]
    if group_a == group_b:
        raise DataContractError("two_sample group_a and group_b must be different")
    left = numeric_series(frame.loc[_group_mask(frame[group], group_a)], value).dropna().to_numpy(dtype=float)
    right = numeric_series(frame.loc[_group_mask(frame[group], group_b)], value).dropna().to_numpy(dtype=float)
    if len(left) < 2 or len(right) < 2:
        raise DataContractError("two_sample requires at least 2 numeric observations in each selected group")
    test = str(op.get("test", "welch_t")).lower()
    alternative = str(op.get("alternative", "two-sided"))
    if test == "welch_t":
        result = stats.ttest_ind(left, right, equal_var=False, alternative=alternative)
    elif test == "student_t":
        result = stats.ttest_ind(left, right, equal_var=True, alternative=alternative)
    elif test == "mannwhitney":
        result = stats.mannwhitneyu(left, right, alternative=alternative, method="auto")
    else:
        raise DataContractError("two_sample test must be welch_t, student_t, or mannwhitney")

    mean_difference = float(left.mean() - right.mean())
    median_difference = float(np.median(left) - np.median(right))
    df = len(left) + len(right) - 2
    pooled_variance = (((len(left) - 1) * left.var(ddof=1)) + ((len(right) - 1) * right.var(ddof=1))) / df
    cohen_d = mean_difference / math.sqrt(pooled_variance) if pooled_variance > 0 else None
    correction = 1 - 3 / (4 * df - 1) if df > 1 else None
    hedges_g = cohen_d * correction if cohen_d is not None and correction is not None else None
    rank_biserial = None
    if test == "mannwhitney":
        rank_biserial = 2 * float(result.statistic) / (len(left) * len(right)) - 1
    bootstrap_statistic = str(op.get("bootstrap_statistic", "mean")).lower()
    if bootstrap_statistic not in {"mean", "median"}:
        raise DataContractError("bootstrap_statistic must be mean or median")
    interval = _bootstrap_difference(
        left,
        right,
        bootstrap_statistic,
        int(op.get("bootstrap_repetitions", 2000)),
        _confidence(op, job),
        _seed(op, job),
    )
    warnings: list[str] = []
    if min(len(left), len(right)) < 20:
        warnings.append("small_group_sample; inspect distribution and robustness")
    if test == "student_t":
        warnings.append("pooled_variance_assumption_requested")
    return {
        "type": "two_sample",
        "value": value,
        "group": group,
        "group_a": group_a,
        "group_b": group_b,
        "test": test,
        "alternative": alternative,
        "n_a": int(len(left)),
        "n_b": int(len(right)),
        "mean_a": _round(left.mean()),
        "mean_b": _round(right.mean()),
        "median_a": _round(np.median(left)),
        "median_b": _round(np.median(right)),
        "mean_difference_a_minus_b": _round(mean_difference),
        "median_difference_a_minus_b": _round(median_difference),
        "test_statistic": _round(result.statistic),
        "p_value": _round(result.pvalue),
        "cohen_d": _round(cohen_d),
        "hedges_g": _round(hedges_g),
        "rank_biserial_a_over_b": _round(rank_biserial),
        "bootstrap_interval": interval,
        "warnings": warnings,
        "claim_limit": "group_difference_not_causation",
    }


def paired_sample(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    left_name, right_name = str(op.get("left", "")), str(op.get("right", ""))
    require_columns(frame, [left_name, right_name], context="paired_sample")
    pair = pd.concat([numeric_series(frame, left_name), numeric_series(frame, right_name)], axis=1).dropna()
    pair.columns = [left_name, right_name]
    if len(pair) < 2:
        raise DataContractError("paired_sample requires at least 2 complete pairs")
    left = pair[left_name].to_numpy(dtype=float)
    right = pair[right_name].to_numpy(dtype=float)
    differences = left - right
    test = str(op.get("test", "paired_t")).lower()
    alternative = str(op.get("alternative", "two-sided"))
    if test == "paired_t":
        result = stats.ttest_rel(left, right, alternative=alternative)
    elif test == "wilcoxon":
        if np.allclose(differences, 0):
            raise DataContractError("wilcoxon is undefined when all paired differences are zero")
        result = stats.wilcoxon(left, right, alternative=alternative, zero_method=str(op.get("zero_method", "wilcox")), method="auto")
    else:
        raise DataContractError("paired_sample test must be paired_t or wilcoxon")
    repetitions = int(op.get("bootstrap_repetitions", 2000))
    if not 200 <= repetitions <= 100000:
        raise DataContractError("bootstrap repetitions must be between 200 and 100000")
    statistic = str(op.get("bootstrap_statistic", "mean")).lower()
    function = np.mean if statistic == "mean" else np.median if statistic == "median" else None
    if function is None:
        raise DataContractError("paired_sample bootstrap_statistic must be mean or median")
    seed = _seed(op, job)
    rng = np.random.default_rng(seed)
    boot = np.empty(repetitions, dtype=float)
    for index in range(repetitions):
        boot[index] = function(rng.choice(differences, len(differences), replace=True))
    confidence = _confidence(op, job)
    alpha = 1 - confidence
    difference_sd = float(differences.std(ddof=1)) if len(differences) > 1 else None
    cohen_dz = float(differences.mean() / difference_sd) if difference_sd and difference_sd > 0 else None
    return {
        "type": "paired_sample",
        "left": left_name,
        "right": right_name,
        "test": test,
        "alternative": alternative,
        "n_pairs": int(len(pair)),
        "dropped_rows": int(len(frame) - len(pair)),
        "mean_left": _round(left.mean()),
        "mean_right": _round(right.mean()),
        "mean_difference_left_minus_right": _round(differences.mean()),
        "median_difference_left_minus_right": _round(np.median(differences)),
        "cohen_dz": _round(cohen_dz),
        "test_statistic": _round(result.statistic),
        "p_value": _round(result.pvalue),
        "bootstrap_interval": {
            "statistic": f"{statistic}_paired_difference",
            "low": _round(np.quantile(boot, alpha / 2)),
            "high": _round(np.quantile(boot, 1 - alpha / 2)),
            "standard_error": _round(boot.std(ddof=1)),
            "confidence": confidence,
            "method": "paired percentile bootstrap",
            "repetitions": repetitions,
            "seed": seed,
        },
        "claim_limit": "paired_difference_not_causation",
    }


def contingency(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    row, column = str(op.get("row", "")), str(op.get("column", ""))
    require_columns(frame, [row, column], context="contingency")
    complete = frame[[row, column]].dropna()
    table = pd.crosstab(complete[row], complete[column], dropna=False)
    if table.shape[0] < 2 or table.shape[1] < 2:
        raise DataContractError("contingency requires at least a 2x2 observed table")
    correction = bool(op.get("yates_correction", True))
    statistic, p_value, dof, expected = stats.chi2_contingency(table.to_numpy(), correction=correction)
    n = int(table.to_numpy().sum())
    phi2 = statistic / n
    cramer_v = math.sqrt(phi2 / max(1, min(table.shape[0] - 1, table.shape[1] - 1)))
    low_expected = int((expected < 5).sum())
    return {
        "type": "contingency",
        "row": row,
        "column": column,
        "n": n,
        "observed": {str(index): {str(key): int(value) for key, value in values.items()} for index, values in table.to_dict(orient="index").items()},
        "chi_square": _round(statistic),
        "degrees_of_freedom": int(dof),
        "p_value": _round(p_value),
        "cramers_v": _round(cramer_v),
        "minimum_expected_count": _round(np.min(expected)),
        "expected_cells_below_5": low_expected,
        "warning": "chi_square_approximation_may_be_unreliable" if low_expected else None,
        "claim_limit": "association_not_causation",
    }


def _vif_values(matrix: np.ndarray, names: list[str], intercept: bool) -> list[dict[str, Any]]:
    start = 1 if intercept else 0
    outputs: list[dict[str, Any]] = []
    for target in range(start, matrix.shape[1]):
        y = matrix[:, target]
        others = np.delete(matrix, target, axis=1)
        if np.var(y) == 0:
            vif = None
        elif others.shape[1] == 0:
            vif = 1.0
        else:
            fitted = others @ np.linalg.lstsq(others, y, rcond=None)[0]
            r2 = 1 - np.sum((y - fitted) ** 2) / np.sum((y - y.mean()) ** 2)
            vif = math.inf if r2 >= 1 - 1e-12 else 1 / (1 - r2)
        outputs.append({"term": names[target], "vif": _round(vif)})
    return outputs


def regression(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    y_name = str(op.get("y", ""))
    x_names = [str(value) for value in op.get("x", [])]
    if not x_names:
        raise DataContractError("regression requires at least one x field")
    require_columns(frame, [y_name, *x_names], context="regression")
    numeric = pd.DataFrame({name: numeric_series(frame, name) for name in [y_name, *x_names]}).dropna()
    n = len(numeric)
    intercept = bool(op.get("intercept", True))
    x = numeric[x_names].to_numpy(dtype=float)
    names = ["intercept", *x_names] if intercept else list(x_names)
    design = np.column_stack([np.ones(n), x]) if intercept else x
    p = design.shape[1]
    if n <= p + 1:
        raise DataContractError(f"regression has {n} complete rows but needs more than {p + 1}")
    beta, _, rank, singular = np.linalg.lstsq(design, numeric[y_name].to_numpy(dtype=float), rcond=None)
    if rank < p:
        raise DataContractError(f"regression design is rank deficient ({rank} < {p})")
    y = numeric[y_name].to_numpy(dtype=float)
    fitted = design @ beta
    residual = y - fitted
    df_resid = n - rank
    rss = float(residual @ residual)
    mse = rss / df_resid
    xtx_inverse = np.linalg.inv(design.T @ design)
    leverage = np.sum((design @ xtx_inverse) * design, axis=1)
    covariance_kind = str(op.get("covariance", "hc3")).lower()
    if covariance_kind == "classical":
        covariance = mse * xtx_inverse
    elif covariance_kind == "hc3":
        denominator = np.maximum(1 - leverage, np.finfo(float).eps)
        scaled = (residual / denominator) ** 2
        meat = design.T @ (design * scaled[:, None])
        covariance = xtx_inverse @ meat @ xtx_inverse
    else:
        raise DataContractError("regression covariance must be classical or hc3")
    standard_error = np.sqrt(np.maximum(np.diag(covariance), 0))
    t_value = np.divide(beta, standard_error, out=np.full_like(beta, np.nan), where=standard_error > 0)
    p_value = 2 * stats.t.sf(np.abs(t_value), df_resid)
    confidence = _confidence(op, job)
    critical = stats.t.ppf(0.5 + confidence / 2, df_resid)
    coefficients = [
        {
            "term": name,
            "estimate": _round(beta[index]),
            "standard_error": _round(standard_error[index]),
            "t_value": _round(t_value[index]),
            "p_value": _round(p_value[index]),
            "ci_low": _round(beta[index] - critical * standard_error[index]),
            "ci_high": _round(beta[index] + critical * standard_error[index]),
        }
        for index, name in enumerate(names)
    ]
    tss = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1 - rss / tss if tss > 0 else None
    adjusted = 1 - (1 - r_squared) * (n - 1) / df_resid if r_squared is not None else None
    durbin_watson = float(np.sum(np.diff(residual) ** 2) / rss) if rss > 0 else None
    cooks = (residual**2 / (p * mse)) * (leverage / np.maximum((1 - leverage) ** 2, np.finfo(float).eps)) if mse > 0 else np.zeros(n)
    normality = None
    if n >= 8:
        normal_result = stats.normaltest(residual)
        normality = {"test": "D'Agostino-Pearson", "statistic": _round(normal_result.statistic), "p_value": _round(normal_result.pvalue)}
    # Breusch-Pagan LM test: auxiliary regression of squared residuals on X.
    auxiliary_beta = np.linalg.lstsq(design, residual**2, rcond=None)[0]
    auxiliary_fitted = design @ auxiliary_beta
    aux_tss = float(np.sum((residual**2 - np.mean(residual**2)) ** 2))
    aux_r2 = 1 - float(np.sum((residual**2 - auxiliary_fitted) ** 2)) / aux_tss if aux_tss > 0 else 0.0
    bp_df = p - 1 if intercept else p
    bp_lm = max(0.0, n * aux_r2)
    bp_p = float(stats.chi2.sf(bp_lm, bp_df)) if bp_df > 0 else None
    condition_number = float(np.linalg.cond(design))
    warnings: list[str] = []
    if condition_number > 30:
        warnings.append("elevated_condition_number; inspect scaling and collinearity")
    if covariance_kind == "classical":
        warnings.append("classical_standard_errors_assume_correct_homoskedastic_specification")
    warnings.append("durbin_watson_uses_current_row_order")
    return {
        "type": "regression",
        "model": "ordinary_least_squares",
        "y": y_name,
        "x": x_names,
        "intercept": intercept,
        "covariance": covariance_kind,
        "confidence": confidence,
        "n_complete": int(n),
        "dropped_rows": int(len(frame) - n),
        "rank": int(rank),
        "degrees_of_freedom_residual": int(df_resid),
        "coefficients": coefficients,
        "fit": {
            "r_squared": _round(r_squared),
            "adjusted_r_squared": _round(adjusted),
            "rmse": _round(math.sqrt(np.mean(residual**2))),
            "mae": _round(np.mean(np.abs(residual))),
            "residual_sum_squares": _round(rss),
        },
        "diagnostics": {
            "condition_number": _round(condition_number),
            "singular_values": [_round(value) for value in singular],
            "vif": _vif_values(design, names, intercept),
            "durbin_watson": _round(durbin_watson),
            "normality": normality,
            "breusch_pagan_lm": _round(bp_lm),
            "breusch_pagan_p_value": _round(bp_p),
            "maximum_leverage": _round(np.max(leverage)),
            "high_leverage_count_gt_2p_over_n": int((leverage > 2 * p / n).sum()),
            "maximum_cooks_distance": _round(np.max(cooks)),
            "influential_count_cooks_gt_4_over_n": int((cooks > 4 / n).sum()),
        },
        "warnings": warnings,
        "claim_limit": "conditional_association_not_causation",
    }


def bootstrap_interval(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    column = str(op.get("column", ""))
    require_columns(frame, [column], context="bootstrap")
    statistic = str(op.get("statistic", "mean")).lower()
    if statistic == "proportion":
        if "success" not in op:
            raise DataContractError("bootstrap proportion requires success")
        series = frame[column].dropna()
        success_mask = series == op["success"]
        if not bool(success_mask.any()) and len(series):
            success_mask = series.astype("string") == str(op["success"])
        values = success_mask.to_numpy(dtype=float)
        function = np.mean
    else:
        values = numeric_series(frame, column).dropna().to_numpy(dtype=float)
        function = np.mean if statistic == "mean" else np.median if statistic == "median" else None
    if function is None:
        raise DataContractError("bootstrap statistic must be mean, median, or proportion")
    if len(values) < 2:
        raise DataContractError("bootstrap needs at least 2 usable observations")
    repetitions = int(op.get("repetitions", 5000))
    if not 200 <= repetitions <= 100000:
        raise DataContractError("bootstrap repetitions must be between 200 and 100000")
    seed = _seed(op, job)
    rng = np.random.default_rng(seed)
    estimates = np.empty(repetitions, dtype=float)
    for index in range(repetitions):
        estimates[index] = function(rng.choice(values, len(values), replace=True))
    confidence = _confidence(op, job)
    alpha = 1 - confidence
    return {
        "type": "bootstrap",
        "column": column,
        "statistic": statistic,
        "n": int(len(values)),
        "dropped_rows": int(len(frame) - len(values)),
        "estimate": _round(function(values)),
        "confidence_interval": {
            "low": _round(np.quantile(estimates, alpha / 2)),
            "high": _round(np.quantile(estimates, 1 - alpha / 2)),
            "confidence": confidence,
            "method": "percentile bootstrap",
        },
        "bootstrap_standard_error": _round(estimates.std(ddof=1)),
        "repetitions": repetitions,
        "seed": seed,
    }


def time_change(frame: pd.DataFrame, op: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    time_name, value_name = str(op.get("time", "")), str(op.get("value", ""))
    group_by = [str(value) for value in op.get("group_by", [])]
    require_columns(frame, [*group_by, time_name, value_name], context="time_change")
    work = frame[[*group_by, time_name, value_name]].copy()
    work["__time"] = pd.to_datetime(work[time_name], errors="coerce", utc=True, format="mixed")
    work["__value"] = pd.to_numeric(work[value_name], errors="coerce").replace([np.inf, -np.inf], np.nan)
    invalid_time = int(work["__time"].isna().sum())
    invalid_value = int(work["__value"].isna().sum())
    work = work.dropna(subset=["__time", "__value"])
    duplicate_keys = [*group_by, "__time"]
    duplicates = int(work.duplicated(duplicate_keys, keep=False).sum())
    duplicate_policy = str(op.get("duplicate_policy", "fail")).lower()
    if duplicate_policy not in {"fail", "allow"}:
        raise DataContractError("time_change duplicate_policy must be fail or allow")
    if duplicates and duplicate_policy == "fail":
        raise DataContractError(f"time_change found {duplicates} rows in duplicate group/timestamp keys")
    work = work.sort_values([*group_by, "__time"], kind="mergesort")
    periods = int(op.get("periods", 1))
    if periods <= 0:
        raise DataContractError("time_change periods must be positive")
    grouped = work.groupby(group_by, dropna=False, sort=False)["__value"] if group_by else work["__value"]
    method = str(op.get("method", "difference")).lower()
    zero_baseline_rows = 0
    if method == "difference":
        changes = grouped.diff(periods) if group_by else work["__value"].diff(periods)
    elif method == "pct_change":
        previous = grouped.shift(periods) if group_by else work["__value"].shift(periods)
        zero_baseline_rows = int((previous == 0).sum())
        changes = (work["__value"] - previous) / previous
        changes = changes.mask(previous == 0)
    elif method == "log_return":
        if (work["__value"] <= 0).any():
            raise DataContractError("log_return requires strictly positive values")
        logged = np.log(work["__value"])
        changes = logged.groupby([work[column] for column in group_by], dropna=False).diff(periods) if group_by else logged.diff(periods)
    else:
        raise DataContractError("time_change method must be difference, pct_change, or log_return")
    work["change"] = changes
    max_rows = int(op.get("max_rows", job.get("max_output_rows", 10000)))
    if len(work) > max_rows:
        raise DataContractError(f"time_change would emit {len(work)} rows, above max_output_rows={max_rows}")
    output_rows = []
    for _, row in work.iterrows():
        item = {column: row[column] for column in group_by}
        item.update({"time_utc": row["__time"].isoformat(), "value": _round(row["__value"]), "change": _round(row["change"])})
        output_rows.append(item)
    return {
        "type": "time_change",
        "time": time_name,
        "value": value_name,
        "group_by": group_by,
        "method": method,
        "periods": periods,
        "invalid_time_rows": invalid_time,
        "invalid_value_rows": invalid_value,
        "duplicate_key_rows": duplicates,
        "duplicate_policy": duplicate_policy,
        "zero_baseline_rows": zero_baseline_rows,
        "change_unit": "fraction" if method in {"pct_change", "log_return"} else "source_value_units",
        "rows": output_rows,
        "row_count": len(output_rows),
    }


def _adjust_pvalues(values: list[float], method: str) -> list[float]:
    p = np.asarray(values, dtype=float)
    count = len(p)
    if count == 0:
        return []
    if method == "bonferroni":
        return np.minimum(1, p * count).tolist()
    order = np.argsort(p)
    ranked = p[order]
    if method == "holm":
        adjusted_ranked = np.maximum.accumulate((count - np.arange(count)) * ranked)
    elif method == "fdr_bh":
        adjusted_ranked = np.minimum.accumulate((ranked * count / np.arange(1, count + 1))[::-1])[::-1]
    elif method == "fdr_by":
        harmonic = np.sum(1 / np.arange(1, count + 1))
        adjusted_ranked = np.minimum.accumulate((ranked * count * harmonic / np.arange(1, count + 1))[::-1])[::-1]
    else:
        raise DataContractError("multiple_testing method must be bonferroni, holm, fdr_bh, or fdr_by")
    adjusted_ranked = np.minimum(1, adjusted_ranked)
    adjusted = np.empty(count, dtype=float)
    adjusted[order] = adjusted_ranked
    return adjusted.tolist()


def _apply_multiple_testing(results: list[dict[str, Any]], settings: dict[str, Any]) -> dict[str, Any] | None:
    locations: list[tuple[dict[str, Any], str]] = []
    values: list[float] = []
    for result in results:
        if result.get("p_value") is not None:
            locations.append((result, "p_value"))
            values.append(float(result["p_value"]))
        if result.get("type") == "regression":
            for coefficient in result.get("coefficients", []):
                if coefficient.get("term") != "intercept" and coefficient.get("p_value") is not None:
                    locations.append((coefficient, "p_value"))
                    values.append(float(coefficient["p_value"]))
    if not values:
        return None
    method = str(settings.get("method", "holm")).lower()
    alpha = float(settings.get("alpha", 0.05))
    if not 0 < alpha < 1:
        raise DataContractError("multiple_testing alpha must be strictly between 0 and 1")
    adjusted = _adjust_pvalues(values, method)
    for (container, _), value in zip(locations, adjusted):
        container["p_value_adjusted"] = _round(value)
        container["reject_after_adjustment"] = bool(value <= alpha)
    return {"method": method, "alpha": alpha, "tests_adjusted": len(values)}


HANDLERS = {
    "aggregate": aggregate,
    "correlation": correlation,
    "two_sample": two_sample,
    "paired_sample": paired_sample,
    "contingency": contingency,
    "regression": regression,
    "bootstrap": bootstrap_interval,
    "time_change": time_change,
}


def run_job(job: dict[str, Any], *, input_override: str | None = None, job_base: Path | None = None) -> dict[str, Any]:
    source = input_override or job.get("input")
    if not source:
        raise DataContractError("job requires input, or pass --input")
    source_path = Path(str(source)).expanduser()
    if not source_path.is_absolute() and job_base is not None:
        source_path = job_base / source_path
    numeric_mode = str(job.get("numeric_mode", "float")).lower()
    if numeric_mode not in {"float", "decimal"}:
        raise DataContractError("job numeric_mode must be float or decimal")
    operations = job.get("operations")
    if not isinstance(operations, list) or not operations:
        raise DataContractError("job requires a non-empty operations list")
    needs_source_text = numeric_mode == "decimal" or any(
        isinstance(op, dict) and str(op.get("numeric_mode", "")).lower() == "decimal" for op in operations
    )
    frame, provenance = load_table(
        source_path,
        sheet=job.get("sheet"),
        delimiter=job.get("delimiter"),
        all_strings=needs_source_text,
    )
    results: list[dict[str, Any]] = []
    for index, op in enumerate(operations):
        if not isinstance(op, dict):
            raise DataContractError(f"operation {index} must be an object")
        kind = str(op.get("type", "")).lower()
        if kind not in HANDLERS:
            raise DataContractError(f"operation {index} has unsupported type {kind!r}; supported: {sorted(HANDLERS)}")
        result = HANDLERS[kind](frame, op, job)
        result["operation_index"] = index
        if op.get("id") is not None:
            result["id"] = str(op["id"])
        results.append(result)
    multiple_testing = None
    if job.get("multiple_testing") is not None:
        if not isinstance(job["multiple_testing"], dict):
            raise DataContractError("multiple_testing must be an object")
        multiple_testing = _apply_multiple_testing(results, job["multiple_testing"])
    canonical_job = json.dumps(json_safe(job), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "status": "VERIFIED",
        "provenance": provenance,
        "job_sha256": hashlib.sha256(canonical_job.encode("utf-8")).hexdigest(),
        "numeric_mode": numeric_mode,
        "source_loaded_as_strings": needs_source_text,
        "results": results,
        "multiple_testing": multiple_testing,
        "environment": environment_record(),
        "claim_policy": "Results are calculations or statistical inferences; none are causal without a separate identification design.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, help="JSON analysis job")
    parser.add_argument("--input", help="Override job input path")
    parser.add_argument("--output", help="Write JSON here instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        job_path = Path(args.job).expanduser().resolve()
        job = json.loads(job_path.read_text(encoding="utf-8"))
        if not isinstance(job, dict):
            raise DataContractError("job JSON root must be an object")
        report = run_job(job, input_override=args.input, job_base=job_path.parent)
        write_json(report, args.output)
        return 0
    except (DataContractError, json.JSONDecodeError, OSError) as exc:
        write_json({"status": "QUARANTINE", "error": str(exc)}, args.output)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
