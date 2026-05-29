# Main-Session Conductor + Plugin-Dependency Migration Design

- Date: 2026-05-30
- Status: Draft, awaits user review
- Scope: Two independent change surfaces shipped under one spec.
  - **Part A — Main-session conductor.** Move the research-pipeline conductor from a dispatchable `research-copilot` sub-agent onto the **main session itself**, so the constraint applies from every interaction onward without explicit `@research-copilot` invocation, and the conductor (not the first sub-agent) always owns the task list.
  - **Part B — Plugin-dependency migration.** Stop vendoring six third-party sources that are themselves Claude plugins; declare them as plugin `dependencies` instead.
- Predecessors (this spec supersedes the conductor-location decision in the first two):
  - `2026-05-27-research-copilot-delegate-only-design.md` (made `research-copilot` a tools-restricted, delegate-only sub-agent; added `PLAN_PUBLISHED` + guard pattern 7)
  - `2026-05-23-self-agent-refactor-design.md` (introduced `PIPELINE-OS.md`, the 8 sub-agents, the dispatch-reminder hook)
  - `2026-05-21-research-copilot-workflow-enforcement-design.md` (introduced `research_copilot_guard.py`)

---

## 1. Problem Statement

Two complaints, two root causes.

### Complaint 1 — The conductor loses its grip after each staged result

`research-copilot` is a **dispatchable sub-agent** (`Agent(subagent_type='research-copilot')`). Its entire state machine and its `research_copilot_guard.py` PreToolUse enforcement apply **only while research-copilot is the active sub-agent**. A sub-agent is ephemeral: the moment it returns a staged result to show the user, control falls back to the **main session** — the only context that persists across the whole conversation — which has:

- no state machine,
- no delegation enforcement (the guard `is_copilot_agent()`-gates itself to a no-op for the main session),
- no task-list discipline.

So after every staged hand-back the pipeline is unconstrained until the user *explicitly* re-invokes the conductor. The only main-session-facing governor today is `user_prompt_dispatch_reminder.py`, and it is doubly weak: it is a **soft text nudge** (not a block), and it **suppresses itself** on exactly the prompts a returning user types — `"下一步"`, `"what's next"`, anything starting with `/` or `@` (see `ALLOWLIST_PHRASES` / `ALLOWLIST_PREFIXES` in that script).

### Complaint 2 — The main agent builds no task list, so "what's next" is decided by the first sub-agent

Task-list discipline exists only **inside** the `research-copilot` sub-agent, and only in **Mode B** (`PLAN_PUBLISHED` state, enforced by guard pattern 7). Mode A (single routing dispatch) is exempt, and the main session has no task-list discipline at all. Consequently, when a sub-agent returns and recommends a next step, nothing forces that recommendation to pass through a conductor-owned plan — the first sub-agent's closing suggestion becomes the de-facto plan.

### Complaint 3 — Six dependencies are vendored despite already being Claude plugins

`scripts/build_copilot_workspace.py` reads `skill.txt` / `agent.txt` / `hook.txt` and **vendors ~280 skills** from `third_party/` into the `deploy` branch as one monolithic plugin. Six of those sources are *already* standalone Claude plugins with their own `plugin.json` / `marketplace.json`. Per `https://code.claude.com/docs/zh-CN/plugin-dependencies`, a plugin can declare `dependencies` and let Claude Code resolve/install them, instead of copying their files.

---

## 2. Platform Facts That Constrain the Design

These were verified during the brainstorming interview and are load-bearing — the design is shaped around them.

1. **No hook can auto-invoke an agent.** Claude Code has no mechanism that *forces* the model to call a tool. "Always-on constraint" is therefore built from three composable pieces: (a) an always-on `UserPromptSubmit` directive injection, (b) standing instructions injected at `SessionStart`, and (c) a `PreToolUse` guard that **denies every bypass**. Blocking all alternatives + a mandatory standing directive is the closest achievable thing to binding.

2. **A plugin's `CLAUDE.md` is NOT injected into the user's session.** It only guides work performed *on* the plugin's own repo. Therefore the main-session conductor cannot be installed via a shipped `CLAUDE.md`; it must be installed entirely through **hooks** (`SessionStart` + `UserPromptSubmit` + `PreToolUse`) — which is exactly the infrastructure this plugin already ships.

3. **Plugin dependencies are per-_plugin_, not per-_skill_.** Declaring a dependency pulls the whole upstream plugin, including sibling skills you never vendored.

