# ASTRA v1.4 tamir tasarımı (2026-09-07)

Durum: brainstorming çıktısı. Kullanıcı gerçek zamanlı izlemiyor (otonom görev); tasarım
kullanıcı onayı beklenmeden, aşağıdaki VARSAYIMLAR açıkça yazılarak uygulanır. Kullanıcı
herhangi bir varsayımı reddederse ilgili plan maddesi geri alınır.

## 1. Hedef (kullanıcının cümlesinden gereksinimler)

| R | Dayanak (kullanıcı) | Teslimat | Kabul kontrolü |
|---|---|---|---|
| R1 | "eksiklikleri, çelişenleri, hataları, makyajlanmaları, süslemeleri bul" | Bulgu listesi: bağımsız okuma + 8 boyutlu ajan taraması + ölçümler; her bulgu satır+alıntı; hasım çürütmeden geçmiş | `astra/bulgular_hukum.json` + `BAG_HARITASI.md`; her onarım bir bulgu kimliğine bağlı |
| R2 | "tamir et" | v1.4 komut metni + kod düzeltmeleri + testler + yeniden üretilmiş tek dosya (`astra_tamir_v1_4.md`) | Tüm testler geçer (eski 113 + yeni); `bundle_tools.py verify` hash/envanter geçer; her bulgu → değişiklik tablosu |
| R3 | "Astra'nın ultra zekâyla çalışmasını zorlayacak, kaçacak yer bırakmayacak şekilde ayarla" | Tek otorite sırası; 7 adımlı zorunlu döngü; her çıkış kapısı ön koşul + artefakt; öz-denetim rubriği; yapılmayanlar bloğu; SINGLE_MODEL'de de aynı artefaktlar | Komut-metni testi: takdir zarfı yok ("gerekirse/mümkünse/uygun"), her çıkış kapısında artefakt maddesi var, koruma listesi cümleleri duruyor |
| R4 | "gerekli araştırmaları yapıp dibine kadar" | ARASTIRMA.md (erişim durumu, ikincil/birincil ayrımı, VERİ YOK listesi) | Belgede her dış iddia etiketli; egress-bloklu kaynaklar "yeniden doğrulanamadı" |
| R5 | dürüstlük (CLAUDE.md sözleşmesi + belgenin kendi ilkesi) | Canlı model/API doğrulaması YAPILMADI ibaresi korunur; "gerçek" dili sentetik için kullanılmaz | Test: koruma listesi + slop listesi |

KAPSAM DIŞI (gerekçeli): canlı gpt-6-astra çağrısı (anahtar yok, egress bloklu); kalıcı
görev zamanlayıcısı; üretim izolasyonu; APPROVED üretimi. Bunlar v1.3'te de kapsam dışıydı;
v1.4 bunları "yapılmadı" olarak taşır.

## 2. Yaklaşımlar

**A — Yerinde cerrahi.** v1.3 yapısı kalır; her bulgu tek tek düzeltilir. Artı: izlenebilir
diff. Eksi: N3/N10 çelişki ve tekrarlar yapısal; üç yerde yazılmış aynı kural düzeltilse de
model üç yer görür; kaçış kapıları yapısal olarak kalır.

**B — Yeniden yapılandırma + izlenebilirlik (SEÇİLDİ).** Komut metni tek kaynak olarak
yeniden yazılır (0 otorite → 1 değişmezler → 2 döngü → 3 çıkış kapıları → 4 makine
sözleşmesi → 5 çıktı → ekler); belge başlığı bu dosyadan üretilir (sürüklenme imkânsız);
kod bulguları TDD ile düzeltilir; her değişiklik bulgu kimliğine bağlanır (A'nın
izlenebilirliği korunur). Artı: çelişki kökten kalkar, reasoning bütçesi korunur, kaçışlar
artefakt şartına bağlanır. Eksi: büyük diff; dürüstlük cümlesi kaybı riski → koruma listesi
testi.

**C — Yalnız metin.** Kod dokunulmaz. Reddedildi: N5 (belirsizlik), N8, N11, N7 kod
düzeyinde; metin düzeltilirken kod çelişik kalır — belgenin kendi "metin ≠ mekanizma" ilkesi
ihlal edilir.

