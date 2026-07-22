#!/bin/bash
# SessionStart hook: beceri motorlarının bağımlılıklarını kurar.
# - Python: pandas/numpy/scipy (data-analysis-deep-scan + motorlar)
# - ffmpeg: video-isleme becerisi (video/ekran kaydı analizi)
# Idempotent, non-interactive, web-only.
set -euo pipefail

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
