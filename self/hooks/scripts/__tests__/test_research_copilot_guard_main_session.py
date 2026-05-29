import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


# ---- M1 delegation gate (main session) ----

def test_m1_blocks_main_session_experiment_bash(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("Bash", {"command": "python train.py --epochs 3"})
    assert msg is not None and "delegate" in msg.lower()


def test_m1_allows_read_only_bash(tmp_path):
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Bash", {"command": "cat results.txt"}) is None


def test_m1_blocks_main_session_research_mcp(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("mcp__arxiv-search__search_arxiv", {"query": "ssms"})
    assert msg is not None and "delegate" in msg.lower()


def test_m1_blocks_write_to_tex(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("Write", {"file_path": "sections/intro.tex"})
    assert msg is not None


def test_m1_blocks_write_to_ideas(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("Edit", {"file_path": ".copilot/ideas.md"})
    assert msg is not None


def test_m1_allows_write_to_state_md(tmp_path):
    """Conductor owns state.md / decisions.md — never denied."""
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Write", {"file_path": ".copilot/state.md"}) is None
    assert check_m1_delegation("Edit", {"file_path": ".copilot/decisions.md"}) is None


def test_m1_allows_unrelated_write(tmp_path):
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Write", {"file_path": "notes/scratch.md"}) is None


def test_m1_allows_lookalike_sections_dir(tmp_path):
    """A dir merely containing 'sections' as a substring is not delegated."""
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Write", {"file_path": "my-sections/notes.md"}) is None
    assert check_m1_delegation("Write", {"file_path": "docs/subsections/a.tex"}) is None


def test_m1_allows_lookalike_references_bib(tmp_path):
    """'references.bib' must match by segment, not substring."""
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Write", {"file_path": "old_references.bib"}) is None


def test_m1_blocks_powershell_experiment(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("PowerShell", {"command": "python train.py"})
    assert msg is not None and "delegate" in msg.lower()


def test_m1_allows_powershell_read_only(tmp_path):
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("PowerShell", {"command": "Get-Content results.txt"}) is None


# ---- M2 task-list gate (main session) ----

def test_m2_blocks_dispatch_without_taskcreate(tmp_path):
    from research_copilot_guard import check_m2_task_list
    t = tmp_path / "s.jsonl"
    _write_transcript(t, [{"type": "tool_use", "name": "Read",
                           "input": {"file_path": ".copilot/state.md"}}])
    msg = check_m2_task_list("Agent", {"subagent_type": "copilot-literature"}, str(t))
    assert msg is not None and "taskcreate" in msg.lower()


def test_m2_allows_dispatch_with_taskcreate(tmp_path):
    from research_copilot_guard import check_m2_task_list
    t = tmp_path / "s.jsonl"
    _write_transcript(t, [{"type": "tool_use", "name": "TaskCreate",
                           "input": {"subject": "S1"}}])
    assert check_m2_task_list("Agent", {"subagent_type": "copilot-literature"}, str(t)) is None


def test_m2_skips_non_copilot_dispatch(tmp_path):
    from research_copilot_guard import check_m2_task_list
    t = tmp_path / "s.jsonl"
    _write_transcript(t, [])
    assert check_m2_task_list("Agent", {"subagent_type": "general-purpose"}, str(t)) is None


def test_m2_fail_open_no_transcript(tmp_path):
    """No transcript_path => cannot inspect => fail-open (allow)."""
    from research_copilot_guard import check_m2_task_list
    assert check_m2_task_list("Agent", {"subagent_type": "copilot-writer"}, "") is None


# ---- main() integration: attribution via agent_id ----

def _run_main(monkeypatch, capsys, payload: dict) -> dict:
    monkeypatch.setattr("sys.stdin", type("S", (), {"read": lambda self: json.dumps(payload)})())
    import importlib, research_copilot_guard
    importlib.reload(research_copilot_guard)
    research_copilot_guard.main()
    return json.loads(capsys.readouterr().out)


def test_main_polices_main_session_train(tmp_path, monkeypatch, capsys):
    """No agent_id => main session => Bash train.py denied."""
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "tool_input": {"command": "python train.py"},
        "transcript_path": str(tmp_path / "x.jsonl"),
    })
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_exempts_copilot_subagent_train(tmp_path, monkeypatch, capsys):
    """agent_id present + copilot-experiment => exempt => allowed."""
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "tool_input": {"command": "python train.py"},
        "transcript_path": str(tmp_path / "x.jsonl"),
        "agent_id": "sa_01", "agent_type": "copilot-experiment",
    })
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_main_fails_open_on_internal_exception(monkeypatch, capsys):
    """An exception inside the decision path must yield allow, never crash."""
    import importlib, research_copilot_guard
    importlib.reload(research_copilot_guard)
    monkeypatch.setattr(research_copilot_guard, "_decide",
                        lambda payload: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("sys.stdin",
                        type("S", (), {"read": lambda self: json.dumps({"tool_name": "Bash"})})())
    research_copilot_guard.main()
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
