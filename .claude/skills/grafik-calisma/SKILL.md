---
name: grafik-calisma
description: Grafik/ekran görüntüsü ve OHLCV için kaynak ve kapanış zamanını doğrula, aktif SMC bölgelerini incele, yapı yönü ile ilk hareketi ayır ve koşullu giriş/stop/hedef hesapla. Binance15m/1h/4h karşılaştırmalarında chart_workflow kullan; puanı olasılık, kalibrasyonu tek başına başarı kanıtı sayma.
---

# Grafik çalışma

## Veri ve görsel sözleşmesi

Sembol, piyasa, fiyat türü, periyot ve UTC kesimini belirle. C0 son kapanmış mumdur; açık ve C0 sonrası kapanışları dışarıda bırak ve sayısını kaydet. `candle_contract.py` tek normalizasyon kaynağıdır: Binance kline dizileri veya OHLCV nesneleri, `cutoff`/`c0`/`as_of`, açılış/kapanış zamanı ve `timeframe` kullanılır. Çelişkili kesim, bozuk OHLC veya karışmış zaman sessizce kabul edilmez. Zamansız eski veri yalnız `time_unverified` taslak üretir.

Özgün ekranı aç; yalnız gözlenebilen seviyeleri işaretle. Piksel ölçümü yaklaşık olup okunabilir eksen dayanaklarına bağlanır. Görsel verinin yerine mum uydurma. 4h dış yapı, 1h ara bağlam, 15m yerel tetik olarak incelenebilir; bu roller tek başına doğruluk kanıtı değildir. Ana yapı düşerken ilk bacak yukarı retracement olabilir. Kurulu Kör Grafik C0 ve yaşam döngüsü protokolü uygulanıyorsa onun daha sıkı kurallarını koru.

## Kullanıcıya grafik planı

`chart_workflow.py` aynı sözleşmenin 15m/1h/4h girdilerini bir kesimde doğrular, analistin kaynaklı gözleminden tek karar kartı üretir ve değişiklik denetimli yerel sonuç kaydı tutar:

```bash
python3 .claude/skills/grafik-calisma/scripts/chart_workflow.py prepare case_job.json --output prepared.json
python3 .claude/skills/grafik-calisma/scripts/chart_workflow.py plan prepared.json observation.json --output decision.json
python3 .claude/skills/grafik-calisma/scripts/chart_workflow.py --help
```

Gözlemde ilk bacak yönü, ana yapı, kaynak mum referansları, giriş bölgesi/türü/koşulu, stop, hedefler, ufuk ve geçerlilik bulunur. Yön analistin çıkarımıdır; kod bunu piyasa sonucu diye doğrulamaz. `confirmed` tetik koşulunun gözlendiği anlamındadır; istatistiksel onay veya kâr garantisi değildir. Giriş koşulluysa yön ve bölgeler korunur, durum açıkça koşullu yazılır.

Fiyat adımı, giriş aralığının iki ucunda R:R ve açık maliyet varsayımları hesaplanır. Ücret/kayma bilinmiyorsa net sonuç bilinmiyor kalır. Özgün görüntüye ölçülü işaretleme için Chart Calculation Workbench; ham OHLCV'den yeni SVG için `grafik-cizim` kullanılabilir. Çizim ile metin aynı karar kaydından gelmeli ve render açılıp kontrol edilmelidir.

## SMC yardımcı hesaplama

`smc_tespit.py` onaylanabilir zamanıyla pivotları ve kapanış kırılımlarını hesaplar. Aktif likidite/OB/FVG listeleri ile tarihsel listeler ayrıdır. Alınmış hedef veya geçersiz OB yeni girişte kullanılamaz. Son olayın yönü dış yapı bağlamıdır; kendi başına sonraki ilk bacak değildir.

`confluence.py` aday giriş bölgelerini ayrı puanlar; başka bölgedeki kanıt aynı girişin puanına eklenmez. Aynı olay ailesi bağımsız oy sayılmaz. Açık hedef, geçerli yapı, zaman ve taze aday tetik olmadan taslak çalışması yapılabilir, onaylı işlem denemez. Varsayımsal impuls ucu açık likidite diye sunulmaz. `plan_yonu`/`plan_durumu` taslak ile uygulanabilirliği ayırır; `yon_bias` yapısal bağlamı korur.

## Tarihsel değerlendirme ve kalibrasyon

Algoritmik edge değerlendirmesi isteniyorsa:

1. Normalleştirilmiş, C0'a kadar kapanmış geçmişi sabitle.
2. `setup_dogrulama.py` ile eğitim bölümünde parametreleri seç, sonraki ayrılmış dönemde dondurulmuş parametreleri değerlendir.
3. Sayısal `confluence_thresholds` ve `thresholds_kaynak` alanlarını SMC/confluence girdisine aktar. Açıklama nesnesini sayısal `min_rr` yerine verme.
4. `sinyal_izni`/`validated_edge` yalnız belirtilen ayrılmış dönemin kanıt kapsamını taşır. Yetersiz kanıtta yapısal eğilim ve koşullu plan kalabilir; sonuç yüksek isabet diye yayımlanmaz.
5. Kalibrasyon geçmiş kazananlara göre ayarlanıp aynı getiride kanıtlanamaz. Referansla giriş, maliyet, kapasite, takip penceresi ve hedef/stop kuralı eşleştirilmelidir.

`kalibrasyon.py` Wilson, zaman/blok bağımlılığına dikkat edilen belirsizlik ve işlem yürütme yardımcılarını içerir. FVG dolum/ömür oranında tamamlanmamış takipler ayrıca belirtilir. `backtest.monte_carlo` sabit getirilerin sırasını değiştirir; gelecekte kâr olasılığı ölçmez. Wilson'dan türetilen gerekli R, uygulanabilir hedef önerisiyle ayrı tutulur; üstten kırpılmış değer konservatif gerekli sınır diye sunulmaz.

Kaynak ve yöntem ayrıntıları: [kalibrasyon-kaynaklar.md](references/kalibrasyon-kaynaklar.md). Puanlar ve tasarım eşikleri gözlenmiş başarı oranı değildir.

## Sonuç ve doğrulama

Kullanıcıya sözleşme/C0, ana yapı, ilk hareketin dayanağı, giriş koşulu/bölgesi, stop/geçersizlik, T1/T2, R aralığı ve iptal koşulunu kısa yaz. İleri sonucunu görmeden planı dondur. Tetiklenmeyeni kazanç/kayıp sayma; yerel dosya hash zincirini harici zaman damgası imzası gibi tanıtma.

Yeni regresyonlar `test_smc_regressions.py`, `test_calibration_regressions.py`, `test_chart_workflow.py` dosyalarındadır. Test sonucu yalnız çalıştırıldığı kaynak sürümü ve kapsamı için geçerlidir. Kod testi, kârlılık veya evrensel sıfır hata kanıtı değildir. Kullanıcıya yeni mimari veya tekrar model eğitimi önermeden önce somut eksik kanıtı belirle.