4. **Cross-marketplace dependencies require two things**: (a) the root `marketplace.json` must list each target marketplace in `allowCrossMarketplaceDependenciesOn`, and (b) **the end user must have run `claude plugin marketplace add` for each** — otherwise the dependency silently stays unresolved ("来自你尚未添加的 marketplace 的依赖将保持未解析状态"). This is a real regression from today's fully-bundled, out-of-box behavior.

5. **Version-pinned deps resolve against `{plugin-name}--v{version}` git tags.** Most of the six upstreams do *not* tag this way (they use plain `vX.Y`). We chose **unpinned** (bare-string-equivalent) deps, so tag-based version resolution does not apply — but unpinned cross-marketplace resolution against these git sources must still be smoke-tested before commit.

---

## 3. Locked Decisions (from clarifying interview)

| # | Question | Choice |
|---|---|---|
| Q0 | Where does the entry-point constraint live? | **Main session IS the conductor** |
| Q1 | When must the conductor own a task list? | **Every execution-class turn forces a task list** (Mode A no longer exempt) |
| Q2 | How hard is the guard when the main session does execution work itself? | **Hard-deny main-session bypass** (no escape hatch) |
| Q3 | Which third-party sources move to dependencies? | **All six**: the three already-plugins (imbad, lylll9436, karpathy) + superpowers + anthropics + orchestra |
| Q4 | Depend vs bundle tradeoff? | **Pure dependency, unpinned** — stop bundling the six; do not version-lock |
| Q5 | What happens to `research-copilot.agent.md`? | **Retire the sub-agent; inject the protocol into the main session** |
| Q6 | How to package the work? | **One spec, two sequential implementation phases** (A then B) |

**Non-goals.**
- Refactor of the 7 `copilot-*` execution sub-agents (their internal state machines, `copilot_write_guard.py`, `copilot_subagent_stop.py` are untouched).
- Migrating the *other* vendored sources to dependencies (humanizer, auto-research, llm-wiki, mean-reviewer, master-cai, k-dense-ai, luwill, lishix520, hkust-supervisor, chenliu remain vendored).
- Version-pinning any dependency.
- Preserving a bundled fallback copy of the six dep sources (pure-dependency means out-of-box requires the user to add marketplaces).

---

## Part A — Main-Session Conductor

### A.1 Architecture

The conductor protocol is installed onto the main session by three hooks. The 7 `copilot-*` execution sub-agents stay exactly as they are.

```
        user prompt
            │
            ▼
   ┌─────────────────────────────────────────────┐
   │  MAIN SESSION = CONDUCTOR                     │
   │  (protocol injected by hooks, not a sub-agent)│
   │                                               │
   │  SessionStart  → inject CONDUCTOR-PROTOCOL +  │
   │                  current .copilot/state.md    │
   │  UserPromptSubmit → re-assert standing orders │
   │                  every turn (no suppression)  │
   │  PreToolUse    → deny main-session bypass     │
   └───────────────┬───────────────────────────────┘
                   │ Agent(subagent_type=copilot-*)
                   │ (must be preceded by TaskCreate)
                   ▼
        7 copilot-* execution sub-agents
        (guard EXEMPTS these — run freely)
```

### A.2 Hook changes

| Hook | File | Today | After |
|---|---|---|---|
| **SessionStart** | `session_start_memory_injector.py` | injects `__HANDOFF__` summaries from `.copilot/*.md` | **also injects the full conductor protocol** (the state machine, the 7-field delegation template, the "you ARE the conductor; diagnose → build task list → delegate" framing) and the current `.copilot/state.md` stage cursor. Sourced from a new `self/CONDUCTOR-PROTOCOL.md`. |
| **UserPromptSubmit** | `user_prompt_dispatch_reminder.py` | soft nudge; **suppressed** on `下一步` / `/` / `@` / status phrases | **Inverted into a standing-orders re-assertion** that fires on **every** turn (no `ALLOWLIST_PHRASES` / prefix suppression). Re-states: *you are the conductor; if this is execution-class work, build a TaskCreate plan then delegate to copilot-\*; do not execute inline.* This is what makes the constraint apply "from whichever interaction onward," regardless of phrasing. |
| **PreToolUse** | `research_copilot_guard.py` | **no-ops for the main session**; only polices the `research-copilot` sub-agent | **Scoping inverted**: the **main session is policed by default**; only `copilot-*` sub-agents are exempt (so they still run experiments, searches, writes freely). |

### A.3 New / changed guard patterns (main-session-scoped, hard-deny)

The guard's existing sub-agent-scoped patterns (1, 3, 5, 6, 7 as they apply to `research-copilot`) are removed along with the retired sub-agent. Two new **main-session** patterns replace them:

| Pattern | Tool match | Denies when |
|---|---|---|
| **M1 — delegation gate** | `Bash`, `PowerShell`, `Write`, `Edit`, MCP retrieval tools (see matcher note) | The **main session** runs execution-class work directly: experiment scripts (`train.py`, `wandb`, `torchrun`, …), paper-retrieval MCP queries (`arxiv-search` / `arxivsub-search` / `google-scholar` / `dblp-bib`), or writes to a research artifact (`sections/*.tex`, `references.bib`, `.copilot/{ideas,experiments,literature}.md`). Deny → "delegate to the matching copilot-\* sub-agent." Read-only inspection (`cat`, `grep`, `ls`, `Read`, `Glob`, `Grep`) is always allowed. |
| **M2 — task-list gate** | `Agent` | The **main session** calls `Agent(subagent_type=copilot-*)` with **zero `TaskCreate` calls in the current turn**. Deny → "build a TaskCreate plan list (one task per planned dispatch) before dispatching." This generalizes today's Mode-B-only pattern 7 to **every** dispatch, satisfying Q1. |

Both fire **only for the main session**; both fail **open** (the `safe_main` wrapper already guarantees an exception yields `allow`).

**Matcher-widening requirement (was a gap in the predecessor design).** Today the conductor was a sub-agent whose `tools:` frontmatter allowlist excluded MCP tools — so it *physically could not* call `arxiv-search` etc., and the guard never needed to watch MCP. The main session has **no `tools:` allowlist**: it can call any MCP tool. For M1's MCP branch to fire at all, the guard's registered matcher in `install.py` must widen from `Bash|PowerShell|Agent|Write|Edit` to also match the paper-retrieval MCP tool names, e.g. append `|mcp__arxiv-search.*|mcp__arxivsub-search.*|mcp__google-scholar.*|mcp__dblp-bib.*`. If the matcher is *not* widened, main-session MCP retrieval is governed only by the soft standing-orders directive (A.2), not a hard deny — which would violate Q2 for the search-paper path. The plan MUST widen the matcher; this is listed as an open item (§5).

### A.4 The active-agent attribution problem (TOP RISK)

The guard must distinguish "the **main session** made this tool call" from "a **copilot-\*** sub-agent made this call." Today, `detect_active_agent()` scans the transcript backward for the most-recent `subagent_type` marker. The failure mode: when a sub-agent finishes and control returns to the main session, there may be **no reset marker** in the transcript — so the next main-session tool call can be **mis-attributed to the just-finished sub-agent**, which would wrongly *exempt* it from M1/M2.

The implementation plan must settle a reliable attribution rule. Candidate approaches to evaluate (decision deferred to the plan):

- **A.4-i — Sub-agent stop marker.** Treat a `SubagentStop`-adjacent transcript entry as a reset back to "main session," so attribution is "main" unless a *later* `subagent_type` marker with no intervening stop exists.
- **A.4-ii — PreToolUse payload inspection.** If the `PreToolUse` hook payload carries a field that directly indicates whether the call originates from a sub-agent context, prefer that over transcript scanning. (Needs verification against the actual payload shape on this Claude Code release.)
- **A.4-iii — Conservative default.** If attribution is ambiguous, default to **"main session"** (i.e. *apply* M1/M2). Rationale: a false deny costs the conductor one extra delegation step (recoverable), whereas a false exempt silently defeats the whole feature. This is the inverse of the current guard's APPROVE-on-doubt posture and must be stated explicitly.

The plan will pick one (likely A.4-iii as the safety net combined with whichever of i/ii proves reliable) and ship a unit test that reproduces the "control just returned to main" transcript shape.

### A.5 Disposition of `research-copilot.agent.md` and `PIPELINE-OS.md`

- **`research-copilot.agent.md` is retired** as a dispatchable sub-agent (removed from `agent.txt` / the agents bundle). Its state table, Mode A/B templates, back-edge inbound matrix, and write-permission notes migrate into a new **`self/CONDUCTOR-PROTOCOL.md`**, authored for a *main-session* reader ("you are the conductor") rather than a sub-agent reader.
- **`PIPELINE-OS.md` stays** as the shared spec. The 7 `copilot-*` sub-agents continue to reference its `§N` sections. The conductor-only sections (§5 approval policy, §6 dispatch policy, §7 back-edge matrix) are now consumed by the injected protocol rather than by a sub-agent file.
- The 7 `copilot-*` sub-agent files, `copilot_write_guard.py`, `copilot_subagent_stop.py`, and `_copilot_hook_lib.py`'s sub-agent machinery are **unchanged** except: `COPILOT_AGENTS` / `detect_active_agent` consumers must treat `research-copilot` as no-longer-a-sub-agent, and the guard's scoping flips per A.2.

