#!/usr/bin/env python3
"""grafik-cizim öz-testi — motor gerçekten çiziyor mu, sayı uyduruyor mu?

Koşum:  python3 self_test.py     (çıkış kodu 0 = tüm testler geçti)

Testler yalnız "hata vermedi" demez; ÖLÇER:
  · ölçek doğruluğu (doğrusal + logaritmik, ters dönüşüm)
  · rezervasyon: grafik dışı hedef fiyat ölçeğe katılıyor mu (kırpma yok)
  · Fibonacci aritmetiği (0.618 seviyesi elle hesapla birebir aynı mı)
  · pozisyon aracının R:R'ı (şişirme yok — risk/ödül ham mesafeden)
  · TÜM araçlar tek tek çiziliyor mu (kayıt defteri ↔ gerçek fonksiyon)
  · GROUNDING: otomatik katmanın ürettiği her fiyat ÖLÇÜLEN kümede mi
    (smc_tespit çıktısı ∪ ham OHLC) — uydurma seviye testi
  · SVG iyi biçimli mi (XML ayrıştırılıyor mu)
"""
from __future__ import annotations

import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BURASI = Path(__file__).resolve().parent
if str(BURASI) not in sys.path:
    sys.path.insert(0, str(BURASI))

import araclar as A  # noqa: E402
import cizim as C  # noqa: E402
import otomatik_cizim as OC  # noqa: E402
from tuval import Tuval  # noqa: E402

GECTI, KALDI = [], []


def onay(ad: str, kosul: bool, detay: str = "") -> None:
    (GECTI if kosul else KALDI).append(f"{ad}{(' — ' + detay) if detay else ''}")


def sahte_mumlar(n: int = 140) -> list:
    """Determinist sentetik seri (rastgelelik yok — test tekrarlanabilir)."""
    m, fiyat, t0 = [], 100.0, 1_700_000_000_000
    for i in range(n):
        dalga = math.sin(i / 7.0) * 3.0 + math.sin(i / 23.0) * 8.0
        acilis = fiyat
        kapanis = 100.0 + dalga + i * 0.09
        yuksek = max(acilis, kapanis) + 0.8 + abs(math.cos(i / 5.0))
        alcak = min(acilis, kapanis) - 0.8 - abs(math.sin(i / 4.0))
        m.append({"open": acilis, "high": yuksek, "low": alcak, "close": kapanis,
                  "volume": 1000 + (i % 17) * 37.0, "time": t0 + i * 14_400_000})
        fiyat = kapanis
    return m


def test_olcek(m):
    t = Tuval(m, genislik=800, yukseklik=500)
    t.hazirla()
    onay("ölçek: üst fiyat üstte", t.y(t.hi) < t.y(t.lo))
    orta = (t.hi + t.lo) / 2
    onay("ölçek: ters dönüşüm", abs(t.fiyat_y(t.y(orta)) - orta) < 1e-6,
         f"{t.fiyat_y(t.y(orta)):.6f} vs {orta:.6f}")
    tl = Tuval(m, log_olcek=True)
    tl.hazirla()
    onay("log ölçek: monoton", tl.y(tl.lo * 1.1) < tl.y(tl.lo))
    onay("bar indeksi: negatif = sondan", abs(t.bar_indeks(-1) - (len(m) - 1)) < 1e-9)
    onay("bar indeksi: gelecek projeksiyonu", t.x(len(m) + 10) > t.x(len(m) - 1))


def test_rezervasyon(m):
    hedef = max(c["high"] for c in m) * 1.6
    t = Tuval(m)
    t.rezerve([hedef])
    t.hazirla()
    onay("rezervasyon: grafik dışı hedef ölçeğe katıldı", t.hi >= hedef,
         f"hi={t.hi:.2f} hedef={hedef:.2f}")
    onay("rezervasyon: hedef tuvalin içinde", t.ana_ust <= t.y(hedef) <= t.ana_alt)


def test_fib(m):
    t = Tuval(m)
    s = {"arac": "fib_retracement", "p1": {"bar": 10, "fiyat": 100.0},
         "p2": {"bar": 60, "fiyat": 200.0}}
    fiyatlar = A.fib_retracement_fiyat(t, s)
    beklenen = 200.0 - (200.0 - 100.0) * 0.618
    onay("fib: 0.618 aritmetiği", any(abs(f - beklenen) < 1e-9 for f in fiyatlar),
         f"beklenen {beklenen}")
    ext = A.fib_genisleme_fiyat(t, {"p1": {"bar": 0, "fiyat": 100.0},
                                    "p2": {"bar": 5, "fiyat": 120.0},
                                    "p3": {"bar": 8, "fiyat": 110.0}})
    onay("fib genişleme: 1.618 aritmetiği",
         any(abs(f - (110.0 + 20.0 * 1.618)) < 1e-9 for f in ext))


