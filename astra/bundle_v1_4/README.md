ASTRA v1.3 — nihai yerel tamir paketi

Karşılaştırma ve inceleyici kapıları artık `Controller.finalize` yoluna bağlıdır.
Host veya inceleyici olmadan onay verilmez. v1.2'den taşınan yapısal testler yeni
zorunlu host arayüzüne uyarlandı. Yeni testler gerçek kaynak okumasını, alt süreç
çağrısını, karşılaştırma çağrısını ve olumsuz sonuçların yayını durdurmasını sınar.

Doğrulama: Python 3.12.13 ile 113 test geçti; hata, başarısızlık ve atlama yok.
Yerel CLI üzerinden dört ayrı senaryo da beklenen sonucu verdi. Sonuçlar
`verification/` dizinindedir. Canlı OpenAI çağrısı yapılmadı; API anahtarı mevcut
değildi. `TEST_FIXTURE` inceleyicilerinin kabul yanıtları anlamsal model başarısı
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

Gerçek uygulama bağlantısı

Uygulama sahibi `SourceVault` kaynaklarını, görev kapsamlarını, zorunlu
karşılaştırmaları ve inceleyiciyi çalıştırmadan önce yapılandırır. `comparisons`
boşsa anlamlı `comparison_exemption` zorunludur; inceleyici bu gerekçeyi gerçek
görevle karşılaştırır. Hiçbir işçi bu ayarı değiştiremez.

`demo_valid/config.json`, tam alanları gösteren çalışır bir örnektir. Gerçek
kullanımda kaynaklar ve işçi komutları uygulamaya ait olmalıdır. `workers` ve
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
)
```

API anahtarını host ortamına güvenli biçimde sağla; config, günlük veya işçi
zarfına yazma. Anahtar yalnız inceleyici alt sürecine aktarılır. Bağlantı tek
`https://api.openai.com/v1/responses` isteği yapar; araç çağrısı ve otomatik tekrar
yoktur. `store=false`, yapılandırılmış assessment şeması, model/effort ve cevap
kimliği kullanılır. Ret, kesilme, model/effort uyuşmazlığı ve erişim hatası sonucu
durdurur. Canlı model çağrısı sağlayıcı kullanım maliyeti doğurur.

Config hazır olduğunda gerçek giriş:

```bash
python3 astra_run.py config.json --output result.json
```

Program `result.json` içine sonucu, host makbuzunu ve olay sırasını yazar. Kayıt
`COMPARISON_STARTED`, `COMPARISON_VALIDATED`, `SEMANTIC_REVIEW_STARTED` ve
`HOST_GATES_PASSED` olaylarını içerir. Başarısız kapıda `FINALIZATION_REJECTED`
vardır. Eski `finalize(decision, review, sources)` çağrısı kullanılabilir; dışarıdan
verilen review yalnız ek ret koşulu olabilir. Gerçek host çağrısının yerine geçmez.

Kaynak ve anlam sınırı

SourceVault, UTF-8 yerel dosyaları sınırlandırılmış okumayla yakalar; dosya içerik
hash'ini incelemeden önce ve sonra kontrol eder. `as_of` ve `valid_until` gerçek
görev bilgisiyle operatör tarafından belirlenir; bilinmeyen tarih uydurulmaz.
Bu erişim, dosyanın alındığı internet sitesini veya üçüncü taraf beyanını
kimlik doğrulamalı biçimde kanıtlamaz. Bu yüzden `source_access_authenticated`
ve `upstream_origin_verified` false kalır.

Karşılaştırma fonksiyonu sayı/alıntı/ölçüm koşullarını denetler. Anlam desteği için
ayrıca çalıştırılan inceleyici bütün kaynak parçalarını, kartları, sayısal kanıtları,
karşılaştırma sonuçlarını ve somut çıktıyı görür. Kaynaklarda bulunmayan karşı
kanıt için yapılmış web araması iddia edemez; gereken kanıt eksikse incelemeyi
reddetmelidir. Bir LLM inceleyicisinin yanılma ihtimali sürer. Canlı model davranışı
ve insan değerlendirmesiyle uyumu ayrıca ölçülmelidir.

`semantic_support_verified`, EXTERNAL_MODEL adaptörünün gerçekten çağrılması ve
bağlı incelemesinin kabul edilmesi anlamındadır; nesnel doğruluğun garantisi
değildir. TEST_FIXTURE için false kalır. Fixture programı EXTERNAL_MODEL diye
etiketlenerek kullanılamaz; bu tür yalnız paketin sabit OpenAI adaptörünü kabul eder.

Kalıcı iş zamanlayıcısı, gerçek kör LLM işçileri, web kaynağının köken doğrulaması,
üretim izolasyonu ve canlı Astra Max değerlendirmesi ayrı kapsamdır. Bu paket
bunları kurulmuş gibi göstermez. Kullanıcı teslimatı ve üretim onayı ayrı tutulur.

İçerik

- `astra_command.md`: tam güncel çalışma komutu.
- `astra_reference.py`: zorunlu host çağrısı içeren denetleyici ve kesin aritmetik.
- `astra_host.py`: kaynak yakalama, donmuş sözleşme, karşılaştırma ve inceleyici kapıları.
- `astra_openai_reviewer.py`: gerçek Responses API taşıma adaptörü.
- `astra_run.py`: gerçek CLI çalıştırıcı.
- `demo_local.py`: açıkça sentetik, yeniden üretilebilir çalışma örnekleri.
- `tests/`: 113 test ve test amacıyla kullanılan işçi/inceleyici dosyaları.
- `verification/`: bu sürümün gerçek yerel çalıştırma kanıtları.
- `history/v1_2/`: önceki belgeden gelen tarihsel kayıtlar; v1.3 sonucu değildir.

Resmî arayüz dayanakları: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[reasoning arayüzü](https://developers.openai.com/api/docs/guides/reasoning),
[Astra model ayarları](https://developers.openai.com/api/docs/models/gpt-6-astra).
