#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KARAR MOTORU v1 — 15M taktik + 4H stratejik Binance kline karar motoru.

Tasarım sözleşmesi (spesifikasyondan):
- Sabitlenmiş mutlak eşik yok: hacim = son N_VOL barın yüzdelik sırası,
  gövde = son N_BODY barın q(BODY_Q)'su, 4H trend = MA5-MA20 farkının kendi
  geçmişinin q(TREND_Q)'su. Her koşuda o anki veriden yeniden hesaplanır.
- Her koşuda TEK karar: LONG / SHORT / BEKLE. Senaryo çatalı yok.
- Karar zinciri (ilk tutan kazanır):
    (1) tamamlanmış dönüş dizisi (süpürme -> geri alım -> displacement -> BOS)
    (2) 15M yapı kırılımı + teyit, 4H karşı değilse
    (3) 4H rejimi + hizalı açık FVG (PUSU)
    (4) BEKLE (tek satır gerekçe)
- Hafıza = akıbet takibi + seviye taşıma. Önceki YÖN yeni karara ağırlık olarak
  GİRMEZ; zincir her koşuda sıfırdan çalışır. Önceki kararın akıbeti yeni fiyat
  yolundan etiketlenir ve raporlanır (durum.json + defter.jsonl).
- Bütün yapısal sabitler çıktıda beyan edilir (SABİTLER bloğu).

Girdi: --m15 ve --h4 dosyaları. Kabul edilen biçimler:
  Binance REST kline JSON'u (liste-listesi), JSON obje listesi
  (open/high/low/close/volume alanlı) veya başlıklı/başlıksız CSV
  (ilk 6 kolon: open_time, open, high, low, close, volume).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# YAPISAL SABİTLER (kalibrasyon değil, yapı tanımı; çıktıda beyan edilir)
# ---------------------------------------------------------------------------
N_VOL = 96          # hacim yüzdelik penceresi (15M bar)
VOL_RANK_MIN = 0.80 # displacement için gereken hacim yüzdelik sırası
N_BODY = 48         # gövde penceresi (15M bar)
BODY_Q = 0.90       # "güçlü gövde" = bu pencerenin q90'ı
MA_FAST = 5         # 4H hızlı MA
MA_SLOW = 20        # 4H yavaş MA
TREND_Q = 0.60      # |MA5-MA20| rejim eşiği = fark geçmişinin q60'ı
TREND_HIST = 120    # rejim eşiği için fark geçmişi penceresi (4H bar)
SWING_K = 2         # fraktal swing kanat genişliği (her iki taraf)
FVG_LOOKBACK = 96   # açık FVG taranan pencere (15M bar)
RECLAIM_MAX = 6     # süpürme sonrası gecikmeli geri alım için azami bar
DISP_MAX = 12       # geri alım sonrası displacement için azami bar
RECENT_N = 24       # sinyalin "güncel" sayıldığı pencere (15M bar = 6 saat)
R_T1_FALLBACK = 1.5 # likidite hedefi yoksa T1 = giriş +/- 1.5R
R_T2_FALLBACK = 2.5 # likidite hedefi yoksa T2 = giriş +/- 2.5R
R_MIN = 1.35        # depo kuralı ("Analiz yapma komutu" 5_RISK): altı = kenar zayıf -> BEKLE
MIN_M15 = N_VOL + 2 * SWING_K + 4
MIN_H4 = MA_SLOW + 5

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
STATE_FILE = os.path.join(STATE_DIR, "durum.json")
LEDGER_FILE = os.path.join(STATE_DIR, "defter.jsonl")


# ---------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------
class Bar:
    __slots__ = ("t", "o", "h", "l", "c", "v")

    def __init__(self, t, o, h, l, c, v):
        self.t, self.o, self.h, self.l, self.c, self.v = t, o, h, l, c, v

    @property
    def body(self):
        return abs(self.c - self.o)

    @property
    def bull(self):
        return self.c > self.o


def _to_ms(x):
    x = float(x)
    # saniye cinsinden gelmişse milisaniyeye çevir (2001'den küçük ms değeri yok)
    return int(x if x > 1e12 else x * 1000)


