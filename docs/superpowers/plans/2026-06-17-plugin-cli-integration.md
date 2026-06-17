# Plugin CLI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `rc init` and `rc doctor` fully integrate the published `@research-copilot/plugin` package while remaining safe for users upgrading from older Research Copilot versions.

**Architecture:** Add focused CLI helper modules for plugin package synchronization, project reconciliation, and doctor checks. Keep platform-specific file writes in the existing adapter configurators, but route `rc init` and `rc doctor --fix` through one shared reconcile path so upgrades and fresh installs behave the same way.

**Tech Stack:** TypeScript ESM, Commander, Vitest, Node built-ins (`fs`, `path`, `child_process`), existing `@research-copilot/core` and `@research-copilot/adapters` packages.

## Global Constraints

- `rc init` must work for both new projects and older Research Copilot projects.
- Users upgrading from older versions must not need to delete `.research/`, `.claude/`, or MCP configuration.
- The npm plugin package must be installed or updated to match the CLI version when Claude Code support is enabled.
- `rc doctor` must distinguish between core project failures and plugin-related warnings.
- Integration must be safe, idempotent, and reversible: merge missing Research Copilot-managed entries, preserve user-owned configuration, and avoid destructive rewrites.
- Do not require Claude Code marketplace setup before Research Copilot can function.
- Do not imply that `npm install -g @research-copilot/plugin` alone makes Claude Code load a plugin.
- Do not overwrite user hooks, user agents, existing `.research/tasks`, specs, workspace files, or unrelated MCP entries.
- Plugin installation failures warn by default and fail only under `--strict-plugin`.
- `rc doctor --fix` is the explicit old-version upgrade path; do not add `rc upgrade` in this implementation.

---

## File Structure

- Create `packages/cli/src/commands/plugin.ts`  
  Owns CLI version reading, npm global plugin version detection, npm plugin synchronization, command-runner injection for tests, and informational Claude Code plugin-list inspection.

- Create `packages/cli/src/commands/reconcile.ts`  
  Owns idempotent project desired-state reconciliation: `.research/` directories, missing workflow/config files, and platform configurator dispatch.

- Modify `packages/cli/src/commands/init.ts`  
  Delegates project setup to `reconcileProject()`, delegates plugin sync to `syncPluginPackage()`, adds `--skip-plugin` and `--strict-plugin`, and returns a structured result for tests.

- Modify `packages/cli/src/commands/doctor.ts`  
  Adds structured checks, `--fix`, `--skip-plugin`, and `--strict-plugin`; checks core config separately from plugin status.

- Modify `packages/cli/src/program.ts`  
  Passes Commander options into `runDoctor()` and `runInit()`.

- Modify tests that call `runInit()` directly  
  Add `skipPlugin: true` where the test is not about npm plugin sync, so test runs never invoke real npm.

- Create `packages/cli/test/plugin.test.ts`  
  Unit tests for plugin helper behavior with fake command runners.

- Create `packages/cli/test/doctor.test.ts`  
  Unit tests for doctor core checks, plugin warnings, strict plugin mode, and `--fix`.

- Modify `packages/cli/test/init.test.ts`, `packages/cli/test/e2e.test.ts`, `packages/cli/test/verify-gate.test.ts`  
  Cover init plugin options and preserve existing tests without real npm calls.

- Modify `INSTALLATION.md`  
  Document the upgrade path and plugin warning remediation.

---

### Task 1: Add plugin package lifecycle helpers

**Files:**
- Create: `packages/cli/src/commands/plugin.ts`
- Create: `packages/cli/test/plugin.test.ts`

**Interfaces:**
- Produces:
  - `PLUGIN_PACKAGE = "@research-copilot/plugin"`
  - `CommandRunner` interface: `{ exec(command: string, options?: ExecOptions): string }`
  - `defaultCommandRunner: CommandRunner`
  - `readCliVersion(startDir?: string): string`
  - `getInstalledPluginVersion(runner?: CommandRunner): string | null`
  - `syncPluginPackage(options: SyncPluginOptions): PluginSyncResult`
  - `checkClaudePluginLoading(runner?: CommandRunner): ClaudePluginStatus`
