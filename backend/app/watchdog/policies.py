from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable

from app.rag.injection import detect_prompt_injection
from app.agent.actions import normalize_intent, ProposedAction
from app.watchdog.schemas import PolicySeverity, WatchdogFinding, WatchdogInput

PolicyHandler = Callable[[WatchdogInput], list[WatchdogFinding]]

DANGEROUS_ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("cancel_job", "cancel_job"),
    ("drain_node", "drain_node"),
    ("block_user", "block_user"),
    ("isolate_node", "isolate_node"),
    ("disable_service", "disable_service"),
    ("delete", "delete"),
    ("kill process", "kill process"),
    ("revoke access", "revoke access"),
    ("shutdown", "shutdown"),
    ("quarantine node", "quarantine node"),
)
BULK_OPERATION_PATTERNS = (
    "all nodes",
    "all users",
    "all jobs",
    "entire cluster",
    "whole cluster",
    "bulk",
    "every node",
    "every user",
    "cluster-wide",
    "wildcard",
)
NODE_PATTERN = re.compile(r"\b[a-z]+[-\s]+node[-\s]+\d+\b")
JOB_PATTERN = re.compile(r"\bjob[-\s]?\d+\b")
USER_PATTERN = re.compile(r"\buser[:\s-]*[a-z0-9_.-]+\b")


@dataclass(frozen=True)
class WatchdogPolicyDefinition:
    policy_id: str
    title: str
    description: str
    handler: PolicyHandler


def _normalized_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str).lower()


def _text_fragments(payload: WatchdogInput) -> list[str]:
    fragments: list[str] = []
    if payload.final_recommendation is not None:
        recommendation = payload.final_recommendation
        fragments.extend(
            [
                str(recommendation.get("summary") or ""),
                " ".join(str(item) for item in recommendation.get("recommended_next_steps", [])),
                " ".join(str(item) for item in recommendation.get("notes", [])),
            ]
        )
        for action in recommendation.get("blocked_actions_requiring_human_approval", []):
            fragments.append(_normalized_json(action))

    for hypothesis in payload.hypotheses:
        fragments.append(str(hypothesis.get("summary") or ""))
        fragments.append(str(hypothesis.get("title") or ""))

    for tool_result in payload.tool_results:
        fragments.append(_normalized_json(tool_result.get("output", {})))

    for item in payload.retrieved_context:
        fragments.append(str(item.get("content_excerpt") or ""))

    for tool in payload.blocked_tools:
        fragments.append(_normalized_json(tool))

    for tool in payload.planned_tools:
        fragments.append(_normalized_json(tool))

    return [fragment for fragment in fragments if fragment]


def _severity_sort_value(severity: PolicySeverity) -> int:
    return {
        PolicySeverity.CRITICAL: 0,
        PolicySeverity.HIGH: 1,
        PolicySeverity.WARNING: 2,
        PolicySeverity.INFO: 3,
    }[severity]


def _proposal_fragments(payload: WatchdogInput) -> list[str]:
    """Only proposal fields: observations/hypotheses never establish action intent."""
    recommendation = payload.final_recommendation or {}
    summary = str(recommendation.get("summary", ""))
    values = [*recommendation.get("recommended_next_steps", [])]
    if _intent_bearing(summary):
        values.append(summary)
    values.extend(_normalized_json(action) for action in recommendation.get("blocked_actions_requiring_human_approval", []))
    values.extend(_normalized_json(item) for item in payload.blocked_tools + payload.planned_tools)
    return [normalize_intent(str(value)) for value in values]


def _intent_bearing(text: str) -> bool:
    normalized = normalize_intent(text)
    # Deterministic fallback for proposal language. Observation summaries such as
    # "logs mention DELETE" remain observations; this is not semantic analysis.
    return bool(re.search(r"\b(?:execute|recommend|perform|run|should|must)\b", normalized)) or any(
        normalized.startswith(normalize_intent(phrase)) for phrase, _ in DANGEROUS_ACTION_PATTERNS
    )


def _action_text(action: ProposedAction) -> str:
    return normalize_intent(_normalized_json({"action_type": action.action_type.value,
        "parameters": action.parameters, "target": action.target,
        "rationale": action.rationale if _intent_bearing(action.rationale) else ""}))