def test_pozisyon(m):
    t = Tuval(m)
    s = {"giris": 100.0, "stop": 95.0, "hedef": 115.0, "bar_baslangic": -20}
    t.rezerve(A._pozisyon_fiyat(t, s))
    t.hazirla()
    svg = A.long_pozisyon_ciz(t, s)
    onay("pozisyon: R:R = 3.00 etiketi", "R:R 3.00" in svg, svg[:0] or "etiket yok")
    onay("pozisyon: hedef yüzdesi", "+15.00%" in svg)
    onay("pozisyon: stop yüzdesi", "-5.00%" in svg)


def test_tum_araclar(m):
    """Kayıt defterindeki HER araç gerçekten çizilebiliyor mu?"""
    ornek = {
        "trend_cizgisi": {"p1": {"bar": 5, "fiyat": 100}, "p2": {"bar": 60, "fiyat": 110}},
        "yatay_cizgi": {"fiyat": 105},
        "yatay_ray": {"fiyat": 104, "bar": 10},
        "dikey_cizgi": {"bar": 30, "etiket": "olay"},
        "dikdortgen": {"fiyat1": 100, "fiyat2": 104, "bar_baslangic": 20},
        "paralel_kanal": {"p1": {"bar": 5, "fiyat": 98}, "p2": {"bar": 80, "fiyat": 108},
                          "p3": {"bar": 5, "fiyat": 94}},
        "regresyon_kanali": {"bar_baslangic": 10, "bar_bitis": 120, "sapma": 2},
        "fib_retracement": {"p1": {"bar": 10, "fiyat": 96}, "p2": {"bar": 90, "fiyat": 118}},
        "fib_genisleme": {"p1": {"bar": 10, "fiyat": 96}, "p2": {"bar": 40, "fiyat": 112},
                          "p3": {"bar": 60, "fiyat": 104}},
        "fib_kanal": {"p1": {"bar": 10, "fiyat": 96}, "p2": {"bar": 90, "fiyat": 112},
                      "p3": {"bar": 10, "fiyat": 92}},
        "fib_yelpaze": {"p1": {"bar": 10, "fiyat": 96}, "p2": {"bar": 70, "fiyat": 116}},
        "fib_zaman": {"bar_baslangic": 10, "bar_bitis": 20},
        "andrews_catali": {"p1": {"bar": 10, "fiyat": 96}, "p2": {"bar": 40, "fiyat": 112},
                           "p3": {"bar": 55, "fiyat": 100}},
        "ok": {"p1": {"bar": 60, "fiyat": 100}, "p2": {"bar": 80, "fiyat": 115},
               "etiket": "kırılım"},
        "yol": {"noktalar": [{"bar": 10, "fiyat": 100}, {"bar": 40, "fiyat": 108},
                             {"bar": 70, "fiyat": 102}]},
        "long_pozisyon": {"giris": 105, "stop": 100, "hedef": 118},
        "short_pozisyon": {"giris": 105, "stop": 110, "hedef": 92},
        "olcum": {"p1": {"bar": 20, "fiyat": 100}, "p2": {"bar": 45, "fiyat": 112}},
        "metin": {"p1": {"bar": 50, "fiyat": 110}, "metin": "CHoCH"},
        "isaret": {"p1": {"bar": 55, "fiyat": 108}, "yon": "yukari", "etiket": "BOS"},
        "fiyat_etiketi": {"fiyat": 111.5},
        "bilgi_paneli": {"satirlar": [{"ad": "Trend", "deger": "BULL"}]},
        "ma": {"tip": "ema", "period": 20},
        "bulut": {"a": {"tip": "ema", "period": 12}, "b": {"tip": "ema", "period": 34}},
    }
    eksik = sorted(set(A.ARACLAR) - set(ornek))
    onay("araç kapsamı: her araç test ediliyor", not eksik, f"testsiz: {eksik}")
    t = Tuval(m)
    for ad, s in ornek.items():
        spec = dict(s, arac=ad)
        try:
            t.rezerve(A.ARACLAR[ad][0](t, spec))
        except Exception as e:  # noqa: BLE001
            onay(f"araç {ad}: rezerve", False, str(e))
    t.hazirla()
    for ad, s in ornek.items():
        spec = dict(s, arac=ad)
        try:
            parca = A.ARACLAR[ad][1](t, spec)
            onay(f"araç {ad}: çizdi", bool(parca) and "<" in parca)
        except Exception as e:  # noqa: BLE001
            onay(f"araç {ad}: çizdi", False, f"{type(e).__name__}: {e}")
    # takma adlar gerçek araca çözülüyor mu
    kirik = [k for k, v in A.TAKMA_AD.items() if v not in A.ARACLAR]
    onay("takma adlar geçerli", not kirik, str(kirik))


