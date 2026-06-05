import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureGemini } from "../src/configurators/gemini.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("gemini configurator", () => {
  it("renders 10 agents to .gemini/agents/*.md with name+description", () => {
    configureGemini(repo);
    const dir = path.join(repo, ".gemini/agents");
    const mds = fs.readdirSync(dir).filter(f => f.endsWith(".md"));
    expect(mds.length).toBe(10);
    const w = fs.readFileSync(path.join(dir, "rc-writer.md"), "utf8");
    expect(w).toContain("name: rc-writer");
    expect(w).toContain("description:");
  });
  it("writes a BeforeAgent hook in settings.json calling rc context --format json --event BeforeAgent", () => {
    configureGemini(repo);
    const s = JSON.parse(fs.readFileSync(path.join(repo, ".gemini/settings.json"), "utf8"));
    const cmds = (s.hooks.BeforeAgent as any[]).flatMap(g => g.hooks ?? []).map((h:any)=>h.command);
    expect(cmds.some(c => /rc context/.test(c) && /--format json/.test(c) && /--event BeforeAgent/.test(c))).toBe(true);
  });
  it("merge-safe + idempotent (foreign settings preserved; single BeforeAgent rc hook on re-run)", () => {
    fs.mkdirSync(path.join(repo, ".gemini"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".gemini/settings.json"), JSON.stringify({ theme: "dark", hooks: { SessionStart: [{ matcher: "*", hooks: [] }] } }));
    configureGemini(repo); configureGemini(repo);
    const s = JSON.parse(fs.readFileSync(path.join(repo, ".gemini/settings.json"), "utf8"));
    expect(s.theme).toBe("dark");
    expect(s.hooks.SessionStart).toBeDefined();
    const rc = (s.hooks.BeforeAgent as any[]).flatMap(g => g.hooks ?? []).filter((h:any)=>/rc context/.test(h.command));
    expect(rc.length).toBe(1);
  });
  it("registers both MCP servers (top-level mcpServers) while preserving the BeforeAgent hook", () => {
    configureGemini(repo);
    const s = JSON.parse(fs.readFileSync(path.join(repo, ".gemini/settings.json"), "utf8"));
    expect(s.mcpServers["research-scholar"].command).toBe("npx");
    expect(s.mcpServers["research-scholar"].args).toContain("@research-copilot/mcp-scholar");
    expect(s.mcpServers["research-pdf"].args).toContain("@research-copilot/mcp-pdf");
    expect(s.hooks.BeforeAgent).toBeDefined(); // merge-safe with hooks block
    // hyphenated names only (Gemini rejects underscores)
    expect(Object.keys(s.mcpServers).every(k => !k.includes("_"))).toBe(true);
  });
  it("MCP write is merge-safe + idempotent (foreign mcpServers preserved; no dup args on re-run)", () => {
    fs.mkdirSync(path.join(repo, ".gemini"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".gemini/settings.json"),
      JSON.stringify({ mcpServers: { other: { command: "node", args: ["x.js"] } } }));
    configureGemini(repo); configureGemini(repo);
    const s = JSON.parse(fs.readFileSync(path.join(repo, ".gemini/settings.json"), "utf8"));
    expect(s.mcpServers.other).toBeDefined();
    expect(s.mcpServers["research-scholar"].args).toEqual(["-y", "@research-copilot/mcp-scholar"]);
  });
});
