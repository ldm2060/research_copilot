import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _StringIO:
    def __init__(self, s): self._s = s
    def read(self): return self._s


def test_allowlist_suppresses_for_slash_command():
    from user_prompt_dispatch_reminder import should_suppress
    assert should_suppress("/loop 1m check the train log") is True


def test_allowlist_suppresses_for_at_mention():
    from user_prompt_dispatch_reminder import should_suppress
    assert should_suppress("@copilot-ideation 找几个改进点") is True


def test_allowlist_suppresses_for_status_query():
    from user_prompt_dispatch_reminder import should_suppress
    assert should_suppress("what's next?") is True
    assert should_suppress("下一步是什么") is True
    assert should_suppress("看一下当前状态") is True


def test_exec_keyword_detected_for_brainstorm():
    from user_prompt_dispatch_reminder import has_exec_keyword
    assert has_exec_keyword("帮我头脑风暴一下改进方向") is True


def test_exec_keyword_detected_for_experiment():
    from user_prompt_dispatch_reminder import has_exec_keyword
    assert has_exec_keyword("跑一下 baseline 复现") is True


def test_no_exec_keyword_for_chat():
    from user_prompt_dispatch_reminder import has_exec_keyword
    assert has_exec_keyword("你觉得这个方向怎么样?") is False


def test_main_respects_disabled_flag(tmp_path, monkeypatch, capsys):
    (tmp_path / ".copilot").mkdir()
    (tmp_path / ".copilot" / "dispatch-reminder.disabled").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", _StringIO("brainstorm 一下"))
    from user_prompt_dispatch_reminder import main
    rc = main()
    assert rc == 0
    assert capsys.readouterr().out == ""
