#!/usr/bin/env python3
"""
Bu deponun beceri/kanca/ajan katmanini MEKANIK olarak denetler.

Kaynak: fs/scripts/check.py (219 satir, sha256 c19d681ddba4...) — o dosyanin
uc isi bu deponun yapisina cevrildi:
  1. manifest lint      -> .claude/skills/*/SKILL.md frontmatter + .claude/settings.json
  2. referans cozumleme -> SKILL.md govdesinde adi gecen dosyalar gercekten var mi
  3. drift/kodlama      -> py_compile, YAML/JSON/CSV ayristirma, UTF-8, +x, oz-test

Cikis kodlari:
  0 = temiz
  1 = en az bir HATA
  2 = HATA yok ama en az bir DENETLENEMEDI (fail-closed: denetlenemeyen GECTI sayilmaz)
  3 = bagimlilik yok (pyyaml)

Kullanim:
  butunluk.py [--depo YOL] [--json] [--oztest-kos | --oztest-kosma]
  butunluk.py --self-test
"""
import argparse
import csv
import io
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- bagimlilik kapisi -------------------------------------------------------
# Kaynak check.py:53-57 ayni deseni kullanir (import yaml -> yoksa exit).
try:
    import yaml
except ImportError:  # pragma: no cover
    print("HATA: pyyaml gerekiyor (pip install pyyaml)", file=sys.stderr)
    sys.exit(3)

# --- sabitler ----------------------------------------------------------------
# [KAYNAK] quick_validate.py:82-84 "Check description length (max 1024 characters
# per spec)" + improve_description.py:132 "There is a hard limit of 1024
# characters - descriptions over that will be truncated".
AZAMI_ACIKLAMA = 1024
# [KAYNAK] quick_validate.py:68-69 "Check name length (max 64 characters per spec)".
AZAMI_AD = 64
# [KAYNAK] quick_validate.py:64 kebab-case deseni.
AD_DESENI = re.compile(r"^[a-z0-9-]+$")

# [VARSAYIM] Bu depoda her yeni becerinin KANIT.md'si beklenir (CLAUDE.md
# "kaynak izlenebilirligi" kurali). Kaynak check.py:184'te ayni sekilde
# ("agent.yaml", "README.md", "steering-examples.json") zorunlu dosya listesi var.
ZORUNLU_BECERI_DOSYALARI = ("SKILL.md", "KANIT.md")

# Oz-test kosulmayacak motorlar. Gerekce: bunlar piramit boru hattini calistirir
# ve engine/state/ ile hafiza/ sicillerini DEGISTIRIR. Denetim aracinin yan
# etkisi olamaz -> GECTI degil, DENETLENEMEDI olarak raporlanir (fail-closed).
OZTEST_YASAK = {
    "piramit-sistem/scripts/piramit.py",
    "piramit-sistem/scripts/self_test.py",
    "piramit-sistem/scripts/saglik.py",
}

# Kosuda uretilen (depoda durmayan) artefakt yollari — referans cozumlemede
# "eksik dosya" degil, "kosu ciktisi" sayilir.
KOSU_ARTEFAKTI = re.compile(r"(^|/)(state|girdi|hafiza)/")

# `jsonl` alternatifi `json`dan ONCE gelmeli ve sonda sinir olmali: aksi halde
# `ornek/olcum_ornek.jsonl` -> `ornek/olcum_ornek.json` diye kirpilip VAR OLMAYAN
# bir dosya raporlanir (bu arac ilk gercek kosusunda tam bunu yapti).
REF_DESENI = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:[A-Za-z0-9_-]+/)+[A-Za-z0-9_.-]+"
    r"\.(?:py|yaml|yml|csv|jsonl|json))(?![A-Za-z0-9_])"
)

# check.py:196 ile ayni fikir: tarama disi dizinler.
ATLA_DIZIN = {".git", "node_modules", "__pycache__", ".venv", "venv"}

HATA = "HATA"
DENETLENEMEDI = "DENETLENEMEDI"
BILGI = "BILGI"


