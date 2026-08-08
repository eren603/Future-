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

## vercel-labs/agent-skills — 9 beceri
- Kaynak: https://github.com/vercel-labs/agent-skills
- Lisans: MIT (SKILL.md frontmatter `license:` alanında)
- Alınma yöntemi: `npx skills add vercel-labs/agent-skills -a claude-code --skill '*' --copy`
- Beceriler: deploy-to-vercel, vercel-cli-with-tokens, vercel-composition-patterns,
  vercel-optimize, vercel-react-best-practices, vercel-react-native-skills,
  vercel-react-view-transitions, web-design-guidelines, writing-guidelines
- NOT: bu depo Python/finans odaklıdır; bu 9 becerinin tetikleyicisi
  React/Next/Expo/UI'dır ve piyasa analizinde eşleşmez. Bağlam maliyeti dışında
  etkileri yoktur. Kaldırmak için: `rm -rf .claude/skills/vercel-* \
  .claude/skills/deploy-to-vercel .claude/skills/web-design-guidelines \
  .claude/skills/writing-guidelines`

## Çakışma önceliği
`CLAUDE.md` → "DIŞ BECERİ SİSTEMLERİ ve ÇAKIŞMA ÖNCELİĞİ" bölümü bağlayıcıdır.
Proje sözleşmesi her zaman üstündür; piyasa verisi geldiğinde varsayılan yol
piramit boru hattıdır.
