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


class TestHandoffFreshness:
    def test_missing_file_blocks(self, monkeypatch, workspace, fixtures_dir):
        # Pre-populate snapshot so we trigger HARD_FAIL (not SOFT_FAIL first-boot path)
        lib.write_snapshot(workspace, {"literature.md": None})
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d.get("decision") == "block"
        assert "literature.md" in d["reason"] or "HANDOFF" in d["reason"]

    def test_stale_handoff_blocks(self, monkeypatch, workspace, fixtures_dir, handoff_writer):
        f = workspace / ".copilot" / "literature.md"
        old = "2026-05-23T00:00:00Z"
        handoff_writer(f, last_updated=old)
        lib.write_snapshot(workspace, {"literature.md": old})
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d.get("decision") == "block"

    def test_fresh_handoff_allows(self, monkeypatch, workspace, fixtures_dir, handoff_writer):
        f = workspace / ".copilot" / "literature.md"
        handoff_writer(f, last_updated="2026-05-24T10:00:00Z")
        lib.write_snapshot(workspace, {"literature.md": "2026-05-23T00:00:00Z"})
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestFuse:
    def test_strikes_1_and_2_block(self, monkeypatch, workspace, fixtures_dir):
        lib.write_snapshot(workspace, {"literature.md": None})
        for _ in range(2):
            d = _run(monkeypatch,
                     _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                     workspace)
            assert d.get("decision") == "block"
        assert lib.counter_get(workspace, "copilot-literature", "literature.md") == 2

    def test_strike_3_releases(self, monkeypatch, workspace, fixtures_dir):
        lib.write_snapshot(workspace, {"literature.md": None})
        for _ in range(2):
            _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert lib.counter_get(workspace, "copilot-literature", "literature.md") == 0
        log = (workspace / ".copilot" / "__violations.log").read_text(encoding="utf-8")
        assert "RELEASE" in log

    def test_pass_resets_counter(self, monkeypatch, workspace, fixtures_dir, handoff_writer):
        lib.write_snapshot(workspace, {"literature.md": None})
        _run(monkeypatch,
             _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
             workspace)
        assert lib.counter_get(workspace, "copilot-literature", "literature.md") == 1
        f = workspace / ".copilot" / "literature.md"
        handoff_writer(f, last_updated="2026-05-24T10:00:00Z")
        lib.write_snapshot(workspace, {"literature.md": "2026-05-23T00:00:00Z"})
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert lib.counter_get(workspace, "copilot-literature", "literature.md") == 0


class TestFirstBoot:
    def test_no_snapshot_fresh_handoff_passes(self, monkeypatch, workspace,
                                                fixtures_dir, handoff_writer):
        s = workspace / ".copilot" / ".session_snapshot.json"
        if s.exists():
            s.unlink()
        f = workspace / ".copilot" / "literature.md"
        handoff_writer(f, last_updated="2026-05-24T10:00:00Z")
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_no_snapshot_no_handoff_soft_not_hard(self, monkeypatch, workspace, fixtures_dir):
        d = _run(monkeypatch,
                 _stop_payload(str(fixtures_dir / "transcript_copilot_literature.jsonl")),
                 workspace)
        assert d["hookSpecificOutput"]["permissionDecision"] == "allow"
        log = (workspace / ".copilot" / "__violations.log").read_text(encoding="utf-8")
        assert "NO-SNAPSHOT" in log
