"""Validate that the installer guard matcher covers every research MCP prefix
declared in the Python guard.

This is a static consistency check — no filesystem or hook runtime needed.
"""
import re
import sys
from pathlib import Path

# Make the guard importable from self/hooks/scripts/
_scripts_dir = Path(__file__).resolve().parents[1]
_self_dir = _scripts_dir.parents[1]  # self/
sys.path.insert(0, str(_scripts_dir))
sys.path.insert(0, str(_self_dir))

import research_copilot_guard as guard  # noqa: E402
import install  # noqa: E402


def _matcher_patterns() -> list[str]:
    """Return the individual alternation segments from the pipe-delimited matcher."""
    return install.RESEARCH_COPILOT_GUARD_MATCHER.split("|")


def test_matcher_covers_all_research_scholar_prefixes():
    """Every mcp__research-scholar__* prefix in the guard must be matched by
    the installer's PreToolUse matcher regex."""
    patterns = _matcher_patterns()
    # Collect all guard prefixes that start with mcp__research-scholar__
    scholar_prefixes = [
        p for p in guard.RESEARCH_MCP_PREFIXES
        if p.startswith("mcp__research-scholar__")
    ]
    assert scholar_prefixes, "guard should declare at least one mcp__research-scholar__ prefix"

    for prefix in scholar_prefixes:
        # The matcher uses regex alternation; find the pattern that could match this prefix
        matched = False
        for pat in patterns:
            try:
                if re.fullmatch(pat, prefix):
                    matched = True
                    break
            except re.error:
                continue
        assert matched, (
            f"Guard prefix {prefix!r} is not covered by any matcher pattern. "
            f"Matcher patterns: {patterns}"
        )


def test_matcher_covers_all_guard_mcp_prefixes():
    """Every MCP prefix in the guard must be matched by at least one pattern
    in the installer's PreToolUse matcher."""
    patterns = _matcher_patterns()
    for prefix in guard.RESEARCH_MCP_PREFIXES:
        matched = False
        for pat in patterns:
            try:
                if re.fullmatch(pat, prefix):
                    matched = True
                    break
            except re.error:
                continue
        assert matched, (
            f"Guard prefix {prefix!r} is not covered by any matcher pattern. "
            f"Matcher patterns: {patterns}"
        )
