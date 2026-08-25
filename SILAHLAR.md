# SİLAH DEFTERİ — depodaki bütün "komut"lar, alt başlıklarıyla

> Kaynak: bu depo (ölçüldü, hafızadan yazılmadı).
> `.claude/skills/` dizin listesi, `piramit.py` **MOTOR** kayıt tablosu,
> her betiğin modül docstring'i + `argparse` argümanları, `.claude/settings.json`
> kanca kaydı. Doğrulama: `python3 .claude/skills/piramit-sistem/scripts/saglik.py --hizli`
> → `SAĞLAM — motor 20/20 yerinde, bağımlılık 3/3, kanca 3/3, girdi/görev OK`.
>
> ⚠️ **Bu depoda slash komutu YOKTUR** — `.claude/commands/` dizini yok.
> Bütün "silahlar" ya kanca ile **tetikleyicisiz** koşar ya da beceri olarak
> otomatik devreye girer. Aşağıdaki CLI satırları elle koşu (kum havuzu/onarım)
> içindir; normal akışta kullanıcı hiçbir komut yazmaz.
>
> ⚠️ Yalnız karar-destek; canlı/otomatik emir (gerçek para) DAHİL DEĞİL.

---

## 1) KANCALAR — komutsuz tetikleyiciler (`.claude/settings.json`)

| Kanca | Dosya | Ne yapar |
|---|---|---|
| `SessionStart` | `.claude/hooks/session-start.sh` | Oturum açılışında sağlık kontrolü + piramit hazır bildirimi |
| `SessionStart` | `.claude/hooks/superpowers-session-start.sh` | `using-superpowers` içeriğini bağlama enjekte eder (bu depoda koşulsuz DEĞİL — öncelik `CLAUDE.md`) |
| `UserPromptSubmit` (timeout 900 sn) | `.claude/hooks/piramit_auto.py` | Her istemde: yeni paketi al (`paket_ac`) → türev girdisi üret (`turev_girdi`) → boru hattını koştur (`piramit.py`) → karar grafiklerini bas (`cizim.py`) → iki-satır özeti bağlama basar |

---

## 2) BORU HATTI — tek orkestratör

```
python3 .claude/skills/piramit-sistem/scripts/piramit.py --job <job.json> [--out rapor.json] [--ozet]
```

Katman sırası: **K1-LLM → K2-AI-AJAN → K3-COKLU-AJAN → K4-AGI → K5-SI**
(`KATMANLAR`, `piramit.py:132`). Her katmanın bir **kapısı** vardır; kapı
kapanırsa boru hattı orada durur ve durduğu katman gizlenmez.

---

## 3) KAYITLI MOTORLAR (20) — katmana göre

Kaynak: `piramit.MOTOR` tablosu (tek kaynak; sağlık kontrolü de buradan sayar).
Motorların çoğu `--job <json>` alır; boru hattı job'u stdin ile besler.

### 3.1 K1 — LLM katmanı (ham veri + bütünlük; çıkarım YOK)

| Motor | Yol | CLI argümanları |
|---|---|---|
| `profile_data` | `data-analysis-deep-scan/scripts/profile_data.py` | `--input --sheet --delimiter --top-n --redact-values --correlation-threshold --output` |
| `verify_data` | `data-analysis-deep-scan/scripts/verify_data.py` | `--contract --input --output` |
| `video_isle` | `video-isleme/scripts/video_isle.py` | `--job` (ffmpeg yoksa kendisi kurar) |

### 3.2 K2 — AI ajan katmanı (tek ajan + araç; motorlar birbirini görmez)

| Motor | Yol | CLI argümanları |
|---|---|---|
| `karar_motoru` | `engine/karar_motoru.py` | `--m15 --h4 --state-dir` |
| `smc_tespit` | `grafik-calisma/scripts/smc_tespit.py` | `--job` |
| `confluence` | `grafik-calisma/scripts/confluence.py` | `--job` |
| `setup_dogrulama` | `grafik-calisma/scripts/setup_dogrulama.py` | `--job` |
| `korelasyon` | `piramit-sistem/scripts/korelasyon.py` | `--a --b --ad-a --ad-b --min-gozlem` |
| `turev_akis` | `turev-akis/scripts/turev_akis.py` | `--job --emit-advisor` |
| `backtest` | `backtest-motoru/scripts/backtest.py` | `--job` |

K2 kapısı: en az **2** bağımsız kanıt ailesi sayısal sonuç üretmeli
(`KONVANSIYON["min_motor_k2"] = 2`, `piramit.py:118`). K3 kapısı: en az **2** ölçülen danışman (`min_danisman_k3`).

### 3.3 K3 — çoklu-ajan katmanı (danışman kurulu)

Alt-süreç motoru **yok**: kurul K1+K2 çıktılarından ve öğrenilmiş ağırlıktan
(`piramit-sistem/hafiza/agirlik.json`, `agirlik_eth.json`) kurulur. Kapı: en az 2 **ölçülen** danışman.

