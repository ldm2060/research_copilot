# Trellis Sub-agent Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce research workflow execution through Trellis task nodes so the main conversation conducts lifecycle and reporting while legal `rc-*` / `copilot-*` executors perform research-domain leaf work.

**Architecture:** Add a TypeScript source of truth for Trellis executor and artifact ownership, expose platform enforcement capability through adapters, inject the capability into `rc context`, report it in `rc doctor`, align research-kit templates with node semantics, and evolve the Python class-1 hook layer into a Trellis claim validator with event logging. The TypeScript core remains pure and filesystem-light; platform-specific capability lives in adapters; hook hard-deny logic stays in `self/hooks/scripts/`.

**Tech Stack:** TypeScript ESM, Node >=20 in the monorepo root, pnpm 9.12.0, Vitest 2.1, Python 3 hook scripts, pytest for hook tests where Python hook behavior is changed.

## Global Constraints

- Scope is **research workflow tasks only**: literature, ideation, experiment, writing, polish, review, rebuttal, verification, and spec consolidation.
- Repository development tasks remain allowed in the main session: code edits, tests, docs, hook debugging, and git commit are not research-domain leaf work.
- Enforcement strategy is **hybrid by platform capability**: class-1 platforms get hard-deny enforcement; class-2 platforms get explicit soft enforcement with risk reporting.
- If a user asks for research-domain work with no active task, the conductor should **auto-create a task node** rather than ask the user to create one manually.
- Enforcement must be Trellis-aligned: task node, lifecycle status, kind, executor claim, and artifact ownership are the source of truth. Tool/path deny-lists are implementation details.
- Do not change the existing lifecycle states: `planning -> in_progress -> verify -> completed`.
- Do not extend this enforcement to repository development work.
- Do not pretend Cursor/Windsurf can provide hard enforcement when the platform lacks the required hooks or agents.
- Do not let executors recursively dispatch other `rc-*` executors.
- Do not hand-edit generated `packages/cli/research-kit/` output.
- Do not change release version numbers by hand.

---

## File Structure

### New files

- `packages/core/src/enforcement.ts` — pure Trellis enforcement primitives: executor ids, enforcement modes, expected executor mapping, artifact ownership classification, and write-claim checks.
- `packages/core/test/enforcement.test.ts` — unit tests for executor mapping, artifact classification, conductor allowances, and executor ownership.
- `self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py` — Python tests for main-session denial, active-node executor matching, class-1 event logging, and `rc-*` / `copilot-*` sub-agent handling.
- `self/hooks/copilot-write-guard.json` — Claude Code hook discovery spec for the sub-agent write partition guard.
- `self/hooks/copilot-subagent-stop.json` — Claude Code hook discovery spec for the sub-agent stop handoff gate.

### Modified files

- `packages/core/src/index.ts` — export `enforcement.ts`.
- `packages/core/src/context.ts` — include optional `[trellis-enforcement]` block in context output.
- `packages/core/test/context.test.ts` — assert enforcement block rendering.
- `packages/cli/src/commands/context.ts` — accept platform, resolve platform enforcement support, pass it into core context.
- `packages/cli/src/program.ts` — wire existing `--platform <p>` option into `runContext`, and add `--platform <p>` to `doctor`.
- `packages/cli/test/context.test.ts` — assert hard and soft platform summaries.
- `packages/cli/src/commands/doctor.ts` — report enforcement mode and reason.
- `packages/cli/test/doctor.test.ts` — assert hard mode for Claude Code and soft mode for Windsurf.
- `packages/adapters/src/registry.ts` — add explicit `enforcement` support metadata to every platform entry.
- `packages/adapters/test/claude-code.test.ts` — assert Claude Code reports hard enforcement.
- `packages/adapters/test/cursor.test.ts` — assert Cursor reports soft enforcement.
- `packages/adapters/test/windsurf.test.ts` — assert Windsurf reports soft enforcement and agent-less reason.
- `packages/adapters/test/templates.test.ts` — assert workflow and agent templates contain Trellis ownership language.
- `research-kit/workflow.md` — rewrite workflow-state blocks around task-node frontier semantics and auto-create behavior.
- `research-kit/agents/rc-plan.md`, `research-kit/agents/rc-literature.md`, `research-kit/agents/rc-ideation.md`, `research-kit/agents/rc-experiment.md`, `research-kit/agents/rc-writer.md`, `research-kit/agents/rc-polisher.md`, `research-kit/agents/rc-reviewer.md`, `research-kit/agents/rc-rebuttal.md`, `research-kit/agents/rc-verify.md`, `research-kit/agents/rc-update-spec.md` — add consistent Trellis node ownership, output, gap, and recursion constraints.
- `self/hooks/scripts/research_copilot_guard.py` — validate active Trellis node and executor claim instead of only hard-coded tool/path deny-list messages.
- `self/install.py` — register `copilot_write_guard.py` and `copilot_subagent_stop.py` in `.claude/settings.json`.
- `self/hooks/tests/integration_run.ps1` — extend smoke coverage to the registered Trellis guard path and new hook JSON specs.

### Responsibilities and boundaries

- `packages/core/src/enforcement.ts` has no filesystem reads and imports only core types. It answers pure questions: expected executor, artifact ownership, and whether a conductor or executor may write a path for a given task.
- `packages/adapters/src/registry.ts` owns platform capability. Core does not import adapters.
- `packages/cli/src/commands/context.ts` bridges adapters to core by converting a platform id into an `EnforcementSummary`.
- `self/hooks/scripts/research_copilot_guard.py` owns Claude Code class-1 runtime blocking. It may read `.research/.runtime/active-task` and `.research/tasks/<id>/task.json` from the current workspace.
- `research-kit/` remains the template source of truth. `packages/cli/research-kit/` is generated by build and must not be edited.

---

### Task 1: Add core Trellis enforcement primitives

**Files:**
- Create: `packages/core/src/enforcement.ts`
- Modify: `packages/core/src/index.ts`
- Test: `packages/core/test/enforcement.test.ts`

**Interfaces:**
- Consumes: `TaskRecord`, `Kind`, and `Status` from `packages/core/src/types.ts`.
- Produces:
  - `ResearchExecutor` union type.
  - `EnforcementMode` union type.
  - `EnforcementSummary` interface.
  - `expectedExecutorFor(task: Pick<TaskRecord, "kind" | "status">): ResearchExecutor`.
  - `canExecutorClaim(task: Pick<TaskRecord, "kind" | "status">, executor: string): boolean`.
  - `classifyArtifact(filePath: string): ArtifactClaim`.
  - `canWriteArtifact(actor: "conductor" | ResearchExecutor, task: Pick<TaskRecord, "kind" | "status">, filePath: string): boolean`.

- [ ] **Step 1: Write failing executor mapping tests**

Create `packages/core/test/enforcement.test.ts` with this content:

