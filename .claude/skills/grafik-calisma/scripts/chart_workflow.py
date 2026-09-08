#!/usr/bin/env python3
"""C0-bound chart decisions and an append-only, local paper-evaluation ledger.

No exchange calls, orders, training, or score-to-probability conversion. Direction
is an analyst observation. OHLC outcomes are simulations, never actual fills.
"""
import argparse
import copy
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

from candle_contract import normalize_candles, epoch_ms

TF_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000}
VERSION = "chart-decision/v1"


class WorkflowError(ValueError):
    pass


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise WorkflowError("JSON yalnızca sonlu sayılar ve standart türler içermeli") from exc


def digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _seal(value, key):
    result = copy.deepcopy(value)
    result[key] = digest(result)
    return result


def _verify(value, key):
    unsigned = copy.deepcopy(value)
    supplied = unsigned.pop(key, None)
    if supplied is None or digest(unsigned) != supplied:
        raise WorkflowError(f"{key}: içerik özeti uyuşmuyor")


def _dec(value, name, positive=True):
    if isinstance(value, bool):
        raise WorkflowError(f"{name}: boolean fiyat olamaz")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise WorkflowError(f"{name}: sayı gerekli") from exc
    if not result.is_finite() or (result <= 0 if positive else result < 0):
        raise WorkflowError(f"{name}: {'pozitif' if positive else 'negatif olmayan'} sonlu sayı gerekli")
    return result


def _price(value, tick, name):
    result = _dec(value, name)
    if result % tick != 0:
        raise WorkflowError(f"{name}: tick_size ile hizalı değil")
    return result


def _str(value):
    return format(value.normalize(), "f")


def _ms(value, name):
    if value is None:
        raise WorkflowError(f"{name} gerekli")
    try:
        return epoch_ms(value)
    except ValueError as exc:
        raise WorkflowError(f"{name}: {exc}") from exc


