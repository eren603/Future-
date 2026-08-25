# KARARGAH TEK v2.4 — motor (v5.4) + META3 katmani (v2.4) TEK DOSYADA
# ====================================================================
# (file content with improvements: centralized indicators, robust stop/target sizing)
# See header comments in the file for provenance and design notes.
# ====================================================================

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
# v5.4.0 (B3 — denetci duzeltmesi): pump_dump_direction icindeki 0.005
# literali TEKILLESTIRILDI; tek kaynak bu sabittir. DEGER DEGISMEDI ve
# davranis esdegerligi testle kanitlandi (birlestirici kosusu).
# MIRAS SABIT — kalibre edilmedi.
PDD_MOVE_ESIK = 0.005

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

# --- v5.4.0 (ajanA) lead-lag / winsorize parametreleri (HIPOTEZ) ---
# Ucu de HIPOTEZ — bu kosunun verisinden turetilmis DEGILLER; canli
# olcumle kalibre edilmeden "dogru deger" iddiasi tasimazlar.
LEAD_LAG_MAX_LAG = 8    # HIPOTEZ — kalibre edilmedi: 15M barda ±8 bar = ±2 saat tarama penceresi
WINSOR_Q_LOW = 0.005    # HIPOTEZ — kalibre edilmedi (oneri: alt %0.5 kantil)
WINSOR_Q_HIGH = 0.995   # HIPOTEZ — kalibre edilmedi (oneri: ust %99.5 kantil)

# --- v5.4.0 (ajanC) RSI parametreleri (HIPOTEZ) ---
# 14 ve 30/70 literatur gelenegidir, bu depoda OLCULEREK kalibre
# edilmemistir; kalibrasyonu WF+FDR+bootstrap kapilarindan gecen
# kurallarin secimi saglar (izgara-ici secim), sabitin kendisi serbestce
# oynanmaz.
RSI_LEN = 14          # HIPOTEZ — RSI uzunlugu; kalibre edilmedi
RSI_LONG_MAX = 30.0   # HIPOTEZ — LONG tetikte RSI < 30 bandi; kalibre edilmedi
RSI_SHORT_MIN = 70.0  # HIPOTEZ — SHORT tetikte RSI > 70 bandi; kalibre edilmedi

# v5.4.0 (ajanA G1): hedef sembol BTCUSDT listede yoktu, hic taranmiyordu;
# basa eklendi. Oz-referans yollari signal_engine icinde temizlendi.
SYMBOLS = [
    "BTC/USDT",  # G1: kullanici gereksinimi — hedef sembol taramaya dahil
    "ETH/USDT", "XRP/USDT", "LINK/USDT", "DOGE/USDT", "DOT/USDT",
    "AVAX/USDT", "SUSHI/USDT", "ZEC/USDT", "ETC/USDT", "FIL/USDT",
    "AAVE/USDT",
]

# --- Robustness constants to avoid vanishingly small stops/targets (new) ---
MIN_STOP_PCT = 0.001            # minimum stop distance as fraction of price (0.1%)
MIN_TARGET_PCT = 0.0015         # minimum target distance as fraction of price (0.15%)
MIN_LIMIT_OFFSET_PCT = 0.00025  # minimum offset for limit price (0.025%)


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


# v5.4.0 (ajanA G3): getiri-tabanli istatistiklerin (korelasyon, lead-lag)
# tek-bar uc degerlere karsi duyarliligini sinirlamak. Kantil SINIRLARI
# (q_low/q_high) HIPOTEZ etiketli sabittir; kirpma ESIKLERI ise her
# kosuda O KOSUNUN serisinden hesaplanir (sabit fiyat siniri yok).
# KAPSAM DISI (K12 geregi gerekceli): HACIM serisine ve pump_anomaly
# girdisine UYGULANMAZ — pump tespitinin hedefi spike'in KENDISIdir;
# winsorize spike'i kirparak tespiti korlestirir. simulate/oos_stats
# islem PnL'lerine de uygulanmaz (gercek maliyet/kayip kirpilamaz).
def winsorize(returns, q_low=WINSOR_Q_LOW, q_high=WINSOR_Q_HIGH):
    """Getiri serisini kendi [q_low, q_high] kantillerine kirpar.

    YALNIZ getiri-tabanli istatistik girdisi icindir (corr_stats,
    lead_lag_stats). Hacim/pump yoluna BAGLANMAZ (gerekce ustte).
    Kantil esikleri seriden hesaplanir; bos/yetersiz seride seri
    oldugu gibi doner (davranis degistirmeden gecirir)."""
    r = pd.Series(returns).astype(float)
    valid = r.dropna()
    if len(valid) < 3:
        return r
    lo = float(valid.quantile(q_low))
    hi = float(valid.quantile(q_high))
    return r.clip(lower=lo, upper=hi)


# v5.4.0 (ajanA G3): korelasyon girdisi getirileri winsorize edilir.
# Cikti sozlesmesi ({"n","r","p"}) ve 50-gozlem alt siniri AYNEN korundu
# (K22/K23: kapi gevsetilmedi/sikilmadi).
def corr_stats(alt_close, ref_close, n_max=672):
    d = pd.concat([log_returns(alt_close), log_returns(ref_close)],
                  axis=1).dropna().tail(n_max)
    if len(d) < 50:
        return None
    # G3: winsorize pencere ICINDEKI veriden kantille (o kosunun verisi)
    a = winsorize(d.iloc[:, 0])
    b = winsorize(d.iloc[:, 1])
    r = float(a.corr(b))
    if not np.isfinite(r):
        return None
    zf = 0.5 * math.log((1.0 + r) / max(1.0 - r, 1e-12))
    se = 1.0 / math.sqrt(len(d) - 3)
    p = 2.0 * (1.0 - norm_cdf(abs(zf) / se))
    return {"n": len(d), "r": r, "p": p}


# v5.4.0 (ajanA G2): oncu-ardil iliskisi. Cikti YALNIZ RAPOR icindir —
# hicbir kapi/veto/karar bu fonksiyona baglanmaz (kanitsiz yeni kapi
# K22'ye takilir; dogrulanmadan karar bileseni yapilamaz).
# Lag isareti sozlesmesi: pozitif lag = REF ONCU (alt_t, ref_{t-lag}
# ciftinin korelasyonu), negatif lag = ALT ONCU.
def lead_lag_stats(alt_close, ref_close, max_lag=LEAD_LAG_MAX_LAG,
                   n_max=672):
    """Log-getirilerde capraz-korelasyon taramasi, lag -max..+max.

    RAPOR-ONLY: karara girmez. Doner: en iyi lag (|r| maksimumu), o
    lagdeki r + Fisher-z p degeri, lag-0 r'si ve asimetri:
      asimetri = mean(r[lag>0]) - mean(r[lag<0])
      (pozitif = ref gecikmeli->alt korelasyonu baskin = REF ONCU).
    max_lag HIPOTEZ etiketli sabittir (kalibre edilmedi). Getiriler
    winsorize edilir (G3). Yetersiz pencerede None (VERI YOK)."""
    d = pd.concat([log_returns(alt_close), log_returns(ref_close)],
                  axis=1).dropna().tail(n_max)
    # veri-yeterlilik korkulugu: corr_stats'in mevcut 50 tabani +
    # her iki uctaki lag tuketimi (gevsetme degil, ek guvence)
    if len(d) < 50 + 2 * max_lag:
        return None
    a = winsorize(d.iloc[:, 0])   # alt getirileri
    b = winsorize(d.iloc[:, 1])   # ref getirileri
    rows = {}
    for lag in range(-max_lag, max_lag + 1):
        pair = pd.concat([a, b.shift(lag)], axis=1).dropna()
        if len(pair) < 50:
            continue
        r = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
        if np.isfinite(r):
            rows[lag] = (r, len(pair))
    if not rows or 0 not in rows:
        return None
    best_lag = max(rows, key=lambda k: abs(rows[k][0]))
    r_best, n_best = rows[best_lag]
    zf = 0.5 * math.log((1.0 + r_best) / max(1.0 - r_best, 1e-12))
    se = 1.0 / math.sqrt(max(n_best - 3, 1))
    p = 2.0 * (1.0 - norm_cdf(abs(zf) / se))
    ref_leads = [rows[k][0] for k in rows if k > 0]
    alt_leads = [rows[k][0] for k in rows if k < 0]
    asym = float("nan")
    if ref_leads and alt_leads:
        asym = float(np.mean(ref_leads) - np.mean(alt_leads))
    return {"best_lag": int(best_lag), "r": r_best, "n": n_best, "p": p,
            "r0": rows[0][0], "asym": asym, "max_lag": int(max_lag)}


