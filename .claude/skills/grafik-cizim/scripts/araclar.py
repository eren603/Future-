#!/usr/bin/env python3
"""Araçlar — TradingView çizim araçlarının SVG karşılıkları.

Her araç iki fonksiyon sunar:
  fiyatlar(t, s) -> list   # ölçeğe rezerve edilecek fiyatlar (grafik dışına taşma yok)
  ciz(t, s)      -> str    # SVG parçası

Nokta gösterimi (her araçta aynı):  {"bar": <int|float>, "fiyat": <float>}
  · bar negatifse SONDAN sayılır (-1 = son mum)
  · bar n'den büyükse GELECEĞE projeksiyon (TradingView sağ boşluğu)
  · {"zaman": <ms>} da kabul edilir (kline zaman damgası)

Kural: bu modül fiyat UYDURMAZ. Verilen sayıları çizer; otomatik seviyeler
otomatik_cizim.py'de ÖLÇÜLEN yapıdan (smc_tespit) türetilir.
"""
from __future__ import annotations

import math

from tuval import bicim_fiyat, ema as _ema_hesap, sma as _sma_hesap

FIB_VARSAYILAN = [0.0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1.0]
FIB_GENISLEME = [0.0, 0.618, 1.0, 1.272, 1.618, 2.0, 2.618]
FIB_DIZI = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
ALTIN_BOLGE = (0.618, 0.786)


# ------------------------------------------------------------------ ortak
def _nokta(t, s, ad, varsayilan_bar=None):
    p = s.get(ad)
    if p is None:
        raise ValueError(f"'{ad}' noktası gerekli (arac={s.get('arac')})")
    if isinstance(p, (list, tuple)) and len(p) == 2:
        p = {"bar": p[0], "fiyat": p[1]}
    bar = p.get("bar", p.get("zaman", varsayilan_bar))
    ref = {"zaman": p["zaman"]} if "zaman" in p else bar
    return t.x(ref), t.y(float(p["fiyat"])), t.bar_indeks(ref), float(p["fiyat"])


def _nokta_fiyat(s, ad):
    p = s.get(ad)
    if p is None:
        return []
    if isinstance(p, (list, tuple)) and len(p) == 2:
        return [float(p[1])]
    return [float(p["fiyat"])] if "fiyat" in p else []


def _renk(t, s, varsayilan_anahtar="vurgu", anahtar="renk"):
    r = s.get(anahtar)
    if not r:
        return t.t.get(varsayilan_anahtar, varsayilan_anahtar)
    return t.t.get(r, r)


def _sag_kenar(t, s):
    """Çizimin biteceği x — 'bar_bitis' verilmemişse sağ kenar."""
    if s.get("bar_bitis") is not None:
        return t.x(s["bar_bitis"])
    return t.sag


def _etiket(t, s, x, y, metin, renk, hiza="start"):
    if not metin:
        return ""
    return t.etiket_kutu(x, y, metin, renk, boyut=int(s.get("etiket_boyut", 11)),
                         hiza=hiza)


# ------------------------------------------------------- 1) trend çizgisi
def trend_cizgisi_fiyat(t, s):
    return _nokta_fiyat(s, "p1") + _nokta_fiyat(s, "p2")


def trend_cizgisi_ciz(t, s):
    x1, y1, b1, f1 = _nokta(t, s, "p1")
    x2, y2, b2, f2 = _nokta(t, s, "p2")
    renk = _renk(t, s)
    kal = float(s.get("kalinlik", 1.8))
    kesik = s.get("kesik")
    uzat = str(s.get("uzat", "yok"))
    if x2 != x1:
        egim = (y2 - y1) / (x2 - x1)
        if uzat in ("sag", "iki"):
            x2b = _sag_kenar(t, s)
            y2, x2 = y1 + egim * (x2b - x1), x2b
        if uzat in ("sol", "iki"):
            x1b = t.sol
            y1, x1 = y1 + egim * (x1b - x1), x1b
    p = [t.cizgi(x1, y1, x2, y2, renk, kal, kesik=kesik, ok=bool(s.get("ok")))]
    if s.get("etiket"):
        p.append(_etiket(t, s, x2 + 6, y2, s["etiket"], renk))
    return "".join(p)


# ---------------------------------------------------- 2) yatay çizgi / ray
def yatay_cizgi_fiyat(t, s):
    return [float(s["fiyat"])]


def yatay_cizgi_ciz(t, s):
    f = float(s["fiyat"])
    y = t.y(f)
    renk = _renk(t, s)
    x1 = t.x(s["bar_baslangic"]) if s.get("bar_baslangic") is not None else t.sol
    x2 = _sag_kenar(t, s)
    p = [t.cizgi(x1, y, x2, y, renk, float(s.get("kalinlik", 1.4)),
                 kesik=s.get("kesik"))]
    if s.get("etiket"):
        if str(s.get("etiket_hiza", "sol")) == "sag":
            p.append(t.yazi(x2 - 6, y - 6, s["etiket"], renk=renk, boyut=11,
                            hiza="end", kalin=True))
        else:
            p.append(t.yazi(x1 + 6, y - 6, s["etiket"], renk=renk, boyut=11, kalin=True))
    if s.get("fiyat_etiketi", True):
        p.append(t.fiyat_ekseni_etiketi(f, renk))
    return "".join(p)


