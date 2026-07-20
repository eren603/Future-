---
name: finansal-veri-analizi
description: >-
  Finansal veri analizi becerisi. Bir soru veri analizi, finansal tablo
  yorumlama, Excel/CSV inceleme, finansal oran, trend, kripto veya hisse verisi
  yorumlama, model/tablo denetimi ile ilgili olduğunda OTOMATİK devreye girer —
  hiçbir slash komutu gerekmez. Kapsam: finansal tablo analizi, Excel modeli
  denetimi (formül izleme, hardcode/sabit-değer tespiti, denge kontrolü), veri
  temizleme/normalize, oran analizi, canlı piyasa/kripto verisini analiz etme.
  Tetikleyici kelimeler (TR/EN): analiz, analysis, veri, data, finansal tablo,
  financial statement, oran, ratio, trend, Excel denetimi, audit, CSV, tablo,
  kripto veri, fiyat verisi, hacim, volume, likidite.
  Anthropic financial-services (audit-xls, clean-data-xls) ve claude-cookbooks
  (analyzing-financial-statements) resmi akışlarına dayanır.
---

# Finansal Veri Analizi

Bir analiz/veri sorusu geldiğinde otomatik uygula.

## Genel disiplin
- **Önce veriyi doğrula.** Eksik/çelişkili alanları "VERİ YOK" işaretle.
- **Gerçek / varsayım / yorum** ayrımını her bulguda koru.
- Sonuç iddiası ("yükseliyor", "sağlıklı") mutlaka **sayısal dayanağa** bağlanır.

## Alt-akışlar

### 1) Finansal Tablo Analizi
- Gelir tablosu: gelir büyümesi, brüt/net marj, faaliyet kârı trendi.
- Bilanço: likidite (cari oran), kaldıraç (borç/özkaynak), işletme sermayesi.
- Nakit akışı: faaliyet nakdi kalitesi, serbest nakit akışı.
- **Oranlar:** ROE, ROA, cari oran, borç/FAVÖK, brüt marj — dönemler arası kıyas.

### 2) Excel Modeli Denetimi (audit)
- Formül izleme: hücre bağımlılıklarını takip et.
- **Hardcode tespiti:** formül içine gömülü sabit sayıları işaretle.
- Denge kontrolü: bilanço tutuyor mu, toplamlar doğru mu.
- Kırık referans / #REF / dairesel bağımlılık taraması.

### 3) Veri Temizleme / Normalize
- Tutarsız birim, tarih formatı, eksik satır, aykırı değer (outlier) temizliği.
- Sonuç: analize hazır düzgün tablo.

### 4) Canlı Piyasa / Kripto Verisi Analizi
Bu oturumda bağlı MCP araçlarını kullan (varsa):
- **Crypto.com MCP** — candlestick (mum), orderbook, ticker, işlemler.
- **LunarCrush** — kripto sosyal/piyasa metrikleri.
- **Bigdata.com** — finansal duygu (sentiment), ETF künyesi.
Ham veriyi çek → trend / hacim / volatilite / destek-direnç çıkar → yorumla.
Veri çekilemiyorsa bunu açıkça söyle, tahmin etme.

## Çıktı
- **Bulgular** (sayısal, dayanaklı) → **yorum** → **belirsizlikler**.
- Tablo/grafik gerekiyorsa `grafik-calisma` becerisine devret.
