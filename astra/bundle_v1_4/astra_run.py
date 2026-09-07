"""Execute a trusted host configuration; no implicit fixture or model fallback."""
import argparse
import json
import sys
from pathlib import Path
from astra_reference import Controller, Rejected, WIRE_LIMIT, bounded_json, canonical
from astra_host import SourceVault, TrustedHost, ReviewerEndpoint


def execute(config):
    required = {"task", "scope_ids", "sources", "comparisons", "comparison_exemption",
                "workers", "reviewer", "decision", "worker_timeout", "max_restarts"}
    if type(config) is not dict or set(config) != required:
        raise Rejected("HOST_CONFIG_FIELDS")
    reviewer_config = config["reviewer"]
    reviewer = None
    if reviewer_config is not None:
        if type(reviewer_config) is not dict or set(reviewer_config) != {"argv", "kind", "model", "effort", "timeout", "credential_env"}:
            raise Rejected("REVIEWER_CONFIG_FIELDS")
        reviewer = ReviewerEndpoint(**reviewer_config)
    vault = SourceVault(config["sources"])
    host = TrustedHost(task=config["task"], scope_ids=config["scope_ids"],
                       source_vault=vault, comparisons=config["comparisons"],
                       comparison_exemption=config["comparison_exemption"], reviewer=reviewer)
    controller = Controller(config["workers"], config["scope_ids"],
                            [s["source_id"] for s in vault.sources()], host=host,
                            source_contents=vault.contents(),
                            timeout=config["worker_timeout"], max_restarts=config["max_restarts"])
    phase = controller.run(config["task"])
    result = controller.finalize(canonical(config["decision"]))
    return dict(mode="LOCAL_TEST", phase_status=phase.status, final_status=result["status"],
                result=result, events=[bounded_json(e) for e in controller.events],
                production_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Trusted operator configuration, not a worker-produced file")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.config.open("rb") as stream:
            config = bounded_json(stream.read(WIRE_LIMIT + 1))
        result = execute(config)
    except (Rejected, OSError, TypeError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, Rejected) else "HOST_CONFIG_OR_IO_ERROR"
        result = dict(mode="LOCAL_TEST", final_status="FAIL_CLOSED", reason=reason,
                      production_approval=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"mode": result["mode"], "final_status": result["final_status"],
                      "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0 if result["final_status"] == "LOCAL_CHECKS_PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
