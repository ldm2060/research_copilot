---
name: research-copilot-guard
event: PreToolUse
purpose: Enforcement guard for the research-copilot agent
---

# Research Copilot Workflow Guard (Specification)

> **NOTE:** This markdown file is the *specification* for the guard's behavior.
> The executable implementation is `self/hooks/scripts/research_copilot_guard.py`.
> Registration into `.claude/settings.json` is done at install time by `self/install.py`
> via `register_research_copilot_guard()`. Do not hand-edit `.claude/settings.json` —
> re-run `python self/install.py` after changing any of these files.

## Registration

`install.py` writes a `PreToolUse` block with matcher `Bash|PowerShell|Agent|Write|Edit`
containing:

- **Primary (only when `python` is in PATH at install time):** a `type: "command"` hook
  invoking `python <path>/research_copilot_guard.py`. Deterministic, zero LLM cost.
- **Fallback (always registered):** a `type: "prompt"` hook with a conservative prompt
  that defaults to APPROVE unless the transcript contains concrete evidence that
  `research-copilot` is the active sub-agent AND the tool call matches an explicit
  violation pattern.

If Python is not available at install time, only the prompt fallback is registered.

## Active-Agent Scoping

Both layers gate on the active sub-agent. The guard is a no-op for tool calls
originating from the main session or from any agent other than `research-copilot`
(in particular, `copilot-experiment` must remain free to run training scripts).
The Python guard inspects the transcript JSONL to find the most recent
`subagent_type` marker; the prompt fallback applies the same rule by reading
the transcript context.

## Patterns

The Python guard checks five patterns in order; first deny short-circuits the rest. All five fire only when the active sub-agent is `research-copilot`:

| # | Name | Tool match | When it denies |
|---|---|---|---|
| 1 | experiment-script | `Bash`, `PowerShell` | Non-read-only command containing experiment keywords (`train.py`, `wandb`, `torchrun`, …) |
| 3 | state-mandated-delegation | `Agent`, `Bash`, `PowerShell`, `Write`, `Edit` | Current state is `S2_IDEATION` or `S3_EXPERIMENT` and the tool call is not the correct delegation |
| 5 | memory-gate | `Write`, `Edit` | Writing to `.copilot/{ideas,experiments,literature,decisions}.md` with no prior `Read` of any `.copilot/*.md` in the session |
| 6 | research-gate | `Write`, `Edit` | Writing a `## Idea` block to `.copilot/ideas.md` with fewer than 2 distinct paper-retrieval MCP queries in the session |
| 7 | plan-list-gate | `Agent` | research-copilot is in `MODE_B_PIPELINE` / `PLAN_PUBLISHED` / `AWAIT_SUBAGENT_END` state and dispatches `Agent(copilot-*)` with zero `TaskCreate` calls in the current turn |

Patterns 5, 6, 7 each have a dedicated unit test file under `self/hooks/scripts/__tests__/`.

The frontmatter `tools:` allowlist on `research-copilot.agent.md` is a stronger, complementary control: it prevents the conductor from ever invoking `Bash` / `PowerShell` / `WebFetch` / MCP tools in the first place, so patterns 1, 5, 6 act as inner safety net rather than primary defense.