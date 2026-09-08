from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from uuid import UUID, uuid4
import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agent.actions import ProposedAction
from app.agent.runner import run_agent_for_alert
from app.db import session as db_session
from app.main import app
from app.models import AgentRun, AgentStep, TicketDraft, ToolCall, ToolExecutionAudit
from app.services.demo_seed import demo_uuid, seed_demo_data
from app.tools import ToolExecutionContext, execute_tool
from app.tools import registry
from app.watchdog import WatchdogInput, evaluate_watchdog
from app.watchdog.policies import dangerous_action_policy, bulk_operation_policy, grounding_reference_integrity_policy


def context(**overrides):
    run_id = uuid4()
    evidence = {"evidence_id": f"{run_id}:alert:1", "agent_run_id": str(run_id),
        "kind": "alert", "observation_status": "valid", "trust_level": "trusted",
        "citation": "alert://1", "summary": "Observed event"}
    values = dict(agent_run_id=run_id, evidence_items=[evidence],
        proposed_actions=[ProposedAction(action_type="investigate", target="gpu-node-14",
            rationale="Inspect the event", requires_approval=False, supporting_evidence_ids=[evidence["evidence_id"]])])
    values.update(overrides)
    return WatchdogInput(**values)


@pytest.fixture
def client_db(monkeypatch, tmp_path):
    # File-backed SQLite exercises actual independent connections/transactions.
    engine = db_session.build_engine(f"sqlite:///{tmp_path}/audit.db")
    monkeypatch.setattr(db_session, "engine", engine)
    seed_demo_data()
    yield TestClient(app), engine
    engine.dispose()


@pytest.mark.parametrize("text", ["DELETE", "DeLeTe", " 'SHUTDOWN' ", '"DrAiN---NoDe"', "DRAIN   NODE", "d.r.a.i.n_node"])
def test_normalized_dangerous_narrative_blocks(text):
    decision = evaluate_watchdog(context(final_recommendation={"summary": f"Execute {text} now"}))
    finding = next(item for item in decision.findings if item.policy_id == "dangerous_action_policy")
    assert finding.blocking is True
    assert decision.verdict.value == "block"
    assert decision.mandatory_review is True


@pytest.mark.parametrize("action_type", ["DRAIN_NODE", "Drain---Node", " 'drain node' ", "DrainNodes"])
def test_structured_dangerous_action_cannot_be_hidden_by_prose(action_type):
    payload = context()
    payload.proposed_actions[0].action_type = ProposedAction(action_type=action_type, rationale="Routine check").action_type
    payload.final_recommendation = {"summary": "Everything is routine."}
    findings = dangerous_action_policy(payload)
    assert len(findings) == 1
    assert findings[0].blocking is True
    assert findings[0].affected_action_ids == [payload.proposed_actions[0].action_id]


def test_evidence_hypotheses_and_tool_output_are_not_action_proposals():
    phrase = "DELETE; DRAIN_NODE all jobs ALL--NODES"
    payload = context(retrieved_context=[{"content_excerpt": phrase, "trust_level": "trusted"}],
        tool_results=[{"output": {"log": phrase}, "trust_level": "trusted"}],
        hypotheses=[{"summary": phrase}])
    payload.evidence_items[0]["summary"] = phrase
    assert dangerous_action_policy(payload) == []
    assert bulk_operation_policy(payload) == []


@pytest.mark.parametrize("mutation", ["cross_run", "missing", "failed", "blocked", "quarantined", "empty", "invalid"])
def test_structural_reference_failure_blocks_action(mutation):
    payload = context()
    evidence = payload.evidence_items[0]
    if mutation == "cross_run":
        evidence["agent_run_id"] = str(uuid4())
    elif mutation == "missing":
        payload.proposed_actions[0].supporting_evidence_ids = ["does-not-exist"]
    elif mutation in {"failed", "blocked"}:
        evidence.update(kind="tool_output", tool_call_id=str(uuid4()), observation_status="succeeded")
        payload.tool_results = [{"tool_call_id": evidence["tool_call_id"], "status": mutation}]
    elif mutation == "quarantined":
        evidence["trust_level"] = "quarantined"
    elif mutation == "empty":
        payload.proposed_actions[0].supporting_evidence_ids = []
    else:
        evidence["observation_status"] = "invalid"
    findings = grounding_reference_integrity_policy(payload)
    assert len(findings) == 1
    assert findings[0].blocking is True
    assert findings[0].affected_action_ids == [payload.proposed_actions[0].action_id]