class Denetci:
    """Bulgulari toplar. check.py:23 `errors: list[str]` + `checked` sayacinin
    seviyelendirilmis karsiligi."""

    def __init__(self, depo: Path):
        self.depo = Path(depo).resolve()
        self.bulgular: list[dict] = []
        self.denetlenen = 0

    # check.py:64-65 `rel()` karsiligi.
    def rel(self, p) -> str:
        try:
            return str(Path(p).resolve().relative_to(self.depo))
        except ValueError:
            return str(p)

    def ekle(self, seviye: str, kod: str, yol, mesaj: str) -> None:
        self.bulgular.append(
            {"seviye": seviye, "kod": kod, "yol": self.rel(yol), "mesaj": mesaj}
        )

    def hata(self, kod, yol, mesaj):
        self.ekle(HATA, kod, yol, mesaj)

    def denetlenemedi(self, kod, yol, mesaj):
        self.ekle(DENETLENEMEDI, kod, yol, mesaj)

    def bilgi(self, kod, yol, mesaj):
        self.ekle(BILGI, kod, yol, mesaj)

    def say(self, seviye: str) -> int:
        return sum(1 for b in self.bulgular if b["seviye"] == seviye)

    def kodlar(self) -> set:
        return {b["kod"] for b in self.bulgular if b["seviye"] != BILGI}


# --- yardimcilar -------------------------------------------------------------
def _frontmatter(metin: str):
    """(meta, hata_mesaji) dondurur.

    check.py:95-105 deseni: once '---' ile basliyor mu, sonra split('---', 2),
    sonra yaml.safe_load.
    """
    if not metin.startswith("---"):
        return None, "bas kisimda '---' yok"
    try:
        _, fm, _ = metin.split("---", 2)
    except ValueError:
        return None, "frontmatter kapanmamis (ikinci '---' yok)"
    try:
        meta = yaml.safe_load(fm)
    except yaml.YAMLError as e:
        return None, f"YAML ayristirma: {e}"
    if not isinstance(meta, dict):
        return None, "frontmatter bir YAML sozlugu degil"
    return meta, None


def _oku(p: Path):
    """(metin, hata). UTF-8 cozulemeyen dosya denetlenemez -> fail-closed.

    check.py:188-211 bayt seviyesinde kodlama kapisi kurar (PowerShell/ASCII).
    Bu depo Turkce ve UTF-8 oldugu icin kapi ASCII'ye degil UTF-8 cozulebilirlige
    ve sahte BOM'a bakar. [SAPMA — KANIT.md #12]
    """
    try:
        ham = p.read_bytes()
    except OSError as e:
        return None, f"okunamadi: {e}"
    if ham.startswith(b"\xef\xbb\xbf"):
        return None, "UTF-8 BOM ile basliyor (YAML frontmatter'i bozar)"
    try:
        return ham.decode("utf-8"), None
    except UnicodeDecodeError as e:
        return None, f"UTF-8 olarak cozulemedi: {e}"


def _beceri_dizinleri(depo: Path):
    kok = depo / ".claude" / "skills"
    if not kok.is_dir():
        return []
    return sorted(d for d in kok.iterdir() if d.is_dir() and d.name not in ATLA_DIZIN)


# --- 1. SKILL.md manifest lint ----------------------------------------------
def denet_beceriler(d: Denetci) -> None:
    dizinler = _beceri_dizinleri(d.depo)
    if not dizinler:
        d.denetlenemedi("BECERI_YOK", d.depo / ".claude/skills", "beceri dizini bulunamadi")
        return
    for bd in dizinler:
        # check.py:181-186 "required files per managed-agent" karsiligi.
        for gerekli in ZORUNLU_BECERI_DOSYALARI:
            if not (bd / gerekli).is_file():
                d.hata("EKSIK_DOSYA", bd / gerekli, f"{gerekli} yok")

        sm = bd / "SKILL.md"
        if not sm.is_file():
            continue
        d.denetlenen += 1
        metin, oku_hata = _oku(sm)
        if oku_hata:
            d.hata("KODLAMA", sm, oku_hata)
            continue

        meta, fm_hata = _frontmatter(metin)
        if fm_hata:
            d.hata("FRONTMATTER", sm, fm_hata)
            continue

        # check.py:101-103: name + description zorunlu.
        for k in ("name", "description"):
            if k not in meta:
                d.hata("FRONTMATTER", sm, f"'{k}' alani yok")

        ad = meta.get("name")
        if isinstance(ad, str):
            ad = ad.strip()
            if ad != bd.name:
                d.hata(
                    "AD_UYUSMAZ",
                    sm,
                    f"name '{ad}' dizin adi '{bd.name}' ile ayni degil",
                )
            if len(ad) > AZAMI_AD:
                d.hata("AD_UZUN", sm, f"name {len(ad)} karakter, azami {AZAMI_AD}")
            if not AD_DESENI.match(ad):
                d.hata("AD_DESEN", sm, f"name '{ad}' kebab-case degil")
        elif ad is not None:
            d.hata("FRONTMATTER", sm, f"name bir metin degil: {type(ad).__name__}")

        ac = meta.get("description")
        if isinstance(ac, str):
            n = len(ac.strip())
            if n > AZAMI_ACIKLAMA:
                d.hata(
                    "ACIKLAMA_UZUN",
                    sm,
                    f"description {n} karakter, sert sinir {AZAMI_ACIKLAMA} "
                    f"(asan kisim kirpilir)",
                )
            if "<" in ac or ">" in ac:
                d.hata("ACIKLAMA_ACI_PARANTEZ", sm, "description '<' ya da '>' iceriyor")
        elif ac is not None:
            d.hata("FRONTMATTER", sm, f"description bir metin degil: {type(ac).__name__}")


