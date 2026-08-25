#!/usr/bin/env bash
# ACİL DURDUR — kaynak: a-cwc-long-running-agents/claude-code-config/.claude/hooks/kill-switch.sh
#                (sha256 a9ec39b3f233, 9 satır)
#
# Kaynak yorumu (BİREBİR):
#   "Halt every tool call while ./AGENT_STOP exists. `touch AGENT_STOP` to engage; `rm AGENT_STOP` to resume."
#
# TÜRKÇESİ: ./AJAN_DUR dosyası var olduğu sürece HER araç çağrısını durdurur.
# Devreye almak için `touch AJAN_DUR`; devam için `rm AJAN_DUR`.
if [ -e "${AJAN_DUR_DOSYASI:-${CLAUDE_PROJECT_DIR:-.}/AJAN_DUR}" ]; then
  cat <<'JSON'
{"decision":"block","reason":"Acil durdurma devrede: AJAN_DUR dosyası mevcut. Ajan durduruldu. Devam etmek için dosyayı silin."}
JSON
fi
