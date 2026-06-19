# Platform Plugin Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `rc plugin install/status/update/remove` so `@research-copilot/plugin` can be registered into Claude Code, Codex, Gemini, Cursor, OpenCode, and Windsurf discovery paths.

**Architecture:** Add a focused registration module that resolves plugin source content, resolves platform targets from `AI_TOOLS`, and performs idempotent install/status/remove operations. Add a thin Commander command module for `rc plugin`, then wire `rc init --install-plugin` and `rc doctor` remediation through the same helper layer.

**Tech Stack:** TypeScript ESM, Commander, Vitest, Node built-ins (`fs`, `path`, `os`), existing `@research-copilot/adapters` registry, existing `packages/cli/src/commands/plugin.ts` npm sync helpers.

## Global Constraints

- Provide a clear command that connects `@research-copilot/plugin` to supported platform discovery paths.
- Keep npm package synchronization and platform registration as separate concepts.
- Support Claude Code first, then Codex, Gemini, Cursor, OpenCode, and Windsurf through the existing platform registry.
- Make registration idempotent: re-running the command updates Research Copilot-managed plugin content without duplicating entries or deleting unrelated user content.
- Support both project-local registration and user-global registration where a platform supports both.
- Give `rc doctor` a precise remediation command when a platform does not list or discover the plugin.
- Do not remove the existing standalone configuration path created by `rc init`.
- Do not require Claude Code marketplace setup for normal Research Copilot use.
- Do not make `npm install -g @research-copilot/plugin` imply platform discovery.
- Do not overwrite unrelated platform plugins, user agents, user skills, rules, hooks, or MCP entries.
- Do not add `rc upgrade`; `rc doctor --fix` remains the explicit old-project repair path.
- `rc plugin install` defaults to `--platform claude --scope project --source npm`.
- `claude` maps to registry id `claude-code`.
- `all` means every platform in `AI_TOOLS`.
- `configured` means platforms with existing project config directories in the current repo: `.claude/`, `.codex/`, `.gemini/`, `.cursor/`, `.opencode/`, or `.windsurf/`.
- Registration copies plugin content; it does not symlink.
- Registration target directory name is always `research-copilot`.
- Claude Code project scope target is `<repo>/.claude/skills/research-copilot/`.
- Claude Code user scope target is `~/.claude/skills/research-copilot/`.
- Codex project scope target is `<repo>/.agents/skills/research-copilot/`.
- Gemini project scope targets are `<repo>/.gemini/skills/research-copilot/` and `<repo>/.agents/skills/research-copilot/`.
- Cursor project scope target is `<repo>/.cursor/skills/research-copilot/`.
- OpenCode project scope target is `<repo>/.opencode/skills/research-copilot/`.
- Windsurf project scope target is `<repo>/.windsurf/workflows/research-copilot/`.

---

## File Structure

- Create `packages/cli/src/commands/plugin-register.ts`  
  Source resolution, platform alias expansion, target resolution, install/status/remove operations, and structured result types.

- Create `packages/cli/src/commands/plugin-command.ts`  
  Commander wiring for `rc plugin install`, `rc plugin status`, `rc plugin update`, and `rc plugin remove`.

- Modify `packages/cli/src/program.ts`  
  Register the new `plugin` command group.

- Modify `packages/cli/src/commands/init.ts`  
  Add `--install-plugin` and call registration after existing standalone init/npm sync.

- Modify `packages/cli/src/commands/doctor.ts`  
  Replace vague Claude Code plugin-list INFO with remediation that points to `rc plugin install --platform claude --scope project`.

- Create `packages/cli/test/plugin-register.test.ts`  
  Unit tests for platform/source/target resolution and install/status/remove safety.

- Create `packages/cli/test/plugin-command.test.ts`  
  CLI-level tests for `rc plugin` command behavior using local fake plugin dist directories.

- Modify `packages/cli/test/init.test.ts`  
  Cover `rc init --install-plugin` programmatic behavior.

- Modify `packages/cli/test/doctor.test.ts`  
  Cover updated remediation text.

- Modify `packages/cli/test/errors.test.ts`  
  Cover Commander parsing for new `plugin` subcommands.

- Modify `INSTALLATION.md` and `packages/plugin/README.md`  
  Document `rc plugin install/status/update/remove` and when to use them.

