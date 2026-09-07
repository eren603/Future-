"""Create a named synthetic example and run the actual CLI host entry point."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("demo_output"))
    parser.add_argument("--case", choices=["valid", "method_mismatch", "semantic_rejection", "reviewer_missing"], default="valid")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    folder = args.output_dir.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    now = datetime.now(timezone.utc)
    rows, sources = [], []
    context = dict(metric="latency", definition="median completion latency", unit="ms",
                   period="same fixed synthetic window", population="same synthetic queries",
                   method="same median harness")
    for i, value in enumerate(("100", "120")):
        quote = f"Candidate {('A', 'B')[i]}: median completion latency {value} ms. Synthetic data."
        if args.case == "semantic_rejection":
            quote = f"Request count {value} requests. Latency was not measured. Synthetic data."
        path = folder / f"source_{i}.txt"
        path.write_text(quote, encoding="utf-8")
        rows.append(dict(context, entity=("A", "B")[i], source_id=f"s{i}", quote=quote, value=value))
        sources.append(dict(source_id=f"s{i}", path=str(path), kind="TOOL",
            as_of=(now-timedelta(seconds=1)).isoformat(), valid_until=(now+timedelta(hours=1)).isoformat()))
    if args.case == "method_mismatch":
        rows[1]["method"] = "p95"
    reviewer_mode = "reject" if args.case == "semantic_rejection" else "pass"
    reviewer = dict(argv=[sys.executable, str(root/"tests/semantic_reviewer_fixture.py"), reviewer_mode],
                    kind="TEST_FIXTURE", model="fixture-model", effort="fixture-effort", timeout=2.0, credential_env=[])
    if args.case == "reviewer_missing":
        reviewer = None
    claims = ["a:c1", "b:c1", "c:c1"]
    config = dict(task="Compare A and B using observed median latency in the same fixed test.",
        scope_ids=["comparison"], sources=sources,
        comparisons=[dict(requirement_id="latency", scope_id="comparison", claim_ids=claims,
                          direction="lower_is_better", rows=rows)], comparison_exemption=None,
        workers={wid: dict(role=role, argv=[sys.executable, str(root/"tests/research_worker_fixture.py")])
                 for wid, role in zip(("a", "b", "c"), ("model", "counterexample", "evidence"))},
        reviewer=reviewer, worker_timeout=2.0, max_restarts=0,
        decision=dict(action="Report the observed latency comparison only.", owner="demo_operator",
                      guard_metric="Valid comparable source measurements", kill_rule="Stop when a gate fails",
                      user_cost="Local synthetic demo", residual_risk="No live model or production isolation",
                      claim_ids=claims))
    config_path = folder/"config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2)+"\n")
    result = subprocess.run([sys.executable, str(root/"astra_run.py"), str(config_path),
                             "--output", str(folder/"result.json")], timeout=30)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
