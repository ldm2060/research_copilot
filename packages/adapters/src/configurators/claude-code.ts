import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { deepMergeJson } from "../render.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function findKit(start: string): string {
  let dir = start;
  for (;;) {
    const cand = path.join(dir, "research-kit");
    if (fs.existsSync(cand)) return cand;
    const parent = path.dirname(dir);
    if (parent === dir) throw new Error("research-kit not found above " + start);
    dir = parent;
  }
}

export function configureClaudeCode(repo: string): void {
  const KIT = findKit(__dirname);
  const cc = path.join(repo, ".claude");
  fs.mkdirSync(path.join(cc, "agents"), { recursive: true });

  // settings.json — merge our UserPromptSubmit hook in, preserving foreign config
  const settingsPath = path.join(cc, "settings.json");
  const existing = fs.existsSync(settingsPath)
    ? JSON.parse(fs.readFileSync(settingsPath, "utf8")) : {};
  const ups: any[] = existing?.hooks?.UserPromptSubmit ?? [];
  const alreadyInjected = Array.isArray(ups) && ups.some((grp: any) =>
    (grp?.hooks ?? []).some((h: any) => typeof h?.command === "string" && h.command.includes("rc context")));
  const ours = {
    hooks: {
      UserPromptSubmit: [{
        matcher: "*",
        hooks: [{ type: "command", command: "rc context --inject --format text", timeout: 20 }],
      }],
    },
  };
  const merged = alreadyInjected ? existing : deepMergeJson(existing, ours);
  fs.writeFileSync(settingsPath, JSON.stringify(merged, null, 2) + "\n", "utf8");

  // agents — copy the 10 neutral templates verbatim (Claude Code consumes md+frontmatter)
  const agentsSrc = path.join(KIT, "agents");
  for (const f of fs.readdirSync(agentsSrc).filter(x => x.endsWith(".md"))) {
    fs.copyFileSync(path.join(agentsSrc, f), path.join(cc, "agents", f));
  }

  // CLAUDE.md — minimal behavioural note pointing at the workflow (idempotent)
  const claudeMd = path.join(repo, "CLAUDE.md");
  const note = "\n- Research workflow is governed by .research/. Each turn, the injected " +
    "[workflow-state]+[research-state] block tells you the next step. Dispatch rc-* executors; do not do domain work inline.\n";
  const cur = fs.existsSync(claudeMd) ? fs.readFileSync(claudeMd, "utf8") : "";
  if (!cur.includes("Research workflow is governed by .research/")) fs.appendFileSync(claudeMd, note, "utf8");
}
