#!/usr/bin/env python3
"""rr_denetim.py öz-testi. Gerçek BTCUSDT vakalarıyla (ATR≈131). SELF_TEST_OK basar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rr_denetim as rr  # noqa: E402

ATR = 131.2


def test_sisirilmis_4R():
    # Şişirilmiş: 1.0×ATR stop + 4×ATR hedef → rapor R=4.0 ama ŞİŞİRİLMİŞ
    r = rr.denetle({"yon": "short", "entry": 65161, "stop": 65291, "target": 64636, "atr": ATR})
    assert r["verdict"] == "ŞİŞİRİLMİŞ", r
    assert r["R_rapor"] >= 3.9, r
    assert r["R_gercekci"] < r["R_rapor"], r          # gerçekçi R daha düşük olmalı
    assert 1.8 <= r["R_gercekci"] <= 2.2, r           # ≈2.0 (stop 2×ATR tabanına çekildi)


def test_mesru_swing_2R():
    # Meşru swing: 2.1×ATR stop + uzak hedef → TUTARLI, R≈2.2
    r = rr.denetle({"yon": "short", "entry": 65270, "stop": 65550, "target": 64650, "atr": ATR})
    assert r["verdict"] == "TUTARLI", r
    assert abs(r["R_rapor"] - r["R_gercekci"]) < 1e-6, r  # şişirme yok → aynı
    assert 2.1 <= r["R_rapor"] <= 2.3, r


def test_motor_scalp_konsistan():
    # Motor scalp: ~1×ATR stop + ~1.4×ATR hedef → ölçekler uyumlu → TUTARLI
    r = rr.denetle({"yon": "short", "entry": 65160.7, "stop": 65290.7, "target": 64979.9, "atr": ATR})
    assert r["verdict"] == "TUTARLI", r
    assert abs(r["R_rapor"] - 1.39) < 0.05, r


def test_long_simetri():
    # Long tarafı: şişirilmiş dar-stop uzak-hedef aynı şekilde yakalanır
    r = rr.denetle({"yon": "long", "entry": 100.0, "stop": 100.0 - 0.5 * ATR,
                    "target": 100.0 + 4.0 * ATR, "atr": ATR})
    assert r["verdict"] == "ŞİŞİRİLMİŞ", r
    assert r["R_gercekci"] < r["R_rapor"], r


def test_geometri_gecersiz():
    # short ama target entry'nin ÜSTÜNDE → GEÇERSİZ
    r = rr.denetle({"yon": "short", "entry": 65000, "stop": 65200, "target": 65300, "atr": ATR})
    assert r["verdict"] == "GEÇERSİZ", r


def test_atr_zorunlu():
    try:
        rr.denetle({"yon": "short", "entry": 65000, "stop": 65200, "target": 64800, "atr": 0})
        assert False, "atr=0 hata vermeliydi"
    except rr.RRError:
        pass


def test_nan_reddedilir():
    # NaN ATR `atr <= 0` denetimini geçerdi ve şişirilmiş-R panzehirini deviren
    # sessiz TUTARLI üretirdi → artık reddedilmeli (S1).
    nan = float("nan")
    for kotu in ({"atr": nan}, {"stop": float("inf")}, {"entry": nan}):
        job = {"yon": "short", "entry": 65000, "stop": 65200, "target": 64800, "atr": ATR}
        job.update(kotu)
        try:
            rr.denetle(job)
            assert False, f"NaN/inf hata vermeliydi: {kotu}"
        except rr.RRError:
            pass


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("SELF_TEST_OK: sisirilmis-4R-yakalandi, mesru-swing-tutarli, motor-scalp-tutarli, "
          "long-simetri, geometri-gecersiz, atr-zorunlu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
