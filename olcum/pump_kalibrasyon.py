# pump_anomaly kalibrasyon olcumu — DETERMINISTIK (sabit tohum), IZLENEBILIR.
# Amac: btc_karargah_v5_3.py basligindaki sentetik olcum sayilarinin kaynagi.
# Kosum: python3 olcum/pump_kalibrasyon.py > olcum/pump_kalibrasyon_cikti.txt
# UYARI: veri sentetik lognormal gurultudur; GERCEK PIYASA OLCUMU DEGILDIR.
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btc_karargah_v5_3 import pump_anomaly, PUMP_SPAN, PUMP_THRESHOLD_Z

# ESKI v5.3 istatistigi (git 8506ea8'deki tanim) — kiyas icin birebir kopya
def pump_anomaly_eski(vol_series, span=PUMP_SPAN, threshold=PUMP_THRESHOLD_Z):
    if len(vol_series) < 5:
        return 0.0, "NONE"
    v = vol_series.astype(float).fillna(0.0)
    ewma = v.ewm(span=span, adjust=False).mean()
    evol = v.ewm(span=span, adjust=False).std()
    z = (v - ewma) / (evol + 1e-12)
    max_z = float(z.max())
    cus = v.diff().abs().rolling(window=10).sum()
    cs = cus / (evol + 1e-6)
    cs_max = float(cs.max()) if len(cs) else 0.0
    score = max(max_z, cs_max)
    if not np.isfinite(score):
        return 0.0, "NONE"
    if score < threshold * 0.6:
        return score, "NORMAL"
    if score < threshold:
        return score, "WATCH"
    return score, "PUMP_OR_DUMP_RISK"

N_SERI = 500
N_BAR = 2400

def seri(seed, sigma):
    return pd.Series(np.random.default_rng(seed).lognormal(3.0, sigma, N_BAR))

print("pump_anomaly kalibrasyonu | seri/hucre=%d | bar=%d | esik=%.1f (sabit)"
      % (N_SERI, N_BAR, PUMP_THRESHOLD_Z))
print("veri: lognormal(3, sigma) SENTETIK gurultu — gercek piyasa DEGIL\n")

print("[1] SAF GURULTU (spike yok) — yanlis-pozitif orani")
for sigma in (0.4, 0.8, 1.2):
    e_v = y_v = y_w = 0
    for k in range(N_SERI):
        v = seri(1000 + k, sigma)
        e_v += pump_anomaly_eski(v)[1] == "PUMP_OR_DUMP_RISK"
        n = pump_anomaly(v)[1]
        y_v += n == "PUMP_OR_DUMP_RISK"
        y_w += n == "WATCH"
    print(f"  sigma={sigma}: ESKI veto {e_v/N_SERI*100:5.1f}% | "
          f"YENI veto {y_v/N_SERI*100:4.1f}% WATCH {y_w/N_SERI*100:4.1f}%")

print("\n[2] SON BARDA HACIM SPIKE — yakalama orani (sigma=0.4)")
for mult in (2, 3, 5, 10, 20):
    hit = 0
    for k in range(N_SERI):
        v = seri(2000 + k, 0.4)
        v.iloc[-1] *= mult
        hit += pump_anomaly(v)[1] == "PUMP_OR_DUMP_RISK"
    print(f"  x{mult:<2d}: YENI veto {hit/N_SERI*100:5.1f}%")

print("\n[3] GECMIS SPIKE (40 bar once x50), su an sakin — kalici veto testi")
e_v = y_v = 0
for k in range(N_SERI):
    v = seri(3000 + k, 0.4)
    v.iloc[-40] *= 50
    e_v += pump_anomaly_eski(v)[1] == "PUMP_OR_DUMP_RISK"
    y_v += pump_anomaly(v)[1] == "PUMP_OR_DUMP_RISK"
print(f"  ESKI veto {e_v/N_SERI*100:5.1f}% | YENI veto {y_v/N_SERI*100:4.1f}%")

print("\n[4] ESKI ISTATISTIGIN TABANI (saf gurultu, sigma=0.4) — skor dagilimi")
skorlar = [pump_anomaly_eski(seri(4000 + k, 0.4))[0] for k in range(N_SERI)]
q = np.percentile(skorlar, [5, 50, 95])
print(f"  eski skor p5={q[0]:.2f} medyan={q[1]:.2f} p95={q[2]:.2f} (esik 3.0)")
