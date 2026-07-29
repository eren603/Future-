# KANIT — rubrik-kapisi

Bu dosya, `rubrik-kapisi` becerisinin **kaynaktan** üretildiğini (hafızadan
değil) satır satır kanıtlar. Doğrulama **kaynağa karşıdır**; kendi çıktımızla
kendimizi doğrulamak dairesel olurdu.

**Okunan kaynak (TAM okundu, Read ile):**

| Dosya | Satır | SHA-256 (ilk 12) |
|---|---|---|
| `evals/README.md` | 112 | `e0d927fa1e7c` |
| `evals/k12-lesson-planning/rubrics/shared.csv` | 34 | `af246166bd2f` |
| `evals/k12-lesson-differentiation/rubrics/clarifying_question.csv` | 2 | `6c8d45d92936` |
| `evals/k12-lesson-differentiation/rubrics/differentiation.csv` | 28 | `d1dc5884dd2d` |

**Üretilen dosyalar:**

| Dosya | Satır |
|---|---|
| `.claude/skills/rubrik-kapisi/SKILL.md` | — |
| `.claude/skills/rubrik-kapisi/rubrikler/kosu_ortak.csv` | 31 (başlık + 30 kriter) |
| `.claude/skills/rubrik-kapisi/rubrikler/emir.csv` | 10 (başlık + 9 kriter) |
| `.claude/skills/rubrik-kapisi/scripts/rubrik.py` | 1262 |
| `.claude/skills/rubrik-kapisi/ornek/` | 14 çıktı dosyası (öz-test) |
| `.claude/skills/rubrik-kapisi/KANIT.md` | bu dosya |

---