def _alintisiz(metin: str) -> str:
    """Blok-alinti (`> `) satirlarini referans taramasindan cikar.

    Gerekce: bu port `check_refs`i beyan edilmis YAML alanindan DUZ METNE
    tasidi (sapma S3). Duz metinde bir SKILL.md, KAYNAK deponun kodunu birebir
    alintilayabilir — ornegin `> # ... consumed by scripts/validate.py`. O yol
    kaynak deponundur, BU deponun referansi degildir; alintiyi bozmadan
    dogru siniflandirmanin tek yolu alinti satirlarini atlamaktir.
    (Kod citleri atlanmaz: bu depoda gercek calistirma ornekleri citler icinde.)
    """
    return "\n".join("" if s.lstrip().startswith(">") else s
                     for s in metin.splitlines())


# --- 2. referans cozumleme (check.py:109-136 check_refs karsiligi) -----------
def denet_referanslar(d: Denetci) -> None:
    beceri_kok = d.depo / ".claude" / "skills"
    for bd in _beceri_dizinleri(d.depo):
        sm = bd / "SKILL.md"
        if not sm.is_file():
            continue
        metin, oku_hata = _oku(sm)
        if oku_hata:
            continue
        for tok in sorted(set(REF_DESENI.findall(_alintisiz(metin)))):
            if "*" in tok:
                continue  # glob kalibi — tek dosyaya isaret etmiyor
            d.denetlenen += 1
            adaylar = [bd / tok, d.depo / tok, beceri_kok / tok]
            if any(a.exists() for a in adaylar):
                continue
            if KOSU_ARTEFAKTI.search(tok):
                d.bilgi("REF_KOSU_ARTEFAKTI", sm, f"{tok} — kosuda uretilir, depoda yok")
                continue
            ilk = tok.split("/")[0]
            icerde = (d.depo / ilk).exists() or (beceri_kok / ilk).exists() or (bd / ilk).exists()
            if icerde:
                d.hata("REF_COZUMLENMEDI", sm, f"{tok} -> dosya yok")
            else:
                d.bilgi(
                    "REF_DIS_KAYNAK",
                    sm,
                    f"{tok} — bu depoda olmayan bir agac; dogrulanamadi",
                )


# --- 3. .claude/settings.json + kancalar -------------------------------------
def _komut_yollari(deger, cikti: list) -> None:
    if isinstance(deger, dict):
        for k, v in deger.items():
            if k == "command" and isinstance(v, str):
                cikti.append(v)
            else:
                _komut_yollari(v, cikti)
    elif isinstance(deger, list):
        for v in deger:
            _komut_yollari(v, cikti)


