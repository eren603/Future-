#!/usr/bin/env python3
"""Karar Kurulu sentez motoru — çok-mercekli görüşleri + adversarial doğrulamayı
tek nihai karara indirger (güven-ağırlıklı, çoğunluk-oyu DEĞİL).

Girdi JSON:
{
  "question": "BTCUSDT 4h yön?",
  "advisors": [
    {"name":"grafik-calisma","stance":"long","confidence":0.72,"evidence":"CHoCH + golden zone"},
    {"name":"backtest-motoru","stance":"long","confidence":0.61,"evidence":"PF 1.8, MC p50>0"},
    {"name":"risk-yonetimi","stance":"flat","confidence":0.50,"evidence":"Kelly~0"},
    ...
  ],
  "verifier": { "grafik-calisma": {"confirmed": true},
                "backtest-motoru": {"confirmed": false, "reason":"tek dönem, overfit riski"} },
  "invalidation": "4h kapanış swing low altı",
  "thresholds": {"score":0.15, "min_agreement":0.55, "refute_penalty":0.25,
                 "min_side_weight":0.6}
}

stance eşlemesi: long/al/+1 => +1 ; short/sat/-1 => -1 ; flat/nötr/bekle/wait/0 => 0.
Karar: LONG / SHORT / NÖTR-BEKLE  + güven skoru + uzlaşı + muhalefet + geçersizlik.
Determinist — rastgelelik yok.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path


class KurulError(Exception):
    pass


LONG = {"long", "al", "buy", "+1", "1", "bull", "yukarı"}
SHORT = {"short", "sat", "sell", "-1", "bear", "aşağı"}
FLAT = {"flat", "nötr", "notr", "neutral", "bekle", "wait", "0", "yok"}


def stance_dir(stance) -> int:
    s = str(stance).strip().lower()
    if s in LONG:
        return 1
    if s in SHORT:
        return -1
    if s in FLAT:
        return 0
    raise KurulError(f"Bilinmeyen stance: {stance}")


def synth(job: dict) -> dict:
    advisors = job.get("advisors") or []
    if not advisors:
        raise KurulError("En az 1 danışman görüşü gerekli")
    th = job.get("thresholds", {})
    score_th = float(th.get("score", 0.15))
    min_agree = float(th.get("min_agreement", 0.55))
    refute_pen = float(th.get("refute_penalty", 0.25))
    min_side_weight = float(th.get("min_side_weight", 0.6))
    verifier = job.get("verifier", {}) or {}

    rows = []
    for a in advisors:
        name = str(a.get("name", "?"))
        d = stance_dir(a.get("stance", "flat"))
        conf = float(a.get("confidence", 0.5))
        conf = min(max(conf, 0.0), 1.0)
        v = verifier.get(name, {})
        confirmed = bool(v.get("confirmed", True))
        eff = conf * (1.0 if confirmed else refute_pen)  # çürütülen görüş ağırlığı düşer
        rows.append({"name": name, "dir": d, "confidence": round(conf, 4),
                     "confirmed": confirmed, "eff_weight": round(eff, 4),
                     "evidence": a.get("evidence", ""),
                     "reason_refuted": (v.get("reason") if not confirmed else None)})

    total_w = sum(r["eff_weight"] for r in rows)
    if total_w <= 0:
        return _decision("NÖTR-BEKLE", 0.0, 0.0, rows, job,
                         note="Tüm görüşler çürütüldü veya sıfır güven → işlem yok")

    # Güven-ağırlıklı yön skoru [-1, +1]
    score = sum(r["eff_weight"] * r["dir"] for r in rows) / total_w

    # Yön bazında ağırlıklar
    w_long = sum(r["eff_weight"] for r in rows if r["dir"] > 0)
    w_short = sum(r["eff_weight"] for r in rows if r["dir"] < 0)
    w_flat = sum(r["eff_weight"] for r in rows if r["dir"] == 0)

    # Uzlaşı = baskın yönün ağırlık payı (0..1); yüksek = güçlü konsensüs
    dominant = max(w_long, w_short, w_flat)
    agreement = dominant / total_w

    # Muhalefet listesi (baskın yöne karşı çıkanlar)
    if score > 0:
        side = "LONG"; side_weight = w_long
        dissent = [r["name"] for r in rows if r["dir"] <= 0 and r["eff_weight"] > 0]
    elif score < 0:
        side = "SHORT"; side_weight = w_short
        dissent = [r["name"] for r in rows if r["dir"] >= 0 and r["eff_weight"] > 0]
    else:
        side = "NÖTR-BEKLE"; side_weight = w_flat
        dissent = []

    # Karar kapıları (fail-closed): zayıf sinyal / düşük uzlaşı / düşük yön-ağırlığı → BEKLE
    reasons = []
    decision = side
    if abs(score) < score_th:
        decision = "NÖTR-BEKLE"; reasons.append(f"|skor|={abs(score):.2f} < eşik {score_th}")
    if agreement < min_agree:
        decision = "NÖTR-BEKLE"; reasons.append(f"uzlaşı {agreement:.2f} < {min_agree}")
    if side != "NÖTR-BEKLE" and side_weight < min_side_weight:
        decision = "NÖTR-BEKLE"; reasons.append(f"yön ağırlığı {side_weight:.2f} < {min_side_weight}")

    # Konsey güveni: |skor| * uzlaşı, doğrulanan görüş oranıyla ölçekli
    confirmed_ratio = sum(1 for r in rows if r["confirmed"]) / len(rows)
    council_conf = round(abs(score) * agreement * (0.5 + 0.5 * confirmed_ratio), 4)
    if decision == "NÖTR-BEKLE":
        council_conf = round(min(council_conf, 0.35), 4)  # beklerken güven tavanı

    return _decision(decision, council_conf, round(score, 4), rows, job,
                     agreement=round(agreement, 4), dissent=dissent,
                     gate_reasons=reasons)


def _decision(decision, conf, score, rows, job, *, agreement=0.0, dissent=None,
              gate_reasons=None, note=None) -> dict:
    return {
        "question": job.get("question", ""),
        "KARAR": decision,
        "guven_skoru": conf,
        "yon_skoru": score,
        "uzlasi": agreement,
        "muhalefet": dissent or [],
        "kapi_gerekceleri": gate_reasons or [],
        "gecersizlik_kosulu": job.get("invalidation", "BELİRTİLMEDİ"),
        "esik_kaynagi": ("tasarım varsayımı (fail-closed karar kapıları; risk "
                         "iştahını kodlar, piyasa verisinden türetilmez — "
                         "thresholds ile koşu başına değiştirilebilir)"),
        "danisman_ozeti": [
            {"ad": r["name"], "yon": {1: "long", -1: "short", 0: "nötr"}[r["dir"]],
             "guven": r["confidence"], "dogrulandi": r["confirmed"],
             "etkin_agirlik": r["eff_weight"], "kanit": r["evidence"],
             "curutme": r["reason_refuted"]}
            for r in rows
        ],
        "not": note or "Karar-destek çıktısıdır; kesinlik/sinyal değil. Canlı emir DAHİL DEĞİL.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Karar Kurulu sentez motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(synth(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
