ASTRA tamir şartnamesi v1.4

Girdi: astra_tamir_v1_3.md (komut metni + paket) ve bu oturumda ARTEFAKTTAN
üretilen bulgular (`astra/BULGULAR_kendi_okuma.md`, `astra/bulgular_ham_isakisi.json`,
`astra/BAG_HARITASI.md`).
Teslimat: onarılmış komut metni ve çalıştırılabilir paket; her onarım bir bulgu
kimliğine bağlı.

Kabul: host yokken başarı yok; zorunlu karşılaştırmalar gerçek `compare_table`
çağrısından geçer; kaynakları host okur ve yolun hiçbir bileşeni sembolik bağ
olamaz; somut aday, bütün kartlar ve kaynak İÇERİKLERİ gerçek inceleyici sürecine
girer. Satır/kaynak/aday/iddia bağları korunur. Eksik, olumsuz, kapsamı eksik veya
yeniden kullanılan inceleme, yanlış alıntı, timeout ve bozuk çıktı kapıyı kapatır.
Durum beyan edilmez, gereksinim defterinden türetilir. Test inceleyicisi canlı
model diye sunulmaz.

v1.4'ün eklediği kabul ölçütleri
- Belirsizlik cezalandırılmaz: kritik olmayan ve karara girmeyen `uncertain` kart
  yayını kapatmaz; kritik olan ya da karara seçilen kapatır.
- BLOCKED en az iki deneme kaydı ister; `owner` yer tutucusu reddedilir.
- `finalize` tek çalışır; inceleme yanıtı tekrar kullanılamaz.
- `kind="TOOL"` içerik özetine bağlanır; bağın SINIRI (args_digest/exit_status
  doğrulanmaz) belgede yazılıdır.
- Zarf kaynak içeriğini taşır ve tel sınırına karşı ölçülür.
- İnceleme bütçesi çağrıdan ÖNCE denetlenir; sabit ÖLÇÜLMÜŞTÜR.
- Komut metni sınanan bir artefakttır (`tests/test_command_text.py`).

Prompt senaryoları: olağan kıyas; eksik ölçüm; farklı yöntem; sayıyı yanlış ölçüt
diye yorumlama; olumsuzlama; kaynaktan talimat saldırısı; genel üstünlük; eksik
karşı kanıt; serbest metinde doğrulanmamış sayı; belirsiz kartın karara seçilmesi;
kanıtsız VERIFIED gereksinim; tele sığmayan iddia kümesi. Yerel fixture sonuçları
bu davranışların canlı modelde ölçülmüş başarısı DEĞİLDİR.

Hedef inceleyici: OpenAI Responses API, gpt-6-astra, desteklenen effort.
Canlı test: NOT_RUN — bu ortamda OPENAI_API_KEY yok ve developers.openai.com
egress engelli. Sıcaklık gönderilmez. Model/effort makbuzu olmadan hedef model
testi denmez. Sağlayıcıya gönderilen şema uzunluk anahtarlarından arındırılmış
taşıma şemasıdır; sunucunun tam şemayı kabul edip etmeyeceği BİLİNMİYOR ve bu
belge onu bildiğini iddia etmez. Üretim izolasyonu, kaynak web sitesinin köken
doğrulaması ve genellenebilir doğruluk garantisi verilmez.
