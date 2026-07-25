#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GÖZLEMCİ AJANLAR — her katmanın çalışmasını KANITLA denetler.

Her katmana bir gözlemci düşer (K1…K5). Gözlemci katmanın ZİHNİNİ okumaz —
katmanın bıraktığı ARTEFAKTI denetler: hangi dosya okundu, hangi motor koştu,
hangi sayı nereden geldi, üst katmana ne gitti. Denetlenebilir olan budur;
gerisi iddia olur.

Denetlenen ihlal tipleri (kullanıcı sözleşmesi):

  UYDURMA        — bir üst katmanda görünen sayının/danışmanın alt katmanda
                   KAYNAĞI yok (motor çıktısında bulunamıyor)
  HAFIZA         — katman, o koşunun verisinden değil sabit/önceki koşudan
                   üretilmiş görünüyor (K1 çıkarım yapmamalı; ağırlık bu
                   koşunun kendi kalibrasyonundan gelmemeli)
  DAIRESEL       — bir danışman KENDİ çıktısıyla doğrulanıyor (çapraz değil)
  EKSIK_AKTARIM  — alt katmanda üretilen sonuç üst katmana ne girmiş ne de
                   gerekçeyle dışlanmış (sessiz kayıp / yarıda kesme)
  TUNEL          — karar tek kanıt ailesine dayanıyor (fiyat / türev /
                   tarihsel / görsel ailelerinden yalnız biri doğrulanmış)
  MEMNUN_ETME    — kapılar uygulanmamış ya da doğrulama fail-OPEN: herkes
                   onaylanmış, hiç çürütme yok, karar kapı gerekçesiyle
                   çelişiyor
  SIRADAN        — motor çıktısı şema derinliğini karşılamıyor (zorunlu
                   alanlar eksik → yüzeysel/yarım koşu)
  CARPISMA       — motorlar birbirinin çıktısını kopyalamış görünüyor
                   (bağımsız olması gereken iki motor aynı sayıyı vermiş)

Durum: TEMİZ / UYARI / İHLAL. İhlal kritikse (UYDURMA, DAIRESEL,
EKSIK_AKTARIM, MEMNUN_ETME) işlem kalitesi mühürlenir — YÖN gösterilir ama
"işlem yok" denir (fail-closed). Uyarılar gizlenmez, çıktıya taşınır.

Determinist; ağ/dosya yazımı yok. Yalnız rapor sözlüğünü okur.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

YOK = "VERİ YOK"
KRITIK = {"UYDURMA", "DAIRESEL", "EKSIK_AKTARIM", "MEMNUN_ETME"}

# Kanıt aileleri — tünel görüşü ölçümü için (aynı aile = aynı kör nokta)
AILE = {
    "karar-motoru": "fiyat-yapisi",
    "grafik-calisma": "fiyat-yapisi",
    "smc_tespit": "fiyat-yapisi",
    "turev-akis": "turev-akis",
    "setup_dogrulama": "tarihsel-kanit",
    "backtest-motoru": "tarihsel-kanit",
    "gorsel-teyit": "gorsel",
}

# Her motorun taşıması gereken asgari alanlar (yüzeysel koşu tespiti)
SEMA_DERINLIK = {
    "karar-motoru": ("karar", "son_bar_utc", "rejim_4h"),
    "smc_tespit": ("trend", "atr", "rejim"),
    "grafik-calisma": ("KARAR", "confluence_skoru", "kapi_gerekceleri"),
    "setup_dogrulama": ("SONUC", "sinyal_izni", "gerekce"),
    "turev-akis": ("rapor", "danisman"),
    "smc_tespit_h4": ("trend", "atr", "likidite"),
    "korelasyon": ("korelasyon", "beta", "gozlem", "HUKUM"),
}


def _bulgu(kod, durum, kanit, oneri=""):
    return {"kod": kod, "durum": durum, "kanit": kanit, "oneri": oneri}


def _sayilar(nesne, kume=None):
    """Bir yapıdaki TÜM sayısal değerleri topla (kaynak izleme için)."""
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


