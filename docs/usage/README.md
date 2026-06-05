# Usage docs

Researcher-facing documentation for the `rc` CLI and the Research Copilot workflow (Phase 0).

- [commands.md](commands.md) — every `rc` subcommand: flags, an example invocation, and expected output.
- [claude-code.md](claude-code.md) — how `rc init --claude` wires the `UserPromptSubmit` hook to `rc context`, verifying with `rc doctor`, and Windows notes.
- [workflow-walkthrough.md](workflow-walkthrough.md) — a worked run from `rc init` through creating an experiment task, starting it, reading the injected `[workflow-state]` + `[research-state]` block, verifying, completing, and reading the next recommendation.

## In one paragraph

`rc init` scaffolds a controlled `.research/` directory and (with `--claude`) wires your coding agent. You create tasks with `rc task create`, each carrying a research `kind` and a generic lifecycle status. The agent does not free-wheel: every turn its hook calls `rc context`, which injects the current `[workflow-state]` (what to do in this lifecycle phase) plus a `[research-state]` block (a live, deterministic recommendation computed from the task graph). You drive the loop with `rc task start` / `verify` / `complete`; the verify gate enforces quality (e.g. number traceability for writing tasks) and rolls a failing task back to `in_progress`.

## Conventions used in these docs

- Phase 0 has no published binary. Examples invoke the CLI as `node packages/cli/dist/rc.js`; shortened to `rc` after the first mention. Build first with `pnpm install && pnpm -r build`.
- A "repo" means the directory you ran `rc init` in (it holds `.research/`). All `rc` commands operate on the current working directory.
- Task ids are `YYYY-MM-DD-slug`, derived from the creation date and a slug of the title.
