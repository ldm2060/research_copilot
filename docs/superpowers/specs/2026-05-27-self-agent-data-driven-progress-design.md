# Self/Agent Data-Driven Progress & Git-Tracked Experiments Design

- Date: 2026-05-27
- Scope: `self/agents/copilot-experiment.agent.md`, `self/agents/copilot-ideation.agent.md`, `self/PIPELINE-OS.md` (§3 capability gates), 2 new SubagentStop hook scripts, hook tests, install.py registration
- Status: Approved (post-brainstorming), ready for implementation plan
- Predecessor: `2026-05-24-copilot-subagent-guard-design.md` (extends the same hook architecture and `_copilot_hook_lib.py` substrate from Rules 1–4 to two new business rules)

## Background

Today's experiment / ideation enforcement landscape (verified by reading `self/PIPELINE-OS.md`, `self/agents/copilot-experiment.agent.md`, `self/agents/copilot-ideation.agent.md`, `.copilot/experiments.md`, `self/AGENTS.md`, all 6 existing hook scripts):

| Existing rule | Source | Enforced? |
|---|---|---|
| Goal anchor is immutable | PIPELINE-OS §5 case ③ | ✅ Approval-gate |
| `memory-gate`: must Read `.copilot/*.md` before transitioning | PIPELINE-OS §3 | ✅ Hard (copilot_write_guard.py) |
| `handoff-gate`: END state must update `## __HANDOFF__` | PIPELINE-OS §3, §9 | ✅ Hard (copilot_subagent_stop.py) |
| Sub-agent writes only its owned `.copilot/*.md` | PIPELINE-OS §8 | ✅ Hard (copilot_write_guard.py) |
| **Rule A — Progress test results are committed to git with detailed notes** | (none) | ❌ Not even specified |
| **Rule B — Experiment analysis & subsequent ideation must cite real metrics, not examples / guesses** | (none) | ❌ Not even specified |

Empirical observations that motivate this design:

- `.copilot/experiments.md` is gitignored at the workspace level today; no Run history is preserved across resets.
- The current `copilot-ideation` state machine has only a `memory-gate` requiring "read" — nothing requires the agent to cite specific metrics in its candidate ideas.
- `copilot-experiment.agent.md` JUDGED state already produces a goal-status label (`goal-met / on-trajectory / off-trajectory / falsified`) but never persists it to git history.
- The hook infrastructure (`_copilot_hook_lib.py`: detect_active_agent / scope_predicate / .guard_override reader / STATE_OUTPUT parser / violations.json IO / safe_main wrapper) is sufficient to absorb two more SubagentStop guards without core changes.

## Goal & Non-goals

**Goal.** Promote Rules A & B from "not specified" to "hook-enforced", with the same SOFT WARN ↔ HARD BLOCK precision-vs-noise discipline used in the predecessor spec.

**Non-goals (this spec).**

- No changes to `research-copilot.agent.md` routing logic. Rules A & B are sub-agent–local; the conductor sees them only through STATE_OUTPUT + `__HANDOFF__`.
- No structured per-Run snapshot directory (`experiments/run-N/{metrics.json, log.txt}`). YAGNI until cross-Run analysis is actually needed.
- No `.gitignore` edits. Per user directive, the workspace `.copilot/` gitignore is irrelevant to packaged outputs.
- No new PIPELINE-OS approval-gate case. The new "progress rule" interview question reuses §5 case ⑤ (candidate selection).
- No new hooks beyond SubagentStop. PreToolUse / PostToolUse stay untouched.

## Design Decision

**Approach B — Prompt-level constraint backed by SubagentStop hook audit.** (Selected from the brainstorming pass; A was prompt-only with no audit, C added two new skills.)