def _dangerous_matches(text: str) -> list[str]:
    tokens = " " + normalize_intent(text) + " "
    return [label for phrase, label in DANGEROUS_ACTION_PATTERNS
            if " " + normalize_intent(phrase) + " " in tokens
            or " " + normalize_intent(phrase).replace(" ", "") + " " in tokens
            or re.search(r"\b" + r"\s*".join(normalize_intent(phrase).replace(" ", "")) + r"\b", tokens)]


def dangerous_action_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    actions = [action for action in payload.proposed_actions if _dangerous_matches(_action_text(action))]
    matched = sorted({match for text in _proposal_fragments(payload) + [_action_text(action) for action in actions]
                      for match in _dangerous_matches(text)})
    if not matched:
        review_actions = [action for action in payload.proposed_actions if action.requires_approval]
        if not review_actions:
            return []
        return [WatchdogFinding(policy_id="dangerous_action_policy", title="Proposed action requires human review",
            severity=PolicySeverity.HIGH, status="require_human_approval",
            affected_action_ids=[action.action_id for action in review_actions],
            reason="The structured proposal explicitly requires approval; no approval/resume capability exists.",
            remediation="Keep the proposal pending human review; do not infer authorization from this verdict.")]
    return [WatchdogFinding(
        policy_id="dangerous_action_policy", title="Disruptive proposed action",
        severity=PolicySeverity.CRITICAL, status="block",
        affected_action_ids=[action.action_id for action in actions],
        reason="A proposed action contains disruptive intent. Autonomous execution is forbidden.",
        evidence_refs=[f"recommendation://{match}" for match in matched],
        remediation="Preserve the blocked proposal for human inspection; do not execute it.",
        metadata={"matched_actions": matched},
    )]


def prompt_injection_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    suspicious_context = [
        item for item in payload.retrieved_context if item.get("is_suspicious") or item.get("matched_patterns")
    ]
    suspicious_tools = [
        item
        for item in payload.tool_results
        if item.get("is_suspicious") or item.get("injection_scan_result") == "flagged"
    ]
    combined_text = " ".join(_text_fragments(payload))
    text_scan = detect_prompt_injection(combined_text) if combined_text else {"is_suspicious": False, "matched_patterns": [], "risk_level": "low"}

    if not suspicious_context and not suspicious_tools and not text_scan["is_suspicious"]:
        return []

    evidence_refs = [
        item.get("citation") or f"retrieval://{item.get('title', 'unknown')}"
        for item in suspicious_context
    ]
    evidence_refs.extend(f"tool://{item.get('tool_name')}" for item in suspicious_tools if item.get("tool_name"))
    if not evidence_refs:
        evidence_refs = [f"pattern://{pattern}" for pattern in text_scan["matched_patterns"]]

    matched_patterns = list(text_scan["matched_patterns"])
    for item in suspicious_context:
        matched_patterns.extend(item.get("matched_patterns", []))
    for item in suspicious_tools:
        matched_patterns.extend(item.get("matched_patterns", []))

    highest_risk = "high" if text_scan["risk_level"] == "high" or suspicious_context or suspicious_tools else "medium"
    status = "block" if highest_risk == "high" else "require_human_approval"
    severity = PolicySeverity.CRITICAL if status == "block" else PolicySeverity.HIGH
    return [
        WatchdogFinding(
            policy_id="prompt_injection_policy",
            title="Prompt-injection indicators detected",
            severity=severity,
            status=status,
            reason=(
                "Suspicious retrieved content, suspicious tool output, or explicit prompt-injection markers were detected."
            ),
            evidence_refs=sorted(set(reference for reference in evidence_refs if reference)),
            remediation=(
                "Treat the affected content as untrusted, keep the run gated for human review, and do not follow embedded instructions."
            ),
            metadata={"matched_patterns": sorted(set(pattern for pattern in matched_patterns if pattern))},
        )
    ]


def untrusted_context_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    untrusted_context = [item for item in payload.retrieved_context if item.get("trust_level") != "trusted"]
    untrusted_tools = [item for item in payload.tool_results if item.get("trust_level") != "trusted"]
    untrusted_evidence = [
        item
        for item in (payload.final_recommendation or {}).get("evidence", [])
        if item.get("trust_level") != "trusted" or item.get("suspicious")
    ]

    if not untrusted_context and not untrusted_tools and not untrusted_evidence:
        return []

    evidence_refs = [
        item.get("citation") or f"retrieval://{item.get('title', 'unknown')}"
        for item in untrusted_context
    ]
    evidence_refs.extend(f"tool://{item.get('tool_name')}" for item in untrusted_tools if item.get("tool_name"))
    evidence_refs.extend(item.get("citation") for item in untrusted_evidence if item.get("citation"))

    return [
        WatchdogFinding(
            policy_id="untrusted_context_policy",
            title="Untrusted context influenced the workflow",
            severity=PolicySeverity.HIGH,
            status="require_human_approval",
            reason=(
                "The workflow relied on untrusted retrieved context or tool output, so the result must stay behind human approval."
            ),
            evidence_refs=sorted(set(reference for reference in evidence_refs if reference)),
            remediation=(
                "Cross-check the recommendation against trusted evidence before acting, and explicitly call out the untrusted sources."
            ),
            metadata={
                "untrusted_retrieval_count": len(untrusted_context),
                "untrusted_tool_count": len(untrusted_tools),
            },
        )
    ]


