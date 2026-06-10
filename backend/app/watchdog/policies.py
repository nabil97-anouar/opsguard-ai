from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.rag.injection import detect_prompt_injection
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
NODE_PATTERN = re.compile(r"\b[a-z]+-node-\d+\b")
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


def dangerous_action_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    combined_text = " ".join(_text_fragments(payload))
    matched = [label for phrase, label in DANGEROUS_ACTION_PATTERNS if phrase in combined_text]
    blocked_actions = payload.final_recommendation.get("blocked_actions_requiring_human_approval", []) if payload.final_recommendation else []

    if not matched and not blocked_actions:
        return []

    evidence_refs = [f"recommendation://{action.get('tool_name')}" for action in blocked_actions if action.get("tool_name")]
    if not evidence_refs:
        evidence_refs = [f"keyword://{value}" for value in matched]

    status = "block" if any(item in {"delete", "shutdown"} for item in matched) else "require_human_approval"
    severity = PolicySeverity.CRITICAL if status == "block" else PolicySeverity.HIGH
    return [
        WatchdogFinding(
            policy_id="dangerous_action_policy",
            title="Dangerous infrastructure action detected",
            severity=severity,
            status=status,
            reason=(
                "The recommendation references dangerous or disruptive infrastructure actions that must never be executed autonomously."
            ),
            evidence_refs=evidence_refs,
            remediation=(
                "Keep the action recommendation-only, require explicit human approval, and do not execute it in the agent workflow."
            ),
            metadata={"matched_actions": sorted(set(matched))},
        )
    ]


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
            title="Recommendation has weak evidence grounding",
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


def bulk_operation_policy(payload: WatchdogInput) -> list[WatchdogFinding]:
    combined_text = " ".join(_text_fragments(payload))
    matched_patterns = [pattern for pattern in BULK_OPERATION_PATTERNS if pattern in combined_text]
    node_matches = sorted(set(NODE_PATTERN.findall(combined_text)))
    job_matches = sorted(set(JOB_PATTERN.findall(combined_text)))
    user_matches = sorted(set(USER_PATTERN.findall(combined_text)))

    if not matched_patterns and len(node_matches) <= 3 and len(job_matches) <= 3 and len(user_matches) <= 3:
        return []

    status = "block" if matched_patterns or len(node_matches) > 5 or len(user_matches) > 5 else "require_human_approval"
    severity = PolicySeverity.CRITICAL if status == "block" else PolicySeverity.HIGH
    evidence_refs = [f"keyword://{pattern}" for pattern in matched_patterns]
    evidence_refs.extend(f"node://{node}" for node in node_matches)
    evidence_refs.extend(f"job://{job}" for job in job_matches)
    evidence_refs.extend(f"user://{user}" for user in user_matches)

    return [
        WatchdogFinding(
            policy_id="bulk_operation_policy",
            title="Bulk or wide-scope action detected",
            severity=severity,
            status=status,
            reason=(
                "The workflow references cluster-wide or multi-target actions that are too broad for automatic handling."
            ),
            evidence_refs=evidence_refs,
            remediation=(
                "Reduce the scope to a single, well-supported target or require explicit human approval for the broader action."
            ),
            metadata={
                "matched_patterns": matched_patterns,
                "node_targets": node_matches,
                "job_targets": job_matches,
                "user_targets": user_matches,
            },
        )
    ]


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