### A.6 Files touched (Part A)

| File | Change |
|---|---|
| `self/CONDUCTOR-PROTOCOL.md` | **new** — main-session conductor protocol (migrated from `research-copilot.agent.md`) |
| `self/hooks/scripts/session_start_memory_injector.py` | inject CONDUCTOR-PROTOCOL + state cursor |
| `self/hooks/scripts/user_prompt_dispatch_reminder.py` | remove suppression; re-assert standing orders every turn |
| `self/hooks/scripts/research_copilot_guard.py` | invert scoping (police main session, exempt copilot-\*); replace patterns with M1 + M2 |
| `self/hooks/scripts/_copilot_hook_lib.py` | attribution rule for "main session" (A.4); drop `research-copilot` from sub-agent set |
| `self/agents/research-copilot.agent.md` | **remove** (retired) |
| `agent.txt` | (no change needed — globs `self/agents/*`; file removal suffices) |
| `self/PIPELINE-OS.md` | trim conductor-only prose that moved to CONDUCTOR-PROTOCOL; keep `§N` shared refs |
| `self/hooks/research-copilot-guard.hook.md` | rewrite spec doc to describe M1/M2 + inverted scoping |
| `self/hooks/scripts/__tests__/` | new tests for M1, M2, A.4 attribution; update/remove pattern-7 test |
| `self/install.py` | widen guard registration matcher to also catch paper-retrieval MCP tools (A.3 matcher note); update the embedded prompt-fallback text to the main-session framing |

---

## Part B — Plugin-Dependency Migration

### B.1 The six sources and their plugin/marketplace identities

Verified from each source's `.claude-plugin/marketplace.json` during the interview:

| Vendored source (today) | Dependency plugin name | Its marketplace name | Granularity note |
|---|---|---|---|
| `third_party/imbad0202-research` | `academic-research-skills` | `academic-research-skills` | single plugin, exact match |
| `third_party/lylll9436` | `paper-polish-workflow` | `paper-polish-workflow` | single plugin, exact match |
| `third_party/andrej-karpathy-skills` | `andrej-karpathy-skills` | `karpathy-skills` | single plugin, exact match |
| superpowers (already installed, never vendored) | `superpowers` | `superpowers-dev` | pure new dep |
| `third_party/anthropics` (used: `doc-coauthoring`, `canvas-design`) | `example-skills` | `anthropic-agent-skills` | **over-pull**: this plugin bundles 11 skills incl. frontend-design, mcp-builder, skill-creator, etc. |
| `third_party/orchestra` (used: `20-ml-paper-writing/*`, `0-autoresearch-skill`) | `ml-paper-writing` **and** `autoresearch` | `ai-research-skills` | the two plugins exactly match what was vendored |

> Note on `anthropic-agent-skills`: depending on `example-skills` pulls 9 skills we did not vendor. The plan should confirm this is acceptable (it adds capability, not breakage). If undesirable, the fallback is to keep `doc-coauthoring`/`canvas-design` vendored and drop only the dep — but per Q3/Q4 the default is to depend.

### B.2 Generated `plugin.json` — add `dependencies`

`build_copilot_workspace.py::package_claude_code_workspace` constructs `plugin_manifest`. Add a `dependencies` array (object form, since every target is cross-marketplace and must name its `marketplace`):

```json
"dependencies": [
  { "name": "academic-research-skills", "marketplace": "academic-research-skills" },
  { "name": "paper-polish-workflow",    "marketplace": "paper-polish-workflow" },
  { "name": "andrej-karpathy-skills",   "marketplace": "karpathy-skills" },
  { "name": "superpowers",              "marketplace": "superpowers-dev" },
  { "name": "example-skills",           "marketplace": "anthropic-agent-skills" },
  { "name": "ml-paper-writing",         "marketplace": "ai-research-skills" },
  { "name": "autoresearch",             "marketplace": "ai-research-skills" }
]
```

No `version` field on any entry (Q4: unpinned).

### B.3 Generated `marketplace.json` — add `allowCrossMarketplaceDependenciesOn`

`build_copilot_workspace.py` constructs `marketplace_manifest`. Add:

```json
"allowCrossMarketplaceDependenciesOn": [
  "academic-research-skills",
  "paper-polish-workflow",
  "karpathy-skills",
  "superpowers-dev",
  "anthropic-agent-skills",
  "ai-research-skills"
]
```

### B.4 `skill.txt` — remove the vendoring lines now covered by deps

Remove these `add` lines (line numbers as of current `skill.txt`):

