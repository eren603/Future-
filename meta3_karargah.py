# META3 KARARGAH v1.5 — Recursive Self-Improving calisma dongusu
# ====================================================================
# KAYNAK SEMA: "META3 — Nihai Recursive Self-Improving Research System"
# (kullanicinin yukledigi PDF; metin cikarimi: scratchpad/meta3.txt).
# Bu modul o semanin bu depodaki DURUST uygulamasidir:
#
#   GOAL -> AGENT -> EVALUATE -> EXPERIMENT MEMORY -> META -> META2
#        -> META3 -> NEXT GENERATION  (hepsi IMMUTABLE CONTROL PLANE icinde)
#
# Sema -> kod eslemesi (PDF bolum numaralariyla):
#   #1/#22 IMMUTABLE CONTROL PLANE  -> IMMUTABLE_PLANE + kapi muhru (hash)
#   #3     AGENT                    -> btc_karargah_v5_4 motoru (karar_uret)
#   #4     EVALUATOR (hakem)        -> degerlendir(): J = wQ*Q + wR*R + wS*S
#                                      - wC*C - wL*L  (agirliklar SABIT ve
#                                      recursive katmanlarca DEGISTIRILEMEZ)
#   #5     AUTORESEARCH dongusu     -> her kosuda varyant deneyi (sandbox=
#                                      golge-degerlendirme; canli emir YOK)
#   #6     META                     -> varyant KEEP/REJECT/ROLLBACK (olcumle);
#                                      kesif karari eps ile (deterministik
#                                      hash takvimi — RNG yok, yeniden
#                                      uretilebilir; eps meta_dongusu'nde
#                                      FIILEN OKUNUR)
#   #7     META2                    -> Meta'nin kesif orani eps'i [0,0.3]
#                                      bandinda olcumle ayarlar (eps'in
#                                      tuketicisi meta_dongusu'ndeki kesif
#                                      kapisidir — olu parametre degildir)
#   #8     META3                    -> META2'nin pencere W'sini [5,50]
#                                      bandinda olcumle ayarlar
#   #10    EXPERIMENT MEMORY        -> meta3_bellek.json (deney kaydi:
#                                      experiment_id, parent_version,
#                                      optimizer_version, hypothesis, patch,
#                                      metrics, cost, latency, risk, decision;
#                                      latency = veri yasi, cost = kosu suresi
#                                      — iki AYRI olcum)
#   #11    EVOLUTION GRAPH          -> bellekteki "evrim" listesi (soy zinciri)
#   #12    FAILURE INTELLIGENCE     -> karantina + basit sinif etiketi
#                                      (veri_yetersiz / olcum_ustun_degil);
#                                      karantina YALNIZ OLCULMUS ret ile artar
#                                      (olculemeyen kiyas = HOLD, ret degil).
#                                      PDF'in planner/tool/memory-failure
#                                      siniflandirmasi UYGULANMADI — bu bilincli
#                                      bir daraltmadir (o siniflar kod-yamalama
#                                      sistemine aittir; burada patch=config).
#   #16    SANDBOX + VERSIONING     -> bellek anlik-goruntusu (.bak) + geri alma
#   #19    DURMA KOSULLARI          -> kosu()/meta_dongusu icinde: HALT (muhur/
#                                      override/bozuk bellek), HOLD (evaluator
#                                      kararsiz), ROLLBACK (olculmus gerileme),
#                                      STOP (kosu-basi deney butcesi bitti —
#                                      kalan adaylar o kosuda degerlendirilmez
#                                      ve bu kayda gecer). "repeated failures ->
#                                      change search" dali karantina ile.
#   #14    RESEARCH CONTROLLER      -> DAGITIK uygulanir: kesif takvimi
#                                      (kesif_zamani) + kosu-basi butce +
#                                      meta2/meta3 kadansi + karantina
#   #24    BILIMSEL SINIR           -> asagida acikca korunur (garanti yok)
#
#   BILINCLI DARALTMALAR (sema bolumune baglanmis, beyansiz degil):
#   #1  GOAL katmani ortuktur: sabit gorev = "yon + giris/cikis uret".
#   #13 Populasyon aramasi SABIT 3-varyant uzayina daraltildi (guvenlik:
#       uretici mutasyon = denetlenemeyen kapi riski; K22).
#   #20 Verimlilik zinciri formul olarak DEGIL yon olarak uygulanir
#       (karar-sayisi sezgiselleri); formul sadakati YOKTUR, beyanlidir.
#   #17 Butce/derinlik kod sabitidir; muhur kapsami asagida acikca
#       listelenir (motor kapi sabitleri + IMMUTABLE_PLANE degerleri).
#
# DURUSTLUK SOZLESMESI (deponun anayasasi + Constitution v2 ile uyum):
#  - "En yuksek dogruluk" bir GARANTI degil, MEKANIZMADIR: sistem her kosuda
#    ONCEKI kosunun verdigi seviyelerin GERCEK akibetini olcer (HESAP VERME),
#    yalnizca OLCULEBILIR iyilesme gosteren degisikligi tutar (KEEP), gerileyeni
#    geri alir (ROLLBACK). PDF'in kendi 24. bolumu de ayni siniri koyar.
#  - Meta katmanlari kapilari GEVSETEMEZ: varyant uzayi yalnizca SIKILASTIRMA
#    (filtre EKLEME) icerir; bu yapisal olarak boyledir (varyant = taban
#    kararin uzerine 'and' kosulu). Gevseten aday uretilemez (K22).
#  - Kod kendi kaynagini DEGISTIRMEZ: "patch" soyutlamasi burada yalnizca
#    YAPILANDIRMA (config) duzeyindedir. Kaynak-kodu kendini yamalayan bir
#    sistem depo sozlesmesinin K16/K22 kurallariyla celisirdi; bu sinir
#    ACIKCA beyan edilir (sessiz daraltma degil).
#  - YON ZORUNLU: her sembolde YON (bias) ve GIRIS/STOP/HEDEF seviyeleri HER
#    KOSUDA basilir. Kapi kapaliysa seviyeler "BILGI" etiketi tasir, "EMIR
#    -ADAYI" degil — yon asla "BEKLE" arkasina gizlenmez.
#  - Canli/otomatik emir YOK. create_order yok, API anahtari yok.
# ====================================================================

import hashlib
import json
import os
import sys
import time
import traceback

import numpy as np
import pandas as pd

# --------------------------------------------------------------------
# MOTOR YUKLEYICI (Pydroid3/Android uyumu — v1.4)
# Pydroid3 scripti exec() ile kendi gecici dizininden calistirir; scriptin
# durdugu klasor sys.path'e girmez ve `import btc_karargah_v5_4` bulunamaz.
# Cozum: motor dosyasi su ADAY dizinlerde aranir ve bulundugu dizin yola
# eklenir. Iki dosya AYNI klasorde durmalidir.
# --------------------------------------------------------------------
_MOTOR_DOSYA = "btc_karargah_v5_4.py"
_ADAY_DIZINLER = []
try:
    _ADAY_DIZINLER.append(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    pass
_ADAY_DIZINLER += [
    os.getcwd(),
    os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0]
    else "",
    "/storage/emulated/0/Download",       # Android indirme klasoru (Pydroid)
    "/storage/emulated/0/Documents",
]
for _d in _ADAY_DIZINLER:
    if _d and os.path.isfile(os.path.join(_d, _MOTOR_DOSYA)):
        if _d not in sys.path:
            sys.path.insert(0, _d)
        break
try:
    import btc_karargah_v5_4 as motor
except ModuleNotFoundError:
    print("HATA: motor dosyasi bulunamadi: " + _MOTOR_DOSYA)
    print("Bu iki dosya AYNI klasorde durmali:")
    print("  1) meta3_karargah.py   (bu dosya)")
    print("  2) btc_karargah_v5_4.py (motor)")
    print("Aranan dizinler:")
    for _d in _ADAY_DIZINLER:
        if _d:
            print("  - " + _d)
    print("Cozum: btc_karargah_v5_4.py dosyasini yukaridaki dizinlerden "
          "birine (tercihen bu dosyanin yanina) kopyala ve tekrar calistir.")
    sys.exit(1)

# --------------------------------------------------------------------
# IMMUTABLE CONTROL PLANE (PDF #17/#22)
# Bu blok recursive katmanlarca DEGISTIRILEMEZ. Kosuda butunluk muhru
# dogrulanir; bozulmussa HALT (PDF #19: safety violation -> HALT).
# --------------------------------------------------------------------
_KAPI_SABITLERI = (
    "FEE_TAKER", "SLIPPAGE", "ATR_LEN", "ATR_SL_MULT", "TIME_STOP_BARS",
    "ALPHA", "MIN_TRADES", "N_FOLDS", "EMBARGO", "BOOTSTRAP_B",
    "PUMP_THRESHOLD_Z", "PUMP_TICK_WATCH", "FR_TOLERANCE_BPS", "LOB_DEPTH",
)

