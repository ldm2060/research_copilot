import { Command } from "commander";
import { runContext } from "./commands/context.js";
import { runDoctor } from "./commands/doctor.js";
import { registerInit } from "./commands/init.js";
import { registerTask } from "./commands/task.js";

export function buildProgram(repo = process.cwd()): Command {
  const program = new Command("rc");
  program.command("context")
    .option("--platform <p>", "platform", "claude-code")
    .option("--inject", "inject mode", false)
    .option("--format <f>", "text|json", "text")
    .action((opts) => {
      process.stdout.write(runContext({ repo, format: opts.format, now: new Date().toISOString() }));
    });
  program.command("doctor").action(() => {
    const { ok, report } = runDoctor(repo);
    process.stdout.write(report.join("\n") + "\n");
    process.exitCode = ok ? 0 : 1;
  });
  registerInit(program, repo);
  registerTask(program, repo);
  return program;
}
