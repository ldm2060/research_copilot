import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";
import { taskCreate, taskSetStatus } from "../src/commands/task.js";
import { runContext } from "../src/commands/context.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("e2e research loop on Claude Code", () => {
  it("init -> create -> start -> context shows in_progress + recommendation", () => {
    runInit({ repo, platforms: ["claude-code"], user: "t", skipPlugin: true });
    const t = taskCreate(repo, { title: "Main exp", kind: "experiment", date: "2026-06-05" });
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    const ctx = runContext({ repo, format: "text", now: "2026-06-05T02:00:00Z" });
    expect(ctx).toContain("[workflow-state:in_progress]");
    expect(ctx).toContain("[research-state]");
    expect(ctx).toContain(t.id);
  });
});
