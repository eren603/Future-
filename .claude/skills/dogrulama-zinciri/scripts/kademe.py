#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MALİYET KADEMESİ — pahalı doğrulamadan ÖNCE ucuz ön eleme kapıları.

Kaynak: `cc/plugins/code-review/commands/code-review.md` (109 satır).
Kaynağın adım 1'i incelemeye BAŞLAMADAN önce dört ucuz soru sorar
(code-review.md:14-20, BİREBİR):

    "1. Launch a haiku agent to check if any of the following are true:
       - The pull request is closed
       - The pull request is a draft
       - The pull request does not need code review (e.g. automated PR, trivial
         change that is obviously correct)
       - Claude has already commented on this PR ...
       If any condition is true, stop and do not proceed."

Bu depoda "inceleme konusu" bir PR değil, bir **piramit koşusunun kararıdır**
(`piramit-sistem/state/son_rapor.json` → `ZIRVE`). Dört soru şuna çevrilir:

  kapali        → koşu bir katman kapısında DURDU (`durum` = "DURDU — …");
                  değerlendirilecek karar yok.
  taslak        → `ZIRVE.ZORUNLU_EKSIK` dolu; karar zorunlu girdi olmadan
                  üretilmiş, TASLAK sayılır (CLAUDE.md: eksikle karar UYDURULMAZ).
  onemsiz       → YÖN nötr/VERİ YOK **ve** emir yok; doğrulanacak sayısal iddia
                  yok ("trivial change that is obviously correct").
  zaten_yapildi → bu koşunun parmak izi değerlendirme defterinde var
                  ("Claude has already commented on this PR").
  veri_ayni     → son bar defterdeki son kayıttan yeni değil (depo kuralı:
                  kanca yalnız veri DEĞİŞMİŞSE koşar).

MUAFİYET — kaynak, ön elemeye tek bir istisna koyar (code-review.md:22, BİREBİR):

    "Note: Still review Claude generated PR's."

Bizdeki karşılığı: **gözlemci mührü** (`DENETIM.muhurlendi`). Mühürlü koşuda
`piramit.py:1664` EMİR'i kapatır; bu koşu "önemsiz" görünür ama tam da
denetlenmesi gereken koşudur. Mühür varsa `onemsiz` kapısı UYGULANMAZ.

