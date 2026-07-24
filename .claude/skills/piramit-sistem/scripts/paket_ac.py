#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paket açıcı — `veri_topla.py`nin ürettiği TEK dosyayı depoya dağıtır.

    python paket_ac.py --paket ~/piramit_veri_BTCUSDT_20260724_1930.json

Yazdıkları:
    engine/girdi/m15.json                        (15M kline)
    engine/girdi/h4.json                         (4H kline)
    engine/girdi/turev_ham/openInterestHist.json
    engine/girdi/turev_ham/premiumIndex.json
    engine/girdi/turev_ham/takerlongshortRatio.json

Sonrasında kanca (UserPromptSubmit) bir sonraki istemde CVD'yi hesaplar,
türev kanallarını bağlar ve piramidi koşturur — elle komut gerekmez.

DOĞRULAMA (fail-closed — şüpheli veri depoya GİRMEZ):
  - paket etiketi ve sürümü tanınmalı
  - sembol beklenenle aynı olmalı (yanlış sembol karara giremez)
  - kline satırları 12 alanlı Binance biçiminde olmalı (CVD alan 9'dan gelir)
  - kline bar sayısı motorun asgarisini karşılamalı
  - zaman damgaları artan sırada olmalı
Bir kanal doğrulamayı geçemezse YALNIZ o kanal atlanır; gerekçe yazılır.
Var olan dosyanın üzerine yazmadan önce eski sürüm `.yedek` olarak saklanır.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO = _HERE.parents[3]
GIRDI = REPO / "engine" / "girdi"
HAM = GIRDI / "turev_ham"

MIN_M15 = 104        # engine/karar_motoru: N_VOL + 2*SWING_K + 4
MIN_H4 = 25          # engine/karar_motoru: MA_SLOW + 5
YOK = "VERİ YOK"


def _kline_gecerli(d, asgari: int) -> tuple:
    if not isinstance(d, list) or not d:
        return False, "liste değil ya da boş"
    if len(d) < asgari:
        return False, f"{len(d)} bar < asgari {asgari} (motor eşiği veriden hesaplayamaz)"
    if not all(isinstance(x, list) and len(x) >= 12 for x in d):
        return False, "satırlar 12 alanlı Binance kline biçiminde değil (taker hacmi yok)"
    zaman = [x[0] for x in d]
    if any(b <= a for a, b in zip(zaman, zaman[1:])):
        return False, "zaman damgaları artan sırada değil"
    return True, f"{len(d)} bar, son {d[-1][4]}"


def _kisa(p: Path) -> str:
    """Depoya göreli yol; depo dışındaysa mutlak yol (patlamadan)."""
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def _yaz(hedef: Path, icerik, yedekle: bool = True) -> None:
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if yedekle and hedef.exists():
        shutil.copy2(hedef, hedef.with_suffix(hedef.suffix + ".yedek"))
    hedef.write_text(json.dumps(icerik, ensure_ascii=False), encoding="utf-8")


def ac(paket: dict, sembol_bekle: str | None) -> dict:
    if paket.get("paket") != "piramit-veri":
        raise SystemExit("HATA: bu dosya piramit-veri paketi değil "
                         "(veri_topla.py ile üretilmiş olmalı).")
    sembol = str(paket.get("sembol", "")).upper()
    if sembol_bekle and sembol != sembol_bekle.upper():
        raise SystemExit(f"HATA: paket sembolü {sembol}, beklenen {sembol_bekle} — "
                         "yanlış sembol karara giremez (fail-closed).")
    veri = paket.get("veri") or {}
    yazilan, atlanan = {}, []

    for ad, hedef, asgari in (("m15", GIRDI / "m15.json", MIN_M15),
                              ("h4", GIRDI / "h4.json", MIN_H4)):
        d = veri.get(ad)
        if d is None:
            atlanan.append(f"{ad}: pakette yok ({YOK})")
            continue
        ok, neden = _kline_gecerli(d, asgari)
        if ok:
            _yaz(hedef, d)
            yazilan[ad] = f"{_kisa(hedef)} — {neden}"
        else:
            atlanan.append(f"{ad}: {neden} → YAZILMADI")

    for ad in ("openInterestHist", "premiumIndex", "takerlongshortRatio"):
        d = veri.get(ad)
        if d is None:
            atlanan.append(f"{ad}: pakette yok ({YOK}) → kanal boş kalır")
            continue
        if isinstance(d, list) and d and str(d[0].get("symbol", sembol)) != sembol:
            atlanan.append(f"{ad}: sembol uyuşmuyor → YAZILMADI")
            continue
        _yaz(HAM / f"{ad}.json", d)
        n = len(d) if isinstance(d, list) else 1
        yazilan[ad] = f"{_kisa(HAM / f'{ad}.json')} — {n} kayıt"

    # tazelik: türev verisi kline'ın son barıyla aynı pencerede mi?
    uyari = []
    try:
        son_bar = int(veri["m15"][-1][0])
        for ad in ("openInterestHist", "takerlongshortRatio"):
            d = veri.get(ad)
            if isinstance(d, list) and d and isinstance(d[-1].get("timestamp"), (int, float)):
                fark = (son_bar - int(d[-1]["timestamp"])) / 60000.0
                if abs(fark) > 120:
                    uyari.append(f"[VARSAYIM] {ad}: kline son barından {fark:+.0f} dk "
                                 "uzakta — eşzamanlı değil")
    except (KeyError, IndexError, TypeError, ValueError):
        pass

    return {"sembol": sembol, "cekim_utc": paket.get("cekim_utc", YOK),
            "yazilan": yazilan, "atlanan": atlanan, "uyarilar": uyari,
            "paket_hatalari": paket.get("hatalar", [])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Piramit veri paketini depoya aç")
    ap.add_argument("--paket", required=True, help="veri_topla.py çıktısı (JSON)")
    ap.add_argument("--sembol", default=None, help="beklenen sembol (doğrulama)")
    a = ap.parse_args(argv)

    p = Path(a.paket).expanduser()
    if not p.exists():
        raise SystemExit(f"HATA: paket bulunamadı: {p}")
    try:
        paket = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"HATA: paket JSON değil: {e}") from e

    sonuc = ac(paket, a.sembol)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    return 0 if sonuc["yazilan"] else 1


if __name__ == "__main__":
    sys.exit(main())
