#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm_trading_v4.py — GURULTULU KANAL (noisy channel) -> TRADING, tek dosya.

Ek bagimlilik YOKTUR (yalniz Python standart kutuphanesi). Pydroid 3 uyumlu.

  python llm_trading_v4.py --self-test    testleri kosturur
  python llm_trading_v4.py --esikler      her sabiti kaynak+gerekcesiyle basar
  python llm_trading_v4.py --ornek        AGSIZ ornek kosu (sahte veri)
  python llm_trading_v4.py --cumle        ornek bozuk cumleyi onarir (mekanizma gosterimi)
  python llm_trading_v4.py --canli BTCUSDT   GERCEK Binance public GET
  python llm_trading_v4.py --rapor r.json    kosuyu JSON'a yazar

NEDEN v4: v3'te EKSIK OLAN TAM KATMAN, LLM zincirinin BIRINCI halkasiydi —
girdi gurultusunun URETIMDEN ONCE onarilmasi (noisy channel). v3 bozuk/eksik
bir kanali "kapsam dusur" diye isliyordu; onarmiyordu. Bu dosya o katmani
LLM'deki mekanizmanin BIREBIR karsiligi olarak kurar:

  CUMLE                                  PIYASA KANALI
  ------------------------------------   ------------------------------------
  P(c) sozcuk onseli                     kanalin kendi gecmis dagilimi
  P(o|c) yazim-hatasi kanali             bozulma modeli (bes mod, asagida)
  posterior = argmax P(c)*P(o|c)         onarilmis deger = argmax ayni carpim
  baglamla yeniden puanlama              capraz-kanal onsel (fiyat -> turev)
  argmax DAIMA token secer (HOLD YOK)    argmax DAIMA yon secer (HOLD YOK)
  dusuk guven != cikti yok               dusuk onarim guveni -> STAKE duser

BES BOZULMA MODU (ornek cumleden birebir turetildi):
  silme        "imdi"        <- "simdi"       : eksik bar / eksik kayit
  degistirme   "sama"        <- "sana"        : spike / aykiri deger
  uzatma       "pugoreeeewu" <- "gore"        : donmus / tekrarli deger
  ekleme       "eskisis"     <- "eskisi"      : cift kayit
  birlestirme  "geteranladinsen" <- iki kelime: tek anlik degerin cok bara yayilmasi

SERT SOZLESME (mekanik korunur, testlerle kilitli):
  1. HOLD/ABSTAIN/BEKLE sinifi YOKTUR. Yon her kosuda uretilir.
  2. "Notr 0.0 yaz" bir onarim DEGILDIR ve hicbir yerde yapilmaz.
  3. Onarim guveni OLCULUR (geriye-donuk beceri), secilmez. Beceri <= 0 ise
     onarim YAPILMAZ ve kapsam duser (fail-closed).
  4. Onarim guveni YALNIZ stake eksenine baglanir; yonu ASLA susturmaz.
  5. R = hedef_mesafe / stop_mesafe. Baska bir R tanimi yoktur.
  6. Look-ahead: bar i icin her hesap YALNIZ <= i veriyi okur.

GUVENLIK SINIRI: bu dosyada API anahtari, imza, emir/iptal ucu YOKTUR ve
eklenmemelidir. Yalniz public GET okunur. Yalniz karar-destek; canli/otomatik
emir DAHIL DEGILDIR. (GuvenlikTesti motor bolumunu tarar.)
"""

import math
import random
import zlib

SURUM = "llm-trading-v4"
YON_SOZLUGU = ("LONG", "SHORT")     # HOLD YOK - sozluk iki elemanlidir
LONG_SINIFI = 1
EPSILON = 1e-12

# ============================================================ ESIK BEYANI
# Kaynak alani uc degerden biri:
#   OLCULEN  - bu kosunun verisinden istatistikle turetildi
#   YAPISAL  - matematiksel/zaman tanimindan gelir, secim degil
#   VARSAYIM - kalibre EDILMEDI; gerekcesi ve olcum yolu zorunlu
ESIK_KAYNAGI = {}


def esik_kaydet(ad, deger, kaynak, gerekce, olcum_yolu=""):
    ESIK_KAYNAGI[ad] = {"deger": deger, "kaynak": kaynak,
                        "gerekce": gerekce, "olcum_yolu": olcum_yolu}
    return deger


def esik_raporu():
    s = ["SABIT ESIK BEYANI (etiketsiz gizli esik yasak):"]
    for ad in sorted(ESIK_KAYNAGI):
        k = ESIK_KAYNAGI[ad]
        s.append("  %-26s = %-12s [%s]" % (ad, k["deger"], k["kaynak"]))
        s.append("      %s" % k["gerekce"])
        if k["olcum_yolu"]:
            s.append("      OLCUM YOLU: %s" % k["olcum_yolu"])
    return "\n".join(s)


# --- gurultulu kanal sabitleri ---
SPIKE_Z = esik_kaydet(
    "SPIKE_Z", 4.0, "OLCULEN",
    "Robust-z (medyan + 1.4826*MAD) esigi; bunun UZERI 'degistirme' bozulmasi "
    "sayilir. Kullanicinin kendi verisinde olculdu (200 bar x 4 seri): "
    "|z|>3 -> 4..8 olay, |z|>4 -> 1..3 olay, |z|>5 -> 0..1 olay. 4.0, taban "
    "tetiklenme oranini %0.5-1.5 bandinda tutar.",
    "kanal basina |z| dagiliminin ust yuzdeligi; hedef taban oran <= %2")

ONARIM_PENCERESI = esik_kaydet(
    "ONARIM_PENCERESI", 8, "OLCULEN",
    "Onarim kestiricilerinin (naif/medyan/ewma) geriye baktigi bar sayisi. "
    "Kullanicinin OI ve taker serilerinde (n=48) W=8 ile olculen beceri: "
    "OI naif +0.842, taker naif -0.568. W buyudukce ornek azalir, kucukdukce "
    "medyan/MAD kararsizlasir.",
    "W'ye karsi olculen beceri egrisi; platoya girdigi en kucuk W")

ASGARI_BECERI = esik_kaydet(
    "ASGARI_BECERI", 0.0, "YAPISAL",
    "Onarimin YAPILABILMESI icin gereken en dusuk beceri. 0.0 bir SECIM "
    "degil TANIMDIR: beceri = 1 - MAE/MAE_taban oldugundan beceri<=0, "
    "kestiricinin taban-kestiriciden IYI OLMADIGI demektir; boyle bir "
    "onarim bilgi tasimaz, uydurma olur.")

ASGARI_BECERI_ORNEK = esik_kaydet(
    "ASGARI_BECERI_ORNEK", 10, "VARSAYIM",
    "Beceri olcumunun anlamli sayilmasi icin gereken en az kestirim adedi. "
    "Kalibre EDILMEDI. Az ornekte beceri isareti gurultuludur; fail-closed "
    "tarafta kalmak icin onarim yapilmaz.",
    "beceri tahmininin bootstrap std'si hedef bandin altina inince")

DONMUS_ARDISIK = esik_kaydet(
    "DONMUS_ARDISIK", 3, "VARSAYIM",
    "Bir kanalin 'donmus' sayilmasi icin gereken ardisik ozdes deger sayisi. "
    "Kalibre EDILMEDI. Kullanicinin verisinde OI ve taker'da 0 ardisik ozdes "
    "deger var; yani bu esik su an HIC tetiklenmiyor (taban oran = 0).",
    "kanalin ardisik-ozdes uzunluk dagiliminin ust yuzdeligi")

ECE_TAVANI = esik_kaydet(
    "ECE_TAVANI", 0.10, "VARSAYIM",
    "Kalibrasyon guvenilmezlik esigi. Kalibre EDILMEDI. Tek yonlu etki: "
    "buyurse stake buyur. Fail-closed tarafta kucuk secildi.",
    "grup ECE dagiliminin ust yuzdeligi (holdout uzerinde)")

ASGARI_OLCUM = esik_kaydet(
    "ASGARI_OLCUM", 20, "VARSAYIM",
    "Ikili oranin Wilson araliginin ise yarar genislige inmesi icin kaba alt "
    "sinir. Kalibre EDILMEDI. n=20'de %95 aralik genisligi ~0.4.",
    "hedeflenen aralik genisligine gore n cozulmeli")

SABIT_TOLERANSI = esik_kaydet(
    "SABIT_TOLERANSI", 1e-9, "YAPISAL",
    "Bir kolonun 'sabit' sayilmasi icin std tavani. float64 hassasiyetinden "
    "gelir, istatistiksel secim degil.")

ETIKET_UFKU = esik_kaydet(
    "ETIKET_UFKU", 16, "VARSAYIM",
    "Etiketin bakacagi ileri bar sayisi (16 x 15dk = 4 saat). Kalibre "
    "EDILMEDI ve DOGRUDAN p'yi, dolayisiyla stake'i belirler.",
    "ufka karsi holdout AUROC ve ilk-gecis karar-veren oraninin taranmasi")

EMBARGO = esik_kaydet(
    "EMBARGO", 4, "VARSAYIM",
    "Purge uzerine eklenen guvenlik boslugu (bar). Kalibre EDILMEDI.",
    "embargo'ya karsi train-test dagilim farkinin olculmesi")

GECIKME_SAYISI = esik_kaydet(
    "GECIKME_SAYISI", 4, "VARSAYIM",
    "Karar tokeninin gordugu gecmis satir sayisi. Kalibre EDILMEDI. Buyurse "
    "baglam artar ama hesap O(n^2) buyur (Pydroid 3 kisiti).",
    "gecikme sayisina karsi holdout AUROC egrisi - platoya girdigi nokta")

BOLME_ORANLARI = esik_kaydet(
    "BOLME_ORANLARI", (0.6, 0.2, 0.2), "YAPISAL",
    "train / kalibrasyon / test paylari. Tek yerde beyan edilir cunku gosterge "
    "butcesi bu paylardan TURETILIR.")

H4_BAR_ORANI = esik_kaydet(
    "H4_BAR_ORANI", 16, "YAPISAL",
    "Bir 4H bari kac 15M barini kapsar (4*60/15). Zaman dilimi tanimindan.")

LIKIDASYON_GUVENLIK_PAYI = esik_kaydet(
    "LIKIDASYON_GUVENLIK_PAYI", 0.5, "VARSAYIM",
    "Likidasyon mesafesinin ne kadarina kadar stake alinabilecegi. Kalibre "
    "EDILMEDI; likidasyona giden yolun yarisinda durmak = muhafazakar taraf.",
    "gerceklesmis en kotu bar-ici sapmanin dagilimindan ust yuzdelik")

EMA_KESME_KATI = esik_kaydet(
    "EMA_KESME_KATI", 2, "YAPISAL",
    "EMA'nin ustel agirlik profilinin kac PERIYOT sonra kesilecegi. Erisim "
    "aritmetiginden gelir: kesme olmadan EMA'nin geriye erisimi SONLU DEGIL "
    "(yalniz float alt-tasmasi keser) ve toleransa bagli bir sayi purge "
    "korkulugu OLAMAZ. Kesilen kuyruk normalize edilerek dagitilir.")

EN_UZUN_GETIRI_GECIKMESI = esik_kaydet(
    "EN_UZUN_GETIRI_GECIKMESI", 16, "YAPISAL",
    "Log getiri ozniteliklerinin en uzun gecikmesi (1, 4, 16). 16 = bir 4H "
    "barin 15M karsiligi.")


# ============================================================ BOLUM 1
# Determinizm ve temel matematik. Modul duzeyi random.* YASAK.

def sabit_kimlik(*parcalar):
    return zlib.crc32("|".join(str(p) for p in parcalar).encode("utf-8")) & 0xFFFFFFFF


def tohumlu_rng(*parcalar):
    return random.Random(sabit_kimlik(*parcalar))


def kirp(x, alt=-1.0, ust=1.0):
    try:
        d = float(x)
    except (TypeError, ValueError):
        return alt
    if math.isnan(d) or math.isinf(d):
        return alt
    return max(alt, min(ust, d))


def ortalama(xs):
    return sum(xs) / len(xs) if xs else 0.0


def medyan(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def mad_sigma(xs):
    """Medyan mutlak sapmadan robust sigma. Normal dagilimda std'ye esdeger."""
    if len(xs) < 2:
        return 0.0
    m = medyan(xs)
    return 1.4826 * medyan([abs(x - m) for x in xs])


