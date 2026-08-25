#!/usr/bin/env bash
# KANIT SİCİLİ — kaynak: a-cwc-long-running-agents/claude-code-config/.claude/hooks/track-read.sh
#                (sha256 357549c4bada, 11 satır)
#
# Kaynak yorumu (BİREBİR):
#   "Records which evidence files (screenshots, console logs) the agent has opened this session.
#    verify-gate.sh consults this list before allowing a test to be marked passing."
#
# TÜRKÇESİ: Ajanın bu oturumda hangi kanıt dosyalarını açtığını kaydeder.
# kanit_kapisi.sh, korunan karar/emir dosyasına yazıma izin vermeden önce bu
# listeye bakar.
#
# BU DEPODAKİ KARŞILIK: "kanıt" = ekran görüntüsü/konsol logu DEĞİL, MOTOR
# ÇIKTISIDIR: piramit raporu (son_rapor*.json), engine durumu
# (engine/state/*.json), karar grafiği (engine/cikti/*.svg).
log="${KANIT_OKUMA_KAYDI:-${CLAUDE_PROJECT_DIR:-.}/.claude/.kanit-okumalari}"
korunan="${KARAR_DOSYASI:-onceki_kosu.json|durum.json}"

path=$(cat | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)

# DAİRESEL DOĞRULAMA ENGELİ (kaynakta YOK — bu depoya eklendi, KANIT.md/SAPMALAR):
# korunan karar dosyasının KENDİSİ kanıt sayılmaz. Aksi halde ajan karar
# dosyasını okuyup kapıyı kendi çıktısıyla açardı = depo yönergesindeki
# "DAİRESEL" gözlemci ihlali.
_eski_ifs="$IFS"; IFS='|'
for k in $korunan; do
  case "$path" in "$k"|*/"$k") IFS="$_eski_ifs"; exit 0 ;; esac
done
IFS="$_eski_ifs"

case "$path" in
  *son_rapor*.json|*engine/state/*.json|*/cikti/*.svg) [ -f "$path" ] && echo "$path" >> "$log" ;;
esac
exit 0
