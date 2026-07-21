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
> Motorlar bağımsızdır → bağımsız tool çağrılarıyla aynı turda paralel çalışır.

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

## Çıktı (nihai karar kartı)
`KARAR (LONG/SHORT/NÖTR-BEKLE)` · `güven_skoru` · `yön_skoru` · `uzlaşı` ·
`muhalefet` · `geçersizlik_koşulu` · `danışman_özeti (kanıt + doğrulama)`.

## Zorunlu disiplin
- Kararı **motor çıktılarına** dayandır; hiçbir motor sonuç üretmeden karar verme.
- Çelişki/belirsizlikte **BEKLE** meşru ve doğru karardır (fail-closed).
- Çıktı **karar-destektir, sinyal/garanti değil**; canlı/otomatik emir **yok**.
- Doğruluk sözleşmesi: gerçek/varsayım/yorum ayrılır, "VERİ YOK" işaretlenir.
