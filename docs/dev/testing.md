# Testing

Research Copilot is tested with [vitest](https://vitest.dev/). The Phase 0 suite is **48 tests, all green**. Because `core` is a pure engine, most coverage is fast unit tests, complemented by configurator golden snapshots and an end-to-end CLI loop.

## Running the tests

From the repo root:

```bash
pnpm vitest run      # one-shot run of the whole suite
pnpm test            # alias for `vitest run` (see root package.json scripts)
pnpm test:watch      # watch mode (alias for `vitest`)
```

`vitest.config.ts` includes `packages/*/test/**/*.test.ts`, so all three packages run together. Expected tail of a clean run:

```
Test Files  ... passed
     Tests  48 passed (48)
```

If the suite can't resolve `@research-copilot/core` (it is consumed by `cli` and `adapters`), build first: `pnpm install && pnpm -r build`.

## Where tests live

Tests sit in `packages/<pkg>/test/`, one file per module:

```
packages/core/test/        active, artifacts, context, graph, lifecycle, paths,
                           research-state, task-store, types, verify, workflow
packages/cli/test/         context, e2e, init, task, verify-gate
packages/adapters/test/    claude-code, templates
```

## The patterns

### Pure-engine unit tests (`core`)

Most `core` tests need no filesystem — they call the function with in-memory data and assert the result. The research-state tests use a small task factory:

```ts
const mk = (over: Partial<TaskRecord>): TaskRecord => ({
  id: "x", title: "x", kind: "writing", status: "planning", priority: "P2",
  children: [], depends_on: [], gaps: [], created: "2026-06-01T00:00:00Z",
  updated: "2026-06-01T00:00:00Z", ...over,
});
const NOW = "2026-06-05T00:00:00Z";
```

Filesystem-touching `core` tests (`task-store`, `active`, `artifacts`, `paths`) create a temp repo with `fs.mkdtempSync(path.join(os.tmpdir(), "rc-"))` and operate on that.

### End-to-end CLI loop (`packages/cli/test/e2e.test.ts`)

The e2e test exercises the real init -> create -> start -> context loop against a fresh temp repo and asserts the injected block:

```ts
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

it("init -> create -> start -> context shows in_progress + recommendation", () => {
  runInit({ repo, platforms: ["claude-code"], user: "t" });
  const t = taskCreate(repo, { title: "Main exp", kind: "experiment", date: "2026-06-05" });
  taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
  const ctx = runContext({ repo, format: "text", now: "2026-06-05T02:00:00Z" });
  expect(ctx).toContain("[workflow-state:in_progress]");
  expect(ctx).toContain("[research-state]");
  expect(ctx).toContain(t.id);
});
```

It imports the command functions directly (`runInit`, `taskCreate`, `taskSetStatus`, `runContext`) rather than spawning a process, which keeps it fast and lets it pass a fixed `now` for deterministic timestamps.

### Verify-gate test (`packages/cli/test/verify-gate.test.ts`)

Covers the writing gate end to end: writes a `.tex` draft plus evidence artifacts into a temp task's `artifacts/`, runs the gate, and asserts pass; then introduces an untraceable number and asserts the gate fails **and rolls the task back to `in_progress`**.

### Configurator golden snapshots (`packages/adapters/test/`)

`claude-code.test.ts` runs `configureClaudeCode(repo)` against a temp repo and asserts the generated `.claude/settings.json` hook, the copied agents, and the `CLAUDE.md` note — including that a re-run is idempotent. `templates.test.ts` checks the neutral `research-kit/` templates render as expected. This is the pattern every new platform follows (see [adding-a-platform.md](adding-a-platform.md#step-4--golden-snapshot-test)).

## Adding a research-state fixture

The recommender is the most ranking-sensitive part of `core`, so its tests are effectively fixtures: each builds a small task set with the `mk` factory, calls `computeResearchState(tasks, NOW, activeId?)`, and asserts the recommendation order or graph counts. To add one:

1. Open `packages/core/test/research-state.test.ts`.
2. Add an `it(...)` describing the scenario in plain words (e.g. "gaps that unblock more downstream tasks score higher").
3. Construct the inputs with `mk({...})`, varying only the fields under test (`priority`, `status`, `depends_on`, `gaps`). Keep timestamps relative to `NOW` if age matters.
4. Assert against `rs.recommendations` (order, `action`, `taskId`/`sourceGap`, `suggestKind`) and/or `rs.graph` counts. When score arithmetic is the point, add a comment showing the calculation (the existing tests do — e.g. `create from hi's gap: 3*3 + 2*1 + 1*2 = 13`).
5. `pnpm vitest run` and confirm the new test plus the existing 48 stay green.

Because `computeResearchState` is pure and takes an explicit `now`, fixtures are fully deterministic — no mocking, no clock, no I/O.
