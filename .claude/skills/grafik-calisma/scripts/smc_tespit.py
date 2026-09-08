#!/usr/bin/env python3
"""SMC tespit motoru — OHLCV'den yapıyı OTOMATİK çıkarır (göz kararı yok).

Çıkardıkları:
- Swing yüksek/düşükleri (fraktal/pivot: sol-sağ pencere)
- Yapı olayları: BOS (trend devamı) / CHoCH (trend değişimi) + trend durumu
- Order block: kırılım impulsu öncesi son ters mum bölgesi
- FVG: 3-mumluk boşluk (dolu/dolmamış işaretli)
- Likidite: eşit tepe/dip kümeleri (ATR toleransıyla) + swing ekstremleri
- ATR (Wilder) ve rejim: ADX tabanlı trend/range/geçiş + yüksek-vol bayrağı
- HTF verisi verilirse HTF yönü (MTF hizalama için)

Çıktının `confluence_job` alanı DOĞRUDAN confluence.py'ye verilebilir —
böylece seviye tespiti tekrarlanabilir/nesnel olur: aynı veri = aynı seviye.

Girdi JSON: {"input": "ohlcv.csv"} veya {"candles":[{open,high,low,close},...]}
(Crypto.com kline {o,h,l,c} kısaltmaları da kabul). Opsiyonel: "htf_candles"
veya "htf_input" (üst zaman dilimi), "params": {left,right,atr_period,
adx_period, eq_tol_atr, adx_trend, adx_range, vol_esik}.

Determinist — rastgelelik yok. Veri yetersizse alan "VERİ YOK" işaretlenir.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


from candle_contract import TespitError, epoch_ms, normalize_candles


DEFAULTS = {
    "left": 2, "right": 2,
    "atr_period": 14, "adx_period": 14,
    "eq_tol_atr": 0.25,          # eşit tepe/dip toleransı (ATR çarpanı)
    "adx_trend": 25.0, "adx_range": 20.0,   # Wilder konvansiyonu (varsayım)
    "vol_esik": None,            # None → KENDİ tarihinden kalibre (quantile)
    "vol_quantile": 0.90,        # yüksek-vol = ATR% kendi tarihinin üst %10'unda
    "fvg_mitigasyon": 0.5,       # bölgenin kaçı tükenince "dolu" sayılır
                                 # (0.5 = consequent encroachment / orta nokta)
}

# karar_motoru.FVG_MITIGASYON ile AYNI olmak zorunda, yoksa iki motor aynı bölge
# için farklı "açık" der. Eşitliği self_test sınar (elle senkron güvenilmez).
FVG_MITIGASYON = DEFAULTS["fvg_mitigasyon"]

def load_frame(job: dict, key: str = "candles", input_key: str = "input") -> pd.DataFrame:
    if job.get(key) is not None:
        rows = job[key]
    elif job.get(input_key):
        path = Path(job[input_key]).expanduser()
        rows = (json.loads(path.read_text(encoding="utf-8")) if path.suffix.lower() == ".json"
                else pd.read_csv(path).to_dict("records"))
    else:
        raise TespitError(f"'{key}' ya da '{input_key}' gerekli")
    if isinstance(rows, dict):
        rows = rows.get("candles", rows.get("data", rows))
    records, contract = normalize_candles(rows, job)
    df = pd.DataFrame(records)
    if len(df) < 20:
        raise TespitError(f"en az 20 tamamlanmış/uygun mum gerekli (gelen: {len(df)})")
    df.attrs["time_contract"] = contract
    return df


def _wilder(series: pd.Series, period: int) -> pd.Series:
    if period < 1:
        raise TespitError("Wilder periyodu >= 1 olmalı")
    result = pd.Series(np.nan, index=series.index, dtype=float)
    seed, previous = [], None
    for i, value in enumerate(series):
        if not np.isfinite(value):
            seed, previous = [], None
            continue
        if previous is None:
            seed.append(float(value))
            if len(seed) == period:
                previous = float(np.mean(seed))
        else:
            previous = (previous * (period - 1) + float(value)) / period
        if previous is not None:
            result.iloc[i] = previous
    return result


def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return _wilder(tr, period)


def wilder_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = _wilder(tr, period)
    pdi = 100.0 * _wilder(plus_dm, period) / atr.replace(0., np.nan)
    mdi = 100.0 * _wilder(minus_dm, period) / atr.replace(0., np.nan)
    denom = pdi + mdi
    dx = (100.0 * (pdi - mdi).abs() / denom.replace(0., np.nan)).mask(denom == 0., 0.)
    return _wilder(dx, period)


def find_swings(df: pd.DataFrame, left: int = 2, right: int = 2):
    """Fraktal/pivot swingler. i, sol ve sağ penceredeki TÜM değerlerden
    kesin büyükse (high) / küçükse (low) swing'dir."""
    if left < 1 or right < 1:
        raise TespitError("left/right >= 1 olmalı")
    h = df["high"].to_numpy()
    l = df["low"].to_numpy()
    n = len(df)
    highs, lows = [], []
    for i in range(left, n - right):
        if "segment_id" in df and df["segment_id"].iloc[i-left:i+right+1].nunique() != 1:
            continue
        if h[i] > h[i - left:i].max() and h[i] > h[i + 1:i + right + 1].max():
            highs.append({**_point_meta(df, i), "price": float(h[i]), "confirmed": True,
                          "confirmed_i": i+right, "scale": "local_fractal"})
        if l[i] < l[i - left:i].min() and l[i] < l[i + 1:i + right + 1].min():
            lows.append({**_point_meta(df, i), "price": float(l[i]), "confirmed": True,
                         "confirmed_i": i+right, "scale": "local_fractal"})
    return highs, lows


