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


def _iter_transcript_tool_uses(transcript_path: str | None):
    """Yield {name, input} dicts for every prior tool_use in the JSONL transcript.

    Handles two common formats:
      1. Flat record: {"type": "tool_use", "name": ..., "input": ...}
      2. Wrapped message: {"role": ..., "content": [{"type": "tool_use", ...}, ...]}
    """
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
                    yield {
                        "name": item.get("name", ""),
                        "input": item.get("input", {}) or {},
                    }


COPILOT_ARTIFACT_NAMES = ("ideas.md", "experiments.md", "literature.md", "decisions.md")
RESEARCH_MCP_PREFIXES = (
    "mcp__arxiv-search__",
    "mcp__arxivsub-search__",
    "mcp__google-scholar__",
    "mcp__dblp-bib__",
)


def check_pattern_5_no_memory_read(tool_name: str, tool_input: dict[str, Any],
                                   transcript_path: str | None) -> str | None:
    """Pattern 5 (memory-gate): block Write/Edit to .copilot/{ideas,experiments,
    literature,decisions}.md when no prior Read of any .copilot/*.md exists in
    the current session transcript."""
    if tool_name not in ("Write", "Edit"):
        return None
    path = str((tool_input or {}).get("file_path", ""))
    norm = path.replace("\\", "/")
    if ".copilot" not in norm:
        return None
    if not any(name in path for name in COPILOT_ARTIFACT_NAMES):
        return None
    for entry in _iter_transcript_tool_uses(transcript_path):
        if entry["name"] != "Read":
            continue
        prior_path = str((entry.get("input") or {}).get("file_path", "")).replace("\\", "/")
        if ".copilot" in prior_path:
            return None
    return ("Blocked by research-copilot-guard (memory-gate): writing to "
            ".copilot/* artifact without prior Read of any .copilot/*.md in "
            "this session. Per PIPELINE-OS §3 memory-gate, Read the existing "
            "artifact first to avoid re-proposing the same idea/experiment.")


def check_pattern_6_no_research_mcp(tool_name: str, tool_input: dict[str, Any],
                                    transcript_path: str | None) -> str | None:
    """Pattern 6 (research-gate): block a new '## Idea' block being written to
    .copilot/ideas.md when fewer than 2 distinct paper-retrieval MCP queries
    appear in the current session transcript."""
    if tool_name not in ("Write", "Edit"):
        return None
    inp = tool_input or {}
    path = str(inp.get("file_path", ""))
    if "ideas.md" not in path:
        return None
    content = str(inp.get("content") or inp.get("new_string") or "")
    if "## Idea" not in content:
        return None

    queries: set[str] = set()
    for entry in _iter_transcript_tool_uses(transcript_path):
        if not any(entry["name"].startswith(prefix) for prefix in RESEARCH_MCP_PREFIXES):
            continue
        inp_e = entry.get("input") or {}
        q = inp_e.get("query") or inp_e.get("q") or ""
        if q:
            queries.add(str(q).strip().lower())

    if len(queries) >= 2:
        return None

    return ("Blocked by research-copilot-guard (research-gate): "
            "'## Idea' block being written to .copilot/ideas.md but only "
            f"{len(queries)} distinct paper-retrieval MCP query(ies) recorded "
            "in this session; need ≥2 distinct queries (different topical "
            "keywords). Call arxiv-search / arxivsub-search / google-scholar "
            "/ dblp-bib MCPs first.")


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


def check_pattern_7_no_plan_list(tool_name: str, tool_input: dict[str, Any],
                                 state: dict[str, Any],
                                 transcript_path: str | None) -> str | None:
    """Pattern 7 (plan-list-gate): in Mode B pipeline, every Agent dispatch
    must be preceded by a TaskCreate plan list in the current turn."""
    if tool_name != "Agent":
        return None
    current_state = state.get("current_state", "UNINITIALIZED")
    if current_state not in {"MODE_B_PIPELINE", "PLAN_PUBLISHED",
                             "AWAIT_SUBAGENT_END"}:
        return None
    sub_type = str((tool_input or {}).get("subagent_type", ""))
    if not sub_type.startswith("copilot-"):
        return None
    if not transcript_path:
        return None
    task_count = 0
    for entry in _iter_transcript_tool_uses(transcript_path):
        if entry["name"] == "TaskCreate":
            task_count += 1
    if task_count == 0:
        return ("Blocked by research-copilot-guard (pattern 7): Mode B "
                "pipeline dispatch requires a published TaskCreate plan "
                "list (one task per planned dispatch). Call TaskCreate "
                "for each stage in order before invoking Agent().")
    return None


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
    transcript_path = payload.get("transcript_path")
    for check in (
        check_pattern_1_experiment(tool_name, tool_input),
        check_pattern_3_delegation(tool_name, tool_input, state),
        check_pattern_5_no_memory_read(tool_name, tool_input, transcript_path),
        check_pattern_6_no_research_mcp(tool_name, tool_input, transcript_path),
        check_pattern_7_no_plan_list(tool_name, tool_input, state, transcript_path),
    ):
        if check:
            print(json.dumps(deny(check)))
            return 0
    print(json.dumps(allow()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
