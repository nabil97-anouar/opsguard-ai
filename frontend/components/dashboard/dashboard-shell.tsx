"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, ArrowUpRight, Check, Cpu, Database, FlaskConical, LoaderCircle, RefreshCw, ShieldCheck, Terminal, TriangleAlert, Zap } from "lucide-react";

import { IncidentImportCard } from "@/components/dashboard/incident-import-card";
import { ImportedEvidencePanel } from "@/components/dashboard/imported-evidence-panel";
import { InvestigationReportLinks } from "@/components/dashboard/investigation-report-links";
import { importPreparedIncident, investigateImportedIncident, providerLabel } from "@/lib/incident-import";
import { assertRunIdentity, createRunSelectionGuard, selectedInvestigationReport } from "@/lib/investigation-selection";
import { AgentRunTrace } from "@/components/dashboard/agent-run-trace";
import { AlertScenarioCard } from "@/components/dashboard/alert-scenario-card";
import { EvaluationSummaryCard } from "@/components/dashboard/evaluation-summary-card";
import { HarnessResultsPanel } from "@/components/dashboard/harness-results-panel";
import { RagContextPanel } from "@/components/dashboard/rag-context-panel";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { SystemStatusCard } from "@/components/dashboard/system-status-card";
import { ToolAttemptsPanel } from "@/components/dashboard/tool-attempts-panel";
import { ToolCallsPanel } from "@/components/dashboard/tool-calls-panel";
import { ToolRegistryGroups } from "@/components/dashboard/tool-registry-groups";
import { WatchdogFindingsPanel } from "@/components/dashboard/watchdog-findings-panel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  ApiClientError,
  getAgentRunDetail,
  listToolAttempts,
  getBackendHealth,
  getReasoningRuntime,
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
  type ImportedIncident,
  type IncidentBundle,
  type AgentRunListItem,
  type DocumentListItem,
  type EvaluationSummaryResponse,
  type HarnessRunResponse,
  type HarnessScenarioResponse,
  type HealthPayload,
  type RetrievalChunk,
  type ReasoningRuntime,
  type ToolListItem,
  type WatchdogPolicyItem,
} from "@/lib/types";
import { executedHarnessRunId, executionProvenanceLabel, harnessExecutionCounts, loadRecordedAgentRun, recordedRetrievalChunks, recordedIncidentTitle, toolRegistryGroups } from "@/lib/dashboard-data";
import { MatrixEnvironment } from "@/components/dashboard/matrix-controls";
import { WorkspaceNavigation, WORKSPACE_TABS, type WorkspaceTab } from "@/components/dashboard/workspace-navigation";
import { ProvenanceLabel } from "@/components/dashboard/provenance-label";
import { API_BASE_URL } from "@/lib/config";
import { StructuredActionsPanel } from "@/components/dashboard/structured-actions-panel";

type ScenarioKind = "gpu" | "prompt";

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

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  return new Date(value).toLocaleString();
}

