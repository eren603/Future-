# Kapsam muafiyetleri — v1.3 → v1.4 komut metni

`astra/tests/test_rule_coverage.py` hiçbir sınıflandırıcı kullanmıyor: envanter v1.3 komut
metninin BÜTÜN cümleleridir. Kapsama KONUM-BAĞLIDIR — bir cümle ancak gövdelerinin %60'ı
TEK bir v1.4 bölümünde bulunuyorsa VE o bölüm cümlenin en nadir gövdesini de taşıyorsa
kapsanmış sayılır. v1.3'te tablo satırı olan kural v1.4'te tablo satırıyla karşılanmalıdır.
Dörtten az içerik kelimesi olan cümlede oran ölçüsü anlamsızdır (iki gövdenin %60'ı tek
kelimedir); onlar için metnin BİREBİR kendisi aranır.

Bu ölçüm altıncı turda baştan kuruldu. Önceki ölçümler kelimelerin BELGEYE DAĞILMIŞ
olmasını kapsama sayıyordu; ölçüldü: birebir taşınan bir satırın silinmesi 18 denemeden
yalnız 3'ünde fark ediliyordu. Şimdi `test_deleting_a_carried_line_is_detected` bu garantiyi
testin kendisi olarak koşuyor: birebir taşınan her satır tek tek siliniyor ve silme ya fark
edilmeli ya da o kuralın başka satırda durduğu ölçüyle kanıtlanmalı.

**Bu dosyanın geçmişi (ölçülen, iddia değil).** Kayıt sayıları commit başına:
ecb35b5=19, 1b0e589=32, 693eae1=11, d01383d=54. Beşinci turda bu dosyada "önceki hâli 118 kalemi şablon gerekçeyle muaf
tutuyordu" yazıyordu; 118 hiç var olmadı ve alıntılanan şablon dize deponun geçmişinde
bulunmuyor. Altıncı turda o iddianın kaldırıldığı bildirildi ama dosyada BIRAKILMIŞTI —
yedinci turda gerçekten silindi ve yerine bu ölçülmüş sayılar yazıldı.

