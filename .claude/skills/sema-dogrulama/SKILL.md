---
name: sema-dogrulama
description: >-
  Elle gelen (UNTRUSTED) girdi dosyalarını şemaya karşı doğrulayan
  enjeksiyona-dayanıklı kapı. Bir dosya insan/panel/ekran-görüntüsü okumasıyla
  üretildiyse ve motora girecekse OTOMATİK devreye girer — slash komutu
  gerekmez. Özellikle engine/girdi/gorsel_okuma.json ve
  engine/girdi/turev_ham/likidasyon.json (zorunlu girdiler) boru hattına
  girmeden ÖNCE doğrulanır. Şema korkulukları: maxLength, pattern, enum,
  additionalProperties:false, maxItems, required, minimum/maximum. Çalışan motor
  scripts/sema_dogrula.py — stdlib-only (jsonschema BU DEPODA KURULU DEĞİL);
  geçerliyse exit 0 + "OK", geçersizse exit 1 + stderr'e "INVALID: <mesaj> at
  <yol>". Tetikleyici kelimeler (TR/EN): şema, sema, doğrula, validate, schema,
  JSON doğrulama, girdi denetimi, prompt injection, enjeksiyon, untrusted, elle
  girdi, panel okuması, görsel okuma, likidasyon dosyası, zorunlu girdi
  kontrolü.
---

# sema-dogrulama — untrusted girdi kapısı

## Ne zaman devreye girer (tetikleyici gerekmez)

| Durum | Eylem |
|---|---|
| `engine/girdi/gorsel_okuma.json` yazıldı/güncellendi | `semalar/gorsel_okuma.json` ile doğrula |
| `engine/girdi/turev_ham/likidasyon.json` yazıldı/güncellendi | `semalar/likidasyon.json` ile doğrula |
| Elle/panelden okunan herhangi bir JSON motora girecek | önce doğrula, sonra motora ver |
| Kullanıcı "şemaya uyuyor mu / doğrula / validate" dedi | doğrudan koştur |

Doğrulama **motordan ÖNCE** koşar. Geçmeyen dosya boru hattına girmez —
`piramit-sistem` bunu "ZORUNLU GİRDİ EKSİK" gibi ele alır; eksik/bozuk girdiyle
karar UYDURULMAZ (fail-closed).

## Neden var — gerekçe kaynaktan

`reader.yaml`, UNTRUSTED belge okuyan bir alt-ajanın çıktı şemasını tanımlar ve
şemanın üstündeki yorum gerekçeyi birebir yazar:

> `# Not an API field — consumed by scripts/validate.py, which validates worker`
> `# output against this schema before returning it to the orchestrator. String`
> `# fields are length-capped and character-class-restricted so injected`
> `# instructions cannot survive intact.`
>
> — `managed-agent-cookbooks/gl-reconciler/subagents/reader.yaml:31-34`

Aynı dosyanın başındaki izolasyon notu da aynı şeyi söyler:

> `# Isolation: read-only tools, no MCP servers, no bash, no write. Its only`
> `# output channel is the structured JSON below, which the deploy harness`
> `# validates (length + character class) before the orchestrator sees it.`
>
> — `reader.yaml:3-5`

Bu depoda durum birebir aynıdır: `gorsel_okuma.json` bir **ekran görüntüsünden
okunan serbest metindir** ve `likidasyon.json` bir **panelden elle
yapıştırılır**. İkisi de karar boru hattına girer. Enjekte edilmiş bir talimatın
bütün hâlde hayatta kalmaması için her string alan **uzunluk-kapaklı** ve
**karakter-sınıfı-kısıtlıdır**; sabit sözcük dağarcığı olan alanlar `enum`,
nesneler `additionalProperties: false`, diziler `maxItems` ile kapatılmıştır.

## Nasıl kullanılır

```bash
# tek dosya doğrulama (kaynak validate.py ile aynı sözleşme)
python3 .claude/skills/sema-dogrulama/scripts/sema_dogrula.py \
        engine/girdi/gorsel_okuma.json \
        .claude/skills/sema-dogrulama/semalar/gorsel_okuma.json
# → stdout "OK", exit 0

python3 .claude/skills/sema-dogrulama/scripts/sema_dogrula.py \
        engine/girdi/turev_ham/likidasyon.json \
        .claude/skills/sema-dogrulama/semalar/likidasyon.json

# öz-test (16 vaka: geçerli + her korkuluk için ihlal)
python3 .claude/skills/sema-dogrulama/scripts/sema_dogrula.py --self-test
```

Çıkış kodları — kaynak `scripts/validate.py:5` sözleşmesi:
`Exits 0 on valid, 1 on invalid (message to stderr)`; argüman sayısı yanlışsa
`__doc__` stderr'e basılır ve **2** döner.

Hata biçimi (kaynak `validate.py:35` ile aynı):

```
INVALID: 'escalate_to_admin' is not one of ['clean', 'breaks_found', 'error'] at status
INVALID: array is too long (11 > maxItems 10) at breaks/0/evidence_refs
```

`<yol>` JSON yolunun `/` ile birleştirilmiş hâlidir; kök düzeyi ihlallerinde boş
kalır (kaynakla aynı davranış).

## Desteklenen anahtar kelimeler (stdlib alt kümesi)

`type` (object/array/string/number/integer/boolean/null), `required`, `enum`,
`pattern` (`re`), `maxLength`, `minLength`, `maxItems`, `minItems`,
`additionalProperties: false`, `properties`, `items`, `minimum`, `maximum`.

**`jsonschema` bu depoda KURULU DEĞİLDİR** — motor saf stdlib'dir. Uygulanmayan
anahtar kelimeler ve diğer sapmalar `KANIT.md → SAPMALAR` bölümünde tek tek
yazılıdır. Şemada bilinmeyen bir `type` adı geçerse doğrulayıcı sessizce
geçmez, hata verir (fail-closed).

## Yeni şema yazarken kural (kaynak desenine sadakat)

1. Her `type: string` alanı **`maxLength` + `pattern`** almalı — ikisinden biri
   eksikse alan enjeksiyon taşıyabilir.
2. Sabit sözcük dağarcığı olan alan `enum` olmalı (serbest string değil).
3. Her `type: object` **`additionalProperties: false`** olmalı.
4. Her `type: array` **`maxItems`** almalı.
5. Motorun okuduğu alanlar `required` olmalı.
6. Alan adları **UYDURULMAZ**: gerçek girdi dosyasından ya da o dosyayı okuyan
   koddan alınır ve şemanın `_kaynak_alanlar` bloğunda dosya:satır ile
   gösterilir.

⚠️ Bu beceri bir KARAR üretmez; yalnız girdi kapısıdır. Yön/işlem hükmü
`piramit-sistem`/`karar-kurulu` sentezinden gelir.
