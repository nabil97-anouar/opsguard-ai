from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agent.runner import create_agent_run
from app.agent.state import EvidenceItem
from app.db import session as db_session
from app.db.init_db import create_db_and_tables
from app.main import app
from app.models import Alert, Document, ToolCall, ToolExecutionAudit
from app.services.incident_schema import IncidentBundleInput
from app.services.demo_seed import seed_demo_data
from app.services.incident_bundles import recorded_bundle_for_run
from app.services.incident_reports import render_incident_markdown

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "incidents"


def example(name="normal-workload"):
    return json.loads((EXAMPLES / f"{name}.json").read_text())


@pytest.fixture
def client_db(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "deterministic")
    engine = db_session.build_engine(f"sqlite:///{tmp_path}/incidents.db")
    monkeypatch.setattr(db_session, "engine", engine)
    create_db_and_tables(engine)
    yield TestClient(app), engine
    engine.dispose()


def import_and_run(client, payload):
    imported = client.post("/api/v1/incidents/import", json=payload)
    assert imported.status_code == 201, imported.text
    response = client.post("/api/v1/agent/runs", json={"alert_id": imported.json()["alert_id"]})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "waiting_for_human", response.text
    return imported.json(), response.json()


@pytest.mark.parametrize("name,verdict", [
    ("normal-workload", "require_human_approval"),
    ("suspicious-activity", "require_human_approval"),
    ("insufficient-evidence", "block"),
    ("malicious-log", "block"),
])
def test_examples_run_without_seed_data_and_retain_observation_identity(client_db, name, verdict):
    client, engine = client_db
    original = example(name)
    imported, run = import_and_run(client, original)
    assert imported["observation_count"] == len(original["observations"])
    assert imported["trust_level"] == "untrusted"
    assert run["execution_kind"] == "incident_investigation"
    assert run["provenance"] == "executed"
    final = run["final_recommendation"]
    assert final["watchdog_status"] == verdict
    assert final["requires_human_approval"] is True
    observations = [item for item in final["evidence"] if item.get("observation_id")]
    assert len(observations) == len(original["observations"])
    assert len({item["observation_id"] for item in observations}) == len(observations)
    with Session(engine) as session:
        for recorded, submitted in zip(observations, original["observations"], strict=True):
            assert recorded["kind"] == "tool_output"
            assert recorded["source_type"] == "tool"
            assert recorded["trust_level"] == "untrusted"
            assert recorded["bundle_id"] == imported["bundle_id"]
            assert recorded["source"] == submitted["source"]
            assert recorded["timestamp_basis"] == "source_observation"
            assert datetime.fromisoformat(recorded["observed_at"].replace("Z", "+00:00")) == datetime.fromisoformat(submitted["observed_at"].replace("Z", "+00:00"))
            assert recorded["evidence_id"] == f"{run['agent_run_id']}:observation:{recorded['observation_id']}"
            tool = session.get(ToolCall, UUID(recorded["tool_call_id"]))
            assert tool.status == "executed"
            assert tool.handler_invoked is True
            assert tool.output == recorded["content"]
            assert tool.output["observation_id"] == recorded["observation_id"]
        assert len(session.exec(select(Alert)).all()) == 1
        assert session.exec(select(Document)).all() == []


