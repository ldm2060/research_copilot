"""Research Copilot Workflow Guard hook (PreToolUse).

Polices the MAIN SESSION acting as conductor. The main session must delegate
domain work to copilot-* sub-agents and must publish a TaskCreate plan list
before dispatching. copilot-* sub-agents run freely (exempt).

Origin attribution uses the authoritative `agent_id` payload field: it is
present ONLY inside a sub-agent call, so its absence => main session. Any
ambiguity resolves to main (conservative — never silently exempt the conductor).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

READ_ONLY_PREFIXES = ("grep", "cat", "ls", "head", "tail", "find",
                      "Get-Content", "Select-String", "Get-ChildItem")
EXPERIMENT_KEYWORDS = ("train.py", "run_experiment", "wandb", "mlflow",
                       "tensorboard", "torchrun", "deepspeed", "accelerate")
EXPERIMENT_REGEX = re.compile(r"python[\w\s.-]*\b(train|experiment|run_exp)\b",
                              re.IGNORECASE)
RESEARCH_MCP_PREFIXES = (
    "mcp__arxiv-search__",
    "mcp__arxivsub-search__",
    "mcp__google-scholar__",
    "mcp__dblp-bib__",
)
# Conductor-owned artifacts: the main session MAY write these.
CONDUCTOR_OWNED_ARTIFACTS = (".copilot/state.md", ".copilot/decisions.md")
# Delegated artifacts: the main session must NOT write these.
DELEGATED_ARTIFACTS = ("sections/", "references.bib",
                       ".copilot/ideas.md", ".copilot/experiments.md",
                       ".copilot/literature.md")
READ_ONLY_TOOLS = ("Read", "Grep", "Glob", "TaskCreate", "TaskUpdate",
                   "TaskList", "TaskGet", "Skill", "AskUserQuestion")
COPILOT_SUBAGENT_PREFIX = "copilot-"


def allow() -> dict[str, Any]:
    return {"hookSpecificOutput": {"permissionDecision": "allow"}}


def deny(message: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"permissionDecision": "deny",
                                   "permissionDecisionReason": message},
            "systemMessage": message}


def is_main_session(payload: dict[str, Any]) -> bool:
    """Main session iff `agent_id` absent/empty (per Claude Code hooks docs)."""
    return not payload.get("agent_id")


def is_exempt_subagent(payload: dict[str, Any]) -> bool:
    if is_main_session(payload):
        return False
    return str(payload.get("agent_type") or "").startswith(COPILOT_SUBAGENT_PREFIX)


def is_read_only(command: str) -> bool:
    stripped = command.strip()
    return any(stripped.startswith(prefix) for prefix in READ_ONLY_PREFIXES)


def _norm(path: str) -> str:
    return str(path).replace("\\", "/")


def _iter_transcript_tool_uses(transcript_path: str | None):
    if not transcript_path:
        return
    p = Path(transcript_path)
    if not p.is_file():
        return
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "tool_use":
            yield {"name": rec.get("name", ""), "input": rec.get("input", {}) or {}}
            continue
        content = None
        if isinstance(rec, dict):
            content = rec.get("content")
            if content is None:
                msg = rec.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    yield {"name": item.get("name", ""),
                           "input": item.get("input", {}) or {}}


def check_m1_delegation(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """M1 delegation gate: deny main-session execution-class work."""
    # Experiment scripts via shell.
    if tool_name in ("Bash", "PowerShell"):
        command = str((tool_input or {}).get("command", ""))
        if not command or is_read_only(command):
            return None
        if any(kw in command for kw in EXPERIMENT_KEYWORDS) or EXPERIMENT_REGEX.search(command):
            return ("Blocked by research-copilot-guard (M1 delegation gate): the "
                    "conductor must not run experiments inline. Delegate via "
                    "Agent(subagent_type='copilot-experiment').")
        return None
    # Paper-retrieval MCP tools.
    if any(tool_name.startswith(p) for p in RESEARCH_MCP_PREFIXES):
        return ("Blocked by research-copilot-guard (M1 delegation gate): the "
                "conductor must not search papers inline. Delegate via "
                "Agent(subagent_type='copilot-literature').")
    # Writes to delegated research artifacts.
    if tool_name in ("Write", "Edit"):
        path = _norm((tool_input or {}).get("file_path", ""))
        if any(_norm(owned) in path for owned in CONDUCTOR_OWNED_ARTIFACTS):
            return None  # conductor owns state.md / decisions.md
        if any(seg in path for seg in DELEGATED_ARTIFACTS):
            return ("Blocked by research-copilot-guard (M1 delegation gate): the "
                    "conductor must not write research artifacts (sections/*.tex, "
                    "references.bib, .copilot/{ideas,experiments,literature}.md) "
                    "inline. Delegate to the matching copilot-* sub-agent.")
    return None


def check_m2_task_list(tool_name: str, tool_input: dict[str, Any],
                       transcript_path: str | None) -> str | None:
    """M2 task-list gate: deny copilot-* dispatch with no TaskCreate this turn."""
    if tool_name != "Agent":
        return None
    sub_type = str((tool_input or {}).get("subagent_type", ""))
    if not sub_type.startswith(COPILOT_SUBAGENT_PREFIX):
        return None
    if not transcript_path:
        return None  # fail-open: cannot inspect
    for entry in _iter_transcript_tool_uses(transcript_path):
        if entry["name"] == "TaskCreate":
            return None
    return ("Blocked by research-copilot-guard (M2 task-list gate): dispatching "
            "a copilot-* sub-agent requires a TaskCreate plan list (one task per "
            "planned dispatch) in this turn. Call TaskCreate first, then Agent().")


def main() -> int:
    raw = sys.stdin.read()
    if not raw:
        print(json.dumps(allow()))
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps(allow()))
        return 0
    try:
        decision = _decide(payload)
    except Exception:
        # Fail-open: any unexpected error yields allow, never traps the user
        # (mirrors _copilot_hook_lib.safe_main's contract).
        import traceback
        sys.stderr.write(traceback.format_exc())
        decision = allow()
    print(json.dumps(decision))
    return 0


def _decide(payload: dict[str, Any]) -> dict[str, Any]:
    """Pure decision logic for a parsed payload. Raising is safe — main()
    catches and fails open."""
    # Exempt copilot-* sub-agents outright (they run experiments/searches/writes).
    if is_exempt_subagent(payload):
        return allow()
    # Everything else (incl. ambiguous) is treated as MAIN SESSION -> police.
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    if tool_name in READ_ONLY_TOOLS:
        return allow()
    transcript_path = payload.get("transcript_path")
    for check in (check_m1_delegation(tool_name, tool_input),
                  check_m2_task_list(tool_name, tool_input, transcript_path)):
        if check:
            return deny(check)
    return allow()


if __name__ == "__main__":
    raise SystemExit(main())