def yatay_ray_ciz(t, s):
    s = dict(s)
    s.setdefault("bar_baslangic", s.get("bar", 0))
    return yatay_cizgi_ciz(t, s)


# --------------------------------------------------------- 3) dikey çizgi
def dikey_cizgi_fiyat(t, s):
    return []


def dikey_cizgi_ciz(t, s):
    x = t.x(s.get("bar", -1))
    renk = _renk(t, s, "metin_soluk")
    p = [t.cizgi(x, t.ana_ust, x, t.ana_alt, renk, float(s.get("kalinlik", 1.2)),
                 kesik=s.get("kesik", "5 4"))]
    if s.get("etiket"):
        p.append(t.yazi(x + 5, t.ana_ust + 14, s["etiket"], renk=renk, boyut=11))
    return "".join(p)


# ------------------------------------------- 4) dikdörtgen / arz-talep bölgesi
def dikdortgen_fiyat(t, s):
    return [float(s["fiyat1"]), float(s["fiyat2"])]


def dikdortgen_ciz(t, s):
    f1, f2 = float(s["fiyat1"]), float(s["fiyat2"])
    x1 = t.x(s.get("bar_baslangic", 0))
    x2 = _sag_kenar(t, s)
    renk = _renk(t, s)
    p = [t.kutu(x1, t.y(f1), x2, t.y(f2), dolgu=renk, kenar=s.get("kenar_ac", True) and renk,
                dolgu_saydam=float(s.get("dolgu_saydam", 0.16)),
                kalinlik=float(s.get("kalinlik", 1.0)), kesik=s.get("kesik"))]
    if s.get("etiket"):
        yorta = (t.y(f1) + t.y(f2)) / 2
        hiza = str(s.get("etiket_hiza", "sag"))
        if hiza == "sag":
            p.append(_etiket(t, s, x2 - 4, yorta, s["etiket"], renk, hiza="end"))
        else:
            p.append(_etiket(t, s, x1 + 4, yorta, s["etiket"], renk))
    return "".join(p)


# ----------------------------------------------------- 5) paralel kanal
def paralel_kanal_fiyat(t, s):
    f = _nokta_fiyat(s, "p1") + _nokta_fiyat(s, "p2") + _nokta_fiyat(s, "p3")
    if len(f) >= 3:
        d = f[2] - f[0]
        f += [f[0] + d, f[1] + d]
    return f


def paralel_kanal_ciz(t, s):
    x1, y1, b1, f1 = _nokta(t, s, "p1")
    x2, y2, b2, f2 = _nokta(t, s, "p2")
    x3, y3, b3, f3 = _nokta(t, s, "p3")
    renk = _renk(t, s)
    dy = y3 - (y1 + (y2 - y1) * ((x3 - x1) / (x2 - x1) if x2 != x1 else 0))
    xs, xe = (t.sol, _sag_kenar(t, s)) if s.get("uzat", True) else (x1, x2)
    egim = (y2 - y1) / (x2 - x1) if x2 != x1 else 0.0
    ys, ye = y1 + egim * (xs - x1), y1 + egim * (xe - x1)
    p = [f'<polygon points="{xs:.1f},{ys:.1f} {xe:.1f},{ye:.1f} '
         f'{xe:.1f},{ye + dy:.1f} {xs:.1f},{ys + dy:.1f}" fill="{renk}" '
         f'fill-opacity="{float(s.get("dolgu_saydam", 0.10))}"/>',
         t.cizgi(xs, ys, xe, ye, renk, float(s.get("kalinlik", 1.6))),
         t.cizgi(xs, ys + dy, xe, ye + dy, renk, float(s.get("kalinlik", 1.6)))]
    if s.get("orta_cizgi", True):
        p.append(t.cizgi(xs, ys + dy / 2, xe, ye + dy / 2, renk, 1.0, kesik="4 4",
                         saydam=0.8))
    if s.get("etiket"):
        p.append(_etiket(t, s, xe - 4, ye, s["etiket"], renk, hiza="end"))
    return "".join(p)


# ------------------------------------------------ 6) regresyon kanalı
def _regresyon(t, s):
    b1 = int(t.bar_indeks(s.get("bar_baslangic", 0)))
    b2 = int(t.bar_indeks(s.get("bar_bitis", t.n - 1)))
    b1, b2 = max(0, min(b1, b2)), min(t.n - 1, max(b1, b2))
    if b2 - b1 < 3:
        raise ValueError("regresyon_kanali için en az 4 bar gerekli")
    kaynak = str(s.get("kaynak", "close"))
    y = [t.m[i][kaynak] for i in range(b1, b2 + 1)]
    x = list(range(len(y)))
    nx = len(x)
    ox, oy = sum(x) / nx, sum(y) / nx
    pay = sum((x[i] - ox) * (y[i] - oy) for i in range(nx))
    payda = sum((x[i] - ox) ** 2 for i in range(nx)) or 1e-9
    egim = pay / payda
    kesme = oy - egim * ox
    art = [y[i] - (kesme + egim * x[i]) for i in range(nx)]
    sigma = math.sqrt(sum(a * a for a in art) / max(1, nx - 2))
    return b1, b2, kesme, egim, sigma, nx


