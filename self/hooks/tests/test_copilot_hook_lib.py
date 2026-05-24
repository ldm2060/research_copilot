"""Tests for _copilot_hook_lib."""
from __future__ import annotations

from pathlib import Path

import pytest

import _copilot_hook_lib as lib


class TestDetectActiveAgent:
    def test_main_only_returns_none(self, fixtures_dir):
        p = fixtures_dir / "transcript_main_only.jsonl"
        assert lib.detect_active_agent(str(p)) is None

    def test_copilot_literature(self, fixtures_dir):
        p = fixtures_dir / "transcript_copilot_literature.jsonl"
        assert lib.detect_active_agent(str(p)) == "copilot-literature"

    def test_copilot_experiment(self, fixtures_dir):
        p = fixtures_dir / "transcript_copilot_experiment_complete.jsonl"
        assert lib.detect_active_agent(str(p)) == "copilot-experiment"

    def test_missing_path_returns_none(self):
        assert lib.detect_active_agent("") is None
        assert lib.detect_active_agent("/nonexistent/path") is None


class TestScopePredicates:
    def test_is_copilot_agent_positive(self):
        for n in ["copilot-literature", "copilot-ideation", "copilot-experiment",
                  "copilot-writer", "copilot-polisher", "copilot-reviewer",
                  "copilot-rebuttal", "research-copilot"]:
            assert lib.is_copilot_agent(n) is True

    def test_is_copilot_agent_negative(self):
        for n in [None, "", "general-purpose", "Explore", "code-reviewer", "main"]:
            assert lib.is_copilot_agent(n) is False


class TestPathNormalize:
    def test_backslash_to_forward(self):
        assert lib.normalize_path("D:\\article\\.copilot\\state.md") == \
               "d:/article/.copilot/state.md"

    def test_already_forward(self):
        assert lib.normalize_path(".copilot/state.md") == ".copilot/state.md"

    def test_relative_workspace(self, workspace):
        f = workspace / ".copilot" / "state.md"
        assert lib.normalize_path(str(f), workspace=workspace) == ".copilot/state.md"

    def test_empty(self):
        assert lib.normalize_path("") == ""


class TestGlobMatch:
    def test_exact(self):
        assert lib.glob_match(".copilot/state.md", ".copilot/state.md") is True

    def test_star(self):
        assert lib.glob_match(".copilot/reviews/round-3.md",
                              ".copilot/reviews/round-*.md") is True

    def test_no_match(self):
        assert lib.glob_match(".copilot/ideas.md", ".copilot/state.md") is False

    def test_s2_pipelines(self):
        assert lib.glob_match(".copilot/pipelines/2026-05-24-S2-ideation-round-1.md",
                              ".copilot/pipelines/*-s2-*.md") is True
        assert lib.glob_match(".copilot/pipelines/2026-05-24-S3-experiment-1.md",
                              ".copilot/pipelines/*-s2-*.md") is False

    def test_star_does_not_cross_slash(self):
        # Tightened semantics: `*` is single-segment only
        assert lib.glob_match("sections/sub/foo.tex", "sections/*.tex") is False
        assert lib.glob_match(".copilot/reviews/round-2/sub/x.md",
                              ".copilot/reviews/round-*.md") is False

    def test_star_single_segment_still_matches(self):
        assert lib.glob_match("sections/intro.tex", "sections/*.tex") is True
        assert lib.glob_match(".copilot/pipelines/2026-05-24-S2-ideation.md",
                              ".copilot/pipelines/*-s2-*.md") is True

    def test_empty_pattern(self):
        assert lib.glob_match("", "") is True
        assert lib.glob_match("anything", "") is False


