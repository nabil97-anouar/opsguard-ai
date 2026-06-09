from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import session as db_session
from app.main import app
from app.models import SafetyEvent, TicketDraft, ToolCall
from app.services.demo_seed import demo_uuid, seed_demo_data


def build_seeded_client(monkeypatch) -> tuple[object, TestClient]:
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)
    seed_demo_data(reset=True)
    return test_engine, TestClient(app)


def test_list_tools_endpoint(monkeypatch) -> None:
    _, client = build_seeded_client(monkeypatch)

    response = client.get("/api/v1/tools")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    names = {item["name"] for item in payload["items"]}
    assert "search_logs" in names
    assert "retrieve_runbook" in names
    assert "cancel_job" in names
    search_logs_definition = next(item for item in payload["items"] if item["name"] == "search_logs")
    assert search_logs_definition["requires_human_approval"] is False
    assert "properties" in search_logs_definition["input_schema"]


def test_unknown_tool_is_rejected(monkeypatch) -> None:
    _, client = build_seeded_client(monkeypatch)

    response = client.post("/api/v1/tools/not-a-real-tool/execute", json={"input": {}, "agent_run_id": None})

    assert response.status_code == 404


def test_search_logs_tool_works(monkeypatch) -> None:
    _, client = build_seeded_client(monkeypatch)

    response = client.post(
        "/api/v1/tools/search_logs/execute",
        json={"input": {"query": "xmrig mining pool", "limit": 5}, "agent_run_id": None},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "executed"
    assert payload["output"]["total"] >= 2
    assert any("xmrig-cuda" in match["message"] for match in payload["output"]["matches"])


def test_get_node_metrics_tool_works(monkeypatch) -> None:
    _, client = build_seeded_client(monkeypatch)

    response = client.post(
        "/api/v1/tools/get_node_metrics/execute",
        json={"input": {"node": "gpu-node-14"}, "agent_run_id": None},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "executed"
    assert payload["output"]["node"] == "gpu-node-14"
    assert payload["output"]["gpu_utilization"] > 90


def test_get_running_jobs_and_network_tools_work(monkeypatch) -> None:
    _, client = build_seeded_client(monkeypatch)

    jobs_response = client.post(
        "/api/v1/tools/get_running_jobs/execute",
        json={"input": {"node": "gpu-node-14"}, "agent_run_id": None},
    )
    network_response = client.post(
        "/api/v1/tools/check_network_connections/execute",
        json={"input": {"node": "gpu-node-14", "limit": 10}, "agent_run_id": None},
    )

    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()
    assert jobs_payload["status"] == "executed"
    assert jobs_payload["output"]["total"] >= 1
    assert any(job["job_id"] == "884231" for job in jobs_payload["output"]["jobs"])

    assert network_response.status_code == 200
    network_payload = network_response.json()
    assert network_payload["status"] == "executed"
    assert network_payload["output"]["total"] >= 2
    assert any(connection["remote_port"] == 3333 for connection in network_payload["output"]["connections"])


def test_query_past_incidents_and_retrieve_runbook_work_after_demo_seed(monkeypatch) -> None:
    _, client = build_seeded_client(monkeypatch)

    incidents_response = client.post(
        "/api/v1/tools/query_past_incidents/execute",
        json={"input": {"query": "gpu mining compromised image", "limit": 5}, "agent_run_id": None},
    )
    runbook_response = client.post(
        "/api/v1/tools/retrieve_runbook/execute",
        json={"input": {"query": "gpu suspicious process xmrig", "limit": 5}, "agent_run_id": None},
    )

    assert incidents_response.status_code == 200
    incidents_payload = incidents_response.json()
    assert incidents_payload["status"] == "executed"
    assert incidents_payload["output"]["total"] >= 1
    assert any("GPU abuse investigation" == incident["title"] for incident in incidents_payload["output"]["incidents"])

    assert runbook_response.status_code == 200
    runbook_payload = runbook_response.json()
    assert runbook_payload["status"] == "executed"
    assert runbook_payload["output"]["total"] >= 1
    assert any(
        "Trusted GPU Abuse Incident Response Runbook" in result["title"]
        for result in runbook_payload["output"]["results"]
    )
    assert all(result["trust_level"] == "trusted" for result in runbook_payload["output"]["results"])


def test_create_ticket_draft_creates_db_row_and_audits_tool_call(monkeypatch) -> None:
    test_engine, client = build_seeded_client(monkeypatch)
    agent_run_id = str(demo_uuid("agent-run:gpu-abuse"))

    with Session(test_engine) as session:
        initial_ticket_count = len(session.exec(select(TicketDraft)).all())
        initial_tool_call_count = len(session.exec(select(ToolCall)).all())

    response = client.post(
        "/api/v1/tools/create_ticket_draft/execute",
        json={
            "input": {
                "agent_run_id": agent_run_id,
                "title": "GPU abuse follow-up draft",
                "body": "Create a draft for suspicious xmrig activity and preserve citations for human review.",
            },
            "agent_run_id": agent_run_id,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "executed"
    assert payload["output"]["status"] == "draft"
    assert payload["output"]["title"] == "GPU abuse follow-up draft"

    with Session(test_engine) as session:
        ticket_drafts = session.exec(
            select(TicketDraft).where(TicketDraft.title == "GPU abuse follow-up draft")
        ).all()
        tool_calls = session.exec(
            select(ToolCall).where(ToolCall.tool_name == "create_ticket_draft")
        ).all()
        assert len(session.exec(select(TicketDraft)).all()) == initial_ticket_count + 1
        assert len(session.exec(select(ToolCall)).all()) == initial_tool_call_count + 1
        assert ticket_drafts
        assert any(tool_call.agent_run_id == demo_uuid("agent-run:gpu-abuse") for tool_call in tool_calls)


def test_dangerous_tools_are_blocked_and_record_safety_event(monkeypatch) -> None:
    test_engine, client = build_seeded_client(monkeypatch)
    agent_run_id = str(demo_uuid("agent-run:prompt-injection"))

    response = client.post(
        "/api/v1/tools/drain_node/execute",
        json={
            "input": {"node": "gpu-node-14", "reason": "suspicious xmrig traffic"},
            "agent_run_id": agent_run_id,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["requires_human_approval"] is True
    assert payload["output"]["status"] == "blocked"

    with Session(test_engine) as session:
        blocked_event = session.exec(
            select(SafetyEvent).where(
                SafetyEvent.event_type == "dangerous_tool_blocked",
                SafetyEvent.affected_component == "drain_node",
            )
        ).first()
        blocked_tool_call = session.exec(
            select(ToolCall).where(
                ToolCall.tool_name == "drain_node",
                ToolCall.status == "blocked",
            )
        ).first()
        assert blocked_event is not None
        assert blocked_tool_call is not None


def test_no_arbitrary_shell_execution_exists_in_tool_registry() -> None:
    tool_root = Path(__file__).resolve().parents[1] / "app" / "tools"
    forbidden_fragments = (
        "subprocess.",
        "os.system",
        "os.popen",
        "Popen(",
        "check_output(",
        "shell=True",
        "create_subprocess",
    )

    for path in sorted(tool_root.glob("*.py")):
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, f"Forbidden execution fragment '{fragment}' found in {path}"