## 1. SATIR SATIR KANIT TABLOSU

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|---|---|---|---|
| 1 | `README.md:20` | `Each rubric is a CSV with the following fields:` | `rubrik.py:45` | `SUTUNLAR = ("ID", "Bucket", "Criterion", "What pass requires", "Notes", "Conditional")` — 6 sütun, kaynak sırasıyla |
| 2 | `README.md:24` | `| `ID` | Unique criterion identifier (e.g., `P1`, `R3`) |` | `kosu_ortak.csv:2-31` | `G1…G6, KP1…KP6, D1…D9, Ç1…Ç9` — kova harfi + numara kalıbı korundu |
| 3 | `README.md:25` | `| `Bucket` | Top-level category: `P` (Pedagogy), `R` (Rigor), `O` (Output/Formatting), or `M` (Model Scaffolding) |` | `kosu_ortak.csv:2-31` | Bu alana uyarlanan 4 kova: `G — Girdi`, `KP — Kapı`, `D — Doğrulama`, `Ç — Çıktı` (eşleme aşağıda "SÜTUN EŞLEME") |
| 4 | `README.md:26` | `| `Criterion` | Short name for the criterion |` | `kosu_ortak.csv` 3. sütun | Kısa ad, ör. `Şişirilmiş-R denetimi her seviyeye uygulandı` |
| 5 | `README.md:27` | `| `What pass requires` | The specific, scoreable condition that constitutes a pass |` | `kosu_ortak.csv` 4. sütun | Her satır **ölçülebilir** koşul (alan adı + eşik) yazar; anlatı yazmaz |
| 6 | `README.md:28` | `| `Notes` | Rationale or design notes |` | `kosu_ortak.csv` 5. sütun | Gerekçe + **eşik kaynağı** (`piramit.py:98` gibi) burada durur |
| 7 | `README.md:29` | `| `Conditional` | If non-empty, the criterion applies only when this condition is met (e.g., `K-5`, `ELA-Gr8+`) |` | `kosu_ortak.csv` 6. sütun; `rubrik.py:198-206` | Koşul anahtarları: `onceki-kosu-kaydi-var`, `seviye-uretildi`, `gorsel-okuma-var`, `turev-motoru-kostu`, `korelasyon-beyan-edildi`, `emir-dogdu`, `emir-dogdu + usd-profil-beyan` |
| 8 | `README.md:33` | `If the condition isn't met, the criterion is skipped (not failed).` | `rubrik.py:712-727` | Koşul sağlanmazsa `durum = ATLANDI` + koşul kanıtı; **DÜŞTÜ sayılmaz** ve `gecme_orani` paydasına girmez (`rubrik.py:761-763`) |
| 9 | `README.md:33` | `Conditional criteria (marked in the `Conditional` column) apply only when the specified condition is met.` | `rubrik.py:708, 713-722` | Koşul, raporun kendi alanından mekanik okunur (ör. `k1.onceki_kayit_var`), elle takdirle değil |
| 10 | `README.md:35` | `Criteria score independently — a failing `R2` tells you something specific about cognitive demand, not just that the output is "bad."` | `rubrik.py:702-744` | Her kriter bağımsız fonksiyonla puanlanır; hiçbir kriter başkasının sonucunu görmez. Ör. `D4` düşünce yalnız "tünel görüşü" bilgisi verir |
| 11 | `README.md:35` | `consider tracking per-criterion pass rates across a prompt suite rather than relying on aggregate scores, since aggregate pass rates can mask meaningful gaps.` | `rubrik.py:752-755`, `766-788`, `791-829` | Çıktı sırası: ① kriter-başına döküm (BİRİNCİL) → ② kova-başına geçme oranı (BİRİNCİL) → ③ toplam (İKİNCİL, "tek başına okunmaz" uyarısıyla). Alıntı `rubrik.py:753`'de birebir taşınır |
| 12 | `README.md:31` | `For lesson plan generation, apply `shared.csv` first, then layer in the relevant subject-specific file. Subject-specific criteria extend the shared set.` | `rubrik.py:1246-1249`; `SKILL.md` "Kullanım" | `--rubrik` birden çok kez verilir: `kosu_ortak.csv` + `emir.csv` katmanlanır |
| 13 | `README.md:42` | `to score the lesson materials as either `0` or `1` against each rubric criterion` | `rubrik.py:42` | İkili puan: `GECTI, DUSTU` (+ kaynağın kapsamadığı iki dürüst durum: `ATLANDI`, `PUANLANMADI`) |
| 14 | `README.md:60-61` | `Pass means the criterion is clearly and fully met. Fail means it is absent, incomplete, or only partially met.` | `rubrik.py:743` | Denetçi `True` dönmezse `DÜŞTÜ`; "kısmen" diye bir not yok |
| 15 | `README.md:6` | `they can also be applied by human evaluators or adapted for deterministic scoring` | `rubrik.py:14-17`, `212-664` | **Sapma değil, kaynağın öngördüğü yol**: LLM-hakem yerine 39 deterministik denetçi (bkz. "SAPMALAR") |
| 16 | `README.md:58-59` | `the content must actually be present in the documents, not merely claimed in the chat response` | `rubrik.py:212-664` | Her denetçi raporun ALANINI okur; "raporda öyle yazıyor" yetmez, sayı/alan bulunmalı (ör. `Ç8` zirvedeki sayıyı alt katmanda arar) |
| 17 | `README.md:90` | `R criteria are designed to catch any downward drift in the intellectual work students are asked to do.` | `kosu_ortak.csv:8-13` (`KP` kovası) | `KP` kovası kanıt talebinin düşmesini yakalar: kapılar, şema derinliği, eşik kayması, R kapısı |
| 18 | `README.md:106` | `Model Scaffolding criteria evaluate the model's conversational behavior, not the artifact content` | `kosu_ortak.csv:14-22` (`D` kovası) | `D` kovası boru hattının **kendi doğrulama davranışını** ölçer (verifier, çelişki turu, dairesellik), karar içeriğini değil |
| 19 | `README.md:100` | `Output criteria evaluate the artifact itself` | `kosu_ortak.csv:23-31` (`Ç` kovası) | `Ç` kovası kullanıcıya giden artefaktı ölçer: iki satır, EMİR, geçersizlik, mühür, kıyas |
| 20 | `shared.csv:5` | `At least 3 misconceptions or anticipated challenges are named. Pass = 3 or more entries. Fail = fewer than 3.` | `kosu_ortak.csv:8` (`KP1`) | Sayı-eşikli aynı kalıp: `Pass = k2.gecti true VE motor_sayisi >= 2 … Fail = tek motor` |
| 21 | `shared.csv:2` | `Pass = full text in header and consistent verbatim usage throughout. Fail = code-only citation, paraphrase, or wording that drifts between header and body.` | `kosu_ortak.csv:12` (`KP5`) | "İki yerde aynı olmalı" kalıbı: kalibre edilen eşik ile sentezin uyguladığı eşik ayrışırsa DÜŞTÜ |
| 22 | `shared.csv:3` | `Pass = a named standard code (e.g., '3.NF.1') or a specific skill description … Fail = vague reference (e.g., 'students should have some background in fractions').` | `kosu_ortak.csv:25` (`Ç3`) | Somutluk kalıbı: gerekçesiz "EMİR YOK" = çıplak red → DÜŞTÜ |
| 23 | `shared.csv:12` | `Count the tasks in each phase and estimate minutes per task. Pass = every phase's workload fits its time.` | `rubrik.py:598-607` (`E4`) | "Say ve karşılaştır" kalıbı: her adayın R'si okunur, `r_min` ile karşılaştırılır |
| 24 | `shared.csv:22` | `List every mismatch found; pass only if BOTH directions are clean.` | `rubrik.py:292-303` (`KP4`) | Çift yönlü çapraz okuma: (a) hata kaydı gerekçeli mi, (b) K2'de koşan yön motoru kurulda mı — **ikisi de** temiz olmalı |
| 25 | `shared.csv:6` | `Pass = all three components present in every entry. Fail = any entry is missing a component` | `rubrik.py:609-620` (`E5`) | Her adayda giriş/stop/hedef gerekçesinin ÜÇÜ birden aranır |
| 26 | `clarifying_question.csv:2` | `M-CLARIFY-STATE,M — Model Scaffolding,Asks for state when unknown (social studies),"…",,state-unknown` | `emir.csv:2-10` | Kaynağın "model davranışını koşullu puanlama" satırı; bizde `emir-dogdu` koşullu 9 kriter aynı kalıpta (Notes boş bırakılabilir, `Conditional` dolu) |
| 27 | `differentiation.csv:5` | `Catches the learning-styles failure mode.` (Notes sütunu) | `kosu_ortak.csv:15` (`D2` Notes) | Notes'un "hangi arıza modunu yakalıyor" kullanımı: `D2` fail-OPEN doğrulamayı yakalar |
| 28 | `differentiation.csv:10` | `Auto-pass if teacher confirmed curriculum use in the prompt.` | `rubrik.py:712-727` | Koşulun otomatik çözülmesi fikri; bizde "auto-pass" yerine **ATLANDI** (kaynak README:33 daha katıdır, onu izledik) |
| 29 | `README.md:70` | `calibrating the judging by modifying the `What pass requires`` | `rubrikler/*.csv` | Eşik değişimi CSV'nin 4. sütunundan yapılır; motor kodu değişmeden kriter sıkılaştırılabilir |
| 30 | `README.md:112` | `Rubric criteria that reference specific KG-sourced content … will require KG access to score accurately` | `rubrik.py:729-735` | Karşılığı: denetçisi olmayan kriter `PUANLANMADI` (fail-closed) — erişilemeyen kanıt "geçti" sayılmaz |

