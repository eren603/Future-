#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAĞLIK KONTROLÜ — "bütün beceriler ve piramit çalışıyor" garantisinin motoru.

Garanti sözle verilmez; bu betik her halkayı MEKANİK denetler ve tek hükümle
bitirir: SAĞLAM (çıkış 0) ya da KIRIK (çıkış 1, kırık halka listesiyle).

İki kip:
    --hizli (varsayılan): saniyeler — dosya/bağımlılık/kanca/derleme denetimi.
                          SessionStart kancası her yeni pencerede bunu koşar;
                          yeni pencere kendi sağlığını kendisi bildirir.
    --tam               : dakikalar — bütün beceri öz-testleri + engine e2e
                          koşulur (piramit 35 test, motor mekaniği dahil).

Denetlenen halkalar:
    1. BAĞIMLILIK  — pandas / numpy / scipy import edilebiliyor mu?
    2. MOTOR       — piramit.py MOTOR kayıt tablosundaki BÜTÜN motor dosyaları
                     yerinde mi? (tek kaynak: tablo piramit.py'den okunur,
                     burada liste KOPYALANMAZ — kopya liste eskir.)
    3. DERLEME     — boru hattının çekirdek betikleri sözdizimsel sağlam mı?
    4. KANCA       — settings.json'da SessionStart + UserPromptSubmit kayıtlı
                     ve kanca dosyaları yerinde mi? (Bu ikisi kopar =
                     "tetikleyicisiz otomatik" ölür.)
    5. GİRDİ/GÖREV — gorev.json + engine/girdi kline dosyaları okunuyor mu?
    6. SÖZLEŞME    — sozlesme.json kütüğündeki her kural, olması gereken
                     dosyada HÂLÂ yazılı mı? (Kırpma/yeniden yazma sırasında bir
                     kural hem CLAUDE.md'den hem beceri dosyasından sessizce
                     kaybolmasın diye. RESIDENT kurallar CLAUDE.md'de olmak
                     ZORUNDA: kanca boru hattını subprocess koşturur ve hiçbir
                     SKILL.md gövdesini bağlama YÜKLEMEZ.)
    7. ÖZ-TEST     — (yalnız --tam) her becerinin self_test.py'si GEÇİYOR mu?
