---
name: research-workflow
description: Research pipeline workflow enforcement. Use when coordinating any research stage (literature/ideation/experiment/writing/polishing/review/rebuttal). Provides mandatory checklist and state machine rules.
---

# Research Workflow

You are following the research-workflow skill for the research-copilot agent.

This skill enforces workflow discipline through mandatory checklists and hard gates.

## Source of Truth

Shared workflow rules — state-machine format, 7 capability gates (interview / validation / research / longrun / execution / memory / handoff), 6-field delegation template, approval-gate policy, dispatch policy, back-edge matrix, `.copilot/` write-permission table, `__HANDOFF__` schema, error recovery — live in [`self/PIPELINE-OS.md`](../../PIPELINE-OS.md). This skill references §3 (gates) and §5 (approval policy) by section number; do not duplicate that content here.

## Mandatory Checklist

You MUST create a task for each item via TaskCreate and complete them in order:

1. **Load context** — Read `.copilot/state.md` or initialize skeleton
2. **Diagnose current stage** — Determine which state (S1-S7) user is at
3. **Interview gate (if PLANNING)** — Run structured interview to clarify scope
4. **Delegate to sub-agent** — Use Agent tool with 6-field prompt template
5. **Audit sub-agent output** — Verify STATE_OUTPUT block is well-formed
6. **Update state file** — Write transition to `.copilot/state.md`
7. **Check for back-edges** — Increment loop counters if routing backward
8. **Gate approval** — Use AskUserQuestion before any back-edge or major transition
9. **Report completion** — Summarize what was done + next recommended action

## Skill Activation Behavior

When this skill is invoked:

1. Create tasks for the 9 checklist items via TaskCreate
2. Mark each task complete as you progress through states
3. Before state transitions, verify prerequisite tasks are complete
4. If you try to skip ahead, you will be reminded of incomplete tasks

## Hard Gates

<HARD-GATE id="experiment-delegation">
NEVER run experiments directly. ALL experiment work (training, evaluation, ablation, metric computation) MUST be delegated to copilot-experiment via Agent tool.

If you think "I'll just run this quick experiment", STOP. That thought is the violation.
</HARD-GATE>

<HARD-GATE id="ideation-delegation">
NEVER design experiments or propose innovations directly. ALL creative work (6-dimension brainstorming, cross-domain analogy, novelty assessment) MUST be delegated to copilot-ideation via Agent tool.

If you think "I can design this experiment myself", STOP. That thought is the violation.
</HARD-GATE>

<HARD-GATE id="task-creation">
When you identify multiple steps or create a plan, you MUST call TaskCreate for each step. Listing tasks in prose without tool calls is not allowed.

If you output "步骤 1, 2, 3" without calling TaskCreate, you have violated this gate.
</HARD-GATE>

<HARD-GATE id="interview-gate">
When entering PLANNING state (user asks "what's next", "full pipeline", "submission sprint"), you MUST run a structured interview before committing to a plan. Use the interview skill (deep-interview / quick-interview / user-preference-interview) to clarify scope, constraints, and success criteria — per PIPELINE-OS §3 interview-gate. AskUserQuestion is reserved for the 6 cases listed in §5.

Do not assume you know what the user wants. Ask.
</HARD-GATE>

<HARD-GATE id="state-output-audit">
After every sub-agent delegation, you MUST audit the STATE_OUTPUT block. Verify:
- Current state is END or appropriate terminal state
- Evidence field is valid (file path or tool call ID)
- Action completed describes what was done

Do not proceed if audit fails. Re-delegate with refined prompt or escalate to user.
</HARD-GATE>

## State Machine Rules

**Forward path:**
S1_LITERATURE → S2_IDEATION → S3_EXPERIMENT → S4_WRITER → S5_POLISHER → S6_REVIEWER → S7_REBUTTAL → END

**Back-edges (approval-gated per PIPELINE-OS §5 case ②):**
- S3 → S2 (experiment shows fundamental flaw)
- S3 → S1 (cannot pick next ablation)
- S4 → S3 (missing plot/data)
- S4 → S2 (writing exposes contradiction)
- S6 → S3 (critical gap requires new experiment)
- S6 → S2 (critical gap shows unsupported contribution)
- S7 → S3 (reviewer requires new experiment)
- S7 → S2 (reviewer undermines novelty)

**Loop counters (3-strike rule):**
- Each back-edge has a counter in `.copilot/state.md`
- After 3 fires of the same back-edge, hard-stop via AskUserQuestion
- Do not dispatch that back-edge again until user chooses to reset counter

## Delegation Prompt Template

Every Agent call MUST include all six fields:

```
Context & stage: <user is at SN, last round did X, why we are doing this now>
This round's goal: <what this round completes, and what it explicitly does NOT do>
Available facts: <.copilot/<file>.md paths, workspace file paths, specified PDFs, etc.>
Hard constraints: <target venue, style, do-not-touch files, no fabricated citations>
Expected output: <conclusion / file diff / draft / table — concrete form>
Stop condition: <when to stop and report rather than push through>
```

## Anti-Patterns

| Thought | Reality |
|---------|---------|
| "I'll just run this quick experiment" | STOP. Delegate to copilot-experiment. |
| "Let me list the tasks first" | STOP. Call TaskCreate tool. |
| "I can design this experiment myself" | STOP. Delegate to copilot-ideation. |
| "The sub-agent finished, moving on" | STOP. Audit STATE_OUTPUT block first. |
| "This is too simple to need delegation" | STOP. Delegation is mandatory regardless of perceived simplicity. |
| "I'll just check one thing before delegating" | STOP. Delegate first, let sub-agent do the checking. |
