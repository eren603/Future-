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
ANA_VARSAYILAN = "BTCUSDT"   # ana slot (engine/girdi) sahibi — paket seçemez


def _sabit_yasak(c):
    """json.loads NaN/Infinity'yi VARSAYILAN olarak kabul eder. NaN ile yapılan
    her karşılaştırma False döndüğü için `_kline_gecerli`in 'artan sıra' kapısı
    ve kancanın 'geri sarma' kapısı sessizce geçilebiliyordu."""
    raise ValueError(f"JSON sabiti yasak: {c} (NaN/Infinity veri olamaz)")
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


SEMBOL_BICIMI = __import__("re").compile(r"[A-Z0-9]{2,20}\Z")


def _sembol_dogrula(sembol) -> str:
    """Sembol adı bir YOL BİLEŞENİ olur — dışarıdan gelen dize doğrulanmadan
    kullanılamaz. Yalnız [A-Z0-9]{2,20} kabul edilir; '../', mutlak yol,
    ayraç ve nokta REDDEDİLİR (fail-closed: şüpheli sembol depoya giremez).
    """
    # `str(None)` → "NONE" idi: tip hatası KABUL EDİLEN sembole dönüşüyor,
    # `semboller:[null]` engine/girdi/none dizini açıyordu. Tip önce denetlenir.
    if not isinstance(sembol, str):
        raise SystemExit(f"HATA: sembol adı metin değil ({type(sembol).__name__}: "
                         f"{sembol!r}) — reddedildi (fail-closed).")
    s = sembol.upper()
    if not SEMBOL_BICIMI.match(s):
        raise SystemExit(f"HATA: geçersiz sembol adı {sembol!r} — yalnız "
                         "A-Z0-9 (2-20 karakter) kabul edilir; yol bileşeni "
                         "olarak kullanıldığı için reddedildi (fail-closed).")
    return s


def _hedefler(sembol: str, ana: str) -> tuple:
    """Sembole göre yazım kökü: ANA sembol engine/girdi'ye, diğerleri alt klasöre."""
    if sembol == ana:
        return GIRDI, HAM
    alt = GIRDI / _sembol_dogrula(sembol).replace("USDT", "").lower()
    # ikinci korkuluk: biçim denetimi atlansa bile hedef depo dışına çıkamaz
    if not alt.resolve().is_relative_to(GIRDI.resolve()):
        raise SystemExit(f"HATA: yazım hedefi engine/girdi dışına çıkıyor "
                         f"({_kisa(alt)}) — reddedildi (fail-closed).")
    return alt, alt / "turev_ham"


def ac_coklu(paket: dict, sembol_bekle: str | None = None) -> dict:
    """v2 paketi: birden çok sembol. v1 (tek sembol) da buraya düşer."""
    surum = int(paket.get("surum", 1))
    if surum < 2:
        return {"semboller": [paket.get("sembol")],
                "sonuc": {str(paket.get("sembol")): ac(paket, sembol_bekle)}}
    semboller = [_sembol_dogrula(s) for s in (paket.get("semboller") or [])]
    # ANA slot (engine/girdi) artık paketteki SIRAYA bırakılmıyor: paket açıkça
    # `ana_sembol` beyan ederse o geçerlidir ve `semboller` içinde olmak
    # ZORUNDADIR. Beyan yoksa depo sabiti BTCUSDT kazanır; o da listede
    # değilse fail-closed REDDEDİLİR — paketteki SIRA ana slotu belirleyemez.
    ana = paket.get("ana_sembol")
    if ana is not None:
        ana = _sembol_dogrula(ana)
        if ana not in semboller:
            raise SystemExit(f"HATA: beyan edilen ana_sembol {ana} paketin "
                             f"semboller listesinde yok {semboller} — "
                             "ana slot sahibi belirsiz (fail-closed).")
    elif ANA_VARSAYILAN in semboller:
        # Beyan yoksa ana slot paketteki SIRAYA bırakılmaz: depo sabiti kazanır.
        ana = ANA_VARSAYILAN
    elif semboller:
        # FAIL-CLOSED: ne `ana_sembol` beyanı var ne de BTCUSDT listede.
        # Eskiden burada `semboller[0]` seçiliyordu — yani yalnız ETHUSDT
        # içeren bir v2 paketi ANA slotu (engine/girdi = BTC yuvası) ele
        # geçirip BTC girdisini eziyordu. Ana slot sahibi belirsizse
        # yazmıyoruz; paket `ana_sembol` beyan etmelidir.
        raise SystemExit(
            f"HATA: ana slot sahibi belirsiz — pakette {ANA_VARSAYILAN} yok "
            f"{semboller} ve `ana_sembol` beyanı da yok. Paketteki SIRA ana "
            "slotu belirleyemez (fail-closed).")
    else:
        ana = None
    veri = paket.get("veri") or {}
    sonuc = {}
    for sem in semboller:
        alt = {"paket": "piramit-veri", "surum": 1, "sembol": sem,
               "veri": veri.get(sem) or {}, "cekim_utc": paket.get("cekim_utc"),
               "hatalar": [h for h in (paket.get("hatalar") or []) if h.startswith(sem)]}
        sonuc[sem] = ac(alt, sem, *_hedefler(sem, ana))
    return {"semboller": semboller, "ana_sembol": ana,
            "cekim_utc": paket.get("cekim_utc", YOK), "sonuc": sonuc,
            "paket_hatalari": paket.get("hatalar", [])}


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

    for ad, hedef, asgari in (("m15", girdi_kok / "m15.json", MIN_M15),
                              ("h4", girdi_kok / "h4.json", MIN_H4)):
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
        paket = json.loads(p.read_text(encoding="utf-8"),
                           parse_constant=_sabit_yasak)
    except (json.JSONDecodeError, ValueError) as e:
        raise SystemExit(f"HATA: paket JSON değil ya da geçersiz sabit: {e}") from e

    sonuc = ac_coklu(paket, a.sembol)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    yazan = sum(1 for r in sonuc["sonuc"].values() if r.get("yazilan"))
    return 0 if yazan else 1


if __name__ == "__main__":
    sys.exit(main())
