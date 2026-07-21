---
name: risk-yonetimi
description: >-
  Risk yönetimi ve pozisyon boyutlandırma motoru. Bir soru pozisyon boyutu, lot,
  kaç birim/kontrat, risk yüzdesi, stop mesafesi, Kelly kriteri, kaldıraç,
  volatilite hedefleme, VaR, CVaR, riske maruz değer, max drawdown hesabı ile
  ilgili olduğunda OTOMATİK devreye girer — slash komutu gerekmez. Çalışan motor:
  scripts/risk.py (numpy/scipy, harici bağımlılık yok). Tetikleyici kelimeler
  (TR/EN): risk, pozisyon boyutu, position size, lot, kaç birim, risk yüzdesi,
  stop, kelly, kaldıraç, leverage, volatilite hedef, vol target, VaR, CVaR,
  riske maruz değer, drawdown, R:R, risk ödül.
  agiprolabs risk-management/position-sizing/kelly-criterion metodolojisine dayanır.
---

# Risk Yönetimi & Pozisyon Boyutlandırma

Bir risk/pozisyon sorusu geldiğinde otomatik uygula. **Çalışan kod
`scripts/risk.py`**. Kullanım: `python3 scripts/risk.py --job job.json`.

## Operasyonlar (`op`)
- **position_size / fixed_fractional** — equity, risk_pct, entry, stop → birim + notional.
  (İşlem başına maks %1-2 risk kuralı ile uyumlu.)
- **position_size / kelly** — win_rate, avg_win, avg_loss → tam Kelly + uygulanan
  kesir. **Varsayılan yarım-Kelly** (aşırı kaldıraçtan korunma). Negatif Kelly =
  kenar yok, pozisyon açma.
- **position_size / vol_target** — hedef vol / varlık vol → kaldıraç.
- **var** — getiri serisinden tarihsel VaR + CVaR (kuyruk kaybı).
- **drawdown** — equity eğrisinden maks düşüş + süre.

## Zorunlu disiplin
- Kelly çıktısını **olduğu gibi tam kaldıraç olarak sunma**; yarım/çeyrek-Kelly öner.
- Her sonuçta risk varsayımlarını (equity, risk%, stop) açıkça yaz.
- Bu bir olasılık/istatistik çıktısıdır, kâr garantisi değildir.

## Diğer becerilerle çakışma (paralel)
- `backtest-motoru` → win_rate/avg_win/avg_loss üretir → buraya Kelly girdisi olur.
- `grafik-calisma` → giriş + stop seviyesi verir → fixed_fractional girdisi olur.
- `portfoy-optimizasyonu` → varlık ağırlıklarıyla toplam portföy riskini birleştirir.