def parse_klines(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    rows = []
    if text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("data") or data.get("klines") or []
        for row in data:
            if isinstance(row, dict):
                t = row.get("open_time", row.get("openTime", row.get("t", row.get("time"))))
                rows.append((t, row.get("open", row.get("o")), row.get("high", row.get("h")),
                             row.get("low", row.get("l")), row.get("close", row.get("c")),
                             row.get("volume", row.get("v"))))
            else:
                rows.append((row[0], row[1], row[2], row[3], row[4], row[5]))
    else:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p for p in line.replace(",", " ").split() if p]
            if len(parts) < 6:
                continue
            try:
                float(parts[1])
            except ValueError:
                continue  # başlık satırı
            rows.append(tuple(parts[:6]))
    bars = []
    for t, o, h, l, c, v in rows:
        try:
            bars.append(Bar(_to_ms(t), float(o), float(h), float(l), float(c), float(v)))
        except (TypeError, ValueError):
            continue
    bars.sort(key=lambda b: b.t)
    # yinelenen zaman damgalarını at (sonuncusu kalır)
    dedup = {}
    for b in bars:
        dedup[b.t] = b
    return [dedup[t] for t in sorted(dedup)]


def fmt_ts(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Yardımcı istatistik (saf Python; harici bağımlılık yok)
# ---------------------------------------------------------------------------
def quantile(values, q):
    s = sorted(values)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def pct_rank(values, x):
    """x'in values içindeki yüzdelik sırası [0,1]."""
    if not values:
        return 0.0
    return sum(1 for v in values if v <= x) / len(values)


def sma(closes, n, i):
    if i + 1 < n:
        return None
    return sum(closes[i + 1 - n:i + 1]) / n


# ---------------------------------------------------------------------------
# Yapı tespiti
# ---------------------------------------------------------------------------
def find_swings(bars, k=SWING_K):
    """Teyitli fraktal swingler: (index, fiyat, 'H'|'L'). Son k bar teyitsizdir."""
    swings = []
    for i in range(k, len(bars) - k):
        win = bars[i - k:i + k + 1]
        if bars[i].h == max(b.h for b in win) and \
           sum(1 for b in win if b.h == bars[i].h) == 1:
            swings.append((i, bars[i].h, "H"))
        if bars[i].l == min(b.l for b in win) and \
           sum(1 for b in win if b.l == bars[i].l) == 1:
            swings.append((i, bars[i].l, "L"))
    swings.sort(key=lambda s: s[0])
    return swings


def open_fvgs(bars, lookback=FVG_LOOKBACK):
    """Açık (dolmamış) 3-mum FVG listesi. Tanım: smart-money-concepts.md."""
    n = len(bars)
    start = max(2, n - lookback)
    out = []
    for i in range(start, n):
        a, c = bars[i - 2], bars[i]
        if c.l > a.h:  # bullish FVG
            top, bot = c.l, a.h
            filled = any(bars[j].l <= bot for j in range(i + 1, n))
            if not filled:
                out.append({"tip": "bull", "ust": top, "alt": bot,
                            "ce": (top + bot) / 2, "bar": i, "zaman": bars[i - 1].t})
        if c.h < a.l:  # bearish FVG
            top, bot = a.l, c.h
            filled = any(bars[j].h >= top for j in range(i + 1, n))
            if not filled:
                out.append({"tip": "bear", "ust": top, "alt": bot,
                            "ce": (top + bot) / 2, "bar": i, "zaman": bars[i - 1].t})
    return out


def body_threshold(bars, i):
    lo = max(0, i - N_BODY)
    window = [b.body for b in bars[lo:i]]
    return quantile(window, BODY_Q) if window else None


def vol_rank(bars, i):
    lo = max(0, i - N_VOL)
    window = [b.v for b in bars[lo:i]]
    return pct_rank(window, bars[i].v) if window else 0.0


def leaves_fvg(bars, i):
    """i barının displacement'ı bir FVG bıraktı mı (i, orta mum olabilir)?"""
    for mid in (i, i + 1):
        if 1 <= mid < len(bars) - 1:
            a, c = bars[mid - 1], bars[mid + 1]
            if c.l > a.h:
                return {"tip": "bull", "ust": c.l, "alt": a.h, "ce": (c.l + a.h) / 2}
            if c.h < a.l:
                return {"tip": "bear", "ust": a.l, "alt": c.h, "ce": (a.l + c.h) / 2}
    return None


def detect_reversal(bars, swings):
    """
    Dönüş dizisi: süpürme -> geri alım -> ters yön yüksek-hacim displacement -> BOS.
    En güncel ve en ilerlemiş adayı döndürür:
    {yon, adim(0-4), supurme_ucu, fvg, bos_bar, aciklama}
    """
    n = len(bars)
    best = None
    scan_from = max(SWING_K, n - FVG_LOOKBACK)
    for j in range(scan_from, n):
        for (si, price, kind) in swings:
            if si >= j:
                continue
            if j - si > FVG_LOOKBACK:
                continue
            # --- adım 1: süpürme (fitil seviye ötesi)
            if kind == "H" and bars[j].h > price:
                yon, swept = "SHORT", "H"
            elif kind == "L" and bars[j].l < price:
                yon, swept = "LONG", "L"
            else:
                continue
            sweep_ext = bars[j].h if swept == "H" else bars[j].l
            cand = {"yon": yon, "adim": 1, "supurme_ucu": sweep_ext,
                    "supurme_bar": j, "seviye": price, "fvg": None,
                    "bos_bar": None}
            # --- adım 2: geri alım (aynı bar veya <= RECLAIM_MAX bar gecikmeli)
            reclaim = None
            inside = (bars[j].c < price) if swept == "H" else (bars[j].c > price)
            if inside:
                reclaim = j
            else:
                for j2 in range(j + 1, min(n, j + 1 + RECLAIM_MAX)):
                    back = (bars[j2].c < price) if swept == "H" else (bars[j2].c > price)
                    # geri alım beklerken süpürme ucu aşılırsa aday düşer
                    worse = (bars[j2].h > sweep_ext) if swept == "H" else (bars[j2].l < sweep_ext)
                    if worse:
                        break
                    if back:
                        reclaim = j2
                        break
            if reclaim is None:
                best = _better(best, cand, n)
                continue
            cand["adim"] = 2
            cand["geri_alim_bar"] = reclaim
            # --- adım 3: displacement (güçlü gövde + yüksek hacim + FVG bırakır)
            disp = None
            for j3 in range(reclaim, min(n, reclaim + 1 + DISP_MAX)):
                b = bars[j3]
                right_dir = (not b.bull) if yon == "SHORT" else b.bull
                bt = body_threshold(bars, j3)
                if bt is None:
                    continue
                if right_dir and b.body >= bt and vol_rank(bars, j3) >= VOL_RANK_MIN:
                    fvg = leaves_fvg(bars, j3)
                    if fvg and ((yon == "SHORT" and fvg["tip"] == "bear") or
                                (yon == "LONG" and fvg["tip"] == "bull")):
                        disp = (j3, fvg)
                        break
            if disp is None:
                best = _better(best, cand, n)
                continue
            cand["adim"] = 3
            cand["disp_bar"], cand["fvg"] = disp
            # --- adım 4: BOS (gövde kapanışıyla yapı kırılımı)
            target_swings = [s for s in swings
                             if s[0] < disp[0] and s[2] == ("L" if yon == "SHORT" else "H")]
            if target_swings:
                lvl = target_swings[-1][1]
                for j4 in range(disp[0], n):
                    broke = (bars[j4].c < lvl) if yon == "SHORT" else (bars[j4].c > lvl)
                    if broke:
                        cand["adim"] = 4
                        cand["bos_bar"] = j4
                        cand["bos_seviye"] = lvl
                        break
            best = _better(best, cand, n)
    return best


def _better(best, cand, n):
    """Önce daha çok adım, eşitse daha güncel olan kazanır. Güncellik: dizinin
    son olayı RECENT_N penceresi içinde olmalı; değilse aday elenir (adim 4 için)."""
    last_event = cand.get("bos_bar") or cand.get("disp_bar") or \
        cand.get("geri_alim_bar") or cand.get("supurme_bar")
    cand["_son_olay"] = last_event
    if cand["adim"] == 4 and n - 1 - cand["bos_bar"] > RECENT_N:
        return best  # tamamlanmış ama bayat dizi sinyal üretmez
    if best is None:
        return cand
    if cand["adim"] != best["adim"]:
        return cand if cand["adim"] > best["adim"] else best
    return cand if last_event >= best["_son_olay"] else best


def detect_bos_15m(bars, swings):
    """
    Zincir (2): MARKET — fiyat son teyitli swing'i GÖVDEYLE kırar (C0),
    teyit: sonraki 15M bar gövde kapanışı C0 ekstremi ötesinde.
    Son RECENT_N bar içinde arar.
    """
    n = len(bars)
    for i in range(n - 2, max(SWING_K, n - RECENT_N) - 1, -1):
        c0, c1 = bars[i], bars[i + 1]
        highs = [s for s in swings if s[2] == "H" and s[0] < i - SWING_K]
        lows = [s for s in swings if s[2] == "L" and s[0] < i - SWING_K]
        if highs:
            lvl = highs[-1][1]
            if c0.c > lvl and c0.bull and c1.c > c0.h:
                return {"yon": "LONG", "seviye": lvl, "c0": i, "teyit": i + 1}
        if lows:
            lvl = lows[-1][1]
            if c0.c < lvl and not c0.bull and c1.c < c0.l:
                return {"yon": "SHORT", "seviye": lvl, "c0": i, "teyit": i + 1}
    return None


def regime_4h(bars4h):
    closes = [b.c for b in bars4h]
    n = len(closes)
    diffs = []
    for i in range(n):
        f, s = sma(closes, MA_FAST, i), sma(closes, MA_SLOW, i)
        if f is not None and s is not None:
            diffs.append(f - s)
    if not diffs:
        return {"rejim": "VERI_YOK", "fark": None, "esik": None}
    hist = [abs(d) for d in diffs[-TREND_HIST:]]
    thr = quantile(hist, TREND_Q)
    cur = diffs[-1]
    if cur > thr:
        rejim = "UP"
    elif cur < -thr:
        rejim = "DOWN"
    else:
        rejim = "FLAT"
    return {"rejim": rejim, "fark": cur, "esik": thr}


# ---------------------------------------------------------------------------
# Önceki kararın akıbeti (hafıza: etkileme değil, hesap verme)
# ---------------------------------------------------------------------------
def label_outcome(prev, bars):
    """Önceki karardan SONRAKİ 15M barların fiyat yoluyla akıbet etiketi."""
    if prev is None:
        return "İLK KOŞU — kıyas yok."
    k = prev.get("karar", {})
    if k.get("karar") == "BEKLE":
        return "Önceki karar BEKLE idi (%s) — pozisyon yok." % fmt_ts(prev["son_bar"])
    yon = k["yon"]
    lo, hi = k["giris_alt"], k["giris_ust"]
    stop, t1, t2, iptal = k["stop"], k["t1"], k["t2"], k["iptal"]
    after = [b for b in bars if b.t > prev["son_bar"]]
    if not after:
        return "Önceki %s kararından sonra yeni bar yok — akıbet ölçülemez (VERİ YOK)." % yon
    # MARKET girişi (bölge tek nokta) ANINDA dolar — iptal-öncesi-dokunuş beklemez.
    # LIMIT girişi (bölge) bölgeye dokununca dolar; dokunmadan iptal olursa İPTAL.
    market = abs(hi - lo) < 1e-6
    triggered = market
    t1_hit = False
    for b in after:
        if not triggered:
            # LIMIT: giriş tetiklenmeden iptal (gövde kapanışı iptal seviyesi ötesinde)
            if (yon == "LONG" and b.c < iptal) or (yon == "SHORT" and b.c > iptal):
                return ("Önceki %s: giriş TETİKLENMEDEN İPTAL (gövde kapanış %.6g, "
                        "iptal %.6g, %s)." % (yon, b.c, iptal, fmt_ts(b.t)))
            if b.l <= hi and b.h >= lo:
                triggered = True
                # aynı barda stop kontrolü aşağıda devam eder
        if triggered:
            stop_hit = b.l <= stop if yon == "LONG" else b.h >= stop
            t1_now = b.h >= t1 if yon == "LONG" else b.l <= t1
            t2_now = b.h >= t2 if yon == "LONG" else b.l <= t2
            if stop_hit and t1_now and not t1_hit:
                return ("Önceki %s: giriş tetiklendi; aynı barda hem stop hem T1 "
                        "menzilde (%s) — akıbet BELİRSİZ, defterde 'belirsiz' yazıldı."
                        % (yon, fmt_ts(b.t)))
            if stop_hit and not t1_hit:
                return "Önceki %s: giriş tetiklendi, STOP oldu (%s)." % (yon, fmt_ts(b.t))
            if t2_now:
                return "Önceki %s: giriş tetiklendi, T1 ve T2 GELDİ (%s)." % (yon, fmt_ts(b.t))
            if t1_now:
                t1_hit = True
            # MARKET girişte invalidation POST-FILL exit gibi çalışır (yumuşak-stop):
            # pozisyon açık, gövde iptal seviyesinin gerisine kapanırsa çıkılır.
            if market and not t1_hit and (
                    (yon == "LONG" and b.c < iptal) or (yon == "SHORT" and b.c > iptal)):
                r = ((b.c - lo) / abs(lo - stop)) if yon == "LONG" else ((lo - b.c) / abs(lo - stop))
                return ("Önceki %s: MARKET giriş doldu, gövde iptal (%.6g) gerisine "
                        "kapandı → INVALIDATION-EXIT %.6g (%s), gerçek R≈%.2f."
                        % (yon, iptal, b.c, fmt_ts(b.t), r))
    if triggered:
        return ("Önceki %s: giriş tetiklendi, %s — pozisyon AÇIK görünümde "
                "(son bar %s)." % (yon, "T1 geldi, T2 bekliyor" if t1_hit else
                                   "stop/hedef henüz yok", fmt_ts(after[-1].t)))
    return "Önceki %s: giriş HENÜZ TETİKLENMEDİ (bölge bekliyor)." % yon


def outcome_code(text):
    for code in ("İPTAL", "STOP", "T1 ve T2", "BELİRSİZ", "TETİKLENMEDİ", "AÇIK"):
        if code in text:
            return code
    return "DİĞER"


# ---------------------------------------------------------------------------
# Karar zinciri
# ---------------------------------------------------------------------------
def _targets(yon, entry, stop, swings, bars):
    """T1/T2 = yön tarafındaki likidite (teyitli swingler); yoksa R katı."""
    risk = abs(entry - stop)
    if yon == "LONG":
        lvls = sorted({s[1] for s in swings if s[2] == "H" and s[1] > entry + risk * 0.5})
    else:
        lvls = sorted({s[1] for s in swings if s[2] == "L" and s[1] < entry - risk * 0.5},
                      reverse=True)
    t1 = lvls[0] if len(lvls) >= 1 else (entry + risk * R_T1_FALLBACK if yon == "LONG"
                                         else entry - risk * R_T1_FALLBACK)
    t2 = lvls[1] if len(lvls) >= 2 else (entry + risk * R_T2_FALLBACK if yon == "LONG"
                                         else entry - risk * R_T2_FALLBACK)
    return t1, t2, ("likidite" if lvls else "R-katı (likidite hedefi yok)")


def decide(bars15, bars4h):
    swings15 = find_swings(bars15)
    swings4h = find_swings(bars4h)
    fvgs = open_fvgs(bars15)
    rej = regime_4h(bars4h)
    rev = detect_reversal(bars15, swings15)
    bos = detect_bos_15m(bars15, swings15)
    last = bars15[-1]

    karar = None

    # (1) tamamlanmış dönüş dizisi
    if rev and rev["adim"] == 4:
        yon = rev["yon"]
        fvg = rev["fvg"]
        entry = fvg["ce"]
        stop = rev["supurme_ucu"]
        iptal = fvg["alt"] if yon == "LONG" else fvg["ust"]
        t1, t2, tk = _targets(yon, entry, stop, swings15, bars15)
        karar = {
            "karar": yon, "yon": yon, "zincir": 1,
            "neden": ("Dönüş dizisi 4/4 tamam: %.6g seviyesi süpürüldü, geri alındı, "
                      "yüksek-hacim displacement FVG bıraktı, BOS %.6g gövdeyle kırıldı."
                      % (rev["seviye"], rev.get("bos_seviye", 0))),
            "giris_alt": min(fvg["alt"], fvg["ust"]), "giris_ust": max(fvg["alt"], fvg["ust"]),
            "giris": entry, "stop": stop, "iptal": iptal, "t1": t1, "t2": t2,
            "iptal_kural": ("Giriş tetiklenmeden 15M gövde kapanışı %.6g ötesine geçerse "
                            "bölge geçersiz." % iptal),
            "hedef_kaynak": tk,
        }
    # (2) 15M yapı kırılımı + teyit, 4H karşı değilse
    elif bos and not ((bos["yon"] == "LONG" and rej["rejim"] == "DOWN") or
                      (bos["yon"] == "SHORT" and rej["rejim"] == "UP")):
        yon = bos["yon"]
        c0 = bars15[bos["c0"]]
        entry = bars15[bos["teyit"]].c if bos["teyit"] == len(bars15) - 1 else last.c
        stop = min(c0.l, bars15[bos["teyit"]].l) if yon == "LONG" else \
            max(c0.h, bars15[bos["teyit"]].h)
        iptal = bos["seviye"]
        t1, t2, tk = _targets(yon, entry, stop, swings15, bars15)
        karar = {
            "karar": yon, "yon": yon, "zincir": 2,
            "neden": ("MARKET: son teyitli swing %.6g gövdeyle kırıldı, sonraki bar "
                      "C0 ekstremi ötesinde kapandı; 4H rejim (%s) karşı değil."
                      % (bos["seviye"], rej["rejim"])),
            "giris_alt": entry, "giris_ust": entry, "giris": entry,
            "stop": stop, "iptal": iptal, "t1": t1, "t2": t2,
            "iptal_kural": ("15M gövde kapanışı kırılan %.6g seviyesinin gerisine dönerse "
                            "sinyal geçersiz." % iptal),
            "hedef_kaynak": tk,
        }
    # (3) 4H rejimi + hizalı açık FVG (PUSU)
    elif rej["rejim"] in ("UP", "DOWN"):
        yon = "LONG" if rej["rejim"] == "UP" else "SHORT"
        aligned = [f for f in fvgs
                   if (yon == "LONG" and f["tip"] == "bull" and f["ust"] < last.c) or
                      (yon == "SHORT" and f["tip"] == "bear" and f["alt"] > last.c)]
        if aligned:
            f = aligned[-1]  # fiyata en yakın / en güncel bölge
            entry = f["ce"]
            below = [s[1] for s in swings15 if s[2] == "L" and s[1] < min(f["alt"], f["ust"])]
            above = [s[1] for s in swings15 if s[2] == "H" and s[1] > max(f["alt"], f["ust"])]
            stop = (max(below) if below else f["alt"]) if yon == "LONG" else \
                   (min(above) if above else f["ust"])
            iptal = f["alt"] if yon == "LONG" else f["ust"]
            t1, t2, tk = _targets(yon, entry, stop, swings15, bars15)
            karar = {
                "karar": yon, "yon": yon, "zincir": 3,
                "neden": ("PUSU: 4H rejim %s (MA5-MA20=%.6g, eşik q%d=%.6g); fiyat "
                          "hizasında açık %s FVG bölgesi var."
                          % (rej["rejim"], rej["fark"], int(TREND_Q * 100), rej["esik"],
                             f["tip"])),
                "giris_alt": min(f["alt"], f["ust"]), "giris_ust": max(f["alt"], f["ust"]),
                "giris": entry, "stop": stop, "iptal": iptal, "t1": t1, "t2": t2,
                "iptal_kural": ("Giriş tetiklenmeden 15M gövde kapanışı %.6g ötesine "
                                "geçerse (FVG dolup taşarsa) bölge geçersiz." % iptal),
                "hedef_kaynak": tk,
            }
        else:
            karar = {"karar": "BEKLE", "yon": None, "zincir": 4,
                     "neden": ("BEKLE: 4H rejim %s ama fiyat hizasında açık FVG (pusu "
                               "bölgesi) yok; dönüş dizisi ve teyitli 15M kırılımı da yok."
                               % rej["rejim"])}
    else:
        karar = {"karar": "BEKLE", "yon": None, "zincir": 4,
                 "neden": ("BEKLE: dönüş dizisi tamamlanmadı, teyitli 15M kırılımı yok, "
                           "4H rejim %s (|MA5-MA20| eşik altında)." % rej["rejim"])}

    if karar["karar"] != "BEKLE":
        risk = abs(karar["giris"] - karar["stop"])
        karar["r"] = round(abs(karar["t1"] - karar["giris"]) / risk, 2) if risk > 0 else None
        # Depo kuralı (Analiz yapma komutu, 5_RISK): R/R < 1.35 => kenar zayıf
        if karar["r"] is None or karar["r"] < R_MIN:
            karar = {"karar": "BEKLE", "yon": None, "zincir": karar["zincir"],
                     "neden": ("BEKLE: %s sinyali var (zincir %d) ama kenar zayıf — "
                               "R=%s < %.2f (depo risk kuralı); T1 likiditesi stopa "
                               "göre çok yakın." %
                               (karar["yon"], karar["zincir"],
                                karar["r"] if karar["r"] is not None else "hesapsız",
                                R_MIN))}
    return karar, {"swings15": swings15, "swings4h": swings4h, "fvgs": fvgs,
                   "rejim": rej, "rev": rev, "bos": bos}


# ---------------------------------------------------------------------------
# Durum / defter
# ---------------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def append_ledger(entry):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Çıktı
# ---------------------------------------------------------------------------
def fnum(x):
    return "%.6g" % x if x is not None else "VERİ YOK"


def render(karar, ctx, akibet, bars15, bars4h, esikler):
    L = []
    L.append("=" * 64)
    L.append("KARAR MOTORU v1 — koşu: son 15M bar %s UTC" % fmt_ts(bars15[-1].t))
    L.append("Veri: 15M %d bar (%s→%s), 4H %d bar (%s→%s)" %
             (len(bars15), fmt_ts(bars15[0].t), fmt_ts(bars15[-1].t),
              len(bars4h), fmt_ts(bars4h[0].t), fmt_ts(bars4h[-1].t)))
    L.append("-" * 64)
    L.append("ÖNCEKİ KARAR AKIBETİ: %s" % akibet)
    L.append("-" * 64)
    L.append("SABİTLER (yapısal, beyan): N_VOL=%d VOL_RANK_MIN=%.2f N_BODY=%d "
             "BODY_Q=%.2f MA=%d/%d TREND_Q=%.2f SWING_K=%d RECENT_N=%d "
             "R_fallback=%.1f/%.1f R_MIN=%.2f" %
             (N_VOL, VOL_RANK_MIN, N_BODY, BODY_Q, MA_FAST, MA_SLOW, TREND_Q,
              SWING_K, RECENT_N, R_T1_FALLBACK, R_T2_FALLBACK, R_MIN))
    L.append("BU KOŞUNUN EŞİKLERİ (veriden hesaplandı): gövde q%d=%s | son bar "
             "hacim sırası=%s | 4H |MA5-MA20| eşiği=%s (fark=%s, rejim=%s)" %
             (int(BODY_Q * 100), fnum(esikler["govde_q"]), fnum(esikler["hacim_sira"]),
              fnum(ctx["rejim"]["esik"]), fnum(ctx["rejim"]["fark"]),
              ctx["rejim"]["rejim"]))
    L.append("-" * 64)
    L.append("KARAR : %s%s" % (karar["karar"],
                               "" if karar["karar"] == "BEKLE"
                               else "  (zincir adımı %d)" % karar["zincir"]))
    L.append("NEDEN : %s" % karar["neden"])
    if karar["karar"] != "BEKLE":
        if karar["giris_alt"] == karar["giris_ust"]:
            L.append("GİRİŞ : %s (market)" % fnum(karar["giris"]))
        else:
            L.append("GİRİŞ : %s – %s bölgesi (CE %s)" %
                     (fnum(karar["giris_alt"]), fnum(karar["giris_ust"]),
                      fnum(karar["giris"])))
        L.append("STOP  : %s" % fnum(karar["stop"]))
        L.append("İPTAL : %s" % karar["iptal_kural"])
        L.append("T1    : %s | T2: %s (kaynak: %s)" %
                 (fnum(karar["t1"]), fnum(karar["t2"]), karar["hedef_kaynak"]))
        L.append("R     : %s (T1'e; giriş-stop mesafesine göre)" %
                 (karar["r"] if karar["r"] is not None else "VERİ YOK"))
    rev = ctx["rev"]
    if rev and 2 <= rev["adim"] < 4:
        L.append("-" * 64)
        L.append("UYARI : dönüş dizisi %d/4 (%s yönünde) — süpürülen seviye %s, "
                 "süpürme ucu %s. Dizi tamamlanırsa yön değişebilir." %
                 (rev["adim"], rev["yon"], fnum(rev["seviye"]),
                  fnum(rev["supurme_ucu"])))
    L.append("=" * 64)
    return "\n".join(L)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Karar Motoru v1")
    ap.add_argument("--m15", required=True, help="15M kline dosyası")
    ap.add_argument("--h4", required=True, help="4H kline dosyası")
    ap.add_argument("--state-dir", default=None, help="durum/defter dizini (varsayılan engine/state)")
    args = ap.parse_args(argv)

    global STATE_DIR, STATE_FILE, LEDGER_FILE
    if args.state_dir:
        STATE_DIR = args.state_dir
        STATE_FILE = os.path.join(STATE_DIR, "durum.json")
        LEDGER_FILE = os.path.join(STATE_DIR, "defter.jsonl")

    bars15 = parse_klines(args.m15)
    bars4h = parse_klines(args.h4)
    if len(bars15) < MIN_M15 or len(bars4h) < MIN_H4:
        print("VERİ YOK / YETERSİZ: 15M=%d bar (gerek %d), 4H=%d bar (gerek %d). "
              "KARAR: BEKLE — NEDEN: eşikler kendi dağılımından hesaplanamaz, "
              "uydurma eşikle karar üretilmez." %
              (len(bars15), MIN_M15, len(bars4h), MIN_H4))
        return 1

    prev = load_state()
    # Takip edilen pozisyon: son BEKLE-olmayan karar, sonuçlanana kadar izlenir.
    takip = prev.get("takip") if prev else None
    if takip is None and prev is not None:
        akibet = ("Takip edilen açık karar yok — önceki koşunun kararı %s idi (%s)."
                  % (prev.get("karar", {}).get("karar", "?"),
                     prev.get("son_bar_utc", "?")))
    else:
        akibet = label_outcome(takip, bars15)
    TERMINAL = ("İPTAL", "STOP", "T1 ve T2", "BELİRSİZ")
    if takip is not None and outcome_code(akibet) in TERMINAL:
        append_ledger({"karar_zamani": takip["son_bar"],
                       "etiket_zamani": bars15[-1].t,
                       "karar": takip["karar"], "sonuc": outcome_code(akibet)})
        takip = None

    karar, ctx = decide(bars15, bars4h)

    if karar["karar"] != "BEKLE":
        if takip is not None:
            # açık karar sonuç ölçülemeden yeni kararla değiştirildi — deftere yaz
            append_ledger({"karar_zamani": takip["son_bar"],
                           "etiket_zamani": bars15[-1].t,
                           "karar": takip["karar"], "sonuc": "DEVRİLDİ",
                           "not": "yeni karar geldi, önceki sonuç ölçülmeden kapandı"})
        takip = {"son_bar": bars15[-1].t, "karar": karar}

    esikler = {"govde_q": body_threshold(bars15, len(bars15) - 1),
               "hacim_sira": vol_rank(bars15, len(bars15) - 1)}
    out = render(karar, ctx, akibet, bars15, bars4h, esikler)
    print(out)

    state = {
        "son_bar": bars15[-1].t,
        "son_bar_utc": fmt_ts(bars15[-1].t),
        "karar": karar,
        "takip": takip,
        "akibet_onceki": akibet,
        "acik_bolgeler": ctx["fvgs"],
        "swing_15m_son": [(s[1], s[2]) for s in ctx["swings15"][-8:]],
        "swing_4h_son": [(s[1], s[2]) for s in ctx["swings4h"][-6:]],
        "rejim_4h": ctx["rejim"],
        "donus_dizisi": ({"yon": ctx["rev"]["yon"], "adim": ctx["rev"]["adim"],
                          "supurme_ucu": ctx["rev"]["supurme_ucu"]}
                         if ctx["rev"] else None),
    }
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
