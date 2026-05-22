# Self Agent Refactor v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `self/` so the research pipeline becomes shorter (PIPELINE-OS extraction), self-researching (research-gate), self-delegating (UserPromptSubmit hook), self-remembering (SessionStart memory injector), self-looping (longrun-gate + loop-armer), and self-confident (approval-gate policy).

**Architecture:** Extract shared `self/PIPELINE-OS.md`; slim 8 agent files (target ≤4 KB each, conductor ≤5 KB); add 3 new hooks (SessionStart memory injector / UserPromptSubmit dispatch reminder / PostToolUse loop-armer); extend `research_copilot_guard.py` with 2 new violation patterns; add `__HANDOFF__` trailer to each `.copilot/` artifact so the injector has a stable target.

**Tech Stack:** Python 3.11 hooks (stdlib only, no extra deps), Markdown agents, YAML-style `__HANDOFF__` trailer parsed via `re` (no PyYAML dependency for the hook itself), JSON for Claude Code settings, pytest for hook unit tests.

**Spec reference:** `docs/superpowers/specs/2026-05-23-self-agent-refactor-design.md`

---

## File Structure

**Create:**
- `self/PIPELINE-OS.md` — Shared spec: state machine, STATE_OUTPUT, 7 capability gates, delegation template, approval-gate policy, dispatch policy, back-edge matrix, `.copilot/` write permissions, memory hand-off schema, error recovery
- `self/hooks/scripts/session_start_memory_injector.py` — Reads `.copilot/*.md` `__HANDOFF__` blocks; prints ≤2 KB summary
- `self/hooks/scripts/user_prompt_dispatch_reminder.py` — UserPromptSubmit hook; injects sub-agent dispatch suggestion when exec keywords detected
- `self/hooks/scripts/post_tool_loop_armer.py` — PostToolUse hook; recommends self-arming `CronCreate` on long background experiments
- `self/hooks/session-memory-injector.json` — Hook manifest
- `self/hooks/dispatch-reminder.json` — Hook manifest
- `self/hooks/loop-armer.json` — Hook manifest
- `self/hooks/scripts/__tests__/test_session_start_memory_injector.py` — pytest unit tests
- `self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py` — pytest unit tests
- `self/hooks/scripts/__tests__/test_post_tool_loop_armer.py` — pytest unit tests
- `self/agents/backup-2026-05-23/` — pre-rewrite agent snapshots

**Modify:**
- `self/agents/research-copilot.agent.md` — Rewrite ≤5 KB (Mode A routing table, Mode B pipeline templates, back-edge inbound matrix, .copilot writers, no execution)
- `self/agents/copilot-literature.agent.md` — Rewrite ≤3 KB
- `self/agents/copilot-ideation.agent.md` — Rewrite ≤3.5 KB (research-gate + memory-gate)
- `self/agents/copilot-experiment.agent.md` — Rewrite ≤3.5 KB (longrun-gate + memory-gate)
- `self/agents/copilot-writer.agent.md` — Rewrite ≤4 KB
- `self/agents/copilot-polisher.agent.md` — Rewrite ≤3 KB
- `self/agents/copilot-reviewer.agent.md` — Rewrite ≤3.5 KB
- `self/agents/copilot-rebuttal.agent.md` — Rewrite ≤3 KB
- `self/AGENTS.md` — Slim ≤4 KB (delete duplicated state machine / gate / delegation prose; keep 8-agent index)
- `self/SKILLS.md` — No structural change; add 1 paragraph noting PIPELINE-OS.md as the new shared spec
- `self/skills/research-workflow/SKILL.md` — Reference PIPELINE-OS.md §3 (gates) and §5 (approval policy); keep existing 5 HARD-GATE blocks
- `self/hooks/scripts/research_copilot_guard.py` — Add `pattern_5_no_memory_read` + `pattern_6_no_research_mcp` detectors
- `self/install.py` — Register 3 new hooks via 3 new `register_*` functions
- `.copilot/state.md` — Append `## __HANDOFF__` trailer
- `.copilot/literature.md` — Append `## __HANDOFF__` trailer
- `.copilot/ideas.md` — Append `## __HANDOFF__` trailer
- `.copilot/experiments.md` — Append `## __HANDOFF__` trailer
- `.copilot/decisions.md` — Append `## __HANDOFF__` trailer
- `.copilot/handoff.md` — Append `## __HANDOFF__` trailer (note: this file is append-only multi-writer; the trailer is fixed at the EOF and rewritten on each append)

---

## Phase 0 — Backup and Scaffold

### Task 0.1: Backup existing agent files

**Files:**
- Create: `self/agents/backup-2026-05-23/` (8 files copied from `self/agents/*.agent.md`)

- [ ] **Step 1: Create backup directory and copy 8 agent files**

```powershell
New-Item -ItemType Directory -Force -Path self/agents/backup-2026-05-23 | Out-Null
Copy-Item self/agents/research-copilot.agent.md self/agents/backup-2026-05-23/
Copy-Item self/agents/copilot-literature.agent.md self/agents/backup-2026-05-23/
Copy-Item self/agents/copilot-ideation.agent.md self/agents/backup-2026-05-23/
Copy-Item self/agents/copilot-experiment.agent.md self/agents/backup-2026-05-23/
Copy-Item self/agents/copilot-writer.agent.md self/agents/backup-2026-05-23/
Copy-Item self/agents/copilot-polisher.agent.md self/agents/backup-2026-05-23/
Copy-Item self/agents/copilot-reviewer.agent.md self/agents/backup-2026-05-23/
Copy-Item self/agents/copilot-rebuttal.agent.md self/agents/backup-2026-05-23/
```

- [ ] **Step 2: Verify backup contents**

Run: `(Get-ChildItem self/agents/backup-2026-05-23/*.agent.md).Count`
Expected: `8`

- [ ] **Step 3: Commit**

```powershell
git add self/agents/backup-2026-05-23/
git commit -m "chore: snapshot 8 agents before refactor-v2 rewrite"
```

---

## Phase 1 — PIPELINE-OS.md

### Task 1.1: Write PIPELINE-OS.md

**Files:**
- Create: `self/PIPELINE-OS.md`

- [ ] **Step 1: Write the file**

