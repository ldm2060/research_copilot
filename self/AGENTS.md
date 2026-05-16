# Agents Overview

Every file under `self/agents/` follows Claude Code's native format (frontmatter with `name` / `description` / `model`, **no `tools` restriction** — they have access to every default tool). Each `.agent.md` can be invoked directly by the user with `@agent-name`, or delegated by the conductor via `Task(subagent_type="...")`.

## System structure

```
              ┌─ user ─┐
              │         │
              ▼         ▼
   research-copilot   @copilot-<sub> direct call
   (pipeline guardian,    (shortcut path when you know what to do)
    recommended single entry)
              │
              └─ Task() delegate ─→ 7 independent sub-agents
                                  │
                                  ├─ Skill tool → match a capability skill
                                  ├─ MCP tool   → match a capability MCP
                                  └─ Bash / Edit / Write / Glob / Grep / Read → local operations

Iron rule: sub-agents do NOT call Task on each other; they coordinate via "soft suggestions" + user decisions
```

## The 8 agents

| Agent | File | Role | Model | Color | When to use |
|---|---|---|---|---|---|
| **research-copilot** | `research-copilot.agent.md` | 🧭 Full-pipeline conductor | sonnet | magenta | "what's next" / "run the full pipeline" / "submission sprint" / "rebuttal prep" / "ideation re-check" |
| **copilot-literature** | `copilot-literature.agent.md` | 📚 Literature scan | haiku | cyan | search papers / lock baseline / augment related work / verify citations |
| **copilot-ideation** | `copilot-ideation.agent.md` | 💡 Interactive ideation | **opus** | magenta | find innovation directions / cross-domain brainstorm / novelty re-check |
| **copilot-experiment** | `copilot-experiment.agent.md` | 🧪 Experiment & validation | sonnet | green | run training / reproduce baseline / ablation / read metric / plot / judge if it works |
| **copilot-writer** | `copilot-writer.agent.md` | ✍️  Paper writing | sonnet | blue | draft sections / turn results into prose / expand / shorten / translate / captions |
| **copilot-polisher** | `copilot-polisher.agent.md` | ✨ Paper polishing | sonnet | blue | academic register / de-AI / syntax / terminology (no technical changes) |
| **copilot-reviewer** | `copilot-reviewer.agent.md` | 🔍 Paper review | **opus** | yellow | pre-submission quality gate / claim-evidence alignment / simulated top-venue review / rebuttal self-check |
| **copilot-rebuttal** | `copilot-rebuttal.agent.md` | 💬 Rebuttal drafting | sonnet | yellow | draft responses to reviewer comments / defense scripts / follow-up requirement list |

**Model assignments — rationale**:
- `opus`: heavy reasoning, cross-domain analogy, independent review — `copilot-ideation` and `copilot-reviewer` need to solidify "novelty judgment" and "strict review."
- `haiku`: retrieval + structured organization, speed first — `copilot-literature` calls paper-retrieval MCPs heavily and only needs summary / categorization / distance scoring.
- `sonnet`: balance of reasoning and speed — conductor, writer, polisher, experiment, rebuttal all fall in this tier.

## The conductor's two work modes

### Mode A: Routing (default)

When the user asks anything: scan `.copilot/state.md` → one-sentence diagnosis → one-sentence recommendation → delegate to one sub-agent **or** integrate yourself.

### Mode B: Pipeline

Triggered by keywords, with preset templates:

| Template | Sequence |
|---|---|
| Full research | S1 literature → S2 ideation → S3 experiment → S4 writing → S5 polishing → S6 review → S7 rebuttal |
| Pre-submission overall optimization | read-through → S4 expand/shorten → S5 polish → S5 de-AI → S6 final review |
| Rebuttal prep | S6 self-check → S7 draft → S6 re-review → S7 final |
| Ideation re-check | S2 brainstorm → S3 quick experimental validation → back to S2 revise OR forward to S4 |
| Custom | user-specified sequence (e.g. `S5→S6→S5→S6`) |

Every stage transition MUST use `AskUserQuestion` as an approval gate; no advance without confirmation.

## Non-linear flow & back-edges

The forward path `S1 → S2 → S3 → S4 → S5 → S6 → S7` is the happy path. In practice, every stage can emit a **back-edge** signal that asks the conductor to route to an earlier stage. **All back-edges flow through `research-copilot` and are gated behind `AskUserQuestion`** — sub-agents emit suggestions, never dispatch each other.

```
S1 literature ────┐
                  ↓
S2 ideation ←─────┤  ← from S3 (idea has a fundamental flaw / implementation path off)
       ↓          │  ← from S4 (writing exposes a conceptual gap or unsupported claim)
S3 experiment ←───┤  ← from S6 (reviewer flags contribution unsupported)
       ↓          │  ← from S7 (reviewer undermines novelty, rare)
S4 writer ←───────┤
       ↓          │  ← from S6 (reviewer flags missing data / ablation)
S5 polisher       │  ← from S7 (reviewer requires new experiment)
       ↓
S6 reviewer
       ↓
S7 rebuttal
```

