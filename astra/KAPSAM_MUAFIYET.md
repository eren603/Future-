# Kapsam muafiyetleri — v1.3 → v1.4 komut metni

`astra/tests/test_rule_coverage.py` HİÇBİR sınıflandırıcı kullanmıyor: envanter v1.3 komut
metninin BÜTÜN cümleleridir. Her cümlenin en ayırt edici kelimesi v1.4'te aranır; Türkçe
eklendiği için gövde (ilk 6 karakter) eşleşmesi de sayılır; ikisi de tutmazsa içerik
kelimelerinin en az %60'ı aranır. Hiçbiri tutmazsa cümle KAPSANMAYAN sayılır ve burada
SINIFIYLA yazılmak zorundadır.

Neden sınıflandırıcı yok: dört denetim üst üste aynı kusuru buldu ve her seferinde sebep
aynıydı — hangi cümlenin "kural" sayılacağına bir şey KARAR VERİYORDU ve o kararın kör
noktası vardı. Elle kelime listesi "göstermez/doğrulamaz/kaydetme/bitirme/koru"yu kaçırdı;
ek tabanlı desen gereklilik kipini ("-malıdır/-meli") ve uzunluk sınırının altındaki
cümleleri kaçırdı. Her yama bir sonraki kör noktayı üretti.

**Beşinci turda kapatılan asıl açık:** bu dosyanın ÖNCEKİ hâli 118 kalemi şablon
gerekçelerle ("v1.3'e özgü açıklayıcı cümle") muaf tutuyordu — yani testten çıkarılan
sınıflandırıcı, düzyazı kılığında buraya taşınmıştı. Artık her kayıt bir SINIF taşır ve
`test_each_waiver_class_is_mechanically_true` o sınıfı cümlenin kendisinden YENİDEN
TÜRETİR; sınıfı tutmayan muafiyet testi DÜŞÜRÜR. Muafiyet yazısına güvenilmiyor, denetleniyor.

Kalan 107 kalem muaf tutulmadı, **v1.4 metnine geri alındı** (16 cümle yeni yazıldı; geri
kalanı gövde eşleşmesi ve Türkçe I/İ katlama düzeltmesiyle zaten metinde olduğu ölçülerek
gösterildi).

Sınıflar (hepsi makineyle yeniden türetilir):

| Sınıf | Makinede nasıl doğrulanır |
|---|---|
| `BASLIK` | Cümlenin v1.3'teki satırı `#` ile başlıyor ya da cümle `**` ile bitiyor (bölüm başlığı, kural değil) |
| `TABLO` | Cümlenin v1.3'teki satırı `\|` ile başlıyor (tablo satırı; hükmü ayrı bir cümlede de yazılı) |
| `PARCA` | Cümle küçük harfle başlıyor (devam yan cümlesi) VE aynı satırdaki kardeş cümlelerden en az biri KAPSANMIŞ |
| `ORNEK` | Cümle "Örneğin" ile başlıyor VE aynı satırdaki kural cümlesi KAPSANMIŞ |

Ölçümün SINIRI (açıkça): bu araç SİLİNMEYİ yakalar, ANLAMI denetlemez. Bir cümle metinde
dururken anlamı tersine çevrilirse bu test bunu görmez — o denetim elle ikinci-göz işidir.
İkinci sınır: 15 karakterden kısa ya da 400 karakterden uzun cümle envantere girmez.
Üçüncü sınır: gövde eşleşmesi sabit önektir, biçimbilimsel çözümleyici değil — az eşleşme
yerine fazla eşleşme yönünde hata yapar.

## Muafiyetler (her biri sınıflı; sınıf testte yeniden türetilir)

