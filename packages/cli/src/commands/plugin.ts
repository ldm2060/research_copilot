import { execSync, type ExecSyncOptions } from "node:child_process";
import * as fs from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const PLUGIN_PACKAGE = "@research-copilot/plugin";

const CLAUDE_PLUGIN_REMEDIATION = "To register the npm plugin, run: rc plugin install --platform claude --scope project";

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

export interface ClaudePluginEntry {
  enabled: boolean;
  version: string | null;
  projectPath?: string;
  scope?: string;
}

export interface ClaudePluginStatus extends ClaudePluginEntry {
  available: boolean;
  listed: boolean;
  message: string;
}

export interface CheckClaudePluginLoadingOptions {
  /** Absolute repo path; used to prefer a project-scoped entry bound to this repo. */
  repo?: string;
  /** CLI/plugin version to surface drift in the message (WARN-level comparison happens in doctor). */
  expectedVersion?: string;
}

const CLAUDE_PLUGIN_ID = "research-copilot@research-copilot";

function isResearchCopilotEntry(obj: unknown): obj is Record<string, unknown> {
  if (!obj || typeof obj !== "object") return false;
  const o = obj as Record<string, unknown>;
  const id = typeof o.id === "string" ? o.id : null;
  const name = typeof o.name === "string" ? o.name : null;
  const marketplace = typeof o.marketplace === "string" ? o.marketplace : null;
  if (id === CLAUDE_PLUGIN_ID) return true;
  // Match "<plugin>@<marketplace>" where either side is research-copilot, or a bare
  // name under the research-copilot marketplace.
  if (id && /research-copilot(@research-copilot)?$/i.test(id)) return true;
  if (name === "research-copilot" && (marketplace === "research-copilot" || id === "research-copilot")) return true;
  return false;
}

function collectEntries(node: unknown, acc: ClaudePluginEntry[] = []): ClaudePluginEntry[] {
  if (Array.isArray(node)) {
    for (const item of node) collectEntries(item, acc);
    return acc;
  }
  if (node && typeof node === "object") {
    if (isResearchCopilotEntry(node)) {
      const o = node as Record<string, any>;
      acc.push({
        enabled: o.enabled === true,
        version: typeof o.version === "string" ? o.version : null,
        projectPath: typeof o.projectPath === "string" ? o.projectPath : undefined,
        scope: typeof o.scope === "string" ? o.scope : undefined,
      });
    }
    for (const v of Object.values(node)) collectEntries(v, acc);
  }
  return acc;
}

function pickEntry(entries: ClaudePluginEntry[], repo?: string): ClaudePluginEntry | null {
  if (entries.length === 0) return null;
  if (!repo) return entries[0];
  const match = entries.find(e => e.projectPath && samePath(repo, e.projectPath));
  return match ?? entries[0];
}

function samePath(a: string, b: string): boolean {
  const norm = (p: string) => resolve(p).toLowerCase().replace(/\\/g, "/").replace(/\/+$/, "");
  return norm(a) === norm(b) && norm(a) !== "";
}

export function checkClaudePluginLoading(
  runner: CommandRunner = defaultCommandRunner,
  opts: CheckClaudePluginLoadingOptions = {},
): ClaudePluginStatus {
  let raw: string;
  try {
    raw = runner.exec("claude plugin list --json", { timeout: 5000 });
  } catch {
    return {
      available: false,
      listed: false,
      enabled: false,
      version: null,
      message: `Claude Code plugin list unavailable; standalone configuration can still work. ${CLAUDE_PLUGIN_REMEDIATION}`,
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return {
      available: false,
      listed: false,
      enabled: false,
      version: null,
      message: `Claude Code plugin list returned non-JSON output; standalone configuration can still work. ${CLAUDE_PLUGIN_REMEDIATION}`,
    };
  }

  const entries = collectEntries(parsed);
  const entry = pickEntry(entries, opts.repo);
  if (!entry) {
    return {
      available: true,
      listed: false,
      enabled: false,
      version: null,
      message: `Claude Code is available but does not list research-copilot plugin; standalone configuration can still work. ${CLAUDE_PLUGIN_REMEDIATION}`,
    };
  }

  const ver = entry.version ?? "unknown";
  const scope = entry.scope ?? "unknown";
  const project = entry.projectPath ? ` (bound to ${entry.projectPath})` : "";
  if (!entry.enabled) {
    return {
      available: true,
      listed: true,
      enabled: false,
      version: entry.version,
      projectPath: entry.projectPath,
      scope: entry.scope,
      message: `Claude Code research-copilot plugin is DISABLED (v${ver}, scope ${scope}${project}). Skills will not load. Enable it: claude plugin enable ${CLAUDE_PLUGIN_ID}`,
    };
  }

  if (opts.expectedVersion && entry.version && entry.version !== opts.expectedVersion) {
    return {
      available: true,
      listed: true,
      enabled: true,
      version: entry.version,
      projectPath: entry.projectPath,
      scope: entry.scope,
      message: `Claude Code research-copilot plugin enabled but stale (v${ver}, expected v${opts.expectedVersion}${project}). Re-add from the marketplace at the new tag.`,
    };
  }

  return {
    available: true,
    listed: true,
    enabled: true,
    version: entry.version,
    projectPath: entry.projectPath,
    scope: entry.scope,
    message: `Claude Code research-copilot plugin enabled (v${ver}${project})`,
  };
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
