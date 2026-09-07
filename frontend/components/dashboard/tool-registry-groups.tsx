import { toolRegistryGroups } from "../../lib/dashboard-data";
import type { ToolListItem } from "../../lib/types";

export function ToolRegistryGroups({ tools }: { tools: ToolListItem[] }) {
  return toolRegistryGroups(tools).map((group) => (
    <section className="mt-4" key={group.key} aria-label={group.label}>
      <p className="text-sm font-medium text-slate-200">
        {group.label} ({group.tools.length})
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {group.tools.map((tool) => (
          <span className="rounded-full border border-white/10 px-3 py-1 font-mono text-xs text-slate-200" key={tool.name}>
            {tool.name}
          </span>
        ))}
        {group.tools.length === 0 ? <p className="text-sm text-slate-400">None registered.</p> : null}
      </div>
    </section>
  ));
}
