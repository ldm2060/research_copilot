import { describe, it, expect } from "vitest";
import { buildGraph } from "../src/graph.js";
import type { TaskRecord } from "../src/types.js";

const mk = (over: Partial<TaskRecord>): TaskRecord => ({
  id: "x", title: "x", kind: "writing", status: "planning", priority: "P2",
  children: [], depends_on: [], gaps: [], created: "", updated: "", ...over,
});

describe("buildGraph", () => {
  it("marks a task blocked when a dependency is not completed", () => {
    const tasks = [
      mk({ id: "a", status: "in_progress" }),
      mk({ id: "b", depends_on: ["a"] }),
    ];
    const g = buildGraph(tasks);
    expect(g.get("b")!.blocked).toBe(true);
    expect(g.get("a")!.blocked).toBe(false);
  });
  it("unblocks when the dependency is completed", () => {
    const tasks = [
      mk({ id: "a", status: "completed" }),
      mk({ id: "b", depends_on: ["a"] }),
    ];
    expect(buildGraph(tasks).get("b")!.blocked).toBe(false);
  });
  it("counts downstream dependents (unblocking potential)", () => {
    const tasks = [
      mk({ id: "a" }), mk({ id: "b", depends_on: ["a"] }), mk({ id: "c", depends_on: ["a"] }),
    ];
    expect(buildGraph(tasks).get("a")!.dependents).toEqual(["b", "c"]);
  });
});
