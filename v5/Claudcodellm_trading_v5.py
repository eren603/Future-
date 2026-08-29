# -*- coding: utf-8 -*-
"""
Claudcodellm_trading_v5.py — v4 (DOKUNULMAMIS) + FADE bahis sinifi (I17)
=======================================================================
v5, v4'U DEGISTIRMEZ: v4 kaynagi oldugu gibi yuklenir; I13 manşet kurali
(hukum satiri) dosyada yoksa E23'te 4/4 testle dogrulanmis kaynak
donusumuyle BELLEK ICINDE uygulanir. Diskteki v4 dosyasina DOKUNULMAZ.

Iki BAGIMSIZ bahis sinifi:
  ANA SINIF (v4) : 15M+4H kanallarindan p/f* uretir; YON her zaman verilir.
  FADE SINIF (v5): 2H kapanislarinda +-E_K xATR'a cift LIMIT koyar; ilk
                   dolan kenar yonu belirler (alt=>LONG, ust=>SHORT);
                   hedef T_K xATR donus, stop S_K xATR; R = T_K/S_K.
                   GECMIS (yalnizca COZULMUS) yarislardan p_hat/edge_hat
                   OLculur; fail-closed stake kapisi: n < MIN_N veya
                   edge_hat <= 0 ise HUKUM_FADE = BAHIS YOK, stake = 0.

THRESHOLD BEYANLARI (KONSEY v9.0 — hepsi v4 esik defterine de yazilir):
  E_K=2.0        OLCULEN  E25/E26: OOS-pozitif bolge [1.5,2.0], en iyi toplam.
  T_K=1.5        OLCULEN  E25: 5/5 sembolde en iyi/tutarli hedef.
  S_K=1.0        OLCULEN  E26: +80.5R [27.8,133.1]. Alternatif S_K=2.0.
  MIN_N=30       YAPISAL  KL Ttemeli; n<30'da kapi KAPALI (fail-closed).
  KELLY_CAP=0.25 VARSAYIM sermaye-riski ust siniri (muhafazakarlik).
  K_STALE=60     YAPISAL  60x2H=5gun dolmayan limit bayatir: emir iptal.
  K_COZUM=120    YAPISAL  Sonlanma garantisi: asilirsa kapanis fiyatiyla
                          pozisyon kapatilir (taker+kayma).
  MAKER/TAKER    OLCULEN  S16: OKX USDT-vadeli Lv1 (%0.02/%0.05).
  KAYMA=0.0002   VARSAYIM E22'den tasinan sabit kayma.
  FUNDING        OLCULEN  S14: sembol bazli son-100 donem |oran| ortalamasi;
                          yon-bagimsiz MALIYET olarak uygulanir (muhafazakar).
  H2_HEDEF=4040  OLCULEN  E25 penceresiyle ayni ~11 ay 2H gecmis.
  CACHE_BAYATLIK VARSAYIM 2H onbellek tazeligi 1 gun.

MEKANIK SOZLESME (v4'ten aynen):
  - HOLD/ABSTAIN/"Notr 0.0" YASAK; ana YON satiri v4'ten her zaman gelir.
  - FADE kapisinin kapalisi BAHIS SINIFI kapisidir (yone HOLD degil): ana
    blok etkilenmez. f*=0'da ana manşet I13 geregi "HUKUM: BAHIS YOK".
  - Guven olculur secilmez; fail-closed: edge_hat<=0 -> stake TAM 0.0.
  - R = hedef_mesafesi/stop_mesafesi (v4 seviyeler() ile ayni, T9 testi).
  - BAK-ILERI YASAK: fade_karar yalnizca barlar[:simdi+1] okur (T2 zehir
    testi: gelecek barlar x10/x0.1 ile zehirlenir, karar DEGISMEZ).

OKX UYUM KATMANI (v5, v4 KAYNAGINA DOKUNMAZ — getir katmaninda):
  v4'un OKX canli yolu kirikti: OkxAdaptor sayfalanir bayragi tasimadigi
  icin ham {"code","data"} sozlugunu kanal olarak depoluyordu ve OKX mum
  satirlari Binance 12-alan biciminden farkliydi (taker_alis kolonu YOK).
  v5 cevirileri: (a) yanit acimi code/data; (b) mum -> history-candles
  (yalnizca KAPALI mumlar; yarim mum C29 riski kapanir) + 12-alanli
  Binance satiri; (c) taker_alis = hacim/2 NOTR dolgu -> CVD delta=0
  -> z=0: yon bilgisi TASIMAZ, uydurma YOK (gercek buyVol taker-volume
  kanalindan ayri olarak zaten modelde); (d) rubik oi/taker satirlari
  Binance sozluk bicimine cevrilir; (e) endTime(Binance)->after(OKX); (f) OKX 100-bar sayfalari IC
  sayfalama ile AZAMI_BAR_BUTCESI bar butcesine tamamlanir (v4'un
  8-sayfa siniri Binance 1500-bar sayfasina gore ayarliydi; OKX
  100-bar sayfasinda ayni bar butcesi ~40 sayfa ister).

GUVENLIK: Yalnizca KARAR DESTEgi. Emir/iptal ucu, API anahtari, imza YOK
(v4 http_getir uzerinden public GET disinda ag KULLANILMAZ).
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time

V4_ADI = "Claudcodellm_trading_v4.py"
H2_ADIM_MS = 7200000

E_K = 2.0
T_K = 1.5
S_K = 1.0
R_FADE = T_K / S_K
MIN_N = 30
KELLY_CAP = 0.25
K_STALE = 60
K_COZUM = 120
ATR_PERIYOT = 14
H2_HEDEF = 4040
MAKER = 0.0002
TAKER = 0.0005
KAYMA = 0.0002
FUNDING_PENCERE = 100
FUNDING_YEDEK = {"BTC": 5.9e-5, "ETH": 4.6e-5, "SOL": 4.4e-5,
                 "XRP": 4.1e-5, "DOGE": 6.6e-5}
CACHE_BAYATLIK_S = 86400

SEMBOL_H2 = {"BTCUSDT": "BTC-USDT-SWAP", "ETHUSDT": "ETH-USDT-SWAP",
             "SOLUSDT": "SOL-USDT-SWAP", "XRPUSDT": "XRP-USDT-SWAP",
             "DOGEUSDT": "DOGE-USDT-SWAP"}

YASAKLI = ("HOLD", "ABSTAIN", "Notr 0.0", "NOTR 0.0")

_I13_ESKI = (
    '        "YON        : %s  (kaynak=%s, p_ham=%s) - yon KOSULSUZ verilir"\n'
    '        % (karar["yon"], karar.get("yon_kaynagi"), _bicim(karar.get("p_ham"))),\n'
)
_I13_YENI = (
    '        "HUKUM      : %s" % ("BAHIS ACILIR - f*=%s" % _bicim(s.get("f"), ".6f")\n'
    '                    if acilir else\n'
    '                    "BAHIS YOK - f*=0 (gurultu bandi); asagidaki yon BILGIDIR,"\n'
    '                    " islem sinyali DEGILDIR"),\n'
    '        "YON        : %s  (kaynak=%s, p_ham=%s)%s"\n'
    '        % (karar["yon"], karar.get("yon_kaynagi"), _bicim(karar.get("p_ham")),\n'
    '           " - yon KOSULSUZ verilir" if acilir\n'
    '           else " - BILGI SATIRI: f*=0, islem ACMA"),\n'
)


def _i13_uygula(kaynak):
    if "HUKUM      :" in kaynak:
        return kaynak, "zaten-uygulanmis"
    if _I13_ESKI not in kaynak:
        raise RuntimeError("I13: eski blok bulunamadi - v4 kaynagi farkli")
    return kaynak.replace(_I13_ESKI, _I13_YENI), "bellek-icinde-uygulandi"


def _v4_yukle():
    kok = os.path.dirname(os.path.abspath(__file__))
    for yol in [os.path.join(kok, V4_ADI), V4_ADI,
                os.path.join("Uploads", V4_ADI)]:
        if os.path.exists(yol):
            kaynak, i13 = _i13_uygula(open(yol, encoding="utf-8").read())
            spec = importlib.util.spec_from_file_location("tv4_v5", yol)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["tv4_v5"] = mod
            mod.__dict__["__name__"] = "tv4_v5"
            exec(compile(kaynak, yol, "exec"), mod.__dict__)
            return mod, i13
    raise FileNotFoundError(V4_ADI + " bulunamadi (v5 ile ayni dizine koyun)")


TV4, I13_DURUM = _v4_yukle()

for _ad, _dg, _ky, _gk, _oy in [
        ("V5_E_KATSAYI", E_K, "OLCULEN",
         "E25/E26: OOS-pozitif bolge [1.5,2.0]; en iyi toplam e=2.0",
         "grid IS/OOS + stride-34 bagimsiz sinyal bootstrap"),
        ("V5_T_KATSAYI", T_K, "OLCULEN",
         "E25: 5/5 sembolde en iyi/tutarli hedef katsayisi",
         "ayni grid taramasi"),
        ("V5_S_KATSAYI", S_K, "OLCULEN",
         "E26: F2(2,1,1.5) +80.5R [27.8,133.1]", "ayni grid taramasi"),
        ("V5_MIN_N", MIN_N, "YAPISAL",
         "KL Ttemeli; daha az orneklemde edge_hat guvenilmez, kapi kapali",
         "bagimsiz yarisma sayisinin bootstrap SE'si"),
        ("V5_KELLY_CAP", KELLY_CAP, "VARSAYIM",
         "sermaye-riski ust siniri; edge_hat/b_win burada kirpilir",
         "gercek dolmam/Itare maliyetleriyle yeniden olculmeli"),
        ("V5_K_STALE_BAR", K_STALE, "YAPISAL",
         "60x2H=5gun dolmayan limit bayatir; emir iptal edilir",
         "dolma suresi dagilimindan (E29 defter akisi) turetilebilir"),
        ("V5_K_COZUM_BAR", K_COZUM, "YAPISAL",
         "sonlanma garantisi; asilirsa pozisyon kapanisla kapatilir",
         "yarisma suresi dagiliminin kuyrugu"),
        ("V5_MAKER", MAKER, "OLCULEN", "S16 OKX USDT-vadeli Lv1", "-"),
        ("V5_TAKER", TAKER, "OLCULEN", "S16 OKX USDT-vadeli Lv1", "-"),
        ("V5_KAYMA", KAYMA, "VARSAYIM", "E22'den tasinan sabit kayma",
         "gercek islem kayitlarindan olculmeli"),
        ("V5_OKX_CVD_NOTR_DOLGU", 0.5, "VARSAYIM",
         "OKX mumlarinda taker-alis kolonu yok; hacim/2 notr dolgu CVD'yi"
         " 0'a ceker (z=0, yon tasimaz)",
         "OKX taker-volume buyVol ile zaman-bazli birlestirilebilir (v5.1)"),
        ("V5_OKX_GECMIS_BAR", 4000, "OLCULEN",
         "history-candles sayfalama derinligi (AZAMI_BAR_BUTCESI ile ayni)",
         "sayfa sayisi x 100")]:
    try:
        TV4.esik_kaydet(_ad, _dg, _ky, _gk, _oy)
    except Exception:
        pass


# ------------------------------------------------- OKX UYUM KATMANI
class _OkxUyumluAdaptor(TV4.OkxAdaptor):
    """OkxAdaptor + sayfalanir. v4'un OKX yolu kirikti (ham yanit sozlugu
    depolaniyordu). v4 KAYNAGI degismez; calisma zamaninda enjekte edilir."""
    sayfalanir = True
    ad = "okx-v5"


TV4.OkxAdaptor = _OkxUyumluAdaptor


def _okx_sekillendir(url, istek, r):
    """OKX ham yanitini v4'un Binance bicimlerine cevirir."""
    if r is None:
        return r
    if "/market/candles" in url or "/market/history-candles" in url:
        adim = 14400000 if str(istek.get("bar", "")).upper().startswith("4H") else 900000
        out = []
        for x in r:
            try:
                ts, o, h, l, c, v = int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])
            except (TypeError, ValueError, IndexError):
                continue
            try:
                qv = float(x[7])
            except (TypeError, ValueError, IndexError):
                qv = v * c
            out.append([ts, o, h, l, c, v, ts + adim - 1, qv, 0, v / 2.0, 0, 0])
        return out
    if "open-interest-history" in url:
        out = []
        for x in r:
            try:
                out.append({"timestamp": int(x[0]), "sumOpenInterest": float(x[1]),
                            "sumOpenInterestValue": float(x[3])})
            except (TypeError, ValueError, IndexError):
                continue
        return out
    if "taker-volume" in url:
        out = []
        for x in r:
            try:
                ts, sell, buy = int(x[0]), float(x[1]), float(x[2])
                oran = float(x[3]) if len(x) > 3 else (buy / sell if sell else 0.0)
            except (TypeError, ValueError, IndexError, ZeroDivisionError):
                continue
            out.append({"timestamp": ts, "sellVol": sell, "buyVol": buy,
                        "buySellRatio": oran})
        return out
    return r


