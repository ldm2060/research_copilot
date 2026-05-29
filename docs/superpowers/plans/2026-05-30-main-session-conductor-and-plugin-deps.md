# Main-Session Conductor + Plugin-Dependency Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the research-pipeline conductor from a dispatchable `research-copilot` sub-agent onto the main session (so the constraint applies from every interaction and the conductor always owns the task list), and stop vendoring six third-party sources that are already Claude plugins by declaring them as dependencies.

**Architecture:** Part A installs the conductor onto the main session via three hooks — `SessionStart` (inject the conductor protocol), `UserPromptSubmit` (re-assert standing orders every turn), and a rewritten `PreToolUse` guard that **polices the main session by default and exempts `copilot-*` sub-agents**, using the authoritative `agent_id` payload field to tell them apart. The `research-copilot` sub-agent file is deleted; its state machine and templates migrate to `self/CONDUCTOR-PROTOCOL.md`. Part B adds a `dependencies` array + `allowCrossMarketplaceDependenciesOn` to the generated manifests and removes 11 vendoring lines from `skill.txt`.

**Tech Stack:** Python 3.11 (hook scripts, stdlib only), pytest, Claude Code plugin manifests (JSON), markdown protocol docs.

**Spec:** `docs/superpowers/specs/2026-05-30-main-session-conductor-and-plugin-deps-design.md`

**Key verified facts (from the pre-plan investigation workflow):**
- The PreToolUse payload carries `agent_id` — *"Present only when the hook fires inside a subagent call. Use this to distinguish subagent hook calls from main-thread calls."* (official hooks docs). **Main session = `agent_id` absent.** `agent_type` = the sub-agent's frontmatter `name` (e.g. `copilot-experiment`). This replaces all transcript-scanning for attribution.
- MCP tool names are `mcp__<server>__<tool>`; a matcher term needs a trailing `.*` or it matches nothing.
- Zero skill-name collisions between the 6 dependency plugins and the kept-vendored skills (verified against a real build).
- All 6 deps resolve **unpinned** regardless of tag scheme (tag resolution only runs for *versioned* deps). Never add a `version` field to karpathy or anthropics (zero git tags).
- `example-skills` bundles **12** skills (not 11 — `webapp-testing` is the 12th); harmless over-pull.
- Test suite has **6** test files that hard-code `research-copilot`, not just the pattern-7 test.

---

## File Structure

**Part A — new file:**
- `self/CONDUCTOR-PROTOCOL.md` — the main-session conductor protocol (state table + Mode A/B templates + back-edge matrix), migrated from `research-copilot.agent.md`. Keeps a markdown state table parseable by the meta-test.

**Part A — deleted file:**
- `self/agents/research-copilot.agent.md` — retired.

**Part A — modified (code):**
- `self/hooks/scripts/research_copilot_guard.py` — invert scoping (police main, exempt copilot-* via `agent_id`); replace patterns 1/3/5/6/7 with M1 (delegation gate) + M2 (task-list gate).
- `self/hooks/scripts/_copilot_hook_lib.py` — drop `research-copilot` from `COPILOT_AGENTS`, `OWNED`, `STATE_MACHINE`; add `is_main_session`/origin helper.
- `self/hooks/scripts/user_prompt_dispatch_reminder.py` — remove suppression; re-assert standing orders every turn; drop the research-copilot dispatch line.
- `self/hooks/scripts/session_start_memory_injector.py` — additionally inject `CONDUCTOR-PROTOCOL.md`.
- `self/hooks/scripts/copilot_subagent_stop.py` — remove the `research-copilot` HANDOFF_FILES entry.
- `self/install.py` — widen guard matcher with the 4 MCP servers; rewrite the prompt-fallback to main-session framing; fix Next-steps print; add Part B prerequisite checklist (Part B task).

**Part A — modified (tests):**
- `self/hooks/tests/test_state_machine_consistency.py` — repoint `research-copilot` source-of-truth to `CONDUCTOR-PROTOCOL.md`.
- `self/hooks/tests/test_copilot_hook_lib.py` — drop `research-copilot` from 3 assertions.
- `self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py` — replace 3 suppression tests.
- `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py` → delete.
- `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py` → delete.
- `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py` → replace with M1/M2 tests (renamed `test_research_copilot_guard_main_session.py`).

**Part A — modified (docs):**
- `self/hooks/research-copilot-guard.hook.md`, `self/PIPELINE-OS.md` (lines 5/68/118/133/139/143), `self/AGENTS.md`, `self/README.md`, `self/agents/copilot-rebuttal.agent.md:29`, `self/agents/copilot-literature.agent.md:3`, `self/skills/deep-interview/SKILL.md`, `self/skills/research-workflow/SKILL.md`.

**Part B — modified:**
- `scripts/build_copilot_workspace.py` (plugin_manifest ~L1090, marketplace_manifest ~L1121).
- `skill.txt` (remove 11 lines), `README.md` (prereq list), `self/install.py` (prereq print), `.claude/skills/validate-plugin-build/SKILL.md` (assert deps present).

---

# PHASE A — Main-Session Conductor

### Task A1: Create `self/CONDUCTOR-PROTOCOL.md` with a parseable state table

**Files:**
- Create: `self/CONDUCTOR-PROTOCOL.md`

This file is the main-session conductor's protocol, migrated from `research-copilot.agent.md`. It MUST contain a markdown state table whose header row includes both `状态` and `可能的下一状态`, with the last column formatted `[A, B, C]` — the meta-test (`_parse_state_table`) keys on exactly that. The states must match `STATE_MACHINE["research-copilot"]` in `_copilot_hook_lib.py` (which we keep, see A6).

- [ ] **Step 1: Write the protocol file**

````markdown
# Conductor Protocol — Main-Session Research Pipeline

> You are the **conductor**. This protocol is injected into the main session at
> SessionStart. You are NOT a sub-agent; there is no `@research-copilot` to call.
> Follow `self/PIPELINE-OS.md` for the shared spec (§N references below).

**当前状态**: UNINITIALIZED
**状态历史**: []

## Standing Orders (every turn)

1. If the user's request is execution-class (search papers, brainstorm, run
   experiments, draft/polish/translate, review, rebut), you MUST first publish a
   `TaskCreate` plan list, then dispatch `Agent(subagent_type='copilot-*')` for each
   task. This holds even for a SINGLE routing dispatch (Mode A): publish a one-task
   list before that one `Agent()` call. The guard (M2) hard-denies any copilot-*
   dispatch with no `TaskCreate` in the turn, so a "quick single dispatch" without a
   task list will be blocked. You own the plan — never let the first sub-agent's
   closing recommendation decide the next step.
2. You MUST NOT execute domain work inline. Never run experiment scripts, never
   call paper-retrieval MCP tools (arxiv-search / arxivsub-search / google-scholar
   / dblp-bib), never write `sections/*.tex` / `references.bib` /
   `.copilot/{ideas,experiments,literature}.md`. Delegate to the matching copilot-*.
3. You MAY write `.copilot/state.md` and `.copilot/decisions.md` (you own them).
4. On every stage transition, refresh the `## __HANDOFF__` block of
   `.copilot/state.md` and `.copilot/decisions.md` (per PIPELINE-OS §9). This is a
   standing instruction — no hook enforces it for the main session.

## My State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/state.md` (incl. `__HANDOFF__`); read SessionStart memory inject context | memory-gate | Stage cursor summary | [DIAGNOSED] |
| DIAGNOSED | One-sentence diagnosis + one-sentence recommendation | none | Diagnosis + recommendation | [MODE_A_ROUTING, MODE_B_PIPELINE, PAUSED] |
| MODE_A_ROUTING | Decide the single sub-agent to route to (no dispatch yet) | none | Routing decision | [PLAN_PUBLISHED] |
| MODE_B_PIPELINE | Plan the sequenced dispatches per pipeline template; record in `decisions.md` | none | Pipeline plan | [PLAN_PUBLISHED] |
| PLAN_PUBLISHED | TaskCreate one task per planned dispatch (1 task = 1 sub-agent call; Mode A = exactly one task); chain with `addBlockedBy` so task N depends on task N-1; update `decisions.md` `__HANDOFF__` with task IDs and dispatch order | none | Task IDs + dispatch order | [AWAIT_SUBAGENT_END] |
| AWAIT_SUBAGENT_END | Audit returned STATE_OUTPUT; check `__HANDOFF__` exists; mark current TaskUpdate=completed; if more tasks remain re-enter `Agent()` for next task | handoff-gate | Audit verdict | [DIAGNOSED, BACK_EDGE_TRIGGERED, PAUSED, PLAN_PUBLISHED, END] |
| BACK_EDGE_TRIGGERED | Increment counter in `state.md`; if 3-strike → AskUserQuestion (§5 case ⑥) | none | Counter state + decision | [MODE_A_ROUTING, MODE_B_PIPELINE, PAUSED] |
| PAUSED | User chose to stop / escalate / switch | none | Pause record | [END] |
| END | Update `state.md` + `decisions.md` `__HANDOFF__` blocks | handoff-gate | Final summary | [] |

