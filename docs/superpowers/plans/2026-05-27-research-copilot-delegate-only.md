# Research-Copilot Delegate-Only Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the four-layer delegate-only enforcement for `research-copilot` (tools allowlist + per-invocation model override + PLAN_PUBLISHED state + guard pattern 7) so the conductor cannot do inline domain work and so sub-agents run on their declared models.

**Architecture:** Edit three files (`PIPELINE-OS.md`, `research-copilot.agent.md`, `research_copilot_guard.py`) + add one new test file (`test_research_copilot_guard_pattern7.py`) + one spec doc nudge (`research-copilot-guard.hook.md`). TDD: write the failing pattern-7 tests first, then implement, then wire into `main()`. Frontmatter and state-table edits are validation-only (no automated tests beyond visual diff + existing meta-tests).

**Tech Stack:** Python 3.11, pytest. PowerShell on Windows for test commands. Existing `research_copilot_guard.py` pattern (re-use `_iter_transcript_tool_uses` helper and `load_state()` helper).

**Spec:** `docs/superpowers/specs/2026-05-27-research-copilot-delegate-only-design.md`

---

## File Structure

```
self/PIPELINE-OS.md                                          [EDIT]
  §4 — template extended 6→7 fields (Model: row + sub-agent model table)
  §6 — dispatch policy mentions plan-list rule for Mode B

self/agents/research-copilot.agent.md                        [EDIT]
  frontmatter — add tools: allowlist line
  state table — insert PLAN_PUBLISHED row; update MODE_A/MODE_B/AWAIT_SUBAGENT_END rows

self/hooks/scripts/research_copilot_guard.py                 [EDIT]
  + check_pattern_7_no_plan_list(tool_name, tool_input, state, transcript_path)
  + wired into main() check loop

self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py   [NEW]
  7 unit tests + 1 integration test (main() end-to-end with monkeypatching)

self/hooks/research-copilot-guard.hook.md                    [EDIT]
  spec note — registration unchanged; pattern 7 added to scope description
```

No restructuring; existing layout. Each task is one small action with a single commit at the end (or grouped with the immediately preceding action where they form a logical TDD trio).

---

## Task 1: Update `PIPELINE-OS.md §4` — extend delegation template from 6 to 7 fields

**Files:**
- Modify: `self/PIPELINE-OS.md` (§4 section, lines 66–77 of the current file)

- [ ] **Step 1: Edit §4 — replace the 6-field template with the 7-field version**

Open `self/PIPELINE-OS.md`. Find the existing `## §4. Delegation Template (6-field)` section. Replace it with the following block:

````markdown
## §4. Delegation Template (7-field)

Every `Task()` / `Agent()` call from research-copilot or any coordinator MUST include all seven fields:

```
Context & stage: <user is at SN; last round did X; why now>
Goal: <what this round completes; what it explicitly does NOT do>
Facts: <.copilot/<file>.md paths, workspace paths, PDFs>
Constraints: <target venue, style, do-not-touch files, no fabricated citations>
Expected output: <conclusion / file diff / draft / table — concrete>
Stop condition: <when to stop and report instead of pushing through>
Model: <haiku | sonnet | opus>     ← matches sub-agent's declared model
```

The 7th field `Model:` MUST be passed as the `model` parameter of the `Agent` tool call (NOT only mentioned in prose). The value MUST match the sub-agent's declared frontmatter model:

| Sub-agent | Required Model value |
|---|---|
| `copilot-literature` | `haiku` |
| `copilot-ideation` | `opus` |
| `copilot-experiment` | `sonnet` |
| `copilot-writer` | `sonnet` |
| `copilot-polisher` | `sonnet` |
| `copilot-reviewer` | `opus` |
| `copilot-rebuttal` | `sonnet` |

Rationale: per Claude Code sub-agent docs, the per-invocation `model` parameter is item 2 in the model resolution chain (above the frontmatter `model:` field). Passing it explicitly bypasses any failure of item 3 to take effect.
````

- [ ] **Step 2: Sanity-check by grep**

Run:

```powershell
Select-String -Path self/PIPELINE-OS.md -Pattern "Delegation Template \(7-field\)"
```

Expected: 1 hit at the new §4 heading.

Run:

```powershell
Select-String -Path self/PIPELINE-OS.md -Pattern "^\| ``copilot-literature`` \| ``haiku`` \|"
```