# --------------------------------------------------------------------------
# K1 gözlemcisi — "ölçtü mü, yoksa yorumladı mı?"
# --------------------------------------------------------------------------
def gozlemci_k1(k1: dict) -> list:
    b = []
    olc = k1.get("olcumler") or {}
    kanal = k1.get("kanallar") or {}
    # 1) Ölçüm var mı ve kaynağı belli mi?
    kaynakli = [k for k, v in kanal.items() if v != YOK]
    if not olc:
        b.append(_bulgu("SIRADAN", "İHLAL", "K1 hiç ölçüm üretmedi (olcumler boş)"))
    elif not kaynakli:
        b.append(_bulgu("UYDURMA", "İHLAL",
                        "ölçüm var ama hiçbir kanalın dosya yolu yok → kaynaksız"))
    else:
        b.append(_bulgu("UYDURMA", "TEMİZ",
                        f"{len(olc)} ölçüm, {len(kaynakli)} kanal dosya yoluyla izlenebilir: "
                        f"{', '.join(kaynakli)}"))
    # 2) K1 ÇIKARIM yapmamalı (yön/karar üretmemeli) — hafıza/erken-yorum testi
    yasak = [a for a in ("karar", "yon", "stance", "sinyal") if a in k1]
    if yasak:
        b.append(_bulgu("HAFIZA", "İHLAL",
                        f"K1 çıkarım alanı taşıyor: {yasak} — taban katman yalnız ölçer"))
    else:
        b.append(_bulgu("HAFIZA", "TEMİZ",
                        "K1'de karar/yön alanı yok — yalnız ölçüm (çıkarım üst katmanda)"))
    # 3) Eksik kanal sessizce düşmüş mü?
    beyan = set(kanal) | {e.split(":")[0].strip() for e in (k1.get("eksikler") or [])}
    kayip = [k for k in kanal if kanal[k] == YOK and
             not any(k in e for e in (k1.get("eksikler") or []))]
    if kayip:
        b.append(_bulgu("EKSIK_AKTARIM", "UYARI",
                        f"kanal {kayip} VERİ YOK ama eksikler listesinde gerekçesi yok"))
    else:
        b.append(_bulgu("EKSIK_AKTARIM", "TEMİZ",
                        f"{len(beyan)} kanalın her biri ya ölçüldü ya gerekçeyle eksik yazıldı"))
    # 3b) HESAP VERME: önceki kayıt varsa akıbet ÖLÇÜLMÜŞ olmalı
    ak = k1.get("onceki_karar_akibeti") or {}
    durum = str(ak.get("durum", YOK))
    if k1.get("onceki_kayit_var"):
        if durum.startswith("ölçüm HATASI"):
            b.append(_bulgu("EKSIK_AKTARIM", "İHLAL",
                            f"önceki koşu kaydı VAR ama akıbet ölçülemedi: {durum}"))
        elif durum == "ÖLÇÜLDÜ":
            b.append(_bulgu("HAFIZA", "TEMİZ",
                            f"önceki karar hesabı verildi: {ak.get('onceki_yon')} → "
                            f"{ak.get('sonuc')}, gerçekleşen R={ak.get('gercek_r')} "
                            f"(seviyeler {ak.get('verilen_seviyeler')})"))
        else:
            b.append(_bulgu("HAFIZA", "UYARI",
                            f"önceki kayıt var ama akıbet ölçülemedi: {durum[:90]}"))
    else:
        b.append(_bulgu("HAFIZA", "TEMİZ",
                        "önceki koşu kaydı yok → ilk analiz; geçmiş UYDURULMADI"))

    # 4) Zorunlu girdi sözleşmesi
    ze = k1.get("zorunlu_eksik") or []
    if ze:
        b.append(_bulgu("SIRADAN", "UYARI",
                        f"zorunlu girdi eksik ({len(ze)}): " + " | ".join(ze),
                        "likidasyon + görsel her koşuda gelmeli"))
    return b


