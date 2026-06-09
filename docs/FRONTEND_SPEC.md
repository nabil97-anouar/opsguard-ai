# FRONTEND_SPEC.md — OpsGuard AI Dashboard

## Design Direction

**Style:** Dark-mode-first, professional SRE/DevSecOps aesthetic. Think Datadog meets Vercel. Not a chatbot UI.

**Color palette:**
- Background: `#0a0a0a` (near black)
- Surface: `#111111` / `#1a1a1a`
- Border: `#2a2a2a`
- Primary accent: `#3b82f6` (blue-500)
- Success: `#22c55e` (green-500)
- Warning: `#f59e0b` (amber-500)
- Error: `#ef4444` (red-500)
- Critical: `#dc2626` (red-600) with pulsing border
- Text primary: `#f8fafc`
- Text muted: `#94a3b8`
- Self-assessment confidence: gradient from red → amber → green

**Typography:**
- System font stack for body
- `font-mono` for code, IDs, metric values, tool outputs
- `text-xs` for metadata, citations
- Large numbers for metrics (agent scores, confidence values)

**Component library:** shadcn/ui adapted to dark theme. Custom components for:
- Self-assessment card
- Kill-chain stage badge
- Tool call timeline item
- Evidence citation block
- Safety event banner
- Confidence gauge

---

## Page Specifications

---

### Page 1: Landing Page (`/`)

**Purpose:** Portfolio showcase entry. First impression for Upwork clients and GitHub visitors.

**Layout:**
```
┌────────────────────────────────────────────────────┐
│  Header: OpsGuard AI     [View Demo] [GitHub]       │
├────────────────────────────────────────────────────┤
│                                                     │
│  Hero: "Secure Self-Aware AI Agents"               │
│  Subtext: One-liner value proposition               │
│  [Launch Demo Dashboard] button (primary CTA)       │
│                                                     │
├──────────────┬─────────────────┬───────────────────┤
│  Feature 1   │   Feature 2     │  Feature 3        │
│  Metacog.    │   Security      │  RAG + Citations  │
│  Self-Assess │   Harness       │                   │
├────────────────────────────────────────────────────┤
│  Architecture diagram (simplified SVG/Mermaid)     │
├────────────────────────────────────────────────────┤
│  Tech stack badges                                  │
│  Python · FastAPI · LangGraph · Qdrant · Next.js   │
└────────────────────────────────────────────────────┘
```

**Key components:**
- Animated confidence gauge (CSS animation, no API needed)
- Feature cards with icons
- Tech badge row
- "Load Demo Data" button that calls `POST /demo/seed`

**Screenshot-worthy:** Full-page hero with dark background and feature cards

---

### Page 2: Dashboard (`/dashboard`)

**Purpose:** Ops overview. Live summary of system state.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  Sidebar nav                                          │
│  ├─ Dashboard                                         │
│  ├─ Alerts                                            │
│  ├─ Safety Events                                     │
│  ├─ Security Harness                                  │
│  ├─ Evaluation                                        │
│  └─ Documents                                         │
├──────────────────────────────────────────────────────┤
│  Header: "OpsGuard AI" + active alerts badge         │
├───────────┬───────────┬───────────┬──────────────────┤
│  Active   │ Running   │ Safety    │  Avg Confidence  │
│  Alerts   │ Agents    │ Events    │  Score           │
│  [22]     │  [3]      │  [5]      │  [0.74]          │
├───────────┴───────────┴───────────┴──────────────────┤
│  Recent Alerts (table: title, severity, status, time)│
│  Recent Agent Runs (table: alert, status, score)     │
│  Recent Safety Events (list)                         │
├──────────────────────────────────────────────────────┤
│  Security Score widget (circle gauge)                │
│  Evaluation Metrics sparklines                       │
└──────────────────────────────────────────────────────┘
```

**Key UI states:**
- Loading: skeleton cards
- Empty: "No alerts yet — [Seed Demo Data]" CTA
- Critical alert badge: pulsing red dot on sidebar nav
- Running agent: spinning indicator

**Screenshot-worthy:** Dashboard with populated metrics, colorful severity badges, running agent

---

### Page 3: Alerts List (`/alerts`)

**Layout:**
- Full-width table with: Severity badge | Title | Infrastructure Type | Source | Status | Created | Agent Run status | Actions
- Filter bar: severity, status, infrastructure_type, search
- Pagination
- "Investigate" button per row (triggers `POST /alerts/{id}/investigate`)

**Severity badges:**
- `critical` — red with pulsing animation
- `error` — red
- `warning` — amber
- `info` — blue

**Empty state:** "No alerts matching filters"

**Screenshot-worthy:** Table with mixed severity rows, status badges, running agent indicators

---

### Page 4: Alert Detail (`/alerts/[id]`)

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  ← Back to Alerts                                    │
│  Alert: "GPU memory overflow on node-04"  [CRITICAL] │
├──────────────────────────────────────────────────────┤
│  Alert metadata row: source | infra | time | status  │
├──────────┬───────────────────────────────────────────┤
│  Raw     │  Agent Investigation                      │
│  Data    │  Status: AWAITING APPROVAL                │
│  JSON    │  Risk Level: HIGH (red badge)             │
│  viewer  │  Confidence: 0.78 (gauge)                 │
│          │  [View Full Trace] [Approve/Reject]        │
├──────────┴───────────────────────────────────────────┤
│  Tab row: Trace | Self-Assessment | Tools | Evidence │
│           Kill-Chain | Approve | Report              │
└──────────────────────────────────────────────────────┘
```

