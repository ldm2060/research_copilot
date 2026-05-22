# Self Agent Refactor v2 — Design Spec

**Date**: 2026-05-23
**Author**: brainstorm session (user-driven)
**Status**: design approved, awaits implementation plan
**Predecessors**:
- `2026-05-05-research-copilot-redesign-design.md` (initial conductor design)
- `2026-05-19-agent-optimization-design.md` (state-machine retrofit)
- `2026-05-19-pipeline-ledger-worker-dispatch-design.md` (worker dispatch)
- `2026-05-21-research-copilot-workflow-enforcement-design.md` (workflow hook)

## 1. Problem Statement

Six pain points reported by the user during real research-pipeline use:

| ID | Pain | Root cause (verified via file inspection) |
|---|---|---|
| ① | Agent files too long; "read once, forget" | `research-copilot.agent.md` = 28.7 KB; 7 `copilot-*` agents 6.6–9.4 KB each; `AGENTS.md` 11 KB; state-machine spec / capability-gate spec / delegation template repeated across all 8 agent files |
| ② | Brainstorming skips literature search; falls back to world knowledge | No capability gate enforces a paper-retrieval MCP call before `CANDIDATES_GENERATED`; novelty axis only says "verify via MCP" in prose, never gated |
| ③ | Sub-agent dispatch is not automatic; requires human reminder | Existing `research-copilot-guard` hook fires PostToolUse with specific patterns; no UserPromptSubmit-side reminder; the conductor file may exceed effective attention budget |
| ④ | No memory across sessions; same idea proposed multiple times | `C:\Users\ldm20\.claude\projects\D--article\memory\` is empty; `.copilot/*.md` exist but no SessionStart injector loads them; sub-agents do not consistently emit a parseable handoff block |
| ⑤ | Long experiments do not auto-loop; results not propagated when finished | `/loop 1m` is documented as a user-side practice (`AGENTS.md` L141); no agent-side automation to arm a self-poll for long background experiments |
| ⑥ | "Walks one step, asks one step"; re-confirmation after plan approved | Every state-machine transition uses `AskUserQuestion`; `AGENTS.md` L60: "MUST use AskUserQuestion as approval gate"; no policy distinguishing reversible / irreversible transitions |

The existing architecture (7 sub-agents + 1 conductor + state machines + hook + `.copilot/` persistence) is sound. The fix is concentrated on: file-size reduction via shared spec extraction, two new hooks (memory injection + dispatch reminder), one new hook (loop-armer), four new capability gates (research / longrun / memory / handoff), one new approval-gate policy.

## 2. Decisions (from clarifying interview)

| Question | Choice |
|---|---|
| Scope | All 6 pain points in a single design, phased rollout |
| Sub-agent enforcement mechanism | `UserPromptSubmit` hook auto-injects "dispatch sub-agent first" reminder (strongest) |
| Memory layer | `.copilot/` inside project + `SessionStart` summary injection (do **not** use the per-project auto-memory dir for now) |
| Slim strategy | Extract a shared `PIPELINE-OS.md`; each agent file retains only its unique state table + role + gates |
| Approval-gate policy | Default = do not ask. Ask only at: cross-stage / irreversible / cross-threshold / candidate-selection / 3-strike loop |

## 3. Target File Layout

```
self/
├── PIPELINE-OS.md                              [NEW]   ~300 lines  shared spec: state machine + delegation + gates + back-edges + STATE_OUTPUT
├── HARD-GATES.md                                [NEW]   ~120 lines  7 global hard gates (incl. new research-gate, longrun-gate, memory-gate, handoff-gate)
├── AGENTS.md                                    [EDIT]  11 KB → ~4 KB. Remove repeated state-machine / delegation / gate prose; keep only 8-agent index + usage notes.
├── agents/
│   ├── research-copilot.agent.md                [REWRITE]  28.7 KB → ≤5 KB
│   ├── copilot-literature.agent.md              [REWRITE]   6.6 KB → ≤3 KB
│   ├── copilot-ideation.agent.md                [REWRITE]   8.5 KB → ≤3.5 KB    (research-gate)
│   ├── copilot-experiment.agent.md              [REWRITE]   8.9 KB → ≤3.5 KB    (longrun-gate)
│   ├── copilot-writer.agent.md                  [REWRITE]   9.4 KB → ≤4 KB
│   ├── copilot-polisher.agent.md                [REWRITE]   7.0 KB → ≤3 KB
│   ├── copilot-reviewer.agent.md                [REWRITE]   8.8 KB → ≤3.5 KB
│   ├── copilot-rebuttal.agent.md                [REWRITE]   8.3 KB → ≤3 KB
│   └── backup-2026-05-23/                       [BACKUP]    pre-rewrite snapshot
├── hooks/
│   ├── scripts/
│   │   ├── session_start_memory_injector.py     [NEW]   reads .copilot/{state,ideas,experiments,literature}.md → ≤2 KB summary
│   │   ├── user_prompt_dispatch_reminder.py     [NEW]   injects "dispatch sub-agent first" reminder on exec-class prompts
│   │   ├── post_tool_loop_armer.py              [NEW]   detects long background experiment → recommends CronCreate self-poll
│   │   ├── scientist_guardrails.py              [KEEP]
│   │   └── research_copilot_guard.py            [EDIT]  add Pattern 5 (no-memory-read) + Pattern 6 (no-research-MCP)
│   ├── session-memory-injector.json             [NEW]
│   ├── dispatch-reminder.json                   [NEW]
│   ├── loop-armer.json                          [NEW]
│   └── scientist-guardrails.json                [KEEP]
├── skills/
│   └── research-workflow/SKILL.md               [EDIT]  reference PIPELINE-OS.md; hard-gates 5 → 7
└── install.py                                   [EDIT]  register 3 new hooks
.copilot/
├── state.md                                     [EDIT]   add __HANDOFF__ trailer
├── ideas.md                                     [EDIT]   add __HANDOFF__ trailer
├── experiments.md                               [EDIT]   add __HANDOFF__ trailer
├── literature.md                                [EDIT]   add __HANDOFF__ trailer
├── decisions.md                                 [EDIT]   add __HANDOFF__ trailer
├── pipelines/*.md                               [EDIT]   add __HANDOFF__ trailer
└── (other files unchanged)
docs/superpowers/specs/2026-05-23-self-agent-refactor-design.md   [THIS]
```

Target byte budget for a fresh dispatch (main session → first sub-agent): `PIPELINE-OS.md` (~5 KB) + one agent (~3.5 KB) ≈ **8 KB**, down from 28.7 + 11 ≈ **40 KB** (a 5× reduction). `AGENTS.md` is reference doc, not auto-loaded.

## 4. PIPELINE-OS.md — Shared Spec

Ten sections, ~300 lines total:

1. **State Machine Format** — naming, initial state, history tracking.
2. **STATE_OUTPUT Block** — mandatory tail of every sub-agent reply; 7 fields.
3. **Capability Gates (7)**:
   - `interview-gate` — match `*-interview` skill
   - `validation-gate` — match `*-validator` / `*-checker`
   - `research-gate` **[NEW]** — match `arxiv-search` / `arxivsub-search` / `google-scholar` / `dblp-bib` MCP; ≥2 distinct queries; required before `CANDIDATES_GENERATED`
   - `longrun-gate` **[NEW]** — required when est-time > 10 min before `EXECUTING`; must arm `Bash(run_in_background=true)` OR `Monitor(persistent=true)` OR `ScheduleWakeup(≥600s)` OR `CronCreate`
   - `execution-gate` — long task launch
   - `memory-gate` **[NEW]** — every sub-agent must Read at least one `.copilot/` file in `UNINITIALIZED → CONTEXT_LOADED`
   - `handoff-gate` **[NEW]** — `END` state must write `__HANDOFF__` block to its owned `.copilot/` artifact
4. **Delegation Template (6-field)** — Context / Goal / Facts / Constraints / Output / Stop.
5. **Approval Gate Policy [NEW]** — DEFAULT: do not ask. ASK iff: cross-stage / back-edge / irreversible / resource >2× / candidate selection / 3-strike loop.
6. **Sub-agent Dispatch Policy [NEW]** — main thread = decisions + routing + summary; sub-agent = all execution > 5 tool calls; every `Task()` carries 6-field template.
7. **Back-edge Matrix** — trigger / source / target / counter / 3-strike action.
8. **`.copilot/` Write Permission Partition** — single-writer per file; `handoff.md` is the only append-only multi-writer.
9. **Memory Hand-off Schema [NEW]** — every `.copilot/<artifact>.md` ends with:

   ```
   ## __HANDOFF__
   - last_updated: <ISO 8601>
   - written_by: <agent name>
   - key_facts: <bullets>
   - next_owner: <agent name>
   ```

   `session_start_memory_injector.py` reads only this block; sub-agents in `END` state write only this block.
10. **Error Recovery** — `malformed-output` / `invalid-transition` / `capability-gate-failed` / `no-handoff-block`.

`HARD-GATES.md` is a companion 120-line file mirroring the 7 gates in agent-prose form (used by `research-workflow/SKILL.md`).

## 5. Per-agent Slim Blueprint

Common structure (≤120 lines each):

```
---
name / description / argument-hint / model / color
---
# <Agent Name> — <One-line role>

## My Unique State Table
## My Unique Output / Artifact (.copilot/* + __HANDOFF__ fields)
## My Unique Gates (reference PIPELINE-OS.md §3)
## My Unique Hard Rules
## When to back-edge to whom
```

Per-agent unique surface:

| Agent | Old | New | Unique content |
|---|---|---|---|
| research-copilot | 28.7 KB | ≤5 KB | Mode A routing table, Mode B pipeline templates, back-edge inbound matrix, `state.md` + `decisions.md` writer, no execution |
| copilot-literature | 6.6 KB | ≤3 KB | States: SCANNING / BASELINE_LOCKED / RELATED_WORK_AUGMENTED. research-gate ×; `literature.md __HANDOFF__` = locked baseline + 5 key prior works |
| copilot-ideation | 8.5 KB | ≤3.5 KB | research-gate ✓; memory-gate ✓ (reads existing `ideas.md` to avoid repeats); novelty axis must cite ≥1 MCP hit |
| copilot-experiment | 8.9 KB | ≤3.5 KB | longrun-gate ✓; memory-gate ✓ (reads `experiments.md` history); Goal anchor immutable; no `.tex` write |
| copilot-writer | 9.4 KB | ≤4 KB | DRAFT / REWRITE / EXPAND / SHORTEN / TRANSLATE; `.tex` writer; cites `experiments.md __HANDOFF__` for numbers |
| copilot-polisher | 7.0 KB | ≤3 KB | POLISH / DE_AI; no technical change; chains `paper-deai` → `de-ai-checker` validation-gate |
| copilot-reviewer | 8.8 KB | ≤3.5 KB | SIMULATE_REVIEW / EXTRACT_GAPS; writes `reviews/round-N.md`; `__HANDOFF__` lists gaps → back-edge target |
| copilot-rebuttal | 8.3 KB | ≤3 KB | PARSE_REVIEWS / DRAFT_RESPONSE / RE_REVIEW; input = reviewer `__HANDOFF__`; output per reviewer-id |

Deleted from every agent (now in `PIPELINE-OS.md`): state-machine format, STATE_OUTPUT block format, generic anti-pattern tables, generic hard constraints 1–6, delegation template, back-edge overview, MCP priority general rule, `.copilot/` permission table, socket-timeout note, `/loop` user practice note.

## 6. SessionStart Memory Injector

File: `self/hooks/scripts/session_start_memory_injector.py` (≤180 lines).

Reads `.copilot/{state,ideas,experiments,literature,decisions}.md` plus the 3 most recent `pipelines/*.md`; extracts each file's `__HANDOFF__` block (or last 20 lines if absent); concatenates to ≤400 lines; prints to stdout (Claude Code captures stdout as additional context).

Hook registration `self/hooks/session-memory-injector.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "*", "hooks": [
        { "type": "command",
          "command": "python ${CLAUDE_PROJECT_DIR}/self/hooks/scripts/session_start_memory_injector.py" }
      ]}
    ]
  }
}
```

Coexists with existing `scientist-guardrails` SessionStart hook (both append to context).

Idempotent: reads only, never writes. If `.copilot/` is empty, prints one-line notice and exits 0.

Fallback: if `python` is unavailable, the hook handler in `install.py` falls back to a shell echo (matches existing `research-copilot-guard` pattern).

## 7. UserPromptSubmit Dispatch Reminder

File: `self/hooks/scripts/user_prompt_dispatch_reminder.py` (≤90 lines).

Allowlist (skip reminder):
- Slash command (`/...`)
- @-mention agent (`@copilot-...`)
- Status / next-step queries ("what's next", "下一步", "状态", "ls ", "cat ")

Exec-keyword detection (issue reminder): paper-retrieval, brainstorm, experiment, train, ablation, write, draft, polish, expand, shorten, translate, caption, review, sanity, rebuttal, read PDF, etc.

Output (when detected): list of 8 sub-agent options with one-line trigger condition for each.

Hook registration `self/hooks/dispatch-reminder.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "matcher": "*", "hooks": [
        { "type": "command",
          "command": "python ${CLAUDE_PROJECT_DIR}/self/hooks/scripts/user_prompt_dispatch_reminder.py" }
      ]}
    ]
  }
}
```

Disable mechanism: presence of `.copilot/dispatch-reminder.disabled` → hook prints nothing and exits 0.

## 8. MCP research-gate (Fix Pain ②)

Two layers:

**Layer 1 — agent-internal state-machine gate** (`copilot-ideation.agent.md`):

```
PREFERENCES_LOCKED → CANDIDATES_GENERATED:
  GATE: research-gate
  REQUIRED: tool history contains ≥1 of:
    mcp__arxiv-search__search_arxiv
    mcp__arxivsub-search__search_papers
    mcp__google-scholar__search_google_scholar
    mcp__dblp-bib__search_dblp_bibtex
  WITH: ≥2 distinct queries related to current preferences
  ON FAIL: [STATE_ERROR: research-gate-failed]
           list available MCPs; remain in PREFERENCES_LOCKED
```

Every candidate's novelty axis must cite ≥1 MCP hit (arxiv id / dblp key / scholar URL).

**Layer 2 — `research_copilot_guard.py` Pattern 6** (PostToolUse):

Detects: `Write` to `.copilot/ideas.md` with `## Idea` heading + zero paper-retrieval MCP calls in current session → emits violation, blocks the write.

**Fallback**: if MCP unavailable, accept `WebFetch` to arxiv.org / scholar.google.com with non-empty result; sub-agent must mark `Capability gate: passed-degraded`.

**Coverage threshold**: ≥2 distinct queries (not the same query repeated). Stretch goal: ≥1 query per active dimension of the 6-dimension enumeration.

**Side effect**: every research-gate MCP hit must be appended to `.copilot/literature.md` under a "novelty-evidence" subsection so the next session's memory injector surfaces it.

## 9. /loop & Long-task Auto-arming (Fix Pain ⑤)

**Trigger**: copilot-experiment `APPROVED → EXECUTING` with est-time > 10 min OR `Bash(run_in_background=true)` matching `train|main\.py|ai_scientist|torchrun|deepspeed`.

**Layer 1 — longrun-gate (agent-internal)**: must call one of `Bash(run_in_background=true)`, `Monitor(persistent=true)`, `ScheduleWakeup(≥600s)`, `CronCreate` before transition.

**Layer 2 — `post_tool_loop_armer.py` (PostToolUse hook)**: detects matching `Bash` background launch, prints recommended `/loop 1m ...` text + suggests agent self-arming via `CronCreate("<<autonomous-loop>>", recurring=true, durable=false, cron="*/3 * * * *")`. Sets `.copilot/.loop-armed` to prevent re-arming.

