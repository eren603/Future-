# KANIT — 4 kancanın kaynağa karşı satır-satır doğrulaması

Bu belge, `.claude/hooks/` altına eklenen 4 kancanın **her kuralının** kaynakta
birebir bulunduğunu gösterir. Hiçbir kural hafızadan yazılmamıştır.

## Kaynaklar ve sağlama toplamları (ölçülmüş)

`sha256sum | cut -c1-12` ile ölçüldü — hepsi görevde beyan edilen değerlerle **UYUŞTU**:

| Kaynak dosya | Beyan edilen | Ölçülen | Durum |
|---|---|---|---|
| `.claude/hooks/track-read.sh` | `357549c4bada` | `357549c4bada` | ✔ |
| `.claude/hooks/verify-gate.sh` | `1ffdb360818e` | `1ffdb360818e` | ✔ |
| `.claude/hooks/kill-switch.sh` | `a9ec39b3f233` | `a9ec39b3f233` | ✔ |
| `.claude/hooks/steer.sh` | `bd4db9fb02b4` | `bd4db9fb02b4` | ✔ |
| `cc/plugins/security-guidance/hooks/hooks.json` | `37181aea2a1c` | `37181aea2a1c` | ✔ |

Kaynak kökü **A**: `.../scratchpad/a-cwc-long-running-agents/claude-code-config/`
Kaynak kökü **B**: `.../scratchpad/cc/plugins/security-guidance/hooks/hooks.json`

---

## Eşleme tablosu

