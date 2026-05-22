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
