# KANIT — butunluk-denetimi

Kaynak izlenebilirliği. Her satır, kaynaktan **kopyala-yapıştır** alıntıyla bu
depodaki uygulamaya bağlanır.

## Doğrulanan kaynaklar

| Kaynak | Satır | sha256 (baş) | Durum |
|--------|-------|--------------|-------|
| `fs/scripts/check.py` | 219 | `c19d681ddba4` | ✅ birebir doğrulandı (`wc -l` + `sha256sum`) |
| `fs/scripts/validate.py` | 42 | `4094e34f8431` | ✅ birebir doğrulandı |
| `fs/scripts/orchestrate.py` | 89 | `d561f9bb62bf` | ✅ birebir doğrulandı |
| `a-skills/.../skill-creator/scripts/quick_validate.py` | — | — | ✅ okundu (1-95) |
| `a-skills/.../skill-creator/scripts/improve_description.py` | — | — | ✅ okundu (132, 155-180) |

---

## Taşınan kurallar

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|--------------------|--------------------------|-------------------|----------|
| 1 | `check.py:6` | `1. Every *.yaml under managed-agents/ parses.` | `scripts/butunluk.py` `denet_veri_dosyalari` | BİREBİR alıntı. Kural taşındı, ağaç değişti: `managed-agents/` yerine `.claude/` altındaki tüm `*.yaml`/`*.yml` `yaml.safe_load` ile ayrıştırılır. |
| 2 | `check.py:7` | `2. Every plugin.json / marketplace.json / steering-examples.json parses.` | `scripts/butunluk.py` `denet_veri_dosyalari` + `denet_settings` | BİREBİR alıntı. Dosya adları bu depoya çevrildi: `.claude/settings.json` + `.claude/**/*.json`. |
| 3 | `check.py:8` | `3. Every <vertical>/agents/*.md has valid YAML frontmatter with name + description.` | `scripts/butunluk.py` `denet_ajanlar` | BİREBİR alıntı. `.claude/agents/*.md` üzerinde aynı kural (`name` + `description` zorunlu). |
| 4 | `check.py:9-10` | `4. Every system.file, skills[].path, callable_agents[].manifest in agent.yaml` / `and subagent yamls resolves to an existing file/dir.` | `scripts/butunluk.py` `denet_referanslar` | **BİRLEŞTİRİLMİŞ** — kaynakta iki satıra bölünmüş tek cümle, tek alıntıda toplandı. Yapılandırılmış YAML alanı yerine SKILL.md gövdesindeki dosya tokenleri çözümlenir (bu depoda `agent.yaml` yok). |
| 5 | `check.py:11` | `5. Every managed-agents/<slug>/ has agent.yaml, README.md, steering-examples.json.` | `scripts/butunluk.py` `ZORUNLU_BECERI_DOSYALARI` | BİREBİR alıntı. "dizin başına zorunlu dosya listesi" kuralı korundu; liste bu depoya çevrildi: `("SKILL.md", "KANIT.md")`. |
| 6 | `check.py:13` | `Exit 0 if clean, 1 otherwise. Requires: pyyaml.` | `scripts/butunluk.py` `cikis_kodu` + bağımlılık kapısı | BİREBİR alıntı. 0/1 korundu; 2 (DENETLENEMEDİ) ve 3 (bağımlılık) eklendi — bkz. sapma S1. |
| 7 | `check.py:95-96` | `if not text.startswith("---"):` / `err(f"frontmatter: {rel(md)}: missing leading ---")` | `scripts/butunluk.py` `_frontmatter` | **BİRLEŞTİRİLMİŞ** — iki ardışık satır tek alıntıda. Aynı kontrol: `if not metin.startswith("---")`. |
| 8 | `check.py:99` | `        _, fm, _ = text.split("---", 2)` | `scripts/butunluk.py` `_frontmatter` | BİREBİR alıntı (baştaki girinti dahil). Aynı ayrıştırma deseni + `ValueError` yakalama. |
| 9 | `check.py:101-103` | `for k in ("name", "description"):` / `if k not in meta:` / `err(f"frontmatter: {rel(md)}: missing '{k}'")` | `scripts/butunluk.py` `denet_beceriler`, `denet_ajanlar` | **BİRLEŞTİRİLMİŞ** — üç ardışık satır. Aynı döngü, aynı iki alan. |
| 10 | `check.py:64-65` | `def rel(p: Path) -> str:` / `    return str(p.relative_to(ROOT))` | `scripts/butunluk.py` `Denetci.rel` | **BİRLEŞTİRİLMİŞ** — iki satırlık fonksiyon. Depo köküne göreli yol; `ValueError` durumunda mutlak yola düşer (kaynakta bu koruma yok). |
| 11 | `check.py:196` | `    if any(part in {".git", "node_modules"} for part in ps.parts):` | `scripts/butunluk.py` `ATLA_DIZIN` + `_taranacak` | BİREBİR alıntı. Aynı "tarama dışı dizin" fikri; küme genişletildi: `__pycache__`, `.venv`, `venv`. |
| 12 | `check.py:189-193` | `# Windows PowerShell 5.1 -- still the default shell on managed Windows -- reads` / `# a .ps1 with no BOM using the machine's ANSI code page, not UTF-8.` | `scripts/butunluk.py` `_oku` | **BİRLEŞTİRİLMİŞ** — yorum bloğundan iki satır. **SAPMA S2:** kural fikri (kodlama kapısı) taşındı, kriteri değişti — bkz. sapma S2. |
| 13 | `check.py:200-201` | `if raw.startswith(b"\xef\xbb\xbf"):` / `continue  # an explicit BOM tells PS 5.1 it is UTF-8; then non-ASCII is fine` | `scripts/butunluk.py` `_oku` | **BİRLEŞTİRİLMİŞ** — iki satır. BOM tespiti aynı bayt dizisiyle; ancak burada BOM **kabul değil, HATA**dır (Markdown frontmatter'ı bozar). |
| 14 | `check.py:214-215` | `if errors:` / `print(f"FAIL — {len(errors)} issue(s) across {checked} file(s):\n", file=sys.stderr)` | `scripts/butunluk.py` `rapor_metin` | **BİRLEŞTİRİLMİŞ** — iki satır. Rapor cümlesi Türkçeleştirildi: `DUSTU — N hata, M denetlenemedi, ...; K denetim yapildi.` |
| 15 | `check.py:219` | `print(f"OK — {checked} file(s) checked, 0 issues.")` | `scripts/butunluk.py` `rapor_metin` | BİREBİR alıntı. Karşılığı: `TAMAM — {d.denetlenen} denetim yapildi, 0 hata, ...`. |
| 16 | `check.py:23` | `errors: list[str] = []` | `scripts/butunluk.py` `Denetci.bulgular` | BİREBİR alıntı. Düz metin listesi yerine seviyeli sözlük listesi (HATA/DENETLENEMEDİ/BİLGİ). |
| 17 | `check.py:24` | `checked = 0` | `scripts/butunluk.py` `Denetci.denetlenen` | BİREBİR alıntı. Aynı "kaç denetim yapıldı" sayacı. |
| 18 | `check.py:53-57` | `try:` / `    import yaml` / `except ImportError:` / `    print("ERROR: requires pyyaml (pip install pyyaml)", file=sys.stderr)` | `scripts/butunluk.py` bağımlılık kapısı | **BİRLEŞTİRİLMİŞ** — dört satır. Aynı desen; çıkış kodu 2 yerine 3 (bkz. sapma S1). |
| 19 | `check.py:74-75` | `except yaml.YAMLError as e:` / `err(f"YAML parse: {rel(yml)}: {e}")` | `scripts/butunluk.py` `denet_veri_dosyalari` | **BİRLEŞTİRİLMİŞ** — iki satır. Aynı istisna türü, aynı mesaj biçimi. |
| 20 | `check.py:88-89` | `except json.JSONDecodeError as e:` / `err(f"JSON parse: {rel(jf)}: {e}")` | `scripts/butunluk.py` `denet_settings`, `denet_veri_dosyalari` | **BİRLEŞTİRİLMİŞ** — iki satır. Aynı istisna, aynı mesaj biçimi. |
| 21 | `check.py:104` | `    except (ValueError, yaml.YAMLError) as e:` | `scripts/butunluk.py` `_frontmatter` | BİREBİR alıntı. Aynı ikili istisna yakalama (bölünemeyen frontmatter + bozuk YAML). |
| 22 | `check.py:161` | `# --- 4b2. agent.md skill references exist in the agent's own bundle --------` | `scripts/butunluk.py` `denet_referanslar` | BİREBİR alıntı. "Düz metin içindeki referans gerçekten var mı" fikri; kaynak backtick'li beceri adına bakar, biz dosya yoluna bakarız. |
| 23 | `quick_validate.py:82` | `        # Check description length (max 1024 characters per spec)` | `scripts/butunluk.py` `AZAMI_ACIKLAMA = 1024` | BİREBİR alıntı (girinti dahil). 1024 eşiği **uydurma değil**, kaynağa bağlı. |
| 24 | `quick_validate.py:83` | `        if len(description) > 1024:` | `scripts/butunluk.py` `denet_beceriler` | BİREBİR alıntı. Karşılığı: `if n > AZAMI_ACIKLAMA`. Kesin **kesin büyüktür** (1024 tam değeri GEÇER) — öz-test "description tam 1024 (sinir)" vakası bunu sınar. |
| 25 | `improve_description.py:132` | `There is a hard limit of 1024 characters — descriptions over that will be truncated, so stay comfortably under it.` | `scripts/butunluk.py` `AZAMI_ACIKLAMA` yorumu + hata mesajı | BİREBİR alıntı (cümlenin ilgili parçası; satırın tamamı daha uzundur). Hata mesajındaki "asan kisim kirpilir" bu cümleden gelir. |
| 26 | `quick_validate.py:69` | `        # Check name length (max 64 characters per spec)` | `scripts/butunluk.py` `AZAMI_AD = 64` | BİREBİR alıntı. |
| 27 | `quick_validate.py:65` | `        if not re.match(r'^[a-z0-9-]+$', name):` | `scripts/butunluk.py` `AD_DESENI` | BİREBİR alıntı. Aynı kebab-case regex'i. |
| 28 | `quick_validate.py:80` | `        if '<' in description or '>' in description:` | `scripts/butunluk.py` `denet_beceriler` | BİREBİR alıntı. Aynı açı-parantez yasağı (`ACIKLAMA_ACI_PARANTEZ`). |
| 29 | `quick_validate.py:17-19` | `    skill_md = skill_path / 'SKILL.md'` / `    if not skill_md.exists():` / `        return False, "SKILL.md not found"` | `scripts/butunluk.py` `ZORUNLU_BECERI_DOSYALARI` | **BİRLEŞTİRİLMİŞ** — üç satır. `SKILL.md` yoksa `EKSIK_DOSYA`. |
| 30 | `quick_validate.py:36-37` | `        if not isinstance(frontmatter, dict):` / `            return False, "Frontmatter must be a YAML dictionary"` | `scripts/butunluk.py` `_frontmatter` | **BİRLEŞTİRİLMİŞ** — iki satır. Karşılığı: `"frontmatter bir YAML sozlugu degil"`. |
| 31 | `validate.py:5` | `Exits 0 on valid, 1 on invalid (message to stderr).` | `scripts/butunluk.py` `cikis_kodu` | BİREBİR alıntı. Aynı çıkış sözleşmesi (genişletildi, S1). |
| 32 | `orchestrate.py:23` | `ALLOWED_TARGETS = {` | `scripts/butunluk.py` `OZTEST_YASAK` | BİREBİR alıntı. Fikir tersine çevrildi: allowlist yerine **denylist** (koşulması yasak motorlar). Gerekçe aşağıda. |

**Taşınan kural sayısı: 32.**

---

## Taşınmayan kurallar (gerekçeli)

| # | Kaynak | Alıntı | Neden taşınmadı |
|---|--------|--------|-----------------|
| A | `check.py:27` + `check.py:41` | `def ensure_hooks_installed() -> None:` / `                ["git", "-C", str(ROOT), "config", "core.hooksPath", want],` (**BİRLEŞTİRİLMİŞ** — bitişik olmayan iki satır) | **Yan etki yasağı.** Bu, denetim aracının depo git yapılandırmasını **değiştirmesidir**. Görev kısıtı: "SADECE `.claude/skills/butunluk-denetimi/` altına yaz." Bir denetleyici denetlediği şeyi değiştiremez. |
| B | `check.py:173-178` | `# --- 4c. marketplace source paths resolve ----------------------------------` | Bu depoda `marketplace.json` / eklenti pazarı **yok**. Karşılığı olmayan kural uydurulmadı. |
| C | `check.py:142-159` | `# --- 4b. agent-plugin bundled skills match vertical source -----------------` (`filecmp.dircmp`) | Bu depoda beceriler **kopyalanmıyor**; tek nüsha `.claude/skills/` altında. Kopya-drift kuralının denetleyecek nesnesi yok. Kısmî karşılığı #22'de (referans çözümleme) yaşar. |
| D | `check.py:188-211` | `ASCII_ONLY_SUFFIXES = {".ps1", ".psm1", ".psd1"}` | Bu depoda PowerShell dosyası yok ve içerik **Türkçe** (zorunlu olarak ASCII dışı). ASCII-only kuralı burada her dosyayı düşürürdü. Fikir taşındı, kriter değişti — sapma S2. |
| E | `validate.py:15` | `import jsonschema` | **`jsonschema` bu depoda KURULU DEĞİL** (görev kısıtı). Şema doğrulaması zaten `sema-dogrulama` becerisinde stdlib ile ayrıca çözülmüş. |
| F | `orchestrate.py:64-82` | `def run(source_session_id: str, agent_ids: dict[str, str]) -> None:` | `anthropic` SDK + canlı oturum akışı gerektirir. Bu araç **ağa çıkmaz**; yapısal denetim çevrimdışıdır. |
| G | `quick_validate.py:42` | `ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}` | Bu depodaki mevcut beceriler `argument-hint` gibi bu kümede olmayan anahtarlar kullanıyor (ör. `sorusturma/SKILL.md`). Kuralı HATA olarak uygulamak **21 becerinin çoğunu yanlış yere düşürürdü**; kaynak listesi bu deponun geleneğini yansıtmıyor. Bilerek atlandı. |

**Taşınmayan kural sayısı: 7.**

---

## Sapmalar

**S1 — Çıkış kodu genişletildi.**
Kaynak `check.py:13` yalnız `Exit 0 if clean, 1 otherwise` der ve `check.py:57`
bağımlılık eksikliğinde `sys.exit(2)` kullanır. Burada:
`0` temiz, `1` HATA, `2` **DENETLENEMEDİ**, `3` bağımlılık/kök yok.
Gerekçe: görev "fail-closed: denetlenemeyen şey GEÇTİ sayılmaz, DENETLENEMEDİ
olur ve çıkış kodunu etkiler" diyor. Kaynakta "denetlenemedi" kavramı yoktur —
bu bir **ekleme**dir, kaynağa yamanmamıştır.

**S2 — ASCII kapısı → UTF-8/BOM kapısı.**
Kaynak `check.py:194` `.ps1/.psm1/.psd1` için **saf ASCII** ister. Bu depo
Türkçedir; ASCII-only her dosyayı düşürürdü. Korunan fikir: *"bir dosya yanlış
kodlamayla okunursa sessizce ve tamamen bozulur, o yüzden burada kapıya al."*
Uygulanan kriter: dosya UTF-8 olarak çözülebiliyor mu + başında BOM var mı
(BOM, YAML frontmatter'ının `---` ile başlamasını bozar → `KODLAMA` hatası).

**S3 — `check_refs` yapılandırılmış alandan düz metne taşındı.**
Kaynak `check.py:116-136` `system.file`, `skills[].path`, `callable_agents[].manifest`
gibi **beyan edilmiş** alanları çözer. Bu depoda böyle bir manifest şeması yok;
referanslar SKILL.md **gövdesinde** düz metin olarak geçer. Bu yüzden regex ile
token çıkarılır. Bedeli: düz metinde geçen kaynak-deposu alıntıları da yakalanır.
Yanlış suçlama olmasın diye üç kova ayrıldı (HATA / koşu artefaktı / dış kaynak);
**dış kaynak GEÇTİ sayılmaz**, "doğrulanamadı" diye BİLGİ olarak listelenir.

**S4 — Öz-test denylist'i (`OZTEST_YASAK`).**
`piramit.py`, `self_test.py`, `saglik.py` koşturulmaz. Gerekçe görev kısıtı:
"piramit boru hattını KOŞTURMA … `engine/state/` ve `hafiza/` DEĞİŞTİRİLMEZ."
Bunlar `GEÇTİ` sayılmaz — `DENETLENEMEDİ` olarak raporlanır ve çıkış kodunu 2'ye
çeker. Sessiz atlama yoktur.

**S5 — İki öz-test geleneği birden kabul edilir.**
Depoda hem `motor.py --self-test` (yeni beceriler) hem ayrı `scripts/self_test.py`
(eski beceriler) yaşıyor — ölçüldü, varsayılmadı. Yalnız `--self-test` bayrağı
aransaydı 10+ eski beceri haksız yere düşerdi.

**S6 — Kanca `+x` kuralı çağrı biçimine bağlıdır.**
`.claude/settings.json` kancaları iki biçimde çağrılıyor: `bash "…/x.sh"`
(yorumlayıcı) ve `"…/session-start.sh"` (doğrudan). `+x` yalnız **doğrudan**
çağrıda zorunludur. Bu ayrım yapılmasaydı `piramit_auto.py` (`python3 …` ile
çağrılıyor, `+x` yok) yanlış yere HATA verirdi — ölçülerek doğrulandı.

---

## [VARSAYIM] etiketleri

| Etiket | Nerede | Ne varsayıldı | Neden kaynağa bağlanamadı |
|--------|--------|---------------|---------------------------|
| `[VARSAYIM] KANIT.md zorunluluğu` | `butunluk.py` `ZORUNLU_BECERI_DOSYALARI` | Her becerinin `KANIT.md`'si olmalı | Bu, `check.py:184`'ün *biçimini* (dizin başına zorunlu dosya listesi) izler ama **dosya adı bu depoya özgüdür**; kaynakta `KANIT.md` geçmez. Depo kuralı olarak görev tanımından gelir, kaynak koddan değil. |
| `[VARSAYIM] koşu artefaktı deseni` | `butunluk.py` `KOSU_ARTEFAKTI` | `state/`, `girdi/`, `hafiza/` altındaki yollar koşuda üretilir | Ölçümle desteklendi (`engine/state/` var ama içindeki dosyalar depoda durmuyor), ancak kaynakta karşılığı yoktur. |
| `[VARSAYIM] 180 sn öz-test zaman aşımı` | `butunluk.py` `denet_oztestler` | Bir öz-test 180 sn'de bitmeli | Kaynakta zaman aşımı yok. Ölçülen en yavaş öz-test çok daha hızlıydı; sayı **seçilmiştir**, türetilmemiştir. Aşılırsa `DENETLENEMEDİ` (GEÇTİ değil). |
| `[VARSAYIM] denylist üyeliği` | `butunluk.py` `OZTEST_YASAK` | Bu üç dosya sicil değiştirir | `grep` ile `engine/state`/`piramit.py` referansları görüldü; **her dosya tek tek çalıştırılarak kanıtlanmadı** (çalıştırmak zaten yasak). Muhafazakâr taraf seçildi. |

---

## Dairesel doğrulama karşıtı not

`--self-test` aracın kendi depo çıktısını kanıt saymaz: her vaka için
`tempfile.mkdtemp` ile **sahte bir depo ağacı** kurulur, kasıtlı kusur eklenir
ve kusurun yakalandığı sınanır. Ayrıca bir **negatif kontrol** ("temiz ağaç")
vardır — araç her şeye HATA diyerek testi geçemez.

Bu negatif kontrol yazım sırasında aracın **kendi iki hatasını** yakaladı:
1. `py_compile.compile(..., cfile=os.devnull)` platformda yazamıyor → her Python
   dosyası sahte `DERLEME_KOSULAMADI` üretiyordu.
2. `py_compile.compile(..., doraise=True, quiet=2)` CPython'da istisnayı
   **hiç yükseltmez** (sessizce `return` eder) → bozuk Python dosyaları
   "derlendi" sanılıyordu. `quiet=1`'e çekildi.

İkisi de düzeltildi; `derlenmeyen Python` vakası artık gerçekten geçiyor.

## Kendini denetleme

Araç kendi becerisini muaf tutmaz. İlk gerçek koşuda **kendi** `SKILL.md`'sindeki
kopuk `scripts/self_test.py` referansını ve **kendi** eksik `KANIT.md`'sini
raporladı (bu dosya o bulgunun karşılığıdır).

## DÜZELTME — 1024 sınırı YANLIŞ SINIFLANDIRILMIŞTI (sonradan eklendi)

Bu belgenin ilk sürümü `1024`'ü **çalışma zamanı sert sınırı** gibi ele aldı ve
motor onu **HATA** olarak raporladı. **Bu yanlıştı.** Düzeltme, kaynağa yeniden
bakılarak değil, kaynağın KAPSAMI sınanarak yapıldı:

**Şüphenin çıkış noktası (dairesellik uyarısı):** aynı dosyanın
(`quick_validate.py:42`) `ALLOWED_PROPERTIES` kümesi `argument-hint`i dışlıyor,
oysa `argument-hint` resmî Anthropic becerilerinde (triage, threat-model,
vuln-scan, dnr-respond, quickstart, patch, dnr-hunt) kullanılıyor ve çalışıyor.
Yani bu dosya `anthropics/skills` **YAYIN** doğrulayıcısıdır, Claude Code'un
çalışma zamanı sözleşmesi değil. `1024`'ün de aynı kategoriden olup olmadığı
sınanmadan "sert sınır" sayılamazdı — sayılmıştı, hata buydu.

**Bağımsız kanıt (üç yoldan):**

| kanıt | yöntem | sonuç |
|---|---|---|
| `anthropics/claude-code` issue **#47627** | WebFetch ile açıldı, başlığı ve içeriği doğrulandı | Sürüm **2.1.105** beceri listeleme sınırını **250 → 1536** yükseltti ve kırpma için başlangıç uyarısı ekledi |
| `anthropics/claude-code` issue **#64606** | WebFetch ile açıldı, doğrulandı | `skillListingBudgetFraction = 0.01`; `200000 * 4 * 0.01 = 8000` — TOPLAM aşılırsa açıklamalar tek tek kırpılmaz, **tamamen düşürülür**, sessizce |
| 234 resmî/üçüncü-parti beceri | diskten ölçüldü | 1024'ü aşan **1** dosya (`a-skills/skills/claude-api/SKILL.md`, 1068) ve o da **kendi deposundaki doğrulayıcıyı geçmiyor** → kural CI'da uygulanmıyor. Medyan **284** karakter |

**Motordaki karşılığı — iki sınır ayrı sabitte, ayrı seviyede:**

| sabit | değer | seviye | kaynak |
|---|---|---|---|
| `YAYIN_ACIKLAMA` / `DESC_YAYIN_MAKS` | 1024 | **UYARI** | `quick_validate.py:83-84` (yayın sözleşmesi) |
| `CALISMA_ZAMANI_ACIKLAMA` / `DESC_MAKS` | 1536 | **HATA** | issue #47627 (gerçekten kırpar) |
| `TOPLAM_ACIKLAMA_BUTCESI` / `DESC_TOPLAM_BUTCE` | 8000 | **UYARI** | issue #64606 (toplam, sessiz düşürme) |

**Neden bütçe HATA değil UYARI:** sayı bir **hata bildiriminden** gelir,
şartnameden değil. HATA demek, ölçülmemiş bir kesinlik iddiası olurdu. Ölçülen
değer her koşuda raporlanır (aşılmasa da), böylece sessizce kaybolmaz.

**Öz-testte gerileme koruması:** 1024–1536 arası bir description için vaka
artık HEM `DESC_YAYIN_SINIRI`/`ACIKLAMA_YAYIN_SINIRI` uyarısının çıkmasını HEM
de eski HATA kodunun çıkmamasını sınar. Ayrıca toplam bütçe için, hiçbir
becerinin tek başına sınırı aşmadığı ama toplamın aştığı ayrı bir vaka var —
dosya dosya bakan bir denetimin göremeyeceği arıza türü budur.

**Ölçülen gerçek durum (bu depo):** toplam 19.964 karakter / bütçe 8.000 =
**%250**. Önceki 14 beceri tek başına 11.093 (%139) idi; bu oturumda eklenen 9
beceri 8.871 ekledi. Kullanıcı bu riski **bilerek kabul etti**; açıklamalar
kısaltılmadı, bulgu yalnız raporlanır.
