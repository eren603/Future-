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

    # I) KÖPRÜ — kurul_kosu: GERÇEK paralel fan-out (suru) → danışman/doğrulayıcı → sentez.
    #    grafik-calisma + turev-akis → yönsel danışman (oy verir).
    #    risk → doğrulayıcı rol (grafik'i teyit eder; units>0).
    import kurul_kosu  # noqa: E402
    plan = {
        "question": "Tam kurul: grafik + türev danışman, risk doğrulayıcı",
        "invalidation": "4h swing low altı",
        "timeout": 60,
        "tasks": [
            {"name": "grafik-calisma", "weight": 1.0,
             "script": ".claude/skills/grafik-calisma/scripts/confluence.py",
             "job": {"structure": {"event": "CHoCH", "direction": "bull"},
                     "impulse": {"start": 100.0, "end": 120.0}, "htf_bias": "bull",
                     "order_blocks": [{"low": 104, "high": 106, "type": "demand"}],
                     "fvgs": [{"low": 104.5, "high": 105.5, "type": "bull"}],
                     "liquidity": [{"price": 128, "type": "buyside"},
                                   {"price": 95, "type": "sellside"}], "atr": 1.5}},
            {"name": "turev-akis", "weight": 1.0,
             "script": ".claude/skills/turev-akis/scripts/turev_akis.py",
             "job": {"price_series": [64000, 64500, 65200, 66000, 66800],
                     "oi_series": [100, 102, 105, 108, 111], "funding": 0.03,
                     "cvd_series": [10, 12, 15, 19, 24], "taker_lsr": 1.35,
                     "liq_long": 0.5, "liq_short": 9.0}},
            {"name": "risk-dogrulayici", "role": "verifier",
             "verifies": "grafik-calisma",
             "confirm_if": {"field": "units", "op": ">", "value": 0},
             "script": ".claude/skills/risk-yonetimi/scripts/risk.py",
             "job": {"op": "position_size", "method": "fixed_fractional",
                     "equity": 10000, "risk_pct": 1.0, "entry": 100, "stop": 98}},
        ],
    }
    k = kurul_kosu.run_council(plan, kurul_kosu.REPO)
    names = {r["ad"]: r for r in k["danisman_ozeti"]}
    assert "grafik-calisma" in names and names["grafik-calisma"]["yon"] == "long", k
    assert "turev-akis" in names and names["turev-akis"]["yon"] == "long", k
    assert k["KARAR"] == "LONG", k                       # iki hizalı danışman → LONG
    # doğrulayıcı çalıştı ve grafik'i teyit etti
    dv = {d["verifies"]: d for d in k["paralel_kosu"]["dogrulayicilar"]}
    assert dv["grafik-calisma"]["confirmed"] is True, k
    assert names["grafik-calisma"]["dogrulandi"] is True, k

    # J) DOĞRULAYICI KURALI (backtest-şekilli sonuç, noktalı alan yolu) birim testi
    ok, _ = kurul_kosu._eval_rule(
        {"profit_factor": 1.8, "monte_carlo": {"p50": 0.12}},
        {"all": [{"field": "profit_factor", "op": ">", "value": 1.0},
                 {"field": "monte_carlo.p50", "op": ">", "value": 0}]})
    assert ok is True
    bad, why = kurul_kosu._eval_rule(
        {"profit_factor": 0.7},
        {"field": "profit_factor", "op": ">", "value": 1.0})
    assert bad is False and "profit_factor" in why
    # fail-closed: alan yoksa doğrulanamaz → False
    miss, _ = kurul_kosu._eval_rule({}, {"field": "sharpe", "op": ">", "value": 0})
    assert miss is False

    print("SELF_TEST_OK: konsensus, celiski, curutme-penaltisi, karar-kapilari, "
          "yon-short, isaret-simetri, isaret-butunluk, canlilik, "
          "KOPRU-tam-kurul(grafik+turev+dogrulayici), dogrulayici-kural")


if __name__ == "__main__":
    main()
