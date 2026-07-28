#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İDDİA DENETÇİSİ — cevap metnindeki her sayının kaynağı var mı?

Gözlemciler boru hattını denetler; bu araç ANLATIYI denetler: kullanıcıya
sunulacak metindeki sayılar gerçekten koşu raporunda var mı, yoksa yazarken
mi uyduruldu?

    python iddia_denetle.py --metin taslak.md --rapor son_rapor.json

Her sayı için: BULUNDU (raporda birebir var) / KAYNAKSIZ (yok).
KAYNAKSIZ çıkan her sayı ya rapordan düzeltilir ya metinden çıkarılır.

SINIRI AÇIKÇA SÖYLENİR: bu araç ANLAM denetlemez. "SHORT" demenin doğru olup
olmadığını bilemez; yalnız sayının kaynağını sınar. Yorum/çıkarım doğruluğu
elle ikinci-göz işidir (CLAUDE.md: grounding mekanikleştirilemez). Yani bu
araç sahte-otorite değildir; uydurma SAYIYA karşı mekanik bir korkuluktur.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Yapısal sayılar: katman numaraları, liste sıraları — piyasa iddiası DEĞİL.
# DARALTILDI: 2/3/4/5/10/100 aynı zamanda R katsayısı, kanal sayısı, kaldıraç ve
# yüzde iddialarında geçiyordu; beyaz listede kalmaları bu iddiaların kaynak
# denetiminden MUAF olması demekti (uydurma sayı için açık kapı).
YAPISAL = {0, 1}
# Negatif işaret yalnız rakam/nokta ile ÖNCELENMEMİŞSE geçerlidir; aksi halde
# "64515.6-64707.5" gibi ARALIKLAR negatif sayı sanılır (yanlış KAYNAKSIZ).
SAYI = re.compile(r"(?<![\d.,])[-+]?\d+(?:[.,]\d+)?")
# Zaman damgaları piyasa iddiası DEĞİLDİR (2026-07-24, 22:04:53, 10:30).
# Taramadan önce maskelenir; sayıldıkları ama denetlenmedikleri raporlanır.
ZAMAN = re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?"
                   r"|(?<!\d)\d{1,2}:\d{2}(?::\d{2})?(?!\d)")
# Git commit kısaltması (3b9fb42) da piyasa iddiası DEĞİLDİR. Yalnız EN AZ BİR
# harf içeren onaltılık öbek maskelenir — saf rakam (ör. 6461155 fiyat) asla.
SHA = re.compile(r"(?<![\w.])(?=[0-9a-f]{7,40}(?![\w]))[0-9]*[a-f][0-9a-f]*")


def rapor_sayilari(nesne, kume=None) -> set:
    kume = set() if kume is None else kume
    if isinstance(nesne, dict):
        for v in nesne.values():
            rapor_sayilari(v, kume)
    elif isinstance(nesne, list):
        for v in nesne:
            rapor_sayilari(v, kume)
    elif isinstance(nesne, bool):
        pass
    elif isinstance(nesne, (int, float)):
        kume.add(round(float(nesne), 6))
    elif isinstance(nesne, str):
        for m in SAYI.finditer(nesne):          # metne gömülü sayılar da kaynaktır
            try:
                kume.add(round(float(m.group().replace(",", ".")), 6))
            except ValueError:
                pass
    return kume


def denetle(metin: str, rapor: dict, tolerans: float = 0.0) -> dict:
    kaynak = rapor_sayilari(rapor)
    zaman_sayisi = len(ZAMAN.findall(metin))
    metin = ZAMAN.sub(lambda m: "#" * len(m.group()), metin)   # zaman maskele
    sha_sayisi = len(SHA.findall(metin))
    metin = SHA.sub(lambda m: "#" * len(m.group()), metin)     # commit maskele
    bulundu, kaynaksiz, yapisal = [], [], []
    for m in SAYI.finditer(metin):
        ham = m.group()
        try:
            v = round(float(ham.replace(",", ".")), 6)
        except ValueError:
            continue
        baglam = metin[max(0, m.start() - 45):m.end() + 25].replace("\n", " ")
        if v in YAPISAL:
            yapisal.append({"deger": v, "baglam": baglam})
            continue
        # Kabul: birebir eşleşme YA DA raporun sayısının GÖSTERİM yuvarlaması
        # (63511.096 → "63511.1"). Eskiden ölçüt bağıl bir banttı
        # (tolerans*max(1,|k|) = %0.5) — BTC ölçeğinde ±320 USDT'lik pencere,
        # yani uydurma bir sayı raporda yakın bir sayı olduğu için "kaynaklı"
        # sayılabiliyordu. Artık bant YOK; yalnız yuvarlama denkliği kabul edilir.
        if v in kaynak \
                or any(round(k, d) == v for k in kaynak for d in (0, 1, 2, 3, 4)) \
                or (tolerans > 0 and any(abs(v - k) <= tolerans for k in kaynak)):
            bulundu.append(v)
        else:
            kaynaksiz.append({"deger": v, "baglam": baglam})
    return {
        "toplam_sayi": len(bulundu) + len(kaynaksiz) + len(yapisal),
        "bulundu": len(bulundu), "yapisal_atlanan": len(yapisal),
        "zaman_damgasi_atlanan": zaman_sayisi,
        "commit_kimligi_atlanan": sha_sayisi,
        "KAYNAKSIZ": kaynaksiz,
        "gecti": not kaynaksiz,
        "tolerans": tolerans,          # gizli eşik kalmasın (0.0 = bant yok)
        "yapisal_muaf": sorted(YAPISAL),
        "sinir": ("Yalnız SAYI kaynağı denetlenir; anlam/çıkarım doğruluğu "
                  "denetlenmez (elle ikinci-göz gerekir). Zaman damgaları "
                  "maskelenir — piyasa iddiası değildir."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cevap metnindeki sayıların kaynak denetimi")
    ap.add_argument("--metin", required=True)
    ap.add_argument("--rapor", required=True, action="append",
                    help="koşu raporu (birden çok kez verilebilir)")
    a = ap.parse_args(argv)

    rapor = {}
    for i, r in enumerate(a.rapor):
        rapor[f"rapor{i}"] = json.loads(Path(r).expanduser().read_text(encoding="utf-8"))
    sonuc = denetle(Path(a.metin).expanduser().read_text(encoding="utf-8"), rapor)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    return 0 if sonuc["gecti"] else 2


if __name__ == "__main__":
    sys.exit(main())
