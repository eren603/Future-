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

# ---------------------------------------------------------------- ESIK BEYANI
# Depo sozlesmesi (CLAUDE.md): kalibre edilemeyen her sabit ACIKCA etiketlenir.
# "Etiketsiz gizli esik" YASAK. Kaynak alani uc degerden biri olabilir:
#   OLCULEN  - bu kosunun verisinden istatistikle turetildi
#   YAPISAL  - matematiksel tanimdan gelir, secim degil
#   VARSAYIM - kalibre EDILMEDI; gerekcesi zorunlu, cikitida beyan edilir

ECE_TAVANI = 0.10        # kalibrasyon guvenilmezlik esigi
ASGARI_OLCUM = 20        # ilk-gecis olcumunun guvenilir sayilmasi icin asgari n
SABIT_ESIK_TOLERANSI = 1e-9   # bir kolonun "sabit" sayilmasi icin std tavani

ESIK_KAYNAGI = {
    "ECE_TAVANI": {
        "deger": ECE_TAVANI,
        "kaynak": "VARSAYIM",
        "gerekce": (
            "Kalibrasyon literaturunde yaygin bir rapor esigi; bu depoda HENUZ "
            "kalibre EDILMEDI. Etkisi tek yonludur: buyutulurse s_kalibrasyon "
            "artar ve stake buyur, kucultulurse stake kuculur. Fail-closed "
            "tarafta kalmak icin kucuk secildi. Olcum yolu: grup ECE dagiliminin "
            "ust yuzdeligi (holdout uzerinde) — yeterli ornek birikince turetilmeli."
        ),
    },
    "ASGARI_OLCUM": {
        "deger": ASGARI_OLCUM,
        "kaynak": "VARSAYIM",
        "gerekce": (
            "Ikili oranin Wilson araliginin ise yarar genislige inmesi icin kaba "
            "alt sinir; kalibre EDILMEDI. n=20'de %95 aralik genisligi ~0.4'tur, "
            "yani olcum zaten zayif sayilir ve p_bilesik geometrik ortalamayla "
            "bastirilir. Olcum yolu: hedeflenen aralik genisligine gore n cozulmeli."
        ),
    },
    "SABIT_ESIK_TOLERANSI": {
        "deger": SABIT_ESIK_TOLERANSI,
        "kaynak": "YAPISAL",
        "gerekce": (
            "Kayan nokta sifir-varyans toleransi; istatistiksel bir secim degil, "
            "float64 hassasiyet sinirindan gelir."
        ),
    },
}


def esik_kaydet(ad, deger, kaynak, gerekce):
    """Sabit esigi beyan defterine yazar. Etiketsiz esik YASAK."""
    ESIK_KAYNAGI[ad] = {"deger": deger, "kaynak": kaynak, "gerekce": gerekce}
    return deger


# Boru hatti sabitleri (hepsi ESIK_KAYNAGI'nda beyanli)
GECIKME_SAYISI = esik_kaydet(
    "GECIKME_SAYISI", 4, "VARSAYIM",
    "Karar tokeninin gordugu gecmis bar sayisi. Kalibre EDILMEDI. Buyutulurse "
    "baglam artar ama hesap O(n^2) buyur (Pydroid 3 kisiti). Olcum yolu: "
    "gecikme sayisina karsi holdout AUROC egrisi - platoya girdigi nokta.")

ETIKET_UFKU = esik_kaydet(
    "ETIKET_UFKU", 16, "VARSAYIM",
    "Etiketin bakacagi ileri bar sayisi (16 x 15dk = 4 saat). Kalibre EDILMEDI "
    "ve DOGRUDAN p'yi, dolayisiyla ECE ve stake'i belirler - etiketsiz gizli "
    "esik yasaginin tam hedefi budur. Olcum yolu: ufka karsi holdout AUROC ve "
    "ilk-gecis karar-veren oraninin birlikte taranmasi.")

EMBARGO = esik_kaydet(
    "EMBARGO", 4, "VARSAYIM",
    "Purge'un uzerine eklenen guvenlik boslugu (bar). Kalibre EDILMEDI. "
    "Kucultulurse sizinti riski artar, buyutulurse ornek kaybi artar. "
    "Olcum yolu: embargo'ya karsi train-test dagilim farkinin olculmesi.")

AZAMI_ORNEK = esik_kaydet(
    "AZAMI_ORNEK", 120, "YAPISAL",
    "HESAP BUTCESI (istatistik esigi DEGIL): her ornek bir Kodlayici.ileri "
    "cagrisidir, attention O(n^2). Hedef ortam Pydroid 3 (telefon). Butce "
    "bolmeyi dejenere edecek kadar kucultulemez: kronolojik_bol en az "
    "3*(ufuk+embargo+5) ornek ister; altina dusulurse bolme BOS kalir ve "
    "egitim/kalibrasyon/degerlendirme hic kosmaz.")

LIKIDASYON_GUVENLIK_PAYI = esik_kaydet(
    "LIKIDASYON_GUVENLIK_PAYI", 0.5, "VARSAYIM",
    "Likidasyon mesafesinin ne kadarina kadar stake alinabilecegi. Kalibre "
    "EDILMEDI. 0.5, likidasyona giden yolun yarisinda durmak demektir; "
    "muhafazakar taraf. Olcum yolu: gerceklesmis en kotu bar-ici sapmanin "
    "dagilimindan ust yuzdelik.")

ISINMA_BARI = esik_kaydet(
    "ISINMA_BARI", 20, "YAPISAL",
    "Gostergelerin (EMA/ATR/RSI/kanal) anlamli deger uretmesi icin gereken "
    "asgari gecmis bar sayisi; en uzun pencere (48) degil, gostergelerin "
    "kararli hale geldigi nokta. Istatistiksel secim degil, gosterge tanimindan.")


def esik_raporu():
    """Sabit esikleri kaynagi ve gerekcesiyle beyan eder (gizli esik yasagi)."""
    satirlar = ["SABIT ESIK BEYANI (etiketsiz gizli esik yasak):"]
    for ad, kayit in ESIK_KAYNAGI.items():
        satirlar.append(f"  {ad} = {kayit['deger']}  [{kayit['kaynak']}]")
        satirlar.append(f"      {kayit['gerekce']}")
    return "\n".join(satirlar)


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


def likidasyon_tavani(giris, likidasyon, kaldirac_azami,
                      guvenlik=LIKIDASYON_GUVENLIK_PAYI):
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


# ---------------------------------------------------------------- BOLUM 6
# Veri adaptorleri. Yalniz public GET. Erisilemeyen kanal None kalir;
# notr 0.0 enjeksiyonu YASAK (uydurma yasagi).
# Ag cagrisi disaridan enjekte edilir (getir_fn) -> agsiz test edilebilir.

KANALLAR = ("kline_15m", "kline_4h", "oi", "funding", "taker", "derinlik")


class Adaptor:
    """Ortak arayuz. Alt siniflar YALNIZ url uretir, ag cagrisi yapmaz."""

    ad = "soyut"
    taban = ""

    def uc(self, kanal, sembol):
        raise NotImplementedError