---

### Page 5: Agent Investigation Trace (`/alerts/[id]/trace`)

**Purpose:** Visual step-by-step execution timeline. Most impressive page for portfolio.

**Layout:**
```
┌──────────────────────────────────────────────────────────┐
│  Timeline (vertical, left to right)                      │
│                                                          │
│  ● ingest_alert         ✓ 12ms                          │
│  │                                                       │
│  ● classify_alert       ✓ 340ms  [alert_type: gpu_mem]  │
│  │                                                       │
│  ◉ metacognitive_self_assessment  ✓ 420ms               │
│  │   Confidence: 0.52 [RETRIEVE MORE]                   │
│  │   ┌──────────────────────────────────┐               │
│  │   │  Self-Assessment Card (expanded) │               │
│  │   └──────────────────────────────────┘               │
│  │                                                       │
│  ● retrieve_context     ✓ 890ms   [5 docs retrieved]    │
│  │                                                       │
│  ● map_to_ai_kill_chain ✓ 210ms   [none detected]       │
│  │                                                       │
│  ● execute_safe_tools   ✓ 1240ms                        │
│  │   ├─ search_logs      ✓ 23ms                         │
│  │   ├─ get_node_metrics ✓ 18ms                         │
│  │   └─ get_running_jobs ✓ 31ms                         │
│  │                                                       │
│  ◉ metacognitive_self_assessment  ✓ 380ms               │
│  │   Confidence: 0.78 [CONTINUE]                        │
│  │                                                       │
│  ● run_prompt_injection_check ✓ 45ms [clean]            │
│  │                                                       │
│  ● generate_recommendation  ✓ 1800ms  [HIGH RISK]       │
│  │                                                       │
│  ⏸ wait_for_human_approval   PENDING                    │
└──────────────────────────────────────────────────────────┘
```

**Node styling:**
- Completed: `●` green, check icon
- Running: spinning indicator
- Pending/waiting: pause icon, amber
- Failed: red X
- Metacognitive assessment nodes: larger, highlighted border, always expanded

**Expandable detail:** Click any node to expand input/output snapshot

**Screenshot-worthy:** Full trace with multiple nodes, self-assessment cards visible, waiting for approval node at bottom

---

### Page 6: Self-Assessment Panel (`/alerts/[id]/self-assessment` or Tab)

**Purpose:** Show all metacognitive assessments in chronological order. Key differentiator.

**Layout per assessment card:**
```
┌──────────────────────────────────────────────────────┐
│  Assessment #1  •  metacognitive_self_assessment     │
│  Capability Area: gpu_incident_triage                │
│                                                      │
│  Confidence  [████████░░] 0.52    MEDIUM UNCERTAINTY │
│                                                      │
│  Decision: ⟳ RETRIEVE MORE (amber badge)            │
│                                                      │
│  What the agent knows:                               │
│  ✓ GPU utilization: 99.7%                           │
│  ✓ ECC errors detected (volatile: 12)               │
│  ✓ Node: gpu-node-04                                │
│                                                      │
│  Missing evidence:                                   │
│  ✗ Process-level memory breakdown                   │
│  ✗ Running job history on this node                 │
│  ✗ Historical ECC error baseline                    │
│                                                      │
│  Rationale:                                          │
│  "GPU metrics are available but process breakdown   │
│   is required to confirm root cause and identify    │
│   the responsible workload..."                       │
│                                                      │
│  Within capability: ✓ Yes                           │
└──────────────────────────────────────────────────────┘
```

