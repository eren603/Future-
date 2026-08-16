# META3 KARARGAH dogrulama testi — agsiz, deterministik (sahte borsa).
# Kosum: PYTHONDONTWRITEBYTECODE=1 python3 olcum/test_meta3.py
# Cikti artefakti: olcum/test_meta3_cikti.txt
# Kanitlanan davranislar (her biri assert'li):
#  T1  Formul denkligi: meta3.karar_uret'in z/ATR/SMA hesabi v5.4'un
#      signal_engine blogu ile BIT DUZEYINDE ayni sonucu uretir.
#  T2  YON ZORUNLU: her sembol ciktisinda YON satiri var; NOTR yalniz
#      gerekceli.
#  T3  Varyantlar yalnizca SIKILASTIRIR: kapali kapiyi ACAMAZ; acik kapiyi
#      filtre dusurebilir ve gerekce yazilir.
#  T4  HESAP VERME: onceki kosunun onerisi sonraki kosuda muhafazakar
#      kurallarla olculur (ayni-bar stop+hedef -> STOP; dolmayan -> IPTAL).
#  T5  META: n < min_akibet_n iken HOLD (fail-closed); n yeterli fikstürde
#      olculmus ustunluk -> KEEP, gerileme -> ROLLBACK.
#  T6  IMMUTABLE: kapi sabiti degisirse muhur tutmaz -> kosu HALT.
#  T7  Bellek surumleme: .bak anlik goruntusu yazilir; deney kayitlari
#      PDF #10 zorunlu alanlarini tasir.
#  T8  META2/META3 bantlari asilamaz (eps/W immutable bant icinde kalir).
import io
import json
import os
import sys
import contextlib

import numpy as np
import pandas as pd

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)
sys.dont_write_bytecode = True

# --- sahte ccxt (ag yok) ---------------------------------------------------
class _SahteEx:
    def __init__(self, *a, **k):
        pass
    def fetch_ohlcv(self, symbol, timeframe="15m", since=None, limit=1000):
        raise RuntimeError("test fetch_ohlcv'yi monkeypatch'ler")
    def fetch_order_book(self, *a, **k):
        raise RuntimeError("ag yok")
    def fetch_trades(self, *a, **k):
        raise RuntimeError("ag yok")
    def fetch_funding_rate_history(self, *a, **k):
        raise RuntimeError("ag yok")
    def fetch_open_interest(self, *a, **k):
        raise RuntimeError("ag yok")

import types
sys.modules["ccxt"] = types.SimpleNamespace(binanceusdm=_SahteEx)

import btc_karargah_v5_4 as motor          # noqa: E402
import meta3_karargah as m3                # noqa: E402

# bellek/override dosyalarini test sandigina yonlendir (depoya yazilmaz)
SANDIK = os.path.join(BURASI, "_meta3_test_sandik")
os.makedirs(SANDIK, exist_ok=True)
m3.BELLEK_YOLU = os.path.join(SANDIK, "bellek.json")
m3.OVERRIDE_YOLU = os.path.join(SANDIK, "override.json")
for f in os.listdir(SANDIK):
    os.remove(os.path.join(SANDIK, f))

SONUC = []
def kayit(ad, kosul, detay=""):
    assert kosul, f"{ad} BASARISIZ {detay}"
    SONUC.append(f"  GECTI: {ad} {detay}")

def sentetik(n, drift, seed, freq="15min"):
    rng = np.random.default_rng(seed)
    cl = 100 * np.exp(np.cumsum(rng.normal(drift, 0.004, n)))
    return pd.DataFrame(
        {"open": cl, "high": cl * 1.003, "low": cl * 0.997, "close": cl,
         "volume": np.full(n, 1000.0)},
        index=pd.date_range("2026-01-01", periods=n, freq=freq, tz="UTC"))

VERI = {}
def sahte_fetch(symbol, timeframe, limit):
    return VERI[(symbol, timeframe)].copy()

