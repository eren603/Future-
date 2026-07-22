#!/usr/bin/env python3
"""Setup tarihsel doğrulama — "edge kanıtı yoksa sinyal yok" (fail-closed) +
DİNAMİK KALİBRASYON (eşikler her koşuda bu verinin kendisinden türetilir).

Golden-zone retest kurulumunu (yapı kırılımı → impuls → 0.618-0.786 retest →
giriş) GEÇMİŞ veride mekanik simüle eder. Sabit eşik yerine (varsayılan mod):

  1) MAE kalibrasyonu (1. geçiş): geniş korkuluk-SL ile simüle edilir,
     kazanan işlemlerin gerçek maksimum ters hareketi (MAE, ATR birimi)
     ölçülür → SL tamponu = MAE quantile (sınırlı). 2. geçiş bu tamponla koşar.
  2) Permütasyon testi: aynı veri + aynı işlem mekaniğiyle rastgele girişler
     → kurulum, piyasa sürüklenmesinden İSTATİSTİKSEL olarak ayrışmalı
     (p <= alpha). "Yükselen piyasada her şey kâr eder" yanılgısını eler.
  3) Bootstrap %95 CI: beklentinin alt sınırı > 0 olmalı.
  4) Yarı-dönem tutarlılık: iki yarının beklentisi de > 0 (drift/rejim kontrolü).
  5) Dinamik R:R önerisi: gereken min R:R = (1-wr_lo)/wr_lo (Wilson kötümser
     kazanma oranından) → confluence eşiği olarak KULLANILIR.

Kapılar (fail-closed, kalibre mod):
  - işlem < n_taban                → VERİ YETERSİZ (sinyal izni YOK)
  - permütasyon p > alpha          → EDGE KANITLANAMADI (rastgeleden ayrışmıyor)
  - bootstrap CI alt sınırı <= 0   → ZAYIF EDGE
  - yarı-dönem beklentisi <= 0     → ZAYIF EDGE (drift)
  - aksi halde                     → EDGE KANITLI (geçmiş veride)

Kalan sabitler istatistik konvansiyonu/korkuluktur ve çıktıdaki
'varsayimlar' defterinde AÇIKÇA listelenir (gizli sabit yok).

Simülasyon kuralları (determinist, ileriye bakış yok):
- Olaylar smc_tespit.structure_events ile; swing i+right barında kesinleşir.
- İmpuls ucu E: olay sonrası koşan ekstrem `freeze` bar yenilenmezse donar;
  giriş taraması ancak ondan SONRA başlar.
- Giriş: golden zone sınırına İLK dokunuş; zone öncesi yeni ekstrem → iptal.
- Aynı barda SL+TP → SL sayılır (muhafazakâr). Aynı anda tek pozisyon.
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
import kalibrasyon as kb  # noqa: E402

_BT = _HERE.parents[1] / "backtest-motoru" / "scripts"
sys.path.insert(0, str(_BT))
import backtest as bt  # noqa: E402

GZ_LO, GZ_HI = 0.618, 0.786

DEFAULTS = {
    "left": 2, "right": 2, "atr_period": 14,
    "scan": 30,          # olay sonrası ekstrem arama penceresi (bar)
    "freeze": 3,         # ekstrem bu kadar bar yenilenmezse impuls ucu donar
    "wait": 40,          # donduktan sonra zone dokunuşu bekleme penceresi
    "atr_mult": 1.0,     # yalnız legacy mod / MAE verisi yoksa (varsayım)
    "tp_rr": 1.5,
    "max_bars": 60,
    "fees_bps": 5.0, "slippage_bps": 2.0,
    "risk_frac": 0.01,   # Monte Carlo için işlem başına risk (kesir)
    "min_trades": None,  # None → kalibrasyon.n_taban; legacy modda 15
    "mc_runs": 1000, "seed": 7,
    "direction": "auto",  # auto | long | short
    "kalibrasyon": True,  # False → eski statik kapılar (legacy)
}


def _sim_pass(df, events, atr_arr, p, atr_mult: float):
    """Tek simülasyon geçişi: verilen SL tamponuyla tüm kurulum işlemleri."""
    n = len(df)
    h = df["high"].to_numpy(); l = df["low"].to_numpy(); c = df["close"].to_numpy()
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

        # impuls ucunu dondur
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
            continue
        E = float(ext)
        rng_ = (E - s_price) if d == "bull" else (s_price - E)
        if rng_ <= 0:
            continue

        z_hi = (E - GZ_LO * rng_) if d == "bull" else (E + GZ_LO * rng_)
        entry_i = None
        start_j = e_i + freeze + 1
        for j in range(start_j, min(e_i + wait, n - 1) + 1):
            if d == "bull":
                if h[j] > E:
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
        is_long = d == "bull"
        sl = s_price - atr_mult * a if is_long else s_price + atr_mult * a
        tp_risk = (entry - sl) if is_long else (sl - entry)
        if tp_risk <= 0:
            continue
        tp = entry + p["tp_rr"] * tp_risk if is_long else entry - p["tp_rr"] * tp_risk

        t = kb.walk_trade(h, l, c, entry_i, entry, sl, tp, int(p["max_bars"]), is_long)
        if t is None:
            continue
        outcome, exit_i, mae_price = t
        cost_r = 2.0 * (p["fees_bps"] + p["slippage_bps"]) / 1e4 * entry / tp_risk
        trades.append({"entry_i": int(entry_i),
                       "dir": "long" if is_long else "short",
                       "R": round(float(outcome - cost_r), 4),
                       "mae_atr": round(float(mae_price / a), 4)})
        busy_until = exit_i

    trades.sort(key=lambda t: t["entry_i"])
    return trades


def simulate(job: dict) -> dict:
    p = {**DEFAULTS, **(job.get("params") or {})}
    kalibre = bool(p["kalibrasyon"])
    df = st.load_frame(job)
    h = df["high"].to_numpy(); l = df["low"].to_numpy(); c = df["close"].to_numpy()

    atr_arr = st.wilder_atr(df, int(p["atr_period"])).to_numpy()
    highs, lows = st.find_swings(df, int(p["left"]), int(p["right"]))
    trend, events = st.structure_events(df, highs, lows, int(p["right"]))

    kal_info = {}
    if kalibre:
        # --- 1. GEÇİŞ: geniş korkuluk-SL ile MAE ölç → tamponu veriden türet ---
        genis = kb.KONVANSIYON["atr_mult_sinir"][1]
        pas1 = _sim_pass(df, events, atr_arr, p, atr_mult=genis)
        kazanan_mae = [t["mae_atr"] for t in pas1 if t["R"] > 0]
        mae_k = kb.mae_atr_mult(kazanan_mae)
        atr_mult = float(mae_k["atr_mult"])
        kal_info["atr_mult_kalibre"] = mae_k
    else:
        atr_mult = float(p["atr_mult"])

    # --- ANA GEÇİŞ ---
    trades = _sim_pass(df, events, atr_arr, p, atr_mult=atr_mult)
    n_tr = len(trades)
    Rs = np.array([t["R"] for t in trades], dtype=float)

    def _cap(x):
        return round(float(min(x, 999.0)), 4)

    rapor = {"islem_sayisi": n_tr, "trend": trend, "olay_sayisi": len(events),
             "kullanilan_atr_mult": round(atr_mult, 3)}
    exp_r = pf = None
    exp1 = exp2 = None
    mc = None
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

    n_taban = int(p["min_trades"]) if p["min_trades"] is not None else \
        (kb.KONVANSIYON["n_taban"] if kalibre else 15)

    if kalibre:
        # --- DİNAMİK KAPILAR (istatistiksel; eşik seçilmez, türetilir) ---
        alpha = kb.KONVANSIYON["alpha"]
        perm = boot = rr_k = None
        if n_tr:
            perm = kb.permutation_pvalue(
                h, l, c, atr_arr, float(Rs.mean()),
                [t["dir"] for t in trades], atr_mult,
                float(p["tp_rr"]), int(p["max_bars"]), seed=int(p["seed"]))
            boot = kb.bootstrap_ci(Rs, seed=int(p["seed"]))
            rr_k = kb.dinamik_min_rr(int((Rs > 0).sum()), n_tr)
            kal_info.update({"permutasyon": perm, "bootstrap_ci_R": boot,
                             "onerilen_min_rr": rr_k})

        if n_tr < n_taban:
            verdict = "VERİ YETERSİZ"
            neden = f"işlem {n_tr} < taban {n_taban} — istatistik kurulamaz"
        elif perm["p"] > alpha:
            verdict = "EDGE KANITLANAMADI"
            neden = (f"permütasyon p={perm['p']} > {alpha}: kurulum, aynı verideki "
                     f"rastgele girişlerden ayrışmıyor (null ort={perm['null_ortalama']}R)")
        elif boot[0] <= 0:
            verdict = "ZAYIF EDGE"
            neden = f"bootstrap %95 CI {boot}: beklenti alt sınırı 0'ı geçmiyor"
        elif exp1 is not None and (exp1 <= 0 or exp2 <= 0):
            verdict = "ZAYIF EDGE"
            neden = f"yarı-dönem tutarsız {[exp1, exp2]} (drift/rejim değişimi)"
        else:
            verdict = "EDGE KANITLI (geçmiş veride)"
            neden = (f"beklenti {exp_r}R (CI {boot}), permütasyon p={perm['p']}, "
                     f"PF {pf}")
        varsayimlar = kb.varsayim_defteri([
            f"tp_rr={p['tp_rr']} (hedef tasarımı; likidite-hedefli sürümde veriye bağlanabilir)",
            f"fees+slippage={p['fees_bps']}+{p['slippage_bps']} bps (borsa varsayımı)",
            "kurulum tanımı: golden-zone retest (0.618-0.786) — SMC çerçevesi yorumsaldır",
        ])
    else:
        # --- LEGACY statik kapılar (geri uyumluluk; varsayım olarak etiketli) ---
        if n_tr < n_taban:
            verdict = "VERİ YETERSİZ"
            neden = f"işlem {n_tr} < {n_taban} — istatistik kurulamaz"
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
        varsayimlar = [f"LEGACY statik eşikler: min_trades={n_taban}, MC p>=0.6, "
                       "PF>1 — TASARIM VARSAYIMI (kalibre mod önerilir)"]

    rapor.update({
        "SONUC": verdict,
        "sinyal_izni": verdict == "EDGE KANITLI (geçmiş veride)",
        "gerekce": neden,
        "kalibrasyon": (kal_info or None),
        "esik_kaynagi": ("veri-türevi (her koşuda bu veriyle yeniden kalibre)"
                         if kalibre else "statik varsayım (legacy)"),
        "varsayimlar": varsayimlar,
        "islemler_son10": trades[-10:],
        "not": ("Geçmiş performans gelecek garantisi değildir. Bu bir eleme "
                "kapısıdır: kanıt yoksa sinyal verilmez. Canlı emir DAHİL DEĞİL."),
    })
    return rapor


def main() -> int:
    ap = argparse.ArgumentParser(description="Setup tarihsel doğrulama + dinamik kalibrasyon")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(simulate(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
