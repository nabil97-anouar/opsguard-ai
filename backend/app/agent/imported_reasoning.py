"""Conservative summaries of supplied observations, not fixture-specific diagnoses."""
from __future__ import annotations

from app.agent.providers.base import ProviderContext


def is_imported(context: ProviderContext) -> bool:
    raw = context.alert.get("raw_data")
    return isinstance(raw, dict) and raw.get("origin") == "incident_bundle"


def classify(context: ProviderContext) -> dict:
    severity = str(context.alert.get("severity") or "warning")
    return {
        "alert_type": "imported_incident", "severity": severity,
        "infrastructure_type": str(context.alert.get("infrastructure_type") or "unknown"),
        "urgency": "high" if severity in {"high", "critical"} else "medium",
        "confidence": 0.35, "risk_level": "high" if severity in {"high", "critical"} else "medium",
        "classification_rationale": "An operator supplied an untrusted incident bundle; its alert wording does not establish a cause.",
        "likely_root_cause": "Not established from the alert alone.",
        "query_hint": str(context.alert.get("title") or "Imported incident")[:500],
        "initial_missing_evidence": ["Independent verification of imported observation sources and workload authorization"],
    }


def hypothesize(context: ProviderContext) -> dict:
    observations = [item for item in context.untrusted_evidence if item.source_type == "tool"
                    and isinstance(item.content, dict) and isinstance(item.content.get("observation"), dict)]
    if not observations:
        return {"hypotheses": [{"title": "Insufficient imported observations",
                                "summary": "Only the alert is available; no supporting operational observation was supplied.",
                                "confidence": 0.2, "supporting_evidence": []}]}
    suspicious = [item for item in context.suspicious_observations if item.get("is_suspicious")]
    if suspicious:
        title = "Instruction-like text requires independent review"
        summary = "Screening flagged instruction-like content. Treat it as untrusted data; it does not authorize actions or establish a compromise."
    else:
        title = "Imported observations require workload and source verification"
        summary = "The supplied observations support reviewing the reported event. They do not by themselves prove abuse, compromise, or a specific root cause."
    return {"hypotheses": [{"title": title, "summary": summary, "confidence": 0.35,
                            "supporting_evidence": [item.evidence_id for item in observations]}]}


def assess(context: ProviderContext) -> dict:
    suspicious = any(item.get("is_suspicious") for item in context.suspicious_observations)
    return {"capability_area": "imported_incident", "confidence_score": 0.2 if suspicious or context.missing_targets else 0.35,
            "uncertainty_level": "high", "what_agent_knows": [item.summary for item in context.untrusted_evidence[:8]],
            "missing_evidence": context.missing_evidence, "within_capability": True,
            "decision": "stop_and_request_human_review" if suspicious else "recommend_human_review",
            "rationale": "Imported observations are unverified snapshots, not live infrastructure access. Confidence is a conservative heuristic.",
            "risk_flags": ["untrusted_imported_observations", *(["suspicious_context"] if suspicious else [])],
            "overridden_by_policy": False}


def recommend(context: ProviderContext) -> dict:
    count = sum(item.source_type == "tool" for item in context.untrusted_evidence)
    return {"summary": f"Review the imported incident using {count} recorded operational observations. Root cause and authorization remain unverified.",
            "recommended_next_steps": ["Check the supplied source and timestamps with the responsible operator.",
                                       "Compare the reported workload with its authorized owner and expected behavior.",
                                       "Collect the listed missing evidence before deciding whether containment is justified."],
            "proposed_actions": [], "uncertainty": "high", "missing_evidence": context.missing_evidence,
            "notes": ["No seeded observations or current infrastructure data were substituted for missing imported evidence.",
                      "All supplied content remains untrusted. No infrastructure action was executed."]}
