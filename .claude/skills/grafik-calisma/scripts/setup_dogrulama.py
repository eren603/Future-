#!/usr/bin/env python3
"""Setup tarihsel doğrulama — "edge kanıtı yoksa sinyal yok" (fail-closed).

Golden-zone retest kurulumunu (yapı kırılımı → impuls → 0.618-0.786 retest →
giriş) GEÇMİŞ veride mekanik olarak simüle eder ve backtest-motoru'nun
Monte Carlo'suna bağlar. Karar verilmeden önce bu kanıt üretilir:

- İşlem sayısı < min_trades        → VERİ YETERSİZ (sinyal izni YOK)
- Beklenti <= 0 veya PF <= 1       → EDGE KANITLANAMADI (sinyal izni YOK)
- MC kâr olasılığı < 0.6 ya da
  yarı-dönem beklentilerinden biri <= 0 → ZAYIF EDGE (sinyal izni YOK)
- Aksi halde                        → EDGE KANITLI (geçmiş veride)

Simülasyon kuralları (determinist, ileriye bakış yok):
- Olaylar smc_tespit.structure_events ile; swing i+right barında kesinleşir.
- İmpuls ucu E: olay sonrası koşan ekstrem, `freeze` bar boyunca yenilenmezse
  donar; giriş taraması ancak ondan SONRA başlar.
- Giriş: fiyat golden zone üst sınırına (long; short'ta alt) İLK dokunuşta,
  o sınır fiyatından. Zone öncesi yeni ekstrem yapılırsa kurulum iptal.
- SL: impuls başlangıç swing'i ± atr_mult*ATR. TP: tp_rr * risk.
- Aynı barda SL ve TP'ye ikisi birden değerse SL sayılır (muhafazakâr).
- max_bars dolarsa kapanıştan çıkılır. Aynı anda tek pozisyon.
- Maliyet: gidiş-dönüş (fees+slippage) R cinsinden düşülür.

⚠️ Geçmiş performans gelecek garantisi değildir; bu bir eleme kapısıdır,
kâr vaadi değildir. Canlı/otomatik emir DAHİL DEĞİL.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import smc_tespit as st  # noqa: E402

_BT = _HERE.parents[2] / "skills" / "backtest-motoru" / "scripts"
if not _BT.exists():
    _BT = _HERE.parents[1] / "backtest-motoru" / "scripts"
sys.path.insert(0, str(_BT))
import backtest as bt  # noqa: E402

GZ_LO, GZ_HI = 0.618, 0.786

DEFAULTS = {
    "left": 2, "right": 2, "atr_period": 14,
    "scan": 30,          # olay sonrası ekstrem arama penceresi (bar)
    "freeze": 3,         # ekstrem bu kadar bar yenilenmezse impuls ucu donar
    "wait": 40,          # donduktan sonra zone dokunuşu bekleme penceresi
    "atr_mult": 1.0,
    "tp_rr": 1.5,
    "max_bars": 60,
    "fees_bps": 5.0, "slippage_bps": 2.0,
    "risk_frac": 0.01,   # Monte Carlo için işlem başına risk (kesir)
    "min_trades": 15,
    "mc_runs": 1000, "seed": 7,
    "direction": "auto",  # auto | long | short
}


def simulate(job: dict) -> dict:
    p = {**DEFAULTS, **(job.get("params") or {})}
    df = st.load_frame(job)
    n = len(df)
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    c = df["close"].to_numpy()

    atr_arr = st.wilder_atr(df, int(p["atr_period"])).to_numpy()
    highs, lows = st.find_swings(df, int(p["left"]), int(p["right"]))
    trend, events = st.structure_events(df, highs, lows, int(p["right"]))

    want_dir = str(p["direction"]).lower()
    freeze = int(p["freeze"]); scan = int(p["scan"]); wait = int(p["wait"])
    trades = []
    busy_until = -1

    for ev in events:
        d = ev["direction"]
        if want_dir in ("long", "short") and \
           d != ("bull" if want_dir == "long" else "bear"):
            continue
        s_price = ev.get("impulse_start")
        if s_price is None:
            continue
        b = int(ev["i"])
        if b <= busy_until:
            continue

        # --- impuls ucunu dondur (freeze bar yenilenmezse) ---
        lim = min(b + scan, n - 1)
        e_i = b
        ext = h[b] if d == "bull" else l[b]
        i = b + 1
        frozen = False
        while i <= lim:
            v = h[i] if d == "bull" else l[i]
            better = v > ext if d == "bull" else v < ext
            if better:
                ext = v; e_i = i
            elif i - e_i >= freeze:
                frozen = True
                break
            i += 1
        if not frozen:
            continue  # uç kesinleşmedi → kurulum yok
        E = float(ext)
        rng_ = (E - s_price) if d == "bull" else (s_price - E)
        if rng_ <= 0:
            continue

        # --- golden zone ve giriş taraması (donduktan sonra) ---
        if d == "bull":
            z_hi = E - GZ_LO * rng_   # giriş tetiği (üst sınır)
        else:
            z_hi = E + GZ_LO * rng_   # short için alt sınır (fiyat yükselip değer)
        entry_i = None
        start_j = e_i + freeze + 1
        for j in range(start_j, min(e_i + wait, n - 1) + 1):
            if d == "bull":
                if h[j] > E:          # zone öncesi yeni ekstrem → kurulum iptal
                    break
                if l[j] <= z_hi:
                    entry_i = j; break
            else:
                if l[j] < E:
                    break
                if h[j] >= z_hi:
                    entry_i = j; break
        if entry_i is None:
            continue

        entry = float(z_hi)
        a = atr_arr[entry_i]
        if not np.isfinite(a) or a <= 0:
            a = 0.02 * entry
        if d == "bull":
            sl = s_price - p["atr_mult"] * a
            risk = entry - sl
        else:
            sl = s_price + p["atr_mult"] * a
            risk = sl - entry
        if risk <= 0:
            continue
        tp = entry + p["tp_rr"] * risk if d == "bull" else entry - p["tp_rr"] * risk

        # --- bar bar sonuç (SL önce: muhafazakâr) ---
        outcome = None
        exit_i = min(entry_i + int(p["max_bars"]), n - 1)
        for k in range(entry_i, exit_i + 1):
            if d == "bull":
                if l[k] <= sl:
                    outcome = -1.0; exit_i = k; break
                if h[k] >= tp:
                    outcome = float(p["tp_rr"]); exit_i = k; break
            else:
                if h[k] >= sl:
                    outcome = -1.0; exit_i = k; break
                if l[k] <= tp:
                    outcome = float(p["tp_rr"]); exit_i = k; break
        if outcome is None:
            outcome = float((c[exit_i] - entry) / risk) if d == "bull" \
                else float((entry - c[exit_i]) / risk)

        cost_r = 2.0 * (p["fees_bps"] + p["slippage_bps"]) / 1e4 * entry / risk
        trades.append({"entry_i": int(entry_i), "dir": "long" if d == "bull" else "short",
                       "R": round(float(outcome - cost_r), 4)})
        busy_until = exit_i

    trades.sort(key=lambda t: t["entry_i"])
    n_tr = len(trades)
    Rs = np.array([t["R"] for t in trades], dtype=float)

    def _cap(x):
        return round(float(min(x, 999.0)), 4)

    rapor = {"islem_sayisi": n_tr, "trend": trend, "olay_sayisi": len(events)}
    if n_tr:
        wins = Rs[Rs > 0]; losses = Rs[Rs < 0]
        pf = _cap(wins.sum() / abs(losses.sum())) if losses.size else _cap(np.inf)
        exp_r = round(float(Rs.mean()), 4)
        half = n_tr // 2
        exp1 = round(float(Rs[:half].mean()), 4) if half else None
        exp2 = round(float(Rs[half:].mean()), 4) if half else None
        mc = bt.monte_carlo([float(r * p["risk_frac"]) for r in Rs],
                            int(p["mc_runs"]), int(p["seed"]))
        rapor.update({"kazanma_orani": round(float((Rs > 0).mean()), 4),
                      "beklenti_R": exp_r, "profit_factor": pf,
                      "yari_donem_beklenti": [exp1, exp2],
                      "monte_carlo": mc})
    else:
        exp_r, pf, mc, exp1, exp2 = 0.0, 0.0, None, None, None

    # --- fail-closed karar ---
    if n_tr < int(p["min_trades"]):
        verdict = "VERİ YETERSİZ"
        neden = f"işlem {n_tr} < {p['min_trades']} — istatistik kurulamaz"
    elif exp_r <= 0 or pf <= 1.0:
        verdict = "EDGE KANITLANAMADI"
        neden = f"beklenti {exp_r}R, PF {pf}"
    elif (mc and mc.get("prob_profit", 0) < 0.6) or \
         (exp1 is not None and (exp1 <= 0 or exp2 <= 0)):
        verdict = "ZAYIF EDGE"
        neden = "MC kâr olasılığı düşük ya da yarı-dönem tutarsız"
    else:
        verdict = "EDGE KANITLI (geçmiş veride)"
        neden = f"beklenti {exp_r}R, PF {pf}, MC p(kâr)={mc['prob_profit']}"

    rapor.update({
        "SONUC": verdict,
        "sinyal_izni": verdict == "EDGE KANITLI (geçmiş veride)",
        "gerekce": neden,
        "islemler_son10": trades[-10:],
        "not": ("Geçmiş performans gelecek garantisi değildir. Bu bir eleme "
                "kapısıdır: kanıt yoksa sinyal verilmez. Canlı emir DAHİL DEĞİL."),
    })
    return rapor


def main() -> int:
    ap = argparse.ArgumentParser(description="Setup tarihsel doğrulama motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(simulate(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
