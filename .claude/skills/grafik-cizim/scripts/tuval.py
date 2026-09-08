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
import bisect
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
    if ham <= 0:
        return aralik
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
    if 0 < abs(p) < 1e-6:
        return f"{p:.6g}".replace(".", ",")  # küçük fiyatı sıfıra yuvarlama
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
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("ortalama periyodu pozitif tam sayı olmalı")
    out, top = [], 0.0
    for i, v in enumerate(deger):
        top += v
        if i >= n:
            top -= deger[i - n]
        out.append(top / n if i >= n - 1 else None)
    return out


def _ema(deger: list, n: int) -> list:
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("ortalama periyodu pozitif tam sayı olmalı")
    k, out, e = 2.0 / (n + 1.0), [], None
    for i, v in enumerate(deger):
        if i == n - 1:
            e = sum(deger[:n]) / n
        elif i >= n:
            e = v * k + e * (1 - k)
        out.append(e if i >= n - 1 else None)
    return out


def _rsi(kapanis: list, n: int = 14) -> list:
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("RSI periyodu pozitif tam sayı olmalı")
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
    out[n] = (50.0 if kaz == 0 else 100.0) if kay == 0 else 100 - 100 / (1 + kaz / kay)
    for i in range(n + 1, len(kapanis)):
        d = kapanis[i] - kapanis[i - 1]
        kaz = (kaz * (n - 1) + max(d, 0.0)) / n
        kay = (kay * (n - 1) + max(-d, 0.0)) / n
        out[i] = (50.0 if kaz == 0 else 100.0) if kay == 0 else 100 - 100 / (1 + kaz / kay)
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
                 dipnot: str = "", sol_bosluk: int = 10,
                 history: list | None = None, display_start: int = 0,
                 price_unit: str = "", timezone: str = "UTC", volume_unit: str = ""):
        if not mumlar:
            raise ValueError("mum listesi boş")
        self.log = bool(log_olcek)
        self.m = self._mumlari_dogrula(mumlar)
        self.n = len(self.m)
        if isinstance(display_start, bool) or not isinstance(display_start, int) or display_start < 0:
            raise ValueError("display_start negatif olmayan tam sayı olmalı")
        self.display_start = display_start
        self.history = self.m if history is None else self._mumlari_dogrula(history)
        if display_start + self.n > len(self.history):
            raise ValueError("görünen mum aralığı history sınırlarını aşıyor")
        for visible, original in zip(self.m, self.history[display_start:display_start + self.n]):
            if any(visible.get(k) != original.get(k) for k in ("open", "high", "low", "close", "time")):
                raise ValueError("görünen mumlar history/display_start aralığıyla eşleşmiyor")
        self.price_unit = str(price_unit or "")
        self.timezone = str(timezone or "UTC")
        self.volume_unit = str(volume_unit or "")
        self.W, self.H = int(genislik), int(yukseklik)
        self.t = TEMALAR.get(tema, TEMALAR["koyu"])
        self.tema_ad = tema if tema in TEMALAR else "koyu"
        self.sag_bosluk = max(0, int(sag_bosluk_bar))
        self.baslik, self.alt_baslik, self.dipnot = baslik, alt_baslik, dipnot
        # Footer prose gets its own row below the time axis, including UTC label.
        self.footer_height = 26 if self.dipnot else 0
        self.ALT = type(self).ALT + self.footer_height
        self.time_axis_y = self.H - 8 - self.footer_height
        self.izgara_ac = izgara
        self.paneller = list(paneller or [])
        self.sol = int(sol_bosluk)
        self.sag = self.W - self.FIYAT_EKSENI
        if self.sag <= self.sol or self.H <= self.UST + self.ALT:
            raise ValueError("tuval boyutları çizim alanı için yetersiz")

        self._rezerv: list[float] = []
        self._hazir = False
        self.uyarilar: list[str] = []
        self._axis_badges: list[tuple] = []
        self._label_boxes: list[tuple] = []
        self._rendering_body = False

        # zaman ekseni granülaritesi (bar aralığından)
        zamanlar = [c.get("time") for c in self.m]
        self.bar_ms = None
        if len(zamanlar) >= 2 and all(z is not None for z in zamanlar):
            farklar = sorted(zamanlar[i + 1] - zamanlar[i] for i in range(len(zamanlar) - 1))
            self.bar_ms = farklar[len(farklar) // 2]
        self.gun_bazli = bool(self.bar_ms and self.bar_ms >= 24 * 3600_000)

    def _mumlari_dogrula(self, mumlar: list) -> list:
        sonuc, onceki_zaman = [], None
        for i, kaynak in enumerate(mumlar):
            c = dict(kaynak)
            for alan in ("open", "high", "low", "close"):
                try:
                    v = float(c[alan])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"mum {i}: geçersiz {alan}") from exc
                if not math.isfinite(v) or (self.log and v <= 0):
                    raise ValueError(f"mum {i}: {alan} sonlu olmalı; log ölçekte pozitif olmalı")
                c[alan] = v
            if c["low"] > min(c["open"], c["close"]) or c["high"] < max(c["open"], c["close"]):
                raise ValueError(f"mum {i}: tutarsız OHLC aralığı")
            if c.get("time") is not None:
                try:
                    z = float(c["time"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"mum {i}: geçersiz zaman damgası") from exc
                if not math.isfinite(z) or (onceki_zaman is not None and z <= onceki_zaman):
                    raise ValueError("zaman damgaları sonlu ve kesin artan olmalı")
                c["time"], onceki_zaman = z, z
            if c.get("volume") is not None:
                try:
                    v = float(c["volume"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"mum {i}: geçersiz hacim") from exc
                if not math.isfinite(v) or v < 0:
                    raise ValueError(f"mum {i}: hacim sonlu ve negatif olmayan sayı olmalı")
                c["volume"] = v
            sonuc.append(c)
        return sonuc

    def _uyar(self, metin: str) -> None:
        if metin not in self.uyarilar:
            self.uyarilar.append(metin)

    # ---------------- ölçek
    def rezerve(self, fiyatlar) -> None:
        """Çizimlerin fiyatları — grafik dışına taşmasın diye ölçeğe katılır."""
        for f in (fiyatlar if isinstance(fiyatlar, (list, tuple)) else [fiyatlar]):
            try:
                f = float(f)
            except (TypeError, ValueError) as exc:
                raise ValueError("rezerve fiyat sayısal olmalı") from exc
            if not math.isfinite(f) or (self.log and f <= 0):
                raise ValueError("rezerve fiyat sonlu olmalı; log ölçekte pozitif olmalı")
            self._rezerv.append(f)

    def hazirla(self) -> None:
        yuksekler = [c["high"] for c in self.m]
        alcaklar = [c["low"] for c in self.m]
        hi = max(yuksekler + self._rezerv)
        lo = min(alcaklar + self._rezerv)
        if self.log:
            log_lo, log_hi = math.log(lo), math.log(hi)
            pay = max((log_hi - log_lo) * 0.06, math.log(1.01) if hi == lo else 0)
            try:
                self.hi, self.lo = math.exp(log_hi + pay), math.exp(log_lo - pay)
            except OverflowError as exc:
                raise ValueError("log fiyat aralığı temsil edilemiyor") from exc
        else:
            if hi <= lo:
                pay = max(abs(lo) * 0.01, 1e-8)
            else:
                pay = (hi - lo) * 0.06
            self.hi, self.lo = hi + pay, lo - pay
        if (not all(math.isfinite(f) for f in (self.lo, self.hi)) or self.hi <= self.lo
                or (self.log and self.lo <= 0) or (not self.log and not math.isfinite(self.hi - self.lo))):
            raise ValueError("fiyat aralığı temsil edilemiyor")

        # panel yükseklikleri
        toplam_alan = self.H - self.UST - self.ALT
        paylar = [float(p.get("yukseklik", 0.16)) for p in self.paneller]
        if not all(math.isfinite(pay) for pay in paylar):
            raise ValueError("panel yükseklikleri sonlu olmalı")
        paylar = [max(0.0, pay) for pay in paylar]
        toplam_pay = sum(paylar)
        carpan = min(1.0, 0.6 / toplam_pay) if toplam_pay else 1.0
        paylar = [pay * carpan for pay in paylar]
        pay_toplam = sum(paylar)
        self.panel_alan = toplam_alan * pay_toplam
        self.ana_ust = self.UST
        self.ana_alt = self.UST + (toplam_alan - self.panel_alan)
        y = self.ana_alt
        self.panel_kutu = []
        for pay in paylar:
            h = toplam_alan * pay
            self.panel_kutu.append((y + min(6, h / 4), y + h - min(4, h / 4)))
            if 0 < h < 24:
                self._uyar("panel alanı dar; panel başlıkları üst üste gelebilir")
            y += h
        self.bar_w = (self.sag - self.sol) / max(1.0, self.n + self.sag_bosluk)
        self._hazir = True

    def x(self, bar) -> float:
        """bar: int (negatif = sondan), float (kesirli/gelecek) veya {'zaman': ms}."""
        i = self.bar_indeks(bar)
        return self.sol + (i + 0.5) * self.bar_w

    def bar_indeks(self, bar) -> float:
        if isinstance(bar, dict):
            if "index" in bar:
                b = float(bar["index"])
                if not math.isfinite(b):
                    raise ValueError("bar indeksi sonlu olmalı")
                return b
            if "zaman" in bar:
                return self._zamandan_indeks(float(bar["zaman"]))
            bar = bar.get("bar", 0)
        if bar is None:
            return float(self.n - 1)
        b = float(bar)
        if not math.isfinite(b):
            raise ValueError("bar indeksi sonlu olmalı")
        if b < 0:
            b = self.n + b
        return b

    def _zamandan_indeks(self, ms: float) -> float:
        zamanlar = [c.get("time") for c in self.m]
        if not math.isfinite(ms):
            raise ValueError("zaman referansı sonlu olmalı")
        if not zamanlar or any(z is None for z in zamanlar):
            raise ValueError("zaman damgası yok — 'zaman' referansı indekse çevrilemedi")
        if self.bar_ms and ms > zamanlar[-1]:
            return (self.n - 1) + (ms - zamanlar[-1]) / self.bar_ms
        if self.bar_ms and ms < zamanlar[0]:
            return (ms - zamanlar[0]) / self.bar_ms
        i = bisect.bisect_left(zamanlar, ms)
        if i < len(zamanlar) and zamanlar[i] == ms:
            return float(i)
        if i == 0 or i == len(zamanlar):
            raise ValueError("tek mumla farklı zaman referansı hesaplanamaz")
        return (i - 1) + (ms - zamanlar[i - 1]) / (zamanlar[i] - zamanlar[i - 1])

    def y(self, fiyat: float) -> float:
        f = float(fiyat)
        if not math.isfinite(f) or (self.log and f <= 0):
            raise ValueError("fiyat sonlu olmalı; log ölçekte pozitif olmalı")
        ust, alt = self.ana_ust, self.ana_alt
        if self.log:
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
                f'stroke="{_oz(renk)}" stroke-width="{kacir(kalinlik)}" stroke-opacity="{kacir(saydam)}"'
                f'{d}{m} stroke-linecap="round"/>')

    def kutu(self, x1, y1, x2, y2, dolgu=None, kenar=None, dolgu_saydam=0.16,
             kalinlik=1.2, kesik=None, kose=0) -> str:
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        p = [f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{max(0.5, x2 - x1):.1f}" '
             f'height="{max(0.5, y2 - y1):.1f}" rx="{kacir(kose)}"']
        p.append(f'fill="{_oz(dolgu)}" fill-opacity="{kacir(dolgu_saydam)}"' if dolgu else 'fill="none"')
        if kenar:
            p.append(f'stroke="{_oz(kenar)}" stroke-width="{kacir(kalinlik)}"')
            if kesik:
                p.append(f'stroke-dasharray="{_oz(kesik)}"')
        return " ".join(p) + "/>"

    def yazi(self, x, y, metin, renk=None, boyut=12, hiza="start", kalin=False,
             saydam=1.0) -> str:
        renk = renk or self.t["metin"]
        if self._hazir and not self._rendering_body and self.paneller and y > self.ana_alt:
            self._uyar(f"çizim etiketi alt panel alanıyla çakışıyor: {str(metin)[:60]}")
        agirlik = ' font-weight="600"' if kalin else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{kacir(renk)}" font-size="{kacir(boyut)}" '
                f'font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif" '
                f'text-anchor="{kacir(hiza)}"{agirlik} fill-opacity="{kacir(saydam)}">'
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
        original_x, original_y = x, y
        if self._hazir and self.sol <= x <= self.sag and self.ana_ust <= y <= self.ana_alt:
            available=self.sag-self.sol-4
            if g>available:
                boyut=max(7,boyut*available/g);g=available
                self._uyar('uzun etiket çizim alanına sığdırıldı; okunabilirlik incelenmeli')
            x1=max(self.sol+2,min(x1,self.sag-g-2))
            y=max(self.ana_ust+10,min(y,self.ana_alt-10))
            def free(candidate):
                return all(x1+g < a or x1 > c or candidate+9 < b or candidate-9 > d
                           for a,b,c,d in self._label_boxes)
            candidates=[y]+[y+direction*step for step in (20,40,60) for direction in (1,-1)]
            fitted=next((candidate for candidate in candidates
                         if self.ana_ust+10 <= candidate <= self.ana_alt-10 and free(candidate)),None)
            if fitted is None:
                self._uyar('çizim etiketleri yoğun; bazı etiketler çakışabilir')
            else:
                y=fitted
            self._label_boxes.append((x1,y-9,x1+g,y+9))
        leader=''
        if abs(y-original_y)>1:
            leader=self.cizgi(original_x,original_y,min(x1+g,max(x1,original_x)),y,renk,.8)
        parts = [leader, self.kutu(x1, y - 9, x1 + g, y + 8, dolgu=renk, kenar=None,
                           dolgu_saydam=dolgu_saydam, kose=2)]
        parts.append(self.yazi(x1 + g / 2, y + 4, metin, renk=metin_renk,
                               boyut=boyut, hiza="middle", kalin=True))
        return "".join(parts)

    def fiyat_ekseni_etiketi(self, fiyat, renk, metin=None) -> str:
        """Rozeti kuyruğa al; render() çakışmaları ayarlayıp kırpma dışında çizer."""
        self.y(fiyat)  # fiyatı doğrula
        badge = (float(fiyat), str(renk), str(metin if metin is not None else bicim_fiyat(fiyat)))
        if badge not in self._axis_badges:
            self._axis_badges.append(badge)
        return f'<g data-axis-badge="{self._axis_badges.index(badge)}"/>'

    def _fiyat_rozetleri(self) -> str:
        badges = sorted(self._axis_badges, key=lambda b: self.y(b[0]))
        if not badges:
            return ""
        y_min, y_max = self.ana_ust + 10, self.ana_alt - 10
        aralik = 20.0
        if len(badges) > 1 and aralik * (len(badges) - 1) > y_max - y_min:
            aralik = max(0.0, (y_max - y_min) / (len(badges) - 1))
            self._uyar("fiyat ekseninde çok fazla rozet var; fiyat etiketleri üst üste gelebilir")
        merkezler = []
        for fiyat, _, _ in badges:
            hedef = min(y_max, max(y_min, self.y(fiyat)))
            merkezler.append(max(hedef, merkezler[-1] + aralik) if merkezler else hedef)
        if merkezler[-1] > y_max:
            merkezler[-1] = y_max
            for i in range(len(merkezler) - 2, -1, -1):
                merkezler[i] = min(merkezler[i], merkezler[i + 1] - aralik)
        p = ['<g data-price-axis-badges="true">']
        for (fiyat, renk, metin), y in zip(badges, merkezler):
            asil_y = self.y(fiyat)
            if abs(y - asil_y) > 0.5:
                p.append(self.cizgi(self.sag - 2, min(self.ana_alt, max(self.ana_ust, asil_y)),
                                    self.sag + 5, y, renk, 1))
            p.append(self.kutu(self.sag + 5, y - 9, self.W - 2, y + 9, dolgu=renk,
                               kenar=None, dolgu_saydam=1.0, kose=2))
            p.append(self.yazi((self.sag + self.W + 3) / 2, y + 4, metin, renk="#ffffff",
                               boyut=11, hiza="middle", kalin=True))
        p.append("</g>")
        return "".join(p)

    # ---------------- gövde
    def _arka(self) -> str:
        return self.kutu(0, 0, self.W, self.H, dolgu=self.t["arka"],
                         kenar=None, dolgu_saydam=1.0)

    def _izgara_ve_eksen(self) -> str:
        p = []
        adim = _guzel_adim(self.hi - self.lo, 9)
        ond = max(0, min(8, -math.floor(math.log10(adim)) + 1)) if adim > 0 else 2
        f = math.ceil(self.lo / adim) * adim
        for _ in range(100):
            if f > self.hi:
                break
            y = self.y(f)
            if self.izgara_ac:
                p.append(self.cizgi(self.sol, y, self.sag, y, self.t["izgara"], 1))
            p.append(self.yazi(self.sag + 8, y + 4, bicim_fiyat(f, ond),
                               renk=self.t["metin_soluk"], boyut=11))
            sonraki = f + adim
            if sonraki <= f:
                break
            f = sonraki
        # zaman ekseni
        adet = max(4, min(12, self.n // 12))
        aralik = max(1, self.n // adet)
        prior_label_right = -float("inf")
        for i in range(0, self.n, aralik):
            x = self.x(i)
            if self.izgara_ac:
                p.append(self.cizgi(x, self.UST, x, self.ana_alt, self.t["izgara"], 1))
            z = self.m[i].get("time")
            etk = _zaman_etiketi(z, self.gun_bazli) if z is not None else str(i)
            label_width = len(etk)*6.2
            anchor = "start" if x < self.sol+65 else "middle"
            label_left = x if anchor == "start" else x-label_width/2
            if label_left >= prior_label_right+8:
                p.append(self.yazi(max(self.sol+2,x), self.time_axis_y, etk,
                                   renk=self.t["metin_soluk"],boyut=11,hiza=anchor))
                prior_label_right=label_left+label_width
        p.append(self.cizgi(self.sag, self.UST, self.sag, self.H - self.ALT + 4,
                            self.t["eksen"], 1))
        p.append(self.cizgi(self.sol, self.ana_alt, self.sag, self.ana_alt,
                            self.t["eksen"], 1))
        if self.price_unit:
            p.append(self.yazi(self.sag + 5, self.UST - 8, self.price_unit + (" · log" if self.log else ""),
                               renk=self.t["metin_soluk"], boyut=10))
        p.append(self.yazi(self.W - 5, self.time_axis_y, self.timezone,
                           renk=self.t["metin_soluk"], boyut=10, hiza="end"))
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
        for cfg, (ust, alt) in zip(self.paneller, self.panel_kutu):
            if alt <= ust:
                continue
            tip = str(cfg.get("tip", "hacim")).lower()
            p.append(self.kutu(self.sol, ust, self.sag, alt, dolgu=self.t["panel"],
                               kenar=None, dolgu_saydam=0.5))
            if tip in ("hacim", "volume"):
                hac = [c.get("volume") or 0.0 for c in self.m]
                mx = max(hac) or 1.0
                gov = max(1.0, self.bar_w * 0.68)
                for i, v in enumerate(hac):
                    if self.m[i].get("_volume_missing"):
                        continue
                    h = (v / mx) * max(0, alt - ust - 4)
                    renk = (self.t["yukari"] if self.m[i]["close"] >= self.m[i]["open"]
                            else self.t["asagi"])
                    p.append(self.kutu(self.x(i) - gov / 2, alt - h, self.x(i) + gov / 2,
                                       alt, dolgu=renk, kenar=None, dolgu_saydam=0.55))
                hacim_ad = f"Hacim ({self.volume_unit})" if self.volume_unit else "Hacim"
                p.append(self.yazi(self.sol + 6, ust + 13, hacim_ad,
                                   renk=self.t["metin_soluk"], boyut=10))
            elif tip in ("rsi", "stoch_rsi"):
                per = int(cfg.get("period", 14))
                tam_seri, parca, onceki = [], [], None
                for c in self.history:
                    segment = c.get("segment_id", 0)
                    if parca and segment != onceki:
                        tam_seri.extend(_rsi(parca, per))
                        parca = []
                    parca.append(c["close"])
                    onceki = segment
                tam_seri.extend(_rsi(parca, per))
                seri = tam_seri[self.display_start:self.display_start + self.n]
                p.append(self._panel_seri(seri, ust, alt, 0, 100, cfg.get("renk", "#c792ea"),
                                          [30, 50, 70], f"RSI({per})"))
            elif tip in ("seri", "line"):
                seri = [None if v is None else float(v) for v in cfg.get("deger", [])]
                if any(v is not None and not math.isfinite(v) for v in seri):
                    raise ValueError("panel serisi sonlu sayılar veya eksik değer içermeli")
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
            bosluk = min(4, (alt - ust) / 4)
            return alt - (v - lo) / (hi - lo) * (alt - ust - 2 * bosluk) - bosluk

        def parcayi_ekle():
            if nokta:
                p.append(f'<polyline points="{" ".join(nokta)}" fill="none" '
                         f'stroke="{kacir(renk)}" stroke-width="1.4"/>')
                nokta.clear()

        for r in ref:
            p.append(self.cizgi(self.sol, yy(r), self.sag, yy(r), self.t["eksen"],
                                1, kesik="3 4"))
        for i, v in enumerate(seri):
            if v is None or not math.isfinite(v):
                parcayi_ekle()
                continue
            nokta.append(f"{self.x(i):.1f},{yy(v):.1f}")
        parcayi_ekle()
        gecerli = [v for v in seri if v is not None and math.isfinite(v)]
        if gecerli:
            son = gecerli[-1]
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
        self.fiyat_ekseni_etiketi(son, son_renk)
        self._rendering_body = True
        try:
            govde = "".join([
                self._arka(),
                self._izgara_ve_eksen(),
                self._alt_paneller(),
                '<g clip-path="url(#plot-clip)" data-plot-layers="true">',
                arka_svg,
                self._mumlar(),
                cizim_svg,
                self.cizgi(self.sol, self.y(son), self.sag, self.y(son), son_renk,
                           1, kesik="4 4", saydam=0.8),
                '</g>',
                self._fiyat_rozetleri(),
                self._baslik(),
                self._dipnot(),
            ])
        finally:
            self._rendering_body = False
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.W}" '
                f'height="{self.H}" viewBox="0 0 {self.W} {self.H}">'
                f'<defs><marker id="ok" markerWidth="9" markerHeight="9" refX="7" '
                f'refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="context-stroke"/>'
                f'</marker><clipPath id="plot-clip"><rect x="{self.sol}" y="{self.ana_ust}" '
                f'width="{self.sag - self.sol}" height="{self.ana_alt - self.ana_ust}"/>'
                f'</clipPath></defs>{govde}</svg>')


# hareketli ortalama yardımcıları araclar.py'den de kullanılır
sma, ema, rsi = _sma, _ema, _rsi
