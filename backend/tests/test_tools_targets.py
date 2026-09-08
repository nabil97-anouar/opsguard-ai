from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.agent.planner import plan_tools_for_state
from app.agent.state import AgentState, AlertSummary
from app.db import session as db_session
from app.main import app
from app.models import ToolCall
from app.rag.trust import TrustLevel
from app.services.demo_seed import demo_uuid, seed_demo_data
from app.tools import registry
from app.tools.base import ToolExecutionContext
from app.tools.registry import list_tools


def _state(alert_type: str, raw_data: dict[str, Any]) -> AgentState:
    alert_id = uuid4()
    return AgentState(
        alert_id=alert_id,
        agent_run_id=uuid4(),
        alert_classification={"alert_type": alert_type},
        alert_summary=AlertSummary(
            id=alert_id,
            title="Operational incident",
            severity="high",
            source="sensor",
            infrastructure_type="gpu_cluster",
            status="new",
            description="Investigate resource activity.",
            raw_data=raw_data,
        ),
    )


@pytest.fixture
def seeded_client(monkeypatch):
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    seed_demo_data(reset=True)
    with TestClient(app) as client:
        yield engine, client


def test_tool_list_separates_executable_adapters_and_blocked_definitions(seeded_client) -> None:
    _, client = seeded_client
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["name"] for item in items if item["executable"]} == {
        "search_logs", "get_node_metrics", "get_running_jobs", "check_network_connections",
        "query_past_incidents", "retrieve_runbook", "create_ticket_draft",
    }
    assert {item["name"] for item in items if not item["executable"]} == {
        "cancel_job", "drain_node", "block_user", "isolate_node", "disable_service",
    }
    for definition in list_tools():
        assert isinstance(definition.trust_level, TrustLevel)
        if definition.executable:
            assert callable(definition.handler)
            assert definition.is_destructive is False
            assert definition.requires_human_approval is False
        else:
            assert definition.handler is None
            assert definition.is_destructive is True
            assert definition.requires_human_approval is True
            assert definition.trust_level == TrustLevel.UNTRUSTED


@pytest.mark.parametrize("restriction", ["requires_human_approval", "is_destructive", "no_handler"])
def test_execution_capability_is_enforced_before_calling_handler(seeded_client, monkeypatch, restriction: str) -> None:
    engine, _ = seeded_client
    definition = registry.get_tool("search_logs")
    calls = []

    def handler(*_):
        calls.append("called")
        return {"matches": [], "total": 0}

    changes: dict[str, Any] = {"handler": handler}
    if restriction == "no_handler":
        changes["handler"] = None
    else:
        changes[restriction] = True
    definition = replace(definition, **changes)
    monkeypatch.setattr(registry, "get_tool", lambda _: definition)
    assert definition.executable is False
    with Session(engine) as session:
        result = registry.execute_tool("search_logs", {"query": "xmrig"}, session, ToolExecutionContext())
    assert result.status == "blocked"
    assert result.outcome == "denied"
    assert calls == []


@pytest.mark.parametrize(
    ("name", "arguments", "status", "outcome"),
    [
        ("search_logs", {"query": "xmrig"}, "executed", "succeeded"),
        ("get_node_metrics", {"node": "missing-node"}, "failed", "failed"),
        ("drain_node", {"node": "explicit-node"}, "blocked", "denied"),
    ],
)
def test_tool_outcome_points_to_exact_persisted_audit_call(
    seeded_client, name: str, arguments: dict[str, str], status: str, outcome: str,
) -> None:
    engine, client = seeded_client
    run_id = demo_uuid("agent-run:gpu-abuse")
    payloads = []
    for _ in range(2):
        response = client.post(
            f"/api/v1/tools/{name}/execute",
            json={"input": arguments, "agent_run_id": str(run_id)},
        )
        assert response.status_code == 200
        payload = response.json()
        payloads.append(payload)
        assert payload["status"] == status
        assert payload["outcome"] == outcome
        assert payload["tool_call_id"] is not None
        with Session(engine) as session:
            tool_call = session.get(ToolCall, UUID(payload["tool_call_id"]))
            assert tool_call is not None
            assert tool_call.agent_run_id == run_id
            assert tool_call.tool_name == name
            assert tool_call.status == status
            assert all(tool_call.input_args[key] == value for key, value in arguments.items())
            if status == "failed":
                assert payload["output"] == {}
                assert tool_call.error_message == payload["error"]
            else:
                assert tool_call.output == payload["output"]
    assert payloads[0]["tool_call_id"] != payloads[1]["tool_call_id"]


def test_standalone_tool_call_has_a_persisted_attempt_identity(seeded_client) -> None:
    _, client = seeded_client
    response = client.post("/api/v1/tools/search_logs/execute", json={"input": {"query": "xmrig"}})
    assert response.status_code == 200
    assert response.json()["outcome"] == "succeeded"
    assert response.json()["tool_call_id"] is not None
    with Session(seeded_client[0]) as session:
        from app.models import ToolExecutionAudit
        assert session.get(ToolExecutionAudit, UUID(response.json()["tool_call_id"])).handler_invoked is True