def okx_uyumlu_getir(url, params, zaman_asimi=20, cek=None):
    """v5 OKX uyumlu getir_fn (v4 http_getir sarmasi; public GET ONLY).
    - Binance ucuna istek -> aninda hata (OKX odakli mod; hizli adaptor dususu).
    - endTime -> after cevirisi; /market/candles -> history-candles (kapali mum).
    - 4H mumleri tek cagri icinde sayfalanir (~1200 bar).
    - code != '0' -> hata (kanal None duser, uydurma YOK)."""
    cek = TV4.http_getir if cek is None else cek
    if "binance.com" in url:
        raise RuntimeError("v5 OKX odakli mod: Binance ucuna istek yapilmaz")
    istek = dict(params or {})
    if "endTime" in istek:
        istek["after"] = istek.pop("endTime")
    mum_mu = "/market/candles" in url
    if mum_mu:
        url = url.replace("/market/candles", "/market/history-candles")
        istek["limit"] = "100"
    r = cek(url, istek, zaman_asimi)
    if isinstance(r, dict) and "code" in r:
        if str(r.get("code")) != "0":
            raise RuntimeError("OKX code=%s msg=%s"
                               % (r.get("code"), str(r.get("msg"))[:60]))
        r = r.get("data")
    if mum_mu and "after" not in istek and r:
        hedef_i = 1200 if str(istek.get("bar", "")) == "4H" else int(TV4.AZAMI_BAR_BUTCESI)
        gorulen = {x[0] for x in r}
        after = r[-1][0]
        for _ in range(80):
            if len(r) >= hedef_i or not after:
                break
            j = cek(url, dict(istek, after=after), zaman_asimi)
            if isinstance(j, dict):
                j = j.get("data") or []
            yeni = [x for x in j if x[0] not in gorulen]
            if not yeni:
                break
            r = r + yeni
            gorulen |= {x[0] for x in yeni}
            after = yeni[-1][0]
    return _okx_sekillendir(url, istek, r)


