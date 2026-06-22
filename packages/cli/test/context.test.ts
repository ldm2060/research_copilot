import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runContext, enforcementForPlatform } from "../src/commands/context.js";

let repo: string;
beforeEach(() => {
  repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-"));
  fs.mkdirSync(path.join(repo, ".research"), { recursive: true });
  fs.writeFileSync(path.join(repo, ".research/workflow.md"),
    "[workflow-state:no_task]\nNo active task.\n[/workflow-state]\n");
});

describe("rc context", () => {
  it("returns the no_task block + research-state when nothing is active", () => {
    const out = runContext({ repo, format: "text", now: "2026-06-05T00:00:00Z" });
    expect(out).toContain("[workflow-state:no_task]");
    expect(out).toContain("[research-state]");
  });

  it("includes hard enforcement for claude-code by default", () => {
    const out = runContext({ repo, format: "text", now: "2026-06-05T00:00:00Z" });
    expect(out).toContain("[trellis-enforcement]");
    expect(out).toContain("Platform: claude-code");
    expect(out).toContain("Mode: hard");
  });

  it("includes soft enforcement for class-2 platforms", () => {
    const out = runContext({ repo, platform: "windsurf", format: "text", now: "2026-06-05T00:00:00Z" });
    expect(out).toContain("Platform: windsurf");
    expect(out).toContain("Mode: soft");
    expect(out).toContain("Strict sub-agent-only execution cannot be guaranteed on this platform.");
  });

  it("falls back to unavailable mode for unknown platforms", () => {
    const out = runContext({ repo, platform: "acme-ide", format: "text", now: "2026-06-05T00:00:00Z" });
    expect(out).toContain("[trellis-enforcement]");
    expect(out).toContain("Platform: acme-ide");
    expect(out).toContain("Mode: unavailable");
    expect(out).toContain('unknown platform "acme-ide"');
    expect(out).toContain("Strict sub-agent-only execution cannot be guaranteed on this platform.");
  });
});

describe("enforcementForPlatform", () => {
  it("returns hard enforcement for claude-code by default (no argument)", () => {
    const result = enforcementForPlatform();
    expect(result.platform).toBe("claude-code");
    expect(result.mode).toBe("hard");
    expect(result.reason).toContain("hooks and executable sub-agents");
  });
  it("returns the enforcement for a known platform", () => {
    const result = enforcementForPlatform("cursor");
    expect(result.platform).toBe("cursor");
    expect(result.mode).toBe("soft");
    expect(result.reason).toContain("advisory");
  });
  it("falls back to unavailable mode for an unknown platform", () => {
    const result = enforcementForPlatform("acme-ide");
    expect(result.platform).toBe("acme-ide");
    expect(result.mode).toBe("unavailable");
    expect(result.reason).toContain('unknown platform "acme-ide"');
  });
});
