# Research-Copilot Delegate-Only Enforcement Design

- Date: 2026-05-27
- Scope: Make `research-copilot` a tools-restricted delegate-only conductor; force per-invocation model override on every sub-agent dispatch; mandate a TaskCreate plan list before any Mode B (multi-stage) pipeline dispatch.
- Status: Draft, awaits user review
- Predecessors:
  - `2026-05-21-research-copilot-workflow-enforcement-design.md` (introduced `research_copilot_guard.py` with patterns 1/3)
  - `2026-05-23-self-agent-refactor-design.md` (introduced `PIPELINE-OS.md`, 8 sub-agents, dispatch-reminder hook)
  - `2026-05-24-copilot-subagent-guard-design.md` (introduced `copilot_write_guard.py`, `copilot_subagent_stop.py`)

## 1. Problem Statement

Two independent failure modes observed in real research-copilot sessions:

### Failure mode A — Sub-agent model resolution falls through to main session

Per the official Claude Code sub-agent docs, model selection follows this priority chain:

1. `CLAUDE_CODE_SUBAGENT_MODEL` environment variable
2. Per-invocation `model` parameter on the `Agent` tool call
3. The sub-agent definition's frontmatter `model:` field
4. The main conversation's model (fallback)

Every `copilot-*.agent.md` declares a `model:` field in frontmatter (e.g. `copilot-literature: haiku`, `copilot-ideation: opus`). Despite item 3 of the chain, the user observes every sub-agent dispatch running on whichever model the main session is set to (item 4). Either the current Claude Code release does not honor item 3 reliably, or the `model:` field is not parsed for some reason. In either case the symptom is real and the fix must come from a higher item in the chain.

### Failure mode B — `research-copilot` executes domain work inline instead of dispatching

`research-copilot.agent.md` declares itself routing-only ("I do NOT execute training, search papers, draft sections, polish, review, or rebut — those go to copilot-*"). Three existing enforcement layers exist but do not prevent inline execution:

| Layer | What it does | Why it doesn't stop inline work |
|---|---|---|
| `user_prompt_dispatch_reminder.py` (UserPromptSubmit) | Injects "dispatch a sub-agent first" text when the prompt contains exec-class keywords | Fires only on user prompt entry; once the conductor is running mid-turn, no further injection happens. A reminder is not a block. |
| `research_copilot_guard.py` patterns 1+3 (PreToolUse) | Denies `Bash/PowerShell` running experiment scripts, denies non-Agent writes when state is `S2_IDEATION` / `S3_EXPERIMENT` | Pattern 1 only catches literal experiment scripts; pattern 3 only fires in those two specific states. S1 / S4 / S5 / S6 / S7 inline work is not blocked. MCP calls, `WebFetch`, `NotebookEdit`, `Skill` invocations, generic `Bash` calls are all allowed. |
| `research-copilot.agent.md` prose ("Hard Constraints" section) | Tells the model "never run experiments / never search papers / never write .tex" | Prose constraints can be overridden by the model's own reasoning; not a guaranteed bottom line. |

Observed behavior: first turn → conductor does inline work; user/hook reminder fires → conductor dispatches once; subsequent turns → conductor reverts to inline work.

The user's proposed remedy: force `research-copilot` to build a **TaskCreate task list** before any multi-stage dispatch, where each task corresponds to one sub-agent dispatch, and forbid the conductor from doing any non-routing tool calls.

## 2. Goal & Non-goals

**Goal.** Promote `research-copilot`'s delegate-only contract from "agent self-discipline + targeted hook" to **frontmatter tools allowlist + per-invocation model override + planning-state precondition + hook backup**. Four layers from top to bottom:

