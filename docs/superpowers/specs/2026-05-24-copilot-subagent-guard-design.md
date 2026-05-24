# Copilot Sub-agent Hook Enforcement Design

- Date: 2026-05-24
- Scope: PreToolUse + SubagentStop hook enforcement for the 8 copilot-* agents
- Status: Approved, ready for implementation
- Predecessor: `2026-05-21-research-copilot-workflow-enforcement-design.md` (this builds on the same hook pattern, extending it from research-copilot to all copilot-* sub-agents)

## Background

Today's enforcement landscape (verified by reading `.claude/settings.json`, all 8 `self/agents/copilot-*.agent.md`, `self/PIPELINE-OS.md`, and the existing `self/hooks/scripts/research_copilot_guard.py`):

| Rule | Source | Enforced? |
|---|---|---|
| Pattern 1 — research-copilot must delegate experiments | research_copilot_guard.py | ✅ Hard |
| Pattern 3 — research-copilot state-mandated delegation | research_copilot_guard.py | ✅ Hard |
| Pattern 5 — memory-gate (Read .copilot/*.md before Write) | research_copilot_guard.py | ✅ Hard |
| Pattern 6 — research-gate (≥2 MCP queries before ideas.md Write) | research_copilot_guard.py | ✅ Hard |
| **Rule 1 — END state MUST update `## __HANDOFF__` block** | PIPELINE-OS §3 handoff-gate, §9 schema, every agent.md END row | ❌ Agent self-discipline only |
| **Rule 2 — Sub-agent may write ONLY its owned `.copilot/*.md`** | PIPELINE-OS §8, every agent.md "Forbidden writes" | ❌ Agent self-discipline only |
| **Rule 3 — Every reply ends with 6-field STATE_OUTPUT block** | PIPELINE-OS §2 | ❌ Agent self-discipline only |
| **Rule 4 — State machine: no jumping (Previous → Current must be in "Next allowed")** | PIPELINE-OS §1, every agent.md state table | ❌ Agent self-discipline only |

Empirical evidence that Rules 1–4 are not currently followed: all 6 files under `.copilot/` (state.md / literature.md / ideas.md / experiments.md / decisions.md / handoff.md) still contain placeholder `__HANDOFF__` blocks dated 2026-05-23 with `key_facts: (placeholder)`, despite multiple agent sessions having run since. `session_start_memory_injector.py` already prints a warning `"sub-agents likely not following PIPELINE-OS §9"` but it is a print, not enforcement.

## Goal & Non-goals

**Goal.** Promote Rules 1–4 from "agent self-discipline" to "hook-enforced", with a precision-vs-noise tradeoff per rule (hard block where machine judgment is reliable; soft warn where it is not).

**Non-goals (this spec).**
- Replacing or refactoring `research_copilot_guard.py` — its existing patterns continue to manage the research-copilot-only layer.
- Auditing past violations retroactively.
- Editing any `self/agents/*.agent.md` or `self/PIPELINE-OS.md` content — the source of truth for OWNED files and state tables stays in those files; the hook merely encodes a snapshot of §8 + each state table into Python.

## Design Decision

**Approach C — Layered enforcement: hard where signals are structural, soft where signals are linguistic.**

Considered and rejected:
- **Approach A (all-hard block, including 6-field STATE_OUTPUT and state-jump):** highest enforcement strength, but Rules 3–4 require parsing assistant prose / markdown structure with non-trivial false-positive risk. Hard-blocking on a misparse traps the agent in an unrecoverable loop.
- **Approach B (all-soft warn, audit chain only):** zero false-positive risk, but the user can bypass research-copilot entirely (dispatch a sub-agent directly), in which case no audit ever happens. Equivalent to today's state.

**Chosen mix (Approach C):**

| Rule | Hook | Severity | Rationale |
|---|---|---|---|
| 2. Owned-file | PreToolUse(Write\|Edit) | **HARD DENY** | Pure path-matching, false-positive ≈ 0 |
| 1. HANDOFF freshness | SubagentStop | **HARD BLOCK + 3-strike fuse** | Anchor `## __HANDOFF__` + ISO `last_updated` is machine-readable |
| 3. STATE_OUTPUT 6 fields | SubagentStop | **SOFT WARN** | Linguistic parse; collect data first, harden in Phase 2 |
| 4. State-machine no-jump | SubagentStop | **SOFT WARN** | Per-agent table, structural but variable; same Phase 2 strategy |

## Architecture

### Component layout

```
self/hooks/scripts/
├── research_copilot_guard.py         (UNCHANGED — research-copilot's existing 4 patterns)
├── session_start_memory_injector.py  (MODIFIED — also writes .session_snapshot.json)
├── _copilot_hook_lib.py              (NEW — shared lib)
├── copilot_write_guard.py            (NEW — PreToolUse, Rule 2)
└── copilot_subagent_stop.py          (NEW — SubagentStop, Rules 1/3/4)
```

```
.copilot/                              (per-worktree; gitignored runtime products)
├── state.md, literature.md, ...      (existing artifacts)
├── .session_snapshot.json            (NEW — last_updated snapshot per artifact)
├── .subagent_stop_block_count.json   (NEW — fuse counters)
├── .guard_override                   (NEW — optional user override)
└── __violations.log                  (NEW — JSONL append-only)
```

```
.claude/settings.json hooks block:
  PreToolUse:
    matcher: "Write|Edit"             (existing block_protected_paths.py)
    matcher: "Bash|PowerShell|Agent|Write|Edit"  (existing research_copilot_guard.py + prompt fallback)
    matcher: "Write|Edit"             (NEW: copilot_write_guard.py)
  SubagentStop:
    (NEW block):
    matcher: "*"
    command: copilot_subagent_stop.py
```

### Flow

```
                    ┌─ subagent_type = copilot-*  ──┐
User / coordinator ─┤                                │
                    └─ subagent_type = anything else ┴─► (hooks skip, fail-open)

  copilot-* lifecycle:
  ─────────────────────────────────────────────────────────────
  SessionStart  →  session_start_memory_injector.py
                   ├─ inject __HANDOFF__ summaries (existing)
                   └─ write .copilot/.session_snapshot.json (NEW)

  Tool call (Write/Edit)
                →  copilot_write_guard.py (PreToolUse)
                   ├─ active agent ∈ copilot-* ?
                   ├─ file ∈ OWNED?      → allow
                   ├─ file ∈ FORBIDDEN?  → DENY + log [HARD/DENY]
                   └─ else (unrelated)   → allow

  Sub-agent ends → copilot_subagent_stop.py (SubagentStop)
                   ├─ CHECK 1 (hard): HANDOFF freshness vs snapshot
                   ├─ CHECK 3 (soft): STATE_OUTPUT 6 fields present
                   ├─ CHECK 4 (soft): Previous → Current legal
                   └─ Decision:
                      CHECK 1 fail + count < 3  → block + count++
                      CHECK 1 fail + count ≥ 3  → log [HARD/RELEASE] + allow
                      CHECK 1 pass              → reset count + emit SOFT warns + allow
```

## Component spec

### `_copilot_hook_lib.py`

Shared helpers:

- `detect_active_agent(transcript_path) -> str | None`
  Re-implements the same scan as `research_copilot_guard.detect_active_agent` (reverse iterate JSONL, return most recent `subagent_type`).
- `OWNED: dict[str, list[str]]`
  Hard-coded OWNED matrix (see "OWNED matrix" section below); paths are glob patterns matched with `fnmatch`.
- `STATE_MACHINE: dict[str, dict[str, list[str]]]`
  Hard-coded `{agent_name: {state: [allowed_next_states, ...]}}`, transcribed verbatim from each `*.agent.md` state table.
- `normalize_path(s) -> str`
  Lowercase + forward-slash + `Path.resolve` if possible.
- `read_snapshot() / write_snapshot()`, `read_counter() / write_counter()`
  JSON I/O with crash-safe defaults (`{}` on parse failure).
- `extract_handoff(text) -> dict | None`
  Parse the trailing `## __HANDOFF__` block; return `{last_updated, written_by, key_facts, next_owner}` or None.
- `extract_state_output(text) -> dict | None`
  Find the last `[STATE_OUTPUT] ... [/STATE_OUTPUT]` in a string; parse 6 fields.
- `log_violation(sev, kind, agent, detail, file=None)`
  Append one JSONL line to `.copilot/__violations.log`.
- `safe_main(real_main)`
  Top-level try/except wrapper; on any exception prints `{"hookSpecificOutput": {"permissionDecision": "allow"}}` + stderr trace. Ensures hook self-crash never traps the user.

### `copilot_write_guard.py` (PreToolUse, matcher `Write|Edit`)

Pseudo-flow:

```python
payload = json.load(sys.stdin)
agent = detect_active_agent(payload["transcript_path"])

# Scope check
if not agent or not agent.startswith("copilot-") and agent != "research-copilot":
    return allow()

tool = payload["tool_name"]
fp = normalize_path(payload["tool_input"].get("file_path", ""))

# handoff.md append-only special case
if fp.endswith(".copilot/handoff.md"):
    if agent in {"copilot-writer", "copilot-polisher", "copilot-reviewer", "copilot-rebuttal"}:
        if tool == "Write":
            log_violation("HARD", "DENY", agent, "Write (full overwrite) to handoff.md; use Edit to append", fp)
            return deny("handoff.md is append-only — use Edit, not Write.")
        return allow()  # Edit
    log_violation("HARD", "DENY", agent, "agent has no write right to handoff.md", fp)
    return deny(f"{agent} is not an owner of handoff.md.")

# Owned-file check
owned_globs = OWNED.get(agent, [])
if any(fnmatch_match(fp, glob) for glob in owned_globs):
    return allow()

# Forbidden if it's a .copilot/* or sections/*.tex or references.bib that we DO know about
if is_known_research_artifact(fp):
    log_violation("HARD", "DENY", agent, f"writing to non-owned artifact", fp)
    return deny(f"{agent} may not write {fp}. See PIPELINE-OS §8.")

# Unrelated path (e.g., agent writes a local scratch file) → allow
return allow()
```

`is_known_research_artifact(fp)` returns True for any path that falls inside `.copilot/`, `sections/*.tex`, `references.bib`, `pipelines/*.md`, `reviews/round-*.md` — i.e., the universe defined by PIPELINE-OS §8. Anything outside that universe is the agent's own private scratch and is freely writable.

### `copilot_subagent_stop.py` (SubagentStop, matcher `*`)

```python
payload = json.load(sys.stdin)
agent = detect_active_agent(payload["transcript_path"])

if not agent or not (agent.startswith("copilot-") or agent == "research-copilot"):
    return allow()  # not our scope

# Override
if env_override_active() or file_override_matches(agent):
    log_violation("INFO", "OVERRIDE", agent, "guard bypassed by override")
    return allow()

stop_hook_active = payload.get("stop_hook_active", False)
transcript = read_assistant_tail(payload["transcript_path"])

# CHECK 1 — HARD
hard_fail_msg = None
for owned_file in agent_handoff_files(agent):  # e.g. literature.md for copilot-literature
    snap = snapshot_get(owned_file)
    cur  = file_handoff_last_updated(owned_file)
    if cur is None or (snap is not None and not iso_later(cur, snap)):
        hard_fail_msg = f"{agent} did not update .copilot/{owned_file} __HANDOFF__ block this session."
        break

# CHECK 3 — SOFT
so = extract_state_output(transcript)
missing = required_fields_missing(so)
if missing:
    log_violation("SOFT", "WARN", agent, f"STATE_OUTPUT missing fields: {missing}")

# CHECK 4 — SOFT
if so:
    prev, curr = so.get("Previous"), so.get("Current")
    allowed = STATE_MACHINE.get(agent, {}).get(prev, None)
    if allowed is not None and curr not in allowed:
        log_violation("SOFT", "WARN", agent, f"transition {prev} -> {curr} not in {allowed}")

# Decision
if hard_fail_msg:
    counter_inc(agent, owned_file)
    n = counter_get(agent, owned_file)
    if n < 3:
        log_violation("HARD", "BLOCK", agent, f"{hard_fail_msg} (strike {n}/3)", owned_file)
        return block(hard_fail_msg + " Append/refresh the block before exiting.")
    log_violation("HARD", "RELEASE", agent, "3-strike fuse triggered, releasing", owned_file)
    counter_reset(agent, owned_file)
    return allow()

counter_reset_all(agent)
return allow()
```

`block(msg)` returns the standard SubagentStop block decision:

```json
{
  "decision": "block",
  "reason": "<msg>"
}
```

(Format follows the Claude Code SubagentStop hook contract; if the actual field names differ in current Claude Code, adjust during integration smoke test — see "Open uncertainties.")

### `session_start_memory_injector.py` augmentation

Append after existing logic:

```python
snapshot = {}
for fname in COPILOT_FILES:
    f = copilot / fname
    if not f.is_file():
        continue
    text = f.read_text(encoding="utf-8", errors="replace")
    handoff = extract_handoff(text)  # imported from _copilot_hook_lib
    snapshot[fname] = handoff.get("last_updated") if handoff else None

(copilot / ".session_snapshot.json").write_text(
    json.dumps(snapshot, indent=2), encoding="utf-8"
)
```

Plus a new pre-existing-injection block: read `__violations.log` tail of last 24h, count HARD vs SOFT, print AFTER the existing `__HANDOFF__` injection (so the user sees research state first, then recent violations as context):

```
[memory-injector] Last 24h: {hard_blocks} HARD blocks ({releases} 3-strike releases), {soft_warns} SOFT warns. See .copilot/__violations.log.
```

### `.claude/settings.json` additions

Add to existing `hooks` object:

```json
"PreToolUse": [
  ...,
  {
    "matcher": "Write|Edit",
    "hooks": [{
      "type": "command",
      "command": "python \"D:/article/self/hooks/scripts/copilot_write_guard.py\"",
      "timeout": 10
    }]
  }
],
"SubagentStop": [
  {
    "matcher": "*",
    "hooks": [{
      "type": "command",
      "command": "python \"D:/article/self/hooks/scripts/copilot_subagent_stop.py\"",
      "timeout": 15
    }]
  }
]
```

The matcher `Write|Edit` deliberately omits `NotebookEdit` (no `.ipynb` in `.copilot/`).

## OWNED matrix

Source of truth: `self/PIPELINE-OS.md §8`. Glob form (matched against forward-slash normalized relative path):

| agent | OWNED globs | Special |
|---|---|---|
| `research-copilot` | `.copilot/state.md`, `.copilot/decisions.md`, `.copilot/pipelines/*.md` | — |
| `copilot-literature` | `.copilot/literature.md` | — |
| `copilot-ideation` | `.copilot/ideas.md`, `.copilot/pipelines/*-S2-*.md` | — |
| `copilot-experiment` | `.copilot/experiments.md`, `.copilot/pipelines/*-S3-*.md` | — |
| `copilot-writer` | `sections/*.tex`, `references.bib`, `.copilot/handoff.md` | handoff.md: Edit only |
| `copilot-polisher` | `sections/*.tex`, `.copilot/handoff.md` | handoff.md: Edit only |
| `copilot-reviewer` | `.copilot/reviews/round-*.md`, `.copilot/handoff.md` | handoff.md: Edit only |
| `copilot-rebuttal` | `.copilot/handoff.md` | handoff.md: Edit only |

`pipelines/*.md` not matching `*-S2-*` or `*-S3-*` → defaults to research-copilot owned. Files outside this universe (e.g. agent's own scratch under `/tmp/`, project root README, etc.) → unconditionally allowed for any agent.

## State machine table (per-agent)

Transcribed from each agent.md state table — used by CHECK 4. Stored as a Python dict literal in `_copilot_hook_lib.py`. Excerpt:

```python
STATE_MACHINE = {
  "copilot-literature": {
    "UNINITIALIZED":          ["SCANNING"],
    "SCANNING":               ["BASELINE_LOCKED", "RELATED_WORK_AUGMENTED"],
    "BASELINE_LOCKED":        ["RELATED_WORK_AUGMENTED", "END"],
    "RELATED_WORK_AUGMENTED": ["END"],
    "END":                    [],
  },
  "copilot-experiment": {
    "UNINITIALIZED":   ["CONTEXT_LOADED"],
    "CONTEXT_LOADED":  ["DESIGN_READY"],
    "DESIGN_READY":    ["APPROVED"],
    "APPROVED":        ["EXECUTING"],
    "EXECUTING":       ["COMPLETED"],
    "COMPLETED":       ["VERIFIED"],
    "VERIFIED":        ["JUDGED"],
    "JUDGED":          ["END", "EXECUTING"],
    "END":             [],
  },
  ...  # 6 more agents transcribed similarly; full 8-agent dict lives in _copilot_hook_lib.py
}
```

Maintenance contract: any change to an agent.md state table must mirror into this dict. The unit test `test_state_machine_dict_matches_agent_md` (see Testing) acts as a sanity tripwire by parsing each agent.md state table with a best-effort markdown-table regex and diffing against the dict.

## Failure handling

### Fuse counter (`.copilot/.subagent_stop_block_count.json`)

```json
{
  "<agent>": {
    "<file>": {
      "count": int,
      "last_block_at": "ISO 8601 or null",
      "reset_at": "ISO 8601 or null"
    }
  }
}
```

Per-(agent, file) bucket. Resetting one bucket does not affect siblings. Explicit state machine:

| Event | Pre-count | Action | Post-count | Decision |
|---|---|---|---|---|
| CHECK 1 fail | 0 | log `[HARD/BLOCK]` "strike 1/3", `last_block_at = now` | 1 | `block` |
| CHECK 1 fail | 1 | log `[HARD/BLOCK]` "strike 2/3", `last_block_at = now` | 2 | `block` |
| CHECK 1 fail | 2 | log `[HARD/RELEASE]` "3-strike fuse, releasing" | 0 (reset) | `allow` |
| CHECK 1 pass | any | clear all of agent's buckets | 0 | `allow` |

Concretely: the 1st and 2nd failed Stop attempts are blocked; the 3rd is allowed through to avoid lockout. A subsequent successful PASS resets the counter so the next failure-cycle starts fresh.

### Violations log (`.copilot/__violations.log`)

JSONL append-only:

```jsonc
{"ts":"2026-05-24T10:30:15Z","sev":"HARD","kind":"DENY","agent":"copilot-literature","detail":"writing to non-owned artifact","file":".copilot/ideas.md"}
{"ts":"2026-05-24T10:31:02Z","sev":"HARD","kind":"BLOCK","agent":"copilot-literature","detail":"... __HANDOFF__ not updated (strike 1/3)","file":"literature.md"}
{"ts":"2026-05-24T10:33:48Z","sev":"HARD","kind":"RELEASE","agent":"copilot-literature","detail":"3-strike fuse triggered, releasing","file":"literature.md"}
{"ts":"2026-05-24T10:40:11Z","sev":"SOFT","kind":"WARN","agent":"copilot-experiment","detail":"STATE_OUTPUT missing fields: ['Capability gate','Evidence']"}
{"ts":"2026-05-24T10:55:33Z","sev":"INFO","kind":"SKIPPED","agent":null,"detail":"transcript_path unreadable; fail-open"}
{"ts":"2026-05-24T11:02:00Z","sev":"INFO","kind":"OVERRIDE","agent":"copilot-literature","detail":"guard bypassed by .guard_override"}
```

`sev ∈ {HARD, SOFT, INFO}`; `kind ∈ {DENY, BLOCK, RELEASE, WARN, SKIPPED, OVERRIDE, DISABLED, AUDIT-NEEDED}`. Unknown fields tolerated by readers.

### Override mechanisms

**Env var (global kill switch):**
```
$env:COPILOT_HOOK_GUARD = "off"
```
Hook checks at top of `_real_main`; if "off", log `[INFO/DISABLED]` and `allow`.

**`.copilot/.guard_override` (scoped, time-limited):**
One rule per line. Grammar:

```
<agent-name> : <directive> until <ISO-8601>
```

Where `<directive> ∈ {skip-handoff-check, skip-owned-check, skip-all}`. Examples:

```
copilot-literature: skip-handoff-check until 2026-05-24T12:00:00Z
copilot-experiment: skip-all until 2026-05-25T09:00:00Z
```

Lines starting with `#` are comments. Hooks parse on each invocation, match agent, verify `now < until`. Match → `allow` + `[INFO/OVERRIDE]`.

## Edge cases (Section 4 of brainstorm)

### Path normalization

`path.replace("\\","/").lower()` before any comparison. Glob matching via `fnmatch.fnmatchcase` after lowercasing. `Path.resolve().relative_to(workspace)` attempted first; on failure (path outside workspace), fall back to substring matching for `.copilot/<filename>`.

### Worktree isolation

`.claude/worktrees/agent-*/` each has its own `.copilot/`. Hook uses `Path.cwd()` as workspace root — automatically isolates snapshots, counters, logs per worktree. No cross-worktree synchronization.

### Backup `agents/` directories

`self/agents/backup-2026-05-21/`, `backup-2026-05-23/` are ignored by the hook entirely. The hook reads `subagent_type` from the transcript, not from any agent.md file path. The OWNED matrix is hard-coded in Python; it does not parse agent.md files at runtime.

### `references.bib` additive-only

PreToolUse does **not** diff-check. copilot-writer's Write/Edit to `references.bib` is allowed. A `[INFO/AUDIT-NEEDED]` is logged so research-copilot's AWAIT_SUBAGENT_END audit step (or a future Phase-2 PostToolUse hook) can verify no entry was overwritten.

### `handoff.md` Edit-content depth

First version checks **tool type only** (Write = deny, Edit = allow). It does not verify Edit truly appends vs deletes existing blocks. Acceptable for v1; Phase 2 candidate: PostToolUse line-count diff check.

### `pipelines/*.md` multi-coordinator

OWNED matrix splits by filename pattern:
- `*-S2-*.md` → copilot-ideation
- `*-S3-*.md` → copilot-experiment
- Anything else → research-copilot

A pipelines file with neither marker defaults to research-copilot.

### First boot / missing snapshot

`.session_snapshot.json` not present → snapshot treated as `{f: None for f in COPILOT_FILES}`. CHECK 1 then degrades:
- File's current `__HANDOFF__` exists with a valid ISO `last_updated` → PASS (anything is newer than None)
- File missing or no `__HANDOFF__` → **SOFT WARN only**, not HARD BLOCK, log `[INFO/NO-SNAPSHOT]`.

This guarantees a fresh deploy or a hook-disable-then-reenable cycle never traps any agent.

### Hook self-crash

Top-level `safe_main(_real_main)` wrapper catches every exception, prints `{"hookSpecificOutput": {"permissionDecision": "allow"}}` to stdout, writes traceback to stderr. Hook is fail-open by design.

### Settings matcher

PreToolUse uses `Write|Edit` (omits `NotebookEdit`). SubagentStop matcher is `*`.

## Testing strategy

### Unit tests (`self/hooks/tests/test_copilot_guards.py`, pytest)

- `test_detect_active_agent_*` — 3 fixture transcripts (copilot-literature active, research-copilot active, main agent only) verify correct return.
- `test_owned_matrix_coverage` — for each of 8 agents × 8 representative paths, assert allow/deny matches the OWNED matrix.
- `test_handoff_freshness_{snapshot_older,snapshot_newer,no_handoff,no_snapshot}` — 4 cases for CHECK 1.
- `test_fuse_count_{1,2,3,4}` — strike 1/2 blocks, strike 3 releases, post-pass resets.
- `test_state_output_parse_{full,missing_field,nested,absent}` — 4 cases for CHECK 3.
- `test_state_machine_legality_{legal_step,illegal_jump}_per_agent` — 8 × 2 = 16 cases for CHECK 4.
- `test_handoff_md_append_only` — Write denied, Edit allowed, for each of the 4 multi-writers.
- `test_self_crash_returns_allow` — inject a malformed payload, confirm hook prints allow + nonzero stderr.
- `test_state_machine_dict_matches_agent_md` — meta-test: parse each agent.md state table with a regex, diff against the hard-coded `STATE_MACHINE` dict, assert equal. This is the maintenance tripwire.

### Integration smoke test (`self/hooks/tests/integration_run.ps1`)

Manual steps (run once after implementation):

1. **Empty SubagentStop**: dispatch `Agent(subagent_type="copilot-literature")` with prompt "do nothing, return immediately". Confirm SubagentStop fires and blocks with HANDOFF message.
2. **Cross-file Write**: in a forced session where active agent is copilot-literature, attempt `Write(.copilot/ideas.md, ...)`. Confirm PreToolUse denies, violations.log has `[HARD/DENY]`.
3. **3-strike release**: deliberately keep failing CHECK 1 three times; confirm 3rd time returns allow + `[HARD/RELEASE]` logged + counter reset.
4. **Override**: set `$env:COPILOT_HOOK_GUARD="off"`; rerun step 1; confirm allow + `[INFO/DISABLED]`.
5. **Snapshot regen**: delete `.session_snapshot.json`, trigger SessionStart, confirm file regenerated.

### Deployment gate

All unit tests pass + steps 1–3 of integration succeed before adding the hook entries to `.claude/settings.json`. Until then, hooks live as scripts but are not registered.

## Open uncertainties

| Item | Current assumption | Resolution plan |
|---|---|---|
| `stop_hook_active` field name & semantics | Per Claude Code docs: payload contains `stop_hook_active=true` on the second+ block iteration | Verify at integration step 1; if field differs, adjust counter logic |
| SubagentStop decision schema | `{"decision":"block","reason":"..."}` | Verify same; some Claude Code versions use `hookSpecificOutput.stopDecision` instead |
| `subagent_type` in transcript metadata | Same JSONL shape as `research_copilot_guard.detect_active_agent` already reads | Reuse that detector verbatim |

## Phase 2 candidates (out of scope for v1)

| Phase 2 item | Triggering condition |
|---|---|
| PostToolUse line-count diff for handoff.md | If integration shows Edit-based delete-then-rewrite of handoff.md occurring |
| `references.bib` diff parser for additive-only | If `[INFO/AUDIT-NEEDED]` accumulates > 5 per week |
| Dynamic STATE_MACHINE parser reading agent.md | If meta-test `test_state_machine_dict_matches_agent_md` drifts frequently |
| Cross-worktree violations aggregator | If multi-worktree dev becomes routine |
| Upgrade Rules 3/4 from SOFT to HARD | If 4 weeks of SOFT WARN logs show < 5% false-positive rate |
