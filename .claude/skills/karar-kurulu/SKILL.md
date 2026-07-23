---
name: karar-kurulu
description: >-
  Orkestratör / nihai karar becerisi. Bir soru KARAR gerektirdiğinde (al/sat/bekle,
  yön, "ne yapmalıyım", "nihai karar", "kurul kararı", "hepsini birleştir",
  karmaşık/çok yönlü değerlendirme) OTOMATİK devreye girer — slash komutu gerekmez.
  Depodaki diğer motorları PARALEL çalıştırır, 5 mercekle maksimum akıl yürütür,
  adversarial doğrulamadan geçirir ve TEK nihai karar üretir. Çalışan sentez
  motoru: scripts/sentez.py (güven-ağırlıklı; çoğunluk oyu değil). Tetikleyici
  kelimeler (TR/EN): karar, nihai karar, kurul, ne yapmalıyım, al/sat/bekle, yön,
  öneri, tavsiye, sonuç, birleştir, sentez, decide, final decision, verdict,
  recommendation.
  UnfairerVorteil/Expert-Council (5 mercek, tek oturum) + adversarial-review
  (Skeptic doğrulayıcı) + Karpathy LLM Council (güven-ağırlıklı sentez) desenine
  dayanır. ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.
---

# Karar Kurulu (Orkestratör)

Bir **karar** gerektiğinde bu beceri diğerlerini yönetir. Amaç: dağınık motor
çıktılarını **tek, gerekçeli, güven skorlu** karara indirgemek.

## Akış (4 aşama)

### 1) Fan-out — motorları PARALEL çalıştır
Soruya uyan tüm motorları birlikte koştur ve her birinden **yapısal bir görüş**
al (yön + güven + kanıt):
- `grafik-calisma` → SMC/Fib: yön + giriş/geçersizlik.
- `backtest-motoru` → strateji istatistiği + Monte Carlo sağlamlığı.
- `risk-yonetimi` → Kelly/pozisyon uygunluğu (kenar var mı?).
- `portfoy-optimizasyonu` → (çok varlıklıysa) ağırlık.
- `karar-motoru` → 15M/4H kline motoru kararı (varsa).
- `data-analysis-deep-scan` → sayısal teyit/çürütme.
- `turev-akis` → türev-akış (OI/funding/CVD/LSR/likidasyon) yön skoru **(fiyat-dışı tek kanal)**.
> Motorlar bağımsızdır → bağımsız tool çağrılarıyla aynı turda paralel çalışır.

#### Türev-akış danışmanı — FORMAL bağlama (öznel yorum devre dışı)
Analizde türev paneli (CoinGlass/borsa; ekran görüntüsü ya da video karesi)
mevcutsa `turev-akis` danışmanı **elle yazılmaz**, motordan üretilir:
```
python3 ../turev-akis/scripts/turev_akis.py --job turev.json --emit-advisor
```
Çıktı doğrudan bir kurul danışmanıdır: `stance` (yön skorunun işaretinden),
`confidence` (motorun `guven` alanı = kapsam × netlik), `evidence` (faktör
dökümü + erken-uyarılar). Bu danışmanı `advisors`'a olduğu gibi ekle; çıktının
`_verifier_confirmed` alanını `verifier["turev-akis"].confirmed`'e taşı (kapsam
< 0.5 ise false → çürütme penaltısı otomatik uygulanır). Motor "VERİ YOK"
(danışman None) dönerse kurula **eklenmez** (fail-closed). Böylece türev katkısı
öznel metin değil, tekrarlanabilir motor çıktısıdır.

### 2) Beş mercek — maksimum akıl yürütme
Her motor çıktısını beş bağımsız mercekten geçir (kullanıcının karar-kurulu
tasarımı): **Muhalif** (zayıflık/risk), **İlk-Prensipler** (asıl problem),
**Genişletici** (kaçırılan fırsat), **Dış-Göz** (basit gözden kaçan),
**Uygulayıcı** (uygulanabilir mi). Mercekler birbirinden etkilenmez.

### 3) Adversarial doğrulama (Skeptic)
Her görüşü **diğer motorların sayısıyla** karşı-sına. Dayanağı olmayan/tek-dönem/
overfit görüşü `verifier.confirmed=false` işaretle → ağırlığı otomatik düşer
(fable-judge mantığı). Kanıtla eşleşmeyen iddia karara tam ağırlıkla giremez.

### 4) Başkan sentezi — sentez.py ile TEK karar
Görüşleri + doğrulayıcı oylarını JSON'a koy ve çalıştır:
```
python3 scripts/sentez.py --job job.json
```
Motor **güven-ağırlıklı** (çoğunluk oyu değil) yön skoru, uzlaşı, muhalefet ve
fail-closed karar kapıları uygular. Zayıf skor / düşük uzlaşı / düşük yön-ağırlığı
→ otomatik **NÖTR-BEKLE** (işlem yok).

## Tek komut: GERÇEK paralel kurul koşusu (kurul_kosu.py)

Fan-out'u elle yapmak yerine `scripts/kurul_kosu.py` motorları **`tools/suru.py`
ile gerçekten paralel** koşar, her motor sonucunu otomatik danışmana çevirir ve
`sentez.py`'yi çağırıp **tek karar** üretir:
```
python3 scripts/kurul_kosu.py --plan plan.json
```
`plan.tasks[]` = `{name, script, job, weight, confidence_field?, evidence_fields?}`.
Akış: **suru (paralel fan-out) → sonuç→danışman eşlemesi → sentez**.
- Motor sonucunda yön (yon_skoru/score/…) yoksa o motor **çekimser** (oy vermez).
- Zaten danışman biçiminde çıkan motor (ör. `turev_akis --emit-advisor`) doğrudan
  kullanılır; `_verifier_confirmed` → doğrulayıcıya taşınır.
- Hiç danışman yoksa karar **NÖTR-BEKLE** (fail-closed). Çıktıya `paralel_kosu`
  (ok/fail/çekimser) şeffaflığı eklenir. Canlı/otomatik emir **DAHİL DEĞİL**.

## Çıktı (nihai karar kartı)
`KARAR (LONG/SHORT/NÖTR-BEKLE)` · `güven_skoru` · `yön_skoru` · `uzlaşı` ·
`muhalefet` · `geçersizlik_koşulu` · `danışman_özeti (kanıt + doğrulama)`.

## Zorunlu disiplin
- Kararı **motor çıktılarına** dayandır; hiçbir motor sonuç üretmeden karar verme.
- Çelişki/belirsizlikte **BEKLE** meşru ve doğru karardır (fail-closed).
- Çıktı **karar-destektir, sinyal/garanti değil**; canlı/otomatik emir **yok**.
- Doğruluk sözleşmesi: gerçek/varsayım/yorum ayrılır, "VERİ YOK" işaretlenir.
