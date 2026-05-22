#!/usr/bin/env python3
"""PreToolUse hook: block Edit/Write to build outputs (dist/) and submodules (third_party/).

These directories are derived state:
  - dist/         is the output of scripts/build_copilot_workspace.py
  - third_party/  is git submodules — edits should happen in upstream repos

Stdin payload contains tool_name + tool_input. We deny when the edited path
falls inside either directory; otherwise approve.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROTECTED_DIRS = (
    REPO_ROOT / "dist",
    REPO_ROOT / "third_party",
)
WATCHED_TOOLS = {"Edit", "Write", "NotebookEdit"}


def allow() -> dict:
    return {"hookSpecificOutput": {"permissionDecision": "allow"}}


def deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }


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

    tool_name = payload.get("tool_name", "")
    if tool_name not in WATCHED_TOOLS:
        print(json.dumps(allow()))
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = str(
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("notebook_path")
        or ""
    )
    if not file_path:
        print(json.dumps(allow()))
        return 0

    try:
        normalized = Path(file_path).resolve()
    except OSError:
        print(json.dumps(allow()))
        return 0

    for protected in PROTECTED_DIRS:
        try:
            normalized.relative_to(protected)
        except ValueError:
            continue
        reason = (
            f"Blocked edit to {protected.name}/: this directory is derived state. "
            + (
                "Run `python scripts/build_copilot_workspace.py` to regenerate dist/."
                if protected.name == "dist"
                else "Edit the upstream submodule repo, then `git submodule update --remote`."
            )
        )
        print(json.dumps(deny(reason)))
        return 0

    print(json.dumps(allow()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
