ASTRA tamir şartnamesi v1.3

Girdi: astra_tamir_v1_2.md ve önceki gerçek denetim bulguları.
Teslimat: nihai tamir edilmiş komut ve çalıştırılabilir paket.

Kabul: host yokken başarı yok; zorunlu karşılaştırmalar gerçek compare_table
çağrısından geçer; kaynakları host okur; somut aday ve kaynaklar gerçek inceleyici
sürecine girer. Satır/kaynak/aday/iddia bağları korunur. Eksik, olumsuz, kapsamı
eksik veya yeniden kullanılan inceleme, yanlış alıntı, timeout ve bozuk çıktı
kapıyı kapatır. Test inceleyicisi canlı model diye sunulmaz. Komut, kod, testler
ve gerçek sonuçları taşıyan dosyalar teslim edilir.

Prompt senaryoları: olağan kıyas; eksik ölçüm; farklı yöntem; sayıyı yanlış ölçüt
diye yorumlama; olumsuzlama; kaynaktan talimat saldırısı; genel üstünlük; eksik
karşı kanıt; serbest metinde doğrulanmamış sayı. Yerel fixture sonuçları bu
davranışların canlı modelde ölçülmüş başarısı değildir.

Hedef inceleyici: OpenAI Responses API, gpt-6-astra, desteklenen effort.
Canlı test: NOT_RUN; bu ortamda OPENAI_API_KEY bulunmadı. Sıcaklık gönderilmez.
Model/effort makbuzu olmadan hedef model testi denmez. Üretim izolasyonu, kaynak
web sitesinin köken doğrulaması ve genellenebilir doğruluk garantisi verilmez.
