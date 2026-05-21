# Research Copilot Workflow Enforcement Design

- Date: 2026-05-21
- Scope: Hook-based enforcement + skill-based guidance for research-copilot workflow discipline
- Status: Approved, ready for implementation

## Background

The current `research-copilot.agent.md` has workflow discipline issues:

1. **Skips sub-agent delegation** — does experiment/ideation work directly instead of delegating to copilot-experiment/copilot-ideation
2. **Lists tasks without creating them** — outputs "步骤 1, 2, 3" in prose without calling TaskCreate tool
3. **Weak enforcement** — state machine structure exists but lacks hard gates to prevent violations
4. **No structured interview** — jumps into planning without clarifying scope/constraints

User feedback from conversation:
> "等一下,Agent没告诉你和实验有关的都需要sub-agent吗,而且应该是先列计划再逐个测试"

The agent violated two rules:
1. Experiment operations should be delegated to sub-agent (research-copilot:copilot-experiment)
2. Should list plan for user confirmation, then execute step-by-step

User requested we study superpowers patterns (brainstorming, writing-plans, executing-plans, subagent-driven-development, verification-before-completion, systematic-debugging) for their enforcement mechanisms.

## Design Decision

Use **Approach A: PreToolUse Hook + Skill Checklist** for enforcement:

- Create `self/hooks/research-copilot-guard.hook.md` to intercept and block violations
- Create `self/skills/research-workflow.skill.md` to provide workflow checklist and hard gates
- Modify `self/agents/research-copilot.agent.md` to invoke skill at startup

**Why this approach:**
- Clean separation: hook = enforcement, skill = workflow guide, agent = domain logic
- Hard enforcement via hook (cannot be bypassed by agent)
- Reusable: other agents could adopt the same workflow skill
- Inspectable: user sees what the hook is blocking in real-time
- Matches superpowers pattern: skills define workflow, enforcement is external

## Architecture

### Three-Component System

```
┌─────────────────────────────────────────────────────────────┐
│ User Request                                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ research-copilot.agent.md                                    │
│ - Invokes research-workflow skill at startup                 │
│ - Follows skill checklist                                    │
│ - Contains domain logic (state machine, routing, templates)  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ research-workflow.skill.md                                   │
│ - 9-step mandatory checklist (via TaskCreate)                │
│ - 5 hard gates (HARD-GATE blocks)                            │
│ - State machine rules reference                              │
│ - Delegation prompt template                                 │
│ - Anti-patterns table                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent attempts tool call (Bash, Agent, TaskCreate, etc.)    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ research-copilot-guard.hook.md (PreToolUse)                  │
│ - Intercepts tool call                                       │
│ - Checks blocking patterns                                   │
│ - Returns: ALLOW or BLOCK with message                       │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌────────┐            ┌──────────┐
    │ ALLOW  │            │  BLOCK   │
    │Execute │            │Return msg│
    └────────┘            └──────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │ Agent corrects action│
                    └──────────────────────┘
```

## Component 1: PreToolUse Hook

**File:** `self/hooks/research-copilot-guard.hook.md`

**Frontmatter:**
```yaml
---
name: research-copilot-guard
event: PreToolUse
agent: research-copilot
---
```

**Purpose:** Intercept research-copilot's tool calls and block workflow violations

### Blocking Rules

