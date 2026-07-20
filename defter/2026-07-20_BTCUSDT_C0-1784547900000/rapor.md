# C0-VETO v2.7-PRAGMATİK — BTCUSDT Koşu Raporu

Koşu kimliği: `2026-07-20_BTCUSDT_C0-1784547900000` · Mod: **PAPER / NO-LIVE-TRADE**
Sözleşme: `C0-VETO-v2.7-PRAGMATIK-BTCUSDT` (dosya SHA-256 `8d590434d12c…`)

---

## Zorunlu satırlar

```
RUN: PRAGMATIK / RETROSPECTIVE_NONBLIND / TAMAMLANDI (was_live_forecast=false)
VERİ: TIER-1 15M=60 satır (59 kapalı) + 4H=22 satır (21 kapalı) · TIER-2 6 görüntü + 1 video (video işlenemedi) · TIER-3 0 — provenance=USER_SUPPLIED_UNRECEIPTED
YÖN: LONG — CONFLUENCE B (M: UP/STRONG, Y: UP)
GİRİŞ: MARKET 15M GÖVDE kapanışı > 65048.30 (C0 high) teyidiyle kapanış fiyatından | PUSU açık boğa FVG 64376.60–64807.10 içinde limit, tercih CE 64591.85
STOP: 64316.00 altı (displacement dibi); iptal = 15M gövde kapanışı < 64316.00 · derin yapısal alternatif 64137.00 (son fraktal dip)
HEDEF: T1 65084.60 (DOL1, BSL), T2 65187.72 (plan_basis=ATR_FALLBACK; yapısal DOL2 veri içinde YOK) — R: market 0.05R/0.19R (YETERSİZ → market planı işlem değeri taşımaz) / pusu-CE 1.79R/2.16R
BAĞLAM: likidite_bandı=hedef_yolunda (T1 hemen üstü 65.1–65.2k yoğun band) · funding_işareti=+ (0.0085%, aşırı değil) · oi_eğimi=artan · liq_baskın_taraf=okunamadı (iki yönlü spikeler)
UYARI: bayatlık — C0 12:00 UTC'de kapandı, koşu sonrası; provenance makbuzsuz (BN-02 yok, SHA'sız kullanıcı yapıştırması); kalibrasyon artefaktı yok → OLASILIK/EDGE İDDİASI YOK, çıktı nitel araştırma sinyalidir; video piksel→sayı yapılmadı; adaptif eşik formülü VARSAYIM (0.10×ATR14(4H) — v2.6 tam formülü bu pencerede yok); PUSU bölgesi sweep fitili değil displacement-FVG'dir (plan_basis notu)
```

---

## 0. ENVANTER (SHA-256)

| Girdi | SHA-256 (ilk 16) |
|---|---|
| C0VETO v2.7 komut dosyası | `8d590434d12cfb71` |
| 15M kline yapıştırması (60 satır) → `klines_15m.json` | dosya deposunda |
| 4H kline yapıştırması (22 satır) → `klines_4h.json` | dosya deposunda |
| SS 150114 (15M spot likidite ısı haritası) | `8b530198ce6e9bad` |
| SS 150122 (4S spot ısı haritası) | `a091d71f72c0a1dc` |
| SS 150130 (4S perp ısı haritası) | `63c23de4348d2833` |
| SS 150147 (15M perp ısı haritası) | `5187fc9fae89266a` |
| SS 150157 (4S perp panel: funding/liq/OI) | `099bb77980b6570b` |
| SS 150208 (15M perp panel: funding/liq/OI) | `f4bf499e337e790b` |
| Video 150217 (işlenemedi — betimsel analiz yapılmadı) | `c095e98d7c5b0e4a` |
| Beceri zip'i `Chatgpt_analiz_becerisi.zip` | GELMEDİ → `scripts_available=false`, akış manuel |

## 1. PROFİL (Beceri-1) — PASS

- 15M: 60 satır, grid 900.000 ms kesintisiz, duplicate yok, OHLC-sanity ihlali yok.
- 4H: 22 satır, grid 14.400.000 ms kesintisiz, temiz.
- Açık bar tespiti: gözlemci zamanı ≈ 12:02 UTC (ekran saatleri 15:01–15:02 UTC+3).
  15M `1784548800000` (12:00) ve 4H `1784548800000` (12:00–16:00) AÇIK → DIŞLANDI.
- **İKİNCİ-YOL 1:** 15M→4H agregasyon mutabakatı, tam kapsanan üç 4H barında
  (00:00, 04:00, 08:00 UTC) O/H/L/C/hacim/işlem-sayısı **birebir eşleşti (3/3)**.
- **İKİNCİ-YOL 2:** ATR0, MA5, MA20 Decimal ve float64 ile bağımsız yeniden hesaplandı, mutabık.
- Çapraz kontrol (TIER-2): Coinglass panelindeki 24S High 65084.6 / Low 63736.1,
  TIER-1 verisindeki maks. yüksek / min. düşük ile aynı.

## 2. C0 KİMLİĞİ

C0 = son KAPALI 15M bar `1784547900000` = **2026-07-20 11:45:00–11:59:59.999 UTC**
O 64807.20 · H 65048.30 · L 64807.10 · C 64970.80 · V 3520.98 · close_location 0.68
Gözlemci C0 sonrasını (12:00 açık barının kısmi verisini) görmüştür → `was_live_forecast=false`.

## 3. MEKANİK (Beceri-3) — CALCULATED

