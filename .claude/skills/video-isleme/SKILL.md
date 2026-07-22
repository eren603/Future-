---
name: video-isleme
description: >-
  Video işleme becerisi. Kullanıcı bir video dosyası gönderdiğinde (mp4, mov,
  webm, mkv, avi, ekran kaydı) ya da bir soru video, klip, kayıt, kare/frame
  çıkarma, video analizi, videodaki grafiği okuma ile ilgili olduğunda OTOMATİK
  devreye girer — slash komutu gerekmez. ffmpeg yoksa KENDİSİ KURAR
  (kendi-kendini onaran; "ffmpeg yok" hatası bir daha oluşmaz). Çalışan motor:
  scripts/video_isle.py — ffprobe metadata + sahne-değişimi tespiti + akıllı
  kare çıkarma (PNG). Çıkan kareler görüntü olarak okunur; video bir
  grafik/mum kaydıysa kareler grafik-calisma boru hattına verilir.
  Tetikleyici kelimeler (TR/EN): video, klip, kayıt, ekran kaydı, mp4, mov,
  webm, mkv, kare, frame, sahne, screen recording, extract frames.
---

# Video İşleme (kendi-kendini onaran)

Amaç: kullanıcının gönderdiği HER video işlenebilsin — "ffmpeg yok" hatası
bir daha yaşanmasın.

## Güvence zinciri (3 katman)
1. **SessionStart hook** (`.claude/hooks/session-start.sh`): oturum açılırken
   ffmpeg yoksa arka planda kurar.
2. **Motorun kendisi** (`scripts/video_isle.py`): her çağrıda `ensure_ffmpeg`
   çalışır — ffmpeg hâlâ yoksa apt-get ile KURAR, sonra işler. Hook yarım
   kalsa bile beceri kendini onarır.
3. **Fail-açıklama:** kurulum da başarısız olursa (ağ kapalı vb.) hata
   yutulmaz; kullanıcıya neden işlenemediği açıkça söylenir ("VERİ YOK"
   disiplini) — sessiz başarısızlık yasak.

## Akış (video geldiğinde otomatik)
1. Motoru çalıştır:
   ```
   python3 scripts/video_isle.py --job job.json
   ```
   Girdi: `{"input": "video.mp4", "out_dir": "<scratchpad>/frames",
   "max_frames": 12, "mode": "scene"}`
   - `mode: "scene"` → sahne-değişimi tespiti (ffmpeg `select=gt(scene,esik)`).
     Sahne sayısı yetersizse otomatik uniform örnekleme ile tamamlar.
   - `mode: "uniform"` → eşit aralıklı N kare.
   Çıktı: PNG kareler + JSON rapor (süre, çözünürlük, fps, codec, kare
   listesi + zaman damgaları).
2. Çıkan kareleri **Read ile görüntü olarak oku** ve içeriğe göre davran:
   - Mum/fiyat grafiği kaydıysa → `grafik-calisma` akışı (SMC + confluence;
     sayısal OHLCV yoksa "görsel-yaklaşık" etiketiyle).
   - Eğitim/anlatım videosuysa → kareleri kronolojik özetle.
3. Ses dökümü bu beceride YOK (whisper kurulu değil) — istenirse açıkça
   "ses dökümü için ek araç gerekir" denir, uydurma altyazı üretilmez.

## Sınırlar (dürüstlük)
- Kare = anlık görüntü; videodaki her bilgiyi yakalamaz (max_frames sınırı).
  Rapor hangi saniyelerin örneklendiğini listeler — kapsam gizlenmez.
- Grafik videosundan okunan seviyeler YAKLAŞIKTIR; kesin analiz için sayısal
  OHLCV istenir (grafik-calisma kuralı).
