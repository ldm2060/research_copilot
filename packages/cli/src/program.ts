import { Command } from "commander";
import { runContext } from "./commands/context.js";
import { runDoctor } from "./commands/doctor.js";
import { registerInit } from "./commands/init.js";
import { registerTask } from "./commands/task.js";
import { sync } from "./commands/sync.js";

export function buildProgram(repo = process.cwd()): Command {
  const program = new Command("rc");
  program.command("context")
    .option("--platform <p>", "platform", "claude-code")
    .option("--inject", "inject mode", false)
    .option("--format <f>", "text|json", "text")
    .option("--event <name>", "hook event name for json envelope")
    .action((opts) => {
      process.stdout.write(runContext({ repo, format: opts.format, now: new Date().toISOString(), eventName: opts.event }));
    });
  program.command("doctor").action(() => {
    const { ok, report } = runDoctor(repo);
    process.stdout.write(report.join("\n") + "\n");
    process.exitCode = ok ? 0 : 1;
  });
  registerInit(program, repo);
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
