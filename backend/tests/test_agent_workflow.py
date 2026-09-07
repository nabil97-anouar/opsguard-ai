from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agent.nodes import NODE_ORDER
from app.agent.runner import run_agent_for_alert
from app.db import session as db_session
from app.main import app
from app.models import AgentRun, Alert, SafetyEvent, SelfAssessment, TicketDraft, ToolCall
from app.services.demo_seed import demo_uuid, seed_demo_data

DANGEROUS_TOOL_NAMES = {"cancel_job", "drain_node", "block_user", "isolate_node", "disable_service"}


def build_seeded_engine(monkeypatch):
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)
    seed_demo_data(reset=True)
    return test_engine


def test_agent_run_on_demo_gpu_alert(monkeypatch) -> None:
    test_engine = build_seeded_engine(monkeypatch)

    with Session(test_engine) as session:
        result = run_agent_for_alert(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))

    assert result.status == "waiting_for_human"
    assert [step.node_name for step in result.steps] == list(NODE_ORDER)
    assert result.self_assessment is not None
    assert 0.45 < result.self_assessment.confidence_score < 1.0
    assert result.final_recommendation is not None
    assert result.final_recommendation.requires_human_approval is True
    assert any("chunk" in citation for citation in result.final_recommendation.citations)

    with Session(test_engine) as session:
        persisted_run = session.get(AgentRun, result.agent_run_id)
        tool_calls = session.exec(select(ToolCall).where(ToolCall.agent_run_id == result.agent_run_id)).all()
        assessments = session.exec(
            select(SelfAssessment).where(SelfAssessment.agent_run_id == result.agent_run_id)
        ).all()
        ticket_drafts = session.exec(
            select(TicketDraft).where(TicketDraft.agent_run_id == result.agent_run_id)
        ).all()

        assert persisted_run is not None
        assert persisted_run.status == "waiting_for_human"
        assert persisted_run.total_tool_calls >= 5
        assert tool_calls
        assert {"search_logs", "get_node_metrics", "get_running_jobs", "check_network_connections", "retrieve_runbook"} <= {
            tool_call.tool_name for tool_call in tool_calls
        }
        assert all(tool_call.tool_name not in DANGEROUS_TOOL_NAMES for tool_call in tool_calls)
        assert len(assessments) == 1
        assert ticket_drafts


def test_agent_run_on_prompt_injection_alert(monkeypatch) -> None:
    test_engine = build_seeded_engine(monkeypatch)

    with Session(test_engine) as session:
        result = run_agent_for_alert(session, alert_id=demo_uuid("alert:rag-prompt-injection"))

    assert result.status == "waiting_for_human"
    assert result.self_assessment is not None
    assert result.self_assessment.decision == "stop_and_request_human_review"
    assert result.self_assessment.uncertainty_level == "high"
    assert result.final_recommendation is not None
    combined_text = " ".join(
        [result.final_recommendation.summary, *result.final_recommendation.notes]
    ).lower()
    assert "prompt-injection" in combined_text or "untrusted" in combined_text
    assert any("untrusted" in note.lower() or "suspicious" in note.lower() for note in result.final_recommendation.notes)

    with Session(test_engine) as session:
        tool_calls = session.exec(select(ToolCall).where(ToolCall.agent_run_id == result.agent_run_id)).all()
        safety_events = session.exec(
            select(SafetyEvent).where(SafetyEvent.agent_run_id == result.agent_run_id)
        ).all()

        assert tool_calls
        assert all(tool_call.tool_name not in DANGEROUS_TOOL_NAMES for tool_call in tool_calls)
        assert any(tool_call.tool_name == "retrieve_runbook" for tool_call in tool_calls)
        assert any(event.event_type == "prompt_injection_detected" for event in safety_events)


def test_agent_run_on_unknown_alert_has_missing_evidence(monkeypatch) -> None:
    test_engine = build_seeded_engine(monkeypatch)

    with Session(test_engine) as session:
        unknown_alert = Alert(
            title="Mysterious telemetry anomaly on service-bus-9",
            severity="warning",
            source="custom-sensor",
            infrastructure_type="devops",
            raw_data={"description": "Intermittent signal drift without a known operational signature."},
            status="new",
            tags=["unknown", "telemetry"],
            is_demo=False,
        )
        session.add(unknown_alert)
        session.commit()
        session.refresh(unknown_alert)

        result = run_agent_for_alert(session, alert_id=unknown_alert.id)

    assert result.status == "waiting_for_human"
    assert result.self_assessment is not None
    assert result.self_assessment.missing_evidence
    assert result.self_assessment.confidence_score < 0.5


def test_agent_run_api_endpoints(monkeypatch) -> None:
    test_engine = build_seeded_engine(monkeypatch)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/agent/runs",
        json={"alert_id": str(demo_uuid("alert:suspicious-gpu-usage"))},
    )
    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["status"] == "waiting_for_human"
    assert [step["node_name"] for step in create_payload["steps"]] == list(NODE_ORDER)

    agent_run_id = create_payload["agent_run_id"]

    detail_response = client.get(f"/api/v1/agent/runs/{agent_run_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["agent_run_id"] == agent_run_id
    assert detail_payload["model_version"] == "deterministic-mock-v2"
    assert detail_payload["tool_calls"]
    assert detail_payload["final_recommendation"]["requires_human_approval"] is True

    list_response = client.get("/api/v1/agent/runs")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["status"] == "ok"
    assert any(item["agent_run_id"] == agent_run_id for item in list_payload["items"])

    with Session(test_engine) as session:
        persisted_run = session.get(AgentRun, UUID(agent_run_id))
        assert persisted_run is not None


def test_no_shell_execution_in_agent_package() -> None:
    agent_root = Path(__file__).resolve().parents[1] / "app" / "agent"
    forbidden_fragments = (
        "subprocess.",
        "os.system",
        "os.popen",
        "Popen(",
        "check_output(",
        "shell=True",
        "create_subprocess",
    )

    for path in sorted(agent_root.glob("*.py")):
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, f"Forbidden execution fragment '{fragment}' found in {path}"