1. **Layer 1 (root cause — tools allowlist):** Remove `Bash`, `PowerShell`, `NotebookEdit`, `WebFetch`, all MCP tools from `research-copilot`'s available toolset. The conductor literally cannot invoke them.
2. **Layer 2 (root cause — model override):** Extend `PIPELINE-OS.md §4` delegation template from 6 fields to 7 fields by adding mandatory `Model:` field; the conductor must pass `model=<sub-agent's declared>` on every `Agent(subagent_type=...)` call.
3. **Layer 3 (workflow discipline):** Add a new `PLAN_PUBLISHED` state in `research-copilot`'s state machine. In **Mode B (multi-stage pipeline)** only, the conductor must call `TaskCreate` for every planned dispatch before entering `AWAIT_SUBAGENT_END`. Mode A (single dispatch) is exempt to avoid overhead.
4. **Layer 4 (hook backup):** Extend `research_copilot_guard.py` with a new pattern 7 that fails closed when `research-copilot` is in `MODE_B_PIPELINE` and calls `Agent` without any prior `TaskCreate` in the current turn.

**Non-goals.**
- Refactor of the other 7 `copilot-*` sub-agents.
- Adding similar restrictions to any agent other than `research-copilot`.
- Modifying `_copilot_hook_lib.py`, `copilot_write_guard.py`, `copilot_subagent_stop.py` (those manage sub-agent-side rules, not conductor-side).
- Investigating why item 3 of the model resolution chain is being skipped (we route around it via item 2).
- Migrating the `tools:` field to any per-Agent-subtype restriction syntax — Claude Code's standard `tools:` frontmatter is a flat tool-name allowlist; we use exactly that.

## 3. Decisions (from clarifying interview)

| Question | Choice |
|---|---|
| Approach | Approach A — four layers (tools allowlist + model override + PLAN_PUBLISHED + hook pattern 7) |
| `tools:` allowlist keep `Write` / `Edit`? | Keep. `research-copilot` writes `.copilot/state.md` and `.copilot/decisions.md`; the existing `copilot_write_guard.py` already restricts the writable paths per agent. |
| Enforce `PLAN_PUBLISHED` in Mode A (single dispatch) too? | No. Only Mode B (multi-stage pipeline). Mode A single dispatch is exempt; adding a TaskCreate for one task would be ceremony, not safety. |

## 4. Architecture

### 4.1 Affected files (full list)

```
self/
├── PIPELINE-OS.md                                   [EDIT]   §4 template 6→7 fields; §6 dispatch policy adds plan-list rule for Mode B
├── agents/
│   └── research-copilot.agent.md                    [EDIT]   frontmatter tools allowlist; state table adds PLAN_PUBLISHED; Mode B template references plan-list rule
├── hooks/
│   ├── scripts/
│   │   ├── research_copilot_guard.py                [EDIT]   add pattern 7 (TaskCreate-before-Agent in MODE_B_PIPELINE)
│   │   └── __tests__/
│   │       └── test_research_copilot_guard_pattern7.py  [NEW]  unit tests for pattern 7
│   └── research-copilot-guard.hook.md               [EDIT]   spec note: matcher unchanged, pattern 7 added
docs/superpowers/specs/2026-05-27-research-copilot-delegate-only-design.md   [THIS]
```

### 4.2 Layered enforcement (top to bottom)

