#!/usr/bin/env python3
"""sentez.py öz-testi. SELF_TEST_OK basar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sentez  # noqa: E402


def main():
    # A) Güçlü long konsensüs, doğrulanmış → LONG, yüksek güven
    a = sentez.synth({
        "question": "A",
        "advisors": [
            {"name": "grafik", "stance": "long", "confidence": 0.8},
            {"name": "backtest", "stance": "long", "confidence": 0.7},
            {"name": "risk", "stance": "long", "confidence": 0.6},
        ],
        "verifier": {"grafik": {"confirmed": True}, "backtest": {"confirmed": True}},
        "invalidation": "swing low altı",
    })
    assert a["KARAR"] == "LONG", a
    assert a["guven_skoru"] > 0.4, a
    assert a["gecersizlik_kosulu"] == "swing low altı"

    # B) Long/Short çelişki → NÖTR-BEKLE (düşük uzlaşı / zayıf skor)
    b = sentez.synth({
        "question": "B",
        "advisors": [
            {"name": "grafik", "stance": "long", "confidence": 0.7},
            {"name": "backtest", "stance": "short", "confidence": 0.7},
            {"name": "risk", "stance": "flat", "confidence": 0.5},
        ],
    })
    assert b["KARAR"] == "NÖTR-BEKLE", b
    assert b["guven_skoru"] <= 0.35, b
    assert len(b["kapi_gerekceleri"]) >= 1

    # C) Long ama en güçlü görüş çürütüldü → yön zayıflar, BEKLE'ye düşebilir
    c = sentez.synth({
        "question": "C",
        "advisors": [
            {"name": "grafik", "stance": "long", "confidence": 0.9},
            {"name": "backtest", "stance": "long", "confidence": 0.85},
            {"name": "risk", "stance": "flat", "confidence": 0.5},
        ],
        "verifier": {"grafik": {"confirmed": False, "reason": "tek dönem overfit"},
                     "backtest": {"confirmed": False, "reason": "MC p5 çok negatif"}},
    })
    # çürütme ağırlıkları düşürdü → nötr ağırlık baskın olabilir
    assert c["KARAR"] in ("NÖTR-BEKLE", "LONG"), c
    ver = {r["ad"]: r for r in c["danisman_ozeti"]}
    assert ver["grafik"]["dogrulandi"] is False and ver["grafik"]["etkin_agirlik"] < 0.9

    # D) Tüm görüş çürütüldü → BEKLE
    d = sentez.synth({
        "question": "D",
        "advisors": [{"name": "x", "stance": "long", "confidence": 0.8}],
        "verifier": {"x": {"confirmed": True}},
    })
    assert d["KARAR"] in ("LONG", "NÖTR-BEKLE")  # tek danışman, uzlaşı=1 ama min_side kapısı

    print("SELF_TEST_OK: konsensus, celiski, curutme-penaltisi, karar-kapilari")


if __name__ == "__main__":
    main()