---

## 2. SÜTUN EŞLEME

Kaynağın 6 CSV sütunu → bizdeki kullanımı (sütun **adları İngilizce kalır** ki
kaynakla birebir eşleşsin; içerik Türkçedir):

| Kaynak sütunu | Kaynaktaki tanım (README:24-29) | Bizdeki kullanım |
|---|---|---|
| `ID` | `Unique criterion identifier (e.g., P1, R3)` | `G1…G6`, `KP1…KP6`, `D1…D9`, `Ç1…Ç9`, `E1…E9`. Puanlayıcıdaki denetçi kaydı bu ID ile eşleşir (`rubrik.py:667-676`) |
| `Bucket` | `Top-level category: P / R / O / M` | `G — Girdi`, `KP — Kapı`, `D — Doğrulama`, `Ç — Çıktı`. Kova-başına geçme oranı buradan hesaplanır (`rubrik.py:766-776`) |
| `Criterion` | `Short name for the criterion` | Kriterin kısa Türkçe adı; çıktı tablosunda başlık olarak basılır |
| `What pass requires` | `The specific, scoreable condition that constitutes a pass` | **Pass = … Fail = …** biçimi (kaynak `shared.csv` üslubu). Alan adı + eşik yazılır, anlatı yazılmaz |
| `Notes` | `Rationale or design notes` | Gerekçe **+ eşiğin depo kaynağı** (`dosya:satır`). Bu sütun uydurma eşik korkuluğudur |
| `Conditional` | `If non-empty, the criterion applies only when this condition is met` | Koşul anahtarı. `rubrik.py:198-206`'daki `KOSUL` sözlüğünde karşılığı olmayan anahtar → `PUANLANMADI` (fail-closed, sessizce geçmez) |

