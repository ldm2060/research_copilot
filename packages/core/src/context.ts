import * as fs from "node:fs";
import { researchPaths } from "./paths.js";
import { listTasks } from "./task-store.js";
import { getActive } from "./active.js";
import { computeResearchState, type ResearchState } from "./research-state.js";
import { extractWorkflowState } from "./workflow.js";

export interface BuildOptions { format: "text" | "json"; now: string; eventName?: string; }

export function renderResearchState(rs: ResearchState): string {
  const lines: string[] = ["[research-state]"];
  lines.push(`Active: ${rs.active ? `${rs.active.id} (${rs.active.kind}, ${rs.active.status})` : "none"}`);
  lines.push(`Graph: ${rs.graph.completed} completed · ${rs.graph.in_progress} in_progress · ${rs.graph.blocked} blocked`);
  if (rs.openGaps.length) {
    lines.push("Open gaps:");
    for (const g of rs.openGaps) lines.push(`  - [from ${g.taskId}] ${g.desc} -> suggests: ${g.suggest_kind}`);
  }
  if (rs.recommendations.length) {
    lines.push("Recommended next (you decide, nothing auto-created):");
    rs.recommendations.forEach((r, i) => lines.push(`  ${i + 1}. ${r.reason}`));
  }
  lines.push(`turn-ts: ${rs.turnTs}`);
  return lines.join("\n");
}

export function buildContext(repo: string, opts: BuildOptions): string {
  const tasks = listTasks(repo);
  const active = getActive(repo) ?? undefined;
  const activeStatus = active ? tasks.find(t => t.id === active)?.status : undefined;
  const rs = computeResearchState(tasks, opts.now, active);

  const wfPath = researchPaths(repo).workflow;
  const wfMd = fs.existsSync(wfPath) ? fs.readFileSync(wfPath, "utf8") : "";
  const stateKey = activeStatus ?? "no_task";
  const wfBlock = extractWorkflowState(wfMd, stateKey) ?? "Refer to workflow.md for current step.";

  const text =
    `[workflow-state:${stateKey}]\n${wfBlock}\n[/workflow-state]\n\n${renderResearchState(rs)}`;

  if (opts.format === "json") {
    return JSON.stringify({
      hookSpecificOutput: { hookEventName: opts.eventName ?? "UserPromptSubmit", additionalContext: text },
    });
  }
  return text;
}
