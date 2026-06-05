import { describe, it, expect } from "vitest";
import * as path from "node:path";
import { researchPaths } from "../src/paths.js";

const n = (s: string) => s.replaceAll(path.sep, "/");

describe("researchPaths", () => {
  it("derives all .research subpaths from a root", () => {
    const p = researchPaths("/repo");
    expect(n(p.root)).toBe(n("/repo/.research"));
    expect(n(p.tasks)).toBe(n("/repo/.research/tasks"));
    expect(n(p.spec)).toBe(n("/repo/.research/spec"));
    expect(n(p.workspace)).toBe(n("/repo/.research/workspace"));
    expect(n(p.runtime)).toBe(n("/repo/.research/.runtime"));
    expect(n(p.workflow)).toBe(n("/repo/.research/workflow.md"));
    expect(n(p.config)).toBe(n("/repo/.research/config.yaml"));
    expect(n(p.activeTask)).toBe(n("/repo/.research/.runtime/active-task"));
    expect(n(p.graphIndex)).toBe(n("/repo/.research/.runtime/graph-index.json"));
    expect(n(p.taskDir("2026-06-05-x"))).toBe(n("/repo/.research/tasks/2026-06-05-x"));
  });
});
