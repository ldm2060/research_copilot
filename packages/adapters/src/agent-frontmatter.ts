export interface ParsedAgent { name: string; description: string; kind?: string; model?: string; body: string; }
export function parseAgent(md: string): ParsedAgent {
  const m = md.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  const fm = m ? m[1] : ""; const body = (m ? m[2] : md).trim();
  const get = (k: string) => {
    const line = fm.split(/\r?\n/).find(l => l.trim().toLowerCase().startsWith(k + ":"));
    if (!line) return undefined;
    let v = line.slice(line.indexOf(":") + 1).trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    return v;
  };
  return { name: get("name") ?? "", description: get("description") ?? "", kind: get("kind"), model: get("model"), body };
}
