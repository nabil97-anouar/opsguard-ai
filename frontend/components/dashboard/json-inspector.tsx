import { CardDescription } from "@/components/ui/card";

type JsonInspectorProps = {
  title: string;
  data: unknown;
  defaultOpen?: boolean;
};

export function JsonInspector({
  title,
  data,
  defaultOpen = false
}: JsonInspectorProps) {
  const serialized = JSON.stringify(data, null, 2);

  return (
    <details
      className="rounded-2xl border border-white/8 bg-black/20"
      open={defaultOpen}
    >
      <summary className="cursor-pointer list-none px-4 py-3 text-sm text-slate-200">
        <div className="flex items-center justify-between gap-3">
          <span>{title}</span>
          <span className="font-mono text-xs uppercase tracking-[0.18em] text-slate-400">
            Expand JSON
          </span>
        </div>
      </summary>
      <div className="border-t border-white/8 px-4 py-4">
        <CardDescription className="sr-only">{title}</CardDescription>
        <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-2xl bg-ink/70 p-4 font-mono text-xs leading-6 text-slate-200">
          {serialized}
        </pre>
      </div>
    </details>
  );
}
