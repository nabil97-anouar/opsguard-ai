const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join, resolve } = require("node:path");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const root = process.env.OPSGUARD_TEST_BUILD_DIRECTORY;
const projectRoot = resolve(__dirname, "..");
const { SystemStatusCard } = require(join(root, "components/dashboard/system-status-card.js"));
const { StructuredActionsPanel } = require(join(root, "components/dashboard/structured-actions-panel.js"));
const { MatrixRainBackground } = require(join(root, "components/dashboard/matrix-rain-background.js"));
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));

const baseProps = {
  health: {status: "healthy", environment: "development", reasoner: "deterministic"},
  documentsCount: 4, trustedDocumentsCount: 2, executableToolsCount: 6,
  blockedToolsCount: 4, policiesCount: 5, isLoading: false
};

test("runtime card renders deterministic, OpenAI, and unavailable provider states exactly", () => {
  const deterministic = render(SystemStatusCard, {...baseProps, reasoning: {
    provider: "deterministic", model: "local-rules-v3", mode: "local",
    implementation_version: "deterministic-v3", schema_version: "reasoning-v1",
    configured: true, available: true, reason: null
  }});
  assert.match(deterministic, />Deterministic</);
  assert.match(deterministic, /local-rules-v3/);

  const openai = render(SystemStatusCard, {...baseProps, reasoning: {
    provider: "openai", model: "gpt-test", mode: "external",
    implementation_version: "openai-responses-v1", schema_version: "reasoning-v1",
    configured: true, available: true, reason: null, openai_api_key: "sk-never-render"
  }});
  assert.match(openai, />Openai</);
  assert.match(openai, /gpt-test/);
  assert.doesNotMatch(openai, /sk-never-render/);

  const unavailable = render(SystemStatusCard, {...baseProps, reasoning: null});
  assert.match(unavailable, />Unavailable</);
});

test("structured action states and evidence references remain explicit", () => {
  const html = render(StructuredActionsPanel, {recommendation: {
    lifecycle_state: "blocked", proposed_actions: [{action_id: "act-02", action_type: "shutdown",
      target: "node-1", parameters: {}, risk_level: "critical", requires_approval: true,
      supporting_evidence_ids: ["run-1:tool:3"], rationale: "Candidate only."}]
  }});
  assert.match(html, />Blocked</);
  assert.match(html, /not valid for action review/);
  assert.match(html, /shutdown/);
  assert.match(html, /run-1:tool:3/);
  assert.match(html, /required/);
});

test("digital rain is decorative, non-interactive, reduced-motion aware, and visibility aware", () => {
  const html = render(MatrixRainBackground, {});
  assert.match(html, /aria-hidden="true"/);
  assert.match(html, /matrix-rain/);
  const source = readFileSync(join(projectRoot, "components/dashboard/matrix-rain-background.tsx"), "utf8");
  assert.match(source, /prefers-reduced-motion/);
  assert.match(source, /visibilitychange/);
  const css = readFileSync(join(projectRoot, "src/app/globals.css"), "utf8");
  assert.match(css, /pointer-events: none/);
});