```ts
import { describe, it, expect } from "vitest";
import {
  expectedExecutorFor,
  canExecutorClaim,
  classifyArtifact,
  canWriteArtifact,
  type ResearchExecutor,
} from "../src/enforcement.js";
import type { TaskRecord } from "../src/types.js";

const task = (over: Partial<TaskRecord>): TaskRecord => ({
  id: "2026-06-22-node",
  title: "node",
  kind: "writing",
  status: "planning",
  priority: "P2",
  children: [],
  depends_on: [],
  gaps: [],
  created: "2026-06-22T00:00:00Z",
  updated: "2026-06-22T00:00:00Z",
  ...over,
});

describe("Trellis executor mapping", () => {
  it("maps lifecycle states to the legal executor", () => {
    expect(expectedExecutorFor(task({ status: "planning", kind: "literature" }))).toBe("rc-plan");
    expect(expectedExecutorFor(task({ status: "verify", kind: "experiment" }))).toBe("rc-verify");
    expect(expectedExecutorFor(task({ status: "completed", kind: "review" }))).toBe("rc-update-spec");
  });

  it("maps every in-progress kind to its leaf executor", () => {
    const cases: Array<[TaskRecord["kind"], ResearchExecutor]> = [
      ["literature", "rc-literature"],
      ["ideation", "rc-ideation"],
      ["experiment", "rc-experiment"],
      ["writing", "rc-writer"],
      ["polish", "rc-polisher"],
      ["review", "rc-reviewer"],
      ["rebuttal", "rc-rebuttal"],
    ];
    for (const [kind, executor] of cases) {
      expect(expectedExecutorFor(task({ status: "in_progress", kind }))).toBe(executor);
      expect(canExecutorClaim(task({ status: "in_progress", kind }), executor)).toBe(true);
      expect(canExecutorClaim(task({ status: "in_progress", kind }), "rc-plan")).toBe(false);
    }
  });
});
```

- [ ] **Step 2: Write failing artifact ownership tests**

Append these tests to `packages/core/test/enforcement.test.ts`:

```ts
describe("Trellis artifact ownership", () => {
  it("classifies canonical .research task paths", () => {
    expect(classifyArtifact(".research/tasks/t1/task.json")).toMatchObject({ owner: "conductor" });
    expect(classifyArtifact(".research/tasks/t1/prd.md")).toMatchObject({ owner: "rc-plan" });
    expect(classifyArtifact(".research/tasks/t1/execute.jsonl")).toMatchObject({ owner: "rc-plan" });
    expect(classifyArtifact(".research/tasks/t1/verify.jsonl")).toMatchObject({ owner: "rc-plan" });
    expect(classifyArtifact(".research/tasks/t1/verify/report.md")).toMatchObject({ owner: "rc-verify" });
    expect(classifyArtifact(".research/spec/baselines/foo.md")).toMatchObject({ owner: "rc-update-spec" });
    expect(classifyArtifact("src/index.ts")).toMatchObject({ owner: "non-research" });
  });

  it("classifies compatibility research paths", () => {
    expect(classifyArtifact(".copilot/literature.md").allowedExecutors).toEqual(["rc-literature"]);
    expect(classifyArtifact(".copilot/ideas.md").allowedExecutors).toEqual(["rc-ideation"]);
    expect(classifyArtifact(".copilot/experiments.md").allowedExecutors).toEqual(["rc-experiment"]);
    expect(classifyArtifact(".copilot/reviews/round-1.md").allowedExecutors).toEqual(["rc-reviewer"]);
    expect(classifyArtifact("sections/method.tex").allowedExecutors).toEqual(["rc-writer", "rc-polisher", "rc-rebuttal"]);
    expect(classifyArtifact("references.bib").allowedExecutors).toEqual(["rc-literature", "rc-writer"]);
  });

  it("allows conductor metadata and repository development writes", () => {
    expect(canWriteArtifact("conductor", task({ status: "planning" }), ".research/tasks/t1/task.json")).toBe(true);
    expect(canWriteArtifact("conductor", task({ status: "planning" }), "packages/core/src/index.ts")).toBe(true);
    expect(canWriteArtifact("conductor", task({ status: "planning" }), ".research/tasks/t1/prd.md")).toBe(false);
    expect(canWriteArtifact("conductor", task({ status: "completed" }), ".research/spec/baselines/foo.md")).toBe(false);
  });

  it("allows only the active node legal executor to write owned artifacts", () => {
    expect(canWriteArtifact("rc-plan", task({ status: "planning", kind: "literature" }), ".research/tasks/t1/prd.md")).toBe(true);
    expect(canWriteArtifact("rc-literature", task({ status: "planning", kind: "literature" }), ".research/tasks/t1/prd.md")).toBe(false);
    expect(canWriteArtifact("rc-literature", task({ status: "in_progress", kind: "literature" }), ".copilot/literature.md")).toBe(true);
    expect(canWriteArtifact("rc-writer", task({ status: "in_progress", kind: "literature" }), ".copilot/literature.md")).toBe(false);
    expect(canWriteArtifact("rc-update-spec", task({ status: "completed", kind: "review" }), ".research/spec/reviews/gaps.md")).toBe(true);
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
vitest run packages/core/test/enforcement.test.ts
```

Expected: FAIL with an import error for `../src/enforcement.js`.

- [ ] **Step 4: Implement `packages/core/src/enforcement.ts`**

Create `packages/core/src/enforcement.ts` with this content:

```ts
import type { Kind, TaskRecord } from "./types.js";

export const RESEARCH_EXECUTORS = [
  "rc-plan",
  "rc-literature",
  "rc-ideation",
  "rc-experiment",
  "rc-writer",
  "rc-polisher",
  "rc-reviewer",
  "rc-rebuttal",
  "rc-verify",
  "rc-update-spec",
] as const;

export type ResearchExecutor = (typeof RESEARCH_EXECUTORS)[number];
export type EnforcementMode = "hard" | "soft" | "unavailable";

export interface EnforcementSummary {
  platform: string;
  mode: EnforcementMode;
  reason: string;
}

export type ArtifactOwner = "conductor" | ResearchExecutor | "kind-executor" | "non-research";

export interface ArtifactClaim {
  owner: ArtifactOwner;
  allowedExecutors: ResearchExecutor[];
  reason: string;
}

const KIND_EXECUTOR: Record<Kind, ResearchExecutor> = {
  literature: "rc-literature",
  ideation: "rc-ideation",
  experiment: "rc-experiment",
  writing: "rc-writer",
  polish: "rc-polisher",
  review: "rc-reviewer",
  rebuttal: "rc-rebuttal",
};

const KIND_EXECUTORS = Object.values(KIND_EXECUTOR);

export function expectedExecutorFor(task: Pick<TaskRecord, "kind" | "status">): ResearchExecutor {
  if (task.status === "planning") return "rc-plan";
  if (task.status === "verify") return "rc-verify";
  if (task.status === "completed") return "rc-update-spec";
  return KIND_EXECUTOR[task.kind];
}

export function canExecutorClaim(task: Pick<TaskRecord, "kind" | "status">, executor: string): boolean {
  return expectedExecutorFor(task) === executor;
}

export function isResearchExecutor(executor: string): executor is ResearchExecutor {
  return (RESEARCH_EXECUTORS as readonly string[]).includes(executor);
}

function norm(filePath: string): string {
  return filePath.replace(/\\/g, "/").replace(/^\.\//, "");
}

function endsWithSegment(filePath: string, suffix: string): boolean {
  const p = norm(filePath);
  return p === suffix || p.endsWith(`/${suffix}`);
}

function underSegment(filePath: string, segment: string): boolean {
  return norm(filePath).split("/").includes(segment);
}

function claim(owner: ArtifactOwner, allowedExecutors: ResearchExecutor[], reason: string): ArtifactClaim {
  return { owner, allowedExecutors, reason };
}

export function classifyArtifact(filePath: string): ArtifactClaim {
  const p = norm(filePath);

  if (endsWithSegment(p, ".research/.runtime/active-task")) {
    return claim("conductor", [], "active task pointer is conductor lifecycle metadata");
  }
  if (/\.research\/tasks\/[^/]+\/task\.json$/.test(p)) {
    return claim("conductor", [], "task metadata is conductor lifecycle metadata");
  }
  if (/\.research\/tasks\/[^/]+\/(prd\.md|execute\.jsonl|verify\.jsonl)$/.test(p)) {
    return claim("rc-plan", ["rc-plan"], "planning artifacts are owned by rc-plan");
  }
  if (/\.research\/tasks\/[^/]+\/verify\//.test(p)) {
    return claim("rc-verify", ["rc-verify"], "verification artifacts are owned by rc-verify");
  }
  if (/\.research\/tasks\/[^/]+\/(artifacts|research)\//.test(p)) {
    return claim("kind-executor", KIND_EXECUTORS, "task leaf artifacts are owned by the active kind executor");
  }
  if (p.startsWith(".research/spec/")) {
    return claim("rc-update-spec", ["rc-update-spec"], "cross-task spec is owned by rc-update-spec");
  }

  if (endsWithSegment(p, ".copilot/literature.md")) {
    return claim("kind-executor", ["rc-literature"], "legacy literature artifact is literature-executor owned");
  }
  if (endsWithSegment(p, ".copilot/ideas.md")) {
    return claim("kind-executor", ["rc-ideation"], "legacy idea artifact is ideation-executor owned");
  }
  if (endsWithSegment(p, ".copilot/experiments.md")) {
    return claim("kind-executor", ["rc-experiment"], "legacy experiment artifact is experiment-executor owned");
  }
  if (p.includes(".copilot/reviews/")) {
    return claim("kind-executor", ["rc-reviewer"], "legacy review artifact is review-executor owned");
  }
  if (underSegment(p, "sections") && p.endsWith(".tex")) {
    return claim("kind-executor", ["rc-writer", "rc-polisher", "rc-rebuttal"], "paper sections are writing, polish, or rebuttal executor owned");
  }
  if (endsWithSegment(p, "references.bib")) {
    return claim("kind-executor", ["rc-literature", "rc-writer"], "bibliography is literature or writing executor owned");
  }

  return claim("non-research", [], "path is outside research workflow ownership");
}

export function canWriteArtifact(
  actor: "conductor" | ResearchExecutor,
  task: Pick<TaskRecord, "kind" | "status">,
  filePath: string,
): boolean {
  const artifact = classifyArtifact(filePath);
  if (artifact.owner === "non-research") return true;
  if (actor === "conductor") return artifact.owner === "conductor";

  const expected = expectedExecutorFor(task);
  if (actor !== expected) return false;
  if (artifact.owner === "kind-executor") return artifact.allowedExecutors.includes(actor);
  return artifact.owner === actor;
}
```

- [ ] **Step 5: Export the module**

Add this line to `packages/core/src/index.ts`:

```ts
export * from "./enforcement.js";
```

- [ ] **Step 6: Run task tests**

Run:

```bash
vitest run packages/core/test/enforcement.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add packages/core/src/enforcement.ts packages/core/src/index.ts packages/core/test/enforcement.test.ts
git commit -m "feat(core): add trellis enforcement primitives"
```

---

### Task 2: Add platform enforcement capability to adapters and context injection

**Files:**
- Modify: `packages/adapters/src/registry.ts`
- Modify: `packages/adapters/test/claude-code.test.ts`
- Modify: `packages/adapters/test/cursor.test.ts`
- Modify: `packages/adapters/test/windsurf.test.ts`
- Modify: `packages/core/src/context.ts`
- Modify: `packages/core/test/context.test.ts`
- Modify: `packages/cli/src/commands/context.ts`
- Modify: `packages/cli/src/program.ts`
- Modify: `packages/cli/test/context.test.ts`

**Interfaces:**
- Consumes from Task 1: `EnforcementSummary`.
- Produces:
  - `ToolEntry.enforcement: EnforcementSummary`.
  - `BuildOptions.enforcement?: EnforcementSummary`.
  - `renderEnforcementSummary(summary: EnforcementSummary): string`.
  - `ContextArgs.platform?: string`.
  - `runContext(args)` passes platform-derived enforcement into `buildContext`.

- [ ] **Step 1: Write failing adapter capability assertions**

Append this test to `packages/adapters/test/claude-code.test.ts`:

```ts
import { AI_TOOLS } from "../src/registry.js";

it("declares hard Trellis enforcement capability", () => {
  expect(AI_TOOLS["claude-code"].enforcement).toEqual({
    platform: "claude-code",
    mode: "hard",
    reason: "supports hooks and executable sub-agents",
  });
});
```

Append this test to `packages/adapters/test/cursor.test.ts`:

```ts
import { AI_TOOLS } from "../src/registry.js";

it("declares soft Trellis enforcement because hooks are unavailable", () => {
  expect(AI_TOOLS.cursor.enforcement).toEqual({
    platform: "cursor",
    mode: "soft",
    reason: "platform lacks hook-based hard deny; breadcrumb rules and agents are advisory",
  });
});
```

Append this test to `packages/adapters/test/windsurf.test.ts`:

```ts
import { AI_TOOLS } from "../src/registry.js";

it("declares soft Trellis enforcement because hooks and executable agents are unavailable", () => {
  expect(AI_TOOLS.windsurf.enforcement).toEqual({
    platform: "windsurf",
    mode: "soft",
    reason: "platform lacks hook-based hard deny and executable sub-agents; workflows are advisory",
  });
});
```

- [ ] **Step 2: Run adapter tests to verify they fail**

Run:

```bash
vitest run packages/adapters/test/claude-code.test.ts packages/adapters/test/cursor.test.ts packages/adapters/test/windsurf.test.ts
```

Expected: FAIL because `ToolEntry.enforcement` does not exist.

- [ ] **Step 3: Implement adapter enforcement metadata**

Modify `packages/adapters/src/registry.ts`.

At the top, add:

```ts
import type { EnforcementSummary } from "@research-copilot/core";
```

Change `ToolEntry` to include:

```ts
  enforcement: EnforcementSummary;
```

Add these properties to the platform entries:

