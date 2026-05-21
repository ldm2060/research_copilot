"""Research Copilot Workflow Guard hook.

PreToolUse hook that enforces workflow discipline for the research-copilot agent.
Reads tool call payload from stdin, detects if research-copilot is the active agent,
applies blocking patterns, and outputs an allow/deny decision.

Detection strategy:
- Read transcript file (JSONL) to find the most recent agent context
- If research-copilot is active, apply blocking patterns
- If a copilot-* sub-agent is active, allow (they need to run their work)
- If detection is uncertain, allow (fail-open for safety)
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
PLANNING_KEYWORDS = ("步骤", "plan:", "checklist", "tasks:")
PLANNING_NUMBERED = re.compile(r"^\s*\d+\.\s+\S", re.MULTILINE)
EXCEPTION_KEYWORDS = ("completed", "done", "已完成", "已经完成")


def allow() -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "permissionDecision": "allow",
        }
    }


def deny(message: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
        "systemMessage": message,
    }


def detect_active_agent(transcript_path: str) -> str | None:
    """Inspect transcript JSONL to find the active sub-agent name.

    Returns the most recent subagent_type seen, or None if uncertain.
    """
    if not transcript_path:
        return None
    path = Path(transcript_path)
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines[-200:]):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        meta = entry.get("metadata") or {}
        candidate = (meta.get("subagent_type")
                     or entry.get("subagent_type")
                     or meta.get("agent")
                     or entry.get("agent"))
        if candidate:
            return str(candidate)
    return None


def is_research_copilot_session(payload: dict[str, Any]) -> bool:
    agent = detect_active_agent(payload.get("transcript_path", ""))
    if agent == "research-copilot":
        return True
    if agent and agent.startswith("copilot-"):
        return False
    return False


def is_read_only(command: str) -> bool:
    stripped = command.strip()
    return any(stripped.startswith(prefix) for prefix in READ_ONLY_PREFIXES)


def check_pattern_1_experiment(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    if tool_name not in ("Bash", "PowerShell"):
        return None
    command = str(tool_input.get("command", ""))
    if not command:
        return None
    if is_read_only(command):
        return None
    keyword_hit = any(kw in command for kw in EXPERIMENT_KEYWORDS)
    regex_hit = bool(EXPERIMENT_REGEX.search(command))
    if keyword_hit or regex_hit:
        return ("Blocked by research-copilot-guard: research-copilot cannot run "
                "experiments directly. Delegate to copilot-experiment via Agent "
                "tool with subagent_type='copilot-experiment'.")
    return None


def check_pattern_3_delegation(tool_name: str, tool_input: dict[str, Any],
                               state: dict[str, Any]) -> str | None:
    current_state = state.get("current_state", "UNINITIALIZED")
    if current_state not in ("S2_IDEATION", "S3_EXPERIMENT"):
        return None
    expected = ("copilot-ideation" if current_state == "S2_IDEATION"
                else "copilot-experiment")
    last_delegation = state.get("last_delegation")
    if last_delegation == expected:
        return None
    if tool_name == "Agent":
        sub_type = tool_input.get("subagent_type", "")
        if sub_type == expected:
            return None
        return (f"Blocked by research-copilot-guard: state {current_state} "
                f"requires delegation to {expected}. Use Agent tool with "
                f"subagent_type='{expected}'.")
    if tool_name in ("Bash", "PowerShell", "Write", "Edit"):
        return (f"Blocked by research-copilot-guard: state {current_state} "
                f"requires delegation to {expected}. Use Agent tool with "
                f"subagent_type='{expected}'.")
    return None


def load_state() -> dict[str, Any]:
    state_path = Path(".copilot/state.md")
    state = {
        "current_state": "UNINITIALIZED",
        "last_delegation": None,
        "skill_invoked": False,
        "override_next": False,
    }
    if not state_path.exists():
        return state
    try:
        text = state_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return state
    stage_match = re.search(r"^-\s*Stage:\s*(\S+)", text, re.MULTILINE)
    if stage_match:
        state["current_state"] = stage_match.group(1).strip()
    owner_match = re.search(r"^-\s*Owner of last round:\s*@?(\S+)",
                            text, re.MULTILINE)
    if owner_match:
        state["last_delegation"] = owner_match.group(1).strip()
    if "OVERRIDE:" in text.splitlines()[-1:] and text.splitlines():
        state["override_next"] = True
    return state


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
    if not is_research_copilot_session(payload):
        print(json.dumps(allow()))
        return 0
    state = load_state()
    if state.get("override_next"):
        print(json.dumps(allow()))
        return 0
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    if tool_name in ("Read", "Grep", "Glob", "TaskCreate", "TaskUpdate",
                     "TaskList", "TaskGet", "Skill", "AskUserQuestion"):
        print(json.dumps(allow()))
        return 0
    if tool_name == "Agent":
        sub_type = str(tool_input.get("subagent_type", ""))
        if sub_type.startswith("copilot-"):
            print(json.dumps(allow()))
            return 0
    for check in (
        check_pattern_1_experiment(tool_name, tool_input),
        check_pattern_3_delegation(tool_name, tool_input, state),
    ):
        if check:
            print(json.dumps(deny(check)))
            return 0
    print(json.dumps(allow()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
