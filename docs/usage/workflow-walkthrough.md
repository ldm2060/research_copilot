# Workflow walkthrough

A worked Phase 0 run on Claude Code: scaffold a project, create and run an experiment task, watch the injected state evolve, pass the verify gate, complete, and read the next recommendation.

Throughout, `rc` is shorthand for `node packages/cli/dist/rc.js` (build first with `pnpm install && pnpm -r build`). All commands run from your project root.

## 0. Initialize

```
$ rc init -u alice --claude
Initialized .research/ for: claude-code
```

This creates `.research/` (tasks/, spec/, workspace/, .runtime/, workflow.md, config.yaml) and wires Claude Code (`.claude/settings.json` hook, `.claude/agents/*.md`, a CLAUDE.md note). Confirm:

```
$ rc doctor
OK  .research/ exists
OK  workflow.md exists
OK  .claude/settings.json exists
```

With no task yet, the injected block is:

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

## 1. Create an experiment task

```
$ rc task create --kind experiment --title "Ablate attention heads" --venue NeurIPS
2026-06-05-ablate-attention-heads
```

The task is created at status `planning` and set active. The injected block now guides planning and recommends resuming it:

```
$ rc context
[workflow-state:planning]
Active task is in PLANNING. Use the rc-plan helper to clarify it into prd.md and curate execute.jsonl / verify.jsonl. Then `rc task start <id>`.
[/workflow-state]

[research-state]
Active: 2026-06-05-ablate-attention-heads (experiment, planning)
Graph: 0 completed · 0 in_progress · 0 blocked
Recommended next (you decide, nothing auto-created):
  1. resume experiment task 2026-06-05-ablate-attention-heads (planning)
turn-ts: 2026-06-05T17:18:56.443Z
```

In a real session you would now have the `rc-plan` agent turn the title into a `prd.md` Goal and curate the execute/verify context. In this walkthrough we move straight on.

## 2. Start it

```
$ rc task start 2026-06-05-ablate-attention-heads
```

The lifecycle moves `planning -> in_progress`. The injected block switches to the execution guidance:

```
$ rc context
[workflow-state:in_progress]
Active task is IN PROGRESS. Dispatch the rc-{kind} executor with prd.md + execute.jsonl specs. Do NOT do domain work inline. When the executor returns, run `rc task verify <id>`.
[/workflow-state]

[research-state]
Active: 2026-06-05-ablate-attention-heads (experiment, in_progress)
Graph: 0 completed · 1 in_progress · 0 blocked
Recommended next (you decide, nothing auto-created):
  1. resume experiment task 2026-06-05-ablate-attention-heads (in_progress)
turn-ts: 2026-06-05T17:18:56.604Z
```

## 3. Execute (the `rc-experiment` agent)

Per the `in_progress` guidance, the main session dispatches the `rc-experiment` executor instead of doing domain work inline. The executor runs the experiments (launching long jobs in the background and watching them), extracts metrics, and writes data + findings into the task's `artifacts/`. If it hits a missing comparison it records a gap:

```
$ rc task add-gap 2026-06-05-ablate-attention-heads \
    --desc "need a stronger baseline comparison" --suggest experiment
```

That gap immediately shows up in the recommender (a second, ranked option to spin up a follow-up experiment):

```
$ rc context
[workflow-state:in_progress]
...
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

## 4. Verify

When the executor returns, move the task into the gate and run verify. (The example below uses a **writing** task to show the number-traceability check, the Phase 0 gate.)

Suppose a writing task `2026-06-05-results-section` has these artifacts:

```
artifacts/draft.tex     ->  "Accuracy improves to 92.5 percent over the 88.0 baseline."
artifacts/metrics.log   ->  "final_acc=92.5\nbaseline=88.0\n"
```

Every number in the draft (`92.5`, `88.0`) is backed by an evidence artifact, so:

```
$ rc task set-status 2026-06-05-results-section verify
$ rc task verify 2026-06-05-results-section
verify OK for 2026-06-05-results-section
```

Now imagine the draft claims an unsupported `99.9`:

```
$ rc task verify 2026-06-05-results-section
verify FAILED (untraceable: 99.9); rolled back to in_progress
$ echo $?
1
```

The gate caught a number with no evidence, exited 1, and **rolled the task back to `in_progress`** so you fix the draft (or produce the missing artifact) before trying again.

## 5. Complete

Once verify passes:

```
$ rc task complete 2026-06-05-results-section
```

The lifecycle moves `verify -> completed`.

## 6. Read the next recommendation

With one task done and an open gap still on the experiment task, the `[research-state]` block now reflects the completion in the graph counts and keeps surfacing the gap-driven recommendation. You consult it and decide the next activity — e.g. accept recommendation 2 and create the follow-up experiment, or pivot to a writing task. Nothing is auto-created; the loop is injection-guided and you stay in control.

```
$ rc task current
2026-06-05-ablate-attention-heads
```

That is the full Phase 0 loop: **init -> create -> start -> (executor) -> verify -> complete -> read the next recommendation**, with `rc context` injecting `[workflow-state]` + `[research-state]` on every turn to steer it.
