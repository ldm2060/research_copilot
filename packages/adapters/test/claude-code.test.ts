import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureClaudeCode } from "../src/configurators/claude-code.js";
import { AI_TOOLS } from "../src/registry.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("claude-code configurator", () => {
  it("writes a UserPromptSubmit hook that calls rc context", () => {
    configureClaudeCode(repo);
    const settings = JSON.parse(fs.readFileSync(path.join(repo, ".claude/settings.json"), "utf8"));
    const cmd = settings.hooks.UserPromptSubmit[0].hooks[0].command;
    expect(cmd).toContain("rc context");
    expect(cmd).toContain("--format text");
  });
  it("renders the 10 agents into .claude/agents", () => {
    configureClaudeCode(repo);
    const agents = fs.readdirSync(path.join(repo, ".claude/agents")).filter(f => f.endsWith(".md"));
    expect(agents.length).toBe(10);
  });
  it("merges into an existing settings.json without clobbering foreign keys", () => {
    fs.mkdirSync(path.join(repo, ".claude"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".claude/settings.json"),
      JSON.stringify({ model: "opus", hooks: { SessionStart: [{ matcher: "*", hooks: [] }] } }));
    configureClaudeCode(repo);
    const s = JSON.parse(fs.readFileSync(path.join(repo, ".claude/settings.json"), "utf8"));
    expect(s.model).toBe("opus");                 // foreign key preserved
    expect(s.hooks.SessionStart).toBeDefined();   // foreign hook preserved
    expect(s.hooks.UserPromptSubmit).toBeDefined(); // ours added
  });
  it("is idempotent — re-running does not stack duplicate hooks or notes", () => {
    configureClaudeCode(repo);
    configureClaudeCode(repo);
    const s = JSON.parse(fs.readFileSync(path.join(repo, ".claude/settings.json"), "utf8"));
    const rcHooks = (s.hooks.UserPromptSubmit as any[])
      .flatMap(g => g.hooks)
      .filter((h: any) => typeof h.command === "string" && h.command.includes("rc context"));
    expect(rcHooks.length).toBe(1);
    const md = fs.readFileSync(path.join(repo, "CLAUDE.md"), "utf8");
    expect(md.split("Research workflow is governed by").length - 1).toBe(1);
  });
  it("writes both research MCP servers into .mcp.json", () => {
    configureClaudeCode(repo);
    const mcp = JSON.parse(fs.readFileSync(path.join(repo, ".mcp.json"), "utf8"));
    expect(mcp.mcpServers["research-scholar"].args).toContain("@research-copilot/mcp-scholar");
    expect(mcp.mcpServers["research-pdf"].args).toContain("@research-copilot/mcp-pdf");
    expect(mcp.mcpServers["research-scholar"].command).toBe("npx");
  });
  it("merges MCP servers into an existing .mcp.json without clobbering foreign servers", () => {
    fs.writeFileSync(path.join(repo, ".mcp.json"),
      JSON.stringify({ mcpServers: { "other-tool": { command: "node", args: ["x.js"] } } }));
    configureClaudeCode(repo);
    const mcp = JSON.parse(fs.readFileSync(path.join(repo, ".mcp.json"), "utf8"));
    expect(mcp.mcpServers["other-tool"]).toBeDefined();        // foreign preserved
    expect(mcp.mcpServers["research-scholar"]).toBeDefined();   // ours added
    expect(mcp.mcpServers["research-pdf"]).toBeDefined();
  });
  it("MCP write is idempotent (re-run: single entry per server)", () => {
    configureClaudeCode(repo);
    configureClaudeCode(repo);
    const mcp = JSON.parse(fs.readFileSync(path.join(repo, ".mcp.json"), "utf8"));
    expect(Object.keys(mcp.mcpServers).filter(k => k === "research-scholar").length).toBe(1);
    expect(mcp.mcpServers["research-scholar"].args).toEqual(["-y", "@research-copilot/mcp-scholar"]);
  });
  it("declares hard Trellis enforcement capability", () => {
    expect(AI_TOOLS["claude-code"].enforcement).toEqual({
      platform: "claude-code",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    });
  });
});
