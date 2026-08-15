# BTC KARARGAH v5.3.2 — ONCU VERI katmani + anlik uyari (v5.2 tamiri)
# --------------------------------------------------------------------
# v5.2 -> v5.3 TAMIR VE EKLENTI LOGU:
#   1) TANIMSIZ ISIM TAMIRI: tick_confirm_score ve PUMP_TICK_WATCH
#      tanimlandi. Kaynak: kullanicinin gonderdigi v5.2 metni (o dosya bu
#      depoda YOK — v5.2'ye dair iddialar o metnin taramasina dayanir ve
#      depodan DOGRULANAMAZ; bu acikca isaretlenir).
#   2) YONTEM CAGRISI TAMIRI: w = w.copy -> w = w.copy();
#      float(w["usd"].sum) -> float(w["usd"].sum()); aynisi amount icin.
#   3) EKLENTI (kullanici gereksinimi): ANLIK uyarilarin karar bileseni
#      ONCU veridir (tick akisi, emir defteri, tick kovalari, kapanmis-
#      dakika hacim z'si). ISTISNA — acik beyan: pump_anomaly hacim
#      bileseni KAPANMIS 15M mumlardan hesaplanir (gecikmeli ama
#      muhafazakar); "katmanin tamami oncu" iddiasi DOGRU DEGILDI,
#      v5.3.2'de duzeltildi.
#   4) ANI UYARILAR: anlik pump/dump dalgasi, V donusu (dip/tepe),
#      trend/rejim donusu — kod her sembolde calistiginda yazdirilir.
#   5) ESIK SABITLERI DEGISTIRILMEDI: FEE_TAKER, SLIPPAGE, ATR_SL_MULT,
#      TIME_STOP_BARS, Z_GRID, ALPHA, EMBARGO, BOOTSTRAP_B, LOB_DEPTH,
#      FR_TOLERANCE_BPS v5.3'ten beri ayni (git diff ile izlenebilir).
#   6) YENI ESIKLER HIPOTEZ ETIKETLIDIR: PUMP_TICK_WATCH, TICK_CONFIRM_*,
#      V_REVERSAL_* — canli olcumle kalibre edilmeden "cozum" kabul
#      edilmez; dogrulama plani dosya sonundadir.
#   7) LOOKAHEAD KORUMALARI (.shift(periods=1), olusmamis mumun
#      dusurulmesi) GEVSETILMEDI. Analiz en guncel KAPANMIS mumla calisir.
#   8) MODUL HICBIR EMIR GONDERMEZ: create_order yok, API anahtari yok;
#      cikti yalnizca sinyal ve uyaridir.
#
# v5.3.1 (canli kosu bulgusu — 11/11 sembol veto):
#   9) pump_anomaly() YENIDEN TANIMLANDI. Canli taramada 11 sembolun 11'i
#      14.79-17.92 bandinda "PUMP_OR_DUMP_RISK" verip motoru kilitledi
#      (kaynak: kullanicinin yapistirdigi canli kosu ciktisi). Kok neden:
#        - skor tum seri uzerinden aliniyordu (z.max()/cs.max()) -> "simdi
#          anomali var mi" yerine "son 25 gunde hic oldu mu";
#        - cs = rolling10(|dv|)/ewm_std(v) standartlastirilmis degildi ve
#          yapisi geregi yuksek bir taban uretiyordu.
#      Tamir: iki bilesen de SON KAPANMIS BARDA, kendi gecmis dagilimina
#      gore z-skoru olarak olculur; referanslar .shift(1) ile alinir.
#      Esik GEVSETILMEDI (PUMP_THRESHOLD_Z = 3.0 aynen).
#      OLCUM ARTEFAKTI (izlenebilir, deterministik, sabit tohum):
#      olcum/pump_kalibrasyon.py -> olcum/pump_kalibrasyon_cikti.txt
#      (500 seri/hucre, sentetik lognormal — GERCEK PIYASA DEGIL):
#      eski istatistik saf gurultude %100 veto, skor medyani 18.63
#      (esik 3.0'a karsi); yeni istatistik saf gurultude veto %2.4-4.8;
#      son barda x2 spike %36.2, x3 %74.2, x5 %97.0, x10 %100 yakalanir;
#      40 bar onceki x50 spike: eski %100 veto -> yeni %0.0.
#
# v5.3.2 (bagimsiz anayasa denetimi bulgulari — Constitution v2):
#  10) K25: "Tarama tamamlandi." kosulsuz basiliyordu (sifir sembol
#      taransa bile). Simdi tamam/atlanan sayilir; TAMAMLANDI yalniz
#      hepsi taranirsa, yoksa KISMEN/BASARISIZ yazilir.
#  11) tick_confirm_score KAPANMAMIS dakikayi "son dakika" sayiyordu:
#      z-skoru duvar-saati fazina bagliydi (dakika basinda buyuk spike
#      bile gomuluyordu = eskalasyon korlesmesi). Simdi yalniz KAPANMIS
#      dakikalar kullanilir; cut ile kismi kalan ilk dakika da dusulur
#      (mum katmanindaki kapanmis-bar disiplini tick katmanina tasindi).
#  12) "CPCV" adlandirmasi yanlisti: fonksiyon kombinatoryal-purged CV
#      degil, embargolu GENISLEYEN-PENCERE walk-forward'dir. Ad ve
#      ciktilar duzeltildi (walkforward_splits / "WF+FDR+bootstrap").
#  13) pump_anomaly kisa seride (<30 bar) "NONE" yerine "VERI_YOK" doner
#      ve ciktida "anomali yok" DENMEZ (eksik veri "anomali yok" degildir).
#      Not: bu yol canli akista erisilmez (sinyal motoru >=700 bar ister).
#  14) selftest genisletildi: pump_anomaly spike yakalama + sakin seri,
#      tick_confirm_score bos-veri fail-closed, v_reversal_detect bos
#      girdi — deterministik, agsiz.
#  15) pump_dump_direction ayni girdiyle iki kez cagriliyordu; tek cagri.
#  16) Miras sabitler (rejim marji, guven formulu, router esikleri, WATCH
#      bandi, LIMIT_TIMEOUT_SEC...) "MIRAS SABIT — kalibre edilmedi"
#      diye etiketlendi; kalibre edilmis suslemesi yapilmaz.
# --------------------------------------------------------------------

import math
import traceback

