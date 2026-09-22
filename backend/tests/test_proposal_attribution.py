from __future__ import annotations

from copy import deepcopy
from uuid import UUID

import pytest
from sqlmodel import Session, select

from app.agent.actions import ActionType, ProposedAction
from app.agent.providers.base import ProviderCallResult
from app.agent.providers.deterministic import DeterministicProvider
from app.agent.runner import get_agent_run_detail, run_agent_for_alert
from app.core.versions import POLICY_VERSION
from app.db import session as db_session
from app.harness.fixtures import base_watchdog_input
from app.models import AgentRun, AgentStep, TicketDraft, ToolCall
from app.services.demo_seed import demo_uuid, seed_demo_data
from app.watchdog import evaluate_watchdog
from app.watchdog.policies import bulk_operation_policy, dangerous_action_policy


BLOCKED_DEFINITIONS = [
    {"tool_name": "drain_node", "target": "all nodes", "rationale": "This operation is prohibited."},
    {"tool_name": "cancel_job", "target": "job-884231", "rationale": "Only a human may consider this."},
]


@pytest.fixture
def engine(monkeypatch):
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    seed_demo_data(reset=True)
    yield engine
    engine.dispose()


def payload_with_definitions():
    payload = base_watchdog_input()
    payload.blocked_tools = deepcopy(BLOCKED_DEFINITIONS)
    payload.final_recommendation["blocked_actions_requiring_human_approval"] = deepcopy(BLOCKED_DEFINITIONS)
    return payload


def test_prohibited_definitions_do_not_establish_disruptive_or_bulk_intent():
    payload = payload_with_definitions()
    assert dangerous_action_policy(payload) == []
    assert bulk_operation_policy(payload) == []
    decision = evaluate_watchdog(payload)
    assert decision.status.value == "allow"
    assert decision.findings == []
    assert decision.policy_version == "watchdog-policy-v4"


def test_review_action_remains_review_required_without_false_destructive_verdict():
    payload = payload_with_definitions()
    payload.proposed_actions = [ProposedAction(
        action_id="review-1", action_type="review_evidence", target="job-884231",
        supporting_evidence_ids=["EVIDENCE-1"], rationale="Review the observations.",
        requires_approval=True,
    )]
    decision = evaluate_watchdog(payload)
    assert decision.status.value == "require_human_approval"
    assert decision.blocking is False
    assert len(decision.findings) == 1
    assert decision.findings[0].affected_action_ids == ["review-1"]
    assert decision.findings[0].metadata == {}


@pytest.mark.parametrize("field", ["summary", "recommended_next_steps"])
def test_explicit_narrative_intent_is_not_hidden_by_blocked_definitions(field):
    payload = payload_with_definitions()
    text = "Execute drain_node on all nodes immediately."
    payload.final_recommendation[field] = text if field == "summary" else [text]
    danger = dangerous_action_policy(payload)
    bulk = bulk_operation_policy(payload)
    assert len(danger) == 1
    assert danger[0].blocking is True
    assert danger[0].metadata["matched_actions"] == ["drain_node"]
    assert len(bulk) == 1
    assert bulk[0].blocking is True


def test_structured_proposal_is_not_hidden_by_matching_blocked_definition():
    payload = payload_with_definitions()
    payload.proposed_actions = [ProposedAction(
        action_id="unsafe-1", action_type="drain_node", target="all nodes",
        rationale="Contain the workload.", requires_approval=False,
        supporting_evidence_ids=["EVIDENCE-1"],
    )]
    decision = evaluate_watchdog(payload)
    assert decision.status.value == "block"
    assert {item.policy_id for item in decision.findings} == {"dangerous_action_policy", "bulk_operation_policy"}
    assert all(item.affected_action_ids == ["unsafe-1"] for item in decision.findings)


def test_imperative_summary_is_checked_without_relying_on_blocked_definitions():
    payload = base_watchdog_input()
    payload.final_recommendation["summary"] = "Drain all nodes, cancel_job, and block_user immediately."
    assert payload.blocked_tools == []
    assert payload.final_recommendation["blocked_actions_requiring_human_approval"] == []
    findings = dangerous_action_policy(payload)
    assert len(findings) == 1
    assert findings[0].blocking is True
    assert findings[0].metadata["matched_actions"] == ["block_user", "cancel_job"]
    assert bulk_operation_policy(payload)[0].blocking is True


@pytest.mark.parametrize("name,target", [("drain_node", "all nodes"), ("cancel_job", "job-884231")])
def test_actual_planned_request_still_blocks_even_when_also_prohibited(name, target):
    payload = payload_with_definitions()
    payload.planned_tools = [{"tool_name": name, "input": {"target": target}, "rationale": "Requested action"}]
    findings = dangerous_action_policy(payload)
    assert len(findings) == 1
    assert findings[0].blocking is True
    assert findings[0].metadata["matched_actions"] == [name]
    if target == "all nodes":
        assert bulk_operation_policy(payload)[0].blocking is True


