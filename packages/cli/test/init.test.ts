import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";
import type { CommandRunner } from "../src/commands/plugin.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

function fakeRunner(): CommandRunner & { calls: string[] } {
  const calls: string[] = [];
  return {
    calls,
    exec(command: string): string {
      calls.push(command);
      if (command.startsWith("npm list")) throw new Error("missing");
      return "";
    },
  };
}

describe("rc init", () => {
  it("scaffolds .research/ and Claude Code config without invoking npm when skipPlugin is true", () => {
    const r = fakeRunner();
    const result = runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true, runner: r });

    expect(fs.existsSync(path.join(repo, ".research/workflow.md"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".research/config.yaml"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".research/spec/venue"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".claude/settings.json"))).toBe(true);
    expect(fs.readdirSync(path.join(repo, ".claude/agents")).length).toBe(10);
    expect(result.plugin?.status).toBe("skipped");
    expect(r.calls).toEqual([]);
  });

  it("scaffolds multiple selected platforms without installing the Claude plugin when Claude Code is not selected", () => {
    const r = fakeRunner();
    const result = runInit({ repo, platforms: ["codex", "gemini"], user: "tester", runner: r });

    expect(fs.existsSync(path.join(repo, ".research/workflow.md"))).toBe(true);
    expect(fs.readdirSync(path.join(repo, ".codex/agents")).filter(f => f.endsWith(".toml")).length).toBe(10);
    expect(fs.readdirSync(path.join(repo, ".gemini/agents")).filter(f => f.endsWith(".md")).length).toBe(10);
    expect(fs.existsSync(path.join(repo, ".claude"))).toBe(false);
    expect(result.plugin).toBeNull();
    expect(r.calls).toEqual([]);
  });

  it("preserves existing research task/spec/workspace/runtime contents on re-run", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const keepers = [
      ".research/tasks/001/task.json",
      ".research/spec/custom.md",
      ".research/workspace/notes.md",
      ".research/runtime/cache.json",
    ];
    for (const rel of keepers) {
      fs.mkdirSync(path.dirname(path.join(repo, rel)), { recursive: true });
      fs.writeFileSync(path.join(repo, rel), `keep ${rel}`);
    }

    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });

    for (const rel of keepers) {
      expect(fs.readFileSync(path.join(repo, rel), "utf8")).toBe(`keep ${rel}`);
    }
  });

  it("does not overwrite an existing config.yaml or workflow.md during reconcile", () => {
    fs.mkdirSync(path.join(repo, ".research"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".research/config.yaml"), "custom: true\n");
    fs.writeFileSync(path.join(repo, ".research/workflow.md"), "custom workflow\n");

    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });

    expect(fs.readFileSync(path.join(repo, ".research/config.yaml"), "utf8")).toBe("custom: true\n");
    expect(fs.readFileSync(path.join(repo, ".research/workflow.md"), "utf8")).toBe("custom workflow\n");
  });

  it("restores missing managed rc agents while preserving user agents", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    fs.writeFileSync(path.join(repo, ".claude/agents/user-agent.md"), "# user agent\n");
    fs.rmSync(path.join(repo, ".claude/agents/rc-verify.md"));

    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });

    expect(fs.existsSync(path.join(repo, ".claude/agents/rc-verify.md"))).toBe(true);
    expect(fs.readFileSync(path.join(repo, ".claude/agents/user-agent.md"), "utf8")).toBe("# user agent\n");
  });

  it("syncs the plugin to the CLI version for Claude Code unless skipped", () => {
    const r = fakeRunner();

    const result = runInit({ repo, platforms: ["claude-code"], user: "tester", runner: r });

    expect(result.plugin?.status).toBe("installed");
    expect(r.calls.some(c => c.startsWith("npm install -g @research-copilot/plugin@"))).toBe(true);
  });

  it("preserves foreign Claude hooks and foreign MCP entries during upgrade reconcile", () => {
    fs.mkdirSync(path.join(repo, ".claude"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".claude/settings.json"), JSON.stringify({
      hooks: { SessionStart: [{ matcher: "*", hooks: [{ type: "command", command: "echo hello" }] }] },
    }));
    fs.writeFileSync(path.join(repo, ".mcp.json"), JSON.stringify({
      mcpServers: { "foreign-server": { command: "node", args: ["server.js"] } },
    }));

    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });

    const settings = JSON.parse(fs.readFileSync(path.join(repo, ".claude/settings.json"), "utf8"));
    expect(settings.hooks.SessionStart[0].hooks[0].command).toBe("echo hello");
    expect(settings.hooks.UserPromptSubmit[0].hooks[0].command).toContain("rc context");

    const mcp = JSON.parse(fs.readFileSync(path.join(repo, ".mcp.json"), "utf8"));
    expect(mcp.mcpServers["foreign-server"].command).toBe("node");
    expect(mcp.mcpServers["research-scholar"].command).toBe("npx");
    expect(mcp.mcpServers["research-pdf"].command).toBe("npx");
  });

  it("does not duplicate Research Copilot hooks after repeated upgrade reconciles", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });

    const settings = JSON.parse(fs.readFileSync(path.join(repo, ".claude/settings.json"), "utf8"));
    const rcHooks = settings.hooks.UserPromptSubmit
      .flatMap((group: any) => group.hooks ?? [])
      .filter((hook: any) => typeof hook.command === "string" && hook.command.includes("rc context"));
    expect(rcHooks.length).toBe(1);
  });
});
