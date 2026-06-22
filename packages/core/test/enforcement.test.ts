import { describe, it, expect } from "vitest";
import {
  expectedExecutorFor,
  canExecutorClaim,
  classifyArtifact,
  canWriteArtifact,
  RESEARCH_EXECUTORS,
  type ResearchExecutor,
} from "../src/enforcement.js";
import type { TaskRecord } from "../src/types.js";

const task = (over: Partial<TaskRecord>): TaskRecord => ({
  id: "2026-06-22-node",
  title: "node",
  kind: "writing",
  status: "planning",
  priority: "P2",
  children: [],
  depends_on: [],
  gaps: [],
  created: "2026-06-22T00:00:00Z",
  updated: "2026-06-22T00:00:00Z",
  ...over,
});

describe("Trellis executor mapping", () => {
  it("maps lifecycle states to the legal executor", () => {
    expect(expectedExecutorFor(task({ status: "planning", kind: "literature" }))).toBe("rc-plan");
    expect(expectedExecutorFor(task({ status: "verify", kind: "experiment" }))).toBe("rc-verify");
    expect(expectedExecutorFor(task({ status: "completed", kind: "review" }))).toBe("rc-update-spec");
  });

  it("maps every in-progress kind to its leaf executor", () => {
    const cases: Array<[TaskRecord["kind"], ResearchExecutor]> = [
      ["literature", "rc-literature"],
      ["ideation", "rc-ideation"],
      ["experiment", "rc-experiment"],
      ["writing", "rc-writer"],
      ["polish", "rc-polisher"],
      ["review", "rc-reviewer"],
      ["rebuttal", "rc-rebuttal"],
    ];
    for (const [kind, executor] of cases) {
      expect(expectedExecutorFor(task({ status: "in_progress", kind }))).toBe(executor);
      expect(canExecutorClaim(task({ status: "in_progress", kind }), executor)).toBe(true);
      expect(canExecutorClaim(task({ status: "in_progress", kind }), "rc-plan")).toBe(false);
    }
  });
});

describe("Trellis artifact ownership", () => {
  it("classifies canonical .research task paths", () => {
    expect(classifyArtifact(".research/tasks/t1/task.json")).toMatchObject({ owner: "conductor" });
    expect(classifyArtifact(".research/tasks/t1/prd.md")).toMatchObject({ owner: "rc-plan" });
    expect(classifyArtifact(".research/tasks/t1/execute.jsonl")).toMatchObject({ owner: "rc-plan" });
    expect(classifyArtifact(".research/tasks/t1/verify.jsonl")).toMatchObject({ owner: "rc-plan" });
    expect(classifyArtifact(".research/tasks/t1/verify/report.md")).toMatchObject({ owner: "rc-verify" });
    expect(classifyArtifact(".research/spec/baselines/foo.md")).toMatchObject({ owner: "rc-update-spec" });
    expect(classifyArtifact("src/index.ts")).toMatchObject({ owner: "non-research" });
  });

  it("classifies compatibility research paths", () => {
    expect(classifyArtifact(".copilot/literature.md").allowedExecutors).toEqual(["rc-literature"]);
    expect(classifyArtifact(".copilot/ideas.md").allowedExecutors).toEqual(["rc-ideation"]);
    expect(classifyArtifact(".copilot/experiments.md").allowedExecutors).toEqual(["rc-experiment"]);
    expect(classifyArtifact(".copilot/reviews/round-1.md").allowedExecutors).toEqual(["rc-reviewer"]);
    expect(classifyArtifact("sections/method.tex").allowedExecutors).toEqual(["rc-writer", "rc-polisher", "rc-rebuttal"]);
    expect(classifyArtifact("references.bib").allowedExecutors).toEqual(["rc-literature", "rc-writer"]);
  });

  it("allows conductor metadata and repository development writes", () => {
    expect(canWriteArtifact("conductor", task({ status: "planning" }), ".research/tasks/t1/task.json")).toBe(true);
    expect(canWriteArtifact("conductor", task({ status: "planning" }), "packages/core/src/index.ts")).toBe(true);
    expect(canWriteArtifact("conductor", task({ status: "planning" }), ".research/tasks/t1/prd.md")).toBe(false);
    expect(canWriteArtifact("conductor", task({ status: "completed" }), ".research/spec/baselines/foo.md")).toBe(false);
  });

  it("allows only the active node legal executor to write owned artifacts", () => {
    expect(canWriteArtifact("rc-plan", task({ status: "planning", kind: "literature" }), ".research/tasks/t1/prd.md")).toBe(true);
    expect(canWriteArtifact("rc-literature", task({ status: "planning", kind: "literature" }), ".research/tasks/t1/prd.md")).toBe(false);
    expect(canWriteArtifact("rc-literature", task({ status: "in_progress", kind: "literature" }), ".copilot/literature.md")).toBe(true);
    expect(canWriteArtifact("rc-writer", task({ status: "in_progress", kind: "literature" }), ".copilot/literature.md")).toBe(false);
    expect(canWriteArtifact("rc-update-spec", task({ status: "completed", kind: "review" }), ".research/spec/reviews/gaps.md")).toBe(true);
  });
});

describe("Trellis enforcement readonly ownership", () => {
  it("RESEARCH_EXECUTORS is a frozen-length readonly tuple", () => {
    // The `as const` assertion makes this a readonly tuple at the type level.
    // At runtime, verify the array contents are the 10 expected executors.
    expect(RESEARCH_EXECUTORS).toHaveLength(10);
    expect(RESEARCH_EXECUTORS[0]).toBe("rc-plan");
    // Type-level: assigning to RESEARCH_EXECUTORS[0] would fail at compile time.
    // Runtime: verify Object.isFrozen is not guaranteed (as const is type-only),
    // but the readonly constraint is enforced by the type system.
  });

  it("classifyArtifact returns readonly allowedExecutors", () => {
    const claim = classifyArtifact(".research/tasks/t1/prd.md");
    // The returned allowedExecutors should match exactly and not be mutable via the type.
    expect(claim.allowedExecutors).toEqual(["rc-plan"]);
    // Type-level: claim.allowedExecutors.push("rc-literature") would fail at compile time
    // because ArtifactClaim.allowedExecutors is `readonly ResearchExecutor[]`.
  });
});
