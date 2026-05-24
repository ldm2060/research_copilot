# Copilot Sub-agent Hook Enforcement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote PIPELINE-OS §8 owned-file partition and §9 `__HANDOFF__` discipline from agent self-discipline to hook enforcement.

**Architecture:** Two new Python hooks (`PreToolUse` + `SubagentStop`) share a stateless lib `_copilot_hook_lib.py` that encodes the OWNED matrix, state-machine table, JSON I/O helpers, parsers, and a fail-open `safe_main` wrapper. The `PreToolUse` hook hard-denies non-owned Write/Edit; the `SubagentStop` hook hard-blocks on missing `__HANDOFF__` updates with a 3-strike fuse, and emits SOFT WARN for STATE_OUTPUT / state-jump issues. The existing `session_start_memory_injector.py` is augmented to write a snapshot of `last_updated` timestamps that the `SubagentStop` hook uses as the freshness baseline.

**Tech Stack:** Python 3 stdlib only (`json`, `re`, `pathlib`, `fnmatch`, `os`, `sys`, `datetime`); pytest for unit tests. PowerShell for the manual smoke-test script.

**Spec:** `docs/superpowers/specs/2026-05-24-copilot-subagent-guard-design.md` — read this first; it contains the OWNED matrix, decision tables, edge cases, and Phase 2 deferral list.

---

## File Layout

Plan creates / modifies the following. All other files left untouched.

NEW under `self/hooks/scripts/`:
- `_copilot_hook_lib.py`
- `copilot_write_guard.py`
- `copilot_subagent_stop.py`

NEW under `self/hooks/tests/`:
- `__init__.py`, `conftest.py`
- `fixtures/` containing 5 sample JSONL transcripts
- `test_copilot_hook_lib.py`
- `test_copilot_write_guard.py`
- `test_copilot_subagent_stop.py`
- `test_session_start_snapshot.py`
- `test_state_machine_consistency.py`
- `integration_run.ps1`

MODIFIED:
- `self/hooks/scripts/session_start_memory_injector.py`
- `.claude/settings.json` (LAST step only)

Runtime products (already gitignored under existing `.copilot/` rule):
- `.copilot/.session_snapshot.json`
- `.copilot/.subagent_stop_block_count.json`
- `.copilot/.guard_override` (user-created, optional)
- `.copilot/__violations.log`

---

## Task 1: Set up test scaffolding

**Files:**
- Create `self/hooks/tests/__init__.py` (empty)
- Create `self/hooks/tests/conftest.py`
- Create 5 fixture JSONL files under `self/hooks/tests/fixtures/`

- [ ] Step 1: Install pytest

```powershell
D:/article/.venv/Scripts/pip.exe install pytest
D:/article/.venv/Scripts/python.exe -c "import pytest; print(pytest.__version__)"
```

- [ ] Step 2: Create empty `__init__.py`

- [ ] Step 3: Write `conftest.py` with the contents shown in spec section "conftest.py" (fixtures: `workspace`, `fixtures_dir`, `payload_builder`, `handoff_writer`). Specifically:

```python
"""Shared pytest fixtures for copilot hook tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".copilot").mkdir()
    return tmp_path


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


def make_payload(tool_name: str, tool_input: dict, transcript_path: str,
                 stop_hook_active: bool = False) -> dict:
    return {"tool_name": tool_name, "tool_input": tool_input,
            "transcript_path": transcript_path,
            "stop_hook_active": stop_hook_active}


@pytest.fixture
def payload_builder():
    return make_payload


def write_handoff_block(file: Path, last_updated: str,
                        written_by: str = "copilot-test",
                        key_facts: list[str] | None = None) -> None:
    facts = key_facts or ["(placeholder)"]
    body = "\n".join([
        "",
        "## __HANDOFF__",
        f"- last_updated: {last_updated}",
        f"- written_by: {written_by}",
        "- key_facts:",
        *(f"  - {f}" for f in facts),
        "- next_owner: (none)",
        "",
    ])
    if file.exists():
        file.write_text(file.read_text() + body, encoding="utf-8")
    else:
        file.write_text(body, encoding="utf-8")


@pytest.fixture
def handoff_writer():
    return write_handoff_block
```

- [ ] Step 4: Create 5 fixture JSONL files.

Each file is one JSON object per line. See `task1_fixtures.md` companion document (or write inline):

`transcript_main_only.jsonl`:
```
{"role":"user","content":"hello"}
{"role":"assistant","content":[{"type":"text","text":"hi"}]}
```

`transcript_copilot_literature.jsonl`: assistant message with `metadata.subagent_type = "copilot-literature"` and a sample `[STATE_OUTPUT]` body in content text.

`transcript_copilot_experiment_complete.jsonl`: `subagent_type = "copilot-experiment"`, STATE_OUTPUT with Previous=JUDGED Current=END, all 6 fields present.

`transcript_copilot_experiment_state_jump.jsonl`: `subagent_type = "copilot-experiment"`, STATE_OUTPUT with Previous=UNINITIALIZED Current=END (illegal jump).

`transcript_malformed_state_output.jsonl`: `subagent_type = "copilot-literature"`, STATE_OUTPUT missing Action completed / Capability gate / Evidence / Next allowed.

- [ ] Step 5: Verify pytest discovery

```powershell
D:/article/.venv/Scripts/python.exe -m pytest self/hooks/tests/ --collect-only
```

- [ ] Step 6: Commit

```powershell
git add self/hooks/tests/
git commit -m "test: scaffold pytest setup for copilot hook tests"
```

---

## Task 2: shared lib — agent detection

