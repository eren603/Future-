"""Uc parcayi TEK dosyada birlestirir: modul + testler + canli veri katmani."""
import io
import re

KOK = "/home/user/Future-/.claude/worktrees/llm-trading-sistem/"
CIKTI = ("/tmp/claude-0/-home-user-Future-/4056c135-aef4-5d4b-804f-5f0dd0c8f598/"
         "scratchpad/llm_trading_tek.py")

modul = io.open(KOK + "llm_trading_v3.py", encoding="utf-8").read()
test = io.open(KOK + "test_llm_trading_v3.py", encoding="utf-8").read()

# --- 1) Modulun oz-testi artik AYNI dosyadaki testleri kosturur -----------
eski_ithal = """    import unittest as _ut
    try:
        import test_llm_trading_v3 as _t
    except ImportError:
        print("test dosyasi bulunamadi - oz-test atlandi")
        return 1
    _OZ_TEST_KOSUYOR = True"""
yeni_ithal = """    import sys as _sys
    import unittest as _ut
    _t = _sys.modules[__name__]        # testler AYNI dosyada
    _OZ_TEST_KOSUYOR = True"""
assert eski_ithal in modul, "oz-test blogu bulunamadi"
modul = modul.replace(eski_ithal, yeni_ithal, 1)

# --- 2) main() ve __main__ blogunu SONA tasimak icin kes ------------------
main_bas = modul.index("def main(argv=None):")
son_blok = modul[main_bas:]
modul = modul[:main_bas]

# --- 3) Test dosyasindan basligi/ithalleri soy ---------------------------
gorunum = test.index("class ")
test_govde = test[gorunum:]
# `m.` -> kendi modulumuz; `_agrega4h`/`FIKSTUR_BARI` gibi test yardimcilarini
# test basligindan geri al
yardimci = re.search(r"(FIKSTUR_BARI = .*?)(?=\nclass )", test[:gorunum + 4000],
                     re.S)
yardimci_metin = yardimci.group(1) if yardimci else ""
if yardimci_metin and yardimci_metin not in test_govde:
    test_govde = yardimci_metin + "\n\n" + test_govde

BASLIK = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm_trading_tek.py - TEK DOSYA: sistem + 236 test + canli veri katmani.

Ek bagimlilik YOKTUR (yalniz Python standart kutuphanesi).
Pydroid 3'te tek dosya olarak calisir.

KULLANIM
--------
  python llm_trading_tek.py --self-test     236 testi kosturur
  python llm_trading_tek.py --esikler       her sabiti kaynak+gerekcesiyle basar
  python llm_trading_tek.py --oz-rapor r.json   sentetik uctan uca kosu -> JSON
  python llm_trading_tek.py --canli BTCUSDT     GERCEK Binance verisiyle kosar
  python llm_trading_tek.py --ornek         AGSIZ ornek kosu (sahte veriyle)

GUVENLIK SINIRI (degismez)
--------------------------
Bu dosyada kimlik anahtari, gizli anahtar, imzalama, imzali uc, emir ucu
ya da iptal ucu YOKTUR ve eklenmemelidir. Yalniz PUBLIC GET piyasa
verisi okunur; kagit defteri YERELDIR. Bu sinir bir TESTLE korunur
(GuvenlikTesti.test_yasakli_desen_yok motor bolumunu tarar).
Yalniz karar-destek; canli/otomatik emir DAHIL DEGILDIR.
"""
'''

# Modulun kendi baslik docstring'ini at (yenisi yukarida)
ilk_ucluk = modul.index('"""')
ikinci_ucluk = modul.index('"""', ilk_ucluk + 3) + 3
modul_govde = modul[ikinci_ucluk:].lstrip("\n")
# shebang/encoding satirlarini da at
modul_govde = re.sub(r"^#!.*\n|^# -\*- coding.*\n", "", modul_govde)

