# KANIT — `dogrulama-zinciri` becerisinin kaynak izlenebilirliği

Bu belge, becerinin **hangi satırının hangi kaynak satırından** geldiğini
gösterir. Kaynak dosyalar:

- **A** = `cc/plugins/code-review/commands/code-review.md`
  (109 satır, sha256 başı `2b0837c5ec0b`)
- **B** = `a-cwc-long-running-agents/claude-code-config/.claude/agents/evaluator.md`
  (25 satır, sha256 başı `0ce0481cdf64`)
- **C** = `a-defending-code-reference-harness/.claude/skills/verify/SKILL.md`
  (42 satır, sha256 başı `40bbbc9145b3`)
- **D** = bu deponun gerçek dosyaları (`piramit-sistem/scripts/piramit.py`,
  `karar-kurulu/scripts/sentez.py`, `rr_denetim.py`, `emir_plani.py`,
  `gozlemci.py`, `.claude/hooks/kanit_kapisi.sh`, `state/son_rapor.json`)

Alıntılar **kopyala-yapıştır**tır, parafraz değildir. Çok satırlı alıntılar
tabloda `/` ile birleştirilmiştir; bu birleştirme dışında metne dokunulmamıştır.

Üretilen dosyalar:

| Dosya | Satır | Rol |
|---|---|---|
| `.claude/skills/dogrulama-zinciri/SKILL.md` | 160 | kademeli akış |
| `.claude/skills/dogrulama-zinciri/scripts/kademe.py` | 580 | maliyet kademesi (madde 8) |
| `.claude/skills/dogrulama-zinciri/scripts/bulgu_dogrula.py` | 1136 | bulgu doğrulayıcı (madde 9) |
| `.claude/agents/degerlendirici.md` | 66 | şüpheci değerlendirici (madde B5) |
| `.claude/skills/dogrulama-zinciri/ornek/*` | — | öz-test ve gerçek koşu çıktıları |