def _now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _int(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise WorkflowError(f"{name}: en az {minimum} tamsayı gerekli")
    return value


def _check_rows(records, contract, tf, tick, allow_cutoff_filter=False):
    if contract["status"] != "verified" or (not allow_cutoff_filter and any(contract["excluded"].values())):
        raise WorkflowError(f"{tf}: açık/gelecek/boşluklu veya doğrulanmamış mum reddedildi")
    step = TF_MS[tf]
    for i, bar in enumerate(records):
        if bar["open_time_ms"] % step or bar["close_time_ms"] != bar["open_time_ms"] + step - 1:
            raise WorkflowError(f"{tf} mum {i}: UTC aralık hizası/kapanış zamanı geçersiz")
        for name in ("open", "high", "low", "close"):
            _price(bar[name], tick, f"{tf} mum {i} {name}")


def _provenance(part, job, cutoff):
    source = part.get("source", job.get("source"))
    if not source or not isinstance(source, (str, dict)):
        raise WorkflowError("source: kaynak URL veya kaynak nesnesi gerekli")
    retrieved = _ms(part.get("retrieved_at", job.get("retrieved_at")), "retrieved_at")
    if retrieved < cutoff:
        raise WorkflowError("retrieved_at kesim zamanından önce olamaz")
    return {"source": copy.deepcopy(source), "retrieved_at_ms": retrieved,
            "verification": "caller_supplied_provenance"}


def prepare(case_job):
    """Validate one Binance USD-M symbol across complete 15m/1h/4h histories.

    Input: {venue:'BINANCE_USDM',symbol,cutoff,tick_size,source,retrieved_at,
      timeframes:{'15m':{symbol,timeframe,rows},'1h':{...},'4h':{...}},screenshots:[]}
    All timestamps use epoch seconds/ms or timezone ISO. Twenty bars per TF is
    a mechanical minimum, not evidence that a particular setup is reliable.
    """
    job = copy.deepcopy(case_job)
    raw_hash = digest(job)
    if job.get("venue") != "BINANCE_USDM":
        raise WorkflowError("venue BINANCE_USDM olmalı")
    symbol = job.get("symbol", "")
    if not re.fullmatch(r"[A-Z0-9_]{4,32}", symbol):
        raise WorkflowError("symbol: büyük harfli Binance sözleşme kodu gerekli")
    cutoff = _ms(job.get("cutoff"), "cutoff")
    tick = _dec(job.get("tick_size"), "tick_size")
    frames = job.get("timeframes", {})
    if set(frames) != set(TF_MS):
        raise WorkflowError("tam olarak 15m, 1h, 4h mum kümeleri gerekli")
    normalized = {}
    for tf, step in TF_MS.items():
        part = frames[tf]
        if part.get("symbol") != symbol or part.get("timeframe") != tf:
            raise WorkflowError(f"{tf}: sembol/zaman dilimi eşleşmiyor")
        rows = part.get("rows")
        if not isinstance(rows, list) or len(rows) < 20:
            raise WorkflowError(f"{tf}: en az 20 kapalı mum gerekli")
        for row in rows:
            if isinstance(row, dict):
                if row.get("symbol", symbol) != symbol or row.get("timeframe", tf) != tf:
                    raise WorkflowError(f"{tf}: mum içinde farklı sembol/zaman dilimi")
        records, contract = normalize_candles(rows, {"cutoff": cutoff, "timeframe": tf})
        _check_rows(records, contract, tf, tick, allow_cutoff_filter=True)
        if len(records) < 20:
            raise WorkflowError(f"{tf}: C0 filtresinden sonra en az 20 kapalı mum gerekli")
        expected_close = ((cutoff + 1) // step) * step - 1
        if records[-1]["close_time_ms"] != expected_close:
            raise WorkflowError(f"{tf}: kesim anındaki son kapalı mum eksik")
        normalized[tf] = {"symbol": symbol, "timeframe": tf, "rows": records,
                          "raw_sha256": digest(rows), "normalized_sha256": digest(records),
                          "count": len(records), "input_count": len(rows), "retained_count": len(records),
                          "excluded_counts": copy.deepcopy(contract["excluded"]), "time_contract": contract,
                          "provenance": _provenance(part, job, cutoff)}
    images = []
    for screenshot in job.get("screenshots", []):
        item = {"path": screenshot} if isinstance(screenshot, str) else dict(screenshot)
        if item.get("timeframe") is not None and item["timeframe"] not in TF_MS:
            raise WorkflowError("ekran görüntüsü zaman dilimi geçersiz")
        path = Path(item["path"]).expanduser().resolve()
        if not path.is_file():
            raise WorkflowError(f"ekran görüntüsü bulunamadı: {path}")
        images.append({"path": str(path), "timeframe": item.get("timeframe"),
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "bytes": path.stat().st_size})
    c0 = normalized["15m"]["rows"][-1]["close_time_ms"]
    return _seal({"schema_version": "chart-case/v1", "venue": "BINANCE_USDM",
                  "symbol": symbol, "tick_size": _str(tick), "requested_cutoff_ms": cutoff,
                  "cutoff_ms": c0, "reference_close": _str(_dec(normalized["15m"]["rows"][-1]["close"], "close")),
                  "raw_job_sha256": raw_hash, "timeframes": normalized, "screenshots": images,
                  "history_policy": {"minimum_bars_each": 20, "reliability_claim": False}}, "case_sha256")


def _anchors(items, case, required=False):
    if not isinstance(items, list) or (required and not items):
        raise WorkflowError("kanıt: gerekçeli mum referansları gerekli")
    result = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("reason", "")).strip():
            raise WorkflowError("her kanıtın reason gerekçesi gerekli")
        tf = item.get("timeframe")
        if tf not in TF_MS:
            raise WorkflowError("kanıt zaman dilimi 15m/1h/4h olmalı")
        i = _int(item.get("bar_index"), "bar_index", minimum=0)
        rows = case["timeframes"][tf]["rows"]
        if i >= len(rows):
            raise WorkflowError("kanıt indeksi C0 sonrasına veya küme dışına taşıyor")
        closed = rows[i]["close_time_ms"]
        if closed > case["cutoff_ms"]:
            raise WorkflowError("kanıt zamanı C0 sonrasına taşıyor")
        for key in ("time", "timestamp", "bar_close_time_ms"):
            if key in item and _ms(item[key], key) != closed:
                raise WorkflowError("kanıt zamanı referans mumun kapanışıyla eşleşmiyor")
        result.append({"reason": str(item["reason"]).strip(), "timeframe": tf,
                       "bar_index": i, "bar_close_time_ms": closed})
    return result


def _rr(direction, edges, stop, targets, costs):
    gross, net = [], []
    sign = Decimal(1) if direction == "LONG" else Decimal(-1)
    known = costs["status"] == "explicit_assumption"
    bps = (Decimal(costs["fee_bps_per_side"]) + Decimal(costs["slippage_bps_per_side"])) / 10000 if known else None
    for target in targets:
        gr, nr = {}, {}
        for name, entry in zip(("entry_low", "entry_mid", "entry_high"), edges):
            risk = sign * (entry - stop)
            reward = sign * (target - entry)
            gr[name] = reward / risk
            if known:
                win_cost, loss_cost = (entry + target) * bps, (entry + stop) * bps
                nr[name] = (reward - win_cost) / (risk + loss_cost)
        gross.append({"target": _str(target), **{k: _str(v) for k, v in gr.items()},
                      "min": _str(min(gr.values())), "max": _str(max(gr.values()))})
        if known:
            net.append({"target": _str(target), **{k: _str(v) for k, v in nr.items()},
                        "min": _str(min(nr.values())), "max": _str(max(nr.values()))})
    return {"gross": gross, "net": net if known else None, "costs": costs,
            "net_definition": "(gross_reward - entry_exit_cost) / (gross_stop_risk + entry_stop_cost)",
            "cost_note": "Komisyon ve kayma iki yönlü fiyat yüzdesi varsayımıdır; funding dahil değil."}


def build_plan(prepared_case, visual_observation):
    """Build an auditable decision from explicitly supplied visual observations.

    A first_leg is never inferred from structure or assigned a probability.
    Invalid supplied geometry errors. Missing geometry produces a blocked card
    while preserving the directional assessment.
    """
    _verify(prepared_case, "case_sha256")
    case, obs = prepared_case, copy.deepcopy(visual_observation)
    direction = obs.get("first_leg")
    if isinstance(direction, dict):
        direction = direction.get("direction")
    if direction not in ("LONG", "SHORT", "UNCERTAIN"):
        raise WorkflowError("first_leg açıkça LONG, SHORT veya UNCERTAIN olmalı")
    if not str(obs.get("main_structure", "")).strip():
        raise WorkflowError("main_structure ilk bacaktan ayrı açıklanmalı")
    evidence = _anchors(obs.get("direction_evidence", []), case, required=direction != "UNCERTAIN")
    entry_input = obs.get("entry") or {}
    trade_direction = entry_input.get("direction", direction if direction != "UNCERTAIN" else None)
    if trade_direction not in (None, "LONG", "SHORT"):
        raise WorkflowError("entry.direction açıkça LONG/SHORT olmalı")
    trade_evidence = _anchors(entry_input.get("direction_evidence", obs.get("direction_evidence", [])), case,
                             required=trade_direction is not None)
    horizon_bars = _int(obs.get("horizon_bars", 12), "horizon_bars")
    horizon_end = case["cutoff_ms"] + horizon_bars * TF_MS["15m"]
    validity = obs.get("validity", {})
    expiry = _ms(validity.get("expires_at", horizon_end), "expires_at")
    if not case["cutoff_ms"] < expiry <= horizon_end:
        raise WorkflowError("geçerlilik C0 sonrasında ve ufuk bitişinden önce/eşit olmalı")
    if (expiry + 1) % TF_MS["15m"]:
        raise WorkflowError("expires_at kapalı 15m mumunun kapanışına hizalanmalı")
    costs = obs.get("costs")
    if costs is None:
        costs = {"status": "unknown", "fee_bps_per_side": None, "slippage_bps_per_side": None}
    else:
        costs = {"status": "explicit_assumption",
                 "fee_bps_per_side": _str(_dec(costs.get("fee_bps_per_side"), "fee_bps_per_side", False)),
                 "slippage_bps_per_side": _str(_dec(costs.get("slippage_bps_per_side"), "slippage_bps_per_side", False))}
    result = {"schema_version": VERSION, "symbol": case["symbol"], "venue": case["venue"],
              "case_sha256": case["case_sha256"], "raw_job_sha256": case["raw_job_sha256"],
              "tick_size": case["tick_size"], "cutoff_ms": case["cutoff_ms"],
              "reference_close": case["reference_close"], "observation_sha256": digest(obs),
              "input_hashes": {tf: {"raw": data["raw_sha256"], "normalized": data["normalized_sha256"],
                                    "count": data["count"], "input_count": data["input_count"],
                                    "excluded_counts": data["excluded_counts"], "provenance": data["provenance"]}
                               for tf, data in case["timeframes"].items()},
              "screenshots": case["screenshots"],
              "first_leg": {"direction": direction, "assessment_source": "analyst_visual_input",
                            "evidence": evidence, "probability": None},
              "main_structure": str(obs["main_structure"]),
              "horizon": {"timeframe": "15m", "bars": horizon_bars, "end_ms": horizon_end},
              "validity": {"expires_at_ms": expiry}, "costs": costs,
              "entry": None, "invalidation": None, "targets": [], "rr": None}
    first_leg_test = obs.get("first_leg_test")
    result["first_leg_test"] = None
    if first_leg_test is not None:
        tick = _dec(case["tick_size"], "tick_size")
        upper = _price(first_leg_test.get("up_price"), tick, "first_leg_test.up_price")
        lower = _price(first_leg_test.get("down_price"), tick, "first_leg_test.down_price")
        if not lower < Decimal(case["reference_close"]) < upper:
            raise WorkflowError("ilk bacak test eşikleri C0 kapanışının iki yanında olmalı")
        result["first_leg_test"] = {"up_price": _str(upper), "down_price": _str(lower),
            "definition": "first_touch_of_preregistered_barriers_from_first_complete_post_record_bar",
            "untouched_or_same_bar_both": "unscored", "end_ms": horizon_end,
            "baseline_note": "Barriers may be asymmetric; no 50% or universal first-leg baseline is assumed.",
            "gap_policy": "Both barriers in one bar remain conservatively ambiguous, including opening gaps."}
    missing = [key for key in ("entry", "stop", "targets") if obs.get(key) is None or obs.get(key) == []]
    blocked = trade_direction is None or bool(missing)
    reason = "İlk bacak belirsiz; açık yönlü işlem senaryosu yok." if trade_direction is None else "Plan geometrisi eksik: " + ", ".join(missing)
    if not blocked:
        tick = _dec(case["tick_size"], "tick_size")
        entry = obs["entry"]
        if entry.get("type") not in ("limit", "stop", "market"):
            raise WorkflowError("entry.type limit/stop/market olmalı")
        if entry.get("trigger_status") not in ("conditional", "confirmed"):
            raise WorkflowError("entry.trigger_status conditional/confirmed olmalı")
        zone = entry.get("zone")
        if not isinstance(zone, list) or len(zone) != 2:
            raise WorkflowError("entry.zone [alt,üst] olmalı")
        low, high = [_price(p, tick, "entry.zone") for p in zone]
        if low > high:
            raise WorkflowError("giriş bölgesi alt sınırı üst sınırı geçemez")
        stop = _price(obs["stop"], tick, "stop")
        targets = [_price(p, tick, "target") for p in obs["targets"]]
        if len(set(targets)) != len(targets):
            raise WorkflowError("hedefler benzersiz olmalı")
        if trade_direction == "LONG":
            valid = stop < low and all(t > high for t in targets) and targets == sorted(targets)
        else:
            valid = stop > high and all(t < low for t in targets) and targets == sorted(targets, reverse=True)
        if not valid:
            raise WorkflowError("yön, stop, giriş ve sıralı hedef geometrisi uyuşmuyor")
        confirmed = entry["trigger_status"] == "confirmed"
        trigger_evidence = _anchors(entry.get("trigger_evidence", []), case, required=confirmed)
        trigger_model = entry.get("trigger_model", "confirmed_at_cutoff" if confirmed else "analyst_confirmation")
        allowed = ("confirmed_at_cutoff",) if confirmed else ("price_touch", "analyst_confirmation")
        if trigger_model not in allowed:
            raise WorkflowError("trigger_model teyit durumuyla uyuşmuyor")
        description = str(entry.get("trigger_description") or "").strip()
        if trigger_model == "analyst_confirmation" and not description:
            raise WorkflowError("koşullu görsel teyit için entry.trigger_description gerekli")
        if entry["type"] == "market" and not confirmed:
            raise WorkflowError("koşullu market girişinde önce görsel teyit gerekli")
        reference = high if trade_direction == "LONG" else low
        result["entry"] = {"direction": trade_direction, "direction_evidence": trade_evidence,
                           "type": entry["type"], "zone": [_str(low), _str(high)],
                           "reference_price": _str(reference), "trigger_status": entry["trigger_status"],
                           "trigger_model": trigger_model, "trigger_description": description or None,
                           "trigger_evidence": trigger_evidence,
                           "paper_fill_rule": "first_complete_post_record_bar; market=open; limit/stop=touch_with_open_gap"}
        result["invalidation"] = {"stop": _str(stop)}
        result["targets"] = [_str(p) for p in targets]
        with localcontext() as ctx:
            ctx.prec = 28
            result["rr"] = _rr(trade_direction, (low, (low + high) / 2, high), stop, targets, costs)
        reason = "Teyit C0 mumlarında mevcut; giriş koşulları geçerlilik süresinde izlenir." if confirmed else "Giriş koşulu bekleniyor; yön değerlendirmesi korunur."
    status = "blocked" if blocked else obs["entry"]["trigger_status"]
    result["final_decision"] = {"status": status, "direction": trade_direction or direction, "cutoff_ms": case["cutoff_ms"], "reason": reason}
    if result.get("entry") and result["entry"].get("trigger_description"):
        reason += " Koşul: " + result["entry"]["trigger_description"]
        result["final_decision"]["reason"] = reason
    result["text_tr"] = f"İlk bacak: {direction}. İşlem senaryosu: {trade_direction or 'yok'}. Durum: { {'blocked':'işlem yok','conditional':'koşullu','confirmed':'teyitli'}[status] }. {reason}"
    return _seal(result, "plan_sha256")


def _read_events(handle):
    handle.seek(0)
    events, previous, ids = [], None, set()
    for line_no, line in enumerate(handle, 1):
        if not line.strip():
            raise WorkflowError(f"kayıt {line_no}: boş satır")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkflowError(f"kayıt {line_no}: bozuk JSON") from exc
        _verify(event, "event_sha256")
        if event.get("previous_sha256") != previous or event.get("sequence") != line_no:
            raise WorkflowError("defter hash zinciri/sırası değişmiş")
        if event["event_id"] in ids:
            raise WorkflowError("tekrarlanan event_id")
        ids.add(event["event_id"])
        if event.get("kind") == "plan":
            _verify(event["plan"], "plan_sha256")
        previous = event["event_sha256"]
        events.append(event)
    return events


def _append(path, create_event):
    import fcntl
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        events = _read_events(handle)
        event = create_event(events)
        event.update(event_id=str(uuid.uuid4()), sequence=len(events) + 1,
                     previous_sha256=events[-1]["event_sha256"] if events else None)
        event = _seal(event, "event_sha256")
        handle.seek(0, 2)
        handle.write(_json(event) + "\n")
        handle.flush()
        import os
        os.fsync(handle.fileno())
        return event


def record_plan(ledger_path, plan, recorded_at=None):
    """Append before outcomes. An injected timestamp is labeled retrospective.

    Local digest chaining detects ordinary mutation; it is not notarization or
    protection against an adversary rewriting and rehashing the whole file.
    """
    _verify(plan, "plan_sha256")
    now = _now_ms() if recorded_at is None else _ms(recorded_at, "recorded_at")
    if now <= plan["cutoff_ms"]:
        raise WorkflowError("kayıt zamanı C0 sonrasında olmalı")
    until = min(plan["horizon"]["end_ms"], plan["validity"]["expires_at_ms"])
    first_open = ((now + TF_MS["15m"] - 1) // TF_MS["15m"]) * TF_MS["15m"]
    if first_open + TF_MS["15m"] - 1 > until:
        raise WorkflowError("geçerlilik süresinde kayıt sonrası tam 15m mumu kalmıyor")
    def event(events):
        if any(e.get("plan", {}).get("plan_sha256") == plan["plan_sha256"] for e in events):
            raise WorkflowError("aynı plan zaten kaydedilmiş")
        return {"kind": "plan", "record_id": str(uuid.uuid4()), "recorded_at_ms": now,
                "clock_source": "system" if recorded_at is None else "declared_test_or_retrospective",
                "prospective_clock_eligible": recorded_at is None, "plan": copy.deepcopy(plan)}
    return _append(ledger_path, event)


def _paper_pnl(plan, fill, exit_price):
    sign = Decimal(1) if plan["final_decision"]["direction"] == "LONG" else Decimal(-1)
    stop = Decimal(plan["invalidation"]["stop"])
    risk = sign * (fill - stop)
    gross = sign * (exit_price - fill)
    costs = plan["costs"]
    net = None
    if costs["status"] == "explicit_assumption":
        rate = (Decimal(costs["fee_bps_per_side"]) + Decimal(costs["slippage_bps_per_side"])) / 10000
        net = gross - (fill + exit_price) * rate
    return {"gross_pnl_per_unit": _str(gross), "net_pnl_per_unit": _str(net) if net is not None else None,
            "gross_R": _str(gross / risk), "net_R_on_initial_gross_risk": _str(net / risk) if net is not None else None}


def evaluate_future(plan_record, future_job, resolved_at=None):
    """Evaluate only complete future 15m bars, with explicit paper-fill assumptions.

    All targets stay in the plan; evaluation uses the first target, full exit.
    Unknown intra-bar ordering is ambiguous, never upgraded to a winner.
    """
    plan = plan_record["plan"]
    _verify(plan, "plan_sha256")
    if future_job.get("symbol") != plan["symbol"] or future_job.get("timeframe") != "15m":
        raise WorkflowError("gelecek veri sembolü/15m zaman dilimi uyuşmuyor")
    now = _now_ms() if resolved_at is None else _ms(resolved_at, "resolved_at")
    if now < plan_record["recorded_at_ms"]:
        raise WorkflowError("çözümleme kayıttan önce olamaz")
    rows = future_job.get("rows")
    if not isinstance(rows, list) or not rows:
        raise WorkflowError("gelecek mumlar gerekli")
    for row in rows:
        if isinstance(row, dict) and (row.get("symbol", plan["symbol"]) != plan["symbol"] or row.get("timeframe", "15m") != "15m"):
            raise WorkflowError("gelecek mum içinde farklı sembol/zaman dilimi")
    records, contract = normalize_candles(rows, {"cutoff": now, "timeframe": "15m"})
    _check_rows(records, contract, "15m", Decimal(plan["tick_size"]))
    if len(records) != len(rows):
        raise WorkflowError("gelecek veri açık veya henüz oluşmamış mum içeriyor")
    start = ((max(plan["cutoff_ms"] + 1, plan_record["recorded_at_ms"]) + TF_MS["15m"] - 1) // TF_MS["15m"]) * TF_MS["15m"]
    if records[0]["open_time_ms"] != start:
        raise WorkflowError("gelecek veri ilk tam kayıt-sonrası mumdan başlamalı; C0/ara mum atlanamaz")
    if any(r["open_time_ms"] <= plan["cutoff_ms"] or r["open_time_ms"] < plan_record["recorded_at_ms"] for r in records):
        raise WorkflowError("gelecek veri C0 veya kayıt öncesi bilgi içeriyor")
    provenance = _provenance(future_job, future_job, records[-1]["close_time_ms"])
    if provenance["retrieved_at_ms"] > now:
        raise WorkflowError("gelecek veri retrieved_at çözümleme anından sonra olamaz")
    horizon = plan["horizon"]["end_ms"]
    until = min(horizon, plan["validity"]["expires_at_ms"])
    available = [r for r in records if r["close_time_ms"] <= until]
    horizon_bar = next((r for r in records if r["close_time_ms"] == horizon), None)
    direction = plan["first_leg"]["direction"]
    direction_result = {"status": "pending", "correct": None, "horizon_close": None}
    if horizon_bar is not None:
        close, ref = Decimal(str(horizon_bar["close"])), Decimal(plan["reference_close"])
        actual = "LONG" if close > ref else "SHORT" if close < ref else "FLAT"
        direction_result = {"status": "resolved" if direction != "UNCERTAIN" and actual != "FLAT" else "abstained_or_flat",
                            "correct": direction == actual if direction != "UNCERTAIN" and actual != "FLAT" else None,
                            "actual_direction": actual, "horizon_close": _str(close),
                            "definition": "horizon_close_vs_C0_close; not_first_touch_order"}
    first_leg_outcome = {"status": "not_configured", "correct": None,
                         "actual_direction": None, "definition": None}
    if plan.get("first_leg_test") is not None:
        spec = plan["first_leg_test"]
        upper, lower = Decimal(spec["up_price"]), Decimal(spec["down_price"])
        first_leg_outcome.update(status="pending", definition=spec["definition"],
                                 evaluation_start_ms=start, end_ms=horizon,
                                 missing_C0_to_record_interval=start > plan["cutoff_ms"] + 1)
        for bar in records:
            if bar["close_time_ms"] > horizon:
                break
            up = Decimal(str(bar["high"])) >= upper
            down = Decimal(str(bar["low"])) <= lower
            if up or down:
                actual = None if up and down else "LONG" if up else "SHORT"
                first_leg_outcome.update(status="ambiguous" if up and down else "abstained" if direction == "UNCERTAIN" else "resolved",
                                         actual_direction=actual,
                                         correct=(direction == actual) if actual is not None and direction != "UNCERTAIN" else None,
                                         bar_open_time_ms=bar["open_time_ms"])
                break
        else:
            if horizon_bar is not None:
                first_leg_outcome["status"] = "untouched"
        if first_leg_outcome["status"] == "pending" and horizon_bar is not None:
            first_leg_outcome["status"] = "untouched"
    output = {"status": "unfilled", "complete": False, "filled": False, "fill": None,
              "exit": None, "pnl": None, "target_policy": "first_target_full_exit",
              "mode": "OHLC_paper_simulation_not_actual_fills", "direction_outcome": direction_result,
              "first_leg_outcome": first_leg_outcome,
              "future_raw_sha256": digest(rows), "future_normalized_sha256": digest(records),
              "future_provenance": provenance, "future_count": len(records), "evaluated_count": len(available),
              "horizon_end_ms": horizon, "valid_until_ms": until, "evaluation_start_ms": start,
              "record_delay_excluded_bars": (start - (plan["cutoff_ms"] + 1)) // TF_MS["15m"],
              "costs": plan["costs"], "reason": "Giriş henüz oluşmadı."}
    if plan["final_decision"]["status"] == "blocked":
        output.update(status="blocked", complete=True, reason="Kayıtta uygun işlem geometrisi yok.")
        return output
    entry = plan["entry"]
    if entry["trigger_model"] == "analyst_confirmation":
        output.update(complete=bool(available and available[-1]["close_time_ms"] == until),
                      reason="Görsel teyit OHLC ile varsayılmadı; fiyat teması giriş sayılmaz.")
        if output["complete"]:
            output["status"] = "expired"
        return output
    long = plan["final_decision"]["direction"] == "LONG"
    reference, stop, target = Decimal(entry["reference_price"]), Decimal(plan["invalidation"]["stop"]), Decimal(plan["targets"][0])
    fill = None
    for bar in available:
        o, h, l = [Decimal(str(bar[k])) for k in ("open", "high", "low")]
        stop_hit = l <= stop if long else h >= stop
        target_hit = h >= target if long else l <= target
        filled_this_bar, known_at_open = False, False
        if fill is None:
            typ = entry["type"]
            touch = typ == "market" or ((l <= reference if long else h >= reference) if typ == "limit" else (h >= reference if long else l <= reference))
            if not touch:
                if stop_hit:
                    output.update(status="invalidated", complete=True, reason="Giriş öncesinde stop/geçersizlik seviyesi aşıldı.")
                    return output
                continue
            fill = o if typ == "market" else ((min(o, reference) if long else max(o, reference)) if typ == "limit" else (max(o, reference) if long else min(o, reference)))
            known_at_open = typ == "market" or ((o <= reference if long else o >= reference) if typ == "limit" else (o >= reference if long else o <= reference))
            if (fill <= stop or fill >= target) if long else (fill >= stop or fill <= target):
                output.update(status="invalidated", complete=True, reason="Açılış boşluğu giriş/stop/hedef geometrisini geçti; dolum varsayılmadı.")
                return output
            output.update(filled=True, fill={"price": _str(fill), "bar_open_time_ms": bar["open_time_ms"],
                                            "timing": "open" if known_at_open else "intrabar_unknown"})
            filled_this_bar = True
        if (stop_hit and target_hit) or (filled_this_bar and not known_at_open and (stop_hit or target_hit)):
            output.update(status="ambiguous", complete=True, reason="Aynı mumda giriş/çıkış sırası OHLC ile belirlenemiyor.")
            return output
        if stop_hit or target_hit:
            if stop_hit:
                exit_price = min(o, stop) if long else max(o, stop)
                status = "SL"
            else:
                exit_price = target  # Conservative: no favorable gap benefit on target.
                status = "TP"
            output.update(status=status, complete=True, exit={"price": _str(exit_price), "bar_open_time_ms": bar["open_time_ms"]},
                          pnl=_paper_pnl(plan, fill, exit_price), reason="Önceden kaydedilen ilk hedef/stop üzerinden kâğıt değerlendirme.")
            return output
    complete = bool(available and available[-1]["close_time_ms"] == until)
    output["complete"] = complete
    if complete:
        output.update(status="expired", reason="Plan süresi doldu; TP/SL sonucu yok.")
        if fill is not None:
            last = Decimal(str(available[-1]["close"]))
            output.update(exit={"price": _str(last), "bar_close_time_ms": until, "type": "horizon_mark"},
                          pnl=_paper_pnl(plan, fill, last))
    elif fill is not None:
        output.update(status="open", reason="Kâğıt giriş oluştu; çıkış/ufuk henüz tamamlanmadı.")
    return output


def resolve_record(ledger_path, record_id, future_job, resolved_at=None):
    now = _now_ms() if resolved_at is None else _ms(resolved_at, "resolved_at")
    def event(events):
        matched = [e for e in events if e.get("kind") == "plan" and e["record_id"] == record_id]
        if len(matched) != 1:
            raise WorkflowError("record_id bulunamadı veya benzersiz değil")
        previous = [e for e in events if e.get("kind") == "resolution" and e["record_id"] == record_id]
        if previous and previous[-1]["resolved_at_ms"] >= now:
            raise WorkflowError("çözümleme zamanı önceki gözlemden sonra olmalı")
        result = evaluate_future(matched[0], future_job, resolved_at=now)
        # New observations must extend exactly the same observed candle prefix.
        if previous:
            prior = previous[-1]
            old_count = prior["result"]["future_count"]
            if len(future_job["rows"]) <= old_count or digest(future_job["rows"][:old_count]) != prior["result"]["future_raw_sha256"]:
                raise WorkflowError("yeni çözümleme önceki mumların değişmez devamı olmalı")
            terminal = {"TP", "SL", "ambiguous", "invalidated", "expired", "blocked"}
            if prior["result"]["status"] in terminal and result["status"] != prior["result"]["status"]:
                raise WorkflowError("terminal işlem sonucu değişemez")
        return {"kind": "resolution", "record_id": record_id, "plan_sha256": matched[0]["plan"]["plan_sha256"],
                "resolved_at_ms": now, "clock_source": "system" if resolved_at is None else "declared_test_or_retrospective",
                "result": result}
    return _append(ledger_path, event)


def summarize_ledger(ledger_path):
    with Path(ledger_path).open(encoding="utf-8") as handle:
        events = _read_events(handle)
    plans = {e["record_id"]: e for e in events if e["kind"] == "plan"}
    latest = {e["record_id"]: e for e in events if e["kind"] == "resolution"}
    counts = {}
    for event in latest.values():
        status = event["result"]["status"]
        counts[status] = counts.get(status, 0) + 1
    direction_trials = [e["result"]["direction_outcome"]["correct"] for e in latest.values()
                        if e["result"]["direction_outcome"]["correct"] is not None]
    first_leg_trials = [e["result"]["first_leg_outcome"]["correct"] for e in latest.values()
                        if e["result"].get("first_leg_outcome", {}).get("correct") is not None]
    first_leg_configured = sum(e["plan"].get("first_leg_test") is not None for e in plans.values())
    prospective_latest = [e for ident, e in latest.items()
                          if plans[ident]["prospective_clock_eligible"] and e["clock_source"] == "system"]
    prospective_first = [e["result"]["first_leg_outcome"]["correct"] for e in prospective_latest
                         if e["result"].get("first_leg_outcome", {}).get("correct") is not None]
    scored = counts.get("TP", 0) + counts.get("SL", 0)
    pnl_rows = [e["result"]["pnl"] for e in latest.values() if e["result"].get("pnl")]
    net_known = [Decimal(r["net_R_on_initial_gross_risk"]) for r in pnl_rows if r["net_R_on_initial_gross_risk"] is not None]
    return {"empirical_scope": "all_local_paper_records_including_declared_clock; not_verified_live_accuracy",
            "recorded_plans": len(plans), "observed_plans": len(latest),
            "pending_plans": len(plans) - len(latest), "status_counts": counts,
            "gross_target_hit_rate": counts.get("TP", 0) / scored if scored else None,
            "target_hit_support": scored,
            "net_profitable_trade_rate": sum(v > 0 for v in net_known) / len(net_known) if net_known else None,
            "net_profit_support": len(net_known),
            "net_profit_definition": "positive_net_PnL_among_filled_closed_paper_trades_with_explicit_costs; includes_horizon_marks",
            "trade_support": scored, "trade_coverage": scored / len(plans) if plans else None,
            "direction_accuracy": sum(direction_trials) / len(direction_trials) if direction_trials else None,
            "direction_support": len(direction_trials), "direction_coverage": len(direction_trials) / len(plans) if plans else None,
            "direction_definition": "horizon_close_vs_C0_close; first-leg path accuracy not established",
            "first_leg_accuracy": sum(first_leg_trials) / len(first_leg_trials) if first_leg_trials else None,
            "first_leg_support": len(first_leg_trials), "first_leg_configured_plans": first_leg_configured,
            "first_leg_coverage": len(first_leg_trials) / first_leg_configured if first_leg_configured else None,
            "first_leg_definition": "first_touch_of_preregistered_barriers_from_first_complete_post_record_bar",
            "prospective_system_clock_first_leg_support": len(prospective_first),
            "prospective_system_clock_first_leg_accuracy": sum(prospective_first) / len(prospective_first) if prospective_first else None,
            "filled_paper_trades": sum(e["result"]["filled"] for e in latest.values()),
            "unfilled_expired_plans": sum(e["result"]["status"] == "expired" and not e["result"]["filled"] for e in latest.values()),
            "gross_R_sum": _str(sum((Decimal(r["gross_R"]) for r in pnl_rows), Decimal(0))) if pnl_rows else None,
            "net_R_sum_known_costs": _str(sum(net_known, Decimal(0))) if net_known else None,
            "net_cost_support": len(net_known),
            "prospective_system_clock_records": sum(e["prospective_clock_eligible"] for e in plans.values()),
            "declared_clock_records": sum(not e["prospective_clock_eligible"] for e in plans.values()),
            "limitation_tr": "Yerel kâğıt kayıtlarıdır; dolmayan/iptal/belirsiz işlemler kazanım veya kayıp sayılmaz. "
                             "Yön ölçümü ufuk kapanışıdır; ayrı ilk-bacak testi yalnızca önceden belirlenmiş eşiklerin ilk temasını, kayıt sonrası tam mumlarda ölçer. "
                             "Küçük/seçilmiş ve örtüşen örneklem genellenemez. "
                             "Zaman damgaları/kaynaklar dışarıdan tasdikli değildir; yüksek doğruluk iddiası yok."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "plan", "record", "resolve", "summary"):
        command = sub.add_parser(name)
        if name == "prepare":
            command.add_argument("case_job")
        elif name == "plan":
            command.add_argument("prepared_case")
            command.add_argument("observation")
        else:
            command.add_argument("ledger")
            if name == "record":
                command.add_argument("plan")
            elif name == "resolve":
                command.add_argument("record_id")
                command.add_argument("future_job")
        command.add_argument("--output")
    args = parser.parse_args(argv)
    def read(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        if args.command == "prepare":
            result = prepare(read(args.case_job))
        elif args.command == "plan":
            result = build_plan(read(args.prepared_case), read(args.observation))
        elif args.command == "record":
            result = record_plan(args.ledger, read(args.plan))
        elif args.command == "resolve":
            result = resolve_record(args.ledger, args.record_id, read(args.future_job))
        else:
            result = summarize_ledger(args.ledger)
        content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
        else:
            print(content, end="")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