**Confidence gauge:** A circular or bar gauge colored red (0–0.4), amber (0.4–0.7), green (0.7–1.0)

**Decision badges:**
- CONTINUE — green
- RETRIEVE MORE — blue
- CALL TOOL — blue
- ASK HUMAN — amber with icon
- STOP — red
- DELEGATE — purple

**Screenshot-worthy:** Two assessment cards side by side showing progression from 0.52 → 0.78

---

### Page 7: Tool Calls Timeline (`/alerts/[id]/tools` or Tab)

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  Tool Calls Timeline                                 │
│                                                      │
│  [1] search_logs          ✓ 23ms                    │
│      Node: gpu-node-04 | Terms: ECC, NVML error     │
│      Found: 3 entries | Trust: untrusted            │
│      [Expand output]                                 │
│                                                      │
│  [2] get_node_metrics     ✓ 18ms                    │
│      Node: gpu-node-04 | Metrics: gpu, memory       │
│      GPU-3: 99.7% util, 79.8/80GB, ECC:12          │
│      [Expand output]                                 │
│                                                      │
│  [3] get_running_jobs     ✓ 31ms                    │
│      Node: gpu-node-04 | Jobs found: 2              │
│      [Expand output]                                 │
│                                                      │
│  [4] create_ticket_draft  ✓ 8ms                     │
│      Ticket: GPU_2024-1145 | Severity: critical     │
│      [View draft]                                    │
└──────────────────────────────────────────────────────┘
```

**Trust level badges:** Color coded (green=trusted, amber=untrusted, red=flagged)
**Expandable JSON:** Each tool call expands to show input args and full output

---

### Page 8: Retrieved Evidence (`/alerts/[id]/evidence` or Tab)

**Layout:**
- Numbered evidence cards
- Each card: document title, section, relevance score gauge, trust badge, chunk content, citation string
- Injection scan badge: CLEAN / FLAGGED (green/red)
- Staleness badge if applicable

```
┌─────────────────────────────────────────────────────┐
│  [EVIDENCE-1]  Relevance: 0.94                      │
│  GPU Memory Overflow Recovery Runbook v2.1          │
│  Section: Step 2 — Check ECC Error Counts           │
│  Trust: ● trusted   Scan: ✓ clean                  │
│  ─────────────────────────────────────────────────  │
│  Check ECC error counts using nvidia-smi:           │
│  nvidia-smi --query-gpu=ecc.errors...               │
│  If volatile errors > 10, this indicates...         │
│  ─────────────────────────────────────────────────  │
│  Citation: "GPU Memory Overflow Runbook, Sec 2, ¶3" │
└─────────────────────────────────────────────────────┘
```

---

### Page 9: AI Kill-Chain Mapping (`/alerts/[id]/kill-chain` or Tab)

**Layout:**
```
Kill-Chain Analysis
Status: ● No stages detected (green)  OR  ⚠ 1 stage detected (amber)

Kill-Chain Stages:
[1] Model Supply Chain Compromise  ─── Not detected
[2] Prompt Injection Delivery       ─── NOT DETECTED ✓
[3] Agentic Pivot                   ─── Not detected
[4] Model Extraction Attempt        ─── Not detected  
[5] Data Extraction Attempt         ─── Not detected
[6] Unsafe Action on Objective      ─── Not detected
[7] Malicious Tool Feedback         ─── Not detected
[8] Malicious Objective Manipulation─── Not detected

