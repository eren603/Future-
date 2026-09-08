# TradingView araçları ve uygulanabilen çizim yolları

Bu harita araç seçimi içindir; TradingView ile tüm davranışların, varsayılanların
ve piksel yerleşiminin eşdeğer olduğu iddiası değildir. Desteklenen gerçek araç
adları ve takma adlar `cizim.py --araclar` çıktısındadır.

## 1. Yeni tuval veya orijinal görsel

| İstek | Uygulama | Kanıt sınırı |
|---|---|---|
| Ham veriden yeni mum grafiği | `cizim.py` normalizasyon ve hesaplarından sonra SVG tuvali | Kaynak mumları, birimleri, zaman kesimini ve hesap konvansiyonlarını doğrula. |
| Yüklenen görselin üzerine çizim | Chart Calculation Workbench kalibrasyonu ve deterministik anotasyonu | Orijinal görsel ve kalibrasyon manifesti korunur; pikselden alınan değerler yaklaşık ölçümdür. |
| Ekran görüntüsüne benzeyen yeni grafik | Aynı sembol/zaman dilimine ait gerçek ham veriyle yeni tuval | Yeniden oluşturulduğunu belirt; ekran görüntüsünden gizli mum geçmişi çıkarma. |

Orijinal görsel üzerine çizim için:

1. Kaynak dosyayı orijinal çözünürlükte incele. Dosya hash'ini, ölçülerini,
   kırpma/ölçekleme işlemlerini ve ham OHLC bulunup bulunmadığını kaydet.
2. Fiyat paneli sınırlarını, x/y eksen yönlerini, doğrusal/log ölçeği, zaman
   dilimini, birimleri ve okunabilir tick konumlarını belirle. Alt panelleri ayrı
   eksen sistemleri olarak ele al.
3. Her kullanılan eksende en az iki güvenilir piksel–veri ankrajı gerekir;
   mümkünse en az üç kullanarak kalibrasyon artıklarını ölç. Eşit bar aralığını
   kesintisiz takvim zamanı sanma; seans boşluklarını ve görünür C0'ı koru.
4. Workbench `scripts/chart_geometry.py` ile dönüşümü hesapla. Doğrusal/log
   fiyat dönüşümünü ve zaman eşlemesini kontrol et; piksel hassasiyetinin izin
   vermediği ondalıkları kesin fiyat gibi sunma.
5. Yalnız gerekli noktaları sayısallaştır; kaynak pikseli, dönüştürülmüş değeri,
   birimi ve belirsizliği birlikte tut. Kalibrasyon yapılamayan eksene kesin
   fiyat/zaman geometrisi çizme.
6. Workbench `scripts/annotate_chart.py` ile çizgi/bölge/etiketleri uygula;
   kaynağın üzerine yeni, uydurulmuş mumlar üretme. Görseli ve manifesti açıp
   ankrajları, örtülen mumları ve etiket taşmalarını doğrula.

Workbench bu depodaki SVG motorundan ayrı bir beceridir; mevcut kurulumundaki
hesap/kalibrasyon sözleşmesini oku ve o kurulumun yollarını kullan. Bilinmeyen
nonlineer ölçek, yetersiz ankraj veya okunamayan zamanlar varsa nitel/ yaklaşık
sonuçla sınırla. Görsel tek başına doğrulanmış OHLC, gösterge geçmişi veya
`confirmed` işlem kararı kanıtı sağlamaz.

## 2. Çizgi, kanal ve Fibonacci

