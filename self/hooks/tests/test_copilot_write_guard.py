"""Tests for copilot_write_guard.py (PreToolUse, Rule 2)."""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

import copilot_write_guard as guard
import _copilot_hook_lib as lib


def _run(monkeypatch, payload: dict, workspace: Path) -> dict:
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))
    monkeypatch.chdir(workspace)
    out = StringIO()
    monkeypatch.setattr("sys.stdout", out)
    guard.real_main()
    return json.loads(out.getvalue().strip().splitlines()[-1])


class TestScope:
    def test_main_agent_allowed(self, monkeypatch, workspace, fixtures_dir, payload_builder):
        p = payload_builder("Write",
                            {"file_path": str(workspace / ".copilot" / "state.md")},
                            str(fixtures_dir / "transcript_main_only.jsonl"))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_unknown_agent_allowed(self, monkeypatch, workspace, tmp_path, payload_builder):
        t = tmp_path / "trans.jsonl"
        t.write_text('{"role":"assistant","metadata":{"subagent_type":"general-purpose"}}\n')
        p = payload_builder("Write",
                            {"file_path": str(workspace / ".copilot" / "state.md")},
                            str(t))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestOwnedAllow:
    def test_literature_writes_own(self, monkeypatch, workspace, fixtures_dir, payload_builder):
        p = payload_builder("Write",
                            {"file_path": str(workspace / ".copilot" / "literature.md")},
                            str(fixtures_dir / "transcript_copilot_literature.jsonl"))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_unrelated_scratch_allowed(self, monkeypatch, workspace, fixtures_dir, payload_builder):
        p = payload_builder("Write",
                            {"file_path": str(workspace / "scratch" / "note.txt")},
                            str(fixtures_dir / "transcript_copilot_literature.jsonl"))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestForbiddenDeny:
    def test_literature_writing_ideas_denied(self, monkeypatch, workspace, fixtures_dir, payload_builder):
        p = payload_builder("Write",
                            {"file_path": str(workspace / ".copilot" / "ideas.md")},
                            str(fixtures_dir / "transcript_copilot_literature.jsonl"))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "deny"
        log = (workspace / ".copilot" / "__violations.log").read_text(encoding="utf-8")
        assert "HARD" in log and "DENY" in log

    def test_literature_editing_state_denied(self, monkeypatch, workspace, fixtures_dir, payload_builder):
        p = payload_builder("Edit",
                            {"file_path": str(workspace / ".copilot" / "state.md")},
                            str(fixtures_dir / "transcript_copilot_literature.jsonl"))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestOverride:
    def test_skip_owned_check_allows(self, monkeypatch, workspace, fixtures_dir, payload_builder):
        (workspace / ".copilot" / ".guard_override").write_text(
            "copilot-literature: skip-owned-check until 2099-01-01T00:00:00Z\n",
            encoding="utf-8")
        p = payload_builder("Write",
                            {"file_path": str(workspace / ".copilot" / "ideas.md")},
                            str(fixtures_dir / "transcript_copilot_literature.jsonl"))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_env_var_off_allows(self, monkeypatch, workspace, fixtures_dir, payload_builder):
        monkeypatch.setenv("COPILOT_HOOK_GUARD", "off")
        p = payload_builder("Write",
                            {"file_path": str(workspace / ".copilot" / "ideas.md")},
                            str(fixtures_dir / "transcript_copilot_literature.jsonl"))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestSafeMain:
    def test_empty_stdin_falls_open(self, monkeypatch, workspace):
        monkeypatch.setattr("sys.stdin", StringIO(""))
        monkeypatch.chdir(workspace)
        out = StringIO()
        monkeypatch.setattr("sys.stdout", out)
        guard.real_main()
        d = json.loads(out.getvalue().strip().splitlines()[-1])
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestHandoffSpecial:
    def _writer_transcript(self, tmp_path: Path) -> str:
        t = tmp_path / "writer.jsonl"
        t.write_text('{"role":"assistant","metadata":{"subagent_type":"copilot-writer"}}\n')
        return str(t)

    def _ideation_transcript(self, tmp_path: Path) -> str:
        t = tmp_path / "ideation.jsonl"
        t.write_text('{"role":"assistant","metadata":{"subagent_type":"copilot-ideation"}}\n')
        return str(t)

    def test_writer_edit_handoff_allowed(self, monkeypatch, workspace, tmp_path, payload_builder):
        p = payload_builder("Edit",
                            {"file_path": str(workspace / ".copilot" / "handoff.md")},
                            self._writer_transcript(tmp_path))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_writer_write_handoff_denied(self, monkeypatch, workspace, tmp_path, payload_builder):
        p = payload_builder("Write",
                            {"file_path": str(workspace / ".copilot" / "handoff.md")},
                            self._writer_transcript(tmp_path))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "append" in d["hookSpecificOutput"]["permissionDecisionReason"].lower()

    def test_ideation_writing_handoff_denied(self, monkeypatch, workspace, tmp_path, payload_builder):
        p = payload_builder("Edit",
                            {"file_path": str(workspace / ".copilot" / "handoff.md")},
                            self._ideation_transcript(tmp_path))
        d = _run(monkeypatch, p, workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "deny"
