#!/usr/bin/env python3
"""Standart eval/benchmark harness — ölçülebilir, yayımlanabilir metrik.

Motor başına dağınık self_test yerine: tüm motorların öz-testlerini bulur, koşar,
geçti/kaldı + süreyi ölçer; ayrıca temsili işlerle gecikmeyi kaydeder. Çıktı hem
JSON hem de BENCHMARK.md (yayımlanabilir tablo). Uydurma yok: koşmayan motor
"FAIL" olarak raporlanır, gizlenmez.

Kullanım:
  python3 tools/benchmark.py                # tüm öz-testler + rapor yaz
  python3 tools/benchmark.py --json         # sadece JSON, dosya yazma
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / ".claude" / "skills"


def discover_self_tests() -> list[Path]:
    return sorted(SKILLS.glob("*/scripts/self_test.py"))


def run_self_test(path: Path, timeout: float = 120) -> dict:
    skill = path.parent.parent.name
    t0 = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, str(path)],
                              capture_output=True, text=True, timeout=timeout)
        dt = time.perf_counter() - t0
        ok = proc.returncode == 0 and "SELF_TEST_OK" in proc.stdout
        return {"skill": skill, "passed": ok, "seconds": round(dt, 4),
                "detail": ("OK" if ok else (proc.stderr or proc.stdout)[-200:])}
    except subprocess.TimeoutExpired:
        return {"skill": skill, "passed": False,
                "seconds": round(time.perf_counter() - t0, 4),
                "detail": "TIMEOUT"}


def bench_tools(timeout: float = 60) -> list[dict]:
    """tools/ altı için hafif çalıştırılabilirlik ölçümü."""
    out = []
    st = REPO / "tools" / "self_test.py"
    if st.exists():
        out.append(run_self_test_file(st, "tools", timeout))
    return out


def run_self_test_file(path: Path, label: str, timeout: float) -> dict:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, str(path)],
                              capture_output=True, text=True, timeout=timeout)
        dt = time.perf_counter() - t0
        ok = proc.returncode == 0 and "SELF_TEST_OK" in proc.stdout
        return {"skill": label, "passed": ok, "seconds": round(dt, 4),
                "detail": ("OK" if ok else (proc.stderr or proc.stdout)[-200:])}
    except subprocess.TimeoutExpired:
        return {"skill": label, "passed": False,
                "seconds": round(time.perf_counter() - t0, 4), "detail": "TIMEOUT"}


def run_benchmark() -> dict:
    rows = [run_self_test(p) for p in discover_self_tests()]
    rows += bench_tools()
    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    total_sec = round(sum(r["seconds"] for r in rows), 4)
    return {"suite": "future-engines", "engine_count": total,
            "passed": passed, "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "total_seconds": total_sec, "rows": rows}


def to_markdown(res: dict) -> str:
    lines = ["# Motor Benchmark — Future-", "",
             f"- Motor sayısı: **{res['engine_count']}**",
             f"- Geçen: **{res['passed']}** / Kalan: **{res['failed']}**",
             f"- Başarı oranı: **{res['pass_rate']*100:.1f}%**",
             f"- Toplam süre: **{res['total_seconds']} sn**", "",
             "| Motor | Sonuç | Süre (sn) | Not |",
             "|-------|-------|-----------|-----|"]
    for r in sorted(res["rows"], key=lambda x: x["skill"]):
        mark = "✅ PASS" if r["passed"] else "❌ FAIL"
        note = r["detail"].replace("\n", " ")[:60]
        lines.append(f"| {r['skill']} | {mark} | {r['seconds']} | {note} |")
    lines += ["", "> Öz-test = bilinen-değer doğrulaması. FAIL gizlenmez.",
              "> Metodoloji: her motorun scripts/self_test.py'si alt-süreçte "
              "koşulur; SELF_TEST_OK + çıkış kodu 0 aranır."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Motor benchmark harness")
    ap.add_argument("--json", action="store_true", help="sadece JSON, dosya yazma")
    args = ap.parse_args()
    res = run_benchmark()
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["failed"] == 0 else 1
    out = REPO / "BENCHMARK.md"
    out.write_text(to_markdown(res), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "rows"},
                     ensure_ascii=False, indent=2))
    print(f"\nRapor yazıldı: {out}")
    return 0 if res["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
