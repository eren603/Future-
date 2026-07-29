---
name: dogrulama-zinciri
description: >-
  Doğrulama zinciri — bir piramit koşusunun KARARINI (yön iddiası, emir
  seviyeleri, danışman duruşları, kapı hükümleri) kademeli olarak inceleyen
  üç adımlı ikinci-göz becerisi. Bir koşu raporu üretildikten sonra, "bu karar
  doğru mu", "kanıtı var mı", "bu bulgu gerçek mi", "ikinci göz", "değerlendir",
  "denetle", "kararı incele", "yanlış pozitif mi" gibi bir iş çıktığında
  OTOMATİK devreye girer — slash komutu gerekmez. Üç adım: (1) MALİYET KADEMESİ
  — pahalı doğrulamaya girmeden ucuz ön eleme (koşu kapıda mı durdu, zorunlu
  girdi eksik mi, yön nötr + emir yok mu, bu koşu zaten değerlendirildi mi, veri
  ilerledi mi); (2) BULGU DOĞRULAYICI — her iddia için bağımsız çoklu-oy, HIGH
  SIGNAL ölçütü ve yanlış-pozitif listesi, doğrulanmayan ELENİR; (3) ŞÜPHECİ
  DEĞERLENDİRİCİ (`.claude/agents/degerlendirici.md`) — raporu AÇMADAN PASS
  veremeyen, yalnız Read/Glob/Grep taşıyan ikinci-göz ajanı. Çalışan motorlar:
  scripts/kademe.py, scripts/bulgu_dogrula.py (stdlib; öz-testli). Tetikleyici
  kelimeler (TR/EN): doğrulama, doğrula, ikinci göz, değerlendirici, evaluator,
  inceleme, review, kod incelemesi, bulgu, finding, yanlış pozitif, false
  positive, yüksek sinyal, high signal, kademe, ön eleme, triage, maliyet, oy,
  çoğunluk, vote, PASS, NEEDS_WORK, kanıt, evidence, denetle, audit.
---

# Doğrulama zinciri — ucuz ele, pahalı doğrula, şüpheci hüküm ver

## Neden tek beceri

Kaynakta (`cc/plugins/code-review/commands/code-review.md`) bu üç iş **aynı
incelemenin ardışık adımlarıdır**: önce ucuz ön eleme (adım 1-3), sonra bulgu
üretimi ve bulgu başına doğrulama (adım 4-6), sonra hüküm (adım 7). Şüpheci
ikinci-göz sözleşmesi (`evaluator.md`) o hükmün biçimidir, çoklu-oy deseni
(`verify/SKILL.md`) ise doğrulamanın kanıt disiplinidir. Üçünü ayırmak zinciri
kırar: ön eleme olmadan her koşu pahalı doğrulamaya girer, doğrulama olmadan
hüküm akla-yatkınlıkla verilir.

**İnceleme konusu bu depoda bir PR değil, bir piramit koşusunun kararıdır**:
`ZIRVE.YON_BIAS`, `ZIRVE.EMIR`, `ZIRVE.emir_adaylari[]`,
`ZIRVE.sentez_karari`, `ZIRVE.kapi_gerekceleri`, `K3.danismanlar[]`,
`K4.verifier`, `K5.sentez`, `DENETIM`.

## Akış

```
son_rapor.json
   │
   ├─ 1. kademe.py            ucuz  ← haiku (code-review.md:14,24)
   │      5 ön eleme kapısı + mühür muafiyeti
   │      → DUR  : pahalı kademe HİÇ koşmaz (exit 1)
   │      → DEVAM: sözleşme yolları (ucuz) + koşu özeti (orta, :28)
   │
   ├─ 2. bulgu_dogrula.py     orta+pahalı ← sonnet/opus (:32,35,38,55)
   │      4 inceleyici → HIGH SIGNAL kapısı (:41-51)
   │      → yanlış-pozitif listesi (:79-86) → bulgu başına çoklu-oy
   │      → doğrulanmayan ELENİR (:57)
   │
   └─ 3. .claude/agents/degerlendirici.md
          raporu AÇAR, oy kayıtlarının işaret ettiği alanları tek tek okur
          → ilk satır: çıplak PASS ya da NEEDS_WORK
```

