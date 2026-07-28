#!/usr/bin/env python3
"""izleme-telemetri — piramit boru hattı için BAĞIMLILIKSIZ yerel metrik yazıcı.

Kaynak rehber (a-claude-code-monitoring-guide) Claude Code CLI'ın token/maliyet
telemetrisini OpenTelemetry ile toplar. Bu depoda OTel/Prometheus/Grafana KURULU
DEĞİLDİR; ölçülen şey de token değil, PİRAMİT BORU HATTININ KENDİSİDİR:
katman/motor süresi, kapı durdurmaları, doğrulanmayan danışmanlar, gözlemci
ihlalleri, zorunlu girdi eksikleri, türev kapsamı, determinizm.

Olay biçimi kaynağın OTel konsol çıktısına SADIKTIR (claude_code_roi_full.md
satır 32-51): her satır bir veri noktasıdır ve
  {"descriptor": {"name","type","description","unit"}, "attributes": {...},
   "value": ...}
alanlarını taşır. Böylece aynı JSONL, dış yığın kurulduğunda OTLP'ye birebir
çevrilebilir (bkz. sunucu/otel-collector-config.yaml — opsiyonel).

Metrik AİLELERİ (kaynaktaki aileleri karşılar):
  SÜRE    (HISTOGRAM) — kaynağın session duration ailesi
  SAYAÇ   (COUNTER)   — kaynağın session/PR/commit/decision/api_error ailesi
  DAĞILIM (GAUGE)     — kaynağın token-by-type / cache oranı ailesi

Doğruluk sözleşmesi: metrik adı `METRIKLER` defterinde yoksa YAZILMAZ (uydurma
metrik adı yasak). Değer sayısal değilse yazılmaz. Eksik alan "VERİ YOK".

Kullanım:
    # motor/katman sarmalama
    from olcum import zamanlayici, sayac, rapordan_yaz
    with zamanlayici("piramit.katman.sure_ms", katman="K1-LLM", kosu_id=kid):
        ...

    # bitmiş bir piramit raporundan tüm sayaçları çıkar
    python olcum.py --rapor engine/cikti/rapor.json --sembol BTCUSDT

    python olcum.py --self-test
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

SEMA = "izleme-telemetri/1"
YOK = "VERİ YOK"

_HERE = Path(__file__).resolve().parent
SKILL_DIR = _HERE.parent
# Depo denetlendi: engine/state/ git-TAKİPLİDİR (durum.json, defter.jsonl,
# onceki_kosu.json commit ediliyor — CLAUDE.md "koşu sonrası engine/state
# değişiklikleri commit+push edilir"). Telemetri oraya yazılsaydı her koşu
# karar siciline gürültü commit'i eklerdi. piramit-sistem/state/ ise BAŞKA bir
# becerinin koşu-artığı dizinidir. Bu yüzden varsayılan kendi dizinimizdir;
# istenirse --dosya / IZLEME_OLCUM_DOSYA ile engine/state'e yönlendirilebilir.
VARSAYILAN_DOSYA = SKILL_DIR / "state" / "olcum.jsonl"
ORNEK_DIZIN = SKILL_DIR / "ornek"

# --------------------------------------------------------------------------
# METRİK DEFTERİ — ad: (tip, birim, açıklama). Defterde olmayan ad YAZILMAZ.
# --------------------------------------------------------------------------
METRIKLER = {
    # --- SÜRE ailesi (HISTOGRAM) ---
    "piramit.kosu.sure_ms": (
        "HISTOGRAM", "ms", "Bir piramit koşusunun uçtan uca süresi"),
    "piramit.katman.sure_ms": (
        "HISTOGRAM", "ms", "Katman başına süre (K1-LLM … K5-SI)"),
    "piramit.motor.sure_ms": (
        "HISTOGRAM", "ms", "Motor başına süre (smc_tespit, sentez, …)"),
    # --- SAYAÇ ailesi (COUNTER) ---
    "piramit.kosu.sayisi": (
        "COUNTER", "{kosu}", "Başlatılan piramit koşusu sayısı"),
    "piramit.kapi.gecti": (
        "COUNTER", "{kapi}", "Katman kapısının GEÇİLDİĞİ koşu sayısı"),
    "piramit.kapi.durdu": (
        "COUNTER", "{durdurma}", "Koşunun DURDUĞU katman kapısı sayısı"),
    "piramit.danisman.dogrulandi": (
        "COUNTER", "{danisman}", "K4 verifier'da confirmed=true olan danışman"),
    "piramit.danisman.dogrulanmadi": (
        "COUNTER", "{danisman}", "K4 verifier'da confirmed=false olan danışman"),
    "piramit.gozlemci.ihlal": (
        "COUNTER", "{ihlal}", "Gözlemci ihlali (UYDURMA/HAFIZA/DAIRESEL/"
                              "EKSIK_AKTARIM/TUNEL/MEMNUN_ETME/SIRADAN/CARPISMA)"),
    "piramit.gozlemci.uyari": (
        "COUNTER", "{uyari}", "Gözlemci uyarısı (kritik olmayan bulgu)"),
    "piramit.muhur": (
        "COUNTER", "{muhur}", "Kritik ihlalle MÜHÜRLENEN koşu (işlem yok)"),
    "piramit.zorunlu_girdi.eksik": (
        "COUNTER", "{eksik}", "Eksik/bayat zorunlu girdi (likidasyon, görsel…)"),
    "piramit.motor.hata": (
        "COUNTER", "{hata}", "Motorun sonuç üretemediği koşu sayısı"),
    "piramit.emir.uretildi": (
        "COUNTER", "{emir}", "EMİR üretildi mi (VAR/YOK) — koşunun iş çıktısı"),
    # --- DAĞILIM ailesi (GAUGE) ---
    "piramit.turev.kapsam": (
        "GAUGE", "1", "turev-akis okunan kapsam (1.0 = tüm türev alanları geldi)"),
    "piramit.determinizm": (
        "GAUGE", "1", "Aynı veri imzası aynı sonuç imzasını verdi mi (1=evet)"),
}

_TIP_AILE = {"HISTOGRAM": "sure", "COUNTER": "sayac", "GAUGE": "dagilim"}

# Piramit katman adları — kaynak: piramit-sistem/scripts/piramit.py satır 120
KATMANLAR = ["K1-LLM", "K2-AI-AJAN", "K3-COKLU-AJAN", "K4-AGI", "K5-SI"]
# Gözlemci ihlal kodları — kaynak: piramit-sistem/scripts/gozlemci.py satır 12-28
IHLAL_KODLARI = ["UYDURMA", "HAFIZA", "DAIRESEL", "EKSIK_AKTARIM", "TUNEL",
                 "MEMNUN_ETME", "SIRADAN", "CARPISMA"]
# Kritik kodlar (mühür) — kaynak: gozlemci.py satır 43
KRITIK = {"UYDURMA", "DAIRESEL", "EKSIK_AKTARIM", "MEMNUN_ETME"}


class OlcumHatasi(Exception):
    pass


# --------------------------------------------------------------------------
# Dosya / temel yazım
# --------------------------------------------------------------------------
_DOSYA: Path | None = None


def dosya_yolu(yol=None) -> Path:
    """Ölçüm dosyası: --dosya > ayarla() > IZLEME_OLCUM_DOSYA > varsayılan."""
    if yol:
        return Path(str(yol)).expanduser()
    if _DOSYA is not None:
        return _DOSYA
    env = os.environ.get("IZLEME_OLCUM_DOSYA")
    if env:
        return Path(env).expanduser()
    return VARSAYILAN_DOSYA


def ayarla(yol) -> Path:
    """Süreç boyunca kullanılacak ölçüm dosyasını sabitle."""
    global _DOSYA
    _DOSYA = Path(str(yol)).expanduser()
    return _DOSYA


def _simdi() -> tuple:
    t = datetime.datetime.now(datetime.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ"), t.timestamp() * 1000.0


def _sayi(x):
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError, ValueError):
        return None


def yeni_kosu_id() -> str:
    return uuid.uuid4().hex[:12]


def yaz(ad: str, deger, dosya=None, **nitelikler) -> dict:
    """Tek veri noktası yaz. Defterde olmayan metrik adı → OlcumHatasi."""
    if ad not in METRIKLER:
        raise OlcumHatasi(f"Bilinmeyen metrik adı: {ad!r} — defterde yok "
                          f"(uydurma metrik yazılmaz). Defter: {sorted(METRIKLER)}")
    v = _sayi(deger)
    if v is None:
        raise OlcumHatasi(f"{ad}: değer sayısal değil ({deger!r}) → yazılmaz")
    tip, birim, aciklama = METRIKLER[ad]
    ts_utc, ts_ms = _simdi()
    olay = {
        "sema": SEMA,
        "descriptor": {"name": ad, "type": tip, "description": aciklama,
                       "unit": birim},
        "aile": _TIP_AILE[tip],
        "attributes": {k: v2 for k, v2 in nitelikler.items() if v2 is not None},
        "value": v,
        "ts_utc": ts_utc,
        "ts_ms": round(ts_ms, 3),
    }
    p = dosya_yolu(dosya)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(olay, ensure_ascii=False) + "\n")
    return olay


def sayac(ad: str, deger=1, dosya=None, **nitelikler) -> dict:
    if METRIKLER.get(ad, ("",))[0] != "COUNTER":
        raise OlcumHatasi(f"{ad}: SAYAÇ ailesinde değil")
    return yaz(ad, deger, dosya=dosya, **nitelikler)


def dagilim(ad: str, deger, dosya=None, **nitelikler) -> dict:
    if METRIKLER.get(ad, ("",))[0] != "GAUGE":
        raise OlcumHatasi(f"{ad}: DAĞILIM ailesinde değil")
    return yaz(ad, deger, dosya=dosya, **nitelikler)


def oku(dosya=None) -> list:
    """JSONL'i olay listesi olarak oku. Bozuk satır ATLANMAZ, işaretlenir."""
    p = dosya_yolu(dosya)
    if not p.exists():
        return []
    olaylar = []
    for i, satir in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        satir = satir.strip()
        if not satir:
            continue
        try:
            o = json.loads(satir)
        except json.JSONDecodeError as e:
            olaylar.append({"_bozuk": f"satır {i}: {e}"})
            continue
        olaylar.append(o)
    return olaylar


