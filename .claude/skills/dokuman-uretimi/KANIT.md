# KANIT — dokuman-uretimi

Bu dosya, `dokuman-uretimi` becerisinin **kaynaktan** üretildiğini (hafızadan
değil) satır satır kanıtlar. Doğrulama kaynağa karşıdır; kendi çıktımızla
kendimizi doğrulamak dairesel olurdu.

## Okunan kaynak (Read ile TAM okundu)

Kök: `/tmp/claude-0/-home-user-Future-/283be249-69b7-573a-85a7-42416ba6aa9f/scratchpad/a-skills/`

| Dosya | Satır (`splitlines`) | sha256 (ilk 12) | Görev tanımındaki beyan | Durum |
|---|---|---|---|---|
| `template/SKILL.md` | 6 | `eb685d91de03` | 6 satır / `eb685d91de03` | **UYUYOR** |
| `skills/skill-creator/SKILL.md` | 485 | `dcd4803e61e9` | 485 satır / `dcd4803e61e9` | **UYUYOR** |
| `skills/skill-creator/scripts/quick_validate.py` | 103 | `67cf57034020` | 103 satır / `67cf57034020` | **UYUYOR** (`wc -l` 102 der — dosya satır sonu ile bitmiyor; `splitlines()` 103. sha birebir tutuyor) |
| `skills/skill-creator/scripts/improve_description.py` | 247 | `87d864570220` | (satır/sha beyan edilmedi) | okundu |
| `skills/skill-creator/scripts/package_skill.py` | 136 | `1a33059b0db1` | (beyan edilmedi) | okundu |
| `skills/skill-creator/scripts/utils.py` | 47 | `3af8ae62c40c` | (beyan edilmedi) | okundu |
| `spec/agent-skills-spec.md` | 3 | `ff22f2be775f` | 3 satır, yönlendirme | **UYUYOR** — yerel şartname metni **YOK** |

## Üretilen dosyalar

| Dosya | Satır |
|---|---|
| `.claude/skills/dokuman-uretimi/SKILL.md` | 146 |
| `.claude/skills/dokuman-uretimi/sablon/SKILL.md.sablon` | 91 |
| `.claude/skills/dokuman-uretimi/scripts/beceri_dogrula.py` | 760 |
| `.claude/skills/dokuman-uretimi/ornek/self_test_cikti.txt` | üretilmiş çıktı |
| `.claude/skills/dokuman-uretimi/ornek/depo_denetim.txt` / `.json` | üretilmiş çıktı |
| `.claude/skills/dokuman-uretimi/KANIT.md` | bu dosya |

---

## 1. SATIR SATIR KANIT TABLOSU