---

### Task 1: Add registration core helpers

**Files:**
- Create: `packages/cli/src/commands/plugin-register.ts`
- Create: `packages/cli/test/plugin-register.test.ts`

**Interfaces:**
- Consumes:
  - `AI_TOOLS` from `@research-copilot/adapters`
  - `CommandRunner`, `PLUGIN_PACKAGE`, `readCliVersion`, `syncPluginPackage` from `./plugin.js`
- Produces:
  - `PluginPlatformInput = "claude" | "claude-code" | "codex" | "gemini" | "cursor" | "opencode" | "windsurf" | "all" | "configured"`
  - `PluginScope = "project" | "user"`
  - `PluginSource = "npm" | "local"`
  - `PluginOperationStatus = "ok" | "missing" | "installed" | "updated" | "removed" | "skipped" | "failed"`
  - `PluginRegistrationOptions`
  - `PluginRegistrationResult`
  - `normalizePluginPlatform(input: string): string`
  - `expandPluginPlatforms(repo: string, input: string): string[]`
  - `resolvePluginSource(options: PluginRegistrationOptions): string`
  - `resolvePlatformTargets(options: PluginRegistrationOptions & { platform: string }): string[]`
  - `installPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[]`
  - `statusPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[]`
  - `removePluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[]`

- [ ] **Step 1: Write failing unit tests for platform and source resolution**

Create `packages/cli/test/plugin-register.test.ts` with this initial content:

```ts
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
import type { CommandRunner } from "../src/commands/plugin.js";

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
    exec(command: string): string {
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pnpm vitest run packages/cli/test/plugin-register.test.ts
```

Expected: FAIL with `Failed to load url ../src/commands/plugin-register.js`.

- [ ] **Step 3: Implement platform and source resolution helpers**

Create `packages/cli/src/commands/plugin-register.ts` with this content:

