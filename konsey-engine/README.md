# KONSEY Engine — canlı yön + giriş/çıkış sinyali

`KONSEY_Evidence_Engine.md` sözleşmesine birebir uyan kanıt kaydı ve yayın kapısı;
üstüne canlı yön / giriş-çıkış sinyal katmanı.

## Temel ilke (değiştirilmedi)

Modelin `VERIFIED` / `PUBLISH_FULL` beyanı **tek başına kabul edilmez**. Nihai kararı
`core.EvidenceRegistry.audit()` verir. Öz-test **T15** bunu kanıtlar: ajan
`PUBLISH_FULL` dese bile kapı `REPAIR` diyorsa yayın yapılmaz.

## Kurulum

```bash
cd konsey-engine && python3 -m pip install -e .
```

## Kullanım

```bash
konsey sinyal --symbols BTCUSDT,ETHUSDT --output outputs/sinyal.json   # yön + giriş/çıkış
konsey init   --output examples/task.json
konsey fetch  --input examples/task.json --output outputs/with-source.json \
              --location https://example.org --source-id S02 --evidence-id E02 --dependency-group G2
konsey audit  --input examples/task.json --output outputs/audit.json --requested-decision PUBLISH_FULL
konsey run    --input examples/task.json --output outputs/agent-result.json \
              --provider openai-compatible --base-url https://api.openai.com/v1 --model gpt-4o-mini
python3 -m konsey_engine.oz_test        # 15 test
```

Dönüş kodu `0` → yayın kapısı geçti. `2` → `PUBLISH_FULL` değil, yayın durdurulmalı.

## Sinyal nasıl üretilir

1. **Kaynak** — önce canlı OKX public mum ucu denenir; kapalıysa yerel arşive düşülür ve
   **düşüş kayda geçer** (`Source.note`). Erişilemeyen kaynak erişilmiş gibi kaydedilmez.
2. **Ölçüm** — `smc_tespit.detect` ile 15M ve 4H yapı (trend/ADX/rejim/ATR/FVG/likidite).
3. **Yön** — ağırlıklı ve **beyan edilmiş**: 4H trend 0.50 · 15M trend 0.30 · türev 0.20.
   `rejim=range` ise 15M ağırlığı %50 kırpılır. Eksik kanal **ağırlığa girmez** (uydurma yok).
4. **Emir** — seviyeler **yalnızca** `emir_plani.plan()` çıktısıdır. MARKET/LIMIT ayrımı
   `|giriş − fiyat| ≤ 0.1×ATR15` kuralıyla. Yön NÖTR ise **iki taraf da** üretilir.
5. **Seviye bilgisi** — emir kapısını geçemeyen adaylar da `bilgi_seviyeleri()` ile
   yer/yön olarak gösterilir (`rr_denetim`'den geçmiş `R_gercekci` ile), **işlem önerisi
   değil** etiketiyle. Kullanıcı "giriş yok" denince limitin nerede olduğunu görür.
6. **Kapı** — `registry.audit()`; bayat veri `external_checks_pending`'e yazılır ve
   yayın durur (fail-closed). Seviyeler yine gösterilir, işlem önerisi sayılmaz.

## Sağlayıcı bağlayıcıları

`adapters.py` ve `orchestrator.py` **verilen hâliyle korunmuştur**; `adapters.py`'ye
yalnızca README s.58'in izin verdiği ek bağlayıcı (`YerelOlcumAdapter`) **eklenmiştir** —
mevcut satırların hiçbiri değiştirilmedi (öz-test T14 doğrular).

## Güvenlik sınırı

Pasif kaynak edinimi. Oturum açma, ödeme, emir gönderme yok — kodda imza/anahtar/emir
ucu bulunmaz. Yalnız karar-destek.
