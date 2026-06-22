"""Research Copilot Workflow Guard hook (PreToolUse).

Polices the MAIN SESSION acting as conductor. The main session must delegate
domain work to rc-* / copilot-* research executors and may only dispatch the
executor that matches the active Trellis task node's status and kind. Research
executors (rc-* / copilot-*) running inside a sub-agent call are exempt.

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
    "mcp__research-scholar__scholar_search",
    "mcp__research-scholar__bibtex",
    "mcp__research-scholar__scholar_metadata",
)
# Conductor-owned artifacts: the main session MAY write these.
CONDUCTOR_OWNED_ARTIFACTS = (".copilot/state.md", ".copilot/decisions.md")
# Delegated artifact files the main session must NOT write. Matched segment-anchored
# (see _path_matches) so 'references.bib' does NOT match 'old_references.bib'. The
# sections/*.tex case is handled separately by a path-segment check.
DELEGATED_ARTIFACT_FILES = (".copilot/ideas.md", ".copilot/experiments.md",
                            ".copilot/literature.md", "references.bib")
READ_ONLY_TOOLS = ("Read", "Grep", "Glob", "TaskCreate", "TaskUpdate",
                   "TaskList", "TaskGet", "Skill", "AskUserQuestion")
COPILOT_SUBAGENT_PREFIX = "copilot-"
RC_SUBAGENT_PREFIX = "rc-"
RESEARCH_EXECUTOR_PREFIXES = (COPILOT_SUBAGENT_PREFIX, RC_SUBAGENT_PREFIX)
KIND_EXECUTOR = {
    "literature": "rc-literature",
    "ideation": "rc-ideation",
    "experiment": "rc-experiment",
    "writing": "rc-writer",
    "polish": "rc-polisher",
    "review": "rc-reviewer",
    "rebuttal": "rc-rebuttal",
}
COPILOT_TO_RC = {
    "copilot-plan": "rc-plan",
    "copilot-literature": "rc-literature",
    "copilot-ideation": "rc-ideation",
    "copilot-experiment": "rc-experiment",
    "copilot-writer": "rc-writer",
    "copilot-polisher": "rc-polisher",
    "copilot-reviewer": "rc-reviewer",
    "copilot-rebuttal": "rc-rebuttal",
    "copilot-verify": "rc-verify",
    "copilot-update-spec": "rc-update-spec",
}


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
    return _is_research_executor(str(payload.get("agent_type") or ""))


def is_read_only(command: str) -> bool:
    stripped = command.strip()
    return any(stripped.startswith(prefix) for prefix in READ_ONLY_PREFIXES)


def _norm(path: str) -> str:
    return str(path).replace("\\", "/")


def _path_matches(path: str, target: str) -> bool:
    """True iff `path` equals `target` or ends with `/target` (segment-anchored).
    Prevents substring false-positives like 'references.bib' matching
    'old_references.bib', or '.copilot/ideas.md' matching an unrelated path."""
    p = _norm(path)
    return p == target or p.endswith("/" + target)


def _canonical_executor(name: str) -> str:
    return COPILOT_TO_RC.get(name, name)


def _is_research_executor(name: str) -> bool:
    return name.startswith(RESEARCH_EXECUTOR_PREFIXES)


def _runtime_dir() -> Path:
    return Path.cwd() / ".research" / ".runtime"


def _load_active_task() -> dict[str, Any] | None:
    active_path = _runtime_dir() / "active-task"
    if not active_path.is_file():
        return None
    task_id = active_path.read_text(encoding="utf-8", errors="replace").strip()
    if not task_id:
        return None
    task_path = Path.cwd() / ".research" / "tasks" / task_id / "task.json"
    if not task_path.is_file():
        return None
    try:
        task = json.loads(task_path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    return task if isinstance(task, dict) else None


def _expected_executor(task: dict[str, Any]) -> str | None:
    status = task.get("status")
    kind = task.get("kind")
    if status == "planning":
        return "rc-plan"
    if status == "verify":
        return "rc-verify"
    if status == "completed":
        return "rc-update-spec"
    if status == "in_progress":
        return KIND_EXECUTOR.get(str(kind))
    return None


def _log_event(event: dict[str, Any]) -> None:
    runtime = _runtime_dir()
    runtime.mkdir(parents=True, exist_ok=True)
    path = runtime / "enforcement-events.jsonl"
    base = {
        "platform": "claude-code",
        "mode": "hard",
    }
    base.update(event)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(base, ensure_ascii=False, sort_keys=True) + "\n")


def _deny_leaf_work(event_name: str, tool_name: str, default_executor: str, reason: str) -> str:
    task = _load_active_task()
    if task is None:
        _log_event({
            "event": "main_attempted_leaf_work_without_active_node",
            "tool": tool_name,
            "decision": "deny",
        })
        return ("Blocked by research-copilot-guard (Trellis claim gate): the conductor "
                "cannot perform research-domain leaf work without an active task node. "
                "Create a Trellis task node first with `rc task create --kind <kind> --title \"<title>\"`.")

    expected = _expected_executor(task) or default_executor
    _log_event({
        "event": event_name,
        "taskId": task.get("id"),
        "status": task.get("status"),
        "kind": task.get("kind"),
        "tool": tool_name,
        "decision": "deny",
        "expectedExecutor": expected,
    })
    return (f"Blocked by research-copilot-guard (Trellis claim gate): active task "
            f"{task.get('id')} is status={task.get('status')} kind={task.get('kind')}. "
            f"Legal executor is {expected}. The conductor must not do this leaf work inline. "
            f"{reason}")


def check_m1_delegation(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """M1 delegation gate: deny main-session execution-class work."""
    # Experiment scripts via shell.
    if tool_name in ("Bash", "PowerShell"):
        command = str((tool_input or {}).get("command", ""))
        if not command or is_read_only(command):
            return None
        if any(kw in command for kw in EXPERIMENT_KEYWORDS) or EXPERIMENT_REGEX.search(command):
            return _deny_leaf_work(
                "main_attempted_experiment",
                tool_name,
                "rc-experiment",
                "Delegate experiment work to the legal task executor.",
            )
        return None
    # Paper-retrieval MCP tools.
    if any(tool_name.startswith(p) for p in RESEARCH_MCP_PREFIXES):
        return _deny_leaf_work(
            "main_attempted_literature_search",
            tool_name,
            "rc-literature",
            "Delegate literature search to the legal task executor.",
        )
    # Writes to delegated research artifacts (segment-anchored, not substring).
    if tool_name in ("Write", "Edit"):
        path = _norm((tool_input or {}).get("file_path", ""))
        if any(_path_matches(path, owned) for owned in CONDUCTOR_OWNED_ARTIFACTS):
            return None  # conductor owns state.md / decisions.md
        segments = path.split("/")
        is_sections_tex = "sections" in segments and path.endswith(".tex")
        if is_sections_tex or any(_path_matches(path, f) for f in DELEGATED_ARTIFACT_FILES):
            return _deny_leaf_work(
                "main_attempted_artifact_write",
                tool_name,
                "rc-writer",
                "Delegate artifact writing to the legal task executor.",
            )
    return None


def check_m2_task_list(tool_name: str, tool_input: dict[str, Any],
                       transcript_path: str | None) -> str | None:
    """M2 task-list gate: deny research executor dispatch without Trellis legality."""
    if tool_name != "Agent":
        return None
    sub_type = str((tool_input or {}).get("subagent_type", ""))
    if not _is_research_executor(sub_type):
        return None

    task = _load_active_task()
    if task is None:
        _log_event({
            "event": "dispatch_without_active_node",
            "tool": "Agent",
            "subagent_type": sub_type,
            "decision": "deny",
        })
        return ("Blocked by research-copilot-guard (Trellis dispatch gate): "
                "research executor dispatch requires an active .research/tasks/<id> task node. "
                "Create a Trellis task node first with `rc task create --kind <kind> --title \"<title>\"`.")

    expected = _expected_executor(task)
    actual = _canonical_executor(sub_type)
    if expected and actual == expected:
        return None

    _log_event({
        "event": "executor_mismatch",
        "taskId": task.get("id"),
        "status": task.get("status"),
        "kind": task.get("kind"),
        "tool": "Agent",
        "subagent_type": sub_type,
        "expectedExecutor": expected,
        "decision": "deny",
    })
    if expected is None:
        return (f"Blocked by research-copilot-guard (Trellis dispatch gate): active task "
                f"{task.get('id')} has unsupported status={task.get('status')} kind={task.get('kind')}. "
                f"Cannot dispatch research executors until task metadata is repaired.")
    return (f"Blocked by research-copilot-guard (Trellis dispatch gate): active task "
            f"{task.get('id')} is status={task.get('status')} kind={task.get('kind')}. "
            f"Legal executor is {expected}; cannot dispatch {sub_type}.")


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
