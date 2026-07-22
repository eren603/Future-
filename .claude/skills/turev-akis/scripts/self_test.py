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
          "short-squeeze, veri-yok-failclosed, kismi-kapsam, notr, "
          "advisor-esleme, advisor-veriyok-none, advisor-notr, advisor-kapsam-confirmed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