def regresyon_kanali_fiyat(t, s):
    b1, b2, kesme, egim, sigma, nx = _regresyon(t, s)
    k = float(s.get("sapma", 2.0))
    uc = [kesme, kesme + egim * (nx - 1)]
    return [v + d for v in uc for d in (-k * sigma, 0, k * sigma)]


def regresyon_kanali_ciz(t, s):
    b1, b2, kesme, egim, sigma, nx = _regresyon(t, s)
    k = float(s.get("sapma", 2.0))
    ileri = int(s.get("ileri_bar", 0))
    xa, xb = t.x(b1), t.x(b2 + ileri)
    fa, fb = kesme, kesme + egim * (nx - 1 + ileri)
    renk = _renk(t, s)
    ya, yb = t.y(fa), t.y(fb)
    yau, ybu = t.y(fa + k * sigma), t.y(fb + k * sigma)
    yad, ybd = t.y(fa - k * sigma), t.y(fb - k * sigma)
    p = [f'<polygon points="{xa:.1f},{yau:.1f} {xb:.1f},{ybu:.1f} {xb:.1f},{ybd:.1f} '
         f'{xa:.1f},{yad:.1f}" fill="{renk}" fill-opacity="'
         f'{float(s.get("dolgu_saydam", 0.10))}"/>',
         t.cizgi(xa, ya, xb, yb, renk, 1.4, kesik="5 4"),
         t.cizgi(xa, yau, xb, ybu, renk, 1.6),
         t.cizgi(xa, yad, xb, ybd, renk, 1.6)]
    if s.get("etiket", True):
        yon = "yükselen" if egim > 0 else "düşen"
        p.append(_etiket(t, s, xa + 4, yau - 12,
                         s.get("etiket") or f"regresyon {yon} ±{k:g}σ", renk))
    return "".join(p)


# ------------------------------------------------- 7) Fibonacci düzeltme
def _fib_seviyeler(s, anahtar="seviyeler", varsayilan=None):
    lv = s.get(anahtar) or (varsayilan if varsayilan is not None else FIB_VARSAYILAN)
    return [float(v) for v in lv]


def fib_retracement_fiyat(t, s):
    f1 = _nokta_fiyat(s, "p1")[0]
    f2 = _nokta_fiyat(s, "p2")[0]
    return [f2 - (f2 - f1) * lv for lv in _fib_seviyeler(s)] + [f1, f2]


def fib_retracement_ciz(t, s):
    x1, y1, b1, f1 = _nokta(t, s, "p1")
    x2, y2, b2, f2 = _nokta(t, s, "p2")
    renk = _renk(t, s, "metin_soluk")
    # tam_genislik: impuls bacağı grafiğin sağında kaldığında etiketler
    # sıkışmasın diye seviyeler tuvalin soluna kadar uzatılır (TradingView'da
    # kullanıcının elle yaptığı şey).
    xs = t.sol if s.get("tam_genislik") else min(x1, x2)
    xe = _sag_kenar(t, s)
    sev = _fib_seviyeler(s)
    p = [t.cizgi(x1, y1, x2, y2, renk, 1.2, kesik="4 4", saydam=0.7)]
    if s.get("altin_bolge", True):
        ga = f2 - (f2 - f1) * ALTIN_BOLGE[0]
        gb = f2 - (f2 - f1) * ALTIN_BOLGE[1]
        p.append(t.kutu(xs, t.y(ga), xe, t.y(gb), dolgu=t.t["olumlu"], kenar=None,
                        dolgu_saydam=0.14))
        p.append(t.yazi(xs + 6, (t.y(ga) + t.y(gb)) / 2 + 4, "altın bölge 0.618–0.786",
                        renk=t.t["olumlu"], boyut=10, kalin=True))
    kullanilan: list[float] = []
    for lv in sorted(sev, key=lambda v: t.y(f2 - (f2 - f1) * v)):
        f = f2 - (f2 - f1) * lv
        y = t.y(f)
        vurgu = abs(lv - 0.618) < 1e-9 or abs(lv - 0.5) < 1e-9
        p.append(t.cizgi(xs, y, xe, y, renk, 1.6 if vurgu else 1.0,
                         saydam=0.95 if vurgu else 0.65))
        ye = y - 4  # etiket çakışma önleyici (seviyeler sıkışınca aşağı kaydır)
        while any(abs(ye - k) < 12 for k in kullanilan):
            ye += 12
        kullanilan.append(ye)
        p.append(t.yazi(xs + 6, ye, f"{lv:g} ({bicim_fiyat(f)})",
                        renk=t.t["metin"] if vurgu else t.t["metin_soluk"],
                        boyut=11, kalin=vurgu))
    if s.get("fiyat_etiketi"):
        for lv in (0.618, 0.786):
            if lv in sev:
                p.append(t.fiyat_ekseni_etiketi(f2 - (f2 - f1) * lv, t.t["olumlu"]))
    return "".join(p)


