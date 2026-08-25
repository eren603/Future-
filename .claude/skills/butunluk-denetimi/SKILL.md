---
name: butunluk-denetimi
description: >-
  Bütünlük denetimi — bu depodaki TÜM becerilerin, kancaların ve ajanların
  yapısal bütünlüğünü mekanik denetleyen SON KATMAN (kendisi dahil, muafiyet
  yok). Yeni beceri/kanca/ajan eklendiğinde ya da "beceriler sağlam mı",
  "hangi beceri bozuk", "SKILL.md geçerli mi", "referans kopmuş mu",
  "öz-test geçiyor mu", "KANIT.md eksik mi", "depo denetimi" işlerinde
  OTOMATİK devreye girer — slash komutu gerekmez. Üç iş:
  (1) MANİFEST LİNT — frontmatter geçerli YAML mı, name dizin adıyla aynı
  mı, description 1024 karakter sert sınırını aşıyor mu; (2) REFERANS
  ÇÖZÜMLEME — SKILL.md gövdesinde adı geçen scripts/*.py, *.yaml, *.csv,
  *.json gerçekten var mı; (3) DRIFT/KODLAMA — py_compile, YAML/JSON/CSV
  ayrıştırma, UTF-8/BOM, settings.json kancalarının diskte varlığı ve +x
  biti, öz-testler exit 0 veriyor mu. Motor: scripts/butunluk.py (stdlib +
  pyyaml; --self-test, 23 vaka). Tetikleyiciler (TR/EN): bütünlük, denetim,
  lint, doğrula, validate, integrity, audit, manifest,
  frontmatter, referans, öz-test, self-test, kanca, hook.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# Bütünlük denetimi (SON KATMAN)

Bu depoya bir beceri, kanca ya da ajan eklendiğinde **yapının kendisi**
denetlenir. Bu beceri piyasa kararı üretmez; yalnız **artefakt bütünlüğü**
ölçer.

⚠️ Bu motor **piramit boru hattını KOŞTURMAZ**. `piramit.py`,
`karar_motoru.py` ve `saglik.py` öz-test yasak listesindedir
(`butunluk.py` içinde `OZTEST_YASAK`) — çünkü bunlar `engine/state/` ve
`hafiza/` sicillerini değiştirir. Denetim aracının yan etkisi olamaz.

## Koşum

```bash
# tam denetim (öz-testler dahil)
python3 .claude/skills/butunluk-denetimi/scripts/butunluk.py --depo .

# hızlı: öz-testleri koşturma, yalnız varlığını ara
python3 .claude/skills/butunluk-denetimi/scripts/butunluk.py --depo . --oztest-kosma

# makine okunur
python3 .claude/skills/butunluk-denetimi/scripts/butunluk.py --depo . --json

# aracın kendi öz-testi (23 vaka, sahte depo ağacı)
python3 .claude/skills/butunluk-denetimi/scripts/butunluk.py --self-test
```

## Çıkış kodları (fail-closed)

| Kod | Anlam |
|-----|-------|
| 0 | temiz |
| 1 | en az bir **HATA** |
| 2 | HATA yok ama en az bir **DENETLENEMEDİ** — denetlenemeyen şey GEÇTİ sayılmaz |
| 3 | bağımlılık yok (pyyaml) ya da `.claude/` bulunamadı |

`DENETLENEMEDİ` sessizce yutulmaz: çıkış kodunu ayrı bir değerle etkiler.
Böylece "hiç denetlenmedi" ile "denetlendi ve temiz" birbirine karışmaz.

## Denetlenen kurallar

**1. Manifest lint** (`denet_beceriler`)
- `SKILL.md` ve `KANIT.md` her beceri dizininde var mı (`ZORUNLU_BECERI_DOSYALARI`)
- frontmatter `---` ile başlıyor, kapanıyor ve geçerli YAML sözlüğü mü
- `name` + `description` alanları var mı
- `name` dizin adıyla **birebir aynı** mı, ≤ 64 karakter ve kebab-case mi
- `description` ≤ **1024** karakter mi ve `<` `>` içermiyor mu

**2. Referans çözümleme** (`denet_referanslar`)
SKILL.md gövdesindeki `dizin/dosya.uzanti` biçimli her token üç tabana karşı
çözümlenir: beceri dizini, depo kökü, `.claude/skills/`. Çözülmezse:
- koşuda üretilen artefakt (`state/`, `girdi/`, `hafiza/`) → **BİLGİ**
- ilk segmenti depoda var olan bir ağaç → **HATA** (kopuk referans)
- depoda hiç olmayan bir ağaç (kaynak deposu alıntısı) → **BİLGİ**, doğrulanamadı

**3. Drift / kodlama**
- `denet_settings` — `.claude/settings.json` geçerli JSON mü; her kanca dosyası
  diskte var mı; **doğrudan** çağrılıyorsa `+x` var mı (yorumlayıcı ile
  çağrılıyorsa `+x` gerekmez — bu ayrım bilerek yapılır)
- `denet_ajanlar` — `.claude/agents/*.md` frontmatter geçerli mi, `name` dosya
  adıyla aynı mı
- `denet_python` — her `.py` `py_compile` ile derleniyor mu
- `denet_veri_dosyalari` — `.yaml/.yml/.json/.csv` ayrıştırılıyor mu, CSV sütun
  sayısı başlıkla tutuyor mu
- `denet_oztestler` — her becerinin öz-test yolu var mı ve **exit 0** veriyor mu.
  İki gelenek de kabul edilir: motorun `--self-test` bayrağı **veya** beceri
  `scripts/` dizini altında ayrı bir `self_test` dosyası (bu beceri birinci
  geleneği kullanır: `butunluk.py --self-test`)

## Doğruluk sözleşmesi

- Uydurma yok; ölçülemeyen `DENETLENEMEDİ` olur, `GEÇTİ` olmaz.
- Her eşik bir kaynağa bağlıdır; bağlanamayan `[VARSAYIM]` diye etiketlenir
  (bkz. `KANIT.md`).
- Bu araç **kendi becerisini de** denetler; kendini muaf tutmak memnun etmedir.
- Dairesel doğrulama yok: `--self-test` sahte bir depo ağacı kurar, aracın
  kendi çıktısını kanıt saymaz.
