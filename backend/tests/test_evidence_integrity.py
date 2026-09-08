from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agent import nodes
from app.agent.actions import ProposedAction
from app.agent.providers.base import ProviderCallResult, ProviderHypotheses
from app.agent.providers.deterministic import DeterministicProvider
from app.agent.runner import create_agent_run, run_agent_for_alert
from app.agent.state import AgentState, EvidenceItem, PlannedToolCall
from app.db import session as db_session
from app.main import app
from app.models import AgentRun, AgentStep, Alert, Document, DocumentChunk, ToolCall
from app.services.demo_seed import demo_uuid, seed_demo_data
from app.tools import registry


@pytest.fixture
def engine(monkeypatch):
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    seed_demo_data(reset=True)
    yield engine
    engine.dispose()


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_status"),
    [
        ("get_node_metrics", {"node": "nonexistent-node"}, "failed"),
        ("drain_node", {"node": "explicit-node"}, "blocked"),
    ],
)
def test_unsuccessful_attempts_never_support_reasoning(engine, tool_name, arguments, expected_status) -> None:
    with Session(engine) as session:
        run = create_agent_run(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))
        state = AgentState(alert_id=run.alert_id, agent_run_id=run.id)
        state.planned_tools = [PlannedToolCall(tool_name=tool_name, input=arguments, rationale="Exercise outcome boundary")]

        nodes.execute_safe_tools(session, run, state)
        assert state.evidence_items == []
        assert state.executed_tools == []
        assert len(state.tool_results) == 1
        assert state.tool_results[0].status == expected_status
        assert state.missing_evidence == [f"Successful output from tool {tool_name}"]
        assert state.steps[0]["output_snapshot"]["evidence_items"] == []
        assert state.steps[0]["output_snapshot"]["executed_tools"] == []
        assert state.steps[0]["output_snapshot"]["tool_results"][0]["status"] == expected_status

        audit = session.get(ToolCall, state.tool_results[0].tool_call_id)
        assert audit is not None
        assert audit.agent_run_id == run.id
        assert audit.status == expected_status

        nodes.synthesize_hypotheses(session, run, state)
        assert len(state.hypotheses) == 1
        assert state.hypotheses[0].supporting_evidence == []
        assert state.hypotheses[0].title == "Insufficient observations to support an incident hypothesis"
        nodes.metacognitive_self_assessment(session, run, state)
        assert state.self_assessment.what_agent_knows == []
        nodes.generate_recommendation(session, run, state)
        assert state.final_recommendation.evidence == []
        assert state.final_recommendation.citations == []


def test_repeated_successful_calls_have_distinct_evidence_and_exact_output(engine) -> None:
    with Session(engine) as session:
        run = create_agent_run(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))
        state = AgentState(alert_id=run.alert_id, agent_run_id=run.id)
        state.planned_tools = [
            PlannedToolCall(tool_name="search_logs", input={"query": query, "limit": 2}, rationale="Collect observations")
            for query in ("xmrig", "ssh")
        ]
        nodes.execute_safe_tools(session, run, state)
        assert [item.status for item in state.tool_results] == ["succeeded", "succeeded"]
        assert len(state.evidence_items) == 2
        assert len({item.evidence_id for item in state.evidence_items}) == 2
        assert len({item.citation for item in state.evidence_items}) == 2
        for evidence, result in zip(state.evidence_items, state.tool_results, strict=True):
            assert evidence.source_type == "tool"
            assert evidence.source == "search_logs"
            assert evidence.tool_call_id == result.tool_call_id
            assert evidence.citation == f"tool://search_logs/{result.tool_call_id}"
            assert evidence.content == result.output
            assert evidence.observed_at == result.observed_at
            assert evidence.observed_at.tzinfo is not None
            audit = session.get(ToolCall, evidence.tool_call_id)
            assert audit.output == evidence.content
            assert audit.agent_run_id == run.id

        snapshot = deepcopy(state.evidence_items[0].content)
        state.tool_results[0].output["matches"] = []
        assert state.evidence_items[0].content == snapshot


