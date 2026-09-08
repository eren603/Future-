# Dinamik kalibrasyon — kanıt tabanı (iki yönlü, kaynaklı)

`kalibrasyon.py`'nin tasarım gerekçesi. Karşı-kanıt DAHİL — tek yönlü
araştırma yasak (at-gözlüğü panzehiri). Kaynaksız iddia buraya giremez.

## Kullanıcı iddiasının denetimi
İddia: "Piyasa dinamik/kaotik/manipülatif; dünkü eşik bugün işe yaramayabilir,
eşikler her çalıştırmada dinamik ayarlanmalı."

**Denetim sonucu: KISMEN DOĞRU.** Uyarlanabilirlik lehine sağlam kanıt var;
ama "her koşuda serbest yeniden ayar" biçimi aleyhine DAHA GÜÇLÜ kanıt var.
Uygulanan biçim: parametre yalnız geçmiş eğitim bölümünde belirlenir; sonra
sabit tutulup ayar için kullanılmayan sonraki bölümde ölçülür. Bir quantile
türetmek de veriyle ayardır; tek başına seçim yanlılığını ortadan kaldırmaz.

## Uyarlanabilirlik LEHİNE kanıt
- **Lo (2004), Adaptive Markets Hypothesis** (J. Portfolio Management):
  piyasa etkinliği evrimseldir; strateji kârlılığı ortamla azalıp geri gelir →
  statik strateji savunulamaz. https://web.mit.edu/Alo/www/Papers/JPM2004_Pub.pdf
- **Ang & Bekaert (RFS 2002; 2004)**: rejim-değiştiren dağıtım, statiğe
  out-of-sample üstün; rejimleri yok saymanın maliyeti ~%2-3 servet.
  https://academic.oup.com/rfs/article-abstract/15/4/1137/1568247
- **Rattray, Sargaison & Van Hemert (JPM 2018)**: volatilite hedefleme
  (sürekli yeniden ölçeklenen risk) 1926-2017, 60 varlıkta Sharpe'ı yükseltir,
  sol kuyruğu inceltir. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538
- **Kalman/Markov-switching literatürü**: tek rejimde kalibre edilen model
  diğer rejimde kötü yönlendirir — ama disiplinli biçim: planlı aralıklarla
  yeniden kalibre + her dönem içinde SABİT tut. https://arxiv.org/html/2410.14841v1

## Naif yeniden-ayar ALEYHİNE kanıt (karşı-kanıt)
- **Bailey, Borwein, López de Prado & Zhu — PBO/CSCV** (J. Computational
  Finance): çok konfigürasyon denemek yüksek backtest performansını kolayca
  üretir; aşırı-uyumlu strateji OOS'ta sistematik kötü.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- **Aynı ekip, "Pseudo-Mathematics..." (Notices of the AMS, 2014)**: bellek
  etkisi altında aşırı-uyumlu backtest'in beklenen OOS getirisi **NEGATİF** —
  agresif ayar hiç ayar yapmamaktan kötü olabilir. Deneme sayısı arttıkça
  gereken minimum backtest uzunluğu (MinBTL) büyür; "her işlemde ayar" =
  gözlem başına bir parametre = serbestlik derecesi sıfır.
  https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf
- **Deflated Sharpe Ratio (Bailey & López de Prado 2014)**: her ek ayar
  denemesi, sonucun aşması gereken istatistik çıtayı yükseltir.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- **Sullivan, Timmermann & White (J. Finance 1999)**: 100 yıl DJIA, ~7800
  teknik kural — data-snooping düzeltmesi sonrası en iyi kural OOS'ta üstünlük
  sağlayamadı. "Geçmişte en iyi eşiği seç, ileri taşı" = belgelenmiş başarısızlık.
  https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00163
- **DeMiguel, Garlappi & Uppal (RFS 2009)**: 14 optimizasyon modeli 1/N'i
  tutarlı geçemedi — tahmin hatası, optimizasyon kazancını yutar.
  https://academic.oup.com/rfs/article-abstract/22/5/1915/1592901
- **Arian, Norouzi & Seco (Knowledge-Based Systems 2024)**: walk-forward bile
  sahte keşfi önlemede en zayıf yöntem; Combinatorial Purged CV üstün.
  https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110
