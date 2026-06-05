# ADR 0001 — Emulate Trellis; full TypeScript rebuild; injection-driven steering

- Status: Accepted
- Date: 2026-06-05
- Supersedes: the 2026-05-05 redesign design (`docs/superpowers/specs/2026-05-05-research-copilot-redesign-design.md`) and the previous Claude Code plugin architecture.
- Source spec: [2026-06-05-research-copilot-trellis-redesign-design.md](../../superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md), §2 (decision log) and §10.

## Context

Research Copilot started as a Claude Code plugin: a marketplace bundle of 320+ skills, ~10 agents, 6 Python MCP servers, and a SessionStart guard hook. That architecture had three structural problems: it was single-platform (Claude Code only), its "guidance" was enforced by brittle hard-reject guard hooks (which can't be unit-tested and don't generalize across platforms), and it depended on five third-party skill marketplaces that frequently failed to resolve.

[Trellis](https://github.com/) — a generic, multi-platform CLI for driving coding agents through a controlled task lifecycle via per-turn context injection — solves the same orchestration problem in a cleaner, testable, multi-platform way. The decision was to **emulate Trellis's architecture wholesale and layer the research domain on top**, rather than patch the plugin.

The eight directional decisions below were confirmed item-by-item in brainstorming and are treated as locked (spec §2).

## Decisions

| # | Decision | Choice | Why |
|---|---|---|---|
| **D1** | Degree of emulation | **Full replica: multi-platform CLI framework** | A generic framework base with a research-domain layer on top, not a light reskin. Buys the platform matrix, the FSM, and the injection model for free. |
| **D2** | Implementation language | **TypeScript full-stack** | CLI + scripts + MCP servers all in TS; the existing Python assets are dropped. One toolchain, one test runner, and a pure `core` that is directly unit-testable. |
| **D3** | Platform coverage | **Broad coverage** | The adapter registry is designed for all 14 Trellis platforms; v1 lands the 6 with verified mechanisms; the rest are a registry+template increment (milestone 2). |
| **D4** | Naming / brand | **Keep research-copilot** | CLI `rc`; directory `.research/`; agent prefix `rc-`; npm package `research-copilot`. Continuity for existing users and the repo identity. |
| **D5** | Phase mapping | **Generic lifecycle × research `kind` × flexible task graph** | Not a fixed pipeline and not generic templates. A small lifecycle FSM crossed with seven research kinds and a `depends_on`/`parent` graph models real research, which is non-linear. |
| **D6** | Orchestration driver | **Injection-driven recommendation (Trellis-native); no conductor agent** | Each turn a hook injects the workflow state + a deterministic research-state recommendation; the user decides. No LLM-in-a-loop conductor to drift or burn tokens. |
| **D7** | Dependency strategy | **rc self-manages skill-packs** | Drop the Claude Code marketplace dependencies; a `skillpacks.yaml` pulls and renders external skills to every platform. Removes the five-marketplace resolution failure mode. |
| **D8** | Enforcement philosophy | **Injection guidance + verify gate + spec norms** | Retire heavy hard-reject guards. Guidance is the injected state block; quality is enforced at the `verify` state transition by deterministic `core` checks; an optional warn-only guard is deferred to milestone 2. |

## Rationale highlights

**Why Trellis.** It already solves multi-platform, per-turn context injection — the exact problem the plugin solved badly. Emulating it (D1) yields the lifecycle FSM, the `rc context` single-source-of-truth injection, and the class-1/class-2 platform model as proven scaffolding; we only add the research layer (the seven kinds, the gap-driven recommender, the writing verify gate).

**Why TypeScript full-stack (D2).** The old split (Python MCP + JS/markdown plugin) made the orchestration logic untestable and the Windows hook story painful. A pure TS `core` makes the recommender and verify checks deterministic unit tests (spec §10.1), and a Node `rc` CLI means hooks call one cross-platform binary — sidestepping the Python-on-Windows hook problems Trellis itself has.

**Why injection-driven, no conductor (D6, D8).** A conductor agent is an LLM in a loop: nondeterministic, token-hungry, and hard to verify. Replacing it with (a) `workflow.md` as the per-state guidance source and (b) a pure `computeResearchState` recommender turns "what next?" into testable data. Enforcement moves from intercepting tool calls (which only two of six v1 platforms even support) to a `verify` state gate that rolls failing tasks back to `in_progress` — uniform across platforms and unit-testable.

## Consequences

- The previous plugin architecture (and the 2026-05-05 design) is superseded; the Python code, the guard hooks, and the marketplace dependencies are abandoned (migration path in spec §11).
- `core` carries the orchestration intelligence and must stay pure and deterministic; `cli`/`adapters` stay thin.
- Adding a platform is a registry entry + a configurator (see [adding-a-platform.md](../adding-a-platform.md)), realizing D3's broad-coverage intent incrementally.
- Quality lives in the verify gate, not in tool interception; the warn-only guard remains a deferred milestone-2 option (D8).
