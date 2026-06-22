# Trellis-Aligned Sub-agent Enforcement Design

- Date: 2026-06-22
- Status: Draft, awaits user review
- Scope: Research workflow execution only. Enforce that research-domain work is represented as Trellis task nodes and executed by the node's legal sub-agent executor, while the main conversation remains the conductor.
- Predecessors:
  - `2026-05-30-main-session-conductor-and-plugin-deps-design.md` promoted the conductor to the main session and introduced main-session hard-deny patterns.
  - `2026-05-24-copilot-subagent-guard-design.md` introduced sub-agent write partitioning and handoff freshness gates.
  - `2026-05-21-research-copilot-workflow-enforcement-design.md` introduced the first workflow enforcement hook pattern.

---

## 1. Problem Statement

The project already states the intended boundary: the main conversation orchestrates lifecycle and reporting, and `rc-*` / `copilot-*` executors do the research-domain work. In practice, that boundary can still feel like a generic deny-list: "main session cannot call these tools or write these paths." That framing is too weak and too detached from Research Copilot's Trellis model.

The desired invariant is stronger and more structural:

> Every research-domain action must belong to a `.research/tasks/<id>` task node, and must be performed by the executor that is legal for that node's current lifecycle state and kind.

The main session is therefore not merely "forbidden from doing search or writing." It is the Trellis conductor: it grows and advances the task graph, selects the frontier node's executor, verifies handoff, and reports to the user. It does not consume the frontier itself.

---

## 2. Locked Decisions

| # | Decision |
|---|---|
| D1 | Scope is **research workflow tasks only**: literature, ideation, experiment, writing, polish, review, rebuttal, verification, and spec consolidation. |
| D2 | Repository development tasks remain allowed in the main session: code edits, tests, docs, hook debugging, and git commit are not research-domain leaf work. |
| D3 | Enforcement strategy is **hybrid by platform capability**: class-1 platforms get hard-deny enforcement; class-2 platforms get explicit soft enforcement with risk reporting. |
| D4 | If a user asks for research-domain work with no active task, the conductor should **auto-create a task node** rather than ask the user to create one manually. |
| D5 | Enforcement must be Trellis-aligned: task node, lifecycle status, kind, executor claim, and artifact ownership are the source of truth. Tool/path deny-lists are implementation details. |

---

## 3. Goal and Non-goals

### Goal

Make research-domain execution sub-agent-only by enforcing Trellis semantics:

1. Research-domain requests become task nodes.
2. The main session can only conduct the graph and lifecycle.
3. Each node status has exactly one legal executor family.
4. Artifacts are owned by the current node and legal executor.
5. Gaps become structured Trellis growth signals, not free-form chat notes.
6. Platform capability is visible: hard where hooks can enforce, soft where they cannot.

### Non-goals

- Do not change the existing lifecycle states: `planning -> in_progress -> verify -> completed`.
- Do not extend this enforcement to repository development work.
- Do not pretend Cursor/Windsurf can provide hard enforcement when the platform lacks the required hooks or agents.
- Do not let executors recursively dispatch other `rc-*` executors.
- Do not hand-edit generated `packages/cli/research-kit/` output.
- Do not change release version numbers by hand.

---

## 4. Trellis Execution Model

### 4.1 The task node is the enforcement unit

Every research-domain action must answer four questions:

1. Which `.research/tasks/<id>` node does this belong to?
2. What is that node's current status?
3. Which executor is legal for `status + kind`?
4. Does this tool call or artifact write fall within that executor's ownership?

If any answer is missing, the action is not a legal Trellis execution. On class-1 platforms, that means hard deny. On class-2 platforms, it means soft warning plus explicit risk reporting.

### 4.2 The conductor advances the frontier

The main conversation is the conductor. It may perform graph and lifecycle operations:

- `rc task current`
- `rc task create --kind <kind> --title <title> [...]`
- `rc task start <id>`
- `rc task verify <id>`
- `rc task complete <id>`
- `rc task set-status <id> <status>` when the transition is allowed by `TRANSITIONS`
- `rc task add-gap <id> --desc <description> --suggest <kind>`
- read context, task metadata, workflow state, and executor handoff
- dispatch the legal executor for the active frontier node
- summarize executor results and request user confirmation where needed

The conductor does not own leaf research artifacts. It is not a literature worker, idea generator, experiment runner, paper writer, reviewer, rebuttal drafter, verifier, or spec consolidator.

### 4.3 Legal executor by status and kind

| Node status | Node kind | Legal executor | Owned work |
|---|---|---|---|
| `planning` | any | `rc-plan` | Convert a fuzzy node into `prd.md`, `execute.jsonl`, and `verify.jsonl`. |
| `in_progress` | `literature` | `rc-literature` | Literature search, baseline tracking, paper summaries, bibliography candidates. |
| `in_progress` | `ideation` | `rc-ideation` | Ideas, novelty analysis, candidate pipelines. |
| `in_progress` | `experiment` | `rc-experiment` | Experiment execution, metrics, ablations, result artifacts. |
| `in_progress` | `writing` | `rc-writer` | Draft text, section artifacts, citation integration. |
| `in_progress` | `polish` | `rc-polisher` | Style/register polishing of writing artifacts. |
| `in_progress` | `review` | `rc-reviewer` | Critical review, gap extraction, reviewer notes. |
| `in_progress` | `rebuttal` | `rc-rebuttal` | Response drafting and rebuttal artifacts. |
| `verify` | any | `rc-verify` | Verification report and gate outcome. |
| `completed` | any | `rc-update-spec` | Cross-task knowledge consolidation into `.research/spec/`. |

