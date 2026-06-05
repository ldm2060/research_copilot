import * as fs from "node:fs";
import * as path from "node:path";

export function runDoctor(repo: string): { ok: boolean; report: string[] } {
  const report: string[] = [];
  let ok = true;
  const checks: [string, boolean][] = [
    [".research/ exists", fs.existsSync(path.join(repo, ".research"))],
    ["workflow.md exists", fs.existsSync(path.join(repo, ".research/workflow.md"))],
    [".claude/settings.json exists", fs.existsSync(path.join(repo, ".claude/settings.json"))],
  ];
  for (const [name, pass] of checks) {
    report.push(`${pass ? "OK " : "FAIL"} ${name}`);
    if (!pass) ok = false;
  }
  return { ok, report };
}