| # | Kaynak dosya:satır | Kaynaktan BİREBİR alıntı | Bizim dosya:satır | Uygulama |
|---|---|---|---|---|
| 1 | `track-read.sh:6` | `log="${VERIFY_READ_LOG:-./.claude/.evidence-reads}"` | `kanit_sicili.sh:16` | Sicil yolu env ile geçersiz kılınabilir; ad `KANIT_OKUMA_KAYDI` / `.claude/.kanit-okumalari` |
| 2 | `track-read.sh:7` | `path=$(cat \| python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)` | `kanit_sicili.sh:19` | stdin'den JSON → `tool_input.file_path`; **birebir aynı** python tek-satırı |
| 3 | `track-read.sh:8-10` | `case "$path" in`<br>`  *screenshots/*\|*-console.txt\|*-result.txt\|*.png) [ -f "$path" ] && echo "$path" >> "$log" ;;`<br>`esac` | `kanit_sicili.sh:31-33` | Aynı `case` + `[ -f ]` + append yapısı; desenler bu deponun kanıtına eşlendi (→ SAPMA 1) |
| 4 | `track-read.sh:11` | `exit 0` | `kanit_sicili.sh:34` | Sicil kancası **asla** araç çağrısını bloklamaz |
| 5 | `track-read.sh:4-5` | `Records which evidence files (screenshots, console logs) the agent has opened this session.`<br>`verify-gate.sh consults this list before allowing a test to be marked passing.` | `kanit_sicili.sh:5-11` | Kaynak yorumu BİREBİR alıntılandı + Türkçesi eklendi |
| 6 | `verify-gate.sh:13` | `log="${VERIFY_READ_LOG:-./.claude/.evidence-reads}"` | `kanit_kapisi.sh:33` | Sicil ve kapı **aynı** sicil dosyasını paylaşır |
| 7 | `verify-gate.sh:14` | `results="${RESULTS_FILE:-test-results.json}"` | `kanit_kapisi.sh:34` | Korunan dosya env ile geçersiz kılınabilir; ad `KARAR_DOSYASI`, varsayılan `onceki_kosu.json\|durum.json` (→ SAPMA 2) |
| 8 | `verify-gate.sh:16-17` | `input=$(cat)`<br>`target=$(printf '%s' "$input" \| python3 -c '...get("file_path",""))' 2>/dev/null)` | `kanit_kapisi.sh:36-37` | stdin bir kez okunur, sonra python'a verilir — **birebir aynı** desen |
| 9 | `verify-gate.sh:19-20` | `# Only guard the results file (anchor on path separator so e.g. vitest-results.json doesn't match)`<br>`case "$target" in "$results"\|*/"$results") ;; *) exit 0 ;; esac` | `kanit_kapisi.sh:40-46` | **Yol ayracına sabitleme korundu** (`"$k"\|*/"$k"`) — `eth_durum.json` eşleşmez (vaka 2F ile kanıtlandı) |
| 10 | `verify-gate.sh:22-27` | `if [ ! -s "$log" ]; then`<br>`  cat <<'JSON'`<br>`{"decision":"block","reason":"Cannot modify the results file: no screenshot or console-log evidence has been Read this session. Open the evidence file with the Read tool first, then retry."}`<br>`JSON`<br>`  exit 0`<br>`fi` | `kanit_kapisi.sh:48-53` | Boş sicil → `{"decision":"block","reason":...}`; blok mesajı Türkçe (→ SAPMA 3) |
| 11 | `verify-gate.sh:28-29` | `# consume the evidence so the next change needs fresh proof`<br>`: > "$log"` | `kanit_kapisi.sh:55` | **Kanıt TÜKETİLİR** — sonraki yazım taze kanıt ister (vaka 2C→2D ile kanıtlandı) |
| 12 | `verify-gate.sh:5-6` | `Denies any Write/Edit to the results file unless the agent has opened at least`<br>`one evidence file (screenshot/console log) since the gate last fired.` | `kanit_kapisi.sh:7-8` | Kaynak amaç cümlesi BİREBİR + Türkçesi |
| 13 | `verify-gate.sh:8-12` | `This is a teaching example, not a security boundary. Known gaps a real`<br>`enforcement layer would close: this only hooks Write/Edit (Bash sed/jq can`<br>`rewrite the file unchecked); the path match is basename-only and`<br>`case-sensitive; and any evidence read unlocks any result row, not the`<br>`corresponding one. Tighten in your project as needed.` | `kanit_kapisi.sh:15-31` | **DÜRÜST UYARI BİREBİR taşındı** (İngilizce orijinal) + Türkçesi + bu depoya özel ek boşluk |
| 14 | `kill-switch.sh:5` | `if [ -e "${AGENT_STOP_FILE:-./AGENT_STOP}" ]; then` | `acil_durdur.sh:10` | Dosya varlığı kontrolü; ad `AJAN_DUR`, env `AJAN_DUR_DOSYASI` |
| 15 | `kill-switch.sh:6-8` | `  cat <<'JSON'`<br>`{"decision":"block","reason":"Kill switch engaged: AGENT_STOP file exists. Agent is halted. Remove the file to resume."}`<br>`JSON` | `acil_durdur.sh:11-13` | Aynı heredoc + aynı JSON şekli; mesaj Türkçe (→ SAPMA 3) |
| 16 | `kill-switch.sh:4` | `Halt every tool call while ./AGENT_STOP exists. \`touch AGENT_STOP\` to engage; \`rm AGENT_STOP\` to resume.` | `acil_durdur.sh:6-9` | BİREBİR alıntı + Türkçesi; `settings.json` matcher `*` = **her** araç çağrısı |
| 17 | `steer.sh:8` | `f="${AGENT_STEER_FILE:-./STEER.md}"` | `yonlendir.sh:15` | Ad `YONLENDIR.md`, env `YONLENDIR_DOSYASI` |
| 18 | `steer.sh:9-10` | `if [ -s "$f" ]; then`<br>`  note=$(cat "$f")` | `yonlendir.sh:16-17` | `-s` = **doluysa** (boş dosya tetiklemez) — birebir |
| 19 | `steer.sh:11` | `reason=$(python3 -c 'import json,sys; print(json.dumps("OPERATOR STEERING: " + sys.argv[1] + "\n\nPause what you were about to do, incorporate this guidance, then continue toward the feature goal."))' "$note" 2>/dev/null) \|\| exit 0` | `yonlendir.sh:18` | `json.dumps` ile kaçış (tırnak/satır sonu güvenli — vaka 4B ile kanıtlandı); `\|\| exit 0` başarısızlık-sessiz davranışı korundu |
| 20 | `steer.sh:12` | `printf '{"decision":"block","reason":%s}\n' "$reason"` | `yonlendir.sh:19` | Birebir aynı `printf` |
| 21 | `steer.sh:13` | `: > "$f"` | `yonlendir.sh:20` | **Bir kez göster, sonra boşalt** (vaka 4B→4C ile kanıtlandı) |
| 22 | `steer.sh:4-7` | `If STEER.md has content, surface it to the agent once and clear the file.`<br>`Write to STEER.md (or pipe from a UI) to redirect the agent mid-run.`<br>`Note: this is a convenience channel, not a trust boundary; if the agent has`<br>`Write access to the project it can write STEER.md itself.` | `yonlendir.sh:6-14` | Dürüst "güven sınırı değildir" uyarısı BİREBİR + Türkçesi |
| 23 | `A/.claude/settings.json:5-8` | `"matcher": "*",`<br>`{ "type": "command", "command": ".claude/hooks/kill-switch.sh" },`<br>`{ "type": "command", "command": ".claude/hooks/steer.sh" }` | `settings.json:26-38` | `PreToolUse` + matcher `*` → `acil_durdur.sh`, `yonlendir.sh` — **aynı sıra** (önce durdurma, sonra yönlendirme) |
| 24 | `A/.claude/settings.json:12-14` | `"matcher": "Read",`<br>`{ "type": "command", "command": ".claude/hooks/track-read.sh" }` | `settings.json:39-47` | `PreToolUse` + matcher `Read` → `kanit_sicili.sh` |
| 25 | `A/.claude/settings.json:18-20` | `"matcher": "Write\|Edit",`<br>`{ "type": "command", "command": ".claude/hooks/verify-gate.sh" }` | `settings.json:48-56` | `PreToolUse` + matcher `Write\|Edit` → `kanit_kapisi.sh` |
| 26 | `B/hooks.json:63-65` | `"asyncRewake": true,`<br>`"rewakeMessage": "Background security review feedback — address or acknowledge the findings below, then continue with the user's original request or continue waiting for their reply. This is supplementary, not a replacement for your previous response:",`<br>`"rewakeSummary": "Background security review found issues"` | `settings.json:64-66` | `Stop` olayında **alan adları BİREBİR**: `asyncRewake` / `rewakeMessage` / `rewakeSummary`; değerler Türkçe (→ SAPMA 3, 5) |
| 27 | `B/hooks.json:57-59` | `"Stop": [`<br>`  {`<br>`    "hooks": [` | `settings.json:58-60` | `Stop` bloğunda **matcher YOK** — kaynakta da yok (Stop olayı matcher almaz) |
| 28 | `A/README.md:5` | `**Requires:** \`bash\`, \`git\`, \`python3\` (the hooks parse JSON via python3; without it they silently no-op).` | 4 kancanın tamamı | `2>/dev/null` ile python3 yoksa sessiz no-op davranışı korundu |
| 29 | `A/.claude/CLAUDE.md:18` | `The \`verify-gate\` hook will deny writes to \`test-results.json\` until you have opened evidence. Do not try to work around it.` | `kanit_kapisi.sh:50` (blok mesajı) | Aynı sözleşme: kanıt açılmadan karar dosyası yazılamaz |