# v5.4.0 (ajanC CAPA-2): Wilder RSI — lookahead'siz.
def wilder_rsi(close, length=None):
    """Wilder RSI — lookahead'siz (.shift(1) disiplini z ile AYNI).

    Duzlestirme: EWM(alpha=1/length, adjust=False) — Wilder'in ozyinelemeli
    ortalamasi (RMA). Tohum: pandas adjust=False geregi ilk gozlem degeri
    (klasik Wilder'daki ilk-14-SMA tohumu DEGIL; fark geometrik hizla soner).
    Bu tohum tercihi bir UYGULAMA HIPOTEZIDIR ve rapora islenmistir.
    min_periods=length: ilk `length` degisim gorulmeden RSI uretilmez (NaN).

    DONUS: .shift(periods=1) UYGULANMIS seri — bar i'deki deger yalniz
    <= i-1 kapanislarindan hesaplanmistir. Boylece simulate() bar i'de
    tetigi degerlendirirken ve canli blok son KAPANMIS barda calisirken
    olusmakta olan bilgi kullanilamaz (mevcut z kolonuyla ayni sozlesme).
    """
    if length is None:
        length = RSI_LEN
    c = close.astype(float)
    delta = c.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False,
                        min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False,
                        min_periods=length).mean()
    rs = avg_gain / (avg_loss + 1e-12)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi.shift(periods=1)


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
    v5.3 TAMIR: w = w.copy() ve .sum() parantezleri eklendi.
    v5.4.0 (B3): 0.005 literali PDD_MOVE_ESIK sabitine tekillestirildi
    (deger ayni; davranis esdegerligi testle kanitli)."""
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
    if move <= -PDD_MOVE_ESIK:
        return "DUMP", move
    if move >= PDD_MOVE_ESIK:
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


# --- v5.4.0 (ajanB) BILESIK ONCU SKOR — RAPOR-ONLY -------------------------
# HIPOTEZ: esit agirlik (w = 1/6). Olculmus agirlik YOK; canli olcumle
# kalibre edilmeden hicbir kanalin ustunlugu iddia edilmez.
# Skor HICBIR veto/karar kapisina bagli DEGILDIR (rapor-only).
KOMPOZIT_KANALLAR = ("pump", "tick", "lob", "funding", "yon", "oi")
KOMPOZIT_AGIRLIK = 1.0 / len(KOMPOZIT_KANALLAR)  # HIPOTEZ: esit agirlik
KOMPOZIT_MIN_KAPSAM = 0.5  # gorev tanimindan; RAPOR esigi (karar kapisi DEGIL)


def composite_leading_score(kanallar):
    """BILESIK ONCU GOSTERGE SKORU — RAPOR-ONLY, HIPOTEZ.

    Girdi sozlugu (eksik/olculemeyen alan None birakilir):
      pump_skor : pump_anomaly() skoru (z)   | pump_not: ayni cagrinin notu
      tick_z    : tick_confirm_score() z'si (son KAPANMIS dakika)
      obi       : lob_imbalance() OBI'si — (b-a)/(b+a), tanim geregi [-1,+1]
      funding   : son funding orani (oran; 0.0001 = 1 bps)
      oi      : acik faiz ANLIK goruntusu (yalniz MEVCUDIYET kanali)
      yon_move  : pump_dump_direction() hareketi (oran)

    NORMALIZASYON FORMULLERI (acik; olcekler MEVCUT sabitlerden):
      yon     v = clip(yon_move / PDD_MOVE_ESIK, -1, +1)
              (PDD_MOVE_ESIK = pump_dump_direction'daki mevcut PUMP/DUMP
               esigi; v5.4.0'da tekillestirilmis TEK kaynak)
      pump    v = isaret(yon_move) * clip(max(pump_skor,0)/PUMP_THRESHOLD_Z, 0, 1)
              (negatif z = sakin hacim, TERS YON KANITI DEGIL -> 0'a kirpilir;
               yon isareti olculen hareketten alinir — hacim z'si yonsuzdur)
      tick    v = isaret(yon_move) * clip(max(tick_z,0)/PUMP_TICK_WATCH, 0, 1)
              (ayni isaret kurali; olcek mevcut hipotez esigi 2.5)
      lob     v = clip(obi, -1.0, +1.0)   (zaten bantta; kirpma yalniz koruma)
      funding v = -clip(funding*1e4 / FR_TOLERANCE_BPS, -1, +1)
              (KONTRARYEN ISARET HIPOTEZDIR: pozitif funding = kalabalik
               long = asagi yonlu oncu baski VARSAYIMI; olculmus dogrulama YOK)
      oi      YONSUZ kanal: TEK anlik goruntudan yon OLCULEMEZ (fark serisi
              yok). Mevcutsa yalniz KAPSAMA katilir, skora katilmaz; yokssa
              kapsami dusurur. Yon icin 0 SAYILMAZ (eksik != notr).

    Kurallar:
      - Eksik kanal atlanir; kapsam = mevcut kanal agirligi / toplam agirlik.
      - Skor = mevcut YONLU kanallarin agirlikli ORTALAMASI (bant [-1,+1]).
      - kapsam < KOMPOZIT_MIN_KAPSAM ise skor rapor edilmez ("VERI YOK").
      - yon_move tam 0.0 ise bu OLCULMUS sifirdir (eksik degil): yon kanali
        0 katkiyla mevcuttur, pump/tick isareti 0 olur.
      - v5.4.0 (B2 — denetci duzeltmesi): YONLU-KAPSAM ("yonlu_kapsam")
        ayrica dondurulur ve cikti satirinda gosterilir — OI'nin yonsuz
        mevcudiyeti rapor-esigi paydasini SESSIZCE sisiremesin diye
        (okur yonlu kanit payini ayrica gorur). OI paydada birakildi:
        rapor esigi davranisi ve onceden sabitlenmis kabul testleri
        korunur (test bulguya uydurulamaz, K23); sissirme gorunurlukle
        cozulur.
    """
    def _clip(x, lo, hi):
        return max(lo, min(hi, float(x)))

    def _isaret(x):
        return 0.0 if x == 0 else (1.0 if x > 0 else -1.0)

    def _var(x):
        return x is not None and math.isfinite(float(x))

    k = kanallar or {}
    pump_skor = k.get("pump_skor")
    pump_not = k.get("pump_not")
    tick_z = k.get("tick_z")
    obi = k.get("obi")
    funding = k.get("funding")
    oi = k.get("oi")
    yon_move = k.get("yon_move")

    degerler = {}          # yonlu kanal -> normalize deger
    mevcut = set()         # kapsama giren kanallar (oi dahil)

    if _var(yon_move):
        mevcut.add("yon")
        degerler["yon"] = _clip(float(yon_move) / PDD_MOVE_ESIK, -1.0, 1.0)
    if _var(pump_skor) and pump_not not in (None, "VERI_YOK") and _var(yon_move):
        mevcut.add("pump")
        degerler["pump"] = _isaret(float(yon_move)) * _clip(
            max(float(pump_skor), 0.0) / PUMP_THRESHOLD_Z, 0.0, 1.0)
    if _var(tick_z) and _var(yon_move):
        mevcut.add("tick")
        degerler["tick"] = _isaret(float(yon_move)) * _clip(
            max(float(tick_z), 0.0) / PUMP_TICK_WATCH, 0.0, 1.0)
    if _var(obi):
        mevcut.add("lob")
        degerler["lob"] = _clip(float(obi), -1.0, 1.0)
    if _var(funding):
        mevcut.add("funding")
        degerler["funding"] = -_clip(
            float(funding) * 1e4 / FR_TOLERANCE_BPS, -1.0, 1.0)
    if _var(oi):
        mevcut.add("oi")   # yonsuz: yalniz kapsam, skora katki YOK

    kapsam = len(mevcut) * KOMPOZIT_AGIRLIK
    # v5.4.0 (B2): yonlu kapsam = yalniz YONLU (skora katki verebilen)
    # kanallarin agirligi; OI buna girmez. Rapor esigi DEGISMEDI (toplam
    # kapsam uzerinden) — bu alan yalniz gorunurluk icindir.
    yonlu_kapsam = len(degerler) * KOMPOZIT_AGIRLIK
    skor = None
    katki = {}
    if degerler:
        top_w = len(degerler) * KOMPOZIT_AGIRLIK
        skor = sum(KOMPOZIT_AGIRLIK * v for v in degerler.values()) / top_w
        katki = {ad: KOMPOZIT_AGIRLIK * v / top_w
                 for ad, v in degerler.items()}
    rapor = (kapsam >= KOMPOZIT_MIN_KAPSAM) and (skor is not None)
    return {
        "skor": skor if rapor else None,   # rapor edilebilir skor
        "ham_skor": skor,                  # dusuk kapsamda da hesap izi
        "kapsam": kapsam,
        "yonlu_kapsam": yonlu_kapsam,      # v5.4.0 (B2): OI'siz kapsam
        "katki": katki,                    # toplami == skor (yonlu kanallar)
        "mevcut": sorted(mevcut),
        "eksik": sorted(set(KOMPOZIT_KANALLAR) - mevcut),
        "oi_mevcut": "oi" in mevcut,
        "rapor": rapor,
    }


def composite_line(sonuc):
    """signal_engine ciktisina yazilacak TEK bilgi satiri (rapor-only).
    v5.4.0 (B2): yonlu-kapsam ayrica gosterilir."""
    kap = sonuc["kapsam"]
    yk = sonuc["yonlu_kapsam"]
    if not sonuc["rapor"]:
        eksik = ",".join(sonuc["eksik"]) or "yok"
        return (f"BILESIK ONCU SKOR (hipotez, rapor-only): "
                f"VERI YOK (kapsam {kap:.2f}; yonlu {yk:.2f}; eksik: {eksik})")
    parca = [f"{ad} {sonuc['katki'][ad]:+.2f}" for ad in sorted(sonuc["katki"])]
    if sonuc["oi_mevcut"]:
        parca.append("oi mevcut(yonsuz)")
    return (f"BILESIK ONCU SKOR (hipotez, rapor-only): {sonuc['skor']:+.2f} | "
            f"kapsam {kap:.2f} (yonlu {yk:.2f}) | katki: {', '.join(parca)}")


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
#    v5.4.0 (ajanC CAPA-3): IMZA DEGISTI — simulate(feat, idx, z_th,
#    rsi_on, direction). Degisiklik SADECE su: rsi_on=True ise tetik ani
#    feat["rsi"] (shift'li) degerine RSI<30 (LONG) / RSI>70 (SHORT) sarti
#    eklenir. Giris/cikis/stop/zaman-stopu/ucret mantigi AYNEN korunur;
#    rsi_on=False kurallar icin davranis ESKISIYLE BIREBIR AYNIDIR.
# ---------------------------------------------------------------------------
def simulate(feat, idx, z_th, rsi_on, direction):
    o = feat["open"][idx]
    cl = feat["close"][idx]
    lo = feat["low"][idx]
    hi = feat["high"][idx]
    z = feat["z"][idx]
    atr = feat["atr"][idx]
    rs = feat["rsi"][idx]          # YAMA (ajanC): shift'li Wilder RSI
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
        # YAMA (ajanC): RSI filtresi — kural izgarasinin ikinci ekseni.
        # rsi_on=False kurallar icin davranis ESKISIYLE BIREBIR AYNI.
        if fired and rsi_on:
            ri = float(rs[i])
            if not np.isfinite(ri):
                fired = False
            elif direction == "LONG":
                fired = ri < RSI_LONG_MAX
            else:
                fired = ri > RSI_SHORT_MIN
        if not fired:
            i += 1
            continue
        entry = float(o[i])
        # NEW: robust stop sizing (use max of ATR-based and MIN_STOP_PCT * price)
        stop_by_atr = ATR_SL_MULT * atr_i
        stop_by_pct = entry * MIN_STOP_PCT
        stop_dist = max(stop_by_atr, stop_by_pct)
        sl = entry - stop_dist if direction == "LONG" else entry + stop_dist
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
#    Modified to nudge limit price away from top-of-book to avoid immediate crossing.
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
        # pick a limit price but nudge it slightly away from the immediate best
        if direction == "LONG":
            offset = max(best_bid * MIN_LIMIT_OFFSET_PCT, best_bid * 1e-6)
            limit_px = max(0.0, best_bid - offset)
            return ("LIMIT", limit_px, "maker", best_bid, best_ask,
                    imb, spread_bps)
        else:
            offset = max(best_ask * MIN_LIMIT_OFFSET_PCT, best_ask * 1e-6)
            limit_px = best_ask + offset
            return ("LIMIT", limit_px, "maker", best_bid, best_ask,
                    imb, spread_bps)
    if direction == "LONG":
        return ("MARKET", best_ask, "taker", best_bid, best_ask,
                imb, spread_bps)
    return ("MARKET", best_bid, "taker", best_bid, best_ask,
            imb, spread_bps)


# ---------------------------------------------------------------------------
# 10. SINYAL MOTORU
#     v5.4.0 BIRLESIK: ajanA (oz-referans temizligi + lead-lag satiri),
#     ajanB (bilesik skor satiri + tscore tekillestirme), ajanC (22-kural
#     izgarasi + canli RSI tetigi). Degismeyen satirlar v5.3.2 ile birebir.
# ---------------------------------------------------------------------------

# Centralized leading indicator computation to avoid duplicated contradictory calls
def compute_leading_indicators(symbol, df_4h, df_15m, btc_4h, btc_15m, target_usd=TARGET_USD):
    """Compute and return a dict of leading indicators and fetched data for a symbol.

    This centralizes fetches and leading calculations, so caller can reuse results.
    """
    out = {}
    trades = fetch_recent_trades(symbol)
    bids, asks = fetch_order_book(symbol)
    fr_df, oi = fetch_funding_oi(symbol)
    fr_latest = 0.0
    fr_var = (not fr_df.empty) and ("fundingRate" in fr_df.columns)
    if fr_var:
        fr_latest = float(fr_df["fundingRate"].iloc[-1])

    score15, note15 = pump_anomaly(df_15m["volume"])
    yon_pd, yon_move = pump_dump_direction(trades, df_15m["close"])
    tscore = tick_confirm_score(symbol, trades)

    obi, depth_usd, spread_bps = lob_imbalance(bids, asks)
    _oi = oi if np.isfinite(oi) else None

    komp = composite_leading_score({
        "pump_skor": score15, "pump_not": note15,
        "tick_z": tscore,
        "obi": obi if (bids is not None and asks is not None and not bids.empty and not asks.empty) else None,
        "funding": fr_latest if fr_var else None,
        "oi": _oi,
        "yon_move": yon_move,
    })

    out.update({
        "trades": trades, "bids": bids, "asks": asks,
        "fr_df": fr_df, "fr_latest": fr_latest, "oi": oi,
        "score15": score15, "note15": note15,
        "yon": yon_pd, "yon_move": yon_move, "tscore": tscore,
        "obi": obi, "depth_usd": depth_usd, "spread_bps": spread_bps,
        "komp": komp
    })
    return out


def signal_engine(symbol, df_4h, df_15m, btc_4h, btc_15m, eth_4h, eth_15m,
                  target_usd=TARGET_USD):
    print(f"\n=== {symbol} ===")
    if symbol == "BTC/USDT":
        print("  Korelasyon alt-BTC: atlandi (sembol referansin kendisi; "
              "kendine-korelasyon r=1.0 bilgi tasimaz)")
    else:
        cb = corr_stats(df_15m["close"], btc_15m["close"])
        if cb:
            print(f"  Korelasyon alt-BTC: r={cb['r']:.3f} "
                  f"(p={cb['p']:.4f}, n={cb['n']})")
        ll = lead_lag_stats(df_15m["close"], btc_15m["close"])
        if ll:
            lider = ("BTC oncu" if ll["best_lag"] > 0 else
                     "alt oncu" if ll["best_lag"] < 0 else "es-anli")
            print(f"  Lead-lag alt-BTC [RAPOR-ONLY, karara girmez]: "
                  f"en iyi lag={ll['best_lag']:+d} bar ({lider}) | "
                  f"r={ll['r']:.3f} (p={ll['p']:.4f}, n={ll['n']}) | "
                  f"r(lag0)={ll['r0']:.3f} | asimetri={ll['asym']:+.3f} "
                  f"(+: BTC oncu)")
        else:
            print("  Lead-lag alt-BTC: VERI YOK (pencere yetersiz)")
    if symbol != "ETH/USDT":
        ce = corr_stats(df_15m["close"], eth_15m["close"])
        if ce:
            print(f"  Korelasyon alt-ETH: r={ce['r']:.3f} "
                  f"(p={ce['p']:.4f}, n={ce['n']})")
    state, state_conf = regime_detector(df_15m["close"], df_4h["close"])
    if symbol == "BTC/USDT":
        btc_state = state
        print(f"  Rejim: {state} (guven={state_conf:.2f}) | "
              f"BTC rejimi: kendisi (oz-kiyas atlandi)")
    else:
        btc_state, _ = regime_detector(btc_15m["close"], btc_4h["close"])
        print(f"  Rejim: {state} (guven={state_conf:.2f}) | "
              f"BTC rejimi: {btc_state}")
    fr_df, oi = fetch_funding_oi(symbol)
    fr_latest = 0.0
    if not fr_df.empty and "fundingRate" in fr_df.columns:
        fr_latest = float(fr_df["fundingRate"].iloc[-1])
    oi_str = f"{oi:,.1f}" if np.isfinite(oi) else "yok"
    print(f"  Funding: {fr_latest * 100:.4f}% (8h) | OI: {oi_str}")

    # Use centralized leading indicators to avoid duplicate/contradictory calls
    inds = compute_leading_indicators(symbol, df_4h, df_15m, btc_4h, btc_15m)
    trades = inds["trades"]
    bids = inds["bids"]; asks = inds["asks"]
    score15 = inds["score15"]; note15 = inds["note15"]
    yon = inds["yon"]; yon_move = inds["yon_move"]; tscore = inds["tscore"]
    komp = inds["komp"]

    # real-time warnings reuse the computed data
    mw = realtime_warnings(symbol, trades, df_15m["close"], bids, asks,
                           score15, note15, yon, yon_move)
    if mw:
        for w in mw:
            print(f"  ONCU UYARI: {w}")
    else:
        print("  ONCU UYARI: yok (olumlu)")

    print(f"  {composite_line(komp)}")

    # --- Pump/Dump vetosu (v5.3: tick teyidi artik tanimli) ---
    note = note15
    src = "OHLCV/15M(kapanmis)"
    if note15 in ("NORMAL", "WATCH"):
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

    # BTC uyum kapisi (aynı davranış korunuyor)
    if symbol != "BTC/USDT" and state in ("BULL", "BEAR") \
            and btc_state != state:
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
    df["rsi"] = wilder_rsi(close, RSI_LEN)
    df["target"] = sma20
    df = df.dropna(subset=["z", "atr", "rsi"])
    if len(df) < 700:
        print(f"  -> Yetersiz veri ({len(df)} mum).")
        return
    feat = {k: df[k].to_numpy(dtype=float) for k in
            ["open", "close", "low", "high", "z", "atr", "rsi"]}

    rule_grid = [(zt, ro) for zt in Z_GRID for ro in (False, True)]

    rule_trades = {rule: [] for rule in rule_grid}
    folds = 0
    for train_idx, test_idx in walkforward_splits(len(df), N_FOLDS, EMBARGO):
        for rule in rule_grid:
            zt, ro = rule
            rule_trades[rule].extend(simulate(feat, test_idx, zt, ro,
                                              direction))
        folds += 1
    if folds == 0:
        print("  -> Walk-forward split yok.")
        return
    stats = {rule: oos_stats(rule_trades[rule]) for rule in rule_grid}
    pvals = {}
    for rule, s in stats.items():
        if s is not None:
            pvals[rule] = 2.0 * (1.0 - norm_cdf(abs(s["t"])))
    if not pvals:
        print("  -> Yeterli OOS yok.")
        return
    keys = list(pvals.keys())
    accepted = fdr_bh([pvals[k] for k in keys], ALPHA)
    accepted_rules = [rule for rule, ok in zip(keys, accepted) if ok]
    p_max = bootstrap_max_t(rule_trades)
    print(f"  Kural izgarasi: {len(rule_grid)} kural "
          f"(= {len(Z_GRID)} z x 2 RSI durumu; esik sabitleri degismedi — "
          f"bootstrap kapisi tek yonlu sertlesir, BH-FDR'de FDR<=ALPHA "
          f"garantisi m'den bagimsiz korunur)")
    print(f"  WF fold: {folds} (genisleyen pencere+embargo) | BH-FDR kabul: "
          f"{[_rl(k) for k in accepted_rules] if accepted_rules else 'yok'} | "
          f"max-t bootstrap p: {p_max:.3f}")
    if not accepted_rules or p_max >= ALPHA:
        print("  -> Anti-overfit kapi kapali.")
        return
    best_rule = max(accepted_rules, key=lambda rule: stats[rule]["mean"])
    best_z, best_rsi = best_rule
    best_stat = stats[best_rule]
    cur = df.iloc[-1]
    prev = df.iloc[-2]
    zi = float(cur["z"])
    atr_i = float(cur["atr"])
    rsi_i = float(cur["rsi"])   # ajanC: shift'li — son KAPANMIS bar oncesi
    if direction == "LONG":
        fired = (zi <= -best_z) and (zi > -4.0) and (float(prev["z"]) < zi) and \
            (zi > float(np.min(df["z"].iloc[-4:-1])))
    else:
        fired = (zi >= best_z) and (zi < 4.0) and (float(prev["z"]) > zi) and \
            (zi < float(np.max(df["z"].iloc[-4:-1])))
    if fired and best_rsi:
        rsi_ok = np.isfinite(rsi_i) and (
            rsi_i < RSI_LONG_MAX if direction == "LONG"
            else rsi_i > RSI_SHORT_MIN)
        if not rsi_ok:
            print(f"  -> Kenar onayli; tetik yok: z sarti sagladi "
                  f"(z={zi:.2f}, esik={best_z}) ama RSI sarti saglanmadi "
                  f"(rsi={rsi_i:.1f}, kural={_rl(best_rule)}).")
            return
    if not fired:
        print(f"  -> Kenar onayli; tetik yok (z={zi:.2f}, esik={best_z}, "
              f"kural={_rl(best_rule)}).")
        return
    order_type, ref_px, role, best_bid, best_ask, imb, spread_bps = \
        execution_router(symbol, direction, target_usd, bids, asks)
    last_close = float(cur["close"])
    # NEW: robust stop sizing for signal reporting
    stop_by_atr = ATR_SL_MULT * atr_i
    stop_by_pct = last_close * MIN_STOP_PCT
    stop_dist = max(stop_by_atr, stop_by_pct)
    sl_px = last_close - stop_dist if direction == "LONG" \
        else last_close + stop_dist
    target_px = float(cur["target"])
    print(f"  >>> {direction} SINYALI (WF+FDR+bootstrap onayli; "
          f"kural={_rl(best_rule)}) <<<")
    if best_rsi:
        kosul = (f"RSI<{RSI_LONG_MAX:.0f}" if direction == "LONG"
                 else f"RSI>{RSI_SHORT_MIN:.0f}")
        print(f"  RSI sarti uygulandi: rsi={rsi_i:.1f} ({kosul}; "
              f"esikler HIPOTEZ etiketli, kural kapilardan gecti)")
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
    print(f"  STOP [market]: {sl_px:.4f} ({ATR_SL_MULT} x ATR, min {MIN_STOP_PCT*100:.3f}% )")
    print(f"  ZAMAN STOPU: {TIME_STOP_BARS} bar (~12 saat)")
    print(f"  OOS: beklenen net %{best_stat['mean'] * 100:.3f}/islem | "
          f"kazanma %{best_stat['win'] * 100:.1f} | PF={best_stat['pf']:.2f} | "
          f"n={best_stat['n']}")
    print(f"  LOB: OBI={imb:.3f} | spread={spread_bps:.2f} bps")
    if abs(inds["fr_latest"]) * 1e4 >= FR_TOLERANCE_BPS:
        print(f"  ONCU IPUCU: funding agir ({inds['fr_latest'] * 100:.4f}%)")


# ---------------------------------------------------------------------------
# 11. ANA DONGU
# ---------------------------------------------------------------------------


# ====================================================================
# BOLUM 2: META3 KATMANI (birebir; tek-dosya surumu)
# ====================================================================
# META3 KARARGAH — Recursive Self-Improving calisma dongusu
# ====================================================================
# (The meta3 section is unchanged except for using compute_leading_indicators
# in karar_uret where needed; most logic preserved.)
# ====================================================================

import hashlib
import math
import json
import os
import sys
import time
import traceback

# --------------------------------------------------------------------
# TEK-DOSYA KOPRUSU: motor ve META3 ayni dosyada — `motor` adi bu
# modulun kendisine baglanir; meta3 kodundaki motor.X referanslari
# DEGISMEDEN calisir (birlesim mekanik, elle yeniden yazim yok).
# --------------------------------------------------------------------
motor = sys.modules[__name__]

# --------------------------------------------------------------------
# IMMUTABLE CONTROL PLANE (PDF #17/#22)
# Bu blok recursive katmanlarca DEGISTIRILEMEZ. Kosuda butunluk muhru
# dogrulanir; bozulmussa HALT (PDF #19: safety violation -> HALT).
# --------------------------------------------------------------------
_KAPI_SABITLERI = (
    "FEE_TAKER", "SLIPPAGE", "ATR_LEN", "ATR_SL_MULT", "TIME_STOP_BARS",
    "ALPHA", "MIN_TRADES", "N_FOLDS", "EMBARGO", "BOOTSTRAP_B",
    "PUMP_THRESHOLD_Z", "PUMP_TICK_WATCH", "FR_TOLERANCE_BPS", "LOB_DEPTH",
)

IMMUTABLE_PLANE = {
    "w_Q": 1.0, "w_R": 0.5, "w_S": 1.0, "w_C": 0.1, "w_L": 0.05,
    "kosu_basi_deney_butcesi": 2,
    "recursive_derinlik": 3,
    "min_akibet_n": 8,
    "eps_bant": (0.0, 0.3),
    "W_bant": (5, 50),
    "karantina_esigi": 3,
    "meta2_min_orneklem": 4,
    "meta2_verim_esigi": 0.25,
    "meta2_adim": 0.05,
    "meta3_min_orneklem": 3,
    "meta3_adim_buyut": 5,
    "meta3_adim_kucult": 3,
    "zorunlu_kesif_periyodu": 25,
}

def _taban_dizin_sec():
    adaylar = []
    try:
        adaylar.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    adaylar += [os.getcwd(),
                os.path.dirname(os.path.abspath(sys.argv[0]))
                if sys.argv and sys.argv[0] else "",
                "/storage/emulated/0/Download",
                "/storage/emulated/0/Documents"]
    adaylar = [a for a in adaylar if a]
    for a in adaylar:
        if os.path.isfile(os.path.join(a, "meta3_bellek.json")):
            return a
    for a in adaylar:
        try:
            p = os.path.join(a, ".meta3_yaz_testi")
            with open(p, "w") as f:
                f.write("t")
            os.remove(p)
            return a
        except OSError:
            continue
    return os.getcwd()


_TABAN_DIZIN = _taban_dizin_sec()
BELLEK_YOLU = os.path.join(_TABAN_DIZIN, "meta3_bellek.json")
OVERRIDE_YOLU = os.path.join(_TABAN_DIZIN, "meta3_override.json")


def kapi_muhru():
    parcalar = []
    for ad in _KAPI_SABITLERI:
        parcalar.append(f"{ad}={getattr(motor, ad)!r}")
    for ad in sorted(IMMUTABLE_PLANE):
        parcalar.append(f"PLANE.{ad}={IMMUTABLE_PLANE[ad]!r}")
    for ad in sorted(VARYANTLAR):
        parcalar.append(f"VAR.{ad}={sorted(VARYANTLAR[ad]['filtreler'])!r}")
    parcalar.append(f"VARSIRA={_VARYANT_SIRA!r}")
    return hashlib.sha256("|".join(parcalar).encode()).hexdigest()


def kesif_zamani(kosu_sayaci, eps):
    per = IMMUTABLE_PLANE["zorunlu_kesif_periyodu"]
    if kosu_sayaci > 0 and kosu_sayaci % per == 0:
        return True
    h = int(hashlib.sha256(f"kesif:{kosu_sayaci}".encode()).hexdigest()[:8], 16)
    return (h % 1000) < int(round(eps * 1000))


VARYANTLAR = {
    "V0_taban": {
        "aciklama": "v5.4 motoru oldugu gibi (WF+FDR+bootstrap kapilari)",
        "filtreler": [],
    },
    "V1_komposit_teyit": {
        "aciklama": ("taban + bilesik oncu skorun isareti yonle AYNI ve "
                     "kapsam >= 0.5 olmali (yalnizca SIKILASTIRMA)"),
        "filtreler": ["komposit_uyum"],
    },
    "V2_cift_teyit": {
        "aciklama": ("V1 + tick momentum isareti de yonle ayni olmali "
                     "(daha da siki)"),
        "filtreler": ["komposit_uyum", "tick_uyum"],
    },
}
_VARYANT_SIRA = ["V0_taban", "V1_komposit_teyit", "V2_cift_teyit"]


def filtre_gecer(filtre_adi, golge):
    deger = golge.get(filtre_adi)
    return deger is True


class BellekBozuk(Exception):
    pass


def _bellek_dogrula(b):
    try:
        assert isinstance(b, dict)
        assert isinstance(b["surum"], int) and b["surum"] >= 1
        assert b["aktif_varyant"] in VARYANTLAR
        assert isinstance(b["eps"], (int, float)) and \
            IMMUTABLE_PLANE["eps_bant"][0] <= b["eps"] <= IMMUTABLE_PLANE["eps_bant"][1]
        assert isinstance(b["W"], int) and \
            IMMUTABLE_PLANE["W_bant"][0] <= b["W"] <= IMMUTABLE_PLANE["W_bant"][1]
        assert isinstance(b["kosu_sayaci"], int) and b["kosu_sayaci"] >= 0
        for alan in ("deneyler", "akibetler", "oneriler", "evrim"):
            assert isinstance(b[alan], list)
        assert isinstance(b["karantina"], dict)
    except (AssertionError, KeyError, TypeError) as e:
        raise BellekBozuk(f"bellek dogrulamasi: {type(e).__name__} {e}") from e
    return b


def _akibet_zinciri(onceki_zincir, kayit):
    govde = json.dumps({k: v for k, v in kayit.items() if k != "zincir"},
                       sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(
        f"{kapi_muhru()}|{onceki_zincir}|{govde}".encode()).hexdigest()[:24]


def akibet_zinciri_dogrula(bellek):
    onceki = ""
    for i, a in enumerate(bellek["akibetler"]):
        beklenen = _akibet_zinciri(onceki, a)
        if a.get("zincir") != beklenen:
            return False, i
        onceki = a["zincir"]
    return True, None


def akibet_ekle(bellek, kayit):
    onceki = (bellek["akibetler"][-1]["zincir"]
              if bellek["akibetler"] else "")
    kayit["zincir"] = _akibet_zinciri(onceki, kayit)
    bellek["akibetler"].append(kayit)


def bellek_yukle():
    if not os.path.exists(BELLEK_YOLU):
        if os.path.exists(BELLEK_YOLU + ".bak"):
            raise BellekBozuk(
                "asil bellek dosyasi yok ama .bak yedegi var — kesintili "
                "yazim suphesi; .bak elle geri konmali ya da bilerek "
                "silinmeli (sessiz gecmis kaybi yasak)")
        return {
            "surum": 1,
            "kapi_muhru": None,
            "aktif_varyant": "V0_taban",
            "eps": 0.15,
            "W": 12,
            "kosu_sayaci": 0,
            "deneyler": [],
            "akibetler": [],
            "oneriler": [],
            "evrim": [{"surum": 1, "ebeveyn": None, "varyant": "V0_taban",
                       "neden": "baslangic"}],
            "karantina": {},
        }
    try:
        with open(BELLEK_YOLU, encoding="utf-8") as f:
            veri = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise BellekBozuk(f"bellek okunamadi: {e}") from e
    return _bellek_dogrula(veri)


def bellek_kaydet(bellek):
    if os.path.exists(BELLEK_YOLU):
        os.replace(BELLEK_YOLU, BELLEK_YOLU + ".bak")
    with open(BELLEK_YOLU, "w", encoding="utf-8") as f:
        json.dump(bellek, f, ensure_ascii=False, indent=1)


def deney_kaydi(bellek, optimizer, hipotez, patch, metrikler, maliyet_sn,
                risk, karar, gecikme_sn=0.0):
    kayit = {
        "experiment_id": f"E{len(bellek['deneyler']) + 1:05d}",
        "parent_version": bellek["surum"],
        "optimizer_version": optimizer,
        "hypothesis": hipotez,
        "patch": patch,
        "metrics": metrikler,
        "cost": None if maliyet_sn is None else round(maliyet_sn, 3),
        "latency": None if gecikme_sn is None else round(gecikme_sn, 3),
        "risk": risk,
        "decision": karar,
    }
    bellek["deneyler"].append(kayit)
    return kayit


def degerlendir(Q, R, S, C, L):
    if any(x is None for x in (Q, R, S, C, L)):
        return None
    P = IMMUTABLE_PLANE
    return (P["w_Q"] * Q + P["w_R"] * R + P["w_S"] * S
            - P["w_C"] * C - P["w_L"] * L)


def akibet_olc(oneri, df_15m):
    giris, stop, hedef = oneri["giris"], oneri["stop"], oneri["hedef"]
    yon = oneri["yon"]
    if not all(isinstance(x, (int, float)) and np.isfinite(x)
               for x in (giris, stop, hedef)) \
            or yon not in ("LONG", "SHORT"):
        return {"sonuc": "GECERSIZ", "r": None}
    if yon == "LONG" and not (stop < giris < hedef):
        return {"sonuc": "GECERSIZ", "r": None}
    if yon == "SHORT" and not (hedef < giris < stop):
        return {"sonuc": "GECERSIZ", "r": None}
    barlar = df_15m[df_15m.index > pd.Timestamp(oneri["bar_ts"], unit="ms",
                                                tz="UTC")]
    if barlar.empty:
        return None
    dolum = False
    for ts, bar in barlar.iterrows():
        lo, hi = float(bar["low"]), float(bar["high"])
        if not np.isfinite(lo) or not np.isfinite(hi):
            continue
        if not dolum:
            if (yon == "LONG" and lo <= giris) or \
                    (yon == "SHORT" and hi >= giris):
                dolum = True
                dolum_bari = True
            else:
                continue
        else:
            dolum_bari = False
        if yon == "LONG":
            if lo <= stop:
                return {"sonuc": "STOP", "r": -1.0}
            if not dolum_bari and hi >= hedef:
                return {"sonuc": "HEDEF",
                        "r": round(abs(hedef - giris) /
                                   max(abs(giris - stop), 1e-9), 3)}
        else:
            if hi >= stop:
                return {"sonuc": "STOP", "r": -1.0}
            if not dolum_bari and lo <= hedef:
                return {"sonuc": "HEDEF",
                        "r": round(abs(giris - hedef) /
                                   max(abs(stop - giris), 1e-9), 3)}
    if not dolum:
        if len(barlar) >= motor.TIME_STOP_BARS:
            return {"sonuc": "IPTAL", "r": None}
        return None
    return None


def teyitli_swingler(df_15m, sol=2, sag=2):
    hi = df_15m["high"].to_numpy(dtype=float)
    lo = df_15m["low"].to_numpy(dtype=float)
    n = len(hi)
    tepeler, dipler = [], []
    for i in range(sol, n - sag):
        pencere_hi = hi[i - sol:i + sag + 1]
        pencere_lo = lo[i - sol:i + sag + 1]
        if np.isfinite(hi[i]) and hi[i] == np.max(pencere_hi):
            tepeler.append(float(hi[i]))
        if np.isfinite(lo[i]) and lo[i] == np.min(pencere_lo):
            dipler.append(float(lo[i]))
    return tepeler, dipler


R_MIN_STRATEJI = 1.35


def bilgi_hedefi(yon, giris, stop, df_15m, pencere=200):
    risk = abs(stop - giris)
    if not np.isfinite(risk) or risk <= 0:
        return None
    kesit = df_15m.iloc[-pencere:] if len(df_15m) > pencere else df_15m
    tepeler, dipler = teyitli_swingler(kesit)
    if yon == "LONG":
        for t in sorted(t for t in tepeler if t > giris):
            if (t - giris) / risk >= R_MIN_STRATEJI:
                return t
    elif yon == "SHORT":
        for d in sorted((d for d in dipler if d < giris), reverse=True):
            if (giris - d) / risk >= R_MIN_STRATEJI:
                return d
    return None


ILK_GECIS_ADIM = 8
STANDART_R_GEOMETRI = 1.35


def wilson_aralik(k, n, z=1.96):
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    payda = 1.0 + z * z / n
    merkez = p + z * z / (2 * n)
    yay = z * math.sqrt(p * (1.0 - p) / n + z * z / (4 * n * n))
    return max(0.0, (merkez - yay) / payda), min(1.0, (merkez + yay) / payda)


def ilk_gecis_olc(df_15m, yon, stop_mesafe, hedef_mesafe,
                  zaman_stop=None, adim=ILK_GECIS_ADIM):
    if zaman_stop is None:
        zaman_stop = motor.TIME_STOP_BARS
    close = df_15m["close"].astype(float)
    hl = (df_15m["high"] - df_15m["low"]).abs()
    hc = (df_15m["high"] - close.shift(periods=1)).abs()
    lc = (df_15m["low"] - close.shift(periods=1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(motor.ATR_LEN).mean().shift(periods=1)
    cl = close.to_numpy(dtype=float)
    hi = df_15m["high"].to_numpy(dtype=float)
    lo = df_15m["low"].to_numpy(dtype=float)
    at = atr.to_numpy(dtype=float)
    atr_simdi = at[-1] if np.isfinite(at[-1]) and at[-1] > 0 else None
    if atr_simdi is None or stop_mesafe <= 0 or hedef_mesafe <= 0:
        return None
    stop_k = stop_mesafe / atr_simdi
    hedef_k = hedef_mesafe / atr_simdi
    n_bar = len(cl)
    sayim = {"hedef": 0, "stop": 0, "zaman": 0}
    i = motor.ATR_LEN + 1
    while i < n_bar - zaman_stop:
        a = at[i]
        if np.isfinite(a) and a > 0:
            g = cl[i]
            if yon == "LONG":
                st, hd = g - stop_k * a, g + hedef_k * a
            else:
                st, hd = g + stop_k * a, g - hedef_k * a
            sonuc = "zaman"
            for j in range(i + 1, min(i + 1 + zaman_stop, n_bar)):
                if yon == "LONG":
                    if lo[j] <= st:
                        sonuc = "stop"
                        break
                    if hi[j] >= hd:
                        sonuc = "hedef"
                        break
                else:
                    if hi[j] >= st:
                        sonuc = "stop"
                        break
                    if lo[j] <= hd:
                        sonuc = "hedef"
                        break
            sayim[sonuc] += 1
        i += adim
    n = sum(sayim.values())
    if n < 30:
        return None
    R = hedef_mesafe / stop_mesafe
    p_h, p_s = sayim["hedef"] / n, sayim["stop"] / n
    h_alt, h_ust = wilson_aralik(sayim["hedef"], n)
    s_alt, s_ust = wilson_aralik(sayim["stop"], n)
    maliyet_R = (2 * motor.FEE_TAKER + 2 * motor.SLIPPAGE) * cl[-1] / stop_mesafe
    ev_nokta = p_h * R - p_s - maliyet_R
    ev_muhafazakar = h_alt * R - s_ust - maliyet_R
    if not (np.isfinite(ev_nokta) and np.isfinite(ev_muhafazakar)):
        return None
    return {"n": n, "p_hedef": round(p_h, 3), "p_stop": round(p_s, 3),
            "p_zaman": round(sayim["zaman"] / n, 3),
            "hedef_alt": round(h_alt, 3), "stop_ust": round(s_ust, 3),
            "R": round(R, 2), "maliyet_R": round(maliyet_R, 3),
            "ev_nokta": round(ev_nokta, 3),
            "ev_muhafazakar": round(ev_muhafazakar, 3)}


def karar_uret(symbol, df_4h, df_15m, btc_4h, btc_15m):
    t0 = time.monotonic()
    sonuc = {"sembol": symbol, "yon": "NOTR", "yon_kaynak": "VERI YOK",
             "kapi": "KAPALI", "kapi_gerekce": "", "etiket": "BILGI",
             "giris": None, "stop": None, "hedef": None, "kural": None,
             "oos": None, "p_max": None, "golge": {}, "bar_ts": None}

    state, conf = motor.regime_detector(df_15m["close"], df_4h["close"])
    btc_state, _ = motor.regime_detector(btc_15m["close"], btc_4h["close"])

    ef = df_4h["close"].ewm(span=50, adjust=False).mean()
    es = df_4h["close"].ewm(span=200, adjust=False).mean()
    egim = float(((ef - es) / df_4h["close"]).iloc[-1])
    if state == "BULL":
        sonuc["yon"], sonuc["yon_kaynak"] = "LONG", f"rejim BULL (guven={conf:.2f})"
    elif state == "BEAR":
        sonuc["yon"], sonuc["yon_kaynak"] = "SHORT", f"rejim BEAR (guven={conf:.2f})"
    elif abs(egim) > 1e-12:
        sonuc["yon"] = "LONG" if egim > 0 else "SHORT"
        sonuc["yon_kaynak"] = (f"rejim {state}; 4H EMA50-EMA200 egimi "
                               f"{egim:+.5f} (zayif kanit — bilgi)")

    # centralized leading indicators
    inds = compute_leading_indicators(symbol, df_4h, df_15m, btc_4h, btc_15m)
    trades = inds["trades"]; bids = inds["bids"]; asks = inds["asks"]
    score15 = inds["score15"]; note15 = inds["note15"]
    yon_pd = inds["yon"]; yon_move = inds["yon_move"]; tscore = inds["tscore"]
    komp = inds["komp"]

    sonuc["komposit"] = komp

    if sonuc["yon"] == "NOTR":
        if komp.get("skor") is not None and komp.get("kapsam", 0) >= 0.5 \
                and abs(komp["skor"]) > 1e-12:
            sonuc["yon"] = "LONG" if komp["skor"] > 0 else "SHORT"
            sonuc["yon_kaynak"] = (f"bilesik oncu skor {komp['skor']:+.2f} "
                                   f"(kapsam {komp['kapsam']:.2f}; zayif kanit)")
        else:
            sonuc["yon_kaynak"] = ("gercek berabere: rejim CALM, egim ~0, "
                                   "komposit olculemedi/sifir")

    yon_isaret = {"LONG": 1.0, "SHORT": -1.0}.get(sonuc["yon"], 0.0)
    if komp.get("skor") is not None and komp.get("kapsam", 0) >= 0.5:
        sonuc["golge"]["komposit_uyum"] = (komp["skor"] * yon_isaret) > 0
    else:
        sonuc["golge"]["komposit_uyum"] = None
    if abs(yon_move) > 1e-12:
        sonuc["golge"]["tick_uyum"] = (yon_move * yon_isaret) > 0
    else:
        sonuc["golge"]["tick_uyum"] = None

    close = df_15m["close"].astype(float)
    sma20 = close.rolling(window=20).mean()
    sd20 = close.rolling(window=20).std(ddof=0)
    z_ser = ((close - sma20) / (sd20 + 1e-12)).shift(periods=1)
    hl = (df_15m["high"] - df_15m["low"]).abs()
    hc = (df_15m["high"] - close.shift(periods=1)).abs()
    lc = (df_15m["low"] - close.shift(periods=1)).abs()
    tr_df = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr_ser = tr_df.rolling(motor.ATR_LEN).mean().shift(periods=1)
    son_kapanis = float(close.iloc[-1])
    atr_i = float(atr_ser.iloc[-1]) if np.isfinite(atr_ser.iloc[-1]) else None
    if atr_i is not None and yon_isaret != 0.0:
        sonuc["giris"] = son_kapanis
        # robust stop sizing
        stop_by_atr = motor.ATR_SL_MULT * atr_i
        stop_by_pct = son_kapanis * MIN_STOP_PCT
        stop_dist = max(stop_by_atr, stop_by_pct)
        sonuc["stop"] = son_kapanis - stop_dist if sonuc["yon"] == "LONG" \
            else son_kapanis + stop_dist
        hedef_px = bilgi_hedefi(sonuc["yon"], son_kapanis, sonuc["stop"],
                                df_15m)
        if hedef_px is not None:
            # ensure minimum distance for target
            min_tgt_dist = max(MIN_TARGET_PCT * son_kapanis, 0.5 * atr_i)
            if (sonuc["yon"] == "LONG" and hedef_px - son_kapanis < min_tgt_dist) or \
               (sonuc["yon"] == "SHORT" and son_kapanis - hedef_px < min_tgt_dist):
                adj = min_tgt_dist
                hedef_px = son_kapanis + adj if sonuc["yon"] == "LONG" else son_kapanis - adj
            sonuc["hedef"] = hedef_px
            sonuc["bar_ts"] = int(df_15m.index[-1].value // 1_000_000)
            sonuc["r"] = round(abs(hedef_px - son_kapanis)
                               / max(abs(sonuc["stop"] - son_kapanis), 1e-12), 2)
            sonuc["ilk_gecis"] = ilk_gecis_olc(
                df_15m, sonuc["yon"],
                abs(sonuc["stop"] - son_kapanis),
                abs(hedef_px - son_kapanis))
        else:
            # fallback: measure standard geometry but do not set hedef (policy)
            fallback_target_dist = STANDART_R_GEOMETRI * abs(sonuc["stop"] - son_kapanis)
            min_target_dist = max(MIN_TARGET_PCT * son_kapanis, 0.5 * atr_i)
            if abs(fallback_target_dist) < min_target_dist:
                fallback_target_dist = min_target_dist
            sonuc["yon_olcum"] = ilk_gecis_olc(
                df_15m, sonuc["yon"], abs(sonuc["stop"] - son_kapanis),
                fallback_target_dist)

    note = note15
    if note15 in ("NORMAL", "WATCH") and tscore is not None \
            and note15 == "WATCH" and tscore >= motor.PUMP_TICK_WATCH:
        note = "PUMP_OR_DUMP_RISK"
    if note == "PUMP_OR_DUMP_RISK":
        sonuc["kapi"], sonuc["kapi_gerekce"] = "VETO", \
            f"pump/dump vetosu (score={score15:.2f}, yon={yon_pd})"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    if symbol != "BTC/USDT" and state in ("BULL", "BEAR") \
            and btc_state != state:
        sonuc["kapi_gerekce"] = f"BTC {btc_state} ile {state} uyumsuz"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    direction = "LONG" if state == "BULL" else \
        "SHORT" if state == "BEAR" else None
    if direction is None:
        sonuc["kapi_gerekce"] = "rejim CALM/UNKNOWN — istatistik kapisi acilmadi"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc

    df = df_15m.copy()
    df["z"] = z_ser
    df["atr"] = atr_ser
    df["rsi"] = motor.wilder_rsi(close, motor.RSI_LEN)
    df["target"] = sma20
    df = df.dropna(subset=["z", "atr", "rsi"])
    if len(df) < 700:
        sonuc["kapi_gerekce"] = f"yetersiz veri ({len(df)} mum)"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    feat = {k: df[k].to_numpy(dtype=float) for k in
            ["open", "close", "low", "high", "z", "atr", "rsi"]}
    rule_grid = [(zt, ro) for zt in motor.Z_GRID for ro in (False, True)]
    rule_trades = {rule: [] for rule in rule_grid}
    folds = 0
    for tr_idx, te_idx in motor.walkforward_splits(len(df), motor.N_FOLDS,
                                                   motor.EMBARGO):
        for rule in rule_grid:
            zt, ro = rule
            rule_trades[rule].extend(motor.simulate(feat, te_idx, zt, ro,
                                                    direction))
        folds += 1
    if folds == 0:
        sonuc["kapi_gerekce"] = "walk-forward split yok"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    stats = {rule: motor.oos_stats(rule_trades[rule]) for rule in rule_grid}
    pvals = {r: 2.0 * (1.0 - motor.norm_cdf(abs(s["t"])))
             for r, s in stats.items() if s is not None}
    if not pvals:
        sonuc["kapi_gerekce"] = "yeterli OOS islem yok"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    keys = list(pvals.keys())
    accepted = motor.fdr_bh([pvals[k] for k in keys], motor.ALPHA)
    accepted_rules = [r for r, ok in zip(keys, accepted) if ok]
    p_max = motor.bootstrap_max_t(rule_trades)
    sonuc["p_max"] = p_max
    if not accepted_rules or p_max >= motor.ALPHA:
        sonuc["kapi_gerekce"] = (f"anti-overfit kapi kapali "
                                 f"(kabul={len(accepted_rules)}, p={p_max:.3f})")
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    best_rule = max(accepted_rules, key=lambda r: stats[r]["mean"])
    best_z, best_rsi = best_rule
    sonuc["kural"] = f"z={best_z}" + ("+RSI" if best_rsi else "")
    sonuc["oos"] = stats[best_rule]
    cur, prev = df.iloc[-1], df.iloc[-2]
    zi, rsi_i = float(cur["z"]), float(cur["rsi"])
    if direction == "LONG":
        fired = (zi <= -best_z) and (zi > -4.0) and (float(prev["z"]) < zi) \
            and (zi > float(np.min(df["z"].iloc[-4:-1])))
    else:
        fired = (zi >= best_z) and (zi < 4.0) and (float(prev["z"]) > zi) \
            and (zi < float(np.max(df["z"].iloc[-4:-1])))
    if fired and best_rsi:
        rsi_ok = np.isfinite(rsi_i) and (
            rsi_i < motor.RSI_LONG_MAX if direction == "LONG"
            else rsi_i > motor.RSI_SHORT_MIN)
        if not rsi_ok:
            fired = False
            sonuc["kapi_gerekce"] = (f"z sarti sagladi ama RSI sarti "
                                     f"saglanmadi (rsi={rsi_i:.1f})")
    if fired:
        sonuc["kapi"] = "ACIK"
        sonuc["etiket"] = "EMIR-ADAYI"
        sonuc["kapi_gerekce"] = (f"WF+FDR+bootstrap onayli; kural="
                                 f"{sonuc['kural']}, z={zi:.2f}")
        sonuc["giris"] = float(cur["close"])
        # robust stop sizing here as well
        stop_by_atr = motor.ATR_SL_MULT * float(cur["atr"])
        stop_by_pct = sonuc["giris"] * MIN_STOP_PCT
        stop_dist = max(stop_by_atr, stop_by_pct)
        sonuc["stop"] = sonuc["giris"] - stop_dist if direction == "LONG" \
            else sonuc["giris"] + stop_dist
        sonuc["hedef"] = float(cur["target"])
        sonuc["yon"] = direction
        sonuc["yon_kaynak"] = f"rejim {state} + tetik ({sonuc['kural']})"
        hedef_dogru = (sonuc["hedef"] > sonuc["giris"] if direction == "LONG"
                       else sonuc["hedef"] < sonuc["giris"])
        if hedef_dogru:
            sonuc["r"] = round(abs(sonuc["hedef"] - sonuc["giris"])
                               / max(abs(sonuc["stop"] - sonuc["giris"]),
                                     1e-12), 2)
            sonuc["bar_ts"] = int(df.index[-1].value // 1_000_000)
            sonuc["ilk_gecis"] = ilk_gecis_olc(
                df_15m, sonuc["yon"],
                abs(sonuc["stop"] - sonuc["giris"]),
                abs(sonuc["hedef"] - sonuc["giris"]))
            if sonuc["r"] < R_MIN_STRATEJI:
                sonuc["etiket"] = "TETIK-BILGI"
                sonuc["kapi_gerekce"] += (
                    f" | R={sonuc['r']:.2f} < {R_MIN_STRATEJI}: STRATEJI.md "
                    f"geregi EMIR-ADAYI etiketi VERILMEDI (motor geometrisi "
                    f"korunarak tetik bilgi olarak basildi)")
        else:
            sonuc["kapi"] = "KAPALI"
            sonuc["etiket"] = "BILGI"
            sonuc["hedef"] = None
            sonuc["bar_ts"] = None
            sonuc["kapi_gerekce"] += (" | hedef (SMA20) yonun ters tarafina "
                                      "dustu — emir-adayi dusuruldu "
                                      "(fail-closed)")
    elif not sonuc["kapi_gerekce"]:
        sonuc["kapi_gerekce"] = (f"kenar onayli; tetik yok (z={zi:.2f}, "
                                 f"esik={best_z}, kural={sonuc['kural']})")
    sonuc["sure_sn"] = time.monotonic() - t0
    return sonuc


def varyant_karari(karar, varyant_adi):
    if karar["kapi"] != "ACIK":
        return karar, []
    dusen = []
    for f in VARYANTLAR[varyant_adi]["filtreler"]:
        if not filtre_gecer(f, karar["golge"]):
            dusen.append(f)
    if dusen:
        karar = dict(karar)
        karar["kapi"] = "KAPALI"
        karar["etiket"] = "BILGI"
        karar["kapi_gerekce"] += (f" | varyant {varyant_adi} filtresi dusurdu: "
                                  f"{','.join(dusen)} (sikilastirma)")
    return karar, dusen


def _varyant_akibet_ozeti(bellek, varyant_adi):
    rler = []
    for a in bellek["akibetler"]:
        r = a.get("r")
        if r is None or not np.isfinite(r):
            continue
        if not str(a.get("etiket", "")).startswith("EMIR-ADAYI"):
            continue
        golge = a.get("golge", {})
        alir = all(filtre_gecer(f, golge)
                   for f in VARYANTLAR[varyant_adi]["filtreler"])
        if alir:
            rler.append(float(r))
    if not rler:
        return {"n": 0, "ort_r": None}
    return {"n": len(rler), "ort_r": float(np.mean(rler))}


def meta_dongusu(bellek, kosu_suresi_sn, veri_yasi_sn, guvenlik_ok=True):
    P = IMMUTABLE_PLANE
    aktif = bellek["aktif_varyant"]
    if not guvenlik_ok:
        deney_kaydi(bellek, "meta",
                    "ic denetim ihlali: S=0 — bu kosuda varyant karari yok",
                    {}, {"S": 0.0}, kosu_suresi_sn, "guvenlik", "HOLD",
                    veri_yasi_sn)
        return "HOLD", "ic denetim ihlali (S=0) — evaluator guvenlik dali"
    ozet_aktif = _varyant_akibet_ozeti(bellek, aktif)
    C = min(kosu_suresi_sn / 60.0, 10.0)
    L = min(veri_yasi_sn / 3600.0, 10.0)

    if ozet_aktif["n"] < P["min_akibet_n"]:
        deney_kaydi(bellek, "meta",
                    f"aktif {aktif}: olculmus akibet n={ozet_aktif['n']} < "
                    f"{P['min_akibet_n']}",
                    {"varyant": aktif}, {"akibet": ozet_aktif},
                    kosu_suresi_sn, "veri_yetersiz", "HOLD", veri_yasi_sn)
        return "HOLD", (f"olculmus akibet yetersiz "
                        f"(EMIR-ADAYI populasyonunda n={ozet_aktif['n']}/"
                        f"{P['min_akibet_n']}; BILGI kayitlari yon-isabet "
                        f"olcumune girer, varyant secimine girmez) — "
                        f"evaluator kararsiz, degisiklik yok (fail-closed)")

    en_iyi = (aktif, ozet_aktif)
    kesif = kesif_zamani(bellek["kosu_sayaci"], bellek["eps"])
    if not kesif:
        deney_kaydi(bellek, "meta",
                    f"kesif takvimi kapali (eps={bellek['eps']:.2f}, "
                    f"kosu #{bellek['kosu_sayaci']}) — aday degerlendirilmedi",
                    {}, {"eps": bellek["eps"]},
                    kosu_suresi_sn, "kesif_kapali", "TUT", veri_yasi_sn)
    else:
        adaylar = [v for v in _VARYANT_SIRA if v != aktif and
                   bellek["karantina"].get(v, 0) < P["karantina_esigi"]]
        degerlendirilen = 0
        for aday in adaylar:
            if degerlendirilen >= P["kosu_basi_deney_butcesi"]:
                deney_kaydi(bellek, "meta",
                            f"kosu-basi deney butcesi bitti; {aday} bu "
                            f"kosuda degerlendirilmedi",
                            {"varyant": aday}, {},
                            kosu_suresi_sn, "butce", "STOP", veri_yasi_sn)
                continue
            ozet = _varyant_akibet_ozeti(bellek, aday)
            degerlendirilen += 1
            if ozet["n"] < P["min_akibet_n"]:
                deney_kaydi(bellek, "meta",
                            f"aday {aday}: karsi-olgusal n={ozet['n']} "
                            f"yetersiz", {"varyant": aday}, {"akibet": ozet},
                            kosu_suresi_sn, "veri_yetersiz", "HOLD",
                            veri_yasi_sn)
                continue
            R_bilesen = (None if bellek.get("_son_p_max") is None
                         else 1.0 - bellek["_son_p_max"])
            J_aday = degerlendir(ozet["ort_r"], R_bilesen, 1.0, C, L)
            J_iyi = degerlendir(en_iyi[1]["ort_r"], R_bilesen, 1.0, C, L)
            if J_aday is None or J_iyi is None:
                deney_kaydi(bellek, "meta",
                            f"{aday}: J hesaplanamadi (bilesen VERI YOK) — "
                            f"ret DEGIL, beklemede",
                            {"varyant": aday}, {"akibet": ozet, "J": None},
                            kosu_suresi_sn, "veri_yetersiz", "HOLD",
                            veri_yasi_sn)
                continue
            if J_aday > J_iyi:
                eski_iyi_ad = en_iyi[0]
                en_iyi = (aday, ozet)
                deney_kaydi(bellek, "meta",
                            f"{aday} J={J_aday:.3f} > {eski_iyi_ad} "
                            f"J={J_iyi:.3f} (olculmus ustunluk)",
                            {"varyant": aday},
                            {"akibet": ozet, "J": round(J_aday, 3),
                             "J_kiyas": round(J_iyi, 3)},
                            kosu_suresi_sn, "olcum_ustun", "KEEP",
                            veri_yasi_sn)
            else:
                bellek["karantina"][aday] = \
                    bellek["karantina"].get(aday, 0) + 1
                deney_kaydi(bellek, "meta",
                            f"{aday} J={J_aday:.3f} <= {en_iyi[0]} "
                            f"J={J_iyi:.3f} (olcumde ustun degil)",
                            {"varyant": aday},
                            {"akibet": ozet, "J": round(J_aday, 3),
                             "J_kiyas": round(J_iyi, 3)},
                            kosu_suresi_sn, "olcum_ustun_degil", "REJECT",
                            veri_yasi_sn)
    if en_iyi[0] != aktif:
        bellek["surum"] += 1
        bellek["evrim"].append({"surum": bellek["surum"],
                                "ebeveyn": bellek["surum"] - 1,
                                "varyant": en_iyi[0],
                                "neden": "meta KEEP (olculmus J ustunlugu)"})
        bellek["aktif_varyant"] = en_iyi[0]
        bellek["karantina"][en_iyi[0]] = 0
        return "KEEP", f"aktif varyant {aktif} -> {en_iyi[0]} (olcumle)"
    taban = _varyant_akibet_ozeti(bellek, "V0_taban")
    if aktif != "V0_taban" and taban["n"] >= P["min_akibet_n"] \
            and ozet_aktif["ort_r"] is not None \
            and taban["ort_r"] is not None \
            and ozet_aktif["ort_r"] < taban["ort_r"]:
        bellek["surum"] += 1
        bellek["evrim"].append({"surum": bellek["surum"],
                                "ebeveyn": bellek["surum"] - 1,
                                "varyant": "V0_taban",
                                "neden": "ROLLBACK (aktif, tabandan olcumle kotu)"})
        bellek["aktif_varyant"] = "V0_taban"
        deney_kaydi(bellek, "meta", f"{aktif} tabandan kotu: "
                    f"{ozet_aktif['ort_r']:.3f} < {taban['ort_r']:.3f}",
                    {"varyant": "V0_taban"},
                    {"aktif": ozet_aktif, "taban": taban},
                    kosu_suresi_sn, "olculmus_gerileme", "ROLLBACK",
                    veri_yasi_sn)
        return "ROLLBACK", f"{aktif} -> V0_taban (olculmus gerileme)"
    return "TUT", f"aktif {aktif} korunuyor (olcumle ustun ya da esit)"


def meta2_dongusu(bellek):
    P = IMMUTABLE_PLANE
    W = bellek["W"]
    if bellek["kosu_sayaci"] % W != 0 or bellek["kosu_sayaci"] == 0:
        return None
    son = [d for d in bellek["deneyler"] if d["optimizer_version"] == "meta"][-3 * W:]
    kesifler = [d for d in son if d["decision"] in ("KEEP", "REJECT")]
    if len(kesifler) < P["meta2_min_orneklem"]:
        deney_kaydi(bellek, "meta2", "kesif orneklemi yetersiz", {},
                    {"n": len(kesifler)}, None, "veri_yetersiz", "HOLD", None)
        return "HOLD"
    verim = sum(1 for d in kesifler if d["decision"] == "KEEP") / len(kesifler)
    eski = bellek["eps"]
    adim = P["meta2_adim"] if verim > P["meta2_verim_esigi"] else -P["meta2_adim"]
    yeni = min(max(eski + adim, P["eps_bant"][0]), P["eps_bant"][1])
    bellek["eps"] = round(yeni, 4)
    deney_kaydi(bellek, "meta2",
                f"kesif verimi {verim:.2f} -> eps {eski:.2f}->{yeni:.2f} "
                f"(bant {P['eps_bant']})", {"eps": bellek["eps"]},
                {"verim": round(verim, 3)}, None, "olcum",
                "KEEP" if yeni != eski else "TUT")
    return "KEEP" if yeni != eski else "TUT"


def meta3_dongusu(bellek):
    P = IMMUTABLE_PLANE
    W = bellek["W"]
    if bellek["kosu_sayaci"] % (W * W) != 0 or bellek["kosu_sayaci"] == 0:
        return None
    m2 = [d for d in bellek["deneyler"] if d["optimizer_version"] == "meta2"]
    if len(m2) < P["meta3_min_orneklem"]:
        deney_kaydi(bellek, "meta3", "meta2 orneklemi yetersiz", {},
                    {"n": len(m2)}, None, "veri_yetersiz", "HOLD", None)
        return "HOLD"
    son3 = [d["decision"] for d in m2[-P["meta3_min_orneklem"]:]]
    eski = bellek["W"]
    if all(k == "TUT" for k in son3):
        yeni = min(eski + P["meta3_adim_buyut"], P["W_bant"][1])
    elif son3.count("KEEP") >= 2:
        yeni = max(eski - P["meta3_adim_kucult"], P["W_bant"][0])
    else:
        yeni = eski
    bellek["W"] = yeni
    deney_kaydi(bellek, "meta3",
                f"meta2 son3={son3} -> W {eski}->{yeni} (bant {P['W_bant']})",
                {"W": yeni}, {"son3": son3}, None, "olcum",
                "KEEP" if yeni != eski else "TUT")
    return "KEEP" if yeni != eski else "TUT"


def ic_denetim(bellek, kararlar, muhur_ok):
    ihlaller = []
    if not muhur_ok:
        ihlaller.append("MUHUR: kapi sabitleri degismis (HALT gerektirir)")
    for k in kararlar:
        if k["yon"] not in ("LONG", "SHORT", "NOTR"):
            ihlaller.append(f"{k['sembol']}: yon alani bozuk")
        if k["yon"] == "NOTR" and "berabere" not in k["yon_kaynak"] \
                and "VERI YOK" not in k["yon_kaynak"]:
            ihlaller.append(f"{k['sembol']}: NOTR gerekcesiz (yon gizlenemez)")
        if k["etiket"] == "EMIR-ADAYI" and k["kapi"] != "ACIK":
            ihlaller.append(f"{k['sembol']}: kapi acik degilken EMIR-ADAYI")
        if k["etiket"] == "EMIR-ADAYI" and \
                (k.get("r") is None or k["r"] < R_MIN_STRATEJI):
            ihlaller.append(f"{k['sembol']}: EMIR-ADAYI etiketi R<"
                            f"{R_MIN_STRATEJI} ile (sozlesme ihlali)")
    for d in bellek["deneyler"][-10:]:
        if d["optimizer_version"] == "meta" and d["decision"] == "KEEP" \
                and "J" not in d["metrics"] and "akibet" not in d["metrics"]:
            ihlaller.append(f"{d['experiment_id']}: KEEP olcumsuz")
    if ihlaller:
        for k in kararlar:
            if k["etiket"] == "EMIR-ADAYI":
                k["etiket"] = "BILGI (MUHURLU — ic denetim ihlali)"
    return ihlaller


def override_kontrol():
    if os.path.exists(OVERRIDE_YOLU):
        try:
            with open(OVERRIDE_YOLU, encoding="utf-8") as f:
                ov = json.load(f)
            if ov.get("dur") is True:
                return "HALT"
        except Exception:
            return "HALT"
    return None


def kosu():
    print("KARARGAH TEK v2.4 (motor v5.4 + META3 v2.4) — recursive karar dongusu "
          "(karar-destek; emir gondermez)")
    print("=" * 70)
    if override_kontrol() == "HALT":
        print("HALT: insan override bayragi aktif (meta3_override.json). "
              "Hicbir islem yapilmadi.")
        return
    print(f"Bellek dosyasi: {BELLEK_YOLU}")
    try:
        bellek = bellek_yukle()
    except BellekBozuk as e:
        print(f"HALT: bellek dosyasi bozuk — {e}")
        print("Yedek: meta3_bellek.json.bak (varsa) elle geri konabilir ya da"
              " dosya silinip temiz baslangic yapilir. Bozuk bellekle KOSU"
              " YAPILMAZ (fail-closed).")
        return
    muhur = kapi_muhru()
    muhur_ok = True
    if bellek["kapi_muhru"] is None:
        bellek["kapi_muhru"] = muhur
        print(f"Kapi muhru ILK kosuda kaydedildi: {muhur[:16]}…")
    elif bellek["kapi_muhru"] != muhur:
        muhur_ok = False
        print("!!! HALT: kapi sabitleri onceki kosudan FARKLI (muhur tutmadi)."
              " Recursive katmanlar sabit degistiremez; degisiklik insan"
              " elinden geldiyse bellek sifirlanmali (meta3_bellek.json sil).")
        return

    zincir_ok, kirik = akibet_zinciri_dogrula(bellek)
    if not zincir_ok:
        print(f"!!! HALT: akibet defteri butunlugu bozuk (kayit #{kirik}). "
              f"Defter elle degistirilmis ya da bozulmus olabilir; olculmus"
              f" gecmis guvenilmezse KEEP/REJECT verilemez. Yedek: .bak")
        return
    t_kosu = time.monotonic()
    motor.selftest()
    try:
        btc_4h = motor.fetch_ohlcv("BTC/USDT", motor.TF_4H, motor.LIMIT_4H)
        btc_15m = motor.fetch_ohlcv("BTC/USDT", motor.TF_15M, motor.LIMIT_15M)
    except Exception:
        traceback.print_exc()
        print("\nKosu BASARISIZ: BTC referans verisi alinamadi.")
        return
    veri_yasi_sn = max(0.0, (pd.Timestamp.now(tz="UTC")
                             - btc_15m.index[-1]).total_seconds())

    print("\n[HESAP VERME] onceki kosunun onerileri:")
    bekleyen = []
    olculen = 0
    for oneri in bellek["oneriler"]:
        try:
            df15 = (btc_15m if oneri["sembol"] == "BTC/USDT"
                    else motor.fetch_ohlcv(oneri["sembol"], motor.TF_15M, 200))
        except Exception:
            bekleyen.append(oneri)
            continue
        sonuc = akibet_olc(oneri, df15)
        if sonuc is None:
            bekleyen.append(oneri)
            continue
        olculen += 1
        akibet_ekle(bellek, {
            "sembol": oneri["sembol"], "varyant": oneri.get("varyant"),
            "etiket": oneri.get("etiket"), "golge": oneri.get("golge", {}),
            "sonuc": sonuc["sonuc"], "r": sonuc["r"],
            "oneri_imza": f"{oneri['sembol']}|{oneri['bar_ts']}",
        })
        r_str = "R yazilmaz" if sonuc["r"] is None else f"R={sonuc['r']:+.2f}"
        print(f"  {oneri['sembol']}: {sonuc['sonuc']} ({r_str})")
    if not bellek["oneriler"]:
        print("  kayit yok (ilk kosu ya da onceki kosuda oneri yoktu) — "
              "gecmis UYDURULMAZ")
    elif olculen == 0:
        print(f"  {len(bekleyen)} oneri hala olculemedi (yeni bar/veri yok)")
    bellek["oneriler"] = bekleyen

    aktif = bellek["aktif_varyant"]
    print(f"\n[AGENT] aktif varyant: {aktif} — "
          f"{VARYANTLAR[aktif]['aciklama']}")
    kararlar = []
    p_maxlar = []
    atlanan = 0
    for sym in motor.SYMBOLS:
        try:
            if sym == "BTC/USDT":
                a4, a15 = btc_4h, btc_15m
            else:
                a4 = motor.fetch_ohlcv(sym, motor.TF_4H, motor.LIMIT_4H)
                a15 = motor.fetch_ohlcv(sym, motor.TF_15M, motor.LIMIT_15M)
            k = karar_uret(sym, a4, a15, btc_4h, btc_15m)
            k, dusen = varyant_karari(k, aktif)
            kararlar.append(k)
            if k["p_max"] is not None:
                p_maxlar.append(k["p_max"])
        except Exception:
            traceback.print_exc()
            atlanan += 1
            print(f"  [{sym}] atlandi.")
    bellek["_son_p_max"] = (float(np.median(p_maxlar)) if p_maxlar else None)

    ihlaller = ic_denetim(bellek, kararlar, muhur_ok)

    print("\n[KARARLAR]")
    print("  (ILK-GECIS siniri — tum semboller icin gecerli: ornekleme "
          "pencereleri ortusuk oldugundan %95 Wilson araligi gercekte ~%90 "
          "kapsar [sentetik olcum]; gecmis dagilim gelecegi garanti etmez)")
    for k in kararlar:
        print(f"\n=== {k['sembol']} ===")
        print(f"  YON: {k['yon']}  (kaynak: {k['yon_kaynak']})")
        ig = k.get("ilk_gecis") or k.get("yon_olcum")
        if ig:
            if ig["ev_muhafazakar"] > 0:
                hukum = "ISLEM DEGERI VAR (olculen, muhafazakar)"
                if k["kapi"] != "ACIK":
                    hukum += (f" — ANCAK KAPI {k['kapi']}: hukum BILGI "
                              f"niteligindedir, islem onerisi DEGILDIR")
            elif ig["ev_nokta"] > 0:
                hukum = ("EV nokta pozitif ama Wilson kotu-ucunda degil — "
                         "KANIT YETERSIZ (yazi-tura bandi)")
            else:
                hukum = "ISLEM DEGERI YOK (olculen EV <= 0)"
            print(f"  ILK-GECIS (bu seviye seti): n={ig['n']} | p_hedef={ig['p_hedef']:.2f} "
                  f"[alt {ig['hedef_alt']:.2f}] | p_stop={ig['p_stop']:.2f} "
                  f"[ust {ig['stop_ust']:.2f}] | p_zaman={ig['p_zaman']:.2f} "
                  f"| maliyet={ig['maliyet_R']:.2f}R")
            print(f"  EV: nokta {ig['ev_nokta']:+.2f}R | muhafazakar "
                  f"{ig['ev_muhafazakar']:+.2f}R -> {hukum}")
        else:
            print(f"  ILK-GECIS: VERI YOK (orneklem < 30 ya da ATR "
                  f"olculemedi) — EV hukmu verilemez")
        if k["giris"] is not None and k["hedef"] is not None:
            r_not = (f"R={k.get('r', 0):.2f}"
                     + ("" if k.get("r", 0) >= 1.35
                        else " (DAR — STRATEJI.md R_min=1.35 altinda)"))
            print(f"  SEVIYELER [{k['etiket']}]: giris {k['giris']:.4f} | "
                  f"stop {k['stop']:.4f} | hedef {k['hedef']:.4f} | "
                  f"{r_not} | zaman-stop {motor.TIME_STOP_BARS} bar")
        elif k["giris"] is not None:
            print(f"  SEVIYELER [{k['etiket']}]: giris {k['giris']:.4f} | "
                  f"stop {k['stop']:.4f} | hedef VERI YOK "
                  f"({k.get('hedef_gerekce', 'olculemedi')})")
        else:
            print(f"  SEVIYELER: VERI YOK (ATR olculemedi ya da yon NOTR"
                  f" — uydurma seviye basilmaz)")
        print(f"  KAPI: {k['kapi']} — {k['kapi_gerekce']}")
        if k.get("oos"):
            print(f"  OLCUM: kural={k['kural']} | OOS ort "
                  f"%{k['oos']['mean'] * 100:.3f} | n={k['oos']['n']} | "
                  f"p_max={k['p_max']:.3f}")
        if k["giris"] is not None and k["bar_ts"] is not None \
                and k["hedef"] is not None:
            imza = f"{k['sembol']}|{k['bar_ts']}"
            bekleyen_imzalar = {f"{o['sembol']}|{o['bar_ts']}"
                                for o in bellek["oneriler"]}
            olculmus_imzalar = {a.get("oneri_imza")
                                for a in bellek["akibetler"]}
            if imza in bekleyen_imzalar or imza in olculmus_imzalar:
                print(f"  (oneri zaten kayitli — ayni bar, mukerrer kayit "
                      f"yazilmadi)")
            else:
                ig_k = k.get("ilk_gecis")
                bellek["oneriler"].append({
                    "sembol": k["sembol"], "yon": k["yon"],
                    "giris": k["giris"], "stop": k["stop"],
                    "hedef": k["hedef"], "bar_ts": k["bar_ts"],
                    "etiket": k["etiket"], "varyant": aktif,
                    "golge": k["golge"],
                    "ev": (None if not ig_k else {
                        "n": ig_k["n"], "p_hedef": ig_k["p_hedef"],
                        "ev_nokta": ig_k["ev_nokta"],
                        "ev_muhafazakar": ig_k["ev_muhafazakar"],
                        "maliyet_R": ig_k["maliyet_R"]}),
                })

    kosu_suresi = time.monotonic() - t_kosu
    print("\n[META]")
    if kararlar:
        m_karar, m_detay = meta_dongusu(bellek, kosu_suresi, veri_yasi_sn, guvenlik_ok=not ihlaller)
        print(f"  META: {m_karar} — {m_detay}")
        bellek["kosu_sayaci"] += 1
        m2 = meta2_dongusu(bellek)
        if m2 is not None:
            print(f"  META2: {m2} (eps={bellek['eps']:.2f})")
        m3 = meta3_dongusu(bellek)
        if m3 is not None:
            print(f"  META3: {m3} (W={bellek['W']})")
    else:
        print("  META: ATLANDI — hicbir sembol karari uretilemedi; kosu "
              "sayaci ILERLEMEDI, katmanlar olcusuz kosturulmadi.")

    if ihlaller:
        print("\n[IC DENETIM] IHLAL — emir-adayi etiketleri MUHURLENDI "
              "(basim ve bellek kayitlari muhurlu etiketle yapildi):")
        for i in ihlaller:
            print(f"  - {i}")
    else:
        print("\n[IC DENETIM] ihlal yok "
              f"(muhur {bellek['kapi_muhru'][:12]}…, "
              f"{len(bellek['deneyler'])} deney kaydi, "
              f"{len(bellek['akibetler'])} akibet kaydi / "
              f"{len([a for a in bellek['akibetler'] if a.get('r') is not None])}"
              f" olculmus)")
    bellek_kaydet(bellek)
    n_olc = len([a for a in bellek["akibetler"] if a.get("r") is not None])
    tamam = len(kararlar)
    toplam = len(motor.SYMBOLS)
    if atlanan == 0 and tamam == toplam:
        kosu_durum = f"TAM ({tamam}/{toplam} sembol)"
    elif tamam > 0:
        kosu_durum = f"KISMEN ({tamam} tamam, {atlanan} atlandi)"
    else:
        kosu_durum = f"BASARISIZ (0/{toplam} sembol — karar uretilemedi)"
    print(f"\n[OZET] kosu: {kosu_durum} | surum v{bellek['surum']} | "
          f"aktif {bellek['aktif_varyant']} | kosu #{bellek['kosu_sayaci']} | "
          f"olculmus akibet: {n_olc} | eps={bellek['eps']:.2f} W={bellek['W']}")
    print("Dogruluk sozlesmesi: bu sistem dogrulugu GARANTI ETMEZ; her "
          "kosuda kendi isabetini OLCER ve yalnizca olculebilir iyilesmeyi "
          "tutar (PDF bolum 24 — bilimsel sinir).")


if __name__ == "__main__":
    kosu()
