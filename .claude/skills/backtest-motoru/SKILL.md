---
name: backtest-motoru
description: >-
  Backtest ve strateji sağlamlık motoru. Bir soru backtest, geriye dönük test,
  strateji testi, strateji performansı, profit factor, Sharpe, max drawdown,
  win rate, equity curve, Monte Carlo, walk-forward, overfitting kontrolü ile
  ilgili olduğunda ya da kullanıcı OHLCV/mum verisi + strateji verip "test et"
  dediğinde OTOMATİK devreye girer — slash komutu gerekmez. Çalışan motor:
  scripts/backtest.py (pandas/numpy, harici bağımlılık yok). Tetikleyici
  kelimeler (TR/EN): backtest, geriye dönük, strateji test, profit factor,
  sharpe, sortino, drawdown, win rate, equity, monte carlo, walk-forward,
  overfitting, sağlamlık, robustness, sma cross, rsi strateji.
  marketcalls/vectorbt-backtesting + Trade-With-Claude/cbt-framework (SADECE
  backtest kısmı; CANLI İŞLEM DAHİL DEĞİL) metodolojisine dayanır.
---

# Backtest & Sağlamlık Motoru

Bir strateji/backtest sorusu geldiğinde otomatik uygula. **Çalışan kod
`scripts/backtest.py`** — sonuç üretmezse iş tamamlanmamış sayılır.

## Nasıl çalıştırılır
1. OHLCV veriyi bir dosyaya al (CSV/JSON; en az `close` kolonu). Kullanıcı
   Binance/kripto verisi verirse doğrudan kaydet; sembol verirse Crypto.com MCP
   `get_candlestick` ile çek.
2. Bir job JSON hazırla ve çalıştır:
   ```
   python3 scripts/backtest.py --job job.json
   ```
3. Strateji tipleri: `sma_cross` (fast/slow), `rsi` (period/buy_below/sell_above),
   `signal_column` (dışarıdan 1/0/-1 sinyal — SMC/Fib sinyallerini buraya bağla).

## Zorunlu disiplin
- **Lookahead engellenir:** pozisyon bir sonraki barda uygulanır (motor bunu yapar).
- **Gerçekçi maliyet:** `fees_bps` + `slippage_bps` her pozisyon değişiminde uygulanır.
  Kullanıcı borsa/enstrüman söylemezse varsayılan ver ama varsayım olduğunu belirt.
- **Sağlamlık şart:** her backtest'e `monte_carlo` (işlem karıştırma) ekle;
  mümkünse `walk_forward` ile train/test tutarlılığını raporla.
- **Tek backtest kanıt değildir.** Çıktı olasılık/geçmiş performanstır — her
  raporda bunu tek cümleyle belirt (doğruluk sözleşmesi).

## Çıktı (motorun ürettiği)
metrics (total_return, max_drawdown, sharpe, sortino, num_trades, win_rate,
profit_factor, expectancy, exposure, final_equity) + monte_carlo (p5/p50/p95,
prob_profit) + walk_forward (train/test tutarlılık).

## Diğer becerilerle çakışma (paralel)
- `forex-trading-expert` → strateji/Pine Script kuralını üretir, buraya sinyal verir.
- `grafik-calisma` → SMC/Fib giriş bölgelerini `signal_column`'a dönüştürür.
- `risk-yonetimi` → çıkan istatistiklerle pozisyon boyutu/Kelly hesaplar.
- `data-analysis-deep-scan` → sonuçların sayısal doğrulamasını yapar.
