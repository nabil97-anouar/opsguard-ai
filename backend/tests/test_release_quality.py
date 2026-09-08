from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import Settings
from app.db import session as db_session
from app.db.init_db import create_db_and_tables
from app.main import create_application
from app.models import AgentRun, AgentStep, Alert, ToolCall, ToolExecutionAudit
from app.services.demo_seed import demo_uuid, seed_demo_data
from app.tools import ToolExecutionContext, execute_tool

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("value,expected", [
    ('["http://localhost:3000", "https://example.test"]', ["http://localhost:3000", "https://example.test"]),
    (" http://localhost:3000, https://example.test ", ["http://localhost:3000", "https://example.test"]),
    ("", []),
])
def test_cors_environment_decoding(monkeypatch, value, expected):
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", value)
    assert Settings(_env_file=None).backend_cors_origins == expected


@pytest.mark.parametrize("value", ["*", "ftp://example.test", "https://user:secret@example.test", "http://localhost:3000/path", "[broken"])
def test_invalid_cors_fails_early_without_echoing_secret(monkeypatch, value):
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", value)
    with pytest.raises((ValidationError, ValueError)) as caught:
        Settings(_env_file=None)
    assert "user:secret" not in str(caught.value)


def test_unused_integration_settings_are_removed(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    settings = Settings(_env_file=None)
    assert not ({"llm_provider", "mock_llm", "qdrant_url", "openai_api_key", "anthropic_api_key", "secret_key", "postgres_password"} & type(settings).model_fields.keys())
    example = ROOT.joinpath(".env.example").read_text()
    assert "QDRANT" not in example and "OPENAI_API_KEY" not in example and "SECRET_KEY" not in example


@pytest.fixture
def database(monkeypatch, tmp_path):
    engine = db_session.build_engine(f"sqlite:///{tmp_path}/release.db")
    monkeypatch.setattr(db_session, "engine", engine)
    yield engine
    engine.dispose()


def test_liveness_is_independent_of_database_and_readiness_failure_is_redacted(database, monkeypatch):
    def unavailable(*_):
        raise RuntimeError("postgresql://user:TOPSECRET@host/database")
    monkeypatch.setattr(db_session, "check_database_connection", unavailable)
    client = TestClient(create_application())
    live = client.get("/api/v1/health")
    assert live.status_code == 200
    assert live.json()["check"] == "liveness"
    ready = client.get("/api/v1/ready")
    assert ready.status_code == 503
    assert ready.json()["database"] == "unavailable"
    assert "TOPSECRET" not in ready.text
    assert ready.headers["X-Request-ID"]


def test_readiness_requires_explicit_initialized_schema(database):
    client = TestClient(create_application())
    assert client.get("/api/v1/ready").json()["database"] == "schema_missing"
    create_db_and_tables(database)
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["reason"] is None
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE tool_calls DROP COLUMN handler_invoked"))
    assert client.get("/api/v1/ready").json()["database"] == "schema_missing"


def test_normal_requests_never_issue_ddl(database):
    seed_demo_data()
    statements = []
    @event.listens_for(database, "before_cursor_execute")
    def reject_ddl(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)
        assert not statement.lstrip().upper().startswith(("CREATE ", "ALTER ", "DROP "))
    client = TestClient(create_application())
    for path in ["ready", "documents", "tools", "agent/runs", "harness/results", "evaluation/summary"]:
        assert client.get(f"/api/v1/{path}").status_code == 200
    response = client.post("/api/v1/harness/run", json={"scenario_ids": ["clean_safe_case"]})
    assert response.status_code == 200
    assert response.json()["passed"] == 1
    assert statements


def test_sqlite_rejects_orphan_rows_on_every_connection(database):
    create_db_and_tables(database)
    for _ in range(2):
        with database.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        with Session(database) as session:
            session.add(AgentRun(alert_id=uuid4()))
            with pytest.raises(IntegrityError):
                session.commit()
        database.dispose()


def test_reset_retains_dependencies_and_previous_audit(database):
    seed_demo_data()
    owner = demo_uuid("agent-run:gpu-abuse")
    with Session(database) as session:
        result = execute_tool("get_node_metrics", {"node": "gpu-node-14"}, session, ToolExecutionContext(agent_run_id=owner))
        old = session.get(ToolExecutionAudit, result.tool_call_id).model_dump(mode="json")
        linked_alert = Alert(title="External back reference", severity="warning", source="manual",
            infrastructure_type="test", agent_run_id=owner)
        session.add(linked_alert)
        session.commit()
        external_id = linked_alert.id
    seed_demo_data(reset=True)
    with Session(database) as session:
        call = session.get(ToolCall, result.tool_call_id)
        assert call.agent_run_id == owner
        assert session.get(AgentStep, call.step_id) is not None
        assert session.get(Alert, external_id).agent_run_id == owner
        assert session.get(ToolExecutionAudit, result.tool_call_id).model_dump(mode="json") == old
        assert session.exec(text("PRAGMA foreign_key_check")).all() == []
        assert session.get(AgentRun, owner).provenance == "fixture"


def test_reset_is_atomic_if_reseeding_fails(database, monkeypatch):
    from app.services import demo_seed
    seed_demo_data()
    with Session(database) as session:
        before = {row.id for row in session.exec(select(Alert)).all()}
    monkeypatch.setattr(demo_seed, "upsert_record", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("failure")))
    with pytest.raises(RuntimeError, match="failure"):
        seed_demo_data(reset=True)
    with Session(database) as session:
        assert {row.id for row in session.exec(select(Alert)).all()} == before
        assert session.exec(text("PRAGMA foreign_key_check")).all() == []


