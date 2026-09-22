const assert = require("node:assert/strict");
const test = require("node:test");
const { join } = require("node:path");
const built = process.env.OPSGUARD_TEST_BUILD_DIRECTORY;
const { createRunSelectionGuard, selectedInvestigationReport, assertRunIdentity } = require(join(built, "lib/investigation-selection.js"));

function run(id, alert = `alert-${id}`) {
  return { agent_run_id: id, alert_id: alert, status: "waiting_for_human", completed_at: "2026-09-22T08:00:00Z",
    steps: [{ node_name: "ingest_alert", output_snapshot: { alert: { title: `Recorded title ${id}` } } }] };
}

test("choosing a file invalidates a pending automatic load and prevents later refresh from selecting old history", async () => {
  const guard = createRunSelectionGuard();
  const initial = guard.beginAutomatic();
  assert.equal(typeof initial, "number");
  let finish;
  const response = new Promise((resolve) => { finish = resolve; });
  let displayed = run("previous");
  const loading = response.then((detail) => { if (guard.commit(initial)) displayed = detail; });
  guard.begin();
  displayed = null;
  finish(run("background-old"));
  await loading;
  assert.equal(displayed, null);
  assert.equal(guard.beginAutomatic(), null);
  assert.equal(selectedInvestigationReport(displayed, false), null);
});

test("a stale historical selection cannot replace a newer imported investigation", async () => {
  const guard = createRunSelectionGuard();
  const historicalRequest = guard.begin();
  let finishHistory;
  const history = new Promise((resolve) => { finishHistory = resolve; });
  let selected = null;
  const loading = history.then((detail) => { if (guard.commit(historicalRequest)) selected = detail; });
  const importRequest = guard.begin();
  const current = run("new-import", "receipt-alert");
  if (guard.commit(importRequest)) selected = current;
  finishHistory(run("old-history"));
  await loading;
  assert.equal(selected, current);
  assert.deepEqual(selectedInvestigationReport(selected, false, "receipt-alert"), {
    runId: "new-import", alertId: "receipt-alert", incidentTitle: "Recorded title new-import",
    status: "waiting_for_human", scope: "imported",
  });
});

test("an explicitly selected older report remains available and refresh never switches it to latest", () => {
  const guard = createRunSelectionGuard();
  const request = guard.begin();
  assert.equal(guard.commit(request), true);
  assert.equal(guard.beginAutomatic(), null);
  const report = selectedInvestigationReport(run("older", "other-alert"), false, "current-import-alert");
  assert.equal(report.runId, "older");
  assert.equal(report.scope, "historical");
  assert.equal(report.incidentTitle, "Recorded title older");
});

test("pending, cleared, and unfinished selections never expose a previous report", () => {
  const previous = run("previous");
  assert.equal(selectedInvestigationReport(previous, true), null);
  assert.equal(selectedInvestigationReport(null, false), null);
  assert.equal(selectedInvestigationReport({ ...previous, completed_at: null }, false), null);
  assert.equal(selectedInvestigationReport({ ...previous, status: "running" }, false), null);
  const failed = { ...run("new-failed"), status: "failed" };
  const report = selectedInvestigationReport(failed, false);
  assert.equal(report.runId, "new-failed");
  assert.equal(report.status, "failed");
});

test("run identity checks require the exact requested run and imported alert", () => {
  assert.doesNotThrow(() => assertRunIdentity(run("r", "a"), { runId: "r", alertId: "a" }));
  assert.throws(() => assertRunIdentity(run("wrong", "a"), { runId: "r", alertId: "a" }), /No report was selected/);
  assert.throws(() => assertRunIdentity(run("r", "wrong"), { runId: "r", alertId: "a" }), /No report was selected/);
});