def test_grounding(m):
    """Otomatik katmanın her fiyatı ÖLÇÜLEN kümeden mi geliyor?"""
    ciz, rapor = OC.uret(m, {"regresyon": {"bar": 100},
                             "ma": [{"tip": "ema", "period": 20}]})
    onay("otomatik: çizim üretti", len(ciz) > 5, f"{len(ciz)} çizim")
    olculen = set()
    for c in m:
        olculen |= {round(c[k], 6) for k in ("open", "high", "low", "close")}
    import smc_tespit as ST  # noqa: PLC0415

    out = ST.detect({"candles": m})
    for ob in out.get("order_blocks") or []:
        olculen |= {round(ob["low"], 6), round(ob["high"], 6)}
    for f in out.get("acik_fvgler") or []:
        olculen |= {round(f["low"], 6), round(f["high"], 6)}
    for h in out.get("likidite") or []:
        olculen.add(round(h["price"], 6))
    for ev in out.get("olaylar") or []:
        olculen.add(round(ev["kirilan_seviye"], 6))
        if ev.get("impulse_start") is not None:
            olculen.add(round(ev["impulse_start"], 6))

    kaynaksiz = []
    for spec in ciz:
        for anahtar in ("fiyat", "fiyat1", "fiyat2", "giris", "stop", "hedef"):
            if spec.get(anahtar) is not None and round(float(spec[anahtar]), 6) not in olculen:
                kaynaksiz.append((spec["arac"], anahtar, spec[anahtar]))
        for nk in ("p1", "p2", "p3"):
            p = spec.get(nk)
            if isinstance(p, dict) and "fiyat" in p and round(float(p["fiyat"]), 6) not in olculen:
                kaynaksiz.append((spec["arac"], nk, p["fiyat"]))
    onay("GROUNDING: otomatik katmanda kaynaksız fiyat yok", not kaynaksiz,
         f"kaynaksız: {kaynaksız[:3]}")


def test_uctan_uca(m, tmp: Path):
    job = {
        "veri": {"mumlar": m},
        "baslik": "ÖZ-TEST · sentetik",
        "paneller": [{"tip": "hacim"}, {"tip": "rsi", "period": 14}],
        "otomatik": {"emir": {"yon": "long", "giris": m[-1]["close"],
                              "stop": m[-1]["low"], "hedef": max(c["high"] for c in m) * 1.2,
                              "r": 2.1}},
        "cizimler": [{"arac": "fibonacci", "p1": {"bar": 10, "fiyat": m[10]["low"]},
                      "p2": {"bar": -5, "fiyat": m[-5]["high"]}}],
        "cikti": str(tmp / "oztest.svg"),
    }
    rapor = C.uygula(job, tmp)
    onay("uçtan uca: SVG yazıldı", Path(rapor["cikti"]).exists())
    onay("uçtan uca: çizim sayısı > 8", rapor["cizim_sayisi"] > 8,
         str(rapor["cizim_sayisi"]))
    onay("uçtan uca: takma ad (fibonacci) çözüldü",
         "fib_retracement" in rapor["araclar"], str(rapor["araclar"]))
    onay("uçtan uca: pozisyon kutusu çizildi", "long_pozisyon" in rapor["araclar"])
    metin = Path(rapor["cikti"]).read_text(encoding="utf-8")
    try:
        kok = ET.fromstring(metin)
        onay("SVG iyi biçimli (XML)", kok.tag.endswith("svg"))
    except ET.ParseError as e:
        onay("SVG iyi biçimli (XML)", False, str(e))
    onay("uçtan uca: hedef fiyat kırpılmadı",
         rapor["fiyat_araligi"]["ust"] >= max(c["high"] for c in m) * 1.2)
    return rapor


def main() -> int:
    m = sahte_mumlar()
    tmp = Path(__file__).resolve().parent / "_oztest_cikti"
    tmp.mkdir(exist_ok=True)
    test_olcek(m)
    test_rezervasyon(m)
    test_fib(m)
    test_pozisyon(m)
    test_tum_araclar(m)
    test_grounding(m)
    test_uctan_uca(m, tmp)
    for t in tmp.glob("*.svg"):
        t.unlink()
    tmp.rmdir()

    print(f"GEÇTİ: {len(GECTI)}   KALDI: {len(KALDI)}")
    for k in KALDI:
        print(f"  ✖ {k}")
    if not KALDI:
        print("✔ grafik-cizim motoru SAĞLAM")
    return 0 if not KALDI else 1


if __name__ == "__main__":
    sys.exit(main())
