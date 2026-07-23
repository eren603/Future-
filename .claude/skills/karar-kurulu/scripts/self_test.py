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

    # G) İŞARET BÜTÜNLÜĞÜ — LONG kararı verilince long ağırlığı short'tan büyük olmalı.
    # (a/b doğrulanır; fail-closed default altında doğrulanmamış görüş penaltı alıp
    # min_side kapısını düşürürdü — bu test yön bütünlüğünü ölçüyor, doğrulamayı değil.)
    g = sentez.synth({
        "question": "G",
        "advisors": [
            {"name": "a", "stance": "long", "confidence": 0.9},
            {"name": "b", "stance": "long", "confidence": 0.8},
            {"name": "c", "stance": "short", "confidence": 0.4},
        ],
        "verifier": {"a": {"confirmed": True}, "b": {"confirmed": True}},
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

    # I) YON_BIAS kapıdan bağımsız: kapı BEKLE'ye düşürse bile yön SHORT basılır.
    # short 0.5 + iki flat 0.6 → yön ağırlığı 0.5<0.6 kapısı BEKLE verir; skor hâlâ negatif.
    i = sentez.synth({
        "question": "I",
        "advisors": [
            {"name": "a", "stance": "short", "confidence": 0.5},
            {"name": "b", "stance": "flat", "confidence": 0.6},
            {"name": "c", "stance": "flat", "confidence": 0.6},
        ],
    })
    assert i["yon_skoru"] < 0, i
    assert i["KARAR"] == "NÖTR-BEKLE", ("kapı BEKLE bekleniyordu", i["KARAR"])
    assert i["YON_BIAS"] == "SHORT", ("YÖN GİZLENDİ — kapı BEKLE ama yön SHORT olmalı", i)
    assert sentez.yon_bias(0.3) == "LONG" and sentez.yon_bias(-0.3) == "SHORT" and sentez.yon_bias(0.0) == "NÖTR"

    # J) FAIL-CLOSED VARSAYILAN (Y1) — verifier girdisi OLMAYAN görüş doğrulanmamış
    #    sayılır ve çürütme penaltısı alır (eski davranış: tam ağırlık = fail-OPEN).
    j = sentez.synth({
        "question": "J",
        "advisors": [{"name": "x", "stance": "long", "confidence": 0.8}],  # verifier YOK
    })
    jx = j["danisman_ozeti"][0]
    assert jx["dogrulandi"] is False, ("FAIL-CLOSED KIRILDI: doğrulama yoksa çürütülmüş sayılmalı", j)
    assert jx["etkin_agirlik"] < 0.8, ("penaltı uygulanmalı (0.8×0.25=0.2)", jx)
    assert jx["curutme"], ("çürütme gerekçesi yazılmalı", jx)

    # K) DOĞRULAMA KÖPRÜSÜ (Y7) — danışman kendi _verifier_confirmed alanını taşırsa
    #    (turev-akis to_advisor bunu üretir) sentez onu okur; ayrı verifier gerekmez.
    k = sentez.synth({
        "question": "K",
        "advisors": [{"name": "turev-akis", "stance": "short", "confidence": 0.7,
                      "_verifier_confirmed": True}],
    })
    kx = k["danisman_ozeti"][0]
    assert kx["dogrulandi"] is True, ("_verifier_confirmed=True köprülenmeli", k)
    assert abs(kx["etkin_agirlik"] - 0.7) < 1e-9, ("doğrulanınca tam ağırlık", kx)

    # K2) Danışman _verifier_confirmed=False taşırsa → penaltı
    k2 = sentez.synth({
        "question": "K2",
        "advisors": [{"name": "turev-akis", "stance": "short", "confidence": 0.7,
                      "_verifier_confirmed": False}],
    })
    assert k2["danisman_ozeti"][0]["dogrulandi"] is False and \
        k2["danisman_ozeti"][0]["etkin_agirlik"] < 0.7, k2

    # L) ÖNCELİK — açık verifier girdisi danışmanın kendi alanını EZER.
    l = sentez.synth({
        "question": "L",
        "advisors": [{"name": "turev-akis", "stance": "short", "confidence": 0.7,
                      "_verifier_confirmed": True}],
        "verifier": {"turev-akis": {"confirmed": False, "reason": "dış çürütme"}},
    })
    lx = l["danisman_ozeti"][0]
    assert lx["dogrulandi"] is False, ("açık verifier _verifier_confirmed'i ezmeli", l)
    assert lx["curutme"] == "dış çürütme", lx

    print("SELF_TEST_OK: konsensus, celiski, curutme-penaltisi, karar-kapilari, "
          "yon-short, isaret-simetri, isaret-butunluk, canlilik, yon-bias-kapidan-bagimsiz, "
          "fail-closed-varsayilan, dogrulama-koprusu, verifier-onceligi")


if __name__ == "__main__":
    main()
