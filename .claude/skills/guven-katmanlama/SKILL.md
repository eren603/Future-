---
name: guven-katmanlama
description: >-
  Güven katmanlama / izolasyon becerisi. Bir koşuda GÜVENİLMEZ girdi
  (yapıştırılan CoinGlass-borsa paneli metni, grafik ekran görüntüsü veya video
  okuması, elle girilen likidasyon değerleri) işlenecekse OTOMATİK devreye
  girer — slash komutu gerekmez. Bu girdileri okuyan bileşenin bir kabuğa, bir
  yazma aracına ya da motor siciline ULAŞAMADIĞINI mekanik olarak doğrular:
  okuyucu (güvenilmez okur, yazamaz) / denetçi (yalnız güvenilir kaynak,
  yazamaz) / yazıcı (tek write sahibi, güvenilmez okumaz). Ayrıca boru hattı
  çıktısında yankılanan devir (handoff) taleplerini sabit allowlist + uzunluk ve
  regex sınırlı yük şemasından geçirir. Çalışan motorlar: scripts/katman_denetle.py
  (iş tanımı → TEMİZ/İHLAL), scripts/devir_allowlist.py (devir talebi → KABUL/RED).
  Sıfır bağımlılık (stdlib; jsonschema BU DEPODA KURULU DEĞİL). Tetikleyici
  kelimeler (TR/EN): güven katmanı, izolasyon, karantina, güvenilmez girdi,
  untrusted, prompt injection, enjeksiyon, yetki, yazma yetkisi, allowlist,
  devir, handoff, panel metni, görsel okuma, likidasyon dosyası, sandbox.
---

# Güven katmanlama — güvenilmez girdi ile yazma yetkisini AYIRMA

## Neden

Bu depo dışarıdan gelen metni motora sokar. `engine/girdi/gorsel_okuma.json`
serbest metin taşır (`gozlem[]`, `celiski_notu`), `engine/girdi/turev_ham/
likidasyon.json` elle CoinGlass panelinden doldurulur, panel metni doğrudan
yapıştırılır. Bunları YAZAN kişi kullanıcı değil; grafiği/paneli üreten taraftır.
Kaynak şablonun teşhisi birebir şu (gl-reconciler/README.md:24):

> "This agent reads counterparty/custodian statements — documents authored by
> outsiders that may carry adversarial instructions. The template is structured
> so a payload in one of those documents cannot reach a shell, a write tool, or
> a firm system"

Bu becerinin tek işi o cümleyi bu depoda **mekanik olarak** doğrulamaktır.
Karar/yön üretmez; `piramit-sistem` ve `karar-kurulu` sentezine karışmaz.

## Üç katman (kaynak tablosunun bu depoya çevrilmiş hâli)

| Katman | Güvenilmez okur? | Açık araçlar | Kaynaklar | Yazabilir |
|---|---|---|---|---|
| `okuyucu` (`katmanlar/okuyucu.yaml`) | **EVET** | `read`, `grep` | yok | **hiçbir yere** |
| `denetci` (`katmanlar/denetci.yaml`) | hayır | `read`, `grep`, `glob`, `agent` | salt-okunur kline + motor çıktıları | **hiçbir yere** |
| `yazici` (`katmanlar/yazici.yaml`) | hayır | `read`, `write`, `edit` | yok | `engine/state/`, `engine/cikti/` |

Kaynak satırları ve birebir alıntıları `KANIT.md`'dedir. Üç yaml'ın her aracı
için "neden açık / neden kapalı" yorumu kaynaktan alıntılıdır.

Ayrıştırıcı kural: **güvenilmez girdiyi okuyan bileşen hiçbir koşulda
`write`/`edit`/`bash` taşıyamaz ve hiçbir dosyaya yazamaz.** Okuyucunun tek
çıkış kanalı, uzunluk ve karakter-sınıfı sınırlı şemadan geçen JSON'dur — bu
sayede enjekte edilmiş talimat bütün hâlde hayatta kalamaz (reader.yaml:31-34).

## Motor 1 — `scripts/katman_denetle.py`

