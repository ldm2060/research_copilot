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

  it("resolves Claude project and user targets", () => {
    expect(resolvePlatformTargets(opts({ platform: "claude", scope: "project" }))).toEqual([
      path.join(repo, ".claude", "skills", "research-copilot"),
    ]);
    expect(resolvePlatformTargets(opts({ platform: "claude", scope: "user" }))).toEqual([
      path.join(home, ".claude", "skills", "research-copilot"),
    ]);
  });

  it("resolves Gemini project targets from both registry skill paths", () => {
    expect(resolvePlatformTargets(opts({ platform: "gemini", scope: "project" }))).toEqual([
      path.join(repo, ".gemini", "skills", "research-copilot"),
      path.join(repo, ".agents", "skills", "research-copilot"),
    ]);
  });

  it("rejects user scope for non-Claude platforms", () => {
    expect(() => resolvePlatformTargets(opts({ platform: "codex", scope: "user" })))
      .toThrow(/user scope is only supported for claude/);
  });

  it("installs Claude project registration by copying plugin dist", () => {
    const [result] = installPluginRegistration(opts({ platform: "claude", scope: "project" }));
    const target = path.join(repo, ".claude", "skills", "research-copilot");

    expect(result.status).toBe("installed");
    expect(result.target).toBe(target);
    expect(fs.existsSync(path.join(target, ".claude-plugin", "plugin.json"))).toBe(true);
    expect(fs.existsSync(path.join(target, "skills", "research-workflow", "SKILL.md"))).toBe(true);
  });

  it("updates an existing Research Copilot registration idempotently", () => {
    const target = path.join(repo, ".claude", "skills", "research-copilot");
    installPluginRegistration(opts({ platform: "claude", scope: "project" }));
    fs.writeFileSync(path.join(target, "old-managed-file.txt"), "old\n");

    const [result] = installPluginRegistration(opts({ platform: "claude", scope: "project" }));

    expect(result.status).toBe("updated");
    expect(fs.existsSync(path.join(target, "old-managed-file.txt"))).toBe(false);
    expect(fs.existsSync(path.join(target, ".claude-plugin", "plugin.json"))).toBe(true);
  });

  it("refuses to overwrite an existing non-Research-Copilot target", () => {
    const target = path.join(repo, ".claude", "skills", "research-copilot");
    fs.mkdirSync(target, { recursive: true });
    fs.writeFileSync(path.join(target, "README.md"), "user-owned\n");

    const [result] = installPluginRegistration(opts({ platform: "claude", scope: "project" }));

    expect(result.status).toBe("failed");
    expect(result.message).toContain("refusing to overwrite non-Research-Copilot directory");
    expect(fs.readFileSync(path.join(target, "README.md"), "utf8")).toBe("user-owned\n");
  });

  it("installs Gemini into both project targets", () => {
    const results = installPluginRegistration(opts({ platform: "gemini", scope: "project" }));

    expect(results.map(r => r.status)).toEqual(["installed", "installed"]);
    expect(fs.existsSync(path.join(repo, ".gemini", "skills", "research-copilot", ".claude-plugin", "plugin.json"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".agents", "skills", "research-copilot", ".claude-plugin", "plugin.json"))).toBe(true);
  });

  it("reports missing and ok status for registrations", () => {
    expect(statusPluginRegistration(opts({ platform: "claude", scope: "project" }))[0].status).toBe("missing");
    installPluginRegistration(opts({ platform: "claude", scope: "project" }));

    const [result] = statusPluginRegistration(opts({ platform: "claude", scope: "project" }));

    expect(result.status).toBe("ok");
    expect(result.message).toContain(".claude");
  });

  it("labels status messages with user scope for Claude user installs", () => {
    installPluginRegistration(opts({ platform: "claude", scope: "user" }));

    const [result] = statusPluginRegistration(opts({ platform: "claude", scope: "user" }));

    expect(result.status).toBe("ok");
    expect(result.message).toContain("user plugin:");
    expect(result.message).not.toContain("project plugin:");
  });

  it("labels status messages with project scope for Claude project installs", () => {
    installPluginRegistration(opts({ platform: "claude", scope: "project" }));

    const [result] = statusPluginRegistration(opts({ platform: "claude", scope: "project" }));

    expect(result.status).toBe("ok");
    expect(result.message).toContain("project plugin:");
  });

  it("removes only Research Copilot registration target", () => {
    const sibling = path.join(repo, ".claude", "skills", "other-plugin");
    fs.mkdirSync(sibling, { recursive: true });
    fs.writeFileSync(path.join(sibling, "README.md"), "keep\n");
    installPluginRegistration(opts({ platform: "claude", scope: "project" }));

    const [result] = removePluginRegistration(opts({ platform: "claude", scope: "project" }));

    expect(result.status).toBe("removed");
    expect(fs.existsSync(path.join(repo, ".claude", "skills", "research-copilot"))).toBe(false);
    expect(fs.readFileSync(path.join(sibling, "README.md"), "utf8")).toBe("keep\n");
  });

  it("refuses to remove a non-Research-Copilot target", () => {
    const target = path.join(repo, ".claude", "skills", "research-copilot");
    fs.mkdirSync(target, { recursive: true });
    fs.writeFileSync(path.join(target, "README.md"), "user-owned\n");

    const [result] = removePluginRegistration(opts({ platform: "claude", scope: "project" }));

    expect(result.status).toBe("failed");
    expect(fs.existsSync(target)).toBe(true);
  });

  it("aggregate user-scope operations produce failed results instead of throwing", () => {
    const statusResults = statusPluginRegistration(opts({ platform: "all", scope: "user" }));
    const nonClaude = statusResults.filter(r => r.platform !== "claude-code");

    // Should not throw; non-Claude platforms should have structured failed results
    expect(nonClaude.length).toBeGreaterThan(0);
    for (const r of nonClaude) {
      expect(r.status).toBe("failed");
      expect(r.message).toContain("user scope is only supported for claude");
    }

    // Claude-code user scope should still be resolved normally
    const claudeResults = statusResults.filter(r => r.platform === "claude-code");
    expect(claudeResults.length).toBe(1);
    expect(claudeResults[0].status).toBe("missing"); // not installed yet
  });

  it("aggregate install with user scope produces failed results for non-Claude platforms", () => {
    const results = installPluginRegistration(opts({ platform: "all", scope: "user" }));

    // Only claude-code should succeed (installed); others should be failed
    const nonClaude = results.filter(r => r.platform !== "claude-code");
    for (const r of nonClaude) {
      expect(r.status).toBe("failed");
      expect(r.message).toContain("user scope is only supported for claude");
    }
    const claudeResult = results.find(r => r.platform === "claude-code");
    expect(claudeResult?.status).toBe("installed");
  });

  it("aggregate project operations dedupe the shared .agents/skills/research-copilot target", () => {
    const results = installPluginRegistration(opts({ platform: "all", scope: "project" }));
    const targets = results.map(r => r.target);

    // No duplicate physical paths
    expect(targets.length).toBe(new Set(targets).size);

    // Gemini should contribute only its .gemini/skills target when deduped
    // (codex already claimed .agents/skills/research-copilot earlier in PLATFORM_ORDER)
    const geminiResults = results.filter(r => r.platform === "gemini");
    expect(geminiResults.length).toBe(1);
    expect(geminiResults[0].target).toContain(path.join(".gemini", "skills", "research-copilot"));
  });

  it("direct Gemini registration preserves both project targets without deduplication", () => {
    const results = installPluginRegistration(opts({ platform: "gemini", scope: "project" }));

    expect(results.length).toBe(2);
    expect(results.map(r => r.status)).toEqual(["installed", "installed"]);
    expect(fs.existsSync(path.join(repo, ".gemini", "skills", "research-copilot", ".claude-plugin", "plugin.json"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".agents", "skills", "research-copilot", ".claude-plugin", "plugin.json"))).toBe(true);
  });
});