# ---------------------------------- 8) Fibonacci genişleme (trend bazlı)
def fib_genisleme_fiyat(t, s):
    f1 = _nokta_fiyat(s, "p1")[0]
    f2 = _nokta_fiyat(s, "p2")[0]
    f3 = _nokta_fiyat(s, "p3")[0]
    return [f3 + (f2 - f1) * lv for lv in _fib_seviyeler(s, varsayilan=FIB_GENISLEME)]


def fib_genisleme_ciz(t, s):
    x1, y1, b1, f1 = _nokta(t, s, "p1")
    x2, y2, b2, f2 = _nokta(t, s, "p2")
    x3, y3, b3, f3 = _nokta(t, s, "p3")
    renk = _renk(t, s, "notr")
    xs, xe = min(x1, x3), _sag_kenar(t, s)
    p = [t.cizgi(x1, y1, x2, y2, renk, 1.1, kesik="4 4", saydam=0.6),
         t.cizgi(x2, y2, x3, y3, renk, 1.1, kesik="4 4", saydam=0.6)]
    for lv in _fib_seviyeler(s, varsayilan=FIB_GENISLEME):
        f = f3 + (f2 - f1) * lv
        y = t.y(f)
        vurgu = abs(lv - 1.618) < 1e-9
        p.append(t.cizgi(xs, y, xe, y, renk, 1.5 if vurgu else 1.0,
                         saydam=0.9 if vurgu else 0.6))
        p.append(t.yazi(xe - 6, y - 4, f"ext {lv:g} ({bicim_fiyat(f)})", renk=renk,
                        boyut=11, hiza="end", kalin=vurgu))
    return "".join(p)


# ------------------------------------------------- 9) Fibonacci kanalı
def fib_kanal_fiyat(t, s):
    f = [_nokta_fiyat(s, k)[0] for k in ("p1", "p2", "p3")]
    gen = f[2] - f[0]
    return [f[0] + gen * lv for lv in _fib_seviyeler(s)] + \
           [f[1] + gen * lv for lv in _fib_seviyeler(s)]


def fib_kanal_ciz(t, s):
    x1, y1, b1, f1 = _nokta(t, s, "p1")
    x2, y2, b2, f2 = _nokta(t, s, "p2")
    x3, y3, b3, f3 = _nokta(t, s, "p3")
    renk = _renk(t, s, "vurgu")
    dy = y3 - y1
    egim = (y2 - y1) / (x2 - x1) if x2 != x1 else 0.0
    xs, xe = t.sol, _sag_kenar(t, s)
    p = []
    for lv in _fib_seviyeler(s):
        ya = y1 + egim * (xs - x1) + dy * lv
        yb = y1 + egim * (xe - x1) + dy * lv
        p.append(t.cizgi(xs, ya, xe, yb, renk, 1.3 if lv in (0.0, 1.0) else 1.0,
                         saydam=0.85 if lv in (0.0, 1.0) else 0.55))
        p.append(t.yazi(xe - 6, yb - 4, f"{lv:g}", renk=renk, boyut=10, hiza="end"))
    return "".join(p)


# ------------------------------------------------- 10) Fibonacci yelpaze
def fib_yelpaze_fiyat(t, s):
    return _nokta_fiyat(s, "p1") + _nokta_fiyat(s, "p2")


def fib_yelpaze_ciz(t, s):
    x1, y1, b1, f1 = _nokta(t, s, "p1")
    x2, y2, b2, f2 = _nokta(t, s, "p2")
    renk = _renk(t, s, "vurgu")
    xe = _sag_kenar(t, s)
    p = [t.cizgi(x1, y1, x2, y2, renk, 1.4)]
    for lv in (0.236, 0.382, 0.5, 0.618, 0.786):
        yh = y1 + (y2 - y1) * (1 - lv)
        if x2 == x1:
            continue
        egim = (yh - y1) / (x2 - x1)
        p.append(t.cizgi(x1, y1, xe, y1 + egim * (xe - x1), renk, 1.0, saydam=0.6))
        p.append(t.yazi(xe - 6, y1 + egim * (xe - x1) - 4, f"{lv:g}", renk=renk,
                        boyut=10, hiza="end"))
    return "".join(p)


# ---------------------------------------------- 11) Fibonacci zaman bölgeleri
def fib_zaman_fiyat(t, s):
    return []


def fib_zaman_ciz(t, s):
    b1 = t.bar_indeks(s.get("bar_baslangic", 0))
    b2 = t.bar_indeks(s.get("bar_bitis", b1 + 10))
    birim = b2 - b1
    renk = _renk(t, s, "metin_soluk")
    p = []
    for k in FIB_DIZI:
        b = b1 + birim * k
        if b > t.n + t.sag_bosluk:
            break
        x = t.x(b)
        p.append(t.cizgi(x, t.ana_ust, x, t.ana_alt, renk, 1.0, kesik="3 5", saydam=0.7))
        p.append(t.yazi(x + 3, t.ana_ust + 12, str(k), renk=renk, boyut=10))
    return "".join(p)