class TestOwnedMatrix:
    def test_literature_owns_literature(self):
        assert lib.is_owned("copilot-literature", ".copilot/literature.md") is True

    def test_literature_does_not_own_ideas(self):
        assert lib.is_owned("copilot-literature", ".copilot/ideas.md") is False

    def test_ideation_owns_s2_pipelines(self):
        assert lib.is_owned("copilot-ideation",
                            ".copilot/pipelines/2026-05-24-s2-ideation.md") is True

    def test_experiment_owns_s3_pipelines(self):
        assert lib.is_owned("copilot-experiment",
                            ".copilot/pipelines/2026-05-24-s3-exp.md") is True

    def test_writer_owns_sections_tex(self):
        assert lib.is_owned("copilot-writer", "sections/intro.tex") is True

    def test_writer_owns_handoff(self):
        assert lib.is_owned("copilot-writer", ".copilot/handoff.md") is True

    def test_unknown_agent(self):
        assert lib.is_owned("unknown", ".copilot/state.md") is False

    def test_research_copilot_state(self):
        assert lib.is_owned("research-copilot", ".copilot/state.md") is True
        assert lib.is_owned("research-copilot", ".copilot/decisions.md") is True


class TestIsKnownArtifact:
    def test_dot_copilot(self):
        assert lib.is_known_research_artifact(".copilot/state.md") is True
        assert lib.is_known_research_artifact(".copilot/handoff.md") is True

    def test_sections(self):
        assert lib.is_known_research_artifact("sections/intro.tex") is True

    def test_references_bib(self):
        assert lib.is_known_research_artifact("references.bib") is True

    def test_unrelated_scratch(self):
        assert lib.is_known_research_artifact("scratch/note.txt") is False
        assert lib.is_known_research_artifact("README.md") is False


class TestStateMachine:
    def test_literature_machine_present(self):
        sm = lib.STATE_MACHINE["copilot-literature"]
        assert sm["UNINITIALIZED"] == ["SCANNING"]
        assert "END" in sm["BASELINE_LOCKED"]

    def test_experiment_machine_present(self):
        sm = lib.STATE_MACHINE["copilot-experiment"]
        assert sm["UNINITIALIZED"] == ["CONTEXT_LOADED"]
        assert "END" in sm["JUDGED"]

    def test_all_8_agents_have_machines(self):
        for agent in lib.COPILOT_AGENTS:
            assert agent in lib.STATE_MACHINE, f"missing state machine for {agent}"

    def test_transition_legal(self):
        assert lib.is_transition_legal(
            "copilot-literature", "UNINITIALIZED", "SCANNING") is True

    def test_transition_illegal(self):
        assert lib.is_transition_legal(
            "copilot-experiment", "UNINITIALIZED", "END") is False

    def test_transition_unknown_agent_allowed(self):
        assert lib.is_transition_legal("unknown", "X", "Y") is True

    def test_transition_unknown_state_allowed(self):
        assert lib.is_transition_legal(
            "copilot-literature", "NEW_STATE", "END") is True


class TestExtractHandoff:
    def test_full_block(self):
        text = """# Some artifact

Body.

## __HANDOFF__
- last_updated: 2026-05-24T10:30:00Z
- written_by: copilot-literature
- key_facts:
  - locked baseline: 1706.03762
  - 3 nearest prior works
- next_owner: copilot-ideation
"""
        h = lib.extract_handoff(text)
        assert h is not None
        assert h["last_updated"] == "2026-05-24T10:30:00Z"
        assert h["written_by"] == "copilot-literature"
        assert h["next_owner"] == "copilot-ideation"
        assert "locked baseline: 1706.03762" in h["key_facts"]

    def test_no_block(self):
        assert lib.extract_handoff("# header only\nno handoff block") is None

    def test_empty(self):
        assert lib.extract_handoff("") is None

    def test_block_without_last_updated(self):
        h = lib.extract_handoff("## __HANDOFF__\n- written_by: x\n")
        assert h is not None
        assert h.get("last_updated") is None


