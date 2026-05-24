"""SubagentStop hook: HANDOFF freshness (HARD), STATE_OUTPUT 6-field (SOFT),
state-machine no-jump (SOFT).

Decision contract:
  - block: {"decision": "block", "reason": "..."}
  - allow: {"hookSpecificOutput": {"permissionDecision": "allow"}}

3-strike fuse: if CHECK 1 fails 3 times for the same (agent, file), the hook
releases the 3rd attempt with [HARD/RELEASE] to avoid lockout.

Falls open via safe_main().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import _copilot_hook_lib as lib


HANDOFF_FILES: dict[str, list[str]] = {
    "research-copilot":    ["state.md", "decisions.md"],
    "copilot-literature":  ["literature.md"],
    "copilot-ideation":    ["ideas.md"],
    "copilot-experiment":  ["experiments.md"],
    # writer/polisher/reviewer/rebuttal write handoff.md (append-only multi-writer)
    # — not subject to HARD freshness; SOFT checks only.
    "copilot-writer":    [],
    "copilot-polisher":  [],
    "copilot-reviewer":  [],
    "copilot-rebuttal":  [],
}


def real_main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps(lib.allow_decision()))
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps(lib.allow_decision()))
        return 0

    agent = lib.detect_active_agent(payload.get("transcript_path", ""))
    if not lib.is_copilot_agent(agent):
        print(json.dumps(lib.allow_decision()))
        return 0

    workspace = Path.cwd()

    if lib.env_guard_disabled():
        lib.log_violation(workspace, "INFO", "DISABLED", agent,
                          "SubagentStop guard bypassed by env var")
        print(json.dumps(lib.allow_decision()))
        return 0

    if lib.override_match(workspace, agent, "skip-handoff-check"):
        lib.log_violation(workspace, "INFO", "OVERRIDE", agent,
                          "skip-handoff-check active")
        print(json.dumps(lib.allow_decision()))
        return 0

    # CHECK 1 (HARD) — Task 12
    # CHECK 3+4 (SOFT) — Task 14
    print(json.dumps(lib.allow_decision()))
    return 0


if __name__ == "__main__":
    raise SystemExit(lib.safe_main(real_main))
