"""Regenerate verification/ from an actual run in this environment.

Nothing here is copied from a previous run: the test log, the result summary and
the four CLI scenarios are produced by really executing them now. Absolute paths
are masked so the artefacts stay reproducible across checkouts.
"""
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
VERIFICATION = BUNDLE / "verification"
CASES = ("valid", "method_mismatch", "semantic_rejection", "reviewer_missing")


def mask(text):
    return text.replace(str(BUNDLE), "<BUNDLE>")


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                           "-p", "test_*.py", "-v"], cwd=BUNDLE, capture_output=True, text=True)
    log = mask(done.stdout + done.stderr)
    (VERIFICATION / "test_run.txt").write_text(log, encoding="utf-8")
    last = [line for line in log.splitlines() if line.startswith("Ran ")]
    return dict(command="python3 -m unittest discover -s tests -p 'test_*.py' -v",
                returncode=done.returncode, summary=last[-1] if last else "UNKNOWN",
                outcome="OK" if done.returncode == 0 else "FAILED")


def run_cases():
    summary = {}
    for case in CASES:
        target = VERIFICATION / "cli_runs" / case
        with tempfile.TemporaryDirectory(prefix="astra-verify-") as workdir:
            folder = Path(workdir) / case
            demo = subprocess.run([sys.executable, str(BUNDLE / "demo_local.py"),
                                   "--case", case, "--output-dir", str(folder)],
                                  cwd=BUNDLE, capture_output=True, text=True)
            shutil.rmtree(target, ignore_errors=True)
            target.mkdir(parents=True, exist_ok=True)
            for produced in sorted(folder.glob("*")):
                text = mask(produced.read_text(encoding="utf-8")).replace(str(folder), "<RUN>")
                (target / produced.name).write_text(text, encoding="utf-8")
            result = json.loads((target / "result.json").read_text(encoding="utf-8"))
        summary[case] = dict(returncode=demo.returncode, final_status=result["final_status"],
                             reason=result.get("result", {}).get("reason"),
                             production_approval=result["production_approval"])
    return summary


def main():
    VERIFICATION.mkdir(exist_ok=True)
    tests = run_tests()
    cases = run_cases()
    stamp = datetime.now(timezone.utc).isoformat()
    (VERIFICATION / "test_result.json").write_text(json.dumps(dict(
        tests, python_version=platform.python_version(), platform=platform.system(),
        generated_at=stamp, scope="LOCAL_TEST only; no live provider call was made"),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (VERIFICATION / "cli_summary.json").write_text(json.dumps(dict(
        cases=cases, python_version=platform.python_version(), generated_at=stamp,
        scope="Local CLI scenarios with fixture workers and a fixture reviewer; "
              "they exercise the pipeline, not semantic quality"),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tests": tests["summary"], "outcome": tests["outcome"],
                      "cases": {k: v["final_status"] for k, v in cases.items()}},
                     ensure_ascii=False))
    return 0 if tests["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
