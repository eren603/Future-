# LLM İşlem Zinciri → Sayısal Trading Sistemi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LLM işlem zincirinin 12 halkasını sayısal trading karşılıklarıyla çalışır biçimde kuran, her barda zorunlu YÖN + sürekli STAKE (`f*`) üreten, tek dosyalık bir karar-destek sistemi yazmak.

**Architecture:** Tek Python dosyası (`llm_trading_v3.py`), yalnız standart kütüphane. İç yapı sekiz bölüme ayrılır: matematik çekirdeği → kalibrasyon → geometri → veri adaptörü → token/model → decoding → stake → çıktı/defter. Saf matematik fonksiyonları veri erişiminden tamamen bağımsızdır ve ağ olmadan test edilir. Model katmanı (embedding/attention/FFN/başlık) deterministik tohumla çalışır; öğrenilen tek parça logit başlığı ile giriş izdüşümüdür.

**Tech Stack:** Python 3.11+, yalnız stdlib (`math`, `json`, `csv`, `random`, `statistics`, `urllib`, `unittest`, `argparse`, `zlib`, `decimal`, `pathlib`, `datetime`). Harici paket YOK (Pydroid 3 kısıtı).

## Global Constraints

- **Tek dosya:** tüm sistem `llm_trading_v3.py` içinde. Testler ayrı `test_llm_trading_v3.py` dosyasında, ayrıca `--self-test` bayrağıyla gömülü hızlı denetim.
- **Yalnız stdlib:** hiçbir `pip install` gerekmez. `numpy`, `pandas`, `requests` KULLANILMAZ.
- **Güvenlik sınırı:** API anahtarı, secret, HMAC, imzalı uç, emir ucu, iptal ucu kodda BULUNMAZ. Yalnız public GET. Kâğıt defteri yereldir.
- **Uydurma yasağı:** erişilemeyen kanal `None` ile işaretlenir; nötr `0.0` enjekte EDİLMEZ. Eksik veri kapsam skorunu düşürür.
- **Determinizm:** aynı girdi + aynı tohum = aynı çıktı. `random` yalnız tohumlanmış `random.Random` üzerinden kullanılır; modül düzeyi `random.*` çağrısı yasak.
- **Sözlük:** `V = {LONG, SHORT}`. Üçüncü sınıf (HOLD/FLAT) EKLENMEZ. Her barda yön ve seviyeler koşulsuz üretilir.
- **Stake:** `f*` maliyet-sonrası asimetrik Kelly; `f* = 0` meşru bir değerdir, "karar vermeme" değildir.
- **λ varsayılan `1.0`** (tam Kelly). Çıktı `λ ∈ {1.0, 0.5, 0.25}` için stake'i yan yana gösterir.
- **Türkçe çıktı, ASCII kod:** kullanıcıya görünen metin Türkçe; değişken/fonksiyon adları ASCII.
- **Satır sınırı:** tek fonksiyon 60 satırı aşmaz; aşarsa bölünür.

## File Structure

| Dosya | Sorumluluk |
|---|---|
| `llm_trading_v3.py` | Tüm sistem. Bölümler sırayla: (1) sabitler/yardımcı matematik, (2) maliyet+Kelly, (3) kalibrasyon metrikleri, (4) shrinkage, (5) geometri araması, (6) veri adaptörleri, (7) token/model, (8) decoding+self-consistency, (9) çıktı+defter, (10) CLI+self-test. |
| `test_llm_trading_v3.py` | `unittest` paketi. Sınıf başına bir test grubu: matematik, kalibrasyon, geometri, sızıntı, ölü-halka, determinizm, güvenlik. |

---

### Task 1: İskelet, güvenlik sınırı ve determinizm

**Files:**
- Create: `llm_trading_v3.py`
- Create: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: yok (ilk görev)
- Produces: `SURUM: str`, `SEMBOLLER: list[str]`, `tohumlu_rng(*parcalar) -> random.Random`, `sabit_kimlik(*parcalar) -> int`, `kirp(x, alt, ust) -> float`

- [x] **Step 1: Write the failing test**

```python
# test_llm_trading_v3.py
import unittest
import re
import pathlib
import llm_trading_v3 as m


class GuvenlikTesti(unittest.TestCase):
    """Kod canli emir gonderemez: yasakli desenler dosyada BULUNMAMALI."""

    YASAK = [
        r"api[_-]?key", r"apiKey", r"secret", r"hmac", r"signature=",
        r"/fapi/v1/order", r"/api/v5/trade/order", r"privateKey",
    ]

    def test_yasakli_desen_yok(self):
        kaynak = pathlib.Path(m.__file__).read_text(encoding="utf-8")
        # kendi yasak listesini sayma: liste tanimini cikar
        kaynak_govde = kaynak
        for desen in self.YASAK:
            bulunan = re.findall(desen, kaynak_govde, re.IGNORECASE)
            self.assertEqual(bulunan, [], f"yasakli desen bulundu: {desen} -> {bulunan}")


class DeterminizmTesti(unittest.TestCase):
    def test_ayni_tohum_ayni_dizi(self):
        a = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        b = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        self.assertEqual(a, b)

    def test_farkli_tohum_farkli_dizi(self):
        a = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        b = [m.tohumlu_rng("x", 2).random() for _ in range(5)]
        self.assertNotEqual(a, b)

    def test_sabit_kimlik_deterministik(self):
        self.assertEqual(m.sabit_kimlik("BTCUSDT", "15m", 3), m.sabit_kimlik("BTCUSDT", "15m", 3))
        self.assertNotEqual(m.sabit_kimlik("BTCUSDT", "15m", 3), m.sabit_kimlik("BTCUSDT", "15m", 4))


class KirpTesti(unittest.TestCase):
    def test_sinirlar(self):
        self.assertEqual(m.kirp(5.0, -1.0, 1.0), 1.0)
        self.assertEqual(m.kirp(-5.0, -1.0, 1.0), -1.0)
        self.assertEqual(m.kirp(0.3, -1.0, 1.0), 0.3)

    def test_gecersiz_girdi_alt_sinira_duser(self):
        self.assertEqual(m.kirp(None, -1.0, 1.0), -1.0)
        self.assertEqual(m.kirp(float("nan"), -1.0, 1.0), -1.0)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3 -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'llm_trading_v3'`

- [x] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM islem zincirinin sayisal trading karsiligi (v3).

Iki eksen uretir: YON (zorunlu argmax, sozluk {LONG, SHORT}) ve
STAKE (f*, surekli, maliyet sonrasi asimetrik Kelly).

Yalniz public GET. Canli emir, anahtar, imzali uc YOKTUR.
"""

import math
import zlib
import random

SURUM = "llm-trading-v3"
SEMBOLLER = ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]
YON_SOZLUGU = ("LONG", "SHORT")


def sabit_kimlik(*parcalar):
    """Deterministik 32-bit kimlik. Ayni girdi daima ayni sayi."""
    metin = "|".join(str(p) for p in parcalar)
    return zlib.crc32(metin.encode("utf-8")) & 0xFFFFFFFF


def tohumlu_rng(*parcalar):
    """Tohumlanmis RNG. Modul duzeyi random.* cagrisi YASAK."""
    return random.Random(sabit_kimlik(*parcalar))


def kirp(x, alt=-1.0, ust=1.0):
    """Sayiyi [alt, ust] araligina kirpar. Gecersiz girdi alt sinira duser."""
    try:
        deger = float(x)
    except (TypeError, ValueError):
        return alt
    if math.isnan(deger) or math.isinf(deger):
        return alt
    return max(alt, min(ust, deger))
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3 -v`
Expected: PASS (6 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: iskelet, guvenlik siniri ve determinizm cekirdegi"
```

---

### Task 2: Maliyet ve asimetrik Kelly çekirdeği

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 2 eklenir)
- Modify: `test_llm_trading_v3.py` (yeni test sınıfı eklenir)

**Interfaces:**
- Consumes: `kirp` (Task 1)
- Produces:
  - `maliyet_r(giris: float, stop_mesafesi: float, komisyon: float, kayma: float, funding: float) -> float`
  - `kelly_asimetrik(p: float, b: float, a: float) -> float`
  - `basabas_p(b: float, a: float) -> float | None`
  - `net_kanatlar(R: float, cost_r: float) -> tuple[float, float]` → `(b, a)`

- [x] **Step 1: Write the failing test**

```python
class KellyTesti(unittest.TestCase):
    def test_net_kanatlar(self):
        b, a = m.net_kanatlar(R=1.3333, cost_r=0.6)
        self.assertAlmostEqual(b, 0.7333, places=4)
        self.assertAlmostEqual(a, 1.6000, places=4)

    def test_basabas_p_bilinen_deger(self):
        # cost_r=0.60, R=1.3333 -> b=0.7333, a=1.6 -> p0 = a/(a+b) = 0.6857
        b, a = m.net_kanatlar(1.3333, 0.60)
        self.assertAlmostEqual(m.basabas_p(b, a), 0.6857, places=4)

    def test_basabas_p_maliyetsiz(self):
        b, a = m.net_kanatlar(1.3333, 0.0)
        self.assertAlmostEqual(m.basabas_p(b, a), 0.4286, places=4)

    def test_kelly_basabasin_altinda_sifir(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        # p0 = 0.6857; altindaki her p icin f* = 0
        for p in (0.50, 0.60, 0.68):
            self.assertEqual(m.kelly_asimetrik(p, b, a), 0.0, f"p={p} icin f* 0 olmali")

    def test_kelly_basabasin_ustunde_pozitif(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        f = m.kelly_asimetrik(0.70, b, a)
        self.assertGreater(f, 0.0)
        self.assertAlmostEqual(f, 0.0284, places=3)

    def test_kelly_negatif_kanat_sifir(self):
        # b <= 0: hicbir p ile bahis yok
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        self.assertLessEqual(b, 0.0)
        self.assertEqual(m.kelly_asimetrik(0.99, b, a), 0.0)

    def test_basabas_p_negatif_kanatta_none(self):
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        self.assertIsNone(m.basabas_p(b, a))

    def test_maliyet_r_hesabi(self):
        # 2 * giris * (komisyon+kayma) / stop_mesafesi, funding eklenir
        cr = m.maliyet_r(giris=100.0, stop_mesafesi=0.15,
                         komisyon=0.0004, kayma=0.0005, funding=0.0)
        self.assertAlmostEqual(cr, (2 * 100.0 * 0.0009) / 0.15, places=8)

    def test_maliyet_r_sifir_stopta_sonsuz_degil(self):
        cr = m.maliyet_r(100.0, 0.0, 0.0004, 0.0005, 0.0)
        self.assertTrue(math.isfinite(cr))
        self.assertGreater(cr, 1000.0)
```

`test_llm_trading_v3.py` başına `import math` eklenir.

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.KellyTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'net_kanatlar'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 2
# Maliyet ve stake: asimetrik Kelly, maliyet SONRASI.
# f* = 0 mesru bir degerdir; "karar vermeme" DEGILDIR.

EPSILON = 1e-12


def maliyet_r(giris, stop_mesafesi, komisyon, kayma, funding):
    """Islem maliyetini R birimine cevirir.

    Gidis-donus komisyon + kayma nominal uzerinden, funding dogrudan eklenir.
    stop_mesafesi 0'a giderse maliyet buyur ama sonsuz olmaz.
    """
    mesafe = max(abs(float(stop_mesafesi)), EPSILON)
    nominal = 2.0 * abs(float(giris)) * (float(komisyon) + float(kayma))
    return (nominal + abs(float(funding)) * abs(float(giris))) / mesafe


def net_kanatlar(R, cost_r):
    """Maliyet sonrasi kazanc (b) ve kayip (a) kanatlari, R biriminde."""
    b = float(R) - float(cost_r)
    a = 1.0 + float(cost_r)
    return b, a


def basabas_p(b, a):
    """f* > 0 icin gereken en kucuk p. Kanat negatifse None (imkansiz)."""
    if b <= 0.0:
        return None
    return a / (a + b)


def kelly_asimetrik(p, b, a):
    """Asimetrik Kelly kesri. f* = (p*b - q*a) / (a*b), negatifse 0."""
    if b <= 0.0 or a <= 0.0:
        return 0.0
    p = kirp(p, 0.0, 1.0)
    q = 1.0 - p
    f = (p * b - q * a) / (a * b)
    return max(0.0, f)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.KellyTesti -v`
Expected: PASS (9 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: maliyet sonrasi asimetrik Kelly ve basabas kimligi"
```

---

### Task 3: Kalibrasyon metrikleri

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 3)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `kirp` (Task 1)
- Produces:
  - `wilson_araligi(basari: int, deneme: int, z: float = 1.96) -> tuple[float, float]`
  - `ece(ciftler: list[tuple[float, int]], bin_sayisi: int = 10) -> float | None`
  - `ece_duyarlilik(ciftler, bin_listesi=(5, 10, 15, 20)) -> dict`
  - `mce(ciftler, bin_sayisi=10) -> float | None`
  - `brier(ciftler) -> float | None`
  - `auroc(ciftler) -> float | None`
  - `grup_ece(ciftler_gruplu: dict[str, list], bin_sayisi=10) -> dict` → `{"gruplar": {...}, "en_kotu": (ad, deger)}`

`ciftler` biçimi: `[(p_long, y), ...]` — `p_long` LONG olasılığı, `y ∈ {0,1}` (1 = LONG doğruydu).

- [x] **Step 1: Write the failing test**

```python
class KalibrasyonMetrikTesti(unittest.TestCase):
    def test_wilson_bilinen_deger(self):
        alt, ust = m.wilson_araligi(17, 48)
        self.assertAlmostEqual(alt, 0.2343, places=3)
        self.assertAlmostEqual(ust, 0.4956, places=3)

    def test_wilson_sifir_deneme(self):
        alt, ust = m.wilson_araligi(0, 0)
        self.assertEqual((alt, ust), (0.0, 1.0))

    def test_ece_mukemmel_kalibre_sifir(self):
        # p=1.0 ve daima dogru; p=0.0 ve daima yanlis -> ECE = 0
        ciftler = [(1.0, 1)] * 50 + [(0.0, 0)] * 50
        self.assertAlmostEqual(m.ece(ciftler), 0.0, places=9)

    def test_ece_tam_ters_bir(self):
        ciftler = [(1.0, 0)] * 50 + [(0.0, 1)] * 50
        self.assertAlmostEqual(m.ece(ciftler), 1.0, places=9)

    def test_ece_tek_bine_cokme_tespiti(self):
        # tum guvenler 0.33-0.34 bandinda -> tek bin
        ciftler = [(0.335, 1) if i % 3 == 0 else (0.335, 0) for i in range(48)]
        rapor = m.ece_duyarlilik(ciftler)
        self.assertTrue(rapor["tek_bine_cokme"], "tek bine cokme tespit edilmeli")

    def test_ece_duyarlilik_dagilmis_veride_cokme_yok(self):
        ciftler = [(i / 100.0, 1 if i > 50 else 0) for i in range(1, 100)]
        rapor = m.ece_duyarlilik(ciftler)
        self.assertFalse(rapor["tek_bine_cokme"])

    def test_brier_bilinen_deger(self):
        # p=0.5 hepsi -> brier = 0.25
        ciftler = [(0.5, 1)] * 10 + [(0.5, 0)] * 10
        self.assertAlmostEqual(m.brier(ciftler), 0.25, places=9)

    def test_auroc_mukemmel_ayirici(self):
        ciftler = [(0.9, 1)] * 10 + [(0.1, 0)] * 10
        self.assertAlmostEqual(m.auroc(ciftler), 1.0, places=9)

    def test_auroc_ayirt_edemeyen(self):
        ciftler = [(0.5, 1)] * 10 + [(0.5, 0)] * 10
        self.assertAlmostEqual(m.auroc(ciftler), 0.5, places=9)

    def test_grup_ece_en_kotuyu_bulur(self):
        gruplu = {
            "buyuk": [(0.8, 1)] * 95 + [(0.8, 0)] * 5,
            "kucuk": [(0.9, 0)] * 5,
        }
        rapor = m.grup_ece(gruplu)
        self.assertEqual(rapor["en_kotu"][0], "kucuk")
        self.assertGreater(rapor["en_kotu"][1], rapor["gruplar"]["buyuk"])
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.KalibrasyonMetrikTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'wilson_araligi'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 3
# Kalibrasyon metrikleri. Dusuk ECE tek basina kanit DEGILDIR;
# ayirt edicilik (AUROC) ve en kotu grup ayrica olculur.


def wilson_araligi(basari, deneme, z=1.96):
    """Wilson skor araligi. Deneme yoksa (0,1) doner (bilgi yok)."""
    if deneme <= 0:
        return 0.0, 1.0
    p = basari / deneme
    payda = 1.0 + z * z / deneme
    merkez = p + z * z / (2.0 * deneme)
    yaricap = z * math.sqrt(p * (1.0 - p) / deneme + z * z / (4.0 * deneme * deneme))
    return (merkez - yaricap) / payda, (merkez + yaricap) / payda


def _kova(ciftler, bin_sayisi):
    """Guven degerine gore kovalara ayirir. Guven = max(p, 1-p)."""
    kovalar = [[] for _ in range(bin_sayisi)]
    for p, y in ciftler:
        guven = max(p, 1.0 - p)
        tahmin = 1 if p >= 0.5 else 0
        indeks = min(bin_sayisi - 1, int(guven * bin_sayisi))
        kovalar[indeks].append((guven, 1.0 if tahmin == y else 0.0))
    return kovalar


def ece(ciftler, bin_sayisi=10):
    """Beklenen kalibrasyon hatasi."""
    if not ciftler:
        return None
    toplam = len(ciftler)
    deger = 0.0
    for kova in _kova(ciftler, bin_sayisi):
        if not kova:
            continue
        ort_guven = sum(g for g, _ in kova) / len(kova)
        ort_dogruluk = sum(d for _, d in kova) / len(kova)
        deger += (len(kova) / toplam) * abs(ort_guven - ort_dogruluk)
    return deger


def mce(ciftler, bin_sayisi=10):
    """En kotu kovadaki kalibrasyon farki."""
    if not ciftler:
        return None
    en_kotu = 0.0
    for kova in _kova(ciftler, bin_sayisi):
        if not kova:
            continue
        ort_guven = sum(g for g, _ in kova) / len(kova)
        ort_dogruluk = sum(d for _, d in kova) / len(kova)
        en_kotu = max(en_kotu, abs(ort_guven - ort_dogruluk))
    return en_kotu


def ece_duyarlilik(ciftler, bin_listesi=(5, 10, 15, 20)):
    """ECE'nin bin sayisina duyarliligi + tek bine cokme tespiti."""
    if not ciftler:
        return {"degerler": {}, "tek_bine_cokme": True, "dolu_kova": 0}
    degerler = {n: ece(ciftler, n) for n in bin_listesi}
    dolu = sum(1 for kova in _kova(ciftler, 10) if kova)
    return {"degerler": degerler, "tek_bine_cokme": dolu <= 1, "dolu_kova": dolu}