import ccxt
import numpy as np
import pandas as pd

EXCHANGE = ccxt.binanceusdm({"enableRateLimit": True})

TF_4H = "4h"
TF_15M = "15m"
TF_MS = {"15m": 900000, "4h": 14400000}
LIMIT_15M = 2400
LIMIT_4H = 600

# Asagidaki sabitler v5.2 mirasidir ve bu depoda KALIBRE EDILMEMISTIR
# (MIRAS SABIT etiketi): degerlerin olculmus bir dayanagi dosyada yok.
FEE_TAKER = 0.00040
SLIPPAGE = 0.0005
ATR_LEN = 14
ATR_SL_MULT = 1.5
TIME_STOP_BARS = 48
ALPHA = 0.05
MIN_TRADES = 8
N_FOLDS = 5
EMBARGO = 24
BOOTSTRAP_B = 2000
# NOT: v5.2 metninde seed cifti okunamaz durumdaydi; asagidaki iki seed
# YENIDEN KURULMUS degerdir (sabit/tekrarlanabilir olmasi disinda bir
# iddiasi yoktur). Farkli seed ile p_max marjinal degisebilir.
BOOTSTRAP_SEEDS = (20240101, 20250101)
Z_GRID = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]
PUMP_BUCKET_MS = 30_000
PUMP_SPAN = 20           # MIRAS SABIT — kalibre edilmedi
PUMP_THRESHOLD_Z = 3.0   # MIRAS SABIT — kalibre edilmedi (degistirilmez, K22)
FR_TOLERANCE_BPS = 5.0   # MIRAS SABIT — kalibre edilmedi
LOB_DEPTH = 5            # MIRAS SABIT — kalibre edilmedi
TARGET_USD = 500.0
LIMIT_TIMEOUT_SEC = 8.0  # MIRAS SABIT — kalibre edilmedi

# --- v5.3 ONCU VERI / ANLIK UYARI parametreleri (HIPOTEZ) ---
PUMP_TICK_WATCH = 2.5          # hipotez: tick hacim z esigi (v5.2'de tanimsizdi)
TICK_CONFIRM_WINDOW_MIN = 15   # hipotez: tick teyit penceresi (dakika)
TICK_CONFIRM_MIN_TRADES = 10   # hipotez: minimum tick adedi
V_REVERSAL_WINDOW_SEC = 900    # hipotez: V donusu pencere genisligi (15 dk)
V_REVERSAL_BUCKET_SEC = 30     # hipotez: tick kova buyuklugu (sn)
V_REVERSAL_MIN_ABS_PCT = 0.004  # hipotez: ekstrem oncesi minimum hareket (%0.4)
V_REVERSAL_FLIP_PCT = 0.002    # hipotez: ekstremden minimum donus (%0.2)
V_REVERSAL_MIN_BUCKETS = 6     # hipotez: minimum dolu kova sayisi
LOB_BIAS_ALERT = 0.10          # router'daki mevcut bias esigi ile ayni

SYMBOLS = [
    "ETH/USDT", "XRP/USDT", "LINK/USDT", "DOGE/USDT", "DOT/USDT",
    "AVAX/USDT", "SUSHI/USDT", "ZEC/USDT", "ETC/USDT", "FIL/USDT",
    "AAVE/USDT",
]


