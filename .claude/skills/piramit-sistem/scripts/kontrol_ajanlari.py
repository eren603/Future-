#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONTROL AJANLARI — çalışan ajanları denetleyen ikinci kat.

`gozlemci.py` PİRAMİT katmanlarını denetler (piyasa boru hattına bağlı).
Bu modül ONDAN GENİŞTİR: KONUDAN BAĞIMSIZ bir ZİNCİR defterini denetler
(Z1 GÖREV → Z2 KANIT → Z3 ÜRETİM → Z4 ÇAPRAZ DOĞRULAMA → Z5 SENTEZ →
Z6 TESLİM) ve piramit raporuna da uygulanabilir. Yani "her konu" için
çalışır: kod taraması, araştırma, yazı, piyasa analizi — hepsi aynı zincir.

Kullanıcı sözleşmesi — kontrol ajanı çalışan ajana ŞU soruları sorar ve her
birini ARTEFAKTLA yanıtlar (zihin okumaz, iddiaya inanmaz):

  ARASTIRMASIZ  — araştırmadan mı üretti? (iddia var, okunmuş kaynak yok)
  HAFIZA        — hafızadan mı üretti? (kaynak "model bilgisi"/önceki koşu)
  UYDURMA       — uydurdu mu? (sayı hiçbir okunan artefaktta geçmiyor;
                  "okudum" denen dosya diskte YOK)
  TAKLIT        — başka ajanı taklit mi etti? (bağımsız iki ajanın sayı
                  kümesi neredeyse birebir aynı)
  BULASMA       — birbirinden etkilendi mi? (bağımsız olması gereken ajan
                  başka bir bağımsız ajanın çıktısını GÖRMÜŞ)
  DAIRESEL      — dairesel mi düşündü? (iddiayı üreten ajan kendini
                  doğrulamış)
  MEMNUN_ETME   — kullanıcıyı memnun etmek için mi? (hiç çürütme yok =
                  fail-OPEN; ya da kullanıcı itirazından sonra YENİ KANIT
                  olmadan fikir değişmiş)
  GOREV_SAPMASI — tam görevi anlayıp yaptı mı? (görev maddesi hiçbir adımda
                  kapsanmamış = sessizce daraltılmış)
  TUNEL         — tünel görüşüne girdi mi? (doğrulanmış kanıt tek ailede)
  GIZLI_GUNDEM  — gizli düşünceye mi girdi? (teslimde hiçbir adımın
                  üretmediği sayı/sürücü var = beyan dışı gerekçe)
  TIYATRO       — gerçekten yaptı mı, gösterip tiyatro mu? (adım "geçti"
                  diyor ama artefakt/iddia üretmemiş, ya da bir öncekinin
                  çıktısını aynen tekrarlamış = sıfır katkı)
  EKSIK_AKTARIM — üretilip üst adıma ne giren ne gerekçeyle dışlanan sonuç
  SIRADAN       — adım şema derinliğini karşılamıyor (yarım koşu)

Kritik (P0) bulguda TESLİM MÜHÜRLENİR: sonuç yine gösterilir ama "bu haliyle
kullanılamaz" denir (fail-closed). Bulgular SEVERITY'ye göre sıralanır ve her
biri için mekanik bir DÜZELTME adımı yazılır.

Determinist: rastgelelik yok, ağ yok, duvar-saati yok. Yalnız defteri ve
defterin işaret ettiği dosyaları okur.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

YOK = "VERİ YOK"

# --- severity: P0 mühürler, P1 düzeltme ister, P2 not düşer ----------------
SEVERITY = {
    "UYDURMA": "P0", "DAIRESEL": "P0", "MEMNUN_ETME": "P0",
    "GOREV_SAPMASI": "P0", "TIYATRO": "P0", "BULASMA": "P0",
    "EKSIK_AKTARIM": "P0",
    "ARASTIRMASIZ": "P1", "HAFIZA": "P1", "TAKLIT": "P1",
    "GIZLI_GUNDEM": "P1",
    "TUNEL": "P2", "SIRADAN": "P2", "CARPISMA": "P2",
}
MUHURLEYEN = {k for k, v in SEVERITY.items() if v == "P0"}