def test_hypothesis_cross_run_and_empty_references_fail():
    payload = context(hypotheses=[{"supporting_evidence": [str(uuid4())]}, {"supporting_evidence": []}])
    findings = grounding_reference_integrity_policy(payload)
    assert findings[0].evidence_refs == ["hypothesis://0", "hypothesis://1"]


@pytest.mark.parametrize("parameters", [
    {"target_count": 2}, {"TARGET_COUNT": " 2 "}, {"targets": ["n1", "n2"]},
    {"scope": "ALL---NODES"}, {"all_jobs": True}, {"selector": "*"},
    {"selector": {}}, {"selector": {"match_labels": {"pool": "gpu"}}},
])
def test_bulk_structured_parameters_block(parameters):
    payload = context()
    payload.proposed_actions[0].parameters = parameters
    findings = bulk_operation_policy(payload)
    assert len(findings) == 1 and findings[0].blocking is True
    assert findings[0].affected_action_ids == [payload.proposed_actions[0].action_id]


def test_one_target_observation_supported_action_passes_structural_policies():
    payload = context()
    payload.proposed_actions[0].parameters = {"target_count": 1, "selector": {"id": "gpu-node-14"}}
    assert dangerous_action_policy(payload) == []
    assert bulk_operation_policy(payload) == []
    assert grounding_reference_integrity_policy(payload) == []


def audit_row(engine, identifier):
    with Session(engine) as session:
        row = session.get(ToolExecutionAudit, UUID(identifier))
        assert row is not None
        return row.model_dump(mode="json")


@pytest.mark.parametrize("name,body,http_status,code", [
    ("unknown", {"input": {}}, 404, "unknown_tool"),
    ("search_logs", {"input": {"query": ""}}, 422, "validation_error"),
    ("search_logs", {"input": []}, 422, "malformed_request"),
    ("search_logs", {"input": {}, "agent_run_id": "bad"}, 422, "malformed_request"),
])
def test_rejected_requests_have_durable_audit(client_db, name, body, http_status, code):
    client, engine = client_db
    response = client.post(f"/api/v1/tools/{name}/execute", json=body)
    assert response.status_code == http_status
    row = audit_row(engine, response.json()["detail"]["tool_call_id"])
    assert row["tool_name"] == name
    assert row["outcome"] == "denied"
    assert row["handler_invoked"] is False
    assert row["error_code"] == code
    assert row["completed_at"] is not None