---

## SAPMALAR (kaynaktan ayrılan her nokta, gerekçesiyle)

### SAPMA 1 — "Kanıt" eşlemesi: ekran görüntüsü → MOTOR ÇIKTISI
**Kaynak** (`track-read.sh:9`): `*screenshots/*|*-console.txt|*-result.txt|*.png`
**Bizde** (`kanit_sicili.sh:32`): `*son_rapor*.json|*engine/state/*.json|*/cikti/*.svg`

**Gerekçe:** Bu depoda tarayıcı ekran görüntüsü yoktur; bir iddianın kanıtı
motorun **dosyaya yazılmış sayısal çıktısıdır**. Depoda ölçülerek bulunan
gerçek kanıt dosyaları:
- `.claude/skills/piramit-sistem/state/son_rapor.json` (57 965 B) ve
  `son_rapor_eth.json` (70 553 B) — K1…K5 katman raporu, `ZIRVE` bloğu
- `engine/state/durum.json`, `defter.jsonl`, `bar_arsivi.jsonl`, `onceki_kosu.json`
- `engine/cikti/btc_karar.svg`, `eth_karar.svg` — çizilmiş karar grafiği

Bu, depo yönergesinin *"dosyadan okunmayan sayı kullanılmaz"* kuralının
kanca düzeyindeki karşılığıdır.

