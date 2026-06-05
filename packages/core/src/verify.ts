export interface CheckResult { ok: boolean; missing: string[]; }

const NUMBER_RE = /-?\d+(?:\.\d+)?/g;
const norm = (s: string) => s.replace(/^(-?)0+(\d)/, "$1$2"); // strip leading zeros

export function numberTraceability(draft: string, artifactsText: string): CheckResult {
  const present = new Set((artifactsText.match(NUMBER_RE) ?? []).map(norm));
  const missing: string[] = [];
  for (const tok of draft.match(NUMBER_RE) ?? []) {
    if (!present.has(norm(tok)) && !missing.includes(tok)) missing.push(tok);
  }
  return { ok: missing.length === 0, missing };
}

export function citationCompliance(tex: string, bibtex: string): CheckResult {
  const keys = new Set<string>();
  for (const m of bibtex.matchAll(/@\w+\s*\{\s*([^,\s}]+)/g)) keys.add(m[1]);
  const missing: string[] = [];
  for (const m of tex.matchAll(/\\cite[a-zA-Z]*(?:\[[^\]]*\])*\{([^}]*)\}/g)) {
    for (const key of m[1].split(",").map(k => k.trim()).filter(Boolean)) {
      if (!keys.has(key) && !missing.includes(key)) missing.push(key);
    }
  }
  return { ok: missing.length === 0, missing };
}
