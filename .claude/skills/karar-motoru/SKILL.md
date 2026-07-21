---
name: karar-motoru
description: >-
  15M + 4H Binance kline karar motoru koşusu. Kullanıcı kline verisi
  yapıştırdığında (15 dakikalık ve/veya 4 saatlik OHLCV seti, Binance REST
  formatı, JSON veya CSV), "motoru çalıştır", "koşu yap", "karar ver",
  "analiz et" dediğinde ya da yeni piyasa verisi gönderdiğinde OTOMATİK
  devreye girer — slash komutu gerekmez. Tetikleyici kelimeler (TR/EN):
  motor, koşu, karar, kline, candles, 15m, 4h, veri gönderiyorum, run engine.
  Motor kodu: engine/karar_motoru.py; hafıza: engine/state/.
---

# Karar Motoru Koşusu

Motorun tek görevi: her koşuda TEK karar (LONG/SHORT/BEKLE) + giriş/stop/
iptal/T1-T2/R + önceki kararın akıbeti. Spesifikasyon: `engine/README.md`.

## Koşu akışı (her veri gelişinde aynen uygula)

1. **Veriyi kaydet:** kullanıcının yapıştırdığı 15M kline setini
   `engine/girdi/m15.json`, 4H setini `engine/girdi/h4.json` dosyasına yaz
   (format neyse olduğu gibi; motor JSON/CSV/Binance listesini kendisi çözer).
   Eksik taraf varsa (yalnız 15M veya yalnız 4H) eksik olanı İSTE; önceki
   koşudan kalan bayat dosyayla ASLA tamamlama.
2. **Motoru çalıştır:**
   `python3 engine/karar_motoru.py --m15 engine/girdi/m15.json --h4 engine/girdi/h4.json`
3. **Çıktıyı OLDUĞU GİBİ ver.** Motorun bastığı bloklar (ÖNCEKİ KARAR AKIBETİ /
   SABİTLER / EŞİKLER / KARAR / NEDEN / GİRİŞ / STOP / İPTAL / T1-T2 / R /
   UYARI) değiştirilmez, süslenmez, senaryo çatalı eklenmez. Motor çıktısının
   üstüne veya altına ikinci bir alternatif yön YAZILMAZ.
4. **Hafızayı kalıcılaştır:** koşu sonrası `engine/state/durum.json` ve
   `engine/state/defter.jsonl` değişti — bu iki dosyayı commit edip
   `claude/trading-engine-spec-k8q8u8` dalına push et. (Konteyner geçicidir;
   commit edilmeyen hafıza bir sonraki oturumda YOKTUR.)

## Yasaklar (motor sözleşmesi)

- Motorun verdiği sayıların dışında seviye uydurulmaz; motor BEKLE diyorsa
  elle sinyal üretilmez.
- Olasılık yüzdesi / isabet garantisi verilmez; isabet yalnız
  `engine/state/defter.jsonl` biriktikçe oradan ölçülür.
- Girdi kline dışı kaynakla (canlı API, tahmin) tamamlanmaz; veri yoksa
  "VERİ YOK" denir.

## Defter dökümü istenirse

Kullanıcı "defteri göster / isabet ne durumda" derse `defter.jsonl` satırlarını
say: sonuç dağılımı (STOP / İPTAL / T1 ve T2 / DEVRİLDİ / BELİRSİZ) + toplam
koşu sayısı. 30 kapanmış karardan az veri varsa bunu açıkça söyle: istatistiksel
hüküm için erken.
