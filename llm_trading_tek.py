#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm_trading_tek.py - TEK DOSYA: sistem + 236 test + canli veri katmani.

Ek bagimlilik YOKTUR (yalniz Python standart kutuphanesi).
Pydroid 3'te tek dosya olarak calisir.

KULLANIM
--------
  python llm_trading_tek.py --self-test     236 testi kosturur
  python llm_trading_tek.py --esikler       her sabiti kaynak+gerekcesiyle basar
  python llm_trading_tek.py --oz-rapor r.json   sentetik uctan uca kosu -> JSON
  python llm_trading_tek.py --canli BTCUSDT     GERCEK Binance verisiyle kosar
  python llm_trading_tek.py --ornek         AGSIZ ornek kosu (sahte veriyle)

GUVENLIK SINIRI (degismez)
--------------------------
Bu dosyada kimlik anahtari, gizli anahtar, imzalama, imzali uc, emir ucu
ya da iptal ucu YOKTUR ve eklenmemelidir. Yalniz PUBLIC GET piyasa
verisi okunur; kagit defteri YERELDIR. Bu sinir bir TESTLE korunur
(GuvenlikTesti.test_yasakli_desen_yok motor bolumunu tarar).
Yalniz karar-destek; canli/otomatik emir DAHIL DEGILDIR.
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

BOLME_ORANLARI = esik_kaydet(
    "BOLME_ORANLARI", (0.6, 0.2, 0.2), "YAPISAL",
    "train / kalibrasyon / test paylari. Tek yerde beyan edilir cunku "
    "AZAMI_ORNEK tabani bu paylardan TURETILIR; iki yerde ayri yazilirsa "
    "butce sessizce yarismayi imkansiz kilar.")

AZAMI_ORNEK = esik_kaydet(
    "AZAMI_ORNEK", int(math.ceil(2 * ASGARI_OLCUM / BOLME_ORANLARI[1])), "YAPISAL",
    "HESAP TAVANI (istatistik esigi DEGIL). Deger, kalibrasyon diliminin "
    "purge'DEN ONCE 2*ASGARI_OLCUM'e ulastigi nokta: 40/0.2 = 200. "
    "DIKKAT - BU TEK BASINA YARISMAYI ACMAZ ve acmasi da beklenmez: purge "
    "her sinirdan en az bir ornek aldigi icin purge SONRASI kal DAIMA "
    "40'in altina duser. Yani bu sayi 'yarisma kosar' demez, 'hesap tavani "
    "budur' der. Yarismanin GERCEKTEN kosmasi icin gereken butce sabit "
    "DEGILDIR, veriye baglidir ve `gereken_ornek_butcesi()` ile her kosuda "
    "TURETILIP ize yazilir (olculdu: 12000 barda 356, 30000 barda 243, "
    "6000 barda 1628 ornek gerekiyor). Tavan, yarismayi acmak icin "
    "BUYUTULMEZ - esigi geciren degere cekmek asiri-uyumdur; cagiran taraf "
    "gereken butceyi izden okuyup paketle bilerek verebilir. Hedef ortam "
    "Pydroid 3 (telefon): 200 ornek + 12000 bar = 1.26 s.")

LIKIDASYON_GUVENLIK_PAYI = esik_kaydet(
    "LIKIDASYON_GUVENLIK_PAYI", 0.5, "VARSAYIM",
    "Likidasyon mesafesinin ne kadarina kadar stake alinabilecegi. Kalibre "
    "EDILMEDI. 0.5, likidasyona giden yolun yarisinda durmak demektir; "
    "muhafazakar taraf. Olcum yolu: gerceklesmis en kotu bar-ici sapmanin "
    "dagilimindan ust yuzdelik.")

H4_BAR_ORANI = esik_kaydet(
    "H4_BAR_ORANI", 16, "YAPISAL",
    "Bir 4H bari kac 15M barini kapsar (4*60/15). Zaman dilimi tanimindan "
    "gelir, istatistiksel secim DEGILDIR.")


YUVARLANAN_PENCERE = esik_kaydet(
    "YUVARLANAN_PENCERE", 48, "YAPISAL",
    "Yuvarlanan istatistik pencereleri (_z, _kanal_konumu) icin bar sayisi. "
    "Tek yerde beyan edilir cunku girdi erisimi - dolayisiyla purge boslugu - "
    "bu sayidan TURETILIR; iki yerde ayri ayri yazilirsa erisim beyani "
    "sessizce gercekten kucuk kalir (fail-open sizinti raporu).")

EMA_HIZLI_PERIYODU = esik_kaydet(
    "EMA_HIZLI_PERIYODU", 8, "VARSAYIM",
    "Hizli EMA periyodu. Kalibre EDILMEDI - yaygin bir kisa-vade secimi. "
    "Erisim aritmetigine girer. Olcum yolu: periyoda karsi holdout AUROC.")

EMA_YAVAS_PERIYODU = esik_kaydet(
    "EMA_YAVAS_PERIYODU", 21, "VARSAYIM",
    "Yavas EMA periyodu. Kalibre EDILMEDI. oznitelik_penceresi'ne girdigi "
    "icin dogrudan purge boslugunu ve kalan ornek sayisini etkiler.")

ATR_PERIYODU = esik_kaydet(
    "ATR_PERIYODU", 14, "VARSAYIM",
    "ATR periyodu. Kalibre EDILMEDI. En uzun erisim zinciri bundan gecer "
    "(_z(atr) = YUVARLANAN_PENCERE + ATR_PERIYODU), yani purge boslugunun "
    "belirleyicisidir.")

RSI_PERIYODU = esik_kaydet(
    "RSI_PERIYODU", 14, "VARSAYIM",
    "RSI periyodu. Kalibre EDILMEDI.")

EN_UZUN_GETIRI_GECIKMESI = esik_kaydet(
    "EN_UZUN_GETIRI_GECIKMESI", 16, "YAPISAL",
    "Log getiri ozniteliklerinin en uzun gecikmesi (1, 4, 16). 16 = bir 4H "
    "barin 15M karsiligi; zaman dilimi tanimindan gelir. Erisim "
    "aritmetigine girer.")

EMA_KESME_KATI = esik_kaydet(
    "EMA_KESME_KATI", 2, "YAPISAL",
    "EMA'nin ustel agirlik profilinin kac PERIYOT sonra kesilecegi. "
    "Istatistiksel secim DEGIL, erisim aritmetiginden gelir: en uzun EMA "
    "periyodu 21'dir, 21*2 = 42 <= YUVARLANAN_PENCERE (48). Yani EMA, "
    "erisime zaten var olan 48 barlik pencerenin OTESINDE hicbir sey "
    "EKLEMEZ - kesme kati buyutulurse purge boslugu buyur ve ayni veriyle "
    "daha az ornek kalir. Kesilen kuyrugun agirligi normalize edilerek "
    "kalan barlara oranli dagitilir (olculdu: periyot=21 icin kesilen "
    "agirlik ~1.8e-2).")

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

def shrinkage_katsayisi(dogru, toplam, ece_enkotu, dolu_kanal, toplam_kanal,
                        taban_oran=0.5, ece_tek_bin=False,
                        sicaklik_sinirda=False):
    """s = s_kanit * s_kalibrasyon * s_kapsam, hepsi [0,1].

    OLCULEN UYARI KAPIYA BAGLANIR. Bir uyariyi olcup hukme baglamamak,
    olcmemekle aynidir - ustelik daha kotusudur, cunku "olctuk" denir.
    Uc kapi:

    (1) taban_oran: yon dogrulugu %50'ye DEGIL, kumenin KENDI cogunluk
        oranina gore olculur. Dengesiz etikette (etiket "16 bar icinde
        +1 ATR mi -1 ATR mi" - trend penceresinde carpiktir) sabit-yonlu
        bir tahminci taban orani kadar dogruluk alir; bu BECERI DEGILDIR
        ve stake kazanmamalidir.
    (2) ece_tek_bin: tum guvenler tek kovaya duserse ECE hicbir
        kalibrasyon bilgisi TASIMAZ (ECE == MCE olur). Boyle bir ECE'den
        pozitif carpan uretmek fail-open'dir.
    (3) sicaklik_sinirda: T izgara kenarinda bulunduysa fit TANIMSIZDIR
        (optimum izgaranin disinda olabilir). Tanimsiz bir fit kalibrasyon
        kaniti sayilmaz.
    """
    taban = kirp(float(taban_oran), 0.5, 1.0)
    alt, _ = wilson_araligi(dogru, toplam)
    # Taban 0.5 iken bu ifade eski `2*(alt-0.5)` formuluyle OZDESTIR.
    pay = max(0.0, 1.0 - taban)
    s_kanit = 0.0 if pay <= 0.0 else kirp((alt - taban) / pay, 0.0, 1.0)

    if ece_enkotu is None or ece_tek_bin or sicaklik_sinirda:
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
    """Stake sozlesmesinin TEK garanti noktasi: kanit yoksa f* TAM OLARAK 0.

    p_ham kanit gucune gore bahsin basabas olasiligina daraltilir; s=0 iken
    p = p0 olur ve Kelly TAM aritmetikte 0 doner.

    KAYAN NOKTA KORKULUGU (olculdu): p0 = a/(a+b) iken Kelly payi
    p0*b - (1-p0)*a ancak TAM aritmetikte sadelesir. float64'te 165 ayri
    (R, maliyet, p) kombinasyonunda 1e-16 mertebesinde artik kaliyor ve
    bu artik ZARARSIZ DEGIL: defter_guncelle `f > 0` kapisiyla POZISYON
    ACIP sembolun yuvasini isgal ediyor, metin_rapor ise `f == 0` kapisiyla
    "bahis sifir" satirini bastiriyordu - iki tuketici ZIT hukum veriyordu.

    Bu yuzden s <= 0 dalinda f DOGRUDAN 0.0 doner. Bu bir esik DEGIL,
    TANIM: s = 0 "kanit yok" demektir ve kanit yokken bahis sifirdir;
    kirpma toleransi secilmis bir sayi olsaydi ESIK_KAYNAGI'na girmesi
    gerekirdi - burada secilmis sayi YOK.
    """
    p0 = basabas_p(b, a)
    if p0 is None:                      # kazanc kanadi yok: bahis imkansiz
        return {"f": 0.0, "p_kullanilan": None, "p0": None,
                "not": "kazanc kanadi <= 0 - bahis matematiksel olarak imkansiz"}
    s = kirp(s, 0.0, 1.0)
    p_kullanilan = daralt(p_ham, s, hedef=p0)
    if s <= 0.0:
        return {"f": 0.0, "p_kullanilan": p_kullanilan, "p0": p0,
                "not": "kanit yok (s=0) - f* tanim geregi 0"}
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
        # TEK KAYNAK: olculen bariyerler ile YAYINLANAN seviyeler AYNI
        # fonksiyondan gelir. Iki ayri hesap, p_hedef'in yayinlanandan
        # BASKA bariyerler icin olculmesi demektir - olcum ile ciktinin
        # ayni nesne olmasi gereken tam nokta.
        _sev = seviyeler(giris, atr_deger, yon, stop_k, hedef_k)
        stop_seviye, hedef_seviye = _sev["stop"], _sev["hedef"]

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


def _aday_degerlendir(stop_k, hedef_k, R, cost_r, b, a, olcum, p_yon, lam):
    """Bir (stop_k, hedef_k) adayini puanlar.

    SECIM YANLILIGI KORKULUGU: 11 aday AYNI orneklem uzerinde yarisiyor ve
    kazanan ayni orneklemle puanlaniyor. Nokta tahmini uzerinden argmax
    gurultuyu kenar sanir - olculdu ki kazanan basabasi ~0.016 SE ile
    geciyordu. Bu yuzden secim ve stake, p_hedef'in NOKTA tahmininden
    degil WILSON ALT SINIRINDAN uretilir. Deyim modulun kendisinden:
    shrinkage_katsayisi da kaniti alt sinirla olcer. Az ornekli aday
    boylece KENDILIGINDEN cezalanir (alt sinir n ile daralir); ayri bir
    n-cezasi sabiti UYDURULMAZ.
    """
    p_hedef_alt, _ = wilson_araligi(
        int(round(olcum["p_hedef"] * olcum["n"])), olcum["n"])
    # Karar olasiligi: modelin yon olasiligi ile olculen ilk-gecis
    # birlestirilir (ikisi de ayni olayi tahmin eder; geometrik ortalama
    # muhafazakardir).
    p_bilesik = math.sqrt(max(0.0, p_yon) * max(0.0, olcum["p_hedef"]))
    p_bilesik_alt = math.sqrt(max(0.0, p_yon) * max(0.0, p_hedef_alt))
    f = kelly_asimetrik(p_bilesik_alt, b, a) * lam
    return {"stop_k": stop_k, "hedef_k": hedef_k, "R": R, "cost_r": cost_r,
            "b": b, "a": a, "p_hedef": olcum["p_hedef"],
            "p_hedef_alt": p_hedef_alt, "p_bilesik": p_bilesik,
            "p_bilesik_alt": p_bilesik_alt,
            "n": olcum["n"], "f": f,
            "elog": beklenen_log(p_bilesik_alt, f, b, a),
            "basabas_p": basabas_p(b, a), "not": ""}


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
        aday = _aday_degerlendir(stop_k, hedef_k, R, cost_r, b, a,
                                 olcum, p_yon, lam)
        denenen.append(aday)
        if en_iyi is None or aday["elog"] > en_iyi["elog"]:
            en_iyi = aday

    if en_iyi is None:
        varsayilan = IZGARA[5]  # (1.5, 3.0) - rapor icin notr referans
        return {"stop_k": varsayilan[0], "hedef_k": varsayilan[1],
                "R": varsayilan[1] / varsayilan[0], "p_hedef": None,
                "p_hedef_alt": None, "p_bilesik": None, "p_bilesik_alt": None,
                "n": 0, "f": 0.0, "elog": None,
                "cost_r": None, "b": None, "a": None, "basabas_p": None,
                "not": "OLCUM YOK - yeterli ilk-gecis ornegi yok (fail-closed)",
                "denenen": denenen}

    # KOPYA sart: en_iyi zaten denenen'in bir ELEMANI. Dogrudan
    # `en_iyi["denenen"] = denenen` yazmak kendine referans yaratir ve
    # karar JSON'a SERILESEMEZ. Kusur yalniz bir geometri KAZANDIGINDA
    # ortaya cikar - yani sistem dogru calistiginda; fail-closed dal
    # (en_iyi is None) taze bir sozluk dondugu icin gizli kaliyordu.
    en_iyi = dict(en_iyi)
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


_KLINE_ALANLARI = (
    ("KLINE_ACILIS_ZAMANI", 0), ("KLINE_ACILIS", 1), ("KLINE_YUKSEK", 2),
    ("KLINE_DUSUK", 3), ("KLINE_KAPANIS", 4), ("KLINE_HACIM", 5),
    ("KLINE_TAKER_ALIS", 9),
)
for _ad, _i in _KLINE_ALANLARI:
    globals()[_ad] = esik_kaydet(
        _ad, _i, "YAPISAL",
        "Binance USD-M kline satirindaki alan indeksi (12 alanli liste). "
        "Borsa dokumantasyonundan gelir; istatistiksel secim DEGILDIR. "
        "Yanlis indeks sessiz veri bozulmasi demektir, o yuzden beyanli.")
del _ad, _i

# Bu kanallar tek ANLIK deger dondurur (seri DEGIL). Bir anlik degeri
# tum barlara yazmak kolonun std'sini 0 yapar; Olcekleyici onu dogru
# bicimde sifirlar ve bilgi modele HIC ulasmaz - ama kapsam skoru "dolu"
# saymaya devam ederdi. Bu fail-open'dir, o yuzden kapsama SAYILMAZLAR.
ANLIK_KANALLAR = ("funding", "derinlik")


def _kline_cevir(satirlar):
    """Binance kline listesini bar sozluklerine cevirir."""
    barlar = []
    for s in satirlar or []:
        barlar.append({
            "t": int(s[KLINE_ACILIS_ZAMANI]),
            "o": float(s[KLINE_ACILIS]), "h": float(s[KLINE_YUKSEK]),
            "l": float(s[KLINE_DUSUK]), "c": float(s[KLINE_KAPANIS]),
            "v": float(s[KLINE_HACIM]),
            "taker_alis": float(s[KLINE_TAKER_ALIS]),
        })
    return barlar


def _seri_hizala(kayitlar, barlar, alan, zaman_alani="timestamp"):
    """Zaman damgali bir kanali 15M bar indeksine hizalar.

    Hizalama GECMISE dogru yapilir: her bar icin zamani <= bar acilisi
    olan SON kayit. Ileri doldurma YOK - gelecek kayit gecmis bara
    yazilirsa look-ahead sizintisi olur.
    """
    if not kayitlar:
        return None
    sirali = sorted(kayitlar, key=lambda k: int(k.get(zaman_alani, 0)))
    cikti, j, son = [], 0, None
    for bar in barlar:
        while j < len(sirali) and int(sirali[j].get(zaman_alani, 0)) <= bar["t"]:
            son = sirali[j]
            j += 1
        cikti.append(None if son is None else float(son[alan]))
    return cikti


def _turev_serisi_kur(barlar15, kanallar):
    """Turev kanallarini bar basina sozluk SERISINE cevirir.

    Anlik kanallar (funding, derinlik) SERIYE CEVRILMEZ: tek deger tum
    barlara yazilamaz (bkz. ANLIK_KANALLAR). CVD kullanicinin KENDI
    kline'indan cevrimdisi hesaplanir: delta = 2*taker_alis - hacim.
    """
    oi = _seri_hizala(kanallar.get("oi"), barlar15, "sumOpenInterest")
    taker = _seri_hizala(kanallar.get("taker"), barlar15, "buySellRatio")
    seri = []
    for i, bar in enumerate(barlar15):
        kayit = {}
        if oi and oi[i] is not None and i > 0 and oi[i - 1]:
            kayit["oi_degisim"] = kirp((oi[i] - oi[i - 1]) / oi[i - 1] * 100.0)
        if taker and taker[i] is not None:
            kayit["taker_dengesi"] = kirp((taker[i] - 1.0))
        hacim = bar["v"] or EPSILON
        kayit["cvd"] = kirp((2.0 * bar["taker_alis"] - hacim) / hacim)
        seri.append(kayit)
    return seri


def paket_kur(sembol, toplama, **ek):
    """veri_topla ciktisini BoruHatti.calistir paketine cevirir.

    Bu, ham borsa JSON'u ile boru hatti arasindaki TEK kopru. Kline yoksa
    fail-closed: ValueError yukselir, uydurma bar URETILMEZ.

    KAPSAM DURUSTLUGU: yalniz SERI olarak modele ULASAN kanallar dolu
    sayilir. Anlik kanallar (funding, derinlik) sayilmaz ve `anlik_kanallar`
    alaninda BEYAN edilir - modele ulasmayan veri stake'i buyutemez.
    """
    kanallar = toplama.get("kanallar") or {}
    barlar15 = _kline_cevir(kanallar.get("kline_15m"))
    if not barlar15:
        raise ValueError("kline_15m YOK - uydurma bar uretilmez (fail-closed)")
    barlar4h = _kline_cevir(kanallar.get("kline_4h")) or None

    seri_kanallar = [k for k in KANALLAR
                     if k not in ANLIK_KANALLAR and kanallar.get(k) is not None]
    anlik = sorted(k for k in ANLIK_KANALLAR if kanallar.get(k) is not None)

    paket = {"sembol": sembol, "barlar15": barlar15, "barlar4h": barlar4h,
             "turev_serisi": _turev_serisi_kur(barlar15, kanallar),
             "dolu_kanal": len(seri_kanallar),
             "toplam_kanal": len(KANALLAR),
             "anlik_kanallar": anlik,
             "adaptor": toplama.get("adaptor"),
             "azami_ornek": AZAMI_ORNEK}
    paket.update(ek)
    return paket


def veri_topla(sembol, adaptorler, getir_fn):
    """TUM adaptorleri dener, EN YUKSEK kapsamli olani secer.

    "Ilk kapsam>0 vereni al" YANLISTI: kapsam dogrudan stake'i belirler
    (s_kapsam), yani 1/6 kanal donduren ana adaptorde kalmak 6/6
    donebilecek yedegi hic denememek demektir - olculebilir bilgiyi
    gerekcesiz atmak. Esitlikte ILK adaptor korunur (ana adaptor
    tercihi bozulmasin).
    """
    en_iyi = None
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
        aday = {"adaptor": adaptor.ad, "kanallar": kanallar, "kapsam": kapsam,
                "dusen": dusen, "yedege_dusuldu": sira > 0}
        if kapsam >= 1.0:               # tam kapsam: aramaya gerek yok
            return aday
        if en_iyi is None or kapsam > en_iyi["kapsam"]:
            en_iyi = aday

    if en_iyi is not None and en_iyi["kapsam"] > 0.0:
        return en_iyi
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


def oznitelik_penceresi():
    """Bir OZNITELIK SATIRININ geriye okudugu azami bar sayisi (ust sinir).

    Zincirleri tek tek toplamak sart: `_z(atr, i)` once atr[i-48:i]'yi okur,
    her atr[j] de kendi 14 barini okur -> zincir 48 + 14 = 62 bar. En uzun
    zincir budur. Token gecikmesini saymak (eski hali) bu zinciri GORMEZ ve
    erisimi 4 bar sanip sizintiyi "yok" diye raporlar.
    """
    z = gosterge_penceresi("z")
    atr_p = gosterge_penceresi("atr", ATR_PERIYODU)
    return max(
        gosterge_penceresi("kanal"),                       # _kanal_konumu
        z,                                                 # _z(hacim)
        z + atr_p,                                         # _z(atr) zinciri
        gosterge_penceresi("rsi", RSI_PERIYODU),           # rsi
        EN_UZUN_GETIRI_GECIKMESI,                          # log getiri
        max(gosterge_penceresi("ema", EMA_YAVAS_PERIYODU), atr_p),  # ema/atr
    )


def girdi_erisimi(gecikme_sayisi=None, h4_var=True, bar_orani=None):
    """Bir ORNEGIN geriye dogru okudugu 15M bar sayisi (beyanli ust sinir).

    Iki bilesen carpisir:
      (1) TOKEN GECIKMESI - ornek `gecikme_sayisi` adet satir gorur, en
          eskisi (gecikme_sayisi - 1) bar geridedir.
      (2) OZNITELIK PENCERESI - her satir kendisi W bar geriye okur.
    Toplam 15M erisimi (gecikme-1) + W'dir.

    4H tarafi ayrica bar_orani ile buyur: en eski 4H token'in kendi penceresi
    W adet 4H bari, yani bar_orani*W adet 15M barini ozetler; ustune 4H
    hizalamasinin kendi gecikmesi (2*bar_orani - 1) biner.

    Purge/embargo bu sayidan turetilir. Daha kisa bir pencereyle yapilan
    sizinti denetimi sizintiyi OLCEMEZ, "yok" diye raporlar (fail-open).
    """
    gecikme = GECIKME_SAYISI if gecikme_sayisi is None else int(gecikme_sayisi)
    oran = H4_BAR_ORANI if bar_orani is None else int(bar_orani)
    W = oznitelik_penceresi()
    erisim = max(0, gecikme - 1) + W
    if h4_var:
        erisim = max(erisim, max(0, gecikme - 1) + (2 * oran - 1) + oran * W)
    return erisim


def gereken_ornek_butcesi(acikllik, bosluk, kal_orani, hedef_kal):
    """Kalibrasyon yarismasinin KOSABILMESI icin gereken ornek sayisi.

    "Ulasilamaz" demek yeterli degildir - NE KADAR veriyle ulasilir,
    TURETILIR:
        adim               = acikllik / azami
        sinir basina kayip = bosluk / adim = bosluk * azami / acikllik
        kal dilimi         = kal_orani * azami
        kal (purge sonrasi) = azami * (kal_orani - bosluk / acikllik)
        gereken: >= hedef_kal
        => azami >= hedef_kal / (kal_orani - bosluk / acikllik)

    Payda <= 0 ise HICBIR butce yetmez (purge, dilimin tamamini yer);
    o durumda None doner - cevap "daha cok ornek" degil "daha uzun veri".
    Formul ampirik olarak sinandi ve SIKI cikti: 20 ornek eksigiyle kal
    hedefin altina duser.
    """
    pay = float(kal_orani) - float(bosluk) / float(max(1, acikllik))
    if pay <= 0.0:
        return None
    return int(math.ceil(float(hedef_kal) / pay))


