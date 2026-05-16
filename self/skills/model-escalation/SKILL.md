---
name: model-escalation
description: "Use when repeated debugging or writing iterations fail, root cause is unclear, environment limits block progress, the user is still dissatisfied after multiple attempts, or the user says '疑难杂症', '卡住', '多轮迭代无解', '反复失败', '更强模型', '升级求助', 'stuck', 'escalate', 'stronger model'. Produces a hand-off summary suitable for a stronger model to pick up."
version: 0.2.0
---

# Model Escalation

## Role
When a problem has resisted multiple solid attempts in the current session, or you can clearly perceive that the current model / environment / context cannot continue to make high-quality progress, your job is to **stop low-yield trial-and-error** and produce a high-quality help summary suitable for handoff to a stronger model.

## Use this skill when
- You have already done ≥ 2–3 rounds of substantive attempts; the problem is unresolved
- The root cause is unclear; continuing edits will significantly raise the risk of accidental damage
- Environment / permission / tool / context limits block verification
- The user remains dissatisfied and you have no high-confidence improvement path
- You can clearly describe the impasse but cannot reliably converge within this session

## Core requirements
- Be honest about the current state; do not exaggerate, do not cover up
- Write only verified information; mark anything unverified explicitly as a "current hypothesis"
- Separate goal, current state, attempts, results, and blocker
- Preserve executable context: error messages, file paths, commands, I/O, blast radius
- Do not push responsibility onto the user; your job is to make the handoff as easy to pick up as possible

## Output format

Output strictly in the structure below.

### Recommend Escalating
The current problem has entered a high-cost iteration zone; continued trial-and-error in this session has low yield. Forward the following summary to a stronger model to continue.

### 1. Goal
- 1–3 sentences on the desired end state
- Acceptance criteria or the user's expected outcome

### 2. Current state
- Where you currently are
- Actual behavior or error symptom
- Files / modules / commands / data directly related to the issue

### 3. Attempts so far
List in chronological order; each item includes:
1. What was done
2. Observed result
3. What this rules out, or why it still fails

### 4. Current judgment
- Confirmed facts
- Current hypotheses
- The actual blocker location

### 5. Suggested questions for the stronger model
- 1–3 most central questions
- MUST be specific. NEVER "help me see what's wrong."

### 6. Forwardable help prompt

```text
I am working on a problem; please continue from the information below and prioritize a minimum verifiable plan.

Goal:
...

Current state:
...

Attempts so far:
...

Confirmed facts:
...

Current hypotheses:
...

Blocker:
...

Please focus on:
1. ...
2. ...
3. ...

If you recommend code changes, prefer a minimum-change plan and state how to verify it.
```

## Execution checklist before output
1. Have you clearly separated facts from hypotheses?
2. Have you stated the user's actual desired outcome rather than just the surface error?
3. Are the critical paths attempted listed completely, so a stronger model does not waste time repeating them?
4. Are the suggested questions specific enough to act on?
5. Have you stopped doing uncertain trial-and-error and shifted to high-quality handoff?
