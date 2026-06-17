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
