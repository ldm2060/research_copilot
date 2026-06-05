import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { researchPaths } from "@research-copilot/core";
import { configurePlatform, kitRoot } from "@research-copilot/adapters";
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
  for (const p of args.platforms) configurePlatform(args.repo, p);
}

export function registerInit(program: Command, repo: string): void {
  program.command("init")
    .option("--claude", "Claude Code", false)
    .option("--codex", "OpenAI Codex", false)
    .option("--opencode", "OpenCode", false)
    .option("--gemini", "Gemini CLI", false)
    .requiredOption("-u, --user <name>", "developer identity")
    .action((opts) => {
      const platforms: string[] = [];
      if (opts.claude) platforms.push("claude-code");
      if (opts.codex) platforms.push("codex");
      if (opts.opencode) platforms.push("opencode");
      if (opts.gemini) platforms.push("gemini");
      if (platforms.length === 0) platforms.push("claude-code"); // default
      runInit({ repo, platforms, user: opts.user });
      process.stdout.write(`Initialized .research/ for: ${platforms.join(", ")}\n`);
    });
}