def denet_settings(d: Denetci) -> None:
    sp = d.depo / ".claude" / "settings.json"
    if not sp.is_file():
        d.denetlenemedi("SETTINGS_YOK", sp, ".claude/settings.json bulunamadi")
        return
    d.denetlenen += 1
    try:
        veri = json.loads(sp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        # check.py:88-89 ile ayni: JSON ayristirma hatasi.
        d.hata("JSON_AYRISTIRMA", sp, f"gecersiz JSON: {e}")
        return

    komutlar: list = []
    _komut_yollari(veri, komutlar)
    if not komutlar:
        d.bilgi("KANCA_YOK", sp, "settings.json icinde kanca komutu yok")
    for komut in komutlar:
        m = re.search(r'\$CLAUDE_PROJECT_DIR/([A-Za-z0-9_./-]+)', komut)
        if not m:
            d.denetlenemedi(
                "KANCA_YOL_COZULMEDI", sp, f"komuttan dosya yolu cikarilamadi: {komut}"
            )
            continue
        goreli = m.group(1)
        hedef = d.depo / goreli
        d.denetlenen += 1
        if not hedef.is_file():
            d.hata("KANCA_DOSYA_YOK", sp, f"{goreli} diskte yok")
            continue
        # Yorumlayici ile cagriliyorsa (+x) gerekmez; dogrudan cagriliyorsa gerekir.
        yorumlayici = re.match(r'^\s*(python3?|bash|sh|zsh|node)\s', komut) is not None
        calistirilabilir = os.access(hedef, os.X_OK)
        if not yorumlayici and not calistirilabilir:
            d.hata(
                "KANCA_CALISTIRILAMAZ",
                hedef,
                "dogrudan cagriliyor ama +x yok (chmod +x gerekir)",
            )
        elif yorumlayici and not calistirilabilir:
            d.bilgi(
                "KANCA_YORUMLAYICI",
                hedef,
                "+x yok ama yorumlayici ile cagriliyor — sorun degil",
            )


# --- 4. .claude/agents/*.md (check.py:92-105 karsiligi) ----------------------
def denet_ajanlar(d: Denetci) -> None:
    ad = d.depo / ".claude" / "agents"
    if not ad.is_dir():
        d.bilgi("AJAN_YOK", ad, ".claude/agents dizini yok")
        return
    for md in sorted(ad.glob("*.md")):
        d.denetlenen += 1
        metin, oku_hata = _oku(md)
        if oku_hata:
            d.hata("KODLAMA", md, oku_hata)
            continue
        meta, fm_hata = _frontmatter(metin)
        if fm_hata:
            d.hata("AJAN_FRONTMATTER", md, fm_hata)
            continue
        for k in ("name", "description"):
            if k not in meta:
                d.hata("AJAN_FRONTMATTER", md, f"'{k}' alani yok")
        ajan_ad = meta.get("name")
        if isinstance(ajan_ad, str) and ajan_ad.strip() != md.stem:
            d.hata(
                "AJAN_AD_UYUSMAZ",
                md,
                f"name '{ajan_ad.strip()}' dosya adi '{md.stem}' ile ayni degil",
            )


# --- 5. Python derleme + veri dosyasi ayristirma -----------------------------
def _taranacak(depo: Path, kalip: str):
    for p in sorted(depo.rglob(kalip)):
        if any(part in ATLA_DIZIN for part in p.parts):
            continue
        yield p


def denet_python(d: Denetci) -> None:
    kok = d.depo / ".claude"
    if not kok.is_dir():
        return
    # cfile bir GECICI dosyaya yazilir: os.devnull'a yazmak platformda
    # basarisiz olur ve her dosya sahte DENETLENEMEDI uretir (oz-testin
    # "temiz agac" negatif kontrolu bu hatayi yakaladi).
    with tempfile.TemporaryDirectory(prefix="butunluk_pyc_") as gec:
        hedef_pyc = str(Path(gec) / "d.pyc")
        for py in _taranacak(kok, "*.py"):
            d.denetlenen += 1
            try:
                # quiet=1 SART: CPython'da quiet=2 istisnayi HIC yukseltmez
                # (doraise=True olsa bile sessizce return eder) -> her dosya
                # "derlendi" sanilir. Oz-test bu hatayi yakaladi.
                py_compile.compile(str(py), cfile=hedef_pyc, doraise=True, quiet=1)
            except py_compile.PyCompileError as e:
                d.hata("DERLENMEDI", py, f"py_compile: {e.msg.strip().splitlines()[0]}")
            except (OSError, ValueError) as e:
                d.denetlenemedi("DERLEME_KOSULAMADI", py, str(e))


def denet_veri_dosyalari(d: Denetci) -> None:
    kok = d.depo / ".claude"
    if not kok.is_dir():
        return
    # check.py:69-75 (YAML) + :83-89 (JSON) karsiligi, CSV eklenmistir.
    for p in _taranacak(kok, "*.yaml"):
        d.denetlenen += 1
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as e:
            d.hata("YAML_AYRISTIRMA", p, str(e).splitlines()[0])
    for p in _taranacak(kok, "*.yml"):
        d.denetlenen += 1
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as e:
            d.hata("YAML_AYRISTIRMA", p, str(e).splitlines()[0])
    for p in _taranacak(kok, "*.json"):
        d.denetlenen += 1
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            d.hata("JSON_AYRISTIRMA", p, str(e).splitlines()[0])
    for p in _taranacak(kok, "*.csv"):
        d.denetlenen += 1
        try:
            metin = p.read_text(encoding="utf-8")
            satirlar = list(csv.reader(io.StringIO(metin)))
        except (csv.Error, UnicodeDecodeError) as e:
            d.hata("CSV_AYRISTIRMA", p, str(e).splitlines()[0])
            continue
        if not satirlar:
            d.hata("CSV_BOS", p, "CSV bos")
            continue
        genislik = len(satirlar[0])
        for i, satir in enumerate(satirlar[1:], start=2):
            if satir and len(satir) != genislik:
                d.hata(
                    "CSV_SUTUN",
                    p,
                    f"satir {i}: {len(satir)} sutun, baslik {genislik} sutun",
                )
                break


# --- 6. oz-test kapisi -------------------------------------------------------
def _oztest_bayragi_var(py: Path) -> bool:
    try:
        metin = py.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "--self-test" in metin


def denet_oztestler(d: Denetci, kos: bool) -> None:
    """Her becerinin oz-test yolu var mi ve exit 0 veriyor mu.

    Bu depoda iki gelenek yan yana yasiyor: (a) motorun kendi --self-test
    bayragi, (b) ayri scripts/self_test.py dosyasi. Ikisi de kabul edilir;
    hicbiri yoksa DENETLENEMEDI (fail-closed).
    """
    for bd in _beceri_dizinleri(d.depo):
        sd = bd / "scripts"
        if not sd.is_dir():
            continue
        pys = sorted(p for p in sd.glob("*.py") if p.name != "__init__.py")
        if not pys:
            continue

        adaylar = []
        yasakli = 0
        for py in pys:
            anahtar = f"{bd.name}/scripts/{py.name}"
            if anahtar in OZTEST_YASAK:
                yasakli += 1
                d.denetlenemedi(
                    "OZTEST_YASAK",
                    py,
                    "boru hattini calistirir ve sicilleri degistirir — "
                    "denetim araci kosturamaz (GECTI sayilmaz)",
                )
                continue
            if py.name == "self_test.py":
                adaylar.append((py, []))
            elif _oztest_bayragi_var(py):
                adaylar.append((py, ["--self-test"]))

        # Adaylarin hepsi yasak listesindeyse bu "oz-test yok" DEGILDIR;
        # zaten OZTEST_YASAK olarak raporlandi — ikinci kez suclamayalim.
        if not adaylar and yasakli:
            continue

        if not adaylar:
            d.denetlenemedi(
                "OZTEST_YOK",
                sd,
                "ne --self-test bayrakli motor ne de scripts/self_test.py var",
            )
            continue

        if not kos:
            for py, _ in adaylar:
                d.bilgi("OZTEST_KOSULMADI", py, "oz-test bulundu ama kosulmadi (--oztest-kosma)")
            continue

        for py, argv in adaylar:
            d.denetlenen += 1
            try:
                sonuc = subprocess.run(
                    [sys.executable, str(py)] + argv,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=str(d.depo),
                )
            except subprocess.TimeoutExpired:
                d.denetlenemedi("OZTEST_ZAMAN_ASIMI", py, "180 sn icinde bitmedi")
                continue
            except OSError as e:
                d.denetlenemedi("OZTEST_KOSULAMADI", py, str(e))
                continue
            if sonuc.returncode != 0:
                kuyruk = (sonuc.stderr or sonuc.stdout or "").strip().splitlines()
                son = kuyruk[-1][:200] if kuyruk else "(cikti yok)"
                d.hata("OZTEST_DUSTU", py, f"exit {sonuc.returncode}: {son}")


# --- calistirici -------------------------------------------------------------
def denetle(depo: Path, oztest_kos: bool = True) -> Denetci:
    d = Denetci(depo)
    denet_beceriler(d)
    denet_referanslar(d)
    denet_settings(d)
    denet_ajanlar(d)
    denet_python(d)
    denet_veri_dosyalari(d)
    denet_oztestler(d, kos=oztest_kos)
    return d


def rapor_metin(d: Denetci) -> str:
    s = []
    hata_n = d.say(HATA)
    dn_n = d.say(DENETLENEMEDI)
    bilgi_n = d.say(BILGI)
    for seviye, im in ((HATA, "x"), (DENETLENEMEDI, "?"), (BILGI, "i")):
        grup = [b for b in d.bulgular if b["seviye"] == seviye]
        if not grup:
            continue
        s.append(f"--- {seviye} ({len(grup)}) ---")
        for b in grup:
            s.append(f"  {im} [{b['kod']}] {b['yol']}: {b['mesaj']}")
        s.append("")
    if hata_n or dn_n:
        # check.py:215 rapor cumlesinin karsiligi.
        s.append(
            f"DUSTU — {hata_n} hata, {dn_n} denetlenemedi, {bilgi_n} bilgi; "
            f"{d.denetlenen} denetim yapildi."
        )
    else:
        # check.py:219 karsiligi.
        s.append(f"TAMAM — {d.denetlenen} denetim yapildi, 0 hata, {bilgi_n} bilgi.")
    return "\n".join(s)


def cikis_kodu(d: Denetci) -> int:
    if d.say(HATA):
        return 1
    if d.say(DENETLENEMEDI):
        return 2  # fail-closed: denetlenemeyen GECTI degildir
    return 0


# --- oz-test -----------------------------------------------------------------
def _sahte_beceri(kok: Path, ad: str, aciklama: str, *, kanit=True,
                  govde="", frontmatter=None, script=True):
    bd = kok / ".claude" / "skills" / ad
    (bd / "scripts").mkdir(parents=True, exist_ok=True)
    if frontmatter is None:
        frontmatter = f"name: {ad}\ndescription: {aciklama}\n"
    (bd / "SKILL.md").write_text(f"---\n{frontmatter}---\n\n{govde}\n", encoding="utf-8")
    if kanit:
        (bd / "KANIT.md").write_text("# KANIT\n", encoding="utf-8")
    if script:
        (bd / "scripts" / "motor.py").write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--self-test' in sys.argv:\n"
            "    print('ok')\n"
            "    sys.exit(0)\n",
            encoding="utf-8",
        )
    return bd