- Consumes: Node `child_process.execSync`, package metadata near compiled command files.

- [ ] **Step 1: Write failing plugin helper tests**

Create `packages/cli/test/plugin.test.ts` with this content:

```ts
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
      message: "Claude Code plugin list unavailable; standalone configuration can still work",
    });
  });
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
pnpm vitest run packages/cli/test/plugin.test.ts
```

Expected: FAIL with module/import errors for `../src/commands/plugin.js` or missing exported symbols.

- [ ] **Step 3: Implement plugin helper module**

Create `packages/cli/src/commands/plugin.ts` with this content:

```ts
import { execSync, type ExecSyncOptions } from "node:child_process";
import * as fs from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const PLUGIN_PACKAGE = "@research-copilot/plugin";

export interface ExecOptions {
  timeout?: number;
}

export interface CommandRunner {
  exec(command: string, options?: ExecOptions): string;
}

export const defaultCommandRunner: CommandRunner = {
  exec(command: string, options: ExecOptions = {}): string {
    const execOptions: ExecSyncOptions = {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      timeout: options.timeout ?? 30000,
    };
    return String(execSync(command, execOptions));
  },
};

export type PluginSyncStatus = "skipped" | "ok" | "installed" | "updated" | "warning";

export interface SyncPluginOptions {
  version: string;
  skip: boolean;
  strict: boolean;
  runner?: CommandRunner;
}

export interface PluginSyncResult {
  status: PluginSyncStatus;
  expectedVersion: string;
  installedVersion: string | null;
  message: string;
}

export interface ClaudePluginStatus {
  available: boolean;
  listed: boolean;
  message: string;
}

export function readCliVersion(startDir = dirname(fileURLToPath(import.meta.url))): string {
  let dir = startDir;
  for (;;) {
    const candidate = join(dir, "package.json");
    if (fs.existsSync(candidate)) {
      const pkg = JSON.parse(fs.readFileSync(candidate, "utf8"));
      if (typeof pkg.version === "string" && pkg.version.length > 0) return pkg.version;
    }
    const parent = dirname(dir);
    if (parent === dir) throw new Error(`Unable to determine CLI version from package.json above ${startDir}`);
    dir = parent;
  }
}

export function getInstalledPluginVersion(runner: CommandRunner = defaultCommandRunner): string | null {
  try {
    const output = runner.exec(`npm list -g ${PLUGIN_PACKAGE} --json`, { timeout: 5000 });
    const parsed = JSON.parse(output);
    const version = parsed?.dependencies?.[PLUGIN_PACKAGE]?.version;
    return typeof version === "string" && version.length > 0 ? version : null;
  } catch {
    return null;
  }
}

export function syncPluginPackage(options: SyncPluginOptions): PluginSyncResult {
  const runner = options.runner ?? defaultCommandRunner;
  const expected = options.version;
  const installCommand = `npm install -g ${PLUGIN_PACKAGE}@${expected}`;

  if (options.skip) {
    return {
      status: "skipped",
      expectedVersion: expected,
      installedVersion: null,
      message: `Skipped ${PLUGIN_PACKAGE} synchronization`,
    };
  }

  const installed = getInstalledPluginVersion(runner);
  if (installed === expected) {
    return {
      status: "ok",
      expectedVersion: expected,
      installedVersion: installed,
      message: `${PLUGIN_PACKAGE} already matches CLI version ${expected}`,
    };
  }

  try {
    runner.exec(installCommand, { timeout: 60000 });
    return {
      status: installed ? "updated" : "installed",
      expectedVersion: expected,
      installedVersion: installed,
      message: installed
        ? `Updated ${PLUGIN_PACKAGE} from ${installed} to ${expected}`
        : `Installed ${PLUGIN_PACKAGE}@${expected}`,
    };
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    const message = `Failed to install ${PLUGIN_PACKAGE}@${expected}: ${detail}. Run manually: ${installCommand}`;
    if (options.strict) throw new Error(message);
    return {
      status: "warning",
      expectedVersion: expected,
      installedVersion: installed,
      message,
    };
  }
}

export function checkClaudePluginLoading(runner: CommandRunner = defaultCommandRunner): ClaudePluginStatus {
  try {
    const output = runner.exec("claude plugin list", { timeout: 5000 });
    const listed = /research-copilot/i.test(output);
    return {
      available: true,
      listed,
      message: listed
        ? "Claude Code lists research-copilot plugin"
        : "Claude Code is available but does not list research-copilot plugin; standalone configuration can still work",
    };
  } catch {
    return {
      available: false,
      listed: false,
      message: "Claude Code plugin list unavailable; standalone configuration can still work",
    };
  }
}
```

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
pnpm vitest run packages/cli/test/plugin.test.ts
```

Expected: PASS for all plugin helper tests.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/plugin.ts packages/cli/test/plugin.test.ts
git commit -m "feat(cli): add plugin sync helpers"
```