```
            ┌─────────────────────────────────────────────────────────────┐
            │ User prompt enters main session                              │
            └─────────────────────┬───────────────────────────────────────┘
                                  ▼
            ┌─────────────────────────────────────────────────────────────┐
            │ user_prompt_dispatch_reminder.py  (existing)                │
            │ Reminder text injected if exec-class keywords detected      │
            └─────────────────────┬───────────────────────────────────────┘
                                  ▼
            ┌─────────────────────────────────────────────────────────────┐
            │ Main session decides: route to research-copilot             │
            └─────────────────────┬───────────────────────────────────────┘
                                  ▼
            ┌─────────────────────────────────────────────────────────────┐
            │ research-copilot starts                                      │
            │ Layer 1: tools allowlist removes Bash/PowerShell/MCP/etc.   │
            │           → conductor literally cannot call them              │
            └─────────────────────┬───────────────────────────────────────┘
                                  ▼
            ┌─────────────────────────────────────────────────────────────┐
            │ State: UNINITIALIZED → DIAGNOSED                             │
            └─────────────────────┬───────────────────────────────────────┘
                                  ▼
                       ┌──────────┴──────────┐
                       ▼                      ▼
                 MODE_A_ROUTING        MODE_B_PIPELINE
                  (single dispatch)     (multi-stage)
                       │                      │
                       │                      ▼
                       │             ┌────────────────────────┐
                       │             │ PLAN_PUBLISHED          │
                       │             │ TaskCreate for each     │
                       │             │ planned dispatch        │
                       │             └──────────┬─────────────┘
                       │                        ▼
                       └────────────► Agent(model=…, subagent_type=…)
                                                │
                                                ▼
                       ┌──────────────────────────────────────────────────┐
                       │ research_copilot_guard.py PreToolUse              │
                       │ Layer 4: pattern 7 (TaskCreate-before-Agent in    │
                       │ MODE_B); existing patterns 1/3/5/6 also apply.    │
                       └────────────────────┬─────────────────────────────┘
                                            ▼
                       ┌──────────────────────────────────────────────────┐
                       │ Sub-agent runs                                    │
                       │ Layer 2: model is the per-invocation override     │
                       │ (item 2 of resolution chain), guaranteed.         │
                       └──────────────────────────────────────────────────┘
```

Layer 1 (tools allowlist) is the load-bearing wall — it removes the option entirely. Layer 4 (hook pattern 7) is the inner safety net that catches the specific failure mode of "dispatching without a plan list."

## 5. Layer 1 — `tools:` allowlist on `research-copilot`

### 5.1 New frontmatter

```yaml
---
name: research-copilot
description: "Conductor for the full S1–S7 research pipeline. Routes user requests to one of 7 copilot-* sub-agents OR delegates a multi-stage pipeline. Owns .copilot/state.md and .copilot/decisions.md. Triggers: '下一步' / 'what's next' / '全流程' / '走一遍 pipeline' / 'submission sprint' / 'rebuttal prep' / 'ideation re-check'. Mode A = routing (single dispatch). Mode B = pipeline (sequenced dispatch with approval gates per PIPELINE-OS §5)."
argument-hint: "Current stage / target deadline / venue (optional)"
model: sonnet
color: magenta
tools: Read, Grep, Glob, Agent, TaskCreate, TaskUpdate, TaskList, TaskGet, Skill, AskUserQuestion, Edit, Write
---
```

### 5.2 Rationale per tool kept

| Tool | Why kept |
|---|---|
| `Read` | Must read `.copilot/*.md`, `PIPELINE-OS.md`, AGENTS.md, sub-agent agent.md files |
| `Grep`, `Glob` | Lightweight surveys of `.copilot/`, `sections/`, `references.bib` (≤5 calls per PIPELINE-OS §6) |
| `Agent` | Core dispatch primitive |
| `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` | Required for `PLAN_PUBLISHED` state and Mode B plan list |
| `Skill` | May invoke `research-workflow` skill or other coordinator skills |
| `AskUserQuestion` | Required at the 6 approval-gate cases per §5 |
| `Edit`, `Write` | Required to write `.copilot/state.md` and `.copilot/decisions.md` (existing `copilot_write_guard.py` enforces the path allowlist; the conductor cannot write anywhere else) |

### 5.3 Rationale per tool removed

