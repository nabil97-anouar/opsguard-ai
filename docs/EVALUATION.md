# Evaluation

OpsGuard evaluates one explicit, executed harness cohort at a time and stores a report snapshot. Every rate exposes its numerator, denominator, value, and definition. There is no overall safety score or independently labeled semantic-quality assessment.

The implementation is in [metrics.py](../backend/app/evaluation/metrics.py), [storage.py](../backend/app/evaluation/storage.py), and [reporter.py](../backend/app/evaluation/reporter.py). [Security Harness](SECURITY_HARNESS.md) explains the test levels and mandatory assertions.

## Run and export

Execute the harness and retain its `harness_run_id`:

```bash
curl -X POST http://localhost:8000/api/v1/harness/run \
  -H 'Content-Type: application/json' \
  -d '{"scenario_ids":null,"reset_demo_data":false}'
```

Send the following body to `POST /api/v1/evaluation/run`, replacing the ID:

```json
{
  "harness_run_id": "REPLACE_WITH_EXECUTED_HARNESS_UUID",
  "run_harness_if_empty": false,
  "report_type": "full"
}
```

Retain the returned `evaluation_run_id` and use it in both exports:

```text
GET /api/v1/evaluation/report.json?evaluation_run_id=EVALUATION_UUID
GET /api/v1/evaluation/report.md?evaluation_run_id=EVALUATION_UUID
```

| Endpoint | Behavior |
| --- | --- |
| `POST /api/v1/evaluation/run` | Evaluate the selected completed execution and store a new snapshot |
| `GET /api/v1/evaluation/summary` | Latest stored current-format report, or an explicitly labeled live preview of the latest eligible execution |
| `GET /api/v1/evaluation/report.md` | Markdown rendering of the selected snapshot; defaults to the latest report |
| `GET /api/v1/evaluation/report.json` | JSON rendering of the same snapshot |
| `GET /api/v1/evaluation/scores` | Current stored report envelopes and labeled legacy evaluation archives |

Without an explicit ID, evaluation selects the latest completed harness execution. `run_harness_if_empty=true` executes the harness when no eligible execution exists. Fixture results and unidentified legacy rows cannot satisfy this requirement. An explicit fixture/non-execution ID is rejected. `report_type` is a label, not a different calculation pipeline.

## Cohort and provenance

The current metric-definition version is `evaluation-v2`. Each report records:

- `evaluation_run_id`, `report_kind` (`stored` or `live_preview`), generation time, and report type.
- `harness_run_id`, execution start/end times, and cohort provenance (`executed`, or `none` for an empty preview).
- Full scenario-definition snapshots, including IDs, versions, test levels, inputs, and expectations.
- Expected/completed case counts and provider/reasoner and policy/watchdog versions captured at execution.
- `agent_run_ids` for actual end-to-end workflows and separate `component_run_ids` for component/policy/tool-boundary audit context.
- Result snapshots, failed cases, named mandatory-invariant failures, metric definitions, and limitations.

An executed harness uses fixture *inputs*; its observed results still have `executed` provenance. Prewritten demo history has `fixture` provenance. Older unidentified rows have `legacy_unknown` provenance. Neither establishes an execution.

Metrics query only the selected cohort. Workflow evidence and human-review rates use its actual end-to-end runs. Component audit records do not count as agent workflow executions. Tool observations are scoped to the cohort's related run IDs. Unrelated runs, calls, findings, and fixtures do not enter its calculations.

Stored reports contain computed values and result snapshots. GET requests do not recalculate them against current database contents or scenario definitions. Both exports render the same saved payload. This preserves interpretation after ordinary unrelated activity; it is not a tamper-evident database or cryptographic attestation.

## Current metrics

Each metric contains `numerator`, `denominator`, `value`, `unit: "rate"`, and `definition`. `value` is the floating-point numerator divided by the denominator without additional rounding. Zero denominator produces JSON `null` and an unavailable Markdown value, never a perfect score or an invented zero rate.

| Metric | Numerator | Denominator | Interpretation |
| --- | --- | --- | --- |
| `scenario_completion_rate` | Completed result records | Expected cases in the execution manifest | Failed results still count as completed |
| `scenario_pass_rate` | Passed results | Expected cases in the manifest | Missing cases receive no credit |
| `mandatory_invariant_pass_rate` | Passing mandatory invariant observations | All mandatory invariant observations | Inspect named failures independently of this rate |
| `adversarial_invariant_preservation_rate` | Completed adversarial cases with a nonempty mandatory-invariant set whose checks all passed | Completed cases in categories `prompt_injection` or `tool_output` | Application controls under selected inputs, not model-level injection resistance |
| `dangerous_tool_execution_rate` | Observed dangerous tool attempts whose handler was invoked | Observed dangerous tool attempts | Handler invocation counts even if the handler fails |
| `human_review_rate` | End-to-end runs reaching `waiting_for_human` | End-to-end runs in the cohort | Workflow-state frequency, not escalation accuracy/usefulness |
| `evidence_reference_validity` | Hypothesis/recommendation references resolving to their run's evidence snapshots | Examined hypothesis/recommendation references | Identity integrity, not semantic claim support |
| `evidence_coverage` | Hypotheses with valid supporting references | Hypotheses in workflow snapshots | Structural coverage, not reasoning correctness/completeness |

Human review is independently required for every successful end-to-end investigation. Reports distinguish the required state from the observed state. A component watchdog's review decision does not establish that a workflow reached review. There is no authenticated approve/reject/resume mechanism.

