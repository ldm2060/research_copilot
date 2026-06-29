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

  it("reports Claude Code plugin loading when --json lists an enabled research-copilot", () => {
    const r = runner({
      "claude plugin list --json": JSON.stringify([
        { id: "other-plugin@other", version: "0.0.1", enabled: true, scope: "user" },
        { id: "research-copilot@research-copilot", version: "1.1.17", enabled: true, scope: "project", projectPath: "C:\\repo" },
      ]),
    });

    const status = checkClaudePluginLoading(r, { repo: "C:\\repo", expectedVersion: "1.1.17" });

    expect(status.available).toBe(true);
    expect(status.listed).toBe(true);
    expect(status.enabled).toBe(true);
    expect(status.version).toBe("1.1.17");
    expect(status.message).toMatch(/enabled \(v1\.1\.17 /);
  });

  it("reports Claude Code plugin inspection as informational when claude is unavailable", () => {
    const r = runner({}, { "claude plugin list --json": new Error("not found") });

    expect(checkClaudePluginLoading(r)).toEqual({
      available: false,
      listed: false,
      enabled: false,
      version: null,
      message: "Claude Code plugin list unavailable; standalone configuration can still work. To register the npm plugin, run: rc plugin install --platform claude --scope project",
    });
  });

  it("reports a registration remediation command when Claude Code does not list research-copilot", () => {
    const r = runner({
      "claude plugin list --json": JSON.stringify([
        { id: "other-plugin@other", version: "0.0.1", enabled: true, scope: "user" },
      ]),
    });

    const status = checkClaudePluginLoading(r);

    expect(status.available).toBe(true);
    expect(status.listed).toBe(false);
    expect(status.enabled).toBe(false);
    expect(status.message).toContain("rc plugin install --platform claude --scope project");
  });

  it("flags a disabled research-copilot plugin with an enable remediation", () => {
    const r = runner({
      "claude plugin list --json": JSON.stringify([
        { id: "research-copilot@research-copilot", version: "1.0.54", enabled: false, scope: "project", projectPath: "C:\\QuantVLA" },
      ]),
    });

    const status = checkClaudePluginLoading(r, { repo: "C:\\aaai" });

    expect(status.listed).toBe(true);
    expect(status.enabled).toBe(false);
    expect(status.version).toBe("1.0.54");
    expect(status.message).toContain("DISABLED");
    expect(status.message).toContain("claude plugin enable research-copilot@research-copilot");
  });

  it("flags version drift when an enabled plugin does not match the expected version", () => {
    const r = runner({
      "claude plugin list --json": JSON.stringify([
        { id: "research-copilot@research-copilot", version: "1.0.54", enabled: true, scope: "project", projectPath: "C:\\aaai" },
      ]),
    });

    const status = checkClaudePluginLoading(r, { repo: "C:\\aaai", expectedVersion: "1.1.22" });

    expect(status.enabled).toBe(true);
    expect(status.message).toContain("stale");
    expect(status.message).toContain("v1.0.54");
    expect(status.message).toContain("v1.1.22");
  });

  it("prefers the project-scoped entry bound to the current repo when multiple exist", () => {
    const r = runner({
      "claude plugin list --json": JSON.stringify([
        { id: "research-copilot@research-copilot", version: "1.0.54", enabled: true, scope: "project", projectPath: "C:\\QuantVLA" },
        { id: "research-copilot@research-copilot", version: "1.1.22", enabled: true, scope: "project", projectPath: "C:\\aaai" },
      ]),
    });

    const status = checkClaudePluginLoading(r, { repo: "C:\\aaai" });

    expect(status.version).toBe("1.1.22");
  });

  it("finds research-copilot when the JSON array is nested under a wrapper object", () => {
    const r = runner({
      "claude plugin list --json": JSON.stringify({ plugins: [
        { id: "research-copilot@research-copilot", version: "1.1.22", enabled: true, scope: "user" },
      ] }),
    });

    const status = checkClaudePluginLoading(r, { expectedVersion: "1.1.22" });

    expect(status.listed).toBe(true);
    expect(status.enabled).toBe(true);
    expect(status.version).toBe("1.1.22");
  });

  it("treats non-JSON output as unavailable", () => {
    const r = runner({ "claude plugin list --json": "not json at all" });

    const status = checkClaudePluginLoading(r);

    expect(status.available).toBe(false);
    expect(status.listed).toBe(false);
    expect(status.message).toContain("non-JSON");
  });
});