| Tool | Why removed |
|---|---|
| `Bash`, `PowerShell` | All shell execution belongs to `copilot-experiment` (training scripts) or to read-only Grep/Glob (which we keep as their own tools) |
| `NotebookEdit` | No `.ipynb` is owned by the conductor |
| `WebFetch` | Web access belongs to `copilot-literature` / skills, not the conductor |
| All `mcp__*` tools | MCP search belongs to `copilot-literature` and `copilot-ideation`; the conductor never queries arxiv / scholar / dblp directly |
| `CronCreate` / `CronDelete` / `CronList` | Long-run cron self-arming belongs to `copilot-experiment` per `post_tool_loop_armer.py` |
| `Monitor`, `ScheduleWakeup` | Same as cron |
| `BashOutput`, `KillShell` | Pair with `Bash`, removed together |
| `ExitPlanMode`, `EnterPlanMode`, `EnterWorktree`, `ExitWorktree` | The conductor does not navigate plan mode or worktrees |
| `TaskOutput`, `TaskStop` | These observe/stop background-task workers spawned by sub-agents; conductor does not own background work |
| `PushNotification` | No notification responsibility |
| All Pencil / chrome-devtools / pdf-text MCP tools | Outside conductor scope |

### 5.4 Compatibility check

Existing PreToolUse hooks (`block_protected_paths.py`, `research_copilot_guard.py`, `copilot_write_guard.py`) remain compatible: their matchers are `Write|Edit|NotebookEdit` and `Bash|PowerShell|Agent|Write|Edit`. With the new allowlist, `Bash` / `PowerShell` / `NotebookEdit` never reach the hook at all (Claude Code rejects the call before hook invocation per the tool restriction contract). This is a strict improvement: hooks act as inner safety net, tool restriction is the outer wall.

## 6. Layer 2 — `PIPELINE-OS.md §4` template extended to 7 fields

### 6.1 New §4 text (replaces the 6-field block)

```markdown
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
```

### 6.2 Why also keep frontmatter `model:` in each sub-agent

We do not remove the frontmatter `model:` field from any `copilot-*.agent.md`. If a future Claude Code release fixes the item-3 fall-through, the frontmatter will continue to work as a fallback. If a sub-agent is invoked outside the conductor (e.g. directly by the user via `@copilot-literature`), the frontmatter still controls the model.

## 7. Layer 3 — `PLAN_PUBLISHED` state in `research-copilot`

### 7.1 Updated state table

```markdown
| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|---|---|---|---|---|
| UNINITIALIZED | Read `.copilot/state.md` (incl. `__HANDOFF__`); read SessionStart memory inject context | memory-gate | Stage cursor summary | [DIAGNOSED] |
| DIAGNOSED | One-sentence diagnosis + one-sentence recommendation | none | Diagnosis + recommendation | [MODE_A_ROUTING, MODE_B_PIPELINE, PAUSED] |
| MODE_A_ROUTING | Single `Agent()` dispatch with 7-field template (incl. `Model:`) | none | Dispatch confirmation | [AWAIT_SUBAGENT_END] |
| MODE_B_PIPELINE | Plan the sequenced dispatches per pipeline template; record in `decisions.md` | none | Pipeline plan | [PLAN_PUBLISHED] |
| PLAN_PUBLISHED | TaskCreate one task per planned dispatch (1 task = 1 sub-agent call); update `decisions.md` `__HANDOFF__` | none | Task IDs + dispatch order | [AWAIT_SUBAGENT_END] |
| AWAIT_SUBAGENT_END | Audit returned STATE_OUTPUT; check `__HANDOFF__` exists; mark current TaskUpdate=completed; if more tasks remain re-enter `Agent()` for next task | handoff-gate | Audit verdict | [DIAGNOSED, BACK_EDGE_TRIGGERED, PAUSED, PLAN_PUBLISHED, END] |
| BACK_EDGE_TRIGGERED | Increment counter in `state.md`; if 3-strike → AskUserQuestion (§5 case ⑥) | none | Counter state + decision | [MODE_A_ROUTING, MODE_B_PIPELINE, PAUSED] |
| PAUSED | User chose to stop / escalate / switch | none | Pause record | [END] |
| END | Update `state.md` + `decisions.md` `__HANDOFF__` blocks | handoff-gate | Final summary | [] |
```

Differences from the current table:

1. `MODE_B_PIPELINE` now transitions to `PLAN_PUBLISHED` (not directly to `AWAIT_SUBAGENT_END`).
2. New `PLAN_PUBLISHED` row with the TaskCreate requirement.
3. `MODE_A_ROUTING` description explicitly mentions the 7-field template.
4. `AWAIT_SUBAGENT_END` can now loop back to `PLAN_PUBLISHED` (more tasks pending) instead of bouncing through `DIAGNOSED` between dispatches in a pipeline.

### 7.2 Why Mode A is exempt

For a single dispatch ("user wants S3 ablation run") creating a one-item task list adds ceremony without safety benefit. The `tools:` allowlist (Layer 1) already prevents inline experiment execution. Pattern 7 in the hook only fires under `MODE_B_PIPELINE`.

### 7.3 PLAN_PUBLISHED rules

- The number of `TaskCreate` calls must equal the number of planned `Agent()` dispatches for the pipeline (e.g., 7 for a full S1→S7 pipeline).
- Each task `description` MUST include the target sub-agent and the stage label (e.g., `Dispatch copilot-experiment for S3 Run 1 baseline reproduction`).
- The `subject` field of each task should be one of: `Dispatch copilot-literature`, `Dispatch copilot-ideation`, etc.
- The conductor sets `addBlockedBy` so task N is blocked by task N-1; the dispatch order is enforced via the task graph, not via prose.
- After `TaskCreate`s complete, the conductor writes a `decisions.md` `__HANDOFF__` block listing the task IDs and dispatch order, then transitions to `AWAIT_SUBAGENT_END` for the first task.
- In `AWAIT_SUBAGENT_END`, after audit the conductor calls `TaskUpdate` with `status=completed` for the just-finished dispatch, then issues the next `Agent()` call for the next task, or transitions to `END` if no tasks remain.

## 8. Layer 4 — `research_copilot_guard.py` pattern 7

### 8.1 New blocking rule

| Violation | Detection | Block message |
|---|---|---|
| Pattern 7 — Mode B Agent dispatch without TaskCreate plan list | Active agent = `research-copilot`; state from `.copilot/state.md` is `MODE_B_PIPELINE` OR `PLAN_PUBLISHED` OR `AWAIT_SUBAGENT_END` after a prior Mode B entry; current tool is `Agent` with `subagent_type` starting with `copilot-`; **and** the current session transcript contains zero `TaskCreate` tool calls between the most recent transition into `MODE_B_PIPELINE` and now | `Blocked by research-copilot-guard (pattern 7): Mode B pipeline dispatch requires a published TaskCreate plan list (one task per planned dispatch). Call TaskCreate for each stage in order before invoking Agent().` |

### 8.2 Detection details

- The hook re-uses `_iter_transcript_tool_uses` (already in `research_copilot_guard.py`) to scan the JSONL transcript for `TaskCreate` calls in the current turn.
- "Current turn" is defined as: from the most recent transcript line where `Stage: MODE_B_PIPELINE` appears in a state file edit, up to the current `PreToolUse` invocation.
- To detect Mode B state, the hook reads `.copilot/state.md` via the existing `load_state()` helper, and additionally treats `current_state == "MODE_B_PIPELINE" or "PLAN_PUBLISHED"` as the Mode B precondition.
- The hook does NOT block the **first** `Agent` call in Mode A (`current_state == "MODE_A_ROUTING"`).

### 8.3 Pattern 7 algorithm

