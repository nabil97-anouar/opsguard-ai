import type { TrustLevel } from "./types";

export type PolicyStatus = "allow" | "allow_with_warnings" | "blocked" | "require_human_approval";
export type BadgeTone = "success" | "warning" | "critical" | "neutral";

const securityTones: Record<TrustLevel | PolicyStatus, BadgeTone> = {
  trusted: "success",
  untrusted: "warning",
  quarantined: "critical",
  allow: "success",
  allow_with_warnings: "warning",
  blocked: "critical",
  require_human_approval: "warning"
};

const statusTones: Readonly<Record<string, BadgeTone>> = {
  ...securityTones,
  block: "critical",
  passed: "success",
  healthy: "success",
  clean: "success",
  executed: "success",
  succeeded: "success",
  configured: "success",
  warning: "warning",
  partial: "warning",
  investigating: "warning",
  open: "warning",
  pending: "warning",
  waiting_for_human: "warning",
  "human review required": "warning",
  denied: "critical",
  invoked: "warning",
  requested: "neutral",
  validated: "neutral",
  candidate: "neutral",
  pending_human_review: "warning",
  failed: "critical",
  error: "critical",
  critical: "critical",
  danger: "critical",
  suspicious: "critical",
  high: "critical",
  restricted: "critical"
};

export function safetyBadgeTone(value: string): BadgeTone {
  const normalized = value.trim().toLowerCase();
  return Object.prototype.hasOwnProperty.call(statusTones, normalized)
    ? statusTones[normalized]
    : "neutral";
}

export const badgeToneClasses: Record<BadgeTone, string> = {
  success: "border-success/30 bg-success/10 text-success",
  warning: "border-warning/30 bg-warning/10 text-amber-50",
  critical: "border-critical/30 bg-critical/10 text-red-100",
  neutral: "border-white/10 bg-white/[0.05] text-slate-200"
};


const watchdogVerdicts: Record<string, { label: string; tone: BadgeTone }> = {
  allow: { label: "Policy permits review", tone: "neutral" },
  allow_with_warnings: { label: "Review with policy warnings", tone: "warning" },
  require_human_approval: { label: "Human review required", tone: "warning" },
  block: { label: "Blocked by policy", tone: "critical" }
};

export function watchdogVerdict(value: string | null | undefined) {
  return value && Object.prototype.hasOwnProperty.call(watchdogVerdicts, value)
    ? watchdogVerdicts[value] : { label: "Policy verdict unavailable", tone: "neutral" as BadgeTone };
}

export function recommendationLifecycle(value: string | undefined): string {
  switch (value) {
    case "candidate": return "Candidate — policy review not completed";
    case "pending_human_review": return "Policy checked — pending human review, not approved";
    case "blocked": return "Blocked — not valid for action review";
    default: return "Historical artifact — policy validation unknown";
  }
}