This table should become the shared source for workflow wording, context injection, and guard behavior. Duplicating the mapping across CLAUDE.md, workflow text, hook scripts, and tests invites drift.

---

## 5. Request Routing and Automatic Node Creation

### 5.1 No active task

When the user asks for research-domain work and there is no active task:

1. The conductor classifies the request into a `Kind`.
2. The conductor creates a task node with `status=planning`:

   ```bash
   rc task create --kind <kind> --title "<derived title>"
   ```

3. The conductor publishes a visible task list for orchestration.
4. The conductor dispatches `rc-plan` with the task id, kind, current status, input context, expected outputs, and recursion prohibition.
5. After `rc-plan` completes, the conductor runs `rc task start <id>` and dispatches the kind-specific executor.

This is not a convenience shortcut. It is how a new Trellis frontier node is born from a direct user request.

If the request is ambiguous enough that `Kind` cannot be selected, the conductor asks one minimal clarifying question and does no research-domain leaf work.

### 5.2 Existing active task

When a task is active, the conductor follows the node lifecycle:

- `planning`: dispatch `rc-plan`; then `rc task start <id>`.
- `in_progress`: dispatch the kind-specific executor; then `rc task verify <id>`.
- `verify`: dispatch or run verification; pass leads to `rc task complete <id>`, failure returns to `in_progress` for executor repair.
- `completed`: dispatch `rc-update-spec`, then use `[research-state]` recommendations and recorded gaps to decide whether to create another node or report completion.

---

## 6. Artifact Ownership

### 6.1 Canonical node-owned layout

The canonical ownership model is centered on `.research/tasks/<id>/`:

```text
.research/tasks/<id>/
  task.json          # conductor/lifecycle metadata, preferably via rc task commands
  prd.md             # rc-plan
  execute.jsonl      # rc-plan
  verify.jsonl       # rc-plan
  artifacts/         # kind executor outputs
  research/          # kind executor research material
  verify/            # rc-verify output
```

Cross-node consolidation is owned by `rc-update-spec`:

```text
.research/spec/      # completed-stage consolidation only
```

### 6.2 Compatibility paths

Existing paper-workflow paths remain supported, but they must be mapped to Trellis ownership rather than treated as free-standing files:

```text
.copilot/*.md
.copilot/reviews/**
sections/*.tex
references.bib
```

Examples:

- `.copilot/literature.md` is literature-executor owned.
- `.copilot/ideas.md` is ideation-executor owned.
- `.copilot/experiments.md` is experiment-executor owned.
- `.copilot/reviews/**` is review-executor owned.
- `sections/*.tex` is writer/polisher/rebuttal owned depending on the current node kind and status.
- `references.bib` is writer/literature owned only when the active node's executor claim permits it.
- `.research/spec/**` is owned by `rc-update-spec`, not by the conductor.

Path matching remains necessary, but the policy reason is node ownership.

---

## 7. Class-1 Hard Enforcement

Class-1 platforms are those with enough hooks and agent capability to enforce claims, such as Claude Code, Codex, OpenCode, and Gemini.

### 7.1 Guard responsibility

The guard validates Trellis claims:

- main session attempts research-domain leaf work without an executor claim: deny;
- executor does not match active node `status + kind`: deny;
- executor writes outside its node ownership: deny;
- executor exits without fresh node-owned output or handoff: block with a limited fuse;
- research-domain action appears with no active node: deny and suggest `rc task create`.

Error messages should be Trellis-specific. Example:

```text
Denied: active task <id> is status=planning kind=literature.
Legal executor is rc-plan. Dispatch rc-plan or advance the lifecycle before invoking rc-literature.
```

### 7.2 Main-session allowance

The main session is still allowed to perform repository development and conductor work:

- inspect source files;
- modify implementation, tests, docs, and specs;
- run `pnpm -r build`, `vitest run`, and similar development validation;
- commit local changes;
- invoke `rc task ...` lifecycle commands;
- read handoff and metadata.

The guard should not confuse "developing Research Copilot" with "using Research Copilot to do research."

### 7.3 Dispatch contract

A legal executor dispatch from the conductor must include enough Trellis claim context for the executor and guard to agree on ownership:

- task id;
- kind;
- lifecycle status;
- executor role;
- input artifact paths;
- expected output/handoff paths;
- instruction that the executor is a leaf worker and must not dispatch other `rc-*` executors;
- gap reporting expectations.

If the conductor attempts to dispatch without a visible task list or without active node context, the guard denies with instructions to publish the orchestration plan first.