```ts
  "claude-code": {
    id: "claude-code", configDir: ".claude", cliFlag: "claude",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".claude/skills"],
    enforcement: {
      platform: "claude-code",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  codex: {
    id: "codex", configDir: ".codex", cliFlag: "codex",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "toml", skillsPaths: [".agents/skills"],
    enforcement: {
      platform: "codex",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  opencode: {
    id: "opencode", configDir: ".opencode", cliFlag: "opencode",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".opencode/skills"],
    enforcement: {
      platform: "opencode",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  gemini: {
    id: "gemini", configDir: ".gemini", cliFlag: "gemini",
    agentCapable: true, hasHooks: true, injectionClass: 1,
    agentFormat: "md", skillsPaths: [".gemini/skills", ".agents/skills"],
    enforcement: {
      platform: "gemini",
      mode: "hard",
      reason: "supports hooks and executable sub-agents",
    },
  },
  cursor: {
    id: "cursor", configDir: ".cursor", cliFlag: "cursor",
    agentCapable: true, hasHooks: false, injectionClass: 2,
    agentFormat: "md", skillsPaths: [".cursor/skills"],
    enforcement: {
      platform: "cursor",
      mode: "soft",
      reason: "platform lacks hook-based hard deny; breadcrumb rules and agents are advisory",
    },
  },
  windsurf: {
    id: "windsurf", configDir: ".windsurf", cliFlag: "windsurf",
    agentCapable: false, hasHooks: false, injectionClass: 2,
    agentFormat: "none", skillsPaths: [".windsurf/workflows"],
    enforcement: {
      platform: "windsurf",
      mode: "soft",
      reason: "platform lacks hook-based hard deny and executable sub-agents; workflows are advisory",
    },
  },
```

- [ ] **Step 4: Write failing context enforcement tests**

Append this test to `packages/core/test/context.test.ts`:

```ts
  it("renders a Trellis enforcement block when enforcement summary is supplied", () => {
    const out = buildContext(repo, {
      format: "text",
      now: "2026-06-05T02:00:00Z",
      enforcement: {
        platform: "claude-code",
        mode: "hard",
        reason: "supports hooks and executable sub-agents",
      },
    });
    expect(out).toContain("[trellis-enforcement]");
    expect(out).toContain("Mode: hard");
    expect(out).toContain("Platform: claude-code");
    expect(out).toContain("Reason: supports hooks and executable sub-agents");
  });
```

Replace `packages/cli/test/context.test.ts` with this content:

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

  it("includes hard enforcement for claude-code by default", () => {
    const out = runContext({ repo, format: "text", now: "2026-06-05T00:00:00Z" });
    expect(out).toContain("[trellis-enforcement]");
    expect(out).toContain("Platform: claude-code");
    expect(out).toContain("Mode: hard");
  });

  it("includes soft enforcement for class-2 platforms", () => {
    const out = runContext({ repo, platform: "windsurf", format: "text", now: "2026-06-05T00:00:00Z" });
    expect(out).toContain("Platform: windsurf");
    expect(out).toContain("Mode: soft");
    expect(out).toContain("Strict sub-agent-only execution cannot be guaranteed on this platform.");
  });
});
```

- [ ] **Step 5: Run context tests to verify they fail**

Run:

```bash
vitest run packages/core/test/context.test.ts packages/cli/test/context.test.ts
```

Expected: FAIL because `BuildOptions.enforcement` and `ContextArgs.platform` do not exist.

- [ ] **Step 6: Implement core context rendering**

Modify `packages/core/src/context.ts`.

Change imports to include the type:

```ts
import type { EnforcementSummary } from "./enforcement.js";
```

Change `BuildOptions` to:

```ts
export interface BuildOptions {
  format: "text" | "json";
  now: string;
  eventName?: string;
  enforcement?: EnforcementSummary;
}
```

Add this function after `renderResearchState`:

```ts
export function renderEnforcementSummary(summary: EnforcementSummary): string {
  const lines = [
    "[trellis-enforcement]",
    `Platform: ${summary.platform}`,
    `Mode: ${summary.mode}`,
    `Reason: ${summary.reason}`,
  ];
  if (summary.mode !== "hard") {
    lines.push("Strict sub-agent-only execution cannot be guaranteed on this platform.");
  }
  lines.push("[/trellis-enforcement]");
  return lines.join("\n");
}
```

Change the `text` construction inside `buildContext` to:

```ts
  const blocks = [
    `[workflow-state:${stateKey}]\n${wfBlock}\n[/workflow-state]`,
    renderResearchState(rs),
  ];
  if (opts.enforcement) blocks.push(renderEnforcementSummary(opts.enforcement));
  const text = blocks.join("\n\n");
```

- [ ] **Step 7: Implement CLI context platform resolution**

Modify `packages/cli/src/commands/context.ts` to this content:

```ts
import { buildContext, type EnforcementSummary } from "@research-copilot/core";
import { AI_TOOLS } from "@research-copilot/adapters";

export interface ContextArgs {
  repo: string;
  format: "text" | "json";
  now: string;
  eventName?: string;
  platform?: string;
}

export function enforcementForPlatform(platform = "claude-code"): EnforcementSummary {
  return AI_TOOLS[platform]?.enforcement ?? {
    platform,
    mode: "unavailable",
    reason: `unknown platform "${platform}"; enforcement capability cannot be determined`,
  };
}

export function runContext(args: ContextArgs): string {
  return buildContext(args.repo, {
    format: args.format,
    now: args.now,
    eventName: args.eventName,
    enforcement: enforcementForPlatform(args.platform),
  });
}
```

Modify the `context` command action in `packages/cli/src/program.ts`:

```ts
    .action((opts) => {
      process.stdout.write(runContext({
        repo,
        platform: opts.platform,
        format: opts.format,
        now: new Date().toISOString(),
        eventName: opts.event,
      }));
    });
```

- [ ] **Step 8: Run task tests**

Run:

```bash
vitest run packages/adapters/test/claude-code.test.ts packages/adapters/test/cursor.test.ts packages/adapters/test/windsurf.test.ts packages/core/test/context.test.ts packages/cli/test/context.test.ts
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
git add packages/adapters/src/registry.ts packages/adapters/test/claude-code.test.ts packages/adapters/test/cursor.test.ts packages/adapters/test/windsurf.test.ts packages/core/src/context.ts packages/core/test/context.test.ts packages/cli/src/commands/context.ts packages/cli/src/program.ts packages/cli/test/context.test.ts
git commit -m "feat: inject trellis enforcement capability"
```

---

### Task 3: Report Trellis enforcement mode in `rc doctor`

**Files:**
- Modify: `packages/cli/src/commands/doctor.ts`
- Modify: `packages/cli/src/program.ts`
- Test: `packages/cli/test/doctor.test.ts`

**Interfaces:**
- Consumes from Task 2: `AI_TOOLS[platform].enforcement`.
- Produces:
  - `DoctorOptions.platform?: string`.
  - Doctor report lines for hard, soft, and unknown enforcement capability.

- [ ] **Step 1: Write failing doctor tests**

Append these tests to `packages/cli/test/doctor.test.ts`:

```ts
  it("reports hard Trellis enforcement for Claude Code", () => {
    runInit({ repo, platforms: ["claude-code"], user: "tester", skipPlugin: true });
    const r = runner({}, { "npm list -g @research-copilot/plugin --json": new Error("missing") });

    const result = runDoctor(repo, { runner: r, platform: "claude-code" });

    expect(result.report.join("\n")).toContain("OK Research workflow enforcement: hard (claude-code)");
    expect(result.report.join("\n")).toContain("supports hooks and executable sub-agents");
  });

  it("reports soft Trellis enforcement for Windsurf", () => {
    runInit({ repo, platforms: ["windsurf"], user: "tester", skipPlugin: true });
    const r = runner({}, { "npm list -g @research-copilot/plugin --json": new Error("missing") });

    const result = runDoctor(repo, { runner: r, platform: "windsurf" });

    const report = result.report.join("\n");
    expect(report).toContain("WARN Research workflow enforcement: soft (windsurf)");
    expect(report).toContain("Strict sub-agent-only execution cannot be guaranteed on this platform.");
  });