| TradingView benzeri öğe | Araç / temel alanlar | Uygulanan davranış ve sınır |
|---|---|---|
| Trend Line / Ray | `trend_cizgisi`: `p1`,`p2`,`uzat` | İki ankraj, sağ/sol/iki uzatma; uzantı analitik projeksiyondur. |
| Horizontal Line / Ray | `yatay_cizgi`: `fiyat`; `yatay_ray`: `fiyat`,`bar` | İsteğe bağlı bar sınırları, etiket ve fiyat rozeti. |
| Vertical / Cross Line | `dikey_cizgi`: `bar`; yatay çizgiyle birleşim | Bar veya zaman referansı; kaynak zaman yoksa zaman eşleme reddedilir. |
| Arrow / Path | `ok`: `p1`,`p2`; `yol`: `noktalar` | Ok ve çok parçalı yol; genel dolgulu poligon düzenleyicisi değildir. |
| Rectangle / Zone | `dikdortgen`: `fiyat1`,`fiyat2` | Fiyat bandı ve bar aralığı; etiketin anlamını çağıran sağlar. |
| Parallel Channel | `paralel_kanal`: `p1`,`p2`,`p3` | İlk iki nokta taban, üçüncü nokta kendi x konumunda paralel uzaklığı belirler; orta çizgi seçilebilir. |
| Regression Trend | `regresyon_kanali`: bar aralığı, `sapma`,`ileri_bar` | Fiyatın bar indeksine OLS uyumu; artık standart sapması `ddof=2`; kanal güven/tahmin aralığı değildir. |
| Andrews Pitchfork | `andrews_catali`: `p1`,`p2`,`p3` | Andrews geometrisi; Schiff/Modified Schiff varyantları uygulanmaz. |
| Fib Retracement | `fib_retracement`: `p1`,`p2`,`seviyeler` | `f2-(f2-f1)*oran`; isteğe bağlı 0.618–0.786 bandı. Log tuval bu aritmetik fiyatları log konumlarına taşır. |
| Trend-Based Fib Extension | `fib_genisleme`: `p1`,`p2`,`p3` | `f3+(f2-f1)*oran`; verilen ankrajlara bağlı hesap. |
| Fib Channel | `fib_kanal`: `p1`,`p2`,`p3` | Üçüncü ankrajın tabana kendi x konumundaki uzaklığı oranlarla çoğaltılır; ölçek konvansiyonunu belirt. |
| Fib Fan | `fib_yelpaze`: `p1`,`p2` | Motorun tanımlı oran ışınları; TradingView'ın tüm fan seçenekleri değildir. |
| Fib Time Zones | `fib_zaman`: başlangıç/bitiş barı | Fibonacci bar uzaklıkları; gelecekteki olay zamanını doğrulamaz. |

Elips/daire, Gann, Fib spiral/yay ve Disjoint Channel için yerleşik eşdeğer yoktur.
Dikdörtgen/metin gibi bir yaklaşık temsil kullanılırsa bunun geometrik eşdeğer
olduğunu iddia etme. Fibonacci ve kanal seviyeleri kendi başına yön teyidi değildir.

Regresyon aritmetik fiyat uzayında hesaplanır; log tuvalde eğri olarak örneklenir.
Bu, log-fiyata regresyon uydurmakla aynı değildir. `ileri_bar` geleceğe uzatmadır;
sonuçları gözlenen mumlardan ve koşul teyidinden ayır.

## 3. Pozisyon, ölçüm ve karar durumu

| Öğe | Araç | Sınır |
|---|---|---|
| Long / Short Position | `long_pozisyon` / `short_pozisyon` | Pozitif giriş/stop/hedef, doğru yön sırası, ham fiyat mesafesi R'si ve karar etiketi. |
| Price / Bar Range | `olcum`: `p1`,`p2` | Fiyat değişimi, yüzde ve bar uzaklığı; işlem gerçekleşmesi veya takvim süresi iddiası değildir. |
| Fiyat rozeti | `fiyat_etiketi`: `fiyat`,`metin` | `render()` sırasında eksende yerleşir; yakın rozetler kaydırılır ve asıl seviyeye çizgiyle bağlanır. |
| Projeksiyon | Gelecek bar / `ileri_bar` | Senaryo; gözlenen fiyat veya yürütülmüş emir değildir. |

Long geometrisi `stop < giris < hedef`; short geometrisi `hedef < giris < stop`.
Sıfır risk, yön çelişkisi, `EMIR YOK` veya `blocked` kutuyu engeller ve gerekçe
raporlanır. `conditional` koşullu, `draft` taslaktır. `confirmed` yalnız aynı
C0'a bağlı kapanmış veri ve son karar yönünün teyidini gösterir; başarı yüzdesi
veya model doğruluğu etiketi değildir. Serbest metin durum doğrulamasını geçersiz kılamaz.

`r_etiketi` serbest metindir ve denetim kanıtı sayılmaz. Motorun R ayrımı:

| Yöntem | Hesap | Anlam |
|---|---|---|
| `raw_price_distance` | `abs(target-entry)/abs(entry-stop)` | rawR / R ham; komisyon, kayma ve gerçekleşme içermez. |
| `net_of_costs` | `(abs(target-entry)-win_cost_price)/(abs(entry-stop)+loss_cost_price)` | netR / R net; verilen maliyet varsayımlarıyla hesaplanır. |
| `atr_floor_scenario` | `reward/max(risk,ATR*stop_floor)` | ATR senaryosu; kullanılan ATR tabanı varsayımdır, çizilen stopu değiştirmez. |

`rr_audit` nesnesi `input_sha256`, `cutoff`, `direction`, `entry`, `stop`,
`target`, `method`, `R` içerir. Hash normalize veriye, cutoff ortak C0'a ve
fiyatlar çizilen geometriye eşleşmelidir. Net yöntem ayrıca negatif olmayan
`win_cost_price`/`loss_cost_price` ister; bunlar fiyat biriminde iki yönlü
komisyon/kayma gibi maliyetlerin beyan edilmiş toplamıdır. Bilinmeyen maliyeti
sıfır kabul edip net diye etiketleme.

