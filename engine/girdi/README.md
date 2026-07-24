# Girdi dizini

Kullanıcının yapıştırdığı kline setleri her koşuda buraya yazılır:
- `m15.json` — 15 dakikalık klineler
- `h4.json` — 4 saatlik klineler

Bayat veriyle koşu yapılmaz: her koşuda iki dosya da o koşunun verisiyle
yenilenir; eksikse kullanıcıdan istenir.

## Otomatik bağlanan opsiyonel kanallar (tetikleyici gerekmez)

`.claude/hooks/piramit_auto.py` her istemde bu dizini tarar. Aşağıdaki dosya
VARSA ilgili motor piramit boru hattına **kendiliğinden** girer; YOKSA
fail-closed atlanır (uydurma girdi üretilmez):

| Dosya | Devreye giren motor |
|---|---|
| `turev.json` | `turev-akis` — OI/funding/CVD/taker-LSR/likidasyon (kline-körlüğü panzehiri) |
| `ohlcv.csv` | `data-analysis-deep-scan` profil + SMC tablo kaynağı |
| `risk.json` | `risk-yonetimi` — pozisyon boyutu/Kelly/vol-hedef |
| `backtest.json` | `backtest-motoru` — PF/Sharpe/Monte Carlo |
| `portfoy.json` | `portfoy-optimizasyonu` — Markowitz/HRP ağırlık |
| `video.mp4` | `video-isleme` — kare çıkarma (kare OKUMA elle) |
| `veri_sozlesmesi.json` | `verify_data` — fail-closed tablo sözleşmesi |

Bu dosyalardan biri değişirse parmak izi değişir ve boru hattı bir sonraki
istemde yeniden koşar. Dosya içerikleri **panelden okunan gerçek değerlerle**
doldurulur — uydurma sayı yasaktır; eksik alan `VERİ YOK` bırakılır.
