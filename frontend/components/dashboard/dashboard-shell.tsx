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
import { EvaluationSummaryCard } from "@/components/dashboard/evaluation-summary-card";
import { HarnessResultsPanel } from "@/components/dashboard/harness-results-panel";
import { MetricCard } from "@/components/dashboard/metric-card";
import { RagContextPanel } from "@/components/dashboard/rag-context-panel";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { SystemStatusCard } from "@/components/dashboard/system-status-card";
import { ToolCallsPanel } from "@/components/dashboard/tool-calls-panel";
import { ToolRegistryGroups } from "@/components/dashboard/tool-registry-groups";
import { WatchdogFindingsPanel } from "@/components/dashboard/watchdog-findings-panel";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import {
  getAgentRunDetail,
  getBackendHealth,
  getEvaluationSummary,
  getErrorMessage,
  getHarnessRunResults,
  listAgentRuns,
  listDocuments,
  listHarnessResults,
  listHarnessScenarios,
  listTools,
  listWatchdogPolicies,
  runAgent,
  runEvaluation,
  runSecurityHarness,
  seedDemoData,
} from "@/lib/api";
import {
  DEMO_ALERT_IDS,
  type AgentRunDetailResponse,
  type DemoSeedSummary,
  type DocumentListItem,
  type EvaluationSummaryResponse,
  type HarnessRunResponse,
  type HarnessScenarioResponse,
  type HealthPayload,
  type RetrievalChunk,
  type ToolListItem,
  type WatchdogPolicyItem,
} from "@/lib/types";
import { executedHarnessRunId, executionProvenanceLabel, harnessExecutionCounts, loadRecordedAgentRun, recordedRetrievalChunks, toolRegistryGroups } from "@/lib/dashboard-data";

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
  }
