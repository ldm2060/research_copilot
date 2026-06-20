import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runDoctor } from "../src/commands/doctor.js";
import { runInit } from "../src/commands/init.js";
import { readCliVersion, type CommandRunner } from "../src/commands/plugin.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

function runner(outputs: Record<string, string>, failures: Record<string, Error> = {}): CommandRunner & { calls: string[] } {
  const calls: string[] = [];
  return {
    calls,
    exec(command: string): string {
      calls.push(command);
      if (failures[command]) throw failures[command];
      return outputs[command] ?? "";
    },
  };
}

describe("rc doctor", () => {
  it("fails core checks when project config is missing", () => {
    const r = runner({}, { "npm list -g @research-copilot/plugin --json": new Error("missing") });

    const result = runDoctor(repo, { runner: r });

    expect(result.ok).toBe(false);
    expect(result.report.join("\n")).toContain("FAIL .research/ exists");
    expect(result.report.join("\n")).toContain("WARN Plugin not installed");
  });

  it("passes core checks and warns on missing plugin by default", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const r = runner({}, { "npm list -g @research-copilot/plugin --json": new Error("missing") });

    const result = runDoctor(repo, { runner: r });

    expect(result.ok).toBe(true);
    expect(result.report.join("\n")).toContain("OK .research/ exists");
    expect(result.report.join("\n")).toContain("WARN Plugin not installed");
  });

  it("fails missing plugin under strict plugin mode", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const r = runner({}, { "npm list -g @research-copilot/plugin --json": new Error("missing") });

    const result = runDoctor(repo, { strictPlugin: true, runner: r });

    expect(result.ok).toBe(false);
    expect(result.report.join("\n")).toContain("FAIL Plugin not installed");
  });

  it("reports plugin version mismatch with exact remediation command", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: "0.0.1" } },
      }),
    });

    const result = runDoctor(repo, { runner: r });

    expect(result.ok).toBe(true);
    expect(result.report.join("\n")).toMatch(/WARN Plugin version mismatch \(CLI: .+, Plugin: 0\.0\.1\)/);
    expect(result.report.join("\n")).toMatch(/npm install -g @research-copilot\/plugin@/);
  });

  it("reports Claude Code plugin loading as informational", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: readCliVersion() } },
      }),
      "claude plugin list": "research-copilot 1.1.17",
    });

    const result = runDoctor(repo, { runner: r });

    expect(result.report.join("\n")).toContain("INFO Claude Code lists research-copilot plugin");
  });

  it("prints plugin registration remediation when Claude Code does not list the plugin", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: readCliVersion() } },
      }),
      "claude plugin list": "other-plugin 0.0.1",
    });

    const result = runDoctor(repo, { runner: r });

    expect(result.ok).toBe(true);
    expect(result.report.join("\n")).toContain("rc plugin install --platform claude --scope project");
  });

  it("does not repeat registration remediation when Claude project plugin is installed", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const target = path.join(repo, ".claude", "skills", "research-copilot");
    fs.mkdirSync(path.join(target, ".claude-plugin"), { recursive: true });
    fs.writeFileSync(path.join(target, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "research-copilot" }));
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: readCliVersion() } },
      }),
      "claude plugin list": "other-plugin 0.0.1",
    });

    const result = runDoctor(repo, { runner: r });
    const report = result.report.join("\n");

    expect(result.ok).toBe(true);
    expect(report).toContain("OK Claude project plugin registration exists");
    expect(report).toContain("INFO Claude Code is available but does not list project-registered research-copilot plugin; project plugin registration is installed");
    expect(report).not.toContain("rc plugin install --platform claude --scope project");
  });

  it("does not repeat registration remediation when Claude Code plugin list is unavailable but project plugin is installed", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const target = path.join(repo, ".claude", "skills", "research-copilot");
    fs.mkdirSync(path.join(target, ".claude-plugin"), { recursive: true });
    fs.writeFileSync(path.join(target, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "research-copilot" }));
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: readCliVersion() } },
      }),
    }, { "claude plugin list": new Error("not found") });

    const result = runDoctor(repo, { runner: r });
    const report = result.report.join("\n");

    expect(result.ok).toBe(true);
    expect(report).toContain("INFO Claude Code plugin list unavailable; project plugin registration is installed");
    expect(report).not.toContain("rc plugin install --platform claude --scope project");
  });

  it("--fix restores missing core config without syncing plugin when skipPlugin is true", () => {
    fs.mkdirSync(path.join(repo, ".research/tasks/001"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".research/tasks/001/task.json"), "{\"id\":\"001\"}\n");
    const r = runner({});

    const result = runDoctor(repo, { fix: true, skipPlugin: true, runner: r });

    expect(result.ok).toBe(true);
    expect(fs.existsSync(path.join(repo, ".research/workflow.md"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".claude/settings.json"))).toBe(true);
    expect(fs.readFileSync(path.join(repo, ".research/tasks/001/task.json"), "utf8")).toBe("{\"id\":\"001\"}\n");
    expect(r.calls).toEqual([]);
    expect(result.report.join("\n")).toContain("Fixed: reconciled Research Copilot project configuration");
  });
});
