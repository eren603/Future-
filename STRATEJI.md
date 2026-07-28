# İŞLEM STRATEJİSİ — BTCUSDT / ETHUSDT (karar-destek düzeni)

> Nasıl üretildi: 4 bağımsız tasarım ajanı (risk/para-yönetimi, icra/mikroyapı,
> süreç/disiplin, muhalif/sınırlar) + her taslağa 1 düşman denetçi = 8 ajan.
> Denetçiler 25 ihlal yakaladı (uydurma oran, aritmetik hata, etiketsiz kesinlik,
> seçici kanıt); aşağıdaki metin yalnız DÜZELTİLMİŞ maddelerden sentezlendi.
> Dayanak dosyaları: eth_profil.json, gorev.json, ajanA/B/C sonuçları,
> sentez_hesap.json. ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.

## 0) Kenarın dürüst teşhisi (stratejinin zemini)

- Bu sistemin ölçülmüş bir "alfası" YOK: drift istatistiksel olarak sıfırdan
  ayırt edilemedi; ölçülen avantaj GEOMETRİ (bariyer mesafeleri) + DİSİPLİN
  (kapılar, fail-closed, akıbet sicili) bileşimidir. Strateji de buna göre
  kurulur: kenar üretmeye değil, kenarsızlıkta HAYATTA KALMAYA optimize edilir.
- Aritmetik kimlik (denetçinin yakaladığı, gizlenmez): sabit kontratta
  R = hedef_mesafe / stop_mesafe. R ≥ 1.35 ⇒ hedef girişten DAİMA stopdan uzak
  ⇒ sürüklenmesiz tabanda P(stop önce) = R/(1+R) = 0.574-0.60 FAVORİDİR.
  Yani her taze emir, tabanda stop-favori doğar; işlemi taşınabilir kılan şey
  giriş SEÇİMİ (yapıya tepki) ve kayıpların sabit-küçük tutulmasıdır.
  Oturumda ölçülen "hedef-önce 0.6536-0.66785" bandı AÇIK pozisyonun KALAN
  geometrisine aitti (kalan R 0.73) — taze kurulum kanıtı olarak KULLANILMAZ.

## 1) Sermaye ve risk çekirdeği

- **Teminat daima tam 400 USD ile taşınır.** 100x borsa ayarı bir boyutlandırma
   izni değildir; gerçek kaldıraç ~14x'tir (3 ETH nominal / 400 teminat).
   Tam teminatta tampon 400/3 = 133.33 puan = stop mesafesinin 4.0 katı
   (bakım-marjinsiz teorik tavan; gerçek likidasyon bundan yakındır — borsa
   ekranından okunur). Her emirden önce borsanın likidasyon fiyatı okunur;
   |giriş − likidasyon| < 4 × 33.3333 puan ise işlem AÇILMAZ (fail-closed).
- **%25 gerçeği:** her stop 100/400 = sermayenin %25'i. Kasa yalnız 4 ardışık
   stop kaldırır. Aynı gün İKİNCİ stoptan sonra gün kapanır (politika seçimi;
   sermaye aritmetiğiyle gerekçeli). Sermaye 400'ün altına inerse 3.0 kontrat
   profili kendiliğinden GEÇERSİZDİR — kontrat düşürülmeden yeni işlem yok.
- **Tek bahis kuralı:** ρ = 0.8939-0.909 ölçüldüğü sürece BTC ve ETH aynı yönde
   TEK bahistir (risk çarpanı 2.0; iki pozisyon = 200 USDT = sermayenin %50'si
   tek senaryoda). Aynı anda en fazla BİR yönlü pozisyon; iki sinyal varsa
   yalnız biri seçilir.
- **Açık pozisyona ekleme YASAK.** Kontrat artışı sabit-USDT stopun puan
   mesafesini küçültür ve stop/ATR4H ∈ [0.8, 2.0] kurulum kapısını bozabilir;
   nominal büyüdükçe likidasyon yaklaşır. Serbest olan tek değişiklik KISMEN
   KAPATMADIR.
- **R kapısı brüt/net ayrımıyla:** hedef bandı 135-150 USDT brüt = R 1.35-1.50.
   Alt kenar 135 R_min'i SINIRDA ve yalnız brüt karşılar (komisyon/funding
   maliyeti VERİ YOK). Ölçülü likidite izin veriyorsa 150 bandı (R 1.50) tercih;
   yalnız 135'e ulaşan kurulum "SINIRDA" etiketiyle işlenir.

## 2) Hangi kurulum işleme alınır

- **Taze emir ancak O KOŞUNUN ölçümü hedef-önceyi favori gösteriyorsa alınır**
   (MC/analog ilk-geçiş yarışında p_hedef > p_stop). Ölçüm yoksa VERİ YOK →
   işlem yok. Bu, R_min kapısının ÜSTÜNE binen ek bir kapıdır: R≥1.35 geometriyi
   stop-favori doğurduğu için, dengeyi çeviren şey ölçülmüş sürükleniş + yapı
   teyididir.
- **Stop-önce-FAVORİ profil (BTC tipi: p_stop=0.5739 > p_t1=0.4261) bu kasayla
   ALINMAZ.** EV = 0.4261×2.18 − 0.5739 = +0.355R pozitif olsa bile bu
   "az-ama-büyük-kazanan" profili ancak çok denemede gerçekleşir; 4 stopluk kasa
   o varyansı taşıyamaz ve modal sonuç kayıptır. Alınacaksa (kasa büyüyünce)
   MARKET tamamen kapalı, yalnız ölçülü seviyeden LIMIT — ince +0.355R marjı
   ölçülmemiş dolum sapmalarını taşıyamaz (kovalama R'yi mekanik düşürür;
   oturumda kanıtlandı: 1.35 → 0.73).

