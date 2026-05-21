---
name: research-workflow
description: Research pipeline workflow enforcement. Use when coordinating any research stage (literature/ideation/experiment/writing/polishing/review/rebuttal). Provides mandatory checklist and state machine rules.
---

# Research Workflow

You are following the research-workflow skill for the research-copilot agent.

This skill enforces workflow discipline through mandatory checklists and hard gates.

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