**Files:**
- Create `self/hooks/scripts/_copilot_hook_lib.py`
- Create `self/hooks/tests/test_copilot_hook_lib.py`

This task implements `is_copilot_agent` (membership in the 8-agent COPILOT_AGENTS frozenset) and `detect_active_agent` (reverse-scans transcript JSONL for the most recent `subagent_type` field across both flat and wrapped record formats).

- [ ] Step 1: Write failing tests for both functions covering: main-only transcript returns None, copilot transcripts return their agent name, empty/missing paths return None, COPILOT_AGENTS membership for all 8 names, negative cases for `None / "" / general-purpose / Explore`.

- [ ] Step 2: Run pytest — confirm ImportError.

- [ ] Step 3: Implement `_copilot_hook_lib.py` with module docstring, `COPILOT_AGENTS` frozenset, `is_copilot_agent`, and `detect_active_agent` (algorithm: read up to last 200 lines of JSONL, reverse iterate, try `metadata.subagent_type` then `subagent_type` then `metadata.agent` then `agent` from each record; first hit wins). Returns None on missing path, unreadable file, or no matches.

- [ ] Step 4: Run tests — expect 6 pass.

- [ ] Step 5: Commit `feat: copilot hook lib detect_active_agent + scope predicate`.

---

## Task 3: shared lib — path normalize + glob match

**Files:**
- Modify `self/hooks/scripts/_copilot_hook_lib.py`
- Modify `self/hooks/tests/test_copilot_hook_lib.py`

- [ ] Step 1: Add failing tests for `normalize_path` (backslash-to-forward, already-forward identity, relative-to-workspace resolution, empty string) and `glob_match` (exact, star, no-match, pipelines S2 vs S3 patterns).

- [ ] Step 2: Run pytest — confirm AttributeError.

- [ ] Step 3: Implement `normalize_path(s, workspace=None)` — if workspace given, try `Path(s).resolve().relative_to(workspace.resolve())`; else fallback `s.replace("\\","/").lower()`. And `glob_match(path, pattern)` using `fnmatch.fnmatchcase` after both sides are lowercased + forward-slashed.

- [ ] Step 4: Run tests — expect 14 pass.

- [ ] Step 5: Commit `feat: copilot hook lib path normalize + glob match`.

---

## Task 4: shared lib — OWNED matrix + STATE_MACHINE

**Files:**
- Modify `self/hooks/scripts/_copilot_hook_lib.py`
- Modify `self/hooks/tests/test_copilot_hook_lib.py`