### Kova eşlemesi (P/R/O/M → G/KP/D/Ç)

| Kaynak kovası | Kaynağın tanımı | Bizim kova | Neden aynı iş |
|---|---|---|---|
| `P — Pedagogy` | "whether the output reflects sound instructional design" (README:80) | `G — Girdi` | İkisi de **temelin sağlamlığını** ölçer: orada standarda/araştırmaya bağlanma, burada ölçüme/dosyaya bağlanma (bar sayısı, zorunlu girdi, tazelik) |
| `R — Rigor` | "designed to catch any downward drift in the intellectual work" (README:90) | `KP — Kapı` | İkisi de **talebin düşmesini** yakalar: orada bilişsel talep, burada kanıt talebi (kapı sayıları, şema derinliği, eşik kayması, R ≥ 1.35) |
| `M — Model Scaffolding` | "evaluate the model's conversational behavior, not the artifact content" (README:106) | `D — Doğrulama` | İkisi de **üreticinin davranışını** ölçer, ürünü değil: orada modelin soru sorma/teslim davranışı, burada boru hattının kendi kendini çürütme davranışı (fail-closed verifier, çelişki turu, dairesellik, tünel) |
| `O — Output/Formatting` | "evaluate the artifact itself: correct file structure … teacher rationale notes" (README:100) | `Ç — Çıktı` | İkisi de **kullanıcıya gidenin kullanılabilirliğini** ölçer: orada dosya yapısı/uzunluk/öğretmen notu, burada iki satır sözleşmesi, EMİR biçimi, geçersizlik, mühür, kaynaksız sayı |

---

## 3. KRİTER TÜRETME KANITI

Her kriterin dayandığı depo satırı. **Uydurma eşik yok**: aşağıdaki her sayı bir
kod satırına iner. İnmeyen tek şey `D4`'ün "≥ 2 aile" sayısıdır ve `[VARSAYIM]`
etiketlidir.