# -------------------------------------------- 12) Andrews çatalı (pitchfork)
def andrews_catali_fiyat(t, s):
    return [f for k in ("p1", "p2", "p3") for f in _nokta_fiyat(s, k)]


def andrews_catali_ciz(t, s):
    x1, y1, _, _ = _nokta(t, s, "p1")
    x2, y2, _, _ = _nokta(t, s, "p2")
    x3, y3, _, _ = _nokta(t, s, "p3")
    renk = _renk(t, s, "vurgu")
    xo, yo = (x2 + x3) / 2, (y2 + y3) / 2
    xe = _sag_kenar(t, s)
    if xo == x1:
        return ""
    egim = (yo - y1) / (xo - x1)
    p = [t.cizgi(x2, y2, x3, y3, renk, 1.2, saydam=0.7),
         t.cizgi(x1, y1, xe, y1 + egim * (xe - x1), renk, 1.6)]
    for dx, dy in ((x2 - xo, y2 - yo), (x3 - xo, y3 - yo)):
        p.append(t.cizgi(x1 + dx, y1 + dy, xe, y1 + dy + egim * (xe - x1 - dx),
                         renk, 1.3, saydam=0.85))
    return "".join(p)


# ------------------------------------------------------------- 13) ok
def ok_fiyat(t, s):
    return _nokta_fiyat(s, "p1") + _nokta_fiyat(s, "p2")


def ok_ciz(t, s):
    x1, y1, _, _ = _nokta(t, s, "p1")
    x2, y2, _, _ = _nokta(t, s, "p2")
    renk = _renk(t, s)
    p = [t.cizgi(x1, y1, x2, y2, renk, float(s.get("kalinlik", 2.4)), ok=True)]
    if s.get("etiket"):
        p.append(_etiket(t, s, x1 + 6, y1, s["etiket"], renk))
    return "".join(p)


# ------------------------------------------------------------- 14) yol
def yol_fiyat(t, s):
    return [float(p["fiyat"]) for p in s.get("noktalar", [])]


def yol_ciz(t, s):
    nk = s.get("noktalar", [])
    if len(nk) < 2:
        return ""
    renk = _renk(t, s)
    pts = " ".join(f"{t.x(p.get('bar')):.1f},{t.y(float(p['fiyat'])):.1f}" for p in nk)
    return (f'<polyline points="{pts}" fill="none" stroke="{renk}" '
            f'stroke-width="{float(s.get("kalinlik", 1.8))}" '
            f'stroke-linejoin="round"/>')


# ------------------------------- 15/16) uzun / kısa pozisyon aracı (R:R kutusu)
def _pozisyon_fiyat(t, s):
    return [float(s["giris"]), float(s["stop"]), float(s["hedef"])]


def _pozisyon_ciz(t, s, yon):
    giris, stop, hedef = float(s["giris"]), float(s["stop"]), float(s["hedef"])
    x1 = t.x(s.get("bar_baslangic", -1))
    x2 = _sag_kenar(t, s) if s.get("bar_bitis") is not None else min(
        t.sag, t.x(t.bar_indeks(s.get("bar_baslangic", -1)) + int(s.get("uzunluk_bar", 20))))
    yg, ys, yh = t.y(giris), t.y(stop), t.y(hedef)
    kar_renk, zarar_renk = t.t["olumlu"], t.t["olumsuz"]
    risk = abs(giris - stop)
    odul = abs(hedef - giris)
    rr = (odul / risk) if risk > 0 else None
    p = [t.kutu(x1, yg, x2, yh, dolgu=kar_renk, kenar=kar_renk, dolgu_saydam=0.18),
         t.kutu(x1, yg, x2, ys, dolgu=zarar_renk, kenar=zarar_renk, dolgu_saydam=0.18),
         t.cizgi(x1, yg, x2, yg, t.t["metin"], 1.4, kesik="4 3")]
    ok_x = (x1 + x2) / 2
    p.append(t.cizgi(ok_x, yg, ok_x, yh, kar_renk, 1.8, ok=True))
    yuzde_h = (hedef - giris) / giris * 100.0
    yuzde_s = (stop - giris) / giris * 100.0
    p += [
        t.etiket_kutu(x2 - 4, yh + 4, f"Hedef {bicim_fiyat(hedef)} ({yuzde_h:+.2f}%)",
                      kar_renk, hiza="end"),
        t.etiket_kutu(x2 - 4, ys + 4, f"Stop {bicim_fiyat(stop)} ({yuzde_s:+.2f}%)",
                      zarar_renk, hiza="end"),
        t.etiket_kutu(x1 + 4, yg + 4,
                      f"{'LONG' if yon == 'long' else 'SHORT'} giriş {bicim_fiyat(giris)}",
                      t.t["vurgu"]),
    ]
    if rr is not None:
        etk = s.get("r_etiketi") or f"R:R {rr:.2f}"
        p.append(t.etiket_kutu(ok_x, (yg + yh) / 2, etk, t.t["vurgu"], hiza="middle"))
    for f, r in ((giris, t.t["vurgu"]), (stop, zarar_renk), (hedef, kar_renk)):
        if s.get("fiyat_etiketi", True):
            p.append(t.fiyat_ekseni_etiketi(f, r))
    return "".join(p)


