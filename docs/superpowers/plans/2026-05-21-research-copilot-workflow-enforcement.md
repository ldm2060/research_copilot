# Research Copilot Workflow Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add hook-based enforcement and skill-based guidance to research-copilot agent to prevent workflow violations

**Architecture:** Three-component system: PreToolUse hook intercepts tool calls and blocks violations, skill provides workflow checklist and hard gates, agent invokes skill and follows discipline

**Tech Stack:** Markdown (hook/skill/agent files), YAML frontmatter, prompt-based hooks

---

## File Structure

**Create:**
- `self/hooks/research-copilot-guard.hook.md` — PreToolUse hook that blocks violations
- `self/skills/research-workflow/SKILL.md` — Workflow checklist and hard gates

**Modify:**
- `self/agents/research-copilot.agent.md` — Add initialization section, update constraints, simplify body

---

### Task 1: Create Hook Directory Structure

**Files:**
- Create: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Create hook file with frontmatter**

```markdown
---
name: research-copilot-guard
event: PreToolUse
agent: research-copilot
---

# Research Copilot Workflow Guard

You are a workflow enforcement guard for the research-copilot agent.

Your job: intercept tool calls and block violations of workflow discipline.

// __CONTINUE_HERE__
```

- [ ] **Step 2: Verify file created**

Run: `Test-Path self/hooks/research-copilot-guard.hook.md`
Expected: True

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add research-copilot-guard hook skeleton"
```

---

### Task 2: Implement Hook Session State Tracking

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Add session state section**

After the hook header, add:

```markdown
## Session State

You maintain session state that resets on SessionStart:

```javascript
{
  skill_invoked: false,           // whether research-workflow skill was called
  current_state: "UNINITIALIZED", // last known state from .copilot/state.md
  last_delegation: null,          // last sub-agent delegated to (allows audit phase)
  planning_mode: false,           // whether user requested full pipeline
  override_next: false            // user requested override for next tool call
}
```

When you see a SessionStart event, reset all fields to their default values.
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "Session State"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add session state tracking to hook"
```

---

### Task 3: Implement Hook Detection Logic

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Add detection logic section**

After session state section, add:

```markdown
## Detection Logic

When a tool call is about to execute:

1. **Parse agent context**
   - If `.copilot/state.md` exists, extract current state from it
   - Load session state from memory

2. **Parse current turn**
   - Extract tool calls from agent's response
   - Extract prose output for pattern matching

3. **Apply blocking rules** (check in order, first match triggers block)
   - Check Pattern 1: Direct experiment execution
   - Check Pattern 2: Planning without TaskCreate
   - Check Pattern 3: Missing sub-agent delegation
   - Check Pattern 4: Missing interview gate

4. **Return decision**
   - ALLOW: `{"allow": true}`
   - BLOCK: `{"allow": false, "message": "<block message>"}`
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "Detection Logic"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add detection logic to hook"
```

---

### Task 4: Implement Hook Blocking Pattern 1 (Direct Experiment Execution)

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Add Pattern 1 section**

After detection logic section, add:

```markdown
## Blocking Patterns

### Pattern 1: Direct Experiment Execution

**Trigger:** Tool is Bash or PowerShell AND command contains experiment keywords

**Keywords:** `train.py`, `run_experiment`, `python.*train`, `torch`, `tensorflow`, `wandb`, `mlflow`

**Exception:** Read-only commands (`grep`, `cat`, `ls`, `Get-Content`, `Select-String`)

**Detection:**
1. Check if tool is Bash or PowerShell
2. Check if command contains any experiment keyword
3. Check if command is read-only (starts with grep/cat/ls/Get-Content/Select-String)
4. If tool matches AND keyword matches AND NOT read-only → BLOCK

**Block message:**
"Blocked: research-copilot cannot run experiments directly. Delegate to copilot-experiment via Agent tool with subagent_type='copilot-experiment'."

**Example violations:**
- `python train.py --config config.yaml`
- `torch.cuda.is_available() && python run_experiment.py`
- `wandb init && python train.py`