# NOT (etiket disiplini): asagidaki TUM sayilar HIPOTEZ etiketlidir —
# hicbiri olculerek kalibre edilmedi; degerleri tasarim tercihi olarak
# secildi ve canli olcum birikmeden "dogru" kabul edilmez. Immutable
# olmalari ayri bir seydir: recursive katmanlar bunlari OYNAYAMAZ
# (evaluator kendi optimize ettigi seyin hakemi olamaz — PDF #4/#24).
IMMUTABLE_PLANE = {
    # Evaluator agirliklari (PDF #4) — HIPOTEZ
    "w_Q": 1.0, "w_R": 0.5, "w_S": 1.0, "w_C": 0.1, "w_L": 0.05,
    # Kaynak/butce sinirlari (PDF #17) — HIPOTEZ
    "kosu_basi_deney_butcesi": 2,     # her kosuda en fazla 2 varyant degerlendirilir
    "recursive_derinlik": 3,          # META -> META2 -> META3; daha derini YOK
    "min_akibet_n": 8,                # bundan az olculmus akibetle KEEP/REJECT
                                      # verilemez -> HOLD (PDF #19 evaluator unstable)
    "eps_bant": (0.0, 0.3),           # META2'nin oynayabilecegi kesif-orani bandi
    "W_bant": (5, 50),                # META3'un oynayabilecegi pencere bandi
    "karantina_esigi": 3,             # OLCULMUS ret sayisi esigi (PDF #12)
    # META2/META3 guncelleme-kurali sabitleri — HIPOTEZ (etiketsiz birakildigi
    # denetimde bulundu; hepsi burada, tek yerde):
    "meta2_min_orneklem": 4,          # kesif verimi icin asgari KEEP/REJECT sayisi
    "meta2_verim_esigi": 0.25,        # verim bunun ustundeyse eps artar
    "meta2_adim": 0.05,               # eps adim buyuklugu
    "meta3_min_orneklem": 3,          # meta2 kaydi asgarisi
    "meta3_adim_buyut": 5,            # W buyutme adimi
    "meta3_adim_kucult": 3,           # W kucultme adimi
    # v1.2 (2. tur denetim bulgusu — eps=0 yutucu durumu): kesif eps=0'a
    # dussa bile her N kosuda bir ZORUNLU kesif yapilir (PDF #19 "repeated
    # failures -> CHANGE SEARCH" ruhu: arama kalici olarak OLEMEZ) — HIPOTEZ
    "zorunlu_kesif_periyodu": 25,
}
# NOT (yapisal sabit): "recursive_derinlik" kodda bir denetleyici tarafindan
# TUKETILMEZ — katman sayisi (META/META2/META3) kodun yapisiyla sabittir;
# sabit, beyan amaclidir. Katman EKLEYEN bir degisiklik bu sabiti de
# denetler hale getirmelidir (2. tur denetim notu).

# v1.4: bellek/override yollari MOTOR dosyasinin klasorune baglanir —
# Pydroid3'te __file__ gecici exec dizinini gosterebilir; motorun klasoru
# ise kullanicinin dosyalarini tuttugu gercek klasordur (hafiza kalici).
_TABAN_DIZIN = os.path.dirname(os.path.abspath(motor.__file__))
BELLEK_YOLU = os.path.join(_TABAN_DIZIN, "meta3_bellek.json")
OVERRIDE_YOLU = os.path.join(_TABAN_DIZIN, "meta3_override.json")


def kapi_muhru():
    """Butunluk muhru (SHA256) — KAPSAM ACIKCA: motorun 14 kapi sabiti +
    IMMUTABLE_PLANE'in TUM degerleri. (Denetim bulgusu: onceki surumde muhur
    yalniz motor sabitlerini kapsiyordu, plane koruma iddiasi muhurden
    genisti; kapsam esitlendi.)

    Meta katmanlari motora config verir, sabitlere dokunamaz; bu muhur her
    kosuda dogrulanir. Beklenen deger ILK kosuda bellege yazilir ve sonraki
    kosularda karsilastirilir (degistiyse HALT + acik rapor).
    """
    parcalar = []
    for ad in _KAPI_SABITLERI:
        parcalar.append(f"{ad}={getattr(motor, ad)!r}")
    for ad in sorted(IMMUTABLE_PLANE):
        parcalar.append(f"PLANE.{ad}={IMMUTABLE_PLANE[ad]!r}")
    # v1.2 (2. tur denetim): VARYANT UZAYI da muhurlu — dis kurcalama arama
    # uzayini sessizce degistiremesin (filtre listeleri dahil).
    for ad in sorted(VARYANTLAR):
        parcalar.append(f"VAR.{ad}={sorted(VARYANTLAR[ad]['filtreler'])!r}")
    # v1.3 (3. tur denetim): aday listesi _VARYANT_SIRA da muhurlu —
    # arama uzayi liste yoluyla da sessizce bosaltilamaz.
    parcalar.append(f"VARSIRA={_VARYANT_SIRA!r}")
    return hashlib.sha256("|".join(parcalar).encode()).hexdigest()


def kesif_zamani(kosu_sayaci, eps):
    """eps'in FIILI tuketicisi: bu kosuda aday-kesfi yapilacak mi?
    Deterministik hash takvimi (RNG yok — ayni sayac+eps ayni karari verir,
    yeniden uretilebilirlik korunur; HIPOTEZ etiketli tasarim tercihi).
    eps=0.3 -> kosularin ~%30'unda kesif.

    v1.2 (2. tur denetim — eps=0 YUTUCU DURUM giderimi): eps 0'a inse bile
    her `zorunlu_kesif_periyodu` kosuda bir kesif ACILIR — arama kalici
    olarak olemez (PDF #19: repeated failures -> CHANGE SEARCH). Periyot
    HIPOTEZ etiketli plane sabitidir."""
    per = IMMUTABLE_PLANE["zorunlu_kesif_periyodu"]
    if kosu_sayaci > 0 and kosu_sayaci % per == 0:
        return True
    h = int(hashlib.sha256(f"kesif:{kosu_sayaci}".encode()).hexdigest()[:8], 16)
    return (h % 1000) < int(round(eps * 1000))


# --------------------------------------------------------------------
# VARYANT UZAYI (META'nin arama uzayi — PDF #5/#6)
# YAPISAL KURAL: her varyant taban karara yalnizca EK kosul (and) koyar.
# Gevsetme ureten varyant TANIMLANAMAZ — uzay listesi budur, uretici yok.
# Filtre girdileri KOSU ANINDA OLCULEN degerlerdir (golge bayraklari);
# boylece akibet olculdugunde varyantin karsi-olgusal sonucu KESIN olarak
# hesaplanir (varyant = taban islemlerinin alt kumesi).
# --------------------------------------------------------------------
VARYANTLAR = {
    "V0_taban": {
        "aciklama": "v5.4 motoru oldugu gibi (WF+FDR+bootstrap kapilari)",
        "filtreler": [],
    },
    "V1_komposit_teyit": {
        "aciklama": ("taban + bilesik oncu skorun isareti yonle AYNI ve "
                     "kapsam >= 0.5 olmali (yalnizca SIKILASTIRMA)"),
        "filtreler": ["komposit_uyum"],
    },
    "V2_cift_teyit": {
        "aciklama": ("V1 + tick momentum isareti de yonle ayni olmali "
                     "(daha da siki)"),
        "filtreler": ["komposit_uyum", "tick_uyum"],
    },
}
_VARYANT_SIRA = ["V0_taban", "V1_komposit_teyit", "V2_cift_teyit"]


def filtre_gecer(filtre_adi, golge):
    """Golge bayraklarindan filtre karari. Bayrak OLCULEMEDIYSE (None)
    fail-closed: filtre GECMEZ (eksik veriyle sikilastirma gevsetilmez)."""
    deger = golge.get(filtre_adi)
    return deger is True


# --------------------------------------------------------------------
# EXPERIMENT MEMORY (PDF #10/#11) + SANDBOX/VERSIONING (PDF #16)
# --------------------------------------------------------------------
class BellekBozuk(Exception):
    """Bellek dosyasi sema/tip dogrulamasindan gecemedi -> HALT (fail-closed).
    (Kirma-denetimi bulgusu: onceki surum bozuk bellegi dogrulamadan
    kullaniyor ya da yakalanmamis cokme veriyordu.)"""


def _bellek_dogrula(b):
    try:
        assert isinstance(b, dict)
        assert isinstance(b["surum"], int) and b["surum"] >= 1
        assert b["aktif_varyant"] in VARYANTLAR
        assert isinstance(b["eps"], (int, float)) and \
            IMMUTABLE_PLANE["eps_bant"][0] <= b["eps"] <= IMMUTABLE_PLANE["eps_bant"][1]
        assert isinstance(b["W"], int) and \
            IMMUTABLE_PLANE["W_bant"][0] <= b["W"] <= IMMUTABLE_PLANE["W_bant"][1]
        assert isinstance(b["kosu_sayaci"], int) and b["kosu_sayaci"] >= 0
        for alan in ("deneyler", "akibetler", "oneriler", "evrim"):
            assert isinstance(b[alan], list)
        assert isinstance(b["karantina"], dict)
    except (AssertionError, KeyError, TypeError) as e:
        raise BellekBozuk(f"bellek dogrulamasi: {type(e).__name__} {e}") from e
    return b


