---
name: grafik-cizim
description: >-
  Ham OHLCV verisinden TradingView tarzı çizimli SVG mum grafikleri üret;
  trend, kanal, Fibonacci, pozisyon, gösterge ve açıklama katmanlarını kaynak
  ve hesap kanıtıyla göster. Kullanıcı mevcut grafik ekran görüntüsüne çizim
  istediğinde orijinal görseli koruyan kalibre edilmiş Workbench yoluna yönlendir.
---

# Grafik Çizim

`grafik-calisma` ölçüm yapar; bu beceri ölçülen veriyi ve verilen çizimleri
sunar. Grafik, kararın koşullarını gösterebilir; tahmin doğruluğu veya işlem
başarısı garantisi vermez. Gözlenen, hesaplanan, görselden tahmin edilen ve
geleceğe yansıtılan değerleri ayrı etiketle.

## Girdiye göre yol seç

| Girdi ve istek | Yol |
|---|---|
| Ham OHLCV ile yeni mum grafiği | `scripts/cizim.py`: ortak mum normalizasyonu → hesap → yeni SVG tuvali. |
| Orijinal ekran görüntüsünün üzerine çizim | Chart Calculation Workbench: eksen kalibrasyonu → deterministik anotasyon → görsel ve manifest denetimi. |
| Görsele benzer yeni grafik | Gerçek ham veriyi iste/kullan; bunun yeniden oluşturulmuş tuval olduğunu belirt. |

Ekran görüntüsünden okunamayan OHLC, hacim, gösterge geçmişi veya zaman damgası
üretme. Ham veri yoksa otomatik SMC/EMA/RSI motorunu sahte mumlarla çalıştırma.
Workbench mevcut değilse yeterli kalibrasyon kanıtını koruyan eşdeğer araç kullan;
bunu sağlayamıyorsan yalnız nitel açıklama veya açıkça yaklaşık işaretleme sun.

## Ham veri ve ortak C0

- `veri.kline`: JSON/CSV dosyası; Binance dizileri veya OHLC nesneleri.
  `veri.mumlar`: doğrudan OHLC nesne listesi. Normalizasyon
  `grafik-calisma/scripts/candle_contract.py` sözleşmesini paylaşır.
- `open/high/low/close` sonlu ve OHLC aralığı tutarlı olmalı. Log ölçekte tüm
  fiyatlar pozitif olmalı. Kaynak sırasını sessizce düzeltme, tekrarları silme
  veya eksik mumu doldurma. Eksik/çelişkili veri hatasını raporla.
- `c0`, `cutoff`, `as_of` aynı kesim zamanının takma adlarıdır. Birden fazlası
  varsa normalize edilmiş değerleri tam aynı zaman damgası olmalı; alternatif
  kesim alanı icat etme. Çoklu zaman dilimleri ve son karar bu ortak kesimi kullanır.
- Mumun uygunluğu açılışa göre değil **kapanış zamanına** göre belirlenir:
  `close_time <= C0`; `closed:false` mumlar dışlanır. Kaynak `close_time`
  veremiyorsa `open_time`/`time` ile `timeframe` veya `interval_seconds` gerekir.
  Sabit aralıkta türetilen kapanış `open_time + interval_ms - 1` konvansiyonudur;
  değişken seans/takvim için gerçek kaynak kapanışını kullan.
- Zamanlar epoch saniye/ms/us/ns veya timezone içeren ISO olabilir; normalize
  çıktı UTC milisaniyedir. Grafik `timezone:"UTC"` çizer. `price_unit` ve
  mümkünse `volume_unit`, piyasa/seans ve düzeltilmiş fiyat temelini belirt.
- Kesim/kapanış kanıtı yoksa `time_unverified` ve TASLAK gösterilir. Düzensiz
  aralıklar uyarı üretir; eşit bar aralıklı x eksenini gerçek geçen süre sanma.
- `son_bar` yalnız görünüm sınırıdır. MA/RSI, otomatik yapı ve seçilmiş regresyon
  aralığı C0'a uygun tam geçmişte hesaplanır, sonra görünür alana taşınır.
  Gösterge için yeterli ısınma geçmişi yoksa çizilemeyen sonucu bildir.

## Koşum ve iş dosyası

Manuel SVG çizim/normalizasyon yolu Python standart kütüphanesiyle çalışır.
Otomatik tespit `pandas`/`numpy` kullanır. PNG dönüşümü isteğe bağlı `cairosvg`
gerektirir; eksik bağımlılığı ve üretilemeyen katmanı rapordan kontrol et.

```bash
python3 .claude/skills/grafik-cizim/scripts/cizim.py --job is.json
python3 .claude/skills/grafik-cizim/scripts/cizim.py --araclar
python3 .claude/skills/grafik-cizim/scripts/self_test.py
```

Aşağıdaki dosya biçim örneğidir; kaynağı ve C0'ı gerçek çalışmaya göre belirle:

```json
{
  "veri": {"kline": "engine/girdi/h4.json"},
  "c0": "2026-01-01T00:00:00Z", "timeframe": "4h",
  "timezone": "UTC", "price_unit": "USDT", "volume_unit": "BTC",
  "son_bar": 160, "baslik": "BTCUSDT · 4H · kaynak adı",
  "tema": "koyu", "genislik": 1600, "yukseklik": 900,
  "log_olcek": false, "sag_bosluk_bar": 30,
  "paneller": [{"tip": "hacim"}, {"tip": "rsi", "period": 14}],
  "otomatik": {"ma": [{"tip": "ema", "period": 50}]},
  "cizimler": [], "cikti": "cikti/btc_4h.svg"
}
```