def low_confidence_high_severity_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    alert = payload.alert
    severity = str(alert.get("severity") or alert.get("alert_summary", {}).get("severity") or "").lower()
    self_assessment = payload.self_assessment or {}
    confidence = float(self_assessment.get("confidence_score") or 0.0)

    if severity not in {"high", "critical"} or confidence >= 0.65:
        return []

    return [
        WatchdogFinding(
            policy_id="low_confidence_high_severity_policy",
            title="High-severity alert has low confidence",
            severity=PolicySeverity.HIGH if severity == "high" else PolicySeverity.CRITICAL,
            status="require_human_approval",
            reason=(
                f"The alert severity is {severity}, but the self-assessed confidence is only {confidence:.2f}."
            ),
            evidence_refs=["self_assessment://latest"],
            remediation=(
                "Escalate to human review and gather more evidence before approving any impactful response."
            ),
            metadata={"severity": severity, "confidence_score": round(confidence, 2)},
        )
    ]


def weak_grounding_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    alert = payload.alert
    severity = str(alert.get("severity") or alert.get("alert_summary", {}).get("severity") or "").lower()
    recommendation = payload.final_recommendation or {}
    citations = [citation for citation in recommendation.get("citations", []) if citation]
    evidence = recommendation.get("evidence", [])
    missing_evidence = list((payload.self_assessment or {}).get("missing_evidence", []))
    unsupported_hypotheses = [item.get("title") or "untitled_hypothesis" for item in payload.hypotheses if not item.get("supporting_evidence")]

    reasons: list[str] = []
    evidence_refs: list[str] = []
    if not citations or not evidence:
        reasons.append("The final recommendation is missing supporting evidence or citations.")
    if unsupported_hypotheses:
        reasons.append("At least one hypothesis does not reference supporting evidence.")
        evidence_refs.extend(f"hypothesis://{title}" for title in unsupported_hypotheses)
    if severity == "critical" and missing_evidence:
        reasons.append("Critical incident handling still has unresolved evidence gaps.")
        evidence_refs.extend(f"missing://{item}" for item in missing_evidence)

    if not reasons:
        return []

    status = "require_human_approval" if severity == "critical" or not citations else "warning"
    severity_value = PolicySeverity.HIGH if status == "require_human_approval" else PolicySeverity.WARNING
    if citations:
        evidence_refs.extend(citations)

    return [
        WatchdogFinding(
            policy_id="weak_grounding_policy",
            title="Recommendation has missing supporting references",
            severity=severity_value,
            status=status,
            reason=" ".join(reasons),
            evidence_refs=sorted(set(reference for reference in evidence_refs if reference)),
            remediation=(
                "Tighten the recommendation with explicit citations, or keep it as a human-review-only draft until grounding improves."
            ),
            metadata={
                "citation_count": len(citations),
                "unsupported_hypothesis_count": len(unsupported_hypotheses),
                "missing_evidence_count": len(missing_evidence),
            },
        )
    ]


