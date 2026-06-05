import * as fs from "node:fs";
import * as path from "node:path";

export function render(tpl: string, vars: Record<string, string>): string {
  return tpl.replace(/\{\{(\w+)\}\}/g, (_, k) => vars[k] ?? `{{${k}}}`);
}
export function deepMergeJson(base: any, add: any): any {
  if (Array.isArray(base) && Array.isArray(add)) return [...base, ...add];
  if (base && add && typeof base === "object" && typeof add === "object") {
    const out: any = { ...base };
    for (const k of Object.keys(add)) out[k] = deepMergeJson(base[k], add[k]);
    return out;
  }
  return add ?? base;
}

export function kitRoot(start: string): string {
  let dir = start;
  for (;;) {
    const cand = path.join(dir, "research-kit");
    if (fs.existsSync(cand)) return cand;
    const parent = path.dirname(dir);
    if (parent === dir) throw new Error("research-kit not found above " + start);
    dir = parent;
  }
}
