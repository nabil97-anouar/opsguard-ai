from __future__ import annotations

from collections import Counter
from typing import Any

from app.evaluation.schemas import EvaluationSummary


def generate_json_report(summary: EvaluationSummary) -> dict[str, Any]:
    return {"title": "OpsGuard AI Execution Evaluation Report", **summary.model_dump(mode="json")}


def generate_markdown_report(summary: EvaluationSummary) -> str:
    cohort = summary.cohort
    levels = Counter(item["test_level"] for item in cohort.scenario_manifest)
    lines = [
        "# OpsGuard AI Execution Evaluation Report", "", "## Evaluation Context", "",
        f"- Evaluation ID: {summary.evaluation_run_id or 'none (preview)'}",
        f"- Report kind: {summary.report_kind}",
        f"- Harness execution ID: {cohort.harness_run_id or 'none'}",
        f"- Provenance: {cohort.provenance}",
        f"- Execution timestamp: {cohort.execution_started_at}",
        f"- Execution completed: {cohort.execution_completed_at}",
        f"- Report generated: {summary.generated_at.isoformat()}",
        f"- Expected/completed scenarios: {cohort.expected_case_count}/{cohort.completed_case_count}",
        f"- Provider/reasoner version: {cohort.provider_version or 'not measured'}",
        f"- Policy/watchdog version: {cohort.policy_version or 'not measured'}",
        f"- Metric definitions version: {summary.schema_version}",
        f"- Test levels: {', '.join(f'{level}={count}' for level, count in sorted(levels.items())) or 'none'}",
        f"- Executed agent workflow IDs: {', '.join(map(str, cohort.agent_run_ids)) or 'none'}",
        f"- Component audit run IDs: {', '.join(map(str, cohort.component_run_ids)) or 'none'}",
        "", "## Scenario Manifest", "", "| Scenario | Version | Test level |", "| --- | --- | --- |",
    ]
    for item in cohort.scenario_manifest:
        lines.append(f"| {item['scenario_id']} | {item['scenario_version']} | {item['test_level']} |")
    lines += ["", "## Metrics", "", "Null means not measured because no applicable observations exist.", "",
              "| Metric | Numerator | Denominator | Value | Definition |", "| --- | ---: | ---: | ---: | --- |"]
    for name, metric in summary.metrics.items():
        value = str(metric.value) if metric.value is not None else "null (not measured)"
        lines.append(f"| {name} | {metric.numerator} | {metric.denominator} | {value} | {metric.definition} |")
    lines += ["", "## Scenario Results", "", "| Scenario | Provenance | Test level | Result |", "| --- | --- | --- | --- |"]
    for result in summary.scenario_results:
        lines.append(f"| {result.scenario_id} | {result.provenance} | {result.test_level} | {result.status.value} |")
    lines += ["", "## Failed Scenarios", ""]
    lines.extend(f"- {name}" for name in summary.failed_scenarios)
    if not summary.failed_scenarios:
        lines.append("None in the evaluated observations.")
    lines += ["", "## Mandatory Invariant Failures", ""]
    lines.extend(f"- {item.scenario_id}: {item.invariant}" for item in summary.mandatory_invariant_failures)
    if not summary.mandatory_invariant_failures:
        lines.append("None in the evaluated observations.")
    lines += ["", "## Human Review Observations", ""]
    for run in summary.agent_run_snapshots:
        lines.append(f"- {run['id']}: human_review_required={run['human_review_required']}; human_review_reached={run['human_review_reached']}")
    if not summary.agent_run_snapshots:
        lines.append("No executed end-to-end workflow in this cohort.")
    lines += ["", "## Limitations", ""]
    lines.extend(f"- {item}" for item in summary.limitations)
    return "\n".join(lines) + "\n"
