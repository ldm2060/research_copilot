"""Tests for snapshot-writing side-effect of session_start_memory_injector."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import _copilot_hook_lib as lib


def _run_injector(workspace: Path) -> tuple[str, int]:
    script = Path(__file__).resolve().parent.parent / "scripts" / "session_start_memory_injector.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout, proc.returncode


class TestSnapshotWriting:
    def test_writes_for_existing_handoff(self, workspace, handoff_writer):
        f = workspace / ".copilot" / "literature.md"
        handoff_writer(f, last_updated="2026-05-24T10:00:00Z",
                       written_by="copilot-literature")
        stdout, rc = _run_injector(workspace)
        assert rc == 0
        snap = lib.read_snapshot(workspace)
        assert snap.get("literature.md") == "2026-05-24T10:00:00Z"

    def test_overwrites_each_run(self, workspace, handoff_writer):
        f = workspace / ".copilot" / "literature.md"
        handoff_writer(f, last_updated="2026-05-24T08:00:00Z")
        _run_injector(workspace)
        f.write_text("\n## __HANDOFF__\n- last_updated: 2026-05-24T12:00:00Z\n",
                     encoding="utf-8")
        _run_injector(workspace)
        snap = lib.read_snapshot(workspace)
        assert snap.get("literature.md") == "2026-05-24T12:00:00Z"

    def test_snapshot_file_created(self, workspace, handoff_writer):
        f = workspace / ".copilot" / "literature.md"
        handoff_writer(f, last_updated="2026-05-24T10:00:00Z")
        _run_injector(workspace)
        assert (workspace / ".copilot" / ".session_snapshot.json").is_file()


import datetime


class TestViolationsSummary:
    def _write_log(self, workspace, records):
        log = workspace / ".copilot" / "__violations.log"
        log.write_text("\n".join(json.dumps(r) for r in records) + "\n",
                       encoding="utf-8")

    def test_empty_log_no_summary(self, workspace, handoff_writer):
        handoff_writer(workspace / ".copilot" / "literature.md",
                       last_updated="2026-05-24T10:00:00Z")
        stdout, rc = _run_injector(workspace)
        assert "Last 24h" not in stdout

    def test_recent_blocks_summarized(self, workspace, handoff_writer):
        handoff_writer(workspace / ".copilot" / "literature.md",
                       last_updated="2026-05-24T10:00:00Z")
        now = datetime.datetime.now(datetime.timezone.utc)
        recent = (now - datetime.timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        self._write_log(workspace, [
            {"ts": recent, "sev": "HARD", "kind": "BLOCK", "agent": "copilot-literature", "detail": "x"},
            {"ts": recent, "sev": "HARD", "kind": "BLOCK", "agent": "copilot-literature", "detail": "y"},
            {"ts": recent, "sev": "HARD", "kind": "RELEASE", "agent": "copilot-literature", "detail": "z"},
            {"ts": recent, "sev": "SOFT", "kind": "WARN", "agent": "copilot-experiment", "detail": "w"},
        ])
        stdout, rc = _run_injector(workspace)
        assert "Last 24h" in stdout
        assert "2 HARD" in stdout
        assert "1 SOFT" in stdout

    def test_old_entries_ignored(self, workspace, handoff_writer):
        handoff_writer(workspace / ".copilot" / "literature.md",
                       last_updated="2026-05-24T10:00:00Z")
        now = datetime.datetime.now(datetime.timezone.utc)
        old = (now - datetime.timedelta(hours=48)).isoformat().replace("+00:00", "Z")
        self._write_log(workspace, [
            {"ts": old, "sev": "HARD", "kind": "BLOCK", "agent": "x", "detail": "old"},
        ])
        stdout, rc = _run_injector(workspace)
        assert "1 HARD" not in stdout


def test_injects_conductor_protocol(tmp_path, monkeypatch, capsys):
    import session_start_memory_injector as inj
    (tmp_path / ".copilot").mkdir()
    # Seed a real __HANDOFF__ block so `blocks` is non-empty and main() reaches
    # the injection point (it does NOT inject on the early "no blocks" return).
    (tmp_path / ".copilot" / "state.md").write_text(
        "## __HANDOFF__\n- last_updated: 2026-05-24T10:00:00Z\n"
        "- written_by: conductor\n- key_facts:\n  - S1 in progress\n"
        "- next_owner: (none)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    # Point the protocol lookup at a temp file. NOTE: this test runs the injector
    # IN-PROCESS (not via subprocess like the other tests in this file) precisely
    # so conductor_protocol_path can be monkeypatched — do not "fix" it to subprocess.
    proto = tmp_path / "CONDUCTOR-PROTOCOL.md"
    proto.write_text("# Conductor Protocol\nYou are the conductor.\n", encoding="utf-8")
    monkeypatch.setattr(inj, "conductor_protocol_path", lambda: proto)
    inj.main()
    out = capsys.readouterr().out
    assert "You are the conductor" in out
