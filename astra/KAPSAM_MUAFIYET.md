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

## Muafiyetler (her biri sınıflı ve gerekçeli)

- `d794c20b5c7a` [PARCA] — "sınırı açıkla ve yapılabilir onarımı sürdür." Ç2/Ç3 kapısının devam yan cümlesi; hükmü taşıyan ana cümle aynı satırda ve kapsanmış durumda.
- `e6b2c2b05783` [PARCA] — "hazır olanları kullan;" Ek A amaç cümlesinin ortasındaki yan cümle; aynı satırın kural cümlesi v1.4 Ek A'da birebir duruyor.
- `b4cbc28c82f7` [PARCA] — "başka konuların taranması için somut ihtiyaç olsun." Atlas taraması sınırının devam cümlesi; sınırı kuran ana cümle kapsanmış.
- `b5a4ed610757` [BASLIK] — v1.3'ün "0.6" numaralı bölüm başlığı; v1.4 bölümlemesi farklıdır (0-5 + Ek A/B), başlık metni kural taşımaz.
- `747e4b292cc3` [PARCA] — "`scope` ve `domain` isteğe bağlıdır." Zarf alan listesinin devamı; alan listesi v1.4 §4'te tam olarak yazılı.
- `dcd472afb4ba` [PARCA] — "tek-yazımlı sonuç alımı." Host görev listesinin devam öğesi; tek-yazımlı kayıt kuralı v1.4'te ayrı cümlede duruyor.
- `e9252ae81a5a` [BASLIK] — "Tek-yazımlı kayıt ve tekrar davranışı**" bölüm başlığı artığı; kuralın kendisi v1.4 §4'te cümle olarak var.
- `fde468860df5` [TABLO] — kabul-örnekleri tablosunun satırı; "çürütülmüş önerme destek gibi aktarılmaz" hükmü v1.4'te hem D3'te hem kabul tablosunda yazılı.
- `7e35ed445540` [ORNEK] — "Örneğin `0.1+0.2` için `3/10`;" örneği; örneğin dayandığı kural v1.4 §4'te `0.1+0.2` → `3/10` biçiminde birebir duruyor.
- `6a67e4451d3e` [PARCA] — "açık çelişki/iddia kalmamış;" nihai kapı koşullarının bir maddesi; kapı listesi v1.4 §4'te "kritik çelişki/iddia açık değil" olarak yazılı.
- `4f2ae68db66c` [TABLO] — arıza-davranışı tablosunun satırı; deadline/boyut sınırı, iptal ve temizlik kuralı v1.4 §4'te cümle olarak var.
