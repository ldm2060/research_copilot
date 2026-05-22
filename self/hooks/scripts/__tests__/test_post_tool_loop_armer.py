import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _StringIO:
    def __init__(self, s): self._s = s
    def read(self): return self._s


def test_should_arm_when_background_bash_with_train_command():
    from post_tool_loop_armer import should_arm
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "python experiments/run/train.py --epochs 100",
            "run_in_background": True,
        },
    }
    assert should_arm(event) is True


def test_should_not_arm_for_synchronous_bash():
    from post_tool_loop_armer import should_arm
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "python experiments/run/train.py",
            "run_in_background": False,
        },
    }
    assert should_arm(event) is False


def test_should_not_arm_for_non_longrun_command():
    from post_tool_loop_armer import should_arm
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "ls .copilot/",
            "run_in_background": True,
        },
    }
    assert should_arm(event) is False


def test_should_not_arm_for_non_bash_tool():
    from post_tool_loop_armer import should_arm
    event = {
        "tool_name": "Read",
        "tool_input": {"file_path": "x.py"},
    }
    assert should_arm(event) is False


def test_main_skips_when_already_armed(tmp_path, monkeypatch, capsys):
    copilot = tmp_path / ".copilot"
    copilot.mkdir()
    (copilot / ".loop-armed").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "python train.py", "run_in_background": True},
    }
    monkeypatch.setattr("sys.stdin", _StringIO(json.dumps(event)))
    from post_tool_loop_armer import main
    rc = main()
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_main_prints_suggestion_and_marks_armed(tmp_path, monkeypatch, capsys):
    (tmp_path / ".copilot").mkdir()
    monkeypatch.chdir(tmp_path)
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "python experiments/run/train.py", "run_in_background": True},
    }
    monkeypatch.setattr("sys.stdin", _StringIO(json.dumps(event)))
    from post_tool_loop_armer import main
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "[loop-armer]" in out
    assert "CronCreate" in out or "/loop" in out
    assert (tmp_path / ".copilot" / ".loop-armed").exists()