| Kriter | Ölçtüğü davranış | Eşik / alan kaynağı (depo) |
|---|---|---|
| `G1` | K1 fiyat kanalı kapısı | `piramit.py:390-396` — `gecti = (m15_ok and h4_ok) or bool(p_csv)` |
| `G2` | K1 çıkarım yapmamalı | `gozlemci.py:105` — `yasak = [a for a in ("karar", "yon", "stance", "sinyal") if a in k1]` (liste birebir kopyalandı: `rubrik.py:223`) |
| `G3` | Zorunlu girdi (likidasyon + görsel) | `piramit.py:333` (likidasyon yolu), `:353` (görsel yolu), `:309` (`zorunlu_eksik`) |
| `G4` | Tazelik damgası, **240 dk** | `piramit.py:114` — `"zorunlu_damga_tolerans_dk": 240`; ölçüm `piramit.py:313-330` |
| `G5` | Eksik kanal gerekçeli | `gozlemci.py:113-121` |
| `G6` | Hesap verme (akıbet ölçümü) | `gozlemci.py:126-136` (HATA=İHLAL / ölçülemedi=uyarı ayrımı), ölçüm `kiyas.py:88-99` |
| `KP1` | K2 kapısı, **≥ 2 motor** | `piramit.py:106` — `"min_motor_k2": 2`; kapı `piramit.py:576` |
| `KP2` | K3 kapısı, **≥ 2 danışman** | `piramit.py:107` — `"min_danisman_k3": 2`; kapı `piramit.py:743` |
| `KP3` | Motor şema derinliği | `gozlemci.py:57-65` — `SEMA_DERINLIK` sözlüğü birebir kopyalandı (`rubrik.py:59-67`) |
| `KP4` | Sessiz kayıp yok | `gozlemci.py:175-182` + `:255-268` (yön üretebilen motor kümesi `{karar-motoru, grafik-calisma, turev-akis}` oradan) |
| `KP5` | Eşik kalibrasyonu ↔ uygulama | `gozlemci.py:390-394` (1e-6 toleransı oradan), üretim `esik_kalibre.py`, uygulama `sentez.py:128-131` |
| `KP6` | İşlem kalitesi kapısı, **R ≥ 1.35** | `piramit.py:98` — `"r_min": 1.35`; kapı kuralı `piramit.py:1261-1272` |
| `D1` | Fail-closed ağırlık, **penaltı 0.25** | `sentez.py:130` — `refute_pen = float(th.get("refute_penalty", 0.25))`; uygulama `sentez.py:88` (`eff = conf * (1.0 if confirmed else refute_pen)`) |
| `D2` | Doğrulama seçici (fail-OPEN yok) | `gozlemci.py:301-308` |
| `D3` | Şişirilmiş-R denetimi | `piramit.py:811-832`; ATR eşikleri `rr_denetim.py:38` — `{"min_stop_atr": 0.8, "swing_stop_atr": 2.0, "far_target_atr": 3.0}` |
| `D4` | Tünel görüşü, **≥ 2 kanıt ailesi** | Aile eşlemesi `gozlemci.py:46-54` (birebir: `rubrik.py:48-56`). **`[VARSAYIM]`** — kaynak kod "≤ 1 aile" olduğunda UYARI basar (`gozlemci.py:316`), sayısal eşiği ayrı sabit olarak tutmaz; rubrik bunu `min_kanit_ailesi = 2` diye açık eşiğe çevirir (`rubrik.py:84`) ve UYARI'yı DÜŞTÜ sayar |
| `D5` | Dairesel doğrulama | `gozlemci.py:289-292` — kaynak listesi `("smc_tespit","setup_dogrulama","backtest","rr_denetim","R_MIN")` birebir |
| `D6` | Çelişki turu + fail-closed NÖTR | `piramit.py:1036-1055`, `:1104-1140`; denetim `gozlemci.py:437-440` |
| `D7` | Görsel tavan **0.50** + karşılıklı teyit | `piramit.py:105` — `"gorsel_tavan": 0.50`; uygulama `:724-725`; teyit `:840-854` |
| `D8` | Türev **kapsam eşiği 0.5** | `turev_akis.py:64` — `"kapsam_esigi": 0.5`; bağlama `turev_akis.py:302` |
| `D9` | Korelasyon **0.85 → risk ×2.0** | `korelasyon.py:32` — `"kopya_esigi": 0.85`; `korelasyon.py:99` — `hukum, risk_kat = "KOPYA POZİSYON", 2.0`; taşıma `piramit.py:860-864` |
| `Ç1` | İki satır sözleşmesi | `piramit.py:1617-1622`; `YON_BIAS` üretimi `sentez.py:177-185` |
| `Ç2` | Yön mekanik türedi | `gozlemci.py:467-469` (aynı işaret testi), skor `sentez.py:107` |
| `Ç3` | EMİR biçimi / gerekçeli red | `emir_plani.py:11-14` (çıktı sözleşmesi), `:341-343` (satır üretimi); gerekçe denetimi `gozlemci.py:413-419` |
| `Ç4` | Geçersizlik taşındı | `piramit.py:1360-1362`, `:1691-1694` |
| `Ç5` | Zorunlu eksik → çelişki + zirve | `piramit.py:869-870`, `:1610` |
| `Ç6` | Gözlemci mührü | Kritik kod kümesi `gozlemci.py:43` — `KRITIK = {"UYDURMA","DAIRESEL","EKSIK_AKTARIM","MEMNUN_ETME"}` (birebir: `rubrik.py:88`); mühür `piramit.py:1658-1667` |
| `Ç7` | KIYAS koştu | Etiketler `kiyas.py:105-115`; denetim `gozlemci.py:512-532` |
| `Ç8` | Kaynaksız sayı yok | `gozlemci.py:453-461`; sayı toplayıcı `gozlemci.py:72-83` (round 6) birebir kopyalandı (`rubrik.py:113-124`) |
| `Ç9` | Ağırlık **[0.40, 1.00]**, **n_taban 10** | `piramit.py:103` — `"agirlik_alt": 0.40, "agirlik_ust": 1.00`; `kalibrasyon.py:38` — `"n_taban": 10`; kural `piramit.py:1505-1516` |
| `E1` | Emir biçimi | `emir_plani.py:11-14`, `:341-343` |
| `E2` | Emir yönü = karar yönü | `gozlemci.py:423-429` |
| `E3` | Aday `rr_denetim` = TUTARLI | `emir_plani.py:269-274`; denetim `gozlemci.py:407-412` |
| `E4` | Aday **R ≥ 1.35** | `emir_plani.py:58` — `"r_min": 1.35`; uygulama `emir_plani.py:275-277` |
| `E5` | Seviyeler ölçülen yapıdan | `emir_plani.py:17-24` (kural), `:132-161` (aday üretimi) |
| `E6` | MARKET **0.1×ATR15** toleransı | `emir_plani.py:59` — `"market_tolerans_atr": 0.1`; uygulama `emir_plani.py:284-285` |
| `E7` | Aday geçersizlik cümlesi | `emir_plani.py:291-292` |
| `E8` | Mühürle çelişmeme | `piramit.py:1664-1667` |
| `E9` | Sabit-USDT 5 kapısı | `emir_plani.py:307-326` |

