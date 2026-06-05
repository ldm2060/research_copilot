import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { createTask, readTask, writeTask, listTasks } from "../src/task-store.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("task-store", () => {
  it("creates a task with id=date-slug and defaults, persists task.json", () => {
    const t = createTask(repo, { title: "Draft Method", kind: "writing", date: "2026-06-05" });
    expect(t.id).toBe("2026-06-05-draft-method");
    expect(t.status).toBe("planning");
    expect(t.priority).toBe("P2");
    expect(t.children).toEqual([]);
    expect(t.gaps).toEqual([]);
    const onDisk = readTask(repo, t.id);
    expect(onDisk.title).toBe("Draft Method");
  });

  it("lists all tasks", () => {
    createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    createTask(repo, { title: "B", kind: "experiment", date: "2026-06-05" });
    const ids = listTasks(repo).map(t => t.id).sort();
    expect(ids).toEqual(["2026-06-05-a", "2026-06-05-b"]);
  });

  it("writeTask updates the updated timestamp", () => {
    const t = createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    const before = t.updated;
    t.title = "A2";
    writeTask(repo, t, "2026-06-06T00:00:00Z");
    expect(readTask(repo, t.id).title).toBe("A2");
    expect(readTask(repo, t.id).updated).toBe("2026-06-06T00:00:00Z");
    expect(readTask(repo, t.id).updated).not.toBe(before);
  });
});
