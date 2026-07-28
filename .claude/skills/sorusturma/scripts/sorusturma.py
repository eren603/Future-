#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SORUŞTURMA MOTORU — boru hattı arızası için kök-neden protokolü.

Ham arıza yığınını (piramit raporu, gözlemci çıktısı, defter satırı, serbest
metin not) alır ve dört iş yapar:

  DOĞRULA   — her bulgunun gerçekten arıza olduğunu artefakttan YENİDEN türet
  TEKİLLEŞTİR — aynı kök nedene bağlı tekrarları topla (doğrulamadan ÖNCE)
  SIRALA    — iddia edilen şiddete değil, TÜRETİLEN etkiye göre sırala
  YÖNLENDİR — her hayatta kalanı sahibine (motor/dosya) etiketle

Çıktı: SORUSTURMA.json + SORUSTURMA.md — "Şunlarla ilgilen" ve "Düşenler"
diye ikiye ayrılmış; DÜŞENLER DE GEREKÇESİYLE raporlanır, gizlenmez.

Fazlar (kaynak triage protokolüyle birebir sıralı):
  0 mod seçimi + mülakat  → 1 al/normalize → 2 tekilleştir → 3 doğrula
  → 4 etki sırala → 5 yönlendir → 6 çıktı

FAIL-CLOSED: doğrulanamayan bulgu "gerçek arıza" sayılmaz; kesinlik
politikasında düşer, kapsam politikasında `elle_inceleme_gerek` olur.
Uydurma yok: her sayı/alıntı okunan bir artefakttan gelir; okunamayan
alan `VERİ YOK` yazılır.

⚠️ Bu motor HEDEF KODU ÇALIŞTIRMAZ. Boru hattını koşturmaz, motor
çağırmaz, ağa çıkmaz. Yalnız artefakt okur (kaynak sözleşmesinin
"Do not execute target code / Do not reach the network" kuralı).

Kullanım:
    python3 sorusturma.py <ariza-yolu> [--auto] [--oy N] [--depo PATH]
        [--yp-kurallari FILE] [--taze] [--cikti-dizini DIR]
        [--baglam FILE] [--oy-dosyasi FILE]
    python3 sorusturma.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

YOK = "VERİ YOK"
_HERE = Path(__file__).resolve().parent
SKILL_DIR = _HERE.parent
VARSAYILAN_YP = SKILL_DIR / "kurallar" / "yanlis_pozitif.yaml"

# Kök sınırlama: append/reset gibi yıkıcı yollar bu kökün DIŞINA çıkamaz.
_KOK = Path(os.environ.get("SORUSTURMA_KOK", os.getcwd())).resolve()

# --------------------------------------------------------------------------
# Sözlük — bu depodaki hüküm/kod dağarcığı
# --------------------------------------------------------------------------
HUKUM = ("gercek_ariza", "yanlis_pozitif", "kopya")
OY = ("GERCEK_ARIZA", "YANLIS_POZITIF", "DOGRULANAMADI")
CURUTME = ("kanit_yok", "zaten_ele_alinmis", "tekrarlanamaz", "tasarim_geregi",
           "artefakt_yanlis_okunmus", "kopya", "uygulanabilir_degil", "yok")
SIDDETLER = ("YÜKSEK", "ORTA", "DÜŞÜK")
_SIDDET_RANK = {"YÜKSEK": 2, "ORTA": 1, "DÜŞÜK": 0}

# Gözlemcinin KRİTİK ihlal kümesi (gozlemci.py sözleşmesi) — deponun kendi
# beyanı; K4/K5'te bu kodlar işlem kalitesini MÜHÜRLER.
KRITIK_KODLAR = {"UYDURMA", "DAIRESEL", "EKSIK_AKTARIM", "MEMNUN_ETME"}
UYARI_KODLAR = {"TUNEL", "CARPISMA", "SIRADAN", "HAFIZA"}

# Doğrulama mercekleri — sıra ÖNEMLİ: --oy N ilk N merceği koşturur.
MERCEKLER = ("artefakt", "yp_kural", "tasarim", "tekrar", "celiski")

# Etki modeli boost'u için anahtar kelimeler (kullanıcı beyanı ile eşleşme)
ETKI_SOZLUGU = {
    "sicil": r"sicil|defter|akıbet|akibet|hafıza|hafiza|kalibrasyon",
    "uydurma": r"uydurma|kaynaksız|kaynaksiz|dayanaksız",
    "emir": r"emir|seviye|stop|hedef|R\b|pozisyon",
    "yon": r"yön|yon_bias|bias|karar yönü",
    "veri": r"girdi|veri|bayat|tazelik|damga",
}

# Ön koşul çıkarımı — mekanik işaretler (varsayimlar'da etiketlenir)
ON_KOSUL_ISARET = [
    (r"ikinci sembol|\beth\b|korelasyon|çapraz-varlık", "ikinci sembol koşusu gerekir"),
    (r"\belle\b|panel|görsel|gorsel|likidasyon|video|ekran görüntüsü",
     "elle girilen zorunlu girdi gerekir"),
    (r"kum_havuzu|kum havuzu|self.?test|öz-?test", "yalnız kum havuzu/öz-test koşusunda"),
    (r"bayat|tazelik|damga", "girdi tazelik toleransının aşılması gerekir"),
    (r"\bağ\b|network|indir|binance|uzak uç", "dış ağ erişimi gerekir"),
    (r"backtest|portföy|portfoy|risk motoru", "isteğe bağlı ek motorun beyan edilmesi gerekir"),
]

# --------------------------------------------------------------------------
# Alan sözlüğü — kaynak-anahtar takma adları → kanonik ad
# --------------------------------------------------------------------------
ALIAS = {
    "dosya": ("dosya", "artefakt", "file", "path", "kaynak_dosya", "dosya_yolu",
              "kanit_dosya", "filename", "rapor"),
    "konum": ("konum", "katman", "alan", "satir", "line", "line_number", "lineno",
              "faz", "motor"),
    "kategori": ("kategori", "kod", "ihlal_kodu", "type", "category", "sinif",
                 "rule_id", "cwe"),
    "siddet": ("siddet", "şiddet", "durum", "severity", "seviye", "level",
               "priority", "risk"),
    "baslik": ("baslik", "başlık", "ozet", "özet", "title", "name", "summary",
               "mesaj", "message"),
    "belirti": ("belirti", "kanit", "kanıt", "description", "details", "detay",
                "aciklama", "açıklama", "body", "evidence", "report"),
    "tekrar_senaryosu": ("tekrar_senaryosu", "senaryo", "repro", "reproduction",
                         "nasil", "tekrar", "adimlar"),
    "on_kosullar": ("on_kosullar", "kosullar", "koşullar", "preconditions",
                    "requirements", "varsayimlar", "assumptions"),
    "oneri": ("oneri", "öneri", "duzeltme", "düzeltme", "fix", "remediation",
              "mitigation", "recommendation"),
    "tarayici_guveni": ("tarayici_guveni", "guven", "güven", "confidence",
                        "score", "skor", "certainty"),
}
KANONIK = tuple(ALIAS)
KAPSAYICI_ANAHTAR = ("arizalar", "bulgular", "ihlaller", "kayitlar", "findings",
                     "results", "issues", "vulnerabilities", "incidents")


# ==========================================================================
# Kontrol noktası (checkpoint) altyapısı — atomik, JSON doğrulamalı
# ==========================================================================
def _sinirla(p, *, bitis: str | None = None) -> Path:
    """Yolu çöz ve _KOK altında kalmasını ZORUNLU kıl."""
    r = Path(p).resolve()
    if not r.is_relative_to(_KOK):
        print(f"sorusturma: {_KOK} dışındaki yol reddedildi: {p}", file=sys.stderr)
        raise SystemExit(2)
    if bitis and not r.name.endswith(bitis):
        print(f"sorusturma: {p} reddedildi (ad {bitis!r} ile bitmeli)", file=sys.stderr)
        raise SystemExit(2)
    return r


def _atomik_yaz(yol: Path, veri: str) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(yol.suffix + ".tmp")
    gecici.write_text(veri, encoding="utf-8")
    os.replace(gecici, yol)


def _ilerleme_oku(durum_dizini: Path) -> dict:
    """TEK GERÇEK KAYNAK: yalnız ilerleme.json okunur; faz*.json GLOB'LANMAZ
    (önceki koşudan kalan bayat dosyalara güvenilmez)."""
    p = durum_dizini / "ilerleme.json"
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        return v if isinstance(v, dict) else {"durum": "bozuk"}
    except (OSError, ValueError):
        return {"durum": "yok"} if not p.exists() else {"durum": "bozuk"}


def _ilerleme_yaz(durum_dizini: Path, *, durum: str, faz: int,
                  parcalar: list) -> None:
    _atomik_yaz(durum_dizini / "ilerleme.json", json.dumps(
        {"durum": durum, "faz_tamam": faz, "parcalar_tamam": parcalar,
         "guncelleme": datetime.now(timezone.utc).isoformat()},
        ensure_ascii=False))


def _faz_kaydet(durum_dizini: Path, n: int, ad: str, yuk: dict,
                parcalar: list | None = None) -> None:
    _atomik_yaz(durum_dizini / f"faz{n}.json",
                json.dumps(yuk, ensure_ascii=False, indent=1))
    _ilerleme_yaz(durum_dizini, durum="koşuyor", faz=n, parcalar=parcalar or [])


