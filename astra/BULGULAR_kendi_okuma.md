# Bağımsız bulgu listesi — orkestratörün kendi satır-satır okuması (kanıt ailesi: OKUMA)

Bu liste iş akışı ajanlarından BAĞIMSIZ tutuldu (BULAŞMA yasağı). Satır numaraları
astra/astra_tamir_v1_3.md'ye aittir. Etiket: [DOKÜMAN] alıntı ile, [ÖLÇÜLDÜ] OLCUM_FAZ3.md'de.

## P0 — amaç bozan

- K-01 [ÖLÇÜLDÜ] Belirsizlik cezası: herhangi bir işçinin, kritik olmayan ve kararda seçilmemiş
  tek bir `stance=uncertain` kartı bile host kapısını `SEMANTIC_CLAIM_UNSUPPORTED` ile kapatır
  (astra_host.py 1649-1656: tüm kartlar için verdict zorunlu; `verdict == "uncertain"` → ret).
  Belge 6.1 (satır 317) "Eşitlik, belirsizlik ve çözümlenmemiş çelişki görünür kalsın" ve kart
  şemasının `uncertain` seçeneğiyle (260) çelişir. Etki: kör işçi belirsizliği yazarsa yayın
  ölür → işçi belirsizliği SAKLAMAYA ya da sahte kesinliğe itilir. Dürüstlük mekanizmasının
  kendisi dürüstlüğü cezalandırıyor.
- K-02 [DOKÜMAN] Kaçış: A.3 (39) "sonucu maddi biçimde değiştiren belirsizlikte önce bağımsız
  yararlı işi tamamla, sonra tek odaklı soru sor" + 6.1 (309) "kullanıcıya gerekçeli tek soru
  sor" + 1 (185) "eksiklik sonucu veya yetkiyi maddi biçimde etkiliyorsa tek odaklı soru sor".
  "Maddi biçimde" ölçütü tanımsız; "yararlı iş"in ölçüsü yok → model istediği anda soru
  sorarak durabilir. Rehber (ARASTIRMA §4): GPT-6 Astra soru sormaya daha yatkın; GPT-5.2
  rehberi "state your best-guess interpretation plainly, then comprehensively cover" der.
- K-03 [DOKÜMAN] BLOCKED'ın maliyeti yok: 5 (278) "Doğrulanmış BLOCKED aynı çalışmada
  sonlandırıcıdır ... BLOCKED işçi yeniden çağrılmaz"; BLOCKED şeması yalnız `block_reason` +
  `next_safe_step` ister (253). Hangi yolların denendiği, hangi kaynağın açıldığı istenmiyor →
  bir işçi tek cümleyle bütün çalışmayı bitirebilir. Kod (6556-6559) da yalnız boş olmamayı
  denetler.
- K-04 [DOKÜMAN] SINGLE_MODEL/ANALYSIS_ONLY tanımsız derinlik: 2 (191, 195) "doğrudan analiz
  ... eksiklerin açıklanması" — bu modda hangi kapıların (gereksinim envanteri, sayısal
  envanter, karşı-kanıt, öz-denetim) hâlâ zorunlu olduğu yazılmıyor; tek modelde çalışan
  Astra için asıl yol bu olduğundan en büyük kaçış burada.

## P1 — kaçış / çelişki

- K-05 [DOKÜMAN] Otorite sırası belirsiz: 21 "üst öncelikli talimatları ... değiştirmez",
  179 "Üst öncelikli talimatlara ... uy" — "üst öncelikli" tanımsız; A-bölümü mü, ROUTER mı,
  1-10 mu, kullanıcı mı önce, yazılmıyor. GPT-6 Astra rehberi: otorite açık olmalı, aksi
  halde model durur/sapar.
- K-06 [ÖLÇÜLDÜ] Owner kapısı göstermelik: 297 "owner gerçek bir sorumlu olmalı;
  'unknown/bilinmiyor' yeterli değildir" → kod (6651) yalnız bu iki kelimeyi reddeder;
  'n/a', '-', 'TBD', '?' geçer.
- K-07 [DOKÜMAN] Kapasite iddiası ile tel sınırı çelişir: 266 "en çok 64 kapsam", şema
  320 kaynak / 320 iddia; ama inceleme isteği (1629-1640) TÜM snapshot + kartlar + şema ile
  tek gövdede `invoke`'a gider ve REQUEST_SIZE 131072 bayt (6406) → pratik kapasite çok daha
  küçük; belge bunu söylemiyor. Ayrıca 16384 max_output_tokens ile 320 iddialık alıntılı
  değerlendirme kesilir (incomplete → kapı kapanır) — tasarım gereği ama yazılmamış.
- K-08 [DOKÜMAN] "Kısa gerekçe" + "sonucu önce ver" (177, 183) ile "bütün sayısal iddiaları
  incele / karşı kanıt ara" (299, 313) arasında çıktı-derinliği gerilimi: kullanıcı çıktısı
  kısaltılırken hangi denetimlerin yapıldığının ARTEFAKTI (kontrol listesi/rubrik sonucu)
  istenmiyor → derin iş yapılmadan da kısa çıktı verilebilir.
- K-09 [DOKÜMAN] Effort doğrulaması: A.2 (35) "Görünmeyen ayarı UNKNOWN bırak" doğru; ama
  komut, hedef modelin kendisi (Astra) tarafından yürütülürken modelin KENDİ effort'unu
  bilemeyeceği, dolayısıyla "max ile çalıştım" diyemeyeceği açıkça yazılmıyor → sahte
  "max" beyanı için kapı açık.
