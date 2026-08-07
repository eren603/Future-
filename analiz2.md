# ANALİZ2 — Tam Analiz Yöntemi ve Referans Oturum Kaydı

> **TETİKLEYİCİ: `analiz2`**
> Kullanıcı bir istemde **`analiz2`** yazdığında (tek başına ya da veri/görüntü
> ekiyle birlikte), **YALNIZ BU DOSYA** açılır ve aşağıdaki yöntem **birebir**
> uygulanır. Başka yöntem dosyasına, başka örneğe, başka oturuma yönelme.
> `CLAUDE.md` ve `STRATEJI.md` yürürlükteki **kurallardır** (değişmez sözleşme);
> bu dosya ise o kuralların **nasıl koşturulacağının** çalışan kaydıdır.
>
> Bu dosya iki bölümdür:
> - **BÖLÜM A — YÖNTEM** (§1–§9): her koşuda uygulanacak adımlar, komutlar, çıktı
>   şablonu, yasaklar.
> - **BÖLÜM B — REFERANS OTURUM** (§10): yöntemin üretildiği pencerenin baştan
>   sona kronolojik kaydı (3 veri paketi, 3 koşu). "Neyi nasıl yaptı" sorusunun
>   birebir cevabı.

---

# BÖLÜM A — YÖNTEM

## §1. Girdi sözleşmesi — her koşuda ÜÇÜ BİRDEN beklenir

| # | Girdi | Nereye yazılır | Zorunlu mu |
|---|---|---|---|
| 1 | `piramit_veri_*.json` paketi (BTC+ETH; 15M+4H kline + OI + funding + taker-LSR) | kanca otomatik açar → `engine/girdi/` ve `engine/girdi/eth/` | **EVET** |
| 2 | CoinGlass **likidasyon** long/short (4S panelden) | `engine/girdi/turev_ham/likidasyon.json` + `engine/girdi/eth/turev_ham/likidasyon.json` | **EVET (elle)** |
| 3 | CoinGlass **görsel okuma** (8 ekran görüntüsü) | `engine/girdi/gorsel_okuma.json` + `engine/girdi/eth/gorsel_okuma.json` | **EVET (elle)** |

**Beklenen 8 görüntü** (referans oturumda hep bu set geldi):
1. BTC 15M Liquidity Heatmap · 2. BTC 4S Liquidity Heatmap · 3. BTC 15M panel
(fiyat+hacim+funding+likidasyon+OI) · 4. BTC 4S panel · 5. ETH 15M Heatmap ·
6. ETH 4S Heatmap · 7. ETH 15M panel · 8. ETH 4S panel.

**TAZELİK:** elle yazılan iki dosya `zaman_utc` damgası taşır. Damga son bardan
**240 dk**'dan eskiyse girdi **BAYAT** sayılır ve kullanılmaz. Kanca kendi
koşusunu bayat girdiyle yapar; bu **her zaman böyledir** — düzeltmek senin işin
(§3).

---

## §2. Kancanın ilk koşusu — NE ANLAMA GELİR