## Kanıt tablosu

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|---|---|---|---|
| 1 | A:14 | `1. Launch a haiku agent to check if any of the following are true:` | `kademe.py:42-47`, `kademe.py:236-243` | Adım 1 tamamı **ucuz** maliyet sınıfına konuldu; haiku → `ucuz`. |
| 2 | A:15 | `- The pull request is closed` | `kademe.py:244-255` | `kapali` kapısı: `rapor["durum"]` "DURDU —" ile başlıyorsa ya da `ZIRVE.iki_satir` yoksa değerlendirilecek karar yoktur. (`durum` biçimi D: `piramit.py:1698`.) |
| 3 | A:16 | `- The pull request is a draft` | `kademe.py:256-265` | `taslak` kapısı: `ZIRVE.ZORUNLU_EKSIK` dolu → karar zorunlu girdi olmadan üretilmiş. (Alan D: `piramit.py:1610`.) |
| 4 | A:17 | `- The pull request does not need code review (e.g. automated PR, trivial change that is obviously correct)` | `kademe.py:266-283` | `onemsiz` kapısı: `YON_BIAS` nötr **ve** emir yok → doğrulanacak sayısal iddia yok. |
| 5 | A:18 | `- Claude has already commented on this PR (check `gh pr view <PR> --comments` for comments left by claude)` | `kademe.py:284-291`, `kademe.py:130-144` (`parmak_izi`) | `zaten_yapildi` kapısı: koşunun parmak izi (sembol + son bar + YON_BIAS + EMIR + karar) değerlendirme defterinde varsa DUR. |
| 6 | A:20 | `If any condition is true, stop and do not proceed.` | `kademe.py:319`, `kademe.py:330-336` | Herhangi bir kapı DURDUR derse `KARAR="DUR"` ve **pahalı kademe hiç koşmaz** (`ozet`/`sozlesme_yollari` üretilmez). |
| 7 | A:22 | `Note: Still review Claude generated PR's.` | `kademe.py:31-38`, `kademe.py:270-276` | Tek istisna korundu: `DENETIM.muhurlendi` ise `onemsiz` kapısı UYGULANMAZ. Gerekçe D: `piramit.py:1664` mühürde EMİR'i kapatır — mühürlü koşu "önemsiz" görünür ama denetlenmesi gerekendir. |
| 8 | A:24 | `2. Launch a haiku agent to return a list of file paths (not their contents) for all relevant CLAUDE.md files including:` | `kademe.py:172-202` | `sozlesme_yollari()`: **yalnız yol** döner; `_not` alanı "içerik OKUNMADI" der. Öz-test vaka 9 içerik alanı olmadığını sınar. |
| 9 | A:25 | `- The root CLAUDE.md file, if it exists` | `kademe.py:193-194` | Kök `CLAUDE.md` listeye girer; yoksa `bulunamayan`a yazılır (ihlal değil — "if it exists"). |
| 10 | A:26 | `- Any CLAUDE.md files in directories containing files modified by the pull request` | `kademe.py:180-192` (`MOTOR_DIZIN`, `SABIT_DIZIN`) | "Değişen dosyaların dizinleri" → **o koşuda çalışan motorların beceri dizinleri** (`K2.motor_sonuclari` anahtarlarından) + boru hattının kendisi. |
| 11 | A:28 | `3. Launch a sonnet agent to view the pull request and return a summary of the changes` | `kademe.py:205-231` | `kosu_ozeti()`, **orta** maliyet sınıfı; her alan rapordan okunur, hiçbiri türetilmez. |
| 12 | A:30 | `4. Launch 4 agents in parallel to independently review the changes. Each agent should return the list of issues, where each issue includes a description and the reason it was flagged (e.g. "CLAUDE.md adherence", "bug").` | `bulgu_dogrula.py:696-711`, `:168-193` | Dört inceleyici; her bulgu `aciklama` + `neden_bayraklandi` taşır (etiketler "CLAUDE.md adherence" / "bug" olarak kullanıldı). |
| 13 | A:32-33 | `Agents 1 + 2: CLAUDE.md compliance sonnet agents` / `Audit changes for CLAUDE.md compliance in parallel. Note: When evaluating CLAUDE.md compliance for a file, you should only consider CLAUDE.md files that share a file path with the file or parents.` | `bulgu_dogrula.py:495-499`, `:575-579`, `kapsam` alanı `:181` | İki sözleşme inceleyicisi (`sozlesme_1` = EMİR kapsamı, `sozlesme_2` = çıktı sözleşmesi); her kural yalnız kendi `kapsam`ındaki artefakta uygulanır. |
| 14 | A:35-36 | `Agent 3: Opus bug agent (parallel subagent with agent 4)` / `Scan for obvious bugs. Focus only on the diff itself without reading extra context.` | `bulgu_dogrula.py:195-198`, `:199-373` | `hata_1` YALNIZ `ZIRVE` bloğunu okur (katman içi üretim yoluna bakmaz) — "without reading extra context"in bu depodaki karşılığı. |
| 15 | A:38-39 | `Agent 4: Opus bug agent (parallel subagent with agent 3)` / `Look for problems that exist in the introduced code. This could be security issues, incorrect logic, etc. Only look for issues that fall within the changed code.` | `bulgu_dogrula.py:370-374`, `:375-493` | `hata_2` koşunun ÜRETTİĞİ mantığı denetler (K3/K4/K5): sentez kapıları, güven tavanı, işaret kuralı, çözümsüz danışman atfı. |
| 16 | A:41 | `**CRITICAL: We only want HIGH SIGNAL issues.** Flag issues where:` | `bulgu_dogrula.py:88-95`, `:717-731` | `yuksek_sinyal()` kapısı; ölçüte bağlanamayan bulgu bayraklanmaz (`:41` gerekçesiyle elenir). |
| 17 | A:42 | `- The code will fail to compile or parse (syntax errors, type errors, missing imports, unresolved references)` | `bulgu_dogrula.py:90-91`; bulgular `:220 EMIR_METNI_UYUSMAZ`, `:474 KAYNAKSIZ_DANISMAN` | "Çözümsüz atıf": basılan emir metni hiçbir kayıtta yok; sentezdeki danışman `K3.danismanlar`'da yok. |
| 18 | A:43 | `- The code will definitely produce wrong results regardless of inputs (clear logic errors)` | `bulgu_dogrula.py:92`; bulgular `:242`, `:283`, `:316`, `:334`, `:352`, `:385`, `:410`, `:428`, `:448` | Girdiden bağımsız kesin yanlışlar: yön çelişkisi, R aritmetiği, geometri, mühürde emir, R kapısı, rr_denetim, kapı-karar çelişkisi, güven tavanı, işaret uyuşmazlığı. |
| 19 | A:44 | `- Clear, unambiguous CLAUDE.md violations where you can quote the exact rule being broken` | `bulgu_dogrula.py:93-94`, `:722-724` | `sinif == "sozlesme"` ise `kural_alintisi` **zorunlu**; boşsa bulgu düşer. Öz-test vaka 6 bunu sınar. |
| 20 | A:46-49 | `Do NOT flag:` / `- Code style or quality concerns` / `- Potential issues that depend on specific inputs or state` / `- Subjective suggestions or improvements` | `bulgu_dogrula.py:97-102`, `:718-719` | `bicim` (:47), `kosullu` (:48), `oneri` (:49) sınıfları bayraklanmaz. Gerçek örnek: `tuzak_uyarisi` taşıyan aday `kosullu`dur (fiyat/likidite durumuna bağlı). |
| 21 | A:51 | `If you are not certain an issue is real, do not flag it. False positives erode trust and waste reviewer time.` | `bulgu_dogrula.py:726-728` | `kesin` alanı False ise bulgu düşer. |
| 22 | A:55 | `5. For each issue found in the previous step by agents 3 and 4, launch parallel subagents to validate the issue.` | `bulgu_dogrula.py:765-810` (`dogrula`), `:828-835` | Bulgu **başına** ayrı doğrulama kaydı; kaynağın "Use Opus subagents for bugs and logic issues, and sonnet agents for CLAUDE.md violations" kademelemesi `INCELEYICILER` tablosundaki `maliyet_sinifi` ile taşındı (`:696-701`). |
| 23 | A:57 | `6. Filter out any issues that were not validated in step 5. This step will give us our list of high signal issues for our review.` | `bulgu_dogrula.py:831-835` | Doğrulanmayan bulgu `elenen`e gider, `dogrulanan`a girmez; `--ayrinti` ile elenme gerekçesi gösterilir. |
| 24 | A:61 | `- If no issues were found, state: "No issues found. Checked for bugs and CLAUDE.md compliance."` | `bulgu_dogrula.py:845-850` | Türkçe karşılığı sabit metin olarak: `Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi.` |
| 25 | A:81 | `- Pre-existing issues` | `bulgu_dogrula.py:106`, `:737-738`, `:814` | `--onceki` raporunda AYNI kod bulunuyorsa elenir (aynı toplayıcı önceki rapora da koşturulur). |
| 26 | A:82 | `- Something that appears to be a bug but is actually correct` | `bulgu_dogrula.py:107`, `:739-740`, `:265-282` | Basılan seviyeler yuvarlanmıştır; R yuvarlanmış sayılarla tutmaz ama motor kaydıyla (`K5.emir_plani.birincil`) tutuyorsa gerçek hata değildir. |
| 27 | A:83 | `- Pedantic nitpicks that a senior engineer would not flag` | `bulgu_dogrula.py:108`, `:741-743`, `:80-82` | Önem eşiği: R farkı < 0.02, fiyat/oran farkı < 0.05 → elenir. |
| 28 | A:84 | `- Issues that a linter will catch (do not run the linter to verify)` | `bulgu_dogrula.py:109`, `:744-750` | Bu depoda "linter" = `gozlemci.py`. Gözlemci **yeniden koşturulmaz**; raporun kendi `DENETIM.ihlal`/`uyari` listesi okunur, orada geçen kod elenir. |
| 29 | A:85 | `- General code quality concerns (e.g., lack of test coverage, general security issues) unless explicitly required in CLAUDE.md` | `bulgu_dogrula.py:110`, `:751-752`, `:685-694` | `genel` sınıfı elenir; örnek: "türev kapsamı 1.00'in altında" genel veri-kalitesi endişesidir. |
| 30 | A:86 | `- Issues mentioned in CLAUDE.md but explicitly silenced in the code (e.g., via a lint ignore comment)` | `bulgu_dogrula.py:111`, `:753-758`, `:672-684` | "Susturma" bu depoda `emir_red_nedenleri` ve `varsayimlar`dır: motorun GEREKÇEYLE reddettiği aday yeniden bayraklanmaz. |
| 31 | A:9 | `- All tools are functional and will work without error. Do not test tools or make exploratory calls.` | `kademe.py` / `bulgu_dogrula.py` — dış çağrı yok | İki motor da yalnız verilen JSON'u okur; keşif amaçlı çağrı, ağ erişimi, motor koşturma YOKTUR. |
| 32 | B:2-4 | `name: evaluator` / `description: Skeptical second-opinion reviewer. …` / `tools: Read, Glob, Grep, Bash` | `degerlendirici.md:1-5` | Aynı frontmatter anahtarları (`name`, `description`, `tools`). `Bash` çıkarıldı — bkz. SAPMA 3. |
| 33 | B:9 | `You are reviewing work that a separate builder agent just claimed is complete. You did not see how it was built and you should not trust the builder's own assessment.` | `degerlendirici.md:7-15` | Birebir alıntılanarak korundu; "builder" → kararı üreten koşu. |
| 34 | B:11 | `Do the following every time:` | `degerlendirici.md:17` | Dört adımlı sabit yordam korundu. |
| 35 | B:13 | `1. Read the spec or acceptance criteria for the feature under review.` | `degerlendirici.md:19-21` | Kabul ölçütü = kök `CLAUDE.md` + `kademe.py`'nin `sozlesme_yollari` listesi. |
| 36 | B:14 | `2. Run `git diff` against the baseline to see exactly what changed.` | `degerlendirici.md:22-28` | "Değişen"in karşılığı: `son_rapor.json` + `kum_havuzu/onceki_kosu.json` (D: `piramit.py:1646`). |
| 37 | B:15 | `3. Open every screenshot or console log under `screenshots/` … and look at what they actually show, not what the filenames imply. If a file fails to open or returns an error, treat it as missing evidence.` | `degerlendirici.md:29-33`; ayrıca `bulgu_dogrula.py:44-47`, `:778-782` | Ajanda: her oy kaydının `yol`unu tek tek AÇ, alan adının ima ettiğine değil gösterdiğine bak. Motorda: açılamayan alan `KANIT_YOK` ve **aleyhe** sayılır. |
| 38 | B:16 | `4. Decide.` | `degerlendirici.md:34` | Korundu. |
| 39 | B:18 | `Plausibility is not correctness. A diff that looks reasonable paired with a screenshot that shows a broken layout is NEEDS_WORK. Missing evidence for any acceptance criterion is NEEDS_WORK. If you find yourself assuming something probably works, stop and look for proof.` | `degerlendirici.md:36-40` | Türkçesi + **İngilizce orijinali birebir** verildi; "akıcı gerekçe + ölçümle çelişen seviye = NEEDS_WORK" karşılığıyla. |
| 40 | B:20 | `Begin your reply with the bare word `PASS` or `NEEDS_WORK` on its own line, with nothing before it, so a wrapper script can read the verdict.` | `degerlendirici.md:48-50` | Sözleşme birebir korundu (çıplak kelime, kendi satırında, önünde hiçbir şey yok). |
| 41 | B:22-23 | `- `PASS`: one line stating what evidence convinced you.` / `- `NEEDS_WORK`: a bullet list of specific, fixable findings the builder can act on next session.` | `degerlendirici.md:52-56` | Aynı iki biçim; `PASS` satırına dosya + alan yolu zorunluluğu eklendi (depo eki). |
| 42 | B:3 | `Has no Write/Edit tools; Bash is granted for git diff only and is NOT a hard read-only boundary (drop it from tools if you need one).` | `degerlendirici.md:4`, `:58-64` | Kaynağın kendi tavsiyesi uygulandı: `Bash` çıkarıldı, gerekçesi alıntıyla yazıldı. |
| 43 | B:25 | `You cannot edit, write, or run the application. Do not offer to fix anything yourself.` | `degerlendirici.md:58-64` | Korundu: düzenleyemez, yazamaz, motor koşturamaz; onarım teklif etmez. |
| 44 | C:18 | `**Stub API server**: a tiny HTTP server that appends each request's headers to a JSONL file` | `bulgu_dogrula.py:37-44`, `:765-807` | Desenin özü: iddia, iddiayı üretenin kendi beyanından değil **bağımsız yakalanan artefakttan** okunur → her oy AYRI bir rapor alanından okunur. |
| 45 | C:31-32 | `, then read` / `   the captured JSONL.` (iki satır birleştirildi) | `bulgu_dogrula.py:777-786` | Hüküm, okunan kayıttan verilir (`oylar[].okunan`); yorum değil, okunan değer taşınır. |
| 46 | C:36-37 | `- Unit tests in `tests/test_patch.py` / `tests/test_patch_grade.py` need docker and fail on docker-less hosts — pre-existing, not your change.` | `bulgu_dogrula.py:737-738` (`:81`) | Kaynak 2'nin bu "pre-existing, not your change" uyarısı, kaynak 1'in `:81` yanlış-pozitif kuralıyla aynı ilkedir; `--onceki` kıyası bunu mekanikleştirir. |
| 47 | D: `piramit.py:1664` | `rapor["ZIRVE"]["EMIR"] = "EMİR YOK — DENETİM MÜHÜRÜ"` | `bulgu_dogrula.py:330-346` (`MUHURLU_EMIR`), `kademe.py:270-276` | Mühürlü koşuda emir kapanmalıdır; kapanmamışsa `:43` bulgusu. Aynı gerçek, kademede muafiyet gerekçesidir. |
| 48 | D: `sentez.py:159-164` | `if abs(score) < score_th:` / `decision = "NÖTR-BEKLE"; reasons.append(...)` | `bulgu_dogrula.py:405-425` (`KAPI_KARAR_CELISKISI`) | Kapı gerekçesi varken karar NÖTR-BEKLE değilse fail-closed kapı uygulanmamıştır. |
| 49 | D: `sentez.py:169-170` | `if decision == "NÖTR-BEKLE":` / `council_conf = round(min(council_conf, 0.35), 4)  # beklerken güven tavanı` | `bulgu_dogrula.py:79`, `:426-444` (`GUVEN_TAVANI_IHLALI`) | Tavan sabiti (0.35) **motordan** alındı, uydurulmadı. |
| 50 | D: `sentez.py:177-185` | `"""Ağırlıklı yön eğilimi — KARAR kapısından BAĞIMSIZ. … Saf işaret: >0 LONG, <0 SHORT, tam 0 ise NÖTR (gerçek berabere)."""` | `bulgu_dogrula.py:445-470` (`YON_SKOR_UYUSMAZ`) | `YON_BIAS`, `yon_skoru` işaretiyle uyuşmalıdır. |
| 51 | D: `rr_denetim.py:57` | `geom_ok = (stop > entry > target) if yon == "short" else (stop < entry < target)` | `bulgu_dogrula.py:310-329` (`GEOMETRI_BOZUK`) | Geometri kuralı motordan birebir alındı. |
| 52 | D: `gozlemci.py:27-28` | `CARPISMA       — motorlar birbirinin çıktısını kopyalamış görünüyor` / `(bağımsız olması gereken iki motor aynı sayıyı vermiş)` | `bulgu_dogrula.py:769-773` | Aynı `yol`dan ikinci kez oy alınmaz — kopya kanal bağımsız oy değildir. |
| 53 | D: `gozlemci.py:43` | `KRITIK = {"UYDURMA", "DAIRESEL", "EKSIK_AKTARIM", "MEMNUN_ETME"}` | `bulgu_dogrula.py:249`, `:414`, `:453`, `:479`, `:632` (`gozlemci_kodu` alanı) | Bulgular gözlemci koduyla eşlenir; gözlemci onu zaten yakaladıysa `:84` ile elenir (çift raporlama yok). |
| 54 | D: `kanit_kapisi.sh:47-51` | `{"decision":"block","reason":"Karar/emir dosyası değiştirilemez: bu oturumda hiçbir motor kanıtı Read ile açılmadı. …"}` | `degerlendirici.md:42-46` | Aynı ilke ajan sözleşmesine yazıldı: **rapor dosyasını AÇMADAN `PASS` verilemez.** |
| 55 | D: `son_rapor.json` | gerçek alanlar: `ZIRVE.YON_BIAS`, `ZIRVE.EMIR`, `ZIRVE.emir_adaylari[]`, `ZIRVE.emir_red_nedenleri`, `ZIRVE.sentez_karari`, `ZIRVE.kapi_gerekceleri`, `ZIRVE.ZORUNLU_EKSIK`, `ZIRVE.iki_satir`, `ZIRVE.ONCEKI_AKIBET`, `KIYAS`, `DENETIM.muhurlendi`, `katmanlar[].gecti`, `K2.motor_sonuclari`, `K3.danismanlar[].name`, `K4.verifier`, `K5.sentez`, `K5.emir_plani.birincil`, `K5.esik_kalibrasyonu.kaynak` | `kademe.py` + `bulgu_dogrula.py` boyunca | Alan adlarının **tamamı** gerçek koşu raporundan okundu; hiçbiri uydurulmadı. Doğrulama: gerçek rapora karşı koşu (aşağıda). |

