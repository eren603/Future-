---
name: grafik-cizim
description: >-
  Grafik ÜZERİNE TradingView'daki gibi çizim yapma becerisi. Bir soru grafiğe
  çizim ekleme, Fibonacci çizme (retracement/genişleme/kanal/yelpaze/zaman
  bölgeleri), trend çizgisi, paralel kanal, regresyon kanalı, Andrews çatalı,
  destek/direnç bölgesi (dikdörtgen), order block / FVG / likidite işaretleme,
  long/short pozisyon aracı (giriş-stop-hedef R:R kutusu), ölçüm aracı, ok/metin/
  etiket, fiyat rozeti, bilgi paneli (tablo), EMA/SMA çizgisi, hacim/RSI alt
  paneli, "grafiği çiz", "işaretle", "çizimli grafik ver", "TradingView gibi
  göster" ile ilgili olduğunda OTOMATİK devreye girer — slash komutu gerekmez.
  Ayrıca kullanıcı bir grafik ekran görüntüsü gönderip "aynısını çiz / üzerine
  çiz" dediğinde de tetiklenir. Çalışan motorlar: scripts/cizim.py (job →
  SVG mum grafiği + çizimler), scripts/araclar.py (24 TradingView aracı),
  scripts/otomatik_cizim.py (smc_tespit'in ÖLÇTÜĞÜ yapıdan otomatik çizim
  katmanı), scripts/self_test.py. Sıfır bağımlılık (SVG; matplotlib GEREKMEZ).
  Tetikleyici kelimeler (TR/EN): çiz, çizim, işaretle, fibonacci, fib, retracement,
  golden zone, trend çizgisi, kanal, channel, pitchfork, dikdörtgen, bölge, zone,
  order block, FVG, likidite, long pozisyon, short position, risk ödül kutusu,
  ölçüm, measure, etiket, label, anotasyon, annotate, chart drawing, plot,
  overlay, TradingView, ekran görüntüsü gibi çiz.
---

# Grafik Çizim — TradingView araç seti (SVG, sıfır bağımlılık)

`grafik-calisma` grafiği **okur/ölçer**; bu beceri onu **çizer**. Analiz motoru
(smc_tespit → confluence → setup_dogrulama) ne ölçtüyse bu motor onu görselleştirir.
Çizilen her sayı ya kullanıcıdan/üst motordan gelir ya da ölçülen yapıdan — **bu
motor fiyat uydurmaz**, ölçemediğini çizmez ve `uyarilar` alanına yazar.

Çıktı **SVG**'dir: matplotlib kurulu olmadığında da çalışır (bu ortamda kurulu
değil), vektörel olduğu için etiketler hiçbir ölçekte bozulmaz. `SendUserFile`
ile doğrudan gösterilebilir.

## Koşum

```bash
python3 .claude/skills/grafik-cizim/scripts/cizim.py --job is.json   # çiz
python3 .claude/skills/grafik-cizim/scripts/cizim.py --araclar       # araç listesi
python3 .claude/skills/grafik-cizim/scripts/self_test.py             # öz-test (46 kontrol)
```

## İş dosyası (job)

```json
{
  "veri": {"kline": "engine/girdi/h4.json"},
  "son_bar": 160,
  "baslik": "BTCUSDT · 4H · Binance",
  "alt_baslik": "SMC + Fibonacci — ölçülen yapıdan",
  "tema": "koyu",
  "genislik": 1600, "yukseklik": 900,
  "log_olcek": false,
  "sag_bosluk_bar": 30,
  "paneller": [{"tip": "hacim", "yukseklik": 0.13}, {"tip": "rsi", "period": 14}],
  "otomatik": {"ma": [{"tip": "ema", "period": 50}], "regresyon": {"bar": 120}},
  "cizimler": [{"arac": "fib_retracement", "p1": {"bar": 84, "fiyat": 61520.0},
                "p2": {"bar": 120, "fiyat": 65780.0}}],
  "cikti": "cikti/btc_4h.svg"
}
```

- `veri`: `{"kline": "<Binance kline JSON/CSV>"}` (deponun kendi
  `engine/karar_motoru.parse_klines` parser'ı kullanılır — ikinci parser yok)
  **veya** `{"mumlar": [{open,high,low,close,volume,time}, …]}`.
- **Nokta gösterimi:** `{"bar": i, "fiyat": p}` — `bar` negatifse **sondan**
  (-1 = son mum), `n`'den büyükse **geleceğe projeksiyon** (TradingView sağ
  boşluğu), `{"zaman": <ms>}` da kabul edilir.
- Çıktı: SVG dosyası + stdout'a JSON rapor (`cizilen_seviyeler`, `araclar`,
  `uyarilar`, `fiyat_araligi`). `cizilen_seviyeler` `iddia_denetle.py` ile
  çapraz kontrol edilebilir.

## Araçlar (24) — TradingView karşılıkları