# --------------------------------------------------------------------------
# SÜRE ailesi — zamanlayici context manager (motorlar bununla sarmalanır)
# --------------------------------------------------------------------------
@contextlib.contextmanager
def zamanlayici(ad: str = "piramit.motor.sure_ms", dosya=None, **nitelikler):
    """Sarmalanan bloğun süresini ms olarak yazar.

    Blok istisna atarsa süre YİNE yazılır (`durum="HATA"`) ve `motor` niteliği
    varsa `piramit.motor.hata` sayacı da artar — sessiz kayıp yok.

    Örnek:
        with zamanlayici("piramit.katman.sure_ms", katman="K2-AI-AJAN",
                         kosu_id=kid, sembol="BTCUSDT"):
            k2 = k2_ajan(...)
    """
    if METRIKLER.get(ad, ("",))[0] != "HISTOGRAM":
        raise OlcumHatasi(f"{ad}: SÜRE ailesinde değil (HISTOGRAM bekleniyor)")
    t0 = time.perf_counter()
    hata = None
    try:
        yield
    except BaseException as e:  # noqa: BLE001 — süre kaydı istisnada da yazılır
        hata = f"{type(e).__name__}: {e}"
        raise
    finally:
        sure_ms = (time.perf_counter() - t0) * 1000.0
        n = dict(nitelikler)
        n["durum"] = "HATA" if hata else "TAMAM"
        if hata:
            n["hata"] = hata[:200]
        yaz(ad, round(sure_ms, 3), dosya=dosya, **n)
        if hata and nitelikler.get("motor"):
            sayac("piramit.motor.hata", 1, dosya=dosya,
                  motor=nitelikler["motor"], kosu_id=nitelikler.get("kosu_id"),
                  sebep=hata[:200])


