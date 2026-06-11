"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  BookText,
  Bot,
  FlaskConical,
  LibraryBig,
  Radar,
  ShieldAlert,
  Sparkles,
  Wrench,
} from "lucide-react";

import { AgentRunTrace } from "@/components/dashboard/agent-run-trace";
import { AlertScenarioCard } from "@/components/dashboard/alert-scenario-card";
import { DemoSeedCard } from "@/components/dashboard/demo-seed-card";
import { HarnessResultsPanel } from "@/components/dashboard/harness-results-panel";
import { MetricCard } from "@/components/dashboard/metric-card";
import { RagContextPanel } from "@/components/dashboard/rag-context-panel";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { SystemStatusCard } from "@/components/dashboard/system-status-card";
import { ToolCallsPanel } from "@/components/dashboard/tool-calls-panel";
import { WatchdogFindingsPanel } from "@/components/dashboard/watchdog-findings-panel";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import {
  getAgentRunDetail,
  getBackendHealth,
  getErrorMessage,
  getHarnessRunResults,
  listAgentRuns,
  listDocuments,
  listHarnessResults,
  listHarnessScenarios,
  listTools,
  listWatchdogPolicies,
  retrieveRagChunks,
  runAgent,
  runSecurityHarness,
  seedDemoData,
} from "@/lib/api";
import {
  DEMO_ALERT_IDS,
  DEMO_RAG_QUERIES,
  type AgentRunDetailResponse,
  type DemoSeedSummary,
  type DocumentListItem,
  type HarnessRunResponse,
  type HarnessScenarioResponse,
  type HealthPayload,
  type RagRetrieveRequest,
  type RetrievalChunk,
  type ToolListItem,
  type WatchdogPolicyItem,
} from "@/lib/types";

type ScenarioKind = "gpu" | "prompt";

const seededAlerts = [
  {
    title: "Suspicious GPU usage / possible crypto-mining",
    severity: "critical",
    status: "investigating",
    source: "slurm-monitor",
    description:
      "Abnormal GPU utilization, unknown process ownership, and outbound mining-pool traffic on gpu-node-14.",
  },
  {
    title: "SSH brute-force attempt",
    severity: "high",
    status: "open",
    source: "auth-log-monitor",
    description:
      "Repeated failed root and admin login attempts from documentation-range external IPs.",
  },
  {
    title: "Storage / inode pressure warning",
    severity: "high",
    status: "open",
    source: "filesystem-monitor",
    description:
      "Inode usage is approaching a critical threshold on shared scratch storage.",
  },
  {
    title: "RAG prompt-injection document poisoning",
    severity: "critical",
    status: "investigating",
    source: "rag-security-harness",
    description:
      "A retrieved runbook contains hidden instructions telling the agent to ignore policies.",
  },
] as const;

const scenarioMetadata: Record<
  ScenarioKind,
  {
    alertId: string;
    label: string;
    query: RagRetrieveRequest;
  }
> = {
  gpu: {
    alertId: DEMO_ALERT_IDS.gpuAbuse,
    label: "GPU abuse investigation",
    query: DEMO_RAG_QUERIES.gpuAbuse,
  },
  prompt: {
    alertId: DEMO_ALERT_IDS.promptInjection,
    label: "Prompt-injection poisoning",
    query: DEMO_RAG_QUERIES.promptInjection,
  },
};

function scenarioLabelForAlertId(alertId: string): string | null {
  if (alertId === DEMO_ALERT_IDS.gpuAbuse) {
    return scenarioMetadata.gpu.label;
  }
  if (alertId === DEMO_ALERT_IDS.promptInjection) {
    return scenarioMetadata.prompt.label;
  }
  return null;
}

function extractRetrievedChunks(agentRun: AgentRunDetailResponse | null): RetrievalChunk[] {
  if (!agentRun) {
    return [];
  }

  const retrievalStep = agentRun.steps.find((step) => step.node_name === "retrieve_context");
  const results = retrievalStep?.output_snapshot.results;
  return Array.isArray(results) ? (results as RetrievalChunk[]) : [];
}

function latestHarnessRunId(harnessRun: HarnessRunResponse | null): string | null {
  return harnessRun?.harness_run_id ?? null;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  return new Date(value).toLocaleString();
}

