---
name: turev-akis
description: >-
  Türev-akış (perp deriverisi) erken-uyarı motoru. Bir soru ya da veri açık
  faiz (OI/Açık Faiz), funding/fonlama oranı, CVD (kümülatif hacim deltası),
  taker Long/Short Ratio (LSR), likidasyon/tasfiye dengesizliği, deleveraging,
  short squeeze, pozisyon boşalması ile ilgili olduğunda ya da kullanıcı
  CoinGlass/borsa türev paneli gönderdiğinde OTOMATİK devreye girer — slash
  komutu gerekmez. Çalışan motor: scripts/turev_akis.py (OI/fiyat matrisi +
  funding + CVD + LSR + likidasyon → sayısal yön skoru + erken-uyarı bayrakları).
  Tetikleyici kelimeler (TR/EN): türev, açık faiz, open interest, OI, funding,
  fonlama, CVD, volume delta, taker, long short ratio, LSR, likidasyon,
  tasfiye, liquidation, deleveraging, squeeze, coinglass, perp, kaldıraç akışı.
  karar-motoru YALNIZ kline görür (türeve kördür); bu motor o boşluğu doldurur.
---

# Türev-Akış Motoru (kline-körlüğü panzehiri)

## Neden var
`karar-motoru` yalnız 15M+4H kline üzerinden karar verir ve `engine/README.md`de
açıkça belirtildiği gibi **OI, funding, likidasyon kaskadı, CVD gibi türev
kanallarına kördür.** Bu veriler CoinGlass ekran görüntülerinden okunuyordu ama
yalnız **sözel** olarak kurula giriyordu — hiçbir mekanik motora bağlı değildi.
Bu motor onları **sayısal bir yön skoruna** çevirir; böylece deleveraging /
taze-short / squeeze gibi türev sinyalleri karara **ölçülerek** dahil olur.

## Ne zaman çalışır (otomatik)
Kullanıcı CoinGlass/borsa türev paneli (ekran görüntüsü veya video karesi)
gönderdiğinde ya da OI/funding/CVD/LSR/likidasyon sayıları elde olduğunda.
**Karar-motoru koşusuyla birlikte** çalışır: motorun kline kararı + bu motorun
türev skoru birlikte `karar-kurulu`ya gider.

## Nasıl çalıştırılır
Panelden okunan değerleri job JSON'a koy (eksik alan yazma → motor "VERİ YOK"
işaretler, fail-closed) ve çalıştır:
```
python3 scripts/turev_akis.py --job job.json
```
Girdi alanları (hepsi opsiyonel; en az biri gerekli):
- `price_series` + `oi_series` — **kronolojik HİZALI** (OI/fiyat matrisi; motorun kalbi)
- `funding` (%), `cvd_series`, `taker_lsr`, `liq_long`/`liq_short` ($M)

## Çıktı
`KARAR_TUREV` (AYI/NÖTR/BOĞA + güç) · `yon_skoru` [-1,+1] · `kapsam` (okunan alan
oranı) · `guven` · faktör dökümü (her sinyalin skoru+gerekçesi) · **erken_uyari**
bayrakları (DELEVERAGING / TAZE SHORT / SOĞUMA) · `varsayimlar` defteri.

## OI/fiyat matrisi (erken-uyarının kalbi)
| OI | Fiyat | Okuma |
|----|-------|-------|
| ↑ | ↑ | taze LONG / sağlıklı trend (boğa) |
| ↑ | ↓ | **taze SHORT giriyor** (ayı, konviksiyonlu) |
| ↓ | ↑ | short kapama (zayıf boğa) |
| ↓ | ↓ | **long tasfiyesi / deleveraging** (ayı; dip-tükenme de olabilir) |

## Zorunlu disiplin
- **Uydurma yasak:** panelde okunmayan sayı girilmez; eksik alan "VERİ YOK".
- Eşikler `varsayimlar` defterinde açık (funding/OI/LSR konvansiyonları); gizli sabit yok.
- Bu skor türev verisini **karara dahil eder, geleceği bilmez** — garanti değil.
- ⚠️ Yalnız analiz/karar-destek; canlı/otomatik emir **DAHİL DEĞİL**.

## Diğer becerilerle (paralel)
- `karar-motoru` → kline kararı; bu motor → türev katmanı. İkisi `karar-kurulu`da birleşir.
- `grafik-calisma` → SMC/likidite yapısı; türev skoru onun yön-biasını teyit/çürütür.
- `video-isleme` → CoinGlass video karesinden OI/CVD/LSR okur → bu motora besler.
- `uzman-modu/iddia_denetim.py` → türev iddiaları da yayın öncesi denetlenir.