MALİYET SINIFLARI — kaynak model kademelemesini burada maliyet sınıfı olarak
taşıyoruz (hangi adım hangi sınıfta, kaynak satırıyla):

  ucuz   ← haiku      : code-review.md:14 (ön eleme), :24 (CLAUDE.md yol toplama)
  orta   ← sonnet     : code-review.md:28 (özet), :32 (sözleşme uyumu ajanları)
  pahali ← opus       : code-review.md:35 ve :38 (hata ajanları), :55 (doğrulayıcı
                        alt-ajanlar: "Use Opus subagents for bugs and logic
                        issues, and sonnet agents for CLAUDE.md violations")

Bu motor YALNIZ ucuz + orta kademeyi koşar. Pahalı kademe ayrı motordur
(`bulgu_dogrula.py`) ve bu motor DEVAM demeden çağrılmaz — maliyet kademesinin
tek varlık sebebi budur.

DÜRÜSTLÜK NOTU: burada gerçek alt-ajan BAŞLATILMAZ. Bu bir Python motorudur;
"haiku/sonnet/opus ajanı" kaynaktaki adımın maliyet sınıfına ve deterministik
karşılığına çevrilmiştir. Bkz. KANIT.md → SAPMALAR.

Kullanım:
  python3 kademe.py --rapor <son_rapor.json> [--defter d.jsonl] [--kok /repo]
                    [--ozet] [--kaydet]
  python3 kademe.py --self-test

Çıkış kodu: 0 = DEVAM (pahalı kademeye geçilebilir), 1 = DUR (elendi),
            2 = kullanım/okuma hatası.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

YOK = "VERİ YOK"

# Maliyet sınıfı → sıra numarası (ucuz önce koşmalı; öz-test bunu sınar)
MALIYET_SIRA = {"ucuz": 1, "orta": 2, "pahali": 3}

# Motor adı → beceri dizini (K2 `motor_sonuclari` anahtarlarından; uydurma yok —
# adlar son_rapor.json'daki gerçek anahtarlardır)
MOTOR_DIZIN = {
    "karar-motoru": "karar-motoru",
    "smc_tespit": "grafik-calisma",
    "smc_tespit_h4": "grafik-calisma",
    "grafik-calisma": "grafik-calisma",
    "setup_dogrulama": "grafik-calisma",
    "korelasyon": "piramit-sistem",
    "turev-akis": "turev-akis",
    "backtest-motoru": "backtest-motoru",
    "risk-yonetimi": "risk-yonetimi",
    "portfoy-optimizasyonu": "portfoy-optimizasyonu",
}

# Boru hattının kendisi — her koşuda kapsamdadır
SABIT_DIZIN = ("piramit-sistem", "karar-kurulu")

NOTR = {"NÖTR", "NOTR", "NEUTRAL", YOK, "", "None"}


class KademeError(Exception):
    pass


# ---------------------------------------------------------------------------
# yardımcılar
# ---------------------------------------------------------------------------
def _k1(rapor: dict) -> dict:
    for k in rapor.get("katmanlar") or []:
        if str(k.get("katman", "")).startswith("K1"):
            return k
    return {}


def _k2(rapor: dict) -> dict:
    for k in rapor.get("katmanlar") or []:
        if str(k.get("katman", "")).startswith("K2"):
            return k
    return {}


def son_bar_ms(rapor: dict):
    """Koşunun son 15M barı — 'veri değişti mi' sorusunun tek ölçülebilir yanıtı."""
    o = (_k1(rapor).get("olcumler") or {})
    for alan in ("m15_son_bar", "h4_son_bar"):
        v = o.get(alan)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return int(v)
    return None


def parmak_izi(rapor: dict) -> str:
    """Koşunun kimliği — 'bu koşu zaten değerlendirildi mi' sorusu için.

    Yalnız KARARI belirleyen alanlar girer; rapor metni değişince kimlik
    değişmesin (aksi halde aynı karar iki kez pahalı doğrulamaya girerdi).
    """
    z = rapor.get("ZIRVE") or {}
    cekirdek = {
        "sembol": rapor.get("sembol", YOK),
        "son_bar_ms": son_bar_ms(rapor),
        "YON_BIAS": z.get("YON_BIAS", YOK),
        "EMIR": z.get("EMIR", YOK),
        "sentez_karari": z.get("sentez_karari", YOK),
    }
    ham = json.dumps(cekirdek, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(ham.encode("utf-8")).hexdigest()[:16]


def _defter_oku(yol) -> list:
    if not yol:
        return []
    p = Path(yol)
    if not p.is_file():
        return []
    kayitlar = []
    for satir in p.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            kayitlar.append(json.loads(satir))
        except json.JSONDecodeError:
            continue  # bozuk satır kayıt sayılmaz (fail-closed değil: eksik kayıt = yeni koşu)
    return kayitlar


def _kapi(ad, sinif, kaynak, hukum, kanit, oneri=""):
    return {"ad": ad, "maliyet_sinifi": sinif, "kaynak": kaynak,
            "hukum": hukum, "kanit": kanit, "oneri": oneri}


# ---------------------------------------------------------------------------
# ADIM 2 (ucuz) — code-review.md:24-27: CLAUDE.md YOLLARINI topla (içerik DEĞİL)
# ---------------------------------------------------------------------------
def sozlesme_yollari(rapor: dict, kok: Path) -> dict:
    """Kaynak: "return a list of file paths (not their contents) for all relevant
    CLAUDE.md files" (code-review.md:24). Kök CLAUDE.md + koşan motorların
    beceri dizinleri. İÇERİK OKUNMAZ — ucuz kademede dosya açmak pahalıdır.
    """
    motorlar = list((_k2(rapor).get("motor_sonuclari") or {}).keys())
    dizinler = []
    for m in motorlar:
        d = MOTOR_DIZIN.get(m)
        if d and d not in dizinler:
            dizinler.append(d)
    for d in SABIT_DIZIN:
        if d not in dizinler:
            dizinler.append(d)

    yollar, eksik = [], []
    kokmd = kok / "CLAUDE.md"
    (yollar if kokmd.is_file() else eksik).append(str(kokmd))
    for d in dizinler:
        p = kok / ".claude" / "skills" / d / "CLAUDE.md"
        if p.is_file():
            yollar.append(str(p))
        else:
            # Kaynak "if it exists" der (:25) — olmayan dosya ihlal değildir.
            eksik.append(str(p))
    return {"yollar": yollar, "bulunamayan": eksik,
            "kapsam_motorlari": motorlar,
            "_not": "yalnız YOL listesi; içerik OKUNMADI (code-review.md:24)"}


# ---------------------------------------------------------------------------
# ADIM 3 (orta) — code-review.md:28: koşunun özeti
# ---------------------------------------------------------------------------
def kosu_ozeti(rapor: dict) -> dict:
    """Kaynak: "Launch a sonnet agent to view the pull request and return a
    summary of the changes" (code-review.md:28). Bizde: koşunun ne dediği.
    Her alan rapordan OKUNUR; hiçbiri türetilmez.
    """
    z = rapor.get("ZIRVE") or {}
    d = rapor.get("DENETIM") or {}
    kiy = (rapor.get("KIYAS") or {}).get("YON_DEGISIMI") or {}
    return {
        "sembol": rapor.get("sembol", YOK),
        "durum": rapor.get("durum", YOK),
        "son_bar_ms": son_bar_ms(rapor),
        "katman_kapilari": [
            {"katman": k.get("katman"), "gecti": k.get("gecti")}
            for k in (rapor.get("katmanlar") or [])],
        "YON_BIAS": z.get("YON_BIAS", YOK),
        "ISLEM_KALITESI": z.get("ISLEM_KALITESI", YOK),
        "sentez_karari": z.get("sentez_karari", YOK),
        "yon_skoru": z.get("yon_skoru"),
        "guven_skoru": z.get("guven_skoru"),
        "EMIR": z.get("EMIR", YOK),
        "aday_sayisi": len(z.get("emir_adaylari") or []),
        "denetim_ozeti": d.get("ozet", YOK),
        "muhurlendi": bool(d.get("muhurlendi")),
        "kiyas_etiketi": kiy.get("etiket", YOK),
    }


# ---------------------------------------------------------------------------
# ADIM 1 (ucuz) — dört ön eleme kapısı + mühür muafiyeti
# ---------------------------------------------------------------------------
def on_eleme(rapor: dict, defter: list) -> tuple:
    kapilar, gerekce, muafiyet = [], [], []
    z = rapor.get("ZIRVE") or {}
    d = rapor.get("DENETIM") or {}
    muhurlu = bool(d.get("muhurlendi"))

    # --- kapali: "The pull request is closed" (code-review.md:15)
    durdu = str(rapor.get("durum", "")).startswith("DURDU") or "iki_satir" not in z
    kapilar.append(_kapi(
        "kapali", "ucuz", "code-review.md:15",
        "DURDUR" if durdu else "GEÇTİ",
        f"durum={rapor.get('durum', YOK)!r}; ZIRVE.iki_satir="
        f"{'var' if 'iki_satir' in z else 'YOK'}",
        "katman kapısında duran koşuda doğrulanacak karar yoktur; "
        "önce eksik girdiyi tamamlayın" if durdu else ""))
    if durdu:
        gerekce.append("koşu katman kapısında DURDU — değerlendirilecek karar yok")

    # --- taslak: "The pull request is a draft" (code-review.md:16)
    eksikler = z.get("ZORUNLU_EKSIK") or []
    kapilar.append(_kapi(
        "taslak", "ucuz", "code-review.md:16",
        "DURDUR" if eksikler else "GEÇTİ",
        f"ZORUNLU_EKSIK={eksikler}",
        "zorunlu girdiyi tamamlayıp koşuyu yenileyin" if eksikler else ""))
    if eksikler:
        gerekce.append(f"zorunlu girdi eksik ({len(eksikler)}) — karar TASLAK")

    # --- onemsiz: "does not need code review … trivial change" (code-review.md:17)
    yon = str(z.get("YON_BIAS", YOK)).strip().upper()
    emir = str(z.get("EMIR", YOK))
    onemsiz = (yon in NOTR) and (emir.startswith("EMİR YOK") or emir == YOK)
    if onemsiz and muhurlu:
        # code-review.md:22 muafiyeti — mühürlü koşu "otomatik/önemsiz" görünse de
        # denetlenir; mühür EMİR'i piramit.py:1664'te zaten kapatmıştır.
        onemsiz = False
        muafiyet.append("code-review.md:22 muafiyeti — DENETİM MÜHÜRÜ var; "
                        "'önemsiz' kapısı uygulanmadı (mühürlü koşu yine incelenir)")
    kapilar.append(_kapi(
        "onemsiz", "ucuz", "code-review.md:17",
        "DURDUR" if onemsiz else ("MUAF" if muafiyet else "GEÇTİ"),
        f"YON_BIAS={yon!r}; EMIR={emir[:60]!r}; muhurlendi={muhurlu}"))
    if onemsiz:
        gerekce.append("yön nötr ve emir yok — doğrulanacak sayısal iddia yok")

    # --- zaten_yapildi: "Claude has already commented on this PR" (:18)
    pi = parmak_izi(rapor)
    gorulmus = any(k.get("parmak_izi") == pi for k in defter)
    kapilar.append(_kapi(
        "zaten_yapildi", "ucuz", "code-review.md:18",
        "DURDUR" if gorulmus else "GEÇTİ",
        f"parmak_izi={pi}; defter_kayit={len(defter)}"))
    if gorulmus:
        gerekce.append(f"bu koşu ({pi}) zaten değerlendirilmiş")

    # --- veri_ayni: depo eki (CLAUDE.md kanca kuralı: veri DEĞİŞMİŞSE koş)
    yeni_bar = son_bar_ms(rapor)
    onceki_bar = None
    for k in reversed(defter):
        if isinstance(k.get("son_bar_ms"), int):
            onceki_bar = k["son_bar_ms"]
            break
    ayni = (yeni_bar is not None and onceki_bar is not None and yeni_bar <= onceki_bar)
    kapilar.append(_kapi(
        "veri_ayni", "ucuz",
        "depo eki — CLAUDE.md: 'engine/girdi/ verisi DEĞİŞMİŞSE boru hattını koşar'",
        "DURDUR" if ayni else "GEÇTİ",
        f"yeni_son_bar={yeni_bar}; defterdeki_son_bar={onceki_bar}"))
    if ayni:
        gerekce.append(f"veri ilerlemedi (son bar {yeni_bar} ≤ {onceki_bar})")

    return kapilar, gerekce, muafiyet


# ---------------------------------------------------------------------------
# ana akış
# ---------------------------------------------------------------------------
def ele(rapor: dict, defter: list | None = None, kok: Path | None = None) -> dict:
    defter = defter or []
    kok = Path(kok) if kok else Path.cwd()
    kapilar, gerekce, muafiyet = on_eleme(rapor, defter)
    dur = any(k["hukum"] == "DURDUR" for k in kapilar)

    sonuc = {
        "KARAR": "DUR" if dur else "DEVAM",
        "gerekce": gerekce,
        "muafiyet": muafiyet,
        "kademeler": kapilar,
        "parmak_izi": parmak_izi(rapor),
        "son_bar_ms": son_bar_ms(rapor),
    }

    if dur:
        # Pahalı kademe HİÇ koşmaz — kademelemenin tasarrufu tam burada.
        sonuc["sozlesme_yollari"] = None
        sonuc["ozet"] = None
        sonuc["sonraki"] = ("YOK — pahalı doğrulama (bulgu_dogrula.py) "
                            "çağrılmadı; ucuz kapıda elendi")
    else:
        sonuc["sozlesme_yollari"] = sozlesme_yollari(rapor, kok)   # ucuz  (:24)
        sonuc["ozet"] = kosu_ozeti(rapor)                          # orta  (:28)
        sonuc["sonraki"] = ("pahalı kademe: bulgu_dogrula.py --rapor <rapor> "
                            "--oy 3   (code-review.md:35,38,55)")

    sonuc["maliyet_dokumu"] = _maliyet_dokumu(sonuc)
    sonuc["not"] = ("Yalnız karar-destek. Bu motor gerçek alt-ajan BAŞLATMAZ; "
                    "kaynağın model kademelemesi maliyet sınıfına çevrilmiştir. "
                    "Canlı/otomatik emir DAHİL DEĞİL.")
    return sonuc


def _maliyet_dokumu(sonuc: dict) -> dict:
    kosan = {"ucuz": 0, "orta": 0, "pahali": 0}
    for k in sonuc["kademeler"]:
        kosan[k["maliyet_sinifi"]] += 1
    if sonuc["KARAR"] == "DEVAM":
        kosan["ucuz"] += 1   # sozlesme_yollari (:24)
        kosan["orta"] += 1   # kosu_ozeti      (:28)
    return {
        "kosan_adim": kosan,
        "pahali_kademe_kosuldu": False,
        "aciklama": ("ucuz ← haiku (code-review.md:14,24); "
                     "orta ← sonnet (:28,32); "
                     "pahali ← opus (:35,38,55) — bu motorda KOŞMAZ"),
    }


def ozet_metin(s: dict) -> str:
    L = ["=" * 68, "MALİYET KADEMESİ — ön eleme", "=" * 68]
    for k in s["kademeler"]:
        im = {"GEÇTİ": "✔", "DURDUR": "✖", "MUAF": "◈"}.get(k["hukum"], "?")
        L.append(f"{im} [{k['maliyet_sinifi']:<6}] {k['ad']:<16} {k['kaynak']}")
        L.append(f"     {k['kanit']}")
    for m in s.get("muafiyet") or []:
        L.append(f"◈ {m}")
    L.append("-" * 68)
    L.append(f"KARAR: {s['KARAR']}")
    for g in s["gerekce"]:
        L.append(f"   ✖ {g}")
    if s["KARAR"] == "DEVAM":
        sy = s["sozlesme_yollari"]
        L.append(f"Sözleşme yolları ({len(sy['yollar'])}, içerik okunmadı):")
        for y in sy["yollar"]:
            L.append(f"   • {y}")
        o = s["ozet"]
        L.append(f"Özet: {o['sembol']} | {o['YON_BIAS']} | {o['sentez_karari']} | "
                 f"{o['EMIR'][:52]}")
        L.append(f"       denetim: {o['denetim_ozeti']}"
                 + ("  ⛔ MÜHÜRLÜ" if o["muhurlendi"] else ""))
    L.append(f"SONRAKİ: {s['sonraki']}")
    md = s["maliyet_dokumu"]["kosan_adim"]
    L.append(f"Maliyet: ucuz={md['ucuz']} orta={md['orta']} pahali={md['pahali']}")
    L.append("=" * 68)
    L.append("⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.")
    return "\n".join(L)


def kaydet(sonuc: dict, defter_yolu: Path, sembol: str = YOK) -> None:
    defter_yolu.parent.mkdir(parents=True, exist_ok=True)
    with defter_yolu.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "parmak_izi": sonuc["parmak_izi"],
            "son_bar_ms": sonuc["son_bar_ms"],
            "sembol": sembol,
            "karar": sonuc["KARAR"],
            "zaman_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        }, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# ÖZ-TEST
# ---------------------------------------------------------------------------
def _rapor(**ust) -> dict:
    """Gerçek alan adlarıyla asgari rapor iskeleti (son_rapor.json'dan alınmıştır)."""
    r = {
        "sembol": "BTCUSDT",
        "durum": "TAMAM — piramidin tepesine ulaşıldı",
        "katmanlar": [
            {"katman": "K1-LLM", "gecti": True,
             "olcumler": {"m15_bar": 200, "m15_son_bar": 1785235500000,
                          "h4_bar": 200, "h4_son_bar": 1785225600000}},
            {"katman": "K2-AI-AJAN", "gecti": True,
             "motor_sonuclari": {"karar-motoru": {}, "smc_tespit": {},
                                 "turev-akis": {}}},
            {"katman": "K3-COKLU-AJAN", "gecti": True, "danismanlar": []},
            {"katman": "K4-AGI", "gecti": True, "verifier": {}},
            {"katman": "K5-SI", "gecti": True},
        ],
        "ZIRVE": {
            "YON_BIAS": "SHORT",
            "ISLEM_KALITESI": "TEMİZ GİRİŞ YOK — TEPKİ/SEVİYE BEKLE",
            "sentez_karari": "NÖTR-BEKLE",
            "yon_skoru": -0.5712, "guven_skoru": 0.2039,
            "ZORUNLU_EKSIK": [],
            "EMIR": "LIMIT SHORT @63990.7 | stop 64234.1 | T1 63461.2 | R 2.18",
            "emir_adaylari": [{"emir_tipi": "LIMIT", "yon": "SHORT",
                               "giris": 63990.7, "stop": 64234.1,
                               "hedef": 63461.2, "R": 2.18,
                               "rr_denetim": "TUTARLI"}],
            "iki_satir": {"1_YON": "YÖN (bias): SHORT",
                          "2_ISLEM_KALITESI": "İŞLEM KALİTESİ: …"},
        },
        "DENETIM": {"ozet": "25 denetim, 0 ihlal, 2 uyarı", "muhurlendi": False,
                    "ihlal": [], "uyari": []},
        "KIYAS": {"YON_DEGISIMI": {"etiket": "DEVAM"}},
    }
    for k, v in ust.items():
        if k == "ZIRVE":
            r["ZIRVE"].update(v)
        elif k == "DENETIM":
            r["DENETIM"].update(v)
        else:
            r[k] = v
    return r


def _self_test() -> int:
    kok = Path(__file__).resolve().parents[4]  # …/Future-
    vakalar = []

    # 1) temiz koşu → DEVAM
    vakalar.append(("temiz-kosu", _rapor(), [], "DEVAM", None))

    # 2) katman kapısında durmuş koşu → DUR (code-review.md:15)
    r2 = _rapor(durum="DURDU — K1-LLM")
    r2["ZIRVE"].pop("iki_satir")
    vakalar.append(("kapali/katman-kapisi", r2, [], "DUR", "kapali"))

    # 3) zorunlu girdi eksik → DUR (:16)
    vakalar.append(("taslak/zorunlu-eksik",
                    _rapor(ZIRVE={"ZORUNLU_EKSIK": ["likidasyon", "gorsel"]}),
                    [], "DUR", "taslak"))

    # 4) yön nötr + emir yok → DUR (:17)
    vakalar.append(("onemsiz/notr-emirsiz",
                    _rapor(ZIRVE={"YON_BIAS": "NÖTR",
                                  "EMIR": "EMİR YOK — yön nötr",
                                  "emir_adaylari": []}),
                    [], "DUR", "onemsiz"))

    # 5) defterde var → DUR (:18)
    r5 = _rapor()
    vakalar.append(("zaten-degerlendirildi", r5,
                    [{"parmak_izi": parmak_izi(r5), "son_bar_ms": 1}],
                    "DUR", "zaten_yapildi"))

    # 6) veri ilerlemedi → DUR (depo eki)
    vakalar.append(("veri-ayni", _rapor(),
                    [{"parmak_izi": "sha256:baska", "son_bar_ms": 1785235500000}],
                    "DUR", "veri_ayni"))

    # 7) mühürlü + nötr + emir yok → DEVAM (code-review.md:22 muafiyeti)
    vakalar.append(("muafiyet/muhurlu-kosu",
                    _rapor(ZIRVE={"YON_BIAS": "NÖTR",
                                  "EMIR": "EMİR YOK — DENETİM MÜHÜRÜ",
                                  "emir_adaylari": []},
                           DENETIM={"muhurlendi": True,
                                    "ihlal": ["K3 UYDURMA: …"]}),
                    [], "DEVAM", None))

    gecen = 0
    print("MALİYET KADEMESİ — öz-test")
    for ad, rapor, defter, beklenen, beklenen_kapi in vakalar:
        s = ele(rapor, defter, kok)
        ok = s["KARAR"] == beklenen
        if beklenen_kapi:
            duran = [k["ad"] for k in s["kademeler"] if k["hukum"] == "DURDUR"]
            ok = ok and beklenen_kapi in duran
        gecen += ok
        detay = (s["gerekce"][0] if s["gerekce"]
                 else (s["muafiyet"][0][:56] if s["muafiyet"] else "kapı yok"))
        print(f"[{'GECTI' if ok else 'KALDI'}] {ad}: {s['KARAR']} — {detay}")

    # 8) sıralama korkuluğu: ucuz kapılar pahalıdan ÖNCE koşmalı
    s = ele(_rapor(), [], kok)
    sira = [MALIYET_SIRA[k["maliyet_sinifi"]] for k in s["kademeler"]]
    sirali = sira == sorted(sira)
    pahali_kosmadi = s["maliyet_dokumu"]["kosan_adim"]["pahali"] == 0
    ok8 = sirali and pahali_kosmadi
    gecen += ok8
    print(f"[{'GECTI' if ok8 else 'KALDI'}] maliyet-sirasi: sınıf sırası={sira} "
          f"monoton={sirali}; pahalı kademe koşmadı={pahali_kosmadi}")

    # 9) adım 2 korkuluğu: YALNIZ yol döner, içerik dönmez (code-review.md:24)
    sy = s["sozlesme_yollari"]
    icerik_yok = all(isinstance(y, str) and y.endswith("CLAUDE.md")
                     for y in sy["yollar"])
    kok_var = any(y == str(kok / "CLAUDE.md") for y in sy["yollar"])
    ok9 = icerik_yok and kok_var and "icerik" not in sy
    gecen += ok9
    print(f"[{'GECTI' if ok9 else 'KALDI'}] yol-toplama: {len(sy['yollar'])} yol, "
          f"kök CLAUDE.md={kok_var}, içerik alanı yok={'icerik' not in sy}")

    # 10) DUR halinde pahalı kademe adresi verilmez (tasarruf kanıtı)
    sdur = ele(_rapor(durum="DURDU — K2-AI-AJAN"), [], kok)
    ok10 = (sdur["ozet"] is None and sdur["sozlesme_yollari"] is None
            and sdur["sonraki"].startswith("YOK"))
    gecen += ok10
    print(f"[{'GECTI' if ok10 else 'KALDI'}] tasarruf: DUR'da orta/pahalı adım "
          f"üretilmedi ({sdur['sonraki'][:40]}…)")

    toplam = len(vakalar) + 3
    print(f"\n{gecen}/{toplam} vaka geçti "
          f"{'(HEPSİ TAMAM)' if gecen == toplam else '(EKSİK)'}")
    return 0 if gecen == toplam else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Maliyet kademesi — pahalı doğrulamadan önce ucuz ön eleme")
    ap.add_argument("--rapor", help="piramit koşu raporu (son_rapor.json)")
    ap.add_argument("--defter", help="değerlendirme defteri (jsonl)")
    ap.add_argument("--kok", help="depo kökü (CLAUDE.md yolları için)")
    ap.add_argument("--ozet", action="store_true", help="metin özeti bas")
    ap.add_argument("--kaydet", action="store_true",
                    help="koşuyu deftere işle (--defter gerekli)")
    ap.add_argument("--self-test", action="store_true", help="öz-test koş")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.rapor:
        ap.error("--rapor ya da --self-test gerekli")

    p = Path(args.rapor).expanduser().resolve()
    try:
        rapor = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"RAPOR OKUNAMADI: {e}", file=sys.stderr)
        return 2
    kok = Path(args.kok).expanduser().resolve() if args.kok else Path.cwd()
    sonuc = ele(rapor, _defter_oku(args.defter), kok)

    if args.kaydet and args.defter:
        kaydet(sonuc, Path(args.defter).expanduser(), rapor.get("sembol", YOK))

    print(ozet_metin(sonuc) if args.ozet
          else json.dumps(sonuc, ensure_ascii=False, indent=2))
    return 0 if sonuc["KARAR"] == "DEVAM" else 1


if __name__ == "__main__":
    sys.exit(main())
