#!/usr/bin/env python3
"""
KONSEY ALL-IN-ONE

Tek dosyalık, Manus API'den bağımsız kanıt kataloğu, web kaynak edinimi,
comparison-article iş akışı ve deterministik PUBLISH_FULL yayın kapısı.

Kullanım:
  python KONSEY_ALL_IN_ONE.py init --output task.json
  python KONSEY_ALL_IN_ONE.py fetch --input task.json --output task.json --location URL
  python KONSEY_ALL_IN_ONE.py audit --input task.json --output audit.json

Not: Bu program modelin muhakemesini garanti etmez. Modelin beyanını değil,
kanıt kayıtlarını ve yapısal koşulları denetler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SKILL_INSTRUCTIONS = r"""
KONSEY yöntemi: OWASP SAMM yönetim ve olgunluk omurgası; OWASP ASVS teknik
 güvenlik doğrulama standardı; PRISMA araştırma şeffaflığı; Cochrane metodolojik
 kalite ve yanlılık incelemesi; GRADE kanıt kesinliği ve sonuç dili kalibrasyonu;
 BIST/IOSCO kurumsal sorumluluk ve bağımsız güvence katmanıdır.

Üst kontroller: tekil kanıt kataloğu, sürümleme, karşıt kanıt ve yanlışlama,
bağımsız güvence, sürekli kontrol izleme, tedarik zinciri kontrolü ve epistemik
yayın kapısı.

Karşılaştırma makalesi: seçenekleri, okuyucuyu, hedef sorguyu, arama niyetini,
öncelikli kriterleri, fiyatı, SERP desenini, doğrulanmış gerçek tablosunu,
5-8 özellikli karşılaştırma tablosunu, kullanım senaryosu bazlı verdict'i,
pros/cons bölümlerini, SEO alanlarını ve görsel gereksinimlerini kaydet.

