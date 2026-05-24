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
