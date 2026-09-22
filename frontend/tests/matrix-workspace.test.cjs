const assert = require("node:assert/strict");
const test = require("node:test");
const { join } = require("node:path");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const built = process.env.OPSGUARD_TEST_BUILD_DIRECTORY;
const { createRainStreams, advanceRain, rainGlyph } = require(join(built, "lib/matrix-rain.js"));
const { MatrixRainBackground } = require(join(built, "components/dashboard/matrix-rain-background.js"));
const { MatrixEnvironment } = require(join(built, "components/dashboard/matrix-controls.js"));
const { WorkspaceNavigation, WORKSPACE_TABS, nextWorkspaceTab } = require(join(built, "components/dashboard/workspace-navigation.js"));
const { DashboardShell } = require(join(built, "components/dashboard/dashboard-shell.js"));
const { SystemStatusCard } = require(join(built, "components/dashboard/system-status-card.js"));
const render = (component, props = {}) => renderToStaticMarkup(React.createElement(component, props));

test("rain starts visible, is deterministic, and moves by elapsed time instead of frame count", () => {
  const initial = createRainStreams(1440, 900);
  assert.equal(initial.length, 66);
  assert.deepEqual(initial, createRainStreams(1440, 900));
  assert.ok(initial.filter((stream) => stream.head > 0 && stream.head < 900).length > 30);
  const thirty = structuredClone(initial);
  const sixty = structuredClone(initial);
  for (let n = 0; n < 30; n++) advanceRain(thirty, 1 / 30, 900, "full");
  for (let n = 0; n < 60; n++) advanceRain(sixty, 1 / 60, 900, "full");
  for (let n = 0; n < initial.length; n++) {
    assert.ok(Math.abs(thirty[n].head - sixty[n].head) < 0.000001);
    assert.notEqual(thirty[n].head, initial[n].head);
  }
  assert.notEqual(rainGlyph(1, 1, 0), rainGlyph(1, 1, 0.2));
});

test("pause preserves the code field and calm reduces motion without changing modes implicitly", () => {
  const initial = createRainStreams(390, 844);
  const paused = structuredClone(initial);
  const calm = structuredClone(initial);
  const full = structuredClone(initial);
  advanceRain(paused, 0.5, 844, "paused");
  advanceRain(calm, 0.5, 844, "calm");
  advanceRain(full, 0.5, 844, "full");
  assert.deepEqual(paused, initial);
  assert.ok(calm[0].head > initial[0].head);
  assert.ok(calm[0].head < full[0].head);
});

// Execute the actual effect with a minimal canvas/scheduler. This verifies that
// reduced motion, hidden tabs, and unmount stop scheduling, not merely CSS names.
function mountRain({ mode = "full", reduced = false } = {}) {
  const saved = { window: global.window, document: global.document, effect: React.useEffect, ref: React.useRef };
  const listeners = new Map();
  const frames = new Map();
  let nextFrame = 0;
  let cleanup;
  let glyphs = 0;
  const context = { fillRect() {}, setTransform() {}, fillText() { glyphs++; } };
  const canvas = { clientWidth: 390, clientHeight: 844, getContext: () => context };
  const preference = { matches: reduced, addEventListener: (name, fn) => listeners.set(`preference:${name}`, fn), removeEventListener: (name) => listeners.delete(`preference:${name}`) };
  global.window = {
    devicePixelRatio: 3,
    matchMedia: () => preference,
    requestAnimationFrame: (fn) => { const id = ++nextFrame; frames.set(id, fn); return id; },
    cancelAnimationFrame: (id) => frames.delete(id),
    addEventListener: (name, fn) => listeners.set(`window:${name}`, fn),
    removeEventListener: (name) => listeners.delete(`window:${name}`),
  };
  global.document = {
    hidden: false,
    addEventListener: (name, fn) => listeners.set(`document:${name}`, fn),
    removeEventListener: (name) => listeners.delete(`document:${name}`),
  };
  React.useRef = () => ({ current: canvas });
  React.useEffect = (effect) => { cleanup = effect(); };
  try { MatrixRainBackground({ mode }); } catch (error) { restore(); throw error; }
  function restore() {
    cleanup?.();
    React.useEffect = saved.effect;
    React.useRef = saved.ref;
    if (saved.window === undefined) delete global.window; else global.window = saved.window;
    if (saved.document === undefined) delete global.document; else global.document = saved.document;
  }
  return {
    frames, listeners, canvas, preference,
    glyphCount: () => glyphs,
    visibility: (hidden) => { global.document.hidden = hidden; listeners.get("document:visibilitychange")(); },
    frame: (time) => { const pending = [...frames.values()]; frames.clear(); for (const fn of pending) fn(time); },
    destroy: restore,
  };
}