**Auto unarm**: copilot-experiment `EXECUTING → COMPLETED` calls `CronDelete(loop_id)` + removes `.copilot/.loop-armed`. The `loop_id` is stored in `experiments.md __HANDOFF__`.

**Pivot from existing AGENTS.md L146** ("agent does not start its own cron"): this rule is **replaced** for the longrun case — an agent **may** auto-arm cron during EXECUTING, but **must** report it in STATE_OUTPUT (so the user sees the cron id) and **must** unarm on EXECUTING exit.

## 10. Approval Gate Policy (Fix Pain ⑥)

Written into `PIPELINE-OS.md` §5.

**DEFAULT**: do not ask. Report after, not before.

**ASK iff one of**:
1. Cross-stage transition (S_n → S_(n±1)), first time within a pipeline.
2. Back-edge (S_n → S_m, m<n).
3. Irreversible operation: overwrite/delete `.tex`, `.bib`, checkpoint, branch, existing `experiments.md` Run blocks.
4. Resource estimate jumps > 2× (time / GPU / cost).
5. Candidate selection: "which idea / which baseline / which ablation".
6. Loop counter hits 3-strike.

**NEVER ASK** (explicitly listed to push back against model self-doubt):
- DESIGN_READY → APPROVED → EXECUTING intra-Run resource confirmations (unless ④ trips).
- COMPLETED → VERIFIED → JUDGED intra-Run steps.
- ANALOGIES_ADDED → FILTERED → AWAITING_SELECTION intra-stage steps.
- Multiple sub-agent dispatches within the same already-approved plan.
- Sub-agent internal state transitions.
- Tool-level operations (Read, Grep, Bash for short commands).
- Re-confirming a pipeline template already approved this session.