def brier(ciftler):
    """Ikili Brier skoru."""
    if not ciftler:
        return None
    return sum((p - y) ** 2 for p, y in ciftler) / len(ciftler)


def auroc(ciftler):
    """ROC egrisi altindaki alan (Mann-Whitney U, baglar 0.5 sayilir)."""
    pozitif = [p for p, y in ciftler if y == 1]
    negatif = [p for p, y in ciftler if y == 0]
    if not pozitif or not negatif:
        return None
    toplam = 0.0
    for pp in pozitif:
        for pn in negatif:
            toplam += 1.0 if pp > pn else (0.5 if pp == pn else 0.0)
    return toplam / (len(pozitif) * len(negatif))


def grup_ece(ciftler_gruplu, bin_sayisi=10):
    """Grup basina ECE + en kotu grup. Grup: sembol/rejim/volatilite/kapsam."""
    gruplar = {}
    for ad, ciftler in ciftler_gruplu.items():
        deger = ece(ciftler, bin_sayisi)
        if deger is not None:
            gruplar[ad] = deger
    if not gruplar:
        return {"gruplar": {}, "en_kotu": (None, None)}
    en_kotu_ad = max(gruplar, key=lambda k: gruplar[k])
    return {"gruplar": gruplar, "en_kotu": (en_kotu_ad, gruplar[en_kotu_ad])}
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.KalibrasyonMetrikTesti -v`
Expected: PASS (10 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: kalibrasyon metrikleri (ECE duyarlilik, MCE, Brier, AUROC, grup)"
```

---

### Task 4: Shrinkage — kanıt yoksa stake yok

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 4)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `wilson_araligi`, `kirp` (Task 1, 3), `basabas_p`, `kelly_asimetrik` (Task 2)
- Produces:
  - `shrinkage_katsayisi(dogru: int, toplam: int, ece_enkotu: float | None, dolu_kanal: int, toplam_kanal: int) -> dict` → `{"s": float, "s_kanit": float, "s_kalibrasyon": float, "s_kapsam": float}`
  - `daralt(p: float, s: float, hedef: float = 0.5) -> float`
  - `stake_hesapla(p_ham: float, s: float, b: float, a: float, lam: float = 1.0) -> dict` → `{"f": float, "p_kullanilan": float | None, "p0": float | None, "not": str}`
  - `ESIK_KAYNAGI: dict`, `esik_raporu() -> str`

> **DÜZELTME (denetçi bulgusu PD-1, uygulama sırasında ölçülerek bulundu):**
> Daraltma hedefi **`0.5` DEĞİLDİR**. `p = 0.5`, bahsin beklenen değerinin sıfır olduğu
> anlamına gelmez: ödül asimetrikse (`b > a`) `p=0.5`'te bile `E[R] > 0` kalır ve Kelly
> pozitif stake verir. Ölçüldü: `R=2.0, cost_r=0.3` ⇒ `b=1.7, a=1.3` ⇒ `f* = 0.0905`,
> yani "kanıt yoksa stake yok" sözleşmesi **sağlanmıyordu**.
> Tarafsız hedef bahsin **başabaş olasılığıdır**: `p0 = a/(a+b)`. Bu hedefle `f*` tam sıfır
> olur (`R ∈ {1.33, 2.0, 3.0, 5.0, 1.5}` için `|f*| < 1e-16` ölçüldü).
> **Sonraki görevler (özellikle Task 12 kalibrasyon ve Task 13 decoding) `0.5` hedefini
> MİRAS ALMAMALIDIR** — stake sözleşmesi yalnız `stake_hesapla()` üzerinden geçer.

- [x] **Step 1: Write the failing test**

```python
class ShrinkageTesti(unittest.TestCase):
    def test_kanit_yoksa_s_sifir(self):
        # 48 denemede 17 dogru -> wilson alt 0.2343 < 0.5 -> s_kanit = 0
        r = m.shrinkage_katsayisi(dogru=17, toplam=48, ece_enkotu=0.02,
                                  dolu_kanal=5, toplam_kanal=5)
        self.assertEqual(r["s_kanit"], 0.0)
        self.assertEqual(r["s"], 0.0)

    def test_guclu_kanit_s_pozitif(self):
        r = m.shrinkage_katsayisi(dogru=900, toplam=1000, ece_enkotu=0.01,
                                  dolu_kanal=5, toplam_kanal=5)
        self.assertGreater(r["s_kanit"], 0.5)
        self.assertGreater(r["s"], 0.5)

    def test_kapsam_dususu_s_dusurur(self):
        tam = m.shrinkage_katsayisi(900, 1000, 0.01, 5, 5)["s"]
        yarim = m.shrinkage_katsayisi(900, 1000, 0.01, 2, 5)["s"]
        self.assertLess(yarim, tam)
        self.assertAlmostEqual(yarim / tam, 2 / 5, places=6)

    def test_kotu_kalibrasyon_s_dusurur(self):
        iyi = m.shrinkage_katsayisi(900, 1000, 0.00, 5, 5)["s"]
        kotu = m.shrinkage_katsayisi(900, 1000, 0.10, 5, 5)["s"]
        self.assertEqual(kotu, 0.0)
        self.assertGreater(iyi, 0.0)

    def test_ece_olculemedi_ise_s_sifir(self):
        r = m.shrinkage_katsayisi(900, 1000, None, 5, 5)
        self.assertEqual(r["s_kalibrasyon"], 0.0)
        self.assertEqual(r["s"], 0.0)

    def test_daralt_sifir_s_sansa_ceker(self):
        self.assertAlmostEqual(m.daralt(0.95, 0.0), 0.5, places=9)

    def test_daralt_bir_s_degistirmez(self):
        self.assertAlmostEqual(m.daralt(0.95, 1.0), 0.95, places=9)

    def test_daralt_ara_deger(self):
        self.assertAlmostEqual(m.daralt(0.90, 0.5), 0.70, places=9)


class ShrinkageKellyEntegrasyonTesti(unittest.TestCase):
    """Sozlesmenin cekirdegi: kanit yoksa f* matematigin kendisiyle 0 olur."""

    def test_kanit_yokken_stake_sifir(self):
        r = m.shrinkage_katsayisi(17, 48, 0.02, 5, 5)
        b, a = m.net_kanatlar(R=2.0, cost_r=0.3)
        self.assertEqual(m.stake_hesapla(0.95, r["s"], b, a)["f"], 0.0)

    def test_kanit_yokken_stake_sifir_her_geometride(self):
        r = m.shrinkage_katsayisi(17, 48, 0.02, 5, 5)
        for R, cost_r in ((1.3333, 0.6), (2.0, 0.3), (3.0, 0.1),
                          (5.0, 0.05), (1.5, 0.0)):
            b, a = m.net_kanatlar(R, cost_r)
            self.assertAlmostEqual(m.stake_hesapla(0.95, r["s"], b, a)["f"],
                                   0.0, places=12)

    def test_eski_zincir_neden_yetmiyordu(self):
        """Regresyon korumasi: 0.5 hedefli daraltma sozlesmeyi SAGLAMAZ."""
        b, a = m.net_kanatlar(R=2.0, cost_r=0.3)
        p_yanlis = m.daralt(0.95, 0.0, hedef=0.5)
        self.assertGreater(m.kelly_asimetrik(p_yanlis, b, a), 0.0)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.ShrinkageTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'shrinkage_katsayisi'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 4
# Shrinkage: kanit yoksa olasilik sansa cekilir, boylece stake kendiliginden
# sifira iner. Sabit esik YOKTUR; uc carpan da veriden gelir.

ECE_TAVANI = 0.10  # bu degerin ustunde kalibrasyon guvenilmez sayilir


def shrinkage_katsayisi(dogru, toplam, ece_enkotu, dolu_kanal, toplam_kanal):
    """s = s_kanit * s_kalibrasyon * s_kapsam, hepsi [0,1]."""
    alt, _ = wilson_araligi(dogru, toplam)
    s_kanit = kirp(2.0 * (alt - 0.5), 0.0, 1.0)

    if ece_enkotu is None:
        s_kalibrasyon = 0.0
    else:
        s_kalibrasyon = kirp(1.0 - float(ece_enkotu) / ECE_TAVANI, 0.0, 1.0)

    if toplam_kanal <= 0:
        s_kapsam = 0.0
    else:
        s_kapsam = kirp(dolu_kanal / toplam_kanal, 0.0, 1.0)

    return {
        "s": s_kanit * s_kalibrasyon * s_kapsam,
        "s_kanit": s_kanit,
        "s_kalibrasyon": s_kalibrasyon,
        "s_kapsam": s_kapsam,
    }


def daralt(p, s, hedef=0.5):
    """p'yi kanit gucune gore HEDEF'e dogru daraltir.

    Tarafsiz hedef 0.5 DEGILDIR: p=0.5, bahsin EV'sinin sifir oldugu anlamina
    gelmez (odul asimetrikse E[R] pozitif kalir). Stake sozlesmesi icin dogru
    hedef bahsin BASABAS olasiligidir; bkz. stake_hesapla.
    """
    hedef = kirp(hedef, 0.0, 1.0)
    return hedef + kirp(s, 0.0, 1.0) * (kirp(p, 0.0, 1.0) - hedef)


def stake_hesapla(p_ham, s, b, a, lam=1.0):
    """Stake sozlesmesinin TEK garanti noktasi: kanit yoksa f* tam olarak 0."""
    p0 = basabas_p(b, a)
    if p0 is None:                      # kazanc kanadi yok: bahis imkansiz
        return {"f": 0.0, "p_kullanilan": None, "p0": None,
                "not": "kazanc kanadi <= 0 - bahis matematiksel olarak imkansiz"}
    p_kullanilan = daralt(p_ham, s, hedef=p0)
    f = kelly_asimetrik(p_kullanilan, b, a) * max(0.0, float(lam))
    return {"f": f, "p_kullanilan": p_kullanilan, "p0": p0, "not": ""}
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.ShrinkageTesti test_llm_trading_v3.ShrinkageKellyEntegrasyonTesti -v`
Expected: PASS (9 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: shrinkage - kanit yoksa stake matematiksel olarak sifir"
```

---

### Task 5: Geometri araması — R karar değişkeni

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 5)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `kelly_asimetrik`, `net_kanatlar`, `maliyet_r` (Task 2)
- Produces:
  - `ilk_gecis_olcum(barlar: list[dict], indeksler: list[int], yon: str, stop_k: float, hedef_k: float, atr_serisi: list[float], azami_bar: int) -> dict` → `{"hedef": int, "stop": int, "zaman_asimi": int, "n": int, "p_hedef": float | None}`
  - `beklenen_log(p_hedef: float, f: float, b: float, a: float) -> float`
  - `geometri_sec(barlar, indeksler, yon, atr_serisi, izgara, cost_fn, lam) -> dict`

`barlar` biçimi: `[{"o":float,"h":float,"l":float,"c":float}, ...]`

- [x] **Step 1: Write the failing test**

```python
class GeometriTesti(unittest.TestCase):
    def _barlar(self, yollar):
        """yollar: her giris icin sonraki barlarin (high, low) listesi."""
        return yollar

    def test_ilk_gecis_ayni_barda_iki_bariyer_stop_sayilir(self):
        # giris 100, atr 1, stop_k=1 -> stop 99, hedef_k=2 -> hedef 102
        # sonraki bar hem 102'ye hem 99'a degiyor -> muhafazakar: STOP
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 103, "l": 98, "c": 100},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["stop"], 1)
        self.assertEqual(r["hedef"], 0)

    def test_ilk_gecis_hedef_once(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 103, "l": 99.5, "c": 102},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["hedef"], 1)
        self.assertAlmostEqual(r["p_hedef"], 1.0, places=9)

    def test_ilk_gecis_zaman_asimi_paydaya_girmez(self):
        barlar = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 4
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0] * 4, azami_bar=2)
        self.assertEqual(r["zaman_asimi"], 1)
        self.assertIsNone(r["p_hedef"])

    def test_ilk_gecis_short_simetrik(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 100.5, "l": 97, "c": 98},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "SHORT", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["hedef"], 1)

    def test_beklenen_log_sifir_stake_sifir(self):
        self.assertAlmostEqual(m.beklenen_log(0.7, 0.0, 1.0, 1.0), 0.0, places=9)

    def test_beklenen_log_bilinen_deger(self):
        # p=0.5, f=0.1, b=1, a=1 -> 0.5*ln(1.1) + 0.5*ln(0.9)
        beklenen = 0.5 * math.log(1.1) + 0.5 * math.log(0.9)
        self.assertAlmostEqual(m.beklenen_log(0.5, 0.1, 1.0, 1.0), beklenen, places=9)

    def test_beklenen_log_iflas_riskinde_sonsuz_negatif(self):
        # f*a >= 1 -> tam kayip -> -inf
        self.assertEqual(m.beklenen_log(0.5, 1.0, 1.0, 1.0), float("-inf"))
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.GeometriTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'ilk_gecis_olcum'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 5
# Geometri (R) sabit degil, karar degiskenidir. Ilk-gecis olasiligi GERCEK
# barlarla olculur; ayni barda iki bariyer = muhafazakar STOP.


