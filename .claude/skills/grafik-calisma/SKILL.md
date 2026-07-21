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
  destek direnç, support resistance, trend, dashboard, plot.
  Detaylı SMC metodolojisi için forex-trading-expert becerisinin
  references/smart-money-concepts.md dosyasını kullanır.
---

# Grafik Okuma & SMC + Fibonacci Analizi

Üç mod var: **görselden okuma**, **canlı veriden analiz**, **grafik üretme**.
Hepsi otomatik; kullanıcı komut yazmaz.

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
