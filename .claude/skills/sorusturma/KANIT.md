# KANIT — `sorusturma` becerisinin kaynağa bağlanması

Kaynak: `a-defending-code-reference-harness/.claude/skills/triage/SKILL.md`
(1018 satır, sha `0b276c035644`); yardımcı kaynaklar
`.claude/skills/verify/SKILL.md` (42 satır, sha `40bbbc9145b3`),
`.claude/skills/triage/README.md`, `.claude/skills/_lib/checkpoint.py`,
harness `CLAUDE.md`.

Alıntılar **kopyala-yapıştırdır**, parafraz değildir. "Bizim dosya:satır"
sütunu bu commit'teki hâle aittir (`SKILL.md` 912 satır,
`scripts/sorusturma.py` 1484 satır, `kurallar/yanlis_pozitif.yaml` 213 satır).
Kısaltmalar: `SKILL` = `.claude/skills/sorusturma/SKILL.md`,
`py` = `.claude/skills/sorusturma/scripts/sorusturma.py`,
`yaml` = `.claude/skills/sorusturma/kurallar/yanlis_pozitif.yaml`.

## Kural eşleme tablosu

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|--------------------|--------------------------|-------------------|----------|
| 1 | triage/SKILL.md:28-32 | "Adversarial triage of raw security-scanner output. Does four jobs: **verify** each finding is real, **deduplicate** across runs and scanners, **rank** survivors by derived exploitability rather than the scanner's claimed severity, and **route** each to a component owner. Output is a short, ranked, owned list instead of a raw dump." | SKILL:35-40 | Dört iş korundu; "exploitability" → "türetilmiş etki" (arıza sömürülmez, tekrarlar). |
| 2 | triage/SKILL.md:10 | `argument-hint: "<findings-path> [--auto] [--votes N] [--repo PATH] [--fp-rules FILE] [--fresh]"` | SKILL:18 | `"<ariza-yolu> [--auto] [--oy N] [--depo PATH] [--yp-kurallari FILE] [--taze]"` — aynı beş bayrak. |
| 3 | triage/SKILL.md:11-23 | `allowed-tools:` … `Read / Glob / Grep / Write / Task / AskUserQuestion / Bash(git log:*) / Bash(jq:*) / Bash(find:*) / Bash(ls:*) / Bash(wc:*) / Bash(python3 .claude/skills/_lib/checkpoint.py:*)` | SKILL:19-30 | Aynı alan kümesi; `jq` düştü (bu depoda kullanılmıyor), checkpoint yardımcısı yerine `Bash(python3 .claude/skills/sorusturma/scripts/sorusturma.py:*)`. |
| 4 | triage/SKILL.md:36-37 | "parse from `$ARGUMENTS`; positional `$1`/`$2` expansion is not stable across runtimes" | SKILL:44-45 | Aynı uyarı çevrildi. |
| 5 | triage/SKILL.md:42-44 | "`--votes N`: verifier votes per finding (default 3; use 1 for a quick pass, 5 for high-stakes batches)." | SKILL:52-54 · py:924, 1458-1459 | `--oy N`, varsayılan 3; `MERCEKLER[:n]` ile ilk N mercek koşar. |
| 6 | triage/SKILL.md:48-51 | "`--fp-rules FILE`: append the contents of FILE to the verifier's exclusion-rule list (Phase 3a). Use for org-specific precedents" | SKILL:57-61 · py:630-673 | `--yp-kurallari FILE`; `_yp_kurallari_yukle` varsayılan YAML'in ÜSTÜNE ekler (YAML ya da düz metin satırları). |
| 7 | triage/SKILL.md:52-54 | "`--fresh`: ignore any existing checkpoint in `./.triage-state/` and start from Phase 0. Without this flag the skill resumes from the last completed phase if a checkpoint is present." | SKILL:62-65 · py:1311-1330 | `--taze`; bayraksız koşu `ilerleme.json`'dan devam eder. |
| 8 | triage/SKILL.md:60-66 | "**Do not execute target code.** No building, running, installing dependencies, or sending requests. … Every conclusion comes from reading source. This applies to the orchestrator and every subagent; include the constraint in every Task prompt." | SKILL:70-77 · py:31-35 | Alan çevirisi: "Boru hattını KOŞTURMA" — `piramit.py`/`karar_motoru.py` çalıştırılmaz, `engine/state` ve `hafiza` DEĞİŞTİRİLMEZ. Kısıt 3a isteminde de yazılı (SKILL:385-390). |
| 9 | triage/SKILL.md:68-69 | "**Do not reach the network.** No package-registry lookups, CVE-database queries, or upstream-commit fetches." | SKILL:79 · py:35 | "Ağa çıkma. Borsa/API sorgusu, paket kaydı araması, uzak veri çekme yok." |
| 10 | triage/SKILL.md:73 | "## Checkpointing (runs before Phase 0 and after every phase)" | SKILL:83 | "Kontrol noktası (Faz 0'dan önce ve her fazdan sonra koşar)". |
| 11 | triage/SKILL.md:75-78 | "On large finding batches a full run can exhaust context or hit rate limits mid-way — particularly Phase 3, which spawns `candidates × votes` verifiers. Phase state persists to `./.triage-state/` so a fresh `/triage` session can resume without re-asking the interview or re-spawning verifiers." | SKILL:85-91 | Aynı gerekçe; dizin `./.sorusturma-state/`. |
| 12 | triage/SKILL.md:87-90 | "`progress.json` — **single source of truth** for resume position … Resume decisions read ONLY this file, never a glob of `phase*.json` or shard files (stale files from a prior run must not be trusted)." | SKILL:96-101 · py:145-154 | `ilerleme.json` = TEK GERÇEK KAYNAK; `_ilerleme_oku` docstring'i bu kuralı taşır, `kostur` devam kararını yalnız bu dosyadan verir. |
| 13 | triage/SKILL.md:104-108 | "`status == \"running\"` with `phase_done == N` → **resume.** Read `./.triage-state/phase0.json` through `phaseN.json` **in order** … Print `Resuming from checkpoint: Phase N complete (…)`, and **skip directly to Phase N+1**." | SKILL:106-111 · py:1320-1332 | `for n in range(0, yeniden + 1)` ile SIRAYLA birleştirme, `Kontrol noktasından devam: Faz N tamam` çıktısı, `basla = yeniden + 1`. |
| 14 | _lib/checkpoint.py:119-123 | "All writes are atomic (tmp + os.replace) so a kill mid-write never leaves a partial file that breaks resume." | py:138-143 | `_atomik_yaz` = tmp + `os.replace`, aynı desen. |
| 15 | _lib/checkpoint.py:60-66 | "Resolve p and require it stays under CHECKPOINT_ROOT (default: cwd). … Confining to cwd keeps the blast radius at the repo being scanned." | py:126-137 | `_sinirla()`; ayrıca durum dizini adının `-state` ile bitmesi zorunlu (`must_end` karşılığı). |
| 16 | triage/SKILL.md:120 | "## Phase 0: Mode select and interview" | SKILL:117 | "Faz 0: Mod seçimi ve mülakat". |
| 17 | triage/SKILL.md:131-135 | "Unless `--auto` was passed, use **AskUserQuestion** to gather context that shapes verification and ranking. Batch into one or two calls of up to four questions. Expect free-text answers via \"Other\"; the multiple-choice options are prompts, not constraints." | SKILL:127-132 | Aynı; dört soru korundu (satır 18-21). |
| 18 | triage/SKILL.md:139-149 | "**Environment & trust boundary** … Reachability is judged against this boundary; \"command injection from env var\" is a true positive in a multi-tenant web service and a rule-8 false positive in an operator CLI." | SKILL:135-145 | Karşılığı **Kapsam**: kum havuzu artefaktındaki tutarsızlık YP kural 11'dir, aynı tutarsızlık `engine/state/` içinde gerçek arızadır — "sınır hükmü belirler" mantığı aynen. |
| 19 | triage/SKILL.md:151-158 | "**Threat model** … `What does a worst-case attacker look like for this system, and what must never happen? Free text is best.` … Phase 4 boosts findings that map onto a stated threat." | SKILL:146-155 | **Etki modeli**: "Bu sistemde ASLA olmaması gereken nedir?" — sicil ezilmesi / uydurma sayı / mühürlü koşuda emir / yön dönmesi / bayat girdi. Faz 4 yükseltmesi korundu. |
| 20 | triage/SKILL.md:161-168 | "**Scoring standard** … The precondition rule is always computed; this controls what `severity_label` additionally shows." | SKILL:156-164 | **Şiddet standardı**; "Ön koşul kuralı HER DURUMDA hesaplanır" cümlesi aynen taşındı. |
| 21 | triage/SKILL.md:170-175 | "**Noise tolerance** … `Precision: drop anything not majority-confirmed (fewer FPs, may miss real bugs)`, `Recall: keep split votes as needs_manual_test (more to review, fewer misses)`, `Ask me per-finding when it happens`." | SKILL:165-172 · py:869-887 | kesinlik / kapsam / sor — üçü de `_oylari_say` içinde uygulanır. |
| 22 | triage/SKILL.md:185-190 | "When `--auto` is set, do not call AskUserQuestion. Use: - Environment: `Unknown. Treat any externally-reachable entry point as untrusted…` - Threat model: empty (no boost). - Scoring: derived HIGH/MEDIUM/LOW. - Noise tolerance: precision." | SKILL:185-193 · py:288-296 | `OTO_BAGLAM`: kapsam "Bilinmiyor…", etki modeli boş, türetilmiş şiddet, kesinlik. |
| 23 | triage/SKILL.md:200-201 | "On resume past Phase 0, the interview is **not** re-asked; `context` is restored from this file." | SKILL:194-196 | Aynen; `faz0.json`'dan geri yüklenir. |
| 24 | triage/SKILL.md:246-247 | "For each raw record, build a finding dict. **Pull what's present; never guess what's absent.**" | SKILL:237-238 · py:328-336 | `_kanonik_al` yalnız var olan takma adı alır; bulunamayanlar `eksik_alanlar`'a yazılır. |
| 25 | triage/SKILL.md:249-260 | Alan eşleme tablosu (`file` ← `path`, `location.file`, `filename`; `category` ← `type`, `cwe`, `rule_id` …) | SKILL:240-252 · py:96-119 | `ALIAS` sözlüğü: aynı yapı, bu deponun anahtarlarıyla (`artefakt`, `katman`, `ihlal_kodu`, `kanit` …). |
| 26 | triage/SKILL.md:263-267 | "`id`: `f001`, `f002`, … in ingest order. If `scanner_confidence` is present on most findings, order ingest by it descending … This is a scheduling prior only — it does not affect verdicts." | SKILL:255-260 · py:508-512 | `a001…`; güven varsa azalan sıralama, "hükmü ETKİLEMEZ" notu korundu. |
| 27 | triage/SKILL.md:270-276 | "If `file` is missing or does not resolve under `--repo`, the finding is **unlocatable**: it skips dedup and verification and is emitted directly with `verdict: false_positive`, `verify_verdict: needs_manual_test`, `confidence: 0`, `refute_reasons: [\"doesnt_exist\"]` … Never emit a confident verdict on a finding you could not locate, and never let it absorb or be absorbed by dedup." | SKILL:262-270 · py:446-451, 534-543, 578-592 | `_yerellestirilemez` → `yanlis_pozitif` + `elle_inceleme_gerek` + `guven 0` + `kanit_yok`; Faz 2 kümelemesine ALINMAZ. Kaynak cümlesi py:448-450'de yorum olarak birebir taşındı. |
| 28 | triage/SKILL.md:280-288 | "Try, in order: (a) `repo/file` as-given; (b) `file` as an absolute or cwd-relative path; (c) `repo/file` with common prefixes stripped from `file` (`src/`, `app/`, `./`, or the repo's own basename…). Record which resolution worked and apply it to every finding. If none resolve, **stop**" | SKILL:269-279 · py:476-491, 544-552 | `_yol_coz` a/b/c aynen; hiçbiri çözülmezse rc=2 ile durur ve `--depo` önerisi basar. |
| 29 | triage/SKILL.md:242 | "If nothing parseable is found, stop and report what was seen." | SKILL:232-233 · py:503-509 | rc=1 + kaç dosyaya bakıldığı; "uydurma bulgu üretilmez". |
| 30 | triage/SKILL.md:301 | "## Phase 2: Deduplicate (before verification)" | SKILL:281 | "Faz 2: Tekilleştir (doğrulamadan ÖNCE)" — sıra korundu (Faz 2 < Faz 3). |
| 31 | triage/SKILL.md:993-995 | "**Dedupe runs before verify** to cut verifier spend by the duplication factor (often 2-4x on multi-scanner input) at the cost of one cheap subagent." | SKILL:283-290 (blok alıntı) · SKILL:882-885 | Sıranın **gerekçesi** kaynaktan birebir alıntılanarak SKILL.md'ye kondu; bu depoya özgü çoğaltma faktörü eklendi (aynı kök neden `ihlal` + `gozlemciler` + `ZIRVE.DENETIM`'de üç kez görünür). |
| 32 | triage/SKILL.md:307-311 | "same `file` (after path normalization), AND same `category` (case-insensitive, punctuation stripped), AND `line` numbers within 10 of each other. Both-missing matches; one-side-missing does NOT (a line-less record must not absorb a located one)." | SKILL:294-301 · py:561-575 | `_konum_yakin`: sayı ise ±10, metin ise birebir (katman adı), iki taraf eksik → eşleşir, tek taraf eksik → EŞLEŞMEZ. `_kategori_norm` noktalama soyar. |
| 33 | triage/SKILL.md:313-316 | "the canonical is the record with the fewest `missing_fields`; ties break to lowest `id`. Every other member gets `verdict: duplicate`, `duplicate_of: <canonical id>` … Record duplicate ids on the canonical as `absorbed: [...]`." | SKILL:302-306 · py:601-616 | Aynı seçim kuralı; alan adları `kopyasi` / `yuttuklari`. |
| 34 | triage/SKILL.md:322-356 | "Two findings are DUPLICATES if fixing one would also fix the other. Two findings are DISTINCT if they have genuinely independent root causes, even if they share a category or file." + `GROUP: <canonical_id> <- <dup_id>, …` | SKILL:307-350 | Aynı istem iskeleti; DUPLICATE/DISTINCT örnekleri arıza alanına çevrildi (aynı kök nedenin farklı katman gözlemcilerince yazılması vb.), çıktı `GRUP: … <- …`. |
| 35 | triage/SKILL.md:376-380 | "For each candidate, N independent adversarial verifiers re-derive the claim from the code and vote. Each verifier's stance is \"find any reason this is wrong.\" Each starts from the code at the cited location, not the scanner's description, and never sees the other verifiers' reasoning (shared context propagates blind spots)." | SKILL:354-360 | Birebir çevrildi; "code" → "artefakt". |
| 36 | triage/SKILL.md:386-388 | "Your default assumption is that the scanner is WRONG. Your job is to re-derive the claim from the source code yourself" | SKILL:376-377 | "Varsayılan varsayımın: RAPOR EDEN YANILIYOR." |
| 37 | triage/SKILL.md:404-405 | "PROCEDURE: follow all four steps. Each exists because skipping it lets a specific false-positive class through." | SKILL:398-399 | Dört adım korundu (oku / geriye izle / korkuluk ara / korkuluğu zorla). |
| 38 | triage/SKILL.md:413-419 | "TRACE REACHABILITY BACKWARDS FROM THE SINK. … A plausible-sounding chain is NOT enough: for at least the FIRST link in the chain, READ the actual call site and QUOTE the file:line in your rationale. Unreachable code is the single largest false-positive source." | SKILL:406-414 | Alan çevirisi: sink → üretici motor/katman. "Kaynaksız sayı … en büyük gerçek-arıza sınıfıdır; tersine, kaynağı bulunan sayı en büyük yanlış-pozitif sınıfıdır." `ILK_KANIT` alıntı zorunluluğu korundu. |
| 39 | triage/SKILL.md:421-427 | "HUNT FOR PROTECTIONS. Actively look for reasons the finding is WRONG: - Input validation / sanitization upstream of the sink - Framework auto-escaping, parameterized queries … - Dead code, test-only code, example/fixture code" | SKILL:415-423 | Korkuluk listesi bu depoya çevrildi: kapı düşmüş mü, mühür devrede mi (`muhurlendi: true`), "VERİ YOK" etiketlenmiş mi, `rr_denetim`/`usd_hedef`/`esik_kalibre` geçmiş mi, KONVANSİYON sabiti mi, kum havuzu artefaktı mı. |
| 40 | triage/SKILL.md:429-432 | "STRESS-TEST EACH PROTECTION. For each protection you found: is it applied on EVERY path to the sink, or only the one the scanner happened to trace?" | SKILL:424-430 | "HER yolda mı uygulanıyor, yoksa yalnız raporun izlediği yolda mı?" + mühür varken `ZIRVE.EMIR` gerçekten kapandı mı. |
| 41 | triage/SKILL.md:435-437 | "EXCLUSION RULES: if the finding matches any of these, it is FALSE_POSITIVE even if technically accurate. Cite the rule number in your verdict." | yaml:1-26 · SKILL:431-433 · py:926-940 | 16 güvenlik kuralı → 13 depo kuralı; kural numarası hükümde anılır (`yp_kurali`). **Vetolama:** kaynakta kurallar HER doğrulayıcının önünde olduğu için oylamayla aşılamaz — motorda YP eşleşmesi tüm oyları çevirir, her merceğin kanıtı gerekçede korunur. |
| 42 | triage/SKILL.md:438-439 | " 1. Volumetric DoS or missing rate-limiting (handled at infrastructure layer)." | yaml:28-46 (kural 1) | Karşılığı: kapı düşmesi / DURDU = fail-closed TASARIM. İstisna deseni motor çökmesini (`Traceback`) dışarıda tutar. |
| 43 | triage/SKILL.md:441-442 | " 2. Test-only code, dead code, example/fixture code, or a crash with no security impact." | yaml:172-186 (kural 11) | Karşılığı: kum havuzu / öz-test artefaktı gerçek sicili etkilemez; istisna `engine/state/(durum\|defter)`. |
| 44 | triage/SKILL.md:443-444 | " 3. Behavior that is the intended design (compression middleware, a backward-compatible weak algorithm offered alongside a strong one)." | yaml:47-158 (kurallar 2,3,4,5,7,8,9) | "Tasarım gereği" ailesi: BEKLE hükmü, çelişki turu → NÖTR, mühürün devreye girmesi, "VERİ YOK" beyanı, "bekleme penceresi dolmadı", etiketli STATİK KORKULUK, "ilk analiz". |
| 45 | triage/SKILL.md:461-463 | " 13. Missing hardening or best-practice gap with no concrete exploit path (missing security headers, no audit logging, permissive config that isn't actually reached by untrusted input)." | yaml:103-119 (kural 6) | TÜNEL uyarısı tek başına VERİ EKSİKLİĞİDİR, kod arızası değil; aile raporda VARSA ama doğrulanmadıysa istisna devreye girer. |
| 46 | triage/SKILL.md:476-486 | "VERDICT: your response MUST end with EXACTLY this block: VERDICT / CONFIDENCE / REFUTE_REASON / EXCLUSION_RULE / FIRST_LINK / RATIONALE" | SKILL:454-464 | `HUKUM / GUVEN / CURUTME_NEDENI / YP_KURALI / ILK_KANIT / GEREKCE` — altı alan bire bir karşılandı. |
| 47 | triage/SKILL.md:496-499 | "CANNOT_VERIFY: static reasoning genuinely hit its limit … Use sparingly; it must not become the default." | SKILL:474-476 · py:59-60 | `DOGRULANAMADI`; "İdareli kullan; VARSAYILAN HÂLİNE GELMEMELİ." |
| 48 | triage/SKILL.md:504-515 | "**Always set `subagent_type`; never fork.** Omitting `subagent_type` forks the orchestrator, and a fork inherits the full conversation context … That defeats verifier independence and re-introduces the inherited-framing failure mode this phase exists to prevent." | SKILL:485-494 | Birebir çevrildi; 4a uyarısı dahil. |
| 49 | triage/SKILL.md:543-546 | "**Put all verifier Task calls in a single assistant message** so they run concurrently. Do not set `run_in_background` … If `len(candidates) * N` exceeds ~40, shard into sequential batches of ~40" | SKILL:519-523 | Aynen. |
| 50 | triage/SKILL.md:588-590 | "Findings with a `file` but no `line` get **one** verifier vote regardless of `--votes` (a file-level sweep is expensive and doesn't benefit from voting)." | SKILL:540-542 · py:924 | `n = 1 if not _metin(b.get("konum")).strip() else …`. |
| 51 | triage/SKILL.md:592-603 | "**If any Task call returns `status: \"async_launched\"` instead of the verifier's text**, the runtime backgrounded it … Do not end your turn until every vote is accounted for. … do not poll transcript files." | SKILL:524-534 | Aynı iki kurtarma yolu; 2b ve 4a'ya da uygulanır. |
| 52 | triage/SKILL.md:605-612 | "If a verifier errored, timed out, or produced no parseable VERDICT block, re-spawn it once. If the retry also fails, count that vote as `cannot_verify` with `confidence: 0` … The remaining N-1 votes still decide." | SKILL:543-551 | Aynen; `dogrulayici_hatasi`. |
| 53 | triage/SKILL.md:616-627 | "`confidence`: mean CONFIDENCE across votes that agree with the majority, rounded to one decimal. … `rationale`: the RATIONALE from the highest-confidence vote on the winning side, verbatim." | SKILL:552-560 · py:848-893 | `_oylari_say`: kazanan taraf ortalaması (1 ondalık), modal YP kuralı, sıralı benzersiz çürütme nedenleri, benzersiz ilk kanıtlar, **birebir** gerekçe. |
| 54 | triage/SKILL.md:629-640 | "Majority TRUE_POSITIVE → `verdict: true_positive` … No majority (tie, or majority CANNOT_VERIFY): Noise tolerance `precision` → `verdict: false_positive`; append `\"(split vote, dropped under precision policy)\"` to rationale." | SKILL:561-575 · py:869-893 | Aynı üç dal; eklenen ibare "(oy bölündü, kesinlik politikasıyla düşürüldü)". |
| 55 | triage/SKILL.md:652-665 | "This is the most expensive checkpoint. … additionally checkpoint **per candidate** as its votes are tallied … the Phase-3 entry point reads `progress.json:shards_done` (default `[]` — do **not** glob shard files on disk; stale shards from a prior run may exist)" | SKILL:581-588 · py:178-196, 913-922 | `parca_<id>.json` + `parcalar_tamam`; devamda yalnız listede OLMAYAN adaylar doğrulanır, disk glob'lanmaz. |
| 56 | triage/SKILL.md:669-673 | "Recompute severity from preconditions and reachability rather than category name … Verification and severity are independent judgments; \"this is real\" must not inflate into \"this is critical.\"" | SKILL:592-596 | Birebir çevrildi. |
| 57 | triage/SKILL.md:708-719 | "\| Preconditions \| Access required \| Severity \| … \| 0 \| Unauthenticated remote \| HIGH \| … Evaluate each column independently and take the LOWER result. … Cross-check: if your preconditions list has 3+ items, HIGH is almost certainly wrong." | SKILL:631-643 · py:1043-1055 | Tablo bire bir: ön koşul 0 / 1-2 / 3+ × tekrar koşulu her_kosuda / belirli_veride / elle_mudahaleyle → YÜKSEK/ORTA/DÜŞÜK; `min(..., key=_SIDDET_RANK)` ile **DÜŞÜK olan** alınır. |
| 58 | triage/SKILL.md:721-724 | "A match may raise severity by ONE step (LOW to MEDIUM or MEDIUM to HIGH), never two." | SKILL:643-648 · py:1057-1058 | `if eslesme and _SIDDET_RANK[siddet] < 2:` — tek basamak, tavan YÜKSEK. |
| 59 | triage/SKILL.md:726-735 | "would the CLAIMED severity contribute to alert fatigue? … Score in -5..+5: +3..+5 claimed severity is justified or understated / 0..+2 roughly right / -1..-3 inflated by one level / -4..-5 badly inflated (LOW dressed as HIGH)" | SKILL:649-657 · py:1060-1068 | `siddet_hizasi`: fark → {2:+5, 1:+3, 0:+2, -1:-3, -2:-5}. Öz-testte a003 için -3 (bir seviye şişirilmiş) ölçüldü. |
| 60 | triage/SKILL.md:736-742 | "exploitable … mitigated  real, but a deployed control reduces it below the derived severity (name the control) … needs_manual_test" | SKILL:658-664 · py:1070-1082 | `onarilabilir` / `hafifletilmis` (kontrol ADIYLA yazılır — `_hafifletici` mührü/emir kapısını okur) / `elle_inceleme_gerek`. |
| 61 | triage/SKILL.md:770-772 | "For findings that did NOT reach Phase 4 (`false_positive`, `duplicate`, unlocatable): set `severity: null`, `verify_verdict: null`, `severity_alignment: null`, `preconditions: []`." | SKILL:691-694 · py:1015-1021 | Aynen. |
| 62 | triage/SKILL.md:788-799 | "stop at the first hit: 1. **CODEOWNERS / OWNERS.** … 2. **git log.** … `git -C {REPO} log --format='%an' -n 50 -- \"{file}\" \| sort \| uniq -c \| sort -rn \| head -3`. … 3. **Module fallback.**" | SKILL:699-712 · py:1100-1150 | Üç basamak aynen; `_git_sahip` aynı git komutunu koşar (öz-testte "en çok katkı veren: Claude (1/1 son commit)"). |
| 63 | triage/SKILL.md:800-804 | "State the source so confidence is clear; a bare username is less useful than `\"component: auth/; no CODEOWNERS entry; top committer jsmith (14/20 recent commits)\"`." | SKILL:713-718 | Aynı cümle; örnek bu depoya çevrildi (`piramit-sistem/scripts/`). |
| 64 | triage/SKILL.md:819-826 | "### 6a. Sort … 1. `verdict`: `true_positive`, then `duplicate`, then `false_positive`. 2. Within true positives: `severity` HIGH > MEDIUM > LOW, then `confidence` descending, then `severity_alignment` descending." | SKILL:722-728 · py:1159-1170 | `_sirala` aynen. |
| 65 | triage/SKILL.md:881-883 | "Every input finding appears exactly once (duplicates reference their canonical via `duplicate_of`). Do not silently drop anything. Do not print this JSON to the terminal; write to file only." | SKILL:762-765 · py:1212-1215 | Aynen; JSON terminale basılmaz. Öz-test ayrıca doğrular ("her bulgu tam bir kez raporda"). |
| 66 | triage/SKILL.md:887-890 | "Build it **incrementally**. Do NOT emit the whole file in one Write. One chunk per finding; a stalled chunk loses that one section, not the file." | SKILL:766-771 · py:204-215, 1240-1276 | `_ekle()` ile bulgu başına parça eklenir; docstring kuralı taşır. |
| 67 | triage/SKILL.md:901 | "## Act on these" | SKILL:771 · py:1229 | `## Şunlarla ilgilen` — çıktının birinci yarısı. |
| 68 | triage/SKILL.md:908-915 | "### [{severity}] {title}  ({id})" · "`{file}:{line}` \| {category} \| claimed {claimed_severity} (alignment {severity_alignment:+d}) \| confidence {confidence}/10" · "**Owner:**" · "**Verdict:**" · "**Preconditions ({n}):**" · "**Why:**" · "**Reachability evidence:**" | SKILL:775-790 · py:1240-1259 | Alan alan aynı bölüm şablonu; "Reachability evidence" → "Kanıt izi". |
| 69 | triage/SKILL.md:916-917 | "> Recommend a human build a PoC; static reasoning hit its limit." | SKILL:788-790 · py:1251-1253 | "> Statik muhakeme sınırına dayandı; bu bulguyu ELLE tekrar üret (kontrollü koşu) — otomatik hüküm verilmedi." |
| 70 | triage/SKILL.md:929-935 | "## Dropped" · "\| id \| title \| file:line \| why dropped \|" · "{false_positives: refute_reasons + exclusion_rule}" · "{duplicates: \"duplicate of {duplicate_of}\"}" · "{unlocatable: \"no source location in input\"}" | SKILL:792-801 · py:1261-1276 | `## Düşenler` — üç düşme sınıfı da gerekçesiyle tabloda; "sessiz düşürme yoktur" satırı eklendi. |
| 71 | triage/SKILL.md:942-957 | "### 6d. Terminal summary — Under ~12 lines: … `Top refute reasons: {top 3 refute_reasons with counts}`" | SKILL:806-820 · py:1280-1303 | `_terminal_ozet`; "En sık çürütme nedeni: tasarim_geregi×2, kopya×1, kanit_yok×1". |
| 72 | triage/SKILL.md:963-971 | "Smoke test (five-finding fixture: 2 real, 1 dup, 2 FP) … Expected: f001 and f003 confirmed; f002 duplicate of f001; f004 dropped (`misread_code`…); f005 dropped (`already_handled`…)" | SKILL:847-860 · ornek/ornek_ariza.json · py:1363-1450 | Altı bulgulu örnek (2 gerçek, 1 kopya, 2 YP, 1 yerelleştirilemez); beklenti aynı kalıpta: a001+a003 onaylanır, a002 a001 kopyası, a004 kural 1, a005 kural 2, a006 `kanit_yok`. |
| 73 | triage/SKILL.md:980-982 | "Hand-check a sample of TRUE_POSITIVE/HIGH results (the `first_links` should point at real call sites) and a sample of FALSE_POSITIVE rejects (the `exclusion_rule` or `refute_reasons` should be defensible)." | SKILL:869-873 | Aynen; gerçek artefakta karşı koşu örneği eklendi. |
| 74 | triage/SKILL.md:988-992 | "**Checkpoints are per-phase JSON**, not conversation state. … file-backed checkpoints let a brand-new session pick up from the last completed phase. `./.triage-state/` is scratch — add to `.gitignore`." | SKILL:876-881 · .gitignore:3-6 | Aynen; `.sorusturma-state/` gitignore'a eklendi. |
| 75 | triage/SKILL.md:996-998 | "**Semantic dedupe is one agent**, given only id/file/line/category/title: enough to cluster, not enough to leak one scanner's reasoning into another finding's verification." | SKILL:886-888 | Aynen. |
| 76 | triage/SKILL.md:1003-1005 | "**`CANNOT_VERIFY`** exists so verifiers aren't forced into a false binary. It maps to `needs_manual_test` under recall policy and to a drop under precision policy." | SKILL:892-894 | Aynen. |
| 77 | triage/SKILL.md:1006-1007 | "**Threat-model boost is capped at one step** so a stated threat can't re-inflate a LOW back to HIGH and defeat the precondition rule." | SKILL:895-896 | Aynen (etki modeli). |
| 78 | triage/SKILL.md:1008-1010 | "**`severity_label` is separate from `severity`.** Sorting always uses the precondition-derived HIGH/MEDIUM/LOW; the label is presentation-layer for whatever standard the reviewer's tooling expects." | SKILL:897-899 · py:1084-1088 | `siddet_etiketi` ayrı alan; sıralama daima türetilmiş şiddetle. |
| 79 | triage/SKILL.md:999-1002 | "**Bash is allowed narrowly** for `git log` (owner hints), `jq`/`find` (ingest), and `python3 .claude/skills/_lib/checkpoint.py` (state I/O). The actual safety property is \"no execution of target code,\" which is preserved." | SKILL:889-891 | Aynen; korunan özellik "boru hattı çalıştırılmaz, sicil değiştirilmez" olarak çevrildi. |
| 80 | triage/README.md:74-76 | "A `needs_manual_test` verdict means static reasoning hit its limit on that finding — treat it as a recommendation for a human to build a controlled proof-of-concept, not as a failure." | SKILL:908-912 | "…bu bir başarısızlık değil, dürüst bir sınır beyanıdır." |
| 81 | verify/SKILL.md:8-10 | "The pipeline's real surface is the in-container `claude -p` process and its outbound API requests. Without docker, drive the same pinned CLI binary directly with the env dict the harness would inject via `docker -e`." | py:1363-1450 | Disiplin aktarıldı: öz-test sahte katman kurmaz, **gerçek motoru** (`kostur()`) uçtan uca sürer, gerçek `SORUSTURMA.json/.md` üretir ve ayrıca kontrol-noktasından devam yolunu da gerçekten koşturup sonucu karşılaştırır. |
| 82 | harness CLAUDE.md:279-281 | "Interactive: `/dnr-hunt` (no alert in hand) → `/dnr-respond` (lead in hand) → `/triage` → `/patch` (run the last two from inside the run dir so their outputs land beside the incidents)." | SKILL:825-843 | Çıktının koşu dizininin yanına düşmesi fikri `--cikti-dizini` ile karşılandı (varsayılan cwd; öz-testte `ornek/`). |

