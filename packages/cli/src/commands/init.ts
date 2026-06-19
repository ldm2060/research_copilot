import type { Command } from "commander";
import { reconcileProject, type ReconcileResult } from "./reconcile.js";
import {
  readCliVersion,
  syncPluginPackage,
  type CommandRunner,
  type PluginSyncResult,
} from "./plugin.js";
import { installPluginRegistration, type PluginRegistrationResult, type PluginSource } from "./plugin-register.js";

export interface InitArgs {
  repo: string;
  platforms: string[];
  user: string;
  skipPlugin?: boolean;
  strictPlugin?: boolean;
  installPlugin?: boolean;
  pluginSource?: PluginSource;
  pluginSourcePath?: string;
  runner?: CommandRunner;
}

export interface InitResult {
  reconcile: ReconcileResult;
  plugin: PluginSyncResult | null;
  registration: PluginRegistrationResult[];
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
    .option("--install-plugin", "Register plugin content into selected platform discovery paths", false)
    .option("--plugin-source <source>", "npm|local", "npm")
    .option("--plugin-path <dist>", "local plugin dist path")
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
        installPlugin: opts.installPlugin,
        pluginSource: opts.pluginSource,
        pluginSourcePath: opts.pluginPath,
      });

      process.stdout.write(`Initialized .research/ for: ${platforms.join(", ")}\n`);
      if (result.plugin) process.stdout.write(`${result.plugin.message}\n`);
      for (const registration of result.registration) {
        process.stdout.write(`${registration.platform} ${registration.message}\n`);
      }
    });
}