```ts
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { AI_TOOLS } from "@research-copilot/adapters";
import {
  PLUGIN_PACKAGE,
  readCliVersion,
  syncPluginPackage,
  type CommandRunner,
} from "./plugin.js";

export type PluginPlatformInput = "claude" | "claude-code" | "codex" | "gemini" | "cursor" | "opencode" | "windsurf" | "all" | "configured";
export type PluginScope = "project" | "user";
export type PluginSource = "npm" | "local";
export type PluginOperationStatus = "ok" | "missing" | "installed" | "updated" | "removed" | "skipped" | "failed";

export interface PluginRegistrationOptions {
  repo: string;
  platform: string;
  scope: PluginScope;
  source: PluginSource;
  sourcePath?: string;
  homeDir?: string;
  runner?: CommandRunner;
  cliVersion?: string;
}

export interface PluginRegistrationResult {
  platform: string;
  scope: PluginScope;
  target: string;
  status: PluginOperationStatus;
  message: string;
}

const VALID_PLATFORM_INPUTS = ["claude", "claude-code", "codex", "gemini", "cursor", "opencode", "windsurf", "all", "configured"];
const PLATFORM_ORDER = Object.keys(AI_TOOLS);
const RC_METADATA_FILES = [
  [".claude-plugin", "plugin.json"],
  [".codex-plugin", "plugin.toml"],
  [".gemini-plugin", "plugin.json"],
  [".cursor-plugin", "plugin.json"],
  [".opencode-plugin", "plugin.json"],
  [".windsurf-plugin", "plugin.json"],
];

export function normalizePluginPlatform(input: string): string {
  if (input === "claude") return "claude-code";
  if (input in AI_TOOLS) return input;
  throw new Error(`unknown platform: ${input}. Valid platforms: ${VALID_PLATFORM_INPUTS.join(", ")}`);
}

export function expandPluginPlatforms(repo: string, input: string): string[] {
  if (input === "all") return [...PLATFORM_ORDER];
  if (input === "configured") {
    const configured = PLATFORM_ORDER.filter(id => fs.existsSync(path.join(repo, AI_TOOLS[id].configDir)));
    return configured.length > 0 ? configured : ["claude-code"];
  }
  return [normalizePluginPlatform(input)];
}

function hasResearchCopilotMetadata(dir: string): boolean {
  return RC_METADATA_FILES.some(parts => {
    const file = path.join(dir, ...parts);
    if (!fs.existsSync(file)) return false;
    return fs.readFileSync(file, "utf8").includes("research-copilot");
  });
}

function hasPluginContentDir(dir: string): boolean {
  return ["skills", "agents", "hooks"].some(name => fs.existsSync(path.join(dir, name)));
}

function validatePluginDist(dir: string): void {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    throw new Error(`plugin source does not exist: ${dir}`);
  }
  if (!hasResearchCopilotMetadata(dir) || !hasPluginContentDir(dir)) {
    throw new Error(`${dir} does not look like @research-copilot/plugin dist`);
  }
}

export function resolvePluginSource(options: PluginRegistrationOptions): string {
  if (options.source === "local") {
    if (!options.sourcePath) throw new Error("--path is required when --source local is used");
    const resolved = path.resolve(options.repo, options.sourcePath);
    validatePluginDist(resolved);
    return resolved;
  }

  const version = options.cliVersion ?? readCliVersion();
  const sync = syncPluginPackage({
    version,
    skip: false,
    strict: true,
    runner: options.runner,
  });
  if (sync.status === "warning") throw new Error(sync.message);
  const npmRoot = (options.runner?.exec("npm root -g", { timeout: 5000 }) ?? "").trim();
  if (!npmRoot) throw new Error(`Unable to resolve npm global root. Run: npm install -g ${PLUGIN_PACKAGE}@${version}`);
  const dist = path.join(npmRoot, "@research-copilot", "plugin", "dist");
  validatePluginDist(dist);
  return dist;
}

function projectTargetRoots(repo: string, platform: string): string[] {
  const entry = AI_TOOLS[platform];
  if (!entry) throw new Error(`unknown platform: ${platform}`);
  return entry.skillsPaths.map(rel => path.join(repo, rel));
}

export function resolvePlatformTargets(options: PluginRegistrationOptions & { platform: string }): string[] {
  const platform = normalizePluginPlatform(options.platform);
  if (options.scope === "user") {
    if (platform !== "claude-code") {
      throw new Error(`user scope is only supported for claude. ${platform} supports project scope only.`);
    }
    return [path.join(options.homeDir ?? os.homedir(), ".claude", "skills", "research-copilot")];
  }
  return projectTargetRoots(options.repo, platform).map(root => path.join(root, "research-copilot"));
}

export function installPluginRegistration(_options: PluginRegistrationOptions): PluginRegistrationResult[] {
  throw new Error("installPluginRegistration is implemented in Task 2");
}

export function statusPluginRegistration(_options: PluginRegistrationOptions): PluginRegistrationResult[] {
  throw new Error("statusPluginRegistration is implemented in Task 2");
}

export function removePluginRegistration(_options: PluginRegistrationOptions): PluginRegistrationResult[] {
  throw new Error("removePluginRegistration is implemented in Task 2");
}
```

- [ ] **Step 4: Run focused test and verify resolution tests pass while operation tests are absent**

Run:

```bash
pnpm vitest run packages/cli/test/plugin-register.test.ts
```

Expected: PASS with 8 tests.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/plugin-register.ts packages/cli/test/plugin-register.test.ts
git commit -m "feat(cli): add plugin registration resolution"
```

---

### Task 2: Implement install, status, and remove operations

**Files:**
- Modify: `packages/cli/src/commands/plugin-register.ts`
- Modify: `packages/cli/test/plugin-register.test.ts`

**Interfaces:**
- Consumes Task 1 helpers.
- Produces working implementations for:
  - `installPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[]`
  - `statusPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[]`
  - `removePluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[]`

- [ ] **Step 1: Append failing operation tests**

Append these tests inside `describe("plugin registration helpers", ...)` in `packages/cli/test/plugin-register.test.ts`:

```ts
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
```

- [ ] **Step 2: Run focused test and verify failures**

Run:

```bash
pnpm vitest run packages/cli/test/plugin-register.test.ts
```

Expected: FAIL on operation helpers because they throw `implemented in Task 2`.

- [ ] **Step 3: Replace operation helper stubs with implementations**

In `packages/cli/src/commands/plugin-register.ts`, replace the three stub functions with this code and add the helper functions immediately above them:

```ts
function relativeToRepo(repo: string, target: string): string {
  const rel = path.relative(repo, target);
  return rel && !rel.startsWith("..") ? rel.replace(/\\/g, "/") : target;
}

