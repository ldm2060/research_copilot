import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { createTask, setStatus } from "../src/task-store.js";
import { setActive, getActive } from "../src/active.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("active pointer + setStatus", () => {
  it("set/get the active task id", () => {
    const t = createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    setActive(repo, t.id);
    expect(getActive(repo)).toBe(t.id);
  });
  it("setStatus enforces the FSM", () => {
    const t = createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    setStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    expect(() => setStatus(repo, t.id, "completed", "2026-06-05T02:00:00Z"))
      .toThrow(/illegal transition/i);
  });
});
