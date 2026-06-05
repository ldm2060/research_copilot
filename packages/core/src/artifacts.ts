import * as fs from "node:fs";
import * as path from "node:path";
import { researchPaths } from "./paths.js";

export type Phase = "execute" | "verify";
export interface ContextRef { type: "spec" | "context"; path: string; reason: string; }
export interface VerifyRow { check: string; kind: string; args?: Record<string, unknown>; }

function dir(repo: string, id: string) { return researchPaths(repo).taskDir(id); }

export function readPrdGoal(repo: string, id: string): string | null {
  const p = path.join(dir(repo, id), "prd.md");
  if (!fs.existsSync(p)) return null;
  const md = fs.readFileSync(p, "utf8");
  const m = md.match(/##\s*Goal\s*\r?\n([\s\S]*?)(\r?\n\s*\r?\n|\r?\n##|$)/);
  return m ? m[1].trim() : null;
}

export function appendContext(
  repo: string, id: string, phase: Phase, row: ContextRef | VerifyRow,
): void {
  const p = path.join(dir(repo, id), `${phase}.jsonl`);
  fs.appendFileSync(p, JSON.stringify(row) + "\n", "utf8");
}

export function readContext(repo: string, id: string, phase: Phase): unknown[] {
  const p = path.join(dir(repo, id), `${phase}.jsonl`);
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, "utf8").split("\n").filter(Boolean).map(l => JSON.parse(l));
}
