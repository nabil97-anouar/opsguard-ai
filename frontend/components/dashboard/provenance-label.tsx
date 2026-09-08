import { executionProvenanceLabel } from "@/lib/dashboard-data";

export function ProvenanceLabel({ provenance }: { provenance: string | null | undefined }) {
  return (
    <span
      className="inline-flex rounded-full border border-white/20 bg-white/[0.05] px-3 py-1 text-xs text-slate-200"
      data-provenance={provenance === "executed" || provenance === "fixture" ? provenance : "legacy_unknown"}
    >
      {executionProvenanceLabel(provenance)}
    </span>
  );
}
