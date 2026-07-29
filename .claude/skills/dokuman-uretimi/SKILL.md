---
name: dokuman-uretimi
description: >-
  Beceri dosyası (SKILL.md) üretim ve düzeltme kapısı. Bu depoda yeni bir beceri
  yazılacaksa, mevcut bir SKILL.md düzeltilecekse ya da bir soru beceri şablonu,
  frontmatter, YAML ayrışma hatası, "beceri yüklenmiyor", description karakter
  sınırı, name kuralı, kebab-case, tetikleyici sözleşmesi, "skill nasıl yazılır"
  ile ilgili olduğunda OTOMATİK devreye girer — slash komutu gerekmez. Beceri
  dosyasının kaynaktan sapmasını engeller: skill-creator disiplini şablona ve
  çalışan doğrulayıcıya taşınmıştır. Sert kurallar: name kebab-case ve en çok 64
  karakter, description en çok 1024 karakter ve açı parantezsiz. Çalışan motor:
  scripts/beceri_dogrula.py (stdlib + pyyaml; öz-test: --self-test; salt-okunur
  --depo kipi). Şablon: sablon/SKILL.md.sablon. Tetikleyici kelimeler (TR/EN):
  beceri, skill, SKILL.md, şablon, template, frontmatter, description, name,
  doküman üretimi, beceri yaz, beceri düzelt, skill creator, kebab-case, 1024.
---

# dokuman-uretimi — beceri dosyasının kaynaktan sapmasını engelleyen kapı

Bu beceri **piyasa kararı üretmez.** Tek işi: bu depoda bir `SKILL.md`
yazılırken ya da düzeltilirken kaynağın (Anthropic `skill-creator`) kurallarının
ve bu deponun beceri sözleşmesinin **mekanik olarak** uygulanmasıdır.

## Ne zaman devreye girer (tetikleyici gerekmez)

| Durum | Eylem |
|---|---|
| Yeni bir `.claude/skills/<ad>/` açılacak | `sablon/SKILL.md.sablon` doldurulur, sonra doğrulayıcı koşar |
| Mevcut bir `SKILL.md` düzeltilecek | düzeltme sonrası doğrulayıcı koşar (ihlal kalırsa iş bitmiş sayılmaz) |
| "Beceri yüklenmiyor / görünmüyor / frontmatter ayrışmıyor" | `AYRISMA_IKI_NOKTA` teşhisi (aşağıda) |
| "description çok mu uzun / name kuralı ne" | doğrulayıcı koşulur, sayı dosyadan okunur — hafızadan söylenmez |
| Depodaki bütün becerilerin manifesti sorulur | `--depo` kipi (SALT-OKUNUR) |

## Neden var

`skill-creator` kuralları bir insanın hatırlaması gereken metinde durursa
**sapma kaçınılmazdır**: description sessizce 1024'ü aşar, `name` dizin adından
ayrılır, düz YAML skaleri kırılır. Bu depoda üçü de gerçekten oldu. Bu yüzden
kurallar metinden **çalışan bir motora** taşındı; "GEÇTİ" hükmü artık
denetlenebilir bir çıktıdan gelir (fail-closed).

## Sözleşme — KAYNAKTAN taşınan sert kurallar

Her satırın atfı kaynak dosyanın satırıdır; hafızadan yazılmamıştır.