Manus API zorunlu değildir. Web, API, RSS, akademik veri tabanı, kurumsal
kaynak veya yerel dosya adaptörleri aynı Source/Evidence sözleşmesine bağlanır.
Erişilemeyen kaynak erişilmiş gibi gösterilmez. Modelin VERIFIED veya
PUBLISH_FULL demesi tek başına kanıt değildir.
"""

ALLOWED_STATUSES = {"VERIFIED", "REPORTED", "INFERRED", "LIMITED", "UNKNOWN"}
ALLOWED_DECISIONS = {"PUBLISH_FULL", "PUBLISH_LIMITED", "REPAIR", "HALT"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def plain_text(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def retrieve(location: str, timeout: int = 20) -> tuple[str, str, str]:
    if location.startswith(("http://", "https://")):
        req = Request(location, headers={"User-Agent": "konsey-all-in-one/1.0"})
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
        text = raw.decode("utf-8", errors="replace")
        if "html" in content_type.lower() or "<html" in text[:1000].lower():
            text = plain_text(text)
        return text, "URL erişimi", location
    path = Path(location)
    return path.read_text(encoding="utf-8"), "dosya", str(path)


def empty_task() -> dict:
    return {
        "task_id": f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "task_type": "COMPARISON_ARTICLE",
        "language": "tr",
        "risk_level": "STANDARD",
        "side_effect_level": "NONE",
        "method_layers_applied": [],
        "method_layers_omitted": [],
        "sources": {},
        "evidence": {},
        "claims": {},
        "contradictions": [],
        "external_checks_pending": [],
        "counter_evidence_search": "NOT_RUN",
        "decision": "REPAIR",
        "epistemic_verdict": "UNKNOWN",
        "comparison": {
            "options": [],
            "audience": "",
            "primary_query": "",
            "search_intent": "",
            "criteria_priority": ["pricing"],
            "serp_brief": "",
            "fact_table": {},
            "verdict": ""
        }
    }


def audit(task: dict) -> dict:
    sources = task.get("sources", {})
    evidence = task.get("evidence", {})
    claims = task.get("claims", {})
    critical = [c for c in claims.values() if c.get("critical", True)]
    missing = []
    invalid = []
    pending_counter = []
    reasons = []

    for claim in critical:
        cid = claim.get("claim_id", "UNKNOWN")
        status = claim.get("status")
        if status not in ALLOWED_STATUSES:
            invalid.append(f"{cid}: invalid status {status}")
        evidence_ids = claim.get("evidence_ids", [])
        if status == "VERIFIED" and not evidence_ids:
            missing.append(cid)
        for eid in evidence_ids:
            item = evidence.get(eid)
            if not item:
                invalid.append(f"{cid}->{eid}")
            elif item.get("source_id") not in sources:
                invalid.append(f"{eid}->{item.get('source_id')}")
        if claim.get("counter_evidence_status", "NOT_RUN") in {"NOT_RUN", "PENDING"}:
            pending_counter.append(cid)

    if missing:
        reasons.append("Kanıtsız VERIFIED kritik iddialar var.")
    if invalid:
        reasons.append("Geçersiz kanıt veya iddia referansı var.")
    if task.get("external_checks_pending"):
        reasons.append("Bekleyen dış kontroller var.")
    if task.get("contradictions"):
        reasons.append("Çözülmemiş çelişkiler var.")
    if task.get("risk_level") in {"HIGH", "CRITICAL"} and pending_counter:
        reasons.append("Yüksek riskli görevde karşıt kanıt araması tamamlanmamış.")

    supported = sum(
        1 for c in critical
        if c.get("evidence_ids") and c.get("claim_id") not in missing
    )
    if not critical:
        reasons.append("Kritik iddia kaydı bulunmuyor; yayın kararı verilemez.")
        decision = "REPAIR"
    elif missing or invalid or task.get("external_checks_pending"):
        decision = "HALT" if task.get("risk_level") == "CRITICAL" else "REPAIR"
    elif task.get("contradictions") or (task.get("risk_level") in {"HIGH", "CRITICAL"} and pending_counter):
        decision = "PUBLISH_LIMITED"
    elif supported == len(critical) and task.get("requested_decision", "PUBLISH_FULL") == "PUBLISH_FULL":
        decision = "PUBLISH_FULL"
    else:
        decision = "PUBLISH_LIMITED"

    freshness = "PASS"
    if not sources:
        freshness = "UNKNOWN"
        reasons.append("Kaynak bulunmuyor.")
    elif any(s.get("freshness", "UNKNOWN") in {"UNKNOWN", "STALE"} for s in sources.values()):
        freshness = "LIMITED"
        reasons.append("En az bir kaynağın güncelliği sınırlı veya bilinmiyor.")

    return {
        "critical_claim_count": len(critical),
        "critical_claims_with_evidence": supported,
        "missing_evidence_claims": missing,
        "invalid_references": invalid,
        "unresolved_contradictions": len(task.get("contradictions", [])),
        "open_external_checks_pending": len(task.get("external_checks_pending", [])),
        "counter_evidence_pending": pending_counter,
        "freshness": freshness,
        "decision": decision,
        "reasons": reasons,
        "audited_at": now(),
        "system_instruction_hash": digest(SKILL_INSTRUCTIONS),
    }


def write_json(path: str, value: dict) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> int:
    write_json(args.output, empty_task())
    print(f"Oluşturuldu: {args.output}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    task = json.loads(Path(args.input).read_text(encoding="utf-8"))
    text, method, location = retrieve(args.location, args.timeout)
    sid = args.source_id or f"S{len(task['sources']) + 1:02d}"
    eid = args.evidence_id or f"E{len(task['evidence']) + 1:02d}"
    task["sources"][sid] = {
        "source_id": sid,
        "url_or_location": location,
        "access_method": method,
        "accessed_at": now(),
        "freshness": "CURRENT",
        "dependency_group": args.dependency_group,
        "title": location,
        "content_hash": digest(text),
    }
    task["evidence"][eid] = {
        "evidence_id": eid,
        "source_id": sid,
        "locator": "retrieved-content",
        "evidence_type": "source",
        "excerpt": text[:args.max_chars],
        "limitations": "Pasif edinim; anlamsal doğrulama ayrıca yapılmalıdır."
    }
    write_json(args.output, task)
    print(json.dumps({"source_id": sid, "evidence_id": eid, "content_hash": digest(text)}, ensure_ascii=False, indent=2))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    task = json.loads(Path(args.input).read_text(encoding="utf-8"))
    task["requested_decision"] = args.requested_decision
    result = audit(task)
    write_json(args.output, {"task": task, "audit": result})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"] == "PUBLISH_FULL" else 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="KONSEY all-in-one independent evidence engine")
    sub = p.add_subparsers(required=True)
    init = sub.add_parser("init")
    init.add_argument("--output", required=True)
    init.set_defaults(func=cmd_init)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--input", required=True)
    fetch.add_argument("--output", required=True)
    fetch.add_argument("--location", required=True)
    fetch.add_argument("--source-id")
    fetch.add_argument("--evidence-id")
    fetch.add_argument("--dependency-group", default="G1")
    fetch.add_argument("--timeout", type=int, default=20)
    fetch.add_argument("--max-chars", type=int, default=12000)
    fetch.set_defaults(func=cmd_fetch)
    aud = sub.add_parser("audit")
    aud.add_argument("--input", required=True)
    aud.add_argument("--output", required=True)
    aud.add_argument("--requested-decision", default="PUBLISH_FULL")
    aud.set_defaults(func=cmd_audit)
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    raise SystemExit(args.func(args))
