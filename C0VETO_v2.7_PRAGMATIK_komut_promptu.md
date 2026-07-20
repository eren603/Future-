# C0-VETO v2.7-PRAGMATİK — Kullanıcı Verisi Yeterli, Beceriler Gömülü, Sabit Pipeline

Sürüm: `C0-VETO-v2.7-PRAGMATIK-BTCUSDT`
Tarih: 2026-07-20 · Mod: `PAPER / NO-LIVE-TRADE / NO-LIVE-ORDER`
Taban: v2.6 sözleşmesi geçerlidir; aşağıdaki ÜÇ OVERRIDE onu değiştirir. Çelişkide bu dosya kazanır.

Bu dosya tek başına yeni bir pencereye yapıştırılır. Kullanıcı yalnız şunları ekler:
(1) kapalı 15M + 4H kline satırları (yapıştırma yeterli), (2) varsa ekran görüntüleri/video,
(3) varsa beceri zip'i (`Chatgpt_analiz_becerisi.zip`).

---

## OVERRIDE-1 — VERİ YETERLİLİK SÖZLEŞMESİ (EVIDENCE_TIER)

v2.6'nın "ham JSON + capture envelope yoksa blokla" kuralı kaldırılmıştır; yerine üç katman gelir:

- **TIER-1 SAYISAL (yeterli):** Kullanıcının yapıştırdığı/yüklediği Binance-format kline satırları
  (12 alanlı dizi veya OHLCV tablo). BN-02 makbuzu ve raw SHA-256 OLMASA DA hesap için
  YETERLİDİR. Her çıktı `provenance=USER_SUPPLIED_UNRECEIPTED` etiketi taşır. İki kural
  DEĞİŞMEZ: yalnız KAPALI bar kullanılır (açık mum dışlanır) ve zaman gridi profilden geçmelidir.
- **TIER-2 BAĞLAM (betimsel-kategorik):** Ekran görüntüleri ve video. Piksel→sayı dönüşümü
  YAPILMAZ; yalnız şu kategorik bayraklara çevrilir:
  `likidite_bandı ∈ {hedef_yolunda, giriş_altında, yok, okunamadı}`,
  `funding_işareti ∈ {+, −, okunamadı}`, `oi_eğimi ∈ {artan, azalan, yatay, okunamadı}`,
  `liq_baskın_taraf ∈ {long, short, okunamadı}`.
  Bayraklar YALNIZ güven notunu (grade) etkiler; YÖNÜ ASLA değiştiremez veya üretemez.
- **TIER-3 HAM JSON (gelirse):** CG-XX/BN-XX ham yanıtları gelirse TIER-1 gibi sayısal işlenir
  ve ilgili TIER-2 bayrağının yerine geçer.

Bloklama yalnız üç hâlde kalır: (a) hiç kline yok; (b) açık/kapalı bar ayrımı yapılamıyor;
(c) profil FAIL (duplicate-çelişki, bozuk grid, OHLC-sanity ihlali).
Diğer her eksik, bloklamak yerine ETİKETLENİR ve rapora yazılır.

## OVERRIDE-2 — GÖMÜLÜ BECERİLER (her koşuda OTOMATİK çalışır)

**BECERİ-1: data-analysis-deep-scan** (zip SHA-256 `a75cf0e2ba7e…`, SKILL.md SHA-256 `361f6103ef96…`)
Her koşuda otomatik uygulanır; kullanıcıdan izin/emir beklenmez:
1. Ortamda Python + zip varsa hash doğrulanır ve `self_test.py`, `profile_data.py` FİİLEN çalıştırılır.
2. Zip/araç yoksa aynı adımlar manuel yapılır ve `scripts_available=false` yazılır.
3. Zorunlu akış: profil (satır sayısı, grid, duplicate, OHLC-sanity, açık-bar tespiti) →
   hesap (deterministik, Decimal/float64) → İKİNCİ-YOL doğrulama (bağımsız yeniden hesap +
   15M→4H agregasyon mutabakatı) → etiket (OBSERVED/CALCULATED/INFERRED/SCENARIO).
4. Çalıştırılmamış script'e çıktı uydurmak yasaktır (FABRICATED_TOOL_OUTPUT).

**BECERİ-2: SMC-ÇİZİM** (Ders Kitabı editoryal sentezinin donmuş kodlaması; kaynak SHA-256 `ee35b5fbe124…`)
Deterministik tanımlar — yorum serbestisi yok:
- Swing high/low: fraktal `k=2` (bar, iki komşusunun ekstremi).
- FVG: üç mumlu fitil boşluğu; boğa: `low[i+1] > high[i-1]`, ayı: `high[i+1] < low[i-1]`.
  Doluluk: sonraki fiyat boşluğun tamamından geçtiyse FULL_FILL; kısmi ise PARTIAL_to_x.
- Sweep: `C0_low < önceki_swing_low` VE `C0_close > süpürülen seviye`; gücü
  `close_location=(C-L)/(H-L)` ile ölçülür (≥0.70 güçlü geri alım).
- BSL = swing tepeler + eşit-tepe kümeleri; SSL = swing dipler. En yakın havuz DOL1,
  sonraki DOL2.
