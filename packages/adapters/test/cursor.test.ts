import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureCursor } from "../src/configurators/cursor.js";
import { AI_TOOLS } from "../src/registry.js";

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
  it("registers both MCP servers in .cursor/mcp.json", () => {
    configureCursor(repo);
    const mcp = JSON.parse(fs.readFileSync(path.join(repo, ".cursor/mcp.json"), "utf8"));
    expect(mcp.mcpServers["research-scholar"].command).toBe("npx");
    expect(mcp.mcpServers["research-scholar"].args).toContain("@research-copilot/mcp-scholar");
    expect(mcp.mcpServers["research-pdf"].args).toContain("@research-copilot/mcp-pdf");
  });
  it("MCP write is merge-safe + idempotent (foreign server preserved; no dup args on re-run)", () => {
    fs.mkdirSync(path.join(repo, ".cursor"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".cursor/mcp.json"),
      JSON.stringify({ mcpServers: { other: { command: "node", args: ["x.js"] } } }));
    configureCursor(repo); configureCursor(repo);
    const mcp = JSON.parse(fs.readFileSync(path.join(repo, ".cursor/mcp.json"), "utf8"));
    expect(mcp.mcpServers.other).toBeDefined();
    expect(mcp.mcpServers["research-scholar"].args).toEqual(["-y", "@research-copilot/mcp-scholar"]);
  });
  it("declares soft Trellis enforcement because hooks are unavailable", () => {
    expect(AI_TOOLS.cursor.enforcement).toEqual({
      platform: "cursor",
      mode: "soft",
      reason: "platform lacks hook-based hard deny; breadcrumb rules and agents are advisory",
    });
  });
});
