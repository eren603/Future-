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
