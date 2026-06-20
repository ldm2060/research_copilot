import { execSync, type ExecSyncOptions } from "node:child_process";
import * as fs from "node:fs";
import { dirname, join } from "node:path";
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
        : `Claude Code is available but does not list research-copilot plugin; standalone configuration can still work. ${CLAUDE_PLUGIN_REMEDIATION}`,
    };
  } catch {
    return {
      available: false,
      listed: false,
      message: `Claude Code plugin list unavailable; standalone configuration can still work. ${CLAUDE_PLUGIN_REMEDIATION}`,
    };
  }
}
