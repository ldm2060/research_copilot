# `rc` command reference

This is the complete Phase 0 command surface. It matches `rc --help` and `rc task --help` exactly.

In Phase 0 invoke the CLI as `node packages/cli/dist/rc.js` (after `pnpm install && pnpm -r build`). Below it is written `rc` for brevity. All commands act on the current working directory (the repo that holds `.research/`).

```
$ rc --help
Usage: rc [options] [command]

Commands:
  context [options]
  doctor
  init [options]
  task
  help [command]     display help for command
```

---

## `rc init`

Scaffold the controlled `.research/` workspace and, with `--claude`, wire Claude Code.

```
Usage: rc init [options]

Options:
  --claude           Claude Code (default: false)
  -u, --user <name>  developer identity   (required)
```

| Flag | Required | Meaning |
|---|---|---|
| `-u, --user <name>` | yes | Developer identity recorded for the workspace. |
| `--claude` | no | Also write Claude Code config (settings hook, agents, CLAUDE.md note). |

What it creates under `.research/`:

- `tasks/`, `spec/{venue,writing,baselines,methodology,novelty}/`, `workspace/`, `.runtime/`
- `workflow.md` (the single source of truth for per-lifecycle-state guidance)
- `config.yaml` (defaults: session commit message, journal cap, lifecycle hooks)

With `--claude` it also writes `.claude/settings.json` (a `UserPromptSubmit` hook calling `rc context --inject --format text`), copies the 10 `rc-*` agent templates into `.claude/agents/`, and appends a one-line workflow note to `CLAUDE.md`. The settings merge is idempotent and preserves any foreign config already present.

**Example:**

```
$ rc init -u alice --claude
Initialized .research/ for: claude-code
```

---

## `rc task create`

Create a research task. Prints the new id on stdout and sets it as the active task.

```
Usage: rc task create [options]

Options:
  --kind <k>      (required) literature|ideation|experiment|writing|polish|review|rebuttal
  --title <t>     (required) human title; slugified into the id
  --venue <v>     optional target venue
  --parent <p>    optional parent task id (builds the task graph)
```

A new task starts at lifecycle status `planning` with priority `P2`. Its id is `YYYY-MM-DD-<slug-of-title>`.

**Example:**

```
$ rc task create --kind experiment --title "Ablate attention heads" --venue NeurIPS
2026-06-05-ablate-attention-heads
```

---

## `rc task start <id>`

Transition `planning -> in_progress`. (Implemented as the FSM transition; illegal transitions throw.)

```
$ rc task start 2026-06-05-ablate-attention-heads
```

Produces no stdout on success.

---

## `rc task set-status <id> <state>`

Apply a lifecycle transition explicitly. `<state>` is one of `planning|in_progress|verify|completed`. The transition must be legal in the FSM (see below) or the command errors.

Allowed transitions:

```
planning   -> in_progress
in_progress -> verify
verify     -> in_progress | completed
completed  -> (terminal)
```

**Example** (move an in-progress task into the verify gate):

```
$ rc task set-status 2026-06-05-results-section verify
```

---

## `rc task verify <id>`

Run the verify gate for the task's `kind`. On pass it prints `verify OK`. On fail it prints the offending tokens, **rolls the task back to `in_progress`** (only if it was in `verify`), and exits 1.

Phase 0 gate: for `kind=writing` it runs **number traceability** — every number in the draft `.tex` artifact must also appear in an evidence artifact (`.log`/`.txt`/`.json`/`.csv`) under the task's `artifacts/`. (Citation compliance also exists in core; see [core API](../dev/core-api.md).)

**Example — pass:**

```
$ rc task verify 2026-06-05-results-section
verify OK for 2026-06-05-results-section
```

**Example — fail (and rollback):**

```
$ rc task verify 2026-06-05-results-section
verify FAILED (untraceable: 99.9); rolled back to in_progress
$ echo $?
1
```

---

## `rc task complete <id>`

Transition `verify -> completed`.

```
$ rc task complete 2026-06-05-results-section
```

Produces no stdout on success. (To complete, the task must already be in `verify`, i.e. it passed the gate.)

---

## `rc task add-gap <id> --desc <d> --suggest <kind>`

Record an open gap on a task. Open gaps feed the `[research-state]` recommender, which can suggest creating a follow-up task of the suggested `kind`.

```
Usage: rc task add-gap [options] <id>

Options:
  --desc <d>      (required) description of the gap
  --suggest <k>   (required) the kind of follow-up task that would resolve it
```

**Example:**

```
$ rc task add-gap 2026-06-05-ablate-attention-heads \
    --desc "need a stronger baseline comparison" --suggest experiment
```

After this, `rc context` surfaces it:

```
Open gaps:
  - [from 2026-06-05-ablate-attention-heads] need a stronger baseline comparison -> suggests: experiment
```

---

## `rc task current`

Print the active task id (or `none`).

```
$ rc task current
2026-06-05-ablate-attention-heads
```

---

## `rc context`

Emit the per-turn injection block: `[workflow-state:<state>]` (read from `workflow.md`) followed by `[research-state]` (computed live from the task graph). This is what the Claude Code `UserPromptSubmit` hook calls every turn.

```
Usage: rc context [options]

Options:
  --platform <p>  platform (default: "claude-code")
  --inject        inject mode (default: false)
  --format <f>    text|json (default: "text")
```

- `--format text` (default): the plain block, for humans or text-injection hooks.
- `--format json`: wraps the block as `{ "hookSpecificOutput": { "hookEventName": "UserPromptSubmit", "additionalContext": "..." } }` — the shape Claude Code expects from a hook.
- `--platform` / `--inject` are accepted for forward compatibility; in Phase 0 only `claude-code` is wired.

**Example (no active task):**

```
$ rc context
[workflow-state:no_task]
No active task. Either answer directly, or run `rc task create --kind <k> --title "<t>"` to start one. Consult [research-state] for recommended next activities.
[/workflow-state]

[research-state]
Active: none
Graph: 0 completed · 0 in_progress · 0 blocked
turn-ts: 2026-06-05T17:18:56.274Z
```

**Example (active in-progress task with an open gap):**

```
$ rc context
[workflow-state:in_progress]
Active task is IN PROGRESS. Dispatch the rc-{kind} executor with prd.md + execute.jsonl specs. Do NOT do domain work inline. When the executor returns, run `rc task verify <id>`.
[/workflow-state]

[research-state]
Active: 2026-06-05-ablate-attention-heads (experiment, in_progress)
Graph: 0 completed · 1 in_progress · 0 blocked
Open gaps:
  - [from 2026-06-05-ablate-attention-heads] need a stronger baseline comparison -> suggests: experiment
Recommended next (you decide, nothing auto-created):
  1. resume experiment task 2026-06-05-ablate-attention-heads (in_progress)
  2. create experiment task to resolve "need a stronger baseline comparison" (from 2026-06-05-ablate-attention-heads)
turn-ts: 2026-06-05T17:18:56.847Z
```

---

## `rc doctor`

Health check. Verifies `.research/`, `.research/workflow.md`, and `.claude/settings.json` exist. Prints one line per check and exits 1 if any fail.

```
$ rc doctor
OK  .research/ exists
OK  workflow.md exists
OK  .claude/settings.json exists
$ echo $?
0
```

If a check fails its line reads `FAIL ...` and the exit code is `1` — useful in CI or as a pre-flight before relying on injection.