def _ornek_adimi(sirali):
    """Ornekler arasi ortalama BAR araligi (alt-orneklem adimi)."""
    if len(sirali) < 2:
        return 1.0
    return max(1.0, (sirali[-1] - sirali[0]) / float(len(sirali) - 1))


def kronolojik_bol(indeksler, ufuk, embargo, giris_erisimi=0, oranlar=None):
    """Train/kalibrasyon/test; sinirlarda purge + embargo + girdi erisimi.

    Bosluk UC bilesenlidir: etiket ufku (ileri), embargo (guvenlik) ve
    girdi erisimi (geri). Ucuncusu olmadan onceki bolmenin ETIKET penceresi
    sonraki bolmenin GIRDI penceresiyle ortusur.
    """
    oranlar = BOLME_ORANLARI if oranlar is None else oranlar
    sirali = sorted(indeksler)
    n = len(sirali)
    bosluk = int(ufuk) + int(embargo) + int(giris_erisimi)
    # Dejenere kapisi ORNEK biriminde olculur: bosluk BAR cinsindendir,
    # ornekler alt-orneklenmis olabilir. Bar boslugunu ornek sayisiyla
    # dogrudan kiyaslamak (eski hali) adim>1 iken bolmeyi gereksiz yere
    # dejenere ilan eder.
    kayip = int(bosluk / _ornek_adimi(sirali)) + 1
    if n < 3 * (kayip + 5):
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


LONG_SINIFI = esik_kaydet(
    "LONG_SINIFI", 1, "YAPISAL",
    "Baslik logit vektorunde LONG'un indeksi. Istatistiksel secim DEGIL, "
    "etiket tanimindan gelir: etiket_uret LONG hedefi once vuruldugunda 1 "
    "doner ve Baslik.egit p[y]'yi buyutur, dolayisiyla P(LONG dogru) = p[1]. "
    "Yon okuyan HER yer bu sabitten gecer; ham indeks yazmak yasaktir - eksen "
    "iki yerde ayri ayri varsayilirsa yon SESSIZCE tersine doner ve modul ici "
    "tutarlilik testleri bunu YAKALAMAZ.")


def long_olasiligi(p):
    """Olasilik vektorunden LONG olasiligi. Eksene TEK erisim noktasi."""
    return p[LONG_SINIFI]


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
        p_long = sum(long_olasiligi(g) for g in gorusler) / n
        p_short = 1.0 - p_long
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


def _ikili_nll(ciftler):
    """(p_long, y) ciftlerinin ortalama negatif log olabilirligi."""
    if not ciftler:
        return float("inf")
    toplam = 0.0
    for p, y in ciftler:
        p = min(1.0 - 1e-9, max(1e-9, p))
        toplam += -math.log(p if y == 1 else 1.0 - p)
    return toplam / len(ciftler)


def _ham_ciftler(ornekler, basliklar, sicaklik=1.0):
    return [(long_olasiligi(topluluk_olasilik(o["x"], basliklar, sicaklik)["p"]),
             o["y"]) for o in ornekler]


def kalibrasyon_sec(kal_ornekler, basliklar):
    """Sicaklik ve izotonik arasinda IC-HOLDOUT NLL'e gore secim.

    ADIL YARISMA: izotonik, veri noktasi sayisi kadar serbestlik derecesine
    kadar cikabilir; sicaklik TEK parametredir. Iki yontem ayni kumede fit
    edilip ayni kumede puanlanirsa yarisma kenari degil EZBERI olcer ve
    yapisal olarak izotoniki secer. Bu yuzden kalibrasyon kumesi KRONOLOJIK
    olarak ikiye bolunur: her iki yontem de A'da fit edilir, NLL'i B'de
    olculur. Kazanan SONRA tum kumede yeniden fit edilir - yarisma ayirmak
    icindir, veriyi israf etmek icin degil.

    Bolunemeyecek kadar az ornekte (her yariya ASGARI_OLCUM dusmuyorsa)
    yarisma YAPILMAZ ve fail-closed olarak sicaklik secilir: ezber riski en
    dusuk olan yontem. Bu durum "yarisma" alaninda BEYAN edilir - sessiz
    varsayilan yoktur.
    """
    n = len(kal_ornekler)
    if n < 2 * ASGARI_OLCUM:
        s = sicaklik_fit(kal_ornekler, basliklar)
        return {"yontem": "sicaklik", "T": s["T"], "fn": None, "nll": s["nll"],
                "sinirda": s["sinirda"],
                "yarisma": f"YAPILMADI - yetersiz ornek (n={n} < {2 * ASGARI_OLCUM}), "
                           "fail-closed sicaklik"}

    kesim = n // 2
    fit_kume, puan_kume = kal_ornekler[:kesim], kal_ornekler[kesim:]

    s_fit = sicaklik_fit(fit_kume, basliklar)
    sicaklik_nll = _ikili_nll(_ham_ciftler(puan_kume, basliklar, s_fit["T"]))

    izo_fit = izotonik_fit(_ham_ciftler(fit_kume, basliklar))
    izo_nll = _ikili_nll([(izo_fit(p), y)
                          for p, y in _ham_ciftler(puan_kume, basliklar)])

    if izo_nll < sicaklik_nll:
        return {"yontem": "izotonik", "T": 1.0,
                "fn": izotonik_fit(_ham_ciftler(kal_ornekler, basliklar)),
                "nll": izo_nll, "sinirda": False, "yarisma": "ic-holdout"}
    s_tam = sicaklik_fit(kal_ornekler, basliklar)
    return {"yontem": "sicaklik", "T": s_tam["T"], "fn": None,
            "nll": sicaklik_nll, "sinirda": s_tam["sinirda"],
            "yarisma": "ic-holdout"}


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


def _basabas_referansi(geo):
    """Daraltma hedefi olarak kullanilacak basabas olasiligi, ya da None.

    `geo.get("basabas_p") or 0.5` YAZILAMAZ: (1) geometri fail-closed
    donunce referans 0.5 olur ve bu, PD-1'de kok neden olarak kayda
    gecmis referansin ta kendisidir; (2) `or` mesru bir 0.0'i da EKSIK
    sayar. Olculemeyen referans UYDURULMAZ - None doner ve p_kullanilan
    "VERI YOK" olarak raporlanir.
    """
    if not isinstance(geo, dict):
        return None
    deger = geo.get("basabas_p")
    return None if deger is None else float(deger)


def karar_uret(baglam):
    """Tek sembol icin nihai karar: YON (zorunlu) + STAKE (surekli)."""
    shr = shrinkage_katsayisi(baglam["dogru"], baglam["toplam"],
                              baglam.get("ece_enkotu"),
                              baglam["dolu_kanal"], baglam["toplam_kanal"],
                              taban_oran=baglam.get("taban_oran", 0.5),
                              ece_tek_bin=baglam.get("ece_tek_bin", False),
                              sicaklik_sinirda=baglam.get("sicaklik_sinirda", False))

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
        "p_kullanilan": (None if _basabas_referansi(geo) is None
                         else daralt(p_yon, shr["s"],
                                     hedef=_basabas_referansi(geo))),
        "shrinkage": shr, "geometri": geo,
        "giris": sev["giris"], "stop": sev["stop"], "hedef": sev["hedef"],
        "R": sev["R"],
        "stake": {"f": secilen["f"], "kirpildi": secilen["kirpildi"],
                  "f_max": f_max, "lambda_tablosu": lambda_tablosu},
    }


# ---------------------------------------------------------------- BOLUM 9a
# Gostergeler (stdlib, kayan pencere).


def gosterge_penceresi(ad, periyot=None):
    """Bir gostergenin GERIYE dogru okudugu bar sayisi (beyanli ust sinir).

    Purge/embargo bu sayilardan turetilir; etiketsiz gizli esik olamaz.
    """
    if ad == "ema":
        return max(1, int(periyot)) * EMA_KESME_KATI
    if ad in ("atr", "rsi"):
        return max(1, int(periyot))
    if ad in ("z", "kanal"):
        return YUVARLANAN_PENCERE
    raise KeyError(f"bilinmeyen gosterge: {ad}")


def ema(degerler, periyot):
    """Ustel agirlikli ortalama, SONLU pencerede KESILMIS ve normalize.

    NEDEN OZYINELEMELI (IIR) YAZIM TERK EDILDI: `cikti[i] = a*x[i] +
    (1-a)*cikti[i-1]` zinciri serinin BASINA kadar uzanir; pratikte yalniz
    float64 alt-tasmasi keser. Yani erisim VERIYE ve TOLERANSA baglidir.
    Olculdu (kurulum: SonluErisimTesti._seri - tohumlu_rng("sonlu-erisim"),
    n=400, i=350, bozma x1.001; periyot=21):
        tolerans  1e-15  1e-12  1e-9  1e-6
        IIR         301    240   168     95     <- toleransa BAGLI
        kesilmis     41     41    41     41     <- toleranstan BAGIMSIZ
    Toleransa bagli bir sayi purge korkulugu OLAMAZ; sizinti penceresi
    KANITLANABILIR bir ust sinir ister, yoksa "sizinti yok" raporu
    fail-open olur. Bu sayilar test_ema_erisimi_* ile artefakta baglidir.

    Kesme, ustel agirligi TERK ETMEK DEGILDIR: ayni alfa*(1-alfa)^L profili
    kullanilir, yalniz `periyot * EMA_KESME_KATI` barda kesilip yeniden
    normalize edilir. Normalizasyon sayesinde sonuc hala gecerli bir
    agirlikli ortalamadir (agirliklar toplami 1), yani kesilen kuyruk
    kaybolmaz, kalan agirliklara ORANLI dagitilir.
    """
    if not degerler:
        return []
    periyot = max(1, int(periyot))
    alfa = 2.0 / (periyot + 1.0)
    pencere = gosterge_penceresi("ema", periyot)
    agirliklar = [alfa * (1.0 - alfa) ** gecikme for gecikme in range(pencere)]
    kumulatif = []
    toplam = 0.0
    for a in agirliklar:
        toplam += a
        kumulatif.append(toplam)

    cikti = []
    for i in range(len(degerler)):
        n = min(i + 1, pencere)
        pay = sum(agirliklar[g] * float(degerler[i - g]) for g in range(n))
        cikti.append(pay / kumulatif[n - 1])
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


def _kanal_konumu(barlar, i, pencere=None):
    pencere = gosterge_penceresi("kanal") if pencere is None else pencere
    onceki = barlar[max(0, i - pencere):i]
    if not onceki:
        return 0.0
    en_yuksek = max(b["h"] for b in onceki)
    en_dusuk = min(b["l"] for b in onceki)
    genislik = en_yuksek - en_dusuk
    if genislik <= 0:
        return 0.0
    return kirp((barlar[i]["c"] - en_dusuk) / genislik * 2.0 - 1.0)