function copyDir(src: string, dst: string): void {
  fs.cpSync(src, dst, { recursive: true });
}

function safeExistingTarget(target: string): "missing" | "research-copilot" | "foreign" {
  if (!fs.existsSync(target)) return "missing";
  return hasResearchCopilotMetadata(target) ? "research-copilot" : "foreign";
}

function resultsForTargets(options: PluginRegistrationOptions): Array<{ platform: string; target: string }> {
  return expandPluginPlatforms(options.repo, options.platform).flatMap(platform =>
    resolvePlatformTargets({ ...options, platform }).map(target => ({ platform, target })),
  );
}

export function installPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[] {
  const source = resolvePluginSource(options);
  const results: PluginRegistrationResult[] = [];

  for (const item of resultsForTargets(options)) {
    const existing = safeExistingTarget(item.target);
    if (existing === "foreign") {
      results.push({
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "failed",
        message: `refusing to overwrite non-Research-Copilot directory: ${relativeToRepo(options.repo, item.target)}`,
      });
      continue;
    }

    fs.mkdirSync(path.dirname(item.target), { recursive: true });
    if (existing === "research-copilot") fs.rmSync(item.target, { recursive: true, force: true });
    copyDir(source, item.target);
    results.push({
      platform: item.platform,
      scope: options.scope,
      target: item.target,
      status: existing === "research-copilot" ? "updated" : "installed",
      message: `${existing === "research-copilot" ? "Updated" : "Installed"} research-copilot plugin at ${relativeToRepo(options.repo, item.target)}`,
    });
  }

  return results;
}

export function statusPluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[] {
  return resultsForTargets(options).map(item => {
    const existing = safeExistingTarget(item.target);
    if (existing === "research-copilot") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "ok",
        message: `project plugin: OK ${relativeToRepo(options.repo, item.target)}`,
      };
    }
    if (existing === "foreign") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "failed",
        message: `project plugin: BLOCKED ${relativeToRepo(options.repo, item.target)} is not Research Copilot-managed`,
      };
    }
    return {
      platform: item.platform,
      scope: options.scope,
      target: item.target,
      status: "missing",
      message: `project plugin: MISSING ${relativeToRepo(options.repo, item.target)}`,
    };
  });
}

export function removePluginRegistration(options: PluginRegistrationOptions): PluginRegistrationResult[] {
  return resultsForTargets(options).map(item => {
    const existing = safeExistingTarget(item.target);
    if (existing === "missing") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "missing",
        message: `No research-copilot plugin registration at ${relativeToRepo(options.repo, item.target)}`,
      };
    }
    if (existing === "foreign") {
      return {
        platform: item.platform,
        scope: options.scope,
        target: item.target,
        status: "failed",
        message: `refusing to remove non-Research-Copilot directory: ${relativeToRepo(options.repo, item.target)}`,
      };
    }
    fs.rmSync(item.target, { recursive: true, force: true });
    return {
      platform: item.platform,
      scope: options.scope,
      target: item.target,
      status: "removed",
      message: `Removed research-copilot plugin registration at ${relativeToRepo(options.repo, item.target)}`,
    };
  });
}
```

- [ ] **Step 4: Run focused test and verify all registration helper tests pass**

Run:

```bash
pnpm vitest run packages/cli/test/plugin-register.test.ts
```

Expected: PASS with 18 tests.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/plugin-register.ts packages/cli/test/plugin-register.test.ts
git commit -m "feat(cli): install platform plugin content"
```

---

### Task 3: Add `rc plugin` Commander command group

**Files:**
- Create: `packages/cli/src/commands/plugin-command.ts`
- Modify: `packages/cli/src/program.ts`
- Create: `packages/cli/test/plugin-command.test.ts`
- Modify: `packages/cli/test/errors.test.ts`

**Interfaces:**
- Consumes Task 2 operation helpers.
- Produces:
  - `PluginCommandOptions`
  - `runPluginCommand(action: "install" | "status" | "update" | "remove", repo: string, options: PluginCommandOptions): { ok: boolean; report: string[] }`
  - `registerPluginCommand(program: Command, repo: string): void`