# --------------------------------------------------------------------------
# DETERMİNİZM — aynı veriyle aynı sonuç mu?
# --------------------------------------------------------------------------
def imza(nesne) -> str:
    """Kanonik JSON'un sha256'sının ilk 16 hanesi (deterministik parmak izi)."""
    ham = json.dumps(nesne, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:16]


def determinizm_olc(veri_imzasi: str, sonuc_imzasi: str, dosya=None,
                    **nitelikler) -> dict:
    """Aynı veri imzası daha önce görülmüşse sonuç imzasıyla karşılaştır.

    İlk gözlem: value=1.0 + `ilk_gozlem=True` (kıyas yok, raporda sayılmaz).
    Tekrar gözlem: sonuç imzası aynıysa 1.0, farklıysa 0.0 (determinizm KIRIK).
    """
    onceki = None
    for o in oku(dosya):
        d = (o.get("descriptor") or {}).get("name")
        a = o.get("attributes") or {}
        if d == "piramit.determinizm" and a.get("veri_imzasi") == veri_imzasi:
            onceki = a.get("sonuc_imzasi")
    ilk = onceki is None
    ayni = 1.0 if (ilk or onceki == sonuc_imzasi) else 0.0
    return dagilim("piramit.determinizm", ayni, dosya=dosya,
                   veri_imzasi=veri_imzasi, sonuc_imzasi=sonuc_imzasi,
                   onceki_sonuc_imzasi=onceki, ilk_gozlem=ilk, **nitelikler)


