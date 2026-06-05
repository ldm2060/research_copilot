import * as fs from "node:fs";
import * as path from "node:path";
import { createTask, readTask, writeTask, setStatus, setActive, getActive,
  numberTraceability, researchPaths,
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

export function runVerifyGate(repo: string, id: string, now: string): { ok: boolean; missing: string[] } {
  const t = readTask(repo, id);
  const dir = path.join(researchPaths(repo).taskDir(id), "artifacts");
  const read = (glob: RegExp) => fs.existsSync(dir)
    ? fs.readdirSync(dir).filter(f => glob.test(f)).map(f => fs.readFileSync(path.join(dir, f), "utf8")).join("\n") : "";
  let result = { ok: true, missing: [] as string[] };
  if (t.kind === "writing") {
    const draft = read(/\.tex$/);
    const artifacts = read(/\.(log|txt|json|csv)$/);
    result = numberTraceability(draft, artifacts);
  }
  if (!result.ok && t.status === "verify") setStatus(repo, id, "in_progress", now); // rollback (guarded)
  return result;
}

export function registerTask(program: Command, repo: string): void {
  const today = () => new Date().toISOString().slice(0, 10);
  const task = program.command("task");
  task.command("create").requiredOption("--kind <k>").requiredOption("--title <t>")
    .option("--venue <v>").option("--parent <p>")
    .action(o => { const t = taskCreate(repo, { title: o.title, kind: o.kind, date: today(), venue: o.venue, parent: o.parent }); process.stdout.write(t.id + "\n"); });
  for (const [cmd, to] of [["start","in_progress"],["complete","completed"]] as const)
    task.command(cmd).argument("<id>").action(id => taskSetStatus(repo, id, to as Status, new Date().toISOString()));
  task.command("verify").argument("<id>").action(id => {
    const r = runVerifyGate(repo, id, new Date().toISOString());
    if (r.ok) process.stdout.write(`verify OK for ${id}\n`);
    else { process.stdout.write(`verify FAILED (untraceable: ${r.missing.join(", ")}); rolled back to in_progress\n`); process.exitCode = 1; }
  });
  task.command("set-status").argument("<id>").argument("<state>")
    .action((id, state) => taskSetStatus(repo, id, state as Status, new Date().toISOString()));
  task.command("add-gap").argument("<id>").requiredOption("--desc <d>").requiredOption("--suggest <k>")
    .action((id, o) => taskAddGap(repo, id, o.desc, o.suggest));
  task.command("current").action(() => process.stdout.write((taskCurrent(repo) ?? "none") + "\n"));
}