## ADIM EŞLEME TABLOSU

`code-review.md`'nin 9 adımının her biri:

| # | Kaynak adım (A:satır) | Bizdeki karşılığı | Durum |
|---|---|---|---|
| 1 | `:14-20` haiku ön eleme (kapalı/taslak/önemsiz/zaten yorumlanmış) + `:22` muafiyet | `kademe.py:244-306` beş ucuz kapı + mühür muafiyeti | **TAM** |
| 2 | `:24-27` haiku, ilgili CLAUDE.md **yollarını** topla (içerik değil) | `kademe.py:172-202` `sozlesme_yollari()` | **TAM** |
| 3 | `:28` sonnet, değişikliklerin özeti | `kademe.py:205-231` `kosu_ozeti()` | **TAM** |
| 4 | `:30-53` 4 paralel inceleyici (2 sonnet sözleşme + 2 opus hata) + HIGH SIGNAL ölçütleri | `bulgu_dogrula.py:195-711` dört inceleyici + `:717-731` HIGH SIGNAL kapısı | **TAM** (ajan değil deterministik kontrol — SAPMA 1; ardışık koşar — SAPMA 2) |
| 5 | `:55` her bulgu için ayrı doğrulayıcı alt-ajan | `bulgu_dogrula.py:765-810` `dogrula()` — bulgu başına bağımsız çoklu-oy | **TAM** (alt-ajan değil — SAPMA 1) |
| 6 | `:57` doğrulanmayanı at | `bulgu_dogrula.py:831-835` `elenen` listesi | **TAM** |
| 7 | `:59-61` özet çıktı; bulgu yoksa sabit cümle | `bulgu_dogrula.py:845-850` + `ozet_metin()` `:857-884` | **TAM** |
| 8 | `:69` yorum taslağını kendin için çıkar, **hiçbir yere gönderme** | `bulgu_dogrula.py:812-855` `calistir()`'in `dogrulanan` listesi — varsayılan çıktıda bulgular basılır, `elenen` yalnız `--ayrinti` ile | **KISMİ** |
| 9 | `:71-77` inline GitHub yorumu gönder (`mcp__github_inline_comment__create_inline_comment`, `confirmed: true`) | — | **TAŞINMADI** |

