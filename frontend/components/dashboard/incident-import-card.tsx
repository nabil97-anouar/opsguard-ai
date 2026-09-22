"use client";

import { useRef, useState } from "react";
import { ArrowRight, Download, FileJson, LoaderCircle, Upload } from "lucide-react";
import { Card, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SafetyBadge } from "./safety-badge";
import { JsonInspector } from "./json-inspector";
import { getErrorMessage } from "@/lib/api";
import { incidentDataDestination } from "@/lib/incident-import";
import { INCIDENT_FILE_ACCEPT, prepareIncidentFile } from "@/lib/incident-file-converter";
import type { ImportedIncident, IncidentBundle, ReasoningRuntime } from "@/lib/types";

type IncidentImportCardProps = {
  imported: ImportedIncident | null;
  runtime: ReasoningRuntime | null;
  disabled: boolean;
  backendAvailable?: boolean;
  isImporting: boolean;
  isRunning: boolean;
  onSelectionChange: () => void;
  onImport: (bundle: IncidentBundle) => Promise<void>;
  onRun: () => Promise<void>;
};

type PreparedFile = Awaited<ReturnType<typeof prepareIncidentFile>>;

export function IncidentImportCard({ imported, runtime, disabled, backendAvailable = true, isImporting, isRunning, onSelectionChange, onImport, onRun }: IncidentImportCardProps) {
  const [prepared, setPrepared] = useState<PreparedFile | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const selection = useRef(0);
  const bundle = prepared?.bundle ?? null;
  const isConvertedText = prepared?.converted && prepared.format === "text";

  async function chooseFile(file: File | undefined) {
    const current = ++selection.current;
    setPrepared(null);
    setError(null);
    setFileName(file?.name ?? null);
    onSelectionChange();
    if (!file) { setReading(false); return; }
    setReading(true);
    try {
      const result = await prepareIncidentFile(file);
      if (selection.current === current) setPrepared(result);
    } catch (failure) {
      if (selection.current === current) setError(getErrorMessage(failure));
    } finally {
      if (selection.current === current) setReading(false);
    }
  }

  async function importSelected() {
    if (!bundle || !backendAvailable) return;
    const current = selection.current;
    setError(null);
    try { await onImport(bundle); } catch (failure) {
      if (selection.current === current) setError(getErrorMessage(failure));
    }
  }

  function downloadJson() {
    if (!bundle) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2) + "\n"], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${(fileName ?? "incident").replace(/\.[^.]+$/, "")}.incident.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <Card className="incident-import-card">
    <div className="panel-heading"><span><Upload size={14} /> INCIDENT / IMPORT</span><span>AUTO CONVERT · MAX 1 MiB</span></div>
    <CardTitle className="mt-4">Investigate your incident evidence</CardTitle>
    <p className="mt-2 text-xs leading-6 text-slate-400">Choose a log, TXT, CSV, JSONL, Markdown, or JSON export. OpsGuard converts it to incident JSON in your browser. Review the result, then import it as untrusted evidence. No model is used for conversion.</p>
    <div className="incident-examples"><span>Start from a synthetic example:</span><a href="/examples/incidents/normal-workload.json" download>Normal workload ↓</a><a href="/examples/incidents/suspicious-activity.json" download>Suspicious activity ↓</a></div>
    <div className="incident-import-grid">
      <div className="incident-file-stage">
        <label htmlFor="incident-json-file"><span className="import-stage-number">01</span> Select, convert, and import</label>
        <input id="incident-json-file" type="file" accept={INCIDENT_FILE_ACCEPT} disabled={disabled || reading} onChange={(event) => void chooseFile(event.target.files?.[0])} />
        {reading ? <p className="mt-3 text-xs text-slate-400" role="status">Converting the selected file locally…</p> : null}
        {bundle && prepared ? <div className="incident-file-preview">
          <p><FileJson size={13} /> {fileName}</p>
          <p role="status">{prepared.converted ? `Converted automatically from ${prepared.format.toUpperCase()} to incident JSON.` : "Incident JSON is ready to import."}</p>
          {prepared.summary ? <p className="text-xs text-slate-300">{prepared.summary.source_line_count} source lines → {prepared.summary.observation_count} evidence chunks{prepared.summary.recognized_journal_lines > 0 ? ` · ${prepared.summary.recognized_journal_lines} journal lines recognized` : ""}. Chunks preserve file text; they are not separate incidents.</p> : null}
          <strong>{bundle.incident.title}</strong>
          <dl><div><dt>Source label</dt><dd>{bundle.incident.source}</dd></div><div><dt>Host/node</dt><dd>{bundle.incident.node ?? "Unknown"}</dd></div><div><dt>Event time</dt><dd>{bundle.incident.observed_at ?? (prepared.summary && prepared.summary.recognized_journal_lines > 0 ? "See source timestamps and conversion notes" : "Not provided")}</dd></div><div><dt>{isConvertedText ? "Evidence chunks" : "Observations"}</dt><dd>{bundle.observations.length}</dd></div><div><dt>Incident severity{prepared.converted ? " (conversion default)" : ""}</dt><dd>{bundle.incident.severity}</dd></div></dl>
          {prepared.warnings.length > 0 ? <details className="my-3 text-xs leading-5 text-amber-200"><summary className="cursor-pointer">Review conversion notes ({prepared.warnings.length})</summary><ul className="mt-2 list-disc space-y-2 pl-4" aria-label="Conversion notes">{prepared.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details> : null}
          <JsonInspector title="Review incident JSON" data={bundle} />
          <Button className="mt-3" variant="ghost" onClick={downloadJson}><Download size={14} className="mr-2" />Download JSON</Button>
        </div> : null}
        {error ? <p className="incident-import-error" role="alert">{error}</p> : null}
        {!backendAvailable ? <p className="mt-3 text-xs leading-5 text-slate-400">You can convert and download locally. Start the backend to import and investigate.</p> : null}
        <Button className="mt-4" disabled={disabled || reading || !bundle || !backendAvailable || imported !== null} onClick={() => void importSelected()} variant="secondary">{isImporting ? <LoaderCircle size={14} className="mr-2 animate-spin" /> : <Upload size={14} className="mr-2" />}{isImporting ? "Importing…" : "Import incident"}</Button>
      </div>
      <div className="incident-run-stage"><p className="import-stage-label"><span className="import-stage-number">02</span> Review destination and run</p><p className="incident-data-notice">{incidentDataDestination(runtime)}</p>
        {imported ? <div className="imported-receipt"><div className="flex flex-wrap items-center gap-2"><SafetyBadge value={imported.receipt.trust_level} /><span>{imported.receipt.observation_count} evidence entries stored</span></div><strong>{imported.bundle.incident.title}</strong><p>Bundle {imported.receipt.bundle_id}</p><p>Alert {imported.receipt.alert_id}</p><p>Imported {imported.receipt.imported_at}</p></div> : <p className="mt-4 text-xs leading-6 text-slate-400">Import an incident first. A separate Run investigation action authorizes reasoning with the selected provider.</p>}
        <Button className="mt-4" disabled={disabled || !backendAvailable || !imported || !runtime?.available} onClick={() => void onRun()}>{isRunning ? <LoaderCircle size={14} className="mr-2 animate-spin" /> : <ArrowRight size={14} className="mr-2" />}{isRunning ? "Investigating…" : "Run imported investigation"}</Button>
      </div>
    </div>
  </Card>;
}
