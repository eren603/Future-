#!/usr/bin/env python3
"""confluence.py öz-testi. Yön, geometri, confluence ve fail-closed kapıları
sınar. SELF_TEST_OK basar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import confluence as cf  # noqa: E402


def main():
    # 1) TEMİZ LONG confluence: yukarı impuls + demand OB golden zone'da +
    #    buyside likidite yukarıda → LONG, giriş=çakışma, R:R>2
    long_job = {
        "structure": {"event": "CHoCH", "direction": "bull"},
        "impulse": {"start": 100.0, "end": 120.0},   # golden zone ~[104.28,107.64]
        "order_blocks": [{"low": 104, "high": 106, "type": "demand"}],
        "liquidity": [{"price": 125, "type": "buyside"},
                      {"price": 95, "type": "sellside"}],
    }
    r = cf.synth(long_job)
    assert r["KARAR"] == "LONG", r
    # golden zone LONG'da impuls tepesinin (120) ALTINDA olmalı
    assert r["golden_zone"][1] < 120, r
    # giriş bölgesi OB ile çakışma → alt sınır 104.28'e yakın, üst 106
    assert 104 <= r["giris_bolgesi"][0] and r["giris_bolgesi"][1] <= 107.65, r
    assert r["gecersizlik_sl"] < r["giris_orta"], r   # SL girişin altında
    assert r["hedefler"][0] == 125, r
    assert r["rr"] >= 2.0, r
    assert not r["kapi_gerekceleri"], r

    # 2) SHORT ayna: aşağı impuls + supply OB + sellside likidite → SHORT
    short_job = {
        "structure": {"event": "CHoCH", "direction": "bear"},
        "impulse": {"start": 120.0, "end": 100.0},   # golden zone ~[112.36,115.72]
        "order_blocks": [{"low": 113, "high": 116, "type": "supply"}],
        "liquidity": [{"price": 95, "type": "sellside"},
                      {"price": 125, "type": "buyside"}],
    }
    r = cf.synth(short_job)
    assert r["KARAR"] == "SHORT", r
    assert r["golden_zone"][0] > 100, r               # SHORT'ta zone dibin (100) ÜSTÜnde
    assert r["gecersizlik_sl"] > r["giris_orta"], r   # SL girişin ÜSTÜnde
    assert r["hedefler"][0] == 95, r
    assert r["rr"] >= 2.0, r
    assert not r["kapi_gerekceleri"], r

    # 3) YALNIZ FİB (confluence yok): OB/FVG yok → NÖTR-BEKLE
    r = cf.synth({
        "structure": {"event": "BOS", "direction": "bull"},
        "impulse": {"start": 100.0, "end": 120.0},
        "liquidity": [{"price": 125, "type": "buyside"}],
    })
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("confluence eksik" in g for g in r["kapi_gerekceleri"]), r

    # 4) YÖN ÇELİŞKİSİ: yapı bull ama impuls aşağı → NÖTR-BEKLE
    r = cf.synth({
        "structure": {"event": "CHoCH", "direction": "bull"},
        "impulse": {"start": 120.0, "end": 100.0},
        "order_blocks": [{"low": 113, "high": 116, "type": "demand"}],
    })
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("çelişiyor" in g for g in r["kapi_gerekceleri"]), r

    # 5) DÜŞÜK R:R: hedef girişe çok yakın → NÖTR-BEKLE
    r = cf.synth({
        "structure": {"event": "CHoCH", "direction": "bull"},
        "impulse": {"start": 100.0, "end": 120.0},
        "order_blocks": [{"low": 104, "high": 106, "type": "demand"}],
        "liquidity": [{"price": 108, "type": "buyside"}],  # çok yakın
    })
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("R:R" in g for g in r["kapi_gerekceleri"]), r

    # 6) İŞARET/GEOMETRİ: LONG golden zone matematiği (0.618–0.786)
    #    range=20 → [120-15.72, 120-12.36] = [104.28, 107.64]
    r = cf.synth(long_job)
    assert abs(r["golden_zone"][0] - 104.28) < 0.01, r
    assert abs(r["golden_zone"][1] - 107.64) < 0.01, r

    print("SELF_TEST_OK: long-confluence, short-ayna, yalniz-fib-BEKLE, "
          "yon-celiskisi-BEKLE, dusuk-rr-BEKLE, golden-zone-geometri")


if __name__ == "__main__":
    main()
