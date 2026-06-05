import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureWindsurf } from "../src/configurators/windsurf.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("windsurf configurator (class-2, agent-less)", () => {
  it("renders the 10 executors as workflows (NOT subagents)", () => {
    configureWindsurf(repo);
    const wf = path.join(repo, ".windsurf/workflows");
    expect(fs.readdirSync(wf).filter(f=>f.endsWith(".md")).length).toBe(10);
    expect(fs.existsSync(path.join(repo, ".windsurf/agents"))).toBe(false); // agent-less
    const writer = fs.readFileSync(path.join(wf, "rc-writer.md"), "utf8");
    expect(writer.length).toBeGreaterThan(20); // has the executor's instructions
  });
  it("writes an always-on rule with the breadcrumb + agent-less inline-execution protocol", () => {
    configureWindsurf(repo);
    const rule = fs.readFileSync(path.join(repo, ".windsurf/rules/research-copilot.md"), "utf8");
    expect(rule).toContain("trigger: always_on");
    expect(rule).toContain("rc context");
    expect(rule).toContain("Active task:");
    expect(rule.toLowerCase()).toMatch(/workflow|inline/); // tells agent to use workflows inline (no subagents)
  });
  it("is idempotent (re-run: 10 workflows, 1 rule)", () => {
    configureWindsurf(repo); configureWindsurf(repo);
    expect(fs.readdirSync(path.join(repo, ".windsurf/workflows")).filter(f=>f.endsWith(".md")).length).toBe(10);
    expect(fs.existsSync(path.join(repo, ".windsurf/rules/research-copilot.md"))).toBe(true);
  });
});