def _faz_yukle(durum_dizini: Path, n: int) -> dict | None:
    try:
        return json.loads((durum_dizini / f"faz{n}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _parca_kaydet(durum_dizini: Path, pid: str, yuk: dict) -> None:
    if "/" in pid or ".." in pid:
        raise SystemExit(2)
    _atomik_yaz(durum_dizini / f"parca_{pid}.json",
                json.dumps(yuk, ensure_ascii=False, indent=1))
    ilerleme = _ilerleme_oku(durum_dizini)
    parcalar = ilerleme.get("parcalar_tamam") or []
    if pid not in parcalar:
        parcalar.append(pid)
    _ilerleme_yaz(durum_dizini, durum="koşuyor",
                  faz=int(ilerleme.get("faz_tamam", 2)), parcalar=parcalar)


def _parca_yukle(durum_dizini: Path, pid: str) -> dict | None:
    try:
        return json.loads((durum_dizini / f"parca_{pid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _durum_sifirla(durum_dizini: Path) -> None:
    d = _sinirla(durum_dizini, bitis="-state")
    if d.exists():
        shutil.rmtree(d)


def _ekle(cikti: Path, parca: str) -> None:
    """Rapor parça parça eklenir: takılan bir parça TEK bölümü kaybettirir,
    dosyanın tamamını değil."""
    cikti.parent.mkdir(parents=True, exist_ok=True)
    with cikti.open("a", encoding="utf-8") as f:
        f.write(parca)
        if not parca.endswith("\n"):
            f.write("\n")


# ==========================================================================
# Yardımcılar
# ==========================================================================
def _metin(x) -> str:
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        return " | ".join(_metin(i) for i in x)
    if isinstance(x, dict):
        return json.dumps(x, ensure_ascii=False)
    return str(x)


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _oku_metin(p: Path, sinir: int = 400_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:sinir]
    except OSError:
        return ""


def _kaynak_satir(yol: Path, desen: str) -> str:
    """Bir kaynak dosyada deseni ara, `dosya:satır` döndür (grounding).
    Bulunamazsa VERİ YOK — satır numarası UYDURULMAZ."""
    try:
        for i, s in enumerate(yol.read_text(encoding="utf-8",
                                            errors="replace").splitlines(), 1):
            if re.search(desen, s):
                return f"{yol.name}:{i}"
    except OSError:
        pass
    return YOK


def _artefakt_satir(yol: Path, anahtarlar: list) -> tuple:
    """Artefaktta anahtarları ara → (ilk_kanit 'dosya:satır', toplam_isabet)."""
    metin = _oku_metin(yol)
    if not metin:
        return YOK, 0
    satirlar = metin.splitlines()
    ilk, toplam = YOK, 0
    for i, s in enumerate(satirlar, 1):
        for a in anahtarlar:
            if a and a in s:
                toplam += 1
                if ilk == YOK:
                    ilk = f"{yol.name}:{i}"
    return ilk, toplam


def _anahtarlar(b: dict) -> list:
    """Bulgunun artefaktta aranacak ayırt edici anahtarları."""
    a = []
    for alan in ("kategori", "konum"):
        v = _metin(b.get(alan)).strip()
        if v and v != YOK:
            a.append(v)
    bel = _metin(b.get("belirti")).strip()
    if len(bel) >= 12:
        # noktalama/format kaymasına dayanıklı olsun diye orta uzunlukta bir dilim
        a.append(bel[:34])
    return [x for x in a if x]


# ==========================================================================
# FAZ 0 — mod seçimi ve mülakat bağlamı
# ==========================================================================
OTO_BAGLAM = {
    "mod": "auto",
    "kapsam": ("Bilinmiyor. Boru hattının TAMAMI kapsam sayılır; hangi katman/"
               "motorun etkilendiği varsayımı gerekçede AÇIKÇA işaretlenir."),
    "etki_modeli": [],
    "siddet_standardi": "türetilmiş YÜKSEK/ORTA/DÜŞÜK (ön koşul + tekrar koşulu)",
    "gurultu_toleransi": "kesinlik",
}


def faz0_mod(args) -> dict:
    """Mülakat CEVAPLARI --baglam dosyasından gelir (SKILL.md'deki
    AskUserQuestion turu onları yazar). --auto ise varsayılanlar kullanılır."""
    baglam = dict(OTO_BAGLAM)
    kaynak = "auto varsayılanları"
    if args.baglam and not args.auto:
        p = Path(args.baglam).expanduser()
        try:
            gelen = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(gelen, dict):
                baglam.update({k: v for k, v in gelen.items() if v not in (None, "")})
                baglam["mod"] = "interaktif"
                kaynak = str(p)
        except (OSError, ValueError) as e:
            baglam["_baglam_hatasi"] = f"{type(e).__name__}: {e}"
    if baglam.get("gurultu_toleransi") not in ("kesinlik", "kapsam", "sor"):
        baglam["gurultu_toleransi"] = "kesinlik"
    baglam.update({
        "oy_sayisi": args.oy,
        "depo": str(args.depo),
        "ariza_yolu": str(args.ariza),
        "yp_kurallari": str(args.yp_kurallari) if args.yp_kurallari else None,
        "_baglam_kaynagi": kaynak,
    })
    return baglam


# ==========================================================================
# FAZ 1 — al ve normalize et
# ==========================================================================
def _kanonik_al(ham: dict) -> dict:
    b = {}
    for kanon, adlar in ALIAS.items():
        for ad in adlar:
            if ad in ham and ham[ad] not in (None, "", [], {}):
                b[kanon] = ham[ad]
                break
    return b


def _rapordan_bulgular(veri: dict, kaynak: str) -> list:
    """piramit.py raporu / gozlemci.py çıktısı → bulgu listesi."""
    out = []
    den = veri.get("DENETIM") if isinstance(veri.get("DENETIM"), dict) else veri
    for anahtar, siddet in (("ihlal", "İHLAL"), ("uyari", "UYARI")):
        for satir in (den.get(anahtar) or []):
            s = _metin(satir)
            m = re.match(r"\s*([A-ZÇĞİÖŞÜ0-9\-]+)\s*/\s*([A-Z_]+)\s*:\s*(.*)", s)
            katman, kod, gerekce = (m.group(1), m.group(2), m.group(3)) if m \
                else (YOK, "GOZLEMCI", s)
            out.append({"kategori": kod, "konum": katman, "siddet": siddet,
                        "baslik": gerekce[:90], "belirti": s, "dosya": kaynak})
    durum = _metin(veri.get("durum"))
    if durum.startswith("DURDU"):
        z = veri.get("ZIRVE") or {}
        out.append({"kategori": "KAPI", "konum": _metin(z.get("ulasilan_katman")),
                    "siddet": "İHLAL", "baslik": durum[:90],
                    "belirti": f"{durum} — {_metin(z.get('neden'))}", "dosya": kaynak})
    z = veri.get("ZIRVE") or {}
    for eksik in (z.get("ZORUNLU_EKSIK") or []):
        out.append({"kategori": "ZORUNLU_GIRDI", "konum": "K1-LLM", "siddet": "UYARI",
                    "baslik": _metin(eksik)[:90],
                    "belirti": f"zorunlu girdi eksik: {_metin(eksik)}", "dosya": kaynak})
    ak = z.get("ONCEKI_AKIBET") or {}
    ak_durum = _metin(ak.get("durum"))
    if "HATA" in ak_durum.upper():
        out.append({"kategori": "AKIBET", "konum": "K1-LLM", "siddet": "İHLAL",
                    "baslik": ak_durum[:90],
                    "belirti": f"akıbet ölçümü hata verdi: {ak_durum}", "dosya": kaynak})
    return out


def _jsonl_bulgular(satirlar: list, kaynak: str) -> list:
    out = []
    for kayit in satirlar:
        if not isinstance(kayit, dict):
            continue
        if kayit.get("duzeltme_notu") or kayit.get("r_iptal_nedeni"):
            out.append({
                "kategori": "SICIL_EZILME", "konum": "duzeltme_notu",
                "siddet": "İHLAL", "dosya": kaynak,
                "baslik": "defter satırı yeniden yazıldı / gerçekleşen R iptal edildi",
                "belirti": (f"duzeltme_notu: {_metin(kayit.get('duzeltme_notu'))} | "
                            f"r_iptal_nedeni: {_metin(kayit.get('r_iptal_nedeni'))}")})
        elif _metin(kayit.get("durum")).startswith("DURDU"):
            out.append({"kategori": "KAPI", "konum": _metin(
                (kayit.get("zirve") or {}).get("ulasilan_katman")),
                "siddet": "İHLAL", "dosya": kaynak,
                "baslik": _metin(kayit.get("durum"))[:90],
                "belirti": _metin(kayit.get("durum"))})
        else:
            k = _kanonik_al(kayit)
            if k:
                k.setdefault("dosya", kaynak)
                out.append(k)
    return out


def _markdown_bulgular(metin: str, kaynak: str) -> list:
    """Serbest arıza notu — en iyi çaba; source_format işaretlenir."""
    parcalar = re.split(r"(?m)^\s*(?:#{2,3}\s+|-{3,}\s*$)", metin)
    out = []
    for p in parcalar:
        p = p.strip()
        if len(p) < 20:
            continue
        alan = {}
        for etiket, kanon in (("Dosya", "dosya"), ("Katman", "konum"),
                              ("Satır", "konum"), ("Kod", "kategori"),
                              ("Kategori", "kategori"), ("Şiddet", "siddet"),
                              ("Belirti", "belirti")):
            m = re.search(rf"(?mi)^\s*{etiket}\s*[:=]\s*(.+)$", p)
            if m:
                alan.setdefault(kanon, m.group(1).strip())
        m = re.search(r"([\w./-]+\.(?:py|json|jsonl|md|yaml)):(\d+)", p)
        if m:
            alan.setdefault("dosya", m.group(1))
            alan.setdefault("konum", m.group(2))
        alan.setdefault("baslik", p.splitlines()[0][:90])
        alan.setdefault("belirti", p[:600])
        alan["_bicim"] = "markdown_sezgisel"
        alan.setdefault("dosya", None)
        if alan["dosya"] is None:
            alan.pop("dosya")
        out.append(alan)
    return out


def _dosyadan_ham(p: Path) -> list:
    """Tek dosyadan ham bulgu listesi çıkar (biçim tanıma)."""
    ad, kaynak = p.name.lower(), str(p)
    if ad.endswith(".jsonl"):
        satirlar = []
        for s in _oku_metin(p).splitlines():
            s = s.strip()
            if not s:
                continue
            try:
                satirlar.append(json.loads(s))
            except ValueError:
                continue
        return _jsonl_bulgular(satirlar, kaynak)
    if ad.endswith(".json"):
        try:
            veri = json.loads(_oku_metin(p, 4_000_000))
        except ValueError:
            return []
        if isinstance(veri, list):
            # Kapsayıcı dosyanın kendi yolu KAYNAKTIR, artefakt DEĞİL: kayıtta
            # artefakt yolu yoksa bulgu "yerelleştirilemez" kalmalı (kaynak
            # sözleşmesi: "Never emit a confident verdict on a finding you
            # could not locate").
            return [_kanonik_al(x) for x in veri if isinstance(x, dict)]
        if isinstance(veri, dict):
            if "DENETIM" in veri or "gozlemciler" in veri or "katmanlar" in veri:
                return _rapordan_bulgular(veri, kaynak)
            for anahtar in KAPSAYICI_ANAHTAR:
                if isinstance(veri.get(anahtar), list):
                    return [_kanonik_al(x) for x in veri[anahtar]
                            if isinstance(x, dict)]
            k = _kanonik_al(veri)
            return [k] if k else []
        return []
    if ad.endswith((".md", ".txt", ".log")):
        return _markdown_bulgular(_oku_metin(p), kaynak)
    return []


def _dosyadan(p: Path) -> list:
    """Ham bulgulara KAYNAK dosyayı iliştir (artefakt yolundan ayrı tutulur)."""
    out = []
    for h in _dosyadan_ham(p):
        if isinstance(h, dict) and h:
            h["_kaynak_dosya"] = str(p)
            out.append(h)
    return out


def _yol_coz(dosya: str, depo: Path) -> tuple:
    """(çözülmüş yol, yöntem) — a) depo/dosya b) mutlak/cwd-göreli
    c) yaygın önek soyularak. Hiçbiri tutmazsa (None, gerekçe)."""
    d = str(dosya).strip()
    adaylar = [("a) depo/dosya", depo / d), ("b) mutlak-veya-cwd", Path(d))]
    for onek in ("src/", "app/", "./", depo.name + "/"):
        if d.startswith(onek):
            adaylar.append((f"c) '{onek}' öneki soyuldu", depo / d[len(onek):]))
    for yontem, aday in adaylar:
        try:
            if aday.exists():
                return aday.resolve(), yontem
        except OSError:
            continue
    return None, "çözülemedi"


def faz1_al(args, baglam: dict) -> dict:
    yol = Path(args.ariza).expanduser()
    depo = Path(args.depo).expanduser().resolve()
    if not yol.exists():
        print(f"sorusturma: arıza yolu yok: {yol}", file=sys.stderr)
        raise SystemExit(2)

    dosyalar = []
    if yol.is_dir():
        for desen in ("**/*.json", "**/*.jsonl", "**/*.md", "**/*.txt"):
            dosyalar += sorted(yol.glob(desen))
    else:
        dosyalar = [yol]

    hamlar = []
    for d in dosyalar[:200]:
        hamlar += _dosyadan(d)
    if not hamlar:
        print(f"sorusturma: '{yol}' içinde ayrıştırılabilir arıza kaydı yok "
              f"(bakılan {len(dosyalar)} dosya). Uydurma bulgu üretilmez.",
              file=sys.stderr)
        raise SystemExit(1)

    # Güven sırası: yüksek-sinyal bulgular önce doğrulanır (yalnız SIRALAMA
    # önceliği; hükmü ETKİLEMEZ).
    guvenli = [h for h in hamlar if _f(h.get("tarayici_guveni")) is not None]
    if len(guvenli) > len(hamlar) / 2:
        hamlar.sort(key=lambda h: -(_f(h.get("tarayici_guveni")) or 0))

    bulgular, coz_yontem = [], YOK
    for i, ham in enumerate(hamlar, 1):
        b = {k: ham.get(k) for k in KANONIK if ham.get(k) not in (None, "", [], {})}
        b["id"] = f"a{i:03d}"
        b["kaynak"] = _metin(ham.get("_kaynak_dosya") or yol)
        b["_bicim"] = ham.get("_bicim", "yapisal")
        g = _f(b.get("tarayici_guveni"))
        b["tarayici_guveni"] = round(g, 3) if g is not None else None
        b["iddia_edilen_siddet"] = _metin(b.get("siddet")) or YOK
        b["eksik_alanlar"] = [k for k in KANONIK if k not in b]
        if isinstance(b.get("on_kosullar"), str):
            b["on_kosullar"] = [b["on_kosullar"]]
        # yerelleştirme
        if not b.get("dosya"):
            b["_yerellestirilemez"] = "girdi kaydında artefakt yolu yok"
        else:
            coz, yontem = _yol_coz(b["dosya"], depo)
            if coz is None:
                b["_yerellestirilemez"] = f"artefakt {depo} altında çözülemedi"
            else:
                b["_cozulmus"] = str(coz)
                coz_yontem = yontem if coz_yontem == YOK else coz_yontem
        bulgular.append(b)

    cozulen = [b for b in bulgular if b.get("_cozulmus")]
    if not cozulen:
        print(f"sorusturma: DURDU — hiçbir bulgunun artefaktı {depo} altında "
              "bulunamadı. Doğrulama artefakt okumaya dayanır; --depo değerini "
              "kayıttaki yollara uyacak şekilde verin. "
              f"İlk kayıttaki yol: {bulgular[0].get('dosya', YOK)}", file=sys.stderr)
        raise SystemExit(2)

    return {"faz": 1, "baglam": baglam, "bulgular": bulgular,
            "yol_cozumu": coz_yontem, "taranan_dosya": len(dosyalar)}


# ==========================================================================
# FAZ 2 — TEKİLLEŞTİR (doğrulamadan ÖNCE)
# ==========================================================================
def _konum_yakin(a, b) -> bool:
    sa, sb = _metin(a).strip(), _metin(b).strip()
    if not sa and not sb:
        return True                     # iki taraf da eksik → eşleşir
    if not sa or not sb:
        return False                    # tek taraf eksik → EŞLEŞMEZ
    na, nb = _f(sa), _f(sb)
    if na is not None and nb is not None:
        return abs(na - nb) <= 10
    return sa.casefold() == sb.casefold()


def _kategori_norm(x) -> str:
    return re.sub(r"[^a-z0-9]+", "", _metin(x).casefold())


def faz2_tekille(durum: dict) -> dict:
    bulgular = durum["bulgular"]
    calisan = [b for b in bulgular if not b.get("_yerellestirilemez")]
    for b in bulgular:
        if b.get("_yerellestirilemez"):
            # Yerelleştirilemez bulgu tekilleştirmeye GİRMEZ: ne yutar ne yutulur.
            b.update({"hukum": "yanlis_pozitif", "dogrulama_hukmu": "elle_inceleme_gerek",
                      "guven": 0, "curutme_nedenleri": ["kanit_yok"],
                      "gerekce": ("girdide artefakt yolu yok; statik olarak "
                                  "doğrulanamaz, elle inceleme gerekir"),
                      "oy_dagilimi": {"gercek_ariza": 0, "yanlis_pozitif": 0,
                                      "dogrulanamadi": 0}})

    kumeler = {}
    for b in calisan:
        yerlesti = False
        for kok, uyeler in kumeler.items():
            temsil = uyeler[0]
            if (_metin(temsil.get("_cozulmus")) == _metin(b.get("_cozulmus"))
                    and _kategori_norm(temsil.get("kategori")) == _kategori_norm(b.get("kategori"))
                    and _konum_yakin(temsil.get("konum"), b.get("konum"))):
                uyeler.append(b)
                yerlesti = True
                break
        if not yerlesti:
            kumeler[b["id"]] = [b]

    adaylar = []
    for uyeler in kumeler.values():
        # kanonik = en az eksik alanı olan; eşitlikte en küçük id
        kanon = sorted(uyeler, key=lambda x: (len(x.get("eksik_alanlar") or []), x["id"]))[0]
        kanon["yuttuklari"] = []
        for u in uyeler:
            if u is kanon:
                continue
            u.update({"hukum": "kopya", "kopyasi": kanon["id"],
                      "curutme_nedenleri": ["kopya"], "guven": 0,
                      "gerekce": (f"{kanon['id']} ile aynı artefakt+kategori+konum "
                                  "kümesinde; biri düzeltilirse diğeri de düzelir")})
            kanon["yuttuklari"].append(u["id"])
        adaylar.append(kanon["id"])

    return {"faz": 2, "baglam": durum["baglam"], "bulgular": bulgular,
            "adaylar": adaylar,
            "not": ("Tekilleştirme doğrulamadan ÖNCE koşar: aynı kök nedene bağlı "
                    "her tekrar N doğrulayıcı harcamasın diye (kaynak tasarım notu: "
                    "'Dedupe runs before verify to cut verifier spend by the "
                    "duplication factor').")}


# ==========================================================================
# FAZ 3 — DOĞRULA (çok mercekli bağımsız oylama)
# ==========================================================================
def _yp_kurallari_yukle(ek_dosya: str | None) -> dict:
    kurallar, kaynaklar = [], []
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        yaml = None
    for p in [VARSAYILAN_YP] + ([Path(ek_dosya).expanduser()] if ek_dosya else []):
        if not p or not Path(p).exists():
            continue
        ham = _oku_metin(Path(p))
        veri = None
        if yaml is not None:
            try:
                veri = yaml.safe_load(ham)
            except Exception:  # noqa: BLE001
                veri = None
        if isinstance(veri, dict) and isinstance(veri.get("kurallar"), list):
            for k in veri["kurallar"]:
                if isinstance(k, dict) and k.get("desen"):
                    k.setdefault("alanlar", veri.get("varsayilan_alanlar")
                                 or ["kategori", "baslik", "belirti", "konum", "siddet"])
                    kurallar.append(k)
            kaynaklar.append(str(p))
        elif isinstance(veri, list):
            # düz metin/kurum kuralları: her satır bir desen
            for i, satir in enumerate(veri, 1):
                kurallar.append({"id": f"kurum-{i}", "ad": "kurum_kurali",
                                 "desen": [re.escape(_metin(satir))],
                                 "alanlar": ["baslik", "belirti"],
                                 "neden": "tasarim_geregi", "guven": 7,
                                 "gerekce": _metin(satir)})
            kaynaklar.append(str(p))
        elif ham.strip():
            for i, satir in enumerate(
                    [s for s in ham.splitlines() if s.strip()
                     and not s.strip().startswith("#")], 1):
                kurallar.append({"id": f"kurum-{i}", "ad": "kurum_kurali",
                                 "desen": [re.escape(satir.strip())],
                                 "alanlar": ["baslik", "belirti"],
                                 "neden": "tasarim_geregi", "guven": 7,
                                 "gerekce": satir.strip()})
            kaynaklar.append(str(p) + " (düz metin)")
    return {"kurallar": kurallar, "kaynaklar": kaynaklar}


def _alan_metni(b: dict, alanlar) -> str:
    return " \n".join(_metin(b.get(a)) for a in alanlar)


def _mercek_artefakt(b: dict, depo: Path, ctx: dict) -> dict:
    """1) ARTEFAKTI KENDİN OKU. İddiayı özetten değil dosyadan yeniden türet."""
    coz = b.get("_cozulmus")
    if not coz:
        return {"mercek": "artefakt", "hukum": "YANLIS_POZITIF", "guven": 8,
                "curutme_nedeni": "kanit_yok", "ilk_kanit": "yok",
                "gerekce": "iddia edilen artefakt depoda çözülemedi"}
    p = Path(coz)
    ilk, isabet = _artefakt_satir(p, _anahtarlar(b))
    if isabet == 0:
        return {"mercek": "artefakt", "hukum": "YANLIS_POZITIF", "guven": 6,
                "curutme_nedeni": "artefakt_yanlis_okunmus", "ilk_kanit": "yok",
                "gerekce": (f"{p.name} okundu; bulgunun anahtarları "
                            f"({', '.join(_anahtarlar(b))[:70]}) artefaktta YOK — "
                            "iddia kaynakta doğrulanmıyor")}
    return {"mercek": "artefakt", "hukum": "GERCEK_ARIZA",
            "guven": 8 if isabet >= 2 else 6, "curutme_nedeni": "yok",
            "ilk_kanit": ilk,
            "gerekce": (f"iddia artefaktta birebir bulundu: {ilk} "
                        f"({isabet} isabet); belirti kaynaktan yeniden türetildi")}


def _mercek_yp_kural(b: dict, depo: Path, ctx: dict) -> dict:
    """2) YANLIŞ-POZİTİF KURALLARI. Tutarsa bulgu teknik olarak doğru olsa
    bile yanlış-pozitiftir; hükümde kural numarası ANILIR."""
    for k in ctx["yp"]["kurallar"]:
        metin = _alan_metni(b, k.get("alanlar") or [])
        tuttu = any(re.search(d, metin, re.IGNORECASE) for d in (k.get("desen") or []))
        if not tuttu:
            continue
        istisna = any(re.search(d, metin, re.IGNORECASE)
                      for d in (k.get("istisna") or []))
        if istisna:
            return {"mercek": "yp_kural", "hukum": "GERCEK_ARIZA", "guven": 6,
                    "curutme_nedeni": "yok", "ilk_kanit": f"YP kural {k.get('id')} (istisna)",
                    "gerekce": (f"YP kuralı {k.get('id')} ({k.get('ad')}) tuttu ama "
                                "İSTİSNASI da tuttu → tasarım savunması düşer, "
                                "bulgu gerçek arıza adayı kalır")}
        return {"mercek": "yp_kural", "hukum": "YANLIS_POZITIF",
                "guven": int(k.get("guven", 8)),
                "curutme_nedeni": k.get("neden", "tasarim_geregi"),
                "yp_kurali": k.get("id"), "ilk_kanit": f"YP kural {k.get('id')}",
                "gerekce": f"YP kuralı {k.get('id')} ({k.get('ad')}): "
                           f"{_metin(k.get('gerekce')).strip()}"}
    return {"mercek": "yp_kural", "hukum": "GERCEK_ARIZA", "guven": 4,
            "curutme_nedeni": "yok", "ilk_kanit": f"{len(ctx['yp']['kurallar'])} YP kuralı",
            "gerekce": (f"{len(ctx['yp']['kurallar'])} yanlış-pozitif kuralının hiçbiri "
                        "tutmadı → tasarım savunması yok")}


def _mercek_tasarim(b: dict, depo: Path, ctx: dict) -> dict:
    """3) DEPO SÖZLEŞMESİ NE DİYOR? Bu davranış deponun KENDİ beyanında
    kritik ihlal mi, yoksa fail-closed tasarım mı?"""
    kod = _metin(b.get("kategori")).upper().replace("İ", "I")
    if kod in KRITIK_KODLAR:
        kanit = _kaynak_satir(ctx["gozlemci_py"], r"^KRITIK\s*=") \
            if ctx["gozlemci_py"].exists() else YOK
        return {"mercek": "tasarim", "hukum": "GERCEK_ARIZA", "guven": 9,
                "curutme_nedeni": "yok", "ilk_kanit": kanit,
                "gerekce": (f"{kod} deponun KENDİ sözleşmesinde KRİTİK ihlaldir "
                            f"(gozlemci.py KRITIK kümesi, {kanit}) — kritik ihlalde "
                            "işlem kalitesi mühürlenir")}
    if kod in UYARI_KODLAR and _metin(b.get("siddet")).upper().startswith("UYAR"):
        kanit = _kaynak_satir(ctx["gozlemci_py"], r"^KRITIK\s*=") \
            if ctx["gozlemci_py"].exists() else YOK
        return {"mercek": "tasarim", "hukum": "DOGRULANAMADI", "guven": 4,
                "curutme_nedeni": "yok", "ilk_kanit": kanit,
                "gerekce": (f"{kod} UYARI seviyesinde işaretlenmiş ve deponun kritik "
                            f"kümesinin DIŞINDA ({kanit}); mühürleme tetiklemez — "
                            "arıza mı ayar mı, statik olarak ayrılamıyor")}
    metin = _alan_metni(b, ("kategori", "baslik", "belirti", "konum"))
    if re.search(r"DURDU|kap[ıi]s[ıi] GEÇ[İI]LMED", metin, re.IGNORECASE) and \
            not re.search(r"Traceback|Exception|çöktü", metin, re.IGNORECASE):
        kanit = _kaynak_satir(ctx["piramit_py"], r"FAIL-CLOSED") \
            if ctx["piramit_py"].exists() else YOK
        return {"mercek": "tasarim", "hukum": "YANLIS_POZITIF", "guven": 8,
                "curutme_nedeni": "tasarim_geregi", "ilk_kanit": kanit,
                "gerekce": (f"kapı düşmesi fail-closed TASARIMDIR ({kanit}): "
                            "'Kapı geçilmezse üst katman KOŞMAZ'")}
    return {"mercek": "tasarim", "hukum": "DOGRULANAMADI", "guven": 3,
            "curutme_nedeni": "yok", "ilk_kanit": YOK,
            "gerekce": (f"kategori '{kod}' deponun sözleşme kümelerinde (kritik/uyarı) "
                        "yer almıyor → tasarım mı arıza mı statik olarak belirsiz")}


def _tarih_dosyalari(depo: Path, coz: str | None) -> list:
    adaylar = []
    if coz:
        adaylar.append(Path(coz))
    desenler = ("**/son_rapor*.json", "**/*defter*.jsonl", "**/durum.json",
                "**/onceki_kosu.json", "**/ornek_*.json", "**/ornek_*.jsonl")
    for d in desenler:
        try:
            adaylar += sorted(depo.glob(d))[:12]
        except OSError:
            continue
    goruldu, out = set(), []
    for p in adaylar:
        try:
            r = p.resolve()
        except OSError:
            continue
        if r not in goruldu and r.is_file():
            goruldu.add(r)
            out.append(r)
    return out[:40]


def _mercek_tekrar(b: dict, depo: Path, ctx: dict) -> dict:
    """4) TEKRAR EDİYOR MU? Tek seferlik gürültü ile sistematik arıza ayrımı."""
    anahtarlar = _anahtarlar(b)
    toplam, dosya_sayisi, ilk = 0, 0, YOK
    for p in _tarih_dosyalari(depo, b.get("_cozulmus")):
        k, n = _artefakt_satir(p, anahtarlar)
        if n:
            toplam += n
            dosya_sayisi += 1
            if ilk == YOK:
                ilk = k
    if toplam >= 2:
        return {"mercek": "tekrar", "hukum": "GERCEK_ARIZA", "guven": 7,
                "curutme_nedeni": "yok", "ilk_kanit": ilk,
                "gerekce": (f"aynı belirti {dosya_sayisi} artefaktta {toplam} kez "
                            "görünüyor → tek seferlik gürültü değil, sistematik")}
    if toplam == 1:
        return {"mercek": "tekrar", "hukum": "DOGRULANAMADI", "guven": 3,
                "curutme_nedeni": "yok", "ilk_kanit": ilk,
                "gerekce": "belirti yalnız bir artefaktta; tekrar kanıtı yok"}
    return {"mercek": "tekrar", "hukum": "YANLIS_POZITIF", "guven": 5,
            "curutme_nedeni": "tekrarlanamaz", "ilk_kanit": "yok",
            "gerekce": "hiçbir koşu artefaktında izi yok → tekrarlanamaz"}


def _mercek_celiski(b: dict, depo: Path, ctx: dict) -> dict:
    """5) ÇÜRÜTEN ARTEFAKT VAR MI? Aynı kod için TEMİZ kaydı iddiayı çürütür."""
    coz = b.get("_cozulmus")
    kod = _metin(b.get("kategori")).upper()
    if not coz or not kod:
        return {"mercek": "celiski", "hukum": "DOGRULANAMADI", "guven": 2,
                "curutme_nedeni": "yok", "ilk_kanit": YOK,
                "gerekce": "çelişki taraması için artefakt/kategori yetersiz"}
    metin = _oku_metin(Path(coz))
    temiz = re.search(rf'"kod"\s*:\s*"{re.escape(kod)}"[^}}]*"durum"\s*:\s*"TEMİZ"',
                      metin)
    ihlal = re.search(rf'"kod"\s*:\s*"{re.escape(kod)}"[^}}]*"durum"\s*:\s*"İHLAL"',
                      metin)
    if temiz and not ihlal:
        satir = metin[:temiz.start()].count("\n") + 1
        return {"mercek": "celiski", "hukum": "YANLIS_POZITIF", "guven": 7,
                "curutme_nedeni": "artefakt_yanlis_okunmus",
                "ilk_kanit": f"{Path(coz).name}:{satir}",
                "gerekce": (f"aynı artefakt {kod} kodunu TEMİZ olarak kaydetmiş ve "
                            "hiç İHLAL kaydı yok → iddia artefakta ters")}
    if ihlal:
        satir = metin[:ihlal.start()].count("\n") + 1
        return {"mercek": "celiski", "hukum": "GERCEK_ARIZA", "guven": 7,
                "curutme_nedeni": "yok", "ilk_kanit": f"{Path(coz).name}:{satir}",
                "gerekce": f"artefakt {kod} kodunu İHLAL olarak kaydetmiş; çelişki yok"}
    return {"mercek": "celiski", "hukum": "GERCEK_ARIZA", "guven": 4,
            "curutme_nedeni": "yok", "ilk_kanit": YOK,
            "gerekce": "iddiayı çürüten karşı artefakt bulunamadı (zayıf teyit)"}


_MERCEK_FN = {"artefakt": _mercek_artefakt, "yp_kural": _mercek_yp_kural,
              "tasarim": _mercek_tasarim, "tekrar": _mercek_tekrar,
              "celiski": _mercek_celiski}


def _oylari_say(b: dict, oylar: list, baglam: dict) -> dict:
    say = {"gercek_ariza": 0, "yanlis_pozitif": 0, "dogrulanamadi": 0}
    esle = {"GERCEK_ARIZA": "gercek_ariza", "YANLIS_POZITIF": "yanlis_pozitif",
            "DOGRULANAMADI": "dogrulanamadi"}
    for o in oylar:
        say[esle.get(_metin(o.get("hukum")).upper(), "dogrulanamadi")] += 1
    toplam = sum(say.values())
    en_cok = max(say, key=lambda k: say[k])
    cogunluk = say[en_cok] * 2 > toplam and en_cok != "dogrulanamadi"

    b["oy_dagilimi"] = say
    b["_oylar"] = oylar
    yp_oylari = [o for o in oylar if _metin(o.get("hukum")).upper() == "YANLIS_POZITIF"]
    b["curutme_nedenleri"] = sorted({_metin(o.get("curutme_nedeni") or "yok")
                                     for o in yp_oylari} - {"yok"})
    kurallar = [o.get("yp_kurali") for o in yp_oylari if o.get("yp_kurali") is not None]
    b["yp_kurali"] = max(set(kurallar), key=kurallar.count) if kurallar else None
    b["ilk_kanitlar"] = sorted({_metin(o.get("ilk_kanit")) for o in oylar
                                if o.get("ilk_kanit") not in (None, "", YOK, "yok")})

    if cogunluk:
        b["hukum"] = "gercek_ariza" if en_cok == "gercek_ariza" else "yanlis_pozitif"
        kazanan = [o for o in oylar
                   if esle.get(_metin(o.get("hukum")).upper()) == en_cok]
        b["bolunmus_oy"] = False
    else:
        tol = baglam.get("gurultu_toleransi", "kesinlik")
        kazanan = sorted(oylar, key=lambda o: -(_f(o.get("guven")) or 0))[:1]
        b["bolunmus_oy"] = True
        if tol == "kapsam":
            b["hukum"] = "gercek_ariza"
            b["dogrulama_hukmu"] = "elle_inceleme_gerek"
        else:
            b["hukum"] = "yanlis_pozitif"
            if tol == "sor":
                b["karar_bekliyor"] = True
    en_iyi = sorted(kazanan, key=lambda o: -(_f(o.get("guven")) or 0))
    b["guven"] = round(sum(_f(o.get("guven")) or 0 for o in en_iyi) / max(len(en_iyi), 1), 1)
    b["gerekce"] = _metin(en_iyi[0].get("gerekce")) if en_iyi else YOK
    if b.get("bolunmus_oy"):
        ek = ("(oy bölündü, kesinlik politikasıyla düşürüldü)"
              if baglam.get("gurultu_toleransi") != "kapsam"
              else "(oy bölündü, kapsam politikasıyla elle incelemeye bırakıldı)")
        b["gerekce"] = f"{b['gerekce']} {ek}"
    return b


def faz3_dogrula(durum: dict, args, durum_dizini: Path) -> dict:
    baglam, bulgular = durum["baglam"], durum["bulgular"]
    index = {b["id"]: b for b in bulgular}
    depo = Path(args.depo).expanduser().resolve()
    ctx = {
        "yp": _yp_kurallari_yukle(args.yp_kurallari),
        "gozlemci_py": depo / ".claude/skills/piramit-sistem/scripts/gozlemci.py",
        "piramit_py": depo / ".claude/skills/piramit-sistem/scripts/piramit.py",
    }
    dis_oylar = {}
    if args.oy_dosyasi:
        try:
            dis_oylar = json.loads(Path(args.oy_dosyasi).expanduser()
                                   .read_text(encoding="utf-8")) or {}
        except (OSError, ValueError) as e:
            dis_oylar = {}
            durum.setdefault("uyarilar", []).append(f"--oy-dosyasi okunamadı: {e}")

    ilerleme = _ilerleme_oku(durum_dizini)
    bitmis = list(ilerleme.get("parcalar_tamam") or [])
    for aid in durum["adaylar"]:
        b = index[aid]
        if aid in bitmis:
            kayitli = _parca_yukle(durum_dizini, aid)
            if kayitli:
                b.update(kayitli)
                continue
        # Konumu olmayan (dosya düzeyi) bulgu TEK oy alır: dosya taraması
        # pahalıdır ve oylamadan fayda görmez.
        n = 1 if not _metin(b.get("konum")).strip() else max(1, min(args.oy, len(MERCEKLER)))
        oylar = [_MERCEK_FN[m](b, depo, ctx) for m in MERCEKLER[:n]]
        for dis in (dis_oylar.get(aid) or []):
            if isinstance(dis, dict) and dis.get("hukum"):
                dis.setdefault("mercek", "dis_dogrulayici")
                oylar.append(dis)
        _oylari_say(b, oylar, baglam)
        b["_oy_sayisi"] = len(oylar)
        _parca_kaydet(durum_dizini, aid,
                      {k: v for k, v in b.items() if not k.startswith("_oy")})

    onaylanan = [b["id"] for b in bulgular if b.get("hukum") == "gercek_ariza"]
    return {"faz": 3, "baglam": baglam, "bulgular": bulgular,
            "adaylar": durum["adaylar"], "onaylanan": onaylanan,
            "yp_kaynaklari": ctx["yp"]["kaynaklar"],
            "yp_kural_sayisi": len(ctx["yp"]["kurallar"]),
            "bolunmus_oylar": [b["id"] for b in bulgular if b.get("bolunmus_oy")]}


# ==========================================================================
# FAZ 4 — ETKİ SIRALAMASI (yalnız onaylanan bulgular)
# ==========================================================================
def _on_kosul_turet(b: dict) -> list:
    beyan = [_metin(x) for x in (b.get("on_kosullar") or []) if _metin(x).strip()]
    metin = _alan_metni(b, ("baslik", "belirti", "tekrar_senaryosu", "konum"))
    turetilen = [etiket for desen, etiket in ON_KOSUL_ISARET
                 if re.search(desen, metin, re.IGNORECASE)]
    out = []
    for x in beyan + turetilen:
        if x not in out:
            out.append(x)
    return out


def _hafifletici(b: dict) -> str | None:
    coz = b.get("_cozulmus")
    if not coz:
        return None
    metin = _oku_metin(Path(coz))
    if '"muhurlendi": true' in metin or "DENETİM MÜHÜRÜ" in metin:
        return ("gözlemci mührü: kritik ihlalde EMİR kapatılır ve işlem "
                "kalitesi MÜHÜRLENİR (piramit.py fail-closed korkuluğu)")
    if "EMİR YOK" in metin and "gerekçe" in metin.lower():
        return "emir planı kapısı: aday gerekçeyle reddedildi (emir_plani.py)"
    return None


def _etki_eslesmesi(b: dict, baglam: dict) -> str | None:
    beyan = baglam.get("etki_modeli") or []
    if not beyan:
        return None
    metin = _alan_metni(b, ("kategori", "baslik", "belirti"))
    for madde in beyan:
        m = _metin(madde)
        anahtar = ETKI_SOZLUGU.get(m.strip().lower())
        if anahtar and re.search(anahtar, metin, re.IGNORECASE):
            return m
        kelimeler = [w for w in re.split(r"\W+", m) if len(w) > 4][:4]
        if kelimeler and any(re.search(re.escape(w), metin, re.IGNORECASE)
                             for w in kelimeler):
            return m
    return None


def faz4_sirala(durum: dict, args) -> dict:
    baglam, bulgular = durum["baglam"], durum["bulgular"]
    depo = Path(args.depo).expanduser().resolve()
    for b in bulgular:
        if b.get("hukum") != "gercek_ariza":
            b.update({"siddet": None, "siddet_etiketi": None, "siddet_hizasi": None,
                      "dogrulama_hukmu": b.get("dogrulama_hukmu"),
                      "on_kosullar": [], "tekrar_kosulu": None,
                      "etki_eslesmesi": None})
            continue
        kosullar = _on_kosul_turet(b)
        n = len(kosullar)
        elle = any("elle" in k or "kum havuzu" in k for k in kosullar)
        # Faz 4 ön koşulları KENDİ okur (kaynak: "You may Read/Grep the codebase
        # to check preconditions"): tekrar merceği Faz 3'te koşmadıysa burada
        # koşar — böylece --oy 1/3 seçimi ETKİ ölçümünü sakatlamaz.
        tekrar_oyu = next((o for o in (b.get("_oylar") or [])
                           if o.get("mercek") == "tekrar"), None)
        if tekrar_oyu is None:
            tekrar_oyu = _mercek_tekrar(b, depo, {})
            tekrar_oyu["mercek"] = "tekrar (Faz 4 ön koşul denetimi)"
            b["_faz4_tekrar"] = tekrar_oyu
            b.setdefault("ilk_kanitlar", [])
            k = _metin(tekrar_oyu.get("ilk_kanit"))
            if k not in ("", YOK, "yok") and k not in b["ilk_kanitlar"]:
                b["ilk_kanitlar"] = sorted(b["ilk_kanitlar"] + [k])
        kendiliginden = _metin(tekrar_oyu.get("hukum")) == "GERCEK_ARIZA"

        if elle or n >= 3:
            tekrar_kosulu = "elle_mudahaleyle"
        elif n >= 1:
            tekrar_kosulu = "belirli_veride"
        elif kendiliginden:
            tekrar_kosulu = "her_kosuda"
        else:
            tekrar_kosulu = "belirli_veride"

        s_kosul = "YÜKSEK" if n == 0 else ("ORTA" if n <= 2 else "DÜŞÜK")
        s_tekrar = {"her_kosuda": "YÜKSEK", "belirli_veride": "ORTA",
                    "elle_mudahaleyle": "DÜŞÜK"}[tekrar_kosulu]
        # İki kolon BAĞIMSIZ değerlendirilir, DÜŞÜK olan alınır.
        siddet = min((s_kosul, s_tekrar), key=lambda s: _SIDDET_RANK[s])

        eslesme = _etki_eslesmesi(b, baglam)
        if eslesme and _SIDDET_RANK[siddet] < 2:   # boost EN FAZLA bir basamak
            siddet = SIDDETLER[SIDDETLER.index(siddet) - 1]

        iddia = _metin(b.get("iddia_edilen_siddet")).upper()
        iddia_seviye = ("YÜKSEK" if re.search(r"İHLAL|IHLAL|HIGH|YÜKSEK|KRİTİK", iddia)
                        else "ORTA" if re.search(r"UYARI|MEDIUM|ORTA", iddia)
                        else "DÜŞÜK" if re.search(r"LOW|DÜŞÜK|TEMİZ", iddia) else None)
        if iddia_seviye is None:
            hiza = 0
        else:
            fark = _SIDDET_RANK[siddet] - _SIDDET_RANK[iddia_seviye]
            hiza = {2: 5, 1: 3, 0: 2, -1: -3, -2: -5}[fark]

        hafif = _hafifletici(b)
        if b.get("dogrulama_hukmu") == "elle_inceleme_gerek":
            hukum = "elle_inceleme_gerek"
        elif b.get("oy_dagilimi", {}).get("dogrulanamadi", 0) >= max(
                1, b.get("_oy_sayisi", 1) // 2) or (b.get("guven") or 0) < 5:
            hukum = "elle_inceleme_gerek"
        elif hafif:
            hukum = "hafifletilmis"
        else:
            hukum = "onarilabilir"

        b.update({"on_kosullar": kosullar, "tekrar_kosulu": tekrar_kosulu,
                  "siddet": siddet, "siddet_hizasi": hiza,
                  "etki_eslesmesi": eslesme, "dogrulama_hukmu": hukum,
                  "hafifletici": hafif,
                  "siddet_etiketi": siddet if "türetilmiş" in _metin(
                      baglam.get("siddet_standardi")) else
                      f"{baglam.get('siddet_standardi')}: {siddet}"})
        b["gerekce"] = (f"{b.get('gerekce', '')}\n\nETKİ: {n} ön koşul, tekrar "
                        f"koşulu {tekrar_kosulu} → {siddet}"
                        + (f"; etki modeli eşleşmesi '{eslesme}' bir basamak "
                           "yükseltti" if eslesme else "")
                        + (f"; hafifletici kontrol devrede → {hafif}" if hafif else ""))
    return {"faz": 4, "baglam": baglam, "bulgular": bulgular,
            "adaylar": durum["adaylar"], "onaylanan": durum["onaylanan"]}


# ==========================================================================
# FAZ 5 — YÖNLENDİR (sahip ipucu)
# ==========================================================================
def _git_sahip(depo: Path, dosya: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(depo), "log", "--format=%an", "-n", "50", "--", dosya],
            capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    adlar = [s.strip() for s in r.stdout.splitlines() if s.strip()]
    if not adlar:
        return None
    say = {}
    for a in adlar:
        say[a] = say.get(a, 0) + 1
    en = sorted(say.items(), key=lambda kv: -kv[1])[0]
    return f"en çok katkı veren: {en[0]} ({en[1]}/{len(adlar)} son commit)"


def faz5_yonlendir(durum: dict, args) -> dict:
    depo = Path(args.depo).expanduser().resolve()
    sahipler = []
    for ad in ("CODEOWNERS", "OWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"):
        p = depo / ad
        if p.exists():
            sahipler.append(p)
    for b in durum["bulgular"]:
        if b.get("hukum") != "gercek_ariza":
            b["sahip_ipucu"] = None
            continue
        dosya = _metin(b.get("dosya"))
        ipucu = None
        for p in sahipler:
            for satir in _oku_metin(p).splitlines():
                satir = satir.strip()
                if not satir or satir.startswith("#"):
                    continue
                parcalar = satir.split()
                desen = parcalar[0].strip("/")
                if desen and desen in dosya:
                    ipucu = f"CODEOWNERS: {parcalar[0]} → {' '.join(parcalar[1:])}"
        if not ipucu:
            g = _git_sahip(depo, dosya)
            if g:
                ipucu = f"{g}; CODEOWNERS kaydı yok"
        if not ipucu:
            ust = Path(dosya).parent
            motor = next((s for s in Path(dosya).parts if s.endswith(".py")), None)
            ipucu = (f"bileşen: {ust}/; CODEOWNERS ya da git geçmişi yok"
                     + (f"; motor {motor}" if motor else ""))
        b["sahip_ipucu"] = ipucu
    return {"faz": 5, "baglam": durum["baglam"], "bulgular": durum["bulgular"],
            "adaylar": durum["adaylar"], "onaylanan": durum["onaylanan"]}


# ==========================================================================
# FAZ 6 — ÇIKTI
# ==========================================================================
_HUKUM_SIRA = {"gercek_ariza": 0, "kopya": 1, "yanlis_pozitif": 2}


def _sirala(bulgular: list) -> list:
    def anahtar(b):
        h = _HUKUM_SIRA.get(b.get("hukum"), 3)
        if h == 0:
            return (0, -_SIDDET_RANK.get(b.get("siddet") or "DÜŞÜK", 0),
                    -(b.get("guven") or 0), -(b.get("siddet_hizasi") or 0), b["id"])
        return (h, 0, 0, 0, b["id"])
    return sorted(bulgular, key=anahtar)


def _temiz(b: dict) -> dict:
    return {k: v for k, v in b.items() if not k.startswith("_")}


def faz6_cikti(durum: dict, args, cikti_dizini: Path) -> dict:
    baglam = durum["baglam"]
    bulgular = _sirala(durum["bulgular"])
    gercek = [b for b in bulgular if b.get("hukum") == "gercek_ariza"]
    kopya = [b for b in bulgular if b.get("hukum") == "kopya"]
    yp = [b for b in bulgular if b.get("hukum") == "yanlis_pozitif"]
    elle = [b for b in gercek if b.get("dogrulama_hukmu") == "elle_inceleme_gerek"]
    siddet_say = {s: len([b for b in gercek if b.get("siddet") == s]) for s in SIDDETLER}

    rapor = {
        "sorusturma_tamam": True,
        "sorusturma_baglami": {
            "mod": baglam.get("mod"), "kapsam": baglam.get("kapsam"),
            "etki_modeli": baglam.get("etki_modeli"),
            "siddet_standardi": baglam.get("siddet_standardi"),
            "gurultu_toleransi": baglam.get("gurultu_toleransi"),
            "oy_sayisi": baglam.get("oy_sayisi"), "depo": baglam.get("depo"),
            "ariza_yolu": baglam.get("ariza_yolu"),
            "yp_kaynaklari": durum.get("yp_kaynaklari"),
            "yp_kural_sayisi": durum.get("yp_kural_sayisi"),
            "baglam_kaynagi": baglam.get("_baglam_kaynagi"),
        },
        "ozet": {
            "girdi_sayisi": len(bulgular), "kopyalar": len(kopya),
            "yanlis_pozitifler": len(yp), "gercek_arizalar": len(gercek),
            "elle_inceleme_gerek": len(elle), "siddete_gore": siddet_say,
            "bolunmus_oylar": durum.get("bolunmus_oylar") or [],
        },
        "bulgular": [_temiz(b) for b in bulgular],
        "varsayimlar": [
            "Şiddet ön koşul sayısı + tekrar koşulundan TÜRETİLİR; iddia edilen "
            "şiddet ayrıca `siddet_hizasi` ile puanlanır (-5..+5).",
            "Ön koşullar beyandan okunur; beyan yoksa metindeki mekanik "
            "işaretlerden türetilir (ON_KOSUL_ISARET) — bu bir SEZGİDİR, ölçüm değil.",
            "Etki modeli eşleşmesi şiddeti EN FAZLA bir basamak yükseltir.",
            "Doğrulama artefakt okumaya dayanır; hedef kodu ÇALIŞTIRILMAZ, "
            "boru hattı yeniden koşturulmaz, ağa çıkılmaz.",
            f"Mercek sırası {list(MERCEKLER)}; --oy N ilk N merceği koşturur.",
        ],
        "not": ("Her girdi bulgusu ÇIKTIDA TAM OLARAK BİR KEZ görünür; kopyalar "
                "`kopyasi` ile kanoniğe bağlanır. Hiçbir bulgu sessizce düşürülmez."),
    }
    json_yolu = cikti_dizini / "SORUSTURMA.json"
    _atomik_yaz(json_yolu, json.dumps(rapor, ensure_ascii=False, indent=2))

    md_yolu = cikti_dizini / "SORUSTURMA.md"
    ozet = (f"{len(bulgular)} kayıt → {len(kopya)} kopya, {len(yp)} yanlış pozitif, "
            f"{len(gercek)} gerçek arıza ({siddet_say['YÜKSEK']} yüksek / "
            f"{siddet_say['ORTA']} orta / {siddet_say['DÜŞÜK']} düşük), "
            f"{len(elle)} elle inceleme gerektiriyor")
    _atomik_yaz(md_yolu, "\n".join([
        "# Soruşturma Raporu", "", ozet, "",
        f"Bağlam: {baglam.get('mod')}; kapsam = {baglam.get('kapsam')}; "
        f"şiddet standardı = {baglam.get('siddet_standardi')}; "
        f"{baglam.get('oy_sayisi')} mercekli doğrulama; "
        f"gürültü toleransı = {baglam.get('gurultu_toleransi')}.", "",
        "## Şunlarla ilgilen", ""]))

    for b in gercek:
        kosullar = b.get("on_kosullar") or []
        parca = "\n".join([
            f"### [{b.get('siddet')}] {_metin(b.get('baslik'))}  ({b['id']})",
            f"`{_metin(b.get('dosya'))}:{_metin(b.get('konum')) or '—'}` | "
            f"{_metin(b.get('kategori'))} | iddia edilen "
            f"{_metin(b.get('iddia_edilen_siddet'))} "
            f"(hiza {b.get('siddet_hizasi'):+d}) | güven {b.get('guven')}/10",
            f"**Sahip:** {_metin(b.get('sahip_ipucu'))}",
            f"**Hüküm:** {b.get('dogrulama_hukmu')}, oylar {b.get('oy_dagilimi')}",
            f"**Ön koşullar ({len(kosullar)}):** " + (
                "\n" + "\n".join(f"- {k}" for k in kosullar) if kosullar
                else "yok (kendiliğinden tekrar ediyor)"),
            f"**Tekrar koşulu:** {b.get('tekrar_kosulu')}",
            f"**Etki modeli eşleşmesi:** {b.get('etki_eslesmesi') or 'yok'}",
            f"**Neden:** {_metin(b.get('gerekce'))}",
            f"**Kanıt izi:** {', '.join(b.get('ilk_kanitlar') or []) or YOK}",
            (f"**Yuttukları:** {', '.join(b.get('yuttuklari') or [])}"
             if b.get("yuttuklari") else ""),
            (f"**Öneri (girdiden):** {_metin(b.get('oneri'))}" if b.get("oneri") else ""),
            ("> Statik muhakeme sınırına dayandı; bu bulguyu ELLE tekrar üret "
             "(kontrollü koşu) — otomatik hüküm verilmedi."
             if b.get("dogrulama_hukmu") == "elle_inceleme_gerek" else ""),
            ""])
        _ekle(md_yolu, re.sub(r"\n{3,}", "\n\n", parca))

    if not gercek:
        _ekle(md_yolu, "_Doğrulamadan geçen arıza yok._\n")

    dusen = "\n".join(
        ["## Düşenler", "",
         "| id | başlık | dosya:konum | neden düştü |",
         "|----|--------|-------------|-------------|"] +
        [f"| {b['id']} | {_metin(b.get('baslik'))[:60]} | "
         f"{_metin(b.get('dosya'))}:{_metin(b.get('konum')) or '—'} | "
         + (f"{b['kopyasi']} kopyası" if b.get("hukum") == "kopya"
            else (("yerelleştirilemez: " + _metin(b.get('_yerellestirilemez')))
                  if b.get("_yerellestirilemez")
                  else ", ".join(b.get("curutme_nedenleri") or ["gerekçe yok"])
                  + (f" (YP kural {b['yp_kurali']})" if b.get("yp_kurali") else "")))
         + " |"
         for b in bulgular if b.get("hukum") in ("kopya", "yanlis_pozitif")] +
        ["", "_Düşen her kayıt gerekçesiyle listelenir; sessiz düşürme yoktur._"])
    _ekle(md_yolu, dusen)

    return {"rapor": rapor, "json": json_yolu, "md": md_yolu, "ozet": ozet,
            "gercek": gercek, "yp": yp, "kopya": kopya}


def _terminal_ozet(c: dict) -> str:
    r = c["rapor"]
    o, s = r["ozet"], r["ozet"]["siddete_gore"]
    ust = c["gercek"][0] if c["gercek"] else None
    nedenler = {}
    for b in r["bulgular"]:
        for n in (b.get("curutme_nedenleri") or []):
            nedenler[n] = nedenler.get(n, 0) + 1
    en = sorted(nedenler.items(), key=lambda kv: -kv[1])[:3]
    return "\n".join([
        f"Soruşturma tamam: {o['girdi_sayisi']} kayıt → {o['gercek_arizalar']} "
        f"gerçek arıza, {o['yanlis_pozitifler']} yanlış pozitif, "
        f"{o['kopyalar']} kopya.", "",
        f"  YÜKSEK: {s['YÜKSEK']}   " + (f"{_metin(ust.get('baslik'))[:52]} "
                                         f"[{_metin(ust.get('sahip_ipucu'))[:40]}]"
                                         if ust else ""),
        f"  ORTA:   {s['ORTA']}",
        f"  DÜŞÜK:  {s['DÜŞÜK']}",
        f"  Elle inceleme gerek: {o['elle_inceleme_gerek']}", "",
        "  En sık çürütme nedeni: " + (", ".join(f"{k}×{v}" for k, v in en) or YOK), "",
        f"Yazıldı: {c['md']} ve {c['json']}"])


# ==========================================================================
# Orkestrasyon
# ==========================================================================
def kostur(args) -> dict:
    cikti_dizini = Path(args.cikti_dizini).expanduser().resolve()
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    durum_dizini = _sinirla(cikti_dizini / ".sorusturma-state", bitis="-state")

    ilerleme = _ilerleme_oku(durum_dizini)
    yeniden = None
    if args.taze or ilerleme.get("durum") in ("yok", "tamam", "bozuk"):
        _durum_sifirla(durum_dizini)
        durum_dizini.mkdir(parents=True, exist_ok=True)
    elif ilerleme.get("durum") == "koşuyor":
        yeniden = int(ilerleme.get("faz_tamam", -1))

    durum, basla = {}, 0
    if yeniden is not None and yeniden >= 0:
        birlestirilmis = {}
        for n in range(0, yeniden + 1):
            p = _faz_yukle(durum_dizini, n)
            if p:
                birlestirilmis.update(p)
        if birlestirilmis:
            durum, basla = birlestirilmis, yeniden + 1
            print(f"Kontrol noktasından devam: Faz {yeniden} tamam "
                  f"({durum_dizini}/faz{yeniden}.json)", file=sys.stderr)

    if basla <= 0:
        durum = {"faz": 0, "baglam": faz0_mod(args)}
        _faz_kaydet(durum_dizini, 0, "mulakat", durum)
    if basla <= 1:
        durum = faz1_al(args, durum["baglam"])
        _faz_kaydet(durum_dizini, 1, "al", durum)
    if basla <= 2:
        durum = faz2_tekille(durum)
        _faz_kaydet(durum_dizini, 2, "tekillestir", durum)
    if basla <= 3:
        durum = faz3_dogrula(durum, args, durum_dizini)
        _faz_kaydet(durum_dizini, 3, "dogrula", durum,
                    parcalar=list(_ilerleme_oku(durum_dizini).get("parcalar_tamam") or []))
    if basla <= 4:
        durum = faz4_sirala(durum, args)
        _faz_kaydet(durum_dizini, 4, "sirala", durum)
    if basla <= 5:
        durum = faz5_yonlendir(durum, args)
        _faz_kaydet(durum_dizini, 5, "yonlendir", durum)

    for ad in ("SORUSTURMA.md",):
        p = cikti_dizini / ad
        if p.exists():
            p.unlink()
    c = faz6_cikti(durum, args, cikti_dizini)
    _ilerleme_yaz(durum_dizini, durum="tamam", faz=6, parcalar=[])
    return c


# ==========================================================================
# ÖZ-TEST
# ==========================================================================
def self_test() -> int:
    global _KOK
    _KOK = SKILL_DIR.resolve()
    ornek = SKILL_DIR / "ornek"
    args = argparse.Namespace(
        ariza=str(ornek / "ornek_ariza.json"), auto=True, oy=3,
        depo=str(SKILL_DIR), yp_kurallari=None, taze=True,
        cikti_dizini=str(ornek), baglam=None, oy_dosyasi=None)
    c = kostur(args)
    r = c["rapor"]
    idler = {b["id"]: b for b in r["bulgular"]}

    T = []

    def kontrol(ad, kosul, ayrinti=""):
        T.append((ad, bool(kosul), ayrinti))

    kontrol("6 kayıt alındı", r["ozet"]["girdi_sayisi"] == 6,
            f"girdi_sayisi={r['ozet']['girdi_sayisi']}")
    kontrol("a001 gerçek arıza", idler["a001"]["hukum"] == "gercek_ariza",
            idler["a001"]["hukum"])
    kontrol("a002 a001'in kopyası",
            idler["a002"]["hukum"] == "kopya" and idler["a002"].get("kopyasi") == "a001",
            f"{idler['a002']['hukum']}/{idler['a002'].get('kopyasi')}")
    kontrol("a003 gerçek arıza", idler["a003"]["hukum"] == "gercek_ariza",
            idler["a003"]["hukum"])
    kontrol("a004 YP kural 1 ile düştü (kapı = tasarım)",
            idler["a004"]["hukum"] == "yanlis_pozitif"
            and idler["a004"].get("yp_kurali") == 1,
            f"{idler['a004']['hukum']}/kural={idler['a004'].get('yp_kurali')}")
    kontrol("a005 YP kural 2 ile düştü (BEKLE = hüküm)",
            idler["a005"]["hukum"] == "yanlis_pozitif"
            and idler["a005"].get("yp_kurali") == 2,
            f"{idler['a005']['hukum']}/kural={idler['a005'].get('yp_kurali')}")
    kontrol("a006 yerelleştirilemez → kanit_yok",
            idler["a006"]["hukum"] == "yanlis_pozitif"
            and "kanit_yok" in (idler["a006"].get("curutme_nedenleri") or []),
            _metin(idler["a006"].get("curutme_nedenleri")))
    kontrol("her bulgu tam bir kez raporda", len(r["bulgular"]) == 6)
    kontrol("çok mercekli oylama koştu (≥3 oy)",
            sum(idler["a001"]["oy_dagilimi"].values()) >= 3,
            _metin(idler["a001"]["oy_dagilimi"]))
    kontrol("şiddet türetildi (a001 YÜKSEK)", idler["a001"].get("siddet") == "YÜKSEK",
            _metin(idler["a001"].get("siddet")))
    kontrol("a003 ön koşullu → ORTA", idler["a003"].get("siddet") == "ORTA",
            f"{idler['a003'].get('siddet')} kosul={idler['a003'].get('on_kosullar')}")
    kontrol("a003 şiddet hizası negatif (iddia şişirilmiş)",
            (idler["a003"].get("siddet_hizasi") or 0) < 0,
            _metin(idler["a003"].get("siddet_hizasi")))
    kontrol("sahip ipucu atandı", bool(idler["a001"].get("sahip_ipucu")),
            _metin(idler["a001"].get("sahip_ipucu")))
    kontrol("kanıt izi dosya:satır taşıyor",
            any(":" in x for x in (idler["a001"].get("ilk_kanitlar") or [])),
            _metin(idler["a001"].get("ilk_kanitlar")))
    md = _oku_metin(c["md"])
    kontrol("MD 'Şunlarla ilgilen' bölümü var", "## Şunlarla ilgilen" in md)
    kontrol("MD 'Düşenler' bölümü var", "## Düşenler" in md)
    kontrol("düşenler tabloda gerekçeli",
            all(f"| {i} |" in md for i in ("a002", "a004", "a005", "a006")))
    kontrol("JSON dosyası yazıldı", Path(c["json"]).exists())
    kontrol("kontrol noktası tamamlandı",
            _ilerleme_oku(Path(args.cikti_dizini) / ".sorusturma-state")
            .get("durum") == "tamam")

    # devam (resume) testi: faz3'e kadar koşmuş bir durumdan devam edilebiliyor mu
    dd = Path(args.cikti_dizini) / ".sorusturma-state"
    _ilerleme_yaz(dd, durum="koşuyor", faz=3,
                  parcalar=list(_ilerleme_oku(dd).get("parcalar_tamam") or []))
    args2 = argparse.Namespace(**{**vars(args), "taze": False})
    c2 = kostur(args2)
    kontrol("kontrol noktasından devam aynı sonucu verdi",
            c2["rapor"]["ozet"] == r["ozet"],
            f"{c2['rapor']['ozet']} vs {r['ozet']}")

    print("=" * 72)
    print("SORUŞTURMA ÖZ-TESTİ")
    print("=" * 72)
    for ad, ok, ayrinti in T:
        print(f"  {'GEÇTİ ' if ok else 'DÜŞTÜ '} {ad}" + (f"  [{ayrinti}]" if ayrinti else ""))
    print("-" * 72)
    print(_terminal_ozet(c))
    dusen = [ad for ad, ok, _ in T if not ok]
    print("-" * 72)
    print(f"SONUÇ: {len(T) - len(dusen)}/{len(T)} test geçti"
          + (f" — DÜŞEN: {dusen}" if dusen else " — TAMAMI GEÇTİ"))
    return 1 if dusen else 0


# ==========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Soruşturma — boru hattı arızası için kök-neden protokolü")
    ap.add_argument("ariza", nargs="?", help="arıza kaydı dosyası ya da dizini")
    ap.add_argument("--auto", action="store_true",
                    help="mülakatı atla, kesinlik-yanlı varsayılanları kullan")
    ap.add_argument("--oy", type=int, default=3,
                    help="bulgu başına doğrulayıcı mercek sayısı (varsayılan 3)")
    ap.add_argument("--depo", default=".", help="artefaktların kökü (salt-okunur)")
    ap.add_argument("--yp-kurallari", help="ek yanlış-pozitif kural dosyası")
    ap.add_argument("--taze", action="store_true",
                    help="kontrol noktasını yok say, Faz 0'dan başla")
    ap.add_argument("--cikti-dizini", default=".",
                    help="SORUSTURMA.json/.md ve durum dizininin yeri")
    ap.add_argument("--baglam", help="mülakat cevapları (JSON) — interaktif mod")
    ap.add_argument("--oy-dosyasi",
                    help="dış doğrulayıcı oyları (JSON: {id: [oy, ...]})")
    ap.add_argument("--self-test", action="store_true", help="öz-test koş")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()
    if not a.ariza:
        ap.error("arıza yolu gerekli (ya da --self-test)")
    if a.oy < 1:
        ap.error("--oy en az 1 olmalı")
    c = kostur(a)
    print(_terminal_ozet(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
