# v2.7-PRAGMATİK Pipeline Uygulaması — 2026-07-20 (C0=04:30Z)

0. ENVANTER: 10 dosya + 2 paste; hash'ler result.json'da. Beceri zip hash EŞLEŞTİ (a75cf0e2…).
1. PROFİL: K15 59 kapalı bar PASS · K4H 21 kapalı bar PASS · 15M→4H mutabakat 3/3 birebir · self_test.py=OK.
2. C0: 2026-07-20 04:15–04:30Z, OHLC 64674.40/64757.00/64602.00/64733.60 · was_live_forecast=false (gözlemci 04:30 sonrası ~30 sn açık mum gördü).
3. MEKANİK: yön_M=UP grade_M=B (gap4h=+0.718%>eşik 0.191%; tetikler nötr; ATR0=240.29).
4. YAPISAL: yön_Y=LONG (SSL 64610.2 sweep + close_location 0.849 güçlü geri alım; AMD: birikim 02:00–04:00, manipülasyon C0, dağılım TEYİT BEKLİYOR). Seviye haritası: stop adayı 64602 altı; DOL1=64887 (64887/64920/64940 kümesi); DOL2=65011–65084.6.
5. BAĞLAM (TIER-2): likidite_bandı=hedef_yolunda (65000–65100, CG-06 ekranları) · funding=+ (0.0032–0.0033%) · oi_eğimi=yatay (101.8K→101.9K) · liq_baskın=long (907.3) · 4H BSL sweep-rejection (veriden, yapısal uyarı).
6. CONFLUENCE: yön_M=yön_Y=YUKARI → YÖN=LONG · uyarı ≥1 (likidite bandı hedef yolunda + 4H sweep-rejection) → GRADE=B.
7. PLAN: MARKET tetik = 15M gövde kapanışı > 64757 · PUSU = 64602.0–64674.4 · STOP = 64602 altı (iptal: 15M gövde < 64602) · T1=64887, T2=65011/65084.6 · R: market ~0.8R(T1)/1.6–2.1R(T2) — pusu ~2.9R(T1)/4.7–5.7R(T2).
8. ÇİZİM: rc_a0_price_only_chart.png (a696e738…) + rc_a0_textbook_smc_chart.png (1ed8b70d…).
9. RAPOR:

RUN: PRAGMATIK / RETROSPECTIVE_NONBLIND / TAMAMLANDI
VERİ: TIER-1 59×15M + 21×4H · TIER-2 6 ekran + 1 video · TIER-3 0 — provenance=USER_SUPPLIED_UNRECEIPTED
YÖN: LONG — CONFLUENCE B (M: UP/B, Y: LONG)
GİRİŞ: MARKET 15M gövde kapanışı > 64757 | PUSU 64602.0–64674.4
STOP: 64602 altı; iptal = 15M gövde kapanışı < 64602
HEDEF: T1 64887, T2 65011–65084.6 — R: market 0.8–2.1R / pusu 2.9–5.7R
BAĞLAM: likidite_bandı=hedef_yolunda · funding=+ · oi=yatay · liq_baskın=long · 4H sweep-rejection uyarısı
UYARI: veri 04:30Z'de bitiyor (bayat olabilir) · provenance makbuzsuz · kural kalibre edilmemiş, olasılık/edge iddiası yok