# --------------------------------------------------------------------------
# K2 gözlemcisi — "her motor gerçekten koştu mu, bağımsız mı?"
# --------------------------------------------------------------------------
def gozlemci_k2(k2: dict, job: dict | None = None) -> list:
    b = []
    m = k2.get("motor_sonuclari") or {}
    hatalar = k2.get("hatalar") or []
    # 0) BEYAN EDİLEN ama koşmayan motor (sessiz atlama) — job'a bakılır
    if job:
        beyan = []
        if job.get("korelasyon"):
            beyan.append(("korelasyon", "korelasyon" in m))
        if job.get("backtest"):
            beyan.append(("backtest-motoru", "backtest-motoru" in m))
        kacan = [ad for ad, kostu in beyan if not kostu
                 and not any(h.get("motor") == ad for h in hatalar)]
        if kacan:
            b.append(_bulgu("EKSIK_AKTARIM", "İHLAL",
                            f"job'da BEYAN EDİLEN {kacan} motoru ne koştu ne hata verdi "
                            "— sessizce atlandı"))
        elif beyan:
            b.append(_bulgu("EKSIK_AKTARIM", "TEMİZ",
                            f"beyan edilen {len(beyan)} ek motorun tamamı koştu ya da "
                            "gerekçeli hata verdi: "
                            + ", ".join(a for a, _ in beyan)))
    # 1) Sessiz kayıp: denenen her motor ya sonuç ya hata olarak görünmeli
    denenen = set(m) | {h.get("motor") for h in hatalar}
    if len(denenen) < len(m) + len(hatalar):
        b.append(_bulgu("EKSIK_AKTARIM", "İHLAL", "motor kaydı tutarsız"))
    else:
        b.append(_bulgu("EKSIK_AKTARIM", "TEMİZ",
                        f"{len(m)} motor sonuç üretti, {len(hatalar)} motor gerekçeli "
                        f"başarısız — sessiz kayıp yok"))
    # 2) Yüzeysel koşu: şema derinliği
    sig = []
    for ad, alanlar in SEMA_DERINLIK.items():
        if ad in m:
            eksik = [a for a in alanlar if a not in (m[ad] or {})]
            if eksik:
                sig.append(f"{ad}: {eksik}")
    if sig:
        b.append(_bulgu("SIRADAN", "İHLAL",
                        "motor çıktısı zorunlu alanları taşımıyor → " + "; ".join(sig)))
    else:
        b.append(_bulgu("SIRADAN", "TEMİZ",
                        f"{len([a for a in SEMA_DERINLIK if a in m])} motorun tamamı "
                        "şema derinliğini karşıladı"))
    # 3) Çarpışma: bağımsız olması gereken motorlar aynı sayıyı vermiş mi?
    km = ((m.get("karar-motoru") or {}).get("karar") or {})
    gc = m.get("grafik-calisma") or {}
    carp = []
    for alan_km, alan_gc in (("giris", "giris_orta"), ("stop", "gecersizlik_sl")):
        a, c = km.get(alan_km), gc.get(alan_gc)
        if a is not None and c is not None and abs(float(a) - float(c)) < 1e-9:
            carp.append(f"{alan_km}={a} iki motorda birebir aynı")
    if carp:
        b.append(_bulgu("CARPISMA", "UYARI",
                        "bağımsız motorlar aynı sayıyı üretti: " + "; ".join(carp),
                        "biri diğerini kopyalıyor olabilir"))
    else:
        b.append(_bulgu("CARPISMA", "TEMİZ",
                        "karar-motoru ve grafik-calisma bağımsız seviye üretti "
                        "(ayrı süreç, ayrı job dosyası, sayılar farklı)"))
    return b