Rationale: The existing hook lib already covers ~80% of what is needed (active-agent detection, override bypass, STATE_OUTPUT parsing, violation logging). Adding two single-purpose audit scripts is mechanically smaller than introducing skills, and pattern-aligned with the predecessor design (`copilot_subagent_stop.py`'s SOFT/HARD layering).

| Rule | Hook | Severity | Rationale |
|---|---|---|---|
| A.1 progress-flag matches commit existence | `copilot_experiment_commit_guard.py` SubagentStop | **HARD BLOCK** | Pure git-log match on `exp(Run N):` subject; false-positive ≈ 0 |
| A.2 commit message contains required fields | same | **SOFT WARN** | Linguistic check; collect data first |
| A.3 Progress Rule yaml malformed | same | **HARD BLOCK** | Pure yaml parse; can't proceed otherwise |
| B.1 every candidate idea cites `experiments.md:Run N` | `copilot_ideation_evidence_guard.py` SubagentStop | **HARD BLOCK** (non-first-boot) | Regex match on output; structural |
| B.2 first-boot candidates lack any evidence line | same | **SOFT WARN** | Allows first-run literature-only path |

## Architecture

### Component layout

```
self/
├── PIPELINE-OS.md                           (MODIFIED — §3 table gains `evidence-gate` row)
├── agents/
│   ├── copilot-experiment.agent.md          (MODIFIED — DESIGN_READY + JUDGED gain progress-rule logic)
│   └── copilot-ideation.agent.md            (MODIFIED — new DATA_REVIEW state + Hard Constraints)
├── hooks/
│   ├── scripts/
│   │   ├── _copilot_hook_lib.py             (UNCHANGED — reused)
│   │   ├── copilot_experiment_commit_guard.py   (NEW — Rule A)
│   │   └── copilot_ideation_evidence_guard.py   (NEW — Rule B)
│   └── tests/
│       ├── test_copilot_experiment_commit_guard.py   (NEW — 6 cases)
│       ├── test_copilot_ideation_evidence_guard.py   (NEW — 6 cases)
│       └── fixtures/
│           ├── transcript_copilot_experiment_progress_run.jsonl   (NEW)
│           └── transcript_copilot_ideation_with_evidence.jsonl    (NEW)
└── install.py                               (MODIFIED — append 2 SubagentStop registrations)
```

### Data flow

```
                            ┌────────────────────────────────────────┐
                            │ research-copilot (unchanged routing)   │
                            └──────────────┬─────────────────────────┘
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            ▼                                                             ▼
  ┌──────────────────────────────┐                          ┌──────────────────────────────────┐
  │ copilot-experiment           │                          │ copilot-ideation                 │
  │                              │                          │                                  │
  │ DESIGN_READY adds:           │                          │ +DATA_REVIEW state               │
  │  · interview "progress rule" │                          │  · MUST Read experiments.md      │
  │  · write Goal-anchor.rule    │                          │  · MUST extract ≥1 Run metric    │
  │                              │                          │  · evidence-gate passes          │
  │ JUDGED adds:                 │                          │                                  │
  │  · apply rule → progress?    │                          │ Subsequent ideation states:      │
  │  · if true: git add/commit   │                          │  · every candidate.idea          │
  │  · update __HANDOFF__ flag   │                          │    references experiments.md:RunN│
  └──────────────────────────────┘                          └──────────────────────────────────┘
            │                                                             │
            │  on SubagentStop                                             │  on SubagentStop
            ▼                                                             ▼
  ┌──────────────────────────────┐                          ┌──────────────────────────────────┐
  │ copilot_experiment_commit_   │                          │ copilot_ideation_evidence_guard  │
  │ guard.py  (NEW)              │                          │ .py  (NEW)                       │
  └──────────────────────────────┘                          └──────────────────────────────────┘
            │                                                             │
            └──────────────── share ─────────►  _copilot_hook_lib.py
```

Walk-through:

1. **Goal anchor** — copilot-experiment in DESIGN_READY calls `deep-interview` to capture a structured `Progress Rule` (yaml block, see §"Data shape" below); writes it into `.copilot/experiments.md`.
2. **Every Run JUDGED** — agent applies the rule mechanically to current Run metrics; writes `progress: true|false` + reasoning + (if true) `commit_sha` into the Run N block.
3. **If progress=true** — agent runs `git diff --name-only $subagent_start_sha HEAD -- ':!.copilot/state.md' ':!.copilot/decisions.md' ':!.copilot/handoff.md'` to find the Run's code changes, `git add` those + `.copilot/experiments.md`, then `git commit -m "exp(Run N): ..."` with the structured message template.
4. **SubagentStop on copilot-experiment** — `copilot_experiment_commit_guard.py` verifies: for every `progress: true` Run, a matching `exp(Run N):` commit exists in `git log`. If not, HARD BLOCK with a remedy hint.
5. **copilot-ideation invocation** — agent enters new `DATA_REVIEW` state after `CONTEXT_LOADED`; must Read `.copilot/experiments.md`, parse Run blocks, emit a Data Evidence Table. `evidence-gate` (new) passes / passed-degraded (first-boot) / FAILED.
6. **Every candidate idea** — must carry an `evidence:` line referencing `experiments.md:Run N — <metric>=<value>` (or `literature.md:<key>` only when no Run exists, or `none (first-boot)` only in the first-boot case).
7. **SubagentStop on copilot-ideation** — `copilot_ideation_evidence_guard.py` scans the output, requires ≥1 `experiments.md:Run \d+` citation per candidate (non-first-boot path); SOFT WARN if first-boot candidates lack a literature/none evidence line; HARD BLOCK otherwise.

## Data shape

### Progress Rule yaml (written once into `.copilot/experiments.md`)

```yaml
primary_metric: val_acc          # required; matched against same-named field in each Run N block
direction: max                   # max | min
min_delta: 0.005                 # required; minimum effective improvement
mode: best_so_far                # best_so_far | vs_baseline | vs_prev
secondary_must_not_regress:      # optional list
  - {name: val_loss, direction: min, max_regress: 0.02}
```

Rules:

- yaml block is fenced with `` ```yaml `` for machine parsing.
- The agent's `deep-interview` skill is asked exactly once, in DESIGN_READY, before the first Run. The block is immutable thereafter (PIPELINE-OS §5 case ③, same invariant as Goal anchor).
- If the block is malformed, the commit guard HARD BLOCKs with `progress-rule-malformed`. Agent must fix the yaml before exiting.

### Run N block format (excerpt, only new fields)

```markdown
### Run 3 (2026-05-27)
- 配置: ...
- 命令: ...
- 主指标: val_acc 0.841 (vs Run 2 best 0.823)
- 消融: ...
- 解读: ...
- **progress**: true
- **progress_reason**: val_acc 0.841 > best_so_far 0.823 + min_delta 0.005
- **commit_sha**: a1b2c3d
```

The `progress` field is what the commit guard reads. `commit_sha` lets the guard cross-check the actual commit hash.

### Commit message template

```
exp(Run N): <one-line improvement summary>

primary_metric: val_acc 0.823 → 0.841 (+0.018)
secondary:
  - val_loss 0.412 → 0.405 (-0.007)
goal_status: on-trajectory
progress_rule: matched (min_delta=0.005)
```

Required structured fields (commit guard SOFT WARNs if missing): `primary_metric:`, `goal_status:`, `progress_rule:`.

### Data Evidence Table (DATA_REVIEW output)

```markdown
| Run | metric | value | progress | interpretation |
|-----|--------|-------|----------|----------------|
| 1   | val_acc | 0.78 | false    | baseline established but below target |
| 2   | val_acc | 0.82 | true     | LR warmup helps; on-trajectory |
| 3   | val_acc | 0.84 | true     | + AugMix push gain; still on-trajectory |
```

### Candidate idea evidence line

Allowed forms (one of):

- `evidence: experiments.md:Run 3 — val_acc=0.84 (on-trajectory)` — preferred
- `evidence: literature.md:smith2025efficient — claims +3% on similar setup` — fallback when no relevant Run exists
- `evidence: none (first-boot)` — only when `.copilot/experiments.md` contains zero `### Run N` headings

## Agent state-machine changes

### copilot-experiment

Modified rows in the state table:

| State | New action | New gate | New output |
|---|---|---|---|
| DESIGN_READY | If `Progress Rule` yaml block missing in experiments.md, invoke `deep-interview` to capture it; else skip | `interview-gate` (conditional) | Progress Rule yaml block appended |
| JUDGED | (1) Parse Progress Rule + Run N metrics → compute `progress=bool` and `progress_reason`. (2) If true: `git diff --name-only $subagent_start_sha HEAD -- :!<routing files>`, `git add` results + experiments.md, `git commit -m "exp(Run N): ..."`. (3) Write `progress`, `progress_reason`, `commit_sha` into Run N block and into `__HANDOFF__.key_facts` | none | Run N block contains `progress:` + (if true) `commit_sha:` |

EXECUTING state additionally records `subagent_start_sha = git rev-parse HEAD` at entry (used by JUDGED for the diff scope).

No other state row changes. END row already has `handoff-gate`; `key_facts` now includes the `commit_sha` bullet.

### copilot-ideation

New row inserted between `CONTEXT_LOADED` and the existing first creative state:

| State | Action | Gate | Output | Next allowed |
|---|---|---|---|---|
| CONTEXT_LOADED | (existing) Read ideas.md / experiments.md / literature.md | `memory-gate` | Context summary | [DATA_REVIEW] |
| **DATA_REVIEW (new)** | Parse all `### Run N` blocks in experiments.md; extract `progress` + `primary_metric` + secondaries; emit a Data Evidence Table (≥1 row, OR explicitly mark `passed-degraded` when no Run blocks exist) | **`evidence-gate` (new)** | Data Evidence Table markdown | [<existing-first-creative-state>] |
| <existing creative states> | (existing) +each candidate idea carries an `evidence:` line per the rules above | (existing) | (existing) + `evidence:` line on each candidate | (existing) |

The exact name of the existing first creative state will be read from `copilot-ideation.agent.md` at implementation time; this spec does not pin it because the file may be revised independently.

A new "Hard Constraints" line is added:

> Every candidate idea emitted after DATA_REVIEW MUST carry an `evidence:` line. Allowed forms:
> - `evidence: experiments.md:Run N — <metric>=<value>`
> - `evidence: literature.md:<paper-key> — <fact>` (only when no relevant Run exists)
> - `evidence: none (first-boot)` (only when experiments.md has zero Run blocks)

## PIPELINE-OS §3 changes

Add one row to the capability-gate table:

```
| `evidence-gate` | `Read` of `.copilot/experiments.md` AND output contains a parsed Run-metric table | CONTEXT_LOADED → DATA_REVIEW (copilot-ideation only) | `[STATE_ERROR: evidence-gate-failed]`. Degraded: if no Run blocks exist yet, mark `Capability gate: passed-degraded` and proceed |
```

This brings the gate count from 7 to 8. No other §3 changes.

## Hook scripts

Both scripts use `_copilot_hook_lib.py` for `detect_active_agent` / `guard_override_active` / `parse_state_output` / `record_violation` / `safe_main`. They live in `self/hooks/scripts/` and are registered as SubagentStop hooks, executed AFTER `copilot_subagent_stop.py` so that STATE_OUTPUT / HANDOFF audit runs first.

### `copilot_experiment_commit_guard.py`

Checks (in order):

1. **Scope** — return ok if active agent ≠ `copilot-experiment` or `.copilot/.guard_override` is active.
2. **experiments.md exists** — return BLOCK `experiments-md-missing` if not.
3. **Progress Rule yaml parses** — locate the yaml block, parse with `yaml.safe_load`. On exception: BLOCK `progress-rule-malformed`.
4. **Run block extraction** — find all `### Run \d+` headers, parse each into `{n, progress, primary_metric_value, commit_sha}`.
5. **Commit existence per progress=true Run** — `git log --format=%s -n 100` and require ≥1 subject starting `exp(Run N):` for every Run with `progress: true`. Missing ones → BLOCK `experiment-commit-missing` with the list of missing Run numbers and a two-line remedy hint.
6. **Commit message field completeness** — for each present commit, `git show -s --format=%B <sha>` must contain `primary_metric:`, `goal_status:`, `progress_rule:`. Missing fields → SOFT WARN `commit-message-thin` and record to violations.json; do not block.

### `copilot_ideation_evidence_guard.py`

Checks (in order):

1. **Scope** — return ok if active agent ≠ `copilot-ideation` or override active.
2. **Candidate section extraction** — parse the agent's final output for a "候选 ideas" / "Candidates" section. If absent (e.g., agent stopped at DATA_REVIEW), return ok.
3. **First-boot detection** — read `.copilot/experiments.md`; treat "no `### Run \d+` headings" as first-boot.
4. **First-boot path** — each candidate must carry `evidence: literature.md:...` or `evidence: none (first-boot)`. Missing → SOFT WARN `ideation-first-boot-no-evidence`.
5. **Non-first-boot path** — each candidate must contain a regex match `experiments\.md:Run\s+\d+`. Missing → HARD BLOCK `ideation-evidence-missing` with the offending candidate titles and a remedy hint.

### Registration

Both append to `.claude/settings.json` SubagentStop array via `self/install.py`, in this order:

```
SubagentStop:
  1. copilot_subagent_stop.py            (existing; STATE_OUTPUT + HANDOFF audit)
  2. copilot_experiment_commit_guard.py  (new; Rule A)
  3. copilot_ideation_evidence_guard.py  (new; Rule B)
```

## Tests

Two new test files under `self/hooks/tests/`, ≥6 cases each, fixtures under `self/hooks/tests/fixtures/`:

```
test_copilot_experiment_commit_guard.py
  ✓ no_progress_run_passes
  ✓ progress_true_with_matching_commit_passes
  ✓ progress_true_without_commit_blocks
  ✓ multiple_progress_runs_some_missing_blocks_specific_ones
  ✓ guard_override_bypasses
  ✓ commit_message_missing_structured_fields_soft_warns

test_copilot_ideation_evidence_guard.py
  ✓ first_boot_no_run_blocks_passes_with_literature_evidence
  ✓ first_boot_no_run_blocks_no_evidence_soft_warns
  ✓ post_first_run_all_candidates_cite_run_passes
  ✓ post_first_run_one_candidate_missing_citation_blocks
  ✓ guard_override_bypasses
  ✓ malformed_output_no_candidates_section_passes
```

Fixtures:

- `transcript_copilot_experiment_progress_run.jsonl` — copilot-experiment session reaching JUDGED with two Run blocks (Run 1 progress=false, Run 2 progress=true with commit_sha).
- `transcript_copilot_ideation_with_evidence.jsonl` — copilot-ideation session emitting three candidate ideas, two with proper evidence, one missing.

Test git history is constructed via `tmp_path` + `git init` in conftest fixtures (matching the existing pattern used in `test_copilot_subagent_stop.py`).

## Failure modes & recovery

| Situation | Hook behavior | Agent recovery |
|---|---|---|
| Agent mislabels `progress: true` but skipped the commit | HARD BLOCK `experiment-commit-missing` | Either run `git commit -m "exp(Run N): ..."` now, OR flip `progress` to false with a justification line |
| Agent commits but message missing structured fields | SOFT WARN `commit-message-thin` | Continue; warning logged to `.copilot/violations.json`; surfaced by next SessionStart memory injector |
| Progress Rule yaml malformed | HARD BLOCK `progress-rule-malformed` | Agent fixes yaml before exiting |
| Ideation produces no candidate section | Pass (nothing to check) | — |
| User manual bypass: `touch .copilot/.guard_override` | Both guards bypass; bypass logged | Same convention as existing guards |
| `.copilot/experiments.md` missing or unreadable | BLOCK `experiments-md-missing` | Agent reconstructs the file |
| Git repo has unrelated uncommitted changes | Commit guard only `git add`s the explicit file list; unrelated changes untouched | Agent handles conflicts on its own; if `git add` fails on the targeted files, agent surfaces and asks |

## Verification criteria

The implementation is complete when:

1. From a fresh workspace with no Run history, invoking copilot-ideation produces `Capability gate: passed-degraded` and literature-only or `none (first-boot)` evidence lines on each candidate without being blocked.
2. Invoking copilot-experiment for Run 1: DESIGN_READY runs deep-interview to capture Progress Rule yaml; JUDGED computes progress; if progress=true, `git log` shows an `exp(Run 1): ...` commit with the structured message template.
3. After step 2, invoking copilot-ideation again: DATA_REVIEW emits a Data Evidence Table containing Run 1; every candidate carries `evidence: experiments.md:Run 1 — ...`; guard passes.
4. Negative test — stub git to fail at commit time in copilot-experiment: SubagentStop guard HARD BLOCKs, violation recorded in `.copilot/violations.json`.
5. `pytest self/hooks/tests/` is green, including the 12 new cases.
6. SessionStart memory injector surfaces any new violations from the last 24 h in its summary block, including those from the two new guards.

## Out of scope (deferred)

- Structured per-Run snapshot directory (`experiments/run-N/{metrics.json, log.txt}`).
- Cross-Run analysis dashboard / leaderboard skill.
- Migrating older `.copilot/experiments.md` content (none exists today beyond the placeholder).
- Extending Rules A & B to other copilot-* agents (writer / polisher / reviewer / rebuttal). Those agents do not produce metric-bearing artifacts in the same sense.
- Auto-rebasing or squashing of `exp(Run N):` commits. Each Run gets its own commit; we let the user manage history.