class TestExtractStateOutput:
    def test_full_block(self):
        text = """prose
[STATE_OUTPUT]
Previous: SCANNING
Current: BASELINE_LOCKED
Action completed: Locked baseline
Capability gate: passed
Evidence: literature.md:42
Next allowed: [RELATED_WORK_AUGMENTED, END]
Transition reason: 2 MCP queries
[/STATE_OUTPUT]
trailing"""
        so = lib.extract_state_output(text)
        assert so["Previous"] == "SCANNING"
        assert so["Current"] == "BASELINE_LOCKED"
        assert so["Capability gate"] == "passed"

    def test_missing_block(self):
        assert lib.extract_state_output("no block") is None

    def test_missing_fields(self):
        text = "[STATE_OUTPUT]\nPrevious: X\nCurrent: Y\n[/STATE_OUTPUT]"
        so = lib.extract_state_output(text)
        assert so["Previous"] == "X"
        assert "Capability gate" not in so

    def test_required_fields_missing_returns_list(self):
        so = lib.extract_state_output("[STATE_OUTPUT]\nPrevious: X\nCurrent: Y\n[/STATE_OUTPUT]")
        missing = lib.state_output_missing_fields(so)
        assert set(missing) == {"Action completed", "Capability gate", "Evidence", "Next allowed"}

    def test_required_fields_complete(self):
        so = {
            "Previous": "X", "Current": "Y", "Action completed": "did stuff",
            "Capability gate": "passed", "Evidence": "x:1", "Next allowed": "[A]",
        }
        assert lib.state_output_missing_fields(so) == []

    def test_state_output_none_returns_all_missing(self):
        missing = lib.state_output_missing_fields(None)
        assert len(missing) >= 6


import json as _json_in_tests


class TestSnapshotIO:
    def test_read_missing(self, workspace):
        assert lib.read_snapshot(workspace) == {}

    def test_write_and_read(self, workspace):
        lib.write_snapshot(workspace, {"state.md": "2026-05-24T10:00:00Z"})
        assert lib.read_snapshot(workspace) == {"state.md": "2026-05-24T10:00:00Z"}

    def test_corrupt_returns_empty(self, workspace):
        (workspace / ".copilot" / ".session_snapshot.json").write_text("not json")
        assert lib.read_snapshot(workspace) == {}


class TestCounterIO:
    def test_read_missing(self, workspace):
        assert lib.counter_read(workspace) == {}

    def test_inc_from_zero(self, workspace):
        assert lib.counter_inc(workspace, "copilot-literature", "literature.md") == 1
        assert lib.counter_inc(workspace, "copilot-literature", "literature.md") == 2

    def test_reset_bucket(self, workspace):
        lib.counter_inc(workspace, "copilot-literature", "literature.md")
        lib.counter_reset(workspace, "copilot-literature", "literature.md")
        assert lib.counter_get(workspace, "copilot-literature", "literature.md") == 0

    def test_reset_all_for_agent(self, workspace):
        lib.counter_inc(workspace, "copilot-experiment", "experiments.md")
        lib.counter_inc(workspace, "copilot-experiment", "other.md")
        lib.counter_reset_all(workspace, "copilot-experiment")
        for v in lib.counter_read(workspace).get("copilot-experiment", {}).values():
            assert v["count"] == 0


class TestViolationsLog:
    def test_log_appends(self, workspace):
        lib.log_violation(workspace, "HARD", "DENY", "copilot-literature",
                          "test detail", file=".copilot/ideas.md")
        log = (workspace / ".copilot" / "__violations.log").read_text(encoding="utf-8")
        line = log.strip().splitlines()[-1]
        rec = _json_in_tests.loads(line)
        assert rec["sev"] == "HARD"
        assert rec["kind"] == "DENY"
        assert rec["agent"] == "copilot-literature"

    def test_log_multiple(self, workspace):
        lib.log_violation(workspace, "SOFT", "WARN", "copilot-experiment", "warn 1")
        lib.log_violation(workspace, "SOFT", "WARN", "copilot-experiment", "warn 2")
        lines = (workspace / ".copilot" / "__violations.log").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
