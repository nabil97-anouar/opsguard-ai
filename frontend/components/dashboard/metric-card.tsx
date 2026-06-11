import type { LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type MetricCardProps = {
  label: string;
  value: string;
  change: string;
  icon?: LucideIcon;
  tone?: "accent" | "success" | "warning" | "critical";
};

export function MetricCard({
  label,
  value,
  change,
  icon: Icon,
  tone = "accent"
}: MetricCardProps) {
  const toneClasses = {
    accent: "border-accent/20 bg-accent/10 text-accentSoft",
    success: "border-success/20 bg-success/10 text-success",
    warning: "border-warning/20 bg-warning/10 text-amber-100",
    critical: "border-critical/20 bg-critical/10 text-red-100"
  };

  return (
    <Card className="border-white/8 bg-gradient-to-b from-white/[0.06] to-white/[0.02]">
      <div className="flex items-start justify-between gap-4">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{label}</p>
        {Icon ? (
          <span
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-2xl border",
              toneClasses[tone]
            )}
          >
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
      </div>
      <p className="mt-4 font-mono text-4xl font-semibold text-slate-50">{value}</p>
      <p className="mt-3 text-sm text-slate-300">{change}</p>
    </Card>
  );
}
