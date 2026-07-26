# Future- — Proje Yönergesi

Bu depo finans/kripto piyasa analizi odaklıdır (Binance futures, fable paneli,
SMC/likidite okuması).

## VARSAYILAN ÇALIŞMA MODU (otomatik — tetikleyici GEREKMEZ)

Bu dosya her oturumda otomatik yüklenir; aşağıdaki disiplin `/komut` beklemeden
**her ciddi analiz/kararda** uygulanır (ayrıntılar aşağıdaki "Ek kural"larda):

1. **Motorlar birlikte koşar** — varsayılan yol `piramit-sistem`
   (`scripts/piramit.py`): K1 LLM → K2 AI AJAN → K3 ÇOKLU-AJAN → K4 AGI → K5 SI
   katmanlarını **kapılarıyla** sırayla koşturan ÇALIŞAN orkestratör (elle
   zincirleme değil). Boru hattı koşamıyorsa (şema dışı/eksik veri) motorlar
   aynı turda ayrı çağrılarla elle koşulur. Her durumda her motor **gerçek
   sayısal sonuç** üretir; dosyadan okunmayan sayı kullanılmaz.
2. **5 danışman merceği:** Muhalif / İlk-Prensipler / Genişletici / Dış-Göz /
   Uygulayıcı — her biri farklı kör noktayı yakalar.
3. **Güven-ağırlıklı sentez** (`karar-kurulu/scripts/sentez.py`) → **iki satır:**
   YÖN (bias, gizlenmez) + İŞLEM KALİTESİ (temiz giriş var mı / tepki bekle).
4. **Doğruluk sözleşmesi:** gerçek/varsayım/yorum ayrılır; eksik = "VERİ YOK";
   uydurma yok. İkinci-göz **ELLE** yapılır — grounding mekanikleştirilemez, sahte
   otorite bir denetçiye devredilmez.
5. **Şişirilmiş R YASAK:** stop/hedef içeren, motorun tek-kaynaklı çıktısı olmayan
   her R `karar-kurulu/scripts/rr_denetim.py`'den geçer (ATR-tutarsız = R_gercekci).
6. **Memnun etme yok:** kullanıcının iddiası dahil hiçbir iddia kanıtsız kabul
   edilmez; akıcı anlatı otomatik "daha kaliteli" sayılmaz (araç-bağımsız sınanır).

⚠️ Yalnız karar-destek; canlı/otomatik emir (gerçek para) DAHİL DEĞİL.

## Otomatik beceri kullanımı (TETİKLEYİCİ GEREKMEZ)

Kullanıcı **hiçbir `/komut` yazmaz.** Bir soru **finans**, **analiz**, **veri**
veya **grafik** ile ilgiliyse, aşağıdaki proje becerileri **otomatik** devreye
girer. Kullanıcının açıkça istemesini bekleme; soru içeriği eşleştiği anda ilgili
beceriyi uygula.

| Soru şununla ilgiliyse | Otomatik uygulanan beceri |
|------------------------|---------------------------|
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
| Tam analiz / tam boru hattı: 15M+4H kline (+ varsa türev paneli), "bütün motorları çalıştır", "en alttan en üste", çok katmanlı değerlendirme | `piramit-sistem` (**VARSAYILAN YOL** — K1→K5, `scripts/piramit.py`) |
| Ciddi analiz/karar/değerlendirme, "uzman gibi bak", derin inceleme, profesyonel görüş, strateji, çok-adımlı muhakeme | `uzman-modu` (ÜST-AKIL DİSİPLİNİ) |

Ek kural (üst-akıl): Ciddi/analitik her soruda `uzman-modu` arka planda
uygulanır — rol + niyet + tam bağlam + çok-mercekli muhakeme + araçla üretim +
**elle ikinci-göz** (Reflexion) disiplini. Dayanaksız/dairesel 'gerçek' iddia
çıkarılır → cevap yayınlanmadan düzeltilir. (İddia-grounding metinden
mekanikleştirilemez; sahte-otorite bir denetçiye devredilmez — mekanikleşen
kontroller `rr_denetim`/`sentez`/motorlar ile, grounding elle.) Süslü/hafızadan/
dairesel cevap YASAK.

Ek kural (orkestratör): Bir soru NİHAİ KARAR gerektirdiğinde `karar-kurulu`
becerisi devreye girer; ilgili tüm motorları **birlikte (aynı turda, bağımsız
çağrılarla)** koşturur → 5 mercekle muhakeme → adversarial doğrulama →
`scripts/sentez.py` ile **güven-ağırlıklı tek karar**. Çelişki/zayıf sinyalde
karar **NÖTR-BEKLE**'dir (fail-closed). Yalnız karar-destek; canlı/otomatik emir
DAHİL DEĞİL.

