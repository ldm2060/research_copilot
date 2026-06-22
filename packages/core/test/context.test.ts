import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { createTask, setStatus } from "../src/task-store.js";
import { setActive } from "../src/active.js";
import { buildContext } from "../src/context.js";

let repo: string;
beforeEach(() => {
  repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-"));
  fs.mkdirSync(path.join(repo, ".research"), { recursive: true });
  fs.writeFileSync(path.join(repo, ".research", "workflow.md"),
    "[workflow-state:in_progress]\nDispatch rc-{kind}.\n[/workflow-state]\n");
});

describe("buildContext (§16.6)", () => {
  it("text format embeds both blocks and turn-ts", () => {
    const t = createTask(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    setStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    setActive(repo, t.id);
    const out = buildContext(repo, { format: "text", now: "2026-06-05T02:00:00Z" });
    expect(out).toContain("[workflow-state:in_progress]");
    expect(out).toContain("Dispatch rc-{kind}.");
    expect(out).toContain("[research-state]");
    expect(out).toContain("turn-ts: 2026-06-05T02:00:00Z");
  });
  it("json format returns hookSpecificOutput.additionalContext", () => {
    const out = buildContext(repo, { format: "json", now: "2026-06-05T02:00:00Z" });
    const parsed = JSON.parse(out);
    expect(parsed.hookSpecificOutput.additionalContext).toContain("[research-state]");
  });
  it("json format honors a custom eventName", () => {
    const out = buildContext(repo, { format: "json", now: "2026-06-05T02:00:00Z", eventName: "BeforeAgent" });
    expect(JSON.parse(out).hookSpecificOutput.hookEventName).toBe("BeforeAgent");
  });
  it("renders a Trellis enforcement block when enforcement summary is supplied", () => {
    const out = buildContext(repo, {
      format: "text",
      now: "2026-06-05T02:00:00Z",
      enforcement: {
        platform: "claude-code",
        mode: "hard",
        reason: "supports hooks and executable sub-agents",
      },
    });
    expect(out).toContain("[trellis-enforcement]");
    expect(out).toContain("Mode: hard");
    expect(out).toContain("Platform: claude-code");
    expect(out).toContain("Reason: supports hooks and executable sub-agents");
  });
});
