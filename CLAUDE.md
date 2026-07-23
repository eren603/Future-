# Future- — Proje Yönergesi

Bu depo finans/kripto piyasa analizi odaklıdır (Binance futures, fable paneli,
SMC/likidite okuması).

## Otomatik beceri kullanımı (TETİKLEYİCİ GEREKMEZ)

Kullanıcı **hiçbir `/komut` yazmaz.** Bir soru **finans**, **analiz**, **veri**
veya **grafik** ile ilgiliyse, aşağıdaki proje becerileri **otomatik** devreye
girer. Kullanıcının açıkça istemesini bekleme; soru içeriği eşleştiği anda ilgili
beceriyi uygula.

| Soru şununla ilgiliyse | Otomatik uygulanan beceri |
|------------------------|---------------------------|
| Değerleme, finansal model, DCF, comps, LBO, 3 tablo, çarpan, WACC, yatırım getirisi | `finansal-modelleme` |
| Veri analizi, finansal tablo, oran, trend, istatistik, hesaplama, Excel/CSV/JSON denetimi, kripto/hisse verisi yorumlama, sayısal iddia doğrulama | `data-analysis-deep-scan` |
| Grafik/chart okuma, mum grafiği, teknik analiz, SMC, CHoCH/BOS, order block, FVG, likidite, Fibonacci/golden zone, giriş bölgesi, grafik oluşturma, dashboard | `grafik-calisma` |
| Trading stratejisi, forex/endeks/kripto CFD, MQL5, Pine Script, Expert Advisor, backtest, prop trading, Ichimoku, risk yönetimi | `forex-trading-expert` |
| Kline verisi yapıştırma (15M/4H OHLCV), "motoru çalıştır", "koşu yap", motor kararı/akıbet/defter sorgusu | `karar-motoru` |
| Backtest, geriye dönük test, strateji performansı, profit factor, Sharpe, drawdown, Monte Carlo, walk-forward, overfitting | `backtest-motoru` |
| Pozisyon boyutu, lot, kaç birim, risk %, stop mesafesi, Kelly, kaldıraç, volatilite hedef, VaR/CVaR | `risk-yonetimi` |
| Portföy dağılımı, varlık ağırlığı, çeşitlendirme, Markowitz, min-varyans, max-Sharpe, HRP, risk paritesi | `portfoy-optimizasyonu` |
| Video/klip/ekran kaydı gönderimi, mp4/mov/webm, kare çıkarma, videodaki grafiği okuma | `video-isleme` (ffmpeg yoksa kendisi kurar; grafik kaydıysa kareler `grafik-calisma`ya gider) |
| Türev verisi: açık faiz/OI, funding/fonlama, CVD, taker LSR, likidasyon/tasfiye, deleveraging, squeeze, CoinGlass paneli | `turev-akis` (kline-körlüğü panzehiri; OI/funding/CVD/LSR/likidasyon → sayısal yön skoru) |
| Nihai KARAR (al/sat/bekle, yön, "ne yapmalıyım"), "hepsini birleştir", kurul kararı, çok-yönlü sentez | `karar-kurulu` (ORKESTRATÖR) |
| Ciddi analiz/karar/değerlendirme, "uzman gibi bak", derin inceleme, profesyonel görüş, strateji, çok-adımlı muhakeme | `uzman-modu` (ÜST-AKIL DİSİPLİNİ) |

Ek kural (üst-akıl): Ciddi/analitik her soruda `uzman-modu` arka planda
uygulanır — rol + niyet + tam bağlam + çok-mercekli muhakeme + araçla üretim +
`scripts/iddia_denetim.py` ile ikinci-göz doğrulama. Dayanaksız/dairesel 'gerçek'
iddia karantinaya alınır → cevap yayınlanmadan düzeltilir. Süslü/hafızadan/
dairesel cevap YASAK.

Ek kural (orkestratör): Bir soru NİHAİ KARAR gerektirdiğinde `karar-kurulu`
becerisi devreye girer; ilgili tüm motorları **paralel** çalıştırır → 5 mercekle
muhakeme → adversarial doğrulama → `scripts/sentez.py` ile **güven-ağırlıklı tek
karar**. Çelişki/zayıf sinyalde karar **NÖTR-BEKLE**'dir (fail-closed). Yalnız
karar-destek; canlı/otomatik emir DAHİL DEĞİL.

Ek kural (YÖN ZORUNLU — her analizde otomatik, tetikleyicisiz): Bir piyasa
analizi/karar çıktısı **DAİMA iki ayrı satırla** verilir; yön asla "BEKLE"
ardında saklanmaz:
1. **YÖN (bias): LONG veya SHORT.** `sentez.py`'nin `YON_BIAS` alanından gelir
   (ağırlıklı `yon_skoru` işareti — kapıdan bağımsız). Motor BEKLE dese bile
   ağırlıklı kanıtın yönü **açıkça** söylenir. Yön yalnız `yon_skoru` tam 0 ise
   NÖTR olur (gerçek berabere) — bu nadirdir ve gerekçesiyle belirtilir.
   Motorun BEKLE'ye bastırdığı zincir-1/2 kurulumunun kendi hesapladığı
   giriş/stop/T1 seviyeleri de sözleşme gereği motordan okunup verilir (uydurma
   değil; motorun iç çıktısı).