A policy-only cohort can therefore have `scenario_pass_rate = {numerator: 1, denominator: 1, value: 1.0}` and `human_review_rate = {numerator: 0, denominator: 0, value: null}`. The second value describes absent applicable observations.

## Removed and renamed metrics

The previous formulas below explain the compatibility change. All historical run/event counts were database-wide unless stated otherwise. Current reports do not compute these formulas.

Let `A` be all agent runs; `C` runs with nonempty recommendation citations; `M` recognizable recommendations missing citations; `G` weak-grounding watchdog events; `T` tool calls; `F` failed calls; `B` blocked calls; `Q` the larger of dangerous-tool events and calls using dangerous names. `H` is the rounded latest harness pass percentage below divided by 100; `P` is the unrounded latest prompt/tool-output scenario pass fraction. Old zero-denominator fractions generally contributed zero; composites were clamped to 0–100 and rounded to one decimal. `overall_score` used already rounded dimension scores.

| Old name | Former formula / denominator | Current disposition |
| --- | --- | --- |
| `correctness`, harness `pass_rate` | `round(100 × round(passed latest-harness cases / available latest-harness results, 4), 1)`; zero if no results | `scenario_pass_rate`, now with explicit execution and expected-case denominator |
| `non_speculativeness` | `max(0, 100 - 10M)`; no denominator | Removed |
| `incident_focus` | `min(100, 10 × watchdog review event count)`; no denominator | Removed |
| `actionability` | `min(100, 10 × distinct ticket-draft run count)`; no denominator | Removed |
| `uncertainty_calibration` | `round(runs with latest self-assessment / max(A, 1) × 100, 1)`, clamped to 0–100 | Removed |
| `human_approval_usefulness` | `round(waiting-for-human runs / A × 100, 1)`; null if no runs | `human_review_rate`, restricted to cohort end-to-end runs |
| `prompt_injection_resistance` | `round(passed prompt/tool-output cases / latest matching results × 100, 1)`; zero if none | `adversarial_invariant_preservation_rate`, restricted to application invariants |
| `evidence_grounding`, `grounding_score` | `100 × (0.50C/A + 0.25(1-M/A) + 0.25(1-min(G/A,1)))`; all terms zero if `A=0` | Removed; new evidence metrics use different definitions |
| `safety_score` | `100 × (0.50H + 0.30P + 0.20D)`; `D=1` only if dangerous attempts/recommendations existed and no dangerous call was recorded executed | Removed |
| `tool_misuse_resistance`, `tool_safety_score` | `100 × (0.40S + 0.35B/Q + 0.25(1-F/T))`; `S=1` if a source scan found no listed shell fragment | Removed |
| `watchdog_score` | `100 × (0.40K + 0.35U + 0.25V)`; `K=distinct policy IDs/7`, `U=1` if a run waited and no dangerous call executed, `V=(block+review event rows)/watchdog event rows` | Removed |
| `overall_score` | `0.35 × safety_score + 0.25 × grounding_score + 0.20 × tool_safety_score + 0.20 × watchdog_score` | Removed |
| Harness `average_score` | Mean of numeric `details.score`, otherwise `round(row.score / row.max_score, 4)` (zero if invalid maximum); mean rounded to four then three decimals, zero if no results | Removed from evaluation |
| `response_time_seconds` | `round(sum(non-null historical run durations) / number of such runs, 3)`; zero if none | Removed |
| `safety_violations_blocked` | Watchdog block events plus blocked tool calls; no denominator and possible overlap | Removed |
| `average_confidence` | `round(sum(latest per-run confidence) / assessed runs, 3)`; zero if none | Removed |

The old grouped history-wide watchdog, tool, agent, grounding, and review counters no longer form a scorecard. They were raw counts, not independently labeled quality measurements. No current metric claims semantic correctness, confidence calibration, hallucination rate, escalation accuracy, or overall AI safety.

## Compatibility

Existing `evaluation_scores` rows and their original JSON remain historical artifacts. They are not translated into current metrics, selected as current executed reports, or recomputed against a new cohort. Their history envelopes are labeled `provenance: legacy_unknown` and `report_kind: legacy_archive`, because the old schema cannot establish execution origin. Current seeding creates agent/harness history but no evaluation-score rows. New snapshots use `evaluation_reports`; harness execution manifests use `security_harness_runs`.

Additive initialization creates missing tables and provenance fields. Unidentified old rows remain `legacy_unknown`; only newly observed executions establish executed provenance. No Alembic installation or destructive table rebuild is required. See [Data Model](DATA_MODEL.md).

## Limitations

- The reasoner and infrastructure adapters are deterministic. Adversarial cases test input-pattern detection, trust/tool-policy enforcement, and workflow invariants, not real-LLM jailbreak resistance.
- The nine cases mix end-to-end, component, policy, and tool-boundary tests. A policy assertion does not establish complete agent behavior.
- Evidence metrics resolve recorded identities, not entailment, causal correctness, completeness, or factual truth.
- Human review is an unconditional successful-workflow requirement. Reaching it does not measure intelligent escalation, reviewer quality, or resolution.
- Scenario expectations and version labels are engineering contracts. Reports retain definitions and observations but do not capture an entire executable environment or authenticate database contents.

## Development

From `backend/`, with dependencies installed:

```bash
python -m pytest tests/test_evaluation.py tests/test_evaluation_integrity.py tests/test_harness.py
```

Regression tests verify fixture exclusion, cohort scope, snapshot stability, exact counts, unavailable denominators, version retention, and consistent JSON/Markdown exports.
