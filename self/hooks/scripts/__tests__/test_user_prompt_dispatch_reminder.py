import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _StringIO:
    def __init__(self, s): self._s = s
    def read(self): return self._s


def test_no_suppression_for_status_query(tmp_path, monkeypatch, capsys):
    """Standing orders fire even on 'what's next' / 下一步 (no suppression)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", _StringIO("下一步"))
    from user_prompt_dispatch_reminder import main
    assert main() == 0
    assert "conductor" in capsys.readouterr().out.lower()


def test_no_suppression_for_slash_or_at(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", _StringIO("/loop 1m check"))
    from user_prompt_dispatch_reminder import main
    assert main() == 0
    assert capsys.readouterr().out.strip() != ""


def test_main_respects_disabled_flag(tmp_path, monkeypatch, capsys):
    (tmp_path / ".copilot").mkdir()
    (tmp_path / ".copilot" / "dispatch-reminder.disabled").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", _StringIO("anything at all"))
    from user_prompt_dispatch_reminder import main
    rc = main()
    assert rc == 0
    assert capsys.readouterr().out == ""