def test_invalid_adapter_output_returns_audited_failure(seeded_client, monkeypatch) -> None:
    engine, client = seeded_client
    definition = replace(registry.get_tool("search_logs"), handler=lambda *_: {"matches": "not-a-list", "total": 1})
    monkeypatch.setattr(registry, "get_tool", lambda _: definition)
    run_id = demo_uuid("agent-run:gpu-abuse")

    response = client.post(
        "/api/v1/tools/search_logs/execute",
        json={"input": {"query": "xmrig"}, "agent_run_id": str(run_id)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["outcome"] == "failed"
    assert payload["output"] == {}
    assert payload["tool_call_id"] is not None
    assert payload["error_code"] == "handler_error"
    assert payload["handler_invoked"] is True
    with Session(engine) as session:
        audit = session.get(ToolCall, UUID(payload["tool_call_id"]))
        assert audit is not None
        assert audit.agent_run_id == run_id
        assert audit.tool_name == "search_logs"
        assert audit.status == "failed"
        assert audit.output == {}
        assert audit.error_message == payload["error"]


def test_invalid_adapter_input_remains_422_and_never_invokes_handler(seeded_client, monkeypatch) -> None:
    _, client = seeded_client
    calls = []

    def handler(*_):
        calls.append("called")
        return {"matches": [], "total": 0}

    definition = replace(registry.get_tool("search_logs"), handler=handler)
    monkeypatch.setattr(registry, "get_tool", lambda _: definition)
    response = client.post(
        "/api/v1/tools/search_logs/execute",
        json={"input": {"query": ""}, "agent_run_id": str(demo_uuid("agent-run:gpu-abuse"))},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["loc"] == ["query"]
    assert response.json()["detail"]["errors"][0]["type"] == "string_too_short"
    assert calls == []


@pytest.mark.parametrize("value", [None, "", "  ", True, [], {}])
def test_gpu_planner_never_invents_missing_targets(value: Any) -> None:
    state = _state("suspicious_gpu_usage", {"node": value, "job_id": value})
    tools, blocked = plan_tools_for_state(state)
    assert [tool.tool_name for tool in tools] == ["search_logs", "retrieve_runbook"]
    assert blocked == []
    assert state.missing_evidence == [
        "Alert does not identify a valid node; target-specific checks and actions were omitted.",
        "Alert does not identify a valid job_id; target-specific checks and actions were omitted.",
    ]
    assert state.missing_targets == ["node", "job_id"]
    assert all("gpu-node-14" not in str(tool.input) and "unknown-job" not in str(tool.input) for tool in tools)
    plan_tools_for_state(state)
    assert len(state.missing_evidence) == 2
    assert state.missing_targets == ["node", "job_id"]


def test_gpu_planner_uses_only_explicit_targets() -> None:
    state = _state("suspicious_gpu_usage", {"node": "actual-node", "job_id": 123})
    tools, blocked = plan_tools_for_state(state)
    target_tools = [tool for tool in tools if "node" in tool.input]
    assert [tool.tool_name for tool in target_tools] == [
        "get_node_metrics", "get_running_jobs", "check_network_connections",
    ]
    assert all(tool.input["node"] == "actual-node" for tool in target_tools)
    assert [(action.tool_name, action.target) for action in blocked] == [
        ("cancel_job", "123"), ("isolate_node", "actual-node"),
    ]
    assert state.missing_evidence == []
    assert state.missing_targets == []


def test_ssh_planner_does_not_invent_an_affected_user() -> None:
    state = _state("ssh_bruteforce", {})
    _, blocked = plan_tools_for_state(state)
    assert blocked == []
    assert state.missing_evidence == [
        "Alert does not identify a valid user; target-specific checks and actions were omitted.",
    ]
    assert state.missing_targets == ["user"]
    explicit_state = _state("ssh_bruteforce", {"user": "affected-user"})
    _, explicit_blocked = plan_tools_for_state(explicit_state)
    assert [(action.tool_name, action.target) for action in explicit_blocked] == [("block_user", "affected-user")]
    assert explicit_state.missing_evidence == []
    assert explicit_state.missing_targets == []


def test_injection_classification_does_not_invent_operational_actions() -> None:
    state = _state("rag_prompt_injection", {})
    _, blocked = plan_tools_for_state(state)
    assert blocked == []


@pytest.mark.parametrize("name", ["get_node_metrics", "check_network_connections", "get_running_jobs"])
def test_blank_node_is_rejected_by_targeted_adapters(seeded_client, name: str) -> None:
    _, client = seeded_client
    response = client.post(f"/api/v1/tools/{name}/execute", json={"input": {"node": "  "}})
    assert response.status_code == 422
