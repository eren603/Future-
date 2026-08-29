from __future__ import annotations

from typing import Any

from .adapters import AgentAdapter, build_prompt
from .core import EvidenceRegistry


DEFAULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["claims", "decision", "epistemic_verdict", "limitations"],
    "properties": {
        "claims": {"type": "array"},
        "decision": {"enum": ["PUBLISH_FULL", "PUBLISH_LIMITED", "REPAIR", "HALT"]},
        "epistemic_verdict": {"enum": ["KNOWN", "PARTIAL", "UNKNOWN"]},
        "limitations": {"type": "array"},
    },
    "additionalProperties": True,
}


def run_agent_and_gate(registry: EvidenceRegistry, adapter: AgentAdapter) -> dict[str, Any]:
    system, user = build_prompt(registry)
    response = adapter.complete(system, user, DEFAULT_SCHEMA)
    model_result = response.structured or {"text": response.text}

    # Never trust the model decision. The local registry is audited independently.
    audit = registry.audit("PUBLISH_FULL")
    return {
        "provider": response.provider,
        "model_output": model_result,
        "independent_audit": audit.to_dict(),
        "final_decision": audit.decision,
        "publish_allowed": audit.decision == "PUBLISH_FULL",
    }