def ilk_gecis_olcum(barlar, indeksler, yon, stop_k, hedef_k, atr_serisi, azami_bar):
    """Her giris indeksi icin hangi bariyerin ONCE vuruldugunu sayar."""
    sayim = {"hedef": 0, "stop": 0, "zaman_asimi": 0}
    for i in indeksler:
        if i >= len(barlar) - 1 or i >= len(atr_serisi):
            continue
        giris = barlar[i]["c"]
        atr = max(atr_serisi[i], EPSILON)
        if yon == "LONG":
            stop_seviye = giris - stop_k * atr
            hedef_seviye = giris + hedef_k * atr
        else:
            stop_seviye = giris + stop_k * atr
            hedef_seviye = giris - hedef_k * atr

        sonuc = "zaman_asimi"
        son = min(len(barlar), i + 1 + azami_bar)
        for j in range(i + 1, son):
            yuksek, dusuk = barlar[j]["h"], barlar[j]["l"]
            if yon == "LONG":
                stop_vurdu = dusuk <= stop_seviye
                hedef_vurdu = yuksek >= hedef_seviye
            else:
                stop_vurdu = yuksek >= stop_seviye
                hedef_vurdu = dusuk <= hedef_seviye
            if stop_vurdu:          # ayni barda ikisi de olsa STOP once sayilir
                sonuc = "stop"
                break
            if hedef_vurdu:
                sonuc = "hedef"
                break
        sayim[sonuc] += 1

    karar_veren = sayim["hedef"] + sayim["stop"]
    p_hedef = (sayim["hedef"] / karar_veren) if karar_veren > 0 else None
    sayim["n"] = karar_veren
    sayim["p_hedef"] = p_hedef
    return sayim


def beklenen_log(p_hedef, f, b, a):
    """E[log servet] tek bahis icin. Iflas riskinde -inf."""
    kazanc = 1.0 + f * b
    kayip = 1.0 - f * a
    if kazanc <= 0.0 or kayip <= 0.0:
        return float("-inf")
    return p_hedef * math.log(kazanc) + (1.0 - p_hedef) * math.log(kayip)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.GeometriTesti -v`
Expected: PASS (7 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: ilk-gecis olcumu ve E[log] - geometri karar degiskeni"
```

---

### Task 6: Geometri seçimi ve stake kırpma

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 5 devamı)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `ilk_gecis_olcum`, `beklenen_log`, `net_kanatlar`, `kelly_asimetrik`, `basabas_p` (Task 2, 5)
- Produces:
  - `IZGARA: tuple` — aday `(stop_k, hedef_k)` çiftleri
  - `geometri_sec(barlar, indeksler, yon, atr_serisi, p_yon, cost_r_fn, lam, azami_bar) -> dict`
  - `stake_kirp(f_ham: float, f_max: float) -> dict`
  - `likidasyon_tavani(giris: float, likidasyon: float | None, kaldirac_azami: float, guvenlik: float) -> float`

- [x] **Step 1: Write the failing test**

```python
class GeometriSecimTesti(unittest.TestCase):
    def _yukselen_barlar(self, n=200):
        """Hedefin stoptan once vurulma egiliminde oldugu sentetik seri."""
        barlar = []
        fiyat = 100.0
        for i in range(n):
            fiyat *= 1.002
            barlar.append({"o": fiyat, "h": fiyat * 1.004, "l": fiyat * 0.999, "c": fiyat})
        return barlar

    def test_geometri_sec_bir_aday_dondurur(self):
        barlar = self._yukselen_barlar()
        atr = [b["c"] * 0.003 for b in barlar]
        indeksler = list(range(0, 150, 5))
        r = m.geometri_sec(barlar, indeksler, "LONG", atr, p_yon=0.6,
                           cost_r_fn=lambda sk: 0.05, lam=1.0, azami_bar=20)
        self.assertIn("stop_k", r)
        self.assertIn("hedef_k", r)
        self.assertIn("R", r)
        self.assertIn("p_hedef", r)
        self.assertIn("elog", r)
        self.assertIn(( r["stop_k"], r["hedef_k"] ), m.IZGARA)

    def test_geometri_sec_olcum_yoksa_fail_closed(self):
        barlar = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 5
        atr = [1.0] * 5
        r = m.geometri_sec(barlar, [0], "LONG", atr, 0.9,
                           lambda sk: 0.05, 1.0, azami_bar=2)
        self.assertEqual(r["f"], 0.0)
        self.assertIsNone(r["p_hedef"])
        self.assertIn("OLCUM YOK", r["not"])

    def test_geometri_sec_yuksek_maliyette_stake_sifir(self):
        barlar = self._yukselen_barlar()
        atr = [b["c"] * 0.003 for b in barlar]
        r = m.geometri_sec(barlar, list(range(0, 150, 5)), "LONG", atr, 0.6,
                           cost_r_fn=lambda sk: 5.0, lam=1.0, azami_bar=20)
        self.assertEqual(r["f"], 0.0)

    def test_likidasyon_tavani_okunamazsa_sifir(self):
        self.assertEqual(m.likidasyon_tavani(100.0, None, 100.0, 0.5), 0.0)

    def test_likidasyon_tavani_mesafeden_gelir(self):
        # likidasyon %20 uzakta, guvenlik 0.5 -> tavan 0.10; kaldirac tavani 1/10=0.1
        tavan = m.likidasyon_tavani(100.0, 80.0, 10.0, 0.5)
        self.assertAlmostEqual(tavan, 0.10, places=9)

    def test_stake_kirp_kirpma_bildirilir(self):
        r = m.stake_kirp(0.5, 0.1)
        self.assertAlmostEqual(r["f"], 0.1, places=9)
        self.assertTrue(r["kirpildi"])

    def test_stake_kirp_kirpma_yoksa_bayrak_kapali(self):
        r = m.stake_kirp(0.05, 0.1)
        self.assertAlmostEqual(r["f"], 0.05, places=9)
        self.assertFalse(r["kirpildi"])
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.GeometriSecimTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'geometri_sec'`

- [x] **Step 3: Write minimal implementation**