Ek kural (PİRAMİT — VARSAYILAN YOL, TETİKLEYİCİ GEREKMEZ): Bir piyasa
analizi/kararı üretilecekse motorlar ELLE zincirlenmez; `piramit-sistem`
becerisinin `scripts/piramit.py` boru hattı koşulur (K1 LLM → K2 AI AJAN →
K3 ÇOKLU-AJAN → K4 AGI → K5 SI). Gerekçe: elle zincirde motor atlanabilir,
`verifier` boş bırakılıp fail-OPEN'a düşülebilir, `rr_denetim` unutulabilir ve
danışman güveni **elle takdir** edilerek kaynaksız sayı üretilebilir — boru
hattı bunların hepsini mekanikleştirir (güven motorun kendi çıktısından gelir).
Kullanıcı `/komut` yazmaz; `.claude/hooks/piramit_auto.py` (UserPromptSubmit)
her istemde girdiyi kontrol eder, `engine/girdi/` verisi DEĞİŞMİŞSE boru hattını
koşar ve iki-satır özetini bağlama enjekte eder; veri değişmemişse son koşunun
özetini taşır (gereksiz koşu ve hafıza kirliliği yok). Boru hattı bir katman
kapısında durursa çıktı OLDUĞU GİBİ verilir — durduğu katman ve gerekçesi
gizlenmez, eksik veriyle karar UYDURULMAZ. Boru hattı koşamıyorsa (şema dışı
veri, motor hatası) elle koşuya düşülür ve bu AÇIKÇA söylenir.
⚠️ K4/K5'in "AGI/SI" adları resimdeki piramide sadakattir; teknik iddia
DEĞİLDİR (K4 = çelişki/doğrulama denetçisi, K5 = sentez + Wilson kalibrasyonu).

Ek kural (GÖZLEMCİ AJANLAR — her katmanda, tetikleyicisiz): Her katmanın
(K1…K5) bir gözlemcisi vardır (`piramit-sistem/scripts/gozlemci.py`) ve katmanın
ZİHNİNİ değil ARTEFAKTINI denetler: hangi dosya okundu, hangi motor koştu, hangi
sayı nereden geldi, üst katmana ne gitti. Denetlenen ihlaller: UYDURMA (üst
katmandaki sayı/danışman alt katmanda kaynaksız), HAFIZA (o koşunun verisinden
değil sabitten/önceki koşudan üretim; K1 çıkarım YAPAMAZ), DAİRESEL (danışman
kendi çıktısıyla doğrulanıyor), EKSİK_AKTARIM (alt katmanda üretilip üst katmana
ne giren ne gerekçeyle dışlanan sonuç = sessiz kayıp/yarıda kesme), TÜNEL (karar
tek kanıt ailesine dayanıyor), MEMNUN_ETME (kapılar uygulanmamış, doğrulama
fail-OPEN, karar kendi skoruyla çelişiyor), SIRADAN (motor çıktısı şema
derinliğini karşılamıyor), ÇARPIŞMA (bağımsız motorlar aynı sayıyı üretmiş =
biri diğerini kopyalamış). Kritik ihlalde (UYDURMA/DAİRESEL/EKSİK_AKTARIM/
MEMNUN_ETME) **işlem kalitesi MÜHÜRLENİR** — YÖN yine gösterilir ama "işlem yok"
denir (fail-closed). Uyarılar gizlenmez, çıktının altında listelenir.
Ek olarak `scripts/iddia_denetle.py` KULLANICIYA SUNULACAK METNİ denetler:
metindeki her sayı koşu raporunda birebir var mı? KAYNAKSIZ çıkan sayı ya
rapordan düzeltilir ya metinden çıkarılır. Bu araç ANLAM denetlemez (yorum
doğruluğu elle ikinci-göz işidir) — yalnız uydurma SAYIYA karşı korkuluktur.