# ---------------------------------------------------------------- KAPI
def _kapi(n, kazan, sum_r, sum_kaz_r):
    """Fail-closed stake kapisi. Girdiler YALNIZCA cozulmus yarismalardan."""
    out = {"acik": False, "n": n, "p_hat": None, "edge_hat": None,
           "b_win": None, "stake": 0.0, "not": ""}
    if n == 0:
        out["not"] = "olcum yok (n=0) - kapi KAPALI (fail-closed)"
        return out
    p = kazan / n
    edge = sum_r / n
    b = (sum_kaz_r / kazan) if kazan else R_FADE
    out.update({"p_hat": p, "edge_hat": edge, "b_win": b})
    if n < MIN_N:
        out["not"] = ("n=%d < MIN_N=%d (istatistik taban) - kapi KAPALI"
                      % (n, MIN_N))
        return out
    if edge <= 0.0:
        out["not"] = ("edge_hat=%+.4fR <= 0 - kapi KAPALI (fail-closed, olculdu)"
                      % edge)
        return out
    out["acik"] = True
    out["stake"] = min(edge / max(b, 1e-12), KELLY_CAP)
    out["not"] = ("edge_hat=%+.4fR (n=%d, p_hat=%.3f) - kapi ACIK"
                  % (edge, n, p))
    return out