def long_pozisyon_ciz(t, s):
    return _pozisyon_ciz(t, s, "long")


def short_pozisyon_ciz(t, s):
    return _pozisyon_ciz(t, s, "short")


# ------------------------------------------------------------ 17) ölçüm
def olcum_fiyat(t, s):
    return _nokta_fiyat(s, "p1") + _nokta_fiyat(s, "p2")


def olcum_ciz(t, s):
    x1, y1, b1, f1 = _nokta(t, s, "p1")
    x2, y2, b2, f2 = _nokta(t, s, "p2")
    artis = f2 >= f1
    renk = t.t["olumlu"] if artis else t.t["olumsuz"]
    d = f2 - f1
    yuzde = (d / f1 * 100.0) if f1 else float("nan")
    bar = abs(int(b2 - b1))
    p = [t.kutu(x1, y1, x2, y2, dolgu=renk, kenar=renk, dolgu_saydam=0.14),
         t.cizgi((x1 + x2) / 2, y1, (x1 + x2) / 2, y2, renk, 1.6, ok=True),
         t.etiket_kutu((x1 + x2) / 2, (y1 + y2) / 2,
                       f"{bicim_fiyat(d)} ({yuzde:+.2f}%) · {bar} bar", renk,
                       hiza="middle")]
    return "".join(p)


# ------------------------------------------------ 18) metin / balon / işaret
def metin_fiyat(t, s):
    return _nokta_fiyat(s, "p1")


def metin_ciz(t, s):
    x, y, _, _ = _nokta(t, s, "p1")
    renk = _renk(t, s, "metin")
    if s.get("kutu", False):
        return t.etiket_kutu(x, y, s.get("metin", ""), renk,
                             hiza=s.get("hiza", "start"))
    return t.yazi(x, y, s.get("metin", ""), renk=renk,
                  boyut=int(s.get("boyut", 12)), hiza=s.get("hiza", "start"),
                  kalin=bool(s.get("kalin", True)))


def isaret_fiyat(t, s):
    return _nokta_fiyat(s, "p1")


def isaret_ciz(t, s):
    x, y, _, f = _nokta(t, s, "p1")
    yon = str(s.get("yon", "yukari"))
    renk = _renk(t, s, "olumlu" if yon == "yukari" else "olumsuz")
    b = float(s.get("boyut", 9))
    if yon == "yukari":
        pts = f"{x:.1f},{y - b:.1f} {x - b:.1f},{y + b:.1f} {x + b:.1f},{y + b:.1f}"
        ty = y + b + 13
    else:
        pts = f"{x:.1f},{y + b:.1f} {x - b:.1f},{y - b:.1f} {x + b:.1f},{y - b:.1f}"
        ty = y - b - 6
    p = [f'<polygon points="{pts}" fill="{renk}"/>']
    if s.get("etiket"):
        p.append(t.yazi(x, ty, s["etiket"], renk=renk, boyut=11, hiza="middle",
                        kalin=True))
    return "".join(p)


def fiyat_etiketi_fiyat(t, s):
    return [float(s["fiyat"])]


def fiyat_etiketi_ciz(t, s):
    return t.fiyat_ekseni_etiketi(float(s["fiyat"]), _renk(t, s),
                                  metin=s.get("metin"))


# ------------------------------------------------------- 19) bilgi paneli
def bilgi_paneli_fiyat(t, s):
    return []


def _bos_kose(t, gen: float, yuk: float) -> str:
    """Paneli mumların EN AZ olduğu köşeye koyar (ölçülür, tahmin edilmez)."""
    en_iyi, en_az = "sag_ust", None
    for kose in ("sag_ust", "sol_ust", "sag_alt", "sol_alt"):
        x1 = (t.sag - gen - 12) if kose.startswith("sag") else (t.sol + 12)
        y1 = (t.ana_ust + 10) if kose.endswith("ust") else (t.ana_alt - yuk - 10)
        x2, y2 = x1 + gen, y1 + yuk
        cakisma = 0
        for i, c in enumerate(t.m):
            x = t.x(i)
            if not (x1 - 6 <= x <= x2 + 6):
                continue
            if max(t.y(c["high"]), y1) <= min(t.y(c["low"]), y2):  # kesişim
                cakisma += 1
        if en_az is None or cakisma < en_az:
            en_iyi, en_az = kose, cakisma
    return en_iyi


def bilgi_paneli_ciz(t, s):
    satir = s.get("satirlar", [])
    if not satir:
        return ""
    gen = int(s.get("genislik", 250))
    sh = 19
    yuk = sh * (len(satir) + 1) + 10
    konum = str(s.get("konum", "oto"))
    if konum == "oto":
        konum = _bos_kose(t, gen, yuk)
    x = t.sag - gen - 12 if konum.startswith("sag") else t.sol + 12
    y = t.ana_ust + 10 if konum.endswith("ust") else t.ana_alt - yuk - 10
    p = [t.kutu(x, y, x + gen, y + yuk, dolgu=t.t["panel"], kenar=t.t["eksen"],
                dolgu_saydam=0.94, kose=4),
         t.yazi(x + 10, y + 16, s.get("baslik", "PANEL"), boyut=12, kalin=True),
         t.cizgi(x, y + sh + 4, x + gen, y + sh + 4, t.t["eksen"], 1)]
    for i, r in enumerate(satir):
        yy = y + sh * (i + 2) + 2
        ad = r.get("ad", "")
        deger = r.get("deger", "VERİ YOK")
        renk = t.t.get(r.get("renk", "metin"), r.get("renk", t.t["metin"]))
        p.append(t.yazi(x + 10, yy, ad, renk=t.t["metin_soluk"], boyut=11))
        p.append(t.yazi(x + gen - 10, yy, str(deger), renk=renk, boyut=11,
                        hiza="end", kalin=True))
    return "".join(p)


