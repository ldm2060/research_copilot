#!/usr/bin/env python3
"""PostToolUse hook: regenerate skill.json when a SKILL.md under self/skills/ is edited.

Claude Code 2.1.142+ requires every plugin skill to ship a sibling skill.json.
Calling self/scripts/generate-skill-json.py keeps metadata in sync with frontmatter.

Stdin payload (PostToolUse):
  { "tool_name": "...", "tool_input": {...}, "tool_response": {...} }

We approve regardless; this is purely a side-effect hook.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "self" / "skills"
GENERATOR = REPO_ROOT / "self" / "scripts" / "generate-skill-json.py"


def main() -> int:
    raw = sys.stdin.read()
    if not raw:
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
    if not file_path:
        return 0

    try:
        normalized = Path(file_path).resolve()
    except OSError:
        return 0

    try:
        normalized.relative_to(SKILLS_ROOT)
    except ValueError:
        return 0

    if normalized.name != "SKILL.md":
        return 0

    if not GENERATOR.is_file():
        sys.stderr.write(f"[regen_skill_json] generator missing: {GENERATOR}\n")
        return 0

    try:
        subprocess.run(
            [sys.executable, str(GENERATOR), "--root", str(SKILLS_ROOT)],
            check=False,
            capture_output=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(f"[regen_skill_json] failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
