#!/usr/bin/env python3
"""Shared deterministic I/O and JSON helpers for Data Analysis Deep Scan."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SUPPORTED_SUFFIXES = {".csv", ".tsv", ".txt", ".json", ".jsonl", ".ndjson", ".xlsx", ".xls", ".parquet"}


class DataContractError(ValueError):
    """Raised when an input or job cannot be interpreted without guessing."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sheet_value(value: Any) -> Any:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text) if text.isdigit() else text


def load_table(
    source: str | Path,
    *,
    sheet: str | int | None = None,
    delimiter: str | None = None,
    all_strings: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load one local table and return the frame plus a provenance record."""
    path = Path(source).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise DataContractError(f"Input file does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DataContractError(f"Unsupported input format {suffix!r}; supported: {sorted(SUPPORTED_SUFFIXES)}")

    dtype = "string" if all_strings else None
    read_meta: dict[str, Any] = {}
    try:
        if suffix in {".csv", ".tsv", ".txt"}:
            sep = delimiter or ("\t" if suffix == ".tsv" else None)
            if sep is None:
                # Python's sniffer handles comma/semicolon/pipe without silently
                # treating a semicolon file as one column.
                frame = pd.read_csv(path, sep=None, engine="python", dtype=dtype)
                read_meta["delimiter"] = "auto"
            else:
                frame = pd.read_csv(path, sep=sep, dtype=dtype)
                read_meta["delimiter"] = sep
        elif suffix in {".jsonl", ".ndjson"}:
            frame = pd.read_json(path, lines=True, dtype=not all_strings)
            if all_strings:
                frame = frame.astype("string")
            read_meta["json_lines"] = True
        elif suffix == ".json":
            try:
                frame = pd.read_json(path, lines=False, dtype=not all_strings)
                read_meta["json_lines"] = False
            except ValueError:
                frame = pd.read_json(path, lines=True, dtype=not all_strings)
                read_meta["json_lines"] = True
            if all_strings:
                frame = frame.astype("string")
        elif suffix in {".xlsx", ".xls"}:
            chosen_sheet = _sheet_value(sheet)
            frame = pd.read_excel(path, sheet_name=chosen_sheet, dtype=dtype)
            read_meta["sheet"] = chosen_sheet
        else:
            frame = pd.read_parquet(path)
            if all_strings:
                frame = frame.astype("string")
    except ImportError as exc:
        raise DataContractError(f"Missing optional reader for {suffix}: {exc}") from exc
    except Exception as exc:
        raise DataContractError(f"Could not read {path.name}: {exc}") from exc

    if not isinstance(frame, pd.DataFrame):
        raise DataContractError("The selected source did not resolve to exactly one table")
    frame.columns = [str(column) for column in frame.columns]
    if len(set(frame.columns)) != len(frame.columns):
        raise DataContractError("Duplicate column names are ambiguous; rename them before analysis")

    meta = {
        "source": str(path),
        "source_name": path.name,
        "suffix": suffix,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "rows_loaded": int(len(frame)),
        "columns_loaded": int(frame.shape[1]),
        "all_strings": bool(all_strings),
        **read_meta,
    }
    return frame, meta


def require_columns(frame: pd.DataFrame, columns: list[str], *, context: str = "operation") -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataContractError(f"{context} references missing columns: {missing}")


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    require_columns(frame, [column])
    values = pd.to_numeric(frame[column], errors="coerce")
    return values.replace([np.inf, -np.inf], np.nan)


def decimal_value(value: Any) -> Decimal | None:
    if value is None or value is pd.NA:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip().replace("_", "")
    if not text:
        return None
    # Deliberately reject locale-ambiguous thousands/decimal punctuation.
    if "," in text:
        raise DataContractError(f"Decimal value uses ambiguous comma punctuation: {text!r}")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
        raise DataContractError(f"Not a base-10 decimal value: {text!r}")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise DataContractError(f"Invalid decimal value: {text!r}") from exc
    if not result.is_finite():
        raise DataContractError(f"Non-finite decimal value: {text!r}")
    return result


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return value.isoformat()
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return value


def environment_record() -> dict[str, str]:
    record = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }
    try:
        import scipy

        record["scipy"] = scipy.__version__
    except ImportError:
        record["scipy"] = "unavailable"
    return record


def write_json(payload: Any, output: str | Path | None = None) -> None:
    text = json.dumps(json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    if output:
        Path(output).expanduser().resolve().write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
