---
name: izleme-telemetri
description: >-
  Piramit boru hattının KENDİSİNİ ölçen yerel telemetri becerisi. Bir soru ya da
  iş "koşu ne kadar sürdü", "hangi katman yavaş", "hangi kapıda durduk", "hangi
  danışman doğrulanmıyor", "gözlemci kaç ihlal verdi", "zorunlu girdi kaç kez
  eksikti", "türev kapsamı ne", "aynı veriyle aynı sonucu alıyor muyuz"
  (determinizm), izleme, telemetri, metrik, ölçüm, gözlemlenebilirlik,
  performans raporu, boru hattı sağlığı ile ilgili olduğunda OTOMATİK devreye
  girer — slash komutu gerekmez. Çalışan motorlar; scripts/olcum.py
  (bağımlılıksız JSONL metrik yazıcı + `zamanlayici` context manager ile
  motor/katman sarmalama) ve scripts/rapor.py (JSONL → Markdown rapor; özet,
  katman/kapı dökümü, trend, mermaid). OTel/Prometheus/Grafana BU ORTAMDA KURULU
  DEĞİLDİR — dış yığın `sunucu/` altında OPSİYONELDİR. Tetikleyici kelimeler
  (TR/EN); izleme, telemetri, metrik, ölçüm, monitoring, observability, süre,
  latency, profil, darboğaz, bottleneck, kapı, gate, ihlal, determinizm, sağlık,
  health, dashboard, rapor, ROI.
---

# izleme-telemetri — piramit boru hattının kendi telemetrisi

Kaynak rehber (`a-claude-code-monitoring-guide`) Claude Code CLI'ın **token ve
maliyet** telemetrisini OpenTelemetry ile toplar. Bu depoda ölçülen şey token
değil, **piramit boru hattının kendisidir**: katman/motor süresi, kapı
durdurmaları, doğrulanmayan danışmanlar, gözlemci ihlalleri, zorunlu girdi
eksikleri, türev kapsamı, determinizm.

> ⚠️ **Docker / OpenTelemetry Collector / Prometheus / Grafana bu ortamda KURULU
> DEĞİLDİR.** Birincil yol tamamen yereldir: `scripts/olcum.py` → JSONL,
> `scripts/rapor.py` → Markdown. `sunucu/` altındaki üç dosya **opsiyonel** dış
> yığın içindir; bu depoda koşmaz, koşacakmış gibi de sunulmaz.

## Ne zaman devreye girer (tetikleyici gerekmez)

| Durum / soru | Eylem |
|---|---|
| "Koşu ne kadar sürdü / hangi katman yavaş" | `rapor.py` → Katman Süre Eğilimi |
| "Hangi kapıda kaç kez durduk" | `rapor.py` → Kapı Durumu |
| "Hangi danışman doğrulanmıyor" | `rapor.py` → Doğrulanmayan Danışmanlar |
| "Gözlemci kaç ihlal verdi, kaç koşu mühürlendi" | `rapor.py` → Gözlemci İhlalleri |
| "Zorunlu girdi kaç kez eksikti / kapsam ne" | `rapor.py` → Süre Analizi |
| "Aynı veriyle aynı sonucu alıyor muyuz" | `olcum.determinizm_olc` → determinizm |
| Bir piramit koşusu bitti | `olcum.py --rapor <rapor.json>` ile sayaçları çıkar |
| Bir motor/katman koşacak | `zamanlayici` ile sarmala |

## Ölçülen metrikler (defter — defterde olmayan ad YAZILMAZ)

`python3 scripts/olcum.py --defter` tam listeyi basar.

**SÜRE (HISTOGRAM, ms)**
- `piramit.kosu.sure_ms` — koşunun uçtan uca süresi
- `piramit.katman.sure_ms{katman}` — K1-LLM … K5-SI
- `piramit.motor.sure_ms{motor}` — smc_tespit, confluence, sentez, …

**SAYAÇ (COUNTER)**
- `piramit.kosu.sayisi{sembol,durum}`
- `piramit.kapi.gecti{katman}` / `piramit.kapi.durdu{katman,kapi}`
- `piramit.danisman.dogrulandi{danisman}` / `piramit.danisman.dogrulanmadi{danisman}`
- `piramit.gozlemci.ihlal{kod,katman,kritik}` / `piramit.gozlemci.uyari{kod}`
- `piramit.muhur` — kritik ihlalle mühürlenen koşu (işlem yok)
- `piramit.zorunlu_girdi.eksik{girdi}` — likidasyon / görsel okuma
- `piramit.motor.hata{motor}`
- `piramit.emir.uretildi{emir}`

**DAĞILIM (GAUGE)**
- `piramit.turev.kapsam` — turev-akis kapsamı (1.0 = tüm türev alanları geldi)
- `piramit.determinizm{veri_imzasi,sonuc_imzasi}` — 1 = aynı veri aynı sonuç

Katman adları `piramit.py`'nin `KATMANLAR` sabitinden, ihlal kodları
`gozlemci.py`'nin ihlal listesinden alınmıştır (uydurma ad yok).

## Kullanım

### 1) Motor/katman sarmalama (süre ailesi)

