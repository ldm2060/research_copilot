"""Shared pytest fixtures for copilot hook tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".copilot").mkdir()
    return tmp_path


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


def make_payload(tool_name: str, tool_input: dict, transcript_path: str,
                 stop_hook_active: bool = False) -> dict:
    return {"tool_name": tool_name, "tool_input": tool_input,
            "transcript_path": transcript_path,
            "stop_hook_active": stop_hook_active}


@pytest.fixture
def payload_builder():
    return make_payload


def write_handoff_block(file: Path, last_updated: str,
                        written_by: str = "copilot-test",
                        key_facts: list[str] | None = None) -> None:
    facts = key_facts or ["(placeholder)"]
    body = "\n".join([
        "",
        "## __HANDOFF__",
        f"- last_updated: {last_updated}",
        f"- written_by: {written_by}",
        "- key_facts:",
        *(f"  - {f}" for f in facts),
        "- next_owner: (none)",
        "",
    ])
    if file.exists():
        file.write_text(file.read_text() + body, encoding="utf-8")
    else:
        file.write_text(body, encoding="utf-8")


@pytest.fixture
def handoff_writer():
    return write_handoff_block
