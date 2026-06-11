import { cn } from "@/lib/utils";

type SafetyBadgeProps = {
  value: string;
  className?: string;
};

const toneMap: Array<{
  match: (value: string) => boolean;
  className: string;
}> = [
  {
    match: (value) =>
      ["passed", "healthy", "trusted", "clean", "allow", "executed", "configured"].some(
        (token) => value.includes(token)
      ),
    className:
      "border-success/30 bg-success/10 text-success"
  },
  {
    match: (value) =>
      [
        "warning",
        "partial",
        "untrusted",
        "investigating",
        "open",
        "allow with warnings"
      ].some((token) => value.includes(token)),
    className:
      "border-warning/30 bg-warning/10 text-amber-100"
  },
  {
    match: (value) =>
      [
        "block",
        "blocked",
        "failed",
        "critical",
        "danger",
        "suspicious",
        "require human",
        "high"
      ].some((token) => value.includes(token)),
    className:
      "border-critical/30 bg-critical/10 text-red-100"
  }
];

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function SafetyBadge({ value, className }: SafetyBadgeProps) {
  const normalized = value.trim().toLowerCase();
  const tone = toneMap.find((item) => item.match(normalized))?.className ??
    "border-white/10 bg-white/[0.05] text-slate-200";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em]",
        tone,
        className
      )}
    >
      {humanize(value)}
    </span>
  );
}