def test_malformed_json_is_audited_without_raw_secret(client_db):
    client, engine = client_db
    response = client.post("/api/v1/tools/search_logs/execute", content='password=SHOULD_NOT_APPEAR{', headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    row = audit_row(engine, response.json()["detail"]["tool_call_id"])
    assert row["outcome"] == "denied" and row["handler_invoked"] is False
    assert "SHOULD_NOT_APPEAR" not in json.dumps(row)


def test_blocked_definition_never_invokes_even_if_registry_flags_corrupted(client_db, monkeypatch):
    client, engine = client_db
    invocations = []
    original = registry.get_tool
    def definition(name):
        return replace(original(name), is_destructive=False, requires_human_approval=False,
            handler=lambda *_: invocations.append(name))
    monkeypatch.setattr(registry, "get_tool", definition)
    response = client.post("/api/v1/tools/drain_node/execute", json={"input": {"node": "gpu-node-14"}})
    assert response.json()["outcome"] == "denied"
    row = audit_row(engine, response.json()["tool_call_id"])
    assert row["handler_invoked"] is False
    assert row["validated"] is True
    assert invocations == []


def test_handler_failure_rolls_back_effects_but_preserves_invocation_and_audit(client_db, monkeypatch):
    _, engine = client_db
    definition = registry.get_tool("search_logs")
    run_id = demo_uuid("agent-run:gpu-abuse")
    def failing_handler(inputs, session, context):
        run = session.get(AgentRun, run_id)
        run.error_message = "must roll back"
        session.add(run)
        session.flush()
        raise RuntimeError("password=TOPSECRET")
    monkeypatch.setattr(registry, "get_tool", lambda _: replace(definition, handler=failing_handler))
    with Session(engine) as caller:
        result = execute_tool("search_logs", {"query": "xmrig", "password": "TOPSECRET"}, caller,
            ToolExecutionContext(agent_run_id=run_id))
        caller.rollback()
    row = audit_row(engine, str(result.tool_call_id))
    assert (row["outcome"], row["handler_invoked"], row["validated"]) == ("failed", True, True)
    assert row["invoked_at"] is not None and row["completed_at"] is not None
    assert row["diagnostic"] == {"exception_type": "RuntimeError"}
    assert "TOPSECRET" not in json.dumps(row)
    with Session(engine) as session:
        assert session.get(AgentRun, run_id).error_message != "must roll back"
        assert session.get(ToolCall, result.tool_call_id).handler_invoked is True


def test_success_has_same_call_run_target_and_tool_identity(client_db):
    client, engine = client_db
    run_id = demo_uuid("agent-run:gpu-abuse")
    response = client.post("/api/v1/tools/get_node_metrics/execute", json={"input": {"node": "gpu-node-14"}, "agent_run_id": str(run_id)})
    row = audit_row(engine, response.json()["tool_call_id"])
    assert row["agent_run_id"] == str(run_id)
    assert row["tool_name"] == "get_node_metrics"
    assert row["validated_target"] == {"node": "gpu-node-14"}
    assert row["outcome"] == "succeeded" and row["handler_invoked"] is True
    assert row["output_snapshot"] == response.json()["output"]


def test_inner_run_identity_cannot_redirect_ticket_or_audit(client_db):
    client, engine = client_db
    owner = demo_uuid("agent-run:gpu-abuse")
    other = demo_uuid("agent-run:prompt-injection")
    response = client.post("/api/v1/tools/create_ticket_draft/execute", json={"agent_run_id": str(owner),
        "input": {"agent_run_id": str(other), "title": "Context-owned draft", "body": "Review evidence"}})
    assert response.json()["outcome"] == "succeeded"
    assert response.json()["output"]["lifecycle_state"] == "candidate"
    assert response.json()["output"]["policy_validation"] == "not_evaluated"
    row = audit_row(engine, response.json()["tool_call_id"])
    assert row["agent_run_id"] == str(owner)
    with Session(engine) as session:
        ticket = session.get(TicketDraft, UUID(response.json()["output"]["ticket_draft_id"]))
        assert ticket.agent_run_id == owner
        assert ticket.lifecycle_state == "candidate"
        assert ticket.policy_validation == "not_evaluated"
        assert session.get(ToolCall, UUID(row["id"])).agent_run_id == owner


def test_policy_review_precedes_ticket_and_blocked_artifact_is_not_review_valid(client_db, monkeypatch):
    _, engine = client_db
    from app.agent import nodes
    original = nodes.evaluate_watchdog
    def inspect_candidate(payload):
        assert payload.final_recommendation["lifecycle_state"] == "candidate"
        assert payload.final_recommendation["review_valid"] is False
        assert payload.final_recommendation["ticket_draft_id"] is None
        with Session(engine) as session:
            assert not session.exec(select(TicketDraft).where(TicketDraft.agent_run_id == payload.agent_run_id)).all()
        return original(payload)
    monkeypatch.setattr(nodes, "evaluate_watchdog", inspect_candidate)
    with Session(engine) as session:
        result = run_agent_for_alert(session, alert_id=demo_uuid("alert:rag-prompt-injection"))
        assert result.status == "waiting_for_human"
        final = result.final_recommendation
        assert final.lifecycle_state == "blocked"
        assert final.review_valid is False
        assert final.watchdog_decision["blocking"] is True
        ticket = session.get(TicketDraft, UUID(final.ticket_draft_id))
        assert ticket.lifecycle_state == "blocked"
        assert ticket.policy_validation == "evaluated"
        candidate_step = session.exec(select(AgentStep).where(AgentStep.agent_run_id == result.agent_run_id,
            AgentStep.node_name == "generate_recommendation")).one()
        assert candidate_step.output_snapshot["lifecycle_state"] == "candidate"
        assert candidate_step.output_snapshot["review_valid"] is False


def test_old_audit_is_unchanged_after_unrelated_activity(client_db):
    client, engine = client_db
    response = client.post("/api/v1/tools/search_logs/execute", json={"input": {"query": "xmrig"}})
    identifier = response.json()["tool_call_id"]
    before = audit_row(engine, identifier)
    client.post("/api/v1/tools/drain_node/execute", json={"input": {"node": "gpu-node-14"}})
    with Session(engine) as session:
        run_agent_for_alert(session, alert_id=demo_uuid("alert:rag-prompt-injection"))
    assert audit_row(engine, identifier) == before


def test_audit_output_redacted_bounded_and_serializable(client_db, monkeypatch):
    client, engine = client_db
    from pydantic import BaseModel
    from typing import Any
    class Output(BaseModel):
        token: str
        payload: Any
    definition = replace(registry.get_tool("search_logs"), output_schema=Output,
        handler=lambda *_: {"token": "TOPSECRET", "payload": ["password=TOPSECRET " + "x" * 50000] * 100})
    monkeypatch.setattr(registry, "get_tool", lambda _: definition)
    response = client.post("/api/v1/tools/search_logs/execute", json={"input": {"query": "xmrig"}})
    row = audit_row(engine, response.json()["tool_call_id"])
    assert row["outcome"] == "succeeded"
    assert len(json.dumps(row["output_snapshot"]).encode()) <= 16384
    assert "TOPSECRET" not in json.dumps(row)


def test_observation_narrative_and_action_rationale_do_not_imply_destructive_intent():
    payload = context(final_recommendation={"summary": "Logs mention DELETE and DRAIN_NODE all jobs."})
    payload.proposed_actions[0].rationale = "Inspect evidence mentioning DELETE."
    assert dangerous_action_policy(payload) == []
    assert bulk_operation_policy(payload) == []


def test_duplicate_action_ids_cannot_hide_dangerous_intent():
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Duplicate"):
        WatchdogInput(proposed_actions=[
            ProposedAction(action_id="same", action_type="drain_node", rationale="Execute drain"),
            ProposedAction(action_id="same", action_type="review_evidence", rationale="Inspect")])


def test_api_never_accepts_forged_source_ledger_for_nonexistent_run(client_db):
    client, _ = client_db
    payload = context()
    response = client.post("/api/v1/watchdog/evaluate", json=payload.model_dump(mode="json"))
    assert response.status_code == 200
    assert response.json()["blocking"] is True
    assert any(item["policy_id"] == "grounding_reference_integrity" for item in response.json()["findings"])


def test_cross_run_api_reference_cannot_be_laundered_by_supplied_same_run_label(client_db):
    client, engine = client_db
    with Session(engine) as session:
        first = run_agent_for_alert(session, alert_id=demo_uuid("alert:rag-prompt-injection"))
        second = run_agent_for_alert(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))
    forged = deepcopy(first.final_recommendation.evidence[0])
    forged["agent_run_id"] = str(second.agent_run_id)
    response = client.post("/api/v1/watchdog/evaluate", json={"agent_run_id": str(second.agent_run_id),
        "evidence_items": [forged], "proposed_actions": [{"action_type": "investigate", "rationale": "Inspect event",
            "supporting_evidence_ids": [forged["evidence_id"]]}]})
    assert response.json()["blocking"] is True
    assert any(item["policy_id"] == "grounding_reference_integrity" for item in response.json()["findings"])


