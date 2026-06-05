import * as fs from "node:fs";
import { researchPaths } from "./paths.js";

export function setActive(repo: string, id: string): void {
  const p = researchPaths(repo);
  fs.mkdirSync(p.runtime, { recursive: true });
  fs.writeFileSync(p.activeTask, id, "utf8");
}
export function getActive(repo: string): string | null {
  const p = researchPaths(repo).activeTask;
  return fs.existsSync(p) ? fs.readFileSync(p, "utf8").trim() || null : null;
}
