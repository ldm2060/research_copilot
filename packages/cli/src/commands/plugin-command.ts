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