```

- [ ] **Step 2: Run doctor tests to verify they fail**

Run:

```bash
vitest run packages/cli/test/doctor.test.ts
```

Expected: FAIL because `DoctorOptions.platform` and enforcement report lines do not exist.

- [ ] **Step 3: Implement doctor enforcement checks**

Modify `packages/cli/src/commands/doctor.ts`.

Add `AI_TOOLS` to imports:

```ts
import { kitRoot, MCP_SERVERS, AI_TOOLS } from "@research-copilot/adapters";
```

Add `platform?: string;` to `DoctorOptions`:

```ts
export interface DoctorOptions {
  strictPlugin?: boolean;
  fix?: boolean;
  skipPlugin?: boolean;
  runner?: CommandRunner;
  platform?: string;
}
```

Add this function after `checkCoreConfig`:

```ts
function checkEnforcement(platform = "claude-code"): Check[] {
  const entry = AI_TOOLS[platform];
  if (!entry) {
    return [{
      level: "FAIL",
      message: `Research workflow enforcement: unavailable (${platform}) — unknown platform`,
    }];
  }
  const level: Check["level"] = entry.enforcement.mode === "hard" ? "OK" : "WARN";
  const checks: Check[] = [{
    level,
    message: `Research workflow enforcement: ${entry.enforcement.mode} (${entry.enforcement.platform}) — ${entry.enforcement.reason}`,
  }];
  if (entry.enforcement.mode !== "hard") {
    checks.push({
      level: "WARN",
      message: "Strict sub-agent-only execution cannot be guaranteed on this platform.",
    });
  }
  return checks;
}
```

Change the checks assembly in `runDoctor`:

```ts
  const checks = [
    ...checkCoreConfig(repo),
    ...checkEnforcement(options.platform),
    ...checkPlugin(repo, options),
  ];
```

- [ ] **Step 4: Wire `--platform` into `doctor`**

Modify the `doctor` command in `packages/cli/src/program.ts`.

Add the option before `.action`:

```ts
    .option("--platform <p>", "platform", "claude-code")
```

Pass it into `runDoctor`:

```ts
        platform: opts.platform,
```

The full doctor command block should pass `fix`, `skipPlugin`, `strictPlugin`, and `platform`.

- [ ] **Step 5: Run task tests**

Run:

```bash
vitest run packages/cli/test/doctor.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add packages/cli/src/commands/doctor.ts packages/cli/src/program.ts packages/cli/test/doctor.test.ts
git commit -m "feat(cli): report trellis enforcement mode"
```

---

### Task 4: Align workflow and agent templates with Trellis node ownership

**Files:**
- Modify: `research-kit/workflow.md`
- Modify: `research-kit/agents/rc-plan.md`
- Modify: `research-kit/agents/rc-literature.md`
- Modify: `research-kit/agents/rc-ideation.md`
- Modify: `research-kit/agents/rc-experiment.md`
- Modify: `research-kit/agents/rc-writer.md`
- Modify: `research-kit/agents/rc-polisher.md`
- Modify: `research-kit/agents/rc-reviewer.md`
- Modify: `research-kit/agents/rc-rebuttal.md`
- Modify: `research-kit/agents/rc-verify.md`
- Modify: `research-kit/agents/rc-update-spec.md`
- Test: `packages/adapters/test/templates.test.ts`

**Interfaces:**
- Consumes from Task 1: executor ownership mapping vocabulary.
- Produces template language that tells the conductor and executors to use task node id, status, kind, ownership, handoff, gap recording, and no recursive `rc-*` dispatch.

- [ ] **Step 1: Write failing template tests**

Replace `packages/adapters/test/templates.test.ts` with this content:

```ts
import { describe, it, expect } from "vitest";
import * as fs from "node:fs"; import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KIT = path.resolve(__dirname, "../../../research-kit");
const agentFiles = [
  "rc-plan.md",
  "rc-literature.md",
  "rc-ideation.md",
  "rc-experiment.md",
  "rc-writer.md",
  "rc-polisher.md",
  "rc-reviewer.md",
  "rc-rebuttal.md",
  "rc-verify.md",
  "rc-update-spec.md",
];

describe("research-kit templates", () => {
  it("has workflow.md with all 5 state blocks", () => {
    const md = fs.readFileSync(path.join(KIT, "workflow.md"), "utf8");
    for (const s of ["no_task","planning","in_progress","verify","completed"])
      expect(md).toContain(`[workflow-state:${s}]`);
  });

  it("frames the workflow as Trellis conductor semantics", () => {
    const md = fs.readFileSync(path.join(KIT, "workflow.md"), "utf8");
    expect(md).toContain("MAIN SESSION = Trellis conductor");
    expect(md).toContain("Every research-domain action must belong to a .research/tasks/<id> task node");
    expect(md).toContain("If the user asks for research-domain work and there is no active task, create a task node first");
    expect(md).toContain("Do not consume the frontier yourself");
  });

  it("has 10 agent templates", () => {
    const agents = fs.readdirSync(path.join(KIT, "agents")).filter(f => f.endsWith(".md"));
    expect(agents.length).toBe(10);
  });

  it("all rc agents declare Trellis node ownership and recursion limits", () => {
    for (const file of agentFiles) {
      const md = fs.readFileSync(path.join(KIT, "agents", file), "utf8");
      expect(md).toContain("## Trellis Node Ownership");
      expect(md).toContain("You are a leaf executor for exactly one `.research/tasks/<id>` task node.");
      expect(md).toContain("Do NOT spawn other `rc-*` agents.");
      expect(md).toContain("Record gaps with `rc task add-gap <id> --desc \"<gap>\" --suggest <kind>`.");
    }
  });
});
```

- [ ] **Step 2: Run template tests to verify they fail**

Run:

```bash
vitest run packages/adapters/test/templates.test.ts
```

Expected: FAIL because the workflow and agents do not yet contain the Trellis language.

- [ ] **Step 3: Replace workflow state text**

Replace `research-kit/workflow.md` with this content:

```md
# Research Copilot Workflow

MAIN SESSION = Trellis conductor. Every research-domain action must belong to a .research/tasks/<id> task node and be executed by the legal rc-* leaf executor for that node's current lifecycle state and kind. The conductor advances the frontier; it does not consume the frontier itself.

[workflow-state:no_task]
No active task node. If the user asks for research-domain work and there is no active task, create a task node first with `rc task create --kind <k> --title "<t>"`, publish the orchestration task list, then dispatch `rc-plan`. If the user asks for repository development or general explanation, answer normally without creating a research task.
[/workflow-state]

[workflow-state:planning]
Active task is in PLANNING. The only legal research executor is `rc-plan`. Dispatch `rc-plan` with task id, kind, status, input context, expected `prd.md` / `execute.jsonl` / `verify.jsonl`, and the no-recursive-dispatch rule. When `rc-plan` returns with planning artifacts, run `rc task start <id>`.
[/workflow-state]

[workflow-state:in_progress]
Active task is IN PROGRESS. Dispatch the kind-specific leaf executor: literature → `rc-literature`, ideation → `rc-ideation`, experiment → `rc-experiment`, writing → `rc-writer`, polish → `rc-polisher`, review → `rc-reviewer`, rebuttal → `rc-rebuttal`. Provide `prd.md`, `execute.jsonl`, task id, ownership paths, and gap reporting expectations. Do not do domain work inline. When the executor returns, run `rc task verify <id>`.
[/workflow-state]