class BinanceAdaptor(Adaptor):
    ad = "binance"
    taban = "https://fapi.binance.com"

    def uc(self, kanal, sembol):
        t = self.taban
        return {
            "kline_15m": (t + "/fapi/v1/klines",
                          {"symbol": sembol, "interval": "15m", "limit": "500"}),
            "kline_4h": (t + "/fapi/v1/klines",
                         {"symbol": sembol, "interval": "4h", "limit": "500"}),
            "oi": (t + "/futures/data/openInterestHist",
                   {"symbol": sembol, "period": "15m", "limit": "500"}),
            "funding": (t + "/fapi/v1/premiumIndex", {"symbol": sembol}),
            "taker": (t + "/futures/data/takerlongshortRatio",
                      {"symbol": sembol, "period": "15m", "limit": "500"}),
            "derinlik": (t + "/fapi/v1/depth", {"symbol": sembol, "limit": "20"}),
        }[kanal]


class OkxAdaptor(Adaptor):
    ad = "okx"
    taban = "https://www.okx.com"

    def _inst(self, sembol):
        return sembol.replace("USDT", "-USDT-SWAP")

    def uc(self, kanal, sembol):
        # NOT: OKX resmi SDK'sinda parametre adi "period"tir, "periodic" DEGIL.
        # Yanlis ad sessizce yok sayilir ve varsayilan periyot doner.
        t, inst = self.taban, self._inst(sembol)
        para = inst.split("-")[0]
        return {
            "kline_15m": (t + "/api/v5/market/candles",
                          {"instId": inst, "bar": "15m", "limit": "300"}),
            "kline_4h": (t + "/api/v5/market/candles",
                         {"instId": inst, "bar": "4H", "limit": "300"}),
            "oi": (t + "/api/v5/rubik/stat/contracts/open-interest-history",
                   {"instId": inst, "period": "15m"}),
            "funding": (t + "/api/v5/public/funding-rate", {"instId": inst}),
            "taker": (t + "/api/v5/rubik/stat/taker-volume",
                      {"instType": "CONTRACTS", "ccy": para, "period": "15m"}),
            "derinlik": (t + "/api/v5/market/books", {"instId": inst, "sz": "20"}),
        }[kanal]


def veri_topla(sembol, adaptorler, getir_fn):
    """Adaptorleri sirayla dener. Kanal basina basari/dusus kaydedilir."""
    yedege_dusuldu = False
    for sira, adaptor in enumerate(adaptorler):
        kanallar = {}
        dusen = []
        for kanal in KANALLAR:
            url, params = adaptor.uc(kanal, sembol)
            try:
                kanallar[kanal] = getir_fn(url, params)
            except Exception:
                kanallar[kanal] = None      # UYDURMA YOK: None kalir
                dusen.append(kanal)
        kapsam = sum(1 for v in kanallar.values() if v is not None) / len(KANALLAR)
        if kapsam > 0.0:
            return {"adaptor": adaptor.ad, "kanallar": kanallar, "kapsam": kapsam,
                    "dusen": dusen, "yedege_dusuldu": yedege_dusuldu or sira > 0}
        yedege_dusuldu = True

    return {"adaptor": None, "kanallar": {k: None for k in KANALLAR},
            "kapsam": 0.0, "dusen": list(KANALLAR), "yedege_dusuldu": True}


# ---------------------------------------------------------------- BOLUM 7a
# Ozellik-token sozlugu. Token kimligi (sembol, zaman_dilimi, aile, gecikme)
# dortlusudur; 4H ve 15M AYRI zaman dilimi tokenlaridir.

ZAMAN_DILIMLERI = ("15m", "4h")
AILELER = {
    "fiyat": 6,     # getiri1, getiri4, getiri16, ema_farki, rsi, kanal_konumu
    "hacim": 2,     # hacim_z, nominal_hacim_z
    "turev": 5,     # oi_degisim, funding_z, taker_dengesi, derinlik_dengesi, kapsam
    "oynaklik": 3,  # atr_orani, oynaklik_orani, rejim
}


class TokenSozlugu:
    """Token kimliklerini tutan sozluk. Ayni dortlu daima ayni kimlik."""

    def __init__(self):
        self._kimlikler = {}

    def kimlik(self, sembol, zaman_dilimi, aile, gecikme):
        anahtar = (sembol, zaman_dilimi, aile, int(gecikme))
        if anahtar not in self._kimlikler:
            self._kimlikler[anahtar] = len(self._kimlikler) + 1
        return self._kimlikler[anahtar]

    @property
    def boyut(self):
        return len(self._kimlikler)


def token_listesi(semboller, gecikme_sayisi):
    """Bir ileri gecis icin uretilecek tokenlarin tam listesi (eskiden yeniye)."""
    tokenlar = []
    for gecikme in range(gecikme_sayisi - 1, -1, -1):
        for sembol in semboller:
            for zaman_dilimi in ZAMAN_DILIMLERI:
                for aile in AILELER:
                    tokenlar.append({
                        "sembol": sembol,
                        "zaman_dilimi": zaman_dilimi,
                        "aile": aile,
                        "gecikme": gecikme,
                        "boyut": AILELER[aile],
                    })
    return tokenlar


# ---------------------------------------------------------------- BOLUM 7b
# Gecmise dayali normalizasyon: olcekleyici YALNIZ train diliminden fit edilir.
# Sabit kolon (std=0) bilgi tasimaz -> ham deger gecirilmez, 0.0 verilir.


class Olcekleyici:
    def __init__(self):
        self._parametre = {}
        self.sabit_kolonlar = []
        self._fit_edildi = False

    def fit(self, satirlar, kesim):
        egitim = satirlar[:max(1, int(kesim))]
        self._parametre = {}
        self.sabit_kolonlar = []
        for aile, boyut in AILELER.items():
            kolonlar = []
            for j in range(boyut):
                degerler = [float(s[aile][j]) for s in egitim if aile in s]
                kolonlar.append(self._kolon_parametresi(aile, j, degerler))
            self._parametre[aile] = kolonlar
        self._fit_edildi = True

    def _kolon_parametresi(self, aile, j, degerler):
        if not degerler:
            self.sabit_kolonlar.append((aile, j))
            return (0.0, 1.0, True)
        ortalama = sum(degerler) / len(degerler)
        if len(degerler) < 2:
            varyans = 0.0
        else:
            varyans = sum((d - ortalama) ** 2 for d in degerler) / (len(degerler) - 1)
        std = math.sqrt(varyans)
        sabit = std < SABIT_ESIK_TOLERANSI
        if sabit:
            self.sabit_kolonlar.append((aile, j))
        return (ortalama, 1.0 if sabit else std, sabit)

    def donustur(self, aile, degerler):
        if not self._fit_edildi:
            raise RuntimeError("Olcekleyici fit edilmeden kullanilamaz")
        sonuc = []
        for deger, (ortalama, std, sabit) in zip(degerler, self._parametre[aile]):
            if sabit:
                sonuc.append(0.0)       # sabit kolon: ham deger SIZDIRILMAZ
            else:
                sonuc.append(kirp((float(deger) - ortalama) / std, -5.0, 5.0))
        return sonuc


