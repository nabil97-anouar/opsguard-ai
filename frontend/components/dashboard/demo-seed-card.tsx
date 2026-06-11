import { DatabaseZap, FlaskConical, LoaderCircle } from "lucide-react";

import { JsonInspector } from "@/components/dashboard/json-inspector";
import { SafetyBadge } from "@/components/dashboard/safety-badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import type { DemoSeedSummary } from "@/lib/types";

type DemoSeedCardProps = {
  onSeed: () => Promise<void> | void;
  onRunHarness: () => Promise<void> | void;
  isSeeding: boolean;
  isRunningHarness: boolean;
  statusMessage: string | null;
  seedSummary: DemoSeedSummary | null;
};

export function DemoSeedCard({
  onSeed,
  onRunHarness,
  isSeeding,
  isRunningHarness,
  statusMessage,
  seedSummary
}: DemoSeedCardProps) {
  return (
    <Card className="border-white/8 bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Demo controls
          </p>
          <CardTitle className="mt-3">Seed and exercise the local stack</CardTitle>
          <CardDescription className="mt-3">
            Use deterministic demo data and the local security harness to make
            the dashboard immediately useful without any external dependencies.
          </CardDescription>
        </div>
        <SafetyBadge value="no real infrastructure actions" />
      </div>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        <Button
          className="w-full justify-center"
          disabled={isSeeding || isRunningHarness}
          onClick={onSeed}
          size="lg"
        >
          {isSeeding ? (
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <DatabaseZap className="mr-2 h-4 w-4" />
          )}
          Seed demo data
        </Button>

        <Button
          className="w-full justify-center"
          disabled={isSeeding || isRunningHarness}
          onClick={onRunHarness}
          size="lg"
          variant="secondary"
        >
          {isRunningHarness ? (
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FlaskConical className="mr-2 h-4 w-4" />
          )}
          Run security harness
        </Button>
      </div>

      <div className="mt-6 rounded-2xl border border-white/8 bg-ink/60 p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
          Current status
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-200">
          {statusMessage ??
            "Seed the deterministic dataset first, then run one of the bundled agent or harness scenarios."}
        </p>
      </div>

      {seedSummary ? (
        <div className="mt-6">
          <JsonInspector
            data={seedSummary}
            title="Latest demo seed summary"
          />
        </div>
      ) : null}
    </Card>
  );
}
