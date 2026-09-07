from __future__ import annotations

from typing import Any

from app.evaluation.schemas import EvaluationSummary


def generate_json_report(summary: EvaluationSummary) -> dict[str, Any]:
    return {
        "title": "OpsGuard AI Safety Evaluation Report",
        "generated_at": summary.generated_at.isoformat(),
        "report_type": summary.report_type,
        "executive_summary": summary.executive_summary,
        "scorecard": summary.scorecard.model_dump(mode="json"),
        "metrics": {
            "harness_performance": summary.harness_performance.model_dump(mode="json"),
            "watchdog_coverage": summary.watchdog_coverage.model_dump(mode="json"),
            "prompt_injection_resistance": summary.prompt_injection_resistance.model_dump(mode="json"),
            "tool_safety": summary.tool_safety.model_dump(mode="json"),
            "agent_quality": summary.agent_quality.model_dump(mode="json"),
            "grounding_evidence": summary.grounding_evidence.model_dump(mode="json"),
            "human_approval_enforcement": summary.human_approval_enforcement.model_dump(mode="json"),
        },
        "latest_agent_run_id": str(summary.latest_agent_run_id) if summary.latest_agent_run_id else None,
        "latest_harness_run_id": str(summary.latest_harness_run_id) if summary.latest_harness_run_id else None,
        "notable_safety_events": [event.model_dump(mode="json") for event in summary.notable_safety_events],
        "limitations": list(summary.limitations),
        "disclaimer": "Scores describe the implemented local regression cases and heuristic calculations; they are not a general security rating.",
    }


def generate_markdown_report(summary: EvaluationSummary) -> str:
    scorecard = summary.scorecard
    harness = summary.harness_performance
    watchdog = summary.watchdog_coverage
    prompt = summary.prompt_injection_resistance
    tools = summary.tool_safety
    agent = summary.agent_quality
    grounding = summary.grounding_evidence
    approvals = summary.human_approval_enforcement

    notable_events = "\n".join(
        [
            (
                f"- `{event.severity}` `{event.event_type}` from `{event.source}`"
                f" on `{event.affected_component or 'n/a'}` at {event.created_at.isoformat()}"
            )
            for event in summary.notable_safety_events
        ]
    ) or "- No notable safety events were recorded."

    limitations = "\n".join([f"- {item}" for item in summary.limitations])

    return f"""# OpsGuard AI Safety Evaluation Report

Generated: {summary.generated_at.isoformat()}

## Executive Summary

{summary.executive_summary}

## Scorecard

| Dimension | Score |
| --- | ---: |
| Safety | {scorecard.safety_score:.1f} |
| Grounding | {scorecard.grounding_score:.1f} |
| Tool Safety | {scorecard.tool_safety_score:.1f} |
| Watchdog | {scorecard.watchdog_score:.1f} |
| Overall | {scorecard.overall_score:.1f} |

## Harness Performance

- Total scenarios: {harness.total_scenarios}
- Passed: {harness.passed}
- Partial: {harness.partial}
- Failed: {harness.failed}
- Pass rate: {harness.pass_rate:.1f}%
- Average score: {harness.average_score:.3f}
- Latest harness run ID: {harness.latest_harness_run_id}

## Watchdog Policy Coverage

- Total watchdog events: {watchdog.total_watchdog_events}
- Policies triggered: {", ".join(watchdog.policy_ids_triggered) if watchdog.policy_ids_triggered else "none"}
- Critical findings: {watchdog.critical_findings}
- High findings: {watchdog.high_findings}
- Warning findings: {watchdog.warning_findings}
- Block decisions: {watchdog.block_decisions}
- Require human approval decisions: {watchdog.require_human_approval_decisions}

## Prompt-Injection Resistance

- Prompt injection events: {prompt.prompt_injection_events}
- Unsafe tool output events: {prompt.unsafe_tool_output_events}
- Suspicious retrieval events: {prompt.suspicious_retrieval_events}
- Prompt-injection scenarios passed: {prompt.prompt_injection_scenarios_passed} / {prompt.prompt_injection_scenarios_total}

## Tool Safety

- Total tool calls: {tools.total_tool_calls}
- Blocked tool calls: {tools.blocked_tool_calls}
- Failed tool calls: {tools.failed_tool_calls}
- Flagged tool outputs: {tools.flagged_tool_outputs}
- Dangerous tool attempts: {tools.dangerous_tool_attempts}
- Arbitrary shell execution present: {tools.arbitrary_shell_execution_present}

## Agent Quality

- Total agent runs: {agent.total_agent_runs}
- Waiting for human runs: {agent.waiting_for_human_runs}
- Failed runs: {agent.failed_runs}
- Average confidence: {agent.average_confidence:.3f}
- Low-confidence high-severity count: {agent.low_confidence_high_severity_count}
- Runs with self-assessment: {agent.runs_with_self_assessment}
- Runs with ticket draft: {agent.runs_with_ticket_draft}

## Grounding/Evidence Quality

- Runs with citations: {grounding.runs_with_citations}
- Runs missing citations: {grounding.runs_missing_citations}
- Weak grounding events: {grounding.weak_grounding_events}
- Untrusted context events: {grounding.untrusted_context_events}

## Human Approval Enforcement

- Runs requiring human approval: {approvals.runs_requiring_human_approval}
- Dangerous recommendations requiring human approval: {approvals.dangerous_recommendations_requiring_human_approval}
- Auto-executed dangerous actions: {approvals.auto_executed_dangerous_actions}

## Notable Safety Events

{notable_events}

## Limitations

{limitations}

## Disclaimer

Scores describe the implemented local regression cases and heuristic calculations; they are not a general security rating.
"""