ATR yöntemi pozitif `atr` ister; mevcut `rr_denetim.py` eşiklerini ve ürettiği
senaryo gerekçesini kaydet. Eşiklere uyum, stopun piyasada korunacağına dair
kanıt değildir. Denetim hesabı yeniden üretir; gelecekteki sonucu doğrulamaz.

## 4. Anotasyon ve göstergeler

| Öğe | Araç / alan | Uygulama sınırı |
|---|---|---|
| Text / Note / Callout | `metin`, `kutu:true`, gerekirse `ok` | Metin ve ayrı ok; ekrandaki her interaktif not davranışını kopyalamaz. |
| Up / Down Marker | `isaret` | Yön işareti; emoji/sticker/serbest ikon seti değildir. |
| Info Table | `bilgi_paneli`: `satirlar`, `konum` | `oto` mum yoğunluğuna göre köşe seçer; tüm çizimlerle çakışmayı garanti etmez. |
| EMA / SMA | `ma`: `tip`,`period`,`kaynak` | Tam uygun geçmişte hesap, ardından görünüm dilimi; yeterli ısınma gerektirir. |
| Two-series Cloud | `bulut`: `a`,`b` | Verilen MA/seri/sabit fiyat arasını doldurur; Ichimoku hesaplarının tamamını üretmez. |
| Volume | `paneller:[{tip:"hacim"}]` | Kaynak hacmi ve varsa hacim birimi; eksik hacimden gerçek ölçüm çıkarma. |
| RSI | `paneller:[{tip:"rsi",period:14}]` | Wilder yumuşatma, ilk n değişim ortalaması; düz seri 50; tam geçmiş ve kaynak segmentleri kullanılır. |
| Custom series | `paneller:[{tip:"seri",deger:[...]}]` | Verilen seri; eksik noktalar çizgiyle birleştirilmez. |
| Bollinger / Keltner / başka bantlar | Dışarıda hesaplanan `bulut` serileri | İlgili bant hesabını, pencereyi ve sapma konvansiyonunu çağıran kaydeder. |

EMA başlangıcı ilk n değerin SMA'sı, devamı `alpha=2/(n+1)`; RSI başlangıcı ilk
n fiyat değişiminin kazanç/kayıp ortalamasıdır. Pencere, fiyat kaynağı, eksik veri
ve seans boşluğu yaklaşımını görünüm seçimiyle değiştirme. Her iki göstergede
kaynak segment değişimi yeni ısınma başlatır; geçmiş kesilmesinin etkisini belirt.

## 5. Koordinatlar, katmanlar ve çıktı kanıtı

`son_bar` son N mumu gösterir; hesap geçmişini kısaltmaz. Elle çizim barları
varsayılan görünür alanı kullanır; `bar_space:"history"` tam geçmiş referansıdır.
Otomatik ankrajlar tam geçmişten görünür koordinatlara taşınır. Negatif legacy
bar sondan sayılır; zaman referansları komşu damgalar arasında kesirli konum verir.

Tüm kaynaklar/karar aynı `c0`/`cutoff`/`as_of` kesimini kullanır; birlikte verilen
takma adlar normalize edildiğinde birebir aynı timestamp olmalı. Yalnız açılış
zamanıyla kapanmışlık iddia etme: kaynak `close_time` veya açıklanmış
`timeframe`/`interval_seconds` ve açılış gerekir. Düzensiz takvimler için kaynak
kapanışlarını kullan. C0 sonrası/açık mum ve doğrulanmamış zaman statüsünü raporla.

Bölge katmanları mumların arkasında, çizgiler/etiketler önde; her ikisi plot
alanında kırpılır. Fiyat rozetleri kırpma dışında yerleştirilir. Alt panellerin
toplam yüksekliği orantılı sınırlandırılır. Çok sayıda rozet, uzun metin veya
küçük panel yine çakışabilir; çıktı görsel olarak denetlenmelidir.

Manuel SVG/normalizasyon standart kütüphaneyi, otomatik SMC tespiti pandas/NumPy'ı
kullanır. İsteğe bağlı PNG dönüşümü cairosvg gerektirir. Ortama ilişkin
matplotlib kurulu/kurulu değil varsayımı yapma.

Yeni tuvalin SVG'si ile `<cikti>.manifest.json` dosyasını birlikte değerlendir:
kaynak/normalize/çıktı hash'leri, C0, dışlanan ve tutulan satırlar, görünüm,
ölçek/birimler, formül konvansiyonları, gerçek çizim sayısı, atlananlar ve
uyarılar. Kaynak sağlayıcı/alınma zamanı gibi harici köken bilgilerini ayrıca
sakla. Ekran görüntüsü yolunda orijinal görsel, kalibrasyon ankrajları/artıkları,
pikselden tahmin edilen değerler ve anotasyon manifesti bu kanıtın karşılığıdır.