def test_deterministic_recommendation_does_not_invent_containment_actions(engine):
    with Session(engine) as session:
        result = run_agent_for_alert(
            session, alert_id=demo_uuid("alert:suspicious-gpu-usage"), provider=DeterministicProvider(),
        )
        final = result.final_recommendation
        assert result.status == "waiting_for_human"
        assert final is not None
        assert {item["tool_name"] for item in final.blocked_actions_requiring_human_approval} == {"cancel_job", "isolate_node"}
        assert len(final.proposed_actions) == len(final.recommended_next_steps)
        assert {item.action_type for item in final.proposed_actions} == {ActionType.REVIEW_EVIDENCE}
        assert final.watchdog_status == "require_human_approval"
        assert final.lifecycle_state.value == "pending_human_review"
        assert final.requires_human_approval is True
        assert final.review_valid is True
        assert not any(item["blocking"] for item in final.watchdog_findings)
        assert final.policy_version == POLICY_VERSION == "watchdog-policy-v4"

        candidate = session.exec(select(AgentStep).where(
            AgentStep.agent_run_id == result.agent_run_id,
            AgentStep.node_name == "generate_recommendation",
        )).one().output_snapshot
        assert candidate["lifecycle_state"] == "candidate"
        assert candidate["review_valid"] is False
        assert candidate["policy_version"] is None
        assert {item["action_type"] for item in candidate["proposed_actions"]} == {"review_evidence"}
        ticket = session.get(TicketDraft, UUID(final.ticket_draft_id))
        assert ticket.lifecycle_state == "pending_human_review"
        assert ticket.policy_version == "watchdog-policy-v4"
        calls = session.exec(select(ToolCall).where(ToolCall.agent_run_id == result.agent_run_id)).all()
        assert not {item.tool_name for item in calls} & {"cancel_job", "isolate_node", "drain_node"}


def test_actual_provider_destructive_action_remains_blocked_end_to_end(engine):
    class UnsafeProvider(DeterministicProvider):
        def recommend(self, context):
            result = super().recommend(context)
            value = result.value.model_copy(update={"proposed_actions": [ProposedAction(
                action_id="provider-unsafe", action_type="cancel_job", target="job-884231",
                supporting_evidence_ids=sorted(context.available_evidence_ids),
                rationale="Contain the workload.", requires_approval=False,
            )]})
            return ProviderCallResult(value=value, duration_ms=result.duration_ms)

    with Session(engine) as session:
        result = run_agent_for_alert(
            session, alert_id=demo_uuid("alert:suspicious-gpu-usage"), provider=UnsafeProvider(),
        )
        final = result.final_recommendation
        assert result.status == "waiting_for_human"
        assert final.watchdog_status == "block"
        assert final.lifecycle_state.value == "blocked"
        assert final.review_valid is False
        assert final.requires_human_approval is True
        finding = next(item for item in final.watchdog_findings if item["policy_id"] == "dangerous_action_policy")
        assert finding["affected_action_ids"] == ["provider-unsafe"]
        assert finding["metadata"]["matched_actions"] == ["cancel_job"]
        assert session.get(TicketDraft, UUID(final.ticket_draft_id)).lifecycle_state == "blocked"
        calls = session.exec(select(ToolCall).where(ToolCall.agent_run_id == result.agent_run_id)).all()
        assert "cancel_job" not in {item.tool_name for item in calls}


def test_policy_upgrade_does_not_rewrite_stored_candidate_or_verdict(engine):
    def snapshot_detail(session, identifier):
        detail = get_agent_run_detail(session, agent_run_id=identifier)
        return {
            name: [item.model_dump(mode="json") for item in value] if isinstance(value, list)
            else value.model_dump(mode="json") if value is not None else None
            for name, value in detail.items()
        }

    with Session(engine) as session:
        old = run_agent_for_alert(
            session, alert_id=demo_uuid("alert:suspicious-gpu-usage"), provider=DeterministicProvider(),
        )
        # Represent a previously persisted policy-v3 run. Reading and creating
        # later runs must preserve its version and verdict, never re-evaluate it.
        row = session.get(AgentRun, old.agent_run_id)
        row.policy_version = "watchdog-policy-v3"
        session.add(row)
        steps = session.exec(select(AgentStep).where(AgentStep.agent_run_id == row.id)).all()
        for step in steps:
            snapshot = deepcopy(step.output_snapshot)
            for candidate in (snapshot, snapshot.get("watchdog_decision") or {}, snapshot.get("final_recommendation") or {}):
                if candidate.get("policy_version"):
                    candidate["policy_version"] = "watchdog-policy-v3"
                if candidate.get("watchdog_decision"):
                    candidate["watchdog_decision"]["policy_version"] = "watchdog-policy-v3"
            step.output_snapshot = snapshot
            session.add(step)
        session.commit()
        before = snapshot_detail(session, row.id)
        assert before["agent_run"]["policy_version"] == "watchdog-policy-v3"
        assert before["final_recommendation"]["policy_version"] == "watchdog-policy-v3"
        newer = run_agent_for_alert(
            session, alert_id=demo_uuid("alert:suspicious-gpu-usage"), provider=DeterministicProvider(),
        )
        assert newer.policy_version == "watchdog-policy-v4"
        assert snapshot_detail(session, row.id) == before
