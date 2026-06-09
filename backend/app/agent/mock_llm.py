from __future__ import annotations

from typing import Any


def _normalize_text(*parts: str) -> str:
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


def classify_alert(alert: dict[str, Any]) -> dict[str, Any]:
    title = str(alert.get("title") or "")
    source = str(alert.get("source") or "")
    severity = str(alert.get("severity") or "info")
    infrastructure_type = str(alert.get("infrastructure_type") or "unknown")
    raw_data = alert.get("raw_data") or {}
    description = str(alert.get("description") or raw_data.get("description") or "")
    combined = _normalize_text(title, source, description, " ".join(alert.get("tags", [])))

    if any(keyword in combined for keyword in ("prompt-injection", "system override", "poisoned", "ignore policies")):
        return {
            "alert_type": "rag_prompt_injection",
            "severity": severity,
            "infrastructure_type": infrastructure_type,
            "urgency": "high",
            "confidence": 0.94,
            "risk_level": "critical",
            "classification_rationale": (
                "The alert references poisoned retrieved content and policy-override language, "
                "which matches a RAG prompt-injection scenario."
            ),
            "likely_root_cause": "Untrusted document poisoning or malicious retrieval content.",
            "query_hint": "prompt injection poisoned runbook system override ignore policies",
            "initial_missing_evidence": [
                "Blast radius of poisoned documents",
                "Whether related tool outputs were influenced by the same content",
            ],
        }

    if any(keyword in combined for keyword in ("xmrig", "crypto-mining", "mining", "gpu usage", "gpu-node", "outbound mining")):
        return {
            "alert_type": "suspicious_gpu_usage",
            "severity": severity,
            "infrastructure_type": infrastructure_type,
            "urgency": "high",
            "confidence": 0.91,
            "risk_level": "high",
            "classification_rationale": (
                "GPU-specific keywords, suspicious outbound traffic, and xmrig indicators point to possible "
                "GPU abuse or unauthorized crypto-mining."
            ),
            "likely_root_cause": "Unauthorized mining process or compromised training image.",
            "query_hint": "gpu abuse xmrig suspicious process mining pool outbound connections",
            "initial_missing_evidence": [
                "Confirmed job ownership on the affected node",
                "Whether the suspicious process belongs to an approved workload",
            ],
        }

    if any(keyword in combined for keyword in ("ssh", "failed password", "brute-force", "auth-log-monitor", "login attempts")):
        return {
            "alert_type": "ssh_bruteforce",
            "severity": severity,
            "infrastructure_type": infrastructure_type,
            "urgency": "high",
            "confidence": 0.88,
            "risk_level": "high",
            "classification_rationale": (
                "Repeated failed authentication attempts and SSH-specific indicators match an external brute-force pattern."
            ),
            "likely_root_cause": "Credential-stuffing or brute-force activity against exposed SSH endpoints.",
            "query_hint": "ssh brute force failed root admin login response runbook",
            "initial_missing_evidence": [
                "Whether any authentication attempts succeeded",
                "Whether MFA or credential rotation was triggered",
            ],
        }

    if any(keyword in combined for keyword in ("inode", "storage", "/scratch", "filesystem-monitor", "capacity")):
        return {
            "alert_type": "storage_inode_pressure",
            "severity": severity,
            "infrastructure_type": infrastructure_type,
            "urgency": "medium",
            "confidence": 0.86,
            "risk_level": "medium",
            "classification_rationale": (
                "The alert describes inode exhaustion and scratch-space pressure, which is consistent with storage capacity risk."
            ),
            "likely_root_cause": "Runaway cache or checkpoint file growth on shared storage.",
            "query_hint": "storage inode pressure scratch cleanup runbook",
            "initial_missing_evidence": [
                "Largest directories driving inode growth",
                "Whether cleanup automation already ran",
            ],
        }

    return {
        "alert_type": "unknown",
        "severity": severity,
        "infrastructure_type": infrastructure_type,
        "urgency": "medium",
        "confidence": 0.42,
        "risk_level": "medium",
        "classification_rationale": (
            "The alert does not cleanly match a known deterministic scenario, so the workflow should stay conservative."
        ),
        "likely_root_cause": "Unknown until additional evidence is collected.",
        "query_hint": f"{title} {description} {source}".strip(),
        "initial_missing_evidence": [
            "Relevant runbook or historical incident context",
            "Structured operational evidence from logs or metrics",
        ],
    }