motor.fetch_ohlcv = sahte_fetch
m3.motor.fetch_ohlcv = sahte_fetch
motor.fetch_recent_trades = lambda s, lookback_min=60: pd.DataFrame(
    columns=["timestamp", "price", "amount"])
motor.fetch_order_book = lambda s: (None, None)
motor.fetch_funding_oi = lambda s: (pd.DataFrame(), float("nan"))
m3.motor.SYMBOLS = ["BTC/USDT", "ETH/USDT"]

def veri_kur(seed=1):
    VERI.clear()
    for i, sym in enumerate(["BTC/USDT", "ETH/USDT"]):
        VERI[(sym, motor.TF_15M)] = sentetik(1400, 0.0006, seed + i)
        VERI[(sym, motor.TF_4H)] = sentetik(400, 0.0025, seed + 10 + i,
                                            freq="4h")

# T1 — formul denkligi ------------------------------------------------------
veri_kur()
df15 = VERI[("BTC/USDT", motor.TF_15M)].copy()
close = df15["close"].astype(float)
sma20 = close.rolling(window=20).mean()
sd20 = close.rolling(window=20).std(ddof=0)
z_v54 = ((close - sma20) / (sd20 + 1e-12)).shift(periods=1)
hl = (df15["high"] - df15["low"]).abs()
hc = (df15["high"] - close.shift(periods=1)).abs()
lc = (df15["low"] - close.shift(periods=1)).abs()
atr_v54 = pd.concat([hl, hc, lc], axis=1).max(axis=1) \
    .rolling(motor.ATR_LEN).mean().shift(periods=1)
k = m3.karar_uret("BTC/USDT", VERI[("BTC/USDT", motor.TF_4H)], df15,
                  VERI[("BTC/USDT", motor.TF_4H)], df15)
if k["giris"] is not None and k["kapi"] != "ACIK":
    beklenen_stop = (float(close.iloc[-1]) - motor.ATR_SL_MULT *
                     float(atr_v54.iloc[-1]) if k["yon"] == "LONG"
                     else float(close.iloc[-1]) + motor.ATR_SL_MULT *
                     float(atr_v54.iloc[-1]))
    kayit("T1 stop = v5.4 formuluyle bit duzeyinde ayni",
          k["stop"] == beklenen_stop, f"({k['stop']} == {beklenen_stop})")
    kayit("T1b hedef = SMA20 birebir",
          k["hedef"] == float(sma20.iloc[-1]))
else:
    kayit("T1 seviye uretildi", k["giris"] is not None,
          f"(kapi={k['kapi']})")

# T2 — YON ZORUNLU ----------------------------------------------------------
kayit("T2 yon alani dolu ve gecerli",
      k["yon"] in ("LONG", "SHORT", "NOTR") and len(k["yon_kaynak"]) > 5,
      f"(yon={k['yon']}, kaynak={k['yon_kaynak'][:50]})")

# T3 — varyant yalnizca SIKILASTIRIR ---------------------------------------
acik = dict(k); acik["kapi"] = "ACIK"; acik["etiket"] = "EMIR-ADAYI"
acik["golge"] = {"komposit_uyum": False, "tick_uyum": None}
v1, dusen1 = m3.varyant_karari(dict(acik), "V1_komposit_teyit")
kayit("T3 acik kapiyi V1 filtresi dusurdu (gerekceli)",
      v1["kapi"] == "KAPALI" and "sikilastirma" in v1["kapi_gerekce"])
kapali = dict(k); kapali["kapi"] = "KAPALI"; kapali["etiket"] = "BILGI"
kapali["golge"] = {"komposit_uyum": True, "tick_uyum": True}
v2, _ = m3.varyant_karari(dict(kapali), "V2_cift_teyit")
kayit("T3b kapali kapiyi hicbir varyant ACAMAZ", v2["kapi"] == "KAPALI")
v0, _ = m3.varyant_karari(dict(acik), "V0_taban")
kayit("T3c taban varyant acik kapiya dokunmaz", v0["kapi"] == "ACIK")