# ------------------------------------------------ 20) hareketli ortalama
def ma_fiyat(t, s):
    seri = _ma_seri(t, s)
    gecerli = [v for v in seri if v is not None]
    return [min(gecerli), max(gecerli)] if gecerli else []


def _ma_seri(t, s):
    per = int(s.get("period", 50))
    kaynak = str(s.get("kaynak", "close"))
    dizi = [c[kaynak] for c in t.m]
    tip = str(s.get("tip", "ema")).lower()
    return _ema_hesap(dizi, per) if tip == "ema" else _sma_hesap(dizi, per)


def ma_ciz(t, s):
    seri = _ma_seri(t, s)
    renk = _renk(t, s, "notr")
    pts = [f"{t.x(i):.1f},{t.y(v):.1f}" for i, v in enumerate(seri) if v is not None]
    if not pts:
        t.uyarilar.append(
            f"ma({s.get('tip', 'ema')}{s.get('period', 50)}): bar sayısı yetersiz "
            f"({t.n} bar) — çizilmedi")
        return ""
    p = [f'<polyline points="{" ".join(pts)}" fill="none" stroke="{renk}" '
         f'stroke-width="{float(s.get("kalinlik", 1.6))}" stroke-linejoin="round"/>']
    if s.get("etiket", True):
        son = [v for v in seri if v is not None][-1]
        p.append(t.yazi(t.x(len(seri) - 1) + 6, t.y(son) + 4,
                        f"{str(s.get('tip', 'ema')).upper()}{int(s.get('period', 50))}",
                        renk=renk, boyut=10, kalin=True))
    return "".join(p)


# ------------------------------------------- 21) bulut / şerit (iki çizgi arası)
def _bulut_seri(t, s, anahtar):
    cfg = dict(s.get(anahtar) or {})
    if cfg.get("deger") is not None:
        d = [None if v is None else float(v) for v in cfg["deger"]]
        return (d + [None] * t.n)[:t.n]
    if cfg.get("fiyat") is not None:
        return [float(cfg["fiyat"])] * t.n
    return _ma_seri(t, cfg)


def bulut_fiyat(t, s):
    d = [v for k in ("a", "b") for v in _bulut_seri(t, s, k) if v is not None]
    return [min(d), max(d)] if d else []


def bulut_ciz(t, s):
    a, b = _bulut_seri(t, s, "a"), _bulut_seri(t, s, "b")
    ust_renk = t.t.get(s.get("renk_yukari", "olumlu"), s.get("renk_yukari", "#26a69a"))
    alt_renk = t.t.get(s.get("renk_asagi", "olumsuz"), s.get("renk_asagi", "#ef5350"))
    saydam = float(s.get("dolgu_saydam", 0.18))
    p, blok, isaret = [], [], None
    for i in range(t.n):
        va, vb = a[i], b[i]
        gecerli = va is not None and vb is not None
        yeni = (va >= vb) if gecerli else None
        if not gecerli or (isaret is not None and yeni != isaret):
            if len(blok) > 1:
                p.append(_bulut_poligon(t, blok, ust_renk if isaret else alt_renk, saydam))
            blok = [] if not gecerli else [(i, va, vb)]
            isaret = yeni
            continue
        isaret = yeni if isaret is None else isaret
        blok.append((i, va, vb))
    if len(blok) > 1:
        p.append(_bulut_poligon(t, blok, ust_renk if isaret else alt_renk, saydam))
    if s.get("kenar", True):
        for seri, renk in ((a, ust_renk), (b, alt_renk)):
            pts = [f"{t.x(i):.1f},{t.y(v):.1f}" for i, v in enumerate(seri) if v is not None]
            if pts:
                p.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{renk}" '
                         f'stroke-width="1.2" stroke-opacity="0.9"/>')
    if not p:
        t.uyarilar.append("bulut: iki seri de hesaplanamadı — çizilmedi (VERİ YOK)")
    return "".join(p)


def _bulut_poligon(t, blok, renk, saydam):
    ust = " ".join(f"{t.x(i):.1f},{t.y(va):.1f}" for i, va, _ in blok)
    alt = " ".join(f"{t.x(i):.1f},{t.y(vb):.1f}" for i, _, vb in reversed(blok))
    return (f'<polygon points="{ust} {alt}" fill="{renk}" '
            f'fill-opacity="{saydam}"/>')


