import { describe, it, expect } from "vitest";
import { computeResearchState } from "../src/research-state.js";
import type { TaskRecord } from "../src/types.js";

const mk = (over: Partial<TaskRecord>): TaskRecord => ({
  id: "x", title: "x", kind: "writing", status: "planning", priority: "P2",
  children: [], depends_on: [], gaps: [], created: "2026-06-01T00:00:00Z",
  updated: "2026-06-01T00:00:00Z", ...over,
});
const NOW = "2026-06-05T00:00:00Z";

describe("computeResearchState (§16.1)", () => {
  it("recommends creating a task for an open gap, tagged with suggest_kind", () => {
    const tasks = [mk({
      id: "2026-06-05-method", kind: "writing", status: "in_progress",
      gaps: [{ desc: "missing ablation X", suggest_kind: "experiment", status: "open" }],
    })];
    const rs = computeResearchState(tasks, NOW);
    const create = rs.recommendations.find(r => r.action === "create");
    expect(create?.suggestKind).toBe("experiment");
    expect(create?.sourceGap).toBe("missing ablation X");
    expect(rs.turnTs).toBe(NOW);
  });

  it("ranks higher-priority resume candidates first", () => {
    const tasks = [
      mk({ id: "low", status: "in_progress", priority: "P3" }),
      mk({ id: "high", status: "in_progress", priority: "P0" }),
    ];
    const rs = computeResearchState(tasks, NOW);
    const resumes = rs.recommendations.filter(r => r.action === "resume").map(r => r.taskId);
    expect(resumes[0]).toBe("high");
  });

  it("does not recommend resuming a blocked task", () => {
    const tasks = [
      mk({ id: "dep", status: "in_progress" }),
      mk({ id: "blocked", status: "in_progress", depends_on: ["dep"] }),
    ];
    const rs = computeResearchState(tasks, NOW);
    expect(rs.recommendations.find(r => r.taskId === "blocked")).toBeUndefined();
    expect(rs.graph.blocked).toBe(1);
  });

  it("gaps that unblock more downstream tasks score higher (tie-break by unblocking potential)", () => {
    const tasks = [
      mk({ id: "g1src", priority: "P2", status: "in_progress",
        gaps: [{ desc: "g1", suggest_kind: "experiment", status: "open" }] }),
      mk({ id: "g2src", priority: "P2", status: "in_progress",
        gaps: [{ desc: "g2", suggest_kind: "experiment", status: "open" }] }),
      mk({ id: "d1", depends_on: ["g2src"] }),
      mk({ id: "d2", depends_on: ["g2src"] }),
    ];
    const rs = computeResearchState(tasks, NOW);
    const creates = rs.recommendations.filter(r => r.action === "create");
    expect(creates[0].sourceGap).toBe("g2");
  });

  it("handles the empty / all-completed case", () => {
    const rs = computeResearchState([mk({ id: "done", status: "completed" })], NOW);
    expect(rs.recommendations).toEqual([]);
    expect(rs.graph.completed).toBe(1);
  });

  it("emits at most 3 recommendations", () => {
    const tasks = Array.from({ length: 6 }, (_, i) =>
      mk({ id: `t${i}`, status: "in_progress", priority: "P1" }));
    expect(computeResearchState(tasks, NOW).recommendations.length).toBeLessThanOrEqual(3);
  });

  it("ranks create vs resume on one score scale (create can outrank a resume)", () => {
    const tasks = [
      mk({ id: "hi", status: "in_progress", priority: "P0",
        gaps: [{ desc: "g", suggest_kind: "experiment", status: "open" }] }),
      mk({ id: "dep", depends_on: ["hi"] }),        // blocked → not a resume candidate
      mk({ id: "lo", status: "in_progress", priority: "P3" }),
    ];
    const rs = computeResearchState(tasks, NOW);
    // create from hi's gap: 3*3 + 2*1(dep) + 1*2 = 13  (hi has 1 dependent: dep)
    // resume hi: 3*3 + 1*2 ≈ 11 ; resume lo: 3*0 + 1*2 = 2
    expect(rs.recommendations[0]).toMatchObject({ action: "create", sourceGap: "g" });
    expect(rs.recommendations[1]).toMatchObject({ action: "resume", taskId: "hi" });
    expect(rs.recommendations[2]).toMatchObject({ action: "resume", taskId: "lo" });
  });

  it("breaks equal-score ties alphabetically by id", () => {
    const tasks = [
      mk({ id: "zebra", status: "in_progress", priority: "P1" }),
      mk({ id: "alpha", status: "in_progress", priority: "P1" }),
    ];
    // identical score → tie-break by localeCompare on taskId → alpha before zebra
    const resumes = computeResearchState(tasks, NOW).recommendations
      .filter(r => r.action === "resume").map(r => r.taskId);
    expect(resumes).toEqual(["alpha", "zebra"]);
  });
});
