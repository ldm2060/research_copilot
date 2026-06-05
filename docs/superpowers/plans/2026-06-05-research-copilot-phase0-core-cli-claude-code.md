# Research Copilot Phase 0 — core + cli + Claude Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic `@research-copilot/core` engine, the `rc` CLI, and the Claude Code adapter so a user can run the full research loop (create task → execute → verify → complete → get next-step recommendation) on Claude Code, with the recommendation engine and verify gate fully unit-tested.

**Architecture:** TypeScript pnpm monorepo. `core` is a pure, side-effect-light library (task model, lifecycle FSM, deterministic research-state recommendation §16.1, verify checks §16.2, workflow.md parser, context builder). `cli` wraps core as the `rc` command. `adapters` renders platform-neutral templates into Claude Code config; the per-turn `[workflow-state]`+`[research-state]` block is produced by `rc context` and injected via a Claude Code `UserPromptSubmit` hook. No conductor agent — steering is injection-driven (spec D6).

**Tech Stack:** TypeScript (ESM), pnpm workspaces, tsup (build), vitest (test), commander (CLI), yaml, zod (schema validation). Node ≥ 20.

**Spec:** `docs/superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md` (commit a1bc561). Section refs below (e.g. §16.1) point there.

**Phase 0 scope (from spec §14):** core + cli + **Claude Code only**. MCP servers (Phase 3), other 5 platforms (Phase 1–2), skillpacks fetch (Phase 4) are OUT of Phase 0. The 28 self-skills and 10 agent templates are authored as platform-neutral markdown here only to the extent the Claude Code loop needs them; their cross-platform rendering is later phases.

**Phase 0 acceptance (must all pass):**
1. `core` unit tests green, incl. research-state heuristic over a fixture set of graph shapes (§16.1) and the deterministic verify checks (§16.2).
2. e2e: in a temp dir, `rc init --claude -u tester` scaffolds `.research/` + `.claude/`; `rc task create/start/verify/complete` walks the FSM; `rc context` emits the two injection blocks and a next-step recommendation.
3. Seeded number-fabrication: a `writing` task whose draft cites a number absent from artifacts fails `rc task verify` and rolls back to `in_progress`.
4. Claude Code adapter output matches golden snapshots; the generated `UserPromptSubmit` hook command resolves to `rc context`.
5. Docs shipped: root README (Phase 0 state), `docs/usage/` (rc commands + Claude Code setup + loop walkthrough), `docs/dev/` (architecture, core API, how-to-add-adapter, tests, ADR-0001).

**Conventions:** TDD — write the failing test, see it fail, implement minimally, see it pass, commit. One logical change per commit. All paths relative to repo root `C:\PythonProject\research_copilot`.

---

## File Structure (created in Phase 0)

```
package.json                      # workspace root (pnpm)
pnpm-workspace.yaml
tsconfig.base.json
vitest.config.ts
packages/
  core/
    package.json
    tsconfig.json
    src/
      types.ts                    # TaskRecord, Kind, Status, Priority, Gap, ResearchState…
      paths.ts                    # .research/ path resolution
      task-store.ts               # read/write task.json, list tasks, id/slug
      lifecycle.ts                # FSM: transitions + canTransition + assertTransition
      graph.ts                    # build graph, blocked detection, graph-index cache
      research-state.ts           # computeResearchState (§16.1)
      workflow.ts                 # parse [workflow-state:STATE] blocks (§16.3)
      context.ts                  # buildContext → text|json (§16.6)
      artifacts.ts                # prd.md / execute.jsonl / verify.jsonl IO (§16.3)
      verify.ts                   # deterministic verify checks (§16.2)
      journal.ts                  # workspace/ append + rotate
      config.ts                   # config.yaml load + merge defaults (§16.3)
      index.ts                    # public API barrel
    test/                         # vitest specs mirror src/
  cli/
    package.json
    tsconfig.json
    bin/rc.ts                     # #! entry → commander program
    src/
      program.ts                  # commander wiring
      commands/{init,task,context,doctor}.ts
    test/
  adapters/
    package.json
    tsconfig.json
    src/
      registry.ts                 # AI_TOOLS registry (§6.3)
      render.ts                   # template placeholder rendering
      configurators/claude-code.ts
    test/
research-kit/
  config.defaults.yaml
  workflow.md                     # [workflow-state:*] blocks (§4.2 / §16.3)
  agents/                         # rc-* neutral agent templates (markdown)
  spec-templates/                 # venue/ writing/ baselines/ methodology/ novelty/
docs/
  usage/{README.md,commands.md,claude-code.md,workflow-walkthrough.md}
  dev/{architecture.md,core-api.md,adding-a-platform.md,testing.md,adr/0001-trellis-emulation.md}
README.md
.gitignore                       # add .research/.runtime/, node_modules, dist
```

---

## Task 0: Monorepo scaffolding

**Files:**
- Create: `package.json`, `pnpm-workspace.yaml`, `tsconfig.base.json`, `vitest.config.ts`, `.gitignore`
- Create: `packages/core/package.json`, `packages/core/tsconfig.json`

- [ ] **Step 1: Create the workspace root files**

`package.json`:
```json
{
  "name": "research-copilot-monorepo",
  "private": true,
  "engines": { "node": ">=20" },
  "scripts": {
    "build": "pnpm -r build",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "tsup": "^8.3.0",
    "vitest": "^2.1.0",
    "@types/node": "^22.0.0"
  },
  "packageManager": "pnpm@9.12.0"
}
```

`pnpm-workspace.yaml`:
```yaml
packages:
  - "packages/*"
```

`tsconfig.base.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "declaration": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

`vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
export default defineConfig({ test: { include: ["packages/*/test/**/*.test.ts"] } });
```

`.gitignore`:
```
node_modules/
dist/
.research/.runtime/
*.tsbuildinfo
```

- [ ] **Step 2: Create the core package manifest**

`packages/core/package.json`:
```json
{
  "name": "@research-copilot/core",
  "version": "0.0.0",
  "type": "module",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": { ".": { "import": "./dist/index.js", "types": "./dist/index.d.ts" } },
  "scripts": { "build": "tsup src/index.ts --format esm --dts" },
  "dependencies": { "yaml": "^2.6.0", "zod": "^3.23.0" }
}
```

`packages/core/tsconfig.json`:
```json
{ "extends": "../../tsconfig.base.json", "compilerOptions": { "outDir": "dist", "rootDir": "src" }, "include": ["src"] }
```

- [ ] **Step 3: Install and verify the toolchain**

Run: `pnpm install`
Expected: lockfile created, no errors.

Run: `pnpm vitest run`
Expected: "No test files found" (exit 0 or the "no tests" notice) — confirms vitest resolves.

- [ ] **Step 4: Commit**

```bash
git add package.json pnpm-workspace.yaml tsconfig.base.json vitest.config.ts .gitignore packages/core/package.json packages/core/tsconfig.json pnpm-lock.yaml
git commit -m "chore: scaffold pnpm monorepo + core package"
```

---

## Task 1: Core types

**Files:**
- Create: `packages/core/src/types.ts`
- Test: `packages/core/test/types.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/types.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { KINDS, STATUSES, isKind } from "../src/types.js";

