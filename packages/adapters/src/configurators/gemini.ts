import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { kitRoot, deepMergeJson } from "../render.js";
import { parseAgent } from "../agent-frontmatter.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HOOK_CMD = "rc context --inject --format json --event BeforeAgent";

export function configureGemini(repo: string): void {
  const base = path.join(repo, ".gemini");
  fs.mkdirSync(path.join(base, "agents"), { recursive: true });
  const KIT = kitRoot(__dirname);

  const agentsSrc = path.join(KIT, "agents");
  for (const f of fs.readdirSync(agentsSrc).filter(x => x.endsWith(".md"))) {
    const a = parseAgent(fs.readFileSync(path.join(agentsSrc, f), "utf8"));
    const fm = ["---", `name: ${a.name}`, `description: ${JSON.stringify(a.description)}`];
    if (a.model) fm.push(`model: ${a.model}`);
    fm.push("---", "");
    fs.writeFileSync(path.join(base, "agents", a.name + ".md"), fm.join("\n") + a.body + "\n", "utf8");
  }

  const settingsPath = path.join(base, "settings.json");
  const existing = fs.existsSync(settingsPath) ? JSON.parse(fs.readFileSync(settingsPath, "utf8")) : {};
  const ups: any[] = existing?.hooks?.BeforeAgent ?? [];
  const already = Array.isArray(ups) && ups.some(g => (g?.hooks ?? []).some((h: any) => typeof h?.command === "string" && h.command.includes("rc context")));
  const ours = { hooks: { BeforeAgent: [{ matcher: "*", hooks: [{ type: "command", command: HOOK_CMD, timeout: 20 }] }] } };
  const merged = already ? existing : deepMergeJson(existing, ours);
  fs.writeFileSync(settingsPath, JSON.stringify(merged, null, 2) + "\n", "utf8");
}
