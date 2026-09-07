ASTRA v1.4 değişiklik kaydı

Bu sürüm yeni bir yetenek eklemez; v1.3'te BULUNAN eksik, çelişki, hata ve
makyajı kapatır. Her madde bir bulgu kimliğine bağlıdır (bulgu → değişiklik
tablosu: `BULGU_DEGISIKLIK.md`).

Kapılar
- Belirsizlik cezası kaldırıldı: kritik OLMAYAN ve karara girmeyen `uncertain`
  kart artık yayını kapatmaz; kritik olan ya da kararın `claim_ids`'ine seçilen
  kapatır. (K-01, celiski-2)
- BLOCKED ucuz kaçış olmaktan çıktı: yanıt en az iki `attempts` kaydı ister.
  (K-03, kacis_yolu-1)
- `owner` yer tutucusu (unknown, bilinmiyor, n/a, tbd, -, ?, boş, iki harften az)
  reddedilir. (K-06)
- `finalize` bir kez çalışır (`FINALIZE_ALREADY_DONE`); inceleme isteği taze
  `review_nonce` + `issued_at` taşır ve aynı yanıt digest'i ikinci kez
  tüketilemez (`SEMANTIC_REVIEW_REPLAY`). (celiski-1)
- Gereksinim defteri eklendi: `VERIFIED` bir öz-beyan değil, bu koşuda var olan
  artefaktları adlandırmak zorundadır (`REQUIREMENT_UNVERIFIED`); dayandığı
  gereksinim VERIFIED değilse VERIFIED olamaz (`REQUIREMENT_DEPENDENCY`).
  `TASK_STATUS` host tarafından TÜRETİLİR, yapılandırmadan okunmaz. (eksiklik-1,
  celiski-7, K-11, makyaj-5)

Kaynak ve zarf
- `kind="TOOL"` etiketi araç çağrısı kaydına bağlandı: `output_digest` okunan
  içerikle eşleşmezse ya da `USER` kaynak kayıt taşırsa `SOURCE_TOOL_BINDING`.
  Sınır açıkça yazıldı: `args_digest`/`exit_status` doğrulanmaz. (eksiklik-6, K-10)
- Yolun HERHANGİ bir bileşeni sembolik bağsa kaynak reddedilir
  (`SOURCE_SYMLINK_REJECTED`); yol çözülmez ve ".." ile gizlenmiş bağ da yakalanır.
  (kod_hata-7)
- İşçi zarfı artık kaynak İÇERİĞİNİ taşır (`source_snapshots`); zarf
  `WIRE_LIMIT`'i aşarsa faz hiç başlamaz (`ENVELOPE_SIZE`). (celiski-8, K-07)

Sağlayıcı arayüzü
- Tele giden şemadan uzunluk anahtarları ayıklandı (`transport_schema`); tam
  doğrulama host'ta kaldı. Sunucu kabulü DOĞRULANMADI — bu bir risk azaltmadır,
  kanıt değildir. (api_uyum-1)
- Modelin tarihli anlık görüntüsü kabul edilir, ilgisiz model reddedilir.
  (api_uyum-3)
- HTTP hatası yalnız sınıfıyla raporlanır (`REVIEW_PROVIDER_HTTP_4XX` / `_5XX`);
  sağlayıcı gövdesi okunmaz. `status != completed` → `REVIEW_PROVIDER_INCOMPLETE:
  <reason>`. `message` olmayan çıktı öğeleri atlanır. (api_uyum-6/8, K-13)
- Proxy/CA yalnız host yapılandırmasından gelir (`ASTRA_HTTPS_PROXY`,
  `ASTRA_CA_BUNDLE`); ortamın `HTTPS_PROXY`'si okunmaz. (api_uyum-13)
- İnceleme çağrısından ÖNCE bütçe kapısı: `kart sayısı × MIN_VERDICT_BYTES >
  WIRE_LIMIT` ise çağrı hiç yapılmaz (`REVIEW_BUDGET_EXCEEDED`). Sabit ölçüldü
  (451 bayt; `astra/OLCUM_FAZ3.md`), beyan edilmedi. (api_uyum-12, K-14)
- `invoke`: işçinin kendi ret kodu (`^[A-Z0-9_:]{3,80}$`) taşınır, serbest metin
  `WORKER_EXIT`e düşer. (kod_hata-4)

Kod kenarları
- `exact_math` yorum/satır sonu/`\`/`;` içeren ifadeyi reddeder. (kod_hata-6)
- Karşılaştırma alıntıları NFKC ile normalleştirilir ve Unicode eksi/tire
  işaretleri sayısal literal denetimini atlatamaz. (kod_hata-2)
- `TEST_FIXTURE` inceleyicisine API anahtarı verilemez
  (`REVIEWER_CREDENTIAL_SCOPE`). (kod_hata-5)
- `astra_run --output` yazılamıyorsa traceback değil FAIL_CLOSED. (kod_hata-12)

Komut metni
- `astra_command.md` yeniden yazıldı ve SINANAN artefakt oldu
  (`tests/test_command_text.py`). Eklenenler: iki talimat yüzeyi ayrımı,
  "Host yoksa host sensin" + `astra_records` bloğu, araç çıktısının da yanlış
  olabileceği, tur bitirme koşulu, `critical` tanımı, kısalığın derinlik yerine
  geçmediği, ölçülmüş kapasite (451 bayt / 290 iddia), APPROVED'ın bu paketçe
  ÜRETİLEMEDİĞİ. Yeniden yazımda düşen 21 sabit adı ve 2 sayı geri alındı.
- `SEMANTIC_POLICY` v1.4: inceleyici soru soramaz; eksik kanıtta `uncertain`
  döner ve neyin eksik olduğunu adlandırır; dayandığı varsayımı beyan eder.

v1.3'ten devralınan testlerde yapılan değişiklikler
- `test_lexically_matching_wrong_meaning_rejects_reviewer_verdict` →
  `test_fixture_uncertain_verdict_on_decision_claim_closes_gate`: eski ad testin
  ölçtüğünden fazlasını iddia ediyordu (ret, anlam eşleşmesinden değil fixture'ın
  koşulsuz "uncertain" etiketinden geliyor).
- `test_valid_and_stale_source`: finalize kilidi nedeniyle ikinci bağımsız bir
  controller kullanır; ölçtüğü iddia (`SOURCE_STALE_OR_TIME`) aynıdır.
- Fixture/demo kaynakları `kind="TOOL"` → `kind="USER", tool_call_record=None`;
  kart etiketi `ARAÇ` → `KULLANICI`. Bu dosyalar elle yazılmış kullanıcı
  dosyalarıdır; yeni kapı yanlış etiketi ortaya çıkardı.
- `test_request_uses_real_responses_contract_and_bound_receipt`: tele giden şema
  artık `transport_schema(ASSESSMENT_SCHEMA)`.

Sınırlar (değişmedi, gizlenmiyor)
- Canlı sağlayıcı çağrısı YAPILMADI: API anahtarı yok ve `developers.openai.com`
  bu ortamda egress engelli. `verification/source_review_notes.json` üç birincil
  iddiayı `PREVIOUSLY_SUPPORTED_NOT_REVERIFIED` olarak işaretler.
- `TEST_FIXTURE` inceleyicisinin kabulü anlamsal model başarısı DEĞİLDİR.
- Ayrı süreçler üretim izolasyonu sağlamaz; paket tamamen LOCAL_TEST'tir.
- `semantic_support_verified` alanı yalnız EXTERNAL_MODEL adaptörünün çağrıldığını
  ve bağlı incelemenin kabul edildiğini söyler; nesnel doğruluk garantisi değildir.