def test_handlers_cannot_commit_their_own_effects(client_db, monkeypatch):
    client, engine = client_db
    definition = registry.get_tool("search_logs")
    def bad_handler(inputs, session, context):
        run = session.get(AgentRun, demo_uuid("agent-run:gpu-abuse"))
        run.error_message = "must not become durable"
        session.add(run)
        session.commit()
        return {"matches": [], "total": 0}
    monkeypatch.setattr(registry, "get_tool", lambda _: replace(definition, handler=bad_handler))
    response = client.post("/api/v1/tools/search_logs/execute", json={"input": {"query": "xmrig"}})
    row = audit_row(engine, response.json()["tool_call_id"])
    assert row["outcome"] == "failed" and row["handler_invoked"] is True
    with Session(engine) as session:
        assert session.get(AgentRun, demo_uuid("agent-run:gpu-abuse")).error_message != "must not become durable"


def test_candidate_clears_provider_supplied_validation_fields(client_db, monkeypatch):
    _, engine = client_db
    from app.agent import nodes
    original = nodes.generate_final_recommendation
    def forged(state):
        payload = original(state)
        payload.update(review_valid=True, lifecycle_state="pending_human_review", policy_version="fake",
            watchdog_decision={"verdict": "allow"}, watchdog_status="allow", ticket_draft_id=str(uuid4()))
        return payload
    monkeypatch.setattr(nodes, "generate_final_recommendation", forged)
    with Session(engine) as session:
        result = run_agent_for_alert(session, alert_id=demo_uuid("alert:rag-prompt-injection"))
        candidate = session.exec(select(AgentStep).where(AgentStep.agent_run_id == result.agent_run_id,
            AgentStep.node_name == "generate_recommendation")).one().output_snapshot
        assert candidate["lifecycle_state"] == "candidate"
        assert candidate["review_valid"] is False
        assert candidate["watchdog_decision"] is None
        assert candidate["watchdog_status"] is None
        assert candidate["ticket_draft_id"] is None