# ------------------------------------------------------------- MOTOR
def _yaris_coz(barlar, i, atr, e=E_K, t=T_K, s=S_K, fund_8h=6e-5):
    """i kapanisinda kurulan cift-limit FADE yarisini i+1'den itibaren cozer.
    Donus: yarisma sozlugu veya None (belirsiz bar / dolmadi / veri bitti).
    Konvansiyonlar (beyan): ayni barda iki kenara da degerse sinyal IPTAL;
    giris barda ve sonrasinda hedef+stop ayni barda degerse STOP (konservatif);
    giris+kapis maker, stop ve zaman kapanisi taker+kayma; funding yon-bagimsiz
    maliyet. R birimi = stop mesafesi (s*atr)."""
    n = len(barlar)
    if i + 1 >= n or not atr or atr <= 0:
        return None
    c = barlar[i]["c"]
    alt, ust = c - e * atr, c + e * atr
    yon = giris = None
    giris_idx = -1
    j = i + 1
    while j < n:
        h, l = barlar[j]["h"], barlar[j]["l"]
        if yon is None:
            if j > i + K_STALE:
                return None
            alt_d, ust_d = l <= alt, h >= ust
            if alt_d and ust_d:
                return None
            if alt_d:
                yon, giris, giris_idx = "LONG", alt, j
            elif ust_d:
                yon, giris, giris_idx = "SHORT", ust, j
            else:
                j += 1
                continue
        hedef = giris + t * atr if yon == "LONG" else giris - t * atr
        stop = giris - s * atr if yon == "LONG" else giris + s * atr
        hd = h >= hedef if yon == "LONG" else l <= hedef
        sd = l <= stop if yon == "LONG" else h >= stop
        if sd or hd:
            fr = fund_8h * (j - giris_idx) / 4.0 * giris
            if sd:
                pnl = -s * atr
                ucret = MAKER * giris + (TAKER + KAYMA) * giris
                sonuc = "STOP"
            else:
                pnl = t * atr
                ucret = MAKER * giris + MAKER * abs(hedef)
                sonuc = "HEDEF"
            return {"sinyal": i, "giris_idx": giris_idx, "cozum": j,
                    "yon": yon, "giris": giris, "hedef": hedef, "stop": stop,
                    "sonuc": sonuc, "net_r": (pnl - ucret - fr) / (s * atr),
                    "atr": atr}
        if j >= giris_idx + K_COZUM:
            cp = barlar[j]["c"]
            pnl = (cp - giris) if yon == "LONG" else (giris - cp)
            ucret = MAKER * giris + (TAKER + KAYMA) * cp
            fr = fund_8h * (j - giris_idx) / 4.0 * giris
            return {"sinyal": i, "giris_idx": giris_idx, "cozum": j,
                    "yon": yon, "giris": giris, "hedef": hedef, "stop": stop,
                    "sonuc": "ZAMAN", "net_r": (pnl - ucret - fr) / (s * atr),
                    "atr": atr}
        j += 1
    return None


def fade_akisi(barlar, fund_8h, e=E_K, t=T_K, s=S_K):
    """Kronolojik olcum akisi (flat iken her kapanis sinyal kurar; aktif
    yarisma bitmeden yeni kurulmaz). Olcum akisi HER ZAMAN akar; kapi
    yalnizca ISLEM kaydini kontrol eder. Donus: (islemler, ozet)."""
    atr_serisi = TV4.atr(barlar, ATR_PERIYOT)
    n_b = len(barlar)
    olc_n = kazan = 0
    sum_r = sum_kaz_r = 0.0
    islemler = []
    i = ATR_PERIYOT + 1
    while i < n_b - 1:
        g = _kapi(olc_n, kazan, sum_r, sum_kaz_r)
        atr = atr_serisi[i]
        r = _yaris_coz(barlar, i, atr, e, t, s, fund_8h) if atr else None
        if r is None:
            i += 1
            continue
        if g["acik"]:
            r["stake"] = g["stake"]
            r["kapi_not"] = g["not"]
            islemler.append(r)
        olc_n += 1
        sum_r += r["net_r"]
        if r["sonuc"] == "HEDEF":
            kazan += 1
            sum_kaz_r += r["net_r"]
        i = r["cozum"] + 1
    return islemler, {"n": olc_n, "kazanc": kazan, "sum_r": sum_r,
                      "sum_kaz_r": sum_kaz_r,
                      "son_kapi": _kapi(olc_n, kazan, sum_r, sum_kaz_r)}