```python
def check_pattern_7_no_plan_list(
    tool_name: str,
    tool_input: dict[str, Any],
    state: dict[str, Any],
    transcript_path: str | None,
) -> str | None:
    """Pattern 7: in Mode B pipeline, every Agent dispatch must be preceded by
    a TaskCreate plan list in the current Mode B session."""
    if tool_name != "Agent":
        return None
    current_state = state.get("current_state", "UNINITIALIZED")
    if current_state not in {"MODE_B_PIPELINE", "PLAN_PUBLISHED",
                             "AWAIT_SUBAGENT_END"}:
        return None
    sub_type = str(tool_input.get("subagent_type", ""))
    if not sub_type.startswith("copilot-"):
        return None
    # Count TaskCreate calls in this turn
    task_count = 0
    for entry in _iter_transcript_tool_uses(transcript_path):
        if entry["name"] == "TaskCreate":
            task_count += 1
    if task_count == 0:
        return (
            "Blocked by research-copilot-guard (pattern 7): Mode B pipeline "
            "dispatch requires a published TaskCreate plan list (one task "
            "per planned dispatch). Call TaskCreate for each stage in order "
            "before invoking Agent()."
        )
    return None
```

### 8.4 Main loop integration

Edit `main()` in `research_copilot_guard.py` to call pattern 7 inside the existing decision loop:

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

### 8.5 Fail-open posture

If `transcript_path` is missing or unreadable, `_iter_transcript_tool_uses` yields zero entries → pattern 7 returns the deny message. To avoid trapping the user when the transcript is genuinely unavailable, the function short-circuits to `None` (allow) when `transcript_path` is falsy. This matches the existing fail-open posture of patterns 5 and 6.

## 9. Test plan

### 9.1 Unit tests (`self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py`, pytest)

| Test | Setup | Expected |
|---|---|---|
| `test_pattern_7_blocks_agent_without_taskcreate_in_mode_b` | Active agent = `research-copilot`; `.copilot/state.md` Stage = `MODE_B_PIPELINE`; transcript has zero TaskCreate entries; payload is `Agent(subagent_type='copilot-literature')` | `permissionDecision=deny`, message contains "pattern 7" |
| `test_pattern_7_allows_agent_with_taskcreate_in_mode_b` | Same as above but transcript has 7 TaskCreate entries before the Agent call | `permissionDecision=allow` |
| `test_pattern_7_skips_in_mode_a` | Stage = `MODE_A_ROUTING`; transcript has zero TaskCreate; payload is Agent | `permissionDecision=allow` (pattern 7 does not fire in Mode A) |
| `test_pattern_7_skips_in_plan_published_with_taskcreate` | Stage = `PLAN_PUBLISHED`; transcript has TaskCreate entries | `permissionDecision=allow` |
| `test_pattern_7_blocks_in_await_subagent_end_no_tasks` | Stage = `AWAIT_SUBAGENT_END`; transcript has zero TaskCreate (i.e., never went through PLAN_PUBLISHED) | `permissionDecision=deny`, message contains "pattern 7" |
| `test_pattern_7_skips_for_non_copilot_subagent` | Stage = `MODE_B_PIPELINE`; payload is `Agent(subagent_type='general-purpose')` | `permissionDecision=allow` |
| `test_pattern_7_fail_open_no_transcript_path` | Stage = `MODE_B_PIPELINE`; `transcript_path` is empty | `permissionDecision=allow` |
| `test_pattern_7_only_fires_when_research_copilot_is_active` | Active agent = `copilot-literature` (sub-agent); Stage = `MODE_B_PIPELINE`; zero TaskCreate; payload is Agent | `permissionDecision=allow` (pattern 7 scoped to research-copilot) |

### 9.2 Manual integration smoke (run once after merge)