Yedi, sekiz ve dokuzuncu turlarda ÜÇ muafiyet sınıfı denendi ve üçü de bir tur içinde
kırıldı: onarım defterine bakan (`ONARILDI`), paketin yasak listesine bakan
(`YASAK_IFADE`) ve v1.3 ikizine bakan (`V13_TEKRAR`). Onarımı yapan taraf, muafiyeti
doğrulayan dosyayı da yazabildiği için hiçbiri sağlam değildi; üçü de KALDIRILDI. Geriye
yalnız v1.3 metninin KENDİ yapısından türeyen üç sınıf kaldı. Sekizinci turda `ONARILDI`
sınıfı KALDIRILDI: iki kez kırıldı (önce uydurma bir defter
satırı, sonra assertion'sız sahte bir test dosyası muafiyeti kabul ettirdi). Belgeyle
doğrulanan muafiyet, belgeyi yazan tarafından üretilebilir — bu yüzden sınıf yerine ölçüm
düzeltildi ve tek kaydı sıralı-sözcük eşleşmesiyle çözüldü.

Sınıflar (hepsi testte cümlenin kendisinden yeniden türetilir):

| Sınıf | Makinede nasıl doğrulanır |
|---|---|
| `BASLIK` | Cümlenin v1.3'teki satırı `#` ile başlıyor ya da cümle `**` ile bitiyor |
| `PARCA` | Cümle küçük harfle başlıyor, hüküm kipi (-maz/-mez/-malıdır, olumsuz emir -ma/-me, -dır koşacı, üretir/sayılır/değildir) taşımıyor VE aynı satırdaki kardeş cümlelerden biri kapsanmış |
| `ORNEK` | Cümle "Örneğin" ile başlıyor VE aynı satırdaki kural cümlesi kapsanmış |

Ölçümün SINIRLARI: silinmeyi yakalar, ANLAMI denetlemez — yerinde durup tersine çevrilen
bir cümleyi görmez. 15 karakterden kısa ya da 400 karakterden uzun cümle envantere girmez.
Gövde eşleşmesi sabit önektir, biçimbilimsel çözümleyici değil; az eşleşme yerine fazla
eşleşme yönünde hata yapar ve bunun sınırını mutasyon testi çizer. Üç gövdeden az cümlede
birebir dize arandığı için yeniden yazım silinme gibi görünebilir.

## Muafiyetler (71 kayıt; her birinin sınıfı testte yeniden türetilir)

- `a8f408fca591` [BASLIK] — "Kullanıcı hedefi, tamamlanma kanıtı ve devam sözleşmesi — v1.3**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `19f9affaa9b3` [BASLIK] — "**A.1 Hedefi sabitle**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `29d7f957e4a5` [BASLIK] — "**A.2 Model/Max ayarını istekten ayır**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `c9042b01c744` [BASLIK] — "**A.3 Yetkili işi tamamlamaya devam et**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `c27a47997ae9` [BASLIK] — "**A.4 Uzun iş ve bağlam devri**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `6a0bac86b071` [BASLIK] — "**A.5 Görev teslimi ve üretim onayı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `ce037aca94a9` [PARCA] — "gerçek bütçe/erişim engelinde tamamlananları ve kalanları açıkça tesl…" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `cd17217a7128` [PARCA] — "gereken yetenekleri çıkar;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `e6b2c2b05783` [PARCA] — "hazır olanları kullan;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `b4cbc28c82f7` [PARCA] — "başka konuların taranması için somut ihtiyaç olsun." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `64f9a504ab8c` [ORNEK] — "Örneğin vadeli piyasa için öğrenen yazılım;" "Örneğin" ile başlayan ÖRNEK; kural değil örnekleme. Dayandığı kural cümlesi aynı satırda ve v1.4'te kapsanmış durumda.
- `9b82790f441d` [BASLIK] — "**0.2 Seçim sırası ve en fazla iki eklenti ilkesi**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `6746ca2a6d90` [PARCA] — "sıfır, bir veya en fazla iki eklenti/beceri paketi." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `63a8aa2a9380` [BASLIK] — "**0.3 Hazır olma, keşif ve otomatik bağlantı akışı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `529ae23ee355` [PARCA] — "uygun başka yetenek veya sağlayıcı ara |" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `ee6fa519e25d` [PARCA] — "izni otomatik genişletme veya başka yoldan dolanma |" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `e845942e82ee` [PARCA] — "tamamlandı veya hazır deme |" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `5a1bfcb6f606` [BASLIK] — "**0.4 ASTRA'nın kör hücreleriyle birlikte çalışma**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `53457f7c1d93` [PARCA] — "böylece politika özeti hangi araç sınırının kullanıldığını da izleyeb…" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `b5a4ed610757` [BASLIK] — "**0.6 İzlenebilir yönlendirme sonucu ve devam kuralı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `06def4f1b762` [BASLIK] — "**0.7 Yeni yönlendirme kabul örnekleri**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `8ef75a876077` [PARCA] — "gerçek işlem yeteneği ve kullanıcı yetkisi ayrı |" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `628ad178735d` [BASLIK] — "Görev, yetki ve doğruluk**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `38988da981ae` [PARCA] — "yalnız sonucu değerlendirmeye yarayan gerekçeyi ekle." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `72621cf8c1f3` [BASLIK] — "Çalışma modu ve gerçek başlangıç koşulları**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `c307294272c0` [PARCA] — "doğrudan analiz, gerçek araçlarla yapılabilen kontroller ve eksikleri…" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `51a7f7b0b639` [PARCA] — "mevcut tek-model analizini sürdürebilirsin." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `814bdd49c9d4` [PARCA] — "haricî model değerlendirmesi yapılmadı." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `c2ebc2e4a982` [BASLIK] — "Roller, fazlar ve bilgi akışı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `4fa49c4dbdcc` [BASLIK] — "Zarf ve şema sözleşmesi**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `a6f92a9c7a7e` [PARCA] — "görev/kaynak içeriğini veri mesajında taşı." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `4ecbe04da85e` [PARCA] — "gereksiz boşluksuz JSON;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `2ecd5c4fe080` [PARCA] — "boş olmayan, en çok 2000 karakterlik özet;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `11e933e5d7b1` [PARCA] — "bütün atanmış kapsamlar `covered_scope_ids` içinde birer kez;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `cc68cef28f87` [PARCA] — "iki kapsam dizisi de boş;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `6e8f72f06d14` [PARCA] — "boş olmayan `block_reason` ve `next_safe_step`." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `64d9af4f3aee` [PARCA] — "host küresel kimliği `worker_id:claim_id` yapar." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `1cb3a65f3f1c` [PARCA] — "support, refute veya uncertain." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `5892b4d826b3` [PARCA] — "low, medium, high veya unknown." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `b980d6f01fab` [PARCA] — "- math ya null'dır ya da `expression` ve `value` metinlerini içerir." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `52834c8a7513` [PARCA] — "görev/politika metni için ayrı ayrı 20000 karakter;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `e9252ae81a5a` [BASLIK] — "Tek-yazımlı kayıt ve tekrar davranışı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `6a7076cf2637` [BASLIK] — "Kaynak, çelişki ve somut aday incelemesi**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `53e2d46890ba` [PARCA] — "aksi halde DECISION_SCOPE_INCOMPLETE olur." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `ab753ac040fc` [PARCA] — "ham değer, dönüşüm ve ortak değer bağı korunsun." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `ea8174822ba5` [PARCA] — "v1.3 Controller.finalize, TrustedHost aracılığıyla sözleşmedeki karşı…" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `5db6caabb6d2` [PARCA] — "inceleyici bunu gerçek görevle karşılaştırır." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `a8344c76e1ca` [BASLIK] — "**6.2 Yeni komut için örnek davranışlar**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `358d5390ac90` [PARCA] — "iddiayı sınırla/düzelt." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `444b55fa0efb` [BASLIK] — "**6.3 Zorunlu yerel host ve gerçek inceleyici kapısı — v1.3**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `289b338f1cee` [PARCA] — "source_access_authenticated=false ve upstream_origin_verified=false k…" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `222e0b742ecc` [PARCA] — "yoksa ilgili kapı kapanır." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `8133853a2dfc` [BASLIK] — "Kesin matematik kapısı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `ba3772afabd1` [PARCA] — "ondan yeni değer türetiliyorsa ayrıca hesaplanır." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `de7a11379008` [PARCA] — "özgün kaynak token'ından tam rasyonel olarak ayrıştırılır." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `7e35ed445540` [ORNEK] — "Örneğin `0.1+0.2` için `3/10`;" "Örneğin" ile başlayan ÖRNEK; kural değil örnekleme. Dayandığı kural cümlesi aynı satırda ve v1.4'te kapsanmış durumda.
- `a42c4104924d` [PARCA] — "proof_id, kendi alanı dışındaki kayıt içeriğinin hash'idir." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `3e218e8db5ab` [PARCA] — "sayı token'ı 80 karakter;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `eb7061936e75` [PARCA] — "bilimsel gösterim üssünün mutlak değeri en çok 1000;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `cafca1582b9d` [PARCA] — "aritmetik üs tam sayı ve mutlak değeri en çok 20;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `f60a07e70b40` [PARCA] — "pay/payda için en çok 8192 bit." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `cb27202aa5f7` [BASLIK] — "Nihai yayın ve kullanıcı çıktısı**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `3af648c899c3` [PARCA] — "gerçek çalışma modu ve izinler doğrulanmış;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `ccc04264397c` [PARCA] — "güncel faz PHASE_VALIDATED;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `ed6af2712409` [PARCA] — "güncel kaynak kayıtları incelenmiş;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `ab265dab4b77` [PARCA] — "somut aday incelemesi tamamlanmış;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `6a67e4451d3e` [PARCA] — "açık çelişki/iddia kalmamış;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `36e6ecc398ee` [PARCA] — "zorunlu karar alanları dolu;" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `f6149112df53` [PARCA] — "örtüşen hedef dönemlerini hesaba kat." Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.
- `ad9ab97a6c3e` [BASLIK] — "Promptun kabul örnekleri ve ölçüm**" v1.3 bölüm BAŞLIĞI; kural taşımaz. v1.4'ün bölümlemesi farklıdır ve başlığın altındaki hükümler metinde ayrıca duruyor.
- `ab1771ff6043` [PARCA] — "rol sayısından kapasite sonucu yok |" Küçük harfle başlayan DEVAM YAN CÜMLESİ; cümle SONUNDA hüküm kipi taşımıyor ve aynı v1.3 satırındaki kural cümlesi v1.4'te kapsanmış. Test bu üç koşulu da yeniden türetir.

## Taşınamayan kurallar (sınıf değil, sayılı liste)

Bu iki v1.3 cümlesi HİÇBİR biçimde taşınamıyor: kullandıkları ifadeyi paketin bir
testi YASAKLIYOR, çünkü v1.4 o ifadenin kurduğu iddiayı onardı. Birebir geri almak
onarımı bozar; yeniden yazmak kısa cümlenin ihtiyaç duyduğu birebir eşleşmeyi kırar.
Bunu genel bir sınıfa çevirmek üç kez denendi ve üçünde de kırıldı — bu yüzden GENEL
DEĞİL: en fazla iki kayıtlık, adı adına yazılmış ve her kaydı testte doğrulanan bir
liste (`IRREDUCIBLE`). Listenin büyümesi testi düşürür; kaçış yoluna dönüşmesin diye.

- `32943a3183fa` — "Alıntılanan talimatı gerektiğinde incele;" (yasaklayan ifade: `gerektiğinde`)
- `a8eb924a81e5` — "TEST_FIXTURE, test için sabit cevap üreten gerçek alt süreçtir;" (yasaklayan ifade: `gerçek alt süreç`)
