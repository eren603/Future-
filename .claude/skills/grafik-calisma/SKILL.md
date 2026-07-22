---
name: grafik-calisma
description: >-
  Grafik okuma, SMC + Fibonacci analiz ve grafik üretme becerisi. Bir soru
  grafik/chart okuma, mum grafiği (candlestick) yorumlama, fiyat grafiği,
  teknik analiz, SMC, CHoCH, BOS, order block, FVG, likidite, Fibonacci
  retracement, golden zone, giriş bölgesi (entry), destek/direnç, trend
  çizgisi, ya da grafik/dashboard OLUŞTURMA ile ilgili olduğunda OTOMATİK
  devreye girer — hiçbir slash komutu gerekmez. Kullanıcı grafik ekran
  görüntüsü gönderdiğinde ya da bir sembol için analiz istediğinde de tetiklenir.
  Tetikleyici kelimeler (TR/EN): grafik, chart, mum, candlestick, teknik analiz,
  technical analysis, SMC, smart money, ICT, CHoCH, BOS, order block, FVG,
  fibonacci, fib, golden zone, OTE, likidite, liquidity sweep, entry, giriş,
  destek direnç, support resistance, trend, dashboard, plot, ATR, rejim,
  regime, MTF, çoklu zaman dilimi, edge, tarihsel doğrulama.
  Çalışan motorlar: scripts/smc_tespit.py (OHLCV'den otomatik yapı/OB/FVG/
  likidite/ATR/rejim tespiti), scripts/confluence.py (katman sıralı giriş/çıkış
  + ATR-stop + MTF + rejim kapıları), scripts/setup_dogrulama.py (tarihsel
  edge kanıtı — kanıt yoksa sinyal yok). Detaylı SMC metodolojisi için
  forex-trading-expert becerisinin references/smart-money-concepts.md
  dosyasını kullanır.
---

# Grafik Okuma & SMC + Fibonacci Analizi

Üç mod var: **görselden okuma**, **canlı veriden analiz**, **grafik üretme**.
Hepsi otomatik; kullanıcı komut yazmaz.