---

## FAZ EŞLEME TABLOSU

| Kaynak fazı (triage/SKILL.md) | Bizdeki karşılığı | Durum |
|-------------------------------|-------------------|-------|
| **Checkpointing** (73-117; Faz 0'dan önce + her fazdan sonra) | SKILL:83-115 · py:145-215 (`_ilerleme_oku`, `_faz_kaydet`, `_parca_kaydet`, `_atomik_yaz`, `_ekle`) | **TAŞINDI.** `ilerleme.json` tek gerçek kaynak, `fazN.json`, `parca_<id>.json`, atomik yazım, `--taze`, devam mesajı. |
| **Faz 0 — Mode select and interview** (120-201) | SKILL:117-197 · py:288-325 (`OTO_BAGLAM`, `faz0_mod`) | **TAŞINDI.** Dört soru + Tur 2 koşullu takip + `--auto` varsayılanları + devamda mülakat sorulmaz. Mülakat AskUserQuestion ile beceride yapılır, cevaplar `--baglam` ile motora geçer (bkz. SAPMALAR §2). |
| **Faz 1 — Ingest and normalize** (205-297) | SKILL:199-279 · py:328-558 (`_kanonik_al`, `_rapordan_bulgular`, `_jsonl_bulgular`, `_markdown_bulgular`, `_dosyadan`, `_yol_coz`, `faz1_al`) | **TAŞINDI.** Biçim tanıma bu deponun artefaktlarına çevrildi (piramit raporu, gözlemci çıktısı, defter jsonl, serbest not); alan sözlüğü, id/kaynak/eksik_alanlar, yerelleştirilemez kuralı, a/b/c yol çözümü. |
| **Faz 2 — Deduplicate (before verification)** (301-370) | SKILL:281-350 · py:561-627 (`_konum_yakin`, `_kategori_norm`, `faz2_tekille`) | **TAŞINDI.** Determinist geçiş motorda; anlamsal geçiş (tek alt-ajan) SKILL.md'de istemiyle. Sıra (Faz 2 < Faz 3) ve **gerekçesi** birebir alıntıyla korundu. |
| **Faz 3 — Verify** (374-665) | SKILL:352-588 · py:630-1010 (5 mercek, `_yp_kurallari_yukle`, `_oylari_say`, `faz3_dogrula`) | **TAŞINDI.** Çok oylu bağımsız doğrulama, `--oy N`, tek-oy istisnası, tally kuralları, gürültü toleransının üç dalı, parça kontrol noktası, YP kuralları + veto. Doğrulayıcı gövdesi ikili: mekanik mercekler (motor) + LLM alt-ajanları (`--oy-dosyasi`) — bkz. SAPMALAR §3. |
| **Faz 4 — Rank by exploitability** (669-781) | SKILL:590-694 · py:963-1098 (`_on_kosul_turet`, `_hafifletici`, `_etki_eslesmesi`, `faz4_sirala`) | **TAŞINDI, ALAN ÇEVİRİSİYLE.** "exploitability" → "etki": erişim seviyesi (unauthenticated / authenticated / local) yerine **tekrar koşulu** (her_kosuda / belirli_veride / elle_mudahaleyle). Tablo, "iki kolonu bağımsız değerlendir, DÜŞÜK olanı al", tek basamak yükseltme, -5..+5 hiza, üç `dogrulama_hukmu` aynen. |
| **Faz 5 — Route** (785-813) | SKILL:697-718 · py:1100-1156 (`_git_sahip`, `faz5_yonlendir`) | **TAŞINDI.** CODEOWNERS → git log → bileşen yedeği; kaynak beyanı zorunlu. |
| **Faz 6 — Output** (817-957) | SKILL:720-823 · py:1159-1303 (`_sirala`, `faz6_cikti`, `_terminal_ozet`) | **TAŞINDI.** Sıralama, `SORUSTURMA.json` (TRIAGE.json şemasının karşılığı), parça parça `SORUSTURMA.md`, "Şunlarla ilgilen" / "Düşenler", <12 satır terminal özeti. |

**Taşınmayan faz yoktur — 7 fazın (0-6) tamamı ve fazlardan önce koşan
kontrol noktası katmanı karşılandı.**

---

## SAPMALAR

### 1. Alan çevirisi: güvenlik → finans karar-desteği

| Kaynak kavramı | Bizdeki karşılığı | Gerekçe |
|----------------|-------------------|---------|
| "security finding" (tarayıcı bulgusu) | "arıza bulgusu" (boru hattı arızası) | Depo bir tarayıcı değil, karar-destek boru hattı. Arıza sınıfları: motor beklenmedik sonuç, kapıda durma, sicil ezilmesi, gözlemci ihlali, akıbet-karar tutarsızlığı. |
| "target codebase" (`--repo`) | artefakt kökü (`--depo`) | Doğrulama kaynak kodu kadar **koşu artefaktını** (rapor/defter/durum JSON'ları) okur. |
| "reachability from untrusted input" | "kaynağa bağlanabilirlik": sayı/alan alt katmanda üretilmiş mi | Bu depodaki muadil soru "saldırgan buraya ulaşabilir mi" değil, "bu sayının kaynağı var mı" (gözlemcinin UYDURMA denetimi). |
| "exploitability" / access level | "etki" / tekrar koşulu | Arıza sömürülmez, TEKRARLAR. Erişim seviyesi kolonunun yerini "her koşuda / belirli veride / elle müdahaleyle" aldı; tablo yapısı ve "DÜŞÜK olanı al" kuralı korundu. |
| 16 dışlama kuralı (DoS, SSRF, XSS…) | 13 YP kuralı (kapı düşmesi, BEKLE, mühür, VERİ YOK…) | Güvenlik kuralları bu depoda anlamsız; yerlerine deponun kendi **tasarım gereği** davranışları kondu. Kural numarasının hükümde anılması kuralı sürüyor. |
| "Do not execute target code" | "Boru hattını KOŞTURMA, sicili DEĞİŞTİRME" | Aynı güvenlik özelliğinin bu depodaki karşılığı: yeniden koşmak `engine/state/` ve `hafiza/` içeriğini değiştirir, yani soruşturma kendi kanıtını bozar. |
| `TRIAGE.json` / `TRIAGE.md` | `SORUSTURMA.json` / `SORUSTURMA.md` | Depo dili Türkçe. |

### 2. `--auto` / mülakat modunun karşılığı

Kaynakta mülakat AskUserQuestion ile **beceri içinde** yapılır ve cevaplar
`context` sözlüğü olarak fazlar boyunca taşınır. Burada mekanik kısım bir
Python motorudur ve **Python AskUserQuestion çağıramaz.** Bölüşüm:

- **Mülakat** (Faz 0b) SKILL.md'de, AskUserQuestion ile, dört soruyla
  yapılır — kaynağın soru sayısı, başlıkları ve şık mantığı korunarak
  (SKILL:127-183).
- Cevaplar Write ile `./.sorusturma-state/baglam.json`'a yazılır ve motora
  **`--baglam`** bayrağıyla verilir (`faz0_mod`, py:298-325). Bağlam
  `faz0.json`'a kaydedilir; devamda mülakat yeniden sorulmaz.
- `--auto` verildiğinde motor `OTO_BAGLAM` sabitini kullanır (py:288-296):
  kaynağın auto varsayılanlarının birebir karşılığı.
- Gürültü toleransının `sor` dalı motorda **kesinliğe düşer** ve bölünmüş
  bulguları `ozet.bolunmus_oylar` altında listeler; SKILL.md bunları tek
  AskUserQuestion çağrısında sunmayı ve seçimi `--baglam` ile geri
  beslemeyi tarif eder (SKILL:570-575) — kaynak: "collect all split
  findings and present them in one AskUserQuestion call at the end of
  Phase 3".

### 3. Doğrulayıcının gövdesi: alt-ajan yerine mercek + alt-ajan

Kaynakta Faz 3'ün N oyu N adet LLM alt-ajanıdır. Python motoru alt-ajan
üretemez, ama **çok-oylu bağımsız doğrulama** korunacak kadar
merkezîydi. Çözüm ikili:

- **Mekanik mercekler** (her koşuda, deterministik, py:679-846):
  `artefakt` (kanıt dosyada birebir var mı, `dosya:satır` alıntısıyla),
  `yp_kural` (13 kural + koşuya özgü ekler), `tasarim` (deponun kendi
  sözleşmesi — `gozlemci.py`'nin `KRITIK` kümesi ve `piramit.py`'nin
  FAIL-CLOSED beyanı, **gerçek satır numarası aranarak**; py:242-253),
  `tekrar` (koşu artefaktları boyunca yineleniyor mu), `celiski` (aynı
  kod için TEMİZ kaydı var mı). Her mercek **farklı bir kanıt ailesine**
  bakar — kaynaktaki "shared context propagates blind spots" gerekçesinin
  mekanik karşılığı. `--oy N` ilk N merceği koşturur.
- **LLM doğrulayıcıları**: SKILL.md Faz 3a istemi Task ile koşulur,
  oyları `--oy-dosyasi` ile motora verilir ve **aynı havuzda** sayılır
  (py:943-946).

Sapma gizlenmiyor: `--auto` ile yalnız motor koşulduğunda oylar
mekaniktir; anlam gerektiren bulgularda LLM doğrulayıcıları eklenmezse
hüküm `DOGRULANAMADI`ya ve oradan (kesinlik politikasında) düşüşe
eğilimlidir — yani **fail-closed** tarafa sapar, memnun etme tarafına
değil.

### 4. YP kuralı vetosu (kaynağa dönüş, motora eklenti)

Mekanik merceklerde dışlama kuralları tek bir merceğin oyu olsaydı
çoğunlukla ezilebilirdi. Kaynakta ise kurallar **her** doğrulayıcının
isteminde yer alır, dolayısıyla hepsi aynı yönde oy verir. Bunu korumak
için motor, YP kuralı (istisnası tutmadan) eşleştiğinde tüm oyları
YANLIS_POZITIF'e çevirir ve her merceğin kendi bulgusunu gerekçede saklar
(py:926-940). Bu, kaynağın davranışını **taklit eder**, ondan sapmaz;
buraya yazılma nedeni uygulamanın kaynakta birebir karşılığı olmamasıdır.
Gerçek artefakt koşusunda etkisi ölçüldü: `K4-AGI/TUNEL` uyarısı veto
olmadan çoğunlukla "gerçek arıza" çıkıyordu, vetoyla YP kural 6'ya düştü.

### 5. Taşınmayan özellikler

| Kaynakta var | Neden taşınmadı |
|--------------|-----------------|
| `Bash(jq:*)` izni | Bu depoda jq kullanılmıyor; JSON okuma motorun içinde. |
| `INCIDENTS.json` / `reports/bug_*/report.json` / `found_bugs.jsonl` alım yolları (triage/SKILL.md:218-235) | `vuln-pipeline`'a özgü kapsayıcılar; bu depoda karşılıkları yok. Yerlerine piramit raporu, gözlemci çıktısı ve `*defter*.jsonl` tanıyıcıları kondu. |
| ASAN üst-kare çıkarımı (`crash.crash_type` → `category`) | C/C++ çökme artefaktı yok. |
| CVSS v3.1 / v4.0 ve OWASP Risk Rating şıkları (triage/SKILL.md:164-166) | Bu depoda anlamı yok; `siddet_etiketi` alanı korundu, şıklar depo kodlamalarıyla değiştirildi (gözlemci kodlaması / koşu-engelleyici-karar-bozan-gürültü / depo bug-bar'ı). |
| Kompakt doğrulayıcı istemi (triage/SKILL.md:548-586) | Ölçek gerekçesi ("when `candidates * votes > ~50`") bu depoda gerçekleşmiyor: tipik koşu 2-6 bulgu üretiyor. Tek istem tutuldu. |
| `checkpoint.py rundir` (harness zaman damgalı koşu dizini) | Bu depo koşu dizini üretmiyor; çıktı yeri `--cikti-dizini` ile verilir. |
| `verify/SKILL.md`'nin docker-suz CLI sürme reçetesi | Harness'e özgü katkıcı aracı; bu depoda muadili yok. Aktarılan tek şey **disiplini** (kanıt satırı 81). |

---

## DOĞRULAMA

```
$ python3 .claude/skills/sorusturma/scripts/sorusturma.py --self-test
Kontrol noktasından devam: Faz 3 tamam (…/ornek/.sorusturma-state/faz3.json)
========================================================================
SORUŞTURMA ÖZ-TESTİ
========================================================================
  GEÇTİ  6 kayıt alındı  [girdi_sayisi=6]
  GEÇTİ  a001 gerçek arıza  [gercek_ariza]
  GEÇTİ  a002 a001'in kopyası  [kopya/a001]
  GEÇTİ  a003 gerçek arıza  [gercek_ariza]
  GEÇTİ  a004 YP kural 1 ile düştü (kapı = tasarım)  [yanlis_pozitif/kural=1]
  GEÇTİ  a005 YP kural 2 ile düştü (BEKLE = hüküm)  [yanlis_pozitif/kural=2]
  GEÇTİ  a006 yerelleştirilemez → kanit_yok  [kanit_yok]
  GEÇTİ  her bulgu tam bir kez raporda
  GEÇTİ  çok mercekli oylama koştu (≥3 oy)  [{"gercek_ariza": 3, "yanlis_pozitif": 0, "dogrulanamadi": 0}]
  GEÇTİ  şiddet türetildi (a001 YÜKSEK)  [YÜKSEK]
  GEÇTİ  a003 ön koşullu → ORTA  [ORTA kosul=['ikinci sembol koşusu açık olmalı']]
  GEÇTİ  a003 şiddet hizası negatif (iddia şişirilmiş)  [-3]
  GEÇTİ  sahip ipucu atandı  [en çok katkı veren: Claude (1/1 son commit); CODEOWNERS kaydı yok]
  GEÇTİ  kanıt izi dosya:satır taşıyor  [YP kuralları: 13 kural, eşleşme yok | ornek_rapor.json:10]
  GEÇTİ  MD 'Şunlarla ilgilen' bölümü var
  GEÇTİ  MD 'Düşenler' bölümü var
  GEÇTİ  düşenler tabloda gerekçeli
  GEÇTİ  JSON dosyası yazıldı
  GEÇTİ  kontrol noktası tamamlandı
  GEÇTİ  kontrol noktasından devam aynı sonucu verdi
------------------------------------------------------------------------
Soruşturma tamam: 6 kayıt → 2 gerçek arıza, 3 yanlış pozitif, 1 kopya.

  YÜKSEK: 1   Kıyas motoru koşmadı: hesap verme başlığı boş kaldı
  ORTA:   1
  DÜŞÜK:  0
  Elle inceleme gerek: 1

  En sık çürütme nedeni: tasarim_geregi×2, kopya×1, kanit_yok×1

Yazıldı: …/ornek/SORUSTURMA.md ve …/ornek/SORUSTURMA.json
------------------------------------------------------------------------
SONUÇ: 20/20 test geçti — TAMAMI GEÇTİ
```

Öz-test kaynağın duman testini (triage/SKILL.md:963-971) aynı kalıpta
izler: 2 gerçek arıza onaylandı, 1 kopya kanoniğe bağlandı, 2 bulgu YP
kuralıyla (numarası anılarak) düştü, 1 bulgu yerelleştirilemedi. Ek olarak
**kontrol noktasından devam** yolu gerçekten koşturulur ve iki koşunun
özeti karşılaştırılır (yalnız dosya varlığı değil, sonuç eşitliği).

### Gerçek artefakta karşı koşu (kurgu değil, canlı depo verisi)

```
$ python3 .claude/skills/sorusturma/scripts/sorusturma.py \
      .claude/skills/piramit-sistem/state/son_rapor.json --auto --oy 5 --depo .

Soruşturma tamam: 2 kayıt → 1 gerçek arıza, 1 yanlış pozitif, 0 kopya.
  YÜKSEK: 1   önceki kayıt var ama akıbet ölçülemedi: ÖLÇÜLEMEDİ
  En sık çürütme nedeni: artefakt_yanlis_okunmus×1, uygulanabilir_degil×1
```

- `K1-LLM/HAFIZA` bulgusu **gerçek arıza** çıktı; kanıt izi `gozlemci.py:43`
  (deponun `KRITIK` kümesinin gerçek satırı — aranarak bulundu, sabit
  yazılmadı), `son_rapor.json:6` ve `son_rapor.json:1324`.
- `K4-AGI/TUNEL` uyarısı **YP kural 6** ile düştü ("TÜNEL uyarısı tek
  başına VERİ EKSİKLİĞİDİR, kod arızası değil") — kaynağın 13. dışlama
  kuralının bu depodaki karşılığı.

### Değiştirilen dosyalar

Yalnız `.claude/skills/sorusturma/` altı:

```
.claude/skills/sorusturma/SKILL.md
.claude/skills/sorusturma/KANIT.md
.claude/skills/sorusturma/.gitignore
.claude/skills/sorusturma/scripts/sorusturma.py
.claude/skills/sorusturma/kurallar/yanlis_pozitif.yaml
.claude/skills/sorusturma/ornek/ornek_ariza.json      (öz-test girdisi)
.claude/skills/sorusturma/ornek/ornek_rapor.json      (öz-test artefaktı)
.claude/skills/sorusturma/ornek/ornek_defter.jsonl    (öz-test artefaktı)
.claude/skills/sorusturma/ornek/SORUSTURMA.{json,md}  (öz-test çıktısı)
```

`.claude/settings.json`, kök `CLAUDE.md`, `.claude/hooks/` ve diğer
beceriler **DEĞİŞTİRİLMEDİ**; `engine/` altına yazılmadı.
