#!/usr/bin/env python3
"""Confluence motoru — yön + giriş/çıkış seviyesi hesaplama.

Fibonacci TEK BAŞINA yeterli değildir. Bu motor giriş bölgesini KATMAN
sırasına göre üretir:

    Bağlam(HTF) → yapı(SMC) → arz-talep(OB/FVG) → likidite → [fib] → onay → risk

Kural: güçlü giriş bölgesi = golden zone (0.618–0.786) + order block/FVG +
likidite AYNI noktada buluştuğunda (confluence). Yalnız fib → confluence
eksik → NÖTR-BEKLE (fail-closed).

Girdi JSON:
{
  "structure": {"event": "CHoCH"|"BOS", "direction": "bull"|"bear"},
  "impulse":   {"start": 100.0, "end": 120.0},   # start→end = impuls bacağı
  "htf_bias":  "bull"|"bear"|null,                # üst zaman dilimi yönü (ops.)
  "order_blocks": [{"low":104,"high":106,"type":"demand"}],   # demand|supply
  "fvgs":         [{"low":104.5,"high":105.5,"type":"bull"}], # bull|bear
  "liquidity":    [{"price":125,"type":"buyside"},{"price":95,"type":"sellside"}],
  "atr": 1.8,                                     # ops. ATR → SL tamponu volatilite-uyarlı
  "regime": {"durum":"trend","yuksek_vol":false}, # ops. rejim filtresi (smc_tespit üretir)
  "thresholds": {"min_confluence":0.5,"min_rr":2.0,"sl_buffer_frac":0.05,
                 "atr_mult":1.0,"high_vol_rr_add":0.5}
}

Ek kapılar: htf_bias işlem yönüyle ÇELİŞİYORSA → BEKLE (MTF hizasızlık);
rejim "range" iken BOS (devam) kurulumu → BEKLE; yüksek-vol'da gereken R:R
high_vol_rr_add kadar artar. ATR verilirse SL tamponu = atr_mult*ATR
(yoksa eski sl_buffer_frac*range).

Determinist — rastgelelik yok. Uydurma yok: seviyeler yalnız verilen
girdiden hesaplanır; eksik girdi kararı BEKLE'ye çeker (fail-closed).
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

# Golden zone (OTE) sınırları
GZ_LO, GZ_HI = 0.618, 0.786

# Confluence ağırlıkları (toplam 1.0)
W = {"structure": 0.30, "htf": 0.15, "ob": 0.25, "fvg": 0.15, "liquidity": 0.15}


class ConfluenceError(Exception):
    pass


def _overlap(a, b):
    """İki [lo,hi] aralığının kesişimi; yoksa None."""
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return [lo, hi] if lo <= hi else None


def _golden_zone(start: float, end: float):
    """İmpuls bacağından golden zone [lo, hi] (yönden bağımsız fiyat aralığı)."""
    rng = abs(end - start)
    if rng <= 0:
        raise ConfluenceError("impuls bacağı sıfır uzunlukta (start==end)")
    if end > start:            # yukarı impuls → long retracement (end'in altı)
        return [end - GZ_HI * rng, end - GZ_LO * rng], rng, "up"
    else:                      # aşağı impuls → short retracement (end'in üstü)
        return [end + GZ_LO * rng, end + GZ_HI * rng], rng, "down"


def _number(value, name):
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ConfluenceError(f"{name} sayısal olmalı") from exc
    if not math.isfinite(number):
        raise ConfluenceError(f"{name} sonlu olmalı")
    return number


def _price(value, name):
    price = _number(value, name)
    if price <= 0:
        raise ConfluenceError(f"{name}: futures fiyatı pozitif olmalı")
    return price


def _candidate_score(zones, st, htf, has_target):
    # Contributions from one causal event family are capped at the largest
    # contribution in that family. Unknown family labels are explicit assumptions.
    votes = {}
    factors = []
    def vote(family, weight, description):
        votes[family] = max(votes.get(family, 0.), weight)
        factors.append(description)
    vote(st.get("family_id") or "unverified:structure", W["structure"],
         "yapı(SMC): " + str(st["event"]).upper() + "/" + st["direction"])
    if htf == st["direction"]:
        vote("htf", W["htf"], "HTF bias hizalı")
    for kind in ("ob", "fvg"):
        hits = [z for z in zones if z["kind"] == kind]
        if hits:
            # Repeated blocks of the same type do not create extra votes.
            distinct = [z for z in hits if z.get("family_id") not in votes]
            selected = (distinct or hits)[0]
            vote(selected.get("family_id") or "unverified:" + kind, W[kind],
                 "order block çakışması" if kind == "ob" else "FVG çakışması")
    if has_target:
        vote("liquidity", W["liquidity"], "açık likidite hedefi var")
    return round(min(sum(votes.values()), 1.), 4), factors, votes


def synth(job: dict) -> dict:
    st = dict(job.get("structure") or {})
    event = str(st.get("event", "")).upper()
    sdir = str(st.get("direction", "")).lower()
    if event not in {"CHOCH", "BOS"} or sdir not in {"bull", "bear"}:
        raise ConfluenceError("structure.event CHoCH|BOS ve direction bull|bear olmalı")
    st.update(event=event, direction=sdir)
    imp = job.get("impulse") or {}
    start, end = (_price(imp.get(k), "impulse." + k) for k in ("start", "end"))
    th = job.get("thresholds") or {}
    min_conf = _number(th.get("min_confluence", .5), "min_confluence")
    min_rr = _number(th.get("min_rr", 2.), "min_rr")
    sl_frac = _number(th.get("sl_buffer_frac", .05), "sl_buffer_frac")
    atr_mult = _number(th.get("atr_mult", 1.), "atr_mult")
    hv_add = _number(th.get("high_vol_rr_add", .5), "high_vol_rr_add")
    if not 0 <= min_conf <= 1 or min_rr <= 0 or min(sl_frac, atr_mult, hv_add) < 0:
        raise ConfluenceError("eşik aralıkları geçersiz")
    atr = _number(job["atr"], "atr") if job.get("atr") is not None else None
    if atr is not None and atr <= 0:
        raise ConfluenceError("ATR pozitif olmalı")
    regime = job.get("regime") or {}
    if isinstance(regime, str):
        regime = {"durum": regime}
    regime_name = str(regime.get("durum", "")).lower() or None
    high_vol = bool(regime.get("yuksek_vol", False))
    htf = str(job.get("htf_bias") or "").lower() or None
    gz, rng, impulse_direction = _golden_zone(start, end)
    is_long = sdir == "bull"
    hard_gates, draft_gates = [], []
    if impulse_direction != ("up" if is_long else "down"):
        hard_gates.append(f"yapı({sdir}) ile impuls({impulse_direction}) çelişiyor")
    if htf in ("bull", "bear") and htf != sdir:
        hard_gates.append(f"HTF bias ({htf}) işlem yönüyle ({sdir}) çelişiyor — MTF hizasızlık")
    if htf and job.get("htf_verified") is False:
        draft_gates.append("HTF zaman/süre eşleşmesi doğrulanmadı")
    if regime_name == "range" and event == "BOS":
        hard_gates.append("range rejiminde devam (BOS) kurulumu — rejim filtresi")

    zones = []
    rejected_states = {"invalidated", "consumed", "filled", "swept"}
    for key, kind, want in (("order_blocks", "ob", "demand" if is_long else "supply"),
                            ("fvgs", "fvg", sdir)):
        for index, original in enumerate(job.get(key) or []):
            if str(original.get("type", "")).lower() != want:
                continue
            if (original.get("status") in rejected_states or original.get("dolu") or
                    original.get("entry_available") is False):
                continue
            low = _price(original.get("low"), key + ".low")
            high = _price(original.get("high"), key + ".high")
            if low >= high:
                raise ConfluenceError("bölge low < high olmalı")
            overlap = _overlap(gz, [low, high])
            if overlap and overlap[0] < overlap[1]:
                zones.append({**original, "kind": kind, "interval": overlap,
                              "id": original.get("id", f"{kind}:{index}")})
    targets = []
    current = _price(job["current_price"], "current_price") if job.get("current_price") is not None else None
    for pool in job.get("liquidity") or []:
        if pool.get("status") != "open":
            continue
        price = _price(pool.get("price"), "liquidity.price")
        if ((is_long and pool.get("type") == "buyside" and price > max(gz[1], current if current is not None else gz[1])) or
                (not is_long and pool.get("type") == "sellside" and price < min(gz[0], current if current is not None else gz[0]))):
            targets.append(price)
    targets = sorted(set(targets), reverse=not is_long)
    if not targets:
        hard_gates.append("doğrulanmış açık likidite hedefi yok; hedef varsayılmaz")

    # Partition the union by every boundary; each candidate retains exactly the
    # zones that cover it. No vote from a disjoint region reaches this entry.
    boundaries = sorted({x for z in zones for x in z["interval"]})
    candidates = []
    for low, high in zip(boundaries, boundaries[1:]):
        covered = [z for z in zones if z["interval"][0] <= low and z["interval"][1] >= high]
        if covered and high > low:
            candidates.append({"entry": [low, high], "zones": covered})
    if not candidates:
        candidates = [{"entry": gz[:], "zones": []}]
    buf = atr_mult * atr if atr is not None else sl_frac * rng
    for candidate in candidates:
        entry = candidate["entry"]
        mid = sum(entry)/2
        # Structural invalidation uses only this candidate's evidence.
        ref = (min([start] + [z["low"] for z in candidate["zones"]]) if is_long else
               max([start] + [z["high"] for z in candidate["zones"]]))
        stop = ref - buf if is_long else ref + buf
        risk = mid-stop if is_long else stop-mid
        reward = (targets[0]-mid if is_long else mid-targets[0]) if targets else None
        price_geometry = (all(math.isfinite(x) and x > 0 for x in (mid, stop, *entry))
                          and risk > 0 and (stop < entry[0] if is_long else stop > entry[1]))
        rr = reward/risk if reward is not None and price_geometry else None
        score, factors, votes = _candidate_score(candidate["zones"], st, htf, bool(targets))
        candidate.update(mid=mid, stop=stop, rr=rr, score=score, factors=factors, votes=votes,
                         price_geometry_valid=price_geometry)
    valid_candidates = [c for c in candidates if c["price_geometry_valid"]]
    if not valid_candidates:
        raise ConfluenceError("türetilen giriş/stop geometrisi geçersiz; futures fiyatları pozitif ve sıralı olmalı")
    selected = max(valid_candidates, key=lambda c: (c["score"], c["rr"] or -1.,
                                              c["entry"][1]-c["entry"][0]))
    entry, mid = selected["entry"], selected["mid"]
    score, factors = selected["score"], selected["factors"]
    rr = round(selected["rr"], 3) if selected["rr"] is not None else None
    if regime_name == "trend":
        factors.append("rejim: trend")
    if not selected["zones"]:
        hard_gates.append("confluence eksik: golden zone hiçbir aktif OB/FVG ile çakışmıyor (yalnız fib)")
    if any(z.get("status") not in ("fresh", "mitigated") for z in selected["zones"]):
        draft_gates.append("bölge yaşam döngüsü doğrulanmadı")
    if score < min_conf:
        hard_gates.append(f"confluence skoru {score:.2f} < {min_conf}")
    min_rr_eff = min_rr + (hv_add if high_vol else 0.)
    if selected["rr"] is not None and selected["rr"] < min_rr_eff:
        hard_gates.append(f"R:R {rr:.2f} < {min_rr_eff}" + (" (yüksek-vol: eşik artırıldı)" if high_vol else ""))
    if job.get("time_contract", {}).get("status") != "verified":
        draft_gates.append("C0 ve tamamlanmış mum zamanı doğrulanmadı (time_unverified)")
    age = st.get("age_bars")
    if st.get("confirmed") is not True or not isinstance(age, (int, float)) or not math.isfinite(age) or age < 0:
        draft_gates.append("yapı kapanışı ve olay yaşı doğrulanmadı")
    lifecycle = job.get("setup_lifecycle") or {}
    if lifecycle.get("status") in ("completed", "invalidated", "consumed"):
        hard_gates.append("kurulum hedefini üretmiş veya geçersizleşmiş")
    elif lifecycle.get("status") != "active":
        draft_gates.append("kurulum yaşam döngüsü doğrulanmadı")

    confirmation = job.get("confirmation") or {}
    if not confirmation:
        for candle in reversed(job.get("recent_candles") or []):
            touched = candle["low"] <= entry[1] and candle["high"] >= entry[0]
            rejected = (candle["close"] > entry[1] and candle["close"] > candle["open"]) if is_long else (
                        candle["close"] < entry[0] and candle["close"] < candle["open"])
            candle_age = job.get("c0_i", candle["i"]) - candle["i"]
            if touched and rejected and 0 <= candle_age <= 3 and candle["i"] >= st.get("i", 0):
                confirmation = {"confirmed": True, "direction": sdir, "age_bars": candle_age,
                                "level": max(entry[0], min(entry[1], candle["low"] if is_long else candle["high"])),
                                "kind": "rejection", "i": candle["i"], "source_i": candle.get("source_i")}
                break
    level = confirmation.get("level")
    confirm_age = confirmation.get("age_bars")
    confirmed = (confirmation.get("confirmed") is True and confirmation.get("direction") == sdir
                 and isinstance(confirm_age, (int, float)) and 0 <= confirm_age <= 3
                 and isinstance(level, (int, float)) and math.isfinite(level)
                 and entry[0] <= level <= entry[1])
    if confirmation.get("i") is not None and job.get("c0_i") is not None:
        confirmed = confirmed and (job["c0_i"]-confirmation["i"] == confirm_age
                                   and confirmation["i"] >= st.get("i", 0))
    if not confirmed:
        draft_gates.append("seçilen girişte taze kapanış/rejection onayı yok")
    gates = hard_gates + draft_gates
    executable = not gates
    direction = "LONG" if is_long else "SHORT"
    return {
        "KARAR": direction if executable else "NÖTR-BEKLE",
        "plan_yonu": direction, "plan_durumu": "ONAYLI" if executable else "ENGELLENDI" if hard_gates else "TASLAK",
        "executable": executable, "yon_bias": sdir,
        "structure_context": {"direction": sdir, "scale": st.get("scale", "unverified"),
                              "external_direction": None},
        "first_leg": {"direction": None, "status": "unconfirmed",
                      "reason": "Koşullu giriş planı, C0 sonrası ilk bacak tahmini değildir."},
        "confluence_skoru": score, "confluence_faktorleri": factors,
        "evidence_family_votes": selected["votes"],
        # Prices retain calculation precision. Fixed decimal rounding can turn
        # valid small-token prices into zero or collapse stop/entry boundaries.
        "golden_zone": gz,
        "giris_bolgesi": entry, "giris_orta": mid,
        "gecersizlik_sl": selected["stop"],
        "hedefler": targets[:2], "rr": rr,
        "entry_evidence_ids": [z["id"] for z in selected["zones"]],
        "entry_candidates": [{"entry": c["entry"], "score": c["score"], "rr": c["rr"],
                              "price_geometry_valid": c["price_geometry_valid"],
                              "evidence_ids": [z["id"] for z in c["zones"]]} for c in candidates],
        "confirmation": confirmation, "time_contract": job.get("time_contract") or {"status": "time_unverified"},
        "fresh_trigger": confirmed,
        "setup_lifecycle": lifecycle, "atr_kullanildi": atr, "rejim": regime_name,
        "esik_kaynagi": str(job.get("thresholds_kaynak") or "varsayılan eşikler (varsayım — kalibre edilmemiş)"),
        "kapi_gerekceleri": gates, "taslak_gerekceleri": draft_gates,
        "katman_sirasi": "bağlam→yapı→arz-talep→likidite→fib→onay→risk",
        "not": "Koşullu karar desteği; plan yönü dış yapı veya ilk gelecek bacak yönü değildir. Canlı emir içermez.",
    }

def main() -> int:
    ap = argparse.ArgumentParser(description="Confluence giriş/çıkış motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(synth(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
