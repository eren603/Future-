# Açık kalemler (Task 11/12/13'e taşınacak; kaybolmasın diye burada)

1. **Protokol dizgesi `ASTRA-HOST-1.3`** — `astra_host.py` içinde inceleme isteği ve
   makbuz `protocol="ASTRA-HOST-1.3"` taşıyor. Paket v1.4 olarak yayımlanacaksa bu
   dizge ya güncellenmeli ya da "protokol sürümü paket sürümünden ayrıdır" diye
   AÇIKÇA belgelenmeli. Sessiz bırakmak makyaj olur. → Task 11.
2. **TOOL kaydının sınırı** — `tool_call_record` yalnız `output_digest` ↔ içerik bağını
   doğruluyor; `args_digest`/`exit_status` kaydediliyor ama doğrulanmıyor. Komut
   metnine (v1.4 §4) açık sınır cümlesi yazıldı. Denetçi bulgusu olarak Task 13
   tablosuna girecek. → Task 10 (yapıldı) + Task 13 (kayıt).
3. **`astra/probes/probe_replay.py`** Task 6 sonrası kırılmıştı (`tool_call_record`
   zorunlu oldu); Task 8'de düzeltildi. `probe_uncertain_card.py` ve
   `probe_math_validate.py` bilerek v1.3 paketini hedefler (taban kanıtı) ve
   DEĞİŞTİRİLMEDİ. → Task 13 (kayıt).
4. **`MIN_VERDICT_BYTES` planla uyuşmuyor** — plan 534 diyordu (kaynaksız), ölçüm 451.
   Plan metni Task 8 bölümünde hâlâ 534 yazıyor; Task 13'te plan/belge tutarlılığı
   düzeltilirken bu da not edilecek. → Task 13.
5. **Plan Task 10 madde 8** "534 bayt/iddia, ~245 iddia" diyordu; komut metnine
   ölçülen değerlerle (451 bayt, 290 iddia) yazıldı. → Task 13 (sapma kaydı).
