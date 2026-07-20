---
name: finansal-modelleme
description: >-
  Finansal modelleme ve değerleme becerisi. Bir soru şirket/varlık değerleme,
  yatırım analizi, finansal model kurma, çarpanlar, nakit akışı, WACC, bilanço /
  gelir tablosu / nakit akış tablosu modelleme ile ilgili olduğunda OTOMATİK
  devreye girer — hiçbir slash komutu gerekmez. Kapsam: DCF, comps (benzer
  şirket analizi), LBO, 3 tablolu model, rekabet/pazar konumlandırma.
  Tetikleyici kelimeler (TR/EN): finans, değerleme, valuation, DCF, comps, LBO,
  financial model, çarpan, multiple, WACC, nakit akışı, cash flow, gelir tablosu,
  bilanço, income statement, balance sheet, yatırım getirisi, ROI, IRR, NPV.
  Anthropic financial-services + claude-cookbooks resmi skill akışlarına dayanır.
---

# Finansal Modelleme & Değerleme

Bir finans/değerleme sorusu geldiğinde bu akışı uygula. Kullanıcı komut yazmasa
da otomatik çalış.

## Genel disiplin
- **Uydurma yok.** Eksik veri "VERİ YOK" işaretlenir; sayı hayalden üretilmez.
- **Varsayımları ayır.** Her modelde girdi varsayımlarını (büyüme, iskonto,
  marj) ayrı ve açık listele.
- **Kaynak göster.** Kullanılan her rakamın nereden geldiğini belirt (kullanıcı
  verisi / connector / varsayım).

## Alt-akışlar

### 1) DCF (İndirgenmiş Nakit Akışı)
1. Serbest nakit akışı projeksiyonu (5–10 yıl).
2. WACC hesapla (özkaynak maliyeti + borç maliyeti, ağırlıklı).
3. Terminal değer (Gordon büyüme veya exit çarpanı).
4. Bugünkü değere indir → firma değeri → özkaynak değeri.
5. **Duyarlılık tablosu:** WACC × büyüme matrisi.

### 2) Comps (Benzer Şirket Analizi)
1. Karşılaştırılabilir şirket kümesini seç.
2. Çarpanları çek: EV/EBITDA, EV/Sales, P/E, P/B.
3. Medyan / çeyreklik dağılımı çıkar.
4. Hedef şirkete uygula → değer aralığı.

### 3) LBO (Kaldıraçlı Satın Alma)
1. Giriş değeri + finansman yapısı (borç/özkaynak).
2. Borç geri ödeme takvimi + faiz.
3. Exit varsayımı → IRR ve MOIC hesapla.

### 4) 3 Tablolu Model
Gelir tablosu → bilanço → nakit akış tablosu birbirine bağlı; **bilanço
denkliği** (Aktif = Pasif) her dönemde kontrol edilir.

### 5) Rekabet / Pazar Konumlandırma
Rakip kümesi, pazar payı, güç/zayıf yön, konumlandırma özeti.

## Çıktı
- Önce **tek cümlelik sonuç** (değer aralığı / karar).
- Sonra varsayımlar, hesap adımları, duyarlılık.
- Excel isteniyorsa `xlsx` becerisiyle tabloyu üret.
