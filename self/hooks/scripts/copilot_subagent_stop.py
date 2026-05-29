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
    # research-copilot retired as a sub-agent (now the main-session conductor);
    # state.md/decisions.md freshness is a CONDUCTOR-PROTOCOL standing order,
    # not SubagentStop-enforced (the main session never fires SubagentStop).
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


def _file_handoff_last_updated(workspace: Path, filename: str) -> str | None:
    f = workspace / ".copilot" / filename
    if not f.is_file():
        return None
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    h = lib.extract_handoff(text)
    return h.get("last_updated") if h else None


def _iso_strictly_later(current: str | None, snapshot: str | None) -> bool:
    """ISO 8601 strings sort lexicographically. None snapshot ('first boot')
    is treated as 'any current value counts as later'."""
    if not current:
        return False
    if snapshot is None:
        return True
    return current > snapshot


def _check_handoff_freshness(workspace: Path, agent: str
                              ) -> tuple[str, str, str | None]:
    """Returns (status, message, file_that_failed).
    status in {PASS, HARD_FAIL, SOFT_FAIL}.

    HARD_FAIL = stale/missing handoff AND a snapshot file exists to compare against.
    SOFT_FAIL = no snapshot file exists at all (first boot / hook reenabled).
    PASS     = all owned files have fresh handoff blocks.
    """
    files = HANDOFF_FILES.get(agent, [])
    if not files:
        return "PASS", "", None
    snapshot_path = workspace / ".copilot" / lib.SNAPSHOT_NAME
    snapshot_exists = snapshot_path.is_file()
    snapshot = lib.read_snapshot(workspace)
    for fname in files:
        cur = _file_handoff_last_updated(workspace, fname)
        snap = snapshot.get(fname)
        if _iso_strictly_later(cur, snap):
            continue
        msg = (f"{agent} did not update .copilot/{fname} __HANDOFF__ "
               f"block this session. Append/refresh the block and "
               f"re-emit STATE_OUTPUT before exiting.")
        return ("SOFT_FAIL" if not snapshot_exists else "HARD_FAIL"), msg, fname
    return "PASS", "", None


def _read_last_assistant_text(transcript_path: str) -> str:
    """Return the concatenated text content of the most recent assistant
    message in the transcript JSONL. Empty string if none found.
    """
    if not transcript_path:
        return ""
    p = Path(transcript_path)
    if not p.is_file():
        return ""
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines[-100:]):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("role") != "assistant":
            continue
        chunks: list[str] = []
        content = entry.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(item.get("text", ""))
        elif isinstance(content, str):
            chunks.append(content)
        if chunks:
            return "\n".join(chunks)
    return ""


def _run_soft_checks(workspace: Path, agent: str, transcript: str) -> None:
    """CHECK 3 (STATE_OUTPUT 6 fields) + CHECK 4 (state transition legality).
    Both are SOFT — append to violations.log but never block."""
    text = _read_last_assistant_text(transcript)
    so = lib.extract_state_output(text)
    missing = lib.state_output_missing_fields(so)
    if missing:
        if so is None:
            lib.log_violation(workspace, "SOFT", "WARN", agent,
                              "STATE_OUTPUT block absent from final reply")
        else:
            lib.log_violation(workspace, "SOFT", "WARN", agent,
                              f"STATE_OUTPUT missing fields: {missing}")
    if so:
        prev, curr = so.get("Previous"), so.get("Current")
        if prev and curr and not lib.is_transition_legal(agent, prev, curr):
            lib.log_violation(workspace, "SOFT", "WARN", agent,
                              f"transition {prev} -> {curr} not in allowed "
                              f"set {lib.STATE_MACHINE.get(agent, {}).get(prev, [])}")


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

    # CHECK 1 — HARD freshness with 3-strike fuse, or SOFT degrade at first boot
    status, fail_msg, fail_file = _check_handoff_freshness(workspace, agent)
    if status == "HARD_FAIL":
        n = lib.counter_inc(workspace, agent, fail_file)
        if n < 3:
            lib.log_violation(workspace, "HARD", "BLOCK", agent,
                              f"{fail_msg} (strike {n}/3)", file=fail_file)
            print(json.dumps(lib.block_decision(fail_msg)))
            return 0
        lib.log_violation(workspace, "HARD", "RELEASE", agent,
                          "3-strike fuse triggered, releasing", file=fail_file)
        lib.counter_reset(workspace, agent, fail_file)
        print(json.dumps(lib.allow_decision()))
        return 0

    if status == "SOFT_FAIL":
        lib.log_violation(workspace, "INFO", "NO-SNAPSHOT", agent,
                          f"{fail_msg} (degraded: no .session_snapshot.json)",
                          file=fail_file)

    if status == "PASS":
        lib.counter_reset_all(workspace, agent)

    # CHECK 3+4 SOFT — never block
    _run_soft_checks(workspace, agent, payload.get("transcript_path", ""))
    print(json.dumps(lib.allow_decision()))
    return 0


if __name__ == "__main__":
    raise SystemExit(lib.safe_main(real_main))
