import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { researchPaths } from "@research-copilot/core";
import { configureClaudeCode, kitRoot } from "@research-copilot/adapters";
import type { Command } from "commander";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export interface InitArgs { repo: string; platforms: string[]; user: string; }

export function runInit(args: InitArgs): void {
  const p = researchPaths(args.repo);
  for (const d of [p.tasks, p.spec, p.workspace, p.runtime]) fs.mkdirSync(d, { recursive: true });
  for (const s of ["venue", "writing", "baselines", "methodology", "novelty"])
    fs.mkdirSync(path.join(p.spec, s), { recursive: true });
  const KIT = kitRoot(__dirname);
  fs.copyFileSync(path.join(KIT, "workflow.md"), p.workflow);
  fs.copyFileSync(path.join(KIT, "config.defaults.yaml"), p.config);
  if (args.platforms.includes("claude-code")) configureClaudeCode(args.repo);
}

export function registerInit(program: Command, repo: string): void {
  program.command("init")
    .option("--claude", "Claude Code", false)
    .requiredOption("-u, --user <name>", "developer identity")
    .action((opts) => {
      const platforms = ["claude-code"];
      runInit({ repo, platforms, user: opts.user });
      process.stdout.write(`Initialized .research/ for: ${platforms.join(", ")}\n`);
    });
}
