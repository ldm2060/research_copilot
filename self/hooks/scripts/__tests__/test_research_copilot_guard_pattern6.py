import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def test_pattern_6_flags_idea_block_write_without_research_mcp(tmp_path):
    from research_copilot_guard import check_pattern_6_no_research_mcp
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "Read",
         "input": {"file_path": str(tmp_path / ".copilot" / "ideas.md")}},
    ])
    msg = check_pattern_6_no_research_mcp(
        tool_name="Write",
        tool_input={"file_path": str(tmp_path / ".copilot" / "ideas.md"),
                    "content": "## Idea 1: Quantum diffusion\n..."},
        transcript_path=str(transcript),
    )
    assert msg is not None
    assert "research-gate" in msg.lower()


def test_pattern_6_allows_when_two_distinct_arxiv_queries_present(tmp_path):
    from research_copilot_guard import check_pattern_6_no_research_mcp
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "mcp__arxiv-search__search_arxiv",
         "input": {"query": "sparse attention transformer"}},
        {"type": "tool_use", "name": "mcp__arxiv-search__search_arxiv",
         "input": {"query": "linear attention efficient"}},
    ])
    msg = check_pattern_6_no_research_mcp(
        tool_name="Write",
        tool_input={"file_path": str(tmp_path / ".copilot" / "ideas.md"),
                    "content": "## Idea 1: New attention\n..."},
        transcript_path=str(transcript),
    )
    assert msg is None


def test_pattern_6_blocks_when_only_one_distinct_query(tmp_path):
    from research_copilot_guard import check_pattern_6_no_research_mcp
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [
        {"type": "tool_use", "name": "mcp__arxiv-search__search_arxiv",
         "input": {"query": "sparse attention"}},
        {"type": "tool_use", "name": "mcp__arxiv-search__search_arxiv",
         "input": {"query": "sparse attention"}},
    ])
    msg = check_pattern_6_no_research_mcp(
        tool_name="Write",
        tool_input={"file_path": str(tmp_path / ".copilot" / "ideas.md"),
                    "content": "## Idea 1\n..."},
        transcript_path=str(transcript),
    )
    assert msg is not None


def test_pattern_6_skips_when_not_idea_block_write(tmp_path):
    from research_copilot_guard import check_pattern_6_no_research_mcp
    transcript = tmp_path / "session.jsonl"
    _write_transcript(transcript, [])
    msg = check_pattern_6_no_research_mcp(
        tool_name="Write",
        tool_input={"file_path": str(tmp_path / ".copilot" / "experiments.md"),
                    "content": "## Run 1\n..."},
        transcript_path=str(transcript),
    )
    assert msg is None