def generate_hypotheses(
    alert: dict[str, Any],
    retrieved_context: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alert_type = str(alert.get("classification", {}).get("alert_type") or alert.get("alert_type") or "unknown")
    context_citations = [item.get("citation") for item in retrieved_context if item.get("citation")]
    tool_names = [item.get("tool_name") for item in tool_results if item.get("tool_name")]

    if alert_type == "suspicious_gpu_usage":
        return [
            {
                "title": "Unauthorized crypto-mining workload is consuming GPU resources",
                "summary": (
                    "The combination of xmrig indicators, outbound pool-like traffic, and high GPU utilization "
                    "suggests a compromised or unauthorized workload."
                ),
                "confidence": 0.74,
                "supporting_evidence": context_citations[:2] + [f"tool://{name}" for name in tool_names[:3]],
            },
            {
                "title": "The suspicious process may have entered through a compromised training image",
                "summary": (
                    "Job metadata and node telemetry are consistent with a container image or runtime compromise "
                    "rather than normal training behavior."
                ),
                "confidence": 0.61,
                "supporting_evidence": [f"tool://{name}" for name in tool_names[:3]],
            },
        ]

    if alert_type == "rag_prompt_injection":
        return [
            {
                "title": "Retrieved runbook content is attempting to replace safety policy",
                "summary": (
                    "The evidence points to deliberate prompt-injection text embedded in an untrusted runbook chunk."
                ),
                "confidence": 0.43,
                "supporting_evidence": context_citations[:2] + [f"tool://{name}" for name in tool_names[:2]],
            },
            {
                "title": "The poisoning may affect more than one document or ingestion path",
                "summary": (
                    "Suspicious retrieved content plus indexer-related log evidence suggests the issue may extend beyond a single chunk."
                ),
                "confidence": 0.34,
                "supporting_evidence": [f"tool://{name}" for name in tool_names[:2]],
            },
        ]

    if alert_type == "ssh_bruteforce":
        return [
            {
                "title": "The login node is under external brute-force pressure",
                "summary": (
                    "Repeated failures across privileged accounts suggest an automated credential attack rather than isolated user error."
                ),
                "confidence": 0.7,
                "supporting_evidence": context_citations[:1] + [f"tool://{name}" for name in tool_names[:2]],
            }
        ]

    if alert_type == "storage_inode_pressure":
        return [
            {
                "title": "Cache or checkpoint growth is exhausting inodes on shared scratch",
                "summary": (
                    "Storage evidence indicates a capacity problem driven by many small files rather than block-space exhaustion."
                ),
                "confidence": 0.68,
                "supporting_evidence": context_citations[:1] + [f"tool://{name}" for name in tool_names[:2]],
            }
        ]

    return [
        {
            "title": "Insufficient evidence for a strong deterministic hypothesis",
            "summary": (
                "The workflow found too little scenario-specific evidence to produce a confident explanation."
            ),
            "confidence": 0.28,
            "supporting_evidence": context_citations[:1],
        }
    ]


def assess_confidence(
    alert: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    suspicious_items: list[dict[str, Any]],
    missing_evidence: list[str],
) -> dict[str, Any]:
    classification = alert.get("classification") or {}
    alert_type = str(classification.get("alert_type") or "unknown")
    base_confidence = float(classification.get("confidence") or 0.45)
    evidence_bonus = min(0.18, len(evidence_items) * 0.035)
    suspicious_penalty = min(0.32, len(suspicious_items) * 0.07)
    missing_penalty = min(0.24, len(missing_evidence) * 0.04)
    confidence_score = max(0.12, min(0.92, base_confidence + evidence_bonus - suspicious_penalty - missing_penalty))
    risk_flags: list[str] = []

    if any(item.get("category") == "retrieved_context" and item.get("is_suspicious") for item in suspicious_items):
        risk_flags.append("suspicious_retrieved_context")
    if any(item.get("category") == "retrieved_context" and item.get("trust_level") != "trusted" for item in suspicious_items):
        risk_flags.append("untrusted_retrieved_context")
    if any(item.get("category") == "tool_output" and item.get("is_suspicious") for item in suspicious_items):
        risk_flags.append("suspicious_tool_output")
    if any(item.get("category") == "tool_output" and item.get("trust_level") != "trusted" for item in suspicious_items):
        risk_flags.append("untrusted_tool_output")
    if missing_evidence:
        risk_flags.append("missing_evidence")

    if alert_type == "rag_prompt_injection":
        confidence_score = min(confidence_score, 0.46)
        uncertainty_level = "high"
        decision = "stop_and_request_human_review"
    elif alert_type == "unknown":
        confidence_score = min(confidence_score, 0.4)
        uncertainty_level = "high"
        decision = "retrieve_more" if missing_evidence else "recommend_human_review"
    else:
        if confidence_score >= 0.75 and not risk_flags:
            uncertainty_level = "medium"
        elif confidence_score >= 0.55:
            uncertainty_level = "medium"
        else:
            uncertainty_level = "high"
        decision = "recommend_human_review" if confidence_score >= 0.45 else "retrieve_more"

    what_agent_knows = [item["summary"] for item in evidence_items[:4]]
    within_capability = alert_type != "unknown"
    rationale_parts = [
        f"Confidence is {confidence_score:.2f} based on {len(evidence_items)} evidence items.",
    ]
    if suspicious_items:
        rationale_parts.append("Some evidence is untrusted or suspicious, so the workflow remains conservative.")
    if missing_evidence:
        rationale_parts.append("Important gaps remain before any action could be justified.")
    if alert_type == "rag_prompt_injection":
        rationale_parts.append("Prompt-injection indicators require stopping at human review rather than trusting the retrieved content.")

    return {
        "capability_area": alert_type,
        "confidence_score": round(confidence_score, 2),
        "uncertainty_level": uncertainty_level,
        "what_agent_knows": what_agent_knows,
        "missing_evidence": missing_evidence,
        "within_capability": within_capability,
        "decision": decision,
        "rationale": " ".join(rationale_parts),
        "risk_flags": risk_flags,
        "overridden_by_policy": False,
    }


def generate_final_recommendation(state: dict[str, Any]) -> dict[str, Any]:
    classification = state.get("alert_classification") or {}
    self_assessment = state.get("self_assessment") or {}
    hypotheses = state.get("hypotheses") or []
    suspicious_items = state.get("suspicious_items") or []
    blocked_tools = state.get("blocked_tools") or []
    evidence_items = state.get("evidence_items") or []
    missing_evidence = state.get("missing_evidence") or []
    alert_summary = state.get("alert_summary") or {}
    alert_type = str(classification.get("alert_type") or "unknown")

    summary = (
        f"Review alert '{alert_summary.get('title', 'unknown alert')}' with a deterministic, evidence-grounded workflow."
    )
    notes: list[str] = []
    if suspicious_items:
        notes.append("Untrusted or suspicious context was observed and should not be treated as instructions.")
    if missing_evidence:
        notes.append("Evidence is incomplete, so the recommendation remains conservative.")
    if alert_type == "rag_prompt_injection":
        notes.append("Prompt-injection indicators were detected in retrieved or indexed content.")

    evidence = [
        {
            "summary": item.get("summary"),
            "citation": item.get("citation"),
            "trust_level": item.get("trust_level"),
            "suspicious": bool(item.get("suspicious")),
        }
        for item in evidence_items[:6]
    ]
    citations = [item.get("citation") for item in evidence_items if item.get("citation")][:8]
    hypothesis_titles = [item.get("title") for item in hypotheses if item.get("title")]

    if alert_type == "suspicious_gpu_usage":
        next_steps = [
            "Have a human operator validate the job owner and preserve process, job, and network evidence.",
            "Review whether the container image or workload was compromised before any containment action.",
            "Use the draft ticket to coordinate platform-security follow-up.",
        ]
    elif alert_type == "ssh_bruteforce":
        next_steps = [
            "Have a human reviewer confirm whether any authentication attempts succeeded.",
            "Validate whether temporary edge blocking and credential review are needed.",
            "Use historical incidents and the runbook to scope follow-up.",
        ]
    elif alert_type == "storage_inode_pressure":
        next_steps = [
            "Have an operator confirm the directories driving inode growth.",
            "Coordinate safe cleanup or quota changes through storage operations.",
            "Use the runbook guidance before any disruptive remediation.",
        ]
    elif alert_type == "rag_prompt_injection":
        next_steps = [
            "Quarantine or review the poisoned document path with a human reviewer.",
            "Check whether related documents or tool outputs were influenced by the same payload.",
            "Preserve citations and suspicious content markers for incident documentation.",
        ]
    else:
        next_steps = [
            "Collect additional logs, metrics, or historical context before acting.",
            "Escalate to a human reviewer because the deterministic workflow lacks enough evidence.",
        ]

    if hypothesis_titles:
        summary = f"{summary} Leading hypothesis: {hypothesis_titles[0]}."

    return {
        "summary": summary,
        "evidence": evidence,
        "citations": citations,
        "recommended_next_steps": next_steps,
        "blocked_actions_requiring_human_approval": [
            {
                "tool_name": item.get("tool_name"),
                "target": item.get("target"),
                "rationale": item.get("rationale"),
                "requires_human_approval": True,
            }
            for item in blocked_tools
        ],
        "uncertainty": str(self_assessment.get("uncertainty_level") or "medium"),
        "missing_evidence": missing_evidence,
        "notes": notes,
        "requires_human_approval": True,
        "ticket_draft_id": None,
    }