- **Harvey, Liu & Zhu (RFS 2016)**: yaygın veri madenciliği yüzünden t>2.0
  anlamsız; yeni bulgu için t>3.0 gerekir.
  https://academic.oup.com/rfs/article-abstract/29/1/5/1843824
- **Kripto özel uyarı**: 2020-22'de tespit edilen rejim desenleri sonraki
  dönemde genellenemedi; uyarlanabilirlik tek başına kurtarmadı (walk-forward
  değerlendirmeli BTC çalışması; tam metin bağımsız doğrulanmadı).

## Nüans (orta yol — depodaki tasarımın dayanağı)
- **Bongaerts, Kang & van Dijk (FAJ 2020)**: KOŞULSUZ volatilite hedefleme
  tutarlı iyileştirmez; yalnız aşırı rejimlerde ayarlayan KOŞULLU versiyon
  Sharpe'ı yükseltir. Ders: "her an" değil "rejim eşiği aşılınca" ayarla.
  https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1790853
- **Pesaran & Timmermann**: yapısal kırılma varken bile yalnız-en-yeni-veri
  optimal değil; kırılma öncesi veriyi kısmen dahil etmek MSFE'yi düşürür.
  https://www.sciencedirect.com/science/article/abs/pii/S0304407613000687

## Uygulama sözleşmesi — nedensel ayrım ve sınırlı tarihsel destek

Yukarıdaki bibliyografya önceki araştırma notudur; bu kod onarımı bütün kaynak
özetlerini bağımsız olarak yeniden doğrulamadı. Hiçbir makale, aşağıdaki somut
stratejiye kârlılık veya eşik doğruluğu garantisi olarak kullanılmaz. Önceki
“istatistikten türetmek optimizasyon değildir” ve rastgele giriş karşılaştırmasının
“White Reality Check soyundan” olduğu iddiaları bu uygulamayı tarif etmiyordu.

### Zaman sırası

- `setup_dogrulama.simulate` ve `fvg_kalibre.kalibre` önce eğitim önekini ayırır.
  Varsayılan oran 0.60 bir tasarım tercihidir. İlerleyen veriyle sabit bir sınır
  korumak için `params.train_end_i` açıkça verilebilir; bu indeks eğitimdeki son bardır.
- MAE, hedef adayı, FVG seviye/stop ve filtre adayları yalnız bu önekten çıkar.
  FVG ızgarasının sıralanması açıkça **eğitimde seçim**dir, anlamlılık testi değildir.
- Seçilen birleşik politika sonraki bölüm boyunca sabittir. Sınırdan eski
  işlemler/sonuç pencereleri taşınmaz. Değerlendirme zaman bloklarının sonunda
  tam azami işlem ufku kalmayan girişler sonuca bakmadan dışarıda bırakılır.
- Aynı değerlendirmeye bakarak tekrar tekrar ayar yapmak bu tek koşunun
  sınamasının dışındadır; `repeated_retuning_adjusted=false` bunu bildirir.

### İşlem ve referans

Ortak `kalibrasyon.execute_orders` her iki tarafa da aynı limit yürütmesini,
aynı maliyet/funding varsayımını ve tek pozisyon kapasitesini uygular. Giriş ve
SL fiyatları emir verilirken kapanmış ATR'den dondurulur. Bekleyen emirler ilk
gerçekleşme sırasıyla yarışır; önceki olayın gelecekteki çıkışı kapasite ayırmaz.

Kapanış girişinin izlenmesi sonraki mumda başlar. Limit giriş mumunun daha önce
oluşmuş olumlu fitili TP diye kredilendirilmez; kapanış veya açılışta gerçekleşmiş
giriş bunu doğrulayabilir. Aynı mumda stop+hedef stop sayılır. Stop ötesi açılış
boşluğu erişilebilen açılış fiyatından çıkar. MAE, stop sonrası daha uç fiyata
uzatılmaz; TP mumunun sırası bilinmiyorsa muhafazakâr OHLC MAE üst sınırı olarak
etiketlenir. Model ölçülmemiş mum içi yolu bildiğini iddia etmez.

