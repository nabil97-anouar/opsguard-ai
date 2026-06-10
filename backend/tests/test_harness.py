from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import session as db_session
from app.harness import get_scenarios, run_security_harness
from app.main import app
from app.models import AgentRun, SafetyEvent, SecurityHarnessResult, SecurityHarnessTest


def build_seeded_engine(monkeypatch):
    test_engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", test_engine)
    return test_engine


def test_harness_scenario_registry_contains_required_ids() -> None:
    scenarios = list(get_scenarios())
    scenario_ids = [scenario.scenario_id for scenario in scenarios]
    expected_ids = [
        "prompt_injection_in_retrieved_document",
        "prompt_injection_in_tool_output",
        "malicious_tool_feedback",
        "unsafe_action_recommendation",
        "unsupported_conclusion",
        "untrusted_context_reliance",
        "low_confidence_high_severity",
        "dangerous_tool_blocked",
        "clean_safe_case",
    ]

    assert scenario_ids == expected_ids
    assert len(scenario_ids) == len(set(scenario_ids))


def test_harness_runner_executes_all_scenarios_and_persists_results(monkeypatch) -> None:
    test_engine = build_seeded_engine(monkeypatch)

    with Session(test_engine) as session:
        result = run_security_harness(session, reset_demo_data=True)

    assert result.status == "completed"
    assert result.total == len(get_scenarios())
    assert result.total == result.passed + result.failed + result.partial

    results_by_id = {item.scenario_id: item for item in result.results}
    assert results_by_id["clean_safe_case"].status == "passed"
    assert results_by_id["dangerous_tool_blocked"].status == "passed"
    assert results_by_id["prompt_injection_in_retrieved_document"].status in {"passed", "partial"}

    with Session(test_engine) as session:
        persisted_results = session.exec(
            select(SecurityHarnessResult).where(SecurityHarnessResult.harness_run_id == result.harness_run_id)
        ).all()
        persisted_tests = session.exec(
            select(SecurityHarnessTest).where(
                SecurityHarnessTest.test_id.in_([scenario.scenario_id for scenario in get_scenarios()])
            )
        ).all()

        assert len(persisted_results) == len(get_scenarios())
        assert len(persisted_tests) == len(get_scenarios())
        assert {row.harness_run_id for row in persisted_results} == {result.harness_run_id}


def test_watchdog_oriented_harness_scenarios_trigger_expected_policies(monkeypatch) -> None:
    test_engine = build_seeded_engine(monkeypatch)
    selected = [
        "unsafe_action_recommendation",
        "unsupported_conclusion",
        "low_confidence_high_severity",
    ]

    with Session(test_engine) as session:
        result = run_security_harness(session, scenario_ids=selected, reset_demo_data=True)

    results_by_id = {item.scenario_id: item for item in result.results}

    unsafe_action = results_by_id["unsafe_action_recommendation"]
    unsupported = results_by_id["unsupported_conclusion"]
    low_confidence = results_by_id["low_confidence_high_severity"]

    assert unsafe_action.watchdog_status in {"require_human_approval", "block"}
    assert any(finding["policy_id"] == "dangerous_action_policy" for finding in unsafe_action.findings)

    assert unsupported.watchdog_status in {"allow_with_warnings", "require_human_approval", "block"}
    assert any(finding["policy_id"] == "weak_grounding_policy" for finding in unsupported.findings)

    assert low_confidence.watchdog_status in {"require_human_approval", "block"}
    assert any(
        finding["policy_id"] == "low_confidence_high_severity_policy"
        for finding in low_confidence.findings
    )


def test_prompt_injection_document_scenario_links_agent_run_and_safety_events(monkeypatch) -> None:
    test_engine = build_seeded_engine(monkeypatch)

    with Session(test_engine) as session:
        result = run_security_harness(
            session,
            scenario_ids=["prompt_injection_in_retrieved_document"],
            reset_demo_data=True,
        )

    scenario_result = result.results[0]
    assert scenario_result.agent_run_id is not None
    assert scenario_result.watchdog_status in {"require_human_approval", "block"}
    assert scenario_result.safety_events
    assert any(
        event["event_type"] == "prompt_injection_detected" or event["source"] == "watchdog"
        for event in scenario_result.safety_events
    )

    with Session(test_engine) as session:
        persisted_run = session.get(AgentRun, scenario_result.agent_run_id)
        persisted_events = session.exec(
            select(SafetyEvent).where(SafetyEvent.agent_run_id == scenario_result.agent_run_id)
        ).all()

        assert persisted_run is not None
        assert persisted_events


def test_harness_api_endpoints(monkeypatch) -> None:
    build_seeded_engine(monkeypatch)
    client = TestClient(app)

    scenarios_response = client.get("/api/v1/harness/scenarios")
    assert scenarios_response.status_code == 200
    scenarios_payload = scenarios_response.json()
    assert scenarios_payload["status"] == "ok"
    assert len(scenarios_payload["items"]) == len(get_scenarios())

    run_response = client.post(
        "/api/v1/harness/run",
        json={
            "scenario_ids": [
                "dangerous_tool_blocked",
                "clean_safe_case",
            ],
            "reset_demo_data": True,
        },
    )
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["status"] == "completed"
    assert run_payload["total"] == 2

    harness_run_id = run_payload["harness_run_id"]

    list_response = client.get("/api/v1/harness/results")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["status"] == "ok"
    assert any(item["harness_run_id"] == harness_run_id for item in list_payload["items"])

    detail_response = client.get(f"/api/v1/harness/results/{harness_run_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["status"] == "completed"
    assert detail_payload["harness_run_id"] == harness_run_id
    assert detail_payload["total"] == 2


def test_no_shell_execution_in_harness_package() -> None:
    harness_root = Path(__file__).resolve().parents[1] / "app" / "harness"
    forbidden_fragments = (
        "subprocess.",
        "os.system",
        "os.popen",
        "Popen(",
        "check_output(",
        "shell=True",
        "create_subprocess",
    )

    for path in sorted(harness_root.glob("*.py")):
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, f"Forbidden execution fragment '{fragment}' found in {path}"
