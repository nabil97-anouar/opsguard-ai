import { FileWarning, Radar, ShieldAlert, Sparkles } from "lucide-react";

import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";

const metrics = [
  {
    label: "Active alerts",
    value: "0",
    change: "Milestone 2 will add persisted alert records."
  },
  {
    label: "Agent runs",
    value: "0",
    change: "Workflow execution arrives in Milestone 6."
  },
  {
    label: "Safety events",
    value: "0",
    change: "Watchdog and harness signals arrive in later milestones."
  },
  {
    label: "Confidence avg",
    value: "--",
    change: "Metacognitive scoring is scaffolded, not implemented yet."
  }
];

const panels = [
  {
    icon: FileWarning,
    title: "Incident Intake",
    description:
      "Future home for alert ingestion, classification, and investigation status."
  },
  {
    icon: Radar,
    title: "RAG Evidence",
    description:
      "Runbook retrieval, provenance, and evidence panels arrive after ingestion and vector indexing."
  },
  {
    icon: ShieldAlert,
    title: "Security Harness",
    description:
      "Prompt injection, unsafe tool-use, and kill-chain test scenarios are reserved for Milestone 8."
  }
];

export default function DashboardPage() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 pb-20 pt-10 lg:px-8">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-accentSoft">
            Dashboard placeholder
          </p>
          <h1 className="mt-3 font-display text-4xl font-semibold text-white">
            OpsGuard AI command surface
          </h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-slate-300">
            This page is intentionally scaffolded for the portfolio flow: alert
            telemetry, agent traces, safety reviews, and evidence panels will be
            layered in milestone by milestone.
          </p>
        </div>

        <div className="rounded-full border border-accent/20 bg-accent/10 px-4 py-2 font-mono text-sm text-accentSoft">
          MILESTONE_01_READY
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard
            change={metric.change}
            key={metric.label}
            label={metric.label}
            value={metric.value}
          />
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-white/8 bg-gradient-to-b from-white/[0.06] to-white/[0.03]">
          <p className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-slate-400">
            <Sparkles className="h-4 w-4 text-accentSoft" />
            Scaffold status
          </p>
          <CardTitle className="mt-4">
            What exists right now
          </CardTitle>
          <CardDescription className="mt-3">
            The frontend shell, the backend health endpoint, environment
            handling, Docker Compose, and future-ready module boundaries are all
            in place.
          </CardDescription>

          <div className="mt-8 space-y-4 text-sm leading-6 text-slate-200">
            <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
              FastAPI app factory with CORS, structured logging, and typed
              settings
            </div>
            <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
              Next.js App Router shell with a premium landing page and dashboard
              placeholder
            </div>
            <div className="rounded-2xl border border-white/8 bg-ink/60 p-4">
              Demo-friendly local infrastructure scaffold for PostgreSQL and
              Qdrant
            </div>
          </div>
        </Card>

        <div className="grid gap-6">
          {panels.map((panel) => {
            const Icon = panel.icon;

            return (
              <Card className="border-white/8 bg-white/[0.03]" key={panel.title}>
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accent">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-xl">{panel.title}</CardTitle>
                    <CardDescription className="mt-3">
                      {panel.description}
                    </CardDescription>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </section>
    </main>
  );
}
