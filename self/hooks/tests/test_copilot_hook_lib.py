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
