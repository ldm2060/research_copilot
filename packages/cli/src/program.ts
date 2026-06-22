import { Command } from "commander";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { runContext } from "./commands/context.js";
import { runDoctor } from "./commands/doctor.js";
import { registerInit } from "./commands/init.js";
import { registerPluginCommand } from "./commands/plugin-command.js";
import { registerTask } from "./commands/task.js";
import { sync } from "./commands/sync.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

export function buildProgram(repo = process.cwd()): Command {
  // Read version from package.json
  const pkgPath = join(__dirname, "..", "package.json");
  const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));

  const program = new Command("rc");
  program.version(pkg.version, "-v, --version", "output the current version");
  program.command("context")
    .option("--platform <p>", "platform", "claude-code")
    .option("--inject", "inject mode", false)
    .option("--format <f>", "text|json", "text")
    .option("--event <name>", "hook event name for json envelope")
    .action((opts) => {
      process.stdout.write(runContext({
        repo,
        platform: opts.platform,
        format: opts.format,
        now: new Date().toISOString(),
        eventName: opts.event,
      }));
    });
  program.command("doctor")
    .option("--fix", "Repair missing Research Copilot project configuration", false)
    .option("--skip-plugin", "Skip npm plugin checks/fixes that install packages", false)
    .option("--strict-plugin", "Treat plugin warnings as failures", false)
    .option("--platform <p>", "platform", "claude-code")
    .action((opts) => {
      const { ok, report } = runDoctor(repo, {
        fix: opts.fix,
        skipPlugin: opts.skipPlugin,
        strictPlugin: opts.strictPlugin,
        platform: opts.platform,
      });
      process.stdout.write(report.join("\n") + "\n");
      process.exitCode = ok ? 0 : 1;
    });
  registerInit(program, repo);
  registerPluginCommand(program, repo);
  registerTask(program, repo);
  program.command("sync")
    .description("Fetch skillpacks and render agents/specs")
    .option("--repo <path>", "Repository root", repo)
    .option("--cache-dir <path>", "Cache directory for skillpacks")
    .option("--target-dir <path>", "Target directory for rendered files")
    .action((opts) => {
      sync({
        repo: opts.repo,
        cacheDir: opts.cacheDir,
        targetDir: opts.targetDir
      });
    });
  return program;
}