Expected: 1 hit (the sub-agent → model row).

- [ ] **Step 3: Commit**

```powershell
git add self/PIPELINE-OS.md
git commit -m "docs(PIPELINE-OS): extend delegation template to 7 fields with Model

Adds explicit Model field requirement to bypass sub-agent frontmatter
model fall-through. Sub-agents now must be invoked with per-invocation
model parameter matching their declared frontmatter model.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Update `PIPELINE-OS.md §6` — add plan-list rule for Mode B

**Files:**
- Modify: `self/PIPELINE-OS.md` (§6 section, lines 96–101 of the current file)

- [ ] **Step 1: Edit §6 — append plan-list paragraph**

Find the existing `## §6. Sub-agent Dispatch Policy` section. The current last paragraph reads:

> Every `Task()` MUST carry §4's 6-field template. Otherwise `user_prompt_dispatch_reminder.py` re-injects guidance on the next turn.

Replace it with:

```markdown
Every `Task()` MUST carry §4's 7-field template (including `Model:`). Otherwise `user_prompt_dispatch_reminder.py` re-injects guidance on the next turn.

**Mode B plan-list rule.** When `research-copilot` enters `MODE_B_PIPELINE`, it MUST publish a TaskCreate plan list (one task per planned sub-agent dispatch) before any `Agent()` call. The conductor transitions `MODE_B_PIPELINE → PLAN_PUBLISHED → AWAIT_SUBAGENT_END`; `research_copilot_guard.py` pattern 7 denies any `Agent(copilot-*)` call made from `MODE_B_PIPELINE` / `PLAN_PUBLISHED` / `AWAIT_SUBAGENT_END` with zero TaskCreate calls in the current turn. Mode A (single dispatch) is exempt.
```

- [ ] **Step 2: Sanity-check by grep**

Run:

```powershell
Select-String -Path self/PIPELINE-OS.md -Pattern "Mode B plan-list rule"
```

Expected: 1 hit.

- [ ] **Step 3: Commit**

```powershell
git add self/PIPELINE-OS.md
git commit -m "docs(PIPELINE-OS): add Mode B plan-list rule in §6

research-copilot must publish a TaskCreate plan list before any
Agent() call in Mode B pipeline. Guard pattern 7 enforces this.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Add `tools:` allowlist to `research-copilot.agent.md` frontmatter

**Files:**
- Modify: `self/agents/research-copilot.agent.md` (frontmatter, lines 1–7)

- [ ] **Step 1: Replace the frontmatter block**

Find the existing frontmatter at the top of the file:

```yaml
---
name: research-copilot
description: "Conductor for the full S1-S7 research pipeline. Routes user requests to one of 7 copilot-* sub-agents OR delegates a multi-stage pipeline. Owns .copilot/state.md and .copilot/decisions.md. Triggers: '下一步' / 'what's next' / '全流程' / '走一遍 pipeline' / 'submission sprint' / 'rebuttal prep' / 'ideation re-check'. Mode A = routing (single dispatch). Mode B = pipeline (sequenced dispatch with approval gates per PIPELINE-OS §5)."
argument-hint: "Current stage / target deadline / venue (optional)"
model: sonnet
color: magenta
---
```

Replace it with (only the `tools:` line is new):

```yaml
---
name: research-copilot
description: "Conductor for the full S1-S7 research pipeline. Routes user requests to one of 7 copilot-* sub-agents OR delegates a multi-stage pipeline. Owns .copilot/state.md and .copilot/decisions.md. Triggers: '下一步' / 'what's next' / '全流程' / '走一遍 pipeline' / 'submission sprint' / 'rebuttal prep' / 'ideation re-check'. Mode A = routing (single dispatch). Mode B = pipeline (sequenced dispatch with approval gates per PIPELINE-OS §5)."
argument-hint: "Current stage / target deadline / venue (optional)"
model: sonnet
color: magenta
tools: Read, Grep, Glob, Agent, TaskCreate, TaskUpdate, TaskList, TaskGet, Skill, AskUserQuestion, Edit, Write
---
```

- [ ] **Step 2: Sanity-check by grep**

Run:

```powershell
Select-String -Path self/agents/research-copilot.agent.md -Pattern "^tools: Read, Grep, Glob, Agent, TaskCreate"
```

Expected: 1 hit.

- [ ] **Step 3: Commit**

```powershell
git add self/agents/research-copilot.agent.md
git commit -m "feat(research-copilot): restrict tools to delegate-only allowlist