def _point_meta(df, i):
    row = df.iloc[i]
    stamp = row.get("close_time_ms")
    return {"i": int(i), "source_i": int(row.get("source_i", i)),
            "time_ms": int(stamp) if stamp is not None and pd.notna(stamp) else None}


def candidate_swings(df, left=2, right=2):
    """Right-edge turns are candidates only; never supplied to structure_events."""
    result = []
    for i in range(max(left, len(df)-right), len(df)):
        window = df.iloc[i-left:]
        if "segment_id" in window and window.segment_id.nunique() != 1:
            continue
        for side, col, compare in (("high", "high", lambda a, b: a > b),
                                   ("low", "low", lambda a, b: a < b)):
            value = float(df[col].iloc[i])
            other = pd.concat([df[col].iloc[i-left:i], df[col].iloc[i+1:]])
            if all(compare(value, v) for v in other):
                result.append({**_point_meta(df, i), "price": value, "side": side,
                               "confirmed": False, "confirmed_i": None,
                               "scale": "local_fractal"})
    return result


def structure_events(df: pd.DataFrame, highs: list, lows: list, right: int = 2):
    """Swing dizisinden BOS/CHoCH olayları. Bir swing ancak i+right barında
    kesinleşir (ileriye bakış yok). Kapanış son kesin swing high üstüne çıkarsa
    boğa kırılımı (trend ayıysa CHoCH, değilse BOS); tersi ayı kırılımı."""
    c = df["close"].to_numpy()
    sh = sorted(highs, key=lambda s: s["i"])
    sl = sorted(lows, key=lambda s: s["i"])
    hi_idx = lo_idx = 0
    LSH = LSL = None
    trend = "belirsiz"
    events = []
    for i in range(len(df)):
        if i and "segment_id" in df and df.segment_id.iloc[i] != df.segment_id.iloc[i-1]:
            LSH = LSL = None
            trend = "belirsiz"
        while hi_idx < len(sh) and sh[hi_idx]["i"] + right <= i:
            LSH = sh[hi_idx]; hi_idx += 1
        while lo_idx < len(sl) and sl[lo_idx]["i"] + right <= i:
            LSL = sl[lo_idx]; lo_idx += 1
        if LSH is not None and c[i] > LSH["price"]:
            events.append({**_point_meta(df, i), "type": "CHoCH" if trend == "bear" else "BOS",
                           "direction": "bull", "kirilan_seviye": LSH["price"],
                           "confirmed": True, "scale": "local_fractal",
                           "family_id": f"event:{i}", "broken_swing_i": LSH["i"],
                           "impulse_start": (LSL["price"] if LSL else None),
                           "impulse_start_i": (LSL["i"] if LSL else None)})
            trend = "bull"
            LSH = None   # tüketildi; yeni swing high beklenir (tekrar tetikleme yok)
        elif LSL is not None and c[i] < LSL["price"]:
            events.append({**_point_meta(df, i), "type": "CHoCH" if trend == "bull" else "BOS",
                           "direction": "bear", "kirilan_seviye": LSL["price"],
                           "confirmed": True, "scale": "local_fractal",
                           "family_id": f"event:{i}", "broken_swing_i": LSL["i"],
                           "impulse_start": (LSH["price"] if LSH else None),
                           "impulse_start_i": (LSH["i"] if LSH else None)})
            trend = "bear"
            LSL = None
    return trend, events