Alıntılar **kopyala-yapıştırdır**. Kaynakta birden çok satıra yayılan ya da
liste maddesi olan bir alıntıyı tek hücrede birleştirdiysem "Uygulama"
sütununda **BİRLEŞTİRİLMİŞ** yazıyor — o hücre "birebir tek satır" değildir,
satırların birebir metinleri `<br>` ile ayrılmıştır.

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|---|---|---|---|
| 1 | `quick_validate.py:17-19` | `skill_md = skill_path / 'SKILL.md'`<br>`if not skill_md.exists():`<br>`return False, "SKILL.md not found"` | `scripts/beceri_dogrula.py:208-211` | BİRLEŞTİRİLMİŞ (3 satır). `YOK_SKILL_MD` kuralı; mesaj metni kaynaktan birebir korundu: `"SKILL.md not found"`. |
| 2 | `quick_validate.py:23-24` | `if not content.startswith('---'):`<br>`return False, "No YAML frontmatter found"` | `scripts/beceri_dogrula.py:216-217` | BİRLEŞTİRİLMİŞ (2 satır). `YOK_FRONTMATTER`; mesaj birebir. |
| 3 | `quick_validate.py:27-29` | `match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)`<br>`if not match:`<br>`return False, "Invalid frontmatter format"` | `scripts/beceri_dogrula.py:74`, `221-223` | BİRLEŞTİRİLMİŞ (3 satır). Aynı regex `FM_DESENI` sabitine alındı: `re.compile(r"^---\n(.*?)\n---", re.DOTALL)`; `GECERSIZ_FM_BICIM` mesajı birebir. |
| 4 | `quick_validate.py:36-37` | `if not isinstance(frontmatter, dict):`<br>`return False, "Frontmatter must be a YAML dictionary"` | `scripts/beceri_dogrula.py:250-252` | BİRLEŞTİRİLMİŞ (2 satır). `FM_SOZLUK_DEGIL`; mesaj birebir. |
| 5 | `quick_validate.py:38-39` | `except yaml.YAMLError as e:`<br>`return False, f"Invalid YAML in frontmatter: {e}"` | `scripts/beceri_dogrula.py:232`, `243-247` | BİRLEŞTİRİLMİŞ (2 satır). `FM_YAML_HATASI`; mesaj öneki birebir (`Invalid YAML in frontmatter: `), hata metni 200 karakterde kırpılır. |
| 6 | `quick_validate.py:42` | `ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}` | `scripts/beceri_dogrula.py:47-70` | Altı anahtar birebir `KAYNAK_ALLOWED_PROPERTIES`'te. UYGULANAN küme GENİŞLETİLMİŞTİR: `DEPO_EK_PROPERTIES = {"argument-hint", "tools"}` ile birleştirilir — gerekçe ve kanıt §5 sonundaki ÇÖZÜLDÜ notunda. Kaynak listesi daraltılmadı. |
| 7 | `quick_validate.py:44-45` | `# Check for unexpected properties (excluding nested keys under metadata)`<br>`unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES` | `scripts/beceri_dogrula.py:264` | BİRLEŞTİRİLMİŞ (2 satır). `beklenmeyen = set(fm.keys()) - ALLOWED_PROPERTIES` — aynı küme farkı. |
| 8 | `quick_validate.py:48-49` | `f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "`<br>`f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"` | `scripts/beceri_dogrula.py:266-272` | BİRLEŞTİRİLMİŞ (2 satır). Aynı mesaj, aynı `sorted()` sırası; f-string yerine `+` birleştirme (görev kısıtı: f-string içinde ters bölü yasak). |
| 9 | `quick_validate.py:53-54` | `if 'name' not in frontmatter:`<br>`return False, "Missing 'name' in frontmatter"` | `scripts/beceri_dogrula.py:275-276` | BİRLEŞTİRİLMİŞ (2 satır). `EKSIK_NAME`; mesaj birebir. |
| 10 | `quick_validate.py:55-56` | `if 'description' not in frontmatter:`<br>`return False, "Missing 'description' in frontmatter"` | `scripts/beceri_dogrula.py:277-279` | BİRLEŞTİRİLMİŞ (2 satır). `EKSIK_DESCRIPTION`; mesaj birebir. |
| 11 | `quick_validate.py:60-61` | `if not isinstance(name, str):`<br>`return False, f"Name must be a string, got {type(name).__name__}"` | `scripts/beceri_dogrula.py:284-288` | BİRLEŞTİRİLMİŞ (2 satır). `NAME_METIN_DEGIL`; `type(name).__name__` ile aynı mesaj. |
| 12 | `quick_validate.py:64` | `# Check naming convention (kebab-case: lowercase with hyphens)` | `scripts/beceri_dogrula.py:57-58` | Yorum, `NAME_DESENI` sabitinin gerekçesi olarak korundu. |
| 13 | `quick_validate.py:65-66` | `if not re.match(r'^[a-z0-9-]+$', name):`<br>`return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"` | `scripts/beceri_dogrula.py:58`, `294-298` | BİRLEŞTİRİLMİŞ (2 satır). Regex birebir `r"^[a-z0-9-]+$"`; mesaj birebir. |
| 14 | `quick_validate.py:67-68` | `if name.startswith('-') or name.endswith('-') or '--' in name:`<br>`return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"` | `scripts/beceri_dogrula.py:300-304` | BİRLEŞTİRİLMİŞ (2 satır). Koşul birebir kopyalandı; mesaj birebir. |
| 15 | `quick_validate.py:69-71` | `# Check name length (max 64 characters per spec)`<br>`if len(name) > 64:`<br>`return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."` | `scripts/beceri_dogrula.py:61`, `306-310` | BİRLEŞTİRİLMİŞ (3 satır). `NAME_MAKS = 64`; mesaj birebir. **Not:** yorumdaki "per spec" iddiası doğrulanamadı (bkz. §4). |
| 16 | `quick_validate.py:75-76` | `if not isinstance(description, str):`<br>`return False, f"Description must be a string, got {type(description).__name__}"` | `scripts/beceri_dogrula.py:321-325` | BİRLEŞTİRİLMİŞ (2 satır). `DESC_METIN_DEGIL`; mesaj birebir. |
| 17 | `quick_validate.py:79-81` | `# Check for angle brackets`<br>`if '<' in description or '>' in description:`<br>`return False, "Description cannot contain angle brackets (< or >)"` | `scripts/beceri_dogrula.py:331-335` | BİRLEŞTİRİLMİŞ (3 satır). `DESC_ACI_PARANTEZ`; koşul ve mesaj birebir. Depoda **1 gerçek ihlal** yakalandı (§5). |
| 18 | `quick_validate.py:82-84` | `# Check description length (max 1024 characters per spec)`<br>`if len(description) > 1024:`<br>`return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."` | `scripts/beceri_dogrula.py:65`, `336-341` | BİRLEŞTİRİLMİŞ (3 satır). `DESC_MAKS = 1024`; karşılaştırma **kesin büyüktür** (`> 1024`), yani tam 1024 GEÇER — kaynakla aynı davranış. Depoda **4 gerçek ihlal** (§5). |
| 19 | `quick_validate.py:89-90` | `if not isinstance(compatibility, str):`<br>`return False, f"Compatibility must be a string, got {type(compatibility).__name__}"` | `scripts/beceri_dogrula.py:378-382` | BİRLEŞTİRİLMİŞ (2 satır). `COMPAT_METIN_DEGIL`; mesaj birebir. |
| 20 | `quick_validate.py:91-92` | `if len(compatibility) > 500:`<br>`return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."` | `scripts/beceri_dogrula.py:68`, `383-388` | BİRLEŞTİRİLMİŞ (2 satır). `COMPAT_MAKS = 500`; mesaj birebir. |
| 21 | `quick_validate.py:103` | `sys.exit(0 if valid else 1)` | `scripts/beceri_dogrula.py:756`, `760` | `return 1 if any(r["hata_sayisi"] for r in raporlar) else 0` + `sys.exit(main())` — aynı fail-closed çıkış sözleşmesi (0 = geçti, 1 = geçmedi). |
| 22 | `improve_description.py:132` | `Concretely, your description should not be more than about 100-200 words, even if that comes at the cost of accuracy. There is a hard limit of 1024 characters — descriptions over that will be truncated, so stay comfortably under it.` | `scripts/beceri_dogrula.py:65`, `71`, `343-348`; `SKILL.md:65`; `sablon/SKILL.md.sablon:63-66` | İKİ ayrı kural: 1024 = **sert sınır** (HATA, `DESC_COK_UZUN`); 100-200 kelime = **yumuşak** (`DESC_COK_KELIME`, UYARI) çünkü kaynak "about" diyor. `DESC_KELIME_ONERI = 200`. |
| 23 | `improve_description.py:154-155` | `"char_count": len(description),`<br>`"over_limit": len(description) > 1024,` | `scripts/beceri_dogrula.py:336-341` | BİRLEŞTİRİLMİŞ (2 satır). 1024 sınırının ikinci bağımsız kaynak teyidi; aynı `>` karşılaştırması. |
| 24 | `improve_description.py:163` | `if len(description) > 1024:` | `scripts/beceri_dogrula.py:337` | Üçüncü teyit (kaynağın kendi "safety net" dalı). Aynı eşik, aynı operatör. |
| 25 | `improve_description.py:135` | `- The skill should be phrased in the imperative -- "Use this skill for" rather than "this skill does"` | `sablon/SKILL.md.sablon:81-82`; `SKILL.md:71` | Şablonun 8. doldurma kuralı: "Yazım emir kipinde." |
| 26 | `improve_description.py:136` | `- The skill description should focus on the user's intent, what they are trying to achieve, vs. the implementation details of how the skill works.` | `sablon/SKILL.md.sablon:4-8` | Şablon description iskeleti "ne yapar + hangi soru/durumda" niyet ekseninde kurgulandı. |
| 27 | `improve_description.py:137` | `- The description competes with other skills for Claude's attention — make it distinctive and immediately recognizable.` | `sablon/SKILL.md.sablon:8` | "Tetikleyici kelimeler (TR/EN)" listesi ayırt edicilik için şablonda zorunlu alan. |
| 28 | `skill-creator/SKILL.md:67` | `- **description**: When to trigger, what it does. This is the primary triggering mechanism - include both what the skill does AND specific contexts for when to use it. All "when to use" info goes here, not in the body.` | `scripts/beceri_dogrula.py:350-355`; `sablon/SKILL.md.sablon:73-75`; `SKILL.md:66` | KIRPILMIŞ alıntı (satır 67 daha uzundur; devamı "undertrigger/pushy" kısmıdır — bkz. #29). `DESC_NIYET_YOK` UYARI kuralı bundan türedi. |
| 29 | `skill-creator/SKILL.md:67` (aynı satırın devamı) | `Note: currently Claude has a tendency to "undertrigger" skills -- to not use them when they'd be useful. To combat this, please make the skill descriptions a little bit "pushy".` | `SKILL.md:72-73` | KIRPILMIŞ alıntı. "Description biraz ısrarcı yazılır" kuralı; bu deponun "OTOMATİK devreye girer" geleneğinin kaynaktaki gerekçesi. |
| 30 | `skill-creator/SKILL.md:76-83` | `skill-name/`<br>`├── SKILL.md (required)`<br>`│   ├── YAML frontmatter (name, description required)`<br>`│   └── Markdown instructions`<br>`└── Bundled Resources (optional)`<br>`    ├── scripts/    - Executable code for deterministic/repetitive tasks`<br>`    ├── references/ - Docs loaded into context as needed`<br>`    └── assets/     - Files used in output (templates, icons, fonts)` | `sablon/SKILL.md.sablon` (dizin sözleşmesi); `SKILL.md:104-118` | BİRLEŞTİRİLMİŞ (8 satır). Beceri anatomisi: `SKILL.md` zorunlu, `scripts/` çalışan kod. Bu depoda 22 beceriden 18'i `scripts/` taşıyor — ölçüldü, varsayılmadı. |
| 31 | `skill-creator/SKILL.md:88-91` | `Skills use a three-level loading system:`<br>`1. **Metadata** (name + description) - Always in context (~100 words)`<br>`2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)`<br>`3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)` | `sablon/SKILL.md.sablon:79-80` | BİRLEŞTİRİLMİŞ (4 satır). Kademeli açılım; description'ın "her zaman bağlamda" olması 1024 sınırının GEREKÇESİDİR. |
| 32 | `skill-creator/SKILL.md:96` | `- Keep SKILL.md under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.` | `sablon/SKILL.md.sablon:79-80`; `SKILL.md:68-69` | Şablonun 7. doldurma kuralı. Bizim `SKILL.md` = 146 satır (sınırın altında; ölçüldü). |
| 33 | `skill-creator/SKILL.md:117` | `Prefer using the imperative form in instructions.` | `sablon/SKILL.md.sablon:81-82`; `SKILL.md:71` | Emir kipi kuralı; #25 ile aynı yöne iki bağımsız kaynak. |
| 34 | `skill-creator/SKILL.md:139` | `Try to explain to the model why things are important in lieu of heavy-handed musty MUSTs. Use theory of mind and try to make the skill general and not super-narrow to specific examples.` | `sablon/SKILL.md.sablon:19-22` ("Neden var" bölümü) | KIRPILMIŞ alıntı (satır 139 bir cümle daha sürer). Şablonda her beceriye zorunlu "Neden var" bölümü konuldu — kural değil GEREKÇE aktarılsın diye. |
| 35 | `skill-creator/SKILL.md:335` | `The description field in SKILL.md frontmatter is the primary mechanism that determines whether Claude invokes a skill.` | `SKILL.md:33-40` ("Neden var") | Doğrulayıcının neden description üzerinde yoğunlaştığının gerekçesi. |
| 36 | `skill-creator/SKILL.md:398` | `Skills appear in Claude's `available_skills` list with their name + description, and Claude decides whether to consult a skill based on that description.` | `SKILL.md:33-40` | Bozuk frontmatter'ın neden "beceri HİÇ YÜKLENMEZ" demek olduğunun mekanik açıklaması. |
| 37 | `skill-creator/SKILL.md:439` | `- **Preserve the original name.** Note the skill's directory name and `name` frontmatter field -- use them unchanged. E.g., if the installed skill is `research-helper`, output `research-helper.skill` (not `research-helper-v2`).` | `scripts/beceri_dogrula.py:312-316`; `KANIT.md §3-D2` | **DİKKAT — SAPMA.** Kaynak "değiştirmeden koru" der; **eşitlik şartı KOYMAZ.** `NAME_DIZIN_UYUSMAZ` bu satırdan TÜRETİLMEMİŞTİR; DEPO EKİ'dir (§3). |
| 38 | `utils.py:34-35` | `# Handle YAML multiline indicators (>, |, >-, |-)`<br>`if value in (">", "|", ">-", "|-"):` | `scripts/beceri_dogrula.py:172-176`, `366-372` | BİRLEŞTİRİLMİŞ (2 satır). Kaynağın tanıdığı 4 blok göstergesi bizde de tanınır; bizimki 2 tane daha kabul eder (`>+`, `|+`) — **SAPMA**, §4/2. |
| 39 | `package_skill.py:17` | `from scripts.quick_validate import validate_skill` | `scripts/beceri_dogrula.py:1-25` (modül sözleşmesi) | Kaynakta doğrulayıcı, paketleyicinin **kapısıdır**. Bizde de aynı rol: üretim akışının son adımı doğrulayıcıdır (`SKILL.md:118-121`). |
| 40 | `package_skill.py:70-76` | `# Run validation before packaging`<br>`valid, message = validate_skill(skill_path)`<br>`if not valid:`<br>`print(f"❌ Validation failed: {message}")`<br>`print("   Please fix the validation errors before packaging.")`<br>`return None` | `SKILL.md:113-114`, `126-129` | BİRLEŞTİRİLMİŞ (satır 70, 72-76; satır 71 atlandı). Fail-closed devri: doğrulama düşerse iş **durur**, devam etmez. |
| 41 | `template/SKILL.md:1-6` | `---`<br>`name: template-skill`<br>`description: Replace with description of the skill and when Claude should use it.`<br>`---`<br>``<br>`# Insert instructions below` | `sablon/SKILL.md.sablon:1-13` | BİRLEŞTİRİLMİŞ (6 satır = dosyanın tamamı). Şablon iskeleti buradan; **genişletildi** — kaynak şablon 6 satır ve bu deponun sözleşmesini (tetikleyici ifadesi, motor yolu, öz-test, uyarı satırı) taşımaz. Genişletme **DEPO EKİ**'dir, kaynak iddiası değildir. |
| 42 | `spec/agent-skills-spec.md:1-3` | `# Agent Skills Spec`<br>``<br>`The spec is now located at <https://agentskills.io/specification>` | `SKILL.md:122-128` | BİRLEŞTİRİLMİŞ (3 satır = dosyanın tamamı). Yerel şartname metni **YOKTUR**; URL bu ortamdan erişilemedi (§4/1). |

---

## 2. BU DEPONUN SÖZLEŞMESİ — VARSAYILMADI, ÖLÇÜLDÜ

`sablon/SKILL.md.sablon` bu depodaki **22 gerçek becerinin** frontmatter'ı
taranarak çıkarıldı (`.claude/skills/*/SKILL.md`, `yaml.safe_load` ile
ayrıştırıldı; `dokuman-uretimi` kendisi sayımın DIŞINDA — kendini sayıp
"gelenek" ilan etmek dairesel olurdu). Ölçüm anı **2026-07-29T00:26Z**; depo
eşzamanlı değiştiği için (§5b) sayılar o anın fotoğrafıdır. Ölçüm sonucu:

| Özellik | Kaç beceride | Şablondaki karşılığı |
|---|---|---|
| `name` = dizin adı | 22 / 22 | zorunlu (HATA) |
| `description: >-` katlanmış blok | 21 / 22 | `KATLANMIS_BLOK_ONER` (UYARI) |
| "OTOMATİK devreye girer" + "slash komutu gerekmez" | 20 / 22 | `TETIKLEYICI_SOZLESME` (UYARI) |
| "Tetikleyici kelimeler (TR/EN)" listesi | 19 / 22 | aynı kural |
| "Çalışan motor: ..." (birebir ifade) | 14 / 22 | şablon alanı, kural değil |
| motor yolu herhangi bir biçimde ("Çalışan motor" / "Motor:" / "Motor kodu") | 16 / 22 | tek kalıp dayatılmadı — bu yüzden kural değil |
| `scripts/` dizini var | 18 / 22 | `MOTOR_OZTEST_YOK` yalnız bu 18'e uygulanır |
| "canlı/otomatik emir DAHİL DEĞİL" uyarısı | 2 / 22 (`karar-kurulu`, `piramit-sistem`) | şablonda **koşullu** ("değilse SİL") |
| `allowed-tools` / `argument-hint` gibi ek anahtar | 2 / 22 | `BEKLENMEYEN_ANAHTAR` (§5'te 1 gerçek ihlal) |

Gövde başlıkları da sayıldı; en sık `## Zorunlu disiplin` (5), `## Koşum` (3),
`## Doğruluk sözleşmesi` (3), `## Çıktı` (3). Şablon bunları taşır.
**Yorum:** 22 becerinin 2'si (`data-analysis-deep-scan`, `forex-trading-expert`)
İngilizce ve TR sözleşmesini taşımıyor; bu yüzden sözleşme ihlali HATA değil
UYARI seviyesindedir — mevcut depoyu tek koşuda "hatalı" ilan etmek gerçeği
değil eşiği değiştirmek olurdu.

---

## 3. DEPO EKİ KURALLARI (KAYNAKTA YOK — ETİKETLİ)

Bunların hiçbiri kaynakta yoktur. Motor çıktısında `DEPO EKI` etiketiyle,
`KURAL_KAYNAGI` sözlüğünde (`scripts/beceri_dogrula.py:86-112`) açık atıfla
basılırlar.

| Kod | Kural | Neden eklendi | Seviye |
|---|---|---|---|
| **D1** `AYRISMA_IKI_NOKTA` | `description` düz YAML skaleri içinde `": "` geçemez | YAML'da `description: Motor: x.py` satırı *mapping values are not allowed in this context* hatası verir → frontmatter ayrışmaz → beceri **hiç yüklenmez**. Bu depoda gerçekten yaşandı (görev tanımı). Motor, YAML ayrıştırma hatası anında ham metni tarar (`scripts/beceri_dogrula.py:164-183`) ve **katlanmış blok (`>-`) önerir**. | HATA |
| **D2** `NAME_DIZIN_UYUSMAZ` | `name` = dizin adı | Kaynak yalnız "use them unchanged" der (`SKILL.md:439`, KANIT #37) — **eşitlik şartı koymaz**. Bu depoda 22/22 eşit; sözleşme ölçümden geldi. `[VARSAYIM]`: eşitsizliğin beceriyi bozduğu **kaynaktan kanıtlanamadı**; kural depo tutarlılığı gerekçesiyle konuldu. | HATA |
| **D3** `MOTOR_OZTEST_YOK` | `scripts/` varsa en az bir motor `--self-test` taşır ya da `scripts/self_test.py` bulunur | Depo yönergesi: "denetlenemeyen GEÇTİ sayılmaz". İki gelenek de kabul edilir çünkü depoda ikisi de yaşıyor: mevcut 22 becerinin 18'inde `scripts/` var; bunların **8'i** `--self-test` bayraklı, **10'u** ayrı `scripts/self_test.py` taşıyor — **ikisi de olmayan 0**. Tek gelenek dayatsaydık 8 ya da 10 beceri haksız yere ihlal sayılırdı. | HATA |
| **D4** `TETIKLEYICI_SOZLESME` | description depo tetikleyici ifadesini + "Tetikleyici" listesini taşır | §2'de ölçülen 20/22 ve 19/22 oranı. Kaynağın "pushy" öğüdünün (KANIT #29) bu depodaki somut biçimi. | UYARI |
| **D5** `KATLANMIS_BLOK_ONER` | 200 karakterden uzun description katlanmış blokla yazılır | §2'de ölçülen 21/22. D1'in **önleyicisi**: katlanmış blok kullanılırsa `": "` sorunu hiç doğmaz. | UYARI |

---

## 4. TAŞINMAYAN KURALLAR VE SAPMALAR

### 1) Resmî şartname — **VERİ YOK**

`spec/agent-skills-spec.md` 3 satırdır ve içeriği yoktur (KANIT #42).
`https://agentskills.io/specification` **iki ayrı yolla** denendi:

- `WebFetch` → `The server returned HTTP 403 Forbidden.`
- `curl` → `curl: (56) CONNECT tunnel failed, response 403`

**Erişilemedi.** Bu yüzden **yapmadığım şey:** şartname metnini yazmadım,
şartnameden alıntı yapmadım, "spec şöyle der" demedim. `quick_validate.py`
yorumlarındaki "(max 64 characters per spec)" ve "(max 1024 characters per
spec)" ifadeleri **kaynağın iddiasıdır**; bağımsız olarak doğrulanmamıştır.
Motor bu sayıları şartnameye değil **koda** atfeder.

### 2) `>+` / `|+` göstergeleri — SAPMA (genişletme)

`utils.py:35` yalnız `(">", "|", ">-", "|-")` tanır. Bizim
`_duz_skaler_iki_nokta` bunlara `">+"` ve `"|+"` ekler
(`scripts/beceri_dogrula.py:174`). Gerekçe: YAML'da geçerli "keep" chomping
göstergeleridir ve bunlar da düz skaler DEĞİLDİR; kaynağın listesini
kullansaydık `description: >+` yazan bir beceri **yanlışlıkla** D1 ihlali
sayılırdı (yanlış pozitif). Kaynaktan **ayrılmıştır**, etiketlenmiştir.

### 3) Taşınmayan kaynak kuralları (gerekçeleriyle)

| Kaynak kuralı | Yer | Neden taşınmadı |
|---|---|---|
| Eval/benchmark döngüsü (test prompt, subagent koşusu, `grading.json`, `benchmark.json`) | `skill-creator/SKILL.md:141-329` | `claude -p`, subagent ve viewer gerektirir; bu görev kapsamı dışıdır ve **koşulmadı**. Koşmadığım bir şeyi "uygulandı" diye yazmak memnun etme olurdu. |
| Description optimizasyon döngüsü (`run_loop.py`, 20 tetikleyici sorgu, %60/%40 train-test) | `skill-creator/SKILL.md:333-404` | Aynı gerekçe: `claude -p` gerekir, ağa/modele çıkar. Kuralın **statik kısmı** (100-200 kelime, 1024 sınırı) taşındı (#22); dinamik ölçüm taşınmadı. |
| `eval-viewer/generate_review.py`, `agents/grader.md`, `agents/comparator.md`, `agents/analyzer.md`, `references/schemas.md` | `skill-creator/SKILL.md:459-468` | Bu dosyalar **kaynak kökünde bulunmadı / okunmadı**; okumadığım dosyaya atıf yapmam. |
| `.skill` paketleme (zip, `EXCLUDE_DIRS`, `ROOT_EXCLUDE_DIRS`) | `package_skill.py:20-101` | Bu depo becerileri dizin olarak taşır, `.skill` paketi üretmez. Paketleyicinin **doğrulama kapısı** deseni alındı (#39, #40), zip mekaniği alınmadı. |
| "Principle of Lack of Surprise" (kötü amaçlı beceri yasağı) | `skill-creator/SKILL.md:113` | Mekanikleştirilemez (kod, bir becerinin niyetinin zararlı olup olmadığını ölçemez). Elle disiplin olarak kalır; sahte-otorite bir denetçiye devredilmedi. |
| Claude.ai / Cowork'e özgü talimatlar | `skill-creator/SKILL.md:420-455` | Ortam koşullu; bu depo Claude Code ortamındadır. |
| `license`, `metadata`, `allowed-tools` alanlarının **içeriğinin** doğrulanması | `quick_validate.py:42` | Kaynak da içeriklerini doğrulamaz — yalnız izinli anahtar listesinde tutar. Aynısı yapıldı; fazlası uydurma olurdu. |

**Sayısal özet:** `quick_validate.py`'nin **17 denetiminin 17'si** taşındı
(%100). `improve_description.py`'den **1 sert + 3 yazım kuralı** taşındı;
LLM çağıran `_call_claude` yolu taşınmadı. `skill-creator/SKILL.md`'den
**şablon/yazım disiplini** taşındı, **eval/benchmark/optimizasyon döngüsü
taşınmadı** (3 büyük bölüm, yukarıda gerekçeli).

### 4) Bilinçli kapsam sapması

Bu beceri **anlam** denetlemez: bir description'ın gerçekten doğru tetikleyip
tetiklemediği ölçülmez. O ölçüm kaynağın eval döngüsüdür ve burada
**koşulmamıştır** — dolayısıyla "description kalitesi doğrulandı" **denmez**.

---

## 5. DEPODAKİ 22 BECERİYE KARŞI GERÇEK KOŞU (salt-okunur)

`--depo .` kipi 23 dizini (22 mevcut + bu beceri) denetledi.
**Hiçbir dosya değiştirilmedi** — bulunan kusurlar RAPORLANDI, DÜZELTİLMEDİ.
Motor yalnız `SKILL.md` ve `scripts/*.py` **okur**; tek yazdığı yer
`--ornek-tazele` ile verilen hedef dizindir.

### 5a. İLK KOŞU — 2026-07-29T00:20Z (`ornek/depo_denetim_ilk_kosu_00-20Z.txt`)

| Beceri | Kod | Bulgu |
|---|---|---|
| `grafik-cizim` | `DESC_COK_UZUN` (HATA) | description **1338** karakter, sınır 1024 |
| `dogrulama-zinciri` | `DESC_COK_UZUN` (HATA) | description **1276** karakter |
| `grafik-calisma` | `DESC_COK_UZUN` (HATA) | description **1243** karakter |
| `rubrik-kapisi` | `DESC_COK_UZUN` (HATA) | description **1233** karakter |
| `sema-dogrulama` | `DESC_ACI_PARANTEZ` (HATA) | description `"INVALID: <mesaj> at <yol>"` içeriyor — `<` ve `>` yasak (`quick_validate.py:80-81`) |
| `sorusturma` | `BEKLENMEYEN_ANAHTAR` (HATA) | frontmatter'da `argument-hint` var; izinli 6 anahtarda yok (`quick_validate.py:42`) |
| `data-analysis-deep-scan` | `TETIKLEYICI_SOZLESME` + `KATLANMIS_BLOK_ONER` (UYARI) | İngilizce beceri; TR sözleşmesini ve katlanmış bloğu taşımıyor |
| `forex-trading-expert` | `TETIKLEYICI_SOZLESME` (UYARI) | İngilizce beceri; TR tetikleyici ifadesi yok |

**TOPLAM: 23 beceri, 6 HATA, 3 UYARI, çıkış kodu 1 (fail-closed).**

### 5b. İKİNCİ KOŞU — 2026-07-29T00:24Z (`ornek/depo_denetim.txt` / `.json`)

İki koşu arasında **başka bir oturum** üç beceriyi düzeltti
(`git status`: `M dogrulama-zinciri/SKILL.md`, `M rubrik-kapisi/SKILL.md`,
`M sema-dogrulama/SKILL.md`). **Bu düzeltmeleri BEN yapmadım** — bu beceri
yalnız `.claude/skills/dokuman-uretimi/` altına yazdı. Kalan kusurlar:

| Beceri | Kod | Bulgu |
|---|---|---|
| `grafik-cizim` | `DESC_COK_UZUN` (HATA) | description hâlâ 1024'ün üstünde |
| `grafik-calisma` | `DESC_COK_UZUN` (HATA) | description hâlâ 1024'ün üstünde |
| `sorusturma` | `BEKLENMEYEN_ANAHTAR` (HATA) | `argument-hint` |
| `data-analysis-deep-scan` | `TETIKLEYICI_SOZLESME` + `KATLANMIS_BLOK_ONER` (UYARI) | değişmedi |
| `forex-trading-expert` | `TETIKLEYICI_SOZLESME` (UYARI) | değişmedi |

**TOPLAM: 23 beceri, 3 HATA, 3 UYARI, çıkış kodu 1 (fail-closed).**

İki snapshot da saklandı; düşen HATA sayısı gizlenmedi ve **bana mal
edilmedi**. Depo eşzamanlı değiştiği için bu sayılar **o anın ölçümüdür**;
güncel hüküm için motor yeniden koşulmalıdır.

**Yorum (gerçek değil, yorum):** 4 uzun description muhtemelen sessizce
büyümüştür — bu tam olarak bu becerinin var olma gerekçesidir. `sema-dogrulama`
ihlali ironiktir: şema doğrulayan beceri, kendi manifestinde yasaklı karakter
taşıyor. `sorusturma`'nın `argument-hint` alanı için burada "kaynak-ortam ayrışması
olabilir, kesin hüküm için şartname gerekir" denmişti. **ÇÖZÜLDÜ — şartmaneye
gerek kalmadan, artefaktla:** `argument-hint`, resmî Anthropic deposu
`defending-code-reference-harness`'ta en az 6 becerinin frontmatter'ında
kullanılıyor (`triage/SKILL.md:10`, `threat-model/SKILL.md:13`,
`vuln-scan/SKILL.md:11`, `dnr-respond/SKILL.md:10`, `quickstart/SKILL.md:10`,
`patch/SKILL.md:11`). Yani `quick_validate.py:42` listesi `anthropics/skills`
YAYIN doğrulayıcısının dar kümesidir, Claude Code'un ÇALIŞMA ZAMANI kuralı
değildir. `sorusturma` bulgusu bu yüzden **YANLIŞ POZİTİFTİ**.

Motorda kaynak listesi DARALTILMADI, kanıtla GENİŞLETİLDİ:
`KAYNAK_ALLOWED_PROPERTIES` (6 anahtar, kaynaktan birebir) ve
`DEPO_EK_PROPERTIES = {"argument-hint", "tools"}` ayrı sabitlerde tutulur;
ikisinin birleşimi uygulanır (`beceri_dogrula.py:47-70`). Böylece hangi
anahtarın kaynaktan hangisinin depo ekinden geldiği kodda görünür kalır.
`tools` alanının dayanağı: `cwc-long-running-agents/.../evaluator.md:4`.

⚠️ Bu bir eşik gevşetmesi DEĞİLDİR: kural "geçsin diye" değiştirilmedi,
kaynağın kapsamı yanlış uygulandığı için kanıtla düzeltildi. Aynı koşuda
`grafik-calisma`/`grafik-cizim` HATA'ları GEVŞETİLMEDİ ve duruyor.

---

## 6. KENDİNİ MUAF TUTMAMA

`SKILL.md` kendi doğrulayıcısından geçer: **0 HATA, 0 UYARI**
(description 929 karakter / 113 kelime; gövde 146 satır — üçü de sınır altında).
Bu, öz-testin **ayrı bir vakasıdır** (`scripts/beceri_dogrula.py:663-679`):
kendi `SKILL.md` HATA verirse öz-test **düşer**.

Öz-test: **20 vaka, 20 geçti, 0 düştü, exit 0** (`ornek/self_test_cikti.txt`).
Öz-test `tempfile.mkdtemp()` içinde sahte beceri ağacı kurar ve `finally`
bloğunda siler; **takipli hiçbir dosyaya yazmaz**. `ornek/` çıktılarını
tazelemek AYRI bayraktır: `--ornek-tazele`.

**Dairesellik uyarısı:** öz-testin "geçti" demesi, kuralların kaynağa
uygunluğunu KANITLAMAZ — yalnız motorun kendi kurallarını uyguladığını
gösterir. Kaynağa uygunluğun kanıtı §1 tablosudur ve **elle** doğrulanır.