**Taşınmayanın gerekçesi (adım 9):** bu beceri bir PR üzerinde çalışmaz; ortada
gönderilecek bir GitHub yorumu, bir diff satırı ve bir commit sha'sı yoktur.
Kaynağın 9. adımı bütünüyle GitHub yayınlama mekaniğidir (`:103-109` bağlantı
biçimi dahil) ve karşılığı olmadan taşınırsa **uydurma** olurdu. Aynı sebeple
`:63-67` `--comment` argümanı ve `:93-101` "no issues" yorum şablonu da
alınmadı; onların bilgi taşıyan kısmı (`:61` sabit cümlesi) 24. satırda
korunmuştur.

**Adım 8 neden kısmi:** kaynak "Do not post this list anywhere" der; bizde
gönderilecek yer olmadığı için kural anlamını yitirir. Taşınan kısım, bulgu
listesinin **yayınlanmadan önce elden geçirilmesi** ilkesidir: `elenen` adaylar
varsayılan çıktıda gösterilmez (`--ayrinti` ister), böylece elenmiş bulgu
kullanıcıya bulgu gibi sunulmaz.

## SAPMALAR

Kaynaktan saptığımız her nokta, gerekçesiyle:

### SAPMA 1 — "alt-ajan" yerine deterministik Python kontrolü (DÜRÜSTLÜK NOTU)

