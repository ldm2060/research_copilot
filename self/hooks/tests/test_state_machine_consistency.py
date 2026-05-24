"""Meta-test: STATE_MACHINE dict must match each agent.md state table."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import _copilot_hook_lib as lib

AGENTS_DIR = Path(__file__).resolve().parent.parent.parent / "agents"

AGENT_FILES = {
    "research-copilot":    AGENTS_DIR / "research-copilot.agent.md",
    "copilot-literature":  AGENTS_DIR / "copilot-literature.agent.md",
    "copilot-ideation":    AGENTS_DIR / "copilot-ideation.agent.md",
    "copilot-experiment":  AGENTS_DIR / "copilot-experiment.agent.md",
    "copilot-writer":      AGENTS_DIR / "copilot-writer.agent.md",
    "copilot-polisher":    AGENTS_DIR / "copilot-polisher.agent.md",
    "copilot-reviewer":    AGENTS_DIR / "copilot-reviewer.agent.md",
    "copilot-rebuttal":    AGENTS_DIR / "copilot-rebuttal.agent.md",
}


def _parse_state_table(text: str) -> dict[str, list[str]]:
    """Best-effort: find a markdown table whose header contains 状态 and
    可能的下一状态, parse first-column (state) and last-column (next states).

    Last column format: `[A, B, C]` or `[A]` or `[]`. Whitespace tolerated.
    """
    lines = text.splitlines()
    result: dict[str, list[str]] = {}
    in_table = False
    for line in lines:
        s = line.strip()
        if s.startswith("|") and "状态" in s and "可能的下一状态" in s:
            in_table = True
            continue
        if not in_table:
            continue
        if not s.startswith("|"):
            if result:
                break  # table ended
            continue
        if set(s.replace("|", "").strip()) <= set("-: "):
            continue  # separator row like |---|---|
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 5:
            continue
        state = cols[0]
        m = re.search(r"\[([^\]]*)\]", cols[-1])
        if not m:
            continue
        inner = m.group(1).strip()
        next_states = [x.strip() for x in inner.split(",") if x.strip()] if inner else []
        result[state] = next_states
    return result


@pytest.mark.parametrize("agent,path", list(AGENT_FILES.items()))
def test_state_machine_matches_agent_md(agent: str, path: Path):
    assert path.is_file(), f"agent.md missing: {path}"
    parsed = _parse_state_table(path.read_text(encoding="utf-8"))
    coded = lib.STATE_MACHINE.get(agent, {})
    if not parsed:
        pytest.xfail(f"could not parse state table in {path.name}")
    for state, next_states in parsed.items():
        assert state in coded, (
            f"{agent}: state '{state}' in agent.md but missing from STATE_MACHINE")
        assert set(next_states) == set(coded[state]), (
            f"{agent}: state '{state}' drift — agent.md={next_states} vs "
            f"coded={coded[state]}")
    for state in coded.keys():
        assert state in parsed, (
            f"{agent}: state '{state}' in STATE_MACHINE but missing from agent.md")
