# Agents Overview

Every file under `self/agents/` follows Claude Code's native format (frontmatter with `name` / `description` / `model`, no `tools` restriction). Each `.agent.md` can be invoked directly as `@agent-name`, or delegated by the conductor via `Task(subagent_type="...")`.

All shared workflow rules live in [`self/PIPELINE-OS.md`](PIPELINE-OS.md). Do not duplicate them here.

## System structure

```
              ┌─ user ─┐
              │         │
              ▼         ▼
   main session (conductor)   @copilot-<sub>
   (conductor, default)   (direct shortcut)
              │
              └─ Task() delegate ─→ 7 copilot-* sub-agents
                                  │
                                  ├─ Skill / MCP / Bash / Edit / Write / Glob / Grep / Read
```

Coordination: the main-session conductor owns cross-stage routing. `copilot-*` stage coordinators may dispatch narrow worker sub-agents only after writing a `pipelines/<round>.md` ledger.

## The 7 sub-agents

The conductor is the main session (protocol in `CONDUCTOR-PROTOCOL.md`); the 7 sub-agents below are dispatched by it.

| Agent | File | Role | Model | Color |
|---|---|---|---|---|
| copilot-literature | copilot-literature.agent.md | 📚 Literature scan | haiku | cyan |
| copilot-ideation | copilot-ideation.agent.md | 💡 Interactive ideation | opus | magenta |
| copilot-experiment | copilot-experiment.agent.md | 🧪 Experiment & validation | sonnet | green |
| copilot-writer | copilot-writer.agent.md | ✍️ Paper writing | sonnet | blue |
| copilot-polisher | copilot-polisher.agent.md | ✨ Paper polishing | sonnet | blue |
| copilot-reviewer | copilot-reviewer.agent.md | 🔍 Paper review | opus | yellow |
| copilot-rebuttal | copilot-rebuttal.agent.md | 💬 Rebuttal | sonnet | yellow |

Models chosen per: `opus` for novelty judgment + critical review (ideation, reviewer); `haiku` for retrieval + structuring (literature); `sonnet` for balanced reasoning + speed (conductor, writer, polisher, experiment, rebuttal).

## Pipeline modes

- **Mode A (routing)**: the conductor scans state → one-sentence diagnosis → one-sentence recommendation → single Task() dispatch.
- **Mode B (pipeline)**: the conductor runs a sequence (full research / pre-submission optimization / rebuttal prep / ideation re-check / custom). Cross-stage transitions are approval gates per PIPELINE-OS §5 case ①.

## .copilot/ artifacts

| File | Single writer | Trailer |
|---|---|---|
| state.md | conductor | `__HANDOFF__` |
| literature.md | copilot-literature | `__HANDOFF__` (incl. novelty-evidence) |
| ideas.md | copilot-ideation | `__HANDOFF__` |
| experiments.md | copilot-experiment | `__HANDOFF__` (incl. loop_id) |
| decisions.md | conductor | `__HANDOFF__` |
| handoff.md | multi-writer, append-only | `__HANDOFF__` (collective) |
| reviews/round-N.md | copilot-reviewer | `__HANDOFF__` |

The SessionStart memory injector reads each `__HANDOFF__` block to bring a fresh session up to speed.

## Hooks in this directory

- `self/hooks/scientist-guardrails.json` — SessionStart: AI Scientist runtime advisory.
- `self/hooks/session-memory-injector.json` — SessionStart: inject `__HANDOFF__` summaries.
- `self/hooks/dispatch-reminder.json` — UserPromptSubmit: nudge sub-agent dispatch on exec-class prompts.
- `self/hooks/loop-armer.json` — PostToolUse: recommend `/loop` self-arming on long background experiments.
- `.claude/settings.json` (registered by `self/install.py`) — also wires `research_copilot_guard.py` as PreToolUse and `block_protected_paths.py` / `regen_skill_json.py` for project housekeeping.

## Troubleshooting

- MCP latency: `python self/scripts/diagnose-mcp.py`.
- Memory injector noisy / silent: check `.copilot/*.md` actually contain `## __HANDOFF__` blocks.
- Dispatch-reminder too talky: `touch .copilot/dispatch-reminder.disabled` to silence it (the hook honours the flag).
- Loop-armer doesn't fire: confirm the launched command matches `LONGRUN_PATTERNS` in `post_tool_loop_armer.py`; otherwise extend the list.
