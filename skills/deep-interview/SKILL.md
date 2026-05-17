---
name: deep-interview
description: "Pre-plan Socratic clarification. Use BEFORE drafting any plan (ideation direction, experiment Goal anchor, rebuttal strategy, pipeline routing) to expose hidden assumptions, lock topology, and converge on scope. Walks the decision tree one branch at a time with a recommended answer per question and an explicit ambiguity score, stopping only when the score crosses the threshold. Triggers on: '帮我厘清需求', '我有个想法不太明确', '在写计划前先聊清楚', '深度访谈', 'clarify before planning', 'deep interview', 'requirements interview', 'scope before plan'."
version: 0.2.0
---

# Deep Interview — Pre-plan clarification gate

Run **before** any plan is drafted. Purpose: turn a vague user ask into a crystallised spec the downstream planner can execute literally. This skill does NOT write the plan itself — when the ambiguity score crosses the threshold, hand off to the appropriate agent / planning skill.

## When this skill fires

Fire automatically when the next action is one of:

- Drafting the **Goal anchor** in `.copilot/experiments.md` (first experiment dispatch)
- Picking a **research direction** in `.copilot/ideas.md` (ideation Step A)
- Deciding the **rebuttal response-strategy** per reviewer comment
- Choosing the **routing template** in `research-copilot` (full pipeline / submission sprint / custom sequence)
- Any other moment where a sub-agent is about to commit a plan to disk

Skip if a `## Goal anchor` (or equivalent immutable plan block) already exists — do not re-interview about a settled commitment.

## Operating principles

1. **One question per round.** Each round ships exactly one question + your recommended answer + a one-sentence reason. Never dump 3–5 parallel questions.
2. **Read before you ask.** If the answer is in `.copilot/{state, literature, ideas, experiments, handoff, decisions}.md`, workspace tex/code/logs, or recent reviewer rounds — read first, then ask only what remains.
3. **Topology first.** Round 0 enumerates 1–6 independent components of the ask (e.g. for "submission sprint": writer pass / polish / review / rebuttal-prep — pick which are in scope). Lock the component list before drilling into any single one.
4. **Rotate across components.** When >1 component is active, rotate targeting so no single component reaches clarity while siblings stay vague.
5. **Score every round.** After each answer, score four dimensions on 0–1:
   - **goal** — does the user know the *what*?
   - **constraints** — compute / data / deadline / venue / word-limit bounds named?
   - **criteria** — falsification + success criteria explicit?
   - **context** — is the existing `.copilot/` / codebase state cross-referenced? (brownfield only)
   - Ambiguity = `1 − (goal·0.35 + constraints·0.25 + criteria·0.25 + context·0.15)` for brownfield, drop the context term and renormalise for greenfield.
6. **Stop condition.** Exit when ambiguity ≤ **0.2** (default; the conductor may override) **or** after 20 rounds (hard cap — force exit and flag the residual gap).
7. **Challenge injections.** At rounds 4 / 6 / 8 (once each), inject one of:
   - **contrarian** — "what would a top-venue reviewer call your weakest assumption here?"
   - **simplifier** — "which of these branches can we drop without breaking the core claim?"
   - **ontologist** — "what is the single noun phrase this contribution renames or invents? where else does that noun already mean something different?"

## Round template

```
Round <N>  (ambiguity: <prev_score> → after this round: <new_score>)

Question: <one question>
My recommendation: <answer + one-sentence reason; cite file path / line / `.copilot/...` if the basis is in the repo>
What I will do once you answer: <next round's branch, or "exit and hand off to <agent>">
```

When invoked from an agent, use `AskUserQuestion` to render the question — never freeform-ask in main response text.

## Output: the crystallised spec

When the stop condition fires, emit:

```markdown
## Deep-interview spec — <slug>
- Date: <YYYY-MM-DD>
- Topology (locked at Round 0): <component list>
- Goal: <one sentence>
- Constraints: <compute / data / deadline / venue / word-limit, each with a number>
- Success criterion: <how we know it worked>
- Falsification criterion: <how we know it failed>
- Residual ambiguity: <final score> on dimensions <list any below 0.6>
- Hand off to: <agent or skill that will draft the plan>
```

Write this block to the file the downstream planner will read:

| Downstream planner | Spec lands in |
|---|---|
| `@copilot-experiment` Step 1 (Goal anchor) | `.copilot/experiments.md` (above the Goal anchor) |
| `@copilot-ideation` Step B | `.copilot/ideas.md` `## User preferences` block |
| `@copilot-rebuttal` Step 2 (per-comment strategy) | top of `rebuttal/round-N.md` |
| `@research-copilot` pipeline routing | `.copilot/decisions.md` |

Do not write the plan itself in this step — only the spec.

## Hand-off

End with one line stating which agent / skill picks up next, e.g. "→ hand off to `@copilot-experiment` to draft the Goal anchor from this spec." After hand-off, the next agent **must** run `grill-with-docs` once its plan is drafted, to gap-check the plan against `.copilot/` documentation and glossary.

## Hard constraints

- **One question per round** — no parallel question dumps
- **Read first, ask second** — never ask about facts already in `.copilot/` or the workspace
- **No plan writing** — only the spec block; the downstream agent writes the plan
- **Do not skip Round 0 topology** — single-component asks still benefit from explicit enumeration
- **Honest ambiguity scores** — neither inflate to declare victory nor deflate to keep drilling
- **Exit at hard cap** — at round 20, exit and flag the residual gap; do not loop forever
