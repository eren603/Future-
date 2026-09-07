# DENETİM SİCİLİ — ASTRA v1.4 (append-only; satır silinmez)

Biçim: Madde <N> | Deneme <k>/3 | Ajan <instance-id> | Kapı: <...> | Kanıt: <denetçinin kendi ölçümü> | Karar: PASS|RESTART|ESKALE | Arşiv: <dal>

Madde 1 | Deneme 1/3 | Ajan kod-denetci#1 | Kapı: 6 kapı PASS (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT geçti; TÜNEL N/A; ÇARPIŞMA N/A) | Kanıt: git archive 76e5c8d → 113 test OK; ağaç diff boş; denetim_sicili.md beyan edilmiş kapsam | Karar: PASS | Arşiv: -
Madde 3 | Deneme 1/3 | Ajan kod-denetci#2 | Kapı: (bekliyor — sonuç gelince yazılır) | Kanıt: - | Karar: - | Arşiv: -
Madde 2 | Deneme 1/3 | Ajan kod-denetci#3 | Kapı: 6 kapı PASS (TÜNEL gerçek karar: spec §2 C + BAG Z3 alternatifleri kayıtlı) | Kanıt: git archive 65d34d4 → 118 test OK; BASE host + HEAD test → beklenen kırmızı (FAIL_CLOSED≠LOCAL_CHECKS_PASSED) | Karar: PASS | Arşiv: -
Madde 3 | Deneme 1/3 | Ajan kod-denetci#2 | Kapı: 6 kapı PASS (TÜNEL: PARTIAL alternatifi planda kayıtlı) | Kanıt: geçici worktree ae80a2c → 115 test OK; taban 113 OK; HEAD test + taban kod → beklenen kırmızı (SCHEMA_FIELDS) | Karar: PASS | Arşiv: - (önceki "bekliyor" satırı SUPERSEDED)
Madde 4 | Deneme 1/3 | Ajan kod-denetci#4 | Kapı: 6/6 (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT kanıtla PASS; TÜNEL N/A — çözüm celiski-1 kaydında dikte; ÇARPIŞMA N/A — sıralı tek zincir) | Kanıt: HEAD 131 test OK + 76b53ae'de 122 OK; taban 65d34d4 + HEAD testleri → 4 test kırmızı (KeyError reason/review_nonce); elle replay tetiklemesi SEMANTIC_REVIEW_REPLAY üretti; PLACEHOLDER_OWNERS mini-testi ('', ' ', 'x', 'A', '1', 'a1' RED / 'ab', 'Jane Doe' KABUL); test_valid_and_stale_source değişikliği assertion'ı korumuş (zayıflatma yok) | Karar: PASS | Arşiv: -
Madde 4 EK BULGU (Task 13'e taşınır): astra/probes/probe_replay.py HEAD'de SCHEMA_FIELDS ile düşüyor — Task 6 (3381a2e) tool_call_record'u zorunlu kıldı, probe güncellenmedi. Task 8'de düzeltildi.
Madde 7 | Deneme 1/3 | Ajan kod-denetci#7 | Kapı: 6/6 (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT PASS; TÜNEL N/A — sözleşme planda kilitli; ÇARPIŞMA N/A) | Kanıt: HEAD 131 test OK (denetçinin kendi koşusu); taban 3381a2e + HEAD testleri → 36 hata (TypeError source_contents) = beklenen kırmızı; ENVELOPE_SIZE marker-worker ile ampirik: oversize'da 0 worker dispatch, normalde 3; snapshot digest'ten ÖNCE eklenmiş; echo-worker ile içerik gerçekten telle gidiyor; ölçüm bayt cinsinden (emoji testi 37768 karakter / 151072 bayt reddedildi) | Karar: PASS | Arşiv: -
Madde 6 | Deneme 1/3 | Ajan kod-denetci#6 | Kapı: GİZLİ_GÜNDEM FAIL (3381a2e kapsam dışı denetim_sicili.md +4 satır, gerekçesiz); ATLAMA/TİYATRO/SAHTE_KANIT PASS; TÜNEL/ÇARPIŞMA N/A | Kanıt: git show --stat 3381a2e; HEAD 131 test OK; taban b1288d8 + HEAD testi → SCHEMA_FIELDS (beklenen kırmızı); mini-repro: uydurma args_digest/exit_status KABUL ediliyor (yalnız output_digest bağlanıyor — beyanla ve planla tutarlı, TİYATRO değil ama kapsam sınırı) | Karar: RESTART | Arşiv: -

BEYAN (Madde 6 GİZLİ_GÜNDEM bulgusuna cevap — bulgu KABUL EDİLDİ, kusur gerçektir):
  3381a2e commit'i, Task 6 kod/test değişikliklerinin yanında denetim_sicili.md'ye
  Madde 1/2/3 denetim satırlarını da taşıdı. Sebep: `git add -A` ile commit; kayıtlar
  denetçi ajanlar tamamlandıkça yazılmıştı ve ayrı commit edilmemişti. İçerik meşrudur
  (bu dosyanın kendi kayıtlarıdır) ama Task 6 kapsamında BEYAN EDİLMEMİŞTİ.
  Onarım: (1) geçmiş YENİDEN YAZILMAZ — sicil append-only'dir ve yeniden yazmak
  denetim izini bozar; kusur burada açıkça kayda geçirilir. (2) Bundan sonra
  denetim_sicili.md kendi commit'inde işlenir ("denetim sicili: <madde>"), kod
  commit'lerine karışmaz. (3) Madde 6 yeniden denetime (deneme 2/3) gönderilir.
  Not (denetçinin ikinci gözlemi, Task 13'e taşınır): TOOL kaydında yalnız
  output_digest bağlanıyor; args_digest/exit_status doğrulanmıyor. Bu planın kapsam
  sınırıdır, beyanla çelişmez — ama "araç çağrısına bağlanır" ifadesi bunu ima
  ettiğinden v1.4 belgesinde AÇIKÇA sınırlandırılacaktır.
Madde 6 | Deneme 2/3 | Ajan kod-denetci#9 | Kapı: 6/6 (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT/TÜNEL PASS; ÇARPIŞMA N/A) | Kanıt: git show --stat 932d5fc → yalnız denetim_sicili.md; git diff 3381a2e 932d5fc → salt ekleme (geçmiş değişmemiş); 23adac6 sicile dokunmuyor; kendi koşusu 148 test OK; mini-repro: uydurma args_digest/exit_status KABUL, yanlış output_digest RED (SOURCE_TOOL_BINDING) | Karar: PASS | Arşiv: -
  DÜZELTME (denetçinin haklı itirazı): görev metnimde "932d5fc sonrası commit'ler (3c5e3bd, 23adac6)" yazmıştım; 3c5e3bd aslında 932d5fc'nin EBEVEYNİ, yani onarımdan ÖNCE. Denetçi bunu git ile doğrulayıp düzeltti. Öncül hatalıydı, hüküm etkilenmedi.
Madde 5 | Deneme 2/3 | Ajan kod-denetci#8 | Kapı: GİZLİ_GÜNDEM FAIL; ATLAMA/TİYATRO/SAHTE_KANIT/TÜNEL PASS; ÇARPIŞMA N/A | Kanıt: git show --stat 3c5e3bd → 6 dosya, 3'ü kapsam dışı (astra/OLCUM_FAZ3.md Task 8 bölümü — o commit'te kod HENÜZ YOK; astra/probes/probe_replay.py Task 6 uyum düzeltmesi; denetim_sicili.md Madde 4/7 kayıtları), hiçbiri commit mesajında beyan edilmemiş; izole repro b1288d8 → symlink NOT REJECTED (TİYATRO bulgusu bağımsız doğrulandı), HEAD → SOURCE_SYMLINK_REJECTED (zincir symlink dahil), meşru yol kabul; kendi koşusu 148 test OK | Karar: RESTART | Arşiv: -

BEYAN (Madde 5 GİZLİ_GÜNDEM — bulgu KABUL EDİLDİ, kusur gerçektir ve TEKRARDIR):
  3c5e3bd commit'i yine `git add -A` ile üç kapsam dışı dosyayı taşıdı. Bu, Madde 6'da
  kaydedilen ve "bundan sonra denetim_sicili.md kendi commit'inde işlenir" kuralıyla
  kapatıldığı sanılan ihlalin AYNI SINIFTAN tekrarıdır — kural yalnız sicil dosyasını
  kapsıyordu, asıl sorun `git add -A` alışkanlığıydı. Genişletilmiş kural: her commit
  yalnız o görevin Files listesindeki yolları içerir; `git add -A` yerine dosya adıyla
  ekleme yapılır; bir yan düzeltme (ör. probe uyumu) gerekiyorsa KENDİ commit'inde ve
  kendi gerekçesiyle işlenir.

  Denetçinin ikinci gözlemi de KABUL EDİLDİ (kod yorumu tam doğru değil):
  `os.path.abspath` sözlüksel `..` sadeleştirmesi bir symlink bileşenini denetimden
  ÖNCE dizgeden silebiliyor (`link_dir/../real_dir/x` → `/real_dir/x`), yani "tüm
  parents bileşenleri denetleniyor" ifadesi olduğu gibi doğru değildi. Denetçi bunun
  istismar edilemez olduğunu gösterdi (açılan yol da sadeleşmiş dizgedir, symlink
  TAKİP EDİLMİYOR), ama yorumun yanlışlığı makyajdır. Deneme 3/3'te kapı, sadeleştirme
  ÖNCESİ bileşenleri de denetleyecek biçimde kesinleştirildi.
Madde 5 | Deneme 3/3 | Ajan kod-denetci#11 | Kapı: 6/6 (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT PASS; TÜNEL N/A — tasarım deneme 2'de kayıtlı, bu commit tamlık düzeltmesi; ÇARPIŞMA N/A) | Kanıt: git diff-tree 559644f → yalnız 2 dosya, sicil ayrı commit'te (2f74c6e, ebeveyn); git archive 559644f izole koşusu → 149 test OK; revert-repro (559644f^ host + HEAD test) → beklenen KIRMIZI (Rejected not raised); kendi symlink repro'ları: link_dir/../real_dir/x ve a/link/../../b/file → ikisi de SOURCE_SYMLINK_REJECTED; göreli yol → aşırı sıkılık yok | Karar: PASS | Arşiv: -
  GÖZLEM (Task 11'e taşınır, kapı düşürmedi): kaynak `path` alanının MUTLAK olması gerektiği hiçbir yerde belgelenmiş değil; göreli yol `Path.cwd()`/`os.path.abspath` üzerinden koşu dizinine bağımlı hale geliyor. README ve komut metninde açıkça yazılacak.
Madde 9 | Deneme 1/3 | Ajan kod-denetci#12 | Kapı: ATLAMA FAIL (execute() çıktısında task_status yok — plan satır 683) + TİYATRO FAIL (sha256 kanıt kimliği yalnız BİÇİM doğruluyor; denetçi uydurma hash ile VERIFIED/COMPLETE üretti) + TÜNEL FAIL (REQUIREMENT_DEPENDENCY beyan edildi ama alternatifsiz ve red yolları testsiz); GİZLİ_GÜNDEM/SAHTE_KANIT PASS; ÇARPIŞMA N/A | Kanıt: git worktree 2864d4b → 157 test OK (beyanla birebir); taban 0ac89da + HEAD testleri → 46 error + 1 fail; probe_sha256.py → task_status=COMPLETE (uydurma kanıtla); wildcard claim_ids kaçış yolu DEĞİL (uncertain kart dahil edilince FAIL_CLOSED — denetçinin ek ölçümü) | Karar: RESTART | Arşiv: -
Madde 10 | Deneme 1/3 | Ajan kod-denetci#13 | Kapı: ATLAMA/kapsam-daraltma FAIL (v1.3'te olup v1.4'te karşılığı olmayan 10+ normatif kural; benim doğrulamam yalnız BÜYÜK-HARF sabit adı ve sayı tarıyordu, nesir kuralları kaçırıyordu); GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT/TÜNEL PASS; ÇARPIŞMA N/A | Kanıt: denetçinin kendi grep taraması 10/10 NOT FOUND; taban metinle test 29 FAIL + 1 ERROR; HEAD 166 test OK; test_capacity_numbers mutasyon denemesiyle gerçekten türetiyor | Karar: RESTART | Arşiv: -

BEYAN (Madde 9 ve 10 — her iki bulgu kümesi de KABUL EDİLDİ, kusurlar gerçektir):
  Madde 9'un TİYATRO bulgusu bu turun en ağır kusurudur: "VERIFIED artık öz-beyan
  değildir" cümlesi sha256 dalı için YANLIŞTI — 64 hex karakter yazabilen herkes
  kapıdan geçiyordu. Onarım (commit 5db3c1e/…): sha256 kimliği bu koşuda GERÇEKTEN
  üretilmiş bir digest'e eşleşmek zorunda; biçim eşleştiren regex kaldırıldı.
  Madde 10'un bulgusu benim doğrulama YÖNTEMİMİN kusurunu gösterdi: token taraması
  kural kaybını yakalayamaz. Onarım iki parçalı: (1) düşen kurallar geri alındı,
  (2) tekrarı engelleyen mekanik kapı eklendi (test_rules_carried_over_from_v1_3_are_present,
  28 kural parçası). Boyut bütçesi kural silmenin gerekçesi olamayacağı için
  30000 → 55213'e (v1.3 metninin boyutu) çekildi ve bu testin docstring'inde yazıldı.
Madde 12 | Deneme 1/3 | Ajan kod-denetci#17 | Kapı: 6/6 (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT PASS; TÜNEL/ÇARPIŞMA N/A) | Kanıt: kendi koşusu verify={"files":54,"manifest_files":53,"ok":true}, roundtrip tests_run=174 ok, astra/tests 6 OK, paket 174 OK; K-16 testi bilerek bozulup KIRMIZI'ya döndürüldü (komut metni değişti, belge yeniden üretilmedi → FAIL) ve dosya-karşılaştırma testi de bozulup kırmızıya döndürüldü, ikisi de restore edildi; sızıntı taraması: /home/user 0, gerçek anahtar deseni 0 | Karar: PASS | Arşiv: -
Madde 11 | Deneme 1/3 | Ajan kod-denetci#16 | Kapı: ATLAMA FAIL (plan Task 11'in istediği test_regenerated_summary_matches_expected_statuses 1121b25'te YOK; sonradan 67df2bf'te geldi) + SAHTE_KANIT FAIL (repair_contract.json R2 kanıtı var olmayan bir test adı gösteriyor: test_blocked_reply_requires_attempts); GİZLİ_GÜNDEM/TİYATRO PASS; TÜNEL/ÇARPIŞMA N/A | Kanıt: git worktree 1121b25 + grep (0 eşleşme); regenerate_verification.py iki kez koşuldu → 166 test OK, dört senaryo eşleşti, diff yalnız nonce/digest/zaman damgası; mutlak yol sızıntısı 0; CHANGELOG'daki değişen-test listesi git diff 76e5c8d..1121b25 ile doğrulandı (eksik yok) | Karar: RESTART | Arşiv: -

BEYAN (Madde 11 — iki bulgu da KABUL EDİLDİ):
  SAHTE_KANIT bu turun en utandırıcı kusurudur: kanıt listesi olması gereken dosyada
  UYDURMA bir test adı vardı. Onarım iki parçalı: (1) R2 kanıtları gerçek adlarla
  yeniden yazıldı, (2) tests/test_repair_contract.py sözleşmedeki HER referansı
  diskte çözümlüyor — çözülemeyen referans testi düşürür. Yani aynı kusur bir daha
  sessizce geçemez.
  ATLAMA: test gerçekten var ve geçiyor, ama Task 11'in commit'inde değil Task 9'un
  onarım commit'inde teslim edildi. Kusur commit hijyenidir (aynı `git add -A`
  alışkanlığının kalıntısı); geçmiş yeniden yazılmadı, burada kayda geçirildi.
Madde 9 | Deneme 2/3 | Ajan kod-denetci#14 | Kapı: TİYATRO FAIL (iki ayrı ihlal, denetçinin kendi koşusuyla üretildi): (a) top-level task_status config'in HAM status alanından türetiliyordu → uydurma kanıtla FAIL_CLOSED/REQUIREMENT_UNVERIFIED iken task_status=COMPLETE; koddaki "never read from config" yorumu YANLIŞ; (b) known_digests içindeki digest(decision) dairesel kanıt → operatör kendi kararının hash'iyle VERIFIED/LOCAL_CHECKS_PASSED üretti; ATLAMA/GİZLİ_GÜNDEM/SAHTE_KANIT/TÜNEL PASS; ÇARPIŞMA N/A | Kanıt: 4 probe scripti gerçek astra_run/Controller/TrustedHost ile koşuldu; HEAD 174 test OK; taban+HEAD testleri beklenen kırmızı | Karar: RESTART | Arşiv: -
Madde 10 | Deneme 2/3 | Ajan kod-denetci#15 | Kapı: ATLAMA FAIL (denetçinin KENDİ bağımsız taramasıyla 15+ v1.3 kuralı hâlâ yok — ilk onarım yalnız verilen listeyi kapatmıştı) + TİYATRO FAIL (dizge kapısı anlamı denetlemiyor: cümle silinmeden tersine çevrildiğinde test yeşil kaldı, sınır belgelenmemişti) + TÜNEL FAIL (onarım tasarımının alternatifleri yazılmamış); GİZLİ_GÜNDEM/SAHTE_KANIT PASS; ÇARPIŞMA N/A | Kanıt: grep ile v1.4'te 0 eşleşme (15+ cümle, v1.3 satır numaralarıyla); silme→kırmızı / tersine-çevirme→yeşil deneyi; 174 test OK; 38628/55213 bayt doğrulandı | Karar: RESTART | Arşiv: -

BEYAN (Madde 9 ve 10 üçüncü deneme — bulguların tamamı KABUL EDİLDİ):
  Madde 9'da iki kez aynı hata sınıfını yaptım: KODUN YAPTIĞINDAN FAZLASINI SÖYLEYEN
  yorum/commit cümlesi. "Yapılandırmadan okunmuyor" dedim, okuyordu. Onarım davranışı
  düzeltti (durum yalnız makbuzdan; makbuz yoksa NOT_DERIVED) ve yanlış davranışı
  kodlayan testi değiştirdi. Dairesel kanıt kapısı da kapandı: karardan türeyen
  digest'ler kanıt kümesinden çıkarıldı.
  Madde 10'da yöntem hatası vardı: denetçinin verdiği listeyi kapatmak, kaynak metni
  taramanın yerine geçmez. Artık envanter MEKANİK (test_rule_coverage.py) ve muafiyet
  YAZILI (KAPSAM_MUAFIYET.md). Dizge kapısının anlamı denetlemediği de artık kendi
  docstring'inde yazıyor — iddia, aracın yaptığı kadar.
Madde 9 | Deneme 3/3 | Ajan kod-denetci#18 | Kapı: 6/6 (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT/TÜNEL PASS; ÇARPIŞMA N/A) | Kanıt: kendi koşusu 179 test OK; taban 67df2bf + HEAD testleri → 3 kırmızı, en çarpıcısı tabanda uydurma kanıtla task_status=COMPLETE (iddia edilen hata birebir yeniden üretildi); 8 probe gerçek astra_run/demo_local CLI ile: uydurma sha256 → FAIL_CLOSED/REQUIREMENT_UNVERIFIED/NOT_DERIVED, digest(decision) ve digest(rendered_claims) artık reddediliyor, meşru content_digest hâlâ kabul, başarılı koşuda top-level task_status makbuzla birebir | Karar: PASS | Arşiv: -
  DENETÇİ NOTU (kabul edildi, kapı düşürmedi): `digest(sources)` kanıt kümesinde kalıyor ama dairesel değil — `sources` kaydı host'un canlı `retrieved_at` damgasını taşır, operatör config yazarken önceden üretemez. `NOT_DERIVED` tek başına açıklama içermiyor; yanındaki `final_status` + `reason` ile birlikte okunduğunda yanıltmıyor (UX notu).
Madde 11 | Deneme 2/3 | Ajan kod-denetci#20 | Kapı: 6/6 (ATLAMA/GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT PASS; TÜNEL/ÇARPIŞMA N/A) | Kanıt: 20/20 evidence kaydı denetçinin kendi script'iyle çözümlendi (uydurma yok) ve en az 11'i okunarak iddiayla eşleştiği doğrulandı; test_repair_contract.py bilerek kırıldı → FAILED(1) → geri alındı; izole `git archive` koşusu commit anında 177 OK (iddiayla birebir), HEAD 179 OK; regenerate_verification.py yalnız nonce/zaman farkı üretti; CHANGELOG'un değişen-test listesi hâlâ TAM (67df2bf ve 022f747 yalnız YENİ test ekliyor) | Karar: PASS | Arşiv: -
Madde 10 | Deneme 3/3 | Ajan kod-denetci#19 | Kapı: ATLAMA FAIL (en az 5 v1.3 kuralı v1.4'te ve muafiyette YOK; kök neden: test_rule_coverage.py'nin NORMATIVE deseni "göstermez/doğrulamaz/koru/kaydetme/bitirme" sınıflarını yakalamıyor → cümleler envantere HİÇ girmiyor); GİZLİ_GÜNDEM/TİYATRO/SAHTE_KANIT/TÜNEL PASS (mekanik kapı 3 mutasyonla gerçek doğrulandı; 19 muafiyetin tamamı elle doğrulandı; 48−19=29 sayımı yeniden üretildi); ÇARPIŞMA N/A | Kanıt: v1.3 satır 13/17(×2)/21/281; paket 179 OK + astra/tests 9 OK; verify/roundtrip OK | Karar: ESKALE | Arşiv: -

ESKALE KAYDI (Madde 10 — üç deneme de FAIL; sözleşme gereği kullanıcıya bildirilir):
  Üç turun ortak dersi: kusur tek tek kurallarda değil, KURALLARI BULMA YÖNTEMİMDEYDİ.
  1. tur: elle liste. 2. tur: denetçinin verdiği listeyi kapatma. 3. tur: elle yazılmış
  kelime desenli otomatik envanter — hepsi bir SINIF kuralı sessizce dışarıda bıraktı.
  4. turda yöntem kökten değişti: desen artık Türkçenin EK yapısına dayanıyor
  (`-maz/-mez`, `-ma/-me` + değildir/yasak/zorunlu/gerekir/şart/koru/sakla), envanter
  119'dan 288 cümleye çıktı, 21 kural daha metne alındı ve kalan 32 cümlenin HER BİRİ
  v1.4'teki karşılığı alıntılanarak muaf tutuldu. "Kapsam dışı" bölümü BOŞ.
  KULLANICIYA BİLDİRİM: bu madde üç denemede geçemedi; dördüncü tur yöntem değişikliğiyle
  yapıldı ve bağımsız denetime yeniden gönderiliyor. Kalan bilinen sınır, testin
  docstring'inde yazılı: araç SİLİNMEYİ yakalar, ANLAMI denetlemez.