test("rain effect draws a static field for reduced motion and pause with no animation scheduled", () => {
  for (const options of [{ reduced: true }, { mode: "paused" }]) {
    const surface = mountRain(options);
    try {
      assert.ok(surface.glyphCount() > 50);
      assert.equal(surface.frames.size, 0);
      assert.equal(surface.canvas.width, 585); // DPR is capped at 1.5.
      assert.equal(surface.listeners.size, 3);
    } finally { surface.destroy(); }
    assert.equal(surface.frames.size, 0);
    assert.equal(surface.listeners.size, 0);
  }
});

test("rain effect advances while visible and cancels all work on hide and unmount", () => {
  const surface = mountRain();
  try {
    assert.equal(surface.frames.size, 1);
    const before = surface.glyphCount();
    surface.frame(100);
    surface.frame(150);
    assert.ok(surface.glyphCount() > before);
    surface.visibility(true);
    assert.equal(surface.frames.size, 0);
    surface.visibility(false);
    assert.equal(surface.frames.size, 1);
    surface.preference.matches = true;
    surface.listeners.get("preference:change")();
    assert.equal(surface.frames.size, 0);
  } finally { surface.destroy(); }
  assert.equal(surface.frames.size, 0);
  assert.equal(surface.listeners.size, 0);
});

test("Matrix environment renders only the full rain canvas, without scrolling commands or FX controls", () => {
  const html = render(MatrixEnvironment);
  assert.equal(html, render(MatrixRainBackground));
  assert.match(html, /<canvas[^>]*class="matrix-rain"[^>]*aria-hidden="true"[^>]*data-rain-mode="full"/);
  assert.doesNotMatch(html, /<button|VISUAL FX|DECORATIVE SIGNAL|NO COMMANDS EXECUTED|rain-controls|ambient-band|ambient-scroll/);
  assert.doesNotMatch(html, /visual:\/\/matrix|shader:\/\/phosphor|frame:\/\/ambient/);
});

test("workspace tabs expose exactly one keyboard-selected tab and wrap keyboard navigation", () => {
  const html = render(WorkspaceNavigation, { activeTab: "evidence", onChange() {} });
  assert.equal((html.match(/role="tab"/g) ?? []).length, 6);
  assert.equal((html.match(/aria-selected="true"/g) ?? []).length, 1);
  assert.match(html, /id="tab-evidence" role="tab" aria-selected="true" aria-controls="panel-evidence" tabindex="0"/);
  assert.equal(nextWorkspaceTab("overview", "ArrowLeft"), "evaluation");
  assert.equal(nextWorkspaceTab("evaluation", "ArrowRight"), "overview");
  assert.equal(nextWorkspaceTab("investigations", "ArrowDown"), "evidence");
  assert.equal(nextWorkspaceTab("tools", "Home"), "overview");
  assert.equal(nextWorkspaceTab("tools", "End"), "evaluation");
  assert.equal(nextWorkspaceTab("tools", "Escape"), null);
  assert.deepEqual(WORKSPACE_TABS.map((tab) => tab.id), ["overview", "investigations", "evidence", "tools", "harness", "evaluation"]);
});

test("initial workspace shows one view and unavailable catalog counts instead of fabricated zeros", () => {
  const html = render(DashboardShell);
  assert.equal((html.match(/role="tabpanel"/g) ?? []).length, 1);
  assert.match(html, /id="panel-overview"/);
  assert.match(html, /Follow the evidence/);
  assert.match(html, /Investigate incident evidence/);
  assert.match(html, /<dt>Documents \/ trusted<\/dt><dd>Unavailable<\/dd>/);
  assert.doesNotMatch(html, /id="panel-harness"|id="panel-evaluation"|No documents stored/);
});

test("institutional readiness never asserts connectivity and exposes no credential fields", () => {
  const html = render(SystemStatusCard, {
    health: {status: "healthy"}, documentsCount: null, trustedDocumentsCount: null,
    executableToolsCount: null, blockedToolsCount: null, policiesCount: null, isLoading: false,
    reasoning: { provider: "institutional", model: "gpt-oss-120b", mode: "external", available: true,
      configured: true, connectivity: "not_checked", response_format: "json_object",
      model_options: [{ id: "gpt-oss-120b", capability: "chat", verified: false }],
      api_key: "never-render-this-secret", base_url: "https://private.invalid", reason: null },
  });
  assert.match(html, />Compatible API</);
  assert.match(html, /gpt-oss-120b/);
  assert.match(html, /CONFIGURED \/ INFERENCE NOT CHECKED/);
  assert.match(html, /service availability unverified/);
  assert.match(html, /Documents \/ trusted<\/dt><dd>Unavailable/);
  assert.doesNotMatch(html, /never-render-this-secret|private\.invalid|Provider available|connection verified/i);
  const unknown = render(SystemStatusCard, {health: null, reasoning: null, isLoading: false});
  assert.match(unknown, /Provider configuration is unavailable/);
  assert.doesNotMatch(unknown, /Deterministic local reasoning\./);
});