"""
from __future__ import annotations

import argparse
import importlib
import json
import py_compile
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
REPO = SKILL.parents[2]
SKILLS = REPO / ".claude" / "skills"
ENGINE = REPO / "engine"

CEKIRDEK = [SCRIPTS / n for n in (
    "piramit.py", "gozlemci.py", "emir_plani.py", "kiyas.py",
    "esik_kalibre.py", "iddia_denetle.py", "usd_hedef.py", "korelasyon.py",
    "akibet_etiketle.py", "turev_girdi.py", "paket_ac.py",
)] + [REPO / ".claude" / "hooks" / "piramit_auto.py"]

OZ_TESTLER = sorted(SKILLS.glob("*/scripts/self_test.py")) + [
    ENGINE / "self_test.py",
    SKILLS / "karar-kurulu" / "scripts" / "rr_denetim_test.py",
]

SOZLESME = SKILL / "sozlesme.json"


def _motor_tablosu() -> dict:
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("piramit").MOTOR


def _duz(metin: str) -> str:
    """Beyaz boşluğu tek boşluğa indirger + NFC normalize eder.

    Gerekçe: kurallar 79 sütuna sarılmış Türkçe metinler; satır sarması bir
    dizgeyi ikiye bölerse denetim haksız yere KIRIK derdi. Büyük/küçük harf
    KORUNUR — "MÜHÜRLENİR" / "EMİR YOK" gibi kipler bilinçlidir.
    """
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", metin))


def kontrol_sozlesme() -> list[str]:
    """Sözleşme kütüğü denetimi — kırık kuralların listesi (boş = SAĞLAM).

    Fail-closed: kütük yoksa ya da okunamıyorsa denetim "geçti" saymaz, KIRIK
    der. Aksi halde kütüğü silmek denetimi sessizce kapatmanın yolu olurdu.
    """
    kirik: list[str] = []
    try:
        reg = json.loads(SOZLESME.read_text(encoding="utf-8"))
        kurallar = reg["kurallar"]
        if not isinstance(kurallar, list) or not kurallar:
            raise ValueError("kurallar listesi boş")
    except Exception as e:  # noqa: BLE001
        return [f"SÖZLEŞME: kütük okunamadı ({SOZLESME.name}: {type(e).__name__}: {e}) "
                "— korunan kural listesi denetlenemiyor (fail-closed)"]

    onbellek: dict[Path, str] = {}
    for k in kurallar:
        try:
            ad, katman = k["ad"], k["katman"]
            hedef, dizge = REPO / k["dosya"], k["dizge"]
        except Exception as e:  # noqa: BLE001
            kirik.append(f"SÖZLEŞME: kütükte bozuk kural kaydı ({type(e).__name__}: {e})")
            continue
        if not hedef.exists():
            kirik.append(f"SÖZLEŞME: [{katman}] {ad} — hedef dosya YOK ({k['dosya']})")
            continue
        if hedef not in onbellek:
            try:
                onbellek[hedef] = _duz(hedef.read_text(encoding="utf-8"))
            except OSError as e:
                kirik.append(f"SÖZLEŞME: {k['dosya']} okunamadı ({e})")
                onbellek[hedef] = ""
        if _duz(dizge) not in onbellek[hedef]:
            nicin = " (her oturumda yüklü olmak ZORUNDA — SKILL.md gövdesi " \
                    "varsayılan yolda bağlama girmez)" if katman == "RESIDENT" else ""
            kirik.append(f"SÖZLEŞME: [{katman}] {ad} KAYBOLDU — "
                         f"\"{dizge}\" artık {k['dosya']} içinde YOK{nicin}")

    # Ölü çapraz-referans: bir SKILL.md CLAUDE.md'ye işaret ederse, CLAUDE.md
    # kırpıldığı anda o işaret sessizce hiçbir yere çıkmaz (2026-07'de oldu).
    for sm in sorted(SKILLS.glob("*/SKILL.md")):
        try:
            if "bkz. CLAUDE.md" in _duz(sm.read_text(encoding="utf-8")):
                kirik.append(f"SÖZLEŞME: ölü çapraz-referans — {sm.parent.name}/SKILL.md "
                             "'bkz. CLAUDE.md' diyor; kural orada birebir yazılmalı "
                             "(CLAUDE.md kırpılınca bu işaret hiçbir yere çıkmaz)")
        except OSError:
            continue
    return kirik


def kontrol_hizli() -> list[str]:
    """Kırık halkaların listesi (boş liste = SAĞLAM)."""
    kirik: list[str] = []

    for mod in ("pandas", "numpy", "scipy"):
        try:
            importlib.import_module(mod)
        except Exception as e:  # noqa: BLE001 — hangi modül, neden: gizlenmez
            kirik.append(f"BAĞIMLILIK: {mod} import edilemedi ({type(e).__name__})")

    try:
        motor = _motor_tablosu()
        for ad, yol in motor.items():
            p = Path(yol)
            if not p.exists():
                kirik.append(f"MOTOR: {ad} dosyası YOK — {yol}")
                continue
            # varlık yetmez: sözdizimi-bozuk motor "SAĞLAM" sayılıyordu —
            # 19 motorun HEPSİ derlenir (yanlış-negatif kapatıldı).
            try:
                py_compile.compile(str(p), doraise=True)
            except Exception as e:  # noqa: BLE001
                kirik.append(f"MOTOR: {ad} derlenemiyor ({e})")
    except Exception as e:  # noqa: BLE001
        kirik.append(f"MOTOR: piramit.py MOTOR tablosu okunamadı ({e})")

    for p in CEKIRDEK:
        if not p.exists():
            kirik.append(f"DERLEME: çekirdek betik YOK — {p.name}")
            continue
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:  # noqa: BLE001
            kirik.append(f"DERLEME: {p.name} derlenemiyor ({e})")

    ayar_p = REPO / ".claude" / "settings.json"
    try:
        ayar = json.loads(ayar_p.read_text(encoding="utf-8"))
        kanca = ayar.get("hooks", {})
        for gerekli in ("SessionStart", "UserPromptSubmit"):
            girisler = kanca.get(gerekli)
            if not girisler:
                kirik.append(f"KANCA: settings.json'da {gerekli} kayıtlı DEĞİL "
                             "— tetikleyicisiz otomatik koşu çalışmaz")
                continue
            # anahtar varlığı yetmez: komutun İŞARET ETTİĞİ dosya da denetlenir
            # (komut ölü dosyaya bakarken "kanca 2/2" deniyordu).
            for grup in girisler:
                for h in (grup.get("hooks") or []):
                    kmt = str(h.get("command") or "")
                    for m in re.findall(r"\$CLAUDE_PROJECT_DIR[\"']?/([^\s\"']+)", kmt):
                        if not (REPO / m).exists():
                            kirik.append(f"KANCA: {gerekli} komutunun hedefi YOK "
                                         f"— {m}")
    except Exception as e:  # noqa: BLE001
        kirik.append(f"KANCA: {ayar_p} okunamadı ({e})")
    for h in ("session-start.sh", "piramit_auto.py"):
        if not (REPO / ".claude" / "hooks" / h).exists():
            kirik.append(f"KANCA: hooks/{h} YOK")

    for p, ad, liste in ((ENGINE / "gorev.json", "duran görev", False),
                         (ENGINE / "girdi" / "m15.json", "BTC 15M kline", True),
                         (ENGINE / "girdi" / "h4.json", "BTC 4H kline", True)):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            kirik.append(f"GİRDİ/GÖREV: {ad} okunamadı ({p.name}: {type(e).__name__})")
            continue
        if liste and not (isinstance(d, list) and d):
            # '[]' geçerli JSON'dur ama boru hattı K1'de durur — "OK" değildir.
            kirik.append(f"GİRDİ/GÖREV: {ad} BOŞ ya da liste değil ({p.name})")

    # Kanca çalışma-zamanı durumu: bozuk state dosyası (sözlük olmayan kök)
    # kancayı her istemde öldürüyordu ve sağlık "SAĞLAM" diyordu.
    for sp, ad in ((SKILL / "state" / "otomatik.json", "kanca durumu"),
                   (SKILL / "state" / "alinan_paketler.json", "paket defteri")):
        if not sp.exists():
            continue
        try:
            d = json.loads(sp.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            kirik.append(f"KANCA-DURUM: {ad} bozuk JSON ({sp.name}: {type(e).__name__})")
            continue
        if not isinstance(d, dict):
            kirik.append(f"KANCA-DURUM: {ad} kökü sözlük değil ({sp.name}) — "
                         "kanca bu dosyayla ölür")

    kirik += kontrol_sozlesme()

    return kirik


def kontrol_tam() -> tuple[list[str], list[str], list[str]]:
    """(kırık, geçen, atlanan) — her öz-test subprocess ile koşulur.

    Gerçek SI hafızası (hafiza/*.json) koşudan ÖNCE anlık görüntüye alınır ve
    koşudan sonra farklıysa GERİ YÜKLENİR: timeout/SIGKILL öz-testin kendi
    finally-geri-yüklemesini atlayabiliyordu → öğrenilmiş ağırlık kalıcı
    kayboluyordu. Ayrıca ffmpeg yoksa video-isleme öz-testi apt-get ile kurulum
    DENEMESİN diye atlanır (sağlık denetimi sistem durumunu değiştirmez).
    """
    kirik, gecen, atlanan = [], [], []
    hafiza_dizin = SKILL / "hafiza"
    yedek = {p: p.read_bytes() for p in sorted(hafiza_dizin.glob("*.json"))} \
        if hafiza_dizin.is_dir() else {}
    try:
        for t in OZ_TESTLER:
            etiket = f"{t.parent.parent.name}/{t.name}" if "skills" in str(t) \
                else f"engine/{t.name}"
            if not t.exists():
                kirik.append(f"ÖZ-TEST: {etiket} dosyası YOK")
                continue
            if "video-isleme" in str(t) and shutil.which("ffmpeg") is None:
                atlanan.append(f"{etiket} (ffmpeg yok — kurulum denenmedi)")
                continue
            try:
                pr = subprocess.run([sys.executable, str(t)], capture_output=True,
                                    text=True, timeout=600, cwd=str(t.parent))
            except subprocess.TimeoutExpired:
                kirik.append(f"ÖZ-TEST: {etiket} ZAMAN AŞIMI (600 s)")
                continue
            if pr.returncode == 0:
                gecen.append(etiket)
            else:
                son = (pr.stdout + pr.stderr).strip().splitlines()
                kirik.append(f"ÖZ-TEST: {etiket} KALDI (rc={pr.returncode}) — "
                             f"{son[-1][:120] if son else 'çıktı yok'}")
    finally:
        for p, icerik in yedek.items():
            try:
                if not p.exists() or p.read_bytes() != icerik:
                    p.write_bytes(icerik)
                    kirik.append(f"HAFIZA: {p.name} öz-test sonrası değişmişti — "
                                 "anlık görüntüden GERİ YÜKLENDİ (veri kaybı yok; "
                                 "öz-testin geri yüklemesi yarım kalmış)")
            except OSError as e:
                kirik.append(f"HAFIZA: {p.name} geri yüklenemedi ({e})")
    return kirik, gecen, atlanan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Piramit + beceri sağlık kontrolü")
    ap.add_argument("--tam", action="store_true",
                    help="öz-testleri de koş (dakikalar)")
    ap.add_argument("--hizli", action="store_true",
                    help="yalnız yapısal denetim (varsayılan)")
    args = ap.parse_args(argv)

    kirik = kontrol_hizli()
    try:
        n_motor = len(_motor_tablosu())
    except Exception:  # noqa: BLE001
        n_motor = 0
    try:
        n_sozlesme = len(json.loads(SOZLESME.read_text(encoding="utf-8"))["kurallar"])
    except Exception:  # noqa: BLE001
        n_sozlesme = 0

    ozet = ""
    if args.tam:
        t_kirik, t_gecen, t_atlanan = kontrol_tam()
        kirik += t_kirik
        ozet = f", öz-test {len(t_gecen)}/{len(OZ_TESTLER)} GEÇTİ"
        if t_atlanan:
            ozet += f" ({len(t_atlanan)} atlandı: {'; '.join(t_atlanan)})"

    if kirik:
        print(f"[SAĞLIK] ⛔ KIRIK — {len(kirik)} halka (motor kaydı {n_motor}):")
        for k in kirik:
            print(f"   ✖ {k}")
        return 1
    print(f"[SAĞLIK] ✔ SAĞLAM — motor {n_motor}/{n_motor} yerinde, "
          f"bağımlılık 3/3, kanca 2/2, girdi/görev OK, "
          f"sözleşme {n_sozlesme}/{n_sozlesme} kural yerinde{ozet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
