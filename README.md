# Research Copilot

English | [简体中文](README.zh-CN.md)

Research Copilot is a Trellis-style, research-native, multi-platform CLI (`rc`) for running academic research as a controlled, stateful workflow. It models each piece of work as a task with a generic lifecycle (`planning -> in_progress -> verify -> completed`) crossed with a research activity `kind` (literature, ideation, experiment, writing, polish, review, rebuttal). Steering is **injection-driven**: each turn a coding-agent hook runs `rc context`, injecting the current workflow state plus a deterministic next-step recommendation computed from the task graph — you decide what to do next, nothing is auto-created.

This rebuild **supersedes the previous Claude Code plugin architecture** (320+ skills / MCP servers shipped as a plugin). See [the redesign spec](docs/superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md) for the locked decisions and rationale.

- Author: ldm2060
- Repo: https://github.com/ldm2060/research_copilot

## Status

**Phase 0 — shipped:**

- `packages/core` — the pure engine: task model, lifecycle FSM, research-state recommender, verify checks, workflow parser, context builder.
- `packages/cli` — the `rc` command-line tool.
- `packages/adapters` — the platform registry plus the Claude Code configurator.
- `research-kit/` — workflow.md, 10 neutral `rc-*` agent templates, config defaults, spec templates.
- **Claude Code is the one fully shipped platform** (class-1 push injection via a `UserPromptSubmit` hook).

Other platforms are designed in the adapter registry; their adapters land in later phases (see the matrix below).

## Installation

### Quick Start (npx - no installation)

```bash
npx @research-copilot/cli init --user your-name --claude
```

### NPM (Recommended)

```bash
npm install -g @research-copilot/cli
```

### Alternative Methods

- **pnpm**: `pnpm add -g @research-copilot/cli`
- **Yarn**: `yarn global add @research-copilot/cli`
- **From Source**: Clone and build (see [INSTALLATION.md](./INSTALLATION.md))
- **GitHub Releases**: Download pre-built archives (see [Releases](https://github.com/ldm2060/research_copilot/releases))

See [INSTALLATION.md](./INSTALLATION.md) for detailed installation instructions, platform-specific notes, and troubleshooting.

## Quick Start Guide

New to Research Copilot? Start here:

- **[Getting Started Guide](docs/usage/getting-started.md)** — Step-by-step tutorial from installation to your first task
- **[快速入门指南（中文）](docs/usage/getting-started.zh-CN.md)** — 中文版快速入门教程

## The `rc` commands

| Command | What it does |
|---|---|
| `rc init -u <name> [--claude]` | Scaffold `.research/` and (with `--claude`) wire Claude Code config. |
| `rc task create --kind <k> --title <t> [--venue <v>] [--parent <p>]` | Create a research task; prints its id and sets it active. |
| `rc task start <id>` | Move a task `planning -> in_progress`. |
| `rc task set-status <id> <state>` | Apply a lifecycle transition explicitly. |
| `rc task verify <id>` | Run the verify gate; failure rolls the task back to `in_progress`. |
| `rc task complete <id>` | Move a task `verify -> completed`. |
| `rc task add-gap <id> --desc <d> --suggest <kind>` | Record an open gap that drives next-step recommendations. |
| `rc task current` | Print the active task id. |
| `rc context [--platform <p>] [--inject] [--format text\|json]` | Emit the per-turn injection block; called by the Claude Code hook each turn. |
| `rc doctor` | Check `.research/`, `workflow.md`, and `.claude/settings.json` exist; exit 1 on failure. |

`kind` is one of: `literature`, `ideation`, `experiment`, `writing`, `polish`, `review`, `rebuttal`. Full flag reference and examples: [docs/usage/commands.md](docs/usage/commands.md).

## Platform support matrix

| Platform | Status | Injection |
|---|---|---|
| Claude Code | ✅ Complete | Class-1 push — `UserPromptSubmit` hook -> `rc context` |
| Codex | ✅ Complete | Class-1 push — `UserPromptSubmit` hook (version-gated) |
| OpenCode | ✅ Complete | Class-1 push — in-process `chat.system.transform` plugin |
| Gemini CLI | ✅ Complete | Class-1 push — `BeforeAgent` hook |
| Cursor | ✅ Complete | Class-2 breadcrumb — sessionStart once + always-on `Active task:` rule |
| Windsurf | ✅ Complete | Class-2 breadcrumb — always-on rule (agent-less) |
| Kiro / Qoder / CodeBuddy / Droid / Pi / Copilot / Kilo / Antigravity | 🔄 Planned | Registry + template increment |

**Class-1** platforms support per-turn push injection; **class-2** platforms cannot, so the agent re-echoes an `Active task:` breadcrumb each turn and re-resolves state. See [docs/dev/architecture.md](docs/dev/architecture.md) and [docs/dev/adding-a-platform.md](docs/dev/adding-a-platform.md).

## Relationship to the old plugin

Research Copilot was previously a Claude Code plugin (a marketplace bundle of 320+ skills, 10 agents, 6 Python MCP servers, and a SessionStart guard hook). That architecture is **superseded** by this TypeScript-full-stack, multi-platform rebuild. The decision log (D1–D8) and migration path are recorded in [the redesign spec](docs/superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md) and [docs/dev/adr/0001-trellis-emulation.md](docs/dev/adr/0001-trellis-emulation.md).

## Documentation

- **Usage (researchers):** [docs/usage/](docs/usage/README.md) — command reference, Claude Code setup, a full workflow walkthrough.
- **Development (contributors):** [docs/dev/architecture.md](docs/dev/architecture.md), [docs/dev/core-api.md](docs/dev/core-api.md), [docs/dev/adding-a-platform.md](docs/dev/adding-a-platform.md), [docs/dev/testing.md](docs/dev/testing.md), [docs/dev/adr/0001-trellis-emulation.md](docs/dev/adr/0001-trellis-emulation.md).