def _z(degerler, i, pencere=None):
    pencere = gosterge_penceresi("z") if pencere is None else pencere
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
        kirp(math.log(kapanislar[i] / kapanislar[i - EN_UZUN_GETIRI_GECIKMESI]))
        if i >= EN_UZUN_GETIRI_GECIKMESI else 0.0,
        kirp((gostergeler["ema_hizli"][i] - gostergeler["ema_yavas"][i])
             / max(gostergeler["atr"][i], EPSILON) / 2.0),
        kirp((gostergeler["rsi"][i] - 50.0) / 20.0),
        _kanal_konumu(barlar, i),
    ]
    # hacim_deger BIR KEZ _gostergeler'de kurulur. Eskiden burada bar BASINA
    # yeniden kuruluyordu: listcomp TUM seriyi kuruyor ama _z yalniz
    # [i-YUVARLANAN_PENCERE:i] ve [i]'yi okuyor = gercek O(N^2).
    # Hoist DAVRANIS-NOTRDUR ve bu ARTEFAKTA KILITLI
    # (HesapKarmasikligiTesti). Profil gozlemi (cProfile, 20000 bar,
    # bu makinede toplam surenin ~%70'i) ARTEFAKTA KILITLI DEGILDIR -
    # makineye ve olcege baglidir, bir karar girdisi degil gozlemdir.
    hacim = [_z(gostergeler["hacimler"], i), _z(gostergeler["hacim_deger"], i)]
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
    hacimler = [b.get("v", 0.0) for b in barlar]
    return {"kapanislar": kapanislar,
            "hacimler": hacimler,
            # Hacim x fiyat serisi: bar basina DEGIL, seri basina bir kez.
            "hacim_deger": [h * k for h, k in zip(hacimler, kapanislar)],
            "ema_hizli": ema(kapanislar, EMA_HIZLI_PERIYODU),
            "ema_yavas": ema(kapanislar, EMA_YAVAS_PERIYODU),
            "atr": atr(barlar, ATR_PERIYODU),
            "rsi": rsi(kapanislar, RSI_PERIYODU)}


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
        # SABIT RASTGELE IZDUSUM - OGRENILMEZ (bilincli sapma, beyanli).
        # Plan/tasarim "ogrenilen giris izdusumu" diyordu. Olculdu:
        # izdusum 256 parametre tasiyor, egitim dilimi 86 ornek
        # (~3 parametre/ornek). Bu orneklem buyuklugunde 256 parametre
        # egitmek asiri-uyumdur; egitilen kisim kucuk baslikta tutuluyor
        # (102 parametre). Halka OLU DEGIL - izdusum degisince karar
        # degisir (SabitIzdusumTesti bunu kilitler) - yalniz OGRENILMEZ.
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

    # -- calistir'in halkalari --------------------------------------------
    # Her yardimci KENDI iz kaydini yazar ve ortak baglami (ctx) besler.
    # Bolme gerekcesi: plan Global Constraint "tek fonksiyon 60 satiri
    # asmaz". Bolme DAVRANIS-NOTRDUR; sira ve iz anahtarlari korunur.

    def _halka_tokenler(self, paket, iz):
        """Halka 0-1: ham girdi -> zaman dilimi basina oznitelik satirlari."""
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
        # bedeli kapsam dususu olarak shrinkage'a yansir.
        etkin_zd = [zd for zd in ZAMAN_DILIMLERI if zd in satir_kumesi]
        iz["halka_1"] = {"ad": "tokenizasyon", "aile_sayisi": len(AILELER),
                         "gecikme": GECIKME_SAYISI,
                         "zaman_dilimi_sayisi": len(etkin_zd),
                         "h4_var": h4_var,
                         "token_sayisi": (GECIKME_SAYISI * len(AILELER)
                                          * len(etkin_zd))}
        return {"barlar": barlar, "gost": gost, "satir_kumesi": satir_kumesi,
                "etkin_zd": etkin_zd, "h4_var": h4_var}

    def _halka_bolme(self, ctx, paket, iz):
        """Halka 11: purge/embargo + sizinti denetimi."""
        barlar = ctx["barlar"]
        bitis = len(barlar) - ETIKET_UFKU - 1
        tum_indeksler = _ornek_indeksleri(ISINMA_BARI, bitis,
                                          paket.get("azami_ornek", AZAMI_ORNEK))
        # Purge/embargo, ornegin GERCEKTEN okudugu geriye erisime gore
        # olculur: gosterge pencerelerinden turetilir, token gecikmesinden DEGIL.
        erisim = girdi_erisimi(GECIKME_SAYISI, h4_var=ctx["h4_var"])
        bolme = kronolojik_bol(tum_indeksler, ETIKET_UFKU, EMBARGO,
                               giris_erisimi=erisim)
        # Bos bolmede "sizinti: False" demek fail-OPEN rapordur: olculemeyen
        # sey "yok" diye raporlanamaz.
        bolme_bos = not (bolme["train"] and bolme["kalibrasyon"] and bolme["test"])
        iz["halka_11"] = {"ad": "otoregresif/bolme", "train": len(bolme["train"]),
                          "kalibrasyon": len(bolme["kalibrasyon"]),
                          "test": len(bolme["test"]), "atilan": bolme["atilan"],
                          "giris_erisimi": erisim,
                          "not": bolme["not"] or ("yetersiz ornek - bolme dejenere"
                                                  if bolme_bos else ""),
                          "sizinti": (None if bolme_bos
                                      else sizinti_var_mi(bolme, ETIKET_UFKU,
                                                          erisim))}
        # Yarisma kosamiyorsa "ulasilamaz" deyip birakmak yetmez: NE KADAR
        # veriyle/butceyle ulasilacagi TURETILIP raporlanir.
        iz["halka_11"]["gereken_azami_ornek"] = gereken_ornek_butcesi(
            max(1, tum_indeksler[-1] - tum_indeksler[0]) if tum_indeksler else 1,
            ETIKET_UFKU + EMBARGO + erisim,
            BOLME_ORANLARI[1], 2 * ASGARI_OLCUM)
        iz["halka_11"]["kullanilan_azami_ornek"] = paket.get("azami_ornek",
                                                             AZAMI_ORNEK)
        ctx["bolme"] = bolme
        ctx["tum_indeksler"] = tum_indeksler

    def _halka_olcek(self, ctx, iz):
        """Halka 2-5: TRAIN-ONLY olcekleyici + konum/attention/FFN beyani."""
        bolme, barlar = ctx["bolme"], ctx["barlar"]
        kesim = (bolme["train"][-1] if bolme["train"]
                 else max(1, len(barlar) // 2))
        olcekleyiciler = {}
        for zd in ctx["etkin_zd"]:     # her zaman dilimi KENDI istatistigiyle
            o = Olcekleyici()
            o.fit(ctx["satir_kumesi"][zd], kesim)
            olcekleyiciler[zd] = o
        iz["halka_2"] = {"ad": "embedding/olcekleme", "kesim": kesim,
                         "sabit_kolon": {zd: len(olcekleyiciler[zd].sabit_kolonlar)
                                         for zd in ctx["etkin_zd"]}}
        iz["halka_3"] = {"ad": "konum kodu", "zaman_ekseni": True,
                         "sembol_ekseni": True, "faz": SEMBOL_EKSENI_FAZI}
        iz["halka_4"] = {"ad": "causal attention", "bas": self.kodlayici.bas_sayisi,
                         "maske": True}
        iz["halka_5"] = {"ad": "FFN", "genislik": self.boyut * 2}
        ctx["olcekleyiciler"] = olcekleyiciler

    def _ornek(self, ctx, i):
        x = self.kodlayici.ileri(
            self._durumlar(ctx["satir_kumesi"], ctx["olcekleyiciler"], i))
        y = etiket_uret(ctx["barlar"], i, ctx["gost"]["atr"])
        return None if y is None else {"x": x, "y": y}

    def _halka_egitim(self, ctx, iz):
        """Halka 6-7: ornek uretimi, baslik egitimi, kalibrasyon secimi."""
        bolme = ctx["bolme"]
        train = [o for o in (self._ornek(ctx, i) for i in bolme["train"]) if o]
        kal = [o for o in (self._ornek(ctx, i) for i in bolme["kalibrasyon"]) if o]
        test = [o for o in (self._ornek(ctx, i) for i in bolme["test"]) if o]

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
                         "sinirda": kalib["sinirda"],
                         "yarisma": kalib.get("yarisma", "YOK")}
        # Yarisma kosmadiysa NE GEREKTIGI de yazilir: "yapilamaz" bir
        # hukumdur, "su kadar veriyle yapilir" bir YOL TARIFIDIR.
        gereken = iz.get("halka_11", {}).get("gereken_azami_ornek")
        if iz["halka_7"]["yarisma"].startswith("YAPILMADI"):
            iz["halka_7"]["yarisma"] += (
                f" | gereken azami_ornek: {gereken}"
                if gereken else
                " | bu veri ACIKLIGINDA hicbir butce yetmez (daha uzun seri gerekir)")
        ctx.update({"train": train, "test": test, "basliklar": basliklar,
                    "kalib": kalib})

    def _halka_degerlendirme(self, ctx, iz):
        """Halka 8: HOLDOUT metrikleri (train'de degil, test diliminde)."""
        basliklar, kalib = ctx["basliklar"], ctx["kalib"]
        ciftler = []
        for o in ctx["test"]:
            p = long_olasiligi(
                topluluk_olasilik(o["x"], basliklar, kalib["T"])["p"])
            if kalib["fn"] is not None:
                p = kalib["fn"](p)
            ciftler.append((p, o["y"]))
        dogru = sum(1 for p, y in ciftler if (1 if p >= 0.5 else 0) == y)
        # TABAN ORAN: kumenin kendi cogunluk sinifi. Yon dogrulugu buna
        # gore olculur; %50 referansi dengesiz etikette beceri UYDURUR.
        pozitif = sum(1 for _, y in ciftler if y == 1)
        taban_oran = (max(pozitif, len(ciftler) - pozitif) / len(ciftler)
                      if ciftler else 0.5)
        # ECE TEK KOVAYA COKTU MU: coktu ise ECE bilgi TASIMAZ (ECE == MCE).
        duyarlilik = ece_duyarlilik(ciftler) if ciftler else {
            "tek_bine_cokme": True, "dolu_kova": 0}
        iz["halka_8"] = {"ad": "softmax/yon ekseni", "test_ornek": len(ciftler),
                         "dogru": dogru,
                         "taban_oran": taban_oran,
                         "ece": ece(ciftler) if ciftler else None,
                         "mce": mce(ciftler) if ciftler else None,
                         "ece_tek_bin": duyarlilik["tek_bine_cokme"],
                         "dolu_kova": duyarlilik["dolu_kova"],
                         "brier": brier(ciftler) if ciftler else None,
                         "auroc": auroc(ciftler) if ciftler else None,
                         "wilson": wilson_araligi(dogru, len(ciftler))}
        ctx["ciftler"] = ciftler
        ctx["dogru"] = dogru
        ctx["taban_oran"] = taban_oran
        ctx["ece_tek_bin"] = duyarlilik["tek_bine_cokme"]

    def _halka_olasilik(self, ctx, iz):
        """Halka 9-10: son barin olasiligi + self-consistency."""
        basliklar, kalib = ctx["basliklar"], ctx["kalib"]
        son = len(ctx["barlar"]) - 1
        x_son = self.kodlayici.ileri(
            self._durumlar(ctx["satir_kumesi"], ctx["olcekleyiciler"], son))
        top = topluluk_olasilik(x_son, basliklar, kalib["T"])
        p_ham = long_olasiligi(top["p"])
        if kalib["fn"] is not None:
            p_ham = kalib["fn"](p_ham)
        # EGITILMEMIS MODELDEN YON BEYAN EDILMEZ. Bolme dejenere ise
        # basliklar rastgele baslangic degerlerindedir; p_ham bir OLCUM
        # degil bir tohum artefaktidir. Onu "yon" diye sunmak uydurmadir.
        # Sozluk kurali (V = {LONG, SHORT}, HOLD YOK) DECODER'in sinif
        # kumesi hakkindadir - burada decoder egitilmis bir model uzerinde
        # hic kosmamistir, yani ucuncu bir sinif eklenmiyor; olcum YOK.
        egitildi = bool(ctx["train"])
        if not egitildi:
            p_ham = None
        iz["halka_9"] = {"ad": "decoding", "p_long": p_ham, "hold": False,
                         "egitildi": egitildi}
        iz["halka_10"] = {"ad": "self-consistency", "uzlasi": top["uzlasi"],
                          "dagilim": top["dagilim"],
                          "T_karari_cevirir": sicaklik_karari_cevirir_mi(
                              [b.logit(x_son) for b in basliklar])}
        ctx["p_ham"] = p_ham
        ctx["egitildi"] = egitildi
        ctx["son"] = son

    def _kapsam(self, ctx, paket, iz):
        """KAPSAM h4_var'dan TURETILIR: modele ULASMAYAN veri kapsami
        BUYUTEMEZ. Paket 4H kanalini dolu sayiyorsa ve 4H gercekten boru
        hattina girmediyse fail-closed olarak bir azaltilir."""
        dolu_kanal = paket["dolu_kanal"]
        if not ctx["h4_var"]:
            dolu_kanal = max(0, dolu_kanal - 1)
            iz["halka_0"]["h4_kanali_dusuldu"] = True
        return dolu_kanal

    def _tamamla(self, karar, paket, iz):
        karar["iz"] = iz
        karar["kalibrasyon"] = iz["halka_8"]
        karar["adaptor"] = paket.get("adaptor")
        return karar

    def _dejenere_karar(self, paket, iz):
        """Fail-closed cikti: model hic egitilmedi, olcum YOK.

        SOZLESME: bu dal NORMAL dalla AYNI anahtarlari tasir. Aksi halde
        tuketiciler (metin_rapor, defter_guncelle, rapor_yaz) yalniz mutlu
        yolda calisir ve fail-closed dalda COKER - yani guvenlik dali,
        cokme dali olur. Eksik olan DEGERLER None'dir; eksik olan
        ANAHTARLAR degil.
        """
        iz["halka_12"] = {"ad": "detokenizasyon", "giris": None, "stop": None,
                          "hedef": None, "R": None, "f": 0.0}
        return self._tamamla({
            "sembol": paket["sembol"], "yon": "VERI YOK",
            "p_ham": None, "p_kullanilan": None,
            "giris": None, "stop": None, "hedef": None, "R": None,
            "geometri": {"stop_k": None, "hedef_k": None, "R": None,
                         "p_hedef": None, "p_bilesik": None, "n": 0,
                         "f": 0.0, "elog": None, "cost_r": None,
                         "b": None, "a": None, "basabas_p": None,
                         "denenen": [],
                         "not": "OLCUM YOK - model egitilmedi"},
            "shrinkage": {"s": 0.0, "s_kanit": 0.0, "s_kalibrasyon": 0.0,
                          "s_kapsam": 0.0},
            "stake": {"f": 0.0, "f_max": 0.0, "kirpildi": False,
                      "lambda_tablosu": {str(lam): {"f": 0.0}
                                         for lam in LAMBDA_TABLOSU},
                      "p_kullanilan": None, "p0": None,
                      "not": "model EGITILMEDI - bolme dejenere"},
            "not": ("bolme dejenere: egitim/kalibrasyon/degerlendirme "
                    "kosmadi. Yon bir OLCUM degil tohum artefakti "
                    "olurdu - beyan edilmiyor (fail-closed).")}, paket, iz)

    def _halka_karar(self, ctx, paket, iz):
        """Halka 12: olasilik + geometri + shrinkage -> uygulanabilir karar."""
        barlar, gost, son = ctx["barlar"], ctx["gost"], ctx["son"]
        ece_grup = (grup_ece({"test": ctx["ciftler"]}) if ctx["ciftler"]
                    else {"en_kotu": (None, None)})
        karar = karar_uret({
            "sembol": paket["sembol"], "barlar": barlar, "atr_serisi": gost["atr"],
            "indeksler": ctx["bolme"]["test"] or ctx["tum_indeksler"][-40:],
            "p_ham": ctx["p_ham"], "dogru": ctx["dogru"],
            "toplam": len(ctx["ciftler"]),
            "ece_enkotu": ece_grup["en_kotu"][1],
            # OLCULEN UYARILAR KAPIYA BAGLI (fail-closed):
            "taban_oran": ctx.get("taban_oran", 0.5),
            "ece_tek_bin": ctx.get("ece_tek_bin", False),
            "sicaklik_sinirda": bool(iz["halka_7"].get("sinirda")),
            "dolu_kanal": self._kapsam(ctx, paket, iz),
            "toplam_kanal": paket["toplam_kanal"],
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
        return self._tamamla(karar, paket, iz)

    def calistir(self, paket):
        """LLM zincirinin 12 halkasini sirayla kosturur."""
        iz = {}
        ctx = self._halka_tokenler(paket, iz)
        self._halka_bolme(ctx, paket, iz)
        self._halka_olcek(ctx, iz)
        self._halka_egitim(ctx, iz)
        self._halka_degerlendirme(ctx, iz)
        self._halka_olasilik(ctx, iz)
        if not ctx["egitildi"]:
            self._kapsam(ctx, paket, iz)      # kapsam notu iz'de yine gorunsun
            return self._dejenere_karar(paket, iz)
        return self._halka_karar(ctx, paket, iz)


# ---------------------------------------------------------------- BOLUM 10
# Cikti, kagit defteri, CLI. GERCEK EMIR YOK.


def bahis_acilir_mi(stake):
    """Bahis ACILIR mi? Stake'i okuyan HER tuketici bu yuklemden gecer.

    Ayni karar hakkinda defter "pozisyon actim", rapor "bahis sifir"
    diyemez. Iki ayri kapi (`f > 0` ve `f == 0`) tam da bunu yapiyordu.
    """
    return float((stake or {}).get("f") or 0.0) > 0.0


def _bicim(deger, kalip=".4f"):
    """OLCULMEMIS deger "VERI YOK" diye yazilir, 0.0000 diye DEGIL.

    Eksigi sifirla doldurmak sayisal bir iddia uydurmaktir; ayrica
    None'i dogrudan bicimlendirmek TypeError verir - rapor katmani
    fail-closed dalda cokerdi.
    """
    if deger is None:
        return "VERI YOK"
    try:
        return format(deger, kalip)
    except (TypeError, ValueError):
        return str(deger)


def metin_rapor(karar):
    g = karar.get("geometri") or {}
    s = karar.get("stake") or {}
    sh = karar.get("shrinkage") or {}
    satirlar = [
        "=" * 78,
        f"{karar['sembol']} | {SURUM} | YALNIZ KARAR-DESTEK (gercek emir YOK)",
        f"YON: {karar['yon']}   (p_ham={_bicim(karar.get('p_ham'))} -> "
        f"p_kullanilan={_bicim(karar.get('p_kullanilan'))})",
        f"SHRINKAGE s={_bicim(sh.get('s'))} "
        f"(kanit={_bicim(sh.get('s_kanit'), '.3f')} "
        f"kalibrasyon={_bicim(sh.get('s_kalibrasyon'), '.3f')} "
        f"kapsam={_bicim(sh.get('s_kapsam'), '.3f')})",
        f"GEOMETRI stop_k={g.get('stop_k', 'VERI YOK')} "
        f"hedef_k={g.get('hedef_k', 'VERI YOK')} "
        f"R={_bicim(g.get('R'))} p_hedef={g.get('p_hedef')} n={g.get('n')}",
        f"basabas p (f*>0 icin gereken) = {g.get('basabas_p')}",
        f"SEVIYELER giris={_bicim(karar.get('giris'), '.8g')} "
        f"stop={_bicim(karar.get('stop'), '.8g')} "
        f"hedef={_bicim(karar.get('hedef'), '.8g')}",
        f"STAKE f*={_bicim(s.get('f'), '.6f')}  "
        f"(f_max={_bicim(s.get('f_max'), '.6f')}, "
        f"kirpildi={'EVET' if s.get('kirpildi') else 'hayir'})",
        "  lambda: " + ("  ".join(f"{lam}->{_bicim(v.get('f'), '.6f')}"
                                  for lam, v in s["lambda_tablosu"].items())
                        if s.get("lambda_tablosu") else "VERI YOK"),
    ]
    for kaynak in (g, s, karar):
        if kaynak.get("not"):
            satirlar.append(f"NOT: {kaynak['not']}")
    if not bahis_acilir_mi(s):
        satirlar.append("f*=0: yon ve seviyeler yine uretildi; bahis buyuklugu sifir.")
    return "\n".join(satirlar)


KARAR_DESTEK_UYARISI = (
    "Yalniz karar-destek. Canli/otomatik emir (gercek para) DAHIL DEGILDIR; "
    "bu dosya bir emir dosyasi degil, bir olcum kaydidir."
)


def rapor_yaz(kararlar, dosya):
    """Kararlari YEREL bir JSON dosyasina yazar. Ag erisimi YOK.

    Deterministik: ayni girdi ayni bayt (sort_keys + sabit girinti). Rapor
    bir KANIT artefaktidir - denetim onu yeniden okuyup sayilari
    dogrulayabilmelidir, dolayisiyla iz (halka_0..12) oldugu gibi tasinir.

    Serilesmeyen bir alan varsa TypeError YUKSELIR ve dosya yazilmaz:
    yazilamayan sey "yazildi" diye raporlanamaz (fail-closed). json.dumps
    varsayilan olarak zaten yukseltir; `default=` ile susturmak, sessizce
    veri kaybi demek olurdu.
    """
    import json

    govde = {"surum": SURUM, "uyari": KARAR_DESTEK_UYARISI,
             "kararlar": list(kararlar)}
    metin = json.dumps(govde, sort_keys=True, indent=1, ensure_ascii=False)
    with open(str(dosya), "w", encoding="utf-8") as f:
        f.write(metin + "\n")


def defter_guncelle(durum, karar, bar):
    """Yerel kagit defteri. f*=0 ise pozisyon ACILMAZ (bahis sifir).

    MALIYET DUSULUR: Kelly kayip kanadini a = 1 + cost_r olarak fiyatlar.
    Defter yalniz `f` dusseydi, boyutlandirdigi hedefe gore SISTEMATIK
    iyimser olurdu - sicil, olctugu seyden BASKA bir seyi olcerdi.
    """
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
            ham = isaret * (cikis - mevcut["giris"]) * mevcut["miktar"]
            # Islem maliyeti (komisyon+kayma), R biriminde tutulan cost_r
            # uzerinden ve stop mesafesiyle olceklenerek dusulur.
            maliyet = (mevcut.get("cost_r", 0.0)
                       * abs(mevcut["giris"] - mevcut["stop"])
                       * mevcut["miktar"])
            yeni["sermaye"] += ham - maliyet
            yeni["pozisyonlar"].pop(sembol, None)

    if sembol not in yeni["pozisyonlar"] and bahis_acilir_mi(karar["stake"]):
        risk_tutari = yeni["sermaye"] * karar["stake"]["f"]
        mesafe = abs(karar["giris"] - karar["stop"]) or EPSILON
        yeni["pozisyonlar"][sembol] = {
            "yon": karar["yon"], "giris": karar["giris"], "stop": karar["stop"],
            "hedef": karar["hedef"], "miktar": risk_tutari / mesafe,
            "cost_r": float((karar.get("geometri") or {}).get("cost_r") or 0.0)}
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
    import sys as _sys
    import unittest as _ut
    _t = _sys.modules[__name__]        # testler AYNI dosyada
    _OZ_TEST_KOSUYOR = True
    try:
        sonuc = _ut.TextTestRunner(verbosity=1).run(
            _ut.defaultTestLoader.loadTestsFromModule(_t))
    finally:
        _OZ_TEST_KOSUYOR = False
    return 0 if sonuc.wasSuccessful() else 1


def _oz_kosu_kararlari(bar_sayisi=None, tohum=2026):
    """Sentetik veriyle tam boru hatti kosusu. Ag YOK, test paketi YOK.

    Bar sayisi varsayilani, bolmenin dejenere olmamasi icin gereken
    mertebeden (purge boslugu = ufuk + embargo + girdi_erisimi) TURETILIR;
    sabit secilmez.
    """
    if bar_sayisi is None:
        bosluk = ETIKET_UFKU + EMBARGO + girdi_erisimi(GECIKME_SAYISI, True)
        bar_sayisi = 6 * bosluk
    rng = tohumlu_rng("oz-kosu", tohum, bar_sayisi)
    barlar, fiyat = [], 100.0
    for _ in range(bar_sayisi):
        fiyat *= 1.0 + rng.uniform(-0.003, 0.0032)
        barlar.append({"o": fiyat, "h": fiyat * 1.002, "l": fiyat * 0.998,
                       "c": fiyat, "v": 1000.0 + rng.uniform(0.0, 100.0)})
    dort = []
    for k in range(0, len(barlar) // H4_BAR_ORANI * H4_BAR_ORANI, H4_BAR_ORANI):
        dilim = barlar[k:k + H4_BAR_ORANI]
        dort.append({"o": dilim[0]["o"], "h": max(b["h"] for b in dilim),
                     "l": min(b["l"] for b in dilim), "c": dilim[-1]["c"],
                     "v": sum(b["v"] for b in dilim)})
    paket = {"sembol": "SENTETIK", "barlar15": barlar, "barlar4h": dort,
             "turev_serisi": None, "dolu_kanal": 2, "toplam_kanal": 6,
             "adaptor": "sentetik-oz-kosu", "azami_ornek": AZAMI_ORNEK}
    return [BoruHatti(tohum=tohum).calistir(paket)]


# ==========================================================================
# BOLUM 12 - CANLI VERI KATMANI (public GET; imza/anahtar/emir ucu YOK)
# ==========================================================================


def http_getir(url, params, zaman_asimi=20):
    """Tek public GET. Bu dosyadaki TEK ag cagrisi.

    Emir/iptal ucu, API anahtari, imza YOKTUR ve eklenmemelidir - modul
    bir EMIR sistemi degil, bir OLCUM sistemidir.
    """
    import json as _json
    import urllib.parse as _up
    import urllib.request as _ur

    tam = url + "?" + _up.urlencode(params)
    istek = _ur.Request(tam, headers={"User-Agent": SURUM})
    with _ur.urlopen(istek, timeout=zaman_asimi) as yanit:
        return _json.loads(yanit.read().decode("utf-8"))


def canli_kosu(sembol, getir_fn=None, tohum=2026, **ek):
    """Uctan uca: veri_topla -> paket_kur -> BoruHatti.calistir.

    getir_fn verilmezse http_getir kullanilir (AGA CIKAR).
    """
    getir_fn = http_getir if getir_fn is None else getir_fn
    toplama = veri_topla(sembol, [BinanceAdaptor(), OkxAdaptor()], getir_fn)
    if toplama["adaptor"] is None:
        raise RuntimeError("hicbir adaptor veri veremedi (fail-closed)")
    paket = paket_kur(sembol, toplama, **ek)
    return BoruHatti(tohum=tohum).calistir(paket), paket, toplama


def _sahte_getir(url, params):
    """AGSIZ ornek veri uretici - `--ornek` icin. Gercek veri DEGILDIR."""
    rng = tohumlu_rng("ornek", url, str(params.get("interval", "")))
    if "klines" in url:
        onbes = "15m" in str(params.get("interval"))
        n, adim = (6000, 900000) if onbes else (375, 14400000)
        satirlar, fiyat = [], 100.0
        for i in range(n):
            fiyat *= 1.0 + rng.uniform(-0.003, 0.003)
            h = 100.0 + rng.uniform(0.0, 50.0)
            satirlar.append([i * adim, "%.8f" % fiyat, "%.8f" % (fiyat * 1.002),
                             "%.8f" % (fiyat * 0.998), "%.8f" % fiyat,
                             "%.8f" % h, i * adim + adim - 1, "0", 50,
                             "%.8f" % (h * (0.4 + rng.uniform(0.0, 0.2))),
                             "0", "0"])
        return satirlar
    if "openInterest" in url:
        return [{"sumOpenInterest": "%.2f" % (1000 + rng.uniform(-50, 50)),
                 "timestamp": i * 900000} for i in range(6000)]
    if "takerlongshort" in url:
        return [{"buySellRatio": "%.4f" % (1.0 + rng.uniform(-0.2, 0.2)),
                 "timestamp": i * 900000} for i in range(6000)]
    if "premiumIndex" in url:
        return {"lastFundingRate": "0.0001"}
    if "depth" in url:
        return {"bids": [["100.0", "5.0"]], "asks": [["100.1", "3.0"]]}
    raise RuntimeError("bilinmeyen uc: " + url)


_TEST_BOLUMU_SINIRI = "# BOLUM 11 - TEST PAKETI"
_TEST_SABITLERI = ("FIKSTUR_BARI",)   # test fiksturu, motor esigi DEGIL


def _modul_kaynagi():
    """Bu dosyanin YALNIZ motor bolumu (test bolumu HARIC).

    Tek dosyada kaynak tarayan testler kendi metinlerini de gorurdu; o
    yuzden tarama sinirlanir. Testleri zayiflatmaz - dogru kaynagi
    gosterir.
    """
    import pathlib as _pl
    metin = _pl.Path(__file__).read_text(encoding="utf-8")
    kesim = metin.find(_TEST_BOLUMU_SINIRI)
    return metin if kesim < 0 else metin[:kesim]


def _kosu_bas(sembol, getir_fn, baslik):
    karar, paket, toplama = canli_kosu(sembol, getir_fn=getir_fn)
    print("=" * 78)
    print(baslik)
    print("adaptor      :", toplama["adaptor"],
          "| ham kapsam:", round(toplama["kapsam"], 4))
    print("seri kanal   :", paket["dolu_kanal"], "/", paket["toplam_kanal"],
          "| anlik (kapsama SAYILMAZ):", paket["anlik_kanallar"])
    print("bar          :", len(paket["barlar15"]), "x 15M +",
          len(paket["barlar4h"] or []), "x 4H")
    print()
    print(metin_rapor(karar))
    iz = karar["iz"]
    print()
    print("bolme        :", {k: iz["halka_11"][k] for k in
                             ("train", "kalibrasyon", "test", "sizinti",
                              "giris_erisimi", "gereken_azami_ornek")})
    print("kalibrasyon  :", iz["halka_7"]["yarisma"])
    return karar


# ==========================================================================
# BOLUM 11 - TEST PAKETI (236 test). `--self-test` bunlari kosturur.
# ==========================================================================

import ast          # noqa: E402
import inspect      # noqa: E402
import json         # noqa: E402
import pathlib      # noqa: E402
import re           # noqa: E402
import shutil       # noqa: E402
import sys as _sys  # noqa: E402
import tempfile     # noqa: E402
import unittest     # noqa: E402

m = _sys.modules[__name__]   # testler kendi dosyasini denetler

class GuvenlikTesti(unittest.TestCase):
    """Kod canli emir gonderemez: yasakli desenler dosyada BULUNMAMALI."""

    YASAK = [
        r"api[_-]?key", r"apiKey", r"secret", r"hmac", r"signature=",
        r"/fapi/v1/order", r"/api/v5/trade/order", r"privateKey",
    ]

    def test_yasakli_desen_yok(self):
        kaynak = m._modul_kaynagi()
        for desen in self.YASAK:
            bulunan = re.findall(desen, kaynak, re.IGNORECASE)
            self.assertEqual(bulunan, [], f"yasakli desen bulundu: {desen} -> {bulunan}")


class DeterminizmTesti(unittest.TestCase):
    def test_ayni_tohum_ayni_dizi(self):
        a = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        b = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        self.assertEqual(a, b)

    def test_farkli_tohum_farkli_dizi(self):
        a = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        b = [m.tohumlu_rng("x", 2).random() for _ in range(5)]
        self.assertNotEqual(a, b)

    def test_sabit_kimlik_deterministik(self):
        self.assertEqual(m.sabit_kimlik("BTCUSDT", "15m", 3),
                         m.sabit_kimlik("BTCUSDT", "15m", 3))
        self.assertNotEqual(m.sabit_kimlik("BTCUSDT", "15m", 3),
                            m.sabit_kimlik("BTCUSDT", "15m", 4))


class KirpTesti(unittest.TestCase):
    def test_sinirlar(self):
        self.assertEqual(m.kirp(5.0, -1.0, 1.0), 1.0)
        self.assertEqual(m.kirp(-5.0, -1.0, 1.0), -1.0)
        self.assertEqual(m.kirp(0.3, -1.0, 1.0), 0.3)

    def test_gecersiz_girdi_alt_sinira_duser(self):
        self.assertEqual(m.kirp(None, -1.0, 1.0), -1.0)
        self.assertEqual(m.kirp(float("nan"), -1.0, 1.0), -1.0)


# ----------------------------------------------------------------- Task 2

class StakeSifirGarantisiTesti(unittest.TestCase):
    """Sistemin BAS GARANTISI: kanit yoksa f* TAM OLARAK 0.

    Onceki hali kayan noktada tutmuyordu: p0 = a/(a+b) iken Kelly payi
    p0*b - (1-p0)*a ancak TAM aritmetikte sadelesir; float64'te 1e-16
    mertebesinde artik kaliyor. Bu bir yuvarlama merakı DEGIL, sozlesme
    ihlali: defter_guncelle `f > 0.0` kapisiyla POZISYON ACIYOR ve o
    sembolun yuvasini isgal ediyor; metin_rapor ise `f == 0.0` kapisiyla
    "bahis buyuklugu sifir" satirini BASTIRIYOR - iki tuketici ayni karar
    hakkinda ZIT hukum veriyor.
    """

    def _izgara(self):
        for R in (1.05, 1.2, 1.35, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0):
            for cost in (0.0, 0.001, 0.002, 0.005, 0.01):
                b, a = m.net_kanatlar(R, cost)
                for p_ham in (0.0, 0.2, 0.4, 0.5, 0.8, 1.0):
                    yield R, cost, p_ham, b, a

    def test_kanit_yokken_f_TAM_SIFIR(self):
        ihlal = []
        for R, cost, p_ham, b, a in self._izgara():
            f = m.stake_hesapla(p_ham, 0.0, b, a)["f"]
            if f != 0.0:
                ihlal.append((R, cost, p_ham, f))
        self.assertEqual(ihlal, [], f"{len(ihlal)} durumda f* tam sifir degil")

    def test_kanit_yokken_lambda_ne_olursa_olsun_sifir(self):
        b, a = m.net_kanatlar(1.05, 0.0)
        for lam in m.LAMBDA_TABLOSU:
            self.assertEqual(m.stake_hesapla(0.95, 0.0, b, a, lam=lam)["f"], 0.0)

    def test_kanit_yokken_defter_POZISYON_ACMAZ(self):
        """Tuketici etkisi: 1e-16'lik stake yuvayi isgal ediyordu."""
        b, a = m.net_kanatlar(1.05, 0.0)
        stake = m.stake_hesapla(0.95, 0.0, b, a)
        karar = {"sembol": "X", "yon": "LONG", "giris": 100.0, "stop": 99.0,
                 "hedef": 101.05, "stake": stake}
        yeni = m.defter_guncelle({"sermaye": 1000.0, "pozisyonlar": {}}, karar,
                                 {"o": 100.0, "h": 100.2, "l": 99.8, "c": 100.0})
        self.assertEqual(yeni["pozisyonlar"], {})

    def test_iki_tuketici_ayni_yuklemi_kullanir(self):
        """defter ve rapor ayni karar hakkinda ZIT hukum veremez."""
        b, a = m.net_kanatlar(1.05, 0.0)
        stake = dict(m.stake_hesapla(0.95, 0.0, b, a),
                     f_max=0.1, kirpildi=False,
                     lambda_tablosu={"1.0": {"f": 0.0}})
        karar = {"sembol": "X", "yon": "LONG", "giris": 100.0, "stop": 99.0,
                 "hedef": 101.05, "p_ham": 0.95, "p_kullanilan": 0.5,
                 "shrinkage": {"s": 0.0, "s_kanit": 0.0, "s_kalibrasyon": 0.0,
                               "s_kapsam": 0.0},
                 "geometri": {"stop_k": 1.0, "hedef_k": 1.05, "R": 1.05,
                              "p_hedef": None, "n": 0, "basabas_p": None,
                              "not": ""},
                 "stake": stake}
        metin = m.metin_rapor(karar)
        yeni = m.defter_guncelle({"sermaye": 1000.0, "pozisyonlar": {}}, karar,
                                 {"o": 100.0, "h": 100.2, "l": 99.8, "c": 100.0})
        acti = bool(yeni["pozisyonlar"])
        sifir_denildi = "bahis buyuklugu sifir" in metin
        self.assertNotEqual(acti, sifir_denildi,
                            "rapor 'sifir' derken defter pozisyon acamaz")
        self.assertFalse(acti)
        self.assertTrue(sifir_denildi)

    def test_kanit_VARKEN_f_hala_pozitif_olabilir(self):
        """Snap yalniz s=0'a bakmali; kanit varken stake KISITLANMAMALI."""
        b, a = m.net_kanatlar(2.0, 0.0)
        f = m.stake_hesapla(0.9, 1.0, b, a)["f"]
        self.assertGreater(f, 0.0)


class KellyTesti(unittest.TestCase):
    def test_net_kanatlar(self):
        b, a = m.net_kanatlar(R=1.3333, cost_r=0.6)
        self.assertAlmostEqual(b, 0.7333, places=4)
        self.assertAlmostEqual(a, 1.6000, places=4)

    def test_basabas_p_bilinen_deger(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        self.assertAlmostEqual(m.basabas_p(b, a), 0.6857, places=4)

    def test_basabas_p_maliyetsiz(self):
        b, a = m.net_kanatlar(1.3333, 0.0)
        self.assertAlmostEqual(m.basabas_p(b, a), 0.4286, places=4)

    def test_kelly_basabasin_altinda_sifir(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        for p in (0.50, 0.60, 0.68):
            self.assertEqual(m.kelly_asimetrik(p, b, a), 0.0,
                             f"p={p} icin f* 0 olmali")

    def test_kelly_basabasin_ustunde_pozitif(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        f = m.kelly_asimetrik(0.70, b, a)
        self.assertGreater(f, 0.0)
        self.assertAlmostEqual(f, 0.0284, places=3)

    def test_kelly_negatif_kanat_sifir(self):
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        self.assertLessEqual(b, 0.0)
        self.assertEqual(m.kelly_asimetrik(0.99, b, a), 0.0)

    def test_basabas_p_negatif_kanatta_none(self):
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        self.assertIsNone(m.basabas_p(b, a))

    def test_maliyet_r_hesabi(self):
        cr = m.maliyet_r(giris=100.0, stop_mesafesi=0.15,
                         komisyon=0.0004, kayma=0.0005, funding=0.0)
        self.assertAlmostEqual(cr, (2 * 100.0 * 0.0009) / 0.15, places=8)

    def test_maliyet_r_sifir_stopta_sonsuz_degil(self):
        cr = m.maliyet_r(100.0, 0.0, 0.0004, 0.0005, 0.0)
        self.assertTrue(math.isfinite(cr))
        self.assertGreater(cr, 1000.0)


# ----------------------------------------------------------------- Task 3

class KalibrasyonMetrikTesti(unittest.TestCase):
    def test_wilson_bilinen_deger(self):
        alt, ust = m.wilson_araligi(17, 48)
        self.assertAlmostEqual(alt, 0.2343, places=3)
        self.assertAlmostEqual(ust, 0.4956, places=3)

    def test_wilson_sifir_deneme(self):
        alt, ust = m.wilson_araligi(0, 0)
        self.assertEqual((alt, ust), (0.0, 1.0))

    def test_ece_mukemmel_kalibre_sifir(self):
        ciftler = [(1.0, 1)] * 50 + [(0.0, 0)] * 50
        self.assertAlmostEqual(m.ece(ciftler), 0.0, places=9)

    def test_ece_tam_ters_bir(self):
        ciftler = [(1.0, 0)] * 50 + [(0.0, 1)] * 50
        self.assertAlmostEqual(m.ece(ciftler), 1.0, places=9)

    def test_ece_tek_bine_cokme_tespiti(self):
        ciftler = [(0.335, 1) if i % 3 == 0 else (0.335, 0) for i in range(48)]
        rapor = m.ece_duyarlilik(ciftler)
        self.assertTrue(rapor["tek_bine_cokme"], "tek bine cokme tespit edilmeli")

    def test_ece_duyarlilik_dagilmis_veride_cokme_yok(self):
        ciftler = [(i / 100.0, 1 if i > 50 else 0) for i in range(1, 100)]
        rapor = m.ece_duyarlilik(ciftler)
        self.assertFalse(rapor["tek_bine_cokme"])

    def test_brier_bilinen_deger(self):
        ciftler = [(0.5, 1)] * 10 + [(0.5, 0)] * 10
        self.assertAlmostEqual(m.brier(ciftler), 0.25, places=9)

    def test_auroc_mukemmel_ayirici(self):
        ciftler = [(0.9, 1)] * 10 + [(0.1, 0)] * 10
        self.assertAlmostEqual(m.auroc(ciftler), 1.0, places=9)

    def test_auroc_ayirt_edemeyen(self):
        ciftler = [(0.5, 1)] * 10 + [(0.5, 0)] * 10
        self.assertAlmostEqual(m.auroc(ciftler), 0.5, places=9)

    def test_mce_en_kotu_kovayi_verir(self):
        """PD-2: mce() uygulanmisti ama testi yoktu."""
        # iyi kova: guven 0.95, dogruluk 1.0 -> fark 0.05
        # kotu kova: guven 0.55, dogruluk 0.0 -> fark 0.55
        ciftler = [(0.95, 1)] * 20 + [(0.55, 0)] * 20
        self.assertAlmostEqual(m.mce(ciftler), 0.55, places=9)

    def test_mce_ece_den_buyuk_esit(self):
        ciftler = [(0.95, 1)] * 20 + [(0.55, 0)] * 20
        self.assertGreaterEqual(m.mce(ciftler), m.ece(ciftler))

    def test_mce_bos_girdide_none(self):
        self.assertIsNone(m.mce([]))

    def test_grup_ece_en_kotuyu_bulur(self):
        gruplu = {
            "buyuk": [(0.8, 1)] * 95 + [(0.8, 0)] * 5,
            "kucuk": [(0.9, 0)] * 5,
        }
        rapor = m.grup_ece(gruplu)
        self.assertEqual(rapor["en_kotu"][0], "kucuk")
        self.assertGreater(rapor["en_kotu"][1], rapor["gruplar"]["buyuk"])


# ----------------------------------------------------------------- Task 4

class OlculupYOKSAYILANTesti(unittest.TestCase):
    """Olculen bir uyari kapiyi ETKILEMIYORSA, olculmemis sayilir.

    Kod incelemesinin uc bulgusu ayni sinifta: sistem dogru teshisi
    KOYUYOR ama hukmu ona BAGLAMIYOR - yani fail-open. Tasarimin tezi
    fail-closed oldugu icin bunlar celiski.
    """

    def _tek_kovali_ciftler(self, n=40):
        """Tum guvenler AYNI kovaya duser -> ECE hicbir bilgi tasimaz."""
        return [(0.52 if i % 2 else 0.53, i % 2) for i in range(n)]

    def test_tek_bine_cokmus_ece_kalibrasyon_kanitini_SIFIRLAR(self):
        ciftler = self._tek_kovali_ciftler()
        duyarlilik = m.ece_duyarlilik(ciftler)
        self.assertTrue(duyarlilik["tek_bine_cokme"], "kurulum bozuk: cokme yok")
        s = m.shrinkage_katsayisi(dogru=30, toplam=40,
                                  ece_enkotu=m.ece(ciftler),
                                  dolu_kanal=6, toplam_kanal=6,
                                  ece_tek_bin=True)
        self.assertEqual(s["s_kalibrasyon"], 0.0)
        self.assertEqual(s["s"], 0.0)

    def test_cok_kovali_ece_kaniti_SIFIRLAMAZ(self):
        s = m.shrinkage_katsayisi(dogru=30, toplam=40, ece_enkotu=0.02,
                                  dolu_kanal=6, toplam_kanal=6,
                                  ece_tek_bin=False)
        self.assertGreater(s["s_kalibrasyon"], 0.0)

    def test_sinirda_sicaklik_kalibrasyon_kanitini_SIFIRLAR(self):
        """T izgara kenarinda ise fit TANIMSIZDIR; kanit sayilmaz."""
        s = m.shrinkage_katsayisi(dogru=30, toplam=40, ece_enkotu=0.02,
                                  dolu_kanal=6, toplam_kanal=6,
                                  sicaklik_sinirda=True)
        self.assertEqual(s["s_kalibrasyon"], 0.0)

    def test_s_kanit_TABAN_ORANA_gore_olculur(self):
        """%50 degil, kumenin KENDI cogunluk orani referanstir.

        Dengesiz etikette (or. taban 0.70) sabit-cogunluk tahmincisi
        %70 dogruluk alir ve BECERI YOKKEN stake kazanirdi. Etiket
        `16 bar icinde +1 ATR mi -1 ATR mi` trend penceresinde carpiktir,
        yani bu varsayimsal degil.
        """
        for n in (40, 100, 200):
            dogru = int(round(0.70 * n))
            beceriksiz = m.shrinkage_katsayisi(dogru, n, ece_enkotu=0.0,
                                               dolu_kanal=6, toplam_kanal=6,
                                               taban_oran=0.70)
            self.assertEqual(beceriksiz["s_kanit"], 0.0,
                             f"n={n}: taban orani kadar dogruluk BECERI DEGIL")

    def test_taban_oranin_uzerinde_kanit_hala_sayilir(self):
        s = m.shrinkage_katsayisi(dogru=95, toplam=100, ece_enkotu=0.0,
                                  dolu_kanal=6, toplam_kanal=6, taban_oran=0.70)
        self.assertGreater(s["s_kanit"], 0.0)

    def test_dengeli_etikette_eski_davranis_korunur(self):
        """taban 0.5 iken formul eski haliyle AYNI sonucu vermeli."""
        yeni = m.shrinkage_katsayisi(dogru=70, toplam=100, ece_enkotu=0.0,
                                     dolu_kanal=6, toplam_kanal=6, taban_oran=0.5)
        alt, _ = m.wilson_araligi(70, 100)
        self.assertAlmostEqual(yeni["s_kanit"],
                               m.kirp(2.0 * (alt - 0.5), 0.0, 1.0), places=12)

    def test_boru_hatti_taban_orani_izde_beyan_eder(self):
        iz = m.BoruHatti(tohum=2026).calistir(
            BoruHattiTesti("test_determinizm")._paket())["iz"]
        self.assertIn("taban_oran", iz["halka_8"])
        self.assertGreaterEqual(iz["halka_8"]["taban_oran"], 0.5)

    def test_boru_hatti_tek_bin_ve_sinirda_bayraklarini_TASIR(self):
        paket = BoruHattiTesti("test_determinizm")._paket()
        r = m.BoruHatti(tohum=2026).calistir(paket)
        h8 = r["iz"]["halka_8"]
        self.assertIn("ece_tek_bin", h8)
        self.assertIn("dolu_kova", h8)
        if h8["ece_tek_bin"] or r["iz"]["halka_7"]["sinirda"]:
            self.assertEqual(r["shrinkage"]["s_kalibrasyon"], 0.0,
                             "olculen uyari kapiyi etkilemiyor = fail-open")


class ShrinkageTesti(unittest.TestCase):
    def test_kanit_yoksa_s_sifir(self):
        r = m.shrinkage_katsayisi(dogru=17, toplam=48, ece_enkotu=0.02,
                                  dolu_kanal=5, toplam_kanal=5)
        self.assertEqual(r["s_kanit"], 0.0)
        self.assertEqual(r["s"], 0.0)

    def test_guclu_kanit_s_pozitif(self):
        r = m.shrinkage_katsayisi(dogru=900, toplam=1000, ece_enkotu=0.01,
                                  dolu_kanal=5, toplam_kanal=5)
        self.assertGreater(r["s_kanit"], 0.5)
        self.assertGreater(r["s"], 0.5)

    def test_kapsam_dususu_s_dusurur(self):
        tam = m.shrinkage_katsayisi(900, 1000, 0.01, 5, 5)["s"]
        yarim = m.shrinkage_katsayisi(900, 1000, 0.01, 2, 5)["s"]
        self.assertLess(yarim, tam)
        self.assertAlmostEqual(yarim / tam, 2 / 5, places=6)

    def test_kotu_kalibrasyon_s_dusurur(self):
        iyi = m.shrinkage_katsayisi(900, 1000, 0.00, 5, 5)["s"]
        kotu = m.shrinkage_katsayisi(900, 1000, 0.10, 5, 5)["s"]
        self.assertEqual(kotu, 0.0)
        self.assertGreater(iyi, 0.0)

    def test_ece_olculemedi_ise_s_sifir(self):
        r = m.shrinkage_katsayisi(900, 1000, None, 5, 5)
        self.assertEqual(r["s_kalibrasyon"], 0.0)
        self.assertEqual(r["s"], 0.0)

    def test_daralt_sifir_s_sansa_ceker(self):
        self.assertAlmostEqual(m.daralt(0.95, 0.0), 0.5, places=9)

    def test_daralt_bir_s_degistirmez(self):
        self.assertAlmostEqual(m.daralt(0.95, 1.0), 0.95, places=9)

    def test_daralt_ara_deger(self):
        self.assertAlmostEqual(m.daralt(0.90, 0.5), 0.70, places=9)


class ShrinkageKellyEntegrasyonTesti(unittest.TestCase):
    """Sozlesmenin cekirdegi: kanit yoksa f* matematigin kendisiyle 0 olur.

    NOT: bu testin ilk hali daralt(p, s) -> kelly() zincirini cagiriyordu ve
    f*=0.0905 verdi. Kok neden: 0.5 hedefli daraltma, odul asimetrikken
    (b>a) bahsin EV'sini sifirlamaz. Tarafsiz hedef basabas olasiligidir.
    Sozlesme artik stake_hesapla icinde garanti edilir.
    """

    def test_kanit_yokken_stake_sifir(self):
        r = m.shrinkage_katsayisi(17, 48, 0.02, 5, 5)
        b, a = m.net_kanatlar(R=2.0, cost_r=0.3)
        sonuc = m.stake_hesapla(0.95, r["s"], b, a)
        self.assertEqual(sonuc["f"], 0.0)

    def test_kanit_yokken_stake_sifir_her_geometride(self):
        r = m.shrinkage_katsayisi(17, 48, 0.02, 5, 5)
        for R, cost_r in ((1.3333, 0.6), (2.0, 0.3), (3.0, 0.1),
                          (5.0, 0.05), (1.5, 0.0)):
            b, a = m.net_kanatlar(R, cost_r)
            sonuc = m.stake_hesapla(0.95, r["s"], b, a)
            self.assertAlmostEqual(sonuc["f"], 0.0, places=12,
                                   msg=f"R={R} cost_r={cost_r} icin f* 0 olmali")

    def test_eski_zincir_neden_yetmiyordu(self):
        """Regresyon korumasi: 0.5 hedefli daraltma sozlesmeyi SAGLAMAZ."""
        b, a = m.net_kanatlar(R=2.0, cost_r=0.3)
        p_yanlis = m.daralt(0.95, 0.0, hedef=0.5)
        self.assertGreater(m.kelly_asimetrik(p_yanlis, b, a), 0.0)

    def test_guclu_kanitla_stake_pozitif(self):
        r = m.shrinkage_katsayisi(900, 1000, 0.01, 5, 5)
        b, a = m.net_kanatlar(R=3.0, cost_r=0.1)
        sonuc = m.stake_hesapla(0.85, r["s"], b, a)
        self.assertGreater(sonuc["f"], 0.0)

    def test_lambda_stake_olcekler(self):
        r = m.shrinkage_katsayisi(900, 1000, 0.01, 5, 5)
        b, a = m.net_kanatlar(R=3.0, cost_r=0.1)
        tam = m.stake_hesapla(0.85, r["s"], b, a, lam=1.0)["f"]
        ceyrek = m.stake_hesapla(0.85, r["s"], b, a, lam=0.25)["f"]
        self.assertAlmostEqual(ceyrek, tam * 0.25, places=12)

    def test_kazanc_kanadi_yoksa_bahis_imkansiz(self):
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        sonuc = m.stake_hesapla(0.99, 1.0, b, a)
        self.assertEqual(sonuc["f"], 0.0)
        self.assertIsNone(sonuc["p0"])
        self.assertIn("imkansiz", sonuc["not"])


# ----------------------------------------------------------------- Task 5

class EsikEtiketiTesti(unittest.TestCase):
    """PD-3: depo sozlesmesi (CLAUDE.md) etiketsiz gizli esigi YASAKLIYOR.

    Kalibre edilemeyen her sabit, kaynagi ve gerekcesiyle beyan edilmeli.
    """

    def test_esik_kaynagi_sozlugu_var(self):
        self.assertTrue(hasattr(m, "ESIK_KAYNAGI"))

    # Etiket gerektirmeyen sabitler: kimlik/yapisal, istatistiksel secim DEGIL.
    MUAF = {
        "SURUM", "SEMBOLLER", "YON_SOZLUGU", "EPSILON", "ESIK_KAYNAGI",
        "KANALLAR", "ZAMAN_DILIMLERI", "AILELER", "IZGARA", "LAMBDA_TABLOSU",
        "SICAKLIK_IZGARASI", "SEMBOL_EKSENI_FAZI",
    }

    def test_her_sabit_esik_etiketli(self):
        """Denetci bulgusu: sabit ad listesi YENI esikleri yakalayamiyordu.

        Artik modul TARANIYOR - eklenen her sayisal BUYUK_HARF sabiti ya
        ESIK_KAYNAGI'nda beyan edilmeli ya MUAF listesinde gerekcelenmeli.
        """
        etiketsiz = []
        for ad in dir(m):
            if (not ad.isupper() or ad.startswith("_")
                    or ad in self.MUAF or ad in _TEST_SABITLERI):
                continue
            if not isinstance(getattr(m, ad), (int, float)):
                continue
            if ad not in m.ESIK_KAYNAGI:
                etiketsiz.append(ad)
        self.assertEqual(etiketsiz, [],
                         f"etiketsiz gizli esik YASAK: {etiketsiz}")

    def test_etiket_zorunlu_alanlari_icerir(self):
        for ad, kayit in m.ESIK_KAYNAGI.items():
            for alan in ("deger", "kaynak", "gerekce"):
                self.assertIn(alan, kayit, f"{ad}.{alan} eksik")

    def test_etiket_degeri_gercek_sabitle_ayni(self):
        self.assertEqual(m.ESIK_KAYNAGI["ECE_TAVANI"]["deger"], m.ECE_TAVANI)
        self.assertEqual(m.ESIK_KAYNAGI["ASGARI_OLCUM"]["deger"], m.ASGARI_OLCUM)

    def test_kalibre_edilmemis_esik_acikca_beyan_edilir(self):
        """Kaynak 'VARSAYIM' ise gerekce bos birakilamaz."""
        for ad, kayit in m.ESIK_KAYNAGI.items():
            if kayit["kaynak"] == "VARSAYIM":
                self.assertTrue(kayit["gerekce"].strip(),
                                f"{ad} VARSAYIM ama gerekcesi bos")

    def test_esik_raporu_metin_uretir(self):
        metin = m.esik_raporu()
        self.assertIn("ECE_TAVANI", metin)
        self.assertIn("VARSAYIM", metin)


class GeometriTesti(unittest.TestCase):
    def test_ilk_gecis_ayni_barda_iki_bariyer_stop_sayilir(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 103, "l": 98, "c": 100},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["stop"], 1)
        self.assertEqual(r["hedef"], 0)

    def test_ilk_gecis_hedef_once(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 103, "l": 99.5, "c": 102},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["hedef"], 1)
        self.assertAlmostEqual(r["p_hedef"], 1.0, places=9)

    def test_ilk_gecis_zaman_asimi_paydaya_girmez(self):
        barlar = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 4
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0] * 4, azami_bar=2)
        self.assertEqual(r["zaman_asimi"], 1)
        self.assertIsNone(r["p_hedef"])

    def test_ilk_gecis_short_simetrik(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 100.5, "l": 97, "c": 98},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "SHORT", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["hedef"], 1)

    def test_beklenen_log_sifir_stake_sifir(self):
        self.assertAlmostEqual(m.beklenen_log(0.7, 0.0, 1.0, 1.0), 0.0, places=9)

    def test_beklenen_log_bilinen_deger(self):
        beklenen = 0.5 * math.log(1.1) + 0.5 * math.log(0.9)
        self.assertAlmostEqual(m.beklenen_log(0.5, 0.1, 1.0, 1.0), beklenen, places=9)

    def test_beklenen_log_iflas_riskinde_sonsuz_negatif(self):
        self.assertEqual(m.beklenen_log(0.5, 1.0, 1.0, 1.0), float("-inf"))


# ----------------------------------------------------------------- Task 6

class BariyerTekKaynakTesti(unittest.TestCase):
    """OLCULEN bariyer ile YAYINLANAN seviye AYNI nesne olmali.

    Iki yerde bagimsiz hesaplaniyordu (`ilk_gecis_olcum` ve `seviyeler`).
    Ayrisirlarsa p_hedef, yayinlanan stop/hedeften BASKA bariyerler icin
    olculmus olur - hem de sessizce.
    """

    def _barlar(self, n=200):
        rng = m.tohumlu_rng("bariyer")
        barlar, fiyat = [], 100.0
        for _ in range(n):
            fiyat *= 1.0 + rng.uniform(-0.003, 0.003)
            barlar.append({"o": fiyat, "h": fiyat * 1.004, "l": fiyat * 0.996,
                           "c": fiyat, "v": 100.0})
        return barlar

    def test_olcum_seviyeler_fonksiyonunu_KULLANIR(self):
        kaynak = inspect.getsource(m.ilk_gecis_olcum)
        self.assertIn("seviyeler(", kaynak,
                      "bariyer ikinci kez elle hesaplanamaz")
        self.assertNotIn("giris - stop_k * atr_deger", kaynak)
        self.assertNotIn("giris + stop_k * atr_deger", kaynak)

    def test_iki_yol_ayni_seviyeleri_verir(self):
        for yon in ("LONG", "SHORT"):
            for stop_k, hedef_k in ((1.0, 2.0), (1.5, 3.0), (2.0, 6.0)):
                s = m.seviyeler(100.0, 2.0, yon, stop_k, hedef_k)
                isaret = 1.0 if yon == "LONG" else -1.0
                self.assertAlmostEqual(s["stop"], 100.0 - isaret * stop_k * 2.0,
                                       places=12)
                self.assertAlmostEqual(s["hedef"], 100.0 + isaret * hedef_k * 2.0,
                                       places=12)

    def test_olcum_yayinlanan_bariyerle_TUTARLI(self):
        """Ayni (giris, atr, yon, k) icin olcum ve cikti ayni sinirlari gorur."""
        barlar = self._barlar()
        atr_serisi = m.atr(barlar)
        i = 100
        olcum = m.ilk_gecis_olcum(barlar, [i], "LONG", 1.5, 3.0, atr_serisi, 32)
        sev = m.seviyeler(barlar[i]["c"], atr_serisi[i], "LONG", 1.5, 3.0)
        # Bariyerleri ELLE yeniden kurup olcumu tekrar uret: ayni cikmali
        vurus = None
        for j in range(i + 1, min(len(barlar), i + 33)):
            if barlar[j]["l"] <= sev["stop"]:
                vurus = "stop"
                break
            if barlar[j]["h"] >= sev["hedef"]:
                vurus = "hedef"
                break
        beklenen = {"stop": olcum["stop"], "hedef": olcum["hedef"]}
        if vurus:
            self.assertEqual(beklenen[vurus], 1, f"{vurus} sayimi tutmadi")
        else:
            self.assertEqual(olcum["zaman_asimi"], 1)


class BasabasReferansiTesti(unittest.TestCase):
    """Raporlanan p_kullanilan, modulun kendi "hata" dedigi referansa DUSEMEZ.

    `hedef=(geo.get("basabas_p") or 0.5)` iki ayri kusur tasiyordu:
    (1) geometri fail-closed dondugunde referans 0.5 oluyordu - PD-1'de
        tam olarak bu referans "kok neden" diye kayda gecmisti;
    (2) `or` mesru bir 0.0'i da EKSIK sayiyordu.
    Olculemeyen bir sey uydurulmaz: basabas yoksa p_kullanilan VERI YOK.
    """

    def _baglam(self, olculebilir):
        rng = m.tohumlu_rng("basabas-ref")
        barlar, fiyat = [], 100.0
        n = 300 if olculebilir else 30
        for _ in range(n):
            fiyat *= 1.0 + rng.uniform(-0.002, 0.004)
            barlar.append({"o": fiyat, "h": fiyat * 1.004, "l": fiyat * 0.996,
                           "c": fiyat, "v": 100.0})
        atr_serisi = m.atr(barlar)
        return {"sembol": "X", "barlar": barlar, "atr_serisi": atr_serisi,
                "indeksler": list(range(m.ISINMA_BARI, max(m.ISINMA_BARI + 1,
                                                           len(barlar) - 40))),
                "p_ham": 0.8, "dogru": 30, "toplam": 40, "ece_enkotu": 0.02,
                "dolu_kanal": 6, "toplam_kanal": 6,
                "giris": barlar[-1]["c"], "atr": atr_serisi[-1],
                "likidasyon": None, "kaldirac_azami": None,
                "komisyon": 0.0004, "kayma": 0.0005, "funding": 0.0,
                "lam": 1.0}

    def test_basabas_olculemezse_p_kullanilan_VERI_YOK(self):
        karar = m.karar_uret(self._baglam(olculebilir=False))
        self.assertIsNone(karar["geometri"]["basabas_p"],
                          "kurulum bozuk: basabas olculebilmis")
        self.assertIsNone(karar["p_kullanilan"])
        self.assertIn("VERI YOK", m.metin_rapor(karar))

    def test_basabas_olculebilirse_p_kullanilan_ONA_daraltilir(self):
        karar = m.karar_uret(self._baglam(olculebilir=True))
        p0 = karar["geometri"]["basabas_p"]
        self.assertIsNotNone(p0, "kurulum bozuk: basabas olculememis")
        p_yon = karar["p_ham"] if karar["yon"] == "LONG" else 1.0 - karar["p_ham"]
        self.assertAlmostEqual(
            karar["p_kullanilan"],
            m.daralt(p_yon, karar["shrinkage"]["s"], hedef=p0), places=12)

    def test_sifir_basabas_EKSIK_sayilmaz(self):
        """`or` deyimi mesru 0.0'i None gibi ele aliyordu."""
        self.assertEqual(m._basabas_referansi({"basabas_p": 0.0}), 0.0)
        self.assertIsNone(m._basabas_referansi({"basabas_p": None}))
        self.assertIsNone(m._basabas_referansi({}))


class SecimYanliligiTesti(unittest.TestCase):
    """11 aday arasindan argmax, secim cezasi olmadan yapilamaz.

    Ayni 40 test ornegi hem p_hedef'i OLCUYOR hem kazanan geometriyi
    SECIYOR. Nokta tahmini uzerinden argmax, gurultuyu kenar sanir:
    olculdu ki kazananin elog'u 1.5e-06 ve p_hedef'in SE'si ~0.074 iken
    kazanan basabasi ~0.016 SE ile geciyordu. `elog <= 0 -> f=0` kapisi
    ISARETI yakalar, "gurultu icinde pozitif"i yakalamaz.

    Cozum modulun KENDI deyimi: kanit, nokta tahminiyle degil Wilson ALT
    siniriyla olculur (shrinkage_katsayisi zaten boyle yapiyor).
    """

    def _barlar(self, n=500, tohum="secim"):
        rng = m.tohumlu_rng(tohum)
        barlar, fiyat = [], 100.0
        for _ in range(n):
            fiyat *= 1.0 + rng.uniform(-0.002, 0.004)
            barlar.append({"o": fiyat, "h": fiyat * 1.004, "l": fiyat * 0.996,
                           "c": fiyat, "v": 100.0})
        return barlar

    def _sec(self, p_yon=0.6, tohum="secim"):
        barlar = self._barlar(tohum=tohum)
        atr_serisi = m.atr(barlar)
        indeksler = list(range(m.ISINMA_BARI, len(barlar) - 40))
        return m.geometri_sec(barlar, indeksler, "LONG", atr_serisi,
                              p_yon=p_yon, cost_r_fn=lambda k: 0.001)

    def test_adaylar_p_hedef_ALT_SINIRINI_tasir(self):
        for aday in self._sec()["denenen"]:
            if aday.get("p_hedef") is None:
                continue
            self.assertIn("p_hedef_alt", aday)
            self.assertLessEqual(aday["p_hedef_alt"], aday["p_hedef"])

    def test_secim_ALT_SINIR_uzerinden_yapilir(self):
        """Kazanan, nokta tahmininin degil alt sinirin argmax'i olmali."""
        secim = self._sec()
        gecerli = [a for a in secim["denenen"] if a.get("elog") is not None]
        self.assertTrue(gecerli, "kurulum bozuk: gecerli aday yok")
        en_iyi = max(gecerli, key=lambda a: a["elog"])
        self.assertEqual((secim["stop_k"], secim["hedef_k"]),
                         (en_iyi["stop_k"], en_iyi["hedef_k"]))
        # elog artik alt sinirdan uretilmis p ile hesaplanmali
        self.assertIn("p_bilesik_alt", secim)

    def test_az_ornekli_aday_CEZALANIR(self):
        """Ayni p_hedef'te n kucukse alt sinir duser, aday geri kalir."""
        genis = m.wilson_araligi(30, 40)[0]
        dar = m.wilson_araligi(75, 100)[0]
        self.assertLess(genis, dar, "kurulum bozuk: alt sinir n ile artmali")

    def test_gurultu_icinde_pozitif_elog_stake_URETMEZ(self):
        """Alt sinir basabasin altindaysa f=0 olmali (fail-closed)."""
        secim = self._sec(p_yon=0.5001)
        if secim.get("p_bilesik_alt") is not None and secim.get("basabas_p"):
            if secim["p_bilesik_alt"] <= secim["basabas_p"]:
                self.assertEqual(secim["f"], 0.0)


class GeometriDaireselTesti(unittest.TestCase):
    """Kazanan geometri, denenen listesinin ICINDE olamaz (dairesel referans).

    Bulundu: `en_iyi["denenen"] = denenen` satiri, en_iyi zaten denenen'in
    bir ELEMANI oldugu icin kendine referans yaratiyordu. Sonuc: bir
    geometri KAZANDIGI anda karar JSON'a serilesemiyor ("Circular reference
    detected"). Kusur, yalniz fail-closed dal (en_iyi is None) calisirken
    gizli kaliyordu - yani sistem DOGRU calistiginda bozuluyordu.
    """

    def _barlar(self, n=400):
        rng = m.tohumlu_rng("dairesel")
        barlar, fiyat = [], 100.0
        for _ in range(n):
            fiyat *= 1.0 + rng.uniform(-0.002, 0.004)
            barlar.append({"o": fiyat, "h": fiyat * 1.004, "l": fiyat * 0.996,
                           "c": fiyat, "v": 100.0})
        return barlar

    def _sec(self):
        barlar = self._barlar()
        atr_serisi = m.atr(barlar)
        indeksler = list(range(m.ISINMA_BARI, len(barlar) - 40))
        return m.geometri_sec(barlar, indeksler, "LONG", atr_serisi,
                              p_yon=0.6, cost_r_fn=lambda k: 0.001)

    def test_kazanan_geometri_serilesebilir(self):
        secim = self._sec()
        self.assertTrue(secim["denenen"], "kurulum bozuk: hic aday denenmemis")
        json.dumps(secim)      # dairesel referansta ValueError yukselir

    def test_kazanan_denenen_listesinin_elemani_DEGIL(self):
        secim = self._sec()
        for aday in secim["denenen"]:
            self.assertIsNot(aday, secim,
                             "kazanan, kendi denenen listesinin elemani olamaz")

    def test_denenen_adaylari_kendi_denenenini_TASIMAZ(self):
        for aday in self._sec()["denenen"]:
            self.assertNotIn("denenen", aday)


class GeometriSecimTesti(unittest.TestCase):
    def _yukselen_barlar(self, n=200):
        barlar = []
        fiyat = 100.0
        for _ in range(n):
            fiyat *= 1.002
            barlar.append({"o": fiyat, "h": fiyat * 1.004,
                           "l": fiyat * 0.999, "c": fiyat})
        return barlar

    def test_geometri_sec_bir_aday_dondurur(self):
        barlar = self._yukselen_barlar()
        atr = [b["c"] * 0.003 for b in barlar]
        indeksler = list(range(0, 150, 5))
        r = m.geometri_sec(barlar, indeksler, "LONG", atr, p_yon=0.6,
                           cost_r_fn=lambda sk: 0.05, lam=1.0, azami_bar=20)
        for alan in ("stop_k", "hedef_k", "R", "p_hedef", "elog"):
            self.assertIn(alan, r)
        self.assertIn((r["stop_k"], r["hedef_k"]), m.IZGARA)

    def test_geometri_sec_olcum_yoksa_fail_closed(self):
        barlar = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 5
        atr = [1.0] * 5
        r = m.geometri_sec(barlar, [0], "LONG", atr, 0.9,
                           lambda sk: 0.05, 1.0, azami_bar=2)
        self.assertEqual(r["f"], 0.0)
        self.assertIsNone(r["p_hedef"])
        self.assertIn("OLCUM YOK", r["not"])

    def test_geometri_sec_yuksek_maliyette_stake_sifir(self):
        barlar = self._yukselen_barlar()
        atr = [b["c"] * 0.003 for b in barlar]
        r = m.geometri_sec(barlar, list(range(0, 150, 5)), "LONG", atr, 0.6,
                           cost_r_fn=lambda sk: 5.0, lam=1.0, azami_bar=20)
        self.assertEqual(r["f"], 0.0)

    def test_likidasyon_tavani_okunamazsa_sifir(self):
        self.assertEqual(m.likidasyon_tavani(100.0, None, 100.0, 0.5), 0.0)

    def test_likidasyon_tavani_mesafeden_gelir(self):
        tavan = m.likidasyon_tavani(100.0, 80.0, 10.0, 0.5)
        self.assertAlmostEqual(tavan, 0.10, places=9)

    def test_stake_kirp_kirpma_bildirilir(self):
        r = m.stake_kirp(0.5, 0.1)
        self.assertAlmostEqual(r["f"], 0.1, places=9)
        self.assertTrue(r["kirpildi"])

    def test_stake_kirp_kirpma_yoksa_bayrak_kapali(self):
        r = m.stake_kirp(0.05, 0.1)
        self.assertAlmostEqual(r["f"], 0.05, places=9)
        self.assertFalse(r["kirpildi"])


# ----------------------------------------------------------------- Task 7

class PaketKurTesti(unittest.TestCase):
    """veri_topla ciktisi ile calistir girdisi arasindaki KOPRU.

    Bu koprusuz sistem KULLANILAMAZ: veri_topla ham Binance JSON'u
    donduruyordu, calistir ise {barlar15, barlar4h, turev_serisi, ...}
    bekliyordu ve arada hicbir sey yoktu.
    """

    def _kline(self, n, taban=100.0, adim_ms=900000):
        """Binance USD-M kline bicimi: 12 alanli liste."""
        satirlar, fiyat = [], taban
        rng = m.tohumlu_rng("paket-kur")
        for i in range(n):
            fiyat *= 1.0 + rng.uniform(-0.003, 0.003)
            hacim = 100.0 + rng.uniform(0, 50)
            satirlar.append([
                i * adim_ms,                      # 0 acilis zamani
                f"{fiyat:.8f}",                   # 1 acilis
                f"{fiyat * 1.002:.8f}",           # 2 yuksek
                f"{fiyat * 0.998:.8f}",           # 3 dusuk
                f"{fiyat:.8f}",                   # 4 kapanis
                f"{hacim:.8f}",                   # 5 hacim
                i * adim_ms + adim_ms - 1,        # 6 kapanis zamani
                f"{hacim * fiyat:.8f}",           # 7 kote hacim
                50,                               # 8 islem sayisi
                f"{hacim * 0.55:.8f}",            # 9 taker alis hacmi
                f"{hacim * 0.55 * fiyat:.8f}",    # 10 taker alis kote
                "0",                              # 11 yoksay
            ])
        return satirlar

    def _toplama(self, oi=True, taker=True, funding=True, derinlik=True):
        n = 400
        k15 = self._kline(n)
        kanallar = {
            "kline_15m": k15,
            "kline_4h": self._kline(n // 16, adim_ms=14400000),
            "oi": ([{"sumOpenInterest": f"{1000 + i:.2f}",
                     "timestamp": k15[i][0]} for i in range(n)] if oi else None),
            "funding": ({"lastFundingRate": "0.0001"} if funding else None),
            "taker": ([{"buySellRatio": f"{1.0 + 0.1 * (i % 5):.4f}",
                        "timestamp": k15[i][0]} for i in range(n)]
                      if taker else None),
            "derinlik": ({"bids": [["100.0", "5.0"]],
                          "asks": [["100.1", "3.0"]]} if derinlik else None),
        }
        dolu = sum(1 for v in kanallar.values() if v is not None)
        return {"adaptor": "binance", "kanallar": kanallar,
                "kapsam": dolu / len(m.KANALLAR), "dusen": [],
                "yedege_dusuldu": False}

    def test_paket_calistir_tarafindan_TUKETILEBILIR(self):
        paket = m.paket_kur("BTCUSDT", self._toplama())
        r = m.BoruHatti(tohum=2026).calistir(paket)
        self.assertIn(r["yon"], list(m.YON_SOZLUGU) + ["VERI YOK"])
        self.assertEqual(r["sembol"], "BTCUSDT")

    def test_kline_alanlari_DOGRU_esleniyor(self):
        paket = m.paket_kur("BTCUSDT", self._toplama())
        ham = self._toplama()["kanallar"]["kline_15m"][0]
        bar = paket["barlar15"][0]
        self.assertAlmostEqual(bar["o"], float(ham[1]), places=8)
        self.assertAlmostEqual(bar["h"], float(ham[2]), places=8)
        self.assertAlmostEqual(bar["l"], float(ham[3]), places=8)
        self.assertAlmostEqual(bar["c"], float(ham[4]), places=8)
        self.assertAlmostEqual(bar["v"], float(ham[5]), places=8)

    def test_ANLIK_kanal_seriye_CEVRILMEZ_ve_kapsami_BUYUTMEZ(self):
        """funding/derinlik tek anlik degerdir; tum barlara yazmak KN-1 tuzagi.

        Tek deger tum barlara yazilirsa kolon std=0 olur, Olcekleyici onu
        dogru bicimde sifirlar ve bilgi modele HIC ulasmaz - ama kapsam
        skoru "dolu" saymaya devam ederdi. Bu fail-open'dir.
        """
        paket = m.paket_kur("BTCUSDT", self._toplama())
        # 6 kanalin 2'si (funding, derinlik) ANLIK -> seri degil -> sayilmaz
        self.assertEqual(paket["dolu_kanal"], 4)
        self.assertEqual(paket["toplam_kanal"], len(m.KANALLAR))
        self.assertIn("anlik_kanallar", paket)
        self.assertEqual(sorted(paket["anlik_kanallar"]), ["derinlik", "funding"])

    def test_eksik_turev_kanali_kapsami_DUSURUR(self):
        tam = m.paket_kur("BTCUSDT", self._toplama())
        eksik = m.paket_kur("BTCUSDT", self._toplama(oi=False))
        self.assertLess(eksik["dolu_kanal"], tam["dolu_kanal"])

    def test_turev_serisi_SERIDIR_sabit_degil(self):
        """Seri gercekten degisiyor mu - std=0 tuzagina dusuluyor mu."""
        paket = m.paket_kur("BTCUSDT", self._toplama())
        seri = paket["turev_serisi"]
        # i=0'da onceki bar YOK: oi_degisim OLCULEMEZ ve anahtar
        # YAZILMAZ (0.0 enjekte edilmez). Olculebilen barlara bakilir.
        oi = [x["oi_degisim"] for x in seri if "oi_degisim" in x]
        taker = [x["taker_dengesi"] for x in seri if "taker_dengesi" in x]
        cvd = [x["cvd"] for x in seri]
        self.assertEqual(len(oi), len(seri) - 1, "yalniz ilk bar olculemez")
        self.assertGreater(len(set(oi)), 1, "oi serisi sabit - bilgi tasimiyor")
        self.assertGreater(len(set(taker)), 1, "taker serisi sabit")
        self.assertEqual(len(cvd), len(seri), "CVD her bardan hesaplanabilir")

    def test_kline_yoksa_fail_closed(self):
        toplama = self._toplama()
        toplama["kanallar"]["kline_15m"] = None
        with self.assertRaises(ValueError):
            m.paket_kur("BTCUSDT", toplama)

    def test_4h_yoksa_paket_yine_kurulur(self):
        toplama = self._toplama()
        toplama["kanallar"]["kline_4h"] = None
        paket = m.paket_kur("BTCUSDT", toplama)
        self.assertIsNone(paket["barlar4h"])
        r = m.BoruHatti(tohum=2026).calistir(paket)
        self.assertFalse(r["iz"]["halka_1"]["h4_var"])


class AdaptorTesti(unittest.TestCase):
    def test_kapsam_tam_veride_bir(self):
        def sahte_getir(url, params):
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertEqual(r["kapsam"], 1.0)
        self.assertEqual(r["adaptor"], "binance")
        self.assertEqual(r["dusen"], [])

    def test_kanal_dusunce_kapsam_duser_ve_uydurulmaz(self):
        def sahte_getir(url, params):
            if "openInterest" in url:
                raise OSError("erisilemedi")
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertLess(r["kapsam"], 1.0)
        self.assertIsNone(r["kanallar"]["oi"])
        self.assertIn("oi", r["dusen"])

    def test_ana_adaptor_tamamen_duserse_yedege_gecer_ve_bildirir(self):
        def sahte_getir(url, params):
            if "binance" in url:
                raise OSError("403")
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor(), m.OkxAdaptor()], sahte_getir)
        self.assertEqual(r["adaptor"], "okx")
        self.assertTrue(r["yedege_dusuldu"])

    def test_hicbir_adaptor_calismazsa_kapsam_sifir(self):
        def sahte_getir(url, params):
            raise OSError("hepsi kapali")
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor(), m.OkxAdaptor()], sahte_getir)
        self.assertEqual(r["kapsam"], 0.0)
        self.assertTrue(all(v is None for v in r["kanallar"].values()))

    def test_notr_sifir_enjekte_edilmez(self):
        """Uydurma yasagi: dusen kanal None olmali, 0.0 OLMAMALI."""
        def sahte_getir(url, params):
            if "premiumIndex" in url or "funding-rate" in url:
                raise OSError("yok")
            return {"ok": True, "veri": [1]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertIsNone(r["kanallar"]["funding"])
        self.assertNotEqual(r["kanallar"]["funding"], 0.0)

    def test_okx_sembol_cevrimi(self):
        u, _ = m.OkxAdaptor().uc("kline_15m", "BTCUSDT")
        self.assertIn("BTC-USDT-SWAP", str(_))

    def test_binance_dogru_period_parametresi(self):
        """OKX SDK'da parametre adi 'period'; 'periodic' gecersizdir."""
        _, params = m.BinanceAdaptor().uc("oi", "BTCUSDT")
        self.assertIn("period", params)
        self.assertNotIn("periodic", params)

    def test_okx_dogru_period_parametresi(self):
        _, params = m.OkxAdaptor().uc("oi", "BTCUSDT")
        self.assertIn("period", params)
        self.assertNotIn("periodic", params)

    def test_hicbir_adaptor_emir_ucu_uretmez(self):
        for adaptor in (m.BinanceAdaptor(), m.OkxAdaptor()):
            for kanal in m.KANALLAR:
                url, _ = adaptor.uc(kanal, "BTCUSDT")
                self.assertNotIn("order", url.lower())
                self.assertNotIn("trade", url.lower())


# ----------------------------------------------------------------- Task 8

class KapsamSecimiTesti(unittest.TestCase):
    """Ilk kapsam>0 veren adaptor degil, EN YUKSEK kapsamli olan secilir.

    Kapsam dogrudan stake'i belirler (s_kapsam). 1/6 kanal donduren ana
    adaptorde kalmak, 6/6 donebilecek yedegi hic denememek demektir -
    yani olculebilir bilgiyi gerekcesiz atmak.
    """

    class _Sahte(m.Adaptor):
        def __init__(self, ad, calisan):
            self.ad = ad
            self.calisan = set(calisan)

        def uc(self, kanal, sembol):
            return (f"https://ornek/{self.ad}/{kanal}", {"symbol": sembol})

    def _getir(self, url, params):
        ad, kanal = url.split("/")[-2], url.split("/")[-1]
        for a in self._adaptorler:
            if a.ad == ad and kanal in a.calisan:
                return {"kanal": kanal}
        raise RuntimeError("kanal yok")

    def test_yuksek_kapsamli_yedek_TERCIH_EDILIR(self):
        zayif = self._Sahte("zayif", ["kline_15m"])
        guclu = self._Sahte("guclu", m.KANALLAR)
        self._adaptorler = [zayif, guclu]
        r = m.veri_topla("BTCUSDT", self._adaptorler, self._getir)
        self.assertEqual(r["adaptor"], "guclu")
        self.assertAlmostEqual(r["kapsam"], 1.0, places=9)

    def test_esitlikte_ILK_adaptor_korunur(self):
        a = self._Sahte("a", ["kline_15m", "kline_4h"])
        b = self._Sahte("b", ["kline_15m", "kline_4h"])
        self._adaptorler = [a, b]
        r = m.veri_topla("BTCUSDT", self._adaptorler, self._getir)
        self.assertEqual(r["adaptor"], "a", "esitlikte ana adaptor korunmali")

    def test_hicbiri_veri_vermezse_fail_closed(self):
        bos = self._Sahte("bos", [])
        self._adaptorler = [bos]
        r = m.veri_topla("BTCUSDT", self._adaptorler, self._getir)
        self.assertIsNone(r["adaptor"])
        self.assertEqual(r["kapsam"], 0.0)


class TokenSozluguTesti(unittest.TestCase):
    def test_ayni_anahtar_ayni_kimlik(self):
        s = m.TokenSozlugu()
        self.assertEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                         s.kimlik("BTCUSDT", "15m", "fiyat", 0))

    def test_farkli_zaman_dilimi_farkli_kimlik(self):
        s = m.TokenSozlugu()
        self.assertNotEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                            s.kimlik("BTCUSDT", "4h", "fiyat", 0))

    def test_farkli_gecikme_farkli_kimlik(self):
        s = m.TokenSozlugu()
        self.assertNotEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                            s.kimlik("BTCUSDT", "15m", "fiyat", 1))

    def test_sozluk_buyur(self):
        s = m.TokenSozlugu()
        self.assertEqual(s.boyut, 0)
        s.kimlik("BTCUSDT", "15m", "fiyat", 0)
        s.kimlik("BTCUSDT", "15m", "fiyat", 1)
        self.assertEqual(s.boyut, 2)

    def test_token_listesi_iki_zaman_dilimi_icerir(self):
        tokenlar = m.token_listesi(["BTCUSDT"], gecikme_sayisi=2)
        zamanlar = {t["zaman_dilimi"] for t in tokenlar}
        self.assertEqual(zamanlar, set(m.ZAMAN_DILIMLERI))

    def test_token_listesi_beklenen_sayida(self):
        tokenlar = m.token_listesi(["BTCUSDT", "ETHUSDT"], gecikme_sayisi=3)
        beklenen = 2 * len(m.ZAMAN_DILIMLERI) * len(m.AILELER) * 3
        self.assertEqual(len(tokenlar), beklenen)

    def test_turev_ailesi_sozlukte_var(self):
        self.assertIn("turev", m.AILELER)

    def test_token_listesi_eskiden_yeniye_sirali(self):
        tokenlar = m.token_listesi(["BTCUSDT"], gecikme_sayisi=3)
        gecikmeler = [t["gecikme"] for t in tokenlar]
        self.assertEqual(gecikmeler[0], 2)
        self.assertEqual(gecikmeler[-1], 0)