[workflow-state:verify]
Active task is in VERIFY. The only legal research executor is `rc-verify`. Dispatch `rc-verify` to run the kind's quality gate. On pass: `rc task complete <id>`. On fail: record gaps, run `rc task set-status <id> in_progress`, and dispatch the kind executor for repair.
[/workflow-state]

[workflow-state:completed]
Active task COMPLETED. The only legal research executor is `rc-update-spec`. Dispatch `rc-update-spec` to sediment learnings into `.research/spec/`, append a journal entry, and surface gap-driven recommendations. Then consult [research-state] to decide whether to create the next Trellis node or report completion to the user.
[/workflow-state]
```

- [ ] **Step 4: Add a consistent Trellis ownership section to every rc agent**

For each file listed in this task, insert the following section immediately after the existing `## Recursion Guard` section. Preserve the agent-specific content below it.

```md
## Trellis Node Ownership

You are a leaf executor for exactly one `.research/tasks/<id>` task node. The conductor must provide the task id, kind, current lifecycle status, input artifact paths, and expected output paths in the dispatch prompt.

You may only perform work that belongs to that node and your executor role. Do NOT spawn other `rc-*` agents. Do NOT advance lifecycle status yourself unless the dispatch explicitly instructs you to run a specific `rc task ...` command as part of your leaf work.

Before doing domain work, read the node's `prd.md` and `execute.jsonl` when they exist. Write only your owned outputs and include a handoff summary that names changed files, open questions, and verification evidence.

Record gaps with `rc task add-gap <id> --desc "<gap>" --suggest <kind>`. Gaps are Trellis graph growth signals, not chat-only notes.
```

For `research-kit/agents/rc-update-spec.md`, use the same text, but this sentence is more precise:

```md
You may write `.research/spec/**` only for the completed task node named in the dispatch prompt.
```

Place that sentence at the end of the inserted section in `rc-update-spec.md`.

- [ ] **Step 5: Correct stale gap examples in `rc-plan.md`**

In `research-kit/agents/rc-plan.md`, replace the three `rc task add-gap` examples so they include `<id>` as required by the actual CLI:

```bash
# Unclear target venue
rc task add-gap <id> --desc "Target venue not specified, assuming ICLR" --suggest literature

# Unclear success criteria
rc task add-gap <id> --desc "Success metric unclear, need user input" --suggest experiment

# Missing dependency
rc task add-gap <id> --desc "Spec for X missing, need to create .research/spec/X.md" --suggest writing
```

- [ ] **Step 6: Run template tests**

Run:

```bash
vitest run packages/adapters/test/templates.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add research-kit/workflow.md research-kit/agents/rc-plan.md research-kit/agents/rc-literature.md research-kit/agents/rc-ideation.md research-kit/agents/rc-experiment.md research-kit/agents/rc-writer.md research-kit/agents/rc-polisher.md research-kit/agents/rc-reviewer.md research-kit/agents/rc-rebuttal.md research-kit/agents/rc-verify.md research-kit/agents/rc-update-spec.md packages/adapters/test/templates.test.ts
git commit -m "docs(kit): align executors with trellis ownership"
```

---

### Task 5: Evolve the Python guard into a Trellis claim validator

**Files:**
- Modify: `self/hooks/scripts/research_copilot_guard.py`
- Create: `self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py`

**Interfaces:**
- Consumes: `.research/.runtime/active-task`, `.research/tasks/<id>/task.json`, hook payload fields `tool_name`, `tool_input`, `agent_id`, `agent_type`, and `transcript_path`.
- Produces:
  - Support for both `rc-*` and `copilot-*` executor names.
  - Deny messages based on active Trellis node status and kind.
  - Enforcement event JSONL entries at `.research/.runtime/enforcement-events.jsonl`.

- [ ] **Step 1: Write failing Python guard tests**

Create `self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py` with this content:

```py
import json
from pathlib import Path

import research_copilot_guard as guard


def write_task(repo: Path, task_id: str, kind: str, status: str) -> None:
    task_dir = repo / ".research" / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    runtime = repo / ".research" / ".runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "active-task").write_text(task_id, encoding="utf-8")
    (task_dir / "task.json").write_text(json.dumps({
        "id": task_id,
        "title": "node",
        "kind": kind,
        "status": status,
        "priority": "P2",
        "children": [],
        "depends_on": [],
        "gaps": [],
        "created": "2026-06-22T00:00:00Z",
        "updated": "2026-06-22T00:00:00Z",
    }), encoding="utf-8")


def test_no_active_node_denies_research_mcp_and_logs_event(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"tool_name": "mcp__research-scholar__scholar_search", "tool_input": {"query": "diffusion"}}

    decision = guard._decide(payload)

    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "create a Trellis task node first" in decision["systemMessage"]
    event_path = tmp_path / ".research" / ".runtime" / "enforcement-events.jsonl"
    event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["event"] == "main_attempted_leaf_work_without_active_node"
    assert event["decision"] == "deny"


def test_planning_node_allows_rc_plan_and_denies_rc_literature(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-lit", "literature", "planning")

    allowed = guard._decide({
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "rc-plan"},
        "transcript_path": None,
    })
    denied = guard._decide({
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "rc-literature"},
        "transcript_path": None,
    })

    assert allowed["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Legal executor is rc-plan" in denied["systemMessage"]


def test_in_progress_node_allows_kind_executor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-lit", "literature", "in_progress")

    allowed = guard._decide({
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "rc-literature"},
        "transcript_path": None,
    })

    assert allowed["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_main_session_artifact_write_uses_active_node_expected_executor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-write", "writing", "in_progress")

    decision = guard._decide({
        "tool_name": "Write",
        "tool_input": {"file_path": "sections/method.tex"},
    })

    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Legal executor is rc-writer" in decision["systemMessage"]


def test_rc_subagent_with_agent_id_is_exempt_for_leaf_tools(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_task(tmp_path, "2026-06-22-lit", "literature", "in_progress")

    decision = guard._decide({
        "agent_id": "agent-1",
        "agent_type": "rc-literature",
        "tool_name": "mcp__research-scholar__scholar_search",
        "tool_input": {"query": "diffusion"},
    })

    assert decision["hookSpecificOutput"]["permissionDecision"] == "allow"
```

- [ ] **Step 2: Run Python tests to verify they fail**

Run:

```bash
python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py
```

Expected: FAIL because the guard does not yet load Trellis tasks, does not know `rc-*`, and does not log enforcement events.

- [ ] **Step 3: Add Trellis constants and active task loading**

Modify `self/hooks/scripts/research_copilot_guard.py`.

Replace the `COPILOT_SUBAGENT_PREFIX` constant with these constants:

```py
COPILOT_SUBAGENT_PREFIX = "copilot-"
RC_SUBAGENT_PREFIX = "rc-"
RESEARCH_EXECUTOR_PREFIXES = (COPILOT_SUBAGENT_PREFIX, RC_SUBAGENT_PREFIX)
KIND_EXECUTOR = {
    "literature": "rc-literature",
    "ideation": "rc-ideation",
    "experiment": "rc-experiment",
    "writing": "rc-writer",
    "polish": "rc-polisher",
    "review": "rc-reviewer",
    "rebuttal": "rc-rebuttal",
}
COPILOT_TO_RC = {
    "copilot-literature": "rc-literature",
    "copilot-ideation": "rc-ideation",
    "copilot-experiment": "rc-experiment",
    "copilot-writer": "rc-writer",
    "copilot-polisher": "rc-polisher",
    "copilot-reviewer": "rc-reviewer",
    "copilot-rebuttal": "rc-rebuttal",
    "copilot-verify": "rc-verify",
    "copilot-update-spec": "rc-update-spec",
}
```

Add these helpers after `_path_matches`:

```py
def _canonical_executor(name: str) -> str:
    return COPILOT_TO_RC.get(name, name)


def _is_research_executor(name: str) -> bool:
    return name.startswith(RESEARCH_EXECUTOR_PREFIXES)


def _runtime_dir() -> Path:
    return Path.cwd() / ".research" / ".runtime"


def _load_active_task() -> dict[str, Any] | None:
    active_path = _runtime_dir() / "active-task"
    if not active_path.is_file():
        return None
    task_id = active_path.read_text(encoding="utf-8", errors="replace").strip()
    if not task_id:
        return None
    task_path = Path.cwd() / ".research" / "tasks" / task_id / "task.json"
    if not task_path.is_file():
        return None
    try:
        task = json.loads(task_path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    return task if isinstance(task, dict) else None


def _expected_executor(task: dict[str, Any]) -> str | None:
    status = task.get("status")
    kind = task.get("kind")
    if status == "planning":
        return "rc-plan"
    if status == "verify":
        return "rc-verify"
    if status == "completed":
        return "rc-update-spec"
    if status == "in_progress":
        return KIND_EXECUTOR.get(str(kind))
    return None
```

- [ ] **Step 4: Add event logging helper**

Add this helper after `_expected_executor`:

```py
def _log_event(event: dict[str, Any]) -> None:
    runtime = _runtime_dir()
    runtime.mkdir(parents=True, exist_ok=True)
    path = runtime / "enforcement-events.jsonl"
    base = {
        "platform": "claude-code",
        "mode": "hard",
    }
    base.update(event)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(base, ensure_ascii=False, sort_keys=True) + "\n")
```

- [ ] **Step 5: Update sub-agent exemption**

Replace `is_exempt_subagent` with:

```py
def is_exempt_subagent(payload: dict[str, Any]) -> bool:
    if is_main_session(payload):
        return False
    return _is_research_executor(str(payload.get("agent_type") or ""))
```

This preserves the conservative rule: no `agent_id` means main session.

- [ ] **Step 6: Add Trellis dispatch validation**

Replace `check_m2_task_list` with this implementation:

```py
def check_m2_task_list(tool_name: str, tool_input: dict[str, Any],
                       transcript_path: str | None) -> str | None:
    """M2 task-list gate: deny research executor dispatch without Trellis legality."""
    if tool_name != "Agent":
        return None
    sub_type = str((tool_input or {}).get("subagent_type", ""))
    if not _is_research_executor(sub_type):
        return None

    task = _load_active_task()
    if task is None:
        _log_event({
            "event": "dispatch_without_active_node",
            "tool": "Agent",
            "subagent_type": sub_type,
            "decision": "deny",
        })
        return ("Blocked by research-copilot-guard (Trellis dispatch gate): "
                "research executor dispatch requires an active .research/tasks/<id> task node. "
                "Create a Trellis task node first with `rc task create --kind <kind> --title \"<title>\"`.")

    expected = _expected_executor(task)
    actual = _canonical_executor(sub_type)
    if expected and actual == expected:
        return None

    _log_event({
        "event": "executor_mismatch",
        "taskId": task.get("id"),
        "status": task.get("status"),
        "kind": task.get("kind"),
        "tool": "Agent",
        "subagent_type": sub_type,
        "expectedExecutor": expected,
        "decision": "deny",
    })
    return (f"Blocked by research-copilot-guard (Trellis dispatch gate): active task "
            f"{task.get('id')} is status={task.get('status')} kind={task.get('kind')}. "
            f"Legal executor is {expected}; cannot dispatch {sub_type}.")
```

- [ ] **Step 7: Update main-session leaf-work messages to use the active node**

Add this helper before `check_m1_delegation`:

```py
def _deny_leaf_work(event_name: str, tool_name: str, default_executor: str, reason: str) -> str:
    task = _load_active_task()
    if task is None:
        _log_event({
            "event": "main_attempted_leaf_work_without_active_node",
            "tool": tool_name,
            "decision": "deny",
        })
        return ("Blocked by research-copilot-guard (Trellis claim gate): the conductor "
                "cannot perform research-domain leaf work without an active task node. "
                "Create a Trellis task node first with `rc task create --kind <kind> --title \"<title>\"`.")

    expected = _expected_executor(task) or default_executor
    _log_event({
        "event": event_name,
        "taskId": task.get("id"),
        "status": task.get("status"),
        "kind": task.get("kind"),
        "tool": tool_name,
        "decision": "deny",
        "expectedExecutor": expected,
    })
    return (f"Blocked by research-copilot-guard (Trellis claim gate): active task "
            f"{task.get('id')} is status={task.get('status')} kind={task.get('kind')}. "
            f"Legal executor is {expected}. The conductor must not do this leaf work inline. "
            f"{reason}")
```

Then replace the three existing M1 return messages with calls to `_deny_leaf_work`:

```py
return _deny_leaf_work(
    "main_attempted_experiment",
    tool_name,
    "rc-experiment",
    "Delegate experiment work to the legal task executor.",
)
```

```py
return _deny_leaf_work(
    "main_attempted_literature_search",
    tool_name,
    "rc-literature",
    "Delegate literature search to the legal task executor.",
)
```

```py
return _deny_leaf_work(
    "main_attempted_artifact_write",
    tool_name,
    "rc-writer",
    "Delegate artifact writing to the legal task executor.",
)
```

Keep the existing read-only, conductor-owned `.copilot/state.md`, and `.copilot/decisions.md` allowances.

- [ ] **Step 8: Include current MCP tool names in the research MCP prefixes**

Update `RESEARCH_MCP_PREFIXES` to include the MCP names available in this repository:

```py
RESEARCH_MCP_PREFIXES = (
    "mcp__arxiv-search__",
    "mcp__arxivsub-search__",
    "mcp__google-scholar__",
    "mcp__dblp-bib__",
    "mcp__research-scholar__scholar_search",
    "mcp__research-scholar__bibtex",
    "mcp__research-scholar__scholar_metadata",
)
```

- [ ] **Step 9: Run Python guard tests**

Run:

```bash
python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py
```

Expected: PASS.

- [ ] **Step 10: Commit**

Run:

```bash
git add self/hooks/scripts/research_copilot_guard.py self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py
git commit -m "feat(hooks): validate trellis executor claims"
```

---

### Task 6: Register sub-agent ownership and stop hooks in installer and plugin hook specs

**Files:**
- Modify: `self/install.py`
- Create: `self/hooks/copilot-write-guard.json`
- Create: `self/hooks/copilot-subagent-stop.json`
- Modify: `self/hooks/tests/integration_run.ps1`

**Interfaces:**
- Consumes existing scripts: `self/hooks/scripts/copilot_write_guard.py` and `self/hooks/scripts/copilot_subagent_stop.py`.
- Produces installer registration for:
  - PreToolUse matcher `Write|Edit` running `copilot_write_guard.py`.
  - SubagentStop hook running `copilot_subagent_stop.py`.

- [ ] **Step 1: Add hook discovery JSON specs**

Create `self/hooks/copilot-write-guard.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python self/hooks/scripts/copilot_write_guard.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Create `self/hooks/copilot-subagent-stop.json`:

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python self/hooks/scripts/copilot_subagent_stop.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Add installer constants**

In `self/install.py`, add these constants after `LOOP_ARMER_SCRIPT`:

```py
COPILOT_WRITE_GUARD_SCRIPT = SELF_DIR / "hooks" / "scripts" / "copilot_write_guard.py"
COPILOT_SUBAGENT_STOP_SCRIPT = SELF_DIR / "hooks" / "scripts" / "copilot_subagent_stop.py"
```

- [ ] **Step 3: Add installer registration functions**

Add these functions after `register_research_copilot_guard`:

```py
def register_copilot_write_guard(target: Path, dry_run: bool) -> None:
    step("Step 3g/5: register copilot write guard PreToolUse hook")
    if not COPILOT_WRITE_GUARD_SCRIPT.is_file():
        warn(f"copilot write guard script missing: {COPILOT_WRITE_GUARD_SCRIPT}; skipping")
        return
    settings_dir = target / ".claude"
    settings_path = settings_dir / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])
    hook_cmd = f'python "{COPILOT_WRITE_GUARD_SCRIPT.resolve()}"'.replace("\\", "/")
    for block in pre_tool:
        if block.get("matcher") == "Write|Edit":
            for hk in block.get("hooks", []):
                if "copilot_write_guard.py" in hk.get("command", ""):
                    info("copilot_write_guard already registered; skipping.")
                    return
    pre_tool.append({
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}],
    })
    if dry_run:
        return
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def register_copilot_subagent_stop(target: Path, dry_run: bool) -> None:
    step("Step 3h/5: register copilot subagent stop hook")
    if not COPILOT_SUBAGENT_STOP_SCRIPT.is_file():
        warn(f"copilot subagent stop script missing: {COPILOT_SUBAGENT_STOP_SCRIPT}; skipping")
        return
    settings_dir = target / ".claude"
    settings_path = settings_dir / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    hooks = settings.setdefault("hooks", {})
    stop_hooks = hooks.setdefault("SubagentStop", [])
    hook_cmd = f'python "{COPILOT_SUBAGENT_STOP_SCRIPT.resolve()}"'.replace("\\", "/")
    for block in stop_hooks:
        for hk in block.get("hooks", []):
            if "copilot_subagent_stop.py" in hk.get("command", ""):
                info("copilot_subagent_stop already registered; skipping.")
                return
    stop_hooks.append({
        "hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}],
    })
    if dry_run:
        return
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Call installer registration functions**

In the main installer flow near the existing hook registration calls, add:

```py
    register_copilot_write_guard(target, args.dry_run)
    register_copilot_subagent_stop(target, args.dry_run)
```

Use the same `target` and `args.dry_run` variables already used by the other registration calls.

- [ ] **Step 5: Extend smoke script assertions**

Append these checks to `self/hooks/tests/integration_run.ps1`:

```powershell
$writeSpec = Join-Path $Root "self/hooks/copilot-write-guard.json"
$stopSpec = Join-Path $Root "self/hooks/copilot-subagent-stop.json"
if (-not (Test-Path $writeSpec)) { throw "missing copilot-write-guard.json" }
if (-not (Test-Path $stopSpec)) { throw "missing copilot-subagent-stop.json" }
(Get-Content $writeSpec -Raw | ConvertFrom-Json).hooks.PreToolUse | Out-Null
(Get-Content $stopSpec -Raw | ConvertFrom-Json).hooks.SubagentStop | Out-Null
```

- [ ] **Step 6: Run hook smoke checks**

Run:

```bash
pwsh -File self/hooks/tests/integration_run.ps1
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add self/install.py self/hooks/copilot-write-guard.json self/hooks/copilot-subagent-stop.json self/hooks/tests/integration_run.ps1
git commit -m "feat(hooks): register subagent ownership gates"
```

---

### Task 7: Full validation and final consistency pass

**Files:**
- Modify only files required to fix failures found by the commands in this task.

**Interfaces:**
- Consumes all tasks above.
- Produces a green build/test run and a final consistency commit if fixes are required.

- [ ] **Step 1: Run TypeScript build**

Run:

```bash
pnpm -r build
```

Expected: all packages build successfully. If TypeScript reports a type error, fix the named file and rerun the same command.

- [ ] **Step 2: Run Vitest suite**

Run:

```bash
vitest run
```

Expected: all Vitest tests pass. If a test fails, fix the implementation or the test expectation so it matches the approved spec, then rerun `vitest run`.

- [ ] **Step 3: Run Python hook tests**

Run:

```bash
python -m pytest self/hooks/scripts/__tests__ self/hooks/tests
```

Expected: all Python hook tests pass. If pytest reports missing dependencies in this environment, run the narrower tests changed by this plan and record the unavailable dependency in the final report:

```bash
python -m pytest self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py
pwsh -File self/hooks/tests/integration_run.ps1
```

- [ ] **Step 4: Run package CI command**

Run:

```bash
pnpm run ci
```

Expected: build and Vitest pass together.

- [ ] **Step 5: Confirm generated CLI kit was not hand-edited**

Run:

```bash
git status --short
```

Expected: no paths under `packages/cli/research-kit/` appear. If they appear because a build copied templates there, do not edit them by hand; either leave generated build output out of the commit or regenerate through the package build path and explain it in the final report.

- [ ] **Step 6: Commit final fixes if any were needed**

If `git status --short` shows fixes from this validation task, run:

```bash
git add packages/core/src/enforcement.ts packages/core/src/index.ts packages/core/test/enforcement.test.ts packages/adapters/src/registry.ts packages/adapters/test/claude-code.test.ts packages/adapters/test/cursor.test.ts packages/adapters/test/windsurf.test.ts packages/core/src/context.ts packages/core/test/context.test.ts packages/cli/src/commands/context.ts packages/cli/src/program.ts packages/cli/test/context.test.ts packages/cli/src/commands/doctor.ts packages/cli/test/doctor.test.ts research-kit/workflow.md research-kit/agents/rc-plan.md research-kit/agents/rc-literature.md research-kit/agents/rc-ideation.md research-kit/agents/rc-experiment.md research-kit/agents/rc-writer.md research-kit/agents/rc-polisher.md research-kit/agents/rc-reviewer.md research-kit/agents/rc-rebuttal.md research-kit/agents/rc-verify.md research-kit/agents/rc-update-spec.md packages/adapters/test/templates.test.ts self/hooks/scripts/research_copilot_guard.py self/hooks/scripts/__tests__/test_research_copilot_guard_trellis.py self/install.py self/hooks/copilot-write-guard.json self/hooks/copilot-subagent-stop.json self/hooks/tests/integration_run.ps1
git commit -m "test: validate trellis enforcement integration"
```

If there are no validation fixes, do not create an empty commit.
