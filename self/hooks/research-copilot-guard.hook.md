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