Ek kural (HESAP VERME + KIYAS — her yeni veride İLK İŞ, atlanamaz): Yeni veri
geldiğinde YENİ analizden ÖNCE iki soru cevaplanır (`scripts/kiyas.py`):
(1) HESAP VERME: bir önceki koşuda verilen giriş/stop/hedef seviyeleri yeni
barlarda ne oldu — tetiklendi mi, stop mu oldu, hedefe mi gitti, gerçekleşen R
kaç? Ölçüm `akibet_etiketle.simule_et` ile aynı muhafazakâr kurallarla yapılır
(aleyhte kenardan dolum, aynı barda stop+hedef → STOP). (2) KIYAS: eski veri ne
gösteriyordu, yeni veri ne gösteriyor — yön DEVAM mı etti, DÖNDÜ mü, NÖTRE mi
çekildi; hangi sürücü değişti (trend, ADX, ATR, türev skoru/kapsamı, funding,
LSR, CVD, OI, likidasyon) ve hangi danışman duruş değiştirdi. Yön AYNI kalsa
bile sürücü değişimi kararın kalitesini değiştirir — bu yüzden kıyas atlanamaz.
Her koşu sonunda `onceki_kosu.json` anlık görüntüsü yazılır (kum havuzu
koşusunda gerçek hafızaya DEĞİL, sandığa). Kayıt yoksa "ilk analiz" denir,
geçmiş UYDURULMAZ. Gözlemci: kayıt varken akıbet ölçülmemişse ya da kıyas
koşmamışsa EKSİK_AKTARIM ihlali verir. Çıktıda bu iki başlık EN ÜSTTE,
YÖN/İŞLEM satırlarından ÖNCE gösterilir.

Ek kural (ÇAPRAZ-VARLIK + SABİT KISIT — boru hattı içinde, elle koşulmaz):
İkinci bir sembol varsa `korelasyon.py` K2'de koşar ve K4'te risk çarpanına
çevrilir: |ρ| ≥ 0.85 → KOPYA POZİSYON, aynı yönde ikinci pozisyon bağımsız
bahis DEĞİLDİR, toplam risk ×2 sayılır. Dolar cinsi kısıt (kontrat + sabit
stop + hedef bandı) varsa `usd_hedef.py` K5'te koşar; ATR ve likidite
KURULUM ÖLÇEĞİ yapısından (`smc_tespit_h4`) gelir — stop/ATR ∈ [0.8, 2.0]
olan dilim kurulum ölçeğidir, alt dilim yalnız TETİK içindir. Her iki motor
da job'da BEYAN EDİLİP koşmazsa gözlemci EKSİK_AKTARIM ihlali verir (sessiz
atlama yok).

Ek kural (ZORUNLU GİRDİLER — her koşuda, atlanamaz): Bir piyasa analizi
üretilecekse şu üçü BİRLİKTE beklenir ve hiçbiri sessizce atlanamaz:
(1) `piramit_veri_*.json` paketi (15M+4H kline + OI + funding + taker-LSR),
(2) **CoinGlass likidasyon** long/short değerleri →
`engine/girdi/turev_ham/likidasyon.json` (türev kapsamını 1.00'e çıkarır),
(3) **grafik ekran görüntüsü ya da video** → görsel okuma
`engine/girdi/gorsel_okuma.json`'a yazılır (video ise önce `video-isleme`
kareleri çıkarır). Görsel okuma bir ÖLÇÜM DEĞİLDİR: güveni `gorsel_tavan`
(0.50) ile sınırlıdır ve doğrulaması `smc_tespit` trendiyle UYUŞMASINA
bağlıdır — uyuşmazsa çürütülür ve "GÖRSEL-MEKANİK ÇELİŞKİSİ" bayrağı düşer
(göz ile algoritma birbirini teyit eder). Eksik olan zorunlu girdi K1'de
tespit edilir, K4'te çelişki olarak taşınır ve çıktının EN ÜSTÜNDE
"⚠ ZORUNLU GİRDİ EKSİK" satırıyla gösterilir; eksikle karar UYDURULMAZ.
TAZELİK ZORUNLU: elle gelen likidasyon/görsel okuma hangi veriye ait olduğunu
`zaman_utc` damgasıyla KANITLAR. Damgasız ya da son bardan `zorunlu_damga_
tolerans_dk` (240) dakikadan eski okuma **BAYAT** sayılır ve kullanılmaz —
yeni kline eski panel okumasıyla birleştirilmez (sahte güncellik yasak).