def broad_scope(value: Any, key: str = "") -> bool:
    """Inspect typed scope parameters recursively; normalization includes punctuation."""
    normalized_key = normalize_intent(key).replace(" ", "")
    target_keys = {"target", "targets", "node", "nodes", "user", "users", "job", "jobs", "selector", "selectors", "scope"}
    count_keys = {"targetcount", "nodecount", "jobcount", "usercount"}
    all_keys = {"all", "allnodes", "alljobs", "allusers", "bulk", "wildcard", "matchall"}
    if isinstance(value, dict):
        if normalized_key in {"selector", "selectors"} and (not value or {normalize_intent(str(name)) for name in value} - {"id", "node", "job", "user", "name"}):
            return True
        return any(broad_scope(item, str(name)) for name, item in value.items())
    if isinstance(value, list):
        return (normalized_key in target_keys and len(value) > 1) or any(broad_scope(item, key) for item in value)
    if isinstance(value, bool):
        return value and normalized_key in all_keys
    if isinstance(value, (int, float)):
        return normalized_key in count_keys and value > 1
    if isinstance(value, str):
        value = unicodedata.normalize("NFKC", value)
        if normalized_key in all_keys and normalize_intent(value) in {"true", "yes", "1"}:
            return True
        if normalized_key in {"selector", "selectors"} and not re.fullmatch(r"(?:id|node|job|user|name)\s*[:=]\s*[a-zA-Z0-9_.-]+", value.strip(), re.I):
            return True
        if normalized_key in target_keys and (len([part for part in re.split(r"[,;]", value) if part.strip()]) > 1 or len(set(NODE_PATTERN.findall(value.lower()))) > 1):
            return True
        if normalized_key in count_keys:
            try:
                return float(value.strip()) > 1
            except ValueError:
                return True  # Unparseable declared counts cannot establish bounded scope.
        text = normalize_intent(value)
        compact = text.replace(" ", "")
        return (any(char in value for char in "*?") and normalized_key in target_keys) or any(
            re.search(r"\b" + re.escape(normalize_intent(pattern)) + r"\b", text) or normalize_intent(pattern).replace(" ", "") == compact
            for pattern in BULK_OPERATION_PATTERNS
        ) or (normalized_key in target_keys and text in {"all", "any", "everything"})
    return False


def bulk_operation_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    actions = [action for action in payload.proposed_actions if broad_scope(action.parameters)
               or broad_scope(action.target, "target") or (_intent_bearing(action.rationale) and broad_scope(action.rationale))]
    prose = " ".join(_proposal_fragments(payload))
    matched = [pattern for pattern in BULK_OPERATION_PATTERNS if re.search(r"\b" + re.escape(normalize_intent(pattern)) + r"\b", prose)]
    targets = set(NODE_PATTERN.findall(prose) + JOB_PATTERN.findall(prose) + USER_PATTERN.findall(prose))
    if not actions and not matched and len(targets) <= 1:
        return []
    return [WatchdogFinding(policy_id="bulk_operation_policy", title="Broad proposed action scope",
        severity=PolicySeverity.CRITICAL, status="block",
        affected_action_ids=[action.action_id for action in actions],
        reason="The proposed operation selects multiple targets, an unbounded selector, or all-target scope.",
        evidence_refs=[f"action://{action.action_id}" for action in actions],
        remediation="Reduce the proposal to one explicit target and re-evaluate it.",
        metadata={"matched_patterns": matched, "targets": sorted(targets)},
    )]


def grounding_reference_integrity_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    """Structural resolution only. The caller must supply the authoritative source ledger."""
    ledger = {item.get("evidence_id"): item for item in payload.evidence_items if item.get("evidence_id")}
    run_id = str(payload.agent_run_id) if payload.agent_run_id else None
    tool_observations = {str(item.get("tool_call_id")): item for item in payload.tool_results if item.get("tool_call_id")}

    def valid(reference):
        item = ledger.get(reference)
        if not item or run_id is None or str(item.get("agent_run_id")) != run_id:
            return False
        if item.get("trust_level") not in {"trusted", "untrusted"}:
            return False
        if item.get("kind") == "tool_output":
            observation = tool_observations.get(str(item.get("tool_call_id")))
            return item.get("observation_status") == "succeeded" and observation is not None and observation.get("status") in {"succeeded", "executed"}
        return item.get("observation_status") == "valid"

    affected = []
    failures = []
    for action in payload.proposed_actions:
        refs = action.supporting_evidence_ids
        if not refs or not all(valid(ref) for ref in refs):
            affected.append(action.action_id)
            failures.append(f"action://{action.action_id}")
    for index, hypothesis in enumerate(payload.hypotheses):
        refs = hypothesis.get("supporting_evidence", [])
        if not refs or not all(valid(ref) for ref in refs):
            failures.append(f"hypothesis://{index}")
    recommendation = payload.final_recommendation or {}
    for item in recommendation.get("evidence", []):
        if not valid(item.get("evidence_id")) or item != ledger.get(item.get("evidence_id")):
            failures.append("recommendation://evidence_snapshot")
    known_citations = {item.get("citation") for key, item in ledger.items() if valid(key)}
    if any(ref not in known_citations for ref in recommendation.get("citations", [])):
        failures.append("recommendation://citation")
    if recommendation.get("summary") and not recommendation.get("evidence"):
        failures.append("recommendation://missing_support")
    if not failures:
        return []
    return [WatchdogFinding(policy_id="grounding_reference_integrity", title="Evidence reference integrity failed",
        severity=PolicySeverity.HIGH, status="block", affected_action_ids=affected,
        reason="Support is absent, unresolved, cross-run, invalid, failed/blocked, quarantined, or differs from its source snapshot.",
        evidence_refs=sorted(set(failures)), remediation="Use successful same-run source observations; this check does not establish semantic entailment.")]