Kaynak beş yerde gerçek ajan başlatır: `:14` haiku, `:24` haiku, `:28` sonnet,
`:30-39` dört ajan, `:55` bulgu başına doğrulayıcı alt-ajanlar.
**Bu iki motor hiçbir alt-ajan başlatmaz.** `kademe.py` ve `bulgu_dogrula.py`
saf Python'dur; ağ çağrısı, model çağrısı, `Task`/`Agent` çağrısı içermezler.

Ne taşındı: (a) adımların **sırası** ve **kapıları**, (b) model kademelemesinin
**maliyet sınıfı** karşılığı (`ucuz`/`orta`/`pahali`, `kademe.py:42-47`,
`bulgu_dogrula.py:696-701`), (c) her adımın **kararı** (dur/devam, bayrakla/
bayraklama, doğrulandı/elendi).

Ne taşınamadı: bir ajanın serbest muhakemeyle **yeni** bir hata sınıfı
keşfetmesi. Motorlar yalnız **kodlanmış** kontrol ailelerini görür. Bu yüzden
zincirin 3. adımı (`.claude/agents/degerlendirici.md`) gerçek bir ajandır ve
serbest muhakemeyi orada yapar — motorlar onun kanıt disiplinini kurar,
yerine geçmez.

### SAPMA 2 — "paralel" adımlar ardışık koşar