Noktalar `{"bar": i, "fiyat": p}` biçimindedir. Varsayılan bar alanı görünür
mum dilimidir; `-1` son mumu, görünüm dışındaki büyük indeks projeksiyonu belirtir.
Tam geçmişe ait elle çizimler için çizim nesnesine `bar_space:"history"` ekle.
`{"zaman": zaman_damgasi, "fiyat": p}` kesirli bar konumuna çevrilir; zaman
verisi yoksa son muma sessizce yapıştırılmaz.

Araçlar ve sınırları için [TradingView haritasını](references/tradingview-arac-haritasi.md)
oku. Ortak görünüm alanları `renk`, `kalinlik`, `kesik`, `dolgu_saydam`,
`etiket`, `katman`dır. Desteklenen adlar/takma adlar için `--araclar` kullan.

`otomatik` etkinse OB/FVG/likidite/yapı/fib/trend/swing etiketleri ve bilgi
paneli kendi seçenekleriyle açılıp kapatılır; tespit ayarları `params` içindedir.
`regresyon` ve `ma` ayrıca istenir; `emir` verilen planı kullanır. Bunların
hepsi varsayılan açık değildir. Üretilemeyen katmanı `uyarilar` ve
`atlanan_cizimler` üzerinden bildir; istenen sayıyı çizilen sayı diye sunma.

## Karar ve pozisyon kanıtı

`final_decision` üst kararın durumunu taşır. Pozisyon geometrisi long için
`stop < giris < hedef`, short için `hedef < giris < stop` olmalıdır.

| Durum | Sunum |
|---|---|
| `confirmed` | Yön, kapanmış veri ve aynı C0 doğrulanmış koşul; başarı olasılığı değildir. |
| `conditional` | Henüz gerçekleşmesi gereken koşula bağlı plan; teyit edilmiş gibi gösterme. |
| `draft` | Taslak veya zaman/kaynak kanıtı eksik plan. |
| `blocked` | İşlem kutusunu çizme; engelleme gerekçesini raporla. |

`confirmed` için `final_decision.direction`, `status` ve ortak C0 alanı gerekir.
`EMIR YOK`/`blocked`, yön çelişkisi veya geçersiz geometri serbest etiketle
geçersiz kılınamaz. Görselden okunan fiyatları tek başına confirmed emir kanıtı sayma.

- **rawR / R ham:** `abs(hedef-giris) / abs(giris-stop)`; maliyet içermez.
- **netR / R net:** `(ödül-kazanılan işlem maliyeti)/(risk+kaybedilen işlem maliyeti)`;
  komisyon/kayma varsayımları aynı fiyat biriminde açıkça verilmelidir.
- **ATR senaryosu:** varsayımsal ATR stop tabanıyla yeniden hesap; çizilen stopu
  değiştirmez, netR değildir ve piyasa başarısını ölçmez.

Denetlenmiş R için `rr_audit`, normalize veri hash'i, aynı C0, yön ve
entry/stop/target ile bağlanır; yöntem ve sayı yeniden hesaplanır. Serbest
`r_etiketi` doğrulama sayılmaz. Ayrıntı ve alanlar araç haritasındadır.

## Görseli ve kanıtı teslim et

SVG ile `<cikti>.manifest.json` üretilir. Manifest kaynak/normalize/çıktı
SHA-256 değerlerini, zaman sözleşmesini, satır sayılarını, görünüm aralığını,
birimleri, hesap konvansiyonlarını ve pozisyon kanıtını içerir. Kaynak sağlayıcı,
alınma zamanı, piyasa/seans ve fiyat temeli biliniyorsa ayrıca kaydet; hash bunları
kendiliğinden doğrulamaz. Görsel anotasyonunda kalibrasyon manifestini de sakla.

Çıktıyı açıp uç değerleri, ölçekleri, saat/birim etiketlerini, görünmeyen serileri,
çizim kırpılmasını ve etiket/panel çakışmalarını kontrol et. Çizimler plot alanında
kırpılır; eksen rozetleri ayrıca yerleştirilir. Otomatik yerleşim çakışmasızlık
vaadi değildir. Kaynağı, hesaplanan/tahmini ayrımını ve kalan uyarıları kısa notla ver.

## Son kararın çizime bağlanması

`confirmed` son karar ayrıca `input_sha256` (bu motorun normalize mum hash'i) ve
`geometry: {entry, stop, target}` taşır. Bunlardan biri çizilen veri/seviyeyle
çelişirse pozisyon çizilmez. `case_sha256` verilirse job alanıyla aynı olmalıdır.
Giriş bölgesi için `geometry.entry_zone`, açık `entry_policy` (midpoint/lower/upper/
reference_price), `stop`, `targets` ve `target_index` kullanılır; referans fiyat
politikasında `reference_price` zorunludur. Koşullu kartların verdiği kaynak,
kesim ve geometri de kontrol edilir; koşullu durum teyitli sayılmaz.

`png: true`, önce cairosvg kullanır; paket yoksa PATH'teki Inkscape'i argüman
listesiyle ve 30 saniye sınırıyla çalıştırır. XML/SVG, çıkış kodu, yeni çıktı
dosyası ve PNG imzası kontrol edilir. Dönüşüm hatası JSON uyarısında kalır.
