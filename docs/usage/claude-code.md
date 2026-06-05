# Claude Code setup

Claude Code is the one fully shipped platform in Phase 0. This page explains what `rc init --claude` wires up, how the per-turn injection works, how to verify it, and the Windows specifics.

## What `rc init --claude` does

```bash
# from your project root, after building the CLI
node packages/cli/dist/rc.js init -u <name> --claude
```

Beyond scaffolding `.research/`, the `--claude` flag configures Claude Code in the same repo:

1. **`.claude/settings.json`** — merges in a `UserPromptSubmit` hook (idempotently; existing/foreign config is preserved). The hook calls `rc context` on every prompt:

   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "matcher": "*",
           "hooks": [
             {
               "type": "command",
               "command": "rc context --inject --format text",
               "timeout": 20
             }
           ]
         }
       ]
     }
   }
   ```

2. **`.claude/agents/*.md`** — the 10 neutral `rc-*` executor agents are copied in: `rc-plan`, `rc-literature`, `rc-ideation`, `rc-experiment`, `rc-writer`, `rc-polisher`, `rc-reviewer`, `rc-rebuttal`, `rc-verify`, `rc-update-spec`.

3. **`CLAUDE.md`** — a one-line behavioural note is appended (idempotent): the workflow is governed by `.research/`, the injected block tells the agent the next step, and it should dispatch `rc-*` executors rather than doing domain work inline.

## How injection works each turn

```
You type a prompt
        │
        ▼
Claude Code fires UserPromptSubmit
        │
        ▼
hook runs:  rc context --inject --format text
        │   (rc reads .research/workflow.md + the task graph)
        ▼
stdout block is injected as additionalContext for this turn
```

The injected block has two parts:

- `[workflow-state:<state>]` — guidance for the current lifecycle phase, pulled verbatim from `.research/workflow.md` (the single source of truth). `<state>` is `no_task`, `planning`, `in_progress`, `verify`, or `completed`.
- `[research-state]` — a live, deterministic summary of the task graph: the active task, completed/in-progress/blocked counts, open gaps, and up to three ranked recommendations for what to do next. Nothing is auto-created — the recommendation is advisory; you decide.

Because the hook uses `--format text`, the raw block is the `additionalContext`. (`--format json` wraps it in the `hookSpecificOutput` envelope; the configurator uses `text`, which Claude Code also accepts for `UserPromptSubmit`.) See [the full output examples](commands.md#rc-context).

The `rc` invocation in the hook is the cross-platform Node CLI, so it works identically on macOS, Linux, and Windows as long as `rc` resolves on the PATH (see Windows notes below).

## Verifying the wiring

Run the health check from the repo root:

```
$ rc doctor
OK  .research/ exists
OK  workflow.md exists
OK  .claude/settings.json exists
```

Exit code `0` means all three are present. Any `FAIL` line means that piece is missing and the exit code is `1`. If `.claude/settings.json` is missing, you likely ran `rc init` without `--claude` — re-run with the flag (the settings merge is idempotent and safe to re-apply).

To sanity-check the hook output directly, run the same command the hook runs:

```bash
rc context --inject --format text
```

You should see the `[workflow-state:...]` and `[research-state]` blocks. If you see `Refer to workflow.md for current step.` instead of state-specific guidance, `.research/workflow.md` is missing or its state markers were edited — restore it from `research-kit/workflow.md`.

## Windows notes

The previous plugin used Python hooks, which on Windows needed `shell: powershell` shims and were error-prone. Phase 0 avoids that entirely: the hook calls `rc`, a Node CLI.

- **Resolving `rc`:** in Phase 0 there is no published binary. Either:
  - run `pnpm --filter research-copilot link --global` so an `rc` shim is on your PATH, or
  - temporarily set the hook command to the explicit path, e.g. `node C:\\path\\to\\research_copilot\\packages\\cli\\dist\\rc.js context --inject --format text`.
- **Once published:** `npx research-copilot` (and a global install) will provide `rc` cross-platform; the hook command `rc context ...` then works without changes.
- **Paths:** the CLI uses `node:path` everywhere, so `.research/` and task ids resolve correctly with Windows separators. No POSIX-only assumptions.

If `rc context` returns nothing in the hook, confirm the command resolves by running it manually in the same shell Claude Code launches; a non-zero exit or empty stdout means `rc` is not on the PATH or the working directory has no `.research/`.