### SAPMA 2 — Korunan "sonuç dosyası": `test-results.json` → `onceki_kosu.json|durum.json`
**Kaynak** (`verify-gate.sh:14`): `results="${RESULTS_FILE:-test-results.json}"`
**Bizde** (`kanit_kapisi.sh:34`): `korunan="${KARAR_DOSYASI:-onceki_kosu.json|durum.json}"`

**Gerekçe — UYDURULMADI, grep ile bulundu:**
- `piramit.py:1646` → `(sdir / "onceki_kosu.json").write_text(...)` — bu dosya
  `YON_BIAS`, `islem_kalitesi` ve `islem_seviyeleri` (giriş/stop/hedef) tutar;
  ölçülen içerik: `"YON_BIAS": "SHORT"`, `"islem_seviyeleri": {"giris": 63990.7,
  "stop": 64234.1, "hedef": 63461.2, "kaynak": "emir_plani"}`.
  Depo `CLAUDE.md`'si bunu açıkça hesap-verme kaydı ilan eder:
  *"Her koşu sonunda `onceki_kosu.json` anlık görüntüsü yazılır"*.
- `karar_motoru.py:56` → `STATE_FILE = os.path.join(STATE_DIR, "durum.json")` —
  bu dosya `karar` bloğunu tutar; ölçülen içerik: `"karar": "SHORT"`,
  `"giris": 64364.0`, `"stop": 64790.3`, `"t1": 63567.0`, `"r": 1.87`.

**İki dosya birlikte korunuyor (kaynakta tek dosya vardı):** kaynağın tek-dosya
sınırı bu depoda yetersiz kalırdı — nihai karar/emir iki ayrı motor tarafından
iki ayrı dosyaya yazılır. `|` ayraçlı liste, kaynağın `case "$target" in
"$results"|*/"$results")` yol-sabitleme mantığını **bozmadan** genişletir.
Tek dosyaya dönmek için: `KARAR_DOSYASI=onceki_kosu.json`.

**Yan fayda:** basename eşleşmesi, kum havuzu kopyasını
(`.../state/kum_havuzu/onceki_kosu.json`) da otomatik kapsar.

### SAPMA 3 — Türkçeleştirme (blok mesajları + rewake metinleri)
**Kaynak** blok mesajları İngilizce; **bizde** Türkçe.
**Gerekçe:** Görev açıkça *"Bu depo Türkçe; blok mesajları Türkçe olsun"* diyor
ve depo `CLAUDE.md`'si tamamen Türkçedir. **Mekanik alanlar (`decision`,
`reason`, `asyncRewake`, `rewakeMessage`, `rewakeSummary`, `type`, `command`,
`matcher`) İngilizce KALDI** — bunlar Claude Code sözleşmesidir, çevrilemez.
Yalnız insan tarafından okunan **değerler** Türkçeleştirildi. Kaynağın
İngilizce dürüst-uyarı metni (`verify-gate.sh:8-12`) `kanit_kapisi.sh` içinde
**BİREBİR İngilizce olarak da** korundu, Türkçesi yanına eklendi.

### SAPMA 4 — Mevcut kancaların korunması + yol biçimi
**Kaynak** (`A/.claude/settings.json`): `PreToolUse` + `Stop` var, `SessionStart`
ve `UserPromptSubmit` **yok**; komutlar göreli yol (`.claude/hooks/x.sh`).
**Bizde:** mevcut `SessionStart` (`session-start.sh`, `timeout: 600`) ve
`UserPromptSubmit` (`piramit_auto.py`, `timeout: 900`) blokları **karakterine
kadar aynen korundu**, üzerine eklendi. Yeni komutlar
`bash "$CLAUDE_PROJECT_DIR/.claude/hooks/..."` biçiminde yazıldı.

