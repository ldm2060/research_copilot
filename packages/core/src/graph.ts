import type { TaskRecord } from "./types.js";

export interface GraphNode {
  task: TaskRecord;
  blocked: boolean;
  dependents: string[]; // ids that depend_on this task
}
export type Graph = Map<string, GraphNode>;

export function buildGraph(tasks: TaskRecord[]): Graph {
  const byId = new Map(tasks.map(t => [t.id, t]));
  const g: Graph = new Map();
  for (const t of tasks) {
    const blocked = t.depends_on.some(d => byId.get(d)?.status !== "completed");
    g.set(t.id, { task: t, blocked, dependents: [] });
  }
  for (const t of tasks) {
    for (const d of t.depends_on) {
      g.get(d)?.dependents.push(t.id);
    }
  }
  return g;
}