Ek kural (VERİ ALIMI + İKİNCİ SEMBOL — kancada, elle komut yok): Kullanıcı bir
`piramit_veri_*.json` paketi gönderdiğinde `paket_ac` ELLE çağrılmaz;
`.claude/hooks/piramit_auto.py` yükleme dizinlerini tarar, **en yeni işlenmemiş**
paketi doğrulamadan geçirip depoya alır ve boru hattını koşturur. İki korkuluk:
(1) aynı içerik iki kez alınmaz (SHA defteri), (2) paketin verisi depodakinden
YENİ DEĞİLSE alınmaz — eski paket yeni veriyi GERİ SARAMAZ (aksi halde BTC eski
bara döner, ETH yeni barda kalır = ayrışmış sahte kıyas). Ana sembol koştuktan
sonra ikinci sembol (`engine/girdi/eth/`) AYNI istemde kendiliğinden koşar:
korelasyon + sabit-USDT profili (`engine/girdi/eth_profil.json`) job'da beyan
edilir, kendi sicilinde (`engine/state/eth`) ve kendi hafızasında
(`hafiza/agirlik_eth.json`) tutulur — ana sembolün öğrenilmiş ağırlığı EZİLMEZ.
Duran görev/hedef/yöntem `engine/gorev.json`'dadır ve her istemde bağlama
basılır: yeni pencere görevi tekrar sormaz, kullanıcı tekrar anlatmaz.

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

Ek kural (EMİR ÇIKTISI — hikâye değil, emir; tetikleyicisiz): Her karar
analizinin sonunda `emir_plani.py` koşar ve kararı UYGULANABİLİR emre çevirir:
`<MARKET|LIMIT> <LONG|SHORT> @giriş | stop | T1 | R`. Seviyeler YALNIZ ölçülen
yapıdan gelir (açık 15M FVG kenarları + teyitli swingler); yuvarlak/uydurma
seviye yasak. Stop: sabit-USDT profili varsa mesafe profilden (usdt/kontrat),
yoksa girişin ötesindeki EN YAKIN teyitli swing. Hedef: profil varsa profilin
kazanç bandı, yoksa yön tarafındaki İLK teyitli likidite — yoksa aday DÜŞER
("R katı" uydurma hedef üretilmez). Her aday `rr_denetim` (ATR ölçeği) ve
profil varsa `usd_hedef` 5 kapısından geçer; ŞİŞİRİLMİŞ ya da R < 1.35 olan
reddedilir. MARKET yalnız fiyat giriş bölgesindeyse (|giriş−fiyat| ≤
0.1×ATR15) verilir, aksi halde LIMIT. Hiçbir aday geçemezse "EMİR YOK" +
düşen kapı yazılır — boş bırakılmaz. Gözlemci: emir seviyeleri denetimden
geçmemişse UYDURMA, emir yönü kararla çelişiyorsa MEMNUN_ETME ihlali verir.

Ek kural (ÇELİŞKİ TURU — adversarial ikinci koşu, tetikleyicisiz): Sentez
bittikten sonra `_celiski_turu` aynı kurulu YALNIZ doğrulanmış danışmanlarla
yeniden sentezler. Yön değişiyorsa karar doğrulanmamış kanıta yaslanıyordur →
**fail-closed NÖTR** (yön yine gösterilir, işleme çevrilmez). Değişmiyorsa
"yön DAYANIKLI" diye raporlanır. Gözlemci, dayanıksız bulguya rağmen kararın
yönlü kalmasını MEMNUN_ETME ihlali sayar.

Ek kural (BİRLEŞİK SENTEZ ÇIKTISI — her karar analizinde standart): Nihai analiz
DAİMA tek-temiz yapıda verilir: **(1) Motorlar (kanıt)** — karar-motoru/turev/
sentez'in dosyadan okunan gerçek sayıları; **(2) 5 danışman merceği (çerçeve)** —
Muhalif/İlk-Prensipler/Genişletici/Dış-Göz/Uygulayıcı, her biri bir motor/panel
kanıtına bağlı (anlatı için sayı UYDURMA); **(3) YÖN** (`YON_BIAS`); **(4) İŞLEM
KALİTESİ** — seviyeler motordan (gerçek), el-ile swing çerçevesi varsa
`rr_denetim.py`'den geçmiş **R_gercekci** ile (yorum etiketli); **(5) gerçek/
varsayım/yorum ayrımı**. Motor mekaniği + 5 mercek birlikte; ne kuru motor
çıktısı ne süslü anlatı — ikisinin kusursuz sentezi.