# ----------------------------------------------------------------- Task 9

class OlcekleyiciTesti(unittest.TestCase):
    def _satirlar(self, n=100):
        return [{"fiyat": [i * 0.01] * m.AILELER["fiyat"],
                 "hacim": [0.0] * m.AILELER["hacim"],
                 "turev": [i * 0.02] * m.AILELER["turev"],
                 "oynaklik": [1.0] * m.AILELER["oynaklik"]} for i in range(n)]

    def test_yalniz_train_diliminden_fit(self):
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        o2 = m.Olcekleyici()
        o2.fit(satirlar[:50], kesim=50)
        self.assertEqual(o.donustur("fiyat", [0.25] * m.AILELER["fiyat"]),
                         o2.donustur("fiyat", [0.25] * m.AILELER["fiyat"]))

    def test_sabit_kolon_isaretlenir(self):
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        self.assertIn(("hacim", 0), o.sabit_kolonlar)

    def test_sabit_kolonda_donusum_sifir_verir(self):
        """Sabit kolon bilgi tasimaz: ham deger SIZDIRILMAZ, 0.0 verilir."""
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        self.assertEqual(o.donustur("hacim", [999.0, 999.0]), [0.0, 0.0])

    def test_fit_edilmeden_donusum_hata_verir(self):
        o = m.Olcekleyici()
        with self.assertRaises(RuntimeError):
            o.donustur("fiyat", [0.0] * m.AILELER["fiyat"])


