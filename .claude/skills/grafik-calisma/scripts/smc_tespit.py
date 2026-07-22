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


class TespitError(Exception):
    pass


DEFAULTS = {
    "left": 2, "right": 2,
    "atr_period": 14, "adx_period": 14,
    "eq_tol_atr": 0.25,          # eşit tepe/dip toleransı (ATR çarpanı)
    "adx_trend": 25.0, "adx_range": 20.0,   # Wilder konvansiyonu (varsayım)
    "vol_esik": None,            # None → KENDİ tarihinden kalibre (quantile)
    "vol_quantile": 0.90,        # yüksek-vol = ATR% kendi tarihinin üst %10'unda
}

_KEYMAP = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
           "open": "open", "high": "high", "low": "low", "close": "close",
           "volume": "volume"}


def load_frame(job: dict, key: str = "candles", input_key: str = "input") -> pd.DataFrame:
    if job.get(key) is not None:
        rows = []
        for c in job[key]:
            row = {}
            for k, v in dict(c).items():
                kk = _KEYMAP.get(str(k).strip().lower())
                if kk:
                    row[kk] = float(v)
            rows.append(row)
        df = pd.DataFrame(rows)
    elif job.get(input_key):
        p = Path(job[input_key]).expanduser()
        if p.suffix.lower() == ".json":
            df = pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))
        else:
            df = pd.read_csv(p)
        df.columns = [str(c).strip().lower() for c in df.columns]
        df = df.rename(columns={k: v for k, v in _KEYMAP.items() if k in df.columns})
    else:
        raise TespitError(f"'{key}' ya da '{input_key}' gerekli")
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise TespitError(f"'{col}' kolonu yok")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    if len(df) < 20:
        raise TespitError(f"en az 20 mum gerekli (gelen: {len(df)})")
    return df


def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def wilder_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    alpha = 1.0 / period
    atr = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    pdi = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr
    mdi = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr
    denom = (pdi + mdi).replace(0.0, np.nan)
    dx = 100.0 * (pdi - mdi).abs() / denom
    return dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean()


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
        if h[i] > h[i - left:i].max() and h[i] > h[i + 1:i + right + 1].max():
            highs.append({"i": int(i), "price": float(h[i])})
        if l[i] < l[i - left:i].min() and l[i] < l[i + 1:i + right + 1].min():
            lows.append({"i": int(i), "price": float(l[i])})
    return highs, lows


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
        while hi_idx < len(sh) and sh[hi_idx]["i"] + right <= i:
            LSH = sh[hi_idx]; hi_idx += 1
        while lo_idx < len(sl) and sl[lo_idx]["i"] + right <= i:
            LSL = sl[lo_idx]; lo_idx += 1
        if LSH is not None and c[i] > LSH["price"]:
            events.append({"i": int(i), "type": "CHoCH" if trend == "bear" else "BOS",
                           "direction": "bull", "kirilan_seviye": LSH["price"],
                           "impulse_start": (LSL["price"] if LSL else None),
                           "impulse_start_i": (LSL["i"] if LSL else None)})
            trend = "bull"
            LSH = None   # tüketildi; yeni swing high beklenir (tekrar tetikleme yok)
        elif LSL is not None and c[i] < LSL["price"]:
            events.append({"i": int(i), "type": "CHoCH" if trend == "bull" else "BOS",
                           "direction": "bear", "kirilan_seviye": LSL["price"],
                           "impulse_start": (LSH["price"] if LSH else None),
                           "impulse_start_i": (LSH["i"] if LSH else None)})
            trend = "bear"
            LSL = None
    return trend, events


def find_order_block(df: pd.DataFrame, ev: dict):
    """Kırılım impulsu içindeki son ters mum = order block."""
    if ev.get("impulse_start_i") is None:
        return None
    o = df["open"].to_numpy(); c = df["close"].to_numpy()
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    lo_i, hi_i = int(ev["impulse_start_i"]), int(ev["i"])
    rng_idx = range(hi_i - 1, lo_i - 1, -1)
    if ev["direction"] == "bull":     # son ayı mumu → demand
        for j in rng_idx:
            if c[j] < o[j]:
                return {"low": float(l[j]), "high": float(h[j]), "type": "demand", "i": int(j)}
    else:                              # son boğa mumu → supply
        for j in rng_idx:
            if c[j] > o[j]:
                return {"low": float(l[j]), "high": float(h[j]), "type": "supply", "i": int(j)}
    return None


def find_fvgs(df: pd.DataFrame):
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    out = []
    n = len(df)
    for i in range(2, n):
        if l[i] > h[i - 2]:
            zone_lo, zone_hi = float(h[i - 2]), float(l[i])
            dolu = bool(l[i + 1:].min() <= zone_lo) if i + 1 < n else False
            out.append({"i": int(i), "type": "bull", "low": zone_lo, "high": zone_hi, "dolu": dolu})
        elif h[i] < l[i - 2]:
            zone_lo, zone_hi = float(h[i]), float(l[i - 2])
            dolu = bool(h[i + 1:].max() >= zone_hi) if i + 1 < n else False
            out.append({"i": int(i), "type": "bear", "low": zone_lo, "high": zone_hi, "dolu": dolu})
    return out