**Main thread vs sub-agent**:
- Main thread speaks only on ① ② ⑤ ⑥; otherwise one-line progress notes.
- Sub-agent reports only at `END` state (or `STATE_ERROR`, or ④ trip).

**Interaction with `research-workflow` skill**: keep all 5 existing `HARD-GATE`s except remove "AskUserQuestion before any back-edge or major transition" (replaced by the 6-case list above).

## 11. Phased Rollout

| Phase | Content | Est. | Depends on | Risk | Rollback |
|---|---|---|---|---|---|
| 0 | Backup to `self/agents/backup-2026-05-23/`; commit this spec & plan | 5 min | — | — | git revert |
| 1 | Create `self/PIPELINE-OS.md` + `self/HARD-GATES.md`; existing agents untouched | 1 h | 0 | low | delete both files |
| 2 | Add `__HANDOFF__` trailer block to existing `.copilot/state.md`, `ideas.md`, `experiments.md`, `literature.md`, `decisions.md`; validate parseability | 30 min | 1 | low | strip trailer block |
| 3 | Create `session_start_memory_injector.py` + hook json; local validate injection ≤2 KB | 1 h | 2 | low | delete hook json |
| 4 | Create `user_prompt_dispatch_reminder.py` + hook json; validate against 10 prompt fixtures | 1 h | 1 | medium (noisy?) | delete hook json or `.disabled` file |
| 5 | Rewrite 8 agents (research-copilot first, then 7 copilot-*) | 4 h | 1, 2 | medium (biggest change) | restore from `backup-2026-05-23/` |
| 6 | Extend `research_copilot_guard.py` with Pattern 5 (no-memory-read) + Pattern 6 (no-research-MCP) | 1 h | 5 | low | comment out new pattern functions |
| 7 | Create `post_tool_loop_armer.py` + hook json; test cycle on a real long experiment (CronCreate paired with CronDelete) | 1.5 h | 5, 6 | medium | delete hook json |
| 8 | Update `AGENTS.md` index, `SKILLS.md`, `research-workflow/SKILL.md`; register 3 new hooks in `install.py` | 1 h | 3, 4, 7 | low | git revert 3 files |
| 9 | End-to-end smoke: mini pipeline (S2 ideation → S3 experiment dry-run); verify all 6 pains resolved | 2 h | 8 | — | — |