```python
# Aday geometri izgarasi: (stop_k, hedef_k) ATR carpanlari.
IZGARA = (
    (1.0, 1.5), (1.0, 2.0), (1.0, 3.0), (1.0, 4.0),
    (1.5, 2.0), (1.5, 3.0), (1.5, 4.0), (1.5, 5.0),
    (2.0, 3.0), (2.0, 4.0), (2.0, 6.0),
)
ASGARI_OLCUM = 20  # bu sayidan az karar veren ornek varsa olcum guvenilmez


def likidasyon_tavani(giris, likidasyon, kaldirac_azami, guvenlik=0.5):
    """Stake'in mutlak ust siniri. Likidasyon okunamazsa fail-closed 0."""
    if likidasyon is None or kaldirac_azami is None or kaldirac_azami <= 0:
        return 0.0
    giris = abs(float(giris))
    if giris <= 0:
        return 0.0
    mesafe_orani = abs(giris - float(likidasyon)) / giris
    return max(0.0, min(1.0 / float(kaldirac_azami), mesafe_orani * float(guvenlik)))


def stake_kirp(f_ham, f_max):
    """f*'i mutlak tavana kirpar ve kirpmayi bildirir."""
    f_ham = max(0.0, float(f_ham))
    f_max = max(0.0, float(f_max))
    if f_ham > f_max:
        return {"f": f_max, "kirpildi": True, "f_ham": f_ham, "f_max": f_max}
    return {"f": f_ham, "kirpildi": False, "f_ham": f_ham, "f_max": f_max}


def geometri_sec(barlar, indeksler, yon, atr_serisi, p_yon,
                 cost_r_fn, lam=1.0, azami_bar=32):
    """E[log] maksimize eden (stop_k, hedef_k) adayini secer.

    p_yon: modelin kalibre + daraltilmis yon olasiligi.
    cost_r_fn(stop_k) -> cost_r: maliyet stop mesafesine bagli oldugu icin
    her aday kendi maliyetiyle degerlendirilir.
    Olcum yetersizse fail-closed: f=0 ve gerekce yazilir.
    """
    en_iyi = None
    denenen = []
    for stop_k, hedef_k in IZGARA:
        olcum = ilk_gecis_olcum(barlar, indeksler, yon, stop_k, hedef_k,
                                atr_serisi, azami_bar)
        R = hedef_k / stop_k
        cost_r = float(cost_r_fn(stop_k))
        b, a = net_kanatlar(R, cost_r)
        if olcum["n"] < ASGARI_OLCUM or olcum["p_hedef"] is None:
            denenen.append({"stop_k": stop_k, "hedef_k": hedef_k, "elog": None,
                            "n": olcum["n"], "not": "OLCUM YOK"})
            continue
        # Karar olasiligi: modelin yon olasiligi ile olculen ilk-gecis birlestirilir
        # (ikisi de ayni olayi tahmin eder; geometrik ortalama muhafazakardir)
        p_bilesik = math.sqrt(max(0.0, p_yon) * max(0.0, olcum["p_hedef"]))
        f = kelly_asimetrik(p_bilesik, b, a) * lam
        elog = beklenen_log(p_bilesik, f, b, a)
        aday = {"stop_k": stop_k, "hedef_k": hedef_k, "R": R, "cost_r": cost_r,
                "b": b, "a": a, "p_hedef": olcum["p_hedef"], "p_bilesik": p_bilesik,
                "n": olcum["n"], "f": f, "elog": elog,
                "basabas_p": basabas_p(b, a), "not": ""}
        denenen.append(aday)
        if en_iyi is None or elog > en_iyi["elog"]:
            en_iyi = aday

    if en_iyi is None:
        varsayilan = IZGARA[5]  # (1.5, 3.0) — rapor icin notr referans
        return {"stop_k": varsayilan[0], "hedef_k": varsayilan[1],
                "R": varsayilan[1] / varsayilan[0], "p_hedef": None,
                "p_bilesik": None, "n": 0, "f": 0.0, "elog": None,
                "cost_r": None, "b": None, "a": None, "basabas_p": None,
                "not": "OLCUM YOK - yeterli ilk-gecis ornegi yok (fail-closed)",
                "denenen": denenen}
    en_iyi["denenen"] = denenen
    if en_iyi["elog"] <= 0.0:
        en_iyi["f"] = 0.0
        en_iyi["not"] = "E[log] <= 0 - hicbir geometri pozitif buyume vermiyor"
    return en_iyi
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.GeometriSecimTesti -v`
Expected: PASS (7 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: E[log] ile geometri secimi, likidasyon tavani ve stake kirpma"
```

---

### Task 7: Veri adaptörü — Binance ana, OKX yedek

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 6)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: yok (bağımsız)
- Produces:
  - `KANALLAR: tuple` — `("kline_15m", "kline_4h", "oi", "funding", "taker", "derinlik")`
  - `Adaptor` sınıfı: `.ad`, `.kline(sembol, aralik, limit)`, `.turev(sembol)`
  - `BinanceAdaptor`, `OkxAdaptor`
  - `veri_topla(sembol, adaptorler, getir_fn) -> dict` → `{"adaptor": str, "kanallar": {ad: veri|None}, "kapsam": float, "dusen": list}`

**Not:** ağ çağrısı `getir_fn` parametresiyle enjekte edilir; testler sahte `getir_fn` verir. Bu, ağsız test edilebilirliğin tek koşuludur.

- [x] **Step 1: Write the failing test**

```python
class AdaptorTesti(unittest.TestCase):
    def test_kapsam_tam_veride_bir(self):
        def sahte_getir(url, params):
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertEqual(r["kapsam"], 1.0)
        self.assertEqual(r["adaptor"], "binance")
        self.assertEqual(r["dusen"], [])

    def test_kanal_dusunce_kapsam_duser_ve_uydurulmaz(self):
        def sahte_getir(url, params):
            if "openInterest" in url or "openInterestHist" in url:
                raise OSError("erisilemedi")
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertLess(r["kapsam"], 1.0)
        self.assertIsNone(r["kanallar"]["oi"])
        self.assertIn("oi", r["dusen"])

    def test_ana_adaptor_tamamen_duserse_yedege_gecer_ve_bildirir(self):
        def sahte_getir(url, params):
            if "binance" in url:
                raise OSError("403")
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor(), m.OkxAdaptor()], sahte_getir)
        self.assertEqual(r["adaptor"], "okx")
        self.assertTrue(r["yedege_dusuldu"])

    def test_hicbir_adaptor_calismazsa_kapsam_sifir(self):
        def sahte_getir(url, params):
            raise OSError("hepsi kapali")
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor(), m.OkxAdaptor()], sahte_getir)
        self.assertEqual(r["kapsam"], 0.0)
        self.assertTrue(all(v is None for v in r["kanallar"].values()))

    def test_notr_sifir_enjekte_edilmez(self):
        """Uydurma yasagi: dusen kanal None olmali, 0.0 OLMAMALI."""
        def sahte_getir(url, params):
            if "premiumIndex" in url or "funding-rate" in url:
                raise OSError("yok")
            return {"ok": True, "veri": [1]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertIsNone(r["kanallar"]["funding"])
        self.assertNotEqual(r["kanallar"]["funding"], 0.0)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.AdaptorTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'BinanceAdaptor'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 6
# Veri adaptorleri. Yalniz public GET. Erisilemeyen kanal None kalir;
# notr 0.0 enjeksiyonu YASAK (uydurma yasagi).

KANALLAR = ("kline_15m", "kline_4h", "oi", "funding", "taker", "derinlik")


class Adaptor:
    """Ortak arayuz. Alt siniflar url uretir; ag cagrisi disaridan enjekte edilir."""

    ad = "soyut"
    taban = ""

    def uc(self, kanal, sembol):
        raise NotImplementedError


class BinanceAdaptor(Adaptor):
    ad = "binance"
    taban = "https://fapi.binance.com"

    def uc(self, kanal, sembol):
        t = self.taban
        return {
            "kline_15m": (t + "/fapi/v1/klines", {"symbol": sembol, "interval": "15m", "limit": "500"}),
            "kline_4h": (t + "/fapi/v1/klines", {"symbol": sembol, "interval": "4h", "limit": "500"}),
            "oi": (t + "/futures/data/openInterestHist", {"symbol": sembol, "period": "15m", "limit": "500"}),
            "funding": (t + "/fapi/v1/premiumIndex", {"symbol": sembol}),
            "taker": (t + "/futures/data/takerlongshortRatio", {"symbol": sembol, "period": "15m", "limit": "500"}),
            "derinlik": (t + "/fapi/v1/depth", {"symbol": sembol, "limit": "20"}),
        }[kanal]


class OkxAdaptor(Adaptor):
    ad = "okx"
    taban = "https://www.okx.com"

    def _inst(self, sembol):
        return sembol.replace("USDT", "-USDT-SWAP")

    def uc(self, kanal, sembol):
        t, inst = self.taban, self._inst(sembol)
        para = inst.split("-")[0]
        return {
            "kline_15m": (t + "/api/v5/market/candles", {"instId": inst, "bar": "15m", "limit": "300"}),
            "kline_4h": (t + "/api/v5/market/candles", {"instId": inst, "bar": "4H", "limit": "300"}),
            "oi": (t + "/api/v5/rubik/stat/contracts/open-interest-history", {"instId": inst, "period": "15m"}),
            "funding": (t + "/api/v5/public/funding-rate", {"instId": inst}),
            "taker": (t + "/api/v5/rubik/stat/taker-volume", {"instType": "CONTRACTS", "ccy": para, "period": "15m"}),
            "derinlik": (t + "/api/v5/market/books", {"instId": inst, "sz": "20"}),
        }[kanal]


def veri_topla(sembol, adaptorler, getir_fn):
    """Adaptorleri sirayla dener. Kanal basina basari/dusus kaydedilir."""
    yedege_dusuldu = False
    for sira, adaptor in enumerate(adaptorler):
        kanallar = {}
        dusen = []
        for kanal in KANALLAR:
            url, params = adaptor.uc(kanal, sembol)
            try:
                kanallar[kanal] = getir_fn(url, params)
            except Exception:
                kanallar[kanal] = None      # UYDURMA YOK: None kalir
                dusen.append(kanal)
        kapsam = sum(1 for v in kanallar.values() if v is not None) / len(KANALLAR)
        if kapsam > 0.0:
            return {"adaptor": adaptor.ad, "kanallar": kanallar, "kapsam": kapsam,
                    "dusen": dusen, "yedege_dusuldu": yedege_dusuldu or sira > 0}
        yedege_dusuldu = True

    bos = {k: None for k in KANALLAR}
    return {"adaptor": None, "kanallar": bos, "kapsam": 0.0,
            "dusen": list(KANALLAR), "yedege_dusuldu": True}
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.AdaptorTesti -v`
Expected: PASS (5 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: cift adaptor (Binance ana / OKX yedek), kapsam skoru, uydurma yasagi"
```

---

### Task 8: Özellik-token sözlüğü — halka 1

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 7a)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `sabit_kimlik` (Task 1)
- Produces:
  - `AILELER: dict[str, int]` — aile adı → boyut
  - `ZAMAN_DILIMLERI: tuple` — `("15m", "4h")`
  - `TokenSozlugu` sınıfı: `.kimlik(sembol, zaman_dilimi, aile, gecikme) -> int`, `.boyut -> int`
  - `token_listesi(semboller, gecikme_sayisi) -> list[dict]`

- [x] **Step 1: Write the failing test**