def test_invalid_adapter_output_is_a_failed_attempt_without_evidence(engine, monkeypatch) -> None:
    get_tool = registry.get_tool
    definition = replace(get_tool("get_node_metrics"), handler=lambda *args: {})
    monkeypatch.setattr(registry, "get_tool", lambda name: definition if name == definition.name else get_tool(name))
    with Session(engine) as session:
        run = create_agent_run(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))
        state = AgentState(alert_id=run.alert_id, agent_run_id=run.id)
        state.planned_tools = [PlannedToolCall(
            tool_name="get_node_metrics", input={"node": "explicit-node"}, rationale="Verify output validation",
        )]
        nodes.execute_safe_tools(session, run, state)
        assert state.tool_results[0].status == "failed"
        assert state.tool_results[0].output == {}
        assert state.evidence_items == []
        assert state.missing_evidence == ["Successful output from tool get_node_metrics"]
        assert session.get(ToolCall, state.tool_results[0].tool_call_id).status == "failed"


def test_every_new_reference_resolves_to_the_complete_run_snapshot(engine) -> None:
    with Session(engine) as session:
        result = run_agent_for_alert(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))
        assert result.status == "waiting_for_human"
        evidence = [EvidenceItem.model_validate(item) for item in result.final_recommendation.evidence]
        assert len(evidence) > 6  # The old recommendation silently truncated these records.
        ids = {item.evidence_id for item in evidence}
        assert len(ids) == len(evidence)
        assert result.final_recommendation.citations == [item.citation for item in evidence]
        hypothesis_step = next(step for step in result.steps if step.node_name == "synthesize_hypotheses")
        for hypothesis in hypothesis_step.output_snapshot["hypotheses"]:
            assert set(hypothesis["supporting_evidence"]) <= ids
            assert all(not reference.startswith("tool://") for reference in hypothesis["supporting_evidence"])

        retrieval_step = next(step for step in result.steps if step.node_name == "retrieve_context")
        retrieved = {item["chunk_id"]: item for item in retrieval_step.output_snapshot["results"]}
        document_evidence = [item for item in evidence if item.kind == "retrieval"]
        assert document_evidence
        for item in document_evidence:
            stored = retrieved[str(item.chunk_id)]
            assert item.document_id == UUID(stored["document_id"])
            assert item.evidence_id == stored["evidence_id"]
            assert item.source == stored["source"]
            assert item.content == stored["content_excerpt"]
            assert item.retrieval_score == stored["score"]
            assert item.trust_level == stored["trust_level"]
            assert item.observed_at == datetime.fromisoformat(stored["observed_at"])


def test_document_edits_do_not_rewrite_historical_evidence(engine) -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/agent/runs", json={"alert_id": str(demo_uuid("alert:suspicious-gpu-usage"))})
        assert response.status_code == 200
        assert response.json()["status"] == "waiting_for_human"
        run_id = response.json()["agent_run_id"]
        before = client.get(f"/api/v1/agent/runs/{run_id}").json()
        old_evidence = deepcopy(before["final_recommendation"]["evidence"])
        document_evidence = [item for item in old_evidence if item["kind"] == "retrieval"]
        assert document_evidence
        with Session(engine) as session:
            for item in document_evidence:
                document = session.get(Document, UUID(item["document_id"]))
                chunk = session.get(DocumentChunk, UUID(item["chunk_id"]))
                document.title = "Changed after the investigation"
                document.file_path = "changed://source"
                document.trust_level = "quarantined"
                chunk.trust_level = "quarantined"
                chunk.content = "Entirely different content recorded later."
                session.add(document)
                session.add(chunk)
            session.commit()
        after = client.get(f"/api/v1/agent/runs/{run_id}")
        assert after.status_code == 200
        assert after.json()["final_recommendation"]["evidence"] == old_evidence
        assert after.json()["steps"] == before["steps"]


