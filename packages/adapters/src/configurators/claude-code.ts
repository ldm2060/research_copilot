import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { deepMergeJson } from "../render.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KIT = path.resolve(__dirname, "../../../../research-kit");

export function configureClaudeCode(repo: string): void {
  const cc = path.join(repo, ".claude");
  fs.mkdirSync(path.join(cc, "agents"), { recursive: true });

  // settings.json — merge our UserPromptSubmit hook in, preserving foreign config
  const settingsPath = path.join(cc, "settings.json");
  const existing = fs.existsSync(settingsPath)
    ? JSON.parse(fs.readFileSync(settingsPath, "utf8")) : {};
  const ours = {
    hooks: {
      UserPromptSubmit: [{
        matcher: "*",
        hooks: [{ type: "command", command: "rc context --inject --format text", timeout: 20 }],
      }],
    },
  };
  fs.writeFileSync(settingsPath, JSON.stringify(deepMergeJson(existing, ours), null, 2) + "\n", "utf8");

  // agents — copy the 10 neutral templates verbatim (Claude Code consumes md+frontmatter)
  const agentsSrc = path.join(KIT, "agents");
  for (const f of fs.readdirSync(agentsSrc).filter(x => x.endsWith(".md"))) {
    fs.copyFileSync(path.join(agentsSrc, f), path.join(cc, "agents", f));
  }

  // CLAUDE.md — minimal behavioural note pointing at the workflow
  fs.writeFileSync(path.join(repo, "CLAUDE.md"),
    "- Research workflow is governed by .research/. Each turn, the injected " +
    "[workflow-state]+[research-state] block tells you the next step. Dispatch rc-* executors; do not do domain work inline.\n",
    { flag: "a" });
}
