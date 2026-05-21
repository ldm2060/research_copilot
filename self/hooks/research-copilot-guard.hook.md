---
name: research-copilot-guard
event: PreToolUse
agent: research-copilot
---

# Research Copilot Workflow Guard (Specification)

> **NOTE:** This markdown file is the *specification* for the guard's behavior.
> The executable implementation lives at `self/hooks/scripts/research_copilot_guard.py`
> and is registered via `self/hooks/research-copilot-guard.json` and `.claude/settings.json`.
> Update both files when changing the rules.

You are a workflow enforcement guard for the research-copilot agent.
Your job: intercept tool calls and block violations of workflow discipline.

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