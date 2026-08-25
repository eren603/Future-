#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RUBRİK KAPISI — bir piramit koşusunun kalitesini KRİTER-BAŞINA notlar.

Girdi: (1) bir koşu raporu (piramit.py --out çıktısı, JSON), (2) bir ya da daha
çok rubrik CSV'si. Çıktı: her kriter için GEÇTİ / DÜŞTÜ / ATLANDI + kanıt satırı.

SÖZLEŞME (kaynak rubrik README'sinden alınmıştır, birebir):
  · `Conditional`  — "If non-empty, the criterion applies only when this
    condition is met"; koşul sağlanmazsa kriter "is skipped (not failed)".
  · Toplam skor    — "aggregate pass rates can mask meaningful gaps"; bu yüzden
    BİRİNCİL çıktı kriter-başına dökümdür, toplam İKİNCİL ve uyarı notludur.

SAPMA (bilinçli): kaynak rubrikler LLM-as-judge için yazılmıştır; burada
puanlama DETERMİNİSTİKTİR — her kriter raporun bir alanına inen bir denetçi
fonksiyonla ölçülür. Denetçisi olmayan kriter "PUANLANMADI" olur ve GEÇTİ
sayılmaz (fail-closed; uydurma not yok).

Sıfır bağımlılık (stdlib). Determinist: ağ yok, duvar-saati yok.
⚠️ Bu bir KOŞU KALİTESİ notudur; piyasa kararı ya da canlı emir DEĞİLDİR.

Kullanım:
    python rubrik.py --rapor son_rapor.json --rubrik rubrikler/kosu_ortak.csv \
                     [--rubrik rubrikler/emir.csv] [--json] [--out puan.json]
    python rubrik.py --self-test
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SKILL = _HERE.parent
ORNEK = SKILL / "ornek"
RUBRIKLER = SKILL / "rubrikler"

YOK = "VERİ YOK"
GECTI, DUSTU, ATLANDI, PUANSIZ = "GEÇTİ", "DÜŞTÜ", "ATLANDI", "PUANLANMADI"

#: Kaynak CSV'nin 6 sütunu — birebir, sırasıyla (evals/README.md:20-29)
SUTUNLAR = ("ID", "Bucket", "Criterion", "What pass requires", "Notes", "Conditional")

#: Kanıt aileleri — gozlemci.py:46-54 (AILE) ile birebir aynı
AILE = {
    "karar-motoru": "fiyat-yapisi",
    "grafik-calisma": "fiyat-yapisi",
    "smc_tespit": "fiyat-yapisi",
    "turev-akis": "turev-akis",
    "setup_dogrulama": "tarihsel-kanit",
    "backtest-motoru": "tarihsel-kanit",
    "gorsel-teyit": "gorsel",
}

#: Motor şema derinliği — gozlemci.py:57-65 (SEMA_DERINLIK) ile birebir aynı
SEMA_DERINLIK = {
    "karar-motoru": ("karar", "son_bar_utc", "rejim_4h"),
    "smc_tespit": ("trend", "atr", "rejim"),
    "grafik-calisma": ("KARAR", "confluence_skoru", "kapi_gerekceleri"),
    "setup_dogrulama": ("SONUC", "sinyal_izni", "gerekce"),
    "turev-akis": ("rapor", "danisman"),
    "smc_tespit_h4": ("trend", "atr", "likidite"),
    "korelasyon": ("korelasyon", "beta", "gozlem", "HUKUM"),
}

#: Depodan OKUNAN eşikler (her biri KANIT.md'de dosya:satır ile bağlıdır)
ESIK = {
    "r_min": 1.35,                 # piramit.py:98 / emir_plani.py:58
    "min_motor_k2": 2,             # piramit.py:106
    "min_danisman_k3": 2,          # piramit.py:107
    "gorsel_tavan": 0.50,          # piramit.py:105
    "tazelik_dk": 240,             # piramit.py:114
    "refute_penalty": 0.25,        # sentez.py:130 (varsayılan)
    "turev_kapsam_esigi": 0.5,     # turev_akis.py:64
    "kopya_esigi": 0.85,           # korelasyon.py:32
    "kopya_risk_kat": 2.0,         # korelasyon.py:99
    "n_taban": 10,                 # kalibrasyon.py:38
    "agirlik_alt": 0.40,           # piramit.py:103
    "agirlik_ust": 1.00,           # piramit.py:103
    "market_tolerans_atr": 0.1,    # emir_plani.py:59
    "min_kanit_ailesi": 2,         # gozlemci.py:314-323 (tünel görüşü)
}

#: Gözlemcinin kritik ihlal kodları — gozlemci.py:43 (KRITIK)
KRITIK_KOD = {"UYDURMA", "DAIRESEL", "EKSIK_AKTARIM", "MEMNUN_ETME"}

EMIR_KALIP = re.compile(
    r"^(MARKET|LIMIT)\s+(LONG|SHORT)\s+@(-?[\d.]+)\s*\|\s*stop\s+(-?[\d.]+)\s*\|"
    r"\s*T1\s+(-?[\d.]+)\s*\|\s*R\s+(-?[\d.]+)\s*$")


class RubrikError(Exception):
    pass


# --------------------------------------------------------------------------
# Yardımcılar
# --------------------------------------------------------------------------
def _f(x):
    """Sayıya çevir; çevrilemiyorsa None (uydurma yok)."""
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _sayilar(nesne, kume=None):
    """Bir yapıdaki TÜM sayısal değerleri topla — gozlemci.py:72-83 ile aynı."""
    kume = set() if kume is None else kume
    if isinstance(nesne, dict):
        for v in nesne.values():
            _sayilar(v, kume)
    elif isinstance(nesne, list):
        for v in nesne:
            _sayilar(v, kume)
    elif isinstance(nesne, (int, float)) and not isinstance(nesne, bool):
        kume.add(round(float(nesne), 6))
    return kume


class Kosu:
    """Koşu raporunun katmanlara ayrılmış görünümü (yalnız okur, yazmaz)."""

    def __init__(self, rapor: dict):
        self.rapor = rapor if isinstance(rapor, dict) else {}
        K = {k.get("katman"): k for k in (self.rapor.get("katmanlar") or [])
             if isinstance(k, dict)}
        self.k1 = K.get("K1-LLM") or {}
        self.k2 = K.get("K2-AI-AJAN") or {}
        self.k3 = K.get("K3-COKLU-AJAN") or {}
        self.k4 = K.get("K4-AGI") or {}
        self.k5 = K.get("K5-SI") or {}
        self.zirve = self.rapor.get("ZIRVE") or {}
        self.denetim = self.rapor.get("DENETIM") or {}
        self.kiyas = self.rapor.get("KIYAS") or {}
        self.job = self.rapor.get("_job") or {}
        self.motorlar = self.k2.get("motor_sonuclari") or {}
        self.danismanlar = self.k3.get("danismanlar") or []
        self.seviyeler = self.k3.get("seviyeler") or {}
        self.verifier = self.k4.get("verifier") or {}
        self.sentez = self.k5.get("sentez") or {}
        self.emir = self.k5.get("emir_plani") or {}
        self.islem = self.k5.get("islem_kalitesi") or {}

    def danisman(self, ad):
        for d in self.danismanlar:
            if d.get("name") == ad:
                return d
        return None


# --------------------------------------------------------------------------
# KOŞULLAR — `Conditional` sütunundaki anahtarın karşılığı.
# Koşul sağlanmazsa kriter ATLANIR, DÜŞMÜŞ SAYILMAZ (kaynak README:33).
# --------------------------------------------------------------------------
def _kosul_onceki_kayit(c: Kosu):
    v = bool(c.k1.get("onceki_kayit_var"))
    return v, f"k1.onceki_kayit_var={c.k1.get('onceki_kayit_var')}"


def _kosul_seviye(c: Kosu):
    return bool(c.seviyeler), f"k3.seviyeler={list(c.seviyeler) or 'boş'}"


def _kosul_gorsel(c: Kosu):
    v = "gorsel" in (c.k1.get("zorunlu_girdiler") or {})
    return v, f"k1.zorunlu_girdiler={list((c.k1.get('zorunlu_girdiler') or {}))}"


def _kosul_turev(c: Kosu):
    v = isinstance(c.motorlar.get("turev-akis"), dict)
    return v, f"turev-akis motor çıktısı {'var' if v else YOK}"


def _kosul_korelasyon(c: Kosu):
    v = bool(c.job.get("korelasyon"))
    return v, f"_job.korelasyon={'beyan edildi' if v else 'beyan yok'}"


def _kosul_emir(c: Kosu):
    e = str(c.zirve.get("EMIR", "") or c.emir.get("EMIR", ""))
    v = e.startswith(("MARKET", "LIMIT"))
    return v, f"EMIR={e[:60] or YOK}"


def _kosul_emir_usd(c: Kosu):
    v1, k1 = _kosul_emir(c)
    v2 = bool(c.job.get("usd_profil"))
    return (v1 and v2), f"{k1}; _job.usd_profil={'beyan edildi' if v2 else 'beyan yok'}"


KOSUL = {
    "onceki-kosu-kaydi-var": _kosul_onceki_kayit,
    "seviye-uretildi": _kosul_seviye,
    "gorsel-okuma-var": _kosul_gorsel,
    "turev-motoru-kostu": _kosul_turev,
    "korelasyon-beyan-edildi": _kosul_korelasyon,
    "emir-dogdu": _kosul_emir,
    "emir-dogdu + usd-profil-beyan": _kosul_emir_usd,
}


# --------------------------------------------------------------------------
# DENETÇİLER — her biri (gecti: bool, kanit: str) döner.
# --------------------------------------------------------------------------
def _g1(c: Kosu):
    olc = c.k1.get("olcumler") or {}
    m15, h4 = olc.get("m15_bar"), olc.get("h4_bar")
    kline = isinstance(m15, int) and m15 > 0 and isinstance(h4, int) and h4 > 0
    csv_ok = bool(c.k1.get("profil"))
    ok = bool(c.k1.get("gecti")) and (kline or csv_ok)
    return ok, (f"gecti={c.k1.get('gecti')}, m15_bar={m15}, h4_bar={h4}, "
                f"ohlcv profili={'var' if csv_ok else 'yok'}")


def _g2(c: Kosu):
    yasak = [a for a in ("karar", "yon", "stance", "sinyal") if a in c.k1]
    return (not yasak), (f"K1'de çıkarım alanı: {yasak or 'yok'} "
                         "(gozlemci.py:105 ile aynı liste)")


def _g3(c: Kosu):
    z = c.k1.get("zorunlu_girdiler") or {}
    eksik = c.k1.get("zorunlu_eksik") or []
    ok = ("likidasyon" in z) and ("gorsel" in z) and not eksik
    return ok, f"zorunlu_girdiler={sorted(z)}, zorunlu_eksik={len(eksik)} madde"


def _g4(c: Kosu):
    taz = c.k1.get("zorunlu_tazelik") or []
    if not taz:
        return False, f"zorunlu_tazelik {YOK} — tazelik hiç ölçülmemiş"
    kotu = [t for t in taz if ("BAYAT" in str(t)) or ("damga" in str(t) and "YOK" in str(t))
            or str(t).startswith(YOK)]
    return (not kotu), (f"{len(taz)} tazelik satırı, bayat/damgasız: {kotu or 'yok'} "
                        f"(tolerans {ESIK['tazelik_dk']} dk)")


def _g5(c: Kosu):
    kanal = c.k1.get("kanallar") or {}
    eksikler = c.k1.get("eksikler") or []
    kayip = [k for k, v in kanal.items()
             if v == YOK and not any(k in str(e) for e in eksikler)]
    return (not kayip), f"gerekçesiz düşen kanal: {kayip or 'yok'} ({len(eksikler)} gerekçe)"


def _g6(c: Kosu):
    ak = c.k1.get("onceki_karar_akibeti") or {}
    durum = str(ak.get("durum", ""))
    if durum.startswith("ölçüm HATASI"):
        return False, f"akıbet ölçüm HATASI: {durum[:80]}"
    if durum == "ÖLÇÜLDÜ":
        r = _f(ak.get("gercek_r"))
        return (r is not None), (f"ÖLÇÜLDÜ: sonuç={ak.get('sonuc')}, gerçek R={ak.get('gercek_r')}, "
                                 f"seviyeler={ak.get('verilen_seviyeler')}")
    gerekce = str(ak.get("sonuc") or durum or "")
    return bool(gerekce.strip()), f"ölçülemedi ama gerekçe yazılı: {gerekce[:90] or YOK}"


def _kp1(c: Kosu):
    n = c.k2.get("motor_sayisi")
    n = n if isinstance(n, int) else len(c.motorlar)
    ok = bool(c.k2.get("gecti")) and n >= ESIK["min_motor_k2"]
    return ok, f"motor_sayisi={n} (kapı >= {ESIK['min_motor_k2']}), gecti={c.k2.get('gecti')}"


def _kp2(c: Kosu):
    n = len(c.danismanlar)
    ok = bool(c.k3.get("gecti")) and n >= ESIK["min_danisman_k3"]
    return ok, (f"danışman={n} (kapı >= {ESIK['min_danisman_k3']}): "
                f"{[d.get('name') for d in c.danismanlar]}")


def _kp3(c: Kosu):
    sig = []
    for ad, alanlar in SEMA_DERINLIK.items():
        if ad in c.motorlar:
            eksik = [a for a in alanlar if a not in (c.motorlar[ad] or {})]
            if eksik:
                sig.append(f"{ad}: {eksik}")
    kosan = [a for a in SEMA_DERINLIK if a in c.motorlar]
    return (not sig), (f"{len(kosan)} şemalı motor denetlendi; eksik alan: "
                       f"{'; '.join(sig) if sig else 'yok'}")


def _kp4(c: Kosu):
    hatalar = c.k2.get("hatalar") or []
    bozuk = [h for h in hatalar if not (isinstance(h, dict) and h.get("motor") and h.get("hata"))]
    yon_uretebilen = {"karar-motoru", "grafik-calisma", "turev-akis"} & set(c.motorlar)
    giren = {d.get("name") for d in c.danismanlar}
    notlar = c.k3.get("notlar") or []
    dusen = yon_uretebilen - giren
    sessiz = {ad for ad in dusen if not any(ad in str(n) for n in notlar)}
    ok = (not bozuk) and (not sessiz)
    return ok, (f"gerekçesiz düşen motor: {sorted(sessiz) or 'yok'}; "
                f"eksik gerekçeli hata kaydı: {len(bozuk)}")


def _kp5(c: Kosu):
    ek = c.k5.get("esik_kalibrasyonu")
    if not isinstance(ek, dict):
        return False, f"esik_kalibrasyonu alanı {YOK}"
    kal = ek.get("esikler") or {}
    uyg = c.sentez.get("esikler") or {}
    if not kal:
        kaynak = str(ek.get("kaynak", ""))
        etiketli = ("KALİBRE EDİLEMEDİ" in kaynak) or ("STATİK" in kaynak.upper())
        return etiketli, f"eşik türetilemedi; kaynak etiketi: {kaynak[:90] or YOK}"
    ayrik = [k for k in kal
             if _f(uyg.get(k)) is None or abs(float(kal[k]) - float(uyg[k])) > 1e-6]
    return (not ayrik), (f"kalibre={kal} | uygulanan={ {k: uyg.get(k) for k in kal} } "
                         f"| ayrışan: {ayrik or 'yok'}")


def _kp6(c: Kosu):
    hukum = str(c.islem.get("hukum", ""))
    adaylar = c.islem.get("adaylar") or []
    if hukum.startswith("TEMİZ GİRİŞ VAR"):
        kotu = []
        for a in adaylar:
            r = _f(a.get("R_gercekci"))
            if a.get("rr_verdict") != "TUTARLI" or r is None or r < ESIK["r_min"]:
                kotu.append(f"{a.get('motor')}: R_gercekci={a.get('R_gercekci')}, "
                            f"verdict={a.get('rr_verdict')}")
        ok = bool(adaylar) and not kotu
        return ok, (f"TEMİZ GİRİŞ VAR, {len(adaylar)} aday; kapıyı geçmeyen: "
                    f"{kotu or 'yok'} (R_min={ESIK['r_min']})")
    engeller = c.islem.get("engeller") or []
    ozet = str(c.islem.get("ozet", "")).strip()
    ok = bool(engeller) or bool(ozet)
    return ok, (f"hüküm={hukum or YOK}; engel gerekçesi={len(engeller)} madde; "
                f"ozet={'var' if ozet else 'yok'}")


def _d1(c: Kosu):
    ozet = c.sentez.get("danisman_ozeti") or []
    pen = _f((c.sentez.get("esikler") or {}).get("refute_penalty")) or ESIK["refute_penalty"]
    ger = c.k4.get("dogrulama_gerekceleri") or {}
    kotu = []
    sayac = 0
    for r in ozet:
        if r.get("dogrulandi"):
            continue
        sayac += 1
        conf, eff = _f(r.get("guven")), _f(r.get("etkin_agirlik"))
        if conf is None or eff is None or abs(eff - conf * pen) > 1e-3:
            kotu.append(f"{r.get('ad')}: etkin={eff} ≠ güven {conf} × {pen}")
        elif not (str(r.get("curutme") or "").strip() or str(ger.get(r.get("ad"), "")).strip()):
            kotu.append(f"{r.get('ad')}: çürütme gerekçesi yazılmamış")
    return (not kotu), (f"{sayac} doğrulanmamış danışman, penaltı={pen}; "
                        f"kural dışı: {kotu or 'yok'}")


def _d2(c: Kosu):
    if not c.danismanlar:
        return False, "danışman yok — doğrulama seçiciliği ölçülemez"
    curutulen = [a for a, v in c.verifier.items() if (v or {}).get("confirmed") is False]
    kapsanmayan = [d.get("name") for d in c.danismanlar if d.get("name") not in c.verifier]
    ok = bool(curutulen) or bool(kapsanmayan)
    return ok, (f"çürütme={curutulen or 'yok'}, verifier'da kapsanmayan="
                f"{kapsanmayan or 'yok'}, onay="
                f"{[a for a, v in c.verifier.items() if (v or {}).get('confirmed')]}")


def _d3(c: Kosu):
    rr = c.k4.get("rr_denetimi") or {}
    atlanan = sorted(set(c.seviyeler) - set(rr))
    sorunlu = []
    for ad, rap in rr.items():
        v = (rap or {}).get("verdict")
        if not v:
            sorunlu.append(f"{ad}: verdict {YOK}")
        elif str(v).startswith("ŞİŞİ") and (c.verifier.get(ad) or {}).get("confirmed") is not False:
            sorunlu.append(f"{ad}: ŞİŞİRİLMİŞ ama doğrulaması çürütülmemiş")
    ok = (not atlanan) and (not sorunlu)
    return ok, (f"seviye={sorted(c.seviyeler)}, denetlenen={sorted(rr)}, "
                f"atlanan={atlanan or 'yok'}, sorun={sorunlu or 'yok'}")


def _d4(c: Kosu):
    onayli = [a for a, v in c.verifier.items() if (v or {}).get("confirmed")]
    aileler = {AILE.get(a, "bilinmeyen") for a in onayli}
    ok = len(aileler) >= ESIK["min_kanit_ailesi"]
    return ok, (f"onaylı danışman={onayli or 'yok'} → aile={sorted(aileler) or 'yok'} "
                f"(gerek >= {ESIK['min_kanit_ailesi']})")


def _d5(c: Kosu):
    ger = c.k4.get("dogrulama_gerekceleri") or {}
    dairesel = []
    for ad, g in ger.items():
        kaynaklar = [x for x in ("smc_tespit", "setup_dogrulama", "backtest",
                                 "rr_denetim", "R_MIN") if x in str(g)]
        if ad in str(g) and not [k for k in kaynaklar if k != ad]:
            dairesel.append(f"{ad} ← {str(g)[:60]}")
    return (not dairesel), (f"{len(ger)} doğrulama gerekçesi; dairesel: "
                            f"{dairesel or 'yok'}")


def _d6(c: Kosu):
    ct = c.k5.get("celiski_turu")
    if not isinstance(ct, dict):
        return False, f"celiski_turu alanı {YOK} — adversarial ikinci koşu yapılmamış"
    if not ct.get("yon_dayaniksiz"):
        return True, str(ct.get("hukum", YOK))[:110]
    karar = str(c.sentez.get("KARAR", ""))
    emir = str(c.zirve.get("EMIR", ""))
    ok = (karar == "NÖTR-BEKLE") and emir.startswith("EMİR YOK")
    return ok, (f"yön DAYANIKSIZ → KARAR={karar}, EMIR={emir[:40]} "
                "(fail-closed NÖTR + emir yok bekleniyor)")


def _d7(c: Kosu):
    d = c.danisman("gorsel-teyit")
    if d is None:
        return False, "görsel okuma geldi ama gorsel-teyit danışmanı kurula girmemiş"
    ham = _f(d.get("_ham_confidence"))
    ham = ham if ham is not None else _f(d.get("confidence"))
    v = c.verifier.get("gorsel-teyit") or {}
    reason = str(v.get("reason", ""))
    tavan_ok = ham is not None and ham <= ESIK["gorsel_tavan"] + 1e-9
    teyit_ok = ("smc_tespit" in reason) and ("trend" in reason)
    bayrak_ok = True
    if v.get("confirmed") is False:
        bayrak_ok = any("GÖRSEL-MEKANİK ÇELİŞKİSİ" in str(x)
                        for x in (c.k4.get("celiskiler") or []))
    ok = tavan_ok and teyit_ok and bayrak_ok
    return ok, (f"ham güven={ham} (tavan {ESIK['gorsel_tavan']}), teyit='{reason[:70]}', "
                f"uyumsuzluk bayrağı={'gerekmedi' if v.get('confirmed') else bayrak_ok}")


def _d8(c: Kosu):
    tv = c.motorlar.get("turev-akis") or {}
    kapsam = _f((tv.get("rapor") or {}).get("kapsam"))
    dan = tv.get("danisman") or {}
    if kapsam is None:
        return False, f"türev kapsamı {YOK} — kanal ölçülmemiş"
    beklenen = kapsam >= ESIK["turev_kapsam_esigi"]
    gercek = dan.get("_verifier_confirmed")
    ok = (gercek is None) or (bool(gercek) == beklenen)
    return ok, (f"kapsam={kapsam} (eşik {ESIK['turev_kapsam_esigi']}) → beklenen doğrulama"
                f"={beklenen}, danışmanda={gercek}")


def _d9(c: Kosu):
    kor = c.motorlar.get("korelasyon")
    if not isinstance(kor, dict):
        return False, "korelasyon BEYAN EDİLDİ ama motor sonucu yok (sessiz atlama)"
    rho = _f(kor.get("korelasyon"))
    carp = _f(kor.get("toplam_risk_carpani"))
    hukum = str(kor.get("HUKUM", YOK))
    tasindi = any("KORELASYON" in str(x) for x in (c.k4.get("celiskiler") or []))
    ok = rho is not None and tasindi
    if ok and abs(rho) >= ESIK["kopya_esigi"]:
        ok = ("KOPYA" in hukum) and carp == ESIK["kopya_risk_kat"]
    return ok, (f"ρ={rho}, HUKUM={hukum}, risk çarpanı={carp} "
                f"(kopya eşiği {ESIK['kopya_esigi']}), K4'e taşındı={tasindi}")


def _c1(c: Kosu):
    iki = c.zirve.get("iki_satir") or {}
    yon = str(c.zirve.get("YON_BIAS", ""))
    ok = (bool(str(iki.get("1_YON", "")).strip())
          and bool(str(iki.get("2_ISLEM_KALITESI", "")).strip())
          and yon in ("LONG", "SHORT", "NÖTR"))
    return ok, (f"YON_BIAS={yon or YOK}; 1_YON={'dolu' if iki.get('1_YON') else 'boş'}, "
                f"2_ISLEM_KALITESI={'dolu' if iki.get('2_ISLEM_KALITESI') else 'boş'}")


def _c2(c: Kosu):
    ys = _f(c.sentez.get("yon_skoru"))
    if ys is None:
        ys = _f(c.zirve.get("yon_skoru"))
    yb = str(c.zirve.get("YON_BIAS", "") or c.sentez.get("YON_BIAS", ""))
    if ys is None:
        return False, f"yon_skoru {YOK} — yönün mekanik türediği kanıtlanamıyor"
    ok = (ys > 0 and yb == "LONG") or (ys < 0 and yb == "SHORT") or (ys == 0 and yb == "NÖTR")
    return ok, f"yon_skoru={ys} → beklenen yön={'LONG' if ys > 0 else 'SHORT' if ys < 0 else 'NÖTR'}, basılan={yb}"


def _c3(c: Kosu):
    e = str(c.zirve.get("EMIR", "") or "")
    if EMIR_KALIP.match(e.strip()):
        return True, f"emir biçimi sözleşmeye uygun: {e}"
    if e.startswith("EMİR YOK"):
        nedenler = (c.zirve.get("emir_red_nedenleri") or [])
        gerekce = str(c.zirve.get("EMIR_GEREKCE", "")).strip()
        ok = bool(nedenler) or bool(gerekce) or len(e) > len("EMİR YOK")
        return ok, (f"EMİR YOK; gerekçe={'var' if ok else 'YOK (çıplak red)'} "
                    f"({(nedenler[:1] or [gerekce or e])[0]!s:.90})")
    return False, f"EMIR alanı biçim dışı: {e[:70] or YOK}"


def _c4(c: Kosu):
    g = c.zirve.get("gecersizlik")
    ok = isinstance(g, str) and bool(g.strip())
    return ok, f"gecersizlik={str(g)[:80] if g is not None else YOK}"


def _c5(c: Kosu):
    ze = c.zirve.get("ZORUNLU_EKSIK")
    if not isinstance(ze, list):
        return False, "ZIRVE.ZORUNLU_EKSIK alanı yok (eksik girdi en üstte taşınmıyor)"
    celiski = " || ".join(str(x) for x in (c.k4.get("celiskiler") or []))
    tasinmayan = [e for e in ze if str(e)[:40] not in celiski]
    return (not tasinmayan), (f"{len(ze)} zorunlu eksik; K4 çelişkilerine taşınmayan: "
                              f"{tasinmayan or 'yok'}")


def _c6(c: Kosu):
    if not c.denetim:
        return False, f"DENETIM alanı {YOK} — gözlemci koşmamış"
    muhur = bool(c.denetim.get("muhurlendi"))
    kritik = c.denetim.get("kritik_ihlal")
    if kritik is None:
        # Alan yoksa kritik ihlal ihlal listesinden TÜRETİLİR (kod kümesi
        # gozlemci.py:43 ile aynı) — eksik alan "kritik yok" sayılmaz.
        kritik = [x for x in (c.denetim.get("ihlal") or [])
                  if any(k in str(x) for k in KRITIK_KOD)]
    if not muhur:
        return (not kritik), (f"mühür yok; kritik ihlal={len(kritik)}; "
                              f"özet={c.denetim.get('ozet', YOK)}")
    ik = str(c.zirve.get("ISLEM_KALITESI", ""))
    em = str(c.zirve.get("EMIR", ""))
    ok = ("DENETİM İHLALİ" in ik) and ("DENETİM MÜHÜRÜ" in em)
    return ok, f"MÜHÜRLÜ ({len(kritik)} kritik ihlal) → ISLEM='{ik[:40]}', EMIR='{em[:40]}'"


def _c7(c: Kosu):
    durum = str(c.kiyas.get("durum", ""))
    yd = c.kiyas.get("YON_DEGISIMI") or {}
    ok = (durum == "KIYASLANDI") and bool(str(yd.get("etiket", "")).strip())
    return ok, (f"KIYAS.durum={durum or YOK}, etiket={yd.get('etiket', YOK)} "
                f"({yd.get('onceki', YOK)} → {yd.get('yeni', YOK)})")


def _c8(c: Kosu):
    alt = _sayilar({"k3": c.k3, "k4": c.k4, "sentez": c.sentez,
                    "islem": c.islem})
    ust = _sayilar({k: v for k, v in c.zirve.items()
                    if k in ("yon_skoru", "guven_skoru", "uzlasi", "seviyeler")})
    kaynaksiz = sorted(x for x in ust if x not in alt)
    return (not kaynaksiz), (f"zirvede {len(ust)} sayı denetlendi; alt katmanda "
                             f"karşılığı olmayan: {kaynaksiz[:6] or 'yok'}")


def _c9(c: Kosu):
    ayr = (c.k5.get("kalibrasyon") or {}).get("ayrinti") or {}
    if not ayr:
        return False, f"kalibrasyon.ayrinti {YOK} — ağırlık kanıtı yok"
    kotu = []
    for motor, a in ayr.items():
        n, w = a.get("n"), _f(a.get("agirlik"))
        if n is None or not a.get("kaynak") or w is None:
            kotu.append(f"{motor}: n/kaynak/agirlik eksik")
            continue
        if not (ESIK["agirlik_alt"] - 1e-9 <= w <= ESIK["agirlik_ust"] + 1e-9):
            kotu.append(f"{motor}: ağırlık {w} sınır dışı")
        elif n < ESIK["n_taban"] and abs(w - 1.0) > 1e-9:
            kotu.append(f"{motor}: n={n} < {ESIK['n_taban']} ama ağırlık {w} ≠ 1.0")
    return (not kotu), (f"{len(ayr)} motor defteri: "
                        + "; ".join(f"{m}(n={a.get('n')}→{a.get('agirlik')})"
                                    for m, a in ayr.items())
                        + f" | kural dışı: {kotu or 'yok'}")


# ---------------------------- EMİR rubriği --------------------------------
def _adaylar(c: Kosu):
    return c.zirve.get("emir_adaylari") or c.emir.get("adaylar") or []


def _e1(c: Kosu):
    e = str(c.zirve.get("EMIR", "") or c.emir.get("EMIR", "")).strip()
    m = EMIR_KALIP.match(e)
    return bool(m), f"EMIR='{e}' → kalıp {'uydu' if m else 'UYMADI'}"


def _e2(c: Kosu):
    yon = str(c.zirve.get("YON_BIAS", "")).upper()
    yanlis = [a.get("yon") for a in _adaylar(c) if str(a.get("yon", "")).upper() != yon]
    return (not yanlis), f"YON_BIAS={yon}, aday yönleri={[a.get('yon') for a in _adaylar(c)]}"


def _e3(c: Kosu):
    supheli = [f"{a.get('giris')}:{a.get('rr_denetim')}" for a in _adaylar(c)
               if a.get("rr_denetim") != "TUTARLI"]
    ad = _adaylar(c)
    return (bool(ad) and not supheli), (f"{len(ad)} aday; TUTARLI olmayan: "
                                        f"{supheli or 'yok'}")


def _e4(c: Kosu):
    kotu = []
    for a in _adaylar(c):
        r = _f(a.get("R"))
        if r is None or r < ESIK["r_min"]:
            kotu.append(f"{a.get('giris')}: R={a.get('R')}")
    ad = _adaylar(c)
    return (bool(ad) and not kotu), (f"R_min={ESIK['r_min']}; kapıyı geçmeyen: "
                                     f"{kotu or 'yok'} | R'ler={[a.get('R') for a in ad]}")


def _e5(c: Kosu):
    izler = ("FVG", "swing", "fiyat", "profil", "likidite")
    kotu = []
    for a in _adaylar(c):
        g = str(a.get("giris_gerekcesi", ""))
        if not (g and a.get("stop_gerekcesi") and a.get("hedef_gerekcesi")):
            kotu.append(f"{a.get('giris')}: gerekçe eksik")
        elif not any(x.lower() in g.lower() for x in izler):
            kotu.append(f"{a.get('giris')}: giriş gerekçesi ölçülen yapıya bağlı değil ({g[:40]})")
    ad = _adaylar(c)
    return (bool(ad) and not kotu), f"{len(ad)} aday; gerekçesi ölçüme bağlanmayan: {kotu or 'yok'}"


def _e6(c: Kosu):
    atr = _f((c.emir.get("yapi_ozeti") or {}).get("atr15"))
    fiyat = _f(c.emir.get("fiyat"))
    if atr is None or fiyat is None:
        return False, f"ATR15/fiyat {YOK} — MARKET/LIMIT ayrımı doğrulanamıyor"
    tol = ESIK["market_tolerans_atr"] * atr
    kotu = []
    for a in _adaylar(c):
        g = _f(a.get("giris"))
        if g is None:
            kotu.append(f"{a.get('giris')}: giriş sayısal değil")
            continue
        yakin = abs(g - fiyat) <= tol
        tip = str(a.get("emir_tipi", ""))
        if (tip == "MARKET") != yakin:
            kotu.append(f"{g}: tip={tip} ama |giriş−fiyat|={round(abs(g - fiyat), 4)} "
                        f"vs tolerans {round(tol, 4)}")
    return (not kotu), (f"fiyat={fiyat}, ATR15={round(atr, 4)}, tolerans={round(tol, 4)}; "
                        f"tutarsız: {kotu or 'yok'}")


def _e7(c: Kosu):
    kotu = [a.get("giris") for a in _adaylar(c)
            if not str(a.get("gecersizlik", "")).strip()
            or str(a.get("stop")) not in str(a.get("gecersizlik", ""))]
    ad = _adaylar(c)
    return (bool(ad) and not kotu), f"{len(ad)} aday; geçersizlik cümlesi eksik/stopsuz: {kotu or 'yok'}"


def _e8(c: Kosu):
    muhur = bool(c.denetim.get("muhurlendi"))
    return (not muhur), (f"DENETIM.muhurlendi={muhur}; kritik ihlal="
                         f"{len(c.denetim.get('kritik_ihlal') or [])}")


def _e9(c: Kosu):
    kotu = []
    for a in _adaylar(c):
        u = a.get("usd_hedef") or {}
        if str(u.get("HUKUM")) != "UYGUN":
            kotu.append(f"{a.get('giris')}: usd_hedef={u.get('HUKUM', YOK)}")
    ad = _adaylar(c)
    return (bool(ad) and not kotu), f"{len(ad)} aday; usd_hedef kapısını geçmeyen: {kotu or 'yok'}"


DENETCI = {
    "G1": _g1, "G2": _g2, "G3": _g3, "G4": _g4, "G5": _g5, "G6": _g6,
    "KP1": _kp1, "KP2": _kp2, "KP3": _kp3, "KP4": _kp4, "KP5": _kp5, "KP6": _kp6,
    "D1": _d1, "D2": _d2, "D3": _d3, "D4": _d4, "D5": _d5,
    "D6": _d6, "D7": _d7, "D8": _d8, "D9": _d9,
    "Ç1": _c1, "Ç2": _c2, "Ç3": _c3, "Ç4": _c4, "Ç5": _c5,
    "Ç6": _c6, "Ç7": _c7, "Ç8": _c8, "Ç9": _c9,
    "E1": _e1, "E2": _e2, "E3": _e3, "E4": _e4, "E5": _e5,
    "E6": _e6, "E7": _e7, "E8": _e8, "E9": _e9,
}


# --------------------------------------------------------------------------
# Rubrik yükleme + puanlama
# --------------------------------------------------------------------------
def rubrik_yukle(yol) -> list:
    """CSV'yi yükle. Sütunlar kaynak sözleşmesiyle BİREBİR aynı olmalı."""
    p = Path(yol).expanduser()
    if not p.exists():
        raise RubrikError(f"Rubrik dosyası yok: {p}")
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        basliklar = tuple(r.fieldnames or ())
        if basliklar != SUTUNLAR:
            raise RubrikError(
                f"{p.name}: sütunlar kaynak şemasıyla aynı değil.\n"
                f"  beklenen: {SUTUNLAR}\n  bulunan : {basliklar}")
        satirlar = [dict(x) for x in r if (x.get("ID") or "").strip()]
    if not satirlar:
        raise RubrikError(f"{p.name}: kriter yok")
    for s in satirlar:
        s["_rubrik"] = p.name
    return satirlar


def puanla(rapor: dict, kriterler: list) -> dict:
    """Her kriteri bağımsız puanla: GEÇTİ / DÜŞTÜ / ATLANDI / PUANLANMADI."""
    c = Kosu(rapor)
    sonuc = []
    for k in kriterler:
        kid = k["ID"].strip()
        kosul_ad = (k.get("Conditional") or "").strip()
        satir = {"ID": kid, "Bucket": k.get("Bucket", ""),
                 "Criterion": k.get("Criterion", ""),
                 "Conditional": kosul_ad, "rubrik": k.get("_rubrik", "")}
        # 1) Koşul: sağlanmazsa kriter ATLANIR — DÜŞMÜŞ SAYILMAZ (kaynak README:33)
        if kosul_ad:
            kfn = KOSUL.get(kosul_ad)
            if kfn is None:
                satir.update({"durum": PUANSIZ,
                              "kanit": f"koşul anahtarı tanınmadı: '{kosul_ad}' "
                                       "(fail-closed; GEÇTİ sayılmaz)"})
                sonuc.append(satir)
                continue
            saglandi, kkanit = kfn(c)
            satir["kosul_kaniti"] = kkanit
            if not saglandi:
                satir.update({"durum": ATLANDI,
                              "kanit": f"koşul sağlanmadı ({kosul_ad}): {kkanit}"})
                sonuc.append(satir)
                continue
        # 2) Denetçi
        fn = DENETCI.get(kid)
        if fn is None:
            satir.update({"durum": PUANSIZ,
                          "kanit": "bu kriterin deterministik denetçisi yok "
                                   "(fail-closed; GEÇTİ sayılmaz)"})
            sonuc.append(satir)
            continue
        try:
            gecti, kanit = fn(c)
        except Exception as e:  # noqa: BLE001 — denetçi hatası gizlenmez
            satir.update({"durum": PUANSIZ,
                          "kanit": f"denetçi HATASI ({type(e).__name__}: {e})"})
            sonuc.append(satir)
            continue
        satir.update({"durum": GECTI if gecti else DUSTU, "kanit": kanit})
        sonuc.append(satir)

    return {
        "sembol": rapor.get("sembol", YOK),
        "koşu_durumu": rapor.get("durum", YOK),
        "kriterler": sonuc,
        "kova_ozeti": _kova_ozeti(sonuc),
        "toplam": _toplam(sonuc),
        "not": ("BİRİNCİL ÖLÇÜM kriter-başına geçme oranıdır. Kaynak rubrik "
                "sözleşmesi: \"aggregate pass rates can mask meaningful gaps\" — "
                "toplam skor tek başına sunulmaz. Koşulu sağlanmayan kriter "
                "ATLANDI'dır, DÜŞMÜŞ SAYILMAZ."),
        "uyari": ("Bu bir KOŞU KALİTESİ notudur; piyasa yönü/kararı değildir. "
                  "Canlı/otomatik emir DAHİL DEĞİL."),
    }


def _oran(gecti, dustu):
    n = gecti + dustu
    return round(gecti / n, 4) if n else None


def _kova_ozeti(sonuc: list) -> dict:
    kova = {}
    for s in sonuc:
        k = kova.setdefault(s["Bucket"], {GECTI: 0, DUSTU: 0, ATLANDI: 0, PUANSIZ: 0})
        k[s["durum"]] += 1
    for k, v in kova.items():
        v["gecme_orani"] = _oran(v[GECTI], v[DUSTU])
        v["dusen_kriterler"] = [s["ID"] for s in sonuc
                                if s["Bucket"] == k and s["durum"] == DUSTU]
    return kova


def _toplam(sonuc: list) -> dict:
    say = {GECTI: 0, DUSTU: 0, ATLANDI: 0, PUANSIZ: 0}
    for s in sonuc:
        say[s["durum"]] += 1
    return {
        **say,
        "puanlanan": say[GECTI] + say[DUSTU],
        "gecme_orani": _oran(say[GECTI], say[DUSTU]),
        "uyari": ("İKİNCİL ÖLÇÜM — toplam geçme oranı anlamlı boşlukları "
                  "maskeleyebilir; kriter-başına dökümü okumadan karar verme."),
    }


def metin(rapor_puani: dict) -> str:
    L = ["=" * 78,
         f"RUBRİK KAPISI — koşu kalitesi notu | sembol: {rapor_puani.get('sembol', YOK)}",
         f"koşu durumu: {rapor_puani.get('koşu_durumu', YOK)}",
         "=" * 78,
         "① KRİTER-BAŞINA DÖKÜM (BİRİNCİL)"]
    isaret = {GECTI: "✔", DUSTU: "✖", ATLANDI: "–", PUANSIZ: "?"}
    kova_sirasi = []
    for s in rapor_puani["kriterler"]:
        if s["Bucket"] not in kova_sirasi:
            kova_sirasi.append(s["Bucket"])
    for kova in kova_sirasi:
        L.append(f"\n  [{kova}]")
        for s in rapor_puani["kriterler"]:
            if s["Bucket"] != kova:
                continue
            L.append(f"   {isaret.get(s['durum'], '?')} {s['ID']:<4} {s['durum']:<11} "
                     f"{s['Criterion'][:52]}")
            L.append(f"        ↳ {str(s['kanit'])[:150]}")
    L.append("\n" + "-" * 78)
    L.append("② KOVA BAŞINA GEÇME ORANI (BİRİNCİL)")
    for kova, v in rapor_puani["kova_ozeti"].items():
        oran = v["gecme_orani"]
        L.append(f"   {kova:<16} {v[GECTI]}/{v[GECTI] + v[DUSTU]} geçti "
                 f"(oran {oran if oran is not None else YOK}) | atlandı {v[ATLANDI]}"
                 + (f" | puanlanmadı {v[PUANSIZ]}" if v[PUANSIZ] else "")
                 + (f" | düşen: {', '.join(v['dusen_kriterler'])}" if v["dusen_kriterler"] else ""))
    t = rapor_puani["toplam"]
    L.append("-" * 78)
    L.append("③ TOPLAM (İKİNCİL — tek başına okunmaz)")
    L.append(f"   {t[GECTI]} geçti / {t[DUSTU]} düştü / {t[ATLANDI]} atlandı"
             + (f" / {t[PUANSIZ]} puanlanmadı" if t[PUANSIZ] else "")
             + f"  → geçme oranı {t['gecme_orani'] if t['gecme_orani'] is not None else YOK}")
    L.append(f"   ⚠ {t['uyari']}")
    L.append("-" * 78)
    L.append(rapor_puani["not"])
    L.append(f"⚠️ {rapor_puani['uyari']}")
    L.append("=" * 78)
    return "\n".join(L)


# --------------------------------------------------------------------------
# ÖZ-TEST — sahte koşu raporlarıyla senaryolar + (varsa) GERÇEK rapor
# --------------------------------------------------------------------------
def _sahte_tam_gecen() -> dict:
    """Her kriteri geçen (koşulluları dahil) sağlıklı koşu."""
    seviye = {"grafik-calisma": {"yon": "short", "entry": 63990.7, "stop": 64234.1,
                                 "target": 63461.2, "atr": 103.55,
                                 "kaynak": "confluence.py (tek-kaynak çıktı)"}}
    aday = {"emir_tipi": "LIMIT", "yon": "SHORT", "giris": 63990.7, "stop": 64234.1,
            "hedef": 63461.2, "R": 2.18, "rr_denetim": "TUTARLI", "risk_puan": 243.4,
            "giris_gerekcesi": "4H teyitli swing direnci",
            "stop_gerekcesi": "girişin üstündeki EN YAKIN teyitli swing (yapı stopu)",
            "hedef_gerekcesi": "yön tarafındaki ilk teyitli likidite",
            "gecersizlik": "64234.1 ötesinde 15M gövde kapanışı → kurulum iptal"}
    sentez = {
        "YON_BIAS": "SHORT", "KARAR": "SHORT", "guven_skoru": 0.4212,
        "yon_skoru": -0.7431, "uzlasi": 0.8123,
        "esikler": {"score": 0.3, "min_agreement": 0.55, "min_side_weight": 0.5,
                    "refute_penalty": 0.25},
        "danisman_ozeti": [
            {"ad": "karar-motoru", "yon": "short", "guven": 0.6, "dogrulandi": False,
             "etkin_agirlik": 0.15, "kanit": "SHORT (zincir 2, R=1.10)",
             "curutme": "R=1.10 < R_MIN=1.35"},
            {"ad": "grafik-calisma", "yon": "short", "guven": 0.85, "dogrulandi": True,
             "etkin_agirlik": 0.85, "kanit": "confluence=0.85", "curutme": None},
            {"ad": "turev-akis", "yon": "short", "guven": 0.4, "dogrulandi": True,
             "etkin_agirlik": 0.4, "kanit": "kapsam 1.0", "curutme": None},
            {"ad": "gorsel-teyit", "yon": "short", "guven": 0.5, "dogrulandi": True,
             "etkin_agirlik": 0.5, "kanit": "görsel okuma bear", "curutme": None}],
    }
    k1 = {
        "katman": "K1-LLM", "rol": "ham veri + bütünlük denetimi (çıkarım yok)",
        "kanallar": {"m15": "/veri/m15.json", "h4": "/veri/h4.json",
                     "ohlcv_csv": YOK, "returns_csv": YOK, "video": YOK},
        "olcumler": {"m15_bar": 200, "m15_son_bar": 1785000000000, "h4_bar": 200},
        "profil": None, "veri_sozlesmesi": None, "video": None,
        "eksikler": [f"ohlcv_csv: {YOK}", f"returns_csv: {YOK}", f"video: {YOK}"],
        "zorunlu_girdiler": {
            "likidasyon": {"liq_long": 12.4, "liq_short": 31.9,
                           "tazelik": "likidasyon: taze (son bara göre 12 dk)"},
            "gorsel": {"trend": "bear", "guven": 0.5,
                       "tazelik": "görsel okuma: taze (son bara göre 12 dk)"}},
        "zorunlu_eksik": [],
        "zorunlu_tazelik": ["likidasyon: taze (son bara göre 12 dk)",
                            "görsel okuma: taze (son bara göre 12 dk)"],
        "onceki_karar_akibeti": {"durum": "ÖLÇÜLDÜ", "sonuc": "HEDEF", "gercek_r": 1.8,
                                 "onceki_yon": "SHORT",
                                 "verilen_seviyeler": {"giris": 64500.0, "stop": 64800.0,
                                                       "hedef": 63900.0}},
        "onceki_kayit_var": True, "gecti": True, "kapi": "K1 kapısı GEÇİLDİ",
    }
    k2 = {
        "katman": "K2-AI-AJAN", "motor_sonuclari": {
            "karar-motoru": {"karar": {"karar": "SHORT", "zincir": 2, "r": 1.10},
                             "son_bar_utc": "2026-07-28 10:45",
                             "rejim_4h": {"rejim": "TREND"}},
            "smc_tespit": {"trend": "bear", "atr": 103.55,
                           "rejim": {"durum": "trend", "adx": 27.1}},
            "grafik-calisma": {"KARAR": "SHORT", "confluence_skoru": 0.85,
                               "kapi_gerekceleri": [], "giris_orta": 63990.7,
                               "gecersizlik_sl": 64234.1, "hedefler": [63461.2],
                               "atr_kullanildi": 103.55},
            "setup_dogrulama": {"SONUC": "EDGE VAR", "sinyal_izni": True,
                                "gerekce": "12 işlem, Wilson alt sınırı 0.55"},
            "smc_tespit_h4": {"trend": "bear", "atr": 608.01,
                              "likidite": [{"price": 63461.2}]},
            "korelasyon": {"korelasyon": 0.8939, "beta": 1.12, "gozlem": 200,
                           "HUKUM": "KOPYA POZİSYON", "toplam_risk_carpani": 2.0,
                           "cift": "BTC ↔ ETH"},
            "turev-akis": {"rapor": {"kapsam": 1.0, "yon_skoru": -0.41},
                           "danisman": {"name": "turev-akis", "stance": "short",
                                        "confidence": 0.4,
                                        "_verifier_confirmed": True}},
        },
        "hatalar": [], "motor_sayisi": 7, "gecti": True, "kapi": "K2 kapısı GEÇİLDİ",
    }
    k3 = {
        "katman": "K3-COKLU-AJAN",
        "danismanlar": [
            {"name": "karar-motoru", "stance": "short", "confidence": 0.6,
             "_ham_confidence": 0.6, "_agirlik": 1.0, "evidence": "SHORT zincir 2"},
            {"name": "grafik-calisma", "stance": "short", "confidence": 0.85,
             "_ham_confidence": 0.85, "_agirlik": 1.0, "evidence": "confluence 0.85"},
            {"name": "turev-akis", "stance": "short", "confidence": 0.4,
             "_ham_confidence": 0.4, "_agirlik": 1.0, "evidence": "kapsam 1.0"},
            {"name": "gorsel-teyit", "stance": "short", "confidence": 0.5,
             "_ham_confidence": 0.5, "_agirlik": 1.0, "evidence": "görsel bear"}],
        "seviyeler": seviye,
        "agirlik_kaynagi": {"agirliklar": {}, "kaynak": "agirlik.json"},
        "notlar": [f"gorsel-teyit güveni {ESIK['gorsel_tavan']} tavanıyla sınırlandı"],
        "gecti": True, "kapi": "K3 kapısı GEÇİLDİ",
    }
    k4 = {
        "katman": "K4-AGI",
        "verifier": {
            "karar-motoru": {"confirmed": False, "reason": "R=1.10 < R_MIN=1.35"},
            "grafik-calisma": {"confirmed": True, "reason": "setup_dogrulama EDGE VAR"},
            "turev-akis": {"confirmed": True, "reason": "kapsam 1.0 ≥ 0.5"},
            "gorsel-teyit": {"confirmed": True,
                             "reason": "mekanik smc_tespit trend=bear vs görsel okuma "
                                       "trend=bear — UYUMLU"}},
        "dogrulama_gerekceleri": {
            "karar-motoru": "R=1.10 vs R_MIN=1.35",
            "grafik-calisma": "setup_dogrulama: EDGE VAR — 12 işlem",
            "turev-akis": "kapsam 1.0 ≥ eşik 0.5",
            "gorsel-teyit": "mekanik smc_tespit trend=bear vs görsel okuma trend=bear"},
        "rr_denetimi": {"grafik-calisma": {"verdict": "TUTARLI", "R_rapor": 2.18,
                                           "R_gercekci": 2.18, "stop_atr": 2.35}},
        "celiskiler": [
            "KORELASYON RİSKİ: BTC ↔ ETH ρ=0.8939 → KOPYA POZİSYON; toplam risk ×2.0",
            "MTF bağlam: karar-motoru rejim=TREND | smc HTF=bear"],
        "mercekler": {}, "baglanmayan_mercekler": [],
        "gecti": True, "kapi": "K4 kapısı GEÇİLDİ",
    }
    k5 = {
        "katman": "K5-SI", "sentez": sentez,
        "esik_kalibrasyonu": {"esikler": {"score": 0.3, "min_agreement": 0.55,
                                          "min_side_weight": 0.5},
                              "kaynak": "VERİDEN TÜRETİLDİ: bootstrap gürültü tabanı"},
        "celiski_turu": {"kostu": True, "yon_ilk": "SHORT",
                         "yon_dogrulanmis_kurul": "SHORT", "yon_dayaniksiz": False,
                         "hukum": "ÇELİŞKİ TURU: yön DAYANIKLI"},
        "emir_plani": {"EMIR": "LIMIT SHORT @63990.7 | stop 64234.1 | T1 63461.2 | R 2.18",
                       "birincil": aday, "adaylar": [aday], "yon": "SHORT",
                       "fiyat": 63511.1, "red_nedenleri": [],
                       "yapi_ozeti": {"son_kapanis": 63511.1, "atr15": 103.55,
                                      "atr4h": 608.01, "bar15": 200, "bar4h": 200}},
        "islem_kalitesi": {
            "hukum": "TEMİZ GİRİŞ VAR",
            "ozet": "TEMİZ GİRİŞ VAR (grafik-calisma): giriş 63990.7, stop 64234.1",
            "adaylar": [{"motor": "grafik-calisma", **seviye["grafik-calisma"],
                         "R_gercekci": 2.18, "rr_verdict": "TUTARLI"}],
            "engeller": [], "seviyeler": seviye,
            "rr_denetimi": k4["rr_denetimi"]},
        "kalibrasyon": {"ayrinti": {"karar-motoru": {
            "n": 3, "wins": 2, "kaynak": "/engine/state/defter.jsonl",
            "wilson_lo": 0.29, "agirlik": 1.0,
            "durum": f"{YOK} — ölçülmüş sonuç 3 < n_taban 10; ağırlık DEĞİŞTİRİLMEDİ"}}},
        "gecti": True, "kapi": "K5 kapısı GEÇİLDİ",
    }
    zirve = {
        "YON_BIAS": "SHORT", "ISLEM_KALITESI": "TEMİZ GİRİŞ VAR",
        "sentez_karari": "SHORT", "guven_skoru": 0.4212, "yon_skoru": -0.7431,
        "uzlasi": 0.8123, "muhalefet": [], "kapi_gerekceleri": [],
        "gecersizlik": "4H kapanış 64500 üstü → kurulum iptal",
        "seviyeler": seviye, "ulasilan_katman": "K5-SI (zirve)",
        "ZORUNLU_EKSIK": [], "zorunlu_girdiler": ["likidasyon", "gorsel"],
        "EMIR": "LIMIT SHORT @63990.7 | stop 64234.1 | T1 63461.2 | R 2.18",
        "EMIR_GEREKCE": "", "emir_adaylari": [aday], "emir_red_nedenleri": [],
        "CELISKI_TURU": "ÇELİŞKİ TURU: yön DAYANIKLI",
        "iki_satir": {"1_YON": "YÖN (bias): SHORT — ağırlıklı yön skoru -0.7431",
                      "2_ISLEM_KALITESI": "İŞLEM KALİTESİ: TEMİZ GİRİŞ VAR"},
    }
    return {
        "sistem": "PİRAMİT", "soru": "öz-test", "sembol": "TEST-TAM",
        "katmanlar": [k1, k2, k3, k4, k5], "ZIRVE": zirve,
        "_job": {"korelasyon": {"a": "m15.json", "b": "eth/m15.json"}},
        "KIYAS": {"durum": "KIYASLANDI",
                  "YON_DEGISIMI": {"onceki": "SHORT", "yeni": "SHORT",
                                   "etiket": "DEVAM", "skor_yeni": -0.7431},
                  "onemli_degisimler": ["ADX: 21.0 → 27.1 (+6.1)"]},
        "DENETIM": {"ozet": "26 denetim, 0 ihlal, 0 uyarı", "ihlal": [], "uyari": [],
                    "kritik_ihlal": [], "muhurlendi": False},
        "durum": "TAMAM — piramidin tepesine ulaşıldı",
    }


def _sahte_kismen_dusen() -> dict:
    """Sağlıklı koşudan bozulmuş: fail-OPEN doğrulama, eşik kayması, şişirilmiş R,
    uygulanmamış mühür, skorla çelişen yön, bayat zorunlu girdi."""
    r = json.loads(json.dumps(_sahte_tam_gecen(), ensure_ascii=False))
    r["sembol"] = "TEST-KISMEN"
    K = {k["katman"]: k for k in r["katmanlar"]}
    k1, k4, k5 = K["K1-LLM"], K["K4-AGI"], K["K5-SI"]
    z = r["ZIRVE"]

    # G3 + G4: bayat likidasyon (damga son bardan eski)
    k1["zorunlu_tazelik"][0] = ("likidasyon: BAYAT — okuma son bardan 700 dk eski "
                                f"(tolerans {ESIK['tazelik_dk']} dk)")
    k1["zorunlu_girdiler"].pop("likidasyon")
    k1["zorunlu_eksik"] = [k1["zorunlu_tazelik"][0]]
    k4["celiskiler"].append(f"ZORUNLU GİRDİ EKSİK — {k1['zorunlu_tazelik'][0]}")
    z["ZORUNLU_EKSIK"] = list(k1["zorunlu_eksik"])

    # D2: herkes onaylı, hiç çürütme yok (fail-OPEN)
    for ad in k4["verifier"]:
        k4["verifier"][ad] = {"confirmed": True, "reason": "onaylandı"}
    k5["sentez"]["danisman_ozeti"][0].update({"dogrulandi": True, "etkin_agirlik": 0.6})

    # D3: şişirilmiş R'ye rağmen danışman doğrulanmış
    k4["rr_denetimi"]["grafik-calisma"] = {"verdict": "ŞİŞİRİLMİŞ", "R_rapor": 4.0,
                                           "R_gercekci": 1.1, "stop_atr": 0.4}

    # KP5: kalibre eşik ile uygulanan eşik ayrıştı
    k5["sentez"]["esikler"]["score"] = 0.15

    # KP6: temiz giriş ilan edildi ama R kapının altında
    k5["islem_kalitesi"]["adaylar"][0].update({"R_gercekci": 1.10,
                                               "rr_verdict": "ŞİŞİRİLMİŞ"})

    # Ç2: yön skorun işaretiyle çelişiyor
    z["YON_BIAS"] = "LONG"

    # Ç6: kritik ihlal var ama işlem/emir hâlâ açık (mühür uygulanmamış)
    r["DENETIM"] = {"ozet": "26 denetim, 2 ihlal, 1 uyarı",
                    "ihlal": ["K4-AGI/UYDURMA: ...", "K5-SI/MEMNUN_ETME: ..."],
                    "uyari": [], "kritik_ihlal": ["K4-AGI/UYDURMA: kaynaksız sayı"],
                    "muhurlendi": True}
    return r


def _sahte_kosullu_atlanan() -> dict:
    """İlk analiz: önceki kayıt yok, görsel yok, türev yok, korelasyon beyanı yok,
    seviye üretilmedi, emir doğmadı → koşullu kriterler ATLANIR (düşmez)."""
    k1 = {
        "katman": "K1-LLM",
        "kanallar": {"m15": "/veri/m15.json", "h4": "/veri/h4.json", "video": YOK},
        "olcumler": {"m15_bar": 180, "m15_son_bar": 1785000000000, "h4_bar": 150},
        "eksikler": [f"video: {YOK}"],
        "zorunlu_girdiler": {"likidasyon": {"liq_long": 5.0, "liq_short": 4.0}},
        "zorunlu_eksik": ["görsel okuma: grafik ekran görüntüsü/video GELMEDİ"],
        "zorunlu_tazelik": ["likidasyon: taze (son bara göre 30 dk)"],
        "onceki_karar_akibeti": {"durum": f"{YOK} — önceki koşu kaydı yok (ilk analiz)"},
        "onceki_kayit_var": False, "gecti": True, "kapi": "K1 kapısı GEÇİLDİ",
    }
    k2 = {
        "katman": "K2-AI-AJAN", "motor_sonuclari": {
            "karar-motoru": {"karar": {"karar": "BEKLE", "zincir": 3, "r": 0.8},
                             "son_bar_utc": "2026-07-28 06:45",
                             "rejim_4h": {"rejim": "FLAT"}},
            "smc_tespit": {"trend": "yatay", "atr": 88.2,
                           "rejim": {"durum": "range", "adx": 14.0}},
            "grafik-calisma": {"KARAR": "NÖTR-BEKLE", "confluence_skoru": 0.42,
                               "kapi_gerekceleri": ["R:R 0.9 < 2.0"]},
            "setup_dogrulama": {"SONUC": "VERİ YETERSİZ", "sinyal_izni": False,
                                "gerekce": "işlem 6 < taban 10"},
        },
        "hatalar": [{"motor": "turev-akis", "hata": f"türev paneli {YOK}"}],
        "motor_sayisi": 4, "gecti": True, "kapi": "K2 kapısı GEÇİLDİ",
    }
    k3 = {
        "katman": "K3-COKLU-AJAN",
        "danismanlar": [
            {"name": "karar-motoru", "stance": "flat", "confidence": 0.4,
             "_ham_confidence": 0.4, "_agirlik": 1.0, "evidence": "BEKLE"},
            {"name": "grafik-calisma", "stance": "flat", "confidence": 0.42,
             "_ham_confidence": 0.42, "_agirlik": 1.0, "evidence": "NÖTR-BEKLE"}],
        "seviyeler": {}, "notlar": [],
        "agirlik_kaynagi": {"agirliklar": {}, "kaynak": f"agirlik.json {YOK} — ilk koşu"},
        "gecti": True, "kapi": "K3 kapısı GEÇİLDİ",
    }
    k4 = {
        "katman": "K4-AGI",
        "verifier": {"karar-motoru": {"confirmed": False},
                     "grafik-calisma": {"confirmed": False,
                                        "reason": "işlem 6 < taban 10"}},
        "dogrulama_gerekceleri": {
            "karar-motoru": "R=0.8 vs R_MIN=1.35",
            "grafik-calisma": "setup_dogrulama: VERİ YETERSİZ — işlem 6 < taban 10"},
        "rr_denetimi": {},
        "celiskiler": ["ZORUNLU GİRDİ EKSİK — görsel okuma: grafik ekran görüntüsü/video "
                       "GELMEDİ",
                       "KLİNE KÖRLÜĞÜ AÇIK: türev kanalı kurula girmedi"],
        "mercekler": {}, "baglanmayan_mercekler": ["genisletici"],
        "gecti": True, "kapi": "K4 kapısı GEÇİLDİ",
    }
    sentez = {
        "YON_BIAS": "NÖTR", "KARAR": "NÖTR-BEKLE", "guven_skoru": 0.0,
        "yon_skoru": 0.0, "uzlasi": 1.0,
        "esikler": {"score": 0.25, "min_agreement": 0.5, "min_side_weight": 0.5,
                    "refute_penalty": 0.25},
        "danisman_ozeti": [
            {"ad": "karar-motoru", "yon": "nötr", "guven": 0.4, "dogrulandi": False,
             "etkin_agirlik": 0.1, "kanit": "BEKLE", "curutme": None},
            {"ad": "grafik-calisma", "yon": "nötr", "guven": 0.42, "dogrulandi": False,
             "etkin_agirlik": 0.105, "kanit": "NÖTR-BEKLE",
             "curutme": "işlem 6 < taban 10"}],
    }
    k5 = {
        "katman": "K5-SI", "sentez": sentez,
        "esik_kalibrasyonu": {"esikler": None,
                              "kaynak": "KALİBRE EDİLEMEDİ (örneklem küçük) → sentez "
                                        "STATİK KORKULUK kullanır (etiketli)"},
        "celiski_turu": {"kostu": False, "yon_dayaniksiz": False,
                         "hukum": "ÇELİŞKİ TURU: gerekmedi — doğrulanmış danışman yok"},
        "emir_plani": {"EMIR": "EMİR YOK", "yon": "NÖTR",
                       "gerekce": "yön NÖTR — yönsüz kurulumda giriş/stop tanımsız",
                       "red_nedenleri": ["yön NÖTR — yönsüz kurulumda giriş/stop tanımsız"],
                       "adaylar": []},
        "islem_kalitesi": {"hukum": "TEMİZ GİRİŞ YOK — TEPKİ/SEVİYE BEKLE",
                           "ozet": "Yön NÖTR ve motorlardan giriş/stop/hedef seti "
                                   f"gelmedi ({YOK})",
                           "adaylar": [], "engeller": [], "seviyeler": {},
                           "rr_denetimi": {}},
        "kalibrasyon": {"ayrinti": {"karar-motoru": {
            "n": 0, "wins": 0, "kaynak": "/engine/state/defter.jsonl", "agirlik": 1.0,
            "durum": f"{YOK} — ölçülmüş sonuç 0 < n_taban 10"}}},
        "gecti": True, "kapi": "K5 kapısı GEÇİLDİ",
    }
    zirve = {
        "YON_BIAS": "NÖTR", "ISLEM_KALITESI": "TEMİZ GİRİŞ YOK — TEPKİ/SEVİYE BEKLE",
        "sentez_karari": "NÖTR-BEKLE", "guven_skoru": 0.0, "yon_skoru": 0.0,
        "uzlasi": 1.0, "muhalefet": [], "kapi_gerekceleri": [],
        "gecersizlik": YOK, "seviyeler": {}, "ulasilan_katman": "K5-SI (zirve)",
        "ZORUNLU_EKSIK": list(k1["zorunlu_eksik"]),
        "zorunlu_girdiler": ["likidasyon"],
        "EMIR": "EMİR YOK", "EMIR_GEREKCE": "yön NÖTR — yönsüz kurulumda giriş/stop tanımsız",
        "emir_adaylari": [],
        "emir_red_nedenleri": ["yön NÖTR — yönsüz kurulumda giriş/stop tanımsız"],
        "CELISKI_TURU": "ÇELİŞKİ TURU: gerekmedi",
        "iki_satir": {"1_YON": "YÖN (bias): NÖTR — ağırlıklı yön skoru 0.0 (gerçek berabere)",
                      "2_ISLEM_KALITESI": "İŞLEM KALİTESİ: temiz giriş yok"},
    }
    return {
        "sistem": "PİRAMİT", "soru": "öz-test", "sembol": "TEST-KOSULLU",
        "katmanlar": [k1, k2, k3, k4, k5], "ZIRVE": zirve, "_job": {},
        "KIYAS": {"durum": f"{YOK} — kıyas için önceki koşu kaydı yok (ilk analiz)"},
        "DENETIM": {"ozet": "22 denetim, 0 ihlal, 2 uyarı", "ihlal": [],
                    "uyari": ["K4-AGI/TUNEL: doğrulanmış kanıt yalnız {} ailesinden"],
                    "kritik_ihlal": [], "muhurlendi": False},
        "durum": "TAMAM — piramidin tepesine ulaşıldı",
    }


def _self_test() -> int:
    ORNEK.mkdir(parents=True, exist_ok=True)
    ortak = rubrik_yukle(RUBRIKLER / "kosu_ortak.csv")
    emir = rubrik_yukle(RUBRIKLER / "emir.csv")
    tum = ortak + emir

    senaryolar = [
        ("tam_gecen", _sahte_tam_gecen(),
         {"max_dustu": 0, "max_puansiz": 0, "min_atlandi": 0}),
        ("kismen_dusen", _sahte_kismen_dusen(),
         {"min_dustu": 6, "max_puansiz": 0}),
        ("kosullu_atlanan", _sahte_kosullu_atlanan(),
         {"min_atlandi": 13, "max_puansiz": 0}),
    ]
    basarisiz = []
    for ad, rap, bekle in senaryolar:
        puan = puanla(rap, tum)
        t = puan["toplam"]
        (ORNEK / f"{ad}_kosu.json").write_text(
            json.dumps(rap, ensure_ascii=False, indent=2), encoding="utf-8")
        (ORNEK / f"{ad}_puan.txt").write_text(metin(puan), encoding="utf-8")
        (ORNEK / f"{ad}_puan.json").write_text(
            json.dumps(puan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(metin(puan))
        print()
        if "max_dustu" in bekle and t[DUSTU] > bekle["max_dustu"]:
            basarisiz.append(f"{ad}: DÜŞTÜ={t[DUSTU]} > {bekle['max_dustu']} "
                             + str([s["ID"] for s in puan["kriterler"]
                                    if s["durum"] == DUSTU]))
        if "min_dustu" in bekle and t[DUSTU] < bekle["min_dustu"]:
            basarisiz.append(f"{ad}: DÜŞTÜ={t[DUSTU]} < {bekle['min_dustu']}")
        if "min_atlandi" in bekle and t[ATLANDI] < bekle["min_atlandi"]:
            basarisiz.append(f"{ad}: ATLANDI={t[ATLANDI]} < {bekle['min_atlandi']}")
        if "max_puansiz" in bekle and t[PUANSIZ] > bekle["max_puansiz"]:
            basarisiz.append(f"{ad}: PUANLANMADI={t[PUANSIZ]} > {bekle['max_puansiz']} "
                             + str([s["ID"] for s in puan["kriterler"]
                                    if s["durum"] == PUANSIZ]))

    # --- GERÇEK koşu raporu (varsa) — sahte veriye karşı gerçek kontrol -----
    gercekler = sorted((SKILL.parent / "piramit-sistem" / "state").glob("son_rapor*.json"))
    for gp in gercekler:
        try:
            rap = json.loads(gp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"GERÇEK RAPOR OKUNAMADI {gp.name}: {e}")
            continue
        puan = puanla(rap, tum)
        (ORNEK / f"gercek_{gp.stem}_puan.txt").write_text(metin(puan), encoding="utf-8")
        (ORNEK / f"gercek_{gp.stem}_puan.json").write_text(
            json.dumps(puan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"### GERÇEK KOŞU: {gp}")
        print(metin(puan))
        print()
        if puan["toplam"][PUANSIZ]:
            basarisiz.append(f"{gp.name}: PUANLANMADI={puan['toplam'][PUANSIZ]}")

    # Rubrik bütünlüğü: her kriterin denetçisi ve tanınan koşulu olmalı
    for k in tum:
        if k["ID"].strip() not in DENETCI:
            basarisiz.append(f"rubrik: {k['ID']} için denetçi yok")
        ko = (k.get("Conditional") or "").strip()
        if ko and ko not in KOSUL:
            basarisiz.append(f"rubrik: {k['ID']} koşulu tanınmıyor ('{ko}')")

    print("=" * 78)
    if basarisiz:
        print("ÖZ-TEST BAŞARISIZ:")
        for b in basarisiz:
            print("  ✖", b)
        return 1
    print(f"ÖZ-TEST TAMAM — {len(senaryolar)} sahte senaryo + {len(gercekler)} gerçek "
          f"rapor, {len(tum)} kriter; çıktılar: {ORNEK}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Piramit koşusunu rubrik CSV'lerine göre kriter-başına notlar")
    ap.add_argument("--rapor", help="piramit.py --out çıktısı (JSON)")
    ap.add_argument("--rubrik", action="append", default=[],
                    help="rubrik CSV yolu (birden çok kez verilebilir)")
    ap.add_argument("--out", help="puan raporunu bu dosyaya JSON yaz")
    ap.add_argument("--json", action="store_true", help="stdout'a JSON bas")
    ap.add_argument("--self-test", action="store_true", help="öz-test koştur")
    a = ap.parse_args(argv)

    if a.self_test:
        return _self_test()
    if not a.rapor:
        ap.error("--rapor gerekli (ya da --self-test)")
    rubrikler = a.rubrik or [str(RUBRIKLER / "kosu_ortak.csv")]
    kriterler = []
    for r in rubrikler:
        kriterler += rubrik_yukle(r)
    rapor = json.loads(Path(a.rapor).expanduser().read_text(encoding="utf-8"))
    puan = puanla(rapor, kriterler)
    if a.out:
        Path(a.out).expanduser().write_text(
            json.dumps(puan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(puan, ensure_ascii=False, indent=2) if a.json else metin(puan))
    # Çıkış kodu: düşen ya da puanlanamayan kriter varsa 2 (fail-closed)
    t = puan["toplam"]
    return 0 if (t[DUSTU] == 0 and t[PUANSIZ] == 0) else 2


if __name__ == "__main__":
    sys.exit(main())