---

### Task 2: Move project setup into idempotent reconciliation

**Files:**
- Create: `packages/cli/src/commands/reconcile.ts`
- Modify: `packages/cli/src/commands/init.ts`
- Modify: `packages/cli/test/init.test.ts`
- Modify: `packages/cli/test/e2e.test.ts`
- Modify: `packages/cli/test/verify-gate.test.ts`

**Interfaces:**
- Consumes from Task 1: `CommandRunner`, `readCliVersion`, `syncPluginPackage`, `PluginSyncResult`.
- Produces:
  - `ReconcileArgs`: `{ repo: string; platforms: string[]; user: string }`
  - `ReconcileResult`: `{ created: string[]; updated: string[]; skipped: string[] }`
  - `reconcileProject(args: ReconcileArgs): ReconcileResult`
  - `InitArgs` extended with `skipPlugin?: boolean`, `strictPlugin?: boolean`, `runner?: CommandRunner`
  - `InitResult`: `{ reconcile: ReconcileResult; plugin: PluginSyncResult | null }`

- [ ] **Step 1: Write failing init/reconcile tests**

Modify `packages/cli/test/init.test.ts` to this content:

```ts
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
});
```

Modify direct `runInit()` calls in `packages/cli/test/e2e.test.ts` and `packages/cli/test/verify-gate.test.ts` by adding `skipPlugin: true`:

```ts
runInit({ repo, platforms: ["claude-code"], user: "t", skipPlugin: true });
```

- [ ] **Step 2: Run focused init tests and verify they fail**

Run:

```bash
pnpm vitest run packages/cli/test/init.test.ts packages/cli/test/e2e.test.ts packages/cli/test/verify-gate.test.ts
```

Expected: FAIL because `skipPlugin`, `runner`, `InitResult`, and `reconcileProject()` do not exist yet.

- [ ] **Step 3: Implement project reconciliation**

Create `packages/cli/src/commands/reconcile.ts` with this content:

