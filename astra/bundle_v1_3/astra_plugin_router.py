"""ASTRA ROUTER 1.0: deterministic planning over host-verified observations.

No connection, installation, tool execution or permission change is performed.
The assistant/host executes the returned plan through actual platform tools.
Atlas text is discovery data, never live authority or an access credential.
"""
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Need:
    key: str
    topic: str
    capability: str
    provider: str | None = None
    account: str | None = None
    effect: str = "read"
    authorized: bool = False
    critical: bool = True


@dataclass(frozen=True)
class Provider:
    name: str
    kind: str  # native | skill | plugin
    verified_capabilities: frozenset[str] = frozenset()
    advertised_capabilities: frozenset[str] = frozenset()
    callable_names: frozenset[str] = frozenset()
    skill_package: str | None = None
    plugin_id: str | None = None
    installed: bool = False
    auth: str = "UNKNOWN"  # GRANTED | NOT_REQUIRED | REQUIRED | UNKNOWN
    state: str = "UNKNOWN"  # AVAILABLE | PENDING | POLICY_BLOCKED | UNAVAILABLE | UNKNOWN
    observed_session: str = ""
    evidence_id: str = ""
    account: str | None = None
    preference: int = 100  # atlas/user preference; not a quality or reliability score


def bound_to(need, provider):
    return ((need.provider is None or need.provider.casefold() == provider.name.casefold())
            and (need.account is None or need.account == provider.account))


def current(provider, session):
    return bool(provider.evidence_id) and provider.observed_session == session


def ready(provider, session, callables, skills):
    if not current(provider, session) or provider.state != "AVAILABLE":
        return False
    if provider.auth not in {"GRANTED", "NOT_REQUIRED"}:
        return False
    if provider.kind == "plugin" and not provider.installed:
        return False
    if provider.kind == "skill":
        return provider.skill_package is not None and provider.skill_package in skills
    return bool(provider.callable_names) and provider.callable_names.issubset(callables)


