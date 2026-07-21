---
name: portfoy-optimizasyonu
description: >-
  Portföy optimizasyonu motoru. Bir soru portföy dağılımı, varlık ağırlığı,
  çeşitlendirme, optimal portföy, Markowitz, ortalama-varyans, minimum
  varyans, maksimum Sharpe, etkin sınır, HRP (hiyerarşik risk paritesi),
  korelasyon bazlı dağıtım ile ilgili olduğunda OTOMATİK devreye girer — slash
  komutu gerekmez. Çalışan motor: scripts/portfolio.py (numpy/scipy). Tetikleyici
  kelimeler (TR/EN): portföy, portfolio, dağılım, ağırlık, weight, çeşitlendirme,
  diversification, markowitz, ortalama varyans, mean variance, minimum varyans,
  max sharpe, etkin sınır, efficient frontier, HRP, risk parity, korelasyon.
  Portfolio Optimization Toolkit (Markowitz + HRP) metodolojisine dayanır.
---

# Portföy Optimizasyonu

Bir portföy/dağılım sorusu geldiğinde otomatik uygula. **Çalışan kod
`scripts/portfolio.py`**. Kullanım: `python3 scripts/portfolio.py --job job.json`.

## Yöntemler (`method`)
- **min_var** — minimum varyans portföyü (en düşük risk).
- **max_sharpe** — risk-ayarlı getiri optimum (etkin sınır tepe noktası).
- **hrp** — Hierarchical Risk Parity (López de Prado): korelasyon ağacı +
  yinelemeli bölme; kovaryans tersine gerek yok, gürültüye daha dayanıklı.

## Girdi
- `returns_csv` (satır=dönem, kolon=varlık, hücre=getiri) ya da satır-içi `returns`.
- `bars_per_year` (yıllıklaştırma: saatlik kripto=8760, günlük=252).
- `long_only` (varsayılan true), `rf` (risksiz getiri).

## Zorunlu disiplin
- Ağırlık toplamı 1'e normalize edilir (motor doğrular).
- Geçmiş getiriye dayalı optimizasyon **geleceği garanti etmez**; örneklem-dışı
  (walk-forward) doğrulama öner.
- Az gözlemde kovaryans gürültülüdür → HRP'yi tercih et, sonucu temkinli sun.

## Diğer becerilerle çakışma (paralel)
- `data-analysis-deep-scan` → getiri matrisini temizler/doğrular, buraya besler.
- `risk-yonetimi` → çıkan ağırlıklarla portföy VaR/drawdown hesaplar.
- `backtest-motoru` → optimize edilen ağırlığı zaman içinde test eder.
