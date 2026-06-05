import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { kitRoot } from "../render.js";
import { parseAgent } from "../agent-frontmatter.js";
import { MCP_SERVERS } from "../mcp.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const RULE = `---
trigger: always_on
---
# Research Copilot (Windsurf — class-2, agent-less)

This repository uses research-copilot (\`.research/\`). Windsurf has no subagents and no per-turn
auto-injection, so on EVERY turn:

1. FIRST run the shell command \`rc context --platform windsurf\` and read its output — your current
   \`[workflow-state:<state>]\` + \`[research-state]\` (active task, graph, recommended next activity).
2. Windsurf has NO subagents. When the state says "dispatch the rc-<kind> executor", instead invoke the
   matching workflow \`/rc-<kind>\` (in \`.windsurf/workflows/\`) and perform that executor's role YOURSELF,
   inline, following its instructions. Write outputs into the task's artifacts; then run \`rc task verify <id>\`.
3. END the turn by echoing one line: \`Active task: <id>\` (from \`rc task current\`).

Never fabricate numbers or citations — the verify gate enforces traceability.
`;

export function configureWindsurf(repo: string): void {
  const base = path.join(repo, ".windsurf");
  fs.mkdirSync(path.join(base, "workflows"), { recursive: true });
  fs.mkdirSync(path.join(base, "rules"), { recursive: true });
  const KIT = kitRoot(__dirname);

  // executors -> workflows (agent-less: each rc-<name> becomes a slash-workflow)
  const agentsSrc = path.join(KIT, "agents");
  for (const f of fs.readdirSync(agentsSrc).filter(x => x.endsWith(".md"))) {
    const a = parseAgent(fs.readFileSync(path.join(agentsSrc, f), "utf8"));
    const wf = ["---", `description: ${JSON.stringify(a.description)}`, "---", "", `# /${a.name}`, "", a.body, ""].join("\n");
    fs.writeFileSync(path.join(base, "workflows", a.name + ".md"), wf, "utf8");
  }

  fs.writeFileSync(path.join(base, "rules", "research-copilot.md"), RULE, "utf8");

  // MCP is USER-GLOBAL only in Windsurf (~/.codeium/windsurf/mcp_config.json) — no repo-local MCP
  // file is supported. Append a one-time setup note to the rule (idempotent: keyed on the heading).
  const rulePath = path.join(base, "rules", "research-copilot.md");
  const cur = fs.readFileSync(rulePath, "utf8");
  if (!cur.includes("## MCP servers")) {
    const snippet = JSON.stringify({ mcpServers: MCP_SERVERS }, null, 2);
    const note = [
      "",
      "## MCP servers (manual, user-global)",
      "",
      "Windsurf reads MCP servers ONLY from the user-global config",
      "`~/.codeium/windsurf/mcp_config.json` (Windsurf does not support a repo-local MCP file).",
      "Add the two research-copilot servers (`research-scholar`, `research-pdf`) there manually,",
      "merging into any existing `mcpServers`:",
      "",
      "```json",
      snippet,
      "```",
      "",
    ].join("\n");
    fs.appendFileSync(rulePath, note, "utf8");
  }
}
