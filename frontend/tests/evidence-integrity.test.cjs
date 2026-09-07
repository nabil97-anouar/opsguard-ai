const assert = require("node:assert/strict");
const { join } = require("node:path");
const { test } = require("node:test");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const built = process.env.OPSGUARD_TEST_BUILD_DIRECTORY;
const { safetyBadgeTone } = require(join(built, "lib/safety-status.js"));
const { loadRecordedAgentRun, recordedRetrievalChunks, toolRegistryGroups } = require(join(built, "lib/dashboard-data.js"));
const { ToolRegistryGroups } = require(join(built, "components/dashboard/tool-registry-groups.js"));

for (const [value, expected] of [
  ["trusted", "success"], ["untrusted", "warning"], ["quarantined", "critical"],
  ["allow", "success"], ["allow_with_warnings", "warning"], ["blocked", "critical"],
  ["require_human_approval", "warning"], ["succeeded", "success"],
  ["untrusted_source", "neutral"], ["allow_unknown", "neutral"], ["constructor", "neutral"]
]) {
  test(`exact status mapping: ${value}`, () => assert.equal(safetyBadgeTone(value), expected));
}

function run(evidence, steps = []) {
  return {
    agent_run_id: "historical-run", alert_id: "909d28d2-5c9f-5fa2-a35e-f6b39c95f83f",
    status: "waiting_for_human", steps,
    final_recommendation: evidence === null ? null : { evidence }
  };
}

test("loading an empty historical fixture run reads only that run, with no fresh retrieval", async () => {
  const calls = [];
  const originalFetch = global.fetch;
  global.fetch = async (...args) => {
    calls.push(["unexpected fetch", ...args]);
    throw new Error("Historical evidence must not query a live source");
  };
  try {
    const detail = run([]);
    const view = await loadRecordedAgentRun("historical-run", async (id) => {
      calls.push(["run detail", id]);
      return detail;
    });
    assert.equal(view.detail, detail);
    assert.deepEqual(view.chunks, []);
    assert.deepEqual(calls, [["run detail", "historical-run"]]);
  } finally {
    global.fetch = originalFetch;
  }
});

const evidence = {
  evidence_id: "evidence-at-run-time", kind: "retrieval", source_type: "document", source: "runbook://gpu",
  document_id: "document-at-run-time", chunk_id: "chunk-at-run-time", tool_call_id: null,
  retrieval_score: 2.5, trust_level: "untrusted", content: "Original runbook text.",
  observed_at: "2026-01-01T12:00:00Z", summary: "Original runbook text.",
  citation: "document-at-run-time#chunk-at-run-time", suspicious: true,
  title: "Original title", chunk_index: 2, doc_type: "runbook", matched_patterns: ["instruction_override"], risk_level: "high"
};

test("canonical historical evidence retains exact identity, content, trust, score and time", () => {
  assert.deepEqual(recordedRetrievalChunks(run([evidence])), [{
    evidence_id: "evidence-at-run-time", observed_at: "2026-01-01T12:00:00Z",
    document_id: "document-at-run-time", chunk_id: "chunk-at-run-time", title: "Original title", source: "runbook://gpu",
    chunk_index: 2, trust_level: "untrusted", doc_type: "runbook", score: 2.5,
    content_excerpt: "Original runbook text.", citation: "document-at-run-time#chunk-at-run-time",
    is_suspicious: true, matched_patterns: ["instruction_override"], risk_level: "high"
  }]);
});

test("explicit empty canonical evidence does not repopulate from other snapshots", () => {
  const stale = recordedRetrievalChunks(run([evidence]))[0];
  assert.deepEqual(recordedRetrievalChunks(run([], [{ node_name: "retrieve_context", output_snapshot: { results: [stale] } }])), []);
});

test("legacy run displays only validated persisted retrieval snapshots", () => {
  const stored = recordedRetrievalChunks(run([evidence]))[0];
  const legacy = run([{ kind: "retrieval", summary: "Older evidence format" }], [{
    node_name: "retrieve_context", output_snapshot: { results: [stored, { chunk_id: "incomplete" }] }
  }]);
  assert.deepEqual(recordedRetrievalChunks(legacy), [stored]);
  assert.deepEqual(recordedRetrievalChunks(run(null)), []);
});

test("tool observations do not become document retrieval entries", () => {
  assert.deepEqual(recordedRetrievalChunks(run([{ ...evidence, kind: "tool_output", source_type: "tool", tool_call_id: "call-1" }])), []);
});

test("executable adapters and blocked definitions render in separate labeled sections", () => {
  const tools = [
    { name: "search_logs", executable: true, is_destructive: false, requires_human_approval: false },
    { name: "drain_node", executable: false, is_destructive: true, requires_human_approval: true }
  ];
  const groups = toolRegistryGroups(tools);
  assert.deepEqual(groups.map((group) => [group.label, group.tools.map((tool) => tool.name)]), [
    ["Executable local adapters", ["search_logs"]], ["Blocked action definitions", ["drain_node"]]
  ]);
  const html = renderToStaticMarkup(React.createElement(ToolRegistryGroups, { tools }));
  const sections = html.match(/<section\b[^>]*>.*?<\/section>/g);
  assert.equal(sections.length, 2);
  assert.match(sections[0], /aria-label="Executable local adapters"/);
  assert.match(sections[0], /search_logs/);
  assert.doesNotMatch(sections[0], /drain_node/);
  assert.match(sections[1], /aria-label="Blocked action definitions"/);
  assert.match(sections[1], /drain_node/);
  assert.doesNotMatch(sections[1], /search_logs/);
});

test("unknown or contradictory execution capability is never presented as executable", () => {
  const tools = [
    { name: "unknown_capability", is_destructive: false, requires_human_approval: false },
    { name: "destructive_mismatch", executable: true, is_destructive: true, requires_human_approval: false },
    { name: "approval_mismatch", executable: true, is_destructive: false, requires_human_approval: true },
    { name: "unknown_approval", executable: true, is_destructive: false }
  ];
  const groups = toolRegistryGroups(tools);
  assert.deepEqual(groups[0].tools, []);
  assert.deepEqual(groups[1].tools, tools);
});