- [ ] **Step 1: Write failing command tests**

Create `packages/cli/test/plugin-command.test.ts` with this content:

```ts
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
```

Append this test inside `describe("applyExitOverride (subcommand usage → exit 2)", ...)` in `packages/cli/test/errors.test.ts`:

```ts
  it("accepts plugin subcommands and options", () => {
    const repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-cli-"));
    const dist = path.join(repo, "dist");
    fs.mkdirSync(path.join(dist, ".claude-plugin"), { recursive: true });
    fs.mkdirSync(path.join(dist, "skills"), { recursive: true });
    fs.writeFileSync(path.join(dist, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "research-copilot" }));
    const program = buildProgram(repo);
    applyExitOverride(program);
    let caught: unknown;
    try {
      program.parse(["plugin", "install", "--platform", "claude", "--scope", "project", "--source", "local", "--path", dist], { from: "user" });
      program.parse(["plugin", "status", "--platform", "claude"], { from: "user" });
      program.parse(["plugin", "remove", "--platform", "claude"], { from: "user" });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeFalsy();
  });
```

- [ ] **Step 2: Run focused command tests and verify failures**

Run:

```bash
pnpm vitest run packages/cli/test/plugin-command.test.ts packages/cli/test/errors.test.ts
```

Expected: FAIL because `plugin-command.js` does not exist and `program.ts` does not register `plugin`.

- [ ] **Step 3: Implement command module**

Create `packages/cli/src/commands/plugin-command.ts` with this content:

```ts
import type { Command } from "commander";
import {
  installPluginRegistration,
  removePluginRegistration,
  statusPluginRegistration,
  type PluginRegistrationOptions,
  type PluginRegistrationResult,
  type PluginScope,
  type PluginSource,
} from "./plugin-register.js";

export interface PluginCommandOptions {
  platform?: string;
  scope?: PluginScope;
  source?: PluginSource;
  path?: string;
}

function toRegistrationOptions(repo: string, options: PluginCommandOptions): PluginRegistrationOptions {
  return {
    repo,
    platform: options.platform ?? "claude",
    scope: options.scope ?? "project",
    source: options.source ?? "npm",
    sourcePath: options.path,
  };
}

function formatResults(results: PluginRegistrationResult[]): string[] {
  return results.map(result => `${result.platform} ${result.message}`);
}

function okForAction(action: "install" | "status" | "update" | "remove", results: PluginRegistrationResult[]): boolean {
  if (results.some(r => r.status === "failed")) return false;
  if (action === "status") return results.every(r => r.status === "ok");
  return true;
}

export function runPluginCommand(
  action: "install" | "status" | "update" | "remove",
  repo: string,
  options: PluginCommandOptions,
): { ok: boolean; report: string[] } {
  const registration = toRegistrationOptions(repo, options);
  const results = action === "remove"
    ? removePluginRegistration(registration)
    : action === "status"
      ? statusPluginRegistration(registration)
      : installPluginRegistration(registration);
  return {
    ok: okForAction(action, results),
    report: formatResults(results),
  };
}

function addSharedOptions(command: Command, includeSource: boolean): Command {
  command
    .option("--platform <platform>", "claude|codex|gemini|cursor|opencode|windsurf|all|configured", "claude")
    .option("--scope <scope>", "project|user", "project");
  if (includeSource) {
    command
      .option("--source <source>", "npm|local", "npm")
      .option("--path <dist>", "local plugin dist path");
  }
  return command;
}

export function registerPluginCommand(program: Command, repo: string): void {
  const plugin = program.command("plugin").description("Register Research Copilot plugin content with supported platforms");

  addSharedOptions(plugin.command("install"), true)
    .description("Install Research Copilot plugin content into platform discovery paths")
    .action((opts) => {
      const result = runPluginCommand("install", repo, opts);
      process.stdout.write(result.report.join("\n") + "\n");
      process.exitCode = result.ok ? 0 : 1;
    });

  addSharedOptions(plugin.command("status"), false)
    .description("Show Research Copilot platform plugin registration status")
    .action((opts) => {
      const result = runPluginCommand("status", repo, opts);
      process.stdout.write(result.report.join("\n") + "\n");
      process.exitCode = result.ok ? 0 : 1;
    });

  addSharedOptions(plugin.command("update"), true)
    .description("Update Research Copilot plugin content in platform discovery paths")
    .action((opts) => {
      const result = runPluginCommand("update", repo, opts);
      process.stdout.write(result.report.join("\n") + "\n");
      process.exitCode = result.ok ? 0 : 1;
    });

  addSharedOptions(plugin.command("remove"), false)
    .description("Remove Research Copilot plugin content from platform discovery paths")
    .action((opts) => {
      const result = runPluginCommand("remove", repo, opts);
      process.stdout.write(result.report.join("\n") + "\n");
      process.exitCode = result.ok ? 0 : 1;
    });
}
```