**Sayım:** 39 kriterin **38'inin** her sayısal eşiği bir kod satırına iner;
**1 tanesi** (`D4`) `[VARSAYIM]` etiketlidir — gerekçesi yukarıda açıktır.

---

## 4. SAPMALAR

1. **Eğitim → finans çevirisi.** Kaynak bir *ders planı artefaktını* puanlar;
   burada puanlanan bir *piramit koşusudur*. Kovalar buna göre yeniden
   adlandırıldı (eşleme tablosu §2). Kaynağın "standarda bağlanma" fikri burada
   "ölçüme/dosyaya bağlanma" olur; "bilişsel talebin düşmemesi" fikri "kanıt
   talebinin düşmemesi" (fail-closed kapılar) olur.

2. **LLM-hakem yerine deterministik puanlama.** Kaynak (README:37-66) bir
   LLM-as-judge sistem istemi verir. Burada puanlama **deterministiktir**: 39
   kriterin her biri raporun bir alanını okuyan bir Python fonksiyonudur
   (`rubrik.py:212-664`). Bu, kaynağın kendi cümlesiyle meşrudur — *"adapted for
   deterministic scoring"* (README:6). **Bedeli açıkça yazılır:** araç **anlam**
   denetlemez. Bir gerekçenin *doğru* olup olmadığı elle ikinci-göz işidir; bu
   araç yalnız **artefakt** denetler (alan var mı, sayı tutuyor mu, eşik
   uygulanmış mı).

3. **İki ek durum.** Kaynak ikili puanlar (`0`/`1`, README:42). Burada iki
   dürüst durum eklendi: `ATLANDI` (kaynağın "skipped (not failed)" kuralının
   görünür karşılığı) ve `PUANLANMADI` (denetçisi ya da tanınan koşulu olmayan
   kriter). `PUANLANMADI` **GEÇTİ sayılmaz** ve geçme oranı paydasına girmez;
   ayrıca CLI çıkış kodunu 2 yapar — sessiz "geçti" imkânsızdır.

4. **`D4` UYARI → DÜŞTÜ.** Boru hattının kendi gözlemcisi tünel görüşünü UYARI
   sayar (mühür düşürmez). Rubrik bunu DÜŞTÜ sayar: rubrik mühürden **daha sıkı**
   olabilir; amacı işlemi durdurmak değil, boşluğu görünür kılmaktır. Nitekim
   depodaki iki GERÇEK koşuda da düşen tek kriter budur (§5) ve boru hattının
   kendi uyarısıyla birebir örtüşür — bağımsız iki yol aynı boşluğu buldu.

5. **Koşul anahtarı biçimi.** Kaynağın `Conditional` değerleri serbest metindir
   (`K-5`, `state-unknown`). Burada makine-okunur kısa anahtarlar kullanıldı;
   tanınmayan anahtar sessizce geçmek yerine `PUANLANMADI` üretir
   (`rubrik.py:714-720`).

---

## 5. DOĞRULAMA