## Mode B Pipeline Templates

| Template | Sequence |
|---|---|
| Full research | S1 literature → S2 ideation → S3 experiment → S4 writer → S5 polisher → S6 reviewer → S7 rebuttal |
| Pre-submission optimization | read-through → S4 expand/shorten → S5 polish → S5 de-AI → S6 final review |
| Rebuttal prep | S6 self-check → S7 draft → S6 re-review → S7 final |
| Ideation re-check | S2 brainstorm → S3 quick experimental validation → back to S2 OR forward to S4 |
| Custom | user-specified sequence (e.g. `S5→S6→S5→S6`) |

Each cross-stage transition is an approval gate per PIPELINE-OS §5 case ①.

## Back-edge Inbound Matrix

Receive back-edge signals from sub-agents per PIPELINE-OS §7. Increment counters in
`state.md`. At 3 strikes, ask the user (case ⑥). Sub-agents emit suggestions to the
conductor (the main session); they never dispatch each other.

## Delegation Template (7-field, per PIPELINE-OS §4)

Every `Agent()` call MUST carry: Context & stage / Goal / Facts / Constraints /
Expected output / Stop condition / Model (passed as the `model` parameter, matching
the sub-agent's declared frontmatter model).
````

- [ ] **Step 2: Verify the state table parses**

Run: `python -c "import sys; sys.path.insert(0,'self/hooks/scripts'); sys.path.insert(0,'self/hooks/tests'); from test_state_machine_consistency import _parse_state_table; d=_parse_state_table(open('self/CONDUCTOR-PROTOCOL.md',encoding='utf-8').read()); print(sorted(d)); assert set(d)=={'UNINITIALIZED','DIAGNOSED','MODE_A_ROUTING','MODE_B_PIPELINE','PLAN_PUBLISHED','AWAIT_SUBAGENT_END','BACK_EDGE_TRIGGERED','PAUSED','END'}, d"`
Expected: prints the 9 sorted state names, no AssertionError. (The `self/hooks/scripts` path entry is required because `test_state_machine_consistency` imports `_copilot_hook_lib` at module top, which lives there; a bare import without it raises `ModuleNotFoundError`.)

- [ ] **Step 3: Commit**

```bash
git add self/CONDUCTOR-PROTOCOL.md
git commit -m "feat(conductor): add main-session CONDUCTOR-PROTOCOL.md"
```

---

### Task A2: Add origin-attribution helpers to `_copilot_hook_lib.py`

**Files:**
- Modify: `self/hooks/scripts/_copilot_hook_lib.py` (add helpers after `detect_active_agent`, ~line 67)
- Test: `self/hooks/tests/test_copilot_hook_lib.py` (add a new test class)

The authoritative signal is the PreToolUse payload's `agent_id` (absent ⇒ main session). This is far more reliable than transcript-scanning.

- [ ] **Step 1: Write the failing test**

Add to `self/hooks/tests/test_copilot_hook_lib.py`:

```python
class TestOriginAttribution:
    def test_no_agent_id_is_main(self):
        assert lib.is_main_session({"tool_name": "Bash", "tool_input": {}}) is True

    def test_empty_agent_id_is_main(self):
        assert lib.is_main_session({"agent_id": "", "agent_type": ""}) is True

    def test_present_agent_id_is_subagent(self):
        p = {"agent_id": "sa_01", "agent_type": "copilot-experiment"}
        assert lib.is_main_session(p) is False

    def test_exempt_copilot_subagent(self):
        p = {"agent_id": "sa_01", "agent_type": "copilot-experiment"}
        assert lib.is_exempt_subagent(p) is True

    def test_non_copilot_subagent_not_exempt(self):
        p = {"agent_id": "sa_02", "agent_type": "Explore"}
        assert lib.is_exempt_subagent(p) is False

    def test_main_session_not_exempt(self):
        assert lib.is_exempt_subagent({"tool_name": "Bash"}) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd self/hooks && python -m pytest tests/test_copilot_hook_lib.py::TestOriginAttribution -v`
Expected: FAIL with `AttributeError: module '_copilot_hook_lib' has no attribute 'is_main_session'`

- [ ] **Step 3: Add the helpers**

Insert into `self/hooks/scripts/_copilot_hook_lib.py` after `detect_active_agent` (after line 67):

```python
COPILOT_SUBAGENT_PREFIX = "copilot-"


def is_main_session(payload: dict) -> bool:
    """True iff this PreToolUse call originates from the MAIN session.

    Authoritative per Claude Code hooks docs: `agent_id` is present ONLY
    inside a sub-agent call, so its ABSENCE means the main thread. Any
    ambiguity (missing/empty agent_id) resolves to main — conservative,
    because a false 'main' over-applies the guard (recoverable) whereas a
    false 'subagent' silently exempts the main session (defeats the guard).
    """
    return not payload.get("agent_id")


def is_exempt_subagent(payload: dict) -> bool:
    """True iff a copilot-* sub-agent made this call (runs freely)."""
    if is_main_session(payload):
        return False
    return str(payload.get("agent_type") or "").startswith(COPILOT_SUBAGENT_PREFIX)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd self/hooks && python -m pytest tests/test_copilot_hook_lib.py::TestOriginAttribution -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add self/hooks/scripts/_copilot_hook_lib.py self/hooks/tests/test_copilot_hook_lib.py
git commit -m "feat(hooks): add agent_id-based main-vs-subagent attribution helpers"
```

---

### Task A3: Rewrite `research_copilot_guard.py` — invert scoping + M1/M2

**Files:**
- Modify: `self/hooks/scripts/research_copilot_guard.py` (rewrite `is_research_copilot_session`, the pattern functions, and `main`)
- Test: `self/hooks/scripts/__tests__/test_research_copilot_guard_main_session.py` (new)

M1 (delegation gate): the main session running experiment scripts, paper-retrieval MCP, or writes to `sections/*.tex` / `references.bib` / `.copilot/{ideas,experiments,literature}.md` → deny. **Carve-out:** `.copilot/state.md` and `.copilot/decisions.md` are conductor-owned → always allowed. M2 (task-list gate): the main session calling `Agent(copilot-*)` with zero `TaskCreate` in the current turn → deny.

- [ ] **Step 1: Write the failing tests**

Create `self/hooks/scripts/__tests__/test_research_copilot_guard_main_session.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


# ---- M1 delegation gate (main session) ----

def test_m1_blocks_main_session_experiment_bash(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("Bash", {"command": "python train.py --epochs 3"})
    assert msg is not None and "delegate" in msg.lower()


def test_m1_allows_read_only_bash(tmp_path):
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Bash", {"command": "cat results.txt"}) is None


def test_m1_blocks_main_session_research_mcp(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("mcp__arxiv-search__search_arxiv", {"query": "ssms"})
    assert msg is not None and "delegate" in msg.lower()


def test_m1_blocks_write_to_tex(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("Write", {"file_path": "sections/intro.tex"})
    assert msg is not None


def test_m1_blocks_write_to_ideas(tmp_path):
    from research_copilot_guard import check_m1_delegation
    msg = check_m1_delegation("Edit", {"file_path": ".copilot/ideas.md"})
    assert msg is not None


def test_m1_allows_write_to_state_md(tmp_path):
    """Conductor owns state.md / decisions.md — never denied."""
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Write", {"file_path": ".copilot/state.md"}) is None
    assert check_m1_delegation("Edit", {"file_path": ".copilot/decisions.md"}) is None


def test_m1_allows_unrelated_write(tmp_path):
    from research_copilot_guard import check_m1_delegation
    assert check_m1_delegation("Write", {"file_path": "notes/scratch.md"}) is None


# ---- M2 task-list gate (main session) ----

def test_m2_blocks_dispatch_without_taskcreate(tmp_path):
    from research_copilot_guard import check_m2_task_list
    t = tmp_path / "s.jsonl"
    _write_transcript(t, [{"type": "tool_use", "name": "Read",
                           "input": {"file_path": ".copilot/state.md"}}])
    msg = check_m2_task_list("Agent", {"subagent_type": "copilot-literature"}, str(t))
    assert msg is not None and "taskcreate" in msg.lower()


def test_m2_allows_dispatch_with_taskcreate(tmp_path):
    from research_copilot_guard import check_m2_task_list
    t = tmp_path / "s.jsonl"
    _write_transcript(t, [{"type": "tool_use", "name": "TaskCreate",
                           "input": {"subject": "S1"}}])
    assert check_m2_task_list("Agent", {"subagent_type": "copilot-literature"}, str(t)) is None


def test_m2_skips_non_copilot_dispatch(tmp_path):
    from research_copilot_guard import check_m2_task_list
    t = tmp_path / "s.jsonl"
    _write_transcript(t, [])
    assert check_m2_task_list("Agent", {"subagent_type": "general-purpose"}, str(t)) is None


def test_m2_fail_open_no_transcript(tmp_path):
    """No transcript_path => cannot inspect => fail-open (allow)."""
    from research_copilot_guard import check_m2_task_list
    assert check_m2_task_list("Agent", {"subagent_type": "copilot-writer"}, "") is None


# ---- main() integration: attribution via agent_id ----

def _run_main(monkeypatch, capsys, payload: dict) -> dict:
    monkeypatch.setattr("sys.stdin", type("S", (), {"read": lambda self: json.dumps(payload)})())
    import importlib, research_copilot_guard
    importlib.reload(research_copilot_guard)
    research_copilot_guard.main()
    return json.loads(capsys.readouterr().out)


def test_main_polices_main_session_train(tmp_path, monkeypatch, capsys):
    """No agent_id => main session => Bash train.py denied."""
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "tool_input": {"command": "python train.py"},
        "transcript_path": str(tmp_path / "x.jsonl"),
    })
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_exempts_copilot_subagent_train(tmp_path, monkeypatch, capsys):
    """agent_id present + copilot-experiment => exempt => allowed."""
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "tool_input": {"command": "python train.py"},
        "transcript_path": str(tmp_path / "x.jsonl"),
        "agent_id": "sa_01", "agent_type": "copilot-experiment",
    })
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_main_fails_open_on_internal_exception(monkeypatch, capsys):
    """An exception inside the decision path must yield allow, never crash."""
    import importlib, research_copilot_guard
    importlib.reload(research_copilot_guard)
    monkeypatch.setattr(research_copilot_guard, "_decide",
                        lambda payload: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("sys.stdin",
                        type("S", (), {"read": lambda self: json.dumps({"tool_name": "Bash"})})())
    research_copilot_guard.main()
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd self/hooks && python -m pytest scripts/__tests__/test_research_copilot_guard_main_session.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_m1_delegation'`

- [ ] **Step 3: Rewrite the guard**

Replace the entire contents of `self/hooks/scripts/research_copilot_guard.py` with:

```python
"""Research Copilot Workflow Guard hook (PreToolUse).

Polices the MAIN SESSION acting as conductor. The main session must delegate
domain work to copilot-* sub-agents and must publish a TaskCreate plan list
before dispatching. copilot-* sub-agents run freely (exempt).

Origin attribution uses the authoritative `agent_id` payload field: it is
present ONLY inside a sub-agent call, so its absence => main session. Any
ambiguity resolves to main (conservative — never silently exempt the conductor).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

READ_ONLY_PREFIXES = ("grep", "cat", "ls", "head", "tail", "find",
                      "Get-Content", "Select-String", "Get-ChildItem")
EXPERIMENT_KEYWORDS = ("train.py", "run_experiment", "wandb", "mlflow",
                       "tensorboard", "torchrun", "deepspeed", "accelerate")
EXPERIMENT_REGEX = re.compile(r"python[\w\s.-]*\b(train|experiment|run_exp)\b",
                              re.IGNORECASE)
RESEARCH_MCP_PREFIXES = (
    "mcp__arxiv-search__",
    "mcp__arxivsub-search__",
    "mcp__google-scholar__",
    "mcp__dblp-bib__",
)
# Conductor-owned artifacts: the main session MAY write these.
CONDUCTOR_OWNED_ARTIFACTS = (".copilot/state.md", ".copilot/decisions.md")
# Delegated artifacts: the main session must NOT write these.
DELEGATED_ARTIFACTS = ("sections/", "references.bib",
                       ".copilot/ideas.md", ".copilot/experiments.md",
                       ".copilot/literature.md")
READ_ONLY_TOOLS = ("Read", "Grep", "Glob", "TaskCreate", "TaskUpdate",
                   "TaskList", "TaskGet", "Skill", "AskUserQuestion")
COPILOT_SUBAGENT_PREFIX = "copilot-"


def allow() -> dict[str, Any]:
    return {"hookSpecificOutput": {"permissionDecision": "allow"}}


def deny(message: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"permissionDecision": "deny",
                                   "permissionDecisionReason": message},
            "systemMessage": message}


def is_main_session(payload: dict[str, Any]) -> bool:
    """Main session iff `agent_id` absent/empty (per Claude Code hooks docs)."""
    return not payload.get("agent_id")


def is_exempt_subagent(payload: dict[str, Any]) -> bool:
    if is_main_session(payload):
        return False
    return str(payload.get("agent_type") or "").startswith(COPILOT_SUBAGENT_PREFIX)


def is_read_only(command: str) -> bool:
    stripped = command.strip()
    return any(stripped.startswith(prefix) for prefix in READ_ONLY_PREFIXES)


def _norm(path: str) -> str:
    return str(path).replace("\\", "/")


def _iter_transcript_tool_uses(transcript_path: str | None):
    if not transcript_path:
        return
    p = Path(transcript_path)
    if not p.is_file():
        return
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "tool_use":
            yield {"name": rec.get("name", ""), "input": rec.get("input", {}) or {}}
            continue
        content = None
        if isinstance(rec, dict):
            content = rec.get("content")
            if content is None:
                msg = rec.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    yield {"name": item.get("name", ""),
                           "input": item.get("input", {}) or {}}


def check_m1_delegation(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """M1 delegation gate: deny main-session execution-class work."""
    # Experiment scripts via shell.
    if tool_name in ("Bash", "PowerShell"):
        command = str((tool_input or {}).get("command", ""))
        if not command or is_read_only(command):
            return None
        if any(kw in command for kw in EXPERIMENT_KEYWORDS) or EXPERIMENT_REGEX.search(command):
            return ("Blocked by research-copilot-guard (M1 delegation gate): the "
                    "conductor must not run experiments inline. Delegate via "
                    "Agent(subagent_type='copilot-experiment').")
        return None
    # Paper-retrieval MCP tools.
    if any(tool_name.startswith(p) for p in RESEARCH_MCP_PREFIXES):
        return ("Blocked by research-copilot-guard (M1 delegation gate): the "
                "conductor must not search papers inline. Delegate via "
                "Agent(subagent_type='copilot-literature').")
    # Writes to delegated research artifacts.
    if tool_name in ("Write", "Edit"):
        path = _norm((tool_input or {}).get("file_path", ""))
        if any(_norm(owned) in path for owned in CONDUCTOR_OWNED_ARTIFACTS):
            return None  # conductor owns state.md / decisions.md
        if any(seg in path for seg in DELEGATED_ARTIFACTS):
            return ("Blocked by research-copilot-guard (M1 delegation gate): the "
                    "conductor must not write research artifacts (sections/*.tex, "
                    "references.bib, .copilot/{ideas,experiments,literature}.md) "
                    "inline. Delegate to the matching copilot-* sub-agent.")
    return None


def check_m2_task_list(tool_name: str, tool_input: dict[str, Any],
                       transcript_path: str | None) -> str | None:
    """M2 task-list gate: deny copilot-* dispatch with no TaskCreate this turn."""
    if tool_name != "Agent":
        return None
    sub_type = str((tool_input or {}).get("subagent_type", ""))
    if not sub_type.startswith(COPILOT_SUBAGENT_PREFIX):
        return None
    if not transcript_path:
        return None  # fail-open: cannot inspect
    for entry in _iter_transcript_tool_uses(transcript_path):
        if entry["name"] == "TaskCreate":
            return None
    return ("Blocked by research-copilot-guard (M2 task-list gate): dispatching "
            "a copilot-* sub-agent requires a TaskCreate plan list (one task per "
            "planned dispatch) in this turn. Call TaskCreate first, then Agent().")


def main() -> int:
    raw = sys.stdin.read()
    if not raw:
        print(json.dumps(allow()))
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps(allow()))
        return 0
    try:
        decision = _decide(payload)
    except Exception:
        # Fail-open: any unexpected error yields allow, never traps the user
        # (mirrors _copilot_hook_lib.safe_main's contract).
        import traceback
        sys.stderr.write(traceback.format_exc())
        decision = allow()
    print(json.dumps(decision))
    return 0


def _decide(payload: dict[str, Any]) -> dict[str, Any]:
    """Pure decision logic for a parsed payload. Raising is safe — main()
    catches and fails open."""
    # Exempt copilot-* sub-agents outright (they run experiments/searches/writes).
    if is_exempt_subagent(payload):
        return allow()
    # Everything else (incl. ambiguous) is treated as MAIN SESSION -> police.
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    if tool_name in READ_ONLY_TOOLS:
        return allow()
    transcript_path = payload.get("transcript_path")
    for check in (check_m1_delegation(tool_name, tool_input),
                  check_m2_task_list(tool_name, tool_input, transcript_path)):
        if check:
            return deny(check)
    return allow()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd self/hooks && python -m pytest scripts/__tests__/test_research_copilot_guard_main_session.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add self/hooks/scripts/research_copilot_guard.py self/hooks/scripts/__tests__/test_research_copilot_guard_main_session.py
git commit -m "feat(guard): police main session with M1 delegation + M2 task-list gates"
```

---

### Task A4: Delete the three obsolete pattern test files

**Files:**
- Delete: `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py`
- Delete: `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py`
- Delete: `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py`

Patterns 5 (memory-gate) and 6 (research-gate) governed the `research-copilot` *sub-agent* writing to `.copilot/*`; that concern now belongs to `copilot_write_guard.py` (sub-agent-side, unchanged). Pattern 7 is superseded by M2 (Task A3). The functions they import (`check_pattern_5_no_memory_read`, `check_pattern_6_no_research_mcp`, `check_pattern_7_no_plan_list`) no longer exist after A3.

- [ ] **Step 1: Delete the files**

```bash
git rm self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py \
       self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py \
       self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py
```

- [ ] **Step 2: Verify no other file imports the deleted functions**

Run: `grep -rn "check_pattern_5_no_memory_read\|check_pattern_6_no_research_mcp\|check_pattern_7_no_plan_list" self/ ; echo "exit=$?"`
Expected: no matches (grep exit=1).

- [ ] **Step 3: Commit**

```bash
git commit -m "test: remove obsolete pattern5/6/7 guard tests (superseded by M1/M2)"
```

---

### Task A5: Retire `research-copilot` from the lib's three data structures

**Files:**
- Modify: `self/hooks/scripts/_copilot_hook_lib.py` (`COPILOT_AGENTS` ~L21, `OWNED` ~L119, `STATE_MACHINE` ~L189)
- Test: `self/hooks/tests/test_copilot_hook_lib.py` (3 assertions), `self/hooks/tests/test_state_machine_consistency.py` (AGENT_FILES)

`research-copilot` is no longer a sub-agent: drop it from `COPILOT_AGENTS` (the sub-agent set) and `OWNED` (sub-agent write matrix). Keep its state machine but **rename the key to `conductor`** — it remains the meta-test's source of truth, now validated against `CONDUCTOR-PROTOCOL.md`.

- [ ] **Step 1: Update the test fixtures first (they encode the new contract)**

In `self/hooks/tests/test_copilot_hook_lib.py`:

Replace lines 30-34 (`test_is_copilot_agent_positive`) so the literal list no longer contains `"research-copilot"`:

```python
    def test_is_copilot_agent_positive(self):
        for n in ["copilot-literature", "copilot-ideation", "copilot-experiment",
                  "copilot-writer", "copilot-polisher", "copilot-reviewer",
                  "copilot-rebuttal"]:
            assert lib.is_copilot_agent(n) is True

    def test_research_copilot_is_not_a_subagent(self):
        assert lib.is_copilot_agent("research-copilot") is False
```

Delete `test_research_copilot_state` (lines 114-116):

```python
    def test_research_copilot_state(self):
        assert lib.is_owned("research-copilot", ".copilot/state.md") is True
        assert lib.is_owned("research-copilot", ".copilot/decisions.md") is True
```

Rename `test_all_8_agents_have_machines` (line 146) to reflect 7 sub-agents:

```python
    def test_all_subagents_have_machines(self):
        for agent in lib.COPILOT_AGENTS:
            assert agent in lib.STATE_MACHINE, f"missing state machine for {agent}"
```

In `self/hooks/tests/test_state_machine_consistency.py`, replace the `research-copilot` entry in `AGENT_FILES` (lines 13-14) with a `conductor` entry pointing at the protocol file (note it lives one level up from `agents/`):

```python
AGENT_FILES = {
    "conductor":           AGENTS_DIR.parent / "CONDUCTOR-PROTOCOL.md",
    "copilot-literature":  AGENTS_DIR / "copilot-literature.agent.md",
    "copilot-ideation":    AGENTS_DIR / "copilot-ideation.agent.md",
    "copilot-experiment":  AGENTS_DIR / "copilot-experiment.agent.md",
    "copilot-writer":      AGENTS_DIR / "copilot-writer.agent.md",
    "copilot-polisher":    AGENTS_DIR / "copilot-polisher.agent.md",
    "copilot-reviewer":    AGENTS_DIR / "copilot-reviewer.agent.md",
    "copilot-rebuttal":    AGENTS_DIR / "copilot-rebuttal.agent.md",
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd self/hooks && python -m pytest tests/test_copilot_hook_lib.py tests/test_state_machine_consistency.py -v`
Expected: FAIL — `test_research_copilot_is_not_a_subagent` fails (research-copilot still in `COPILOT_AGENTS`), and the `conductor` meta-test fails (`STATE_MACHINE` has no `conductor` key).

- [ ] **Step 3: Apply the lib edits**

In `self/hooks/scripts/_copilot_hook_lib.py`:

Remove `"research-copilot",` from the `COPILOT_AGENTS` frozenset (line 22) so it begins:

```python
COPILOT_AGENTS = frozenset([
    "copilot-literature",
    "copilot-ideation",
    "copilot-experiment",
    "copilot-writer",
    "copilot-polisher",
    "copilot-reviewer",
    "copilot-rebuttal",
])
```

Delete the entire `"research-copilot": [...]` block from `OWNED` (lines 119-123), so `OWNED` begins directly with `"copilot-literature"`.

Rename the `STATE_MACHINE` key (line 189) from `"research-copilot"` to `"conductor"` (the 9-state block is unchanged otherwise):

```python
STATE_MACHINE: dict[str, dict[str, list[str]]] = {
    "conductor": {
        "UNINITIALIZED":        ["DIAGNOSED"],
        "DIAGNOSED":            ["MODE_A_ROUTING", "MODE_B_PIPELINE", "PAUSED"],
        "MODE_A_ROUTING":       ["PLAN_PUBLISHED"],
        "MODE_B_PIPELINE":      ["PLAN_PUBLISHED"],
        "PLAN_PUBLISHED":       ["AWAIT_SUBAGENT_END"],
        "AWAIT_SUBAGENT_END":   ["DIAGNOSED", "BACK_EDGE_TRIGGERED", "PAUSED", "PLAN_PUBLISHED", "END"],
        "BACK_EDGE_TRIGGERED":  ["MODE_A_ROUTING", "MODE_B_PIPELINE", "PAUSED"],
        "PAUSED":               ["END"],
        "END":                  [],
    },
    "copilot-literature": {
```

Note: `MODE_A_ROUTING → PLAN_PUBLISHED` (changed from the old `→ AWAIT_SUBAGENT_END`) so Mode A also publishes a one-task list before dispatching, matching the M2 guard (per decision Q1, Mode A is no longer exempt). This must match the A1 `CONDUCTOR-PROTOCOL.md` table exactly or the meta-test fails.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd self/hooks && python -m pytest tests/test_copilot_hook_lib.py tests/test_state_machine_consistency.py -v`
Expected: all pass (the `conductor` meta-test parses `CONDUCTOR-PROTOCOL.md` from A1 and matches the renamed `STATE_MACHINE["conductor"]`).

- [ ] **Step 5: Commit**

```bash
git add self/hooks/scripts/_copilot_hook_lib.py self/hooks/tests/test_copilot_hook_lib.py self/hooks/tests/test_state_machine_consistency.py
git commit -m "refactor(hooks): retire research-copilot sub-agent; rename state machine to conductor"
```

---

### Task A6: Rewrite the UserPromptSubmit reminder as always-on standing orders

**Files:**
- Modify: `self/hooks/scripts/user_prompt_dispatch_reminder.py`
- Test: `self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py`

Remove suppression entirely (today it self-suppresses on `下一步` / `/` / `@` / status phrases — the exact prompts a returning user types). The reminder fires on every turn, re-asserting that the main session is the conductor. Keep the `.disabled` flag escape hatch.

- [ ] **Step 1: Rewrite the failing tests**

Replace the 3 suppression tests (lines 12-27) in `self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py` with:

```python
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
```

Keep `test_main_respects_disabled_flag` (lines 44-52) but update its assertion: the disabled flag silences output regardless of prompt. Delete `test_exec_keyword_detected_for_brainstorm`, `test_exec_keyword_detected_for_experiment`, `test_no_exec_keyword_for_chat`, and the `should_suppress` import-based tests (the `should_suppress` / `has_exec_keyword` functions are removed below).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd self/hooks && python -m pytest scripts/__tests__/test_user_prompt_dispatch_reminder.py -v`
Expected: FAIL — `main` still suppresses `下一步` (asserts "conductor" not in output).

- [ ] **Step 3: Rewrite the hook**

Replace the entire contents of `self/hooks/scripts/user_prompt_dispatch_reminder.py` with:

```python
"""UserPromptSubmit hook: re-assert the main-session conductor's standing orders
on EVERY turn. No suppression — the constraint must apply from every interaction
onward, including 'next step' / slash / @ prompts. Honors a .disabled flag."""
from __future__ import annotations

import sys
from pathlib import Path

STANDING_ORDERS = (
    "[conductor] You are the research-pipeline conductor (main session). Standing orders:\n"
    "  1. Do NOT execute domain work inline. For any execution-class request, FIRST\n"
    "     publish a TaskCreate plan list (one task per planned dispatch), THEN dispatch:\n"
    "       - literature / paper search -> Agent(subagent_type='copilot-literature')\n"
    "       - innovation / brainstorm    -> Agent(subagent_type='copilot-ideation')\n"
    "       - experiment / training      -> Agent(subagent_type='copilot-experiment')\n"
    "       - drafting / writing         -> Agent(subagent_type='copilot-writer')\n"
    "       - polish / de-AI             -> Agent(subagent_type='copilot-polisher')\n"
    "       - review / sanity            -> Agent(subagent_type='copilot-reviewer')\n"
    "       - rebuttal                   -> Agent(subagent_type='copilot-rebuttal')\n"
    "  2. You OWN the plan and the task list — never let the first sub-agent's closing\n"
    "     recommendation decide the next step. Audit each return, then advance the plan.\n"
    "  3. You may write .copilot/state.md and .copilot/decisions.md; refresh their\n"
    "     __HANDOFF__ blocks on every stage transition (PIPELINE-OS §9).\n"
    "  4. Read .copilot/state.md before diagnosing where the pipeline stands.\n"
)


def main() -> int:
    if (Path.cwd() / ".copilot" / "dispatch-reminder.disabled").exists():
        return 0
    # Drain stdin (the prompt) so the hook doesn't block; content is not inspected —
    # standing orders fire unconditionally.
    _ = sys.stdin.read()
    sys.stdout.write(STANDING_ORDERS)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd self/hooks && python -m pytest scripts/__tests__/test_user_prompt_dispatch_reminder.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add self/hooks/scripts/user_prompt_dispatch_reminder.py self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py
git commit -m "feat(hooks): always-on conductor standing orders (no suppression)"
```

---

### Task A7: Inject CONDUCTOR-PROTOCOL.md at SessionStart

**Files:**
- Modify: `self/hooks/scripts/session_start_memory_injector.py`
- Test: `self/hooks/tests/test_session_start_snapshot.py` (add one test)

Purely additive: after emitting the `__HANDOFF__` summaries, also emit the conductor protocol so the main session loads it every session. The protocol file lives at the plugin root (`${CLAUDE_PLUGIN_ROOT}/CONDUCTOR-PROTOCOL.md` when installed; `self/CONDUCTOR-PROTOCOL.md` in the dev repo). Resolve it relative to the script location to work in both layouts.

- [ ] **Step 1: Write the failing test**

Add to `self/hooks/tests/test_session_start_snapshot.py`:

```python
def test_injects_conductor_protocol(tmp_path, monkeypatch, capsys):
    import session_start_memory_injector as inj
    (tmp_path / ".copilot").mkdir()
    # Seed a real __HANDOFF__ block so `blocks` is non-empty and main() reaches
    # the injection point (it does NOT inject on the early "no blocks" return).
    (tmp_path / ".copilot" / "state.md").write_text(
        "## __HANDOFF__\n- last_updated: 2026-05-24T10:00:00Z\n"
        "- written_by: conductor\n- key_facts:\n  - S1 in progress\n"
        "- next_owner: (none)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    # Point the protocol lookup at a temp file. NOTE: this test runs the injector
    # IN-PROCESS (not via subprocess like the other tests in this file) precisely
    # so conductor_protocol_path can be monkeypatched — do not "fix" it to subprocess.
    proto = tmp_path / "CONDUCTOR-PROTOCOL.md"
    proto.write_text("# Conductor Protocol\nYou are the conductor.\n", encoding="utf-8")
    monkeypatch.setattr(inj, "conductor_protocol_path", lambda: proto)
    inj.main()
    out = capsys.readouterr().out
    assert "You are the conductor" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd self/hooks && python -m pytest tests/test_session_start_snapshot.py::test_injects_conductor_protocol -v`
Expected: FAIL with `AttributeError: ... has no attribute 'conductor_protocol_path'`

- [ ] **Step 3: Add the resolver + injection**

In `self/hooks/scripts/session_start_memory_injector.py`, add near the top (after the imports, before `extract_handoff_block`):

```python
def conductor_protocol_path() -> Path:
    """Locate CONDUCTOR-PROTOCOL.md in both dev (self/) and installed
    (${CLAUDE_PLUGIN_ROOT}/) layouts. The script lives at
    <root>/hooks/scripts/session_start_memory_injector.py, so the protocol is
    two levels up.
    """
    return Path(__file__).resolve().parent.parent.parent / "CONDUCTOR-PROTOCOL.md"
```

Then, immediately before the final `return 0` of `main()` (after the violations-log summary block, ~line 162), add:

```python
    proto = conductor_protocol_path()
    if proto.is_file():
        try:
            sys.stdout.write(
                "\n\n[conductor] Active protocol (you ARE the conductor; "
                "delegate execution to copilot-*, own the task list):\n\n"
                + proto.read_text(encoding="utf-8", errors="replace") + "\n"
            )
            sys.stdout.flush()
        except OSError:
            pass
```

Note: the early `return 0` paths (no `.copilot/`, or no `__HANDOFF__` blocks found) skip injection — the protocol loads once a pipeline workspace with at least one handoff block exists, which is the only situation where conductor context is meaningful. The A7 test therefore seeds a `.copilot/state.md` handoff block so execution reaches this point. (If you instead want the protocol injected on *every* session regardless of `.copilot/` contents, move this block above the `if not blocks:` early return at ~line 106 and drop the seeded-block setup from the test — this plan keeps end-placement.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd self/hooks && python -m pytest tests/test_session_start_snapshot.py::test_injects_conductor_protocol -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add self/hooks/scripts/session_start_memory_injector.py self/hooks/tests/test_session_start_snapshot.py
git commit -m "feat(hooks): inject CONDUCTOR-PROTOCOL.md at SessionStart"
```

---

### Task A8: Remove the stale `research-copilot` HANDOFF_FILES entry

**Files:**
- Modify: `self/hooks/scripts/copilot_subagent_stop.py:23`
- Test: `self/hooks/tests/test_copilot_subagent_stop.py` (verify no regression)

`HANDOFF_FILES["research-copilot"]` is now unreachable (`is_copilot_agent("research-copilot")` is False after A5, so `real_main` short-circuits before consulting it). Remove it for cleanliness. Per the accepted decision, state.md/decisions.md freshness is no longer hook-enforced — it's a standing order in CONDUCTOR-PROTOCOL.md (A1, order 4).

- [ ] **Step 1: Remove the entry**

In `self/hooks/scripts/copilot_subagent_stop.py`, delete line 23 (`"research-copilot":    ["state.md", "decisions.md"],`) and update the comment block above the writer/polisher entries to note the conductor is no longer a sub-agent:

```python
HANDOFF_FILES: dict[str, list[str]] = {
    # research-copilot retired as a sub-agent (now the main-session conductor);
    # state.md/decisions.md freshness is a CONDUCTOR-PROTOCOL standing order,
    # not SubagentStop-enforced (the main session never fires SubagentStop).
    "copilot-literature":  ["literature.md"],
    "copilot-ideation":    ["ideas.md"],
    "copilot-experiment":  ["experiments.md"],
    "copilot-writer":    [],
    "copilot-polisher":  [],
    "copilot-reviewer":  [],
    "copilot-rebuttal":  [],
}
```

- [ ] **Step 2: Run the subagent-stop tests**

Run: `cd self/hooks && python -m pytest tests/test_copilot_subagent_stop.py -v`
Expected: all pass (no test asserted the research-copilot entry; if one does, update it to drop the research-copilot case).

- [ ] **Step 3: Commit**

```bash
git add self/hooks/scripts/copilot_subagent_stop.py
git commit -m "refactor(hooks): drop unreachable research-copilot HANDOFF_FILES entry"
```

---

### Task A9: Update `install.py` — matcher, guard prompt, next-steps

**Files:**
- Modify: `self/install.py` (lines 44-64 prompt, line 65 matcher, lines 582-583 next-steps)

Three edits: widen the matcher so M1's MCP branch can fire; rewrite the prompt-fallback (currently the *inverse* of the new policy — it tells the fallback to APPROVE main-session calls); fix the next-steps print that references the retired `@research-copilot`.

- [ ] **Step 1: Widen the matcher**

Replace `self/install.py:65`:

```python
RESEARCH_COPILOT_GUARD_MATCHER = "Bash|PowerShell|Agent|Write|Edit|mcp__arxiv-search__.*|mcp__arxivsub-search__.*|mcp__google-scholar__.*|mcp__dblp-bib__.*"
```

- [ ] **Step 2: Rewrite the prompt-fallback**

Replace the `RESEARCH_COPILOT_GUARD_PROMPT` string (lines 44-64) with main-session framing:

```python
RESEARCH_COPILOT_GUARD_PROMPT = (
    "You are the research-copilot-guard fallback, running in parallel with a "
    "primary Python guard (if Python is available). The main session acts as the "
    "research-pipeline CONDUCTOR and must DELEGATE domain work to copilot-* "
    "sub-agents. Default to APPROVE unless you have STRONG, CONCRETE evidence "
    "that ALL of the following hold:\n\n"
    "1. This call originates from the MAIN SESSION (NOT a sub-agent). In the hook "
    "payload, a sub-agent call carries a non-empty `agent_id` field; the main "
    "session has NO `agent_id`. If `agent_id` is present, output `approve` "
    "(sub-agents run freely).\n"
    "2. The main session is doing execution-class work that must be delegated:\n"
    "   - Bash/PowerShell running an experiment script (train.py, run_experiment, "
    "wandb, mlflow, torchrun, deepspeed) that is NOT read-only inspection; OR\n"
    "   - a paper-retrieval MCP tool (mcp__arxiv-search__*, mcp__arxivsub-search__*, "
    "mcp__google-scholar__*, mcp__dblp-bib__*); OR\n"
    "   - a Write/Edit to sections/*.tex, references.bib, or "
    ".copilot/{ideas,experiments,literature}.md (but NOT .copilot/state.md or "
    ".copilot/decisions.md, which the conductor owns).\n\n"
    "If `agent_id` is present (sub-agent), or the call is read-only, or you are "
    "uncertain, output `approve`. Only when BOTH conditions above are concretely "
    "met, output `deny` with message: 'Blocked by research-copilot-guard (prompt "
    "fallback): the conductor must delegate this to a copilot-* sub-agent.'\n\n"
    "Return the standard PreToolUse decision JSON. Be brief."
)
```

- [ ] **Step 3: Fix the next-steps print**

Replace `self/install.py:582-583` (the `@research-copilot` line) with conductor framing:

```python
    print("  2. The main session is now the pipeline conductor — just state your goal")
    print("     (e.g. 'where does this research stand?'); it will plan and delegate.")
    print("  3. Call a sub-agent directly: @copilot-literature / @copilot-ideation / @copilot-experiment / @copilot-writer / @copilot-polisher / @copilot-reviewer / @copilot-rebuttal")
```

- [ ] **Step 4: Verify install.py still parses + dry-run**

Run: `python self/install.py --dry-run --skip-deps --skip-verify`
Expected: runs without error; the printed PreToolUse matcher line shows the widened matcher.

- [ ] **Step 5: Verify the widened matcher with the investigation's one-liner**

Run:
```bash
python -c "import re;p=re.compile(r'Bash|PowerShell|Agent|Write|Edit|mcp__arxiv-search__.*|mcp__arxivsub-search__.*|mcp__google-scholar__.*|mcp__dblp-bib__.*');[print('MATCH' if p.search(t) else 'no   ',t) for t in ['Bash','Edit','Read','mcp__arxiv-search__search_arxiv','mcp__dblp-bib__get_dblp_bibtex','mcp__pdf-text__extract_pdf_text','mcp__ai-scientist__list_experiments']]"
```
Expected: MATCH for Bash/Edit/the 2 retrieval MCPs; `no` for Read, `mcp__pdf-text__*`, `mcp__ai-scientist__*`.

- [ ] **Step 6: Commit**

```bash
git add self/install.py
git commit -m "feat(install): widen guard matcher for retrieval MCP; main-session prompt-fallback"
```

---

### Task A10: Update docs that name the retired sub-agent

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`, `self/PIPELINE-OS.md`, `self/AGENTS.md`, `self/README.md`, `self/agents/copilot-rebuttal.agent.md:29`, `self/agents/copilot-literature.agent.md:3`, `self/skills/deep-interview/SKILL.md`, `self/skills/research-workflow/SKILL.md`
- Delete: `self/agents/research-copilot.agent.md`

These are documentation/prose edits — no behavior. The principle: every reference to `research-copilot` *as a dispatchable sub-agent* becomes "the conductor (main session)". Do NOT touch the top-level `README.md` install commands (`research-copilot@research-copilot` is the plugin name, unrelated).

- [ ] **Step 1: Delete the retired agent file**

```bash
git rm self/agents/research-copilot.agent.md
```

- [ ] **Step 2: Rewrite `self/hooks/research-copilot-guard.hook.md`**

Rewrite to describe the new behavior: line 4 purpose → "Enforcement guard for the main-session conductor"; the "Active-Agent Scoping" section → "polices the main session by default (identified by absent `agent_id`); exempts `copilot-*` sub-agents (non-empty `agent_id` + `agent_type` starting `copilot-`)"; the Patterns table → M1 (delegation gate) + M2 (task-list gate); update the matcher string to the widened value; remove the line about `research-copilot.agent.md`'s `tools:` allowlist (replace with: the main session has no tools allowlist, so the widened matcher + M1 is the MCP/experiment bottom line).

- [ ] **Step 3: Reword `self/PIPELINE-OS.md` lines 5, 68, 118, 133, 139, 143**

- L5 `**Loaded by**:` — remove `research-copilot,` and add `the main-session conductor (CONDUCTOR-PROTOCOL.md)` at the front.
- L68 `Every Task()/Agent() call from research-copilot or any coordinator` → `...from the conductor (main session) or any coordinator`.
- L118 (Mode B plan-list rule) — replace the pattern-7 / MODE_B-state description with: "the main-session conductor must publish a `TaskCreate` plan list before any `Agent(copilot-*)` dispatch; `research_copilot_guard.py` M2 denies a copilot-* dispatch with zero `TaskCreate` in the turn."
- L116 (`Otherwise user_prompt_dispatch_reminder.py re-injects guidance on the next turn`) — this clause is stale after A6 (the reminder now fires unconditionally, not on a missing-template condition). Rewrite to: "`user_prompt_dispatch_reminder.py` re-asserts the conductor's standing orders every turn." (Adjust the surrounding sentence about the 7-field template so it no longer implies conditional re-injection.)
- L133 `All back-edges pass through research-copilot` → `...through the conductor (main session)`.
- L139, L143 write-permission table rows: `state.md | research-copilot` → `state.md | conductor`; `decisions.md | research-copilot` → `decisions.md | conductor`.

- [ ] **Step 4: Update `self/AGENTS.md`**

Update the system-structure diagram and the "8 agents" table: remove the `research-copilot` row from the sub-agent table (now 7 sub-agents), and replace the conductor box in the diagram with "main session (conductor, via hooks)". Update the Mode A/B prose to say the conductor is the main session.

- [ ] **Step 5: Reword `self/README.md`**

Rewrite the sub-agent references (the conductor entry-point description, the `.copilot/` ownership notes, the user-action table routing to `@research-copilot`, and the guard description) to main-session-conductor framing. Leave the top-level `README.md` untouched.

- [ ] **Step 6: Reword the two sub-agent files (override the spec's "untouched" non-goal for these 2 lines)**

- `self/agents/copilot-rebuttal.agent.md:29`: `emit a back-edge signal S7 → S3 to research-copilot` → `...to the conductor (main session)`.
- `self/agents/copilot-literature.agent.md:3`: `Dispatched by research-copilot` → `Dispatched by the conductor`.

- [ ] **Step 7: Reword the two skills**

- `self/skills/deep-interview/SKILL.md:18,76`: reword `research-copilot` routing references to "the conductor".
- `self/skills/research-workflow/SKILL.md:8`: `for the research-copilot agent` → `for the main-session conductor`.

- [ ] **Step 8: Verify no dangling dispatchable-sub-agent references remain**

Run: `grep -rn "subagent_type=.research-copilot\|subagent_type='research-copilot'\|@research-copilot" self/ ; echo "exit=$?"`
Expected: no matches (exit=1). (`research-copilot` may still legitimately appear as the *plugin* name or in historical spec/plan docs under `docs/`, which are out of scope here.)

Known-harmless leftover (do NOT treat as a regression in A11): `self/hooks/scripts/__tests__/test_session_start_memory_injector.py:15,45` contain `- written_by: research-copilot` as free-text inside HANDOFF *fixtures*. `written_by` is never validated against `COPILOT_AGENTS`, so these do not break and need not change. Optionally update them to `conductor` for cleanliness — no behavior impact either way.

- [ ] **Step 9: Commit**

```bash
git add -A self/
git commit -m "docs: retire research-copilot sub-agent references; conductor framing"
```

---

### Task A11: Full Phase-A test run

**Files:** none (verification only)

- [ ] **Step 1: Run the entire hook test suite**

Run: `cd self/hooks && python -m pytest -v`
Expected: all pass; specifically no collection errors from deleted pattern5/6/7 imports, and the new `test_research_copilot_guard_main_session.py` + `TestOriginAttribution` + the conductor meta-test all green.

- [ ] **Step 2: Confirm no lingering imports of removed functions**

Run: `grep -rn "is_research_copilot_session\|check_pattern_1_experiment\|check_pattern_3_delegation" self/ ; echo "exit=$?"`
Expected: no matches (exit=1).

- [ ] **Step 3: Manual behavior check (golden path + the A.4 regression)**

This is the feature-correctness check the spec calls out. With the guard installed (`python self/install.py --skip-deps --skip-verify`), simulate two PreToolUse payloads through the guard directly:

```bash
# Main session running train.py -> DENY
echo '{"tool_name":"Bash","tool_input":{"command":"python train.py"},"transcript_path":""}' | python self/hooks/scripts/research_copilot_guard.py
# copilot-experiment running train.py -> ALLOW
echo '{"tool_name":"Bash","tool_input":{"command":"python train.py"},"transcript_path":"","agent_id":"sa_1","agent_type":"copilot-experiment"}' | python self/hooks/scripts/research_copilot_guard.py
```
Expected: first prints `"permissionDecision": "deny"`; second prints `"permissionDecision": "allow"`. This is the exact A.4 scenario — the main-session call is policed even though no transcript reset exists, because attribution uses `agent_id`.

- [ ] **Step 4: Commit (if any fixups were needed)**

```bash
git add -A && git commit -m "test: Phase A full-suite green; conductor guard behavior verified"
```

---

# PHASE B — Plugin-Dependency Migration

### Task B1: Add `dependencies` + `allowCrossMarketplaceDependenciesOn` to the build script

**Files:**
- Modify: `scripts/build_copilot_workspace.py` (`plugin_manifest` ~L1090, `marketplace_manifest` ~L1121)

Both insertion points are verified clean (no hardcoded dep paths). All 7 dependency `name`/`marketplace` pairs and the 6 marketplace names are verified against the upstream marketplace.json files.

- [ ] **Step 1: Add `dependencies` to `plugin_manifest`**

In `scripts/build_copilot_workspace.py`, the `plugin_manifest` dict (~lines 1090-1096) gains a `dependencies` key:

```python
    plugin_manifest = {
        "name": "research-copilot",
        "description": "Academic research workspace: paper writing, review, literature search, and AI Scientist workflow",
        "version": plugin_version,
        "author": {"name": "ldm2060"},
        "repository": plugin_repository,
        "dependencies": [
            {"name": "academic-research-skills", "marketplace": "academic-research-skills"},
            {"name": "paper-polish-workflow", "marketplace": "paper-polish-workflow"},
            {"name": "andrej-karpathy-skills", "marketplace": "karpathy-skills"},
            {"name": "superpowers", "marketplace": "superpowers-dev"},
            {"name": "example-skills", "marketplace": "anthropic-agent-skills"},
            {"name": "ml-paper-writing", "marketplace": "ai-research-skills"},
            {"name": "autoresearch", "marketplace": "ai-research-skills"},
        ],
    }
```

(No `version` field on any entry — unpinned. Per the investigation, karpathy and anthropics have **zero** git tags, so a version field would hard-fail them with `no-matching-tag`.)

- [ ] **Step 2: Add `allowCrossMarketplaceDependenciesOn` to `marketplace_manifest`**

The `marketplace_manifest` dict (~lines 1121-1131) gains the allowlist (uses **marketplace** names, not repo names):

```python
    marketplace_manifest = {
        "name": "research-copilot",
        "owner": {"name": "ldm2060"},
        "allowCrossMarketplaceDependenciesOn": [
            "academic-research-skills",
            "paper-polish-workflow",
            "karpathy-skills",
            "superpowers-dev",
            "anthropic-agent-skills",
            "ai-research-skills",
        ],
        "plugins": [
            {
                "name": "research-copilot",
                "source": plugin_source,
                "description": "Academic research workspace: paper writing, review, literature search, and AI Scientist workflow",
            }
        ],
    }
```

- [ ] **Step 3: Build and assert the manifests contain the new keys**

Run:
```bash
python scripts/build_copilot_workspace.py --version-bump none --output dist/copilot-workspace-test
python -c "import json; m=json.load(open('dist/copilot-workspace-test/.claude-plugin/plugin.json')); assert len(m['dependencies'])==7, m['dependencies']; print('deps OK:', [d['name'] for d in m['dependencies']])"
python -c "import json; m=json.load(open('dist/copilot-workspace-test/.claude-plugin/marketplace.json')); assert len(m['allowCrossMarketplaceDependenciesOn'])==6, m; print('allowlist OK:', m['allowCrossMarketplaceDependenciesOn'])"
```
Expected: prints `deps OK: [...7 names...]` and `allowlist OK: [...6 names...]`.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_copilot_workspace.py
git commit -m "feat(build): declare 7 plugin dependencies + cross-marketplace allowlist"
```

---

### Task B2: Remove the 11 vendoring lines from `skill.txt`

**Files:**
- Modify: `skill.txt`

The 11 lines whose skills are now covered by dependencies. The investigation confirmed zero collisions and that `lylll9436/references` (L18) is consumed only by the also-removed lylll9436 skills.

- [ ] **Step 1: Remove the 11 lines**

Delete these exact lines from `skill.txt`:

```
add third_party\anthropics\skills\doc-coauthoring
add third_party\anthropics\skills\canvas-design
add third_party\orchestra\20-ml-paper-writing\*
add third_party\orchestra\0-autoresearch-skill
add third_party\imbad0202-research\academic-paper
add third_party\imbad0202-research\academic-paper-reviewer
add third_party\imbad0202-research\academic-pipeline
add third_party\imbad0202-research\deep-research
add third_party\lylll9436\skills\*
add third_party\lylll9436\references
add third_party\andrej-karpathy-skills\skills\karpathy-guidelines
```

The resulting `skill.txt` keeps: `add self\skills`, humanizer, auto-research (skills + the skills-codex del/re-add lines), llm-wiki, mean-reviewer, master-cai, k-dense-ai, luwill, lishix520 (composer + strategist), hkust-supervisor, chenliu, and `del assets`.

- [ ] **Step 1b: Confirm no KEPT skill consumes `lylll9436/references` before removing L18**

The L18 (`add third_party\lylll9436\references`) removal is only safe if no still-vendored skill references those files. Verify:

```bash
grep -rniE "lylll9436/references|anti-ai-patterns|body-generation-rules|bilingual-output|skill-skeleton|skill-conventions|repo-patterns" \
  self/skills third_party/humanizer third_party/llm-wiki third_party/mean-reviewer \
  third_party/master-cai third_party/luwill third_party/chenliu third_party/auto-research/skills \
  third_party/k-dense-ai/scientific-skills third_party/lishix520 third_party/hkust-supervisor 2>/dev/null
echo "exit=$?"
```
Expected: no matches (exit=1). This confirms the only consumers were lylll9436's own ppw-* skills (also removed, and replaced by the `paper-polish-workflow` dependency which ships its own `references/`). If any KEPT skill DOES match, restore L18 and leave that reference dir vendored.

- [ ] **Step 2: Build and assert the 28 dep-provided skills are gone, kept skills remain**

Run:
```bash
python scripts/build_copilot_workspace.py --version-bump none --output dist/copilot-workspace-test
python - <<'PY'
import os
b = "dist/copilot-workspace-test/skills"
have = {d for d in os.listdir(b) if os.path.isfile(os.path.join(b, d, "SKILL.md"))}
removed = {"academic-paper","academic-paper-reviewer","academic-pipeline","deep-research",
           "get-paper","paper-polish-workflow","ppw-abstract","ppw-caption","ppw-cover-letter",
           "ppw-de-ai","ppw-experiment","ppw-literature","ppw-logic","ppw-polish",
           "ppw-repo-to-paper","ppw-reviewer-simulation","ppw-team","ppw-translation",
           "ppw-update","ppw-visualization","karpathy-guidelines","ml-paper-writing",
           "academic-plotting","systems-paper-writing","presenting-conference-talks",
           "autoresearch","canvas-design","doc-coauthoring"}
leaked = removed & have
assert not leaked, f"these should be gone: {sorted(leaked)}"
# spot-check kept skills survive:
for k in ("humanizer","mean-reviewer","talk-normal","paper-polish","research-workflow"):
    assert k in have, f"kept skill missing: {k}"
print("OK: 28 dep skills removed; kept skills intact; total skills now", len(have))
PY
```
Expected: prints `OK: ...` (no AssertionError). Also assert the L18 support dir is gone: `test ! -d dist/copilot-workspace-test/skills/references && echo "references support dir gone"`.

- [ ] **Step 3: Commit**

```bash
git add skill.txt
git commit -m "build: stop vendoring 6 sources now declared as dependencies"
```

---

### Task B3: Extend `validate-plugin-build` to assert dependencies present

**Files:**
- Modify: `.claude/skills/validate-plugin-build/SKILL.md`

Currently the validation only checks `marketplace.json` *exists*. Add content assertions for the new keys (additive).

- [ ] **Step 1: Add assertion steps**

In the manifest-verification section of `.claude/skills/validate-plugin-build/SKILL.md` (after the existing `test -f ... marketplace.json` check), add:

````markdown
Assert the generated manifests declare the plugin dependencies:

```bash
python -c "import json,sys; m=json.load(open('dist/claude-workspace/.claude-plugin/plugin.json')); d=m.get('dependencies',[]); names={x['name'] for x in d}; expect={'academic-research-skills','paper-polish-workflow','andrej-karpathy-skills','superpowers','example-skills','ml-paper-writing','autoresearch'}; sys.exit(0 if names==expect else f'dependencies mismatch: {names}')"
python -c "import json,sys; m=json.load(open('dist/claude-workspace/.claude-plugin/marketplace.json')); a=set(m.get('allowCrossMarketplaceDependenciesOn',[])); expect={'academic-research-skills','paper-polish-workflow','karpathy-skills','superpowers-dev','anthropic-agent-skills','ai-research-skills'}; sys.exit(0 if a==expect else f'allowlist mismatch: {a}')"
```

Both must exit 0. Also assert the un-vendored skills no longer ship (catches an accidental skill.txt revert):

```bash
test ! -d dist/claude-workspace/skills/academic-paper && test ! -d dist/claude-workspace/skills/canvas-design && echo "un-vendored skills correctly absent"
```
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/validate-plugin-build/SKILL.md
git commit -m "test(validate-build): assert dependencies + allowlist + un-vendored skills"
```

---

### Task B4: Document the marketplace-add prerequisite

**Files:**
- Modify: `README.md` (top-level), `self/install.py` (prerequisite print)

Pure-dependency means out-of-box now requires the user to add 6 marketplaces first, or the cross-marketplace deps stay silently unresolved.

- [ ] **Step 1: Add the prerequisite block to `README.md`**

Insert this block **once**, immediately after the `## Install` heading (line 5) and **before** the `### From GitHub` subsection — so it applies to both the GitHub and Gitee install paths (each has its own `/plugin install` line):

````markdown
### Prerequisite: add the dependency marketplaces

This plugin depends on six third-party plugins. Add their marketplaces **before** installing, or the dependencies will stay unresolved:

```bash
claude plugin marketplace add Imbad0202/academic-research-skills
claude plugin marketplace add Lylll9436/Paper-Polish-Workflow-skill
claude plugin marketplace add forrestchang/andrej-karpathy-skills
claude plugin marketplace add obra/superpowers
claude plugin marketplace add anthropics/skills
claude plugin marketplace add Orchestra-Research/AI-Research-SKILLs
```

Then install research-copilot as usual; Claude Code resolves and installs the dependencies automatically.
````

- [ ] **Step 2: Print the same checklist from `install.py`**

In `self/install.py`, in the final "Next steps" print block, immediately after the `print("  4. Diagnose MCP latency: ...")` line (the last numbered next-step; note A9 already edited this block, so anchor on this content, not a line number), add:

```python
    print()
    print("  Dependency marketplaces (add these so plugin deps resolve):")
    for mp in (
        "Imbad0202/academic-research-skills",
        "Lylll9436/Paper-Polish-Workflow-skill",
        "forrestchang/andrej-karpathy-skills",
        "obra/superpowers",
        "anthropics/skills",
        "Orchestra-Research/AI-Research-SKILLs",
    ):
        print(f"    claude plugin marketplace add {mp}")
```

- [ ] **Step 3: Verify install.py runs**

Run: `python self/install.py --dry-run --skip-deps --skip-verify`
Expected: the 6 `marketplace add` lines appear in the output.

- [ ] **Step 4: Commit**

```bash
git add README.md self/install.py
git commit -m "docs: document the 6 marketplace-add prerequisites for plugin deps"
```

---

### Task B5: Scratch-profile install smoke test (verification)

**Files:** none (verification only)

The one fact the investigation could not verify without a live install: that unpinned cross-marketplace deps actually resolve end-to-end on the target Claude Code build. This is the B.6 smoke test.

- [ ] **Step 1: Build a release bundle to a scratch dir**

Run: `python scripts/build_copilot_workspace.py --version-bump none --output dist/copilot-workspace-test`
Expected: builds; `dist/copilot-workspace-test/.claude-plugin/plugin.json` has the 7 deps.

- [ ] **Step 2: Add the 6 dependency marketplaces (isolated scratch profile)**

To avoid mutating your real Claude Code marketplace config, run these against an isolated config dir. Set `CLAUDE_CONFIG_DIR` to a throwaway path for this step (and unset it after):

```bash
export CLAUDE_CONFIG_DIR="$(mktemp -d)/cc-scratch"   # PowerShell: $env:CLAUDE_CONFIG_DIR = "$env:TEMP\cc-scratch"
claude plugin marketplace add Imbad0202/academic-research-skills
claude plugin marketplace add Lylll9436/Paper-Polish-Workflow-skill
claude plugin marketplace add forrestchang/andrej-karpathy-skills
claude plugin marketplace add obra/superpowers
claude plugin marketplace add anthropics/skills
claude plugin marketplace add Orchestra-Research/AI-Research-SKILLs
```
Expected: each reports the marketplace added. (If `CLAUDE_CONFIG_DIR` is not honored on the installed Claude Code build, these `marketplace add` calls are reversible with `claude plugin marketplace remove <name>` — note which were newly added so you can clean up.)

- [ ] **Step 3: Verify dependency resolution reports no errors**

Run: `claude plugin list --json | python -c "import json,sys; d=json.load(sys.stdin); errs=[(p.get('name'),p.get('errors')) for p in (d if isinstance(d,list) else d.get('plugins',[])) if p.get('errors')]; print('errors:', errs)"`
Expected: `errors: []` for the dependency plugins (no `dependency-unsatisfied` / `no-matching-tag` / `cross-marketplace`).

- [ ] **Step 4: Record the result**

If any source fails to resolve, the per-source fallback (per spec B.6) is to re-vendor *only that source* — restore its `skill.txt` line(s) and drop its dependency entry from `plugin.json` (Task B1) + its marketplace from the allowlist. **Note the B.4 coupling:** if `paper-polish-workflow` must be re-vendored, restore BOTH `skill.txt` lines (the `skills\*` line AND the `references` line) together — the ppw-* skills hard-refuse when their reference files are missing.

- [ ] **Step 5: Final commit (if fallbacks were applied)**

```bash
git add -A && git commit -m "fix(deps): re-vendor <source> — unpinned cross-marketplace resolution failed"
```

---

## Self-Review Notes (resolved during planning)

- **Spec gaps the investigation surfaced and this plan covers:** the 3 extra test files (A4), the lib's 3 data structures (A5), the dispatch-reminder suppression tests (A6), the `install.py` prompt-fallback being the policy inverse (A9), the 6 PIPELINE-OS lines + 2 sub-agent files + 2 skills + README (A10), the lost state.md freshness enforcement (handled as a CONDUCTOR-PROTOCOL standing order per the accepted soft-directive decision, A1 order 4).
- **Spec corrections baked in:** `example-skills` is 12 skills not 11 (harmless over-pull; B1 depends on the whole plugin anyway); tag-scheme prose was wrong for 3 sources but irrelevant since all deps are unpinned (B1 adds no version fields).
- **M1 carve-out** for conductor-owned `.copilot/state.md` / `.copilot/decisions.md` is implemented and tested (A3 `test_m1_allows_write_to_state_md`).
- **Attribution** uses the authoritative `agent_id` payload field (A2/A3), not transcript-scanning — the A.4 top risk is de-risked; the residual is a version smoke-test (A11 step 3 confirms behavior locally; if an older Claude Code build omits `agent_id`, the conservative default treats calls as main, which over-applies rather than silently exempts).

**Fixes applied after the plan self-review workflow (3 blockers / 3 majors / minors):**
- **Mode A reconciliation (major):** Per Q1, Mode A is no longer exempt from the task list. The A1 state table and A5 `STATE_MACHINE["conductor"]` now route `MODE_A_ROUTING → PLAN_PUBLISHED` (publish a one-task list) → `AWAIT_SUBAGENT_END`, matching the non-state-gated M2 guard. Without this the protocol would have told the conductor to dispatch in a way M2 hard-denies.
- **Guard fail-open (major):** A3's `main()` now wraps the decision in `_decide()` with a `try/except → allow`, replicating `safe_main`'s contract the spec requires; tested by `test_main_fails_open_on_internal_exception` (test count is now 14).
- **A7 test reachability (blocker):** the SessionStart-injection test now seeds a `.copilot/state.md` `__HANDOFF__` block so `main()` reaches the end-placed injection (the empty-`.copilot/` version hit the `if not blocks:` early return and would have failed).
- **A1 verify one-liner (major):** added `self/hooks/scripts` to `sys.path` so `test_state_machine_consistency`'s top-level `import _copilot_hook_lib` resolves under a bare `python -c`.
- **Minors:** B2 adds a grep step that *confirms* (not asserts) no kept skill consumes `lylll9436/references` before removing L18; A10 adds PIPELINE-OS L116 (stale dispatch-reminder clause) and a note on the harmless `test_session_start_memory_injector.py` fixture strings; B4 README placement is pinned to "after `## Install`, before `### From GitHub`" so it covers both install paths; B4 install.py anchor is content-based (A9 shifts line numbers); B5 runs `marketplace add` under an isolated `CLAUDE_CONFIG_DIR` scratch profile.

