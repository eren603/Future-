# KANIT — eleme-motoru

Bu dosya, `eleme-motoru` becerisinin **kaynaktan** üretildiğini (hafızadan
değil) satır satır kanıtlar. Doğrulama kaynağa karşıdır; kendi çıktımızla
kendimizi doğrulamak dairesel olurdu.

**Okunan kaynak (TAM okundu, Read ile):**

| Dosya | Satır | SHA |
|---|---|---|
| `findings_filter.py` | 343 | `a18eb6a21120` |
| `claude_api_client.py` | 376 | `32b5ca67c3d2` |

**Üretilen dosyalar:**

| Dosya | Satır |
|---|---|
| `.claude/skills/eleme-motoru/SKILL.md` | — |
| `.claude/skills/eleme-motoru/emsaller/emsal_defteri.yaml` | 618 |
| `.claude/skills/eleme-motoru/scripts/eleme.py` | 783 |
| `.claude/skills/eleme-motoru/KANIT.md` | bu dosya |

---

## 1. SATIR SATIR KANIT TABLOSU

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|---|---|---|---|
| 1 | `findings_filter.py:16-17` | `class FilterStats:` / `"""Statistics about the filtering process."""` | `eleme.py:107` | `class ElemeIstatistigi` — aynı rol, Türkçe ad |
| 2 | `findings_filter.py:18` | `total_findings: int = 0` | `eleme.py:122` | `toplam_bulgu: int = 0` |
| 3 | `findings_filter.py:19` | `hard_excluded: int = 0` | `eleme.py:123` | `sert_elenen: int = 0` |
| 4 | `findings_filter.py:20` | `claude_excluded: int = 0` | `eleme.py:125` | `emsal_elenen: int = 0` (LLM aşaması → emsal defteri aşaması) |
| 5 | `findings_filter.py:21` | `kept_findings: int = 0` | `eleme.py:126` | `tutulan: int = 0` |
| 6 | `findings_filter.py:22` | `exclusion_breakdown: Dict[str, int] = field(default_factory=dict)` | `eleme.py:127` | `eleme_dagilimi: Dict[str, int]` |
| 7 | `findings_filter.py:23` | `confidence_scores: List[float] = field(default_factory=list)` | `eleme.py:128` | `guven_skorlari: List[float]` |
| 8 | `findings_filter.py:24` | `runtime_seconds: float = 0.0` | `eleme.py:129` | `sure_saniye: float = 0.0` |
| 9 | `findings_filter.py:27-28` | `class HardExclusionRules:` / `"""Hard exclusion rules for common false positives."""` | `eleme.py:157` | `class SertElemeKurallari` — "Yaygın yanlış-pozitifler için sert eleme kuralları" |
| 10 | `findings_filter.py:30` | `# Pre-compiled regex patterns for better performance` | `eleme.py:165,173,183,196,204` | 5 aile modül yüklenirken `re.compile` edilir |
| 11 | `findings_filter.py:31-35` | `_DOS_PATTERNS: List[Pattern] = [` … `r'\b(denial of service\|dos attack\|resource exhaustion)\b'` | `eleme.py:165-171` | `_GENEL_RISK_DESENLERI` — ölçülmemiş felaket/tükenme cümlesi |
| 12 | `findings_filter.py:38-43` | `_RATE_LIMITING_PATTERNS` … `r'\b(implement\|add)\s+rate\s+limit'` | `eleme.py:173-181` | `_GENEL_TAVSIYE_DESENLERI` — seviyesiz genel öğüt ("stop kullanılmalı") |
| 13 | `findings_filter.py:45-51` | `_RESOURCE_PATTERNS` … `r'\bunclosed\s+(resource\|file\|connection)'` | `eleme.py:183-194` | `_ISLETIM_DESENLERI` — işletim/bakım bulgusu |
| 14 | `findings_filter.py:53-57` | `_OPEN_REDIRECT_PATTERNS` … `r'\b(open redirect\|unvalidated redirect)\b'` | `eleme.py:196-202` | `_DUSUK_ETKI_DESENLERI` — düşük etkili / teorik mikro-yapı |
| 15 | `findings_filter.py:59-69` | `_MEMORY_SAFETY_PATTERNS` … `r'\b(memory safety\|memory corruption)\b'` | `eleme.py:275-283` | `_TUREV_DESENLERI` — **koşullu** aile (2. katman, bkz. #22) |
| 16 | `findings_filter.py:71-75` | `_REGEX_INJECTION` … `r'\b(regex\|regular expression)\s+injection\b'` | `eleme.py:204-210` | `_KAPSAM_DISI_DESENLERI` — "not applicable" ailesi = canlı/otomatik emir |
| 17 | `findings_filter.py:77-79` | `_SSRF_PATTERNS: List[Pattern] = [` `re.compile(r'\b(ssrf\|server\s+.?side\s+.?request\s+.?forgery)\b', re.IGNORECASE)` | `eleme.py:285-287` | `_SQUEEZE_DESENLERI` — tek desenli **koşullu** aile (bkz. #23) |
| 18 | `findings_filter.py:81-82` | `@classmethod` / `def get_exclusion_reason(cls, finding: Dict[str, Any]) -> Optional[str]:` | `eleme.py:216-217` | `SertElemeKurallari.eleme_gerekcesi(cls, bulgu) -> Optional[str]` — tek fonksiyon, gerekçe string'i döner |
| 19 | `findings_filter.py:91-94` | `# Check if finding is in a Markdown file` / `file_path = finding.get('file', '')` / `if file_path.lower().endswith('.md'):` / `return "Finding in Markdown documentation file"` | `eleme.py:223-226` | `kaynak.endswith((".md",".txt",".rst"))` → `"İddia belge/anlatı dosyasından (motor çıktısı değil)"` |
| 20 | `findings_filter.py:99-105` | `# Handle None values` / `if description is None:` … `combined_text = f"{title} {description}".lower()` | `eleme.py:231-242` | Aynı None yönetimi + `_kucult` (Türkçe `İ/I` güvenli küçültme) |
| 21 | `findings_filter.py:108-110` | `for pattern in cls._DOS_PATTERNS:` / `if pattern.search(combined_text):` / `return "Generic DOS/resource exhaustion finding (low signal)"` | `eleme.py:243-245` | Aynı döngü kalıbı; `"Genel felaket/tükenme iddiası (ölçüme bağlı değil, düşük sinyal)"` |
| 22 | `findings_filter.py:133-143` | `# Check memory safety patterns - exclude if NOT in C/C++ files` … `if file_ext not in c_cpp_extensions:` … `return "Memory safety finding in non-C/C++ code (not applicable)"` | `eleme.py:310-317` | **KAPI 1a**: türev iddiası `fiyat-yapisi`/`tarihsel-kanit` ailesinden ise elenir — `karar-motoru` türeve kördür (`engine/README.md`) |
| 23 | `findings_filter.py:145-152` | `# Check SSRF patterns - exclude if in HTML files only` … `if file_ext in html_extensions:` … `return "SSRF finding in HTML file (not applicable to client-side code)"` | `eleme.py:325-333` | **KAPI 2a**: squeeze/kaskad bayrağı `rejim.durum == "range"` ise elenir |
| 24 | `findings_filter.py:154` | `return None` | `eleme.py:262` / `eleme.py:355` | Eleme yoksa `None` (iddia geçer) |
| 25 | `findings_filter.py:197-199` | `def filter_findings(self,` `findings: List[Dict[str, Any]],` `pr_context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any], FilterStats]:` | `eleme.py:507-509` | `ElemeMotoru.ele(bulgular, baglam) -> Tuple[bool, Dict, ElemeIstatistigi]` — `pr_context` → `baglam` |
| 26 | `findings_filter.py:209` | `start_time = time.time()` | `eleme.py:513` | `t0 = time.time()` |
| 27 | `findings_filter.py:211-222` | `if not findings:` / `stats = FilterStats(total_findings=0, runtime_seconds=0.0)` | `eleme.py:518-525` | Boş girdi erken dönüşü, aynı sözleşme |
| 28 | `findings_filter.py:234-236` | `for i, finding in enumerate(findings):` / `exclusion_reason = HardExclusionRules.get_exclusion_reason(finding)` / `if exclusion_reason:` | `eleme.py:530-540` | Aynı döngü; katman etiketiyle |
| 29 | `findings_filter.py:237-242` | `excluded_hard.append({` `"finding": finding,` `"index": i,` `"exclusion_reason": exclusion_reason,` `"filter_stage": "hard_rules"` | `eleme.py:535-538` | `{"bulgu", "sira", "eleme_gerekcesi", "katman": "1-sert-kural"}` |
| 30 | `findings_filter.py:246-247` | `key = exclusion_reason.split('(')[0].strip()` / `stats.exclusion_breakdown[key] = stats.exclusion_breakdown.get(key, 0) + 1` | `eleme.py:502-505` | `_dagilim()` — aynı anahtar türetimi birebir |
| 31 | `findings_filter.py:271` | `confidence = analysis_result.get('confidence_score', 10.0)` | `eleme.py:458-478` | `guven_10()` — **sapma:** varsayılan 10.0 değil, fail-closed 0.0 (bkz. SAPMALAR) |
| 32 | `findings_filter.py:276` | `stats.confidence_scores.append(confidence)` | `eleme.py:553` | `ist.guven_skorlari.append(guven)` |
| 33 | `findings_filter.py:283` | `"exclusion_reason": exclusion_reason or f"Low confidence score: {confidence}",` | `eleme.py:430-431` | `f"Düşük güven skoru: {round(guven,2)} (1-3 bandı: gürültü)"` |
| 34 | `findings_filter.py:290-294` | `enriched_finding = finding.copy()` / `enriched_finding['_filter_metadata'] = {` `'confidence_score': confidence,` | `eleme.py:565-570` | `zengin["_eleme_verisi"] = {"guven_skoru", "gerekce", "aile"}` |
| 35 | `findings_filter.py:322` | `stats.runtime_seconds = time.time() - start_time` | `eleme.py:573` | `ist.sure_saniye = time.time() - t0` |
| 36 | `findings_filter.py:325-337` | `filtered_results = {` `"filtered_findings": …,` `"excluded_findings": …,` `"analysis_summary": {` … `"average_confidence": …` | `eleme.py:576-596` | `{"tutulan_bulgular","elenen_bulgular","ozet"{…,"ortalama_guven",…}}` |
| 37 | `claude_api_client.py:190` | `Your task is to filter out false positives and low-signal findings to reduce alert fatigue.` | `SKILL.md` "Neden var" | Becerinin var oluş gerekçesi — birebir aktarıldı |
| 38 | `claude_api_client.py:191` | `You must maintain high recall (don't miss real vulnerabilities) while improving precision.` | `eleme.py:566-571`, `SKILL.md` "Sınırlar" | Elenen iddia yok sayılmaz, gerekçesiyle raporlanır (recall koruması) |
| 39 | `claude_api_client.py:243` | `HARD EXCLUSIONS - Automatically exclude findings matching these patterns:` | `emsal_defteri.yaml:45-314` | 16 maddenin tamamı `SERT-01…SERT-16` olarak deftere alındı |
| 40 | `claude_api_client.py:261-265` | `SIGNAL QUALITY CRITERIA - For remaining findings, assess:` … `3. Are there specific code locations and reproduction steps?` | `eleme.py:440-447` (`guven_bandi_orta_sayisiz`), `emsal_defteri.yaml:490-510` | Somutluk şartı: orta güven bandında kanıtta sayısal dayanak yoksa elenir |
| 41 | `claude_api_client.py:267` | `PRECEDENTS - ` | `emsal_defteri.yaml:316-618` | 17 maddenin tamamı `EMSAL-01…EMSAL-17` olarak deftere alındı |
| 42 | `claude_api_client.py:292` | `Assign a confidence score from 1-10:` | `eleme.py:458-489` | `guven_10()` 1-10 ölçeği |
| 43 | `claude_api_client.py:293` | `- 1-3: Low confidence, likely false positive or noise` | `eleme.py:75`, `eleme.py:430` | `guven_dusuk_ust = 3.0` → bu bandın altı elenir |
| 44 | `claude_api_client.py:294` | `- 4-6: Medium confidence, needs investigation  ` | `eleme.py:76-77`, `eleme.py:441-446` | `guven_orta_alt/ust = 4.0/6.0` → EMSAL-11 somutluk şartı |
| 45 | `claude_api_client.py:295` | `- 7-10: High confidence, likely true vulnerability` | `eleme.py:565-571` | Bu bant koşulsuz tutulur (ek kapı yok) |

---

## 2. 33 MADDE İZLEME TABLOSU

Kaynaktaki **16 sert dışlama + 17 emsal**. Her madde tek tek ele alındı; hiçbiri
atlanmadı. `uygulanamaz` olanlar deftere gerekçesiyle YAZILDI (sessiz kayıp yok).

### 2.1 HARD EXCLUSIONS (`claude_api_client.py:244-259`)

| Madde | Kaynak satır | Durum | Defter kaydı | Nerede uygulanıyor |
|---|---|---|---|---|
| 1 DOS / resource exhaustion | :244 | **uygulandı** | `SERT-01` (yaml:45) | K1 `_GENEL_RISK_DESENLERI` (`eleme.py:165`) |
| 2 Secrets/credentials on disk | :245 | **uygulandı** | `SERT-02` (yaml:63) | K1 `_ISLETIM_DESENLERI` (`eleme.py:184`) |
| 3 Rate limiting / overload | :246 | **uygulandı** | `SERT-03` (yaml:79) | K1 `_GENEL_TAVSIYE_DESENLERI` (`eleme.py:174-176`) |
| 4 Memory/CPU exhaustion | :247 | **uygulandı** | `SERT-04` (yaml:95) | K1 `_ISLETIM_DESENLERI` (`eleme.py:185-186`) |
| 5 Input validation w/o proven impact | :248 | **uygulandı** | `SERT-05` (yaml:110) | K1 `_GENEL_TAVSIYE_DESENLERI` (`eleme.py:181`) |
| 6 GitHub action input sanitization | :249 | **uygulanamaz** | `SERT-06` (yaml:126) | — Gerekçe: bulgu = piyasa iddiası; CI/kanca yüzeyi yön iddiası üretmez. Ayrıca `.claude/hooks/` bu becerinin yetki alanı DIŞINDA |
| 7 Lack of hardening measures | :250 | **uygulandı** | `SERT-07` (yaml:141) | K1 `_GENEL_TAVSIYE_DESENLERI` (`eleme.py:180`) |
| 8 Theoretical race conditions | :251 | **uygulandı** | `SERT-08` (yaml:158) | K1 `_DUSUK_ETKI_DESENLERI` (`eleme.py:200`) |
| 9 Outdated third-party libraries | :252 | **uygulandı** | `SERT-09` (yaml:175) | K1 `_ISLETIM_DESENLERI` (`eleme.py:188`) + tazelik hükmü K2 KAPI 3 |
| 10 Memory safety impossible in rust | :253 | **uygulandı** | `SERT-10` (yaml:192) | K2 **KAPI 1a** aile kapısı (`eleme.py:310-317`) |
| 11 Files only used in tests | :254 | **uygulandı** | `SERT-11` (yaml:210) | K1 kaynak kapısı `_TEST_KAYNAK` (`eleme.py:213,227`) |
| 12 Log spoofing | :255 | **uygulandı** | `SERT-12` (yaml:226) | K1 `_ISLETIM_DESENLERI` (`eleme.py:192`) |
| 13 SSRF that only controls the path | :256 | **uygulandı** | `SERT-13` (yaml:243) | K2 **KAPI 2b** (`eleme.py:335-340`) |
| 14 User content in AI system prompts | :257 | **uygulandı** | `SERT-14` (yaml:260) | K3 emsal `kontrol.desen` (`eleme.py:433-452`) |
| 15 Unavailable dependency | :258 | **uygulandı** | `SERT-15` (yaml:280) | K1 `_ISLETIM_DESENLERI` (`eleme.py:189`) |
| 16 Crashes that are not vulnerabilities | :259 | **uygulandı** | `SERT-16` (yaml:296) | K1 `_ISLETIM_DESENLERI` (`eleme.py:190-191`) |

### 2.2 PRECEDENTS (`claude_api_client.py:268-284`)

| Madde | Kaynak satır | Durum | Defter kaydı | Nerede uygulanıyor |
|---|---|---|---|---|
| 1 Logging secrets / URLs / headers | :268 | **uygulandı** | `EMSAL-01` (yaml:316) | K3 `desen` + `istisna_desen` — sıradan log elenir, **etiketsiz gizli eşik TUTULUR** |
| 2 UUIDs unguessable | :269 | **uygulanamaz** | `EMSAL-02` (yaml:336) | — Gerekçe: hiçbir iddianın geçerliliği tanımlayıcı tahmin edilebilirliğine bağlı değil; zorlama analoji uydurma kural olurdu |
| 3 Audit logs not critical | :270 | **uygulanamaz (TERS)** | `EMSAL-03` (yaml:351) | — Gerekçe: bu depoda sicil/hesap-verme **KRİTİKTİR** (CLAUDE.md "HESAP VERME + KIYAS … atlanamaz"; `gozlemci.py` EKSIK_AKTARIM). Emsali taşımak sözleşmeyi çiğnerdi |
| 4 Env vars / CLI flags are trusted | :271 | **uygulandı** | `EMSAL-04` (yaml:367) | K3 `desen` + `kosul: kaynak_motor` (`eleme.py:434-437`) — motorun kendi kline'ından ölçtüğü değer güvenilir; elle okuma DEĞİL |
| 5 Resource management not valid | :272 | **uygulandı** | `EMSAL-05` (yaml:389) | K1 `_ISLETIM_DESENLERI` (SERT-04 ile aynı aile; kaynak da tekrar eder) |
| 6 Tabnabbing / XS-Leaks / open redirect | :273 | **uygulandı** | `EMSAL-06` (yaml:402) | K1 `_DUSUK_ETKI_DESENLERI` (`eleme.py:197-199`) |
| 7 Outdated third-party libraries (tekrar) | :274 | **uygulandı** | `EMSAL-07` (yaml:418) | SERT-09 ile aynı kural; tekrar gizlenmedi |
| 8 React secure unless dangerouslySetInnerHTML | :275 | **uygulandı** | `EMSAL-08` (yaml:433) | K3 `kosul: kaynak_motor` — motor seviyesine "uydurma" itirazı elenir; ELLE seviyeye itiraz geçerli (`rr_denetim`) |
| 9 GitHub action workflows | :276 | **uygulanamaz** | `EMSAL-09` (yaml:455) | — SERT-06 ile aynı yüzey (CI/kanca); iki maddeye iki farklı karşılık uydurmak sahte ayrım olurdu |
| 10 Client-side permission checks | :277 | **uygulandı** | `EMSAL-10` (yaml:469) | K3 `desen` — sunum katmanının kapı uygulamaması bulgu değil (CLAUDE.md "Grafik bir KARAR DEĞİLDİR") |
| 11 MEDIUM only if obvious and concrete | :278 | **uygulandı** | `EMSAL-11` (yaml:490) | K3 `kosul: guven_bandi_orta_sayisiz` (`eleme.py:441-446`) |
| 12 ipynb notebooks | :279 | **uygulandı** | `EMSAL-12` (yaml:511) | K1 kaynak kapısı (SERT-11 ile aynı yüzey: öz-test/kum havuzu) |
| 13 Logging non-PII | :280 | **uygulandı** | `EMSAL-13` (yaml:526) | K3 `desen` + `istisna_desen` — ara hesap elenir, **kaynaksız sayı TUTULUR** (`iddia_denetle.py`) |
| 14 Command injection in shell scripts | :281 | **uygulandı** | `EMSAL-14` (yaml:547) | K3 `desen` + `istisna_desen` — somut yol yoksa elenir (paket alımı SHA + gerileme korkuluğu) |
| 15 SSRF/path-traversal in client-side JS | :282 | **uygulandı** | `EMSAL-15` (yaml:568) | K2 **KAPI 1a + 1b** (SERT-10 ile aynı kapı; kaynak da bu mantığı iki kez kurar) |
| 16 Path traversal with ../ | :283 | **uygulanamaz** | `EMSAL-16` (yaml:585) | — Gerekçe: tamamen dosya-yolu semantiği; piyasa iddiası alanında karşılığı yok |
| 17 Injecting into log queries | :284 | **uygulandı** | `EMSAL-17` (yaml:599) | K3 `desen` + `istisna_desen` — kullanıcı anlatısının rapora karışması bulgu değil; KESİN kaynaksız sayı doğuruyorsa bulgu |

### 2.3 Sayım

| | Adet |
|---|---|
| Toplam madde | **33** |
| Uygulandı | **28** |
| Uygulanamaz (gerekçeli, deftere yazılı) | **5** — `SERT-06`, `EMSAL-02`, `EMSAL-03`, `EMSAL-09`, `EMSAL-16` |
| Defterde eksik | **0** |

---

## 3. SAPMALAR

Kaynağa göre bilinçli ayrılıklar. Hepsi ya alan çevirisinin ya da bu deponun
CLAUDE.md sözleşmesinin sonucudur.

### 3.1 Alan çevirisi (güvenlik → finans)

| Kaynak kavramı | Bu depodaki karşılığı | Dayanak |
|---|---|---|
| `finding` (güvenlik bulgusu) | danışman/motor **iddiası** | `karar-kurulu/scripts/sentez.py:8-13` danışman şeması (`name/stance/confidence/evidence`) |
| `finding['file']` | `bulgu['kaynak']` — iddiayı üreten motor dosyası | `piramit.py` motor kayıtları |
| `finding['title'] + ['description']` | `bulgu['baslik'] + ['evidence']` | `sentez.py` `evidence` alanı |
| `pr_context` | `baglam` = `{rejim, turev_kapsam, turev_faktorler, son_bar_utc}` | `smc_tespit.py:264-269` (`rejim.durum/adx/yuksek_vol`), `turev_akis.py:228,256-268` (`kapsam`, `faktorler`) |
| C/C++ dosya uzantısı kapısı | **motor ailesi** kapısı (`fiyat-yapisi` türev iddiası üretemez) | `gozlemci.py:46-54` AILE sözlüğü; `engine/README.md` kline-körlüğü |
| HTML dosya kapısı | **rejim** kapısı (`durum == "range"` → squeeze bayrağı geçersiz) | `smc_tespit.py:238-244` |
| — (kaynakta yok) | **tazelik** kapısı (damgasız/240 dk+ elle okuma = BAYAT) | `piramit.py:112-114` `zorunlu_damga_tolerans_dk`; CLAUDE.md "TAZELİK ZORUNLU" |
| Claude API eleme aşaması (LLM) | **emsal defteri** (33 madde, makine denetimi) | Bu ortamda API çağrısı yok; determinizm şart |

### 3.2 `FilterStats` → `ElemeIstatistigi` ad değişimi

7 alanın tamamı karşılandı (izleme tablosu #2-#8). Bir **ek alan** eklendi:

- `baglam_elenen: int` — kaynakta yoktur. Kaynakta bağlam kapıları
  `get_exclusion_reason` içindedir ve elemeleri `hard_excluded` sayacına yazılır.
  Burada 2. katman ayrı sayılır ki *hangi kapının* elediği görünsün. `sert_elenen`
  ve `emsal_elenen` anlamları değişmedi; `eleme_dagilimi` zaten gerekçe bazlıdır.

### 3.3 fail-OPEN → fail-CLOSED (davranış sapması)

| Kaynak | Bizde |
|---|---|
| `findings_filter.py:271` `confidence = analysis_result.get('confidence_score', 10.0)` | `confidence` yoksa **0.0** + uyarı (`eleme.py:461-467`) |
| `findings_filter.py:300-306` API hatasında `'confidence_score': 10.0,  # Default high confidence` → bulgu tutulur | Doğrulanmamış iddia `× refute_penalty (0.25)` ile cezalandırılır (`eleme.py:485-487`) |

Gerekçe: `sentez.py:74-76` — *"Eski davranış `get("confirmed", True)` idi: doğrulanmayan
görüş TAM ağırlık alıyordu — 'fail-closed' sözleşmesinin tersi."* Bu depo
fail-closed olmak zorundadır (CLAUDE.md). Kaynağın fail-OPEN varsayılanını
taşımak sözleşmeyi çiğnerdi.

### 3.4 Uygulanamayan 5 madde

`SERT-06`, `EMSAL-09` (CI/kanca yüzeyi — piyasa iddiası değil, `.claude/hooks/`
yetki alanı dışı), `EMSAL-02` (UUID tahmin edilemezliği — karşılığı yok),
`EMSAL-16` (dosya yolu semantiği — karşılığı yok), `EMSAL-03` (**ters yönde**:
bu depoda sicil/kıyas kritiktir). Beşi de deftere `uygulanamaz: true` +
gerekçesiyle yazıldı; hiçbiri sessizce atlanmadı.

### 3.5 Diğer küçük sapmalar

- **Katman ayrımı:** kaynakta sert kural + bağlam kapıları TEK fonksiyondadır
  (`get_exclusion_reason`). Burada görev tanımı gereği 1. ve 2. katman ayrıldı;
  semantik aynı, sıra aynı (bağlamsız kurallar önce).
- **Türkçe küçültme:** `str.lower()` Türkçe `İ` için birleşik nokta üretir;
  `_kucult()` (`eleme.py:97-99`) önce `İ→i`, `I→ı` eşler. Kaynakta
  `re.IGNORECASE` ile çözülen sorunun Türkçe karşılığı.
- **Kaynak kapısına `.txt/.rst` eklendi** (`.md` kapısının doğal genişlemesi:
  belge/anlatı dosyası) — kaynakta yalnız `.md` vardır.

---

## 4. DOĞRULAMA

`--self-test` gerçekten koşturuldu (`exit=0`). 16 vaka: 1 temiz motor iddiası,
1 temiz türev iddiası, 7 × katman-1 eleme, 4 × katman-2 kapı (aile / kapsam /
rejim / tazelik), 3 × katman-3 emsal.

```
$ python3 .claude/skills/eleme-motoru/scripts/eleme.py --self-test

  [OK ] V01 temiz motor iddiası
        beklenen=TUTULDU gerçek=TUTULDU
        gerekçe : 3 katmandan da geçti
  [OK ] V02 belge kaynağı (.md kapısı)
        gerekçe : İddia belge/anlatı dosyasından (motor çıktısı değil)
  [OK ] V03 genel felaket iddiası
        gerekçe : Genel felaket/tükenme iddiası (ölçüme bağlı değil, düşük sinyal)
  [OK ] V04 seviyesiz genel tavsiye
        gerekçe : Seviyesiz genel tavsiye (ölçülmüş seviye yok)
  [OK ] V05 işletim bulgusu
        gerekçe : İşletim/bakım bulgusu (yön sinyali değil)
  [OK ] V06 kapsam dışı (canlı emir)
        gerekçe : Kapsam dışı iddia (canlı/otomatik emir — bu depo yalnız karar-desteği)
  [OK ] V07 düşük etkili/teorik
        gerekçe : Düşük etkili / teorik mikro-yapı iddiası (ATR ölçeğinde anlamsız)
  [OK ] V08 türev iddiası, kapsam düşük (KAPI 1b)
        gerekçe : Türev yön iddiası, kapsam 0.3 < 0.5 (fail-closed: doğrulanmamış türev)
  [OK ] V09 türev iddiası fiyat-yapısı ailesinden (KAPI 1a)
        gerekçe : Türev iddiası 'fiyat-yapisi' ailesinden (grafik-calisma) — bu motor
                  türev kanallarına kördür (yapısal olarak üretemez)
  [OK ] V10 squeeze bayrağı RANGE rejiminde (KAPI 2a)
        gerekçe : Squeeze/kaskad bayrağı RANGE rejiminde (adx=14.2) — yönsel dayanağı yok
  [OK ] V11 bayat elle görsel okuma (KAPI 3)
        gerekçe : BAYAT elle okuma: son bardan 1440 dk eski (tolerans 240 dk)
  [OK ] V12 doğrulanmamış → düşük güven bandı
        gerekçe : Düşük güven skoru: 1.5 (1-3 bandı: gürültü)
  [OK ] V13 EMSAL-11 orta güven + sayısız kanıt
        gerekçe : EMSAL-11: Orta güven bandı (4-6) + kanıtta sayısal dayanak yok
  [OK ] V14 EMSAL-04 motor değerine 'manipüle edilebilir' itirazı
        gerekçe : EMSAL-04: Motorun kendi kline'ından ölçtüğü değer güvenilir taban sayılır
  [OK ] V15 temiz türev iddiası (kapsam yeterli)
        gerekçe : 3 katmandan da geçti
  [OK ] V16 test kaynağı
        gerekçe : Test/kum-havuzu kaynaklı iddia (gerçek koşu değil)

  16/16 vaka geçti

==========================================================================
TOPLU KOŞU (16 iddia birlikte, baglam=geniş)
==========================================================================
ElemeIstatistigi
  toplam_bulgu   : 16
  sert_elenen    : 7
  baglam_elenen  : 2   (EK ALAN — kaynakta yok)
  emsal_elenen   : 3
  tutulan        : 4
  sure_saniye    : 0.0005
  guven_skorlari : [7.0, 6.2, 6.6, 1.5, 5.5, 8.0, 7.1]  (ortalama=5.99)
  eleme_dagilimi :
        1 × BAYAT elle okuma: son bardan 1440 dk eski
        1 × Düşük etkili / teorik mikro-yapı iddiası
        1 × Düşük güven skoru: 1.5
        1 × EMSAL-04: Motorun kendi kline'ından ölçtüğü değer güvenilir taban sayılır
        1 × EMSAL-11: Orta güven bandı
        1 × Genel felaket/tükenme iddiası
        1 × Kapsam dışı iddia
        1 × Seviyesiz genel tavsiye
        1 × Test/kum-havuzu kaynaklı iddia
        1 × Türev iddiası 'fiyat-yapisi' ailesinden
        1 × İddia belge/anlatı dosyasından
        1 × İşletim/bakım bulgusu

  tutulan iddialar: ['karar-motoru', 'turev-akis', 'backtest-motoru', 'turev-akis']

  FilterStats 7 alan karşılığı: TAM

ÖZ-TEST GEÇTİ
```

**Bağlam duyarlılığının kanıtı:** V08 (türev iddiası) *dar* bağlamda
(`turev_kapsam=0.30`) ELENİR, *geniş* bağlamda (`0.85`) TUTULUR — toplu koşuda
`turev-akis` iki kez tutulanlar arasındadır. Aynı iddia, farklı bağlam, farklı
hüküm: filtre gerçekten bağlam-duyarlıdır, sabit değildir.

`--job` modu da koşturuldu: JSON iş dosyası → `tutulan_bulgular` /
`elenen_bulgular` / `ozet` / `istatistik` çıktısı üretildi.
