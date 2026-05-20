---
name: plugin-dev-agent-development
description: "Workflow for Research Copilot plugin development. Use when creating, updating, reviewing, or debugging `.agent.md`, `SKILL.md`, agent orchestration rules, worker dispatch protocols, pipeline ledger workflows, or plugin packaging docs. Triggers on: plugin-dev, agent-development, agent development, skill development, pipeline ledger, worker dispatch, agent orchestration."
version: 0.1.0
---

# Plugin Dev Agent Development

Use this workflow when developing Research Copilot agents, skills, orchestration rules, or plugin packaging behavior.

## Scope

In scope:

- Creating or editing `.agent.md` files.
- Creating or editing `SKILL.md` files.
- Changing agent routing, worker dispatch, or pipeline-ledger protocols.
- Updating plugin packaging docs or manifests that affect Research Copilot behavior.

Out of scope:

- General application code that does not change agent / skill / plugin behavior.
- MCP server runtime debugging, unless the change affects agent orchestration docs.

## Required workflow

1. Clarify the requested behavior and the affected customization surface.
2. Read the relevant existing agent / skill / manifest files before proposing edits.
3. If the change spans multiple files or agents, write a pipeline ledger under `.copilot/pipelines/` before editing.
4. Break the work into narrow worker-dispatchable tasks with explicit read/write scope.
5. Dispatch workers only for isolated subtasks; keep cross-file orchestration in the coordinator.
6. Review worker returns for spec compliance, evidence, and conflicts before accepting them.
7. Update docs and generated metadata in the same change as the agent / skill behavior.
8. Run the repository's skill metadata and bundle verification commands before declaring completion.

## Pipeline ledger requirement

For multi-file or multi-agent work, create a ledger named:

```text
.copilot/pipelines/YYYY-MM-DD-plugin-dev-<topic>-round-N.md
```

The ledger must contain:

```markdown
## 1. Intake
## 2. Round Plan
## 3. Task Breakdown
## 4. Dispatch Log
## 5. Worker Returns
## 6. Coordinator Review
## 7. Stage Output
```

Write `Intake`, `Round Plan`, and `Task Breakdown` before editing files or dispatching workers.

## Worker prompt template

Every worker prompt must include:

```text
Context & stage: <plugin-dev topic and parent coordinator>
This worker's goal: <one narrow task and explicit non-goals>
Available facts: <paths, excerpts, manifests, prior decisions>
Hard constraints: <allowed files, forbidden files, no invented behavior>
Expected output: <exact patch / audit / table / summary shape>
Stop condition: <when to return blocked>
```

## Verification

Run these commands after edits that affect self-owned skills or bundle output:

```bash
python self/scripts/generate-skill-json.py --check
python scripts/build_copilot_workspace.py --repo-root . --output dist/claude-workspace --target github
```

Also run text consistency checks for changed agent rules:

```bash
rg "sub-agents do NOT Task each other|NEVER let sub-agents call Task" self/AGENTS.md self/agents
rg "pipeline ledger|Worker boundaries|Context & stage" self/AGENTS.md self/agents self/skills/plugin-dev-agent-development
```

The first search should not find stale absolute bans. The second search should show the new protocol in the relevant files.

## Hard constraints

- Do not mix design, implementation, verification, and final reporting in the main session for multi-file agent work.
- Do not let workers change files outside their declared write scope.
- Do not accept worker output without coordinator review.
- Do not leave `skill.json` stale after changing a self-owned skill's frontmatter.
- Do not introduce duplicate skills when an existing self-owned skill already covers the same workflow.