def plan_routes(needs, providers, *, session, available_callables=(), available_skills=(),
                declined=(), explicitly_reallowed=(), suggestion_already_used=False):
    """Prefer native coverage, then the smallest useful <=2 providers per topic.

    Connection suggestions require fresh catalogue metadata and exact plugin IDs.
    Side effects need separate authorization even when the provider is ready.
    """
    if not session or not needs or len(needs) > 256 or len(providers) > 512:
        raise ValueError("INVALID_PLAN_SIZE_OR_SESSION")
    if len({n.key for n in needs}) != len(needs) or len({p.name.casefold() for p in providers}) != len(providers):
        raise ValueError("DUPLICATE_NEED_OR_PROVIDER")
    if any(n.effect not in {"read", "local_compute", "external_write", "financial_trade", "permission_change"} for n in needs):
        raise ValueError("INVALID_EFFECT")
    if any(p.kind not in {"native", "skill", "plugin"} for p in providers):
        raise ValueError("INVALID_PROVIDER_KIND")
    excluded = {x.casefold() for x in declined} - {x.casefold() for x in explicitly_reallowed}
    candidates = [p for p in providers if p.name.casefold() not in excluded]
    live = [p for p in candidates if ready(p, session, set(available_callables), set(available_skills))]
    assignments, actions, gaps = {}, [], []
    ordered = sorted(live, key=lambda p: (p.preference, p.name.casefold()))
    for need in needs:
        native = [p for p in ordered if p.kind == "native" and bound_to(need, p)
                  and need.capability in p.verified_capabilities]
        if native:
            assignments[need.key] = native[0]
    topic_choices = {}
    for topic in sorted({n.topic for n in needs}):
        pending = [n for n in needs if n.topic == topic and n.key not in assignments]
        pool = [p for p in ordered if p.kind != "native" and any(
            bound_to(n, p) and n.capability in p.verified_capabilities for n in pending)]
        # Bound combinatorial work; callers should supply relevant providers only.
        if len(pool) > 64:
            raise ValueError("TOO_MANY_RELEVANT_PROVIDERS")
        best, best_key = (), None
        for count in range(min(2, len(pool)) + 1):
            for choice in combinations(pool, count):
                missing = [n for n in pending if not any(bound_to(n, p) and n.capability in p.verified_capabilities for p in choice)]
                key = (sum(n.critical for n in missing), len(missing), len(choice),
                       sum(p.preference for p in choice), tuple(p.name.casefold() for p in choice))
                if best_key is None or key < best_key:
                    best, best_key = choice, key
        topic_choices[topic] = [p.name for p in best]
        for need in pending:
            for provider in best:
                if bound_to(need, provider) and need.capability in provider.verified_capabilities:
                    assignments[need.key] = provider
                    break
    suggested = suggestion_already_used
    newly_pending = set()
    def improves_topic(new_provider, topic):
        topic_needs = [n for n in needs if n.topic == topic]
        baseline = {n.key for n in topic_needs if n.key in assignments}
        base_score = (sum(n.critical for n in topic_needs if n.key in baseline), len(baseline))
        native_keys = {n.key for n in topic_needs if n.key in assignments and assignments[n.key].kind == "native"}
        peers = [None] + [p for p in live if p.kind != "native" and p.name != new_provider.name]
        for peer in peers:
            covered = set(native_keys)
            for n in topic_needs:
                if bound_to(n, new_provider) and n.capability in (new_provider.verified_capabilities | new_provider.advertised_capabilities):
                    covered.add(n.key)
                if peer and bound_to(n, peer) and n.capability in peer.verified_capabilities:
                    covered.add(n.key)
            score = (sum(n.critical for n in topic_needs if n.key in covered), len(covered))
            if score > base_score:
                return True
        return False
    for need in needs:
        if need.provider is not None and need.provider.casefold() in excluded:
            actions.append({"need": need.key, "action": "RESPECT_DECLINE", "provider": need.provider})
            gaps.append({"need": need.key, "reason": "USER_DECLINED", "critical": need.critical})
            continue
        if need.key in assignments:
            provider = assignments[need.key]
            action = "READ_SKILL" if provider.kind == "skill" else "USE_NATIVE" if provider.kind == "native" else "USE_PLUGIN"
            if need.effect not in {"read", "local_compute"} and not need.authorized:
                action = "PREPARE_AUTHORIZATION"
            actions.append({"need": need.key, "action": action, "provider": provider.name,
                            "evidence_id": provider.evidence_id, "effect": need.effect})
            if action == "PREPARE_AUTHORIZATION":
                gaps.append({"need": need.key, "reason": "ACTION_NOT_AUTHORIZED", "critical": need.critical})
            continue
        prospective = [p for p in candidates if current(p, session) and bound_to(need, p)
                       and need.capability in (p.verified_capabilities | p.advertised_capabilities)]
        prospective.sort(key=lambda p: (p.state != "PENDING", p.preference, p.name.casefold()))
        provider = next((p for p in prospective if p.state == "PENDING" or p.name.casefold() in newly_pending), None)
        if provider:
            action = "WAIT_EXISTING_CONNECTION"
        else:
            provider = next((p for p in prospective if p.kind == "plugin" and p.installed
                             and p.state == "AVAILABLE" and p.auth == "REQUIRED"
                             and improves_topic(p, need.topic)), None)
            if provider:
                action = "NEEDS_ACCOUNT_CONNECTION"
            else:
                provider = next((p for p in prospective if p.kind == "plugin" and not p.installed
                                 and p.state == "AVAILABLE" and p.plugin_id and improves_topic(p, need.topic)), None)
                if provider:
                    action = "QUEUE_CONNECTION" if suggested else "SUGGEST_ONE_CONNECTION"
                    suggested = True
                elif any(p.state == "POLICY_BLOCKED" for p in prospective):
                    action = "REPORT_POLICY_BLOCK"
                else:
                    action = "DISCOVER_CAPABILITY"
        record = {"need": need.key, "action": action, "provider": provider.name if provider else None,
                  "capability": need.capability, "topic": need.topic}
        if provider and action == "SUGGEST_ONE_CONNECTION":
            record["plugin_id"] = provider.plugin_id
            newly_pending.add(provider.name.casefold())
        if action in {"SUGGEST_ONE_CONNECTION", "QUEUE_CONNECTION", "NEEDS_ACCOUNT_CONNECTION"}:
            record["replan_after_verified_connection"] = True
        actions.append(record)
        gaps.append({"need": need.key, "reason": action, "critical": need.critical})
    return {"router_version": "ASTRA-ROUTER-1.0", "executed": False,
            "status": "PLAN_READY" if not gaps else "PLAN_HAS_GAPS",
            "topic_providers": topic_choices, "actions": actions, "gaps": gaps,
            "new_suggestion_count": sum(a["action"] == "SUGGEST_ONE_CONNECTION" for a in actions)}


def atlas_candidates(atlas, topic_id):
    """Return snapshot data for discovery; never transform status into readiness."""
    return [dict(entry) for entry in atlas["entries"] if entry["topic"] == topic_id]
