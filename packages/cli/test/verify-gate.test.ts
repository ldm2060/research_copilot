import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";
import { taskCreate, taskSetStatus, runVerifyGate } from "../src/commands/task.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); runInit({ repo, platforms: ["claude-code"], user: "t", skipPlugin: true }); });

function seed(id: string, draft: string, artifacts: string) {
  const dir = path.join(repo, ".research/tasks", id, "artifacts");
  fs.writeFileSync(path.join(dir, "draft.tex"), draft);
  fs.writeFileSync(path.join(dir, "run.log"), artifacts);
}

describe("verify gate (acceptance 3)", () => {
  it("fails and rolls back on a fabricated number", () => {
    const t = taskCreate(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    taskSetStatus(repo, t.id, "verify", "2026-06-05T02:00:00Z");
    seed(t.id, "We reach 99.9 acc.", "final_acc=92.5");
    const res = runVerifyGate(repo, t.id, "2026-06-05T03:00:00Z");
    expect(res.ok).toBe(false);
    expect(res.missing).toContain("99.9");
    expect(JSON.parse(fs.readFileSync(path.join(repo, ".research/tasks", t.id, "task.json"), "utf8")).status)
      .toBe("in_progress"); // rolled back
  });
  it("passes when numbers trace", () => {
    const t = taskCreate(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    taskSetStatus(repo, t.id, "verify", "2026-06-05T02:00:00Z");
    seed(t.id, "We reach 92.5 acc.", "final_acc=92.5");
    expect(runVerifyGate(repo, t.id, "2026-06-05T03:00:00Z").ok).toBe(true);
  });
});
