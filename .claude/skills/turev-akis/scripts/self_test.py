#!/usr/bin/env python3
"""Türev-akış motoru sentetik self-test — mekanik doğruluk (isabet kanıtı DEĞİL)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from turev_akis import analyze, to_advisor  # noqa: E402


def _approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_taze_short():
    # OI yukari + fiyat asagi = taze short = ayi
    r = analyze({"price_series": [66700, 66000], "oi_series": [100.0, 105.0]})
    assert r["yon_skoru"] < 0, r
    assert any("TAZE SHORT" in w for w in r["erken_uyari"]), r["erken_uyari"]


def test_deleveraging():
    # OI asagi + fiyat asagi = long tasfiyesi
    r = analyze({"price_series": [66700, 65500], "oi_series": [107.0, 102.5]})
    assert r["yon_skoru"] < 0, r
    assert any("DELEVERAGING" in w for w in r["erken_uyari"]), r["erken_uyari"]


def test_saglikli_trend():
    # OI yukari + fiyat yukari = taze long = boga
    r = analyze({"price_series": [65000, 66000], "oi_series": [100.0, 106.0]})
    assert r["yon_skoru"] > 0, r


def test_funding_asiri_long_contrarian():
    r = analyze({"funding": 0.05})
    f = [x for x in r["faktorler"] if x["faktor"] == "funding"][0]
    assert f["skor"] == -1.0, f  # asiri long -> contrarian ayi


def test_short_squeeze_liq():
    r = analyze({"liq_long": 0.5, "liq_short": 10.0})
    lq = [x for x in r["faktorler"] if x["faktor"] == "liquidation"][0]
    assert lq["skor"] == 0.8, lq  # short tasfiyesi baskin -> yukari squeeze


def test_liq_tek_tarafli():
    # Y3: TEK-TARAFLI likidasyon EN GÜÇLÜ kaskaddır; eski kod (ls>0/ll>0 bekçileri)
    # bir taraf 0 olunca "dengeli" 0.0 döndürüp motoru tam gerektiğinde susturuyordu.
    r = analyze({"liq_long": 10.0, "liq_short": 0.0})   # yalnız long tasfiyesi → aşağı kaskad
    lq = [x for x in r["faktorler"] if x["faktor"] == "liquidation"][0]
    assert lq["skor"] == -0.8, ("tek-taraflı long tasfiyesi ayı -0.8 olmalı", lq)
    r2 = analyze({"liq_long": 0.0, "liq_short": 8.0})   # yalnız short tasfiyesi → squeeze
    lq2 = [x for x in r2["faktorler"] if x["faktor"] == "liquidation"][0]
    assert lq2["skor"] == 0.8, ("tek-taraflı short tasfiyesi boğa +0.8 olmalı", lq2)
    # Gerçekten dengeli (oran<2x) hâlâ 0.0
    r3 = analyze({"liq_long": 10.0, "liq_short": 8.0})
    lq3 = [x for x in r3["faktorler"] if x["faktor"] == "liquidation"][0]
    assert lq3["skor"] == 0.0, ("oran<2x dengeli olmalı", lq3)


def _fund(v):
    return [x for x in analyze({"funding": v})["faktorler"] if x["faktor"] == "funding"][0]["skor"]


def test_funding_merdiveni():
    # Y4 + kademe: MONOTON contrarian merdiven. Taban nötr (Y4 çekirdeği), ama gerçekten
    # kalabalık (0.03–0.05) bölge hafife ALINMAZ — aksi halde bıçak sırtında meşru
    # SHORT'lar LONG'a aşırı-döner. Eski kod 0.01'i -1.0 sanıp sistematik aşağı yanlıydı.
    assert _fund(0.01) == 0.0, "taban %0.01 nötr (aşırı değil)"
    assert _fund(0.005) == 0.0, "taban-altı nötr"
    assert _fund(0.02) == -0.3, "ılımlı elevated → -0.3"
    assert _fund(0.03) == -0.6, "kalabalık → -0.6 (hafife alınmaz)"
    assert _fund(0.04) == -0.6, "kalabalık → -0.6"
    assert _fund(0.05) == -1.0, "aşırı → -1.0"
    assert _fund(0.06) == -1.0, "aşırı → -1.0"
    # Simetri: short-yoğun negatif funding contrarian BOĞA, aynı büyüklükte
    assert _fund(-0.03) == +0.6 and _fund(-0.05) == +1.0, "negatif taraf simetrik contrarian boğa"
    # Monotonluk: |f| arttıkça |skor| azalmaz
    vals = [abs(_fund(v)) for v in (0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06)]
    assert all(b >= a for a, b in zip(vals, vals[1:])), ("funding merdiveni monoton değil", vals)


def test_varsayim_defteri_sabitler():
    # Y5: faktör büyüklükleri + eşleme eşikleri deftere yazılmalı ("gizli sabit yok")
    r = analyze({"funding": 0.0})
    metin = " ".join(r["varsayimlar"])
    assert "faktör skor büyüklükleri" in metin, metin
    assert "eşleme eşikleri" in metin, metin


def test_veri_yok_fail_closed():
    # Hicbir alan yok -> VERI YOK, yon uretilmez (fail-closed)
    r = analyze({})
    assert r["KARAR_TUREV"] == "VERİ YOK", r
    assert r["yon_skoru"] is None, r
    assert r["guven"] == 0.0, r


def test_kismi_kapsam_normalize():
    # Sadece funding gelirse kapsam<1 ama yon uretilir (yeniden normalize)
    r = analyze({"funding": 0.0})
    assert r["yon_skoru"] is not None, r
    assert r["kapsam"] < 1.0, r


def test_nötr_karisik():
    # Celiskili sinyaller ~ notr
    r = analyze({"price_series": [66000, 66000], "oi_series": [100.0, 100.0],
                 "funding": 0.0, "taker_lsr": 1.0})
    assert -0.2 < r["yon_skoru"] < 0.2, r


def test_advisor_eslemesi():
    # AYI skor -> stance short, confidence = guven, evidence dolu
    r = analyze({"price_series": [66700, 65500], "oi_series": [107.0, 102.5], "funding": 0.0015})
    a = to_advisor(r)
    assert a is not None and a["name"] == "turev-akis", a
    assert a["stance"] == "short", a
    assert _approx(a["confidence"], r["guven"]), a
    assert "Türev motoru" in a["evidence"], a


def test_advisor_veri_yok_none():
    # VERI YOK -> danisman EKLENMEZ (None)
    assert to_advisor(analyze({})) is None


def test_advisor_notr_flat():
    r = analyze({"price_series": [66000, 66000], "oi_series": [100.0, 100.0],
                 "funding": 0.0, "taker_lsr": 1.0})
    a = to_advisor(r)
    assert a["stance"] == "flat", a


def test_advisor_kapsam_confirmed():
    # Tam kapsam -> confirmed true; ince kapsam -> false
    tam = to_advisor(analyze({"price_series": [66700, 65500], "oi_series": [107.0, 102.5],
                              "funding": 0.0015, "cvd_series": [12, 15], "taker_lsr": 0.8,
                              "liq_long": 1.0, "liq_short": 0.1}))
    assert tam["_verifier_confirmed"] is True, tam
    ince = to_advisor(analyze({"funding": 0.05}))
    assert ince["_verifier_confirmed"] is False, ince


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("SELF_TEST_OK: taze-short, deleveraging, saglikli-trend, funding-contrarian, "
          "short-squeeze, liq-tek-tarafli, funding-merdiveni-monoton, varsayim-defteri-sabitler, "
          "veri-yok-failclosed, kismi-kapsam, notr, "
          "advisor-esleme, advisor-veriyok-none, advisor-notr, advisor-kapsam-confirmed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