CANLI = '''

# ==========================================================================
# BOLUM 12 - CANLI VERI KATMANI (public GET; imza/anahtar/emir ucu YOK)
# ==========================================================================


def http_getir(url, params, zaman_asimi=20):
    """Tek public GET. Bu dosyadaki TEK ag cagrisi.

    Emir/iptal ucu, API anahtari, imza YOKTUR ve eklenmemelidir - modul
    bir EMIR sistemi degil, bir OLCUM sistemidir.
    """
    import json as _json
    import urllib.parse as _up
    import urllib.request as _ur

    tam = url + "?" + _up.urlencode(params)
    istek = _ur.Request(tam, headers={"User-Agent": SURUM})
    with _ur.urlopen(istek, timeout=zaman_asimi) as yanit:
        return _json.loads(yanit.read().decode("utf-8"))


def canli_kosu(sembol, getir_fn=None, tohum=2026, **ek):
    """Uctan uca: veri_topla -> paket_kur -> BoruHatti.calistir.

    getir_fn verilmezse http_getir kullanilir (AGA CIKAR).
    """
    getir_fn = http_getir if getir_fn is None else getir_fn
    toplama = veri_topla(sembol, [BinanceAdaptor(), OkxAdaptor()], getir_fn)
    if toplama["adaptor"] is None:
        raise RuntimeError("hicbir adaptor veri veremedi (fail-closed)")
    paket = paket_kur(sembol, toplama, **ek)
    return BoruHatti(tohum=tohum).calistir(paket), paket, toplama


def _sahte_getir(url, params):
    """AGSIZ ornek veri uretici - `--ornek` icin. Gercek veri DEGILDIR."""
    rng = tohumlu_rng("ornek", url, str(params.get("interval", "")))
    if "klines" in url:
        onbes = "15m" in str(params.get("interval"))
        n, adim = (6000, 900000) if onbes else (375, 14400000)
        satirlar, fiyat = [], 100.0
        for i in range(n):
            fiyat *= 1.0 + rng.uniform(-0.003, 0.003)
            h = 100.0 + rng.uniform(0.0, 50.0)
            satirlar.append([i * adim, "%.8f" % fiyat, "%.8f" % (fiyat * 1.002),
                             "%.8f" % (fiyat * 0.998), "%.8f" % fiyat,
                             "%.8f" % h, i * adim + adim - 1, "0", 50,
                             "%.8f" % (h * (0.4 + rng.uniform(0.0, 0.2))),
                             "0", "0"])
        return satirlar
    if "openInterest" in url:
        return [{"sumOpenInterest": "%.2f" % (1000 + rng.uniform(-50, 50)),
                 "timestamp": i * 900000} for i in range(6000)]
    if "takerlongshort" in url:
        return [{"buySellRatio": "%.4f" % (1.0 + rng.uniform(-0.2, 0.2)),
                 "timestamp": i * 900000} for i in range(6000)]
    if "premiumIndex" in url:
        return {"lastFundingRate": "0.0001"}
    if "depth" in url:
        return {"bids": [["100.0", "5.0"]], "asks": [["100.1", "3.0"]]}
    raise RuntimeError("bilinmeyen uc: " + url)


_TEST_BOLUMU_SINIRI = "# BOLUM 11 - TEST PAKETI"
_TEST_SABITLERI = ("FIKSTUR_BARI",)   # test fiksturu, motor esigi DEGIL


def _modul_kaynagi():
    """Bu dosyanin YALNIZ motor bolumu (test bolumu HARIC).

    Tek dosyada kaynak tarayan testler kendi metinlerini de gorurdu; o
    yuzden tarama sinirlanir. Testleri zayiflatmaz - dogru kaynagi
    gosterir.
    """
    import pathlib as _pl
    metin = _pl.Path(__file__).read_text(encoding="utf-8")
    kesim = metin.find(_TEST_BOLUMU_SINIRI)
    return metin if kesim < 0 else metin[:kesim]


def _kosu_bas(sembol, getir_fn, baslik):
    karar, paket, toplama = canli_kosu(sembol, getir_fn=getir_fn)
    print("=" * 78)
    print(baslik)
    print("adaptor      :", toplama["adaptor"],
          "| ham kapsam:", round(toplama["kapsam"], 4))
    print("seri kanal   :", paket["dolu_kanal"], "/", paket["toplam_kanal"],
          "| anlik (kapsama SAYILMAZ):", paket["anlik_kanallar"])
    print("bar          :", len(paket["barlar15"]), "x 15M +",
          len(paket["barlar4h"] or []), "x 4H")
    print()
    print(metin_rapor(karar))
    iz = karar["iz"]
    print()
    print("bolme        :", {k: iz["halka_11"][k] for k in
                             ("train", "kalibrasyon", "test", "sizinti",
                              "giris_erisimi", "gereken_azami_ornek")})
    print("kalibrasyon  :", iz["halka_7"]["yarisma"])
    return karar
'''

YENI_MAIN = '''

def main(argv=None):
    import argparse
    ayristirici = argparse.ArgumentParser(description=SURUM)
    ayristirici.add_argument("--self-test", action="store_true",
                             help="gomulu 236 testi kosturur")
    ayristirici.add_argument("--esikler", action="store_true",
                             help="her sabiti kaynak+gerekcesiyle basar")
    ayristirici.add_argument("--oz-rapor", metavar="DOSYA",
                             help="sentetik uctan uca kosu -> JSON (ag YOK)")
    ayristirici.add_argument("--ornek", action="store_true",
                             help="AGSIZ ornek kosu (sahte veri)")
    ayristirici.add_argument("--canli", metavar="SEMBOL",
                             help="GERCEK Binance public GET ile kosar")
    ayristirici.add_argument("--lam", type=float, default=1.0)
    args = ayristirici.parse_args(argv)

    if args.self_test:
        return _oz_test()
    if args.esikler:
        print(esik_raporu())
        return 0
    if args.oz_rapor:
        rapor_yaz(_oz_kosu_kararlari(), args.oz_rapor)
        print("rapor yazildi: " + str(args.oz_rapor))
        return 0
    if args.ornek:
        _kosu_bas("BTCUSDT", _sahte_getir,
                  "ORNEK KOSU - SAHTE VERI (ag YOK). Gercek karar DEGILDIR.")
        return 0
    if args.canli:
        try:
            _kosu_bas(args.canli, None,
                      "CANLI KOSU - " + args.canli + " (public GET)")
        except Exception as hata:                    # ag/veri hatasi
            print("CANLI KOSU BASARISIZ (fail-closed): %s: %s"
                  % (type(hata).__name__, hata))
            print("Uydurma veriyle karar URETILMEZ.")
            return 1
        return 0

    print(SURUM + " - tek dosya. Secenekler:")
    print("  --self-test        236 testi kosturur")
    print("  --esikler          sabit beyani")
    print("  --ornek            AGSIZ ornek kosu")
    print("  --canli BTCUSDT    gercek veriyle kosu")
    print("  --oz-rapor r.json  sentetik kosu -> JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_BASLIK = '''

