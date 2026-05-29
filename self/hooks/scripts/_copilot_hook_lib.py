"""Shared helpers for copilot_* hooks. Stateless.

Encodes the OWNED matrix (PIPELINE-OS §8) and per-agent state machines.
Provides JSON I/O, parsers, log writers, and a fail-open safe_main wrapper.

All hooks depending on this lib MUST wrap their main() with safe_main() so
any exception yields an `allow` decision rather than trapping the user.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any


COPILOT_AGENTS = frozenset([
    "research-copilot",
    "copilot-literature",
    "copilot-ideation",
    "copilot-experiment",
    "copilot-writer",
    "copilot-polisher",
    "copilot-reviewer",
    "copilot-rebuttal",
])


def is_copilot_agent(name: str | None) -> bool:
    return name in COPILOT_AGENTS


def detect_active_agent(transcript_path: str) -> str | None:
    """Scan transcript JSONL in reverse, return most recent subagent_type.

    Handles two formats:
      1. Flat: {"subagent_type": "...", ...}
      2. Wrapped: {"role": ..., "metadata": {"subagent_type": "..."}, ...}
    """
    if not transcript_path:
        return None
    p = Path(transcript_path)
    if not p.is_file():
        return None
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
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


COPILOT_SUBAGENT_PREFIX = "copilot-"


def is_main_session(payload: dict) -> bool:
    """True iff this PreToolUse call originates from the MAIN session.

    Authoritative per Claude Code hooks docs: `agent_id` is present ONLY
    inside a sub-agent call, so its ABSENCE means the main thread. Any
    ambiguity (missing/empty agent_id) resolves to main — conservative,
    because a false 'main' over-applies the guard (recoverable) whereas a
    false 'subagent' silently exempts the main session (defeats the guard).
    """
    return not payload.get("agent_id")


def is_exempt_subagent(payload: dict) -> bool:
    """True iff a copilot-* sub-agent made this call (runs freely)."""
    if is_main_session(payload):
        return False
    return str(payload.get("agent_type") or "").startswith(COPILOT_SUBAGENT_PREFIX)


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------

import fnmatch


def normalize_path(s: str, workspace: Path | None = None) -> str:
    """Normalize a path for matching: lowercase, forward-slash, relative-if-possible.

    - Empty string returns empty string.
    - If `workspace` is given AND the path resolves inside workspace,
      returns the relative path under workspace.
    - Otherwise returns lowercased forward-slashed absolute path.
    """
    if not s:
        return ""
    if workspace is not None:
        try:
            rel = Path(s).resolve().relative_to(workspace.resolve())
            return str(rel).replace("\\", "/").lower()
        except (ValueError, OSError):
            pass
    return s.replace("\\", "/").lower()


def glob_match(path: str, pattern: str) -> bool:
    """Case-insensitive single-segment glob match.

    Uses `pathlib.PurePosixPath.match` semantics — `*` matches one path
    segment, NOT across `/`. So `sections/*.tex` matches `sections/foo.tex`
    but NOT `sections/sub/foo.tex`.

    Both `path` and `pattern` are lowercased and forward-slashed before
    matching, so callers don't have to pre-normalize.
    """
    from pathlib import PurePosixPath
    p = path.replace("\\", "/").lower()
    g = pattern.replace("\\", "/").lower()
    if not g:
        return p == g
    return PurePosixPath(p).match(g)


# ---------------------------------------------------------------------------
# OWNED matrix (PIPELINE-OS §8) and ownership predicates
# ---------------------------------------------------------------------------

OWNED: dict[str, list[str]] = {
    "research-copilot": [
        ".copilot/state.md",
        ".copilot/decisions.md",
        ".copilot/pipelines/*.md",
    ],
    "copilot-literature": [".copilot/literature.md"],
    "copilot-ideation": [
        ".copilot/ideas.md",
        ".copilot/pipelines/*-s2-*.md",
    ],
    "copilot-experiment": [
        ".copilot/experiments.md",
        ".copilot/pipelines/*-s3-*.md",
    ],
    "copilot-writer": [
        "sections/*.tex",
        "references.bib",
        ".copilot/handoff.md",
    ],
    "copilot-polisher": [
        "sections/*.tex",
        ".copilot/handoff.md",
    ],
    "copilot-reviewer": [
        ".copilot/reviews/round-*.md",
        ".copilot/handoff.md",
    ],
    "copilot-rebuttal": [".copilot/handoff.md"],
}

HANDOFF_APPEND_ONLY_AGENTS = frozenset([
    "copilot-writer", "copilot-polisher",
    "copilot-reviewer", "copilot-rebuttal",
])


def is_owned(agent: str, path: str) -> bool:
    """True iff `agent` is allowed to write `path` per PIPELINE-OS §8."""
    if agent not in OWNED:
        return False
    p = path.replace("\\", "/").lower()
    return any(glob_match(p, pat) for pat in OWNED[agent])


_KNOWN_ARTIFACT_GLOBS = [
    ".copilot/state.md",
    ".copilot/literature.md",
    ".copilot/ideas.md",
    ".copilot/experiments.md",
    ".copilot/decisions.md",
    ".copilot/handoff.md",
    ".copilot/reviews/*.md",
    ".copilot/pipelines/*.md",
    "sections/*.tex",
    "references.bib",
]


def is_known_research_artifact(path: str) -> bool:
    """True iff `path` is one of the artifacts PIPELINE-OS §8 governs.
    Paths outside this universe are unconditionally allowed for any agent."""
    p = path.replace("\\", "/").lower()
    return any(glob_match(p, pat) for pat in _KNOWN_ARTIFACT_GLOBS)


# ---------------------------------------------------------------------------
# STATE_MACHINE — transcribed from each *.agent.md state table
# ---------------------------------------------------------------------------

STATE_MACHINE: dict[str, dict[str, list[str]]] = {
    "research-copilot": {
        "UNINITIALIZED":        ["DIAGNOSED"],
        "DIAGNOSED":            ["MODE_A_ROUTING", "MODE_B_PIPELINE", "PAUSED"],
        "MODE_A_ROUTING":       ["AWAIT_SUBAGENT_END"],
        "MODE_B_PIPELINE":      ["PLAN_PUBLISHED"],
        "PLAN_PUBLISHED":       ["AWAIT_SUBAGENT_END"],
        "AWAIT_SUBAGENT_END":   ["DIAGNOSED", "BACK_EDGE_TRIGGERED", "PAUSED", "PLAN_PUBLISHED", "END"],
        "BACK_EDGE_TRIGGERED":  ["MODE_A_ROUTING", "MODE_B_PIPELINE", "PAUSED"],
        "PAUSED":               ["END"],
        "END":                  [],
    },
    "copilot-literature": {
        "UNINITIALIZED":          ["SCANNING"],
        "SCANNING":               ["BASELINE_LOCKED", "RELATED_WORK_AUGMENTED"],
        "BASELINE_LOCKED":        ["RELATED_WORK_AUGMENTED", "END"],
        "RELATED_WORK_AUGMENTED": ["END"],
        "END":                    [],
    },
    "copilot-ideation": {
        "UNINITIALIZED":         ["CONTEXT_LOADED", "END"],
        "CONTEXT_LOADED":        ["INTERVIEWING"],
        "INTERVIEWING":          ["PREFERENCES_LOCKED"],
        "PREFERENCES_LOCKED":    ["CANDIDATES_GENERATED"],
        "CANDIDATES_GENERATED":  ["ANALOGIES_ADDED"],
        "ANALOGIES_ADDED":       ["FILTERED"],
        "FILTERED":              ["AWAITING_SELECTION"],
        "AWAITING_SELECTION":    ["DIRECTION_SELECTED", "PREFERENCES_LOCKED"],
        "DIRECTION_SELECTED":    ["VALIDATED"],
        "VALIDATED":             ["END"],
        "END":                   [],
    },
    "copilot-experiment": {
        "UNINITIALIZED":   ["CONTEXT_LOADED"],
        "CONTEXT_LOADED":  ["DESIGN_READY"],
        "DESIGN_READY":    ["APPROVED"],
        "APPROVED":        ["EXECUTING"],
        "EXECUTING":       ["COMPLETED"],
        "COMPLETED":       ["VERIFIED"],
        "VERIFIED":        ["JUDGED"],
        "JUDGED":          ["END", "EXECUTING"],
        "END":             [],
    },
    "copilot-writer": {
        "UNINITIALIZED": ["PLAN_DRAFT", "EXPAND", "SHORTEN", "TRANSLATE", "CAPTION"],
        "PLAN_DRAFT":    ["DRAFTING"],
        "DRAFTING":      ["REVIEW_SELF", "END"],
        "EXPAND":        ["REVIEW_SELF", "END"],
        "SHORTEN":       ["REVIEW_SELF", "END"],
        "TRANSLATE":     ["END"],
        "CAPTION":       ["END"],
        "REVIEW_SELF":   ["END"],
        "END":           [],
    },
    "copilot-polisher": {
        "UNINITIALIZED": ["POLISHING"],
        "POLISHING":     ["DE_AI"],
        "DE_AI":         ["VALIDATED"],
        "VALIDATED":     ["END"],
        "END":           [],
    },
    "copilot-reviewer": {
        "UNINITIALIZED":   ["SIMULATE_REVIEW"],
        "SIMULATE_REVIEW": ["EXTRACT_GAPS"],
        "EXTRACT_GAPS":    ["WRITE_ROUND"],
        "WRITE_ROUND":     ["END"],
        "END":             [],
    },
    "copilot-rebuttal": {
        "UNINITIALIZED":   ["PARSE_REVIEWS"],
        "PARSE_REVIEWS":   ["DRAFT_RESPONSE"],
        "DRAFT_RESPONSE":  ["RE_REVIEW", "END"],
        "RE_REVIEW":       ["END"],
        "END":             [],
    },
}


def is_transition_legal(agent: str, previous: str, current: str) -> bool:
    """True if `previous -> current` appears in agent's table.
    Returns True (no false warns) for unknown agent OR unknown source state."""
    sm = STATE_MACHINE.get(agent)
    if sm is None:
        return True
    allowed = sm.get(previous)
    if allowed is None:
        return True
    return current in allowed


# ---------------------------------------------------------------------------
# Parsers (HANDOFF + STATE_OUTPUT)
# ---------------------------------------------------------------------------

_HANDOFF_HEADER = "## __HANDOFF__"
_STATE_OUTPUT_RE = re.compile(
    r"\[STATE_OUTPUT\](.*?)\[/STATE_OUTPUT\]",
    re.DOTALL,
)
REQUIRED_STATE_OUTPUT_FIELDS = (
    "Previous", "Current", "Action completed", "Capability gate",
    "Evidence", "Next allowed",
)


def extract_handoff(text: str) -> dict[str, Any] | None:
    """Parse the LAST `## __HANDOFF__` block in `text`.

    Returns dict with keys last_updated, written_by, key_facts (list), next_owner;
    None if no block present. Missing individual fields are None / [].
    """
    if not text:
        return None
    idx = text.rfind(_HANDOFF_HEADER)
    if idx < 0:
        return None
    body = text[idx + len(_HANDOFF_HEADER):].strip()
    end = body.find("\n## ")
    if end >= 0:
        body = body[:end]
    result: dict[str, Any] = {
        "last_updated": None,
        "written_by": None,
        "key_facts": [],
        "next_owner": None,
    }
    in_key_facts = False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("- last_updated:"):
            result["last_updated"] = s.split(":", 1)[1].strip() or None
            in_key_facts = False
        elif s.startswith("- written_by:"):
            result["written_by"] = s.split(":", 1)[1].strip() or None
            in_key_facts = False
        elif s.startswith("- next_owner:"):
            result["next_owner"] = s.split(":", 1)[1].strip() or None
            in_key_facts = False
        elif s.startswith("- key_facts:"):
            in_key_facts = True
        elif in_key_facts and s.startswith("- "):
            result["key_facts"].append(s[2:].strip())
        elif in_key_facts and s.startswith("-"):
            result["key_facts"].append(s[1:].strip())
        else:
            in_key_facts = False
    return result


def extract_state_output(text: str) -> dict[str, str] | None:
    """Parse the LAST [STATE_OUTPUT]...[/STATE_OUTPUT] block.

    Missing fields are absent from the dict (NOT present as None).
    Returns None if no block found at all.
    """
    if not text:
        return None
    matches = _STATE_OUTPUT_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    result: dict[str, str] = {}
    for line in body.splitlines():
        s = line.strip()
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        result[k.strip()] = v.strip()
    return result or None


def state_output_missing_fields(so: dict[str, str] | None) -> list[str]:
    """Return REQUIRED_STATE_OUTPUT_FIELDS missing from `so`.
    If so is None (no block at all), all 6 are reported."""
    if so is None:
        return list(REQUIRED_STATE_OUTPUT_FIELDS)
    return [f for f in REQUIRED_STATE_OUTPUT_FIELDS if f not in so]


# ---------------------------------------------------------------------------
# Runtime state files (under .copilot/)
# ---------------------------------------------------------------------------

SNAPSHOT_NAME = ".session_snapshot.json"
COUNTER_NAME = ".subagent_stop_block_count.json"
VIOLATIONS_NAME = "__violations.log"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")


def _copilot_dir(workspace: Path) -> Path:
    d = workspace / ".copilot"
    d.mkdir(exist_ok=True)
    return d


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def read_snapshot(workspace: Path) -> dict[str, Any]:
    return _read_json(_copilot_dir(workspace) / SNAPSHOT_NAME)


def write_snapshot(workspace: Path, data: dict[str, Any]) -> None:
    _write_json(_copilot_dir(workspace) / SNAPSHOT_NAME, data)


def counter_read(workspace: Path) -> dict[str, dict[str, dict[str, Any]]]:
    return _read_json(_copilot_dir(workspace) / COUNTER_NAME)


def counter_inc(workspace: Path, agent: str, file: str) -> int:
    data = counter_read(workspace)
    bucket = data.setdefault(agent, {}).setdefault(
        file, {"count": 0, "last_block_at": None, "reset_at": None})
    bucket["count"] = int(bucket.get("count", 0)) + 1
    bucket["last_block_at"] = _now_iso()
    _write_json(_copilot_dir(workspace) / COUNTER_NAME, data)
    return bucket["count"]


def counter_get(workspace: Path, agent: str, file: str) -> int:
    return counter_read(workspace).get(agent, {}).get(file, {}).get("count", 0)


def counter_reset(workspace: Path, agent: str, file: str) -> None:
    data = counter_read(workspace)
    if agent in data and file in data[agent]:
        data[agent][file]["count"] = 0
        data[agent][file]["reset_at"] = _now_iso()
        _write_json(_copilot_dir(workspace) / COUNTER_NAME, data)


def counter_reset_all(workspace: Path, agent: str) -> None:
    data = counter_read(workspace)
    if agent in data:
        for bucket in data[agent].values():
            bucket["count"] = 0
            bucket["reset_at"] = _now_iso()
        _write_json(_copilot_dir(workspace) / COUNTER_NAME, data)


def log_violation(workspace: Path, sev: str, kind: str, agent: str | None,
                  detail: str, file: str | None = None) -> None:
    """Append one JSONL record to .copilot/__violations.log."""
    rec = {"ts": _now_iso(), "sev": sev, "kind": kind,
           "agent": agent, "detail": detail}
    if file is not None:
        rec["file"] = file
    log = _copilot_dir(workspace) / VIOLATIONS_NAME
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

OVERRIDE_NAME = ".guard_override"
_OVERRIDE_LINE_RE = re.compile(
    r"^\s*(?P<agent>[\w-]+)\s*:\s*(?P<directive>skip-[\w-]+)\s+until\s+(?P<until>\S+)\s*$"
)


def env_guard_disabled() -> bool:
    """True iff the global kill-switch env var COPILOT_HOOK_GUARD is 'off'."""
    return os.environ.get("COPILOT_HOOK_GUARD", "").strip().lower() == "off"


def override_match(workspace: Path, agent: str, directive: str) -> bool:
    """True iff `.copilot/.guard_override` has an active entry for this
    agent + directive (or `skip-all` for the same agent).

    Comments (#-prefixed) and unparseable lines are ignored. Expired
    entries (now >= until) are ignored.
    """
    f = _copilot_dir(workspace) / OVERRIDE_NAME
    if not f.is_file():
        return False
    try:
        content = f.read_text(encoding="utf-8")
    except OSError:
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _OVERRIDE_LINE_RE.match(line)
        if not m or m.group("agent") != agent:
            continue
        d = m.group("directive")
        if d != "skip-all" and d != directive:
            continue
        try:
            until = datetime.datetime.fromisoformat(
                m.group("until").replace("Z", "+00:00"))
        except ValueError:
            continue
        if until.tzinfo is None:
            until = until.replace(tzinfo=datetime.timezone.utc)
        if now < until:
            return True
    return False


# ---------------------------------------------------------------------------
# Decision builders + safe_main
# ---------------------------------------------------------------------------

def allow_decision() -> dict[str, Any]:
    return {"hookSpecificOutput": {"permissionDecision": "allow"}}


def deny_decision(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }


def block_decision(reason: str) -> dict[str, Any]:
    """SubagentStop block decision — agent resumes with `reason` appended to context."""
    return {"decision": "block", "reason": reason}


def safe_main(real_main) -> int:
    """Wrap a hook's main(): exceptions yield `allow` to stdout, never trap user.

    Hook scripts MUST call this from their `if __name__ == "__main__"` block:
        if __name__ == "__main__":
            raise SystemExit(lib.safe_main(real_main))
    """
    try:
        return int(real_main() or 0)
    except SystemExit:
        raise
    except Exception:
        sys.stderr.write(traceback.format_exc())
        try:
            sys.stdout.write(json.dumps(allow_decision()) + "\n")
            sys.stdout.flush()
        except Exception:
            pass
        return 0