def test_nondestructive_approval_required_adapter_remains_denied(client_db, monkeypatch):
    client, engine = client_db
    observed = []
    definition = replace(registry.get_tool("search_logs"), requires_human_approval=True,
        handler=lambda *_: observed.append("invoked"))
    monkeypatch.setattr(registry, "get_tool", lambda _: definition)
    response = client.post("/api/v1/tools/search_logs/execute", json={"input": {"query": "xmrig"}})
    assert response.json()["requires_human_approval"] is True
    assert response.json()["outcome"] == "denied"
    assert response.json()["error_code"] == "approval_required"
    assert observed == []
    assert audit_row(engine, response.json()["tool_call_id"])["handler_invoked"] is False


def test_invalid_step_context_denies_without_misattributing_projection(client_db):
    _, engine = client_db
    with Session(engine) as session:
        other_step = session.exec(select(AgentStep).where(AgentStep.agent_run_id == demo_uuid("agent-run:prompt-injection"))).first()
        result = execute_tool("search_logs", {"query": "xmrig"}, session,
            ToolExecutionContext(agent_run_id=demo_uuid("agent-run:gpu-abuse"), step_id=other_step.id))
        assert result.outcome == "denied"
        assert result.handler_invoked is False
        assert session.get(ToolCall, result.tool_call_id) is None
    row = audit_row(engine, str(result.tool_call_id))
    assert row["error_code"] == "invalid_run_context"


def test_one_target_policy_denial_is_audited_before_invocation(client_db):
    client, engine = client_db
    response = client.post("/api/v1/tools/get_node_metrics/execute", json={"input": {"node": "*"}})
    row = audit_row(engine, response.json()["tool_call_id"])
    assert row["outcome"] == "denied" and row["handler_invoked"] is False
    assert row["error_code"] == "broad_target_denied"
    assert row["validated_target"] == {}


def test_approval_flag_is_a_structured_review_requirement():
    payload = context()
    payload.proposed_actions[0].requires_approval = True
    finding = dangerous_action_policy(payload)[0]
    assert finding.blocking is False
    assert finding.mandatory_review is True
    assert finding.affected_action_ids == [payload.proposed_actions[0].action_id]


def test_malformed_input_keeps_valid_outer_run_context(client_db):
    client, engine = client_db
    owner = str(demo_uuid("agent-run:gpu-abuse"))
    response = client.post("/api/v1/tools/search_logs/execute", json={"agent_run_id": owner, "input": []})
    row = audit_row(engine, response.json()["detail"]["tool_call_id"])
    assert row["agent_run_id"] == owner
    assert row["handler_invoked"] is False
    assert row["outcome"] == "denied"


def test_output_validation_failure_rolls_back_effects_and_keeps_invocation(client_db, monkeypatch):
    client, engine = client_db
    definition = registry.get_tool("search_logs")
    def invalid_output(inputs, session, context):
        run = session.get(AgentRun, demo_uuid("agent-run:gpu-abuse"))
        run.error_message = "invalid output side effect"
        session.add(run)
        session.flush()
        return {"invalid": True}
    monkeypatch.setattr(registry, "get_tool", lambda _: replace(definition, handler=invalid_output))
    response = client.post("/api/v1/tools/search_logs/execute", json={"input": {"query": "xmrig"}})
    row = audit_row(engine, response.json()["tool_call_id"])
    assert row["outcome"] == "failed" and row["handler_invoked"] is True
    assert row["diagnostic"] == {"exception_type": "ValidationError"}
    with Session(engine) as session:
        assert session.get(AgentRun, demo_uuid("agent-run:gpu-abuse")).error_message != "invalid output side effect"