| Violation | Detection | Block Message |
|-----------|-----------|---------------|
| **Direct experiment execution** | Tool: Bash/PowerShell<br>Command contains: `train.py`, `run_experiment`, `python.*train`, `torch`, `tensorflow`, `wandb`, `mlflow`<br>Exception: Read-only commands (`grep`, `cat`, `ls`) | "Blocked: research-copilot cannot run experiments directly. Delegate to copilot-experiment via Agent tool with subagent_type='copilot-experiment'." |
| **Planning without TaskCreate** | Agent output contains: "步骤", "plan", "tasks", "checklist", numbered lists (1., 2., 3.)<br>No TaskCreate tool call in current turn<br>Exception: Referencing existing tasks or summarizing completed work | "Blocked: You listed tasks but didn't call TaskCreate. Create tasks via TaskCreate tool before proceeding." |
| **Missing sub-agent delegation** | Current state is S2_IDEATION or S3_EXPERIMENT (from `.copilot/state.md`)<br>No Agent tool call with matching subagent_type in current turn<br>Exception: State is in audit phase (checking sub-agent output) | "Blocked: State {state} requires delegation to {copilot-stage}. Use Agent tool with subagent_type='{copilot-stage}'." |
| **Missing interview gate** | Current state is PLANNING or CONTEXT_LOADED with plan-level request<br>No Skill tool call for research-workflow in current turn<br>Exception: Skill already invoked in this session | "Blocked: PLANNING state requires structured interview. Invoke research-workflow skill first." |

### Allow-List

Always allow:
- Read operations: Read, Grep, Glob
- State file updates: Write to `.copilot/state.md`, `.copilot/decisions.md`
- Agent tool calls to `copilot-*` agents
- TaskCreate, TaskUpdate, TaskList tool calls

### Session State Tracking

Hook maintains session state (reset on SessionStart):

```javascript
{
  skill_invoked: false,           // whether research-workflow skill was called
  current_state: "UNINITIALIZED", // last known state from .copilot/state.md
  last_delegation: null,          // last sub-agent delegated to (allows audit phase)
  planning_mode: false,           // whether user requested full pipeline
  override_next: false            // user requested override for next tool call
}
```

### Detection Logic

```
1. Parse agent context
   - Extract current state from .copilot/state.md if available
   - Extract session state from hook memory

2. Parse current turn
   - Extract tool calls from agent's response
   - Extract prose output for pattern matching

3. Apply blocking rules
   - Check each violation pattern in order
   - First match triggers block

4. Return decision
   - ALLOW: tool executes normally
   - BLOCK: return block message to agent, tool does not execute
```

### User Override

If user says "override hook" or "bypass guard":
- Set `override_next = true` in session state
- Allow next tool call through
- Log override to `.copilot/state.md` for audit trail
- Reset `override_next = false` after one tool call

## Component 2: Research Workflow Skill

**File:** `self/skills/research-workflow.skill.md`

**Frontmatter:**
```yaml
---
name: research-workflow
description: Research pipeline workflow enforcement. Use when coordinating any research stage (literature/ideation/experiment/writing/polishing/review/rebuttal). Provides mandatory checklist and state machine rules.
---
```

**Purpose:** Provide workflow checklist and hard gates that research-copilot must follow

### Mandatory Checklist

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

### Hard Gates

```markdown
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
When entering PLANNING state (user asks "what's next", "full pipeline", "submission sprint"), you MUST run a structured interview before committing to a plan. Use AskUserQuestion to clarify scope, constraints, and success criteria.

Do not assume you know what the user wants. Ask.
</HARD-GATE>

<HARD-GATE id="state-output-audit">
After every sub-agent delegation, you MUST audit the STATE_OUTPUT block. Verify:
- Current state is END or appropriate terminal state
- Evidence field is valid (file path or tool call ID)
- Action completed describes what was done

Do not proceed if audit fails. Re-delegate with refined prompt or escalate to user.
</HARD-GATE>
```

### State Machine Rules

The skill includes a simplified reference to the state machine from the agent file:

```
Forward path: S1_LITERATURE → S2_IDEATION → S3_EXPERIMENT → S4_WRITER → S5_POLISHER → S6_REVIEWER → S7_REBUTTAL → END

Back-edges (gated behind AskUserQuestion):
- S3 → S2 (experiment shows fundamental flaw)
- S3 → S1 (cannot pick next ablation)
- S4 → S3 (missing plot/data)
- S4 → S2 (writing exposes contradiction)
- S6 → S3 (critical gap requires new experiment)
- S6 → S2 (critical gap shows unsupported contribution)
- S7 → S3 (reviewer requires new experiment)
- S7 → S2 (reviewer undermines novelty)

Loop counters (3-strike rule):
- Each back-edge has a counter in .copilot/state.md
- After 3 fires of the same back-edge, hard-stop via AskUserQuestion
```

