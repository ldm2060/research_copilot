import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_extract_handoff_block_returns_block_text_when_present():
    from session_start_memory_injector import extract_handoff_block
    text = (
        "# heading\n"
        "some content\n"
        "\n"
        "## __HANDOFF__\n"
        "- last_updated: 2026-05-23T00:00:00Z\n"
        "- written_by: research-copilot\n"
        "- key_facts:\n"
        "  - locked baseline = Foo\n"
        "- next_owner: copilot-ideation\n"
    )
    block = extract_handoff_block(text)
    assert block is not None
    assert "last_updated" in block
    assert "key_facts" in block
    assert "locked baseline = Foo" in block


def test_extract_handoff_block_returns_none_when_absent():
    from session_start_memory_injector import extract_handoff_block
    assert extract_handoff_block("just a body\nno trailer\n") is None


def test_extract_last_n_lines_returns_tail():
    from session_start_memory_injector import extract_last_n_lines
    text = "\n".join(f"line {i}" for i in range(1, 31)) + "\n"
    result = extract_last_n_lines(text, n=5)
    assert result == "line 26\nline 27\nline 28\nline 29\nline 30"


def test_main_prints_summary_when_copilot_dir_has_handoff_blocks(tmp_path, monkeypatch, capsys):
    copilot = tmp_path / ".copilot"
    copilot.mkdir()
    (copilot / "state.md").write_text(
        "# state\n\n## __HANDOFF__\n"
        "- last_updated: 2026-05-23T00:00:00Z\n"
        "- written_by: research-copilot\n"
        "- key_facts:\n"
        "  - stage cursor at S2\n"
        "- next_owner: copilot-ideation\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    from session_start_memory_injector import main
    rc = main()
    assert rc == 0
    captured = capsys.readouterr().out
    assert "[memory-injector]" in captured
    assert "stage cursor at S2" in captured


def test_main_skips_when_no_copilot_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    from session_start_memory_injector import main
    rc = main()
    assert rc == 0
    captured = capsys.readouterr().out
    assert "not initialized" in captured.lower() or "skipping" in captured.lower()