```python
import sys; sys.path.insert(0, ".claude/skills/izleme-telemetri/scripts")
from olcum import zamanlayici, yeni_kosu_id

kid = yeni_kosu_id()
with zamanlayici("piramit.kosu.sure_ms", kosu_id=kid, sembol="BTCUSDT"):
    with zamanlayici("piramit.katman.sure_ms", katman="K2-AI-AJAN",
                     kosu_id=kid, sembol="BTCUSDT"):
        k2 = k2_ajan(job, taban, k1)
    with zamanlayici("piramit.motor.sure_ms", motor="smc_tespit", kosu_id=kid):
        ...
```

Blok istisna atarsa süre **yine** yazılır (`durum="HATA"`) ve `motor` niteliği
varsa `piramit.motor.hata` sayacı artar — sessiz kayıp yok.

### 2) Bitmiş bir koşu raporundan sayaç çıkarımı

```bash
python3 .claude/skills/izleme-telemetri/scripts/olcum.py \
        --rapor .claude/skills/piramit-sistem/state/son_rapor.json --sembol BTCUSDT
```

`rapordan_yaz()` piramit raporunun **gerçek alanlarını** okur: `katmanlar[].gecti`
/ `kapi`, `K4-AGI.verifier[].confirmed`, `DENETIM.ihlal|uyari|muhurlendi`,
`ZIRVE.ZORUNLU_EKSIK`, `ZIRVE.EMIR`, `K2.motor_sonuclari["turev-akis"].rapor.kapsam`,
`K2.hatalar[]`. Süre metrikleri buradan **gelmez** (rapor süre taşımaz) —
süreler yalnız `zamanlayici` ile ölçülür.

### 3) Rapor üretimi

```bash
python3 .claude/skills/izleme-telemetri/scripts/rapor.py --out ornek/rapor.md
python3 .claude/skills/izleme-telemetri/scripts/rapor.py --json   # toplulaştırma
```

### 4) Öz-test (ikisi de çalışır durumda)

```bash
python3 .claude/skills/izleme-telemetri/scripts/olcum.py --self-test   # 15/15
python3 .claude/skills/izleme-telemetri/scripts/rapor.py --self-test   # 12/12
```

Örnek çıktılar: `ornek/olcum_ornek.jsonl`, `ornek/rapor_ornek.md`,
`ornek/self_test_olcum.json`, `ornek/self_test_rapor.json`.

## Ölçüm dosyası nerede

Varsayılan: `.claude/skills/izleme-telemetri/state/olcum.jsonl` (gitignore'da).

Neden `engine/state/` değil: o dizin **git-takiplidir** ve CLAUDE.md'ye göre her
koşudan sonra commit+push edilir — telemetri oraya yazılsaydı karar sicilini
gürültüyle doldururdu. `piramit-sistem/state/` ise başka bir becerinin koşu-artığı
dizinidir. İstenirse yönlendirilebilir:

```bash
--dosya engine/state/olcum.jsonl        # ya da
IZLEME_OLCUM_DOSYA=engine/state/olcum.jsonl
```

## Olay biçimi (OTel'e sadık)

Her JSONL satırı bir veri noktasıdır ve kaynak rehberdeki OTel konsol çıktısıyla
aynı alanları taşır — dış yığın kurulursa eşleme birebirdir:

```json
{"sema":"izleme-telemetri/1",
 "descriptor":{"name":"piramit.katman.sure_ms","type":"HISTOGRAM",
               "description":"Katman başına süre (K1-LLM … K5-SI)","unit":"ms"},
 "aile":"sure","attributes":{"katman":"K2-AI-AJAN","kosu_id":"…","sembol":"BTCUSDT",
 "durum":"TAMAM"},"value":2413.87,"ts_utc":"2026-07-28T23:29:55Z","ts_ms":…}
```

## Opsiyonel dış yığın (`sunucu/`) — KURULU DEĞİL

| Dosya | Kaynak karşılığı | Not |
|---|---|---|
| `sunucu/otel-collector-config.yaml` | `otel-collector-config.yaml` | OTLP alıcı + Prometheus dışa aktarıcı; JSONL→OTLP köprüsü YAZILMADI |
| `sunucu/prometheus.yml` | `prometheus.yml` | scrape hedefleri; `piramit-olcum` job'ı yorumda |
| `sunucu/grafana-dashboard.json` | `grafana/dashboards/working-dashboard.json` | 8 panel, kaynakla aynı yerleşim; sorgular piramit metriklerine çevrildi |

Bu dosyalar Docker/Grafana kurulu bir makinede kullanılmak içindir. Burada
**çalıştırılamaz**; "kuruldu/çalışıyor" diye sunulması yasaktır.

## Doğruluk sözleşmesi

- Metrik adı defterde yoksa **yazılmaz** (`OlcumHatasi`) — uydurma metrik yasak.
- Değer sayısal değilse yazılmaz; eksik alan **VERİ YOK**.
- Rapordaki her sayı JSONL'den okunur; içgörüler **etiketli eşik kuralından**
  türetilir ve eşikler raporun "Varsayımlar / eşik kaynağı" bölümünde açıkça
  listelenir (gizli sabit yok).
- Kıyas için 2'den az koşu varsa eğilim **uydurulmaz**, "VERİ YOK" yazılır.
- Bu beceri bir **karar** üretmez; yön/işlem hükmü yine `piramit-sistem` /
  `karar-kurulu` sentezinden gelir. Canlı/otomatik emir DAHİL DEĞİL.

Kaynak → uygulama izlenebilirliği: **KANIT.md** (birebir alıntılı eşleme tablosu,
metrik eşleme tablosu, sapmalar, öz-test çıktıları).
