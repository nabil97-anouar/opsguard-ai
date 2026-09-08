from __future__ import annotations

from time import perf_counter

from app.agent import deterministic_rules
from app.agent.providers.base import (
    LLMProvider,
    ProviderAssessment,
    ProviderCallResult,
    ProviderClassification,
    ProviderContext,
    ProviderHypotheses,
    ProviderIdentity,
    ProviderRecommendation,
    validate_evidence_references,
)

DETERMINISTIC_IMPLEMENTATION_VERSION = "deterministic-v3"


class DeterministicProvider(LLMProvider):
    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider="deterministic",
            model="local-rules-v3",
            mode="local",
            implementation_version=DETERMINISTIC_IMPLEMENTATION_VERSION,
        )

    def classify(self, context: ProviderContext) -> ProviderCallResult[ProviderClassification]:
        started = perf_counter()
        value = ProviderClassification.model_validate(deterministic_rules.classify_alert(context.alert))
        return ProviderCallResult(value=value, duration_ms=_elapsed(started))

    def hypothesize(self, context: ProviderContext) -> ProviderCallResult[ProviderHypotheses]:
        started = perf_counter()
        alert = {**context.alert, "classification": context.classification}
        raw = deterministic_rules.generate_hypotheses(alert, _legacy_evidence(context))
        value = ProviderHypotheses.model_validate({"hypotheses": raw})
        validate_evidence_references(context, hypotheses=value.hypotheses)
        return ProviderCallResult(value=value, duration_ms=_elapsed(started))

    def assess(self, context: ProviderContext) -> ProviderCallResult[ProviderAssessment]:
        started = perf_counter()
        alert = {**context.alert, "classification": context.classification}
        raw = deterministic_rules.assess_confidence(
            alert,
            _legacy_evidence(context),
            context.suspicious_observations,
            context.missing_evidence,
            missing_targets=context.missing_targets,
        )
        return ProviderCallResult(value=ProviderAssessment.model_validate(raw), duration_ms=_elapsed(started))

    def recommend(self, context: ProviderContext) -> ProviderCallResult[ProviderRecommendation]:
        started = perf_counter()
        legacy_state = {
            "alert_summary": context.alert,
            "alert_classification": context.classification,
            "evidence_items": _legacy_evidence(context),
            "suspicious_items": context.suspicious_observations,
            "missing_evidence": context.missing_evidence,
            "missing_targets": context.missing_targets,
            "hypotheses": context.hypotheses,
            "blocked_tools": context.blocked_action_definitions,
            "self_assessment": context.self_assessment or {},
        }
        raw = deterministic_rules.generate_final_recommendation(legacy_state)
        value = ProviderRecommendation(
            summary=raw["summary"],
            recommended_next_steps=raw["recommended_next_steps"],
            uncertainty=raw["uncertainty"],
            missing_evidence=raw["missing_evidence"],
            notes=raw["notes"],
            proposed_actions=[],
        )
        return ProviderCallResult(value=value, duration_ms=_elapsed(started))


def _legacy_evidence(context: ProviderContext) -> list[dict[str, object]]:
    return [
        {
            **item.model_dump(mode="json"),
            "kind": "tool_output" if item.source_type == "tool" else ("alert" if item.source_type == "alert" else "retrieval"),
            "citation": f"evidence://{item.evidence_id}",
        }
        for item in context.untrusted_evidence
    ]


def _elapsed(started: float) -> int:
    return max(0, int(round((perf_counter() - started) * 1000)))
