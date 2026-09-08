const test = require("node:test");
const assert = require("node:assert/strict");
const { join } = require("node:path");
const root = process.env.OPSGUARD_TEST_BUILD_DIRECTORY;
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const { watchdogVerdict, recommendationLifecycle } = require(join(root, "lib/safety-status.js"));
const { ToolAttemptsPanel } = require(join(root, "components/dashboard/tool-attempts-panel.js"));
const { ToolCallsPanel } = require(join(root, "components/dashboard/tool-calls-panel.js"));
const { WatchdogFindingsPanel } = require(join(root, "components/dashboard/watchdog-findings-panel.js"));
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));
const attempt = (outcome, invoked) => ({id: "attempt-1", agent_run_id: "run-1", tool_name: "drain_node",
  origin: "api", outcome, validated: true, handler_invoked: invoked, requested_at: "2026-09-08T12:00:00Z",
  invoked_at: invoked ? "2026-09-08T12:00:01Z" : null, completed_at: "2026-09-08T12:00:02Z",
  input_snapshot: {node: "gpu-node-14"}, validated_target: {}, output_snapshot: {}, user_error: null});

test("watchdog verdict mapping accepts only exact enum values", () => {
  assert.deepEqual(watchdogVerdict("block"), {label: "Blocked by policy", tone: "critical"});
  assert.equal(watchdogVerdict("require_human_approval").label, "Human review required");
  assert.equal(watchdogVerdict("allow").label, "Policy permits review");
  assert.equal(watchdogVerdict("allow_with_warnings").label, "Review with policy warnings");
  for (const value of ["BLOCK", " allow ", "disallow", "not_blocked", "allowed", undefined]) {
    assert.equal(watchdogVerdict(value).label, "Policy verdict unavailable");
  }
});
test("denied request clearly states handler was never invoked", () => {
  const html = render(ToolAttemptsPanel, {attempts: [attempt("denied", false)]});
  assert.match(html, />Denied</); assert.match(html, /Handler invoked: no/);
  assert.match(html, /Invoked never/); assert.match(html, /Call attempt-1 · Run run-1/);
});
test("failed request retains independently observed handler invocation", () => {
  const html = render(ToolAttemptsPanel, {attempts: [attempt("failed", true)]});
  assert.match(html, />Failed</); assert.match(html, /Handler invoked: yes/); assert.doesNotMatch(html, /Invoked never/);
});
test("invoked without completion is presented as an incomplete attempt", () => {
  const html = render(ToolAttemptsPanel, {attempts: [{...attempt("invoked", true), completed_at: null}]});
  assert.match(html, /Completed not recorded/); assert.match(html, /Handler invoked: yes/);
});
test("historical tool call does not infer invocation from success status", () => {
  const html = render(ToolCallsPanel, {toolCalls: [{id: "old", tool_name: "search_logs", status: "executed",
    output: {}, input_args: {}, trust_level: "untrusted", injection_scan_result: "clean", created_at: "2026-01-01"}], isLoading: false});
  assert.match(html, /Handler invoked: unknown \(historical\)/);
});
test("candidate, policy-checked, and blocked artifacts have distinct exact labels", () => {
  for (const lifecycle of ["candidate", "pending_human_review", "blocked"]) {
    const html = render(WatchdogFindingsPanel, {recommendation: {lifecycle_state: lifecycle, watchdog_findings: [],
      watchdog_status: null, summary: "Proposal", proposed_actions: []}});
    assert.ok(html.includes(recommendationLifecycle(lifecycle)));
  }
  assert.match(recommendationLifecycle("candidate"), /not completed/);
  assert.match(recommendationLifecycle("pending_human_review"), /not approved/);
  assert.match(recommendationLifecycle("blocked"), /not valid/);
});
test("watchdog renders affected actions and explicit blocking/review flags", () => {
  const html = render(WatchdogFindingsPanel, {recommendation: {lifecycle_state: "blocked", watchdog_status: "block",
    watchdog_decision: {verdict: "block", blocking: true, mandatory_review: true, policy_version: "watchdog-policy-v3"},
    watchdog_findings: [{finding_id: "finding-1", policy_id: "dangerous_action_policy", title: "Disruptive intent",
      severity: "critical", status: "block", reason: "Unauthorized proposal", remediation: "Do not dispatch",
      affected_action_ids: ["action-1"], blocking: true, mandatory_review: true, evidence_refs: [], metadata: {}}]}});
  assert.match(html, /Affected actions: action-1/); assert.match(html, /Blocking: yes/);
  assert.match(html, /Mandatory review: yes/); assert.match(html, /watchdog-policy-v3/);
});
