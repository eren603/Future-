#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM islem zincirinin sayisal trading karsiligi (v3).

Iki eksen uretir:
  YON   - zorunlu argmax, sozluk {LONG, SHORT}. HOLD YOKTUR.
  STAKE - f*, surekli. Maliyet sonrasi asimetrik Kelly.
          f* = 0 bir "karar vermeme" DEGILDIR; Kelly'nin dogal degeridir.

Matematiksel hedef: E[log servet] maksimizasyonu.

Yalniz public GET. Canli emir, anahtar, imzali uc, emir ucu YOKTUR.
Yalniz Python standart kutuphanesi (Pydroid 3 uyumlu).
"""

import math
import random
import zlib

SURUM = "llm-trading-v3"
SEMBOLLER = ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]
YON_SOZLUGU = ("LONG", "SHORT")

EPSILON = 1e-12


# ---------------------------------------------------------------- BOLUM 1
# Determinizm ve temel yardimcilar.
# Modul duzeyi random.* cagrisi YASAK; her sey tohumlu_rng uzerinden.


def sabit_kimlik(*parcalar):
    """Deterministik 32-bit kimlik. Ayni girdi daima ayni sayi."""
    metin = "|".join(str(p) for p in parcalar)
    return zlib.crc32(metin.encode("utf-8")) & 0xFFFFFFFF


def tohumlu_rng(*parcalar):
    """Tohumlanmis RNG. Determinizmin tek kaynagi."""
    return random.Random(sabit_kimlik(*parcalar))


def kirp(x, alt=-1.0, ust=1.0):
    """Sayiyi [alt, ust] araligina kirpar. Gecersiz girdi alt sinira duser."""
    try:
        deger = float(x)
    except (TypeError, ValueError):
        return alt
    if math.isnan(deger) or math.isinf(deger):
        return alt
    return max(alt, min(ust, deger))


# ---------------------------------------------------------------- BOLUM 2
# Maliyet ve stake: asimetrik Kelly, maliyet SONRASI.


def maliyet_r(giris, stop_mesafesi, komisyon, kayma, funding):
    """Islem maliyetini R birimine cevirir.

    Gidis-donus komisyon + kayma nominal uzerinden, funding dogrudan eklenir.
    stop_mesafesi 0'a giderse maliyet buyur ama sonsuz olmaz.
    """
    mesafe = max(abs(float(stop_mesafesi)), EPSILON)
    nominal = 2.0 * abs(float(giris)) * (float(komisyon) + float(kayma))
    return (nominal + abs(float(funding)) * abs(float(giris))) / mesafe


def net_kanatlar(R, cost_r):
    """Maliyet sonrasi kazanc (b) ve kayip (a) kanatlari, R biriminde."""
    b = float(R) - float(cost_r)
    a = 1.0 + float(cost_r)
    return b, a


def basabas_p(b, a):
    """f* > 0 icin gereken en kucuk p. Kanat negatifse None (imkansiz)."""
    if b <= 0.0:
        return None
    return a / (a + b)


def kelly_asimetrik(p, b, a):
    """Asimetrik Kelly kesri. f* = (p*b - q*a) / (a*b), negatifse 0."""
    if b <= 0.0 or a <= 0.0:
        return 0.0
    p = kirp(p, 0.0, 1.0)
    q = 1.0 - p
    f = (p * b - q * a) / (a * b)
    return max(0.0, f)


# ---------------------------------------------------------------- BOLUM 3
# Kalibrasyon metrikleri. Dusuk ECE tek basina kanit DEGILDIR;
# ayirt edicilik (AUROC) ve en kotu grup ayrica olculur.


def wilson_araligi(basari, deneme, z=1.96):
    """Wilson skor araligi. Deneme yoksa (0,1) doner (bilgi yok)."""
    if deneme <= 0:
        return 0.0, 1.0
    p = basari / deneme
    payda = 1.0 + z * z / deneme
    merkez = p + z * z / (2.0 * deneme)
    yaricap = z * math.sqrt(p * (1.0 - p) / deneme + z * z / (4.0 * deneme * deneme))
    return (merkez - yaricap) / payda, (merkez + yaricap) / payda


def _kova(ciftler, bin_sayisi):
    """Guven degerine gore kovalara ayirir. Guven = max(p, 1-p)."""
    kovalar = [[] for _ in range(bin_sayisi)]
    for p, y in ciftler:
        guven = max(p, 1.0 - p)
        tahmin = 1 if p >= 0.5 else 0
        indeks = min(bin_sayisi - 1, int(guven * bin_sayisi))
        kovalar[indeks].append((guven, 1.0 if tahmin == y else 0.0))
    return kovalar


def ece(ciftler, bin_sayisi=10):
    """Beklenen kalibrasyon hatasi."""
    if not ciftler:
        return None
    toplam = len(ciftler)
    deger = 0.0
    for kova in _kova(ciftler, bin_sayisi):
        if not kova:
            continue
        ort_guven = sum(g for g, _ in kova) / len(kova)
        ort_dogruluk = sum(d for _, d in kova) / len(kova)
        deger += (len(kova) / toplam) * abs(ort_guven - ort_dogruluk)
    return deger


def mce(ciftler, bin_sayisi=10):
    """En kotu kovadaki kalibrasyon farki."""
    if not ciftler:
        return None
    en_kotu = 0.0
    for kova in _kova(ciftler, bin_sayisi):
        if not kova:
            continue
        ort_guven = sum(g for g, _ in kova) / len(kova)
        ort_dogruluk = sum(d for _, d in kova) / len(kova)
        en_kotu = max(en_kotu, abs(ort_guven - ort_dogruluk))
    return en_kotu


def ece_duyarlilik(ciftler, bin_listesi=(5, 10, 15, 20)):
    """ECE'nin bin sayisina duyarliligi + tek bine cokme tespiti."""
    if not ciftler:
        return {"degerler": {}, "tek_bine_cokme": True, "dolu_kova": 0}
    degerler = {n: ece(ciftler, n) for n in bin_listesi}
    dolu = sum(1 for kova in _kova(ciftler, 10) if kova)
    return {"degerler": degerler, "tek_bine_cokme": dolu <= 1, "dolu_kova": dolu}