**Gerekçe:** (a) Görev bu iki kancanın bozulmamasını şart koşuyor; (b) deponun
kendi kancaları zaten `$CLAUDE_PROJECT_DIR` kullanıyor — göreli yol, kanca
çalışma dizini depo kökü olmadığında kırılırdı. Aynı nedenle sicil/AJAN_DUR/
YONLENDIR yolları `${CLAUDE_PROJECT_DIR:-.}` ile öneklendi (kaynakta `./` idi);
`:-.` yedeği kaynağın davranışını değişken tanımsızken korur.

### SAPMA 5 — `Stop` kancasının komutu: `commit-on-stop.sh` DEĞİL, `yonlendir.sh`
**Kaynak A** `Stop` olayına `commit-on-stop.sh` bağlar; **kaynak B** `Stop`
olayına `asyncRewake` desenini bağlar.
**Bizde** `Stop` → `yonlendir.sh` + `asyncRewake`.

**Gerekçe — dürüst açıklama:** Görev bana **yalnız 6 dosyanın** sahipliğini
verdi; `commit-on-stop.sh` bu listede **yok**, dolayısıyla onu yazamazdım ve
`Stop`'a bağlayamazdım (olmayan dosyaya bağlamak sessiz hata üretirdi).
Sahip olduğum 4 kanca içinde `Stop` anında anlamlı çıktı üreten **tek** kanca
`yonlendir.sh`'tir: operatör oturum biterken `YONLENDIR.md`'ye yazmışsa, ajan
durmak yerine o yönlendirmeyle **yeniden uyandırılır**. `asyncRewake` deseninin
üç alan adı kaynak B'den (`hooks.json:63-65`) **birebir** alınmıştır — uydurma
alan adı yoktur.
**Bilinen sınır:** Bu depoda oturum sonu commit'i **`Stop` kancasıyla
yapılmıyor**; depo `CLAUDE.md`'si commit'i ajanın kendi sorumluluğuna bırakır
(*"koşu sonrası `engine/state/` değişiklikleri commit+push edilir"*). Bir
`commit-on-stop` karşılığı isteniyorsa ayrı bir dosya olarak eklenmelidir.

### SAPMA 6 — Dairesel doğrulama engeli (kaynakta YOK, eklendi)
**Bizde** (`kanit_sicili.sh:25-29`): korunan karar dosyasının **kendisi** kanıt
olarak sicile yazılmaz.
**Gerekçe:** Kaynakta sonuç dosyası (`test-results.json`) kanıt desenlerine
(`*.png` vb.) zaten uymuyordu, dolayısıyla sorun görünmüyordu. Bizde ise
korunan `onceki_kosu.json`/`durum.json`, kanıt deseni `*engine/state/*.json`'un
**içine düşüyor** — önlem alınmasa ajan karar dosyasını okuyup kapıyı **kendi
çıktısıyla** açabilirdi. Bu tam olarak depo `CLAUDE.md`'sinin *"DAİRESEL
(danışman kendi çıktısıyla doğrulanıyor)"* ihlalidir. 5 satırlık `for`/`case`
bloğu bunu kapatır (vaka 1D ile kanıtlandı).

### Kaynakta olup bizde OLMAYAN (bilinçli)
`commit-on-stop.sh` **port edilmedi** — dosya sahipliğim dışında (SAPMA 5).
`A/.claude/CLAUDE.md` ve `A/.claude/agents/evaluator.md` **kopyalanmadı** —
görev `CLAUDE.md`'ye ve diğer dosyalara dokunmayı açıkça yasakladı.

---

## DOĞRULAMA — gerçek JSON girdisiyle elle koşum

Tüm koşumlar `CLAUDE_PROJECT_DIR=/home/user/Future-` ile, sicil ve tetik
dosyaları kum-havuzuna yönlendirilerek yapıldı (depo durumu kirletilmedi).
**14 vaka / 14 BAŞARILI.**