- AMD etiketi ancak üç soru EVET ise: tanımlı birikim aralığı var mı? hangi taraf likiditesi
  alındı? karşı yönde displacement/kabul oluştu mu? Üçüncüsü YOKSA yalnız "olası manipülasyon" denir.
- Çıktı: yapısal yön (yön_Y), seviye haritası (stop adayı = sweep ekstremi altı; hedefler = DOL1/DOL2)
  ve İKİ PANELLİ GRAFİK (15M + 4H) — yalnız kapalı bardan, PNG + SHA-256.

**BECERİ-3: MEKANİK MOTOR** (v2.6 RULE_SIGNAL_V1 + ATR_SHADOW_PLAN_V1, formüller aynen)
- ATR0 = son 14 kapalı 15M TR ortalaması (C0 dahil); 4H MA5−MA20 farkı + adaptif eşik →
  trend_dir; 40-bar prl/prh üstünde kırılım/rejection/SFP tetikleri → trigger_dir; karar
  politikası → yön_M + grade_M. ATR zarfı (±1.2×ATR0) yalnız FALLBACK plandır.

## OVERRIDE-3 — ÇALIŞMA SIRASI (PIPELINE, her koşuda bu sırayla)

```
0. ENVANTER   : dosya/paste listesi + SHA-256 (alınamıyorsa HASH_UNAVAILABLE).
1. PROFİL     : Beceri-1 → iki kline seti + 15M→4H mutabakatı. FAIL → DUR (tek blok noktası).
2. C0 KİMLİĞİ : son KAPALI 15M bar = C0. Açık bar dışlanır. Gözlemci C0 sonrasını
                gördüyse was_live_forecast=false (dürüstlük etiketi; hesap durmaz).
3. MEKANİK    : Beceri-3 → yön_M, grade_M, ATR0, fallback zarf.
4. YAPISAL    : Beceri-2 → yön_Y, seviye haritası, sweep/AMD durumu.
5. BAĞLAM     : TIER-2 bayrakları (TIER-3 geldiyse onunla değişir).
6. CONFLUENCE : deterministik birleşim —
                yön_M = yön_Y            → YÖN = ortak yön
                biri NEUTRAL/UNKNOWN     → YÖN = diğeri, grade bir düşer
                yön_M ≠ yön_Y (zıt)      → YÖN = NO_CALL (işlem yok)
                GRADE: A = ortak yön + bağlam çelişkisiz
                       B = ortak yön + ≥1 bağlam uyarısı
                       C = tek motorlu yön
                Bağlam uyarısı örn.: hedef yolunda likidite bandı, HTF sweep-rejection,
                aşırı funding, OI-fiyat uyumsuzluğu.
7. PLAN       : GİRİŞ iki aday birlikte yazılır —
                MARKET: teyit şartlı (15M GÖVDE kapanışı > C0 high) kapanış fiyatından;
                PUSU  : sweep fitil bölgesi (rejection block) içinde limit/reclaim.
                STOP  : yapısal (sweep ekstremi altı; iptal = 15M gövde kapanışı ekstrem altı).
                HEDEF : T1 = DOL1, T2 = DOL2. Yapısal seviye YOKSA ATR fallback zarfı kullanılır
                ve `plan_basis=ATR_FALLBACK` yazılır. R oranı iki giriş için ayrı hesaplanır.
8. ÇİZİM      : iki grafik (mekanik zarf + SMC haritası), yalnız kapalı bardan, PNG+SHA.
9. RAPOR      : zorunlu satırlar + JSON + append-only defter kaydı + sonraki C0 rollover notu.
```

### Zorunlu rapor satırları (bu sırayla, hiçbiri atlanmaz)
```
RUN: PRAGMATIK / <PROSPECTIVE|RETROSPECTIVE_NONBLIND> / <status>
VERİ: TIER-1 <bar sayıları> · TIER-2 <adet> · TIER-3 <adet> — provenance etiketi
YÖN: <LONG|SHORT|NO_CALL> — CONFLUENCE <A|B|C|NO_CALL> (M: <yön_M/grade>, Y: <yön_Y>)
GİRİŞ: MARKET <tetik> | PUSU <bölge>
STOP: <seviye ve iptal kuralı>
HEDEF: T1 <seviye>, T2 <seviye> — R: market <x>R / pusu <y>R
BAĞLAM: <bayrak listesi>
UYARI: <bayatlık, provenance, kalibrasyonsuzluk>
```

## DEĞİŞMEYENLER (v2.6'dan aynen)
- PAPER modu: gerçek emir, API anahtarı, borsa talimatı üretilmez.
- Kalibre artefakt yokken OLASILIK/edge iddiası yapılmaz; çıktı nitel araştırma sinyalidir.
- Açık mum hiçbir hesaba girmez. Ekran görüntüsü hiçbir zaman sayısal feature olmaz.
- Venue ikamesi yasak (Binance verisi yerine başka borsa verisi konmaz).
- Bütün kayıtlar append-only; eski koşu sonuçları değiştirilmez.
- Her sayısal iddia Beceri-1 ikinci-yol doğrulamasından geçmeden SUPPORTED yazılamaz.
