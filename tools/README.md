# tools/ — Kimi K2.6/K3'ten uyarlanan çalışan yetenekler

Bu klasördeki araçlar **doğrudan çalıştırılır** — skill auto-trigger'a bağlı
değildir, tetikleyici kelime gerekmez. Hepsi **ek bağımlılık olmadan** çalışır
(numpy + stdlib; video için ffmpeg). Her biri `self_test.py` ile doğrulanır.

Kaynak esin: `anthropics/financial-services` karşılaştırması + Kimi K2.6/K3
(Moonshot AI) resmi yetenek listesi. Model-seviyesi özellikler (1M bağlam, açık
ağırlık, KDA mimarisi) uyarlanamaz; buradakiler **repo-seviyesi** uyarlanabilir
olanlardır.

## 1. `belge_ingest.py` — Belge + video ingest (kapalı hat)
Dosyayı host modelin görüşüne bağlı olmadan yerelde yapılandırılmış veriye çevirir.
- **xlsx/docx:** stdlib zipfile+xml · **pdf:** zlib (FlateDecode, best-effort)
- **csv/tsv/json/md/txt:** doğrudan · **video:** ffmpeg → kareler (grafik-calisma'ya hazır)
```bash
python3 tools/belge_ingest.py --file rapor.xlsx
python3 tools/belge_ingest.py --file klip.mp4 --frames-dir /tmp/kareler --fps 0.5
```
Çıkaramazsa **VERİ YOK** (uydurma yok).

## 2. `gorsel_dongu.py` — İteratif görsel/sinyal geri-besleme döngüsü
Grafik okuma tek atış değil: sinyal üret → hedef R:R'ye göre puanla → parametreyi
(fib + ATR-stop) OTE korkuluğu içinde ayarla → tekrar. Yakınsayana kadar döner.
```bash
python3 tools/gorsel_dongu.py --job job.json
# job: {"high":[...],"low":[...],"close":[...],"target_rr":2.0}
```

## 3. `suru.py` — Paralel alt-ajan orkestrasyonu
Repodaki motorları GERÇEKTEN paralel (thread + alt-süreç) koşar, sonuçları
güven-ağırlıklı birleştirir. Çelişki/zayıf sinyalde **NÖTR-BEKLE** (fail-closed).
```bash
python3 tools/suru.py --plan plan.json
# plan: {"tasks":[{"name","script","job","weight"}], "timeout":60}
```
⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.

## 4. `benchmark.py` — Standart eval/benchmark harness
Tüm motorların öz-testini bulur, koşar, geçti/kaldı + süreyi ölçer; `BENCHMARK.md`
(yayımlanabilir tablo) üretir. FAIL gizlenmez.
```bash
python3 tools/benchmark.py          # rapor yaz
python3 tools/benchmark.py --json   # sadece JSON
```

## 5. `dosya_skill.py` — Dosya → skill hattı
Bir belgeyi otomatik `SKILL.md` iskelesine çevirir (tetikleyici + bölümler
belgeden çıkarılır). İçerik uydurulmaz; boşsa VERİ YOK.
```bash
python3 tools/dosya_skill.py --file notlar.md --name benim-becerim \
    --out .claude/skills/benim-becerim/SKILL.md
```

## Doğrulama
```bash
python3 tools/self_test.py     # SELF_TEST_OK
```
