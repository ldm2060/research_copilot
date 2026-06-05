import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureOpenCode } from "../src/configurators/opencode.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("opencode configurator", () => {
  it("renders 10 agents to .opencode/agent/*.md with mode: subagent", () => {
    configureOpenCode(repo);
    const dir = path.join(repo, ".opencode/agent");
    const mds = fs.readdirSync(dir).filter(f => f.endsWith(".md"));
    expect(mds.length).toBe(10);
    const writer = fs.readFileSync(path.join(dir, "rc-writer.md"), "utf8");
    expect(writer).toMatch(/^---/);
    expect(writer).toContain("mode: subagent");
    expect(writer).toContain("description:");
    expect(writer.split("---").slice(2).join("---").trim().length).toBeGreaterThan(10); // body present
  });
  it("writes a plugin that spawns `rc context` as a subprocess (not in-process import)", () => {
    configureOpenCode(repo);
    const plug = fs.readFileSync(path.join(repo, ".opencode/plugin/research-copilot.ts"), "utf8");
    expect(plug).toContain("rc");
    expect(plug).toContain("context");
    expect(plug).toMatch(/child_process|execFile|spawn/);
    expect(plug).toContain("experimental.chat.system.transform");
    expect(plug).not.toMatch(/@research-copilot\/core/); // must NOT import core in-process
  });
  it("is idempotent (re-run: still 10 agents + 1 plugin)", () => {
    configureOpenCode(repo); configureOpenCode(repo);
    expect(fs.readdirSync(path.join(repo, ".opencode/agent")).filter(f=>f.endsWith(".md")).length).toBe(10);
    expect(fs.existsSync(path.join(repo, ".opencode/plugin/research-copilot.ts"))).toBe(true);
  });
  it("registers both MCP servers in opencode.json with local shape (command is an array)", () => {
    configureOpenCode(repo);
    const oc = JSON.parse(fs.readFileSync(path.join(repo, "opencode.json"), "utf8"));
    expect(oc.mcp["research-scholar"].type).toBe("local");
    expect(Array.isArray(oc.mcp["research-scholar"].command)).toBe(true);
    expect(oc.mcp["research-scholar"].command).toContain("@research-copilot/mcp-scholar");
    expect(oc.mcp["research-pdf"].command).toContain("@research-copilot/mcp-pdf");
  });
  it("MCP write is merge-safe + idempotent (foreign mcp preserved; no dup command on re-run)", () => {
    fs.writeFileSync(path.join(repo, "opencode.json"),
      JSON.stringify({ mcp: { other: { type: "local", command: ["node", "x.js"] } } }));
    configureOpenCode(repo); configureOpenCode(repo);
    const oc = JSON.parse(fs.readFileSync(path.join(repo, "opencode.json"), "utf8"));
    expect(oc.mcp.other).toBeDefined();
    expect(oc.mcp["research-scholar"].command).toEqual(["npx", "-y", "@research-copilot/mcp-scholar"]);
  });
});
