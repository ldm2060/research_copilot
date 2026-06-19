import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runPluginCommand } from "../src/commands/plugin-command.js";

let repo: string;
let dist: string;

beforeEach(() => {
  repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-plugin-cmd-"));
  dist = path.join(repo, "fake-plugin-dist");
  fs.mkdirSync(path.join(dist, ".claude-plugin"), { recursive: true });
  fs.mkdirSync(path.join(dist, "skills", "research-workflow"), { recursive: true });
  fs.writeFileSync(path.join(dist, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "research-copilot" }));
  fs.writeFileSync(path.join(dist, "skills", "research-workflow", "SKILL.md"), "# Research Workflow\n");
});

describe("rc plugin command", () => {
  it("installs a local Claude project plugin", () => {
    const result = runPluginCommand("install", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });

    expect(result.ok).toBe(true);
    expect(result.report.join("\n")).toContain("Installed research-copilot plugin");
    expect(fs.existsSync(path.join(repo, ".claude", "skills", "research-copilot", ".claude-plugin", "plugin.json"))).toBe(true);
  });

  it("reports missing before install and ok after install", () => {
    const before = runPluginCommand("status", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });
    runPluginCommand("install", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });
    const after = runPluginCommand("status", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });

    expect(before.ok).toBe(false);
    expect(before.report.join("\n")).toContain("MISSING");
    expect(after.ok).toBe(true);
    expect(after.report.join("\n")).toContain("OK");
  });

  it("update uses install semantics and updates an existing registration", () => {
    runPluginCommand("install", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });

    const result = runPluginCommand("update", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });

    expect(result.ok).toBe(true);
    expect(result.report.join("\n")).toContain("Updated research-copilot plugin");
  });

  it("removes a Claude project plugin registration", () => {
    runPluginCommand("install", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });

    const result = runPluginCommand("remove", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });

    expect(result.ok).toBe(true);
    expect(result.report.join("\n")).toContain("Removed research-copilot plugin");
    expect(fs.existsSync(path.join(repo, ".claude", "skills", "research-copilot"))).toBe(false);
  });

  it("returns non-zero status when install would overwrite foreign content", () => {
    const target = path.join(repo, ".claude", "skills", "research-copilot");
    fs.mkdirSync(target, { recursive: true });
    fs.writeFileSync(path.join(target, "README.md"), "foreign\n");

    const result = runPluginCommand("install", repo, {
      platform: "claude",
      scope: "project",
      source: "local",
      path: dist,
    });

    expect(result.ok).toBe(false);
    expect(result.report.join("\n")).toContain("refusing to overwrite non-Research-Copilot directory");
  });
});
