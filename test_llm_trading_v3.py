#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llm_trading_v3 icin test paketi.

Kritik test siniflari:
  GuvenlikTesti      - canli emir deseni kodda YOK
  DeterminizmTesti   - ayni girdi = ayni cikti
  KellyTesti         - maliyet sonrasi asimetrik Kelly ve basabas kimligi
  KalibrasyonMetrik  - ECE (bin duyarliligi), MCE, Brier, AUROC, grup
  ShrinkageTesti     - kanit yoksa f* matematiksel olarak 0
  GeometriTesti      - ilk-gecis muhafazakar, E[log] dogru
"""

import inspect
import math
import pathlib
import re
import unittest

import llm_trading_v3 as m


# ----------------------------------------------------------------- Task 1

class GuvenlikTesti(unittest.TestCase):
    """Kod canli emir gonderemez: yasakli desenler dosyada BULUNMAMALI."""

    YASAK = [
        r"api[_-]?key", r"apiKey", r"secret", r"hmac", r"signature=",
        r"/fapi/v1/order", r"/api/v5/trade/order", r"privateKey",
    ]

    def test_yasakli_desen_yok(self):
        kaynak = pathlib.Path(m.__file__).read_text(encoding="utf-8")
        for desen in self.YASAK:
            bulunan = re.findall(desen, kaynak, re.IGNORECASE)
            self.assertEqual(bulunan, [], f"yasakli desen bulundu: {desen} -> {bulunan}")


class DeterminizmTesti(unittest.TestCase):
    def test_ayni_tohum_ayni_dizi(self):
        a = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        b = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        self.assertEqual(a, b)

    def test_farkli_tohum_farkli_dizi(self):
        a = [m.tohumlu_rng("x", 1).random() for _ in range(5)]
        b = [m.tohumlu_rng("x", 2).random() for _ in range(5)]
        self.assertNotEqual(a, b)

    def test_sabit_kimlik_deterministik(self):
        self.assertEqual(m.sabit_kimlik("BTCUSDT", "15m", 3),
                         m.sabit_kimlik("BTCUSDT", "15m", 3))
        self.assertNotEqual(m.sabit_kimlik("BTCUSDT", "15m", 3),
                            m.sabit_kimlik("BTCUSDT", "15m", 4))


class KirpTesti(unittest.TestCase):
    def test_sinirlar(self):
        self.assertEqual(m.kirp(5.0, -1.0, 1.0), 1.0)
        self.assertEqual(m.kirp(-5.0, -1.0, 1.0), -1.0)
        self.assertEqual(m.kirp(0.3, -1.0, 1.0), 0.3)

    def test_gecersiz_girdi_alt_sinira_duser(self):
        self.assertEqual(m.kirp(None, -1.0, 1.0), -1.0)
        self.assertEqual(m.kirp(float("nan"), -1.0, 1.0), -1.0)


# ----------------------------------------------------------------- Task 2

class KellyTesti(unittest.TestCase):
    def test_net_kanatlar(self):
        b, a = m.net_kanatlar(R=1.3333, cost_r=0.6)
        self.assertAlmostEqual(b, 0.7333, places=4)
        self.assertAlmostEqual(a, 1.6000, places=4)

    def test_basabas_p_bilinen_deger(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        self.assertAlmostEqual(m.basabas_p(b, a), 0.6857, places=4)

    def test_basabas_p_maliyetsiz(self):
        b, a = m.net_kanatlar(1.3333, 0.0)
        self.assertAlmostEqual(m.basabas_p(b, a), 0.4286, places=4)

    def test_kelly_basabasin_altinda_sifir(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        for p in (0.50, 0.60, 0.68):
            self.assertEqual(m.kelly_asimetrik(p, b, a), 0.0,
                             f"p={p} icin f* 0 olmali")

    def test_kelly_basabasin_ustunde_pozitif(self):
        b, a = m.net_kanatlar(1.3333, 0.60)
        f = m.kelly_asimetrik(0.70, b, a)
        self.assertGreater(f, 0.0)
        self.assertAlmostEqual(f, 0.0284, places=3)

    def test_kelly_negatif_kanat_sifir(self):
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        self.assertLessEqual(b, 0.0)
        self.assertEqual(m.kelly_asimetrik(0.99, b, a), 0.0)

    def test_basabas_p_negatif_kanatta_none(self):
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        self.assertIsNone(m.basabas_p(b, a))

    def test_maliyet_r_hesabi(self):
        cr = m.maliyet_r(giris=100.0, stop_mesafesi=0.15,
                         komisyon=0.0004, kayma=0.0005, funding=0.0)
        self.assertAlmostEqual(cr, (2 * 100.0 * 0.0009) / 0.15, places=8)

    def test_maliyet_r_sifir_stopta_sonsuz_degil(self):
        cr = m.maliyet_r(100.0, 0.0, 0.0004, 0.0005, 0.0)
        self.assertTrue(math.isfinite(cr))
        self.assertGreater(cr, 1000.0)


# ----------------------------------------------------------------- Task 3

class KalibrasyonMetrikTesti(unittest.TestCase):
    def test_wilson_bilinen_deger(self):
        alt, ust = m.wilson_araligi(17, 48)
        self.assertAlmostEqual(alt, 0.2343, places=3)
        self.assertAlmostEqual(ust, 0.4956, places=3)

    def test_wilson_sifir_deneme(self):
        alt, ust = m.wilson_araligi(0, 0)
        self.assertEqual((alt, ust), (0.0, 1.0))

    def test_ece_mukemmel_kalibre_sifir(self):
        ciftler = [(1.0, 1)] * 50 + [(0.0, 0)] * 50
        self.assertAlmostEqual(m.ece(ciftler), 0.0, places=9)

    def test_ece_tam_ters_bir(self):
        ciftler = [(1.0, 0)] * 50 + [(0.0, 1)] * 50
        self.assertAlmostEqual(m.ece(ciftler), 1.0, places=9)

    def test_ece_tek_bine_cokme_tespiti(self):
        ciftler = [(0.335, 1) if i % 3 == 0 else (0.335, 0) for i in range(48)]
        rapor = m.ece_duyarlilik(ciftler)
        self.assertTrue(rapor["tek_bine_cokme"], "tek bine cokme tespit edilmeli")

    def test_ece_duyarlilik_dagilmis_veride_cokme_yok(self):
        ciftler = [(i / 100.0, 1 if i > 50 else 0) for i in range(1, 100)]
        rapor = m.ece_duyarlilik(ciftler)
        self.assertFalse(rapor["tek_bine_cokme"])

    def test_brier_bilinen_deger(self):
        ciftler = [(0.5, 1)] * 10 + [(0.5, 0)] * 10
        self.assertAlmostEqual(m.brier(ciftler), 0.25, places=9)

    def test_auroc_mukemmel_ayirici(self):
        ciftler = [(0.9, 1)] * 10 + [(0.1, 0)] * 10
        self.assertAlmostEqual(m.auroc(ciftler), 1.0, places=9)

    def test_auroc_ayirt_edemeyen(self):
        ciftler = [(0.5, 1)] * 10 + [(0.5, 0)] * 10
        self.assertAlmostEqual(m.auroc(ciftler), 0.5, places=9)

    def test_mce_en_kotu_kovayi_verir(self):
        """PD-2: mce() uygulanmisti ama testi yoktu."""
        # iyi kova: guven 0.95, dogruluk 1.0 -> fark 0.05
        # kotu kova: guven 0.55, dogruluk 0.0 -> fark 0.55
        ciftler = [(0.95, 1)] * 20 + [(0.55, 0)] * 20
        self.assertAlmostEqual(m.mce(ciftler), 0.55, places=9)

    def test_mce_ece_den_buyuk_esit(self):
        ciftler = [(0.95, 1)] * 20 + [(0.55, 0)] * 20
        self.assertGreaterEqual(m.mce(ciftler), m.ece(ciftler))

    def test_mce_bos_girdide_none(self):
        self.assertIsNone(m.mce([]))

    def test_grup_ece_en_kotuyu_bulur(self):
        gruplu = {
            "buyuk": [(0.8, 1)] * 95 + [(0.8, 0)] * 5,
            "kucuk": [(0.9, 0)] * 5,
        }
        rapor = m.grup_ece(gruplu)
        self.assertEqual(rapor["en_kotu"][0], "kucuk")
        self.assertGreater(rapor["en_kotu"][1], rapor["gruplar"]["buyuk"])


# ----------------------------------------------------------------- Task 4

class ShrinkageTesti(unittest.TestCase):
    def test_kanit_yoksa_s_sifir(self):
        r = m.shrinkage_katsayisi(dogru=17, toplam=48, ece_enkotu=0.02,
                                  dolu_kanal=5, toplam_kanal=5)
        self.assertEqual(r["s_kanit"], 0.0)
        self.assertEqual(r["s"], 0.0)

    def test_guclu_kanit_s_pozitif(self):
        r = m.shrinkage_katsayisi(dogru=900, toplam=1000, ece_enkotu=0.01,
                                  dolu_kanal=5, toplam_kanal=5)
        self.assertGreater(r["s_kanit"], 0.5)
        self.assertGreater(r["s"], 0.5)

    def test_kapsam_dususu_s_dusurur(self):
        tam = m.shrinkage_katsayisi(900, 1000, 0.01, 5, 5)["s"]
        yarim = m.shrinkage_katsayisi(900, 1000, 0.01, 2, 5)["s"]
        self.assertLess(yarim, tam)
        self.assertAlmostEqual(yarim / tam, 2 / 5, places=6)

    def test_kotu_kalibrasyon_s_dusurur(self):
        iyi = m.shrinkage_katsayisi(900, 1000, 0.00, 5, 5)["s"]
        kotu = m.shrinkage_katsayisi(900, 1000, 0.10, 5, 5)["s"]
        self.assertEqual(kotu, 0.0)
        self.assertGreater(iyi, 0.0)

    def test_ece_olculemedi_ise_s_sifir(self):
        r = m.shrinkage_katsayisi(900, 1000, None, 5, 5)
        self.assertEqual(r["s_kalibrasyon"], 0.0)
        self.assertEqual(r["s"], 0.0)

    def test_daralt_sifir_s_sansa_ceker(self):
        self.assertAlmostEqual(m.daralt(0.95, 0.0), 0.5, places=9)

    def test_daralt_bir_s_degistirmez(self):
        self.assertAlmostEqual(m.daralt(0.95, 1.0), 0.95, places=9)

    def test_daralt_ara_deger(self):
        self.assertAlmostEqual(m.daralt(0.90, 0.5), 0.70, places=9)


class ShrinkageKellyEntegrasyonTesti(unittest.TestCase):
    """Sozlesmenin cekirdegi: kanit yoksa f* matematigin kendisiyle 0 olur.

    NOT: bu testin ilk hali daralt(p, s) -> kelly() zincirini cagiriyordu ve
    f*=0.0905 verdi. Kok neden: 0.5 hedefli daraltma, odul asimetrikken
    (b>a) bahsin EV'sini sifirlamaz. Tarafsiz hedef basabas olasiligidir.
    Sozlesme artik stake_hesapla icinde garanti edilir.
    """

    def test_kanit_yokken_stake_sifir(self):
        r = m.shrinkage_katsayisi(17, 48, 0.02, 5, 5)
        b, a = m.net_kanatlar(R=2.0, cost_r=0.3)
        sonuc = m.stake_hesapla(0.95, r["s"], b, a)
        self.assertEqual(sonuc["f"], 0.0)

    def test_kanit_yokken_stake_sifir_her_geometride(self):
        r = m.shrinkage_katsayisi(17, 48, 0.02, 5, 5)
        for R, cost_r in ((1.3333, 0.6), (2.0, 0.3), (3.0, 0.1),
                          (5.0, 0.05), (1.5, 0.0)):
            b, a = m.net_kanatlar(R, cost_r)
            sonuc = m.stake_hesapla(0.95, r["s"], b, a)
            self.assertAlmostEqual(sonuc["f"], 0.0, places=12,
                                   msg=f"R={R} cost_r={cost_r} icin f* 0 olmali")

    def test_eski_zincir_neden_yetmiyordu(self):
        """Regresyon korumasi: 0.5 hedefli daraltma sozlesmeyi SAGLAMAZ."""
        b, a = m.net_kanatlar(R=2.0, cost_r=0.3)
        p_yanlis = m.daralt(0.95, 0.0, hedef=0.5)
        self.assertGreater(m.kelly_asimetrik(p_yanlis, b, a), 0.0)

    def test_guclu_kanitla_stake_pozitif(self):
        r = m.shrinkage_katsayisi(900, 1000, 0.01, 5, 5)
        b, a = m.net_kanatlar(R=3.0, cost_r=0.1)
        sonuc = m.stake_hesapla(0.85, r["s"], b, a)
        self.assertGreater(sonuc["f"], 0.0)

    def test_lambda_stake_olcekler(self):
        r = m.shrinkage_katsayisi(900, 1000, 0.01, 5, 5)
        b, a = m.net_kanatlar(R=3.0, cost_r=0.1)
        tam = m.stake_hesapla(0.85, r["s"], b, a, lam=1.0)["f"]
        ceyrek = m.stake_hesapla(0.85, r["s"], b, a, lam=0.25)["f"]
        self.assertAlmostEqual(ceyrek, tam * 0.25, places=12)

    def test_kazanc_kanadi_yoksa_bahis_imkansiz(self):
        b, a = m.net_kanatlar(R=1.0, cost_r=1.5)
        sonuc = m.stake_hesapla(0.99, 1.0, b, a)
        self.assertEqual(sonuc["f"], 0.0)
        self.assertIsNone(sonuc["p0"])
        self.assertIn("imkansiz", sonuc["not"])


# ----------------------------------------------------------------- Task 5

class EsikEtiketiTesti(unittest.TestCase):
    """PD-3: depo sozlesmesi (CLAUDE.md) etiketsiz gizli esigi YASAKLIYOR.

    Kalibre edilemeyen her sabit, kaynagi ve gerekcesiyle beyan edilmeli.
    """

    def test_esik_kaynagi_sozlugu_var(self):
        self.assertTrue(hasattr(m, "ESIK_KAYNAGI"))

    # Etiket gerektirmeyen sabitler: kimlik/yapisal, istatistiksel secim DEGIL.
    MUAF = {
        "SURUM", "SEMBOLLER", "YON_SOZLUGU", "EPSILON", "ESIK_KAYNAGI",
        "KANALLAR", "ZAMAN_DILIMLERI", "AILELER", "IZGARA", "LAMBDA_TABLOSU",
        "SICAKLIK_IZGARASI", "SEMBOL_EKSENI_FAZI",
    }

    def test_her_sabit_esik_etiketli(self):
        """Denetci bulgusu: sabit ad listesi YENI esikleri yakalayamiyordu.

        Artik modul TARANIYOR - eklenen her sayisal BUYUK_HARF sabiti ya
        ESIK_KAYNAGI'nda beyan edilmeli ya MUAF listesinde gerekcelenmeli.
        """
        etiketsiz = []
        for ad in dir(m):
            if not ad.isupper() or ad.startswith("_") or ad in self.MUAF:
                continue
            if not isinstance(getattr(m, ad), (int, float)):
                continue
            if ad not in m.ESIK_KAYNAGI:
                etiketsiz.append(ad)
        self.assertEqual(etiketsiz, [],
                         f"etiketsiz gizli esik YASAK: {etiketsiz}")

    def test_etiket_zorunlu_alanlari_icerir(self):
        for ad, kayit in m.ESIK_KAYNAGI.items():
            for alan in ("deger", "kaynak", "gerekce"):
                self.assertIn(alan, kayit, f"{ad}.{alan} eksik")

    def test_etiket_degeri_gercek_sabitle_ayni(self):
        self.assertEqual(m.ESIK_KAYNAGI["ECE_TAVANI"]["deger"], m.ECE_TAVANI)
        self.assertEqual(m.ESIK_KAYNAGI["ASGARI_OLCUM"]["deger"], m.ASGARI_OLCUM)

    def test_kalibre_edilmemis_esik_acikca_beyan_edilir(self):
        """Kaynak 'VARSAYIM' ise gerekce bos birakilamaz."""
        for ad, kayit in m.ESIK_KAYNAGI.items():
            if kayit["kaynak"] == "VARSAYIM":
                self.assertTrue(kayit["gerekce"].strip(),
                                f"{ad} VARSAYIM ama gerekcesi bos")

    def test_esik_raporu_metin_uretir(self):
        metin = m.esik_raporu()
        self.assertIn("ECE_TAVANI", metin)
        self.assertIn("VARSAYIM", metin)


class GeometriTesti(unittest.TestCase):
    def test_ilk_gecis_ayni_barda_iki_bariyer_stop_sayilir(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 103, "l": 98, "c": 100},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["stop"], 1)
        self.assertEqual(r["hedef"], 0)

    def test_ilk_gecis_hedef_once(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 103, "l": 99.5, "c": 102},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["hedef"], 1)
        self.assertAlmostEqual(r["p_hedef"], 1.0, places=9)

    def test_ilk_gecis_zaman_asimi_paydaya_girmez(self):
        barlar = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 4
        r = m.ilk_gecis_olcum(barlar, [0], "LONG", 1.0, 2.0, [1.0] * 4, azami_bar=2)
        self.assertEqual(r["zaman_asimi"], 1)
        self.assertIsNone(r["p_hedef"])

    def test_ilk_gecis_short_simetrik(self):
        barlar = [
            {"o": 100, "h": 100, "l": 100, "c": 100},
            {"o": 100, "h": 100.5, "l": 97, "c": 98},
        ]
        r = m.ilk_gecis_olcum(barlar, [0], "SHORT", 1.0, 2.0, [1.0, 1.0], azami_bar=5)
        self.assertEqual(r["hedef"], 1)

    def test_beklenen_log_sifir_stake_sifir(self):
        self.assertAlmostEqual(m.beklenen_log(0.7, 0.0, 1.0, 1.0), 0.0, places=9)

    def test_beklenen_log_bilinen_deger(self):
        beklenen = 0.5 * math.log(1.1) + 0.5 * math.log(0.9)
        self.assertAlmostEqual(m.beklenen_log(0.5, 0.1, 1.0, 1.0), beklenen, places=9)

    def test_beklenen_log_iflas_riskinde_sonsuz_negatif(self):
        self.assertEqual(m.beklenen_log(0.5, 1.0, 1.0, 1.0), float("-inf"))


# ----------------------------------------------------------------- Task 6

class GeometriSecimTesti(unittest.TestCase):
    def _yukselen_barlar(self, n=200):
        barlar = []
        fiyat = 100.0
        for _ in range(n):
            fiyat *= 1.002
            barlar.append({"o": fiyat, "h": fiyat * 1.004,
                           "l": fiyat * 0.999, "c": fiyat})
        return barlar

    def test_geometri_sec_bir_aday_dondurur(self):
        barlar = self._yukselen_barlar()
        atr = [b["c"] * 0.003 for b in barlar]
        indeksler = list(range(0, 150, 5))
        r = m.geometri_sec(barlar, indeksler, "LONG", atr, p_yon=0.6,
                           cost_r_fn=lambda sk: 0.05, lam=1.0, azami_bar=20)
        for alan in ("stop_k", "hedef_k", "R", "p_hedef", "elog"):
            self.assertIn(alan, r)
        self.assertIn((r["stop_k"], r["hedef_k"]), m.IZGARA)

    def test_geometri_sec_olcum_yoksa_fail_closed(self):
        barlar = [{"o": 100, "h": 100, "l": 100, "c": 100}] * 5
        atr = [1.0] * 5
        r = m.geometri_sec(barlar, [0], "LONG", atr, 0.9,
                           lambda sk: 0.05, 1.0, azami_bar=2)
        self.assertEqual(r["f"], 0.0)
        self.assertIsNone(r["p_hedef"])
        self.assertIn("OLCUM YOK", r["not"])

    def test_geometri_sec_yuksek_maliyette_stake_sifir(self):
        barlar = self._yukselen_barlar()
        atr = [b["c"] * 0.003 for b in barlar]
        r = m.geometri_sec(barlar, list(range(0, 150, 5)), "LONG", atr, 0.6,
                           cost_r_fn=lambda sk: 5.0, lam=1.0, azami_bar=20)
        self.assertEqual(r["f"], 0.0)

    def test_likidasyon_tavani_okunamazsa_sifir(self):
        self.assertEqual(m.likidasyon_tavani(100.0, None, 100.0, 0.5), 0.0)

    def test_likidasyon_tavani_mesafeden_gelir(self):
        tavan = m.likidasyon_tavani(100.0, 80.0, 10.0, 0.5)
        self.assertAlmostEqual(tavan, 0.10, places=9)

    def test_stake_kirp_kirpma_bildirilir(self):
        r = m.stake_kirp(0.5, 0.1)
        self.assertAlmostEqual(r["f"], 0.1, places=9)
        self.assertTrue(r["kirpildi"])

    def test_stake_kirp_kirpma_yoksa_bayrak_kapali(self):
        r = m.stake_kirp(0.05, 0.1)
        self.assertAlmostEqual(r["f"], 0.05, places=9)
        self.assertFalse(r["kirpildi"])


# ----------------------------------------------------------------- Task 7

class AdaptorTesti(unittest.TestCase):
    def test_kapsam_tam_veride_bir(self):
        def sahte_getir(url, params):
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertEqual(r["kapsam"], 1.0)
        self.assertEqual(r["adaptor"], "binance")
        self.assertEqual(r["dusen"], [])

    def test_kanal_dusunce_kapsam_duser_ve_uydurulmaz(self):
        def sahte_getir(url, params):
            if "openInterest" in url:
                raise OSError("erisilemedi")
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertLess(r["kapsam"], 1.0)
        self.assertIsNone(r["kanallar"]["oi"])
        self.assertIn("oi", r["dusen"])

    def test_ana_adaptor_tamamen_duserse_yedege_gecer_ve_bildirir(self):
        def sahte_getir(url, params):
            if "binance" in url:
                raise OSError("403")
            return {"ok": True, "veri": [1, 2, 3]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor(), m.OkxAdaptor()], sahte_getir)
        self.assertEqual(r["adaptor"], "okx")
        self.assertTrue(r["yedege_dusuldu"])

    def test_hicbir_adaptor_calismazsa_kapsam_sifir(self):
        def sahte_getir(url, params):
            raise OSError("hepsi kapali")
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor(), m.OkxAdaptor()], sahte_getir)
        self.assertEqual(r["kapsam"], 0.0)
        self.assertTrue(all(v is None for v in r["kanallar"].values()))

    def test_notr_sifir_enjekte_edilmez(self):
        """Uydurma yasagi: dusen kanal None olmali, 0.0 OLMAMALI."""
        def sahte_getir(url, params):
            if "premiumIndex" in url or "funding-rate" in url:
                raise OSError("yok")
            return {"ok": True, "veri": [1]}
        r = m.veri_topla("BTCUSDT", [m.BinanceAdaptor()], sahte_getir)
        self.assertIsNone(r["kanallar"]["funding"])
        self.assertNotEqual(r["kanallar"]["funding"], 0.0)

    def test_okx_sembol_cevrimi(self):
        u, _ = m.OkxAdaptor().uc("kline_15m", "BTCUSDT")
        self.assertIn("BTC-USDT-SWAP", str(_))

    def test_binance_dogru_period_parametresi(self):
        """OKX SDK'da parametre adi 'period'; 'periodic' gecersizdir."""
        _, params = m.BinanceAdaptor().uc("oi", "BTCUSDT")
        self.assertIn("period", params)
        self.assertNotIn("periodic", params)

    def test_okx_dogru_period_parametresi(self):
        _, params = m.OkxAdaptor().uc("oi", "BTCUSDT")
        self.assertIn("period", params)
        self.assertNotIn("periodic", params)

    def test_hicbir_adaptor_emir_ucu_uretmez(self):
        for adaptor in (m.BinanceAdaptor(), m.OkxAdaptor()):
            for kanal in m.KANALLAR:
                url, _ = adaptor.uc(kanal, "BTCUSDT")
                self.assertNotIn("order", url.lower())
                self.assertNotIn("trade", url.lower())