### 3.4 K4 — AGI katmanı (çelişki + fail-closed doğrulama)

| Motor | Yol | CLI argümanları |
|---|---|---|
| `rr_denetim` | `karar-kurulu/scripts/rr_denetim.py` | `--job` (ATR-ölçekli "şişirilmiş R" panzehiri) |

Ayrıca korelasyon burada risk çarpanına çevrilir (|ρ| ≥ 0.85 → KOPYA POZİSYON).

### 3.5 K5 — SI katmanı (güven-ağırlıklı sentez + kalibrasyon)

| Motor | Yol | CLI argümanları |
|---|---|---|
| `esik_kalibre` | `piramit-sistem/scripts/esik_kalibre.py` | `--job` (kapılar sentezden ÖNCE veriden türetilir) |
| `sentez` | `karar-kurulu/scripts/sentez.py` | `--job` (çoğunluk oyu değil, güven-ağırlıklı) |
| `risk` | `risk-yonetimi/scripts/risk.py` | `--job` |
| `portfolio` | `portfoy-optimizasyonu/scripts/portfolio.py` | `--job` |

### 3.6 Zirve sonrası — karar → emir → sicil

| Motor | Yol | CLI argümanları | Rol |
|---|---|---|---|
| `sentez` (2. koşu) | `karar-kurulu/scripts/sentez.py` | `--job` | **ÇELİŞKİ TURU**: yalnız doğrulanmış danışmanlarla; yön değişirse fail-closed NÖTR |
| `emir_plani` | `piramit-sistem/scripts/emir_plani.py` | `--job` | Kararı `<MARKET\|LIMIT> <LONG\|SHORT> @giriş \| stop \| T1 \| R` emrine çevirir |
| `ilk_gecis` | `piramit-sistem/scripts/ilk_gecis.py` | `--m15 --yon --giris --stop --hedef --ufuk --n --seed` | Hedef mi stop mu ÖNCE — Monte Carlo ilk-geçiş yarışı |
| `usd_hedef` | `piramit-sistem/scripts/usd_hedef.py` | `--job` | Sabit-USDT profili (kontrat + sabit stop + kazanç bandı) 5 kapısı |
| `kiyas` | `piramit-sistem/scripts/kiyas.py` | `--onceki --yeni --m15 --arsiv` | HESAP VERME + KIYAS (her yeni veride İLK İŞ) |
| `akibet_etiketle` | `piramit-sistem/scripts/akibet_etiketle.py` | `--defter --m15 --arsiv --yaz --azami-bekleme --azami-tutma` | Geçmiş emirlerin akıbeti = SI geri beslemesinin yakıtı |

---

## 4) KAYIT DIŞI SİLAHLAR — denetim, girdi, çizim, sağlık

Bunlar `MOTOR` tablosunda değildir (karar üretmezler); denetler, besler, çizerler.

### 4.1 Denetçiler (fail-closed korkuluklar)

| Betik | Argüman | Ne denetler |
|---|---|---|
| `piramit-sistem/scripts/gozlemci.py` | `--rapor` | Her katmanın ARTEFAKTINI: UYDURMA / HAFIZA / DAİRESEL / EKSİK_AKTARIM / TÜNEL / MEMNUN_ETME / SIRADAN / ÇARPIŞMA. Kritik ihlalde işlem kalitesi MÜHÜRLENİR |
| `piramit-sistem/scripts/iddia_denetle.py` | `--metin --rapor` | Kullanıcıya sunulacak metindeki her SAYI koşu raporunda var mı (anlam denetlemez) |
| `karar-kurulu/scripts/rr_denetim.py` | `--job` | Dar stop + uzak hedef ile şişirilmiş R → `R_gercekci` |
| `grafik-calisma/scripts/kalibrasyon.py` | (kütüphane) | Permütasyon / bootstrap / Wilson / MAE-quantile ile eşik türetimi |

### 4.2 Veri alımı ve besleme

| Betik | Argüman | Rol |
|---|---|---|
| `piramit-sistem/scripts/veri_topla.py` | (argparse yok) | Telefon/masaüstünde `piramit_veri_*.json` paketi üretir |
| `piramit-sistem/scripts/paket_ac.py` | `--paket --sembol` | Paketi doğrulayıp depoya dağıtır (SHA defteri + geri-sarma kilidi) |
| `piramit-sistem/scripts/turev_girdi.py` | `--m15 --seri --out --ek --oi-snapshot --http --ham --sembol` | CVD'yi kullanıcının KENDİ kline'ından çevrimdışı hesaplar (kline körlüğü panzehiri) |
| `data-analysis-deep-scan/scripts/analyze_data.py` | `--job --input --output` | Denetlenebilir hesap koşusu |
| `data-analysis-deep-scan/scripts/join_data.py` | `--spec --output --manifest` | Kardinalite denetimli birleştirme |

### 4.3 Çizim (SVG — matplotlib GEREKMEZ)

