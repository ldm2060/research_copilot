import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("rc init", () => {
  it("scaffolds .research/ and Claude Code config", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester" });
    expect(fs.existsSync(path.join(repo, ".research/workflow.md"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".research/config.yaml"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".research/spec/venue"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".claude/settings.json"))).toBe(true);
    expect(fs.readdirSync(path.join(repo, ".claude/agents")).length).toBe(10);
  });

  it("scaffolds multiple selected platforms", () => {
    runInit({ repo, platforms: ["codex", "gemini"], user: "tester" });
    expect(fs.existsSync(path.join(repo, ".research/workflow.md"))).toBe(true);
    expect(fs.readdirSync(path.join(repo, ".codex/agents")).filter(f=>f.endsWith(".toml")).length).toBe(10);
    expect(fs.readdirSync(path.join(repo, ".gemini/agents")).filter(f=>f.endsWith(".md")).length).toBe(10);
    expect(fs.existsSync(path.join(repo, ".claude"))).toBe(false); // not selected
  });
});