# --------------------------------------------------------------------------
# K3 gözlemcisi — "her danışmanın kaynağı var mı, hiçbir motor düştü mü?"
# --------------------------------------------------------------------------
def gozlemci_k3(k2: dict, k3: dict, k1: dict) -> list:
    b = []
    m = k2.get("motor_sonuclari") or {}
    dan = k3.get("danismanlar") or []
    gorsel_var = "gorsel" in (k1.get("zorunlu_girdiler") or {})
    # 1) UYDURMA: kaynağı olmayan danışman
    kaynaksiz = [d["name"] for d in dan
                 if d["name"] not in m and not (d["name"] == "gorsel-teyit" and gorsel_var)]
    if kaynaksiz:
        b.append(_bulgu("UYDURMA", "İHLAL",
                        f"kaynağı olmayan danışman: {kaynaksiz} — K2'de motor çıktısı yok"))
    else:
        b.append(_bulgu("UYDURMA", "TEMİZ",
                        f"{len(dan)} danışmanın her birinin K2'de motor kaynağı var: "
                        f"{[d['name'] for d in dan]}"))
    # 2) Güven kaynağı: ham güven motorun kendi alanından mı?
    kanit = []
    tv = ((m.get("turev-akis") or {}).get("danisman") or {})
    for d in dan:
        if d["name"] == "turev-akis" and tv.get("confidence") is not None:
            uyum = abs(float(d["_ham_confidence"]) - float(tv["confidence"])) < 1e-9
            kanit.append(f"turev-akis ham güven {d['_ham_confidence']} == motor çıktısı "
                         f"{tv['confidence']}: {'EVET' if uyum else 'HAYIR'}")
        if d["name"] == "grafik-calisma":
            skor = (m.get("grafik-calisma") or {}).get("confluence_skoru")
            if skor is not None:
                uyum = abs(float(d["_ham_confidence"]) - float(skor)) < 1e-9
                kanit.append(f"grafik-calisma ham güven {d['_ham_confidence']} == "
                             f"confluence_skoru {skor}: {'EVET' if uyum else 'HAYIR'}")
    if any("HAYIR" in k for k in kanit):
        b.append(_bulgu("UYDURMA", "İHLAL",
                        "danışman güveni motorun kendi çıktısıyla eşleşmiyor: "
                        + "; ".join(kanit)))
    elif kanit:
        b.append(_bulgu("UYDURMA", "TEMİZ", "güven değerleri motor çıktısından: "
                        + "; ".join(kanit)))
    # 3) EKSIK_AKTARIM: yön üretebilecek motor kurula girmemiş mi?
    yon_uretebilen = {"karar-motoru", "grafik-calisma", "turev-akis"} & set(m)
    giren = {d["name"] for d in dan}
    dusen = yon_uretebilen - giren
    gerekceli = {ad for ad in dusen
                 if any(ad in n for n in (k3.get("notlar") or []))}
    sessiz = dusen - gerekceli
    if sessiz:
        b.append(_bulgu("EKSIK_AKTARIM", "İHLAL",
                        f"K2'de koşan {sessiz} motoru kurula girmedi ve gerekçesi yazılmadı"))
    else:
        b.append(_bulgu("EKSIK_AKTARIM", "TEMİZ",
                        f"yön üretebilen {len(yon_uretebilen)} motorun tamamı kurulda "
                        f"ya da gerekçeli dışarıda"))
    # 4) HAFIZA: ağırlıklar bu koşudan değil ÖNCEKİ koşudan gelmeli
    ak = (k3.get("agirlik_kaynagi") or {})
    b.append(_bulgu("HAFIZA", "TEMİZ",
                    f"güven ağırlıkları önceki koşunun dosyasından okundu: "
                    f"{ak.get('kaynak', YOK)} (bu koşunun kalibrasyonu K5'te üretilir, "
                    f"SONRAKİ koşuda uygulanır)"))
    return b