Ek kural (ŞİŞİRİLMİŞ R YASAK — mekanik, tetikleyicisiz): Stop/hedef içeren bir R
sunulacaksa ve o R motorun tek-kaynaklı çıktısı DEĞİLSE (ör. 5 mercekte el ile
swing hedefi/stop kuruldu), `karar-kurulu/scripts/rr_denetim.py`'den GEÇMEDEN
yayınlanamaz. Araç, dar-stop (scalp) + uzak-hedef (swing) eşleşmesiyle R'yi yapay
şişirmeyi ATR-ölçekle mekanik yakalar → **ŞİŞİRİLMİŞSE R_gercekci kullanılır.**
ATR o koşunun kline'ından hesaplanır. Cazip/akıcı anlatı otomatik "daha kaliteli"
sayılmaz (narrative-fluency yanılgısı); başlık sayıları araç-bağımsız aritmetikle
sınanır. Bu, "serbest ayar/aşırı-uyum" panzehiridir.

Ek kural (motorlar — birlikte & zorunlu sonuç): Bu becerilerin her biri kendi
içinde ÇALIŞAN Python motoruna sahiptir (`.claude/skills/<ad>/scripts/`). Bir
soru birden çok motoru ilgilendiriyorsa **hepsi birlikte** (aynı turda, ayrı
çağrılarla; otomatik fan-out kodu YOK — birlikte demek elle art arda/tek turda
demektir) uygulanır ve her biri **gerçek sayısal sonuç** üretir — bir motor
sonuç üretmeden cevap tamamlanmış sayılmaz. Zincir örneği: `grafik-calisma` (SMC/Fib sinyali) →
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
PANEL YOKSA DA KÖRLÜK KAPANIR: `piramit-sistem/scripts/turev_girdi.py` **CVD'yi
kullanıcının KENDİ kline'ından çevrimdışı hesaplar** (12 alanlı Binance
kline'ının 9. alanı = taker alış hacmi; delta = 2×taker − hacim). Kanca bunu her
istemde üretip `engine/girdi/turev.json`'a yazar → türev danışmanı kurula
kendiliğinden girer. OI, anlık görüntü defterinden (`engine/state/turev_seri.jsonl`;
MCP/borsa görüntüleri `--oi-snapshot` ile eklenir), funding/LSR ağ izin verirse
Binance vadeli genel uçlarından gelir; likidasyon yalnız elle panelden. Eksik
kanal UYDURULMAZ — motor kapsamı düşükse skoru VERİ YOK'a çeker ve danışman
doğrulanmamış sayılır (fail-closed).

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
  eşik yasak.
- **Karar kapıları da dinamiktir** (`piramit-sistem/scripts/esik_kalibre.py`,
  K5'te sentezden ÖNCE koşar): `score` eşiği bu koşunun kurulundan bootstrap
  ile ölçülür (z×SE — sinyal kendi gürültüsünü aşmalı); `min_agreement` ve
  `min_side_weight` çoğunluk kuralına (0.5 pay / 0.5 × toplam etkin ağırlık)
  bağlanır — yapısal olduğu ETİKETLENİR; üçü birden **rejim sertliğiyle**
  çarpılır: sertlik = clamp(p_başabaş / p_devamlılık_Wilson_alt, 1.0, 2.0),
  yani ölçülen yön devamlılığı başabaşın altındaysa kuruldan daha çok kanıt
  istenir. Sertlik 1.0'ın ALTINA inmez (eşik gevşetilmez — yanlış-pozitifin
  maliyeti asimetriktir). Türetilemezse statik korkuluğa düşer ve "STATİK
  KORKULUK (fail-closed)" diye etiketlenir. Gözlemci, kalibre edilen eşikle
  sentezin UYGULADIĞI eşiği karşılaştırır; ayrılırsa UYDURMA ihlali verir. Serbest ayar (eşiği "en iyi sonucu verene" çekmek = aşırı-uyum)
  da yasak: türetim yalnız istatistiksel test + korkulukla yapılır.

### Sert yasaklar (ELLE uygulanan kanıt disiplini — mekanik denetçiye devredilmez)
1. **Uydurma/ölçülmemiş sayı:** kaynağı olmayan nicel iddia (ör. "%95 kapasite",
   "%90 doğruluk") gerçek gibi sunulamaz → karantina.
2. **Uydurma kıdem/kimlik:** kanıtlanamaz özgeçmiş (ör. "30 yıllık coin futures
   uzmanı" — kripto vadeli ~2016) → karantina. Rol yetkinlikle tanımlanır, sahte
   yılla değil.
3. **Kullanıcıyı memnun etme / gerekçesiz geri adım:** kullanıcının iddiası dahil
   HİÇBİR iddia doğrulanmadan kabul edilmez. İtiraz gelince kanıtsız fikir
   değiştirilmez; kanıt desteklerse kabul, desteklemezse gerekçeyle itiraz edilir.