### Delegation Prompt Template

Every Agent call MUST include all six fields:

```
Context & stage: <user is at SN, last round did X, why we are doing this now>
This round's goal: <what this round completes, and what it explicitly does NOT do>
Available facts: <.copilot/<file>.md paths, workspace file paths, specified PDFs, etc.>
Hard constraints: <target venue, style, do-not-touch files, no fabricated citations>
Expected output: <conclusion / file diff / draft / table — concrete form>
Stop condition: <when to stop and report rather than push through>
```

### Anti-Patterns

| Thought | Reality |
|---------|---------|
| "I'll just run this quick experiment" | STOP. Delegate to copilot-experiment. |
| "Let me list the tasks first" | STOP. Call TaskCreate tool. |
| "I can design this experiment myself" | STOP. Delegate to copilot-ideation. |
| "The sub-agent finished, moving on" | STOP. Audit STATE_OUTPUT block first. |
| "This is too simple to need delegation" | STOP. Delegation is mandatory regardless of perceived simplicity. |
| "I'll just check one thing before delegating" | STOP. Delegate first, let sub-agent do the checking. |

### Skill Activation Behavior

When research-workflow skill is invoked:

1. Create tasks for the 9 checklist items via TaskCreate
2. Mark each task complete as the agent progresses through states
3. Before state transitions, verify prerequisite tasks are complete
4. If agent tries to skip ahead, remind them of incomplete tasks

## Component 3: Agent Modification

**File:** `self/agents/research-copilot.agent.md`

### Changes

**1. Add initialization section (after frontmatter, before state machine):**

```markdown
## Initialization

On first invocation, you MUST:

1. Invoke research-workflow skill via Skill tool
2. Follow the skill's 9-step checklist for every state transition
3. The skill defines 5 hard gates that cannot be bypassed
4. The research-copilot-guard hook enforces these gates

If you attempt to violate a gate, the hook will block your tool call and return an error message. Acknowledge the violation and perform the correct action.
```

**2. Simplify agent body:**

Remove redundant enforcement prose (now in skill):
- Remove verbose "NEVER do X" statements (now in HARD-GATE blocks)
- Remove "MUST do Y" statements (now in checklist)

Keep domain logic:
- State machine definition (skill references it)
- Delegation prompt template (skill references it)
- Back-edge routing matrix (domain-specific logic)
- Model heterogeneity guidance (domain-specific logic)
- Sub-agent output audit checklist (domain-specific logic)
- `.copilot/` skeleton initialization (domain-specific logic)

**3. Update hard constraints section:**

```markdown
## Hard Constraints

- **MUST follow research-workflow skill** — invoke at startup, follow 9-step checklist for every state transition
- **NEVER run experiments directly** — enforced by research-copilot-guard hook + skill HARD-GATE
- **NEVER skip TaskCreate** — enforced by research-copilot-guard hook + skill HARD-GATE
- **MUST delegate to sub-agents** — enforced by research-copilot-guard hook + skill HARD-GATE
- **MUST audit STATE_OUTPUT blocks** — enforced by skill HARD-GATE
- **MUST enforce capability gates** — interview-gate before PLANNING, validation-gate at S6_REVIEWER
- **MUST stop at approval gates** — every state transition uses AskUserQuestion in pipeline mode
- **MUST gate every back-edge behind AskUserQuestion** — never unilaterally route backward
- **MUST hard-stop at 3 loop fires** — when any counter reaches 3, do not dispatch that back-edge again
- **Resource honesty** — for long tasks estimate cost and ask user before proceeding
- **NEVER fabricate** — data, citations, experiment results must be verifiable
```

## Enforcement Flow

