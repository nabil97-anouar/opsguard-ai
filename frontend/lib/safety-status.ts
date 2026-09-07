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