def _temiz_agac(kok: Path):
    (kok / ".claude").mkdir(parents=True, exist_ok=True)
    (kok / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    _sahte_beceri(kok, "temiz-beceri", "Duzgun bir beceri.", govde="Motor: scripts/motor.py")


def self_test() -> int:
    vakalar = []  # (ad, beklenen_kod, kurucu)

    def vaka(ad, kod):
        def sar(fn):
            vakalar.append((ad, kod, fn))
            return fn
        return sar

    @vaka("temiz agac (negatif kontrol)", None)
    def _(kok):
        _temiz_agac(kok)

    @vaka("gecersiz YAML frontmatter", "FRONTMATTER")
    def _(kok):
        _temiz_agac(kok)
        _sahte_beceri(kok, "bozuk-yaml", "x",
                      frontmatter="name: bozuk-yaml\ndescription: bir: iki: uc\n  - kirik\n")

    @vaka("frontmatter kapanmamis", "FRONTMATTER")
    def _(kok):
        _temiz_agac(kok)
        bd = kok / ".claude" / "skills" / "kapanmamis"
        (bd / "scripts").mkdir(parents=True)
        (bd / "SKILL.md").write_text("---\nname: kapanmamis\n", encoding="utf-8")
        (bd / "KANIT.md").write_text("# K\n", encoding="utf-8")

    @vaka("description 1024'u asiyor", "ACIKLAMA_UZUN")
    def _(kok):
        _temiz_agac(kok)
        _sahte_beceri(kok, "uzun-aciklama", "A" * (AZAMI_ACIKLAMA + 1))

    @vaka("description tam 1024 (sinir — hata OLMAMALI)", None)
    def _(kok):
        _temiz_agac(kok)
        _sahte_beceri(kok, "sinir-aciklama", "A" * AZAMI_ACIKLAMA,
                      govde="Motor: scripts/motor.py")

    @vaka("name dizin adiyla uyusmuyor", "AD_UYUSMAZ")
    def _(kok):
        _temiz_agac(kok)
        _sahte_beceri(kok, "ad-uyusmaz", "x",
                      frontmatter="name: baska-ad\ndescription: x\n")

    @vaka("name alani yok", "FRONTMATTER")
    def _(kok):
        _temiz_agac(kok)
        _sahte_beceri(kok, "adsiz", "x", frontmatter="description: sadece aciklama\n")

    @vaka("var olmayan referans dosya", "REF_COZUMLENMEDI")
    def _(kok):
        _temiz_agac(kok)
        _sahte_beceri(kok, "kayip-ref", "x", govde="Motor: scripts/yok_boyle_bir_sey.py")

    @vaka("KANIT.md eksik", "EKSIK_DOSYA")
    def _(kok):
        _temiz_agac(kok)
        _sahte_beceri(kok, "kanitsiz", "x", kanit=False, govde="Motor: scripts/motor.py")

    @vaka("derlenmeyen Python", "DERLENMEDI")
    def _(kok):
        _temiz_agac(kok)
        bd = _sahte_beceri(kok, "bozuk-py", "x", govde="Motor: scripts/motor.py")
        (bd / "scripts" / "kirik.py").write_text("def f(:\n  pass\n", encoding="utf-8")

    @vaka("settings.json gecersiz JSON", "JSON_AYRISTIRMA")
    def _(kok):
        _temiz_agac(kok)
        (kok / ".claude" / "settings.json").write_text('{"hooks": [,]}', encoding="utf-8")

    @vaka("kanca dosyasi diskte yok", "KANCA_DOSYA_YOK")
    def _(kok):
        _temiz_agac(kok)
        (kok / ".claude" / "settings.json").write_text(json.dumps({
            "hooks": {"Stop": [{"hooks": [{"type": "command",
                      "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/yok.sh"'}]}]}
        }), encoding="utf-8")

    @vaka("kanca +x degil (dogrudan cagriliyor)", "KANCA_CALISTIRILAMAZ")
    def _(kok):
        _temiz_agac(kok)
        hd = kok / ".claude" / "hooks"
        hd.mkdir(parents=True)
        (hd / "k.sh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        os.chmod(hd / "k.sh", 0o644)
        (kok / ".claude" / "settings.json").write_text(json.dumps({
            "hooks": {"Stop": [{"hooks": [{"type": "command",
                      "command": '"$CLAUDE_PROJECT_DIR/.claude/hooks/k.sh"'}]}]}
        }), encoding="utf-8")

    @vaka("kanca +x degil ama python3 ile cagriliyor (hata OLMAMALI)", None)
    def _(kok):
        _temiz_agac(kok)
        hd = kok / ".claude" / "hooks"
        hd.mkdir(parents=True)
        (hd / "k.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        os.chmod(hd / "k.py", 0o644)
        (kok / ".claude" / "settings.json").write_text(json.dumps({
            "hooks": {"Stop": [{"hooks": [{"type": "command",
                      "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/k.py"'}]}]}
        }), encoding="utf-8")

    @vaka("ajan frontmatter gecersiz", "AJAN_FRONTMATTER")
    def _(kok):
        _temiz_agac(kok)
        ad = kok / ".claude" / "agents"
        ad.mkdir(parents=True)
        (ad / "a.md").write_text("frontmatter yok, duz metin\n", encoding="utf-8")

    @vaka("ajan adi dosya adiyla uyusmuyor", "AJAN_AD_UYUSMAZ")
    def _(kok):
        _temiz_agac(kok)
        ad = kok / ".claude" / "agents"
        ad.mkdir(parents=True)
        (ad / "a.md").write_text("---\nname: b\ndescription: x\n---\n", encoding="utf-8")

    @vaka("bozuk CSV sutun sayisi", "CSV_SUTUN")
    def _(kok):
        _temiz_agac(kok)
        bd = _sahte_beceri(kok, "csv-beceri", "x", govde="Tablo: veri/t.csv")
        (bd / "veri").mkdir()
        (bd / "veri" / "t.csv").write_text("a,b,c\n1,2\n", encoding="utf-8")

    @vaka("bozuk YAML veri dosyasi", "YAML_AYRISTIRMA")
    def _(kok):
        _temiz_agac(kok)
        bd = _sahte_beceri(kok, "yaml-beceri", "x", govde="Kural: kurallar/k.yaml")
        (bd / "kurallar").mkdir()
        (bd / "kurallar" / "k.yaml").write_text("a: [1, 2\nb: }{\n", encoding="utf-8")

    @vaka("oz-test yolu yok", "OZTEST_YOK")
    def _(kok):
        _temiz_agac(kok)
        bd = _sahte_beceri(kok, "oztestsiz", "x", script=False,
                           govde="Motor: scripts/m.py")
        (bd / "scripts" / "m.py").write_text("print('bayraksiz')\n", encoding="utf-8")

    @vaka("oz-test exit 0 vermiyor", "OZTEST_DUSTU")
    def _(kok):
        _temiz_agac(kok)
        bd = _sahte_beceri(kok, "dusen-oztest", "x", script=False,
                           govde="Motor: scripts/m.py")
        (bd / "scripts" / "m.py").write_text(
            "import sys\nif '--self-test' in sys.argv:\n    sys.exit(1)\n", encoding="utf-8")

    @vaka("SKILL.md yok", "EKSIK_DOSYA")
    def _(kok):
        _temiz_agac(kok)
        bd = kok / ".claude" / "skills" / "skillsiz"
        bd.mkdir(parents=True)
        (bd / "KANIT.md").write_text("# K\n", encoding="utf-8")

    @vaka("UTF-8 BOM'lu SKILL.md", "KODLAMA")
    def _(kok):
        _temiz_agac(kok)
        bd = kok / ".claude" / "skills" / "bomlu"
        bd.mkdir(parents=True)
        (bd / "KANIT.md").write_text("# K\n", encoding="utf-8")
        (bd / "SKILL.md").write_bytes(
            b"\xef\xbb\xbf---\nname: bomlu\ndescription: x\n---\n")

    @vaka("settings.json yok", "SETTINGS_YOK")
    def _(kok):
        (kok / ".claude" / "skills").mkdir(parents=True)
        _sahte_beceri(kok, "temiz-beceri", "x", govde="Motor: scripts/motor.py")

    gecen = dusen = 0
    satirlar = []
    for ad, beklenen, kurucu in vakalar:
        gecici = Path(tempfile.mkdtemp(prefix="butunluk_oztest_"))
        try:
            kurucu(gecici)
            d = denetle(gecici, oztest_kos=True)
            kodlar = d.kodlar()
            if beklenen is None:
                ok = not kodlar
                ayrinti = "temiz beklendi, bulunan: " + (", ".join(sorted(kodlar)) or "yok")
            else:
                ok = beklenen in kodlar
                ayrinti = f"beklenen {beklenen}, bulunan: " + (", ".join(sorted(kodlar)) or "yok")
            satirlar.append(f"  [{'GECTI' if ok else 'DUSTU'}] {ad} — {ayrinti}")
            gecen += ok
            dusen += (not ok)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    print("OZ-TEST — butunluk.py")
    print("\n".join(satirlar))
    print(f"\n{len(vakalar)} vaka: {gecen} gecti, {dusen} dustu.")
    return 0 if dusen == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Beceri/kanca/ajan butunluk denetimi")
    ap.add_argument("--depo", default=".", help="depo koku (varsayilan: .)")
    ap.add_argument("--json", action="store_true", help="JSON rapor")
    ap.add_argument("--oztest-kosma", action="store_true",
                    help="oz-testleri kosturma, yalnizca varligini ara")
    ap.add_argument("--self-test", action="store_true", help="aracin kendi oz-testi")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    depo = Path(a.depo).resolve()
    if not (depo / ".claude").is_dir():
        print(f"HATA: {depo} altinda .claude/ yok", file=sys.stderr)
        return 3

    d = denetle(depo, oztest_kos=not a.oztest_kosma)
    if a.json:
        print(json.dumps({
            "depo": str(depo),
            "denetlenen": d.denetlenen,
            "ozet": {
                "hata": d.say(HATA),
                "denetlenemedi": d.say(DENETLENEMEDI),
                "bilgi": d.say(BILGI),
            },
            "bulgular": d.bulgular,
            "cikis_kodu": cikis_kodu(d),
        }, ensure_ascii=False, indent=2))
    else:
        print(rapor_metin(d))
    return cikis_kodu(d)


if __name__ == "__main__":
    sys.exit(main())
