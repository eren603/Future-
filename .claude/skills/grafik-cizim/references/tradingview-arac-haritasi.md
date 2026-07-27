# TradingView çizim araçları → `grafik-cizim` haritası

TradingView'ın çizim paleti ile bu depodaki motorun eşlemesi. "Kapsam" sütunu
dürüsttür: **kısmi** ve **yok** olanlar gizlenmez.

## 1. Çizgiler & geometri

| TradingView | Motor aracı | Kapsam |
|---|---|---|
| Trend Line | `trend_cizgisi` | tam (`uzat`: sag/sol/iki, ok ucu, etiket) |
| Ray / Extended Line | `trend_cizgisi` (`uzat`) | tam |
| Horizontal Line | `yatay_cizgi` | tam (+ eksen fiyat rozeti) |
| Horizontal Ray | `yatay_ray` | tam |
| Vertical Line | `dikey_cizgi` | tam |
| Cross Line | `dikey_cizgi` + `yatay_cizgi` | tam (iki araçla) |
| Arrow | `ok` | tam |
| Polyline / Path | `yol` | tam |
| Rectangle | `dikdortgen` | tam |
| Ellipse / Circle | — | **yok** (`dikdortgen` + `metin` ile yaklaşılır) |
| Triangle / Polygon | `yol` (kapalı) | kısmi (dolgu yok) |
| Parallel Channel | `paralel_kanal` | tam (orta çizgi dahil) |
| Regression Trend | `regresyon_kanali` | tam (±nσ, `ileri_bar` projeksiyonu) |
| Disjoint Channel | — | **yok** |
| Flat Top/Bottom | `dikdortgen` + `trend_cizgisi` | kısmi |
| Pitchfork (Andrews) | `andrews_catali` | tam |
| Schiff / Modified Schiff Pitchfork | — | **yok** |
| Gann Box / Gann Fan | — | **yok** |

## 2. Fibonacci ailesi

| TradingView | Motor aracı | Kapsam |
|---|---|---|
| Fib Retracement | `fib_retracement` | tam — seviyeler ayarlanabilir, **altın bölge (0.618–0.786) gölgeli**, etiket "0.618 (64.972,45)", çakışma önleyici etiket dizilimi |
| Trend-Based Fib Extension | `fib_genisleme` | tam (1.272/1.414/1.618/2.0/2.618) |
| Fib Channel | `fib_kanal` | tam |
| Fib Speed Resistance Fan | `fib_yelpaze` | tam |
| Fib Time Zones | `fib_zaman` | tam (1,2,3,5,8,13,21,34,55,89) |
| Fib Circles / Spiral / Arcs | — | **yok** (nadiren kullanılır) |
| Fib Wedge | — | **yok** |