## Kesinlik boru hattı (SAYISAL VERİ VARSA ZORUNLU SIRA)
Yön + giriş/çıkış istendiğinde ve OHLCV verisi mevcutsa (kullanıcı yapıştırdı
ya da Crypto.com MCP'den çekildi), seviyeler göz kararı DEĞİL şu zincirle üretilir:

```
veri (OHLCV)
 → scripts/smc_tespit.py      # swing/BOS-CHoCH/OB/FVG/likidite/ATR/rejim OTOMATİK
                              # (aynı veri = aynı seviye; öznellik yok). HTF verisi
                              # de verilirse htf_bias çıkarır (MTF hizalama).
 → scripts/setup_dogrulama.py # KALİBRASYON + KANIT (her koşuda bu veriyle):
                              #  - MAE kalibrasyonu → SL tamponu (atr_mult) veriden
                              #  - permütasyon testi → edge, rastgele girişten ayrışmalı
                              #  - bootstrap CI → beklenti alt sınırı > 0
                              #  - Wilson → önerilen min R:R = (1-wr_lo)/wr_lo
                              # sinyal_izni=false ise SİNYAL VERİLMEZ (fail-closed).
 → scripts/confluence.py      # tespit çıktısı + KALİBRE eşiklerle (atr_mult ve
                              # min_rr setup_dogrulama.kalibrasyon'dan; job'a
                              # thresholds_kaynak yaz) katman sıralı giriş/çıkış.
 → karar-kurulu               # nihai tek karar (diğer motorlarla sentez)
```

Kurallar: (1) `smc_tespit` çıktısındaki `confluence_job` doğrudan
`confluence.py`'ye verilir — elle seviye uydurulmaz. (2) `setup_dogrulama`
`sinyal_izni=false` derse sonuç en fazla "kurulum var ama tarihsel kanıt yok →
BEKLE" olur. (3) Görsel-yalnız analizde (sayısal veri yoksa) bu zincir
çalıştırılamaz; çıktı "yaklaşık/kanıtsız" etiketiyle verilir ve kullanıcıdan
OHLCV istenir.

## Dinamik eşik ilkesi (kalibrasyon.py)
Piyasa durağan değildir: sabit eşik (dünkü 15 işlem / MC 0.6 / R:R 2) bir
sonraki koşuda geçersiz olabilir. Bu yüzden eşikler SEÇİLMEZ, her koşuda o
koşunun verisinden İSTATİSTİKLE türetilir (`scripts/kalibrasyon.py`):
permütasyon p-değeri (edge ≠ piyasa sürüklenmesi), bootstrap CI, Wilson
kötümser kazanma oranından min R:R, kazanan-MAE quantile'ından SL tamponu.
İki tuzak da yasak: statik eşik VE serbest ayar (aşırı-uyum). Türetimler
korkulukla sınırlıdır; kalibre edilemeyen her sabit çıktıdaki `varsayimlar`
defterinde AÇIKÇA etiketlenir — gizli sabit eşik yasaktır. Her motor çıktısı
`esik_kaynagi` alanıyla eşiklerin veri-türevi mi varsayım mı olduğunu bildirir.

## A) Görselden okuma (ekran görüntüsü / chart resmi)
Kullanıcı bir grafik görseli gönderdiğinde şu sırayla analiz et:

1. **Bağlam:** sembol, zaman dilimi, borsa (görünüyorsa). Görünmüyorsa "VERİ YOK"
   de, uydurma.
2. **Piyasa yapısı (SMC):**
   - Swing yüksek/düşükleri belirle → trend (HH-HL / LH-LL).
   - **BOS** (trend yönünde yapı kırılımı) ve **CHoCH** (trend değişim sinyali —
     son swing'in ters yönde kırılması) işaretle.
   - **Order Block** (kırılım öncesi son ters mum bölgesi), **FVG** (üç mumluk
     boşluk) ve **likidite havuzları** (eşit tepe/dip, süpürme fitilleri) tespit et.
   - Detaylı tanımlar: `../forex-trading-expert/references/smart-money-concepts.md`.
3. **Confluence ile yön + giriş/çıkış (ZORUNLU KATMAN SIRASI):**
   Fibonacci **tek başına yeterli değildir** — sadece bir "nerede" aracıdır;
   yönü, bağlamı, geçerliliği bilmez. Giriş/çıkış seviyesi **her zaman** şu
   sırayla hesaplanır (fib en sonda bir rötuş katmanıdır):

   > **bağlam(HTF) → yapı(SMC) → arz-talep(OB/FVG) → likidite → [fib] → onay → risk**

   Kural: **güçlü giriş bölgesi = golden zone (0.618–0.786) + order block/FVG +
   likidite AYNI noktada buluştuğunda (confluence).** Yalnız fib = confluence
   eksik → **NÖTR-BEKLE** (fail-closed). Bunu hafızadan değil **motorla** üret:
   ```
   python3 scripts/confluence.py --job job.json
   ```
   Motor girdisi: `structure` (CHoCH/BOS + bull/bear), `impulse` (swing bacağı),
   `htf_bias`, `order_blocks`, `fvgs`, `liquidity`. Çıktı: KARAR (LONG/SHORT/
   NÖTR-BEKLE), confluence skoru + faktörler, golden zone, **giriş bölgesi**
   (golden zone ∩ OB/FVG), **geçersizlik (SL)** = impulsu başlatan swing ötesi,
   **hedefler** = hedef yöndeki likidite, ve **R:R**. Kapılar (fail-closed):
   yapı-impuls çelişkisi / confluence yok / skor<eşik / R:R<eşik → BEKLE.
4. **Sonuç kartı:** motor çıktısını olduğu gibi ver — yön, giriş bölgesi,
   geçersizlik, hedef(ler), R:R, confluence skoru + **olasılık dili** ("olur"
   değil "olabilir"). Görselde OKUNAMAYAN hiçbir sayı üretme; seviyeleri
   görseldeki ölçekten yaklaşık ver ve yaklaşık olduğunu söyle. Onay (alt-TF
   tetik) girişten önce beklenir.

## B) Canlı veriden analiz (sembol verildiğinde)
Kullanıcı "BTC 4h analiz et" gibi bir istek verirse:
1. **Crypto.com MCP** `get_candlestick` ile OHLCV çek (uygun interval, ~100-200 mum).
2. Aynı katman sırasını SAYISAL veriyle uygula: swing tespiti + CHoCH/BOS + OB/FVG
   + likidite havuzlarını çıkar, sonra `scripts/confluence.py` motoruna ver →
   yön + giriş/çıkış + R:R gerçek fiyatlarla hesaplanır (yalnız fib değil, confluence).
3. Hesaplama/doğrulama gerekiyorsa `data-analysis-deep-scan` scriptleriyle çalış.
4. İstenirse matplotlib ile **işaretlenmiş grafik çiz** (aşağıdaki C modu) ve
   SendUserFile ile gönder.

## C) Grafik üretme
- **Analiz grafiği:** matplotlib ile mum grafiği + CHoCH/BOS çizgileri + fib
  bölgeleri (renkli bantlar) + giriş/geçersizlik etiketleri çiz, PNG olarak gönder.
  (pandas/numpy SessionStart hook ile kurulu; mplfinance yoksa `pip install
  mplfinance` dene, olmazsa matplotlib ile candlestick'i elle çiz.)
- **Genel grafik/dashboard:** `dataviz` becerisi kurallarıyla (erişilebilir renk,
  net eksen); Excel içi grafik için `xlsx`.

## Zorunlu risk çerçevesi (her analizde)
- Bu bir **olasılık senaryosudur, sinyal değildir** — her çıktıda tek cümleyle belirt.
- Risk yönetimi: işlem başına maks %1-2 risk, min 1:2 R:R
  (forex-trading-expert Risk Management bölümüyle uyumlu).
- Gerçek / varsayım / yorum ayrımı korunur; emin olunmayan nokta açıkça söylenir.
