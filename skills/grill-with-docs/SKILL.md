---
name: grill-with-docs
description: "Post-plan stress test. Use AFTER a plan is drafted (Goal anchor, ideation candidate, rebuttal strategy, pipeline template) to gap-check the plan against the project's existing documentation, terminology, and recent reviewer / handoff history in `.copilot/`. Sharpens fuzzy terms inline, cross-references the codebase / tex / logs, and offers ADRs only when a decision is hard to reverse. Never used to draft the plan itself. Triggers on: '校验计划', '对着文档拷问', '把计划放到文档里盘一遍', 'grill the plan', 'stress-test plan', 'audit plan against docs', 'check plan for gaps'."
version: 0.2.0
---

# Grill with docs — Post-plan gap check

Run **after** a plan exists (Goal anchor in `experiments.md`, selected direction in `ideas.md`, response strategy in `rebuttal/round-N.md`, or routing decision in `decisions.md`). Purpose: stress-test that plan against the project's existing language and documented state, surface contradictions, and update the docs inline as terminology is resolved.

This skill is **not for plan drafting**. If no plan exists yet, run `deep-interview` first, hand off to the planning agent, then return here.

## When this skill fires

Fire automatically when the most recent disk write was one of:

- `## Goal anchor` block freshly written to `.copilot/experiments.md`
- A new `## Selected direction` in `.copilot/ideas.md`
- A new `## Reviewer N strategy` block in `rebuttal/round-N.md`
- A new pipeline template entry in `.copilot/decisions.md`

Also fires on user request: "校验一下这个计划" / "grill this plan."

## Documentation surface (auto-detected)

```
.copilot/
├── state.md             ← stage cursor + loop counters
├── literature.md        ← locked baseline + related work
├── ideas.md             ← user preferences + candidates + selected
├── experiments.md       ← Goal anchor + Run-N history
├── handoff.md           ← writer / polisher / reviewer / rebuttal facts
├── decisions.md         ← approval-gate decisions
├── glossary.md          ← created lazily by THIS skill on first term resolve
├── adr/                 ← created lazily by THIS skill on first ADR
└── reviews/round-N.md   ← independent review rounds
```

`glossary.md` and `adr/` are created **only when** the first term / first ADR appears — do not pre-create empty scaffolds.

## Procedure

### Step 1 — Read the plan + the docs

Load the just-written plan block and the relevant `.copilot/` files. For multi-doc projects (rare in this repo), also load any sibling `CONTEXT.md` / `CONTEXT-MAP.md` if present.

### Step 2 — Run the four challenges, in order

| Challenge | What you do |
|---|---|
| **Glossary clash** | For every noun phrase in the plan, check `.copilot/glossary.md` (and the existing tex / `ideas.md` / `literature.md`). If a term collides with prior usage or is fuzzy ("module," "robustness," "improvement"), propose a precise canonical term and ask the user to confirm. Update `glossary.md` inline when resolved. |
| **Sharpen fuzzy language** | For every claim ("works better," "more robust," "faster"), demand the metric / unit / baseline / threshold. Push the user to a number or a falsifiable shape. |
| **Concrete scenario stress test** | For every relationship in the plan ("Module A feeds Module B"), spell out one concrete scenario end-to-end. If the scenario breaks, flag it before any experiment burns compute. |
| **Cross-reference with code / data** | For every "how it works" claim, grep the codebase / tex / logs and confirm the code agrees. If the plan describes behaviour the code does not exhibit, the plan is wrong — flag it. |

Each challenge runs **once** per pass. One question at a time, with a recommended answer + the file:line that motivated the question.

### Step 3 — Update docs inline (lazy creation)

When a term is resolved, write to `.copilot/glossary.md` immediately:

```markdown
## <Canonical term>
- Definition: <one sentence>
- First defined: <YYYY-MM-DD> (during grill-with-docs of <plan slug>)
- Aliases to avoid: <fuzzy or colliding terms now retired>
- Used in: <file paths / sections>
```

Create `glossary.md` if it does not yet exist.

### Step 4 — Offer an ADR only when all three are true

Add to `.copilot/adr/NNNN-<slug>.md` only when:

1. **Hard to reverse** — changing this mid-project means redoing experiments / rewriting sections
2. **Surprising without context** — a future reader (or a reviewer) will ask "why this way?"
3. **Result of a real trade-off** — there were ≥2 alternatives, one was picked for a specific reason

If even one is false, skip the ADR. Most decisions live in `decisions.md` already and do not need promotion. Number ADRs by file count: first ADR is `0001-<slug>.md`.

ADR template:

```markdown
# <NNNN> — <Title>
- Status: accepted | superseded by NNNN
- Date: <YYYY-MM-DD>
- Context: <2-3 sentences — why this came up, which plan triggered it>
- Decision: <the chosen alternative, one sentence>
- Alternatives considered: <list with one-line "why not">
- Consequences: <experiments / sections / future ablations this commits us to>
```

## Output

When the pass finishes, emit:

```markdown
## Grill-with-docs report — <plan slug>
- Date: <YYYY-MM-DD>
- Plan reviewed: <file:line>
- Glossary entries added / updated: <count> → <glossary.md anchors>
- Fuzzy claims sharpened: <count> → <plan file:line edits>
- Scenarios stress-tested: <count> → <list of scenarios + outcomes>
- Code cross-references: <count> → <files / functions verified>
- ADRs created: <count> → <adr/NNNN-*.md anchors, or "none — bar not met">
- Plan changes proposed: <list of edits to the plan file, with file:line>
- Residual risks: <list anything you grilled and could not resolve>
- Hand off to: <agent who acts on the changes, or "user approval" if changes need confirmation>
```

## Hard constraints

- **Post-plan only** — if no plan block exists, exit and recommend `deep-interview` first
- **Read before challenging** — every challenge must cite a concrete file:line, not "in general"
- **Update docs inline** — never batch glossary updates "for the end"
- **ADR bar is strict** — three conditions, ALL must hold; otherwise leave the decision in `decisions.md`
- **Do not edit the plan unilaterally** — propose edits with file:line; the writing agent (or user) applies them
- **One challenge round per pass** — do not loop the four challenges; if more passes are needed, the user explicitly re-invokes
- **Lazy file creation** — `glossary.md` and `adr/` directory created only on first real entry
