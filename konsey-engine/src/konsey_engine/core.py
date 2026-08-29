"""KONSEY cekirdek: kanit katalogu + deterministik yayin kapisi.

Sozlesme (KONSEY_Evidence_Engine.md):
  - Modelin kendi VERIFIED / PUBLISH_FULL beyani KANIT DEGILDIR.
  - PUBLISH_FULL yalnizca su dordu birden saglandiginda verilir:
      1) her kritik iddianin cozulebilir kanit referansi var
      2) bekleyen dis kontrol yok
      3) kaynak referanslari cozulebilir
      4) yayin kapisi basarili
  - Erisilemeyen kaynak ERISILMIS gibi kaydedilmez.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ALLOWED_STATUSES = {"VERIFIED", "REPORTED", "INFERRED", "LIMITED", "UNKNOWN"}
ALLOWED_DECISIONS = {"PUBLISH_FULL", "PUBLISH_LIMITED", "REPAIR", "HALT"}
FRESHNESS = {"CURRENT", "LIMITED", "STALE", "UNKNOWN"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def plain_text(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Source:
    source_id: str
    location: str
    access_method: str
    accessed_at: str
    freshness: str = "UNKNOWN"
    dependency_group: str = "G0"
    digest: str = ""
    note: str = ""


@dataclass
class Evidence:
    evidence_id: str
    source_id: str
    method: str
    accessed_at: str
    description: str = ""
    observed: str = ""
    exit_code: int | None = None


@dataclass
class Claim:
    claim_id: str
    statement: str
    status: str = "UNKNOWN"
    evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_status: str = "NOT_RUN"
    critical: bool = True
    note: str = ""


@dataclass
class AuditResult:
    critical_claim_count: int
    critical_claims_with_evidence: int
    missing_evidence_claims: list[str]
    invalid_references: list[str]
    unresolved_contradictions: int
    open_external_checks_pending: int
    counter_evidence_pending: list[str]
    freshness: str
    decision: str
    reasons: list[str]
    audited_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceRegistry:
    """Kaynak / kanit / iddia katalogu + kapi. Erisilemeyen kaynak KAYDEDILMEZ."""

    def __init__(self, task_id: str | None = None, task_type: str = "MARKET_SIGNAL",
                 risk_level: str = "HIGH", side_effect_level: str = "NONE") -> None:
        self.task_id = task_id or f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self.task_type = task_type
        self.risk_level = risk_level
        self.side_effect_level = side_effect_level
        self.language = "tr"
        self.sources: dict[str, Source] = {}
        self.evidence: dict[str, Evidence] = {}
        self.claims: dict[str, Claim] = {}
        self.contradictions: list[str] = []
        self.external_checks_pending: list[str] = []
        self.counter_evidence_search = "NOT_RUN"
        self.method_layers_applied: list[str] = []
        self.method_layers_omitted: list[str] = []
        self.payload: dict[str, Any] = {}

    # ---------------------------------------------------------------- kaynak
    def add_source(self, source_id: str, location: str, access_method: str,
                   freshness: str = "UNKNOWN", dependency_group: str = "G0",
                   content: str = "", note: str = "") -> Source:
        if freshness not in FRESHNESS:
            raise ValueError(f"gecersiz freshness: {freshness}")
        s = Source(source_id, location, access_method, now(), freshness,
                   dependency_group, digest(content) if content else "", note)
        self.sources[source_id] = s
        return s

    def add_evidence(self, evidence_id: str, source_id: str, method: str,
                     description: str = "", observed: str = "",
                     exit_code: int | None = None) -> Evidence:
        if source_id not in self.sources:
            raise KeyError(f"kanit cozulemeyen kaynaga baglandi: {source_id}")
        e = Evidence(evidence_id, source_id, method, now(), description,
                     observed[:6000], exit_code)
        self.evidence[evidence_id] = e
        return e

    def add_claim(self, claim_id: str, statement: str, status: str,
                  evidence_ids: list[str] | None = None,
                  counter_evidence_status: str = "NOT_RUN",
                  critical: bool = True, note: str = "") -> Claim:
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"gecersiz status: {status}")
        c = Claim(claim_id, statement, status, list(evidence_ids or []),
                  counter_evidence_status, critical, note)
        self.claims[claim_id] = c
        return c

    def fetch(self, location: str, source_id: str, evidence_id: str,
              dependency_group: str = "G0", timeout: int = 20) -> Evidence:
        """Pasif edinim. ERISILEMEZSE kayit YAPILMAZ - istisna firlatir."""
        if location.startswith(("http://", "https://")):
            req = Request(location, headers={"User-Agent": "konsey-engine/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace")
            if "html" in ctype.lower() or "<html" in text[:1000].lower():
                text = plain_text(text)
            yontem = "URL erisimi"
        else:
            text = Path(location).read_text(encoding="utf-8")
            yontem = "dosya"
        self.add_source(source_id, location, yontem, "CURRENT", dependency_group, text)
        return self.add_evidence(evidence_id, source_id, yontem,
                                 f"{location} icerigi", text[:2000])

    # ------------------------------------------------------------------ kapi
    def audit(self, requested_decision: str = "PUBLISH_FULL") -> AuditResult:
        if requested_decision not in ALLOWED_DECISIONS:
            raise ValueError(f"gecersiz karar: {requested_decision}")
        critical = [c for c in self.claims.values() if c.critical]
        missing, invalid, pending_counter, reasons = [], [], [], []

        for c in critical:
            if c.status not in ALLOWED_STATUSES:
                invalid.append(f"{c.claim_id}: invalid status {c.status}")
            if c.status == "VERIFIED" and not c.evidence_ids:
                missing.append(c.claim_id)
            for eid in c.evidence_ids:
                item = self.evidence.get(eid)
                if not item:
                    invalid.append(f"{c.claim_id}->{eid}")
                elif item.source_id not in self.sources:
                    invalid.append(f"{eid}->{item.source_id}")
            if c.counter_evidence_status in {"NOT_RUN", "PENDING"}:
                pending_counter.append(c.claim_id)

        if missing:
            reasons.append("Kanitsiz VERIFIED kritik iddialar var.")
        if invalid:
            reasons.append("Gecersiz kanit veya iddia referansi var.")
        if self.external_checks_pending:
            reasons.append("Bekleyen dis kontroller var.")
        if self.contradictions:
            reasons.append("Cozulmemis celiskiler var.")
        if self.risk_level in {"HIGH", "CRITICAL"} and pending_counter:
            reasons.append("Yuksek riskli gorevde karsit kanit aramasi tamamlanmamis.")

        supported = sum(1 for c in critical if c.evidence_ids and c.claim_id not in missing)
        if not critical:
            reasons.append("Kritik iddia kaydi bulunmuyor; yayin karari verilemez.")
            decision = "REPAIR"
        elif missing or invalid or self.external_checks_pending:
            decision = "HALT" if self.risk_level == "CRITICAL" else "REPAIR"
        elif self.contradictions or (self.risk_level in {"HIGH", "CRITICAL"} and pending_counter):
            decision = "PUBLISH_LIMITED"
        elif supported == len(critical) and requested_decision == "PUBLISH_FULL":
            decision = "PUBLISH_FULL"
        else:
            decision = "PUBLISH_LIMITED"

        freshness = "PASS"
        if not self.sources:
            freshness = "UNKNOWN"
            reasons.append("Kaynak bulunmuyor.")
        elif any(s.freshness in {"UNKNOWN", "STALE"} for s in self.sources.values()):
            freshness = "LIMITED"
            reasons.append("En az bir kaynagin guncelligi sinirli veya bilinmiyor.")

        return AuditResult(len(critical), supported, missing, invalid,
                           len(self.contradictions), len(self.external_checks_pending),
                           pending_counter, freshness, decision, reasons, now())

    # ------------------------------------------------------------------ seri
    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id, "task_type": self.task_type,
            "language": self.language, "risk_level": self.risk_level,
            "side_effect_level": self.side_effect_level,
            "method_layers_applied": self.method_layers_applied,
            "method_layers_omitted": self.method_layers_omitted,
            "sources": {k: asdict(v) for k, v in self.sources.items()},
            "evidence": {k: asdict(v) for k, v in self.evidence.items()},
            "claims": {k: asdict(v) for k, v in self.claims.items()},
            "contradictions": self.contradictions,
            "external_checks_pending": self.external_checks_pending,
            "counter_evidence_search": self.counter_evidence_search,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvidenceRegistry":
        r = cls(d.get("task_id"), d.get("task_type", "MARKET_SIGNAL"),
                d.get("risk_level", "HIGH"), d.get("side_effect_level", "NONE"))
        r.sources = {k: Source(**v) for k, v in (d.get("sources") or {}).items()}
        r.evidence = {k: Evidence(**v) for k, v in (d.get("evidence") or {}).items()}
        r.claims = {k: Claim(**v) for k, v in (d.get("claims") or {}).items()}
        r.contradictions = list(d.get("contradictions") or [])
        r.external_checks_pending = list(d.get("external_checks_pending") or [])
        r.counter_evidence_search = d.get("counter_evidence_search", "NOT_RUN")
        r.method_layers_applied = list(d.get("method_layers_applied") or [])
        r.method_layers_omitted = list(d.get("method_layers_omitted") or [])
        r.payload = dict(d.get("payload") or {})
        return r

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "EvidenceRegistry":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
