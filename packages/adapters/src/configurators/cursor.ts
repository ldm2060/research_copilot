import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { kitRoot } from "../render.js";
import { parseAgent } from "../agent-frontmatter.js";
import { MCP_SERVERS } from "../mcp.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const RULE = `---
alwaysApply: true
---
# Research Copilot (Cursor — class-2)

This repository uses research-copilot (\`.research/\`). Cursor cannot inject per-turn state
automatically, so follow this protocol on EVERY turn:

1. FIRST run the shell command \`rc context --platform cursor\` and read its output — it is your
   current \`[workflow-state:<state>]\` + \`[research-state]\` (active task, task graph, and the
   recommended next research activity).
2. Act on it: if a task is in_progress, dispatch the matching \`rc-<kind>\` subagent (in
   \`.cursor/agents/\`) with the task's prd.md + execute.jsonl specs. Do NOT do domain work inline.
   When the executor returns, run \`rc task verify <id>\`.
3. END the turn by echoing one line: \`Active task: <id>\` (from \`rc task current\`), so the next
   turn can re-resolve context.

Never fabricate numbers or citations — the verify gate enforces traceability.
`;

export function configureCursor(repo: string): void {
  const base = path.join(repo, ".cursor");
  fs.mkdirSync(path.join(base, "agents"), { recursive: true });
  fs.mkdirSync(path.join(base, "rules"), { recursive: true });
  const KIT = kitRoot(__dirname);

  const agentsSrc = path.join(KIT, "agents");
  for (const f of fs.readdirSync(agentsSrc).filter(x => x.endsWith(".md"))) {
    const a = parseAgent(fs.readFileSync(path.join(agentsSrc, f), "utf8"));
    const fm = ["---", `name: ${a.name}`, `description: ${JSON.stringify(a.description)}`];
    if (a.model) fm.push(`model: ${a.model}`);
    fm.push("---", "");
    fs.writeFileSync(path.join(base, "agents", a.name + ".md"), fm.join("\n") + a.body + "\n", "utf8");
  }

  fs.writeFileSync(path.join(base, "rules", "research-copilot.mdc"), RULE, "utf8");

  // best-effort sessionStart injection (Cursor hooks.json) — idempotent
  const hooksPath = path.join(base, "hooks.json");
  const hooks = fs.existsSync(hooksPath) ? JSON.parse(fs.readFileSync(hooksPath, "utf8")) : { version: 1 };
  hooks.hooks = hooks.hooks ?? {};
  const ss: any[] = hooks.hooks.sessionStart ?? (hooks.hooks.sessionStart = []);
  if (!ss.some((h: any) => typeof h?.command === "string" && h.command.includes("rc context"))) {
    ss.push({ command: "rc context --platform cursor" });
  }
  fs.writeFileSync(hooksPath, JSON.stringify(hooks, null, 2) + "\n", "utf8");

  // .cursor/mcp.json — register our two MCP servers (merge-safe + idempotent)
  const mcpPath = path.join(base, "mcp.json");
  const mcp = fs.existsSync(mcpPath) ? JSON.parse(fs.readFileSync(mcpPath, "utf8")) : {};
  mcp.mcpServers = { ...(mcp.mcpServers ?? {}), ...MCP_SERVERS };
  fs.writeFileSync(mcpPath, JSON.stringify(mcp, null, 2) + "\n", "utf8");
}