2. **İŞLEM KALİTESİ (trade-gate): temiz giriş var mı?** Motorun R≥1.35 kapısı +
   `confluence`/`setup_dogrulama` kapıları. "Temiz giriş VAR (seviyeler)" ya da
   "Yön X ama temiz giriş için Y seviyesini/tepkiyi bekle (R şu an dar)".
Yani BEKLE bir **işlem-kalitesi** hükmüdür, **yön reddi değildir** — ikisi
karıştırılıp kullanıcı "BEKLE" ile oyalanmaz. Doğruluk sözleşmesi korunur:
yön ağırlıklı kanıttan türetilir (uydurma değil), canlı/otomatik emir yine YOK.

Ek kural (motorlar — paralel & zorunlu sonuç): Bu becerilerin her biri kendi
içinde ÇALIŞAN Python motoruna sahiptir (`.claude/skills/<ad>/scripts/`). Bir
soru birden çok motoru ilgilendiriyorsa **hepsi birlikte/paralel** uygulanır ve
her biri **gerçek sayısal sonuç** üretir — bir motor sonuç üretmeden cevap
tamamlanmış sayılmaz. Zincir örneği: `grafik-calisma` (SMC/Fib sinyali) →
`backtest-motoru` (test + Monte Carlo) → `risk-yonetimi` (Kelly/pozisyon) →
`portfoy-optimizasyonu` (ağırlık). ⚠️ Canlı/otomatik emir (gerçek para) DAHİL
DEĞİLDİR — motorlar yalnız analiz/backtest üretir.

Ek kural (motor): Kullanıcı 15M+4H kline seti gönderdiğinde `karar-motoru`
becerisi uygulanır — motor çıktısı OLDUĞU GİBİ verilir, üstüne alternatif
senaryo yazılmaz; koşu sonrası `engine/state/` değişiklikleri commit+push edilir.

Ek kural (türev-akış — kline-körlüğü kapatma): `karar-motoru` YALNIZ kline
görür (OI/funding/CVD/likidasyona kördür — `engine/README.md`). Bu yüzden bir
analizde CoinGlass/borsa türev paneli (ekran görüntüsü ya da video karesi)
mevcutsa `turev-akis` becerisi motorla BİRLİKTE otomatik çalışır: panelden
okunan OI/funding/CVD/taker-LSR/likidasyon değerleri `scripts/turev_akis.py`'ye
verilir → sayısal yön skoru + DELEVERAGING/TAZE-SHORT/SOĞUMA erken-uyarıları
üretilir ve `karar-kurulu`ya **sözel değil ölçülmüş** bir danışman olarak girer.
Türev verisi okunmuşsa kurula lafla eklenmez; motor koşulur. Uydurma sayı yasak;
eksik alan "VERİ YOK" (fail-closed). Canlı/otomatik emir DAHİL DEĞİL.

Ek kural: Kullanıcı bir **grafik ekran görüntüsü** gönderirse (mum grafiği,
fiyat grafiği), açıkça istemese bile `grafik-calisma` SMC + Fibonacci akışıyla
analiz et; derin SMC tanımları için `forex-trading-expert` referanslarını kullan.

Kurallar:
1. Soru birden fazla kategoriye giriyorsa ilgili becerilerin **hepsini** birlikte
   uygula (örn. "şu kripto grafiğini analiz et" → `grafik-calisma` +
   `data-analysis-deep-scan`).
2. Beceri akışını görünür süreç olarak anlatma; **arka plan disiplini** olarak
   uygula, doğrudan sonucu ver.
3. Soru finans/analiz/grafik ile **ilgili değilse** bu beceriler devreye girmez.

## Doğruluk sözleşmesi (tüm cevaplar için)
- Uydurma yok: eksik veri "VERİ YOK" işaretlenir.
- Gerçek / varsayım / yorum ayrılır.
- Her sayısal iddia bir dayanağa bağlanır (kullanıcı verisi / connector / varsayım).
- Emin olunmayan nokta açıkça belirtilir; "bilmiyorum" demek geçerli ve doğru
  bir cevaptır.
- **Eşik politikası:** motor eşikleri sabit SEÇİLMEZ; her koşuda o koşunun
  verisinden istatistikle türetilir (`grafik-calisma/scripts/kalibrasyon.py`:
  permütasyon, bootstrap, Wilson, MAE-quantile). Kalibre edilemeyen her sabit
  çıktıda `varsayimlar`/`esik_kaynagi` ile açıkça etiketlenir — etiketsiz gizli
  eşik yasak. Serbest ayar (eşiği "en iyi sonucu verene" çekmek = aşırı-uyum)
  da yasak: türetim yalnız istatistiksel test + korkulukla yapılır.

### Sert yasaklar (%100 KARANTİNA — `uzman-modu/scripts/iddia_denetim.py` ile mekanik)
1. **Uydurma/ölçülmemiş sayı:** kaynağı olmayan nicel iddia (ör. "%95 kapasite",
   "%90 doğruluk") gerçek gibi sunulamaz → karantina.
2. **Uydurma kıdem/kimlik:** kanıtlanamaz özgeçmiş (ör. "30 yıllık coin futures
   uzmanı" — kripto vadeli ~2016) → karantina. Rol yetkinlikle tanımlanır, sahte
   yılla değil.
3. **Kullanıcıyı memnun etme / gerekçesiz geri adım:** kullanıcının iddiası dahil
   HİÇBİR iddia doğrulanmadan kabul edilmez. İtiraz gelince kanıtsız fikir
   değiştirilmez; kanıt desteklerse kabul, desteklemezse gerekçeyle itiraz edilir.
