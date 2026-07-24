#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KORELASYON MOTORU — iki sembol bağımsız bahis mi, aynı bahsin kopyası mı?

Sorun: ETH'te BTC ile aynı yönde pozisyon açmak "iki işlem" değil, aynı
riskin iki katıdır. Korelasyon ölçülmeden ikisi ayrı fırsat sanılır — bu
gizli bir kaldıraç artışıdır.

Ölçtükleri (hepsi veriden, uydurma yok):
  - Pearson korelasyon (log getiriler, hizalı zaman damgalarında)
  - Beta (ETH getirisinin BTC'ye duyarlılığı; regresyon eğimi)
  - Açıklanan varyans R² (ETH hareketinin ne kadarı BTC ile açıklanıyor)
  - Artık (residual) oynaklık: BTC'den bağımsız kalan kısım
  - Rejim kontrolü: son yarı vs ilk yarı korelasyonu (kararlı mı?)

Hüküm eşikleri (KONVANSİYON — çıktıda raporlanır, gizli sabit yok):
  |ρ| ≥ 0.85 → KOPYA POZİSYON (aynı bahis; toplam risk 2× sayılmalı)
  |ρ| ≥ 0.60 → GÜÇLÜ BAĞLI (kısmi çeşitlendirme; risk ~1.5×)
  |ρ| <  0.60 → BAĞIMSIZ SAYILABİLİR (gerçek çeşitlendirme)

Determinist. Yalnız karar-destek.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

YOK = "VERİ YOK"
KONVANSIYON = {"kopya_esigi": 0.85, "guclu_esigi": 0.60, "min_gozlem": 30}


class KorelasyonError(Exception):
    pass


def _kline_yukle(yol: Path) -> dict:
    """Binance kline dosyasından {zaman: kapanış} sözlüğü."""
    ham = json.loads(yol.read_text(encoding="utf-8"))
    out = {}
    for satir in ham:
        if isinstance(satir, list) and len(satir) >= 5:
            out[int(satir[0])] = float(satir[4])
    return out


def _log_getiri(seri: list) -> list:
    return [math.log(seri[i] / seri[i - 1]) for i in range(1, len(seri))
            if seri[i - 1] > 0 and seri[i] > 0]


def _pearson(x: list, y: list) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        raise KorelasyonError("sıfır varyans — korelasyon tanımsız")
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def olc(yol_a: Path, yol_b: Path, ad_a: str, ad_b: str, p: dict) -> dict:
    A, B = _kline_yukle(yol_a), _kline_yukle(yol_b)
    ortak = sorted(set(A) & set(B))       # SADECE hizalı zaman damgaları
    if len(ortak) < p["min_gozlem"] + 1:
        raise KorelasyonError(f"{YOK} — hizalı bar {len(ortak)} < "
                              f"{p['min_gozlem'] + 1} (korelasyon kurulamaz)")
    ra = _log_getiri([A[t] for t in ortak])
    rb = _log_getiri([B[t] for t in ortak])
    n = min(len(ra), len(rb))
    ra, rb = ra[-n:], rb[-n:]

    rho = _pearson(ra, rb)
    # beta: b = cov(b,a)/var(a)  (a = BTC referans)
    ma, mb = sum(ra) / n, sum(rb) / n
    var_a = sum((x - ma) ** 2 for x in ra) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / n
    beta = cov / var_a if var_a > 0 else None
    r2 = rho ** 2
    # artık oynaklık: BTC ile açıklanamayan kısım
    if beta is not None:
        artik = [y - (mb + beta * (x - ma)) for x, y in zip(ra, rb)]
        artik_std = math.sqrt(sum(z ** 2 for z in artik) / n)
    else:
        artik_std = None
    tam_std = math.sqrt(sum((y - mb) ** 2 for y in rb) / n)

    # kararlılık: iki yarının korelasyonu
    yari = n // 2
    try:
        rho_ilk = _pearson(ra[:yari], rb[:yari])
        rho_son = _pearson(ra[yari:], rb[yari:])
    except KorelasyonError:
        rho_ilk = rho_son = None

    if abs(rho) >= p["kopya_esigi"]:
        hukum, risk_kat = "KOPYA POZİSYON", 2.0
        aciklama = (f"{ad_b}, {ad_a} ile neredeyse aynı hareket ediyor (ρ={rho:.3f}). "
                    "Aynı yönde iki pozisyon = tek bahsin iki katı riski.")
    elif abs(rho) >= p["guclu_esigi"]:
        hukum, risk_kat = "GÜÇLÜ BAĞLI", 1.5
        aciklama = (f"Hareketin %{r2*100:.0f}'i {ad_a} ile açıklanıyor (ρ={rho:.3f}); "
                    "çeşitlendirme kısmi.")
    else:
        hukum, risk_kat = "BAĞIMSIZ SAYILABİLİR", 1.0
        aciklama = (f"ρ={rho:.3f} — {ad_b} hareketinin çoğu {ad_a}'dan bağımsız; "
                    "gerçek çeşitlendirme var.")

    return {
        "cift": f"{ad_a} ↔ {ad_b}", "gozlem": n,
        "korelasyon": round(rho, 4), "beta": (round(beta, 4) if beta is not None else YOK),
        "aciklanan_varyans_r2": round(r2, 4),
        "artik_oynaklik_orani": (round(artik_std / tam_std, 4) if artik_std and tam_std else YOK),
        "kararlilik": {"ilk_yari": (round(rho_ilk, 4) if rho_ilk is not None else YOK),
                       "son_yari": (round(rho_son, 4) if rho_son is not None else YOK),
                       "kayma": (round(abs(rho_son - rho_ilk), 4)
                                 if None not in (rho_ilk, rho_son) else YOK)},
        "HUKUM": hukum, "toplam_risk_carpani": risk_kat, "aciklama": aciklama,
        "varsayimlar": [
            f"eşikler: kopya ≥{p['kopya_esigi']}, güçlü ≥{p['guclu_esigi']} (konvansiyon)",
            "log getiri, YALNIZ hizalı zaman damgaları (eşleşmeyen bar atıldı)",
            f"asgari gözlem {p['min_gozlem']} — altında korelasyon üretilmez (fail-closed)",
        ],
        "not": ("Korelasyon nedensellik değildir ve rejimle değişir; kararlılık "
                "alanı bunun ölçüsüdür. Aynı yönde korele pozisyon gizli kaldıraçtır."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="İki sembol arası korelasyon/beta")
    ap.add_argument("--a", required=True, help="referans sembol kline (ör. BTC m15)")
    ap.add_argument("--b", required=True, help="ikinci sembol kline (ör. ETH m15)")
    ap.add_argument("--ad-a", default="A")
    ap.add_argument("--ad-b", default="B")
    ap.add_argument("--min-gozlem", type=int, default=KONVANSIYON["min_gozlem"])
    a = ap.parse_args(argv)
    p = {**KONVANSIYON, "min_gozlem": a.min_gozlem}
    print(json.dumps(olc(Path(a.a), Path(a.b), a.ad_a, a.ad_b, p),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
