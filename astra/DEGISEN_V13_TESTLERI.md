# v1.3'ten devralınan testlerde yapılan değişiklikler (Task 11 → CHANGELOG girdisi)

Plan Global Constraints: "v1.3'ten gelen 113 test yalnız gerekçesi CHANGELOG'a yazılarak
değiştirilebilir (adı değişen test: eski ad → yeni ad + neden)". Bu dosya o kaydın
biriktiği yerdir; Task 11'de CHANGELOG.md'ye taşınır.

| # | Görev | Test / dosya | Değişiklik | Gerekçe |
|---|-------|--------------|-----------|---------|
| 1 | Task 2 | `test_lexically_matching_wrong_meaning_rejects_reviewer_verdict` → `test_fixture_uncertain_verdict_on_decision_claim_closes_gate` (tests/test_host_integration.py) | AD DEĞİŞTİ | Eski ad testin ölçtüğünden fazlasını iddia ediyordu: ret, anlam eşleşmesinden değil fixture'ın koşulsuz "uncertain" etiketinden geliyor. Ad artık ölçülen şeyi söylüyor (makyaj temizliği). |
| 2 | Task 4 | `test_valid_and_stale_source` (tests/test_astra.py) | İkinci bağımsız `controller()` ile ayrıldı | `FINALIZE_ALREADY_DONE` kilidi tek controller üzerinde iki finalize'ı kapatıyor; test aynı iddiayı (`SOURCE_STALE_OR_TIME`) ölçmeye devam ediyor, zayıflatılmadı. |
| 3 | Task 6 | fixture/demo kaynak tanımları (tests/host_fixture_support.py, tests/test_host_integration.py, tests/test_comparison.py, demo_local.py) | `kind="TOOL"` → `kind="USER", tool_call_record=None`; kart etiketi `ARAÇ` → `KULLANICI` | Bu dosyalar elle yazılmış kullanıcı dosyalarıdır, araç çıktısı DEĞİL. Yeni `SOURCE_TOOL_BINDING` kapısı doğru etiketlemeyi zorunlu kıldı. Kapıyı yumuşatmak için değil, yanlış etiketi düzeltmek için yapıldı. |
| 4 | Task 8 | `test_request_uses_real_responses_contract_and_bound_receipt` (tests/test_openai_reviewer.py) | `sent["text"]["format"]["schema"] == ASSESSMENT_SCHEMA` → `== transport_schema(ASSESSMENT_SCHEMA)` | Tele giden şema artık uzunluk anahtarlarından arındırılmış taşıma şemasıdır; host tam şemayla doğrulamaya devam eder. |
| 5 | Task 5 (deneme 2/3) | `test_symlinked_source_is_rejected` yanına `test_symlinked_parent_directory_is_rejected` eklendi | EKLEME (değişiklik değil) | Denetçi, ara dizin symlink'inin hâlâ izlendiğini yeniden üretti; kod_hata-7'nin ikinci yarısı ancak bu testle kapandı. |
