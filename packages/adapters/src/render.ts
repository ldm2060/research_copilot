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
