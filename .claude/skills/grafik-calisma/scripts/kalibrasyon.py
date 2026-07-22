#!/usr/bin/env python3
"""Dinamik eşik kalibrasyonu — eşikler her koşuda VERİDEN türetilir.

Sorun: sabit eşikler (min 15 işlem, MC p>=0.6, R:R>=2) tasarım varsayımıydı.
Piyasa durağan değildir (dinamik/kaotik/manipülatif): dünün eşiği bugünün
verisinde geçersiz olabilir. Çözüm iki uçlu tuzaktan kaçınır:

  TUZAK 1 (statik): sabit eşik → rejim değişince anlamsızlaşır.
  TUZAK 2 (serbest ayar): her işlemde eşiği "en iyi sonucu verene" çekmek →
  aşırı-uyum (backtest overfitting, veri madenciliği). Bu da yasak.

Bu modülün yolu: eşik SEÇİLMEZ, İSTATİSTİKTEN TÜRETİLİR — her koşuda,
o koşunun verisiyle:

- Permütasyon testi: kurulumun getirisi, AYNI veri + AYNI işlem mekaniğiyle
  rastgele girişlerin dağılımıyla kıyaslanır → ampirik p-değeri. Böylece
  "yükselen piyasada her şey kâr eder" yanılgısı elenir (edge, piyasa
  sürüklenmesinden ayrıştırılır).
- Bootstrap güven aralığı: beklentinin %95 CI alt sınırı > 0 olmalı.
- Wilson alt sınırı: kazanma oranının kötümser tahmini → gereken minimum R:R
  = (1-wr_lo)/wr_lo (başabaş formülünden; kazanma oranı ne kadar belirsizse
  gereken R:R o kadar yüksek).
- MAE kalibrasyonu: SL tamponu, kazanan işlemlerin gerçek maksimum ters
  hareket (MAE) dağılımının quantile'ından (ATR birimiyle) türetilir.

Kalan sabitler İSTATİSTİK KONVANSİYONLARIDIR (piyasa parametresi değil) ve
her çıktıda 'varsayimlar' defterinde açıkça listelenir — gizli sabit yok.
Determinist: tüm rastgelelik tohumlu.
"""
from __future__ import annotations

import numpy as np

# İstatistik konvansiyonları + korkuluklar (piyasa eşiği DEĞİL; defterde raporlanır)
KONVANSIYON = {
    "alpha": 0.05,            # anlamlılık düzeyi — bilimsel konvansiyon
    "ci_guven": 0.95,         # bootstrap güven düzeyi — konvansiyon
    "n_taban": 10,            # bootstrap/permütasyonun anlamlı olması için asgari örnek
    "n_boot": 1000,
    "n_perm": 200,
    "wilson_z": 1.96,         # %95 için normal quantile
    "rr_sinir": (1.0, 5.0),   # türetilen R:R korkuluğu (aşırı-uyum freni)
    "atr_mult_sinir": (0.5, 3.0),  # türetilen SL tamponu korkuluğu
    "mae_quantile": 0.9,      # kazananların MAE'sinin kapsanma oranı
}


def varsayim_defteri(ekstra: list | None = None) -> list:
    """Çıktıya konan açık varsayım listesi — hiçbir sabit gizli kalmaz."""
    d = [
        f"alpha={KONVANSIYON['alpha']} (anlamlılık; istatistik konvansiyonu)",
        f"CI güven={KONVANSIYON['ci_guven']} (konvansiyon)",
        f"n_taban={KONVANSIYON['n_taban']} işlem (küçük örneklemde test anlamsız; istatistik tabanı)",
        f"R:R korkuluğu={KONVANSIYON['rr_sinir']} (türetim sınırı; aşırı-uyum freni)",
        f"ATR-çarpan korkuluğu={KONVANSIYON['atr_mult_sinir']} (türetim sınırı)",
        f"MAE quantile={KONVANSIYON['mae_quantile']} (kazananların kapsanma oranı)",
    ]
    return d + list(ekstra or [])


def wilson_lo(wins: int, n: int, z: float | None = None) -> float:
    """Kazanma oranının Wilson skor alt sınırı (kötümser tahmin)."""
    if n <= 0:
        return 0.0
    z = KONVANSIYON["wilson_z"] if z is None else z
    p = wins / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    rad = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float(max(0.0, (center - rad) / denom))