Frontmatter tools: removes Bash, PowerShell, all MCP, WebFetch,
NotebookEdit, cron/wakeup/monitor. The conductor now can only
dispatch, plan via Task tools, read, ask, and write to its
.copilot/ artifacts.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Insert `PLAN_PUBLISHED` state and update related rows in state table

**Files:**
- Modify: `self/agents/research-copilot.agent.md` (state table, currently lines 18–27)

- [ ] **Step 1: Replace the state table**

Find the existing `## My Unique State Table` section. Replace the existing table with:

```markdown
| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/state.md` (incl. `__HANDOFF__`); read SessionStart memory inject context | memory-gate | Stage cursor summary | [DIAGNOSED] |
| DIAGNOSED | One-sentence diagnosis + one-sentence recommendation | none | Diagnosis + recommendation | [MODE_A_ROUTING, MODE_B_PIPELINE, PAUSED] |
| MODE_A_ROUTING | Single `Agent()` dispatch with 7-field template (incl. `Model:` matching sub-agent frontmatter) | none | Dispatch confirmation | [AWAIT_SUBAGENT_END] |
| MODE_B_PIPELINE | Plan the sequenced dispatches per pipeline template; record in `decisions.md` | none | Pipeline plan | [PLAN_PUBLISHED] |
| PLAN_PUBLISHED | TaskCreate one task per planned dispatch (1 task = 1 sub-agent call); chain with `addBlockedBy` so task N depends on task N-1; update `decisions.md` `__HANDOFF__` with task IDs and dispatch order | none | Task IDs + dispatch order | [AWAIT_SUBAGENT_END] |
| AWAIT_SUBAGENT_END | Audit returned STATE_OUTPUT; check `__HANDOFF__` exists; mark current TaskUpdate=completed; if more tasks remain re-enter `Agent()` for next task | handoff-gate | Audit verdict | [DIAGNOSED, BACK_EDGE_TRIGGERED, PAUSED, PLAN_PUBLISHED, END] |
| BACK_EDGE_TRIGGERED | Increment counter in `state.md`; if 3-strike → AskUserQuestion (§5 case ⑥) | none | Counter state + decision | [MODE_A_ROUTING, MODE_B_PIPELINE, PAUSED] |
| PAUSED | User chose to stop / escalate / switch | none | Pause record | [END] |
| END | Update `state.md` + `decisions.md` `__HANDOFF__` blocks | handoff-gate | Final summary | [] |
```

- [ ] **Step 2: Verify the state-machine meta-test still passes**

The repo has a meta-test `self/hooks/tests/test_state_machine_consistency.py` that parses each agent.md's state table and compares against the hard-coded `STATE_MACHINE` dict in `_copilot_hook_lib.py`. We just added a new state, so the dict will need updating too — but `research-copilot` may not be in the dict (per `2026-05-24` spec, that dict tracks the 7 `copilot-*` sub-agents). Verify:

```powershell
Select-String -Path self/hooks/scripts/_copilot_hook_lib.py -Pattern "research-copilot"
```

If no hit (expected — the dict tracks copilot-* sub-agents only), the meta-test does not cover research-copilot. Skip to Step 4.

If there IS a hit, edit `_copilot_hook_lib.py` to mirror the new states in the `STATE_MACHINE` dict, then run:

```powershell
python -m pytest self/hooks/tests/test_state_machine_consistency.py -v
```

Expected: PASS.

- [ ] **Step 3: Run all existing hook tests to verify no regression**

```powershell
python -m pytest self/hooks/ -v
```

Expected: all tests pass (existing patterns 5, 6, meta-test, etc.).

- [ ] **Step 4: Commit**

```powershell
git add self/agents/research-copilot.agent.md
git commit -m "feat(research-copilot): add PLAN_PUBLISHED state to state table

Mode B pipeline now transitions MODE_B_PIPELINE → PLAN_PUBLISHED →
AWAIT_SUBAGENT_END. PLAN_PUBLISHED mandates one TaskCreate per
planned dispatch with addBlockedBy chain. Mode A unchanged.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Write failing unit tests for pattern 7

