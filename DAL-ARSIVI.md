# Dal arşivi — ne nerede duruyor

> Üretim: 2026-08-08, bağımsız envanter ajanı + elle doğrulama.
> Yöntem: `git merge-base --is-ancestor` (ATA) ve
> `git diff --name-status origin/main <dal>` (main'de OLMAYAN dosya var mı).

## Neden bu dosya var

Depoda main dışında 24 dal birikmişti. Hepsi silinip tek yere toplanacaktı;
silmeden önce arşiv **etiketi** basılacaktı ama bu oturumun git kimliği
`refs/tags/*` yazamıyor ve dal silemiyor (GitHub 403 — yalnız kendi çalışma
dalına push edebiliyor). Bu yüzden arşiv REF olarak değil bu KAYIT olarak
tutuluyor: aşağıdaki SHA'lar dallar silinmeden ÖNCE ölçüldü.

⚠️ **BENZERSİZ** işaretli dallar silinirse içerikleri KAYBOLUR (main'de yok).
Silmeden önce içeriği main'e alın ya da yerel klonda saklayın.

## Özet — 25 dal

| sınıf | adet | silinebilir mi |
|---|---|---|
| BENZERSİZ | 12 | **HAYIR** — main'de olmayan içerik taşıyor |
| İÇERİK MAIN'DE | 6 | evet — dosya farkı sıfır |
| ATA | 6 | evet — main geçmişinin parçası |
| AKTİF | 1 | hayır — çalışma dalı |

## Tam liste

| dal (`claude/…`) | SHA | son commit | sınıf | main'de OLMAYAN içerik |
|---|---|---|---|---|
| `ai-behavior-review-rules-ay0mo5` | `1f7f74fa15df` | 2026-08-03 | BENZERSİZ | .claude/skills/bag-kurma/ + .claude/agents/denetci.md (150 satır) |
| `crypto-market-data-3zm3cp` | `a275f816ccdc` | 2026-07-21 | BENZERSİZ | sistem/kaos-uyumlu-v3/ karar motoru + defter/ koşu arşivleri (SHA256'lı) |
| `crypto-market-data-jeufi9` | `52d5d9a78e67` | 2026-07-20 | BENZERSİZ | C0VETO v2.7 prompt sürümü + c0veto_runs/ arşivi |
| `depo-incelemesi-k165uz` | `0d5a285e63ae` | 2026-07-29 | BENZERSİZ | 9 beceri (butunluk-denetimi, dogrulama-zinciri, dokuman-uretimi, eleme-motoru, guven-katmanlama, izleme-telemetri, rubrik-kapisi, sema-dogrulama, sorusturma) + 5 kanca — 91 dosya ~23.2k satır |
| `doctor-command-y15960` | `ea1333d9c9b8` | 2026-07-28 | BENZERSİZ | ilk_gecis.py (ALINDI → main), sozlesme.json, DENETIM_ACIK_BULGULAR.md |
| `fvg-mitigation-calibration-52jxv4` | `30024bae2796` | 2026-07-31 | BENZERSİZ | grafik-calisma/scripts/fvg_kalibre.py (433 satır) — bekleyen iş FVG_MITIGASYON_KALIBRASYONU'nun motoru |
| `github-repo-comments-circulans-ste5ji` | `64ab6b42f97b` | 2026-07-23 | BENZERSİZ | tools/ takımı (7 dosya), degerleme.py, kurul_kosu.py, BENCHMARK.md |
| `karar-motoru-run-jde0pt` | `be7e9a79cbc6` | 2026-07-23 | BENZERSİZ | uzman-modu/scripts/iddia_denetim.py — blob bcf40b7, ste5ji ile BİREBİR AYNI |
| `kontrol-ajanlari-mimarisi-mrvhkl` | `82f78f9a3662` | 2026-07-26 | BENZERSİZ | kontrol_ajanlari.py (658 satır) + .claude/kontrol/kontrol_mimari.xml + zincir_sablon.json |
| `match-level-usage-explanation-44zi08` | `4a1ca2a9bb1a` | 2026-07-22 | BENZERSİZ | aynı blob bcf40b7 — ste5ji/jde0pt ile birebir aynı |
| `new-session-wtmu3n` | `a86659a459e3` | 2026-07-26 | BENZERSİZ | Wilder ATR düzeltmesi (ALINDI → main); Kimi yerel konsolu: llm_kurul.py, kimi_konsol.py, kimi_web.html, kimi-kur.sh, KURULUM.md. DİKKAT: bu daldaki emir_plani.py main'den ESKİ — bütün dosya alınırsa STOP-AV bayrağı / _nd() / rr_denetim hata yüzeyi KAYBOLUR |
| `new-session-x68zlz` | `d06aac57ea34` | 2026-07-26 | BENZERSİZ | piramit-sistem/tests/sabit/{eth_h4,eth_m15}.json — main'de tests/ dizini YOK |
| `analiz2-line-by-line-0nigal` | `8422630ccc0f` | 2026-08-07 | İÇERİK MAIN'DE | commit'leri farklı ama main'de olmayan dosya YOK (git diff origin/main <dal> → boş) |
| `code-security-review-agents-mozek1` | `710153de66d9` | 2026-07-28 | İÇERİK MAIN'DE | commit'leri farklı ama main'de olmayan dosya YOK (git diff origin/main <dal> → boş) |
| `new-session-shm7ng` | `057316698806` | 2026-07-25 | İÇERİK MAIN'DE | commit'leri farklı ama main'de olmayan dosya YOK (git diff origin/main <dal> → boş) |
| `repo-audit-critical-findings-3zdrm5` | `bd8c53e84cfe` | 2026-07-24 | İÇERİK MAIN'DE | commit'leri farklı ama main'de olmayan dosya YOK (git diff origin/main <dal> → boş) |
| `stress-stomach-pain-relief-of8j0g` | `3a2d17806e91` | 2026-08-02 | İÇERİK MAIN'DE | commit'leri farklı ama main'de olmayan dosya YOK (git diff origin/main <dal> → boş) |
| `trading-engine-spec-k8q8u8` | `8b38ebdce1b3` | 2026-07-21 | İÇERİK MAIN'DE | commit'leri farklı ama main'de olmayan dosya YOK (git diff origin/main <dal> → boş) |
| `code-review-documentation-5bdifi` | `362422770ec9` | 2026-07-30 | ATA | main geçmişinde zaten var — silmek hiçbir şey kaybettirmez |
| `kontrol-mimarisi-dogrulama-1qjpej` | `d5297e98f89e` | 2026-07-25 | ATA | main geçmişinde zaten var — silmek hiçbir şey kaybettirmez |
| `new-session-08gk0x` | `ae3ee15e3b53` | 2026-07-30 | ATA | main geçmişinde zaten var — silmek hiçbir şey kaybettirmez |
| `opus5-framework-setup-5ph8gv` | `d5297e98f89e` | 2026-07-25 | ATA | main geçmişinde zaten var — silmek hiçbir şey kaybettirmez |
| `task-goal-analysis-4sahc3` | `f59ad6426b76` | 2026-07-28 | ATA | main geçmişinde zaten var — silmek hiçbir şey kaybettirmez |
| `tradingview-chart-drawing-skills-haszvx` | `34cafe4ecb20` | 2026-07-27 | ATA | main geçmişinde zaten var — silmek hiçbir şey kaybettirmez |
| `yeni-verileri-analiz-b4zf7f` | `d582664fc4c6` | 2026-08-08 | AKTİF | bu oturumun çalışma dalı — dokunulmadı |

## Silme (yalnız yetkili kimlikle — bu oturum yapamaz)

```bash
# BENZERSİZ olanlar için ÖNCE arşiv etiketi ŞART:
git tag arsiv/<dal> origin/claude/<dal> && git push origin --tags
# sonra:
git push origin --delete claude/<dal>
```

GitHub arayüzünden: **Branches → sağdaki çöp kutusu**. Silinen dal ~90 gün
içinde aynı sayfadan **Restore** ile geri alınabilir; sonrası garantisizdir.

## Bu koşuda main'e ALINAN iki şey

| ne | nereden | neden |
|---|---|---|
| `piramit-sistem/scripts/ilk_gecis.py` | `doctor-command-y15960` | STRATEJI.md §2 ilk-geçiş ölçümünü şart koşuyor, motoru main'de yoktu → kapı ölçümsüzdü |
| `emir_plani.py` `_atr()` → Wilder | `new-session-wtmu3n` (YALNIZ bu fonksiyon) | `smc_tespit` Wilder, `emir_plani` basit ortalama kullanıyordu; ETH 4H'de 20.8914 vs 22.1913 (%6 sapma). Kapı eşikleri [0.8, 2.0] ve 3.0 Wilder ölçeğine kalibre. Sonrası: 22.191252 vs 22.191247 |