def brier(ciftler):
    """Ikili Brier skoru."""
    if not ciftler:
        return None
    return sum((p - y) ** 2 for p, y in ciftler) / len(ciftler)


def auroc(ciftler):
    """ROC egrisi altindaki alan (Mann-Whitney U, baglar 0.5 sayilir)."""
    pozitif = [p for p, y in ciftler if y == 1]
    negatif = [p for p, y in ciftler if y == 0]
    if not pozitif or not negatif:
        return None
    toplam = 0.0
    for pp in pozitif:
        for pn in negatif:
            toplam += 1.0 if pp > pn else (0.5 if pp == pn else 0.0)
    return toplam / (len(pozitif) * len(negatif))


def grup_ece(ciftler_gruplu, bin_sayisi=10):
    """Grup basina ECE + en kotu grup. Grup: sembol/rejim/volatilite/kapsam."""
    gruplar = {}
    for ad, ciftler in ciftler_gruplu.items():
        deger = ece(ciftler, bin_sayisi)
        if deger is not None:
            gruplar[ad] = deger
    if not gruplar:
        return {"gruplar": {}, "en_kotu": (None, None)}
    en_kotu_ad = max(gruplar, key=lambda k: gruplar[k])
    return {"gruplar": gruplar, "en_kotu": (en_kotu_ad, gruplar[en_kotu_ad])}


# ---------------------------------------------------------------- BOLUM 4
# Shrinkage: kanit yoksa olasilik sansa cekilir, boylece stake kendiliginden
# sifira iner. Sabit esik YOKTUR; uc carpan da veriden gelir.

ECE_TAVANI = 0.10  # bu degerin ustunde kalibrasyon guvenilmez sayilir


def shrinkage_katsayisi(dogru, toplam, ece_enkotu, dolu_kanal, toplam_kanal):
    """s = s_kanit * s_kalibrasyon * s_kapsam, hepsi [0,1]."""
    alt, _ = wilson_araligi(dogru, toplam)
    s_kanit = kirp(2.0 * (alt - 0.5), 0.0, 1.0)

    if ece_enkotu is None:
        s_kalibrasyon = 0.0
    else:
        s_kalibrasyon = kirp(1.0 - float(ece_enkotu) / ECE_TAVANI, 0.0, 1.0)

    if toplam_kanal <= 0:
        s_kapsam = 0.0
    else:
        s_kapsam = kirp(dolu_kanal / toplam_kanal, 0.0, 1.0)

    return {
        "s": s_kanit * s_kalibrasyon * s_kapsam,
        "s_kanit": s_kanit,
        "s_kalibrasyon": s_kalibrasyon,
        "s_kapsam": s_kapsam,
    }


