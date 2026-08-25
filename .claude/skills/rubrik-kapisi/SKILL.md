---
name: rubrik-kapisi
description: >-
  Rubrik kapısı — "iş bitti mi / koşu kaliteli mi" sorusunun NOTLANABİLİR
  cevabı. Bir piramit koşusu (piramit.py raporu) üretildikten sonra ya da bir
  soru "bu koşu kaliteli mi", "iş bitti mi", "kaçıncı kriter düştü", "koşuyu
  puanla", "eksik ne kaldı" ile ilgili olduğunda OTOMATİK devreye girer — slash
  komutu gerekmez. Koşuyu 39 kriterle (30 çekirdek + 9 emir kriteri) tek tek
  notlar: GEÇTİ / DÜŞTÜ / ATLANDI. Koşulu sağlanmayan kriter ATLANIR — DÜŞMÜŞ
  SAYILMAZ. BİRİNCİL çıktı kriter-başına geçme oranıdır; toplam skor ikincildir
  ve maskeleme uyarısıyla verilir. Çalışan motor: scripts/rubrik.py (stdlib;
  öz-test: --self-test, 3 sahte senaryo + GERÇEK koşu raporları). Rubrikler:
  rubrikler/kosu_ortak.csv, rubrikler/emir.csv (kaynak şemasıyla birebir 6
  sütun). Tetikleyici kelimeler (TR/EN): rubrik, rubric, kriter, criterion,
  puanla, score, not ver, kalite, kabul kriteri, checklist, koşu kalitesi, iş
  bitti mi, definition of done, geçme oranı, pass rate. ⚠️ Bu bir KOŞU KALİTESİ
  notudur; piyasa kararı/canlı emir DEĞİLDİR.
---

# Rubrik Kapısı — koşu kalitesinin notlanabilir cevabı

`piramit.py` bir koşunun **ne yaptığını** anlatır. Bu beceri o koşunun
**kaliteli olup olmadığını** notlar: her kriter bağımsız puanlanır, kanıtı
raporun hangi alanından geldiğiyle birlikte basılır.

Kaynak: Learning Commons × Anthropic K-12 eval rubrikleri (`evals/README.md`,
`k12-lesson-planning/rubrics/shared.csv`). Oradaki **kullanım sözleşmesi**
birebir korunmuştur; puanlanan şey ders planı değil, **bir piramit koşusudur**.

## Neyi notluyoruz

| Kova | Ne ölçer | Kaynak kovası |
|---|---|---|
| `G — Girdi` | K1'in ölçüm sağlamlığı: kanal, bar, zorunlu girdi, tazelik, hesap verme | `P — Pedagogy` (temel tasarım sağlamlığı) |
| `KP — Kapı` | Fail-closed eşikler: K2/K3 kapıları, şema derinliği, eşik kalibrasyonu, R kapısı | `R — Rigor` (talebin düşmesini yakalar) |
| `D — Doğrulama` | Boru hattının kendi denetim davranışı: fail-closed verifier, tünel, dairesellik, çelişki turu | `M — Model Scaffolding` (üreticinin davranışı, artefakt değil) |
| `Ç — Çıktı` | Kullanıcı sözleşmesi: iki satır, EMİR, geçersizlik, mühür, kıyas, kaynaksız sayı | `O — Output/Formatting` (artefaktın kendisi) |

## Kullanım (motor koşar, elle not verilmez)

```bash
# Çekirdek rubrik
python3 .claude/skills/rubrik-kapisi/scripts/rubrik.py \
    --rapor .claude/skills/piramit-sistem/state/son_rapor.json \
    --rubrik .claude/skills/rubrik-kapisi/rubrikler/kosu_ortak.csv

# Emir doğduysa emir rubriği de katmanlanır (kaynak kuralı: shared + ek dosya)
python3 .claude/skills/rubrik-kapisi/scripts/rubrik.py \
    --rapor <rapor.json> \
    --rubrik <...>/kosu_ortak.csv --rubrik <...>/emir.csv --json --out puan.json

# Öz-test (3 sahte senaryo + depodaki gerçek koşu raporları)
python3 .claude/skills/rubrik-kapisi/scripts/rubrik.py --self-test
```

Çıkış kodu: `0` = düşen/puanlanamayan kriter yok, `2` = var (fail-closed).

## Sözleşme (kaynaktan, gevşetilmez)

1. **Koşullu kriter atlanır, düşmez.** `Conditional` sütunu doluysa kriter
   yalnız o koşulda uygulanır; koşul sağlanmazsa **ATLANDI** yazılır —
   *"If the condition isn't met, the criterion is skipped (not failed)."*
   Koşullar rapordan mekanik okunur: `onceki-kosu-kaydi-var`, `seviye-uretildi`,
   `gorsel-okuma-var`, `turev-motoru-kostu`, `korelasyon-beyan-edildi`,
   `emir-dogdu`, `emir-dogdu + usd-profil-beyan`.
2. **Kriterler bağımsız puanlanır; toplam skor tek başına sunulmaz.**
   *"aggregate pass rates can mask meaningful gaps"* — bu yüzden birincil çıktı
   kriter-başına ve kova-başına geçme oranıdır, toplam ikincil ve uyarı notludur.
3. **Rubrik katmanlanır.** Kaynakta `shared.csv` + konu dosyası; burada
   `kosu_ortak.csv` + `emir.csv`.
4. **Denetçisi olmayan kriter GEÇTİ sayılmaz** → `PUANLANMADI` (fail-closed).
   Uydurma not yok; tanınmayan koşul anahtarı da `PUANLANMADI`'dır.
5. **Eşikler uydurulmaz.** Her sayısal eşik depodaki bir kod satırından okunur
   (`r_min 1.35`, `min_motor_k2 2`, `min_danisman_k3 2`, `gorsel_tavan 0.50`,
   tazelik `240 dk`, `refute_penalty 0.25`, türev `kapsam_esigi 0.5`, korelasyon
   `0.85 → ×2.0`, `n_taban 10`, ağırlık `[0.40, 1.00]`, MARKET toleransı
   `0.1×ATR15`). Kaynakları `KANIT.md` → "KRİTER TÜRETME KANITI".

## Sapma (açıkça)

Kaynak rubrikler **LLM-as-judge** için yazılmıştır. Burada puanlama
**deterministiktir**: her kriter raporun bir alanına inen bir Python denetçisiyle
ölçülür (ağ yok, model yok, rastgelelik yok). Kaynak bunu zaten öngörür:
*"they can also be applied by human evaluators or adapted for deterministic
scoring."* Bunun bedeli: **anlam** denetlenmez (bir gerekçenin doğru olup
olmadığı elle ikinci-göz işidir); bu araç yalnız **artefakt** denetler.

⚠️ Bu bir koşu kalitesi notudur; piyasa yönü/kararı üretmez, canlı/otomatik emir
DAHİL DEĞİLDİR.
