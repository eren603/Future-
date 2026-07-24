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

# Yapısal sayılar: katman numaraları, tarih/saat parçaları, liste sıraları.
# Bunlar piyasa iddiası değildir; kaynak aranmaz (ama listelenir).
YAPISAL = {0, 1, 2, 3, 4, 5, 10, 100}
SAYI = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


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


def denetle(metin: str, rapor: dict, tolerans: float = 0.005) -> dict:
    kaynak = rapor_sayilari(rapor)
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
        if v in kaynak or any(abs(v - k) <= tolerans * max(1.0, abs(k))
                              for k in kaynak):
            bulundu.append(v)
        else:
            kaynaksiz.append({"deger": v, "baglam": baglam})
    return {
        "toplam_sayi": len(bulundu) + len(kaynaksiz) + len(yapisal),
        "bulundu": len(bulundu), "yapisal_atlanan": len(yapisal),
        "KAYNAKSIZ": kaynaksiz,
        "gecti": not kaynaksiz,
        "sinir": ("Yalnız SAYI kaynağı denetlenir; anlam/çıkarım doğruluğu "
                  "denetlenmez (elle ikinci-göz gerekir)."),
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
