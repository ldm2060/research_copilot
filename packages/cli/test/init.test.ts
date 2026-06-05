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
});
