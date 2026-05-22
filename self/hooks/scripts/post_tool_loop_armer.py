"""PostToolUse hook: detect long background experiments and recommend
arming a CronCreate-based self-poll so the main session continues after
notifications. Sets `.copilot/.loop-armed` to avoid duplicate suggestions."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LONGRUN_PATTERNS = (
    re.compile(r"\btrain(\.py|_)"),
    re.compile(r"\bmain\.py\b"),
    re.compile(r"\bai_scientist\b"),
    re.compile(r"\btorchrun\b"),
    re.compile(r"\bdeepspeed\b"),
    re.compile(r"\bexperiments?/"),
    re.compile(r"\baccelerate launch\b"),
)


def should_arm(event: dict) -> bool:
    if event.get("tool_name") != "Bash":
        return False
    inp = event.get("tool_input") or {}
    if not inp.get("run_in_background"):
        return False
    cmd = inp.get("command", "") or ""
    return any(p.search(cmd) for p in LONGRUN_PATTERNS)


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    if not should_arm(event):
        return 0

    flag = Path.cwd() / ".copilot" / ".loop-armed"
    if flag.exists():
        return 0

    sys.stdout.write(
        "[loop-armer] Detected long-running background experiment.\n"
        "[loop-armer] Recommend arming a self-poll so the loop continues across notifications:\n"
        "  CronCreate(cron=\"*/3 * * * *\", prompt=\"<<autonomous-loop>>\", recurring=true, durable=false)\n"
        "[loop-armer] Or the user can paste:\n"
        "  /loop 1m If a background experiment task is still running, check its log tail and decide next step. Otherwise, delete this scheduled task.\n"
        "[loop-armer] On EXECUTING -> END the agent MUST CronDelete the returned id and remove .copilot/.loop-armed.\n"
    )
    sys.stdout.flush()
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