```
1. User request arrives
   ↓
2. research-copilot invokes research-workflow skill (if not already invoked)
   ↓
3. Skill creates 9 checklist tasks via TaskCreate
   ↓
4. Agent follows checklist, attempts tool call (e.g., Bash to run experiment)
   ↓
5. research-copilot-guard hook intercepts (PreToolUse event)
   ↓
6. Hook checks blocking patterns
   ↓
   ├─ ALLOW → Tool executes normally
   │          ↓
   │          Agent continues, marks task complete
   │
   └─ BLOCK → Return block message to agent
              ↓
              Agent receives error, acknowledges violation
              ↓
              Agent performs correct action (e.g., Agent tool call to copilot-experiment)
              ↓
              Hook allows corrected action through
              ↓
              Agent continues, marks task complete
```

## Error Recovery

When the hook blocks an action:

1. Hook returns block message to agent as tool error
2. Agent must:
   - Acknowledge the violation ("I attempted to run the experiment directly, which violates the experiment-delegation gate")
   - Explain what it should have done instead ("I should delegate to copilot-experiment via Agent tool")
   - Perform the correct action (call Agent tool with subagent_type='copilot-experiment')
3. Hook allows the corrected action through
4. Agent continues with workflow

## Benefits

1. **Hard enforcement** — Hook cannot be bypassed by agent reasoning
2. **Clear workflow** — Skill provides explicit checklist and gates
3. **Clean separation** — Hook = police, Skill = guide, Agent = domain expert
4. **Inspectable** — User sees block messages in real-time
5. **Recoverable** — Agent can correct violations without user intervention
6. **Reusable** — Other agents could adopt the same workflow skill
7. **Maintainable** — Enforcement logic is centralized in hook, not scattered across agent prose

## Implementation Notes

### Hook Implementation

The hook is implemented as a prompt-based hook (not executable script):

```markdown
---
name: research-copilot-guard
event: PreToolUse
agent: research-copilot
---

You are a workflow enforcement guard for the research-copilot agent.

Your job: intercept tool calls and block violations of workflow discipline.

[Detection logic and blocking rules as specified above]

Return format:
- ALLOW: `{"allow": true}`
- BLOCK: `{"allow": false, "message": "<block message>"}`
```

### Skill Implementation

The skill follows standard skill format:

```markdown
---
name: research-workflow
description: Research pipeline workflow enforcement...
---

# Research Workflow

[Checklist, hard gates, state machine rules, templates, anti-patterns as specified above]
```

### Agent Modification

Minimal changes to existing agent file:
- Add initialization section (5 lines)
- Update hard constraints section (add skill reference)
- Remove redundant enforcement prose (simplify body)
- Keep all domain logic intact

## Testing Strategy

1. **Hook blocking tests:**
   - Attempt direct experiment execution → should block
   - Attempt planning without TaskCreate → should block
   - Attempt to skip sub-agent delegation → should block
   - Attempt to skip interview gate → should block

2. **Skill checklist tests:**
   - Invoke skill → should create 9 tasks
   - Complete workflow → should mark all tasks complete
   - Skip a step → should remind about incomplete tasks

3. **Error recovery tests:**
   - Trigger block → agent should acknowledge and correct
   - Corrected action → should be allowed through

4. **User override tests:**
   - User says "override hook" → next tool call should be allowed
   - Override should be logged to `.copilot/state.md`

## YAGNI Boundaries

**Not doing:**
- Hook-based enforcement for other agents (only research-copilot for now)
- Executable script hooks (using prompt-based hooks only)
- Automatic violation correction (agent must correct manually)
- Violation metrics/analytics (just block and log)
- Hook configuration UI (edit hook file directly)

## Success Criteria

1. research-copilot cannot run experiments directly (hook blocks it)
2. research-copilot cannot list tasks without calling TaskCreate (hook blocks it)
3. research-copilot must delegate to sub-agents for S2/S3 states (hook enforces it)
4. research-copilot must run interview before PLANNING (hook enforces it)
5. Skill checklist is created and followed for every workflow
6. User can see block messages and understand what went wrong
7. Agent can recover from violations without user intervention

---

**Next step:** Invoke writing-plans skill to create implementation plan