# --------------------------------------------------------------------------
# Piramit raporundan sayaç çıkarımı (gerçek entegrasyon yolu)
# --------------------------------------------------------------------------
def _ihlal_kodu(satir: str) -> tuple:
    """'K3-COKLU-AJAN/UYDURMA: kanıt…' → ('K3-COKLU-AJAN', 'UYDURMA')."""
    kat, _, geri = str(satir).partition("/")
    kod = geri.partition(":")[0].strip()
    if kod not in IHLAL_KODLARI:
        kod = YOK
    return (kat.strip() or YOK), kod


def rapordan_yaz(rapor: dict, kosu_id: str | None = None, sembol=None,
                 dosya=None) -> list:
    """Bitmiş bir `piramit.py` raporundan SAYAÇ/DAĞILIM metriklerini çıkarır.

    Süre metrikleri buradan GELMEZ — piramit raporu süre taşımaz; süreler
    `zamanlayici` ile koşu sırasında sarmalanarak ölçülür (uydurma yok).
    """
    if not isinstance(rapor, dict):
        raise OlcumHatasi("rapor bir sözlük değil")
    kosu_id = kosu_id or yeni_kosu_id()
    sembol = sembol or rapor.get("sembol") or YOK
    ortak = {"kosu_id": kosu_id, "sembol": sembol}
    yazilan = []

    yazilan.append(sayac("piramit.kosu.sayisi", 1, dosya=dosya,
                         durum=str(rapor.get("durum", YOK))[:80], **ortak))

    katmanlar = rapor.get("katmanlar") or []
    for k in katmanlar:
        ad = k.get("katman", YOK)
        gecti = bool(k.get("gecti"))
        metrik = "piramit.kapi.gecti" if gecti else "piramit.kapi.durdu"
        yazilan.append(sayac(metrik, 1, dosya=dosya, katman=ad,
                             kapi=str(k.get("kapi", YOK))[:200], **ortak))
    # Koşulmayan katmanlar (kapı kapandığı için) sessizce kaybolmaz:
    kosan = {k.get("katman") for k in katmanlar}
    for ad in KATMANLAR:
        if ad not in kosan:
            yazilan.append(sayac("piramit.kapi.durdu", 0, dosya=dosya,
                                 katman=ad, kapi="KOŞMADI — alt kapı kapalı",
                                 kosmadi=True, **ortak))

    K = {k.get("katman"): k for k in katmanlar}

    # K2 motor hataları
    for h in (K.get("K2-AI-AJAN") or {}).get("hatalar") or []:
        yazilan.append(sayac("piramit.motor.hata", 1, dosya=dosya,
                             motor=h.get("motor", YOK),
                             sebep=str(h.get("hata", YOK))[:200], **ortak))

    # K2 türev kapsamı (dağılım)
    m2 = (K.get("K2-AI-AJAN") or {}).get("motor_sonuclari") or {}
    kapsam = _sayi((((m2.get("turev-akis") or {}).get("rapor")) or {}).get("kapsam"))
    if kapsam is not None:
        yazilan.append(dagilim("piramit.turev.kapsam", kapsam, dosya=dosya,
                               **ortak))

    # K4 danışman doğrulaması
    for d_ad, v in ((K.get("K4-AGI") or {}).get("verifier") or {}).items():
        onay = bool((v or {}).get("confirmed"))
        metrik = ("piramit.danisman.dogrulandi" if onay
                  else "piramit.danisman.dogrulanmadi")
        yazilan.append(sayac(metrik, 1, dosya=dosya, danisman=d_ad,
                             gerekce=str((v or {}).get("reason", ""))[:200],
                             **ortak))

    # Gözlemci bulguları
    denetim = rapor.get("DENETIM") or {}
    for satir in denetim.get("ihlal") or []:
        kat, kod = _ihlal_kodu(satir)
        yazilan.append(sayac("piramit.gozlemci.ihlal", 1, dosya=dosya,
                             kod=kod, katman=kat, kritik=(kod in KRITIK),
                             kanit=str(satir)[:200], **ortak))
    for satir in denetim.get("uyari") or []:
        kat, kod = _ihlal_kodu(satir)
        yazilan.append(sayac("piramit.gozlemci.uyari", 1, dosya=dosya,
                             kod=kod, katman=kat, kanit=str(satir)[:200],
                             **ortak))
    if denetim.get("muhurlendi"):
        yazilan.append(sayac("piramit.muhur", 1, dosya=dosya,
                             kritik_sayisi=len(denetim.get("kritik_ihlal") or []),
                             **ortak))

    # Zorunlu girdi eksikleri + emir çıktısı
    zirve = rapor.get("ZIRVE") or {}
    for e in zirve.get("ZORUNLU_EKSIK") or []:
        girdi = str(e).split(":")[0].strip() or YOK
        yazilan.append(sayac("piramit.zorunlu_girdi.eksik", 1, dosya=dosya,
                             girdi=girdi, gerekce=str(e)[:200], **ortak))
    emir = str(zirve.get("EMIR", YOK))
    var = 0 if (emir == YOK or emir.startswith("EMİR YOK")) else 1
    yazilan.append(sayac("piramit.emir.uretildi", var, dosya=dosya,
                         emir=emir[:120], **ortak))
    return yazilan