# --- her koda mekanik düzeltme reçetesi -----------------------------------
DUZELTME = {
    "ARASTIRMASIZ": "Adımı, iddiadan ÖNCE en az bir kaynak okuyacak şekilde tekrar koştur; okunan dosya/araç çıktısını artefakt olarak defterе yaz.",
    "HAFIZA": "Kaynağı 'model bilgisi/önceki koşu' olan iddiayı bu koşunun verisinden yeniden üret; üretilemiyorsa iddiayı VERİ YOK'a çevir.",
    "UYDURMA": "Kaynaksız sayıyı ya artefakttan düzelt ya metinden çıkar; 'okundu' denen dosya yoksa adımı gerçekten koştur.",
    "TAKLIT": "İki ajanı farklı kanıt ailesiyle ve farklı girdiyle yeniden koştur; aynı sayıyı üretiyorlarsa biri bağımsız değildir — kuruldan düşür.",
    "BULASMA": "Bağımsız ajanı, diğerinin çıktısını GÖRMEDEN yeniden koştur (izole girdi); görmüşse bulgusunu bağımsız sayma.",
    "DAIRESEL": "Doğrulamayı BAŞKA bir ajana/aileye devret; kendi çıktısıyla doğrulanan iddiayı doğrulanmamış say.",
    "MEMNUN_ETME": "Her iddia için en az bir ÇÜRÜTME denemesi koştur; kullanıcı itirazından sonra kanıt gelmediyse eski konumu gerekçesiyle koru.",
    "GOREV_SAPMASI": "Kapsanmayan görev maddesini kendi adımıyla koştur ya da 'yapılmadı + neden' diye AÇIKÇA yaz — sessiz daraltma yok.",
    "TUNEL": "İkinci bir kanıt ailesi besle (farklı kaynak türü); tek aileyle çıkan sonucu 'tek pencere' etiketiyle sun.",
    "GIZLI_GUNDEM": "Teslimdeki her sürücüyü/sayıyı üreten adıma bağla; bağlanamayan gerekçeyi metinden çıkar.",
    "TIYATRO": "Sıfır katkılı adımı ya gerçek çıktı üretecek şekilde koştur ya zincirden çıkar — 'koştu' etiketi artefaktsız verilemez.",
    "EKSIK_AKTARIM": "Üretilip taşınmayan sonucu üst adıma ver ya da 'şu gerekçeyle dışlandı' diye yaz.",
    "SIRADAN": "Adımın zorunlu alanlarını doldur (girdi/artefakt/iddia/kapı); yarım koşu tamamlanmış sayılmaz.",
    "CARPISMA": "Bağımsız iki motorun birebir aynı sayısını ayrı girdilerle doğrula; biri kopyalıyorsa kaynağı ayır.",
}

ZORUNLU_ALAN = ("id", "ad", "gecti")
HAFIZA_KAYNAK = ("hafiza", "hafıza", "model bilgisi", "model_bilgisi",
                 "onceki_kosu", "önceki koşu", "ezber", "memory")
SAYI_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
MAX_ARTEFAKT_BAYT = 2_000_000


def _bulgu(kod, adim, kanit, ajan=None, severity=None):
    return {"kod": kod, "severity": severity or SEVERITY.get(kod, "P2"), "adim": adim,
            "ajan": ajan or YOK, "kanit": kanit, "duzeltme": DUZELTME.get(kod, "")}


def _sayi_kumesi(nesne, kume=None):
    """Bir yapıdaki tüm sayıları 6 haneye yuvarlayarak topla."""
    kume = set() if kume is None else kume
    if isinstance(nesne, dict):
        for v in nesne.values():
            _sayi_kumesi(v, kume)
    elif isinstance(nesne, (list, tuple, set)):
        for v in nesne:
            _sayi_kumesi(v, kume)
    elif isinstance(nesne, bool):
        pass
    elif isinstance(nesne, (int, float)):
        kume.add(round(float(nesne), 6))
    elif isinstance(nesne, str):
        for m in SAYI_RE.findall(nesne):
            try:
                kume.add(round(float(m.replace(",", ".")), 6))
            except ValueError:
                pass
    return kume