Komut:

```
$ python3 .claude/skills/rubrik-kapisi/scripts/rubrik.py --self-test
```

Çıkış kodu `0`. Tam çıktı: `ornek/self_test_cikti.txt`. Senaryo sonuçları:

| Senaryo | GEÇTİ | DÜŞTÜ | ATLANDI | PUANLANMADI | Düşen kriterler |
|---|---|---|---|---|---|
| `tam_gecen` (sahte, sağlıklı koşu) | 38 | 0 | 1 | 0 | — (atlanan: `E9`, usd profili beyan edilmemiş) |
| `kismen_dusen` (sahte, bozulmuş koşu) | 27 | 11 | 1 | 0 | `G3, G4, KP5, KP6, D2, D3, D7, Ç2, Ç6, E2, E8` |
| `kosullu_atlanan` (sahte, ilk analiz) | 22 | 2 | 15 | 0 | `G3, D4` (atlanan: `G6, D3, D7, D8, D9, Ç7, E1…E9`) |
| **GERÇEK** `piramit-sistem/state/son_rapor.json` (BTC) | 36 | 1 | 2 | 0 | `D4` |
| **GERÇEK** `piramit-sistem/state/son_rapor_eth.json` (ETH) | 37 | 1 | 1 | 0 | `D4` |

`kismen_dusen` senaryosunda kasıtlı olarak bozulanlar ve rubriğin yakaladığı
karşılıkları: bayat likidasyon (`G3`,`G4`), tüm danışmanların onaylanması =
fail-OPEN (`D2`), şişirilmiş R'ye rağmen onaylı danışman (`D3`), kalibre eşikten
sapan sentez eşiği (`KP5`), R kapısının altında "temiz giriş var" (`KP6`),
görsel tavanın aşılması (`D7`), skorun işaretiyle çelişen yön (`Ç2`),
uygulanmamış gözlemci mührü (`Ç6`,`E8`), kararla çelişen emir yönü (`E2`).

### GERÇEK koşu çıktısı (BTC) — özet

```
② KOVA BAŞINA GEÇME ORANI (BİRİNCİL)
   G — Girdi        6/6 geçti (oran 1.0) | atlandı 0
   KP — Kapı        9/9 geçti (oran 1.0) | atlandı 1
   D — Doğrulama    8/9 geçti (oran 0.8889) | atlandı 1 | düşen: D4
   Ç — Çıktı        13/13 geçti (oran 1.0) | atlandı 0
③ TOPLAM (İKİNCİL — tek başına okunmaz)
   36 geçti / 1 düştü / 2 atlandı  → geçme oranı 0.973
```

(Atlananlar: `D3` — bu koşuda K3 seviye üretmedi; `E9` — sabit-USDT profili
beyan edilmemiş. İkisi de **düşmüş sayılmaz**.)

Düşen kriterin kanıt satırı (rapordan okunmuştur, uydurma değil) —
`ornek/gercek_son_rapor_puan.txt:50-51`:

```
   ✖ D4   DÜŞTÜ       Tünel görüşü yok — en az iki kanıt ailesi doğrulandı
        ↳ onaylı danışman=['gorsel-teyit'] → aile=['gorsel'] (gerek >= 2)
```

Bu bulgu, koşunun **kendi** gözlemci uyarısıyla bağımsız olarak örtüşür
(`son_rapor.json` → `DENETIM.uyari`): *"K4-AGI/TUNEL: doğrulanmış kanıt yalnız
{'gorsel'} ailesinden — tek pencereden bakılıyor"*. Rubrik bu boşluğu kendi
yolundan (verifier + AILE eşlemesi) bulmuştur; gözlemcinin metnini okumaz.

Tam çıktılar: `ornek/gercek_son_rapor_puan.txt`,
`ornek/gercek_son_rapor_eth_puan.txt`, `ornek/tam_gecen_puan.txt`,
`ornek/kismen_dusen_puan.txt`, `ornek/kosullu_atlanan_puan.txt` (+ `.json`
eşleri ve sahte koşu raporları `*_kosu.json`).

---

⚠️ Bu beceri bir **koşu kalitesi** notu üretir; piyasa yönü/kararı üretmez.
Canlı/otomatik emir DAHİL DEĞİLDİR.
