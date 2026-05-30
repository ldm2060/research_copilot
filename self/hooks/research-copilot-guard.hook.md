---
name: research-copilot-guard
event: PreToolUse
purpose: Enforcement guard for the main-session conductor
---

# Research Copilot Workflow Guard (Specification)

> **NOTE:** This markdown file is the *specification* for the guard's behavior.
> The executable implementation is `self/hooks/scripts/research_copilot_guard.py`.
> Registration into `.claude/settings.json` is done at install time by `self/install.py`
> via `register_research_copilot_guard()`. Do not hand-edit `.claude/settings.json` —
> re-run `python self/install.py` after changing any of these files.

## Registration

`install.py` writes a `PreToolUse` block with matcher
`Bash|PowerShell|Agent|Write|Edit|mcp__arxiv-search__.*|mcp__arxivsub-search__.*|mcp__google-scholar__.*|mcp__dblp-bib__.*`
containing:

- **Primary (only when `python` is in PATH at install time):** a `type: "command"` hook
  invoking `python <path>/research_copilot_guard.py`. Deterministic, zero LLM cost.
- **Fallback (always registered):** a `type: "prompt"` hook with a conservative prompt
  that defaults to APPROVE unless the PreToolUse payload indicates the call originates
  from the main session AND the tool call matches an explicit violation pattern.

If Python is not available at install time, only the prompt fallback is registered.

## Active-Agent Scoping

Both layers gate on the originating agent, identified from the PreToolUse payload's
`agent_id` field. The guard **polices the main session by default** — the main session
is identified by an ABSENT `agent_id` in the payload. It **exempts `copilot-*` sub-agents**
(non-empty `agent_id` whose `agent_type` starts with `copilot-`), so e.g.
`copilot-experiment` must remain free to run training scripts. Ambiguous attribution
defaults to main (conservative).

## Patterns

The Python guard checks two patterns in order; first deny short-circuits the rest. Both fire only when the originating agent is the main session (conductor):

| # | Name | Tool match | When it denies |
|---|---|---|---|
| M1 | delegation gate | `Bash`, `PowerShell`, `Write`, `Edit`, `mcp__arxiv-search__*`, `mcp__arxivsub-search__*`, `mcp__google-scholar__*`, `mcp__dblp-bib__*` | The main session runs experiment scripts via Bash/PowerShell, calls a paper-retrieval MCP tool, or writes `sections/*.tex` / `references.bib` / `.copilot/{ideas,experiments,literature}.md` — i.e. work that belongs to a sub-agent. Writes to `.copilot/state.md` and `.copilot/decisions.md` (the conductor's own artifacts) are allowed. |
| M2 | task-list gate | `Agent` | The main session dispatches `Agent(copilot-*)` with zero `TaskCreate` calls in the current turn. |

Each pattern has dedicated unit-test coverage under `self/hooks/scripts/__tests__/`.

The retired sub-agent's `tools:` allowlist no longer applies; the main session has no
tools allowlist, so the widened PreToolUse matcher + M1 is the bottom line for blocking
inline MCP/experiment work.