import type { Status } from "./types.js";

export function extractWorkflowState(md: string, state: Status | "no_task"): string | null {
  const re = new RegExp(
    `\\[workflow-state:${state}\\]\\r?\\n([\\s\\S]*?)\\r?\\n\\[/workflow-state\\]`,
  );
  const m = md.match(re);
  return m ? m[1].trim() : null;
}
