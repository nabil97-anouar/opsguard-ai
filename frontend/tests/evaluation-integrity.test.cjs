const assert = require("node:assert/strict");
const { join } = require("node:path");
const { test } = require("node:test");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const built = process.env.OPSGUARD_TEST_BUILD_DIRECTORY;
const { HarnessResultsPanel } = require(join(built, "components/dashboard/harness-results-panel.js"));
const { EvaluationSummaryCard } = require(join(built, "components/dashboard/evaluation-summary-card.js"));
const { AgentRunTrace } = require(join(built, "components/dashboard/agent-run-trace.js"));
const { executedHarnessRunId, harnessExecutionCounts } = require(join(built, "lib/dashboard-data.js"));
const { runEvaluation } = require(join(built, "lib/api.js"));

function result(provenance = "executed", overrides = {}) {
  return {
    scenario_id: "tool-boundary", scenario_version: "2", test_level: "tool_boundary",
    provenance, name: "Destructive handler boundary", category: "tool_policy",
    status: "passed", score: 1, observed_behavior: "Handler was not called.",
    expected_behavior: "No destructive handler invocation.", findings: [], safety_events: [],
    agent_run_id: null, tool_call_ids: [], watchdog_status: "blocked", failure_reason: null,
    injection_detected: false, action_blocked: true, harness_run_id: "harness-123",
    harness_result_id: `result-${provenance}`, created_at: "2026-09-08T12:00:00Z",
    mandatory_invariants: { no_destructive_handler_invocation: true }, invariant_failures: [], metadata: {},
    ...overrides,
  };
}

function harness(results = [result()]) {
  const executed = results.length > 0 && results.every((item) => item.provenance === "executed");
  return { status: executed ? "completed" : "not_executed", provenance: executed ? "executed" : "fixture", harness_run_id: "harness-123", total: results.length,
    completed_case_count: executed ? results.length : 0, expected_case_count: executed ? results.length : null,
    passed: results.filter((item) => item.status === "passed").length,
    failed: results.filter((item) => item.status === "failed").length,
    partial: results.filter((item) => item.status === "partial").length, results };
}

function report(overrides = {}) {
  return {
    schema_version: "evaluation-v2", report_kind: "stored", evaluation_run_id: "evaluation-123",
    generated_at: "2026-09-08T12:01:00Z", report_type: "full",
    cohort: {
      harness_run_id: "harness-123", provenance: "executed",
      execution_started_at: "2026-09-08T12:00:00Z", execution_completed_at: "2026-09-08T12:00:03Z",
      expected_case_count: 3, completed_case_count: 2,
      provider_version: "deterministic-reasoner-v2", policy_version: "watchdog-v2",
      agent_run_ids: ["agent-123"], component_run_ids: ["component-123"],
      scenario_manifest: [{ scenario_id: "tool-boundary", scenario_version: "2", test_level: "tool_boundary" }],
    },
    metrics: {
      scenario_pass_rate: { numerator: 1, denominator: 2, value: 0.5, unit: "rate", definition: "Passed / completed executed scenarios." },
      evidence_reference_validity: { numerator: 0, denominator: 0, value: null, unit: "rate", definition: "Resolved / recorded evidence references." },
    },
    scenario_results: [result()], failed_scenarios: ["tool-boundary"],
    mandatory_invariant_failures: [{ scenario_id: "tool-boundary", invariant: "no_destructive_handler_invocation" }],
    limitations: ["Local deterministic fixtures provide no semantic correctness ground truth."],
    ...overrides,
  };
}

function renderHarness(run) {
  return renderToStaticMarkup(React.createElement(HarnessResultsPanel, { harnessRun: run, scenarios: [], isLoading: false }));
}

function renderEvaluation(summary) {
  return renderToStaticMarkup(React.createElement(EvaluationSummaryCard, { summary, isLoading: false, isRunningEvaluation: false, onRunEvaluation() {} }));
}

test("harness runtime rendering visibly separates fixture and executed provenance and test levels", () => {
  const html = renderHarness(harness([result("fixture"), result()]));
  assert.match(html, /data-provenance="fixture"[^>]*>Fixture \/ example — not executed/);
  assert.match(html, /data-provenance="executed"[^>]*>Executed/);
  assert.match(html, /Test Level: Tool Boundary/);
  assert.match(html, /tool-boundary · version 2/);
  assert.match(html, /Harness record group ID: harness-123/);
  assert.doesNotMatch(html, />100%<|Safety score|Overall score/i);
  const fixture = renderHarness(harness([result("fixture")]));
  assert.match(fixture, /Completed \/ expected scenarios: 0 \/ unknown/);
  assert.match(fixture, /Not Executed/);
});