def rapor_dosyasindan(yol, kosu_id=None, sembol=None, dosya=None) -> list:
    p = Path(str(yol)).expanduser()
    if not p.exists():
        raise OlcumHatasi(f"Rapor dosyası yok: {p}")
    return rapordan_yaz(json.loads(p.read_text(encoding="utf-8")),
                        kosu_id=kosu_id, sembol=sembol, dosya=dosya)


# --------------------------------------------------------------------------
# ÖZ-TEST — sahte koşu olayları üretir, sonra kendi çıktısını doğrular
# --------------------------------------------------------------------------
def _sahte_rapor(sembol, durdu_katman=None, ihlal=None, kapsam=0.75,
                 emir="LIMIT LONG @100.0 | 98.0 | 104.0 | R=2.00"):
    """Piramit rapor ŞEMASINA (piramit.py `kos()` çıktısı) uyan sahte rapor."""
    katmanlar = []
    for ad in KATMANLAR:
        gecti = (durdu_katman is None) or (KATMANLAR.index(ad)
                                           < KATMANLAR.index(durdu_katman))
        katmanlar.append({"katman": ad, "gecti": gecti,
                          "kapi": f"{ad} kapısı " + ("GEÇİLDİ" if gecti
                                                     else "KAPALI: yetersiz kanıt")})
        if not gecti:
            break
    K2 = {"katman": "K2-AI-AJAN", "gecti": True, "kapi": "K2 kapısı GEÇİLDİ",
          "hatalar": [{"motor": "turev-akis", "hata": "türev paneli VERİ YOK"}],
          "motor_sonuclari": {"turev-akis": {"rapor": {"kapsam": kapsam}}}}
    for i, k in enumerate(katmanlar):
        if k["katman"] == "K2-AI-AJAN":
            katmanlar[i] = {**k, **K2}
    verifier = {"karar-motoru": {"confirmed": True, "reason": "R=1.62 ≥ 1.35"},
                "grafik-calisma": {"confirmed": False,
                                   "reason": "setup_dogrulama: sinyal izni YOK"},
                "gorsel-teyit": {"confirmed": False, "reason": "UYUMSUZ"}}
    for i, k in enumerate(katmanlar):
        if k["katman"] == "K4-AGI":
            katmanlar[i] = {**k, "verifier": verifier}
    denetim = {"ihlal": list(ihlal or []), "uyari": ["K4-AGI/TUNEL: tek kanıt ailesi"],
               "kritik_ihlal": [x for x in (ihlal or [])
                                if _ihlal_kodu(x)[1] in KRITIK]}
    denetim["muhurlendi"] = bool(denetim["kritik_ihlal"])
    return {
        "sembol": sembol,
        "durum": ("TAMAM — piramidin tepesine ulaşıldı" if durdu_katman is None
                  else f"DURDU — {durdu_katman}"),
        "katmanlar": katmanlar,
        "DENETIM": denetim,
        "ZIRVE": {"YON_BIAS": "LONG",
                  "ZORUNLU_EKSIK": ["likidasyon: CoinGlass long/short GELMEDİ",
                                    "görsel okuma: BAYAT — 310 dk eski"],
                  "EMIR": "EMİR YOK — DENETİM MÜHÜRÜ" if denetim["muhurlendi"]
                          else emir},
    }


