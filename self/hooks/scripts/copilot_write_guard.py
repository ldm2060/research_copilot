"""PreToolUse hook: enforce owned-file partition (PIPELINE-OS §8).

When the active sub-agent is copilot-*, denies Write/Edit to non-owned
artifacts. Paths outside the research-artifact universe (.copilot/,
sections/*.tex, references.bib) are unconditionally allowed.

handoff.md special case (Task 10) is added in the next commit.

Falls open on any exception via safe_main().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import _copilot_hook_lib as lib


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
                          "guard bypassed by env var")
        print(json.dumps(lib.allow_decision()))
        return 0

    if lib.override_match(workspace, agent, "skip-owned-check"):
        lib.log_violation(workspace, "INFO", "OVERRIDE", agent,
                          "skip-owned-check active")
        print(json.dumps(lib.allow_decision()))
        return 0

    file_path = str((payload.get("tool_input") or {}).get("file_path", ""))
    if not file_path:
        print(json.dumps(lib.allow_decision()))
        return 0

    norm = lib.normalize_path(file_path, workspace=workspace)

    # handoff.md special case: append-only for the 4 multi-writers.
    if norm.endswith(".copilot/handoff.md"):
        tool_name = payload.get("tool_name", "")
        if agent in lib.HANDOFF_APPEND_ONLY_AGENTS:
            if tool_name == "Write":
                lib.log_violation(workspace, "HARD", "DENY", agent,
                                  "Write (overwrite) to handoff.md; "
                                  "use Edit to append", file=norm)
                msg = ("Blocked by copilot-write-guard: handoff.md is "
                       "append-only. Use Edit to add a new block, not Write.")
                print(json.dumps(lib.deny_decision(msg)))
                return 0
            # Edit allowed for these 4 agents — fall through to owned check
        else:
            lib.log_violation(workspace, "HARD", "DENY", agent,
                              "agent has no write right to handoff.md",
                              file=norm)
            msg = (f"Blocked by copilot-write-guard: {agent} is not an "
                   f"owner of handoff.md.")
            print(json.dumps(lib.deny_decision(msg)))
            return 0

    if lib.is_owned(agent, norm):
        print(json.dumps(lib.allow_decision()))
        return 0

    if lib.is_known_research_artifact(norm):
        lib.log_violation(workspace, "HARD", "DENY", agent,
                          "writing to non-owned artifact", file=norm)
        msg = (f"Blocked by copilot-write-guard: {agent} may not write "
               f"{norm}. See PIPELINE-OS §8.")
        print(json.dumps(lib.deny_decision(msg)))
        return 0

    print(json.dumps(lib.allow_decision()))
    return 0


if __name__ == "__main__":
    raise SystemExit(lib.safe_main(real_main))
