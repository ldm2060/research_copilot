import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def test_pattern_7_blocks_agent_without_taskcreate_in_mode_b(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "Read",
         "input": {"file_path": ".copilot/state.md"}},
    ])
    msg = check_pattern_7_no_plan_list(
        tool_name="Agent",
        tool_input={"subagent_type": "copilot-literature"},
        state={"current_state": "MODE_B_PIPELINE"},
        transcript_path=str(transcript),
    )
    assert msg is not None
    assert "pattern 7" in msg.lower()


def test_pattern_7_allows_agent_with_taskcreate_in_mode_b(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "TaskCreate",
         "input": {"subject": "Dispatch copilot-literature",
                   "description": "S1 baseline lock"}},
        {"type": "tool_use", "name": "TaskCreate",
         "input": {"subject": "Dispatch copilot-ideation",
                   "description": "S2 brainstorm"}},
    ])
    msg = check_pattern_7_no_plan_list(
        tool_name="Agent",
        tool_input={"subagent_type": "copilot-literature"},
        state={"current_state": "MODE_B_PIPELINE"},
        transcript_path=str(transcript),
    )
    assert msg is None


def test_pattern_7_skips_in_mode_a(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [])
    msg = check_pattern_7_no_plan_list(
        tool_name="Agent",
        tool_input={"subagent_type": "copilot-literature"},
        state={"current_state": "MODE_A_ROUTING"},
        transcript_path=str(transcript),
    )
    assert msg is None


def test_pattern_7_skips_in_plan_published_with_taskcreate(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "TaskCreate",
         "input": {"subject": "Dispatch copilot-experiment",
                   "description": "S3 Run 1"}},
    ])
    msg = check_pattern_7_no_plan_list(
        tool_name="Agent",
        tool_input={"subagent_type": "copilot-experiment"},
        state={"current_state": "PLAN_PUBLISHED"},
        transcript_path=str(transcript),
    )
    assert msg is None


def test_pattern_7_blocks_in_await_subagent_end_no_tasks(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "Read",
         "input": {"file_path": ".copilot/state.md"}},
    ])
    msg = check_pattern_7_no_plan_list(
        tool_name="Agent",
        tool_input={"subagent_type": "copilot-writer"},
        state={"current_state": "AWAIT_SUBAGENT_END"},
        transcript_path=str(transcript),
    )
    assert msg is not None
    assert "pattern 7" in msg.lower()


def test_pattern_7_skips_for_non_copilot_subagent(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [])
    msg = check_pattern_7_no_plan_list(
        tool_name="Agent",
        tool_input={"subagent_type": "general-purpose"},
        state={"current_state": "MODE_B_PIPELINE"},
        transcript_path=str(transcript),
    )
    assert msg is None


def test_pattern_7_fail_open_no_transcript_path(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    msg = check_pattern_7_no_plan_list(
        tool_name="Agent",
        tool_input={"subagent_type": "copilot-literature"},
        state={"current_state": "MODE_B_PIPELINE"},
        transcript_path="",
    )
    assert msg is None


def test_pattern_7_skips_when_tool_is_not_agent(tmp_path):
    from research_copilot_guard import check_pattern_7_no_plan_list
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [])
    msg = check_pattern_7_no_plan_list(
        tool_name="Read",
        tool_input={"file_path": ".copilot/literature.md"},
        state={"current_state": "MODE_B_PIPELINE"},
        transcript_path=str(transcript),
    )
    assert msg is None