**Files:**
- Create: `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py`
- Test runner: pytest, same harness used by pattern 5/6 tests

- [ ] **Step 1: Create the test file**

Create `self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py` with the following content:

```python
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
```

- [ ] **Step 2: Run the test file — confirm all tests fail with ImportError**

```powershell
python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py -v
```

Expected: 8 tests **fail** with `ImportError: cannot import name 'check_pattern_7_no_plan_list' from 'research_copilot_guard'`. This confirms the tests are wired correctly and that the function does not yet exist.

- [ ] **Step 3: Do not commit yet — wait for implementation (Task 6)**

---

## Task 6: Implement `check_pattern_7_no_plan_list` in `research_copilot_guard.py`

**Files:**
- Modify: `self/hooks/scripts/research_copilot_guard.py` (insert new function before `main()`)

- [ ] **Step 1: Add the new function**

Open `self/hooks/scripts/research_copilot_guard.py`. Find the line `def main() -> int:` (around line 275). Just above it (after `check_pattern_3_delegation` and `load_state`), insert:

```python
def check_pattern_7_no_plan_list(tool_name: str, tool_input: dict[str, Any],
                                 state: dict[str, Any],
                                 transcript_path: str | None) -> str | None:
    """Pattern 7 (plan-list-gate): in Mode B pipeline, every Agent dispatch
    must be preceded by a TaskCreate plan list in the current turn."""
    if tool_name != "Agent":
        return None
    current_state = state.get("current_state", "UNINITIALIZED")
    if current_state not in {"MODE_B_PIPELINE", "PLAN_PUBLISHED",
                             "AWAIT_SUBAGENT_END"}:
        return None
    sub_type = str((tool_input or {}).get("subagent_type", ""))
    if not sub_type.startswith("copilot-"):
        return None
    if not transcript_path:
        return None
    task_count = 0
    for entry in _iter_transcript_tool_uses(transcript_path):
        if entry["name"] == "TaskCreate":
            task_count += 1
    if task_count == 0:
        return ("Blocked by research-copilot-guard (pattern 7): Mode B "
                "pipeline dispatch requires a published TaskCreate plan "
                "list (one task per planned dispatch). Call TaskCreate "
                "for each stage in order before invoking Agent().")
    return None
```

- [ ] **Step 2: Run the unit tests — confirm all 8 pass**

```powershell
python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py -v
```

Expected: 8 tests **pass**.

- [ ] **Step 3: Do not commit yet — wait for main() wiring (Task 7)**

---

## Task 7: Wire `check_pattern_7_no_plan_list` into `main()` decision loop

**Files:**
- Modify: `self/hooks/scripts/research_copilot_guard.py` (the `main()` function check loop, currently at lines 304–312)

- [ ] **Step 1: Edit the check loop in `main()`**

Find the existing check loop in `main()`:

```python
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

Replace it with:

```python
    for check in (
        check_pattern_1_experiment(tool_name, tool_input),
        check_pattern_3_delegation(tool_name, tool_input, state),
        check_pattern_5_no_memory_read(tool_name, tool_input, transcript_path),
        check_pattern_6_no_research_mcp(tool_name, tool_input, transcript_path),
        check_pattern_7_no_plan_list(tool_name, tool_input, state, transcript_path),
    ):
        if check:
            print(json.dumps(deny(check)))
            return 0
```

- [ ] **Step 2: Run all hook tests — confirm no regression**

```powershell
python -m pytest self/hooks/scripts/__tests__/ -v
```

Expected: all tests in patterns 5, 6, 7 pass. (No tests cover patterns 1 / 3 at the unit level in `scripts/__tests__/`; those are exercised by the integration script.)

```powershell
python -m pytest self/hooks/ -v
```

Expected: all tests under `self/hooks/` pass (including `test_state_machine_consistency.py` and the existing `self/hooks/tests/` directory).

- [ ] **Step 3: Commit pattern 7 + tests + wiring together**

```powershell
git add self/hooks/scripts/research_copilot_guard.py self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py
git commit -m "feat(research-copilot-guard): add pattern 7 (plan-list-gate)

In Mode B pipeline (MODE_B_PIPELINE / PLAN_PUBLISHED /
AWAIT_SUBAGENT_END states), deny any Agent(copilot-*) call from
research-copilot when no TaskCreate appears earlier in the
current turn. Mode A single dispatch and non-copilot subagent
types are exempt. Fail-open when transcript_path is empty.

