const assert = require("node:assert/strict");
const test = require("node:test");
const { join } = require("node:path");
const { readFileSync } = require("node:fs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const built = process.env.OPSGUARD_TEST_BUILD_DIRECTORY;
const { parseIncidentJson, importPreparedIncident, investigateImportedIncident, incidentDataDestination, providerLabel } = require(join(built, "lib/incident-import.js"));
const { apiErrorDetail } = require(join(built, "lib/api.js"));
const { investigationReportPath, recordedImportedEvidence, recordedRetrievalChunks, recordedIncidentTitle } = require(join(built, "lib/dashboard-data.js"));
const { IncidentImportCard } = require(join(built, "components/dashboard/incident-import-card.js"));
const { InvestigationReportLinks } = require(join(built, "components/dashboard/investigation-report-links.js"));
const { ImportedEvidencePanel } = require(join(built, "components/dashboard/imported-evidence-panel.js"));
const { SystemStatusCard } = require(join(built, "components/dashboard/system-status-card.js"));
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));
const bundle = {
  schema_version: "incident-bundle-v1",
  incident: { title: "Imported GPU workload", description: "Review current workload observations.", severity: "warning", source: "operator-export", observed_at: "2026-09-22T08:00:00Z", node: "test-node" },
  observations: [{ kind: "metric", source: "gpu-export", observed_at: "2026-09-22T08:00:00Z", node: "test-node", name: "gpu_utilization", value: 90, unit: "percent" }],
};
const receipt = { status: "imported", bundle_id: "bundle-original", alert_id: "alert-original", observation_count: 1, trust_level: "untrusted", imported_at: "2026-09-22T08:01:00Z" };
const cardProps = { imported: null, runtime: { provider: "institutional", model: "gpt-oss-120b", mode: "external", available: true }, disabled: false, isImporting: false, isRunning: false, onSelectionChange() {}, async onImport() {}, async onRun() {} };

function response(payload, status = 200) { return { ok: status < 400, status, headers: { get: () => "application/json" }, json: async () => payload }; }

test("incident bundle validation enforces limits and schema without echoing invalid input", () => {
  assert.deepEqual(parseIncidentJson(JSON.stringify(bundle)), bundle);
  assert.throws(() => parseIncidentJson("TOP-SECRET-NOT-JSON"), (error) => /not valid JSON/.test(error.message) && !error.message.includes("TOP-SECRET"));
  assert.throws(() => parseIncidentJson(JSON.stringify({ ...bundle, incident: { ...bundle.incident, description: "漢".repeat(400000) } })), /exceeds 1 MiB/);
  assert.throws(() => parseIncidentJson(JSON.stringify({ ...bundle, observations: Array.from({ length: 33 }, () => bundle.observations[0]) })), /at most 32/);
  assert.throws(() => parseIncidentJson(JSON.stringify({ ...bundle, schema_version: "other" })), /incident-bundle-v1/);
  assert.throws(() => parseIncidentJson(JSON.stringify({ ...bundle, observations: [{ kind: "shell" }] })), /kind must be log, metric, job, or network/);
});

test("import is one explicit request; a later run uses returned alert ID and never seeds", async () => {
  const originalFetch = global.fetch;
  const calls = [];
  const detail = { agent_run_id: "run-original", alert_id: receipt.alert_id, status: "waiting_for_human", steps: [], final_recommendation: { evidence: [] } };
  global.fetch = async (url, options) => {
    calls.push({ path: new URL(url).pathname, body: options.body ? JSON.parse(options.body) : null });
    if (calls.length === 1) return response(receipt, 201);
    if (calls.length === 2) return response({ agent_run_id: detail.agent_run_id });
    if (calls.length === 3) return response(detail);
    throw new Error("Unexpected extra network request");
  };
  try {
    const imported = await importPreparedIncident(bundle);
    assert.deepEqual(imported, receipt);
    assert.deepEqual(calls, [{ path: "/api/v1/incidents/import", body: bundle }]);
    assert.deepEqual(await investigateImportedIncident(imported), detail);
    assert.deepEqual(calls, [
      { path: "/api/v1/incidents/import", body: bundle },
      { path: "/api/v1/agent/runs", body: { alert_id: "alert-original" } },
      { path: "/api/v1/agent/runs/run-original", body: null },
    ]);
  } finally { global.fetch = originalFetch; }
});

