#!/usr/bin/env python3
"""Tuval — TradingView benzeri mum grafiği SVG tuvali (SIFIR bağımlılık).

Neden SVG: bu ortamda matplotlib KURULU DEĞİL (grafik-calisma/SKILL.md'nin
"C) Grafik üretme" maddesi bu yüzden çalışmıyordu). SVG stdlib ile üretilir,
vektörel olduğu için fiyat etiketleri hiçbir ölçekte bozulmaz ve doğrudan
görüntülenebilir.

Tuvalin sorumluluğu SADECE koordinat + gövde:
  · fiyat ↔ piksel ölçeği (doğrusal / logaritmik)
  · bar indeksi ↔ piksel (negatif indeks = sondan; n'den büyük = geleceğe
    projeksiyon — TradingView'daki sağ boşluk)
  · mum gövdeleri, ızgara, sağ fiyat ekseni, zaman ekseni, alt paneller
  · tema (koyu/açık)

Çizim ARAÇLARI araclar.py'dedir; tuval onlara x()/y()/etiket() verir.
"""
from __future__ import annotations

import datetime as _dt
import math
import re

# ---------------------------------------------------------------- temalar
TEMALAR = {
    "koyu": {
        "arka": "#131722", "izgara": "#252a35", "eksen": "#363c4e",
        "metin": "#d1d4dc", "metin_soluk": "#787b86",
        "yukari": "#26a69a", "asagi": "#ef5350",
        "yukari_fitil": "#26a69a", "asagi_fitil": "#ef5350",
        "panel": "#1b2130", "vurgu": "#2962ff",
        "olumlu": "#26a69a", "olumsuz": "#ef5350", "notr": "#ff9800",
    },
    "acik": {
        "arka": "#ffffff", "izgara": "#eef0f4", "eksen": "#d6dae2",
        "metin": "#131722", "metin_soluk": "#6a6d78",
        "yukari": "#089981", "asagi": "#f23645",
        "yukari_fitil": "#089981", "asagi_fitil": "#f23645",
        "panel": "#f4f6fa", "vurgu": "#2962ff",
        "olumlu": "#089981", "olumsuz": "#f23645", "notr": "#ff9800",
    },
}

_AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
          "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