# ------------------------------------------------------------- kayıt defteri
ARACLAR = {
    "trend_cizgisi": (trend_cizgisi_fiyat, trend_cizgisi_ciz),
    "yatay_cizgi": (yatay_cizgi_fiyat, yatay_cizgi_ciz),
    "yatay_ray": (yatay_cizgi_fiyat, yatay_ray_ciz),
    "dikey_cizgi": (dikey_cizgi_fiyat, dikey_cizgi_ciz),
    "dikdortgen": (dikdortgen_fiyat, dikdortgen_ciz),
    "paralel_kanal": (paralel_kanal_fiyat, paralel_kanal_ciz),
    "regresyon_kanali": (regresyon_kanali_fiyat, regresyon_kanali_ciz),
    "fib_retracement": (fib_retracement_fiyat, fib_retracement_ciz),
    "fib_genisleme": (fib_genisleme_fiyat, fib_genisleme_ciz),
    "fib_kanal": (fib_kanal_fiyat, fib_kanal_ciz),
    "fib_yelpaze": (fib_yelpaze_fiyat, fib_yelpaze_ciz),
    "fib_zaman": (fib_zaman_fiyat, fib_zaman_ciz),
    "andrews_catali": (andrews_catali_fiyat, andrews_catali_ciz),
    "ok": (ok_fiyat, ok_ciz),
    "yol": (yol_fiyat, yol_ciz),
    "long_pozisyon": (_pozisyon_fiyat, long_pozisyon_ciz),
    "short_pozisyon": (_pozisyon_fiyat, short_pozisyon_ciz),
    "olcum": (olcum_fiyat, olcum_ciz),
    "metin": (metin_fiyat, metin_ciz),
    "isaret": (isaret_fiyat, isaret_ciz),
    "fiyat_etiketi": (fiyat_etiketi_fiyat, fiyat_etiketi_ciz),
    "bilgi_paneli": (bilgi_paneli_fiyat, bilgi_paneli_ciz),
    "ma": (ma_fiyat, ma_ciz),
    "bulut": (bulut_fiyat, bulut_ciz),
}

# İngilizce/TradingView adları da kabul edilir (kullanıcı hangi dilde yazarsa)
TAKMA_AD = {
    "trendline": "trend_cizgisi", "trend_line": "trend_cizgisi",
    "horizontal_line": "yatay_cizgi", "hline": "yatay_cizgi",
    "ray": "yatay_ray", "horizontal_ray": "yatay_ray",
    "vertical_line": "dikey_cizgi", "vline": "dikey_cizgi",
    "rectangle": "dikdortgen", "zone": "dikdortgen", "bolge": "dikdortgen",
    "parallel_channel": "paralel_kanal", "channel": "paralel_kanal",
    "regression_channel": "regresyon_kanali", "regresyon": "regresyon_kanali",
    "fib": "fib_retracement", "fibonacci": "fib_retracement",
    "fib_retracement_tool": "fib_retracement", "fibonacci_retracement": "fib_retracement",
    "fib_extension": "fib_genisleme", "trend_based_fib_extension": "fib_genisleme",
    "fib_channel": "fib_kanal", "fib_fan": "fib_yelpaze",
    "fib_time_zones": "fib_zaman", "pitchfork": "andrews_catali",
    "arrow": "ok", "path": "yol", "polyline": "yol",
    "long_position": "long_pozisyon", "short_position": "short_pozisyon",
    "measure": "olcum", "text": "metin", "label": "metin",
    "marker": "isaret", "price_label": "fiyat_etiketi", "price_tag": "fiyat_etiketi",
    "info_panel": "bilgi_paneli", "table": "bilgi_paneli",
    "moving_average": "ma", "ema": "ma", "sma": "ma",
    "cloud": "bulut", "kumo": "bulut", "band": "bulut", "serit": "bulut",
    "ma_cloud": "bulut", "fill": "bulut",
}


# Katman (z) düzeni — TradingView'daki gibi: bölgeler/kanallar mumların ARKASINDA,
# çizgiler ve etiketler önünde. 0'ın altı arka plana çizilir.
KATMAN = {
    "dikdortgen": -2, "paralel_kanal": -2, "regresyon_kanali": -2,
    "fib_kanal": -1, "fib_zaman": -1, "andrews_catali": -1,
    "fib_retracement": -1, "fib_genisleme": -1, "fib_yelpaze": -1,
    "yatay_cizgi": 1, "yatay_ray": 1, "dikey_cizgi": 1, "trend_cizgisi": 1,
    "bulut": -2,
    "yol": 1, "ma": 2, "ok": 3, "olcum": 3,
    "long_pozisyon": 3, "short_pozisyon": 3,
    "metin": 4, "isaret": 4, "fiyat_etiketi": 4, "bilgi_paneli": 5,
}


def katman(ad: str) -> int:
    return KATMAN.get(coz(ad), 1)


def coz(ad: str) -> str:
    a = str(ad).strip().lower()
    return TAKMA_AD.get(a, a)


def arac(ad: str):
    a = coz(ad)
    if a not in ARACLAR:
        raise KeyError(f"bilinmeyen araç: {ad} (mevcut: {', '.join(sorted(ARACLAR))})")
    return ARACLAR[a]
