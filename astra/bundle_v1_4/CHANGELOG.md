ASTRA v1.3 değişiklik kaydı

- Controller.finalize artık TrustedHost olmadan başarı üretmez.
- Donmuş görev/kapsam/karşılaştırma sözleşmesi ve gerçek dosya snapshot yakalama eklendi.
- compare_table, gerçek finalizer yolundaki zorunlu çağrıya bağlandı.
- Kaynak metinleri, bütün kartlar, hesap kanıtları, kıyas sonuçları ve somut aday inceleyiciye gönderiliyor.
- İnceleyici yanıtı request_digest, model/effort ve iddia/kıyas kapsamına bağlanıyor.
- Eski kullanıcı tarafından sağlanan review alanları yalnız ek ret koşulu; tek başına onay veremez.
- Olumsuz, eksik, eski, yanlış alıntılı veya yeniden kullanılan inceleme sonucu kapatıyor.
- Kaynaklar inceleme öncesi ve sonrasında tekrar kontrol ediliyor.
- Gerçek OpenAI Responses inceleyici adaptörü ile CLI ve açık sentetik demolar eklendi.
- TEST_FIXTURE'ın EXTERNAL_MODEL diye yeniden etiketlenmesi reddediliyor.
- 79 mevcut test yeni host arayüzüne uyarlandı; 26 host/entegrasyon ve 8 HTTP taşıma testi eklendi.
- 113 test başarılı; dört gerçek CLI senaryosu beklenen sonucu verdi.

Test anlamı: sabit test inceleyicileri verilen kararın doğru kapıda uygulanmasını doğrular;
yeni bir LLM'nin anlamsal hatayı bağımsız olarak bulabildiğini kanıtlamaz. HTTP testleri
sağlayıcı yanıt örneklerini kullanır. Canlı API çağrısı ve model değerlendirmesi yapılmadı.
Üretim izolasyonu, upstream web kaynağı kimlik doğrulaması ve kalıcı zamanlayıcı kurulmadı.