Adım 1 `DUR` derse adım 2 ve 3 **koşulmaz** — kademelemenin tek varlık sebebi
budur. Adım 2 doğrulanmış bulgu üretirse adım 3'ün hükmü `NEEDS_WORK` olmalıdır;
`PASS` yalnız kanıt AÇILARAK verilebilir.

## Motor 1 — `scripts/kademe.py` (maliyet kademesi)

```bash
python3 .claude/skills/dogrulama-zinciri/scripts/kademe.py \
    --rapor .claude/skills/piramit-sistem/state/son_rapor.json \
    --kok /home/user/Future- --ozet
python3 .claude/skills/dogrulama-zinciri/scripts/kademe.py --self-test
```

Beş ucuz kapı (hepsi kaynak adım 1'in çevirisidir):

| Kapı | Kaynak | Bu depodaki karşılığı |
|---|---|---|
| `kapali` | `:15` PR is closed | `durum` = "DURDU — …" ya da `ZIRVE.iki_satir` yok |
| `taslak` | `:16` PR is a draft | `ZIRVE.ZORUNLU_EKSIK` dolu |
| `onemsiz` | `:17` does not need code review | `YON_BIAS` nötr **ve** emir yok |
| `zaten_yapildi` | `:18` Claude has already commented | parmak izi değerlendirme defterinde |
| `veri_ayni` | depo eki (kanca kuralı) | son bar defterdeki son kayıttan yeni değil |

**Muafiyet** — kaynağın tek istisnası (`:22` "Note: Still review Claude
generated PR's."): `DENETIM.muhurlendi` ise `onemsiz` kapısı **uygulanmaz**.
Mühürlü koşuda `piramit.py:1664` EMİR'i kapatır; o koşu "önemsiz" görünür ama
tam da denetlenmesi gereken koşudur.

DEVAM halinde iki şey daha üretilir: `sozlesme_yollari` (kök `CLAUDE.md` +
koşan motorların beceri dizinleri — **yalnız yol, içerik okunmaz**, `:24`) ve
`ozet` (koşunun ne dediği, `:28`).

Çıkış kodu: **0 = DEVAM**, 1 = DUR, 2 = okuma hatası.

## Motor 2 — `scripts/bulgu_dogrula.py` (bulgu başına doğrulama)

```bash
python3 .claude/skills/dogrulama-zinciri/scripts/bulgu_dogrula.py \
    --rapor .../son_rapor.json --onceki .../onceki_rapor.json \
    --oy 3 --ozet --ayrinti
python3 .claude/skills/dogrulama-zinciri/scripts/bulgu_dogrula.py --self-test
```

**Dört inceleyici** (kaynak adım 4'ün dört ajanı, `:30-39`):

- `sozlesme_1` (orta, `:32`) — EMİR kapsamı: `EMIR_YOK_GEREKCESIZ`, `R_DENETIMSIZ`
- `sozlesme_2` (orta, `:32`) — çıktı sözleşmesi: `IKI_SATIR_EKSIK`,
  `ESIK_ETIKETSIZ`, `KIYAS_ATLANDI`, `CANLI_EMIR_UYARISI_YOK`
- `hata_1` (pahalı, `:35` — "without reading extra context") — **yalnız `ZIRVE`**:
  `EMIR_METNI_UYUSMAZ`, `EMIR_YON_CELISKISI`, `R_ARITMETIK_TUTARSIZ`,
  `GEOMETRI_BOZUK`, `MUHURLU_EMIR`, `R_KAPISI_IHLALI`
- `hata_2` (pahalı, `:38` — "within the changed code") — koşunun ÜRETTİĞİ mantık:
  `RR_DENETIMSIZ_ADAY`, `KAPI_KARAR_CELISKISI`, `GUVEN_TAVANI_IHLALI`,
  `YON_SKOR_UYUSMAZ`, `KAYNAKSIZ_DANISMAN`

Kapsam kuralı (`:33`): bir sözleşme kuralı yalnız KENDİ kapsamındaki artefakta
uygulanır (`kapsam` alanı).

**HIGH SIGNAL kapısı** (`:41-51`) — bulgu şu üçten birine bağlanamıyorsa düşer:
`:42` ayrıştırılamaz/çözümsüz atıf · `:43` girdiden bağımsız kesin yanlış ·
`:44` **birebir alıntılanabilen** sözleşme ihlali (alıntı yoksa bulgu düşer).
Bayraklanmayan sınıflar: `bicim` (`:47`), `kosullu` (`:48`), `oneri` (`:49`);
kesin olmayan bulgu `:51` ile düşer.

**Yanlış-pozitif listesi** (`:79-86`): `:81` önceden var olan · `:82` hata gibi
görünüp doğru olan (yuvarlanmış seviyelerle R tutmaz, motor kaydıyla tutar) ·
`:83` kılı kırk yaran (önem eşiği altı) · `:84` zaten gözlemcinin yakaladığı
(**gözlemci YENİDEN KOŞTURULMAZ**, raporun `DENETIM` alanı okunur) · `:85` genel
kalite endişesi · `:86` gerekçeyle susturulmuş (`emir_red_nedenleri`,
`varsayimlar`).

**Çoklu-oy** (kaynak 2, `verify/SKILL.md`): her bulgu, raporun **birden çok
bağımsız alanından** ayrı ayrı okunur; çoğunluk kuralı (`evet > n/2`).
Korkuluklar:

- Kanıtı açılamayan oy `KANIT_YOK`'tur ve **aleyhe** sayılır (fail-closed).
- Aynı yol iki kez oy kullanamaz (`gozlemci.py` ÇARPIŞMA ilkesi).
- İstenen oy sayısı mevcut bağımsız kanalı **aşamaz** — eksik oy UYDURULMAZ.
- Tek kanallı bulgu doğrulanmış SAYILMAZ (dairesel doğrulama korkuluğu).

Çıkış kodu: **0 = doğrulanmış bulgu yok**, 1 = bulgu var, 2 = okuma hatası.

## Adım 3 — `.claude/agents/degerlendirici.md` (şüpheci ikinci göz)

Sözleşmesi kaynaktan birebir korunur: cevabın **ilk satırı çıplak `PASS` ya da
`NEEDS_WORK`**; `Write`/`Edit` aracı YOK; "Plausibility is not correctness" /
"Akla yatkınlık doğruluk değildir"; kanıt eksikse `NEEDS_WORK`. Bu depoya özel
atlanamaz kural: **rapor dosyasını AÇMADAN `PASS` veremez** — aynı ilke
`.claude/hooks/kanit_kapisi.sh` kancasında da kodludur.

## Sınırlar (uydurma yok)

- **Bu motorlar gerçek alt-ajan BAŞLATMAZ.** Kaynağın haiku/sonnet/opus
  kademelemesi burada **maliyet sınıfına** ve deterministik Python
  kontrollerine çevrilmiştir; "paralel" adımlar ardışık koşar (kontroller
  birbirinden bağımsız olduğu için sonuç aynıdır). Ayrıntı: `KANIT.md` → SAPMALAR.
- Doğrulama **biçim ve aritmetik** düzeyindedir: bir sayının rapordaki başka
  alanlarla tutarlı olduğunu gösterir, piyasa hakkında DOĞRU olduğunu göstermez.
  Anlam denetimi elle ikinci-göz işidir (CLAUDE.md).
- Karar/yön ÜRETMEZ, mevcut kararı değiştirmez, motor koşturmaz, ağa çıkmaz.
- ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.
