# Kapsam muafiyetleri — v1.3 → v1.4 komut metni

`astra/tests/test_rule_coverage.py` v1.3 komut metnindeki normatif cümleleri SUFFIX
kalıplarıyla çıkarır (Türkçede kuralı ek belirler: `-maz/-mez` olumsuz geniş zaman,
`-ma/-me` olumsuz emir, ayrıca "değildir/yasak/zorunlu/gerekir/şart/koru/sakla").
Her cümlenin en AYIRT EDİCİ kelimesi v1.4'te aranır; bulunamazsa cümlenin içerik
kelimelerinin en az %60'ı aranır. İkisi de tutmazsa cümle KAPSANMAYAN sayılır ve burada
gerekçesiyle yazılmak zorundadır; yazılmazsa test düşer. Bayat muafiyet de reddedilir.

Neden suffix: üçüncü denetim, elle yazılmış bir kelime listesinin ("sayma|deme|...")
"göstermez", "doğrulamaz", "kaydetme", "bitirme", "koru" gibi TÜM sınıfları sessizce
envanter dışında bıraktığını gösterdi — o cümleler kapsanmayan sayılmıyordu bile.

Ölçümün SINIRI (açıkça): bu araç SİLİNMEYİ yakalar, ANLAMI denetlemez. Bir cümle metinde
dururken anlamı tersine çevrilirse bu test bunu görmez — o denetim elle ikinci-göz işidir.
İkinci sınır: bir cümle 40 karakterden kısa ya da 400 karakterden uzunsa envantere girmez.

## Yeniden yazılmış / yapısal olarak karşılanmış

- `7f93ed5868a1` — D8'de şu sözlerle geçiyor: "Kabul ölçütleri çıktı GÖRÜLDÜKTEN sonra başarı elde etmek amacıyla GEVŞETİLMEZ."
- `4286766bfd7c` — D7.1'de: "başka bir yapılandırmayla çalışıldıysa sonuç 'hedef model testi' diye KAYDEDİLMEZ."
- `2f057904e242` — Ç1'de karşılanıyor: yoruma bağlı olmayan iş bitirilir, rutin tercih için soru sorulmaz, varsayım yazılır ve iş sürer.
- `7a9b1650fd56` — §2 bağlam devri paragrafında: "Kayıt yoksa önceki iş yapılmış varsayılmaz."
- `1c8f9dcbc985` — Ek A'da: "'kurulu/görünür' kaydı bu oturumda hazır araç kanıtı değildir."
- `a41f397c5dfa` — Okuma sırası talimatı; v1.4'te Ek A'nın kendisi koşullu bölüm olarak işaretli ("yalnız görev gerektiriyorsa"), ayrı bir okuma-sırası cümlesi gerekmiyor.
- `e0a2ea456500` — Ek A'da: "Bütün atlas, bütün beceri yönergesi ve bütün test kodu her işçiye YÜKLENMEZ."
- `23570f18861b` — Bölüm BAŞLIĞI, kural değil. v1.4'te aynı içerik Ek A'daki boşluk taraması tablosuyla karşılanıyor.
- `af73f3c5f9d5` — Ek A READY kanıt listesinde: "doğru ürün kimliği, kurulu/etkin, çağrılabilir araç ya da görünür beceri, gerekli hesap bağlantısı, izin."
- `59a2cc26267f` — Ek A'da: "Bir aracın bağlanmış olması gerçek izolasyon kanıtı OLUŞTURMAZ."
- `c02765ee45ba` — Ek A'da: "GPU, süre, bellek, kütüphane desteği VARSAYILMAZ."
- `b5a4ed610757` — Bölüm BAŞLIĞI, kural değil; içeriği Ek A'daki TOOL_ROUTE kaydı ve §3 Ç6 astra_records bloğuyla karşılanıyor.
- `e1b5e4d18a3c` — §5'te: "Gizli düşünce zinciri istenmez ve yayımlanmaz; 'neyi sınadığın' yazılır, 'ne düşündüğün' değil."
- `da757582053c` — Ç6'da: "Yasak olan yalnız 'konsey çalıştırıldı' rol konuşması ve APPROVED iddiasıdır."
- `d28f3cc4cff6` — Cümle bir LİSTE GİRİŞİDİR; listenin kendisi §4'te REAL_ISOLATION başlangıç kaydı olarak birebir taşınıyor.
- `735c0f199a17` — Aynı listenin bir maddesi; §4 REAL_ISOLATION kaydında "gerçek model/sağlayıcı/sürüm makbuzu" olarak geçiyor.
- `c61b47ec98eb` — v1.3 SÜRÜM CÜMLESİ (paketin ne içerdiğini anlatır), normatif kural değil; v1.4'ün kendi karşılığı §4'te ve README'de.
- `7f0fc98d78da` — §4'te: "işçi kimliğinde ve yerel iddia kimliğinde `:` KULLANILMAZ."
- `00c0b887edd4` — §4 kayıt paragrafında: "İşçinin sahip olduğu DEĞİŞEBİLİR nesne kayıt diye saklanmaz."
- `a5610ce18332` — Kabul örnekleri TABLOSUNDAN bir satır; v1.4'te aynı davranış §4 kayıt/tekrar paragrafında (bozuk zarf INVALID) yazılı.
- `0bf6c540ca4c` — §4'te ret koduyla: "kapsamı eksik karar `DECISION_SCOPE_INCOMPLETE` ile kapanır" + hemen ardından bu eşleşmenin sınırı.
- `7a2139284ea9` — ADIM 3'te: "Arama özeti, sayfa başlığı, üretici beyanı ya da aynı asıl kaynağın kopyaları bağımsız doğrulama değildir."
- `892472d71b45` — Araştırma sözleşmesinde: "Eksik hücre sıfırla ya da tahminle DOLDURULMAZ."
- `a8aa7aee9031` — Araştırma sözleşmesinde: "Nitel değerlendirme ölçülmüş sayısal puana DÖNÜŞTÜRÜLMEZ."
- `deea6ac8d3e1` — ADIM 7'de: MODE, FINAL_STATUS ve TASK_STATUS birlikte yazılır ve TASK_STATUS gereksinim durumlarından türetilir.
- `fde468860df5` — Kabul örnekleri TABLOSUNDAN bir satır; kural D3'te ("support/refute/uncertain yönü ve koşullar çıktıya kadar korunur") duruyor.
- `0c22e1589ac7` — §4'te: "bu, upstream web sitesinin kimlik doğrulaması DEĞİLDİR (`source_access_authenticated=false`...)."
- `88518aef1299` — §4'te: "API anahtarı yoksa fixture'a sessiz geçiş yoktur."
- `e4e163e32d80` — Ek B'de: "Öncü sayılan veri için tahmin anında erişilebilirlik ve katkı hipotezi deneyle sınanır."
- `79ea168f8f8b` — Ek B'de: "sonradan öğrenilen bilgi geçmiş karara sızdırılmaz."
- `11d60490de47` — Ek B'de: "eğitim/doğrulama/test zaman sırasıyla ayrılır; ayrılmış test verisi parametre seçiminde kullanılmaz."
- `d7a67d182f8f` — Kapanış paragrafında: "Model çıktısının her çağrıda aynı olacağı varsayılmaz."

## Kapsam dışı bırakılan

(Şu an yok. Bu bölüm boş kaldığı sürece v1.3'ün hiçbir kuralı bilerek dışarıda
bırakılmamış demektir; buraya bir kayıt girerse gerekçesi ayrıca yazılır.)