### 1) `kanit_sicili.sh` — 4 vaka

**1A — motor raporu okundu → KAYDEDİLMELİ**
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/.claude/skills/piramit-sistem/state/son_rapor.json"}}' | bash .claude/hooks/kanit_sicili.sh
exit=0
sicil: /home/user/Future-/.claude/skills/piramit-sistem/state/son_rapor.json
```

**1B — karar SVG'si okundu → KAYDEDİLMELİ**
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/engine/cikti/btc_karar.svg"}}' | bash .claude/hooks/kanit_sicili.sh
exit=0
sicil satır sayısı: 2
```

**1C — alakasız dosya (`CLAUDE.md`) → KAYDEDİLMEMELİ**
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/CLAUDE.md"}}' | bash .claude/hooks/kanit_sicili.sh
exit=0
sicil satır sayısı (değişmemeli): 2
```

**1D — DAİRESEL: korunan karar dosyası kanıt SAYILMAMALI** (SAPMA 6)
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/engine/state/onceki_kosu.json"}}' | bash .claude/hooks/kanit_sicili.sh
exit=0
sicil satır sayısı (değişmemeli): 2
/home/user/Future-/.claude/skills/piramit-sistem/state/son_rapor.json
/home/user/Future-/engine/cikti/btc_karar.svg
```

### 2) `kanit_kapisi.sh` — 6 vaka

**2A — KANIT YOKKEN karar dosyasına yazım → BLOK**
```
$ : > "$KANIT_OKUMA_KAYDI"
$ echo '{"tool_input":{"file_path":"/home/user/Future-/engine/state/onceki_kosu.json"}}' | bash .claude/hooks/kanit_kapisi.sh
{"decision":"block","reason":"Karar/emir dosyası değiştirilemez: bu oturumda hiçbir motor kanıtı Read ile açılmadı. Önce kanıtı okuyun — .claude/skills/piramit-sistem/state/son_rapor*.json, engine/state/*.json ya da engine/cikti/*.svg — sonra tekrar deneyin. Kanıtsız karar yazımı YASAK (uydurma sayı korkuluğu)."}
exit=0
```

