# FAZ 3 — Sayısal iddia doğrulama (ölçüldü, 2026-09-07, Python 3.11.15)

Komut: `cd astra/bundle_v1_3 && python3 -m unittest discover -s tests -p 'test_*.py'` → `Ran 113 tests ... OK`
Ölçüm betiği: bu dosyanın altındaki Python bloğu (astra/ dizininden koşuldu).

| İddia (belgede) | Ölçülen | Hüküm |
|---|---|---|
| "113 test geçti" (satır 7, 732, 752) | 113 test OK (35 astra + 15 comparison + 4 goal + 26 host_integration + 8 openai_reviewer + 25 router) | DOĞRU (3.11.15'te de) |
| "79 mevcut test uyarlandı; 26 host/entegrasyon ve 8 HTTP taşıma testi eklendi" (731) | v1.2: 79 (35+15+4+25); fark 34 = 26 + 8 | DOĞRU |
| Komut metni 19-410 ile gömülü astra_command.md 866-1257 aynı mı | 392 satır / 392 satır, unified diff 0 satır | AYNI (sürüklenme yok) |
| Atlas "66 konu / 306 kayıt" (65, 1808-1809) | topics=66, entries=306, count toplamı=306 | DOĞRU |
| Manifest dosya sayısı | 48 kayıt + BUNDLE_MANIFEST.json = 49 dosya; extract sonrası 49 dosya; hash/boyut denetimi geçti | DOĞRU |
| "Python 3.12.13 ile" (7, 752) | Bu ortam 3.11.15 — 3.12.13 iddiası burada yeniden üretilemedi, sonuç aynı | KISMEN (sürüm farklı, sonuç aynı) |
| Ret kodları test kapsamı (belgede iddia yok; ölçüm) | Kodda 118 `Rejected("...")` kodu; 78'inin adı hiçbir testte geçmiyor (bazıları adsız assertRaises ile dolaylı sınanıyor). Adı geçmeyenler arasında: CRITICAL_UNCERTAINTY, OWNER_REQUIRED, CLAIM_SCOPE, COVERAGE_INCOMPLETE, HOST_SOURCE_SCOPE, COMPARISON_SCOPE, COMPARISON_CONTRACT_AMBIGUOUS, SEMANTIC_EXCERPT_COVERAGE, SOURCE_CHANGED_DURING_READ, SOURCE_REGULAR_FILE_REQUIRED, RUN_ALREADY_FINISHED, REVIEW_PROVIDER_* (8 adet) | KAPSAM BOŞLUĞU (test eklenmeli) |

Ölçüm betiği:
```python
import re, json, pathlib, difflib, collections
doc = pathlib.Path('astra_tamir_v1_3.md').read_text(encoding='utf-8').splitlines()
cmd, emb = doc[18:410], doc[865:1257]
d = [l for l in difflib.unified_diff(cmd, emb, lineterm='', n=0) if l[:1] in '+-' and not l.startswith(('+++','---'))]
run = pathlib.Path('bundle_v1_3/verification/test_run.txt').read_text().splitlines()
mods = collections.Counter(re.search(r'\((\w+)\.', l).group(1) for l in run if l.endswith('... ok'))
codes = set()
for p in pathlib.Path('bundle_v1_3').glob('*.py'):
    codes |= set(re.findall(r'Rejected\("([A-Z_]+)"\)', p.read_text()))
tests = "".join(p.read_text() for p in pathlib.Path('bundle_v1_3/tests').glob('*.py'))
untested = sorted(c for c in codes if c not in tests)
```
Çıktı: fark=0; test/modül={'test_astra':35,'test_comparison':15,'test_goal_regressions':4,'test_host_integration':26,'test_openai_reviewer':8,'test_plugin_router':25}; v1.2 toplam 79; Rejected 118 / adı geçmeyen 78; atlas 66/306; manifest 48.

## Ek ölçümler (probes/, 2026-09-07)

`python3 astra/probes/probe_uncertain_card.py`:
```
phase: PHASE_VALIDATED
finalize (uncertain kart seçili): FAIL_CLOSED SEMANTIC_CLAIM_UNSUPPORTED
finalize (uncertain kart seçilmedi): FAIL_CLOSED SEMANTIC_CLAIM_UNSUPPORTED
```
→ Kritik OLMAYAN, kararda SEÇİLMEMİŞ tek bir `stance=uncertain` kart bile host kapısını
kapatıyor (astra_host.py `verify`: tüm kartlar için verdict zorunlu + `verdict == "uncertain"`
→ ret). Belge 6.1 "belirsizlik görünür kalsın" ve kart şemasındaki `uncertain` seçeneğiyle
ÇELİŞİR; işçiyi belirsizliği saklamaya ya da sahte kesinliğe İTER (dürüstlük-karşıtı teşvik).

`python3 astra/probes/probe_math_validate.py` (özet):
- owner 'n/a' / '-' / 'TBD' / '?' / 'N/A' / 'operator' → GEÇER (yalnız 'unknown'/'bilinmiyor' RED)
  → belge 6 "owner gerçek bir sorumlu olmalı" vaadi kodda yalnız iki kelimeyle karşılanıyor.
- exact_math: '1_000'→1000, '1.'→1, '.5'→1/2, '0x10'→UNSUPPORTED, '1e'→DOMAIN_OR_UNSUPPORTED,
  '2**-1'→1/2, '1e-400' sıfır değil, '10**20**1' → 10^20 (sağdan birleşme; Python semantiği).
- validate(None, nullable+enum) → SCHEMA_ENUM (None enum'da olmadığı için nullable enum imkânsız);
  validate('', min=0) geçer; bounded_json iç içe FORBIDDEN anahtarı yakalar, değer olarak geçirir.

`python3 astra/probes/probe_replay.py` (bundle_v1_4, Task 4 ÖNCESİ):
```
first: LOCAL_CHECKS_PASSED | second: LOCAL_CHECKS_PASSED None
request_digest equal: True
```
→ celiski-1 orkestratör tarafından bağımsız doğrulandı: aynı faz+aday için ikinci finalize
aynı request_digest ile geçiyor; nonce/kilit yok.

`python3 astra/probes/probe_replay.py` (Task 4 SONRASI): `first: LOCAL_CHECKS_PASSED | second: FAIL_CLOSED FINALIZE_ALREADY_DONE`, `request_digest equal: False` (nonce).