- [ ] Step 1: Add failing tests:
  - `TestOwnedMatrix` — 8 cases asserting each agent owns its rightful files and rejects others (use spec's OWNED matrix as authoritative).
  - `TestIsKnownArtifact` — 5 cases distinguishing `.copilot/*`, `sections/*.tex`, `references.bib` (known) from `scratch/note.txt`, `README.md` (unknown).
  - `TestStateMachine` — verify all 8 agents have entries; verify legal transition (e.g., `copilot-literature` `UNINITIALIZED → SCANNING`); verify illegal transition (e.g., `copilot-experiment` `UNINITIALIZED → END`); verify unknown agent and unknown source state both return True (no false warns).

- [ ] Step 2: Run pytest — confirm AttributeError.

- [ ] Step 3: Implement in `_copilot_hook_lib.py`:

```python
OWNED: dict[str, list[str]] = {
    "research-copilot": [".copilot/state.md", ".copilot/decisions.md",
                         ".copilot/pipelines/*.md"],
    "copilot-literature": [".copilot/literature.md"],
    "copilot-ideation": [".copilot/ideas.md",
                         ".copilot/pipelines/*-s2-*.md"],
    "copilot-experiment": [".copilot/experiments.md",
                           ".copilot/pipelines/*-s3-*.md"],
    "copilot-writer": ["sections/*.tex", "references.bib",
                       ".copilot/handoff.md"],
    "copilot-polisher": ["sections/*.tex", ".copilot/handoff.md"],
    "copilot-reviewer": [".copilot/reviews/round-*.md",
                         ".copilot/handoff.md"],
    "copilot-rebuttal": [".copilot/handoff.md"],
}

HANDOFF_APPEND_ONLY_AGENTS = frozenset([
    "copilot-writer", "copilot-polisher",
    "copilot-reviewer", "copilot-rebuttal",
])


def is_owned(agent: str, path: str) -> bool:
    if agent not in OWNED:
        return False
    p = path.replace("\\", "/").lower()
    return any(glob_match(p, pat) for pat in OWNED[agent])


_KNOWN_ARTIFACT_GLOBS = [
    ".copilot/state.md", ".copilot/literature.md", ".copilot/ideas.md",
    ".copilot/experiments.md", ".copilot/decisions.md",
    ".copilot/handoff.md", ".copilot/reviews/*.md",
    ".copilot/pipelines/*.md", "sections/*.tex", "references.bib",
]


def is_known_research_artifact(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    return any(glob_match(p, pat) for pat in _KNOWN_ARTIFACT_GLOBS)
```

Then add the `STATE_MACHINE` dict — one entry per agent. Source of truth is each `self/agents/<agent>.agent.md` "My Unique State Table" section. The full dict for all 8 agents (verified against the current agent.md files; Task 17 meta-test will catch drift):

```python
STATE_MACHINE: dict[str, dict[str, list[str]]] = {
    "research-copilot": {
        "UNINITIALIZED":        ["DIAGNOSED"],
        "DIAGNOSED":            ["MODE_A_ROUTING", "MODE_B_PIPELINE", "PAUSED"],
        "MODE_A_ROUTING":       ["AWAIT_SUBAGENT_END"],
        "MODE_B_PIPELINE":      ["AWAIT_SUBAGENT_END"],
        "AWAIT_SUBAGENT_END":   ["DIAGNOSED", "BACK_EDGE_TRIGGERED", "PAUSED", "END"],
        "BACK_EDGE_TRIGGERED":  ["MODE_A_ROUTING", "PAUSED"],
        "PAUSED":               ["END"],
        "END":                  [],
    },
    "copilot-literature": {
        "UNINITIALIZED":          ["SCANNING"],
        "SCANNING":               ["BASELINE_LOCKED", "RELATED_WORK_AUGMENTED"],
        "BASELINE_LOCKED":        ["RELATED_WORK_AUGMENTED", "END"],
        "RELATED_WORK_AUGMENTED": ["END"],
        "END":                    [],
    },
    "copilot-ideation": {
        "UNINITIALIZED":         ["CONTEXT_LOADED", "END"],
        "CONTEXT_LOADED":        ["INTERVIEWING"],
        "INTERVIEWING":          ["PREFERENCES_LOCKED"],
        "PREFERENCES_LOCKED":    ["CANDIDATES_GENERATED"],
        "CANDIDATES_GENERATED":  ["ANALOGIES_ADDED"],
        "ANALOGIES_ADDED":       ["FILTERED"],
        "FILTERED":              ["AWAITING_SELECTION"],
        "AWAITING_SELECTION":    ["DIRECTION_SELECTED", "PREFERENCES_LOCKED"],
        "DIRECTION_SELECTED":    ["VALIDATED"],
        "VALIDATED":             ["END"],
        "END":                   [],
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
    "copilot-writer": {
        "UNINITIALIZED": ["PLAN_DRAFT", "EXPAND", "SHORTEN", "TRANSLATE", "CAPTION"],
        "PLAN_DRAFT":    ["DRAFTING"],
        "DRAFTING":      ["REVIEW_SELF", "END"],
        "EXPAND":        ["REVIEW_SELF", "END"],
        "SHORTEN":       ["REVIEW_SELF", "END"],
        "TRANSLATE":     ["END"],
        "CAPTION":       ["END"],
        "REVIEW_SELF":   ["END"],
        "END":           [],
    },
    "copilot-polisher": {
        "UNINITIALIZED": ["POLISHING"],
        "POLISHING":     ["DE_AI"],
        "DE_AI":         ["VALIDATED"],
        "VALIDATED":     ["END"],
        "END":           [],
    },
    "copilot-reviewer": {
        "UNINITIALIZED":   ["SIMULATE_REVIEW"],
        "SIMULATE_REVIEW": ["EXTRACT_GAPS"],
        "EXTRACT_GAPS":    ["WRITE_ROUND"],
        "WRITE_ROUND":     ["END"],
        "END":             [],
    },
    "copilot-rebuttal": {
        "UNINITIALIZED":   ["PARSE_REVIEWS"],
        "PARSE_REVIEWS":   ["DRAFT_RESPONSE"],
        "DRAFT_RESPONSE":  ["RE_REVIEW", "END"],
        "RE_REVIEW":       ["END"],
        "END":             [],
    },
}


def is_transition_legal(agent: str, previous: str, current: str) -> bool:
    """True if `previous -> current` appears in agent's table.
    Returns True (no false warns) for unknown agent OR unknown source state."""
    sm = STATE_MACHINE.get(agent)
    if sm is None:
        return True
    allowed = sm.get(previous)
    if allowed is None:
        return True
    return current in allowed
```

- [ ] Step 4: Run tests — expect 30 pass.

- [ ] Step 5: Commit `feat: copilot hook lib OWNED matrix + STATE_MACHINE`.

---

## Task 5: shared lib — parsers

**Files:**
- Modify `self/hooks/scripts/_copilot_hook_lib.py`
- Modify `self/hooks/tests/test_copilot_hook_lib.py`

- [ ] Step 1: Add failing tests for `extract_handoff` (full block parses last_updated, written_by, key_facts list, next_owner; no block → None; empty → None; missing last_updated → None inside result), `extract_state_output` (full block parses 6 fields; missing block → None; partial block → only present fields), `state_output_missing_fields` (lists missing from REQUIRED_STATE_OUTPUT_FIELDS; None → all required fields listed).

- [ ] Step 2: Run pytest — confirm fail.

- [ ] Step 3: Implement:
  - `REQUIRED_STATE_OUTPUT_FIELDS = ("Previous","Current","Action completed","Capability gate","Evidence","Next allowed")`
  - `extract_handoff(text)` — find last `## __HANDOFF__`; parse `- last_updated:` / `- written_by:` / `- next_owner:` lines; parse `- key_facts:` as start of a sub-list, append subsequent `- ` lines until a non-list-item.
  - `extract_state_output(text)` — `re.compile(r"\[STATE_OUTPUT\](.*?)\[/STATE_OUTPUT\]", re.DOTALL)`, take last match, split each line on `:` once, build dict.
  - `state_output_missing_fields(so)` — return list of REQUIRED_STATE_OUTPUT_FIELDS not in so (or all if so is None).

- [ ] Step 4: Run tests — expect 41 pass.

- [ ] Step 5: Commit `feat: copilot hook lib HANDOFF + STATE_OUTPUT parsers`.

---

## Task 6: shared lib — JSON I/O (snapshot, counter, violations log)

**Files:**
- Modify `self/hooks/scripts/_copilot_hook_lib.py`
- Modify `self/hooks/tests/test_copilot_hook_lib.py`

- [ ] Step 1: Add failing tests:
  - `TestSnapshotIO`: read missing → `{}`, write+read roundtrip, corrupt JSON → `{}`.
  - `TestCounterIO`: read missing → `{}`, inc 1→2, reset bucket, reset_all for agent.
  - `TestViolationsLog`: log_appends with `sev/kind/agent/file/detail/ts` JSONL record; multiple logs accumulate as lines.

- [ ] Step 2: Run pytest — confirm fail.

- [ ] Step 3: Implement:

```python
import datetime

SNAPSHOT_NAME = ".session_snapshot.json"
COUNTER_NAME = ".subagent_stop_block_count.json"
VIOLATIONS_NAME = "__violations.log"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")


def _copilot_dir(workspace: Path) -> Path:
    d = workspace / ".copilot"
    d.mkdir(exist_ok=True)
    return d


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def read_snapshot(workspace): return _read_json(_copilot_dir(workspace) / SNAPSHOT_NAME)
def write_snapshot(workspace, data): _write_json(_copilot_dir(workspace) / SNAPSHOT_NAME, data)
def counter_read(workspace): return _read_json(_copilot_dir(workspace) / COUNTER_NAME)


def counter_inc(workspace, agent, file) -> int:
    data = counter_read(workspace)
    bucket = data.setdefault(agent, {}).setdefault(
        file, {"count": 0, "last_block_at": None, "reset_at": None})
    bucket["count"] = int(bucket.get("count", 0)) + 1
    bucket["last_block_at"] = _now_iso()
    _write_json(_copilot_dir(workspace) / COUNTER_NAME, data)
    return bucket["count"]


def counter_get(workspace, agent, file) -> int:
    return counter_read(workspace).get(agent, {}).get(file, {}).get("count", 0)


def counter_reset(workspace, agent, file):
    data = counter_read(workspace)
    if agent in data and file in data[agent]:
        data[agent][file]["count"] = 0
        data[agent][file]["reset_at"] = _now_iso()
        _write_json(_copilot_dir(workspace) / COUNTER_NAME, data)


def counter_reset_all(workspace, agent):
    data = counter_read(workspace)
    if agent in data:
        for bucket in data[agent].values():
            bucket["count"] = 0
            bucket["reset_at"] = _now_iso()
        _write_json(_copilot_dir(workspace) / COUNTER_NAME, data)


def log_violation(workspace, sev, kind, agent, detail, file=None):
    rec = {"ts": _now_iso(), "sev": sev, "kind": kind,
           "agent": agent, "detail": detail}
    if file is not None:
        rec["file"] = file
    log = _copilot_dir(workspace) / VIOLATIONS_NAME
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
```

- [ ] Step 4: Run tests — expect 50 pass.

- [ ] Step 5: Commit `feat: copilot hook lib snapshot/counter/violations JSON I/O`.

---

## Task 7: shared lib — overrides (env var + file)

**Files:**
- Modify `self/hooks/scripts/_copilot_hook_lib.py`
- Modify `self/hooks/tests/test_copilot_hook_lib.py`

- [ ] Step 1: Add failing tests for `env_guard_disabled()` (env unset → False, "off" → True, other value → False) and `override_match(workspace, agent, directive)` (file missing → False, line matches + unexpired → True, expired → False, `skip-all` matches any directive, `#` comments ignored, wrong agent → False).

- [ ] Step 2: Run pytest — confirm fail.

- [ ] Step 3: Implement:

```python
import os

OVERRIDE_NAME = ".guard_override"
_OVERRIDE_LINE_RE = re.compile(
    r"^\s*(?P<agent>[\w-]+)\s*:\s*(?P<directive>skip-[\w-]+)\s+until\s+(?P<until>\S+)\s*$"
)


def env_guard_disabled() -> bool:
    return os.environ.get("COPILOT_HOOK_GUARD", "").strip().lower() == "off"


def override_match(workspace, agent, directive) -> bool:
    f = _copilot_dir(workspace) / OVERRIDE_NAME
    if not f.is_file():
        return False
    try:
        content = f.read_text(encoding="utf-8")
    except OSError:
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _OVERRIDE_LINE_RE.match(line)
        if not m or m.group("agent") != agent:
            continue
        d = m.group("directive")
        if d != "skip-all" and d != directive:
            continue
        try:
            until = datetime.datetime.fromisoformat(
                m.group("until").replace("Z", "+00:00"))
        except ValueError:
            continue
        if until.tzinfo is None:
            until = until.replace(tzinfo=datetime.timezone.utc)
        if now < until:
            return True
    return False
```

- [ ] Step 4: Run tests — expect 59 pass.

- [ ] Step 5: Commit `feat: copilot hook lib env-var + .guard_override checks`.

---

## Task 8: shared lib — decisions + safe_main

**Files:**
- Modify `self/hooks/scripts/_copilot_hook_lib.py`
- Modify `self/hooks/tests/test_copilot_hook_lib.py`

- [ ] Step 1: Add failing tests for `allow_decision()`, `deny_decision(reason)`, `block_decision(reason)` decision-builder shapes, and `safe_main` (clean function exits 0; raising function still exits 0 and prints allow to stdout).

- [ ] Step 2: Run pytest — confirm fail.

- [ ] Step 3: Implement:

```python
import sys
import traceback


def allow_decision():
    return {"hookSpecificOutput": {"permissionDecision": "allow"}}


def deny_decision(reason):
    return {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }


def block_decision(reason):
    return {"decision": "block", "reason": reason}


def safe_main(real_main):
    try:
        return int(real_main() or 0)
    except SystemExit:
        raise
    except Exception:
        sys.stderr.write(traceback.format_exc())
        try:
            sys.stdout.write(json.dumps(allow_decision()) + "\n")
            sys.stdout.flush()
        except Exception:
            pass
        return 0
```

- [ ] Step 4: Run tests — expect 64 pass.

- [ ] Step 5: Commit `feat: copilot hook lib decision helpers + safe_main wrapper`.

---

## Task 9: PreToolUse hook — owned-file enforcement (no handoff special case yet)

**Files:**
- Create `self/hooks/scripts/copilot_write_guard.py`
- Create `self/hooks/tests/test_copilot_write_guard.py`

- [ ] Step 1: Write failing tests covering: scope skip (main agent / unknown agent → allow), OWNED allow (literature → literature.md, unrelated scratch path), forbidden DENY (literature → ideas.md, literature → state.md; both Write and Edit), env-var off → allow, `.guard_override skip-owned-check` → allow, empty stdin → allow.

Use a helper `_run(monkeypatch, payload, workspace)` that monkeypatches sys.stdin / sys.stdout / chdir, calls `guard.real_main()`, and returns the parsed JSON.

- [ ] Step 2: Run pytest — confirm ModuleNotFoundError.

- [ ] Step 3: Implement `copilot_write_guard.py`:

```python
"""PreToolUse hook: enforce owned-file partition (PIPELINE-OS §8).

When the active sub-agent is copilot-*, denies Write/Edit to non-owned
artifacts. Falls open on any exception via safe_main().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import _copilot_hook_lib as lib


def real_main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps(lib.allow_decision())); return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps(lib.allow_decision())); return 0

    agent = lib.detect_active_agent(payload.get("transcript_path", ""))
    if not lib.is_copilot_agent(agent):
        print(json.dumps(lib.allow_decision())); return 0

    workspace = Path.cwd()

    if lib.env_guard_disabled():
        lib.log_violation(workspace, "INFO", "DISABLED", agent,
                          "guard bypassed by env var")
        print(json.dumps(lib.allow_decision())); return 0

    if lib.override_match(workspace, agent, "skip-owned-check"):
        lib.log_violation(workspace, "INFO", "OVERRIDE", agent,
                          "skip-owned-check active")
        print(json.dumps(lib.allow_decision())); return 0

    file_path = str((payload.get("tool_input") or {}).get("file_path", ""))
    if not file_path:
        print(json.dumps(lib.allow_decision())); return 0

    norm = lib.normalize_path(file_path, workspace=workspace)

    # PLACEHOLDER for handoff.md special case — added in Task 10.

    if lib.is_owned(agent, norm):
        print(json.dumps(lib.allow_decision())); return 0

    if lib.is_known_research_artifact(norm):
        lib.log_violation(workspace, "HARD", "DENY", agent,
                          "writing to non-owned artifact", file=norm)
        msg = (f"Blocked by copilot-write-guard: {agent} may not write "
               f"{norm}. See PIPELINE-OS §8.")
        print(json.dumps(lib.deny_decision(msg))); return 0

    print(json.dumps(lib.allow_decision())); return 0


if __name__ == "__main__":
    raise SystemExit(lib.safe_main(real_main))
```

- [ ] Step 4: Run tests — expect 9 pass.

- [ ] Step 5: Commit `feat: copilot_write_guard PreToolUse owned-file enforcement`.

---

## Task 10: PreToolUse hook — handoff.md append-only special case

**Files:**
- Modify `self/hooks/scripts/copilot_write_guard.py`
- Modify `self/hooks/tests/test_copilot_write_guard.py`

- [ ] Step 1: Add failing tests in `TestHandoffSpecial`:
  - copilot-writer Edit to handoff.md → allow
  - copilot-writer Write to handoff.md → deny (reason contains "append")
  - copilot-ideation Edit to handoff.md → deny (ideation has no write right to handoff.md)

- [ ] Step 2: Run pytest — confirm at least one fails (the Write deny).

- [ ] Step 3: In `copilot_write_guard.py`, replace the `# PLACEHOLDER for handoff.md special case — added in Task 10.` line with:

```python
    if norm.endswith(".copilot/handoff.md"):
        tool_name = payload.get("tool_name", "")
        if agent in lib.HANDOFF_APPEND_ONLY_AGENTS:
            if tool_name == "Write":
                lib.log_violation(workspace, "HARD", "DENY", agent,
                                  "Write (overwrite) to handoff.md; "
                                  "use Edit to append", file=norm)
                msg = ("Blocked by copilot-write-guard: handoff.md is "
                       "append-only. Use Edit to add a new block, not Write.")
                print(json.dumps(lib.deny_decision(msg))); return 0
            # Edit allowed for these 4 agents — fall through
        else:
            lib.log_violation(workspace, "HARD", "DENY", agent,
                              "agent has no write right to handoff.md",
                              file=norm)
            msg = (f"Blocked by copilot-write-guard: {agent} is not an "
                   f"owner of handoff.md.")
            print(json.dumps(lib.deny_decision(msg))); return 0
```

- [ ] Step 4: Run tests — expect 12 pass.

- [ ] Step 5: Commit `feat: copilot_write_guard handoff.md append-only special case`.

---

## Task 11: SubagentStop hook — scope + override skeleton

**Files:**
- Create `self/hooks/scripts/copilot_subagent_stop.py`
- Create `self/hooks/tests/test_copilot_subagent_stop.py`

- [ ] Step 1: Write failing tests:
  - `TestScope`: main-agent and non-copilot transcripts → allow.
  - `TestOverride`: env off → allow, `skip-handoff-check` override → allow.

Helpers: `_run(monkeypatch, payload, workspace)` similar to Task 9; `_stop_payload(transcript_path, stop_hook_active=False)` builder.

- [ ] Step 2: Run pytest — confirm ModuleNotFoundError.

- [ ] Step 3: Implement the skeleton:

```python
"""SubagentStop hook: HANDOFF freshness (HARD), STATE_OUTPUT 6-field (SOFT),
state-machine no-jump (SOFT).

3-strike fuse: CHECK 1 failing 3 times for the same (agent, file) releases
on strike 3 with [HARD/RELEASE] to avoid lockout.

Falls open via safe_main().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import _copilot_hook_lib as lib


HANDOFF_FILES = {
    "research-copilot":    ["state.md", "decisions.md"],
    "copilot-literature":  ["literature.md"],
    "copilot-ideation":    ["ideas.md"],
    "copilot-experiment":  ["experiments.md"],
    "copilot-writer":    [],
    "copilot-polisher":  [],
    "copilot-reviewer":  [],
    "copilot-rebuttal":  [],
}


def real_main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps(lib.allow_decision())); return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps(lib.allow_decision())); return 0

    agent = lib.detect_active_agent(payload.get("transcript_path", ""))
    if not lib.is_copilot_agent(agent):
        print(json.dumps(lib.allow_decision())); return 0

    workspace = Path.cwd()

    if lib.env_guard_disabled():
        lib.log_violation(workspace, "INFO", "DISABLED", agent,
                          "SubagentStop guard bypassed by env var")
        print(json.dumps(lib.allow_decision())); return 0

    if lib.override_match(workspace, agent, "skip-handoff-check"):
        lib.log_violation(workspace, "INFO", "OVERRIDE", agent,
                          "skip-handoff-check active")
        print(json.dumps(lib.allow_decision())); return 0

    # CHECK 1 (HARD) — Task 12
    # CHECK 3+4 (SOFT) — Task 14
    print(json.dumps(lib.allow_decision()))
    return 0


if __name__ == "__main__":
    raise SystemExit(lib.safe_main(real_main))
```

- [ ] Step 4: Run tests — expect 4 pass.

- [ ] Step 5: Commit `feat: copilot_subagent_stop scope+override skeleton`.

---

## Task 12: SubagentStop — CHECK 1 HANDOFF freshness + 3-strike fuse

**Files:**
- Modify `self/hooks/scripts/copilot_subagent_stop.py`
- Modify `self/hooks/tests/test_copilot_subagent_stop.py`

- [ ] Step 1: Add failing tests:
  - `TestHandoffFreshness`: missing file with snapshot present → block; stale handoff (current == snapshot) → block; fresh handoff (current > snapshot) → allow.
  - `TestFuse`: strikes 1 and 2 → block (counter increments); strike 3 → allow with RELEASE logged + counter reset to 0; successful pass after a block → counter resets.

Pre-write snapshot with `lib.write_snapshot(workspace, {"literature.md": ...})` in each test setup so that absent snapshot ≠ test condition.

- [ ] Step 2: Run pytest — confirm fail (always allows).

- [ ] Step 3: Implement helpers above `real_main`:

```python
def _file_handoff_last_updated(workspace, filename):
    f = workspace / ".copilot" / filename
    if not f.is_file():
        return None
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    h = lib.extract_handoff(text)
    return h.get("last_updated") if h else None


def _iso_strictly_later(current, snapshot):
    if not current:
        return False
    if snapshot is None:
        return True
    return current > snapshot


def _check_handoff_freshness(workspace, agent):
    """Returns (status, msg, file). status ∈ {PASS, HARD_FAIL, SOFT_FAIL}."""
    files = HANDOFF_FILES.get(agent, [])
    if not files:
        return "PASS", "", None
    snapshot_path = workspace / ".copilot" / lib.SNAPSHOT_NAME
    snapshot_exists = snapshot_path.is_file()
    snapshot = lib.read_snapshot(workspace)
    for fname in files:
        cur = _file_handoff_last_updated(workspace, fname)
        snap = snapshot.get(fname)
        if _iso_strictly_later(cur, snap):
            continue
        msg = (f"{agent} did not update .copilot/{fname} __HANDOFF__ "
               f"block this session. Append/refresh the block and "
               f"re-emit STATE_OUTPUT before exiting.")
        return ("SOFT_FAIL" if not snapshot_exists else "HARD_FAIL"), msg, fname
    return "PASS", "", None
```

Replace the placeholder body at the end of `real_main` with:

```python
    status, fail_msg, fail_file = _check_handoff_freshness(workspace, agent)
    if status == "HARD_FAIL":
        n = lib.counter_inc(workspace, agent, fail_file)
        if n < 3:
            lib.log_violation(workspace, "HARD", "BLOCK", agent,
                              f"{fail_msg} (strike {n}/3)", file=fail_file)
            print(json.dumps(lib.block_decision(fail_msg))); return 0
        lib.log_violation(workspace, "HARD", "RELEASE", agent,
                          "3-strike fuse triggered, releasing", file=fail_file)
        lib.counter_reset(workspace, agent, fail_file)
        print(json.dumps(lib.allow_decision())); return 0

    if status == "SOFT_FAIL":
        lib.log_violation(workspace, "INFO", "NO-SNAPSHOT", agent,
                          f"{fail_msg} (degraded: no .session_snapshot.json)",
                          file=fail_file)

    if status == "PASS":
        lib.counter_reset_all(workspace, agent)

    # CHECK 3+4 SOFT — Task 14
    print(json.dumps(lib.allow_decision()))
    return 0
```

- [ ] Step 4: Run tests — expect 10 pass.

- [ ] Step 5: Commit `feat: copilot_subagent_stop CHECK 1 HANDOFF freshness + 3-strike fuse`.

---

## Task 13: SubagentStop — verify first-boot graceful degradation

**Files:**
- Modify `self/hooks/tests/test_copilot_subagent_stop.py` (no script changes — Task 12 already implements SOFT_FAIL branch)

- [ ] Step 1: Add verification tests under `TestFirstBoot`:
  - No snapshot file + fresh handoff written → allow.
  - No snapshot file + no handoff → allow + violations log contains "NO-SNAPSHOT".

- [ ] Step 2: Run pytest — expect both pass without further code changes.

- [ ] Step 3: Commit `test: verify first-boot graceful degradation`.

---

## Task 14: SubagentStop — CHECK 3 + CHECK 4 SOFT WARNs

**Files:**
- Modify `self/hooks/scripts/copilot_subagent_stop.py`
- Modify `self/hooks/tests/test_copilot_subagent_stop.py`

- [ ] Step 1: Add failing tests under `TestSoftWarns`. Helper `_setup_pass(workspace, handoff_writer, fname)` pre-creates handoff + snapshot so CHECK 1 passes:
  - malformed STATE_OUTPUT transcript → allow + log has SOFT + WARN + "STATE_OUTPUT"
  - illegal state-jump transcript (UNINITIALIZED → END on copilot-experiment) → allow + log has SOFT + "transition" or "UNINITIALIZED"
  - clean experiment-complete transcript (JUDGED → END) → allow + no SOFT lines in log

- [ ] Step 2: Run pytest — confirm 2 of 3 fail.

- [ ] Step 3: In `copilot_subagent_stop.py`, add helpers above `real_main`:

```python
def _read_last_assistant_text(transcript_path):
    if not transcript_path:
        return ""
    p = Path(transcript_path)
    if not p.is_file():
        return ""
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines[-100:]):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("role") != "assistant":
            continue
        chunks = []
        content = entry.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(item.get("text", ""))
        elif isinstance(content, str):
            chunks.append(content)
        if chunks:
            return "\n".join(chunks)
    return ""


def _run_soft_checks(workspace, agent, transcript):
    text = _read_last_assistant_text(transcript)
    so = lib.extract_state_output(text)
    missing = lib.state_output_missing_fields(so)
    if missing:
        if so is None:
            lib.log_violation(workspace, "SOFT", "WARN", agent,
                              "STATE_OUTPUT block absent from final reply")
        else:
            lib.log_violation(workspace, "SOFT", "WARN", agent,
                              f"STATE_OUTPUT missing fields: {missing}")
    if so:
        prev, curr = so.get("Previous"), so.get("Current")
        if prev and curr and not lib.is_transition_legal(agent, prev, curr):
            lib.log_violation(workspace, "SOFT", "WARN", agent,
                              f"transition {prev} -> {curr} not in allowed "
                              f"set {lib.STATE_MACHINE.get(agent, {}).get(prev, [])}")
```

Update the final stanza of `real_main` to call `_run_soft_checks(workspace, agent, payload.get("transcript_path", ""))` immediately before the closing `print(json.dumps(lib.allow_decision()))`.

- [ ] Step 4: Run tests — expect 15 pass.

- [ ] Step 5: Commit `feat: copilot_subagent_stop CHECK 3 + CHECK 4 SOFT WARNs`.

---

## Task 15: SessionStart augmentation — write snapshot

**Files:**
- Modify `self/hooks/scripts/session_start_memory_injector.py`
- Create `self/hooks/tests/test_session_start_snapshot.py`

- [ ] Step 1: Write failing tests using `subprocess.run` to invoke the injector with `cwd=workspace`:
  - writes snapshot for existing handoff → `.session_snapshot.json` contains correct last_updated
  - overwrites snapshot each run → second run sees the newer timestamp
  - snapshot file is created when at least one .copilot file exists

- [ ] Step 2: Run pytest — confirm fail.

- [ ] Step 3: In `session_start_memory_injector.py`, after the existing block-building `for fname in COPILOT_FILES:` loop and BEFORE the `if not blocks:` check, INSERT a snapshot-writing block that reads each file's last `## __HANDOFF__` section, extracts `- last_updated:` value (or None if absent), writes `{fname: last_updated_or_None}` to `.copilot/.session_snapshot.json`. Wrap in try/except OSError. Ensure `import json` is at the top.

- [ ] Step 4: Run tests — expect 3 pass.

- [ ] Step 5: Commit `feat: session_start_memory_injector writes .session_snapshot.json`.

---

## Task 16: SessionStart augmentation — 24h violations summary

**Files:**
- Modify `self/hooks/scripts/session_start_memory_injector.py`
- Modify `self/hooks/tests/test_session_start_snapshot.py`

- [ ] Step 1: Add failing tests under `TestViolationsSummary`:
  - empty log (or no log file) → stdout does not mention "Last 24h"
  - recent log with 2 HARD/BLOCK + 1 HARD/RELEASE + 1 SOFT/WARN → stdout contains "Last 24h", "2 HARD", "1 SOFT"
  - log entries older than 24h are ignored

- [ ] Step 2: Run pytest — confirm fail.

- [ ] Step 3: In `session_start_memory_injector.py`, AFTER the existing `[memory-injector] Constraints: ...` print, BEFORE `return 0`, add a block that opens `.copilot/__violations.log` if present, parses each JSONL line, counts records with `ts >= now - 24h`, broken down as HARD/BLOCK, HARD/RELEASE, SOFT/WARN. If any are non-zero, print `[memory-injector] Last 24h: {hard_blocks} HARD blocks ({releases} 3-strike releases), {soft_warns} SOFT warns. See .copilot/__violations.log.`

- [ ] Step 4: Run tests — expect 6 pass.

- [ ] Step 5: Commit `feat: session_start_memory_injector summarizes last-24h violations`.

---

## Task 17: Meta-test — STATE_MACHINE dict matches each agent.md

**Files:**
- Create `self/hooks/tests/test_state_machine_consistency.py`

- [ ] Step 1: Write the parametrized meta-test that:
  - For each of 8 agents, locates `self/agents/<agent>.agent.md`
  - Parses the first markdown table whose header contains "状态" and "可能的下一状态"
  - Compares first-column (state name) and last-column ("[A, B]" parsed) to `lib.STATE_MACHINE[agent]`
  - Asserts both directions: every state in agent.md is in dict, every state in dict is in agent.md, allowed-next sets equal

If parsing fails for any file, use `pytest.xfail(...)` so the test is loud-but-non-fatal.

- [ ] Step 2: Run pytest — expect 8 pass.

If any FAIL with state drift, fix `STATE_MACHINE` in `_copilot_hook_lib.py` (agent.md is source of truth).

- [ ] Step 3: Commit `test: meta-test STATE_MACHINE matches agent.md`.

---

## Task 18: Full sweep + import sanity

**Files:** (no new files; gate)

- [ ] Step 1: Run all hook tests:

```powershell
D:/article/.venv/Scripts/python.exe -m pytest self/hooks/tests/ -v
```

Expect ~105 tests, all pass.

- [ ] Step 2: If any fail, stop and fix. Tests are the gate to Task 20.

- [ ] Step 3: Sanity check the scripts import cleanly:

```powershell
D:/article/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'self/hooks/scripts'); import _copilot_hook_lib, copilot_write_guard, copilot_subagent_stop; print('OK')"
```

Expect prints `OK`.

---

## Task 19: PowerShell integration smoke test

**Files:**
- Create `self/hooks/tests/integration_run.ps1`

- [ ] Step 1: Write a smoke-test script that:
  - Creates a temp workspace with `.copilot/`
  - Builds a fake transcript with `subagent_type = copilot-literature`
  - Pipes a Write payload (writing to `.copilot/ideas.md`) to `copilot_write_guard.py` → assert stdout contains `"deny"`
  - Pipes a SubagentStop payload (no snapshot, no handoff) to `copilot_subagent_stop.py` → assert stdout contains `"allow"` AND `.copilot/__violations.log` contains `NO-SNAPSHOT`
  - Prints "ALL INTEGRATION CHECKS PASSED" on success

Use `Start-Process` with `-RedirectStandardInput` / `-RedirectStandardOutput` and a temp workspace under `$env:TEMP`.

- [ ] Step 2: Run the script:

```powershell
pwsh -File D:/article/self/hooks/tests/integration_run.ps1
```

Expect green PASS messages and exit 0.

- [ ] Step 3: Commit `test: PowerShell integration smoke test for copilot hooks`.

---

## Task 20: Register hooks in `.claude/settings.json` (DEPLOYMENT GATE)

**Files:**
- Modify `D:/article/.claude/settings.json`

**Pre-condition:** Tasks 1–19 complete. All tests green. Integration script passes.

- [ ] Step 1: Re-verify gates:

```powershell
D:/article/.venv/Scripts/python.exe -m pytest self/hooks/tests/ -q
pwsh -File D:/article/self/hooks/tests/integration_run.ps1
```

Both must succeed before proceeding.

- [ ] Step 2: Edit `.claude/settings.json`. Inside the existing `hooks` object:

(a) Append to the existing `PreToolUse` array:

```json
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"D:/article/self/hooks/scripts/copilot_write_guard.py\"",
            "timeout": 10
          }
        ]
      }
```

(b) Add a new `SubagentStop` key inside `hooks` (sibling to PreToolUse / PostToolUse):

```json
    "SubagentStop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python \"D:/article/self/hooks/scripts/copilot_subagent_stop.py\"",
            "timeout": 15
          }
        ]
      }
    ],
```

- [ ] Step 3: Validate JSON:

```powershell
D:/article/.venv/Scripts/python.exe -c "import json; json.loads(open('D:/article/.claude/settings.json', encoding='utf-8').read()); print('OK')"
```

Expect prints `OK`.

- [ ] Step 4: Open a fresh Claude Code session in `D:/article/`. The first SessionStart writes `.copilot/.session_snapshot.json`. Verify the file appears.

- [ ] Step 5: Smoke-test with a real sub-agent. Dispatch a tiny task with `@copilot-literature` ("read literature.md and return"). Verify one of:
  - Agent updates `## __HANDOFF__` → SubagentStop allows
  - Agent doesn't → block + agent retries; after 3 strikes → release + RELEASE log entry

If a stuck loop appears: `$env:COPILOT_HOOK_GUARD = "off"` to escape, then debug.

- [ ] Step 6: Commit `feat: register copilot_write_guard + copilot_subagent_stop hooks`.

---

## Out-of-scope (Phase 2)

Per spec's "Phase 2 candidates":
- PostToolUse line-count diff for handoff.md
- references.bib additive-only diff parser
- Dynamic STATE_MACHINE parser reading agent.md at runtime
- Cross-worktree violations aggregator
- Upgrading SOFT WARN rules to HARD after FP data
- Updating `self/install.py` to auto-register the new hooks

Not part of this plan unless explicitly requested.
