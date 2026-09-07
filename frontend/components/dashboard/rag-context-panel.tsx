import { BookMarked, TriangleAlert } from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { RetrievalChunk } from "@/lib/types";

type RagContextPanelProps = {
  chunks: RetrievalChunk[];
  isLoading: boolean;
  hasRecordedRun: boolean;
};

export function RagContextPanel({ chunks, isLoading, hasRecordedRun }: RagContextPanelProps) {
  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            RAG citations
          </p>
          <CardTitle className="mt-3">Retrieved context with provenance</CardTitle>
          <CardDescription className="mt-3">
            These snapshots show what this run retrieved, including its recorded trust
            and source references. Current document changes do not update this evidence.
          </CardDescription>
        </div>
        <SafetyBadge value={`${chunks.length} chunks`} />
      </div>

      <div className="mt-8 space-y-4">
        {isLoading && chunks.length === 0 ? (
          <p className="text-sm text-slate-300">Loading retrieval context…</p>
        ) : null}

        {!isLoading && chunks.length === 0 ? (
          <p className="rounded-2xl border border-white/8 bg-ink/60 p-4 text-sm text-slate-300">
            {hasRecordedRun
              ? "No retrieval evidence was recorded for this run. Historical evidence is not replaced with a fresh search."
              : "Run an investigation to record retrieval evidence and source references."}
          </p>
        ) : null}

        {chunks.map((chunk) => (
          <div
            className="rounded-2xl border border-white/8 bg-ink/60 p-5"
            key={chunk.evidence_id ?? chunk.chunk_id}
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-2xl">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accentSoft">
                    <BookMarked className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="font-medium text-white">{chunk.title}</p>
                    <p className="mt-1 text-sm text-slate-400">{chunk.source}</p>
                  </div>
                </div>

                <p className="mt-4 text-sm leading-6 text-slate-200">
                  {chunk.content_excerpt}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <SafetyBadge value={chunk.trust_level} />
                <SafetyBadge value={chunk.risk_level} />
                {chunk.is_suspicious ? <SafetyBadge value="suspicious" /> : null}
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  Citation
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  {chunk.citation}
                </p>
                <p className="mt-2 font-mono text-xs text-slate-400">
                  Score {chunk.score.toFixed(2)} · Chunk {chunk.chunk_index}
                </p>
                <p className="mt-2 break-all font-mono text-xs text-slate-400">
                  Document {chunk.document_id} · Chunk ID {chunk.chunk_id}
                </p>
                <p className="mt-2 break-all font-mono text-xs text-slate-400">
                  {chunk.evidence_id ? `Evidence ${chunk.evidence_id}` : "Evidence ID not recorded (legacy run)"}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  {chunk.observed_at ? `Retrieved ${new Date(chunk.observed_at).toLocaleString()}` : "Retrieval timestamp not recorded (legacy run)"}
                </p>
              </div>

              <div className="rounded-2xl border border-white/8 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  Matched patterns
                </p>
                {chunk.matched_patterns.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {chunk.matched_patterns.map((pattern) => (
                      <div
                        className="inline-flex items-center gap-2 rounded-full border border-critical/20 bg-critical/10 px-3 py-1 text-xs text-red-100"
                        key={pattern}
                      >
                        <TriangleAlert className="h-3.5 w-3.5" />
                        {pattern}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-300">
                    No prompt-injection markers were detected for this chunk.
                  </p>
                )}
              </div>
            </div>

            <div className="mt-4">
              <JsonInspector data={chunk} title="Chunk details" />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