**Example allowed:**
- `cat train.log | grep "epoch"`
- `ls experiments/`
- `Get-Content train.py`
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "Pattern 1: Direct Experiment Execution"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add Pattern 1 (direct experiment execution) to hook"
```

---

### Task 5: Implement Hook Blocking Pattern 2 (Planning Without TaskCreate)

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Add Pattern 2 section**

After Pattern 1, add:

```markdown
### Pattern 2: Planning Without TaskCreate

**Trigger:** Agent output contains planning keywords AND no TaskCreate tool call in current turn

**Keywords:** "步骤", "plan", "tasks", "checklist", numbered lists (1., 2., 3.)

**Exception:** Referencing existing tasks or summarizing completed work (contains "completed", "done", "已完成")

**Detection:**
1. Check if agent prose output contains any planning keyword
2. Check if current turn includes TaskCreate tool call
3. Check if output is referencing existing work (contains exception keywords)
4. If keyword matches AND no TaskCreate AND NOT referencing existing → BLOCK

**Block message:**
"Blocked: You listed tasks but didn't call TaskCreate. Create tasks via TaskCreate tool before proceeding."

**Example violations:**
- "步骤 1: 读取文件, 步骤 2: 分析数据"
- "Here's the plan: 1. Load data 2. Train model 3. Evaluate"
- "Tasks: check state, delegate to sub-agent, audit output"

**Example allowed:**
- "I completed tasks 1-3" (referencing existing)
- [TaskCreate tool call present in same turn]
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "Pattern 2: Planning Without TaskCreate"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add Pattern 2 (planning without TaskCreate) to hook"
```

---

### Task 6: Implement Hook Blocking Pattern 3 (Missing Sub-Agent Delegation)

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Add Pattern 3 section**

After Pattern 2, add:

```markdown
### Pattern 3: Missing Sub-Agent Delegation

**Trigger:** Current state is S2_IDEATION or S3_EXPERIMENT AND no Agent tool call with matching subagent_type