1. `/clear` the session, dispatch `@research-copilot 全流程跑一遍 NeurIPS submission sprint` (Mode B trigger).
2. Confirm `research-copilot` cannot call `Bash` / `PowerShell` / any MCP (tools allowlist takes effect).
3. Confirm `research-copilot` enters `MODE_B_PIPELINE`, then `PLAN_PUBLISHED`, with `TaskList` showing 7 dispatch tasks.
4. Try to bypass by issuing `Agent(subagent_type='copilot-literature')` from a state where transcript has no `TaskCreate` → confirm pattern 7 blocks with the expected message.
5. After the conductor publishes the plan, confirm the first `Agent()` call carries `model='haiku'` parameter (inspect the tool call payload).
6. Confirm sub-agent runs on Haiku (look at sub-agent status / cost meter; alternatively, look at the model line in the sub-agent's first response if displayed).

### 9.3 Regression check on existing tests

The existing `test_research_copilot_guard_pattern5.py` and `test_research_copilot_guard_pattern6.py` should still pass unchanged. The new pattern 7 is appended to the check list; patterns 1, 3, 5, 6 are untouched.

## 10. Edge cases

### 10.1 User invokes Mode A but task is actually multi-stage

If the user types "走完 S2 → S3 → S4" but `state.md` Stage = `MODE_A_ROUTING`, the conductor must transition `DIAGNOSED → MODE_B_PIPELINE` (per the existing state table) before dispatching. Pattern 7 then fires when the conductor is in `MODE_B_PIPELINE` and dispatches without a plan list — correct behavior.

### 10.2 User explicitly requests Mode A with inline planning

Some users may want a single-shot dispatch with no plan list ceremony. The conductor recognizes this from the prompt and stays in `MODE_A_ROUTING`. Pattern 7 does not fire. The tools allowlist (Layer 1) still prevents inline execution.

### 10.3 Recovery after a sub-agent BACK_EDGE_TRIGGERED

Per the state table, `BACK_EDGE_TRIGGERED` can re-enter `MODE_B_PIPELINE` or `MODE_A_ROUTING`. If it re-enters `MODE_B_PIPELINE`, the conductor must call `TaskCreate` again for the new plan (the previous plan is now invalid). Pattern 7's transcript scan counts TaskCreate calls from the current Mode B entry forward, so a stale TaskCreate from the previous Mode B session does NOT satisfy the rule. **Implementation note:** "current Mode B entry" is defined as the most recent line in `.copilot/state.md` containing the literal token `MODE_B_PIPELINE`; the hook should compare its mtime to the latest TaskCreate timestamp in the transcript. If implementation difficulty is high, accept a fail-open here and rely on Layer 3 (the conductor's own state machine discipline).

### 10.4 `tools:` field not honored by Claude Code

If a future Claude Code release ignores or mis-parses the `tools:` field, Layer 1 collapses and we rely on Layer 4 (hook) + Layer 3 (state machine) + prose rules. Mitigation: integration smoke test 2 above explicitly verifies Bash is denied; if not, file a Claude Code issue and fall back to a hook-side deny list (extension of pattern 3 to cover all states, not just S2/S3).

### 10.5 Model parameter not supported by the Agent tool

If a future Claude Code release does not accept `model` as a per-invocation parameter for `Agent()`, Layer 2 collapses. Mitigation: set the env var `CLAUDE_CODE_SUBAGENT_MODEL=<the-right-model>` in a SessionStart hook conditionally. (Out of scope for v1; revisit if integration test 5 fails.)

## 11. Phased rollout

| Phase | Content | Est. | Depends on | Rollback |
|---|---|---|---|---|
| 0 | Commit this spec | 5 min | — | git revert |
| 1 | Edit `PIPELINE-OS.md §4` to 7 fields; edit §6 to reference plan-list rule | 20 min | 0 | git revert one file |
| 2 | Edit `research-copilot.agent.md` frontmatter (tools allowlist) and state table (PLAN_PUBLISHED) | 30 min | 1 | git revert one file |
| 3 | Edit `research_copilot_guard.py` to add pattern 7 + write unit tests | 1 h | 2 | git revert pattern 7 only |
| 4 | Update `research-copilot-guard.hook.md` spec note | 10 min | 3 | trivial |
| 5 | Run pytest (existing patterns 5/6/integration tests must still pass) | 15 min | 3 | — |
| 6 | Integration smoke test (steps in §9.2) | 30 min | 5 | — |
| 7 | If smoke passes, declare done; if smoke fails, see §10.4 / §10.5 fallbacks | — | 6 | per fallback |