def _zone_lifecycle(df, low, high, direction, formed_i, threshold=.5):
    after = df.iloc[formed_i+1:]
    bull = direction in ("bull", "demand")
    touch = (after.low <= high) & (after.high >= low)
    penetration = ((high-after.low)/(high-low) if bull else
                   (after.high-low)/(high-low)).clip(0., 1.)
    ratio = float(penetration.max()) if len(after) else 0.
    invalid = (after.close < low) if bull else (after.close > high)
    consumed = ((after.low <= high-(high-low)*threshold) if bull else
                (after.high >= low+(high-low)*threshold))
    def first(mask):
        found = np.flatnonzero(mask.to_numpy())
        return int(formed_i+1+found[0]) if len(found) else None
    invalid_i, consumed_i, touched_i = first(invalid), first(consumed), first(touch)
    tests = int((touch & ~touch.shift(1, fill_value=False)).sum())
    status = ("invalidated" if invalid_i is not None else "consumed" if consumed_i is not None
              else "mitigated" if touched_i is not None else "fresh")
    return {"status": status, "entry_available": status in ("fresh", "mitigated"),
            "fill_ratio": ratio, "fill_status": "filled" if ratio >= 1 else "partial" if ratio > 0 else "fresh",
            "first_touch_i": touched_i, "consumed_i": consumed_i, "invalidated_i": invalid_i,
            "test_count": tests}


def find_order_block(df: pd.DataFrame, ev: dict):
    """Kırılım impulsu içindeki son ters mum = order block."""
    if ev.get("impulse_start_i") is None:
        return None
    o = df["open"].to_numpy(); c = df["close"].to_numpy()
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    lo_i, hi_i = int(ev["impulse_start_i"]), int(ev["i"])
    rng_idx = range(hi_i - 1, lo_i - 1, -1)
    for j in rng_idx:
        opposite = (c[j] < o[j]) if ev["direction"] == "bull" else (c[j] > o[j])
        if opposite:
            side = "demand" if ev["direction"] == "bull" else "supply"
            if h[j] <= l[j]:
                continue
            return {**_point_meta(df, j), "id": f"ob:{hi_i}:{j}", "low": float(l[j]),
                    "high": float(h[j]), "type": side, "formed_i": hi_i,
                    "family_id": ev.get("family_id", f"event:{hi_i}"),
                    **_zone_lifecycle(df, float(l[j]), float(h[j]), side, hi_i)}
    return None


