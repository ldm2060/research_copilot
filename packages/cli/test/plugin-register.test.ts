import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import {
  expandPluginPlatforms,
  installPluginRegistration,
  normalizePluginPlatform,
  removePluginRegistration,
  resolvePlatformTargets,
  resolvePluginSource,
  statusPluginRegistration,
  type PluginRegistrationOptions,
} from "../src/commands/plugin-register.js";
import type { ExecOptions, CommandRunner } from "../src/commands/plugin.js";

let repo: string;
let home: string;
let dist: string;

beforeEach(() => {
  repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-plugin-reg-"));
  home = fs.mkdtempSync(path.join(os.tmpdir(), "rc-plugin-home-"));
  dist = path.join(repo, "fake-plugin-dist");
  fs.mkdirSync(path.join(dist, ".claude-plugin"), { recursive: true });
  fs.mkdirSync(path.join(dist, ".codex-plugin"), { recursive: true });
  fs.mkdirSync(path.join(dist, "skills", "research-workflow"), { recursive: true });
  fs.mkdirSync(path.join(dist, "agents"), { recursive: true });
  fs.writeFileSync(path.join(dist, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "research-copilot" }));
  fs.writeFileSync(path.join(dist, ".codex-plugin", "plugin.toml"), 'name = "research-copilot"\n');
  fs.writeFileSync(path.join(dist, "skills", "research-workflow", "SKILL.md"), "# Research Workflow\n");
  fs.writeFileSync(path.join(dist, "agents", "rc-test.md"), "# Agent\n");
});

function runner(outputs: Record<string, string>, failures: Record<string, Error> = {}): CommandRunner & { calls: string[] } {
  const calls: string[] = [];
  return {
    calls,
    exec(command: string, _options?: ExecOptions): string {
      calls.push(command);
      if (failures[command]) throw failures[command];
      return outputs[command] ?? "";
    },
  };
}

function opts(overrides: Partial<PluginRegistrationOptions> = {}): PluginRegistrationOptions {
  return {
    repo,
    platform: "claude",
    scope: "project",
    source: "local",
    sourcePath: dist,
    homeDir: home,
    ...overrides,
  };
}

describe("plugin registration helpers", () => {
  it("normalizes claude alias to claude-code", () => {
    expect(normalizePluginPlatform("claude")).toBe("claude-code");
    expect(normalizePluginPlatform("claude-code")).toBe("claude-code");
  });

  it("rejects unknown platform names with valid choices", () => {
    expect(() => normalizePluginPlatform("unknown-platform"))
      .toThrow(/unknown platform: unknown-platform.*claude.*codex.*gemini.*cursor.*opencode.*windsurf/s);
  });

  it("expands all platforms from the adapter registry", () => {
    expect(expandPluginPlatforms(repo, "all")).toEqual([
      "claude-code",
      "codex",
      "opencode",
      "gemini",
      "cursor",
      "windsurf",
    ]);
  });

  it("expands configured platforms by existing config directories", () => {
    fs.mkdirSync(path.join(repo, ".claude"));
    fs.mkdirSync(path.join(repo, ".gemini"));

    expect(expandPluginPlatforms(repo, "configured")).toEqual(["claude-code", "gemini"]);
  });

  it("defaults configured to claude-code when no platform config directory exists", () => {
    expect(expandPluginPlatforms(repo, "configured")).toEqual(["claude-code"]);
  });

  it("resolves and validates a local plugin dist", () => {
    expect(resolvePluginSource(opts())).toBe(path.resolve(dist));
  });

  it("rejects a local source without plugin metadata", () => {
    const bad = path.join(repo, "bad-dist");
    fs.mkdirSync(bad);

    expect(() => resolvePluginSource(opts({ sourcePath: bad })))
      .toThrow(/does not look like @research-copilot\/plugin dist/);
  });

  it("resolves npm plugin dist from npm root -g after sync", () => {
    const npmRoot = path.join(repo, "npm-root");
    const npmDist = path.join(npmRoot, "@research-copilot", "plugin", "dist");
    fs.mkdirSync(path.join(npmDist, ".claude-plugin"), { recursive: true });
    fs.mkdirSync(path.join(npmDist, "skills"), { recursive: true });
    fs.writeFileSync(path.join(npmDist, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "research-copilot" }));
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({ dependencies: { "@research-copilot/plugin": { version: "1.1.17" } } }),
      "npm root -g": npmRoot,
    });

    const source = resolvePluginSource(opts({ source: "npm", sourcePath: undefined, runner: r, cliVersion: "1.1.17" }));

    expect(source).toBe(npmDist);
    expect(r.calls).toEqual([
      "npm list -g @research-copilot/plugin --json",
      "npm root -g",
    ]);
  });
});
