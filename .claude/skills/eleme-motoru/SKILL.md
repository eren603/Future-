---
name: eleme-motoru
description: >-
  Eleme motoru — danışman/motor iddialarını kurula girmeden ÖNCE üç katmanda
  eleyen yanlış-pozitif kırıcı. Bir koşuda birden çok motor/danışman iddiası
  (yön sinyali, erken-uyarı bayrağı, seviye önerisi) sentez.py'ye girecekse
  OTOMATİK devreye girer — slash komutu gerekmez. Katmanlar: (1) SERT KURAL —
  regex desen aileleriyle genel felaket cümlesi, seviyesiz tavsiye, işletim
  bulgusu, düşük etkili/teorik mikro-yapı, kapsam dışı (canlı emir) iddiaları;
  (2) BAĞLAM KAPISI — türev iddiası fiyat-yapısı motorundan geliyorsa ya da
  turev kapsamı 0.5 altındaysa, squeeze/kaskad bayrağı RANGE rejimindeyse,
  elle okuma damgasız/240 dk'dan bayatsa; (3) EMSAL DENETİMİ — 33 maddelik
  emsal defterine (emsaller/emsal_defteri.yaml) karşı kontrol + 1-10 güven
  bandı. Çalışan motor scripts/eleme.py (öz-test: --self-test, 16 vaka).
  Tetikleyici kelimeler (TR/EN): eleme, ele, filtre, filter, yanlış pozitif,
  false positive, gürültü, noise, emsal, precedent, sinyal kalitesi, signal
  quality, danışman ayıklama, iddia denetimi, düşük sinyal, alert fatigue.
  Kaynak: claude-code-security-review eleme boru hattı (findings_filter.py +
  claude_api_client.py) — güvenlik alanından finans karar-desteğine çevrildi.
allowed-tools: Read, Bash
---

# Eleme Motoru (emsal defteri + bağlam-duyarlı filtre + eleme istatistiği)

## Neden var

`sentez.py` güven-ağırlıklı bir sentez yapar: **hangi iddiaların kurula
girdiğini sorgulamaz.** Zayıf, ölçüme bağlanmamış, yanlış motordan gelmiş ya da
bağlamı olmayan bir iddia kurula girdiğinde ağırlığını alır ve kararı kaydırır.
Kaynak boru hattının çözdüğü sorun tam da budur: *"filter out false positives
and low-signal findings to reduce alert fatigue"* (claude_api_client.py:190).

Bu motor **karar vermez**, yalnız gürültüyü ayıklar. Yön hükmü yine
`karar-kurulu/scripts/sentez.py` + `piramit-sistem/scripts/piramit.py`
sentezinden gelir.

## "Bulgu" bu depoda ne demek

Kaynakta bulgu = güvenlik bulgusu (`file` / `title` / `description`).
Burada bulgu = **danışman/motor iddiası** — `sentez.py`'nin danışman şeması:

```json
{
  "name": "turev-akis",            // danışman adı (gozlemci.py AILE eşlemesi)
  "stance": "short",               // long | short | flat
  "confidence": 0.71,              // 0..1
  "evidence": "OI %2.4 arttı + fiyat düştü → taze short; funding %0.041",
  "_verifier_confirmed": true,     // motorun kendi doğrulaması (fail-closed)
  "kaynak": "turev_akis.py",       // <- kaynaktaki `file` alanı
  "baslik": "taze short",          // <- kaynaktaki `title` alanı (ops.)
  "zaman_utc": "2026-07-28T11:40:00Z"   // elle okuma damgası (ops.)
}
```

## Koşum

```bash
# öz-test (16 vaka + ElemeIstatistigi dökümü)
python3 .claude/skills/eleme-motoru/scripts/eleme.py --self-test

# gerçek koşu
python3 .claude/skills/eleme-motoru/scripts/eleme.py --job is.json
```

`is.json`:

```json
{
  "bulgular": [ { "name": "...", "stance": "...", "confidence": 0.6,
                  "evidence": "...", "kaynak": "..." } ],
  "baglam": {
    "rejim": {"durum": "range", "adx": 14.2, "yuksek_vol": false},
    "turev_kapsam": 0.30,
    "turev_faktorler": [{"faktor": "liquidation", "skor": null}],
    "son_bar_utc": "2026-07-28T12:00:00Z"
  }
}
```

`baglam` alanlarının hepsi depodaki motorların GERÇEK çıktı alanlarıdır:
`rejim` ← `grafik-calisma/scripts/smc_tespit.py` (`durum` ∈ trend/range/gecis/
VERİ YOK), `turev_kapsam` ve `turev_faktorler` ← `turev-akis/scripts/
turev_akis.py` (`kapsam`, `faktorler[].skor`), `son_bar_utc` ← koşunun son barı.

## Üç katman

**1 — Sert kurallar** (`SertElemeKurallari`, deterministik regex, bağlamsız).
Önceden derlenmiş 5 desen ailesi + kaynak kapısı:

