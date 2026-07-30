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
import os
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
    # Atomik yazım (S6): geçici dosya + os.replace. paket_ac bir subprocess olarak
    # 120 sn zaman aşımıyla ya da harness'in kanca kesmesiyle yazım ORTASINDA
    # öldürülebilir; yarım/bozuk karar girdisi (m15/h4) kalmasın.
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if yedekle and hedef.exists():
        shutil.copy2(hedef, hedef.with_suffix(hedef.suffix + ".yedek"))
    tmp = hedef.with_suffix(hedef.suffix + ".tmp")
    tmp.write_text(json.dumps(icerik, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, hedef)


def _hedefler(sembol: str, ana: str) -> tuple:
    """Sembole göre yazım kökü: ANA sembol engine/girdi'ye, diğerleri alt klasöre."""
    if sembol == ana:
        return GIRDI, HAM
    # yol-kaçışı korkuluğu (S2): sembol dışarıdan gelir; yol köküne YALNIZ
    # alfanümerik parça girer — "../", mutlak yol, ayraç depo dışına yazamaz.
    guvenli = "".join(c for c in sembol.replace("USDT", "").lower() if c.isalnum())
    if not guvenli:
        raise SystemExit(f"HATA: geçersiz sembol adı {sembol!r} — yol üretilemez "
                         "(fail-closed).")
    alt = GIRDI / guvenli
    return alt, alt / "turev_ham"


def ac_coklu(paket: dict, sembol_bekle: str | None = None) -> dict:
    """v2 paketi: birden çok sembol. v1 (tek sembol) da buraya düşer."""
    surum = int(paket.get("surum", 1))
    if surum < 2:
        return {"semboller": [paket.get("sembol")],
                "sonuc": {str(paket.get("sembol")): ac(paket, sembol_bekle)}}
    semboller = paket.get("semboller") or []
    # ana slot (engine/girdi = BTC karar girdisi) LİSTE SIRASINDAN değil
    # KİMLİKTEN seçilir (B2): yanlış sıralı/ETH-öncelikli paket ana slotu ezemez.
    # BTCUSDT yoksa ana=None → hiçbir sembol engine/girdi köküne yazılmaz
    # (hepsi alt klasöre), durum çıktıda raporlanır (fail-closed).
    ana = "BTCUSDT" if "BTCUSDT" in semboller else None
    veri = paket.get("veri") or {}
    sonuc = {}
    for sem in semboller:
        alt = {"paket": "piramit-veri", "surum": 1, "sembol": sem,
               "veri": veri.get(sem) or {}, "cekim_utc": paket.get("cekim_utc"),
               "hatalar": [h for h in (paket.get("hatalar") or []) if h.startswith(sem)]}
        sonuc[sem] = ac(alt, sem, *_hedefler(sem, ana))
    hatalar = list(paket.get("hatalar", []))
    if ana is None and semboller:
        hatalar.append("BTCUSDT pakette yok — ana slot (engine/girdi) YAZILMADI, "
                       "tüm semboller alt klasöre açıldı (fail-closed)")
    return {"semboller": semboller, "ana_sembol": ana,
            "cekim_utc": paket.get("cekim_utc", YOK), "sonuc": sonuc,
            "paket_hatalari": hatalar}


def ac(paket: dict, sembol_bekle: str | None,
       girdi_kok: Path | None = None, ham_kok: Path | None = None) -> dict:
    if paket.get("paket") != "piramit-veri":
        raise SystemExit("HATA: bu dosya piramit-veri paketi değil "
                         "(veri_topla.py ile üretilmiş olmalı).")
    sembol = str(paket.get("sembol", "")).upper()
    if sembol_bekle and sembol != sembol_bekle.upper():
        raise SystemExit(f"HATA: paket sembolü {sembol}, beklenen {sembol_bekle} — "
                         "yanlış sembol karara giremez (fail-closed).")
    veri = paket.get("veri") or {}
    girdi_kok = girdi_kok or GIRDI
    ham_kok = ham_kok or HAM
    yazilan, atlanan = {}, []

    # m15 ve h4 ATOMİK ÇİFTTİR (B5): ikisi de doğrulamadan geçmeden HİÇBİRİ
    # yazılmaz. Eskiden bağımsızdı — yeni m15 + bozuk h4 pakette YENİ 15M yazılıp
    # ESKİ 4H yerinde kalıyordu; kanca bunu başarı sayıp SHA gömüyor, boru hattı
    # YENİ 15M + BAYAT 4H çiftiyle koşuyordu (ayrışmış sahte veri).
    kline_hedef = {"m15": girdi_kok / "m15.json", "h4": girdi_kok / "h4.json"}
    kline_ok = {}
    for ad, asgari in (("m15", MIN_M15), ("h4", MIN_H4)):
        d = veri.get(ad)
        if d is None:
            atlanan.append(f"{ad}: pakette yok ({YOK})")
            continue
        ok, neden = _kline_gecerli(d, asgari)
        if ok:
            kline_ok[ad] = (d, neden)
        else:
            atlanan.append(f"{ad}: {neden} → YAZILMADI")
    if len(kline_ok) == 2:
        for ad in ("m15", "h4"):
            d, neden = kline_ok[ad]
            _yaz(kline_hedef[ad], d)
            yazilan[ad] = f"{_kisa(kline_hedef[ad])} — {neden}"
    elif kline_ok:
        atlanan.append("m15/h4 ATOMİK ÇİFT: yalnız biri geçerli → İKİSİ DE "
                       "YAZILMADI (yeni/bayat kline çifti karışmasın; fail-closed)")

    for ad in ("openInterestHist", "premiumIndex", "takerlongshortRatio"):
        d = veri.get(ad)
        if d is None:
            atlanan.append(f"{ad}: pakette yok ({YOK}) → kanal boş kalır")
            continue
        # eleman tipi denetimi (S1): d liste-ama-eleman-sözlük-değil ise (ör.
        # [1,2,3]) d[0].get() AttributeError fırlatırdı ve bu blok try içinde DEĞİL.
        if isinstance(d, list) and d and not isinstance(d[0], dict):
            atlanan.append(f"{ad}: liste elemanları sözlük değil → YAZILMADI")
            continue
        if isinstance(d, list) and d and str(d[0].get("symbol", sembol)) != sembol:
            atlanan.append(f"{ad}: sembol uyuşmuyor → YAZILMADI")
            continue
        _yaz(ham_kok / f"{ad}.json", d)
        n = len(d) if isinstance(d, list) else 1
        yazilan[ad] = f"{_kisa(ham_kok / f'{ad}.json')} — {n} kayıt"

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

    sonuc = ac_coklu(paket, a.sembol)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    yazan = sum(1 for r in sonuc["sonuc"].values() if r.get("yazilan"))
    return 0 if yazan else 1


if __name__ == "__main__":
    sys.exit(main())