```bash
python3 .claude/skills/guven-katmanlama/scripts/katman_denetle.py --job is_tanimi.json
python3 .claude/skills/guven-katmanlama/scripts/katman_denetle.py --self-test
```

İş tanımı biçimi:

```json
{
  "sembol": "BTCUSDT",
  "bilesenler": [
    {"ad": "panel-okuyucu", "katman": "okuyucu", "araclar": ["read", "grep"],
     "okur": ["engine/girdi/gorsel_okuma.json",
              "engine/girdi/turev_ham/likidasyon.json"],
     "yazar": [],
     "cikti": {"sembol": "BTCUSDT", "durum": "veri_var",
               "olcumler": [{"kanal": "liq_long", "deger": 0.2299}]}},
    {"ad": "piramit", "katman": "denetci",
     "araclar": ["read", "grep", "glob", "agent"],
     "okur": ["engine/girdi/m15.json", "engine/girdi/h4.json"], "yazar": []},
    {"ad": "sicil-yazici", "katman": "yazici", "araclar": ["read", "write"],
     "okur": ["engine/state/durum.json"],
     "yazar": ["engine/state/defter.jsonl", "engine/cikti/btc_karar.svg"]}
  ]
}
```

Yakaladığı ihlaller: `YAZMA_YETKISI` (güvenilmez okuyan bileşende yazma/kabuk),
`SIZINTI` (güvenilmez dosyayı okuyucu olmayan katman açıyor), `ARAC_IHLALI`
(tabloda kapalı araç), `YAZMA_HEDEFI` (izinli önek dışına yazma),
`SINIFLANDIRILMAMIS` (girdi güvenilir mi bilinmiyor — fail-closed),
`KATMAN_ATLAMA` (güvenilmez girdi var, okuyucu yok), `BILINMEYEN_KATMAN`,
`BILINMEYEN_ARAC`, `SEMA` (okuyucu çıktısı şemayı geçmedi),
`BAGLAYICI_IHLALI`, `BOS_IS_TANIMI`.

Çıkış kodu 0 = TEMİZ, 1 = İHLAL. **Fail-closed:** sınıflandırılamayan girdi
"güvenilir" varsayılmaz, İHLAL sayılır.

## Motor 2 — `scripts/devir_allowlist.py`

```bash
python3 .claude/skills/guven-katmanlama/scripts/devir_allowlist.py --dosya rapor.txt
python3 .claude/skills/guven-katmanlama/scripts/devir_allowlist.py --self-test
```

Devir talebi bloğu boru hattı çıktısında yankılanabilir; çıktı güvenilmez panel
okumasının **aşağı akışındadır**. İki korkuluk (kaynak orchestrate.py:8-14):

- **(a)** `hedef_sembol` ∈ `{BTCUSDT, ETHUSDT}` ve `hedef_bilesen` ∈ 16 gerçek
  motor adı (`piramit.py` `MOTOR` sözlüğü) — sabit allowlist.
- **(b)** yük şeması: `olay` ≤ 2000 karakter, `baglam_ref` ≤ 256 karakter ve
  `^[A-Za-z0-9 ._/:#-]+$`, `additionalProperties: false`.

Çıkış kodu 0 = geçerli devir, 1 = devir yok/REDDEDİLDİ.

⚠ Kaynağın `HANDOFF_RE` deseni iç içe yükte kırpma yaptığı için orada iki
korkuluk hiç çalışmıyordu; bu port deseni çıpa olarak korur ama bloğu
parantez dengeleyerek kapatır. Ölçüm ve gerekçe `KANIT.md`/SAPMALAR'dadır.

## Sınırlar (uydurma yok)

- Bu beceri bir **iş tanımını** denetler; işletim sistemi düzeyinde yetki
  uygulamaz. Beyan edilmemiş bir okuma/yazma denetlenemez.
- `SEMA` denetimi yalnız **biçim** korkuluğudur; okunan sayının DOĞRU olduğunu
  söylemez (anlam denetimi elle ikinci-göz işidir — CLAUDE.md).
- Karar/yön üretmez. Canlı/otomatik emir DAHİL DEĞİL.
