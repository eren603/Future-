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

    # E) YÖN DOĞRULUĞU — hepsi ayı → SHORT, skor NEGATİF (short dediğinde short)
    e = sentez.synth({
        "question": "E",
        "advisors": [
            {"name": "grafik", "stance": "short", "confidence": 0.8},
            {"name": "backtest", "stance": "sat", "confidence": 0.7},
            {"name": "risk", "stance": "sell", "confidence": 0.6},
        ],
        "verifier": {"grafik": {"confirmed": True}, "backtest": {"confirmed": True}},
    })
    assert e["KARAR"] == "SHORT", e
    assert e["yon_skoru"] < 0, e  # işaret negatif olmalı

    # F) İŞARET SİMETRİSİ — aynı seti long yap → LONG, skor mutlak değeri ~aynı,
    #    işaret ters. (long dediğinde long, tam ayna)
    f = sentez.synth({
        "question": "F",
        "advisors": [
            {"name": "grafik", "stance": "long", "confidence": 0.8},
            {"name": "backtest", "stance": "al", "confidence": 0.7},
            {"name": "risk", "stance": "buy", "confidence": 0.6},
        ],
        "verifier": {"grafik": {"confirmed": True}, "backtest": {"confirmed": True}},
    })
    assert f["KARAR"] == "LONG", f
    assert f["yon_skoru"] > 0, f
    assert abs(f["yon_skoru"] + e["yon_skoru"]) < 1e-9, (e["yon_skoru"], f["yon_skoru"])

    # G) İŞARET BÜTÜNLÜĞÜ — LONG kararı verilince long ağırlığı short'tan büyük olmalı
    g = sentez.synth({
        "question": "G",
        "advisors": [
            {"name": "a", "stance": "long", "confidence": 0.9},
            {"name": "b", "stance": "long", "confidence": 0.8},
            {"name": "c", "stance": "short", "confidence": 0.4},
        ],
    })
    wl = sum(x["etkin_agirlik"] for x in g["danisman_ozeti"] if x["yon"] == "long")
    ws = sum(x["etkin_agirlik"] for x in g["danisman_ozeti"] if x["yon"] == "short")
    assert g["KARAR"] == "LONG" and wl > ws, (g["KARAR"], wl, ws)

    # H) CANLILIK (anti-dejenerasyon): hizalı + güçlü + doğrulanmış panel HER
    #    ZAMAN ateşlemeli — "sürekli BEKLE" ölü sistemine düşmemeli. Kapılar
    #    yalnız zayıf/çelişkili sinyali elemeli, gerçek konsensüsü değil.
    for stance, want in (("long", "LONG"), ("short", "SHORT")):
        h = sentez.synth({
            "question": "H",
            "advisors": [
                {"name": "a", "stance": stance, "confidence": 0.75},
                {"name": "b", "stance": stance, "confidence": 0.7},
                {"name": "c", "stance": stance, "confidence": 0.65},
            ],
            "verifier": {"a": {"confirmed": True}, "b": {"confirmed": True}},
        })
        assert h["KARAR"] == want, ("CANLILIK KIRILDI", stance, h["KARAR"])

    print("SELF_TEST_OK: konsensus, celiski, curutme-penaltisi, karar-kapilari, "
          "yon-short, isaret-simetri, isaret-butunluk, canlilik")


if __name__ == "__main__":
    main()