- [ ] **Step 4: Register command group in program.ts**

Add this import in `packages/cli/src/program.ts`:

```ts
import { registerPluginCommand } from "./commands/plugin-command.js";
```

Add this call after `registerInit(program, repo);`:

```ts
  registerPluginCommand(program, repo);
```

- [ ] **Step 5: Run focused command tests and verify they pass**

Run:

```bash
pnpm vitest run packages/cli/test/plugin-command.test.ts packages/cli/test/errors.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/cli/src/commands/plugin-command.ts packages/cli/src/program.ts packages/cli/test/plugin-command.test.ts packages/cli/test/errors.test.ts
git commit -m "feat(cli): add plugin registration commands"
```

---

### Task 4: Wire `rc init --install-plugin`

**Files:**
- Modify: `packages/cli/src/commands/init.ts`
- Modify: `packages/cli/test/init.test.ts`

**Interfaces:**
- Consumes `installPluginRegistration()` from Task 2.
- Produces:
  - `InitArgs.installPlugin?: boolean`
  - `InitResult.registration?: PluginRegistrationResult[]`
  - CLI option `--install-plugin`

- [ ] **Step 1: Add failing init tests**

Append this import to `packages/cli/test/init.test.ts`:

```ts
import type { PluginRegistrationResult } from "../src/commands/plugin-register.js";
```

Append these tests inside `describe("rc init", ...)`:

```ts
  it("registers plugin content when installPlugin is true", () => {
    const dist = path.join(repo, "dist");
    fs.mkdirSync(path.join(dist, ".claude-plugin"), { recursive: true });
    fs.mkdirSync(path.join(dist, "skills"), { recursive: true });
    fs.writeFileSync(path.join(dist, ".claude-plugin", "plugin.json"), JSON.stringify({ name: "research-copilot" }));
    const r = fakeRunner();

    const result = runInit({
      repo,
      platforms: ["claude-code"],
      user: "tester",
      skipPlugin: true,
      installPlugin: true,
      pluginSource: "local",
      pluginSourcePath: dist,
      runner: r,
    });

    expect((result.registration as PluginRegistrationResult[])[0].status).toBe("installed");
    expect(fs.existsSync(path.join(repo, ".claude", "skills", "research-copilot", ".claude-plugin", "plugin.json"))).toBe(true);
  });

  it("does not register plugin content unless installPlugin is true", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });

    expect(fs.existsSync(path.join(repo, ".claude", "skills", "research-copilot"))).toBe(false);
  });
```

- [ ] **Step 2: Run focused init tests and verify failures**

Run:

```bash
pnpm vitest run packages/cli/test/init.test.ts
```

Expected: FAIL because `installPlugin`, `pluginSource`, `pluginSourcePath`, and `registration` are not implemented.

- [ ] **Step 3: Update init interfaces and implementation**

Modify `packages/cli/src/commands/init.ts` imports to include:

```ts
import { installPluginRegistration, type PluginRegistrationResult, type PluginSource } from "./plugin-register.js";
```

Add fields to `InitArgs`:

```ts
  installPlugin?: boolean;
  pluginSource?: PluginSource;
  pluginSourcePath?: string;
```

Add field to `InitResult`:

```ts
  registration: PluginRegistrationResult[];
```

Modify `runInit()` after the existing plugin sync block:

```ts
  const registration = args.installPlugin
    ? installPluginRegistration({
      repo: args.repo,
      platform: args.platforms.length === 1 ? args.platforms[0] : "configured",
      scope: "project",
      source: args.pluginSource ?? "npm",
      sourcePath: args.pluginSourcePath,
      runner: args.runner,
    })
    : [];

  return { reconcile, plugin, registration };
```

