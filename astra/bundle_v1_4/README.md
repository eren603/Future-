ASTRA v1.4 — yerel tamir paketi

v1.3'ün kapıları korunuyor; bu sürüm o kapılardaki eksik, çelişki, hata ve
makyajı kapatıyor. Değişikliklerin tamamı bulgu kimliğine bağlıdır (`CHANGELOG.md`,
`BULGU_DEGISIKLIK.md`). Host veya inceleyici olmadan onay verilmez.

Doğrulama

`verification/` dizinindeki dosyalar ELLE yazılmaz; `scripts/regenerate_verification.py`
testleri ve dört yerel CLI senaryosunu GERÇEKTEN koşturup üretir ve koşulan Python
sürümünü kendisi yazar. Sayı ve sürüm bu yüzden bu belgede tekrarlanmaz —
`verification/test_result.json` ve `verification/cli_summary.json` okunur.

```bash
python3 scripts/regenerate_verification.py
```

Bu senaryolar YEREL CLI senaryolarıdır (fixture işçi ve fixture inceleyici):
boru hattını sınarlar, ANLAMI sınamazlar. Canlı OpenAI çağrısı yapılmadı; API
anahtarı yok ve sağlayıcı belgeleri bu ortamda erişilemez durumda.
`TEST_FIXTURE` inceleyicilerinin kabul yanıtları anlamsal model başarısı
sayılmaz. Ayrı süreçler üretim izolasyonu sağlamaz; bütün paket LOCAL_TEST'tir.

Python 3.11+ ve POSIX ortamında, bu dizinden:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 demo_local.py --case valid --output-dir demo_valid
python3 demo_local.py --case method_mismatch --output-dir demo_method
python3 demo_local.py --case semantic_rejection --output-dir demo_semantic
python3 demo_local.py --case reviewer_missing --output-dir demo_missing
```

Her demo için yeni bir çıktı dizini kullanılır. İlk demo 0, diğer üç demo 1 çıkış
kodu verir; olumsuz senaryolardaki FAIL_CLOSED beklenen sonuçtur. Demo kaynakları,
işçi yanıtları ve inceleyici kararları sentetiktir. Saklanmış eski demo config'leri
yerel yol ve süre koşulları içerir; yeni çalıştırma için `demo_local.py` ile
yeniden üret. Hazır kanıt dosyalarını yeni bir kaynak erişimi gibi kullanma.

Uygulama bağlantısı

Uygulama sahibi `SourceVault` kaynaklarını, görev kapsamlarını, zorunlu
karşılaştırmaları, gereksinim defterini ve inceleyiciyi çalıştırmadan önce
yapılandırır. `comparisons` boşsa anlamlı `comparison_exemption` zorunludur.
`requirements` isteğe bağlıdır; verildiğinde `VERIFIED` olan her gereksinim bu
koşuda var olan artefaktları adlandırmak zorundadır. `task_status` yapılandırmaya
YAZILAMAZ — host onu defterden türetir. Hiçbir işçi bu ayarı değiştiremez.

Kaynak `path` alanı MUTLAK yol olmalıdır: göreli yol koşu dizinine (`os.getcwd()`)
bağlanır ve aynı yapılandırma başka bir dizinden koşulduğunda başka bir dosyayı
gösterir. Kaynak yolları sembolik bağ içeremez (hiçbir bileşeninde); `kind="TOOL"` kaynak,
içeriğe bağlanan bir araç çağrısı kaydı ister. Bu kayıt `output_digest` ↔ içerik
bağını kanıtlar; `args_digest` ve `exit_status` KAYDEDİLİR ama doğrulanmaz.

`demo_valid/config.json`, tam alanları gösteren çalışır bir örnektir. `workers` ve
`reviewer.argv` çalıştırılabilir komut tanımlar; bu config güvenilir operatör
yapılandırmasıdır, modelden gelen görev verisi değildir.

Gerçek inceleyici tanımı Python ile şöyle oluşturulur:

```python
import sys
from pathlib import Path
from astra_host import ReviewerEndpoint

reviewer = ReviewerEndpoint(
    argv=(sys.executable, str(Path("astra_openai_reviewer.py").resolve())),
    kind="EXTERNAL_MODEL", model="gpt-6-astra", effort="max",
    timeout=60.0, credential_env=("OPENAI_API_KEY",),
    network=(("proxy", None), ("ca_bundle", None)),
)
```

API anahtarını host ortamına güvenli biçimde sağla; config, günlük veya işçi
zarfına yazma. Anahtar yalnız inceleyici alt sürecine aktarılır ve yalnız paketin
kendi adaptörü onu alabilir. Proxy ve CA paketi yalnız `network` alanından gelir;
ortamın `HTTPS_PROXY` değişkeni OKUNMAZ. Bağlantı tek
`https://api.openai.com/v1/responses` isteği yapar; araç çağrısı ve otomatik tekrar
yoktur. `store=false`, uzunluk anahtarları ayıklanmış taşıma şeması, model/effort ve
cevap kimliği kullanılır. Sağlayıcının tam şemayı kabul edip etmeyeceği
BİLİNMİYOR; bu yüzden doğrulama host tarafında yapılır. Ret, kesilme, model/effort
uyuşmazlığı ve erişim hatası sonucu durdurur; HTTP hatası yalnız sınıfıyla
raporlanır, sağlayıcı gövdesi okunmaz. Canlı model çağrısı sağlayıcı kullanım
maliyeti doğurur.