```markdown
# Pipeline OS — Research Copilot Shared Spec

**Version**: 2.0
**Date**: 2026-05-23
**Loaded by**: research-copilot, copilot-literature, copilot-ideation, copilot-experiment, copilot-writer, copilot-polisher, copilot-reviewer, copilot-rebuttal, research-workflow skill.

Every section below is referenced by sub-agent files using `§N`. Do not duplicate this content into any agent file.

## §1. State Machine Format

Every agent tracks its current state and history at the top of its file:

```
**当前状态**: <STATE_NAME>
**状态历史**: [<STATE_1>, <STATE_2>, ...]
```

- State names: `UPPERCASE_WITH_UNDERSCORES`.
- Initial state: `UNINITIALIZED`.
- Terminal state: `END`.
- State history: chronological list of all states visited this session.

Each agent defines its own state-transition table:

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |

Columns:
- **状态**: state name.
- **必须完成的动作**: mandatory action before leaving the state.
- **能力门控**: capability gate (`none` or one of §3).
- **输出格式**: required output for this state.
- **可能的下一状态**: non-empty list of allowed next states (except `END`).

## §2. STATE_OUTPUT Block

Every sub-agent reply MUST end with:

```
[STATE_OUTPUT]
Previous: <previous state>
Current: <current state>
Action completed: <one-line description>
Capability gate: <passed | passed-degraded | not-required | FAILED>
Evidence: <file:line OR tool call ID>
Next allowed: [<state_a>, <state_b>, ...]
Transition reason: <why this transition>
[/STATE_OUTPUT]
```

Malformed or missing → conductor responds `[STATE_ERROR: malformed-output]` listing missing fields; agent retries.

## §3. Capability Gates (7)

| Gate | Matches | Required transition | On fail |
|---|---|---|---|
| `interview-gate` | skill `*-interview` / `quick-interview` | when entering PLANNING / DESIGN_READY without locked goal | `[STATE_ERROR: interview-gate-failed]`, list skills, remain in source state |
| `validation-gate` | skill `*-validator` / `*-checker` | after first DIRECTION_SELECTED / first VERIFIED / after polish | `[STATE_ERROR: validation-gate-failed]` |
| `research-gate` | MCP `arxiv-search` / `arxivsub-search` / `google-scholar` / `dblp-bib` | PREFERENCES_LOCKED → CANDIDATES_GENERATED | `[STATE_ERROR: research-gate-failed]`. Degraded path: `WebFetch` to arxiv.org / scholar.google.com; mark `Capability gate: passed-degraded` |
| `longrun-gate` | one of `Bash(run_in_background=true)`, `Monitor(persistent=true)`, `ScheduleWakeup(delaySeconds≥600)`, `CronCreate` | APPROVED → EXECUTING when est-time > 10 min | `[STATE_ERROR: longrun-gate-failed]` |
| `execution-gate` | scientist-experiment-runner / equivalent | long-task launch within experiment scope | `[STATE_ERROR: execution-gate-failed]` |
| `memory-gate` | `Read` of any `.copilot/*.md` | UNINITIALIZED → CONTEXT_LOADED for every sub-agent | `[STATE_ERROR: memory-gate-failed]` |
| `handoff-gate` | `Edit` / `Write` to agent's owned `.copilot/*.md` adding/updating `## __HANDOFF__` | * → END | `[STATE_ERROR: handoff-gate-failed]` |

`research-gate` minimum coverage: ≥2 distinct queries (different topical keywords, not the same query repeated against different MCP).

## §4. Delegation Template (6-field)

Every `Task()` call from research-copilot or any coordinator MUST include all six fields:

```
Context & stage: <user is at SN; last round did X; why now>
Goal: <what this round completes; what it explicitly does NOT do>
Facts: <.copilot/<file>.md paths, workspace paths, PDFs>
Constraints: <target venue, style, do-not-touch files, no fabricated citations>
Expected output: <conclusion / file diff / draft / table — concrete>
Stop condition: <when to stop and report instead of pushing through>
```

## §5. Approval Gate Policy

**DEFAULT**: do not ask. Report after, not before.

**ASK iff** one of:
1. Cross-stage transition (S_n → S_(n±1)), first time within a pipeline.
2. Back-edge (S_n → S_m, m<n).
3. Irreversible operation: overwrite/delete `.tex`, `.bib`, checkpoint, branch, existing `experiments.md` Run blocks.
4. Resource estimate jumps > 2× (time / GPU / cost).
5. Candidate selection: "which idea / which baseline / which ablation".
6. Loop counter hits 3-strike.

**NEVER ASK** for: DESIGN_READY → APPROVED → EXECUTING intra-Run; COMPLETED → VERIFIED → JUDGED intra-Run; ANALOGIES_ADDED → FILTERED → AWAITING_SELECTION intra-stage; multiple sub-agent dispatches within an approved plan; sub-agent internal transitions; tool-level operations (Read, Grep, short Bash); re-confirming a pipeline template already approved this session.

Main thread speaks on ① ② ⑤ ⑥ only; otherwise one-line progress notes. Sub-agent reports only at `END` (or `STATE_ERROR`, or ④ trip).

## §6. Sub-agent Dispatch Policy

Main thread CAN do: routing, decisions, summary, light reads (≤ 5 tool calls), AskUserQuestion under §5.

Main thread MUST `Agent(subagent_type=<copilot-*>)` for: any execution task that has its own state machine; any task expected to take > 5 tool calls; any task that writes to a `.copilot/*.md` owned by a sub-agent (per §8).

Every `Task()` MUST carry §4's 6-field template. Otherwise `user_prompt_dispatch_reminder.py` re-injects guidance on the next turn.

## §7. Back-edge Matrix

| Trigger | From | To | Counter (in `.copilot/state.md`) | After 3 strikes |
|---|---|---|---|---|
| Idea has fundamental flaw or implementation path off | S3 | S2 | `back_edge_S3_to_S2` | AskUserQuestion: continue / switch / escalate / stop |
| Cannot pick next ablation; literature gap | S3 | S1 | `back_edge_S3_to_S1` | same |
| Writing exposes conceptual gap or unsupported claim | S4 | S2 | `back_edge_S4_to_S2` | same |
| Missing plot or data while writing | S4 | S3 | `back_edge_S4_to_S3` | same |
| Reviewer flags contribution unsupported | S6 | S2 | `back_edge_S6_to_S2` | same |
| Reviewer flags missing data or ablation | S6 | S3 | `back_edge_S6_to_S3` | same |
| Reviewer requires new experiment | S7 | S3 | `back_edge_S7_to_S3` | same |
| Reviewer undermines novelty | S7 | S2 | `back_edge_S7_to_S2` | same |

All back-edges pass through `research-copilot`; sub-agents emit suggestions, never dispatch each other.

## §8. .copilot/ Write Permission Partition

| File | Single writer | Content |
|---|---|---|
| `state.md` | research-copilot | Stage cursor + next-step recommendation + stage history + loop counters |
| `literature.md` | copilot-literature | Candidate papers + locked baseline + novelty-evidence subsection |
| `ideas.md` | copilot-ideation | 6-dimension candidates + selected direction |
| `experiments.md` | copilot-experiment | Goal anchor + Run N blocks + loop_id |
| `decisions.md` | research-copilot | Decision records at every approval gate |
| `handoff.md` | append-only multi-writer | Sub-agent fact handoff |
| `reviews/round-N.md` | copilot-reviewer | Each independent review round |
| `pipelines/*.md` | current stage coordinator | Per-round plan + worker dispatch + worker returns + coordinator review + stage output |

All agents may **read** every file.

## §9. Memory Hand-off Schema

Every `.copilot/<artifact>.md` ends with:

```
## __HANDOFF__
- last_updated: <ISO 8601>
- written_by: <agent name>
- key_facts:
  - <bullet 1>
  - <bullet 2>
- next_owner: <agent name>
```

- `session_start_memory_injector.py` reads ONLY this block (no full-file scan).
- Sub-agents in `END` state MUST write or refresh this block before exiting (handoff-gate enforces).
- Parser tolerates missing block (falls back to last 20 lines of the file).
- `key_facts` accepts free-form bullets; injector preserves them verbatim.

## §10. Error Recovery

| Error code | When emitted | Recovery |
|---|---|---|
| `[STATE_ERROR: malformed-output]` | STATE_OUTPUT block missing fields | Conductor lists missing fields; agent re-emits |
| `[STATE_ERROR: invalid-transition]` | Agent jumps to a state not in "Next allowed" | Conductor lists allowed states; agent retries |
| `[STATE_ERROR: <gate>-failed]` | Capability gate skipped | Agent lists skills/MCPs matching gate; agent calls one; retries |
| `[STATE_ERROR: no-handoff-block]` | Agent reached END but did not write `__HANDOFF__` | Agent appends block; retries |

`research-workflow` skill keeps its 5 enforcement HARD-GATE blocks (`experiment-delegation`, `ideation-delegation`, `task-creation`, `interview-gate`, `state-output-audit`) and references §3/§5/§6 of this file instead of duplicating their content.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/PIPELINE-OS.md).Length / 1KB, 1)`
Expected: a number ≤ 8.0

- [ ] **Step 3: Sanity-check section anchors**

Run: `Select-String -Path self/PIPELINE-OS.md -Pattern "^## §" | Measure-Object`
Expected: `Count : 10`

- [ ] **Step 4: Commit**

```powershell
git add self/PIPELINE-OS.md
git commit -m "feat: add PIPELINE-OS.md shared spec (state machine + 7 gates + dispatch/approval policies)"
```

---

## Phase 2 — `__HANDOFF__` Trailer Blocks

### Task 2.1: Add `__HANDOFF__` skeleton to `.copilot/state.md`

**Files:**
- Modify: `.copilot/state.md`

- [ ] **Step 1: Append the trailer at EOF**

Read the current content, then append:

```markdown

## __HANDOFF__
- last_updated: 2026-05-23T00:00:00Z
- written_by: research-copilot
- key_facts:
  - (placeholder — research-copilot will overwrite on next END transition)
- next_owner: (none)
```

- [ ] **Step 2: Verify the trailer exists at EOF**

Run: `(Get-Content .copilot/state.md -Tail 1) -match 'next_owner'`
Expected: `True`

- [ ] **Step 3: Commit (combined with 2.2–2.6 to reduce commit noise — defer to Task 2.7)**

### Task 2.2: Add `__HANDOFF__` skeleton to `.copilot/literature.md`

**Files:**
- Modify: `.copilot/literature.md`

- [ ] **Step 1: Append**

```markdown

## __HANDOFF__
- last_updated: 2026-05-23T00:00:00Z
- written_by: copilot-literature
- key_facts:
  - (placeholder)
- next_owner: (none)
```

- [ ] **Step 2: Verify**

Run: `(Get-Content .copilot/literature.md -Tail 1) -match 'next_owner'`
Expected: `True`

### Task 2.3: Add `__HANDOFF__` skeleton to `.copilot/ideas.md`

**Files:**
- Modify: `.copilot/ideas.md`

- [ ] **Step 1: Append**

```markdown

## __HANDOFF__
- last_updated: 2026-05-23T00:00:00Z
- written_by: copilot-ideation
- key_facts:
  - (placeholder)
- next_owner: (none)
```

- [ ] **Step 2: Verify**

Run: `(Get-Content .copilot/ideas.md -Tail 1) -match 'next_owner'`
Expected: `True`

### Task 2.4: Add `__HANDOFF__` skeleton to `.copilot/experiments.md`

**Files:**
- Modify: `.copilot/experiments.md`

- [ ] **Step 1: Append**

```markdown

## __HANDOFF__
- last_updated: 2026-05-23T00:00:00Z
- written_by: copilot-experiment
- key_facts:
  - (placeholder)
- next_owner: (none)
```

- [ ] **Step 2: Verify**

Run: `(Get-Content .copilot/experiments.md -Tail 1) -match 'next_owner'`
Expected: `True`

### Task 2.5: Add `__HANDOFF__` skeleton to `.copilot/decisions.md`

**Files:**
- Modify: `.copilot/decisions.md`

- [ ] **Step 1: Append**

```markdown

## __HANDOFF__
- last_updated: 2026-05-23T00:00:00Z
- written_by: research-copilot
- key_facts:
  - (placeholder)
- next_owner: (none)
```

- [ ] **Step 2: Verify**

Run: `(Get-Content .copilot/decisions.md -Tail 1) -match 'next_owner'`
Expected: `True`

### Task 2.6: Add `__HANDOFF__` skeleton to `.copilot/handoff.md`

**Files:**
- Modify: `.copilot/handoff.md`

- [ ] **Step 1: Append**

```markdown

## __HANDOFF__
- last_updated: 2026-05-23T00:00:00Z
- written_by: (multi)
- key_facts:
  - (placeholder)
- next_owner: (none)
```

- [ ] **Step 2: Verify**

Run: `(Get-Content .copilot/handoff.md -Tail 1) -match 'next_owner'`
Expected: `True`

### Task 2.7: Commit all 6 `.copilot/` trailer additions

- [ ] **Step 1: Stage and commit**

```powershell
git add .copilot/state.md .copilot/literature.md .copilot/ideas.md .copilot/experiments.md .copilot/decisions.md .copilot/handoff.md
git commit -m "feat: add __HANDOFF__ trailer block to 6 .copilot artifacts"
```

---

## Phase 3 — SessionStart Memory Injector

### Task 3.1: Write failing test for handoff parser

**Files:**
- Create: `self/hooks/scripts/__tests__/__init__.py` (empty file)
- Create: `self/hooks/scripts/__tests__/test_session_start_memory_injector.py`

- [ ] **Step 1: Create `__init__.py`**

Write empty file at `self/hooks/scripts/__tests__/__init__.py`.

- [ ] **Step 2: Write the first failing test**

```python
# self/hooks/scripts/__tests__/test_session_start_memory_injector.py
import sys
from pathlib import Path

# Allow `import session_start_memory_injector` from the parent directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_extract_handoff_block_returns_block_text_when_present():
    from session_start_memory_injector import extract_handoff_block
    text = (
        "# heading\n"
        "some content\n"
        "\n"
        "## __HANDOFF__\n"
        "- last_updated: 2026-05-23T00:00:00Z\n"
        "- written_by: research-copilot\n"
        "- key_facts:\n"
        "  - locked baseline = Foo\n"
        "- next_owner: copilot-ideation\n"
    )
    block = extract_handoff_block(text)
    assert block is not None
    assert "last_updated" in block
    assert "key_facts" in block
    assert "locked baseline = Foo" in block
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest self/hooks/scripts/__tests__/test_session_start_memory_injector.py -v`
Expected: `ModuleNotFoundError: No module named 'session_start_memory_injector'`

### Task 3.2: Write minimal injector to pass first test

**Files:**
- Create: `self/hooks/scripts/session_start_memory_injector.py`

- [ ] **Step 1: Write the module skeleton with `extract_handoff_block`**

```python
# self/hooks/scripts/session_start_memory_injector.py
"""SessionStart hook: inject .copilot/ __HANDOFF__ summaries into context."""
from __future__ import annotations

from pathlib import Path
import sys

HANDOFF_HEADER = "## __HANDOFF__"


def extract_handoff_block(text: str) -> str | None:
    """Return the body of the trailing ## __HANDOFF__ section, or None."""
    idx = text.rfind(HANDOFF_HEADER)
    if idx < 0:
        return None
    body = text[idx + len(HANDOFF_HEADER):].strip()
    # If a later heading appears (defensive), stop there.
    end = body.find("\n## ")
    if end >= 0:
        body = body[:end].rstrip()
    return body or None


def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the first test, verify it passes**

Run: `python -m pytest self/hooks/scripts/__tests__/test_session_start_memory_injector.py::test_extract_handoff_block_returns_block_text_when_present -v`
Expected: `1 passed`

### Task 3.3: Add test for missing block fallback

- [ ] **Step 1: Append second test**

```python
def test_extract_handoff_block_returns_none_when_absent():
    from session_start_memory_injector import extract_handoff_block
    assert extract_handoff_block("just a body\nno trailer\n") is None


def test_extract_last_n_lines_returns_tail():
    from session_start_memory_injector import extract_last_n_lines
    text = "\n".join(f"line {i}" for i in range(1, 31)) + "\n"
    result = extract_last_n_lines(text, n=5)
    assert result == "line 26\nline 27\nline 28\nline 29\nline 30"
```

- [ ] **Step 2: Run tests, verify second fails**

Run: `python -m pytest self/hooks/scripts/__tests__/test_session_start_memory_injector.py -v`
Expected: `test_extract_last_n_lines_returns_tail` fails with `ImportError` or `AttributeError`.

### Task 3.4: Implement `extract_last_n_lines`

- [ ] **Step 1: Append helper to injector module**

Add to `self/hooks/scripts/session_start_memory_injector.py`:

```python
def extract_last_n_lines(text: str, n: int) -> str:
    lines = text.rstrip("\n").split("\n")
    return "\n".join(lines[-n:])
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest self/hooks/scripts/__tests__/test_session_start_memory_injector.py -v`
Expected: `3 passed`

### Task 3.5: Add integration test for end-to-end injection

- [ ] **Step 1: Append integration test using `tmp_path`**

```python
def test_main_prints_summary_when_copilot_dir_has_handoff_blocks(tmp_path, monkeypatch, capsys):
    copilot = tmp_path / ".copilot"
    copilot.mkdir()
    (copilot / "state.md").write_text(
        "# state\n\n## __HANDOFF__\n"
        "- last_updated: 2026-05-23T00:00:00Z\n"
        "- written_by: research-copilot\n"
        "- key_facts:\n"
        "  - stage cursor at S2\n"
        "- next_owner: copilot-ideation\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    from session_start_memory_injector import main
    rc = main()
    assert rc == 0
    captured = capsys.readouterr().out
    assert "[memory-injector]" in captured
    assert "stage cursor at S2" in captured


def test_main_skips_when_no_copilot_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    from session_start_memory_injector import main
    rc = main()
    assert rc == 0
    captured = capsys.readouterr().out
    assert "not initialized" in captured.lower() or "skipping" in captured.lower()
```

- [ ] **Step 2: Run tests, verify integration test fails**

Run: `python -m pytest self/hooks/scripts/__tests__/test_session_start_memory_injector.py -v`
Expected: 2 new tests fail (main is empty).

### Task 3.6: Implement `main`

- [ ] **Step 1: Replace `main` in the injector module**

```python
COPILOT_FILES = ["state.md", "literature.md", "ideas.md",
                 "experiments.md", "decisions.md", "handoff.md"]
MAX_TOTAL_LINES = 400
PIPELINES_TAIL_LINES = 20
RECENT_PIPELINES = 3


def main() -> int:
    workspace = Path.cwd()
    copilot = workspace / ".copilot"
    if not copilot.exists():
        sys.stdout.write("[memory-injector] .copilot/ not initialized — skipping.\n")
        sys.stdout.flush()
        return 0

    blocks: list[str] = []
    total_lines = 0

    for fname in COPILOT_FILES:
        f = copilot / fname
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        block = extract_handoff_block(text)
        if block is None:
            block = extract_last_n_lines(text, n=PIPELINES_TAIL_LINES)
            if not block.strip():
                continue
            header = f"### {fname} (no __HANDOFF__; last {PIPELINES_TAIL_LINES} lines)"
        else:
            header = f"### {fname}"
        blocks.append(f"{header}\n{block}")
        total_lines += block.count("\n") + 2
        if total_lines >= MAX_TOTAL_LINES:
            blocks.append(f"[memory-injector] truncated at {MAX_TOTAL_LINES} lines budget")
            break

    pipelines_dir = copilot / "pipelines"
    if pipelines_dir.is_dir() and total_lines < MAX_TOTAL_LINES:
        recent = sorted(pipelines_dir.glob("*.md"))[-RECENT_PIPELINES:]
        for p in recent:
            text = p.read_text(encoding="utf-8", errors="replace")
            block = extract_handoff_block(text) or extract_last_n_lines(text, n=PIPELINES_TAIL_LINES)
            if not block.strip():
                continue
            blocks.append(f"### pipelines/{p.stem}\n{block}")
            total_lines += block.count("\n") + 2
            if total_lines >= MAX_TOTAL_LINES:
                break

    if not blocks:
        sys.stdout.write(
            "[memory-injector] .copilot/ exists but no __HANDOFF__ blocks found — "
            "sub-agents likely not following PIPELINE-OS §9.\n"
        )
        sys.stdout.flush()
        return 0

    sys.stdout.write("[memory-injector] Loaded research state from .copilot/:\n\n")
    sys.stdout.write("\n\n".join(blocks))
    sys.stdout.write(
        "\n\n[memory-injector] Constraints: do NOT propose ideas already in ideas.md; "
        "do NOT re-run experiments already in experiments.md unless explicitly asked.\n"
    )
    sys.stdout.flush()
    return 0
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest self/hooks/scripts/__tests__/test_session_start_memory_injector.py -v`
Expected: `5 passed`

### Task 3.7: Write the hook manifest

**Files:**
- Create: `self/hooks/session-memory-injector.json`

- [ ] **Step 1: Write the manifest**

```json
{
  "description": "SessionStart hook: inject .copilot/ __HANDOFF__ summaries so the new session knows where the pipeline stands.",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python self/hooks/scripts/session_start_memory_injector.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; json.load(open('self/hooks/session-memory-injector.json'))"`
Expected: no output, exit 0.

### Task 3.8: Commit Phase 3

- [ ] **Step 1: Stage and commit**

```powershell
git add self/hooks/scripts/session_start_memory_injector.py self/hooks/scripts/__tests__/__init__.py self/hooks/scripts/__tests__/test_session_start_memory_injector.py self/hooks/session-memory-injector.json
git commit -m "feat: add SessionStart memory injector hook reading .copilot __HANDOFF__"
```

---

## Phase 4 — UserPromptSubmit Dispatch Reminder

### Task 4.1: Write failing test for keyword detection

**Files:**
- Create: `self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py`

- [ ] **Step 1: Write the test file**

```python
# self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


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
```

- [ ] **Step 2: Run, verify it fails**

Run: `python -m pytest self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py -v`
Expected: `ModuleNotFoundError`.

### Task 4.2: Implement the reminder script

**Files:**
- Create: `self/hooks/scripts/user_prompt_dispatch_reminder.py`

- [ ] **Step 1: Write the module**

```python
# self/hooks/scripts/user_prompt_dispatch_reminder.py
"""UserPromptSubmit hook: when the prompt looks like an execution task,
inject a one-screen reminder to dispatch a sub-agent instead of inlining."""
from __future__ import annotations

import sys
from pathlib import Path

ALLOWLIST_PREFIXES = ("/", "@")
ALLOWLIST_PHRASES = (
    "what's next", "what is next", "下一步", "状态", "看一下", "看看",
    "show me", "ls ", "cat ", "tell me about", "explain",
)
EXEC_KEYWORDS = (
    # literature / search
    "搜", "查", "文献", "paper", "arxiv", "scholar", "citation",
    # ideation
    "brainstorm", "头脑风暴", "创新", "idea", "ideation",
    # experiment
    "跑", "训练", "实验", "ablation", "baseline", "复现", "train", "experiment",
    # writing
    "写", "draft", "polish", "expand", "shorten", "translate", "caption",
    # review / rebuttal
    "review", "审稿", "rebuttal", "反驳", "sanity",
    # PDF / read paper
    "pdf", "读 ", "read the paper",
)


def should_suppress(prompt: str) -> bool:
    stripped = prompt.lstrip()
    if stripped.startswith(ALLOWLIST_PREFIXES):
        return True
    low = prompt.lower()
    return any(p in low for p in ALLOWLIST_PHRASES)


def has_exec_keyword(prompt: str) -> bool:
    low = prompt.lower()
    return any(k.lower() in low for k in EXEC_KEYWORDS)


def main() -> int:
    # Honour disable flag.
    if (Path.cwd() / ".copilot" / "dispatch-reminder.disabled").exists():
        return 0

    prompt = sys.stdin.read()
    if should_suppress(prompt):
        return 0
    if not has_exec_keyword(prompt):
        return 0

    sys.stdout.write(
        "[dispatch-reminder] Detected execution-class task. Before doing it inline, dispatch a sub-agent:\n"
        "  · literature / paper search → Agent(subagent_type='copilot-literature')\n"
        "  · innovation / brainstorm → Agent(subagent_type='copilot-ideation')\n"
        "  · experiment / training → Agent(subagent_type='copilot-experiment')\n"
        "  · drafting / writing → Agent(subagent_type='copilot-writer')\n"
        "  · polish / de-AI → Agent(subagent_type='copilot-polisher')\n"
        "  · review / sanity → Agent(subagent_type='copilot-reviewer')\n"
        "  · rebuttal → Agent(subagent_type='copilot-rebuttal')\n"
        "  · full pipeline / routing → Agent(subagent_type='research-copilot')\n"
        "Skip dispatch only if: simple question, status query, file-list, or user explicitly asked inline execution.\n"
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run tests, verify all pass**

Run: `python -m pytest self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py -v`
Expected: `6 passed`

### Task 4.3: Add the .disabled flag test

- [ ] **Step 1: Append test**

```python
def test_main_respects_disabled_flag(tmp_path, monkeypatch, capsys):
    (tmp_path / ".copilot").mkdir()
    (tmp_path / ".copilot" / "dispatch-reminder.disabled").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", _StringIO("brainstorm 一下"))
    from user_prompt_dispatch_reminder import main
    rc = main()
    assert rc == 0
    assert capsys.readouterr().out == ""


class _StringIO:
    def __init__(self, s): self._s = s
    def read(self): return self._s
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py -v`
Expected: `7 passed`

### Task 4.4: Write the hook manifest

**Files:**
- Create: `self/hooks/dispatch-reminder.json`

- [ ] **Step 1: Write**

```json
{
  "description": "UserPromptSubmit hook: nudge main thread to dispatch a sub-agent for execution-class prompts.",
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python self/hooks/scripts/user_prompt_dispatch_reminder.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; json.load(open('self/hooks/dispatch-reminder.json'))"`
Expected: no output, exit 0.

### Task 4.5: Commit Phase 4

- [ ] **Step 1: Stage and commit**

```powershell
git add self/hooks/scripts/user_prompt_dispatch_reminder.py self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py self/hooks/dispatch-reminder.json
git commit -m "feat: add UserPromptSubmit dispatch-reminder hook with allowlist + disable flag"
```

---

## Phase 5 — Slim 8 Agent Files

Each agent rewrite follows the same shape:

1. Replace the existing file with a ≤ target-size rewrite that drops every section that PIPELINE-OS.md now owns (state machine format, STATE_OUTPUT, capability gates table, delegation template, dispatch policy, approval policy, back-edge overview, MCP priority, .copilot write-permission table, socket-timeout, /loop user practice).
2. Keep ONLY the agent's unique state-transition table, unique gates required at specific transitions, unique writeable artifacts, unique back-edge sources, and the agent's role/`description`.
3. Verify byte count is under target.
4. Diff against backup to make sure no hard rule was dropped.
5. Commit.

### Task 5.1: Rewrite `research-copilot.agent.md` (target ≤ 5 KB)

**Files:**
- Modify: `self/agents/research-copilot.agent.md`

- [ ] **Step 1: Overwrite the file**

```markdown
---
name: research-copilot
description: "Conductor for the full S1–S7 research pipeline. Routes user requests to one of 7 copilot-* sub-agents OR delegates a multi-stage pipeline. Owns .copilot/state.md and .copilot/decisions.md. Triggers: '下一步' / 'what's next' / '全流程' / '走一遍 pipeline' / 'submission sprint' / 'rebuttal prep' / 'ideation re-check'. Mode A = routing (single dispatch). Mode B = pipeline (sequenced dispatch with approval gates per PIPELINE-OS §5)."
argument-hint: "Current stage / target deadline / venue (optional)"
model: sonnet
color: magenta
---

# Research Copilot — Pipeline Conductor

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for state machine format (§1), STATE_OUTPUT (§2), capability gates (§3), delegation template (§4), approval policy (§5), dispatch policy (§6), back-edge matrix (§7), `.copilot/` write permissions (§8), memory hand-off schema (§9), error recovery (§10). Do NOT duplicate that content here.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/state.md` (incl. `__HANDOFF__`); read SessionStart memory inject context | memory-gate | Stage cursor summary | [DIAGNOSED] |
| DIAGNOSED | One-sentence diagnosis + one-sentence recommendation | none | Diagnosis + recommendation | [MODE_A_ROUTING, MODE_B_PIPELINE, PAUSED] |
| MODE_A_ROUTING | Single `Task()` dispatch with 6-field template | none | Dispatch confirmation | [AWAIT_SUBAGENT_END] |
| MODE_B_PIPELINE | Plan sequenced dispatches per pipeline template; record in `decisions.md` | none | Pipeline plan | [AWAIT_SUBAGENT_END] |
| AWAIT_SUBAGENT_END | Audit returned STATE_OUTPUT; check `__HANDOFF__` exists | handoff-gate | Audit verdict | [DIAGNOSED, BACK_EDGE_TRIGGERED, PAUSED, END] |
| BACK_EDGE_TRIGGERED | Increment counter in `state.md`; if 3-strike → AskUserQuestion (§5 case ⑥) | none | Counter state + decision | [MODE_A_ROUTING, PAUSED] |
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

Receive back-edge signals from sub-agents per PIPELINE-OS §7. Increment counters in `state.md`. At 3 strikes, ask the user (case ⑥).

## Write Permissions

I write `.copilot/state.md` and `.copilot/decisions.md`. I do NOT write any sub-agent's owned artifact (see §8). I do NOT execute training, search papers, draft sections, polish, review, or rebut — those go to copilot-*.

## Hard Constraints

- Every dispatch MUST carry the 6-field delegation template (§4); reject and re-emit if not.
- Audit every sub-agent's STATE_OUTPUT + `__HANDOFF__` block; reject if malformed.
- Approval gates per PIPELINE-OS §5 ONLY — do not ask outside the 6 cases.
- Never run experiments / never search papers / never write `.tex` — delegate.
```

- [ ] **Step 2: Verify byte count**

Run: `[Math]::Round((Get-Item self/agents/research-copilot.agent.md).Length / 1KB, 1)`
Expected: ≤ 5.0

- [ ] **Step 3: Diff against backup to verify no hard rule lost**

Run: `git diff --stat self/agents/research-copilot.agent.md`
Inspect the diff: every removed rule must either (a) be present in `self/PIPELINE-OS.md`, or (b) be intentionally dropped per the spec.

- [ ] **Step 4: Commit**

```powershell
git add self/agents/research-copilot.agent.md
git commit -m "refactor: slim research-copilot.agent.md to ≤5KB; PIPELINE-OS owns shared spec"
```

### Task 5.2: Rewrite `copilot-literature.agent.md` (target ≤ 3 KB)

**Files:**
- Modify: `self/agents/copilot-literature.agent.md`

- [ ] **Step 1: Overwrite**

```markdown
---
name: copilot-literature
description: "Literature scan sub-agent. Use to search for prior work, lock the baseline, augment related-work, verify citations. Dispatched by research-copilot or invoked as @copilot-literature. Writes `.copilot/literature.md` (incl. novelty-evidence subsection). Triggers: 'search papers', 'lock baseline', 'related work', '查文献', '锁 baseline'."
argument-hint: "Topic / venue / year window / baseline candidate"
model: haiku
color: cyan
---

# Copilot Literature — Prior-work Scan

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for all shared rules.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/literature.md` (incl. `__HANDOFF__`) | memory-gate | Context summary | [SCANNING] |
| SCANNING | ≥2 distinct MCP queries (arxiv-search / arxivsub-search / google-scholar / dblp-bib) | research-gate | Candidate list | [BASELINE_LOCKED, RELATED_WORK_AUGMENTED] |
| BASELINE_LOCKED | Append "Locked baseline" block to literature.md | none | Locked baseline block | [RELATED_WORK_AUGMENTED, END] |
| RELATED_WORK_AUGMENTED | Append ≥10 prior-work entries to literature.md (paper id, claim, distance to ours) | none | Related-work block | [END] |
| END | Update `__HANDOFF__` in literature.md | handoff-gate | Final summary | [] |

## My Unique Artifact

- Writes: `.copilot/literature.md`
- `__HANDOFF__.key_facts` MUST include: locked baseline (paper id + 1-line claim), 3–5 closest prior works.

## Hard Constraints

- Never fabricate citations. Every paper id must come from an MCP hit recorded in tool history.
- Forbidden writes: `.copilot/{state,ideas,experiments,decisions}.md`, `sections/*.tex`, `references.bib`.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/agents/copilot-literature.agent.md).Length / 1KB, 1)`
Expected: ≤ 3.0

- [ ] **Step 3: Commit**

```powershell
git add self/agents/copilot-literature.agent.md
git commit -m "refactor: slim copilot-literature.agent.md to ≤3KB"
```

### Task 5.3: Rewrite `copilot-ideation.agent.md` (target ≤ 3.5 KB)

**Files:**
- Modify: `self/agents/copilot-ideation.agent.md`

- [ ] **Step 1: Overwrite**

```markdown
---
name: copilot-ideation
description: "Ideation sub-agent (interactive). Use for innovation direction search, cross-domain brainstorm, novelty re-calibration, mining improvement axes given a baseline. Writes `.copilot/ideas.md`. Triggers: '找创新方向' / '头脑风暴' / '创新点重校' / 'brainstorm' / 'novelty re-check'."
argument-hint: "Selected baseline / preference keywords / conservative-vs-aggressive risk"
model: opus
color: magenta
---

# Copilot Ideation — Interactive Brainstorm Partner

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for all shared rules.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/literature.md` (baseline locked?) + `.copilot/ideas.md` (existing candidates) | memory-gate | Context summary | [CONTEXT_LOADED, END] |
| CONTEXT_LOADED | Create pipeline ledger `pipelines/YYYY-MM-DD-S2-ideation-round-N.md`; plan interview | none | Ledger path + interview plan | [INTERVIEWING] |
| INTERVIEWING | ≥4 interview questions (dissatisfaction / resources / orientation / risk) | interview-gate | Preference summary | [PREFERENCES_LOCKED] |
| PREFERENCES_LOCKED | ≥2 distinct paper-retrieval MCP queries; capture novelty evidence | research-gate | MCP hit list | [CANDIDATES_GENERATED] |
| CANDIDATES_GENERATED | 6-dimension enumeration (1–3 per dim); ≥6 candidates total | none | Candidate list by dimension | [ANALOGIES_ADDED] |
| ANALOGIES_ADDED | ≥2 cross-domain analogies per candidate | none | Enriched candidates | [FILTERED] |
| FILTERED | 5-axis filter (novelty / non-stitching / feasibility / efficacy / reviewer risk); rank ★1-5 | none | Filtered + ranked | [AWAITING_SELECTION] |
| AWAITING_SELECTION | Present top 3; wait for user pick (§5 case ⑤) | none | Candidate summary | [DIRECTION_SELECTED, PREFERENCES_LOCKED] |
| DIRECTION_SELECTED | Record selected direction; call validation skill | validation-gate | Selected direction block | [VALIDATED] |
| VALIDATED | Finalize direction with validation feedback | none | Final direction | [END] |
| END | Update `__HANDOFF__` in ideas.md | handoff-gate | Handoff to copilot-experiment | [] |

## My Unique Gates and Rules

- `research-gate` at PREFERENCES_LOCKED → CANDIDATES_GENERATED: ≥2 distinct queries; each candidate's novelty axis MUST cite ≥1 MCP hit (arxiv id / dblp key / scholar URL). On MCP unavailability, fall back to `WebFetch` and mark `Capability gate: passed-degraded`.
- `memory-gate` MUST read ideas.md first; do NOT propose a candidate already present (compare titles + core-idea bullet).

## My Unique Artifact

- Writes: `.copilot/ideas.md`. `__HANDOFF__.key_facts` includes: selected direction (1 line), 3 nearest prior works, the falsification claim.

## Hard Constraints

- Each candidate: cross-domain analogy + 5-axis filter + recommendation rating + `for @copilot-experiment` block + `for @copilot-writer` block.
- Never select for the user — sort and recommend only.
- Forbidden writes: `.copilot/{state,literature,experiments,decisions}.md`, `sections/*.tex`.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/agents/copilot-ideation.agent.md).Length / 1KB, 1)`
Expected: ≤ 3.5

- [ ] **Step 3: Commit**

```powershell
git add self/agents/copilot-ideation.agent.md
git commit -m "refactor: slim copilot-ideation.agent.md to ≤3.5KB; add research-gate + memory-gate"
```

### Task 5.4: Rewrite `copilot-experiment.agent.md` (target ≤ 3.5 KB)

**Files:**
- Modify: `self/agents/copilot-experiment.agent.md`

- [ ] **Step 1: Overwrite**

```markdown
---
name: copilot-experiment
description: "Experiment execution + validation sub-agent. Use to reproduce a baseline, run training, hyperparameter sweep, ablations, read metrics, plot, judge convergence. Writes `.copilot/experiments.md`. Triggers: '跑实验' / '跑训练' / '复现 baseline' / '消融' / 'train' / 'reproduce baseline' / 'ablation'."
argument-hint: "Selected idea / baseline code path / compute budget / time budget"
model: sonnet
color: green
---

# Copilot Experiment — State Machine Agent

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for all shared rules.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/{ideas,experiments}.md` (incl. `__HANDOFF__`) + workspace training scripts | memory-gate | Context summary | [CONTEXT_LOADED] |
| CONTEXT_LOADED | Check Goal anchor in experiments.md; if missing call interview skill | interview-gate (conditional) | Goal anchor block | [DESIGN_READY] |
| DESIGN_READY | Write Run N design to experiments.md | none | Design block | [APPROVED] |
| APPROVED | Resource report; if est-time > 10 min arm a long-task mechanism | longrun-gate (conditional) | Resource report + loop_id (if armed) | [EXECUTING] |
| EXECUTING | Run experiment via `Bash(run_in_background=true)` / `Monitor` / `ScheduleWakeup` | none | Command + artifact paths | [COMPLETED] |
| COMPLETED | Read logs, extract metrics, append Run N block | none | Run N block | [VERIFIED] |
| VERIFIED | Verify artifacts; compare to Goal anchor | validation-gate (Run 1 only) | Evidence + status | [JUDGED] |
| JUDGED | Decide goal-met / on-trajectory / off-trajectory / falsified | none | Decision + next action | [END, EXECUTING] |
| END | If long-task was armed, CronDelete + remove `.copilot/.loop-armed`; update `__HANDOFF__` | handoff-gate | Final report | [] |

## Iteration Loop Logic

| Goal anchor status | Next state | Action |
|---|---|---|
| `goal-met` | END | Hand off to copilot-writer |
| `on-trajectory` (≤2 rounds left) | EXECUTING | Iterate autonomously (no AskUserQuestion) |
| `off-trajectory` (≤2 rounds left) | EXECUTING | Iterate autonomously with debugging plan |
| `off-trajectory` (rounds exhausted) | END | Signal back-edge S3→S2 to conductor |
| `falsified` | END | Signal back-edge S3→S2 |

Autonomy rule: within `on-trajectory` / `off-trajectory`, pick next config yourself. Re-engage user only when goal met, back-edge triggered, or resource estimate jumps > 2× (§5 case ④).

## My Unique Gates and Rules

- `longrun-gate` at APPROVED → EXECUTING when est-time > 10 min: must call ONE of `Bash(run_in_background=true)`, `Monitor(persistent=true)`, `ScheduleWakeup(delaySeconds≥600)`, `CronCreate`.
- If using `CronCreate` to self-arm `/loop`, record the returned id in experiments.md `__HANDOFF__.loop_id`. On EXECUTING → END, call `CronDelete(loop_id)` and remove `.copilot/.loop-armed`.
- `memory-gate`: MUST Read experiments.md history first; do NOT re-run a Run config already present (compare cmd + key hyperparameters).

## My Unique Artifact

- Writes: `.copilot/experiments.md`. `__HANDOFF__.key_facts` includes: last Run metric vs Goal anchor target, Goal status, loop_id (if any).

## Hard Constraints

- Never fabricate metrics — every number cites a real log line.
- Goal anchor is immutable after first write; only user can revise (§5 case ③).
- Never write `.tex` / `.bib` / `.copilot/{state,literature,ideas,decisions}.md`.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/agents/copilot-experiment.agent.md).Length / 1KB, 1)`
Expected: ≤ 3.5

- [ ] **Step 3: Commit**

```powershell
git add self/agents/copilot-experiment.agent.md
git commit -m "refactor: slim copilot-experiment.agent.md to ≤3.5KB; add longrun-gate + memory-gate"
```

### Task 5.5: Rewrite `copilot-writer.agent.md` (target ≤ 4 KB)

**Files:**
- Modify: `self/agents/copilot-writer.agent.md`

- [ ] **Step 1: Overwrite**

```markdown
---
name: copilot-writer
description: "Paper writing sub-agent. Use to draft sections from experimental results, turn metrics into prose, expand / shorten / translate sections, write figure / table captions. Writes `sections/*.tex` and reads `.copilot/experiments.md`. Triggers: 'draft' / 'expand' / 'shorten' / 'translate' / 'caption' / '写章节'."
argument-hint: "Section name / target style / length budget / venue"
model: sonnet
color: blue
---

# Copilot Writer — Section Drafting

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for all shared rules.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/{ideas,experiments,literature}.md` `__HANDOFF__` | memory-gate | Context summary | [PLAN_DRAFT, EXPAND, SHORTEN, TRANSLATE, CAPTION] |
| PLAN_DRAFT | Outline section structure (claim → evidence → discussion) | none | Outline | [DRAFTING] |
| DRAFTING | Write LaTeX to `sections/<name>.tex`; cite numbers from experiments.md only | none | LaTeX diff | [REVIEW_SELF, END] |
| EXPAND | Expand the target text without padding (surface implicit logic) | none | LaTeX diff | [REVIEW_SELF, END] |
| SHORTEN | Trim 5–15 words while keeping every technical detail | none | LaTeX diff | [REVIEW_SELF, END] |
| TRANSLATE | Zh ↔ En translation, top-venue compliant | none | LaTeX diff | [END] |
| CAPTION | Produce figure / table caption (Title / Sentence case) | none | Caption block | [END] |
| REVIEW_SELF | Sanity-check against experiments.md (no fabricated numbers) | none | Self-review report | [END] |
| END | Update writer's section block in `handoff.md` (append-only) | handoff-gate | Final draft | [] |

## My Unique Artifact

- Writes: `sections/*.tex`, occasionally `references.bib` (additive only, never overwrite existing entries).
- Appends to: `.copilot/handoff.md` with "section drafted, key claims, where numbers came from".

## Hard Constraints

- Every numeric claim must trace to an experiments.md Run block (cite by Run id + metric name + log line).
- Never fabricate. Never invent a citation.
- Forbidden writes: `.copilot/{state,literature,ideas,experiments,decisions}.md`.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/agents/copilot-writer.agent.md).Length / 1KB, 1)`
Expected: ≤ 4.0

- [ ] **Step 3: Commit**

```powershell
git add self/agents/copilot-writer.agent.md
git commit -m "refactor: slim copilot-writer.agent.md to ≤4KB"
```

### Task 5.6: Rewrite `copilot-polisher.agent.md` (target ≤ 3 KB)

**Files:**
- Modify: `self/agents/copilot-polisher.agent.md`

- [ ] **Step 1: Overwrite**

```markdown
---
name: copilot-polisher
description: "Paper polishing sub-agent. Use for academic register, de-AI rewrite, syntax, terminology — NO technical changes. Triggers: 'polish' / 'de-AI' / '润色' / '去 AI 味'."
argument-hint: "Section path or LaTeX block / target style"
model: sonnet
color: blue
---

# Copilot Polisher — Language Polish + De-AI

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for all shared rules.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read target `sections/*.tex` + `.copilot/handoff.md` `__HANDOFF__` | memory-gate | Context summary | [POLISHING] |
| POLISHING | Invoke `paper-polish` skill | none | LaTeX diff | [DE_AI] |
| DE_AI | Invoke `paper-deai` skill | none | LaTeX diff | [VALIDATED] |
| VALIDATED | Invoke `de-ai-checker` skill for verification | validation-gate | Validation report | [END] |
| END | Append polish summary to `.copilot/handoff.md` | handoff-gate | Final report | [] |

## Hard Constraints

- NO technical changes: do not alter numbers, formulas, claims, citations.
- NO content additions / removals beyond stylistic compression.
- Forbidden writes: `.copilot/{state,literature,ideas,experiments,decisions}.md`.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/agents/copilot-polisher.agent.md).Length / 1KB, 1)`
Expected: ≤ 3.0

- [ ] **Step 3: Commit**

```powershell
git add self/agents/copilot-polisher.agent.md
git commit -m "refactor: slim copilot-polisher.agent.md to ≤3KB"
```

### Task 5.7: Rewrite `copilot-reviewer.agent.md` (target ≤ 3.5 KB)

**Files:**
- Modify: `self/agents/copilot-reviewer.agent.md`

- [ ] **Step 1: Overwrite**

```markdown
---
name: copilot-reviewer
description: "Pre-submission paper review sub-agent. Use for top-venue critical review, sanity check, logic check, claim-vs-evidence alignment, rebuttal self-check. Writes `.copilot/reviews/round-N.md`. Triggers: 'review' / 'sanity' / '审稿' / 'pre-submission check'."
argument-hint: "PDF or LaTeX path / review depth / venue"
model: opus
color: yellow
---

# Copilot Reviewer — Critical Pre-submission Review

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for all shared rules.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read target manuscript + `.copilot/{ideas,experiments,literature}.md` `__HANDOFF__` | memory-gate | Context summary | [SIMULATE_REVIEW] |
| SIMULATE_REVIEW | Invoke `paper-review` + `paper-sanity-check` + `paper-logic-check` skills | none | Review draft | [EXTRACT_GAPS] |
| EXTRACT_GAPS | Map each weakness to a back-edge target (S2 / S3 / S4) | none | Gap → back-edge map | [WRITE_ROUND] |
| WRITE_ROUND | Write `.copilot/reviews/round-N.md` (N auto-incremented) | none | reviews/round-N.md | [END] |
| END | Set `__HANDOFF__.key_facts` to list of back-edge targets | handoff-gate | Final report | [] |

## My Unique Artifact

- Writes: `.copilot/reviews/round-N.md`.
- `__HANDOFF__.key_facts` MUST list each weakness → suggested back-edge (e.g. "missing ablation on hyperparameter X → S3").

## Hard Constraints

- Be honest. Top-venue calibration, not vague.
- Cite claim-evidence mismatches by exact .tex section + experiments.md Run id.
- Forbidden writes: `.copilot/{state,literature,ideas,experiments,decisions}.md`, `sections/*.tex`.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/agents/copilot-reviewer.agent.md).Length / 1KB, 1)`
Expected: ≤ 3.5

- [ ] **Step 3: Commit**

```powershell
git add self/agents/copilot-reviewer.agent.md
git commit -m "refactor: slim copilot-reviewer.agent.md to ≤3.5KB"
```

### Task 5.8: Rewrite `copilot-rebuttal.agent.md` (target ≤ 3 KB)

**Files:**
- Modify: `self/agents/copilot-rebuttal.agent.md`

- [ ] **Step 1: Overwrite**

```markdown
---
name: copilot-rebuttal
description: "Rebuttal drafting sub-agent. Use to parse reviewer comments and draft responses, plan follow-up experiments, write defense scripts. Reads `.copilot/reviews/round-N.md`. Triggers: 'rebuttal' / 'reviewer response' / '反驳' / '审稿意见回复'."
argument-hint: "Reviewer round / target tone / submission deadline"
model: sonnet
color: yellow
---

# Copilot Rebuttal — Reviewer Response

**当前状态**: UNINITIALIZED
**状态历史**: []

Follow `self/PIPELINE-OS.md` for all shared rules.

## My Unique State Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/reviews/round-N.md` + `.copilot/handoff.md` `__HANDOFF__` | memory-gate | Reviewer issue list | [PARSE_REVIEWS] |
| PARSE_REVIEWS | Group issues by reviewer id; classify (factual / framing / new-experiment) | none | Issue map | [DRAFT_RESPONSE] |
| DRAFT_RESPONSE | Per reviewer-id, write response block (acknowledge / clarify / counter / commit to follow-up) | none | Response block per reviewer | [RE_REVIEW, END] |
| RE_REVIEW | Self-check tone + completeness | none | Self-check report | [END] |
| END | Append rebuttal block to `.copilot/handoff.md` | handoff-gate | Final rebuttal | [] |

## My Unique Artifact

- Appends to: `.copilot/handoff.md` (append-only, multi-writer).
- For new-experiment commitments, emit a back-edge signal S7 → S3 to research-copilot (do not dispatch experiments directly).

## Hard Constraints

- Tone: respectful, evidence-driven, never combative.
- Every counter-argument must cite a specific experiments.md Run block or sections/*.tex line.
- Forbidden writes: `.copilot/{state,literature,ideas,experiments,decisions}.md`, `sections/*.tex`.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/agents/copilot-rebuttal.agent.md).Length / 1KB, 1)`
Expected: ≤ 3.0

- [ ] **Step 3: Commit**

```powershell
git add self/agents/copilot-rebuttal.agent.md
git commit -m "refactor: slim copilot-rebuttal.agent.md to ≤3KB"
```

---

## Phase 6 — Extend `research_copilot_guard.py`

### Task 6.1: Read existing guard structure

**Files:**
- Read: `self/hooks/scripts/research_copilot_guard.py`

- [ ] **Step 1: Confirm current pattern conventions**

Run: `Select-String -Path self/hooks/scripts/research_copilot_guard.py -Pattern '^def check_pattern_|^def main\b'`
Expected: shows `check_pattern_1_experiment(tool_name, tool_input)`, `check_pattern_3_delegation(tool_name, tool_input, state)`, `main()`.

Observations confirmed (the new patterns 5 and 6 MUST follow this exact convention):
- function signature: `(tool_name: str, tool_input: dict, ...optional state)` returning `str | None` (a deny message or None to approve)
- registered as call results inside the tuple at the `for check in (...)` block in `main()` (currently lines 191–194)
- session-wide tool history is NOT pre-loaded; it must be parsed from `payload["transcript_path"]` (a JSONL file Claude Code provides on each PreToolUse event)

- [ ] **Step 2: Confirm transcript_path is in the payload**

Open `main()` at the existing line `payload = json.loads(raw)`; we will pass `payload.get("transcript_path")` to the new patterns later.

### Task 6.2: Write failing test for Pattern 5 (no memory read)

**Files:**
- Create: `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py`

- [ ] **Step 1: Write the test file**

```python
# self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py
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
```

- [ ] **Step 2: Run, verify it fails**

Run: `python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py -v`
Expected: `ImportError: cannot import name 'check_pattern_5_no_memory_read'`.

### Task 6.3: Implement Pattern 5

**Files:**
- Modify: `self/hooks/scripts/research_copilot_guard.py`

- [ ] **Step 1: Add a transcript-parser helper (place right above `def check_pattern_1_experiment`)**

```python
def _iter_transcript_tool_uses(transcript_path: str | None):
    """Yield {name, input} dicts for every prior tool_use in the JSONL transcript."""
    if not transcript_path:
        return
    p = Path(transcript_path)
    if not p.is_file():
        return
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") == "tool_use":
                yield {"name": rec.get("name", ""), "input": rec.get("input", {}) or {}}
    except OSError:
        return
```

- [ ] **Step 2: Add `check_pattern_5_no_memory_read` after the helper**

```python
COPILOT_ARTIFACT_NAMES = ("ideas.md", "experiments.md", "literature.md", "decisions.md")


def check_pattern_5_no_memory_read(tool_name: str, tool_input: dict[str, Any],
                                   transcript_path: str | None) -> str | None:
    """Pattern 5 (memory-gate): block Write/Edit to .copilot/{ideas,experiments,
    literature,decisions}.md when no prior Read of any .copilot/*.md exists in
    the current session transcript."""
    if tool_name not in ("Write", "Edit"):
        return None
    path = str(tool_input.get("file_path", ""))
    if ".copilot" not in path.replace("\\", "/"):
        return None
    if not any(name in path for name in COPILOT_ARTIFACT_NAMES):
        return None
    for entry in _iter_transcript_tool_uses(transcript_path):
        if entry["name"] != "Read":
            continue
        prior_path = str((entry.get("input") or {}).get("file_path", ""))
        if ".copilot" in prior_path.replace("\\", "/"):
            return None
    return ("Blocked by research-copilot-guard (memory-gate): writing to "
            ".copilot/* artifact without prior Read of any .copilot/*.md in "
            "this session. Per PIPELINE-OS §3 memory-gate, Read the existing "
            "artifact first to avoid re-proposing the same idea/experiment.")
```

- [ ] **Step 3: Register Pattern 5 in `main()`**

Find the existing block (currently at lines 191–197):

```python
    for check in (
        check_pattern_1_experiment(tool_name, tool_input),
        check_pattern_3_delegation(tool_name, tool_input, state),
    ):
        if check:
            print(json.dumps(deny(check)))
            return 0
```

Replace with:

```python
    transcript_path = payload.get("transcript_path")
    for check in (
        check_pattern_1_experiment(tool_name, tool_input),
        check_pattern_3_delegation(tool_name, tool_input, state),
        check_pattern_5_no_memory_read(tool_name, tool_input, transcript_path),
    ):
        if check:
            print(json.dumps(deny(check)))
            return 0
```

- [ ] **Step 4: Run Pattern 5 tests, verify all pass**

Run: `python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py -v`
Expected: `3 passed`.

### Task 6.4: Write failing test for Pattern 6 (no research MCP)

**Files:**
- Create: `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py`

- [ ] **Step 1: Write the test file**

```python
# self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py
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
```

- [ ] **Step 2: Run, verify it fails**

Run: `python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py -v`
Expected: `ImportError`.

### Task 6.5: Implement Pattern 6

**Files:**
- Modify: `self/hooks/scripts/research_copilot_guard.py`

- [ ] **Step 1: Add Pattern 6 after Pattern 5**

```python
RESEARCH_MCP_PREFIXES = (
    "mcp__arxiv-search__",
    "mcp__arxivsub-search__",
    "mcp__google-scholar__",
    "mcp__dblp-bib__",
)


def check_pattern_6_no_research_mcp(tool_name: str, tool_input: dict[str, Any],
                                    transcript_path: str | None) -> str | None:
    """Pattern 6 (research-gate): block a new '## Idea' block being written to
    .copilot/ideas.md when fewer than 2 distinct paper-retrieval MCP queries
    appear in the current session transcript."""
    if tool_name not in ("Write", "Edit"):
        return None
    inp = tool_input or {}
    path = str(inp.get("file_path", ""))
    if "ideas.md" not in path:
        return None
    content = str(inp.get("content") or inp.get("new_string") or "")
    if "## Idea" not in content:
        return None

    queries: set[str] = set()
    for entry in _iter_transcript_tool_uses(transcript_path):
        if not any(entry["name"].startswith(prefix) for prefix in RESEARCH_MCP_PREFIXES):
            continue
        inp_e = entry.get("input") or {}
        q = inp_e.get("query") or inp_e.get("q") or ""
        if q:
            queries.add(str(q).strip().lower())

    if len(queries) >= 2:
        return None

    return ("Blocked by research-copilot-guard (research-gate): "
            "'## Idea' block being written to .copilot/ideas.md but only "
            f"{len(queries)} distinct paper-retrieval MCP query(ies) recorded "
            "in this session; need ≥2 distinct queries (different topical "
            "keywords). Call arxiv-search / arxivsub-search / google-scholar "
            "/ dblp-bib MCPs first.")
```

- [ ] **Step 2: Register Pattern 6 in `main()`**

Extend the `for check in (...)` tuple to include `check_pattern_6_no_research_mcp(tool_name, tool_input, transcript_path)`:

```python
    transcript_path = payload.get("transcript_path")
    for check in (
        check_pattern_1_experiment(tool_name, tool_input),
        check_pattern_3_delegation(tool_name, tool_input, state),
        check_pattern_5_no_memory_read(tool_name, tool_input, transcript_path),
        check_pattern_6_no_research_mcp(tool_name, tool_input, transcript_path),
    ):
        if check:
            print(json.dumps(deny(check)))
            return 0
```

- [ ] **Step 3: Run Pattern 6 tests**

Run: `python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py -v`
Expected: `4 passed`.

### Task 6.6: Run the full guard test suite

- [ ] **Step 1: Run all guard tests**

Run: `python -m pytest self/hooks/scripts/__tests__/ -v -k "guard"`
Expected: `7 passed` (3 from Pattern 5, 4 from Pattern 6).

### Task 6.7: Commit Phase 6

- [ ] **Step 1: Stage and commit**

```powershell
git add self/hooks/scripts/research_copilot_guard.py self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py
git commit -m "feat: add research_copilot_guard patterns 5 (no-memory-read) + 6 (no-research-mcp)"
```

---

## Phase 7 — `post_tool_loop_armer.py`

### Task 7.1: Write failing test for trigger detection

**Files:**
- Create: `self/hooks/scripts/__tests__/test_post_tool_loop_armer.py`

- [ ] **Step 1: Write the test**

```python
# self/hooks/scripts/__tests__/test_post_tool_loop_armer.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


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


class _StringIO:
    def __init__(self, s): self._s = s
    def read(self): return self._s
```

- [ ] **Step 2: Run, verify all fail**

Run: `python -m pytest self/hooks/scripts/__tests__/test_post_tool_loop_armer.py -v`
Expected: `ImportError`.

### Task 7.2: Implement the loop-armer script

**Files:**
- Create: `self/hooks/scripts/post_tool_loop_armer.py`

- [ ] **Step 1: Write the module**

```python
# self/hooks/scripts/post_tool_loop_armer.py
"""PostToolUse hook: detect long background experiments and recommend
arming a CronCreate-based self-poll so the main session continues after
notifications. Sets `.copilot/.loop-armed` to avoid duplicate suggestions."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LONGRUN_PATTERNS = (
    re.compile(r"\btrain(\.py|_)"),
    re.compile(r"\bmain\.py\b"),
    re.compile(r"\bai_scientist\b"),
    re.compile(r"\btorchrun\b"),
    re.compile(r"\bdeepspeed\b"),
    re.compile(r"\bexperiments?/"),
    re.compile(r"\baccelerate launch\b"),
)


def should_arm(event: dict) -> bool:
    if event.get("tool_name") != "Bash":
        return False
    inp = event.get("tool_input") or {}
    if not inp.get("run_in_background"):
        return False
    cmd = inp.get("command", "") or ""
    return any(p.search(cmd) for p in LONGRUN_PATTERNS)


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    if not should_arm(event):
        return 0

    flag = Path.cwd() / ".copilot" / ".loop-armed"
    if flag.exists():
        return 0

    sys.stdout.write(
        "[loop-armer] Detected long-running background experiment.\n"
        "[loop-armer] Recommend arming a self-poll so the loop continues across notifications:\n"
        "  CronCreate(cron=\"*/3 * * * *\", prompt=\"<<autonomous-loop>>\", recurring=true, durable=false)\n"
        "[loop-armer] Or the user can paste:\n"
        "  /loop 1m If a background experiment task is still running, check its log tail and decide next step. Otherwise, delete this scheduled task.\n"
        "[loop-armer] On EXECUTING -> END the agent MUST CronDelete the returned id and remove .copilot/.loop-armed.\n"
    )
    sys.stdout.flush()
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest self/hooks/scripts/__tests__/test_post_tool_loop_armer.py -v`
Expected: `6 passed`

### Task 7.3: Write the hook manifest

**Files:**
- Create: `self/hooks/loop-armer.json`

- [ ] **Step 1: Write**

```json
{
  "description": "PostToolUse hook: when copilot-experiment launches a long background experiment, recommend arming /loop or CronCreate so results flow back after task notification.",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python self/hooks/scripts/post_tool_loop_armer.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; json.load(open('self/hooks/loop-armer.json'))"`
Expected: no output, exit 0.

### Task 7.4: Commit Phase 7

- [ ] **Step 1: Stage and commit**

```powershell
git add self/hooks/scripts/post_tool_loop_armer.py self/hooks/scripts/__tests__/test_post_tool_loop_armer.py self/hooks/loop-armer.json
git commit -m "feat: add PostToolUse loop-armer hook for long background experiments"
```

---

## Phase 8 — Update AGENTS.md, SKILLS.md, research-workflow, install.py

### Task 8.1: Slim AGENTS.md

**Files:**
- Modify: `self/AGENTS.md`

- [ ] **Step 1: Overwrite with the slimmed version**

```markdown
# Agents Overview

Every file under `self/agents/` follows Claude Code's native format (frontmatter with `name` / `description` / `model`, no `tools` restriction). Each `.agent.md` can be invoked directly as `@agent-name`, or delegated by the conductor via `Task(subagent_type="...")`.

All shared workflow rules live in [`self/PIPELINE-OS.md`](PIPELINE-OS.md). Do not duplicate them here.

## System structure

```
              ┌─ user ─┐
              │         │
              ▼         ▼
   research-copilot   @copilot-<sub>
   (conductor, default)   (direct shortcut)
              │
              └─ Task() delegate ─→ 7 copilot-* sub-agents
                                  │
                                  ├─ Skill / MCP / Bash / Edit / Write / Glob / Grep / Read
```

Coordination: `research-copilot` owns cross-stage routing. `copilot-*` stage coordinators may dispatch narrow worker sub-agents only after writing a `pipelines/<round>.md` ledger.

## The 8 agents

| Agent | File | Role | Model | Color |
|---|---|---|---|---|
| research-copilot | research-copilot.agent.md | 🧭 Pipeline conductor | sonnet | magenta |
| copilot-literature | copilot-literature.agent.md | 📚 Literature scan | haiku | cyan |
| copilot-ideation | copilot-ideation.agent.md | 💡 Interactive ideation | opus | magenta |
| copilot-experiment | copilot-experiment.agent.md | 🧪 Experiment & validation | sonnet | green |
| copilot-writer | copilot-writer.agent.md | ✍️ Paper writing | sonnet | blue |
| copilot-polisher | copilot-polisher.agent.md | ✨ Paper polishing | sonnet | blue |
| copilot-reviewer | copilot-reviewer.agent.md | 🔍 Paper review | opus | yellow |
| copilot-rebuttal | copilot-rebuttal.agent.md | 💬 Rebuttal | sonnet | yellow |

Models chosen per: `opus` for novelty judgment + critical review (ideation, reviewer); `haiku` for retrieval + structuring (literature); `sonnet` for balanced reasoning + speed (conductor, writer, polisher, experiment, rebuttal).

## Pipeline modes

- **Mode A (routing)**: research-copilot scans state → one-sentence diagnosis → one-sentence recommendation → single Task() dispatch.
- **Mode B (pipeline)**: research-copilot runs a sequence (full research / pre-submission optimization / rebuttal prep / ideation re-check / custom). Cross-stage transitions are approval gates per PIPELINE-OS §5 case ①.

## .copilot/ artifacts

| File | Single writer | Trailer |
|---|---|---|
| state.md | research-copilot | `__HANDOFF__` |
| literature.md | copilot-literature | `__HANDOFF__` (incl. novelty-evidence) |
| ideas.md | copilot-ideation | `__HANDOFF__` |
| experiments.md | copilot-experiment | `__HANDOFF__` (incl. loop_id) |
| decisions.md | research-copilot | `__HANDOFF__` |
| handoff.md | multi-writer, append-only | `__HANDOFF__` (collective) |
| reviews/round-N.md | copilot-reviewer | `__HANDOFF__` |

The SessionStart memory injector reads each `__HANDOFF__` block to bring a fresh session up to speed.

## Hooks in this directory

- `self/hooks/scientist-guardrails.json` — SessionStart: AI Scientist runtime advisory.
- `self/hooks/session-memory-injector.json` — SessionStart: inject `__HANDOFF__` summaries.
- `self/hooks/dispatch-reminder.json` — UserPromptSubmit: nudge sub-agent dispatch on exec-class prompts.
- `self/hooks/loop-armer.json` — PostToolUse: recommend `/loop` self-arming on long background experiments.
- `.claude/settings.json` (registered by `self/install.py`) — also wires `research_copilot_guard.py` as PreToolUse and `block_protected_paths.py` / `regen_skill_json.py` for project housekeeping.

## Troubleshooting

- MCP latency: `python self/scripts/diagnose-mcp.py`.
- Memory injector noisy / silent: check `.copilot/*.md` actually contain `## __HANDOFF__` blocks.
- Dispatch-reminder too talky: `touch .copilot/dispatch-reminder.disabled` to silence it (the hook honours the flag).
- Loop-armer doesn't fire: confirm the launched command matches `LONGRUN_PATTERNS` in `post_tool_loop_armer.py`; otherwise extend the list.
```

- [ ] **Step 2: Verify size**

Run: `[Math]::Round((Get-Item self/AGENTS.md).Length / 1KB, 1)`
Expected: ≤ 5.0 (target 4 KB, accept up to 5 KB)

- [ ] **Step 3: Commit**

```powershell
git add self/AGENTS.md
git commit -m "refactor: slim self/AGENTS.md to reference PIPELINE-OS; drop duplicated rules"
```

### Task 8.2: Add PIPELINE-OS note to SKILLS.md

**Files:**
- Modify: `self/SKILLS.md`

- [ ] **Step 1: Insert the note**

Find the line starting with `# Skills Overview` and immediately after the first paragraph add:

```markdown

Workflow rules consumed by these skills (state machine, capability gates, approval policy, dispatch policy) live in [`self/PIPELINE-OS.md`](PIPELINE-OS.md). Skill files reference its sections instead of duplicating content.
```

- [ ] **Step 2: Commit**

```powershell
git add self/SKILLS.md
git commit -m "docs: cross-link SKILLS.md to PIPELINE-OS.md"
```

### Task 8.3: Update `research-workflow/SKILL.md`

**Files:**
- Modify: `self/skills/research-workflow/SKILL.md`

- [ ] **Step 1: Read the file to locate the existing HARD-GATE blocks**

Run: `Select-String -Path self/skills/research-workflow/SKILL.md -Pattern '<HARD-GATE'`
Note the 5 existing HARD-GATE block locations.

- [ ] **Step 2: Above the first HARD-GATE block, insert a reference paragraph**

Insert after `# Research Workflow` header and before the `## Mandatory Checklist`:

```markdown

## Source of Truth

Shared workflow rules — state-machine format, 7 capability gates (interview / validation / research / longrun / execution / memory / handoff), 6-field delegation template, approval-gate policy, dispatch policy, back-edge matrix, `.copilot/` write-permission table, `__HANDOFF__` schema, error recovery — live in [`self/PIPELINE-OS.md`](../../PIPELINE-OS.md). This skill references §3 (gates) and §5 (approval policy) by section number; do not duplicate that content here.
```

- [ ] **Step 3: Replace the back-edge AskUserQuestion line with the §5 reference**

The current file contains the exact line: `**Back-edges (gated behind AskUserQuestion):**` (at L75 in the existing file). Replace that single line with:

```markdown
**Back-edges (approval-gated per PIPELINE-OS §5 case ②):**
```

Also remove the interview-gate HARD-GATE block's "Use AskUserQuestion" prescription if it conflicts — the HARD-GATE itself remains; only its prose pointing to AskUserQuestion is softened. Specifically inside the `<HARD-GATE id="interview-gate">` block, replace `Use AskUserQuestion to clarify scope, constraints, and success criteria.` with `Use the interview skill (deep-interview / quick-interview / user-preference-interview) to clarify scope, constraints, and success criteria — per PIPELINE-OS §3 interview-gate. AskUserQuestion is reserved for the 6 cases listed in §5.`

- [ ] **Step 4: Commit**

```powershell
git add self/skills/research-workflow/SKILL.md
git commit -m "docs: research-workflow SKILL.md references PIPELINE-OS.md instead of duplicating"
```

### Task 8.4: Add registration functions to `install.py`

**Files:**
- Modify: `self/install.py`

- [ ] **Step 1: Add the script-path constants near the top (after `HOOK_SCRIPT = ...`)**

Locate the line `HOOK_SCRIPT = SELF_DIR / "hooks" / "scripts" / "scientist_guardrails.py"` and add immediately after:

```python
SESSION_MEMORY_INJECTOR_SCRIPT = SELF_DIR / "hooks" / "scripts" / "session_start_memory_injector.py"
DISPATCH_REMINDER_SCRIPT = SELF_DIR / "hooks" / "scripts" / "user_prompt_dispatch_reminder.py"
LOOP_ARMER_SCRIPT = SELF_DIR / "hooks" / "scripts" / "post_tool_loop_armer.py"
```

- [ ] **Step 2: Add three `register_*` functions before `def main()`**

```python
def register_session_memory_injector(target: Path, dry_run: bool) -> None:
    step("Step 3c/5: register SessionStart memory injector hook")
    if not SESSION_MEMORY_INJECTOR_SCRIPT.is_file():
        warn(f"injector script missing: {SESSION_MEMORY_INJECTOR_SCRIPT}; skipping")
        return
    _add_session_start_hook(
        target=target,
        dry_run=dry_run,
        script=SESSION_MEMORY_INJECTOR_SCRIPT,
        identifier_substr="session_start_memory_injector.py",
        timeout=10,
    )


def register_dispatch_reminder(target: Path, dry_run: bool) -> None:
    step("Step 3d/5: register UserPromptSubmit dispatch-reminder hook")
    if not DISPATCH_REMINDER_SCRIPT.is_file():
        warn(f"reminder script missing: {DISPATCH_REMINDER_SCRIPT}; skipping")
        return
    _add_user_prompt_submit_hook(
        target=target,
        dry_run=dry_run,
        script=DISPATCH_REMINDER_SCRIPT,
        identifier_substr="user_prompt_dispatch_reminder.py",
        timeout=5,
    )


def register_loop_armer(target: Path, dry_run: bool) -> None:
    step("Step 3e/5: register PostToolUse loop-armer hook")
    if not LOOP_ARMER_SCRIPT.is_file():
        warn(f"loop-armer script missing: {LOOP_ARMER_SCRIPT}; skipping")
        return
    _add_post_tool_use_hook(
        target=target,
        dry_run=dry_run,
        script=LOOP_ARMER_SCRIPT,
        matcher="Bash",
        identifier_substr="post_tool_loop_armer.py",
        timeout=5,
    )
```

- [ ] **Step 3: Add the generic helper functions used above**

```python
def _load_settings(target: Path) -> tuple[Path, dict]:
    settings_dir = target / ".claude"
    settings_path = settings_dir / "settings.json"
    if settings_path.is_file():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        settings = {}
    return settings_path, settings


def _save_settings(settings_path: Path, settings: dict) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _already_registered(blocks: list, identifier_substr: str) -> bool:
    for b in blocks:
        if not isinstance(b, dict):
            continue
        for hk in b.get("hooks", []):
            if not isinstance(hk, dict):
                continue
            if identifier_substr in (hk.get("command", "") or ""):
                return True
    return False


def _add_session_start_hook(target: Path, dry_run: bool, script: Path,
                            identifier_substr: str, timeout: int) -> None:
    settings_path, settings = _load_settings(target)
    blocks = settings.setdefault("hooks", {}).setdefault("SessionStart", [])
    if _already_registered(blocks, identifier_substr):
        info(f"  {identifier_substr} already registered; skipping.")
        return
    cmd = f'python "{script.resolve()}"'.replace("\\", "/")
    blocks.append({
        "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]
    })
    info(f"  added SessionStart hook: {cmd}")
    if not dry_run:
        _save_settings(settings_path, settings)


def _add_user_prompt_submit_hook(target: Path, dry_run: bool, script: Path,
                                 identifier_substr: str, timeout: int) -> None:
    settings_path, settings = _load_settings(target)
    blocks = settings.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    if _already_registered(blocks, identifier_substr):
        info(f"  {identifier_substr} already registered; skipping.")
        return
    cmd = f'python "{script.resolve()}"'.replace("\\", "/")
    blocks.append({
        "matcher": "*",
        "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]
    })
    info(f"  added UserPromptSubmit hook: {cmd}")
    if not dry_run:
        _save_settings(settings_path, settings)


def _add_post_tool_use_hook(target: Path, dry_run: bool, script: Path,
                            matcher: str, identifier_substr: str, timeout: int) -> None:
    settings_path, settings = _load_settings(target)
    blocks = settings.setdefault("hooks", {}).setdefault("PostToolUse", [])
    if _already_registered(blocks, identifier_substr):
        info(f"  {identifier_substr} already registered; skipping.")
        return
    cmd = f'python "{script.resolve()}"'.replace("\\", "/")
    blocks.append({
        "matcher": matcher,
        "hooks": [{"type": "command", "command": cmd, "timeout": timeout}]
    })
    info(f"  added PostToolUse hook ({matcher}): {cmd}")
    if not dry_run:
        _save_settings(settings_path, settings)
```

- [ ] **Step 4: Call the three new registrars inside `main()`**

Locate the existing `register_research_copilot_guard(target, args.dry_run)` call inside `def main()` and insert the three new calls immediately after it:

```python
    register_session_memory_injector(target, args.dry_run)
    register_dispatch_reminder(target, args.dry_run)
    register_loop_armer(target, args.dry_run)
```

- [ ] **Step 5: Dry-run the installer**

Run: `python self/install.py --dry-run --skip-deps --skip-verify`
Expected: output includes "Step 3c/5", "Step 3d/5", "Step 3e/5" and "added SessionStart / UserPromptSubmit / PostToolUse hook" lines pointing at the 3 new scripts.

- [ ] **Step 6: Real install (writes `.claude/settings.json`)**

Run: `python self/install.py --skip-deps --skip-verify`
Expected: "Install complete." line at the end.

- [ ] **Step 7: Verify settings.json mentions all 3 new scripts**

Run: `Select-String -Path .claude/settings.json -Pattern 'session_start_memory_injector|user_prompt_dispatch_reminder|post_tool_loop_armer' | Measure-Object`
Expected: `Count : 3`

- [ ] **Step 8: Commit**

```powershell
git add self/install.py
git commit -m "feat: install.py registers 3 new hooks (memory-injector, dispatch-reminder, loop-armer)"
```

---

## Phase 9 — End-to-End Smoke and Acceptance Evidence

### Task 9.1: Full hook test suite passes

- [ ] **Step 1: Run the entire hook test directory**

Run: `python -m pytest self/hooks/scripts/__tests__/ -v`
Expected: all tests pass; record the count (e.g. `18 passed`).

### Task 9.2: Measure byte budgets

- [ ] **Step 1: Print agent file sizes**

Run (PowerShell):

```powershell
Get-ChildItem self/agents/*.agent.md | Sort-Object Name | ForEach-Object {
  [PSCustomObject]@{Name=$_.Name; KB=[Math]::Round($_.Length/1KB,1)}
} | Format-Table -AutoSize
```

Expected:
- `research-copilot.agent.md` ≤ 5.0
- `copilot-experiment.agent.md` ≤ 3.5
- `copilot-ideation.agent.md` ≤ 3.5
- `copilot-reviewer.agent.md` ≤ 3.5
- `copilot-writer.agent.md` ≤ 4.0
- `copilot-literature.agent.md` ≤ 3.0
- `copilot-polisher.agent.md` ≤ 3.0
- `copilot-rebuttal.agent.md` ≤ 3.0

- [ ] **Step 2: Print PIPELINE-OS.md + AGENTS.md sizes**

Run: `Get-ChildItem self/PIPELINE-OS.md, self/AGENTS.md | ForEach-Object { [PSCustomObject]@{Name=$_.Name; KB=[Math]::Round($_.Length/1KB,1)} }`
Expected: PIPELINE-OS ≤ 8 KB; AGENTS ≤ 5 KB.

### Task 9.3: Acceptance evidence per pain

Add the following section to the spec:

**Files:**
- Modify: `docs/superpowers/specs/2026-05-23-self-agent-refactor-design.md`

- [ ] **Step 1: Append an `## Acceptance Evidence (Phase 9)` section**

```markdown

## 17. Acceptance Evidence (Phase 9 result)

| Pain | Evidence command | Expected result |
|---|---|---|
| ① files too long | `Get-ChildItem self/agents/*.agent.md, self/PIPELINE-OS.md, self/AGENTS.md` | conductor ≤5KB, others ≤4KB, PIPELINE-OS ≤8KB, AGENTS ≤5KB |
| ② no MCP research | `python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py` | 4 passed |
| ③ no sub-agent dispatch | `python -m pytest self/hooks/scripts/__tests__/test_user_prompt_dispatch_reminder.py` | 7 passed; in real session a brainstorming prompt triggers the reminder |
| ④ no memory | Fresh session in this repo: SessionStart log shows `[memory-injector] Loaded research state from .copilot/:` followed by handoff summaries | injection ≤ 2 KB |
| ⑤ no loop | `python -m pytest self/hooks/scripts/__tests__/test_post_tool_loop_armer.py` | 6 passed; in real long experiment `.copilot/.loop-armed` appears |
| ⑥ walks one step asks one step | `Select-String -Path self/agents/*.agent.md -Pattern 'AskUserQuestion' | Measure-Object` | minimal hits; only at §5 cases |
```

- [ ] **Step 2: Commit**

```powershell
git add docs/superpowers/specs/2026-05-23-self-agent-refactor-design.md
git commit -m "docs: append Phase 9 acceptance evidence section to refactor spec"
```

### Task 9.4: Mini end-to-end pipeline dry-run

This task verifies the SessionStart injector + dispatch-reminder + memory-gate interact correctly. It does NOT launch real training (no GPU dependency).

- [ ] **Step 1: Open a fresh shell and start a fresh Claude Code session in this repo**

Manual step: invoke a new Claude Code session. Verify on session start that the chat receives the `[memory-injector]` block listing the current `__HANDOFF__` contents of all 6 `.copilot/*.md` files.

- [ ] **Step 2: From the main thread submit the brainstorming prompt**

Manual prompt: `想找几个改进方向，帮我头脑风暴一下`
Verify: `[dispatch-reminder]` block appears in the new chat turn, recommending `Agent(subagent_type='copilot-ideation')`. Verify main thread DOES dispatch to copilot-ideation (not inline brainstorm).

- [ ] **Step 3: Inside copilot-ideation, attempt to write to `.copilot/ideas.md` before calling any MCP**

Expected: `research_copilot_guard.py` Pattern 6 blocks the write with the research-gate message. After ≥2 arxiv-search calls with distinct queries, the write proceeds.

- [ ] **Step 4: Confirm `__HANDOFF__` is appended when ideation reaches END**

Run: `Get-Content .copilot/ideas.md -Tail 10`
Expected: `## __HANDOFF__` block with `last_updated`, `written_by: copilot-ideation`, and a `key_facts:` list reflecting the new round.

- [ ] **Step 5: Record findings in `.copilot/pipelines/2026-05-23-smoke-acceptance.md`**

Write a brief ledger:

```markdown
# 2026-05-23 Refactor v2 Smoke Acceptance

- SessionStart injector: ✓ shows handoff summaries
- Dispatch reminder: ✓ fires on brainstorm prompt
- Research-gate (Pattern 6): ✓ blocks idea write without ≥2 MCP queries
- Handoff-gate: ✓ END state appends __HANDOFF__ to ideas.md

## __HANDOFF__
- last_updated: 2026-05-23T00:00:00Z
- written_by: smoke-acceptance
- key_facts:
  - All 6 pains have verifiable acceptance evidence
- next_owner: (none)
```

- [ ] **Step 6: Commit**

```powershell
git add .copilot/pipelines/2026-05-23-smoke-acceptance.md
git commit -m "docs: smoke acceptance log for self/ agent refactor v2"
```

---

## Self-Review

After completing Phase 9, run the spec/plan cross-check:

- **Spec coverage**: each of the 6 pains has a corresponding phase. Confirm via `Acceptance Evidence` table.
- **Placeholders**: this plan contains zero "TBD" / "TODO" markers; every code block is complete.
- **Type consistency**: `Violation` class is reused from existing `research_copilot_guard.py` (do NOT re-declare it). `__HANDOFF__` schema is fixed across all 6 agents' writes. `loop_id` field name is consistent across `experiments.md` and the loop-armer flag.
- **Cross-file references**: every agent file references `PIPELINE-OS.md §N` (no broken section number — PIPELINE-OS has §1–§10).

If anything fails, fix inline and continue.
