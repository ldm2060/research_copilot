# Architecture

Research Copilot is a Trellis-style framework: a generic, multi-platform CLI base with a research-domain layer on top. This page maps the layers, the two-layer state model, the injection-driven steering, and the platform model. It corresponds to the redesign spec §3–§6 ([docs/superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md](../superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md)).

## Layer map (spec §3.1)

A pnpm monorepo with three packages plus a content kit:

```
packages/
├── core/         pure engine — no I/O beyond reading .research/; unit-testable TS
│   ├── types.ts          Kind, Status, Priority, Gap, TaskRecord
│   ├── paths.ts          researchPaths(repo) — every .research/ path
│   ├── task-store.ts     create/read/write/list tasks, setStatus, slugify
│   ├── lifecycle.ts      FSM: TRANSITIONS, canTransition, assertTransition, nextStatuses
│   ├── graph.ts          buildGraph — blocked/dependents from depends_on
│   ├── research-state.ts computeResearchState (§16.1 recommender)
│   ├── workflow.ts       extractWorkflowState — parse workflow.md markers
│   ├── artifacts.ts      prd Goal + execute/verify.jsonl context IO
│   ├── verify.ts         numberTraceability, citationCompliance (§16.2)
│   ├── active.ts         get/set the active-task pointer
│   ├── context.ts        buildContext — assemble the injection block
│   └── index.ts          public barrel (re-exports all of the above)
│
├── cli/          the `rc` command — thin Commander layer over core + adapters
│   ├── program.ts        buildProgram(): wires context/doctor/init/task
│   └── commands/         context.ts, doctor.ts, init.ts, task.ts
│
└── adapters/     platform registry + per-platform configurators
    ├── registry.ts       AI_TOOLS: one ToolEntry per platform
    ├── render.ts         deepMergeJson, render(tpl,vars), kitRoot()
    ├── configurators/    claude-code.ts (Phase 0); others land later
    └── index.ts          public barrel

research-kit/             neutral content (not code): consumed by init/adapters
├── workflow.md           [workflow-state:*] guidance, single source of truth
├── agents/               10 rc-* executor templates (md + frontmatter)
├── config.defaults.yaml  copied to .research/config.yaml
└── spec-templates/       venue/baselines/writing/methodology/novelty seeds
```

Dependency direction is strict and one-way: `cli` and `adapters` depend on `core`; `core` depends on nothing internal. `core` is pure and deterministic, which is what makes the recommender and verify checks unit-testable (spec §10.1).

`research-kit/` is **content, not code**. Both `rc init` and the adapters locate it at runtime via `kitRoot(__dirname)`, which walks up from the package's `dist/` until it finds the `research-kit/` directory.

## Two-layer state model (spec §4.1, decision D5)

Each task carries two orthogonal axes:

1. **Generic lifecycle status** — a small FSM shared by all tasks:

   ```
   planning -> in_progress -> verify -> completed
                                 │
                                 └── verify -> in_progress  (rollback on gate failure)
   ```

   `completed` is terminal. This lives in `lifecycle.ts` as `TRANSITIONS`; illegal moves throw via `assertTransition`.

2. **Research activity `kind`** — what the task *is*, one of seven: `literature`, `ideation`, `experiment`, `writing`, `polish`, `review`, `rebuttal`. The `kind` selects the executor agent (`rc-<kind>`) and the verify gate behaviour (e.g. `writing` -> number traceability).

This crossing (generic lifecycle × research kind × a flexible task graph via `parent`/`depends_on`) is decision **D5** — *not* a fixed pipeline and *not* generic templates. Tasks form a graph; a task is `blocked` when any of its `depends_on` is not yet `completed`.

## Injection-driven steering — no conductor (spec §4, §6.2, decision D6)

There is **no conductor agent**. Steering is data, not an LLM in a loop:

- The single source of truth for "what to do in this lifecycle phase" is `.research/workflow.md`, parsed by `extractWorkflowState`.
- The "what's worth doing next" recommendation is computed deterministically by `computeResearchState` from the task graph (priority, unblocking potential, lifecycle bonus, age).
- `buildContext` assembles both into one block: `[workflow-state:<state>]` + `[research-state]`.
- A platform hook calls `rc context` each turn and injects that block. The agent (and you) read it; **nothing is auto-created** — recommendations are advisory.

```
turn -> hook -> rc context -> buildContext(repo)
                                 ├─ extractWorkflowState(workflow.md, status)   → [workflow-state:*]
                                 └─ computeResearchState(tasks, now, activeId)   → [research-state]
        injected as additionalContext
```

Quality is enforced at the **verify gate** (a state transition), not by intercepting tools (decision D8). A failing gate rolls the task back to `in_progress`. This replaces the old plugin's hard-reject guard hooks with deterministic, testable `core` checks.

## Platform model — class-1 vs class-2 (spec §6.1)

Per-turn injection is not universally supported, which drives the adapter strategy:

- **Class-1 (push / hook):** the platform can inject computed context every turn via a hook. Claude Code (`UserPromptSubmit`), Codex (`UserPromptSubmit`, version-gated), OpenCode (in-process `chat.system.transform` plugin), Gemini (`BeforeAgent`). The configurator wires the hook; `rc context` produces the block.
- **Class-2 (pull / breadcrumb):** the platform cannot push per turn. Context is injected once at session start, and an always-on rule forces the agent to re-echo an `Active task: <path>` breadcrumb each turn and re-resolve state via `rc task current`. Cursor and Windsurf are class-2 (Windsurf is additionally agent-less, so executors degrade to inline workflow/rules).

All platforms normalize onto one source of truth: `rc context --platform <X>`. A platform's adapter is just "call `rc context` at the right event and use its output as additional context." Adding a platform is one registry entry plus a configurator — see [adding-a-platform.md](adding-a-platform.md).

Phase 0 ships Claude Code only. The other five v1 platforms (Codex/OpenCode/Gemini/Cursor/Windsurf) are designed in the registry and land in Phase 1–2; the remaining eight (Kiro/Qoder/CodeBuddy/Droid/Pi/Copilot/Kilo/Antigravity) are milestone 2.

## Where to go next

- Public `core` API with signatures and examples: [core-api.md](core-api.md).
- Onboarding a new platform: [adding-a-platform.md](adding-a-platform.md).
- Tests (vitest, e2e, fixtures): [testing.md](testing.md).
- The decision record (D1–D8): [adr/0001-trellis-emulation.md](adr/0001-trellis-emulation.md).
