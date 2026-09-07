**ASTRA v1.4 — onarılmış çalışma komutu ve çalıştırılabilir paket (tek dosya)**

Durum: LOCAL_TEST. Canlı sağlayıcı çağrısı YAPILMADI (API anahtarı yok,
`developers.openai.com` bu ortamda egress engelli). `TEST_FIXTURE` inceleyicisinin
kabulü anlamsal model başarısı DEĞİLDİR. Üretim izolasyonu ve `APPROVED` bu paketle
üretilemez. Bu belge bir teslimattır; ayrıca indirilecek bir paket dosyası yoktur.

Bu dosya iki şey taşır: (1) aşağıdaki **çalışma komutu**, (2) «Gömülü dosyalar»
başlığından sonra paketin bütün dosyaları. Komut metni gömülü `astra_command.md`
ile BİREBİR aynıdır ve bu eşitlik `astra/tests/test_bundle_tools.py` tarafından
sınanır — belge başlığı ile paket birbirinden ayrı düşemez.

Paketi çıkarmak ve kendi testlerini koşturmak için:

```bash
python3 bundle_tools.py extract astra_tamir_v1_4.md ./astra_v1_4
cd astra_v1_4 && python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/regenerate_verification.py     # verification/ dizinini kendi koşunla üretir
```

`extract` her dosyayı manifestteki sha256 ve boyutla karşılaştırır; uyuşmazlık
varsa çıkarma durur. Hash bir kimlik doğrulama imzası değildir; yalnız içerik
bütünlüğü denetimidir.

---

**Çalışma komutu**

<!-- ASTRA_COMMAND_HERE -->

---

**Gömülü dosyalar**
