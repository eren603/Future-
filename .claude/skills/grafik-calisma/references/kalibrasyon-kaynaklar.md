# Dinamik kalibrasyon — kanıt tabanı (iki yönlü, kaynaklı)

`kalibrasyon.py`'nin tasarım gerekçesi. Karşı-kanıt DAHİL — tek yönlü
araştırma yasak (at-gözlüğü panzehiri). Kaynaksız iddia buraya giremez.

## Kullanıcı iddiasının denetimi
İddia: "Piyasa dinamik/kaotik/manipülatif; dünkü eşik bugün işe yaramayabilir,
eşikler her çalıştırmada dinamik ayarlanmalı."

**Denetim sonucu: KISMEN DOĞRU.** Uyarlanabilirlik lehine sağlam kanıt var;
ama "her koşuda serbest yeniden ayar" biçimi aleyhine DAHA GÜÇLÜ kanıt var.
Doğru biçim: eşik SEÇİLMEZ (optimize edilmez), İSTATİSTİKTEN TÜRETİLİR.

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

## Sentez → depodaki uygulama
Literatürün onayladığı dinamiklik: (a) az-parametreli ve ekonomik gerekçeli
(volatilite ölçekleme, rejim kapısı), (b) seçim-yanlılığına karşı test edilmiş,
(c) koşullu/eşikli. Bu yüzden `kalibrasyon.py`:
1. **Eşik optimizasyonu YOK** — hiçbir eşik "en iyi sonucu verene" çekilmez
   (data-snooping'in kendisi olurdu).
2. **Türetim istatistiksel**: permütasyon testi (edge ≠ sürüklenme; White'ın
   Reality Check soyundan), bootstrap CI, Wilson kötümser kazanma oranı →
   min R:R, kazanan-MAE quantile → SL tamponu (volatilite ölçekleme sınıfı).
3. **Korkuluklar** (clamp) + **varsayım defteri**: kalan her sabit etiketli.
4. **Fail-closed**: kanıt/veri yetersiz → sinyal yok.

## Sınır (dürüstlük)
Geçmiş ≠ gelecek; kalibrasyon da geçmiş veriden yapılır. Permütasyon+bootstrap
sahte keşfi azaltır, sıfırlamaz (tek tarihsel yol; CPCV değil). Manipülatif
piyasada hiçbir istatistik garantisi yoktur — bu yüzden nihai karar hâlâ
fail-closed kapılardan geçer ve zayıf kanıtta BEKLE verilir.