class KonumKoduTesti(unittest.TestCase):
    def test_zaman_konumu_gecikmeye_gore_degisir(self):
        self.assertNotEqual(m.zaman_konumu(0, 16), m.zaman_konumu(1, 16))

    def test_zaman_konumu_deterministik(self):
        self.assertEqual(m.zaman_konumu(3, 16), m.zaman_konumu(3, 16))

    def test_sembol_konumu_ayri_eksen(self):
        """Sembol ekseni zaman ekseninden BAGIMSIZ olmali."""
        z0 = m.zaman_konumu(0, 16)
        s0 = m.sembol_konumu(0, 16)
        s1 = m.sembol_konumu(1, 16)
        self.assertNotEqual(s0, s1)
        self.assertNotEqual(s0, z0)

    def test_konum_boyutu_dogru(self):
        self.assertEqual(len(m.zaman_konumu(2, 16)), 16)
        self.assertEqual(len(m.sembol_konumu(2, 16)), 16)

    def test_ayni_indekste_iki_eksen_ayrisir(self):
        """Ayni sayisal indeks, iki eksende FARKLI vektor uretmeli."""
        for k in range(1, 5):
            self.assertNotEqual(m.zaman_konumu(k, 16), m.sembol_konumu(k, 16))

    def _l2(self, a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def test_faz_olculen_ayrisma_degeri(self):
        """SEMBOL_EKSENI_FAZI docstring'indeki SAYIYI kilitler.

        Denetci bulgusu (SAHTE_KANIT): docstring'e once boyut=4 ve olceksiz
        bir deneme kosusundan alinan 1.08..1.58 yazilmisti; fonksiyonun
        gercek ciktisi (boyut=16, 0.10 olcek) 0.2165..0.2970'tir. Bu test
        sayiyi artefakta baglar - bir daha kaynaksiz sayi yazilamaz.
        """
        beklenen = [0.216478, 0.243442, 0.270609, 0.297025]
        for k, deger in enumerate(beklenen):
            self.assertAlmostEqual(
                self._l2(m.zaman_konumu(k, 16), m.sembol_konumu(k, 16)),
                deger, places=6, msg=f"konum={k} icin olculen deger degisti")

    def test_fazsiz_kurulum_sifirda_tam_cakisir(self):
        """Fazin NEDEN gerekli oldugunun kaniti: fazsiz L2 tam 0."""
        fazsiz = [x * 0.10 for x in m._sinuzoidal(0, 16, 97.0, faz=0.0)]
        self.assertAlmostEqual(self._l2(m.zaman_konumu(0, 16), fazsiz),
                               0.0, places=12)


# ---------------------------------------------------------------- Task 10

class SabitIzdusumTesti(unittest.TestCase):
    """Giris izdusumu OGRENILMEZ - sabit rastgele izdusumdur. BEYAN EDILIR.

    Plan ve tasarim belgesi "ogrenilen giris izdusumu" diyordu; kod bunu
    hicbir zaman guncellemiyor. Bu bir eksiklik olarak DEGIL, olculmus bir
    tasarim kararı olarak kayda gecer: izdusum 256 parametre tasir ve
    egitim dilimi 86 ornektir (~3 parametre/ornek). O parametreleri bu
    orneklem buyuklugunde egitmek asiri-uyumdur; sabit rastgele izdusum +
    egitilen kucuk baslik (102 parametre) bilincli secimdir.

    Halka OLU DEGILDIR: izdusum degisince cikti degisir - yalniz
    OGRENILMEZ.
    """

    def test_izdusum_kosu_boyunca_DEGISMEZ(self):
        bh = m.BoruHatti(tohum=2026)
        once = {a: [list(satir) for satir in mat]
                for a, mat in bh.giris_izdusumu.items()}
        bh.calistir(BoruHattiTesti("test_determinizm")._paket())
        for aile, mat in bh.giris_izdusumu.items():
            for i, satir in enumerate(mat):
                self.assertEqual(list(satir), once[aile][i],
                                 f"{aile}: izdusum egitiliyormus gibi degisti")

    def test_izdusum_OLU_DEGIL_ciktiyi_belirler(self):
        """Sabit olmak olu olmak degildir: degistirince karar degismeli."""
        paket = BoruHattiTesti("test_determinizm")._paket()
        taban = m.BoruHatti(tohum=2026).calistir(paket)["p_ham"]
        bh = m.BoruHatti(tohum=2026)
        for mat in bh.giris_izdusumu.values():
            for satir in mat:
                for j in range(len(satir)):
                    satir[j] = -satir[j]
        self.assertNotAlmostEqual(bh.calistir(paket)["p_ham"], taban, places=9)

    def test_parametre_orneklem_orani_OLCULUR(self):
        """Sapmanin gerekcesi sayidir, anlati degil."""
        bh = m.BoruHatti(tohum=2026)
        izdusum_p = sum(len(mat) * len(mat[0])
                        for mat in bh.giris_izdusumu.values())
        baslik_p = (2 * bh.boyut + 2) * 3
        self.assertEqual(izdusum_p, 256)
        self.assertEqual(baslik_p, 102)
        train = bh.calistir(BoruHattiTesti("test_determinizm")._paket())
        n = train["iz"]["halka_6"]["train_ornek"]
        self.assertGreater(izdusum_p / n, 2.0,
                           "izdusum egitilseydi parametre/ornek orani asiri olurdu")


class OluHalkaTesti(unittest.TestCase):
    """Sozlesmenin 1. kabul olcutu: hicbir halka olu olmamali.

    Her halka icin, o halka devre disi birakilinca nihai ciktinin
    OLCULEBILIR bicimde degistigi kanitlanir.
    """

    def _kodlayici_ve_durumlar(self, n=9, d=16):
        kod = m.Kodlayici(boyut=d, bas_sayisi=2, tohum=2026)
        rng = m.tohumlu_rng("test-durum", n, d)
        durumlar = [[rng.uniform(-1, 1) for _ in range(d)] for _ in range(n)]
        return kod, durumlar

    def _fark(self, a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def test_qk_terimi_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        self.assertGreater(
            self._fark(kod.ileri(durumlar, qk_acik=True),
                       kod.ileri(durumlar, qk_acik=False)), 1e-6,
            "QK terimi ciktiyi degistirmiyor -> olu halka")

    def test_nedensel_maske_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        self.assertGreater(
            self._fark(kod.ileri(durumlar, maske_acik=True),
                       kod.ileri(durumlar, maske_acik=False)), 1e-6,
            "Nedensel maske ciktiyi degistirmiyor -> olu halka")

    def test_ffn_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        self.assertGreater(
            self._fark(kod.ileri(durumlar, ffn_acik=True),
                       kod.ileri(durumlar, ffn_acik=False)), 1e-6,
            "FFN ciktiyi degistirmiyor -> olu halka")

    def test_girdi_degisince_cikti_degisir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        rng = m.tohumlu_rng("test-durum-2", 9, 16)
        baska = [[rng.uniform(-1, 1) for _ in range(16)] for _ in range(9)]
        self.assertGreater(self._fark(kod.ileri(durumlar), kod.ileri(baska)), 1e-3)

    def test_temsil_piyasaya_duyarli(self):
        """63-bulgu #0'in panzehiri: temsilin %99'u sabit OLMAMALI."""
        kod = m.Kodlayici(boyut=16, bas_sayisi=2, tohum=2026)
        ciktilar = []
        for k in range(20):
            rng = m.tohumlu_rng("duyarlilik", k)
            durumlar = [[rng.uniform(-1, 1) for _ in range(16)] for _ in range(9)]
            ciktilar.append(kod.ileri(durumlar))
        ortalama = [sum(c[j] for c in ciktilar) / len(ciktilar) for j in range(16)]
        sapma = [math.sqrt(sum((c[j] - ortalama[j]) ** 2 for c in ciktilar) / len(ciktilar))
                 for j in range(16)]
        norm_ort = math.sqrt(sum(x * x for x in ortalama))
        norm_sap = math.sqrt(sum(x * x for x in sapma))
        degisken_pay = norm_sap / math.sqrt(norm_sap ** 2 + norm_ort ** 2)
        self.assertGreater(degisken_pay, 0.10,
                           f"temsil %{degisken_pay*100:.1f} degisken - cok sabit")


class SoftmaxTesti(unittest.TestCase):
    def test_toplam_bir(self):
        self.assertAlmostEqual(sum(m.kararli_softmax([1.0, 2.0, 3.0])), 1.0, places=9)

    def test_sicaklik_tek_softmaxta_sirayi_degistirmez(self):
        for T in (0.1, 1.0, 10.0):
            p = m.kararli_softmax([3.0, 1.0], T)
            self.assertGreater(p[0], p[1])

    def test_buyuk_deger_tasmaz(self):
        p = m.kararli_softmax([1000.0, 999.0])
        self.assertTrue(all(math.isfinite(x) for x in p))


# ---------------------------------------------------------------- Task 11

class SizintiTesti(unittest.TestCase):
    def test_purge_embargo_ortusmeyi_keser(self):
        b = m.kronolojik_bol(list(range(0, 400, 5)), ufuk=16, embargo=4)
        self.assertFalse(m.sizinti_var_mi(b, ufuk=16, giris_penceresi=6),
                         "purge/embargo etiket penceresini kesmeli")

    def test_purge_yoksa_sizinti_tespit_edilir(self):
        b = m.kronolojik_bol(list(range(0, 400, 5)), ufuk=0, embargo=0)
        self.assertTrue(m.sizinti_var_mi(b, ufuk=16, giris_penceresi=6))

    def test_bolme_kronolojik_sirali(self):
        b = m.kronolojik_bol(list(range(0, 400, 5)), ufuk=16, embargo=4)
        self.assertLess(max(b["train"]), min(b["kalibrasyon"]))
        self.assertLess(max(b["kalibrasyon"]), min(b["test"]))

    def test_atilan_ornek_sayilir(self):
        indeksler = list(range(0, 400, 5))
        b = m.kronolojik_bol(indeksler, ufuk=16, embargo=4)
        toplam = len(b["train"]) + len(b["kalibrasyon"]) + len(b["test"])
        self.assertEqual(toplam + b["atilan"], len(indeksler))
        self.assertGreater(b["atilan"], 0)

    # -- gereken ornek butcesi TURETILIR, "ulasilamaz" denip birakilmaz --

    def test_gereken_butce_kapali_formulden_gelir(self):
        """azami >= hedef / (kal_orani - bosluk/acikllik).

        Turetim: adim = acikllik/azami; sinir basina purge kaybi =
        bosluk/adim = bosluk*azami/acikllik; kal dilimi = kal_orani*azami.
        """
        bosluk, hedef, kal_orani = 1046, 40, 0.2
        gereken = m.gereken_ornek_butcesi(11980, bosluk, kal_orani, hedef)
        self.assertEqual(gereken,
                         math.ceil(hedef / (kal_orani - bosluk / 11980.0)))

    def test_gereken_butce_ampirik_olarak_YETER(self):
        """Turetilen butce GERCEKTEN kal >= hedef veriyor mu (formul sinandi)."""
        erisim = m.girdi_erisimi(m.GECIKME_SAYISI, h4_var=True)
        bosluk = m.ETIKET_UFKU + m.EMBARGO + erisim
        hedef = 2 * m.ASGARI_OLCUM
        for bar in (12000, 30000):
            acikllik = bar - m.ISINMA_BARI - m.ETIKET_UFKU - 1
            azami = m.gereken_ornek_butcesi(acikllik, bosluk,
                                            m.BOLME_ORANLARI[1], hedef)
            idx = m._ornek_indeksleri(m.ISINMA_BARI, bar - m.ETIKET_UFKU - 1, azami)
            b = m.kronolojik_bol(idx, m.ETIKET_UFKU, m.EMBARGO,
                                 giris_erisimi=erisim)
            self.assertGreaterEqual(len(b["kalibrasyon"]), hedef,
                                    f"{bar} barda turetilen butce yetmedi")

    def test_gereken_butce_SIKI_bir_alt_sinir(self):
        """Formul gevsek olamaz: belirgin olcude altinda kal hedefe DUSMELI."""
        erisim = m.girdi_erisimi(m.GECIKME_SAYISI, h4_var=True)
        bosluk = m.ETIKET_UFKU + m.EMBARGO + erisim
        hedef = 2 * m.ASGARI_OLCUM
        bar = 30000
        acikllik = bar - m.ISINMA_BARI - m.ETIKET_UFKU - 1
        azami = m.gereken_ornek_butcesi(acikllik, bosluk,
                                        m.BOLME_ORANLARI[1], hedef)
        idx = m._ornek_indeksleri(m.ISINMA_BARI, bar - m.ETIKET_UFKU - 1,
                                  azami - 20)
        b = m.kronolojik_bol(idx, m.ETIKET_UFKU, m.EMBARGO, giris_erisimi=erisim)
        self.assertLess(len(b["kalibrasyon"]), hedef)

    def test_aciklik_yetmezse_butce_VERI_YOK(self):
        """acikllik <= bosluk/kal_orani ise hicbir butce yetmez."""
        self.assertIsNone(m.gereken_ornek_butcesi(3000, 1046, 0.2, 40))

    def test_cok_az_veride_bos_bolme(self):
        b = m.kronolojik_bol([1, 2, 3], ufuk=16, embargo=4)
        self.assertEqual(b["train"], [])
        self.assertIn("yetersiz", b["not"])

    # -- 4H token erisimi: purge/embargo penceresi 15M gecikmesi DEGILDIR --

    def test_girdi_erisimi_gosterge_penceresinden_turetilir(self):
        """Erisim TOKEN GECIKMESI DEGIL, ozniteligin okudugu bar sayisidir.

        Olculdu: gecikme yalniz 4 bar sayarken _z(atr) uzerinden gercek
        okuma 62 bara uzaniyordu; 4 barlik pencereyle yapilan sizinti
        denetimi fail-open bir rapordur.
        """
        W = m.oznitelik_penceresi()
        self.assertGreaterEqual(W, m.YUVARLANAN_PENCERE + 14,
                                "_z(atr) zinciri: 48 pencere USTUNE ATR periyodu")
        self.assertEqual(m.girdi_erisimi(4, h4_var=False),
                         (4 - 1) + W)
        self.assertEqual(m.girdi_erisimi(4, h4_var=True),
                         (4 - 1) + (2 * m.H4_BAR_ORANI - 1) + m.H4_BAR_ORANI * W)

    def test_girdi_erisimi_gercek_okumayi_KAPSAR(self):
        """Beyan edilen erisim, perturbasyonla OLCULEN erisimden kucuk olamaz.

        Fail-closed yon: beyan >= gercek. Bu test formulu gercege karsi
        sinar; formul kucuk kalirsa sizinti raporu yalan olur.
        """
        rng = m.tohumlu_rng("erisim-kapsam")
        n, hedef = 400, 350
        barlar, f = [], 100.0
        for _ in range(n):
            f *= 1.0 + rng.uniform(-0.004, 0.004)
            barlar.append({"o": f, "h": f * 1.003, "l": f * 0.997, "c": f,
                           "v": rng.uniform(80.0, 120.0)})

        def satir(bs):
            return m.satir_uret(bs, m._gostergeler(bs), None, hedef)

        taban = satir(barlar)
        en_uzak = 0
        for d in range(1, hedef + 1):
            bozuk = [dict(b) for b in barlar]
            for anahtar in ("o", "h", "l", "c"):
                bozuk[hedef - d][anahtar] *= 1.001
            if satir(bozuk) != taban:
                en_uzak = d
        self.assertLessEqual(en_uzak, m.girdi_erisimi(1, h4_var=False),
                             f"olculen erisim {en_uzak} beyani asti")
        self.assertGreater(en_uzak, m.YUVARLANAN_PENCERE,
                           "olcum kurulumu bozuk: erisim pencereden kucuk cikti")

    def test_sizinti_denetimi_4h_erisimini_hesaba_katar(self):
        """Ayni bolme: 15M penceresiyle 'temiz', gercek erisimle SIZINTILI.

        Fail-open rapor yasagi: olculmeyen sey 'yok' diye raporlanamaz.
        """
        e15 = m.girdi_erisimi(4, h4_var=False)      # olculdu: 65
        e4h = m.girdi_erisimi(4, h4_var=True)       # olculdu: 1026
        bolme = {"train": list(range(0, 4000, 40)),
                 "kalibrasyon": list(range(4200, 5400, 40)),
                 "test": list(range(5600, 6600, 40))}
        self.assertFalse(m.sizinti_var_mi(bolme, 16, e15),
                         "15M penceresiyle bu bolme temiz gorunur")
        self.assertTrue(m.sizinti_var_mi(bolme, 16, e4h),
                        "4H erisimiyle AYNI bolme sizintilidir")

    def test_bolme_giris_erisimi_kadar_purge_eder(self):
        erisim = m.girdi_erisimi(4, h4_var=True)
        indeksler = list(range(0, 30000, 60))
        b = m.kronolojik_bol(indeksler, ufuk=16, embargo=4, giris_erisimi=erisim)
        self.assertTrue(b["train"] and b["kalibrasyon"] and b["test"],
                        "yeterli veride erisim eklenince bolme dejenere OLMAMALI")
        self.assertGreaterEqual(b["kalibrasyon"][0] - b["train"][-1], 16 + 4 + erisim)
        self.assertFalse(m.sizinti_var_mi(b, 16, erisim))

    def test_veri_yetmezse_bolme_fail_closed_bos_doner(self):
        """Durust erisim, az veride bolmeyi DEJENERE eder - ve etmelidir.

        700 barlik bir pencere 4H tokenleriyle egitilemez. Dogru cevap
        kucuk bir pencereye SIGDIRMAK degil, "yetersiz" demektir.
        """
        b = m.kronolojik_bol(list(range(0, 700, 7)), ufuk=16, embargo=4,
                             giris_erisimi=m.girdi_erisimi(4, h4_var=True))
        self.assertEqual(b["train"], [])
        self.assertIn("yetersiz", b["not"])

    def test_dejenere_kapisi_ornek_biriminde_olculur(self):
        """Kapi bar-boslugunu ornek sayisiyla kiyaslarsa alt-orneklemde yanilir.

        Bosluk BAR cinsindendir; ornekler alt-orneklenmis olabilir. 30000
        barda 500 ornek (adim 60) icin 1046 barlik bosluk ~17 ornege mal
        olur, 1046'ya DEGIL.
        """
        b = m.kronolojik_bol(list(range(0, 30000, 60)), ufuk=16, embargo=4,
                             giris_erisimi=m.girdi_erisimi(4, True))
        self.assertEqual(b["not"], "")


class BaslikTesti(unittest.TestCase):
    def _ogrenilebilir(self, n=200):
        rng = m.tohumlu_rng("baslik-test")
        ornekler = []
        for _ in range(n):
            x = [rng.uniform(-1, 1) for _ in range(16)]
            ornekler.append({"x": x, "y": 1 if sum(x[:4]) > 0 else 0})
        return ornekler

    def test_egitim_kaybi_duser(self):
        ornekler = self._ogrenilebilir()
        b = m.Baslik(boyut=16, tohum=7)
        once = b.kayip(ornekler)
        b.egit(ornekler, devir=60, ogrenme_hizi=0.15)
        self.assertLess(b.kayip(ornekler), once, "egitim kaybi dusmeli")

    def test_logit_iki_sinif(self):
        self.assertEqual(len(m.Baslik(boyut=16, tohum=7).logit([0.0] * 16)), 2)

    def test_egitilmemis_baslik_neredeyse_esit_olasilik(self):
        p = m.kararli_softmax(m.Baslik(boyut=16, tohum=7).logit([0.0] * 16))
        self.assertAlmostEqual(p[0], 0.5, places=1)


# ---------------------------------------------------------------- Task 12

class KalibrasyonFitTesti(unittest.TestCase):
    def _basliklar_ve_ornekler(self):
        rng = m.tohumlu_rng("kal-fit")
        basliklar = [m.Baslik(boyut=8, tohum=100 + k) for k in range(3)]
        ornekler = []
        for _ in range(300):
            x = [rng.uniform(-1, 1) for _ in range(8)]
            ornekler.append({"x": x, "y": 1 if sum(x[:3]) > 0 else 0})
        for b in basliklar:
            b.egit(ornekler[:200], devir=40, ogrenme_hizi=0.2)
        return basliklar, ornekler[200:]

    def test_sicaklik_fit_dagitilan_dagilimda_yapilir(self):
        """63-bulgu #28'in panzehiri: T, DAGITILAN dagilimda fit edilmeli."""
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.sicaklik_fit(kal, basliklar)

        def nll(T):
            toplam = 0.0
            for o in kal:
                p = m.topluluk_olasilik(o["x"], basliklar, T)["p"]
                toplam += -math.log(max(1e-12, p[o["y"]]))
            return toplam / len(kal)

        self.assertLessEqual(r["nll"], nll(1.0) + 1e-9)
        self.assertLessEqual(r["nll"], nll(5.0) + 1e-9)
        self.assertAlmostEqual(r["nll"], nll(r["T"]), places=9)

    def test_sicaklik_sinirda_bayragi(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.sicaklik_fit(kal, basliklar)
        self.assertIn("sinirda", r)
        self.assertIsInstance(r["sinirda"], bool)

    def test_topluluk_uzlasi_ve_dagilim(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.topluluk_olasilik(kal[0]["x"], basliklar, 1.0)
        self.assertAlmostEqual(sum(r["p"]), 1.0, places=9)
        self.assertGreaterEqual(r["uzlasi"], 1.0 / 3.0)
        self.assertLessEqual(r["uzlasi"], 1.0)
        self.assertGreaterEqual(r["dagilim"], 0.0)

    def test_izotonik_monoton(self):
        ciftler = [(0.1, 0), (0.2, 0), (0.3, 1), (0.4, 0), (0.5, 1),
                   (0.6, 1), (0.7, 1), (0.8, 1), (0.9, 1)]
        fn = m.izotonik_fit(ciftler)
        degerler = [fn(x / 10.0) for x in range(1, 10)]
        for i in range(1, len(degerler)):
            self.assertGreaterEqual(degerler[i] + 1e-9, degerler[i - 1])

    def test_kalibrasyon_sec_nll_dusuk_olani_secer(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.kalibrasyon_sec(kal, basliklar)
        self.assertIn(r["yontem"], ("sicaklik", "izotonik"))
        self.assertTrue(math.isfinite(r["nll"]))

    # -- yarisma adaleti: ayni kumede fit + puanlama izotoniki KAYIRIR --

    def _sinyalsiz(self, tohum, n=120, boyut=4):
        """Etiketi x'ten BAGIMSIZ kume: hicbir yontem gercek kenar bulamaz."""
        rng = m.tohumlu_rng(tohum)
        basliklar = [m.Baslik(boyut=boyut, tohum=100 + k) for k in range(3)]
        ornekler = [{"x": [rng.uniform(-1, 1) for _ in range(boyut)],
                     "y": 1 if rng.random() < 0.5 else 0} for _ in range(n)]
        return basliklar, ornekler

    @staticmethod
    def _nll(ciftler):
        toplam = 0.0
        for p, y in ciftler:
            p = min(1.0 - 1e-9, max(1e-9, p))
            toplam += -math.log(p if y == 1 else 1.0 - p)
        return toplam / len(ciftler)

    def _ham(self, ornekler, basliklar, T=1.0):
        return [(m.long_olasiligi(m.topluluk_olasilik(o["x"], basliklar, T)["p"]),
                 o["y"]) for o in ornekler]

    def test_ezberleyen_izotonik_secilmez(self):
        """Ic-orneklemde izotonik KAZANIR, dis-orneklemde KAYBEDER.

        Izotonik n serbestlik derecesine kadar cikar; sicaklik tek
        parametredir. Ayni kumede fit edilip ayni kumede puanlanan bir
        yarisma bu yuzden yapisal olarak izotoniki secer - kenar degil
        EZBER olculur. Adil yarisma sicakligi secmeli.
        """
        basliklar, ornekler = self._sinyalsiz("kal-b")
        kal, dis = ornekler[:60], ornekler[60:]
        izo = m.izotonik_fit(self._ham(kal, basliklar))
        sic = m.sicaklik_fit(kal, basliklar)

        ic_izo = self._nll([(izo(p), y) for p, y in self._ham(kal, basliklar)])
        ic_sic = self._nll(self._ham(kal, basliklar, sic["T"]))
        dis_izo = self._nll([(izo(p), y) for p, y in self._ham(dis, basliklar)])
        dis_sic = self._nll(self._ham(dis, basliklar, sic["T"]))
        # Kurulumun gecerliligi: tuzak GERCEKTEN kurulu olmali.
        self.assertLess(ic_izo, ic_sic, "kurulum bozuk: izotonik ic-orneklemde kaybediyor")
        self.assertGreater(dis_izo, dis_sic, "kurulum bozuk: izotonik dis-orneklemde kazaniyor")

        self.assertEqual(m.kalibrasyon_sec(kal, basliklar)["yontem"], "sicaklik")

    def test_yarisma_ic_holdoutta_yapilir_ve_beyan_edilir(self):
        basliklar, ornekler = self._sinyalsiz("kal-a")
        r = m.kalibrasyon_sec(ornekler[:60], basliklar)
        self.assertEqual(r["yarisma"], "ic-holdout")

    def test_yetersiz_ornekte_yarisma_yapilmaz_fail_closed(self):
        """Bolunemeyecek kadar az ornekte ezber riski en dusuk yontem secilir."""
        basliklar, ornekler = self._sinyalsiz("kal-c")
        r = m.kalibrasyon_sec(ornekler[:2 * m.ASGARI_OLCUM - 1], basliklar)
        self.assertEqual(r["yontem"], "sicaklik")
        self.assertIn("yetersiz", r["yarisma"])

    def test_kazanan_tum_kalibrasyon_kumesinde_yeniden_fit_edilir(self):
        """Yarisma ayirmak icindir; kazanan veriyi ISRAF etmemeli."""
        basliklar, ornekler = self._sinyalsiz("kal-d", n=200)
        kal = ornekler[:120]
        r = m.kalibrasyon_sec(kal, basliklar)
        if r["yontem"] == "sicaklik":
            self.assertAlmostEqual(r["T"], m.sicaklik_fit(kal, basliklar)["T"],
                                   places=9)
        else:
            tam = m.izotonik_fit(self._ham(kal, basliklar))
            for p in (0.1, 0.3, 0.5, 0.7, 0.9):
                self.assertAlmostEqual(r["fn"](p), tam(p), places=9)

    def test_karisim_softmaxinda_sicaklik_karari_cevirebilir(self):
        """63-bulgu #24: olasilik-havuzunda T argmax'i DEGISTIREBILIR.

        Bu bir hata degil, olgudur; sistem bunu BILMELI ve raporlamali.
        """
        self.assertTrue(m.sicaklik_karari_cevirir_mi([[10.0, 0.0], [0.0, 1.0],
                                                      [0.0, 1.0]]))
        self.assertFalse(m.sicaklik_karari_cevirir_mi([[3.0, 0.0], [2.0, 0.0],
                                                       [1.0, 0.0]]))


# ---------------------------------------------------------------- Task 13

class DecodingTesti(unittest.TestCase):
    def test_daima_yon_uretir(self):
        for p in (0.0, 0.4999, 0.5, 0.5001, 1.0):
            self.assertIn(m.decode(p), m.YON_SOZLUGU)

    def test_beraberlikte_long(self):
        self.assertEqual(m.decode(0.5), "LONG")

    def test_hold_asla_donmez(self):
        """Belgenin Gerekce 1-2: decoding secimsiz adim uretemez."""
        rng = m.tohumlu_rng("decode-fuzz")
        for _ in range(500):
            self.assertIn(m.decode(rng.random()), ("LONG", "SHORT"))

    def test_seviyeler_long_yonlu(self):
        s = m.seviyeler(giris=100.0, atr_deger=2.0, yon="LONG", stop_k=1.5, hedef_k=3.0)
        self.assertAlmostEqual(s["stop"], 97.0, places=9)
        self.assertAlmostEqual(s["hedef"], 106.0, places=9)
        self.assertAlmostEqual(s["R"], 2.0, places=9)

    def test_seviyeler_short_simetrik(self):
        s = m.seviyeler(100.0, 2.0, "SHORT", 1.5, 3.0)
        self.assertAlmostEqual(s["stop"], 103.0, places=9)
        self.assertAlmostEqual(s["hedef"], 94.0, places=9)


class SinifEkseniTesti(unittest.TestCase):
    """etiket_uret'in y'si ile decode'un okudugu olasilik AYNI ekseni gostermeli.

    Bu sinif bir SEMANTIK bagi sinar: modul ici tutarlilik testleri (softmax
    toplami 1, decode daima yon uretir) eksen ters olsa bile GECER. Bag ancak
    ogrenilebilir bir sinyalle olculur: etiket kuralini bilen bir baslik
    egitilir, sonra decode'un ayni yonu soyleyip soylemedigine BAKILIR.
    """

    def _ogrenilebilir(self, n=400, boyut=4, tohum="eksen-test"):
        rng = m.tohumlu_rng(tohum)
        kume = []
        for _ in range(n):
            x = [rng.uniform(-1, 1) for _ in range(boyut)]
            # etiket_uret sozlesmesi: 1 = "LONG hedefi once vuruldu" = LONG DOGRU
            kume.append({"x": x, "y": 1 if x[0] > 0 else 0})
        return kume

    def setUp(self):
        self.kume = self._ogrenilebilir()
        self.b = m.Baslik(boyut=4, tohum=42)
        self.b.egit(self.kume, devir=120, ogrenme_hizi=0.20)

    def _p_long(self, x):
        return m.long_olasiligi(m.topluluk_olasilik(x, [self.b])["p"])

    def test_long_dogru_ornekte_decode_LONG_der(self):
        self.assertEqual(m.decode(self._p_long([0.9, 0.0, 0.0, 0.0])), "LONG")

    def test_long_yanlis_ornekte_decode_SHORT_der(self):
        self.assertEqual(m.decode(self._p_long([-0.9, 0.0, 0.0, 0.0])), "SHORT")

    def test_ogrenilebilir_sinyalde_dogruluk_sanstan_yuksek(self):
        """Eksen tersse bu deger 0.5'in COK ALTINA duser (1 - dogruluk)."""
        dogru = sum(1 for o in self.kume
                    if (1 if self._p_long(o["x"]) >= 0.5 else 0) == o["y"])
        self.assertGreater(dogru / len(self.kume), 0.9)

    def test_ters_eksenin_bedeli_ARTEFAKTA_KILITLI(self):
        """Eksen ters cevrilince dogruluk ne oluyor - sayi burada URETILIYOR.

        Bu testin varlik sebebi: c9ba8cd commit mesajinda depo
        artefaktindan yeniden URETILEMEYEN bir vektor yazilmisti
        (denetci #6 yakaladi, sicilde G-1). Kaynagi olmayan nicel iddia
        gercek gibi sunulamaz. Bundan sonra bu sayilar burada olculuyor;
        deger degisirse test duser.
        """
        dogru_eksen = sum(1 for o in self.kume
                          if (1 if self._p_long(o["x"]) >= 0.5 else 0) == o["y"])
        ters_eksen = len(self.kume) - dogru_eksen
        self.assertEqual(dogru_eksen + ters_eksen, len(self.kume))
        self.assertGreater(dogru_eksen / len(self.kume), 0.9)
        self.assertLess(ters_eksen / len(self.kume), 0.1)
        # Ters eksen TAM olarak tamamlayicidir: 1 - dogruluk.
        p = self._p_long([0.9, 0.0, 0.0, 0.0])
        self.assertAlmostEqual(p + (1.0 - p), 1.0, places=12)
        self.assertEqual(m.decode(p), "LONG")
        self.assertEqual(m.decode(1.0 - p), "SHORT")

    def test_eksen_tek_yerde_beyan_edilir(self):
        """Ham indeks (p[0]/p[1]) ile yon okumak yasak: eksen kayabilir."""
        self.assertTrue(hasattr(m, "LONG_SINIFI"))
        self.assertEqual(m.long_olasiligi([0.3, 0.7]), [0.3, 0.7][m.LONG_SINIFI])

    def test_kaynakta_ham_indeksle_yon_okunmuyor(self):
        """Modulde `["p"][0]` kalmamali - eksen kacisi buradan sizar."""
        kaynak = m._modul_kaynagi()
        self.assertNotIn('["p"][0]', kaynak)
        self.assertNotIn('["p"][1]', kaynak)

    def test_sicaklik_karari_cevirir_mi_ayni_ekseni_kullanir(self):
        """T taramasi da LONG_SINIFI'ndan gecmeli; aksi halde iki eksen olur."""
        logitler = [[0.0, 3.0], [0.0, 3.0], [0.0, 3.0]]   # net LONG (sinif 1)
        for T in (0.2, 1.0, 5.0):
            gorusler = [m.kararli_softmax(z, T) for z in logitler]
            p_long = sum(m.long_olasiligi(g) for g in gorusler) / len(gorusler)
            self.assertEqual(m.decode(p_long), "LONG")
        self.assertFalse(m.sicaklik_karari_cevirir_mi(logitler))


class KararUretTesti(unittest.TestCase):
    def _baglam(self, kanit_yok=True):
        barlar = [{"o": 100 + i * 0.1, "h": 100 + i * 0.1 + 0.5,
                   "l": 100 + i * 0.1 - 0.5, "c": 100 + i * 0.1} for i in range(300)]
        return {
            "sembol": "BTCUSDT", "barlar": barlar, "atr_serisi": [1.0] * 300,
            "indeksler": list(range(0, 250, 5)),
            "p_ham": 0.95 if kanit_yok else 0.72,
            "dogru": 17 if kanit_yok else 700,
            "toplam": 48 if kanit_yok else 1000,
            "ece_enkotu": 0.02, "dolu_kanal": 6, "toplam_kanal": 6,
            "giris": 130.0, "atr": 1.0, "likidasyon": 100.0,
            "kaldirac_azami": 10.0, "komisyon": 0.0004, "kayma": 0.0005,
            "funding": 0.0, "lam": 1.0,
        }

    def test_stake_sifirken_bile_seviyeler_uretilir(self):
        """Belgenin Gerekce 5: seviyeler KOSULSUZ uretilir."""
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertIn(r["yon"], m.YON_SOZLUGU)
        self.assertIsNotNone(r["giris"])
        self.assertIsNotNone(r["stop"])
        self.assertIsNotNone(r["hedef"])
        self.assertEqual(r["stake"]["f"], 0.0)

    def test_kanit_yoksa_stake_sifir(self):
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertEqual(r["stake"]["f"], 0.0)
        self.assertEqual(r["shrinkage"]["s"], 0.0)

    def test_cikti_lambda_uclusu_icerir(self):
        r = m.karar_uret(self._baglam(kanit_yok=True))
        for lam in ("1.0", "0.5", "0.25"):
            self.assertIn(lam, r["stake"]["lambda_tablosu"])

    def test_basabas_p_daima_raporlanir(self):
        self.assertIn("basabas_p", m.karar_uret(self._baglam())["geometri"])

    def test_yon_daraltilmamis_olasiliktan_gelir(self):
        """Shrinkage stake'i sifirlar ama YON bilgisini yok etmez."""
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertEqual(r["yon"], "LONG")   # p_ham=0.95 -> LONG

    def test_likidasyon_okunamazsa_stake_sifir(self):
        b = self._baglam(kanit_yok=False)
        b["likidasyon"] = None
        r = m.karar_uret(b)
        self.assertEqual(r["stake"]["f"], 0.0)
        self.assertEqual(r["stake"]["f_max"], 0.0)


# ---------------------------------------------------------------- Task 14

class GostergeTesti(unittest.TestCase):
    def test_ema_ilk_deger_girdiye_esit(self):
        self.assertAlmostEqual(m.ema([5.0, 6.0, 7.0], 3)[0], 5.0, places=9)

    def test_ema_uzunluk_korunur(self):
        self.assertEqual(len(m.ema([1.0] * 10, 3)), 10)

    def test_atr_pozitif(self):
        barlar = [{"o": 100, "h": 101, "l": 99, "c": 100} for _ in range(20)]
        self.assertTrue(all(x >= 0 for x in m.atr(barlar, 14)))

    def test_rsi_araligi(self):
        rng = m.tohumlu_rng("rsi")
        for x in m.rsi([100 + rng.uniform(-1, 1) for _ in range(60)], 14):
            self.assertGreaterEqual(x, 0.0)
            self.assertLessEqual(x, 100.0)


FIKSTUR_BARI = 6000   # 62.5 gun 15M; durust purge boslugu (1046) altinda
                      # bolmenin dejenere OLMAMASI icin gereken mertebe


def _agrega4h(barlar15):
    """16 adet 15M barini GERCEK bir 4H barina toplar (ornekleme DEGIL).

    Ornekleme (barlar15[::16]) hizalama semantigini sinayamaz cunku 4H
    barinin kapanisi 15M barininkiyle ayni olur. Agregasyon ise 4H barinin
    ANCAK 16. barda kapandigini gorunur kilar.
    """
    cikti = []
    for k in range(0, len(barlar15) - 15, 16):
        dilim = barlar15[k:k + 16]
        cikti.append({"o": dilim[0]["o"],
                      "h": max(b["h"] for b in dilim),
                      "l": min(b["l"] for b in dilim),
                      "c": dilim[-1]["c"],
                      "v": sum(b["v"] for b in dilim)})
    return cikti


class SonluErisimTesti(unittest.TestCase):
    """Gostergelerin geriye erisimi KANITLANABILIR bicimde SONLU olmali.

    Ozyinelemeli (IIR) EMA'nin erisimi SONLU DEGILDIR: cikti[i] cikti[i-1]'e,
    o da cikti[i-2]'ye bagli - zincir serinin BASINA kadar gider ve pratikte
    yalniz float64 alt-tasmasiyla kesilir. Bu, erisimin VERIYE ve TOLERANSA
    bagli olmasi demektir; olcum bunu dogruladi (ayni bar, tol 1e-15 -> 313
    bar, tol 1e-9 -> 168 bar). Toleransa bagli bir sayi purge korkulugu
    OLAMAZ: sizinti penceresi kanitlanabilir bir ust sinir ister.

    Cozum ustel agirligi TERK ETMEK degil, onu SONLU pencereye KESMEKTIR:
    ayni agirlik profili, kanitlanabilir sinir.
    """

    def _seri(self, n=400):
        rng = m.tohumlu_rng("sonlu-erisim")
        return [100.0 + rng.uniform(-1.0, 1.0) for _ in range(n)]

    def _erisim(self, fn, seri, i, tolerans):
        """i'inci ciktiyi degistiren EN UZAK gecmis barin mesafesi."""
        taban = fn(seri)[i]
        en_uzak = 0
        for d in range(1, i + 1):
            bozuk = list(seri)
            bozuk[i - d] *= 1.001
            if abs(fn(bozuk)[i] - taban) > tolerans:
                en_uzak = d
        return en_uzak

    def test_ema_erisimi_toleranstan_bagimsiz(self):
        """IIR'de bu test DUSER: erisim toleransla degisir."""
        seri = self._seri()
        i = 350
        kati = self._erisim(lambda s: m.ema(s, 21), seri, i, 1e-15)
        maddi = self._erisim(lambda s: m.ema(s, 21), seri, i, 1e-9)
        self.assertEqual(kati, maddi,
                         "erisim toleransa bagliysa ust sinir kanitlanamaz")

    def test_docstringteki_erisim_sayilari_ARTEFAKTA_KILITLI(self):
        """Uretim docstring'indeki tablo bu fikstürden URETILIR.

        Sicildeki G-1/H-2 ihlalinin kapagi: kaynagi olmayan nicel iddia
        yasak. Deger degisirse hem test duser hem docstring guncellenir.
        """
        seri, i, periyot = self._seri(), 350, 21
        kesik = [self._erisim(lambda s: m.ema(s, periyot), seri, i, tol)
                 for tol in (1e-15, 1e-12, 1e-9, 1e-6)]
        self.assertEqual(kesik, [41, 41, 41, 41])
        alfa = 2.0 / (periyot + 1.0)
        kuyruk = (1.0 - alfa) ** m.gosterge_penceresi("ema", periyot)
        self.assertAlmostEqual(kuyruk, 0.018260, places=6)

    def test_ema_erisimi_beyan_edilen_pencereyi_asmaz(self):
        seri = self._seri()
        i = 350
        for periyot in (8, 21):
            erisim = self._erisim(lambda s: m.ema(s, periyot), seri, i, 1e-15)
            self.assertLessEqual(erisim, m.gosterge_penceresi("ema", periyot),
                                 f"ema({periyot}) beyan edilen pencereyi asti")

    def test_ema_hala_ustel_agirlikli(self):
        """Kesme, ustel agirligi TERK ETMEK degildir: son bar en agir olmali."""
        n = 200
        for periyot in (8, 21):
            # Tek bir bara birim darbe: agirlik profili dogrudan okunur.
            agirliklar = []
            for d in range(0, 6):
                seri = [0.0] * n
                seri[n - 1 - d] = 1.0
                agirliklar.append(m.ema(seri, periyot)[n - 1])
            for k in range(1, len(agirliklar)):
                self.assertLess(agirliklar[k], agirliklar[k - 1],
                                "agirlik gecmise dogru AZALMALI (ustel profil)")

    def test_gosterge_penceresi_beyan_edilmis(self):
        """Kesme uzunlugu etiketsiz gizli esik OLAMAZ."""
        self.assertIn("EMA_KESME_KATI", m.ESIK_KAYNAGI)
        self.assertEqual(m.ESIK_KAYNAGI["EMA_KESME_KATI"]["kaynak"], "YAPISAL")


class HesapKarmasikligiTesti(unittest.TestCase):
    """satir_uret bar BASINA tum seriyi yeniden kurmamali (gercek O(N^2)).

    Olculdu (cProfile, 20000 bar): `_z([h*k for h,k in zip(...)], i)` listcomp'u
    toplam surenin %71.3'unu yiyordu. Bu bir hiz suslemesi degil: hedef ortam
    Pydroid 3 (telefon) ve durust purge daha buyuk fikstur GEREKTIRIYOR -
    kosmayan sistem dogru sonuc vermez.
    """

    def _barlar(self, n):
        rng = m.tohumlu_rng("karmasiklik")
        barlar, fiyat = [], 100.0
        for _ in range(n):
            fiyat *= 1.0 + rng.uniform(-0.004, 0.004)
            barlar.append({"o": fiyat, "h": fiyat * 1.002, "l": fiyat * 0.998,
                           "c": fiyat, "v": rng.uniform(80.0, 120.0)})
        return barlar

    def test_gostergeler_hacim_degerini_onceden_hesaplar(self):
        gost = m._gostergeler(self._barlar(60))
        self.assertIn("hacim_deger", gost)
        self.assertEqual(len(gost["hacim_deger"]), 60)

    def test_hacim_deger_serisi_eski_ic_formulle_ayni(self):
        """Hoist DAVRANIS DEGISTIRMEMELI: seri birebir ayni olmali."""
        barlar = self._barlar(80)
        gost = m._gostergeler(barlar)
        beklenen = [h * k for h, k in zip(gost["hacimler"], gost["kapanislar"])]
        self.assertEqual(gost["hacim_deger"], beklenen)

    def test_satir_uret_kaynakta_seri_boyu_listcomp_kurmuyor(self):
        """Yapisal kilit: fonksiyon govdesinde tum seri uzerinde zip/listcomp yok."""
        kaynak = inspect.getsource(m.satir_uret)
        self.assertNotIn("zip(hacimler", kaynak)
        self.assertNotIn("for h, k in zip", kaynak)

    def test_satir_uret_maliyeti_seri_boyuyla_buyumuyor(self):
        """Bar basina maliyet N'den BAGIMSIZ olmali (yapisal, zamanlama degil).

        Ayni bar indeksinde uretilen satir, serinin GERISINE eklenen barlardan
        etkilenmemeli; etkileniyorsa fonksiyon tum seriyi geziyor demektir.
        """
        kisa = self._barlar(200)
        uzun = kisa + self._barlar(2000)
        i = 150
        s1 = m.satir_uret(kisa, m._gostergeler(kisa), None, i)
        s2 = m.satir_uret(uzun, m._gostergeler(uzun), None, i)
        self.assertEqual(s1, s2, "gelecek barlar gecmis satiri degistiremez")


class BoruHattiTesti(unittest.TestCase):
    def _paket(self, turev_var=True, tohum="boru"):
        """Fikstur, boru hattinin GERCEKTEN egitebilecegi kadar veri icermeli.

        FIKSTUR_BARI 700 idi. Erisim durustce gosterge pencerelerinden
        turetilince (15M 65, 4H 1026 bar) 700 barlik pencerede purge
        boslugu 1046'ya cikiyor ve bolme TAMAMEN dejenere oluyor - egitim
        de kalibrasyon da degerlendirme de hic kosmuyor. O halde 700 barlik
        fikstur uzerinde "boru hatti gecti" demek TIYATRODUR: testler
        bosluga karsi gecer.

        Cozum esigi gevsetmek DEGIL, fiksturu gercekci kilmaktir: 6000 bar
        = 62.5 gun 15M verisi, gercek sistemin de bekledigi mertebe.
        Uretim maliyeti onbellege alinir; aksi halde her cagride yeniden
        kurulur (suite ~20 kez cagiriyor).
        """
        anahtar = (turev_var, tohum)
        onbellek = getattr(BoruHattiTesti, "_ONBELLEK", None)
        if onbellek is None:
            onbellek = BoruHattiTesti._ONBELLEK = {}
        if anahtar in onbellek:
            return dict(onbellek[anahtar])

        rng = m.tohumlu_rng(tohum)
        barlar15, fiyat = [], 100.0
        for _ in range(FIKSTUR_BARI):
            fiyat *= (1.0 + rng.uniform(-0.003, 0.0032))
            barlar15.append({"o": fiyat, "h": fiyat * 1.002, "l": fiyat * 0.998,
                             "c": fiyat, "v": 1000 + rng.uniform(0, 100)})
        # Turev SERI olmalidir: tek anlik deger tum barlara yazilirsa std=0
        # olur ve Olcekleyici onu dogru bicimde sifirlar (bilgi kaybolur).
        turev_serisi = None
        if turev_var:
            turev_serisi = []
            for i in range(len(barlar15)):
                turev_serisi.append({
                    "oi_degisim": 0.01 + 0.02 * math.sin(i / 7.0),
                    "funding_z": 0.2 + 0.5 * math.sin(i / 11.0),
                    "taker_dengesi": 0.1 + 0.3 * math.cos(i / 5.0),
                    "derinlik_dengesi": -0.05 + 0.2 * math.sin(i / 13.0)})
        paket = {"sembol": "BTCUSDT", "barlar15": barlar15,
                 "barlar4h": _agrega4h(barlar15), "turev_serisi": turev_serisi,
                 "dolu_kanal": 6 if turev_var else 3, "toplam_kanal": 6,
                 "likidasyon": barlar15[-1]["c"] * 0.8, "kaldirac_azami": 10.0,
                 "azami_ornek": m.AZAMI_ORNEK}
        onbellek[anahtar] = paket
        return dict(paket)

    def test_egitilmemis_modelden_yon_BEYAN_EDILMEZ(self):
        """Bolme dejenere ise baslik hic egitilmemistir - p rastgele baslangictir.

        Bunu "yon" diye sunmak UYDURMADIR. Sozluk kurali (V = {LONG, SHORT},
        HOLD YOK) DECODER'in sinif kumesi hakkindadir; burada decoder
        egitilmis bir model uzerinde hic KOSMAMISTIR. Dogru cevap ucuncu
        bir sinif degil, "VERI YOK"tur (fail-closed).
        """
        kucuk = self._paket()
        kucuk["barlar15"] = kucuk["barlar15"][:400]
        kucuk["barlar4h"] = _agrega4h(kucuk["barlar15"])
        if kucuk["turev_serisi"] is not None:
            kucuk["turev_serisi"] = kucuk["turev_serisi"][:400]
        r = m.BoruHatti(tohum=2026).calistir(kucuk)

        self.assertTrue(r["iz"]["halka_11"]["not"], "kurulum bozuk: bolme dejenere degil")
        self.assertFalse(r["iz"]["halka_9"]["egitildi"])
        self.assertEqual(r["yon"], "VERI YOK")
        self.assertIsNone(r["iz"]["halka_9"]["p_long"])
        self.assertEqual(r["stake"]["f"], 0.0)
        self.assertIsNone(r["giris"])
        self.assertIsNone(r["stop"])
        self.assertIsNone(r["hedef"])

    def test_egitilmis_modelde_yon_yine_kosulsuz_uretilir(self):
        """Fail-closed dal, normal yolda yon uretimini KISITLAMAMALI."""
        r = m.BoruHatti(tohum=2026).calistir(self._paket())
        self.assertTrue(r["iz"]["halka_9"]["egitildi"])
        self.assertIn(r["yon"], m.YON_SOZLUGU)
        self.assertIsNotNone(r["giris"])

    def test_hicbir_fonksiyon_satir_sinirini_asmaz(self):
        """Plan Global Constraint: tek fonksiyon 60 satiri asmaz."""
        agac = ast.parse(pathlib.Path(m.__file__).read_text(encoding="utf-8"))
        uzun = []
        for dugum in ast.walk(agac):
            if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef)):
                n = (dugum.end_lineno or dugum.lineno) - dugum.lineno + 1
                if n > 60:
                    uzun.append((dugum.name, n))
        self.assertEqual(uzun, [], f"60 satiri asan fonksiyon(lar): {uzun}")

    def test_iz_giris_erisimini_DOGRUDAN_beyan_eder(self):
        """G-4: bu alan dolayli kilitliydi; dogrudan iddia ucuz ve gerekli."""
        iz = m.BoruHatti(tohum=2026).calistir(self._paket())["iz"]
        self.assertEqual(iz["halka_11"]["giris_erisimi"],
                         m.girdi_erisimi(m.GECIKME_SAYISI, h4_var=True))
        self.assertGreater(iz["halka_11"]["giris_erisimi"],
                           m.GECIKME_SAYISI * m.H4_BAR_ORANI,
                           "erisim token gecikmesinden BUYUK olmali")

    def test_iz_yarisma_hukmu_GERCEKLE_UYUSMALI(self):
        """Kosulsuz kilit: beyan edilen hukum, kalibrasyon boyutuyla TUTMALI.

        Onceki hali kosulluydu ("YAPILMADI ise sunlari kontrol et") ve
        yarismayi yalanla "ic-holdout" gosteren bir mutasyondan GECIYORDU.
        Hukum artik ize degil OLCULEN n'e karsi sinaniyor.
        """
        iz = m.BoruHatti(tohum=2026).calistir(self._paket())["iz"]
        yarisma = iz["halka_7"]["yarisma"]
        kal_n = iz["halka_11"]["kalibrasyon"]
        if kal_n < 2 * m.ASGARI_OLCUM:
            self.assertTrue(yarisma.startswith("YAPILMADI"),
                            f"kal={kal_n} < {2 * m.ASGARI_OLCUM} iken "
                            f"yarisma kosmus gibi beyan edilemez: {yarisma}")
            self.assertIn("yetersiz ornek", yarisma)
            self.assertIn("fail-closed", yarisma)
            self.assertEqual(iz["halka_7"]["yontem"], "sicaklik")
            self.assertIn(str(kal_n), yarisma, "beyan olculen n'i TASIMALI")
        else:
            self.assertEqual(yarisma, "ic-holdout")

    def test_iz_giris_erisimi_gercek_olcumu_KAPSAR(self):
        """Kosulsuz kilit: ize yazilan erisim, perturbasyonla olculeni kapsar."""
        paket = self._paket()
        iz = m.BoruHatti(tohum=2026).calistir(paket)["iz"]
        barlar = paket["barlar15"]
        gost = m._gostergeler(barlar)
        hedef = 300
        taban = m.satir_uret(barlar, gost, None, hedef)
        en_uzak = 0
        for d in range(1, hedef + 1):
            bozuk = [dict(b) for b in barlar]
            for anahtar in ("o", "h", "l", "c"):
                bozuk[hedef - d][anahtar] *= 1.001
            if m.satir_uret(bozuk, m._gostergeler(bozuk), None, hedef) != taban:
                en_uzak = d
        self.assertLessEqual(en_uzak, iz["halka_11"]["giris_erisimi"])
        self.assertGreater(en_uzak, 0, "olcum kurulumu bozuk")

    def test_uctan_uca_karar_uretir(self):
        r = m.BoruHatti(tohum=2026).calistir(self._paket())
        self.assertIn(r["yon"], m.YON_SOZLUGU)
        self.assertIsNotNone(r["giris"])
        self.assertIn("iz", r)

    def test_iz_on_uc_halka_icerir(self):
        r = m.BoruHatti(tohum=2026).calistir(self._paket())
        for halka in range(13):
            self.assertIn(f"halka_{halka}", r["iz"], f"halka_{halka} izde yok")

    def test_boru_hatti_gercekten_kosuyor(self):
        """Denetci bulgusu TIYATRO: bolme bos kalinca egitim/kalibrasyon/
        degerlendirme HIC calismiyordu ama testler bos gecip PASS veriyordu."""
        iz = m.BoruHatti(tohum=2026).calistir(self._paket())["iz"]
        self.assertGreater(iz["halka_11"]["train"], 0, "bolme dejenere")
        self.assertGreater(iz["halka_6"]["train_ornek"], 0, "baslik egitilmedi")
        self.assertGreater(iz["halka_8"]["test_ornek"], 0, "degerlendirme yok")
        self.assertNotEqual(iz["halka_7"]["yontem"], "YOK", "kalibrasyon secilmedi")

    def test_bos_bolmede_sizinti_fail_closed(self):
        """Bos bolmede 'sizinti: False' demek fail-OPEN rapordur."""
        kucuk = self._paket()
        kucuk["azami_ornek"] = 20          # bilerek dejenere
        iz = m.BoruHatti(tohum=2026).calistir(kucuk)["iz"]
        self.assertIsNone(iz["halka_11"]["sizinti"])
        self.assertIn("yetersiz", iz["halka_11"]["not"])

    def test_4h_ailesi_temsili_degistirir(self):
        """Denetci bulgusu ATLAMA: 4H boru hattina HIC girmiyordu."""
        p1 = self._paket()
        p2 = self._paket()
        p2["barlar4h"] = [{"o": b["o"] * 1.5, "h": b["h"] * 1.6,
                           "l": b["l"] * 1.4, "c": b["c"] * 1.5, "v": b["v"]}
                          for b in p2["barlar4h"]]
        r1 = m.BoruHatti(tohum=2026).calistir(p1)
        r2 = m.BoruHatti(tohum=2026).calistir(p2)
        self.assertNotAlmostEqual(r1["p_ham"], r2["p_ham"], places=6)

    def test_iz_iki_zaman_dilimi_raporlar(self):
        iz = m.BoruHatti(tohum=2026).calistir(self._paket())["iz"]
        self.assertEqual(iz["halka_1"]["zaman_dilimi_sayisi"],
                         len(m.ZAMAN_DILIMLERI))
        self.assertEqual(iz["halka_1"]["token_sayisi"],
                         m.GECIKME_SAYISI * len(m.AILELER) * len(m.ZAMAN_DILIMLERI))

    def test_4h_kanali_dusunce_kapsam_duser(self):
        """Modele ulasmayan veri s_kapsam'i BUYUTMEMELI (fail-closed).

        Denetci bulgusu TIYATRO: bu testin ilk hali dolu_kanal'i ELLE
        dusuruyordu, yani kendi kurdugu seyi olcuyordu ve 4H VARKEN de
        geciyordu. Artik dolu_kanal'a DOKUNULMUYOR - kapsam dususu
        boru hattinin KENDISINDEN gelmeli.
        """
        tam = m.BoruHatti(tohum=2026).calistir(self._paket())
        eksik_p = self._paket()
        eksik_p["barlar4h"] = None          # dolu_kanal DEGISMIYOR
        eksik = m.BoruHatti(tohum=2026).calistir(eksik_p)
        self.assertLess(eksik["shrinkage"]["s_kapsam"],
                        tam["shrinkage"]["s_kapsam"],
                        "4H yokken kapsam DUSMELI - yoksa kapsam yalan soyler")

    def test_4h_hizalama_look_ahead_icermez(self):
        """Denetci bulgusu (olumcul): i//16 HENUZ KAPANMAMIS 4H barini veriyordu.

        4H bar k, 15M barlarini [16k, 16k+15] araliginda kapsar ve ancak
        16k+15'te KAPANIR. 15M bar i, en fazla i'den ONCE kapanmis bir 4H
        barini gorebilir.
        """
        p1 = self._paket()
        i = 320
        p2 = self._paket()
        b4 = [dict(b) for b in p2["barlar4h"]]
        hedef = i // 16
        b4[hedef] = {"o": b4[hedef]["o"] * 3, "h": b4[hedef]["h"] * 3,
                     "l": b4[hedef]["l"] * 3, "c": b4[hedef]["c"] * 3,
                     "v": b4[hedef]["v"]}
        p2["barlar4h"] = b4

        g41 = m._gostergeler(p1["barlar4h"])
        g42 = m._gostergeler(p2["barlar4h"])
        e1 = m._h4_hizala(len(p1["barlar15"]), len(p1["barlar4h"]))
        e2 = m._h4_hizala(len(p2["barlar15"]), len(p2["barlar4h"]))
        satir1 = m.satir_uret(p1["barlar4h"], g41, None, e1[i])
        satir2 = m.satir_uret(p2["barlar4h"], g42, None, e2[i])
        self.assertEqual(satir1["fiyat"], satir2["fiyat"],
                         "15M bar %d, HENUZ KAPANMAMIS 4H barini goruyor "
                         "= look-ahead sizintisi" % i)

    def test_4h_hizalama_son_kapanan_bari_verir(self):
        """Esleme kurali: 15M bar i -> 4H bar (i+1)//16 - 1 (0'a kirpilmis)."""
        eslesme = m._h4_hizala(700, 43)
        # 4H bar k, 15M [16k, 16k+15] araligini kapsar, 16k+15'te KAPANIR.
        self.assertEqual(eslesme[0], 0)    # isinma: henuz kapanmis bar yok, kirpilir
        self.assertEqual(eslesme[14], 0)   # isinma
        self.assertEqual(eslesme[15], 0)   # bar 0 TAM burada kapanir -> gorulebilir
        self.assertEqual(eslesme[16], 0)   # bar 1 basladi ama kapanmadi
        self.assertEqual(eslesme[30], 0)   # bar 1 hala olusuyor
        self.assertEqual(eslesme[31], 1)   # bar 1 TAM burada kapandi
        self.assertEqual(eslesme[32], 1)   # bar 2 olusuyor
        self.assertEqual(eslesme[320], 19)  # bar 20 HENUZ kapanmadi (335'te kapanir)

    def test_4h_yokken_token_uretilmez(self):
        """Notr 0.0 enjeksiyonu YASAK: 4H yoksa token HIC uretilmemeli."""
        eksik_p = self._paket()
        eksik_p["barlar4h"] = None
        iz = m.BoruHatti(tohum=2026).calistir(eksik_p)["iz"]
        self.assertFalse(iz["halka_1"]["h4_var"])
        self.assertEqual(iz["halka_1"]["token_sayisi"],
                         m.GECIKME_SAYISI * len(m.AILELER))

    def test_determinizm(self):
        p = self._paket()
        a = m.BoruHatti(tohum=2026).calistir(p)
        b = m.BoruHatti(tohum=2026).calistir(p)
        self.assertEqual(a["yon"], b["yon"])
        self.assertAlmostEqual(a["stake"]["f"], b["stake"]["f"], places=12)

    def test_kanal_dususu_stake_dusurur(self):
        tam = m.BoruHatti(tohum=2026).calistir(self._paket(turev_var=True))
        eksik = m.BoruHatti(tohum=2026).calistir(self._paket(turev_var=False))
        self.assertLessEqual(eksik["stake"]["f"], tam["stake"]["f"])
        self.assertLess(eksik["shrinkage"]["s_kapsam"], tam["shrinkage"]["s_kapsam"])

    def test_turev_ailesi_temsili_degistirir(self):
        """63-bulgu #1'in panzehiri: turev GERCEKTEN modele giriyor mu."""
        p1 = self._paket(turev_var=True)
        p2 = self._paket(turev_var=True)
        p2["turev_serisi"] = [
            {"oi_degisim": -0.9 + 0.05 * math.cos(i / 3.0),
             "funding_z": -2.0 + 0.4 * math.sin(i / 9.0),
             "taker_dengesi": -0.8 + 0.3 * math.sin(i / 4.0),
             "derinlik_dengesi": 0.7 + 0.2 * math.cos(i / 6.0)}
            for i in range(len(p2["barlar15"]))]
        r1 = m.BoruHatti(tohum=2026).calistir(p1)
        r2 = m.BoruHatti(tohum=2026).calistir(p2)
        self.assertNotAlmostEqual(r1["p_ham"], r2["p_ham"], places=6)


# ---------------------------------------------------------------- Task 15

class CiktiTesti(unittest.TestCase):
    def _karar(self):
        return {
            "sembol": "BTCUSDT", "yon": "LONG", "p_ham": 0.55,
            "p_kullanilan": 0.5,
            "shrinkage": {"s": 0.0, "s_kanit": 0.0, "s_kalibrasyon": 1.0,
                          "s_kapsam": 1.0},
            "geometri": {"stop_k": 1.5, "hedef_k": 3.0, "R": 2.0, "p_hedef": 0.4,
                         "n": 40, "basabas_p": 0.68, "elog": -0.01, "not": ""},
            "giris": 100.0, "stop": 98.5, "hedef": 103.0, "R": 2.0,
            "stake": {"f": 0.0, "kirpildi": False, "f_max": 0.1,
                      "lambda_tablosu": {"1.0": {"f": 0.0}, "0.5": {"f": 0.0},
                                         "0.25": {"f": 0.0}}},
        }

    def test_defter_maliyeti_dusuyor_mu(self):
        """Kelly kayip kanadini f*a fiyatlar; defter de ayni maliyeti dusmeli.

        Aksi halde kagit defteri, boyutlandirdigi hedefe gore SISTEMATIK
        iyimser olur - yani sicil, olctugu seyden farkli bir seyi olcer.
        """
        durum = {"sermaye": 1000.0, "pozisyonlar": {}}
        karar = dict(self._karar())
        karar["stake"] = {"f": 0.02, "kirpildi": False, "f_max": 0.1,
                          "lambda_tablosu": {"1.0": {"f": 0.02}}}
        karar["geometri"] = dict(karar["geometri"], cost_r=0.01)
        acilis = m.defter_guncelle(durum, karar, {"o": 100.0, "h": 100.2,
                                                  "l": 99.9, "c": 100.0})
        # Stop'a giden bar: kayip, maliyeti DE icermeli
        kapanis = m.defter_guncelle(acilis, dict(karar, sembol="BTCUSDT"),
                                    {"o": 98.6, "h": 98.7, "l": 98.0, "c": 98.5})
        kayip = durum["sermaye"] - kapanis["sermaye"]
        risk = durum["sermaye"] * 0.02
        self.assertGreater(kayip, risk,
                           "maliyet dusulmemis: kayip tam risk kadar cikti")
        self.assertLess(kayip, risk * 1.5, "maliyet asiri dusulmus")

    def test_metin_rapor_yon_icerir(self):
        self.assertIn("LONG", m.metin_rapor(self._karar()))

    # -- tuketiciler GERCEK boru hatti kararlariyla da sinanmali (H-1) --
    #
    # Bulundu: metin_rapor suite'te YALNIZ elle kurulmus sentetik bir
    # kararla cagriliyordu; dejenere bolmenin urettigi karar (p_ham=None,
    # geometri=None) ona hic verilmemisti ve TypeError ile patliyordu.
    # Kusuru bir denetci yakaladi, bir test degil - kapak burada.

    def _boru_karari(self, bar_sayisi=None):
        paket = BoruHattiTesti("test_determinizm")._paket()
        if bar_sayisi is not None:
            paket["barlar15"] = paket["barlar15"][:bar_sayisi]
            paket["barlar4h"] = _agrega4h(paket["barlar15"])
            if paket["turev_serisi"] is not None:
                paket["turev_serisi"] = paket["turev_serisi"][:bar_sayisi]
        return m.BoruHatti(tohum=2026).calistir(paket)

    def test_metin_rapor_gercek_boru_hatti_kararini_yazar(self):
        metin = m.metin_rapor(self._boru_karari())
        self.assertIn("KARAR-DESTEK", metin)
        self.assertIn("STAKE", metin)

    def test_metin_rapor_dejenere_kararda_PATLAMAZ(self):
        karar = self._boru_karari(400)
        self.assertEqual(karar["yon"], "VERI YOK", "kurulum bozuk: dejenere degil")
        metin = m.metin_rapor(karar)
        self.assertIn("VERI YOK", metin)
        self.assertIn("EGITILMEDI", metin.upper())

    def test_dejenere_karar_normal_karar_ANAHTARLARINI_TASIR(self):
        """Iki dal ayni sozlesmeyi konusmali; aksi halde tuketiciler patlar."""
        normal = self._boru_karari()
        dejenere = self._boru_karari(400)
        eksik = set(normal) - set(dejenere)
        self.assertEqual(eksik, set(), f"dejenere dalda eksik anahtar: {eksik}")
        for alt in ("stake", "shrinkage"):
            eksik_alt = set(normal[alt]) - set(dejenere[alt])
            self.assertEqual(eksik_alt, set(),
                             f"dejenere {alt} eksik anahtar: {eksik_alt}")

    def test_defter_guncelle_dejenere_kararda_PATLAMAZ(self):
        durum = {"sermaye": 1000.0, "pozisyonlar": {}}
        karar = self._boru_karari(400)
        bar = {"o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0}
        yeni = m.defter_guncelle(durum, karar, bar)
        self.assertEqual(yeni["pozisyonlar"], {})
        self.assertEqual(yeni["sermaye"], 1000.0)

    # -- rapor_yaz: plan Task 15'in beyan ettigi cikti (G-6) --

    def _gecici(self, ad="rapor.json"):
        dizin = tempfile.mkdtemp(prefix="llm-trading-test-")
        self.addCleanup(shutil.rmtree, dizin, True)
        return pathlib.Path(dizin) / ad

    def test_rapor_yaz_dosya_uretir_ve_geri_okunur(self):
        yol = self._gecici()
        m.rapor_yaz([self._karar()], yol)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertEqual(veri["surum"], m.SURUM)
        self.assertEqual(len(veri["kararlar"]), 1)
        self.assertEqual(veri["kararlar"][0]["sembol"], "BTCUSDT")
        self.assertEqual(veri["kararlar"][0]["yon"], "LONG")

    def test_rapor_yaz_deterministik(self):
        """Ayni girdi ayni bayt: rapor bir kanit artefaktidir."""
        a, b = self._gecici("a.json"), self._gecici("b.json")
        m.rapor_yaz([self._karar()], a)
        m.rapor_yaz([self._karar()], b)
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_rapor_yaz_karar_destek_uyarisini_TASIR(self):
        """Dosya baglamindan koparilinca da sinir okunabilmeli."""
        yol = self._gecici()
        m.rapor_yaz([self._karar()], yol)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertIn("karar-destek", veri["uyari"].lower())
        self.assertIn("otomatik emir", veri["uyari"].lower())

    def test_rapor_yaz_serilesmeyen_alani_SESSIZCE_ATMAZ(self):
        """Yazilamayan sey 'yazildi' diye raporlanamaz (fail-closed)."""
        karar = self._karar()
        karar["fn"] = lambda x: x
        with self.assertRaises(TypeError):
            m.rapor_yaz([karar], self._gecici())

    def test_rapor_yaz_bos_liste_de_gecerli_dosya_yazar(self):
        yol = self._gecici()
        m.rapor_yaz([], yol)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertEqual(veri["kararlar"], [])

    def test_rapor_yaz_boru_hatti_kararini_yazabilir(self):
        """Gercek karar (iz dahil) seri hale gelmeli - sozlesme kontrolu."""
        paket = BoruHattiTesti("test_determinizm")._paket()
        karar = m.BoruHatti(tohum=2026).calistir(paket)
        yol = self._gecici()
        m.rapor_yaz([karar], yol)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertIn("iz", veri["kararlar"][0])
        self.assertIn("halka_11", veri["kararlar"][0]["iz"])

    def test_rapor_yaz_gizli_alan_SIZDIRMAZ(self):
        """Guvenlik siniri: dosyada anahtar/imza/emir ucu deseni bulunmaz."""
        paket = BoruHattiTesti("test_determinizm")._paket()
        karar = m.BoruHatti(tohum=2026).calistir(paket)
        yol = self._gecici()
        m.rapor_yaz([karar], yol)
        metin = yol.read_text(encoding="utf-8").lower()
        for desen in ("api_key", "apikey", "secret", "hmac", "signature",
                      "/order", "/cancel", "listenkey"):
            self.assertNotIn(desen, metin)

    def test_main_rapor_bayragi_dosya_yazar(self):
        yol = self._gecici("cli.json")
        self.assertEqual(m.main(["--oz-rapor", str(yol)]), 0)
        veri = json.loads(yol.read_text(encoding="utf-8"))
        self.assertEqual(veri["surum"], m.SURUM)
        self.assertIsInstance(veri["kararlar"], list)

    def test_metin_rapor_stake_sifiri_gizlemez(self):
        metin = m.metin_rapor(self._karar())
        self.assertIn("f*", metin)

    def test_metin_rapor_basabas_gosterir(self):
        self.assertIn("basabas", m.metin_rapor(self._karar()).lower())

    def test_defter_stake_sifirda_pozisyon_acmaz(self):
        yeni = m.defter_guncelle({"sermaye": 1000.0, "pozisyonlar": {}},
                                 self._karar(),
                                 {"o": 100, "h": 101, "l": 99, "c": 100})
        self.assertNotIn("BTCUSDT", yeni["pozisyonlar"])

    def test_defter_stake_pozitifken_pozisyon_acar(self):
        karar = self._karar()
        karar["stake"]["f"] = 0.02
        yeni = m.defter_guncelle({"sermaye": 1000.0, "pozisyonlar": {}}, karar,
                                 {"o": 100, "h": 101, "l": 99, "c": 100})
        self.assertIn("BTCUSDT", yeni["pozisyonlar"])

    def test_defter_stopta_kapatir(self):
        durum = {"sermaye": 1000.0, "pozisyonlar": {
            "BTCUSDT": {"yon": "LONG", "giris": 100.0, "stop": 98.5,
                        "hedef": 103.0, "miktar": 10.0}}}
        yeni = m.defter_guncelle(durum, self._karar(),
                                 {"o": 100, "h": 100, "l": 98.0, "c": 99})
        self.assertNotIn("BTCUSDT", yeni["pozisyonlar"])
        self.assertLess(yeni["sermaye"], 1000.0)

    def test_main_esikler_sifir_doner(self):
        """--esikler yan etkisiz; --self-test ozyineleme yaratir, orada sinanmaz."""
        self.assertEqual(m.main(["--esikler"]), 0)

    def test_oz_test_ozyineleme_korumasi(self):
        """Oz-test icinden tekrar cagrilirsa ic ice kosu YAPILMAZ."""
        if m.oz_test_kosuyor():          # --self-test ICINDEN kosuyoruz
            self.assertEqual(m._oz_test(), 0, "ic ice kosu engellenmedi")
        else:                            # dogrudan unittest ile kosuyoruz
            self.assertFalse(m.oz_test_kosuyor())




def main(argv=None):
    import argparse
    ayristirici = argparse.ArgumentParser(description=SURUM)
    ayristirici.add_argument("--self-test", action="store_true",
                             help="gomulu 236 testi kosturur")
    ayristirici.add_argument("--esikler", action="store_true",
                             help="her sabiti kaynak+gerekcesiyle basar")
    ayristirici.add_argument("--oz-rapor", metavar="DOSYA",
                             help="sentetik uctan uca kosu -> JSON (ag YOK)")
    ayristirici.add_argument("--ornek", action="store_true",
                             help="AGSIZ ornek kosu (sahte veri)")
    ayristirici.add_argument("--canli", metavar="SEMBOL",
                             help="GERCEK Binance public GET ile kosar")
    ayristirici.add_argument("--lam", type=float, default=1.0)
    args = ayristirici.parse_args(argv)

    if args.self_test:
        return _oz_test()
    if args.esikler:
        print(esik_raporu())
        return 0
    if args.oz_rapor:
        rapor_yaz(_oz_kosu_kararlari(), args.oz_rapor)
        print("rapor yazildi: " + str(args.oz_rapor))
        return 0
    if args.ornek:
        _kosu_bas("BTCUSDT", _sahte_getir,
                  "ORNEK KOSU - SAHTE VERI (ag YOK). Gercek karar DEGILDIR.")
        return 0
    if args.canli:
        try:
            _kosu_bas(args.canli, None,
                      "CANLI KOSU - " + args.canli + " (public GET)")
        except Exception as hata:                    # ag/veri hatasi
            print("CANLI KOSU BASARISIZ (fail-closed): %s: %s"
                  % (type(hata).__name__, hata))
            print("Uydurma veriyle karar URETILMEZ.")
            return 1
        return 0

    print(SURUM + " - tek dosya. Secenekler:")
    print("  --self-test        236 testi kosturur")
    print("  --esikler          sabit beyani")
    print("  --ornek            AGSIZ ornek kosu")
    print("  --canli BTCUSDT    gercek veriyle kosu")
    print("  --oz-rapor r.json  sentetik kosu -> JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
