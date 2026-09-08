from __future__ import annotations

from typing import Literal, cast

from app.agent.providers.base import ProviderContext, ProviderEvidence
from app.agent.state import AgentState
from app.tools.hygiene import snapshot


def build_provider_context(
    state: AgentState,
    task: Literal["classification", "hypotheses", "assessment", "recommendation"],
) -> ProviderContext:
    evidence = [ProviderEvidence.model_validate(snapshot({
        "evidence_id": item.evidence_id,
        "source_type": item.source_type,
        "trust_level": item.trust_level,
        "observation_status": item.observation_status,
        "source": item.source,
        "title": item.title,
        "summary": item.summary,
        "content": item.content,
    })) for item in state.evidence_items[:50]]
    assessment = state.self_assessment.model_dump(mode="json") if state.self_assessment else None
    return ProviderContext(
        agent_run_id=str(state.agent_run_id),
        task=task,
        alert=cast(dict[str, object], snapshot(state.alert_summary.model_dump(mode="json") if state.alert_summary else {})),
        classification=cast(dict[str, object], snapshot(state.alert_classification)),
        untrusted_evidence=evidence,
        suspicious_observations=cast(list[dict[str, object]], snapshot(state.suspicious_items)),
        missing_evidence=cast(list[str], snapshot(state.missing_evidence)),
        missing_targets=cast(list[str], snapshot(state.missing_targets)),
        hypotheses=cast(list[dict[str, object]], snapshot([item.model_dump(mode="json") for item in state.hypotheses])),
        self_assessment=cast(dict[str, object] | None, snapshot(assessment)),
        blocked_action_definitions=cast(
            list[dict[str, object]], snapshot([item.model_dump(mode="json") for item in state.blocked_tools])
        ),
    )
