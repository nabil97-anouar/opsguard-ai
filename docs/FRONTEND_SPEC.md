# Dashboard Guide

The OpsGuard AI dashboard displays local investigation records, retrieved context, tool activity, policy findings, and evaluation results. It runs sample investigations and security scenarios through the FastAPI backend.

## Open the dashboard

Follow the [Quick Start](../README.md#quick-start), then open `http://localhost:3000`. Both `/` and `/dashboard` render the same dashboard. Header links navigate to sections on `/`.

The frontend uses Next.js, React, TypeScript, and Tailwind CSS. It manages state with React hooks and calls the backend through the handwritten client in [`frontend/lib/api.ts`](../frontend/lib/api.ts). Response types are declared in [`frontend/lib/types.ts`](../frontend/lib/types.ts).

## Workflow

1. Select **Seed sample data** to create the bundled alerts, documents, and related records. This button calls `POST /api/v1/demo/seed` with `reset: false`.
2. Select **Run scenario** for GPU abuse or prompt-injection poisoning. Each action upserts sample data, starts an investigation, and loads its recorded details when the request returns.
3. Inspect the investigation trace, retrieval context, tool calls, and watchdog findings. Expand the JSON sections to see the stored step and tool payloads.
4. Select **Run security harness** to run the bundled component and workflow scenarios. This action requests a reset of seeded records before execution.
5. Select **Run evaluation** to calculate and store an aggregate summary. It can run the harness if results are absent. Open the Markdown or JSON report to inspect counts, scores, and limitations.

Completed investigations end with `waiting_for_human`. This is a terminal review handoff. Approval, rejection, workflow resumption, and infrastructure execution controls are not implemented; review and any subsequent operational action happen outside this application.

## Dashboard sections

| Section | What it displays |
| --- | --- |
| Backend overview | Health response, configured environment and reasoning provider, document counts, separate executable/blocked tool counts, and policy count. The health response is not a complete dependency-readiness check. |
| Sample data and tests | Seeding and harness controls, progress messages, and the most recent seed summary. |
| Agent scenarios | Launch controls for the two bundled investigations. |
| Scenario catalog | Static descriptions and labels for four sample incidents. These labels describe fixtures rather than current alert state. |
| Documents, tools, and policies | A preview of documents and policies, plus separate labeled lists for executable adapters and blocked action definitions. |
| Agent run trace | Run identifiers and status, recommendation summary, ordered steps, durations, and expandable input/output snapshots. Assessment details and missing evidence are available in the recorded JSON. |
| RAG citations | Persisted excerpts, source/document/chunk/evidence IDs, observation times, trust labels, retrieval scores, citations, and pattern-scan findings. |
| Tool calls | Exact call IDs, recorded tool names, outcomes, trust labels, scan results, input arguments, and outputs. Failed and blocked attempts are not supporting observations. |
| Watchdog findings | Policy verdict, reasons, remediation text, reference identifiers, and finding metadata. A verdict does not authorize infrastructure execution. |
| Security harness | Passed, partial, and failed counts; expected and observed behavior; findings, safety events, and result metadata. |
| Evaluation and reports | Aggregate engineering indicators, activity counts, summary text, and report links. |

## Interpreting evidence and evaluation

Retrieval scores measure lexical matches. A citation identifies retrieved material; its presence does not prove that the material supports a particular claim. Trust and scan labels are metadata, not a guarantee that content is reliable or free of injected instructions. Review the text and recorded tool output together.

The dashboard reads canonical evidence from the displayed run's recommendation. Older runs may display their own validated `retrieve_context` step snapshots. It never issues fresh retrieval while loading a run. An explicit empty evidence set stays empty, and absent historical evidence has an explicit empty state. Editing current documents does not change the stored content or trust shown for an earlier run.

Confidence and aggregate evaluation scores are deterministic engineering heuristics. They are not calibrated probabilities, semantic correctness measurements, or estimates of resistance to arbitrary attacks. Evaluation score badges are display summaries; watchdog findings contain the actual policy verdicts. Report endpoints prefer the latest saved evaluation; run evaluation to refresh it from recorded activity.

See [Evaluation](EVALUATION.md), [RAG Design](RAG_DESIGN.md), and [Security Boundaries](SECURITY_BOUNDARIES.md) for the implemented calculations and controls.

## Current interaction limits

- Initial loading retrieves reference data, the latest available investigation, recent harness activity, and an evaluation summary. Refreshes are driven by explicit actions; there is no polling or streamed step progress.
- The dashboard has no alert editor, document uploader, investigation-history selector, or separate approval page.
- Independent action controls can overlap. Run mutations sequentially, especially when the harness resets sample records. Refresh the page if displayed records no longer match the current backend state.
- Some refresh failures are reduced to a single message or not surfaced by action handlers. Raw step records and API responses remain useful when investigating inconsistent displays.
- Status badges use exact mappings: untrusted content and approval/warning decisions receive warning treatment, quarantined content and blocked decisions receive critical treatment, and unknown labels remain neutral. Color does not grant execution authority.

## Frontend configuration and checks

The browser API address comes from `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000/api/v1`. For native development, supply it in the frontend process environment or `frontend/.env.local`. Public Next.js environment values are embedded during the build; changing a container's runtime environment does not update the browser bundle.

Only the API base URL belongs in frontend configuration. Provider credentials must remain on the backend. The layout currently uses `next/font/google`, so builds require access to download the configured fonts.

From `frontend/`, run:

```bash
npm ci
npm test
npm run lint
npm run typecheck
npm run build
```

The Node test suite covers the production historical loader, snapshot selection, exact badge mappings, and server-rendered tool grouping. It uses the existing TypeScript compiler and creates temporary build artifacts without adding dependencies. There is no browser automation suite or general runtime validation of every API response.