```python
class TokenSozluguTesti(unittest.TestCase):
    def test_ayni_anahtar_ayni_kimlik(self):
        s = m.TokenSozlugu()
        self.assertEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                         s.kimlik("BTCUSDT", "15m", "fiyat", 0))

    def test_farkli_zaman_dilimi_farkli_kimlik(self):
        s = m.TokenSozlugu()
        self.assertNotEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                            s.kimlik("BTCUSDT", "4h", "fiyat", 0))

    def test_farkli_gecikme_farkli_kimlik(self):
        s = m.TokenSozlugu()
        self.assertNotEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                            s.kimlik("BTCUSDT", "15m", "fiyat", 1))

    def test_sozluk_buyur(self):
        s = m.TokenSozlugu()
        self.assertEqual(s.boyut, 0)
        s.kimlik("BTCUSDT", "15m", "fiyat", 0)
        s.kimlik("BTCUSDT", "15m", "fiyat", 1)
        self.assertEqual(s.boyut, 2)

    def test_token_listesi_iki_zaman_dilimi_icerir(self):
        tokenlar = m.token_listesi(["BTCUSDT"], gecikme_sayisi=2)
        zamanlar = {t["zaman_dilimi"] for t in tokenlar}
        self.assertEqual(zamanlar, set(m.ZAMAN_DILIMLERI))

    def test_token_listesi_beklenen_sayida(self):
        # sembol x zaman_dilimi x aile x gecikme
        tokenlar = m.token_listesi(["BTCUSDT", "ETHUSDT"], gecikme_sayisi=3)
        beklenen = 2 * len(m.ZAMAN_DILIMLERI) * len(m.AILELER) * 3
        self.assertEqual(len(tokenlar), beklenen)

    def test_turev_ailesi_sozlukte_var(self):
        self.assertIn("turev", m.AILELER)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.TokenSozluguTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'TokenSozlugu'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 7a
# Ozellik-token sozlugu. Token kimligi (sembol, zaman_dilimi, aile, gecikme)
# dortlusudur; 4H ve 15M AYRI zaman dilimi tokenlaridir.

ZAMAN_DILIMLERI = ("15m", "4h")
AILELER = {
    "fiyat": 6,     # getiri1, getiri4, getiri16, ema_farki, rsi, kanal_konumu
    "hacim": 2,     # hacim_z, nominal_hacim_z
    "turev": 5,     # oi_degisim, funding_z, taker_dengesi, derinlik_dengesi, kapsam
    "oynaklik": 3,  # atr_orani, oynaklik_orani, rejim
}


class TokenSozlugu:
    """Token kimliklerini tutan sozluk. Ayni dortlu daima ayni kimlik."""

    def __init__(self):
        self._kimlikler = {}

    def kimlik(self, sembol, zaman_dilimi, aile, gecikme):
        anahtar = (sembol, zaman_dilimi, aile, int(gecikme))
        if anahtar not in self._kimlikler:
            self._kimlikler[anahtar] = len(self._kimlikler) + 1
        return self._kimlikler[anahtar]

    @property
    def boyut(self):
        return len(self._kimlikler)


def token_listesi(semboller, gecikme_sayisi):
    """Bir ileri gecis icin uretilecek tokenlarin tam listesi (eskiden yeniye)."""
    tokenlar = []
    for gecikme in range(gecikme_sayisi - 1, -1, -1):
        for sembol in semboller:
            for zaman_dilimi in ZAMAN_DILIMLERI:
                for aile in AILELER:
                    tokenlar.append({
                        "sembol": sembol,
                        "zaman_dilimi": zaman_dilimi,
                        "aile": aile,
                        "gecikme": gecikme,
                        "boyut": AILELER[aile],
                    })
    return tokenlar
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.TokenSozluguTesti -v`
Expected: PASS (7 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: ozellik-token sozlugu, 15m ve 4h ayri zaman dilimi tokenlari"
```

---

### Task 9: Train-only ölçekleyici ve konum kodu — halka 2 ve 3

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 7b)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `kirp` (Task 1), `AILELER` (Task 8)
- Produces:
  - `Olcekleyici` sınıfı: `.fit(satirlar, kesim)`, `.donustur(aile, degerler) -> list[float]`, `.sabit_kolonlar -> list`
  - `zaman_konumu(gecikme: int, boyut: int) -> list[float]`
  - `sembol_konumu(sembol_indeksi: int, boyut: int) -> list[float]`

- [x] **Step 1: Write the failing test**

```python
class OlcekleyiciTesti(unittest.TestCase):
    def _satirlar(self, n=100):
        return [{"fiyat": [i * 0.01] * m.AILELER["fiyat"],
                 "hacim": [0.0] * m.AILELER["hacim"],
                 "turev": [i * 0.02] * m.AILELER["turev"],
                 "oynaklik": [1.0] * m.AILELER["oynaklik"]} for i in range(n)]

    def test_yalniz_train_diliminden_fit(self):
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        # 50 sonrasi veri istatistigi etkilememeli
        o2 = m.Olcekleyici()
        o2.fit(satirlar[:50], kesim=50)
        self.assertEqual(o.donustur("fiyat", [0.25] * m.AILELER["fiyat"]),
                         o2.donustur("fiyat", [0.25] * m.AILELER["fiyat"]))

    def test_sabit_kolon_isaretlenir(self):
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        self.assertIn(("hacim", 0), o.sabit_kolonlar)

    def test_sabit_kolonda_donusum_sifir_verir(self):
        """Sabit kolon bilgi tasimaz: ham deger gecirilmez, 0.0 verilir."""
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        sonuc = o.donustur("hacim", [999.0, 999.0])
        self.assertEqual(sonuc, [0.0, 0.0])

    def test_fit_edilmeden_donusum_hata_verir(self):
        o = m.Olcekleyici()
        with self.assertRaises(RuntimeError):
            o.donustur("fiyat", [0.0] * m.AILELER["fiyat"])


class KonumKoduTesti(unittest.TestCase):
    def test_zaman_konumu_gecikmeye_gore_degisir(self):
        self.assertNotEqual(m.zaman_konumu(0, 16), m.zaman_konumu(1, 16))

    def test_zaman_konumu_deterministik(self):
        self.assertEqual(m.zaman_konumu(3, 16), m.zaman_konumu(3, 16))

    def test_sembol_konumu_ayri_eksen(self):
        """Sembol ekseni zaman ekseninden BAGIMSIZ olmali."""
        z0 = m.zaman_konumu(0, 16)
        s0 = m.sembol_konumu(0, 16)
        s1 = m.sembol_konumu(1, 16)
        self.assertNotEqual(s0, s1)
        self.assertNotEqual(s0, z0)

    def test_konum_boyutu_dogru(self):
        self.assertEqual(len(m.zaman_konumu(2, 16)), 16)
        self.assertEqual(len(m.sembol_konumu(2, 16)), 16)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.OlcekleyiciTesti test_llm_trading_v3.KonumKoduTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'Olcekleyici'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 7b
# Gecmise dayali normalizasyon: olcekleyici YALNIZ train diliminden fit edilir.
# Sabit kolon (std=0) bilgi tasimaz -> ham deger gecirilmez, 0.0 verilir.

SABIT_ESIK = 1e-9


class Olcekleyici:
    def __init__(self):
        self._parametre = {}
        self.sabit_kolonlar = []
        self._fit_edildi = False

    def fit(self, satirlar, kesim):
        egitim = satirlar[:max(1, int(kesim))]
        self._parametre = {}
        self.sabit_kolonlar = []
        for aile, boyut in AILELER.items():
            kolonlar = []
            for j in range(boyut):
                degerler = [float(s[aile][j]) for s in egitim if aile in s]
                if not degerler:
                    kolonlar.append((0.0, 1.0, True))
                    self.sabit_kolonlar.append((aile, j))
                    continue
                ortalama = sum(degerler) / len(degerler)
                if len(degerler) < 2:
                    varyans = 0.0
                else:
                    varyans = sum((d - ortalama) ** 2 for d in degerler) / (len(degerler) - 1)
                std = math.sqrt(varyans)
                sabit = std < SABIT_ESIK
                if sabit:
                    self.sabit_kolonlar.append((aile, j))
                kolonlar.append((ortalama, std if not sabit else 1.0, sabit))
            self._parametre[aile] = kolonlar
        self._fit_edildi = True

    def donustur(self, aile, degerler):
        if not self._fit_edildi:
            raise RuntimeError("Olcekleyici fit edilmeden kullanilamaz")
        sonuc = []
        for deger, (ortalama, std, sabit) in zip(degerler, self._parametre[aile]):
            if sabit:
                sonuc.append(0.0)       # sabit kolon: ham deger SIZDIRILMAZ
            else:
                sonuc.append(kirp((float(deger) - ortalama) / std, -5.0, 5.0))
        return sonuc


def _sinuzoidal(konum, boyut, taban):
    cikti = []
    for k in range(boyut):
        payda = taban ** (2.0 * (k // 2) / max(1, boyut))
        aci = konum / payda
        cikti.append(math.sin(aci) if k % 2 == 0 else math.cos(aci))
    return cikti


def zaman_konumu(gecikme, boyut):
    """Zaman ekseni konum kodu (gecikme = kac bar geride)."""
    return [x * 0.10 for x in _sinuzoidal(gecikme, boyut, 10000.0)]


def sembol_konumu(sembol_indeksi, boyut):
    """Sembol ekseni konum kodu — zaman ekseninden BAGIMSIZ taban."""
    return [x * 0.10 for x in _sinuzoidal(sembol_indeksi, boyut, 97.0)]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.OlcekleyiciTesti test_llm_trading_v3.KonumKoduTesti -v`
Expected: PASS (8 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: train-only olcekleyici (sabit kolon korumasi) ve ayri zaman/sembol konum kodu"
```

---

### Task 10: Causal attention ve FFN — halka 4 ve 5, ölü-halka testleriyle

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 7c)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `tohumlu_rng`, `kirp` (Task 1)
- Produces:
  - `matris(satir, sutun, tohum_parcalari, olcek) -> list[list[float]]`
  - `matvec(M, v) -> list[float]`, `nokta(a, b) -> float`, `topla_vek(*v) -> list[float]`
  - `kararli_softmax(logitler, sicaklik=1.0) -> list[float]`
  - `katman_norm(v) -> list[float]`
  - `Kodlayici` sınıfı: `.ileri(durumlar, qk_acik=True, maske_acik=True, ffn_acik=True) -> list[float]`

**Kritik:** `Kodlayici.ileri` üç anahtar alır (`qk_acik`, `maske_acik`, `ffn_acik`). Bunlar üretimde daima `True`'dur; **yalnız ölü-halka testleri için** vardır. Test, her anahtarı kapatınca çıktının DEĞİŞTİĞİNİ kanıtlar.

- [x] **Step 1: Write the failing test**

```python
class OluHalkaTesti(unittest.TestCase):
    """Sozlesmenin 1. kabul olcutu: hicbir halka olu olmamali."""

    def _kodlayici_ve_durumlar(self, n=9, d=16):
        kod = m.Kodlayici(boyut=d, bas_sayisi=2, tohum=2026)
        rng = m.tohumlu_rng("test-durum", n, d)
        durumlar = [[rng.uniform(-1, 1) for _ in range(d)] for _ in range(n)]
        return kod, durumlar

    def _fark(self, a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def test_qk_terimi_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        acik = kod.ileri(durumlar, qk_acik=True)
        kapali = kod.ileri(durumlar, qk_acik=False)
        self.assertGreater(self._fark(acik, kapali), 1e-6,
                           "QK terimi ciktiyi degistirmiyor -> olu halka")

    def test_nedensel_maske_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        acik = kod.ileri(durumlar, maske_acik=True)
        kapali = kod.ileri(durumlar, maske_acik=False)
        self.assertGreater(self._fark(acik, kapali), 1e-6,
                           "Nedensel maske ciktiyi degistirmiyor -> olu halka")

    def test_ffn_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        acik = kod.ileri(durumlar, ffn_acik=True)
        kapali = kod.ileri(durumlar, ffn_acik=False)
        self.assertGreater(self._fark(acik, kapali), 1e-6,
                           "FFN ciktiyi degistirmiyor -> olu halka")

    def test_girdi_degisince_cikti_degisir(self):
        """Temsil piyasaya duyarli olmali (63-bulgu #0'in panzehiri)."""
        kod, durumlar = self._kodlayici_ve_durumlar()
        rng = m.tohumlu_rng("test-durum-2", 9, 16)
        baska = [[rng.uniform(-1, 1) for _ in range(16)] for _ in range(9)]
        self.assertGreater(self._fark(kod.ileri(durumlar), kod.ileri(baska)), 1e-3)

    def test_duyarlilik_orani_esik_ustunde(self):
        """Farkli girdilerde temsil degisken payi olculebilir olmali."""
        kod = m.Kodlayici(boyut=16, bas_sayisi=2, tohum=2026)
        ciktilar = []
        for k in range(20):
            rng = m.tohumlu_rng("duyarlilik", k)
            durumlar = [[rng.uniform(-1, 1) for _ in range(16)] for _ in range(9)]
            ciktilar.append(kod.ileri(durumlar))
        ortalama = [sum(c[j] for c in ciktilar) / len(ciktilar) for j in range(16)]
        sapma = [math.sqrt(sum((c[j] - ortalama[j]) ** 2 for c in ciktilar) / len(ciktilar))
                 for j in range(16)]
        norm_ort = math.sqrt(sum(x * x for x in ortalama))
        norm_sap = math.sqrt(sum(x * x for x in sapma))
        degisken_pay = norm_sap / math.sqrt(norm_sap ** 2 + norm_ort ** 2)
        self.assertGreater(degisken_pay, 0.10,
                           f"temsil %{degisken_pay*100:.1f} degisken - cok sabit")


class SoftmaxTesti(unittest.TestCase):
    def test_toplam_bir(self):
        p = m.kararli_softmax([1.0, 2.0, 3.0])
        self.assertAlmostEqual(sum(p), 1.0, places=9)

    def test_sicaklik_sirayi_degistirmez(self):
        z = [3.0, 1.0]
        for T in (0.1, 1.0, 10.0):
            p = m.kararli_softmax(z, T)
            self.assertGreater(p[0], p[1])

    def test_buyuk_deger_tasmaz(self):
        p = m.kararli_softmax([1000.0, 999.0])
        self.assertTrue(all(math.isfinite(x) for x in p))
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.OluHalkaTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'Kodlayici'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 7c
# Causal attention + FFN. qk_acik/maske_acik/ffn_acik anahtarlari YALNIZ
# olu-halka testleri icindir; uretimde daima True.


def matris(satir, sutun, tohum_parcalari, olcek=0.12):
    rng = tohumlu_rng(*tohum_parcalari)
    return [[rng.uniform(-olcek, olcek) for _ in range(sutun)] for _ in range(satir)]


def vektor(boyut, tohum_parcalari, olcek=0.12):
    rng = tohumlu_rng(*tohum_parcalari)
    return [rng.uniform(-olcek, olcek) for _ in range(boyut)]


def matvec(M, v):
    return [sum(satir[j] * v[j] for j in range(len(v))) for satir in M]


def nokta(a, b):
    return sum(x * y for x, y in zip(a, b))


def topla_vek(*vektorler):
    if not vektorler:
        return []
    return [sum(v[i] for v in vektorler) for i in range(len(vektorler[0]))]


def kararli_softmax(logitler, sicaklik=1.0):
    T = max(float(sicaklik), 1e-6)
    olcekli = [float(z) / T for z in logitler]
    en_buyuk = max(olcekli) if olcekli else 0.0
    us = [math.exp(max(-60.0, min(60.0, z - en_buyuk))) for z in olcekli]
    toplam = sum(us) or 1.0
    return [u / toplam for u in us]


def katman_norm(v, epsilon=1e-5):
    ort = sum(v) / len(v)
    std = math.sqrt(sum((x - ort) ** 2 for x in v) / len(v) + epsilon)
    return [(x - ort) / std for x in v]


def relu(v):
    return [max(0.0, x) for x in v]


class Kodlayici:
    """Tek bloklu nedensel kodlayici. Karar tokeni SON siradadir; ara durumlar
    da FFN'e girer, boylece maske ciktiyi gercekten etkiler."""

    def __init__(self, boyut=16, bas_sayisi=2, tohum=2026):
        self.boyut = boyut
        self.bas_sayisi = bas_sayisi
        self.bas_boyut = boyut // bas_sayisi
        self.tohum = tohum
        self.wq = [matris(self.bas_boyut, boyut, (tohum, "wq", h)) for h in range(bas_sayisi)]
        self.wk = [matris(self.bas_boyut, boyut, (tohum, "wk", h)) for h in range(bas_sayisi)]
        self.wv = [matris(self.bas_boyut, boyut, (tohum, "wv", h)) for h in range(bas_sayisi)]
        self.wo = matris(boyut, self.bas_boyut * bas_sayisi, (tohum, "wo"))
        self.ff1 = matris(boyut * 2, boyut, (tohum, "ff1"))
        self.ff2 = matris(boyut, boyut * 2, (tohum, "ff2"))

    def _dikkat(self, durumlar, qk_acik, maske_acik):
        n = len(durumlar)
        olcek = math.sqrt(max(1, self.bas_boyut))
        bas_ciktilari = []
        for h in range(self.bas_sayisi):
            q = [matvec(self.wq[h], x) for x in durumlar]
            k = [matvec(self.wk[h], x) for x in durumlar]
            v = [matvec(self.wv[h], x) for x in durumlar]
            cikti = []
            for i in range(n):
                skorlar = []
                for j in range(n):
                    if maske_acik and j > i:
                        skorlar.append(-1e9)
                    elif qk_acik:
                        skorlar.append(nokta(q[i], k[j]) / olcek)
                    else:
                        skorlar.append(0.0)
                agirlik = kararli_softmax(skorlar)
                cikti.append([sum(agirlik[j] * v[j][u] for j in range(n))
                              for u in range(self.bas_boyut)])
            bas_ciktilari.append(cikti)
        return bas_ciktilari

    def ileri(self, durumlar, qk_acik=True, maske_acik=True, ffn_acik=True):
        """Karar temsilini dondurur. Ara durumlar havuzlanir -> maske etkilidir."""
        n = len(durumlar)
        bas_ciktilari = self._dikkat(durumlar, qk_acik, maske_acik)
        yeni = []
        for i in range(n):
            birlesik = []
            for h in range(self.bas_sayisi):
                birlesik.extend(bas_ciktilari[h][i])
            yeni.append(katman_norm(topla_vek(durumlar[i], matvec(self.wo, birlesik))))

        # Karar temsili: son token + TUM durumlarin ortalamasi.
        # Ortalama sayesinde maskelenen konumlar cikitiyi gercekten etkiler.
        havuz = [sum(y[j] for y in yeni) / n for j in range(self.boyut)]
        h_vek = topla_vek(yeni[-1], havuz)
        if ffn_acik:
            ff = relu(matvec(self.ff1, h_vek))
            h_vek = topla_vek(h_vek, matvec(self.ff2, ff))
        return katman_norm(h_vek)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.OluHalkaTesti test_llm_trading_v3.SoftmaxTesti -v`
Expected: PASS (8 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: nedensel attention + FFN, olu-halka testleriyle kanitlanmis"
```

---

### Task 11: Purge/embargo bölme ve logit başlığı — halka 6

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 7d)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `kararli_softmax`, `matris`, `vektor`, `nokta`, `tohumlu_rng` (Task 1, 10)
- Produces:
  - `kronolojik_bol(indeksler, ufuk, embargo, oranlar=(0.6, 0.2, 0.2)) -> dict` → `{"train": [...], "kalibrasyon": [...], "test": [...], "atilan": int}`
  - `Baslik` sınıfı: `.logit(x) -> list[float]`, `.egit(ornekler, devir, ogrenme_hizi)`
  - `sizinti_var_mi(bolme, ufuk, giris_penceresi) -> bool`

- [x] **Step 1: Write the failing test**

```python
class SizintiTesti(unittest.TestCase):
    def test_purge_embargo_ortusmeyi_keser(self):
        indeksler = list(range(0, 400, 5))
        b = m.kronolojik_bol(indeksler, ufuk=16, embargo=4)
        self.assertFalse(m.sizinti_var_mi(b, ufuk=16, giris_penceresi=6),
                         "purge/embargo etiket penceresini kesmeli")

    def test_purge_yoksa_sizinti_tespit_edilir(self):
        indeksler = list(range(0, 400, 5))
        b = m.kronolojik_bol(indeksler, ufuk=0, embargo=0)
        # ufuk 16 ile sinanirsa sizinti gorulmeli
        self.assertTrue(m.sizinti_var_mi(b, ufuk=16, giris_penceresi=6))

    def test_bolme_kronolojik_sirali(self):
        indeksler = list(range(0, 400, 5))
        b = m.kronolojik_bol(indeksler, ufuk=16, embargo=4)
        self.assertLess(max(b["train"]), min(b["kalibrasyon"]))
        self.assertLess(max(b["kalibrasyon"]), min(b["test"]))

    def test_atilan_ornek_sayilir(self):
        indeksler = list(range(0, 400, 5))
        b = m.kronolojik_bol(indeksler, ufuk=16, embargo=4)
        toplam = len(b["train"]) + len(b["kalibrasyon"]) + len(b["test"])
        self.assertEqual(toplam + b["atilan"], len(indeksler))
        self.assertGreater(b["atilan"], 0)

    def test_cok_az_veride_bos_bolme(self):
        b = m.kronolojik_bol([1, 2, 3], ufuk=16, embargo=4)
        self.assertEqual(b["train"], [])
        self.assertIn("yetersiz", b["not"])


class BaslikTesti(unittest.TestCase):
    def test_egitim_kaybi_duser(self):
        rng = m.tohumlu_rng("baslik-test")
        ornekler = []
        for _ in range(200):
            x = [rng.uniform(-1, 1) for _ in range(16)]
            y = 1 if sum(x[:4]) > 0 else 0      # ogrenilebilir kural
            ornekler.append({"x": x, "y": y})
        b = m.Baslik(boyut=16, tohum=7)
        once = b.kayip(ornekler)
        b.egit(ornekler, devir=60, ogrenme_hizi=0.15)
        sonra = b.kayip(ornekler)
        self.assertLess(sonra, once, "egitim kaybi dusmeli")

    def test_logit_iki_sinif(self):
        b = m.Baslik(boyut=16, tohum=7)
        z = b.logit([0.0] * 16)
        self.assertEqual(len(z), 2)

    def test_egitilmemis_baslik_neredeyse_esit_olasilik(self):
        b = m.Baslik(boyut=16, tohum=7)
        p = m.kararli_softmax(b.logit([0.0] * 16))
        self.assertAlmostEqual(p[0], 0.5, places=1)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.SizintiTesti test_llm_trading_v3.BaslikTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'kronolojik_bol'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 7d
# Kronolojik bolme + purge/embargo + egitilen logit basligi (V = LONG/SHORT).


def kronolojik_bol(indeksler, ufuk, embargo, oranlar=(0.6, 0.2, 0.2)):
    """Train/kalibrasyon/test; sinirlarda purge (ufuk) + embargo uygulanir."""
    sirali = sorted(indeksler)
    n = len(sirali)
    bosluk = int(ufuk) + int(embargo)
    if n < 3 * (bosluk + 5):
        return {"train": [], "kalibrasyon": [], "test": [], "atilan": n,
                "not": "yetersiz ornek - bolme yapilamadi"}

    kesim1 = int(n * oranlar[0])
    kesim2 = int(n * (oranlar[0] + oranlar[1]))
    train = sirali[:kesim1]
    kalibrasyon = sirali[kesim1:kesim2]
    test = sirali[kesim2:]

    # PURGE: train'in etiket penceresi kalibrasyonun girdisine tasmasin
    if train and kalibrasyon:
        sinir = kalibrasyon[0]
        train = [i for i in train if i + bosluk < sinir]
    if kalibrasyon and test:
        sinir = test[0]
        kalibrasyon = [i for i in kalibrasyon if i + bosluk < sinir]

    atilan = n - (len(train) + len(kalibrasyon) + len(test))
    return {"train": train, "kalibrasyon": kalibrasyon, "test": test,
            "atilan": atilan, "not": ""}


def sizinti_var_mi(bolme, ufuk, giris_penceresi):
    """Bir bolmenin etiket penceresi sonraki bolmenin girdi penceresine giriyor mu?"""
    ciftler = [("train", "kalibrasyon"), ("kalibrasyon", "test")]
    for once, sonra in ciftler:
        a, b = bolme.get(once) or [], bolme.get(sonra) or []
        if not a or not b:
            continue
        etiket_sonu = max(a) + int(ufuk)
        girdi_basi = min(b) - int(giris_penceresi) + 1
        if etiket_sonu >= girdi_basi:
            return True
    return False


class Baslik:
    """Iki sinifli (LONG/SHORT) egitilen logit basligi, agirlikli capraz entropi."""

    def __init__(self, boyut=16, tohum=3000):
        self.boyut = boyut
        self.w = matris(2, boyut, (tohum, "baslik-w"), 0.02)
        self.b = vektor(2, (tohum, "baslik-b"), 0.02)
        self.tohum = tohum

    def logit(self, x):
        return [nokta(self.w[k], x) + self.b[k] for k in range(2)]

    def kayip(self, ornekler):
        if not ornekler:
            return float("inf")
        toplam = 0.0
        for o in ornekler:
            p = kararli_softmax(self.logit(o["x"]))
            toplam += -math.log(max(1e-12, p[o["y"]]))
        return toplam / len(ornekler)

    def _sinif_agirliklari(self, ornekler):
        sayim = [0, 0]
        for o in ornekler:
            sayim[o["y"]] += 1
        toplam = sum(sayim) or 1
        return [toplam / (2.0 * max(1, s)) for s in sayim]

    def egit(self, ornekler, devir=60, ogrenme_hizi=0.10, agirlik_azalmasi=5e-4):
        if not ornekler:
            return
        agirliklar = self._sinif_agirliklari(ornekler)
        rng = tohumlu_rng(self.tohum, "karistir")
        sira = list(range(len(ornekler)))
        for adim in range(devir):
            rng.shuffle(sira)
            grad_w = [[0.0] * self.boyut for _ in range(2)]
            grad_b = [0.0, 0.0]
            for indeks in sira:
                o = ornekler[indeks]
                p = kararli_softmax(self.logit(o["x"]))
                agirlik = agirliklar[o["y"]]
                for k in range(2):
                    hata = (p[k] - (1.0 if k == o["y"] else 0.0)) * agirlik
                    for j in range(self.boyut):
                        grad_w[k][j] += hata * o["x"][j]
                    grad_b[k] += hata
            hiz = ogrenme_hizi / (1.0 + adim / 25.0)
            payda = max(1, len(ornekler))
            for k in range(2):
                for j in range(self.boyut):
                    g = grad_w[k][j] / payda + agirlik_azalmasi * self.w[k][j]
                    self.w[k][j] -= hiz * g
                self.b[k] -= hiz * grad_b[k] / payda
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.SizintiTesti test_llm_trading_v3.BaslikTesti -v`
Expected: PASS (8 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: purge/embargo kronolojik bolme ve egitilen iki-sinifli logit basligi"
```

---

### Task 12: Kalibrasyon fit — halka 7, dağıtılan dağılımın kendisinde

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 7e)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `kararli_softmax`, `ece`, `brier` (Task 3, 10)
- Produces:
  - `topluluk_olasilik(x, basliklar, sicaklik) -> dict` → `{"p": [p_long, p_short], "gorusler": [...], "uzlasi": float, "dagilim": float}`
  - `sicaklik_fit(ornekler, basliklar) -> dict` → `{"T": float, "nll": float, "sinirda": bool}`
  - `izotonik_fit(ciftler) -> callable`
  - `kalibrasyon_sec(kal_ornekler, basliklar) -> dict` → `{"yontem": str, "T": float, "fn": callable, "nll": float}`

**Kritik:** `sicaklik_fit`, `topluluk_olasilik`'ın ürettiği **aynı** dağılım üzerinde NLL minimize eder (63-bulgu #28'in panzehiri).

- [x] **Step 1: Write the failing test**

```python
class KalibrasyonFitTesti(unittest.TestCase):
    def _basliklar_ve_ornekler(self):
        rng = m.tohumlu_rng("kal-fit")
        basliklar = [m.Baslik(boyut=8, tohum=100 + k) for k in range(3)]
        ornekler = []
        for _ in range(300):
            x = [rng.uniform(-1, 1) for _ in range(8)]
            y = 1 if sum(x[:3]) > 0 else 0
            ornekler.append({"x": x, "y": y})
        for b in basliklar:
            b.egit(ornekler[:200], devir=40, ogrenme_hizi=0.2)
        return basliklar, ornekler[200:]

    def test_sicaklik_fit_dagitilan_dagilimda_yapilir(self):
        """T, topluluk_olasilik'in urettigi dagilimda fit edilmeli."""
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.sicaklik_fit(kal, basliklar)
        # fit edilen T ile hesaplanan NLL, baska bir T'den kucuk olmali
        def nll(T):
            toplam = 0.0
            for o in kal:
                p = m.topluluk_olasilik(o["x"], basliklar, T)["p"]
                toplam += -math.log(max(1e-12, p[o["y"]]))
            return toplam / len(kal)
        self.assertLessEqual(r["nll"], nll(1.0) + 1e-9)
        self.assertLessEqual(r["nll"], nll(5.0) + 1e-9)

    def test_sicaklik_sinirda_bayragi(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.sicaklik_fit(kal, basliklar)
        self.assertIn("sinirda", r)
        self.assertIsInstance(r["sinirda"], bool)

    def test_topluluk_uzlasi_ve_dagilim(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.topluluk_olasilik(kal[0]["x"], basliklar, 1.0)
        self.assertAlmostEqual(sum(r["p"]), 1.0, places=9)
        self.assertGreaterEqual(r["uzlasi"], 1.0 / 3.0)
        self.assertLessEqual(r["uzlasi"], 1.0)
        self.assertGreaterEqual(r["dagilim"], 0.0)

    def test_izotonik_monoton(self):
        ciftler = [(0.1, 0), (0.2, 0), (0.3, 1), (0.4, 0), (0.5, 1),
                   (0.6, 1), (0.7, 1), (0.8, 1), (0.9, 1)]
        fn = m.izotonik_fit(ciftler)
        degerler = [fn(x / 10.0) for x in range(1, 10)]
        for i in range(1, len(degerler)):
            self.assertGreaterEqual(degerler[i] + 1e-9, degerler[i - 1])

    def test_kalibrasyon_sec_nll_dusuk_olani_secer(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.kalibrasyon_sec(kal, basliklar)
        self.assertIn(r["yontem"], ("sicaklik", "izotonik"))
        self.assertTrue(math.isfinite(r["nll"]))
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.KalibrasyonFitTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'topluluk_olasilik'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 7e
# Kalibrasyon: T, DAGITILAN dagilimin kendisinde fit edilir (log-havuz /
# olasilik-havuz uyusmazligi yapisal olarak kapatilir).

SICAKLIK_IZGARASI = tuple(math.exp(-2.0 + 4.0 * i / 40.0) for i in range(41))


def topluluk_olasilik(x, basliklar, sicaklik=1.0):
    """Her baslik icin softmax alinir, SONRA olasiliklar ortalanir."""
    gorusler = [kararli_softmax(b.logit(x), sicaklik) for b in basliklar]
    n = len(gorusler) or 1
    p = [sum(g[k] for g in gorusler) / n for k in range(2)]
    argmaxlar = [0 if g[0] >= g[1] else 1 for g in gorusler]
    uzlasi = max(argmaxlar.count(0), argmaxlar.count(1)) / n
    dagilim = sum(sum((g[k] - p[k]) ** 2 for g in gorusler) / n for k in range(2)) / 2.0
    return {"p": p, "gorusler": gorusler, "uzlasi": uzlasi, "dagilim": dagilim}


def _nll(ornekler, basliklar, sicaklik):
    if not ornekler:
        return float("inf")
    toplam = 0.0
    for o in ornekler:
        p = topluluk_olasilik(o["x"], basliklar, sicaklik)["p"]
        toplam += -math.log(max(1e-12, p[o["y"]]))
    return toplam / len(ornekler)


def sicaklik_fit(ornekler, basliklar):
    """T'yi DAGITILAN dagilimda (olasilik-havuzu) NLL minimize ederek secer."""
    en_iyi_T, en_iyi_nll = 1.0, float("inf")
    for T in SICAKLIK_IZGARASI:
        deger = _nll(ornekler, basliklar, T)
        if deger < en_iyi_nll:
            en_iyi_T, en_iyi_nll = T, deger
    sinirda = (en_iyi_T <= SICAKLIK_IZGARASI[0] * 1.001 or
               en_iyi_T >= SICAKLIK_IZGARASI[-1] * 0.999)
    return {"T": en_iyi_T, "nll": en_iyi_nll, "sinirda": sinirda}


def izotonik_fit(ciftler):
    """PAVA ile monoton kalibrasyon egrisi. Donen fonksiyon p -> p_kalibre."""
    sirali = sorted(ciftler, key=lambda c: c[0])
    if not sirali:
        return lambda p: p
    x = [c[0] for c in sirali]
    y = [float(c[1]) for c in sirali]
    agirlik = [1.0] * len(y)
    i = 0
    while i < len(y) - 1:
        if y[i] <= y[i + 1] + 1e-12:
            i += 1
            continue
        toplam_a = agirlik[i] + agirlik[i + 1]
        ort = (y[i] * agirlik[i] + y[i + 1] * agirlik[i + 1]) / toplam_a
        y[i:i + 2] = [ort]
        agirlik[i:i + 2] = [toplam_a]
        x[i:i + 2] = [x[i]]
        i = max(0, i - 1)

    def uygula(p):
        if p <= x[0]:
            return y[0]
        for k in range(1, len(x)):
            if p <= x[k]:
                return y[k - 1]
        return y[-1]

    return uygula


def kalibrasyon_sec(kal_ornekler, basliklar):
    """Sicaklik ve izotonik arasinda holdout NLL'e gore secim."""
    sicaklik = sicaklik_fit(kal_ornekler, basliklar)

    ham = [(topluluk_olasilik(o["x"], basliklar, 1.0)["p"][0], o["y"]) for o in kal_ornekler]
    izo = izotonik_fit(ham)
    izo_nll = 0.0
    for p_ham, y in ham:
        p_kal = min(1.0 - 1e-9, max(1e-9, izo(p_ham)))
        izo_nll += -math.log(p_kal if y == 1 else 1.0 - p_kal)
    izo_nll = izo_nll / len(ham) if ham else float("inf")

    if izo_nll < sicaklik["nll"]:
        return {"yontem": "izotonik", "T": 1.0, "fn": izo, "nll": izo_nll,
                "sinirda": False}
    T = sicaklik["T"]
    return {"yontem": "sicaklik", "T": T, "fn": None, "nll": sicaklik["nll"],
            "sinirda": sicaklik["sinirda"]}
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.KalibrasyonFitTesti -v`
Expected: PASS (5 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: kalibrasyon fit - dagitilan dagilimda sicaklik + izotonik yarismasi"
```

---

### Task 13: Decoding ve nihai karar — halka 9, 10, 12

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 8)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `topluluk_olasilik`, `daralt`, `shrinkage_katsayisi`, `geometri_sec`, `stake_kirp`, `likidasyon_tavani`, `kelly_asimetrik` (Task 4, 6, 12)
- Produces:
  - `decode(p_long: float) -> str` — daima "LONG" veya "SHORT"
  - `seviyeler(giris, atr, yon, stop_k, hedef_k) -> dict`
  - `karar_uret(baglam: dict) -> dict` — tek sembol için nihai karar sözlüğü

- [x] **Step 1: Write the failing test**

```python
class DecodingTesti(unittest.TestCase):
    def test_daima_yon_uretir(self):
        for p in (0.0, 0.4999, 0.5, 0.5001, 1.0):
            self.assertIn(m.decode(p), m.YON_SOZLUGU)

    def test_beraberlikte_long(self):
        self.assertEqual(m.decode(0.5), "LONG")

    def test_hold_asla_donmez(self):
        rng = m.tohumlu_rng("decode-fuzz")
        for _ in range(500):
            self.assertIn(m.decode(rng.random()), ("LONG", "SHORT"))

    def test_seviyeler_long_yonlu(self):
        s = m.seviyeler(giris=100.0, atr=2.0, yon="LONG", stop_k=1.5, hedef_k=3.0)
        self.assertAlmostEqual(s["stop"], 97.0, places=9)
        self.assertAlmostEqual(s["hedef"], 106.0, places=9)
        self.assertAlmostEqual(s["R"], 2.0, places=9)

    def test_seviyeler_short_simetrik(self):
        s = m.seviyeler(100.0, 2.0, "SHORT", 1.5, 3.0)
        self.assertAlmostEqual(s["stop"], 103.0, places=9)
        self.assertAlmostEqual(s["hedef"], 94.0, places=9)

    def test_stake_sifirken_bile_seviyeler_uretilir(self):
        """Belgenin Gerekce 5'i: seviyeler KOSULSUZ uretilir."""
        baglam = self._baglam(kanit_yok=True)
        r = m.karar_uret(baglam)
        self.assertIn(r["yon"], m.YON_SOZLUGU)
        self.assertIsNotNone(r["giris"])
        self.assertIsNotNone(r["stop"])
        self.assertIsNotNone(r["hedef"])
        self.assertEqual(r["stake"]["f"], 0.0)

    def test_kanit_yoksa_stake_sifir(self):
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertEqual(r["stake"]["f"], 0.0)
        self.assertEqual(r["shrinkage"]["s"], 0.0)

    def test_cikti_lambda_uclusu_icerir(self):
        r = m.karar_uret(self._baglam(kanit_yok=True))
        for lam in ("1.0", "0.5", "0.25"):
            self.assertIn(lam, r["stake"]["lambda_tablosu"])

    def test_basabas_p_daima_raporlanir(self):
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertIn("basabas_p", r["geometri"])

    def _baglam(self, kanit_yok=True):
        barlar = [{"o": 100 + i * 0.1, "h": 100 + i * 0.1 + 0.5,
                   "l": 100 + i * 0.1 - 0.5, "c": 100 + i * 0.1} for i in range(300)]
        return {
            "sembol": "BTCUSDT",
            "barlar": barlar,
            "atr_serisi": [1.0] * 300,
            "indeksler": list(range(0, 250, 5)),
            "p_ham": 0.95 if kanit_yok else 0.72,
            "dogru": 17 if kanit_yok else 700,
            "toplam": 48 if kanit_yok else 1000,
            "ece_enkotu": 0.02,
            "dolu_kanal": 6,
            "toplam_kanal": 6,
            "giris": 130.0,
            "atr": 1.0,
            "likidasyon": 100.0,
            "kaldirac_azami": 10.0,
            "komisyon": 0.0004,
            "kayma": 0.0005,
            "funding": 0.0,
            "lam": 1.0,
        }
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.DecodingTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'decode'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 8
# Decoding: sozluk V = {LONG, SHORT}. HOLD YOKTUR. Seviyeler KOSULSUZ uretilir.
# Stake ayri bir eksendir; f*=0 bir sinif degil, Kelly'nin dogal degeridir.

LAMBDA_TABLOSU = (1.0, 0.5, 0.25)


def decode(p_long):
    """argmax. Beraberlikte LONG (tanimli ve deterministik)."""
    return "LONG" if float(p_long) >= 0.5 else "SHORT"


def seviyeler(giris, atr, yon, stop_k, hedef_k):
    giris, atr = float(giris), max(float(atr), EPSILON)
    if yon == "LONG":
        stop = giris - stop_k * atr
        hedef = giris + hedef_k * atr
    else:
        stop = giris + stop_k * atr
        hedef = giris - hedef_k * atr
    return {"giris": giris, "stop": stop, "hedef": hedef,
            "stop_mesafesi": abs(giris - stop), "R": hedef_k / stop_k}


def karar_uret(baglam):
    """Tek sembol icin nihai karar: YON (zorunlu) + STAKE (surekli)."""
    # 1) Kanit gucu -> shrinkage
    shr = shrinkage_katsayisi(baglam["dogru"], baglam["toplam"],
                              baglam.get("ece_enkotu"),
                              baglam["dolu_kanal"], baglam["toplam_kanal"])
    p_kullanilan = daralt(baglam["p_ham"], shr["s"])

    # 2) YON — kosulsuz, daraltilmamis olasiligin isaretinden (yon bilgisi kaybolmasin)
    yon = decode(baglam["p_ham"])
    p_yon = p_kullanilan if yon == "LONG" else (1.0 - p_kullanilan)

    # 3) Geometri — maliyet stop mesafesine bagli oldugu icin aday basina hesaplanir
    def cost_r_fn(stop_k):
        mesafe = stop_k * max(float(baglam["atr"]), EPSILON)
        return maliyet_r(baglam["giris"], mesafe, baglam["komisyon"],
                         baglam["kayma"], baglam["funding"])

    geo = geometri_sec(baglam["barlar"], baglam["indeksler"], yon,
                       baglam["atr_serisi"], p_yon, cost_r_fn,
                       lam=1.0, azami_bar=baglam.get("azami_bar", 32))

    # 4) Seviyeler — KOSULSUZ
    sev = seviyeler(baglam["giris"], baglam["atr"], yon,
                    geo["stop_k"], geo["hedef_k"])

    # 5) Stake — lambda tablosu + likidasyon tavani
    f_max = likidasyon_tavani(baglam["giris"], baglam.get("likidasyon"),
                              baglam.get("kaldirac_azami"), 0.5)
    lambda_tablosu = {}
    for lam in LAMBDA_TABLOSU:
        kirpilmis = stake_kirp(geo["f"] * lam, f_max)
        lambda_tablosu[str(lam)] = kirpilmis
    secilen = lambda_tablosu[str(float(baglam.get("lam", 1.0)))]

    return {
        "sembol": baglam["sembol"],
        "yon": yon,
        "p_ham": baglam["p_ham"],
        "p_kullanilan": p_kullanilan,
        "shrinkage": shr,
        "geometri": geo,
        "giris": sev["giris"], "stop": sev["stop"], "hedef": sev["hedef"],
        "R": sev["R"],
        "stake": {"f": secilen["f"], "kirpildi": secilen["kirpildi"],
                  "f_max": f_max, "lambda_tablosu": lambda_tablosu},
    }
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.DecodingTesti -v`
Expected: PASS (9 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: decoding (HOLD yok) + kosulsuz seviyeler + surekli stake ekseni"
```

---

### Task 14: Öznitelik üretimi ve uçtan uca boru hattı — halka 0, 1, 11

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 9)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: tüm önceki bölümler
- Produces:
  - `ema(degerler, periyot) -> list[float]`, `atr(barlar, periyot) -> list[float]`, `rsi(kapanislar, periyot) -> list[float]`
  - `satir_uret(barlar15, barlar4h, turev, indeks) -> dict`
  - `BoruHatti` sınıfı: `.calistir(veri_paketi) -> dict`

- [x] **Step 1: Write the failing test**

```python
class GostergeTesti(unittest.TestCase):
    def test_ema_ilk_deger_girdiye_esit(self):
        self.assertAlmostEqual(m.ema([5.0, 6.0, 7.0], 3)[0], 5.0, places=9)

    def test_ema_uzunluk_korunur(self):
        self.assertEqual(len(m.ema([1.0] * 10, 3)), 10)

    def test_atr_pozitif(self):
        barlar = [{"o": 100, "h": 101, "l": 99, "c": 100} for _ in range(20)]
        self.assertTrue(all(x >= 0 for x in m.atr(barlar, 14)))

    def test_rsi_araligi(self):
        rng = m.tohumlu_rng("rsi")
        kapanislar = [100 + rng.uniform(-1, 1) for _ in range(60)]
        for x in m.rsi(kapanislar, 14):
            self.assertGreaterEqual(x, 0.0)
            self.assertLessEqual(x, 100.0)


class BoruHattiTesti(unittest.TestCase):
    def _paket(self, turev_var=True):
        rng = m.tohumlu_rng("boru")
        barlar15 = []
        fiyat = 100.0
        for _ in range(600):
            fiyat *= (1.0 + rng.uniform(-0.003, 0.0032))
            barlar15.append({"o": fiyat, "h": fiyat * 1.002, "l": fiyat * 0.998,
                             "c": fiyat, "v": 1000 + rng.uniform(0, 100)})
        barlar4h = barlar15[::16]
        turev = {"oi_degisim": 0.01, "funding_z": 0.2, "taker_dengesi": 0.1,
                 "derinlik_dengesi": -0.05} if turev_var else None
        return {"sembol": "BTCUSDT", "barlar15": barlar15, "barlar4h": barlar4h,
                "turev": turev, "kapsam": 1.0 if turev_var else 0.5,
                "dolu_kanal": 6 if turev_var else 3, "toplam_kanal": 6}

    def test_uctan_uca_karar_uretir(self):
        bh = m.BoruHatti(tohum=2026)
        r = bh.calistir(self._paket())
        self.assertIn(r["yon"], m.YON_SOZLUGU)
        self.assertIsNotNone(r["giris"])
        self.assertIn("iz", r)

    def test_iz_on_iki_halka_icerir(self):
        bh = m.BoruHatti(tohum=2026)
        r = bh.calistir(self._paket())
        for halka in range(13):
            self.assertIn(f"halka_{halka}", r["iz"], f"halka_{halka} izde yok")

    def test_determinizm(self):
        p = self._paket()
        a = m.BoruHatti(tohum=2026).calistir(p)
        b = m.BoruHatti(tohum=2026).calistir(p)
        self.assertEqual(a["yon"], b["yon"])
        self.assertAlmostEqual(a["p_kullanilan"], b["p_kullanilan"], places=12)
        self.assertAlmostEqual(a["stake"]["f"], b["stake"]["f"], places=12)

    def test_kanal_dususu_stake_dusurur(self):
        tam = m.BoruHatti(tohum=2026).calistir(self._paket(turev_var=True))
        eksik = m.BoruHatti(tohum=2026).calistir(self._paket(turev_var=False))
        self.assertLessEqual(eksik["stake"]["f"], tam["stake"]["f"])
        self.assertLess(eksik["shrinkage"]["s_kapsam"], tam["shrinkage"]["s_kapsam"])

    def test_turev_ailesi_temsili_degistirir(self):
        """Turev kanali gercekten modele giriyor mu (63-bulgu #1'in panzehiri)."""
        bh = m.BoruHatti(tohum=2026)
        p1 = self._paket(turev_var=True)
        p2 = self._paket(turev_var=True)
        p2["turev"] = {"oi_degisim": -0.9, "funding_z": -2.0,
                       "taker_dengesi": -0.8, "derinlik_dengesi": 0.7}
        r1 = bh.calistir(p1)
        r2 = m.BoruHatti(tohum=2026).calistir(p2)
        self.assertNotAlmostEqual(r1["p_ham"], r2["p_ham"], places=6)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.GostergeTesti test_llm_trading_v3.BoruHattiTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'ema'`

- [x] **Step 3: Write minimal implementation**

Bu görev iki parçadır. Önce göstergeler:

```python
# ---------------------------------------------------------------- BOLUM 9a
# Gostergeler (stdlib, kayan pencere).


def ema(degerler, periyot):
    if not degerler:
        return []
    alfa = 2.0 / (periyot + 1.0)
    cikti = [float(degerler[0])]
    for x in degerler[1:]:
        cikti.append(alfa * float(x) + (1.0 - alfa) * cikti[-1])
    return cikti


def atr(barlar, periyot=14):
    gercek_araliklar = []
    for i, b in enumerate(barlar):
        onceki = barlar[i - 1]["c"] if i else b["c"]
        gercek_araliklar.append(max(b["h"] - b["l"], abs(b["h"] - onceki),
                                    abs(b["l"] - onceki)))
    cikti = []
    for i in range(len(gercek_araliklar)):
        pencere = gercek_araliklar[max(0, i - periyot + 1):i + 1]
        cikti.append(sum(pencere) / len(pencere))
    return cikti


def rsi(kapanislar, periyot=14):
    cikti = [50.0] * len(kapanislar)
    for i in range(periyot, len(kapanislar)):
        kazanc, kayip = [], []
        for j in range(i - periyot + 1, i + 1):
            fark = kapanislar[j] - kapanislar[j - 1]
            kazanc.append(max(fark, 0.0))
            kayip.append(max(-fark, 0.0))
        ok = sum(kazanc) / len(kazanc)
        oy = sum(kayip) / len(kayip)
        if oy == 0:
            cikti[i] = 100.0 if ok > 0 else 50.0
        else:
            cikti[i] = 100.0 - 100.0 / (1.0 + ok / oy)
    return cikti
```

Sonra boru hattı (`BoruHatti.calistir` içinde 12 halkanın her biri `iz` sözlüğüne yazılır ve
`satir_uret` türev ailesini gerçek değerlerle doldurur; türev yoksa `None` kalır ve
`s_kapsam` düşer). Uygulama sırası: satır üretimi → sözlük → ölçekleyici (train-only) →
konum kodu → kodlayıcı → bölme → başlık eğitimi → kalibrasyon → topluluk → decode →
geometri → stake → iz.

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3.GostergeTesti test_llm_trading_v3.BoruHattiTesti -v`
Expected: PASS (9 test)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: gostergeler ve uctan uca boru hatti, 12 halka izi"
```

---

### Task 15: Çıktı, kâğıt defteri, CLI ve öz-test

**Files:**
- Modify: `llm_trading_v3.py` (bölüm 10)
- Modify: `test_llm_trading_v3.py`

**Interfaces:**
- Consumes: `BoruHatti`, `karar_uret` (Task 13, 14)
- Produces:
  - `rapor_yaz(kararlar, dosya) -> None`
  - `defter_guncelle(durum, karar, bar) -> dict`
  - `metin_rapor(karar) -> str`
  - `main(argv) -> int`

- [x] **Step 1: Write the failing test**

```python
class CiktiTesti(unittest.TestCase):
    def _karar(self):
        return {
            "sembol": "BTCUSDT", "yon": "LONG", "p_ham": 0.55,
            "p_kullanilan": 0.5,
            "shrinkage": {"s": 0.0, "s_kanit": 0.0, "s_kalibrasyon": 1.0, "s_kapsam": 1.0},
            "geometri": {"stop_k": 1.5, "hedef_k": 3.0, "R": 2.0, "p_hedef": 0.4,
                         "n": 40, "basabas_p": 0.68, "elog": -0.01, "not": ""},
            "giris": 100.0, "stop": 98.5, "hedef": 103.0, "R": 2.0,
            "stake": {"f": 0.0, "kirpildi": False, "f_max": 0.1,
                      "lambda_tablosu": {"1.0": {"f": 0.0}, "0.5": {"f": 0.0},
                                         "0.25": {"f": 0.0}}},
        }

    def test_metin_rapor_yon_icerir(self):
        metin = m.metin_rapor(self._karar())
        self.assertIn("LONG", metin)

    def test_metin_rapor_stake_sifiri_gizlemez(self):
        metin = m.metin_rapor(self._karar())
        self.assertIn("f*", metin)
        self.assertIn("0.0", metin)

    def test_metin_rapor_basabas_gosterir(self):
        self.assertIn("basabas", m.metin_rapor(self._karar()).lower())

    def test_defter_stake_sifirda_pozisyon_acmaz(self):
        durum = {"sermaye": 1000.0, "pozisyonlar": {}}
        yeni = m.defter_guncelle(durum, self._karar(),
                                 {"o": 100, "h": 101, "l": 99, "c": 100})
        self.assertNotIn("BTCUSDT", yeni["pozisyonlar"])

    def test_defter_stake_pozitifken_pozisyon_acar(self):
        karar = self._karar()
        karar["stake"]["f"] = 0.02
        durum = {"sermaye": 1000.0, "pozisyonlar": {}}
        yeni = m.defter_guncelle(durum, karar, {"o": 100, "h": 101, "l": 99, "c": 100})
        self.assertIn("BTCUSDT", yeni["pozisyonlar"])

    def test_main_self_test_sifir_doner(self):
        self.assertEqual(m.main(["--self-test"]), 0)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_llm_trading_v3.CiktiTesti -v`
Expected: FAIL with `AttributeError: module 'llm_trading_v3' has no attribute 'metin_rapor'`

- [x] **Step 3: Write minimal implementation**

```python
# ---------------------------------------------------------------- BOLUM 10
# Cikti, kagit defteri, CLI. Gercek emir YOK.


def metin_rapor(karar):
    g = karar["geometri"]
    s = karar["stake"]
    satirlar = [
        "=" * 78,
        f"{karar['sembol']} | {SURUM} | YALNIZ KARAR-DESTEK (gercek emir YOK)",
        f"YON: {karar['yon']}   (p_ham={karar['p_ham']:.4f} -> "
        f"p_kullanilan={karar['p_kullanilan']:.4f})",
        f"SHRINKAGE s={karar['shrinkage']['s']:.4f} "
        f"(kanit={karar['shrinkage']['s_kanit']:.3f} "
        f"kalibrasyon={karar['shrinkage']['s_kalibrasyon']:.3f} "
        f"kapsam={karar['shrinkage']['s_kapsam']:.3f})",
        f"GEOMETRI stop_k={g['stop_k']} hedef_k={g['hedef_k']} R={g['R']:.4f} "
        f"p_hedef={g['p_hedef']} n={g['n']}",
        f"basabas p (f*>0 icin gereken) = {g['basabas_p']}",
        f"SEVIYELER giris={karar['giris']:.8g} stop={karar['stop']:.8g} "
        f"hedef={karar['hedef']:.8g}",
        f"STAKE f*={s['f']:.6f}  (f_max={s['f_max']:.6f}, "
        f"kirpildi={'EVET' if s['kirpildi'] else 'hayir'})",
        "  lambda: " + "  ".join(
            f"{lam}->{v['f']:.6f}" for lam, v in s["lambda_tablosu"].items()),
    ]
    if g.get("not"):
        satirlar.append(f"NOT: {g['not']}")
    if s["f"] == 0.0:
        satirlar.append("f*=0: yon ve seviyeler yine uretildi; bahis buyuklugu sifir.")
    return "\n".join(satirlar)


def defter_guncelle(durum, karar, bar):
    """Yerel kagit defteri. f*=0 ise pozisyon ACILMAZ (bahis sifir)."""
    yeni = {"sermaye": durum["sermaye"],
            "pozisyonlar": dict(durum.get("pozisyonlar", {}))}
    sembol = karar["sembol"]
    mevcut = yeni["pozisyonlar"].get(sembol)
    if mevcut:
        yon = mevcut["yon"]
        if yon == "LONG":
            cikis = mevcut["stop"] if bar["l"] <= mevcut["stop"] else (
                mevcut["hedef"] if bar["h"] >= mevcut["hedef"] else None)
        else:
            cikis = mevcut["stop"] if bar["h"] >= mevcut["stop"] else (
                mevcut["hedef"] if bar["l"] <= mevcut["hedef"] else None)
        if cikis is not None:
            isaret = 1.0 if yon == "LONG" else -1.0
            yeni["sermaye"] += isaret * (cikis - mevcut["giris"]) * mevcut["miktar"]
            yeni["pozisyonlar"].pop(sembol, None)

    if sembol not in yeni["pozisyonlar"] and karar["stake"]["f"] > 0.0:
        risk_tutari = yeni["sermaye"] * karar["stake"]["f"]
        mesafe = abs(karar["giris"] - karar["stop"]) or EPSILON
        yeni["pozisyonlar"][sembol] = {
            "yon": karar["yon"], "giris": karar["giris"], "stop": karar["stop"],
            "hedef": karar["hedef"], "miktar": risk_tutari / mesafe}
    return yeni


def _oz_test():
    """Gomulu hizli denetim (Pydroid 3 icin). unittest'i calistirir."""
    import unittest as _ut
    try:
        import test_llm_trading_v3 as _t
    except ImportError:
        print("test dosyasi bulunamadi - oz-test atlandi")
        return 1
    sonuc = _ut.TextTestRunner(verbosity=1).run(
        _ut.defaultTestLoader.loadTestsFromModule(_t))
    return 0 if sonuc.wasSuccessful() else 1


def main(argv=None):
    import argparse
    ayristirici = argparse.ArgumentParser(description=SURUM)
    ayristirici.add_argument("--self-test", action="store_true")
    ayristirici.add_argument("--lam", type=float, default=1.0)
    args = ayristirici.parse_args(argv)
    if args.self_test:
        return _oz_test()
    print("Canli kosu icin ag erisimi gerekir; bu ortamda --self-test kullanin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest test_llm_trading_v3 -v`
Expected: PASS (tüm testler)

- [x] **Step 5: Commit**

```bash
git add llm_trading_v3.py test_llm_trading_v3.py
git commit -m "feat: metin raporu, kagit defteri, CLI ve gomulu oz-test"
```

---

## Self-Review sonucu

**1. Spec kapsamı:** Spec'in her bölümü bir göreve bağlı —
§2 iki eksen → Task 13; §3 halka 0 → Task 7, halka 1 → Task 8, halka 2-3 → Task 9,
halka 4-5 → Task 10, halka 6 → Task 11, halka 7-8 → Task 12, halka 9-10 → Task 12-13,
halka 11-12 → Task 14-15; §4 kalibrasyon → Task 3, 4, 12; §5 geometri → Task 5, 6;
§6 hata yönetimi → Task 7 (uydurma yasağı), Task 9 (sabit kolon), Task 6 (fail-closed);
§7 test stratejisi → her görevde; §8 çıktı → Task 15; §9 kapsam dışı → Task 1 güvenlik testi.

**2. Placeholder taraması:** "TBD"/"TODO" yok; her kod adımında gerçek kod var.
Task 14 Step 3'ün ikinci parçası (BoruHatti gövdesi) sıra listesi olarak verildi — bu bir
placeholder değil, önceki 13 görevde tanımlanan fonksiyonların çağrı sırasıdır; her fonksiyon
adı ve imzası daha önce tanımlanmıştır.

**3. Tip tutarlılığı:** `ciftler` biçimi `(p_long, y)` her yerde aynı; `barlar` sözlüğü
`{"o","h","l","c"}` her yerde aynı; `geometri_sec` dönüşü `stop_k/hedef_k/R/p_hedef/f/elog/
basabas_p/not` alanlarıyla Task 6, 13, 15'te tutarlı; `stake_kirp` dönüşü `{"f","kirpildi",
"f_ham","f_max"}` Task 6 ve 13'te tutarlı; `shrinkage_katsayisi` dönüşü `{"s","s_kanit",
"s_kalibrasyon","s_kapsam"}` Task 4, 13, 15'te tutarlı.


---

## Uygulama sapmaları (plan → kod), gerekçeleriyle

Plan bir sözleşmedir; sapmalar sessiz kalamaz. 75 adımın tamamı uygulandı,
her grup bağımsız denetçiden PASS aldı (`denetim_sicili.md`). Aşağıdakiler
plandan **bilinçli** ayrılmalardır.

1. **`Adaptor.kline(sembol, aralik, limit)` / `.turev(sembol)` → tek
   `Adaptor.uc(kanal, sembol)`.** Plandaki iki metot ad olarak VERİ ÇEKMEYİ
   ima ediyor. Bu depoda ağ çağrısı yapılmaz: adaptör yalnız **public GET
   URL'i üretir**, isteği kullanıcı/dış katman atar. Altı kanalın tamamı
   (`KANALLAR`) tek bir sözlükten çözülüyor; iki ayrı metot aynı sözlüğü
   ikiye bölüp isim üzerinden yanlış bir yetenek vaat ederdi.

2. **`AZAMI_ORNEK` sabit 120 → türetilmiş 200.** Plan bunu bir hesap
   bütçesi olarak sabitliyordu. Ölçüldü ki 120, kalibrasyon dilimini
   yapısal olarak 24'te tavanlıyor ve `kalibrasyon_sec`'in adil yarışma
   şartını (`2 × ASGARI_OLCUM = 40`) **hiçbir veri miktarında**
   sağlayamıyor. Değer artık `ceil(2 × ASGARI_OLCUM / BOLME_ORANLARI[1])`
   ile modülün kendi sabitlerinden türetiliyor. **Yarışmayı açmak için
   büyütülmedi** — 200'de de `kal < 40` kalıyor ve doğru cevap "yarışma
   yapılamaz" demektir (izde beyan ediliyor). Eşiği geçiren değere çekmek
   aşırı-uyumdur.

3. **`ema()` özyinelemeli → sonlu pencerede kesilmiş.** Planda EMA'nın
   yazımı belirtilmemişti. Ölçüldü ki özyinelemeli (IIR) yazımın geriye
   erişimi **toleransa bağlı** (1e-15'te 301, 1e-9'da 168 bar) ve bu
   yüzden purge korkuluğu olarak kullanılamaz. Üstel ağırlık profili
   korunup `periyot × EMA_KESME_KATI` barda kesiliyor ve normalize
   ediliyor.

4. **Fikstür 700 → 6000 bar.** Erişim dürüstçe türetilince purge boşluğu
   1046 bara çıkıyor ve 700 barlık pencerede bölme tamamen dejenere
   oluyor (train=0). Bu bir eşik gevşetmesi değil, fikstürün gerçekçi
   kılınmasıdır: 700 barda "boru hattı geçti" demek tiyatro olurdu.

5. **`girdi_erisimi` eklendi (planda yoktu).** Plan purge'u
   `ufuk + embargo` olarak tanımlıyordu. Ölçüldü ki örneğin gerçek geriye
   erişimi gösterge zincirlerinden geliyor (`_z(atr)` → 48 + 14 = 62) ve
   4H tokeni varken 16 katına çıkıyor. Eski hali `sizinti: False`
   raporluyordu — **ölçülmüş bir fail-open**.

6. **`_bicim()` + dejenere dalın anahtar denkliği (planda yoktu).**
   Fail-closed dal, tüketiciler (`metin_rapor`) None değerlerde
   patladığı için çökme dalına dönüşmüştü.
