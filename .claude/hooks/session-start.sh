#!/bin/bash
# SessionStart hook: beceri motorlarının bağımlılıklarını kurar.
# - Python: pandas/numpy/scipy (data-analysis-deep-scan + motorlar)
# - ffmpeg: video-isleme becerisi (video/ekran kaydı analizi)
# Idempotent, non-interactive, web-only.
set -euo pipefail

# --- Python bağımlılıkları (yoksa kur; durum raporundan ÖNCE ki rapor
# kurulum SONRASI gerçeği söylesin — kurulum başarılıysa "eksik" denmez).
# Uzak-dışı yüzeyde de denenir (--user, sistemi kirletmez) — eskiden yalnız
# CLAUDE_CODE_REMOTE=true iken kuruluyordu ve yerel taze pencerede motorlar
# sessizce koşamıyordu. ---
if ! python3 -c "import pandas, numpy, scipy" >/dev/null 2>&1; then
  if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
    python3 -m pip install -q --disable-pip-version-check pandas numpy scipy || true
  else
    python3 -m pip install -q --disable-pip-version-check --user pandas numpy scipy || true
  fi
fi

# --- Piramit hazırlık raporu (her ortamda; uzak/yerel farketmez) ---
# Not: asıl otomatik koşu UserPromptSubmit kancasındadır
# (.claude/hooks/piramit_auto.py) — burada yalnız DURUM bildirilir.
PIRAMIT="${CLAUDE_PROJECT_DIR:-.}/.claude/skills/piramit-sistem/scripts/piramit.py"
SAGLIK="${CLAUDE_PROJECT_DIR:-.}/.claude/skills/piramit-sistem/scripts/saglik.py"
if [ -f "$PIRAMIT" ]; then
  if python3 -c "import pandas, numpy, scipy" >/dev/null 2>&1; then
    echo "[PİRAMİT] Boru hattı hazır (K1→K5). Piyasa analizi/kararında VARSAYILAN yol; tetikleyici gerekmez."
  else
    echo "[PİRAMİT] Boru hattı var ama pandas/numpy/scipy KURULAMADI — motorlar koşamaz; elle koşuya düşülür (AÇIKÇA söylenmeli)."
  fi
  # Sağlık kontrolü: her yeni pencere bütün halkaları (motor kayıtları,
  # kancalar, girdi/görev, derleme) MEKANİK denetler ve tek satır bildirir.
  # Kırık halka varsa GİZLENMEZ — garanti söz değil, bu denetimdir.
  if [ -f "$SAGLIK" ]; then
    python3 "$SAGLIK" --hizli 2>&1 || true
  fi
else
  echo "[PİRAMİT] Boru hattı dosyası YOK — motorlar elle koşulur."
fi

# --- Duran görev damgası: YENİ pencere görevi TAM görmeli (ikinci emniyet).
# UserPromptSubmit kancası damgayı oturum kimliğiyle tutar; ortam değişkeni
# yoksa damga burada sıfırlanır ki duran görev sessizce kaybolmasın. ---
rm -f "${CLAUDE_PROJECT_DIR:-.}/.claude/skills/piramit-sistem/state/gorev_damga.json"

# Only run in Claude Code on the web (remote) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
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
