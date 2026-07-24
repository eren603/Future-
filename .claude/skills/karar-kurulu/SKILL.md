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

### 2) Beş danışman merceği — maksimum akıl yürütme
Her motor çıktısını beş bağımsız arketip-mercekten geçir ("The 5 Advisors";
mercekler birbirinden ETKİLENMEZ, her biri farklı kör noktayı yakalar):
1. **Muhalif / The Contrarian** — "bu ne yüzden ÇÖKER?" Kurulumu öldürecek
   senaryo (tepki riski, likidite tuzağı, geç giriş, dar menzil).
2. **İlk-Prensipler / First Principles** — problemi çıplak çerçevele; etiketleri
   at, ham yapıyı (trend/aralık, kenar mı orta mı) yeniden sor.
3. **Genişletici / The Expansionist** — kaçırılan yukarı/aşağı potansiyel;
   scalp mı yoksa daha büyük swing mi? (ama R'yi ŞİŞİRMEDEN — bkz. adım 4).
4. **Dış-Göz / The Outsider** — bağlamsız taze göz: "hiç işlem gerekir mi,
   yoksa orta-aralık chop mu?"
5. **Uygulayıcı / The Executor** — "Pazartesi somut ne yaparsın?" Net giriş/
   stop/hedef/geçersizlik ya da "şu tepkiyi bekle".
Beş mercek çelişirse sentez fail-closed'a yaklaşır; yakınsarsa güven artar.

### 3) Adversarial doğrulama (Skeptic)
Her görüşü **diğer motorların sayısıyla** karşı-sına. Dayanağı olmayan/tek-dönem/
overfit görüşü `verifier.confirmed=false` işaretle → ağırlığı otomatik düşer
(fable-judge mantığı). Kanıtla eşleşmeyen iddia karara tam ağırlıkla giremez.

### 3b) R:R tutarlılık kapısı — ŞİŞİRİLMİŞ R YASAK (mekanik, zorunlu)
Bir kurulumun R:R'si sunulacaksa (giriş/stop/hedef) ve o R **motorun kendi tek
kaynaklı çıktısı DEĞİLSE** (ör. 5 mercekte el ile swing hedefi/stop kuruldu),
`rr_denetim.py`'den GEÇMEDEN yayınlanamaz:
```
python3 scripts/rr_denetim.py --job rr.json   # {yon,entry,stop,target,atr}
```
Araç, DAR stopu (scalp ölçeği) UZAK hedefle (swing ölçeği) eşleştirip R'yi yapay
yükseltmeyi mekanik yakalar (ATR-ölçek): stop < ~1×ATR veya "uzak hedef + dar
stop" → **ŞİŞİRİLMİŞ** → çıktıda **R_gercekci** kullanılır, R_rapor değil. ATR o
koşunun kline'ından hesaplanır (uydurma eşik yok). Motorun kendi içinde-tutarlı
R'si (stop ve hedef aynı ölçekte) TUTARLI geçer. Bu, "serbest ayar/aşırı-uyum"
panzehiridir: cazip ama aritmetiği tutmayan R karara giremez.

### 4) Başkan sentezi — sentez.py ile TEK karar
Görüşleri + doğrulayıcı oylarını JSON'a koy ve çalıştır:
```
python3 scripts/sentez.py --job job.json
```
Motor **güven-ağırlıklı** (çoğunluk oyu değil) yön skoru, uzlaşı, muhalefet ve
fail-closed karar kapıları uygular. Zayıf skor / düşük uzlaşı / düşük yön-ağırlığı
→ otomatik **NÖTR-BEKLE** (işlem yok).

## Çıktı (nihai karar kartı)
`YON_BIAS (LONG/SHORT)` · `KARAR (LONG/SHORT/NÖTR-BEKLE)` · `güven_skoru` ·
`yön_skoru` · `uzlaşı` · `muhalefet` · `geçersizlik_koşulu` ·
`danışman_özeti (kanıt + doğrulama)`.

### ⚠️ YÖN ile KARAR AYRIDIR (zorunlu sunum)
`YON_BIAS` alanı `yon_skoru` işaretinden gelir ve **KARAR kapısından
bağımsızdır**: kapı NÖTR-BEKLE dese bile ağırlıklı kanıtın yönü (LONG/SHORT)
her zaman basılır. Kullanıcıya iki satır ver:
1. **YÖN:** `YON_BIAS` (long/short) — saklanmaz, "BEKLE" ardına gizlenmez.
2. **İŞLEM KALİTESİ:** `KARAR` — temiz giriş var mı, yoksa "yön X ama temiz
   giriş için Y'yi bekle" mi.
NÖTR-BEKLE bir **işlem-kalitesi** hükmüdür, yön reddi değil.

> **Not (kapı kaynağı — doküman-kod hizası):** R≥1.35 ve confluence kapıları
> `sentez.py`'de DEĞİL, işlem-kalitesi motorlarındadır: `karar-motoru`
> (R≥1.35 gerçek risk-ödül kapısı) ve `grafik-calisma/confluence.py`
> (min_rr + confluence + setup_dogrulama kapıları). `sentez.py` yalnız
> danışman görüşlerini güven-ağırlıklı birleştirir (skor/uzlaşı/yön-ağırlığı
> kapıları). Yani "temiz giriş" hükmü bu motorlardan gelir; kurul sentezi onu
> raporlar, kendi içinde R hesaplamaz. Motor BEKLE
verdiğinde bile motorun zincir-1/2 iç kurulumunun giriş/stop/T1'i motordan
okunup verilir (uydurma değil).

## Birleşik sentez çıktı formatı (STANDART — her karar analizinde)
Nihai çıktı DAİMA şu tek-temiz yapıda verilir (motor mekaniği + 5 mercek
çerçevesi, şişirilmiş sayı olmadan):
1. **Motorlar (kanıt):** karar-motoru/turev/sentez'in gerçek sayıları — her biri
   dosyadan okundu, tek satır.
2. **5 mercek (çerçeve):** Muhalif/İlk-Prensipler/Genişletici/Dış-Göz/Uygulayıcı
   — kısa, her biri bir motor/panel kanıtına bağlı (anlatı için sayı uydurma).
3. **YÖN (bias):** `YON_BIAS` — saklanmaz.
4. **İŞLEM KALİTESİ:** temiz giriş var mı / tepki bekle; seviyeler **motordan**
   (fact) ve varsa el-ile swing çerçevesi **rr_denetim'den geçmiş R** ile
   (yorum olarak etiketli). **"R_rapor" değil, ŞİŞİRİLMİŞSE "R_gercekci".**
5. **Gerçek/varsayım/yorum ayrımı:** motordan gelen = gerçek; el-ile türetilen
   (swing seviyesi/R) = yorum, açıkça etiketli.

## Zorunlu disiplin
- Kararı **motor çıktılarına** dayandır; hiçbir motor sonuç üretmeden karar verme.
- Çelişki/belirsizlikte **BEKLE** meşru ve doğru karardır (fail-closed).
- Çıktı **karar-destektir, sinyal/garanti değil**; canlı/otomatik emir **yok**.
- Doğruluk sözleşmesi: gerçek/varsayım/yorum ayrılır, "VERİ YOK" işaretlenir.
- **Şişirilmiş R yasak:** stop/hedef içeren her R, motorun tek-kaynaklı çıktısı
  değilse `rr_denetim.py`'den geçer; ATR-tutarsız (dar-stop+uzak-hedef) R
  yayınlanamaz — `R_gercekci` kullanılır. Cazip anlatı ≠ geçerli aritmetik.
- **Narrative-fluency yanılgısına düşme:** akıcı/etkileyici çıktı otomatik "daha
  kaliteli" değildir; başlık sayıları araç-bağımsız (ATR/aritmetik) sınanır.
