from __future__ import annotations

from sqlalchemy import inspect, text
from sqlmodel import Session, select

from app.db import session as db_session
from app.db.init_db import create_db_and_tables
from app.models import AgentRun, EvaluationReport, EvaluationScore, SecurityHarnessResult, SecurityHarnessRun
from app.services.demo_seed import demo_uuid, seed_demo_data


def test_additive_upgrade_preserves_legacy_rows_and_never_invents_execution(monkeypatch):
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    seed_demo_data()
    with Session(engine) as session:
        fixture = session.exec(select(AgentRun)).first()
        legacy = AgentRun(alert_id=fixture.alert_id, status="waiting_for_human", is_demo=True)
        session.add(legacy)
        session.flush()
        report = EvaluationScore(agent_run_id=legacy.id, correctness=84, summary_payload={"old": "unchanged"})
        session.add(report)
        session.commit()
        legacy_id, report_id = legacy.id, report.id
        legacy_payload = report.model_dump(mode="json")
    # Remove only v2 additions to reproduce a pre-milestone SQLite schema.
    EvaluationReport.__table__.drop(engine)
    SecurityHarnessRun.__table__.drop(engine)
    with engine.begin() as connection:
        for table, columns in {
            "agent_runs": ["provenance", "execution_kind", "provider_version", "policy_version"],
            "security_harness_results": ["provenance", "test_level", "scenario_version"],
        }.items():
            for column in columns:
                connection.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
    create_db_and_tables(engine)
    create_db_and_tables(engine)  # Upgrade is idempotent.
    assert "evaluation_reports" in inspect(engine).get_table_names()
    with Session(engine) as session:
        assert session.get(AgentRun, legacy_id).provenance == "legacy_unknown"
        assert session.get(AgentRun, legacy_id).execution_kind == "unknown"
        fixtures = session.exec(select(SecurityHarnessResult)).all()
        assert len(fixtures) == 6
        assert {row.provenance for row in fixtures} == {"fixture"}
        assert not session.exec(select(SecurityHarnessRun)).all()
        assert session.get(EvaluationScore, report_id).model_dump(mode="json") == legacy_payload
        assert not session.exec(select(EvaluationReport)).all()


def test_reset_with_foreign_keys_preserves_executed_input_alert(monkeypatch):
    from app.harness import run_security_harness
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    create_db_and_tables(engine)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    with Session(engine) as session:
        first = run_security_harness(session, scenario_ids=["prompt_injection_in_retrieved_document"])
        run_id = first.results[0].agent_run_id
        seed_demo_data(reset=True)
        session.expire_all()
        assert session.get(AgentRun, run_id).provenance == "executed"
        assert session.get(AgentRun, run_id).alert_id == demo_uuid("alert:rag-prompt-injection")


def test_agent_api_distinguishes_fixture_history_from_execution_on_demo_input(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    seed_demo_data()
    client = TestClient(app)
    history = client.get("/api/v1/agent/runs").json()["items"]
    assert len(history) == 2
    assert {run["provenance"] for run in history} == {"fixture"}
    assert {run["execution_kind"] for run in history} == {"fixture"}
    response = client.post("/api/v1/agent/runs", json={"alert_id": str(demo_uuid("alert:rag-prompt-injection"))})
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "waiting_for_human"
    assert run["provenance"] == "executed"
    assert run["execution_kind"] == "agent_workflow"
    assert run["provider_version"] == "deterministic-mock-v2"
    assert run["policy_version"] == "watchdog-policy-v3"
    detail = client.get(f"/api/v1/agent/runs/{run['agent_run_id']}").json()
    assert detail["provenance"] == "executed"
    assert detail["execution_kind"] == "agent_workflow"
    with Session(engine) as session:
        from uuid import UUID
        assert session.get(AgentRun, UUID(run["agent_run_id"])).is_demo is True
