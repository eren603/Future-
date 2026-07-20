# KAOS-UYUMLU v3.1-ADAPTİF — 4H stratejik / 15M taktik bölge & dönüş motoru

Mod: **PAPER** · Sembol: kullanıcının yapıştırdığı Binance kline seti · Çalıştırma:

```
python3 motor.py <15m.json> <4h.json> --asof <kapalı bar sayısı>
```

## v3.1 — bağımsız adversarial doğrulama sonrası (workflow `wf_c13d5d60`, 6 denetçi)

PASS: lookahead (kesme + sahte-bar + indeks testleriyle sızıntı YOK), determinizm
(bit-özdeş, hash-seed bağımsız). FAIL→DÜZELTİLDİ: (1) market yönünde SHORT'u
maskeleyen `elif` (çift kırılımda artık daha YENİ teyitli swing kazanır +
`kirilim_taze` bayrağı); (2) 4H rejimi bilinmezken sinyale yanlış "KARŞI-REJİM"
damgası (artık `rejim_bilinmiyor`); (3) displacement hacim filtresinin pencere
yetersizken sessiz baypası (artık tespit DEVRE DIŞI + açık uyarı); (4) beyansız
sabitler (0.80 hacim eşiği, q90, 96/48 pencereleri, ATR 14, 1.2 zarf, FVG limiti —
tamamı `SABITLER` sözlüğünde ve her çıktıda); (5) sabit ondalık yuvarlamanın küçük
fiyatlı varlıkta seviye çıktısını bozması (referans-ölçekli 8 anlamlı hane);
(6) FVG INVALID tanımının ilan edilen iptal kuralıyla çelişkisi (gövde KAPANIŞI
kuralına hizalandı); (7) ölü kod/çift kontrol temizliği, `--asof` sınır korumaları,
displacement eşiğinin adayın KENDİ barının penceresinden hesaplanması.

## Kaos itirazına tasarım cevabı (neden "eski kalibrasyon tutmaz" sorununu çözer)

Kullanıcı itirazı: "piyasa dinamik/kaotik/manipülasyonlu; eski veriyle yapılan hiçbir
kalibrasyon/eşik bir sonraki trade'de tutmaz."

Bu itirazın DOĞRU çekirdeği: sabitlenmiş mutlak eşikler (örn. "hacim > 5000 ise") rejim
değişince bozulur (durağan-olmama). YANLIŞ çıkarımı: "o hâlde hiçbir istatistik işe
yaramaz" — bu kendi kendini çürütür; hiçbir düzenlilik kalıcı olmasaydı "yüksek
olasılıklı sistem" talebi de tanım gereği imkânsız olurdu. Kalıcılığı en güçlü bilinen
düzenlilik volatilite kümelenmesidir; motor bu yüzden HER ŞEYİ o anki pencerenin kendi
dağılımına normalleştirir:

1. **Sabit mutlak eşik yok.** Hacim eşiği yok → hacim YÜZDELİK SIRASI (son 96 bar
   içindeki rank; ölçek-bağımsız). Gövde eşiği yok → son 48 barın q90'ı. 4H trend
   eşiği → |MA5−MA20| farkının kendi geçmişinin q60'ı (geçmiş kısaysa getiri-tabanlı
   fallback, BAYRAKLI). Her koşuda yeniden hesaplanır; "dünkü eşik" diye bir şey yok.
2. **Yapısal tanımlar ayrı beyan edilir** (eşik değil, geometri tanımı): fraktal k=2,
   FVG üç-mum boşluğu, güçlü geri alım close_location ≥ 0.70, dönüş dizisi penceresi
   12 bar, gecikmeli geri alım 3 bar, ATR zarfı 1.2×. Bunlar dondurulmuş sözlüktür;
   değişiklik yeni sürüm gerektirir.
3. **Lookahead yasak.** Fraktal teyidi +2 bar gecikmeli kullanılır; `--asof N` ile
   geçmiş herhangi bir ana gidilir ve tam koşu = önek koşusu olmak zorundadır
   (doğrulama defterinde test edildi).
4. **Olasılık/isabet İDDİA EDİLMEZ, ÖLÇÜLÜR.** Çıktı yalnız SİNYAL / İZLE / YOK +
   VERİ-YETERSİZ üretir. "Yüksek doğruluk" bir vaat değil, append-only defterde
   walk-forward birikecek bir ölçümdür (≥20 çözümlü sinyalden önce hiçbir isabet
   yüzdesi telaffuz edilmez).
5. **Rejim koşullaması.** 15M sinyali 4H rejimiyle etiketlenir; karşı-rejim sinyali
   "KARŞI-REJİM" damgası taşır (kör karşı-trend market yok).

## Katmanlar

- **4H stratejik:** adaptif eşikli MA5−MA20 rejimi (UP/DOWN/NEUTRAL) + 4H swing
  haritası + dönüş-izleme kolu (4H SSL sweep-reclaim → LONG kolu; BSL sweep-reject →
  SHORT kolu).
- **15M taktik:**
  - **Dönüş dizisi (kullanıcının 'trend dönüşümü yakala' talebi):**
    ① likidite alımı (teyitli swing sweep) → ② geri alım (aynı-bar güçlü ≥0.70 /
    aynı-bar zayıf / ≤3 bar gecikmeli gövde) → ③ karşı yön displacement (gövde ≥ q90
    VE hacim rank ≥ 0.80) → ④ karşı yön BOS (gövde kapanışıyla teyitli swing kırımı).
    12 bar içinde dördü tamamlanırsa **DONUS SİNYALİ** (giriş bölgesi = displacement
    FVG/CE; iptal = sweep ekstremi). Eksikse **İZLE** (aşama numarasıyla).
  - **Pusu bölgeleri:** açık (FRESH/TESTED) FVG'ler + CE + iptal kuralı.
  - **Market durumu:** C0 kapanışı son teyitli swing'in ötesindeyse, yön + teyit şartı
    (sonraki 15M gövde kapanışı C0 ekstremi ötesinde) — kör market yok.
- **Defter:** her sinyal/İZLE değişimi append-only kayda; sonuç etiketleri
  (T1/iptal/16-bar uç nokta) doldukça isabet ölçülür.

## Bilinen sınırlar (dürüstlük beyanı)

- 59 kapalı barla hiçbir "yüksek doğruluk" iddiası MEŞRU DEĞİL; motor bu iddiayı
  üretmez. İsabet ancak ileriye dönük defterle kanıtlanır.
- "25 dakikalık giriş-çıkış" talebi: eldeki grid 15 dakikadır; 25dk grid yok
  (VARSAYIM: 15M kastedildi; istenirse 5M veri ile 25dk yeniden örnekleme eklenir).
- Manipülasyon/haber şoku modellenmez; motorun cevabı iptal kuralı ve rejim
  damgasıdır, tahmin değil.
- Adaptif eşikler rejimi GECİKMEYLE izler (pencere uzunluğu kadar atalet); bu
  gecikme yapısal olarak kaçınılmazdır ve gizlenmez.
