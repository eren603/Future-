#!/usr/bin/env python3
"""Kurul koşusu — GERÇEK paralel fan-out + güven-ağırlıklı sentez tek komutta.

Köprü: tools/suru.py motorları paralel koşar → her motor sonucu bir kurul
danışmanına (stance/confidence/evidence) çevrilir → sentez.py tek nihai karar
üretir. Böylece karar-kurulu "tek oturumda elle" değil, ÖLÇÜLEN paralel koşuyla
çalışır.

Fail-closed: yön çıkaramayan motor kurula OY VERMEZ (çekimser); hiç danışman
yoksa karar NÖTR-BEKLE. Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.

Kullanım:
  python3 kurul_kosu.py --plan plan.json
  plan = {
    "question": "BTCUSDT 4h yön?",
    "invalidation": "4h kapanış swing low altı",
    "thresholds": {"score":0.15, "min_agreement":0.55},
    "timeout": 60,
    "tasks": [
      {"name":"risk", "script":".claude/skills/risk-yonetimi/scripts/risk.py",
       "job":{...}, "weight":1.0,
       "confidence_field":"applied_fraction",   # opsiyonel: güveni bu alandan al
       "evidence_fields":["full_kelly","note"]}, # opsiyonel: kanıt bu alanlardan
      {"name":"turev-akis", "script":".../turev_akis.py", "job":{...}}
    ]
  }
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]                      # .../.claude/skills/karar-kurulu/scripts → repo kökü
sys.path.insert(0, str(HERE))               # sentez
sys.path.insert(0, str(REPO / "tools"))     # suru

import sentez  # noqa: E402
import suru  # noqa: E402


class KurulKosuError(Exception):
    pass


_CONF_FIELDS = ("guven", "guven_skoru", "confidence", "council_conf",
                "guven_araligi", "kapsam", "confluence_skoru")


def _resolve_path(result: dict, dotted: str):
    """Noktalı alan yolu: 'monte_carlo.p50' → result['monte_carlo']['p50']."""
    cur = result
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


_OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b, "!=": lambda a, b: a != b}


def _eval_rule(result: dict, rule: dict) -> tuple[bool, str]:
    """Doğrulama kuralı: {"all":[{"field","op","value"}, ...]} ya da tek koşul.
    Tüm koşullar sağlanırsa confirmed=True. Alan yoksa/sayısal değilse → False
    (fail-closed: doğrulanamayan iddia teyit edilmez)."""
    conds = rule.get("all") if isinstance(rule.get("all"), list) else [rule]
    for c in conds:
        field = c.get("field")
        val = _resolve_path(result, str(field)) if field else None
        if not isinstance(val, (int, float)):
            return False, f"{field}: sayısal değer yok (doğrulanamadı)"
        op = c.get("op", ">")
        fn = _OPS.get(op)
        if fn is None:
            return False, f"bilinmeyen op: {op}"
        if not fn(float(val), float(c.get("value", 0))):
            return False, f"{field}={val} koşulu sağlamıyor ({op} {c.get('value')})"
    return True, "sağlamlık kuralları sağlandı"


def _pick_confidence(result: dict, hint: str | None, direction: float) -> float:
    """Güveni: (1) task ipucu alanı, (2) bilinen güven alanları, (3) |yön|."""
    if hint and isinstance(result.get(hint), (int, float)):
        c = float(result[hint])
    else:
        c = None
        for k in _CONF_FIELDS:
            v = result.get(k)
            if isinstance(v, (int, float)):
                c = float(v)
                break
    if c is None:
        c = min(1.0, abs(direction))        # yön büyüklüğü güvene vekil
    # 0..1'e sıkıştır (bazı alanlar 0..1 dışı olabilir → kırp)
    return min(max(c, 0.0), 1.0)


def _evidence(result: dict, fields: list[str] | None) -> str:
    if fields:
        parts = [f"{f}={result[f]}" for f in fields if f in result]
        if parts:
            return "; ".join(parts)
    # varsayılan: kısa özet (yön + belirgin alanlar)
    keep = {k: result[k] for k in list(result)[:6]
            if isinstance(result[k], (int, float, str, bool))}
    return json.dumps(keep, ensure_ascii=False)[:200]


def _to_advisor(name: str, result: dict, task: dict):
    """Motor sonucunu kurul danışmanına çevir. Yön yoksa None (çekimser)."""
    if not isinstance(result, dict):
        return None, None
    # 1) Zaten danışman biçiminde mi? (ör. turev_akis --emit-advisor)
    if "stance" in result and "confidence" in result:
        adv = {"name": name, "stance": result["stance"],
               "confidence": float(result["confidence"]),
               "evidence": result.get("evidence", "")}
        vconf = result.get("_verifier_confirmed", True)
        return adv, bool(vconf)
    # 2) Yön skoru çıkar
    d = suru._extract_direction(result)
    if d is None:
        return None, None
    if d > 0.05:
        stance = "long"
    elif d < -0.05:
        stance = "short"
    else:
        stance = "flat"
    conf = _pick_confidence(result, task.get("confidence_field"), d)
    ev = _evidence(result, task.get("evidence_fields"))
    return {"name": name, "stance": stance, "confidence": conf, "evidence": ev}, True


def run_council(plan: dict, repo_root: Path | None = None) -> dict:
    tasks = plan.get("tasks")
    if not tasks:
        raise KurulKosuError("VERİ YOK: 'tasks' gerekli")
    root = repo_root or REPO
    # 1) GERÇEK paralel fan-out
    swarm = suru.run_swarm({"tasks": tasks, "timeout": plan.get("timeout", 60)}, root)

    # 2) Sonuç → danışman / doğrulayıcı
    advisors, verifier, abstained, verifiers_run = [], {}, [], []
    task_by_name = {t.get("name"): t for t in tasks}
    for r in swarm["results"]:
        name = r["name"]
        task = task_by_name.get(name, {})
        role = str(task.get("role", "advisor")).lower()

        # DOĞRULAYICI rol (ör. backtest): yön oyu vermez, bir danışmanı teyit/çürütür
        if role == "verifier":
            target = task.get("verifies")
            rule = task.get("confirm_if")
            if not target or not isinstance(rule, dict):
                abstained.append({"name": name,
                                  "reason": "verifier: 'verifies'/'confirm_if' eksik"})
                continue
            if not r["ok"]:
                # doğrulanamadı (motor çöktü) → çürütme YAPMA, sadece not düş
                abstained.append({"name": name,
                                  "reason": f"verifier çalışmadı: {r.get('error','')}"})
                continue
            ok, why = _eval_rule(r["result"], rule)
            verifier[target] = {"confirmed": ok, "reason": None if ok else why}
            verifiers_run.append({"name": name, "verifies": target,
                                  "confirmed": ok, "reason": why})
            continue

        # DANIŞMAN rol (varsayılan)
        if not r["ok"]:
            abstained.append({"name": name, "reason": r.get("error", "hata")})
            continue
        adv, vconf = _to_advisor(name, r["result"], task)
        if adv is None:
            abstained.append({"name": name, "reason": "yön skoru yok (çekimser)"})
            continue
        advisors.append(adv)
        if vconf is not None and name not in verifier:
            verifier[name] = {"confirmed": bool(vconf)}

    # 3) Fail-closed: danışman yoksa BEKLE
    if not advisors:
        return {"question": plan.get("question", ""), "KARAR": "NÖTR-BEKLE",
                "guven_skoru": 0.0, "yon_skoru": 0.0, "uzlasi": 0.0,
                "muhalefet": [], "kapi_gerekceleri": ["hiçbir motor yön üretmedi"],
                "gecersizlik_kosulu": plan.get("invalidation", "BELİRTİLMEDİ"),
                "danisman_ozeti": [], "cekimser": abstained,
                "paralel_kosu": {"ok": swarm["ok_count"], "fail": swarm["failed"],
                                 "dogrulayicilar": verifiers_run},
                "not": "Fan-out sonuç verdi ama yön yok → fail-closed BEKLE. "
                       "Canlı emir DAHİL DEĞİL."}

    # 4) Sentez — tek nihai karar
    decision = sentez.synth({
        "question": plan.get("question", ""),
        "advisors": advisors, "verifier": verifier,
        "invalidation": plan.get("invalidation", "BELİRTİLMEDİ"),
        "thresholds": plan.get("thresholds", {}),
    })
    # 5) Paralel-koşu şeffaflığı ekle
    decision["paralel_kosu"] = {"ok": swarm["ok_count"], "fail": swarm["failed"],
                                "cekimser": abstained,
                                "dogrulayicilar": verifiers_run}
    return decision


def main() -> int:
    ap = argparse.ArgumentParser(description="Kurul koşusu (paralel fan-out → sentez)")
    ap.add_argument("--plan", required=True)
    args = ap.parse_args()
    plan = json.loads(Path(args.plan).expanduser().read_text(encoding="utf-8"))
    try:
        print(json.dumps(run_council(plan), ensure_ascii=False, indent=2))
    except KurulKosuError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