```ts
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { researchPaths } from "@research-copilot/core";
import { configurePlatform, kitRoot } from "@research-copilot/adapters";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export interface ReconcileArgs {
  repo: string;
  platforms: string[];
  user: string;
}

export interface ReconcileResult {
  created: string[];
  updated: string[];
  skipped: string[];
}

function ensureDir(dir: string, rel: string, result: ReconcileResult): void {
  if (fs.existsSync(dir)) {
    result.skipped.push(rel);
    return;
  }
  fs.mkdirSync(dir, { recursive: true });
  result.created.push(rel);
}

function copyIfMissing(src: string, dst: string, rel: string, result: ReconcileResult): void {
  if (fs.existsSync(dst)) {
    result.skipped.push(rel);
    return;
  }
  fs.copyFileSync(src, dst);
  result.created.push(rel);
}

export function reconcileProject(args: ReconcileArgs): ReconcileResult {
  const result: ReconcileResult = { created: [], updated: [], skipped: [] };
  const paths = researchPaths(args.repo);

  for (const [dir, rel] of [
    [paths.tasks, ".research/tasks"],
    [paths.spec, ".research/spec"],
    [paths.workspace, ".research/workspace"],
    [paths.runtime, ".research/runtime"],
  ] as const) {
    ensureDir(dir, rel, result);
  }

  for (const name of ["venue", "writing", "baselines", "methodology", "novelty"]) {
    ensureDir(path.join(paths.spec, name), `.research/spec/${name}`, result);
  }

  const kit = kitRoot(__dirname);
  copyIfMissing(path.join(kit, "workflow.md"), paths.workflow, ".research/workflow.md", result);
  copyIfMissing(path.join(kit, "config.defaults.yaml"), paths.config, ".research/config.yaml", result);

  for (const platform of args.platforms) {
    configurePlatform(args.repo, platform);
    result.updated.push(`platform:${platform}`);
  }

  return result;
}
```

- [ ] **Step 4: Refactor init to use reconciliation and plugin sync**

Replace `packages/cli/src/commands/init.ts` with this content:

```ts
import type { Command } from "commander";
import { reconcileProject, type ReconcileResult } from "./reconcile.js";
import {
  readCliVersion,
  syncPluginPackage,
  type CommandRunner,
  type PluginSyncResult,
} from "./plugin.js";

export interface InitArgs {
  repo: string;
  platforms: string[];
  user: string;
  skipPlugin?: boolean;
  strictPlugin?: boolean;
  runner?: CommandRunner;
}

export interface InitResult {
  reconcile: ReconcileResult;
  plugin: PluginSyncResult | null;
}

export function runInit(args: InitArgs): InitResult {
  const reconcile = reconcileProject({ repo: args.repo, platforms: args.platforms, user: args.user });
  let plugin: PluginSyncResult | null = null;

  if (args.platforms.includes("claude-code")) {
    plugin = syncPluginPackage({
      version: readCliVersion(),
      skip: args.skipPlugin ?? false,
      strict: args.strictPlugin ?? false,
      runner: args.runner,
    });
  }

  return { reconcile, plugin };
}

export function registerInit(program: Command, repo: string): void {
  program.command("init")
    .option("--claude", "Claude Code", false)
    .option("--codex", "OpenAI Codex", false)
    .option("--opencode", "OpenCode", false)
    .option("--gemini", "Gemini CLI", false)
    .option("--cursor", "Cursor", false)
    .option("--windsurf", "Windsurf", false)
    .option("--skip-plugin", "Skip npm plugin synchronization", false)
    .option("--strict-plugin", "Fail when npm plugin synchronization fails", false)
    .requiredOption("-u, --user <name>", "developer identity")
    .action((opts) => {
      const platforms: string[] = [];
      if (opts.claude) platforms.push("claude-code");
      if (opts.codex) platforms.push("codex");
      if (opts.opencode) platforms.push("opencode");
      if (opts.gemini) platforms.push("gemini");
      if (opts.cursor) platforms.push("cursor");
      if (opts.windsurf) platforms.push("windsurf");
      if (platforms.length === 0) platforms.push("claude-code");

      const result = runInit({
        repo,
        platforms,
        user: opts.user,
        skipPlugin: opts.skipPlugin,
        strictPlugin: opts.strictPlugin,
      });

      process.stdout.write(`Initialized .research/ for: ${platforms.join(", ")}\n`);
      if (result.plugin) process.stdout.write(`${result.plugin.message}\n`);
    });
}
```