Her istemde `.claude/hooks/piramit_auto.py` (UserPromptSubmit) otomatik çalışır ve:
- gönderilen paketi depoya alır (SHA defteri + "eski paket yeni veriyi geri
  saramaz" korkuluğu),
- türev kanalını üretir,
- boru hattını **o anki** (yani **BAYAT**) görsel/likidasyon ile koşturur,
- iki karar grafiğini basar,
- okunmamış görüntüleri listeler.

⚠️ **Kancanın bu ilk koşusu NİHAİ DEĞİLDİR.** Çıktısında
`⚠ ZORUNLU GİRDİ EKSİK … BAYAT` satırları varsa (referans oturumda 3/3 koşuda
vardı: 10490 dk, 628 dk, 655 dk), o koşu **eksik girdiyle** yapılmıştır ve
kullanıcıya sunulmaz. Sen görüntüleri okuyup taze girdiyle **YENİDEN**
koşturursun.

---

## §3. ADIM ADIM İŞ AKIŞI (atlanamaz, sıra dokunulmaz)

### Adım 0 — Kanca çıktısını oku
Hook çıktısı büyükse `persisted-output` dosyasını **Read** ile tamamen oku.
Şunları not al: paket damgası (`cekim_utc`), son bar, BAYAT gecikmesi (dk),
kancanın ürettiği ilk özet, `hafıza[btc_anlik]` / `hafıza[eth_anlik]`.

### Adım 1 — 8 görüntüyü ELLE oku
`Read` ile hepsini gör (2'şerli paralel çağrılar hızlıdır). Her görüntüden şunlar
çıkarılır:

**Panelden (15M ve 4S ayrı ayrı):** fiyat + % değişim · 24S High/Low/Vol ·
MA(5)/MA(10)/MA(30) · pencere tepesi/dibi · VOL + MA(5)/MA(10) · **Funding
Rates** (değer + şeridin yönü: pozitif/negatif/sarı bar var mı) · **Sembol
Likidasyonları Longs/Shorts** · **Açık Faiz** (4 değer = OHLC + eğrinin yönü).

**Heatmap'ten:** fiyat etiketi · pencere tepesi/dibi · **kalın koyu (mor)
likidite bantlarının fiyat seviyeleri** · kitap ölçeği (sağ üstteki sayı) ·
fiyatın bantlara göre konumu (yol açık mı, tıkalı mı).

### Adım 2 — ÇAPRAZ SORGU (panel ↔ kline) — atlanamaz
Panel 24S High/Low ve pencere uçları, kline'ın **aynı bar** uçlarıyla
karşılaştırılır:

```bash
python3 -c "
import json,datetime
for p,lab in [('engine/girdi/m15.json','BTC15'),('engine/girdi/h4.json','BTC4H'),('engine/girdi/eth/m15.json','ETH15'),('engine/girdi/eth/h4.json','ETH4H')]:
    k=json.load(open(p)); last=k[-1]
    print(lab,'son bar',datetime.datetime.utcfromtimestamp(last[0]/1000),'C',last[4],
          '| son96 max/min',max(float(x[2]) for x in k[-96:]),min(float(x[3]) for x in k[-96:]))
"
```
- **BİREBİR tutuyorsa** → görsel okuma güvenilir, yaz.
- **Tutmuyorsa** → sebebini BUL ve YAZ, gizleme. Referans oturumda iki sebep
  çıktı: (a) borsanın 24S penceresi 96 bardan ~1 saat geniş (100 barlık minimumla
  eşleşti), (b) son bar AÇIK olduğu için panel ile paket 2 dk farklı andan.
- Uydurma açıklama yasak; açıklanamayan sapma **çelişki** olarak raporlanır.

### Adım 3 — İki JSON'u yaz (dört dosya)

`engine/girdi/turev_ham/likidasyon.json` (ve `eth/` eşi):
```json
{
  "liq_long": 0.1131,
  "liq_short": 0.1484,
  "birim": "milyon USD (CoinGlass 4S bar, Sembol Likidasyonları)",
  "kaynak": "CoinGlass Binance BTCUSDT Perpetual 4S — Longs 113.1K / Shorts 148.4K (…yorum…). 15M panelde …",
  "zaman_utc": "YYYY-MM-DD HH:MM",
  "zaman_yerel": "… (cihaz, UTC+3)",
  "damga_kaynagi": "ekran görüntüsü cihaz saati … (UTC+3) → UTC …; paket çekimi … ile aynı dakika; son bar … (N dk)"
}
```
Birim dönüşümü: `259.2` → 0.0002592 · `227.8K` → 0.2278 · `1.2M` → 1.2.

⚠️ **KAPSAM UYARISI kuralı:** 4S barı ekran anında çok yeniyse (15M ve 4S
panelleri **aynı** likidasyon değerini gösteriyorsa, bar birkaç dakikalıktır)
mutlak değerler önemsizdir; `kaynak` alanına açıkça yaz ve çıktıda
"bu koşuda likidasyon skoru gürültüdür" de. (Referans oturum 3. koşu: ETH toplam
345.6 USD.)

`engine/girdi/gorsel_okuma.json` (ve `eth/` eşi) — şema:
```json
{
  "kaynak": "elle-görsel (Claude okuması) + ÇAPRAZ SORGU — CoinGlass … ↔ kline uçları (aynı bar)",
  "sembol": "BTCUSDT", "zaman_dilimi": "15m",
  "trend": "bull | bear | yatay",
  "yapi_olayi": "…15M yapısı + MA dizilimi + 4S dizilimi, sayılarla…",
  "seviyeler": {"direnc": [ … ], "destek": [ … ]},
  "gozlem": ["15M panel: …", "4S panel: …", "15M heatmap: …", "4S heatmap: …",
             "ÇAPRAZ SORGU (panel ↔ kline, aynı bar): …", "Görsel yön okuması: …"],
  "h4_trend": "bull | bear | yatay",
  "celiski_notu": "…uyum durumu + iç kalite uyarıları…",
  "guven": 0.5,
  "zaman_utc": "…", "zaman_yerel": "…", "damga_kaynagi": "…"
}
```

**`trend` alanı nasıl seçilir (dürüstlük kuralı):** `trend` → danışman duruşu
eşlemesi `bull→long`, `bear→short`, **diğer her şey→flat**'tır ve K4'te
`smc_tespit` 15M trendiyle karşılaştırılır. Uyuşmazsa **GÖRSEL-MEKANİK
ÇELİŞKİSİ** düşer ve görsel danışman çürütülür.
**Motoru memnun etmek için trend seçmek YASAKTIR.** Gözün ne görüyorsa onu yaz;
çelişki çıkarsa çıksın — fail-closed tasarımın amacı budur.
`guven` daima `0.50` (tavan; görsel bir ölçüm değildir).

### Adım 4 — State'i geri al ve türevi tazele
Kancanın bayat koşusu gerçek deftere zaten yazdı. Aynı bar iki kez işlenmesin
diye state geri alınır, sonra taze girdiyle **bir kez** koşulur:

```bash
git checkout -- engine/state .claude/skills/piramit-sistem/hafiza

timeout 90 python3 .claude/skills/piramit-sistem/scripts/turev_girdi.py \
  --m15 engine/girdi/m15.json --seri engine/state/turev_seri.jsonl \
  --sembol BTCUSDT --ham engine/girdi/turev_ham --out engine/girdi/turev.json --http

timeout 90 python3 .claude/skills/piramit-sistem/scripts/turev_girdi.py \
  --m15 engine/girdi/eth/m15.json --seri engine/state/eth/turev_seri.jsonl \
  --sembol ETHUSDT --ham engine/girdi/eth/turev_ham --out engine/girdi/eth/turev.json --http
```
Çıktıdaki `funding` değerini panel okumanla karşılaştır (ör. panel %0.0038 ↔
motor 0.003833 → ✔). Tutmuyorsa dur ve sebebini araştır.
Ağ engeli (`fapi.binance.com` CONNECT 403) **normaldir**; kanallar paketin
`turev_ham/` dosyalarından dolar, `_eksikler: []` görmelisin.

### Adım 5 — Boru hattını YENİDEN koştur (ana sembol)

```bash
python3 - <<'EOF'
import json, pathlib
REPO=pathlib.Path('.').resolve(); G=REPO/'engine/girdi'
job={"soru":"otomatik koşu — engine/girdi verisi değişti (taze görsel+likidasyon ile YENİDEN)",
 "sembol":"engine/girdi",
 "veri":{"m15":str(G/'m15.json'),"h4":str(G/'h4.json'),
         "turev":json.loads((G/'turev.json').read_text(encoding='utf-8'))},
 "state_dir":str(REPO/'engine/state'),
 "bar_arsivi":str(REPO/'engine/state/bar_arsivi.jsonl'),
 "defter_dizini":str(REPO/'engine/state'),
 "korelasyon":{"a":str(G/'m15.json'),"b":str(G/'eth/m15.json'),"ad_a":"BTC","ad_b":"ETH"},
 "_hafiza":"GERÇEK — yeni bar, hafıza güncellenir"}
(REPO/'.claude/skills/piramit-sistem/state/_job/otomatik_job.json').write_text(
    json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
EOF

timeout 900 python3 .claude/skills/piramit-sistem/scripts/piramit.py \
  --job .claude/skills/piramit-sistem/state/_job/otomatik_job.json \
  --out .claude/skills/piramit-sistem/state/son_rapor.json --ozet
```
Ana sembolde `gorsel` ve `likidasyon` yolu **verilmez** — K1 varsayılan olarak
`engine/girdi/gorsel_okuma.json` ve `turev_ham/likidasyon.json`'u okur.

### Adım 6 — İkinci sembol (ETH) — korelasyon + sabit-USDT profili BEYAN EDİLİR

```bash
python3 - <<'EOF'
import json, pathlib
REPO=pathlib.Path('.').resolve(); G=REPO/'engine/girdi'; g=G/'eth'; st=REPO/'engine/state/eth'
veri={"m15":str(g/'m15.json'),"h4":str(g/'h4.json'),
      "likidasyon":str(g/'turev_ham/likidasyon.json'),
      "gorsel":str(g/'gorsel_okuma.json'),
      "turev":json.loads((g/'turev.json').read_text(encoding='utf-8'))}
job={"soru":"otomatik koşu — ETH (ana sembolle korelasyonlu) [taze görsel+likidasyon ile YENİDEN]",
 "sembol":"engine/girdi/eth","veri":veri,"state_dir":str(st),"defter_dizini":str(st),
 "bar_arsivi":str(st/'bar_arsivi.jsonl'),"_hafiza":"GERÇEK — yeni bar","_ikinci_sembol":"ETH",
 "korelasyon":{"a":str(G/'m15.json'),"b":str(g/'m15.json'),"ad_a":"BTC","ad_b":"ETH"},
 "usd_profil":str(G/'eth_profil.json')}
(REPO/'.claude/skills/piramit-sistem/state/_job/eth_job.json').write_text(
    json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
EOF

timeout 900 python3 .claude/skills/piramit-sistem/scripts/piramit.py \
  --job .claude/skills/piramit-sistem/state/_job/eth_job.json \
  --out .claude/skills/piramit-sistem/state/son_rapor_eth.json --ozet
```
ETH'de `usd_profil` **koşulsuz** beyan edilir (beyan edilip koşmazsa gözlemci
EKSİK_AKTARIM verir → işlem mühürlenir).

### Adım 7 — Rapordan GERÇEK sayıları çek (uydurma yok)

```bash
python3 - <<'EOF'
import json
def dump(ad,rp):
    r=json.load(open(rp)); ms=r["katmanlar"][1]["motor_sonuclari"]; z=r["ZIRVE"]
    k4=[L for L in r["katmanlar"] if L["katman"].startswith("K4")][0]
    k5=[L for L in r["katmanlar"] if L["katman"].startswith("K5")][0]
    print("#"*70);print("###",ad)
    print("ONCEKI_AKIBET:",json.dumps(z.get("ONCEKI_AKIBET"),ensure_ascii=False)[:500])
    km=ms["karar-motoru"]; print("karar-motoru:",json.dumps(km["karar"],ensure_ascii=False)[:330],
          "| rejim4h:",json.dumps(km.get("rejim_4h"),ensure_ascii=False))
    smc=ms["smc_tespit"]; print("smc15:",smc["trend"],smc["rejim"]["durum"],"adx",smc["rejim"]["adx"],"atr",smc["atr"])
    s4=ms["smc_tespit_h4"]; print("smc4h:",s4["trend"],"adx",s4["rejim"]["adx"],"atr",s4["atr"])
    gc=ms["grafik-calisma"]; print("confluence:",gc["KARAR"],"skor",gc["confluence_skoru"],"bias",gc["yon_bias"],
          "gz",gc["golden_zone"],"sl",gc["gecersizlik_sl"],"hed",gc["hedefler"],"rr",gc["rr"],"kapı",gc["kapi_gerekceleri"])
    tv=ms["turev-akis"]["rapor"]; print("turev:",tv["KARAR_TUREV"],"skor",tv["yon_skoru"],"kapsam",tv["kapsam"],"güven",tv["guven"])
    for f in tv["faktorler"]: print("   ",f["faktor"],f["skor"],f["aciklama"][:95])
    print("   uyarı:",tv["erken_uyari"])
    sd=ms["setup_dogrulama"]; print("setup_dogrulama:",sd["SONUC"],sd["gerekce"],"| perm p",sd["kalibrasyon"]["permutasyon"]["p"])
    print("korelasyon:",ms["korelasyon"]["korelasyon"],ms["korelasyon"]["HUKUM"],"beta",ms["korelasyon"]["beta"])
    print("K4 verifier:",json.dumps(k4["verifier"],ensure_ascii=False)[:520])
    print("K4 çelişki:",json.dumps(k4["celiskiler"],ensure_ascii=False)[:520])
    print("K5 çelişki turu:",json.dumps(k5["celiski_turu"],ensure_ascii=False)[:400])
    print("K5 eşik:",json.dumps(k5["esik_kalibrasyonu"].get("esikler"),ensure_ascii=False),"|",k5["esik_kalibrasyonu"].get("kaynak"))
    rj=k5["esik_kalibrasyonu"].get("rejim") or {}
    print("K5 VR:",json.dumps(rj.get("varyans_orani"),ensure_ascii=False)[:230],"| sertlik",rj.get("sertlik"))
    print("EMIR:",z.get("EMIR"),"|",z.get("EMIR_GEREKCE"))
    for a in (z.get("emir_adaylari") or []): print("   aday:",json.dumps(a,ensure_ascii=False)[:520])
    print("red:",json.dumps(z.get("emir_red_nedenleri"),ensure_ascii=False)[:400])
    print("usd_hedef:",json.dumps(k5.get("usd_hedef"),ensure_ascii=False)[:900])
    print("ZIRVE:",z["YON_BIAS"],z["yon_skoru"],"uzlasi",z["uzlasi"],"kapı",z["kapi_gerekceleri"])
    print("DENETIM:",json.dumps(z.get("DENETIM"),ensure_ascii=False)[:400])
dump("BTC",".claude/skills/piramit-sistem/state/son_rapor.json")
dump("ETH",".claude/skills/piramit-sistem/state/son_rapor_eth.json")
EOF
```

### Adım 8 — HESAP VERME'yi ELLE de doğrula
Motorun `ONCEKI_AKIBET` alanı **tek başına yeterli değildir**; referans oturumda
motorun defteri hatalı çıktı (§10.1). Önceki koşuda seviye verilmişse akıbeti
kendi aritmetiğinle ölç:

```bash
python3 - <<'EOF'
import json,datetime
k=json.load(open('engine/girdi/eth/m15.json'))
G,S,T = 1908.95, 1875.616667, 1953.95      # önceki koşunun giriş/stop/T1'i
BAS   = 1785963600000                       # emrin verildiği barın ms zamanı
sonra=[b for b in k if b[0]>BAS]
mx=max(float(b[2]) for b in sonra); mn=min(float(b[3]) for b in sonra); R=G-S
print("bar:",len(sonra),"(%.2f saat)"%(len(sonra)*0.25))
print("MFE %.2f puan = %+.3fR"%(mx-G,(mx-G)/R), "| MAE %.2f puan = %+.3fR"%(mn-G,(mn-G)/R))
for b in sonra:
    h,l=float(b[2]),float(b[3]); d=datetime.datetime.utcfromtimestamp(b[0]/1000)
    if l<=S and h>=T: print("AYNI BAR stop+hedef →",d,"= STOP"); break
    if l<=S: print("STOP:",d); break
    if h>=T: print("T1:",d); break
else: print("AÇIK — ne stop ne T1")
EOF
```
Kurallar: **tetiklenmediyse İPTAL, R YAZILMAZ**; aynı barda stop+hedef → **STOP**;
sonuçlanmadıysa **AÇIK** denir ve R yazılmaz (MFE/MAE raporlanır).

### Adım 9 — EMİR DOĞDUYSA: İLK-GEÇİŞ ÖLÇÜMÜ (STRATEJI.md §2 kapısı)
`EMİR` `MARKET`/`LIMIT` ile başlıyorsa, emir **işlem önerisi sayılmadan önce**
o koşunun kendi arşivinde ilk-geçiş yarışı ölçülür. Betik:
`.claude/skills/piramit-sistem/scripts/` altında YOKTUR — kum havuzunda yazılır
(referans betik §10.2'de). İki bağımsız yöntem koşulur:

- **A) ANALOG** — arşivdeki her bardan aynı **göreli** stop/hedef mesafeleriyle
  ileri yürünür; arşiv boşluğunu geçen pencere sayılmaz; ufuk 96 bar; aynı barda
  ikisi → STOP.
- **B) BLOK BOOTSTRAP MC** — aynı arşivin 15M log-getirilerinden blok (8)
  yeniden örnekleme, 20000 yol, bar-içi menzil oranları korunur; SEED sabit
  (determinist).
