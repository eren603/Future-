#!/bin/bash
# SessionStart (2. giriş): duran görevin "ek" bölümü — strateji süzgeci +
# bekleyen işler.
#
# NEDEN AYRI KANCA: harness enjeksiyon eşiği KARAKTER cinsindendir ve bu
# depoda ÖLÇÜLDÜ — 13069 karakterlik çıktı "Output too large (12.8KB)" ile
# dosyaya kaydırılıp bağlama yalnız 2 KB önizleme girdi; 6290 karakterlik
# çıktı tam geçti. Tek parça duran görev 7731 karakter, yani kanıtlanmamış
# bantta. Her SessionStart girişi AYRI enjeksiyon aldığı için görev ikiye
# bölündü: her parça kanıtlanmış-güvenli sınırın altında kalır ve yeni
# pencere görevi EKSİKSİZ alır.
set -euo pipefail
KANCA="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/piramit_auto.py"
if [ -f "$KANCA" ]; then
  python3 "$KANCA" --gorev ek || true
fi