Total ≈ 3 h. Phase 2 is the highest-risk edit (touches the conductor's frontmatter and state table); diff-review it carefully.

## 12. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Claude Code version does not respect `tools:` allowlist | low | high | Smoke test 2; if fails, extend hook pattern 3 from `S2_IDEATION/S3_EXPERIMENT` to all states |
| Claude Code version does not accept per-invocation `model` parameter | low | medium | Smoke test 5; if fails, use `CLAUDE_CODE_SUBAGENT_MODEL` env via SessionStart hook |
| Pattern 7 false-positive blocks a legitimate Mode A scenario the conductor mis-tagged as Mode B | medium | low | Pattern 7 scoped to `current_state in {MODE_B_PIPELINE, PLAN_PUBLISHED, AWAIT_SUBAGENT_END}`; if conductor accidentally enters MODE_B without a real multi-stage need, user can override with `.copilot/.guard_override` (existing mechanism per 2026-05-24 spec) |
| `TaskCreate` transcript scan slow on long sessions | low | low | `_iter_transcript_tool_uses` already used by patterns 5/6 with acceptable perf; no change needed |
| User confused by pattern 7 message and does not know why blocked | low | low | Block message names the pattern and prescribes the fix verbatim |
| `MODE_B` re-entry edge case (§10.3) | medium | low | Accept fail-open if implementation is hard; Layer 3 state machine still enforces discipline |

## 13. Out of scope

- Auto-converting TaskCreate to Agent (not supported by Claude Code per docs; `Task` is just a list manager).
- Adding `tools:` allowlists to the 7 `copilot-*` sub-agents (their tool scopes are appropriate to their roles; they need MCP / Bash / Write / etc.).
- Refactoring `user_prompt_dispatch_reminder.py` (its job is the user-prompt-side nudge; nothing changes here).
- Persisting violations of pattern 7 to `.copilot/__violations.log` (the existing `copilot_subagent_stop.py` log channel covers sub-agent-side violations; pattern 7 fires on the conductor and is logged to the hook's stderr / `systemMessage`).

## 14. Acceptance criteria

1. `wc -L self/agents/research-copilot.agent.md` shows the new `tools:` line in the frontmatter (≤200 chars).
2. `grep -c '^| Model:' self/PIPELINE-OS.md` (or equivalent locating the 7th field row) ≥1 hit.
3. `grep -c PLAN_PUBLISHED self/agents/research-copilot.agent.md` ≥3 hits (state table row, Mode A row reference, Mode B row reference).
4. `pytest self/hooks/scripts/__tests__/test_research_copilot_guard_pattern7.py` → all 8 tests pass.
5. `pytest self/hooks/scripts/__tests__/` (full suite) → no regressions on patterns 5/6.
6. Manual smoke test (§9.2) steps 1–5 all pass.
7. The two pain points from §1 are resolved: (A) sub-agents run on their declared model (verified via the per-invocation `model` parameter); (B) the conductor cannot do inline domain work (verified by blocked Bash attempt) and cannot dispatch in Mode B without a plan list (verified by blocked Agent attempt without TaskCreate).

## 15. Open questions

| Q | Resolution plan |
|---|---|
| Does Claude Code 2.x accept `Agent(model=…)` per-invocation override? | Verify in smoke test step 5; if no, fall back to env var per §10.5 |
| Is the `tools:` frontmatter field strictly enforced or merely advisory in current Claude Code? | Verify in smoke test step 2; if advisory, extend hook pattern 3 to cover all states |
| Should pattern 7 also fire when conductor is in `BACK_EDGE_TRIGGERED` re-entering Mode B? | Per §10.3, accept fail-open for v1; revisit if observed in production |

## 16. Handoff to writing-plans

This spec is the input to `superpowers:writing-plans` next, which will produce a step-by-step implementation plan with TaskCreate-ready items per phase 0–7.