- L2 `add third_party\anthropics\skills\doc-coauthoring`
- L3 `add third_party\anthropics\skills\canvas-design`
- L5 `add third_party\orchestra\20-ml-paper-writing\*`
- L6 `add third_party\orchestra\0-autoresearch-skill`
- L12 `add third_party\imbad0202-research\academic-paper`
- L13 `add third_party\imbad0202-research\academic-paper-reviewer`
- L14 `add third_party\imbad0202-research\academic-pipeline`
- L15 `add third_party\imbad0202-research\deep-research`
- L17 `add third_party\lylll9436\skills\*`
- L18 `add third_party\lylll9436\references`
- L25 `add third_party\andrej-karpathy-skills\skills\karpathy-guidelines`

**Kept** (not dependencies, remain vendored): `self\skills`, humanizer, auto-research (skills + skills-codex), llm-wiki, mean-reviewer, master-cai, k-dense-ai, luwill, lishix520, hkust-supervisor, chenliu, and the `del` lines.

> Open item for the plan: `third_party/lylll9436/references` (L18) — confirm nothing in the *kept* skills references those files before removing; if depended-upon, keep L18.

### B.5 README + install.py — document the new user prerequisite

Pure-dependency means the plugin is **no longer out-of-box** unless the user has the six marketplaces added. Add to README install instructions and surface in `install.py` output a pre-install checklist:

```
claude plugin marketplace add Imbad0202/academic-research-skills
claude plugin marketplace add Lylll9436/Paper-Polish-Workflow-skill
claude plugin marketplace add <karpathy-skills repo>
claude plugin marketplace add <superpowers-dev / obra/superpowers>
claude plugin marketplace add <anthropic-agent-skills repo>
claude plugin marketplace add <orchestra ai-research-skills repo>
```

(The plan will resolve each marketplace's canonical `marketplace add` argument — github `owner/repo` or URL — from the upstream marketplace.json `source` fields.)

### B.6 TOP RISK (Part B)

`superpowers-dev`, `anthropic-agent-skills`, `karpathy-skills`, `paper-polish-workflow` tag with plain `vX.Y`, not `{name}--v*`. We are unpinned, so tag-based version resolution does not apply — but whether **unpinned** cross-marketplace deps resolve cleanly against these git sources must be verified with a real `claude plugin install` against a scratch profile before this part is considered done. If resolution fails for a given source, the fallback is to re-vendor that one source only (revert its `skill.txt` lines + drop its dep entry), leaving the others on deps.

### B.7 Files touched (Part B)

| File | Change |
|---|---|
| `scripts/build_copilot_workspace.py` | add `dependencies` to `plugin_manifest`; add `allowCrossMarketplaceDependenciesOn` to `marketplace_manifest` |
| `skill.txt` | remove the 11 vendoring lines in B.4 |
| `README.md` | document the `marketplace add` prerequisite list |
| `self/install.py` | print the prerequisite checklist; (no settings change) |
| `.claude/skills/validate-plugin-build/SKILL.md` | extend build validation to assert deps + allowlist present (if it currently asserts manifest shape) |

---

## 4. Sequencing

Two independent phases, A before B (Q6). Each is independently testable and independently revertable.

1. **Phase A — Main-session conductor.** Hooks + protocol doc + guard rewrite + tests. Verifiable by: a transcript-shape unit test for A.4; a manual session check that (i) a fresh session with no `@research-copilot` still enforces delegation, and (ii) `Bash train.py` from the main session is denied while the same call from `copilot-experiment` is allowed.
2. **Phase B — Dependency migration.** Build-script + skill.txt + manifests + docs. Verifiable by: a scratch-profile `claude plugin install` that resolves all seven deps after the six `marketplace add`s (B.6), and a `deploy`-branch diff showing the six sources' skills are gone while the kept ones remain.

---

## 5. Open Items For The Plan

- **A.4** — pick the active-agent attribution rule + ship the regression test for the "control returned to main" transcript shape.
- **A.3-matcher** — widen the `install.py` guard matcher to include the paper-retrieval MCP tool names so M1's MCP branch can fire; without it, main-session MCP search is only soft-governed.
- **B.1** — confirm the `example-skills` over-pull (9 extra skills) is acceptable, or special-case anthropics back to vendoring.
- **B.4** — confirm `lylll9436/references` (L18) is not consumed by a kept skill before removal.
- **B.5** — resolve each of the six marketplaces' canonical `claude plugin marketplace add` argument from upstream `marketplace.json` `source` fields.
- **B.6** — scratch-profile install test for unpinned cross-marketplace resolution; define per-source re-vendor fallback.
