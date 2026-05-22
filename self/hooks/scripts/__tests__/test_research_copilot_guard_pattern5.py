import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def test_pattern_5_flags_write_to_ideas_without_prior_copilot_read(tmp_path):
    from research_copilot_guard import check_pattern_5_no_memory_read
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
    ])
    msg = check_pattern_5_no_memory_read(
        tool_name="Write",
        tool_input={"file_path": str(tmp_path / ".copilot" / "ideas.md"),
                    "content": "## Idea 1\n..."},
        transcript_path=str(transcript),
    )
    assert msg is not None
    assert "memory-gate" in msg.lower()


def test_pattern_5_allows_when_prior_copilot_read_present(tmp_path):
    from research_copilot_guard import check_pattern_5_no_memory_read
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "Read",
         "input": {"file_path": str(tmp_path / ".copilot" / "ideas.md")}},
    ])
    msg = check_pattern_5_no_memory_read(
        tool_name="Write",
        tool_input={"file_path": str(tmp_path / ".copilot" / "ideas.md"),
                    "content": "## Idea 1\n..."},
        transcript_path=str(transcript),
    )
    assert msg is None


def test_pattern_5_skips_when_target_is_not_copilot_artifact(tmp_path):
    from research_copilot_guard import check_pattern_5_no_memory_read
    msg = check_pattern_5_no_memory_read(
        tool_name="Write",
        tool_input={"file_path": "sections/method.tex", "content": "..."},
        transcript_path=str(tmp_path / "missing.jsonl"),
    )
    assert msg is None
