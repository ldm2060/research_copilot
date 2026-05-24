"""Shared helpers for copilot_* hooks. Stateless.

Encodes the OWNED matrix (PIPELINE-OS §8) and per-agent state machines.
Provides JSON I/O, parsers, log writers, and a fail-open safe_main wrapper.

All hooks depending on this lib MUST wrap their main() with safe_main() so
any exception yields an `allow` decision rather than trapping the user.
"""
from __future__ import annotations

import json
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