- K-10 [DOKÜMAN] "Gerçek" kelimesi enflasyonu: 7 "Dört gerçek CLI senaryosu", 850 "gerçek CLI
  çalıştırıcı", 853 "gerçek yerel çalıştırma kanıtları", 348 "TEST_FIXTURE ... gerçek alt
  süreçtir" — senaryolar sentetik ve fixture inceleyici `pass` modunda her kartı
  stance→verdict eşlemesiyle otomatik onaylıyor (7305). "valid" senaryosu yalnız BORU
  HATTINI kanıtlar; belge bunu 9. satırda söylüyor ama başlıkta "gerçek" diyor (makyaj).
- K-11 [DOKÜMAN] repair_contract.json (7140-7188) R1/R2/R3 "VERIFIED" + task_status
  "COMPLETE": kanıt olarak aynı paketin kendi test dosyaları gösteriliyor; A.1 (31) "Modelin
  kendi 'yaptım' cümlesi ... bu kanıt değildir" ilkesine göre bu kayıt öz-beyan → dairesel.
- K-12 [DOKÜMAN] Kaynak doğrulama iddiası: 459 "OpenAI arayüzü için ... kontrol edildi",
  9556-9575 üç iddia SUPPORTED. Bu oturumda birincil sayfalar açılamadı (ARASTIRMA §1);
  belge tarih veriyor ama alıntı/parça vermiyor (6.1'in 311. satırdaki kendi kuralı:
  "gerçekten açılan içerikteki ilgili konum/parça ... kaydet") → kendi kuralını ihlal.
- K-13 [DOKÜMAN] Strict şema riski: ASSESSMENT_SCHEMA (1385-1391) minLength/maxLength/
  minItems/maxItems/enum ile `strict:true` gönderiliyor (1736-1737); sunucu kabulü hiçbir
  artefaktla gösterilmemiş (ARASTIRMA §3). İlk canlı çağrı 400 ile kapanabilir; README bunu
  "canlı doğrulanmadı" diye etiketlemiyor.
- K-14 [DOKÜMAN] Zaman aşımı tutarsızlığı: adaptör HTTP timeout=45 (1743), README örneği
  ReviewerEndpoint timeout=60 (796); alt süreç 60'ta öldürülür, HTTP 45'te — tutarlı ama
  belgede açıklanmıyor; ayrıca 429/5xx tek deneme → REVIEW_PROVIDER_UNAVAILABLE, hata gövdesi
  yutuluyor (1748-1749) → operatör teşhis yapamaz.
- K-15 [DOKÜMAN] ROUTER platforma bağlı: 108, 123 "Plugin Management içindeki search_plugins",
  "bir turda en fazla bir suggest_plugins" — ChatGPT-apps'e özgü; komut başka host'ta
  (Codex/Claude/API) çalışırken bu araçlar yok. 108 "hayalî araç adı yazma" diyor ama kendisi
  ad veriyor; hangi ortamda geçerli olduğu etiketlenmemiş.
- K-16 [DOKÜMAN] Tekrar/şişkinlik: aynı dürüstlük cümleleri (canlı çağrı yok / TEST_FIXTURE
  onay değil / üretim izolasyonu yok) belgede en az 9 yerde (9, 11, 212, 305, 348, 350, 457,
  734-737, 752-756, 832-838); komutun kendisi (17-411) gömülü kopyayla (866-1257) iki kez
  taşınıyor → modelin bağlamı iki kat; rehber (ARASTIRMA §4) tekrar/çelişkinin reasoning
  bütçesini yediğini söylüyor.

## P2 — süsleme / tutarsızlık

- K-17 [DOKÜMAN] "Nihai tamir edilmiş" (1), "kusursuz" (321, olumsuz bağlamda), "imkânsız"
  yok ama "asla"/"kesinlikle" (400) — sınırlı; başlıktaki "nihai" kendi 11. satırıyla
  ("genel doğruluk garantisi verilmez") gerilimli.
- K-18 [DOKÜMAN] 0.7 ve 6.2 ve 10 tabloları aynı kabul-örneği türünü üç yerde tekrarlar.
- K-19 [DOKÜMAN] Python sürümü: 7 "3.12.13" — bu ortamda 3.11.15 ile aynı sonuç; README
  "3.11+" diyor; tutarlı ama "3.12.13 ile" cümlesi sonucu sürüme bağlıyormuş gibi okunuyor.
- K-20 [DOKÜMAN] 391 "Sonradan öğrenilen/revize edilen bilgiyi geçmiş karara sızdırma" gibi
  9. bölüm Binance profili bu komutun GENEL kullanımında ölü ağırlık; koşullu bölüm olarak
  ayrılmış (384) ama komut gövdesinde taşınıyor.

## Kaybolmaması gereken dürüstlük cümleleri (koruma listesi)
- 9, 11 (durum satırı), 179 ("ASTRA bu protokolün adıdır; seçilmiş modelin kanıtı değildir"),
  183 (yapmadığın çağrıya "çalıştırıldı" yazma), 206 (model yazdığı `real_isolation: true`
  kabul edilmez), 305, 344 (inceleyicide arama aracı yok), 348, 370 (APPROVED yalnız
  REAL_ISOLATION), 382 (APPROVED canlı emir yetkisi değildir), 409.