# ----------------------------------------------------------------- Task 8

class TokenSozluguTesti(unittest.TestCase):
    def test_ayni_anahtar_ayni_kimlik(self):
        s = m.TokenSozlugu()
        self.assertEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                         s.kimlik("BTCUSDT", "15m", "fiyat", 0))

    def test_farkli_zaman_dilimi_farkli_kimlik(self):
        s = m.TokenSozlugu()
        self.assertNotEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                            s.kimlik("BTCUSDT", "4h", "fiyat", 0))

    def test_farkli_gecikme_farkli_kimlik(self):
        s = m.TokenSozlugu()
        self.assertNotEqual(s.kimlik("BTCUSDT", "15m", "fiyat", 0),
                            s.kimlik("BTCUSDT", "15m", "fiyat", 1))

    def test_sozluk_buyur(self):
        s = m.TokenSozlugu()
        self.assertEqual(s.boyut, 0)
        s.kimlik("BTCUSDT", "15m", "fiyat", 0)
        s.kimlik("BTCUSDT", "15m", "fiyat", 1)
        self.assertEqual(s.boyut, 2)

    def test_token_listesi_iki_zaman_dilimi_icerir(self):
        tokenlar = m.token_listesi(["BTCUSDT"], gecikme_sayisi=2)
        zamanlar = {t["zaman_dilimi"] for t in tokenlar}
        self.assertEqual(zamanlar, set(m.ZAMAN_DILIMLERI))

    def test_token_listesi_beklenen_sayida(self):
        tokenlar = m.token_listesi(["BTCUSDT", "ETHUSDT"], gecikme_sayisi=3)
        beklenen = 2 * len(m.ZAMAN_DILIMLERI) * len(m.AILELER) * 3
        self.assertEqual(len(tokenlar), beklenen)

    def test_turev_ailesi_sozlukte_var(self):
        self.assertIn("turev", m.AILELER)

    def test_token_listesi_eskiden_yeniye_sirali(self):
        tokenlar = m.token_listesi(["BTCUSDT"], gecikme_sayisi=3)
        gecikmeler = [t["gecikme"] for t in tokenlar]
        self.assertEqual(gecikmeler[0], 2)
        self.assertEqual(gecikmeler[-1], 0)


