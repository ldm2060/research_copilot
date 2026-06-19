import { describe, it, expect } from "vitest";
import {
  checkClaudePluginLoading,
  getInstalledPluginVersion,
  syncPluginPackage,
  type CommandRunner,
} from "../src/commands/plugin.js";

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

describe("plugin package helpers", () => {
  it("reads the installed global plugin version from npm list JSON", () => {
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: "1.1.17" } },
      }),
    });

    expect(getInstalledPluginVersion(r)).toBe("1.1.17");
  });

  it("returns null when npm list fails or the dependency is absent", () => {
    const r = runner({}, { "npm list -g @research-copilot/plugin --json": new Error("missing") });

    expect(getInstalledPluginVersion(r)).toBeNull();
  });

  it("skips plugin sync when --skip-plugin is active", () => {
    const r = runner({});

    const result = syncPluginPackage({ version: "1.1.17", skip: true, strict: false, runner: r });

    expect(result.status).toBe("skipped");
    expect(r.calls).toEqual([]);
  });

  it("does not reinstall when the installed version already matches", () => {
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: "1.1.17" } },
      }),
    });

    const result = syncPluginPackage({ version: "1.1.17", skip: false, strict: false, runner: r });

    expect(result.status).toBe("ok");
    expect(result.installedVersion).toBe("1.1.17");
    expect(r.calls).toEqual(["npm list -g @research-copilot/plugin --json"]);
  });

  it("installs the exact CLI version when the plugin is missing", () => {
    const r = runner(
      { "npm install -g @research-copilot/plugin@1.1.17": "installed" },
      { "npm list -g @research-copilot/plugin --json": new Error("missing") },
    );

    const result = syncPluginPackage({ version: "1.1.17", skip: false, strict: false, runner: r });

    expect(result.status).toBe("installed");
    expect(r.calls).toEqual([
      "npm list -g @research-copilot/plugin --json",
      "npm install -g @research-copilot/plugin@1.1.17",
    ]);
  });

  it("updates the exact CLI version when the plugin version differs", () => {
    const r = runner({
      "npm list -g @research-copilot/plugin --json": JSON.stringify({
        dependencies: { "@research-copilot/plugin": { version: "1.1.13" } },
      }),
      "npm install -g @research-copilot/plugin@1.1.17": "updated",
    });

    const result = syncPluginPackage({ version: "1.1.17", skip: false, strict: false, runner: r });

    expect(result.status).toBe("updated");
    expect(result.installedVersion).toBe("1.1.13");
  });

  it("returns a warning result when npm install fails in non-strict mode", () => {
    const r = runner(
      {},
      {
        "npm list -g @research-copilot/plugin --json": new Error("missing"),
        "npm install -g @research-copilot/plugin@1.1.17": new Error("network down"),
      },
    );

    const result = syncPluginPackage({ version: "1.1.17", skip: false, strict: false, runner: r });

    expect(result.status).toBe("warning");
    expect(result.message).toContain("npm install -g @research-copilot/plugin@1.1.17");
  });

  it("throws when npm install fails in strict mode", () => {
    const r = runner(
      {},
      {
        "npm list -g @research-copilot/plugin --json": new Error("missing"),
        "npm install -g @research-copilot/plugin@1.1.17": new Error("network down"),
      },
    );

    expect(() => syncPluginPackage({ version: "1.1.17", skip: false, strict: true, runner: r }))
      .toThrow(/Failed to install @research-copilot\/plugin@1.1.17/);
  });

  it("reports Claude Code plugin loading when claude plugin list contains research-copilot", () => {
    const r = runner({ "claude plugin list": "research-copilot 1.1.17\nother-plugin 0.0.1" });

    expect(checkClaudePluginLoading(r)).toEqual({
      available: true,
      listed: true,
      message: "Claude Code lists research-copilot plugin",
    });
  });

  it("reports Claude Code plugin inspection as informational when claude is unavailable", () => {
    const r = runner({}, { "claude plugin list": new Error("not found") });

    expect(checkClaudePluginLoading(r)).toEqual({
      available: false,
      listed: false,
      message: "Claude Code plugin list unavailable; standalone configuration can still work. To register the npm plugin, run: rc plugin install --platform claude --scope project",
    });
  });

  it("reports a registration remediation command when Claude Code does not list research-copilot", () => {
    const r = runner({ "claude plugin list": "other-plugin 0.0.1" });

    expect(checkClaudePluginLoading(r)).toEqual({
      available: true,
      listed: false,
      message: "Claude Code is available but does not list research-copilot plugin; standalone configuration can still work. To register the npm plugin, run: rc plugin install --platform claude --scope project",
    });
  });
});