def daralt(p, s, hedef=0.5):
    """p'yi kanit gucune gore HEDEF'e dogru daraltir.

    Tarafsiz hedef 0.5 DEGILDIR: p=0.5, bahsin EV'sinin sifir oldugu anlamina
    gelmez (odul asimetrikse E[R] pozitif kalir). Stake sozlesmesi icin dogru
    hedef bahsin BASABAS olasiligidir; bkz. stake_hesapla.
    """
    hedef = kirp(hedef, 0.0, 1.0)
    return hedef + kirp(s, 0.0, 1.0) * (kirp(p, 0.0, 1.0) - hedef)


def stake_hesapla(p_ham, s, b, a, lam=1.0):
    """Stake sozlesmesinin TEK garanti noktasi: kanit yoksa f* tam olarak 0.

    p_ham kanit gucune gore bahsin basabas olasiligina daraltilir; s=0 iken
    p = p0 olur ve Kelly tanim geregi 0 doner.
    """
    p0 = basabas_p(b, a)
    if p0 is None:                      # kazanc kanadi yok: bahis imkansiz
        return {"f": 0.0, "p_kullanilan": None, "p0": None,
                "not": "kazanc kanadi <= 0 - bahis matematiksel olarak imkansiz"}
    p_kullanilan = daralt(p_ham, s, hedef=p0)
    f = kelly_asimetrik(p_kullanilan, b, a) * max(0.0, float(lam))
    return {"f": f, "p_kullanilan": p_kullanilan, "p0": p0, "not": ""}


# ---------------------------------------------------------------- BOLUM 5
# Geometri (R) sabit degil, karar degiskenidir. Ilk-gecis olasiligi GERCEK
# barlarla olculur; ayni barda iki bariyer = muhafazakar STOP.

IZGARA = (
    (1.0, 1.5), (1.0, 2.0), (1.0, 3.0), (1.0, 4.0),
    (1.5, 2.0), (1.5, 3.0), (1.5, 4.0), (1.5, 5.0),
    (2.0, 3.0), (2.0, 4.0), (2.0, 6.0),
)
ASGARI_OLCUM = 20  # bu sayidan az karar veren ornek varsa olcum guvenilmez


def ilk_gecis_olcum(barlar, indeksler, yon, stop_k, hedef_k, atr_serisi, azami_bar):
    """Her giris indeksi icin hangi bariyerin ONCE vuruldugunu sayar."""
    sayim = {"hedef": 0, "stop": 0, "zaman_asimi": 0}
    for i in indeksler:
        if i >= len(barlar) - 1 or i >= len(atr_serisi):
            continue
        giris = barlar[i]["c"]
        atr_deger = max(atr_serisi[i], EPSILON)
        if yon == "LONG":
            stop_seviye = giris - stop_k * atr_deger
            hedef_seviye = giris + hedef_k * atr_deger
        else:
            stop_seviye = giris + stop_k * atr_deger
            hedef_seviye = giris - hedef_k * atr_deger

        sonuc = "zaman_asimi"
        son = min(len(barlar), i + 1 + azami_bar)
        for j in range(i + 1, son):
            yuksek, dusuk = barlar[j]["h"], barlar[j]["l"]
            if yon == "LONG":
                stop_vurdu = dusuk <= stop_seviye
                hedef_vurdu = yuksek >= hedef_seviye
            else:
                stop_vurdu = yuksek >= stop_seviye
                hedef_vurdu = dusuk <= hedef_seviye
            if stop_vurdu:      # ayni barda ikisi de olsa STOP once sayilir
                sonuc = "stop"
                break
            if hedef_vurdu:
                sonuc = "hedef"
                break
        sayim[sonuc] += 1

    karar_veren = sayim["hedef"] + sayim["stop"]
    sayim["n"] = karar_veren
    sayim["p_hedef"] = (sayim["hedef"] / karar_veren) if karar_veren > 0 else None
    return sayim


