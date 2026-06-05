import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { parse as parseToml, stringify as toToml } from "smol-toml";
import { kitRoot } from "../render.js";
import { parseAgent } from "../agent-frontmatter.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HOOK_CMD = "rc context --inject --format text";

export function configureCodex(repo: string): void {
  const base = path.join(repo, ".codex");
  fs.mkdirSync(path.join(base, "agents"), { recursive: true });
  const KIT = kitRoot(__dirname);

  // agents -> flat TOML
  const agentsSrc = path.join(KIT, "agents");
  for (const f of fs.readdirSync(agentsSrc).filter(x => x.endsWith(".md"))) {
    const a = parseAgent(fs.readFileSync(path.join(agentsSrc, f), "utf8"));
    const obj: Record<string, unknown> = { name: a.name, description: a.description, developer_instructions: a.body };
    if (a.model) obj.model = a.model;
    fs.writeFileSync(path.join(base, "agents", a.name + ".toml"), toToml(obj) + "\n", "utf8");
  }

  // hooks.json — idempotent UserPromptSubmit
  const hooksPath = path.join(base, "hooks.json");
  const hooks = fs.existsSync(hooksPath) ? JSON.parse(fs.readFileSync(hooksPath, "utf8")) : {};
  const ups: any[] = hooks.UserPromptSubmit ?? (hooks.UserPromptSubmit = []);
  const already = ups.some(g => (g.hooks ?? []).some((h: any) => String(h.command).includes("rc context")));
  if (!already) ups.push({ matcher: "*", hooks: [{ type: "command", command: HOOK_CMD, timeout: 20 }] });
  fs.writeFileSync(hooksPath, JSON.stringify(hooks, null, 2) + "\n", "utf8");

  // config.toml — ensure [features] hooks = true (merge-safe)
  const cfgPath = path.join(base, "config.toml");
  const cfg = fs.existsSync(cfgPath) ? (parseToml(fs.readFileSync(cfgPath, "utf8")) as any) : {};
  cfg.features = { ...(cfg.features ?? {}), hooks: true };
  fs.writeFileSync(cfgPath, toToml(cfg) + "\n", "utf8");
}