function harnessPassRate(harnessRun: HarnessRunResponse | null): string {
  if (!harnessRun || harnessRun.total === 0) {
    return "--";
  }

  return `${Math.round((harnessRun.passed / harnessRun.total) * 100)}%`;
}

export function DashboardShell() {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [tools, setTools] = useState<ToolListItem[]>([]);
  const [policies, setPolicies] = useState<WatchdogPolicyItem[]>([]);
  const [harnessScenarios, setHarnessScenarios] = useState<HarnessScenarioResponse[]>([]);
  const [agentRun, setAgentRun] = useState<AgentRunDetailResponse | null>(null);
  const [ragChunks, setRagChunks] = useState<RetrievalChunk[]>([]);
  const [harnessRun, setHarnessRun] = useState<HarnessRunResponse | null>(null);
  const [seedSummary, setSeedSummary] = useState<DemoSeedSummary | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeScenarioLabel, setActiveScenarioLabel] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isRunningHarness, setIsRunningHarness] = useState(false);
  const [runningScenario, setRunningScenario] = useState<ScenarioKind | null>(null);

  const trustedDocumentsCount = documents.filter(
    (document) => document.trust_level === "trusted"
  ).length;

  async function applyAgentRunDetail(
    detail: AgentRunDetailResponse,
    explicitLabel?: string | null
  ): Promise<void> {
    setAgentRun(detail);
    setActiveScenarioLabel(explicitLabel ?? scenarioLabelForAlertId(detail.alert_id) ?? "Latest agent run");

    const extractedChunks = extractRetrievedChunks(detail);
    if (extractedChunks.length > 0) {
      setRagChunks(extractedChunks);
      return;
    }

    const fallbackQuery =
      detail.alert_id === DEMO_ALERT_IDS.gpuAbuse
        ? DEMO_RAG_QUERIES.gpuAbuse
        : detail.alert_id === DEMO_ALERT_IDS.promptInjection
          ? DEMO_RAG_QUERIES.promptInjection
          : null;

    if (!fallbackQuery) {
      setRagChunks([]);
      return;
    }

    try {
      const retrieval = await retrieveRagChunks(fallbackQuery);
      setRagChunks(retrieval.results);
    } catch {
      setRagChunks([]);
    }
  }

  async function loadReferenceData(): Promise<string[]> {
    const issues: string[] = [];
    const results = await Promise.allSettled([
      getBackendHealth(),
      listDocuments(),
      listTools(),
      listWatchdogPolicies(),
      listHarnessScenarios(),
    ]);

    const [healthResult, documentsResult, toolsResult, policiesResult, scenariosResult] = results;

    if (healthResult.status === "fulfilled") {
      setHealth(healthResult.value);
    } else {
      issues.push(getErrorMessage(healthResult.reason));
      setHealth(null);
    }

    if (documentsResult.status === "fulfilled") {
      setDocuments(documentsResult.value);
    } else {
      issues.push(getErrorMessage(documentsResult.reason));
      setDocuments([]);
    }

    if (toolsResult.status === "fulfilled") {
      setTools(toolsResult.value.items);
    } else {
      issues.push(getErrorMessage(toolsResult.reason));
      setTools([]);
    }

    if (policiesResult.status === "fulfilled") {
      setPolicies(policiesResult.value.items);
    } else {
      issues.push(getErrorMessage(policiesResult.reason));
      setPolicies([]);
    }

    if (scenariosResult.status === "fulfilled") {
      setHarnessScenarios(scenariosResult.value.items);
    } else {
      issues.push(getErrorMessage(scenariosResult.reason));
      setHarnessScenarios([]);
    }

    return issues;
  }

  async function loadLatestAgentActivity(): Promise<string[]> {
    const issues: string[] = [];

    try {
      const response = await listAgentRuns();
      if (response.items.length === 0) {
        setAgentRun(null);
        setRagChunks([]);
        setActiveScenarioLabel(null);
        return issues;
      }

      const detail = await getAgentRunDetail(response.items[0].agent_run_id);
      await applyAgentRunDetail(detail);
    } catch (error) {
      issues.push(getErrorMessage(error));
      setAgentRun(null);
      setRagChunks([]);
      setActiveScenarioLabel(null);
    }

    return issues;
  }

  async function loadLatestHarnessActivity(): Promise<string[]> {
    const issues: string[] = [];

    try {
      const response = await listHarnessResults();
      if (response.items.length === 0 || !response.items[0].harness_run_id) {
        setHarnessRun(null);
        return issues;
      }

      const detail = await getHarnessRunResults(response.items[0].harness_run_id);
      setHarnessRun(detail);
    } catch (error) {
      issues.push(getErrorMessage(error));
      setHarnessRun(null);
    }

    return issues;
  }

  async function bootstrapDashboard(): Promise<void> {
    setIsBootstrapping(true);
    setErrorMessage(null);

    const [referenceIssues, agentIssues, harnessIssues] = await Promise.all([
      loadReferenceData(),
      loadLatestAgentActivity(),
      loadLatestHarnessActivity(),
    ]);

    const issues = [...referenceIssues, ...agentIssues, ...harnessIssues];

    if (issues.length > 0) {
      setErrorMessage(issues[0]);
    } else {
      setStatusMessage((current) =>
        current ??
        "Backend connected. Seed the bundled demo dataset to inspect live traces, citations, watchdog findings, and harness evidence."
      );
    }

    setIsBootstrapping(false);
  }

  // This is an intentional mount-only bootstrap. Subsequent refreshes are driven
  // by explicit user actions so the dashboard does not refetch on every render.
  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    void bootstrapDashboard();
  }, []);
  /* eslint-enable react-hooks/exhaustive-deps */

  async function handleSeedDemoData(): Promise<void> {
    setIsSeeding(true);
    setErrorMessage(null);
    setStatusMessage("Seeding the deterministic demo dataset and refreshing the dashboard surface…");

    try {
      const response = await seedDemoData(false);
      setSeedSummary(response.summary);
      await Promise.all([loadReferenceData(), loadLatestAgentActivity(), loadLatestHarnessActivity()]);
      setStatusMessage("Demo data seeded. The local stack is ready for agent and harness scenarios.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSeeding(false);
    }
  }

  async function handleRunScenario(kind: ScenarioKind): Promise<void> {
    const scenario = scenarioMetadata[kind];
    setRunningScenario(kind);
    setErrorMessage(null);
    setStatusMessage(`Running ${scenario.label.toLowerCase()} with grounded retrieval, safe tools, and watchdog review…`);

    try {
      const seedResponse = await seedDemoData(false);
      setSeedSummary(seedResponse.summary);

      const runResponse = await runAgent(scenario.alertId);
      const detail = await getAgentRunDetail(runResponse.agent_run_id);
      await applyAgentRunDetail(detail, scenario.label);
      await loadReferenceData();
      setStatusMessage(
        `${scenario.label} completed with status ${detail.status}. Human approval is still required before any risky action can progress.`
      );
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setRunningScenario(null);
    }
  }

  async function handleRunHarness(): Promise<void> {
    setIsRunningHarness(true);
    setErrorMessage(null);
    setStatusMessage("Running the deterministic security harness across the local stack…");

    try {
      const response = await runSecurityHarness(null, true);
      setHarnessRun(response);
      await loadReferenceData();
      if (!agentRun) {
        await loadLatestAgentActivity();
      }
      setStatusMessage(
        `Security harness completed: ${response.passed} passed, ${response.partial} partial, ${response.failed} failed.`
      );
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsRunningHarness(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 pb-20 pt-10 lg:px-8">
      <section
        className="grid gap-8 xl:grid-cols-[1.02fr_0.98fr] xl:items-start"
        id="overview"
      >
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-accentSoft">
            <Sparkles className="h-3.5 w-3.5" />
            OpsGuard AI
          </div>

          <h1 className="mt-6 max-w-4xl font-display text-5xl font-semibold leading-tight text-white md:text-6xl">
            Secure self-aware agentic incident triage
          </h1>

          <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">
            RAG-grounded incident investigation with safe tools, watchdog policies,
            and adversarial security harness.
          </p>

          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
            This dashboard shows the whole story: seeded alerts, deterministic agent
            reasoning, auditable tool calls, grounded citations, policy findings, and
            the human-approval boundary that keeps risky actions recommendation-only.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a className={buttonVariants({ size: "lg" })} href="#controls">
              Seed and run demos
            </a>
            <a
              className={buttonVariants({ size: "lg", variant: "secondary" })}
              href="#harness"
            >
              Inspect harness evidence
            </a>
            <SafetyBadge value="mock-safe mode" />
            <SafetyBadge value="human approval required" />
            <SafetyBadge value="no shell execution" />
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/8 bg-white/[0.03] p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
                Live backend
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-200">
                {health
                  ? `Healthy in ${health.environment}. Last sync ${formatTimestamp(health.timestamp)}.`
                  : "Waiting for the local backend connection."}
              </p>
            </div>

            <div className="rounded-3xl border border-white/8 bg-white/[0.03] p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
                Latest harness run
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-200">
                {latestHarnessRunId(harnessRun)
                  ? `Run ${latestHarnessRunId(harnessRun)} captured ${harnessRun?.total ?? 0} adversarial scenarios.`
                  : "Run the bundled security harness to populate local AI-safety evidence."}
              </p>
            </div>
          </div>

          {statusMessage ? (
            <div className="mt-6 rounded-3xl border border-success/20 bg-success/10 p-5 text-sm leading-6 text-slate-50">
              {statusMessage}
            </div>
          ) : null}

          {errorMessage ? (
            <div className="mt-4 rounded-3xl border border-critical/20 bg-critical/10 p-5 text-sm leading-6 text-red-50">
              {errorMessage}
            </div>
          ) : null}
        </div>

        <SystemStatusCard
          documentsCount={documents.length}
          health={health}
          isLoading={isBootstrapping}
          policiesCount={policies.length}
          toolsCount={tools.length}
          trustedDocumentsCount={trustedDocumentsCount}
        />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          change="Seeded runbooks and safety docs available for deterministic retrieval."
          icon={LibraryBig}
          label="Knowledge base"
          value={String(documents.length)}
        />
        <MetricCard
          change={`${trustedDocumentsCount} trusted sources currently visible to the dashboard.`}
          icon={BookText}
          label="Trusted documents"
          tone="success"
          value={String(trustedDocumentsCount)}
        />
        <MetricCard
          change={
            agentRun
              ? `${agentRun.tool_calls.length} tool calls recorded for the latest trace.`
              : "Run a scenario to inspect the allowlisted tool audit trail."
          }
          icon={Wrench}
          label="Tool activity"
          tone={agentRun?.tool_calls.length ? "accent" : "warning"}
          value={String(agentRun?.tool_calls.length ?? 0)}
        />
        <MetricCard
          change={`${harnessScenarios.length} deterministic adversarial scenarios are available locally.`}
          icon={FlaskConical}
          label="Harness pass rate"
          tone={harnessRun && harnessRun.failed === 0 ? "success" : "warning"}
          value={harnessPassRate(harnessRun)}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.94fr_1.06fr]" id="controls">
        <DemoSeedCard
          isRunningHarness={isRunningHarness}
          isSeeding={isSeeding}
          onRunHarness={handleRunHarness}
          onSeed={handleSeedDemoData}
          seedSummary={seedSummary}
          statusMessage={statusMessage}
        />

        <AlertScenarioCard
          latestRunStatus={agentRun?.status ?? null}
          onRunGpuScenario={() => handleRunScenario("gpu")}
          onRunPromptScenario={() => handleRunScenario("prompt")}
          runningScenario={runningScenario}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Card className="border-white/8 bg-white/[0.03]">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Incident overview
          </p>
          <CardTitle className="mt-3">Bundled alert scenarios</CardTitle>
          <CardDescription className="mt-3">
            The demo dataset ships with four realistic operational and AI-safety
            incidents so the portfolio flow works end to end on a local machine.
          </CardDescription>

          <div className="mt-8 space-y-4">
            {seededAlerts.map((alert) => (
              <div
                className="rounded-2xl border border-white/8 bg-ink/60 p-5"
                key={alert.title}
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="max-w-2xl">
                    <p className="font-medium text-white">{alert.title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {alert.description}
                    </p>
                    <p className="mt-3 font-mono text-xs text-slate-400">
                      {alert.source}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <SafetyBadge value={alert.severity} />
                    <SafetyBadge value={alert.status} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="border-white/8 bg-white/[0.03]">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Control surface
          </p>
          <CardTitle className="mt-3">Knowledge, tools, and policy rails</CardTitle>
          <CardDescription className="mt-3">
            The frontend stays local-first and portfolio-friendly by leaning on the
            existing deterministic backend: typed tools, grounded retrieval, and
            explicit watchdog policy gates.
          </CardDescription>

          <div className="mt-8 grid gap-4">
            <div className="rounded-2xl border border-white/8 bg-ink/60 p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accentSoft">
                  <Radar className="h-4 w-4" />
                </span>
                <div>
                  <p className="font-medium text-white">Document surface</p>
                  <p className="mt-1 text-sm leading-6 text-slate-300">
                    Trust labels and prompt-injection flags stay visible all the way
                    into the agent trace.
                  </p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {documents.length > 0 ? (
                  documents.slice(0, 5).map((document) => (
                    <div
                      className="rounded-full border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-200"
                      key={document.id}
                    >
                      <span className="font-medium">{document.title}</span>
                      <span className="mx-2 text-slate-500">•</span>
                      <span>{document.trust_level}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-300">
                    Seed the demo dataset to load the runbooks and safety policy bundle.
                  </p>
                )}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-white/8 bg-ink/60 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-accentSoft">
                    <Bot className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="font-medium text-white">Allowlisted tools</p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">
                      Typed, deterministic, auditable, and mock-data based.
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {tools.slice(0, 6).map((tool) => (
                    <SafetyBadge key={tool.name} value={tool.name} />
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-white/8 bg-ink/60 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-critical/20 bg-critical/10 text-red-100">
                    <ShieldAlert className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="font-medium text-white">Watchdog policies</p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">
                      Recommendation checks that gate risky, weakly grounded, or
                      injection-tainted outcomes.
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {policies.slice(0, 5).map((policy) => (
                    <SafetyBadge key={policy.policy_id} value={policy.policy_id} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Card>
      </section>

      <section className="grid gap-6" id="traces">
        <AgentRunTrace
          activeScenarioLabel={activeScenarioLabel}
          agentRun={agentRun}
          isLoading={isBootstrapping || runningScenario !== null}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <RagContextPanel
          chunks={ragChunks}
          isLoading={isBootstrapping || runningScenario !== null}
        />
        <ToolCallsPanel
          isLoading={isBootstrapping || runningScenario !== null}
          toolCalls={agentRun?.tool_calls ?? []}
        />
      </section>

      <section className="grid gap-6">
        <WatchdogFindingsPanel recommendation={agentRun?.final_recommendation ?? null} />
      </section>

      <section className="grid gap-6" id="harness">
        <HarnessResultsPanel
          harnessRun={harnessRun}
          isLoading={isBootstrapping || isRunningHarness}
          scenarios={harnessScenarios}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <Card className="border-white/8 bg-white/[0.03]">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accentSoft">
              <Activity className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Human approval story
              </p>
              <p className="mt-1 font-medium text-white">
                Recommendations stop at the handoff line
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            The agent can ground, summarize, and draft. It cannot self-authorize
            infrastructure changes. Dangerous actions stay blocked or recommendation-only.
          </p>
        </Card>

        <Card className="border-white/8 bg-white/[0.03]">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-warning/20 bg-warning/10 text-amber-100">
              <Wrench className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Tooling posture
              </p>
              <p className="mt-1 font-medium text-white">
                Safe by default
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            Every tool is allowlisted, typed, deterministic, and audited. There is no
            arbitrary shell execution, no hidden subprocess layer, and no live cluster control.
          </p>
        </Card>

        <Card className="border-white/8 bg-white/[0.03]">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-success/20 bg-success/10 text-success">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Portfolio signal
              </p>
              <p className="mt-1 font-medium text-white">
                End-to-end local demo
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            The dashboard is designed to showcase the whole system without paid APIs,
            external services, or production credentials. It is ready for demos, screenshots,
            and technical walkthroughs.
          </p>
        </Card>
      </section>
    </main>
  );
}