The complete signal → back-edge mapping lives in `research-copilot.agent.md` §"Back-edge routing matrix." Per-edge loop counters in `.copilot/state.md` cap iteration at **3 fires of the same back-edge**, after which the conductor hard-stops and asks the user via `AskUserQuestion`:
- "Keep iterating (reset this counter)"
- "Switch strategy (pause this back-edge)"
- "Escalate to `/model-escalation`"
- "Stop the pipeline (I decide)"

This bounds runaway experiment↔ideation or reviewer↔experiment cycles.

## Sub-agent write-permission partitioning (persistent memory)

`.copilot/` is cross-session working memory; **write permissions are strictly partitioned** to avoid mutual overwrite:

| File | Writer | Content |
|---|---|---|
| `state.md` | research-copilot | Current stage cursor + next-step recommendation + stage history |
| `literature.md` | copilot-literature | Candidate papers + selected baseline |
| `ideas.md` | copilot-ideation | 6-dimension candidates + selected direction |
| `experiments.md` | copilot-experiment | Experiment design + Run-N log |
| `handoff.md` | writer / polisher / reviewer / rebuttal | Sub-agent fact handoff (append) |
| `decisions.md` | research-copilot | Decision record at every approval gate |
| `reviews/round-N.md` | copilot-reviewer | Each independent review round |

**All sub-agents may read every file** (facts shared). `handoff.md` is the only multi-writer file and is append-only.

## Routing rules

All agents share these hard constraints:

1. **MCP priority (generic)** — for paper retrieval prefer the paper-retrieval MCP class; BibTeX edits only via the BibTeX MCP class; fall back to `WebSearch` only if these miss. **Agent files do NOT hardcode MCP names** — let Claude Code match by description keywords against the current tool list.
2. **NEVER fabricate** — data, citations, experiment results, reviewer consensus must never be reconstructed from memory.
3. **NEVER hardcode skill / MCP / other agent names** — describe by capability phrase ("paper-retrieval class," "BibTeX metadata class") so future tool-list changes do not require agent edits.
4. **Sub-agents do NOT Task each other** — all cross-agent dispatch flows through `research-copilot`; sub-agents emit only soft suggestions at end-of-response.
5. **Long-task discipline** — training / large-scale retrieval / long fetches MUST use `Bash(run_in_background=true)`, `Monitor`, or `ScheduleWakeup`. **NEVER** poll with repeated `Bash(timeout=600000)` to "just wait." See `copilot-experiment.agent.md` §"Step 3: Execute — long-task time-budget rule" for the full table.
6. **WebFetch single-call timeout cap 30 s** — drop on timeout, fall back to `WebSearch` summary.

## Skill invocation — two modes

Agents request a capability skill in one of two ways. The default is the **capability phrase**, which lets the Claude Code harness auto-match against the current skill list and stays robust when names change.

| Mode | When to use | Phrasing in a sub-agent's prompt |
|---|---|---|
| **Capability phrase** (default) | The user has not named a specific skill | "Use the available *paper-polish* capability to ..." |
| **Explicit `Skill(...)`** | The user typed `/<skill-name>` in their request, or auto-activation has demonstrably missed in this session | "Invoke `Skill(skill='paper-polish', args='...')` for this round." |

`self/` ships 23 skills; `third_party/` adds more if installed (`scripts/build_copilot_workspace.py` merges them into `dist/`). The hard constraint "**NEVER hardcode skill / MCP / other agent names in capability prose**" applies to all agents — explicit `Skill(...)` is allowed only for the two carve-outs above.

## Socket-timeout mitigation

- Nested Task deadlocks → the iron rule "sub-agents do not call each other" eliminates nesting
- Hardcoded MCP-priority accumulating timeouts → no hardcoding, match capability at runtime
- Long-task blocking → enforced background mode
- MCP server hang without logs → `self/scripts/diagnose-mcp.py` probes each server individually

Detailed diagnosis: `python self/scripts/diagnose-mcp.py`.

## `/loop` resilience for flaky third-party models

If your Claude Code session is backed by a third-party model that drops mid-task on network glitches, you can arm a session-level watchdog before kicking off a long pipeline:

```
/loop 1m If the current session's task is not complete, continue. Otherwise, delete this scheduled task.
```

This re-triggers the model every minute until the work is done, then self-deletes via `CronDelete`. It is a **user-side** practice — agents do not start their own cron tasks (that would surprise the user and conflict with the conductor's "MUST stop at approval gates" hard constraint).

Alternatives when network stability matters:
- Use the native Claude Code models (Sonnet / Opus / Haiku) — most stable
- Run `/model-escalation` to hand off a stuck task to a stronger model with a fresh prompt
- Run `python self/scripts/diagnose-mcp.py` to rule out an MCP hang (a different failure mode that `/loop` will not fix)

Distinguishing the two failure modes:
- **Model network drop**: the assistant goes silent mid-response or replies with a transport error → `/loop` reactivates
- **MCP hang**: tool calls return `socket timeout` or never resolve → run `diagnose-mcp.py`, the loop will not unstick this