def find_fvgs(df: pd.DataFrame, mitigasyon: float | None = None):
    """3-mum FVG'ler. `dolu` eşiği bölgenin `mitigasyon` oranı kadar tükenmesidir
    (0.5 = consequent encroachment / orta nokta). Giriş fiyatı da orta noktadır
    (karar_motoru.decide: entry = fvg["ce"]), bu yüzden eşik onunla HİZALI olmak
    zorunda: 1.0 (uzak kenar) kullanılırsa girişi çoktan geçilmiş bölge "açık"
    görünür ve confluence FVG kapısı bayat kurulumla açılır (fail-OPEN).

    `mitigasyon=None` ise modül sabiti ÇAĞRI ANINDA okunur — varsayılan argümana
    bağlanırsa çalışma anında sabiti değiştirmek etkisiz kalır (karar_motoru
    sabiti çağrı anında okuyor; iki motor asimetrik davranmamalı)."""
    mitigasyon = FVG_MITIGASYON if mitigasyon is None else mitigasyon
    if not np.isfinite(mitigasyon) or not 0 <= mitigasyon <= 1:
        raise TespitError("FVG mitigasyon 0–1 aralığında olmalı")
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    out = []
    n = len(df)
    for i in range(2, n):
        if "segment_id" in df and df.segment_id.iloc[i-2:i+1].nunique() != 1:
            continue
        if l[i] > h[i - 2]:
            zone_lo, zone_hi = float(h[i - 2]), float(l[i])
            esik = zone_hi - (zone_hi - zone_lo) * mitigasyon
            dolu = bool(l[i + 1:].min() <= esik) if i + 1 < n else False
            out.append({**_point_meta(df, i), "id": f"fvg:{i}:bull", "type": "bull",
                        "low": zone_lo, "high": zone_hi, "dolu": dolu,
                        **_zone_lifecycle(df, zone_lo, zone_hi, "bull", i, mitigasyon)})
        elif h[i] < l[i - 2]:
            zone_lo, zone_hi = float(h[i]), float(l[i - 2])
            esik = zone_lo + (zone_hi - zone_lo) * mitigasyon
            dolu = bool(h[i + 1:].max() >= esik) if i + 1 < n else False
            out.append({**_point_meta(df, i), "id": f"fvg:{i}:bear", "type": "bear",
                        "low": zone_lo, "high": zone_hi, "dolu": dolu,
                        **_zone_lifecycle(df, zone_lo, zone_hi, "bear", i, mitigasyon)})
    return out


def find_liquidity(highs: list, lows: list, tol: float, df=None):
    """Timestamped liquidity zones; active status requires subsequent wick checks.

    Cluster diameter is bounded by tol (no single-link chaining). Its outer
    boundary, rather than an unobserved average price, is the target level.
    """
    if not np.isfinite(tol) or tol < 0:
        raise TespitError("likidite toleransı negatif/sonlu olmayan sayı olamaz")
    pools = []
    for swings, side in ((highs, "buyside"), (lows, "sellside")):
        groups = []
        for swing in sorted(swings, key=lambda s: s["price"]):
            if groups and swing["price"] - groups[-1][0]["price"] <= tol:
                groups[-1].append(swing)
            else:
                groups.append([swing])
        for group in groups:
            low, high = min(s["price"] for s in group), max(s["price"] for s in group)
            anchor = max(group, key=lambda s: s["i"])
            formed_i = max(s.get("confirmed_i", s["i"] + 2) for s in group)
            price = high if side == "buyside" else low
            swept_i = None
            if df is not None:
                tail = df.iloc[anchor["i"]+1:]
                hits = (tail.high >= price) if side == "buyside" else (tail.low <= price)
                positions = np.flatnonzero(hits.to_numpy())
                if len(positions):
                    swept_i = int(anchor["i"] + 1 + positions[0])
            pools.append({"id": f"liquidity:{side}:{anchor['i']}", "price": float(price),
                          "low": float(low), "high": float(high), "type": side,
                          "kind": ("esit-tepe" if side == "buyside" else "esit-dip")
                                  if len(group) >= 2 else "swing-ekstrem",
                          "count": len(group), "anchor_indices": [s["i"] for s in group],
                          "anchor_source_indices": [s.get("source_i", s["i"]) for s in group],
                          "formed_i": formed_i, "source_i": anchor.get("source_i", anchor["i"]),
                          "time_ms": anchor.get("time_ms"), "swept_i": swept_i,
                          "swept_time_ms": _point_meta(df, swept_i)["time_ms"] if swept_i is not None else None,
                          "status": ("unverified" if df is None else
                                     "swept" if swept_i is not None else "open")})
    return pools

