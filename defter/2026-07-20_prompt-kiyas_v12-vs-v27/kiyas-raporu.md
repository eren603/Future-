# PROMPT KIYAS DENETİMİ — C0-VETO v1.2 (olasılıksal) vs v2.7-PRAGMATİK (plan)

Tarih: 2026-07-20 · Ortak test verisi: `2026-07-20_BTCUSDT_C0-1784547900000` koşusunun TIER-1 seti
(59 kapalı 15M + 21 kapalı 4H) · Hesap: `kiyas_v12.py` (ikinci-yol assert'leri geçti)
Girdi SHA-256: v1.2 dosyası `867f2000-Kimianalizpromptu.txt` — depoda; v2.7 `8d590434d12c…`

## 1. Aynı C0 üzerinde iki prompt'un fiilî çıktısı (CALCULATED)

| Katman | v1.2 (Kimi) | v2.7 PRAGMATİK | Uyum |
|---|---|---|---|
| ATR14 | 180.7643 | 180.7643 | AYNI |
| 4H eğilim | tb=+1 (rel +0.64% > eşik 0.21%) | trend_dir=UP (MA farkı +412.67) | AYNI YÖN |
| 40-bar referans | prh 64940 / prl 63736.1 | prh 64940 / prl 63736.1 | AYNI |
| Kırılım tespiti | rejim 7 BREAKOUT-EXPANSION (zincir ④), olay ev10 SH (yapı kayması yukarı), hücre 82, aile KIRILIM-VOL | tetik BREAKOUT_UP + BOS UP + AMD-boğa | AYNI OLGU, farklı dil |
| Momentum/kalite | mom1 +0.91, ER10 0.77, mb +0.95, volz +1.13, ratio 1.90 EXPANDING (sabit eşik damgalı) | close_loc 0.68, displacement 2.7×ATR | TUTARLI |
| ±1.2×ATR çerçevesi | hedef 65187.7 / stop 64753.9 | ATR zarfı 65187.72 / 64753.88 | AYNI (tanım özdeş) |
| Nihai çıktı | 3 olasılık vektörü (K3) + rejim etiketi; endpoint max p < 0.45 ise ABSTAIN | YÖN=LONG, GRADE=B, giriş/stop/hedef/R planı | FARKLI TÜR ÇIKTI |

K3 vektörleri v1.2'de FORMÜLSÜZ (model yargısı gerektirir). Bu koşu için ürettiğim örnek vektörler
(etiket: MODEL-YARGISI, kalibrasyonsuz): first_leg UP .58 / DOWN .22 / NEITHER .12 / AMB .08;
endpoint_16 UP .42 / FLAT .30 / DOWN .28 → **max .42 < .45 → v1.2 resmî çıktısı ABSTAIN olurdu**
(bekçi-e tetik); first_passage TARGET .38 / STOP .25 / NEITHER .32 / AMB .05.

## 2. Veri yeterliliği (kullanıcının fiilî veri diyetiyle)

| Gereksinim | v1.2 | v2.7 |
|---|---|---|
| 60-bar yapı bandı (rpos) | 59 bar var → EKSİK damgası | gerekmiyor |
| 96-bar robust-z (bekçi-b) | HESAPLANAMAZ | gerekmiyor |
| 60 geçmiş ratio (quantile eşik) | yok → sabit eşik fallback | gerekmiyor |
| Ekran görüntüsü/heatmap | veto girdisi YASAK, sayı okuma yasak | TIER-2 kategorik bayrak olarak KABUL |
| Video | AÇIKÇA REDDEDİLİR ("video verisi kabul etme") | TIER-2 olarak işlendi (Denetim-B: CVD bulgusu ORADAN çıktı) |
| OI/funding sayısal | yoksa D4=NEU, rejim 10/11 üretilemez | yoksa TIER-2 bayrak, grade etkisi |
Sonuç: kullanıcının gönderdiği paket (60 bar + ekranlar + video) v2.7'ye TAM oturuyor;
v1.2 aynı paketin bir kısmını reddediyor, bir kısmında fallback'e düşüyor.

## 3. "Hangisi daha doğru karar veriyor" — olasılıksal denetim hükmü

**Ampirik cevap bugün ÜRETİLEMEZ (VERİ YOK):** iki prompt'un da çözümlenmiş tahmin/karar
geçmişi 0'dır. Tek ortak koşu (bu C0) çözümsüzdür; çözüm C0+16 kapalı barı
(12:00–15:45 UTC) gerektirir ve bu veri elde yoktur. Bu durumda "şu prompt %X daha
isabetli" cümlesi kurmak UYDURMA olur; kurulmamıştır.

**Yapısal (tasarım) denetimi — hangisi doğru karara daha yatkın:**
- v1.2'nin üstünlüğü: doğruluk MUHASEBESİ. Brier/log-loss/kapsama/kalibrasyon kovası,
  değiştirilemez tahmin kaydı, ABSTAIN ve bekçi-veto. İkisinden yalnız v1.2 kendi
  isabetini ZAMANLA KANITLAYABİLİR. Zayıf noktası: K3 olasılık üretiminin formülü yok →
  sayılar model yargısıdır; iki koşu aynı veriyle farklı vektör üretebilir
  (yeniden-üretilebilirlik düşük, sahte-kesinlik riski).
- v2.7'nin üstünlüğü: veri BÜTÜNLÜĞÜ ve eyleme dönüklük. Çift-yol doğrulama, SHA zinciri,
  agregasyon mutabakatı, deterministik yön motorları (aynı veri → hep aynı yön) ve
  giriş/stop/hedef/R planı. Zayıf noktası: kendini hiç SKORLAMAZ — "kalibrasyonsuz nitel
  sinyal" dürüst bir etiket ama defterde isabet ölçümü tasarım gereği yok.
- Bu C0'da somut fark: v2.7 LONG/B + plan verdi; v1.2 (endpoint max p < 0.45) ABSTAIN
  verirdi. Hangisinin "doğru karar" olduğu ancak sonuç verisiyle söylenebilir.

## 4. Hüküm ve protokol

Kullanışlılık: karar/plan isteyen kullanıcı için v2.7; ölçülebilir tahmin araştırması için v1.2.
Verimlilik: v1.2 koşu başına hafif (tek geçiş, grafiksiz); v2.7 ağır ama denetlenebilir artefakt bırakır.
Doğruluk: bugün eşitlik varsayılmak zorunda (kanıt yok); kanıt üretme KAPASİTESİ v1.2'de,
kanıt kalitesi altyapısı v2.7'de.

**Önerilen melez protokol (20 koşu):** her yeni C0'da (a) v2.7 motorları yön+plan üretir,
(b) v1.2'nin sonuç tanımları (first_leg / endpoint_16 / first_passage) ve Brier defteri
her koşuya bağlanır, (c) C0+16 dolunca üç etiket çözülür, hem v1.2 vektörleri Brier ile
hem v2.7 yön kararı isabet/kapsama ile skorlanır. ≥20 çözümlü koşudan sonra
"hangisi daha doğru" sorusu ilk kez SAYIYLA yanıtlanabilir.
İlk adım: 16:00 UTC sonrası 12:00–15:45 kapalı 15M barları yapıştırılırsa bu koşu (#1)
iki taraf için de çözülür (v2.7: 65084.6 hedefi mi 64316 iptali mi önce; v1.2: ±45.2 ve
±216.9 bantlarına ilk temas + uç nokta).
