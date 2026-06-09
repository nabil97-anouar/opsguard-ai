from __future__ import annotations

from sqlalchemy import inspect
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db import session as db_session
from app.main import app
from app.models import *  # noqa: F403,F401

EXPECTED_TABLES = {
    "agent_runs",
    "agent_steps",
    "alerts",
    "document_chunks",
    "documents",
    "evaluation_scores",
    "human_feedback",
    "incidents",
    "kill_chain_mappings",
    "safety_events",
    "security_harness_results",
    "security_harness_tests",
    "self_assessments",
    "ticket_drafts",
    "tool_calls",
}


def test_db_health_endpoint_with_sqlite_fallback(monkeypatch) -> None:
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)

    client = TestClient(app)
    response = client.get("/api/v1/db/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["latency_ms"] >= 0


def test_create_tables_endpoint_with_sqlite_fallback(monkeypatch) -> None:
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)

    client = TestClient(app)
    response = client.post("/api/v1/db/create-tables")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "created"
    assert set(payload["tables"]) == EXPECTED_TABLES
    assert set(inspect(test_engine).get_table_names()) == EXPECTED_TABLES


def test_create_tables_endpoint_is_blocked_in_production(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post("/api/v1/db/create-tables")

    assert response.status_code == 403