# ---------------------------------------------------------------------------
# 0. KENDINDEN KONTROL
# ---------------------------------------------------------------------------
def selftest():
    end_ms = int(pd.Timestamp.now(tz="UTC").value // 1_000_000)
    assert isinstance(end_ms, int) and end_ms > 1_700_000_000_000, \
        "Selftest 1 BASARISIZ: zaman damgasi"
    s = pd.Series([1.0, 2.0]).shift(periods=1)
    assert pd.isna(s.iloc[0]) and float(s.iloc[1]) == 1.0, \
        "Selftest 2 BASARISIZ: shift sonucu"
    probe = pd.Series([1.0, 2.0, 3.0, 5.0, 8.0]).ewm(span=3).std()
    assert len(probe.dropna()) > 0, \
        "Selftest 3 BASARISIZ: ewm.std"
    # v5.3.2: davranis testleri (deterministik, agsiz)
    v = pd.Series(np.random.default_rng(42).lognormal(3.0, 0.4, 600))
    sc, note = pump_anomaly(v)
    assert note in ("NORMAL", "WATCH"), \
        f"Selftest 4 BASARISIZ: sakin seride {note} (skor={sc:.2f})"
    v2 = v.copy()
    v2.iloc[-1] *= 10.0
    sc2, note2 = pump_anomaly(v2)
    assert note2 == "PUMP_OR_DUMP_RISK", \
        f"Selftest 5 BASARISIZ: x10 spike yakalanmadi ({note2}, {sc2:.2f})"
    assert pump_anomaly(pd.Series([1.0] * 10))[1] == "VERI_YOK", \
        "Selftest 6 BASARISIZ: kisa seri VERI_YOK degil"
    bos = pd.DataFrame(columns=["timestamp", "price", "amount"])
    assert tick_confirm_score("SELFTEST", bos) is None, \
        "Selftest 7 BASARISIZ: bos tick verisi None donmedi"
    assert v_reversal_detect(None) == [], \
        "Selftest 8 BASARISIZ: bos girdi V-donusu bos liste degil"
    print("Kendinden kontrol: OK (8 test)")


# ---------------------------------------------------------------------------
# 1. VERI CEKME (KAPANMAMIS MUM ANALIZE ALINMAZ — lookahead korumasi)
# ---------------------------------------------------------------------------
def unix_ms(lookback_min=0):
    now_ms = int(pd.Timestamp.now(tz="UTC").value // 1_000_000)
    return int(now_ms - lookback_min * 60_000)


def fetch_ohlcv(symbol, timeframe, limit):
    step_ms = TF_MS.get(timeframe)
    if step_ms is None:
        raise ValueError("TF desteklenmiyor: " + timeframe)
    end = unix_ms()
    since = end - limit * step_ms
    arr = None
    while since < end:
        part = EXCHANGE.fetch_ohlcv(symbol, timeframe=timeframe,
                                    since=since, limit=1000)
        if not part:
            break
        arr = np.asarray(part, dtype=float) if arr is None else \
            np.vstack([arr, np.asarray(part, dtype=float)])
        since += len(part) * step_ms
    if arr is None:
        raise ValueError("Veri alinamadi: " + symbol)
    df = pd.DataFrame(arr, columns=["timestamp", "open", "high", "low",
                                    "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = (df.drop_duplicates(subset="timestamp")
            .tail(limit)
            .set_index("timestamp")
            .astype(float))
    if len(df) > 1:
        df = df.iloc[:-1]  # koruma: olusmamis mum dusurulur (degismedi)
    return df


def fetch_order_book(symbol):
    try:
        ob = EXCHANGE.fetch_order_book(symbol, limit=LOB_DEPTH)
    except Exception:
        return None, None
    if not ob or not ob.get("bids") or not ob.get("asks"):
        return None, None
    bids = pd.DataFrame(ob["bids"][:LOB_DEPTH], columns=["price", "size"])
    asks = pd.DataFrame(ob["asks"][:LOB_DEPTH], columns=["price", "size"])
    return bids, asks


def fetch_recent_trades(symbol, lookback_min=60):
    empty = pd.DataFrame(columns=["timestamp", "price", "amount"])
    try:
        trades = EXCHANGE.fetch_trades(
            symbol, since=unix_ms(lookback_min=lookback_min), limit=1000)
    except Exception:
        return empty
    if not trades:
        return empty
    df = pd.DataFrame(trades)
    for col in ("timestamp", "price", "amount"):
        if col not in df.columns:
            return empty
    return df[["timestamp", "price", "amount"]].astype(float)


def fetch_funding_oi(symbol):
    fr_df = pd.DataFrame()
    oi = float("nan")
    try:
        fr_raw = EXCHANGE.fetch_funding_rate_history(symbol, limit=8)
        if fr_raw:
            fr_df = pd.DataFrame(fr_raw)
    except Exception:
        pass
    try:
        oi_raw = EXCHANGE.fetch_open_interest(symbol)
        oi = float(oi_raw.get("openInterestAmount", float("nan")))
    except Exception:
        pass
    return fr_df, oi


def lob_imbalance(bids, asks):
    """ONCU veri: emir defteri dengesi (pozitif = alis agirlikli)."""
    if bids is None or asks is None or bids.empty or asks.empty:
        return 0.0, 0.0, float("inf")
    bid_usd = float((bids["price"] * bids["size"]).sum())
    ask_usd = float((asks["price"] * asks["size"]).sum())
    best_bid = float(bids["price"].iloc[0])
    best_ask = float(asks["price"].iloc[0])
    spread_bps = (best_ask - best_bid) / best_bid * 1e4
    imb = (bid_usd - ask_usd) / max(bid_usd + ask_usd, 1e-12)
    return imb, bid_usd + ask_usd, spread_bps


# ---------------------------------------------------------------------------
# 2. KORELASYON — BTC ve ETH referans
# ---------------------------------------------------------------------------
def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def log_returns(close):
    return np.log(close / close.shift(periods=1)).dropna()


def corr_stats(alt_close, ref_close, n_max=672):
    d = pd.concat([log_returns(alt_close), log_returns(ref_close)],
                  axis=1).dropna().tail(n_max)
    if len(d) < 50:
        return None
    r = float(d.iloc[:, 0].corr(d.iloc[:, 1]))
    if not np.isfinite(r):
        return None
    zf = 0.5 * math.log((1.0 + r) / max(1.0 - r, 1e-12))
    se = 1.0 / math.sqrt(len(d) - 3)
    p = 2.0 * (1.0 - norm_cdf(abs(zf) / se))
    return {"n": len(d), "r": r, "p": p}


# ---------------------------------------------------------------------------
# 3. PUMP / DUMP — EWMA + degisim noktasi skoru (ONCU: hacim fiyatin onunde)
# ---------------------------------------------------------------------------
def pump_anomaly(vol_series, span=PUMP_SPAN, threshold=PUMP_THRESHOLD_Z):
    """Hacim anomalisi — SON KAPANMIS BARDA olculur (seri maksimumu DEGIL).

    v5.3.1 TAMIR. Belirti (kaynak: kullanicinin yapistirdigi canli kosu
    ciktisi): 11/11 sembol 14.79-17.92 bandinda veto yedi; kalici veto
    davranisi spike ICERMEYEN sentetik gurultude de yeniden uretildi
    (olcum artefakti: olcum/pump_kalibrasyon_cikti.txt). Kok neden:
      (a) Eski kod skoru TUM seri uzerinden aliyordu (z.max(), cs.max()) —
          "su anda anomali var mi" yerine "son 25 gunde hic oldu mu" sorusu.
          Cevap her sembolde EVET oldugu icin veto kalici hale geliyordu.
      (b) Eski `cs = rolling10(|dv|) / ewm_std(v)` STANDARTLASTIRILMIS bir
          istatistik degildi: 10 barlik mutlak degisim toplami tek barlik
          standart sapmaya bolununce spike olmadan da yuksek taban uretir —
          olcum: sentetik gurultude cs-medyani ~9.9-10.9, yani esik 3.0'in
          ~3.3-3.6 kati (bkz. artefakt bolum [5]; eski TOPLAM skorun
          tabani icin bolum [4]: medyan 18.63).
    Tamir: her iki bilesen de KENDI gecmis dagilimina gore z-skoruna
    cevrildi ve referans .shift(1) ile hesaplandi (bar kendi referansinin
    icinde yer almaz). Esik GEVSETILMEDI (PUMP_THRESHOLD_Z = 3.0 aynen);
    degisen sey esigin uygulandigi istatistigin dogru tanimlanmasidir.
    """
    if len(vol_series) < 30:
        # v5.3.2 (K34): eksik veri "anomali yok" DEGILDIR — acikca isaretle.
        # Canli akista erisilmez yol (sinyal motoru >= 700 bar ister).
        return 0.0, "VERI_YOK"
    v = vol_series.astype(float).fillna(0.0)
    # (1) hacim seviyesi: son bar, kendisini ICERMEYEN EWMA referansina gore
    ewma = v.ewm(span=span, adjust=False).mean().shift(periods=1)
    evol = v.ewm(span=span, adjust=False).std().shift(periods=1)
    z = (v - ewma) / (evol + 1e-12)
    z_now = float(z.iloc[-1])
    # (2) degisim noktasi: 10-barlik |dv| toplaminin KENDI dagilimindaki z'si
    cus = v.diff().abs().rolling(window=10).sum()
    cus_mu = cus.ewm(span=span * 5, adjust=False).mean().shift(periods=1)
    cus_sd = cus.ewm(span=span * 5, adjust=False).std().shift(periods=1)
    cs = (cus - cus_mu) / (cus_sd + 1e-12)
    cs_now = float(cs.iloc[-1])
    if not (np.isfinite(z_now) or np.isfinite(cs_now)):
        return 0.0, "VERI_YOK"
    z_now = z_now if np.isfinite(z_now) else 0.0
    cs_now = cs_now if np.isfinite(cs_now) else 0.0
    score = max(z_now, cs_now)
    if score < threshold * 0.6:  # WATCH bandi carpani 0.6: MIRAS SABIT — kalibre edilmedi
        return score, "NORMAL"
    if score < threshold:
        return score, "WATCH"
    return score, "PUMP_OR_DUMP_RISK"


def pump_dump_direction(trades, close_15m, lookback_min=15):
    """Yon tespiti: tick VWAP + 15m OHLCV birlikte. ONCU veri.
      Hacim anomalisi + fiyat yukari = PUMP (sisme fazi)
      Hacim anomalisi + fiyat asagi  = DUMP (satis dalgasi)
    v5.3 TAMIR: w = w.copy() ve .sum() parantezleri eklendi."""
    tick_dir = 0.0
    if trades is not None and not trades.empty and len(trades) >= 10:
        cut = unix_ms(lookback_min=lookback_min)
        w = trades[trades["timestamp"] >= cut]
        if len(w) >= 10:
            w = w.copy()
            w["usd"] = w["price"] * w["amount"]
            tot_usd = float(w["usd"].sum())
            tot_amt = float(w["amount"].sum())
            if tot_amt > 0:
                vwap = tot_usd / tot_amt
                last_px = float(w["price"].iloc[-1])
                tick_dir = (last_px - vwap) / vwap
    ohlcv_dir = 0.0
    if close_15m is not None and len(close_15m) >= 3:
        c = close_15m.astype(float)
        ohlcv_dir = (float(c.iloc[-1]) - float(c.iloc[-3])) / float(c.iloc[-3])
    move = tick_dir if abs(tick_dir) > 1e-12 else ohlcv_dir
    if move <= -0.005:
        return "DUMP", move
    if move >= 0.005:
        return "PUMP", move
    return "YON_BELIRSIZ", move


# ---------------------------------------------------------------------------
# 4. v5.3 ONCU VERI KATMANI — tick teyidi, V donusu, trend donusu
# ---------------------------------------------------------------------------
def tick_confirm_score(symbol, trades=None):
    """ONCU tick hacim z-skoru. Son dakikanin USD hacmi, onceki dakikalara
    gore kac sigma sapmis? Yetersiz veride None.
    (v5.2'de cagiriliyordu ama tanimsizdi; v5.3'te tanimlandi.)"""
    if trades is None:
        trades = fetch_recent_trades(symbol,
                                     lookback_min=TICK_CONFIRM_WINDOW_MIN)
    if trades is None or trades.empty:
        return None
    t = trades.copy()
    t = t[t["timestamp"] >= unix_ms(lookback_min=TICK_CONFIRM_WINDOW_MIN)]
    if len(t) < TICK_CONFIRM_MIN_TRADES:
        return None
    t["usd"] = t["price"] * t["amount"]
    t["minute"] = (t["timestamp"] // 60_000).astype("int64")
    m = t.groupby("minute")["usd"].sum().sort_index()
    # v5.3.2: yalniz KAPANMIS dakikalar. Icinde bulundugumuz dakika kismi
    # oldugundan z-skoru duvar-saati fazina bagimliydi (dakika basinda
    # buyuk spike bile gomuluyordu). Kapanmis-bar disiplini tick katmanina
    # tasindi. Cut ile kismi kalan ILK dakika da dusulur.
    now_minute = unix_ms() // 60_000
    m = m[m.index < now_minute]
    if len(m) >= 2:
        m = m.iloc[1:]
    if len(m) < 5:
        return None
    cur = float(m.iloc[-1])   # son KAPANMIS dakika
    past = m.iloc[:-1].astype(float)
    base = float(past.mean())
    sd = float(past.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0.0 or base <= 0.0:
        return None
    return (cur - base) / sd


def v_reversal_detect(trades, window_sec=V_REVERSAL_WINDOW_SEC,
                      bucket_sec=V_REVERSAL_BUCKET_SEC,
                      min_abs_pct=V_REVERSAL_MIN_ABS_PCT,
                      flip_pct=V_REVERSAL_FLIP_PCT,
                      min_buckets=V_REVERSAL_MIN_BUCKETS):
    """V DONUSU (dip/tepe) — ONCU tick verisiyle anlik tespit.
    Yalnizca uyari uretir; islem/stop kararina karismaz.
    Esikler hipotezdir: canli calistirilarak kalibre edilmelidir."""
    if trades is None or trades.empty or len(trades) < 20:
        return []
    cut = unix_ms(lookback_min=window_sec / 60.0)
    w = trades[trades["timestamp"] >= cut].copy()
    if len(w) < 20:
        return []
    w = w.sort_values("timestamp")
    w["bucket"] = (w["timestamp"] // (bucket_sec * 1000)).astype("int64")
    b = w.groupby("bucket")["price"].agg(["mean", "min", "max", "count"]).dropna()
    if len(b) < min_buckets:
        return []
    px = b["mean"].to_numpy(dtype=float)
    n = len(px)
    warnings = []
    imin = int(np.argmin(px))
    if 1 <= imin <= n - 3:  # ekstrem pencerenin icinde, ucunda degil
        recover = float(px[-1]) / float(px[imin]) - 1.0     # pozitif
        drop = -(float(px[imin]) / float(px[0]) - 1.0)      # dusus buyuklugu (pozitif)
        if drop >= min_abs_pct and recover >= flip_pct:
            warnings.append({"kind": "V_DIP",
                             "drop_pct": drop * 100.0,
                             "recover_pct": recover * 100.0,
                             "detail": "satis dalgasi sonrasi yukari donus onculeri"})
    imax = int(np.argmax(px))
    if 1 <= imax <= n - 3:
        rise = float(px[imax]) / float(px[0]) - 1.0         # pozitif
        pull = float(px[-1]) / float(px[imax]) - 1.0        # negatif
        if rise >= min_abs_pct and pull <= -flip_pct:
            warnings.append({"kind": "V_TEPE",
                             "rise_pct": rise * 100.0,
                             "pullback_pct": -pull * 100.0,
                             "detail": "alis dalgasi sonrasi asagi donus onculeri"})
    return warnings


def trend_flip_watch(close_15m, trades, min_mom_pct=0.001):  # min_mom_pct: hipotez, kalibre edilmedi
    """Trend/rejim donusu uyarisi. EMA8/21 kesismesi yalnizca baglamdir;
    karar ONCU tick momentumundadir."""
    if close_15m is None or len(close_15m) < 30:
        return None
    c = close_15m.astype(float)
    e8 = c.ewm(span=8, adjust=False).mean()
    e21 = c.ewm(span=21, adjust=False).mean()
    cross_up = float(e8.iloc[-1]) > float(e21.iloc[-1]) and \
        float(e8.iloc[-2]) <= float(e21.iloc[-2])
    cross_dn = float(e8.iloc[-1]) < float(e21.iloc[-1]) and \
        float(e8.iloc[-2]) >= float(e21.iloc[-2])
    if not (cross_up or cross_dn):
        return None
    mom = 0.0
    if trades is not None and not trades.empty:
        t = trades.copy()
        cut = unix_ms(lookback_min=10)
        t = t[t["timestamp"] >= cut].sort_values("timestamp")
        if len(t) >= 10:
            half = len(t) // 2
            lo = float(t["price"].iloc[:half].mean())
            hi = float(t["price"].iloc[half:].mean())
            if lo > 0:
                mom = (hi - lo) / lo
    if cross_up:
        if mom > min_mom_pct:
            return (f"TREND DONUSU: EMA8/21 yukari kesisti + "
                    f"tick momentum {mom * 100:+.2f}%")
        return (f"TREND DONUSU ONCUSU: EMA8/21 kesisti, "
                f"tick dogrulama YOK (mom={mom * 100:+.2f}%)")
    if mom < -min_mom_pct:
        return (f"TREND DONUSU: EMA8/21 asagi kesisti + "
                f"tick momentum {mom * 100:+.2f}%")
    return (f"TREND DONUSU ONCUSU: EMA8/21 kesisti, "
            f"tick dogrulama YOK (mom={mom * 100:+.2f}%)")


def realtime_warnings(symbol, trades, close_15m, bids, asks,
                      vol_score, vol_note, yon, yon_move):
    """ONCU veri (tick akisi, LOB, anlik hacim z) ile ANI uyarilar.
    Yalnizca uyari: islem kararina ve stoplara karismaz."""
    warns = []
    imb, depth_usd, spread_bps = lob_imbalance(bids, asks)
    if vol_note == "PUMP_OR_DUMP_RISK":
        if yon == "DUMP":
            warns.append(f"ANILIK DUMP DALGASI: hacim z={vol_score:.2f}, "
                         f"tick {yon_move * 100:+.2f}%")
        elif yon == "PUMP":
            warns.append(f"ANILIK PUMP DALGASI: hacim z={vol_score:.2f}, "
                         f"tick {yon_move * 100:+.2f}%")
        else:
            warns.append(f"ANILIK PUMP/DUMP RISKI: hacim z={vol_score:.2f}, "
                         f"yon belirsiz")
    if imb <= -LOB_BIAS_ALERT:
        warns.append(f"LOB ALARM: satis agirlikli (OBI={imb:+.2f})")
    elif imb >= LOB_BIAS_ALERT:
        warns.append(f"LOB ALARM: alis agirlikli (OBI={imb:+.2f})")
    for v in v_reversal_detect(trades):
        if v["kind"] == "V_DIP":
            warns.append(f"V DONUSU: dusus {v['drop_pct']:.2f}% -> "
                         f"toparlanma {v['recover_pct']:+.2f}% | {v['detail']}")
        else:
            warns.append(f"V DONUSU: yukselis {v['rise_pct']:.2f}% -> "
                         f"geri cekilme {v['pullback_pct']:+.2f}% | {v['detail']}")
    flip = trend_flip_watch(close_15m, trades)
    if flip:
        warns.append(flip)
    return warns


# ---------------------------------------------------------------------------
# 5. REJIM TESPITI — dinamik ATR-marjli
# ---------------------------------------------------------------------------
def regime_detector(close_15m, close_4h):
    if len(close_15m) < 20 or len(close_4h) < 50:
        return "UNKNOWN", 0.0
    r15 = log_returns(close_15m)
    if len(r15) < 20:
        return "UNKNOWN", 0.0
    ef = close_4h.ewm(span=50, adjust=False).mean()
    es = close_4h.ewm(span=200, adjust=False).mean()
    slope = (ef - es) / close_4h
    tr4 = (close_4h - close_4h.shift(periods=1)).abs()
    atr_pct = float((tr4.rolling(window=14).mean() / close_4h).iloc[-1])
    if not np.isfinite(atr_pct):
        atr_pct = 0.0
    margin = max(0.003, atr_pct * 1.5)  # MIRAS SABIT (0.003, 1.5) — kalibre edilmedi
    s = slope.reindex(r15.index, method="ffill").fillna(0.0)
    mu = float(r15.mean())
    cur = float(s.iloc[-1])
    # Guven formulu (0.5 + |cur|*5, tavan 0.9) ve CALM=0.7: MIRAS SABIT —
    # kalibre edilmedi; olculmus olasilik DEGIL, siralama amacli skordur.
    if cur > margin and mu > 0:
        return "BULL", min(0.9, 0.5 + abs(cur) * 5.0)
    if cur < -margin and mu < 0:
        return "BEAR", min(0.9, 0.5 + abs(cur) * 5.0)
    return "CALM", 0.7


# ---------------------------------------------------------------------------
# 6. ISTATISTIK (BH-FDR + coklu seed max-t bootstrap)
# ---------------------------------------------------------------------------
def oos_stats(trades, min_n=MIN_TRADES):
    if len(trades) < min_n:
        return None
    a = np.asarray(trades, dtype=float)
    n = len(a)
    mean = float(np.mean(a))
    sd = float(np.std(a, ddof=1))
    t = mean / (sd / math.sqrt(n)) if sd > 0 else 0.0
    wins = a[a > 0]
    losses = -a[a <= 0]
    ls = float(np.sum(losses))
    pf = float(np.sum(wins) / ls) if ls > 0 else float("inf")
    cum = np.cumprod(1.0 + a)
    pk = np.maximum.accumulate(cum)
    return {"n": n, "mean": mean, "sd": sd, "t": t,
            "win": float(len(wins) / n), "pf": pf,
            "mdd": float(np.min(cum / pk - 1.0))}


def fdr_bh(pvalues, alpha=ALPHA):
    m = len(pvalues)
    if m == 0:
        return []
    order = np.argsort(pvalues)
    arr = np.asarray(pvalues, dtype=float)[order]
    thr_arr = np.asarray([(k + 1) / m * alpha for k in range(m)])
    accept = arr <= thr_arr
    if not accept.any():
        return [False] * m
    kmax = int(np.max(np.where(accept)[0]))
    keep = np.zeros(m, dtype=bool)
    keep[:kmax + 1] = True
    out = [False] * m
    for i, ix in enumerate(order):
        out[ix] = bool(keep[i])
    return out


def bootstrap_max_t(oos_by_rule, B=BOOTSTRAP_B, seeds=BOOTSTRAP_SEEDS):
    valid = []
    for r in oos_by_rule.values():
        a = np.asarray(r, dtype=float)
        if len(a) >= 2:
            valid.append(a)
    if not valid:
        return 1.0
    t_obs = 0.0
    for a in valid:
        m = len(a)
        sd = float(np.std(a, ddof=1))
        if sd > 0:
            t_obs = max(t_obs, float(np.mean(a)) / (sd / math.sqrt(m)))
    p_seeds = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        n_exceed = 0
        for _ in range(B):
            tmax = 0.0
            for a in valid:
                m = len(a)
                sample = a[rng.integers(0, m, size=m)]
                centered = sample - float(np.mean(a))
                cm = float(np.mean(centered))
                cs = float(np.std(centered, ddof=1))
                tb = cm / (cs / math.sqrt(m)) if cs > 0 else 0.0
                tmax = max(tmax, tb)
            if tmax >= t_obs:
                n_exceed += 1
        p_seeds.append(n_exceed / B)
    return float(np.mean(p_seeds))


# ---------------------------------------------------------------------------
# 7. WALK-FORWARD BOLUMLEME (genisleyen pencere + embargo)
#    v5.3.2 AD DUZELTMESI: eski ad "cpcv_splits" YANLISTI — bu fonksiyon
#    kombinatoryal-purged CV (CPCV) degil, embargolu genisleyen-pencere
#    walk-forward'dir (train daima testten once; kombinasyon yok).
#    Sahip olunmayan yontem adi iddia edilmez.
# ---------------------------------------------------------------------------
def walkforward_splits(n, k=N_FOLDS, embargo=EMBARGO):
    fold = n // k
    splits = []
    if fold <= 0:
        return splits
    for t in range(1, k):
        test = np.arange(t * fold, min((t + 1) * fold, n))
        train = np.arange(0, t * fold)
        train = train[train <= (t * fold - 1 - embargo)]
        if len(train) < 200:
            continue
        splits.append((train, test))
    return splits


# ---------------------------------------------------------------------------
# 8. ISLEM SIMULASYONU
# ---------------------------------------------------------------------------
def simulate(feat, idx, z_th, direction):
    o = feat["open"][idx]
    cl = feat["close"][idx]
    lo = feat["low"][idx]
    hi = feat["high"][idx]
    z = feat["z"][idx]
    atr = feat["atr"][idx]
    n = len(o)
    if n < 63:
        return []
    trades = []
    i = 62
    while i < n - 1:
        zi = float(z[i])
        atr_i = float(atr[i])
        if not (np.isfinite(zi) and np.isfinite(atr_i) and atr_i > 0):
            i += 1
            continue
        if direction == "LONG":
            fired = (zi <= -z_th) and (z[i - 1] < zi) and \
                (zi > float(np.min(z[i - 3:i])))
        else:
            fired = (zi >= z_th) and (z[i - 1] > zi) and \
                (zi < float(np.max(z[i - 3:i])))
        if not fired:
            i += 1
            continue
        entry = float(o[i])
        sl = entry - ATR_SL_MULT * atr_i if direction == "LONG" \
            else entry + ATR_SL_MULT * atr_i
        ep = None
        j = min(i + TIME_STOP_BARS, n - 1)
        k = i + 1
        while k < min(i + TIME_STOP_BARS, n):
            if direction == "LONG":
                if lo[k] <= sl:
                    ep = sl
                    j = k
                    break
                if z[k] >= 0.0:
                    ep = cl[k]
                    j = k
                    break
            else:
                if hi[k] >= sl:
                    ep = sl
                    j = k
                    break
                if z[k] <= 0.0:
                    ep = cl[k]
                    j = k
                    break
            k += 1
        if ep is None:
            ep = cl[j]
        gross = (ep - entry) / entry if direction == "LONG" \
            else (entry - ep) / entry
        trades.append(gross - 2.0 * FEE_TAKER - 2.0 * SLIPPAGE)
        i = j + 1
    return trades


# ---------------------------------------------------------------------------
# 9. EXECUTION ROUTER — MARKET mi LIMIT mi? (v5.3: LOB disaridan alinabilir)
#    HICBIR EMIR GONDERMEZ; yalnizca sinyali etiketler.
# ---------------------------------------------------------------------------
def execution_router(symbol, direction, target_usd, bids=None, asks=None):
    if bids is None or asks is None:
        bids, asks = fetch_order_book(symbol)
    imb, depth_usd, spread_bps = lob_imbalance(bids, asks)
    if bids is None or asks is None or bids.empty or asks.empty:
        return ("MARKET", float("nan"), "taker", None, None, imb, spread_bps)
    best_bid = float(bids["price"].iloc[0])
    best_ask = float(asks["price"].iloc[0])
    # Router esikleri (0.10 OBI, 2x derinlik, 5 bps): MIRAS SABIT — kalibre edilmedi
    bias = (imb > 0.10 and direction == "LONG") or \
        (imb < -0.10 and direction == "SHORT")
    depth_ok = depth_usd >= target_usd * 2.0
    if bias and depth_ok and spread_bps < 5.0:
        if direction == "LONG":
            return ("LIMIT", best_bid, "maker", best_bid, best_ask,
                    imb, spread_bps)
        return ("LIMIT", best_ask, "maker", best_bid, best_ask,
                imb, spread_bps)
    if direction == "LONG":
        return ("MARKET", best_ask, "taker", best_bid, best_ask,
                imb, spread_bps)
    return ("MARKET", best_bid, "taker", best_bid, best_ask,
            imb, spread_bps)


# ---------------------------------------------------------------------------
# 10. SINYAL MOTORU
# ---------------------------------------------------------------------------
def signal_engine(symbol, df_4h, df_15m, btc_4h, btc_15m, eth_4h, eth_15m,
                  target_usd=TARGET_USD):
    print(f"\n=== {symbol} ===")
    cb = corr_stats(df_15m["close"], btc_15m["close"])
    if cb:
        print(f"  Korelasyon alt-BTC: r={cb['r']:.3f} "
              f"(p={cb['p']:.4f}, n={cb['n']})")
    if symbol != "ETH/USDT":
        ce = corr_stats(df_15m["close"], eth_15m["close"])
        if ce:
            print(f"  Korelasyon alt-ETH: r={ce['r']:.3f} "
                  f"(p={ce['p']:.4f}, n={ce['n']})")
    state, state_conf = regime_detector(df_15m["close"], df_4h["close"])
    btc_state, _ = regime_detector(btc_15m["close"], btc_4h["close"])
    print(f"  Rejim: {state} (guven={state_conf:.2f}) | BTC rejimi: {btc_state}")
    fr_df, oi = fetch_funding_oi(symbol)
    fr_latest = 0.0
    if not fr_df.empty and "fundingRate" in fr_df.columns:
        fr_latest = float(fr_df["fundingRate"].iloc[-1])
    oi_str = f"{oi:,.1f}" if np.isfinite(oi) else "yok"
    print(f"  Funding: {fr_latest * 100:.4f}% (8h) | OI: {oi_str}")

    trades = fetch_recent_trades(symbol)
    # v5.3: LOB tek cagirilir; hem uyari katmaninda hem router'da kullanilir
    bids, asks = fetch_order_book(symbol)

    # --- ANLIK UYARILAR (v5.3) — tick/LOB oncu; hacim bileseni kapanmis 15M ---
    score15, note15 = pump_anomaly(df_15m["volume"])
    # v5.3.2: yon tespiti TEK kez hesaplanir. (v5.3/v5.3.1'de ayni girdiyle
    # iki kez cagriliyordu — git f34721b, eski satirlar 702 ve 721; kaldirildi.)
    yon, yon_move = pump_dump_direction(trades, df_15m["close"])
    mw = realtime_warnings(symbol, trades, df_15m["close"], bids, asks,
                           score15, note15, yon, yon_move)
    if mw:
        for w in mw:
            print(f"  ONCU UYARI: {w}")
    else:
        print("  ONCU UYARI: yok (olumlu)")

    # --- Pump/Dump vetosu (v5.3: tick teyidi artik tanimli) ---
    note = note15
    src = "OHLCV/15M(kapanmis)"
    if note15 in ("NORMAL", "WATCH"):
        tscore = tick_confirm_score(symbol, trades)
        if tscore is not None:
            src = "OHLCV/15M(kapanmis) + tick teyit"
            print(f"  Tick teyit: z={tscore:.2f} (esik {PUMP_TICK_WATCH})")
            if note15 == "WATCH" and tscore >= PUMP_TICK_WATCH:
                note = "PUMP_OR_DUMP_RISK"
    print(f"  Pump/Dump oncu: {note} | score={score15:.2f} | kaynak={src}")
    if note == "VERI_YOK":
        print("  Yon izleme: VERI YOK — hacim serisi anomali olcumu icin "
              "yetersiz (eksik veri 'anomali yok' sayilmaz)")
    elif note != "PUMP_OR_DUMP_RISK":
        print(f"  Yon izleme: {yon} ({yon_move * 100:+.2f}%) - anomali yok, "
              f"izlemede")
    else:
        if yon == "DUMP":
            print(f"  -> VETO: DUMP oncu uyarisi (satis dalgasi) | "
                  f"hareket={yon_move * 100:+.2f}%")
        elif yon == "PUMP":
            print(f"  -> VETO: PUMP oncu uyarisi (sisme/satilabilir fazi) | "
                  f"hareket={yon_move * 100:+.2f}%")
        else:
            print(f"  -> VETO: PUMP/DUMP riski, yon belirsiz "
                  f"(hareket={yon_move * 100:+.2f}%)")
        return

    if state in ("BULL", "BEAR") and btc_state != state:
        print(f"  -> Iptal: BTC {btc_state} ile alt {state} uyumsuz.")
        return

    direction = "LONG" if state == "BULL" else \
        "SHORT" if state == "BEAR" else None
    if direction is None:
        print("  -> Rejim CALM/UNKNOWN.")
        return

    df = df_15m.copy()
    close = df["close"].astype(float)
    sma20 = close.rolling(window=20).mean()
    sd20 = close.rolling(window=20).std(ddof=0)
    df["z"] = ((close - sma20) / (sd20 + 1e-12)).shift(periods=1)
    hl = (df["high"] - df["low"]).abs()
    hc = (df["high"] - close.shift(periods=1)).abs()
    lc = (df["low"] - close.shift(periods=1)).abs()
    tr_df = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["atr"] = tr_df.rolling(ATR_LEN).mean().shift(periods=1)
    df["target"] = sma20
    df = df.dropna(subset=["z", "atr"])
    if len(df) < 700:
        print(f"  -> Yetersiz veri ({len(df)} mum).")
        return
    feat = {k: df[k].to_numpy(dtype=float) for k in
            ["open", "close", "low", "high", "z", "atr"]}
    rule_trades = {z: [] for z in Z_GRID}
    folds = 0
    for train_idx, test_idx in walkforward_splits(len(df), N_FOLDS, EMBARGO):
        for zt in Z_GRID:
            rule_trades[zt].extend(simulate(feat, test_idx, zt, direction))
        folds += 1
    if folds == 0:
        print("  -> Walk-forward split yok.")
        return
    stats = {zt: oos_stats(rule_trades[zt]) for zt in Z_GRID}
    pvals = {}
    for zt, s in stats.items():
        if s is not None:
            pvals[zt] = 2.0 * (1.0 - norm_cdf(abs(s["t"])))
    if not pvals:
        print("  -> Yeterli OOS yok.")
        return
    keys = list(pvals.keys())
    accepted = fdr_bh([pvals[k] for k in keys], ALPHA)
    accepted_z = [zt for zt, ok in zip(keys, accepted) if ok]
    p_max = bootstrap_max_t(rule_trades)
    print(f"  WF fold: {folds} (genisleyen pencere+embargo) | BH-FDR kabul: "
          f"{accepted_z if accepted_z else 'yok'} | "
          f"max-t bootstrap p: {p_max:.3f}")
    if not accepted_z or p_max >= ALPHA:
        print("  -> Anti-overfit kapi kapali.")
        return
    best_z = max(accepted_z, key=lambda zt: stats[zt]["mean"])
    best_stat = stats[best_z]
    cur = df.iloc[-1]
    prev = df.iloc[-2]
    zi = float(cur["z"])
    atr_i = float(cur["atr"])
    if direction == "LONG":
        fired = (zi <= -best_z) and (zi > -4.0) and (float(prev["z"]) < zi) and \
            (zi > float(np.min(df["z"].iloc[-4:-1])))
    else:
        fired = (zi >= best_z) and (zi < 4.0) and (float(prev["z"]) > zi) and \
            (zi < float(np.max(df["z"].iloc[-4:-1])))
    if not fired:
        print(f"  -> Kenar onayli; tetik yok (z={zi:.2f}, esik={best_z}).")
        return
    order_type, ref_px, role, best_bid, best_ask, imb, spread_bps = \
        execution_router(symbol, direction, target_usd, bids, asks)
    last_close = float(cur["close"])
    target_px = float(cur["target"])
    sl_px = last_close - ATR_SL_MULT * atr_i if direction == "LONG" \
        else last_close + ATR_SL_MULT * atr_i
    print(f"  >>> {direction} SINYALI (WF+FDR+bootstrap onayli) <<<")
    print(f"  Referans (son kapanis): {last_close:.4f}")
    if order_type == "MARKET":
        px_str = f"{ref_px:.4f}" if np.isfinite(ref_px) else f"{last_close:.4f}"
        side_str = "ASK'tan al" if direction == "LONG" else "BID'den sat"
        print(f"  GIRIS [MARKET/taker]: {px_str} -> {side_str}")
    else:
        if direction == "LONG":
            print(f"  GIRIS [LIMIT/maker]: {ref_px:.4f} -> "
                  f"best BID'e alis emri; {LIMIT_TIMEOUT_SEC:.0f} sn "
                  f"dolmazsa MARKET'e gec")
        else:
            print(f"  GIRIS [LIMIT/maker]: {ref_px:.4f} -> "
                  f"best ASK'a satis emri; {LIMIT_TIMEOUT_SEC:.0f} sn "
                  f"dolmazsa MARKET'e gec")
    if best_ask is not None and best_bid is not None:
        print(f"  (best bid={best_bid:.4f} | best ask={best_ask:.4f})")
    print(f"  CIKIS HEDEF [Z=0, limit]: {target_px:.4f}")
    print(f"  STOP [market]: {sl_px:.4f} ({ATR_SL_MULT} x ATR)")
    print(f"  ZAMAN STOPU: {TIME_STOP_BARS} bar (~12 saat)")
    print(f"  OOS: beklenen net %{best_stat['mean'] * 100:.3f}/islem | "
          f"kazanma %{best_stat['win'] * 100:.1f} | PF={best_stat['pf']:.2f} | "
          f"n={best_stat['n']}")
    print(f"  LOB: OBI={imb:.3f} | spread={spread_bps:.2f} bps")
    if abs(fr_latest) * 1e4 >= FR_TOLERANCE_BPS:
        print(f"  ONCU IPUCU: funding agir ({fr_latest * 100:.4f}%)")


# ---------------------------------------------------------------------------
# 11. ANA DONGU
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("BTC Karargah v5.3.2 — oncu veri katmani (karar-destek; emir gondermez)")
    print("=" * 70)
    # v5.3.2 (K25): tamamlanma beyani KOSULSUZ degil — sayilarak verilir.
    tamam, atlanan = 0, 0
    kurulum_hatasi = False
    try:
        selftest()
        btc_4h = fetch_ohlcv("BTC/USDT", TF_4H, LIMIT_4H)
        btc_15m = fetch_ohlcv("BTC/USDT", TF_15M, LIMIT_15M)
        eth_4h = fetch_ohlcv("ETH/USDT", TF_4H, LIMIT_4H)
        eth_15m = fetch_ohlcv("ETH/USDT", TF_15M, LIMIT_15M)
        for alt in SYMBOLS:
            try:
                a4 = fetch_ohlcv(alt, TF_4H, LIMIT_4H)
                a15 = fetch_ohlcv(alt, TF_15M, LIMIT_15M)
                signal_engine(alt, a4, a15, btc_4h, btc_15m,
                              eth_4h, eth_15m, TARGET_USD)
                tamam += 1
            except Exception:
                traceback.print_exc()
                atlanan += 1
                print(f"  [{alt}] atlandi.")
    except Exception:
        kurulum_hatasi = True
        traceback.print_exc()
    if kurulum_hatasi:
        print(f"\nTarama BASARISIZ — kurulum/veri hatasi "
              f"({tamam}/{len(SYMBOLS)} sembol tarandi).")
    elif atlanan == 0 and tamam == len(SYMBOLS):
        print(f"\nTarama tamamlandi ({tamam}/{len(SYMBOLS)} sembol).")
    else:
        print(f"\nTarama KISMEN tamamlandi: {tamam} tamam, "
              f"{atlanan} atlandi ({len(SYMBOLS)} sembol).")

# --------------------------------------------------------------------
# DOGRULAMA PLANI (yeni esikler HIPOTEZDIR — olculmeden "cozuldu" denmez):
#   (a) tarama modunda art arda kosulup hicbir NameError/TypeError
#       cikmadigi kaydedilir,
#   (b) her sembol icin oncu uyari sayisi,
#   (c) uyari sonrasi 15-60 dk icindeki gerceklesme orani (sahte pozitif),
#   (d) hareket olup uyari cikmayan durumlar (sahte negatif).
# Bu olcumler yapilmadan PUMP_TICK_WATCH / TICK_CONFIRM_* / V_REVERSAL_*
# degerlerinin "basarili" oldugu iddia EDILEMEZ.
# --------------------------------------------------------------------