def test_distinct_findings_of_same_policy_are_not_lost(client_db):
    _, engine = client_db
    from app.watchdog.audit import record_watchdog_decision
    from app.models import SafetyEvent
    owner = demo_uuid("agent-run:gpu-abuse")
    first = context()
    first.proposed_actions[0].action_type = ProposedAction(action_type="delete", rationale="Execute").action_type
    second = deepcopy(first)
    second.proposed_actions[0].action_id = "second-action"
    with Session(engine) as session:
        for payload in [first, first, second]:
            record_watchdog_decision(session, agent_run_id=owner, decision=evaluate_watchdog(payload))
        session.commit()
        events = session.exec(select(SafetyEvent).where(SafetyEvent.agent_run_id == owner,
            SafetyEvent.source == "watchdog", SafetyEvent.affected_component == "dangerous_action_policy")).all()
        assert len(events) == 2
        assert len({event.details["finding_id"] for event in events}) == 2


def test_additive_tool_and_ticket_upgrade_preserves_unknown_history(client_db):
    _, engine = client_db
    from sqlalchemy import text
    from app.db.init_db import create_db_and_tables
    with Session(engine) as session:
        call = session.exec(select(ToolCall)).first()
        ticket = session.exec(select(TicketDraft)).first()
        call_id, ticket_id = call.id, ticket.id
        old_output, old_description = deepcopy(call.output), ticket.description
    ToolExecutionAudit.__table__.drop(engine)
    with engine.begin() as connection:
        for table, columns in {
            "tool_calls": ["handler_invoked", "outcome", "origin"],
            "ticket_drafts": ["lifecycle_state", "policy_validation", "policy_version"],
        }.items():
            for column in columns:
                connection.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
    create_db_and_tables(engine)
    create_db_and_tables(engine)
    with Session(engine) as session:
        call, ticket = session.get(ToolCall, call_id), session.get(TicketDraft, ticket_id)
        assert call.handler_invoked is None and call.outcome == "legacy_unknown"
        assert call.output == old_output
        assert ticket.lifecycle_state == "legacy_unknown"
        assert ticket.policy_validation == "not_evaluated" and ticket.policy_version is None
        assert ticket.description == old_description
        assert session.exec(select(ToolExecutionAudit)).all() == []


def test_structured_parameter_cannot_hide_action_behind_innocuous_type():
    payload = context()
    payload.proposed_actions[0].parameters = {"operation": " 'DeLeTe' "}
    finding = dangerous_action_policy(payload)[0]
    assert finding.blocking is True
    assert finding.affected_action_ids == [payload.proposed_actions[0].action_id]


def test_normalized_proposal_text_retains_multiple_target_detection():
    payload = context(final_recommendation={"summary": "Execute investigation on GPU-NODE-14 and GpU-NoDe-15."})
    finding = bulk_operation_policy(payload)[0]
    assert finding.blocking is True
    assert finding.metadata["targets"] == ["gpu node 14", "gpu node 15"]


def test_api_resolves_successful_same_run_source_without_caller_ledger(client_db):
    client, engine = client_db
    with Session(engine) as session:
        run = run_agent_for_alert(session, alert_id=demo_uuid("alert:rag-prompt-injection"))
    evidence = [item for item in run.final_recommendation.evidence if item["kind"] == "tool_output"]
    assert evidence
    response = client.post("/api/v1/watchdog/evaluate", json={"agent_run_id": str(run.agent_run_id),
        "proposed_actions": [{"action_type": "investigate", "rationale": "Inspect observation",
            "requires_approval": False, "supporting_evidence_ids": [evidence[0]["evidence_id"]]}]})
    assert response.status_code == 200
    assert not any(item["policy_id"] == "grounding_reference_integrity" for item in response.json()["findings"])


@pytest.mark.parametrize("value", ['password="TOPSECRET"', "token='TOPSECRET'", '{"api_key": "TOPSECRET"}', "Bearer TOPSECRET"])
def test_obvious_quoted_credentials_are_redacted(value):
    from app.tools.hygiene import snapshot
    assert "TOPSECRET" not in json.dumps(snapshot({"message": value}))


@pytest.mark.parametrize("parameters", [
    {"nodes": "*"}, {"jobs": "ALL"}, {"ALL_NODES": "TrUe"}, {"target_count": "2.0"},
    {"target": ["n1", "n2"]}, {"target": "＊"},
])
def test_equivalent_bulk_scope_formats_cannot_bypass(parameters):
    payload = context()
    payload.proposed_actions[0].parameters = parameters
    assert bulk_operation_policy(payload)[0].blocking is True


def test_exact_single_target_selector_is_case_insensitive():
    payload = context()
    payload.proposed_actions[0].parameters = {"SELECTOR": {"ID": "gpu-node-14"}}
    assert bulk_operation_policy(payload) == []