def detect(job: dict) -> dict:
    p = {**DEFAULTS, **(job.get("params") or {})}
    df = load_frame(job)
    n = len(df)
    time_contract = df.attrs["time_contract"]

    atr_s = wilder_atr(df, int(p["atr_period"]))
    atr = float(atr_s.iloc[-1]) if np.isfinite(atr_s.iloc[-1]) else None
    close_last = float(df["close"].iloc[-1])

    adx_s = wilder_adx(df, int(p["adx_period"]))
    adx = float(adx_s.iloc[-1]) if np.isfinite(adx_s.iloc[-1]) else None
    if adx is None:
        durum = "VERİ YOK"
    elif adx >= p["adx_trend"]:
        durum = "trend"
    elif adx < p["adx_range"]:
        durum = "range"
    else:
        durum = "gecis"

    # Yüksek-vol eşiği: sabit % değil, KENDİ tarihinin quantile'ı (veri-türevi).
    # Kullanıcı vol_esik verirse o kullanılır (varsayım olarak etiketlenir).
    atr_pct_s = (atr_s / df["close"]).replace([np.inf, -np.inf], np.nan).dropna()
    if p["vol_esik"] is not None:
        vol_esik = float(p["vol_esik"])
        vol_kaynak = f"kullanıcı sabiti {vol_esik} (varsayım)"
    elif len(atr_pct_s) >= 5:
        vol_esik = float(np.quantile(atr_pct_s.to_numpy(),
                                     float(p["vol_quantile"])))
        vol_kaynak = (f"veri-türevi: ATR% tarihinin q{p['vol_quantile']} "
                      f"= {round(vol_esik, 5)}")
    else:
        vol_esik = None
        vol_kaynak = "VERİ YOK (ATR% serisi kısa)"
    atr_pct_last = (atr / close_last) if atr else None
    yuksek_vol = bool(atr_pct_last is not None and vol_esik is not None
                      and atr_pct_last > vol_esik)
    regime = {"adx": round(adx, 2) if adx is not None else None,
              "durum": durum, "yuksek_vol": yuksek_vol,
              "atr_pct": round(atr_pct_last, 5) if atr_pct_last else None,
              "vol_esik": round(vol_esik, 5) if vol_esik is not None else None,
              "vol_esik_kaynagi": vol_kaynak}

    highs, lows = find_swings(df, int(p["left"]), int(p["right"]))
    trend, events = structure_events(df, highs, lows, int(p["right"]))

    obs_all = []
    for ev in events:
        ob = find_order_block(df, ev)
        if ob:
            obs_all.append(ob)
    obs = [ob for ob in obs_all if ob["entry_available"]]
    fvgs = find_fvgs(df, float(p["fvg_mitigasyon"]))
    for fvg in fvgs:
        related = [ev for ev in events if ev.get("impulse_start_i") is not None
                   and ev["impulse_start_i"] <= fvg["i"]-1 <= ev["i"]+1
                   and ev["direction"] == fvg["type"]]
        fvg["family_id"] = related[-1]["family_id"] if related else f"gap:{fvg['i']}"
    acik_fvgs = [f for f in fvgs if not f["dolu"] and f["entry_available"]]

    # ATR yoksa (kısa/NaN seri) eşit tepe/dip toleransı gizli 0.001×close'a düşer;
    # bu fallback varsayımlara ETİKETLENİR (B5): etiketsiz gizli eşik yasak.
    atr_tol_fallback = not (atr and atr > 0)
    tol = (0.001 * close_last) if atr_tol_fallback else (p["eq_tol_atr"] * atr)
    liq_all = find_liquidity(highs, lows, tol, df)
    liq = [q for q in liq_all if q["status"] == "open"]

    # HTF (MTF hizalama): verilirse aynı yapı mantığıyla HTF trendi
    htf_bias = None
    htf_info = None
    if job.get("htf_candles") is not None or job.get("htf_input"):
        hjob = dict(job)
        if time_contract.get("c0_time_ms") is not None:
            for alias in ("cutoff", "c0", "as_of"):
                hjob.pop(alias, None)
            hjob["cutoff"] = time_contract["c0_time_ms"]
        hjob.pop("interval_seconds", None)
        hjob.pop("timeframe", None)
        if job.get("htf_timeframe"):
            hjob["timeframe"] = job["htf_timeframe"]
        if job.get("htf_interval_seconds"):
            hjob["interval_seconds"] = job["htf_interval_seconds"]
        hdf = load_frame(hjob, key="htf_candles", input_key="htf_input")
        hh, hl = find_swings(hdf, int(p["left"]), int(p["right"]))
        htrend, hevents = structure_events(hdf, hh, hl, int(p["right"]))
        htf_bias = htrend if htrend in ("bull", "bear") else None
        htf_info = {"trend": htrend, "olay_sayisi": len(hevents),
                    "time_contract": hdf.attrs["time_contract"]}
        base_interval = time_contract.get("interval_ms")
        high_interval = hdf.attrs["time_contract"].get("interval_ms")
        htf_info["higher_timeframe_verified"] = bool(base_interval and high_interval and
                                                    high_interval > base_interval)
        if not htf_info["higher_timeframe_verified"]:
            htf_info["warning"] = "üst zaman dilimi süresi doğrulanmadı"

    # confluence.py için hazır girdi (son olaydan)
    confluence_job = None
    lifecycle = {"status": "unconfirmed", "first_target": None}
    if events:
        last = events[-1]
        if last.get("impulse_start") is not None:
            b = int(last["i"])
            if last["direction"] == "bull":
                imp_end = float(df["high"].iloc[b:].max())
            else:
                imp_end = float(df["low"].iloc[b:].min())
            past = df.iloc[:b+1]
            known_h = [s for s in highs if s["confirmed_i"] <= b]
            known_l = [s for s in lows if s["confirmed_i"] <= b]
            event_atr = atr_s.iloc[b]
            event_tol = (p["eq_tol_atr"] * float(event_atr) if np.isfinite(event_atr) and event_atr > 0
                         else .001 * abs(float(past.close.iloc[-1])))
            original_pools = find_liquidity(known_h, known_l, event_tol, past)
            eligible = [q for q in original_pools if q["status"] == "open" and
                        ((last["direction"] == "bull" and q["type"] == "buyside" and q["price"] > past.close.iloc[-1]) or
                         (last["direction"] == "bear" and q["type"] == "sellside" and q["price"] < past.close.iloc[-1]))]
            eligible.sort(key=lambda q: abs(q["price"]-past.close.iloc[-1]))
            first_target = eligible[0]["price"] if eligible else None
            after = df.iloc[b+1:]
            paid = first_target is not None and bool(((after.high >= first_target) if last["direction"] == "bull"
                                                     else (after.low <= first_target)).any())
            invalid = bool(((after.close < last["impulse_start"]) if last["direction"] == "bull"
                            else (after.close > last["impulse_start"])).any())
            age = n-1-b
            lifecycle = {"status": "invalidated" if invalid else "completed" if paid else "active",
                         "first_target": first_target, "target_paid": paid, "event_i": b,
                         "age_bars": age, "fresh_structure": age <= 3,
                         "first_target_status": "unknown" if first_target is None else "taken" if paid else "open"}
            confluence_job = {
                "structure": {"event": last["type"], "direction": last["direction"],
                              "confirmed": True, "age_bars": age, "i": b,
                              "source_i": last["source_i"], "time_ms": last["time_ms"],
                              "scale": "local_fractal", "family_id": last["family_id"]},
                "impulse": {"start": float(last["impulse_start"]), "end": imp_end},
                "order_blocks": obs,
                "fvgs": acik_fvgs,
                "liquidity": liq,
                "regime": {"durum": durum, "yuksek_vol": yuksek_vol},
                "time_contract": {k: v for k, v in time_contract.items()
                                  if k not in ("excluded", "input_rows")},
                "setup_lifecycle": lifecycle, "current_price": close_last,
                "confirmation": job.get("confirmation"),
                "c0_i": n-1,
                "recent_candles": [{**row, "i": i} for i, row in enumerate(
                    df.where(pd.notna(df), None).to_dict("records")) if i >= n-4],
            }
            if atr is not None:
                confluence_job["atr"] = round(atr, 8)
            if htf_bias:
                confluence_job["htf_bias"] = htf_bias
                confluence_job["htf_verified"] = bool(htf_info["higher_timeframe_verified"] and
                    htf_info["time_contract"]["status"] == "verified")
            # KALİBRASYON KÖPRÜSÜ (Y2): kalibre edilmiş eşikler (min_rr vb.) buradan
            # confluence'a KODLA akar — eskiden confluence_job'da 'thresholds' hiç yoktu,
            # bu yüzden confluence her koşuda varsayılan min_rr=2.0 kullanıyordu ("dinamik
            # eşik" anlatısı çıktıyı etkilemeyen ölü koddu). Job 'confluence_thresholds'
            # taşırsa (kalibrasyon.py ya da çağıran) olduğu gibi geçir; kaynağı da işaretle.
            ct = job.get("confluence_thresholds") or job.get("thresholds")
            if ct:
                confluence_job["thresholds"] = ct
                confluence_job["thresholds_kaynak"] = job.get(
                    "thresholds_kaynak", "smc_tespit → confluence köprüsü (job'dan aktarıldı)")

    return {
        "bar_sayisi": n,
        "trend": trend,
        "structure_context": {"direction": trend, "scale": "local_fractal",
                              "external_direction": None,
                              "note": "Yerel fraktal yapı; dış yapı veya C0 sonrası ilk bacak yönü değildir."},
        "first_leg": {"direction": None, "status": "unconfirmed",
                      "reason": "Yerel yapı tek başına sonraki fiyat bacağını doğrulamaz."},
        "time_contract": time_contract,
        "normalized_candles": df.where(pd.notna(df), None).to_dict("records"),
        "swings": {"highs": highs, "lows": lows,
                   "candidates": candidate_swings(df, int(p["left"]), int(p["right"]))},
        "setup_lifecycle": lifecycle,
        "olaylar": events[-10:],
        "swing_sayisi": {"high": len(highs), "low": len(lows)},
        "order_blocks": obs,
        "order_blocks_all": obs_all,
        "acik_fvgler": acik_fvgs,
        "fvgler_all": fvgs,
        "likidite": liq,
        "liquidity_all": liq_all,
        "atr": round(atr, 8) if atr is not None else "VERİ YOK",
        "rejim": regime,
        "htf": htf_info,
        "confluence_job": confluence_job,
        "varsayimlar": [
            f"swing pencere left/right={p['left']}/{p['right']} (fraktal granülarite; varsayım)",
            f"ATR/ADX periyodu={p['atr_period']}/{p['adx_period']} (Wilder konvansiyonu)",
            f"ADX trend/range eşiği={p['adx_trend']}/{p['adx_range']} (Wilder konvansiyonu; "
            "params ile ezilebilir)",
            (f"eşit tepe/dip toleransı=0.001×close (ATR hesaplanamadı — ETİKETLİ "
             "fallback varsayım)" if atr_tol_fallback else
             f"eşit tepe/dip toleransı={p['eq_tol_atr']}×ATR (varsayım)"),
            f"yüksek-vol eşiği: {vol_kaynak}",
            "OB CE=%50 tüketim ve taze yapı=son 0–3 mum tasarım varsayımlarıdır; piyasa üstünlüğü kanıtı değildir.",
            (f"FVG mitigasyon eşiği={p['fvg_mitigasyon']} — KALİBRE EDİLMEMİŞ "
             "tasarım varsayımı (consequent encroachment konvansiyonu; edge kanıtı "
             "DEĞİL). Girişin de bölge orta noktası olmasıyla hizalıdır. "
             "1.0=uzak kenar (eski), 0.0=ilk dokunuş; params ile ezilebilir"),
        ],
        "not": ("Tespitler algoritmiktir (aynı veri = aynı seviye). SMC kavramları "
                "yorumsal bir çerçevedir; tespit nesnelliği doğruluk garantisi değildir."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="SMC tespit motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(detect(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