Add CLI options in `registerInit()`:

```ts
    .option("--install-plugin", "Register plugin content into selected platform discovery paths", false)
    .option("--plugin-source <source>", "npm|local", "npm")
    .option("--plugin-path <dist>", "local plugin dist path")
```

Pass them into `runInit()`:

```ts
        installPlugin: opts.installPlugin,
        pluginSource: opts.pluginSource,
        pluginSourcePath: opts.pluginPath,
```

After printing plugin sync message, print registration messages:

```ts
      for (const registration of result.registration) {
        process.stdout.write(`${registration.platform} ${registration.message}\n`);
      }
```

- [ ] **Step 4: Run focused init tests and verify they pass**

Run:

```bash
pnpm vitest run packages/cli/test/init.test.ts
```

Expected: PASS.

- [ ] **Step 5: Run plugin command tests to ensure shared registration helpers still pass**

Run:

```bash
pnpm vitest run packages/cli/test/plugin-register.test.ts packages/cli/test/plugin-command.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/cli/src/commands/init.ts packages/cli/test/init.test.ts
git commit -m "feat(cli): register plugin during init"
```

---

### Task 5: Update doctor remediation text

**Files:**
- Modify: `packages/cli/src/commands/plugin.ts`
- Modify: `packages/cli/test/plugin.test.ts`
- Modify: `packages/cli/test/doctor.test.ts`

**Interfaces:**
- Consumes existing `checkClaudePluginLoading()` and doctor plugin checks.
- Produces explicit remediation text containing `rc plugin install --platform claude --scope project`.

- [ ] **Step 1: Update failing expectations first**

In `packages/cli/test/plugin.test.ts`, change the unavailable/list-missing assertions to expect remediation text.

Replace the `reports Claude Code plugin inspection as informational when claude is unavailable` expectation with:

```ts
    expect(checkClaudePluginLoading(r)).toEqual({
      available: false,
      listed: false,
      message: "Claude Code plugin list unavailable; standalone configuration can still work. To register the npm plugin, run: rc plugin install --platform claude --scope project",
    });
```

Add this test after the existing positive `claude plugin list` test:

```ts
  it("reports a registration remediation command when Claude Code does not list research-copilot", () => {
    const r = runner({ "claude plugin list": "other-plugin 0.0.1" });

    expect(checkClaudePluginLoading(r)).toEqual({
      available: true,
      listed: false,
      message: "Claude Code is available but does not list research-copilot plugin; standalone configuration can still work. To register the npm plugin, run: rc plugin install --platform claude --scope project",
    });
  });
```

In `packages/cli/test/doctor.test.ts`, append this test inside `describe("rc doctor", ...)`:

```ts
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
```

- [ ] **Step 2: Run focused tests and verify failures**

Run:

```bash
pnpm vitest run packages/cli/test/plugin.test.ts packages/cli/test/doctor.test.ts
```

Expected: FAIL because `checkClaudePluginLoading()` still returns the old message.

- [ ] **Step 3: Update plugin loading messages**

In `packages/cli/src/commands/plugin.ts`, add this constant near `PLUGIN_PACKAGE`:

```ts
const CLAUDE_PLUGIN_REMEDIATION = "To register the npm plugin, run: rc plugin install --platform claude --scope project";
```

Update `checkClaudePluginLoading()` messages to:

```ts
        ? "Claude Code lists research-copilot plugin"
        : `Claude Code is available but does not list research-copilot plugin; standalone configuration can still work. ${CLAUDE_PLUGIN_REMEDIATION}`,
```

and in the catch block:

```ts
      message: `Claude Code plugin list unavailable; standalone configuration can still work. ${CLAUDE_PLUGIN_REMEDIATION}`,
```

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
pnpm vitest run packages/cli/test/plugin.test.ts packages/cli/test/doctor.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/plugin.ts packages/cli/test/plugin.test.ts packages/cli/test/doctor.test.ts
git commit -m "fix(cli): point doctor to plugin registration"
```

---

### Task 6: Document `rc plugin` workflow and run full validation

**Files:**
- Modify: `INSTALLATION.md`
- Modify: `packages/plugin/README.md`
- Modify: `packages/cli/test/errors.test.ts`

**Interfaces:**
- Consumes all command behavior from Tasks 1-5.
- Produces user-facing docs for `rc plugin install/status/update/remove` and final CI evidence.

- [ ] **Step 1: Add command parsing coverage for init plugin flags**

Append this assertion to the existing `accepts init plugin flags` test in `packages/cli/test/errors.test.ts` by changing the parse call to include plugin registration flags:

```ts
      program.parse(["init", "--skip-plugin", "--strict-plugin", "--install-plugin", "--plugin-source", "local", "--plugin-path", repo, "--user", "tester"], { from: "user" });
