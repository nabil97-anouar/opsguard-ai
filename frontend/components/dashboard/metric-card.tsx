import { Card } from "@/components/ui/card";

type MetricCardProps = {
  label: string;
  value: string;
  change: string;
};

export function MetricCard({
  label,
  value,
  change
}: MetricCardProps) {
  return (
    <Card className="border-white/8 bg-gradient-to-b from-white/[0.06] to-white/[0.02]">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <p className="mt-4 font-mono text-4xl font-semibold text-slate-50">{value}</p>
      <p className="mt-3 text-sm text-slate-300">{change}</p>
    </Card>
  );
}