> = {
  gpu: {
    alertId: DEMO_ALERT_IDS.gpuAbuse,
    label: "GPU abuse investigation",
  },
  prompt: {
    alertId: DEMO_ALERT_IDS.promptInjection,
    label: "Prompt-injection poisoning",
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

function latestHarnessRunId(harnessRun: HarnessRunResponse | null): string | null {
  return harnessRun?.harness_run_id ?? null;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  return new Date(value).toLocaleString();
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
  const [evaluationSummary, setEvaluationSummary] =
    useState<EvaluationSummaryResponse | null>(null);
  const [seedSummary, setSeedSummary] = useState<DemoSeedSummary | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeScenarioLabel, setActiveScenarioLabel] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isRunningHarness, setIsRunningHarness] = useState(false);
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);
  const [runningScenario, setRunningScenario] = useState<ScenarioKind | null>(null);

  const trustedDocumentsCount = documents.filter(
    (document) => document.trust_level === "trusted"
  ).length;
  const toolGroups = toolRegistryGroups(tools);

  function applyAgentRunDetail(
    detail: AgentRunDetailResponse,
    explicitLabel?: string | null,
    recordedChunks = recordedRetrievalChunks(detail)
  ): void {
    setAgentRun(detail);
    setActiveScenarioLabel(explicitLabel ?? scenarioLabelForAlertId(detail.alert_id) ?? "Latest agent run");

    setRagChunks(recordedChunks);
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

      const { detail, chunks } = await loadRecordedAgentRun(response.items[0].agent_run_id, getAgentRunDetail);
      applyAgentRunDetail(detail, undefined, chunks);
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

  async function loadEvaluationSnapshot(): Promise<string[]> {
    const issues: string[] = [];

    try {
      const response = await getEvaluationSummary();
      setEvaluationSummary(response);
    } catch (error) {
      issues.push(getErrorMessage(error));
      setEvaluationSummary(null);
    }

    return issues;
  }

  async function bootstrapDashboard(): Promise<void> {
    setIsBootstrapping(true);
    setErrorMessage(null);

    const [referenceIssues, agentIssues, harnessIssues, evaluationIssues] = await Promise.all([
      loadReferenceData(),
      loadLatestAgentActivity(),
      loadLatestHarnessActivity(),
      loadEvaluationSnapshot(),
    ]);

    const issues = [...referenceIssues, ...agentIssues, ...harnessIssues, ...evaluationIssues];

    if (issues.length > 0) {
      setErrorMessage(issues[0]);
    } else {
      setStatusMessage((current) =>
        current ??
        "Backend connected. Seed the sample dataset to inspect investigation traces, citations, policy findings, and harness results."
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
    setStatusMessage("Seeding the sample dataset and refreshing dashboard records…");

    try {
      const response = await seedDemoData(false);
      setSeedSummary(response.summary);
      await Promise.all([
        loadReferenceData(),
        loadLatestAgentActivity(),
        loadLatestHarnessActivity(),
        loadEvaluationSnapshot(),
      ]);
      setStatusMessage("Sample data seeded. Investigation and harness scenarios are available.");
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
    setStatusMessage(`Running ${scenario.label.toLowerCase()} with runbook retrieval, local tools, and watchdog review…`);

    try {
      const seedResponse = await seedDemoData(false);
      setSeedSummary(seedResponse.summary);

      const runResponse = await runAgent(scenario.alertId);
      const detail = await getAgentRunDetail(runResponse.agent_run_id);
      applyAgentRunDetail(detail, scenario.label);
      await Promise.all([loadReferenceData(), loadEvaluationSnapshot()]);
      setStatusMessage(
        `${scenario.label} returned status ${detail.status}. Review recommendations manually; infrastructure actions cannot be executed here.`
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
    setStatusMessage("Running the local security harness against its configured components and workflow scenarios…");

    try {
      const response = await runSecurityHarness(null, false);
      setHarnessRun(response);
      await Promise.all([loadReferenceData(), loadEvaluationSnapshot()]);
      if (!agentRun) {
        await loadLatestAgentActivity();
      }
      setStatusMessage(
        `Security harness ${response.harness_run_id} completed: ${response.passed} passed, ${response.failed} failed.`
      );
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsRunningHarness(false);
    }
  }

  async function handleRunEvaluation(): Promise<void> {
    setIsRunningEvaluation(true);
    setErrorMessage(null);
    setStatusMessage("Evaluating the selected execution cohort and storing its report…");

    try {
      const response = await runEvaluation(true, "full", executedHarnessRunId(harnessRun));
      setEvaluationSummary(response.summary);
      await loadLatestHarnessActivity();
      setStatusMessage(
        `Evaluation ${response.evaluation_run_id} stored for harness ${response.summary.cohort.harness_run_id}: ${response.summary.cohort.completed_case_count} / ${response.summary.cohort.expected_case_count} scenarios completed.`
      );
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsRunningEvaluation(false);
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
            Incident triage with evidence and policy checks
          </h1>

          <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">
            Inspect runbook context, local tool responses, investigation traces,
            and adversarial test results.
          </p>

          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
            Investigations use deterministic reasoning and local infrastructure responses.
            Review retrieved citations, uncertainty, and watchdog findings before deciding
            what to do outside the system.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a className={buttonVariants({ size: "lg" })} href="#controls">
              Seed and run scenarios
            </a>
            <a
              className={buttonVariants({ size: "lg", variant: "secondary" })}
              href="#harness"
            >
              Inspect harness evidence
            </a>
            <SafetyBadge value="deterministic local reasoning" />
            <SafetyBadge value="human review required" />
            <SafetyBadge value="no shell execution" />
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/8 bg-white/[0.03] p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
                Backend connection
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-200">
                {health
                  ? `API responding in ${health.environment}. Last sync ${formatTimestamp(health.timestamp)}.`
                  : "Waiting for the local backend connection."}
              </p>
            </div>

            <div className="rounded-3xl border border-white/8 bg-white/[0.03] p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
                Latest harness run
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-200">
                {latestHarnessRunId(harnessRun)
                  ? `Record group ${latestHarnessRunId(harnessRun)}: ${executionProvenanceLabel(harnessRun?.provenance)}. ${harnessRun?.total ?? 0} scenario records.`
                  : "Run the bundled security harness to record scenario outcomes."}
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
          executableToolsCount={toolGroups[0].tools.length}
          blockedToolsCount={toolGroups[1].tools.length}
          trustedDocumentsCount={trustedDocumentsCount}
        />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          change="Stored runbooks and policy documents available for lexical retrieval."
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
              : "Run a scenario to inspect the recorded tool calls."
          }
          icon={Wrench}
          label="Tool activity"
          tone={agentRun?.tool_calls.length ? "accent" : "warning"}
          value={String(agentRun?.tool_calls.length ?? 0)}
        />
        <MetricCard
          change="Passed / completed records in the displayed executed cohort. Fixtures do not count."
          icon={FlaskConical}
          label="Executed scenario passes"
          tone={executedHarnessRunId(harnessRun) && harnessRun?.failed === 0 ? "success" : "warning"}
          value={harnessExecutionCounts(harnessRun)}
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
            Scenario catalog
          </p>
          <CardTitle className="mt-3">Bundled alert scenarios</CardTitle>
          <CardDescription className="mt-3">
            Four sample incidents cover GPU abuse, SSH login attempts, storage
            pressure, and document poisoning. The labels below describe the bundled fixtures.
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
            Available components
          </p>
          <CardTitle className="mt-3">Documents, tools, and policies</CardTitle>
          <CardDescription className="mt-3">
            Inspect the document catalog, typed tool definitions, and deterministic
            watchdog policies exposed by the backend.
          </CardDescription>

          <div className="mt-8 grid gap-4">
            <div className="rounded-2xl border border-white/8 bg-ink/60 p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accentSoft">
                  <Radar className="h-4 w-4" />
                </span>
                <div>
                  <p className="font-medium text-white">Document catalog</p>
                  <p className="mt-1 text-sm leading-6 text-slate-300">
                    Document trust labels and retrieval scan findings are available
                    alongside the investigation trace.
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
                    Seed the sample dataset to load the runbooks and policy documents.
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
                    <p className="font-medium text-white">Tool definitions</p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">
                      The registry includes local adapters and blocked action definitions.
                    </p>
                  </div>
                </div>

                <ToolRegistryGroups tools={tools} />
              </div>

              <div className="rounded-2xl border border-white/8 bg-ink/60 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-critical/20 bg-critical/10 text-red-100">
                    <ShieldAlert className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="font-medium text-white">Watchdog policies</p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">
                      Checks for dangerous recommendations, citation gaps, low confidence,
                      and suspicious context.
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
          hasRecordedRun={agentRun !== null}
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

      <section className="grid gap-6">
        <EvaluationSummaryCard
          isLoading={isBootstrapping}
          isRunningEvaluation={isRunningEvaluation}
          onRunEvaluation={handleRunEvaluation}
          summary={evaluationSummary}
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
                Human review
              </p>
              <p className="mt-1 font-medium text-white">
                Investigations end with a review handoff
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            Completed investigations stop at waiting_for_human. Review happens outside
            the application; approval, rejection, and workflow resumption are not implemented.
          </p>
        </Card>

        <Card className="border-white/8 bg-white/[0.03]">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-warning/20 bg-warning/10 text-amber-100">
              <Wrench className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Tool execution
              </p>
              <p className="mt-1 font-medium text-white">
                Typed local adapters
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            Executable adapters validate inputs and outputs and record tool activity.
            Infrastructure responses are simulated, and destructive tool requests are blocked.
          </p>
        </Card>

        <Card className="border-white/8 bg-white/[0.03]">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-success/20 bg-success/10 text-success">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                Reproducible testing
              </p>
              <p className="mt-1 font-medium text-white">
                Recorded scenarios and reports
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            Run the bundled scenarios to inspect component and workflow behavior.
            Export stored cohort reports with execution IDs, versioned scenario
            expectations, raw metric counts, and evaluation limitations.
          </p>
        </Card>
      </section>
    </main>
  );
}
