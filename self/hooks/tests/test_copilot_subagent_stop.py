"""Tests for copilot_subagent_stop.py (SubagentStop)."""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

import copilot_subagent_stop as guard
import _copilot_hook_lib as lib


def _run(monkeypatch, payload: dict, workspace: Path) -> dict:
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))
    monkeypatch.chdir(workspace)
    out = StringIO()
    monkeypatch.setattr("sys.stdout", out)
    guard.real_main()
    return json.loads(out.getvalue().strip().splitlines()[-1])


def _stop_payload(transcript_path: str, stop_hook_active: bool = False) -> dict:
    return {"transcript_path": transcript_path, "stop_hook_active": stop_hook_active}


class TestScope:
    def test_main_agent_allowed(self, monkeypatch, workspace, fixtures_dir):
        d = _run(monkeypatch, _stop_payload(str(fixtures_dir / "transcript_main_only.jsonl")), workspace)
        assert "decision" not in d
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_non_copilot_agent_allowed(self, monkeypatch, workspace, tmp_path):
        t = tmp_path / "trans.jsonl"
        t.write_text('{"role":"assistant","metadata":{"subagent_type":"general-purpose"}}\n')
        d = _run(monkeypatch, _stop_payload(str(t)), workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestOverride:
    def test_env_off_allows(self, monkeypatch, workspace, fixtures_dir):
        monkeypatch.setenv("COPILOT_HOOK_GUARD", "off")
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_skip_handoff_check_allows(self, monkeypatch, workspace, fixtures_dir):
        (workspace / ".copilot" / ".guard_override").write_text(
            "copilot-literature: skip-handoff-check until 2099-01-01T00:00:00Z\n",
            encoding="utf-8")
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"