---

## 8. Class-2 Soft Enforcement

Cursor and Windsurf lack the full hook/agent enforcement surface. They must not report strict enforcement.

`rc doctor` should report the actual mode, for example:

```text
Research workflow enforcement: soft
Reason: platform "windsurf" does not support PreToolUse/SubagentStop hooks.
Strict sub-agent-only execution cannot be guaranteed on this platform.
```

`rc context` should inject a concise enforcement summary so the main session knows whether it is under hard or soft enforcement.

Class-2 behavior:

- keep the same Trellis conductor instructions;
- warn when a research-domain request should become a task node;
- record risk/violation events where possible;
- never claim that hard-deny protection exists.

---

## 9. Gaps as Trellis Growth Signals

Executor gaps should not remain only in prose. When an executor identifies missing work, the conductor records it structurally:

```bash
rc task add-gap <id> --desc "<gap>" --suggest <kind>
```

`research-state.ts` then uses gaps as next-node recommendations. After a node reaches `completed` and `rc-update-spec` consolidates learning, the conductor can create child or sibling nodes from those gaps.

This keeps Trellis growth explicit: gaps expand the task graph rather than becoming untracked chat suggestions.

---

## 10. Observability

Violations should be logged as Trellis enforcement events, not only as hook stderr. Recommended file:

```text
.research/.runtime/enforcement-events.jsonl
```

Example event:

```json
{
  "time": "2026-06-22T00:00:00Z",
  "platform": "claude-code",
  "mode": "hard",
  "event": "main_attempted_leaf_work",
  "taskId": "lit-001",
  "status": "in_progress",
  "kind": "literature",
  "tool": "mcp__research-scholar__scholar_search",
  "decision": "deny",
  "expectedExecutor": "rc-literature"
}
```

`rc doctor` and `rc context` can summarize recent hard denies and soft warnings. The user should be able to tell whether the system blocked a violation, warned about a risk, or was running on a platform that cannot enforce.

---

## 11. Implementation Touchpoints

Likely files to change during implementation:

- `packages/core/src/types.ts` — add enforcement mode / platform capability / executor ownership types as needed.
- `packages/core/src/research-state.ts` — surface frontier, gaps, and enforcement mode in recommendations.
- `packages/core/src/context.ts` — inject Trellis enforcement summary.
- `packages/core/src/enforcement.ts` or equivalent — centralize pure functions such as `expectedExecutorFor(task)`, `canConductorAct(...)`, `canExecutorClaim(...)`, and `canWriteArtifact(...)`.
- `packages/cli/src/commands/context.ts` — expose enforcement summary in text and JSON outputs.
- `packages/cli/src/commands/doctor.ts` — report hard/soft/unavailable mode and reasons.
- `packages/adapters/src/registry.ts` — make platform enforcement capability explicit.
- `research-kit/workflow.md` — rewrite the conductor guidance around Trellis node semantics.
- `research-kit/agents/rc-*.md` — declare node ownership, expected inputs/outputs, gap reporting, and recursion prohibition.
- hook scripts and plugin source under `self/hooks/` if the current shipped plugin path still uses those scripts — evolve deny-list checks into Trellis claim validation.
- tests for pure enforcement logic, CLI context/doctor output, and hook behavior.

Generated `packages/cli/research-kit/` should not be edited by hand.

---

## 12. Test Strategy

Tests should assert Trellis semantics rather than only string matching.

1. **No active node**
   - main session research MCP call is denied on class-1 platforms;
   - response suggests `rc task create`;
   - direct research-domain request follows the auto-create path.

2. **Planning node**
   - `rc-plan` is allowed;
   - kind executor is denied;
   - conductor direct write to planning artifacts is denied unless performed through lifecycle metadata commands.

3. **In-progress node**
   - matching kind executor is allowed;
   - mismatched executor is denied;
   - main session leaf work is denied.

4. **Verify node**
   - `rc-verify` is allowed;
   - kind executor is denied until lifecycle returns to `in_progress`.

5. **Completed node**
   - `rc-update-spec` is allowed;
   - conductor writes to `.research/spec/**` are denied.

6. **Artifact ownership**
   - node-owned paths map to the active node and legal executor;
   - compatibility paths under `.copilot/`, `sections/*.tex`, and `references.bib` map correctly;
   - repository development files remain writable by the main session.

7. **Platform mode**
   - class-1 reports hard enforcement;
   - class-2 reports soft enforcement with reason;
   - context and doctor never overstate enforcement strength.

---

## 13. Acceptance Criteria

- Research-domain user requests with no active task result in a new Trellis task node, not inline leaf work.
- Main-session research-domain leaf work is hard-denied on class-1 platforms.
- Executor dispatch legality is determined by active node `status + kind`.
- Artifact writes are validated through node/executor ownership.
- Class-2 platforms visibly report soft enforcement and cannot be mistaken for hard enforcement.
- Gap reporting feeds `research-state` recommendations as task-graph growth signals.
- Tests cover lifecycle state, executor mapping, artifact ownership, and platform mode.
