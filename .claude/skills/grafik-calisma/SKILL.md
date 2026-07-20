---
name: grafik-calisma
description: >-
  Grafik okuma ve grafik üzerinde çalışma becerisi. Bir soru grafik/chart
  okuma, mum grafiği (candlestick) yorumlama, fiyat grafiği, teknik analiz,
  görsel veri, trend çizgisi, ya da grafik/tablo OLUŞTURMA (dataviz, Excel
  grafikleri, sunum grafiklerini tazeleme) ile ilgili olduğunda OTOMATİK
  devreye girer — hiçbir slash komutu gerekmez.
  Tetikleyici kelimeler (TR/EN): grafik, chart, mum, candlestick, teknik analiz,
  technical analysis, trend, fiyat grafiği, price chart, görsel, dashboard,
  heatmap, destek direnç, support resistance, çizgi grafik, bar chart, plot.
  Anthropic dataviz + xlsx + financial-services (deck-refresh) resmi akışlarına
  dayanır.
---

# Grafik Okuma & Grafikle Çalışma

Bir grafik sorusu geldiğinde otomatik uygula. İki mod var: **okuma/yorumlama**
ve **oluşturma**.

## A) Grafik Okuma / Yorumlama
Görsel bir grafik verildiğinde (ekran görüntüsü, chart):
1. **Ne tür grafik:** mum / çizgi / bar / dağılım.
2. **Eksenler ve ölçek:** zaman aralığı, fiyat/değer birimi.
3. **Yapı:** trend yönü, destek/direnç, bant kenarı, fitil/süpürme, boşluk (gap).
4. **Hacim/momentum** varsa oku.
5. **Yorum:** ne söylüyor + belirsizlik. Uydurma seviye verme; grafikte görünen
   sayıyı kullan.

> Not: Teknik analiz olasılıktır, kesinlik değil. "Olur" yerine "olabilir /
> olasılık şu" dilini kullan.

## B) Grafik Oluşturma
- **dataviz** becerisi: web/artifact grafikleri, dashboard, sparkline, heatmap,
  renk paleti, açık/koyu tema uyumu. Grafik kodu yazmadan ÖNCE dataviz
  rehberini uygula.
- **xlsx** becerisi: Excel içi grafik ve tablo.
- **deck-refresh** akışı: sunumdaki gömülü grafik/tabloları veriye yeniden bağla
  ve tazele.

## Çıktı
- Okuma modunda: yapı → yorum → belirsizlik.
- Oluşturma modunda: doğru grafik tipini seç, erişilebilir renk, net eksen/etiket.