def fade_karar(barlar, sembol_kisa, e=E_K, t=T_K, s=S_K, fund_8h=None,
               simdi=None):
    """Son (veya simdi) kapanisinda FADE karari. Yalnizca barlar[:simdi+1]
    okunur - bak-ileri YOK (T2 zehir testi bunu kanitlar)."""
    if fund_8h is None:
        fund_8h = FUNDING_YEDEK.get(sembol_kisa, 6e-5)
    kesit = len(barlar) - 1 if simdi is None else simdi
    b = barlar[:kesit + 1]
    isl, oz = fade_akisi(b, fund_8h, e, t, s)
    atr_serisi = TV4.atr(b, ATR_PERIYOT)
    atr = atr_serisi[-1]
    c = b[-1]["c"]
    kn = {"alt": c - e * atr, "ust": c + e * atr, "atr": atr} if atr else None
    return {"kapi": oz["son_kapi"], "kenarlar": kn, "e": e, "t": t, "s": s,
            "n_olcum": oz["n"], "islemler": isl, "ozet": oz}


# ------------------------------------------------------------- RAPOR
def _f3(v):
    return "yok" if v is None else "%.3f" % v


def _f4(v):
    return "yok" if v is None else "%+.4f" % v


def fade_blok(fk, sembol_kisa):
    g = fk["kapi"]
    kn = fk["kenarlar"]
    L = ["-" * 78,
         "FADE BAHIS SINIFI (v5-I17) - %s | 2H cift limit +-%.1fxATR"
         % (sembol_kisa, fk["e"])]
    if g["acik"] and kn:
        L.append("HUKUM_FADE  : BAHIS ACILIR - %s" % g["not"])
        L.append("EMIR_FADE   : cift tarafli LIMIT (maker) alt %s / ust %s"
                 % (TV4._bicim(kn["alt"], ".8g"), TV4._bicim(kn["ust"], ".8g")))
        L.append("YON_FADE    : ILK DOLAN KENAR belirler (alt=>LONG, ust=>SHORT)")
        L.append("HEDEF_FADE  : giris %s%.1fxATR donus | STOP_FADE: giris %s%.1fxATR"
                 % ("+" if True else "", fk["t"],
                    "-" if True else "", fk["s"]))
        L.append("R_FADE      : %.4f  (R = hedef_mesafesi / stop_mesafesi)"
                 % R_FADE)
        L.append("STAKE_FADE  : %.2f%% sermaye-riski (edge/b_win; cap %.0f%%)"
                 % (100 * g["stake"], 100 * KELLY_CAP))
        L.append("IPTAL_FADE  : kenar %d barda (5 gun) dolmazsa emir IPTAL"
                 % K_STALE)
    else:
        L.append("HUKUM_FADE  : BAHIS YOK - %s" % g["not"])
        L.append("NOT_FADE    : FADE sinifi KAPALI; ISLEM YOK (ana siniftan bagimsiz)")
        if g["n"]:
            L.append("BILGI_FADE  : olcum n=%d | p_hat=%s | edge_hat=%sR | stake=0"
                     % (g["n"], _f3(g["p_hat"]), _f4(g["edge_hat"])))
    return "\n".join(L)


# --------------------------------------------------------- 2H VERI
def h2_barlar(sembol_kisa, getir_fn=None, hedef=H2_HEDEF,
              onbellek=None, bayatlik_s=CACHE_BAYATLIK_S):
    """2H barlar: onbellek tazeyse onbellek, degilse OKX public
    history-candles sayfali cekimi (v4.http_getir - tek ag fonksiyonu,
    anahtar/imza YOK). Donus: (barlar, funding_8h, kaynak)."""
    inst = SEMBOL_H2.get(sembol_kisa + "USDT", sembol_kisa + "-USDT-SWAP")
    onbellek = onbellek or ("okx_h2_cache_%s.json" % sembol_kisa)
    simdi_ms = int(time.time() * 1000)
    if os.path.exists(onbellek):
        try:
            k = json.load(open(onbellek))
            if (k.get("inst") == inst and k.get("barlar")
                    and simdi_ms - k["barlar"][-1]["t"] < bayatlik_s * 1000
                    and len(k["barlar"]) >= 0.9 * hedef):
                return k["barlar"], k.get("funding_8h"), "onbellek"
        except Exception:
            pass
    getir_fn = TV4.http_getir if getir_fn is None else getir_fn
    gorulen, barlar = set(), []
    after = ""
    while len(barlar) < hedef:
        params = {"instId": inst, "bar": "2H", "limit": 100}
        if after:
            params["after"] = after
        j = getir_fn("https://www.okx.com/api/v5/market/history-candles", params)
        rows = (j.get("data") or []) if isinstance(j, dict) else []
        if not rows:
            break
        for x in rows:
            t = int(x[0])
            if t in gorulen:
                continue
            gorulen.add(t)
            barlar.append({"t": t, "o": float(x[1]), "h": float(x[2]),
                           "l": float(x[3]), "c": float(x[4]),
                           "v": float(x[5])})
        after = rows[-1][0]
    barlar.sort(key=lambda b: b["t"])
    fr = None
    try:
        jf = getir_fn("https://www.okx.com/api/v5/public/funding-rate-history",
                      {"instId": inst, "limit": FUNDING_PENCERE})
        degerler = [abs(float(x["fundingRate"]))
                    for x in (jf.get("data") or []) if x.get("fundingRate")]
        if degerler:
            fr = sum(degerler) / len(degerler)
    except Exception:
        pass
    try:
        json.dump({"inst": inst, "barlar": barlar, "funding_8h": fr},
                  open(onbellek, "w"))
    except Exception:
        pass
    return barlar, fr, "canli-cekim"


