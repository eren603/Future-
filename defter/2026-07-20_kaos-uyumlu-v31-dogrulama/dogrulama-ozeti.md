# KAOS-UYUMLU v3 → v3.1 — Bağımsız Adversarial Doğrulama Özeti (append-only)

Workflow: `wf_c13d5d60` (6 bağımsız denetçi ajan, 59 araç çağrısı, ~20 dk) ·
Motor: `sistem/kaos-uyumlu-v3/motor.py` · Veri: 59 kapalı 15M + 21 kapalı 4H (BTCUSDT)

## Denetçi kararları (v3.0 üzerinde)

| Denetçi | Karar | Ana kanıt |
|---|---|---|
| Lookahead/sızıntı | **PASS** | Fiziksel kesme testi: t=40..59'un TAMAMI, gelecek barlar diskte hiç yokken bit-özdeş; sahte uç-bar/bozuk açık-bar testleri değişiklik üretmedi; indeks ihlali 0 |
| Determinizm | **PASS** | 5 koşu + 4 hash-seed → tek md5; yeniden serileştirme bayt-özdeş |
| Adaptiflik | FAIL → **düzeltildi** | Hacim x10/x0.1 ve fiyat x2'de karar alanları birebir aynı (ölçek bağımsızlığı ampirik doğru); ama beyansız 0.80 eşiği + sabit ondalık yuvarlama küçük fiyatta seviye çıktısını bozuyordu (x1e-6'da atr_zarf=[0.1,0.1]) |
| Dürüstlük/abstain | FAIL → **düzeltildi** | Rejim VERI_YETERSIZ iken sinyale "KARŞI-REJİM" damgası; hacim filtresi pencere yetersizken sessiz baypas (sentetik veriyle uyarısız SINYAL üretimi fiilen gösterildi) |
| Kod incelemesi | FAIL → **düzeltildi** | market_durumu'nda SHORT'u maskeleyen elif (sentetik repro: gerçek ayı kırılımında LONG basıyordu); FVG INVALID/iptal kuralı çelişkisi; ölü kod; alan tutarsızlıkları; --asof 0 çöküşü |

## v3.1 düzeltme doğrulamaları (bu depoda yeniden koşuldu)

- Ana koşu (asof 59): sinyal/pusu/market çekirdeği v3.0 ile aynı kaldı ✓
- Maskeleme reprosu: artık doğru **SHORT** ✓ · Bilinmeyen rejim: **rejim_bilinmiyor** ✓
- Sentetik hacim-baypas: sessiz SINYAL yok; "tespiti devre dışı" notu + uyarı ✓
- x1e-6 fiyat: seviyeler anlamlı (atr_zarf [0.064753883, 0.065187717]) ✓
- asof 0: temiz VERI_YETERSIZ ✓ · asof'suz: açık-bar uyarısı ✓
- Determinizm ve önek/kesme tutarlılığı v3.1'de yeniden doğrulandı ✓

## Walk-forward replay (t=35..59, TEK GÜN — ANEKDOT, istatistik DEĞİL)

- Hiçbir İZLE kaydı pencere içinde tam SİNYAL'e terfi etmedi; +860'lık 11:30-11:45
  rallisi, IZLE_LONG 12-barlık pencereden düştükten SONRA tamamlanmış sinyal olmadan geldi
  → `donus_pencere=12` sabitinin bu gün için dar kaldığı KAYDA GEÇti (tek güne bakıp
  sabiti değiştirmek aşırı-uyum olur; değişiklik ancak defter birikince, yeni sürümle).
- market_durumu okumalarından yalnız t=58'deki LONG bir sonraki barda teyit edildi
  (11:45 kapanış 64970.8 > 64915.4); t=38 SHORT ve t=43 LONG teyitsiz söndü —
  "teyitsiz market yok" kuralının değeri bu gün içinde üç kez görüldü.
- t=35'teki DONUS_SHORT kısa vadede ~-365 lehe gitti, gün içi ralliyle geçersizleşti.
- 4H rejimi 24/25 koşuda VERI_YETERSIZ idi (21 kapalı 4H şartı ancak t=59'da doldu):
  rejim koşullaması için 4H geçmişinin daha uzun yapıştırılması gerekir (≥40 bar önerilir).

## Güncel çıktı (asof 59 = C0 11:45 UTC): `guncel_cikti_asof59.json`

Pusu: FVG_BULL 64376.6–64807.1 (CE 64591.85, FRESH) + FVG_BULL 64087.6–64155.5 (TESTED) ·
Market: LONG, teyit "15M gövde kapanışı > 65048.3" · İzleme: IZLE_SHORT aşama2 (64337, zayıf) ·
4H: UP (fallback-eşik BAYRAKLI) + 4H_SSL_SWEEP_RECLAIM LONG-dönüş kolu · ATR zarfı 64753.9–65187.7.