| Betik | Argüman | Rol |
|---|---|---|
| `grafik-cizim/scripts/cizim.py` | `--job --araclar` | Job → çizimli mum grafiği (SVG) |
| `grafik-cizim/scripts/otomatik_cizim.py` | `--job` | `smc_tespit`in ÖLÇTÜĞÜ yapıdan otomatik katman (OB/FVG/likidite/BOS-CHoCH/fib) |
| `grafik-cizim/scripts/araclar.py` | (kütüphane) | 24 TradingView aracının SVG karşılığı |
| `grafik-cizim/scripts/tuval.py` | (kütüphane) | Sıfır bağımlılıklı mum tuvali |

### 4.4 Sağlık ve öz-testler

```
python3 .claude/skills/piramit-sistem/scripts/saglik.py --hizli   # saniyeler
python3 .claude/skills/piramit-sistem/scripts/saglik.py --tam     # bütün öz-testler
```

Öz-testi olan beceriler (`*/scripts/self_test.py`): backtest-motoru,
data-analysis-deep-scan, grafik-calisma, grafik-cizim, karar-kurulu,
piramit-sistem, portfoy-optimizasyonu, risk-yonetimi, turev-akis, video-isleme
+ `engine/self_test.py` + `karar-kurulu/scripts/rr_denetim_test.py`.

---

## 5) BECERİLER — komutsuz devreye giren 13 proje becerisi

`.claude/skills/` altında; hepsi `CLAUDE.md` tablosuyla soru içeriğine göre
**otomatik** tetiklenir (slash komutu yok).

| Beceri | Ne zaman | Motoru |
|---|---|---|
| `piramit-sistem` | **VARSAYILAN YOL** — tam analiz / kline+türev | `piramit.py` (+13 yardımcı betik) |
| `karar-kurulu` | Nihai karar, "hepsini birleştir" | `sentez.py`, `rr_denetim.py` |
| `karar-motoru` | 15M+4H kline seti geldiğinde | `engine/karar_motoru.py` |
| `turev-akis` | OI / funding / CVD / LSR / likidasyon | `turev_akis.py` |
| `grafik-calisma` | Grafik okuma, SMC, Fibonacci, giriş bölgesi | `smc_tespit.py`, `confluence.py`, `setup_dogrulama.py`, `kalibrasyon.py` |
| `grafik-cizim` | Grafik ÜZERİNE çizim, R:R kutusu, TradingView tarzı | `cizim.py`, `otomatik_cizim.py`, `araclar.py`, `tuval.py` |
| `backtest-motoru` | Backtest, profit factor, Monte Carlo, walk-forward | `backtest.py` |
| `risk-yonetimi` | Pozisyon boyutu, Kelly, kaldıraç, VaR/CVaR | `risk.py` |
| `portfoy-optimizasyonu` | Ağırlık, Markowitz, HRP, risk paritesi | `portfolio.py` |
| `data-analysis-deep-scan` | Veri/oran/istatistik/sayısal iddia denetimi | `profile_data.py`, `verify_data.py`, `analyze_data.py`, `join_data.py` |
| `video-isleme` | Video/ekran kaydı → kare çıkarma | `video_isle.py` |
| `forex-trading-expert` | SMC/ICT/MQL5/Pine referans derinliği | (betik yok — referans belgeleri) |
| `uzman-modu` | Ciddi analiz/karar disiplini (üst-akıl) | (betik yok — protokol) |

---

## 6) SUPERPOWERS (14) — yalnız DEPO KODU değişecekse

Kaynak: `obra/superpowers` (MIT), `.claude/skills/UCUNCU-TARAF.md`.
Piyasa analizi üretilirken **devreye girmez** (`CLAUDE.md` öncelik sırası).

- Süreç: `brainstorming`, `writing-plans`, `executing-plans`,
  `subagent-driven-development`, `dispatching-parallel-agents`
- Kalite: `test-driven-development`, `systematic-debugging`,
  `verification-before-completion` *(bu madde piyasa tarafında da geçerlidir)*
- İnceleme: `requesting-code-review`, `receiving-code-review`
- Dal/iş akışı: `using-git-worktrees`, `finishing-a-development-branch`
- Meta: `using-superpowers`, `writing-skills`

---

## 7) ÇAKIŞMA ÖNCELİĞİ (üstteki kazanır)

1. `CLAUDE.md` + `STRATEJI.md` — proje sözleşmesi
2. Somut depo kanıtı (dosya / ölçüm / koşu raporu)
3. Superpowers iş akışı — yalnız kod/mühendislik işlerinde
4. Genel tercihler

---

## 8) ÇIKTI SÖZLEŞMESİ — her karar analizinde

1. HESAP VERME (önceki emrin akıbeti) → 2. KIYAS (yön + sürücü değişimi) →
3. Motorlar (kanıt) → 4. 5 danışman merceği → **YÖN (bias)** + **İŞLEM KALİTESİ**
→ 5. EMİR PLANI ya da "EMİR YOK" + düşen kapı → 6. gerçek/varsayım/yorum ayrımı.