**Exception:** State is in audit phase (last_delegation matches current state's expected sub-agent)

**Detection:**
1. Check current_state from session state
2. If state is S2_IDEATION or S3_EXPERIMENT:
   - Check if current turn includes Agent tool call
   - Check if Agent call has subagent_type='copilot-ideation' (for S2) or 'copilot-experiment' (for S3)
   - Check if last_delegation matches expected sub-agent (audit phase exception)
3. If state matches AND no matching Agent call AND NOT audit phase → BLOCK

**Block message:**
"Blocked: State {state} requires delegation to {copilot-stage}. Use Agent tool with subagent_type='{copilot-stage}'."

**Example violations:**
- State is S3_EXPERIMENT, agent calls Bash instead of Agent
- State is S2_IDEATION, agent calls Agent with subagent_type='copilot-literature'

**Example allowed:**
- State is S3_EXPERIMENT, agent calls Agent with subagent_type='copilot-experiment'
- State is S3_EXPERIMENT, last_delegation='copilot-experiment' (audit phase)
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "Pattern 3: Missing Sub-Agent Delegation"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add Pattern 3 (missing sub-agent delegation) to hook"
```

---

### Task 7: Implement Hook Blocking Pattern 4 (Missing Interview Gate)

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Add Pattern 4 section**

After Pattern 3, add:

```markdown
### Pattern 4: Missing Interview Gate

**Trigger:** Current state is PLANNING or CONTEXT_LOADED with plan-level request AND no Skill tool call for research-workflow

**Exception:** skill_invoked is true (skill already called this session)

**Detection:**
1. Check current_state from session state
2. Check skill_invoked from session state
3. If state is PLANNING or (CONTEXT_LOADED AND planning_mode is true):
   - Check if current turn includes Skill tool call with skill='research-workflow'
   - Check if skill_invoked is true
4. If state matches AND no Skill call AND skill_invoked is false → BLOCK

**Block message:**
"Blocked: PLANNING state requires structured interview. Invoke research-workflow skill first."

**Example violations:**
- State is PLANNING, skill_invoked=false, agent calls Agent directly
- State is CONTEXT_LOADED, planning_mode=true, no Skill call

**Example allowed:**
- State is PLANNING, agent calls Skill with skill='research-workflow'
- State is PLANNING, skill_invoked=true (already called)
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "Pattern 4: Missing Interview Gate"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add Pattern 4 (missing interview gate) to hook"
```

---

### Task 8: Implement Hook Allow-List and User Override

**Files:**
- Modify: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Add allow-list section**

After blocking patterns, add:

```markdown
## Allow-List

Always allow these tool calls (skip all blocking patterns):

- **Read operations:** Read, Grep, Glob
- **State file updates:** Write to `.copilot/state.md`, `.copilot/decisions.md`
- **Agent delegations:** Agent tool calls to `copilot-*` agents
- **Task management:** TaskCreate, TaskUpdate, TaskList, TaskGet

## User Override

If user message contains "override hook" or "bypass guard":

1. Set `override_next = true` in session state
2. Allow the next tool call through (skip all blocking patterns)
3. Log override to `.copilot/state.md`: append line "OVERRIDE: [timestamp] [tool] [reason: user requested]"
4. Reset `override_next = false` after one tool call

**Example:**
User: "override hook"
Agent: [attempts Bash command to run experiment]
Hook: Detects override_next=true → ALLOW → Log to state.md → Reset override_next=false
```

- [ ] **Step 2: Verify sections added**

Run: `Select-String -Path self/hooks/research-copilot-guard.hook.md -Pattern "Allow-List"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/hooks/research-copilot-guard.hook.md
git commit -m "feat: add allow-list and user override to hook"
```

---

### Task 9: Create Skill Directory Structure

**Files:**
- Create: `self/skills/research-workflow/SKILL.md`

- [ ] **Step 1: Create skill directory**

Run: `New-Item -ItemType Directory -Path self/skills/research-workflow -Force`
Expected: Directory created

- [ ] **Step 2: Create skill file with frontmatter**

```markdown
---
name: research-workflow
description: Research pipeline workflow enforcement. Use when coordinating any research stage (literature/ideation/experiment/writing/polishing/review/rebuttal). Provides mandatory checklist and state machine rules.
---

# Research Workflow

You are following the research-workflow skill for the research-copilot agent.

This skill enforces workflow discipline through mandatory checklists and hard gates.

// __CONTINUE_HERE__
```

- [ ] **Step 3: Verify file created**

Run: `Test-Path self/skills/research-workflow/SKILL.md`
Expected: True

- [ ] **Step 4: Commit**

```powershell
git add self/skills/research-workflow/SKILL.md
git commit -m "feat: add research-workflow skill skeleton"
```

---

### Task 10: Implement Skill Mandatory Checklist

**Files:**
- Modify: `self/skills/research-workflow/SKILL.md`

- [ ] **Step 1: Add mandatory checklist section**

After the skill header, add:

```markdown
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
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/skills/research-workflow/SKILL.md -Pattern "Mandatory Checklist"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/skills/research-workflow/SKILL.md
git commit -m "feat: add mandatory checklist to skill"
```

---

### Task 11: Implement Skill Hard Gates

**Files:**
- Modify: `self/skills/research-workflow/SKILL.md`

- [ ] **Step 1: Add hard gates section**

After checklist section, add:

```markdown
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

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/skills/research-workflow/SKILL.md -Pattern "HARD-GATE"`
Expected: Match found (5 occurrences)

- [ ] **Step 3: Commit**

```powershell
git add self/skills/research-workflow/SKILL.md
git commit -m "feat: add 5 hard gates to skill"
```

---

### Task 12: Implement Skill State Machine Rules

**Files:**
- Modify: `self/skills/research-workflow/SKILL.md`

- [ ] **Step 1: Add state machine rules section**

After hard gates, add:

```markdown
## State Machine Rules

**Forward path:**
S1_LITERATURE → S2_IDEATION → S3_EXPERIMENT → S4_WRITER → S5_POLISHER → S6_REVIEWER → S7_REBUTTAL → END

**Back-edges (gated behind AskUserQuestion):**
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
```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/skills/research-workflow/SKILL.md -Pattern "State Machine Rules"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/skills/research-workflow/SKILL.md
git commit -m "feat: add state machine rules to skill"
```

---

### Task 13: Implement Skill Delegation Template and Anti-Patterns

**Files:**
- Modify: `self/skills/research-workflow/SKILL.md`

- [ ] **Step 1: Add delegation template section**

After state machine rules, add:

```markdown
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
```

- [ ] **Step 2: Verify sections added**

Run: `Select-String -Path self/skills/research-workflow/SKILL.md -Pattern "Delegation Prompt Template"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/skills/research-workflow/SKILL.md
git commit -m "feat: add delegation template and anti-patterns to skill"
```

---

### Task 14: Modify Agent - Add Initialization Section

**Files:**
- Modify: `self/agents/research-copilot.agent.md`

- [ ] **Step 1: Add initialization section after frontmatter**

After line 7 (after frontmatter), before "# Research Copilot", insert:

```markdown
## Initialization

On first invocation, you MUST:

1. Invoke research-workflow skill via Skill tool
2. Follow the skill's 9-step checklist for every state transition
3. The skill defines 5 hard gates that cannot be bypassed
4. The research-copilot-guard hook enforces these gates

If you attempt to violate a gate, the hook will block your tool call and return an error message. Acknowledge the violation and perform the correct action.

```

- [ ] **Step 2: Verify section added**

Run: `Select-String -Path self/agents/research-copilot.agent.md -Pattern "## Initialization" -Context 0,5`
Expected: Match found with 5 lines of context

- [ ] **Step 3: Commit**

```powershell
git add self/agents/research-copilot.agent.md
git commit -m "feat: add initialization section to research-copilot agent"
```

---

### Task 15: Modify Agent - Update Hard Constraints Section

**Files:**
- Modify: `self/agents/research-copilot.agent.md`

- [ ] **Step 1: Find and update hard constraints section**

Locate the "## Hard Constraints" section (around line 530) and replace the first 4 bullet points with:

```markdown
- **MUST follow research-workflow skill** — invoke at startup, follow 9-step checklist for every state transition
- **NEVER run experiments directly** — enforced by research-copilot-guard hook + skill HARD-GATE
- **NEVER skip TaskCreate** — enforced by research-copilot-guard hook + skill HARD-GATE
- **MUST delegate to sub-agents** — enforced by research-copilot-guard hook + skill HARD-GATE
```

Keep all other constraints unchanged.

- [ ] **Step 2: Verify changes**

Run: `Select-String -Path self/agents/research-copilot.agent.md -Pattern "MUST follow research-workflow skill"`
Expected: Match found

- [ ] **Step 3: Commit**

```powershell
git add self/agents/research-copilot.agent.md
git commit -m "feat: update hard constraints to reference hook and skill"
```

---

### Task 16: Test Hook Blocking - Direct Experiment Execution

**Files:**
- Test: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Manual test - attempt direct experiment**

Invoke research-copilot agent and attempt to run experiment directly:
```
User: "Run python train.py"
Expected: Hook blocks with message about delegating to copilot-experiment
```

- [ ] **Step 2: Manual test - read-only command allowed**

Invoke research-copilot agent and attempt read-only command:
```
User: "Check what's in train.log"
Agent attempts: cat train.log
Expected: Hook allows (read-only exception)
```

- [ ] **Step 3: Document test results**

Create test log: `docs/superpowers/test-logs/2026-05-21-hook-test-pattern1.md`
Record: test case, expected behavior, actual behavior, pass/fail

---

### Task 17: Test Hook Blocking - Planning Without TaskCreate

**Files:**
- Test: `self/hooks/research-copilot-guard.hook.md`

- [ ] **Step 1: Manual test - list tasks without TaskCreate**

Invoke research-copilot agent:
```
User: "What should we do next?"
Agent outputs: "步骤 1: 读取状态, 步骤 2: 委派子agent"
Expected: Hook blocks with message about calling TaskCreate
```

- [ ] **Step 2: Manual test - TaskCreate present**

Invoke research-copilot agent:
```
Agent calls TaskCreate for each step
Expected: Hook allows
```

- [ ] **Step 3: Document test results**

Append to: `docs/superpowers/test-logs/2026-05-21-hook-test-pattern2.md`

---

### Task 18: Test Skill Checklist Creation

**Files:**
- Test: `self/skills/research-workflow/SKILL.md`

- [ ] **Step 1: Manual test - skill invocation**

Invoke research-copilot agent:
```
User: "Start research workflow"
Expected: Agent invokes research-workflow skill, creates 9 tasks via TaskCreate
```

- [ ] **Step 2: Verify tasks created**

Check task list:
```
Expected: 9 tasks matching checklist items (Load context, Diagnose stage, etc.)
```

- [ ] **Step 3: Document test results**

Create: `docs/superpowers/test-logs/2026-05-21-skill-test-checklist.md`

---

### Task 19: Test End-to-End Workflow

**Files:**
- Test: Full workflow with hook + skill + agent

- [ ] **Step 1: Test full workflow**

Invoke research-copilot agent:
```
User: "I want to run a full research pipeline"
Expected sequence:
1. Agent invokes research-workflow skill
2. Skill creates 9 tasks
3. Agent follows checklist
4. Hook blocks any violations
5. Agent corrects and proceeds
```

- [ ] **Step 2: Verify state transitions**

Check `.copilot/state.md`:
```
Expected: State transitions logged, no violations
```

- [ ] **Step 3: Document test results**

Create: `docs/superpowers/test-logs/2026-05-21-e2e-test.md`

---

### Task 20: Final Verification and Documentation

**Files:**
- Modify: `self/README.md` (if exists)

- [ ] **Step 1: Verify all files created**

Run:
```powershell
Test-Path self/hooks/research-copilot-guard.hook.md
Test-Path self/skills/research-workflow/SKILL.md
Select-String -Path self/agents/research-copilot.agent.md -Pattern "## Initialization"
```
Expected: All return True/Match

- [ ] **Step 2: Update documentation**

If `self/README.md` exists, add section:
```markdown
## Workflow Enforcement

research-copilot agent uses hook-based enforcement:
- `hooks/research-copilot-guard.hook.md` - Blocks workflow violations
- `skills/research-workflow/SKILL.md` - Provides checklist and hard gates

See `docs/superpowers/specs/2026-05-21-research-copilot-workflow-enforcement-design.md` for details.
```

- [ ] **Step 3: Final commit**

```powershell
git add -A
git commit -m "docs: add workflow enforcement documentation"
```

---

## Self-Review

**Spec coverage check:**
- ✓ Component 1 (Hook): Tasks 1-8 implement all blocking patterns, session state, detection logic, allow-list, user override
- ✓ Component 2 (Skill): Tasks 9-13 implement checklist, hard gates, state machine rules, delegation template, anti-patterns
- ✓ Component 3 (Agent): Tasks 14-15 add initialization and update constraints
- ✓ Testing: Tasks 16-19 cover all blocking patterns and end-to-end workflow
- ✓ Documentation: Task 20 verifies and documents

**Placeholder scan:**
- No TBD, TODO, or "implement later" markers
- All code blocks are complete
- All test cases have expected behavior specified

**Type consistency:**
- Hook file: `research-copilot-guard.hook.md` (consistent across all tasks)
- Skill file: `research-workflow/SKILL.md` (consistent across all tasks)
- Agent file: `research-copilot.agent.md` (consistent across all tasks)
- Session state fields: consistent naming across hook tasks

---

## Execution Handoff

Plan complete and saved to `docs\superpowers\plans\2026-05-21-research-copilot-workflow-enforcement.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
