import { createTask, readTask, writeTask, setStatus, setActive, getActive,
  type Kind, type Status } from "@research-copilot/core";
import type { Command } from "commander";

export function taskCreate(repo: string, i: { title: string; kind: Kind; date: string; venue?: string; parent?: string }) {
  const t = createTask(repo, i);
  setActive(repo, t.id);
  return t;
}
export function taskSetStatus(repo: string, id: string, to: Status, now: string) {
  setStatus(repo, id, to, now);
}
export function taskAddGap(repo: string, id: string, desc: string, suggest_kind: Kind) {
  const t = readTask(repo, id);
  t.gaps.push({ desc, suggest_kind, status: "open" });
  writeTask(repo, t, new Date().toISOString());
}
export function taskCurrent(repo: string) { return getActive(repo); }

export function registerTask(program: Command, repo: string): void {
  const today = () => new Date().toISOString().slice(0, 10);
  const task = program.command("task");
  task.command("create").requiredOption("--kind <k>").requiredOption("--title <t>")
    .option("--venue <v>").option("--parent <p>")
    .action(o => { const t = taskCreate(repo, { title: o.title, kind: o.kind, date: today(), venue: o.venue, parent: o.parent }); process.stdout.write(t.id + "\n"); });
  for (const [cmd, to] of [["start","in_progress"],["verify","verify"],["complete","completed"]] as const)
    task.command(cmd).argument("<id>").action(id => taskSetStatus(repo, id, to as Status, new Date().toISOString()));
  task.command("set-status").argument("<id>").argument("<state>")
    .action((id, state) => taskSetStatus(repo, id, state as Status, new Date().toISOString()));
  task.command("add-gap").argument("<id>").requiredOption("--desc <d>").requiredOption("--suggest <k>")
    .action((id, o) => taskAddGap(repo, id, o.desc, o.suggest));
  task.command("current").action(() => process.stdout.write((taskCurrent(repo) ?? "none") + "\n"));
}