test("fixtures and unknown records cannot supply the displayed executed cohort or pass count", () => {
  for (const run of [null, harness([]), harness([result("fixture")]), harness([result("legacy_unknown")]), harness([result(), result("fixture")]), { ...harness(), provenance: "legacy_unknown" }, { ...harness(), status: "running" }]) {
    assert.equal(executedHarnessRunId(run), null);
    assert.equal(harnessExecutionCounts(run), "Not executed");
  }
  assert.equal(executedHarnessRunId(harness()), "harness-123");
  assert.equal(harnessExecutionCounts(harness()), "1 / 1");
});

test("harness mandatory invariant failures are rendered explicitly, including legacy partial records", () => {
  const html = renderHarness(harness([result("executed", {
    status: "failed", score: 0,
    mandatory_invariants: { no_destructive_handler_invocation: false },
    invariant_failures: ["no_destructive_handler_invocation"], failure_reason: "Forbidden handler invoked.",
  })]));
  assert.match(html, /Failed: no_destructive_handler_invocation/);
  assert.match(html, /no_destructive_handler_invocation: failed/);
  assert.match(html, /Forbidden handler invoked\./);
  const legacy = renderHarness(harness([result("legacy_unknown", { status: "partial", mandatory_invariants: {}, invariant_failures: [] })]));
  assert.match(legacy, /Legacy \/ unknown provenance — execution unverified/);
  assert.match(legacy, /Legacy partial result/);
  assert.match(legacy, /No observed mandatory-invariant checks recorded/);
});

test("evaluation renders exact cohort identity, versions, numerator, denominator and honest zero values", () => {
  const html = renderEvaluation(report());
  assert.match(html, /Stored evaluation report/);
  for (const value of ["evaluation-123", "harness-123", "deterministic-reasoner-v2", "watchdog-v2", "evaluation-v2", "2026-09-08T12:00:00Z", "tool_boundary: 1"]) assert.ok(html.includes(value), value);
  const rows = html.match(/<tr\b[^>]*>.*?<\/tr>/g);
  assert.match(rows[1], /scenario_pass_rate/);
  assert.match(rows[1], /<td[^>]*>1<\/td><td[^>]*>2<\/td><td[^>]*>0.5 \(50.0%\)<\/td>/);
  assert.match(rows[2], /evidence_reference_validity/);
  assert.match(rows[2], /<td[^>]*>0<\/td><td[^>]*>0<\/td><td[^>]*>N\/A — no applicable observations<\/td>/);
  assert.match(html, /tool-boundary: no_destructive_handler_invocation/);
  assert.match(html, /not escalation accuracy or approval usefulness/);
  assert.match(html, /not model-level prompt-injection resistance/);
});

test("both exports are pinned to the displayed stored evaluation ID", () => {
  const html = renderEvaluation(report());
  const exports = html.match(/href="[^"]+\/evaluation\/report\.(?:md|json)\?evaluation_run_id=evaluation-123"/g);
  assert.equal(exports.length, 2);
  const preview = renderEvaluation(report({ report_kind: "live_preview", evaluation_run_id: null }));
  assert.match(preview, /Live preview — no stored evaluation/);
  assert.doesNotMatch(preview, /href="[^"]+\/evaluation\/report/);
});

test("agent traces visibly mark example history as fixture provenance", () => {
  const html = renderToStaticMarkup(React.createElement(AgentRunTrace, {
    agentRun: { agent_run_id: "agent-fixture", alert_id: "alert", provenance: "fixture", status: "waiting_for_human", risk_level: "high", approval_status: "pending", steps: [], final_recommendation: null },
    activeScenarioLabel: null, isLoading: false,
  }));
  assert.match(html, /data-provenance="fixture"[^>]*>Fixture \/ example — not executed/);
});

test("evaluation API client submits the selected execution ID explicitly", async () => {
  const originalFetch = global.fetch;
  const calls = [];
  global.fetch = async (url, options) => {
    calls.push([url, JSON.parse(options.body)]);
    return { ok: true, headers: { get: () => "application/json" }, json: async () => ({ status: "ok", evaluation_run_id: "evaluation-123", summary: report() }) };
  };
  try {
    await runEvaluation(true, "full", executedHarnessRunId(harness()));
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0][1], { run_harness_if_empty: true, report_type: "full", harness_run_id: "harness-123" });
  } finally {
    global.fetch = originalFetch;
  }
});