test("failed import never starts an investigation and validation output cannot echo observations or secrets", async () => {
  const originalFetch = global.fetch;
  const calls = [];
  global.fetch = async (url) => {
    calls.push(url);
    return response({ detail: [{ loc: ["body", "observations", 0, "observed_at"], type: "timezone_aware", msg: "SECRET-LOG-CONTENT", input: "SECRET-INPUT", ctx: { secret: "SECRET-CONTEXT" } }] }, 422);
  };
  try {
    await assert.rejects(importPreparedIncident(bundle), (error) => {
      assert.match(error.message, /observations\.0\.observed_at: timestamp must include a timezone/);
      assert.doesNotMatch(error.message, /SECRET/);
      return true;
    });
    assert.equal(calls.length, 1);
    assert.match(calls[0], /\/incidents\/import$/);
  } finally { global.fetch = originalFetch; }
  assert.equal(apiErrorDetail({ detail: [null] }, 422), "Request validation failed. bundle: invalid value.");
  assert.doesNotMatch(apiErrorDetail({ detail: [{ loc: ["body", "SECRET-FIELD"], type: "__proto__", msg: "SECRET-MESSAGE" }] }, 422), /SECRET/);
});

test("run is disabled before import, and external destination is disclosed before a separate explicit run", () => {
  const before = render(IncidentImportCard, cardProps);
  const runButton = before.match(/<button[^>]*>.*?Run imported investigation<\/button>/g)?.at(-1);
  assert.ok(runButton);
  assert.match(runButton, /disabled=""/);
  assert.match(before, /Import alone does not call the model/);
  assert.match(before, /Institutional \/ gpt-oss-120b/);
  assert.match(before, /input[^>]*type="file"[^>]*accept="\.json,\.jsonl,\.ndjson,\.csv,\.txt,\.log,\.md,\.markdown,text\/plain,application\/json,text\/csv"/);
  assert.match(before, /synthetic example/);
  assert.match(before, /converts it to incident JSON in your browser/);
  assert.match(before, /No model is used for conversion/);
  const after = render(IncidentImportCard, { ...cardProps, imported: { bundle, receipt } });
  assert.match(after, /bundle-original/);
  assert.match(after, /alert-original/);
  assert.match(after, />Untrusted</);
  const buttons = after.match(/<button\b[^>]*>.*?<\/button>/g);
  assert.doesNotMatch(buttons.at(-1), /disabled=/);
});

test("historical investigation export URLs are pinned to the exact selected run", () => {
  assert.equal(investigationReportPath("json", "run-one"), "/agent/runs/run-one/report.json");
  assert.equal(investigationReportPath("md", "a/b?x=1"), "/agent/runs/a%2Fb%3Fx%3D1/report.md");
  assert.equal(render(InvestigationReportLinks, { selection: null }), "");
  const html = render(InvestigationReportLinks, { selection: {
    runId: "historical-run", alertId: "historical-alert", incidentTitle: "SSH authentication incident",
    status: "waiting_for_human", scope: "historical",
  } });
  assert.match(html, /href="[^\"]+\/agent\/runs\/historical-run\/report\.md"/);
  assert.match(html, /href="[^\"]+\/agent\/runs\/historical-run\/report\.json"/);
  assert.doesNotMatch(html, /latest|evaluation_run_id/);
  assert.match(html, /SELECTED HISTORICAL REPORT/);
  assert.match(html, /SSH authentication incident/);
  assert.match(html, /Run historical-run · Alert historical-alert · waiting_for_human/);
});

for (const mismatch of ["alert", "run"]) {
  test(`imported investigation rejects a returned ${mismatch} identity mismatch`, async () => {
    const originalFetch = global.fetch;
    let calls = 0;
    global.fetch = async () => {
      calls += 1;
      if (calls === 1) return response({ agent_run_id: "requested-run" });
      return response({ agent_run_id: mismatch === "run" ? "wrong-run" : "requested-run",
        alert_id: mismatch === "alert" ? "wrong-alert" : receipt.alert_id });
    };
    try {
      await assert.rejects(investigateImportedIncident(receipt), /does not match the requested incident or run/);
      assert.equal(calls, 2);
    } finally { global.fetch = originalFetch; }
  });
}

const observationEvidence = {
  evidence_id: "run-1:tool:call-1", kind: "tool_output", source_type: "tool", source: "original-export",
  tool_call_id: "call-1", bundle_id: "bundle-1", observation_id: "observation-1", document_id: null, chunk_id: null,
  retrieval_score: null, trust_level: "untrusted", observed_at: "2026-09-22T08:00:00Z",
  content: { bundle_id: "bundle-1", observation_id: "observation-1", observation: bundle.observations[0] },
  summary: "Imported GPU metric", citation: "tool://read_imported_observation/call-1", suspicious: false,
};
function runWithEvidence(evidence) { return { agent_run_id: "run-1", steps: [], final_recommendation: { evidence } }; }