- [ ] **Step 5: Run focused init tests and verify they pass**

Run:

```bash
pnpm vitest run packages/cli/test/init.test.ts packages/cli/test/e2e.test.ts packages/cli/test/verify-gate.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/cli/src/commands/reconcile.ts packages/cli/src/commands/init.ts packages/cli/test/init.test.ts packages/cli/test/e2e.test.ts packages/cli/test/verify-gate.test.ts
git commit -m "feat(cli): reconcile init and plugin sync"
```

---

### Task 3: Expand doctor checks, strict plugin mode, and fix mode

**Files:**
- Modify: `packages/cli/src/commands/doctor.ts`
- Modify: `packages/cli/src/program.ts`
- Create: `packages/cli/test/doctor.test.ts`

**Interfaces:**
- Consumes from Task 1: `CommandRunner`, `checkClaudePluginLoading`, `getInstalledPluginVersion`, `readCliVersion`, `PLUGIN_PACKAGE`.
- Consumes from Task 2: `runInit()` and `skipPlugin` support.
- Produces:
  - `DoctorOptions`: `{ strictPlugin?: boolean; fix?: boolean; skipPlugin?: boolean; runner?: CommandRunner }`
  - `runDoctor(repo: string, options?: DoctorOptions): { ok: boolean; report: string[] }`

- [ ] **Step 1: Write failing doctor tests**

Create `packages/cli/test/doctor.test.ts` with this content:

```ts
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
```

- [ ] **Step 2: Run focused doctor tests and verify they fail**

Run:

```bash
pnpm vitest run packages/cli/test/doctor.test.ts
```

Expected: FAIL because `runDoctor()` does not accept options, lacks strict/fix behavior, and lacks expanded checks.

- [ ] **Step 3: Implement expanded doctor**

Replace `packages/cli/src/commands/doctor.ts` with this content:

```ts
import * as fs from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { kitRoot, MCP_SERVERS } from "@research-copilot/adapters";
import { runInit } from "./init.js";
import {
  checkClaudePluginLoading,
  getInstalledPluginVersion,
  PLUGIN_PACKAGE,
  readCliVersion,
  type CommandRunner,
} from "./plugin.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

export interface DoctorOptions {
  strictPlugin?: boolean;
  fix?: boolean;
  skipPlugin?: boolean;
  runner?: CommandRunner;
}

interface Check {
  level: "OK" | "FAIL" | "WARN" | "INFO";
  message: string;
}

function existsCheck(path: string, label: string): Check {
  return fs.existsSync(path)
    ? { level: "OK", message: `${label} exists` }
    : { level: "FAIL", message: `${label} exists` };
}

function readJson(path: string): any | null {
  try {
    return JSON.parse(fs.readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function expectedAgentNames(): string[] {
  const agentsDir = join(kitRoot(__dirname), "agents");
  return fs.readdirSync(agentsDir).filter(f => f.endsWith(".md")).sort();
}

function checkCoreConfig(repo: string): Check[] {
  const checks: Check[] = [];
  checks.push(existsCheck(join(repo, ".research"), ".research/"));
  checks.push(existsCheck(join(repo, ".research/workflow.md"), "workflow.md"));
  checks.push(existsCheck(join(repo, ".research/config.yaml"), ".research/config.yaml"));
  checks.push(existsCheck(join(repo, ".claude/settings.json"), ".claude/settings.json"));

  const settings = readJson(join(repo, ".claude/settings.json"));
  const rcHook = Array.isArray(settings?.hooks?.UserPromptSubmit)
    && settings.hooks.UserPromptSubmit.some((group: any) =>
      (group?.hooks ?? []).some((hook: any) => typeof hook?.command === "string" && hook.command.includes("rc context")));
  checks.push(rcHook
    ? { level: "OK", message: "Claude UserPromptSubmit hook contains rc context" }
    : { level: "FAIL", message: "Claude UserPromptSubmit hook contains rc context" });

  const agentDir = join(repo, ".claude/agents");
  for (const agent of expectedAgentNames()) {
    checks.push(fs.existsSync(join(agentDir, agent))
      ? { level: "OK", message: `.claude/agents/${agent} exists` }
      : { level: "FAIL", message: `.claude/agents/${agent} exists` });
  }

  const mcp = readJson(join(repo, ".mcp.json"));
  for (const name of Object.keys(MCP_SERVERS)) {
    checks.push(mcp?.mcpServers?.[name]
      ? { level: "OK", message: `.mcp.json includes ${name}` }
      : { level: "FAIL", message: `.mcp.json includes ${name}` });
  }

  const claudeMd = fs.existsSync(join(repo, "CLAUDE.md")) ? fs.readFileSync(join(repo, "CLAUDE.md"), "utf8") : "";
  checks.push(claudeMd.includes("Research workflow is governed by .research/")
    ? { level: "OK", message: "CLAUDE.md contains Research Copilot workflow instruction" }
    : { level: "FAIL", message: "CLAUDE.md contains Research Copilot workflow instruction" });

  return checks;
}

function checkPlugin(options: DoctorOptions): Check[] {
  const checks: Check[] = [];
  if (options.skipPlugin) {
    checks.push({ level: "INFO", message: "Skipped plugin checks" });
    return checks;
  }

  const cliVersion = readCliVersion();
  const pluginVersion = getInstalledPluginVersion(options.runner);
  const failLevel = options.strictPlugin ? "FAIL" : "WARN";

  if (!pluginVersion) {
    checks.push({
      level: failLevel,
      message: `Plugin not installed (run: npm install -g ${PLUGIN_PACKAGE}@${cliVersion})`,
    });
  } else if (pluginVersion !== cliVersion) {
    checks.push({
      level: failLevel,
      message: `Plugin version mismatch (CLI: ${cliVersion}, Plugin: ${pluginVersion}). Run: npm install -g ${PLUGIN_PACKAGE}@${cliVersion}`,
    });
  } else {
    checks.push({ level: "OK", message: `Plugin version matches (${cliVersion})` });
  }

  const claude = checkClaudePluginLoading(options.runner);
  checks.push({ level: "INFO", message: claude.message });
  return checks;
}

export function runDoctor(repo: string, options: DoctorOptions = {}): { ok: boolean; report: string[] } {
  const report: string[] = [];

  if (options.fix) {
    runInit({
      repo,
      platforms: ["claude-code"],
      user: "doctor-fix",
      skipPlugin: options.skipPlugin,
      strictPlugin: options.strictPlugin,
      runner: options.runner,
    });
    report.push("Fixed: reconciled Research Copilot project configuration");
  }

  const checks = [...checkCoreConfig(repo), ...checkPlugin(options)];
  let ok = true;
  for (const check of checks) {
    report.push(`${check.level} ${check.message}`);
    if (check.level === "FAIL") ok = false;
  }

  return { ok, report };
}
```

- [ ] **Step 4: Confirm MCP server export**

No source change is needed for this step. `packages/adapters/src/index.ts` already exports `MCP_SERVERS` through:

```ts
export * from "./mcp.js";
```

Keep this step as a check so the implementer knows why Task 3 imports `MCP_SERVERS` from `@research-copilot/adapters`.

- [ ] **Step 5: Wire doctor CLI options**

Modify the `doctor` command block in `packages/cli/src/program.ts` to:

```ts
  program.command("doctor")
    .option("--fix", "Repair missing Research Copilot project configuration", false)
    .option("--skip-plugin", "Skip npm plugin checks/fixes that install packages", false)
    .option("--strict-plugin", "Treat plugin warnings as failures", false)
    .action((opts) => {
      const { ok, report } = runDoctor(repo, {
        fix: opts.fix,
        skipPlugin: opts.skipPlugin,
        strictPlugin: opts.strictPlugin,
      });
      process.stdout.write(report.join("\n") + "\n");
      process.exitCode = ok ? 0 : 1;
    });
```

