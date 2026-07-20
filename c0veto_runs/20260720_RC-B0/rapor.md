# v2.7-PRAGMATİK — RC-B0 Koşusu (C0 = 2026-07-20 10:45–11:00Z)

## Sabah planının KESİN SONUCU (artık veriyle skorlandı; defter kaydı)
- MARKET (tetik: 15M gövde > 64757): HİÇ TETİKLENMEDİ → NO_FILL (teyit kapısı çöküşten korudu)
- PUSU (bölge 64602–64674.4 / ATR bölgesi): 04:30–04:45 barında doldu/tetiklendi → 04:45–05:00 barında STOP (64602) → **STOP_FIRST, ≈ −1R (−72.4/birim)**
- first_leg (ATR ±1.2): D=64445.25'e ilk dokunuş 05:00 barında → **DOWN** (sabahki UP çağrısı YANLIŞ)
- endpoint_16: C16=64210.30, R16=−0.81% → **DOWN** (YANLIŞ)
- Ders: iki bağlam uyarısı (65k bandı + 4H sweep-rejection) haklı çıktı; grade=B'nin anlamı buydu.

## RC-B0 zorunlu rapor
RUN: PRAGMATIK / RETROSPECTIVE_NONBLIND / TAMAMLANDI
VERİ: TIER-1 59×15M (20:15→11:00Z) + 21×4H kapalı bar; 11:00 15M ve 08:00 4H barları AÇIK→dışlandı · TIER-2 6 ekran + 1 video (11:06Z) · TIER-3 0 — provenance=USER_SUPPLIED_UNRECEIPTED
YÖN: LONG — CONFLUENCE C (M: UP/B — gap4h=+0.622%>thr=0.197%, tetik NÖTR; Y: NÖTR — C0'da sweep yok, ama 06:30'dan beri HL-HH toparlanma: 63736→63858→64137)
GİRİŞ: MARKET 15M gövde kapanışı > 64327.3 (C0 high) | PUSU (ATR fallback) 64246–64260
STOP: 64114.7 (ATR fallback; ≈64137 HL'nin altı) — iptal: 15M gövde kapanışı < 64137
HEDEF: T1 64503 (ayı-FVG üstü/kırılım origin), T2 64673 (üst ayı-FVG üstü) — R(giriş 64280.5, stop 64114.7): T1 1.34R, T2 2.37R
BAĞLAM: funding + YÜKSELMİŞ (0.0078%) [uyarı] · liq_baskın=long (gün içi ağır long tasfiyesi) [uyarı] · OI yatay-artan · üstte uzak 65.1–65.2k kalın band · YAKIN ÜST ENGEL (veriden): dolmamış ayı FVG'leri 64393–64503 ve 64536–64673
UYARI: Sinyal ZAYIF (grade C — yapısal motor teyit vermedi); iki dolmamış ayı FVG'si hedef yolunda; provenance makbuzsuz; kalibrasyonsuz, olasılık/edge iddiası yok; 11:00 barının kapanışı görülmedi
ROLLOVER: bir sonraki C0 = 11:15Z kapanışı (taze kapalı bar gelirse yeni koşu)
