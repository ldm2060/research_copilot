"""Shared helpers for copilot_* hooks. Stateless.

Encodes the OWNED matrix (PIPELINE-OS §8) and per-agent state machines.
Provides JSON I/O, parsers, log writers, and a fail-open safe_main wrapper.

All hooks depending on this lib MUST wrap their main() with safe_main() so
any exception yields an `allow` decision rather than trapping the user.
"""
from __future__ import annotations

import json
import re
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
        "MODE_B_PIPELINE":      ["AWAIT_SUBAGENT_END"],
        "AWAIT_SUBAGENT_END":   ["DIAGNOSED", "BACK_EDGE_TRIGGERED", "PAUSED", "END"],
        "BACK_EDGE_TRIGGERED":  ["MODE_A_ROUTING", "PAUSED"],
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