def beklenen_log(p_hedef, f, b, a):
    """E[log servet] tek bahis icin. Iflas riskinde -inf."""
    kazanc = 1.0 + f * b
    kayip = 1.0 - f * a
    if kazanc <= 0.0 or kayip <= 0.0:
        return float("-inf")
    return p_hedef * math.log(kazanc) + (1.0 - p_hedef) * math.log(kayip)


def likidasyon_tavani(giris, likidasyon, kaldirac_azami, guvenlik=0.5):
    """Stake'in mutlak ust siniri. Likidasyon okunamazsa fail-closed 0."""
    if likidasyon is None or kaldirac_azami is None or kaldirac_azami <= 0:
        return 0.0
    giris = abs(float(giris))
    if giris <= 0:
        return 0.0
    mesafe_orani = abs(giris - float(likidasyon)) / giris
    return max(0.0, min(1.0 / float(kaldirac_azami), mesafe_orani * float(guvenlik)))


def stake_kirp(f_ham, f_max):
    """f*'i mutlak tavana kirpar ve kirpmayi bildirir."""
    f_ham = max(0.0, float(f_ham))
    f_max = max(0.0, float(f_max))
    if f_ham > f_max:
        return {"f": f_max, "kirpildi": True, "f_ham": f_ham, "f_max": f_max}
    return {"f": f_ham, "kirpildi": False, "f_ham": f_ham, "f_max": f_max}


def geometri_sec(barlar, indeksler, yon, atr_serisi, p_yon,
                 cost_r_fn, lam=1.0, azami_bar=32):
    """E[log] maksimize eden (stop_k, hedef_k) adayini secer.

    p_yon: modelin kalibre + daraltilmis yon olasiligi.
    cost_r_fn(stop_k) -> cost_r: maliyet stop mesafesine bagli oldugu icin
    her aday kendi maliyetiyle degerlendirilir.
    Olcum yetersizse fail-closed: f=0 ve gerekce yazilir.
    """
    en_iyi = None
    denenen = []
    for stop_k, hedef_k in IZGARA:
        olcum = ilk_gecis_olcum(barlar, indeksler, yon, stop_k, hedef_k,
                                atr_serisi, azami_bar)
        R = hedef_k / stop_k
        cost_r = float(cost_r_fn(stop_k))
        b, a = net_kanatlar(R, cost_r)
        if olcum["n"] < ASGARI_OLCUM or olcum["p_hedef"] is None:
            denenen.append({"stop_k": stop_k, "hedef_k": hedef_k, "elog": None,
                            "n": olcum["n"], "not": "OLCUM YOK"})
            continue
        # Karar olasiligi: modelin yon olasiligi ile olculen ilk-gecis birlestirilir
        # (ikisi de ayni olayi tahmin eder; geometrik ortalama muhafazakardir).
        p_bilesik = math.sqrt(max(0.0, p_yon) * max(0.0, olcum["p_hedef"]))
        f = kelly_asimetrik(p_bilesik, b, a) * lam
        elog = beklenen_log(p_bilesik, f, b, a)
        aday = {"stop_k": stop_k, "hedef_k": hedef_k, "R": R, "cost_r": cost_r,
                "b": b, "a": a, "p_hedef": olcum["p_hedef"], "p_bilesik": p_bilesik,
                "n": olcum["n"], "f": f, "elog": elog,
                "basabas_p": basabas_p(b, a), "not": ""}
        denenen.append(aday)
        if en_iyi is None or elog > en_iyi["elog"]:
            en_iyi = aday

    if en_iyi is None:
        varsayilan = IZGARA[5]  # (1.5, 3.0) - rapor icin notr referans
        return {"stop_k": varsayilan[0], "hedef_k": varsayilan[1],
                "R": varsayilan[1] / varsayilan[0], "p_hedef": None,
                "p_bilesik": None, "n": 0, "f": 0.0, "elog": None,
                "cost_r": None, "b": None, "a": None, "basabas_p": None,
                "not": "OLCUM YOK - yeterli ilk-gecis ornegi yok (fail-closed)",
                "denenen": denenen}

    en_iyi["denenen"] = denenen
    if en_iyi["elog"] <= 0.0:
        en_iyi["f"] = 0.0
        en_iyi["not"] = "E[log] <= 0 - hicbir geometri pozitif buyume vermiyor"
    return en_iyi