def test_historical_run_without_evidence_is_not_backfilled(engine, monkeypatch) -> None:
    with Session(engine) as session:
        run = create_agent_run(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))
        run.status = "waiting_for_human"
        session.add(run)
        session.commit()
        run_id = run.id

    def unexpected_retrieval(*args, **kwargs):
        pytest.fail("Reading history must not invoke retrieval")

    monkeypatch.setattr(nodes, "retrieve_chunks", unexpected_retrieval)
    monkeypatch.setattr("app.rag.retrieval.retrieve_chunks", unexpected_retrieval)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/agent/runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "waiting_for_human"
        assert payload["steps"] == []
        assert payload["tool_calls"] == []
        assert payload["final_recommendation"] is None


def test_missing_node_skips_targeted_tools_and_reduces_confidence(engine) -> None:
    with Session(engine) as session:
        fixture = session.get(Alert, demo_uuid("alert:suspicious-gpu-usage"))
        original = run_agent_for_alert(session, alert_id=fixture.id)
        assert original.status == "waiting_for_human"
        raw_data = {key: value for key, value in fixture.raw_data.items() if key not in {"node", "job_id"}}
        alert = Alert(
            title="Suspicious GPU usage requires investigation",
            source=fixture.source,
            severity=fixture.severity,
            infrastructure_type=fixture.infrastructure_type,
            raw_data=raw_data,
            tags=fixture.tags,
            status="new",
        )
        session.add(alert)
        session.commit()
        result = run_agent_for_alert(session, alert_id=alert.id)
        assert result.status == "waiting_for_human"
        calls = session.exec(select(ToolCall).where(ToolCall.agent_run_id == result.agent_run_id)).all()
        assert {call.tool_name for call in calls} == {"search_logs", "retrieve_runbook", "create_ticket_draft"}
        assert all("node" not in call.input_args for call in calls)
        assert result.final_recommendation.blocked_actions_requiring_human_approval == []
        assert "Alert does not identify a valid node; target-specific checks and actions were omitted." in result.self_assessment.missing_evidence
        assert result.self_assessment.confidence_score < original.self_assessment.confidence_score
        assert result.self_assessment.confidence_score == 0.4
        assert "missing_operational_target" in result.self_assessment.risk_flags


def test_unknown_hypothesis_reference_fails_validation(engine) -> None:
    class InvalidHypothesisProvider(DeterministicProvider):
        def hypothesize(self, _context):
            return ProviderCallResult(value=ProviderHypotheses(hypotheses=[{
                "title": "Unsupported", "summary": "Unsupported", "confidence": 0.9,
                "supporting_evidence": ["another-run:tool:missing"],
            }]), duration_ms=0)

    with Session(engine) as session:
        result = run_agent_for_alert(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"),
                                     provider=InvalidHypothesisProvider())
        assert result.status == "failed"
        assert result.error == "Hypothesis references evidence outside this run."
        assert result.final_recommendation is None
        run = session.get(AgentRun, result.agent_run_id)
        assert run.status == "failed"
        steps = session.exec(select(AgentStep).where(AgentStep.agent_run_id == run.id)).all()
        assert steps[-1].node_name == "synthesize_hypotheses"


def test_recommendation_cannot_reference_another_runs_evidence(engine) -> None:
    class InvalidRecommendationProvider(DeterministicProvider):
        def recommend(self, context):
            result = super().recommend(context)
            action = ProposedAction(action_type="investigate", target="gpu-node-14",
                supporting_evidence_ids=["another-run:tool:missing"], rationale="Unsupported reference.")
            return ProviderCallResult(value=result.value.model_copy(update={"proposed_actions": [action]}), duration_ms=0)

    with Session(engine) as session:
        result = run_agent_for_alert(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"),
                                     provider=InvalidRecommendationProvider())
        assert result.status == "failed"
        assert result.error == "Recommendation actions reference evidence outside this run."
        assert result.final_recommendation is None
        failed_step = result.steps[-1]
        assert failed_step.node_name == "generate_recommendation"
        assert failed_step.status == "failed"
        assert "final_recommendation" not in failed_step.output_snapshot