Kaynak `:30` "4 agents in parallel", `:32` "in parallel", `:55` "parallel
subagents" der. `topla()` (`bulgu_dogrula.py:704-711`) dört inceleyiciyi
**ardışık** çağırır. Sonuç aynıdır çünkü inceleyiciler birbirinin çıktısını
okumaz (hepsi yalnız rapordan okur) ve kontroller deterministtir. Paralellik
kaynakta bir **hız** kararıdır, bir semantik kural değil.

### SAPMA 3 — `Bash` ajanın araç listesinden çıkarıldı

Kaynak `evaluator.md:4` `tools: Read, Glob, Grep, Bash` verir. Bunu kaynağın
**kendi tavsiyesiyle** daralttık (`evaluator.md:3`, birebir):
`Bash is granted for git diff only and is NOT a hard read-only boundary (drop it
from tools if you need one)`. Bu depoda kanıt bir git diff'i değil, bir JSON
raporudur; `Read`/`Glob`/`Grep` yeter. Böylece ajan gerçekten salt-okunur olur
ve `kanit_kapisi.sh`'ın kabul ettiği boşluk ("Bash sed/jq dosyayı denetimsizce
yeniden yazabilir") bu ajan için kapanır.

### SAPMA 4 — beşinci ön eleme kapısı kaynakta YOKTUR

`veri_ayni` kapısı (`kademe.py:293-306`) kaynağın dört sorusuna eklenmiş
**depo ekidir**. Gerekçesi kaynak değil, bu deponun `CLAUDE.md`'sidir:
"`engine/girdi/` verisi DEĞİŞMİŞSE boru hattını koşar ve iki-satır özetini
bağlama enjekte eder; veri değişmemişse son koşunun özetini taşır". Kapının
`kaynak` alanı bunu "depo eki" olarak **etiketler**; kaynak satırı iddia
edilmez.

### SAPMA 5 — çoklu-oy `verify/SKILL.md`'de LİTERAL olarak yoktur

Görev "çoklu-oy desenini uygula" der ve `verify/SKILL.md`'yi kaynak gösterir.
**Dürüst olmak gerekirse:** o dosyada `--oy`, "vote", "majority" gibi bir
kelime geçmez. Kaynakta olan şey, çoklu-oyun **ilkesidir**: bir iddiayı,
iddiayı üreten sürecin kendi beyanına sormak yerine bağımsız yakalanan bir
artefakttan okumak (`:18` başlıkları JSONL'e yazan stub sunucu, `:31-32`
", then read / the captured JSONL."), ve bir kanalın çalışmamasını **kanıt yokluğu**
saymak (`:36-37` "pre-existing, not your change" ile birlikte `evaluator.md:15`).

