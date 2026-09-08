from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select

from app.agent.runner import run_agent_for_alert
from app.db import session as db_session
from app.evaluation import calculate_evaluation_summary, create_evaluation_report
from app.evaluation.metrics import latest_executed_harness_run
from app.harness import run_security_harness
from app.main import app
from app.models import AgentStep, EvaluationReport, SecurityHarnessResult, SecurityHarnessRun
from app.services.demo_seed import demo_uuid, seed_demo_data


@pytest.fixture
def session(monkeypatch):
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as active_session:
        yield active_session
    engine.dispose()


def test_seeded_results_do_not_establish_an_execution(session):
    seed_demo_data()
    fixtures = session.exec(select(SecurityHarnessResult)).all()
    assert len(fixtures) == 6
    assert {row.provenance for row in fixtures} == {"fixture"}
    assert latest_executed_harness_run(session) is None
    summary = calculate_evaluation_summary(session)
    assert summary.cohort.provenance == "none"
    assert summary.cohort.expected_case_count == 0
    assert summary.metrics["scenario_pass_rate"].value is None
    with pytest.raises(ValueError, match="executed harness manifest"):
        calculate_evaluation_summary(session, harness_run_id=fixtures[0].harness_run_id)


def test_run_if_empty_executes_when_only_fixtures_exist(session):
    seed_demo_data()
    fixture_execution_ids = {row.harness_run_id for row in session.exec(select(SecurityHarnessResult)).all()}
    response = TestClient(app).post("/api/v1/evaluation/run", json={"run_harness_if_empty": True})
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["cohort"]["provenance"] == "executed"
    assert summary["cohort"]["harness_run_id"] not in {str(value) for value in fixture_execution_ids}
    assert summary["metrics"]["scenario_pass_rate"]["denominator"] == 9
    session.expire_all()
    assert len(session.exec(select(SecurityHarnessRun)).all()) == 1
    rows = session.exec(select(SecurityHarnessResult)).all()
    assert sum(row.provenance == "fixture" for row in rows) == 6
    assert sum(row.provenance == "executed" for row in rows) == 9


def test_explicit_cohort_cannot_be_replaced_by_newer_execution(session):
    first = run_security_harness(session, scenario_ids=["clean_safe_case"])
    second = run_security_harness(session, scenario_ids=["dangerous_tool_blocked"])
    summary = calculate_evaluation_summary(session, harness_run_id=first.harness_run_id)
    assert summary.cohort.harness_run_id == first.harness_run_id != second.harness_run_id
    assert [item["scenario_id"] for item in summary.cohort.scenario_manifest] == ["clean_safe_case"]
    assert [item.scenario_id for item in summary.scenario_results] == ["clean_safe_case"]
    assert summary.cohort.agent_run_ids == []
    assert summary.metrics["dangerous_tool_execution_rate"].denominator == 0
    assert summary.metrics["human_review_rate"].value is None


def test_unrelated_activity_and_current_versions_do_not_change_stored_exports(session, monkeypatch):
    execution = run_security_harness(session)
    summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)
    stored = create_evaluation_report(session, summary=summary)
    report_id = stored.id
    client = TestClient(app)
    json_url = f"/api/v1/evaluation/report.json?evaluation_run_id={report_id}"
    markdown_url = f"/api/v1/evaluation/report.md?evaluation_run_id={report_id}"
    original_json = client.get(json_url)
    original_markdown = client.get(markdown_url)
    assert original_json.status_code == original_markdown.status_code == 200
    run_agent_for_alert(session, alert_id=demo_uuid("alert:suspicious-gpu-usage"))
    newer = run_security_harness(session, scenario_ids=["dangerous_tool_blocked"])
    newer_summary = calculate_evaluation_summary(session, harness_run_id=newer.harness_run_id)
    create_evaluation_report(session, summary=newer_summary)
    monkeypatch.setattr("app.core.versions.PROVIDER_VERSION", "future-provider")
    monkeypatch.setattr("app.core.versions.POLICY_VERSION", "future-policy")
    monkeypatch.setattr("app.evaluation.reporter.generate_markdown_report", lambda _: "Changed renderer")
    assert client.get(json_url).content == original_json.content
    assert client.get(markdown_url).content == original_markdown.content
    payload = original_json.json()
    markdown = original_markdown.text
    assert payload["evaluation_run_id"] == str(report_id)
    assert payload["cohort"]["harness_run_id"] == str(execution.harness_run_id)
    for key in ("provider_version", "policy_version"):
        assert payload["cohort"][key] in markdown
    assert payload["schema_version"] == "evaluation-v2"
    assert "evaluation-v2" in markdown
    assert str(report_id) in markdown and str(execution.harness_run_id) in markdown
    for scenario in payload["cohort"]["scenario_manifest"]:
        assert f"| {scenario['scenario_id']} | {scenario['scenario_version']} | {scenario['test_level']} |" in markdown


def test_policy_cohort_does_not_claim_human_escalation_or_model_resistance(session):
    execution = run_security_harness(session, scenario_ids=["unsafe_action_recommendation"])
    summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)
    assert summary.cohort.agent_run_ids == []
    assert len(summary.cohort.component_run_ids) == 1
    assert summary.agent_run_snapshots == []
    assert summary.scenario_results[0].human_review_required is True
    assert summary.scenario_results[0].human_review_reached is None
    for name in ("human_review_rate", "evidence_reference_validity", "evidence_coverage",
                 "adversarial_invariant_preservation_rate", "dangerous_tool_execution_rate"):
        metric = summary.metrics[name]
        assert (metric.numerator, metric.denominator, metric.value) == (0, 0, None)
    assert set(summary.metrics) == {
        "scenario_completion_rate", "scenario_pass_rate", "mandatory_invariant_pass_rate",
        "adversarial_invariant_preservation_rate", "dangerous_tool_execution_rate", "human_review_rate",
        "evidence_reference_validity", "evidence_coverage",
    }
    assert "not escalation accuracy or usefulness" in " ".join(summary.limitations)
    assert "does not measure model-level prompt-injection" in " ".join(summary.limitations)


