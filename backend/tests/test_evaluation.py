from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from sqlmodel import Session, select

from app.db import session as db_session
from app.evaluation import calculate_evaluation_summary, generate_json_report, generate_markdown_report
from app.harness import get_scenarios, run_security_harness
from app.main import app
from app.models import EvaluationScore, SecurityHarnessResult


def build_test_engine(monkeypatch):
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)
    SQLModel.metadata.create_all(test_engine)
    return test_engine


def test_evaluation_summary_works_on_empty_db(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)

    with Session(test_engine) as session:
        summary = calculate_evaluation_summary(session)

    assert summary.harness_performance.total_scenarios == 0
    assert summary.agent_quality.total_agent_runs == 0
    assert summary.human_approval_enforcement.auto_executed_dangerous_actions == 0
    assert summary.tool_safety.arbitrary_shell_execution_present is False

    for value in (
        summary.scorecard.safety_score,
        summary.scorecard.grounding_score,
        summary.scorecard.tool_safety_score,
        summary.scorecard.watchdog_score,
        summary.scorecard.overall_score,
    ):
        assert 0.0 <= value <= 100.0


def test_evaluation_summary_works_after_harness_run(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)

    with Session(test_engine) as session:
        harness_run = run_security_harness(session, reset_demo_data=True)
        summary = calculate_evaluation_summary(session)

    assert summary.harness_performance.total_scenarios == len(get_scenarios())
    assert summary.harness_performance.latest_harness_run_id == harness_run.harness_run_id
    assert summary.harness_performance.pass_rate > 0
    assert summary.prompt_injection_resistance.prompt_injection_events > 0
    assert summary.prompt_injection_resistance.prompt_injection_scenarios_total > 0
    assert summary.tool_safety.flagged_tool_outputs > 0
    assert summary.tool_safety.dangerous_tool_attempts > 0
    assert summary.human_approval_enforcement.auto_executed_dangerous_actions == 0

    for value in (
        summary.scorecard.safety_score,
        summary.scorecard.grounding_score,
        summary.scorecard.tool_safety_score,
        summary.scorecard.watchdog_score,
        summary.scorecard.overall_score,
    ):
        assert 0.0 <= value <= 100.0


def test_reporters_include_required_sections(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)

    with Session(test_engine) as session:
        run_security_harness(session, reset_demo_data=True)
        summary = calculate_evaluation_summary(session)

    markdown_report = generate_markdown_report(summary)
    json_report = generate_json_report(summary)

    for section in (
        "# OpsGuard AI Safety Evaluation Report",
        "## Executive Summary",
        "## Scorecard",
        "## Harness Performance",
        "## Watchdog Policy Coverage",
        "## Prompt-Injection Resistance",
        "## Tool Safety",
        "## Agent Quality",
        "## Grounding/Evidence Quality",
        "## Human Approval Enforcement",
        "## Notable Safety Events",
        "## Limitations",
    ):
        assert section in markdown_report

    assert json_report["title"] == "OpsGuard AI Safety Evaluation Report"
    assert "scorecard" in json_report
    assert "metrics" in json_report
    assert json_report["metrics"]["harness_performance"]["total_scenarios"] == len(get_scenarios())


def test_evaluation_run_endpoint_triggers_harness_and_persists_score(monkeypatch) -> None:
    test_engine = build_test_engine(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/api/v1/evaluation/run",
        json={"run_harness_if_empty": True, "report_type": "full"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["persisted"] is True
    assert payload["summary"]["harness_performance"]["total_scenarios"] == len(get_scenarios())
    assert 0.0 <= payload["scorecard"]["overall_score"] <= 100.0

    with Session(test_engine) as session:
        harness_results = session.exec(select(SecurityHarnessResult)).all()
        evaluation_scores = session.exec(select(EvaluationScore)).all()

        assert harness_results
        assert len(evaluation_scores) == 1
        assert evaluation_scores[0].report_type == "full"
        assert evaluation_scores[0].summary_payload["harness_performance"]["total_scenarios"] == len(get_scenarios())


def test_evaluation_summary_report_and_scores_endpoints(monkeypatch) -> None:
    build_test_engine(monkeypatch)
    client = TestClient(app)

    run_response = client.post(
        "/api/v1/evaluation/run",
        json={"run_harness_if_empty": True, "report_type": "full"},
    )
    assert run_response.status_code == 200

    summary_response = client.get("/api/v1/evaluation/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert "scorecard" in summary_payload
    assert summary_payload["harness_performance"]["total_scenarios"] == len(get_scenarios())

    markdown_response = client.get("/api/v1/evaluation/report.md")
    assert markdown_response.status_code == 200
    assert markdown_response.headers["content-type"].startswith("text/markdown")
    assert "OpsGuard AI Safety Evaluation Report" in markdown_response.text

    json_response = client.get("/api/v1/evaluation/report.json")
    assert json_response.status_code == 200
    json_payload = json_response.json()
    assert json_payload["title"] == "OpsGuard AI Safety Evaluation Report"
    assert json_payload["metrics"]["harness_performance"]["total_scenarios"] == len(get_scenarios())

    scores_response = client.get("/api/v1/evaluation/scores")
    assert scores_response.status_code == 200
    scores_payload = scores_response.json()
    assert scores_payload["status"] == "ok"
    assert scores_payload["items"]


def test_no_shell_execution_in_evaluation_package() -> None:
    evaluation_root = Path(__file__).resolve().parents[1] / "app" / "evaluation"
    forbidden_fragments = (
        "subprocess.",
        "os.system",
        "os.popen",
        "Popen(",
        "check_output(",
        "shell=True",
        "create_subprocess",
    )

    for path in sorted(evaluation_root.glob("*.py")):
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, f"Forbidden execution fragment '{fragment}' found in {path}"