**2B — korunmayan dosyaya yazım → GEÇİŞ (çıktı boş)**
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/CLAUDE.md"}}' | bash .claude/hooks/kanit_kapisi.sh
[çıktı yok] exit=0
```

**2C — KANIT OKUNDUKTAN SONRA → GEÇİŞ + kanıt TÜKETİLİR**
```
$ echo '{"tool_input":{"file_path":".../state/son_rapor.json"}}' | bash .claude/hooks/kanit_sicili.sh
yazımdan önce sicil boyutu: 70 bayt
$ echo '{"tool_input":{"file_path":"/home/user/Future-/engine/state/onceki_kosu.json"}}' | bash .claude/hooks/kanit_kapisi.sh
[blok JSON'u YOK] exit=0
yazımdan sonra sicil boyutu (TÜKETİLDİ): 0 bayt
```

**2D — tüketim sonrası İKİNCİ yazım → yine BLOK (taze kanıt şart)**
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/engine/state/onceki_kosu.json"}}' | bash .claude/hooks/kanit_kapisi.sh
{"decision":"block","reason":"Karar/emir dosyası değiştirilemez: bu oturumda hiçbir motor kanıtı Read ile açılmadı. ..."}
exit=0
```

**2E — ikinci korunan dosya `durum.json` → BLOK** (SAPMA 2)
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/engine/state/durum.json"}}' | bash .claude/hooks/kanit_kapisi.sh
{"decision":"block","reason":"Karar/emir dosyası değiştirilemez: ..."}
exit=0
```

**2F — yol-ayracı sabitlemesi: `eth_durum.json` EŞLEŞMEMELİ → GEÇİŞ**
```
$ echo '{"tool_input":{"file_path":"/home/user/Future-/engine/state/eth_durum.json"}}' | bash .claude/hooks/kanit_kapisi.sh
[çıktı yok] exit=0
```
Bu, kaynak `verify-gate.sh:19` yorumunun (*"anchor on path separator so e.g.
vitest-results.json doesn't match"*) bu depodaki karşılığıdır.

### 3) `acil_durdur.sh` — 2 vaka

**3A — `AJAN_DUR` YOK → GEÇİŞ**
```
$ echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | bash .claude/hooks/acil_durdur.sh
[çıktı yok] exit=0
```

**3B — `AJAN_DUR` VAR → BLOK**
```
$ touch "$AJAN_DUR_DOSYASI"
$ echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | bash .claude/hooks/acil_durdur.sh
{"decision":"block","reason":"Acil durdurma devrede: AJAN_DUR dosyası mevcut. Ajan durduruldu. Devam etmek için dosyayı silin."}
exit=0
```

### 4) `yonlendir.sh` — 3 vaka

**4A — `YONLENDIR.md` yok/boş → GEÇİŞ**
```
$ echo '{"tool_name":"Read"}' | bash .claude/hooks/yonlendir.sh
[çıktı yok] exit=0
```

**4B — `YONLENDIR.md` DOLU → BİR KEZ gösterir** (tırnak + satır sonu kaçış testi)
```
$ printf 'BTC yerine ETH analizine geç. "Tırnaklı" metin ve\nsatır sonu testi.\n' > "$YONLENDIR_DOSYASI"
$ echo '{"tool_name":"Read"}' | bash .claude/hooks/yonlendir.sh
{"decision":"block","reason":"OPERATÖR YÖNLENDİRMESİ: BTC yerine ETH analizine geç. \"Tırnaklı\" metin ve\nsatır sonu testi.\n\nYapmak üzere olduğunuz işi duraklatın, bu yönlendirmeyi dahil edin, sonra hedefe doğru devam edin."}
exit=0
```
`json.dumps` çift tırnağı `\"`, satır sonunu `\n`, Türkçe harfleri `\uXXXX`
olarak kaçırdı → **JSON kırılmıyor** (kaynak `steer.sh:11` deseninin faydası).

**4C — İKİNCİ çağrı: dosya boşaltıldı → tekrar GÖSTERMEZ**
```
dosya boyutu (0 olmalı): 0 bayt
$ echo '{"tool_name":"Read"}' | bash .claude/hooks/yonlendir.sh
[çıktı yok] exit=0
```

### 5) `settings.json` geçerlilik
```
$ python3 -c "import json;json.load(open('.claude/settings.json'))"
settings.json GEÇERLİ JSON
```
Mevcut iki kancanın korunduğu ayrıca doğrulandı: `SessionStart` →
`session-start.sh` (`timeout` 600), `UserPromptSubmit` → `piramit_auto.py`
(`timeout` 900) — değerler değişmedi.

### 6) İzin bitleri
```
-rwxr-xr-x  .claude/hooks/acil_durdur.sh
-rwxr-xr-x  .claude/hooks/kanit_kapisi.sh
-rwxr-xr-x  .claude/hooks/kanit_sicili.sh
-rwxr-xr-x  .claude/hooks/yonlendir.sh
```

---

## Kullanım

| Kanca | Olay / matcher | Devreye alma |
|---|---|---|
| `acil_durdur.sh` | `PreToolUse` `*` | `touch AJAN_DUR` → durur; `rm AJAN_DUR` → devam |
| `yonlendir.sh` | `PreToolUse` `*` + `Stop` (`asyncRewake`) | `echo "..." > YONLENDIR.md` |
| `kanit_sicili.sh` | `PreToolUse` `Read` | otomatik |
| `kanit_kapisi.sh` | `PreToolUse` `Write\|Edit` | otomatik |

**Env ile ayar:** `KANIT_OKUMA_KAYDI`, `KARAR_DOSYASI`, `AJAN_DUR_DOSYASI`,
`YONLENDIR_DOSYASI`.

⚠️ `kanit_kapisi.sh` bir **öğretici korkuluktur, güvenlik sınırı değildir** —
kaynaktaki dürüst uyarının tamamı dosyanın başında İngilizce ve Türkçe durur.
