import { cn } from "@/lib/utils";
import { badgeToneClasses, safetyBadgeTone } from "@/lib/safety-status";

type SafetyBadgeProps = {
  value: string;
  className?: string;
};

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function SafetyBadge({ value, className }: SafetyBadgeProps) {
  const tone = badgeToneClasses[safetyBadgeTone(value)];

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
