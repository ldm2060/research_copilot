import type { TaskRecord, Kind, Status } from "./types.js";
import { buildGraph } from "./graph.js";

export interface Recommendation {
  action: "resume" | "create";
  taskId?: string;
  suggestKind?: Kind;
  reason: string;
  sourceGap?: string;
  score: number;
}
export interface ResearchState {
  active: { id: string; kind: Kind; status: Status } | null;
  graph: { completed: number; in_progress: number; blocked: number; planning: number };
  openGaps: { taskId: string; desc: string; suggest_kind: Kind }[];
  recommendations: Recommendation[];
  turnTs: string;
}

const PRIORITY_RANK = { P0: 3, P1: 2, P2: 1, P3: 0 } as const;
const LIFECYCLE_BONUS: Record<Status, number> = { in_progress: 2, verify: 1, planning: 0.5, completed: 0 };
const W = { priority: 3, unblocking: 2, lifecycle: 1, age: 0.001 } as const;
const MAX_RECS = 3;

export function computeResearchState(
  tasks: TaskRecord[], now: string, activeId?: string,
): ResearchState {
  const g = buildGraph(tasks);
  const counts = { completed: 0, in_progress: 0, blocked: 0, planning: 0 };
  for (const n of g.values()) {
    if (n.blocked) counts.blocked++;
    if (n.task.status === "completed") counts.completed++;
    else if (n.task.status === "in_progress") counts.in_progress++;
    else if (n.task.status === "planning") counts.planning++;
  }

  const openGaps = tasks.flatMap(t =>
    t.gaps.filter(gp => gp.status === "open")
      .map(gp => ({ taskId: t.id, desc: gp.desc, suggest_kind: gp.suggest_kind })));

  const ageDays = (iso: string) =>
    Math.max(0, (Date.parse(now) - Date.parse(iso)) / 86_400_000);

  const recs: Recommendation[] = [];

  // (a) resume candidates: not completed, not blocked
  for (const n of g.values()) {
    if (n.task.status === "completed" || n.blocked) continue;
    const score =
      W.priority * PRIORITY_RANK[n.task.priority] +
      W.lifecycle * LIFECYCLE_BONUS[n.task.status] +
      W.age * ageDays(n.task.updated);
    recs.push({ action: "resume", taskId: n.task.id, score,
      reason: `resume ${n.task.kind} task ${n.task.id} (${n.task.status})` });
  }

  // (b) create candidates from open gaps; unblocking potential = #dependents of the gap's source task
  for (const t of tasks) {
    const dependents = g.get(t.id)?.dependents.length ?? 0;
    for (const gp of t.gaps.filter(x => x.status === "open")) {
      const score =
        W.priority * PRIORITY_RANK[t.priority] +
        W.unblocking * dependents +
        W.lifecycle * LIFECYCLE_BONUS[t.status];
      recs.push({ action: "create", suggestKind: gp.suggest_kind, sourceGap: gp.desc, score,
        reason: `create ${gp.suggest_kind} task to resolve "${gp.desc}" (from ${t.id})` });
    }
  }

  recs.sort((x, y) =>
    y.score - x.score ||
    (x.taskId ?? x.sourceGap ?? "").localeCompare(y.taskId ?? y.sourceGap ?? ""));

  const active = activeId
    ? (() => { const n = g.get(activeId); return n ? { id: n.task.id, kind: n.task.kind, status: n.task.status } : null; })()
    : null;

  return { active, graph: counts, openGaps, recommendations: recs.slice(0, MAX_RECS), turnTs: now };
}