export function DashboardShell() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("overview");
  const [runHistory, setRunHistory] = useState<AgentRunListItem[]>([]);
  const [importedIncident, setImportedIncident] = useState<ImportedIncident | null>(null);
  const [isImportingIncident, setIsImportingIncident] = useState(false);
  const [isRunningImported, setIsRunningImported] = useState(false);
  const [isLoadingRun, setIsLoadingRun] = useState(false);
  const selectedRunRequest = useRef(createRunSelectionGuard());
  const runHistoryRequest = useRef(0);
  const [availability, setAvailability] = useState({ documents: false, tools: false, policies: false, attempts: false, runs: false, harness: false, evaluation: false });
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [reasoning, setReasoning] = useState<ReasoningRuntime | null>(null);
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [tools, setTools] = useState<ToolListItem[]>([]);
  const [policies, setPolicies] = useState<WatchdogPolicyItem[]>([]);
  const [harnessScenarios, setHarnessScenarios] = useState<HarnessScenarioResponse[]>([]);
  const [recentAttempts, setRecentAttempts] = useState<import("@/lib/types").ToolAttempt[]>([]);
  const [agentRun, setAgentRun] = useState<AgentRunDetailResponse | null>(null);
  const [ragChunks, setRagChunks] = useState<RetrievalChunk[]>([]);
  const [harnessRun, setHarnessRun] = useState<HarnessRunResponse | null>(null);
  const [evaluationSummary, setEvaluationSummary] =
    useState<EvaluationSummaryResponse | null>(null);

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

  function clearSelectedRun(): void {
    setAgentRun(null);
    setRagChunks([]);
    setActiveScenarioLabel(null);
  }

  function beginRunSelection(): number {
    const request = selectedRunRequest.current.begin();
    clearSelectedRun();
    setIsLoadingRun(false);
    return request;
  }

  function handleIncidentFileSelection(): void {
    beginRunSelection();
    setImportedIncident(null);
    setStatusMessage(null);
    setErrorMessage(null);
  }

  function applyAgentRunDetail(
    detail: AgentRunDetailResponse,
    explicitLabel?: string | null,
    recordedChunks = recordedRetrievalChunks(detail)
  ): void {
    setAgentRun(detail);
    setActiveScenarioLabel(explicitLabel ?? scenarioLabelForAlertId(detail.alert_id) ?? recordedIncidentTitle(detail) ?? "Recorded investigation");

    setRagChunks(recordedChunks);
  }

  async function loadReferenceData(): Promise<string[]> {
    const issues: string[] = [];
    const results = await Promise.allSettled([
      getBackendHealth(),
      getReasoningRuntime(),
      listDocuments(),
      listTools(),
      listWatchdogPolicies(),
      listHarnessScenarios(),
      listToolAttempts(),
    ]);

    const [healthResult, reasoningResult, documentsResult, toolsResult, policiesResult, scenariosResult, attemptsResult] = results;
    setAvailability((current) => ({ ...current,
      documents: documentsResult.status === "fulfilled", tools: toolsResult.status === "fulfilled",
      policies: policiesResult.status === "fulfilled", attempts: attemptsResult.status === "fulfilled",
    }));
    if (attemptsResult.status === "fulfilled") setRecentAttempts(attemptsResult.value.items);
    else issues.push(getErrorMessage(attemptsResult.reason));

    if (healthResult.status === "fulfilled") {
      setHealth(healthResult.value);
    } else {
      issues.push(getErrorMessage(healthResult.reason));
      setHealth(null);
    }

    if (reasoningResult.status === "fulfilled") {
      setReasoning(reasoningResult.value);
    } else {
      issues.push(getErrorMessage(reasoningResult.reason));
      setReasoning(null);
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
    const request = selectedRunRequest.current.beginAutomatic();

    try {
      const response = await refreshRunHistory();
      if (request === null || !selectedRunRequest.current.isCurrent(request)) return issues;
      if (response.items.length === 0) {
        clearSelectedRun();
        return issues;
      }

      const runId = response.items[0].agent_run_id;
      const { detail, chunks } = await loadRecordedAgentRun(runId, getAgentRunDetail);
      if (!selectedRunRequest.current.isCurrent(request)) return issues;
      assertRunIdentity(detail, { runId });
      if (selectedRunRequest.current.commit(request)) applyAgentRunDetail(detail, undefined, chunks);
    } catch (error) {
      issues.push(getErrorMessage(error));
      if (request !== null && selectedRunRequest.current.isCurrent(request)) clearSelectedRun();
    }

    return issues;
  }

  async function refreshRunHistory() {
    const request = ++runHistoryRequest.current;
    try {
      const response = await listAgentRuns();
      if (request === runHistoryRequest.current) {
        setRunHistory(response.items);
        setAvailability((current) => ({ ...current, runs: true }));
      }
      return response;
    } catch (error) {
      if (request === runHistoryRequest.current) setAvailability((current) => ({ ...current, runs: false }));
      throw error;
    }
  }

  async function loadLatestHarnessActivity(): Promise<string[]> {
    const issues: string[] = [];

    try {
      const response = await listHarnessResults();
      setAvailability((current) => ({ ...current, harness: true }));
      if (response.items.length === 0 || !response.items[0].harness_run_id) {
        setHarnessRun(null);
        return issues;
      }

      const detail = await getHarnessRunResults(response.items[0].harness_run_id);
      setHarnessRun(detail);
    } catch (error) {
      issues.push(getErrorMessage(error));
      setAvailability((current) => ({ ...current, harness: false }));
      setHarnessRun(null);
    }

    return issues;
  }

  async function loadEvaluationSnapshot(): Promise<string[]> {
    const issues: string[] = [];

    try {
      const response = await getEvaluationSummary();
      setEvaluationSummary(response);
      setAvailability((current) => ({ ...current, evaluation: true }));
    } catch (error) {
      issues.push(getErrorMessage(error));
      setAvailability((current) => ({ ...current, evaluation: false }));
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
        "Workspace synchronized. Start an investigation or inspect a recorded run."
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
      await seedDemoData(false);
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
    const request = beginRunSelection();
    setRunningScenario(kind);
    setActiveTab("investigations");
    setErrorMessage(null);
    setStatusMessage(`Running ${scenario.label.toLowerCase()} with runbook retrieval, local tools, and watchdog review…`);

    try {
      const runResponse = await runAgent(scenario.alertId);
      const detail = await getAgentRunDetail(runResponse.agent_run_id);
      if (!selectedRunRequest.current.isCurrent(request)) return;
      assertRunIdentity(detail, { runId: runResponse.agent_run_id, alertId: scenario.alertId });
      applyAgentRunDetail(detail, scenario.label);
      await refreshRunHistory();
      await Promise.all([loadReferenceData(), loadEvaluationSnapshot()]);
      if (!selectedRunRequest.current.isCurrent(request)) return;
      setStatusMessage(
        `${scenario.label} returned status ${detail.status}. Review recommendations manually; infrastructure actions cannot be executed here.`
      );
    } catch (error) {
      if (!selectedRunRequest.current.isCurrent(request)) return;
      setErrorMessage(error instanceof ApiClientError && error.status === 404
        ? "The synthetic alert is not present. Select Seed sample data explicitly, then run this sample scenario."
        : getErrorMessage(error));
    } finally {
      if (selectedRunRequest.current.isCurrent(request)) setRunningScenario(null);
    }
  }

  async function handleImportIncident(bundle: IncidentBundle): Promise<void> {
    const request = beginRunSelection();
    setImportedIncident(null);
    setIsImportingIncident(true);
    setErrorMessage(null);
    setStatusMessage("Importing incident observations into the backend. No model request is being made…");
    try {
      const receipt = await importPreparedIncident(bundle);
      if (!selectedRunRequest.current.isCurrent(request)) return;
      setImportedIncident({ bundle, receipt });
      setStatusMessage(`Imported ${receipt.observation_count} observations as untrusted input. Review the provider destination, then run the investigation.`);
    } catch (error) {
      if (!selectedRunRequest.current.isCurrent(request)) return;
      setImportedIncident(null);
      setStatusMessage(null);
      throw error;
    } finally {
      if (selectedRunRequest.current.isCurrent(request)) setIsImportingIncident(false);
    }
  }

  async function handleRunImportedIncident(): Promise<void> {
    if (!importedIncident || !reasoning?.available) return;
    const request = beginRunSelection();
    setIsRunningImported(true);
    setErrorMessage(null);
    setStatusMessage(`Investigating the imported incident with ${providerLabel(reasoning.provider)} / ${reasoning.model}…`);
    try {
      const detail = await investigateImportedIncident(importedIncident.receipt);
      if (!selectedRunRequest.current.isCurrent(request)) return;
      assertRunIdentity(detail, { alertId: importedIncident.receipt.alert_id });
      applyAgentRunDetail(detail);
      await refreshRunHistory();
      await loadReferenceData();
      if (!selectedRunRequest.current.isCurrent(request)) return;
      if (detail.status === "failed") {
        setErrorMessage(detail.error_message ?? "The investigation failed. Inspect the recorded trace; no successful model result was substituted.");
      } else {
        setStatusMessage("Imported investigation recorded. Inspect evidence and policy findings, then export the selected run's report. Human review remains required.");
      }
    } catch (error) {
      if (selectedRunRequest.current.isCurrent(request)) {
        setStatusMessage(null);
        setErrorMessage(getErrorMessage(error));
      }
    } finally {
      if (selectedRunRequest.current.isCurrent(request)) setIsRunningImported(false);
    }
  }

  async function handleRunHarness(): Promise<void> {
    setIsRunningHarness(true);
    setActiveTab("harness");
    setErrorMessage(null);
    setStatusMessage("Running the local security harness against its configured components and workflow scenarios…");

    try {
      const response = await runSecurityHarness(null, false);
      setHarnessRun(response);
      setAvailability((current) => ({ ...current, harness: true }));
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
      setAvailability((current) => ({ ...current, evaluation: true }));
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

  async function selectRecordedRun(id: string): Promise<void> {
    if (!id) return;
    const requestId = beginRunSelection();
    setIsLoadingRun(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const { detail, chunks } = await loadRecordedAgentRun(id, getAgentRunDetail);
      if (!selectedRunRequest.current.isCurrent(requestId)) return;
      assertRunIdentity(detail, { runId: id });
      applyAgentRunDetail(detail, undefined, chunks);
    } catch (error) {
      if (selectedRunRequest.current.isCurrent(requestId)) setErrorMessage(getErrorMessage(error));
    } finally {
      if (selectedRunRequest.current.isCurrent(requestId)) setIsLoadingRun(false);
    }
  }

  const busy = isImportingIncident || isRunningImported || isLoadingRun || isBootstrapping || runningScenario !== null || isSeeding || isRunningHarness || isRunningEvaluation;
  const currentTab = WORKSPACE_TABS.find((tab) => tab.id === activeTab)!;
  const traceLoading = isRunningImported || isBootstrapping || runningScenario !== null || isLoadingRun;
  const selectedReport = selectedInvestigationReport(agentRun, traceLoading || isImportingIncident, importedIncident?.receipt.alert_id);

  return (
    <main className="operations-console">
      <MatrixEnvironment />
      <div className="signal-masthead">
        <div><p className="console-kicker"><span className="status-dot" aria-hidden="true" /> AI SECURITY / OPERATIONS</p><h1>Follow the evidence<span className="terminal-cursor" aria-hidden="true">_</span></h1><p>Investigate incidents. Inspect the reasoning. Keep control.</p></div>
        <div className="masthead-boundary"><ShieldCheck size={16} /><span>HUMAN REVIEW<br /><strong>ALWAYS REQUIRED</strong></span></div>
      </div>
      <div className="workspace-frame">
        <div className="workspace-titlebar"><span className="window-dots" aria-hidden="true"><i /><i /><i /></span><span>opsguard / operations</span><span className={health ? "connection-indicator online" : "connection-indicator"}>{isBootstrapping ? "CONNECTING" : health ? "BACKEND CONNECTED" : "BACKEND UNAVAILABLE"}</span></div>
        <div className="workspace-grid">
          <WorkspaceNavigation activeTab={activeTab} onChange={setActiveTab} />
          <div className="workspace-content">
            <div className="workspace-toolbar"><div><span className="view-index">/{currentTab.code}</span><h2>{currentTab.label}</h2></div><Button variant="ghost" disabled={busy} onClick={() => void bootstrapDashboard()} aria-label="Refresh workspace">{isBootstrapping ? <LoaderCircle size={14} className="animate-spin" /> : <RefreshCw size={14} />}<span>Refresh</span></Button></div>
            {errorMessage ? <div className="console-notice console-error" role="alert"><TriangleAlert size={17} /><div><strong>Workspace request needs attention.</strong><p>{errorMessage}. {health ? "Inspect backend logs for this request, then refresh." : "On this Mac, open http://localhost:3000 and confirm the backend is running. If using a different origin, configure it explicitly in backend CORS."}</p><p className="api-target">API target: {API_BASE_URL}</p></div></div> : null}
            {statusMessage && !errorMessage ? <div className="console-notice" role="status">{busy ? <LoaderCircle size={14} className="animate-spin" /> : <Check size={14} />}<span>{statusMessage}</span></div> : null}
            {activeTab !== "overview" && activeTab !== "harness" && activeTab !== "evaluation" ? <div className="recorded-run-selector"><label htmlFor="recorded-run">RECORDED RUN</label><select id="recorded-run" value={agentRun?.agent_run_id ?? ""} disabled={busy || !availability.runs} onChange={(event) => void selectRecordedRun(event.target.value)}><option value="" disabled>{isBootstrapping ? "Loading runs…" : !availability.runs ? "Run history unavailable" : "No run selected"}</option>{runHistory.map((run) => <option key={run.agent_run_id} value={run.agent_run_id}>{scenarioLabelForAlertId(run.alert_id) ?? "Investigation"} · {run.agent_run_id.slice(0, 8)} · {run.provenance === "fixture" ? "fixture" : run.status}</option>)}</select>{agentRun ? <ProvenanceLabel provenance={agentRun.provenance} /> : null}</div> : null}
            <section id={`panel-${activeTab}`} role="tabpanel" aria-labelledby={`tab-${activeTab}`} tabIndex={0} className="workspace-tab-panel">
              {activeTab === "overview" ? <>
                <div className="overview-grid">
                  <Card className="mission-card"><div className="panel-heading"><span><Terminal size={14} /> INVESTIGATION / LAUNCHER</span><span>INCIDENT TRIAGE</span></div><div className="mission-intro"><p className="text-accent font-mono text-xs">READY WHEN YOU ARE.</p><h3>Turn an alert into<br />a reviewable investigation.</h3><p>Run an incident through retrieval, typed local tools, model reasoning, and watchdog checks.</p></div>
                    <div className="mission-actions"><button className="mission-action" disabled={busy} onClick={() => setActiveTab("investigations")}><span className="mission-icon"><Database size={22} /></span><span><strong>Investigate incident evidence</strong><small>Your log export / JSON incident bundle</small></span><ArrowUpRight size={19} /></button><button className="mission-action" disabled={busy} onClick={() => setActiveTab("investigations")}><span className="mission-icon amber"><Cpu size={22} /></span><span><strong>Explore synthetic scenarios</strong><small>Optional examples / explicit seeding required</small></span><ArrowUpRight size={19} /></button></div>
                    {reasoning?.mode === "external" ? <p className="external-disclosure">Uses {reasoning.provider} / {reasoning.model}. Scenario evidence is sent to the configured model service.</p> : null}
                    <div className="mission-footer"><span>IMPORTED OBSERVATIONS OR EXPLICIT SAMPLE DATA</span><span>NO LIVE CLUSTER ACCESS</span></div>
                  </Card>
                  <SystemStatusCard health={health} documentsCount={availability.documents ? documents.length : null} trustedDocumentsCount={availability.documents ? trustedDocumentsCount : null} executableToolsCount={availability.tools ? toolGroups[0].tools.length : null} blockedToolsCount={availability.tools ? toolGroups[1].tools.length : null} policiesCount={availability.policies ? policies.length : null} isLoading={isBootstrapping} reasoning={reasoning} />
                </div>
                <div className="overview-bottom-grid"><Card><div className="panel-heading"><span><Zap size={14} /> SELECTED INVESTIGATION</span><span>RECORDED STATE</span></div>{agentRun ? <><div className="mt-4 flex flex-wrap items-center gap-2"><SafetyBadge value={agentRun.status} /><ProvenanceLabel provenance={agentRun.provenance} /></div><h3 className="mt-3 text-base text-white">{activeScenarioLabel}</h3><p className="mt-2 text-xs leading-5 text-slate-400">{formatTimestamp(agentRun.started_at)} · {agentRun.llm_provider} / {agentRun.model_version ?? "model not recorded"}</p><p className="mt-3 line-clamp-2 text-sm text-slate-300">{agentRun.final_recommendation?.summary ?? agentRun.error_message ?? "No recommendation recorded."}</p><button className="text-link mt-4" onClick={() => setActiveTab("investigations")}>Inspect recorded trace <ArrowRight size={13} /></button></> : <div className="empty-console"><span aria-hidden="true">[ — ]</span><p>{isBootstrapping ? "Loading recorded investigations…" : availability.runs ? "No investigation recorded. Import an incident bundle to start an investigation." : "Run history unavailable. No activity counts can be shown."}</p></div>}</Card>
                  <Card><div className="panel-heading"><span><FlaskConical size={14} /> SECURITY REGRESSION</span><span>HARNESS</span></div><div className="harness-overview-count">{isBootstrapping ? "…" : availability.harness ? harnessExecutionCounts(harnessRun) : "Unavailable"}</div><p className="text-xs leading-5 text-slate-400">{harnessRun ? executionProvenanceLabel(harnessRun.provenance) : "No executed cohort selected."} Passed / completed executed cases. Fixture history does not count.</p><div className="mt-4 flex flex-wrap gap-2"><Button disabled={busy || !health} onClick={() => void handleRunHarness()} variant="secondary">Run security harness <ArrowUpRight size={13} className="ml-2" /></Button><button className="text-link" onClick={() => setActiveTab("evaluation")}>Reports <ArrowRight size={13} /></button></div></Card></div>
                <div className="workspace-utility"><span><Database size={13} /> Need the bundled runbooks and example history?</span><button disabled={busy || !health} onClick={() => void handleSeedDemoData()}>{isSeeding ? "Seeding…" : "Seed sample data"} <ArrowRight size={12} /></button></div>
              </> : null}
              {activeTab === "investigations" ? <><IncidentImportCard imported={importedIncident} runtime={reasoning} disabled={busy} backendAvailable={Boolean(health)} isImporting={isImportingIncident} isRunning={isRunningImported} onSelectionChange={handleIncidentFileSelection} onImport={handleImportIncident} onRun={handleRunImportedIncident} /><InvestigationReportLinks selection={selectedReport} /><details className="sample-scenarios"><summary>Optional synthetic scenarios</summary><div className="workspace-utility mt-4"><span>These fixtures require explicit seeding before running.</span><Button disabled={busy || !health} onClick={() => void handleSeedDemoData()} variant="secondary">Seed sample data</Button></div><AlertScenarioCard latestRunStatus={agentRun?.status ?? null} onRunGpuScenario={() => handleRunScenario("gpu")} onRunPromptScenario={() => handleRunScenario("prompt")} runningScenario={runningScenario} disabled={busy || !health || !reasoning?.available} providerLabel={reasoning?.provider !== "deterministic" && reasoning ? `${providerLabel(reasoning.provider)} / ${reasoning.model}` : null} /></details><AgentRunTrace activeScenarioLabel={activeScenarioLabel} agentRun={agentRun} isLoading={traceLoading} /><StructuredActionsPanel recommendation={agentRun?.final_recommendation ?? null} /><WatchdogFindingsPanel recommendation={agentRun?.final_recommendation ?? null} /></> : null}
              {activeTab === "evidence" ? <><InvestigationReportLinks selection={selectedReport} /><ImportedEvidencePanel run={agentRun} /><RagContextPanel chunks={ragChunks} hasRecordedRun={agentRun !== null} isLoading={traceLoading} /><Card><div className="panel-heading"><span><Database size={14} /> CURRENT DOCUMENT CATALOG</span><span>SEPARATE FROM RUN SNAPSHOTS</span></div><p className="mt-3 text-xs text-slate-400">Changing the current catalog does not rewrite a historical investigation.</p>{!availability.documents ? <p className="empty-state">Document catalog unavailable.</p> : documents.length === 0 ? <p className="empty-state">No documents stored. Seed the sample data to load example runbooks.</p> : <div className="document-catalog">{documents.map((document) => <div key={document.id}><div><p>{document.title}</p><small>{document.source}</small></div><SafetyBadge value={document.trust_level} /></div>)}</div>}</Card></> : null}
              {activeTab === "tools" ? <><Card><div className="panel-heading"><span><Terminal size={14} /> TYPED TOOL REGISTRY</span><span>APPLICATION POLICY</span></div>{availability.tools ? <ToolRegistryGroups tools={tools} /> : <p className="empty-state">Tool definitions unavailable.</p>}</Card>{availability.attempts ? <ToolAttemptsPanel attempts={recentAttempts} /> : <Card><p className="empty-state">Tool attempt audit unavailable.</p></Card>}<ToolCallsPanel isLoading={traceLoading} toolCalls={agentRun?.tool_calls ?? []} /><Card><div className="panel-heading"><span><ShieldCheck size={14} /> WATCHDOG POLICIES</span></div>{availability.policies ? <div className="policy-catalog">{policies.map((policy) => <div key={policy.policy_id}><strong>{policy.title}</strong><code>{policy.policy_id}</code><p>{policy.description}</p></div>)}</div> : <p className="empty-state">Policy definitions unavailable.</p>}</Card></> : null}
              {activeTab === "harness" ? <><div className="tab-action-row"><p>Execute deterministic component, policy, tool-boundary, and workflow checks.</p><Button disabled={busy || !health} onClick={() => void handleRunHarness()}>{isRunningHarness ? <LoaderCircle size={14} className="animate-spin mr-2" /> : <FlaskConical size={14} className="mr-2" />}Run security harness</Button></div>{availability.harness || isBootstrapping ? <HarnessResultsPanel harnessRun={harnessRun} isLoading={isBootstrapping || isRunningHarness} scenarios={harnessScenarios} /> : <Card><p className="empty-state">Harness history unavailable. Refresh after restoring the backend connection.</p></Card>}</> : null}
              {activeTab === "evaluation" ? availability.evaluation || isBootstrapping ? <EvaluationSummaryCard isLoading={isBootstrapping} isRunningEvaluation={isRunningEvaluation} onRunEvaluation={handleRunEvaluation} summary={evaluationSummary} /> : <Card><p className="empty-state">Evaluation data unavailable. Refresh after restoring the backend connection.</p></Card> : null}
            </section>
            <footer className="workspace-footer"><span><ShieldCheck size={12} /> RECOMMENDATIONS STOP AT HUMAN REVIEW</span><span>NO APPROVE / RESUME EXECUTION</span></footer>
          </div>
        </div>
      </div>
      <div className="console-bottom-line"><span>OPSGUARD / EVIDENCE INTEGRITY SYSTEM</span><span>TRUST IS A BOUNDARY, NOT A PROMPT.</span></div>
    </main>
  );
}