| Aile | Eler |
|---|---|
| `_GENEL_RISK_DESENLERI` | "piyasa çökebilir", "likidite kuruyabilir", kara kuğu |
| `_GENEL_TAVSIYE_DESENLERI` | "stop kullanılmalı", "risk yönetimi şart", "best practice" |
| `_ISLETIM_DESENLERI` | API anahtarı, bellek/CPU, bağlantı koptu, motor çöktü, "kullanıcı diyor ki" |
| `_DUSUK_ETKI_DESENLERI` | tek fitil gürültüsü, 1 tick sapma, "teorik olarak" |
| `_KAPSAM_DISI_DESENLERI` | canlı/otomatik emir, bot çalıştır (bu depo yalnız karar-desteği) |
| kaynak kapısı | `.md/.txt/.rst` belge kaynağı; `self_test.py`/örnek/kum-havuzu |

**2 — Bağlam kapıları** (`BaglamKapilari`): bir iddia yalnız belirli
rejim/kapsam/aile/tazelik bağlamında geçerlidir.

- **KAPI 1a** — türev iddiası (`OI/funding/CVD/LSR/likidasyon/deleveraging`)
  `fiyat-yapisi` ya da `tarihsel-kanit` ailesinden geliyorsa **elenir**:
  `karar-motoru` YALNIZ kline görür, türeve KÖRDÜR (`engine/README.md`,
  `turev_akis.py:4-8`). Aile eşlemesi `gozlemci.py` AILE sözlüğünden.
- **KAPI 1b** — türev iddiası + `turev_kapsam < 0.5` → elenir (`turev_akis.py`
  `kapsam_esigi`, fail-closed).
- **KAPI 2a** — squeeze/kaskad bayrağı + `rejim.durum == "range"` → elenir
  (yatay rejimde sıkışma bayrağının yönsel dayanağı yok).
- **KAPI 2b** — squeeze/kaskad bayrağı ama `liquidation` faktörü `skor: null`
  (VERİ YOK) → dayanaksız bayrak, elenir.
- **KAPI 3** — elle okuma (`gorsel-teyit` / `elle: true`) damgasız ya da son
  bardan **240 dk**'dan eski → **BAYAT**, elenir (`piramit.py`
  `zorunlu_damga_tolerans_dk`).

**3 — Emsal denetimi** (`EmsalDenetimi` → `emsaller/emsal_defteri.yaml`):
kaynaktaki **16 sert dışlama + 17 emsal = 33 madde** deftere birebir alıntıyla
yazılmıştır. Defterde `kontrol` bloğu olanlar makineyle koşar; alana
çevrilemeyen 5 madde `uygulanamaz: true` + gerekçesiyle kayıtlıdır (atlanmaz).
Ayrıca güven bandı uygulanır: **1-3 = gürültü → elenir** (kaynak ölçeği,
`claude_api_client.py:292-295`).

## Güven skoru (1-10)

`guven_10 = clamp(confidence,0,1) × 10`, doğrulanmamışsa `× refute_penalty
(0.25)` — `sentez.py:88`'in etkin-ağırlık aritmetiği. Elle görsel okumanın
güveni `gorsel_tavan = 0.50` ile sınırlanır (`piramit.py:724-732`): okuma bir
ölçüm değildir.

⚠️ **Kaynaktan bilinçli sapma:** kaynak fail-OPEN'dır (API hatasında/filtre
kapalıyken `confidence = 10.0` verip bulguyu tutar, `findings_filter.py:271,
302`). Bu depo **fail-closed** olmak zorundadır (CLAUDE.md, `sentez.py:74-87`):
`confidence` yoksa taban **0.0** alınır ve uyarı yazılır.

## Çıktı

```
tutulan_bulgular[]  — geçen iddialar (+ _eleme_verisi: guven_skoru, aile)
elenen_bulgular[]   — {bulgu, sira, eleme_gerekcesi, katman}   (sessiz kayıp YOK)
ozet{}              — sayımlar + eleme_dagilimi + ortalama_guven + sure_saniye
uyarilar[]          — güven tavanı / VERİ YOK / defter yüklenemedi
```

`ElemeIstatistigi` dataclass alanları (kaynak `FilterStats`'ın birebir
karşılıkları): `toplam_bulgu`, `sert_elenen`, `emsal_elenen`, `tutulan`,
`eleme_dagilimi`, `guven_skorlari`, `sure_saniye` (+ ek alan `baglam_elenen`).

## Sınırlar (dürüstlük)

- Eleme **anlam** denetlemez; desen ve bağlam denetler. Yorum doğruluğu elle
  ikinci-göz işidir (CLAUDE.md: grounding mekanikleştirilemez).
- Elenen iddia **yok sayılmaz**, gerekçesiyle raporlanır — gizlenen eleme
  `gozlemci.py` gözünde EKSIK_AKTARIM olurdu.
- Bu motor bir KARAR üretmez; yön/işlem hükmü sentezden gelir.
- Canlı/otomatik emir DAHİL DEĞİL.

## Kanıt

Kaynağa karşı satır satır doğrulama ve 33 madde izleme tablosu: `KANIT.md`.