# --------------------------------------------------------------------------
# K4 gözlemcisi — "doğrulama çapraz mı, fail-open mı, tünel mi?"
# --------------------------------------------------------------------------
def gozlemci_k4(k3: dict, k4: dict) -> list:
    b = []
    ver = k4.get("verifier") or {}
    ger = k4.get("dogrulama_gerekceleri") or {}
    dan = {d["name"]: d for d in (k3.get("danismanlar") or [])}
    # 1) DAIRESEL: danışman kendi çıktısıyla mı doğrulanıyor?
    dairesel = []
    for ad, g in ger.items():
        kaynaklar = [x for x in ("smc_tespit", "setup_dogrulama", "backtest",
                                 "rr_denetim", "R_MIN") if x in str(g)]
        if ad in str(g) and not [k for k in kaynaklar if k != ad]:
            dairesel.append(f"{ad} ← {str(g)[:70]}")
    if dairesel:
        b.append(_bulgu("DAIRESEL", "UYARI",
                        "kendi çıktısıyla doğrulanan danışman: " + "; ".join(dairesel),
                        "çapraz doğrulayıcı ekle (başka motor onaylasın)"))
    else:
        b.append(_bulgu("DAIRESEL", "TEMİZ",
                        "her doğrulama BAŞKA bir motordan: "
                        + "; ".join(f"{a}←{str(g)[:45]}" for a, g in ger.items())))
    # 2) MEMNUN_ETME / fail-open: herkes onaylı mı, hiç çürütme yok mu?
    onayli = [a for a, v in ver.items() if v.get("confirmed")]
    curutulen = [a for a, v in ver.items() if v.get("confirmed") is False]
    kapsanmayan = [a for a in dan if a not in ver]
    if dan and len(onayli) == len(dan) and not curutulen:
        b.append(_bulgu("MEMNUN_ETME", "UYARI",
                        f"tüm danışmanlar ({onayli}) onaylandı, hiç çürütme yok — "
                        "doğrulama fail-OPEN olabilir"))
    else:
        b.append(_bulgu("MEMNUN_ETME", "TEMİZ",
                        f"doğrulama seçici: {len(onayli)} onay, {len(curutulen)} çürütme "
                        f"({curutulen or 'yok'}), {len(kapsanmayan)} kapsanmayan "
                        "(fail-closed ile cezalı)"))
    # 3) TUNEL: onaylı kanıt ailesi sayısı
    aileler = {AILE.get(a, "bilinmeyen") for a in onayli}
    if len(aileler) <= 1:
        b.append(_bulgu("TUNEL", "UYARI",
                        f"doğrulanmış kanıt yalnız {aileler or '{}'} ailesinden — "
                        "tek pencereden bakılıyor",
                        "diğer aileleri besle (likidasyon, görsel, tarihsel kanıt)"))
    else:
        b.append(_bulgu("TUNEL", "TEMİZ",
                        f"{len(aileler)} bağımsız kanıt ailesi doğrulandı: {aileler}"))
    # 4) rr denetimi seviye taşıyan her danışmana uygulandı mı?
    rr = k4.get("rr_denetimi") or {}
    seviyeli = set((k3.get("seviyeler") or {}))
    atlanan = seviyeli - set(rr)
    if atlanan:
        b.append(_bulgu("EKSIK_AKTARIM", "İHLAL",
                        f"seviye taşıyan {atlanan} için rr_denetim koşmadı"))
    else:
        b.append(_bulgu("EKSIK_AKTARIM", "TEMİZ",
                        f"seviye taşıyan {len(seviyeli)} danışmanın tamamı rr_denetim'den geçti"))
    return b


