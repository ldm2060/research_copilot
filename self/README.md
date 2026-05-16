# self/ — Research Copilot Workspace Assets

This directory holds **all the self-owned assets** for the Claude Code paper-research workspace: agents, skills, hooks, MCP servers, and their installer. `third_party/` provides additional capabilities, but `self/` keeps the core loop self-sufficient.

## 🚀 One-shot install

```bash
python self/install.py
```

Automatically does:

1. Install Python deps (`pdfplumber` etc.)
2. Write project-level `.mcp.json` pointing at the MCP servers under `self/mcp/servers/` (env includes `PYTHONFAULTHANDLER=1` / `OMP_NUM_THREADS=1` to mitigate socket timeouts).
3. Register the SessionStart hook into `.claude/settings.json` (scientist-guardrails).
4. Regenerate `skill.json` metadata next to every `SKILL.md` (required by Claude Code 2.1.142+ for plugin skill discovery).
5. Handshake each MCP server with a JSON-RPC `initialize` request.
6. Report the status of optional secrets (`ARXIVSUB_SKILL_KEY`).

After install, **restart Claude Code or run `/clear`** to use.

### Optional flags

```bash
python self/install.py --dry-run        # print plan, do not write
python self/install.py --skip-deps      # skip pip install
python self/install.py --skip-verify    # skip the MCP startup test
python self/install.py --target /path   # install into a non-default workspace
```

### Skill metadata only

If you only need to refresh `skill.json` files (e.g. after editing SKILL.md frontmatter):

```bash
bash self/scripts/generate-skill-json.sh         # regenerate as needed
bash self/scripts/generate-skill-json.sh --check # CI mode: non-zero if any are stale
```

The bash wrapper delegates to `self/scripts/generate-skill-json.py`, which works cross-platform.

## 📁 Directory layout

```
self/
├── README.md                       # this file
├── AGENTS.md                       # the 8-agent overview
├── SKILLS.md                       # skill overview
├── install.py                      # one-shot installer
├── VERSION
├── agents/                         # 1 conductor + 7 sub-agents
│   ├── research-copilot.agent.md       🧭 pipeline conductor (the recommended single entry point)
│   ├── copilot-literature.agent.md     📚 literature scan
│   ├── copilot-ideation.agent.md       💡 interactive ideation
│   ├── copilot-experiment.agent.md     🧪 experiment running & validation
│   ├── copilot-writer.agent.md         ✍️  paper drafting
│   ├── copilot-polisher.agent.md       ✨ paper polishing
│   ├── copilot-reviewer.agent.md       🔍 paper review
│   └── copilot-rebuttal.agent.md       💬 rebuttal drafting
├── skills/                         # 23 skills (not hardcoded by any agent file)
│   ├── paper-*/                        # paper writing / rewriting / checks
│   ├── scientist-*/                    # AI Scientist workflow capabilities
│   ├── arxivsub-skill/                 # arXiv + top-venue search capability
│   ├── init-mcp/                       # MCP install entry
│   ├── talk-normal/                    # reply style
│   └── model-escalation/               # escalation handoff
├── runtimes/                       # static runtime assets (not skills)
│   └── scientist-support/runtime/       # AI Scientist runtime assets
├── hooks/                          # SessionStart hook
├── mcp/                            # 6 MCP servers
└── scripts/
    ├── diagnose-mcp.py             # MCP responsiveness diagnostic
    ├── generate-skill-json.sh      # bash wrapper for the skill.json generator
    └── generate-skill-json.py      # cross-platform skill.json generator
```

Cross-session working memory lives in the repo-root `.copilot/`, owned by `@research-copilot`:

```
.copilot/                        ← default to .gitignore
├── state.md                     current stage cursor + next-step recommendation       ← only research-copilot writes
├── literature.md                literature bank                                       ← only copilot-literature writes
├── ideas.md                     candidate ideas                                       ← only copilot-ideation writes
├── experiments.md               experiment log                                        ← only copilot-experiment writes
├── handoff.md                   sub-agent fact handoff (append-only)                  ← writer / polisher / reviewer / rebuttal
├── decisions.md                 approval-gate decision record                         ← only research-copilot writes
└── reviews/round-N.md           each independent review round                         ← only copilot-reviewer writes
```

## 🧭 Entry point selection

| What you want | Entry |
|---|---|
| Unsure what to do next / want a guided pipeline | `@research-copilot` |
| Run the full pipeline (from research target to submission) | `@research-copilot` with "run the full pipeline" |
| Pre-submission overall optimization | `@research-copilot` with "submission sprint" |
| Rebuttal prep | `@research-copilot` with "rebuttal prep" |
| You already know what to do — call a sub-agent | `@copilot-<sub>` (see AGENTS.md) |
| First-time MCP setup | `python self/install.py` or `/init-mcp` |
| Stuck after many rounds, want a stronger model | `/model-escalation` |
| Paper search skill | `/arxivsub-skill` (requires `ARXIVSUB_SKILL_KEY`) |
| MCP latency / socket-timeout diagnosis | `python self/scripts/diagnose-mcp.py` |

## 🔧 Troubleshooting

**MCP servers not showing up in the tool list**
- Restart Claude Code or run `/clear`
- Check that `.mcp.json` exists and points at the correct paths
- Re-run `python self/install.py --skip-deps`

**`pdf-text` reports a missing package**
- Run `pip install pdfplumber` or `pip install PyPDF2`
- Or re-run `python self/install.py`

**`arxivsub-search` reports `missing_api_key`**
- Set the `ARXIVSUB_SKILL_KEY` environment variable, or add to a repo-root `.env`
- Restart Claude Code so the new env var takes effect

**Hook not triggering**
- Check that `.claude/settings.json` contains a `hooks.SessionStart` entry
- Confirm `python` is on PATH

**Agent calls hanging / socket timeouts**
- Run `python self/scripts/diagnose-mcp.py` to find the slowest server
- Inspect each server's initialize time + tools/list time
- `--watch` for continuous monitoring of intermittent stalls
- Tip: long tasks (training) MUST use `run_in_background=true`; sub-agents already follow this

**Skills not auto-loading after a Claude Code update**
- Claude Code 2.1.142+ requires `skill.json` next to each `SKILL.md`. Re-run `python self/install.py` (or `bash self/scripts/generate-skill-json.sh`) to regenerate them.

## Relationship to third_party/

`self/` is the core loop: one conductor + seven sub-agents + self-owned skills + self-owned MCPs are enough for an end-to-end "ordinary paper-research full pipeline."

`third_party/` provides extensions (superpowers, orchestra, oh-my-paper, imbad0202-research, k-dense-ai, etc.), driven by the repo-root `agent.txt` / `skill.txt` / `hook.txt` manifests through `scripts/build_copilot_workspace.py` into the `dist/` distribution.

If you only want `self/`, run `install.py` and you are done; `third_party/` is not required.
