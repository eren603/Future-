#!/usr/bin/env python3
"""beceri_dogrula.py — SKILL.md sozlesme dogrulayicisi.

Kaynak: `skill-creator/scripts/quick_validate.py` (103 satir, sha 67cf57034020)
        `skill-creator/scripts/improve_description.py` (247 satir, sha 87d864570220)
        `skill-creator/SKILL.md` (485 satir, sha dcd4803e61e9)
        `template/SKILL.md` (6 satir, sha eb685d91de03)

Her kural iki etiketten birini tasir:
  KAYNAK   — yukaridaki dosyalarda BIREBIR bulunan kural (satir atifli).
  DEPO EKI — kaynakta YOK; bu depoya ozgu, gerekcesi KANIT.md'de yazili.

Bagimlilik: yalnizca stdlib + pyyaml. jsonschema KURULU DEGIL, kullanilmaz.

Kipler:
  --beceri YOL        tek beceri dizinini dogrula
  --depo YOL          YOL/.claude/skills altindaki TUM becerileri dogrula
                      (SALT-OKUNUR: hicbir dosyayi degistirmez)
  --self-test         gecici dizinde sahte beceri agaci kurup vakalari sinar
                      (takipli hicbir dosyaya YAZMAZ)
  --ornek-tazele YOL  ornek/ ciktilarini BILEREK tazelemek icin ayri bayrak

Cikis kodu: 0 = HATA yok, 1 = en az bir HATA (fail-closed), 2 = kullanim hatasi.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - ortamda pyyaml kurulu
    print("HATA: pyyaml gerekli (import yaml basarisiz).", file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------------------
# Kaynaktan BIREBIR tasinan sabitler
# ---------------------------------------------------------------------------

# quick_validate.py:42 — KAYNAK liste (yayin dogrulayicisinin dar kumesi)
KAYNAK_ALLOWED_PROPERTIES = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}

# DEPO EKI (kanitla genisletildi, keyfi degil): quick_validate.py `anthropics/
# skills` YAYIN dogrulayicisidir; Claude Code'un CALISMA ZAMANI kabul ettigi
# alan kumesi daha genistir. Kanit — `argument-hint` resmi Anthropic
# becerilerinde kullaniliyor:
#   defending-code-reference-harness/.claude/skills/triage/SKILL.md:10
#   .../threat-model/SKILL.md:13   .../vuln-scan/SKILL.md:11
#   .../dnr-respond/SKILL.md:10    .../quickstart/SKILL.md:10
#   .../patch/SKILL.md:11
# `tools` ise ajan dosyalarinda gecer (cwc-long-running-agents/.../evaluator.md:4).
# Kaynak listesini DARALTMADIK, genislettik; daraltma bu depodaki gecerli
# becerileri haksiz dusururdu (dogrulanmis yanlis pozitif: sorusturma).
DEPO_EK_PROPERTIES = {"argument-hint", "tools"}

ALLOWED_PROPERTIES = KAYNAK_ALLOWED_PROPERTIES | DEPO_EK_PROPERTIES

# quick_validate.py:65 -> re.match(r'^[a-z0-9-]+$', name)
NAME_DESENI = re.compile(r"^[a-z0-9-]+$")

# quick_validate.py:70-71 -> "Maximum is 64 characters."
NAME_MAKS = 64

# quick_validate.py:83-84 -> "Maximum is 1024 characters."
# improve_description.py:132 -> "There is a hard limit of 1024 characters"
DESC_MAKS = 1024

# quick_validate.py:91-92 -> "Maximum is 500 characters."
COMPAT_MAKS = 500

# improve_description.py:132 -> "not be more than about 100-200 words"
DESC_KELIME_ONERI = 200

# quick_validate.py:27
FM_DESENI = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# DEPO EKI: bu deponun tetikleyici sozlesmesi (22 becerinin 20'sinden olculdu)
DEPO_TETIKLEYICI_IFADELER = (
    "OTOMATİK devreye girer",
    "slash komutu gerekmez",
)
DEPO_TETIKLEYICI_LISTE = "Tetikleyici"

# DEPO EKI: katlanmis blok onerisi esigi
KATLANMIS_ONERI_ESIGI = 200

KURAL_KAYNAGI = {
    # kod: (etiket, kaynak atfi)
    "YOK_SKILL_MD": ("KAYNAK", "quick_validate.py:17-19"),
    "YOK_FRONTMATTER": ("KAYNAK", "quick_validate.py:23-24"),
    "GECERSIZ_FM_BICIM": ("KAYNAK", "quick_validate.py:27-29"),
    "FM_YAML_HATASI": ("KAYNAK", "quick_validate.py:38-39"),
    "FM_SOZLUK_DEGIL": ("KAYNAK", "quick_validate.py:36-37"),
    "BEKLENMEYEN_ANAHTAR": ("KAYNAK", "quick_validate.py:44-50"),
    "EKSIK_NAME": ("KAYNAK", "quick_validate.py:53-54"),
    "EKSIK_DESCRIPTION": ("KAYNAK", "quick_validate.py:55-56"),
    "NAME_METIN_DEGIL": ("KAYNAK", "quick_validate.py:60-61"),
    "NAME_KEBAB_DEGIL": ("KAYNAK", "quick_validate.py:65-66"),
    "NAME_TIRE_HATASI": ("KAYNAK", "quick_validate.py:67-68"),
    "NAME_COK_UZUN": ("KAYNAK", "quick_validate.py:70-71"),
    "DESC_METIN_DEGIL": ("KAYNAK", "quick_validate.py:75-76"),
    "DESC_ACI_PARANTEZ": ("KAYNAK", "quick_validate.py:80-81"),
    "DESC_COK_UZUN": ("KAYNAK", "quick_validate.py:83-84"),
    "COMPAT_METIN_DEGIL": ("KAYNAK", "quick_validate.py:89-90"),
    "COMPAT_COK_UZUN": ("KAYNAK", "quick_validate.py:91-92"),
    "DESC_COK_KELIME": ("KAYNAK", "improve_description.py:132"),
    "DESC_NIYET_YOK": ("KAYNAK", "skill-creator/SKILL.md:67"),
    "AYRISMA_IKI_NOKTA": ("DEPO EKI", "kaynakta YOK — KANIT.md D1"),
    "NAME_DIZIN_UYUSMAZ": ("DEPO EKI", "kaynakta YOK — KANIT.md D2"),
    "MOTOR_OZTEST_YOK": ("DEPO EKI", "kaynakta YOK — KANIT.md D3"),
    "TETIKLEYICI_SOZLESME": ("DEPO EKI", "kaynakta YOK — KANIT.md D4"),
    "KATLANMIS_BLOK_ONER": ("DEPO EKI", "kaynakta YOK — KANIT.md D5"),
}

HATA = "HATA"
UYARI = "UYARI"


class Bulgu:
    __slots__ = ("kod", "seviye", "mesaj")

    def __init__(self, kod: str, seviye: str, mesaj: str) -> None:
        if kod not in KURAL_KAYNAGI:
            raise KeyError("etiketsiz kural kodu: " + kod)
        self.kod = kod
        self.seviye = seviye
        self.mesaj = mesaj

    @property
    def etiket(self) -> str:
        return KURAL_KAYNAGI[self.kod][0]

    @property
    def kaynak(self) -> str:
        return KURAL_KAYNAGI[self.kod][1]

    def sozluk(self) -> dict:
        return {
            "kod": self.kod,
            "seviye": self.seviye,
            "etiket": self.etiket,
            "kaynak": self.kaynak,
            "mesaj": self.mesaj,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return "<Bulgu " + self.kod + " " + self.seviye + ">"


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------

NL = "\n"


def _description_ham_satiri(fm_ham: str) -> str | None:
    """Frontmatter ham metninde `description:` satirini dondur (yoksa None)."""
    for satir in fm_ham.split(NL):
        if satir.startswith("description:"):
            return satir
    return None


def _duz_skaler_iki_nokta(fm_ham: str) -> str | None:
    """DEPO EKI: duz YAML skaleri icinde `": "` var mi?

    `description: Motor: scripts/x.py` bicimindeki bir satir YAML'da
    "mapping values are not allowed in this context" hatasi verir; frontmatter
    AYRISMAZ ve beceri HIC YUKLENMEZ. Bu depoda gercekten yasandi.
    Katlanmis blok (`>-`) / literal blok (`|`) / tirnakli skaler muaftir.
    """
    satir = _description_ham_satiri(fm_ham)
    if satir is None:
        return None
    deger = satir[len("description:"):].strip()
    if deger in (">", "|", ">-", "|-", ">+", "|+", ""):
        return None
    if deger[:1] in ('"', "'"):
        return None
    if ": " in deger:
        return deger
    return None


def _motor_oztestli(py: Path) -> bool:
    """DEPO EKI: motor `--self-test` bayragi tasiyor mu?"""
    try:
        metin = py.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "--self-test" in metin


def _kelime_say(metin: str) -> int:
    return len(metin.split())


# ---------------------------------------------------------------------------
# Cekirdek dogrulama
# ---------------------------------------------------------------------------

def dogrula(beceri_yolu) -> list[Bulgu]:
    """Bir beceri dizinini dogrula, Bulgu listesi dondur (bos = temiz)."""
    beceri_yolu = Path(beceri_yolu)
    bulgular: list[Bulgu] = []

    # --- KAYNAK quick_validate.py:17-19 -----------------------------------
    skill_md = beceri_yolu / "SKILL.md"
    if not skill_md.exists():
        bulgular.append(Bulgu("YOK_SKILL_MD", HATA, "SKILL.md not found"))
        return bulgular

    icerik = skill_md.read_text(encoding="utf-8")

    # --- KAYNAK quick_validate.py:23-24 -----------------------------------
    if not icerik.startswith("---"):
        bulgular.append(Bulgu("YOK_FRONTMATTER", HATA, "No YAML frontmatter found"))
        return bulgular

    # --- KAYNAK quick_validate.py:27-29 -----------------------------------
    eslesme = FM_DESENI.match(icerik)
    if not eslesme:
        bulgular.append(Bulgu("GECERSIZ_FM_BICIM", HATA, "Invalid frontmatter format"))
        return bulgular

    fm_ham = eslesme.group(1)

    # --- DEPO EKI: ayrismayi ONCEDEN teshis et ----------------------------
    iki_nokta = _duz_skaler_iki_nokta(fm_ham)

    # --- KAYNAK quick_validate.py:34-39 -----------------------------------
    try:
        fm = yaml.safe_load(fm_ham)
    except yaml.YAMLError as e:
        if iki_nokta is not None:
            bulgular.append(Bulgu(
                "AYRISMA_IKI_NOKTA", HATA,
                "description duz YAML skaleri icinde ': ' geciyor -> frontmatter "
                "AYRISMIYOR, beceri HIC YUKLENMEZ. Cozum: katlanmis blok kullan "
                "(description: >- ve govdeyi 2 bosluk girintili yaz). "
                "Sorunlu deger: " + iki_nokta[:80],
            ))
        bulgular.append(Bulgu(
            "FM_YAML_HATASI", HATA,
            "Invalid YAML in frontmatter: " + str(e).replace(NL, " ")[:200],
        ))
        return bulgular

    # --- KAYNAK quick_validate.py:36-37 -----------------------------------
    if not isinstance(fm, dict):
        bulgular.append(Bulgu(
            "FM_SOZLUK_DEGIL", HATA, "Frontmatter must be a YAML dictionary"))
        return bulgular

    # --- DEPO EKI: ayristi ama yine de riskli yazim ------------------------
    if iki_nokta is not None:
        bulgular.append(Bulgu(
            "AYRISMA_IKI_NOKTA", HATA,
            "description duz skalerinde ': ' var — bu yazim YAML'da kirilgan; "
            "katlanmis blok (>-) kullan. Sorunlu deger: " + iki_nokta[:80],
        ))

    # --- KAYNAK quick_validate.py:44-50 -----------------------------------
    beklenmeyen = set(fm.keys()) - ALLOWED_PROPERTIES
    if beklenmeyen:
        bulgular.append(Bulgu(
            "BEKLENMEYEN_ANAHTAR", HATA,
            "Unexpected key(s) in SKILL.md frontmatter: "
            + ", ".join(sorted(str(k) for k in beklenmeyen))
            + ". Allowed properties are: "
            + ", ".join(sorted(ALLOWED_PROPERTIES)),
        ))

    # --- KAYNAK quick_validate.py:53-56 -----------------------------------
    if "name" not in fm:
        bulgular.append(Bulgu("EKSIK_NAME", HATA, "Missing 'name' in frontmatter"))
    if "description" not in fm:
        bulgular.append(Bulgu(
            "EKSIK_DESCRIPTION", HATA, "Missing 'description' in frontmatter"))

    # --- name ------------------------------------------------------------
    name = fm.get("name", "")
    if "name" in fm:
        if not isinstance(name, str):
            bulgular.append(Bulgu(
                "NAME_METIN_DEGIL", HATA,
                "Name must be a string, got " + type(name).__name__))
            name = ""
        else:
            name = name.strip()

    if isinstance(name, str) and name:
        # KAYNAK quick_validate.py:65-66
        if not NAME_DESENI.match(name):
            bulgular.append(Bulgu(
                "NAME_KEBAB_DEGIL", HATA,
                "Name '" + name + "' should be kebab-case (lowercase letters, "
                "digits, and hyphens only)"))
        # KAYNAK quick_validate.py:67-68
        if name.startswith("-") or name.endswith("-") or "--" in name:
            bulgular.append(Bulgu(
                "NAME_TIRE_HATASI", HATA,
                "Name '" + name + "' cannot start/end with hyphen or contain "
                "consecutive hyphens"))
        # KAYNAK quick_validate.py:70-71
        if len(name) > NAME_MAKS:
            bulgular.append(Bulgu(
                "NAME_COK_UZUN", HATA,
                "Name is too long (" + str(len(name)) + " characters). "
                "Maximum is " + str(NAME_MAKS) + " characters."))
        # DEPO EKI: dizin adiyla esitlik
        if name != beceri_yolu.name:
            bulgular.append(Bulgu(
                "NAME_DIZIN_UYUSMAZ", HATA,
                "frontmatter name='" + name + "' ile dizin adi '"
                + beceri_yolu.name + "' AYNI DEGIL."))

    # --- description -----------------------------------------------------
    description = fm.get("description", "")
    if "description" in fm:
        if not isinstance(description, str):
            bulgular.append(Bulgu(
                "DESC_METIN_DEGIL", HATA,
                "Description must be a string, got " + type(description).__name__))
            description = ""
        else:
            description = description.strip()

    if isinstance(description, str) and description:
        # KAYNAK quick_validate.py:80-81
        if "<" in description or ">" in description:
            bulgular.append(Bulgu(
                "DESC_ACI_PARANTEZ", HATA,
                "Description cannot contain angle brackets (< or >)"))
        # KAYNAK quick_validate.py:83-84
        if len(description) > DESC_MAKS:
            bulgular.append(Bulgu(
                "DESC_COK_UZUN", HATA,
                "Description is too long (" + str(len(description))
                + " characters). Maximum is " + str(DESC_MAKS) + " characters."))
        # KAYNAK improve_description.py:132 (yumusak — "about 100-200 words")
        kelime = _kelime_say(description)
        if kelime > DESC_KELIME_ONERI:
            bulgular.append(Bulgu(
                "DESC_COK_KELIME", UYARI,
                "description " + str(kelime) + " kelime; kaynak 'not be more than "
                "about 100-200 words' diyor (yumusak oneri, sert sinir degil)."))
        # KAYNAK skill-creator/SKILL.md:67 — "When to trigger, what it does"
        if "Use " not in description and "kullan" not in description.lower() \
                and "devreye girer" not in description and "Use" != description[:3]:
            bulgular.append(Bulgu(
                "DESC_NIYET_YOK", UYARI,
                "description NE ZAMAN tetiklenecegini soylemiyor gibi gorunuyor "
                "(kaynak: 'When to trigger, what it does')."))
        # DEPO EKI: bu deponun tetikleyici sozlesmesi
        eksik_ifade = [i for i in DEPO_TETIKLEYICI_IFADELER if i not in description]
        if eksik_ifade:
            bulgular.append(Bulgu(
                "TETIKLEYICI_SOZLESME", UYARI,
                "depo sozlesmesi ifadesi eksik: " + ", ".join(eksik_ifade)))
        elif DEPO_TETIKLEYICI_LISTE not in description:
            bulgular.append(Bulgu(
                "TETIKLEYICI_SOZLESME", UYARI,
                "description 'Tetikleyici kelimeler (TR/EN): ...' listesi tasimiyor"))
        # DEPO EKI: uzun description icin katlanmis blok
        ham_satir = _description_ham_satiri(fm_ham)
        if ham_satir is not None and len(description) > KATLANMIS_ONERI_ESIGI:
            deger = ham_satir[len("description:"):].strip()
            if deger not in (">", "|", ">-", "|-", ">+", "|+"):
                bulgular.append(Bulgu(
                    "KATLANMIS_BLOK_ONER", UYARI,
                    "uzun description tek satirda; depo geleneği katlanmis blok "
                    "(description: >-) — 22 beceriden 21'i boyle."))

    # --- compatibility (KAYNAK quick_validate.py:87-92) -------------------
    compatibility = fm.get("compatibility", "")
    if compatibility:
        if not isinstance(compatibility, str):
            bulgular.append(Bulgu(
                "COMPAT_METIN_DEGIL", HATA,
                "Compatibility must be a string, got "
                + type(compatibility).__name__))
        elif len(compatibility) > COMPAT_MAKS:
            bulgular.append(Bulgu(
                "COMPAT_COK_UZUN", HATA,
                "Compatibility is too long (" + str(len(compatibility))
                + " characters). Maximum is " + str(COMPAT_MAKS) + " characters."))

    # --- DEPO EKI: motor oz-testi ----------------------------------------
    scripts_dizin = beceri_yolu / "scripts"
    if scripts_dizin.is_dir():
        py_dosyalar = sorted(
            p for p in scripts_dizin.glob("*.py") if p.name != "__init__.py")
        if py_dosyalar:
            ayri_oztest = any(p.name == "self_test.py" for p in py_dosyalar)
            bayrakli = any(_motor_oztestli(p) for p in py_dosyalar)
            if not (ayri_oztest or bayrakli):
                bulgular.append(Bulgu(
                    "MOTOR_OZTEST_YOK", HATA,
                    "scripts/ altinda " + str(len(py_dosyalar)) + " motor var ama "
                    "ne '--self-test' bayrakli motor ne de scripts/self_test.py "
                    "bulundu (denetlenemeyen 'GECTI' sayilmaz)."))

    return bulgular


# ---------------------------------------------------------------------------
# Raporlama
# ---------------------------------------------------------------------------

def rapor_sozluk(beceri_yolu, bulgular: list[Bulgu]) -> dict:
    hatalar = [b for b in bulgular if b.seviye == HATA]
    return {
        "beceri": Path(beceri_yolu).name,
        "yol": str(beceri_yolu),
        "sonuc": "TEMIZ" if not hatalar else "HATALI",
        "hata_sayisi": len(hatalar),
        "uyari_sayisi": len(bulgular) - len(hatalar),
        "bulgular": [b.sozluk() for b in bulgular],
    }


def rapor_metin(raporlar: list[dict]) -> str:
    satirlar: list[str] = []
    toplam_hata = 0
    toplam_uyari = 0
    for r in raporlar:
        toplam_hata += r["hata_sayisi"]
        toplam_uyari += r["uyari_sayisi"]
        bas = "OK  " if r["sonuc"] == "TEMIZ" else "FAIL"
        satirlar.append(
            bas + "  " + r["beceri"].ljust(26)
            + " hata=" + str(r["hata_sayisi"])
            + " uyari=" + str(r["uyari_sayisi"]))
        for b in r["bulgular"]:
            satirlar.append(
                "        [" + b["seviye"] + "/" + b["etiket"] + "] "
                + b["kod"] + " (" + b["kaynak"] + ")")
            satirlar.append("            " + b["mesaj"])
    satirlar.append("")
    satirlar.append(
        "TOPLAM: " + str(len(raporlar)) + " beceri, "
        + str(toplam_hata) + " HATA, " + str(toplam_uyari) + " UYARI")
    satirlar.append(
        "Cikis kodu: " + ("1 (fail-closed)" if toplam_hata else "0"))
    return NL.join(satirlar)


def depo_becerileri(depo: Path) -> list[Path]:
    kok = depo / ".claude" / "skills"
    if not kok.is_dir():
        kok = depo
    return sorted(p for p in kok.iterdir() if p.is_dir() and not p.name.startswith("."))


# ---------------------------------------------------------------------------
# Oz-test — GECICI dizinde calisir, takipli hicbir dosyaya yazmaz
# ---------------------------------------------------------------------------

GECERLI_SKILL_MD = """---
name: ornek-beceri
description: >-
  Ornek beceri sozlesmesi. Bir soru ornek, deneme, sinama ile ilgili oldugunda
  OTOMATİK devreye girer — slash komutu gerekmez. Calisan motor:
  scripts/motor.py. Tetikleyici kelimeler (TR/EN): ornek, deneme, sinama, test.
