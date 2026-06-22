import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureWindsurf } from "../src/configurators/windsurf.js";
import { AI_TOOLS } from "../src/registry.js";

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
  it("does NOT write a repo-local MCP file (Windsurf MCP is user-global only)", () => {
    configureWindsurf(repo);
    expect(fs.existsSync(path.join(repo, ".windsurf/mcp.json"))).toBe(false);
    expect(fs.existsSync(path.join(repo, ".windsurf/mcp_config.json"))).toBe(false);
    expect(fs.existsSync(path.join(repo, ".mcp.json"))).toBe(false);
  });
  it("documents the two MCP servers + global mcp_config.json path in a note", () => {
    configureWindsurf(repo);
    const rule = fs.readFileSync(path.join(repo, ".windsurf/rules/research-copilot.md"), "utf8");
    expect(rule).toContain("mcp_config.json");      // global config path
    expect(rule).toContain("research-scholar");
    expect(rule).toContain("research-pdf");
    expect(rule).toContain("@research-copilot/mcp-scholar");
  });
  it("MCP note is idempotent (single note on re-run)", () => {
    configureWindsurf(repo); configureWindsurf(repo);
    const rule = fs.readFileSync(path.join(repo, ".windsurf/rules/research-copilot.md"), "utf8");
    expect(rule.split("mcp_config.json").length - 1).toBeGreaterThanOrEqual(1);
    // the heading anchoring the note must appear exactly once
    expect(rule.split("## MCP servers").length - 1).toBe(1);
  });
  it("declares soft Trellis enforcement because hooks and executable agents are unavailable", () => {
    expect(AI_TOOLS.windsurf.enforcement).toEqual({
      platform: "windsurf",
      mode: "soft",
      reason: "platform lacks hook-based hard deny and executable sub-agents; workflows are advisory",
    });
  });
});