## 3. Mimari

```
astra/
  astra_command.md (v1.4, TEK KAYNAK) ─┐
  bundle_v1_4/ (kod+testler+verification) ├─ scripts/bundle_tools.py build ─→ astra_tamir_v1_4.md
  README/CHANGELOG/prompt_spec/repair_contract ┘        (manifest sha256 yeniden üretilir)
```

Bileşenler ve sorumlulukları:

1. **Komut metni** (`bundle_v1_4/astra_command.md`): ≈21 KB (v1.3: 55 KB). Bölümler sabit.
   Taslak: scratchpad `astra_command_v1_4_TASLAK.md`. Koruma listesi cümleleri korunur.
2. **astra_reference.py**: REPLY_SCHEMA BLOCKED yanıtına `attempts` (≥2, her biri ≥10
   karakter) ekler; READY'de `attempts=[]`; `check_reply` uygular; DEFAULT_POLICY metni
   güncellenir. `exact_math` yorum/satır sonu/ters bölü reddeder; `proof.source` normalize.
   `finalize` başarıdan sonra kilitlenir (FINALIZE_ALREADY_DONE); owner yer-tutucu kümesi
   genişler (unknown, bilinmiyor, n/a, na, tbd, -, ?, none, null, boş) + en az 2 harf.
   Zarf, host vault'undan izinli kaynak snapshot'larını `source_snapshots` alanıyla taşır
   (digest'e dahil; WIRE_LIMIT aşımı → Rejected ENVELOPE_SIZE, koşu başlamaz).
3. **astra_host.py**: `verify` belirsiz hükmü kritik olmayan ve karara girmeyen kartlar için
   kabul eder (stance ile eşleşmeli), yalnız kritik ya da `decision.claim_ids` içindeki
   belirsiz kart kapıyı kapatır. İstek `review_nonce` + `issued_at` taşır; tüketilmiş
   digest kümesi → SEMANTIC_REVIEW_REPLAY. TEST_FIXTURE + credential_env → REVIEWER_CREDENTIAL_SCOPE.
   TOOL türü kaynak `tool_call_record` ister (tool_name, args_digest, exit_status,
   output_digest == içerik digest'i) → yoksa SOURCE_TOOL_BINDING. İnceleme öncesi bütçe ön
   kapısı: kart sayısı × asgari hüküm boyutu > WIRE_LIMIT → REVIEW_BUDGET_EXCEEDED.
   `transport_schema()` sunucuya giden şemadan minLength/maxLength/minItems/maxItems'ı çıkarır;
   tam doğrulama host'ta kalır. SEMANTIC_POLICY: belirsizlik cümlesi tek kural. Gereksinim
   defteri: REQUIREMENT_SCHEMA + `derive_task_status()`; TrustedHost isteğe bağlı
   `requirements` alır; VERIFIED gereksinim en az bir gerçek kanıt kimliği (kaynak, proof,
   karşılaştırma, teslimat sha256) taşımalı, yoksa REQUIREMENT_UNVERIFIED; task_status host
   türetir. `ReviewerEndpoint` `network={proxy, ca_bundle}` alır → alt sürece sabit adlarla
   geçer. Adaptör stderr'indeki ret kodu (allowlist) WORKER_EXIT yerine taşınır.
4. **astra_compare.py**: NFKC + Unicode eksi/tire/bölü/iki nokta lookbehind.
5. **astra_openai_reviewer.py**: model eşleşmesi snapshot toleranslı (`expected` ya da
   `expected-...`), dönen model adı fişe; HTTP durum sınıfı Rejected koduna eklenir
   (REVIEW_PROVIDER_HTTP_4xx/5xx, gövde asla); `incomplete_details.reason` fişe;
   `output[].type=="message"` süzgeci; proxy/CA yalnız config'ten.
6. **astra_run.py**: `decision.claim_ids == ["*"]` → koşu sonrası bütün kart kimlikleri
   (kararın kartlardan sonra kurulması); çıktı yazımı try içinde; `requirements` alanı
   isteğe bağlı; sonuçta `task_status` host'tan.
7. **Testler**: her değişiklik için önce başarısız test; tautolojik testler yeniden
   adlandırılır ve sınırı belgeleyen negatif test eklenir; EXTERNAL_MODEL başarı yolu
   `invoke` patch'iyle sınanır; adı hiç geçmeyen ret kodlarının kritik olanları için test;
   komut-metni testi (`tests/test_command_text.py`): koruma cümleleri, takdir zarfı yok, slop
   yok, çıkış kapılarında artefakt maddesi, belge başlığı == gömülü kopya.
8. **verification/**: bu ortamda yeniden koşulur (gerçek çıktı), Python sürümü yazılır;
   `source_review_notes.json` → üç iddia "bu oturumda yeniden doğrulanamadı (egress)" +
   ikincil kaynak etiketleri; `repair_contract.json` host türetimli (status LOCAL_TESTED,
   task_status türetilmiş, canlı bağımlılık açık).

## 4. Veri akışı (v1.4 çalışma döngüsü — komut metninin özü)

Envanter (R-listesi) → araç eşlemesi → kanıt (arama günlüğü) → üretim (hesap kaydı) →
hasım turu (≥3 saldırı) → öz-denetim rubriği (7 madde) → teslim (YAPILMAYANLAR + durum).
Çıkış kapıları (soru / BLOCKED / VERİ YOK / kapsam dışı / kapasite / tek model) yalnız ön
koşul + artefaktla. Host yoksa kayıtlar yanıt sonunda `astra_records` JSON bloğunda.

## 5. Hata yönetimi

Fail-closed korunur; yeni ret kodları: ENVELOPE_SIZE, SEMANTIC_REVIEW_REPLAY,
FINALIZE_ALREADY_DONE, SOURCE_TOOL_BINDING, REVIEW_BUDGET_EXCEEDED, REQUIREMENT_UNVERIFIED,
REVIEW_PROVIDER_HTTP_4xx/5xx, BLOCKED_ATTEMPTS_REQUIRED. Hiçbir hata gövdesi/anahtar
loglanmaz; yalnız kod ve HTTP durum sınıfı.

## 6. Test stratejisi

Eski 113 test korunur (davranış değişen 3-4 test güncellenir ve gerekçesi CHANGELOG'da);
yeni testler ≈ 35-45. Doğrulama komutu: `python3 -m unittest discover -s tests -p 'test_*.py'`
+ `python3 astra/scripts/bundle_tools.py verify astra/astra_tamir_v1_4.md` + demo 4 senaryo.

## 7. Varsayımlar (kullanıcı onayı yerine)

- V1 Teslimat biçimi: v1.3 ile aynı tek Markdown (komut + gömülü paket), adı
  `astra_tamir_v1_4.md`; ek olarak paket dizini depoda.
- V2 Komut dili Türkçe; kod yorumları İngilizce (v1.3 ile aynı).
- V3 "Kaçış bırakma" = çıkışları kaldırmak değil, artefakt şartına bağlamak (dürüstlük
  sözleşmesi çıkışları gerektirir).
- V4 Kod uyumluluğu: v1.3 config dosyaları (`decision.claim_ids` açık) çalışmaya devam eder;
  yeni alanlar isteğe bağlı ya da geri uyumlu; BLOCKED `attempts` fixture'ları güncellenir.
- V5 Canlı API davranışı (model alias/snapshot, strict şema) VARSAYIM etiketiyle
  toleranslı hale getirilir; doğrulama yapılamaz.
- V6 Hasım çürütme sonuçları (iş akışı) gelmeden plan yazılır; çürüyen bulguya bağlı
  madde plan gözden geçirme noktasında düşürülür.

## 8. Bulgu → değişiklik izlenebilirliği

Plan dosyasında her madde `bulgu:` satırıyla hangi kimliklere (K-xx, boyut-n) karşılık
geldiğini yazar; çürütülen bulgunun maddesi "ÇÜRÜDÜ — uygulanmadı" olarak kalır (sessiz
silme yok).