- [ ] **Step 6: Run focused doctor tests and verify they pass**

Run:

```bash
pnpm vitest run packages/cli/test/doctor.test.ts
```

Expected: PASS.

- [ ] **Step 7: Run CLI error tests to ensure Commander behavior still passes**

Run:

```bash
pnpm vitest run packages/cli/test/errors.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/cli/src/commands/doctor.ts packages/cli/src/program.ts packages/cli/test/doctor.test.ts packages/adapters/src/index.ts
git commit -m "feat(cli): expand doctor checks and fix mode"
```

---

### Task 4: Add integration coverage for upgrade safety and command-line flags

**Files:**
- Modify: `packages/cli/test/init.test.ts`
- Modify: `packages/cli/test/doctor.test.ts`
- Modify: `packages/cli/test/errors.test.ts`

**Interfaces:**
- Consumes all public behavior from Tasks 1-3.
- Produces stronger regression coverage for old-version upgrades and CLI flag parsing.

- [ ] **Step 1: Add upgrade-safety regression tests**

Append these tests inside the `describe("rc init", ...)` block in `packages/cli/test/init.test.ts`:

```ts
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
```

- [ ] **Step 2: Add CLI flag parsing tests**

Append this import line to the import section in `packages/cli/test/errors.test.ts`:

```ts
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
```

Append these tests inside `describe("applyExitOverride (subcommand usage → exit 2)", ...)` in `packages/cli/test/errors.test.ts`:

```ts
  it("accepts init plugin flags", () => {
    const repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-cli-"));
    const program = buildProgram(repo);
    applyExitOverride(program);
    let caught: unknown;
    try {
      program.parse(["init", "--skip-plugin", "--strict-plugin", "--user", "tester"], { from: "user" });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeFalsy();
  });

  it("accepts doctor plugin and fix flags", () => {
    const repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-cli-"));
    const program = buildProgram(repo);
    applyExitOverride(program);
    let caught: unknown;
    try {
      program.parse(["doctor", "--fix", "--skip-plugin", "--strict-plugin"], { from: "user" });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeFalsy();
  });
```

These tests use a temporary repository and pass `--skip-plugin`, so they do not call npm and do not write to a fixed path.

- [ ] **Step 3: Run focused tests and verify failures before any fixes**

Run:

```bash
pnpm vitest run packages/cli/test/init.test.ts packages/cli/test/errors.test.ts
```

Expected: PASS after Tasks 1-3 are implemented. A failure here means the CLI option wiring or idempotent init behavior in earlier tasks needs correction before continuing.

- [ ] **Step 4: Run all CLI tests**

Run:

```bash
pnpm vitest run packages/cli/test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/test/init.test.ts packages/cli/test/doctor.test.ts packages/cli/test/errors.test.ts
git commit -m "test(cli): cover plugin upgrade safety"
```

---

### Task 5: Update user documentation and run full validation

**Files:**
- Modify: `INSTALLATION.md`
- Modify: `packages/plugin/README.md`

**Interfaces:**
- Consumes final CLI behavior from Tasks 1-4.
- Produces documented commands for new installs and old-version upgrades.

- [ ] **Step 1: Add installation and upgrade documentation**

In `INSTALLATION.md`, update the npm section to include this text near the existing `npm install -g` and `rc init` examples:

````md
### Plugin integration and upgrades

`rc init` is safe to run more than once. On a new project it initializes Research Copilot; on an older Research Copilot project it reconciles missing or outdated managed configuration while preserving existing tasks, specs, workspace files, user hooks, user agents, and unrelated MCP servers.

For a fresh install:

```bash
npm install -g @research-copilot/cli
rc init --user your-name --claude
rc doctor
```

