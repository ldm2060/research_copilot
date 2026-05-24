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