```

- [ ] **Step 2: Run errors test and verify it passes**

Run:

```bash
pnpm vitest run packages/cli/test/errors.test.ts
```

Expected: PASS.

- [ ] **Step 3: Update INSTALLATION.md**

In `INSTALLATION.md`, add this section after the existing plugin integration and upgrades section:

```md
### Registering plugin content with CLI platforms

`rc init` configures the project-local standalone Research Copilot workflow. To also make the published plugin content discoverable through a platform plugin or skills directory, run `rc plugin install`.

For Claude Code project scope:

```bash
rc plugin install --platform claude --scope project
rc plugin status --platform claude
```

For every platform already configured in the repository:

```bash
rc plugin install --platform configured --scope project
rc plugin status --platform configured
```

For local plugin development:

```bash
pnpm --filter @research-copilot/plugin build
rc plugin install --platform claude --scope project --source local --path packages/plugin/dist
```

To update or remove registered plugin content:

```bash
rc plugin update --platform claude --scope project
rc plugin remove --platform claude --scope project
```

`rc plugin install` copies plugin content into the selected platform discovery path, such as `.claude/skills/research-copilot/` for Claude Code project scope. It refuses to overwrite an existing non-Research-Copilot directory.
```

- [ ] **Step 4: Update packages/plugin/README.md**

In `packages/plugin/README.md`, add this subsection after `## Manual Plugin Synchronization`:

```md
## Platform Registration

Installing this npm package synchronizes plugin content, but platform CLIs discover plugins through their own plugin or skills directories. Use the Research Copilot CLI to register the plugin content:

```bash
rc plugin install --platform claude --scope project
rc plugin status --platform claude
```

For local development against a built plugin dist:

```bash
pnpm --filter @research-copilot/plugin build
rc plugin install --platform claude --scope project --source local --path packages/plugin/dist
```

The registration command copies this package's `dist/` content into the selected platform discovery path and preserves unrelated plugins.
```

- [ ] **Step 5: Run documentation grep**

Run:

```bash
rg "automatically installed when you run|npm global installation alone|does not list research-copilot plugin; standalone configuration can still work$" INSTALLATION.md packages/plugin/README.md packages/cli/src/commands -n
```

Expected: No matches. If there is a match in `packages/cli/src/commands/plugin.ts`, update the string so it includes `rc plugin install --platform claude --scope project`.

- [ ] **Step 6: Run full validation**

Run:

```bash
pnpm run ci
```

Expected: PASS with all build steps and Vitest test files passing.

- [ ] **Step 7: Commit**

```bash
git add INSTALLATION.md packages/plugin/README.md packages/cli/test/errors.test.ts
git commit -m "docs: document platform plugin registration"
```

---

## Self-Review Notes

- Spec coverage:
  - `rc plugin install/status/update/remove`: Tasks 2 and 3.
  - Platform aliases `claude`, `all`, and `configured`: Task 1.
  - npm and local source resolution: Task 1.
  - Idempotent copy registration and foreign-target protection: Task 2.
  - Claude project/user targets and Gemini dual targets: Tasks 1 and 2.
  - `rc init --install-plugin`: Task 4.
  - `rc doctor` remediation command: Task 5.
  - Documentation and full validation: Task 6.
- Placeholder scan: no placeholder task remains; every code change step includes concrete code or exact replacement text.
- Type consistency:
  - `PluginRegistrationOptions`, `PluginRegistrationResult`, `PluginScope`, and `PluginSource` are introduced in Task 1 before later tasks import them.
  - `runPluginCommand()` and `registerPluginCommand()` are introduced in Task 3 before docs reference the command behavior.
  - `InitResult.registration` is introduced in Task 4 and used only after `PluginRegistrationResult` exists.