For an existing project upgrading from an older version:

```bash
npm install -g @research-copilot/cli@latest
rc doctor
rc doctor --fix
rc doctor
```

When Claude Code support is enabled, `rc init` and `rc doctor --fix` synchronize the companion npm plugin package to the CLI version:

```bash
npm install -g @research-copilot/plugin@<cli-version>
```

The plugin synchronization is a packaging/version check. Research Copilot's project-local Claude Code configuration remains the reliable runtime path, so plugin install or Claude Code plugin-list warnings do not block normal initialization unless `--strict-plugin` is used.

Use `--skip-plugin` for offline or CI environments:

```bash
rc init --user your-name --claude --skip-plugin
rc doctor --skip-plugin
```

Use `--strict-plugin` when release validation should fail if the npm plugin is missing or out of sync:

```bash
rc doctor --strict-plugin
```
````

In `packages/plugin/README.md`, replace the current Installation and Manual Installation sections with this text:

````md
## Installation

Most users should install the Research Copilot CLI, then let `rc init` or `rc doctor --fix` synchronize this companion plugin package:

```bash
npm install -g @research-copilot/cli
rc init --user your-name --claude
rc doctor
```

For an existing Research Copilot project after upgrading the CLI:

```bash
npm install -g @research-copilot/cli@latest
rc doctor --fix
rc doctor
```

`rc init` and `rc doctor --fix` are idempotent: they preserve existing tasks, specs, workspace files, user hooks, user agents, and unrelated MCP servers.

## Manual Plugin Synchronization

If `rc doctor` reports a plugin version mismatch, install the exact version it prints:

```bash
npm install -g @research-copilot/plugin@<cli-version>
```

This npm package is a companion package for plugin content and version synchronization. Project-local Claude Code configuration created by `rc init` remains the reliable runtime path, so npm global installation alone is not the only Research Copilot activation step.
````

Keep the rest of the README unchanged.

- [ ] **Step 2: Run documentation grep for outdated unsafe wording**

Run:

```bash
rg "re-run init to install plugin|npm install -g @research-copilot/plugin.*Claude Code.*available|automatically installed when you run" INSTALLATION.md packages/plugin/README.md docs -n
```

Expected: Either no matches, or matches that now accurately explain that npm global install is synchronization/packaging and standalone config remains the runtime path. Fix any wording that implies npm global install alone loads the Claude Code plugin.

- [ ] **Step 3: Run full validation**

Run:

```bash
pnpm run ci
```

Expected: PASS for recursive build and Vitest suite.

- [ ] **Step 4: Inspect git status**

Run:

```bash
git status --short
```

Expected: only the intended documentation changes remain unstaged for this task before commit.

- [ ] **Step 5: Commit**

```bash
git add INSTALLATION.md packages/plugin/README.md
git commit -m "docs: document plugin upgrade workflow"
```

---

## Self-Review Notes

- Spec coverage:
  - Idempotent init/reconcile: Tasks 2 and 4.
  - Old-version upgrade path: Tasks 2, 3, and docs in Task 5.
  - npm plugin version sync: Task 1 and Task 2.
  - `rc doctor` sections, strict plugin mode, and `--fix`: Task 3.
  - `--skip-plugin`: Tasks 2 and 3.
  - Preserve user state and foreign config: Tasks 2 and 4.
  - Avoid requiring `claude plugin install`: Task 1 checks are informational; Task 5 documents runtime model.
- Placeholder scan: no open-ended placeholders are intended; both `INSTALLATION.md` and `packages/plugin/README.md` have concrete replacement text.
- Type consistency:
  - `CommandRunner`, `PluginSyncResult`, `ReconcileResult`, `InitResult`, and `DoctorOptions` are defined before later tasks consume them.
  - `runInit()` remains callable by existing tests, with extra optional fields only.
  - `runDoctor()` keeps its existing return shape while adding optional behavior.
