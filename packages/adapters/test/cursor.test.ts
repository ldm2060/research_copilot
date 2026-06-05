import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureCursor } from "../src/configurators/cursor.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("cursor configurator (class-2 breadcrumb)", () => {
  it("renders 10 agents to .cursor/agents/*.md", () => {
    configureCursor(repo);
    expect(fs.readdirSync(path.join(repo, ".cursor/agents")).filter(f=>f.endsWith(".md")).length).toBe(10);
  });
  it("writes an always-apply rule with the breadcrumb protocol", () => {
    configureCursor(repo);
    const mdc = fs.readFileSync(path.join(repo, ".cursor/rules/research-copilot.mdc"), "utf8");
    expect(mdc).toContain("alwaysApply: true");
    expect(mdc).toContain("rc context");          // self-fetch each turn
    expect(mdc).toContain("Active task:");          // breadcrumb echo
  });
  it("is idempotent (re-run: 10 agents, 1 rule)", () => {
    configureCursor(repo); configureCursor(repo);
    expect(fs.readdirSync(path.join(repo, ".cursor/agents")).filter(f=>f.endsWith(".md")).length).toBe(10);
    expect(fs.existsSync(path.join(repo, ".cursor/rules/research-copilot.mdc"))).toBe(true);
  });
});
