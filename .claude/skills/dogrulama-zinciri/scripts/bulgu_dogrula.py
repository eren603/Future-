#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BULGU DOĞRULAYICI — her iddia için BAĞIMSIZ doğrulama; doğrulanmayan ELENİR.

Kaynak 1: `cc/plugins/code-review/commands/code-review.md` (109 satır)
Kaynak 2: `a-defending-code-reference-harness/.claude/skills/verify/SKILL.md` (42 satır)

Kaynak 1'in 4-6. adımları (BİREBİR):

  ":30  4. Launch 4 agents in parallel to independently review the changes.
         Each agent should return the list of issues, where each issue includes a
         description and the reason it was flagged (e.g. "CLAUDE.md adherence", "bug")."
  ":41  **CRITICAL: We only want HIGH SIGNAL issues.**"
  ":51  If you are not certain an issue is real, do not flag it. False positives
         erode trust and waste reviewer time."
  ":55  5. For each issue found in the previous step by agents 3 and 4, launch
         parallel subagents to validate the issue."
  ":57  6. Filter out any issues that were not validated in step 5. This step will
         give us our list of high signal issues for our review."

Bu depoda "inceleme konusu" bir diff değil, bir **piramit koşusunun kararıdır**:
yön iddiası (`ZIRVE.YON_BIAS`), emir seviyeleri (`ZIRVE.EMIR`,
`emir_adaylari[]`), danışman duruşları (`K3.danismanlar[]`, `K5.sentez`), kapı
hükümleri (`kapi_gerekceleri`, `DENETIM`).