# ------------------------------------------------------------ KOSU
def v5_kosu_bas(sembol, getir_fn=None, hedef_h2=H2_HEDEF, baslik=None):
    """Bir sembolu v5 olarak kosturur: v4 ana sinif (dokunulmamis cikti)
    + FADE blogu. Donus: kayit sozlugu."""
    getir_fn = okx_uyumlu_getir if getir_fn is None else getir_fn
    karar, paket, toplama = TV4.canli_kosu(sembol, getir_fn=getir_fn)
    kisa = sembol[:-4] if sembol.endswith("USDT") else sembol
    barlar2h, fr, kaynak = h2_barlar(kisa, hedef=hedef_h2)
    fk = fade_karar(barlar2h, kisa, fund_8h=fr)
    print("=" * 78)
    print(baslik or ("v5 KOSU - %s (ANA sinif v4 + FADE sinifi v5)" % sembol))
    print("adaptor    :", toplama["adaptor"], "| ham kapsam:",
          round(toplama["kapsam"], 4))
    print("seri kanal :", paket["dolu_kanal"], "/", paket["toplam_kanal"],
          "| anlik (kapsama SAYILMAZ):", paket["anlik_kanallar"])
    print("bar        :", len(paket["barlar15"]), "x 15M +",
          len(paket["barlar4h"] or []), "x 4H | FADE:", len(barlar2h),
          "x 2H (kaynak: %s, funding_8h=%s)" % (kaynak, _f4(fr)))
    print()
    print(TV4.metin_rapor(karar))
    print()
    print(TV4.sonuc_satiri(karar, "CANLI (public GET)", paket))
    print(fade_blok(fk, kisa))
    return {"sembol": sembol, "karar": karar, "paket": paket,
            "toplama": toplama, "fade": fk, "h2_kaynak": kaynak}


def fade_durum_tablosu(semboller):
    print("=" * 78)
    print("FADE DURUM OZETI (v5) - 2H, cift limit +-%.1fxATR, hedef %.1f, stop %.1f"
          % (E_K, T_K, S_K))
    print("%-6s %-6s %-6s %-9s %-10s %-8s %s"
          % ("sembol", "n", "p_hat", "edge_hat", "hukum", "stake", "gerekce"))
    for semb in semboller:
        kisa = semb[:-4] if semb.endswith("USDT") else semb
        try:
            barlar, fr, _ = h2_barlar(kisa)
            fk = fade_karar(barlar, kisa, fund_8h=fr)
            g = fk["kapi"]
            print("%-6s %-6d %-6s %-+9.4f %-10s %-8s %s"
                  % (kisa, g["n"], _f3(g["p_hat"]), (g["edge_hat"] or 0.0),
                     "ACIK" if g["acik"] else "KAPALI",
                     ("%.2f%%" % (100 * g["stake"])) if g["acik"] else "0",
                     g["not"][:44]))
        except Exception as h:
            print("%-6s HATA: %s" % (kisa, h))


def varsayilan_kosu_v5(canli_getir=None, semboller=None):
    semboller = tuple(semboller or TV4.VARSAYILAN_SEMBOLLER)
    print("v5 KOSU BASLIYOR - %d sembol: %s" % (len(semboller), ", ".join(semboller)))
    kayitlar, dusenler = [], []
    for semb in semboller:
        try:
            kayitlar.append(v5_kosu_bas(semb, canli_getir))
        except Exception as h:
            dusenler.append((semb, "%s: %s" % (type(h).__name__, h)))
            print("!! %s KOSULAMADI -> %s: %s" % (semb, type(h).__name__, h))
    if kayitlar:
        print()
        print(TV4.portfoy_raporu(TV4.portfoy_karari(kayitlar)))
    fade_durum_tablosu(semboller)
    if dusenler:
        print("KOSULAMAYANLAR:", dusenler)
    return {"kayitlar": kayitlar, "dusenler": dusenler}


# -------------------------------------------------------- OZ TEST
def _mini_karar(f=0.0, not_="kanit yok (s=0)"):
    return {"sembol": "TEST", "yon": "LONG", "yon_kaynagi": "TEST",
            "p_ham": 0.5001, "giris": 100.0, "stop": 98.0, "hedef": 103.0,
            "R": 1.5,
            "geometri": {"basabas_p": 0.4, "p_hedef": 0.55, "n": 100},
            "stake": {"f": f, "not": not_},
            "iz": {"halka_0": {"onarim_guveni_gm": 1.0, "dolu_kanal": 4,
                               "toplam_kanal": 6, "anlik_kanallar": 2},
                   "halka_11": {"gecis": {"kalicilik": 0.6},
                                "pencere": 16, "gecis_kaymasi": 0.01}},
            "fiyat_gurultusu": {"spike_adet": 0, "donmus": 0,
                                "olcek_kaynagi": "ham", "atr_ham": 1.0,
                                "atr_gurultusuz": 1.0}}


