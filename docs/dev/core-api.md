# `core` API reference

The public surface of `@research-copilot/core`, re-exported from `packages/core/src/index.ts`. `core` is a pure, deterministic engine — no network, no global state — which is what makes it directly unit-testable.

```ts
import {
  computeResearchState, buildContext,
  createTask, readTask, writeTask, listTasks, setStatus,
  numberTraceability, citationCompliance,
  canTransition, assertTransition, nextStatuses,
  researchPaths,
} from "@research-copilot/core";
```

All functions that touch disk take a `repo` (the directory holding `.research/`) as their first argument and resolve paths via `researchPaths(repo)`.

## Types (`types.ts`)

```ts
type Kind = "literature" | "ideation" | "experiment" | "writing" | "polish" | "review" | "rebuttal";
type Status = "planning" | "in_progress" | "verify" | "completed";
type Priority = "P0" | "P1" | "P2" | "P3";

interface Gap { desc: string; suggest_kind: Kind; status: "open" | "resolved"; }

interface TaskRecord {
  id: string;            // YYYY-MM-DD-slug
  title: string;
  kind: Kind;
  status: Status;
  priority: Priority;
  venue?: string;
  parent?: string;
  children: string[];
  depends_on: string[];
  gaps: Gap[];
  branch?: string;
  created: string;       // ISO 8601
  updated: string;       // ISO 8601
}

function isKind(x: string): x is Kind;
```

`KINDS` and `STATUSES` are exported as `readonly` tuples for iteration/validation.

## research-state recommender (`research-state.ts`, spec §16.1)

```ts
function computeResearchState(tasks: TaskRecord[], now: string, activeId?: string): ResearchState;
```

Pure function: builds the task graph, counts lifecycle states, collects open gaps, and emits up to **3** ranked recommendations.

- `action: "resume"` candidates = tasks that are not `completed` and not `blocked`.
- `action: "create"` candidates = one per open gap (tagged with the gap's `suggest_kind`).
- Score = `3·priorityRank + 2·unblockingPotential + 1·lifecycleBonus + 0.001·ageDays`. Ties break alphabetically by `taskId`/`sourceGap`. (`create` and `resume` share one score scale, so a high-value gap can outrank a resume.)

```ts
const rs = computeResearchState(listTasks(repo), new Date().toISOString(), "2026-06-05-exp");
// rs.recommendations[0]?.reason -> "resume experiment task 2026-06-05-exp (in_progress)"
```

`ResearchState` shape: `{ active, graph: {completed,in_progress,blocked,planning}, openGaps[], recommendations[], turnTs }`.

## Context builder (`context.ts`)

```ts
function buildContext(repo: string, opts: { format: "text" | "json"; now: string }): string;
```

Reads the active task + all tasks, computes research-state, pulls the matching `[workflow-state:*]` block from `.research/workflow.md`, and returns the combined injection block. `format: "json"` wraps it as `{ hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext } }`. Degrades gracefully to `Refer to workflow.md for current step.` if the state marker is missing.

```ts
const block = buildContext(repo, { format: "text", now: new Date().toISOString() });
// "[workflow-state:in_progress]\n...\n[/workflow-state]\n\n[research-state]\n..."
```

`renderResearchState(rs: ResearchState): string` is also exported (the `[research-state]` half on its own).

## Task store (`task-store.ts`)

```ts
function createTask(repo: string, input: CreateInput): TaskRecord;   // status="planning", priority default "P2"
function readTask(repo: string, id: string): TaskRecord;
function writeTask(repo: string, task: TaskRecord, now?: string): void;  // bumps updated; mkdirs research/ + artifacts/
function listTasks(repo: string): TaskRecord[];                       // all tasks with a task.json
function setStatus(repo: string, id: string, to: Status, now: string): void;  // asserts a legal FSM transition
function slugify(title: string): string;
function taskJsonPath(repo: string, id: string): string;

interface CreateInput {
  title: string; kind: Kind; date: string;
  priority?: Priority; venue?: string; parent?: string; now?: string;
}
```

```ts
const t = createTask(repo, { title: "Ablate heads", kind: "experiment", date: "2026-06-05" });
setStatus(repo, t.id, "in_progress", new Date().toISOString());
```

## Verify checks (`verify.ts`, spec §16.2)

```ts
function numberTraceability(draft: string, artifactsText: string): CheckResult;
function citationCompliance(tex: string, bibtex: string): CheckResult;
interface CheckResult { ok: boolean; missing: string[]; }
```

- `numberTraceability` — every number in `draft` must appear in `artifactsText` (leading zeros normalized). `missing` lists untraceable tokens.
- `citationCompliance` — every `\cite*{key}` in `tex` must have a matching `@type{key` entry in `bibtex`. `missing` lists unresolved keys.

```ts
numberTraceability("acc 92.5 over 88.0", "final_acc=92.5\nbaseline=88.0");  // { ok: true, missing: [] }
citationCompliance("see \\cite{vaswani}", "@article{vaswani, ...}");        // { ok: true, missing: [] }
```

## Lifecycle FSM (`lifecycle.ts`)

```ts
const TRANSITIONS: Record<Status, Status[]>;  // planning->[in_progress], in_progress->[verify], verify->[in_progress,completed], completed->[]
function nextStatuses(from: Status): Status[];
function canTransition(from: Status, to: Status): boolean;
function assertTransition(from: Status, to: Status): void;  // throws on illegal move
```

```ts
canTransition("verify", "completed");   // true
nextStatuses("verify");                 // ["in_progress", "completed"]
assertTransition("planning", "completed"); // throws: illegal transition: planning -> completed (allowed: in_progress)
```

## Graph (`graph.ts`)

```ts
function buildGraph(tasks: TaskRecord[]): Map<string, GraphNode>;
interface GraphNode { task: TaskRecord; blocked: boolean; dependents: string[]; }
```

A task is `blocked` if any `depends_on` target is not `completed`; `dependents` is the inverse edge.

```ts
const g = buildGraph(listTasks(repo));
g.get("2026-06-05-exp")?.blocked;       // boolean
```

## Active pointer (`active.ts`)

```ts
function setActive(repo: string, id: string): void;   // writes .research/.runtime/active-task
function getActive(repo: string): string | null;
```

## Artifacts / context IO (`artifacts.ts`)

```ts
function readPrdGoal(repo: string, id: string): string | null;   // the "## Goal" section of prd.md
function appendContext(repo: string, id: string, phase: "execute" | "verify", row: ContextRef | VerifyRow): void;
function readContext(repo: string, id: string, phase: "execute" | "verify"): unknown[];
interface ContextRef { type: "spec" | "context"; path: string; reason: string; }
interface VerifyRow  { check: string; kind: string; args?: Record<string, unknown>; }
```

Curates the per-task `execute.jsonl` / `verify.jsonl` injection manifests.

## Workflow parser (`workflow.ts`)

```ts
function extractWorkflowState(md: string, state: Status | "no_task"): string | null;
```

Returns the text between `[workflow-state:<state>]` and `[/workflow-state]` in `workflow.md`, or `null` if absent.

## Paths (`paths.ts`)

```ts
function researchPaths(repoRoot: string): ResearchPaths;
interface ResearchPaths {
  root; tasks; spec; workspace; runtime;
  workflow; config; activeTask; graphIndex;
  taskDir(id: string): string;
}
```

The single source of every `.research/` path. All other modules resolve paths through it (e.g. `researchPaths(repo).workflow` -> `<repo>/.research/workflow.md`).

```ts
researchPaths(repo).taskDir("2026-06-05-exp"); // <repo>/.research/tasks/2026-06-05-exp
```