# ---------------------------------------------------------------- yardımcı
def kacir(s) -> str:
    """XML kaçışı."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


_OZ_GUVENLI = re.compile(r"[^#a-zA-Z0-9 .,()%-]")


def _oz(v) -> str:
    """Öznitelik değeri güvenli süzgeci (S1): renk/kesik gibi job'dan gelen
    değerlerdeki `"` ya da SVG-kırıcı/enjeksiyon karakterlerini AT. cizgi/kutu
    bu değerleri kaçışsız gömdüğü için gereklidir."""
    return _OZ_GUVENLI.sub("", str(v))


def _guzel_adim(aralik: float, hedef: int = 8) -> float:
    if aralik <= 0:
        return 1.0
    ham = aralik / max(1, hedef)
    us = math.floor(math.log10(ham))
    taban = 10.0 ** us
    for m in (1, 2, 2.5, 5, 10):
        if ham <= taban * m:
            return taban * m
    return taban * 10


def bicim_fiyat(p: float, ondalik: int | None = None) -> str:
    """62887.8 → '62.887,80' (TR biçimi; kullanıcının grafiklerindeki gibi)."""
    if p is None or (isinstance(p, float) and (math.isnan(p) or math.isinf(p))):
        return "VERİ YOK"
    if ondalik is None:
        a = abs(p)
        ondalik = 2 if a >= 100 else 4 if a >= 1 else 6
    s = f"{abs(p):,.{ondalik}f}"
    s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return ("-" if p < 0 else "") + s


def _zaman_etiketi(ms: float, gun_bazli: bool) -> str:
    d = _dt.datetime.fromtimestamp(ms / 1000.0, _dt.timezone.utc)
    if gun_bazli:
        return f"{d.day} {_AYLAR[d.month - 1]}"
    return f"{d.day} {_AYLAR[d.month - 1]} {d.hour:02d}:{d.minute:02d}"


def _sma(deger: list, n: int) -> list:
    out, top = [], 0.0
    for i, v in enumerate(deger):
        top += v
        if i >= n:
            top -= deger[i - n]
        out.append(top / n if i >= n - 1 else None)
    return out


def _ema(deger: list, n: int) -> list:
    k, out, e = 2.0 / (n + 1.0), [], None
    for i, v in enumerate(deger):
        if i == n - 1:
            e = sum(deger[:n]) / n
        elif i >= n:
            e = v * k + e * (1 - k)
        out.append(e if i >= n - 1 else None)
    return out


def _rsi(kapanis: list, n: int = 14) -> list:
    if len(kapanis) < n + 1:
        return [None] * len(kapanis)
    out = [None] * len(kapanis)
    kaz = kay = 0.0
    for i in range(1, n + 1):
        d = kapanis[i] - kapanis[i - 1]
        kaz += max(d, 0.0)
        kay += max(-d, 0.0)
    kaz /= n
    kay /= n
    out[n] = 100.0 if kay == 0 else 100 - 100 / (1 + kaz / kay)
    for i in range(n + 1, len(kapanis)):
        d = kapanis[i] - kapanis[i - 1]
        kaz = (kaz * (n - 1) + max(d, 0.0)) / n
        kay = (kay * (n - 1) + max(-d, 0.0)) / n
        out[i] = 100.0 if kay == 0 else 100 - 100 / (1 + kaz / kay)
    return out


# ---------------------------------------------------------------- tuval
class Tuval:
    """Mum grafiği tuvali. Önce rezerve(), sonra hazirla(), sonra ciz()."""

    FIYAT_EKSENI = 78
    UST = 46
    ALT = 26

    def __init__(self, mumlar: list, *, genislik: int = 1600, yukseklik: int = 900,
                 tema: str = "koyu", log_olcek: bool = False,
                 sag_bosluk_bar: int = 25, baslik: str = "", alt_baslik: str = "",
                 paneller: list | None = None, izgara: bool = True,
                 dipnot: str = "", sol_bosluk: int = 10):
        if not mumlar:
            raise ValueError("mum listesi boş")
        self.m = mumlar
        self.n = len(mumlar)
        self.W, self.H = int(genislik), int(yukseklik)
        self.t = TEMALAR.get(tema, TEMALAR["koyu"])
        self.tema_ad = tema if tema in TEMALAR else "koyu"
        self.log = bool(log_olcek)
        self.sag_bosluk = max(0, int(sag_bosluk_bar))
        self.baslik, self.alt_baslik, self.dipnot = baslik, alt_baslik, dipnot
        self.izgara_ac = izgara
        self.paneller = list(paneller or [])
        self.sol = int(sol_bosluk)
        self.sag = self.W - self.FIYAT_EKSENI

        self._rezerv: list[float] = []
        self._hazir = False
        self.uyarilar: list[str] = []

        # zaman ekseni granülaritesi (bar aralığından)
        zamanlar = [c.get("time") for c in mumlar if c.get("time")]
        self.bar_ms = None
        if len(zamanlar) >= 2:
            farklar = sorted(zamanlar[i + 1] - zamanlar[i] for i in range(len(zamanlar) - 1))
            self.bar_ms = farklar[len(farklar) // 2]
        self.gun_bazli = bool(self.bar_ms and self.bar_ms >= 4 * 3600_000)

    # ---------------- ölçek
    def rezerve(self, fiyatlar) -> None:
        """Çizimlerin fiyatları — grafik dışına taşmasın diye ölçeğe katılır."""
        for f in (fiyatlar if isinstance(fiyatlar, (list, tuple)) else [fiyatlar]):
            try:
                f = float(f)
            except (TypeError, ValueError):
                continue
            if math.isfinite(f) and (not self.log or f > 0):
                self._rezerv.append(f)

    def hazirla(self) -> None:
        yuksekler = [c["high"] for c in self.m]
        alcaklar = [c["low"] for c in self.m]
        hi = max(yuksekler + self._rezerv)
        lo = min(alcaklar + self._rezerv)
        if hi <= lo:
            hi, lo = hi + 1, lo - 1
        pay = (hi - lo) * 0.06
        self.hi, self.lo = hi + pay, max(lo - pay, 1e-12) if self.log else lo - pay

        # panel yükseklikleri
        toplam_alan = self.H - self.UST - self.ALT
        pay_toplam = sum(float(p.get("yukseklik", 0.16)) for p in self.paneller)
        pay_toplam = min(pay_toplam, 0.6)
        self.panel_alan = toplam_alan * pay_toplam
        self.ana_ust = self.UST
        self.ana_alt = self.UST + (toplam_alan - self.panel_alan)
        y = self.ana_alt
        self.panel_kutu = []
        for p in self.paneller:
            h = toplam_alan * min(float(p.get("yukseklik", 0.16)), 0.6)
            self.panel_kutu.append((y + 6, y + h - 4))
            y += h
        self.bar_w = (self.sag - self.sol) / max(1.0, self.n + self.sag_bosluk)
        self._hazir = True

    def x(self, bar) -> float:
        """bar: int (negatif = sondan), float (kesirli/gelecek) veya {'zaman': ms}."""
        i = self.bar_indeks(bar)
        return self.sol + (i + 0.5) * self.bar_w

    def bar_indeks(self, bar) -> float:
        if isinstance(bar, dict):
            if "zaman" in bar:
                return self._zamandan_indeks(float(bar["zaman"]))
            bar = bar.get("bar", 0)
        if bar is None:
            return float(self.n - 1)
        b = float(bar)
        if b < 0:
            b = self.n + b
        return b

    def _zamandan_indeks(self, ms: float) -> float:
        zamanlar = [c.get("time") for c in self.m]
        if not zamanlar or zamanlar[0] is None:
            self.uyarilar.append("zaman damgası yok — 'zaman' referansı indekse çevrilemedi")
            return float(self.n - 1)
        if self.bar_ms and ms > zamanlar[-1]:
            return (self.n - 1) + (ms - zamanlar[-1]) / self.bar_ms
        en_iyi, mesafe = 0, None
        for i, z in enumerate(zamanlar):
            if z is None:
                continue
            d = abs(z - ms)
            if mesafe is None or d < mesafe:
                en_iyi, mesafe = i, d
        return float(en_iyi)

    def y(self, fiyat: float) -> float:
        f = float(fiyat)
        ust, alt = self.ana_ust, self.ana_alt
        if self.log:
            f = max(f, 1e-12)
            oran = ((math.log(f) - math.log(self.lo))
                    / (math.log(self.hi) - math.log(self.lo)))
        else:
            oran = (f - self.lo) / (self.hi - self.lo)
        return alt - oran * (alt - ust)

    def fiyat_y(self, y: float) -> float:
        """Ters dönüşüm (etiket yerleşimi için)."""
        oran = (self.ana_alt - y) / (self.ana_alt - self.ana_ust)
        if self.log:
            return math.exp(math.log(self.lo) + oran * (math.log(self.hi) - math.log(self.lo)))
        return self.lo + oran * (self.hi - self.lo)

    # ---------------- ilkel çizimler (araclar.py bunları kullanır)
    def cizgi(self, x1, y1, x2, y2, renk, kalinlik=1.4, kesik=None, saydam=1.0,
              ok=False) -> str:
        d = f' stroke-dasharray="{_oz(kesik)}"' if kesik else ""
        m = ' marker-end="url(#ok)"' if ok else ""
        return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{_oz(renk)}" stroke-width="{kalinlik}" stroke-opacity="{saydam}"'
                f'{d}{m} stroke-linecap="round"/>')

    def kutu(self, x1, y1, x2, y2, dolgu=None, kenar=None, dolgu_saydam=0.16,
             kalinlik=1.2, kesik=None, kose=0) -> str:
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        p = [f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{max(0.5, x2 - x1):.1f}" '
             f'height="{max(0.5, y2 - y1):.1f}" rx="{kose}"']
        p.append(f'fill="{_oz(dolgu)}" fill-opacity="{dolgu_saydam}"' if dolgu else 'fill="none"')
        if kenar:
            p.append(f'stroke="{_oz(kenar)}" stroke-width="{kalinlik}"')
            if kesik:
                p.append(f'stroke-dasharray="{_oz(kesik)}"')
        return " ".join(p) + "/>"

    def yazi(self, x, y, metin, renk=None, boyut=12, hiza="start", kalin=False,
             saydam=1.0) -> str:
        renk = renk or self.t["metin"]
        agirlik = ' font-weight="600"' if kalin else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{renk}" font-size="{boyut}" '
                f'font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif" '
                f'text-anchor="{hiza}"{agirlik} fill-opacity="{saydam}">'
                f'{kacir(metin)}</text>')

    def etiket_kutu(self, x, y, metin, renk, *, metin_renk="#ffffff", boyut=11,
                    hiza="start", dolgu_saydam=1.0) -> str:
        """TradingView tarzı dolu etiket hapı."""
        g = 7.0 * len(str(metin)) + 12
        if hiza == "end":
            x1 = x - g
        elif hiza == "middle":
            x1 = x - g / 2
        else:
            x1 = x
        parts = [self.kutu(x1, y - 9, x1 + g, y + 8, dolgu=renk, kenar=None,
                           dolgu_saydam=dolgu_saydam, kose=2)]
        parts.append(self.yazi(x1 + g / 2, y + 4, metin, renk=metin_renk,
                               boyut=boyut, hiza="middle", kalin=True))
        return "".join(parts)

    def fiyat_ekseni_etiketi(self, fiyat, renk, metin=None) -> str:
        """Sağ fiyat ekseninde fiyat rozeti (kullanıcının grafiklerindeki gibi)."""
        y = self.y(fiyat)
        m = metin or bicim_fiyat(fiyat)
        return "".join([
            self.kutu(self.sag + 1, y - 9, self.W - 2, y + 9, dolgu=renk,
                      kenar=None, dolgu_saydam=1.0, kose=2),
            self.yazi((self.sag + self.W) / 2, y + 4, m, renk="#ffffff",
                      boyut=11, hiza="middle", kalin=True)])

    # ---------------- gövde
    def _arka(self) -> str:
        return self.kutu(0, 0, self.W, self.H, dolgu=self.t["arka"],
                         kenar=None, dolgu_saydam=1.0)

    def _izgara_ve_eksen(self) -> str:
        p = []
        adim = _guzel_adim(self.hi - self.lo, 9)
        ond = max(0, min(8, -math.floor(math.log10(adim)) + 1)) if adim > 0 else 2
        f = math.ceil(self.lo / adim) * adim
        while f <= self.hi:
            y = self.y(f)
            if self.izgara_ac:
                p.append(self.cizgi(self.sol, y, self.sag, y, self.t["izgara"], 1))
            p.append(self.yazi(self.sag + 8, y + 4, bicim_fiyat(f, ond),
                               renk=self.t["metin_soluk"], boyut=11))
            f += adim
        # zaman ekseni
        adet = max(4, min(12, self.n // 12))
        aralik = max(1, self.n // adet)
        for i in range(0, self.n, aralik):
            x = self.x(i)
            if self.izgara_ac:
                p.append(self.cizgi(x, self.UST, x, self.ana_alt, self.t["izgara"], 1))
            z = self.m[i].get("time")
            etk = _zaman_etiketi(z, self.gun_bazli) if z else str(i)
            p.append(self.yazi(x, self.H - 8, etk, renk=self.t["metin_soluk"],
                               boyut=11, hiza="middle"))
        p.append(self.cizgi(self.sag, self.UST, self.sag, self.H - self.ALT + 4,
                            self.t["eksen"], 1))
        p.append(self.cizgi(self.sol, self.ana_alt, self.sag, self.ana_alt,
                            self.t["eksen"], 1))
        return "".join(p)

    def _mumlar(self) -> str:
        p = []
        gov = max(1.0, self.bar_w * 0.68)
        for i, c in enumerate(self.m):
            x = self.x(i)
            yukari = c["close"] >= c["open"]
            renk = self.t["yukari"] if yukari else self.t["asagi"]
            p.append(self.cizgi(x, self.y(c["high"]), x, self.y(c["low"]), renk, 1.0))
            y1, y2 = self.y(c["open"]), self.y(c["close"])
            if abs(y1 - y2) < 1:
                y2 = y1 + 1
            p.append(self.kutu(x - gov / 2, y1, x + gov / 2, y2, dolgu=renk,
                               kenar=renk, dolgu_saydam=1.0, kalinlik=0.8))
        return "".join(p)

    def _alt_paneller(self) -> str:
        p = []
        kapanis = [c["close"] for c in self.m]
        for cfg, (ust, alt) in zip(self.paneller, self.panel_kutu):
            tip = str(cfg.get("tip", "hacim")).lower()
            p.append(self.kutu(self.sol, ust, self.sag, alt, dolgu=self.t["panel"],
                               kenar=None, dolgu_saydam=0.5))
            if tip in ("hacim", "volume"):
                hac = [c.get("volume") or 0.0 for c in self.m]
                mx = max(hac) or 1.0
                gov = max(1.0, self.bar_w * 0.68)
                for i, v in enumerate(hac):
                    h = (v / mx) * (alt - ust - 4)
                    renk = (self.t["yukari"] if self.m[i]["close"] >= self.m[i]["open"]
                            else self.t["asagi"])
                    p.append(self.kutu(self.x(i) - gov / 2, alt - h, self.x(i) + gov / 2,
                                       alt, dolgu=renk, kenar=None, dolgu_saydam=0.55))
                p.append(self.yazi(self.sol + 6, ust + 13, "Hacim",
                                   renk=self.t["metin_soluk"], boyut=10))
            elif tip in ("rsi", "stoch_rsi"):
                per = int(cfg.get("period", 14))
                seri = _rsi(kapanis, per)
                p.append(self._panel_seri(seri, ust, alt, 0, 100, cfg.get("renk", "#c792ea"),
                                          [30, 50, 70], f"RSI({per})"))
            elif tip in ("seri", "line"):
                seri = [None if v is None else float(v) for v in cfg.get("deger", [])]
                seri = (seri + [None] * self.n)[:self.n]
                gec = [v for v in seri if v is not None] or [0, 1]
                p.append(self._panel_seri(seri, ust, alt, min(gec), max(gec),
                                          cfg.get("renk", self.t["vurgu"]), [],
                                          str(cfg.get("ad", "seri"))))
            else:
                self.uyarilar.append(f"bilinmeyen panel tipi: {tip}")
        return "".join(p)

    def _panel_seri(self, seri, ust, alt, lo, hi, renk, ref, ad) -> str:
        p, nokta = [], []
        if hi <= lo:
            hi = lo + 1

        def yy(v):
            return alt - (v - lo) / (hi - lo) * (alt - ust - 8) - 4

        for r in ref:
            p.append(self.cizgi(self.sol, yy(r), self.sag, yy(r), self.t["eksen"],
                                1, kesik="3 4"))
        for i, v in enumerate(seri):
            if v is None:
                continue
            nokta.append(f"{self.x(i):.1f},{yy(v):.1f}")
        if nokta:
            p.append(f'<polyline points="{" ".join(nokta)}" fill="none" '
                     f'stroke="{renk}" stroke-width="1.4"/>')
            son = [v for v in seri if v is not None][-1]
            p.append(self.yazi(self.sag + 8, yy(son) + 4, f"{son:.2f}", renk=renk, boyut=10))
        p.append(self.yazi(self.sol + 6, ust + 13, ad, renk=self.t["metin_soluk"], boyut=10))
        return "".join(p)

    def _baslik(self) -> str:
        p = [self.yazi(self.sol + 4, 22, self.baslik, boyut=15, kalin=True)]
        if self.alt_baslik:
            p.append(self.yazi(self.sol + 4, 38, self.alt_baslik,
                               renk=self.t["metin_soluk"], boyut=11))
        return "".join(p)

    def _dipnot(self) -> str:
        if not self.dipnot:
            return ""
        return self.yazi(self.sol + 4, self.H - 8, self.dipnot,
                         renk=self.t["metin_soluk"], boyut=10)

    def render(self, cizim_svg: str = "", arka_svg: str = "") -> str:
        """arka_svg: mumların ARKASINA çizilenler (bölge/kanal — TradingView düzeni)."""
        if not self._hazir:
            self.hazirla()
        son = self.m[-1]["close"]
        son_renk = (self.t["yukari"] if son >= self.m[-1]["open"] else self.t["asagi"])
        govde = "".join([
            self._arka(),
            self._izgara_ve_eksen(),
            self._alt_paneller(),
            arka_svg,
            self._mumlar(),
            cizim_svg,
            self.cizgi(self.sol, self.y(son), self.sag, self.y(son), son_renk,
                       1, kesik="4 4", saydam=0.8),
            self.fiyat_ekseni_etiketi(son, son_renk),
            self._baslik(),
            self._dipnot(),
        ])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.W}" '
                f'height="{self.H}" viewBox="0 0 {self.W} {self.H}">'
                f'<defs><marker id="ok" markerWidth="9" markerHeight="9" refX="7" '
                f'refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="context-stroke"/>'
                f'</marker></defs>{govde}</svg>')


# hareketli ortalama yardımcıları araclar.py'den de kullanılır
sma, ema, rsi = _sma, _ema, _rsi
