import Link from "next/link";
import {
  Activity,
  BrainCircuit,
  Database,
  Radar,
  Shield,
  Siren
} from "lucide-react";

import { FeatureCard } from "@/components/home/feature-card";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { API_BASE_URL } from "@/lib/config";

const features = [
  {
    icon: BrainCircuit,
    title: "Metacognitive self-assessment",
    description:
      "The agent estimates confidence, missing evidence, and capability limits before recommending next steps."
  },
  {
    icon: Radar,
    title: "Evidence-grounded incident triage",
    description:
      "Runbooks, incident reports, and future tool outputs are treated as untrusted evidence that must be cited."
  },
  {
    icon: Shield,
    title: "Built-in AI security harness",
    description:
      "Prompt injection, tool misuse, and AI kill-chain scenarios are first-class tests, not an afterthought."
  }
];

const architectureLayers = [
  "Next.js dashboard for alerts, traces, and approvals",
  "FastAPI backend with typed configuration and structured logs",
  "PostgreSQL + Qdrant for operational memory and retrieval",
  "Future agent workflow, safety watchdog, and harness modules"
];

const valueSignals = [
  { label: "Incident domains", value: "Cloud · DevOps · SaaS · GPU · HPC" },
  { label: "Security posture", value: "Allowlisted tools · Human approval · Audit trail" },
  { label: "Milestone", value: "01 / Scaffold live" }
];

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 pb-20 pt-10 lg:px-8">
      <section className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-accentSoft">
            <Siren className="h-3.5 w-3.5" />
            Flagship Portfolio Project
          </div>

          <h1 className="mt-6 max-w-4xl font-display text-5xl font-semibold leading-tight text-white md:text-6xl">
            Secure self-aware AI agents for incident triage and AI security
            testing
          </h1>

          <p className="mt-6 max-w-3xl text-lg leading-8 text-slate-300">
            OpsGuard AI demonstrates how operational AI systems should behave:
            grounded in evidence, explicit about uncertainty, and careful about
            risky actions.
          </p>

          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
            Here, <span className="text-slate-200">self-aware</span> does not
            mean consciousness. It means the agent evaluates confidence, missing
            evidence, and capability boundaries before it proceeds.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link className={buttonVariants({ size: "lg" })} href="/dashboard">
              Open Dashboard
            </Link>
            <a
              className={buttonVariants({ variant: "secondary", size: "lg" })}
              href={`${API_BASE_URL}/health`}
              rel="noreferrer"
              target="_blank"
            >
              Check Backend Health
            </a>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {valueSignals.map((signal) => (
              <Card
                className="border-white/8 bg-white/[0.03] p-5"
                key={signal.label}
              >
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
                  {signal.label}
                </p>
                <p className="mt-3 text-sm leading-6 text-slate-200">
                  {signal.value}
                </p>
              </Card>
            ))}
          </div>
        </div>

        <Card className="relative overflow-hidden border-accent/20 bg-gradient-to-br from-white/[0.07] via-white/[0.04] to-accent/10 p-7">
          <div className="absolute right-6 top-6 h-24 w-24 rounded-full bg-accent/20 blur-3xl" />
          <div className="relative">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-accentSoft">
                  Mission Control
                </p>
                <h2 className="mt-2 font-display text-2xl font-semibold">
                  Safer operational AI by design
                </h2>
              </div>
              <div className="animate-float rounded-full border border-success/30 bg-success/10 px-3 py-1 font-mono text-xs text-success">
                MOCK MODE
              </div>
            </div>

            <div className="mt-8 grid gap-4">
              <div className="rounded-2xl border border-white/10 bg-ink/60 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-300">Confidence gate</span>
                  <span className="font-mono text-sm text-success">0.82</span>
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full w-[82%] rounded-full bg-gradient-to-r from-warning via-accent to-success" />
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-ink/60 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm text-slate-200">
                  <Database className="h-4 w-4 text-accent" />
                  Evidence posture
                </div>
                <ul className="space-y-3 text-sm text-slate-300">
                  <li>Runbooks and reports are untrusted until validated.</li>
                  <li>Tool outputs remain typed, allowlisted, and auditable.</li>
                  <li>Risky actions stay recommendation-only until approved.</li>
                </ul>
              </div>

              <div className="rounded-2xl border border-critical/20 bg-critical/10 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-red-200">
                  Safety rule
                </p>
                <p className="mt-2 text-sm leading-6 text-red-50">
                  No arbitrary shell execution. Dangerous actions are simulated
                  recommendations only.
                </p>
              </div>
            </div>
          </div>
        </Card>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {features.map((feature) => (
          <FeatureCard
            description={feature.description}
            icon={feature.icon}
            key={feature.title}
            title={feature.title}
          />
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-white/8 bg-white/[0.03]">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            Architecture summary
          </p>
          <CardTitle className="mt-3">
            Multi-layer system, not a generic chatbot
          </CardTitle>
          <CardDescription className="mt-3 max-w-2xl">
            The scaffold already separates the frontend experience, backend API,
            future storage services, and the modules reserved for RAG, tools,
            metacognition, safety, and evaluation.
          </CardDescription>

          <div className="mt-8 grid gap-4">
            {architectureLayers.map((layer, index) => (
              <div
                className="flex items-start gap-4 rounded-2xl border border-white/8 bg-ink/60 p-4"
                key={layer}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-accent/20 bg-accent/10 font-mono text-sm text-accentSoft">
                  {index + 1}
                </div>
                <p className="text-sm leading-6 text-slate-200">{layer}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="border-white/8 bg-gradient-to-b from-white/[0.05] to-white/[0.02]">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">
            What this repo is proving
          </p>
          <div className="mt-6 grid gap-4">
            {[
              "Production-style naming, folders, and environment setup from day one",
              "Local-first demo path with mock LLM support and no paid API requirement",
              "A future-ready path for secure agent workflows, RAG, and evaluation"
            ].map((point) => (
              <div
                className="flex gap-3 rounded-2xl border border-white/8 bg-ink/60 p-4"
                key={point}
              >
                <Activity className="mt-0.5 h-4 w-4 shrink-0 text-accentSoft" />
                <p className="text-sm leading-6 text-slate-200">{point}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 rounded-2xl border border-accent/20 bg-accent/10 p-5">
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-accentSoft">
              Next up
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-100">
              Milestone 2 will add persistence, SQLModel domain entities, and
              the first CRUD API for alerts and documents.
            </p>
          </div>
        </Card>
      </section>
    </main>
  );
}