def _artefakt_sayilari(art: dict) -> tuple[set, str | None]:
    """Bir artefaktın sayı kümesi + varsa 'dosya yok' kanıtı.

    tur='dosya' ise dosya GERÇEKTEN okunur (var mı, içinde sayı var mı).
    Böylece "okudum" iddiası mekanik olarak sınanır — beyanla geçilemez.
    """
    tur = str(art.get("tur", "")).lower()
    ref = str(art.get("ref", "")).strip()
    kume = _sayi_kumesi(art.get("sayilar"))
    if tur == "dosya" and ref:
        p = Path(ref).expanduser()
        if not p.exists():
            return kume, f"artefakt dosyası diskte YOK: {ref}"
        try:
            if p.is_file() and p.stat().st_size <= MAX_ARTEFAKT_BAYT:
                kume |= _sayi_kumesi(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError as e:
            return kume, f"artefakt okunamadı: {ref} ({e})"
    return kume, None


# --------------------------------------------------------------------------
# KA-KAYNAK — "araştırdı mı, hafızadan mı, uydurdu mu?"
# --------------------------------------------------------------------------
def ka_kaynak(defter: dict) -> list:
    b, havuz = [], set()
    for a in defter.get("adimlar") or []:
        aid, ajan = a.get("id", YOK), a.get("ajan")
        iddialar = a.get("iddialar") or []
        arts = a.get("artefaktlar") or []
        okunan = [x for x in arts if x.get("okundu")]
        adim_sayi = set()
        for art in arts:
            k, hata = _artefakt_sayilari(art)
            adim_sayi |= k
            if hata:
                b.append(_bulgu("UYDURMA", aid, hata, ajan))
        havuz |= adim_sayi

        if iddialar and not okunan:
            b.append(_bulgu("ARASTIRMASIZ", aid,
                            f"{len(iddialar)} iddia üretildi ama okunmuş kaynak yok "
                            "(artefakt listesi boş/okundu=false)", ajan))
        for i in iddialar:
            kaynak = str(i.get("kaynak", "")).strip()
            if not kaynak or kaynak == YOK:
                b.append(_bulgu("ARASTIRMASIZ", aid,
                                f"kaynaksız iddia: {str(i.get('metin', ''))[:70]}", ajan))
            elif any(h in kaynak.lower() for h in HAFIZA_KAYNAK):
                b.append(_bulgu("HAFIZA", aid,
                                f"iddia bu koşunun verisinden değil '{kaynak}' kaynağından: "
                                f"{str(i.get('metin', ''))[:60]}", ajan))
            kaynaksiz = sorted(x for x in _sayi_kumesi(i.get("sayilar"))
                               if x not in adim_sayi and x not in havuz)
            if kaynaksiz:
                b.append(_bulgu("UYDURMA", aid,
                                f"iddiadaki sayı hiçbir okunan artefaktta yok: "
                                f"{kaynaksiz[:5]} ← {str(i.get('metin', ''))[:50]}", ajan))
    return b


# --------------------------------------------------------------------------
# KA-BAGIMSIZLIK — "taklit mi, bulaşma mı, dairesel mi?"
# --------------------------------------------------------------------------
def ka_bagimsizlik(defter: dict) -> list:
    b = []
    adimlar = defter.get("adimlar") or []
    bagimsiz = [a for a in adimlar if a.get("bagimsiz")]
    bagimsiz_id = {a.get("id") for a in bagimsiz}

    # 1) BULASMA — bağımsız ajan, KENDİSİNE BESLENMEYEN bir bağımsız ajanın
    # çıktısına bakmış. Doğrulayıcı/çürütücü zaten denetleyeceği çıktıyı okur;
    # o girdi_id ile BEYAN edildiği sürece bulaşma değildir (yanlış-pozitif
    # korkuluğu). Bulaşma = beslenmediğin halde akranın sonucuna bakmak.
    for a in bagimsiz:
        besleme = set(a.get("girdi_id") or [])
        gordugu = (set(a.get("gordugu_adimlar") or [])
                   & (bagimsiz_id - {a.get("id")}) - besleme)
        if gordugu:
            b.append(_bulgu("BULASMA", a.get("id", YOK),
                            f"bağımsız olması gereken adım, kendisine BESLENMEYEN "
                            f"{sorted(gordugu)} çıktısına bakmış — çıpalanmış, "
                            "bulgusu bağımsız değil", a.get("ajan")))

    # 2) TAKLIT — bağımsız iki adımın sayı kümesi neredeyse birebir aynı
    ozet = {}
    for a in bagimsiz:
        s = _sayi_kumesi([i.get("sayilar") for i in (a.get("iddialar") or [])])
        if s:
            ozet[a.get("id")] = (s, a.get("ajan"))
    idler = sorted(ozet)
    for i, x in enumerate(idler):
        for y in idler[i + 1:]:
            sx, sy = ozet[x][0], ozet[y][0]
            ortak = len(sx & sy) / len(sx | sy)
            if ortak >= 0.9:
                b.append(_bulgu("TAKLIT", f"{x}~{y}",
                                f"bağımsız iki ajanın sayı kümesi %{ortak * 100:.0f} "
                                f"örtüşüyor ({sorted(sx & sy)[:5]}) — biri diğerini "
                                "kopyalamış olabilir", f"{ozet[x][1]} / {ozet[y][1]}"))

    # 3) DAIRESEL — iddiayı üreten ajan kendini doğrulamış
    uretici = {}
    for a in adimlar:
        for i in a.get("iddialar") or []:
            uretici[str(i.get("metin", ""))[:80]] = (a.get("ajan"), a.get("id"))
    for d in defter.get("dogrulamalar") or []:
        anahtar = str(d.get("iddia", ""))[:80]
        sahip = uretici.get(anahtar)
        if sahip and d.get("dogrulayan_ajan") == sahip[0]:
            b.append(_bulgu("DAIRESEL", sahip[1],
                            f"'{anahtar[:50]}' iddiasını üreten ajan ({sahip[0]}) "
                            "kendi iddiasını doğruladı", sahip[0]))
    return b


# --------------------------------------------------------------------------
# KA-NIYET — "memnun etme, görev sapması, gizli gündem"
# --------------------------------------------------------------------------
def ka_niyet(defter: dict) -> list:
    b = []
    dog = defter.get("dogrulamalar") or []
    onay = [d for d in dog if str(d.get("sonuc", "")).upper().startswith("ONAY")]
    curut = [d for d in dog if str(d.get("sonuc", "")).upper().startswith("ÇÜR")
             or str(d.get("sonuc", "")).upper().startswith("CUR")]
    if dog and not curut:
        b.append(_bulgu("MEMNUN_ETME", "Z4",
                        f"{len(onay)} doğrulamanın tamamı ONAY, hiç çürütme yok — "
                        "doğrulama fail-OPEN (çürütme denenmemiş olabilir)"))

    # kullanıcı itirazından sonra YENİ KANIT olmadan dönüş
    it = defter.get("kullanici_itirazi")
    if isinstance(it, dict) and it.get("fikir_degisti"):
        if not (it.get("yeni_kanit") or []):
            b.append(_bulgu("MEMNUN_ETME", it.get("adim", "Z5"),
                            "kullanıcı itirazından sonra YENİ KANIT olmadan konum "
                            f"değişti: {str(it.get('eski', ''))[:40]} → "
                            f"{str(it.get('yeni', ''))[:40]}"))

    # GOREV_SAPMASI — her görev maddesi bir adımda kapsanmalı
    maddeler = defter.get("gorev_maddeleri") or []
    kapsanan = set()
    for a in defter.get("adimlar") or []:
        kapsanan |= set(a.get("kapsanan_maddeler") or [])
    dislanan = {str(x.get("id")): x.get("gerekce")
                for x in (defter.get("dislanan_maddeler") or [])}
    for m in maddeler:
        mid = m.get("id") if isinstance(m, dict) else str(m)
        if mid not in kapsanan and not dislanan.get(str(mid)):
            metin = m.get("metin", mid) if isinstance(m, dict) else str(m)
            b.append(_bulgu("GOREV_SAPMASI", "ZİNCİR",
                            f"görev maddesi '{str(metin)[:60]}' hiçbir adımda "
                            "kapsanmadı ve gerekçeyle dışlanmadı — sessiz daraltma"))

    # GIZLI_GUNDEM — teslimdeki sayı/sürücü hiçbir adımda üretilmemiş
    teslim = defter.get("teslim") or {}
    uretilen = set()
    for a in defter.get("adimlar") or []:
        uretilen |= _sayi_kumesi([i.get("sayilar") for i in (a.get("iddialar") or [])])
        for art in a.get("artefaktlar") or []:
            k, _ = _artefakt_sayilari(art)
            uretilen |= k
    kacak = sorted(x for x in _sayi_kumesi(teslim.get("sayilar")) if x not in uretilen)
    if kacak:
        b.append(_bulgu("GIZLI_GUNDEM", "Z6",
                        f"teslimde hiçbir adımın üretmediği sayı var: {kacak[:5]} — "
                        "beyan dışı gerekçe (gizli sürücü)"))
    for s in teslim.get("suruculer") or []:
        if str(s.get("kaynak_adim", "")) not in {a.get("id") for a in
                                                 (defter.get("adimlar") or [])}:
            b.append(_bulgu("GIZLI_GUNDEM", "Z6",
                            f"teslimdeki sürücü '{str(s.get('ad', ''))[:40]}' hiçbir "
                            "adıma bağlı değil"))
    return b


# --------------------------------------------------------------------------
# KA-KAPSAM — "tünel görüşü, eksik aktarım"
# --------------------------------------------------------------------------
def ka_kapsam(defter: dict) -> list:
    b = []
    dog = defter.get("dogrulamalar") or []
    aileler = {str(d.get("aile", "bilinmeyen")) for d in dog
               if str(d.get("sonuc", "")).upper().startswith("ONAY")}
    if dog and len(aileler) <= 1:
        b.append(_bulgu("TUNEL", "Z4",
                        f"doğrulanmış kanıt yalnız {aileler or '{}'} ailesinden — "
                        "tek pencereden bakılıyor"))
    adimlar = defter.get("adimlar") or []
    tuketilen = set()
    for a in adimlar:
        tuketilen |= set(a.get("girdi_id") or [])
    teslim_giris = set((defter.get("teslim") or {}).get("girdi_id") or [])
    dislanan = {str(x.get("id")): x.get("gerekce")
                for x in (defter.get("dislanan_ciktilar") or [])}
    for a in adimlar:
        aid = a.get("id")
        uretti = bool(a.get("iddialar") or a.get("artefaktlar"))
        if uretti and aid not in tuketilen and aid not in teslim_giris \
                and not dislanan.get(str(aid)):
            b.append(_bulgu("EKSIK_AKTARIM", aid,
                            "adım sonuç üretti ama ne bir sonraki adıma girdi ne de "
                            "gerekçeyle dışlandı — sessiz kayıp", a.get("ajan")))
    return b


# --------------------------------------------------------------------------
# KA-GERCEKLIK — "gerçekten yaptı mı, tiyatro mu?"
# --------------------------------------------------------------------------
def ka_gerceklik(defter: dict) -> list:
    b = []
    adimlar = defter.get("adimlar") or []
    onceki_imza = {}
    for a in adimlar:
        aid, ajan = a.get("id", YOK), a.get("ajan")
        eksik = [x for x in ZORUNLU_ALAN if x not in a]
        if eksik:
            b.append(_bulgu("SIRADAN", aid, f"adım zorunlu alanları taşımıyor: {eksik}", ajan))
        arts, iddialar = a.get("artefaktlar") or [], a.get("iddialar") or []
        if a.get("gecti") and not arts and not iddialar:
            b.append(_bulgu("TIYATRO", aid,
                            "adım 'geçti' diyor ama ne artefakt ne iddia üretti — "
                            "sıfır katkı (kutu tiyatrosu)", ajan))
        imza = frozenset(_sayi_kumesi([i.get("sayilar") for i in iddialar])) | \
            frozenset(str(i.get("metin", ""))[:60] for i in iddialar)
        for gid in a.get("girdi_id") or []:
            if imza and onceki_imza.get(gid) == imza:
                b.append(_bulgu("TIYATRO", aid,
                                f"adım çıktısı girdisi {gid} ile BİREBİR aynı — "
                                "yeni bilgi eklemedi", ajan))
        onceki_imza[aid] = imza
        if a.get("gecti") and str(a.get("kapi", "")).strip() in ("", YOK):
            b.append(_bulgu("SIRADAN", aid, "adım geçti ama kapı gerekçesi yazılmadı", ajan))
    return b


# --------------------------------------------------------------------------
# ZİNCİR denetimi (konudan bağımsız)
# --------------------------------------------------------------------------
def denetle_zincir(defter: dict) -> dict:
    bulgular = (ka_kaynak(defter) + ka_bagimsizlik(defter) + ka_niyet(defter)
                + ka_kapsam(defter) + ka_gerceklik(defter))
    return _paketle(bulgular, defter.get("gorev", YOK),
                    len(defter.get("adimlar") or []))


# --------------------------------------------------------------------------
# PİRAMİT raporu denetimi (gozlemci.py'nin ÜSTÜNE yeni kodlar)
# --------------------------------------------------------------------------
def denetle_piramit(rapor: dict) -> dict:
    b = []
    K = {k.get("katman"): k for k in (rapor.get("katmanlar") or [])}
    k1, k2 = K.get("K1-LLM") or {}, K.get("K2-AI-AJAN") or {}
    k3, k4 = K.get("K3-COKLU-AJAN") or {}, K.get("K4-AGI") or {}
    k5 = K.get("K5-SI") or {}
    zirve = rapor.get("ZIRVE") or {}
    job = rapor.get("_job") or {}
    motorlar = k2.get("motor_sonuclari") or {}
    danismanlar = k3.get("danismanlar") or []
    ver = k4.get("verifier") or {}

    # TIYATRO — katman GEÇTİ ama katkısı SIFIR.
    # Katkı yalnız "yeni sayı" değildir: K3 danışman listesi, K4 doğrulama
    # matrisi gibi YAPISAL çıktılar da katkıdır (aksi halde yanlış-pozitif).
    # Tiyatro = ne yeni sayı ne yeni yapısal çıktı, ya da yükün bir alt
    # katmanla BİREBİR aynı olması.
    KAPI_ALAN = {"katman", "gecti", "kapi", "not", "aciklama"}
    birikim, yukler = set(), {}
    for kat in ("K1-LLM", "K2-AI-AJAN", "K3-COKLU-AJAN", "K4-AGI", "K5-SI"):
        k = K.get(kat)
        if not k:
            continue
        yuk = {x: y for x, y in k.items()
               if not str(x).startswith("_") and x not in KAPI_ALAN and y not in
               (None, "", [], {}, YOK)}
        s = _sayi_kumesi(yuk)
        imza = json.dumps(yuk, ensure_ascii=False, sort_keys=True, default=str)
        kopya = [a for a, v in yukler.items() if v == imza]
        if k.get("gecti") and birikim and not (s - birikim) and not yuk:
            b.append(_bulgu("TIYATRO", kat,
                            "katman GEÇTİ ama ne yeni sayı ne yeni yapısal çıktı "
                            "üretti — kutu tiyatrosu"))
        elif k.get("gecti") and kopya:
            b.append(_bulgu("TIYATRO", kat,
                            f"katman yükü {kopya[0]} ile BİREBİR aynı — sıfır katkı"))
        birikim |= s
        yukler[kat] = imza

    # ARASTIRMASIZ — danışman yön veriyor ama besleyen kanal ölçülmemiş
    kanal = k1.get("kanallar") or {}
    kanalsiz = [d.get("name") for d in danismanlar
                if d.get("name") not in motorlar
                and not (k1.get("zorunlu_girdiler") or {}).get("gorsel")]
    if kanalsiz:
        b.append(_bulgu("ARASTIRMASIZ", "K3-COKLU-AJAN",
                        f"K2'de motor çıktısı olmayan danışman yön verdi: {kanalsiz}"))

    # TAKLIT — iki danışman aynı duruş + birebir aynı ham güven
    for i, d1 in enumerate(danismanlar):
        for d2 in danismanlar[i + 1:]:
            h1, h2 = d1.get("_ham_confidence"), d2.get("_ham_confidence")
            if h1 is not None and h1 == h2 and d1.get("stance") == d2.get("stance"):
                b.append(_bulgu("TAKLIT", "K3-COKLU-AJAN",
                                f"{d1.get('name')} ve {d2.get('name')} aynı duruş "
                                f"({d1.get('stance')}) ve birebir aynı ham güven ({h1}) "
                                "— bağımsız üretim şüpheli"))

    # GOREV_SAPMASI — job'da beyan edilen iş yapılmamış
    beyan = [("korelasyon", job.get("korelasyon"), "korelasyon" in motorlar),
             ("backtest-motoru", job.get("backtest"), "backtest-motoru" in motorlar),
             ("usd_hedef", job.get("usd_profil"), bool(k5.get("usd_hedef")))]
    for ad, istendi, yapildi in beyan:
        if istendi and not yapildi:
            b.append(_bulgu("GOREV_SAPMASI", "ZİNCİR",
                            f"job'da BEYAN EDİLEN '{ad}' işi yapılmadı ve gerekçesi yok"))
    for e in (zirve.get("ZORUNLU_EKSIK") or []):
        # P1, P0 DEĞİL: zorunlu girdi eksikliği ajanın görev sapması değil,
        # KULLANICI tarafından verilmemiş bir kanaldır. CLAUDE.md sözleşmesi
        # bunu zaten K1'de tespit edip K4'te çelişki olarak taşıyor ve çıktının
        # EN ÜSTÜNDE "⚠ ZORUNLU GİRDİ EKSİK" satırıyla gösteriyor; türev kapsamı
        # düşünce danışman da fail-closed doğrulanmamış sayılıyor. P0 saymak
        # CoinGlass paneli/görsel elle verilmeyen HER koşuyu mühürler — sözleşmede
        # olmayan, sistemi kullanılamaz kılan bir davranış. Bulgu GİZLENMEZ,
        # yalnız mühür yetkisi yoktur.
        b.append(_bulgu("GOREV_SAPMASI", "K1-LLM",
                        f"zorunlu girdi eksik, görev tam koşulmadı: {str(e)[:80]}",
                        severity="P1"))

    # GIZLI_GUNDEM — yön var ama o yönü DOĞRULANMIŞ tek bir danışman bile yok
    yon = str((k5.get("sentez") or {}).get("YON_BIAS", zirve.get("YON_BIAS", ""))).upper()
    if yon in ("LONG", "SHORT"):
        destek = [d.get("name") for d in danismanlar
                  if str(d.get("stance", "")).upper() == yon
                  and (ver.get(d.get("name")) or {}).get("confirmed")]
        if not destek:
            b.append(_bulgu("GIZLI_GUNDEM", "K5-SI",
                            f"YÖN {yon} ama bu yönü DOĞRULANMIŞ tek danışman yok — "
                            "karar beyan edilmemiş bir gerekçeye yaslanıyor"))

    # MEMNUN_ETME — teslimde kapı ile hüküm çelişiyor mu (mühürlüyken emir var mı)
    if (rapor.get("DENETIM") or {}).get("muhurlendi") and \
            not str(zirve.get("EMIR", "")).startswith("EMİR YOK"):
        b.append(_bulgu("MEMNUN_ETME", "K5-SI",
                        "gözlemci mührüne rağmen uygulanabilir EMİR basılmış"))

    # gozlemci.py bulgularını da sıralamaya kat (ikisi tek panelde görünsün)
    for x in ((rapor.get("DENETIM") or {}).get("ihlal") or []):
        kod = str(x).split("/")[1].split(":")[0] if "/" in str(x) else "SIRADAN"
        b.append(_bulgu(kod if kod in SEVERITY else "SIRADAN",
                        str(x).split("/")[0], f"[gözlemci] {str(x)[:140]}"))
    return _paketle(b, rapor.get("sembol", YOK), len(rapor.get("katmanlar") or []))


# --------------------------------------------------------------------------
def _paketle(bulgular: list, konu: str, adim_sayisi: int) -> dict:
    sira = {"P0": 0, "P1": 1, "P2": 2}
    bulgular = sorted(bulgular, key=lambda x: (sira.get(x["severity"], 3), x["kod"]))
    p0 = [x for x in bulgular if x["severity"] == "P0"]
    hukum = ("MÜHÜR — teslim bu haliyle kullanılamaz" if p0
             else "UYARI — teslim edilebilir, bulgular açıkça yazılır"
             if bulgular else "TEMİZ")
    return {
        "konu": konu,
        "hukum": hukum,
        "muhurlendi": bool(p0),
        "ozet": (f"{adim_sayisi} adım denetlendi, {len(bulgular)} bulgu "
                 f"(P0={len(p0)}, P1={sum(1 for x in bulgular if x['severity'] == 'P1')}, "
                 f"P2={sum(1 for x in bulgular if x['severity'] == 'P2')})"),
        "bulgular": bulgular,
        "duzeltme_plani": [{"sira": i + 1, "severity": x["severity"], "kod": x["kod"],
                            "adim": x["adim"], "yap": x["duzeltme"]}
                           for i, x in enumerate(bulgular)],
        "not": ("Kontrol ajanı ZİHİN okumaz: dosya var mı, sayı kaynakta geçiyor mu, "
                "ajan diğerini görmüş mü, adım çıktı üretmiş mi — hepsi artefakttan "
                "ölçülür. P0 bulgu teslimi MÜHÜRLER (sonuç gösterilir, 'kullanılamaz' "
                "denir)."),
    }


# --------------------------------------------------------------------------
# XML çıktı
# --------------------------------------------------------------------------
def _kacir(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def xml_panel(sonuc: dict) -> str:
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<kontrol_paneli konu="{_kacir(sonuc.get("konu"))}" '
         f'hukum="{_kacir(sonuc.get("hukum"))}" '
         f'muhurlendi="{str(bool(sonuc.get("muhurlendi"))).lower()}">',
         f'  <ozet>{_kacir(sonuc.get("ozet"))}</ozet>', '  <bulgular>']
    for x in sonuc.get("bulgular") or []:
        L.append(f'    <bulgu kod="{_kacir(x["kod"])}" severity="{_kacir(x["severity"])}" '
                 f'adim="{_kacir(x["adim"])}" ajan="{_kacir(x["ajan"])}">')
        L.append(f'      <kanit>{_kacir(x["kanit"])}</kanit>')
        L.append(f'      <duzeltme>{_kacir(x["duzeltme"])}</duzeltme>')
        L.append('    </bulgu>')
    L.append('  </bulgular>')
    L.append('  <duzeltme_plani>')
    for d in sonuc.get("duzeltme_plani") or []:
        L.append(f'    <adim sira="{d["sira"]}" severity="{_kacir(d["severity"])}" '
                 f'kod="{_kacir(d["kod"])}">{_kacir(d["yap"])}</adim>')
    L.append('  </duzeltme_plani>')
    L.append(f'  <not>{_kacir(sonuc.get("not"))}</not>')
    L.append('</kontrol_paneli>')
    return "\n".join(L)


def ozet_metin(sonuc: dict) -> str:
    L = [f"KONTROL AJANLARI: {sonuc['ozet']}"
         + ("  ⛔ MÜHÜR" if sonuc["muhurlendi"] else "  ✔ temiz")]
    for x in (sonuc.get("bulgular") or [])[:8]:
        isaret = {"P0": "⛔", "P1": "⚠", "P2": "·"}.get(x["severity"], "·")
        L.append(f"   {isaret} [{x['severity']}] {x['kod']} @{x['adim']}: {x['kanit'][:96]}")
    return "\n".join(L)


# --------------------------------------------------------------------------
def _oz_test() -> int:
    """Her kodun hem tetiklendiğini hem temiz durumda tetiklenmediğini sınar."""
    tmp = Path(__file__).resolve().parent / "_kontrol_test_artefakt.json"
    tmp.write_text(json.dumps({"olcum": [42.0, 7.5]}), encoding="utf-8")
    temiz = {
        "gorev": "test", "gorev_maddeleri": [{"id": "M1", "metin": "ölç"}],
        "adimlar": [
            {"id": "Z1", "ad": "KANIT", "ajan": "a1", "gecti": True, "kapi": "ölçüm var",
             "bagimsiz": True, "girdi_id": [], "kapsanan_maddeler": ["M1"],
             "artefaktlar": [{"tur": "dosya", "ref": str(tmp), "okundu": True}],
             "iddialar": [{"metin": "ölçüm 42", "sayilar": [42.0], "kaynak": str(tmp)}]},
            {"id": "Z2", "ad": "SENTEZ", "ajan": "a2", "gecti": True, "kapi": "sentez",
             "bagimsiz": False, "girdi_id": ["Z1"], "kapsanan_maddeler": ["M1"],
             "artefaktlar": [{"tur": "arac", "ref": "sentez.py", "okundu": True,
                              "sayilar": [7.5]}],
             "iddialar": [{"metin": "sonuç 7.5", "sayilar": [7.5], "kaynak": "sentez.py"}]}],
        "dogrulamalar": [
            {"iddia": "ölçüm 42", "dogrulayan_ajan": "a9", "aile": "olcum", "sonuc": "ONAY"},
            {"iddia": "sonuç 7.5", "dogrulayan_ajan": "a8", "aile": "hesap", "sonuc": "ONAY"},
            {"iddia": "sonuç 7.5", "dogrulayan_ajan": "a7", "aile": "hesap",
             "sonuc": "ÇÜRÜTÜLDÜ"}],
        "teslim": {"metin": "42 ve 7.5", "sayilar": [42.0, 7.5], "girdi_id": ["Z2"]},
    }
    r = denetle_zincir(temiz)
    assert not r["bulgular"], f"temiz defterde bulgu çıktı: {r['bulgular']}"

    def boz(f):
        d = json.loads(json.dumps(temiz))
        f(d)
        return {x["kod"] for x in denetle_zincir(d)["bulgular"]}

    kontroller = [
        ("UYDURMA", lambda d: d["adimlar"][0]["iddialar"].append(
            {"metin": "uydurma", "sayilar": [999.99], "kaynak": str(tmp)})),
        ("UYDURMA", lambda d: d["adimlar"][0]["artefaktlar"].__setitem__(
            0, {"tur": "dosya", "ref": "/yok/dosya.json", "okundu": True})),
        ("ARASTIRMASIZ", lambda d: d["adimlar"][0].__setitem__("artefaktlar", [])),
        ("HAFIZA", lambda d: d["adimlar"][0]["iddialar"][0].__setitem__(
            "kaynak", "model bilgisi")),
        # bulaşma: beslenmediği halde akranın çıktısına bakmış
        ("BULASMA", lambda d: (d["adimlar"][1].__setitem__("bagimsiz", True),
                               d["adimlar"][1].__setitem__("girdi_id", []),
                               d["adimlar"][1].__setitem__("gordugu_adimlar", ["Z1"]))),
        ("TAKLIT", lambda d: (d["adimlar"][1].__setitem__("bagimsiz", True),
                              d["adimlar"][1]["iddialar"][0].__setitem__(
                                  "sayilar", [42.0]))),
        ("DAIRESEL", lambda d: d["dogrulamalar"][0].__setitem__("dogrulayan_ajan", "a1")),
        ("MEMNUN_ETME", lambda d: d["dogrulamalar"][2].__setitem__("sonuc", "ONAY")),
        ("MEMNUN_ETME", lambda d: d.__setitem__("kullanici_itirazi", {
            "fikir_degisti": True, "yeni_kanit": [], "eski": "A", "yeni": "B"})),
        ("GOREV_SAPMASI", lambda d: d["gorev_maddeleri"].append(
            {"id": "M2", "metin": "kapsanmayan"})),
        ("GIZLI_GUNDEM", lambda d: d["teslim"]["sayilar"].append(123.456)),
        ("TUNEL", lambda d: d["dogrulamalar"][1].__setitem__("aile", "olcum")),
        ("TIYATRO", lambda d: d["adimlar"].append(
            {"id": "Z3", "ad": "BOŞ", "ajan": "a3", "gecti": True, "kapi": "-",
             "girdi_id": ["Z2"]})),
        ("EKSIK_AKTARIM", lambda d: d["adimlar"].append(
            {"id": "Z3", "ad": "KAYIP", "ajan": "a3", "gecti": True, "kapi": "-",
             "girdi_id": ["Z2"], "artefaktlar": [{"tur": "arac", "ref": "x",
                                                  "okundu": True, "sayilar": [7.5]}],
             "iddialar": [{"metin": "kayıp", "sayilar": [7.5], "kaynak": "x"}]})),
        ("SIRADAN", lambda d: d["adimlar"][0].pop("kapi")),
    ]
    for kod, f in kontroller:
        kodlar = boz(f)
        assert kod in kodlar, f"{kod} tetiklenmedi (çıkan: {kodlar})"

    # piramit tarafı: mühürlüyken emir basılırsa MEMNUN_ETME
    pr = {"sembol": "TEST", "katmanlar": [
        {"katman": "K1-LLM", "gecti": True, "kanallar": {"15m": "a.json"}},
        {"katman": "K3-COKLU-AJAN", "gecti": True, "danismanlar": [
            {"name": "m1", "stance": "long", "_ham_confidence": 0.5},
            {"name": "m2", "stance": "long", "_ham_confidence": 0.5}]},
        {"katman": "K4-AGI", "gecti": True, "kapi": "geçti", "verifier": {}}],
        "ZIRVE": {"YON_BIAS": "LONG", "EMIR": "LIMIT LONG @1"},
        "DENETIM": {"muhurlendi": True, "ihlal": []},
        "_job": {"korelasyon": True}}
    kodlar = {x["kod"] for x in denetle_piramit(pr)["bulgular"]}
    for beklenen in ("TAKLIT", "GOREV_SAPMASI", "GIZLI_GUNDEM", "MEMNUN_ETME",
                     "ARASTIRMASIZ", "TIYATRO"):
        assert beklenen in kodlar, f"piramit: {beklenen} yok ({kodlar})"
    # YANLIŞ-POZİTİF korkuluğu: yapısal çıktı üreten katman TİYATRO sayılmamalı
    pr2 = json.loads(json.dumps(pr))
    pr2["katmanlar"] = pr2["katmanlar"][:2]
    tiyatrolar = [x for x in denetle_piramit(pr2)["bulgular"] if x["kod"] == "TIYATRO"]
    assert not tiyatrolar, f"danışman üreten katman tiyatro sayıldı: {tiyatrolar}"

    assert xml_panel(r).startswith("<?xml")
    tmp.unlink(missing_ok=True)
    print(f"ÖZ-TEST TAMAM — {len(kontroller)} bozma senaryosu + temiz defter + "
          "piramit denetimi geçti")
    return 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Kontrol ajanları denetimi")
    ap.add_argument("--zincir", help="zincir defteri JSON (konudan bağımsız)")
    ap.add_argument("--rapor", help="piramit.py --out raporu")
    ap.add_argument("--xml", action="store_true", help="XML panel bas")
    ap.add_argument("--ozet", action="store_true", help="tek satırlık özet bas")
    ap.add_argument("--mimari", action="store_true", help="mimari XML dosyasını bas")
    ap.add_argument("--oz-test", action="store_true", help="öz-test koş")
    a = ap.parse_args(argv)

    if a.oz_test:
        return _oz_test()
    if a.mimari:
        p = Path(__file__).resolve().parents[3] / "kontrol" / "kontrol_mimari.xml"
        print(p.read_text(encoding="utf-8"))
        return 0
    if not (a.zincir or a.rapor):
        ap.error("--zincir ya da --rapor gerekli")
    if a.zincir:
        sonuc = denetle_zincir(json.loads(
            Path(a.zincir).expanduser().read_text(encoding="utf-8")))
    else:
        sonuc = denetle_piramit(json.loads(
            Path(a.rapor).expanduser().read_text(encoding="utf-8")))
    if a.xml:
        print(xml_panel(sonuc))
    elif a.ozet:
        print(ozet_metin(sonuc))
    else:
        print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    return 2 if sonuc["muhurlendi"] else 0


if __name__ == "__main__":
    sys.exit(main())
