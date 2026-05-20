# Agent State Machine Specification

**Version**: 1.0  
**Date**: 2026-05-21  
**Purpose**: Defines the state machine format and rules for all research copilot agents

## State Definition Format

Every agent must track its current state and history in this exact format:

```markdown
**当前状态**: <STATE_NAME>
**状态历史**: [<STATE_1>, <STATE_2>, ...]
```

**Rules**:
- State names must be UPPERCASE_WITH_UNDERSCORES
- Initial state is always `UNINITIALIZED`
- State history is a chronological list of all states visited

## State Transition Table Structure

Every agent must define its state machine as a table:

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|------|--------------|---------|---------|---------------|
| UNINITIALIZED | Load context | none | Context summary | [STATE_A] |
| STATE_A | Perform action | gate-type | Output format | [STATE_B, STATE_C] |

**Columns**:
- **状态**: State name (UPPERCASE_WITH_UNDERSCORES)
- **必须完成的动作**: Mandatory action before leaving this state
- **能力门控**: Capability gate type (`none`, `interview-gate`, `validation-gate`, `execution-gate`)
- **输出格式**: Required output format for this state
- **可能的下一状态**: List of allowed next states (must be non-empty except for END state)

## Mandatory STATE_OUTPUT Block

Every agent response must end with this structured block:

```
[STATE_OUTPUT]
Previous: <previous state name>
Current: <current state name>
Action completed: <brief description of what was done>
Capability gate: <passed/not-required/FAILED>
Evidence: <file:line or tool call ID>
Next allowed: [<state1>, <state2>, ...]
Transition reason: <why this transition was chosen>
[/STATE_OUTPUT]
```

**Field requirements**:
- **Previous**: State before this response (or `UNINITIALIZED` if first response)
- **Current**: State after completing this response's action
- **Action completed**: One-line description of the action taken
- **Capability gate**: 
  - `passed` if gate was required and skill was called
  - `not-required` if no gate for this transition
  - `FAILED` if gate was required but skill was not called
- **Evidence**: Verifiable proof of action completion (file path with line number, or tool call ID from history)
- **Next allowed**: List of states that can follow (copied from transition table)
- **Transition reason**: Brief explanation of why this next state was chosen

**Error handling**: If STATE_OUTPUT is malformed or missing required fields, the conductor will reject the response and require retry.

## State Machine Patterns

### Pattern 1: Linear Flow
```
S0 → S1 → S2 → S3 → END
```
No branches. Each state has exactly one next state.

### Pattern 2: Single Branch
```
S0 → S1 → S2 → S3 → END
           ↓
           S4 → S2
```
One decision point. State S1 can transition to S2 or S4 based on condition.

### Pattern 3: Iteration Loop
```
S0 → S1 → S2 → S3 → END
           ↑      ↓
           └──────┘
```
State S3 can loop back to S2 for iteration. Must have exit condition to reach END.

### Pattern 4: Back-edge
```
S0 → S1 → S2 → S3 → S4 → END
           ↑      ↓
           └──────┘
```
State S3 can return to earlier state S2 if validation fails. Must have forward progress condition.

## Error Handling

### Malformed STATE_OUTPUT

If STATE_OUTPUT block is missing or malformed:
1. Conductor outputs: `[STATE_ERROR: malformed-output]`
2. Lists missing or invalid fields
3. Requires agent to retry with correct format

### Invalid State Transition

If agent attempts transition not in "Next allowed" list:
1. Conductor outputs: `[STATE_ERROR: invalid-transition]`
2. Shows: `Attempted: <current> → <attempted_next>, Allowed: [<allowed_states>]`
3. Requires agent to choose valid transition

### Capability Gate Failure

If capability gate is required but skill was not called:
1. Agent outputs: `Capability gate: FAILED` in STATE_OUTPUT
2. Agent lists available skills matching gate category
3. Agent immediately calls required skill and retries transition

## Verification Rules

**State consistency**: `Current` state in STATE_OUTPUT must match `**当前状态**` in state definition.

**History tracking**: Each new state must be appended to `**状态历史**`.

**Evidence requirement**: Evidence must be verifiable. File paths must exist. Tool call IDs must be in recent history.

**Transition validity**: `Next allowed` must exactly match the transition table for current state.
