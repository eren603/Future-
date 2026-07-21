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

Ek kural: Kullanıcı bir **grafik ekran görüntüsü** gönderirse (mum grafiği,
fiyat grafiği), açıkça istemese bile `grafik-calisma` SMC + Fibonacci akışıyla
analiz et; derin SMC tanımları için `forex-trading-expert` referanslarını kullan.

Kurallar:
1. Soru birden fazla kategoriye giriyorsa ilgili becerilerin **hepsini** birlikte
   uygula (örn. "şu kripto grafiğini analiz et" → `grafik-calisma` +
   `finansal-veri-analizi`).
2. Beceri akışını görünür süreç olarak anlatma; **arka plan disiplini** olarak
   uygula, doğrudan sonucu ver.
3. Soru finans/analiz/grafik ile **ilgili değilse** bu beceriler devreye girmez.

## Doğruluk sözleşmesi (tüm cevaplar için)
- Uydurma yok: eksik veri "VERİ YOK" işaretlenir.
- Gerçek / varsayım / yorum ayrılır.
- Her sayısal iddia bir dayanağa bağlanır (kullanıcı verisi / connector / varsayım).
- Emin olunmayan nokta açıkça belirtilir; "bilmiyorum" demek geçerli ve doğru
  bir cevaptır.
