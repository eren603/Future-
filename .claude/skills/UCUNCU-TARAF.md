# Üçüncü taraf beceriler — kaynak ve lisans

Bu dizindeki becerilerin bir kısmı dış depolardan alınmıştır. Proje motorları
(`piramit-sistem`, `karar-motoru`, `grafik-calisma`, …) bu depoya aittir.

## obra/superpowers — 14 beceri
- Kaynak: https://github.com/obra/superpowers
- Lisans: MIT · `.claude-plugin/plugin.json` sürüm 6.2.0 · Yazar: Jesse Vincent
- Alınma yöntemi: `npx skills add obra/superpowers -a claude-code --skill '*' --copy --full-depth`
- Beceriler: brainstorming, dispatching-parallel-agents, executing-plans,
  finishing-a-development-branch, receiving-code-review, requesting-code-review,
  subagent-driven-development, systematic-debugging, test-driven-development,
  using-git-worktrees, using-superpowers, verification-before-completion,
  writing-plans, writing-skills
- NOT: upstream plugin'in `hooks/session-start` betiği KOPYALANMADI. Yerine
  `.claude/hooks/superpowers-session-start.sh` yazıldı (yol bağımsız + öncelik
  korkuluğu gömülü). Gerekçe betiğin kendi başlığındadır.

## Instagram'daki 5 eklenti — KURULU DEĞİL (denendi, ölçüldü, kaldırıldı)
2026-08-24'te bir Instagram videosunda önerilen beş Claude Code eklentisi
araştırıldı; ikisi fiilen kuruldu, biri sözleşmeye karşı sınandı, **hepsi
kaldırıldı**. Gerekçe tek satırda: beşi de modelin ETRAFINDAKİ boruları
değiştiriyor; bu depoda tavanı belirleyen şey borular değil, türev veri
kapsamı (`STRATEJI.md §4`: OI eksiği kapsamı 0.66'da bıraktı) ve **elle
ikinci-göz** (`CLAUDE.md`: grounding mekanikleştirilemez).

| Eklenti | Kaynak | Kaldırma gerekçesi (ölçülmüş) |
|---|---|---|
| **Headroom** | `headroomlabs-ai/headroom` | **Sınandı.** Sayı bütünlüğü GEÇTİ (252/252 birebir, %27.9 tasarruf) ama YAPI bütünlüğü BOZULDU: `router:tool_result:mixed` dönüşümü ZİRVE'den 8 alanı siliyor — `iki_satir`, `KIYAS`, `ONCEKI_AKIBET`, `CELISKI_TURU`, `ILK_GECIS`, `EMIR_GEREKCE`, `kapi_gerekceleri`, `_anlik_goruntu`. Varsayılan ayarda dahi. Sayı bozulmadığı için `iddia_denetle.py` YAKALAYAMAZ → gözlemcinin `EKSİK_AKTARIM` ihlali. Ayrıca ~9 GB disk + numpy/pandas/scipy yükseltmesi. |
| **claude-mem** | `thedotmack/claude-mem` | Karşılığı zaten var ve daha sıkı: `engine/state/devir_teslim.json` + `defter.jsonl` + `hafiza/agirlik.json` (Wilson-kalibreli, fail-closed). claude-mem kaynaksız düzyazı enjekte eder → `gozlemci.py`'nin `HAFIZA` ihlal sınıfıyla çelişir. |
| **task-observer** | `rebelytics/one-skill-to-rule-them-all` | Kuruldu, sonra kaldırıldı. Gerçek ama dar bir boşluk dolduruyordu (oturum gözlemi); `gozlemci.py` zaten boru hattı artefaktını denetliyor. Maliyet ölçüldü: **976 karakter ≈ 244 token/oturum** beceri listesinde. Faydası yalnız haftalık inceleme yapılırsa doğuyor. |
| **claude-code-setup** | `anthropics/claude-plugins-official` | Salt-okunur önyükleme öneri aracı. Bu depoda 28 beceri, 3 kanca, 20/20 motor, sağlık denetçisi ve yazılı çakışma-önceliği zaten var — var olanı önerir. |
| **OmniRoute** | `diegosouzapw/OmniRoute` | Claude Code eklentisi DEĞİL (`.claude-plugin/marketplace.json` → HTTP 404); yerel vekil sunucu. Zayıflattığı şey mekanik yarı değil, tam da muhakeme/ikinci-göz yarısı. Ayrıca istemler ve strateji kodu üçüncü taraf sağlayıcılara gider. |

- Kaldırılanlar: `.claude/skills/task-observer/`, `EKLENTILER.md`,
  `.claude/eklenti/headroom_sinav.py`, `settings.json`'daki
  `extraKnownMarketplaces`, `headroom-ai` paketi, marketplace kayıtları.
- **Headroom sınav aracı ve tam ölçüm raporu git geçmişindedir** (commit
  `7c2fe5e`). Konu tekrar açılırsa oradan geri alınır — hüküm anlatı değil,
  tekrar koşulabilir ölçümdür.
- NOT: `headroom-ai` kurulumunun getirdiği `numpy 2.4.6 / pandas 3.0.5 /
  scipy 1.17.1` yükseltmesi geri alınmadı (paket kaldırıldı, bağımlılıklar
  kaldı). Yükseltmeden sonra `engine/self_test.py` ve `saglik.py` koşuldu →
  geçti. Konteyner geçici olduğu için bu yükseltme kalıcı da değildir.

## vercel-labs/agent-skills — KURULU DEĞİL (kaldırıldı)
- 2026-08-08'de 9 beceri kuruldu, aynı gün `/doctor` denetiminde **kaldırıldı**.
- Gerekçe (ölçülmüş): bu depo Python/finans odaklıdır; 9 becerinin tetikleyicisi
  React/Next/Expo/UI'dır ve piyasa analizinde hiç eşleşmez. Beceri listeleme
  bütçesinde ~800 est. token/oturum yer kaplıyorlardı (toplam listeleme ~%1
  bütçesinin 2,6 katındaydı), karşılığında sıfır kullanım.
- Geri istenirse:
  `npx skills add vercel-labs/agent-skills -a claude-code --skill '*' --copy`
  ardından `~/.claude/skills/` altındaki dizinleri `.claude/skills/` içine kopyala.

## Tek-kaynak kuralı
Bu beceriler YALNIZ depoda (`.claude/skills/`) tutulur. `~/.claude/skills/`
altına kopya BIRAKILMAZ: iki kök ayrışırsa hangisinin yükleneceği makineye ve
çözüm sırasına bağlı kalır ve sessizce farklı sürüm koşar. (2026-08-08'de 23
beceri iki kökte birden duruyordu — bayt-özdeşti ama sapma riski taşıyordu;
global kopyalar silindi.)

## Çakışma önceliği
`CLAUDE.md` → "DIŞ BECERİ SİSTEMLERİ ve ÇAKIŞMA ÖNCELİĞİ" bölümü bağlayıcıdır.
Proje sözleşmesi her zaman üstündür; piyasa verisi geldiğinde varsayılan yol
piramit boru hattıdır.