Total ≈ 12 h. Phase 5 is the heaviest; can be split into 8 commits (1 per agent).

## 12. Test Plan

| Pain | Acceptance evidence |
|---|---|
| ① Files too long | `wc -c self/PIPELINE-OS.md` ≤ 8 KB; each agent file ≤ 4 KB; research-copilot ≤ 5 KB; `AGENTS.md` ≤ 5 KB |
| ② No MCP research in brainstorm | In a fresh session, prompt copilot-ideation; verify it calls `mcp__arxiv-search` or peer ≥2 times before writing `## Idea` to `ideas.md`; verify each idea's novelty axis includes an MCP hit citation |
| ③ Missing sub-agent dispatch | Submit 10 exec-class prompts to main thread; verify `user_prompt_dispatch_reminder.py` injects the reminder in ≥8 of them (the 2 exempt ones are slash command / @-mention); verify main thread responds with `Agent()` call rather than executing inline |
| ④ No memory | Start a fresh session in an existing project; verify `session_start_memory_injector.py` injects `__HANDOFF__` summaries; prompt brainstorming and verify copilot-ideation does not re-propose an idea already in `ideas.md` |
| ⑤ No loop / no result update | Start a long background experiment; verify `post_tool_loop_armer.py` prints suggestion; verify agent auto-arms `CronCreate`; on COMPLETED verify `CronDelete` fires and `.loop-armed` is removed |
| ⑥ Walks one step asks one step | Execute a 5-state pipeline; verify `AskUserQuestion` fires ≤ 2 times (one cross-stage, one candidate selection) — not at every state transition |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agent rewrite drops a critical hard rule | medium | high | `backup-2026-05-23/`; diff-review each rewrite against backup; smoke tests |
| `dispatch-reminder` too noisy | medium | low | `.disabled` flag file; allowlist tuning |
| `memory-injector` exceeds 2 KB and chokes context | low | medium | hard cap in code; truncate per-file budget |
| Agent auto-`CronCreate` produces orphan cron tasks | medium | medium | CronDelete on EXECUTING exit; `loop-armed` flag; CronList visible in `/tasks` for manual cleanup |
| `__HANDOFF__` schema changes break old `.copilot/` files | low | medium | parser tolerates missing block (falls back to last 20 lines) |
| `research-gate` blocks legitimate brainstorming when MCPs are down | low | low | WebFetch fallback path; `passed-degraded` capability state |
| Hooks fire without Python available | low | low | install.py shell fallback (matches existing pattern) |

## 14. Out of Scope

- Cross-project / cross-machine memory (the user has opted out of auto-memory dir for now).
- Rewriting any skill (only `research-workflow/SKILL.md` is touched).
- Touching `self/runtimes/scientist-support/` or any MCP server.
- Frontend / UI work; this is a CLI-only refactor.
- Migrating away from `.copilot/` to another persistence layout.

## 15. Open Questions Resolved During Brainstorm

| Q | A |
|---|---|
| Scope | All 6 pains in one spec |
| Sub-agent enforcement | UserPromptSubmit hook |
| Memory location | `.copilot/` only |
| Slim strategy | Extract PIPELINE-OS.md |
| Approval gate | 6 explicit cases |
| MCP research minimum | ≥2 distinct queries; degraded WebFetch allowed |
| `.loop-armed` collision | TBD during P7 (single-project assumption acceptable for v2; revisit if user runs parallel terminals on same repo) |
| 4 new gates | research / longrun / memory / handoff — all included |
| `__HANDOFF__` contract | yaml-style bullets, parsed by injector |

## 16. Handoff to writing-plans

This spec is the input to `superpowers:writing-plans` next, which will produce a step-by-step implementation plan with TaskCreate-ready items per phase.
