#!/usr/bin/env bash
# Claude Code'u Kimi'ye çevirir: Opus 5 gider, Kimi K3 + Kimi Code gelir.
# Depoya HİÇBİR ŞEY yazmaz — anahtar yalnız ~/.claude/settings.json'a gider.
#
# Kullanım:
#   ./kimi-kur.sh sk-ANAHTARINIZ            # Moonshot (Anthropic uyumlu)
#   ./kimi-kur.sh sk-ANAHTARINIZ kimicode   # Kimi Code ucu
#   ./kimi-kur.sh --geri                    # Claude'a geri dön
set -euo pipefail

AYAR="$HOME/.claude/settings.json"
mkdir -p "$(dirname "$AYAR")"
[ -f "$AYAR" ] || echo '{}' > "$AYAR"

if [ "${1:-}" = "--geri" ]; then
  tmp=$(mktemp)
  python3 - "$AYAR" > "$tmp" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); e=d.get("env") or {}
for k in ("ANTHROPIC_BASE_URL","ANTHROPIC_AUTH_TOKEN","ANTHROPIC_API_KEY",
          "ANTHROPIC_MODEL","ANTHROPIC_SMALL_FAST_MODEL"):
    e.pop(k,None)
if e: d["env"]=e
else: d.pop("env",None)
print(json.dumps(d,ensure_ascii=False,indent=2))
PY
  mv "$tmp" "$AYAR"; chmod 600 "$AYAR"
  echo "✔ Kimi ayarları kaldırıldı — Claude Code kendi hesabına döndü."
  echo "  Claude Code'u yeniden başlat."
  exit 0
fi

ANAHTAR="${1:-}"
if [ -z "$ANAHTAR" ]; then
  echo "Kullanım: $0 <KIMI_API_ANAHTARI> [kimicode]   |   $0 --geri" >&2
  echo "Anahtar: https://platform.moonshot.ai  ya da  https://platform.kimi.ai" >&2
  exit 2
fi

if [ "${2:-}" = "kimicode" ]; then
  UC="https://api.kimi.com/coding"; MODEL="k3-256k"
else
  UC="https://api.moonshot.ai/anthropic"; MODEL="kimi-k3"
fi

tmp=$(mktemp)
python3 - "$AYAR" "$UC" "$ANAHTAR" "$MODEL" > "$tmp" <<'PY'
import json,sys
p,uc,key,model = sys.argv[1:5]
d = json.load(open(p))
d.setdefault("env",{}).update({
    "ANTHROPIC_BASE_URL": uc,
    "ANTHROPIC_AUTH_TOKEN": key,
    "ANTHROPIC_MODEL": model,
    "ANTHROPIC_SMALL_FAST_MODEL": model,
})
print(json.dumps(d,ensure_ascii=False,indent=2))
PY
mv "$tmp" "$AYAR"; chmod 600 "$AYAR"

# Piramidin LLM kurulu (kimi-k3 tez ↔ kimi-code antitez) aynı anahtarı kullanır.
KABUK="$HOME/.bashrc"; [ -n "${ZSH_VERSION:-}" ] && KABUK="$HOME/.zshrc"
grep -q "^export KIMI_API_KEY=" "$KABUK" 2>/dev/null \
  && sed -i "s|^export KIMI_API_KEY=.*|export KIMI_API_KEY='$ANAHTAR'|" "$KABUK" \
  || echo "export KIMI_API_KEY='$ANAHTAR'" >> "$KABUK"

echo "✔ Claude Code → Kimi"
echo "   uç   : $UC"
echo "   model: $MODEL   (küçük/hızlı model de aynı)"
echo "   ayar : $AYAR  (chmod 600, depoya girmez)"
echo "✔ KIMI_API_KEY $KABUK dosyasına yazıldı — piramidin llm-kurul motoru bunu okur"
echo
echo "Şimdi: yeni terminal aç (ya da: source $KABUK) ve Claude Code'u yeniden başlat."
echo "Doğrulama: python3 .claude/skills/piramit-sistem/scripts/llm_kurul.py --job <(echo '{\"kanit\":{\"test\":1}}')"