def find_liquidity(highs: list, lows: list, tol: float):
    """Eşit tepe/dip kümeleri (tolerans içinde >=2 swing) + swing ekstremleri."""
    pools = []

    def clusters(swings, side):
        if not swings:
            return
        prices = sorted(s["price"] for s in swings)
        grup = [prices[0]]
        for p in prices[1:]:
            if p - grup[-1] <= tol:
                grup.append(p)
            else:
                if len(grup) >= 2:
                    pools.append({"price": float(np.mean(grup)), "type": side,
                                  "kind": "esit-tepe" if side == "buyside" else "esit-dip",
                                  "count": len(grup)})
                grup = [p]
        if len(grup) >= 2:
            pools.append({"price": float(np.mean(grup)), "type": side,
                          "kind": "esit-tepe" if side == "buyside" else "esit-dip",
                          "count": len(grup)})

    clusters(highs, "buyside")
    clusters(lows, "sellside")
    if highs:
        hp = max(s["price"] for s in highs)
        if not any(p["type"] == "buyside" and abs(p["price"] - hp) <= tol for p in pools):
            pools.append({"price": float(hp), "type": "buyside", "kind": "swing-ekstrem", "count": 1})
    if lows:
        lp = min(s["price"] for s in lows)
        if not any(p["type"] == "sellside" and abs(p["price"] - lp) <= tol for p in pools):
            pools.append({"price": float(lp), "type": "sellside", "kind": "swing-ekstrem", "count": 1})
    return pools


def detect(job: dict) -> dict:
    p = {**DEFAULTS, **(job.get("params") or {})}
    df = load_frame(job)
    n = len(df)

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

    obs = []
    for ev in events[-5:]:
        ob = find_order_block(df, ev)
        if ob:
            obs.append(ob)
    fvgs = find_fvgs(df)
    acik_fvgs = [f for f in fvgs if not f["dolu"]][-10:]

    tol = (p["eq_tol_atr"] * atr) if atr else 0.001 * close_last
    liq = find_liquidity(highs, lows, tol)

    # HTF (MTF hizalama): verilirse aynı yapı mantığıyla HTF trendi
    htf_bias = None
    htf_info = None
    if job.get("htf_candles") is not None or job.get("htf_input"):
        hdf = load_frame(job, key="htf_candles", input_key="htf_input")
        hh, hl = find_swings(hdf, int(p["left"]), int(p["right"]))
        htrend, hevents = structure_events(hdf, hh, hl, int(p["right"]))
        htf_bias = htrend if htrend in ("bull", "bear") else None
        htf_info = {"trend": htrend, "olay_sayisi": len(hevents)}

    # confluence.py için hazır girdi (son olaydan)
    confluence_job = None
    if events:
        last = events[-1]
        if last.get("impulse_start") is not None:
            b = int(last["i"])
            if last["direction"] == "bull":
                imp_end = float(df["high"].iloc[b:].max())
            else:
                imp_end = float(df["low"].iloc[b:].min())
            confluence_job = {
                "structure": {"event": last["type"], "direction": last["direction"]},
                "impulse": {"start": float(last["impulse_start"]), "end": imp_end},
                "order_blocks": obs,
                "fvgs": [{"low": f["low"], "high": f["high"], "type": f["type"]}
                         for f in acik_fvgs],
                "liquidity": [{"price": q["price"], "type": q["type"]} for q in liq],
                "regime": {"durum": durum, "yuksek_vol": yuksek_vol},
            }
            if atr is not None:
                confluence_job["atr"] = round(atr, 8)
            if htf_bias:
                confluence_job["htf_bias"] = htf_bias

    return {
        "bar_sayisi": n,
        "trend": trend,
        "olaylar": events[-10:],
        "swing_sayisi": {"high": len(highs), "low": len(lows)},
        "order_blocks": obs,
        "acik_fvgler": acik_fvgs,
        "likidite": liq,
        "atr": round(atr, 8) if atr is not None else "VERİ YOK",
        "rejim": regime,
        "htf": htf_info,
        "confluence_job": confluence_job,
        "varsayimlar": [
            f"swing pencere left/right={p['left']}/{p['right']} (fraktal granülarite; varsayım)",
            f"ATR/ADX periyodu={p['atr_period']}/{p['adx_period']} (Wilder konvansiyonu)",
            f"ADX trend/range eşiği={p['adx_trend']}/{p['adx_range']} (Wilder konvansiyonu; "
            "params ile ezilebilir)",
            f"eşit tepe/dip toleransı={p['eq_tol_atr']}×ATR (varsayım)",
            f"yüksek-vol eşiği: {vol_kaynak}",
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