def std(xs):
    if len(xs) < 2:
        return 0.0
    m = ortalama(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def kararli_softmax(logitler, sicaklik=1.0):
    T = max(float(sicaklik), 1e-6)
    o = [float(z) / T for z in logitler]
    mx = max(o) if o else 0.0
    us = [math.exp(max(-60.0, min(60.0, z - mx))) for z in o]
    t = sum(us) or 1.0
    return [u / t for u in us]


def wilson_araligi(basari, deneme, z=1.96):
    if deneme <= 0:
        return 0.0, 1.0
    p = basari / deneme
    payda = 1.0 + z * z / deneme
    merkez = p + z * z / (2.0 * deneme)
    yaricap = z * math.sqrt(p * (1.0 - p) / deneme + z * z / (4.0 * deneme * deneme))
    return (merkez - yaricap) / payda, (merkez + yaricap) / payda


# ============================================================ BOLUM 2
# GURULTULU KANAL — BOZULMA TESPITI (bes mod).
# Her mod, ornek cumledeki bir yazim-hatasi tipinin BIREBIR karsiligidir.
# Tespit YALNIZ <= i veriyi okur (look-ahead yok).

BOZULMA_MODLARI = ("SILME", "DEGISTIRME", "UZATMA", "EKLEME", "BIRLESTIRME")


def bozulma_tespit(kayitlar, beklenen_adim_ms, deger_alani, zaman_alani="timestamp"):
    """Bir zaman damgali kanalda bes bozulma modunu tespit eder.

    kayitlar: [{zaman_alani: int_ms, deger_alani: sayi}, ...]
    Doner: {"kayitlar": temizlenmis, "bulgular": [...], "sayim": {mod: adet}}

    ONEMLI: bu fonksiyon ONARMAZ, yalniz TESPIT eder ve kanali kronolojik
    siraya sokar. Onarim BOLUM 4'te ve YALNIZ olculen beceri izin verirse.
    """
    bulgular = []
    sayim = dict((m, 0) for m in BOZULMA_MODLARI)
    if not kayitlar:
        return {"kayitlar": [], "bulgular": bulgular, "sayim": sayim,
                "not": "kanal BOS - tespit yapilamadi"}

    ayikla = []
    for k in kayitlar:
        try:
            t = int(k[zaman_alani])
            v = float(k[deger_alani])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        ayikla.append((t, v))
    ayikla.sort(key=lambda p: p[0])

    # EKLEME: ayni zaman damgasinda birden fazla kayit ("eskisis" <- "eskisi")
    tekil = []
    gorulen = {}
    for t, v in ayikla:
        if t in gorulen:
            sayim["EKLEME"] += 1
            bulgular.append({"mod": "EKLEME", "zaman": t,
                             "aciklama": "cift kayit; ilk kayit korundu"})
            continue
        gorulen[t] = True
        tekil.append((t, v))

    # SILME: beklenen adimdan buyuk atlama ("imdi" <- "simdi")
    adim = int(beklenen_adim_ms)
    eksik_zamanlar = []
    for i in range(1, len(tekil)):
        fark = tekil[i][0] - tekil[i - 1][0]
        if adim > 0 and fark > adim:
            kayip = fark // adim - 1
            if kayip > 0:
                sayim["SILME"] += kayip
                for k in range(1, kayip + 1):
                    eksik_zamanlar.append(tekil[i - 1][0] + k * adim)
                bulgular.append({"mod": "SILME", "zaman": tekil[i - 1][0],
                                 "aciklama": "%d bar eksik" % kayip})

    degerler = [v for _, v in tekil]

    # UZATMA: ardisik ozdes deger ("eeee" <- "e")
    ardisik = 1
    for i in range(1, len(degerler)):
        if degerler[i] == degerler[i - 1]:
            ardisik += 1
            if ardisik == DONMUS_ARDISIK:
                sayim["UZATMA"] += 1
                bulgular.append({"mod": "UZATMA", "zaman": tekil[i][0],
                                 "aciklama": "%d ardisik ozdes deger (donmus kanal)"
                                             % DONMUS_ARDISIK})
        else:
            ardisik = 1

    # DEGISTIRME: robust-z spike ("sama" <- "sana")
    spike_indeksleri = []
    if len(degerler) >= 5:
        d = []
        for i in range(1, len(degerler)):
            onceki = degerler[i - 1]
            d.append(math.log(degerler[i] / onceki)
                     if onceki > 0 and degerler[i] > 0 else degerler[i] - onceki)
        m = medyan(d)
        s = mad_sigma(d)
        if s > SABIT_TOLERANSI:
            for i, x in enumerate(d):
                if abs((x - m) / s) > SPIKE_Z:
                    sayim["DEGISTIRME"] += 1
                    spike_indeksleri.append(i + 1)
                    bulgular.append({"mod": "DEGISTIRME", "zaman": tekil[i + 1][0],
                                     "aciklama": "robust-z = %.2f > %.1f"
                                                 % ((x - m) / s, SPIKE_Z)})

    return {"kayitlar": tekil, "bulgular": bulgular, "sayim": sayim,
            "eksik_zamanlar": eksik_zamanlar, "spike_indeksleri": spike_indeksleri,
            "not": ""}


def birlestirme_tespit(kayit_sayisi, hedef_bar_sayisi, kanal_adi):
    """BIRLESTIRME ("geteranladinsen"): TEK anlik deger, cok bara yayilmak
    isteniyor. Bu bir bozulmadir ve YAYMA YASAKTIR.

    Gerekce (olculdu): tek deger tum barlara yazilirsa kolonun std'si 0 olur,
    olcekleyici onu DOGRU bicimde sifirlar ve bilgi modele HIC ulasmaz - ama
    kapsam skoru 'dolu' saymaya devam ederdi. Bu fail-open'dir.
    """
    if kayit_sayisi <= 1 and hedef_bar_sayisi > 1:
        return {"mod": "BIRLESTIRME", "kanal": kanal_adi,
                "aciklama": "tek anlik deger %d bara yayilamaz; kanal SERI "
                            "DEGIL - kapsama sayilmaz" % hedef_bar_sayisi,
                "yayilabilir": False}
    return {"mod": None, "kanal": kanal_adi, "yayilabilir": True}


# ============================================================ BOLUM 3
# GURULTULU KANAL — ONARIM BECERISININ OLCULMESI.
# Bu, sistemin en kritik parcasidir: onarim guveni SECILMEZ, OLCULUR.
# Olcum geriye-donuk yurutulur (bar t YALNIZ t'den onceki W bardan kestirilir).

KESTIRICILER = ("naif", "medyan", "ewma")


def _kestir(gecmis, kestirici):
    """gecmis: [v_{t-W} .. v_{t-1}]. Doner: v_t kestirimi. Look-ahead YOK."""
    if not gecmis:
        return None
    if kestirici == "naif":
        return gecmis[-1]
    if kestirici == "medyan":
        return medyan(gecmis)
    if kestirici == "ewma":
        a = 2.0 / (len(gecmis) + 1.0)
        e = gecmis[0]
        for x in gecmis[1:]:
            e = a * x + (1.0 - a) * e
        return e
    raise KeyError("bilinmeyen kestirici: %s" % kestirici)


def onarim_becerisi(degerler, pencere=None):
    """Kanalin kendi gecmisinde OLCULEN onarim becerisi.

    beceri = 1 - MAE(kestirici) / MAE(taban)
    taban  = kumenin medyani (bilgi tasimayan kestirici)

    beceri > 0  -> kestirim taban-kestiriciden IYI -> onarim MESRU
    beceri <= 0 -> kestirim bilgi TASIMIYOR        -> onarim YAPILMAZ

    Bu, ornek cumledeki P(o|c) kanal modelinin OLCULMUS halidir: bir sozcugu
    onarabilmemiz, o dilde onarimin gercekten ise yaradigini gormemize baglidir.
    """
    W = ONARIM_PENCERESI if pencere is None else int(pencere)
    n = len(degerler)
    if n < W + ASGARI_BECERI_ORNEK:
        return {"beceri": 0.0, "kestirici": None, "n": max(0, n - W),
                "mae": None, "taban_mae": None,
                "not": "ornek yetersiz (n=%d, gereken %d) - onarim YAPILMAZ"
                       % (n, W + ASGARI_BECERI_ORNEK)}

    hedefler = degerler[W:]
    taban = medyan(hedefler)
    taban_mae = ortalama([abs(g - taban) for g in hedefler])
    if taban_mae <= SABIT_TOLERANSI:
        return {"beceri": 0.0, "kestirici": None, "n": len(hedefler),
                "mae": 0.0, "taban_mae": taban_mae,
                "not": "seri sabit - onarilacak degisim YOK"}

    en_iyi = None
    tablo = {}
    for k in KESTIRICILER:
        hata = []
        for t in range(W, n):
            tah = _kestir(degerler[t - W:t], k)
            if tah is None:
                continue
            hata.append(abs(tah - degerler[t]))
        if not hata:
            continue
        mae = ortalama(hata)
        beceri = 1.0 - mae / taban_mae
        tablo[k] = {"mae": mae, "beceri": beceri}
        if en_iyi is None or beceri > tablo[en_iyi]["beceri"]:
            en_iyi = k

    if en_iyi is None:
        return {"beceri": 0.0, "kestirici": None, "n": 0, "mae": None,
                "taban_mae": taban_mae, "not": "kestirim uretilemedi"}

    b = tablo[en_iyi]["beceri"]
    return {"beceri": max(0.0, min(1.0, b)),
            "ham_beceri": b,
            "kestirici": en_iyi if b > ASGARI_BECERI else None,
            "n": len(hedefler), "mae": tablo[en_iyi]["mae"],
            "taban_mae": taban_mae, "tablo": tablo,
            "not": "" if b > ASGARI_BECERI else
                   "beceri %.4f <= %.1f - onarim YAPILMAZ (fail-closed)"
                   % (b, ASGARI_BECERI)}


# ============================================================ BOLUM 4
# GURULTULU KANAL — ONARIMIN UYGULANMASI.
#   onarilmis = argmax_c  log P(c) + log P(gozlem|c)
# Adaylar kestiricilerden gelir; onsel kanalin kendi dagilimindan; kanal
# modeli bozulma modunun maliyetinden. Notr 0.0 HICBIR YERDE yazilmaz.

def _log_onsel(aday, gecmis):
    """log P(c): aday, kanalin kendi yakin gecmis dagiliminda ne kadar olasi?"""
    if not gecmis:
        return -1e9
    m = medyan(gecmis)
    s = mad_sigma(gecmis)
    if s <= SABIT_TOLERANSI:
        return 0.0 if abs(aday - m) <= SABIT_TOLERANSI else -1e9
    z = (aday - m) / s
    return -0.5 * z * z


# Bozulma moduna gore -log P(gozlem|aday). Cumle tarafindaki MALIYET
# tablosunun karsiligi; YAPISAL cunku modun kendi tanimindan gelir.
KANAL_MALIYETI = {
    "SILME": esik_kaydet("MALIYET_SILME", 1.0, "YAPISAL",
                         "Eksik kayit: gozlem YOK, dolayisiyla kanal modeli "
                         "sabit bir belirsizlik maliyeti tasir."),
    "DEGISTIRME": esik_kaydet("MALIYET_DEGISTIRME", 1.3, "YAPISAL",
                              "Spike: gozlem VAR ama aykiri. Silmeden pahali, "
                              "cunku gozlemi tamamen atmak bilgi kaybidir."),
    "UZATMA": esik_kaydet("MALIYET_UZATMA", 0.25, "YAPISAL",
                          "Donmus deger: gozlem var ve tekrarli; en ucuz "
                          "onarim, cunku tekrarin kendisi bilgidir."),
}


def deger_onar(gozlem, gecmis, mod, beceri_kaydi):
    """Tek bir bozuk gozlemi onarir. HOLD YOK: daima bir deger doner.

    Doner: {"deger", "guven", "kaynak", "not"}
      kaynak = "HAM" (onarim gerekmedi/yapilamadi) | kestirici adi
      guven  = OLCULEN beceri (onarim yapildiysa) | 1.0 (ham gecerliyse)
    """
    kestirici = (beceri_kaydi or {}).get("kestirici")
    beceri = float((beceri_kaydi or {}).get("beceri") or 0.0)

    if kestirici is None:
        # Onarim MESRU DEGIL. Gozlem varsa OLDUGU GIBI gecer; yoksa YOK kalir.
        if gozlem is None:
            return {"deger": None, "guven": 0.0, "kaynak": "YOK",
                    "not": "onarim becerisi olculemedi/negatif; deger UYDURULMAZ"}
        return {"deger": gozlem, "guven": 1.0, "kaynak": "HAM",
                "not": "onarim gerekmedi ya da mesru degil; ham deger korundu"}

    adaylar = []
    for k in KESTIRICILER:
        v = _kestir(gecmis, k)
        if v is not None:
            adaylar.append((k, v))
    if gozlem is not None:
        adaylar.append(("HAM", gozlem))
    if not adaylar:
        return {"deger": None, "guven": 0.0, "kaynak": "YOK",
                "not": "aday uretilemedi - deger UYDURULMAZ"}

    maliyet = KANAL_MALIYETI.get(mod, 1.0)
    puanlar = []
    for ad, v in adaylar:
        lp = _log_onsel(v, gecmis)
        if ad != "HAM":
            lp -= maliyet          # onarim, gozlemi degistirmenin bedelini oder
        puanlar.append((ad, v, lp))
    puanlar.sort(key=lambda t: -t[2])
    p = kararli_softmax([t[2] for t in puanlar])
    kazanan = puanlar[0]
    posterior = p[0]

    # Onarim guveni = OLCULEN beceri x posterior. Ikisi de [0,1] oldugundan
    # sonuc [0,1]'dedir ve ASLA 1'i asamaz -> fail-open imkansiz.
    guven = max(0.0, min(1.0, beceri * posterior))
    return {"deger": kazanan[1], "guven": guven, "kaynak": kazanan[0],
            "posterior": posterior, "beceri": beceri,
            "not": "%s ile onarildi (mod=%s)" % (kazanan[0], mod)}


def kanal_onar(kayitlar, beklenen_adim_ms, deger_alani, zaman_alani="timestamp",
               pencere=None):
    """Bir kanali ucdan uca onarir: tespit -> beceri olcumu -> onarim.

    Doner: {"seri": [(zaman, deger)], "guven_serisi": [...], "rapor": {...}}
    Onarilan her degerin guveni AYRI tasinir; ortalama guven rapora girer.
    """
    tespit = bozulma_tespit(kayitlar, beklenen_adim_ms, deger_alani, zaman_alani)
    tekil = tespit["kayitlar"]
    if not tekil:
        return {"seri": [], "guven_serisi": [], "rapor": tespit,
                "beceri": {"beceri": 0.0, "kestirici": None},
                "ortalama_guven": 0.0}

    degerler = [v for _, v in tekil]
    beceri = onarim_becerisi(degerler, pencere)
    W = ONARIM_PENCERESI if pencere is None else int(pencere)

    seri, guvenler = [], []
    spike = set(tespit.get("spike_indeksleri") or [])
    for i, (t, v) in enumerate(tekil):
        gecmis = degerler[max(0, i - W):i]
        if i in spike:
            o = deger_onar(v, gecmis, "DEGISTIRME", beceri)
        else:
            o = {"deger": v, "guven": 1.0, "kaynak": "HAM", "not": ""}
        seri.append((t, o["deger"]))
        guvenler.append(o["guven"])

    # SILME modu: eksik zamanlar icin onarim (yalniz beceri izin veriyorsa)
    eksik = tespit.get("eksik_zamanlar") or []
    if eksik and beceri.get("kestirici"):
        zaman_indeks = dict((t, i) for i, (t, _) in enumerate(seri))
        for t in eksik:
            onceki = [v for tt, v in seri if tt < t and v is not None]
            o = deger_onar(None, onceki[-W:], "SILME", beceri)
            if o["deger"] is not None:
                seri.append((t, o["deger"]))
                guvenler.append(o["guven"])
        birlikte = sorted(zip([t for t, _ in seri], [v for _, v in seri], guvenler))
        seri = [(t, v) for t, v, _ in birlikte]
        guvenler = [g for _, _, g in birlikte]

    return {"seri": seri, "guven_serisi": guvenler, "rapor": tespit,
            "beceri": beceri,
            "ortalama_guven": ortalama(guvenler) if guvenler else 0.0,
            "en_zayif_guven": min(guvenler) if guvenler else 0.0}


# ============================================================ BOLUM 5
# BUTCE-UYUMLU GOSTERGE PROFILI.
# Gosterge pencereleri SABIT SECILMEZ; eldeki bar sayisindan TURETILIR.
# Gerekce (olculdu): sabit pencere (yuvarlanan 48 / ATR 14 / EMA 21) purge
# boslugunu 4H ile birlikte 1046 bara cikariyor; 200 barlik bir veriyle
# bolme DAIMA dejenere oluyor ve sistem hicbir zaman egitilemiyor.

PROFIL_ADAYLARI = (
    # (yuvarlanan, atr, ema_hizli, ema_yavas, rsi, ad)
    (48, 14, 8, 21, 14, "TAM"),
    (32, 10, 6, 16, 10, "ORTA"),
    (24, 7, 5, 8, 7, "KISA"),
    (16, 7, 4, 6, 7, "COK_KISA"),
    (12, 5, 3, 5, 5, "ASGARI"),
)


def gosterge_penceresi(profil, ad, periyot=None):
    if ad == "ema":
        return max(1, int(periyot)) * EMA_KESME_KATI
    if ad in ("atr", "rsi"):
        return max(1, int(periyot))
    if ad in ("z", "kanal"):
        return profil["yuvarlanan"]
    raise KeyError("bilinmeyen gosterge: %s" % ad)


def oznitelik_penceresi(profil):
    """Bir OZNITELIK SATIRININ geriye okudugu azami bar (kanitlanabilir ust sinir).

    Zincirleri tek tek toplamak sart: _z(atr, i) once atr[i-yuv:i]'yi okur,
    her atr[j] de kendi periyodunu okur -> zincir yuv + atr_periyodu.
    """
    yuv = profil["yuvarlanan"]
    return max(
        yuv,                                            # _kanal_konumu, _z(hacim)
        yuv + profil["atr"],                            # _z(atr) ZINCIRI
        profil["rsi"],
        EN_UZUN_GETIRI_GECIKMESI,
        profil["ema_yavas"] * EMA_KESME_KATI,
    )


def girdi_erisimi(profil, h4_var=True, h4_profil=None, onarim_penceresi=None):
    """Bir ORNEGIN geriye okudugu 15M bar sayisi (beyanli ust sinir).

    Uc bilesen: token gecikmesi + oznitelik penceresi + ONARIM penceresi.
    4H tarafi ayrica H4_BAR_ORANI ile buyur.
    """
    Wr = ONARIM_PENCERESI if onarim_penceresi is None else int(onarim_penceresi)
    W15 = oznitelik_penceresi(profil) + Wr
    e = max(0, GECIKME_SAYISI - 1) + W15
    if h4_var:
        h4p = h4_profil or profil
        W4 = oznitelik_penceresi(h4p)
        e = max(e, max(0, GECIKME_SAYISI - 1)
                + (2 * H4_BAR_ORANI - 1) + H4_BAR_ORANI * W4)
    return e


def purge_boslugu(profil, h4_var=True, h4_profil=None, onarim_penceresi=None):
    return (ETIKET_UFKU + EMBARGO
            + girdi_erisimi(profil, h4_var, h4_profil, onarim_penceresi))


def gereken_ornek_butcesi(acikllik, bosluk, kal_orani, hedef_kal):
    """'Ulasilamaz' demek YETMEZ - NE KADAR veriyle ulasilir, TURETILIR.

        kal (purge sonrasi) = azami * (kal_orani - bosluk/acikllik)
        gereken: >= hedef_kal  =>  azami >= hedef_kal / (kal_orani - bosluk/acikllik)

    Payda <= 0 ise bu ACIKLIKTA hicbir butce yetmez; cevap 'daha cok ornek'
    degil 'daha UZUN veri'dir. O durumda None yerine gereken ACIKLIGI doner
    (bkz. gereken_acikllik) - kullaniciya daima bir SAYI verilir."""
    pay = float(kal_orani) - float(bosluk) / float(max(1, acikllik))
    if pay <= 0.0:
        return None
    return int(math.ceil(float(hedef_kal) / pay))


def gereken_acikllik(bosluk, kal_orani, hedef_kal, pay_orani=0.5):
    """Payda pozitif olmasi icin gereken EN AZ veri acikligi (bar).

    kal_orani - bosluk/acikllik > 0  =>  acikllik > bosluk / kal_orani
    Sinira dayanmak sonsuz ornek isteyeceginden, paydanin kal_orani'nin
    pay_orani kadarina ulastigi nokta hedeflenir (YAPISAL secim):
        acikllik >= bosluk / (kal_orani * (1 - pay_orani))
    ve o aciklikta gereken ornek sayisi da birlikte doner.
    """
    payda = float(kal_orani) * (1.0 - float(pay_orani))
    acik = int(math.ceil(float(bosluk) / max(payda, 1e-9)))
    ornek = gereken_ornek_butcesi(acik, bosluk, kal_orani, hedef_kal)
    return {"acikllik": acik, "ornek": ornek,
            "gun_15m": acik / 96.0}


# ============================================================ BOLUM 10
# Kalibrasyon metrikleri. Dusuk ECE tek basina kanit DEGILDIR.


def profil_sec(bar_sayisi, h4_var=True, h4_profil_adi=None):
    """Eldeki bar sayisiyla DEJENERE OLMAYAN en UZUN pencereli profil CIFTINI
    (15M profili, 4H profili) secer.

    NEDEN CIFT: 4H tokeninin geriye erisimi H4_BAR_ORANI (16) ile carpilir;
    yani 4H penceresi 15M penceresinden 16 KAT pahalidir. Olculdu: 4H profili
    sabit tutuldugunda purge her 15M profilinde AYNI (550) kaliyor ve 15M
    tarafini kisaltmak hicbir sey kazandirmiyordu.

    Secim olcutu PERFORMANS DEGIL, BOLMENIN ISTATISTIKSEL GECERLILIGIDIR:
    kalibrasyon dilimi purge SONRASI 2*ASGARI_OLCUM ornege sahip olmali.
    Bu yine de bir ASIRI-UYUM riskidir ve ACIKCA beyan edilir.
    """
    def yap(p):
        yuv, atr, eh, ey, rsi, ad = p
        return {"yuvarlanan": yuv, "atr": atr, "ema_hizli": eh,
                "ema_yavas": ey, "rsi": rsi, "ad": ad}

    adaylar15 = [yap(p) for p in PROFIL_ADAYLARI]
    if not h4_var:
        adaylar4 = [None]
    elif h4_profil_adi:
        adaylar4 = [yap(p) for p in PROFIL_ADAYLARI if p[5] == h4_profil_adi]
    else:
        adaylar4 = [yap(p) for p in PROFIL_ADAYLARI]

    def olcut(pr, h4p):
        b = purge_boslugu(pr, h4_var, h4p)
        g = gereken_ornek_butcesi(bar_sayisi, b, BOLME_ORANLARI[1],
                                  2 * ASGARI_OLCUM)
        taban = 3 * (b + 5)
        gb = max(g, taban) if g else None
        return b, gb, (gb is not None and gb <= bar_sayisi)

    denenen = []
    # Kisaltma butcesi k = i + j; kucuk k = uzun pencere. Esitlikte 15M'i
    # uzun tutmayi tercih et (i kucuk), cunku karar tetigi 15M'dedir.
    for k in range(len(adaylar15) + len(adaylar4) - 1):
        for i in range(min(k, len(adaylar15) - 1) + 1):
            j = k - i
            if j >= len(adaylar4):
                continue
            pr, h4p = adaylar15[i], adaylar4[j]
            b, gb, uygun = olcut(pr, h4p)
            denenen.append({"15m": pr["ad"],
                            "4h": (h4p["ad"] if h4p else "YOK"),
                            "purge": b, "gereken_bar": gb, "uygun": uygun})
            if uygun:
                return {"profil": pr, "h4_profil": h4p, "purge": b,
                        "gereken_bar": gb, "denenen": denenen,
                        "kaynak": "OLCULEN (eldeki bar sayisindan turetildi)",
                        "not": ""}

    pr = adaylar15[-1]
    h4p = adaylar4[-1]
    b, gb, _ = olcut(pr, h4p)
    if gb is None:
        ga = gereken_acikllik(b, BOLME_ORANLARI[1], 2 * ASGARI_OLCUM)
        gb = ga["ornek"] if ga["ornek"] else ga["acikllik"]
        gb = max(gb, ga["acikllik"])
        notu = ("HICBIR profil cifti %d bara sigmadi. Bu ACIKLIKTA purge (%d "
                "bar) kalibrasyon diliminin tamamini yiyor; gereken en az %d "
                "bar (%.1f gun 15M). 4H katmani kaldirilirsa cok daha az yeter."
                % (bar_sayisi, b, gb, gb / 96.0))
    else:
        notu = ("HICBIR profil cifti %d bara sigmadi. En kisa cift ile bile "
                "gereken %d bar (%.1f gun 15M). 4H katmani kaldirilirsa cok "
                "daha az bar yeter." % (bar_sayisi, gb, gb / 96.0))
    return {"profil": pr, "h4_profil": h4p, "purge": b, "gereken_bar": gb,
            "denenen": denenen, "kaynak": "OLCULEN", "not": notu}


# ============================================================ BOLUM 6
# Gostergeler (stdlib, sonlu pencere, kanitlanabilir geriye erisim).

def ema(degerler, periyot):
    """Ustel agirlikli ortalama, SONLU pencerede KESILMIS ve normalize.

    Ozyinelemeli (IIR) yazim TERK EDILDI: zincir serinin BASINA kadar uzanir
    ve yalniz float alt-tasmasi keser -> erisim TOLERANSA baglidir. Toleransa
    bagli bir sayi purge korkulugu OLAMAZ. Kesme, ustel agirligi terk etmez;
    ayni alfa*(1-alfa)^L profili periyot*EMA_KESME_KATI barda kesilip yeniden
    normalize edilir (agirliklar toplami 1).
    """
    if not degerler:
        return []
    periyot = max(1, int(periyot))
    alfa = 2.0 / (periyot + 1.0)
    pencere = periyot * EMA_KESME_KATI
    ag = [alfa * (1.0 - alfa) ** g for g in range(pencere)]
    kum, t = [], 0.0
    for a in ag:
        t += a
        kum.append(t)
    cikti = []
    for i in range(len(degerler)):
        n = min(i + 1, pencere)
        pay = sum(ag[g] * float(degerler[i - g]) for g in range(n))
        cikti.append(pay / kum[n - 1])
    return cikti


def atr(barlar, periyot=14):
    ar = []
    for i, b in enumerate(barlar):
        onceki = barlar[i - 1]["c"] if i else b["c"]
        ar.append(max(b["h"] - b["l"], abs(b["h"] - onceki), abs(b["l"] - onceki)))
    cikti = []
    for i in range(len(ar)):
        p = ar[max(0, i - periyot + 1):i + 1]
        cikti.append(sum(p) / len(p))
    return cikti


def rsi(kapanislar, periyot=14):
    cikti = [50.0] * len(kapanislar)
    for i in range(periyot, len(kapanislar)):
        kaz, kay = [], []
        for j in range(i - periyot + 1, i + 1):
            f = kapanislar[j] - kapanislar[j - 1]
            kaz.append(max(f, 0.0))
            kay.append(max(-f, 0.0))
        ok, oy = sum(kaz) / len(kaz), sum(kay) / len(kay)
        cikti[i] = (100.0 if ok > 0 else 50.0) if oy == 0 else 100.0 - 100.0 / (1.0 + ok / oy)
    return cikti


# ============================================================ BOLUM 7
# Oznitelik satiri. ONARIM IZI AYRI BIR AILEDIR (uydurma degil, olcum).

AILELER = {
    "fiyat": 6,      # getiri1, getiri4, getiri16, ema_farki, rsi, kanal_konumu
    "hacim": 2,      # hacim_z, nominal_hacim_z
    "turev": 4,      # oi_degisim, taker_dengesi, cvd, kapsam
    "oynaklik": 3,   # atr_orani, oynaklik_orani, rejim
    "onarim": 3,     # onarim_guveni, onarim_farki, bozulma_yogunlugu
}
ZAMAN_DILIMLERI = ("15m", "4h")


def _kanal_konumu(barlar, i, pencere):
    onceki = barlar[max(0, i - pencere):i]
    if not onceki:
        return 0.0
    yuksek = max(b["h"] for b in onceki)
    dusuk = min(b["l"] for b in onceki)
    g = yuksek - dusuk
    if g <= 0:
        return 0.0
    return kirp((barlar[i]["c"] - dusuk) / g * 2.0 - 1.0)


def _z(degerler, i, pencere):
    gecmis = degerler[max(0, i - pencere):i]
    if len(gecmis) < 5:
        return 0.0
    o = ortalama(gecmis)
    s = std(gecmis)
    if s < SABIT_TOLERANSI:
        return 0.0
    return kirp((degerler[i] - o) / s, -5.0, 5.0) / 5.0


def gostergeler_kur(barlar, profil):
    kapanislar = [b["c"] for b in barlar]
    hacimler = [b.get("v", 0.0) for b in barlar]
    return {
        "kapanislar": kapanislar,
        "hacimler": hacimler,
        # Hacim x fiyat serisi bar basina DEGIL, seri basina bir kez kurulur.
        "hacim_deger": [h * k for h, k in zip(hacimler, kapanislar)],
        "ema_hizli": ema(kapanislar, profil["ema_hizli"]),
        "ema_yavas": ema(kapanislar, profil["ema_yavas"]),
        "atr": atr(barlar, profil["atr"]),
        "rsi": rsi(kapanislar, profil["rsi"]),
    }


def _olcekli(t, anahtar, olcekler):
    """Turev ozniteligini kanalin KENDI robust sigmasina bolup TEK KEZ kirpar.

    Olcek yoksa (kanal cok kisa / sabit) oznitelik URETILMEZ ve 0.0 doner -
    ama bu bir "notr enjeksiyonu" DEGILDIR: ayni satirdaki kapsam bayragi
    ve gozlem maskesi modele bu ailenin olculemedigini soyler.
    """
    v = t.get(anahtar)
    if v is None:
        return 0.0
    sg = (olcekler or {}).get(anahtar)
    if not sg:
        return 0.0
    return kirp(float(v) / (5.0 * sg))


def satir_uret(barlar, gost, turev_seri, onarim_seri, profil, i, olcekler=None):
    """Bes aileli oznitelik satiri.

    turev_seri : bar basina sozluk listesi (SERI, tek anlik deger DEGIL)
    onarim_seri: bar basina {"guven","fark","yogunluk"} - ONARIM IZI

    onarim ailesi neden var: "bu barin OI'si 0.31 guvenle onarildi" GERCEK bir
    bilgidir. v3'te bu bilgi hic uretilmiyordu; pydroid surumunde ise dikkat
    skoruna log(quality) diye ENJEKTE ediliyordu - o yanlisti, cunku egitim ve
    cikarim arasinda dikkati 20x kaydiriyordu. Dogru yer: normal bir OZNITELIK.
    """
    kapanislar = gost["kapanislar"]
    yuv = profil["yuvarlanan"]
    fiyat = [
        kirp(math.log(kapanislar[i] / kapanislar[i - 1])) if i >= 1 else 0.0,
        kirp(math.log(kapanislar[i] / kapanislar[i - 4])) if i >= 4 else 0.0,
        kirp(math.log(kapanislar[i] / kapanislar[i - EN_UZUN_GETIRI_GECIKMESI]))
        if i >= EN_UZUN_GETIRI_GECIKMESI else 0.0,
        kirp((gost["ema_hizli"][i] - gost["ema_yavas"][i])
             / max(gost["atr"][i], EPSILON) / 2.0),
        kirp((gost["rsi"][i] - 50.0) / 20.0),
        _kanal_konumu(barlar, i, yuv),
    ]
    hacim = [_z(gost["hacimler"], i, yuv), _z(gost["hacim_deger"], i, yuv)]

    t = None if turev_seri is None else turev_seri[i]
    if t is None:
        # Kapsam 0 ISARETLENIR; deger UYDURULMAZ. 0.0'lar burada "notr
        # enjeksiyonu" DEGIL, kapsam bayraginin (son eleman 0.0) tasidigi
        # "bu ailede olcum YOK" bilgisinin yanindaki dolgudur - ve model
        # kapsam bayragini gordugu icin ayirt edebilir.
        turev_vek = [0.0, 0.0, 0.0, 0.0]
    else:
        # TEK asamali kirp, kanal olcegine bolunmus. Cift kirp YOK.
        turev_vek = [_olcekli(t, "oi_degisim", olcekler),
                     _olcekli(t, "taker_dengesi", olcekler),
                     kirp(t.get("cvd", 0.0)),
                     1.0]
    oynaklik = [
        kirp(gost["atr"][i] / max(kapanislar[i], EPSILON) * 100.0),
        kirp(_z(gost["atr"], i, yuv) * 2.0),
        1.0 if gost["ema_hizli"][i] > gost["ema_yavas"][i] else -1.0,
    ]
    o = (onarim_seri[i] if onarim_seri else None) or {}
    # ONARIM AILESI = GOZLEM MASKESI. Surekli onarim guveni ("guven") BURAYA
    # GIRMEZ; o yalniz stake eksenindedir (bkz. turev_serisi_kur gerekcesi).
    onarim = [
        kirp(float(o.get("m_oi", 1.0)), 0.0, 1.0) * 2.0 - 1.0,
        kirp(float(o.get("m_taker", 1.0)), 0.0, 1.0) * 2.0 - 1.0,
        kirp(float(o.get("yogunluk", 0.0)), 0.0, 1.0) * 2.0 - 1.0,
    ]
    return {"fiyat": fiyat, "hacim": hacim, "turev": turev_vek,
            "oynaklik": oynaklik, "onarim": onarim}


class Olcekleyici:
    """Gecmise dayali normalizasyon. YALNIZ train diliminden fit edilir.
    Sabit kolon (std=0) bilgi tasimaz -> ham deger SIZDIRILMAZ, 0.0 verilir."""

    def __init__(self):
        self._p = {}
        self.sabit_kolonlar = []
        self._fit = False

    def fit(self, satirlar, kesim):
        egitim = satirlar[:max(1, int(kesim))]
        self._p = {}
        self.sabit_kolonlar = []
        for aile, boyut in AILELER.items():
            kol = []
            for j in range(boyut):
                d = [float(s[aile][j]) for s in egitim if aile in s]
                kol.append(self._kolon(aile, j, d))
            self._p[aile] = kol
        self._fit = True

    def _kolon(self, aile, j, d):
        if not d:
            self.sabit_kolonlar.append((aile, j))
            return (0.0, 1.0, True)
        o = ortalama(d)
        s = std(d)
        sabit = s < SABIT_TOLERANSI
        if sabit:
            self.sabit_kolonlar.append((aile, j))
        return (o, 1.0 if sabit else s, sabit)

    def donustur(self, aile, degerler):
        if not self._fit:
            raise RuntimeError("Olcekleyici fit edilmeden kullanilamaz")
        c = []
        for d, (o, s, sabit) in zip(degerler, self._p[aile]):
            c.append(0.0 if sabit else kirp((float(d) - o) / s, -5.0, 5.0))
        return c


# ============================================================ BOLUM 8
# Konum kodu + nedensel dikkat + FFN + logit basligi.

SEMBOL_EKSENI_FAZI = math.pi / 4.0


def _sinuzoidal(konum, boyut, taban, faz=0.0):
    c = []
    for k in range(boyut):
        payda = taban ** (2.0 * (k // 2) / max(1, boyut))
        aci = konum / payda + faz
        c.append(math.sin(aci) if k % 2 == 0 else math.cos(aci))
    return c


def zaman_konumu(gecikme, boyut):
    return [x * 0.10 for x in _sinuzoidal(gecikme, boyut, 10000.0)]


def eksen_konumu(indeks, boyut):
    """Zaman ekseninden AYRISIK. Faz kaydirmasi ZORUNLU: konum=0'da
    sin(0)=0, cos(0)=1 her tabanda AYNI vektoru verir -> iki eksen cakisir."""
    return [x * 0.10 for x in _sinuzoidal(indeks, boyut, 97.0,
                                          faz=SEMBOL_EKSENI_FAZI)]


def matris(satir, sutun, tohum, olcek=0.12):
    r = tohumlu_rng(*tohum)
    return [[r.uniform(-olcek, olcek) for _ in range(sutun)] for _ in range(satir)]


def vektor(boyut, tohum, olcek=0.12):
    r = tohumlu_rng(*tohum)
    return [r.uniform(-olcek, olcek) for _ in range(boyut)]


def matvec(M, v):
    return [sum(s[j] * v[j] for j in range(len(v))) for s in M]


def nokta(a, b):
    return sum(x * y for x, y in zip(a, b))


def topla_vek(*vs):
    if not vs:
        return []
    return [sum(v[i] for v in vs) for i in range(len(vs[0]))]


def katman_norm(v, eps=1e-5):
    o = sum(v) / len(v)
    s = math.sqrt(sum((x - o) ** 2 for x in v) / len(v) + eps)
    return [(x - o) / s for x in v]


def relu(v):
    return [max(0.0, x) for x in v]


class Kodlayici:
    """Tek bloklu nedensel kodlayici.

    Karar temsili = son token + TUM durumlarin havuzu. Havuz sayesinde
    maskelenen konumlar ciktiyi GERCEKTEN etkiler; yalniz son tokene
    bakilsaydi nedensel maske olu kod olurdu.
    """

    def __init__(self, boyut=16, bas_sayisi=2, tohum=2026):
        self.boyut = boyut
        self.bas_sayisi = bas_sayisi
        self.bas_boyut = boyut // bas_sayisi
        self.tohum = tohum
        self.wq = [matris(self.bas_boyut, boyut, (tohum, "wq", h)) for h in range(bas_sayisi)]
        self.wk = [matris(self.bas_boyut, boyut, (tohum, "wk", h)) for h in range(bas_sayisi)]
        self.wv = [matris(self.bas_boyut, boyut, (tohum, "wv", h)) for h in range(bas_sayisi)]
        self.wo = matris(boyut, self.bas_boyut * bas_sayisi, (tohum, "wo"))
        self.ff1 = matris(boyut * 2, boyut, (tohum, "ff1"))
        self.ff2 = matris(boyut, boyut * 2, (tohum, "ff2"))

    def _dikkat(self, durumlar, qk_acik, maske_acik):
        n = len(durumlar)
        olcek = math.sqrt(max(1, self.bas_boyut))
        cikti_bas = []
        for h in range(self.bas_sayisi):
            q = [matvec(self.wq[h], x) for x in durumlar]
            k = [matvec(self.wk[h], x) for x in durumlar]
            v = [matvec(self.wv[h], x) for x in durumlar]
            c = []
            for i in range(n):
                sk = []
                for j in range(n):
                    if maske_acik and j > i:
                        sk.append(-1e9)
                    elif qk_acik:
                        sk.append(nokta(q[i], k[j]) / olcek)
                    else:
                        sk.append(0.0)
                a = kararli_softmax(sk)
                c.append([sum(a[j] * v[j][u] for j in range(n))
                          for u in range(self.bas_boyut)])
            cikti_bas.append(c)
        return cikti_bas

    def ileri(self, durumlar, qk_acik=True, maske_acik=True, ffn_acik=True):
        n = len(durumlar)
        cb = self._dikkat(durumlar, qk_acik, maske_acik)
        yeni = []
        for i in range(n):
            b = []
            for h in range(self.bas_sayisi):
                b.extend(cb[h][i])
            yeni.append(katman_norm(topla_vek(durumlar[i], matvec(self.wo, b))))
        havuz = [sum(y[j] for y in yeni) / n for j in range(self.boyut)]
        hv = topla_vek(yeni[-1], havuz)
        if ffn_acik:
            hv = topla_vek(hv, matvec(self.ff2, relu(matvec(self.ff1, hv))))
        return katman_norm(hv)


class Baslik:
    """Iki sinifli (LONG/SHORT) egitilen logit basligi, sinif-agirlikli CE."""

    def __init__(self, boyut=16, tohum=3000):
        self.boyut = boyut
        self.w = matris(2, boyut, (tohum, "baslik-w"), 0.02)
        self.b = vektor(2, (tohum, "baslik-b"), 0.02)
        self.tohum = tohum

    def logit(self, x):
        return [nokta(self.w[k], x) + self.b[k] for k in range(2)]

    def _agirliklar(self, ornekler):
        sayim = [0, 0]
        for o in ornekler:
            sayim[o["y"]] += 1
        t = sum(sayim) or 1
        return [t / (2.0 * max(1, s)) for s in sayim]

    def egit(self, ornekler, devir=50, hiz=0.12, azalma=5e-4):
        if not ornekler:
            return
        ag = self._agirliklar(ornekler)
        rng = tohumlu_rng(self.tohum, "karistir")
        sira = list(range(len(ornekler)))
        for adim in range(devir):
            rng.shuffle(sira)
            gw = [[0.0] * self.boyut for _ in range(2)]
            gb = [0.0, 0.0]
            for ix in sira:
                o = ornekler[ix]
                p = kararli_softmax(self.logit(o["x"]))
                a = ag[o["y"]]
                for k in range(2):
                    hata = (p[k] - (1.0 if k == o["y"] else 0.0)) * a
                    for j in range(self.boyut):
                        gw[k][j] += hata * o["x"][j]
                    gb[k] += hata
            h = hiz / (1.0 + adim / 25.0)
            payda = max(1, len(ornekler))
            for k in range(2):
                for j in range(self.boyut):
                    self.w[k][j] -= h * (gw[k][j] / payda + azalma * self.w[k][j])
                self.b[k] -= h * gb[k] / payda


# ============================================================ BOLUM 9
# Kronolojik bolme + purge/embargo/girdi erisimi + sizinti denetimi.

def _ornek_adimi(sirali):
    if len(sirali) < 2:
        return 1.0
    return max(1.0, (sirali[-1] - sirali[0]) / float(len(sirali) - 1))


def kronolojik_bol(indeksler, ufuk, embargo, giris_erisimi=0, oranlar=None):
    """Bosluk UC bilesenlidir: etiket ufku (ileri), embargo (guvenlik) ve
    girdi erisimi (geri). Ucuncusu olmadan onceki bolmenin ETIKET penceresi
    sonraki bolmenin GIRDI penceresiyle ortusur."""
    oranlar = BOLME_ORANLARI if oranlar is None else oranlar
    sirali = sorted(indeksler)
    n = len(sirali)
    bosluk = int(ufuk) + int(embargo) + int(giris_erisimi)
    kayip = int(bosluk / _ornek_adimi(sirali)) + 1
    if n < 3 * (kayip + 5):
        return {"train": [], "kalibrasyon": [], "test": [], "atilan": n,
                "bosluk": bosluk,
                "not": "yetersiz ornek - bolme yapilamadi (n=%d, gereken %d)"
                       % (n, 3 * (kayip + 5))}
    k1 = int(n * oranlar[0])
    k2 = int(n * (oranlar[0] + oranlar[1]))
    train, kal, test = sirali[:k1], sirali[k1:k2], sirali[k2:]
    if train and kal:
        train = [i for i in train if i + bosluk < kal[0]]
    if kal and test:
        kal = [i for i in kal if i + bosluk < test[0]]
    atilan = n - (len(train) + len(kal) + len(test))
    return {"train": train, "kalibrasyon": kal, "test": test,
            "atilan": atilan, "bosluk": bosluk, "not": ""}


def sizinti_var_mi(bolme, ufuk, giris_penceresi):
    for once, sonra in (("train", "kalibrasyon"), ("kalibrasyon", "test")):
        a, b = bolme.get(once) or [], bolme.get(sonra) or []
        if not a or not b:
            continue
        if max(a) + int(ufuk) >= min(b) - int(giris_penceresi) + 1:
            return True
    return False


def _kova(ciftler, bin_sayisi):
    kovalar = [[] for _ in range(bin_sayisi)]
    for p, y in ciftler:
        guven = max(p, 1.0 - p)
        tahmin = 1 if p >= 0.5 else 0
        ix = min(bin_sayisi - 1, int(guven * bin_sayisi))
        kovalar[ix].append((guven, 1.0 if tahmin == y else 0.0))
    return kovalar


def ece(ciftler, bin_sayisi=10):
    if not ciftler:
        return None
    toplam = len(ciftler)
    d = 0.0
    for k in _kova(ciftler, bin_sayisi):
        if not k:
            continue
        d += (len(k) / toplam) * abs(ortalama([g for g, _ in k])
                                     - ortalama([x for _, x in k]))
    return d


def mce(ciftler, bin_sayisi=10):
    if not ciftler:
        return None
    en = 0.0
    for k in _kova(ciftler, bin_sayisi):
        if not k:
            continue
        en = max(en, abs(ortalama([g for g, _ in k]) - ortalama([x for _, x in k])))
    return en


def ece_duyarlilik(ciftler, binler=(5, 10, 15, 20)):
    if not ciftler:
        return {"degerler": {}, "tek_bine_cokme": True, "dolu_kova": 0}
    dolu = sum(1 for k in _kova(ciftler, 10) if k)
    return {"degerler": dict((n, ece(ciftler, n)) for n in binler),
            "tek_bine_cokme": dolu <= 1, "dolu_kova": dolu}


def brier(ciftler):
    return None if not ciftler else ortalama([(p - y) ** 2 for p, y in ciftler])


def auroc(ciftler):
    poz = [p for p, y in ciftler if y == 1]
    neg = [p for p, y in ciftler if y == 0]
    if not poz or not neg:
        return None
    t = 0.0
    for a in poz:
        for b in neg:
            t += 1.0 if a > b else (0.5 if a == b else 0.0)
    return t / (len(poz) * len(neg))


# ============================================================ BOLUM 11
# Kalibrasyon secimi: sicaklik vs izotonik, IC-HOLDOUT ile.

SICAKLIK_IZGARASI = tuple(math.exp(-2.0 + 4.0 * i / 40.0) for i in range(41))


def long_olasiligi(p):
    return p[LONG_SINIFI]


def topluluk_olasilik(x, basliklar, sicaklik=1.0):
    g = [kararli_softmax(b.logit(x), sicaklik) for b in basliklar]
    n = len(g) or 1
    p = [sum(x2[k] for x2 in g) / n for k in range(2)]
    argm = [0 if x2[0] >= x2[1] else 1 for x2 in g]
    uzlasi = max(argm.count(0), argm.count(1)) / n
    dagilim = sum(sum((x2[k] - p[k]) ** 2 for x2 in g) / n for k in range(2)) / 2.0
    return {"p": p, "gorusler": g, "uzlasi": uzlasi, "dagilim": dagilim}


def _nll(ornekler, basliklar, sicaklik):
    if not ornekler:
        return float("inf")
    t = 0.0
    for o in ornekler:
        p = topluluk_olasilik(o["x"], basliklar, sicaklik)["p"]
        t += -math.log(max(1e-12, p[o["y"]]))
    return t / len(ornekler)


def sicaklik_fit(ornekler, basliklar):
    en_T, en_nll = 1.0, float("inf")
    for T in SICAKLIK_IZGARASI:
        d = _nll(ornekler, basliklar, T)
        if d < en_nll:
            en_T, en_nll = T, d
    sinirda = (en_T <= SICAKLIK_IZGARASI[0] * 1.001
               or en_T >= SICAKLIK_IZGARASI[-1] * 0.999)
    return {"T": en_T, "nll": en_nll, "sinirda": sinirda}


def izotonik_fit(ciftler):
    s = sorted(ciftler, key=lambda c: c[0])
    if not s:
        return lambda p: p
    x = [c[0] for c in s]
    y = [float(c[1]) for c in s]
    w = [1.0] * len(y)
    i = 0
    while i < len(y) - 1:
        if y[i] <= y[i + 1] + 1e-12:
            i += 1
            continue
        ta = w[i] + w[i + 1]
        y[i:i + 2] = [(y[i] * w[i] + y[i + 1] * w[i + 1]) / ta]
        w[i:i + 2] = [ta]
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
    if not ciftler:
        return float("inf")
    t = 0.0
    for p, y in ciftler:
        p = min(1.0 - 1e-9, max(1e-9, p))
        t += -math.log(p if y == 1 else 1.0 - p)
    return t / len(ciftler)


def _ham_ciftler(ornekler, basliklar, sicaklik=1.0):
    return [(long_olasiligi(topluluk_olasilik(o["x"], basliklar, sicaklik)["p"]),
             o["y"]) for o in ornekler]


def kalibrasyon_sec(kal, basliklar):
    """ADIL YARISMA: izotonik, veri noktasi kadar serbestlik derecesine cikar;
    sicaklik TEK parametredir. Ayni kumede fit+puanlama yarisma degil EZBER
    olcer ve yapisal olarak izotoniki secer. O yuzden ic-holdout."""
    n = len(kal)
    if n < 2 * ASGARI_OLCUM:
        s = sicaklik_fit(kal, basliklar)
        return {"yontem": "sicaklik", "T": s["T"], "fn": None, "nll": s["nll"],
                "sinirda": s["sinirda"],
                "yarisma": "YAPILMADI - yetersiz ornek (n=%d < %d), fail-closed sicaklik"
                           % (n, 2 * ASGARI_OLCUM)}
    kesim = n // 2
    fit_k, puan_k = kal[:kesim], kal[kesim:]
    sf = sicaklik_fit(fit_k, basliklar)
    s_nll = _ikili_nll(_ham_ciftler(puan_k, basliklar, sf["T"]))
    izo = izotonik_fit(_ham_ciftler(fit_k, basliklar))
    i_nll = _ikili_nll([(izo(p), y) for p, y in _ham_ciftler(puan_k, basliklar)])
    if i_nll < s_nll:
        return {"yontem": "izotonik", "T": 1.0,
                "fn": izotonik_fit(_ham_ciftler(kal, basliklar)),
                "nll": i_nll, "sinirda": False, "yarisma": "ic-holdout"}
    st_ = sicaklik_fit(kal, basliklar)
    return {"yontem": "sicaklik", "T": st_["T"], "fn": None, "nll": s_nll,
            "sinirda": st_["sinirda"], "yarisma": "ic-holdout"}


# ============================================================ BOLUM 12
# SHRINKAGE — DORT KAPI. v3'te uc kapi vardi; DORDUNCUSU bu surumun kalbi.
#   s = s_kanit * s_kalibrasyon * s_kapsam * s_onarim
# Dordu de [0,1]. Carpim oldugu icin HERHANGI biri 0 ise stake TAM 0'dir ve
# hicbir kapi digerini "telafi" edemez -> fail-open yapisal olarak imkansiz.

def shrinkage_katsayisi(dogru, toplam, ece_enkotu, dolu_kanal, toplam_kanal,
                        onarim_guveni=1.0, taban_oran=0.5,
                        ece_tek_bin=False, sicaklik_sinirda=False):
    """OLCULEN UYARI KAPIYA BAGLANIR. Bir uyariyi olcup hukme baglamamak,
    olcmemekle ayni - ustelik daha kotusu, cunku 'olctuk' denir."""
    taban = kirp(float(taban_oran), 0.5, 1.0)
    alt, _ = wilson_araligi(dogru, toplam)
    pay = max(0.0, 1.0 - taban)
    s_kanit = 0.0 if pay <= 0.0 else kirp((alt - taban) / pay, 0.0, 1.0)

    if ece_enkotu is None or ece_tek_bin or sicaklik_sinirda:
        s_kalib = 0.0
    else:
        s_kalib = kirp(1.0 - float(ece_enkotu) / ECE_TAVANI, 0.0, 1.0)

    s_kapsam = 0.0 if toplam_kanal <= 0 else kirp(dolu_kanal / toplam_kanal, 0.0, 1.0)

    # DORDUNCU KAPI: onarim guveni. [0,1] araligina KIRPILIR -> 1'i asamaz,
    # yani riski ASLA BUYUTEMEZ. Bu, "quality bias" hatasinin panzehiridir.
    s_onarim = kirp(float(onarim_guveni), 0.0, 1.0)

    return {"s": s_kanit * s_kalib * s_kapsam * s_onarim,
            "s_kanit": s_kanit, "s_kalibrasyon": s_kalib,
            "s_kapsam": s_kapsam, "s_onarim": s_onarim}


def daralt(p, s, hedef=0.5):
    """p'yi kanit gucune gore HEDEF'e dogru daraltir.
    Tarafsiz hedef 0.5 DEGILDIR: odul asimetrikse p=0.5'te bile EV pozitiftir.
    Dogru hedef bahsin BASABAS olasiligidir (bkz. stake_hesapla)."""
    hedef = kirp(hedef, 0.0, 1.0)
    return hedef + kirp(s, 0.0, 1.0) * (kirp(p, 0.0, 1.0) - hedef)


# ============================================================ BOLUM 13
# Maliyet, asimetrik Kelly, geometri izgarasi, likidasyon tavani.

def maliyet_r(giris, stop_mesafesi, komisyon, kayma, funding):
    mesafe = max(abs(float(stop_mesafesi)), EPSILON)
    nominal = 2.0 * abs(float(giris)) * (float(komisyon) + float(kayma))
    return (nominal + abs(float(funding)) * abs(float(giris))) / mesafe


def net_kanatlar(R, cost_r):
    return float(R) - float(cost_r), 1.0 + float(cost_r)


def basabas_p(b, a):
    return None if b <= 0.0 else a / (a + b)


def kelly_asimetrik(p, b, a):
    if b <= 0.0 or a <= 0.0:
        return 0.0
    p = kirp(p, 0.0, 1.0)
    f = (p * b - (1.0 - p) * a) / (a * b)
    return max(0.0, f)


def stake_hesapla(p_ham, s, b, a, lam=1.0):
    """Stake sozlesmesinin TEK garanti noktasi: kanit yoksa f* TAM OLARAK 0.

    KAYAN NOKTA KORKULUGU: p0 = a/(a+b) iken Kelly payi p0*b-(1-p0)*a ancak
    TAM aritmetikte sadelesir; float64'te 1e-16 mertebesinde artik kalir ve
    bu artik ZARARSIZ DEGIL (bir tuketici f>0 gorup pozisyon acar, digeri
    f==0 gorup 'bahis sifir' der). Bu yuzden s<=0 dalinda f DOGRUDAN 0.0
    doner. Bu bir ESIK DEGIL, TANIM: s=0 'kanit yok' demektir.
    """
    p0 = basabas_p(b, a)
    if p0 is None:
        return {"f": 0.0, "p_kullanilan": None, "p0": None,
                "not": "kazanc kanadi <= 0 - bahis matematiksel olarak imkansiz"}
    s = kirp(s, 0.0, 1.0)
    pk = daralt(p_ham, s, hedef=p0)
    if s <= 0.0:
        return {"f": 0.0, "p_kullanilan": pk, "p0": p0,
                "not": "kanit yok (s=0) - f* tanim geregi 0"}
    # BASABAS ALTI/ESITI: TANIM GEREGI bahis yok. Kelly payi
    # p*b - (1-p)*a ancak TAM aritmetikte p=p0'da sadelesir; float64'te
    # ~1e-17 artik kalir ve bu artik ZARARSIZ DEGIL - olculdu: R=1.5,
    # cost=0.0, s=1.0 -> f = 7.4e-17 ve bahis_acilir_mi TRUE donuyordu,
    # yani sifir bahis POZISYON ACIYORDU. Bu bir ESIK degil TANIMDIR.
    if pk <= p0:
        return {"f": 0.0, "p_kullanilan": pk, "p0": p0,
                "not": "p_kullanilan <= basabas - tanim geregi bahis YOK"}
    return {"f": kelly_asimetrik(pk, b, a) * max(0.0, float(lam)),
            "p_kullanilan": pk, "p0": p0, "not": ""}


def likidasyon_tavani(giris, likidasyon, kaldirac_azami,
                      guvenlik=LIKIDASYON_GUVENLIK_PAYI):
    if likidasyon is None or kaldirac_azami is None or kaldirac_azami <= 0:
        return 0.0
    g = abs(float(giris))
    if g <= 0:
        return 0.0
    oran = abs(g - float(likidasyon)) / g
    return max(0.0, min(1.0 / float(kaldirac_azami), oran * float(guvenlik)))


def stake_gecit_kirp(f_stake, f_gecit):
    """Stake, GECIDIN kendi f'ini ASAMAZ (fail-closed).

    Gecit (geometri_sec) ve stake (stake_hesapla) ayni bahsi IKI FARKLI
    olasilikla boyutlandirir: gecit p_bilesik_alt ile, stake daraltilmis
    p ile. Ayrisirlarsa KUCUK olan gecerlidir - buyugu secmek, gecidi
    acan kanittan DAHA BUYUK bir bahis demektir.

    Doner: (f, bagladi_mi)
    """
    f_stake = max(0.0, float(f_stake))
    f_gecit = max(0.0, float(f_gecit))
    return (f_gecit, True) if f_stake > f_gecit else (f_stake, False)


def stake_kirp(f_ham, f_max):
    f_ham = max(0.0, float(f_ham))
    f_max = max(0.0, float(f_max))
    if f_ham > f_max:
        return {"f": f_max, "kirpildi": True, "f_ham": f_ham, "f_max": f_max}
    return {"f": f_ham, "kirpildi": False, "f_ham": f_ham, "f_max": f_max}


IZGARA = ((1.0, 1.5), (1.0, 2.0), (1.0, 3.0), (1.0, 4.0),
          (1.5, 2.0), (1.5, 3.0), (1.5, 4.0), (1.5, 5.0),
          (2.0, 3.0), (2.0, 4.0), (2.0, 6.0))


def seviyeler(giris, atr_deger, yon, stop_k, hedef_k):
    """R = hedef_mesafe / stop_mesafe. BASKA BIR R TANIMI YOKTUR.
    (Uc ayri belgede 'stop 1.5xATR + hedef 2.0xATR = RRR 1:2' yazildi;
     gercek R = 1.3333. Bu fonksiyon o hatayi yapisal olarak imkansiz kilar.)"""
    giris = float(giris)
    a = max(float(atr_deger), EPSILON)
    if yon == "LONG":
        stop, hedef = giris - stop_k * a, giris + hedef_k * a
    else:
        stop, hedef = giris + stop_k * a, giris - hedef_k * a
    stop_mesafe = abs(giris - stop)
    hedef_mesafe = abs(hedef - giris)
    return {"giris": giris, "stop": stop, "hedef": hedef,
            "stop_mesafesi": stop_mesafe, "hedef_mesafesi": hedef_mesafe,
            "R": hedef_mesafe / max(stop_mesafe, EPSILON)}


def ilk_gecis_olcum(barlar, indeksler, yon, stop_k, hedef_k, atr_serisi, azami_bar):
    """Her giris indeksi icin hangi bariyerin ONCE vuruldugunu sayar.
    Ayni barda ikisi de vurulursa muhafazakar olarak STOP sayilir."""
    sayim = {"hedef": 0, "stop": 0, "zaman_asimi": 0}
    for i in indeksler:
        if i >= len(barlar) - 1 or i >= len(atr_serisi):
            continue
        giris = barlar[i]["c"]
        a = max(atr_serisi[i], EPSILON)
        sev = seviyeler(giris, a, yon, stop_k, hedef_k)   # TEK KAYNAK
        sonuc = "zaman_asimi"
        for j in range(i + 1, min(len(barlar), i + 1 + azami_bar)):
            y, d = barlar[j]["h"], barlar[j]["l"]
            if yon == "LONG":
                stop_vurdu, hedef_vurdu = d <= sev["stop"], y >= sev["hedef"]
            else:
                stop_vurdu, hedef_vurdu = y >= sev["stop"], d <= sev["hedef"]
            if stop_vurdu:
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
    kaz, kay = 1.0 + f * b, 1.0 - f * a
    if kaz <= 0.0 or kay <= 0.0:
        return float("-inf")
    return p_hedef * math.log(kaz) + (1.0 - p_hedef) * math.log(kay)


def geometri_sec(barlar, indeksler, yon, atr_serisi, p_yon, cost_r_fn,
                 lam=1.0, azami_bar=32):
    """E[log] maksimize eden (stop_k, hedef_k). SECIM YANLILIGI KORKULUGU:
    11 aday AYNI orneklem uzerinde yarisir; nokta tahmini uzerinden argmax
    gurultuyu kenar sanir. Bu yuzden secim ve stake p_hedef'in NOKTA
    tahmininden degil WILSON ALT SINIRINDAN uretilir - az ornekli aday
    KENDILIGINDEN cezalanir, ayri bir n-cezasi sabiti UYDURULMAZ."""
    en_iyi, denenen = None, []
    for stop_k, hedef_k in IZGARA:
        olcum = ilk_gecis_olcum(barlar, indeksler, yon, stop_k, hedef_k,
                                atr_serisi, azami_bar)
        R = hedef_k / stop_k
        cost_r = float(cost_r_fn(stop_k))
        b, a = net_kanatlar(R, cost_r)
        if olcum["n"] < ASGARI_OLCUM or olcum["p_hedef"] is None or b <= 0:
            denenen.append({"stop_k": stop_k, "hedef_k": hedef_k, "elog": None,
                            "n": olcum["n"], "not": "OLCUM YOK" if b > 0
                            else "kazanc kanadi <= 0 (maliyet R'yi yiyor)"})
            continue
        p_alt, _ = wilson_araligi(int(round(olcum["p_hedef"] * olcum["n"])), olcum["n"])
        p_bil = math.sqrt(max(0.0, p_yon) * max(0.0, olcum["p_hedef"]))
        p_bil_alt = math.sqrt(max(0.0, p_yon) * max(0.0, p_alt))
        f = kelly_asimetrik(p_bil_alt, b, a) * lam
        aday = {"stop_k": stop_k, "hedef_k": hedef_k, "R": R, "cost_r": cost_r,
                "b": b, "a": a, "p_hedef": olcum["p_hedef"], "p_hedef_alt": p_alt,
                "p_bilesik": p_bil, "p_bilesik_alt": p_bil_alt, "n": olcum["n"],
                "f": f, "elog": beklenen_log(p_bil_alt, f, b, a),
                "basabas_p": basabas_p(b, a), "not": ""}
        denenen.append(aday)
        if en_iyi is None or aday["elog"] > en_iyi["elog"]:
            en_iyi = aday
    if en_iyi is None:
        v = IZGARA[5]
        return {"stop_k": v[0], "hedef_k": v[1], "R": v[1] / v[0],
                "p_hedef": None, "p_hedef_alt": None, "p_bilesik": None,
                "p_bilesik_alt": None, "n": 0, "f": 0.0, "elog": None,
                "cost_r": None, "b": None, "a": None, "basabas_p": None,
                "denenen": denenen,
                "not": "OLCUM YOK - yeterli ilk-gecis ornegi yok (fail-closed)"}
    # KOPYA sart: en_iyi zaten denenen'in bir ELEMANI; dogrudan atama kendine
    # referans yaratir ve karar JSON'a SERILESEMEZ.
    en_iyi = dict(en_iyi)
    en_iyi["denenen"] = denenen
    if en_iyi["elog"] <= 0.0:
        en_iyi["f"] = 0.0
        en_iyi["not"] = "E[log] <= 0 - hicbir geometri pozitif buyume vermiyor"
    return en_iyi


# ============================================================ BOLUM 14
# DECODING — HOLD YOK.

def decode(p_long):
    """argmax. Beraberlikte LONG (tanimli ve deterministik).
    Sozluk V = {LONG, SHORT}. Ucuncu bir eleman YOKTUR ve eklenemez."""
    return "LONG" if float(p_long) >= 0.5 else "SHORT"


def etiket_uret(barlar, i, atr_serisi, ufuk=None):
    """Iki sinifli etiket: LONG(1) = hedef once vuruldu. Ayni barda ikisi = STOP."""
    u = ETIKET_UFKU if ufuk is None else ufuk
    o = ilk_gecis_olcum(barlar, [i], "LONG", 1.0, 1.0, atr_serisi, u)
    if o["p_hedef"] is None:
        return None
    return 1 if o["hedef"] > 0 else 0


# ============================================================ BOLUM 15
# Veri adaptorleri ve paket kurucu. Yalniz public GET. Ag cagrisi ENJEKTE
# edilir (getir_fn) -> agsiz test edilebilir. Erisilemeyen kanal None kalir.

KANALLAR = ("kline_15m", "kline_4h", "oi", "funding", "taker", "derinlik")
# Tek ANLIK deger donduren kanallar SERIYE CEVRILMEZ (BIRLESTIRME bozulmasi).
ANLIK_KANALLAR = ("funding", "derinlik")

_KLINE_ALANLARI = (("KLINE_ACILIS_ZAMANI", 0), ("KLINE_ACILIS", 1),
                   ("KLINE_YUKSEK", 2), ("KLINE_DUSUK", 3),
                   ("KLINE_KAPANIS", 4), ("KLINE_HACIM", 5),
                   ("KLINE_TAKER_ALIS", 9))
for _ad, _i in _KLINE_ALANLARI:
    globals()[_ad] = esik_kaydet(
        _ad, _i, "YAPISAL",
        "Binance USD-M kline satirindaki alan indeksi (12 alanli liste). "
        "Borsa dokumantasyonundan gelir; yanlis indeks sessiz veri bozulmasi.")
del _ad, _i


class Adaptor:
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
                          {"symbol": sembol, "interval": "15m", "limit": "1500"}),
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

    def _inst(self, s):
        return s.replace("USDT", "-USDT-SWAP")

    def uc(self, kanal, sembol):
        # NOT: OKX resmi SDK'sinda parametre adi "period"tur, "periodic" DEGIL.
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


def _kline_cevir(satirlar):
    barlar = []
    for s in satirlar or []:
        barlar.append({"t": int(s[KLINE_ACILIS_ZAMANI]),
                       "o": float(s[KLINE_ACILIS]), "h": float(s[KLINE_YUKSEK]),
                       "l": float(s[KLINE_DUSUK]), "c": float(s[KLINE_KAPANIS]),
                       "v": float(s[KLINE_HACIM]),
                       "taker_alis": float(s[KLINE_TAKER_ALIS])})
    barlar.sort(key=lambda b: b["t"])
    return barlar


BAYATLIK_TAVANI = esik_kaydet(
    "BAYATLIK_TAVANI", 4, "VARSAYIM",
    "Hizalanan kaydin kac ADIM eski olabilecegi. Kalibre EDILMEDI. Bunun "
    "UZERINDE bir kayit ILERI DOLDURMA olur: bosluk boyunca eski deger "
    "tasinir ve model onu TAZE saniverir - olculdugu gibi bu FAIL-OPEN'dir "
    "(bozuk kanalda onarim guveni 1.0 cikiyordu).",
    "bayatlik yasina karsi ozniteligin hedefle korelasyonunun dustugu nokta")


def _hizala_geriye(seri, barlar, adim_ms=900000, bayatlik_tavani=None):
    """Onarilmis (zaman, deger) serisini 15M bar indeksine hizalar.

    GECMISE dogru: her bar icin zamani <= bar acilisi olan SON kayit.
    Ileri doldurma YOK (look-ahead yok) - AMA bayatlik SINIRLIDIR: kayit
    BAYATLIK_TAVANI adimdan eskiyse deger KULLANILMAZ (None) ve yas
    raporlanir. Aksi halde bir bosluk boyunca eski deger tasinir ve
    onarim guveni sahte olarak 1.0 cikar.

    Doner: [(deger|None, yas_adim|None), ...]
    """
    tavan = BAYATLIK_TAVANI if bayatlik_tavani is None else int(bayatlik_tavani)
    if not seri:
        return [(None, None)] * len(barlar)
    s = sorted(seri, key=lambda p: p[0])
    cikti, j, son_t, son_v = [], 0, None, None
    for b in barlar:
        while j < len(s) and s[j][0] <= b["t"]:
            son_t, son_v = s[j][0], s[j][1]
            j += 1
        if son_v is None:
            cikti.append((None, None))
            continue
        yas = int((b["t"] - son_t) // max(1, adim_ms))
        cikti.append((son_v, yas) if yas <= tavan else (None, yas))
    return cikti


def _bayatlik_guveni(yas, tavan=None):
    """Yas ile azalan guven. yas=0 -> 1.0, yas=tavan -> 1/e civari."""
    tavan = BAYATLIK_TAVANI if tavan is None else int(tavan)
    if yas is None:
        return 0.0
    # KIRPMA ZORUNLU: yas negatif olursa (kayit bardan YENI) us pozitife
    # doner ve carpan 1.0'i ASAR -> riski BUYUTUR (fail-open). Bugunku cagri
    # yolunda yas >= 0, ama korumasiz bir fonksiyon gelecekteki bir cagirana
    # acik kapi birakir. Olculdu: yas=-1 -> 1.2840, yas=-2 -> 1.6487.
    return min(1.0, math.exp(-max(0.0, float(yas)) / max(1.0, float(tavan))))


def turev_serisi_kur(barlar15, kanallar, adim_ms=900000):
    """Turev kanallarini ONARIP bar basina sozluk serisine cevirir.

    CVD kullanicinin KENDI kline'indan cevrimdisi hesaplanir:
      delta = 2*taker_alis - hacim   (12 alanli Binance kline'inin 9. alani)
    Bu kanal HER BARDA doludur, o yuzden onarim gerektirmez.
    """
    rapor = {}
    oi_ham = kanallar.get("oi")
    tk_ham = kanallar.get("taker")

    oi_onarim = kanal_onar(oi_ham or [], adim_ms, "sumOpenInterest")
    tk_onarim = kanal_onar(tk_ham or [], adim_ms, "buySellRatio")
    rapor["oi"] = {"beceri": oi_onarim["beceri"], "sayim": oi_onarim["rapor"]["sayim"],
                   "ortalama_guven": oi_onarim["ortalama_guven"],
                   "kayit": len(oi_onarim["seri"])}
    rapor["taker"] = {"beceri": tk_onarim["beceri"], "sayim": tk_onarim["rapor"]["sayim"],
                      "ortalama_guven": tk_onarim["ortalama_guven"],
                      "kayit": len(tk_onarim["seri"])}
    for ad in ANLIK_KANALLAR:
        if kanallar.get(ad) is not None:
            rapor[ad] = birlestirme_tespit(1, len(barlar15), ad)

    oi_hiz = _hizala_geriye(oi_onarim["seri"], barlar15, adim_ms)
    tk_hiz = _hizala_geriye(tk_onarim["seri"], barlar15, adim_ms)
    oi_gh = _hizala_geriye(list(zip([t for t, _ in oi_onarim["seri"]],
                                    oi_onarim["guven_serisi"])), barlar15, adim_ms)
    tk_gh = _hizala_geriye(list(zip([t for t, _ in tk_onarim["seri"]],
                                    tk_onarim["guven_serisi"])), barlar15, adim_ms)

    # BEKLENEN turev kanallari: hepsi guven hesabina girer. Bir kanal HIC
    # gelmediyse ya da bayatladiysa katkisi 0'dir - atlanmaz. Atlamak,
    # olculen fail-open'in ta kendisiydi.
    beklenen = []
    if oi_ham is not None:
        beklenen.append("oi")
    if tk_ham is not None:
        beklenen.append("taker")

    # KANAL OLCEGI: her turev ozniteligi kendi ROBUST sigmasina bolunur.
    # Sabit bir "x5" carpani YOKTUR - o carpan cift-kirp doygunlugunun
    # kaynagiydi. Sigma kanalin HAM serisinden gelir (FIR: gelecege bakmaz);
    # olculemezse oznitelik URETILMEZ (uydurma yasagi).
    def _kanal_olcegi(seri_deger):
        d = [seri_deger[j] - seri_deger[j - 1] for j in range(1, len(seri_deger))]
        sg = mad_sigma(d) if len(d) >= 2 else 0.0
        return sg if sg > SABIT_TOLERANSI else None

    oi_ham_deger = [v for _, v in oi_onarim["seri"]]
    tk_ham_deger = [v for _, v in tk_onarim["seri"]]
    olcek = {
        "oi_degisim": _kanal_olcegi([100.0 * (oi_ham_deger[j] / oi_ham_deger[j - 1] - 1.0)
                                     for j in range(1, len(oi_ham_deger))
                                     if oi_ham_deger[j - 1]]) if len(oi_ham_deger) > 2 else None,
        "taker_dengesi": _kanal_olcegi([v - 1.0 for v in tk_ham_deger])
        if len(tk_ham_deger) > 2 else None,
    }
    rapor["_olcek"] = dict(olcek)

    seri, onarim_izi = [], []
    for i, bar in enumerate(barlar15):
        k = {}
        oi_v, oi_y = oi_hiz[i]
        oi_v0 = oi_hiz[i - 1][0] if i > 0 else None
        if oi_v is not None and oi_v0:
            # KIRPMA YOK. Olculdu: uretimde kirp(D%) + oznitelikte kirp(x*5)
            # cift kirp demektir ve %0.20 UZERINDE buyukluk bilgisini tamamen
            # yok eder (0.20->1.00, 0.60->1.00, 2.00->1.00). Olceklendirme
            # TEK yerde ve kanalin KENDI robust sigmasiyla yapilir.
            k["oi_degisim"] = (oi_v - oi_v0) / oi_v0 * 100.0
        tk_v, tk_y = tk_hiz[i]
        if tk_v is not None:
            k["taker_dengesi"] = tk_v - 1.0
        hacim = bar["v"] or EPSILON
        k["cvd"] = kirp((2.0 * bar["taker_alis"] - hacim) / hacim)
        seri.append(k if k else None)

        # Guven = onarim guveni x bayatlik guveni, kanal basina; eksik kanal 0.
        katkilar = []
        if "oi" in beklenen:
            g = (oi_gh[i][0] or 0.0) if oi_v is not None else 0.0
            katkilar.append(g * _bayatlik_guveni(oi_y))
        if "taker" in beklenen:
            g = (tk_gh[i][0] or 0.0) if tk_v is not None else 0.0
            katkilar.append(g * _bayatlik_guveni(tk_y))
        katkilar.append(1.0)          # cvd: kullanicinin KENDI kline'indan, tam
        kullanilabilir = sum(1 for x in (oi_v, tk_v) if x is not None)
        onarim_izi.append({
            # "guven" YALNIZ STAKE eksenine gider - modele GIRMEZ.
            # Olculdu: surekli onarim guveni modele oznitelik olarak
            # verildiginde p_long'u degistiriyor ve YONU CEVIRIYOR
            # (guven 1.0 -> SHORT, guven 0.0 -> LONG). Onarim guveni bizim
            # KESTIRICIMIZIN kalitesidir, piyasa hakkinda bir olgu DEGILDIR;
            # yonu belirlememelidir.
            "guven": ortalama(katkilar) if katkilar else 0.0,
            # Modele giden: GOZLEM MASKESI (kanal basina ayri bit). Bu bir
            # OLGUDUR - "bu barda borsa OI yayinladi mi" - ve piyasayla
            # ilgilidir (or. oynaklikta kesinti). Kanal basina AYRI tutulur;
            # tek skalere ezilirse model hangi kanalin eksik oldugunu
            # ayirt edemez.
            "m_oi": 1.0 if oi_v is not None else 0.0,
            "m_taker": 1.0 if tk_v is not None else 0.0,
            "yogunluk": (1.0 - kullanilabilir / float(len(beklenen))
                         if beklenen else 1.0),
        })
    return seri, onarim_izi, rapor


def paket_kur(sembol, toplama, **ek):
    """Ham borsa JSON'u ile boru hatti arasindaki TEK kopru.

    KAPSAM DURUSTLUGU: yalniz SERI olarak modele ULASAN kanallar dolu sayilir.
    Anlik kanallar (funding, derinlik) sayilmaz ve ayrica BEYAN edilir -
    modele ulasmayan veri stake'i buyutemez.
    """
    kanallar = toplama.get("kanallar") or {}
    barlar15 = _kline_cevir(kanallar.get("kline_15m"))
    if not barlar15:
        raise ValueError("kline_15m YOK - uydurma bar uretilmez (fail-closed)")
    barlar4h = _kline_cevir(kanallar.get("kline_4h")) or None
    turev, onarim_izi, onarim_raporu = turev_serisi_kur(barlar15, kanallar)

    seri_kanallar = [k for k in KANALLAR
                     if k not in ANLIK_KANALLAR and kanallar.get(k) is not None]
    anlik = sorted(k for k in ANLIK_KANALLAR if kanallar.get(k) is not None)
    paket = {"sembol": sembol, "barlar15": barlar15, "barlar4h": barlar4h,
             "turev_serisi": turev, "onarim_izi": onarim_izi,
             "onarim_raporu": onarim_raporu,
             "dolu_kanal": len(seri_kanallar), "toplam_kanal": len(KANALLAR),
             "anlik_kanallar": anlik, "adaptor": toplama.get("adaptor")}
    paket.update(ek)
    return paket


def veri_topla(sembol, adaptorler, getir_fn):
    """TUM adaptorleri dener, EN YUKSEK kapsamli olani secer. Esitlikte ILK."""
    en_iyi = None
    for sira, ad in enumerate(adaptorler):
        kanallar, dusen = {}, []
        for kanal in KANALLAR:
            url, params = ad.uc(kanal, sembol)
            try:
                kanallar[kanal] = getir_fn(url, params)
            except Exception:
                kanallar[kanal] = None       # UYDURMA YOK
                dusen.append(kanal)
        kapsam = sum(1 for v in kanallar.values() if v is not None) / len(KANALLAR)
        aday = {"adaptor": ad.ad, "kanallar": kanallar, "kapsam": kapsam,
                "dusen": dusen, "yedege_dusuldu": sira > 0}
        if kapsam >= 1.0:
            return aday
        if en_iyi is None or kapsam > en_iyi["kapsam"]:
            en_iyi = aday
    if en_iyi is not None and en_iyi["kapsam"] > 0.0:
        return en_iyi
    return {"adaptor": None, "kanallar": dict((k, None) for k in KANALLAR),
            "kapsam": 0.0, "dusen": list(KANALLAR), "yedege_dusuldu": True}


# ============================================================ BOLUM 16
# BORU HATTI — 13 halka. Halka 0 GURULTULU KANAL ONARIMIDIR (yeni).

def _h4_hizala(n15, n4h):
    """Her 15M bar indeksi icin SON KAPANMIS 4H bar indeksi.

    LOOK-AHEAD YASAGI: 4H bar k, 15M barlarini [16k, 16k+15] araliginda
    KAPSAR ve ancak 16k+15'te KAPANIR. Bu yuzden 15M bar i, k=i//16 barini
    GOREMEZ. Dogru esleme: (i+1)//16 - 1, 0'a kirpilmis.
    """
    return [min(max(0, (i + 1) // H4_BAR_ORANI - 1), n4h - 1) for i in range(n15)]


def _ornek_indeksleri(baslangic, bitis, azami):
    a = list(range(baslangic, bitis))
    if len(a) <= azami:
        return a
    if azami <= 1:
        return a[-1:]
    adim = (len(a) - 1) / (azami - 1)
    return [a[round(k * adim)] for k in range(azami)]


class BoruHatti:
    """LLM zincirinin 13 halkasi. Halka 0 = gurultulu kanal onarimi."""

    def __init__(self, tohum=2026, boyut=16):
        self.tohum = tohum
        self.boyut = boyut
        self.kodlayici = Kodlayici(boyut=boyut, bas_sayisi=2, tohum=tohum)
        self.aile_gomme = dict((a, vektor(boyut, (tohum, "aile", a), 0.06))
                               for a in AILELER)
        self.zd_gomme = dict((z, vektor(boyut, (tohum, "zd", z), 0.06))
                             for z in ZAMAN_DILIMLERI)
        # SABIT RASTGELE IZDUSUM - OGRENILMEZ (bilincli, beyanli sapma):
        # izdusum boyut*sum(AILELER) parametre tasir; egitim dilimi ~100 ornek.
        # Bu orneklemde bu kadar parametre egitmek asiri-uyumdur. Halka OLU
        # DEGIL (izdusum degisince karar degisir), yalniz OGRENILMEZ.
        self.giris_izdusumu = dict((a, matris(boyut, AILELER[a],
                                              (tohum, "izdusum", a), 0.10))
                                   for a in AILELER)

    def _durumlar(self, satir_kumesi, olcekleyiciler, indeks, eksen=0):
        durumlar = []
        for gecikme in range(GECIKME_SAYISI - 1, -1, -1):
            j = max(0, indeks - gecikme)
            for zd in sorted(satir_kumesi):
                satirlar = satir_kumesi[zd]
                olc = olcekleyiciler[zd]
                for aile in AILELER:
                    olcekli = olc.donustur(aile, satirlar[j][aile])
                    icerik = matvec(self.giris_izdusumu[aile], olcekli)
                    kimlik = sabit_kimlik("S", zd, aile, gecikme)
                    tg = vektor(self.boyut, (self.tohum, "token", kimlik), 0.05)
                    durumlar.append(topla_vek(
                        icerik, tg, self.aile_gomme[aile], self.zd_gomme[zd],
                        zaman_konumu(gecikme, self.boyut),
                        eksen_konumu(eksen, self.boyut)))
        return durumlar

    # ---- halkalar ----
    def _h0_onarim(self, paket, iz):
        r = paket.get("onarim_raporu") or {}
        izi = paket.get("onarim_izi") or []
        guvenler = [x.get("guven", 0.0) for x in izi] or [0.0]
        # Kanal onarim guveni: geometrik ortalama (bir kanal cokerse toplam
        # guven de coker - aritmetik ortalama bunu maskelerdi).
        pozitif = [max(g, 1e-6) for g in guvenler]
        gm = math.exp(sum(math.log(g) for g in pozitif) / len(pozitif))
        iz["halka_0"] = {"ad": "gurultulu kanal onarimi",
                         "kanal_raporu": r,
                         "onarim_guveni_gm": gm,
                         "en_zayif_bar_guveni": min(guvenler),
                         "bar_sayisi": len(paket["barlar15"]),
                         "dolu_kanal": paket["dolu_kanal"],
                         "toplam_kanal": paket["toplam_kanal"],
                         "anlik_kanallar": paket.get("anlik_kanallar")}
        return gm

    def _h1_profil(self, paket, iz):
        n = len(paket["barlar15"])
        h4_var = bool(paket.get("barlar4h"))
        sec = profil_sec(n, h4_var=h4_var)
        iz["halka_1"] = {"ad": "butce-uyumlu gosterge profili",
                         "profil": sec["profil"]["ad"], "pencereler": sec["profil"],
                         "purge": sec["purge"], "gereken_bar": sec["gereken_bar"],
                         "eldeki_bar": n, "kaynak": sec["kaynak"],
                         "denenen": sec["denenen"], "not": sec["not"]}
        return sec

    def _h2_tokenler(self, paket, sec, iz):
        barlar = paket["barlar15"]
        profil = sec["profil"]
        gost = gostergeler_kur(barlar, profil)
        turev = paket.get("turev_serisi")
        onarim = paket.get("onarim_izi")
        satir_kumesi = {"15m": [satir_uret(barlar, gost, turev, onarim, profil, i)
                                for i in range(len(barlar))]}
        barlar4h = paket.get("barlar4h")
        h4_var = bool(barlar4h)
        if h4_var:
            h4p = sec.get("h4_profil") or profil
            g4 = gostergeler_kur(barlar4h, h4p)
            s4 = [satir_uret(barlar4h, g4, None, None, h4p, i)
                  for i in range(len(barlar4h))]
            esl = _h4_hizala(len(barlar), len(barlar4h))
            satir_kumesi["4h"] = [s4[esl[i]] for i in range(len(barlar))]
        # 4H YOKSA notr satir ENJEKTE EDILMEZ ve 15M KOPYALANMAZ; o zaman
        # dilimi icin token HIC uretilmez, bedeli kapsam dususudur.
        etkin = [z for z in ZAMAN_DILIMLERI if z in satir_kumesi]
        iz["halka_2"] = {"ad": "tokenizasyon", "aile_sayisi": len(AILELER),
                         "gecikme": GECIKME_SAYISI, "zaman_dilimi": etkin,
                         "h4_var": h4_var,
                         "token_sayisi": GECIKME_SAYISI * len(AILELER) * len(etkin)}
        return {"barlar": barlar, "gost": gost, "satir_kumesi": satir_kumesi,
                "h4_var": h4_var, "profil": profil, "sec": sec}

    def _h3_bolme(self, ctx, paket, iz):
        barlar, sec = ctx["barlar"], ctx["sec"]
        isinma = max(sec["profil"]["yuvarlanan"], ONARIM_PENCERESI) + 4
        bitis = len(barlar) - ETIKET_UFKU - 1
        azami = paket.get("azami_ornek") or max(1, bitis - isinma)
        tum = _ornek_indeksleri(isinma, max(isinma + 1, bitis), azami)
        erisim = girdi_erisimi(sec["profil"], ctx["h4_var"], sec.get("h4_profil"))
        bolme = kronolojik_bol(tum, ETIKET_UFKU, EMBARGO, giris_erisimi=erisim)
        bos = not (bolme["train"] and bolme["kalibrasyon"] and bolme["test"])
        iz["halka_3"] = {"ad": "purge/embargo/bolme",
                         "train": len(bolme["train"]),
                         "kalibrasyon": len(bolme["kalibrasyon"]),
                         "test": len(bolme["test"]), "atilan": bolme["atilan"],
                         "giris_erisimi": erisim, "bosluk": bolme["bosluk"],
                         "isinma": isinma,
                         # Bos bolmede "sizinti: False" demek fail-OPEN rapordur.
                         "sizinti": (None if bos else
                                     sizinti_var_mi(bolme, ETIKET_UFKU, erisim)),
                         "not": bolme["not"] or ("bolme dejenere" if bos else "")}
        iz["halka_3"]["gereken_azami_ornek"] = gereken_ornek_butcesi(
            max(1, tum[-1] - tum[0]) if len(tum) > 1 else 1,
            bolme["bosluk"], BOLME_ORANLARI[1], 2 * ASGARI_OLCUM)
        ctx["bolme"] = bolme
        ctx["tum_indeksler"] = tum

    def _h4_olcek(self, ctx, iz):
        bolme, barlar = ctx["bolme"], ctx["barlar"]
        kesim = bolme["train"][-1] if bolme["train"] else max(1, len(barlar) // 2)
        olc = {}
        for zd in ctx["satir_kumesi"]:
            o = Olcekleyici()
            o.fit(ctx["satir_kumesi"][zd], kesim)
            olc[zd] = o
        iz["halka_4"] = {"ad": "embedding/olcekleme", "kesim": kesim,
                         "sabit_kolon": dict((z, len(olc[z].sabit_kolonlar))
                                             for z in olc)}
        iz["halka_5"] = {"ad": "konum kodu", "zaman_ekseni": True,
                         "eksen_faz": SEMBOL_EKSENI_FAZI}
        iz["halka_6"] = {"ad": "nedensel dikkat",
                         "bas": self.kodlayici.bas_sayisi, "maske": True}
        iz["halka_7"] = {"ad": "FFN", "genislik": self.boyut * 2}
        ctx["olcekleyiciler"] = olc

    def _ornek(self, ctx, i):
        x = self.kodlayici.ileri(
            self._durumlar(ctx["satir_kumesi"], ctx["olcekleyiciler"], i))
        y = etiket_uret(ctx["barlar"], i, ctx["gost"]["atr"])
        return None if y is None else {"x": x, "y": y}

    def _h8_egitim(self, ctx, iz):
        b = ctx["bolme"]
        train = [o for o in (self._ornek(ctx, i) for i in b["train"]) if o]
        kal = [o for o in (self._ornek(ctx, i) for i in b["kalibrasyon"]) if o]
        test = [o for o in (self._ornek(ctx, i) for i in b["test"]) if o]
        basliklar = []
        for g in range(3):
            bs = Baslik(boyut=self.boyut, tohum=self.tohum + 100 * (g + 1))
            if train:
                alt = [train[k] for k in range(g, len(train), 3)] or train
                bs.egit(alt, devir=40, hiz=0.15)
            basliklar.append(bs)
        iz["halka_8"] = {"ad": "logit basligi", "train_ornek": len(train),
                         "gorus": len(basliklar)}
        kalib = kalibrasyon_sec(kal, basliklar) if kal else {
            "yontem": "YOK", "T": 1.0, "fn": None, "nll": None,
            "sinirda": False, "yarisma": "YOK"}
        gereken = iz.get("halka_3", {}).get("gereken_azami_ornek")
        if str(kalib.get("yarisma", "")).startswith("YAPILMADI"):
            kalib["yarisma"] += (" | gereken azami_ornek: %s" % gereken
                                 if gereken else
                                 " | bu veri ACIKLIGINDA hicbir butce yetmez")
        iz["halka_9"] = {"ad": "sicaklik kalibrasyonu", "yontem": kalib["yontem"],
                         "T": kalib["T"], "nll": kalib["nll"],
                         "sinirda": kalib["sinirda"],
                         "yarisma": kalib.get("yarisma", "YOK")}
        ctx.update({"train": train, "test": test, "basliklar": basliklar,
                    "kalib": kalib})

    def _h10_degerlendirme(self, ctx, iz):
        bs, kal = ctx["basliklar"], ctx["kalib"]
        ciftler = []
        for o in ctx["test"]:
            p = long_olasiligi(topluluk_olasilik(o["x"], bs, kal["T"])["p"])
            if kal["fn"] is not None:
                p = kal["fn"](p)
            ciftler.append((p, o["y"]))
        dogru = sum(1 for p, y in ciftler if (1 if p >= 0.5 else 0) == y)
        poz = sum(1 for _, y in ciftler if y == 1)
        taban = (max(poz, len(ciftler) - poz) / len(ciftler)) if ciftler else 0.5
        duy = ece_duyarlilik(ciftler) if ciftler else {"tek_bine_cokme": True,
                                                       "dolu_kova": 0}
        iz["halka_10"] = {"ad": "softmax/degerlendirme", "test_ornek": len(ciftler),
                          "dogru": dogru, "taban_oran": taban,
                          "ece": ece(ciftler) if ciftler else None,
                          "mce": mce(ciftler) if ciftler else None,
                          "ece_tek_bin": duy["tek_bine_cokme"],
                          "dolu_kova": duy["dolu_kova"],
                          "brier": brier(ciftler) if ciftler else None,
                          "auroc": auroc(ciftler) if ciftler else None,
                          "wilson": wilson_araligi(dogru, len(ciftler))}
        ctx.update({"ciftler": ciftler, "dogru": dogru, "taban_oran": taban,
                    "ece_tek_bin": duy["tek_bine_cokme"]})

    def _h11_olasilik(self, ctx, iz):
        bs, kal = ctx["basliklar"], ctx["kalib"]
        son = len(ctx["barlar"]) - 1
        x = self.kodlayici.ileri(
            self._durumlar(ctx["satir_kumesi"], ctx["olcekleyiciler"], son))
        top = topluluk_olasilik(x, bs, kal["T"])
        p = long_olasiligi(top["p"])
        if kal["fn"] is not None:
            p = kal["fn"](p)
        egitildi = bool(ctx["train"])
        iz["halka_11"] = {"ad": "decoding (HOLD YOK)", "p_long": p,
                          "hold": False, "egitildi": egitildi,
                          "uzlasi": top["uzlasi"], "dagilim": top["dagilim"]}
        ctx["p_ham"] = p
        ctx["egitildi"] = egitildi
        ctx["son"] = son


# ============================================================ BOLUM 17
# YAPISAL TABAN YON — "HOLD YOK" sartinin durust karsiligi.
#
# Model egitilemediyse (bolme dejenere) v3 "VERI YOK" diyordu; bu UCUNCU BIR
# SINIFTIR ve kullanicinin sarti bunu yasakliyor. Ama egitilmemis bir agin
# p'sini yon diye sunmak da UYDURMADIR (o bir tohum artefaktidir).
#
# Cozum: yon DAIMA uretilir, fakat egitilmemis durumda OLCULEN bir yapisal
# skordan gelir - rastgele baslangictan degil. Kaynak ACIKCA etiketlenir.
# Bu, LLM'in bozuk cumlede yaptigi seyin aynisidir: sozluk bulunamazsa bile
# en yakin adayi secer, ama guveni dusuk raporlar.

def yapisal_yon_skoru(barlar, gost, profil, i=None):
    """Olculen yapisal yon skoru -> P(LONG). Yalniz <= i veri okunur."""
    i = (len(barlar) - 1) if i is None else i
    if i < 2:
        return {"p_long": 0.5, "bilesenler": {}, "not": "bar yetersiz"}
    yuv = profil["yuvarlanan"]
    b = {}
    # 1) EMA egimi (trend)
    a = max(gost["atr"][i], EPSILON)
    b["ema_farki"] = kirp((gost["ema_hizli"][i] - gost["ema_yavas"][i]) / a)
    # 2) Kanal konumu (aralikta nerede)
    b["kanal"] = _kanal_konumu(barlar, i, yuv)
    # 3) Getiri isaret tutarliligi (son min(yuv, i) bar)
    p = max(2, min(yuv, i))
    kap = gost["kapanislar"]
    isaretler = [1 if kap[j] > kap[j - 1] else -1 for j in range(i - p + 1, i + 1)]
    b["tutarlilik"] = kirp(sum(isaretler) / float(len(isaretler)))
    # 4) RSI sapmasi
    b["rsi"] = kirp((gost["rsi"][i] - 50.0) / 50.0)
    skor = sum(b.values()) / len(b)
    # Lojistik: skor 0 -> 0.5. Egim 2.0 YAPISAL (skor zaten [-1,1]'e kirpili).
    p_long = 1.0 / (1.0 + math.exp(-2.0 * skor))
    return {"p_long": p_long, "skor": skor, "bilesenler": b,
            "not": "OLCULEN yapisal taban (model egitilmedi)"}


esik_kaydet("YAPISAL_LOJISTIK_EGIM", 2.0, "YAPISAL",
            "Yapisal skor [-1,1] araligina kirpili oldugundan egim 2.0, "
            "skor=+-1'de p=0.88/0.12 verir. Bir performans ayari DEGIL, "
            "kirpma araligindan gelen olcek.")


# ============================================================ BOLUM 18
# NIHAI KARAR — yon (zorunlu) + stake (surekli) + seviyeler.

LAMBDA_TABLOSU = (1.0, 0.5, 0.25)


def _basabas_referansi(geo):
    """`geo.get("basabas_p") or 0.5` YAZILAMAZ: geometri fail-closed donunce
    referans 0.5 olur ve bu, daraltma hedefinin yanlis olmasinin ta kendisidir;
    ayrica `or` mesru bir 0.0'i da EKSIK sayar."""
    if not isinstance(geo, dict):
        return None
    d = geo.get("basabas_p")
    return None if d is None else float(d)


def karar_uret(baglam):
    shr = shrinkage_katsayisi(
        baglam["dogru"], baglam["toplam"], baglam.get("ece_enkotu"),
        baglam["dolu_kanal"], baglam["toplam_kanal"],
        onarim_guveni=baglam.get("onarim_guveni", 1.0),
        taban_oran=baglam.get("taban_oran", 0.5),
        ece_tek_bin=baglam.get("ece_tek_bin", False),
        sicaklik_sinirda=baglam.get("sicaklik_sinirda", False))

    # YON kosulsuz ve DARALTILMAMIS olasiliktan gelir: shrinkage stake'i
    # sifirlar ama yon BILGISINI yok etmez.
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
    f_max = likidasyon_tavani(baglam["giris"], baglam.get("likidasyon"),
                              baglam.get("kaldirac_azami"),
                              LIKIDASYON_GUVENLIK_PAYI)
    b, a = geo.get("b"), geo.get("a")
    # OLAY UYUSMAZLIGI DUZELTMESI: Kelly'ye giren p, b/a'nin TANIMLANDIGI
    # olayin olasiligi olmalidir. p_yon ETIKET olayindan gelir (SIMETRIK
    # 1xATR bariyer, ETIKET_UFKU bar); b/a ise ASIMETRIK (stop_k, hedef_k)
    # bariyerinden ve azami_bar ufkundan. Iki FARKLI olay. Gecidin kendisi
    # zaten p_bilesik_alt = sqrt(p_yon * p_hedef_alt) hesapliyor ama bu deger
    # stake'e VERILMIYORDU - yani gecidi acan olasilik ile boyutlandiran
    # olasilik farkliydi.
    p_stake = geo.get("p_bilesik_alt")
    if p_stake is None:
        p_stake = p_yon
    lt = {}
    for lam in LAMBDA_TABLOSU:
        if b is None or a is None or geo["f"] <= 0.0:
            # SOZLESME: bu dal NORMAL dalla AYNI anahtarlari tasir. Aksi
            # halde tuketiciler yalniz mutlu yolda calisir ve fail-closed
            # dalda coker - yani guvenlik dali, cokme dali olur.
            lt[str(lam)] = {
                "f": 0.0, "kirpildi": False, "f_ham": 0.0,
                "f_max": f_max, "f_gecit": 0.0,
                "f_stake_ham": 0.0, "gecit_bagladi": False,
                # GEREKCE dalin KENDI kosulundan okunur - sonradan tahmin
                # EDILMEZ. Rapor "f*=0" derken NEDEN'i de tasimak zorunda.
                "not": ("geometri olcumu YOK (b/a uretilemedi)"
                        if (b is None or a is None)
                        else "gecidin f'i sifir - olculen ilk-gecis "
                             "bahsi desteklemiyor")}
            continue
        ham = stake_hesapla(p_stake, shr["s"], b, a, lam)
        # FAIL-CLOSED KORKULUK: stake, gecidin kendi f'ini ASAMAZ. Iki hesap
        # ayrisirsa kucuk olan gecerlidir ve oran ize yazilir.
        f_gecit = geo["f"] * max(0.0, float(lam))
        f_kirpik, gecit_bagladi = stake_gecit_kirp(ham["f"], f_gecit)
        lt[str(lam)] = stake_kirp(f_kirpik, f_max)
        lt[str(lam)]["f_gecit"] = f_gecit
        lt[str(lam)]["f_stake_ham"] = ham["f"]
        lt[str(lam)]["gecit_bagladi"] = gecit_bagladi
        lt[str(lam)]["not"] = ham["not"]
    secilen = lt[str(float(baglam.get("lam", 1.0)))]
    bref = _basabas_referansi(geo)
    return {
        "sembol": baglam["sembol"], "yon": yon,
        "yon_kaynagi": baglam.get("yon_kaynagi", "MODEL"),
        "p_ham": baglam["p_ham"],
        "p_kullanilan": (None if bref is None
                         else daralt(p_yon, shr["s"], hedef=bref)),
        "shrinkage": shr, "geometri": geo,
        "giris": sev["giris"], "stop": sev["stop"], "hedef": sev["hedef"],
        "R": sev["R"],
        "stake": {"f": secilen["f"], "kirpildi": secilen["kirpildi"],
                  "f_max": f_max, "lambda_tablosu": lt,
                  "not": secilen.get("not", ""),
                  "gecit_bagladi": secilen.get("gecit_bagladi", False),
                  "p_stake": p_stake, "p_yon": p_yon,
                  "olay_uyumu": ("GECIT_OLAYI" if geo.get("p_bilesik_alt")
                                 is not None else "ETIKET_OLAYI (gecit olcumu YOK)")},
    }


def _bh_karar(self, ctx, paket, iz):
    barlar, gost, son = ctx["barlar"], ctx["gost"], ctx["son"]
    egitildi = ctx["egitildi"]
    if egitildi:
        p_ham = ctx["p_ham"]
        kaynak = "MODEL"
        yapisal = None
    else:
        yapisal = yapisal_yon_skoru(barlar, gost, ctx["profil"], son)
        p_ham = yapisal["p_long"]
        kaynak = "YAPISAL_TABAN"
        iz["halka_11"]["p_long"] = p_ham
        iz["halka_11"]["yapisal_taban"] = yapisal
    grup = ({"test": ctx["ciftler"]} if ctx.get("ciftler") else None)
    ece_enkotu = None
    if grup:
        d = dict((k, ece(v)) for k, v in grup.items() if ece(v) is not None)
        ece_enkotu = max(d.values()) if d else None
    karar = karar_uret({
        "sembol": paket["sembol"], "barlar": barlar, "atr_serisi": gost["atr"],
        "indeksler": ctx["bolme"]["test"] or ctx["tum_indeksler"][-40:],
        "p_ham": p_ham, "yon_kaynagi": kaynak,
        "dogru": ctx.get("dogru", 0), "toplam": len(ctx.get("ciftler") or []),
        "ece_enkotu": ece_enkotu,
        "taban_oran": ctx.get("taban_oran", 0.5),
        "ece_tek_bin": ctx.get("ece_tek_bin", True),
        "sicaklik_sinirda": bool(iz.get("halka_9", {}).get("sinirda")),
        "onarim_guveni": ctx.get("onarim_guveni", 1.0),
        "dolu_kanal": ctx["dolu_kanal"], "toplam_kanal": paket["toplam_kanal"],
        "giris": barlar[son]["c"], "atr": gost["atr"][son],
        "likidasyon": paket.get("likidasyon"),
        "kaldirac_azami": paket.get("kaldirac_azami"),
        "komisyon": paket.get("komisyon", 0.0004),
        "kayma": paket.get("kayma", 0.0005),
        "funding": paket.get("funding", 0.0),
        "lam": paket.get("lam", 1.0)})
    iz["halka_12"] = {"ad": "detokenizasyon (seviyeler)",
                      "giris": karar["giris"], "stop": karar["stop"],
                      "hedef": karar["hedef"], "R": karar["R"],
                      "f": karar["stake"]["f"]}
    karar["iz"] = iz
    karar["kalibrasyon"] = iz["halka_10"]
    karar["adaptor"] = paket.get("adaptor")
    karar["egitildi"] = egitildi
    return karar


def _bh_kapsam(self, ctx, paket, iz):
    """KAPSAM h4_var'dan TURETILIR: modele ULASMAYAN veri kapsami BUYUTEMEZ."""
    dolu = paket["dolu_kanal"]
    if not ctx["h4_var"] and dolu > 0:
        dolu -= 1
        iz["halka_0"]["h4_kanali_dusuldu"] = True
    return dolu


def _bh_calistir(self, paket):
    """13 halka, sirayla. Halka 0 = gurultulu kanal onarimi (yeni)."""
    iz = {}
    onarim_gm = self._h0_onarim(paket, iz)
    sec = self._h1_profil(paket, iz)
    ctx = self._h2_tokenler(paket, sec, iz)
    ctx["onarim_guveni"] = onarim_gm
    self._h3_bolme(ctx, paket, iz)
    self._h4_olcek(ctx, iz)
    self._h8_egitim(ctx, iz)
    self._h10_degerlendirme(ctx, iz)
    self._h11_olasilik(ctx, iz)
    ctx["dolu_kanal"] = self._kapsam(ctx, paket, iz)
    return self._karar(ctx, paket, iz)


BoruHatti._karar = _bh_karar
BoruHatti._kapsam = _bh_kapsam
BoruHatti.calistir = _bh_calistir


# ============================================================ BOLUM 19
# CUMLE ONARIMI — mekanizmanin CALISAN gosterimi (trading ile AYNI matematik).

CUMLE_SOZLUGU = {
    "simdi": .90, "sana": .80, "bana": .85, "sen": .90, "sende": .50,
    "verdigim": .60, "verdigin": .55, "erdigim": .05, "eskisi": .60,
    "eskisin": .10, "yerinde": .70, "anladin": .70, "anladim": .60,
    "getir": .50, "gonderdigim": .40, "programi": .35, "gorevi": .30,
    "soru": .40, "gore": .50, "sorunu": .35, "yerine": .60, "gecti": .40,
}
CUMLE_MALIYETI = {"silme": 1.0, "ekleme": 1.0, "degistirme": 1.3,
                  "uzatma": 0.25, "birlestirme": 1.6}
ESDEGER = {("s", "b"): .6, ("s", "ş"): .2, ("i", "ı"): .15, ("k", "g"): .6,
           ("g", "ğ"): .15, ("m", "n"): .5, ("u", "ü"): .15, ("o", "ö"): .15,
           ("c", "ç"): .15, ("e", "a"): .7}


def _harf_yakinligi(a, b):
    if a == b:
        return 0.0
    return CUMLE_MALIYETI["degistirme"] * ESDEGER.get((a, b), ESDEGER.get((b, a), 1.0))


def cumle_kanal_maliyeti(gozlem, aday):
    """Tipli duzenleme mesafesi -> -log P(gozlem|aday).
    Bes bozulma modunun HEPSI burada: silme, ekleme, degistirme, uzatma."""
    n, m = len(gozlem), len(aday)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        D[i][0] = D[i - 1][0] + CUMLE_MALIYETI["ekleme"]
    for j in range(1, m + 1):
        D[0][j] = D[0][j - 1] + CUMLE_MALIYETI["silme"]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            en = min(D[i - 1][j] + CUMLE_MALIYETI["ekleme"],
                     D[i][j - 1] + CUMLE_MALIYETI["silme"],
                     D[i - 1][j - 1] + _harf_yakinligi(gozlem[i - 1], aday[j - 1]))
            if i > 1 and gozlem[i - 1] == gozlem[i - 2]:      # UZATMA
                en = min(en, D[i - 1][j] + CUMLE_MALIYETI["uzatma"])
            D[i][j] = en
    return D[n][m]


def cumle_adaylari(gozlem, k=5):
    """posterior ~ P(c) * P(o|c). HOLD YOK: daima en az bir aday doner."""
    p = [(c, math.log(o) - cumle_kanal_maliyeti(gozlem, c))
         for c, o in CUMLE_SOZLUGU.items()]
    p.sort(key=lambda t: -t[1])
    return p[:k]


def cumle_bolumle(gozlem):
    """BIRLESTIRME onarimi: tek gozlemi iki parcaya bolmeyi dene."""
    en = (None, -1e18)
    for i in range(3, max(4, len(gozlem) - 2)):
        a1 = cumle_adaylari(gozlem[:i], 1)
        a2 = cumle_adaylari(gozlem[i:], 1)
        if not a1 or not a2:
            continue
        p = a1[0][1] + a2[0][1] - CUMLE_MALIYETI["birlestirme"]
        if p > en[1]:
            en = ((a1[0][0], a2[0][0]), p)
    return en


def cumle_onar(cumle):
    onarilan, guvenler, satirlar = [], [], []
    for kelime in cumle.split():
        tek = cumle_adaylari(kelime, 5)
        bol = cumle_bolumle(kelime)
        if bol[0] and bol[1] > tek[0][1]:
            adlar = [" ".join(bol[0])] + [t[0] for t in tek]
            lp = [bol[1]] + [t[1] for t in tek]
        else:
            adlar = [t[0] for t in tek]
            lp = [t[1] for t in tek]
        p = kararli_softmax(lp)
        onarilan.append(adlar[0])
        guvenler.append(p[0])
        satirlar.append({"gozlem": kelime, "onarim": adlar[0], "posterior": p[0],
                         "marj": (p[0] - p[1]) if len(p) > 1 else 1.0,
                         "alternatifler": list(zip(adlar[1:4], p[1:4]))})
    pozitif = [max(g, 1e-9) for g in guvenler]
    gm = math.exp(sum(math.log(g) for g in pozitif) / len(pozitif))
    return {"onarilan": " ".join(onarilan), "satirlar": satirlar,
            "guven_gm": gm, "en_zayif": min(guvenler)}


ORNEK_CUMLE = "imdi sama erdikim pugoreeeewu eskisis yerinde geteranladinsen"


# ============================================================ BOLUM 20
# Cikti, kagit defteri, CLI. GERCEK EMIR YOK.

def bahis_acilir_mi(stake):
    """Stake'i okuyan HER tuketici bu yuklemden gecer. Ayni karar hakkinda
    defter 'pozisyon actim', rapor 'bahis sifir' diyemez."""
    return float((stake or {}).get("f") or 0.0) > 0.0


def _bicim(d, kalip=".4f"):
    """OLCULMEMIS deger 'VERI YOK' yazilir, 0.0000 DEGIL."""
    if d is None:
        return "VERI YOK"
    try:
        return format(d, kalip)
    except (TypeError, ValueError):
        return str(d)


KARAR_DESTEK_UYARISI = (
    "Yalniz karar-destek. Canli/otomatik emir (gercek para) DAHIL DEGILDIR; "
    "bu dosya bir emir dosyasi degil, bir olcum kaydidir.")


def metin_rapor(karar):
    g = karar.get("geometri") or {}
    s = karar.get("stake") or {}
    sh = karar.get("shrinkage") or {}
    iz = karar.get("iz") or {}
    h0 = iz.get("halka_0") or {}
    h1 = iz.get("halka_1") or {}
    h3 = iz.get("halka_3") or {}
    sat = [
        "=" * 78,
        "%s | %s | YALNIZ KARAR-DESTEK (gercek emir YOK)" % (karar["sembol"], SURUM),
        "-" * 78,
        "ONARIM   guven(gm)=%s  en_zayif_bar=%s  kanal=%s/%s  anlik(sayilmaz)=%s"
        % (_bicim(h0.get("onarim_guveni_gm")), _bicim(h0.get("en_zayif_bar_guveni")),
           h0.get("dolu_kanal"), h0.get("toplam_kanal"), h0.get("anlik_kanallar")),
    ]
    for kanal, r in (h0.get("kanal_raporu") or {}).items():
        if isinstance(r, dict) and "beceri" in r:
            b = r["beceri"]
            sat.append("   %-9s beceri=%s kestirici=%s  bozulma=%s"
                       % (kanal, _bicim(b.get("beceri")), b.get("kestirici"),
                          r.get("sayim")))
    sat += [
        "PROFIL   %s %s | purge=%s | eldeki_bar=%s | gereken_bar=%s"
        % (h1.get("profil"), h1.get("pencereler"), h1.get("purge"),
           h1.get("eldeki_bar"), h1.get("gereken_bar")),
        "BOLME    train=%s kal=%s test=%s | erisim=%s | bosluk=%s | sizinti=%s"
        % (h3.get("train"), h3.get("kalibrasyon"), h3.get("test"),
           h3.get("giris_erisimi"), h3.get("bosluk"), h3.get("sizinti")),
        "         gereken_azami_ornek=%s (kalibrasyon dilimi purge sonrasi "
        "bos kalmasin diye)" % h3.get("gereken_azami_ornek"),
        "-" * 78,
        "YON: %s   (kaynak=%s, p_ham=%s -> p_kullanilan=%s)"
        % (karar["yon"], karar.get("yon_kaynagi"), _bicim(karar.get("p_ham")),
           _bicim(karar.get("p_kullanilan"))),
        "SHRINKAGE s=%s  (kanit=%s kalibrasyon=%s kapsam=%s ONARIM=%s)"
        % (_bicim(sh.get("s"), ".6f"), _bicim(sh.get("s_kanit"), ".3f"),
           _bicim(sh.get("s_kalibrasyon"), ".3f"), _bicim(sh.get("s_kapsam"), ".3f"),
           _bicim(sh.get("s_onarim"), ".3f")),
        "GEOMETRI stop_k=%s hedef_k=%s R=%s p_hedef=%s n=%s"
        % (g.get("stop_k"), g.get("hedef_k"), _bicim(g.get("R")),
           _bicim(g.get("p_hedef")), g.get("n")),
        "basabas p (f*>0 icin gereken) = %s" % _bicim(g.get("basabas_p")),
        "SEVIYELER giris=%s stop=%s hedef=%s"
        % (_bicim(karar.get("giris"), ".8g"), _bicim(karar.get("stop"), ".8g"),
           _bicim(karar.get("hedef"), ".8g")),
        "STAKE f*=%s (f_max=%s, kirpildi=%s)"
        % (_bicim(s.get("f"), ".6f"), _bicim(s.get("f_max"), ".6f"),
           "EVET" if s.get("kirpildi") else "hayir"),
        "  lambda: " + ("  ".join("%s->%s" % (l, _bicim(v.get("f"), ".6f"))
                                  for l, v in s["lambda_tablosu"].items())
                        if s.get("lambda_tablosu") else "VERI YOK"),
    ]
    for kaynak in (g, s, karar, h1, h3):
        if isinstance(kaynak, dict) and kaynak.get("not"):
            sat.append("NOT: %s" % kaynak["not"])
    if not bahis_acilir_mi(s):
        sat.append("f*=0: YON ve SEVIYELER yine uretildi; bahis buyuklugu sifir.")
    sat.append(KARAR_DESTEK_UYARISI)
    return "\n".join(sat)


SONUC_BASLIGI = "SONUC (calistirmanin cevabi)"


def sonuc_satiri(karar, veri_kaynagi, paket=None):
    """Kosunun SONUCU: tek blok, IKI ayri hukum.

    (1) YON kosulsuz verilir (LONG/SHORT) - kararsizlik SINIFI yoktur;
        belirsizlik yon eksenine degil STAKE eksenine gider.
    (2) ISLEM KALITESI ayri hukumdur: bahis buyuklugu sifir olabilir ve
        GEREKCE motorun kendi notundan okunur (stake["not"]), sonradan
        tahmin EDILMEZ.
    Bu blok yeni bir sey HESAPLAMAZ; yalnizca karar sozlesmesinde ZATEN
    olan alanlari basar - aksi halde rapor, olctugunden baskasini soylerdi.
    """
    g = karar.get("geometri") or {}
    s = karar.get("stake") or {}
    h0 = ((karar.get("iz") or {}).get("halka_0")) or {}
    acilir = bahis_acilir_mi(s)
    gerekce = (s.get("not") or "").strip()
    if acilir and s.get("kirpildi"):
        gerekce = "likidasyon tavani f'i kirpti"
    elif acilir and s.get("gecit_bagladi"):
        gerekce = "gecit f'i bagladi (kucuk olan gecerli)"
    sat = ["=" * 78,
           "%s | %s | veri: %s" % (SONUC_BASLIGI, karar["sembol"], veri_kaynagi),
           "-" * 78]
    if paket is not None:
        sat.append("BAR        : %d x 15M + %d x 4H"
                   % (len(paket["barlar15"]), len(paket["barlar4h"] or [])))
    sat += [
        "YON        : %s  (kaynak=%s, p_ham=%s) - yon KOSULSUZ verilir"
        % (karar["yon"], karar.get("yon_kaynagi"), _bicim(karar.get("p_ham"))),
        "GIRIS      : %s" % _bicim(karar.get("giris"), ".8g"),
        "STOP       : %s" % _bicim(karar.get("stop"), ".8g"),
        "HEDEF      : %s" % _bicim(karar.get("hedef"), ".8g"),
        "R          : %s   (R = hedef_mesafesi / stop_mesafesi)"
        % _bicim(karar.get("R")),
        "basabas p  : %s | OLCULEN p_hedef: %s (n=%s)"
        % (_bicim(g.get("basabas_p")), _bicim(g.get("p_hedef")), g.get("n")),
        "ISLEM      : %s" % ("BAHIS ACILIR - f*=%s" % _bicim(s.get("f"), ".6f")
                             if acilir else "BAHIS ACILMAZ - f*=0"),
        "  gerekce  : %s" % (gerekce or "ek not YOK"),
        "ONARIM     : guven(gm)=%s | kanal %s/%s | anlik(sayilmaz)=%s"
        % (_bicim(h0.get("onarim_guveni_gm")), h0.get("dolu_kanal"),
           h0.get("toplam_kanal"), h0.get("anlik_kanallar")),
        "-" * 78,
        KARAR_DESTEK_UYARISI,
        "=" * 78]
    return "\n".join(sat)


def rapor_yaz(kararlar, dosya):
    """Deterministik JSON. Serilesmeyen alan varsa TypeError YUKSELIR ve dosya
    YAZILMAZ: yazilamayan sey 'yazildi' diye raporlanamaz (fail-closed)."""
    import json as _json
    govde = {"surum": SURUM, "uyari": KARAR_DESTEK_UYARISI,
             "kararlar": list(kararlar)}
    metin = _json.dumps(govde, sort_keys=True, indent=1, ensure_ascii=False,
                        default=lambda o: None if callable(o) else str(o))
    with open(str(dosya), "w", encoding="utf-8") as f:
        f.write(metin + "\n")


def defter_guncelle(durum, karar, bar):
    """Yerel kagit defteri. f*=0 ise pozisyon ACILMAZ.
    MALIYET DUSULUR: Kelly kayip kanadini a=1+cost_r fiyatlar; defter yalniz
    f'i dusseydi sicil, olctugu seyden BASKA bir seyi olcerdi."""
    yeni = {"sermaye": durum["sermaye"],
            "pozisyonlar": dict(durum.get("pozisyonlar", {}))}
    s = karar["sembol"]
    m = yeni["pozisyonlar"].get(s)
    if m:
        if m["yon"] == "LONG":
            cikis = (m["stop"] if bar["l"] <= m["stop"]
                     else (m["hedef"] if bar["h"] >= m["hedef"] else None))
        else:
            cikis = (m["stop"] if bar["h"] >= m["stop"]
                     else (m["hedef"] if bar["l"] <= m["hedef"] else None))
        if cikis is not None:
            isaret = 1.0 if m["yon"] == "LONG" else -1.0
            ham = isaret * (cikis - m["giris"]) * m["miktar"]
            maliyet = (m.get("cost_r", 0.0) * abs(m["giris"] - m["stop"]) * m["miktar"])
            yeni["sermaye"] += ham - maliyet
            yeni["pozisyonlar"].pop(s, None)
    if s not in yeni["pozisyonlar"] and bahis_acilir_mi(karar["stake"]):
        risk = yeni["sermaye"] * karar["stake"]["f"]
        mesafe = abs(karar["giris"] - karar["stop"]) or EPSILON
        yeni["pozisyonlar"][s] = {
            "yon": karar["yon"], "giris": karar["giris"], "stop": karar["stop"],
            "hedef": karar["hedef"], "miktar": risk / mesafe,
            "cost_r": float((karar.get("geometri") or {}).get("cost_r") or 0.0)}
    return yeni


# ==========================================================================
# BOLUM 21 — CANLI VERI KATMANI (public GET; imza/anahtar/emir ucu YOK)
# ==========================================================================

def http_getir(url, params, zaman_asimi=20):
    """Bu dosyadaki TEK ag cagrisi. Emir/iptal ucu, API anahtari, imza
    YOKTUR ve eklenmemelidir - modul bir EMIR sistemi degil, OLCUM sistemidir."""
    import json as _json
    import urllib.parse as _up
    import urllib.request as _ur
    tam = url + "?" + _up.urlencode(params)
    istek = _ur.Request(tam, headers={"User-Agent": SURUM})
    with _ur.urlopen(istek, timeout=zaman_asimi) as y:
        return _json.loads(y.read().decode("utf-8"))


def canli_kosu(sembol, getir_fn=None, tohum=2026, **ek):
    getir_fn = http_getir if getir_fn is None else getir_fn
    toplama = veri_topla(sembol, [BinanceAdaptor(), OkxAdaptor()], getir_fn)
    if toplama["adaptor"] is None:
        raise RuntimeError("hicbir adaptor veri veremedi (fail-closed)")
    paket = paket_kur(sembol, toplama, **ek)
    return BoruHatti(tohum=tohum).calistir(paket), paket, toplama


def _sahte_getir(url, params):
    """AGSIZ ornek veri. GERCEK VERI DEGILDIR. Bilerek BOZULMA icerir:
    OI'de bosluk + spike, taker'da son bar EKSIK - onarim katmani sinansin."""
    rng = tohumlu_rng("ornek", url, str(params.get("interval", "")))
    if "klines" in url:
        onbes = "15m" in str(params.get("interval"))
        n, adim = (2400, 900000) if onbes else (600, 14400000)
        satirlar, fiyat = [], 100.0
        for i in range(n):
            fiyat *= 1.0 + rng.uniform(-0.003, 0.0031)
            h = 100.0 + rng.uniform(0.0, 50.0)
            satirlar.append([i * adim, "%.8f" % fiyat, "%.8f" % (fiyat * 1.002),
                             "%.8f" % (fiyat * 0.998), "%.8f" % fiyat,
                             "%.8f" % h, i * adim + adim - 1, "0", 50,
                             "%.8f" % (h * (0.4 + rng.uniform(0.0, 0.2))),
                             "0", "0"])
        return satirlar
    if "openInterest" in url:
        kayit = []
        oi_x = 1000.0
        for i in range(2400):
            if 400 <= i < 410:            # BOSLUK (SILME modu)
                continue
            oi_x += rng.uniform(-3.0, 3.0)   # yavas suruklenen STOK (gercek OI gibi)
            v = oi_x
            if i == 800:                  # SPIKE (DEGISTIRME modu)
                v *= 1.9
            kayit.append({"sumOpenInterest": "%.4f" % v, "timestamp": i * 900000})
        return kayit
    if "takerlongshort" in url:
        # SON BAR EKSIK (gercek veride olculdu: taker son 15M barda YOK)
        return [{"buySellRatio": "%.4f" % (1.0 + rng.uniform(-0.2, 0.2)),
                 "timestamp": i * 900000} for i in range(2399)]
    if "premiumIndex" in url:
        return {"lastFundingRate": "0.0001"}
    if "depth" in url:
        return {"bids": [["100.0", "5.0"]], "asks": [["100.1", "3.0"]]}
    raise RuntimeError("bilinmeyen uc: " + url)


_TEST_BOLUMU_SINIRI = "# BOLUM 22 - TEST PAKETI"


def _modul_kaynagi():
    """Bu dosyanin YALNIZ motor bolumu (test bolumu HARIC).
    Tek dosyada kaynak tarayan testler kendi metinlerini de gorurdu."""
    import pathlib as _pl
    metin = _pl.Path(__file__).read_text(encoding="utf-8")
    k = metin.find(_TEST_BOLUMU_SINIRI)
    return metin if k < 0 else metin[:k]


def _kosu_bas(sembol, getir_fn, baslik, veri_kaynagi):
    """Bir kosu basar ve DAIMA SONUC blogu ile biter.
    Hangi moddan girilirse girilsin cikti ayni sozlesmeyi tasir:
    once kanit (metin_rapor), en sonda hukum (sonuc_satiri)."""
    karar, paket, toplama = canli_kosu(sembol, getir_fn=getir_fn)
    print("=" * 78)
    print(baslik)
    print("adaptor    :", toplama["adaptor"], "| ham kapsam:", round(toplama["kapsam"], 4))
    print("seri kanal :", paket["dolu_kanal"], "/", paket["toplam_kanal"],
          "| anlik (kapsama SAYILMAZ):", paket["anlik_kanallar"])
    print("bar        :", len(paket["barlar15"]), "x 15M +",
          len(paket["barlar4h"] or []), "x 4H")
    print()
    print(metin_rapor(karar))
    print()
    print(sonuc_satiri(karar, veri_kaynagi, paket))
    return karar


VARSAYILAN_SEMBOL = "BTCUSDT"


def mekanizma_ozeti(cumle=None):
    """Bozuk cumle -> onarim: piyasa kanallarina uygulanan AYNI matematigin
    tek bakista okunan gosterimi. argmax_c [ log P(c) + log P(gozlem|c) ]."""
    r = cumle_onar(cumle or ORNEK_CUMLE)
    return "\n".join([
        "MEKANIZMA (ayni matematik kanallara da uygulanir)",
        "  gozlem  : %s" % (cumle or ORNEK_CUMLE),
        "  onarim  : %s" % r["onarilan"],
        "  guven   : gm=%.4f | en zayif halka=%.4f  "
        "(dusuk guven YON'u degil STAKE'i kucultur)"
        % (r["guven_gm"], r["en_zayif"])])


def varsayilan_kosu(canli_getir=None, rapor=None):
    """ARGUMANSIZ calistirmanin yaptigi is: KOS ve SONUCU YAZ.

    Once GERCEK veri denenir. Ag yoksa AGSIZ ornege DUSULUR - ama dusuldugu
    acikca yazilir ve sonuc blogu 'ORNEK (SAHTE VERI)' etiketi tasir:
    sahte veriden cikan sayi, gercek karar gibi SUNULMAZ (uydurma yasagi).
    """
    print(mekanizma_ozeti())
    print()
    print("KOSU BASLIYOR - once gercek veri denenir (ag yoksa ornege duser).")
    print("Bu islem cep telefonunda 1-2 dakika surebilir; bekleyin.")
    print()
    try:
        k = _kosu_bas(VARSAYILAN_SEMBOL, canli_getir,
                      "CANLI KOSU - " + VARSAYILAN_SEMBOL + " (public GET)",
                      "CANLI (borsa public GET)")
    except Exception as h:                      # ag/veri yoksa: DUSUS, gizlenmez
        print("CANLI VERI ALINAMADI -> %s: %s" % (type(h).__name__, h))
        print("AGSIZ ORNEGE dusuluyor: asagidaki sayilar SAHTE veriden gelir,")
        print("GERCEK KARAR DEGILDIR. Gercek karar icin: --canli " + VARSAYILAN_SEMBOL)
        print()
        k = _kosu_bas(VARSAYILAN_SEMBOL, _sahte_getir,
                      "ORNEK KOSU - SAHTE VERI (ag YOK). Gercek karar DEGILDIR.",
                      "ORNEK (SAHTE VERI - gercek karar DEGIL)")
    if rapor:
        rapor_yaz([k], rapor)
        print("rapor yazildi:", rapor)
    return k


_OZ_TEST_KOSUYOR = False


def oz_test_kosuyor():
    return _OZ_TEST_KOSUYOR


def _oz_test():
    global _OZ_TEST_KOSUYOR
    if _OZ_TEST_KOSUYOR:
        return 0
    import sys as _sys
    import unittest as _ut
    _t = _sys.modules[__name__]
    _OZ_TEST_KOSUYOR = True
    try:
        s = _ut.TextTestRunner(verbosity=1).run(
            _ut.defaultTestLoader.loadTestsFromModule(_t))
    finally:
        _OZ_TEST_KOSUYOR = False
    return 0 if s.wasSuccessful() else 1


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=SURUM)
    ap.add_argument("--self-test", action="store_true", help="gomulu testleri kosturur")
    ap.add_argument("--esikler", action="store_true", help="sabit beyani")
    ap.add_argument("--cumle", nargs="?", const=ORNEK_CUMLE,
                    help="bozuk cumleyi onarir (mekanizma gosterimi)")
    ap.add_argument("--ornek", action="store_true", help="AGSIZ ornek kosu")
    ap.add_argument("--canli", metavar="SEMBOL", help="GERCEK Binance public GET")
    ap.add_argument("--rapor", metavar="DOSYA", help="kosuyu JSON'a yazar")
    ap.add_argument("--lam", type=float, default=1.0)
    a = ap.parse_args(argv)

    if a.self_test:
        return _oz_test()
    if a.esikler:
        print(esik_raporu())
        return 0
    if a.cumle:
        r = cumle_onar(a.cumle)
        print("GOZLEM (bozuk kanal):", a.cumle)
        print()
        print("%-18s %-16s %8s %8s   %s" % ("gozlem", "onarim", "P(post)", "marj", "alt."))
        print("-" * 88)
        for s in r["satirlar"]:
            print("%-18s %-16s %8.4f %8.4f   %s"
                  % (s["gozlem"], s["onarim"], s["posterior"], s["marj"],
                     ", ".join("%s(%.2f)" % (x, p) for x, p in s["alternatifler"])))
        print("-" * 88)
        print("ONARILAN     :", r["onarilan"])
        print("ONARIM GUVENI: gm=%.4f  en zayif halka=%.4f" % (r["guven_gm"], r["en_zayif"]))
        print()
        print("Trading tarafinda AYNI matematik kanallara uygulanir:")
        print("  P(c)*P(o|c) -> argmax -> guven; HOLD YOK, dusuk guven STAKE'e gider.")
        return 0
    if a.ornek:
        k = _kosu_bas(VARSAYILAN_SEMBOL, _sahte_getir,
                      "ORNEK KOSU - SAHTE VERI (ag YOK). Gercek karar DEGILDIR.",
                      "ORNEK (SAHTE VERI - gercek karar DEGIL)")
        if a.rapor:
            rapor_yaz([k], a.rapor)
            print("rapor yazildi:", a.rapor)
        return 0
    if a.canli:
        try:
            k = _kosu_bas(a.canli, None,
                          "CANLI KOSU - " + a.canli + " (public GET)",
                          "CANLI (borsa public GET)")
            if a.rapor:
                rapor_yaz([k], a.rapor)
                print("rapor yazildi:", a.rapor)
        except Exception as h:
            print("CANLI KOSU BASARISIZ (fail-closed): %s: %s" % (type(h).__name__, h))
            print("Uydurma veriyle karar URETILMEZ.")
            return 1
        return 0

    # ARGUMANSIZ CALISTIRMA = TAM KOSU + SONUC. Secenek listesi basmak bir
    # cikti DEGILDIR; dosya calistirildiginda hukmunu yazmak zorundadir.
    varsayilan_kosu(rapor=a.rapor)
    print()
    print("Diger modlar: --self-test | --esikler | --cumle | --ornek | "
          "--canli SEMBOL | --rapor r.json")
    return 0


# ==========================================================================
# BOLUM 22 - TEST PAKETI. `--self-test` bunlari kosturur.
# ==========================================================================

import re          # noqa: E402
import unittest    # noqa: E402


# ------------------------------------------------------- SOZLESME TESTLERI
class HoldYasagiTesti(unittest.TestCase):
    """Kullanicinin ACIK sarti: HOLD/ABSTAIN/BEKLE YOKTUR."""

    def test_sozluk_iki_elemanli(self):
        self.assertEqual(YON_SOZLUGU, ("LONG", "SHORT"))
        self.assertEqual(len(YON_SOZLUGU), 2)

    def test_decode_daima_yon_doner(self):
        for p in (0.0, 0.1, 0.4999, 0.5, 0.5001, 0.9, 1.0):
            self.assertIn(decode(p), YON_SOZLUGU)

    def test_kaynakta_hold_sinifi_yok(self):
        kaynak = _modul_kaynagi()
        for yasak in ("HOLD", "ABSTAIN"):
            # yalniz sozluk/sinif olarak gecmemeli; aciklama metninde gecebilir
            for m in re.finditer(r'["\']%s["\']' % yasak, kaynak):
                self.fail("motor bolumunde %s SINIFI bulundu: %s"
                          % (yasak, kaynak[max(0, m.start() - 60):m.end() + 20]))

    def test_dejenere_bolmede_bile_yon_uretilir(self):
        """Model egitilemese bile yon gelir - ama YAPISAL_TABAN etiketiyle."""
        rng = tohumlu_rng("dejenere")
        n = 60                       # bilerek YETERSIZ
        barlar, f = [], 100.0
        for i in range(n):
            f *= 1.0 + rng.uniform(-0.002, 0.003)
            barlar.append({"t": i * 900000, "o": f, "h": f * 1.002,
                           "l": f * 0.998, "c": f, "v": 1000.0,
                           "taker_alis": 500.0})
        paket = {"sembol": "TEST", "barlar15": barlar, "barlar4h": None,
                 "turev_serisi": None, "onarim_izi": None, "onarim_raporu": {},
                 "dolu_kanal": 1, "toplam_kanal": 6, "anlik_kanallar": [],
                 "adaptor": "test"}
        k = BoruHatti(tohum=7).calistir(paket)
        self.assertIn(k["yon"], YON_SOZLUGU)
        self.assertEqual(k["yon_kaynagi"], "YAPISAL_TABAN")
        self.assertFalse(k["egitildi"])
        self.assertEqual(k["stake"]["f"], 0.0)      # kanit yok -> bahis 0


class UydurmaYasagiTesti(unittest.TestCase):
    def test_notr_sifir_enjeksiyonu_yok(self):
        """Eksik gozlem UYDURULMAZ: beceri yoksa deger None kalir."""
        beceri = {"beceri": 0.0, "kestirici": None}
        o = deger_onar(None, [1.0, 2.0, 3.0], "SILME", beceri)
        self.assertIsNone(o["deger"])
        self.assertEqual(o["guven"], 0.0)

    def test_ham_deger_korunur_onarim_mesru_degilse(self):
        beceri = {"beceri": 0.0, "kestirici": None}
        o = deger_onar(42.0, [1.0, 2.0], "DEGISTIRME", beceri)
        self.assertEqual(o["deger"], 42.0)
        self.assertEqual(o["kaynak"], "HAM")

    def test_her_esik_beyanli(self):
        for ad, k in ESIK_KAYNAGI.items():
            self.assertIn(k["kaynak"], ("OLCULEN", "YAPISAL", "VARSAYIM"), ad)
            self.assertTrue(k["gerekce"].strip(), ad)
            if k["kaynak"] == "VARSAYIM":
                self.assertTrue(k["olcum_yolu"].strip(),
                                "%s VARSAYIM ama olcum yolu YOK" % ad)


class GuvenlikTesti(unittest.TestCase):
    def test_yasakli_desen_yok(self):
        kaynak = _modul_kaynagi()
        yasak = [r"api[_-]?key", r"secret", r"hmac", r"signature=",
                 r"/order\b", r"/fapi/v1/order", r"cancelOrder", r"privateKey"]
        for d in yasak:
            self.assertIsNone(re.search(d, kaynak, re.I),
                              "motor bolumunde yasakli desen: %s" % d)

    def test_tek_ag_cagrisi(self):
        kaynak = _modul_kaynagi()
        self.assertEqual(len(re.findall(r"urlopen\(", kaynak)), 1)


# ------------------------------------------------- GURULTULU KANAL TESTLERI
def _kayit(t, v, alan="deger"):
    return {"timestamp": t, alan: v}


class BozulmaTespitTesti(unittest.TestCase):
    ADIM = 900000

    def test_silme_tespit_edilir(self):
        k = [_kayit(i * self.ADIM, 10.0 + i) for i in range(20)]
        del k[10:13]                                   # 3 bar sil
        r = bozulma_tespit(k, self.ADIM, "deger")
        self.assertEqual(r["sayim"]["SILME"], 3)
        self.assertEqual(len(r["eksik_zamanlar"]), 3)

    def test_ekleme_cift_kayit_tespit_edilir(self):
        k = [_kayit(i * self.ADIM, 10.0 + i) for i in range(10)]
        k.append(_kayit(5 * self.ADIM, 99.0))
        r = bozulma_tespit(k, self.ADIM, "deger")
        self.assertEqual(r["sayim"]["EKLEME"], 1)
        self.assertEqual(len(r["kayitlar"]), 10)

    def test_uzatma_donmus_deger_tespit_edilir(self):
        v = [10.0, 11.0, 12.0] + [12.0, 12.0] + [13.0, 14.0]
        k = [_kayit(i * self.ADIM, x) for i, x in enumerate(v)]
        r = bozulma_tespit(k, self.ADIM, "deger")
        self.assertGreaterEqual(r["sayim"]["UZATMA"], 1)

    def test_degistirme_spike_tespit_edilir(self):
        rng = tohumlu_rng("spike-testi")
        v = [100.0 * (1 + rng.uniform(-0.001, 0.001)) for _ in range(60)]
        v[40] = v[39] * 1.8                            # bariz spike
        k = [_kayit(i * self.ADIM, x) for i, x in enumerate(v)]
        r = bozulma_tespit(k, self.ADIM, "deger")
        self.assertGreaterEqual(r["sayim"]["DEGISTIRME"], 1)
        self.assertIn(40, r["spike_indeksleri"])

    def test_birlestirme_tek_anlik_deger_yayilmaz(self):
        r = birlestirme_tespit(1, 200, "funding")
        self.assertEqual(r["mod"], "BIRLESTIRME")
        self.assertFalse(r["yayilabilir"])

    def test_temiz_kanalda_bulgu_yok(self):
        k = [_kayit(i * self.ADIM, 10.0 + i * 0.1) for i in range(50)]
        r = bozulma_tespit(k, self.ADIM, "deger")
        self.assertEqual(sum(r["sayim"].values()), 0)


class OnarimBecerisiTesti(unittest.TestCase):
    def test_kestirilebilir_seride_beceri_pozitif(self):
        """Yavas suruklenen seri (OI gibi): naif kestirici cok iyi olmali."""
        rng = tohumlu_rng("yavas")
        v, x = [], 1000.0
        for _ in range(80):
            x += rng.uniform(-1.0, 1.0)
            v.append(x)
        b = onarim_becerisi(v)
        self.assertGreater(b["beceri"], 0.0)
        self.assertIsNotNone(b["kestirici"])

    def test_beyaz_gurultude_beceri_pozitif_degil_ve_onarim_yapilmaz(self):
        """Bagimsiz gurultu (taker gibi): gecmisten kestirilemez."""
        rng = tohumlu_rng("gurultu")
        v = [rng.gauss(1.0, 0.5) for _ in range(80)]
        b = onarim_becerisi(v)
        self.assertIsNone(b["kestirici"],
                          "beyaz gurultude onarim YAPILMAMALI (beceri=%.4f)"
                          % b["beceri"])

    def test_yetersiz_ornekte_onarim_yapilmaz(self):
        b = onarim_becerisi([1.0, 2.0, 3.0])
        self.assertIsNone(b["kestirici"])
        self.assertEqual(b["beceri"], 0.0)

    def test_sabit_seride_onarim_yapilmaz(self):
        b = onarim_becerisi([5.0] * 40)
        self.assertIsNone(b["kestirici"])

    def test_beceri_look_ahead_icermez(self):
        """Bar t'nin kestirimi t'den SONRAKI barlar degisince DEGISMEMELI."""
        rng = tohumlu_rng("look")
        v = [1000.0 + i + rng.uniform(-1, 1) for i in range(60)]
        W = ONARIM_PENCERESI
        t = 30
        once = _kestir(v[t - W:t], "medyan")
        v2 = list(v)
        for j in range(t, len(v2)):
            v2[j] *= 3.0
        sonra = _kestir(v2[t - W:t], "medyan")
        self.assertEqual(once, sonra)


class OnarimUygulamaTesti(unittest.TestCase):
    def test_onarim_guveni_1i_asamaz(self):
        """FAIL-OPEN IMKANSIZ: guven = beceri * posterior, ikisi de [0,1]."""
        beceri = {"beceri": 1.0, "kestirici": "naif"}
        o = deger_onar(1000.0, [1000.0] * 8, "DEGISTIRME", beceri)
        self.assertLessEqual(o["guven"], 1.0)
        self.assertGreaterEqual(o["guven"], 0.0)

    def test_spike_onarilinca_seri_degisir_ham_seri_degismez(self):
        rng = tohumlu_rng("spike-onarim")
        v = [1000.0 + i * 0.5 + rng.uniform(-0.5, 0.5) for i in range(60)]
        v[40] = v[39] * 1.8
        k = [_kayit(i * 900000, x) for i, x in enumerate(v)]
        r = kanal_onar(k, 900000, "deger")
        onarilan = [x for _, x in r["seri"]]
        self.assertNotEqual(onarilan[40], v[40],
                            "spike onarilmadi (beceri=%s)" % r["beceri"])
        self.assertEqual(onarilan[0], v[0])

    def test_shrinkage_onarim_kapisi_stake_dusurur(self):
        tam = shrinkage_katsayisi(90, 100, 0.01, 6, 6, onarim_guveni=1.0,
                                  taban_oran=0.5)
        yari = shrinkage_katsayisi(90, 100, 0.01, 6, 6, onarim_guveni=0.5,
                                   taban_oran=0.5)
        sifir = shrinkage_katsayisi(90, 100, 0.01, 6, 6, onarim_guveni=0.0,
                                    taban_oran=0.5)
        self.assertAlmostEqual(yari["s"], tam["s"] * 0.5, places=9)
        self.assertEqual(sifir["s"], 0.0)

    def test_onarim_guveni_yonu_susturamaz(self):
        """Onarim guveni 0 olsa bile YON uretilir (kullanicinin sarti)."""
        rng = tohumlu_rng("yon-korunur")
        n = 60
        barlar, f = [], 100.0
        for i in range(n):
            f *= 1.0 + rng.uniform(-0.002, 0.003)
            barlar.append({"t": i * 900000, "o": f, "h": f * 1.002,
                           "l": f * 0.998, "c": f, "v": 1000.0, "taker_alis": 500.0})
        paket = {"sembol": "TEST", "barlar15": barlar, "barlar4h": None,
                 "turev_serisi": None,
                 "onarim_izi": [{"guven": 0.0, "fark": 0.0, "yogunluk": 1.0}] * n,
                 "onarim_raporu": {}, "dolu_kanal": 1, "toplam_kanal": 6,
                 "anlik_kanallar": [], "adaptor": "test"}
        k = BoruHatti(tohum=11).calistir(paket)
        self.assertIn(k["yon"], YON_SOZLUGU)
        self.assertEqual(k["stake"]["f"], 0.0)


# ------------------------------------------------- ARITMETIK / SIZINTI TESTLERI
class GeometriTesti(unittest.TestCase):
    def test_R_hedef_bolu_stop_mesafesidir(self):
        """Uc ayri belgede 'stop 1.5xATR + hedef 2.0xATR = RRR 1:2' yazildi.
        GERCEK R = 1.3333. Bu test o hatayi yapisal olarak imkansiz kilar."""
        s = seviyeler(100.0, 1.0, "LONG", 1.5, 2.0)
        self.assertAlmostEqual(s["R"], 2.0 / 1.5, places=12)
        self.assertAlmostEqual(s["R"], 1.3333333333333333, places=10)
        self.assertNotAlmostEqual(s["R"], 2.0, places=3)

    def test_R_yon_bagimsizdir(self):
        a = seviyeler(100.0, 1.0, "LONG", 1.5, 3.0)["R"]
        b = seviyeler(100.0, 1.0, "SHORT", 1.5, 3.0)["R"]
        self.assertAlmostEqual(a, b, places=12)
        self.assertAlmostEqual(a, 2.0, places=12)

    def test_seviyeler_ve_ilk_gecis_ayni_kaynaktan(self):
        """Olculen bariyerler ile YAYINLANAN seviyeler AYNI fonksiyondan."""
        kaynak = _modul_kaynagi()
        govde = kaynak[kaynak.index("def ilk_gecis_olcum"):]
        govde = govde[:govde.index("\ndef ")]
        self.assertIn("seviyeler(", govde)


class MaliyetKellyTesti(unittest.TestCase):
    def test_basabas_dogru(self):
        b, a = net_kanatlar(2.0, 0.5)
        self.assertAlmostEqual(b, 1.5)
        self.assertAlmostEqual(a, 1.5)
        self.assertAlmostEqual(basabas_p(b, a), 0.5)

    def test_kanat_negatifse_bahis_imkansiz(self):
        b, a = net_kanatlar(1.0, 1.5)
        self.assertLessEqual(b, 0.0)
        self.assertIsNone(basabas_p(b, a))
        r = stake_hesapla(0.99, 1.0, b, a)
        self.assertEqual(r["f"], 0.0)

    def test_kanit_yoksa_stake_TAM_sifir(self):
        """160 kombinasyonda ihlal olmamali (kayan nokta artigi dahil)."""
        ihlal = 0
        for R in (1.2, 1.35, 1.5, 2.0, 3.0):
            for cost in (0.0, 0.1, 0.3, 0.6, 1.0, 1.5, 2.0, 3.0):
                b, a = net_kanatlar(R, cost)
                for p in (0.0, 0.25, 0.5, 0.75, 1.0):
                    f = stake_hesapla(p, 0.0, b, a)["f"]
                    if f != 0.0:
                        ihlal += 1
        self.assertEqual(ihlal, 0)

    def test_maliyet_R_birimine_dogru_cevrilir(self):
        # 18 bp gidis-donus, stop mesafesi fiyatin %0.30'u -> cost_r = 0.60
        c = maliyet_r(100.0, 0.30, 0.0004, 0.0005, 0.0)
        self.assertAlmostEqual(c, 0.0018 * 100.0 / 0.30, places=12)
        self.assertAlmostEqual(c, 0.6, places=12)

    def test_kelly_monoton(self):
        b, a = net_kanatlar(2.0, 0.2)
        onceki = -1.0
        for p in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            f = kelly_asimetrik(p, b, a)
            self.assertGreaterEqual(f, onceki)
            onceki = f


class SizintiTesti(unittest.TestCase):
    def test_h4_hizalama_look_ahead_icermez(self):
        """4H bar k, 15M [16k, 16k+15]'i kapsar ve 16k+15'te KAPANIR."""
        esl = _h4_hizala(64, 4)
        self.assertEqual(esl[15], 0)      # bar 15: 4H bar 0 yeni kapandi
        self.assertEqual(esl[16], 0)      # bar 16: hala 4H bar 0
        self.assertEqual(esl[31], 1)
        self.assertEqual(esl[32], 1)
        for i in range(64):
            self.assertLessEqual(esl[i], (i + 1) // 16 - 1 if i >= 15 else 0)

    def test_purge_boslugu_erisimi_icerir(self):
        p = {"yuvarlanan": 24, "atr": 7, "ema_hizli": 5, "ema_yavas": 8, "rsi": 7,
             "ad": "KISA"}
        e = girdi_erisimi(p, h4_var=False)
        self.assertGreaterEqual(e, oznitelik_penceresi(p))
        self.assertEqual(purge_boslugu(p, h4_var=False), ETIKET_UFKU + EMBARGO + e)

    def test_onarim_penceresi_erisime_eklenir(self):
        p = {"yuvarlanan": 24, "atr": 7, "ema_hizli": 5, "ema_yavas": 8, "rsi": 7,
             "ad": "KISA"}
        a = girdi_erisimi(p, h4_var=False, onarim_penceresi=0)
        b = girdi_erisimi(p, h4_var=False, onarim_penceresi=24)
        self.assertEqual(b - a, 24)

    def test_bos_bolmede_sizinti_None(self):
        """Olculemeyen sey 'yok' diye raporlanamaz (fail-OPEN yasagi)."""
        b = kronolojik_bol(list(range(10)), 16, 4, 100)
        self.assertEqual(b["train"], [])
        self.assertIn("yetersiz", b["not"])

    def test_ema_erisimi_toleranstan_bagimsiz(self):
        """Ozyinelemeli EMA'nin erisimi TOLERANSA baglidir; kesilmis EMA'nin
        DEGILDIR. Kanitlanabilir ust sinir olmadan purge korkulugu kurulamaz."""
        rng = tohumlu_rng("ema-erisim")
        n, i, per = 400, 350, 21
        v = [100.0 + rng.uniform(-1, 1) for _ in range(n)]
        taban = ema(v, per)[i]
        pencere = per * EMA_KESME_KATI
        for tol in (1e-15, 1e-12, 1e-9, 1e-6):
            erisim = 0
            for g in range(1, n):
                if i - g < 0:
                    break
                v2 = list(v)
                v2[i - g] *= 1.001
                if abs(ema(v2, per)[i] - taban) > tol:
                    erisim = g
            self.assertLessEqual(erisim, pencere,
                                 "tolerans %g'de erisim %d > pencere %d"
                                 % (tol, erisim, pencere))


class ProfilTesti(unittest.TestCase):
    def test_az_barda_kisa_profil_secilir(self):
        """4H'siz 500 barda bir cift SIGAR; 200 barda SIGMAZ ve bu durust
        biçimde raporlanir (gereken bar SAYIYLA soylenir)."""
        s = profil_sec(500, h4_var=False)
        self.assertEqual(s["not"], "")
        self.assertLessEqual(s["gereken_bar"], 500)
        self.assertTrue(any(d["uygun"] for d in s["denenen"]))
        az = profil_sec(200, h4_var=False)
        self.assertTrue(az["not"])
        self.assertIsNotNone(az["gereken_bar"])
        self.assertGreater(az["gereken_bar"], 200)

    def test_4h_penceresi_de_uyarlanir(self):
        """4H penceresi 16x pahalidir; sabit tutulursa 15M'i kisaltmak
        purge'u HIC dusurmez (olculdu: her profilde purge=550)."""
        a = profil_sec(2400, h4_var=True)
        b = profil_sec(20000, h4_var=True)
        self.assertLess(a["purge"], b["purge"])
        self.assertNotEqual(a["h4_profil"]["ad"], b["h4_profil"]["ad"])

    def test_cok_barda_tam_profil_secilir(self):
        s = profil_sec(50000, h4_var=True)
        self.assertEqual(s["profil"]["ad"], "TAM")

    def test_hicbiri_uymazsa_gereken_bar_SAYIYLA_soylenir(self):
        """'Ulasilamaz' demek YETMEZ - kac bar gerektigi SAYIYLA soylenir."""
        s = profil_sec(30, h4_var=True)
        self.assertTrue(s["not"])
        self.assertIsNotNone(s["gereken_bar"])
        self.assertGreater(s["gereken_bar"], 30)
        self.assertIn("gereken en az", s["not"])
        self.assertIn("gun 15M", s["not"])

    def test_gereken_acikllik_somut_sayi_doner(self):
        g = gereken_acikllik(550, 0.2, 40)
        self.assertGreater(g["acikllik"], 550)
        self.assertIsNotNone(g["ornek"])
        self.assertAlmostEqual(g["gun_15m"], g["acikllik"] / 96.0, places=9)

    def test_profil_kaynagi_olculen(self):
        s = profil_sec(1000, h4_var=False)
        self.assertIn("OLCULEN", s["kaynak"])


class KalibrasyonTesti(unittest.TestCase):
    def test_ece_tek_bine_cokme_yakalanir(self):
        c = [(0.335, 1), (0.336, 0), (0.334, 1), (0.337, 0)]
        d = ece_duyarlilik(c)
        self.assertTrue(d["tek_bine_cokme"])

    def test_wilson_alt_siniri_daralir(self):
        a1, _ = wilson_araligi(7, 10)
        a2, _ = wilson_araligi(70, 100)
        self.assertLess(a1, a2)

    def test_auroc_mukemmel_ayirmada_1(self):
        c = [(0.9, 1), (0.8, 1), (0.2, 0), (0.1, 0)]
        self.assertAlmostEqual(auroc(c), 1.0)

    def test_yarisma_yetersiz_ornekte_yapilmaz(self):
        b = [Baslik(boyut=4, tohum=1)]
        k = [{"x": [0.1, 0.2, 0.3, 0.4], "y": 1} for _ in range(5)]
        r = kalibrasyon_sec(k, b)
        self.assertTrue(r["yarisma"].startswith("YAPILMADI"))
        self.assertEqual(r["yontem"], "sicaklik")


class CumleTesti(unittest.TestCase):
    def test_ornek_cumle_onarilir(self):
        r = cumle_onar(ORNEK_CUMLE)
        self.assertIn("simdi", r["onarilan"])
        self.assertIn("eskisi", r["onarilan"])
        self.assertIn("yerinde", r["onarilan"])
        self.assertGreater(r["guven_gm"], 0.4)

    def test_her_kelime_icin_cikti_uretilir_hold_yok(self):
        r = cumle_onar(ORNEK_CUMLE)
        self.assertEqual(len(r["satirlar"]), len(ORNEK_CUMLE.split()))
        for s in r["satirlar"]:
            self.assertTrue(s["onarim"])
            self.assertGreater(s["posterior"], 0.0)

    def test_birlestirme_bolunur(self):
        r = cumle_onar("geteranladinsen")
        self.assertIn(" ", r["onarilan"])


class DeterminizmTesti(unittest.TestCase):
    def test_ayni_tohum_ayni_sonuc(self):
        a = tohumlu_rng("x", 1).random()
        b = tohumlu_rng("x", 1).random()
        self.assertEqual(a, b)

    def test_modul_duzeyi_random_yok(self):
        kaynak = _modul_kaynagi()
        satirlar = [s for s in kaynak.splitlines()
                    if re.search(r"^\s*random\.", s) or re.search(r"[^_a-z]random\.(random|uniform|gauss|shuffle)\(", s)]
        for s in satirlar:
            self.assertIn("tohumlu_rng", s + " ",
                          "tohumsuz random kullanimi: %s" % s.strip())


_FIKSTUR_ONBELLEK = {}


def _fikstur_kosu(tohum=5):
    """Uctan uca kosuyu test paketi icinde BIR KEZ kosar.
    Ayni girdi -> ayni cikti (determinizm testiyle kilitli), o yuzden
    onbellek dogrulugu bozmaz; yalniz Pydroid 3'te sureyi ~6x kisaltir."""
    if tohum not in _FIKSTUR_ONBELLEK:
        _FIKSTUR_ONBELLEK[tohum] = canli_kosu("BTCUSDT", getir_fn=_sahte_getir,
                                              tohum=tohum)
    k, p, t = _FIKSTUR_ONBELLEK[tohum]
    return dict(k), p, t


class UctanUcaTesti(unittest.TestCase):
    def test_ornek_kosu_calisir_ve_yon_uretir(self):
        karar, paket, toplama = _fikstur_kosu(5)
        self.assertIn(karar["yon"], YON_SOZLUGU)
        self.assertIsNotNone(karar["giris"])
        self.assertIsNotNone(karar["stop"])
        self.assertIsNotNone(karar["hedef"])
        self.assertGreaterEqual(karar["stake"]["f"], 0.0)
        iz = karar["iz"]
        for h in ("halka_0", "halka_1", "halka_2", "halka_3", "halka_10",
                  "halka_11", "halka_12"):
            self.assertIn(h, iz)
        self.assertFalse(iz["halka_11"]["hold"])

    def test_onarim_raporu_bozulmayi_yakalar(self):
        """Sahte veri BILEREK bozulma iceriyor: OI'de bosluk + spike."""
        _, paket, _ = _fikstur_kosu(5)
        r = paket["onarim_raporu"]
        self.assertIn("oi", r)
        sayim = r["oi"]["sayim"]
        self.assertGreater(sayim["SILME"] + sayim["DEGISTIRME"], 0,
                           "enjekte edilen bozulma YAKALANMADI: %s" % sayim)

    def test_anlik_kanal_kapsama_sayilmaz(self):
        _, paket, _ = _fikstur_kosu(5)
        self.assertTrue(set(paket["anlik_kanallar"]) <= set(ANLIK_KANALLAR))
        self.assertLessEqual(paket["dolu_kanal"],
                             len(KANALLAR) - len(paket["anlik_kanallar"]))

    def test_rapor_serilesir(self):
        import json as _json
        import tempfile
        import os as _os
        karar, _, _ = _fikstur_kosu(5)
        fd, yol = tempfile.mkstemp(suffix=".json")
        _os.close(fd)
        try:
            rapor_yaz([karar], yol)
            with open(yol, encoding="utf-8") as f:
                g = _json.load(f)
            self.assertEqual(g["surum"], SURUM)
            self.assertEqual(len(g["kararlar"]), 1)
        finally:
            _os.unlink(yol)

    def test_metin_rapor_cokmez(self):
        karar, _, _ = _fikstur_kosu(5)
        m = metin_rapor(karar)
        self.assertIn("YON:", m)
        self.assertIn("ONARIM", m)
        self.assertIn("karar-destek", m)

    def test_defter_f_sifirda_pozisyon_acmaz(self):
        karar, _, _ = _fikstur_kosu(5)
        karar["stake"]["f"] = 0.0
        d = defter_guncelle({"sermaye": 1000.0, "pozisyonlar": {}}, karar,
                            {"h": 1e9, "l": 0.0})
        self.assertEqual(d["pozisyonlar"], {})



# ---- FAIL-OPEN REGRESYON TESTLERI (kosarken bulunan gercek kusur) ----
class FailOpenTesti(unittest.TestCase):
    """Kosarken olculdu: OI'de 10 SILME + 2 DEGISTIRME varken ve beceri=0
    iken onarim guveni 1.0000 cikiyordu. Kok neden: _hizala_geriye bosluk
    boyunca ESKI degeri tasiyordu ve bayatlik guvene hic yansimiyordu."""

    def test_bayat_kayit_kullanilmaz(self):
        barlar = [{"t": i * 900000} for i in range(20)]
        seri = [(0, 5.0)]                       # yalniz ilk barda kayit
        h = _hizala_geriye(seri, barlar, 900000)
        self.assertEqual(h[0], (5.0, 0))
        self.assertEqual(h[BAYATLIK_TAVANI][0], 5.0)
        self.assertIsNone(h[BAYATLIK_TAVANI + 1][0],
                          "tavani asan bayat kayit KULLANILMAMALI")

    def test_bayatlik_guveni_yasla_azalir(self):
        g = [_bayatlik_guveni(y) for y in range(0, BAYATLIK_TAVANI + 1)]
        self.assertAlmostEqual(g[0], 1.0)
        for i in range(1, len(g)):
            self.assertLess(g[i], g[i - 1])
        self.assertEqual(_bayatlik_guveni(None), 0.0)

    def test_bozuk_onarilamaz_kanalda_guven_1_olamaz(self):
        """Ana regresyon: kanal bozuk + beceri yok -> guven 1.0 OLMAMALI."""
        _, paket, _ = _fikstur_kosu(5)
        izi = paket["onarim_izi"]
        gm_girdi = [max(x["guven"], 1e-6) for x in izi]
        gm = math.exp(sum(math.log(g) for g in gm_girdi) / len(gm_girdi))
        r = paket["onarim_raporu"]
        bozuk = sum(r["oi"]["sayim"].values()) + sum(r["taker"]["sayim"].values())
        self.assertGreater(bozuk, 0, "fikstur bozulma icermiyor")
        self.assertLess(gm, 1.0,
                        "FAIL-OPEN: bozuk kanalda onarim guveni %.6f" % gm)

    def test_bayat_kanal_guveni_dusurur(self):
        """GERCEK VERIDE OLCULEN DURUM: taker LSR'nin son kaydi, son 15M
        barindan 15 dk ONCE bitiyor - yani KARAR BARINDA taker YOK. Kanal
        'var' gorunuyor ama karar aninda bayat. Bu, guveni DUSURMELI.

        Not: HIC gelmeyen kanal AYRI bir seydir ve s_kapsam ile cezalandirilir;
        onu s_onarim ile de cezalandirmak CIFT SAYIM olur."""
        n = 40
        barlar = [{"t": i * 900000, "v": 1000.0, "taker_alis": 500.0}
                  for i in range(n)]
        oi = [{"sumOpenInterest": 1000.0 + i, "timestamp": i * 900000}
              for i in range(n)]
        taze = [{"buySellRatio": 1.0, "timestamp": i * 900000} for i in range(n)]
        # taker son 10 barda YOK (bayat) - gercek veride olculen desen
        bayat = [{"buySellRatio": 1.0, "timestamp": i * 900000}
                 for i in range(n - 10)]
        g_taze = ortalama([x["guven"] for x in
                           turev_serisi_kur(barlar, {"oi": oi, "taker": taze})[1]])
        g_bayat = ortalama([x["guven"] for x in
                            turev_serisi_kur(barlar, {"oi": oi, "taker": bayat})[1]])
        self.assertLess(g_bayat, g_taze,
                        "bayat kanal guveni DUSURMELI (taze %.4f, bayat %.4f)"
                        % (g_taze, g_bayat))
        son = turev_serisi_kur(barlar, {"oi": oi, "taker": bayat})[1][-1]
        self.assertLess(son["guven"], 1.0,
                        "karar barinda bayat kanal varken guven 1.0 OLAMAZ")


class OnarimIzOzniteligiTesti(unittest.TestCase):
    def test_onarim_ailesi_MASKE_tasir_guven_DEGIL(self):
        """TRIAD B1 sonrasi sozlesme: onarim ailesi GOZLEM MASKESI tasir;
        surekli onarim guveni modele GIRMEZ (yalniz stake eksenindedir)."""
        p = {"yuvarlanan": 12, "atr": 5, "ema_hizli": 3, "ema_yavas": 5,
             "rsi": 5, "ad": "ASGARI"}
        barlar = [{"t": i, "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0,
                   "v": 10.0, "taker_alis": 5.0} for i in range(30)]
        g = gostergeler_kur(barlar, p)
        a = satir_uret(barlar, g, None,
                       [{"guven": 0.3, "m_oi": 1.0, "m_taker": 0.0,
                         "yogunluk": 0.5}] * 30, p, 20)
        b = satir_uret(barlar, g, None,
                       [{"guven": 0.9, "m_oi": 1.0, "m_taker": 0.0,
                         "yogunluk": 0.5}] * 30, p, 20)
        self.assertEqual(len(a["onarim"]), AILELER["onarim"])
        self.assertEqual(a["onarim"], b["onarim"],
                         "guven degisince oznitelik DEGISMEMELI")
        self.assertAlmostEqual(a["onarim"][0], 1.0 * 2 - 1, places=9)
        self.assertAlmostEqual(a["onarim"][1], 0.0 * 2 - 1, places=9)

    def test_onarim_ozniteligi_karari_etkiler(self):
        """Olu halka testi: onarim izi degisince karar DEGISMELI."""
        def kos(guven):
            rng = tohumlu_rng("olu-halka", guven)
            n = 400
            barlar, f = [], 100.0
            for i in range(n):
                f *= 1.0 + rng.uniform(-0.003, 0.0031)
                barlar.append({"t": i * 900000, "o": f, "h": f * 1.002,
                               "l": f * 0.998, "c": f, "v": 1000.0,
                               "taker_alis": 500.0})
            paket = {"sembol": "T", "barlar15": barlar, "barlar4h": None,
                     "turev_serisi": [{"cvd": 0.1}] * n,
                     "onarim_izi": [{"guven": guven, "fark": 0.0,
                                     "yogunluk": 0.0}] * n,
                     "onarim_raporu": {}, "dolu_kanal": 4, "toplam_kanal": 6,
                     "anlik_kanallar": [], "adaptor": "t"}
            return BoruHatti(tohum=3).calistir(paket)
        a, b = kos(1.0), kos(0.0)
        self.assertNotEqual(a["shrinkage"]["s_onarim"], b["shrinkage"]["s_onarim"])
        self.assertEqual(b["shrinkage"]["s"], 0.0)



# ---- TRIAD DENETIM REGRESYONLARI (KONSEY v8.1 FINAL_AUDIT bulgulari) ----
class TriadDenetimTesti(unittest.TestCase):
    """KONSEY v8.1 TRIAD FINAL_AUDIT'in bu dosyada MEKANIK dogrulanan
    bulgulari. Her test, bulgunun geri gelmesini engelleyen korkuluktur."""

    def test_O2_cift_kirp_doygunlugu_yok(self):
        """BULGU O2: uretimde kirp(D%) + oznitelikte kirp(x*5) cift kirptir
        ve %0.20 UZERINDE buyukluk bilgisini yok eder (olculdu: 0.20->1.00,
        0.60->1.00, 2.00->1.00). Buyuk degisim kucukten AYIRT EDILEBILMELI."""
        olcek = {"oi_degisim": 0.05}       # robust sigma
        a = _olcekli({"oi_degisim": 0.20}, "oi_degisim", olcek)
        b = _olcekli({"oi_degisim": 0.60}, "oi_degisim", olcek)
        c = _olcekli({"oi_degisim": 2.00}, "oi_degisim", olcek)
        self.assertLess(abs(a), abs(b), "%%0.20 ile %%0.60 ayirt edilemiyor")
        self.assertLessEqual(abs(b), abs(c))
        # kucuk degisimler de dogrusal kalmali
        k1 = _olcekli({"oi_degisim": 0.05}, "oi_degisim", olcek)
        k2 = _olcekli({"oi_degisim": 0.10}, "oi_degisim", olcek)
        self.assertAlmostEqual(k2, 2.0 * k1, places=9)

    def test_O2_olcek_yoksa_oznitelik_uretilmez(self):
        self.assertEqual(_olcekli({"oi_degisim": 5.0}, "oi_degisim", {}), 0.0)
        self.assertEqual(_olcekli({}, "oi_degisim", {"oi_degisim": 0.1}), 0.0)

    def test_AR04_bayatlik_carpani_1i_asamaz(self):
        """BULGU AR-04: yas<0 iken us pozitife doner ve carpan 1.0'i ASAR
        (olculdu: yas=-1 -> 1.2840, yas=-2 -> 1.6487) -> riski BUYUTUR."""
        for y in (-10, -2, -1, 0, 1, 4, 100):
            g = _bayatlik_guveni(y)
            self.assertLessEqual(g, 1.0, "yas=%s -> guven=%s > 1.0" % (y, g))
            self.assertGreaterEqual(g, 0.0)

    def test_B1_onarim_guveni_p_longa_GIRMEZ(self):
        """BULGU B1: surekli onarim guveni modele oznitelik olarak verilince
        p_long'u degistiriyor ve YONU CEVIRIYOR (olculdu: guven 1.0 -> SHORT,
        guven 0.0 -> LONG). Onarim guveni bizim KESTIRICIMIZIN kalitesidir,
        piyasa hakkinda bir olgu DEGILDIR; yonu belirlememelidir."""
        def kos(guven):
            # TOHUM guvene BAGLI OLMAMALI - aksi halde iki kosu FARKLI fiyat
            # verisi uretir ve test onarim guvenini degil veriyi olcer.
            rng = tohumlu_rng("b1-regresyon")
            n = 400
            barlar, f = [], 100.0
            for i in range(n):
                f *= 1.0 + rng.uniform(-0.003, 0.0031)
                barlar.append({"t": i * 900000, "o": f, "h": f * 1.002,
                               "l": f * 0.998, "c": f, "v": 1000.0,
                               "taker_alis": 500.0})
            paket = {"sembol": "T", "barlar15": barlar, "barlar4h": None,
                     "turev_serisi": [{"cvd": 0.1}] * n,
                     "onarim_izi": [{"guven": guven, "m_oi": 1.0,
                                     "m_taker": 1.0, "yogunluk": 0.0}] * n,
                     "onarim_raporu": {}, "dolu_kanal": 4, "toplam_kanal": 6,
                     "anlik_kanallar": [], "adaptor": "t"}
            return BoruHatti(tohum=3).calistir(paket)
        a, b = kos(1.0), kos(0.0)
        self.assertEqual(a["p_ham"], b["p_ham"],
                         "onarim guveni p_long'u DEGISTIRIYOR (%.12f vs %.12f)"
                         % (a["p_ham"], b["p_ham"]))
        self.assertEqual(a["yon"], b["yon"])
        # ama STAKE ekseninde etkisi SURMELI
        self.assertNotEqual(a["shrinkage"]["s_onarim"], b["shrinkage"]["s_onarim"])
        self.assertEqual(b["shrinkage"]["s"], 0.0)

    def test_B1_gozlem_maskesi_modele_GIRER(self):
        """Maske bir OLGUDUR ('borsa bu barda OI yayinladi mi') ve kanal
        basina AYRI tutulur; tek skalere ezilirse model hangi kanalin eksik
        oldugunu ayirt edemez."""
        p = {"yuvarlanan": 12, "atr": 5, "ema_hizli": 3, "ema_yavas": 5,
             "rsi": 5, "ad": "ASGARI"}
        barlar = [{"t": i, "o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0,
                   "v": 10.0, "taker_alis": 5.0} for i in range(30)]
        g = gostergeler_kur(barlar, p)
        tam = [{"guven": 0.3, "m_oi": 1.0, "m_taker": 1.0, "yogunluk": 0.0}] * 30
        oi_yok = [{"guven": 0.3, "m_oi": 0.0, "m_taker": 1.0, "yogunluk": 0.5}] * 30
        tk_yok = [{"guven": 0.3, "m_oi": 1.0, "m_taker": 0.0, "yogunluk": 0.5}] * 30
        s1 = satir_uret(barlar, g, None, tam, p, 20)["onarim"]
        s2 = satir_uret(barlar, g, None, oi_yok, p, 20)["onarim"]
        s3 = satir_uret(barlar, g, None, tk_yok, p, 20)["onarim"]
        self.assertNotEqual(s1, s2)
        self.assertNotEqual(s2, s3, "oi eksik ile taker eksik AYIRT EDILEMIYOR")

    def test_AR03_stake_gecidin_olasiligini_kullanir(self):
        """BULGU AR-03: Kelly'ye giren p, b/a'nin TANIMLANDIGI olay olmali.
        p_yon ETIKET olayindan (simetrik 1xATR, ETIKET_UFKU bar), b/a ise
        ASIMETRIK (stop_k,hedef_k) bariyerinden ve azami_bar ufkundan gelir."""
        karar, _, _ = _fikstur_kosu(5)
        st = karar["stake"]
        self.assertIn("p_stake", st)
        self.assertIn("olay_uyumu", st)
        geo = karar["geometri"]
        if geo.get("p_bilesik_alt") is not None:
            self.assertAlmostEqual(st["p_stake"], geo["p_bilesik_alt"], places=12)
            self.assertEqual(st["olay_uyumu"], "GECIT_OLAYI")

    def test_AR03_stake_gecidin_f_sini_ASAMAZ(self):
        """Fail-closed korkuluk: iki hesap ayrisirsa KUCUK olan gecerlidir.

        Bu test kapagin GERCEKTEN BAGLADIGI vakayi icerir - fikstur kosusunda
        f=0 oldugu icin 'f <= f_gecit' iddiasi ici bos gecerdi (tiyatro)."""
        # (a) kapak BAGLAR
        f, bagladi = stake_gecit_kirp(0.40, 0.10)
        self.assertTrue(bagladi)
        self.assertAlmostEqual(f, 0.10, places=12)
        # (b) kapak BAGLAMAZ
        f, bagladi = stake_gecit_kirp(0.05, 0.10)
        self.assertFalse(bagladi)
        self.assertAlmostEqual(f, 0.05, places=12)
        # (c) esitlik: baglamaz, deger korunur
        f, bagladi = stake_gecit_kirp(0.10, 0.10)
        self.assertFalse(bagladi)
        self.assertAlmostEqual(f, 0.10, places=12)
        # (d) negatif girdi 0'a kirpilir
        self.assertEqual(stake_gecit_kirp(-1.0, 0.5)[0], 0.0)
        self.assertEqual(stake_gecit_kirp(0.5, -1.0)[0], 0.0)
        # (e) karar_uret bu fonksiyonu GERCEKTEN cagiriyor mu
        kaynak = _modul_kaynagi()
        govde = kaynak[kaynak.index("def karar_uret"):]
        govde = govde[:govde.index("\ndef ")]
        self.assertIn("stake_gecit_kirp(", govde,
                      "karar_uret gecit kapagini CAGIRMIYOR")
        # (f) kosuda alan tasiniyor
        karar, _, _ = _fikstur_kosu(5)
        for lam, v in karar["stake"]["lambda_tablosu"].items():
            self.assertIn("gecit_bagladi", v)
            self.assertLessEqual(v["f"], v["f_gecit"] + 1e-12)

    def test_AR02_s_kapsam_ve_s_onarim_CARPIM(self):
        """min() degil CARPIM: min'de bir kapi digerini MASKELER."""
        t = shrinkage_katsayisi(90, 100, 0.01, 4, 6, onarim_guveni=1.0)
        y = shrinkage_katsayisi(90, 100, 0.01, 4, 6, onarim_guveni=0.5)
        self.assertAlmostEqual(y["s"] / t["s"], 0.5, places=12)

    def test_B5_p_esit_p0_iken_bahis_ACILMAZ(self):
        """A'da olculdu: p_ham==p0 iken f = 9.46e-17 ve bahis_acilir_mi True
        donuyordu. Dogru olcut f==0.0 degil, TUKETICI YUKLEMIDIR."""
        for R in (1.2, 1.5, 2.0, 3.0):
            for cost in (0.0, 0.3, 0.6, 1.0):
                b, a = net_kanatlar(R, cost)
                p0 = basabas_p(b, a)
                if p0 is None:
                    continue
                for s in (1.0, 1e-6, 1e-12, 1e-18, 0.0):
                    r = stake_hesapla(p0, s, b, a)
                    self.assertFalse(bahis_acilir_mi({"f": r["f"]}),
                                     "R=%s cost=%s s=%s -> f=%r" % (R, cost, s, r["f"]))


class ArgumansizKosuTesti(unittest.TestCase):
    """Kullanicinin sarti: dosya ARGUMANSIZ calistirilinca KOSAR ve SONUC
    yazar. Secenek listesi basmak bir cikti DEGILDIR."""

    @staticmethod
    def _yakala(fn, *a, **k):
        import contextlib as _c
        import io as _io
        tampon = _io.StringIO()
        with _c.redirect_stdout(tampon):
            sonuc = fn(*a, **k)
        return sonuc, tampon.getvalue()

    def test_argumansiz_main_menu_BASMAZ_kosu_yapar(self):
        mod = _sys_modulu()
        esk, cagri = mod.varsayilan_kosu, {}

        def sahte(**kw):
            cagri["kw"] = kw
            return {"sembol": "X"}

        mod.varsayilan_kosu = sahte
        try:
            kod, cikti = self._yakala(mod.main, [])
        finally:
            mod.varsayilan_kosu = esk
        self.assertEqual(kod, 0)
        self.assertIn("kw", cagri, "argumansiz calistirma KOSU yapmadi")
        self.assertNotIn("Secenekler:", cikti)

    def test_canli_patlarsa_ORNEGE_duser_ve_ETIKETLER(self):
        """Dusus gizlenemez: sahte veriden cikan sayi 'canli' diye sunulamaz."""
        mod = _sys_modulu()
        esk, cagrilar = mod._kosu_bas, []

        def sahte(sembol, getir_fn, baslik, veri_kaynagi):
            cagrilar.append((getir_fn, veri_kaynagi))
            if len(cagrilar) == 1:
                raise RuntimeError("ag YOK (test)")
            print("SONUC (test govdesi)")
            return {"sembol": sembol}

        mod._kosu_bas = sahte
        try:
            _, cikti = self._yakala(mod.varsayilan_kosu)
        finally:
            mod._kosu_bas = esk
        self.assertEqual(len(cagrilar), 2, "canli patlayinca ornege DUSULMEDI")
        self.assertIsNone(cagrilar[0][0])              # 1. deneme: GERCEK ag
        self.assertIs(cagrilar[1][0], _sahte_getir)    # 2. deneme: AGSIZ ornek
        self.assertIn("SAHTE VERI", cagrilar[1][1])
        self.assertIn("CANLI VERI ALINAMADI", cikti)
        self.assertIn("GERCEK KARAR DEGILDIR", cikti)

    def test_canli_calisirsa_ORNEK_etiketi_KULLANILMAZ(self):
        mod = _sys_modulu()
        esk, cagrilar = mod._kosu_bas, []

        def sahte(sembol, getir_fn, baslik, veri_kaynagi):
            cagrilar.append((getir_fn, veri_kaynagi))
            return {"sembol": sembol}

        mod._kosu_bas = sahte
        try:
            _, cikti = self._yakala(mod.varsayilan_kosu)
        finally:
            mod._kosu_bas = esk
        self.assertEqual(len(cagrilar), 1)
        self.assertIn("CANLI", cagrilar[0][1])
        self.assertNotIn("SAHTE", cagrilar[0][1])
        self.assertNotIn("CANLI VERI ALINAMADI", cikti)

    def test_sonuc_blogu_YON_ve_SEVIYE_tasir(self):
        k, paket, _ = _fikstur_kosu()
        m = sonuc_satiri(k, "TEST", paket)
        self.assertIn("SONUC", m)
        self.assertRegex(m, r"YON\s+: (LONG|SHORT)\b")
        for alan in ("GIRIS", "STOP", "HEDEF", "R ", "ISLEM"):
            self.assertIn(alan, m)
        self.assertIn(KARAR_DESTEK_UYARISI, m)

    def test_kosu_bas_SONUC_blogunu_BASAR(self):
        """Her kosu modu sonuc blogu ile biter; blok koddan DUSURULEMEZ."""
        mod = _sys_modulu()
        fikstur = _fikstur_kosu()
        esk = mod.canli_kosu
        mod.canli_kosu = lambda sembol, getir_fn=None, **kw: fikstur
        try:
            _, cikti = self._yakala(mod._kosu_bas, "BTCUSDT", None,
                                    "TEST BASLIK", "TEST-KAYNAK")
        finally:
            mod.canli_kosu = esk
        self.assertIn(SONUC_BASLIGI, cikti)
        self.assertIn("TEST-KAYNAK", cikti)
        self.assertRegex(cikti, r"YON\s+: (LONG|SHORT)\b")

    def test_sonuc_gerekcesi_MOTORUN_notudur_uydurulmaz(self):
        """f*=0 gerekcesi sonradan TAHMIN edilmez; stake['not']'tan gelir."""
        k, paket, _ = _fikstur_kosu()
        k = dict(k)
        k["stake"] = dict(k["stake"])
        k["stake"]["f"] = 0.0
        k["stake"]["not"] = "OZGUN-GEREKCE-IZI"
        self.assertIn("OZGUN-GEREKCE-IZI", sonuc_satiri(k, "TEST", paket))

    def test_stake_notu_karar_sozlesmesinde_VAR(self):
        k, _, _ = _fikstur_kosu()
        self.assertIn("not", k["stake"])
        for v in k["stake"]["lambda_tablosu"].values():
            self.assertIn("not", v)
        if not bahis_acilir_mi(k["stake"]):
            self.assertTrue((k["stake"]["not"] or "").strip(),
                            "f*=0 ama GEREKCE bos - rapor nedenini soyleyemez")

    def test_stake_notu_BAHIS_ACILAN_dalda_da_VAR(self):
        """Fikstur fail-closed dala dusuyor; sozlesme POZITIF dalda da
        gecerli olmali - yoksa test tiyatrodur (olculdu: bu test olmadan
        'lt[...]["not"] = ham["not"]' silinse HICBIR test dusmuyordu)."""
        k = _pozitif_f_karari()
        self.assertTrue(bahis_acilir_mi(k["stake"]), "kurgu f>0 uretmedi")
        for lam, v in k["stake"]["lambda_tablosu"].items():
            self.assertIn("not", v, "lambda=%s dalinda GEREKCE alani YOK" % lam)
        self.assertIn("not", k["stake"])

    def test_mekanizma_ozeti_bozuk_cumleyi_onarir(self):
        m = mekanizma_ozeti()
        self.assertIn(ORNEK_CUMLE, m)
        self.assertIn("gm=", m)


def _pozitif_f_karari():
    """f* > 0 uretan KURGU baglam (guclu, gurultusuz trend). Fikstur kosusu
    daima fail-closed dala dustugu icin pozitif dal baska turlu sinanamaz."""
    rng = tohumlu_rng("pozitif-f")
    n, barlar, f = 400, [], 100.0
    for i in range(n):
        f *= 1.0 + 0.004 + rng.uniform(-0.0005, 0.0005)
        barlar.append({"t": i * 900000, "o": f, "h": f * 1.004, "l": f * 0.999,
                       "c": f, "v": 1000.0, "taker_alis": 600.0})
    atr = [f * 0.002] * n
    return karar_uret({
        "sembol": "TEST", "barlar": barlar, "atr_serisi": atr,
        "indeksler": list(range(50, 340)), "p_ham": 0.95,
        "yon_kaynagi": "TEST", "dogru": 95, "toplam": 100, "ece_enkotu": 0.01,
        "taban_oran": 0.5, "ece_tek_bin": False, "sicaklik_sinirda": False,
        "onarim_guveni": 1.0, "dolu_kanal": 6, "toplam_kanal": 6,
        "giris": barlar[350]["c"], "atr": atr[350],
        "likidasyon": barlar[350]["c"] * 0.5, "kaldirac_azami": 10,
        "komisyon": 0.0, "kayma": 0.0, "funding": 0.0, "lam": 1.0})


def _sys_modulu():
    import sys as _sys
    return _sys.modules[__name__]


if __name__ == "__main__":
    raise SystemExit(main())