describe("types", () => {
  it("exposes the 7 research kinds", () => {
    expect(KINDS).toEqual([
      "literature","ideation","experiment","writing","polish","review","rebuttal"
    ]);
  });
  it("exposes the lifecycle statuses in order", () => {
    expect(STATUSES).toEqual(["planning","in_progress","verify","completed"]);
  });
  it("isKind narrows valid kinds", () => {
    expect(isKind("writing")).toBe(true);
    expect(isKind("nope")).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/types.test.ts`
Expected: FAIL — cannot find module `../src/types.js`.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/types.ts`:
```ts
export const KINDS = [
  "literature","ideation","experiment","writing","polish","review","rebuttal"
] as const;
export type Kind = (typeof KINDS)[number];

export const STATUSES = ["planning","in_progress","verify","completed"] as const;
export type Status = (typeof STATUSES)[number];

export type Priority = "P0" | "P1" | "P2" | "P3";

export interface Gap {
  desc: string;
  suggest_kind: Kind;
  status: "open" | "resolved";
}

export interface TaskRecord {
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

export function isKind(x: string): x is Kind {
  return (KINDS as readonly string[]).includes(x);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/types.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/types.ts packages/core/test/types.test.ts
git commit -m "feat(core): task model types"
```

---

## Task 2: Path resolution

**Files:**
- Create: `packages/core/src/paths.ts`
- Test: `packages/core/test/paths.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/paths.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { researchPaths } from "../src/paths.js";

describe("researchPaths", () => {
  it("derives all .research subpaths from a root", () => {
    const p = researchPaths("/repo");
    expect(p.root).toBe("/repo/.research");
    expect(p.tasks).toBe("/repo/.research/tasks");
    expect(p.spec).toBe("/repo/.research/spec");
    expect(p.workspace).toBe("/repo/.research/workspace");
    expect(p.runtime).toBe("/repo/.research/.runtime");
    expect(p.workflow).toBe("/repo/.research/workflow.md");
    expect(p.config).toBe("/repo/.research/config.yaml");
    expect(p.activeTask).toBe("/repo/.research/.runtime/active-task");
    expect(p.graphIndex).toBe("/repo/.research/.runtime/graph-index.json");
    expect(p.taskDir("2026-06-05-x")).toBe("/repo/.research/tasks/2026-06-05-x");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/paths.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/paths.ts`:
```ts
import * as path from "node:path";

export interface ResearchPaths {
  root: string; tasks: string; spec: string; workspace: string; runtime: string;
  workflow: string; config: string; activeTask: string; graphIndex: string;
  taskDir(id: string): string;
}

export function researchPaths(repoRoot: string): ResearchPaths {
  const root = path.join(repoRoot, ".research");
  const runtime = path.join(root, ".runtime");
  return {
    root,
    tasks: path.join(root, "tasks"),
    spec: path.join(root, "spec"),
    workspace: path.join(root, "workspace"),
    runtime,
    workflow: path.join(root, "workflow.md"),
    config: path.join(root, "config.yaml"),
    activeTask: path.join(runtime, "active-task"),
    graphIndex: path.join(runtime, "graph-index.json"),
    taskDir: (id: string) => path.join(root, "tasks", id),
  };
}
```

> Note: tests use POSIX separators; `path.join` on Windows yields `\`. Run assertions through a normalizer. Update the test Step 1 to wrap expected/received with `.replaceAll("\\\\","/")` if running on Windows, OR set the test to compare `p.root.replaceAll(path.sep, "/")`. Implementer: add a tiny `const n = (s:string)=>s.replaceAll(path.sep,"/")` in the test and wrap both sides.

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/paths.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/paths.ts packages/core/test/paths.test.ts
git commit -m "feat(core): .research path resolution"
```

---

## Task 3: Task store (read/write/list task.json)

**Files:**
- Create: `packages/core/src/task-store.ts`
- Test: `packages/core/test/task-store.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/task-store.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { createTask, readTask, writeTask, listTasks } from "../src/task-store.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("task-store", () => {
  it("creates a task with id=date-slug and defaults, persists task.json", () => {
    const t = createTask(repo, { title: "Draft Method", kind: "writing", date: "2026-06-05" });
    expect(t.id).toBe("2026-06-05-draft-method");
    expect(t.status).toBe("planning");
    expect(t.priority).toBe("P2");
    expect(t.children).toEqual([]);
    expect(t.gaps).toEqual([]);
    const onDisk = readTask(repo, t.id);
    expect(onDisk.title).toBe("Draft Method");
  });

  it("lists all tasks", () => {
    createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    createTask(repo, { title: "B", kind: "experiment", date: "2026-06-05" });
    const ids = listTasks(repo).map(t => t.id).sort();
    expect(ids).toEqual(["2026-06-05-a", "2026-06-05-b"]);
  });

  it("writeTask updates the updated timestamp", () => {
    const t = createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    const before = t.updated;
    t.title = "A2";
    writeTask(repo, t, "2026-06-06T00:00:00Z");
    expect(readTask(repo, t.id).title).toBe("A2");
    expect(readTask(repo, t.id).updated).toBe("2026-06-06T00:00:00Z");
    expect(readTask(repo, t.id).updated).not.toBe(before);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/task-store.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/task-store.ts`:
```ts
import * as fs from "node:fs";
import * as path from "node:path";
import { researchPaths } from "./paths.js";
import type { TaskRecord, Kind, Priority } from "./types.js";

export function slugify(title: string): string {
  return title.toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
}

export interface CreateInput {
  title: string; kind: Kind; date: string;
  priority?: Priority; venue?: string; parent?: string; now?: string;
}

export function createTask(repo: string, input: CreateInput): TaskRecord {
  const id = `${input.date}-${slugify(input.title)}`;
  const now = input.now ?? input.date + "T00:00:00Z";
  const task: TaskRecord = {
    id, title: input.title, kind: input.kind, status: "planning",
    priority: input.priority ?? "P2", venue: input.venue, parent: input.parent,
    children: [], depends_on: [], gaps: [], created: now, updated: now,
  };
  writeTask(repo, task, now);
  return task;
}

export function taskJsonPath(repo: string, id: string): string {
  return path.join(researchPaths(repo).taskDir(id), "task.json");
}

export function writeTask(repo: string, task: TaskRecord, now?: string): void {
  if (now) task.updated = now;
  const dir = researchPaths(repo).taskDir(task.id);
  fs.mkdirSync(path.join(dir, "research"), { recursive: true });
  fs.mkdirSync(path.join(dir, "artifacts"), { recursive: true });
  fs.writeFileSync(taskJsonPath(repo, task.id), JSON.stringify(task, null, 2) + "\n", "utf8");
}

export function readTask(repo: string, id: string): TaskRecord {
  return JSON.parse(fs.readFileSync(taskJsonPath(repo, id), "utf8")) as TaskRecord;
}

export function listTasks(repo: string): TaskRecord[] {
  const dir = researchPaths(repo).tasks;
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(id => fs.existsSync(taskJsonPath(repo, id)))
    .map(id => readTask(repo, id));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/task-store.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/task-store.ts packages/core/test/task-store.test.ts
git commit -m "feat(core): task store (create/read/write/list task.json)"
```

---

## Task 4: Lifecycle FSM

**Files:**
- Create: `packages/core/src/lifecycle.ts`
- Test: `packages/core/test/lifecycle.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/lifecycle.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { canTransition, assertTransition, nextStatuses } from "../src/lifecycle.js";

describe("lifecycle FSM", () => {
  it("allows the forward path", () => {
    expect(canTransition("planning", "in_progress")).toBe(true);
    expect(canTransition("in_progress", "verify")).toBe(true);
    expect(canTransition("verify", "completed")).toBe(true);
  });
  it("allows verify->in_progress rollback", () => {
    expect(canTransition("verify", "in_progress")).toBe(true);
  });
  it("rejects illegal jumps", () => {
    expect(canTransition("planning", "completed")).toBe(false);
    expect(canTransition("completed", "in_progress")).toBe(false);
  });
  it("assertTransition throws on illegal", () => {
    expect(() => assertTransition("planning", "completed")).toThrow(/illegal transition/i);
  });
  it("nextStatuses lists legal successors", () => {
    expect(nextStatuses("verify").sort()).toEqual(["completed", "in_progress"]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/lifecycle.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/lifecycle.ts`:
```ts
import type { Status } from "./types.js";

export const TRANSITIONS: Record<Status, Status[]> = {
  planning: ["in_progress"],
  in_progress: ["verify"],
  verify: ["in_progress", "completed"],
  completed: [],
};

export function nextStatuses(from: Status): Status[] {
  return TRANSITIONS[from];
}
export function canTransition(from: Status, to: Status): boolean {
  return TRANSITIONS[from].includes(to);
}
export function assertTransition(from: Status, to: Status): void {
  if (!canTransition(from, to)) {
    throw new Error(`illegal transition: ${from} -> ${to} (allowed: ${TRANSITIONS[from].join(", ") || "none"})`);
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/lifecycle.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/lifecycle.ts packages/core/test/lifecycle.test.ts
git commit -m "feat(core): lifecycle FSM with transition validation"
```

---

## Task 5: Graph build + blocked detection

**Files:**
- Create: `packages/core/src/graph.ts`
- Test: `packages/core/test/graph.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/graph.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { buildGraph } from "../src/graph.js";
import type { TaskRecord } from "../src/types.js";

const mk = (over: Partial<TaskRecord>): TaskRecord => ({
  id: "x", title: "x", kind: "writing", status: "planning", priority: "P2",
  children: [], depends_on: [], gaps: [], created: "", updated: "", ...over,
});

describe("buildGraph", () => {
  it("marks a task blocked when a dependency is not completed", () => {
    const tasks = [
      mk({ id: "a", status: "in_progress" }),
      mk({ id: "b", depends_on: ["a"] }),
    ];
    const g = buildGraph(tasks);
    expect(g.get("b")!.blocked).toBe(true);
    expect(g.get("a")!.blocked).toBe(false);
  });
  it("unblocks when the dependency is completed", () => {
    const tasks = [
      mk({ id: "a", status: "completed" }),
      mk({ id: "b", depends_on: ["a"] }),
    ];
    expect(buildGraph(tasks).get("b")!.blocked).toBe(false);
  });
  it("counts downstream dependents (unblocking potential)", () => {
    const tasks = [
      mk({ id: "a" }), mk({ id: "b", depends_on: ["a"] }), mk({ id: "c", depends_on: ["a"] }),
    ];
    expect(buildGraph(tasks).get("a")!.dependents).toEqual(["b", "c"]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/graph.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/graph.ts`:
```ts
import type { TaskRecord } from "./types.js";

export interface GraphNode {
  task: TaskRecord;
  blocked: boolean;
  dependents: string[]; // ids that depend_on this task
}
export type Graph = Map<string, GraphNode>;

export function buildGraph(tasks: TaskRecord[]): Graph {
  const byId = new Map(tasks.map(t => [t.id, t]));
  const g: Graph = new Map();
  for (const t of tasks) {
    const blocked = t.depends_on.some(d => byId.get(d)?.status !== "completed");
    g.set(t.id, { task: t, blocked, dependents: [] });
  }
  for (const t of tasks) {
    for (const d of t.depends_on) {
      g.get(d)?.dependents.push(t.id);
    }
  }
  return g;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/graph.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/graph.ts packages/core/test/graph.test.ts
git commit -m "feat(core): task graph + blocked/dependents computation"
```

---

## Task 6: research-state recommendation engine (§16.1)

**Files:**
- Create: `packages/core/src/research-state.ts`
- Test: `packages/core/test/research-state.test.ts`

This is the centerpiece (spec §16.1). It is a pure function of the task list + a fixed clock.

- [ ] **Step 1: Write the failing test**

`packages/core/test/research-state.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { computeResearchState } from "../src/research-state.js";
import type { TaskRecord } from "../src/types.js";

const mk = (over: Partial<TaskRecord>): TaskRecord => ({
  id: "x", title: "x", kind: "writing", status: "planning", priority: "P2",
  children: [], depends_on: [], gaps: [], created: "2026-06-01T00:00:00Z",
  updated: "2026-06-01T00:00:00Z", ...over,
});
const NOW = "2026-06-05T00:00:00Z";

describe("computeResearchState (§16.1)", () => {
  it("recommends creating a task for an open gap, tagged with suggest_kind", () => {
    const tasks = [mk({
      id: "2026-06-05-method", kind: "writing", status: "in_progress",
      gaps: [{ desc: "missing ablation X", suggest_kind: "experiment", status: "open" }],
    })];
    const rs = computeResearchState(tasks, NOW);
    const create = rs.recommendations.find(r => r.action === "create");
    expect(create?.suggestKind).toBe("experiment");
    expect(create?.sourceGap).toBe("missing ablation X");
    expect(rs.turnTs).toBe(NOW);
  });

  it("ranks higher-priority resume candidates first", () => {
    const tasks = [
      mk({ id: "low", status: "in_progress", priority: "P3" }),
      mk({ id: "high", status: "in_progress", priority: "P0" }),
    ];
    const rs = computeResearchState(tasks, NOW);
    const resumes = rs.recommendations.filter(r => r.action === "resume").map(r => r.taskId);
    expect(resumes[0]).toBe("high");
  });

  it("does not recommend resuming a blocked task", () => {
    const tasks = [
      mk({ id: "dep", status: "in_progress" }),
      mk({ id: "blocked", status: "in_progress", depends_on: ["dep"] }),
    ];
    const rs = computeResearchState(tasks, NOW);
    expect(rs.recommendations.find(r => r.taskId === "blocked")).toBeUndefined();
    expect(rs.graph.blocked).toBe(1);
  });

  it("gaps that unblock more downstream tasks score higher (tie-break by unblocking potential)", () => {
    const tasks = [
      mk({ id: "g1src", priority: "P2", status: "in_progress",
        gaps: [{ desc: "g1", suggest_kind: "experiment", status: "open" }] }),
      mk({ id: "g2src", priority: "P2", status: "in_progress",
        gaps: [{ desc: "g2", suggest_kind: "experiment", status: "open" }] }),
      // g2src has two dependents -> resolving its gap has higher unblocking potential
      mk({ id: "d1", depends_on: ["g2src"] }),
      mk({ id: "d2", depends_on: ["g2src"] }),
    ];
    const rs = computeResearchState(tasks, NOW);
    const creates = rs.recommendations.filter(r => r.action === "create");
    expect(creates[0].sourceGap).toBe("g2");
  });

  it("handles the empty / all-completed case", () => {
    const rs = computeResearchState([mk({ id: "done", status: "completed" })], NOW);
    expect(rs.recommendations).toEqual([]);
    expect(rs.graph.completed).toBe(1);
  });

  it("emits at most 3 recommendations", () => {
    const tasks = Array.from({ length: 6 }, (_, i) =>
      mk({ id: `t${i}`, status: "in_progress", priority: "P1" }));
    expect(computeResearchState(tasks, NOW).recommendations.length).toBeLessThanOrEqual(3);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/research-state.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/research-state.ts`:
```ts
import type { TaskRecord, Kind, Status } from "./types.js";
import { buildGraph } from "./graph.js";

export interface Recommendation {
  action: "resume" | "create";
  taskId?: string;
  suggestKind?: Kind;
  reason: string;
  sourceGap?: string;
  score: number;
}
export interface ResearchState {
  active: { id: string; kind: Kind; status: Status } | null;
  graph: { completed: number; in_progress: number; blocked: number; planning: number };
  openGaps: { taskId: string; desc: string; suggest_kind: Kind }[];
  recommendations: Recommendation[];
  turnTs: string;
}

const PRIORITY_RANK = { P0: 3, P1: 2, P2: 1, P3: 0 } as const;
const LIFECYCLE_BONUS: Record<Status, number> = { in_progress: 2, verify: 1, planning: 0.5, completed: 0 };
const W = { priority: 3, unblocking: 2, lifecycle: 1, age: 0.001 } as const;
const MAX_RECS = 3;

export function computeResearchState(
  tasks: TaskRecord[], now: string, activeId?: string,
): ResearchState {
  const g = buildGraph(tasks);
  const counts = { completed: 0, in_progress: 0, blocked: 0, planning: 0 };
  for (const n of g.values()) {
    if (n.blocked) counts.blocked++;
    if (n.task.status === "completed") counts.completed++;
    else if (n.task.status === "in_progress") counts.in_progress++;
    else if (n.task.status === "planning") counts.planning++;
  }

  const openGaps = tasks.flatMap(t =>
    t.gaps.filter(gp => gp.status === "open")
      .map(gp => ({ taskId: t.id, desc: gp.desc, suggest_kind: gp.suggest_kind })));

  const ageDays = (iso: string) =>
    Math.max(0, (Date.parse(now) - Date.parse(iso)) / 86_400_000);

  const recs: Recommendation[] = [];

  // (a) resume candidates: not completed, not blocked
  for (const n of g.values()) {
    if (n.task.status === "completed" || n.blocked) continue;
    const score =
      W.priority * PRIORITY_RANK[n.task.priority] +
      W.lifecycle * LIFECYCLE_BONUS[n.task.status] +
      W.age * ageDays(n.task.updated);
    recs.push({ action: "resume", taskId: n.task.id, score,
      reason: `resume ${n.task.kind} task ${n.task.id} (${n.task.status})` });
  }

  // (b) create candidates from open gaps; unblocking potential = #dependents of the gap's source task
  for (const t of tasks) {
    const dependents = g.get(t.id)?.dependents.length ?? 0;
    for (const gp of t.gaps.filter(x => x.status === "open")) {
      const score =
        W.priority * PRIORITY_RANK[t.priority] +
        W.unblocking * dependents +
        W.lifecycle * LIFECYCLE_BONUS[t.status];
      recs.push({ action: "create", suggestKind: gp.suggest_kind, sourceGap: gp.desc, score,
        reason: `create ${gp.suggest_kind} task to resolve "${gp.desc}" (from ${t.id})` });
    }
  }

  recs.sort((x, y) =>
    y.score - x.score ||
    (x.taskId ?? x.sourceGap ?? "").localeCompare(y.taskId ?? y.sourceGap ?? ""));

  const active = activeId
    ? (() => { const n = g.get(activeId); return n ? { id: n.task.id, kind: n.task.kind, status: n.task.status } : null; })()
    : null;

  return { active, graph: counts, openGaps, recommendations: recs.slice(0, MAX_RECS), turnTs: now };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/research-state.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/research-state.ts packages/core/test/research-state.test.ts
git commit -m "feat(core): deterministic research-state recommendation engine (spec 16.1)"
```

---

## Task 7: workflow.md block parser (§16.3)

**Files:**
- Create: `packages/core/src/workflow.ts`
- Test: `packages/core/test/workflow.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/workflow.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { extractWorkflowState } from "../src/workflow.js";

const MD = `# workflow
[workflow-state:planning]
Plan the task.
[/workflow-state]

[workflow-state:in_progress]
Dispatch the rc-{kind} executor.
[/workflow-state]
`;

describe("extractWorkflowState", () => {
  it("extracts the body of a named state block", () => {
    expect(extractWorkflowState(MD, "in_progress")).toBe("Dispatch the rc-{kind} executor.");
  });
  it("returns null for an absent state", () => {
    expect(extractWorkflowState(MD, "completed")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/workflow.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/workflow.ts`:
```ts
import type { Status } from "./types.js";

export function extractWorkflowState(md: string, state: Status | "no_task"): string | null {
  const re = new RegExp(
    `\\[workflow-state:${state}\\]\\r?\\n([\\s\\S]*?)\\r?\\n\\[/workflow-state\\]`,
  );
  const m = md.match(re);
  return m ? m[1].trim() : null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/workflow.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/workflow.ts packages/core/test/workflow.test.ts
git commit -m "feat(core): workflow.md [workflow-state:STATE] parser"
```

---

## Task 8: Artifacts IO — prd.md / execute.jsonl / verify.jsonl (§16.3)

**Files:**
- Create: `packages/core/src/artifacts.ts`
- Test: `packages/core/test/artifacts.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/artifacts.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { createTask } from "../src/task-store.js";
import { readPrdGoal, appendContext, readContext } from "../src/artifacts.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("artifacts IO", () => {
  it("reads prd.goal as the first paragraph under ## Goal", () => {
    const t = createTask(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    const dir = path.join(repo, ".research/tasks", t.id);
    fs.writeFileSync(path.join(dir, "prd.md"),
      "# M\n\n## Goal\nWrite the method.\n\n## Scope\n...");
    expect(readPrdGoal(repo, t.id)).toBe("Write the method.");
  });
  it("appends and reads execute.jsonl context refs", () => {
    const t = createTask(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    appendContext(repo, t.id, "execute", { type: "spec", path: "spec/writing/style.md", reason: "tone" });
    const rows = readContext(repo, t.id, "execute");
    expect(rows).toEqual([{ type: "spec", path: "spec/writing/style.md", reason: "tone" }]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/artifacts.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/artifacts.ts`:
```ts
import * as fs from "node:fs";
import * as path from "node:path";
import { researchPaths } from "./paths.js";

export type Phase = "execute" | "verify";
export interface ContextRef { type: "spec" | "context"; path: string; reason: string; }
export interface VerifyRow { check: string; kind: string; args?: Record<string, unknown>; }

function dir(repo: string, id: string) { return researchPaths(repo).taskDir(id); }

export function readPrdGoal(repo: string, id: string): string | null {
  const p = path.join(dir(repo, id), "prd.md");
  if (!fs.existsSync(p)) return null;
  const md = fs.readFileSync(p, "utf8");
  const m = md.match(/##\s*Goal\s*\r?\n([\s\S]*?)(\r?\n\s*\r?\n|\r?\n##|$)/);
  return m ? m[1].trim() : null;
}

export function appendContext(
  repo: string, id: string, phase: Phase, row: ContextRef | VerifyRow,
): void {
  const p = path.join(dir(repo, id), `${phase}.jsonl`);
  fs.appendFileSync(p, JSON.stringify(row) + "\n", "utf8");
}

export function readContext(repo: string, id: string, phase: Phase): unknown[] {
  const p = path.join(dir(repo, id), `${phase}.jsonl`);
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, "utf8").split("\n").filter(Boolean).map(l => JSON.parse(l));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/artifacts.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/artifacts.ts packages/core/test/artifacts.test.ts
git commit -m "feat(core): prd/execute.jsonl/verify.jsonl artifact IO"
```

---

## Task 9: Deterministic verify checks (§16.2)

**Files:**
- Create: `packages/core/src/verify.ts`
- Test: `packages/core/test/verify.test.ts`

Phase 0 implements the two flagship deterministic checks: `number-traceability` (acceptance criterion 3) and `citation-compliance`. Other [det] checks land with their kinds in later phases.

- [ ] **Step 1: Write the failing test**

`packages/core/test/verify.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { numberTraceability, citationCompliance } from "../src/verify.js";

describe("verify checks (§16.2)", () => {
  it("number-traceability passes when every draft number appears in artifacts text", () => {
    const draft = "We reach 92.5 accuracy with 3 seeds.";
    const artifacts = "final_acc=92.5\nseeds=3\n";
    expect(numberTraceability(draft, artifacts)).toEqual({ ok: true, missing: [] });
  });
  it("number-traceability fails and reports a fabricated number", () => {
    const draft = "We reach 99.9 accuracy.";
    const artifacts = "final_acc=92.5\n";
    expect(numberTraceability(draft, artifacts)).toEqual({ ok: false, missing: ["99.9"] });
  });
  it("citation-compliance fails on a cite key absent from bibtex", () => {
    const tex = "Strong results \\cite{smith2020} and \\cite{ghost2099}.";
    const bib = "@article{smith2020, title={x}}";
    expect(citationCompliance(tex, bib)).toEqual({ ok: false, missing: ["ghost2099"] });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/verify.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/verify.ts`:
```ts
export interface CheckResult { ok: boolean; missing: string[]; }

const NUMBER_RE = /-?\d+(?:\.\d+)?/g;
const norm = (s: string) => s.replace(/^(-?)0+(\d)/, "$1$2"); // strip leading zeros

export function numberTraceability(draft: string, artifactsText: string): CheckResult {
  const present = new Set((artifactsText.match(NUMBER_RE) ?? []).map(norm));
  const missing: string[] = [];
  for (const tok of draft.match(NUMBER_RE) ?? []) {
    if (!present.has(norm(tok)) && !missing.includes(tok)) missing.push(tok);
  }
  return { ok: missing.length === 0, missing };
}

export function citationCompliance(tex: string, bibtex: string): CheckResult {
  const keys = new Set<string>();
  for (const m of bibtex.matchAll(/@\w+\s*\{\s*([^,\s}]+)/g)) keys.add(m[1]);
  const missing: string[] = [];
  for (const m of tex.matchAll(/\\cite[a-zA-Z]*\{([^}]*)\}/g)) {
    for (const key of m[1].split(",").map(k => k.trim()).filter(Boolean)) {
      if (!keys.has(key) && !missing.includes(key)) missing.push(key);
    }
  }
  return { ok: missing.length === 0, missing };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/verify.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/verify.ts packages/core/test/verify.test.ts
git commit -m "feat(core): number-traceability + citation-compliance verify checks (spec 16.2)"
```

---

## Task 10: Active-task pointer + setStatus (FSM-guarded) + graph index

**Files:**
- Create: `packages/core/src/active.ts`
- Modify: `packages/core/src/task-store.ts` (add `setStatus`)
- Test: `packages/core/test/active.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/active.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { createTask, setStatus } from "../src/task-store.js";
import { setActive, getActive } from "../src/active.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("active pointer + setStatus", () => {
  it("set/get the active task id", () => {
    const t = createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    setActive(repo, t.id);
    expect(getActive(repo)).toBe(t.id);
  });
  it("setStatus enforces the FSM", () => {
    const t = createTask(repo, { title: "A", kind: "writing", date: "2026-06-05" });
    setStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    expect(() => setStatus(repo, t.id, "completed", "2026-06-05T02:00:00Z"))
      .toThrow(/illegal transition/i);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/active.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/active.ts`:
```ts
import * as fs from "node:fs";
import { researchPaths } from "./paths.js";

export function setActive(repo: string, id: string): void {
  const p = researchPaths(repo);
  fs.mkdirSync(p.runtime, { recursive: true });
  fs.writeFileSync(p.activeTask, id, "utf8");
}
export function getActive(repo: string): string | null {
  const p = researchPaths(repo).activeTask;
  return fs.existsSync(p) ? fs.readFileSync(p, "utf8").trim() || null : null;
}
```

Append to `packages/core/src/task-store.ts`:
```ts
import { assertTransition } from "./lifecycle.js";
import type { Status } from "./types.js";

export function setStatus(repo: string, id: string, to: Status, now: string): void {
  const t = readTask(repo, id);
  assertTransition(t.status, to);
  t.status = to;
  writeTask(repo, t, now);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/active.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/active.ts packages/core/src/task-store.ts packages/core/test/active.test.ts
git commit -m "feat(core): active-task pointer + FSM-guarded setStatus"
```

---

## Task 11: Context builder (§16.6) + core barrel

**Files:**
- Create: `packages/core/src/context.ts`
- Create: `packages/core/src/index.ts`
- Test: `packages/core/test/context.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/core/test/context.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { createTask, setStatus } from "../src/task-store.js";
import { setActive } from "../src/active.js";
import { buildContext } from "../src/context.js";

let repo: string;
beforeEach(() => {
  repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-"));
  fs.writeFileSync(path.join(repo, ".research", "workflow.md") ,
    "[workflow-state:in_progress]\nDispatch rc-{kind}.\n[/workflow-state]\n");
});

describe("buildContext (§16.6)", () => {
  it("text format embeds both blocks and turn-ts", () => {
    const t = createTask(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    setStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    setActive(repo, t.id);
    const out = buildContext(repo, { format: "text", now: "2026-06-05T02:00:00Z" });
    expect(out).toContain("[workflow-state:in_progress]");
    expect(out).toContain("Dispatch rc-{kind}.");
    expect(out).toContain("[research-state]");
    expect(out).toContain("turn-ts: 2026-06-05T02:00:00Z");
  });
  it("json format returns hookSpecificOutput.additionalContext", () => {
    const out = buildContext(repo, { format: "json", now: "2026-06-05T02:00:00Z" });
    const parsed = JSON.parse(out);
    expect(parsed.hookSpecificOutput.additionalContext).toContain("[research-state]");
  });
});
```

> Note: `createTask` writes under `.research/tasks/...`; ensure the `beforeEach` creates `.research/` before writing workflow.md (mkdir). Implementer: add `fs.mkdirSync(path.join(repo,".research"),{recursive:true})` before the writeFileSync.

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/core/test/context.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/core/src/context.ts`:
```ts
import * as fs from "node:fs";
import { researchPaths } from "./paths.js";
import { listTasks } from "./task-store.js";
import { getActive } from "./active.js";
import { computeResearchState, type ResearchState } from "./research-state.js";
import { extractWorkflowState } from "./workflow.js";

export interface BuildOptions { format: "text" | "json"; now: string; }

export function renderResearchState(rs: ResearchState): string {
  const lines: string[] = ["[research-state]"];
  lines.push(`Active: ${rs.active ? `${rs.active.id} (${rs.active.kind}, ${rs.active.status})` : "none"}`);
  lines.push(`Graph: ${rs.graph.completed} completed · ${rs.graph.in_progress} in_progress · ${rs.graph.blocked} blocked`);
  if (rs.openGaps.length) {
    lines.push("Open gaps:");
    for (const g of rs.openGaps) lines.push(`  - [from ${g.taskId}] ${g.desc} -> suggests: ${g.suggest_kind}`);
  }
  if (rs.recommendations.length) {
    lines.push("Recommended next (you decide, nothing auto-created):");
    rs.recommendations.forEach((r, i) => lines.push(`  ${i + 1}. ${r.reason}`));
  }
  lines.push(`turn-ts: ${rs.turnTs}`);
  return lines.join("\n");
}

export function buildContext(repo: string, opts: BuildOptions): string {
  const tasks = listTasks(repo);
  const active = getActive(repo) ?? undefined;
  const activeStatus = active ? tasks.find(t => t.id === active)?.status : undefined;
  const rs = computeResearchState(tasks, opts.now, active);

  const wfPath = researchPaths(repo).workflow;
  const wfMd = fs.existsSync(wfPath) ? fs.readFileSync(wfPath, "utf8") : "";
  const stateKey = activeStatus ?? "no_task";
  const wfBlock = extractWorkflowState(wfMd, stateKey) ?? "Refer to workflow.md for current step.";

  const text =
    `[workflow-state:${stateKey}]\n${wfBlock}\n[/workflow-state]\n\n${renderResearchState(rs)}`;

  if (opts.format === "json") {
    return JSON.stringify({
      hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: text },
    });
  }
  return text;
}
```

`packages/core/src/index.ts`:
```ts
export * from "./types.js";
export * from "./paths.js";
export * from "./task-store.js";
export * from "./lifecycle.js";
export * from "./graph.js";
export * from "./research-state.js";
export * from "./workflow.js";
export * from "./artifacts.js";
export * from "./verify.js";
export * from "./active.js";
export * from "./context.js";
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/core/test/context.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Build core to confirm the barrel + types compile**

Run: `pnpm --filter @research-copilot/core build`
Expected: emits `packages/core/dist/index.js` + `.d.ts`, no TS errors.

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/context.ts packages/core/src/index.ts packages/core/test/context.test.ts
git commit -m "feat(core): context builder (workflow-state + research-state, text|json) + public barrel"
```

---

## Task 12: research-kit templates (workflow.md, agents, config defaults)

**Files:**
- Create: `research-kit/workflow.md`
- Create: `research-kit/config.defaults.yaml`
- Create: `research-kit/agents/rc-literature.md` … `rc-rebuttal.md` (7), `rc-plan.md`, `rc-verify.md`, `rc-update-spec.md` (10 total)
- Create: `research-kit/spec-templates/{venue,writing,baselines,methodology,novelty}/.gitkeep`
- Test: `packages/adapters/test/templates.test.ts` (presence/shape assertions)

These are platform-neutral content (markdown). Phase 0 needs them so `rc init` can scaffold a working Claude Code setup.

- [ ] **Step 1: Write `research-kit/workflow.md`** (one block per lifecycle state)

```markdown
# Research Copilot Workflow

[workflow-state:no_task]
No active task. Either answer directly, or run `rc task create --kind <k> --title "<t>"` to start one. Consult [research-state] for recommended next activities.
[/workflow-state]

[workflow-state:planning]
Active task is in PLANNING. Use the rc-plan helper to clarify it into prd.md and curate execute.jsonl / verify.jsonl. Then `rc task start <id>`.
[/workflow-state]

[workflow-state:in_progress]
Active task is IN PROGRESS. Dispatch the rc-{kind} executor with prd.md + execute.jsonl specs. Do NOT do domain work inline. When the executor returns, run `rc task verify <id>`.
[/workflow-state]

[workflow-state:verify]
Active task is in VERIFY. Dispatch rc-verify to run the kind's quality gate. On pass: `rc task complete <id>`. On fail: fix and `rc task set-status <id> in_progress`.
[/workflow-state]

[workflow-state:completed]
Active task COMPLETED. Run rc-update-spec to sediment learnings into spec/, append a journal entry, then consult [research-state] for the next activity.
[/workflow-state]
```

- [ ] **Step 2: Write `research-kit/config.defaults.yaml`**

```yaml
session_commit_message: "chore(research): update journal/index"
max_journal_lines: 2000
default_venue: null
lifecycle_hooks:
  after_create: []
  after_start: []
  after_verify: []
  after_complete: []
  after_archive: []
```

- [ ] **Step 3: Write the 10 agent templates** (one file each; same frontmatter shape, body per role). Example `research-kit/agents/rc-writer.md`:

```markdown
---
name: rc-writer
description: Drafts LaTeX paper sections from experiment artifacts. Use for writing tasks. Cite only numbers present in the task artifacts.
kind: writing
model: sonnet
---
You are the writing executor. Read the injected spec refs (execute.jsonl) and prd.md Goal.
Draft into the task's artifacts/. Every numeric claim must trace to a value in this task's
or a dependency's artifacts/. Record any gap you discover via `rc task add-gap`.
```

Repeat for the other 9 with role-appropriate bodies and frontmatter `kind`/`model` (literature=haiku, ideation=opus, experiment=sonnet, polish=sonnet, review=opus, rebuttal=sonnet; helpers rc-plan=sonnet kind:plan, rc-verify=sonnet kind:verify, rc-update-spec=haiku kind:update-spec). Use the §5 table for descriptions.

- [ ] **Step 4: Create spec-template dirs**

Run: `mkdir research-kit/spec-templates/venue research-kit/spec-templates/writing research-kit/spec-templates/baselines research-kit/spec-templates/methodology research-kit/spec-templates/novelty` and add an empty `.gitkeep` in each (PowerShell: `New-Item -ItemType File <dir>/.gitkeep`).

- [ ] **Step 5: Write the presence test**

`packages/adapters/test/templates.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import * as fs from "node:fs"; import * as path from "node:path";

const KIT = path.resolve(__dirname, "../../../research-kit");
describe("research-kit templates", () => {
  it("has workflow.md with all 5 state blocks", () => {
    const md = fs.readFileSync(path.join(KIT, "workflow.md"), "utf8");
    for (const s of ["no_task","planning","in_progress","verify","completed"])
      expect(md).toContain(`[workflow-state:${s}]`);
  });
  it("has 10 agent templates", () => {
    const agents = fs.readdirSync(path.join(KIT, "agents")).filter(f => f.endsWith(".md"));
    expect(agents.length).toBe(10);
  });
});
```

- [ ] **Step 6: Run / Commit**

Run: `pnpm vitest run packages/adapters/test/templates.test.ts` → PASS (create `packages/adapters/package.json` + `tsconfig.json` mirroring core first; depend on `@research-copilot/core` via `workspace:*`).

```bash
git add research-kit packages/adapters/package.json packages/adapters/tsconfig.json packages/adapters/test/templates.test.ts
git commit -m "feat(kit): workflow.md + 10 agent templates + config defaults + spec template dirs"
```

---

## Task 13: Adapters registry + Claude Code configurator (§6.3)

**Files:**
- Create: `packages/adapters/src/registry.ts`
- Create: `packages/adapters/src/render.ts`
- Create: `packages/adapters/src/configurators/claude-code.ts`
- Create: `packages/adapters/src/index.ts`
- Test: `packages/adapters/test/claude-code.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/adapters/test/claude-code.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { configureClaudeCode } from "../src/configurators/claude-code.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("claude-code configurator", () => {
  it("writes a UserPromptSubmit hook that calls rc context", () => {
    configureClaudeCode(repo);
    const settings = JSON.parse(fs.readFileSync(path.join(repo, ".claude/settings.json"), "utf8"));
    const cmd = settings.hooks.UserPromptSubmit[0].hooks[0].command;
    expect(cmd).toContain("rc context");
    expect(cmd).toContain("--format text");
  });
  it("renders the 10 agents into .claude/agents", () => {
    configureClaudeCode(repo);
    const agents = fs.readdirSync(path.join(repo, ".claude/agents")).filter(f => f.endsWith(".md"));
    expect(agents.length).toBe(10);
  });
  it("merges into an existing settings.json without clobbering foreign keys", () => {
    fs.mkdirSync(path.join(repo, ".claude"), { recursive: true });
    fs.writeFileSync(path.join(repo, ".claude/settings.json"),
      JSON.stringify({ model: "opus", hooks: { SessionStart: [{ matcher: "*", hooks: [] }] } }));
    configureClaudeCode(repo);
    const s = JSON.parse(fs.readFileSync(path.join(repo, ".claude/settings.json"), "utf8"));
    expect(s.model).toBe("opus");                 // foreign key preserved
    expect(s.hooks.SessionStart).toBeDefined();   // foreign hook preserved
    expect(s.hooks.UserPromptSubmit).toBeDefined(); // ours added
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/adapters/test/claude-code.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

`packages/adapters/src/registry.ts`:
```ts
export type InjectionClass = 1 | 2;
export interface ToolEntry {
  id: string; configDir: string; cliFlag: string;
  agentCapable: boolean; hasHooks: boolean;
  injectionClass: InjectionClass;
  agentFormat: "md" | "toml" | "none";
  skillsPaths: string[];
}
export const AI_TOOLS: Record<string, ToolEntry> = {
  "claude-code": {
    id: "claude-code", configDir: ".claude", cliFlag: "claude",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".claude/skills"],
  },
  // cursor / codex / opencode / windsurf / gemini land in Phase 1–2
};
```

`packages/adapters/src/render.ts`:
```ts
export function render(tpl: string, vars: Record<string, string>): string {
  return tpl.replace(/\{\{(\w+)\}\}/g, (_, k) => vars[k] ?? `{{${k}}}`);
}
export function deepMergeJson(base: any, add: any): any {
  if (Array.isArray(base) && Array.isArray(add)) return [...base, ...add];
  if (base && add && typeof base === "object" && typeof add === "object") {
    const out: any = { ...base };
    for (const k of Object.keys(add)) out[k] = deepMergeJson(base[k], add[k]);
    return out;
  }
  return add ?? base;
}
```

`packages/adapters/src/configurators/claude-code.ts`:
```ts
import * as fs from "node:fs";
import * as path from "node:path";
import { deepMergeJson } from "../render.js";

const KIT = path.resolve(__dirname, "../../../../research-kit");

export function configureClaudeCode(repo: string): void {
  const cc = path.join(repo, ".claude");
  fs.mkdirSync(path.join(cc, "agents"), { recursive: true });

  // settings.json — merge our UserPromptSubmit hook in, preserving foreign config
  const settingsPath = path.join(cc, "settings.json");
  const existing = fs.existsSync(settingsPath)
    ? JSON.parse(fs.readFileSync(settingsPath, "utf8")) : {};
  const ours = {
    hooks: {
      UserPromptSubmit: [{
        matcher: "*",
        hooks: [{ type: "command", command: "rc context --inject --format text", timeout: 20 }],
      }],
    },
  };
  fs.writeFileSync(settingsPath, JSON.stringify(deepMergeJson(existing, ours), null, 2) + "\n", "utf8");

  // agents — copy the 10 neutral templates verbatim (Claude Code consumes md+frontmatter)
  const agentsSrc = path.join(KIT, "agents");
  for (const f of fs.readdirSync(agentsSrc).filter(x => x.endsWith(".md"))) {
    fs.copyFileSync(path.join(agentsSrc, f), path.join(cc, "agents", f));
  }

  // CLAUDE.md — minimal behavioural note pointing at the workflow
  fs.writeFileSync(path.join(repo, "CLAUDE.md"),
    "- Research workflow is governed by .research/. Each turn, the injected " +
    "[workflow-state]+[research-state] block tells you the next step. Dispatch rc-* executors; do not do domain work inline.\n",
    { flag: "a" });
}
```

`packages/adapters/src/index.ts`:
```ts
export * from "./registry.js";
export * from "./render.js";
export { configureClaudeCode } from "./configurators/claude-code.js";
```

> Note: `__dirname` is unavailable in pure ESM. Add to each configurator/test file that needs it:
> `import { fileURLToPath } from "node:url"; const __dirname = path.dirname(fileURLToPath(import.meta.url));`

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/adapters/test/claude-code.test.ts`
Expected: PASS (3 tests, incl. the merge-preservation test).

- [ ] **Step 5: Commit**

```bash
git add packages/adapters/src packages/adapters/test/claude-code.test.ts
git commit -m "feat(adapters): registry + Claude Code configurator (merge-safe hook + agents)"
```

---

## Task 14: CLI skeleton + `rc context` + `rc doctor`

**Files:**
- Create: `packages/cli/package.json`, `packages/cli/tsconfig.json`, `packages/cli/bin/rc.ts`
- Create: `packages/cli/src/program.ts`, `packages/cli/src/commands/context.ts`, `packages/cli/src/commands/doctor.ts`
- Test: `packages/cli/test/context.test.ts`

- [ ] **Step 1: Create the cli manifest**

`packages/cli/package.json`:
```json
{
  "name": "research-copilot",
  "version": "0.0.0",
  "type": "module",
  "bin": { "rc": "./dist/rc.js" },
  "scripts": { "build": "tsup bin/rc.ts --format esm" },
  "dependencies": {
    "@research-copilot/core": "workspace:*",
    "@research-copilot/adapters": "workspace:*",
    "commander": "^12.1.0"
  }
}
```

`packages/cli/tsconfig.json`: same shape as core's.

- [ ] **Step 2: Write the failing test** (drives `rc context` through the program)

`packages/cli/test/context.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runContext } from "../src/commands/context.js";

let repo: string;
beforeEach(() => {
  repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-"));
  fs.mkdirSync(path.join(repo, ".research"), { recursive: true });
  fs.writeFileSync(path.join(repo, ".research/workflow.md"),
    "[workflow-state:no_task]\nNo active task.\n[/workflow-state]\n");
});

describe("rc context", () => {
  it("returns the no_task block + research-state when nothing is active", () => {
    const out = runContext({ repo, format: "text", now: "2026-06-05T00:00:00Z" });
    expect(out).toContain("[workflow-state:no_task]");
    expect(out).toContain("[research-state]");
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pnpm vitest run packages/cli/test/context.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 4: Write minimal implementation**

`packages/cli/src/commands/context.ts`:
```ts
import { buildContext } from "@research-copilot/core";

export interface ContextArgs { repo: string; format: "text" | "json"; now: string; }
export function runContext(args: ContextArgs): string {
  return buildContext(args.repo, { format: args.format, now: args.now });
}
```

`packages/cli/src/commands/doctor.ts`:
```ts
import * as fs from "node:fs";
import * as path from "node:path";

export function runDoctor(repo: string): { ok: boolean; report: string[] } {
  const report: string[] = [];
  let ok = true;
  const checks: [string, boolean][] = [
    [".research/ exists", fs.existsSync(path.join(repo, ".research"))],
    ["workflow.md exists", fs.existsSync(path.join(repo, ".research/workflow.md"))],
    [".claude/settings.json exists", fs.existsSync(path.join(repo, ".claude/settings.json"))],
  ];
  for (const [name, pass] of checks) {
    report.push(`${pass ? "OK " : "FAIL"} ${name}`);
    if (!pass) ok = false;
  }
  return { ok, report };
}
```

`packages/cli/src/program.ts`:
```ts
import { Command } from "commander";
import { runContext } from "./commands/context.js";
import { runDoctor } from "./commands/doctor.js";
import { registerInit } from "./commands/init.js";
import { registerTask } from "./commands/task.js";

export function buildProgram(repo = process.cwd()): Command {
  const program = new Command("rc");
  program.command("context")
    .option("--platform <p>", "platform", "claude-code")
    .option("--inject", "inject mode", false)
    .option("--format <f>", "text|json", "text")
    .action((opts) => {
      process.stdout.write(runContext({ repo, format: opts.format, now: new Date().toISOString() }));
    });
  program.command("doctor").action(() => {
    const { ok, report } = runDoctor(repo);
    process.stdout.write(report.join("\n") + "\n");
    process.exitCode = ok ? 0 : 1;
  });
  registerInit(program, repo);
  registerTask(program, repo);
  return program;
}
```

`packages/cli/bin/rc.ts`:
```ts
#!/usr/bin/env node
import { buildProgram } from "../src/program.js";
buildProgram().parse(process.argv);
```

> The program imports `./commands/init.js` and `./commands/task.js` — created in Tasks 15–16. To keep this task green in isolation, stub them: create `init.ts`/`task.ts` exporting `export function registerInit(){}` / `export function registerTask(){}` now, and flesh them out next. (Commit the stubs with this task.)

- [ ] **Step 5: Run test to verify it passes**

Run: `pnpm vitest run packages/cli/test/context.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/cli
git commit -m "feat(cli): rc program skeleton + rc context + rc doctor"
```

---

## Task 15: `rc init`

**Files:**
- Create: `packages/cli/src/commands/init.ts` (replace the stub)
- Test: `packages/cli/test/init.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/cli/test/init.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("rc init", () => {
  it("scaffolds .research/ and Claude Code config", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester" });
    expect(fs.existsSync(path.join(repo, ".research/workflow.md"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".research/config.yaml"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".research/spec/venue"))).toBe(true);
    expect(fs.existsSync(path.join(repo, ".claude/settings.json"))).toBe(true);
    expect(fs.readdirSync(path.join(repo, ".claude/agents")).length).toBe(10);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/cli/test/init.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

`packages/cli/src/commands/init.ts`:
```ts
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { researchPaths } from "@research-copilot/core";
import { configureClaudeCode } from "@research-copilot/adapters";
import type { Command } from "commander";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KIT = path.resolve(__dirname, "../../../../research-kit");

export interface InitArgs { repo: string; platforms: string[]; user: string; }

export function runInit(args: InitArgs): void {
  const p = researchPaths(args.repo);
  for (const d of [p.tasks, p.spec, p.workspace, p.runtime]) fs.mkdirSync(d, { recursive: true });
  for (const s of ["venue","writing","baselines","methodology","novelty"])
    fs.mkdirSync(path.join(p.spec, s), { recursive: true });
  fs.copyFileSync(path.join(KIT, "workflow.md"), p.workflow);
  fs.copyFileSync(path.join(KIT, "config.defaults.yaml"), p.config);

  if (args.platforms.includes("claude-code")) configureClaudeCode(args.repo);
}

export function registerInit(program: Command, repo: string): void {
  program.command("init")
    .option("--claude", "Claude Code", false)
    .requiredOption("-u, --user <name>", "developer identity")
    .action((opts) => {
      const platforms = opts.claude ? ["claude-code"] : ["claude-code"];
      runInit({ repo, platforms, user: opts.user });
      process.stdout.write(`Initialized .research/ for: ${platforms.join(", ")}\n`);
    });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/cli/test/init.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/init.ts packages/cli/test/init.test.ts
git commit -m "feat(cli): rc init scaffolds .research + Claude Code config"
```

---

## Task 16: `rc task` lifecycle commands

**Files:**
- Create: `packages/cli/src/commands/task.ts` (replace the stub)
- Test: `packages/cli/test/task.test.ts`

- [ ] **Step 1: Write the failing test**

`packages/cli/test/task.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";
import { taskCreate, taskSetStatus, taskAddGap, taskCurrent } from "../src/commands/task.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); runInit({ repo, platforms: ["claude-code"], user: "t" }); });

describe("rc task lifecycle", () => {
  it("create -> start -> verify -> complete walks the FSM and tracks active", () => {
    const t = taskCreate(repo, { title: "Method", kind: "writing", date: "2026-06-05" });
    expect(taskCurrent(repo)).toBe(t.id);
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    taskSetStatus(repo, t.id, "verify", "2026-06-05T02:00:00Z");
    taskSetStatus(repo, t.id, "completed", "2026-06-05T03:00:00Z");
    expect(() => taskSetStatus(repo, t.id, "in_progress", "2026-06-05T04:00:00Z")).toThrow();
  });
  it("add-gap records an open gap with suggest_kind", () => {
    const t = taskCreate(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    taskAddGap(repo, t.id, "missing ablation", "experiment");
    const stored = JSON.parse(fs.readFileSync(path.join(repo, ".research/tasks", t.id, "task.json"), "utf8"));
    expect(stored.gaps[0]).toMatchObject({ desc: "missing ablation", suggest_kind: "experiment", status: "open" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/cli/test/task.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

`packages/cli/src/commands/task.ts`:
```ts
import { createTask, readTask, writeTask, setStatus, setActive, getActive,
  type Kind, type Status } from "@research-copilot/core";
import type { Command } from "commander";

export function taskCreate(repo: string, i: { title: string; kind: Kind; date: string; venue?: string; parent?: string }) {
  const t = createTask(repo, i);
  setActive(repo, t.id);
  return t;
}
export function taskSetStatus(repo: string, id: string, to: Status, now: string) {
  setStatus(repo, id, to, now);
}
export function taskAddGap(repo: string, id: string, desc: string, suggest_kind: Kind) {
  const t = readTask(repo, id);
  t.gaps.push({ desc, suggest_kind, status: "open" });
  writeTask(repo, t, new Date().toISOString());
}
export function taskCurrent(repo: string) { return getActive(repo); }

export function registerTask(program: Command, repo: string): void {
  const today = () => new Date().toISOString().slice(0, 10);
  const task = program.command("task");
  task.command("create").requiredOption("--kind <k>").requiredOption("--title <t>")
    .option("--venue <v>").option("--parent <p>")
    .action(o => { const t = taskCreate(repo, { title: o.title, kind: o.kind, date: today(), venue: o.venue, parent: o.parent }); process.stdout.write(t.id + "\n"); });
  for (const [cmd, to] of [["start","in_progress"],["verify","verify"],["complete","completed"]] as const)
    task.command(cmd).argument("<id>").action(id => taskSetStatus(repo, id, to as Status, new Date().toISOString()));
  task.command("set-status").argument("<id>").argument("<state>")
    .action((id, state) => taskSetStatus(repo, id, state as Status, new Date().toISOString()));
  task.command("add-gap").argument("<id>").requiredOption("--desc <d>").requiredOption("--suggest <k>")
    .action((id, o) => taskAddGap(repo, id, o.desc, o.suggest));
  task.command("current").action(() => process.stdout.write((taskCurrent(repo) ?? "none") + "\n"));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/cli/test/task.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/task.ts packages/cli/test/task.test.ts
git commit -m "feat(cli): rc task create/start/verify/complete/set-status/add-gap/current"
```

---

## Task 17: Wire `rc task verify` to the verify gate (acceptance 3)

**Files:**
- Modify: `packages/cli/src/commands/task.ts` (verify runs number-traceability before allowing verify→completed path)
- Test: `packages/cli/test/verify-gate.test.ts`

The acceptance criterion: a writing task whose draft cites a number absent from artifacts must FAIL the gate and roll back to `in_progress`.

- [ ] **Step 1: Write the failing test**

`packages/cli/test/verify-gate.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";
import { taskCreate, taskSetStatus, runVerifyGate } from "../src/commands/task.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); runInit({ repo, platforms: ["claude-code"], user: "t" }); });

function seed(id: string, draft: string, artifacts: string) {
  const dir = path.join(repo, ".research/tasks", id, "artifacts");
  fs.writeFileSync(path.join(dir, "draft.tex"), draft);
  fs.writeFileSync(path.join(dir, "run.log"), artifacts);
}

describe("verify gate (acceptance 3)", () => {
  it("fails and rolls back on a fabricated number", () => {
    const t = taskCreate(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    taskSetStatus(repo, t.id, "verify", "2026-06-05T02:00:00Z");
    seed(t.id, "We reach 99.9 acc.", "final_acc=92.5");
    const res = runVerifyGate(repo, t.id, "2026-06-05T03:00:00Z");
    expect(res.ok).toBe(false);
    expect(res.missing).toContain("99.9");
    expect(JSON.parse(fs.readFileSync(path.join(repo, ".research/tasks", t.id, "task.json"), "utf8")).status)
      .toBe("in_progress"); // rolled back
  });
  it("passes when numbers trace", () => {
    const t = taskCreate(repo, { title: "M", kind: "writing", date: "2026-06-05" });
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    taskSetStatus(repo, t.id, "verify", "2026-06-05T02:00:00Z");
    seed(t.id, "We reach 92.5 acc.", "final_acc=92.5");
    expect(runVerifyGate(repo, t.id, "2026-06-05T03:00:00Z").ok).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run packages/cli/test/verify-gate.test.ts`
Expected: FAIL — `runVerifyGate` not exported.

- [ ] **Step 3: Add `runVerifyGate` to `task.ts`**

```ts
import * as fs from "node:fs";
import * as path from "node:path";
import { readTask, setStatus, numberTraceability, researchPaths } from "@research-copilot/core";

export function runVerifyGate(repo: string, id: string, now: string): { ok: boolean; missing: string[] } {
  const t = readTask(repo, id);
  const dir = path.join(researchPaths(repo).taskDir(id), "artifacts");
  const read = (glob: RegExp) => fs.existsSync(dir)
    ? fs.readdirSync(dir).filter(f => glob.test(f)).map(f => fs.readFileSync(path.join(dir, f), "utf8")).join("\n") : "";
  let result = { ok: true, missing: [] as string[] };
  if (t.kind === "writing") {
    const draft = read(/\.tex$/);
    const artifacts = read(/\.(log|txt|json|csv)$/);
    result = numberTraceability(draft, artifacts);
  }
  if (!result.ok) setStatus(repo, id, "in_progress", now); // rollback
  return result;
}
```

Then update the `verify` command to call the gate and only stay in `verify` (for the human to then `complete`) when it passes:
```ts
// in registerTask, replace the "verify" branch:
task.command("verify").argument("<id>").action(id => {
  const r = runVerifyGate(repo, id, new Date().toISOString());
  if (r.ok) process.stdout.write(`verify OK for ${id}\n`);
  else { process.stdout.write(`verify FAILED (untraceable: ${r.missing.join(", ")}); rolled back to in_progress\n`); process.exitCode = 1; }
});
```
> Note: the FSM move into `verify` happens via `rc task set-status <id> verify` after the executor returns; `rc task verify` then runs the gate. Keep `taskSetStatus` for the move and `runVerifyGate` for the check.

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run packages/cli/test/verify-gate.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/task.ts packages/cli/test/verify-gate.test.ts
git commit -m "feat(cli): verify gate runs number-traceability and rolls back on failure"
```

---

## Task 18: End-to-end loop test (acceptance 2) + build

**Files:**
- Test: `packages/cli/test/e2e.test.ts`

- [ ] **Step 1: Write the e2e test**

`packages/cli/test/e2e.test.ts`:
```ts
import { describe, it, expect, beforeEach } from "vitest";
import * as fs from "node:fs"; import * as os from "node:os"; import * as path from "node:path";
import { runInit } from "../src/commands/init.js";
import { taskCreate, taskSetStatus } from "../src/commands/task.js";
import { runContext } from "../src/commands/context.js";

let repo: string;
beforeEach(() => { repo = fs.mkdtempSync(path.join(os.tmpdir(), "rc-")); });

describe("e2e research loop on Claude Code", () => {
  it("init -> create -> start -> context shows in_progress + recommendation", () => {
    runInit({ repo, platforms: ["claude-code"], user: "t" });
    const t = taskCreate(repo, { title: "Main exp", kind: "experiment", date: "2026-06-05" });
    taskSetStatus(repo, t.id, "in_progress", "2026-06-05T01:00:00Z");
    const ctx = runContext({ repo, format: "text", now: "2026-06-05T02:00:00Z" });
    expect(ctx).toContain("[workflow-state:in_progress]");
    expect(ctx).toContain("[research-state]");
    expect(ctx).toContain(t.id);
  });
});
```

- [ ] **Step 2: Run the full suite**

Run: `pnpm vitest run`
Expected: ALL tests across core/cli/adapters PASS.

- [ ] **Step 3: Build everything**

Run: `pnpm -r build`
Expected: `dist/` emitted for core, adapters, cli; no TS errors.

- [ ] **Step 4: Smoke-test the built CLI**

Run (PowerShell): `node packages/cli/dist/rc.js doctor` from a temp dir that has had `.research` created, OR `node packages/cli/dist/rc.js --help`.
Expected: help text lists `init`, `task`, `context`, `doctor`.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/test/e2e.test.ts
git commit -m "test(cli): e2e research loop on Claude Code + full build green"
```

---

## Task 19: Documentation — README + docs/usage + docs/dev (spec §17)

**Files:**
- Create: `README.md`
- Create: `docs/usage/README.md`, `docs/usage/commands.md`, `docs/usage/claude-code.md`, `docs/usage/workflow-walkthrough.md`
- Create: `docs/dev/architecture.md`, `docs/dev/core-api.md`, `docs/dev/adding-a-platform.md`, `docs/dev/testing.md`, `docs/dev/adr/0001-trellis-emulation.md`

> Spec §17 requires docs as a Phase acceptance gate. Write real content — no "TODO".

- [ ] **Step 1: Root `README.md`**

Content must include: one-paragraph intro (research-copilot = Trellis-style, research-native, multi-platform `rc` CLI); install (`npm i -g research-copilot` once published / `node packages/cli/dist/rc.js` from source in Phase 0); `rc` command list (init/task/context/doctor); platform support matrix (Claude Code = ✅ shipped; Cursor/Codex/OpenCode/Windsurf/Gemini = wired in Phase 1–2; others = planned); relationship to the old plugin (superseded; see spec); links to `docs/usage/` and `docs/dev/`. Link the spec at `docs/superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md`.

- [ ] **Step 2: `docs/usage/`**

- `commands.md`: every `rc` subcommand with flags + an example invocation and expected output (from Tasks 14–17).
- `claude-code.md`: how `rc init --claude -u <name>` wires the `UserPromptSubmit` hook → `rc context`; how to verify with `rc doctor`; Windows note (rc shim / `npx` fallback).
- `workflow-walkthrough.md`: a worked run — create an experiment task, start it, what the injected `[workflow-state]`+`[research-state]` looks like, verify, complete, read the next recommendation. Paste real `rc context` output.
- `README.md`: index of the above.

- [ ] **Step 3: `docs/dev/`**

- `architecture.md`: the layer map (core/cli/adapters/research-kit), pointing to spec §3–§6; the two-layer state model (§4); injection-driven recommendation (no conductor).
- `core-api.md`: the public surface from `packages/core/src/index.ts` — `computeResearchState`, `buildContext`, task-store fns, `numberTraceability`/`citationCompliance`, FSM — with signatures and one example each.
- `adding-a-platform.md`: the registry entry shape (`AI_TOOLS`) + writing a `configure<Platform>()` + the injection-class decision (class-1 hook vs class-2 breadcrumb, §6.1) + golden-snapshot test. This directly enables Phase 1–2 / milestone-2 platforms.
- `testing.md`: how to run vitest, where tests live, the e2e/golden-snapshot patterns, how to add a research-state fixture.
- `adr/0001-trellis-emulation.md`: the decision record — summarize locked decisions D1–D8 (link spec §2), why Trellis, why TS, why injection-driven; supersedes the 2026-05-05 design.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/usage docs/dev
git commit -m "docs: Phase 0 README + usage + dev/onboarding docs (spec 17)"
```

---

## Task 20: Phase 0 acceptance sweep + CI script

**Files:**
- Modify: root `package.json` (add `ci` script)
- Create: `.github/workflows/ci.yml` (optional but recommended)

- [ ] **Step 1: Add a `ci` script**

In root `package.json` scripts: `"ci": "pnpm -r build && vitest run"`.

- [ ] **Step 2: Run the acceptance sweep**

Run: `pnpm ci`
Expected: build green + ALL tests pass. Confirm against acceptance:
1. core unit tests incl. research-state fixtures (Task 6) + verify checks (Task 9) ✅
2. e2e loop (Task 18) ✅
3. verify-gate rollback on fabricated number (Task 17) ✅
4. Claude Code adapter merge-safe + 10 agents + hook→`rc context` (Task 13) ✅
5. docs present (Task 19) ✅

- [ ] **Step 3: (Optional) CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: ci
on: [push, pull_request]
jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 9 }
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm ci
```

- [ ] **Step 4: Commit**

```bash
git add package.json .github/workflows/ci.yml
git commit -m "chore: ci script + workflow; Phase 0 acceptance green"
```

---

## Self-Review (completed during authoring)

**Spec coverage (Phase 0 slice):** core types/store/FSM/graph (§3.3, §4.1) → Tasks 1–5,10; research-state §16.1 → Task 6; workflow parser + context builder §16.3/§16.6 → Tasks 7,11; artifacts §16.3 → Task 8; verify checks §16.2 → Tasks 9,17; CLI surface §6.4/§16.9 → Tasks 14–17; adapters/registry/Claude Code §6.1/§6.3 → Task 13; agents/workflow templates §5/§4.2 → Task 12; injection wiring §6.2 → Tasks 11,13,14; docs §17 → Task 19; acceptance §14 → Tasks 18,20. Out-of-Phase-0 (correctly deferred): MCP servers §7 (Phase 3), other platforms §6.1 (Phase 1–2), skillpacks §9/§16.10 (Phase 4), full per-kind verify table §16.2 (kinds beyond writing land with their phases).

**Placeholder scan:** no TBD/TODO; every code step has complete code; commands have expected output. The two `init.ts`/`task.ts` stubs in Task 14 are explicitly created and then replaced in Tasks 15–16 (not placeholders — real, sequenced).

**Type consistency:** `TaskRecord`/`Kind`/`Status`/`Gap` defined Task 1, used unchanged everywhere; `computeResearchState(tasks, now, activeId?)` signature consistent across Tasks 6,11; `numberTraceability(draft, artifacts)` consistent Tasks 9,17; `configureClaudeCode(repo)` consistent Tasks 13,15; `researchPaths` shape consistent throughout.

**Known implementer notes (already inlined):** ESM `__dirname` shim; Windows path normalization in path test; create `.research/` before writing workflow.md in context/e2e fixtures.

---

## Execution Handoff

Phase 0 plan complete. **Phases 1–4 will each get their own plan authored after Phase 0 lands** (their bite-sized code depends on Phase 0's realized core/adapters APIs). 