| Kural | Kaynak (birebir) | Kod |
|---|---|---|
| `SKILL.md` bulunmalı | `quick_validate.py:17-19` | `YOK_SKILL_MD` |
| Dosya `---` ile başlamalı | `quick_validate.py:23-24` | `YOK_FRONTMATTER` |
| Frontmatter `^---\n(.*?)\n---` ile kapanmalı | `quick_validate.py:27-29` | `GECERSIZ_FM_BICIM` |
| Frontmatter geçerli YAML olmalı | `quick_validate.py:38-39` | `FM_YAML_HATASI` |
| Frontmatter sözlük olmalı | `quick_validate.py:36-37` | `FM_SOZLUK_DEGIL` |
| İzinli anahtarlar: `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility` | `quick_validate.py:42` | `BEKLENMEYEN_ANAHTAR` |
| `name` zorunlu | `quick_validate.py:53-54` | `EKSIK_NAME` |
| `description` zorunlu | `quick_validate.py:55-56` | `EKSIK_DESCRIPTION` |
| `name` metin olmalı | `quick_validate.py:60-61` | `NAME_METIN_DEGIL` |
| `name` kebab-case (`^[a-z0-9-]+$`) | `quick_validate.py:65-66` | `NAME_KEBAB_DEGIL` |
| `name` başta/sonda tire ve `--` içeremez | `quick_validate.py:67-68` | `NAME_TIRE_HATASI` |
| `name` en çok **64** karakter | `quick_validate.py:70-71` | `NAME_COK_UZUN` |
| `description` metin olmalı | `quick_validate.py:75-76` | `DESC_METIN_DEGIL` |
| `description` açı parantezi içeremez | `quick_validate.py:80-81` | `DESC_ACI_PARANTEZ` |
| `description` en çok **1024** karakter | `quick_validate.py:83-84` | `DESC_COK_UZUN` |
| `compatibility` metin, en çok 500 karakter | `quick_validate.py:89-92` | `COMPAT_*` |
| `description` yaklaşık 100-200 kelime | `improve_description.py:132` | `DESC_COK_KELIME` (UYARI) |
| "When to trigger, what it does" — tetiklenme bilgisi description'da | `skill-creator/SKILL.md:67` | `DESC_NIYET_YOK` (UYARI) |

Kaynağın doğrudan kod karşılığı olmayan, ama üretimde uyulan yazım kuralları:

- Gövde 500 satırın altında kalır; aşarsa `references/` katmanı açılır
  (`skill-creator/SKILL.md:96`).
- Emir kipi kullanılır (`skill-creator/SKILL.md:117`).
- Description "biraz ısrarcı" yazılır — kaynak Claude'un beceriyi
  **az tetiklediğini** söyler (`skill-creator/SKILL.md:67`).

## DEPO EKİ kuralları (KAYNAKTA YOK — etiketlidir)

Bunlar `skill-creator` kaynağında **bulunmaz**; bu depoda ölçülmüş gerçek
kusurlardan türetilmiştir ve motor çıktısında `DEPO EKI` etiketiyle basılır.

| Kod | Kural | Gerekçe |
|---|---|---|
| `AYRISMA_IKI_NOKTA` | `description` düz YAML skaleri içinde `": "` geçemez | Geçerse YAML "mapping values are not allowed in this context" verir, frontmatter AYRIŞMAZ, beceri **hiç yüklenmez**. Çözüm: katlanmış blok `>-`. Bu depoda gerçekten oldu. |
| `NAME_DIZIN_UYUSMAZ` | `name` = dizin adı | Kaynak yalnız "preserve the original name" der (`skill-creator/SKILL.md:439`); **eşitlik şartı kaynakta yoktur**. Bu depoda 22/22 beceri eşit — sözleşme buradan ölçüldü. |
| `MOTOR_OZTEST_YOK` | `scripts/` varsa en az bir motor `--self-test` taşır ya da `self_test.py` adlı ayrı bir dosya bulunur | Denetlenemeyen "GEÇTİ" sayılmaz. |
| `TETIKLEYICI_SOZLESME` | description "OTOMATİK devreye girer — slash komutu gerekmez" + "Tetikleyici kelimeler" taşır | Depo geleneği: 22 beceriden 20'si. UYARI seviyesi. |
| `KATLANMIS_BLOK_ONER` | 200 karakterden uzun description katlanmış blokla yazılır | 22 beceriden 21'i böyle. UYARI seviyesi. |

## Kullanım (motor koşar, elle göz kararı verilmez)

