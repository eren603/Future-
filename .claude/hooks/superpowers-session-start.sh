#!/bin/bash
# SessionStart hook — Superpowers `using-superpowers` becerisini oturuma enjekte eder.
#
# NEDEN KENDİ SARMALAYICIMIZ (upstream hooks/session-start yerine):
#   1. Upstream betik `${PLUGIN_ROOT}/skills/using-superpowers/SKILL.md` yolunu
#      arar (plugin yerleşimi). Bizde beceriler `.claude/skills/` altında.
#   2. Upstream içeriği <EXTREMELY_IMPORTANT> ile sarar ve "her cevaptan ÖNCE,
#      açıklayıcı soru sormadan önce bile skill çağır" der. Bu, CLAUDE.md'deki
#      duran piramit kuralıyla (yeni veri gelince boru hattı tetikleyicisiz
#      koşar) her koşuda yarışır. Bu yüzden enjeksiyona ÖNCELİK KORKULUĞU
#      eklenir — beceri içeriği aynen aktarılır, üstüne sıralama yazılır.
#   3. JSON kaçışı bash parametre ikamesi yerine python3 ile yapılır (kaçış
#      hatası = bozuk hook çıktısı = sessiz enjeksiyon kaybı).
#
# Çıktı sözleşmesi: Claude Code `hookSpecificOutput.additionalContext` okur.
# Beceri dosyası yoksa hook SESSİZCE ve BAŞARIYLA çıkar (oturumu bloklamaz).
set -euo pipefail

PROJE="${CLAUDE_PROJECT_DIR:-.}"
BECERI="${PROJE}/.claude/skills/using-superpowers/SKILL.md"

[ -f "$BECERI" ] || exit 0

python3 - "$BECERI" <<'PY'
import json, sys, pathlib

icerik = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")

ONCELIK = """
<ONCELIK-SIRASI kaynak="CLAUDE.md">
Yukarıdaki 'using-superpowers' becerisi bu depoda KOŞULSUZ DEĞİLDİR.
Çelişki halinde sıra (üstteki kazanır):
  1. CLAUDE.md + STRATEJI.md — proje sözleşmesi (piyasa kararı disiplini,
     doğruluk sözleşmesi, sert yasaklar)
  2. Somut depo kanıtı (dosya/ölçüm/koşu raporu)
  3. Superpowers iş akışı — KOD/MÜHENDİSLİK işlerinde
  4. Vercel Agent Skills — React/Next/Expo/UI işlerinde
  5. Genel tercihler

Somut kural: kullanıcı piyasa verisi (piramit_veri_*.json, kline, CoinGlass
paneli) gönderdiğinde VARSAYILAN yol piramit boru hattıdır; 'önce brainstorm
edelim' ya da 'önce skill çağırayım' diye araya girilmez. Superpowers akışı
(brainstorm → plan → TDD → review → verification) DEPO KODU değiştirilecekse
uygulanır, piyasa analizi üretilirken DEĞİL.
</ONCELIK-SIRASI>
"""

metin = ("<EXTREMELY_IMPORTANT>\n"
         "Bu oturumda Superpowers becerileri kurulu. Aşağıdaki, "
         "'using-superpowers' becerisinin tam içeriğidir; diğer beceriler için "
         "'Skill' aracını kullan.\n\n"
         + icerik + "\n" + ONCELIK +
         "</EXTREMELY_IMPORTANT>")

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": metin,
    }
}, ensure_ascii=False))
PY