SEMBOL_EKSENI_FAZI = math.pi / 4.0
"""Sembol ekseninin faz kaydirmasi.

Gerekce: taban degistirmek TEK BASINA yetmez. konum=0'da aci = 0/payda = 0
olur ve sin(0)=0, cos(0)=1 her tabanda AYNI vektoru verir; yani lag=0 ile
sembol=0 cakisir ve model bu iki ekseni ayirt edemez.

Olculen (boyut=16, fonksiyonun kendi ciktisi, 0.10 olcek dahil):
  fazsiz  konum=0 -> L2 = 0.000000  (TAM CAKISMA)
  fazli   konum 0..3 -> L2 = 0.2165, 0.2434, 0.2706, 0.2970
Bu degerler KonumKoduTesti.test_faz_olculen_ayrisma_degeri ile kilitlidir;
sayi degisirse test duser.
"""


def _sinuzoidal(konum, boyut, taban, faz=0.0):
    cikti = []
    for k in range(boyut):
        payda = taban ** (2.0 * (k // 2) / max(1, boyut))
        aci = konum / payda + faz
        cikti.append(math.sin(aci) if k % 2 == 0 else math.cos(aci))
    return cikti


def zaman_konumu(gecikme, boyut):
    """Zaman ekseni konum kodu (gecikme = kac bar geride)."""
    return [x * 0.10 for x in _sinuzoidal(gecikme, boyut, 10000.0)]


def sembol_konumu(sembol_indeksi, boyut):
    """Sembol ekseni konum kodu - zaman ekseninden AYRISIK.

    Ayrisma iki mekanizmayla saglanir: farkli taban (frekans bandi) VE
    faz kaydirmasi (konum=0 cakismasini kaldirir).
    """
    return [x * 0.10 for x in _sinuzoidal(sembol_indeksi, boyut, 97.0,
                                          faz=SEMBOL_EKSENI_FAZI)]


# ---------------------------------------------------------------- BOLUM 7c
# Causal attention + FFN.
# qk_acik / maske_acik / ffn_acik anahtarlari YALNIZ olu-halka testleri
# icindir; uretimde daima True. Her anahtar kapatilinca cikti DEGISMELIDIR.


def matris(satir, sutun, tohum_parcalari, olcek=0.12):
    rng = tohumlu_rng(*tohum_parcalari)
    return [[rng.uniform(-olcek, olcek) for _ in range(sutun)] for _ in range(satir)]


def vektor(boyut, tohum_parcalari, olcek=0.12):
    rng = tohumlu_rng(*tohum_parcalari)
    return [rng.uniform(-olcek, olcek) for _ in range(boyut)]


def matvec(M, v):
    return [sum(satir[j] * v[j] for j in range(len(v))) for satir in M]


def nokta(a, b):
    return sum(x * y for x, y in zip(a, b))


def topla_vek(*vektorler):
    if not vektorler:
        return []
    return [sum(v[i] for v in vektorler) for i in range(len(vektorler[0]))]


def kararli_softmax(logitler, sicaklik=1.0):
    T = max(float(sicaklik), 1e-6)
    olcekli = [float(z) / T for z in logitler]
    en_buyuk = max(olcekli) if olcekli else 0.0
    us = [math.exp(max(-60.0, min(60.0, z - en_buyuk))) for z in olcekli]
    toplam = sum(us) or 1.0
    return [u / toplam for u in us]


def katman_norm(v, epsilon=1e-5):
    ort = sum(v) / len(v)
    std = math.sqrt(sum((x - ort) ** 2 for x in v) / len(v) + epsilon)
    return [(x - ort) / std for x in v]


def relu(v):
    return [max(0.0, x) for x in v]


class Kodlayici:
    """Tek bloklu nedensel kodlayici.

    Karar temsili = son token + TUM durumlarin havuzu. Havuz sayesinde
    maskelenen konumlar ciktiyi GERCEKTEN etkiler (yalniz son tokene
    bakilsaydi maske olu kod olurdu).
    """

    def __init__(self, boyut=16, bas_sayisi=2, tohum=2026):
        self.boyut = boyut
        self.bas_sayisi = bas_sayisi
        self.bas_boyut = boyut // bas_sayisi
        self.tohum = tohum
        self.wq = [matris(self.bas_boyut, boyut, (tohum, "wq", h))
                   for h in range(bas_sayisi)]
        self.wk = [matris(self.bas_boyut, boyut, (tohum, "wk", h))
                   for h in range(bas_sayisi)]
        self.wv = [matris(self.bas_boyut, boyut, (tohum, "wv", h))
                   for h in range(bas_sayisi)]
        self.wo = matris(boyut, self.bas_boyut * bas_sayisi, (tohum, "wo"))
        self.ff1 = matris(boyut * 2, boyut, (tohum, "ff1"))
        self.ff2 = matris(boyut, boyut * 2, (tohum, "ff2"))

    def _dikkat(self, durumlar, qk_acik, maske_acik):
        n = len(durumlar)
        olcek = math.sqrt(max(1, self.bas_boyut))
        bas_ciktilari = []
        for h in range(self.bas_sayisi):
            q = [matvec(self.wq[h], x) for x in durumlar]
            k = [matvec(self.wk[h], x) for x in durumlar]
            v = [matvec(self.wv[h], x) for x in durumlar]
            cikti = []
            for i in range(n):
                skorlar = []
                for j in range(n):
                    if maske_acik and j > i:
                        skorlar.append(-1e9)
                    elif qk_acik:
                        skorlar.append(nokta(q[i], k[j]) / olcek)
                    else:
                        skorlar.append(0.0)
                agirlik = kararli_softmax(skorlar)
                cikti.append([sum(agirlik[j] * v[j][u] for j in range(n))
                              for u in range(self.bas_boyut)])
            bas_ciktilari.append(cikti)
        return bas_ciktilari

    def ileri(self, durumlar, qk_acik=True, maske_acik=True, ffn_acik=True):
        n = len(durumlar)
        bas_ciktilari = self._dikkat(durumlar, qk_acik, maske_acik)
        yeni = []
        for i in range(n):
            birlesik = []
            for h in range(self.bas_sayisi):
                birlesik.extend(bas_ciktilari[h][i])
            yeni.append(katman_norm(topla_vek(durumlar[i],
                                              matvec(self.wo, birlesik))))
        havuz = [sum(y[j] for y in yeni) / n for j in range(self.boyut)]
        h_vek = topla_vek(yeni[-1], havuz)
        if ffn_acik:
            h_vek = topla_vek(h_vek, matvec(self.ff2, relu(matvec(self.ff1, h_vek))))
        return katman_norm(h_vek)


# ---------------------------------------------------------------- BOLUM 7d
# Kronolojik bolme + purge/embargo + egitilen logit basligi (V = LONG/SHORT).


def kronolojik_bol(indeksler, ufuk, embargo, oranlar=(0.6, 0.2, 0.2)):
    """Train/kalibrasyon/test; sinirlarda purge (ufuk) + embargo uygulanir."""
    sirali = sorted(indeksler)
    n = len(sirali)
    bosluk = int(ufuk) + int(embargo)
    if n < 3 * (bosluk + 5):
        return {"train": [], "kalibrasyon": [], "test": [], "atilan": n,
                "not": "yetersiz ornek - bolme yapilamadi"}

    kesim1 = int(n * oranlar[0])
    kesim2 = int(n * (oranlar[0] + oranlar[1]))
    train, kalibrasyon, test = sirali[:kesim1], sirali[kesim1:kesim2], sirali[kesim2:]

    if train and kalibrasyon:      # PURGE: etiket penceresi sonraki bolmeye tasmasin
        train = [i for i in train if i + bosluk < kalibrasyon[0]]
    if kalibrasyon and test:
        kalibrasyon = [i for i in kalibrasyon if i + bosluk < test[0]]

    atilan = n - (len(train) + len(kalibrasyon) + len(test))
    return {"train": train, "kalibrasyon": kalibrasyon, "test": test,
            "atilan": atilan, "not": ""}


def sizinti_var_mi(bolme, ufuk, giris_penceresi):
    """Bir bolmenin etiket penceresi sonrakinin girdi penceresine giriyor mu?"""
    for once, sonra in (("train", "kalibrasyon"), ("kalibrasyon", "test")):
        a, b = bolme.get(once) or [], bolme.get(sonra) or []
        if not a or not b:
            continue
        if max(a) + int(ufuk) >= min(b) - int(giris_penceresi) + 1:
            return True
    return False


class Baslik:
    """Iki sinifli (LONG/SHORT) egitilen logit basligi, agirlikli capraz entropi."""

    def __init__(self, boyut=16, tohum=3000):
        self.boyut = boyut
        self.w = matris(2, boyut, (tohum, "baslik-w"), 0.02)
        self.b = vektor(2, (tohum, "baslik-b"), 0.02)
        self.tohum = tohum

    def logit(self, x):
        return [nokta(self.w[k], x) + self.b[k] for k in range(2)]

    def kayip(self, ornekler):
        if not ornekler:
            return float("inf")
        toplam = 0.0
        for o in ornekler:
            p = kararli_softmax(self.logit(o["x"]))
            toplam += -math.log(max(1e-12, p[o["y"]]))
        return toplam / len(ornekler)

    def _sinif_agirliklari(self, ornekler):
        sayim = [0, 0]
        for o in ornekler:
            sayim[o["y"]] += 1
        toplam = sum(sayim) or 1
        return [toplam / (2.0 * max(1, s)) for s in sayim]

    def egit(self, ornekler, devir=60, ogrenme_hizi=0.10, agirlik_azalmasi=5e-4):
        if not ornekler:
            return
        agirliklar = self._sinif_agirliklari(ornekler)
        rng = tohumlu_rng(self.tohum, "karistir")
        sira = list(range(len(ornekler)))
        for adim in range(devir):
            rng.shuffle(sira)
            grad_w = [[0.0] * self.boyut for _ in range(2)]
            grad_b = [0.0, 0.0]
            for indeks in sira:
                o = ornekler[indeks]
                p = kararli_softmax(self.logit(o["x"]))
                agirlik = agirliklar[o["y"]]
                for k in range(2):
                    hata = (p[k] - (1.0 if k == o["y"] else 0.0)) * agirlik
                    for j in range(self.boyut):
                        grad_w[k][j] += hata * o["x"][j]
                    grad_b[k] += hata
            hiz = ogrenme_hizi / (1.0 + adim / 25.0)
            payda = max(1, len(ornekler))
            for k in range(2):
                for j in range(self.boyut):
                    self.w[k][j] -= hiz * (grad_w[k][j] / payda
                                           + agirlik_azalmasi * self.w[k][j])
                self.b[k] -= hiz * grad_b[k] / payda


# ---------------------------------------------------------------- BOLUM 7e
# Kalibrasyon: T, DAGITILAN dagilimin kendisinde fit edilir.

SICAKLIK_IZGARASI = tuple(math.exp(-2.0 + 4.0 * i / 40.0) for i in range(41))


def topluluk_olasilik(x, basliklar, sicaklik=1.0):
    """Her baslik icin softmax alinir, SONRA olasiliklar ortalanir."""
    gorusler = [kararli_softmax(b.logit(x), sicaklik) for b in basliklar]
    n = len(gorusler) or 1
    p = [sum(g[k] for g in gorusler) / n for k in range(2)]
    argmaxlar = [0 if g[0] >= g[1] else 1 for g in gorusler]
    uzlasi = max(argmaxlar.count(0), argmaxlar.count(1)) / n
    dagilim = sum(sum((g[k] - p[k]) ** 2 for g in gorusler) / n
                  for k in range(2)) / 2.0
    return {"p": p, "gorusler": gorusler, "uzlasi": uzlasi, "dagilim": dagilim}


def _nll(ornekler, basliklar, sicaklik):
    if not ornekler:
        return float("inf")
    toplam = 0.0
    for o in ornekler:
        p = topluluk_olasilik(o["x"], basliklar, sicaklik)["p"]
        toplam += -math.log(max(1e-12, p[o["y"]]))
    return toplam / len(ornekler)


def sicaklik_fit(ornekler, basliklar):
    """T'yi DAGITILAN dagilimda (olasilik-havuzu) NLL minimize ederek secer."""
    en_iyi_T, en_iyi_nll = 1.0, float("inf")
    for T in SICAKLIK_IZGARASI:
        deger = _nll(ornekler, basliklar, T)
        if deger < en_iyi_nll:
            en_iyi_T, en_iyi_nll = T, deger
    sinirda = (en_iyi_T <= SICAKLIK_IZGARASI[0] * 1.001
               or en_iyi_T >= SICAKLIK_IZGARASI[-1] * 0.999)
    return {"T": en_iyi_T, "nll": en_iyi_nll, "sinirda": sinirda}


def sicaklik_karari_cevirir_mi(baslik_logitleri, izgara=(0.2, 1.0, 5.0)):
    """Karisim softmaxinda T, argmax'i degistirebilir mi?

    Tek softmax monotondur ama OLASILIK-HAVUZU karisimi degildir: T->0'da
    karar oy sayisina, T->buyukte ortalama logit farkina duser. Ikisi
    celisirse yon T ile doner. Bu bir hata degil OLGUDUR; sistem bunu
    olcup raporlar (63-bulgu #24).
    """
    kararlar = set()
    for T in izgara:
        gorusler = [kararli_softmax(z, T) for z in baslik_logitleri]
        n = len(gorusler) or 1
        p_long = sum(g[0] for g in gorusler) / n
        p_short = sum(g[1] for g in gorusler) / n
        kararlar.add("LONG" if p_long >= p_short else "SHORT")
    return len(kararlar) > 1


def izotonik_fit(ciftler):
    """PAVA ile monoton kalibrasyon egrisi. Donen fonksiyon p -> p_kalibre."""
    sirali = sorted(ciftler, key=lambda c: c[0])
    if not sirali:
        return lambda p: p
    x = [c[0] for c in sirali]
    y = [float(c[1]) for c in sirali]
    agirlik = [1.0] * len(y)
    i = 0
    while i < len(y) - 1:
        if y[i] <= y[i + 1] + 1e-12:
            i += 1
            continue
        toplam_a = agirlik[i] + agirlik[i + 1]
        ort = (y[i] * agirlik[i] + y[i + 1] * agirlik[i + 1]) / toplam_a
        y[i:i + 2] = [ort]
        agirlik[i:i + 2] = [toplam_a]
        x[i:i + 2] = [x[i]]
        i = max(0, i - 1)

    def uygula(p):
        if p <= x[0]:
            return y[0]
        for k in range(1, len(x)):
            if p <= x[k]:
                return y[k - 1]
        return y[-1]

    return uygula


def kalibrasyon_sec(kal_ornekler, basliklar):
    """Sicaklik ve izotonik arasinda holdout NLL'e gore secim."""
    sicaklik = sicaklik_fit(kal_ornekler, basliklar)

    ham = [(topluluk_olasilik(o["x"], basliklar, 1.0)["p"][0], o["y"])
           for o in kal_ornekler]
    izo = izotonik_fit(ham)
    izo_nll = float("inf")
    if ham:
        toplam = 0.0
        for p_ham, y in ham:
            p_kal = min(1.0 - 1e-9, max(1e-9, izo(p_ham)))
            toplam += -math.log(p_kal if y == 1 else 1.0 - p_kal)
        izo_nll = toplam / len(ham)

    if izo_nll < sicaklik["nll"]:
        return {"yontem": "izotonik", "T": 1.0, "fn": izo, "nll": izo_nll,
                "sinirda": False}
    return {"yontem": "sicaklik", "T": sicaklik["T"], "fn": None,
            "nll": sicaklik["nll"], "sinirda": sicaklik["sinirda"]}


# ---------------------------------------------------------------- BOLUM 8
# Decoding: sozluk V = {LONG, SHORT}. HOLD YOKTUR. Seviyeler KOSULSUZ uretilir.
# Stake ayri bir eksendir; f*=0 bir sinif degil, Kelly'nin dogal degeridir.

LAMBDA_TABLOSU = (1.0, 0.5, 0.25)


def decode(p_long):
    """argmax. Beraberlikte LONG (tanimli ve deterministik)."""
    return "LONG" if float(p_long) >= 0.5 else "SHORT"


def seviyeler(giris, atr_deger, yon, stop_k, hedef_k):
    giris = float(giris)
    atr_deger = max(float(atr_deger), EPSILON)
    if yon == "LONG":
        stop = giris - stop_k * atr_deger
        hedef = giris + hedef_k * atr_deger
    else:
        stop = giris + stop_k * atr_deger
        hedef = giris - hedef_k * atr_deger
    return {"giris": giris, "stop": stop, "hedef": hedef,
            "stop_mesafesi": abs(giris - stop), "R": hedef_k / stop_k}


def karar_uret(baglam):
    """Tek sembol icin nihai karar: YON (zorunlu) + STAKE (surekli)."""
    shr = shrinkage_katsayisi(baglam["dogru"], baglam["toplam"],
                              baglam.get("ece_enkotu"),
                              baglam["dolu_kanal"], baglam["toplam_kanal"])

    # YON kosulsuz ve DARALTILMAMIS olasiliktan gelir: shrinkage stake'i
    # sifirlar ama yon BILGISINI yok etmez (belgenin Gerekce 2'si korunur).
    yon = decode(baglam["p_ham"])
    p_yon = baglam["p_ham"] if yon == "LONG" else (1.0 - baglam["p_ham"])

    def cost_r_fn(stop_k):
        mesafe = stop_k * max(float(baglam["atr"]), EPSILON)
        return maliyet_r(baglam["giris"], mesafe, baglam["komisyon"],
                         baglam["kayma"], baglam["funding"])

    geo = geometri_sec(baglam["barlar"], baglam["indeksler"], yon,
                       baglam["atr_serisi"], p_yon, cost_r_fn,
                       lam=1.0, azami_bar=baglam.get("azami_bar", 32))

    sev = seviyeler(baglam["giris"], baglam["atr"], yon,
                    geo["stop_k"], geo["hedef_k"])

    # STAKE: sozlesme stake_hesapla icinde garanti edilir (kanit yoksa f*=0).
    f_max = likidasyon_tavani(baglam["giris"], baglam.get("likidasyon"),
                              baglam.get("kaldirac_azami"),
                              LIKIDASYON_GUVENLIK_PAYI)
    b, a = (geo.get("b"), geo.get("a"))
    lambda_tablosu = {}
    for lam in LAMBDA_TABLOSU:
        if b is None or a is None or geo["f"] <= 0.0:
            lambda_tablosu[str(lam)] = {"f": 0.0, "kirpildi": False,
                                        "f_ham": 0.0, "f_max": f_max}
            continue
        ham = stake_hesapla(p_yon, shr["s"], b, a, lam)
        lambda_tablosu[str(lam)] = stake_kirp(ham["f"], f_max)
    secilen = lambda_tablosu[str(float(baglam.get("lam", 1.0)))]

    return {
        "sembol": baglam["sembol"], "yon": yon,
        "p_ham": baglam["p_ham"],
        "p_kullanilan": daralt(p_yon, shr["s"],
                               hedef=(geo.get("basabas_p") or 0.5)),
        "shrinkage": shr, "geometri": geo,
        "giris": sev["giris"], "stop": sev["stop"], "hedef": sev["hedef"],
        "R": sev["R"],
        "stake": {"f": secilen["f"], "kirpildi": secilen["kirpildi"],
                  "f_max": f_max, "lambda_tablosu": lambda_tablosu},
    }


# ---------------------------------------------------------------- BOLUM 9a
# Gostergeler (stdlib, kayan pencere).


def ema(degerler, periyot):
    if not degerler:
        return []
    alfa = 2.0 / (periyot + 1.0)
    cikti = [float(degerler[0])]
    for x in degerler[1:]:
        cikti.append(alfa * float(x) + (1.0 - alfa) * cikti[-1])
    return cikti


def atr(barlar, periyot=14):
    araliklar = []
    for i, b in enumerate(barlar):
        onceki = barlar[i - 1]["c"] if i else b["c"]
        araliklar.append(max(b["h"] - b["l"], abs(b["h"] - onceki),
                             abs(b["l"] - onceki)))
    cikti = []
    for i in range(len(araliklar)):
        pencere = araliklar[max(0, i - periyot + 1):i + 1]
        cikti.append(sum(pencere) / len(pencere))
    return cikti


def rsi(kapanislar, periyot=14):
    cikti = [50.0] * len(kapanislar)
    for i in range(periyot, len(kapanislar)):
        kazanc, kayip = [], []
        for j in range(i - periyot + 1, i + 1):
            fark = kapanislar[j] - kapanislar[j - 1]
            kazanc.append(max(fark, 0.0))
            kayip.append(max(-fark, 0.0))
        ok = sum(kazanc) / len(kazanc)
        oy = sum(kayip) / len(kayip)
        if oy == 0:
            cikti[i] = 100.0 if ok > 0 else 50.0
        else:
            cikti[i] = 100.0 - 100.0 / (1.0 + ok / oy)
    return cikti


# ---------------------------------------------------------------- BOLUM 9b
# Uctan uca boru hatti. 12 halkanin her biri ize yazilir.

H4_BAR_ORANI = esik_kaydet(
    "H4_BAR_ORANI", 16, "YAPISAL",
    "Bir 4H bari kac 15M barini kapsar (4*60/15). Zaman dilimi tanimindan "
    "gelir, istatistiksel secim DEGILDIR.")


def _h4_hizala(n15, n4h):
    """Her 15M bar indeksi icin SON KAPANMIS 4H bar indeksi.

    LOOK-AHEAD YASAGI: 4H bar k, 15M barlarini [16k, 16k+15] araliginda
    KAPSAR ve ancak 16k+15'te KAPANIR. Bu yuzden 15M bar i, k = i//16
    barini GOREMEZ - o bar hala olusmaktadir ve kapanisi/EMA/RSI/ATR degeri
    i'den SONRAKI barlari icerir.

    Dogru esleme: en son KAPANMIS bar = (i + 1) // 16 - 1, 0'a kirpilmis.
    Isinma doneminde (i < 15) henuz kapanmis 4H bari yoktur; 0'a kirpilir
    ve bu donem zaten ISINMA_BARI ile ornek disi birakilir.

    Bu kural test_4h_hizalama_look_ahead_icermez ve
    test_4h_hizalama_son_kapanan_bari_verir ile kilitlidir.
    """
    return [min(max(0, (i + 1) // H4_BAR_ORANI - 1), n4h - 1) for i in range(n15)]


def _ornek_indeksleri(baslangic, bitis, azami=AZAMI_ORNEK):
    """Araligi esit araliklarla en cok `azami` ornege indirger."""
    adaylar = list(range(baslangic, bitis))
    if len(adaylar) <= azami:
        return adaylar
    if azami <= 1:
        return adaylar[-1:]
    adim = (len(adaylar) - 1) / (azami - 1)
    return [adaylar[round(k * adim)] for k in range(azami)]


def _kanal_konumu(barlar, i, pencere=48):
    onceki = barlar[max(0, i - pencere):i]
    if not onceki:
        return 0.0
    en_yuksek = max(b["h"] for b in onceki)
    en_dusuk = min(b["l"] for b in onceki)
    genislik = en_yuksek - en_dusuk
    if genislik <= 0:
        return 0.0
    return kirp((barlar[i]["c"] - en_dusuk) / genislik * 2.0 - 1.0)


def _z(degerler, i, pencere=48):
    gecmis = degerler[max(0, i - pencere):i]
    if len(gecmis) < 5:
        return 0.0
    ort = sum(gecmis) / len(gecmis)
    var = sum((x - ort) ** 2 for x in gecmis) / max(1, len(gecmis) - 1)
    std = math.sqrt(var)
    if std < SABIT_ESIK_TOLERANSI:
        return 0.0
    return kirp((degerler[i] - ort) / std, -5.0, 5.0) / 5.0


def satir_uret(barlar, gostergeler, turev_serisi, i):
    """Bir bar icin dort aileli oznitelik satiri.

    turev_serisi bar basina bir sozluk listesidir (SERI, tek anlik deger
    DEGIL). Gerekce (olculerek bulundu): tek anlik deger tum barlara ayni
    yazilirsa kolon std=0 olur, Olcekleyici onu DOGRU biçimde sabit sayip
    0.0 verir ve turev bilgisi modele HIC ulasmaz - eski sistemin #1
    bulgusunun tekrari. Turev bir seri olarak gelmelidir.

    turev_serisi None ise turev ailesi kapsam=0 ile isaretlenir; bu
    shrinkage uzerinden stake'i dusurur (uydurma yasagi).
    """
    turev = None if turev_serisi is None else turev_serisi[i]
    kapanislar = gostergeler["kapanislar"]
    fiyat = [
        kirp(math.log(kapanislar[i] / kapanislar[i - 1])) if i >= 1 else 0.0,
        kirp(math.log(kapanislar[i] / kapanislar[i - 4])) if i >= 4 else 0.0,
        kirp(math.log(kapanislar[i] / kapanislar[i - 16])) if i >= 16 else 0.0,
        kirp((gostergeler["ema_hizli"][i] - gostergeler["ema_yavas"][i])
             / max(gostergeler["atr"][i], EPSILON) / 2.0),
        kirp((gostergeler["rsi"][i] - 50.0) / 20.0),
        _kanal_konumu(barlar, i),
    ]
    hacimler = gostergeler["hacimler"]
    hacim = [_z(hacimler, i), _z([h * k for h, k in zip(hacimler, kapanislar)], i)]
    if turev is None:
        turev_vek = [0.0, 0.0, 0.0, 0.0, 0.0]      # kapsam=0 -> bilgi YOK
    else:
        turev_vek = [kirp(turev.get("oi_degisim", 0.0) * 5.0),
                     kirp(turev.get("funding_z", 0.0)),
                     kirp(turev.get("taker_dengesi", 0.0)),
                     kirp(turev.get("derinlik_dengesi", 0.0)),
                     1.0]
    oynaklik = [
        kirp(gostergeler["atr"][i] / max(kapanislar[i], EPSILON) * 100.0),
        kirp(_z(gostergeler["atr"], i) * 2.0),
        1.0 if gostergeler["ema_hizli"][i] > gostergeler["ema_yavas"][i] else -1.0,
    ]
    return {"fiyat": fiyat, "hacim": hacim, "turev": turev_vek,
            "oynaklik": oynaklik}


def _gostergeler(barlar):
    kapanislar = [b["c"] for b in barlar]
    return {"kapanislar": kapanislar,
            "hacimler": [b.get("v", 0.0) for b in barlar],
            "ema_hizli": ema(kapanislar, 8),
            "ema_yavas": ema(kapanislar, 21),
            "atr": atr(barlar, 14),
            "rsi": rsi(kapanislar, 14)}


def etiket_uret(barlar, i, atr_serisi, ufuk=ETIKET_UFKU):
    """Iki sinifli etiket: ufuk icinde yon lehine mi hareket etti?

    LONG etiketi (1): hedef once vuruldu. Ayni barda ikisi de = STOP (0).
    """
    olcum = ilk_gecis_olcum(barlar, [i], "LONG", 1.0, 1.0, atr_serisi, ufuk)
    if olcum["p_hedef"] is None:
        return None
    return 1 if olcum["hedef"] > 0 else 0


class BoruHatti:
    """LLM zincirinin 12 halkasini sirayla kosturan orkestrator."""

    def __init__(self, tohum=2026, boyut=16):
        self.tohum = tohum
        self.boyut = boyut
        self.sozluk = TokenSozlugu()
        self.kodlayici = Kodlayici(boyut=boyut, bas_sayisi=2, tohum=tohum)
        self.aile_gomme = {aile: vektor(boyut, (tohum, "aile", aile), 0.06)
                           for aile in AILELER}
        self.zd_gomme = {zd: vektor(boyut, (tohum, "zd", zd), 0.06)
                         for zd in ZAMAN_DILIMLERI}
        self.giris_izdusumu = {aile: matris(boyut, AILELER[aile],
                                            (tohum, "izdusum", aile), 0.10)
                               for aile in AILELER}

    def _durumlar(self, satir_kumesi, olcekleyiciler, indeks, sembol_indeksi=0):
        """Halka 1-3: tokenlar -> gomme + konum kodu.

        HER zaman dilimi icin AYRI token uretilir (spec halka 1: "4H ve 15M
        ayri zaman dilimi tokenlari"). satir_kumesi: {zaman_dilimi: [satir]},
        olcekleyiciler: {zaman_dilimi: Olcekleyici}. 4H satirlari 15M
        indeksine hizalanmistir (look-ahead yok).
        """
        durumlar = []
        for gecikme in range(GECIKME_SAYISI - 1, -1, -1):
            j = max(0, indeks - gecikme)
            for zd in sorted(satir_kumesi):
                satirlar = satir_kumesi[zd]
                olcekleyici = olcekleyiciler[zd]
                for aile in AILELER:
                    olcekli = olcekleyici.donustur(aile, satirlar[j][aile])
                    icerik = matvec(self.giris_izdusumu[aile], olcekli)
                    kimlik = self.sozluk.kimlik("S", zd, aile, gecikme)
                    token_gomme = vektor(self.boyut,
                                         (self.tohum, "token", kimlik), 0.05)
                    durumlar.append(topla_vek(
                        icerik, token_gomme, self.aile_gomme[aile],
                        self.zd_gomme[zd],
                        zaman_konumu(gecikme, self.boyut),
                        sembol_konumu(sembol_indeksi, self.boyut)))
        return durumlar

    def calistir(self, paket):
        iz = {}
        barlar = paket["barlar15"]
        iz["halka_0"] = {"ad": "ham girdi", "bar_sayisi": len(barlar),
                         "dolu_kanal": paket["dolu_kanal"],
                         "toplam_kanal": paket["toplam_kanal"]}

        gost = _gostergeler(barlar)
        turev_serisi = paket.get("turev_serisi")
        satir_kumesi = {"15m": [satir_uret(barlar, gost, turev_serisi, i)
                                for i in range(len(barlar))]}

        # 4H: kendi gostergeleriyle hesaplanip 15M indeksine HIZALANIR.
        # Hizalama look-ahead icermez: her 15M bari icin SON KAPANMIS 4H bari.
        barlar4h = paket.get("barlar4h")
        h4_var = bool(barlar4h)
        if h4_var:
            gost4 = _gostergeler(barlar4h)
            h4_satir = [satir_uret(barlar4h, gost4, None, i)
                        for i in range(len(barlar4h))]
            eslesme = _h4_hizala(len(barlar), len(barlar4h))
            satir_kumesi["4h"] = [h4_satir[eslesme[i]] for i in range(len(barlar))]
        # 4H YOKSA: notr 0.0 satir ENJEKTE EDILMEZ (uydurma yasagi) ve 15M
        # satiri KOPYALANMAZ. O zaman dilimi icin token HIC uretilmez;
        # bedeli kapsam dususu olarak shrinkage'a yansir (asagida).
        etkin_zd = [zd for zd in ZAMAN_DILIMLERI if zd in satir_kumesi]
        iz["halka_1"] = {"ad": "tokenizasyon", "aile_sayisi": len(AILELER),
                         "gecikme": GECIKME_SAYISI,
                         "zaman_dilimi_sayisi": len(etkin_zd),
                         "h4_var": h4_var,
                         "token_sayisi": (GECIKME_SAYISI * len(AILELER)
                                          * len(etkin_zd))}

        baslangic = ISINMA_BARI
        bitis = len(barlar) - ETIKET_UFKU - 1
        tum_indeksler = _ornek_indeksleri(baslangic, bitis,
                                          paket.get("azami_ornek", AZAMI_ORNEK))
        bolme = kronolojik_bol(tum_indeksler, ETIKET_UFKU, EMBARGO)
        # Bos bolmede "sizinti: False" demek fail-OPEN rapordur: olculemeyen
        # sey "yok" diye raporlanamaz.
        bolme_bos = not (bolme["train"] and bolme["kalibrasyon"] and bolme["test"])
        iz["halka_11"] = {"ad": "otoregresif/bolme", "train": len(bolme["train"]),
                          "kalibrasyon": len(bolme["kalibrasyon"]),
                          "test": len(bolme["test"]), "atilan": bolme["atilan"],
                          "not": bolme["not"] or ("yetersiz ornek - bolme dejenere"
                                                  if bolme_bos else ""),
                          "sizinti": (None if bolme_bos
                                      else sizinti_var_mi(bolme, ETIKET_UFKU,
                                                          GECIKME_SAYISI))}

        kesim = (bolme["train"][-1] if bolme["train"]
                 else max(1, len(barlar) // 2))
        olcekleyiciler = {}
        for zd in etkin_zd:             # her zaman dilimi KENDI istatistigiyle
            o = Olcekleyici()
            o.fit(satir_kumesi[zd], kesim)
            olcekleyiciler[zd] = o
        iz["halka_2"] = {"ad": "embedding/olcekleme", "kesim": kesim,
                         "sabit_kolon": {zd: len(olcekleyiciler[zd].sabit_kolonlar)
                                         for zd in etkin_zd}}
        iz["halka_3"] = {"ad": "konum kodu", "zaman_ekseni": True,
                         "sembol_ekseni": True, "faz": SEMBOL_EKSENI_FAZI}
        iz["halka_4"] = {"ad": "causal attention", "bas": self.kodlayici.bas_sayisi,
                         "maske": True}
        iz["halka_5"] = {"ad": "FFN", "genislik": self.boyut * 2}

        def ornek(i):
            x = self.kodlayici.ileri(self._durumlar(satir_kumesi, olcekleyiciler, i))
            y = etiket_uret(barlar, i, gost["atr"])
            return None if y is None else {"x": x, "y": y}

        train = [o for o in (ornek(i) for i in bolme["train"]) if o]
        kal = [o for o in (ornek(i) for i in bolme["kalibrasyon"]) if o]
        test = [o for o in (ornek(i) for i in bolme["test"]) if o]

        basliklar = []
        for gorus in range(3):
            b = Baslik(boyut=self.boyut, tohum=self.tohum + 100 * (gorus + 1))
            if train:
                alt = [train[k] for k in range(gorus, len(train), 3)] or train
                b.egit(alt, devir=40, ogrenme_hizi=0.15)
            basliklar.append(b)
        iz["halka_6"] = {"ad": "logit basligi", "train_ornek": len(train),
                         "gorus": len(basliklar)}

        kalib = kalibrasyon_sec(kal, basliklar) if kal else {
            "yontem": "YOK", "T": 1.0, "fn": None, "nll": None, "sinirda": False}
        iz["halka_7"] = {"ad": "kalibrasyon", "yontem": kalib["yontem"],
                         "T": kalib["T"], "nll": kalib["nll"],
                         "sinirda": kalib["sinirda"]}

        ciftler = []
        for o in test:
            p = topluluk_olasilik(o["x"], basliklar, kalib["T"])["p"][0]
            if kalib["fn"] is not None:
                p = kalib["fn"](p)
            ciftler.append((p, o["y"]))
        dogru = sum(1 for p, y in ciftler if (1 if p >= 0.5 else 0) == y)
        iz["halka_8"] = {"ad": "softmax/yon ekseni", "test_ornek": len(ciftler),
                         "dogru": dogru,
                         "ece": ece(ciftler) if ciftler else None,
                         "mce": mce(ciftler) if ciftler else None,
                         "brier": brier(ciftler) if ciftler else None,
                         "auroc": auroc(ciftler) if ciftler else None,
                         "wilson": wilson_araligi(dogru, len(ciftler))}

        son = len(barlar) - 1
        x_son = self.kodlayici.ileri(self._durumlar(satir_kumesi, olcekleyiciler, son))
        top = topluluk_olasilik(x_son, basliklar, kalib["T"])
        p_ham = top["p"][0]
        if kalib["fn"] is not None:
            p_ham = kalib["fn"](p_ham)
        iz["halka_9"] = {"ad": "decoding", "p_long": p_ham, "hold": False}
        iz["halka_10"] = {"ad": "self-consistency", "uzlasi": top["uzlasi"],
                          "dagilim": top["dagilim"],
                          "T_karari_cevirir": sicaklik_karari_cevirir_mi(
                              [b.logit(x_son) for b in basliklar])}

        ece_grup = grup_ece({"test": ciftler}) if ciftler else {
            "en_kotu": (None, None)}

        # KAPSAM h4_var'dan TURETILIR: modele ULASMAYAN veri kapsami
        # BUYUTEMEZ. Paket 4H kanalini dolu sayiyorsa ve 4H gercekten
        # boru hattina girmediyse fail-closed olarak bir azaltilir.
        dolu_kanal = paket["dolu_kanal"]
        if not h4_var:
            dolu_kanal = max(0, dolu_kanal - 1)
            iz["halka_0"]["h4_kanali_dusuldu"] = True
        karar = karar_uret({
            "sembol": paket["sembol"], "barlar": barlar, "atr_serisi": gost["atr"],
            "indeksler": bolme["test"] or tum_indeksler[-40:],
            "p_ham": p_ham, "dogru": dogru, "toplam": len(ciftler),
            "ece_enkotu": ece_grup["en_kotu"][1],
            "dolu_kanal": dolu_kanal, "toplam_kanal": paket["toplam_kanal"],
            "giris": barlar[son]["c"], "atr": gost["atr"][son],
            "likidasyon": paket.get("likidasyon"),
            "kaldirac_azami": paket.get("kaldirac_azami"),
            "komisyon": paket.get("komisyon", 0.0004),
            "kayma": paket.get("kayma", 0.0005),
            "funding": paket.get("funding", 0.0),
            "lam": paket.get("lam", 1.0)})
        iz["halka_12"] = {"ad": "detokenizasyon", "giris": karar["giris"],
                          "stop": karar["stop"], "hedef": karar["hedef"],
                          "R": karar["R"], "f": karar["stake"]["f"]}
        karar["iz"] = iz
        karar["kalibrasyon"] = iz["halka_8"]
        karar["adaptor"] = paket.get("adaptor")
        return karar


# ---------------------------------------------------------------- BOLUM 10
# Cikti, kagit defteri, CLI. GERCEK EMIR YOK.


def metin_rapor(karar):
    g, s = karar["geometri"], karar["stake"]
    satirlar = [
        "=" * 78,
        f"{karar['sembol']} | {SURUM} | YALNIZ KARAR-DESTEK (gercek emir YOK)",
        f"YON: {karar['yon']}   (p_ham={karar['p_ham']:.4f} -> "
        f"p_kullanilan={karar['p_kullanilan']:.4f})",
        f"SHRINKAGE s={karar['shrinkage']['s']:.4f} "
        f"(kanit={karar['shrinkage']['s_kanit']:.3f} "
        f"kalibrasyon={karar['shrinkage']['s_kalibrasyon']:.3f} "
        f"kapsam={karar['shrinkage']['s_kapsam']:.3f})",
        f"GEOMETRI stop_k={g['stop_k']} hedef_k={g['hedef_k']} "
        f"R={g['R']:.4f} p_hedef={g['p_hedef']} n={g['n']}",
        f"basabas p (f*>0 icin gereken) = {g['basabas_p']}",
        f"SEVIYELER giris={karar['giris']:.8g} stop={karar['stop']:.8g} "
        f"hedef={karar['hedef']:.8g}",
        f"STAKE f*={s['f']:.6f}  (f_max={s['f_max']:.6f}, "
        f"kirpildi={'EVET' if s['kirpildi'] else 'hayir'})",
        "  lambda: " + "  ".join(f"{lam}->{v['f']:.6f}"
                                 for lam, v in s["lambda_tablosu"].items()),
    ]
    if g.get("not"):
        satirlar.append(f"NOT: {g['not']}")
    if s["f"] == 0.0:
        satirlar.append("f*=0: yon ve seviyeler yine uretildi; bahis buyuklugu sifir.")
    return "\n".join(satirlar)


def defter_guncelle(durum, karar, bar):
    """Yerel kagit defteri. f*=0 ise pozisyon ACILMAZ (bahis sifir)."""
    yeni = {"sermaye": durum["sermaye"],
            "pozisyonlar": dict(durum.get("pozisyonlar", {}))}
    sembol = karar["sembol"]
    mevcut = yeni["pozisyonlar"].get(sembol)
    if mevcut:
        if mevcut["yon"] == "LONG":
            cikis = (mevcut["stop"] if bar["l"] <= mevcut["stop"]
                     else (mevcut["hedef"] if bar["h"] >= mevcut["hedef"] else None))
        else:
            cikis = (mevcut["stop"] if bar["h"] >= mevcut["stop"]
                     else (mevcut["hedef"] if bar["l"] <= mevcut["hedef"] else None))
        if cikis is not None:
            isaret = 1.0 if mevcut["yon"] == "LONG" else -1.0
            yeni["sermaye"] += isaret * (cikis - mevcut["giris"]) * mevcut["miktar"]
            yeni["pozisyonlar"].pop(sembol, None)

    if sembol not in yeni["pozisyonlar"] and karar["stake"]["f"] > 0.0:
        risk_tutari = yeni["sermaye"] * karar["stake"]["f"]
        mesafe = abs(karar["giris"] - karar["stop"]) or EPSILON
        yeni["pozisyonlar"][sembol] = {
            "yon": karar["yon"], "giris": karar["giris"], "stop": karar["stop"],
            "hedef": karar["hedef"], "miktar": risk_tutari / mesafe}
    return yeni


_OZ_TEST_KOSUYOR = False


def oz_test_kosuyor():
    """Oz-test icinden cagrildik mi? Ozyinelemeyi kesmek icin."""
    return _OZ_TEST_KOSUYOR


def _oz_test():
    """Gomulu hizli denetim (Pydroid 3 icin).

    Ozyineleme korumasi: test paketi main(--self-test) cagirirsa bu bayrak
    sayesinde ic ice kosu YAPILMAZ.
    """
    global _OZ_TEST_KOSUYOR
    if _OZ_TEST_KOSUYOR:
        return 0
    import unittest as _ut
    try:
        import test_llm_trading_v3 as _t
    except ImportError:
        print("test dosyasi bulunamadi - oz-test atlandi")
        return 1
    _OZ_TEST_KOSUYOR = True
    try:
        sonuc = _ut.TextTestRunner(verbosity=1).run(
            _ut.defaultTestLoader.loadTestsFromModule(_t))
    finally:
        _OZ_TEST_KOSUYOR = False
    return 0 if sonuc.wasSuccessful() else 1


def main(argv=None):
    import argparse
    ayristirici = argparse.ArgumentParser(description=SURUM)
    ayristirici.add_argument("--self-test", action="store_true")
    ayristirici.add_argument("--esikler", action="store_true")
    ayristirici.add_argument("--lam", type=float, default=1.0)
    args = ayristirici.parse_args(argv)
    if args.self_test:
        return _oz_test()
    if args.esikler:
        print(esik_raporu())
        return 0
    print(f"{SURUM}: canli kosu icin ag erisimi gerekir.")
    print("Bu ortamda: --self-test (testler) veya --esikler (esik beyani).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