## 3) İcra kuralları

- **LIMIT varsayılandır; MARKET yalnız fiyat giriş bölgesindeyken**
   (|giriş − fiyat| ≤ 0.1×ATR15 — emir_plani kuralı). Fiyat kovalanmaz.
- **Stop-av bayrağında stop BÜYÜTÜLMEZ, giriş KAYDIRILIR.** Stop USDT sabit
   olduğundan tek serbest değişken giriştir: bayraklı adayda giriş, stopun
   bilinen havuzun >0.25×ATR15 ötesine düşeceği seviyeye LIMIT ile çekilir;
   kaydırma R'yi 1.35 altına düşürürse aday ATLANIR.
- **Hedef:** 45-50 puan bandının içinde, yön tarafındaki EN YAKIN teyitli
    likiditenin YAKIN kenarına konur (likiditeyle yarışılmaz). Bandda teyitli
    likidite yoksa aday düşer — "R katı" uydurma hedef üretilmez.
- **Geçersizlik çizgisi:** kurulumun havuz-ötesi seviyesinde 15M GÖVDE
    kapanışı = tez bitti, çık. Fitil süpürmesi tek başına çıkış nedeni değildir
    (VARSAYIM etiketli kural — süpürme frekansı henüz ölçülmedi).
- **Dolmayan limitin ömrü:** 240 dk ya da yeni paket — hangisi önce gelirse
    emir İPTAL edilir ve yeni koşunun adayı beklenir (yapısal analoji: panel
    tazelik toleransıyla aynı pencere; VARSAYIM etiketli).
- **Tek aktif emir:** aynı anda tek bekleyen yönlü emir; dolum görülünce
    diğer semboldeki plan iptal edilir (elle — otomatik OCO kurulmaz, sistem
    karar-destektir).

## 4) Rejim filtreleri

- **Funding pozisyon aleyhine döndüğünde pozisyon BÜYÜTÜLMEZ** ve karar yeni
    koşunun akıbet+kıyas ölçümüne bırakılır. Ölçülen örnek: ETH funding
    +0.0028 → −0.0056; negatif funding + üstte yoğun likidite bloğu açık SHORT
    için squeeze YAKITI olabilir (YORUM etiketi — sayısallaştırılmadı).
- **Bayat veriyle karar YOK:** panel damgası son bardan >240 dk eskiyse açık
    pozisyon "İZLENMEYEN RİSK" olarak raporlanır; bayat panelle ne emir verilir
    ne tutma kararı alınır. Kadans: ≤4 saatte bir TAM üçlü (kline paketi +
    CoinGlass likidasyon + panel görüntüsü) — eksik kanal türev kapsamını ve
    danışman güvenini düşürür (bu koşuda OI eksiği kapsamı 0.66'da bıraktı).

## 5) Süreç döngüsü (her koşuda, sırası dokunulmaz)

- Önce HESAP VERME (önceki emrin akıbeti; tetiklenmemişe R yazılmaz), sonra
    KIYAS (yön + sürücü değişimi), en son yeni karar. "EMİR YOK" birinci sınıf
    çıktıdır — sinyal-avcılığı ve intikam işlemi yasaktır.
- **Mühür/NÖTR protokolü:** gözlemci mühürlerse ya da çelişki turu fail-closed
    NÖTR derse, hüküm piyasa hakkında değil VERİ hakkındadır: yön bilgi olarak
    okunur, emir açılmaz, mühür elle seviye uydurarak DELİNMEZ; eksik kanal
    tamamlanıp sonraki kadansta taze paket gönderilir.
- **Haftalık geriye-dönük ölçüm:** kapanan tüm emirler simule_et kurallarıyla
    derlenir (yalnız DOLAN emirler paydada; İPTAL'ler ayrı, R'siz; stop-av
    bayraklı kesit ayrı). Kıyas GEOMETRİ-EŞLİ yapılır: her emrin tabanı kendi
    giriş geometrisinden b/(a+b) ile hesaplanır; oturum bantları yalnız aynı
    kalan-geometrideki kesitle kıyaslanır. Parametre değişikliği yalnız bu
    ölçümle yapılır — anlatıyla asla.

## 6) Yasaklar (muhalif merceğin nihai listesi)

- Kenarı "alfa" diye satmak; 5.6 günlük tek-rejim arşivinden genelleme ve
  parametre ayarı; kesinlik dili (kaybetmek taban senaryodur, anomali değil).
- Marjini 100x'e göre kısıp taşımak (likidasyon stopun önüne geçer — stop
  kurguya döner); stop USDT'sini büyütmek; açık pozisyona eklemek.
- ρ ≥ 0.85 iken ikinci sembolde aynı yönlü pozisyon; canlı/otomatik emir.
- Stop-av bayrağını yok saymak da stopu kaldırmak da yasak — cevap girişten
  verilir (giriş-kaydırma maddesi).
- Ufuk/koşul etiketi olmayan olasılık aktarımı (384-bar sayısını 24-saat
  sayısı gibi sunmak dahil).

## 7) Sınırlar (stratejinin kendisi hakkında dürüstlük)

Arşiv ~5.6 gün tek rejim; analog pencereler örtüşük (güven aralıkları
olduğundan dar); dolum olasılığı modellenmedi; komisyon/funding maliyeti
VERİ YOK; süpürülme frekansı henüz ölçülmedi. Bu belge kural değil KANUN da
değildir: haftalık ölçüm döngüsü (haftalık ölçüm maddesi) hangi maddenin veriyle
güncelleneceğini söyler.