# T4 — HESAP VERME (akibet olcumu) -----------------------------------------
bars = sentetik(60, 0.0, 99)
oneri = {"sembol": "X", "yon": "LONG", "giris": float(bars["close"].iloc[5]),
         "stop": 0.0, "hedef": 1e9,
         "bar_ts": int(bars.index[3].value // 1_000_000)}
# stop=0/hedef=1e9: dolum olur, sonuc cikmaz -> None (acik pozisyon)
kayit("T4a acik pozisyon: sonuc None (uydurma kapanis yok)",
      m3.akibet_olc(oneri, bars) is None)
o2 = dict(oneri)
o2["stop"] = float(bars["low"].iloc[6:].min()) * 1.001   # stop kesin gelir
o2["hedef"] = float(bars["high"].iloc[6:].max()) * 0.999  # hedef de gelir
s2 = m3.akibet_olc(o2, bars)
kayit("T4b ayni pencerede stop+hedef -> muhafazakar STOP",
      s2 is not None and s2["sonuc"] == "STOP" and s2["r"] == -1.0,
      f"({s2})")
o3 = dict(oneri); o3["giris"] = 1e-9  # LONG alis limiti fiyatin COK altinda: hic dolmaz
s3 = m3.akibet_olc(o3, bars)
kayit("T4c dolmayan oneri TIME_STOP sonrasi IPTAL, R yazilmaz",
      s3 is not None and s3["sonuc"] == "IPTAL" and s3["r"] is None,
      f"({s3})")

# T5 — META: HOLD / KEEP / ROLLBACK ----------------------------------------
# v1.1: kesif kapisi deterministik hash takvimiyle — testte kesfin ACIK
# oldugu bir kosu sayaci secilir (eps=0.3, bant ustu)
KESIF_ACIK = next(i for i in range(500) if m3.kesif_zamani(i, 0.3))
KESIF_KAPALI = next(i for i in range(500) if not m3.kesif_zamani(i, 0.3))
bellek = m3.bellek_yukle()
bellek["eps"] = 0.3
bellek["kosu_sayaci"] = KESIF_ACIK
karar, detay = m3.meta_dongusu(bellek, 1.0, 60.0)
kayit("T5a olculmus akibet yokken META = HOLD", karar == "HOLD", f"({detay})")
# fikstur: taban icin 10 olculmus akibet (ort R -0.2), V1 alt kumesi ustun
bellek["akibetler"] = []
for i in range(10):
    bellek["akibetler"].append({
        "sembol": "X", "varyant": "V0_taban", "etiket": "EMIR-ADAYI",
        "golge": {"komposit_uyum": i < 8, "tick_uyum": None},
        "sonuc": "HEDEF" if (i < 8 and i % 2 == 0) else "STOP",
        "r": 1.5 if (i < 8 and i % 2 == 0) else -1.0})
bellek["_son_p_max"] = 0.01
karar2, detay2 = m3.meta_dongusu(bellek, 1.0, 60.0)
kayit("T5b olcumle ustun varyant -> KEEP (varyant degisti)",
      karar2 == "KEEP" and bellek["aktif_varyant"] == "V1_komposit_teyit",
      f"({detay2})")
# gerileme fiksturu: V1 alt kumesi tabandan kotu -> ROLLBACK
bellek["akibetler"] = []
for i in range(12):
    v1_de = i < 8
    bellek["akibetler"].append({
        "sembol": "X", "varyant": "V0_taban", "etiket": "EMIR-ADAYI",
        "golge": {"komposit_uyum": v1_de, "tick_uyum": None},
        "sonuc": "STOP" if v1_de else "HEDEF",
        "r": -1.0 if v1_de else 1.5})
karar3, detay3 = m3.meta_dongusu(bellek, 1.0, 60.0)
kayit("T5c gerileyen varyant olcumle TABANA doner (KEEP ya da ROLLBACK)",
      karar3 in ("KEEP", "ROLLBACK")
      and bellek["aktif_varyant"] == "V0_taban", f"({karar3}: {detay3})")
# T5d — GERCEK ROLLBACK dali: aday J'si hesaplanamazken (p_max None ->
# J=None -> aday KEEP edilemez) aktif varyant tabandan olcumle kotu ise
# rollback tetiklenmeli.
bellek["aktif_varyant"] = "V1_komposit_teyit"
bellek["_son_p_max"] = None
karar4, detay4 = m3.meta_dongusu(bellek, 1.0, 60.0)
kayit("T5d aday J olculemezken gerileme -> ROLLBACK dali",
      karar4 == "ROLLBACK" and bellek["aktif_varyant"] == "V0_taban",
      f"({karar4}: {detay4})")

# T5e — kesif takvimi KAPALIYKEN aday degerlendirilmez (eps tuketicisi) ----
bellek["aktif_varyant"] = "V0_taban"
bellek["kosu_sayaci"] = KESIF_KAPALI
onceki_deney_n = len(bellek["deneyler"])
karar5, detay5 = m3.meta_dongusu(bellek, 1.0, 60.0)
son_kayitlar = bellek["deneyler"][onceki_deney_n:]
kayit("T5e kesif kapaliyken aday KEEP/REJECT kaydi yok (eps FIILEN okunur)",
      all(d["decision"] not in ("KEEP", "REJECT") for d in son_kayitlar
          if d["optimizer_version"] == "meta"),
      f"({[d['decision'] for d in son_kayitlar]})")
# v1.2: eps=0'da bile ZORUNLU kesif periyodu vardir (yutucu-durum giderimi);
# eps=0 yalniz periyot DISINDA kesif acmaz.
_per = m3.IMMUTABLE_PLANE["zorunlu_kesif_periyodu"]
kayit("T5f eps=0.0 periyot disinda kesif acmaz (periyotta ZORUNLU acar)",
      not any(m3.kesif_zamani(i, 0.0) for i in range(300) if i % _per != 0
              or i == 0)
      and m3.kesif_zamani(_per, 0.0))

# T5g — J=None -> HOLD, karantina ARTMAZ (olculmemis ret yasagi) -----------
bellek["kosu_sayaci"] = KESIF_ACIK
bellek["_son_p_max"] = None          # R bileseni VERI YOK -> J=None
bellek["karantina"] = {}
onceki_deney_n = len(bellek["deneyler"])
m3.meta_dongusu(bellek, 1.0, 60.0)
yeni = [d for d in bellek["deneyler"][onceki_deney_n:]
        if d["optimizer_version"] == "meta"]
kayit("T5g J=None iken REJECT yok, HOLD var, karantina bos",
      all(d["decision"] != "REJECT" for d in yeni)
      and bellek["karantina"] == {},
      f"(kararlar={[d['decision'] for d in yeni]}, "
      f"karantina={bellek['karantina']})")

# T6 — IMMUTABLE muhur ------------------------------------------------------
veri_kur()
m3.bellek_kaydet(m3.bellek_yukle())          # temiz bellek + ilk muhur icin
for f in os.listdir(SANDIK):
    os.remove(os.path.join(SANDIK, f))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m3.kosu()                                 # kosu 1: muhur kaydedilir
cikti1 = buf.getvalue()
kayit("T6a ilk kosu muhru kaydetti", "Kapi muhru ILK kosuda" in cikti1)
eski_alpha = motor.ALPHA
motor.ALPHA = 0.99                            # sabit kurcalandi (test!)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m3.kosu()
motor.ALPHA = eski_alpha
kayit("T6b sabit degisince HALT (muhur tutmadi)",
      "HALT: kapi sabitleri" in buf.getvalue())
# T6c — muhur PLANE degerlerini de kapsar (denetim bulgusu kapatildi)
eski_wq = m3.IMMUTABLE_PLANE["w_Q"]
m3.IMMUTABLE_PLANE["w_Q"] = 9.9
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m3.kosu()
m3.IMMUTABLE_PLANE["w_Q"] = eski_wq
kayit("T6c PLANE degeri degisince de HALT (muhur kapsami genisledi)",
      "HALT: kapi sabitleri" in buf.getvalue())
# T6d — bozuk bellek dosyasi -> yakalanmamis cokme DEGIL, temiz HALT
with open(m3.BELLEK_YOLU, "w", encoding="utf-8") as f:
    f.write("{bozuk json!!")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m3.kosu()
kayit("T6d bozuk bellek -> temiz HALT (fail-closed)",
      "HALT: bellek dosyasi bozuk" in buf.getvalue())
os.remove(m3.BELLEK_YOLU)          # temiz baslangic (T7 icin)
if os.path.exists(m3.BELLEK_YOLU + ".bak"):
    os.remove(m3.BELLEK_YOLU + ".bak")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m3.kosu()                       # yeni ilk kosu (muhur yeniden kaydedilir)

# T7 — bellek surumleme + deney alanlari -----------------------------------
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m3.kosu()                                 # kosu 2 (muhur artik tutuyor)
cikti2 = buf.getvalue()
kayit("T7a .bak anlik goruntusu var",
      os.path.exists(m3.BELLEK_YOLU + ".bak"))
with open(m3.BELLEK_YOLU, encoding="utf-8") as f:
    bel = json.load(f)
zorunlu = ("experiment_id", "parent_version", "optimizer_version",
           "hypothesis", "patch", "metrics", "cost", "latency", "risk",
           "decision")
kayit("T7b her deney kaydi PDF #10 alanlarini tasir",
      all(all(a in d for a in zorunlu) for d in bel["deneyler"]),
      f"({len(bel['deneyler'])} kayit)")
kayit("T7c evrim zinciri soy tutuyor",
      bel["evrim"][0]["ebeveyn"] is None and
      all(e["ebeveyn"] == bel["evrim"][i]["surum"]
          for i, e in enumerate(bel["evrim"][1:])))

# T2 (kosu ciktisinda) — her sembolde YON satiri
for sym in ("BTC/USDT", "ETH/USDT"):
    kayit(f"T2b ciktida {sym} YON satiri var",
          f"=== {sym} ===" in cikti2 and "YON:" in cikti2)

# T9 — v1.1 denetim-kapatma testleri ---------------------------------------
# T9a: GECERSIZ oneri (NaN stop) R uydurmaz
bars9 = sentetik(30, 0.0, 7)
o9 = {"sembol": "X", "yon": "LONG", "giris": 100.0, "stop": float("nan"),
      "hedef": 120.0, "bar_ts": int(bars9.index[2].value // 1_000_000)}
s9 = m3.akibet_olc(o9, bars9)
kayit("T9a NaN seviyeli oneri -> GECERSIZ, R=None (zehirleme yok)",
      s9 is not None and s9["sonuc"] == "GECERSIZ" and s9["r"] is None,
      f"({s9})")
# T9b: gap dolumu — LONG girisi barin ustunden aciga dusen fiyatta dolar
gap = sentetik(10, 0.0, 8)
gv = gap.copy()
gv.iloc[3, gv.columns.get_loc("low")] = 50.0     # giris 90'in altina gap
gv.iloc[3, gv.columns.get_loc("high")] = 60.0    # aralik 90'i icermiyor
gv.iloc[4:, gv.columns.get_loc("low")] = 40.0    # stop kesin gelir
o9b = {"sembol": "X", "yon": "LONG", "giris": 90.0, "stop": 45.0,
       "hedef": 200.0, "bar_ts": int(gv.index[1].value // 1_000_000)}
s9b = m3.akibet_olc(o9b, gv)
kayit("T9b gap'ten gecen LONG dolumu artik OLCULUYOR (lo<=giris)",
      s9b is not None and s9b["sonuc"] == "STOP", f"({s9b})")
# T9c: varyant secim populasyonu YALNIZ EMIR-ADAYI (BILGI karismaz)
b9 = m3.bellek_yukle()
b9["akibetler"] = (
    [{"sembol": "X", "etiket": "EMIR-ADAYI", "golge": {}, "sonuc": "HEDEF",
      "r": 1.0} for _ in range(4)]
    + [{"sembol": "X", "etiket": "BILGI", "golge": {}, "sonuc": "STOP",
        "r": -1.0} for _ in range(50)])
oz9 = m3._varyant_akibet_ozeti(b9, "V0_taban")
kayit("T9c BILGI akibetleri varyant olcumune KARISMAZ",
      oz9["n"] == 4 and oz9["ort_r"] == 1.0, f"({oz9})")
# T9d: muhur SIRASI — ihlalli karar hem basimda hem BELLEKTE muhurlu
kk = {"sembol": "T", "yon": "LONG", "yon_kaynak": "test", "kapi": "KAPALI",
      "kapi_gerekce": "x", "etiket": "EMIR-ADAYI", "giris": 1.0, "stop": 0.9,
      "hedef": 1.2, "kural": None, "oos": None, "p_max": None,
      "golge": {}, "bar_ts": 123}
ihl = m3.ic_denetim(b9, [kk], True)
kayit("T9d ic_denetim ihlali yakaladi ve etiketi muhurledi",
      len(ihl) > 0 and kk["etiket"].startswith("BILGI (MUHURLU"),
      f"(etiket={kk['etiket']})")

# T10 — v1.2 (2. tur denetim) kapatma testleri ------------------------------
# T10a: akibet zinciri — sahte kayit enjeksiyonu HALT'a dusurur
b10 = m3.bellek_yukle()
m3.akibet_ekle(b10, {"sembol": "X", "etiket": "EMIR-ADAYI", "golge": {},
                     "sonuc": "HEDEF", "r": 1.5, "oneri_imza": "X|1|V0"})
ok10, _ = m3.akibet_zinciri_dogrula(b10)
kayit("T10a zincirli ekleme dogrulaniyor", ok10)
b10["akibetler"].append({"sembol": "X", "etiket": "EMIR-ADAYI", "golge": {},
                         "sonuc": "HEDEF", "r": 9.9,
                         "oneri_imza": "SAHTE"})   # zincirsiz enjeksiyon
ok10b, kirik = m3.akibet_zinciri_dogrula(b10)
kayit("T10b zincirsiz sahte kayit YAKALANIYOR", not ok10b and kirik == 1,
      f"(kirik indeks={kirik})")
# uctan uca: bozuk zincirli bellek kosuda HALT
m3.bellek_kaydet(b10)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    m3.kosu()
kayit("T10c bozuk zincirle kosu HALT",
      "akibet defteri butunlugu bozuk" in buf.getvalue())
os.remove(m3.BELLEK_YOLU)
if os.path.exists(m3.BELLEK_YOLU + ".bak"):
    os.remove(m3.BELLEK_YOLU + ".bak")
# T10d: dolum barinda HEDEF sayilmaz (iyimserlik giderimi) — ayni barda
# dolum + hedef degdi ama STOP degmedi -> sonuc None (olcum surer)
b_t10 = sentetik(10, 0.0, 12)
bt = b_t10.copy()
bt.iloc[3, bt.columns.get_loc("low")] = 89.0    # dolum (giris 90)
bt.iloc[3, bt.columns.get_loc("high")] = 130.0  # hedef 120 ayni barda degdi
bt.iloc[4:, bt.columns.get_loc("high")] = 80.0  # sonraki barlar hedefe degmez
bt.iloc[4:, bt.columns.get_loc("low")] = 70.0   # stop 60'a da degmez
o10 = {"sembol": "X", "yon": "LONG", "giris": 90.0, "stop": 60.0,
       "hedef": 120.0, "bar_ts": int(bt.index[1].value // 1_000_000)}
s10 = m3.akibet_olc(o10, bt)
kayit("T10d dolum barindaki hedef SAYILMAZ (bar-ici sira bilinmez)",
      s10 is None, f"({s10})")
bt2 = bt.copy()
bt2.iloc[5, bt2.columns.get_loc("high")] = 121.0  # hedef SONRAKI barda
s10b = m3.akibet_olc(o10, bt2)
kayit("T10e sonraki barda hedef SAYILIR",
      s10b is not None and s10b["sonuc"] == "HEDEF", f"({s10b})")
# T10f: zorunlu kesif — eps=0 olsa bile periyotta kesif acilir
per = m3.IMMUTABLE_PLANE["zorunlu_kesif_periyodu"]
kayit("T10f eps=0'da zorunlu kesif periyodu calisiyor (yutucu durum yok)",
      m3.kesif_zamani(per, 0.0) and m3.kesif_zamani(2 * per, 0.0)
      and not any(m3.kesif_zamani(i, 0.0)
                  for i in range(1, per) if i % per != 0))
# T10g: S=0 (ic denetim ihlali) -> META HOLD, varyant karari yok
b10g = m3.bellek_yukle()
b10g["eps"] = 0.3
b10g["kosu_sayaci"] = KESIF_ACIK
for i in range(10):
    m3.akibet_ekle(b10g, {"sembol": "X", "varyant": "V0_taban",
                          "etiket": "EMIR-ADAYI",
                          "golge": {"komposit_uyum": True, "tick_uyum": None},
                          "sonuc": "HEDEF", "r": 1.0,
                          "oneri_imza": f"X|{i}|V0"})
b10g["_son_p_max"] = 0.01
kr, dt = m3.meta_dongusu(b10g, 1.0, 60.0, guvenlik_ok=False)
kayit("T10g ic denetim ihlalinde META = HOLD (S=0 olculdu)",
      kr == "HOLD" and "S=0" in dt, f"({dt})")
# T10h: .bak varken asil dosya yoksa sessiz sifirlama YOK -> BellekBozuk
m3.bellek_kaydet(m3.bellek_yukle())
m3.bellek_kaydet(m3.bellek_yukle())        # .bak olustur
os.remove(m3.BELLEK_YOLU)                  # asil dosya kayboldu
try:
    m3.bellek_yukle()
    kayit("T10h .bak varken sessiz sifirlama engellendi", False)
except m3.BellekBozuk:
    kayit("T10h .bak varken sessiz sifirlama engellendi (BellekBozuk)", True)
os.remove(m3.BELLEK_YOLU + ".bak")

# T8 — META2/META3 bant disina cikamaz -------------------------------------
b2 = m3.bellek_yukle()
b2["kosu_sayaci"] = b2["W"]
b2["deneyler"] = [{"experiment_id": f"E{i}", "parent_version": 1,
                   "optimizer_version": "meta", "hypothesis": "x",
                   "patch": {}, "metrics": {}, "cost": 0, "latency": 0,
                   "risk": "dusuk", "decision": "KEEP"} for i in range(20)]
b2["eps"] = 0.30
m3.meta2_dongusu(b2)
kayit("T8a eps ust banttan cikamadi",
      m3.IMMUTABLE_PLANE["eps_bant"][0] <= b2["eps"]
      <= m3.IMMUTABLE_PLANE["eps_bant"][1], f"(eps={b2['eps']})")
b2["kosu_sayaci"] = b2["W"] * b2["W"]
b2["deneyler"] += [{"experiment_id": f"M{i}", "parent_version": 1,
                    "optimizer_version": "meta2", "hypothesis": "x",
                    "patch": {}, "metrics": {}, "cost": 0, "latency": 0,
                    "risk": "dusuk", "decision": "TUT"} for i in range(3)]
b2["W"] = 50
m3.meta3_dongusu(b2)
kayit("T8b W ust banttan cikamadi",
      m3.IMMUTABLE_PLANE["W_bant"][0] <= b2["W"]
      <= m3.IMMUTABLE_PLANE["W_bant"][1], f"(W={b2['W']})")

print("\n".join(SONUC))
print(f"\nSONUC: {len(SONUC)} kontrol, 0 basarisiz.")