# ----------------------------------------------------------------- Task 9

class OlcekleyiciTesti(unittest.TestCase):
    def _satirlar(self, n=100):
        return [{"fiyat": [i * 0.01] * m.AILELER["fiyat"],
                 "hacim": [0.0] * m.AILELER["hacim"],
                 "turev": [i * 0.02] * m.AILELER["turev"],
                 "oynaklik": [1.0] * m.AILELER["oynaklik"]} for i in range(n)]

    def test_yalniz_train_diliminden_fit(self):
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        o2 = m.Olcekleyici()
        o2.fit(satirlar[:50], kesim=50)
        self.assertEqual(o.donustur("fiyat", [0.25] * m.AILELER["fiyat"]),
                         o2.donustur("fiyat", [0.25] * m.AILELER["fiyat"]))

    def test_sabit_kolon_isaretlenir(self):
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        self.assertIn(("hacim", 0), o.sabit_kolonlar)

    def test_sabit_kolonda_donusum_sifir_verir(self):
        """Sabit kolon bilgi tasimaz: ham deger SIZDIRILMAZ, 0.0 verilir."""
        satirlar = self._satirlar(100)
        o = m.Olcekleyici()
        o.fit(satirlar, kesim=50)
        self.assertEqual(o.donustur("hacim", [999.0, 999.0]), [0.0, 0.0])

    def test_fit_edilmeden_donusum_hata_verir(self):
        o = m.Olcekleyici()
        with self.assertRaises(RuntimeError):
            o.donustur("fiyat", [0.0] * m.AILELER["fiyat"])