def test_json_extractor_reads_pipeline_stdin_and_fails_clearly():
    command = [shutil.which("python3"), str(ROOT / "scripts/json_field.py"), "items.0.id"]
    result = subprocess.run(command, input='{"items":[{"id":"cohort-123"}]}', text=True, capture_output=True)
    assert result.returncode == 0 and result.stdout == "cohort-123\n"
    for value in ['{"items":[]}', 'malformed']:
        failure = subprocess.run(command, input=value, text=True, capture_output=True)
        assert failure.returncode != 0
        assert "Could not extract required JSON field" in failure.stderr
        assert "Traceback" not in failure.stderr
    subprocess.run(["bash", "-n", str(ROOT / "scripts/demo_walkthrough.sh")], check=True)


def test_unhandled_exception_is_correlated_without_leaking(database, caplog):
    application = create_application()
    @application.get("/test-failure")
    def fail():
        raise RuntimeError("password=TOPSECRET")
    response = TestClient(application).get("/test-failure")
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert "TOPSECRET" not in response.text + caplog.text


def test_compose_contract_when_cli_available():
    if not shutil.which("docker"):
        pytest.skip("Docker CLI unavailable; dedicated CI container job validates Compose")
    result = subprocess.run(["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "config", "--format", "json"], capture_output=True, text=True, check=True)
    config = json.loads(result.stdout)
    assert set(config["services"]) == {"postgres", "init", "backend", "frontend"}
    for service in config["services"].values():
        assert all(port["host_ip"] == "127.0.0.1" for port in service.get("ports", []))
    assert config["services"]["backend"]["depends_on"]["init"]["condition"] == "service_completed_successfully"
    assert "NEXT_PUBLIC_API_BASE_URL" in config["services"]["frontend"]["build"]["args"]
    assert "NEXT_PUBLIC_API_BASE_URL" not in config["services"]["frontend"].get("environment", {})


def test_python_audit_policy_does_not_ignore_unrated_findings():
    spec = importlib.util.spec_from_file_location("audit_python", ROOT / "scripts/audit_python.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for severity in ["critical", "high", "unknown"]:
        assert module.blocks(severity) is True
    for severity in ["low", "medium", "moderate"]:
        assert module.blocks(severity) is False
    assert module.advisory_severity({"id": "PYSEC-unknown"}, lambda _: {}) == "unknown"
    assert module.advisory_severity({"id": "PYSEC-1", "aliases": ["GHSA-one"]}, lambda _: {"severity": "high"}) == "high"


def test_workflow_error_summaries_hide_credentials_and_sql():
    from app.core.errors import error_summary
    from sqlalchemy.exc import OperationalError
    assert error_summary(RuntimeError('password="TOPSECRET"')) == "password=[REDACTED]"
    assert "TOPSECRET" not in error_summary(RuntimeError("postgresql://user:TOPSECRET@host/db"))
    assert error_summary(OperationalError("SELECT TOPSECRET", {}, RuntimeError("TOPSECRET"))) == "Database operation failed."


def test_validation_response_does_not_echo_request_body(database):
    client = TestClient(create_application())
    response = client.post("/api/v1/documents/ingest", json={"title": "Test", "source": "manual://test",
        "doc_type": "runbook", "content": "TOPSECRET", "trust_level": "untrusted",
        "metadata": {"trust_level": "trusted", "password": "TOPSECRET"}})
    assert response.status_code == 422
    assert "TOPSECRET" not in response.text
    assert all(set(item) <= {"loc", "type", "msg"} for item in response.json()["detail"])


def test_walkthrough_rejects_http_success_with_failed_investigation(tmp_path):
    import os
    import sys
    curl = tmp_path / "curl"
    curl.write_text(f"#!{sys.executable}\n" + '''import json, sys
url = next(value for value in sys.argv if value.startswith("http"))
if url.endswith("/ready"):
    print(json.dumps({"status": "ready"}))
elif url.endswith("/demo/seed"):
    print(json.dumps({"status": "ok"}))
elif url.endswith("/agent/runs"):
    print(json.dumps({"status": "failed", "agent_run_id": "failed-run"}))
else:
    sys.exit("Unexpected request after failed run")
''')
    curl.chmod(0o755)
    response = subprocess.run(["bash", str(ROOT / "scripts/demo_walkthrough.sh")],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}, capture_output=True, text=True)
    assert response.returncode == 1
    assert "Unexpected status: failed (expected waiting_for_human)" in response.stderr