def v5_selftest(barlar=None, sembol_kisa="BTC"):
    import copy
    import random
    import unittest

    R = []

    def kayit(ad, ok, detay=""):
        R.append((ad, "PASS" if ok else "FAIL", detay))

    # T1 v4 yukleme + I13 islevsel
    kayit("T1 v4 yuklendi (I13: %s)" % I13_DURUM,
          callable(getattr(TV4, "canli_kosu", None))
          and callable(getattr(TV4, "sonuc_satiri", None)))
    kapali = TV4.sonuc_satiri(_mini_karar(0.0), "TEST", None)
    acik = TV4.sonuc_satiri(_mini_karar(0.05, "olculmus kenar"), "TEST", None)
    kayit("T1b I13 f*=0 -> HUKUM BAHIS YOK + yon BILGI satiri",
          ("HUKUM      : BAHIS YOK" in kapali)
          and ("BILGI SATIRI" in kapali)
          and ("YON        : LONG" in kapali))
    kayit("T1c I13 f*>0 -> HUKUM BAHIS ACILIR",
          "HUKUM      : BAHIS ACILIR" in acik
          and "KOSULSUZ" in acik)

    # T2 bak-ileri zehir testi
    if barlar is not None:
        simdi = max(ATR_PERIYOT + 1, len(barlar) - 1000)
        d1 = fade_karar(barlar, sembol_kisa, simdi=simdi)
        zehir = [dict(b) for b in barlar]
        for j in range(simdi + 1, len(zehir)):
            carp = 10.0 if (j % 2) else 0.1
            zehir[j] = dict(zehir[j], o=zehir[j]["o"] * carp,
                            h=zehir[j]["h"] * carp, l=zehir[j]["l"] * carp,
                            c=zehir[j]["c"] * carp)
        d2 = fade_karar(zehir, sembol_kisa, simdi=simdi)
        kayit("T2 bak-ileri YOK (gelecek zehirlendi, karar ayni)",
              d1 == d2, "simdi=%d, n_islem=%d" % (simdi, len(d1["islemler"])))

    # T3 fail-closed (kesintisiz yukselen trend)
    X = 1.0
    p = 100.0
    trend = []
    for i in range(700):
        trend.append({"t": i * H2_ADIM_MS, "o": p, "h": p + 2 * X,
                      "l": p, "c": p + 2 * X, "v": 1.0})
        p += 2 * X
    isl, oz = fade_akisi(trend, 1e-5)
    kayit("T3 fail-closed (sentetik kayip trendi)",
          (not oz["son_kapi"]["acik"]) and oz["n"] >= MIN_N
          and oz["son_kapi"]["edge_hat"] is not None
          and oz["son_kapi"]["edge_hat"] < 0 and not isl,
          "n=%d edge=%s" % (oz["n"], _f4(oz["son_kapi"]["edge_hat"])))

    # T4 kapi matematigi
    k1 = _kapi(40, 25, 6.0, 40.0)
    k2 = _kapi(40, 20, -2.0, 30.0)
    k3 = _kapi(29, 20, 5.0, 30.0)
    kayit("T4 kapi: n>=MIN_N ve edge>0 ACIK; edge<=0 KAPALI; n<MIN_N KAPALI",
          k1["acik"] and k1["stake"] > 0 and (not k2["acik"])
          and k2["stake"] == 0.0 and (not k3["acik"]),
          "stake1=%.4f" % k1["stake"])

    # T5 R sozlesmesi (v4 seviyeler ile capraz kontrol)
    r_v4 = TV4.seviyeler(100.0, 2.0, "LONG", S_K, T_K)["R"]
    r_v4s = TV4.seviyeler(100.0, 2.0, "SHORT", S_K, T_K)["R"]
    kayit("T5 R = hedef/stop (v4 seviyeler ile AYNI)",
          abs(r_v4 - R_FADE) < 1e-12 and abs(r_v4s - R_FADE) < 1e-12)

    # T6 yasakli kelimeler (v5 bloklari + sonuc satirlari)
    fk_kapali = fade_karar(trend[:200], "BTC")
    blok1 = fade_blok(fk_kapali, "BTC")
    fk_acik = {"kapi": _kapi(40, 25, 6.0, 40.0),
               "kenarlar": {"alt": 99.0, "ust": 101.0, "atr": 1.0},
               "e": E_K, "t": T_K, "s": S_K, "n_olcum": 40}
    blok2 = fade_blok(fk_acik, "BTC")
    kayit("T6 yasakli desen yok (HOLD/ABSTAIN/Notr 0.0)",
          not any(k in blok1 + blok2 + kapali + acik for k in YASAKLI))
    kayit("T6b her iki durumda HUKUM_FADE satiri var",
          "HUKUM_FADE" in blok1 and "HUKUM_FADE" in blok2)

    # T7 determinizm
    if barlar is not None:
        kayit("T7 determinizm (ayni girdi -> ayni karar)",
              fade_karar(barlar, sembol_kisa, simdi=len(barlar) - 1)
              == fade_karar(barlar, sembol_kisa, simdi=len(barlar) - 1))

    # T8 v4'un kendi baglayici testleri (alt kume) hala GECIYOR
    hedef_testler = {"test_sozluk_iki_elemanli", "test_decode_daima_yon_doner",
                     "test_kaynakta_hold_sinifi_yok",
                     "test_dejenere_bolmede_bile_yon_uretilir",
                     "test_notr_sifir_enjeksiyonu_yok",
                     "test_R_hedef_bolu_stop_mesafesidir",
                     "test_kanit_yoksa_stake_TAM_sifir",
                     "test_yon_HER_zaman_uretilir"}
    vaka, bulunan = [], set()
    for ad in dir(TV4):
        sinif = getattr(TV4, ad)
        if not (isinstance(sinif, type) and issubclass(sinif, unittest.TestCase)):
            continue
        for t in hedef_testler:
            if hasattr(sinif, t):
                vaka.append(sinif(t))
                bulunan.add(t)
    sonuc = unittest.TestResult()
    unittest.TestSuite(vaka).run(sonuc)
    kayit("T8 v4 baglayici testleri (%d/%d)" % (len(vaka), len(hedef_testler)),
          (len(sonuc.failures) + len(sonuc.errors)) == 0 and len(vaka) > 0,
          "basarisiz=%d" % (len(sonuc.failures) + len(sonuc.errors)))

    # T9 kenar geometrisi: alt/ust mesafesi = E_K * ATR
    if barlar is not None:
        fk = fade_karar(barlar, sembol_kisa, simdi=len(barlar) - 1)
        kn = fk["kenarlar"]
        c = barlar[-1]["c"]
        kayit("T9 kenarlar c +- E_K*ATR",
              kn is not None
              and abs((kn["ust"] - c) - E_K * kn["atr"]) < 1e-9
              and abs((c - kn["alt"]) - E_K * kn["atr"]) < 1e-9)
    # T10 OKX uyum katmani (sahte OKX yanitlariyla)
    def _cek(url, params, zaman_asimi=20):
        if "/market/candles" in url or "/market/history-candles" in url:
            return {"code": "0", "data": [["1000", "1", "2", "0.5", "1.5",
                                           "10", "10", "15", "1"]]}
        if "open-interest-history" in url:
            return {"code": "0", "data": [["1000", "5", "5", "100"]]}
        if "taker-volume" in url:
            return {"code": "0", "data": [["1000", "3", "2"]]}
        return {"code": "0", "data": [{"x": 1}]}
    bin_hata = False
    try:
        okx_uyumlu_getir("https://api.binance.com/fapi/v1/klines", {}, cek=_cek)
    except RuntimeError:
        bin_hata = True
    kl = okx_uyumlu_getir("https://www.okx.com/api/v5/market/candles",
                          {"instId": "BTC-USDT-SWAP", "bar": "15m"}, cek=_cek)
    oi = okx_uyumlu_getir(
        "https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history",
        {"instId": "BTC-USDT-SWAP"}, cek=_cek)
    tk = okx_uyumlu_getir(
        "https://www.okx.com/api/v5/rubik/stat/taker-volume",
        {"ccy": "BTC"}, cek=_cek)
    kayit("T10 OKX uyum: binance yasak + 12-alan mum + oi/taker sozluk",
          bin_hata and len(kl) == 1 and len(kl[0]) == 12
          and abs(kl[0][9] - 5.0) < 1e-9 and kl[0][0] == 1000
          and isinstance(oi[0], dict) and "sumOpenInterest" in oi[0]
          and isinstance(tk[0], dict) and "buySellRatio" in tk[0]
          and abs(tk[0]["buySellRatio"] - 2.0 / 3.0) < 1e-9)
    tutulan = {}

    def _cek2(url, params, zaman_asimi=20):
        tutulan["url"] = url
        tutulan.update(params)
        return {"code": "0", "data": []}
    okx_uyumlu_getir("https://www.okx.com/api/v5/market/candles",
                    {"bar": "15m", "endTime": "999"}, cek=_cek2)
    kayit("T10b endTime->after + history-candles cevirisi",
          tutulan.get("after") == "999" and "endTime" not in tutulan
          and "/history-candles" in tutulan.get("url", ""))
    kayit("T11 OkxAdaptor sayfalanir enjeksiyonu (v4 kaynagi degismez)",
          bool(getattr(TV4.OkxAdaptor, "sayfalanir", False))
          and TV4.OkxAdaptor.ad == "okx-v5")
    return R


def _main(argv=None):
    if argv and argv[0] == "--self-test":
        for ad, durum, detay in v5_selftest():
            print("[%s] %s %s" % (durum, ad, detay))
        return 0
    if argv and argv[0] == "--fade-only":
        fade_durum_tablosu(TV4.VARSAYILAN_SEMBOLLER
                           + tuple(s for s in SEMBOL_H2
                                   if s not in TV4.VARSAYILAN_SEMBOLLER))
        return 0
    varsayilan_kosu_v5()
    return 0


if __name__ == "__main__":
    import sys as _s
    raise SystemExit(_main(_s.argv[1:]))
