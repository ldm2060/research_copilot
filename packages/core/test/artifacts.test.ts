import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { createTask } from "../src/task-store.js";
import { readPrdGoal, appendContext, readContext } from "../src/artifacts.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("artifacts IO", () => {
  it("reads prd.goal as the first paragraph under ## Goal", () => {
    const t = createTask(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    const dir = path.join(repo, ".research/tasks", t.id);
    fs.writeFileSync(path.join(dir, "prd.md"),
      "# M\n\n## Goal\nWrite the method.\n\n## Scope\n...");
    expect(readPrdGoal(repo, t.id)).toBe("Write the method.");
  });
  it("appends and reads execute.jsonl context refs", () => {
    const t = createTask(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    appendContext(repo, t.id, "execute", { type: "spec", path: "spec/writing/style.md", reason: "tone" });
    const rows = readContext(repo, t.id, "execute");
    expect(rows).toEqual([{ type: "spec", path: "spec/writing/style.md", reason: "tone" }]);
  });
});
