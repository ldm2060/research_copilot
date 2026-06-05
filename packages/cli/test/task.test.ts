import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";
import { taskCreate, taskSetStatus, taskAddGap, taskCurrent } from "../src/commands/task.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); runInit({ repo, platforms: ["claude-code"], user: "t" }); });

describe("rc task lifecycle", () => {
  it("create -> start -> verify -> complete walks the FSM and tracks active", () => {
    const t = taskCreate(repo, { title: "Method", kind: "writing", date: "2026-06-05" });
    expect(taskCurrent(repo)).toBe(t.id);
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    taskSetStatus(repo, t.id, "verify", "2026-06-05T02:00:00Z");
    taskSetStatus(repo, t.id, "completed", "2026-06-05T03:00:00Z");
    expect(() => taskSetStatus(repo, t.id, "in_progress", "2026-06-05T04:00:00Z")).toThrow();
  });
  it("add-gap records an open gap with suggest_kind", () => {
    const t = taskCreate(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    taskAddGap(repo, t.id, "missing ablation", "experiment");
    const stored = JSON.parse(fs.readFileSync(path.join(repo, ".research/tasks", t.id, "task.json"), "utf8"));
    expect(stored.gaps[0]).toMatchObject({ desc: "missing ablation", suggest_kind: "experiment", status: "open" });
  });
});