Referans politikası yalnız EĞİTİM emirlerinden dondurulur: yön, önceki kapanışa
göre ATR ölçekli limit/stop/hedef mesafeleri, ömür ve varsa geçersizlik tarifleri
ile eğitimdeki emir/bar oranı. Değerlendirme döneminde sabit seed ile her barda
Bernoulli emir verme denemesi yapılır; emir o bardan ÖNCEKİ kapanış/ATR ile
ölçeklenir. Gelecekteki holdout emirleri, yön karışımı veya işlem sayısı referans
politikasına giremez. Sonraki holdout fiyatlarının değiştirilmesi önceki referans
emirlerini değiştirmez; bu özellik regresyonla sınanır. Aynı yürütme motoru ve
maliyet/kapasite kuralları iki tarafa da uygulanır.

Dolum ve kapasite nedeniyle gerçekleşen işlem sayıları değişebilir; iki seri de
sıfır işlem olan zaman bloklarını içerir. Bu **eğitimde donmuş rastgele-zaman
referansı**dır, permutation p testi değildir. Eski `permutation_pvalue` işlevi
yalnız betimsel uyumluluk çıktısı verir; `p=null`, `valid_for_edge_permission=false`.

### Kanıt kapısı ve çıktı

- `evaluation` eğitim/değerlendirme sınırlarını, sabit parametre durumunu, zaman
  ekseni kontrolünü, net işlem ve referans sayısını, blok sayısını ve CI'ları verir.
- Bloklar birbiriyle örtüşmez; içindeki getiriler birlikte toplanır. Bootstrap
  birimi tek FVG satırı değil takvim bloğudur. Bloklar arası yaklaşık bağımsızlık
  hâlâ bir varsayımdır; keyfî rejim değişimine karşı garanti yoktur.
- En az 10 blok ve iki tarafta en az 10 kullanılan işlem bir tasarım tabanıdır.
  Eğitim örneği de yeterli olmalıdır. Net getiri CI altı ve eşleştirilmiş
  referans-farkı CI altı pozitif, iki yarının net blok ortalaması pozitif ve zaman
  ekseni geçerli ise `sinyal_izni=true`, `evidence_status=heldout_support` olur.
- Sonuç **“AYRILMIŞ DÖNEMDE DESTEK VAR”** der; “EDGE KANITLI” veya gelecek
  başarı yüzdesi demez. `validated_edge` yalnız aynı sınırlı tarihsel desteğin
  uyumluluk boolean'ıdır; onu tek başına gelecek iddiasına dönüştürmeyin.
- `confluence_thresholds={atr_mult: sayı, min_rr: sayı}` her durumda kullanılabilir
  eğitim/tasarım adayını taşır. Yetersiz kanıt bu sayısal çıktıyı silmez; işlem
  iznini kapatır. `min_rr`, sabit değerlendirilmiş hedef adayıdır; başabaş garantisi değildir.

### Wilson, maliyet, yaşam süresi ve Monte Carlo sınırları

Wilson dönüşümündeki teorik `(1-p)/p` gereksinimi kırpılmadan `required_rr` /
`min_rr` alanında kalır. Örnek yoksa gereksinim `null`dır. Ayrı `candidate_rr`
tasarım sınırında tutulur; `feasible=false` yüksek gereksinimin 5R ile karşılandığı
anlamına gelmez. Hedef değişince kazanma olasılığı yeniden ölçülmelidir; bu yüzden
hedef adayı eğitimde seçilir ve sonraki bölümde sabit değerlendirilir. Net ücret,
kayma, funding ve süre-sonu çıkışları ikili/brüt Wilson formülüne indirgenmez.

FVG çıktısı brüt R, maliyet R ve net R'yi ayırır. Dolum oranının paydasına yalnız
tam takip ufku olan FVG'ler girer; yeniler `n_censored` sayılır. Ömür quantile'ı
tam gözlenmiş bütün FVG'leri kapsar; dolmayanlar da paydadadır. İstenen quantile
ufuk içinde erişilmediyse `bar=null`; dolanlara koşullu medyan ayrıca etiketlidir.

`backtest.monte_carlo` sabit işlemlerin sırasından kaynaklanan düşüş riskini ölçer.
Başlangıç equity=1 hesaba katılır. Çarpım sıradan bağımsız olduğundan terminal
getiri değişmez; `prob_profit=null`, `valid_for_future_profit_probability=false`.
Bu çıktı gelecekte kâr olasılığı veya sinyal kapısı değildir.