def unsafe_tool_output_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    suspicious_tools = []
    for tool_result in payload.tool_results:
        scan = detect_prompt_injection(_normalized_json(tool_result.get("output", {})))
        if tool_result.get("is_suspicious") or tool_result.get("matched_patterns") or scan["is_suspicious"]:
            suspicious_tools.append(
                {
                    "tool_name": tool_result.get("tool_name"),
                    "matched_patterns": sorted(set(list(tool_result.get("matched_patterns", [])) + list(scan["matched_patterns"]))),
                    "risk_level": tool_result.get("risk_level") or scan["risk_level"],
                }
            )

    if not suspicious_tools:
        return []

    evidence_refs = [f"tool://{item['tool_name']}" for item in suspicious_tools if item.get("tool_name")]
    matched_patterns = [
        pattern
        for item in suspicious_tools
        for pattern in item.get("matched_patterns", [])
    ]
    return [
        WatchdogFinding(
            policy_id="unsafe_tool_output_policy",
            title="Suspicious tool output detected",
            severity=PolicySeverity.HIGH,
            status="require_human_approval",
            reason=(
                "At least one tool output contains suspicious or directive-style content that should not directly drive decisions."
            ),
            evidence_refs=evidence_refs,
            remediation=(
                "Treat the tool output as untrusted, preserve it as evidence, and require human review before acting on it."
            ),
            metadata={"matched_patterns": sorted(set(pattern for pattern in matched_patterns if pattern))},
        )
    ]


POLICY_DEFINITIONS: tuple[WatchdogPolicyDefinition, ...] = (
    WatchdogPolicyDefinition(policy_id="grounding_reference_integrity", title="Evidence reference integrity",
        description="Checks same-run references to valid source observations, not semantic entailment.",
        handler=grounding_reference_integrity_policy),
    WatchdogPolicyDefinition(
        policy_id="dangerous_action_policy",
        title="Dangerous action gate",
        description="Flags dangerous infrastructure actions and keeps them behind human approval.",
        handler=dangerous_action_policy,
    ),
    WatchdogPolicyDefinition(
        policy_id="prompt_injection_policy",
        title="Prompt-injection gate",
        description="Flags suspicious retrieved context, matched prompt-injection patterns, and explicit override text.",
        handler=prompt_injection_policy,
    ),
    WatchdogPolicyDefinition(
        policy_id="untrusted_context_policy",
        title="Untrusted context gate",
        description="Requires human approval when untrusted retrieved or tool-derived context influences the result.",
        handler=untrusted_context_policy,
    ),
    WatchdogPolicyDefinition(
        policy_id="low_confidence_high_severity_policy",
        title="Low-confidence high-severity gate",
        description="Flags high-severity incidents when the self-assessed confidence is too low.",
        handler=low_confidence_high_severity_policy,
    ),
    WatchdogPolicyDefinition(
        policy_id="weak_grounding_policy",
        title="Weak grounding gate",
        description="Flags unsupported conclusions, missing citations, and critical evidence gaps.",
        handler=weak_grounding_policy,
    ),
    WatchdogPolicyDefinition(
        policy_id="bulk_operation_policy",
        title="Bulk operation gate",
        description="Flags cluster-wide, multi-target, or wildcard-style actions.",
        handler=bulk_operation_policy,
    ),
    WatchdogPolicyDefinition(
        policy_id="unsafe_tool_output_policy",
        title="Unsafe tool output gate",
        description="Flags suspicious tool outputs or directive-style tool content.",
        handler=unsafe_tool_output_policy,
    ),
)


def list_policy_definitions() -> list[WatchdogPolicyDefinition]:
    return list(POLICY_DEFINITIONS)


def iter_policy_handlers() -> list[WatchdogPolicyDefinition]:
    return list(POLICY_DEFINITIONS)