# ==========================================================================
# BOLUM 11 - TEST PAKETI (236 test). `--self-test` bunlari kosturur.
# ==========================================================================

import ast          # noqa: E402
import inspect      # noqa: E402
import json         # noqa: E402
import pathlib      # noqa: E402
import re           # noqa: E402
import shutil       # noqa: E402
import sys as _sys  # noqa: E402
import tempfile     # noqa: E402
import unittest     # noqa: E402

m = _sys.modules[__name__]   # testler kendi dosyasini denetler

'''

# --- 3b) TEK DOSYA ARTEFAKTLARI ------------------------------------------
# Kaynak TARAYAN testler artik KENDI metinlerini de goruyor. Ayri dosyada
# bu sorun yoktu. Cozum: tarayicilar MODUL bolumune kirpilir (sentinel'e
# kadar). Bu testleri ZAYIFLATMAK degil, DOGRU kaynagi gostermektir.
_YAMALAR = [
    # (a) guvenlik tarayicisi: testin KENDI yasak-desen listesini bulmasin
    ('        kaynak = pathlib.Path(m.__file__).read_text(encoding="utf-8")\n'
     '        for desen in self.YASAK:',
     '        kaynak = m._modul_kaynagi()\n'
     '        for desen in self.YASAK:'),
    # (b) eksen tarayicisi: testin kendi \'["p"][0]\' dizgesini bulmasin
    ('        kaynak = pathlib.Path(m.__file__).read_text(encoding="utf-8")\n'
     '        self.assertNotIn(\'["p"][0]\', kaynak)',
     '        kaynak = m._modul_kaynagi()\n'
     '        self.assertNotIn(\'["p"][0]\', kaynak)'),
    # (c) esik tarayicisi: FIKSTUR_BARI bir TEST sabitidir, motor esigi degil
    ("            if not ad.isupper() or ad.startswith(\"_\") or ad in self.MUAF:",
     "            if (not ad.isupper() or ad.startswith(\"_\")\n"
     "                    or ad in self.MUAF or ad in _TEST_SABITLERI):"),
    # (d) ozyineleme testi: tek dosyada --self-test ICINDEN kosar, yani
    #     bayrak DOGRU sekilde True'dur. Sinanacak sey bayragin degeri degil,
    #     ic ice kosunun ENGELLENDIGIDIR.
    ('        """Oz-test icinden tekrar cagrilirsa ic ice kosu YAPILMAZ."""\n'
     "        self.assertFalse(m.oz_test_kosuyor())",
     '        """Oz-test icinden tekrar cagrilirsa ic ice kosu YAPILMAZ."""\n'
     "        if m.oz_test_kosuyor():          # --self-test ICINDEN kosuyoruz\n"
     "            self.assertEqual(m._oz_test(), 0, \"ic ice kosu engellenmedi\")\n"
     "        else:                            # dogrudan unittest ile kosuyoruz\n"
     "            self.assertFalse(m.oz_test_kosuyor())"),
]
for eski, yeni in _YAMALAR:
    if eski not in test_govde:
        raise SystemExit("HATA: yama capasi bulunamadi ->\n" + eski[:120])
    test_govde = test_govde.replace(eski, yeni, 1)

tam = (BASLIK + "\n" + modul_govde.rstrip("\n") + "\n"
       + CANLI.rstrip("\n") + "\n"
       + TEST_BASLIK + test_govde.rstrip("\n") + "\n"
       + YENI_MAIN)

# test dosyasinin kendi __main__ blogunu at (bizimki sonda)
for _blok in ('if __name__ == "__main__":\n    unittest.main(verbosity=2)\n',
              'if __name__ == "__main__":\n    unittest.main()\n'):
    if _blok in tam:
        tam = tam.replace(_blok, "", 1)
        break
else:
    raise SystemExit("HATA: test __main__ blogu bulunamadi - elle kontrol et")

io.open(CIKTI, "w", encoding="utf-8").write(tam)
print("yazildi:", CIKTI)
print("satir  :", tam.count("\n") + 1)
