# C0-VETO v2.6 BTCUSDT — Koşu Raporu (RC-A0)

Analiz başlangıcı: 2026-07-20T04:33:14Z · C0 = 2026-07-20T04:15–04:30Z (son kapalı 15M bar)
Sözleşme: C0-VETO-v2.6-BTCUSDT-RESEARCH · Mod: PAPER / NO-LIVE-TRADE

```
RUN: CASE_AUDIT / RETROSPECTIVE_NONBLIND_AUDIT / FEATURES_ONLY
ROUTER: AUTO_NEXT_C0 → new RUN_CARD RC-20260720-C0close0445Z-c1168185-R1 / forecast_id FC-20260720-0445Z-R1 (parent RC-20260720-C0close0430Z-c1168185-A0) — yeni kart BLOCKED_INCOMPLETE_C0 (04:45 barı için native veri yok; ortamda Binance aracı yok)
EXEC_DATA: YOK — fapi.binance.com/api.binance.com proxy CONNECT 403 (04:34Z test); Crypto.com MCP İKAME EDİLMEDİ (BLOCKED_SCOPE_MISMATCH_EXEC_VENUE)
DEEP_SCAN_AUDIT: PARTIAL — 2 ham girdi profillendi / 5 ikinci-yol doğrulama / karantina: video + CG-05; atlanan: V1–V6, beceri script'leri (zip yüklenmedi → manuel motor c0veto_engine.py)
CALIBRATED_FORECAST: YOK — BLOCKED_CALIBRATION_REQUIRED, BLOCKED_MODEL_ARTIFACT_MISSING
RULE_SIGNAL: UP — RETROSPECTIVE_NONBLIND_DIAGNOSTIC — B (gözlemci C0 sonrası ~30 sn açık mum gördü; was_live_forecast=false)
RULE_SIGNAL_V2: BLOCKED_CALIBRATION_REQUIRED — V2 artefakt zinciri yok
REFERENCE_PLAN: LONG — E=64733.60 T=65021.95 S=64445.25 — ATR_FALLBACK_UNVALIDATED (raw; tickSize erişilemedi), DIAGNOSTIC_ONLY
PUSU_REFERENCE: zone=[64673.53, 64697.56] + trigger: zone dokunuşu sonrası kapalı 15M reclaim > zone üstü + expiry: C0+4 bar (05:30:00Z) — UNARMED_SHADOW / DIAGNOSTIC_ONLY
MARKET: YOK — MARKET_YOK_LIVE_QUOTE_MISSING, EXEC_DATA=YOK, fee=UNKNOWN
PUSU: YOK — canlı bid/ask/fee/latency kapıları geçilemedi (REFERENCE_EXECUTION_CONFUSION önlemi)
NİHAİ İCRA: NO_ENTRY
```

## Sayısal çekirdek (hepsi CALCULATED, ikinci-yol doğrulamalı)

| Büyüklük | Değer | Kaynak |
|---|---|---|
| C0 OHLC | 64674.40 / 64757.00 / 64602.00 / 64733.60 | K15 satır 59 |
| ATR0 (14 TR, C0 dahil) | 240.29 | RULE_SIGNAL_V1 md.3 |
| ma5_4h / ma20_4h | 64592.62 / 64131.845 | 21 eligible 4H kapanış |
| gap4h / thr4h | +0.71848% / 0.19111% → **trend_dir=UP** | md.4-5 |
| mb | −0.1635 (karşı kanıt) | md.5 |
| prl / prh (40 bar) | 64305.00 / 65084.60 | md.6 |
| Tetikler | hepsi FALSE → **trigger_dir=NEUTRAL** | md.7-8 |
| Karar | **UP / LONG / grade B** (trend kaynaklı) | karar politikası |

Veri bütünlüğü: 15M (59 kapalı bar) ve 4H (21 kapalı bar) tekdüze grid, duplicate yok, OHLC-sanity PASS; 15M→4H agregasyonu 3 tam pencerede birebir eşleşti; ekran 24S High/Low (65084.6/64259.5) yapıştırılan veriyle bağımsız olarak tutarlı. Açık barlar (15M 04:30+, 4H 04:00+) hiçbir hesaba girmedi.

Ekranlar: 4 adet CoinGlass **Liquidity Heatmap** ekranı CG-06 (order-book) sınıfındadır, CG-05 liquidation heatmap DEĞİLDİR (G25); tamamı DESCRIPTIVE_ONLY. Betimsel not: ~65.000–65.100 bandında belirgin likidite bandı görünüyor (piksel→sayı dönüşümü yapılmadı). Video: hash alındı, kör kullanım için karantinada.

## Bir sonraki tek güvenli adım
RC-R1 kartını açabilmek için: 04:45:00Z ve sonrası kapalı 15M + 4H **raw Binance kline JSON'u** ile BN-02 makbuzu (endpoint, query, istek/yanıt zamanları, SHA-256) ve CG-00 pair-mapping yanıtı gönderin. Canlı (blind, PT30S uyumlu) forecast bu ortamda ancak Binance API erişimi açılırsa mümkündür.
