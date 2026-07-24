#!/bin/bash
# SessionStart hook: beceri motorlarının bağımlılıklarını kurar.
# - Python: pandas/numpy/scipy (data-analysis-deep-scan + motorlar)
# - ffmpeg: video-isleme becerisi (video/ekran kaydı analizi)
# Idempotent, non-interactive, web-only.
set -euo pipefail

# --- Piramit hazırlık raporu (her ortamda; uzak/yerel farketmez) ---
# Not: asıl otomatik koşu UserPromptSubmit kancasındadır
# (.claude/hooks/piramit_auto.py) — burada yalnız DURUM bildirilir.
PIRAMIT="${CLAUDE_PROJECT_DIR:-.}/.claude/skills/piramit-sistem/scripts/piramit.py"
if [ -f "$PIRAMIT" ]; then
  if python3 -c "import pandas, numpy, scipy" >/dev/null 2>&1; then
    echo "[PİRAMİT] Boru hattı hazır (K1→K5). Piyasa analizi/kararında VARSAYILAN yol; tetikleyici gerekmez."
  else
    echo "[PİRAMİT] Boru hattı var ama pandas/numpy/scipy eksik — motorlar koşamaz. Kurulum denenecek; olmazsa elle koşuya düşülür (AÇIKÇA söylenmeli)."
  fi
else
  echo "[PİRAMİT] Boru hattı dosyası YOK — motorlar elle koşulur."
fi

# Only run in Claude Code on the web (remote) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# --- Python bağımlılıkları (yoksa kur) ---
if ! python3 -c "import pandas, numpy, scipy" >/dev/null 2>&1; then
  python3 -m pip install -q --disable-pip-version-check pandas numpy scipy || true
fi

# --- ffmpeg (yoksa arka planda kur; oturum açılışını bloklamaz) ---
# Not: video-isleme/scripts/video_isle.py da kendi içinde ensure_ffmpeg ile
# eksikse kurar (çift emniyet) — bu kurulum yarım kalsa bile beceri çalışır.
if ! command -v ffmpeg >/dev/null 2>&1; then
  (
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq && apt-get install -y -qq ffmpeg
  ) >/tmp/ffmpeg-install.log 2>&1 &
fi