8 unit tests added.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: Update `research-copilot-guard.hook.md` spec note

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md` (the prose at the top after frontmatter)

- [ ] **Step 1: Append a pattern 7 line to the spec note**

Open `self/hooks/research-copilot-guard.hook.md`. After the `## Active-Agent Scoping` section, append:

```markdown
## Patterns

The Python guard checks five patterns in order; first deny short-circuits the rest. All five fire only when the active sub-agent is `research-copilot`:

| # | Name | Tool match | When it denies |
|---|---|---|---|
| 1 | experiment-script | `Bash`, `PowerShell` | Non-read-only command containing experiment keywords (`train.py`, `wandb`, `torchrun`, …) |
| 3 | state-mandated-delegation | `Agent`, `Bash`, `PowerShell`, `Write`, `Edit` | Current state is `S2_IDEATION` or `S3_EXPERIMENT` and the tool call is not the correct delegation |
| 5 | memory-gate | `Write`, `Edit` | Writing to `.copilot/{ideas,experiments,literature,decisions}.md` with no prior `Read` of any `.copilot/*.md` in the session |
| 6 | research-gate | `Write`, `Edit` | Writing a `## Idea` block to `.copilot/ideas.md` with fewer than 2 distinct paper-retrieval MCP queries in the session |
| 7 | plan-list-gate | `Agent` | research-copilot is in `MODE_B_PIPELINE` / `PLAN_PUBLISHED` / `AWAIT_SUBAGENT_END` state and dispatches `Agent(copilot-*)` with zero `TaskCreate` calls in the current turn |

Patterns 5, 6, 7 each have a dedicated unit test file under `self/hooks/scripts/__tests__/`.

The frontmatter `tools:` allowlist on `research-copilot.agent.md` is a stronger, complementary control: it prevents the conductor from ever invoking `Bash` / `PowerShell` / `WebFetch` / MCP tools in the first place, so patterns 1, 5, 6 act as inner safety net rather than primary defense.
```

- [ ] **Step 2: Sanity-check by grep**

```powershell
Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "plan-list-gate"
```

Expected: 1 hit.

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "docs(research-copilot-guard): add patterns table incl. pattern 7

Document the five active patterns (1, 3, 5, 6, 7) in the hook spec
and note that the new frontmatter tools allowlist makes patterns
1/5/6 secondary defenses.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: Full regression run + acceptance evidence

**Files:**
- No edits; this is a verification gate.

- [ ] **Step 1: Run the entire `self/hooks/` test suite**

```powershell
python -m pytest self/hooks/ -v
```

Expected: all tests pass. Capture the pass count for the commit message of Task 10.

- [ ] **Step 2: Verify acceptance criteria from spec §14**

Run each:

```powershell
# Criterion 1: tools allowlist present
Select-String -Path self/agents/research-copilot.agent.md -Pattern "^tools: Read, Grep, Glob, Agent"
```

Expected: 1 hit.

```powershell
# Criterion 2: 7th field Model: present in §4
Select-String -Path self/PIPELINE-OS.md -Pattern "^Model: <haiku"
```

Expected: 1 hit.

```powershell
# Criterion 3: PLAN_PUBLISHED mentioned ≥3 times in research-copilot.agent.md
$count = (Select-String -Path self/agents/research-copilot.agent.md -Pattern "PLAN_PUBLISHED" | Measure-Object).Count
if ($count -lt 3) { Write-Error "Expected ≥3 hits, got $count" } else { Write-Output "PLAN_PUBLISHED hits: $count (>=3)" }
```

Expected: ≥3.

```powershell
# Criterion 4: pattern 7 tests pass
python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py -v
```

Expected: 8 passed.

```powershell
# Criterion 5: pattern 5/6 regression
python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern5.py self/hooks/scripts/__tests__/test_research_copilot_guard_pattern6.py -v
```

Expected: all passed.

- [ ] **Step 3: Inspect git log to confirm commit chain**

```powershell
git log --oneline -10
```

Expected: the 6 commits from Tasks 1, 2, 3, 4, 7, 8 visible, plus the earlier spec commit (`e8c05c1`).

- [ ] **Step 4: No commit — this is a verification gate only**

If any of Steps 1–3 fail, fix the underlying task before proceeding to Task 10.

---

## Task 10: Manual smoke test note (offline; user runs)

**Files:**
- No edits.

- [ ] **Step 1: Print the smoke test instructions for the user**

Output the following block as a chat message to the user, asking them to run it after `/clear`:

```
Smoke test (run after /clear to pick up new tools allowlist):

1. Dispatch: @research-copilot 全流程跑一遍 NeurIPS submission sprint
2. Verify: research-copilot tries to call Bash / PowerShell / any MCP →
   expect "Tool not available" error (tools allowlist took effect).
3. Verify: research-copilot enters MODE_B_PIPELINE then PLAN_PUBLISHED →
   /tasks shows ~7 dispatch tasks with addBlockedBy chain.
4. Verify: any Agent() call from research-copilot includes a model=
   parameter matching the target sub-agent's declared frontmatter
   (haiku for copilot-literature, opus for copilot-ideation/reviewer,
   sonnet for the rest).
5. (Negative case) Manually clear the task list, ask research-copilot
   to dispatch copilot-literature → expect "Blocked by
   research-copilot-guard (pattern 7)" with prescription to call
   TaskCreate first.

If steps 2 or 4 fail, fall back to:
- Step 2 fail → hook-side deny list expansion (see spec §10.4).
- Step 4 fail → CLAUDE_CODE_SUBAGENT_MODEL env var via SessionStart
  hook (see spec §10.5).
```

- [ ] **Step 2: No commit. Plan complete.**

---

## Spec coverage check

| Spec §  | Plan task | Notes |
|---|---|---|
| §5 (tools allowlist) | Task 3 | Frontmatter edit; commit-only, no test (existing meta-tests do not cover research-copilot) |
| §6 (Model: field in §4 template) | Task 1 | Doc edit |
| §6.1 (§4 sub-agent → model table) | Task 1 | Doc edit |
| §6.2 (keep frontmatter `model:` in copilots) | — | No-op; we explicitly do not touch the 7 copilot-* frontmatters |
| §7.1 (PLAN_PUBLISHED state table) | Task 4 | State table replaced |
| §7.2 (Mode A exempt) | Task 6 | Pattern 7 logic gates on state ∈ {MODE_B, PLAN_PUBLISHED, AWAIT_SUBAGENT_END} |
| §7.3 (PLAN_PUBLISHED rules) | Task 4 | State table row + state-table prose |
| §8 (pattern 7) | Tasks 5, 6, 7 | TDD: test → impl → wire |
| §9.1 (8 unit tests) | Task 5 | Test 8 from spec "only fires when research-copilot is active" replaced by `test_pattern_7_skips_when_tool_is_not_agent` (already-covered scoping is enforced by `main()`'s `is_research_copilot_session` gate; spec test 8 would only assert at integration level, which is the user's manual smoke step in Task 10) |
| §9.2 (manual integration smoke) | Task 10 | User runs |
| §9.3 (regression on patterns 5/6) | Task 9 | Verification gate |
| §11 (phased rollout) | Tasks 1–10 mirror phases 1–7 |
| §12 risks §10.3/10.4/10.5 | Task 10 fallback notes | Documented in smoke instructions |
| §14 acceptance criteria 1–7 | Task 9 | Each criterion has a verification command |

## Self-review notes (inline fixes applied during plan writing)

1. Test 8 from spec §9.1 ("only fires when research-copilot is active") cannot be a pure unit test on `check_pattern_7_no_plan_list` — that function does not check the active agent (the check happens upstream in `main()` via `is_research_copilot_session()`). Replaced it with `test_pattern_7_skips_when_tool_is_not_agent` (tests the early-return guard) and moved the active-agent assertion to Task 10's manual smoke (Step 5 in the smoke block).
2. Step 2 of Task 4 checks for `research-copilot` in `_copilot_hook_lib.py` to determine whether the meta-test needs updating; per the 2026-05-24 spec the dict tracks copilot-* only, so the meta-test should pass unchanged, but the conditional handles the case where someone added research-copilot to the dict later.
3. Each TDD pair (Task 5 → Task 6) commits together at the end of Task 7, so the failing-tests commit is never published alone. This matches existing project convention seen in commit `afb677c` (test added alongside its meta-source).