- `d794c20b5c7a` [PARCA] — "sınırı açıkla ve yapılabilir onarımı sürdür." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `29d7f957e4a5` [BASLIK] — "**A.2 Model/Max ayarını istekten ayır**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `3d773651bd2d` [PARCA] — "engellenen eylemin yeniden adlandırılmış kopyası olamaz." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `86a64042308e` [PARCA] — "değişmeyen kanıtı somut ihtiyaç olmadan yeniden üretmez." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `ce037aca94a9` [PARCA] — "gerçek bütçe/erişim engelinde tamamlananları ve kalanları açıkça tesl…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `5fbf7a5bdcf5` [PARCA] — "aşağıdaki kaynak, karşılaştırma ve inceleyici kapıları gerçek çağrı y…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `e6b2c2b05783` [PARCA] — "hazır olanları kullan;" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `a41f397c5dfa` [PARCA] — "ardından bu yönlendirme katmanını ve görevle ilgili konu satırlarını …" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `b4cbc28c82f7` [PARCA] — "başka konuların taranması için somut ihtiyaç olsun." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `23570f18861b` [BASLIK] — "**0.1 Görevden yetenek çıkarma ve kör nokta taraması**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `64f9a504ab8c` [ORNEK] — "Örneğin vadeli piyasa için öğrenen yazılım;" "Örneğin" ile başlayan ÖRNEK; kural değil örnekleme. Dayandığı kural cümlesi aynı satırda ve v1.4'te kapsanmış durumda.
- `a16d03d96439` [PARCA] — "need_id, topic_id, somut yetenek, kabul kanıtı, kritik/isteğe bağlı d…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `fc6ea39ee542` [PARCA] — "gerçekten ikiden fazla paket gerekiyorsa sınırı sessizce aşma." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `0330ef4e936f` [PARCA] — "somut yeteneğe uygunluk → gerçek erişim ve hesap kapsamı → kanıtlanmı…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `74adbc2a632b` [PARCA] — "metindeki yasak tek başına erişim sınırı değildir." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `53457f7c1d93` [PARCA] — "böylece politika özeti hangi araç sınırının kullanıldığını da izleyeb…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `b5a4ed610757` [BASLIK] — "**0.6 İzlenebilir yönlendirme sonucu ve devam kuralı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `3776158ed383` [PARCA] — "görev/kapsam kimliği, eşlenen konu kimlikleri, gerekli yetenekler, me…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `93a33720d68c` [PARCA] — "hangi araçlar neden seçildi, yeni bağlantı gerekiyorsa hangisi ve ney…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `72621cf8c1f3` [BASLIK] — "Çalışma modu ve gerçek başlangıç koşulları**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `c307294272c0` [PARCA] — "doğrudan analiz, gerçek araçlarla yapılabilen kontroller ve eksikleri…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `51a7f7b0b639` [PARCA] — "mevcut tek-model analizini sürdürebilirsin." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `c61b47ec98eb` [PARCA] — "v1.3 yerel TrustedHost ve gerçek OpenAI Responses inceleyici taşıma a…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `2df5b28791ec` [PARCA] — "görünürlük yukarıdaki tek alan sözleşmesiyle belirlenir." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `4ecbe04da85e` [PARCA] — "gereksiz boşluksuz JSON;" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `73c75be74b21` [PARCA] — "scope_id görevdeki kapsam kimliğidir." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `b980d6f01fab` [PARCA] — "- math ya null'dır ya da `expression` ve `value` metinlerini içerir." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `4c8130cb09e4` [PARCA] — "çok parçalı görev zamanlayıcısı içermez." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `e9252ae81a5a` [BASLIK] — "Tek-yazımlı kayıt ve tekrar davranışı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `94dff095cbc8` [PARCA] — "retrieved_at erişim zamanıdır;" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `a731b089694e` [PARCA] — "action, owner, guard_metric, kill_rule, user_cost, residual_risk ve d…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `4b8ae75d3f86` [PARCA] — "görev/politika sözleşmesi, phase_digest, candidate_digest, source_reg…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `298c87cfb504` [PARCA] — "candidate_review_passed, coverage_review_passed, numeric_inventory_co…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `5555b9ba257d` [PARCA] — "evrensel “iki link her şeyi doğrular” kuralı kullanma." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `ab753ac040fc` [PARCA] — "ham değer, dönüşüm ve ortak değer bağı korunsun." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `ea8174822ba5` [PARCA] — "v1.3 Controller.finalize, TrustedHost aracılığıyla sözleşmedeki karşı…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `59ae17b14595` [PARCA] — "işçilere veya dosya/günlüklere yazılmaz." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `764ef452ec11` [PARCA] — "ret, timeout, kesik/bozuk yanıt, model/ayar uyuşmazlığı, yeniden kull…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `2d504c28193b` [PARCA] — "olgusal doğruluk garantisi değildir." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `ba3772afabd1` [PARCA] — "ondan yeni değer türetiliyorsa ayrıca hesaplanır." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `ea5e75b9eae5` [PARCA] — "ondalık/tam sayı literal'leri, bilimsel gösterim, parantez, tekli +/−…" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `de7a11379008` [PARCA] — "özgün kaynak token'ından tam rasyonel olarak ayrıştırılır." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `7e35ed445540` [ORNEK] — "Örneğin `0.1+0.2` için `3/10`;" "Örneğin" ile başlayan ÖRNEK; kural değil örnekleme. Dayandığı kural cümlesi aynı satırda ve v1.4'te kapsanmış durumda.
- `b2018d4a748a` [PARCA] — "host son cümleyi `expression = exact` biçiminde üretir." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `a42c4104924d` [PARCA] — "proof_id, kendi alanı dışındaki kayıt içeriğinin hash'idir." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `eb7061936e75` [PARCA] — "bilimsel gösterim üssünün mutlak değeri en çok 1000;" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `72927f7b11d3` [PARCA] — "aritmetik örneğini yapılmış simülasyon gibi sunma." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `6a67e4451d3e` [PARCA] — "açık çelişki/iddia kalmamış;" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `69e0473dbcff` [PARCA] — "uygulanmış veya onaylanmış karar uydurma." Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `ad9ab97a6c3e` [BASLIK] — "Promptun kabul örnekleri ve ölçüm**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `8b14b698e435` [PARCA] — "gerçek inceleme ve kullanılabilen araçlar;" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `d76f6bb5d685` [PARCA] — "hesap aracı yoksa çalıştırılmış iddiası yok |" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `3fa8af0602be` [PARCA] — "engellenen işçi tekrar çağrılmaz |" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
- `370136efc896` [PARCA] — "protokol yetkisi verilmez |" Noktalı virgül/iki nokta ile bölünmüş DEVAM YAN CÜMLESİ; küçük harfle başlar, tek başına hüküm kurmaz. Aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış — test bu koşulu yeniden türetir.