Config hazır olduğunda giriş:

```bash
python3 astra_run.py config.json --output result.json
```

Program `result.json` içine sonucu, host makbuzunu ve olay sırasını yazar. Kayıt
`COMPARISON_STARTED`, `COMPARISON_VALIDATED`, `SEMANTIC_REVIEW_STARTED` ve
`HOST_GATES_PASSED` olaylarını içerir; başarısız kapıda `FINALIZATION_REJECTED`
vardır. `decision.claim_ids` yerine `["*"]` yazılabilir: kart kimlikleri işçi
kapsamlıdır ve faz koşmadan bilinemez, host bunları faz sonrası genişletir.
`--output` yazılamıyorsa program traceback vermez, FAIL_CLOSED sonucu basar.

Kaynak ve anlam sınırı

SourceVault, UTF-8 yerel dosyaları sınırlandırılmış okumayla yakalar; dosya içerik
hash'ini incelemeden önce ve sonra kontrol eder. `as_of` ve `valid_until` gerçek
görev bilgisiyle operatör tarafından belirlenir; bilinmeyen tarih uydurulmaz.
Bu erişim, dosyanın alındığı internet sitesini veya üçüncü taraf beyanını
kimlik doğrulamalı biçimde kanıtlamaz; `source_access_authenticated` ve
`upstream_origin_verified` false kalır.

Karşılaştırma fonksiyonu sayı/alıntı/ölçüm koşullarını denetler; alıntılar NFKC
ile normalleştirilir, böylece Unicode eksi/tire işaretleri sayı denetimini
atlatamaz. Anlam desteği için ayrıca çalıştırılan inceleyici bütün kaynak
parçalarını, kartları, sayısal kanıtları, karşılaştırma sonuçlarını ve somut
çıktıyı görür — ama ARAMA ARACI YOKTUR: kaynaklarda bulunmayan karşı kanıt için
web araması iddia edemez ve eksik kanıtta `uncertain` döner. Bir LLM
inceleyicisinin yanılma ihtimali sürer; canlı model davranışı ve insan
değerlendirmesiyle uyumu ayrıca ölçülmelidir.

`semantic_support_verified`, EXTERNAL_MODEL adaptörünün gerçekten çağrılması ve
bağlı incelemesinin kabul edilmesi anlamındadır; nesnel doğruluğun garantisi
değildir. TEST_FIXTURE için false kalır. Fixture programı EXTERNAL_MODEL diye
etiketlenerek kullanılamaz ve API anahtarı alamaz.

Kalıcı iş zamanlayıcısı, gerçek kör LLM işçileri, web kaynağının köken doğrulaması,
üretim izolasyonu ve canlı model değerlendirmesi ayrı kapsamdır. Bu paket bunları
kurulmuş gibi göstermez. Kullanıcı teslimatı ve üretim onayı ayrı tutulur.

İçerik

- `astra_command.md`: tam güncel çalışma komutu (`tests/test_command_text.py` ile sınanır).
- `astra_reference.py`: zorunlu host çağrısı içeren denetleyici ve kesin aritmetik.
- `astra_host.py`: kaynak yakalama, donmuş sözleşme, gereksinim defteri,
  karşılaştırma ve inceleyici kapıları.
- `astra_openai_reviewer.py`: Responses API taşıma adaptörü (canlı çağrı ile sınanmadı).
- `astra_run.py`: CLI çalıştırıcı.
- `demo_local.py`: açıkça sentetik, yeniden üretilebilir çalışma örnekleri.
- `scripts/regenerate_verification.py`: `verification/` dizinini gerçek koşudan üretir.
- `tests/`: paketin testleri ve test amacıyla kullanılan işçi/inceleyici dosyaları.
- `verification/`: bu ortamda yapılan yerel koşunun kanıtları.
- `history/v1_2/`: önceki belgeden gelen tarihsel kayıtlar; bu sürümün sonucu değildir.

Resmî arayüz dayanakları (bu oturumda YENİDEN DOĞRULANAMADI — egress engelli;
bkz. `verification/source_review_notes.json`):
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[reasoning arayüzü](https://developers.openai.com/api/docs/guides/reasoning),
[Astra model ayarları](https://developers.openai.com/api/docs/models/gpt-6-astra).
