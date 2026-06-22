import json
from pathlib import Path

import research_copilot_guard as guard


def write_task(repo: Path, task_id: str, kind: str, status: str) -> None:
    task_dir = repo / ".research" / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    runtime = repo / ".research" / ".runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "active-task").write_text(task_id, encoding="utf-8")
    (task_dir / "task.json").write_text(json.dumps({
        "id": task_id,
        "title": "node",
        "kind": kind,
        "status": status,
        "priority": "P2",
        "children": [],
        "depends_on": [],
        "gaps": [],
        "created": "2026-06-22T00:00:00Z",
        "updated": "2026-06-22T00:00:00Z",
    }), encoding="utf-8")


def test_no_active_node_denies_research_mcp_and_logs_event(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "mcp__research-scholar__scholar_search", "tool_input": {"query": "diffusion"}}

    decision = guard._decide(payload)

    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "create a Trellis task node first" in decision["systemMessage"]
    event_path = tmp_path / ".research" / ".runtime" / "enforcement-events.jsonl"
    event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["event"] == "main_attempted_leaf_work_without_active_node"
    assert event["decision"] == "deny"


def test_planning_node_allows_rc_plan_and_denies_rc_literature(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-lit", "literature", "planning")

    allowed = guard._decide({
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "rc-plan"},
        "transcript_path": None,
    })
    denied = guard._decide({
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "rc-literature"},
        "transcript_path": None,
    })

    assert allowed["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Legal executor is rc-plan" in denied["systemMessage"]


def test_in_progress_node_allows_kind_executor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-lit", "literature", "in_progress")

    allowed = guard._decide({
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "rc-literature"},
        "transcript_path": None,
    })

    assert allowed["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_main_session_artifact_write_uses_active_node_expected_executor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-write", "writing", "in_progress")

    decision = guard._decide({
        "tool_name": "Write",
        "tool_input": {"file_path": "sections/method.tex"},
    })

    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Legal executor is rc-writer" in decision["systemMessage"]


def test_rc_subagent_with_agent_id_is_exempt_for_leaf_tools(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-lit", "literature", "in_progress")

    decision = guard._decide({
        "agent_id": "agent-1",
        "agent_type": "rc-literature",
        "tool_name": "mcp__research-scholar__scholar_search",
        "tool_input": {"query": "diffusion"},
    })

    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"
