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


if __name__ == "__main__":
    unittest.main()
