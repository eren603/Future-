"""Standard-library C0 and OHLC candle contract, shared by detection and rendering."""
import math
import re
from datetime import datetime


class TespitError(ValueError):
    pass


_KEYMAP = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
           "open": "open", "high": "high", "low": "low", "close": "close",
           "volume": "volume"}


def epoch_ms(value):
    """Numeric epoch seconds/ms/us/ns or timezone-qualified ISO -> milliseconds."""
    if isinstance(value, bool):
        raise TespitError("zaman boolean olamaz")
    try:
        number = float(value)
    except (ValueError, TypeError):
        try:
            stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise TespitError("ISO zamanında timezone gerekli")
            number = stamp.timestamp() * 1000
        except (ValueError, TypeError) as exc:
            raise TespitError(f"geçersiz zaman: {value!r}") from exc
    else:
        magnitude = abs(number)
        number *= 1000 if magnitude < 1e11 else (1 if magnitude < 1e14 else
                                                 (.001 if magnitude < 1e17 else .000001))
    if not math.isfinite(number):
        raise TespitError("zaman sonlu olmalı")
    return int(round(number))


def _closed(value):
    if value is None:
        return None
    if value in (True, 1, "true", "True", "1"):
        return True
    if value in (False, 0, "false", "False", "0"):
        return False
    raise TespitError("closed true/false olmalı")