def self_test(dosya=None) -> dict:
    """Sahte koşu olayları yaz → kendi yazdığını oku → sayıları doğrula."""
    hedef = Path(str(dosya)) if dosya else (ORNEK_DIZIN / "olcum_ornek.jsonl")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if hedef.exists():
        hedef.unlink()                      # öz-test tekrar edilebilir olmalı
    ayarla(hedef)
    kontroller, bekleme = [], {}

    senaryolar = [
        # (sembol, durdu_katman, ihlaller, kapsam, katman süreleri ms)
        ("BTCUSDT", None, [], 1.0, [120.0, 2400.0, 180.0, 90.0, 700.0]),
        ("BTCUSDT", None, ["K3-COKLU-AJAN/UYDURMA: kaynaksız danışman güveni"],
         0.55, [110.0, 2600.0, 210.0, 95.0, 760.0]),
        ("ETHUSDT", "K3-COKLU-AJAN", [], 0.40, [130.0, 2100.0, 150.0]),
    ]
    kosular = []
    for sembol, durdu, ihl, kapsam, sureler in senaryolar:
        kid = yeni_kosu_id()
        kosular.append(kid)
        t_kosu = 0.0
        for ad, ms in zip(KATMANLAR, sureler):
            # Gerçek zamanlayıcı kullanılır (sahte sayı ENJEKTE EDİLMEZ):
            # blok gerçekten `ms/1000` kadar uyur, süre ölçülür.
            with zamanlayici("piramit.katman.sure_ms", katman=ad, kosu_id=kid,
                             sembol=sembol):
                time.sleep(min(ms, 30.0) / 1000.0)
            t_kosu += ms
        with zamanlayici("piramit.motor.sure_ms", motor="smc_tespit",
                         kosu_id=kid, sembol=sembol):
            time.sleep(0.002)
        try:
            with zamanlayici("piramit.motor.sure_ms", motor="turev-akis",
                             kosu_id=kid, sembol=sembol):
                raise RuntimeError("türev paneli VERİ YOK")
        except RuntimeError:
            pass                             # hata sayacı yazıldı, koşu sürüyor
        with zamanlayici("piramit.kosu.sure_ms", kosu_id=kid, sembol=sembol):
            time.sleep(0.003)
        rapor = _sahte_rapor(sembol, durdu, ihl, kapsam)
        rapordan_yaz(rapor, kosu_id=kid, sembol=sembol)
        # Veri imzası = girdinin parmak izi, sonuç imzası = çıktının parmak izi.
        # BTC iki kez AYNI veriyle koşar; ikincisinde gözlemci ihlali çıkar →
        # sonuç imzası değişir → determinizm KIRIK (0.0) ölçülmelidir.
        determinizm_olc(imza({"sembol": sembol, "bar": "2026-07-28T12:00Z"}),
                        imza({"YON": "LONG", "durdu": durdu, "ihlal": ihl}),
                        kosu_id=kid, sembol=sembol)

    olaylar = oku()
    adlar = [(o.get("descriptor") or {}).get("name") for o in olaylar]

    def _say(ad, **filtre):
        n = 0
        for o in olaylar:
            if (o.get("descriptor") or {}).get("name") != ad:
                continue
            a = o.get("attributes") or {}
            if all(a.get(k) == v for k, v in filtre.items()):
                n += int(o.get("value") or 0) if ad.startswith("piramit.kosu.sayisi") \
                    or o["descriptor"]["type"] == "COUNTER" else 1
        return n

    bekleme["olay_sayisi"] = len(olaylar)
    kontroller.append(("bozuk satır yok",
                       not any("_bozuk" in o for o in olaylar)))
    kontroller.append(("3 koşu sayacı", _say("piramit.kosu.sayisi") == 3))
    kontroller.append(("13 katman süresi (5+5+3)",
                       adlar.count("piramit.katman.sure_ms") == 13))
    kontroller.append(("2 motor hatası sayacı (turev-akis ×3 sarmalama + "
                       "3 rapor hatası)",
                       _say("piramit.motor.hata", motor="turev-akis") == 6))
    kontroller.append(("1 kapı durdurma (ETH/K3)",
                       _say("piramit.kapi.durdu", katman="K3-COKLU-AJAN") == 1))
    kontroller.append(("2 koşuda doğrulanmayan grafik-calisma",
                       _say("piramit.danisman.dogrulanmadi",
                            danisman="grafik-calisma") == 2))
    kontroller.append(("1 UYDURMA ihlali",
                       _say("piramit.gozlemci.ihlal", kod="UYDURMA") == 1))
    kontroller.append(("1 mühür", _say("piramit.muhur") == 1))
    kontroller.append(("6 zorunlu girdi eksiği (3 koşu × 2)",
                       _say("piramit.zorunlu_girdi.eksik") == 6))
    kontroller.append(("3 türev kapsam ölçümü",
                       adlar.count("piramit.turev.kapsam") == 3))
    det = [o for o in olaylar
           if (o.get("descriptor") or {}).get("name") == "piramit.determinizm"]
    kontroller.append(("3 determinizm ölçümü", len(det) == 3))
    kontroller.append(("BTC ikinci koşusu determinizm KIRIK (0.0)",
                       any(o["value"] == 0.0 and not o["attributes"]["ilk_gozlem"]
                           for o in det)))
    sureler = [o["value"] for o in olaylar
               if (o.get("descriptor") or {}).get("name") == "piramit.katman.sure_ms"]
    kontroller.append(("süreler pozitif ve gerçek ölçüm",
                       bool(sureler) and all(s > 0 for s in sureler)))
    # Uydurma metrik adı reddedilmeli
    try:
        yaz("claude_code.cost.usage", 1.0)
        kontroller.append(("defter dışı metrik reddedildi", False))
    except OlcumHatasi:
        kontroller.append(("defter dışı metrik reddedildi", True))
    # Sayısal olmayan değer reddedilmeli
    try:
        yaz("piramit.turev.kapsam", "çok")
        kontroller.append(("sayısal olmayan değer reddedildi", False))
    except OlcumHatasi:
        kontroller.append(("sayısal olmayan değer reddedildi", True))

    gecen = sum(1 for _, ok in kontroller if ok)
    sonuc = {
        "arac": "olcum.py --self-test",
        "dosya": str(hedef),
        "olay_sayisi": len(olaylar),
        "metrik_adlari": sorted(set(a for a in adlar if a)),
        "sure_ozet_ms": {
            "n": len(sureler),
            "ortalama": round(statistics.fmean(sureler), 3) if sureler else YOK,
            "en_uzun": round(max(sureler), 3) if sureler else YOK},
        "kontroller": [{"ad": a, "sonuc": "GEÇTİ" if ok else "KALDI"}
                       for a, ok in kontroller],
        "SONUC": "GEÇTİ" if gecen == len(kontroller) else "KALDI",
        "gecen": f"{gecen}/{len(kontroller)}",
        "kosu_idler": kosular,
        **bekleme,
    }
    return sonuc


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="piramit boru hattı için yerel metrik yazıcı (JSONL)")
    ap.add_argument("--dosya", help="JSONL ölçüm dosyası "
                                    f"(varsayılan: {VARSAYILAN_DOSYA})")
    ap.add_argument("--rapor", help="piramit.py rapor JSON'undan sayaç çıkar")
    ap.add_argument("--sembol", help="rapor için sembol etiketi")
    ap.add_argument("--kosu-id", help="rapor için koşu kimliği")
    ap.add_argument("--metrik", help="tek veri noktası yaz: metrik adı")
    ap.add_argument("--deger", type=float, help="--metrik ile yazılacak değer")
    ap.add_argument("--nitelik", action="append", default=[],
                    metavar="ANAHTAR=DEGER", help="niteliği ekle (tekrarlanabilir)")
    ap.add_argument("--defter", action="store_true", help="metrik defterini bas")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.dosya:
        ayarla(a.dosya)

    if a.self_test:
        s = self_test(a.dosya)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0 if s["SONUC"] == "GEÇTİ" else 1

    if a.defter:
        print(json.dumps({ad: {"tip": t, "birim": b, "aciklama": c}
                          for ad, (t, b, c) in METRIKLER.items()},
                         ensure_ascii=False, indent=2))
        return 0

    nitelikler = {}
    for n in a.nitelik:
        k, _, v = n.partition("=")
        nitelikler[k.strip()] = v.strip()

    if a.rapor:
        yazilan = rapor_dosyasindan(a.rapor, kosu_id=a.kosu_id, sembol=a.sembol)
        print(json.dumps({"yazilan_olay": len(yazilan),
                          "dosya": str(dosya_yolu()),
                          "metrikler": sorted({o["descriptor"]["name"]
                                               for o in yazilan})},
                         ensure_ascii=False, indent=2))
        return 0

    if a.metrik:
        if a.deger is None:
            print("HATA: --metrik ile --deger zorunlu", file=sys.stderr)
            return 2
        o = yaz(a.metrik, a.deger, **nitelikler)
        print(json.dumps(o, ensure_ascii=False))
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OlcumHatasi as e:
        print(f"OLÇÜM HATASI: {e}", file=sys.stderr)
        sys.exit(1)
