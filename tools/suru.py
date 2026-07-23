#!/usr/bin/env python3
"""Paralel alt-ajan orkestrasyonu (sürü) — programatik çok-motor koşusu.

karar-kurulu tek oturumda konuşur; bu araç repodaki motorları GERÇEKTEN paralel
(çoklu iş parçacığı, alt-süreç) koşar, sonuçları toplar ve güven-ağırlıklı
birleştirir. Fail-closed: bir motor çökerse null döner, sürü devam eder; çelişki/
zayıf sinyalde birleşik karar NÖTR (canlı emir DAHİL DEĞİL).

Kullanım:
  python3 suru.py --plan plan.json
  plan = {"tasks":[
     {"name":"risk","script":".claude/skills/risk-yonetimi/scripts/risk.py",
      "job":{...}, "weight":1.0},
     {"name":"portfoy","script":".../portfolio.py","job":{...}}
   ], "timeout": 60}
  (ya da run_swarm() import et)
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


class SuruError(Exception):
    pass


def _run_one(task: dict, timeout: float, repo_root: Path) -> dict:
    name = task.get("name", "?")
    script = task.get("script")
    if not script:
        return {"name": name, "ok": False, "error": "script yok", "result": None}
    spath = (repo_root / script) if not Path(script).is_absolute() else Path(script)
    if not spath.exists():
        return {"name": name, "ok": False, "error": f"script yok: {spath}",
                "result": None}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as tf:
        json.dump(task.get("job", {}), tf, ensure_ascii=False)
        jobfile = tf.name
    try:
        proc = subprocess.run([sys.executable, str(spath), "--job", jobfile],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": name, "ok": False, "error": "timeout", "result": None}
    finally:
        try:
            Path(jobfile).unlink()
        except OSError:
            pass
    if proc.returncode != 0:
        return {"name": name, "ok": False,
                "error": (proc.stderr or proc.stdout)[-300:], "result": None}
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"name": name, "ok": False, "error": "çıktı JSON değil",
                "result": proc.stdout[-300:]}
    return {"name": name, "ok": True, "error": None, "result": result,
            "weight": float(task.get("weight", 1.0))}


_DIR_WORDS = {
    "long": 1.0, "al": 1.0, "buy": 1.0, "bull": 1.0, "boğa": 1.0, "boga": 1.0,
    "short": -1.0, "sat": -1.0, "sell": -1.0, "bear": -1.0, "ayı": -1.0,
    "ayi": -1.0, "bekle": 0.0, "wait": 0.0, "notr": 0.0, "nötr": 0.0,
    "neutral": 0.0, "nötr-bekle": 0.0, "notr-bekle": 0.0, "flat": 0.0,
}


def _extract_direction(result: dict) -> float | None:
    """Sonuçtan yön skoru çıkar (varsa): -1..+1. Önce nihai KARAR/sayısal skor,
    sonra yön-etiketi alanları taranır (sıra önemlidir: KARAR kapıları içerir)."""
    if not isinstance(result, dict):
        return None
    # sayısal yön skoru öncelikli
    for key in ("yon_skoru", "direction", "score", "signal"):
        v = result.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    # nihai karar / yön etiketi (motorun kendi kapılarını yansıtır)
    for key in ("KARAR", "karar", "yon", "yon_bias", "bias", "stance"):
        v = result.get(key)
        if isinstance(v, str):
            w = v.strip().lower()
            if w in _DIR_WORDS:
                return _DIR_WORDS[w]
    return None


def run_swarm(plan: dict, repo_root: Path | None = None) -> dict:
    tasks = plan.get("tasks")
    if not tasks or not isinstance(tasks, list):
        raise SuruError("VERİ YOK: 'tasks' listesi gerekli")
    timeout = float(plan.get("timeout", 60))
    root = repo_root or Path(__file__).resolve().parent.parent
    max_workers = min(len(tasks), 8)
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_run_one, t, timeout, root): t for t in tasks}
        for fut in as_completed(futs):
            results.append(fut.result())
    # isim sırası korunsun
    order = {t.get("name", f"t{i}"): i for i, t in enumerate(tasks)}
    results.sort(key=lambda r: order.get(r["name"], 999))

    # güven-ağırlıklı yön birleşimi (yön skoru olanlar üzerinden)
    num, den, voters = 0.0, 0.0, []
    for r in results:
        if not r["ok"]:
            continue
        d = _extract_direction(r["result"])
        if d is None:
            continue
        w = r.get("weight", 1.0)
        num += w * d
        den += w
        voters.append({"name": r["name"], "direction": d, "weight": w})
    combined = (num / den) if den > 0 else None
    if combined is None:
        decision = "NÖTR-BEKLE (yön sinyali yok)"
    elif abs(combined) < 0.2:
        decision = "NÖTR-BEKLE (zayıf/çelişkili)"
    else:
        decision = "LONG eğilim" if combined > 0 else "SHORT eğilim"

    ok_n = sum(1 for r in results if r["ok"])
    return {"op": "suru", "task_count": len(tasks), "ok_count": ok_n,
            "failed": [r["name"] for r in results if not r["ok"]],
            "combined_direction": (round(combined, 4)
                                   if combined is not None else None),
            "voters": voters, "decision": decision, "results": results,
            "note": "yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Paralel alt-ajan sürüsü")
    ap.add_argument("--plan", required=True)
    args = ap.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    try:
        print(json.dumps(run_swarm(plan), ensure_ascii=False, indent=2))
    except SuruError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