Overall confidence: 0.12 (no threat indicators)
Rationale: [text]
```

If stage detected: card expands to show indicators and evidence.

---

### Page 10: Safety Events (`/safety`)

**Purpose:** Chronological log of all safety events across all agent runs.

**Layout:** Table with: event_type | severity | source | affected component | agent run link | pattern matched | timestamp

**Filter by:** event_type, severity, date range

**Empty state:** "No safety events recorded — system is operating normally" (green checkmark)

---

### Page 11: Human Approval Panel (`/alerts/[id]/approve` or Modal)

**Purpose:** The most operationally important page. Used when agent requires human review.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  ⚠ Human Review Required                            │
│  Risk Level: HIGH   Confidence: 0.78                │
│                                                      │
│  Recommendation Summary:                             │
│  Root cause: ECC memory fault on GPU 3, node-04     │
│  Confidence: 0.78 (medium-high)                     │
│                                                      │
│  Suggested Actions:                                  │
│  [REQUIRES APPROVAL]                                 │
│  drain_node(gpu-node-04)                            │
│  Rationale: GPU 3 has 47 aggregate ECC errors...    │
│  Evidence: [EVIDENCE-1], [TOOL-1]                   │
│                                                      │
│  Self-Assessment:                                    │
│  Decision: ASK HUMAN  |  Confidence: 0.78           │
│  Missing: Historical ECC baseline                   │
│                                                      │
│  Kill-Chain: No adversarial indicators              │
│                                                      │
│  Evidence (3 docs):  [view ↓]                       │
│  Tool Outputs:       [view ↓]                       │
│                                                      │
│  Your decision:                                      │
│  [text area for reason]                             │
│                                                      │
│  [REJECT]                 [APPROVE]                 │
│  (red)                    (green)                   │
└──────────────────────────────────────────────────────┘
```

**Screenshot-worthy:** Full approval modal with recommendation, evidence, and decision buttons visible

---

### Page 12: Security Harness (`/harness`)

**Purpose:** Run and view AI security tests. Red-team showcase.

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│  Security Harness                                    │
│  [Run All Tests] [Run Category ▼]                   │
├───────────────┬──────────────────────────────────────┤
│  Score: 87.5  │  Category Breakdown                 │
│  ████████░░   │  Prompt Injection: 90/100            │
│  Mostly Secure│  Kill-Chain: 85/100                 │
│               │  Secret Leakage: 100/100            │
│               │  Unsupported Conclusions: 80/100    │
├───────────────┴──────────────────────────────────────┤
│  Test Results Table                                  │
│  PI-001  log_injection_override   10/10  PASS  ✓    │
│  PI-002  runbook_poisoning        10/10  PASS  ✓    │
│  PI-003  tool_output_injection    10/10  PASS  ✓    │
│  KCA-001 injection_delivery       8/10   PASS  ✓    │
│  KCA-002 agentic_pivot            8/10   PASS  ✓    │
│  KCA-004 unsafe_action            10/10  PASS  ✓    │
│  SL-001  system_prompt_extract    10/10  PASS  ✓    │
│  UC-001  unsupported_conclusion   8/10   PASS  ✓    │
│  [click row to expand details]                      │
└──────────────────────────────────────────────────────┘
```

**Expanded test detail card:**
- Attack payload (syntax-highlighted, injection patterns highlighted in red)
- Expected behavior
- Actual behavior
- Detection log
- Linked safety events

**Screenshot-worthy:** Score card + test table with all green passes + one expanded detail card

---

### Page 13: Evaluation Panel (`/evaluation`)

**Layout:**
- Metric cards for each evaluation dimension
- Per-run score table
- Score trend chart (sparkline per metric over last N runs)

**Key metrics displayed large:**
- Evidence Grounding: `0.81`
- Safety Score: `0.97`
- Uncertainty Calibration: `0.88`
- Prompt Injection Resistance: `0.92`

---

### Page 14: Incident Report Export (`/reports`)

**Layout:**
- List of exportable reports per completed agent run
- "Export JSON" and "Export Markdown" buttons per report
- Preview panel: scrollable rendered Markdown or formatted JSON

---

## Demo Video Flow

1. Open Dashboard — show populated alerts, metrics
2. Click critical alert — show detail with "Investigate" button
3. Watch trace animate in real-time (use pre-seeded demo data for speed)
4. Highlight self-assessment card: confidence score, decision RETRIEVE MORE → CONTINUE
5. Scroll tool calls timeline — show 3 tool calls with outputs
6. Show evidence panel — cite runbook and past incident
7. Show human approval panel — pause on AWAITING APPROVAL, explain what it means
8. Approve → workflow completes
9. Show incident report
10. Navigate to Security Harness — show 87.5 score, all green tests
11. Expand one test (PI-001) — show attack payload and detection log
12. End on Evaluation panel — show clean metrics

**Total demo video target: 3–5 minutes**

---

## Empty and Loading States

**Empty states:**
- Alerts list: "No alerts yet. [Seed demo data] to load example scenarios."
- Safety events: "No safety events. System operating normally." + green shield icon
- Documents: "No documents ingested. Upload a runbook to get started."

**Loading states:** Skeleton cards for all data-driven components. No spinners — skeleton layouts only.

**Error states:** Inline error banner with error code and suggested action. Never blank pages.
