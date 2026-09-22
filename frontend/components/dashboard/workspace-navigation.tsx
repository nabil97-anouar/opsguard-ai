"use client";

import { Activity, BookOpen, Braces, FlaskConical, LayoutDashboard, ShieldCheck } from "lucide-react";

export const WORKSPACE_TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, code: "01" },
  { id: "investigations", label: "Investigations", icon: Activity, code: "02" },
  { id: "evidence", label: "Evidence", icon: BookOpen, code: "03" },
  { id: "tools", label: "Tools & policy", icon: Braces, code: "04" },
  { id: "harness", label: "Security harness", icon: ShieldCheck, code: "05" },
  { id: "evaluation", label: "Evaluation", icon: FlaskConical, code: "06" },
] as const;
export type WorkspaceTab = typeof WORKSPACE_TABS[number]["id"];

export function nextWorkspaceTab(current: WorkspaceTab, key: string): WorkspaceTab | null {
  const index = WORKSPACE_TABS.findIndex((tab) => tab.id === current);
  if (key === "Home") return WORKSPACE_TABS[0].id;
  if (key === "End") return WORKSPACE_TABS[WORKSPACE_TABS.length - 1].id;
  if (key === "ArrowRight" || key === "ArrowDown") return WORKSPACE_TABS[(index + 1) % WORKSPACE_TABS.length].id;
  if (key === "ArrowLeft" || key === "ArrowUp") return WORKSPACE_TABS[(index - 1 + WORKSPACE_TABS.length) % WORKSPACE_TABS.length].id;
  return null;
}

export function WorkspaceNavigation({ activeTab, onChange }: { activeTab: WorkspaceTab; onChange: (tab: WorkspaceTab) => void }) {
  return <nav className="workspace-navigation" aria-label="Operations workspace"><p className="nav-caption">WORKSPACE</p><div role="tablist" aria-label="Investigation views">
    {WORKSPACE_TABS.map(({ id, label, icon: Icon, code }) => <button key={id} id={`tab-${id}`} role="tab" aria-selected={activeTab === id} aria-controls={`panel-${id}`} tabIndex={activeTab === id ? 0 : -1} onClick={() => onChange(id)} onKeyDown={(event) => {
      const next = nextWorkspaceTab(id, event.key);
      if (next) { event.preventDefault(); onChange(next); document.getElementById(`tab-${next}`)?.focus(); }
    }}><span className="nav-code">{code}</span><Icon size={16} /><span>{label}</span><span className="nav-arrow" aria-hidden="true">›</span></button>)}
  </div><div className="nav-footnote"><span className="nav-mark" aria-hidden="true">[ O / G ]</span><p>EVIDENCE FIRST.<br />HUMAN REVIEW REQUIRED.</p><span>LOCAL TOOL ADAPTERS<br />NO LIVE REMEDIATION</span></div></nav>;
}