class KonumKoduTesti(unittest.TestCase):
    def test_zaman_konumu_gecikmeye_gore_degisir(self):
        self.assertNotEqual(m.zaman_konumu(0, 16), m.zaman_konumu(1, 16))

    def test_zaman_konumu_deterministik(self):
        self.assertEqual(m.zaman_konumu(3, 16), m.zaman_konumu(3, 16))

    def test_sembol_konumu_ayri_eksen(self):
        """Sembol ekseni zaman ekseninden BAGIMSIZ olmali."""
        z0 = m.zaman_konumu(0, 16)
        s0 = m.sembol_konumu(0, 16)
        s1 = m.sembol_konumu(1, 16)
        self.assertNotEqual(s0, s1)
        self.assertNotEqual(s0, z0)

    def test_konum_boyutu_dogru(self):
        self.assertEqual(len(m.zaman_konumu(2, 16)), 16)
        self.assertEqual(len(m.sembol_konumu(2, 16)), 16)

    def test_ayni_indekste_iki_eksen_ayrisir(self):
        """Ayni sayisal indeks, iki eksende FARKLI vektor uretmeli."""
        for k in range(1, 5):
            self.assertNotEqual(m.zaman_konumu(k, 16), m.sembol_konumu(k, 16))

    def _l2(self, a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def test_faz_olculen_ayrisma_degeri(self):
        """SEMBOL_EKSENI_FAZI docstring'indeki SAYIYI kilitler.

        Denetci bulgusu (SAHTE_KANIT): docstring'e once boyut=4 ve olceksiz
        bir deneme kosusundan alinan 1.08..1.58 yazilmisti; fonksiyonun
        gercek ciktisi (boyut=16, 0.10 olcek) 0.2165..0.2970'tir. Bu test
        sayiyi artefakta baglar - bir daha kaynaksiz sayi yazilamaz.
        """
        beklenen = [0.216478, 0.243442, 0.270609, 0.297025]
        for k, deger in enumerate(beklenen):
            self.assertAlmostEqual(
                self._l2(m.zaman_konumu(k, 16), m.sembol_konumu(k, 16)),
                deger, places=6, msg=f"konum={k} icin olculen deger degisti")

    def test_fazsiz_kurulum_sifirda_tam_cakisir(self):
        """Fazin NEDEN gerekli oldugunun kaniti: fazsiz L2 tam 0."""
        fazsiz = [x * 0.10 for x in m._sinuzoidal(0, 16, 97.0, faz=0.0)]
        self.assertAlmostEqual(self._l2(m.zaman_konumu(0, 16), fazsiz),
                               0.0, places=12)


# ---------------------------------------------------------------- Task 10

class OluHalkaTesti(unittest.TestCase):
    """Sozlesmenin 1. kabul olcutu: hicbir halka olu olmamali.

    Her halka icin, o halka devre disi birakilinca nihai ciktinin
    OLCULEBILIR bicimde degistigi kanitlanir.
    """

    def _kodlayici_ve_durumlar(self, n=9, d=16):
        kod = m.Kodlayici(boyut=d, bas_sayisi=2, tohum=2026)
        rng = m.tohumlu_rng("test-durum", n, d)
        durumlar = [[rng.uniform(-1, 1) for _ in range(d)] for _ in range(n)]
        return kod, durumlar

    def _fark(self, a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def test_qk_terimi_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        self.assertGreater(
            self._fark(kod.ileri(durumlar, qk_acik=True),
                       kod.ileri(durumlar, qk_acik=False)), 1e-6,
            "QK terimi ciktiyi degistirmiyor -> olu halka")

    def test_nedensel_maske_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        self.assertGreater(
            self._fark(kod.ileri(durumlar, maske_acik=True),
                       kod.ileri(durumlar, maske_acik=False)), 1e-6,
            "Nedensel maske ciktiyi degistirmiyor -> olu halka")

    def test_ffn_ciktiyi_degistirir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        self.assertGreater(
            self._fark(kod.ileri(durumlar, ffn_acik=True),
                       kod.ileri(durumlar, ffn_acik=False)), 1e-6,
            "FFN ciktiyi degistirmiyor -> olu halka")

    def test_girdi_degisince_cikti_degisir(self):
        kod, durumlar = self._kodlayici_ve_durumlar()
        rng = m.tohumlu_rng("test-durum-2", 9, 16)
        baska = [[rng.uniform(-1, 1) for _ in range(16)] for _ in range(9)]
        self.assertGreater(self._fark(kod.ileri(durumlar), kod.ileri(baska)), 1e-3)

    def test_temsil_piyasaya_duyarli(self):
        """63-bulgu #0'in panzehiri: temsilin %99'u sabit OLMAMALI."""
        kod = m.Kodlayici(boyut=16, bas_sayisi=2, tohum=2026)
        ciktilar = []
        for k in range(20):
            rng = m.tohumlu_rng("duyarlilik", k)
            durumlar = [[rng.uniform(-1, 1) for _ in range(16)] for _ in range(9)]
            ciktilar.append(kod.ileri(durumlar))
        ortalama = [sum(c[j] for c in ciktilar) / len(ciktilar) for j in range(16)]
        sapma = [math.sqrt(sum((c[j] - ortalama[j]) ** 2 for c in ciktilar) / len(ciktilar))
                 for j in range(16)]
        norm_ort = math.sqrt(sum(x * x for x in ortalama))
        norm_sap = math.sqrt(sum(x * x for x in sapma))
        degisken_pay = norm_sap / math.sqrt(norm_sap ** 2 + norm_ort ** 2)
        self.assertGreater(degisken_pay, 0.10,
                           f"temsil %{degisken_pay*100:.1f} degisken - cok sabit")


class SoftmaxTesti(unittest.TestCase):
    def test_toplam_bir(self):
        self.assertAlmostEqual(sum(m.kararli_softmax([1.0, 2.0, 3.0])), 1.0, places=9)

    def test_sicaklik_tek_softmaxta_sirayi_degistirmez(self):
        for T in (0.1, 1.0, 10.0):
            p = m.kararli_softmax([3.0, 1.0], T)
            self.assertGreater(p[0], p[1])

    def test_buyuk_deger_tasmaz(self):
        p = m.kararli_softmax([1000.0, 999.0])
        self.assertTrue(all(math.isfinite(x) for x in p))


# ---------------------------------------------------------------- Task 11

class SizintiTesti(unittest.TestCase):
    def test_purge_embargo_ortusmeyi_keser(self):
        b = m.kronolojik_bol(list(range(0, 400, 5)), ufuk=16, embargo=4)
        self.assertFalse(m.sizinti_var_mi(b, ufuk=16, giris_penceresi=6),
                         "purge/embargo etiket penceresini kesmeli")

    def test_purge_yoksa_sizinti_tespit_edilir(self):
        b = m.kronolojik_bol(list(range(0, 400, 5)), ufuk=0, embargo=0)
        self.assertTrue(m.sizinti_var_mi(b, ufuk=16, giris_penceresi=6))

    def test_bolme_kronolojik_sirali(self):
        b = m.kronolojik_bol(list(range(0, 400, 5)), ufuk=16, embargo=4)
        self.assertLess(max(b["train"]), min(b["kalibrasyon"]))
        self.assertLess(max(b["kalibrasyon"]), min(b["test"]))

    def test_atilan_ornek_sayilir(self):
        indeksler = list(range(0, 400, 5))
        b = m.kronolojik_bol(indeksler, ufuk=16, embargo=4)
        toplam = len(b["train"]) + len(b["kalibrasyon"]) + len(b["test"])
        self.assertEqual(toplam + b["atilan"], len(indeksler))
        self.assertGreater(b["atilan"], 0)

    def test_cok_az_veride_bos_bolme(self):
        b = m.kronolojik_bol([1, 2, 3], ufuk=16, embargo=4)
        self.assertEqual(b["train"], [])
        self.assertIn("yetersiz", b["not"])

    # -- 4H token erisimi: purge/embargo penceresi 15M gecikmesi DEGILDIR --

    def test_girdi_erisimi_gosterge_penceresinden_turetilir(self):
        """Erisim TOKEN GECIKMESI DEGIL, ozniteligin okudugu bar sayisidir.

        Olculdu: gecikme yalniz 4 bar sayarken _z(atr) uzerinden gercek
        okuma 62 bara uzaniyordu; 4 barlik pencereyle yapilan sizinti
        denetimi fail-open bir rapordur.
        """
        W = m.oznitelik_penceresi()
        self.assertGreaterEqual(W, m.YUVARLANAN_PENCERE + 14,
                                "_z(atr) zinciri: 48 pencere USTUNE ATR periyodu")
        self.assertEqual(m.girdi_erisimi(4, h4_var=False),
                         (4 - 1) + W)
        self.assertEqual(m.girdi_erisimi(4, h4_var=True),
                         (4 - 1) + (2 * m.H4_BAR_ORANI - 1) + m.H4_BAR_ORANI * W)

    def test_girdi_erisimi_gercek_okumayi_KAPSAR(self):
        """Beyan edilen erisim, perturbasyonla OLCULEN erisimden kucuk olamaz.

        Fail-closed yon: beyan >= gercek. Bu test formulu gercege karsi
        sinar; formul kucuk kalirsa sizinti raporu yalan olur.
        """
        rng = m.tohumlu_rng("erisim-kapsam")
        n, hedef = 400, 350
        barlar, f = [], 100.0
        for _ in range(n):
            f *= 1.0 + rng.uniform(-0.004, 0.004)
            barlar.append({"o": f, "h": f * 1.003, "l": f * 0.997, "c": f,
                           "v": rng.uniform(80.0, 120.0)})

        def satir(bs):
            return m.satir_uret(bs, m._gostergeler(bs), None, hedef)

        taban = satir(barlar)
        en_uzak = 0
        for d in range(1, hedef + 1):
            bozuk = [dict(b) for b in barlar]
            for anahtar in ("o", "h", "l", "c"):
                bozuk[hedef - d][anahtar] *= 1.001
            if satir(bozuk) != taban:
                en_uzak = d
        self.assertLessEqual(en_uzak, m.girdi_erisimi(1, h4_var=False),
                             f"olculen erisim {en_uzak} beyani asti")
        self.assertGreater(en_uzak, m.YUVARLANAN_PENCERE,
                           "olcum kurulumu bozuk: erisim pencereden kucuk cikti")

    def test_sizinti_denetimi_4h_erisimini_hesaba_katar(self):
        """Ayni bolme: 15M penceresiyle 'temiz', gercek erisimle SIZINTILI.

        Fail-open rapor yasagi: olculmeyen sey 'yok' diye raporlanamaz.
        """
        e15 = m.girdi_erisimi(4, h4_var=False)      # olculdu: 65
        e4h = m.girdi_erisimi(4, h4_var=True)       # olculdu: 1026
        bolme = {"train": list(range(0, 4000, 40)),
                 "kalibrasyon": list(range(4200, 5400, 40)),
                 "test": list(range(5600, 6600, 40))}
        self.assertFalse(m.sizinti_var_mi(bolme, 16, e15),
                         "15M penceresiyle bu bolme temiz gorunur")
        self.assertTrue(m.sizinti_var_mi(bolme, 16, e4h),
                        "4H erisimiyle AYNI bolme sizintilidir")

    def test_bolme_giris_erisimi_kadar_purge_eder(self):
        erisim = m.girdi_erisimi(4, h4_var=True)
        indeksler = list(range(0, 30000, 60))
        b = m.kronolojik_bol(indeksler, ufuk=16, embargo=4, giris_erisimi=erisim)
        self.assertTrue(b["train"] and b["kalibrasyon"] and b["test"],
                        "yeterli veride erisim eklenince bolme dejenere OLMAMALI")
        self.assertGreaterEqual(b["kalibrasyon"][0] - b["train"][-1], 16 + 4 + erisim)
        self.assertFalse(m.sizinti_var_mi(b, 16, erisim))

    def test_veri_yetmezse_bolme_fail_closed_bos_doner(self):
        """Durust erisim, az veride bolmeyi DEJENERE eder - ve etmelidir.

        700 barlik bir pencere 4H tokenleriyle egitilemez. Dogru cevap
        kucuk bir pencereye SIGDIRMAK degil, "yetersiz" demektir.
        """
        b = m.kronolojik_bol(list(range(0, 700, 7)), ufuk=16, embargo=4,
                             giris_erisimi=m.girdi_erisimi(4, h4_var=True))
        self.assertEqual(b["train"], [])
        self.assertIn("yetersiz", b["not"])

    def test_dejenere_kapisi_ornek_biriminde_olculur(self):
        """Kapi bar-boslugunu ornek sayisiyla kiyaslarsa alt-orneklemde yanilir.

        Bosluk BAR cinsindendir; ornekler alt-orneklenmis olabilir. 30000
        barda 500 ornek (adim 60) icin 1046 barlik bosluk ~17 ornege mal
        olur, 1046'ya DEGIL.
        """
        b = m.kronolojik_bol(list(range(0, 30000, 60)), ufuk=16, embargo=4,
                             giris_erisimi=m.girdi_erisimi(4, True))
        self.assertEqual(b["not"], "")


class BaslikTesti(unittest.TestCase):
    def _ogrenilebilir(self, n=200):
        rng = m.tohumlu_rng("baslik-test")
        ornekler = []
        for _ in range(n):
            x = [rng.uniform(-1, 1) for _ in range(16)]
            ornekler.append({"x": x, "y": 1 if sum(x[:4]) > 0 else 0})
        return ornekler

    def test_egitim_kaybi_duser(self):
        ornekler = self._ogrenilebilir()
        b = m.Baslik(boyut=16, tohum=7)
        once = b.kayip(ornekler)
        b.egit(ornekler, devir=60, ogrenme_hizi=0.15)
        self.assertLess(b.kayip(ornekler), once, "egitim kaybi dusmeli")

    def test_logit_iki_sinif(self):
        self.assertEqual(len(m.Baslik(boyut=16, tohum=7).logit([0.0] * 16)), 2)

    def test_egitilmemis_baslik_neredeyse_esit_olasilik(self):
        p = m.kararli_softmax(m.Baslik(boyut=16, tohum=7).logit([0.0] * 16))
        self.assertAlmostEqual(p[0], 0.5, places=1)


# ---------------------------------------------------------------- Task 12

class KalibrasyonFitTesti(unittest.TestCase):
    def _basliklar_ve_ornekler(self):
        rng = m.tohumlu_rng("kal-fit")
        basliklar = [m.Baslik(boyut=8, tohum=100 + k) for k in range(3)]
        ornekler = []
        for _ in range(300):
            x = [rng.uniform(-1, 1) for _ in range(8)]
            ornekler.append({"x": x, "y": 1 if sum(x[:3]) > 0 else 0})
        for b in basliklar:
            b.egit(ornekler[:200], devir=40, ogrenme_hizi=0.2)
        return basliklar, ornekler[200:]

    def test_sicaklik_fit_dagitilan_dagilimda_yapilir(self):
        """63-bulgu #28'in panzehiri: T, DAGITILAN dagilimda fit edilmeli."""
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.sicaklik_fit(kal, basliklar)

        def nll(T):
            toplam = 0.0
            for o in kal:
                p = m.topluluk_olasilik(o["x"], basliklar, T)["p"]
                toplam += -math.log(max(1e-12, p[o["y"]]))
            return toplam / len(kal)

        self.assertLessEqual(r["nll"], nll(1.0) + 1e-9)
        self.assertLessEqual(r["nll"], nll(5.0) + 1e-9)
        self.assertAlmostEqual(r["nll"], nll(r["T"]), places=9)

    def test_sicaklik_sinirda_bayragi(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.sicaklik_fit(kal, basliklar)
        self.assertIn("sinirda", r)
        self.assertIsInstance(r["sinirda"], bool)

    def test_topluluk_uzlasi_ve_dagilim(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.topluluk_olasilik(kal[0]["x"], basliklar, 1.0)
        self.assertAlmostEqual(sum(r["p"]), 1.0, places=9)
        self.assertGreaterEqual(r["uzlasi"], 1.0 / 3.0)
        self.assertLessEqual(r["uzlasi"], 1.0)
        self.assertGreaterEqual(r["dagilim"], 0.0)

    def test_izotonik_monoton(self):
        ciftler = [(0.1, 0), (0.2, 0), (0.3, 1), (0.4, 0), (0.5, 1),
                   (0.6, 1), (0.7, 1), (0.8, 1), (0.9, 1)]
        fn = m.izotonik_fit(ciftler)
        degerler = [fn(x / 10.0) for x in range(1, 10)]
        for i in range(1, len(degerler)):
            self.assertGreaterEqual(degerler[i] + 1e-9, degerler[i - 1])

    def test_kalibrasyon_sec_nll_dusuk_olani_secer(self):
        basliklar, kal = self._basliklar_ve_ornekler()
        r = m.kalibrasyon_sec(kal, basliklar)
        self.assertIn(r["yontem"], ("sicaklik", "izotonik"))
        self.assertTrue(math.isfinite(r["nll"]))

    # -- yarisma adaleti: ayni kumede fit + puanlama izotoniki KAYIRIR --

    def _sinyalsiz(self, tohum, n=120, boyut=4):
        """Etiketi x'ten BAGIMSIZ kume: hicbir yontem gercek kenar bulamaz."""
        rng = m.tohumlu_rng(tohum)
        basliklar = [m.Baslik(boyut=boyut, tohum=100 + k) for k in range(3)]
        ornekler = [{"x": [rng.uniform(-1, 1) for _ in range(boyut)],
                     "y": 1 if rng.random() < 0.5 else 0} for _ in range(n)]
        return basliklar, ornekler

    @staticmethod
    def _nll(ciftler):
        toplam = 0.0
        for p, y in ciftler:
            p = min(1.0 - 1e-9, max(1e-9, p))
            toplam += -math.log(p if y == 1 else 1.0 - p)
        return toplam / len(ciftler)

    def _ham(self, ornekler, basliklar, T=1.0):
        return [(m.long_olasiligi(m.topluluk_olasilik(o["x"], basliklar, T)["p"]),
                 o["y"]) for o in ornekler]

    def test_ezberleyen_izotonik_secilmez(self):
        """Ic-orneklemde izotonik KAZANIR, dis-orneklemde KAYBEDER.

        Izotonik n serbestlik derecesine kadar cikar; sicaklik tek
        parametredir. Ayni kumede fit edilip ayni kumede puanlanan bir
        yarisma bu yuzden yapisal olarak izotoniki secer - kenar degil
        EZBER olculur. Adil yarisma sicakligi secmeli.
        """
        basliklar, ornekler = self._sinyalsiz("kal-b")
        kal, dis = ornekler[:60], ornekler[60:]
        izo = m.izotonik_fit(self._ham(kal, basliklar))
        sic = m.sicaklik_fit(kal, basliklar)

        ic_izo = self._nll([(izo(p), y) for p, y in self._ham(kal, basliklar)])
        ic_sic = self._nll(self._ham(kal, basliklar, sic["T"]))
        dis_izo = self._nll([(izo(p), y) for p, y in self._ham(dis, basliklar)])
        dis_sic = self._nll(self._ham(dis, basliklar, sic["T"]))
        # Kurulumun gecerliligi: tuzak GERCEKTEN kurulu olmali.
        self.assertLess(ic_izo, ic_sic, "kurulum bozuk: izotonik ic-orneklemde kaybediyor")
        self.assertGreater(dis_izo, dis_sic, "kurulum bozuk: izotonik dis-orneklemde kazaniyor")

        self.assertEqual(m.kalibrasyon_sec(kal, basliklar)["yontem"], "sicaklik")

    def test_yarisma_ic_holdoutta_yapilir_ve_beyan_edilir(self):
        basliklar, ornekler = self._sinyalsiz("kal-a")
        r = m.kalibrasyon_sec(ornekler[:60], basliklar)
        self.assertEqual(r["yarisma"], "ic-holdout")

    def test_yetersiz_ornekte_yarisma_yapilmaz_fail_closed(self):
        """Bolunemeyecek kadar az ornekte ezber riski en dusuk yontem secilir."""
        basliklar, ornekler = self._sinyalsiz("kal-c")
        r = m.kalibrasyon_sec(ornekler[:2 * m.ASGARI_OLCUM - 1], basliklar)
        self.assertEqual(r["yontem"], "sicaklik")
        self.assertIn("yetersiz", r["yarisma"])

    def test_kazanan_tum_kalibrasyon_kumesinde_yeniden_fit_edilir(self):
        """Yarisma ayirmak icindir; kazanan veriyi ISRAF etmemeli."""
        basliklar, ornekler = self._sinyalsiz("kal-d", n=200)
        kal = ornekler[:120]
        r = m.kalibrasyon_sec(kal, basliklar)
        if r["yontem"] == "sicaklik":
            self.assertAlmostEqual(r["T"], m.sicaklik_fit(kal, basliklar)["T"],
                                   places=9)
        else:
            tam = m.izotonik_fit(self._ham(kal, basliklar))
            for p in (0.1, 0.3, 0.5, 0.7, 0.9):
                self.assertAlmostEqual(r["fn"](p), tam(p), places=9)

    def test_karisim_softmaxinda_sicaklik_karari_cevirebilir(self):
        """63-bulgu #24: olasilik-havuzunda T argmax'i DEGISTIREBILIR.

        Bu bir hata degil, olgudur; sistem bunu BILMELI ve raporlamali.
        """
        self.assertTrue(m.sicaklik_karari_cevirir_mi([[10.0, 0.0], [0.0, 1.0],
                                                      [0.0, 1.0]]))
        self.assertFalse(m.sicaklik_karari_cevirir_mi([[3.0, 0.0], [2.0, 0.0],
                                                       [1.0, 0.0]]))


# ---------------------------------------------------------------- Task 13

class DecodingTesti(unittest.TestCase):
    def test_daima_yon_uretir(self):
        for p in (0.0, 0.4999, 0.5, 0.5001, 1.0):
            self.assertIn(m.decode(p), m.YON_SOZLUGU)

    def test_beraberlikte_long(self):
        self.assertEqual(m.decode(0.5), "LONG")

    def test_hold_asla_donmez(self):
        """Belgenin Gerekce 1-2: decoding secimsiz adim uretemez."""
        rng = m.tohumlu_rng("decode-fuzz")
        for _ in range(500):
            self.assertIn(m.decode(rng.random()), ("LONG", "SHORT"))

    def test_seviyeler_long_yonlu(self):
        s = m.seviyeler(giris=100.0, atr_deger=2.0, yon="LONG", stop_k=1.5, hedef_k=3.0)
        self.assertAlmostEqual(s["stop"], 97.0, places=9)
        self.assertAlmostEqual(s["hedef"], 106.0, places=9)
        self.assertAlmostEqual(s["R"], 2.0, places=9)

    def test_seviyeler_short_simetrik(self):
        s = m.seviyeler(100.0, 2.0, "SHORT", 1.5, 3.0)
        self.assertAlmostEqual(s["stop"], 103.0, places=9)
        self.assertAlmostEqual(s["hedef"], 94.0, places=9)


class SinifEkseniTesti(unittest.TestCase):
    """etiket_uret'in y'si ile decode'un okudugu olasilik AYNI ekseni gostermeli.

    Bu sinif bir SEMANTIK bagi sinar: modul ici tutarlilik testleri (softmax
    toplami 1, decode daima yon uretir) eksen ters olsa bile GECER. Bag ancak
    ogrenilebilir bir sinyalle olculur: etiket kuralini bilen bir baslik
    egitilir, sonra decode'un ayni yonu soyleyip soylemedigine BAKILIR.
    """

    def _ogrenilebilir(self, n=400, boyut=4, tohum="eksen-test"):
        rng = m.tohumlu_rng(tohum)
        kume = []
        for _ in range(n):
            x = [rng.uniform(-1, 1) for _ in range(boyut)]
            # etiket_uret sozlesmesi: 1 = "LONG hedefi once vuruldu" = LONG DOGRU
            kume.append({"x": x, "y": 1 if x[0] > 0 else 0})
        return kume

    def setUp(self):
        self.kume = self._ogrenilebilir()
        self.b = m.Baslik(boyut=4, tohum=42)
        self.b.egit(self.kume, devir=120, ogrenme_hizi=0.20)

    def _p_long(self, x):
        return m.long_olasiligi(m.topluluk_olasilik(x, [self.b])["p"])

    def test_long_dogru_ornekte_decode_LONG_der(self):
        self.assertEqual(m.decode(self._p_long([0.9, 0.0, 0.0, 0.0])), "LONG")

    def test_long_yanlis_ornekte_decode_SHORT_der(self):
        self.assertEqual(m.decode(self._p_long([-0.9, 0.0, 0.0, 0.0])), "SHORT")

    def test_ogrenilebilir_sinyalde_dogruluk_sanstan_yuksek(self):
        """Eksen tersse bu deger 0.5'in COK ALTINA duser (1 - dogruluk)."""
        dogru = sum(1 for o in self.kume
                    if (1 if self._p_long(o["x"]) >= 0.5 else 0) == o["y"])
        self.assertGreater(dogru / len(self.kume), 0.9)

    def test_eksen_tek_yerde_beyan_edilir(self):
        """Ham indeks (p[0]/p[1]) ile yon okumak yasak: eksen kayabilir."""
        self.assertTrue(hasattr(m, "LONG_SINIFI"))
        self.assertEqual(m.long_olasiligi([0.3, 0.7]), [0.3, 0.7][m.LONG_SINIFI])

    def test_kaynakta_ham_indeksle_yon_okunmuyor(self):
        """Modulde `["p"][0]` kalmamali - eksen kacisi buradan sizar."""
        kaynak = pathlib.Path(m.__file__).read_text(encoding="utf-8")
        self.assertNotIn('["p"][0]', kaynak)
        self.assertNotIn('["p"][1]', kaynak)

    def test_sicaklik_karari_cevirir_mi_ayni_ekseni_kullanir(self):
        """T taramasi da LONG_SINIFI'ndan gecmeli; aksi halde iki eksen olur."""
        logitler = [[0.0, 3.0], [0.0, 3.0], [0.0, 3.0]]   # net LONG (sinif 1)
        for T in (0.2, 1.0, 5.0):
            gorusler = [m.kararli_softmax(z, T) for z in logitler]
            p_long = sum(m.long_olasiligi(g) for g in gorusler) / len(gorusler)
            self.assertEqual(m.decode(p_long), "LONG")
        self.assertFalse(m.sicaklik_karari_cevirir_mi(logitler))


class KararUretTesti(unittest.TestCase):
    def _baglam(self, kanit_yok=True):
        barlar = [{"o": 100 + i * 0.1, "h": 100 + i * 0.1 + 0.5,
                   "l": 100 + i * 0.1 - 0.5, "c": 100 + i * 0.1} for i in range(300)]
        return {
            "sembol": "BTCUSDT", "barlar": barlar, "atr_serisi": [1.0] * 300,
            "indeksler": list(range(0, 250, 5)),
            "p_ham": 0.95 if kanit_yok else 0.72,
            "dogru": 17 if kanit_yok else 700,
            "toplam": 48 if kanit_yok else 1000,
            "ece_enkotu": 0.02, "dolu_kanal": 6, "toplam_kanal": 6,
            "giris": 130.0, "atr": 1.0, "likidasyon": 100.0,
            "kaldirac_azami": 10.0, "komisyon": 0.0004, "kayma": 0.0005,
            "funding": 0.0, "lam": 1.0,
        }

    def test_stake_sifirken_bile_seviyeler_uretilir(self):
        """Belgenin Gerekce 5: seviyeler KOSULSUZ uretilir."""
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertIn(r["yon"], m.YON_SOZLUGU)
        self.assertIsNotNone(r["giris"])
        self.assertIsNotNone(r["stop"])
        self.assertIsNotNone(r["hedef"])
        self.assertEqual(r["stake"]["f"], 0.0)

    def test_kanit_yoksa_stake_sifir(self):
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertEqual(r["stake"]["f"], 0.0)
        self.assertEqual(r["shrinkage"]["s"], 0.0)

    def test_cikti_lambda_uclusu_icerir(self):
        r = m.karar_uret(self._baglam(kanit_yok=True))
        for lam in ("1.0", "0.5", "0.25"):
            self.assertIn(lam, r["stake"]["lambda_tablosu"])

    def test_basabas_p_daima_raporlanir(self):
        self.assertIn("basabas_p", m.karar_uret(self._baglam())["geometri"])

    def test_yon_daraltilmamis_olasiliktan_gelir(self):
        """Shrinkage stake'i sifirlar ama YON bilgisini yok etmez."""
        r = m.karar_uret(self._baglam(kanit_yok=True))
        self.assertEqual(r["yon"], "LONG")   # p_ham=0.95 -> LONG

    def test_likidasyon_okunamazsa_stake_sifir(self):
        b = self._baglam(kanit_yok=False)
        b["likidasyon"] = None
        r = m.karar_uret(b)
        self.assertEqual(r["stake"]["f"], 0.0)
        self.assertEqual(r["stake"]["f_max"], 0.0)


# ---------------------------------------------------------------- Task 14

class GostergeTesti(unittest.TestCase):
    def test_ema_ilk_deger_girdiye_esit(self):
        self.assertAlmostEqual(m.ema([5.0, 6.0, 7.0], 3)[0], 5.0, places=9)

    def test_ema_uzunluk_korunur(self):
        self.assertEqual(len(m.ema([1.0] * 10, 3)), 10)

    def test_atr_pozitif(self):
        barlar = [{"o": 100, "h": 101, "l": 99, "c": 100} for _ in range(20)]
        self.assertTrue(all(x >= 0 for x in m.atr(barlar, 14)))

    def test_rsi_araligi(self):
        rng = m.tohumlu_rng("rsi")
        for x in m.rsi([100 + rng.uniform(-1, 1) for _ in range(60)], 14):
            self.assertGreaterEqual(x, 0.0)
            self.assertLessEqual(x, 100.0)


FIKSTUR_BARI = 6000   # 62.5 gun 15M; durust purge boslugu (1046) altinda
                      # bolmenin dejenere OLMAMASI icin gereken mertebe


def _agrega4h(barlar15):
    """16 adet 15M barini GERCEK bir 4H barina toplar (ornekleme DEGIL).

    Ornekleme (barlar15[::16]) hizalama semantigini sinayamaz cunku 4H
    barinin kapanisi 15M barininkiyle ayni olur. Agregasyon ise 4H barinin
    ANCAK 16. barda kapandigini gorunur kilar.
    """
    cikti = []
    for k in range(0, len(barlar15) - 15, 16):
        dilim = barlar15[k:k + 16]
        cikti.append({"o": dilim[0]["o"],
                      "h": max(b["h"] for b in dilim),
                      "l": min(b["l"] for b in dilim),
                      "c": dilim[-1]["c"],
                      "v": sum(b["v"] for b in dilim)})
    return cikti


class SonluErisimTesti(unittest.TestCase):
    """Gostergelerin geriye erisimi KANITLANABILIR bicimde SONLU olmali.

    Ozyinelemeli (IIR) EMA'nin erisimi SONLU DEGILDIR: cikti[i] cikti[i-1]'e,
    o da cikti[i-2]'ye bagli - zincir serinin BASINA kadar gider ve pratikte
    yalniz float64 alt-tasmasiyla kesilir. Bu, erisimin VERIYE ve TOLERANSA
    bagli olmasi demektir; olcum bunu dogruladi (ayni bar, tol 1e-15 -> 313
    bar, tol 1e-9 -> 168 bar). Toleransa bagli bir sayi purge korkulugu
    OLAMAZ: sizinti penceresi kanitlanabilir bir ust sinir ister.

    Cozum ustel agirligi TERK ETMEK degil, onu SONLU pencereye KESMEKTIR:
    ayni agirlik profili, kanitlanabilir sinir.
    """

    def _seri(self, n=400):
        rng = m.tohumlu_rng("sonlu-erisim")
        return [100.0 + rng.uniform(-1.0, 1.0) for _ in range(n)]

    def _erisim(self, fn, seri, i, tolerans):
        """i'inci ciktiyi degistiren EN UZAK gecmis barin mesafesi."""
        taban = fn(seri)[i]
        en_uzak = 0
        for d in range(1, i + 1):
            bozuk = list(seri)
            bozuk[i - d] *= 1.001
            if abs(fn(bozuk)[i] - taban) > tolerans:
                en_uzak = d
        return en_uzak

    def test_ema_erisimi_toleranstan_bagimsiz(self):
        """IIR'de bu test DUSER: erisim toleransla degisir."""
        seri = self._seri()
        i = 350
        kati = self._erisim(lambda s: m.ema(s, 21), seri, i, 1e-15)
        maddi = self._erisim(lambda s: m.ema(s, 21), seri, i, 1e-9)
        self.assertEqual(kati, maddi,
                         "erisim toleransa bagliysa ust sinir kanitlanamaz")

    def test_ema_erisimi_beyan_edilen_pencereyi_asmaz(self):
        seri = self._seri()
        i = 350
        for periyot in (8, 21):
            erisim = self._erisim(lambda s: m.ema(s, periyot), seri, i, 1e-15)
            self.assertLessEqual(erisim, m.gosterge_penceresi("ema", periyot),
                                 f"ema({periyot}) beyan edilen pencereyi asti")

    def test_ema_hala_ustel_agirlikli(self):
        """Kesme, ustel agirligi TERK ETMEK degildir: son bar en agir olmali."""
        n = 200
        for periyot in (8, 21):
            # Tek bir bara birim darbe: agirlik profili dogrudan okunur.
            agirliklar = []
            for d in range(0, 6):
                seri = [0.0] * n
                seri[n - 1 - d] = 1.0
                agirliklar.append(m.ema(seri, periyot)[n - 1])
            for k in range(1, len(agirliklar)):
                self.assertLess(agirliklar[k], agirliklar[k - 1],
                                "agirlik gecmise dogru AZALMALI (ustel profil)")

    def test_gosterge_penceresi_beyan_edilmis(self):
        """Kesme uzunlugu etiketsiz gizli esik OLAMAZ."""
        self.assertIn("EMA_KESME_KATI", m.ESIK_KAYNAGI)
        self.assertEqual(m.ESIK_KAYNAGI["EMA_KESME_KATI"]["kaynak"], "YAPISAL")


class HesapKarmasikligiTesti(unittest.TestCase):
    """satir_uret bar BASINA tum seriyi yeniden kurmamali (gercek O(N^2)).

    Olculdu (cProfile, 20000 bar): `_z([h*k for h,k in zip(...)], i)` listcomp'u
    toplam surenin %71.3'unu yiyordu. Bu bir hiz suslemesi degil: hedef ortam
    Pydroid 3 (telefon) ve durust purge daha buyuk fikstur GEREKTIRIYOR -
    kosmayan sistem dogru sonuc vermez.
    """

    def _barlar(self, n):
        rng = m.tohumlu_rng("karmasiklik")
        barlar, fiyat = [], 100.0
        for _ in range(n):
            fiyat *= 1.0 + rng.uniform(-0.004, 0.004)
            barlar.append({"o": fiyat, "h": fiyat * 1.002, "l": fiyat * 0.998,
                           "c": fiyat, "v": rng.uniform(80.0, 120.0)})
        return barlar

    def test_gostergeler_hacim_degerini_onceden_hesaplar(self):
        gost = m._gostergeler(self._barlar(60))
        self.assertIn("hacim_deger", gost)
        self.assertEqual(len(gost["hacim_deger"]), 60)

    def test_hacim_deger_serisi_eski_ic_formulle_ayni(self):
        """Hoist DAVRANIS DEGISTIRMEMELI: seri birebir ayni olmali."""
        barlar = self._barlar(80)
        gost = m._gostergeler(barlar)
        beklenen = [h * k for h, k in zip(gost["hacimler"], gost["kapanislar"])]
        self.assertEqual(gost["hacim_deger"], beklenen)

    def test_satir_uret_kaynakta_seri_boyu_listcomp_kurmuyor(self):
        """Yapisal kilit: fonksiyon govdesinde tum seri uzerinde zip/listcomp yok."""
        kaynak = inspect.getsource(m.satir_uret)
        self.assertNotIn("zip(hacimler", kaynak)
        self.assertNotIn("for h, k in zip", kaynak)

    def test_satir_uret_maliyeti_seri_boyuyla_buyumuyor(self):
        """Bar basina maliyet N'den BAGIMSIZ olmali (yapisal, zamanlama degil).

        Ayni bar indeksinde uretilen satir, serinin GERISINE eklenen barlardan
        etkilenmemeli; etkileniyorsa fonksiyon tum seriyi geziyor demektir.
        """
        kisa = self._barlar(200)
        uzun = kisa + self._barlar(2000)
        i = 150
        s1 = m.satir_uret(kisa, m._gostergeler(kisa), None, i)
        s2 = m.satir_uret(uzun, m._gostergeler(uzun), None, i)
        self.assertEqual(s1, s2, "gelecek barlar gecmis satiri degistiremez")


class BoruHattiTesti(unittest.TestCase):
    def _paket(self, turev_var=True, tohum="boru"):
        """Fikstur, boru hattinin GERCEKTEN egitebilecegi kadar veri icermeli.

        FIKSTUR_BARI 700 idi. Erisim durustce gosterge pencerelerinden
        turetilince (15M 65, 4H 1026 bar) 700 barlik pencerede purge
        boslugu 1046'ya cikiyor ve bolme TAMAMEN dejenere oluyor - egitim
        de kalibrasyon da degerlendirme de hic kosmuyor. O halde 700 barlik
        fikstur uzerinde "boru hatti gecti" demek TIYATRODUR: testler
        bosluga karsi gecer.

        Cozum esigi gevsetmek DEGIL, fiksturu gercekci kilmaktir: 6000 bar
        = 62.5 gun 15M verisi, gercek sistemin de bekledigi mertebe.
        Uretim maliyeti onbellege alinir; aksi halde her cagride yeniden
        kurulur (suite ~20 kez cagiriyor).
        """
        anahtar = (turev_var, tohum)
        onbellek = getattr(BoruHattiTesti, "_ONBELLEK", None)
        if onbellek is None:
            onbellek = BoruHattiTesti._ONBELLEK = {}
        if anahtar in onbellek:
            return dict(onbellek[anahtar])

        rng = m.tohumlu_rng(tohum)
        barlar15, fiyat = [], 100.0
        for _ in range(FIKSTUR_BARI):
            fiyat *= (1.0 + rng.uniform(-0.003, 0.0032))
            barlar15.append({"o": fiyat, "h": fiyat * 1.002, "l": fiyat * 0.998,
                             "c": fiyat, "v": 1000 + rng.uniform(0, 100)})
        # Turev SERI olmalidir: tek anlik deger tum barlara yazilirsa std=0
        # olur ve Olcekleyici onu dogru bicimde sifirlar (bilgi kaybolur).
        turev_serisi = None
        if turev_var:
            turev_serisi = []
            for i in range(len(barlar15)):
                turev_serisi.append({
                    "oi_degisim": 0.01 + 0.02 * math.sin(i / 7.0),
                    "funding_z": 0.2 + 0.5 * math.sin(i / 11.0),
                    "taker_dengesi": 0.1 + 0.3 * math.cos(i / 5.0),
                    "derinlik_dengesi": -0.05 + 0.2 * math.sin(i / 13.0)})
        paket = {"sembol": "BTCUSDT", "barlar15": barlar15,
                 "barlar4h": _agrega4h(barlar15), "turev_serisi": turev_serisi,
                 "dolu_kanal": 6 if turev_var else 3, "toplam_kanal": 6,
                 "likidasyon": barlar15[-1]["c"] * 0.8, "kaldirac_azami": 10.0,
                 "azami_ornek": m.AZAMI_ORNEK}
        onbellek[anahtar] = paket
        return dict(paket)

    def test_uctan_uca_karar_uretir(self):
        r = m.BoruHatti(tohum=2026).calistir(self._paket())
        self.assertIn(r["yon"], m.YON_SOZLUGU)
        self.assertIsNotNone(r["giris"])
        self.assertIn("iz", r)

    def test_iz_on_uc_halka_icerir(self):
        r = m.BoruHatti(tohum=2026).calistir(self._paket())
        for halka in range(13):
            self.assertIn(f"halka_{halka}", r["iz"], f"halka_{halka} izde yok")

    def test_boru_hatti_gercekten_kosuyor(self):
        """Denetci bulgusu TIYATRO: bolme bos kalinca egitim/kalibrasyon/
        degerlendirme HIC calismiyordu ama testler bos gecip PASS veriyordu."""
        iz = m.BoruHatti(tohum=2026).calistir(self._paket())["iz"]
        self.assertGreater(iz["halka_11"]["train"], 0, "bolme dejenere")
        self.assertGreater(iz["halka_6"]["train_ornek"], 0, "baslik egitilmedi")
        self.assertGreater(iz["halka_8"]["test_ornek"], 0, "degerlendirme yok")
        self.assertNotEqual(iz["halka_7"]["yontem"], "YOK", "kalibrasyon secilmedi")

    def test_bos_bolmede_sizinti_fail_closed(self):
        """Bos bolmede 'sizinti: False' demek fail-OPEN rapordur."""
        kucuk = self._paket()
        kucuk["azami_ornek"] = 20          # bilerek dejenere
        iz = m.BoruHatti(tohum=2026).calistir(kucuk)["iz"]
        self.assertIsNone(iz["halka_11"]["sizinti"])
        self.assertIn("yetersiz", iz["halka_11"]["not"])

    def test_4h_ailesi_temsili_degistirir(self):
        """Denetci bulgusu ATLAMA: 4H boru hattina HIC girmiyordu."""
        p1 = self._paket()
        p2 = self._paket()
        p2["barlar4h"] = [{"o": b["o"] * 1.5, "h": b["h"] * 1.6,
                           "l": b["l"] * 1.4, "c": b["c"] * 1.5, "v": b["v"]}
                          for b in p2["barlar4h"]]
        r1 = m.BoruHatti(tohum=2026).calistir(p1)
        r2 = m.BoruHatti(tohum=2026).calistir(p2)
        self.assertNotAlmostEqual(r1["p_ham"], r2["p_ham"], places=6)

    def test_iz_iki_zaman_dilimi_raporlar(self):
        iz = m.BoruHatti(tohum=2026).calistir(self._paket())["iz"]
        self.assertEqual(iz["halka_1"]["zaman_dilimi_sayisi"],
                         len(m.ZAMAN_DILIMLERI))
        self.assertEqual(iz["halka_1"]["token_sayisi"],
                         m.GECIKME_SAYISI * len(m.AILELER) * len(m.ZAMAN_DILIMLERI))

    def test_4h_kanali_dusunce_kapsam_duser(self):
        """Modele ulasmayan veri s_kapsam'i BUYUTMEMELI (fail-closed).

        Denetci bulgusu TIYATRO: bu testin ilk hali dolu_kanal'i ELLE
        dusuruyordu, yani kendi kurdugu seyi olcuyordu ve 4H VARKEN de
        geciyordu. Artik dolu_kanal'a DOKUNULMUYOR - kapsam dususu
        boru hattinin KENDISINDEN gelmeli.
        """
        tam = m.BoruHatti(tohum=2026).calistir(self._paket())
        eksik_p = self._paket()
        eksik_p["barlar4h"] = None          # dolu_kanal DEGISMIYOR
        eksik = m.BoruHatti(tohum=2026).calistir(eksik_p)
        self.assertLess(eksik["shrinkage"]["s_kapsam"],
                        tam["shrinkage"]["s_kapsam"],
                        "4H yokken kapsam DUSMELI - yoksa kapsam yalan soyler")

    def test_4h_hizalama_look_ahead_icermez(self):
        """Denetci bulgusu (olumcul): i//16 HENUZ KAPANMAMIS 4H barini veriyordu.

        4H bar k, 15M barlarini [16k, 16k+15] araliginda kapsar ve ancak
        16k+15'te KAPANIR. 15M bar i, en fazla i'den ONCE kapanmis bir 4H
        barini gorebilir.
        """
        p1 = self._paket()
        i = 320
        p2 = self._paket()
        b4 = [dict(b) for b in p2["barlar4h"]]
        hedef = i // 16
        b4[hedef] = {"o": b4[hedef]["o"] * 3, "h": b4[hedef]["h"] * 3,
                     "l": b4[hedef]["l"] * 3, "c": b4[hedef]["c"] * 3,
                     "v": b4[hedef]["v"]}
        p2["barlar4h"] = b4

        g41 = m._gostergeler(p1["barlar4h"])
        g42 = m._gostergeler(p2["barlar4h"])
        e1 = m._h4_hizala(len(p1["barlar15"]), len(p1["barlar4h"]))
        e2 = m._h4_hizala(len(p2["barlar15"]), len(p2["barlar4h"]))
        satir1 = m.satir_uret(p1["barlar4h"], g41, None, e1[i])
        satir2 = m.satir_uret(p2["barlar4h"], g42, None, e2[i])
        self.assertEqual(satir1["fiyat"], satir2["fiyat"],
                         "15M bar %d, HENUZ KAPANMAMIS 4H barini goruyor "
                         "= look-ahead sizintisi" % i)

    def test_4h_hizalama_son_kapanan_bari_verir(self):
        """Esleme kurali: 15M bar i -> 4H bar (i+1)//16 - 1 (0'a kirpilmis)."""
        eslesme = m._h4_hizala(700, 43)
        # 4H bar k, 15M [16k, 16k+15] araligini kapsar, 16k+15'te KAPANIR.
        self.assertEqual(eslesme[0], 0)    # isinma: henuz kapanmis bar yok, kirpilir
        self.assertEqual(eslesme[14], 0)   # isinma
        self.assertEqual(eslesme[15], 0)   # bar 0 TAM burada kapanir -> gorulebilir
        self.assertEqual(eslesme[16], 0)   # bar 1 basladi ama kapanmadi
        self.assertEqual(eslesme[30], 0)   # bar 1 hala olusuyor
        self.assertEqual(eslesme[31], 1)   # bar 1 TAM burada kapandi
        self.assertEqual(eslesme[32], 1)   # bar 2 olusuyor
        self.assertEqual(eslesme[320], 19)  # bar 20 HENUZ kapanmadi (335'te kapanir)

    def test_4h_yokken_token_uretilmez(self):
        """Notr 0.0 enjeksiyonu YASAK: 4H yoksa token HIC uretilmemeli."""
        eksik_p = self._paket()
        eksik_p["barlar4h"] = None
        iz = m.BoruHatti(tohum=2026).calistir(eksik_p)["iz"]
        self.assertFalse(iz["halka_1"]["h4_var"])
        self.assertEqual(iz["halka_1"]["token_sayisi"],
                         m.GECIKME_SAYISI * len(m.AILELER))

    def test_determinizm(self):
        p = self._paket()
        a = m.BoruHatti(tohum=2026).calistir(p)
        b = m.BoruHatti(tohum=2026).calistir(p)
        self.assertEqual(a["yon"], b["yon"])
        self.assertAlmostEqual(a["stake"]["f"], b["stake"]["f"], places=12)

    def test_kanal_dususu_stake_dusurur(self):
        tam = m.BoruHatti(tohum=2026).calistir(self._paket(turev_var=True))
        eksik = m.BoruHatti(tohum=2026).calistir(self._paket(turev_var=False))
        self.assertLessEqual(eksik["stake"]["f"], tam["stake"]["f"])
        self.assertLess(eksik["shrinkage"]["s_kapsam"], tam["shrinkage"]["s_kapsam"])

    def test_turev_ailesi_temsili_degistirir(self):
        """63-bulgu #1'in panzehiri: turev GERCEKTEN modele giriyor mu."""
        p1 = self._paket(turev_var=True)
        p2 = self._paket(turev_var=True)
        p2["turev_serisi"] = [
            {"oi_degisim": -0.9 + 0.05 * math.cos(i / 3.0),
             "funding_z": -2.0 + 0.4 * math.sin(i / 9.0),
             "taker_dengesi": -0.8 + 0.3 * math.sin(i / 4.0),
             "derinlik_dengesi": 0.7 + 0.2 * math.cos(i / 6.0)}
            for i in range(len(p2["barlar15"]))]
        r1 = m.BoruHatti(tohum=2026).calistir(p1)
        r2 = m.BoruHatti(tohum=2026).calistir(p2)
        self.assertNotAlmostEqual(r1["p_ham"], r2["p_ham"], places=6)


# ---------------------------------------------------------------- Task 15

class CiktiTesti(unittest.TestCase):
    def _karar(self):
        return {
            "sembol": "BTCUSDT", "yon": "LONG", "p_ham": 0.55,
            "p_kullanilan": 0.5,
            "shrinkage": {"s": 0.0, "s_kanit": 0.0, "s_kalibrasyon": 1.0,
                          "s_kapsam": 1.0},
            "geometri": {"stop_k": 1.5, "hedef_k": 3.0, "R": 2.0, "p_hedef": 0.4,
                         "n": 40, "basabas_p": 0.68, "elog": -0.01, "not": ""},
            "giris": 100.0, "stop": 98.5, "hedef": 103.0, "R": 2.0,
            "stake": {"f": 0.0, "kirpildi": False, "f_max": 0.1,
                      "lambda_tablosu": {"1.0": {"f": 0.0}, "0.5": {"f": 0.0},
                                         "0.25": {"f": 0.0}}},
        }

    def test_metin_rapor_yon_icerir(self):
        self.assertIn("LONG", m.metin_rapor(self._karar()))

    def test_metin_rapor_stake_sifiri_gizlemez(self):
        metin = m.metin_rapor(self._karar())
        self.assertIn("f*", metin)

    def test_metin_rapor_basabas_gosterir(self):
        self.assertIn("basabas", m.metin_rapor(self._karar()).lower())

    def test_defter_stake_sifirda_pozisyon_acmaz(self):
        yeni = m.defter_guncelle({"sermaye": 1000.0, "pozisyonlar": {}},
                                 self._karar(),
                                 {"o": 100, "h": 101, "l": 99, "c": 100})
        self.assertNotIn("BTCUSDT", yeni["pozisyonlar"])

    def test_defter_stake_pozitifken_pozisyon_acar(self):
        karar = self._karar()
        karar["stake"]["f"] = 0.02
        yeni = m.defter_guncelle({"sermaye": 1000.0, "pozisyonlar": {}}, karar,
                                 {"o": 100, "h": 101, "l": 99, "c": 100})
        self.assertIn("BTCUSDT", yeni["pozisyonlar"])

    def test_defter_stopta_kapatir(self):
        durum = {"sermaye": 1000.0, "pozisyonlar": {
            "BTCUSDT": {"yon": "LONG", "giris": 100.0, "stop": 98.5,
                        "hedef": 103.0, "miktar": 10.0}}}
        yeni = m.defter_guncelle(durum, self._karar(),
                                 {"o": 100, "h": 100, "l": 98.0, "c": 99})
        self.assertNotIn("BTCUSDT", yeni["pozisyonlar"])
        self.assertLess(yeni["sermaye"], 1000.0)

    def test_main_esikler_sifir_doner(self):
        """--esikler yan etkisiz; --self-test ozyineleme yaratir, orada sinanmaz."""
        self.assertEqual(m.main(["--esikler"]), 0)

    def test_oz_test_ozyineleme_korumasi(self):
        """Oz-test icinden tekrar cagrilirsa ic ice kosu YAPILMAZ."""
        self.assertFalse(m.oz_test_kosuyor())


if __name__ == "__main__":
    unittest.main()