- **C) KOŞULLU ANALOG** — önceden belirlenmiş **TEK** varyant (ör. "son 28 barda
  ≥ +%2 impuls VE fiyat > 30-bar ortalaması"); sonucu ne olursa olsun raporlanır.

**Hüküm kuralı (fail-closed):** iki yöntem **aynı yönde** ve Wilson %95 aralığı
0.50'yi **dışlayacak** biçimde `p_hedef > p_stop` göstermiyorsa → emir
**"işlem önerisi DEĞİL — STRATEJİ: ATLA"**. Ölçüm hiç yoksa → "ÖLÇÜM YOK — taban
stop-favori", yine işlem önerisi sayılmaz.
Taban hatırlatması: adil rassal yürüyüşte `P(stop önce) = hedef/(hedef+stop)`;
R 1.35 için **0.5745** — geometri zaten stop-favoridir.

⚠️ **Aşırı-uyum yasağı:** favorable sonuç çıkana kadar varyant denemek yasaktır.
Varyant sayısı önceden sabitlenir ve **hepsi** raporlanır.

### Adım 10 — ÇİZİM + ELLE İKİNCİ-GÖZ (çıktıdan ÖNCE, atlanamaz)

```bash
python3 - <<'EOF'
import json, pathlib, subprocess, sys, re
REPO=pathlib.Path('.').resolve(); SK=REPO/'.claude/skills/piramit-sistem'
for ad,kline,rap,svg in (("BTCUSDT","engine/girdi/m15.json","son_rapor.json","btc_karar.svg"),
                         ("ETHUSDT","engine/girdi/eth/m15.json","son_rapor_eth.json","eth_karar.svg")):
    z=json.loads((SK/'state'/rap).read_text(encoding='utf-8')).get("ZIRVE") or {}
    oto={"smc":True,"ma":[{"tip":"ema","period":50,"renk":"#ff9800"}]}
    e0=((z.get("emir_adaylari") or [{}])[0] if str(z.get("EMIR","")).startswith(("MARKET","LIMIT")) else None)
    if e0 and None not in (e0.get("giris"),e0.get("stop"),e0.get("hedef")):
        oto["emir"]={"giris":e0["giris"],"stop":e0["stop"],"hedef":e0["hedef"],"yon":str(e0.get("yon","")).lower()}
    cikti=REPO/'engine/cikti'/svg
    job={"veri":{"kline":str(REPO/kline)},"baslik":f"{ad} · 15M · Binance",
         "alt_baslik":f"otomatik SMC katmanı — YÖN: {z.get('YON_BIAS','VERİ YOK')} (skor {z.get('yon_skoru')}) | {str(z.get('EMIR','VERİ YOK'))[:64]}",
         "tema":"koyu","paneller":[{"tip":"hacim","yukseklik":0.12}],"otomatik":oto,"cikti":str(cikti)}
    jp=SK/'state/_job'/f'cizim_{svg}.json'; jp.write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8')
    pr=subprocess.run([sys.executable,str(REPO/'.claude/skills/grafik-cizim/scripts/cizim.py'),'--job',str(jp)],
                      capture_output=True,text=True,cwd=str(REPO))
    print(ad,"rc",pr.returncode,"| emir kutusu:", "VAR" if "emir" in oto else "YOK")
    t=cikti.read_text(encoding='utf-8'); e=re.findall(r'>([^<>]{2,42})</text>', t)
    i=e.index('ÖLÇÜLEN YAPI') if 'ÖLÇÜLEN YAPI' in e else 0
    print("   yapı kutusu:", e[i:i+12]); print("   etiketler:", e[18:56])
EOF
```
**Kontrol listesi (üçü de yazılır):**
- **(a) SAYI TUTARLILIĞI** — çizimdeki altın bölge / giriş / stop / hedef / trend
  / ADX / ATR etiketleri koşu raporuyla **birebir** mi?
- **(b) GEOMETRİ** — giriş açık FVG/teyitli swing üzerinde mi *görünüyor*; stop
  bariz likidite havuzunun İÇİNDE değil ve havuzun >0.25×ATR15 ötesinde mi;
  hedefin önünde görünür duvar var mı? (Emir yoksa: "kutu YOK, EMİR YOK ile
  tutarlı".)
- **(c) YÖN** — emir kutusunun yönü çizilen yapı akışıyla çelişiyor mu?
Herhangi biri tutmazsa **"ÇİZİM-RAPOR ÇELİŞKİSİ"** yazılır ve işlem hükmü
fail-closed tutulur (yön yine gösterilir).
**Bilinen sınır (yaz):** bu ortamda SVG→raster dönüştürücü yok (`rsvg-convert` /
`inkscape` / `cairosvg` yok); ikinci göz raster üzerinden değil, çizimin ürettiği
**etiket/seviye kümesi** + CoinGlass görüntüleri üzerinden yapılır.
**Bilinen etiket farkı:** çizim "R:R x.xx (denetimsiz)" yazar; rapordaki
`rr_denetim` **TUTARLI** olabilir. Sayı aynıysa bu motor çelişkisi değildir —
çizim işine denetim bayrağı geçirilmediği için düşen varsayılan etikettir; yaz.

### Adım 11 — Metin denetimi (uydurma sayıya karşı korkuluk)
Cevabı bir dosyaya yaz, sonra:
```bash
python3 .claude/skills/piramit-sistem/scripts/iddia_denetle.py \
  --metin <cevap.md> \
  --rapor .claude/skills/piramit-sistem/state/son_rapor.json \
  --rapor .claude/skills/piramit-sistem/state/son_rapor_eth.json
```
`KAYNAKSIZ` çıkan her sayı ya rapordan düzeltilir ya metinden çıkarılır **ya da**
rapor-dışı **adlandırılmış** kaynağı metinde açıkça gösterilir (`durum.json`
takip bloğu, `h4.json` üzerindeki kendi aritmetiğin, `bar_arsivi.jsonl`,
`eth_profil.json`, kanca çıktısı…). Araç **anlam** denetlemez; yorum doğruluğu
elle ikinci-göz işidir.

### Adım 12 — Commit + push
```bash
git add -A && git commit -q -F - <<'EOF'
veri: <YYYY-MM-DD HH:MM> UTC paketi + CoinGlass panel okuması, piramit yeniden koşuldu

- 8 CoinGlass ekran görüntüsü elle okundu → gorsel_okuma.json ve likidasyon.json
  taze damgayla yazıldı (zaman_utc …, son bardan N dk).
- Otomatik koşu zorunlu girdileri BAYAT (N dk) gördüğü için boru hattı taze
  girdilerle yeniden koşturuldu; state ilk koşu öncesine döndürülüp bar tek kez
  işlendi.
- Sonuç: …
- Karar grafikleri yeniden basıldı.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF

for i in 1 2 3 4; do git push -u origin <dal> && break; s=$((2**i)); sleep $s; done
```
Ardından iki SVG `SendUserFile` ile (`display: "render"`) gönderilir.

---

## §4. ÇIKTI ŞABLONU (10 başlık — sıra değişmez)

```
① HESAP VERME            önceki koşunun seviyeleri ne oldu (İPTAL / STOP / T1 / AÇIK);
                          R yalnız sonuçlandıysa yazılır. Motorun defteriyle KENDİ
                          ölçümün çelişiyorsa ikisi de yazılır.
② KIYAS                   tablo: yön, fiyat, yapı yönü, ADX, ATR, türev skoru,
                          taker LSR, ρ … + "tek cümlede" özet.
③ MOTORLAR                karar-motoru / smc_tespit(15M+4H) / confluence /
                          turev-akis(5 faktör tek tek) / setup_dogrulama /
                          korelasyon / eşik kalibrasyonu — hepsi dosyadan okunan
                          gerçek sayılarla.
④ 5 DANIŞMAN MERCEĞİ      Muhalif / İlk-Prensipler / Genişletici / Dış-Göz /
                          Uygulayıcı — her biri BİR motora bağlı; anlatı için
                          sayı uydurma.
⑤ GÖRSEL OKUMA            damga + tazelik, ZORUNLU GİRDİ durumu, çapraz sorgu
                          sonucu, panelden okunanlar, likidite haritası,
                          görsel-mekanik teyit/çelişki.
⑥ YÖN (bias)              LONG / SHORT / NÖTR + yon_skoru + uzlaşı + çelişki turu.
⑦ İŞLEM KALİTESİ + EMİR   temiz giriş var mı; emir varsa tam satır + rr_denetim +
                          usd_hedef kapıları; yoksa gerekçe. Motorun BEKLE'ye
                          bastırdığı kurulumun kendi seviyeleri de verilir
                          ("işlem önerisi değil" etiketiyle).
⑧ STRATEJİ SÜZGECİ        TEK BAHİS (ρ) / EKLEME YASAĞI / TAZE EMİR GEOMETRİ
                          KAPISI (ilk-geçiş ölçümü) / STOP-AV / FUNDING-BAYAT /
                          SERMAYE NOTU. Hüküm: "işlem önerisi" ya da "ATLA".
⑨ ÇİZİM + İKİNCİ GÖZ      (a)(b)(c) kontrol listesi + sınırlar + gözlemci sayıları.
⑩ GERÇEK / VARSAYIM / YORUM   üç kategori ayrı ayrı; YORUM açıkça etiketli.
```
En sonda daima: `⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.`

---

## §5. HÜKÜM SÖZLÜĞÜ — hangi çıktı ne demek

| Motor çıktısı | Anlamı | Ne yapılır |
|---|---|---|
| `YÖN (bias): LONG/SHORT` | ağırlıklı kanıtın yönü, **kapıdan bağımsız** | daima gösterilir, gizlenmez |
| `YÖN: NÖTR` (skor tam 0.0) | gerçek berabere — danışmanların hiçbiri yön üretmedi | "kaçamak değil" diye açıkla |
| `İŞLEM KALİTESİ: TEMİZ GİRİŞ YOK` | kalite hükmü, **yön reddi değil** | seviye bekleme gerekçesi yazılır |
| `EMİR YOK — DENETİM MÜHÜRÜ` | gözlemci kritik ihlal buldu | yön gösterilir, **mühür elle delinmez** |
| `ÇELİŞKİ TURU: yön DAYANIKSIZ` | yalnız doğrulanmış danışmanlarla yön değişiyor | fail-closed NÖTR |
| `esik_kaynagi: STATİK KORKULUK` | eşik türetilemedi (yönlü danışman < 2) | açıkça etiketle |
| `esik_kaynagi: VERİDEN TÜRETİLDİ` | bootstrap + çoğunluk × rejim sertliği | eşik değerlerini yaz |
| `setup_dogrulama: VERİ YETERSİZ` | işlem sayısı < 10 | Dış-Göz merceği izin VERMİYOR |
| `korelasyon HUKUM: KOPYA POZİSYON` | \|ρ\| ≥ 0.85 → çarpan 2.0 | TEK BAHİS kuralı bağlar |
| `korelasyon HUKUM: GÜÇLÜ BAĞLI` | 0.80 ≤ \|ρ\| < 0.85 → çarpan 1.5 | bağımsız bahis değil, ama TEK BAHİS eşiği aşılmadı |

---

## §6. SERT YASAKLAR (referans oturumda hepsi test edildi)

1. **Bayat girdiyle karar sunma.** Kancanın BAYAT koşusu kullanıcıya verilmez.
2. **Motoru memnun etmek için `trend` seçme.** Göz ne görüyorsa o yazılır.
3. **Aşırı-uyum.** İlk-geçiş varyantları önceden sabitlenir, hepsi raporlanır.
4. **Tetiklenmemiş işleme R yazma.** İPTAL denir.
5. **Mührü elle delme.** Gözlemci ihlali varsa işlem yok — seviye uydurulmaz.
6. **Uydurma sayı.** `iddia_denetle.py` korkuluktur; anlam denetimi elle.
7. **Motorun defterine körü körüne güvenme.** Referans oturumda defter hatalıydı
   (§10.1); kritik akıbet iddiaları elle doğrulanır.
8. **Aynı barı iki kez deftere işleme.** Yeniden koşmadan önce `git checkout --
   engine/state .claude/skills/piramit-sistem/hafiza`.
9. **Motor kodunu analiz sırasında değiştirme.** Bulunan hata **raporlanır**,
   karar mekaniği aynı koşuda değiştirilmez.

---

## §7. BİLİNEN AÇIK SORUNLAR (her koşuda taşınır, unutulmaz)

### 7.1 `FVG_MITIGASYON = 0.50` — KALİBRE EDİLMEMİŞ
`karar_motoru` + `smc_tespit` sabiti. Consequent-encroachment konvansiyonuna
dayanır, **edge kanıtına değil**. Ölçülen durum: 182 kayan pencerede 0.5 vs 1.0 →
0 karar farkı; 0.5 vs 0.0 → 3 pencere farklı ve **üçünde de 0.0 daha iyi**.
Geniş tarihsel set gerekiyor (data.binance.vision arşivi; `fapi.binance.com` bu
ortamda 403 ama arşiv alan adı ayrı, denenmeli).
**Referans oturumda 2. ve 3. koşuda İKİ SEMBOLDE de dönüş dizisi 4/4 tamamlandı
ve kurulumu tam olarak bu eşik öldürdü.** Yani artık tek seferlik değil,
sistematik kesme noktası — her çıktıda VARSAYIM olarak beyan et.

### 7.2 `durum.json` defter hatası — 15M arşiv boşluğu
BTC'nin 2026-07-27 23:30 SHORT'u (giriş 64364.0 / stop 64790.3 / T1 63567.0 /
T2 63298.25 / R 1.87) defterde hâlâ **"T2 bekliyor — pozisyon AÇIK"**.
4H serisiyle doğrulandı: tetik 07-29 04:00 (H 64544.0), T1 07-29 16:00
(L 63483.9), **T2 07-29 20:00 (L 63234.0)** → kurulum kapandı.
Sebep: 15M `bar_arsivi.jsonl`'de **2026-07-29 03:30 → 2026-08-03 08:45 arası
7515 dakikalık (5.2 gün) boşluk** — T2'nin bastığı barlar arşivde yok.
Karar yönünü değiştirmez ama **sicili ve ağırlık öğrenmesini kirletir.**
Her koşuda hâlâ açıksa tekrar bildir.

---

## §8. ORTAM NOTLARI

- `fapi.binance.com` → CONNECT 403 (proxy). Normal; kanallar paketin
  `turev_ham/` dosyalarından dolar. `--http` yine verilir (mandal tek yönlü).
- SVG→raster dönüştürücü YOK. İkinci göz etiket kümesi üzerinden.
- Kum havuzu (geçici betikler) için scratchpad dizini kullanılır, `/tmp` değil.
- Kanca her istemde koşar; paket SHA defteriyle iki kez alınmaz, eski paket yeni
  veriyi geri saramaz.

---

## §9. HIZLI KONTROL LİSTESİ (koşu bitmeden hepsi ✔ olmalı)

- [ ] Kanca çıktısı tam okundu, BAYAT gecikmesi not edildi
- [ ] 8 görüntünün **hepsi** okundu
- [ ] Çapraz sorgu yapıldı, sapma varsa **sebebi bulundu**
- [ ] 4 JSON yazıldı (2 görsel + 2 likidasyon), `zaman_utc` damgalı
- [ ] Likidasyon barı taze mi diye bakıldı (kapsam uyarısı gerekiyor mu)
- [ ] `git checkout -- engine/state …` yapıldı (çift işleme yok)
- [ ] `turev_girdi.py` iki sembol için koştu, funding panel ile eşleşti
- [ ] `piramit.py` iki sembol için koştu, **ZORUNLU GİRDİ EKSİK satırı YOK**
- [ ] HESAP VERME elle de ölçüldü
- [ ] Emir doğduysa ilk-geçiş ölçümü koştu (3 yöntem, hepsi raporlandı)
- [ ] Çizim basıldı, (a)(b)(c) ikinci-göz yapıldı
- [ ] `iddia_denetle.py` koştu, KAYNAKSIZ sayıların kaynağı metinde gösterildi
- [ ] 10 başlıklı şablonla yazıldı, sonda karar-destek uyarısı var
- [ ] Commit + push yapıldı, iki SVG gönderildi

---

# BÖLÜM B — REFERANS OTURUM (kronolojik, eksiksiz)

Bu pencerede 3 veri paketi geldi. Her biri aynı yöntemle işlendi. Aşağıda ne
geldiği, ne yapıldığı, motorun ne dediği ve ne raporlandığı sırayla verilmiştir.

---

## §10.0 Oturum başlangıcı

- `SessionStart` kancası: `[PİRAMİT] Boru hattı hazır (K1→K5)` +
  `[SAĞLIK] ✔ SAĞLAM — motor 19/19 yerinde, bağımlılık 3/3, kanca 2/2, girdi/görev OK`
- Devir-teslim hafızası: BTCUSDT/ETHUSDT son bar `2026-07-25 13:45`, ikisi de
  LONG; ETH'de `LIMIT LONG @1863.68 | stop 1830.346667 | T1 1908.68 | R 1.35`.
- Anlık hafıza: son bar `2026-07-29 03:30`, BTC NÖTR (0.0), ETH SHORT (−0.8277)
  seviyeler `giris 1898.44 / stop 1931.773333 / hedef 1853.44`.

---

## §10.1 KOŞU 1 — paket `piramit_veri_BTC_ETH_20260805_1032.json` (çekim 10:32:54 UTC)

**Kullanıcı:** 8 CoinGlass görüntüsü + paket, "yeni veriler analize basla".

**Kancanın ilk koşusu (BAYAT):**
- `ZORUNLU GİRDİ EKSİK: likidasyon BAYAT (10490 dk), görsel okuma BAYAT (10490 dk)`
- BTC NÖTR (0.0), ETH NÖTR (0.0), EMİR YOK. Gözlemci 26/0 ihlal/3 uyarı.

**Yapılanlar:**
1. 8 görüntü okundu. BTC 15M panel: fiyat 64157 (+1.07%), 24S 63436–64513,
   MA5 64145.71 / MA10 64140.53 / MA30 64169.56 (**29 puan sıkışma**), VOL 5.5M
   vs MA10 36.8M, funding %0.0038, OI 107.3K, likidasyon Longs --/Shorts --.
   BTC 4S: MA5 64141.63 > MA10 63963.10 > MA30 63362.62, likidasyon
   **Longs 113.1K / Shorts 148.4K**, OI 107.8K→107.3K.
   ETH 15M: 1872.09 (+0.91%), MA5 1871.67 / MA10 1870.92 / MA30 1869.10
   (**2.6 puan**), funding %0.001 (tepeden iniyor), OI 2.3M.
   ETH 4S: MA5 1870.81 > MA10 1868.48 > MA30 1864.24, likidasyon
   **Longs 9.2K / Shorts 75.0K**.
   Heatmap: BTC 15M'de 64400 + 64500 **çift kalın bant**; ETH 15M'de 1872–1882
   neredeyse tamamen dolu.
2. **Çapraz sorgu:** BTC tepe 64513 ↔ kline 64512.9 ✔, 15M dip 63582.1 ✔,
   4H dip 62228.8 ✔. **Sapma:** panel 24S dipleri (BTC 63436 / ETH 1854.61)
   96 barlık pencerede yok → **100 barlık pencerede** BTC min 63428.8 /
   ETH min 1853.22 bulundu → borsanın 24S penceresi ~1 saat geniş. Açıklandı,
   çelişki sayılmadı.
3. Dört JSON yazıldı, damga `2026-08-05 10:32` (son bar 10:30 → 2 dk).
   `trend`: BTC **yatay**, ETH **yatay** (MA'lar iç içe olduğu için — dürüst
   okuma; motorun bull/bear demesine rağmen değiştirilmedi).
4. `git checkout -- engine/state …` → türev yeniden üretildi (funding 0.003833 ↔
   panel %0.0038 ✔; ETH 0.00092 ↔ %0.001 ✔) → boru hattı iki sembol için
   yeniden koşuldu.

**Sonuç (taze girdiyle):**
- **BTC NÖTR** — yon_skoru 0.0, uzlaşı 1.0; 4 danışman: karar-motoru 0.4 /
  grafik-calisma 0.85 / turev-akis 0.203 / gorsel-teyit 0.5, **hiçbiri yönlü değil**.
- **ETH NÖTR** — aynı şekilde 0.0.
- Motorlar: BTC `karar-motoru` BEKLE (zincir 4, "4H rejim UP ama fiyat hizasında
  açık FVG yok"), rejim UP 562.62/eşik 557.874; `smc_tespit` 15M bull/range
  ADX **8.15** ATR **101.85**; `confluence` skor 0.85, altın bölge
  64098.3926–64123.7438, **R:R 0.473**; `turev-akis` skor −0.003 kapsam 1.00
  (OI −%1.10 → −0.6, CVD +%4.8 → +0.7, LSR 1.0829 → +0.5, likidasyon dengeli);
  `setup_dogrulama` VERİ YETERSİZ (5 işlem, perm p 0.8955).
  ETH: BEKLE (zincir 4, 4H rejim FLAT 5.59/eşik 22.72); smc15 bear ADX 13.98
  ATR 3.51; confluence bias bear, altın bölge 1871.461–1873.897, **R:R 0.506**,
  iki kapı (MTF hizasızlık + R:R); turev skor −0.006.
- **ρ = 0.9085** (beta 1.0326, R² 0.8254) → **KOPYA POZİSYON**, çarpan 2.0.
- Eşikler: ikisinde de **STATİK KORKULUK** (0.15 / 0.55 / 0.6).
- Gözlemci: BTC 25/0 ihlal/2 uyarı, ETH 26/0 ihlal/2 uyarı.

**HESAP VERME:** ETH'nin önceki SHORT seviyeleri (1898.44 / 1931.773333 /
1853.44) → **İPTAL (bölgeye dokunulmadı) — R YAZILMADI**. BTC: VERİ YOK.

**🔴 BULUNAN HATA (§7.2):** `durum.json` BTC'nin 07-27 SHORT'unu "T2 bekliyor —
pozisyon AÇIK" gösteriyordu. 4H serisiyle elle ölçüldü: tetik 07-29 04:00
(H 64544.0), T1 07-29 16:00 (L 63483.9), **T2 07-29 20:00 (L 63234.0)**.
Sebep: 15M arşivinde **7515 dakikalık boşluk**. Raporlandı, kod değiştirilmedi.

**Çizim/ikinci-göz:** BTC "BULL / range · 8.15", altın bölge 64.123,74 –
64.098,39 ✔ birebir; ETH "BEAR / range · 13.98", 1.871,46 – 1.873,90 ✔; emir
kutusu yok (EMİR YOK ile tutarlı).

**Commit:** `1fbfb26`.

---

## §10.2 KOŞU 2 — paket `piramit_veri_BTC_ETH_20260805_2105.json` (çekim 21:05:49 UTC)

**Kancanın ilk koşusu (BAYAT 628 dk):** BTC NÖTR, ETH **LONG 0.6612** +
`MARKET LONG @1908.95`.

**Yapılanlar:** aynı 12 adım. Görüntü damgası `2026-08-05 21:05` (son bar 21:00
→ 5 dk).
- BTC 15M: 64766 (+0.75%), 24S 63847–65022, MA5 64872.38 > MA10 64852.16 >
  MA30 64659.96, VOL 48.3M vs MA10 103.5M, funding %0.0011 **sonda negatif
  (sarı) bara döndü**, likidasyon 15M Longs 70.9K, **OI 108.8K → 107.4K**.
  BTC 4S likidasyon **Longs 107.5K / Shorts 1.2M (short 11.2× baskın)**.
- ETH 15M: 1908.54 (+1.82%), 24S 1854.51–1927.19, MA5 1917.46 ≈ MA10 1917.60,
  VOL 102.8M vs MA10 55.7M (**ortalama ÜSTÜ, kırmızı bar**), funding %0.005
  **yükseliyor**, likidasyon 15M Longs 615.4K. ETH 4S likidasyon
  **Longs 685.2K / Shorts 181.5K (long 3.8×)**.
- Çapraz sorgu **tamamı birebir** (65022.0 / 63847.0 / 64758.10; 1927.19 /
  1854.51 / 1909.00).
- `trend`: bu kez **ikisi de bull** (63847→65022 kesintisiz impuls; 1854.51→
  1927.19 = %3.92).

**Sonuç:**
- **BTC: YÖN LONG (0.1546)** ama **ÇELİŞKİ TURU DAYANIKSIZ** (tüm kurul LONG,
  doğrulanmış 1 danışmanla NÖTR) → fail-closed + gözlemci **1 İHLAL**
  `K5-SI/MEMNUN_ETME` → **EMİR YOK — DENETİM MÜHÜRÜ**. Kapı ayrıca
  "yön ağırlığı 0.12 < 0.6".
- **ETH: YÖN LONG (0.7716)**, eşikler **VERİDEN TÜRETİLDİ** (score 0.5617 /
  agreement 0.6178 / side_weight 0.7774; sertlik 1.2356) → kapı geçildi.
  **EMİR: `MARKET LONG @1908.95 | stop 1875.616667 | T1 1953.95 | R 1.35`**,
  `rr_denetim` TUTARLI, `usd_hedef` **6/6 kapı UYGUN** (stop 1.4035×ATR, hedef
  2.1053×ATR, tasfiye 133.3333 puan, gerçek kaldıraç 14.32, net kazanç
  130.42–145.42 USDT). Alternatif 3 LIMIT adayının **hepsi STOP-AV bayraklı**.
  Gözlemci 0 ihlal; uyarı: *"doğrulanmış kanıt yalnız {'gorsel'} ailesinden"*.
- Motorlar: iki sembolde de `karar-motoru` **zincir 1**, "dönüş dizisi 4/4 TAMAM
  (LONG) ama FVG mitige → kurulum BAYAT" (→ §7.1). BTC smc15 **bear** ADX 27.73;
  confluence BTC bias **bear** **R:R 3.247** (yalnız MTF hizasızlığı reddetti);
  ETH smc15 bull ADX 36.05, confluence bias bull R:R 1.876.
  `turev-akis`: BTC +0.171 (likidasyon +0.8 squeeze, taker LSR 0.3519 → −0.5);
  ETH +0.271 (**OI↑%1.06 + fiyat↑ → +1.0 taze LONG**, CVD +%176.2, likidasyon
  −0.8). ρ **0.8546** → KOPYA POZİSYON.
- Görsel-mekanik: ETH **UYUMLU (doğrulandı)**, BTC **ÇELİŞKİ** (göz bull,
  algoritma bear).

**İLK-GEÇİŞ ÖLÇÜMÜ (bu koşuda yazıldı; §9'un referansı):**
Girdi: ETH `bar_arsivi.jsonl` (848 bar, kesintisiz ~8.8 gün; 5.2 günlük boşluk
dışlandı), ufuk 96 bar, aynı barda stop+hedef → STOP.

| yöntem | p_hedef | p_stop | n | Wilson %95 (p_hedef) |
|---|---|---|---|---|
| ANALOG | 0.5229 | 0.4771 | 503 | **[0.4792, 0.5662]** → 0.50'yi içeriyor |
| MC blok bootstrap (20000 yol, blok 8) | **0.4681** | **0.5319** | 13489 | [0.4597, 0.4765] → 0.50 altında, anlamlı |
| Koşullu analog (≥+%2 impuls + fiyat>MA30) | 0.0 | 1.0 | **2** | [0.0, 0.6576] → VERİ YETERSİZ |

Taban: R 1.35 → `P(stop önce) = 0.5745`.
**Hüküm: iki yöntem ters işaret → sağlam değil → STRATEJİ: ATLA** (emir ve yön
yine gösterildi).

**Çizim/ikinci-göz:** ETH kutusu **LONG 1.908,95 / Stop 1.875,62 / Hedef
1.953,95** ✔ raporla birebir; altın bölgeler ✔. **(b) kısmi uyarı:** giriş
"güncel fiyat (MARKET adayı)" — yapı üzerinde değil; hedefe giden yolda 1920
bandı + 1927.19 + 1940 var. **Etiket farkı:** çizim "R:R 1.35 (denetimsiz)",
rapor `rr_denetim` TUTARLI — açıklandı.

**Commit:** `ff8651a`.

---

## §10.3 KOŞU 3 — paket `piramit_veri_BTC_ETH_20260806_0810.json` (çekim 08:10:13 UTC)

**Kancanın ilk koşusu (BAYAT 655 dk):** BTC NÖTR, ETH NÖTR.

**Yapılanlar:** aynı akış. Görüntü damgası `2026-08-06 08:08` (son bar 08:00 →
8 dk). **Yeni durum:** 08:00 barı hem panelde hem pakette **AÇIK** — panel
08:08'de, paket 08:10:13'te alındı; BTC panel fiyatı 64811 vs kline kapanış
64765.00 (46 puan). Sapma değil, **aynı ana ait değil** diye not edildi.

**⚠ Likidasyon kapsam sorunu (yeni ders):** 4S barı ekran anında ~9 dakikalıktı;
**15M ve 4S panelleri aynı değeri gösterdi** → BTC Longs 259.2 USD /
Shorts 227.8K USD; ETH Longs 30.5 / Shorts 315.1 USD (toplam **345.6 USD**).
Değerler doğru yazıldı ama `kaynak` alanına **KAPSAM UYARISI** eklendi ve
çıktıda "`turev-akis` bu koşuda likidasyonu +0.8 skorladı, **bu gürültüdür**"
denildi.

**Sonuç:**
- **BTC NÖTR (0.0)** ve **ETH NÖTR (0.0)** — dört danışman da flat; kapı
  "|skor| 0.00 < eşik 0.15"; çelişki turu **DAYANIKLI**; **EMİR YOK** (ikisinde).
- Motorlar: `karar-motoru` **üçüncü kez** zincir 1 "4/4 TAMAM ama FVG mitige"
  (BTC 64772.3 süpürüldü ce=64775.4; ETH 1906.16 süpürüldü ce=1908.8) → §7.1.
  BTC smc15 bull/range ADX **18.46** ATR 94.74216823; confluence skor **1.0**
  bias bull, altın bölge 64511.5756–64609.9228, **R:R 0.489**.
  ETH smc15 bear ADX **18.28** ATR 4.29968911; confluence skor 0.85 bias bear,
  altın bölge 1911.09792–1912.34784, **R:R 0.747**.
  `turev-akis` ikisinde de **+0.117** (OI BTC −%1.72 / ETH −%3.00 → −0.6;
  CVD +0.7; taker LSR **1.0776 / 1.1956** → +0.5; likidasyon +0.8 = gürültü);
  uyarı **DELEVERAGING + SOĞUMA**.
  `setup_dogrulama` VERİ YETERSİZ (4 ve 3 işlem).
- **ρ 0.8434** → hüküm **KOPYA POZİSYON → GÜÇLÜ BAĞLI**, çarpan 2.0 → **1.5**
  (TEK BAHİS eşiği 0.85 bu koşuda aşılmadı).
- Eşikler: ikisinde de STATİK KORKULUK. Rejim VR: BTC 0.5408 (z −2.031,
  anlamlı), ETH 0.8555 (z −0.626, anlamsız).
- Görsel-mekanik: gözüm **ikisinde de yatay**, algoritma BTC bull / ETH bear →
  **iki tarafta da çelişki**, görsel danışman çürütüldü.
- Gözlemci: BTC 25/0 ihlal, ETH 26/0 ihlal.

**HESAP VERME (2. koşunun ETH emri):**
`MARKET LONG @1908.95 | stop 1875.616667 | T1 1953.95` → 44 bar / 11 saat sonra
**AÇIK — ne stop ne T1, R YAZILMADI**. MFE 1917.99 = **+0.271R**, MAE 1893.62 =
**−0.460R**, o anki fiyat 1908.74 = **−0.006R**. Motorun kendi ölçümü de aynı
("AÇIK — çıkış henüz olmadı; sonraki koşuda ölçülür").
Defter hatası (§7.2) **üçüncü kez** doğrulandı, hâlâ açık.

**Çizim/ikinci-göz:** BTC "BULL / range · 18.46 / ATR 94.74", altın bölge
64.609,92 – 64.511,58 ✔; ETH "BEAR / range · 18.28 / ATR 4.30", 1.911,10 –
1.912,35 ✔; iki grafikte de kutu YOK ✔.

**Commit:** `307e3d9`.

---

## §10.4 Üç koşunun karşılaştırmalı tablosu

| | Koşu 1 (08-05 10:30) | Koşu 2 (08-05 21:00) | Koşu 3 (08-06 08:00) |
|---|---|---|---|
| BTC fiyat | 64166.20 | 64758.10 | 64765.00 |
| ETH fiyat | 1872.27 | 1908.95 | 1908.74 |
| BTC ADX / ATR | 8.15 / 101.85 | 27.73 / 136.38 | 18.46 / 94.74 |
| ETH ADX / ATR | 13.98 / 3.51 | 36.05 / 6.91 | 18.28 / 4.30 |
| BTC yön | NÖTR 0.0 | **LONG 0.1546 (MÜHÜRLÜ)** | NÖTR 0.0 |
| ETH yön | NÖTR 0.0 | **LONG 0.7716** | NÖTR 0.0 |
| ETH emir | yok | **MARKET LONG @1908.95** | yok |
| Strateji süzgeci | — | **ATLA** (ilk-geçiş sağlam değil) | — |
| ρ / hüküm | 0.9085 KOPYA | 0.8546 KOPYA | 0.8434 GÜÇLÜ BAĞLI |
| Eşik kaynağı | statik / statik | statik / **veriden** | statik / statik |
| Gözlemci ihlal | 0 / 0 | **1 (BTC)** / 0 | 0 / 0 |
| Zorunlu girdi | taze (2 dk) | taze (5 dk) | taze (8 dk) |

**Üç koşunun dersi:** yön üç kez de kanıtla değişti, ama **hiçbirinde işlem
önerisi doğmadı** — biri mühürle, biri strateji süzgeciyle, ikisi yön yokluğuyla
düştü. "EMİR YOK" birinci sınıf çıktıdır; sinyal avcılığı yapılmaz.

---

## §10.5 Bu oturumda kullanıcıya verilen çıktıların iskeleti

Her koşuda kullanıcıya gönderilenler:
1. 10 başlıklı Markdown analiz (§4 şablonu),
2. `engine/cikti/btc_karar.svg` + `engine/cikti/eth_karar.svg`
   (`SendUserFile`, `display: "render"`),
3. commit kimliği + dal adı,
4. `⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.`

---

*Bu dosya `analiz2` tetikleyicisinin tek hedefidir. Yöntem değişirse burası
güncellenir; başka yere yöntem yazılmaz.*
