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
    6. ÖZ-TEST     — (yalnız --tam) her becerinin self_test.py'si GEÇİYOR mu?
"""
from __future__ import annotations

import argparse
import importlib
import json
import py_compile
import subprocess
import sys
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


def _motor_tablosu() -> dict:
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("piramit").MOTOR


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
            if not Path(yol).exists():
                kirik.append(f"MOTOR: {ad} dosyası YOK — {yol}")
    except Exception as e:  # noqa: BLE001
        kirik.append(f"MOTOR: piramit.py MOTOR tablosu okunamadı ({e})")
        motor = {}

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
            if not kanca.get(gerekli):
                kirik.append(f"KANCA: settings.json'da {gerekli} kayıtlı DEĞİL "
                             "— tetikleyicisiz otomatik koşu çalışmaz")
    except Exception as e:  # noqa: BLE001
        kirik.append(f"KANCA: {ayar_p} okunamadı ({e})")
    for h in ("session-start.sh", "piramit_auto.py"):
        if not (REPO / ".claude" / "hooks" / h).exists():
            kirik.append(f"KANCA: hooks/{h} YOK")

    for p, ad in ((ENGINE / "gorev.json", "duran görev"),
                  (ENGINE / "girdi" / "m15.json", "BTC 15M kline"),
                  (ENGINE / "girdi" / "h4.json", "BTC 4H kline")):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            kirik.append(f"GİRDİ/GÖREV: {ad} okunamadı ({p.name}: {type(e).__name__})")

    return kirik


def kontrol_tam() -> tuple[list[str], list[str]]:
    """(kırık, geçen) — her öz-test subprocess ile koşulur."""
    kirik, gecen = [], []
    for t in OZ_TESTLER:
        etiket = f"{t.parent.parent.name}/{t.name}" if "skills" in str(t) \
            else f"engine/{t.name}"
        if not t.exists():
            kirik.append(f"ÖZ-TEST: {etiket} dosyası YOK")
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
    return kirik, gecen


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

    ozet = ""
    if args.tam:
        t_kirik, t_gecen = kontrol_tam()
        kirik += t_kirik
        ozet = f", öz-test {len(t_gecen)}/{len(OZ_TESTLER)} GEÇTİ"

    if kirik:
        print(f"[SAĞLIK] ⛔ KIRIK — {len(kirik)} halka (motor kaydı {n_motor}):")
        for k in kirik:
            print(f"   ✖ {k}")
        return 1
    print(f"[SAĞLIK] ✔ SAĞLAM — motor {n_motor}/{n_motor} yerinde, "
          f"bağımlılık 3/3, kanca 2/2, girdi/görev OK{ozet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