Bizim uyguladığımız: bir bulgu, raporun **birden çok bağımsız alanından** ayrı
ayrı okunur ve çoğunluk kuralı uygulanır (`bulgu_dogrula.py:765-810`).
Rastgele örnekleme YOKTUR (koşu deterministtir); "oy" = bağımsız kanaldan
okuma. Korkuluklar: aynı yol iki kez oy veremez, oy sayısı mevcut kanalı
aşamaz (eksik oy uydurulmaz), `KANIT_YOK` aleyhe sayılır, tek kanallı bulgu
doğrulanmış sayılmaz.

### SAPMA 6 — "PR" → "koşu kararı" çevirisinin sınırları

| Kaynaktaki kavram | Bizdeki karşılık | Zayıf nokta |
|---|---|---|
| PR diff | `ZIRVE` bloğu | Diff bir **değişimdir**; `ZIRVE` bir **durumdur**. "Pre-existing" (`:81`) ayrımı ancak `--onceki` verilirse yapılabilir; verilmezse hiçbir bulgu `:81` ile elenmez (fail-open değil, sadece kapsam dışı). |
| PR başlığı/açıklaması (`:53` yazarın niyeti) | `rapor["soru"]`, `ZIRVE.gecersizlik` | Koşuda "yazar niyeti" yoktur; motor niyet beyan etmez. Bu bağlam inceleyicilere verilmedi. |
| `gh pr view --comments` | `--defter` JSONL | Yorum yok; parmak izi defteri var. Defter verilmezse `zaten_yapildi` kapısı hiçbir zaman kapanmaz. |
| linter (`:84`) | `gozlemci.py` çıktısı | Gözlemci **yeniden koşturulmaz** (kaynak: "do not run the linter to verify"); yalnız raporun taşıdığı `DENETIM` okunur. Rapor gözlemci koşmadan üretilmişse bu kural sessizce boşa düşer. |

### SAPMA 7 — sabitler nereden geldi

`R_MIN = 1.35` (`bulgu_dogrula.py:77`) ve `BEKLE_GUVEN_TAVANI = 0.35`
(`:79`) **motorlardan** alınmıştır (CLAUDE.md emir kuralı; `sentez.py:170`).
Buna karşılık önem eşikleri `ONEM_ESIGI_R = 0.02` / `ONEM_ESIGI_FIYAT = 0.05`
(`:81-82`) ve oy mutabakat toleransı `0.005` **tasarım varsayımıdır** — kaynakta
`:83` "pedantic nitpicks" ölçüsü nicel verilmemiştir. Bu bir **[VARSAYIM]**
olarak burada etiketlenir; koşu verisinden kalibre edilmiş değildir.

## DOĞRULAMA

Dairesel değildir: öz-test vakaları **kaynağın kurallarına** karşı koşar
(HIGH SIGNAL ölçütleri, yanlış-pozitif listesi, ön eleme kapıları, çoğunluk
kuralı) ve ayrıca motorlar bu deponun **gerçek** koşu raporuna karşı çalıştırılır.

### `kademe.py --self-test` (10 vaka)

```
$ python3 .claude/skills/dogrulama-zinciri/scripts/kademe.py --self-test
MALİYET KADEMESİ — öz-test
[GECTI] temiz-kosu: DEVAM — kapı yok
[GECTI] kapali/katman-kapisi: DUR — koşu katman kapısında DURDU — değerlendirilecek karar yok
[GECTI] taslak/zorunlu-eksik: DUR — zorunlu girdi eksik (2) — karar TASLAK
[GECTI] onemsiz/notr-emirsiz: DUR — yön nötr ve emir yok — doğrulanacak sayısal iddia yok
[GECTI] zaten-degerlendirildi: DUR — bu koşu (sha256:b7b55df0e7bfee79) zaten değerlendirilmiş
[GECTI] veri-ayni: DUR — veri ilerlemedi (son bar 1785235500000 ≤ 1785235500000)
[GECTI] muafiyet/muhurlu-kosu: DEVAM — code-review.md:22 muafiyeti — DENETİM MÜHÜRÜ var; 'önems
[GECTI] maliyet-sirasi: sınıf sırası=[1, 1, 1, 1, 1] monoton=True; pahalı kademe koşmadı=True
[GECTI] yol-toplama: 1 yol, kök CLAUDE.md=True, içerik alanı yok=True
[GECTI] tasarruf: DUR'da orta/pahalı adım üretilmedi (YOK — pahalı doğrulama (bulgu_dogrula.py…)

10/10 vaka geçti (HEPSİ TAMAM)
EXIT=0
```

Kapsanan kaynak kuralları: `:15` (vaka 2), `:16` (3), `:17` (4), `:18` (5),
`:22` muafiyet (7), `:24` yalnız-yol (9), `:20` dur-ve-devam-etme (10),
depo eki (6), maliyet sıralaması (8).