@pytest.mark.parametrize("metadata_form", ["omitted", "null"])
def test_file_like_bundle_keeps_unknown_event_time_and_target_explicit(client_db, monkeypatch, metadata_form):
    client, engine = client_db
    payload = {
        "schema_version": "incident-bundle-v1",
        "incident": {"title": "Imported server.log", "description": "User supplied a log file.",
                     "severity": "warning", "source": "server.log"},
        "observations": [{"kind": "log", "source": "server.log", "message": "Worker finished its task."}],
    }
    if metadata_form == "null":
        payload["incident"].update(observed_at=None, node=None)
        payload["observations"][0].update(observed_at=None, node=None)
    monkeypatch.setattr("app.agent.nodes.retrieve_chunks", lambda *args, **kwargs: pytest.fail("Imported file retrieved global evidence"))
    before = datetime.now(UTC)
    imported, run = import_and_run(client, payload)
    after = datetime.now(UTC)
    evidence = run["final_recommendation"]["evidence"]
    assert len(evidence) == 2
    assert {item["timestamp_basis"] for item in evidence} == {"recorded"}
    assert all(before <= datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00")) <= after for item in evidence)
    alert = next(item for item in evidence if item["kind"] == "alert")
    observation = next(item for item in evidence if item.get("observation_id"))
    assert alert["content"]["raw_data"]["observed_at"] is None
    assert alert["content"]["raw_data"]["node"] is None
    assert observation["content"]["observation"]["observed_at"] is None
    assert observation["content"]["observation"]["node"] is None
    assert observation["summary"] == "Imported log observation from server.log; no node was supplied."
    gaps = run["final_recommendation"]["missing_evidence"]
    assert "Imported incident has no source event timestamp; the evidence timestamp records ingestion only." in gaps
    for field in ("source event timestamp", "node target"):
        assert f"Imported observations missing a {field}: {observation['observation_id']}. No value was inferred." in gaps
    assert "gpu-node-14" not in json.dumps(run)
    assert run["self_assessment"]["confidence_score"] == 0.2
    with Session(engine) as session:
        stored = session.get(Alert, UUID(imported["alert_id"])).raw_data["bundle"]
        assert stored["incident"]["observed_at"] is None
        assert stored["observations"][0]["observation"]["observed_at"] is None
        assert stored["observations"][0]["observation"]["node"] is None
        attempt = session.get(ToolExecutionAudit, UUID(observation["tool_call_id"]))
        recorded_time = datetime.fromisoformat(observation["observed_at"].replace("Z", "+00:00"))
        assert recorded_time.replace(tzinfo=None) == attempt.requested_at.replace(tzinfo=None)
    report_url = f"/api/v1/agent/runs/{run['agent_run_id']}/report"
    report = client.get(report_url + ".json")
    assert report.status_code == 200
    assert report.json()["evidence"] == evidence
    assert report.json()["source_bundle"]["incident"]["observed_at"] is None
    markdown = client.get(report_url + ".md").text
    assert "Recorded by OpsGuard (source event time unknown):" in markdown
    assert "Observed at source:" not in markdown
    assert client.get(report_url + ".json").content == report.content


def test_maximum_unknown_metadata_bundle_preserves_all_ids_and_bounded_gaps(client_db):
    client, _ = client_db
    payload = example()
    payload["incident"]["observed_at"] = None
    payload["observations"] = [{"kind": "log", "source": "events.log", "message": f"Event {index}"}
                               for index in range(32)]
    _, run = import_and_run(client, payload)
    evidence = [item for item in run["final_recommendation"]["evidence"] if item.get("observation_id")]
    assert len(evidence) == 32
    assert {item["timestamp_basis"] for item in evidence} == {"recorded"}
    gaps = run["final_recommendation"]["missing_evidence"]
    assert len(gaps) < 30
    time_gap = next(gap for gap in gaps if gap.startswith("Imported observations missing a source event timestamp:"))
    node_gap = next(gap for gap in gaps if gap.startswith("Imported observations missing a node target:"))
    for item in evidence:
        assert item["observation_id"] in time_gap
        assert item["observation_id"] in node_gap
        assert item["content"]["observation"]["node"] is None
        assert item["content"]["observation"]["observed_at"] is None


def test_source_event_time_is_preserved_independently_of_unknown_node(client_db):
    client, _ = client_db
    payload = example()
    payload["observations"] = [payload["observations"][0]]
    payload["observations"][0]["node"] = None
    payload["observations"][0]["observed_at"] = "2026-08-01T18:45:00+02:00"
    _, run = import_and_run(client, payload)
    evidence = run["final_recommendation"]["evidence"]
    assert {item["timestamp_basis"] for item in evidence} == {"source_observation"}
    item = next(item for item in evidence if item.get("observation_id"))
    assert datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00")) == datetime.fromisoformat("2026-08-01T18:45:00+02:00")
    assert item["content"]["observation"]["node"] is None
    markdown = client.get(f"/api/v1/agent/runs/{run['agent_run_id']}/report.md").text
    assert "Observed at source:" in markdown
    assert "Recorded by OpsGuard (source event time unknown):" not in markdown


def test_missing_observation_time_is_not_borrowed_from_alert(client_db):
    client, _ = client_db
    payload = example()
    payload["observations"] = [payload["observations"][0]]
    payload["observations"][0].pop("observed_at")
    _, run = import_and_run(client, payload)
    evidence = run["final_recommendation"]["evidence"]
    alert = next(item for item in evidence if item["kind"] == "alert")
    observation = next(item for item in evidence if item.get("observation_id"))
    assert alert["timestamp_basis"] == "source_observation"
    assert observation["timestamp_basis"] == "recorded"
    assert observation["content"]["observation"]["observed_at"] is None
    assert observation["observed_at"] != alert["observed_at"]


def test_legacy_evidence_without_timestamp_basis_remains_readable_without_inference(client_db):
    client, _ = client_db
    _, run = import_and_run(client, example())
    report = client.get(f"/api/v1/agent/runs/{run['agent_run_id']}/report.json").json()
    for item in report["evidence"]:
        item.pop("timestamp_basis")
        assert EvidenceItem.model_validate(item).timestamp_basis is None
    rendered = render_incident_markdown(report)
    assert "Stored timestamp (basis not recorded):" in rendered
    assert "Observed at source:" not in rendered
    assert "Recorded by OpsGuard (source event time unknown):" not in rendered


def test_fixture_hostname_collision_never_reads_mock_or_catalog_data(client_db, monkeypatch):
    client, engine = client_db
    seed_demo_data(reset=True)
    from app.tools import implementations
    from app.agent import nodes

    class NoFixtureAccess:
        def __iter__(self):
            pytest.fail("Imported incident accessed fixture observations")

        def get(self, *_):
            pytest.fail("Imported incident accessed fixture observations")

    for name in ("MOCK_LOG_ENTRIES", "MOCK_NODE_METRICS", "MOCK_RUNNING_JOBS", "MOCK_NETWORK_CONNECTIONS"):
        monkeypatch.setattr(implementations, name, NoFixtureAccess())
    monkeypatch.setattr(nodes, "retrieve_chunks", lambda *args, **kwargs: pytest.fail("Imported run retrieved global documents"))
    imported, run = import_and_run(client, example())
    text = json.dumps(run["final_recommendation"]).lower()
    assert "xmrig" not in text
    assert "crypto-mining" not in text
    assert "compromised training image" not in text
    assert {step["node_name"] for step in run["steps"]} == set(nodes.NODE_ORDER)
    tools = next(step["output_snapshot"] for step in run["steps"] if step["node_name"] == "execute_safe_tools")
    assert {item["tool_name"] for item in tools["tool_results"]} == {"read_incident_observation"}
    assert all(item["status"] == "succeeded" for item in tools["tool_results"])
    assert len(tools["evidence_items"]) == 4
    assert imported["alert_id"] != "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f"


@pytest.mark.parametrize("tool,arguments", [
    ("search_logs", {"query": "xmrig"}), ("get_node_metrics", {"node": "gpu-node-14"}),
    ("get_running_jobs", {"node": "gpu-node-14"}), ("check_network_connections", {"node": "gpu-node-14"}),
    ("query_past_incidents", {"query": "mining"}), ("retrieve_runbook", {"query": "gpu"}),
])
def test_direct_tool_api_cannot_bypass_imported_source_isolation(client_db, tool, arguments):
    client, engine = client_db
    _, run = import_and_run(client, example())
    response = client.post(f"/api/v1/tools/{tool}/execute", json={"agent_run_id": run["agent_run_id"], "input": arguments})
    assert response.status_code == 200
    assert response.json()["outcome"] == "denied"
    assert response.json()["handler_invoked"] is False
    assert response.json()["error_code"] == "imported_source_isolation"
    with Session(engine) as session:
        row = session.get(ToolExecutionAudit, UUID(response.json()["tool_call_id"]))
        assert row.handler_invoked is False


def test_missing_target_and_observations_are_explicit_gaps(client_db):
    client, _ = client_db
    _, run = import_and_run(client, example("insufficient-evidence"))
    final = run["final_recommendation"]
    assert {item["kind"] for item in final["evidence"]} == {"alert"}
    assert not any(item.get("observation_id") for item in final["evidence"])
    for kind in ("log", "metric", "job", "network"):
        assert f"No imported {kind} observations were supplied; no fixture or live data was substituted." in final["missing_evidence"]
    assert any("valid node" in gap for gap in final["missing_evidence"])
    assert "gpu-node-14" not in json.dumps(run)
    classification = next(step["output_snapshot"] for step in run["steps"] if step["node_name"] == "classify_alert")
    assert classification["infrastructure_type"] == "unknown"
    assert run["self_assessment"]["confidence_score"] == 0.2
    assert run["self_assessment"]["uncertainty_level"] == "high"


def test_malicious_observation_is_screened_and_never_authorizes_execution(client_db):
    client, _ = client_db
    _, run = import_and_run(client, example("malicious-log"))
    final = run["final_recommendation"]
    observed = [item for item in final["evidence"] if item.get("observation_id")]
    assert len(observed) == 1
    assert observed[0]["suspicious"] is True
    assert observed[0]["matched_patterns"]
    assert any(item["policy_id"] == "prompt_injection_policy" and item["blocking"] for item in final["watchdog_findings"])
    assert {item["action_type"] for item in final["proposed_actions"]} == {"review_evidence"}
    markdown = client.get(f"/api/v1/agent/runs/{run['agent_run_id']}/report.md")
    assert markdown.status_code == 200
    assert "````json" in markdown.text
    assert "IGNORE PREVIOUS INSTRUCTIONS" in markdown.text


@pytest.mark.parametrize("mutation", ["trust", "identity", "too_many", "naive_time", "naive_observation_time", "timestamp_basis", "string_metric", "invalid_ip", "too_long", "unknown_version", "unknown_kind", "blank_node"])
def test_invalid_import_is_rejected_without_persisting_records(client_db, mutation):
    client, engine = client_db
    payload = example()
    if mutation == "trust":
        payload["observations"][0]["trust_level"] = "trusted"
    elif mutation == "identity":
        payload["observations"][0]["observation_id"] = str(uuid4())
    elif mutation == "too_many":
        payload["observations"] = payload["observations"] * 9
    elif mutation == "naive_time":
        payload["incident"]["observed_at"] = "2026-09-22T12:00:00"
    elif mutation == "naive_observation_time":
        payload["observations"][0]["observed_at"] = "2026-09-22T12:00:00"
    elif mutation == "timestamp_basis":
        payload["observations"][0]["timestamp_basis"] = "source_observation"
    elif mutation == "string_metric":
        payload["observations"][1]["value"] = "90.0"
    elif mutation == "invalid_ip":
        payload["observations"][3]["remote_ip"] = "secret-sentinel-invalid"
    elif mutation == "too_long":
        payload["observations"][0]["message"] = "x" * 2001
    elif mutation == "unknown_version":
        payload["schema_version"] = "v99"
    elif mutation == "unknown_kind":
        payload["observations"][0]["kind"] = "shell"
    else:
        payload["observations"][0]["node"] = "   "
    response = client.post("/api/v1/incidents/import", json=payload)
    assert response.status_code == 422
    assert "secret-sentinel-invalid" not in response.text
    with Session(engine) as session:
        assert session.exec(select(Alert)).all() == []


def test_body_limit_applies_before_parsing_and_without_content_length(client_db):
    client, engine = client_db
    def chunks():
        for _ in range(17):
            yield b"x" * 65536
    response = client.post("/api/v1/incidents/import", content=chunks(), headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert client.post("/api/v1/incidents/import", content=b"{}", headers={"Content-Type": "text/plain"}).status_code == 415
    with Session(engine) as session:
        assert session.exec(select(Alert)).all() == []


def test_validation_errors_never_echo_unknown_field_names(client_db):
    client, _ = client_db
    payload = example()
    payload["Authorization: Bearer SECRET_FIELD_SENTINEL"] = True
    response = client.post("/api/v1/incidents/import", json=payload)
    assert response.status_code == 422
    assert "SECRET_FIELD_SENTINEL" not in response.text
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_redaction_expansion_is_validated_before_persistence(client_db):
    client, engine = client_db
    payload = example()
    payload["incident"]["source"] = "token=x " + "s" * 92
    assert len(payload["incident"]["source"]) == 100
    response = client.post("/api/v1/incidents/import", json=payload)
    assert response.status_code == 422
    with Session(engine) as session:
        assert session.exec(select(Alert)).all() == []


def test_serialized_unicode_budgets_prevent_provider_snapshot_overflow(client_db):
    client, engine = client_db
    rejected = example()
    rejected["incident"]["description"] = "漢" * 1600
    response = client.post("/api/v1/incidents/import", json=rejected)
    assert response.status_code == 422
    with Session(engine) as session:
        assert session.exec(select(Alert)).all() == []

    payload = example()
    payload["incident"]["description"] = "漢" * 500
    payload["observations"] = [payload["observations"][0]]
    observation = payload["observations"][0]
    observation.update(source="源" * 100, node="節" * 100, message="観" * 1700)
    assert len(json.dumps(observation, ensure_ascii=True).encode()) < 12000
    _, run = import_and_run(client, payload)
    recorded = next(item for item in run["final_recommendation"]["evidence"] if item.get("observation_id"))
    assert recorded["content"]["observation"]["message"] == observation["message"]
    assert run["final_recommendation"]["summary"].startswith("Review the imported incident using 1 recorded")


def test_every_bounded_observation_is_retained_not_silently_truncated(client_db):
    client, _ = client_db
    payload = example()
    payload["observations"] = [deepcopy(payload["observations"][0]) for _ in range(32)]
    for index, item in enumerate(payload["observations"]):
        item["message"] = f"Unique observation {index}: " + "x" * 1900
    _, run = import_and_run(client, payload)
    recorded = [item for item in run["final_recommendation"]["evidence"] if item.get("observation_id")]
    assert len(recorded) == 32
    assert [item["content"]["observation"]["message"] for item in recorded] == [item["message"] for item in payload["observations"]]
    assert "[TRUNCATED]" not in json.dumps(recorded)


def test_reports_and_bound_tool_reads_ignore_current_alert_documents_and_later_attempts(client_db):
    client, engine = client_db
    imported, run = import_and_run(client, example())
    run_id = run["agent_run_id"]
    json_path, markdown_path = f"/api/v1/agent/runs/{run_id}/report.json", f"/api/v1/agent/runs/{run_id}/report.md"
    original_json, original_md = client.get(json_path), client.get(markdown_path)
    assert original_json.status_code == original_md.status_code == 200
    report = original_json.json()
    assert report["schema_version"] == "incident-report-v1"
    assert len(report["evidence"]) == 5
    assert report["source_bundle"]["bundle_id"] == imported["bundle_id"]
    with Session(engine) as session:
        alert = session.get(Alert, UUID(imported["alert_id"]))
        alert.title = "Changed current alert"
        alert.raw_data = {"origin": "changed", "node": "unrelated"}
        session.add(alert)
        session.commit()
        recorded = recorded_bundle_for_run(session, UUID(run_id))
        assert recorded["incident"]["title"] == example()["incident"]["title"]
    client.post("/api/v1/tools/search_logs/execute", json={"agent_run_id": run_id, "input": {"query": "mining"}})
    import_and_run(client, example("suspicious-activity"))
    assert client.get(json_path).content == original_json.content
    assert client.get(markdown_path).content == original_md.content


def test_cross_bundle_observation_is_not_readable(client_db):
    client, _ = client_db
    _, first = import_and_run(client, example())
    _, second = import_and_run(client, example("malicious-log"))
    foreign_id = next(item["observation_id"] for item in second["final_recommendation"]["evidence"] if item.get("observation_id"))
    response = client.post("/api/v1/tools/read_incident_observation/execute", json={
        "agent_run_id": first["agent_run_id"], "input": {"observation_id": foreign_id}})
    assert response.status_code == 200
    assert response.json()["outcome"] == "failed"
    assert response.json()["output"] == {}


def test_empty_historical_report_stays_empty_and_running_report_is_unavailable(client_db, monkeypatch):
    client, engine = client_db
    imported = client.post("/api/v1/incidents/import", json=example()).json()
    with Session(engine) as session:
        run = create_agent_run(session, alert_id=UUID(imported["alert_id"]))
        run_id = str(run.id)
        assert client.get(f"/api/v1/agent/runs/{run_id}/report.json").status_code == 409
        run.status = "failed"
        run.completed_at = datetime.now(UTC)
        session.add(run)
        session.commit()
    monkeypatch.setattr("app.rag.retrieval.retrieve_chunks", lambda *args, **kwargs: pytest.fail("Export retrieved fresh context"))
    report = client.get(f"/api/v1/agent/runs/{run_id}/report.json")
    assert report.status_code == 200
    assert report.json()["evidence"] == []
    assert report.json()["incident"] is None
    assert report.json()["source_bundle"] is None
    assert report.json()["final_recommendation"] is None
    # A later direct API attempt may attach a synthetic audit step, but cannot
    # retroactively populate this empty historical investigation.
    client.post("/api/v1/tools/search_logs/execute", json={"agent_run_id": run_id, "input": {"query": "gpu"}})
    assert client.get(f"/api/v1/agent/runs/{run_id}/report.json").content == report.content
    assert client.get(f"/api/v1/agent/runs/{uuid4()}/report.json").status_code == 404


def test_credentials_redacted_before_import_persistence_and_openapi_has_no_dangling_refs(client_db):
    client, engine = client_db
    payload = example()
    payload["observations"][0]["message"] = "Authorization: Bearer SENTINEL_SUPER_SECRET"
    imported, run = import_and_run(client, payload)
    with Session(engine) as session:
        row = session.get(Alert, UUID(imported["alert_id"]))
        assert "SENTINEL_SUPER_SECRET" not in json.dumps(row.raw_data)
    assert "SENTINEL_SUPER_SECRET" not in json.dumps(run)
    schema = client.get("/openapi.json").json()["paths"]["/api/v1/incidents/import"]["post"]["requestBody"]
    assert "#/$defs" not in json.dumps(schema)


def test_all_published_example_copies_validate():
    files = list(EXAMPLES.glob("*.json"))
    assert len(files) == 4
    for file in files:
        IncidentBundleInput.model_validate_json(file.read_bytes())
        public = Path(__file__).resolve().parents[2] / "frontend" / "public" / "examples" / "incidents" / file.name
        if file.stem in {"normal-workload", "suspicious-activity"}:
            assert public.exists()
            assert json.loads(public.read_text()) == json.loads(file.read_text())