DÖRT İNCELEYİCİ (kaynak adım 4'ün dört ajanı — code-review.md:30-39):
  sozlesme_1 (orta ← sonnet, :32)  — EMİR kapsamındaki CLAUDE.md kuralları
  sozlesme_2 (orta ← sonnet, :32)  — ÇIKTI sözleşmesi kuralları
  hata_1     (pahalı ← opus, :35)  — "Focus only on the diff itself without
                                      reading extra context": YALNIZ `ZIRVE`
  hata_2     (pahalı ← opus, :38)  — "problems that exist in the introduced
                                      code": koşunun ÜRETTİĞİ sentez/kapı mantığı
Kapsam kuralı (:33 "you should only consider CLAUDE.md files that share a file
path with the file or parents") → her sözleşme kuralı yalnız KENDİ kapsamındaki
artefakta uygulanır (`kapsam` alanı).

ÇOKLU-OY (kaynak 2). `verify/SKILL.md` bir iddiayı, iddiayı üretenin kendi
raporuna sormak yerine BAĞIMSIZ bir kanaldan yakalanan artefakta sorar:

  ":18  a tiny HTTP server that appends each request's headers to a JSONL file"
  ":31-32  , then read / the captured JSONL."   (iki satır birleştirildi)

Buradaki karşılığı: bir bulgu, raporun BİRDEN ÇOK bağımsız alanından ayrı ayrı
okunur (`--oy N`) ve **çoğunluk kuralı** uygulanır. Kanıtı açılamayan oy
KANIT_YOK'tur ve aleyhe sayılır (fail-closed) — bu, evaluator.md:15'in
"If a file fails to open or returns an error, treat it as missing evidence"
kuralının veri düzeyindeki hâlidir. Tek kanallı bulgu doğrulanmış SAYILMAZ
(dairesel doğrulama korkuluğu). Oy sayısı mevcut BAĞIMSIZ kanal sayısını AŞAMAZ
— eksik oy UYDURULMAZ (aynı kanalı iki kez saymak `gozlemci.py`'nin ÇARPIŞMA
ihlalidir).

DÜRÜSTLÜK NOTU: burada gerçek alt-ajan BAŞLATILMAZ. Kaynağın "launch parallel
subagents to validate" adımı, deterministik ve kanıtı dosyadan okunan Python
kontrollerine çevrilmiştir; "paralel" değil ardışık koşar (sonuç aynı, çünkü
kontroller birbirinden bağımsızdır). Bkz. KANIT.md → SAPMALAR.

Kullanım:
  python3 bulgu_dogrula.py --rapor <son_rapor.json> [--onceki <onceki.json>]
                           [--oy 3] [--ozet] [--ayrinti]
  python3 bulgu_dogrula.py --self-test

Çıkış kodu: 0 = doğrulanmış bulgu YOK, 1 = doğrulanmış bulgu VAR,
            2 = kullanım/okuma hatası.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

YOK = "VERİ YOK"

# CLAUDE.md emir kapısı — "R < 1.35 olan reddedilir"
R_MIN = 1.35
# sentez.py:170 — "beklerken güven tavanı"
BEKLE_GUVEN_TAVANI = 0.35
# :83 "Pedantic nitpicks a senior engineer would not flag" — önem eşiği
ONEM_ESIGI_R = 0.02
ONEM_ESIGI_FIYAT = 0.05

EMIR_RE = re.compile(
    r"^(MARKET|LIMIT)\s+(LONG|SHORT)\s*@\s*([-\d.]+)\s*\|\s*stop\s+([-\d.]+)"
    r"\s*\|\s*T1\s+([-\d.]+)\s*\|\s*R\s+([-\d.]+)")

# HIGH SIGNAL ölçütleri (code-review.md:42-44) — bulgu bunlardan BİRİNE
# bağlanamıyorsa bayraklanmaz.
YUKSEK_SINYAL = {
    ":42": "kod ayrıştırılamaz/çözümsüz atıf (fail to compile or parse, "
           "unresolved references)",
    ":43": "girdiden bağımsız kesin yanlış sonuç (clear logic errors)",
    ":44": "kuralı BİREBİR alıntılanabilen açık sözleşme ihlali",
}

# Bayraklanmayacak sınıflar (code-review.md:46-50)
BAYRAKSIZ_SINIF = {
    "bicim": ":47 Code style or quality concerns",
    "kosullu": ":48 Potential issues that depend on specific inputs or state",
    "oneri": ":49 Subjective suggestions or improvements",
}

# Yanlış-pozitif listesi (code-review.md:79-86)
YANLIS_POZITIF = {
    ":81": "Pre-existing issues",
    ":82": "Something that appears to be a bug but is actually correct",
    ":83": "Pedantic nitpicks that a senior engineer would not flag",
    ":84": "Issues that a linter will catch (do not run the linter to verify)",
    ":85": "General code quality concerns … unless explicitly required in CLAUDE.md",
    ":86": "Issues mentioned in CLAUDE.md but explicitly silenced in the code",
}


class BulguError(Exception):
    pass


# ---------------------------------------------------------------------------
# okuma yardımcıları — her kanıt DOSYADAN okunur, hiçbiri türetilmez
# ---------------------------------------------------------------------------
def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def baglam(rapor: dict) -> dict:
    """Katmanları K1…K5 anahtarlarıyla erişilebilir yapar (yol ifadeleri için)."""
    ctx = dict(rapor)
    for k in rapor.get("katmanlar") or []:
        ad = str(k.get("katman", ""))
        if ad[:2] in ("K1", "K2", "K3", "K4", "K5"):
            ctx[ad[:2]] = k
    return ctx


def al(kok, yol: str):
    """Noktalı yol okuyucu: 'K5.emir_plani.birincil.R', 'ZIRVE.emir_adaylari.0.yon'.
    Bulunamayan yol None döner → oy KANIT_YOK olur (fail-closed)."""
    cur = kok
    for parca in yol.split("."):
        if isinstance(cur, dict):
            if parca not in cur:
                return None
            cur = cur[parca]
        elif isinstance(cur, list):
            try:
                cur = cur[int(parca)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def emir_coz(metin) -> dict | None:
    """'LIMIT SHORT @63990.7 | stop 64234.1 | T1 63461.2 | R 2.18' → alanlar."""
    m = EMIR_RE.match(str(metin or "").strip())
    if not m:
        return None
    return {"emir_tipi": m.group(1), "yon": m.group(2), "giris": float(m.group(3)),
            "stop": float(m.group(4)), "hedef": float(m.group(5)),
            "R": float(m.group(6))}


def _bulgu(kod, inceleyici, sinif, aciklama, neden, kural, *, kesin=True,
           alinti="", kapsam="", onem=1.0, kanallar=None, **ek):
    b = {
        "kod": kod, "inceleyici": inceleyici, "sinif": sinif,
        "aciklama": aciklama,
        # code-review.md:30 "each issue includes a description and the reason it
        # was flagged (e.g. "CLAUDE.md adherence", "bug")"
        "neden_bayraklandi": neden,
        "yuksek_sinyal_kural": kural,
        "kesin": bool(kesin),
        "kural_alintisi": alinti,
        "kapsam": kapsam,
        "onem": float(onem),
        "oy_kanallari": kanallar or [],
    }
    b.update(ek)
    return b


def _kanal(kanal, yol, deger, sorunlu: bool | None):
    """Tek bir bağımsız okuma. sorunlu=None → kanıt açılamadı (KANIT_YOK)."""
    return {"kanal": kanal, "yol": yol, "deger": deger, "sorunlu": sorunlu}


# ---------------------------------------------------------------------------
# İNCELEYİCİ 3 — hata_1 (pahalı ← opus, code-review.md:35-36)
#   "Focus only on the diff itself without reading extra context."
#   → YALNIZ ZIRVE bloğu okunur; katman içi üretim yoluna bakılmaz.
# ---------------------------------------------------------------------------
def inceleyici_hata_1(ctx: dict) -> list:
    b = []
    z = ctx.get("ZIRVE") or {}
    emir_metni = str(z.get("EMIR", YOK))
    coz = emir_coz(emir_metni)
    adaylar = z.get("emir_adaylari") or []
    a0 = adaylar[0] if adaylar else {}
    yon_bias = str(z.get("YON_BIAS", YOK)).strip().upper()

    # H1 — basılan emir metni ile yapısal kayıt uyuşmuyor (:42 parse/atıf)
    if coz and a0:
        farklar = []
        for alan in ("yon", "giris", "stop", "hedef", "R"):
            av, mv = a0.get(alan), coz.get(alan)
            if isinstance(mv, float) and _num(av) is not None:
                if abs(float(av) - mv) > 1e-6:
                    farklar.append((alan, av, mv))
            elif str(av).upper() != str(mv).upper():
                farklar.append((alan, av, mv))
        if farklar:
            b.append(_bulgu(
                "EMIR_METNI_UYUSMAZ", "hata_1", "hata",
                f"Basılan EMİR metni ile emir_adaylari[0] uyuşmuyor: {farklar}",
                "bug — çözümsüz atıf (basılan sayı hiçbir kayıtta yok)", ":42",
                kapsam="ZIRVE.EMIR", onem=1.0,
                kanallar=[
                    _kanal("emir_adaylari", "ZIRVE.emir_adaylari.0",
                           {k: a0.get(k) for k, _, _ in farklar}, True),
                    _kanal("emir_plani.birincil", "K5.emir_plani.birincil",
                           al(ctx, "K5.emir_plani.birincil"),
                           al(ctx, "K5.emir_plani.birincil") is not None),
                    _kanal("emir_plani.EMIR", "K5.emir_plani.EMIR",
                           al(ctx, "K5.emir_plani.EMIR"),
                           (al(ctx, "K5.emir_plani.EMIR") != emir_metni)
                           if al(ctx, "K5.emir_plani.EMIR") is not None else None),
                ]))

    # H2 — emir yönü ile karar yönü ters (:43 kesin yanlış)
    if coz and yon_bias in ("LONG", "SHORT") and coz["yon"] != yon_bias:
        skor = _num(z.get("yon_skoru"))
        skor_yon = None if skor is None else ("LONG" if skor > 0 else
                                              ("SHORT" if skor < 0 else "NÖTR"))
        b.append(_bulgu(
            "EMIR_YON_CELISKISI", "hata_1", "hata",
            f"Emir yönü {coz['yon']} ama YON_BIAS {yon_bias}",
            "bug — karar yönü ile emir yönü ters", ":43",
            kapsam="ZIRVE.EMIR", onem=1.0, gozlemci_kodu="MEMNUN_ETME",
            kanallar=[
                _kanal("EMIR metni", "ZIRVE.EMIR", coz["yon"], True),
                _kanal("emir_adaylari", "ZIRVE.emir_adaylari.0.yon",
                       a0.get("yon"),
                       None if a0.get("yon") is None
                       else str(a0["yon"]).upper() != yon_bias),
                _kanal("emir_plani", "K5.emir_plani.yon",
                       al(ctx, "K5.emir_plani.yon"),
                       None if al(ctx, "K5.emir_plani.yon") is None
                       else str(al(ctx, "K5.emir_plani.yon")).upper() != yon_bias),
                _kanal("yon_skoru işareti", "ZIRVE.yon_skoru", skor,
                       None if skor_yon is None else skor_yon != coz["yon"]),
            ]))

    # H3 — R aritmetiği tutarsız (:43)
    if coz:
        risk_m = abs(coz["giris"] - coz["stop"])
        odul_m = abs(coz["hedef"] - coz["giris"])
        hesap_m = odul_m / risk_m if risk_m else None
        # AYNI hesabı tam-hassasiyetli kayıtlardan da yap (:82 mutabakat yolu):
        # basılan seviyeler YUVARLANMIŞTIR; motor kaydı yuvarlanmamıştır.
        def _hesap(kayit):
            if not kayit or any(_num((kayit or {}).get(k)) is None
                                for k in ("giris", "stop", "hedef")):
                return None
            r_ = abs(float(kayit["giris"]) - float(kayit["stop"]))
            o_ = abs(float(kayit["hedef"]) - float(kayit["giris"]))
            return (o_ / r_) if r_ else None

        hesap_a = _hesap(a0)                                   # ZIRVE kaydı
        hesap_t = _hesap(al(ctx, "K5.emir_plani.birincil"))    # motor kaydı
        if hesap_m is not None:
            fark_m = abs(hesap_m - coz["R"])
            uyustu = any(h is not None and abs(h - coz["R"]) <= 0.005
                         for h in (hesap_a, hesap_t))
            if fark_m > 0.005:
                b.append(_bulgu(
                    "R_ARITMETIK_TUTARSIZ", "hata_1", "hata",
                    f"Basılan R {coz['R']} ≠ |hedef−giriş|/|giriş−stop| "
                    f"= {hesap_m:.4f} (fark {fark_m:.4f})",
                    "bug — aritmetik hata (girdiden bağımsız)", ":43",
                    kapsam="ZIRVE.EMIR", onem=fark_m,
                    yeniden_hesap_uyustu=uyustu,
                    kanallar=[
                        _kanal("aritmetik (metin)", "ZIRVE.EMIR",
                               round(hesap_m, 4), True),
                        _kanal("aritmetik (kayıt)", "ZIRVE.emir_adaylari.0",
                               None if hesap_a is None else round(hesap_a, 4),
                               None if hesap_a is None
                               else abs(hesap_a - coz["R"]) > 0.005),
                        _kanal("aritmetik (motor kaydı)",
                               "K5.emir_plani.birincil",
                               None if hesap_t is None else round(hesap_t, 4),
                               None if hesap_t is None
                               else abs(hesap_t - coz["R"]) > 0.005),
                    ]))

    # H4 — yön geometrisi bozuk (:43) — rr_denetim.py:57 kuralı
    if coz:
        g = ((coz["stop"] > coz["giris"] > coz["hedef"]) if coz["yon"] == "SHORT"
             else (coz["stop"] < coz["giris"] < coz["hedef"]))
        if not g:
            a_g = None
            if a0 and all(_num(a0.get(k)) is not None
                          for k in ("giris", "stop", "hedef")):
                a_g = ((float(a0["stop"]) > float(a0["giris"]) > float(a0["hedef"]))
                       if str(a0.get("yon", "")).upper() == "SHORT"
                       else (float(a0["stop"]) < float(a0["giris"]) < float(a0["hedef"])))
            rr = a0.get("rr_denetim")
            b.append(_bulgu(
                "GEOMETRI_BOZUK", "hata_1", "hata",
                f"{coz['yon']} geometrisi bozuk: stop {coz['stop']} / "
                f"giriş {coz['giris']} / hedef {coz['hedef']}",
                "bug — rr_denetim.py:57 geometri kuralı ihlali", ":43",
                kapsam="ZIRVE.EMIR", onem=1.0,
                kanallar=[
                    _kanal("EMIR metni", "ZIRVE.EMIR", coz, True),
                    _kanal("emir_adaylari", "ZIRVE.emir_adaylari.0",
                           {k: a0.get(k) for k in ("giris", "stop", "hedef")},
                           None if a_g is None else (not a_g)),
                    _kanal("rr_denetim", "ZIRVE.emir_adaylari.0.rr_denetim", rr,
                           None if rr is None else str(rr) != "TUTARLI"),
                ]))

    # H5 — mühürlü koşuda emir basılmış (:43) — piramit.py:1664
    muhur = bool(al(ctx, "DENETIM.muhurlendi"))
    if muhur and coz:
        b.append(_bulgu(
            "MUHURLU_EMIR", "hata_1", "hata",
            "DENETİM MÜHÜRÜ varken uygulanabilir emir basılmış",
            "bug — mühürde emir kapanmalıydı (piramit.py:1664)", ":43",
            kapsam="ZIRVE.EMIR", onem=1.0,
            kanallar=[
                _kanal("EMIR", "ZIRVE.EMIR", emir_metni[:48], True),
                _kanal("emir_adaylari", "ZIRVE.emir_adaylari", len(adaylar),
                       len(adaylar) > 0),
                _kanal("ISLEM_KALITESI", "ZIRVE.ISLEM_KALITESI",
                       z.get("ISLEM_KALITESI"),
                       "DENETİM İHLALİ" not in str(z.get("ISLEM_KALITESI", ""))),
            ]))

    # H6 — R kapısı ihlali (:43) — CLAUDE.md "R < 1.35 olan reddedilir"
    for i, a in enumerate(adaylar):
        R = _num(a.get("R"))
        if R is not None and R < R_MIN:
            b.append(_bulgu(
                "R_KAPISI_IHLALI", "hata_1", "hata",
                f"Emir adayı {i} R={R} < {R_MIN} olduğu hâlde sunulmuş",
                "bug — emir kapısı uygulanmamış", ":43",
                kapsam="ZIRVE.emir_adaylari", onem=R_MIN - R,
                kanallar=[
                    _kanal("aday.R", f"ZIRVE.emir_adaylari.{i}.R", R, True),
                    _kanal("EMIR metni", "ZIRVE.EMIR",
                           None if not coz else coz["R"],
                           None if not coz else coz["R"] < R_MIN),
                    _kanal("emir_plani", f"K5.emir_plani.adaylar.{i}.R",
                           al(ctx, f"K5.emir_plani.adaylar.{i}.R"),
                           None if al(ctx, f"K5.emir_plani.adaylar.{i}.R") is None
                           else float(al(ctx, f"K5.emir_plani.adaylar.{i}.R")) < R_MIN),
                ]))
    return b


# ---------------------------------------------------------------------------
# İNCELEYİCİ 4 — hata_2 (pahalı ← opus, code-review.md:38-39)
#   "Look for problems that exist in the introduced code … Only look for issues
#    that fall within the changed code."
#   → koşunun ÜRETTİĞİ sentez/kapı mantığı (K3/K4/K5)
# ---------------------------------------------------------------------------
def inceleyici_hata_2(ctx: dict) -> list:
    b = []
    z = ctx.get("ZIRVE") or {}
    adaylar = z.get("emir_adaylari") or []

    # I1 — rr_denetim TUTARLI değilken aday sunulmuş (:43)
    for i, a in enumerate(adaylar):
        rr = str(a.get("rr_denetim", YOK))
        if rr not in ("TUTARLI", YOK):
            b.append(_bulgu(
                "RR_DENETIMSIZ_ADAY", "hata_2", "hata",
                f"Aday {i} rr_denetim={rr} olduğu hâlde emir listesinde",
                "bug — şişirilmiş R kapısı uygulanmamış", ":43",
                kapsam="K5.emir_plani", onem=1.0,
                susturma_izi=f"giriş {a.get('giris')}",
                kanallar=[
                    _kanal("aday.rr_denetim", f"ZIRVE.emir_adaylari.{i}.rr_denetim",
                           rr, True),
                    _kanal("emir_plani", f"K5.emir_plani.adaylar.{i}.rr_denetim",
                           al(ctx, f"K5.emir_plani.adaylar.{i}.rr_denetim"),
                           None if al(ctx, f"K5.emir_plani.adaylar.{i}.rr_denetim")
                           is None else
                           str(al(ctx, f"K5.emir_plani.adaylar.{i}.rr_denetim"))
                           != "TUTARLI"),
                    _kanal("K4.rr_denetimi", "K4.rr_denetimi",
                           al(ctx, "K4.rr_denetimi"),
                           None if al(ctx, "K4.rr_denetimi") is None
                           else not al(ctx, "K4.rr_denetimi")),
                ]))

    # I2 — kapı gerekçesi var ama karar BEKLE değil (:43) — sentez.py:159-164
    kapilar = z.get("kapi_gerekceleri") or []
    karar = str(z.get("sentez_karari", YOK))
    if kapilar and karar not in ("NÖTR-BEKLE", YOK):
        b.append(_bulgu(
            "KAPI_KARAR_CELISKISI", "hata_2", "hata",
            f"{len(kapilar)} kapı gerekçesi var ama sentez_karari={karar}",
            "bug — fail-closed kapı uygulanmamış", ":43",
            kapsam="K5.sentez", onem=1.0, gozlemci_kodu="MEMNUN_ETME",
            kanallar=[
                _kanal("ZIRVE.karar", "ZIRVE.sentez_karari", karar, True),
                _kanal("K5.sentez.KARAR", "K5.sentez.KARAR",
                       al(ctx, "K5.sentez.KARAR"),
                       None if al(ctx, "K5.sentez.KARAR") is None
                       else str(al(ctx, "K5.sentez.KARAR")) != "NÖTR-BEKLE"),
                _kanal("kapi_gerekceleri", "ZIRVE.kapi_gerekceleri",
                       len(kapilar), len(kapilar) > 0),
            ]))

    # I3 — BEKLE kararında güven tavanı aşılmış (:43) — sentez.py:169-170
    guven = _num(z.get("guven_skoru"))
    if karar == "NÖTR-BEKLE" and guven is not None and guven > BEKLE_GUVEN_TAVANI:
        b.append(_bulgu(
            "GUVEN_TAVANI_IHLALI", "hata_2", "hata",
            f"BEKLE kararında guven_skoru {guven} > tavan {BEKLE_GUVEN_TAVANI}",
            "bug — sentez.py:170 güven tavanı uygulanmamış", ":43",
            kapsam="K5.sentez", onem=guven - BEKLE_GUVEN_TAVANI,
            kanallar=[
                _kanal("ZIRVE.guven", "ZIRVE.guven_skoru", guven, True),
                _kanal("K5.sentez.guven", "K5.sentez.guven_skoru",
                       al(ctx, "K5.sentez.guven_skoru"),
                       None if _num(al(ctx, "K5.sentez.guven_skoru")) is None
                       else _num(al(ctx, "K5.sentez.guven_skoru")) > BEKLE_GUVEN_TAVANI),
                _kanal("karar", "ZIRVE.sentez_karari", karar, karar == "NÖTR-BEKLE"),
            ]))

    # I4 — YON_BIAS ile yon_skoru işareti uyuşmuyor (:43) — sentez.py:177-185
    skor = _num(z.get("yon_skoru"))
    yb = str(z.get("YON_BIAS", YOK)).strip().upper()
    if skor is not None and yb in ("LONG", "SHORT", "NÖTR"):
        beklenen = "LONG" if skor > 0 else ("SHORT" if skor < 0 else "NÖTR")
        if beklenen != yb:
            b.append(_bulgu(
                "YON_SKOR_UYUSMAZ", "hata_2", "hata",
                f"YON_BIAS={yb} ama yon_skoru={skor} → {beklenen} olmalıydı",
                "bug — yon_bias() işaret kuralı ihlali", ":43",
                kapsam="K5.sentez", onem=abs(skor), gozlemci_kodu="UYDURMA",
                kanallar=[
                    _kanal("ZIRVE.yon_skoru", "ZIRVE.yon_skoru", skor, True),
                    _kanal("K5.sentez.yon_skoru", "K5.sentez.yon_skoru",
                           al(ctx, "K5.sentez.yon_skoru"),
                           None if _num(al(ctx, "K5.sentez.yon_skoru")) is None
                           else ("LONG" if _num(al(ctx, "K5.sentez.yon_skoru")) > 0
                                 else "SHORT" if _num(al(ctx, "K5.sentez.yon_skoru")) < 0
                                 else "NÖTR") != yb),
                    _kanal("K5.sentez.YON_BIAS", "K5.sentez.YON_BIAS",
                           al(ctx, "K5.sentez.YON_BIAS"),
                           None if al(ctx, "K5.sentez.YON_BIAS") is None
                           else str(al(ctx, "K5.sentez.YON_BIAS")).upper() != beklenen),
                ]))

    # I5 — sentezdeki danışman K3'te yok (:42 çözümsüz atıf)
    k3_adlar = {str(d.get("name")) for d in (al(ctx, "K3.danismanlar") or [])}
    k2_adlar = set((al(ctx, "K2.motor_sonuclari") or {}).keys())
    k4_adlar = set((al(ctx, "K4.verifier") or {}).keys())
    for d in (al(ctx, "K5.sentez.danisman_ozeti") or []):
        ad = str(d.get("ad"))
        if k3_adlar and ad not in k3_adlar:
            b.append(_bulgu(
                "KAYNAKSIZ_DANISMAN", "hata_2", "hata",
                f"Sentezdeki danışman {ad!r} K3.danismanlar içinde yok",
                "bug — çözümsüz atıf (kaynağı olmayan danışman)", ":42",
                kapsam="K5.sentez", onem=1.0, gozlemci_kodu="UYDURMA",
                kanallar=[
                    _kanal("K3.danismanlar", "K3.danismanlar",
                           sorted(k3_adlar), ad not in k3_adlar),
                    _kanal("K2.motor_sonuclari", "K2.motor_sonuclari",
                           sorted(k2_adlar),
                           None if not k2_adlar else ad not in k2_adlar),
                    _kanal("K4.verifier", "K4.verifier", sorted(k4_adlar),
                           None if not k4_adlar else ad not in k4_adlar),
                ]))
    return b


# ---------------------------------------------------------------------------
# İNCELEYİCİ 1 — sozlesme_1 (orta ← sonnet, :32) — kapsam: EMİR artefaktı
#   ":33 you should only consider CLAUDE.md files that share a file path with
#        the file or parents"  → kural yalnız kendi kapsamına uygulanır.
# ---------------------------------------------------------------------------
def inceleyici_sozlesme_1(ctx: dict) -> list:
    b = []
    z = ctx.get("ZIRVE") or {}
    emir = str(z.get("EMIR", YOK))
    adaylar = z.get("emir_adaylari") or []
    red = z.get("emir_red_nedenleri") or []

    # S1 — "EMİR YOK" ama düşen kapı yazılmamış (:44)
    if emir.startswith("EMİR YOK") and not red and not str(
            z.get("EMIR_GEREKCE", "")).strip():
        b.append(_bulgu(
            "EMIR_YOK_GEREKCESIZ", "sozlesme_1", "sozlesme",
            "EMİR YOK basılmış ama düşen kapı/gerekçe listesi boş",
            "CLAUDE.md adherence — emir çıktısı sözleşmesi", ":44",
            kapsam="ZIRVE.EMIR", onem=1.0,
            alinti="Hiçbir aday geçemezse \"EMİR YOK\" + düşen kapı yazılır — "
                   "boş bırakılmaz.",
            kanallar=[
                _kanal("red_nedenleri", "ZIRVE.emir_red_nedenleri", red, not red),
                _kanal("EMIR_GEREKCE", "ZIRVE.EMIR_GEREKCE",
                       z.get("EMIR_GEREKCE"),
                       not str(z.get("EMIR_GEREKCE", "")).strip()),
                _kanal("emir_plani.red", "K5.emir_plani.red_nedenleri",
                       al(ctx, "K5.emir_plani.red_nedenleri"),
                       None if al(ctx, "K5.emir_plani.red_nedenleri") is None
                       else not al(ctx, "K5.emir_plani.red_nedenleri")),
            ]))

    # S2 — R taşıyan aday rr_denetim'den geçmemiş (:44)
    for i, a in enumerate(adaylar):
        if _num(a.get("R")) is not None and not str(a.get("rr_denetim", "")).strip():
            b.append(_bulgu(
                "R_DENETIMSIZ", "sozlesme_1", "sozlesme",
                f"Aday {i} R taşıyor ama rr_denetim alanı yok",
                "CLAUDE.md adherence — şişirilmiş R yasağı", ":44",
                kapsam="ZIRVE.emir_adaylari", onem=1.0,
                alinti="**Şişirilmiş R YASAK:** stop/hedef içeren, motorun "
                       "tek-kaynaklı çıktısı olmayan her R "
                       "`karar-kurulu/scripts/rr_denetim.py`'den geçer "
                       "(ATR-tutarsız = R_gercekci).",
                kanallar=[
                    _kanal("aday", f"ZIRVE.emir_adaylari.{i}.rr_denetim",
                           a.get("rr_denetim"), True),
                    _kanal("emir_plani", f"K5.emir_plani.adaylar.{i}.rr_denetim",
                           al(ctx, f"K5.emir_plani.adaylar.{i}.rr_denetim"),
                           None if al(ctx, f"K5.emir_plani.adaylar.{i}.rr_denetim")
                           is None else
                           not str(al(ctx,
                                      f"K5.emir_plani.adaylar.{i}.rr_denetim")).strip()),
                    _kanal("K4.rr_denetimi", "K4.rr_denetimi",
                           al(ctx, "K4.rr_denetimi"),
                           None if al(ctx, "K4.rr_denetimi") is None
                           else not al(ctx, "K4.rr_denetimi")),
                ]))

    # --- Bayraklanmayacak sınıflar (kaynak :46-50) — üretilir ki ELENDİĞİ görünsün
    for i, a in enumerate(adaylar):
        if a.get("tuzak_uyarisi"):
            b.append(_bulgu(
                "STOP_AVI_RISKI", "sozlesme_1", "kosullu",
                f"Aday {i}: {str(a['tuzak_uyarisi'])[:70]}",
                "potential issue — fiyat/likidite durumuna bağlı", ":43",
                kapsam="ZIRVE.emir_adaylari", onem=0.5,
                kanallar=[_kanal("aday", f"ZIRVE.emir_adaylari.{i}.tuzak_uyarisi",
                                 a["tuzak_uyarisi"], True)]))
        g = str(a.get("giris_gerekcesi", ""))
        if g and len(g) < 12:
            b.append(_bulgu(
                "GEREKCE_KISA", "sozlesme_1", "bicim",
                f"Aday {i} giriş gerekçesi çok kısa ({len(g)} karakter)",
                "style — anlatım kalitesi", ":44",
                kapsam="ZIRVE.emir_adaylari", onem=0.1,
                kanallar=[_kanal("aday", f"ZIRVE.emir_adaylari.{i}.giris_gerekcesi",
                                 g, True)]))
    return b


# ---------------------------------------------------------------------------
# İNCELEYİCİ 2 — sozlesme_2 (orta ← sonnet, :32) — kapsam: ÇIKTI sözleşmesi
# ---------------------------------------------------------------------------
def inceleyici_sozlesme_2(ctx: dict) -> list:
    b = []
    z = ctx.get("ZIRVE") or {}

    # S3 — iki satır sözleşmesi (:44)
    iki = z.get("iki_satir")
    if not iki or not str((iki or {}).get("1_YON", "")).strip() \
            or not str((iki or {}).get("2_ISLEM_KALITESI", "")).strip():
        b.append(_bulgu(
            "IKI_SATIR_EKSIK", "sozlesme_2", "sozlesme",
            "YÖN / İŞLEM KALİTESİ iki-satır çıktısı eksik",
            "CLAUDE.md adherence — yön zorunlu kuralı", ":44",
            kapsam="ZIRVE.iki_satir", onem=1.0,
            alinti="Bir piyasa analizi/karar çıktısı **DAİMA iki ayrı satırla** "
                   "verilir; yön asla \"BEKLE\" ardında saklanmaz",
            kanallar=[
                _kanal("iki_satir", "ZIRVE.iki_satir", iki, not iki),
                _kanal("YON_BIAS", "ZIRVE.YON_BIAS", z.get("YON_BIAS"),
                       str(z.get("YON_BIAS", YOK)) == YOK),
                _kanal("ISLEM_KALITESI", "ZIRVE.ISLEM_KALITESI",
                       z.get("ISLEM_KALITESI"),
                       str(z.get("ISLEM_KALITESI", YOK)) == YOK),
            ]))

    # S4 — eşik kaynağı etiketsiz (:44)
    vars_ = ctx.get("varsayimlar")
    e_kaynak = al(ctx, "K5.sentez.esik_kaynagi")
    kal_kaynak = al(ctx, "K5.esik_kalibrasyonu.kaynak")
    if not vars_ and not e_kaynak and not kal_kaynak:
        b.append(_bulgu(
            "ESIK_ETIKETSIZ", "sozlesme_2", "sozlesme",
            "Kararda eşik/varsayım etiketi yok (gizli eşik)",
            "CLAUDE.md adherence — eşik politikası", ":44",
            kapsam="rapor.varsayimlar", onem=1.0,
            alinti="Kalibre edilemeyen her sabit çıktıda "
                   "`varsayimlar`/`esik_kaynagi` ile açıkça etiketlenir — "
                   "etiketsiz gizli eşik yasak.",
            kanallar=[
                _kanal("varsayimlar", "varsayimlar", vars_, not vars_),
                _kanal("sentez.esik_kaynagi", "K5.sentez.esik_kaynagi",
                       e_kaynak, not e_kaynak),
                _kanal("esik_kalibrasyonu", "K5.esik_kalibrasyonu.kaynak",
                       kal_kaynak, not kal_kaynak),
            ]))

    # S5 — önceki kayıt var ama kıyas/akıbet atlanmış (:44)
    onceki_var = bool(al(ctx, "K1.onceki_kayit_var"))
    kiyas = ctx.get("KIYAS")
    akibet = z.get("ONCEKI_AKIBET") or al(ctx, "K1.onceki_karar_akibeti")
    if onceki_var and (not kiyas or not akibet):
        b.append(_bulgu(
            "KIYAS_ATLANDI", "sozlesme_2", "sozlesme",
            "Önceki koşu kaydı var ama HESAP VERME / KIYAS üretilmemiş",
            "CLAUDE.md adherence — hesap verme + kıyas kuralı", ":44",
            kapsam="rapor.KIYAS", onem=1.0, gozlemci_kodu="EKSIK_AKTARIM",
            alinti="Ek kural (HESAP VERME + KIYAS — her yeni veride İLK İŞ, "
                   "atlanamaz)",
            kanallar=[
                _kanal("KIYAS", "KIYAS", bool(kiyas), not kiyas),
                _kanal("ONCEKI_AKIBET", "ZIRVE.ONCEKI_AKIBET", bool(akibet),
                       not akibet),
                _kanal("K1.onceki_kayit_var", "K1.onceki_kayit_var",
                       onceki_var, onceki_var),
            ]))

    # S6 — karar-destek uyarısı düşmüş (:44)
    metinler = [str(ctx.get("not", "")), str(al(ctx, "K5.sentez.not") or ""),
                str(al(ctx, "K5.emir_plani.not") or "")]
    bulundu = ["DAHİL DEĞİL" in m for m in metinler]
    if not any(bulundu):
        b.append(_bulgu(
            "CANLI_EMIR_UYARISI_YOK", "sozlesme_2", "sozlesme",
            "Çıktıda 'canlı/otomatik emir DAHİL DEĞİL' uyarısı yok",
            "CLAUDE.md adherence — kapsam uyarısı", ":44",
            kapsam="rapor.not", onem=1.0,
            alinti="⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.",
            kanallar=[
                _kanal("rapor.not", "not", metinler[0][:40], not bulundu[0]),
                _kanal("sentez.not", "K5.sentez.not", metinler[1][:40],
                       None if al(ctx, "K5.sentez.not") is None else not bulundu[1]),
                _kanal("emir_plani.not", "K5.emir_plani.not", metinler[2][:40],
                       None if al(ctx, "K5.emir_plani.not") is None
                       else not bulundu[2]),
            ]))

    # --- yanlış-pozitif tuzakları: üretilir ki ELENDİĞİ görünsün
    d = ctx.get("DENETIM") or {}
    for x in (d.get("uyari") or []) + (d.get("ihlal") or []):
        if "TUNEL" in str(x):
            b.append(_bulgu(
                "TUNEL_TEK_AILE", "sozlesme_2", "sozlesme",
                f"Gözlemci tünel uyarısı: {str(x)[:70]}",
                "CLAUDE.md adherence — tünel görüşü", ":44",
                kapsam="DENETIM", onem=0.6, gozlemci_kodu="TUNEL",
                alinti="TÜNEL (karar tek kanıt ailesine dayanıyor)",
                kanallar=[_kanal("DENETIM", "DENETIM.uyari", str(x)[:60], True)]))
            break
    for x in (z.get("emir_red_nedenleri") or []):
        if "ŞİŞİRİLMİŞ" in str(x):
            b.append(_bulgu(
                "SISIRILMIS_R_ADAYI", "sozlesme_2", "sozlesme",
                f"Şişirilmiş R'li aday üretilmiş: {str(x)[:70]}",
                "CLAUDE.md adherence — şişirilmiş R", ":44",
                kapsam="ZIRVE.emir_red_nedenleri", onem=0.7,
                susturma_izi=str(x),
                alinti="**Şişirilmiş R YASAK:**",
                kanallar=[_kanal("red_nedenleri", "ZIRVE.emir_red_nedenleri",
                                 str(x)[:60], True)]))
            break
    kapsam_t = al(ctx, "K2.motor_sonuclari.turev-akis.rapor.kapsam")
    if _num(kapsam_t) is not None and _num(kapsam_t) < 1.0:
        b.append(_bulgu(
            "TUREV_KAPSAMI_DUSUK", "sozlesme_2", "genel",
            f"Türev kapsamı {kapsam_t} < 1.00 — veri kalitesi genel endişesi",
            "general quality concern", ":44",
            kapsam="K2.motor_sonuclari", onem=0.3,
            kanallar=[_kanal("turev", "K2.motor_sonuclari.turev-akis.rapor.kapsam",
                             kapsam_t, True)]))
    return b


INCELEYICILER = (
    ("sozlesme_1", "orta", "code-review.md:32", inceleyici_sozlesme_1),
    ("sozlesme_2", "orta", "code-review.md:32", inceleyici_sozlesme_2),
    ("hata_1", "pahali", "code-review.md:35", inceleyici_hata_1),
    ("hata_2", "pahali", "code-review.md:38", inceleyici_hata_2),
)


def topla(rapor: dict) -> list:
    """ADIM 4 — dört inceleyici (code-review.md:30). Paralel DEĞİL, ardışık:
    kontroller birbirinden bağımsız olduğu için sonuç aynıdır (bkz. KANIT.md)."""
    ctx = baglam(rapor)
    hepsi = []
    for _ad, _sinif, _kaynak, fn in INCELEYICILER:
        hepsi.extend(fn(ctx))
    return hepsi


# ---------------------------------------------------------------------------
# HIGH SIGNAL kapısı (code-review.md:41-51)
# ---------------------------------------------------------------------------
def yuksek_sinyal(b: dict) -> tuple:
    if b["sinif"] in BAYRAKSIZ_SINIF:
        return False, BAYRAKSIZ_SINIF[b["sinif"]]
    if b.get("yuksek_sinyal_kural") not in YUKSEK_SINYAL:
        return False, ":41 CRITICAL: We only want HIGH SIGNAL issues — ölçüt yok"
    if b["sinif"] == "sozlesme" and not str(b.get("kural_alintisi", "")).strip():
        return False, (":44 Clear, unambiguous CLAUDE.md violations where you can "
                       "quote the exact rule being broken — alıntı yok")
    if not b.get("kesin"):
        return False, (":51 If you are not certain an issue is real, do not flag it")
    return True, YUKSEK_SINYAL[b["yuksek_sinyal_kural"]]


# ---------------------------------------------------------------------------
# Yanlış-pozitif listesi (code-review.md:79-86)
# ---------------------------------------------------------------------------
def yanlis_pozitif(b: dict, rapor: dict, onceki_kodlar: set) -> tuple:
    z = rapor.get("ZIRVE") or {}
    d = rapor.get("DENETIM") or {}

    if b["kod"] in onceki_kodlar:                                     # :81
        return True, ":81"
    if b.get("yeniden_hesap_uyustu"):                                 # :82
        return True, ":82"
    esik = ONEM_ESIGI_R if "R_" in b["kod"] else ONEM_ESIGI_FIYAT     # :83
    if b.get("onem", 1.0) < esik:
        return True, ":83"
    gk = b.get("gozlemci_kodu")                                       # :84
    if gk:
        # "do not run the linter to verify" → gözlemci YENİDEN KOŞTURULMAZ,
        # raporun kendi DENETIM alanı okunur.
        for x in (d.get("ihlal") or []) + (d.get("uyari") or []):
            if gk in str(x):
                return True, ":84"
    if b["sinif"] == "genel":                                         # :85
        return True, ":85"
    iz = str(b.get("susturma_izi", ""))                               # :86
    if iz:
        susturma = [str(x) for x in (z.get("emir_red_nedenleri") or [])]
        susturma += [str(x) for x in (rapor.get("varsayimlar") or [])]
        if any(iz in s or s in iz for s in susturma):
            return True, ":86"
    return False, ""


# ---------------------------------------------------------------------------
# ADIM 5 — bulgu başına BAĞIMSIZ doğrulama (çoklu-oy, verify/SKILL.md)
# ---------------------------------------------------------------------------
def dogrula(b: dict, oy: int = 3) -> dict:
    """Her oy AYRI bir rapor alanından okunur. Kanıtı açılamayan oy KANIT_YOK'tur
    ve ALEYHE sayılır (fail-closed). Aynı yol iki kez oy kullanamaz (ÇARPIŞMA)."""
    gorulen, kanallar = set(), []
    for k in b.get("oy_kanallari") or []:
        if k["yol"] in gorulen:
            continue                       # kopya kanal = bağımsız oy DEĞİL
        gorulen.add(k["yol"])
        kanallar.append(k)

    istenen = max(1, int(oy))
    kullanilan = kanallar[:istenen]        # oy sayısı kanal sayısını AŞAMAZ
    oylar = []
    for i, k in enumerate(kullanilan, 1):
        hukum = ("KANIT_YOK" if k["sorunlu"] is None
                 else ("EVET" if k["sorunlu"] else "HAYIR"))
        oylar.append({"oy_no": i, "kanal": k["kanal"], "yol": k["yol"],
                      "okunan": k["deger"], "hukum": hukum})

    evet = sum(1 for o in oylar if o["hukum"] == "EVET")
    hayir = sum(1 for o in oylar if o["hukum"] == "HAYIR")
    yok = sum(1 for o in oylar if o["hukum"] == "KANIT_YOK")
    n = len(oylar)

    if n < 2:
        gecti, gerekce = False, ("tek kanallı doğrulama — bağımsız ikinci kanal "
                                 "yok (dairesel doğrulama korkuluğu)")
    elif evet > n / 2:
        gecti, gerekce = True, f"çoğunluk: {evet}/{n} EVET"
    else:
        gecti, gerekce = False, (f"çoğunluk YOK: {evet} evet / {hayir} hayır / "
                                 f"{yok} kanıt yok (beraberlik = RED, fail-closed)")

    return {
        "dogrulandi": gecti, "gerekce": gerekce,
        "istenen_oy": istenen, "kullanilan_oy": n,
        "mevcut_kanal": len(kanallar),
        "oylar": oylar,
        "kural": "çoğunluk (evet > n/2); KANIT_YOK aleyhe; n<2 → RED",
        "uyari": ("istenen oy sayısı mevcut bağımsız kanalı aşıyor — eksik oy "
                  "UYDURULMADI" if istenen > len(kanallar) else ""),
    }


# ---------------------------------------------------------------------------
# boru hattı
# ---------------------------------------------------------------------------
def calistir(rapor: dict, onceki: dict | None = None, oy: int = 3) -> dict:
    adaylar = topla(rapor)                                      # adım 4
    onceki_kodlar = {x["kod"] for x in topla(onceki)} if onceki else set()

    dogrulanan, elenen = [], []
    for b in adaylar:
        ok, gerekce = yuksek_sinyal(b)
        if not ok:
            elenen.append({**b, "eleme_asamasi": "HIGH_SIGNAL",
                           "eleme_gerekcesi": gerekce})
            continue
        fp, kural = yanlis_pozitif(b, rapor, onceki_kodlar)
        if fp:
            elenen.append({**b, "eleme_asamasi": "YANLIS_POZITIF",
                           "eleme_gerekcesi": f"{kural} {YANLIS_POZITIF[kural]}"})
            continue
        kayit = dogrula(b, oy)                                  # adım 5
        if kayit["dogrulandi"]:
            dogrulanan.append({**b, "dogrulama": kayit})
        else:                                                   # adım 6
            elenen.append({**b, "eleme_asamasi": "DOGRULANMADI",
                           "eleme_gerekcesi": kayit["gerekce"],
                           "dogrulama": kayit})

    return {
        "KARAR": "BULGU VAR" if dogrulanan else "BULGU YOK",
        "aday_sayisi": len(adaylar),
        "dogrulanan": dogrulanan,
        "elenen": elenen,
        "oy_kurali": f"--oy {oy}; çoğunluk (evet > n/2); KANIT_YOK aleyhe; n<2 RED",
        "inceleyiciler": [{"ad": a, "maliyet_sinifi": s, "kaynak": k}
                          for a, s, k, _ in INCELEYICILER],
        # code-review.md:61 — "No issues found. Checked for bugs and CLAUDE.md
        # compliance." satırının bu depodaki karşılığı:
        "ozet_satiri": (
            "Bulgu yok. Emir/yön tutarlılığı ve CLAUDE.md sözleşmesi denetlendi."
            if not dogrulanan
            else f"{len(dogrulanan)} doğrulanmış bulgu "
                 f"({len(elenen)} aday elendi)."),
        "not": ("Yalnız karar-destek. Bu motor gerçek alt-ajan BAŞLATMAZ; "
                "doğrulama deterministik ve dosyadan okunur. "
                "Canlı/otomatik emir DAHİL DEĞİL."),
    }


def ozet_metin(s: dict, ayrinti: bool = False) -> str:
    L = ["=" * 68, "BULGU DOĞRULAYICI — bulgu başına bağımsız oy", "=" * 68]
    L.append(f"aday: {s['aday_sayisi']} | doğrulanan: {len(s['dogrulanan'])} | "
             f"elenen: {len(s['elenen'])}")
    L.append(f"oy kuralı: {s['oy_kurali']}")
    L.append("-" * 68)
    for b in s["dogrulanan"]:
        L.append(f"⛔ {b['kod']} [{b['inceleyici']} {b['yuksek_sinyal_kural']}] "
                 f"— {b['aciklama']}")
        L.append(f"   neden: {b['neden_bayraklandi']}")
        if b.get("kural_alintisi"):
            L.append(f"   kural: \"{b['kural_alintisi'][:96]}\"")
        L.append(f"   doğrulama: {b['dogrulama']['gerekce']}")
        for o in b["dogrulama"]["oylar"]:
            L.append(f"      oy{o['oy_no']} {o['hukum']:<10} {o['yol']} = "
                     f"{str(o['okunan'])[:40]}")
    if ayrinti:
        L.append("-" * 68)
        L.append("ELENEN ADAYLAR (code-review.md:57 — doğrulanmayan atılır):")
        for b in s["elenen"]:
            L.append(f"   ✖ {b['kod']:<24} {b['eleme_asamasi']:<16} "
                     f"{b['eleme_gerekcesi'][:60]}")
    L.append("-" * 68)
    L.append(s["ozet_satiri"])
    L.append("=" * 68)
    L.append("⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# ÖZ-TEST — vakalar KAYNAK kurallarına karşı koşar (kendi çıktımıza değil)
# ---------------------------------------------------------------------------
def _rapor(**ust) -> dict:
    """Gerçek alan adlarıyla asgari koşu raporu (son_rapor.json'dan alınmıştır)."""
    aday = {"emir_tipi": "LIMIT", "yon": "SHORT", "giris": 63990.7,
            "stop": 64234.1, "hedef": 63461.2, "R": 2.18,
            "rr_denetim": "TUTARLI",
            "giris_gerekcesi": "4H teyitli swing direnci"}
    r = {
        "sembol": "BTCUSDT",
        "durum": "TAMAM — piramidin tepesine ulaşıldı",
        "varsayimlar": ["eşikler bu koşudan kalibre edildi"],
        "not": "Yalnız karar-destek. Canlı/otomatik emir DAHİL DEĞİL.",
        "katmanlar": [
            {"katman": "K1-LLM", "gecti": True, "onceki_kayit_var": True,
             "onceki_karar_akibeti": {"durum": "ÖLÇÜLEMEDİ"}},
            {"katman": "K2-AI-AJAN", "gecti": True,
             "motor_sonuclari": {"karar-motoru": {}, "grafik-calisma": {},
                                 "turev-akis": {"rapor": {"kapsam": 0.75}}}},
            {"katman": "K3-COKLU-AJAN", "gecti": True,
             "danismanlar": [{"name": "karar-motoru", "stance": "flat"},
                             {"name": "grafik-calisma", "stance": "short"},
                             {"name": "turev-akis", "stance": "short"}]},
            {"katman": "K4-AGI", "gecti": True,
             "verifier": {"karar-motoru": {"confirmed": False}},
             "rr_denetimi": {}},
            {"katman": "K5-SI", "gecti": True,
             "sentez": {"KARAR": "NÖTR-BEKLE", "YON_BIAS": "SHORT",
                        "yon_skoru": -0.5712, "guven_skoru": 0.2039,
                        "esik_kaynagi": "VERİDEN TÜRETİLDİ",
                        "not": "Karar-destek çıktısıdır. Canlı emir DAHİL DEĞİL.",
                        "danisman_ozeti": [{"ad": "karar-motoru"},
                                           {"ad": "grafik-calisma"},
                                           {"ad": "turev-akis"}]},
             "esik_kalibrasyonu": {"kaynak": "VERİDEN TÜRETİLDİ"},
             "emir_plani": {"EMIR": "LIMIT SHORT @63990.7 | stop 64234.1 | "
                                    "T1 63461.2 | R 2.18",
                            "yon": "SHORT", "birincil": dict(aday),
                            "adaylar": [dict(aday)], "red_nedenleri": [],
                            "not": "Canlı emir DAHİL DEĞİL."}},
        ],
        "ZIRVE": {
            "YON_BIAS": "SHORT", "sentez_karari": "NÖTR-BEKLE",
            "ISLEM_KALITESI": "TEMİZ GİRİŞ YOK — TEPKİ/SEVİYE BEKLE",
            "yon_skoru": -0.5712, "guven_skoru": 0.2039,
            "kapi_gerekceleri": ["|skor|=0.57 < eşik 0.66"],
            "ZORUNLU_EKSIK": [],
            "EMIR": "LIMIT SHORT @63990.7 | stop 64234.1 | T1 63461.2 | R 2.18",
            "EMIR_GEREKCE": "", "emir_red_nedenleri": [],
            "emir_adaylari": [dict(aday)],
            "ONCEKI_AKIBET": {"durum": "ÖLÇÜLEMEDİ"},
            "iki_satir": {"1_YON": "YÖN (bias): SHORT",
                          "2_ISLEM_KALITESI": "İŞLEM KALİTESİ: …"},
        },
        "KIYAS": {"YON_DEGISIMI": {"etiket": "DEVAM"}},
        "DENETIM": {"ozet": "25 denetim, 0 ihlal, 2 uyarı", "muhurlendi": False,
                    "ihlal": [], "uyari": []},
    }
    for k, v in ust.items():
        if k in ("ZIRVE", "DENETIM"):
            r[k].update(v)
        elif k == "K5":
            [x for x in r["katmanlar"] if x["katman"] == "K5-SI"][0].update(v)
        else:
            r[k] = v
    return r


def _kodlar(sonuc, alan):
    return [b["kod"] for b in sonuc[alan]]


def _self_test() -> int:
    vakalar, gecen = [], 0
    print("BULGU DOĞRULAYICI — öz-test")

    def kos(ad, rapor, beklenen_karar, *, dogrulanan=(), elenen=(),
            onceki=None, oy=3, ek=None):
        s = calistir(rapor, onceki, oy)
        ok = s["KARAR"] == beklenen_karar
        for k in dogrulanan:
            ok = ok and k in _kodlar(s, "dogrulanan")
        for k in elenen:
            ok = ok and k in _kodlar(s, "elenen") and k not in _kodlar(s, "dogrulanan")
        if ek:
            ok = ok and ek(s)
        vakalar.append((ad, ok, s))
        print(f"[{'GECTI' if ok else 'KALDI'}] {ad}: {s['KARAR']} — "
              f"{s['ozet_satiri'][:66]}")
        return ok

    # 1) temiz koşu → bulgu yok (kaynağın :61 satırının karşılığı)
    gecen += kos("temiz-kosu", _rapor(), "BULGU YOK",
                 ek=lambda s: s["ozet_satiri"].startswith("Bulgu yok."))

    # 2) emir yönü ters (:43)
    r = _rapor(ZIRVE={"YON_BIAS": "LONG", "yon_skoru": 0.42})
    gecen += kos("emir-yonu-ters", r, "BULGU VAR", dogrulanan=("EMIR_YON_CELISKISI",))

    # 3) R aritmetiği tutarsız (:43)
    r = _rapor(ZIRVE={"EMIR": "LIMIT SHORT @63990.7 | stop 64234.1 | "
                              "T1 63461.2 | R 4.90"})
    r["ZIRVE"]["emir_adaylari"][0]["R"] = 4.90
    gecen += kos("R-aritmetigi-tutarsiz", r, "BULGU VAR",
                 dogrulanan=("R_ARITMETIK_TUTARSIZ",))

    # 4) mühürlü koşuda emir (:43) — piramit.py:1664
    gecen += kos("muhurlu-emir",
                 _rapor(DENETIM={"muhurlendi": True, "ihlal": ["K3 UYDURMA: x"]}),
                 "BULGU VAR", dogrulanan=("MUHURLU_EMIR",))

    # 5) biçim/koşullu adaylar bayraklanmaz (:47/:48)
    r = _rapor()
    r["ZIRVE"]["emir_adaylari"][0]["tuzak_uyarisi"] = "STOP-AV RİSKİ: …"
    r["ZIRVE"]["emir_adaylari"][0]["giris_gerekcesi"] = "kısa"
    gecen += kos("bayraksiz-sinif", r, "BULGU YOK",
                 elenen=("STOP_AVI_RISKI", "GEREKCE_KISA"),
                 ek=lambda s: all(
                     any(b["kod"] == k and b["eleme_asamasi"] == "HIGH_SIGNAL"
                         for b in s["elenen"])
                     for k in ("STOP_AVI_RISKI", "GEREKCE_KISA")))

    # 6) alıntısız sözleşme bulgusu elenir (:44)
    sahte = _bulgu("ALINTISIZ_KURAL", "sozlesme_2", "sozlesme", "x",
                   "CLAUDE.md adherence", ":44", alinti="")
    ok6 = yuksek_sinyal(sahte)[0] is False and "quote the exact rule" in \
        yuksek_sinyal(sahte)[1]
    vakalar.append(("alintisiz-kural-elenir", ok6, None))
    gecen += ok6
    print(f"[{'GECTI' if ok6 else 'KALDI'}] alintisiz-kural-elenir: "
          f"{yuksek_sinyal(sahte)[1][:60]}")

    # 7) önceden var olan bulgu elenir (:81)
    r = _rapor(ZIRVE={"YON_BIAS": "LONG", "yon_skoru": 0.42})
    gecen += kos("onceden-var-elenir", r, "BULGU YOK", onceki=r,
                 elenen=("EMIR_YON_CELISKISI",),
                 ek=lambda s: any(b["kod"] == "EMIR_YON_CELISKISI"
                                  and b["eleme_gerekcesi"].startswith(":81")
                                  for b in s["elenen"]))

    # 8) gözlemcinin zaten yakaladığı bulgu elenir (:84)
    r = _rapor(DENETIM={"uyari": ["K4 TUNEL: tek aile"]})
    gecen += kos("gozlemci-yakalamis-elenir", r, "BULGU YOK",
                 elenen=("TUNEL_TEK_AILE",),
                 ek=lambda s: any(b["kod"] == "TUNEL_TEK_AILE"
                                  and b["eleme_gerekcesi"].startswith(":84")
                                  for b in s["elenen"]))

    # 9) gerekçeyle susturulmuş bulgu elenir (:86)
    r = _rapor(ZIRVE={"emir_red_nedenleri":
                      ["giriş 63511.1: rr_denetim ŞİŞİRİLMİŞ (R 0.6) — reddedildi"]})
    gecen += kos("susturulmus-elenir", r, "BULGU YOK",
                 elenen=("SISIRILMIS_R_ADAYI",),
                 ek=lambda s: any(b["kod"] == "SISIRILMIS_R_ADAYI"
                                  and b["eleme_gerekcesi"].startswith(":86")
                                  for b in s["elenen"]))

    # 10) genel kalite endişesi elenir (:85)
    gecen += kos("genel-endise-elenir", _rapor(), "BULGU YOK",
                 elenen=("TUREV_KAPSAMI_DUSUK",),
                 ek=lambda s: any(b["kod"] == "TUREV_KAPSAMI_DUSUK"
                                  and b["eleme_gerekcesi"].startswith(":85")
                                  for b in s["elenen"]))

    # 11) çoğunluk kuralı: 1 evet / 2 hayır → RED; KANIT_YOK aleyhe
    b_az = _bulgu("TEST_COGUNLUK", "hata_1", "hata", "x", "bug", ":43",
                  kanallar=[_kanal("a", "A", 1, True), _kanal("b", "B", 2, False),
                            _kanal("c", "C", 3, False)])
    b_yok = _bulgu("TEST_KANITSIZ", "hata_1", "hata", "x", "bug", ":43",
                   kanallar=[_kanal("a", "A", 1, True), _kanal("b", "B", None, None)])
    b_tek = _bulgu("TEST_TEK_KANAL", "hata_1", "hata", "x", "bug", ":43",
                   kanallar=[_kanal("a", "A", 1, True)])
    d1, d2, d3 = dogrula(b_az, 3), dogrula(b_yok, 3), dogrula(b_tek, 3)
    ok11 = (not d1["dogrulandi"]) and (not d2["dogrulandi"]) and \
        (not d3["dogrulandi"]) and "tek kanallı" in d3["gerekce"]
    vakalar.append(("cogunluk-kurali", ok11, None))
    gecen += ok11
    print(f"[{'GECTI' if ok11 else 'KALDI'}] cogunluk-kurali: 1/3 evet→RED, "
          f"KANIT_YOK aleyhe→RED, tek kanal→RED")

    # 12) oy sayısı mevcut kanalı AŞAMAZ (uydurma oy yok)
    b_iki = _bulgu("TEST_OY_TAVANI", "hata_1", "hata", "x", "bug", ":43",
                   kanallar=[_kanal("a", "A", 1, True), _kanal("b", "B", 2, True),
                             _kanal("a-kopya", "A", 1, True)])
    d4 = dogrula(b_iki, 9)
    ok12 = (d4["kullanilan_oy"] == 2 and d4["mevcut_kanal"] == 2
            and d4["istenen_oy"] == 9 and d4["uyari"] and d4["dogrulandi"])
    vakalar.append(("oy-tavani", ok12, None))
    gecen += ok12
    print(f"[{'GECTI' if ok12 else 'KALDI'}] oy-tavani: istenen 9 → kullanılan "
          f"{d4['kullanilan_oy']} (kopya kanal sayılmadı)")

    # 13) yeniden hesap mutabık → :82 ile elenir
    #     Basılan/özet seviyeler YUVARLANMIŞ (63990.0), motor kaydı tam (63990.7):
    #     yuvarlanmış sayılarla R tutmaz ama motor kaydıyla tutar → gerçek hata DEĞİL.
    r = _rapor()
    r["ZIRVE"]["EMIR"] = "LIMIT SHORT @63990.0 | stop 64234.1 | T1 63461.2 | R 2.18"
    r["ZIRVE"]["emir_adaylari"][0]["giris"] = 63990.0
    gecen += kos("yeniden-hesap-mutabik", r, "BULGU YOK",
                 ek=lambda s: any(b["kod"] == "R_ARITMETIK_TUTARSIZ"
                                  and b["eleme_gerekcesi"].startswith(":82")
                                  for b in s["elenen"]))

    # 14) çözümsüz atıf: sentezde K3'te olmayan danışman (:42)
    r = _rapor()
    k5 = [x for x in r["katmanlar"] if x["katman"] == "K5-SI"][0]
    k5["sentez"]["danisman_ozeti"].append({"ad": "hayalet-danisman"})
    gecen += kos("kaynaksiz-danisman", r, "BULGU VAR",
                 dogrulanan=("KAYNAKSIZ_DANISMAN",))

    toplam = len(vakalar)
    print(f"\n{gecen}/{toplam} vaka geçti "
          f"{'(HEPSİ TAMAM)' if gecen == toplam else '(EKSİK)'}")
    return 0 if gecen == toplam else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Bulgu doğrulayıcı — bulgu başına bağımsız oy; "
                    "doğrulanmayan elenir")
    ap.add_argument("--rapor", help="piramit koşu raporu (son_rapor.json)")
    ap.add_argument("--onceki", help="önceki koşu raporu (:81 pre-existing için)")
    ap.add_argument("--oy", type=int, default=3, help="bulgu başına oy sayısı")
    ap.add_argument("--ozet", action="store_true", help="metin özeti bas")
    ap.add_argument("--ayrinti", action="store_true", help="elenen adayları da bas")
    ap.add_argument("--self-test", action="store_true", help="öz-test koş")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.rapor:
        ap.error("--rapor ya da --self-test gerekli")

    try:
        rapor = json.loads(Path(args.rapor).expanduser().resolve()
                           .read_text(encoding="utf-8"))
        onceki = (json.loads(Path(args.onceki).expanduser().resolve()
                             .read_text(encoding="utf-8")) if args.onceki else None)
    except (OSError, json.JSONDecodeError) as e:
        print(f"RAPOR OKUNAMADI: {e}", file=sys.stderr)
        return 2

    s = calistir(rapor, onceki, args.oy)
    print(ozet_metin(s, args.ayrinti) if args.ozet
          else json.dumps(s, ensure_ascii=False, indent=2))
    return 1 if s["dogrulanan"] else 0


if __name__ == "__main__":
    sys.exit(main())