```bash
# tek beceri
python3 .claude/skills/dokuman-uretimi/scripts/beceri_dogrula.py \
    --beceri .claude/skills/<ad>

# depodaki bütün beceriler (SALT-OKUNUR — hiçbir dosyayı değiştirmez)
python3 .claude/skills/dokuman-uretimi/scripts/beceri_dogrula.py --depo .

# öz-test (geçici dizinde sahte beceri ağacı; çalışma ağacını KİRLETMEZ)
python3 .claude/skills/dokuman-uretimi/scripts/beceri_dogrula.py --self-test

# ornek/ çıktılarını BİLEREK tazele (öz-test bunu kendiliğinden yapmaz)
python3 .claude/skills/dokuman-uretimi/scripts/beceri_dogrula.py \
    --ornek-tazele .claude/skills/dokuman-uretimi/ornek --depo .
```

Çıkış kodu: `0` = HATA yok, `1` = en az bir HATA (fail-closed), `2` = kullanım
hatası. UYARI çıkış kodunu değiştirmez — ihlal ile öneri karıştırılmaz.

## Yeni beceri üretim akışı

1. `sablon/SKILL.md.sablon` dosyasını `.claude/skills/<ad>/SKILL.md` olarak
   kopyala; büyük harfli yer tutucuların **hepsini** doldur, son bölümü sil.
2. Kaynaktan üretiliyorsa kaynağı **TAMAMEN** oku (satır + sha doğrula) ve
   `KANIT.md` yaz: birebir alıntı tablosu, taşınmayan kurallar + gerekçe,
   sapmalar, `[VARSAYIM]` / DEPO EKİ etiketleri.
3. Motoru `scripts/` altına yaz, `--self-test` ver; öz-test **geçici dizine**
   yazsın (takipli dosyayı tazelemek ayrı bayrakla olur).
4. Doğrulayıcıyı koştur. HATA varsa iş bitmemiştir.

## Sınırlar (dürüstlük — uydurma yok)

- **Resmî şartname metni bu depoda YOKTUR.** `spec/agent-skills-spec.md`
  yalnız 3 satırdır ve <https://agentskills.io/specification> adresine
  yönlendirir; adres bu ortamdan **403 Forbidden** verdi (WebFetch ve curl,
  iki ayrı deneme). Şartnamenin yerel metni = **VERİ YOK**. Bu yüzden
  buradaki sınırlar (64 / 1024 / 500) şartnameden değil, `quick_validate.py`
  kodundan alınmıştır; kodun yorumu "per spec" der ama şartname metni
  **doğrulanamamıştır**.
- Bu motor **anlam denetlemez**: description'ın gerçekten iyi tetikleyip
  tetiklemediği ölçülmez (o iş `skill-creator`'ın eval döngüsüdür ve
  `claude -p` gerektirir — burada koşulmadı).
- `butunluk-denetimi` becerisiyle **kısmi örtüşme vardır** (o da manifest
  lint + 1024 kontrolü yapar). Bu beceri ondan farklı olarak *üretim*
  tarafındadır: şablon + kaynak atfı + DEPO EKİ ayrımı. Örtüşen kontrol
  ikisinde de bağımsız hesaplanır; biri diğerinin çıktısını okumaz
  (dairesel doğrulama yasak).
- Bu beceri başka becerilerin dosyalarını **DEĞİŞTİRMEZ**; yalnız raporlar.

## Doğruluk sözleşmesi

- Eksik veri "VERİ YOK" işaretlenir; uydurma sayı yasak.
- Gerçek / varsayım / yorum ayrılır.
- Kaynakta olmayan her kural `DEPO EKI` etiketiyle basılır — etiketsiz gizli
  kural yoktur.
- Bu becerinin kendi `SKILL.md`'si de kendi doğrulayıcısından geçer; öz-test
  bunu ayrı bir vaka olarak sınar (kendini muaf tutmak = memnun etme).