def normalize_candles(rows, job=None):
    """Shared normalization without a minimum row count; no current-time inference.

    Returns (records, time_contract). An explicit cutoff requires known close
    times. Untimed legacy data is retained as time_unverified, never C0-safe.
    """
    job = job or {}
    allowed = {"c0", "cutoff", "as_of"}
    for key in job:
        name = str(key).lower()
        if name not in allowed and (name.startswith("c0") or "cutoff" in name or
                                    name.startswith("as_of")):
            raise TespitError(f"desteklenmeyen kesim alanı {key}; c0/cutoff/as_of kullan")
    cuts = [epoch_ms(job[k]) for k in allowed if job.get(k) is not None]
    if len(set(cuts)) > 1:
        raise TespitError("c0/cutoff/as_of aynı zamanı göstermeli")
    cutoff = cuts[0] if cuts else None
    interval = job.get("interval_seconds")
    declared_timeframe = str(job.get("timeframe") or "")
    if job.get("timeframe"):
        match = re.fullmatch(r"(\d+)([smhdw])", declared_timeframe)
        if match:
            declared_interval = int(match[1]) * {"s": 1, "m": 60, "h": 3600,
                                                "d": 86400, "w": 604800}[match[2]]
            if interval is not None and float(interval) != declared_interval:
                raise TespitError("timeframe ile interval_seconds çelişiyor")
            interval = declared_interval
        else:
            raise TespitError("timeframe 1m/15m/1h/4h/1d/1w gibi sabit bir aralık olmalı")
    interval_ms = float(interval) * 1000 if interval is not None else None
    if interval_ms is not None and (not math.isfinite(interval_ms) or interval_ms <= 0):
        raise TespitError("interval_seconds pozitif ve sonlu olmalı")
    convention = job.get("close_time_convention", "inclusive")
    if convention not in ("inclusive", "exclusive"):
        raise TespitError("close_time_convention inclusive|exclusive olmalı")
    origin_ms = 345_600_000 if declared_timeframe.endswith("w") else 0
    normalized, excluded = [], {"open": 0, "future": 0}
    for source_i, original in enumerate(rows):
        if isinstance(original, (list, tuple)):
            if len(original) < 6:
                raise TespitError("Binance mumunda en az 6 alan gerekli")
            row = dict(zip(("open_time", "open", "high", "low", "close", "volume"), original[:6]))
            if len(original) >= 7:
                row["close_time"] = original[6]
        else:
            row = {str(k).strip().lower(): v for k, v in dict(original).items()}
        for alias, canonical in _KEYMAP.items():
            if alias in row:
                row[canonical] = row[alias]
        source = row.get("source_i", source_i)
        if isinstance(source, bool) or int(source) != float(source) or int(source) < 0:
            raise TespitError("source_i negatif olmayan tam sayı olmalı")
        row["source_i"] = int(source)
        flag = _closed(row.get("closed", row.get("is_closed")))
        if flag is False:
            excluded["open"] += 1
            continue
        op_raw = next((row[k] for k in ("open_time", "timestamp", "time", "t")
                       if row.get(k) is not None), None)
        cl_raw = row.get("close_time")
        op_ms = row.get("open_time_ms")
        cl_ms = row.get("close_time_ms")
        op_ms = int(op_ms) if op_ms is not None else (epoch_ms(op_raw) if op_raw is not None else None)
        cl_ms = int(cl_ms) if cl_ms is not None else (epoch_ms(cl_raw) if cl_raw is not None else None)
        if op_raw is not None and op_ms != epoch_ms(op_raw):
            raise TespitError("open_time ile open_time_ms çelişiyor")
        if cl_raw is not None and cl_ms != epoch_ms(cl_raw):
            raise TespitError("close_time ile close_time_ms çelişiyor")
        if cl_ms is None and op_ms is not None and interval_ms is not None:
            cl_ms = int(op_ms + interval_ms - (1 if convention == "inclusive" else 0))
        if interval_ms is not None and op_ms is not None:
            if (op_ms-origin_ms) % interval_ms != 0:
                raise TespitError("open_time bildirilen mum aralığının zaman ızgarasına uymuyor")
            expected_close = op_ms + interval_ms - (1 if convention == "inclusive" else 0)
            if cl_ms is not None and cl_ms != expected_close:
                raise TespitError("close_time bildirilen mum aralığıyla çelişiyor")
        if cutoff is not None and cl_ms is None:
            raise TespitError("kesim için close_time veya open_time + interval_seconds/timeframe gerekli")
        if cl_ms is not None and op_ms is not None and cl_ms < op_ms:
            raise TespitError("close_time open_time'dan önce olamaz")
        if cutoff is not None and cl_ms > cutoff:
            excluded["future"] += 1
            continue
        if cutoff is not None:
            flag = True
        for key in ("open", "high", "low", "close"):
            try:
                row[key] = float(row[key])
            except (KeyError, ValueError, TypeError) as exc:
                raise TespitError(f"mum {source_i}: sayısal {key} gerekli") from exc
            if not math.isfinite(row[key]):
                raise TespitError(f"mum {source_i}: {key} sonlu olmalı; eksik mum sessizce silinmez")
        if row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"]):
            raise TespitError(f"mum {source_i}: OHLC geometrisi geçersiz")
        if "volume" in row:
            row["volume"] = float(row["volume"])
            if not math.isfinite(row["volume"]) or row["volume"] < 0:
                raise TespitError("hacim negatif veya sonlu olmayan sayı olamaz")
        row.update(open_time_ms=op_ms, close_time_ms=cl_ms, closed=flag)
        normalized.append(row)
    times = [r["open_time_ms"] for r in normalized]
    if len({r["source_i"] for r in normalized}) != len(normalized):
        raise TespitError("source_i değerleri benzersiz olmalı")
    if any(t is not None for t in times) and not all(t is not None for t in times):
        raise TespitError("zamanlı ve zamansız mumlar karıştırılamaz")
    gaps = []
    expected = interval_ms
    if times and all(t is not None for t in times):
        differences = [b-a for a, b in zip(times, times[1:])]
        if any(d <= 0 for d in differences):
            raise TespitError("mum zamanları benzersiz ve artan sırada olmalı")
        expected = interval_ms
        if expected is None and differences:
            ordered = sorted(differences)
            expected = ordered[len(ordered)//2]
        gaps = [i+1 for i, d in enumerate(differences) if d != expected]
        if expected is not None:
            for row in normalized:
                if row["close_time_ms"] is not None and row["close_time_ms"] != (
                        row["open_time_ms"] + expected - (1 if convention == "inclusive" else 0)):
                    raise TespitError("close_time mumların gözlenen aralığıyla çelişiyor")
    segment = 0
    for i, row in enumerate(normalized):
        if i in gaps:
            segment += 1
        row["segment_id"] = segment
    verified = cutoff is not None and bool(normalized) and not gaps and all(
        r["closed"] is True and r["close_time_ms"] is not None and
        r["open_time_ms"] is not None for r in normalized)
    contract = {"status": "verified" if verified else "time_unverified",
                "cutoff_ms": cutoff, "c0_time_ms": normalized[-1]["close_time_ms"] if normalized else None,
                "c0_source_i": normalized[-1]["source_i"] if normalized else None,
                "gaps_before_i": gaps, "excluded": excluded,
                "input_rows": len(rows), "retained_rows": len(normalized), "interval_ms": expected,
                "reason": None if verified else "kapanış/zaman doğrulanmadı veya mum aralığında boşluk var"}
    return normalized, contract
