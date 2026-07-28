#!/usr/bin/env bash
# YÖNLENDİR — kaynak: a-cwc-long-running-agents/claude-code-config/.claude/hooks/steer.sh
#              (sha256 bd4db9fb02b4, 14 satır)
#
# Kaynak yorumu (BİREBİR):
#   "If STEER.md has content, surface it to the agent once and clear the file.
#    Write to STEER.md (or pipe from a UI) to redirect the agent mid-run.
#    Note: this is a convenience channel, not a trust boundary; if the agent has
#    Write access to the project it can write STEER.md itself."
#
# TÜRKÇESİ: YONLENDIR.md doluysa içeriğini ajana BİR KEZ gösterir ve dosyayı
# boşaltır. Koşu ortasında ajanı yeniden yönlendirmek için YONLENDIR.md'ye
# yazın. Not: bu bir KOLAYLIK kanalıdır, bir GÜVEN SINIRI DEĞİLDİR; ajanın
# projeye Write erişimi varsa YONLENDIR.md'yi kendisi de yazabilir.
f="${YONLENDIR_DOSYASI:-${CLAUDE_PROJECT_DIR:-.}/YONLENDIR.md}"
if [ -s "$f" ]; then
  note=$(cat "$f")
  reason=$(python3 -c 'import json,sys; print(json.dumps("OPERATÖR YÖNLENDİRMESİ: " + sys.argv[1] + "\n\nYapmak üzere olduğunuz işi duraklatın, bu yönlendirmeyi dahil edin, sonra hedefe doğru devam edin."))' "$note" 2>/dev/null) || exit 0
  printf '{"decision":"block","reason":%s}\n' "$reason"
  : > "$f"
fi
