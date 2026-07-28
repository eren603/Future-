#!/usr/bin/env bash
# KANIT KAPISI — kaynak: a-cwc-long-running-agents/claude-code-config/.claude/hooks/verify-gate.sh
#                (sha256 1ffdb360818e, 29 satır)
#
# Kaynak yorumu (BİREBİR):
#   "Denies any Write/Edit to the results file unless the agent has opened at least
#    one evidence file (screenshot/console log) since the gate last fired."
#
# TÜRKÇESİ: Kapı en son ateşlendiğinden beri ajan en az bir kanıt dosyası
# (motor raporu / engine durumu / karar SVG'si) AÇMADIYSA, karar-emir
# dosyasına yapılan her Write/Edit'i reddeder.
#
# ───────────────────────────────────────────────────────────────────────────
# KAYNAKTAKİ DÜRÜST UYARI — BİREBİR (verify-gate.sh:8-12):
#
#   "This is a teaching example, not a security boundary. Known gaps a real
#    enforcement layer would close: this only hooks Write/Edit (Bash sed/jq can
#    rewrite the file unchecked); the path match is basename-only and
#    case-sensitive; and any evidence read unlocks any result row, not the
#    corresponding one. Tighten in your project as needed."
#
# TÜRKÇESİ: Bu bir ÖĞRETİCİ ÖRNEKTİR, bir GÜVENLİK SINIRI DEĞİLDİR. Gerçek bir
# zorlama katmanının kapatacağı bilinen boşluklar: yalnızca Write/Edit'e
# bağlanır (Bash sed/jq dosyayı denetimsizce yeniden yazabilir); yol eşleşmesi
# yalnızca dosya-adı bazlıdır ve büyük/küçük harfe duyarlıdır; ve herhangi bir
# kanıt okuması, KARŞILIK GELEN satırı değil, HERHANGİ bir sonuç satırını açar.
# Kendi projenizde gerektiği kadar sıkılaştırın.
#
# BU DEPOYA ÖZEL EK BOŞLUK: motorlar (piramit.py, karar_motoru.py) karar
# dosyalarını Python'dan yazar — Write/Edit'e bağlı bu kapı onları GÖRMEZ.
# Kapı yalnız AJANIN elle yazımını denetler.
# ───────────────────────────────────────────────────────────────────────────
log="${KANIT_OKUMA_KAYDI:-${CLAUDE_PROJECT_DIR:-.}/.claude/.kanit-okumalari}"
korunan="${KARAR_DOSYASI:-onceki_kosu.json|durum.json}"

input=$(cat)
target=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)

# Yalnız karar/emir dosyasını koru (yol ayracına sabitle — ör. eth_durum.json eşleşmesin)
_vurdu=0
_eski_ifs="$IFS"; IFS='|'
for k in $korunan; do
  case "$target" in "$k"|*/"$k") _vurdu=1 ;; esac
done
IFS="$_eski_ifs"
[ "$_vurdu" = 1 ] || exit 0

if [ ! -s "$log" ]; then
  cat <<'JSON'
{"decision":"block","reason":"Karar/emir dosyası değiştirilemez: bu oturumda hiçbir motor kanıtı Read ile açılmadı. Önce kanıtı okuyun — .claude/skills/piramit-sistem/state/son_rapor*.json, engine/state/*.json ya da engine/cikti/*.svg — sonra tekrar deneyin. Kanıtsız karar yazımı YASAK (uydurma sayı korkuluğu)."}
JSON
  exit 0
fi
# kanıtı TÜKET — bir sonraki değişiklik TAZE kanıt istesin
: > "$log"