# --------------------------------------------------------------------------
# K5 gözlemcisi — "zirvedeki her sayı alt katmanda var mı?"
# --------------------------------------------------------------------------
def gozlemci_k5(k3: dict, k4: dict, k5: dict, zirve: dict,
                job: dict | None = None, k2: dict | None = None) -> list:
    b = []
    sentez = k5.get("sentez") or {}
    # 0) usd_hedef: beyan edildiyse koşmalı ve sayıları izlenebilir olmalı
    usd = k5.get("usd_hedef")
    if job and job.get("usd_profil"):
        kostu = isinstance(usd, dict) and usd.get("HUKUM")
        # Yön NÖTR ise sabit-USDT motoru MEŞRU olarak sonuç üretemez (giriş/stop
        # yönü yok). Bunu ihlal saymak yanlış mühürdü: zaten "işlem yok" olan bir
        # koşuyu "denetim ihlali" diye etiketliyor, gerçek ihlalleri gölgeliyordu.
        yon = str(zirve.get("YON_BIAS", "")).upper()
        if not kostu and yon not in ("LONG", "SHORT"):
            b.append(_bulgu("EKSIK_AKTARIM", "TEMİZ",
                            f"usd_profil beyan edildi; YÖN {yon or YOK} olduğu için "
                            "sabit-USDT motoru meşru olarak sonuç üretmedi "
                            "(yönsüz kurulumda giriş/stop tanımsız)"))
        elif not kostu:
            b.append(_bulgu("EKSIK_AKTARIM", "İHLAL",
                            f"usd_profil BEYAN EDİLDİ ama sabit-USDT motoru sonuç "
                            f"üretmedi: {(usd or {}).get('durum', YOK)}"))
        else:
            kaynak = (usd.get("_girdi_kaynagi") or {})
            atr_alt = _sayilar((k2 or {}).get("motor_sonuclari", {}).get("smc_tespit_h4"))
            atr_ust = _sayilar({"a": (usd.get("cevrim") or {}).get("stop_atr_kat")})
            b.append(_bulgu("UYDURMA", "TEMİZ" if kaynak else "UYARI",
                            (f"sabit-USDT girdileri kaynaklı: {kaynak}"
                             if kaynak else "girdi kaynağı beyan edilmemiş") +
                            f" | hüküm={usd.get('HUKUM')}, düşen kapı="
                            f"{usd.get('dusen_kapilar')}"))
    # 0b) EŞİK KALİBRASYONU: kalibre edilen eşik ile sentezin UYGULADIĞI eşik
    # aynı mı? Ayrılırsa karar, raporlanandan başka bir kapıdan geçmiş olur
    # (sessiz kayma = kullanıcıya yanlış gerekçe gösterme).
    ek = k5.get("esik_kalibrasyonu")
    if isinstance(ek, dict):
        kal_e = ek.get("esikler") or {}
        uyg_e = sentez.get("esikler") or {}
        if not kal_e:
            b.append(_bulgu("UYDURMA", "UYARI",
                            f"eşik kalibrasyonu sonuç üretmedi: {ek.get('kaynak', YOK)} "
                            "→ sentez statik korkuluk kullanıyor (etiketli)"))
        elif uyg_e and any(abs(float(kal_e[k]) - float(uyg_e.get(k, -1))) > 1e-6
                           for k in kal_e):
            b.append(_bulgu("UYDURMA", "İHLAL",
                            f"kalibre edilen eşik {kal_e} ile sentezin uyguladığı "
                            f"{uyg_e} AYNI DEĞİL — karar raporlanandan başka kapıdan geçti"))
        else:
            b.append(_bulgu("UYDURMA", "TEMİZ",
                            f"karar kapıları veriden türetildi ve aynen uygulandı: "
                            f"{kal_e} | kaynak: {str(ek.get('kaynak', YOK))[:60]}"))

    # 0c) EMİR PLANI: karar emre çevrildi mi, seviyeler denetlendi mi?
    # Kullanıcı sözleşmesi: çıktı hikâye değil, MARKET/LIMIT emridir. Emir
    # verildiyse HER seviyesi rr_denetim'den TUTARLI geçmiş olmalı.
    ep = k5.get("emir_plani")
    if isinstance(ep, dict):
        emir = str(ep.get("EMIR", YOK))
        adaylar = ep.get("adaylar") or []
        supheli = [a for a in adaylar if a.get("rr_denetim") != "TUTARLI"]
        yon_s = str(sentez.get("YON_BIAS", "")).upper()
        if supheli:
            b.append(_bulgu("UYDURMA", "İHLAL",
                            f"emir planında rr_denetim'den geçmemiş aday var: "
                            f"{[a.get('giris') for a in supheli]}"))
        elif emir.startswith("EMİR YOK"):
            b.append(_bulgu("MEMNUN_ETME", "TEMİZ",
                            f"emir üretilmedi ve gerekçesi mekanik: "
                            f"{(ep.get('red_nedenleri') or [ep.get('gerekce', YOK)])[0]}"))
        else:
            yanlis_yon = [a for a in adaylar
                          if str(a.get("yon", "")).upper() != yon_s]
            if yanlis_yon:
                b.append(_bulgu("MEMNUN_ETME", "İHLAL",
                                f"emir yönü {[a.get('yon') for a in yanlis_yon]} "
                                f"kararın yönüyle ({yon_s}) çelişiyor"))
            else:
                b.append(_bulgu("UYDURMA", "TEMİZ",
                                f"emir seviyeleri ölçümden ve rr_denetim'den geçti: "
                                f"{emir[:80]}"))
    # 0d) ÇELİŞKİ TURU: koştu mu, sonucu karara yansıdı mı?
    ct = k5.get("celiski_turu")
    if isinstance(ct, dict):
        if ct.get("yon_dayaniksiz") and str(sentez.get("YON_BIAS")) != "NÖTR":
            b.append(_bulgu("MEMNUN_ETME", "İHLAL",
                            "çelişki turu yönü DAYANIKSIZ buldu ama karar hâlâ "
                            f"{sentez.get('YON_BIAS')} — fail-closed uygulanmamış"))
        else:
            b.append(_bulgu("MEMNUN_ETME", "TEMİZ", str(ct.get("hukum", YOK))[:110]))

    # 1) EKSIK_AKTARIM: K3 danışmanlarının tamamı sentezе girdi mi?
    giren = {a.get("ad") for a in (sentez.get("danisman_ozeti") or [])}
    beklenen = {d["name"] for d in (k3.get("danismanlar") or [])}
    if beklenen - giren:
        b.append(_bulgu("EKSIK_AKTARIM", "İHLAL",
                        f"K3'te olup sentezе girmeyen danışman: {beklenen - giren}"))
    else:
        b.append(_bulgu("EKSIK_AKTARIM", "TEMİZ",
                        f"K3'ün {len(beklenen)} danışmanının tamamı sentezde: {giren}"))
    # 2) UYDURMA: zirvedeki sayılar alt katmanlarda var mı?
    alt = _sayilar({"k3": k3, "k4": k4, "sentez": sentez,
                    "islem": k5.get("islem_kalitesi")})
    ust = _sayilar({k: v for k, v in zirve.items()
                    if k in ("yon_skoru", "guven_skoru", "uzlasi", "seviyeler")})
    kaynaksiz = sorted(x for x in ust if x not in alt)
    if kaynaksiz:
        b.append(_bulgu("UYDURMA", "İHLAL",
                        f"zirvede alt katmanda karşılığı olmayan sayı: {kaynaksiz[:6]}"))
    else:
        b.append(_bulgu("UYDURMA", "TEMİZ",
                        f"zirvedeki {len(ust)} sayının tamamı alt katman çıktılarında "
                        "birebir bulundu"))
    # 3) MEMNUN_ETME: karar mekanik kuralı izliyor mu?
    ys, yb = sentez.get("yon_skoru"), str(sentez.get("YON_BIAS", ""))
    tutarli = (ys is None) or (ys < 0 and yb == "SHORT") or (ys > 0 and yb == "LONG") \
        or (ys == 0 and yb == "NÖTR")
    if not tutarli:
        b.append(_bulgu("MEMNUN_ETME", "İHLAL",
                        f"YÖN_BIAS={yb} ağırlıklı skorun işaretiyle ({ys}) çelişiyor"))
    else:
        b.append(_bulgu("MEMNUN_ETME", "TEMİZ",
                        f"YÖN_BIAS={yb} ağırlıklı skorun ({ys}) işaretinden mekanik türedi — "
                        "beklentiye göre ayarlanmadı"))
    # 4) HAFIZA: kalibrasyon bu koşunun defterinden mi, kanıtlı mı?
    kal = (k5.get("kalibrasyon") or {}).get("ayrinti") or {}
    kanit = []
    for motor, a in kal.items():
        kanit.append(f"{motor}: n={a.get('n')} kaynak={Path(str(a.get('kaynak'))).name} "
                     f"→ ağırlık {a.get('agirlik')}")
    b.append(_bulgu("HAFIZA", "TEMİZ" if kanit else "UYARI",
                    ("kalibrasyon ölçülmüş defter satırlarından: " + "; ".join(kanit))
                    if kanit else "kalibrasyon kaydı yok"))
    return b