test("imported evidence preserves observation identity and snapshot without becoming retrieved document context", () => {
  const detail = runWithEvidence([observationEvidence]);
  assert.deepEqual(recordedImportedEvidence(detail), [observationEvidence]);
  assert.deepEqual(recordedRetrievalChunks(detail), []);
  const html = render(ImportedEvidencePanel, { run: detail });
  for (const value of ["bundle-1", "observation-1", "call-1", "original-export", "2026-09-22T08:00:00Z", "gpu_utilization"]) assert.ok(html.includes(value), value);
  assert.match(html, /Exact observation snapshot/);
  assert.match(html, />Untrusted</);
  assert.match(html, /not independently verified/);
  assert.deepEqual(recordedImportedEvidence(runWithEvidence([])), []);
  assert.deepEqual(recordedImportedEvidence({ ...detail, final_recommendation: null }), []);
  assert.match(render(ImportedEvidencePanel, { run: runWithEvidence([]) }), /Historical evidence stays empty/);
  assert.deepEqual(recordedImportedEvidence(runWithEvidence([{ ...observationEvidence, observation_id: undefined }])), []);
});

test("imported historical title comes from its saved alert snapshot", () => {
  const detail = runWithEvidence([]);
  detail.steps = [{ node_name: "ingest_alert", output_snapshot: { alert: { title: "Original incident title" } } }];
  assert.equal(recordedIncidentTitle(detail), "Original incident title");
  assert.equal(recordedIncidentTitle(runWithEvidence([])), null);
});

test("provider labels are exact and local Ollama is never confused with deterministic or verified inference", () => {
  const cases = [["deterministic", "Deterministic", "local"], ["openai", "OpenAI", "external"], ["institutional", "Institutional", "external"], ["anthropic", "Claude / Anthropic", "external"], ["ollama", "Ollama", "local"]];
  for (const [provider, expected, mode] of cases) {
    assert.equal(providerLabel(provider), expected);
    const runtime = { provider, model: "selected-model", mode, configured: true, available: true, connectivity: provider === "deterministic" ? "local" : "not_checked" };
    const html = render(SystemStatusCard, { health: null, documentsCount: null, trustedDocumentsCount: null, executableToolsCount: null, blockedToolsCount: null, policiesCount: null, isLoading: false, reasoning: runtime });
    assert.ok(html.includes(expected));
    if (provider === "deterministic") assert.match(html, /LOCAL REASONING READY/);
    else { assert.match(html, /CONFIGURED \/ INFERENCE NOT CHECKED/); assert.doesNotMatch(html, /LOCAL REASONING READY|Deterministic local reasoning/); }
    const notice = incidentDataDestination(runtime);
    if (provider === "ollama") assert.match(notice, /backend's configured local endpoint/);
    else if (provider === "deterministic") assert.match(notice, /No model-service request/);
    else assert.match(notice, /Redact secrets/);
  }
  assert.equal(providerLabel("anthropic_extra"), "Unavailable");
  assert.equal(providerLabel("constructor"), "Unavailable");
});

test("sample launches require explicit seeding and imported investigation is the primary workspace action", () => {
  const source = readFileSync(join(__dirname, "../components/dashboard/dashboard-shell.tsx"), "utf8");
  const handler = source.slice(source.indexOf("async function handleRunScenario"), source.indexOf("async function handleImportIncident"));
  assert.doesNotMatch(handler, /seedDemoData\(/);
  assert.match(handler, /Select Seed sample data explicitly/);
  assert.match(source, /Import incident evidence/);
});

test("downloadable synthetic examples match the backend-validated repository examples", () => {
  for (const name of ["normal-workload.json", "suspicious-activity.json"]) {
    const publicText = readFileSync(join(__dirname, "../public/examples/incidents", name), "utf8");
    const sourceText = readFileSync(join(__dirname, "../../examples/incidents", name), "utf8");
    assert.equal(publicText, sourceText);
    const example = parseIncidentJson(publicText);
    assert.equal(example.schema_version, "incident-bundle-v1");
    assert.ok(example.observations.length > 0);
    assert.equal(example.incident.source, "sanitized-example");
  }
});


test("unknown event time remains null in an accepted bundle and is not displayed as a source timestamp", () => {
  const unknown = { ...bundle, incident: { ...bundle.incident, observed_at: null }, observations: [{ kind: "log", source: "export.log", message: "Workload started", node: null, observed_at: null }] };
  assert.deepEqual(parseIncidentJson(JSON.stringify(unknown)), unknown);
  const html = render(ImportedEvidencePanel, { run: runWithEvidence([{ ...observationEvidence, timestamp_basis: "recorded", content: { observation: unknown.observations[0] } }]) });
  assert.match(html, /Recorded at · event time unknown/);
  assert.doesNotMatch(html, /<dt>Observed<\/dt>/);
  assert.match(html, /not an inferred event time/);
});

test("local conversion remains available without a backend while import and investigation stay disabled", () => {
  const html = render(IncidentImportCard, { ...cardProps, backendAvailable: false, runtime: null });
  const input = html.match(/<input[^>]+type="file"[^>]*>/)[0];
  assert.doesNotMatch(input, /disabled=/);
  assert.match(html, /You can convert and download locally/);
  for (const button of html.match(/<button\b[^>]*>.*?<\/button>/g)) assert.match(button, /disabled=""/);
});
