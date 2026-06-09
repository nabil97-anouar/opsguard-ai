from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db import session as db_session
from app.main import app
from app.models import Alert, AgentRun, AgentStep, Document, DocumentChunk, Incident, SafetyEvent, SecurityHarnessResult, SecurityHarnessTest
from app.services.demo_seed import seed_demo_data


def count_rows(session: Session, model: type) -> int:
    return len(session.exec(select(model)).all())


def test_demo_seed_endpoint_with_sqlite_fallback(monkeypatch) -> None:
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)

    client = TestClient(app)
    response = client.post("/api/v1/demo/seed", json={"reset": False})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["message"] == "demo data seeded"
    assert payload["summary"]["created"]["alerts"] == 4
    assert payload["summary"]["created"]["documents"] == 5
    assert payload["summary"]["created"]["document_chunks"] == 10
    assert payload["summary"]["created"]["agent_runs"] == 2
    assert payload["summary"]["created"]["agent_steps"] == 20
    assert payload["summary"]["created"]["incidents"] == 3
    assert payload["summary"]["created"]["security_harness_tests"] == 6
    assert payload["summary"]["created"]["security_harness_results"] == 6

    with Session(test_engine) as session:
        assert count_rows(session, Alert) == 4
        assert count_rows(session, Incident) == 3
        assert count_rows(session, Document) == 5
        assert count_rows(session, DocumentChunk) == 10
        assert count_rows(session, AgentRun) == 2
        assert count_rows(session, AgentStep) == 20
        assert count_rows(session, SecurityHarnessTest) == 6
        assert count_rows(session, SecurityHarnessResult) == 6

        poisoned_document = session.exec(
            select(Document).where(
                Document.trust_level == "untrusted",
                Document.injection_scan_result == "flagged",
            )
        ).first()
        assert poisoned_document is not None
        assert "Hidden Override" in poisoned_document.title

        prompt_injection_event = session.exec(
            select(SafetyEvent).where(SafetyEvent.event_type == "prompt_injection_detected")
        ).first()
        assert prompt_injection_event is not None


def test_demo_seed_is_idempotent(monkeypatch) -> None:
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)

    first_summary = seed_demo_data(reset=False)
    second_summary = seed_demo_data(reset=False)

    assert first_summary["created"]["alerts"] == 4
    assert second_summary["created"]["alerts"] == 0
    assert second_summary["skipped"]["alerts"] == 4
    assert second_summary["created"]["documents"] == 0
    assert second_summary["skipped"]["documents"] == 5
    assert second_summary["created"]["security_harness_results"] == 0
    assert second_summary["skipped"]["security_harness_results"] == 6

    with Session(test_engine) as session:
        assert count_rows(session, Alert) == 4
        assert count_rows(session, Document) == 5
        assert count_rows(session, SecurityHarnessResult) == 6


def test_demo_seed_reset_preserves_non_demo_data(monkeypatch) -> None:
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)

    seed_demo_data(reset=False)

    with Session(test_engine) as session:
        user_alert = Alert(
            title="User-created alert",
            severity="warning",
            source="manual",
            infrastructure_type="devops",
            raw_data={"note": "should survive demo reset"},
            status="new",
            tags=["user"],
            is_demo=False,
        )
        session.add(user_alert)
        session.commit()
        user_alert_id = user_alert.id

    reset_summary = seed_demo_data(reset=True)
    assert reset_summary["status"] == "ok"
    assert reset_summary["created"]["alerts"] == 4

    with Session(test_engine) as session:
        persisted_alert = session.get(Alert, user_alert_id)
        assert persisted_alert is not None
        assert persisted_alert.is_demo is False
        assert count_rows(session, Alert) == 5


def test_demo_seed_endpoint_is_blocked_in_production(monkeypatch) -> None:
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post("/api/v1/demo/seed", json={"reset": False})

    assert response.status_code == 403