def bootstrap_ci(rs, n_boot: int | None = None, seed: int = 7,
                 alpha: float | None = None):
    """Ortalama R beklentisi için percentile-bootstrap CI (determinist)."""
    rs = np.asarray(rs, dtype=float)
    if rs.size == 0:
        return None
    n_boot = KONVANSIYON["n_boot"] if n_boot is None else int(n_boot)
    alpha = KONVANSIYON["alpha"] if alpha is None else float(alpha)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, rs.size, size=(n_boot, rs.size))
    means = rs[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return [round(float(lo), 4), round(float(hi), 4)]


def dinamik_min_rr(wins: int, n: int) -> dict:
    """Gereken minimum R:R = başabaş R:R'nin kötümser (Wilson) hali.
    Başabaş: beklenti=0 → rr_be = (1-wr)/wr. wr yerine Wilson alt sınırı
    kullanılır: örneklem küçük/başarı belirsizse gereken R:R otomatik yükselir."""
    lo_sin, hi_sin = KONVANSIYON["rr_sinir"]
    if n <= 0:
        return {"min_rr": hi_sin, "wr_wilson_lo": 0.0,
                "kaynak": "işlem yok → korkuluk üst sınırı (fail-closed)"}
    wl = wilson_lo(wins, n)
    if wl <= 0.0:
        return {"min_rr": hi_sin, "wr_wilson_lo": 0.0,
                "kaynak": "Wilson alt sınırı 0 → korkuluk üst sınırı (fail-closed)"}
    rr = (1.0 - wl) / wl
    return {"min_rr": round(float(min(max(rr, lo_sin), hi_sin)), 3),
            "wr_wilson_lo": round(wl, 4),
            "kaynak": "veri-türevi: (1-wr_lo)/wr_lo, Wilson %95 alt sınırından"}


def mae_atr_mult(mae_atr_list) -> dict:
    """SL tamponu (ATR çarpanı) = kazanan işlemlerin MAE (ATR birimi)
    dağılımının quantile'ı, korkulukla sınırlı."""
    lo_sin, hi_sin = KONVANSIYON["atr_mult_sinir"]
    arr = np.asarray([m for m in mae_atr_list if np.isfinite(m)], dtype=float)
    if arr.size == 0:
        return {"atr_mult": 1.0, "kaynak": "MAE verisi yok → varsayılan 1.0 (varsayım)"}
    q = float(np.quantile(arr, KONVANSIYON["mae_quantile"]))
    return {"atr_mult": round(min(max(q, lo_sin), hi_sin), 3),
            "mae_q": round(q, 4),
            "kaynak": f"veri-türevi: kazanan MAE q{KONVANSIYON['mae_quantile']}"}


def walk_trade(h, l, c, entry_i: int, entry: float, sl: float, tp: float,
               max_bars: int, is_long: bool):
    """Tek işlemi bar bar yürüt. Aynı barda SL+TP → SL sayılır (muhafazakâr).
    Döner: (R, exit_i, mae_price). mae_price = pozisyon aleyhine en kötü
    hareketin giriş fiyatına uzaklığı (>=0)."""
    n = len(c)
    risk = (entry - sl) if is_long else (sl - entry)
    if risk <= 0:
        return None
    exit_i = min(entry_i + max_bars, n - 1)
    outcome = None
    worst = entry
    for k in range(entry_i, exit_i + 1):
        if is_long:
            worst = min(worst, l[k])
            if l[k] <= sl:
                outcome = -1.0; exit_i = k; break
            if h[k] >= tp:
                outcome = (tp - entry) / risk; exit_i = k; break
        else:
            worst = max(worst, h[k])
            if h[k] >= sl:
                outcome = -1.0; exit_i = k; break
            if l[k] <= tp:
                outcome = (entry - tp) / risk; exit_i = k; break
    if outcome is None:
        outcome = ((c[exit_i] - entry) / risk) if is_long else ((entry - c[exit_i]) / risk)
    mae_price = (entry - worst) if is_long else (worst - entry)
    return float(outcome), int(exit_i), float(max(0.0, mae_price))


def permutation_pvalue(h, l, c, atr, actual_mean_r: float, dirs: list,
                       atr_mult: float, tp_rr: float, max_bars: int,
                       n_perm: int | None = None, seed: int = 7) -> dict:
    """Kurulum seçiminin edge'i piyasa sürüklenmesinden ayrıştırır:
    AYNI veri + AYNI işlem mekaniği (ATR-SL, aynı tp_rr, aynı yön karışımı,
    aynı işlem sayısı) ile RASTGELE giriş barları → null dağılım.
    p = P(rastgele ortalama R >= gerçek ortalama R). Determinist (tohumlu)."""
    n_perm = KONVANSIYON["n_perm"] if n_perm is None else int(n_perm)
    n = len(c)
    valid = [i for i in range(n - 2) if np.isfinite(atr[i]) and atr[i] > 0]
    if not valid or not dirs:
        return {"p": 1.0, "not": "geçerli bar/işlem yok → p=1 (fail-closed)"}
    rng = np.random.default_rng(seed)
    ge = 0
    null_means = []
    for k in range(n_perm):
        rs = []
        for d in dirs:
            i = valid[int(rng.integers(0, len(valid)))]
            entry = float(c[i])
            a = float(atr[i])
            if d == "long":
                sl = entry - atr_mult * a
                tp = entry + tp_rr * (entry - sl)
                t = walk_trade(h, l, c, i, entry, sl, tp, max_bars, True)
            else:
                sl = entry + atr_mult * a
                tp = entry - tp_rr * (sl - entry)
                t = walk_trade(h, l, c, i, entry, sl, tp, max_bars, False)
            if t is not None:
                rs.append(t[0])
        m = float(np.mean(rs)) if rs else 0.0
        null_means.append(m)
        if m >= actual_mean_r:
            ge += 1
    p = (1 + ge) / (n_perm + 1)   # +1 düzeltmesi: p asla 0 raporlanmaz
    return {"p": round(float(p), 4),
            "null_ortalama": round(float(np.mean(null_means)), 4),
            "null_q95": round(float(np.quantile(null_means, 0.95)), 4),
            "n_perm": n_perm}