| Araç | TradingView | Zorunlu alanlar |
|---|---|---|
| `trend_cizgisi` | Trend Line / Ray | `p1`,`p2` (+`uzat`: sag/sol/iki, `ok`) |
| `yatay_cizgi` | Horizontal Line | `fiyat` (+`bar_baslangic`,`bar_bitis`) |
| `yatay_ray` | Horizontal Ray | `fiyat`,`bar` |
| `dikey_cizgi` | Vertical Line | `bar` |
| `dikdortgen` | Rectangle / Zone | `fiyat1`,`fiyat2` (+`bar_baslangic`) |
| `paralel_kanal` | Parallel Channel | `p1`,`p2`,`p3` |
| `regresyon_kanali` | Regression Trend | `bar_baslangic`,`bar_bitis` (+`sapma`,`ileri_bar`) |
| `andrews_catali` | Pitchfork | `p1`,`p2`,`p3` |
| `fib_retracement` | Fib Retracement | `p1`,`p2` (+`seviyeler`,`altin_bolge`,`tam_genislik`) |
| `fib_genisleme` | Trend-Based Fib Extension | `p1`,`p2`,`p3` |
| `fib_kanal` | Fib Channel | `p1`,`p2`,`p3` |
| `fib_yelpaze` | Fib Fan (Speed Fan) | `p1`,`p2` |
| `fib_zaman` | Fib Time Zones | `bar_baslangic`,`bar_bitis` |
| `long_pozisyon` | Long Position | `giris`,`stop`,`hedef` |
| `short_pozisyon` | Short Position | `giris`,`stop`,`hedef` |
| `olcum` | Measure / Price Range | `p1`,`p2` |
| `ok` | Arrow | `p1`,`p2` |
| `yol` | Path / Polyline | `noktalar[]` |
| `metin` | Text / Callout | `p1`,`metin` (+`kutu`) |
| `isaret` | Arrow Marker Up/Down | `p1`,`yon` |
| `fiyat_etiketi` | Price Label (eksen rozeti) | `fiyat` |
| `bilgi_paneli` | Table / Info Panel | `satirlar[]` (+`konum`: `oto`) |
| `ma` (`ema`/`sma`) | Moving Average | `period` (+`tip`) |
| `bulut` | MA Cloud / Kumo / Band fill | `a`,`b` (MA tanımı, seri ya da sabit fiyat) |

Ortak alanlar: `renk` (tema anahtarı ya da hex), `kalinlik`, `kesik` ("5 3"),
`dolgu_saydam`, `etiket`, `katman` (z-sırası). İngilizce adlar da kabul edilir
(`fibonacci`, `rectangle`, `long_position`, `pitchfork`, `measure`, …) —
`araclar.TAKMA_AD`.

**Katman düzeni** TradingView'daki gibidir: bölge/kanal mumların **arkasına**,
çizgi/etiket/panel **önüne** çizilir. `bilgi_paneli` varsayılan `konum: "oto"`
ile mumların **en az olduğu köşeyi ölçerek** yerleşir (üst üste binme yok).

## Otomatik katman (`otomatik`)

`grafik-calisma/scripts/smc_tespit.py`'nin **ölçtüğü** yapıyı çizime çevirir —
ikinci bir tespit mantığı yazılmaz:

| Anahtar | Ne çizer |
|---|---|
| `ob` | order block dikdörtgenleri (talep yeşil / arz kırmızı) |
| `fvg` | açık FVG bantları |
| `likidite` | eşit tepe/dip likidite rayları (`×adet` etiketli) |
| `yapi` | BOS / CHoCH kırılım çizgileri + yön işareti |
| `fib` | son impuls bacağından Fibonacci + altın bölge (0.618–0.786) |
| `trend_cizgisi` | son iki teyitli swing'den trend çizgisi |
| `swing_etiket` | HH / HL / LH / LL etiketleri |
| `regresyon` | `{"bar": 120, "sapma": 2.0, "ileri_bar": 30}` |
| `ma` | `[{"tip":"ema","period":50,"renk":"#ff9800"}]` |
| `panel` | ölçülen değerlerle bilgi paneli (trend, ADX/rejim, ATR, ATR%, sayımlar) |
| `emir` | `{"yon","giris","stop","hedef","r"}` ya da `emir_plani.py` çıktı dosyası → pozisyon kutusu |

Her biri varsayılan **açık**; `false` ile kapatılır. Ölçülemeyen çizim atlanır
ve `uyarilar`a "VERİ YOK" gerekçesiyle yazılır — **uydurulmaz**.

## Doğruluk sözleşmesi (bu motora özel)

1. **Uydurma seviye yok.** `otomatik` katmanının ürettiği her fiyat, öz-testin
   GROUNDING testiyle ölçülen kümede (smc_tespit çıktısı ∪ ham OHLC) olduğu
   kanıtlanır; kaynaksız fiyat testi düşürür.
2. **Şişirilmiş R yok.** Pozisyon aracı R'yi `|hedef−giriş| / |giriş−stop|`
   ham mesafeden hesaplar. Bir R **karar** olarak sunulacaksa önce
   `karar-kurulu/scripts/rr_denetim.py`'den geçirilir; etiket `r_etiketi` ile
   denetlenmiş değerden verilir.
3. **Grafik karar değildir.** Çıktı karar-desteğidir; yön/işlem hükmü
   `karar-kurulu` / `piramit-sistem` sentezinden gelir.
4. Görsel bir **ölçüm değildir**: kullanıcının ekran görüntüsünden okunan
   seviyelerin güveni `gorsel_tavan` = **0.50** ile tavanlıdır ve `smc_tespit`
   yapısıyla uyuşmazsa çürütülür ("GÖRSEL-MEKANİK ÇELİŞKİSİ"). Mekanik ayrıntı:
   `piramit-sistem/SKILL.md` §"Zorunlu girdiler".

## Ne zaman hangi mod

- Kullanıcı "çiz / işaretle / göster" derse → `otomatik` katman + gerekirse elle çizim.
- Karar analizinden sonra seviyeleri görselleştirmek gerekiyorsa → `otomatik.emir`
  ile `emir_plani.py` çıktısını ver (giriş/stop/hedef kutusu birebir motordan).
- Kullanıcı bir TradingView ekran görüntüsü gönderip "aynısını kur" derse →
  `references/tradingview-arac-haritasi.md` eşlemesiyle araçları seç.