def _akibet_zinciri(onceki_zincir, kayit):
    """Akibet defteri butunluk zinciri (2. tur KIRMA bulgusu: sahte
    EMIR-ADAYI akibet enjeksiyonu KEEP fabrikleyebiliyordu). Her kayit,
    muhur + onceki halka + kaydin kendisi uzerinden SHA256 halkasi tasir;
    kosu basinda zincir dogrulanir, tutmazsa HALT.

    ACIK SINIR BEYANI (gizlenmez): tuz kod icindedir; dosyaya YAZMA yetkisi
    olan ve bu kodu okuyabilen bir saldirgan zinciri yeniden hesaplayabilir.
    Bu koruma kazara bozulmayi ve kaba kurcalamayi YAKALAR, kararli ic
    saldirgani DURDURAMAZ — dis-sir olmadan dosya duzeyinde kesin butunluk
    matematiksel olarak mumkun degildir (PDF #24 durustlugu)."""
    govde = json.dumps({k: v for k, v in kayit.items() if k != "zincir"},
                       sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(
        f"{kapi_muhru()}|{onceki_zincir}|{govde}".encode()).hexdigest()[:24]


def akibet_zinciri_dogrula(bellek):
    """Tum akibet defterini zincirle dogrular. Donus: (ok, kirik_indeks)."""
    onceki = ""
    for i, a in enumerate(bellek["akibetler"]):
        beklenen = _akibet_zinciri(onceki, a)
        if a.get("zincir") != beklenen:
            return False, i
        onceki = a["zincir"]
    return True, None


def akibet_ekle(bellek, kayit):
    onceki = (bellek["akibetler"][-1]["zincir"]
              if bellek["akibetler"] else "")
    kayit["zincir"] = _akibet_zinciri(onceki, kayit)
    bellek["akibetler"].append(kayit)


def bellek_yukle():
    if not os.path.exists(BELLEK_YOLU):
        # v1.2 (2. tur denetim): .bak varken asil dosyanin yoklugu SESSIZ
        # temiz-baslangic sayilMAZ — kesintili yazim olabilir (K4/K34).
        if os.path.exists(BELLEK_YOLU + ".bak"):
            raise BellekBozuk(
                "asil bellek dosyasi yok ama .bak yedegi var — kesintili "
                "yazim suphesi; .bak elle geri konmali ya da bilerek "
                "silinmeli (sessiz gecmis kaybi yasak)")
        return {
            "surum": 1,
            "kapi_muhru": None,
            "aktif_varyant": "V0_taban",
            "eps": 0.15,          # META baslangic kesif orani (HIPOTEZ)
            "W": 12,              # META2 degerlendirme penceresi (HIPOTEZ)
            "kosu_sayaci": 0,
            "deneyler": [],       # PDF #10 alanlariyla
            "akibetler": [],      # olculmus gercek sonuclar (HESAP VERME)
            "oneriler": [],       # onceki kosunun acik onerileri (akibet bekliyor)
            "evrim": [{"surum": 1, "ebeveyn": None, "varyant": "V0_taban",
                       "neden": "baslangic"}],
            "karantina": {},      # varyant -> ardisik basarisizlik sayisi
        }
    try:
        with open(BELLEK_YOLU, encoding="utf-8") as f:
            veri = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise BellekBozuk(f"bellek okunamadi: {e}") from e
    return _bellek_dogrula(veri)


def bellek_kaydet(bellek):
    # PDF #16: once anlik goruntu (.bak), sonra yaz — yazim yarida kalirsa
    # onceki surum geri alinabilir (ROLLBACK).
    if os.path.exists(BELLEK_YOLU):
        os.replace(BELLEK_YOLU, BELLEK_YOLU + ".bak")
    with open(BELLEK_YOLU, "w", encoding="utf-8") as f:
        json.dump(bellek, f, ensure_ascii=False, indent=1)


def deney_kaydi(bellek, optimizer, hipotez, patch, metrikler, maliyet_sn,
                risk, karar, gecikme_sn=0.0):
    """PDF #10'un zorunlu alanlariyla deney kaydi.
    cost = kosu suresi (sn), latency = veri yasi (sn) — iki AYRI olcum
    (denetim bulgusu: onceki surumde latency cost kopyasiydi)."""
    kayit = {
        "experiment_id": f"E{len(bellek['deneyler']) + 1:05d}",
        "parent_version": bellek["surum"],
        "optimizer_version": optimizer,     # "meta" | "meta2" | "meta3"
        "hypothesis": hipotez,
        "patch": patch,                     # config degisikligi (kod DEGIL)
        "metrics": metrikler,
        # v1.2: olculmemis maliyet/gecikme 0.0 DEGIL None yazilir (VERI YOK)
        "cost": None if maliyet_sn is None else round(maliyet_sn, 3),
        "latency": None if gecikme_sn is None else round(gecikme_sn, 3),
        "risk": risk,                       # basit sinif etiketi (PDF #12):
                                            # veri_yetersiz|olcum_ustun_degil|...
        "decision": karar,                  # KEEP|REJECT|HOLD|ROLLBACK|STOP|TUT
    }
    bellek["deneyler"].append(kayit)
    return kayit


# --------------------------------------------------------------------
# EVALUATOR (PDF #4) — IMMUTABLE; recursive katmanlar cagirir ama DEGISTIREMEZ
# --------------------------------------------------------------------
def degerlendir(Q, R, S, C, L):
    """J = wQ*Q + wR*R + wS*S - wC*C - wL*L  (PDF #4 formulu).

    Q: olculmus kalite (oncelik: gercek akibet ortalama R'si; yoksa OOS ort.)
    R: saglamlik = 1 - bootstrap p_max (olculen)
    S: guvenlik = kapilar/muhur ihlalsiz mi (1.0 / 0.0)
    C: maliyet = kosu suresi / 60 sn (olculen, normalize)
    L: gecikme = veri yasi / 3600 sn (olculen, normalize)
    Bilesenlerden herhangi biri OLCULEMEDIYSE None gecilir ve J=None doner
    (uydurma bileşenle skor uretilmez — fail-closed)."""
    if any(x is None for x in (Q, R, S, C, L)):
        return None
    P = IMMUTABLE_PLANE
    return (P["w_Q"] * Q + P["w_R"] * R + P["w_S"] * S
            - P["w_C"] * C - P["w_L"] * L)


# --------------------------------------------------------------------
# HESAP VERME — onceki kosunun onerilerinin GERCEK akibeti (Q'nun zemini)
# Kurallar muhafazakar (repo sozlesmesi): ayni barda stop+hedef -> STOP;
# giris dolumu bar araligiyla; tetiklenmemis oneri IPTAL, R yazilmaz.
# --------------------------------------------------------------------
def akibet_olc(oneri, df_15m):
    """oneri: {sembol, yon, giris, stop, hedef, bar_ts(ms), etiket}
    df_15m: guncel 15M kline (kapanmis barlar). Donus: dict ya da None
    (yeni bar yoksa None = henuz olculemiyor)."""
    giris, stop, hedef = oneri["giris"], oneri["stop"], oneri["hedef"]
    yon = oneri["yon"]
    # Kirma-denetimi bulgusu: sonlu olmayan seviye (NaN/inf) R'yi sessizce
    # zehirliyordu. Gecersiz oneri OLCULMEZ ve acikca isaretlenir.
    if not all(np.isfinite(x) for x in (giris, stop, hedef)) \
            or yon not in ("LONG", "SHORT"):
        return {"sonuc": "GECERSIZ", "r": None}
    # v1.5 (canli kosu bulgusu — kullanicinin ilk META3 kosusu): hedefi yonun
    # TERS tarafinda olan oneri OLCULMEZ. Ters geometri (SHORT'ta giris ustu
    # hedef) ilk barda sahte HEDEF uretir ve akibet defterini zehirler.
    # Dogru geometri: LONG stop < giris < hedef; SHORT hedef < giris < stop.
    if yon == "LONG" and not (stop < giris < hedef):
        return {"sonuc": "GECERSIZ", "r": None}
    if yon == "SHORT" and not (hedef < giris < stop):
        return {"sonuc": "GECERSIZ", "r": None}
    barlar = df_15m[df_15m.index > pd.Timestamp(oneri["bar_ts"], unit="ms",
                                                tz="UTC")]
    if barlar.empty:
        return None
    dolum = False
    for ts, bar in barlar.iterrows():
        lo, hi = float(bar["low"]), float(bar["high"])
        if not np.isfinite(lo) or not np.isfinite(hi):
            continue
        if not dolum:
            # Yon-duyarli limit dolumu (denetim bulgusu: aralik-icerme sarti
            # gap'ten gecen dolumu kaciriyordu). LONG alis limiti: fiyat
            # girise/altina degdiyse dolar (lo <= giris); SHORT satis
            # limiti: fiyat girise/ustune degdiyse dolar (hi >= giris).
            if (yon == "LONG" and lo <= giris) or \
                    (yon == "SHORT" and hi >= giris):
                dolum = True
                dolum_bari = True
            else:
                continue
        else:
            dolum_bari = False
        # Dolumdan sonra: STOP kontrolu HER barda (dolum bari dahil —
        # muhafazakar). HEDEF ise dolum barinda SAYILMAZ (v1.2, 2. tur
        # denetim bulgusu: bar-ici sira bilinmezken dolum+hedef ayni barda
        # HEDEF yazmak iyimserdi); hedef ancak SONRAKI barlarda olculur.
        if yon == "LONG":
            if lo <= stop:
                return {"sonuc": "STOP", "r": -1.0}
            if not dolum_bari and hi >= hedef:
                return {"sonuc": "HEDEF",
                        "r": round(abs(hedef - giris) /
                                   max(abs(giris - stop), 1e-9), 3)}
        else:
            if hi >= stop:
                return {"sonuc": "STOP", "r": -1.0}
            if not dolum_bari and lo <= hedef:
                return {"sonuc": "HEDEF",
                        "r": round(abs(giris - hedef) /
                                   max(abs(stop - giris), 1e-9), 3)}
    if not dolum:
        # TIME_STOP_BARS kadar bar gectiyse dolmayan emir IPTAL (R yazilmaz)
        if len(barlar) >= motor.TIME_STOP_BARS:
            return {"sonuc": "IPTAL", "r": None}
        return None  # hala bekliyor
    return None      # dolum var, sonuc yok — acik pozisyon, olcum surer


def teyitli_swingler(df_15m, sol=2, sag=2):
    """Teyitli fraktal swingler (v1.5). sol/sag=2 HIPOTEZ etiketli.
    Bir bar tepe sayilir: high'i solundaki `sol` ve sagindaki `sag` barin
    high'larindan buyuk-esitse; dip icin simetrik. Sagindaki barlar KAPANMIS
    oldugu icin teyit lookahead icermez; son `sag` bar teyitsizdir ve
    yapisal olarak taranamaz (dogru davranis)."""
    hi = df_15m["high"].to_numpy(dtype=float)
    lo = df_15m["low"].to_numpy(dtype=float)
    n = len(hi)
    tepeler, dipler = [], []
    for i in range(sol, n - sag):
        pencere_hi = hi[i - sol:i + sag + 1]
        pencere_lo = lo[i - sol:i + sag + 1]
        if np.isfinite(hi[i]) and hi[i] == np.max(pencere_hi):
            tepeler.append(float(hi[i]))
        if np.isfinite(lo[i]) and lo[i] == np.min(pencere_lo):
            dipler.append(float(lo[i]))
    return tepeler, dipler


def bilgi_hedefi(yon, giris, df_15m, pencere=200):
    """v1.5 (canli kosu bulgusu): BILGI seviyelerinin hedefi artik SMA20
    DEGIL — SMA20 hedefi yalniz z-ekstrem tetiginde anlamlidir; rejim-yonu
    seviyelerinde cogu zaman yonun TERS tarafina dusuyordu (kullanicinin
    ilk kosusunda 8/12 sembolde ters hedef olculdu).

    Yeni kural (STRATEJI.md sozlesmesiyle uyumlu: 'R kati uydurma hedef
    uretilmez'): hedef = yon tarafinda girisin OTESINDEKI EN YAKIN teyitli
    swing (SHORT: girisin altindaki en yakin teyitli dip; LONG: girisin
    ustundeki en yakin teyitli tepe). Son `pencere` bar taranir (HIPOTEZ).
    Yon tarafinda teyitli swing yoksa None doner — uydurma hedef basilmaz."""
    kesit = df_15m.iloc[-pencere:] if len(df_15m) > pencere else df_15m
    tepeler, dipler = teyitli_swingler(kesit)
    if yon == "LONG":
        adaylar = [t for t in tepeler if t > giris]
        return min(adaylar) if adaylar else None
    if yon == "SHORT":
        adaylar = [d for d in dipler if d < giris]
        return max(adaylar) if adaylar else None
    return None


# --------------------------------------------------------------------
# AGENT KATMANI (PDF #3) — v5.4 motorunun VERI donduren sarmali
# signal_engine print-tabanli oldugundan ayni olcum bloklari burada VERI
# olarak uretilir. Formuller v5.4 ile BIREBIR aynidir (test dosyasi iki
# yolun ayni sayilari urettigini assert eder — kopya sapmasi kaniti).
# --------------------------------------------------------------------
def karar_uret(symbol, df_4h, df_15m, btc_4h, btc_15m):
    """Tek sembol icin olculmus karar verisi. Donus dict:
    yon, yon_kaynak, kapi (ACIK/KAPALI/VETO), kapi_gerekce, giris, stop,
    hedef, etiket (EMIR-ADAYI/BILGI), kural, oos, p_max, golge (varyant
    bayraklari), bar_ts, ek olculer."""
    t0 = time.monotonic()
    sonuc = {"sembol": symbol, "yon": "NOTR", "yon_kaynak": "VERI YOK",
             "kapi": "KAPALI", "kapi_gerekce": "", "etiket": "BILGI",
             "giris": None, "stop": None, "hedef": None, "kural": None,
             "oos": None, "p_max": None, "golge": {}, "bar_ts": None}

    state, conf = motor.regime_detector(df_15m["close"], df_4h["close"])
    btc_state, _ = motor.regime_detector(btc_15m["close"], btc_4h["close"])

    # --- YON (bias) — ZORUNLU, asla gizlenmez ---------------------------
    # Oncelik sirasi (HIPOTEZ etiketli siralama; her aday OLCULMUS deger):
    #  1) rejim BULL/BEAR  2) 4H EMA50-EMA200 egiminin isareti (CALM'da)
    #  3) bilesik oncu skorun isareti (kapsam>=0.5 ise)  4) NOTR (gercek 0)
    ef = df_4h["close"].ewm(span=50, adjust=False).mean()
    es = df_4h["close"].ewm(span=200, adjust=False).mean()
    egim = float(((ef - es) / df_4h["close"]).iloc[-1])
    if state == "BULL":
        sonuc["yon"], sonuc["yon_kaynak"] = "LONG", f"rejim BULL (guven={conf:.2f})"
    elif state == "BEAR":
        sonuc["yon"], sonuc["yon_kaynak"] = "SHORT", f"rejim BEAR (guven={conf:.2f})"
    elif abs(egim) > 1e-12:
        sonuc["yon"] = "LONG" if egim > 0 else "SHORT"
        sonuc["yon_kaynak"] = (f"rejim {state}; 4H EMA50-EMA200 egimi "
                               f"{egim:+.5f} (zayif kanit — bilgi)")
    # (3/4 asagida, komposit hesaplandiktan sonra tamamlanir)

    # --- oncu katman olcumleri (v5.4 ile ayni fonksiyonlar) -------------
    trades = motor.fetch_recent_trades(symbol)
    bids, asks = motor.fetch_order_book(symbol)
    fr_df, oi = motor.fetch_funding_oi(symbol)
    fr_latest = 0.0
    fr_var = (not fr_df.empty) and ("fundingRate" in fr_df.columns)
    if fr_var:
        fr_latest = float(fr_df["fundingRate"].iloc[-1])
    score15, note15 = motor.pump_anomaly(df_15m["volume"])
    yon_pd, yon_move = motor.pump_dump_direction(trades, df_15m["close"])
    tscore = motor.tick_confirm_score(symbol, trades)
    obi_var = (bids is not None and asks is not None
               and not bids.empty and not asks.empty)
    komp = motor.composite_leading_score({
        "pump_skor": score15, "pump_not": note15, "tick_z": tscore,
        "obi": motor.lob_imbalance(bids, asks)[0] if obi_var else None,
        "funding": fr_latest if fr_var else None,
        "oi": oi if np.isfinite(oi) else None,
        "yon_move": yon_move,
    })
    sonuc["komposit"] = komp

    if sonuc["yon"] == "NOTR":
        if komp.get("skor") is not None and komp.get("kapsam", 0) >= 0.5 \
                and abs(komp["skor"]) > 1e-12:
            sonuc["yon"] = "LONG" if komp["skor"] > 0 else "SHORT"
            sonuc["yon_kaynak"] = (f"bilesik oncu skor {komp['skor']:+.2f} "
                                   f"(kapsam {komp['kapsam']:.2f}; zayif kanit)")
        else:
            sonuc["yon_kaynak"] = ("gercek berabere: rejim CALM, egim ~0, "
                                   "komposit olculemedi/sifir")

    # --- GOLGE BAYRAKLARI (varyant filtreleri icin; kosu aninda olculur) -
    yon_isaret = {"LONG": 1.0, "SHORT": -1.0}.get(sonuc["yon"], 0.0)
    if komp.get("skor") is not None and komp.get("kapsam", 0) >= 0.5:
        sonuc["golge"]["komposit_uyum"] = (komp["skor"] * yon_isaret) > 0
    else:
        sonuc["golge"]["komposit_uyum"] = None   # olculemedi -> fail-closed
    if abs(yon_move) > 1e-12:
        sonuc["golge"]["tick_uyum"] = (yon_move * yon_isaret) > 0
    else:
        sonuc["golge"]["tick_uyum"] = None

    # --- SEVIYELER — HER KOSUDA (olculen yapidan; uydurma yok) ----------
    close = df_15m["close"].astype(float)
    sma20 = close.rolling(window=20).mean()
    sd20 = close.rolling(window=20).std(ddof=0)
    z_ser = ((close - sma20) / (sd20 + 1e-12)).shift(periods=1)
    hl = (df_15m["high"] - df_15m["low"]).abs()
    hc = (df_15m["high"] - close.shift(periods=1)).abs()
    lc = (df_15m["low"] - close.shift(periods=1)).abs()
    tr_df = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr_ser = tr_df.rolling(motor.ATR_LEN).mean().shift(periods=1)
    son_kapanis = float(close.iloc[-1])
    atr_i = float(atr_ser.iloc[-1]) if np.isfinite(atr_ser.iloc[-1]) else None
    if atr_i is not None and yon_isaret != 0.0:
        # v1.5: BILGI hedefi teyitli swingden (yon tarafinda, girisin
        # otesinde). SMA20 hedefi BILGI seviyelerinden KALDIRILDI — canli
        # kosuda 8/12 sembolde yonun ters tarafina dustugu olculdu.
        hedef_px = bilgi_hedefi(sonuc["yon"], son_kapanis, df_15m)
        sonuc["giris"] = son_kapanis
        sonuc["stop"] = (son_kapanis - motor.ATR_SL_MULT * atr_i
                         if sonuc["yon"] == "LONG"
                         else son_kapanis + motor.ATR_SL_MULT * atr_i)
        if hedef_px is not None:
            sonuc["hedef"] = hedef_px
            sonuc["bar_ts"] = int(df_15m.index[-1].value // 1_000_000)
            sonuc["r"] = round(abs(hedef_px - son_kapanis)
                               / max(abs(sonuc["stop"] - son_kapanis), 1e-12), 2)
        else:
            sonuc["hedef_gerekce"] = ("yon tarafinda teyitli swing yok — "
                                      "uydurma hedef basilmaz (STRATEJI.md)")

    # --- VETO / KAPI zinciri (v5.4 signal_engine ile ayni sira) ---------
    note = note15
    if note15 in ("NORMAL", "WATCH") and tscore is not None \
            and note15 == "WATCH" and tscore >= motor.PUMP_TICK_WATCH:
        note = "PUMP_OR_DUMP_RISK"
    if note == "PUMP_OR_DUMP_RISK":
        sonuc["kapi"], sonuc["kapi_gerekce"] = "VETO", \
            f"pump/dump vetosu (score={score15:.2f}, yon={yon_pd})"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    if symbol != "BTC/USDT" and state in ("BULL", "BEAR") \
            and btc_state != state:
        sonuc["kapi_gerekce"] = f"BTC {btc_state} ile {state} uyumsuz"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    direction = "LONG" if state == "BULL" else \
        "SHORT" if state == "BEAR" else None
    if direction is None:
        sonuc["kapi_gerekce"] = "rejim CALM/UNKNOWN — istatistik kapisi acilmadi"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc

    # --- WF + FDR + bootstrap (v5.4 ile birebir ayni mekanik) -----------
    df = df_15m.copy()
    df["z"] = z_ser
    df["atr"] = atr_ser
    df["rsi"] = motor.wilder_rsi(close, motor.RSI_LEN)
    df["target"] = sma20
    df = df.dropna(subset=["z", "atr", "rsi"])
    if len(df) < 700:
        sonuc["kapi_gerekce"] = f"yetersiz veri ({len(df)} mum)"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    feat = {k: df[k].to_numpy(dtype=float) for k in
            ["open", "close", "low", "high", "z", "atr", "rsi"]}
    rule_grid = [(zt, ro) for zt in motor.Z_GRID for ro in (False, True)]
    rule_trades = {rule: [] for rule in rule_grid}
    folds = 0
    for tr_idx, te_idx in motor.walkforward_splits(len(df), motor.N_FOLDS,
                                                   motor.EMBARGO):
        for rule in rule_grid:
            zt, ro = rule
            rule_trades[rule].extend(motor.simulate(feat, te_idx, zt, ro,
                                                    direction))
        folds += 1
    if folds == 0:
        sonuc["kapi_gerekce"] = "walk-forward split yok"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    stats = {rule: motor.oos_stats(rule_trades[rule]) for rule in rule_grid}
    pvals = {r: 2.0 * (1.0 - motor.norm_cdf(abs(s["t"])))
             for r, s in stats.items() if s is not None}
    if not pvals:
        sonuc["kapi_gerekce"] = "yeterli OOS islem yok"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    keys = list(pvals.keys())
    accepted = motor.fdr_bh([pvals[k] for k in keys], motor.ALPHA)
    accepted_rules = [r for r, ok in zip(keys, accepted) if ok]
    p_max = motor.bootstrap_max_t(rule_trades)
    sonuc["p_max"] = p_max
    if not accepted_rules or p_max >= motor.ALPHA:
        sonuc["kapi_gerekce"] = (f"anti-overfit kapi kapali "
                                 f"(kabul={len(accepted_rules)}, p={p_max:.3f})")
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    best_rule = max(accepted_rules, key=lambda r: stats[r]["mean"])
    best_z, best_rsi = best_rule
    sonuc["kural"] = f"z={best_z}" + ("+RSI" if best_rsi else "")
    sonuc["oos"] = stats[best_rule]
    cur, prev = df.iloc[-1], df.iloc[-2]
    zi, rsi_i = float(cur["z"]), float(cur["rsi"])
    if direction == "LONG":
        fired = (zi <= -best_z) and (zi > -4.0) and (float(prev["z"]) < zi) \
            and (zi > float(np.min(df["z"].iloc[-4:-1])))
    else:
        fired = (zi >= best_z) and (zi < 4.0) and (float(prev["z"]) > zi) \
            and (zi < float(np.max(df["z"].iloc[-4:-1])))
    if fired and best_rsi:
        rsi_ok = np.isfinite(rsi_i) and (
            rsi_i < motor.RSI_LONG_MAX if direction == "LONG"
            else rsi_i > motor.RSI_SHORT_MIN)
        if not rsi_ok:
            fired = False
            sonuc["kapi_gerekce"] = (f"z sarti sagladi ama RSI sarti "
                                     f"saglanmadi (rsi={rsi_i:.1f})")
    if fired:
        sonuc["kapi"] = "ACIK"
        sonuc["etiket"] = "EMIR-ADAYI"
        sonuc["kapi_gerekce"] = (f"WF+FDR+bootstrap onayli; kural="
                                 f"{sonuc['kural']}, z={zi:.2f}")
        # kapi acikken giris/stop v5.4'un canli tetik hesabiyla ayni.
        # Hedef = SMA20 (motorun z=0 cikisi): z-EKSTREM tetiginde SMA
        # tanimi geregi yonun DOGRU tarafindadir (LONG tetigi z<=-esik'te
        # atesler -> fiyat SMA'nin altinda -> hedef ustte). v1.5 guvence:
        # yine de ters dusen (teorik) hedef EMIR-ADAYI'yi BILGI'ye dusurur.
        sonuc["giris"] = float(cur["close"])
        sonuc["stop"] = (sonuc["giris"] - motor.ATR_SL_MULT * float(cur["atr"])
                         if direction == "LONG"
                         else sonuc["giris"] + motor.ATR_SL_MULT * float(cur["atr"]))
        sonuc["hedef"] = float(cur["target"])
        sonuc["yon"] = direction
        sonuc["yon_kaynak"] = f"rejim {state} + tetik ({sonuc['kural']})"
        hedef_dogru = (sonuc["hedef"] > sonuc["giris"] if direction == "LONG"
                       else sonuc["hedef"] < sonuc["giris"])
        if hedef_dogru:
            sonuc["r"] = round(abs(sonuc["hedef"] - sonuc["giris"])
                               / max(abs(sonuc["stop"] - sonuc["giris"]),
                                     1e-12), 2)
            sonuc["bar_ts"] = int(df.index[-1].value // 1_000_000)
        else:
            sonuc["kapi"] = "KAPALI"
            sonuc["etiket"] = "BILGI"
            sonuc["hedef"] = None
            sonuc["kapi_gerekce"] += (" | hedef (SMA20) yonun ters tarafina "
                                      "dustu — emir-adayi dusuruldu "
                                      "(fail-closed)")
    elif not sonuc["kapi_gerekce"]:
        sonuc["kapi_gerekce"] = (f"kenar onayli; tetik yok (z={zi:.2f}, "
                                 f"esik={best_z}, kural={sonuc['kural']})")
    sonuc["sure_sn"] = time.monotonic() - t0
    return sonuc


def varyant_karari(karar, varyant_adi):
    """Aktif varyantin filtrelerini taban karara uygular (yalnizca
    SIKILASTIRMA: kapi ACIKsa kapatabilir, KAPALIYI ACAMAZ)."""
    if karar["kapi"] != "ACIK":
        return karar, []
    dusen = []
    for f in VARYANTLAR[varyant_adi]["filtreler"]:
        if not filtre_gecer(f, karar["golge"]):
            dusen.append(f)
    if dusen:
        karar = dict(karar)
        karar["kapi"] = "KAPALI"
        karar["etiket"] = "BILGI"
        karar["kapi_gerekce"] += (f" | varyant {varyant_adi} filtresi dusurdu: "
                                  f"{','.join(dusen)} (sikilastirma)")
    return karar, dusen


# --------------------------------------------------------------------
# META (PDF #6) — varyant secimi, KEEP/REJECT/ROLLBACK; olcum = akibet
# --------------------------------------------------------------------
def _varyant_akibet_ozeti(bellek, varyant_adi):
    """Bir varyantin karsi-olgusal akibet ozeti: taban onerilerin olculmus
    R'leri uzerinden, o varyantin golge bayraklariyla ALACAGI alt kume.

    POPULASYON SAFLIGI (denetim bulgusu): yalniz kapi-onayli EMIR-ADAYI
    etiketli onerilerin akibeti sayilir — BILGI seviyeleri yon-kalitesi
    raporu icin tutulur ama varyant SECIMINE girmez (varyantin gercekte
    isleme cevirecegi populasyon EMIR-ADAYI'dir). Sonlu olmayan R atilir."""
    rler = []
    for a in bellek["akibetler"]:
        r = a.get("r")
        if r is None or not np.isfinite(r):
            continue
        if not str(a.get("etiket", "")).startswith("EMIR-ADAYI"):
            continue
        golge = a.get("golge", {})
        alir = all(filtre_gecer(f, golge)
                   for f in VARYANTLAR[varyant_adi]["filtreler"])
        if alir:
            rler.append(float(r))
    if not rler:
        return {"n": 0, "ort_r": None}
    return {"n": len(rler), "ort_r": float(np.mean(rler))}


def meta_dongusu(bellek, kosu_suresi_sn, veri_yasi_sn, guvenlik_ok=True):
    """PDF #6: analyze -> hypothesis -> (config) patch -> evaluate ->
    keep/reject. Donus: (karar_str, detay).

    v1.1 denetim duzeltmeleri:
    - eps FIILEN OKUNUR: aday-kesfi kesif_zamani(kosu_sayaci, eps) ile
      kapilanir (olu parametre bulgusu kapatildi; META2->META halkasi gercek).
    - J hesaplanamiyorsa (bilesen VERI YOK) karar REJECT DEGIL HOLD'dur ve
      karantina ARTMAZ (olculmemis ret yasagi — K34).
    - Butce bitince kalan adaylar icin STOP kaydi dusulur (PDF #19 budget
      exhausted dali gorunur).
    """
    P = IMMUTABLE_PLANE
    aktif = bellek["aktif_varyant"]
    # v1.2 (2. tur denetim — S bileseni artik OLCULUYOR): ic denetim ihlali
    # varsa S=0 -> bu kosuda KEEP/REJECT verilemez (PDF #19 safety dali);
    # kayit "guvenlik" sinifiyla dusulur.
    if not guvenlik_ok:
        deney_kaydi(bellek, "meta",
                    "ic denetim ihlali: S=0 — bu kosuda varyant karari yok",
                    {}, {"S": 0.0}, kosu_suresi_sn, "guvenlik", "HOLD",
                    veri_yasi_sn)
        return "HOLD", "ic denetim ihlali (S=0) — evaluator guvenlik dali"
    ozet_aktif = _varyant_akibet_ozeti(bellek, aktif)
    C = min(kosu_suresi_sn / 60.0, 10.0)
    L = min(veri_yasi_sn / 3600.0, 10.0)

    if ozet_aktif["n"] < P["min_akibet_n"]:
        deney_kaydi(bellek, "meta",
                    f"aktif {aktif}: olculmus akibet n={ozet_aktif['n']} < "
                    f"{P['min_akibet_n']}",
                    {"varyant": aktif}, {"akibet": ozet_aktif},
                    kosu_suresi_sn, "veri_yetersiz", "HOLD", veri_yasi_sn)
        return "HOLD", (f"olculmus akibet yetersiz "
                        f"(n={ozet_aktif['n']}/{P['min_akibet_n']}) — "
                        f"evaluator kararsiz, degisiklik yok (fail-closed)")

    en_iyi = (aktif, ozet_aktif)
    kesif = kesif_zamani(bellek["kosu_sayaci"], bellek["eps"])
    if not kesif:
        deney_kaydi(bellek, "meta",
                    f"kesif takvimi kapali (eps={bellek['eps']:.2f}, "
                    f"kosu #{bellek['kosu_sayaci']}) — aday degerlendirilmedi",
                    {}, {"eps": bellek["eps"]},
                    kosu_suresi_sn, "kesif_kapali", "TUT", veri_yasi_sn)
    else:
        adaylar = [v for v in _VARYANT_SIRA if v != aktif and
                   bellek["karantina"].get(v, 0) < P["karantina_esigi"]]
        degerlendirilen = 0
        for aday in adaylar:
            # NOT (2. tur denetim): 3-varyantli mevcut uzayda aday tavani
            # butceye esit oldugundan bu dal FIILEN erisilmez; uzay
            # buyurse calisir (olculerek gosterildi). Beyanli olu dal.
            if degerlendirilen >= P["kosu_basi_deney_butcesi"]:
                deney_kaydi(bellek, "meta",
                            f"kosu-basi deney butcesi bitti; {aday} bu "
                            f"kosuda degerlendirilmedi",
                            {"varyant": aday}, {},
                            kosu_suresi_sn, "butce", "STOP", veri_yasi_sn)
                continue
            ozet = _varyant_akibet_ozeti(bellek, aday)
            degerlendirilen += 1
            if ozet["n"] < P["min_akibet_n"]:
                deney_kaydi(bellek, "meta",
                            f"aday {aday}: karsi-olgusal n={ozet['n']} "
                            f"yetersiz", {"varyant": aday}, {"akibet": ozet},
                            kosu_suresi_sn, "veri_yetersiz", "HOLD",
                            veri_yasi_sn)
                continue
            R_bilesen = (None if bellek.get("_son_p_max") is None
                         else 1.0 - bellek["_son_p_max"])
            J_aday = degerlendir(ozet["ort_r"], R_bilesen, 1.0, C, L)
            J_iyi = degerlendir(en_iyi[1]["ort_r"], R_bilesen, 1.0, C, L)
            if J_aday is None or J_iyi is None:
                # OLCULMEMIS RET YASAK: J hesaplanamadi -> HOLD, karantina
                # ARTMAZ (denetim bulgusu kapatildi).
                deney_kaydi(bellek, "meta",
                            f"{aday}: J hesaplanamadi (bilesen VERI YOK) — "
                            f"ret DEGIL, beklemede",
                            {"varyant": aday}, {"akibet": ozet, "J": None},
                            kosu_suresi_sn, "veri_yetersiz", "HOLD",
                            veri_yasi_sn)
                continue
            if J_aday > J_iyi:
                eski_iyi_ad = en_iyi[0]
                en_iyi = (aday, ozet)
                deney_kaydi(bellek, "meta",
                            f"{aday} J={J_aday:.3f} > {eski_iyi_ad} "
                            f"J={J_iyi:.3f} (olculmus ustunluk)",
                            {"varyant": aday},
                            {"akibet": ozet, "J": round(J_aday, 3),
                             "J_kiyas": round(J_iyi, 3)},
                            kosu_suresi_sn, "olcum_ustun", "KEEP",
                            veri_yasi_sn)
            else:
                bellek["karantina"][aday] = \
                    bellek["karantina"].get(aday, 0) + 1
                deney_kaydi(bellek, "meta",
                            f"{aday} J={J_aday:.3f} <= {en_iyi[0]} "
                            f"J={J_iyi:.3f} (olcumde ustun degil)",
                            {"varyant": aday},
                            {"akibet": ozet, "J": round(J_aday, 3),
                             "J_kiyas": round(J_iyi, 3)},
                            kosu_suresi_sn, "olcum_ustun_degil", "REJECT",
                            veri_yasi_sn)
    if en_iyi[0] != aktif:
        bellek["surum"] += 1
        bellek["evrim"].append({"surum": bellek["surum"],
                                "ebeveyn": bellek["surum"] - 1,
                                "varyant": en_iyi[0],
                                "neden": "meta KEEP (olculmus J ustunlugu)"})
        bellek["aktif_varyant"] = en_iyi[0]
        bellek["karantina"][en_iyi[0]] = 0
        return "KEEP", f"aktif varyant {aktif} -> {en_iyi[0]} (olcumle)"
    # gerileme kontrolu: aktif varyant tabandan olcumle kotuyse ROLLBACK
    taban = _varyant_akibet_ozeti(bellek, "V0_taban")
    if aktif != "V0_taban" and taban["n"] >= P["min_akibet_n"] \
            and ozet_aktif["ort_r"] is not None \
            and taban["ort_r"] is not None \
            and ozet_aktif["ort_r"] < taban["ort_r"]:
        bellek["surum"] += 1
        bellek["evrim"].append({"surum": bellek["surum"],
                                "ebeveyn": bellek["surum"] - 1,
                                "varyant": "V0_taban",
                                "neden": "ROLLBACK (aktif, tabandan olcumle kotu)"})
        bellek["aktif_varyant"] = "V0_taban"
        deney_kaydi(bellek, "meta", f"{aktif} tabandan kotu: "
                    f"{ozet_aktif['ort_r']:.3f} < {taban['ort_r']:.3f}",
                    {"varyant": "V0_taban"},
                    {"aktif": ozet_aktif, "taban": taban},
                    kosu_suresi_sn, "olculmus_gerileme", "ROLLBACK",
                    veri_yasi_sn)
        return "ROLLBACK", f"{aktif} -> V0_taban (olculmus gerileme)"
    return "TUT", f"aktif {aktif} korunuyor (olcumle ustun ya da esit)"


# --------------------------------------------------------------------
# META2 (PDF #7) ve META3 (PDF #8) — ust katmanlar, dusuk frekans
# Yalnizca IMMUTABLE bantlar icinde, OLCUME dayali ayar; her karar kayitli.
# --------------------------------------------------------------------
def meta2_dongusu(bellek):
    P = IMMUTABLE_PLANE
    W = bellek["W"]
    if bellek["kosu_sayaci"] % W != 0 or bellek["kosu_sayaci"] == 0:
        return None
    son = [d for d in bellek["deneyler"] if d["optimizer_version"] == "meta"][-3 * W:]
    kesifler = [d for d in son if d["decision"] in ("KEEP", "REJECT")]
    if len(kesifler) < P["meta2_min_orneklem"]:
        deney_kaydi(bellek, "meta2", "kesif orneklemi yetersiz", {},
                    {"n": len(kesifler)}, None, "veri_yetersiz", "HOLD", None)
        return "HOLD"
    verim = sum(1 for d in kesifler if d["decision"] == "KEEP") / len(kesifler)
    eski = bellek["eps"]
    # verim yuksekse kesif artar, dusukse azalir — bant DISINA CIKAMAZ
    # (esik/adim sabitleri IMMUTABLE_PLANE'de, HIPOTEZ etiketli)
    adim = P["meta2_adim"] if verim > P["meta2_verim_esigi"] else -P["meta2_adim"]
    yeni = min(max(eski + adim, P["eps_bant"][0]), P["eps_bant"][1])
    bellek["eps"] = round(yeni, 4)
    deney_kaydi(bellek, "meta2",
                f"kesif verimi {verim:.2f} -> eps {eski:.2f}->{yeni:.2f} "
                f"(bant {P['eps_bant']})", {"eps": bellek["eps"]},
                {"verim": round(verim, 3)}, None, "olcum",
                "KEEP" if yeni != eski else "TUT")
    return "KEEP" if yeni != eski else "TUT"


def meta3_dongusu(bellek):
    P = IMMUTABLE_PLANE
    W = bellek["W"]
    if bellek["kosu_sayaci"] % (W * W) != 0 or bellek["kosu_sayaci"] == 0:
        return None
    m2 = [d for d in bellek["deneyler"] if d["optimizer_version"] == "meta2"]
    if len(m2) < P["meta3_min_orneklem"]:
        deney_kaydi(bellek, "meta3", "meta2 orneklemi yetersiz", {},
                    {"n": len(m2)}, None, "veri_yetersiz", "HOLD", None)
        return "HOLD"
    # meta2 kararlari hep TUT ise pencere buyutulur (daha seyrek, daha ucuz),
    # sik KEEP ise kucultulur — bant DISINA CIKAMAZ. NOT (beyanli daraltma):
    # PDF #20'nin verimlilik FORMULLERI degil, yonu uygulanir — karar-sayisi
    # sezgiseli (adim sabitleri IMMUTABLE_PLANE'de, HIPOTEZ etiketli).
    son3 = [d["decision"] for d in m2[-P["meta3_min_orneklem"]:]]
    eski = bellek["W"]
    if all(k == "TUT" for k in son3):
        yeni = min(eski + P["meta3_adim_buyut"], P["W_bant"][1])
    elif son3.count("KEEP") >= 2:
        yeni = max(eski - P["meta3_adim_kucult"], P["W_bant"][0])
    else:
        yeni = eski
    bellek["W"] = yeni
    deney_kaydi(bellek, "meta3",
                f"meta2 son3={son3} -> W {eski}->{yeni} (bant {P['W_bant']})",
                {"W": yeni}, {"son3": son3}, None, "olcum",
                "KEEP" if yeni != eski else "TUT")
    return "KEEP" if yeni != eski else "TUT"


# --------------------------------------------------------------------
# IC DENETCI (kosu ici; PDF AUDIT + kullanicinin denetci sarti)
# Kosu bittikten sonra kaydi denetler; kritik ihlalde EMIR-ADAYI etiketleri
# MUHURLENIR (fail-closed: BILGI'ye dusurulur) ve ihlal ACIKCA basilir.
# --------------------------------------------------------------------
def ic_denetim(bellek, kararlar, muhur_ok):
    ihlaller = []
    if not muhur_ok:
        ihlaller.append("MUHUR: kapi sabitleri degismis (HALT gerektirir)")
    for k in kararlar:
        if k["yon"] not in ("LONG", "SHORT", "NOTR"):
            ihlaller.append(f"{k['sembol']}: yon alani bozuk")
        if k["yon"] == "NOTR" and "berabere" not in k["yon_kaynak"] \
                and "VERI YOK" not in k["yon_kaynak"]:
            ihlaller.append(f"{k['sembol']}: NOTR gerekcesiz (yon gizlenemez)")
        if k["etiket"] == "EMIR-ADAYI" and k["kapi"] != "ACIK":
            ihlaller.append(f"{k['sembol']}: kapi acik degilken EMIR-ADAYI")
    # bellek tutarliligi: son meta KEEP kayitlari J olcumu tasimali
    for d in bellek["deneyler"][-10:]:
        if d["optimizer_version"] == "meta" and d["decision"] == "KEEP" \
                and "J" not in d["metrics"] and "akibet" not in d["metrics"]:
            ihlaller.append(f"{d['experiment_id']}: KEEP olcumsuz")
    if ihlaller:
        for k in kararlar:
            if k["etiket"] == "EMIR-ADAYI":
                k["etiket"] = "BILGI (MUHURLU — ic denetim ihlali)"
    return ihlaller


def override_kontrol():
    """PDF #17 Human Override: meta3_override.json {'dur': true} -> HALT."""
    if os.path.exists(OVERRIDE_YOLU):
        try:
            with open(OVERRIDE_YOLU, encoding="utf-8") as f:
                ov = json.load(f)
            if ov.get("dur") is True:
                return "HALT"
        except Exception:
            return "HALT"   # bozuk override dosyasi da guvenli tarafta durdurur
    return None


# --------------------------------------------------------------------
# NIHAI CALISMA DONGUSU (PDF #21) — her calistirmada
# --------------------------------------------------------------------
def kosu():
    print("META3 KARARGAH v1.5 — recursive karar dongusu "
          "(karar-destek; emir gondermez)")
    print("=" * 70)
    if override_kontrol() == "HALT":
        print("HALT: insan override bayragi aktif (meta3_override.json). "
              "Hicbir islem yapilmadi.")
        return
    try:
        bellek = bellek_yukle()
    except BellekBozuk as e:
        print(f"HALT: bellek dosyasi bozuk — {e}")
        print("Yedek: meta3_bellek.json.bak (varsa) elle geri konabilir ya da"
              " dosya silinip temiz baslangic yapilir. Bozuk bellekle KOSU"
              " YAPILMAZ (fail-closed).")
        return
    muhur = kapi_muhru()
    muhur_ok = True
    if bellek["kapi_muhru"] is None:
        bellek["kapi_muhru"] = muhur
        print(f"Kapi muhru ILK kosuda kaydedildi: {muhur[:16]}…")
    elif bellek["kapi_muhru"] != muhur:
        muhur_ok = False
        print("!!! HALT: kapi sabitleri onceki kosudan FARKLI (muhur tutmadi)."
              " Recursive katmanlar sabit degistiremez; degisiklik insan"
              " elinden geldiyse bellek sifirlanmali (meta3_bellek.json sil).")
        return

    zincir_ok, kirik = akibet_zinciri_dogrula(bellek)
    if not zincir_ok:
        print(f"!!! HALT: akibet defteri butunlugu bozuk (kayit #{kirik}). "
              f"Defter elle degistirilmis ya da bozulmus olabilir; olculmus"
              f" gecmis guvenilmezse KEEP/REJECT verilemez. Yedek: .bak")
        return
    t_kosu = time.monotonic()
    motor.selftest()
    try:
        btc_4h = motor.fetch_ohlcv("BTC/USDT", motor.TF_4H, motor.LIMIT_4H)
        btc_15m = motor.fetch_ohlcv("BTC/USDT", motor.TF_15M, motor.LIMIT_15M)
    except Exception:
        traceback.print_exc()
        print("\nKosu BASARISIZ: BTC referans verisi alinamadi.")
        return
    veri_yasi_sn = max(0.0, (pd.Timestamp.now(tz="UTC")
                             - btc_15m.index[-1]).total_seconds())

    # ---- 1) HESAP VERME: onceki onerilerin GERCEK akibeti --------------
    print("\n[HESAP VERME] onceki kosunun onerileri:")
    bekleyen = []
    olculen = 0
    for oneri in bellek["oneriler"]:
        try:
            df15 = (btc_15m if oneri["sembol"] == "BTC/USDT"
                    else motor.fetch_ohlcv(oneri["sembol"], motor.TF_15M, 200))
        except Exception:
            bekleyen.append(oneri)
            continue
        sonuc = akibet_olc(oneri, df15)
        if sonuc is None:
            bekleyen.append(oneri)
            continue
        olculen += 1
        akibet_ekle(bellek, {
            "sembol": oneri["sembol"], "varyant": oneri.get("varyant"),
            "etiket": oneri.get("etiket"), "golge": oneri.get("golge", {}),
            "sonuc": sonuc["sonuc"], "r": sonuc["r"],
            # v1.3: imza varyanttan BAGIMSIZ — ayni (sembol, bar) gozlemi
            # varyant degisse de tek kayittir (3. tur denetim: varyant-
            # degisimli ayni-bar yan kapisi kapatildi)
            "oneri_imza": f"{oneri['sembol']}|{oneri['bar_ts']}",
        })
        r_str = "R yazilmaz" if sonuc["r"] is None else f"R={sonuc['r']:+.2f}"
        print(f"  {oneri['sembol']}: {sonuc['sonuc']} ({r_str})")
    if not bellek["oneriler"]:
        print("  kayit yok (ilk kosu ya da onceki kosuda oneri yoktu) — "
              "gecmis UYDURULMAZ")
    elif olculen == 0:
        print(f"  {len(bekleyen)} oneri hala olculemedi (yeni bar/veri yok)")
    bellek["oneriler"] = bekleyen

    # ---- 2) AGENT: her sembol icin karar (aktif varyantla) -------------
    aktif = bellek["aktif_varyant"]
    print(f"\n[AGENT] aktif varyant: {aktif} — "
          f"{VARYANTLAR[aktif]['aciklama']}")
    kararlar = []
    p_maxlar = []
    atlanan = 0
    for sym in motor.SYMBOLS:
        try:
            if sym == "BTC/USDT":
                a4, a15 = btc_4h, btc_15m
            else:
                a4 = motor.fetch_ohlcv(sym, motor.TF_4H, motor.LIMIT_4H)
                a15 = motor.fetch_ohlcv(sym, motor.TF_15M, motor.LIMIT_15M)
            k = karar_uret(sym, a4, a15, btc_4h, btc_15m)
            k, dusen = varyant_karari(k, aktif)
            kararlar.append(k)
            if k["p_max"] is not None:
                p_maxlar.append(k["p_max"])
        except Exception:
            traceback.print_exc()
            atlanan += 1
            print(f"  [{sym}] atlandi.")
    bellek["_son_p_max"] = (float(np.median(p_maxlar)) if p_maxlar else None)

    # ---- 2b) IC DENETIM — BASIM ve BELLEK KAYDINDAN ONCE ---------------
    # (Kirma-denetimi bulgusu: onceki surumde denetim basimdan SONRA
    # geliyordu; muhurlenen etiket ekranda ve bellekte muhursuz kaliyordu.
    # Sira duzeltildi: once denetim, sonra basim/kayit — muhur FIILEN isler.)
    ihlaller = ic_denetim(bellek, kararlar, muhur_ok)

    # ---- 3) CIKTI: YON + SEVIYELER her sembolde ZORUNLU ---------------
    print("\n[KARARLAR]")
    for k in kararlar:
        print(f"\n=== {k['sembol']} ===")
        print(f"  YON: {k['yon']}  (kaynak: {k['yon_kaynak']})")
        if k["giris"] is not None and k["hedef"] is not None:
            # v1.5: R olculur ve basilir; R_min=1.35 atfi STRATEJI.md
            # sozlesmesinden (izlenebilir kaynak). Altindaysa acikca DAR
            # etiketi tasir — dar geometri gizlenmez.
            r_not = (f"R={k.get('r', 0):.2f}"
                     + ("" if k.get("r", 0) >= 1.35
                        else " (DAR — STRATEJI.md R_min=1.35 altinda)"))
            print(f"  SEVIYELER [{k['etiket']}]: giris {k['giris']:.4f} | "
                  f"stop {k['stop']:.4f} | hedef {k['hedef']:.4f} | "
                  f"{r_not} | zaman-stop {motor.TIME_STOP_BARS} bar")
        elif k["giris"] is not None:
            print(f"  SEVIYELER [{k['etiket']}]: giris {k['giris']:.4f} | "
                  f"stop {k['stop']:.4f} | hedef VERI YOK "
                  f"({k.get('hedef_gerekce', 'olculemedi')})")
        else:
            print(f"  SEVIYELER: VERI YOK (ATR olculemedi ya da yon NOTR"
                  f" — uydurma seviye basilmaz)")
        print(f"  KAPI: {k['kapi']} — {k['kapi_gerekce']}")
        if k.get("oos"):
            print(f"  OLCUM: kural={k['kural']} | OOS ort "
                  f"%{k['oos']['mean'] * 100:.3f} | n={k['oos']['n']} | "
                  f"p_max={k['p_max']:.3f}")
        # oneri kaydi: SEVIYESI OLAN her karar akibet defterine girer
        # (BILGI dahil — dogruluk olcumu icin; EMIR-ADAYI ayrica etiketli)
        # v1.2 (2. tur denetim — MUKERRER KAYIT giderimi): ayni
        # (sembol, bar_ts, varyant) imzasi bekleyen onerilerde YA DA olculmus
        # akibetlerde varsa yeniden yazilmaz — ayni bar icinde tekrar kosu
        # ayni gozlemi cifte sayamaz (n sisirme kapisi kapali).
        if k["giris"] is not None and k["bar_ts"] is not None:
            imza = f"{k['sembol']}|{k['bar_ts']}"
            bekleyen_imzalar = {f"{o['sembol']}|{o['bar_ts']}"
                                for o in bellek["oneriler"]}
            olculmus_imzalar = {a.get("oneri_imza")
                                for a in bellek["akibetler"]}
            if imza in bekleyen_imzalar or imza in olculmus_imzalar:
                print(f"  (oneri zaten kayitli — ayni bar, mukerrer kayit "
                      f"yazilmadi)")
            else:
                bellek["oneriler"].append({
                    "sembol": k["sembol"], "yon": k["yon"],
                    "giris": k["giris"], "stop": k["stop"],
                    "hedef": k["hedef"], "bar_ts": k["bar_ts"],
                    "etiket": k["etiket"], "varyant": aktif,
                    "golge": k["golge"],
                })

    # ---- 4) META / META2 / META3 (PDF #21 sirasi) ----------------------
    kosu_suresi = time.monotonic() - t_kosu
    print("\n[META]")
    if kararlar:
        m_karar, m_detay = meta_dongusu(bellek, kosu_suresi, veri_yasi_sn, guvenlik_ok=not ihlaller)
        print(f"  META: {m_karar} — {m_detay}")
        bellek["kosu_sayaci"] += 1
        m2 = meta2_dongusu(bellek)
        if m2 is not None:
            print(f"  META2: {m2} (eps={bellek['eps']:.2f})")
        m3 = meta3_dongusu(bellek)
        if m3 is not None:
            print(f"  META3: {m3} (W={bellek['W']})")
    else:
        # Denetim bulgusu: bos kosu birinci-sinif kosu sayilmasin — sayac
        # ilerlemez, META katmanlari olcusuz veriyle KOSMAZ (fail-closed).
        print("  META: ATLANDI — hicbir sembol karari uretilemedi; kosu "
              "sayaci ILERLEMEDI, katmanlar olcusuz kosturulmadi.")

    # ---- 5) IC DENETIM (audit) + bellek yazimi -------------------------
    if ihlaller:
        print("\n[IC DENETIM] IHLAL — emir-adayi etiketleri MUHURLENDI "
              "(basim ve bellek kayitlari muhurlu etiketle yapildi):")
        for i in ihlaller:
            print(f"  - {i}")
    else:
        print("\n[IC DENETIM] ihlal yok "
              f"(muhur {bellek['kapi_muhru'][:12]}…, "
              f"{len(bellek['deneyler'])} deney kaydi, "
              f"{len(bellek['akibetler'])} olculmus akibet)")
    bellek_kaydet(bellek)
    n_olc = len([a for a in bellek["akibetler"] if a.get("r") is not None])
    tamam = len(kararlar)
    toplam = len(motor.SYMBOLS)
    if atlanan == 0 and tamam == toplam:
        kosu_durum = f"TAM ({tamam}/{toplam} sembol)"
    elif tamam > 0:
        kosu_durum = f"KISMEN ({tamam} tamam, {atlanan} atlandi)"
    else:
        kosu_durum = f"BASARISIZ (0/{toplam} sembol — karar uretilemedi)"
    print(f"\n[OZET] kosu: {kosu_durum} | surum v{bellek['surum']} | "
          f"aktif {bellek['aktif_varyant']} | kosu #{bellek['kosu_sayaci']} | "
          f"olculmus akibet: {n_olc} | eps={bellek['eps']:.2f} W={bellek['W']}")
    print("Dogruluk sozlesmesi: bu sistem dogrulugu GARANTI ETMEZ; her "
          "kosuda kendi isabetini OLCER ve yalnizca olculebilir iyilesmeyi "
          "tutar (PDF bolum 24 — bilimsel sinir).")


if __name__ == "__main__":
    kosu()
