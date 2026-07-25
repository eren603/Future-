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
  # FAIL-CLOSED: verifier'da girdisi OLMAYAN danışman DOĞRULANMAMIŞ sayılır ve
  # çürütme penaltısı alır. Motor kendi doğrulamasını taşıyorsa (advisor içinde
  # "_verifier_confirmed": true/false) o okunur. Kanıtsız görüş tam ağırlık ALMAZ.
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


def satirlar(advisors: list, verifier: dict | None = None,
             refute_pen: float = 0.25) -> list:
    """Danışman görüşlerini etkin ağırlıklı satırlara çevir.

    Modül düzeyinde durur ki eşik kalibrasyonu (esik_kalibre.py) AYNI etkin
    ağırlıkları kullansın — iki yerde iki kopya olsaydı eşikler zamanla
    sentezin gerçek ağırlıklarından ayrışırdı (sessiz kayma).
    """
    verifier = verifier or {}
    rows = []
    for a in advisors:
        name = str(a.get("name", "?"))
        d = stance_dir(a.get("stance", "flat"))
        conf = min(max(float(a.get("confidence", 0.5)), 0.0), 1.0)
        # Fail-closed doğrulama çözümü. Öncelik:
        #   1) açık verifier girdisi (verifier[name]["confirmed"])
        #   2) danışmanın kendi taşıdığı _verifier_confirmed alanı (ör. turev-akis
        #      to_advisor bunu üretir — motor kendi kapsamını doğrular)
        #   3) hiçbiri yoksa DOĞRULANMAMIŞ sayılır → çürütme penaltısı (fail-OPEN değil).
        # Eski davranış get("confirmed", True) idi: doğrulanmayan görüş TAM ağırlık
        # alıyordu — "fail-closed" sözleşmesinin tersi. Artık kanıt yoksa güvenilmez.
        v = verifier.get(name, {})
        if "confirmed" in v:
            confirmed = bool(v["confirmed"])
            refute_reason = v.get("reason") if not confirmed else None
        elif "_verifier_confirmed" in a:
            confirmed = bool(a["_verifier_confirmed"])
            refute_reason = ("motorun kendi doğrulaması yetersiz (kapsam/kanıt düşük)"
                             if not confirmed else None)
        else:
            confirmed = False
            refute_reason = "doğrulama YOK → fail-closed varsayılan (çürütme penaltısı)"
        eff = conf * (1.0 if confirmed else refute_pen)  # çürütülen görüş ağırlığı düşer
        rows.append({"name": name, "dir": d, "confidence": round(conf, 4),
                     "confirmed": confirmed, "eff_weight": round(eff, 4),
                     "evidence": a.get("evidence", ""),
                     "reason_refuted": refute_reason})
    return rows


def olcumler(rows: list) -> dict:
    """Satırlardan sentez ölçümleri: skor, uzlaşı, yön ağırlığı.

    Eşik kalibrasyonu null dağılımı üretirken AYNI aritmetiği kullanır —
    eşik ile karar aynı ölçekte olsun (ölçek uyuşmazlığı = sahte kapı).
    """
    total_w = sum(r["eff_weight"] for r in rows)
    if total_w <= 0:
        return {"total_w": 0.0, "score": 0.0, "agreement": 0.0,
                "side_weight": 0.0, "side": "NÖTR-BEKLE",
                "w_long": 0.0, "w_short": 0.0, "w_flat": 0.0}
    score = sum(r["eff_weight"] * r["dir"] for r in rows) / total_w
    w_long = sum(r["eff_weight"] for r in rows if r["dir"] > 0)
    w_short = sum(r["eff_weight"] for r in rows if r["dir"] < 0)
    w_flat = sum(r["eff_weight"] for r in rows if r["dir"] == 0)
    agreement = max(w_long, w_short, w_flat) / total_w
    if score > 0:
        side, side_weight = "LONG", w_long
    elif score < 0:
        side, side_weight = "SHORT", w_short
    else:
        side, side_weight = "NÖTR-BEKLE", w_flat
    return {"total_w": total_w, "score": score, "agreement": agreement,
            "side_weight": side_weight, "side": side,
            "w_long": w_long, "w_short": w_short, "w_flat": w_flat}


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

    rows = satirlar(advisors, verifier, refute_pen)
    total_w = sum(r["eff_weight"] for r in rows)
    if total_w <= 0:
        return _decision("NÖTR-BEKLE", 0.0, 0.0, rows, job,
                         note="Tüm görüşler çürütüldü veya sıfır güven → işlem yok")

    o = olcumler(rows)
    score, agreement = o["score"], o["agreement"]
    w_long, w_short, w_flat = o["w_long"], o["w_short"], o["w_flat"]
    side, side_weight = o["side"], o["side_weight"]

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


def yon_bias(score) -> str:
    """Ağırlıklı yön eğilimi — KARAR kapısından BAĞIMSIZ. Kullanıcıya her koşuda
    net yön verilir: kapı BEKLE dese bile eğilim gizlenmez. Saf işaret: >0 LONG,
    <0 SHORT, tam 0 ise NÖTR (gerçek berabere)."""
    if score > 0:
        return "LONG"
    if score < 0:
        return "SHORT"
    return "NÖTR"


def _decision(decision, conf, score, rows, job, *, agreement=0.0, dissent=None,
              gate_reasons=None, note=None) -> dict:
    return {
        "question": job.get("question", ""),
        "YON_BIAS": yon_bias(score),
        "KARAR": decision,
        "guven_skoru": conf,
        "yon_skoru": score,
        "uzlasi": agreement,
        "muhalefet": dissent or [],
        "kapi_gerekceleri": gate_reasons or [],
        "gecersizlik_kosulu": job.get("invalidation", "BELİRTİLMEDİ"),
        # Eşiklerin NEREDEN geldiği kararla birlikte taşınır. Çağıran koşu
        # başına kalibre ediyorsa (esik_kalibre.py) kaynağını yazar; yazmazsa
        # eşikler tasarım varsayımıdır ve öyle etiketlenir.
        "esik_kaynagi": job.get("esik_kaynagi") or (
            "tasarım varsayımı (fail-closed karar kapıları; risk iştahını "
            "kodlar, piyasa verisinden türetilmez — thresholds ile koşu "
            "başına değiştirilebilir)"),
        "esikler": {
            "score": float((job.get("thresholds") or {}).get("score", 0.15)),
            "min_agreement": float((job.get("thresholds") or {}).get(
                "min_agreement", 0.55)),
            "min_side_weight": float((job.get("thresholds") or {}).get(
                "min_side_weight", 0.6)),
            "refute_penalty": float((job.get("thresholds") or {}).get(
                "refute_penalty", 0.25))},
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
