# Karar Motoru v1 — Spesifikasyon

15M (taktik) + 4H (stratejik) Binance kline setinden her koşuda TEK karar
üreten deterministik motor. Kod: `karar_motoru.py`. Test: `self_test.py`.

## İlkeler (kullanıcı spesifikasyonundan)

1. **Sabit mutlak eşik yok.** Hacim = son 96 barın yüzdelik sırası; gövde =
   son 48 barın q90'ı; 4H trend = |MA5−MA20| farkının kendi geçmişinin q60'ı.
   Her koşuda o anki verinin dağılımından yeniden hesaplanır ve çıktıda
   beyan edilir.
2. **Her koşuda tek karar:** LONG / SHORT / BEKLE. Senaryo çatalı yasak.
   BEKLE tek satır gerekçeyle meşru bir karardır.
3. **Karar zinciri (ilk tutan kazanır):**
   1. Tamamlanmış dönüş dizisi: likidite süpürmesi → geri alım (aynı-bar veya
      ≤6 bar gecikmeli) → karşı yönde yüksek-hacim displacement (FVG bırakır)
      → BOS. Giriş = displacement FVG'si (CE), stop = süpürme ucu.
   2. 15M yapı kırılımı (MARKET): son teyitli swing gövdeyle kırılır (C0),
      teyit = sonraki 15M gövde kapanışı C0 ekstremi ötesinde; 4H rejim karşı
      değilse yön alınır.
   3. 4H rejimi (PUSU): rejim UP/DOWN + fiyat hizasında açık 15M FVG varsa
      FVG bölgesinden giriş.
   4. BEKLE.
4. **Hafıza = hesap verme + seviye taşıma; yön ağırlığı DEĞİL.**
   - `state/durum.json`: son karar, takip edilen açık karar, açık FVG'ler,
     son swingler, 4H rejim, dönüş dizisi durumu.
   - Her koşu önce önceki açık kararın akıbetini yeni fiyat yolundan etiketler
     (TETİKLENMEDİ / İPTAL / STOP / T1 ve T2 / AÇIK / BELİRSİZ / DEVRİLDİ) ve
     `ÖNCEKİ KARAR AKIBETİ` satırında raporlar; kapanan karar
     `state/defter.jsonl`'a yazılır. Karar zinciri her koşuda SIFIRDAN çalışır —
     önceki yön yeni karara ağırlık olarak girmez (çapa/hedef-donması önlemi).
5. **Erken uyarı:** dönüş dizisi 2/4 veya 3/4 ise karar bloğu değişmeden tek
   satır `UYARI` basılır (taraf değişimi sezgisi, karar değil).
6. **Depo risk kuralı:** R (T1'e) < 1.35 ise karar BEKLE'ye düşer
   ("Analiz yapma komutu" 5_RISK ile uyum).
7. **Dürüstlük:** olasılık yüzdesi üretilmez; isabet yalnız defterden ölçülür.
   Yetersiz veride motor eşik uydurmaz, "VERİ YOK / YETERSİZ" der (rc=1).

## Beyan edilen yapısal sabitler

`N_VOL=96, VOL_RANK_MIN=0.80, N_BODY=48, BODY_Q=0.90, MA=5/20, TREND_Q=0.60,
TREND_HIST=120, SWING_K=2, FVG_LOOKBACK=96, RECLAIM_MAX=6, DISP_MAX=12,
RECENT_N=24, R_T1/T2_FALLBACK=1.5/2.5, R_MIN=1.35`
Bunlar kalibrasyon değil yapı tanımıdır; her çıktıda basılır. Değişiklik ancak
defter verisiyle gerekçelendirilir.

## Kullanım

```bash
python3 engine/karar_motoru.py --m15 engine/girdi/m15.json --h4 engine/girdi/h4.json
python3 engine/self_test.py   # mekanik doğruluk testi (isabet kanıtı değil)
```

Girdi biçimleri: Binance REST kline JSON'u (liste-listesi), obje listesi
(open/high/low/close/volume) veya CSV/boşluklu metin (ilk 6 kolon:
open_time, open, high, low, close, volume). Zaman damgası sn veya ms olabilir.

## Bilinen sınırlar (beyan)

- Girdi yalnız kline: spoof, OI, funding, likidasyon kaskadı GÖRÜLMEZ; bu
  kanallardan gelen manipülasyona karşı motor kördür ve bunu iddia etmez.
- Manipülasyon savunması kline izleriyle sınırlı: gövde-kapanış şartı (sahte
  kırılım), süpürme-dışı stop (stop avı), hacim yüzdelik şartı (hacimsiz
  kandırmaca).
- Aynı barda hem stop hem hedef menzildeyse akıbet BELİRSİZ etiketlenir;
  bar-içi sıra kline'dan bilinemez.
- İsabet oranı hakkında hiçbir iddia yok: defter <30 kapanmış karar iken
  istatistiksel hüküm verilmez.
