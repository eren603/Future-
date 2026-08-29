"""konsey CLI — audit / fetch / run / sinyal."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import EvidenceRegistry


def _kayit(yol: str) -> EvidenceRegistry:
    return EvidenceRegistry.load(yol)


def cmd_init(a) -> int:
    EvidenceRegistry().save(a.output)
    print(f"Olusturuldu: {a.output}")
    return 0


def cmd_fetch(a) -> int:
    reg = _kayit(a.input) if Path(a.input).exists() else EvidenceRegistry()
    try:
        reg.fetch(a.location, a.source_id, a.evidence_id, a.dependency_group)
    except Exception as e:  # noqa: BLE001
        print(f"ERISILEMEDI (kayit YAPILMADI): {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    reg.save(a.output)
    print(f"Eklendi: {a.source_id}/{a.evidence_id} -> {a.output}")
    return 0


def cmd_audit(a) -> int:
    reg = _kayit(a.input)
    r = reg.audit(a.requested_decision)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
    return 0 if r.decision == "PUBLISH_FULL" else 2


def cmd_run(a) -> int:
    """Saglayici ajanla kosu (README s.56-99). Ag + anahtar gerektirir."""
    from .adapters import OpenAICompatibleAdapter, GenericJSONAdapter
    from .orchestrator import run_agent_and_gate
    reg = _kayit(a.input)
    if a.provider == "openai-compatible":
        ad = OpenAICompatibleAdapter(a.base_url, a.api_key_env, a.model)
    elif a.provider == "generic-json":
        ad = GenericJSONAdapter(a.endpoint, a.api_key_env)
    else:
        print(f"bilinmeyen saglayici: {a.provider}", file=sys.stderr)
        return 2
    rapor = run_agent_and_gate(reg, ad)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(rapor, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps(rapor["independent_audit"], ensure_ascii=False, indent=2))
    return 0 if rapor["publish_allowed"] else 2


def cmd_sinyal(a) -> int:
    """Canli yon + giris/cikis. Ag kapaliysa yerel arsive duser ve BEYAN EDER."""
    from .kosu import kos
    rapor = kos([s.strip().upper() for s in a.symbols.split(",")], a.output)
    return 0 if rapor["publish_allowed"] else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="konsey", description="KONSEY evidence engine")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("init"); p.add_argument("--output", required=True); p.set_defaults(f=cmd_init)

    p = sp.add_parser("fetch")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--location", required=True); p.add_argument("--source-id", required=True)
    p.add_argument("--evidence-id", required=True); p.add_argument("--dependency-group", default="G0")
    p.set_defaults(f=cmd_fetch)

    p = sp.add_parser("audit")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--requested-decision", default="PUBLISH_FULL")
    p.set_defaults(f=cmd_audit)

    p = sp.add_parser("run")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--provider", default="openai-compatible")
    p.add_argument("--base-url", default="https://api.openai.com/v1")
    p.add_argument("--endpoint", default=""); p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY")
    p.set_defaults(f=cmd_run)

    p = sp.add_parser("sinyal", help="canli yon + giris/cikis seviyeleri")
    p.add_argument("--symbols", default="BTCUSDT")
    p.add_argument("--output", default="outputs/sinyal.json")
    p.set_defaults(f=cmd_sinyal)

    a = ap.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