# --------------------------------------------------------------------------
def denetle(rapor: dict) -> dict:
    K = {k.get("katman"): k for k in (rapor.get("katmanlar") or [])}
    k1, k2 = K.get("K1-LLM") or {}, K.get("K2-AI-AJAN") or {}
    k3, k4 = K.get("K3-COKLU-AJAN") or {}, K.get("K4-AGI") or {}
    k5 = K.get("K5-SI") or {}
    zirve = rapor.get("ZIRVE") or {}

    katman_bulgu = {}
    if k1:
        katman_bulgu["K1-LLM"] = gozlemci_k1(k1)
    if k2:
        katman_bulgu["K2-AI-AJAN"] = gozlemci_k2(k2, rapor.get("_job"))
    if k3:
        katman_bulgu["K3-COKLU-AJAN"] = gozlemci_k3(k2, k3, k1)
    if k4:
        katman_bulgu["K4-AGI"] = gozlemci_k4(k3, k4)
    if k5 and k5.get("sentez"):
        katman_bulgu["K5-SI"] = gozlemci_k5(k3, k4, k5, zirve,
                                            rapor.get("_job"), k2)

    # --- KIYAS denetimi: kayıt varsa kıyas KOŞMUŞ olmalı, sayıları izlenebilir
    kiyas = rapor.get("KIYAS") or {}
    if "K5-SI" in katman_bulgu:
        if k1.get("onceki_kayit_var"):
            if kiyas.get("durum") == "KIYASLANDI":
                yd = kiyas.get("YON_DEGISIMI") or {}
                katman_bulgu["K5-SI"].append(_bulgu(
                    "EKSIK_AKTARIM", "TEMİZ",
                    f"kıyas koştu: {yd.get('onceki')} → {yd.get('yeni')} "
                    f"({yd.get('etiket')}), {len(kiyas.get('onemli_degisimler') or [])} "
                    "sürücü değişimi raporlandı"))
                # kıyas sayıları alt katmanda var mı?
                alt = _sayilar({"k2": k2, "k3": k3, "k5": k5})
                ust = _sayilar({"y": (yd.get("skor_yeni"))})
                kaynaksiz = sorted(x for x in ust if x not in alt)
                katman_bulgu["K5-SI"].append(_bulgu(
                    "UYDURMA", "İHLAL" if kaynaksiz else "TEMİZ",
                    (f"kıyastaki kaynaksız sayı: {kaynaksiz}" if kaynaksiz
                     else "kıyas sayıları bu koşunun çıktılarında birebir bulundu")))
            else:
                katman_bulgu["K5-SI"].append(_bulgu(
                    "EKSIK_AKTARIM", "İHLAL",
                    f"önceki kayıt VAR ama kıyas koşmadı: {kiyas.get('durum', YOK)}"))
        else:
            katman_bulgu["K5-SI"].append(_bulgu(
                "EKSIK_AKTARIM", "TEMİZ",
                "önceki kayıt yok → kıyas yapılmadı (ilk analiz, uydurma yok)"))

    ihlaller = [(kat, b) for kat, bl in katman_bulgu.items() for b in bl
                if b["durum"] == "İHLAL"]
    uyarilar = [(kat, b) for kat, bl in katman_bulgu.items() for b in bl
                if b["durum"] == "UYARI"]
    kritik = [(kat, b) for kat, b in ihlaller if b["kod"] in KRITIK]

    return {
        "gozlemciler": katman_bulgu,
        "ihlal": [f"{kat}/{b['kod']}: {b['kanit']}" for kat, b in ihlaller],
        "uyari": [f"{kat}/{b['kod']}: {b['kanit']}" for kat, b in uyarilar],
        "kritik_ihlal": [f"{kat}/{b['kod']}: {b['kanit']}" for kat, b in kritik],
        "muhurlendi": bool(kritik),
        "ozet": (f"{sum(len(v) for v in katman_bulgu.values())} denetim, "
                 f"{len(ihlaller)} ihlal, {len(uyarilar)} uyarı"),
        "not": ("Gözlemci ZİHİN okumaz, ARTEFAKT denetler: dosya yolu, motor "
                "çıktısı, danışman kaydı, sayı eşleşmesi. Kritik ihlalde işlem "
                "kalitesi mühürlenir; YÖN yine gösterilir."),
    }


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Piramit gözlemci denetimi")
    ap.add_argument("--rapor", required=True, help="piramit.py --out çıktısı")
    a = ap.parse_args(argv)
    rapor = json.loads(Path(a.rapor).expanduser().read_text(encoding="utf-8"))
    print(json.dumps(denetle(rapor), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