Not (metodoloji): Fibonacci **tek başına yön vermez** — `grafik-calisma`
SKILL.md'deki katman sırası geçerlidir: `bağlam(HTF) → yapı(SMC) → arz-talep
(OB/FVG) → likidite → [fib] → onay → risk`. Motor fib'i son rötuş katmanı
olarak çizer; giriş kararı `confluence.py` + `setup_dogrulama.py` iznine bağlıdır.

## 3. Pozisyon & risk araçları

| TradingView | Motor aracı | Kapsam |
|---|---|---|
| Long Position | `long_pozisyon` | tam — yeşil hedef kutusu + kırmızı stop kutusu, %, R:R etiketi, eksen rozetleri |
| Short Position | `short_pozisyon` | tam |
| Risk/Reward ratio etiketi | pozisyon aracının `r_etiketi` | tam (denetlenmiş R dışarıdan verilir) |
| Price Range / Date Range | `olcum` | tam (Δfiyat, %, bar sayısı) |
| Bars Pattern / Ghost Feed | — | **yok** |
| Projection | `regresyon_kanali.ileri_bar` + gelecek `bar` indeksi | kısmi |

## 4. Anotasyon

| TradingView | Motor aracı | Kapsam |
|---|---|---|
| Text | `metin` | tam |
| Anchored Text / Note | `metin` (`kutu: true`) | tam |
| Callout | `metin` + `ok` | kısmi (kuyruk ayrı çizilir) |
| Price Label | `fiyat_etiketi` | tam (sağ eksen rozeti) |
| Arrow Up / Down marker | `isaret` | tam |
| Flag / Emoji / Sticker | — | **yok** |
| Table / Info panel (Pine `table.new`) | `bilgi_paneli` | tam — `konum: "oto"` ile **mumların en az olduğu köşe ölçülerek** seçilir |

## 5. Grafik üstü göstergeler (çizim sayılan kısım)

| TradingView | Motor aracı | Kapsam |
|---|---|---|
| Moving Average (EMA/SMA) | `ma` | tam |
| MA Cloud / Ichimoku Kumo / Band fill | `bulut` | tam (kesişimde renk döner; seri ya da sabit fiyat kabul eder) |
| Volume (alt panel) | `paneller: [{"tip":"hacim"}]` | tam |
| RSI (alt panel) | `paneller: [{"tip":"rsi"}]` | tam |
| Herhangi bir seri (alt panel) | `paneller: [{"tip":"seri","deger":[...]}]` | tam |
| Bollinger / Keltner | `bulut` (dışarıdan seri) | kısmi (bant hesabı çağıran tarafta) |
| Log ölçek / gelecek boşluğu | `log_olcek`, `sag_bosluk_bar` | tam |

## 6. Kullanıcının gönderdiği 7 görselin eşlemesi

Her satır, o görseldeki çizimi üretmek için gereken araçlardır (görseller
"neyin gerektiğini" belirlemek için okundu; **bu bir fiyat ölçümü değildir**).

| # | Görsel | Görülen çizimler | Gereken araçlar |
|---|---|---|---|
| 1 | THY 4sa (BIST) | renkli yatay bantlar (pembe/mavi/sarı/yeşil), yatay ışınlar, noktalı ve düz trend çizgileri, kalın ok, eksen fiyat rozetleri (330,75 / 311,00 / 295,25), alt osilatör paneli | `dikdortgen`, `yatay_ray`, `trend_cizgisi`, `ok`, `fiyat_etiketi`, `paneller:[{tip:"seri"\|"rsi"}]` |
| 2 | ETHUSDT 1sa | düşen paralel kanal + kesik orta çizgi, **long pozisyon aracı** (hedef +%66,74 / stop −%34,21 kutuları), iki hareketli ortalama, kesik trend çizgileri, geleceğe projeksiyon | `paralel_kanal`, `long_pozisyon`, `ma`, `trend_cizgisi`, `sag_bosluk_bar` + gelecek `bar` |
| 3 | Kanal + MA (küçük) | mavi/kırmızı ikiye bölünmüş kanal gövdesi, MA | `paralel_kanal` (+`dikdortgen`), `ma` |
| 4 | DOGEUSDT 1sa | **Fibonacci düzeltme etiketli seviyeler** (0.786 (0,25802) …), düşen kanal, long pozisyon kutusu, yatay çizgiler, eksen rozetleri | `fib_retracement`, `paralel_kanal`, `long_pozisyon`, `yatay_cizgi`, `fiyat_etiketi` |
| 5 | NIBAS 1sa | etiketli DESTEK/DİRENÇ bant dikdörtgenleri, yeşil trend çizgisi, beyaz MA, **sağ üstte bilgi tablosu** | `dikdortgen` (+`etiket`), `trend_cizgisi`, `ma`, `bilgi_paneli` |
| 6 | BIST 100 4sa | sarı paralel kanal + kesik orta çizgi, gri yatay bölge dikdörtgenleri (13.700-800 …), kırmızı/yeşil yatay çizgi + rozet, daire işareti | `paralel_kanal`, `dikdortgen`, `yatay_cizgi`, `fiyat_etiketi`, `isaret` (daire yerine üçgen/metin — elips **yok**) |
| 7 | Futures scalp (mobil) | kırmızı/yeşil arz-talep bantları, **iki MA arası mor bulut**, çok sayıda MA, kesik basamaklı stop çizgisi, "1 Buy STP / 1 Buy LMT" emir seviyesi etiketleri, çok renkli eksen rozetleri | `dikdortgen`, `bulut`, `ma`, `yol`, `yatay_cizgi`(+`etiket`), `fiyat_etiketi` |

**Sonuç:** 7 görseldeki çizimlerin tamamı — elips (6) ve emoji/sticker hariç —
mevcut 24 araçla üretilebilir.

## 7. Neden SVG (matplotlib değil)

- Bu ortamda `matplotlib` **kurulu değil** (`grafik-calisma/SKILL.md`'nin
  "C) Grafik üretme" maddesi bu yüzden çalışmıyordu); SVG için ek paket gerekmez.
- Vektörel: fiyat etiketleri her ölçekte keskin, dosya küçük, diff'lenebilir.
- İstenirse `cairosvg` varsa PNG de üretilir (`job.png: true`); yoksa
  rapora "VERİ YOK — png üretilemedi" yazılır, SVG yine geçerlidir.

## 8. Dış kaynak notu

Depo dışı bir kütüphaneye bağımlılık **bilinçli olarak alınmadı**: TradingView
Lightweight Charts (JS), mplfinance ve plotly benzer işi görür ama her biri kurulum
(ve JS için tarayıcı) ister; bu depo çevrimdışı, determinist ve sıfır-bağımlılık
disiplininde çalışır. Aynı çizim sözlüğü (job şeması) ileride başka bir görselleyiciye
bağlanabilir — araç adları TradingView terminolojisiyle birebir eşlenmiştir.