### `bulgu_dogrula.py --self-test` (14 vaka)

```
$ python3 .claude/skills/dogrulama-zinciri/scripts/bulgu_dogrula.py --self-test
BULGU DOĞRULAYICI — öz-test
[GECTI] temiz-kosu: BULGU YOK — Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi
[GECTI] emir-yonu-ters: BULGU VAR — 1 doğrulanmış bulgu (1 aday elendi).
[GECTI] R-aritmetigi-tutarsiz: BULGU VAR — 1 doğrulanmış bulgu (1 aday elendi).
[GECTI] muhurlu-emir: BULGU VAR — 1 doğrulanmış bulgu (1 aday elendi).
[GECTI] bayraksiz-sinif: BULGU YOK — Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi
[GECTI] alintisiz-kural-elenir: :44 Clear, unambiguous CLAUDE.md violations where you can qu
[GECTI] onceden-var-elenir: BULGU YOK — Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi
[GECTI] gozlemci-yakalamis-elenir: BULGU YOK — Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi
[GECTI] susturulmus-elenir: BULGU YOK — Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi
[GECTI] genel-endise-elenir: BULGU YOK — Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi
[GECTI] cogunluk-kurali: 1/3 evet→RED, KANIT_YOK aleyhe→RED, tek kanal→RED
[GECTI] oy-tavani: istenen 9 → kullanılan 2 (kopya kanal sayılmadı)
[GECTI] yeniden-hesap-mutabik: BULGU YOK — Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi
[GECTI] kaynaksiz-danisman: BULGU VAR — 1 doğrulanmış bulgu (1 aday elendi).

14/14 vaka geçti (HEPSİ TAMAM)
EXIT=0
```

Kapsanan kaynak kuralları: `:42` (vaka 14), `:43` (2,3,4), `:44` (6),
`:47`/`:48` (5), `:57`+`:61` (1), `:81` (7), `:82` (13), `:84` (8),
`:85` (10), `:86` (9), çoklu-oy korkulukları (11,12).

### Gerçek koşu raporuna karşı (kendi çıktımıza değil, gerçek veriye)

```
$ python3 .../kademe.py --rapor .claude/skills/piramit-sistem/state/son_rapor.json \
      --kok /home/user/Future- --ozet
✔ [ucuz  ] kapali           code-review.md:15
✔ [ucuz  ] taslak           code-review.md:16
✔ [ucuz  ] onemsiz          code-review.md:17
✔ [ucuz  ] zaten_yapildi    code-review.md:18
✔ [ucuz  ] veri_ayni        depo eki
KARAR: DEVAM
Maliyet: ucuz=6 orta=1 pahali=0
EXIT=0

$ python3 .../bulgu_dogrula.py --rapor .../son_rapor.json --oy 3 --ozet --ayrinti
aday: 3 | doğrulanan: 0 | elenen: 3
   ✖ STOP_AVI_RISKI       HIGH_SIGNAL      :48 Potential issues that depend on specific inputs or state
   ✖ TUNEL_TEK_AILE       YANLIS_POZITIF   :84 Issues that a linter will catch …
   ✖ SISIRILMIS_R_ADAYI   YANLIS_POZITIF   :86 Issues mentioned in CLAUDE.md but explicitly silenced …
Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi.
EXIT=0
```

Yani motorlar **gerçek, sağlıklı bir koşuyu** hatalı bulmuyor (yanlış-pozitif
yok) ve gerçek rapordaki üç düşük-sinyalli adayı üç ayrı kuralla eliyor.
Bozuk bir koşuda ise bulgu üretip **oy dökümüyle** gösteriyor:

```
$ python3 .../bulgu_dogrula.py --rapor ornek/bozuk_rapor.json --oy 4 --ozet --ayrinti
⛔ EMIR_YON_CELISKISI [hata_1 :43] — Emir yönü SHORT ama YON_BIAS LONG
   doğrulama: çoğunluk: 4/4 EVET
      oy1 EVET  ZIRVE.EMIR = SHORT
      oy2 EVET  ZIRVE.emir_adaylari.0.yon = SHORT
      oy3 EVET  K5.emir_plani.yon = SHORT
      oy4 EVET  ZIRVE.yon_skoru = 0.42
EXIT=1
```

Tam çıktılar: `ornek/kademe_self_test.txt`, `ornek/bulgu_dogrula_self_test.txt`,
`ornek/gercek_kosu.txt`, `ornek/bozuk_kosu.txt`, `ornek/bozuk_rapor.json`.

## Dokunulmayan dosyalar

Yalnız `.claude/skills/dogrulama-zinciri/` altına ve
`.claude/agents/degerlendirici.md`'ye yazıldı (`.claude/agents/` dizini bu
görevle oluşturuldu). `.claude/settings.json`, `CLAUDE.md`, `.claude/hooks/`
ve diğer beceriler dahil **başka hiçbir dosya değiştirilmedi.**