def test_evidence_metrics_count_references_and_ignore_self_invented_final_evidence(session):
    execution = run_security_harness(session, scenario_ids=["prompt_injection_in_retrieved_document"])
    workflow_id = execution.results[0].agent_run_id
    assert workflow_id is not None
    known = [
        {"evidence_id": "this-run:one", "citation": "alert://one"},
        {"evidence_id": "this-run:two", "citation": "tool://two"},
    ]
    hypotheses = [
        {"supporting_evidence": ["this-run:one", "other-run:invented"]},
        {"supporting_evidence": ["this-run:two"]},
        {"supporting_evidence": []},
    ]
    recommendation = {"summary": "Test references", "citations": ["alert://one", "tool://invented", "tool://two"],
        "evidence": [*known, {"evidence_id": "other-run:invented", "citation": "tool://invented"}]}
    for step in session.exec(select(AgentStep).where(AgentStep.agent_run_id == workflow_id)).all():
        payload = deepcopy(step.output_snapshot)
        if step.node_name in {"ingest_alert", "retrieve_context", "execute_safe_tools"}:
            payload["evidence_items"] = known if step.node_name == "ingest_alert" else []
        if step.node_name == "synthesize_hypotheses":
            payload["hypotheses"] = hypotheses
        if "final_recommendation" in payload:
            payload["final_recommendation"] = recommendation
        elif step.node_name == "generate_recommendation":
            payload = recommendation
        step.output_snapshot = payload
        session.add(step)
    session.commit()
    summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)
    validity = summary.metrics["evidence_reference_validity"]
    coverage = summary.metrics["evidence_coverage"]
    assert (validity.numerator, validity.denominator, validity.value) == (4, 6, 4 / 6)
    assert (coverage.numerator, coverage.denominator, coverage.value) == (1, 3, 1 / 3)


@pytest.mark.parametrize("raises_after_invocation", [False, True])
def test_dangerous_invocation_is_counted_even_with_corrupted_flags_or_handler_failure(
    session, monkeypatch, raises_after_invocation,
):
    from app.tools import registry

    original = registry.get_tool
    observed = []

    def destructive_handler(input_model, active_session, context):
        observed.append(input_model.node)
        if raises_after_invocation:
            raise RuntimeError("Failure after destructive handler entry")
        return {"status": "blocked", "reason": "Misleading response", "requires_human_approval": True}

    def corrupted_definition(name):
        definition = original(name)
        if name == "drain_node":
            return replace(definition, handler=destructive_handler, is_destructive=False, requires_human_approval=False)
        return definition

    monkeypatch.setattr(registry, "get_tool", corrupted_definition)
    execution = run_security_harness(session, scenario_ids=["dangerous_tool_blocked"])
    summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)
    assert observed == ["gpu-node-14"]
    assert summary.failed_scenarios == ["dangerous_tool_blocked"]
    assert summary.scenario_results[0].status == "failed"
    metric = summary.metrics["dangerous_tool_execution_rate"]
    assert (metric.numerator, metric.denominator, metric.value) == (1, 1, 1.0)
    assert summary.metrics["scenario_pass_rate"].numerator == 0
    assert "no_destructive_handler_invocation" in [failure.invariant for failure in summary.mandatory_invariant_failures]


def test_terminal_status_alone_does_not_establish_reached_review(session):
    execution = run_security_harness(session, scenario_ids=["prompt_injection_in_retrieved_document"])
    workflow_id = execution.results[0].agent_run_id
    review = session.exec(select(AgentStep).where(AgentStep.agent_run_id == workflow_id,
        AgentStep.node_name == "wait_for_human_approval")).one()
    review.status = "failed"
    session.add(review)
    session.commit()
    summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)
    metric = summary.metrics["human_review_rate"]
    assert (metric.numerator, metric.denominator, metric.value) == (0, 1, 0.0)
    assert summary.agent_run_snapshots[0]["human_review_required"] is True
    assert summary.agent_run_snapshots[0]["human_review_reached"] is False


def test_stored_snapshot_cannot_be_reused_as_an_overwrite(session):
    execution = run_security_harness(session, scenario_ids=["clean_safe_case"])
    summary = calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)
    report = create_evaluation_report(session, summary=summary)
    original = deepcopy(report.summary_payload)
    with pytest.raises(ValueError, match="cannot be overwritten"):
        create_evaluation_report(session, summary=summary)
    assert session.get(EvaluationReport, report.id).summary_payload == original


def test_unknown_and_incomplete_execution_ids_are_rejected(session):
    with pytest.raises(ValueError, match="executed harness manifest"):
        calculate_evaluation_summary(session, harness_run_id=uuid4())
    execution = run_security_harness(session, scenario_ids=["clean_safe_case"])
    manifest = session.get(SecurityHarnessRun, execution.harness_run_id)
    manifest.status = "running"
    session.add(manifest)
    session.commit()
    with pytest.raises(ValueError, match="has not completed"):
        calculate_evaluation_summary(session, harness_run_id=execution.harness_run_id)
    assert latest_executed_harness_run(session) is None
