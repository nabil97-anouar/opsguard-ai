# Dashboard Guide

The OpsGuard AI dashboard imports incident bundles, launches investigations and displays their recorded evidence, reasoning, tool activity, policy findings, and regression results. It calls the FastAPI backend; it does not connect directly to infrastructure or model services.

## Open the dashboard

Follow the [Quick Start](../README.md#quick-start), then open `http://localhost:3000` on the same machine. Both `/` and `/dashboard` render the same workspace. Use the workspace navigation to switch views; the header contains a home link and an API health link.

The frontend uses Next.js, React, TypeScript, and Tailwind CSS. React hooks manage workspace state, [`frontend/lib/api.ts`](../frontend/lib/api.ts) contains the API client, and [`frontend/lib/types.ts`](../frontend/lib/types.ts) defines its response types. Fonts use local system stacks; no remote font download is required.

## Workflow

1. On **Overview**, check the backend connection and selected reasoning provider. Open **Investigations** to import an incident bundle, inspect its receipt, then start its investigation explicitly. Sample scenarios require separate seeding; they do not supply observations to imported runs. When a model provider is selected, the interface identifies where context will be sent.
2. In **Investigations**, inspect the trace, structured proposals, and watchdog findings. Use **Recorded run** to select a historical investigation. Fixture records are labeled **Fixture / example — not executed**.
3. Switch to **Evidence** to inspect the selected run's persisted retrieval snapshots. Switching views retains the selected investigation. **Tools & policy** separates recorded run tool calls from the recent request audit across runs.
4. Select **Run security harness** to execute the bundled deterministic component, policy, tool-boundary, and workflow checks. It requests `reset_demo_data: false` and preserves existing records.
5. In **Evaluation**, select **Run evaluation** to store a report for the displayed executed harness cohort. The request includes that execution ID. If only fixture or unverified history is available, the backend resolves an actual execution or runs the harness. Markdown and JSON export links point to the exact stored evaluation ID.

**Seed sample data** is also available on Overview. It calls `POST /api/v1/demo/seed` with `reset: false`, creating bundled alerts, documents, and example history without running investigations or tests.

Completed investigations end with `waiting_for_human`. This is a terminal review handoff. Approval, rejection, workflow resumption, and infrastructure execution controls are not implemented.

## Workspace views

Only the active view is rendered. The navigation supports arrow keys, Home, and End, and exposes tab and panel relationships to assistive technology. On smaller screens, navigation becomes a compact grid.

| View | Contents |
| --- | --- |
| Overview | Backend connection, sample investigation launchers, runtime-provider diagnostics, document and registry counts, selected investigation summary, executed harness pass count, and seeding controls. |
| Investigations | Automatic file conversion, JSON preview/download, import and explicit run controls, per-run historical exports, sample launch controls, recorded-run selector, executed/fixture/unknown provenance, exact run IDs, provider/model identity, recommendation, ordered steps, durations, expandable snapshots, structured proposals, and watchdog findings. |
| Evidence | Selected-run retrieval excerpts, document/chunk/evidence IDs, sources, recorded trust, scores, timestamps, citations, and scan findings. The current document catalog appears separately and does not replace historical snapshots. |
| Tools & policy | Separate executable-adapter and blocked-definition lists; recent request audit across runs; selected-run tool observations and attempts; watchdog policy definitions. |
| Security harness | Execution controls, record-group identity, per-result provenance, scenario versions and test levels, pass/fail and historical partial states, mandatory-invariant observations, failures, findings, and metadata. |
| Evaluation | Stored report versus live preview, cohort and evaluation IDs, expected/completed counts, versions, numerator/denominator metrics, limitations, invariant failures, and exports pinned to the stored report. |

Tool audit records retain exact `requested`, `validated`, `denied`, `invoked`, `succeeded`, and `failed` outcomes, with an independent handler-invocation flag. An audit row does not prove that a handler ran. Failed or denied requests are not positive evidence. Historical invocation information can be unknown.

Policy displays retain exact candidate, pending-review, and blocked states. Pending review does not mean approved; a blocked artifact is not valid for action review. Findings include affected actions and distinguish blocking from mandatory review. Status colors do not grant authority.

## Matrix presentation and motion

The interface uses a full-viewport generated canvas with falling digits and characters, green trails, and bright stream heads. The initial field is populated immediately, including when animation is disabled. Readable dark panels sit above the canvas; the masthead and footer have explicit foreground stacking. Desktop margins and the navigation rail leave the background visible.

The background runs at full intensity without an on-screen effects toolbar. Previously saved effects preferences are no longer read. The operating-system reduced-motion preference overrides movement and leaves a static canvas. The canvas stops scheduling frames while the document is hidden and removes its listeners and pending frame on unmount.

Motion advances using elapsed time rather than frame count. Rendering is capped at approximately 30 frames per second and a device pixel ratio of 1.5. These are implementation limits, not hardware performance guarantees.

A separate scrolling terminal-style strip contains visual-only text. It has no visible explanatory label, is hidden from assistive technology, and never represents tool execution, infrastructure commands, or audit events. Reduced-motion preferences and hidden-document state stop this strip.

The background is implemented in:

- [`matrix-rain.ts`](../frontend/lib/matrix-rain.ts)
- [`matrix-rain-background.tsx`](../frontend/components/dashboard/matrix-rain-background.tsx)
- [`matrix-controls.tsx`](../frontend/components/dashboard/matrix-controls.tsx)
- [`globals.css`](../frontend/src/app/globals.css)

## Runtime and connection states

The runtime card supports deterministic, OpenAI, institutional, Claude, and Ollama provider responses. It distinguishes local readiness, unavailable configuration, and **Configured / inference not checked** for all model adapters, including loopback Ollama. Loaded credentials do not prove endpoint reachability, model availability, or successful inference. The runtime endpoint does not make a model call.

Successful or failed investigation traces record the actual selected provider and requested model. Individual provider-call snapshots can also include a service-reported model identifier; the trace shows it separately when present. A missing service-reported identifier is not inferred.

Institutional chat-model options are informational and labeled as availability-unverified. Select the provider and model through backend environment configuration, then restart the backend. There is no browser credential form or model-selection API. The embedding model is not listed as a chat option.

Initial loading and explicit refreshes request reference data, run history, harness activity, and the evaluation summary. Failed catalog requests display **Unavailable**, not a false count of zero. Connection errors show the configured API target and local-origin troubleshooting guidance. A successful liveness response does not establish database or model-service readiness; `/ready` is the SQL readiness probe.

## Evidence and evaluation semantics

Retrieval scores measure lexical matches. A valid citation identifies material that existed in the run; it does not prove semantic support for a claim. Trust labels and scan results are not guarantees of reliability or comprehensive injection detection.

Historical evidence is read from the selected run's canonical recommendation evidence. Older runs may display their own validated `retrieve_context` snapshots. Loading a run never issues fresh retrieval. An explicitly empty evidence set stays empty. Later document edits do not change an earlier run's recorded text or trust labels. Switching views does not reload or replace that evidence.

Self-assessed confidence is not calibrated probability. Evaluation has no aggregate safety score. Metrics show raw numerators and denominators, with **N/A — no applicable observations** for zero denominators. Human-review rates describe terminal behavior, not escalation accuracy or approval usefulness. The bundled harness does not establish external-model prompt-injection resistance.

Stored reports remain immutable when unrelated investigations run. Without a stored report, the dashboard labels the response as a live preview and does not offer stored-report exports. Fixture passes never contribute to the executed pass indicator. Legacy partial results are historical records, not evidence that mandatory invariants passed.

See [Evaluation](EVALUATION.md), [RAG Design](RAG_DESIGN.md), and [Security Boundaries](SECURITY_BOUNDARIES.md) for implemented controls and calculations.

## Interaction limits

- Responses load after API requests complete; there is no polling or streamed investigation progress.
- The recorded-run selector covers the history returned by the existing API. There is no paginated history browser, alert editor, document uploader, or approval page.
- Refresh preserves the selected recorded investigation while updating reference data and available run choices. Reloading the page starts again from the latest available run.
- Some action-triggered refresh errors are represented through unavailable panels rather than a separate message for every endpoint. API responses and backend logs remain useful for diagnosis.
- API response types are compile-time contracts; the frontend does not perform general runtime validation of every response.

## Configuration and verification

The browser API address comes from `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000/api/v1`. Supply it in the frontend process environment or `frontend/.env.local`. Next.js embeds public environment values at build time. Compose passes the API URL as a build argument; rebuild to change it. Backend provider credentials never belong in frontend configuration.

Use Node 22. From `frontend/`, run:

```bash
npm ci
npm test
npm run lint
npm run typecheck
npm run build
```

The Node suite covers historical snapshot selection, exact safety mappings, audit invocation semantics, fixture/executed provenance, evaluation cohort integrity, immutable export links, provider configuration states, keyboard tab navigation, and animation defaults. Canvas tests exercise the effect with a controlled scheduler to verify visible initialization, elapsed-time motion, reduced motion, pause, hidden-tab cancellation, and unmount cleanup. The suite uses the existing TypeScript compiler and temporary build output.

Manual or browser-driven visual verification should also check:

1. Visible code motion immediately after opening the workspace, captured in a recording rather than inferred from a still image.
2. Full animation without an effects toolbar or signal label; reduced motion produces a static field.
3. Desktop and mobile layouts, including populated investigation, evidence, and policy views with long IDs. There should be no page-level horizontal overflow; wide report tables may scroll inside their container.
4. Historical selection retained across views, with no retrieval request while inspecting an old run.
5. Disconnected and partially unavailable backend states.
6. The distinction between configured external inference and a recorded successful model call.

Unit tests and a production build do not substitute for these visual and runtime checks. There is no committed general-purpose browser automation suite.