---

# Ornek beceri

## Ne zaman devreye girer (tetikleyici gerekmez)

Ornek amacli.

## Kosum

```bash
python3 .claude/skills/ornek-beceri/scripts/motor.py --self-test
```
"""

MOTOR_OZTESTLI = (
    "import sys" + NL
    + "if '--self-test' in sys.argv:" + NL
    + "    print('ok')" + NL
    + "    sys.exit(0)" + NL
)

MOTOR_OZTESTSIZ = "print('motor')" + NL


def _beceri_kur(kok: Path, ad: str, skill_md: str, motor: str | None = None) -> Path:
    d = kok / ad
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(skill_md, encoding="utf-8")
    if motor is not None:
        (d / "scripts" / "motor.py").write_text(motor, encoding="utf-8")
    else:
        shutil.rmtree(d / "scripts")
    return d


def _fm(name: str, desc_satiri: str) -> str:
    return "---" + NL + "name: " + name + NL + desc_satiri + NL + "---" + NL + NL + "# Govde" + NL


def _katlanmis(desc: str) -> str:
    govde = NL.join("  " + p for p in desc.split(NL))
    return "description: >-" + NL + govde


def self_test() -> int:
    """Sahte beceri agaci kurar, her bozuk vakanin YAKALANDIGINI sinar."""
    gecici = Path(tempfile.mkdtemp(prefix="beceri_dogrula_oztest_"))
    satirlar: list[str] = []
    gecen = 0
    dusen = 0

    sozlesme = (
        "Sinama becerisi. Bir soru sinama ile ilgili oldugunda OTOMATİK devreye "
        "girer — slash komutu gerekmez. Tetikleyici kelimeler (TR/EN): sinama.")

    try:
        vakalar: list[tuple[str, Path, set[str], set[str]]] = []

        # 0 — GECERLI referans vaka: hicbir HATA cikmamali
        d = _beceri_kur(gecici, "ornek-beceri", GECERLI_SKILL_MD, MOTOR_OZTESTLI)
        vakalar.append(("gecerli-beceri-temiz", d, set(), set()))

        # 1 — `": "` yuzunden AYRISMAYAN frontmatter
        bozuk = (
            "---" + NL
            + "name: iki-nokta" + NL
            + "description: Motor: scripts/motor.py — bu satir YAML'i kirar." + NL
            + "---" + NL + NL + "# Govde" + NL)
        d = _beceri_kur(gecici, "iki-nokta", bozuk, MOTOR_OZTESTLI)
        vakalar.append(("iki-nokta-ayrismiyor", d,
                        {"AYRISMA_IKI_NOKTA", "FM_YAML_HATASI"}, set()))

        # 2 — 1024'u asan description
        uzun = sozlesme + " " + ("uzatma " * 200)
        d = _beceri_kur(gecici, "uzun-desc",
                        _fm("uzun-desc", _katlanmis(uzun)), MOTOR_OZTESTLI)
        vakalar.append(("description-1024-asiyor", d, {"DESC_COK_UZUN"}, set()))

        # 3 — name != dizin adi
        d = _beceri_kur(gecici, "dizin-adi",
                        _fm("baska-ad", _katlanmis(sozlesme)), MOTOR_OZTESTLI)
        vakalar.append(("name-dizin-uyusmaz", d, {"NAME_DIZIN_UYUSMAZ"}, set()))

        # 4 — eksik description
        eksik = "---" + NL + "name: eksik-desc" + NL + "---" + NL + NL + "# Govde" + NL
        d = _beceri_kur(gecici, "eksik-desc", eksik, MOTOR_OZTESTLI)
        vakalar.append(("description-eksik", d, {"EKSIK_DESCRIPTION"}, set()))

        # 5 — gecersiz name karakteri (kebab-case degil)
        d = _beceri_kur(gecici, "Gecersiz_Name",
                        _fm("Gecersiz_Name", _katlanmis(sozlesme)), MOTOR_OZTESTLI)
        vakalar.append(("name-gecersiz-karakter", d, {"NAME_KEBAB_DEGIL"}, set()))

        # 6 — --self-test'i olmayan motor
        d = _beceri_kur(gecici, "oztestsiz",
                        _fm("oztestsiz", _katlanmis(sozlesme)), MOTOR_OZTESTSIZ)
        vakalar.append(("motor-oztestsiz", d, {"MOTOR_OZTEST_YOK"}, set()))

        # 7 — SKILL.md yok
        d = gecici / "skillmd-yok"
        (d / "scripts").mkdir(parents=True, exist_ok=True)
        vakalar.append(("skill-md-yok", d, {"YOK_SKILL_MD"}, set()))

        # 8 — frontmatter hic yok
        d = _beceri_kur(gecici, "fm-yok", "# Sadece govde" + NL, MOTOR_OZTESTLI)
        vakalar.append(("frontmatter-yok", d, {"YOK_FRONTMATTER"}, set()))

        # 9 — kapanmayan frontmatter
        acik = "---" + NL + "name: fm-acik" + NL + "description: x" + NL
        d = _beceri_kur(gecici, "fm-acik", acik, MOTOR_OZTESTLI)
        vakalar.append(("frontmatter-kapanmiyor", d, {"GECERSIZ_FM_BICIM"}, set()))

        # 10 — beklenmeyen anahtar
        ek = ("---" + NL + "name: fazla-anahtar" + NL
              + _katlanmis(sozlesme) + NL
              + "author: kimse" + NL + "---" + NL + NL + "# Govde" + NL)
        d = _beceri_kur(gecici, "fazla-anahtar", ek, MOTOR_OZTESTLI)
        vakalar.append(("beklenmeyen-anahtar", d, {"BEKLENMEYEN_ANAHTAR"}, set()))

        # 11 — description'da aci parantez
        aci = sozlesme + " Cikti: INVALID: [mesaj] at <yol>."
        d = _beceri_kur(gecici, "aci-parantez",
                        _fm("aci-parantez", _katlanmis(aci)), MOTOR_OZTESTLI)
        vakalar.append(("aci-parantez", d, {"DESC_ACI_PARANTEZ"}, set()))

        # 12 — name 64 karakteri asiyor
        uzun_ad = "a" * 65
        d = _beceri_kur(gecici, uzun_ad,
                        _fm(uzun_ad, _katlanmis(sozlesme)), MOTOR_OZTESTLI)
        vakalar.append(("name-64-asiyor", d, {"NAME_COK_UZUN"}, set()))

        # 13 — ardisik tire
        d = _beceri_kur(gecici, "cift--tire",
                        _fm("cift--tire", _katlanmis(sozlesme)), MOTOR_OZTESTLI)
        vakalar.append(("name-ardisik-tire", d, {"NAME_TIRE_HATASI"}, set()))

        # 14 — compatibility 500'u asiyor
        uzun_uyum = "x" * 501
        yol = ("---" + NL + "name: uyum-uzun" + NL + _katlanmis(sozlesme) + NL
               + "compatibility: " + uzun_uyum + NL + "---" + NL + NL + "# Govde" + NL)
        d = _beceri_kur(gecici, "uyum-uzun", yol, MOTOR_OZTESTLI)
        vakalar.append(("compatibility-500-asiyor", d, {"COMPAT_COK_UZUN"}, set()))

        # 15 — frontmatter sozluk degil
        liste = "---" + NL + "- a" + NL + "- b" + NL + "---" + NL + NL + "# Govde" + NL
        d = _beceri_kur(gecici, "fm-liste", liste, MOTOR_OZTESTLI)
        vakalar.append(("frontmatter-sozluk-degil", d, {"FM_SOZLUK_DEGIL"}, set()))

        # 16 — name metin degil
        sayi = ("---" + NL + "name: 12345" + NL + _katlanmis(sozlesme) + NL
                + "---" + NL + NL + "# Govde" + NL)
        d = _beceri_kur(gecici, "name-sayi", sayi, MOTOR_OZTESTLI)
        vakalar.append(("name-metin-degil", d, {"NAME_METIN_DEGIL"}, set()))

        # 17 — eksik name
        eksik_n = ("---" + NL + _katlanmis(sozlesme) + NL + "---" + NL
                   + NL + "# Govde" + NL)
        d = _beceri_kur(gecici, "name-eksik", eksik_n, MOTOR_OZTESTLI)
        vakalar.append(("name-eksik", d, {"EKSIK_NAME"}, set()))

        # 18 — depo tetikleyici sozlesmesi eksik (UYARI)
        yalin = ("Kisa bir aciklama; bu depo sozlesmesinin ifadelerini tasimiyor. "
                 "Use this skill for testing.")
        d = _beceri_kur(gecici, "sozlesmesiz",
                        _fm("sozlesmesiz", _katlanmis(yalin)), MOTOR_OZTESTLI)
        vakalar.append(("tetikleyici-sozlesme-uyari", d,
                        {"TETIKLEYICI_SOZLESME"}, set()))

        # --- vakalari kostur --------------------------------------------
        for ad, yol, beklenen, beklenmeyen in vakalar:
            bulgular = dogrula(yol)
            kodlar = {b.kod for b in bulgular}
            hatalar = {b.kod for b in bulgular if b.seviye == HATA}
            sorun = []
            for k in beklenen:
                if k not in kodlar:
                    sorun.append("beklenen kod YAKALANMADI: " + k)
            for k in beklenmeyen:
                if k in kodlar:
                    sorun.append("beklenmeyen kod cikti: " + k)
            if not beklenen and hatalar:
                sorun.append("temiz olmasi gereken vakada HATA: "
                             + ", ".join(sorted(hatalar)))
            if sorun:
                dusen += 1
                satirlar.append("FAIL  " + ad)
                for s in sorun:
                    satirlar.append("        " + s)
                satirlar.append("        cikan kodlar: "
                                + (", ".join(sorted(kodlar)) or "(yok)"))
            else:
                gecen += 1
                satirlar.append(
                    "ok    " + ad.ljust(30)
                    + " kodlar=" + (",".join(sorted(kodlar)) or "-"))

        # --- kendini muaf tutmama: bu becerinin KENDISI de gecmeli -------
        kendi = Path(__file__).resolve().parent.parent
        if (kendi / "SKILL.md").exists():
            kendi_bulgular = dogrula(kendi)
            kendi_hata = [b for b in kendi_bulgular if b.seviye == HATA]
            if kendi_hata:
                dusen += 1
                satirlar.append("FAIL  kendi-SKILL.md-kendi-dogrulayicisindan-gecmeli")
                for b in kendi_hata:
                    satirlar.append("        " + b.kod + ": " + b.mesaj)
            else:
                gecen += 1
                satirlar.append(
                    "ok    kendi-SKILL.md-kendi-dogrulayicisindan-gecmeli".ljust(36)
                    + " uyari=" + str(len(kendi_bulgular)))
        else:
            satirlar.append("ATLANDI  kendi SKILL.md bulunamadi (" + str(kendi) + ")")

    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    satirlar.append("")
    satirlar.append("OZ-TEST: " + str(gecen + dusen) + " vaka, "
                    + str(gecen) + " gecti, " + str(dusen) + " dustu")
    cikti = NL.join(satirlar)
    print(cikti)
    return 0 if dusen == 0 else 1


# ---------------------------------------------------------------------------
# ornek/ tazeleme — AYRI bayrak (oz-test asla buraya yazmaz)
# ---------------------------------------------------------------------------

def ornek_tazele(hedef: Path, depo: Path) -> int:
    hedef.mkdir(parents=True, exist_ok=True)

    # 1) oz-test ciktisi
    import io
    from contextlib import redirect_stdout
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        kod = self_test()
    (hedef / "self_test_cikti.txt").write_text(
        tampon.getvalue().rstrip() + NL + "exit=" + str(kod) + NL, encoding="utf-8")

    # 2) depodaki gercek becerilere karsi denetim
    raporlar = [rapor_sozluk(b, dogrula(b)) for b in depo_becerileri(depo)]
    (hedef / "depo_denetim.txt").write_text(
        rapor_metin(raporlar) + NL, encoding="utf-8")
    (hedef / "depo_denetim.json").write_text(
        json.dumps(raporlar, ensure_ascii=False, indent=2) + NL, encoding="utf-8")

    print("ornek tazelendi: " + str(hedef))
    return 0


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="beceri_dogrula.py",
        description="SKILL.md sozlesme dogrulayicisi (kaynak: skill-creator)")
    ap.add_argument("--beceri", help="tek beceri dizini")
    ap.add_argument("--depo", help="depo koku; .claude/skills altini tarar (salt-okunur)")
    ap.add_argument("--self-test", action="store_true",
                    help="gecici dizinde oz-test (takipli dosyaya YAZMAZ)")
    ap.add_argument("--ornek-tazele", metavar="DIZIN", default=None,
                    help="ornek/ ciktilarini BILEREK tazele (ayri bayrak)")
    ap.add_argument("--json", action="store_true", help="JSON rapor")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()

    if a.ornek_tazele:
        depo = Path(a.depo) if a.depo else Path(__file__).resolve().parents[4]
        return ornek_tazele(Path(a.ornek_tazele), depo)

    if a.beceri:
        yollar = [Path(a.beceri)]
    elif a.depo:
        yollar = depo_becerileri(Path(a.depo))
    else:
        ap.print_usage(sys.stderr)
        print("HATA: --beceri, --depo, --self-test ya da --ornek-tazele gerekli.",
              file=sys.stderr)
        return 2

    raporlar = [rapor_sozluk(y, dogrula(y)) for y in yollar]
    if a.json:
        print(json.dumps(raporlar, ensure_ascii=False, indent=2))
    else:
        print(rapor_metin(raporlar))
    return 1 if any(r["hata_sayisi"] for r in raporlar) else 0


if __name__ == "__main__":
    sys.exit(main())
