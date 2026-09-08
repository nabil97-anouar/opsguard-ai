from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select

from app.db import session as db_session
from app.evaluation import calculate_evaluation_summary, generate_json_report, generate_markdown_report
from app.harness import get_scenarios, run_security_harness
from app.main import app
from app.models import EvaluationReport, EvaluationScore


def build_test_engine(monkeypatch):
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)
    SQLModel.metadata.create_all(test_engine)
    return test_engine


def test_evaluation_summary_works_on_empty_db(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)
    with Session(test_engine) as session:
        summary = calculate_evaluation_summary(session)

    assert summary.report_kind == "live_preview"
    assert summary.evaluation_run_id is None
    assert summary.cohort.provenance == "none"
    assert summary.cohort.expected_case_count == summary.cohort.completed_case_count == 0
    assert summary.cohort.agent_run_ids == []
    assert summary.scenario_results == []
    assert summary.metrics
    for metric in summary.metrics.values():
        assert (metric.numerator, metric.denominator, metric.value) == (0, 0, None)
        assert metric.definition
    assert "null (not measured)" in generate_markdown_report(summary)


def test_evaluation_summary_works_after_harness_run(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)
    with Session(test_engine) as session:
        execution = run_security_harness(session)
        summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)

    assert summary.cohort.harness_run_id == execution.harness_run_id
    assert summary.cohort.expected_case_count == summary.cohort.completed_case_count == len(get_scenarios()) == 9
    assert summary.metrics["scenario_pass_rate"].model_dump() == {
        "numerator": 9, "denominator": 9, "value": 1.0, "unit": "rate",
        "definition": "Cases passing every expectation and mandatory invariant / expected cases; missing cases cannot pass.",
    }
    assert (summary.metrics["dangerous_tool_execution_rate"].numerator,
            summary.metrics["dangerous_tool_execution_rate"].denominator) == (0, 1)
    assert (summary.metrics["human_review_rate"].numerator,
            summary.metrics["human_review_rate"].denominator) == (1, 1)
    assert summary.failed_scenarios == []
    assert summary.mandatory_invariant_failures == []


def test_reporters_include_context_metrics_and_limitations(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)
    with Session(test_engine) as session:
        execution = run_security_harness(session, scenario_ids=["clean_safe_case"])
        summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)

    markdown = generate_markdown_report(summary)
    report = generate_json_report(summary)
    for section in (
        "# OpsGuard AI Execution Evaluation Report", "## Evaluation Context", "## Scenario Manifest",
        "## Metrics", "## Scenario Results", "## Failed Scenarios", "## Mandatory Invariant Failures",
        "## Human Review Observations", "## Limitations",
    ):
        assert section in markdown
    assert report["title"] == "OpsGuard AI Execution Evaluation Report"
    assert report["cohort"]["harness_run_id"] == str(execution.harness_run_id)
    assert "scorecard" not in report
    assert report["metrics"]["human_review_rate"]["value"] is None
    assert "Numerator | Denominator | Value | Definition" in markdown


def test_evaluation_run_endpoint_triggers_execution_and_persists_report(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)
    client = TestClient(app)
    response = client.post("/api/v1/evaluation/run", json={"run_harness_if_empty": True, "report_type": "full"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["persisted"] is True
    assert payload["evaluation_run_id"] == payload["summary"]["evaluation_run_id"]
    assert payload["summary"]["cohort"]["provenance"] == "executed"
    assert payload["summary"]["report_kind"] == "stored"
    with Session(test_engine) as session:
        reports = session.exec(select(EvaluationReport)).all()
        assert len(reports) == 1
        assert session.exec(select(EvaluationScore)).all() == []
        assert reports[0].summary_payload["evaluation_run_id"] == payload["evaluation_run_id"]


def test_evaluation_summary_report_and_history_endpoints(monkeypatch) -> None:
    build_test_engine(monkeypatch)
    client = TestClient(app)
    response = client.post("/api/v1/evaluation/run", json={"run_harness_if_empty": True})
    assert response.status_code == 200
    evaluation_id = response.json()["evaluation_run_id"]
    summary = client.get("/api/v1/evaluation/summary")
    assert summary.status_code == 200
    assert summary.json()["evaluation_run_id"] == evaluation_id
    markdown = client.get(f"/api/v1/evaluation/report.md?evaluation_run_id={evaluation_id}")
    report = client.get(f"/api/v1/evaluation/report.json?evaluation_run_id={evaluation_id}")
    assert markdown.status_code == report.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert f"Evaluation ID: {evaluation_id}" in markdown.text
    assert report.json()["evaluation_run_id"] == evaluation_id
    history = client.get("/api/v1/evaluation/scores")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1
    assert history.json()["items"][0]["id"] == evaluation_id
    assert history.json()["items"][0]["provenance"] == "executed"
    assert history.json()["items"][0]["report_kind"] == "stored"


def test_no_shell_execution_in_evaluation_package() -> None:
    evaluation_root = Path(__file__).resolve().parents[1] / "app" / "evaluation"
    forbidden_fragments = ("subprocess.", "os.system", "os.popen", "Popen(", "check_output(", "shell=True", "create_subprocess")
    for path in sorted(evaluation_root.glob("*.py")):
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, f"Forbidden execution fragment '{fragment}' found in {path}"
