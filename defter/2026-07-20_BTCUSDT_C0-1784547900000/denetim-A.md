# DENETİM-A — "Hesaplanmayan veri / karara girmeyen hesap" denetimi

Koşu: `2026-07-20_BTCUSDT_C0-1784547900000` · Tür: append-only ek (asıl rapor DEĞİŞTİRİLMEDİ)
Soru: Hesaplanmayan veri var mı? Hesaplanıp karara eklenmeyen hesap var mı? Nihai sonuca etkisi var mı?
Hesap dosyası: `denetim.py` (Decimal birincil yol; float64 + quote-taban çapraz oran ikinci yol)

## A. Ana koşuda HİÇ hesaplanmayan veriler (post-hoc hesaplandı)

| Kalem | Post-hoc sonuç | Etiket |
|---|---|---|
| Taker-buy oranı (tbb/v) — displacement 11:30 | %58.55 (quote çapraz %58.53) | CALCULATED |
| Taker-buy oranı — C0 (11:45) | %52.61 | CALCULATED |
| Taker-buy oranı — son 6 bar / oturum (59 bar) | %54.92 / %50.92 | CALCULATED |
| Delta proxy (2·tbb−v) — son 6 bar / oturum | +1392.4 / +1635.6 BTC | CALCULATED |
| Quote-volume + taker mutabakatı (3 tam 4H barı) | fark 0.000 (3/3) | CALCULATED |
| Close→open süreklilik (maks. sapma) | 15M: 0.10 · 4H: 0.10 | CALCULATED |
| Eşit-tepe kümeleri (Beceri-2 BSL tanımının parçasıydı; koşuda yalnız fraktal swing kodlandı) | %0.02 tol: {65039.80, 65048.30} · %0.05 tol: {65011, 65039.80, 65048.30}; eşit-dip kümesi YOK | CALCULATED |
| Video (10.2 MB) | işlenmedi — içerik bilinmiyor | VERİ YOK |

## B. Ana koşuda hesaplanıp KARARDA kullanılmayan kalemler

- Geçmiş sweep listesi (02:45 güçlü BSL-SFP close_loc 1.00; 11:00 zayıf BSL-SFP 0.35) — sabit kural gereği son BOS belirleyici olduğundan karara girmedi.
- ATR zarfının alt bandı 64753.88 (hiçbir plan öğesinde kullanılmadı).
- Kısmî dolu FVG 64087.60–64155.50 (PARTIAL_to_64137) — derin stop 64137 ile çakışan destek; raporda anılmadı.
- C0 close_location 0.679 ve prl40 63736.10 — bilgi düzeyinde kaldı.

## C. Süreç gedikleri (sonucu değiştirmedi ama kayda geçer)

1. Rapordaki "derin stop → 1.08R" satırı elle hesaplanmıştı (v2.7 ikinci-yol kuralına aykırı).
   Post-hoc script doğrulaması: **1.0833** → sayı doğru, süreç gediği gerçek.
2. "Veri içinde süpürülmemiş TEK BSL = 65084.60" ifadesi **fraktal-teyitli** havuzlar için doğru;
   Beceri-2'nin tam tanımı (eşit-tepe kümeleri dâhil) uygulanmadığından eksik kapsamlıydı.
   Küme 65039.80–65048.30 ADAY havuzdur (65048.30 = C0'ın kendi tepesi, fraktal teyidi için
   2 kapalı bar gerekir → C0 anında teyitsiz; 65011 C0 fitiliyle zaten süpürülmüş).
3. Quote-volume kolonu ana mutabakata dahil edilmemişti (post-hoc: 3/3 birebir).

## D. Nihai sonuca etki değerlendirmesi

- **YÖN: DEĞİŞMEZ (LONG).** Sözleşme gereği yön yalnız yön_M + yön_Y birleşiminden çıkar; eksik
  kalemlerin hiçbiri bu iki motorun girdisi değil. Taker verisi yön lehine (displacement %58.5
  alıcı) ama zaten yön üretme/değiştirme yetkisi yok.
- **GRADE: DEĞİŞMEZ (B).** Bağlam uyarısı (hedef yolunda likidite bandı) duruyor; pozitif taker
  verisi uyarıyı silmez, grade yükseltme kuralı yok.
- **PLAN: seviyeler aynı, tek dürüstlük düzeltmesi R aralığında.** Eşit-tepe kümesi 65048.30,
  market teyit eşiğiyle (gövde kapanışı > 65048.30) zaten çakışık → market planı etkilenmez.
  Pusu-CE R_T1 dürüst aralık olarak yazılır: küme-hedef kabulünde **1.65R**, fraktal DOL1
  (65084.60) hedefinde **1.79R**; derin stopta sırasıyla 1.00R / 1.08R; T2(ATR) derin stopta 1.31R.
- Video işlenmediği için etkisi **bilinemez** (VERİ YOK); bu bir belirsizlik olarak kalır.

## E. Sonraki sürüme (v2.8) öneri listesi — bu koşuda UYGULANMADI (motorlar donmuş)

eşit-tepe/eşit-dip kümeleme, taker-delta bağlam bayrağı, quote-volume mutabakatı,
rapor içinde elle aritmetik yasağının otomasyonu (tüm R değerleri script çıktısından).
