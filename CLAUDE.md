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
veya **grafik** ile ilgiliyse, ilgili proje becerileri **otomatik** devreye
girer. Kullanıcının açıkça istemesini bekleme; soru içeriği eşleştiği anda ilgili
beceriyi uygula.

Hangi sorunun hangi beceriyi tetiklediği her becerinin KENDİ `description`
alanında yazılıdır (tetikleyici kelimeler TR/EN dahil) ve bu tanımlar her
oturumda zaten yüklüdür — burada tekrarlanmaz. Yalnız iki rota sabittir:
**VARSAYILAN YOL = `piramit-sistem`** (tam analiz / K1→K5) ve **ORKESTRATÖR =
`karar-kurulu`** (nihai karar). Eşleşen her beceri, kullanıcı istemeden uygulanır.

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

Ek kural (PİRAMİT MEKANİĞİ — mekanik ayrıntı beceride, HÜKÜM burada):
Gözlemci ajanların 8 ihlali, `kiyas.py` ölçüm kuralları, `korelasyon.py` /
`usd_hedef.py` iç mekaniği, `emir_plani.py` kapıları ve çelişki turunun işleyişi
`.claude/skills/piramit-sistem/SKILL.md`'dedir. ⚠️ O gövde YALNIZ beceri Skill
aracıyla çağrılırsa bağlama girer — kanca boru hattını subprocess olarak koşturur
ve SKILL.md'yi OKUMAZ. Bu yüzden davranış hükümleri burada, her oturumda yüklü
kalır ve BAĞLAYICIDIR:
1. Eksik veriyle karar UYDURULMAZ; bütün kapılar fail-closed'dır.
2. Kritik ihlalde (UYDURMA/DAİRESEL/EKSİK_AKTARIM/MEMNUN_ETME) YÖN gösterilir,
   işlem kalitesi MÜHÜRLENİR. **Gözlemci uyarıları gizlenmez — kritik olmayanlar
   (TÜNEL/SIRADAN/ÇARPIŞMA/HAFIZA) dahil çıktının altında listelenir.**
3. Hesap-verme + kıyas başlıkları çıktının EN ÜSTÜNDE, YÖN/İŞLEM satırlarından
   ÖNCE gösterilir. Kayıt yoksa "ilk analiz" denir, geçmiş UYDURULMAZ.
4. **Emir sözleşmesi:** her karar analizinin sonunda `emir_plani.py` koşar;
   çıktı ya `<MARKET|LIMIT> <LONG|SHORT> @giriş | stop | T1 | R` ya da düşen
   kapıyla birlikte **"EMİR YOK"**tur — boş BIRAKILMAZ. Seviyeler YALNIZ ölçülen
   yapıdan; her aday `rr_denetim`den geçer, R < 1.35 reddedilir.
5. **İkinci sembol varsa** `korelasyon.py` koşar: |ρ| ≥ 0.85 → KOPYA POZİSYON,
   aynı yöndeki ikinci pozisyon bağımsız bahis DEĞİLDİR, toplam risk ×2 sayılır.
6. **Görsel/ekran görüntüsünden okunan hiçbir seviye ÖLÇÜM DEĞİLDİR:** güveni
   `gorsel_tavan` (0.50) ile tavanlıdır ve `smc_tespit` yapısıyla uyuşmazsa
   çürütülür → "GÖRSEL-MEKANİK ÇELİŞKİSİ" bayrağı düşer.

Ek kural (ZORUNLU GİRDİLER + TAZELİK — her koşuda, atlanamaz): Üç girdi birlikte
beklenir, hiçbiri sessizce atlanamaz: (1) `piramit_veri_*.json` paketi (15M+4H
kline + OI + funding + taker-LSR), (2) **CoinGlass likidasyon** long/short →
`engine/girdi/turev_ham/likidasyon.json` (türev kapsamı 0.85 → 1.00),
(3) **grafik ekran görüntüsü ya da video** → `engine/girdi/gorsel_okuma.json`.
Eksik girdi K1'de yakalanır, K4'te çelişkiye dönüşür ve çıktının EN ÜSTÜNDE
"⚠ ZORUNLU GİRDİ EKSİK" ile gösterilir; eksikle karar UYDURULMAZ. Elle gelen
likidasyon/görsel okuma hangi veriye ait olduğunu
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

Ek kural (KURUL MEKANİĞİ — mekanik ayrıntı beceride, HÜKÜM burada): 5 danışman
merceğinin tanımları, birleşik sentez çıktısının 5 parçalı yapısı ve
şişirilmiş-R denetiminin iç mekaniği `.claude/skills/karar-kurulu/SKILL.md`'dedir
(o gövde yalnız beceri Skill aracıyla çağrılırsa yüklenir).
Hükümleri BAĞLAYICIDIR: motorun tek-kaynaklı çıktısı olmayan her R
`rr_denetim.py`'den GEÇMEDEN yayınlanamaz (ŞİŞİRİLMİŞSE **R_gercekci**
kullanılır); anlatı için sayı UYDURULMAZ; akıcı anlatı otomatik "daha kaliteli"
sayılmaz (narrative-fluency yanılgısı) — başlık sayıları araç-bağımsız
aritmetikle sınanır. Bu, "serbest ayar/aşırı-uyum" panzehiridir.

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
PANEL YOKSA DA KÖRLÜK KISMEN KAPANIR: `piramit-sistem/scripts/turev_girdi.py`
CVD'yi kullanıcının KENDİ kline'ından her zaman, OI'yi anlık görüntü defterinden,
funding/LSR'yi ağ izin verirse Binance vadeli uçlarından üretir. **LİKİDASYON
OTOMATİK GELMEZ — yalnız elle panelden** (zorunlu girdi #2); gelmezse türev
kapsamı 0.85'te kalır ve bu eksiklik raporlanır. Kanal kaynakları
`piramit-sistem/SKILL.md` §"Türev kanalı" tablosundadır. Eksik kanal UYDURULMAZ —
motor kapsamı düşükse skoru VERİ YOK'a çeker ve danışman doğrulanmamış sayılır
(fail-closed).

Ek kural: Kullanıcı bir **grafik ekran görüntüsü** gönderirse (mum grafiği,
fiyat grafiği), açıkça istemese bile `grafik-calisma` SMC + Fibonacci akışıyla
analiz et; derin SMC tanımları için `forex-trading-expert` referanslarını kullan.

Ek kural (ÇİZİM — çizilecekse motor koşar, elle SVG/kod yazılmaz): Bir grafik
ÜRETİLECEKSE (kullanıcı "çiz/işaretle/grafik ver" dedi ya da seviyeleri
göstermek gerekiyor) `grafik-cizim` becerisinin `scripts/cizim.py` motoru
koşulur — matplotlib ARANMAZ (bu ortamda kurulu değil; motor sıfır bağımlılıkla
SVG üretir). Çizim mekaniği (otomatik katman, grounding testi, `emir_plani`
kutusu, `r_etiketi`) `grafik-cizim/SKILL.md`'dedir. Seviyeler elle UYDURULMAZ;
ölçülemeyen çizim atlanır ve gerekçesi raporun `uyarilar` alanına yazılır.
Grafik bir KARAR DEĞİLDİR — yön/işlem hükmü yine `piramit-sistem`/`karar-kurulu`
sentezinden gelir; çıktı `SendUserFile` ile gönderilir.

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