| Büyüklük | Değer | Not |
|---|---|---|
| ATR0 (14×15M TR, C0 dahil) | **180.76** | |
| 4H MA5 / MA20 | 64638.60 / 64225.93 | 21 kapalı 4H bar |
| MA5−MA20 | **+412.67** | eşik +48.92 (VARSAYIM: 0.10×ATR14(4H)=489.20) → **trend_dir=UP** (fark eşiğin 8.4 katı; 0.25× eşik varsayımında da UP) |
| 40-bar prh / prl (C0 hariç) | 64940.00 / 63736.10 | |
| Tetik | **BREAKOUT_UP** — C0 kapanışı 64970.80 > prh 64940.00 | trigger_dir=UP |
| **yön_M** | **UP · grade STRONG** (trend+tetik aynı yön) | |
| ATR fallback zarfı | 64753.88 – 65187.72 (C0 kapanışı ±1.2×ATR0) | |

## 4. YAPISAL / SMC (Beceri-2) — CALCULATED

- Swing'ler fraktal k=2, yalnız kapalı bar. Son teyitli 15M swing high 64393.20 (09:45),
  son teyitli swing low 64137.00 (10:00).
- **SSL süpürme** 06:30 UTC: L 63736.10 prior yapının altı; aynı-bar geri alım ZAYIF
  (close_location 0.15, kapanış süpürülen 64046 seviyesinin altında) → tek başına sinyal değil.
- 06:30–11:15 birikim aralığı (63858–64393); 08:30'da alt sınır testi güçlü redle alındı
  (close_loc 0.90).
- **11:30 UTC displacement**: gövde +484.6 (≈2.7×ATR0), hacim 7970 (koşunun en yükseği),
  **BOS UP** (kapanış > 64393.20) ve **açık boğa FVG 64376.60–64807.10** (CE 64591.85) bıraktı.
  C0 devamla 64940 kırdı, 65011.00 BSL havuzunu fitille aldı.
- **AMD**: birikim ✓ · SSL alımı ✓ (63736.10) · karşı yön displacement ✓ → AMD-boğa etiketi
  VERİLİR (süpürme barının kendi geri alımı zayıftı; geri alım gecikmeli geldi — nüans).
- **yön_Y = UP.**
- Havuzlar: veri içinde süpürülmemiş TEK BSL = **65084.60** (00:15 UTC tepesi = DOL1 = T1).
  Yapısal DOL2 **VERİ YOK** → T2 = ATR fallback 65187.72. (Ekran görüntüsündeki 65.5–65.6k
  bölgesi TIER-2'dir; kural gereği sayısal hedefe ÇEVRİLMEZ.)
  SSL tarafı: 64137.00 → 63858.10 → 63736.10.

## 5. BAĞLAM (TIER-2 bayrakları — yalnız grade etkiler)

- `likidite_bandı = hedef_yolunda`: 15M/4S ısı haritalarında 65.1–65.2k (ve 4S'te 65.5k)
  üstte yoğun band — T1'in hemen üstü satış duvarı; kâr alma bölgesi olarak da okunur.
- `funding_işareti = +` (0.0085%; baz 0.01'in altında, AŞIRI DEĞİL).
- `oi_eğimi = artan` (15M panelde son bölümde OI yükselişi, fiyatla uyumlu).
- `liq_baskın_taraf = okunamadı` (son ralli mumunda hem yeşil hem kırmızı likidasyon spikei).

## 6. CONFLUENCE

yön_M=UP ∧ yön_Y=UP → **YÖN = LONG**. Bağlam uyarısı ≥1 (hedef yolunda likidite bandı)
→ **GRADE = B**.

## 7. PLAN (PAPER — emir değildir)

| Öğe | Seviye | R (T1 / T2) |
|---|---|---|
| MARKET (teyit: 15M gövde kapanışı > 65048.30) | ~65048.30+ | **0.05R / 0.19R → YETERSİZ** |
| PUSU limit — FVG üst sınırı | 64807.10 | 0.57R / 0.78R |
| **PUSU limit — CE (tercih)** | **64591.85** | **1.79R / 2.16R** |
| STOP | 64316.00 altı; iptal = 15M gövde kapanışı < 64316.00 (derin alt.: 64137.00) | — |
| T1 = DOL1 | 65084.60 | |
| T2 | 65187.72 `plan_basis=ATR_FALLBACK` | |

Dürüst okuma: yapı yukarı ama fiyat hedefe ÇOK yakın; anlamlı asimetri yalnız FVG-CE'ye
geri çekilme pususunda var. Market kovalamak bu haliyle negatif beklentili konum.
Derin stop (64137) kullanılırsa pusu-CE R'si T1 için 1.08'e düşer.

## 8. ÇİZİMLER

- `grafik_mekanik_15M.png` — SHA-256 `913e7bc4cf22da574bc883fac591dd008c17d086db9a856cf08fcdc33cef0fe1`
- `grafik_smc_haritasi.png` — SHA-256 `8c1c0033b33a53e45b5ee22bb518ae34ee4040205e6c4bb72cb69bf1dcda295f`

## 9. ROLLOVER

Sonraki C0 adayı: `1784548800000` (12:00–12:15 UTC) barının KAPALI hali yeniden
yapıştırıldığında. Bu kayıt append-only'dir; değiştirilemez, yeni koşu yeni klasör açar.

*Bu çıktı kalibre edilmemiş nitel araştırma sinyalidir; yatırım tavsiyesi değildir.*
