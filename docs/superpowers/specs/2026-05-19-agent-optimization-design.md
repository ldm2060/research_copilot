# Agent Optimization Design

**Date**: 2026-05-19  
**Author**: Claude Opus 4.7  
**Status**: Approved by user, pending implementation

## Executive Summary

This design optimizes the 8 research copilot agents in `self/agents/` to address three core problems:

1. **Weak model constraint** — agents don't follow instructions reliably
2. **Flow deviation** — agents abandon the prescribed workflow mid-execution
3. **Skill invocation failure** — agents rarely call skills as intended

**Solution**: State machine + capability-gated transitions. Each agent becomes a state machine with mandatory state output blocks and capability gates that require calling specific skill categories before certain transitions.

**Key Design Choices** (based on user preferences):
- **Skill enforcement**: Mandatory for certain transitions, but category-based (not specific skill names)
- **Flow flexibility**: Allows conditional branches and loops (not strictly linear)
- **Constraint priority**: Prioritizes constraint strength over brevity (150-180 lines per agent)
- **Migration strategy**: Full rewrite of all 8 agents in phases

## Problem Analysis

### Problem 1: Weak Model Constraint

**Root cause**: Current agents rely on narrative guidance ("you should", "recommended") rather than hard constraints. Models can selectively ignore these.

**Evidence**: Agents use phrases like "建议" (suggest), "推荐" (recommend), "应该" (should) — all weak modals.

**Impact**: Models deviate from intended behavior without triggering errors.

### Problem 2: Flow Deviation

**Root cause**: Workflow is described as linear text. After reading, models "forget" subsequent steps. No explicit "current step" or "next step must be X" tracking.

**Evidence**: Workflow and constraints are mixed together. Models can't distinguish "must do" from "can do".

**Impact**: Models start following the workflow but gradually drift into free-form execution.

### Problem 3: Skill Invocation Failure

**Root cause**: Skill invocation instructions are buried in long text, using "capability phrases" rather than explicit tool calls. Models must "infer" when to use skills rather than being **forced** at specific steps.

**Evidence**: No pre-checks like "if you don't call X skill, you cannot proceed".

**Impact**: Models skip skill calls, missing critical validation and interview steps.

### Problem 4: Information Density

**Root cause**: Current agents average 200-270 lines with repetitive explanations, examples, and tables. True constraint instructions are diluted.

**Evidence**: Large sections devoted to examples and explanations rather than executable constraints.

**Impact**: Signal-to-noise ratio is low. Critical constraints are hard to find.

## Design Solution

### Core Concept: Capability-Gated State Machine

Each agent is a state machine where:

1. **States are explicit** — agent must output current state in structured block
2. **Transitions are constrained** — can only move to allowed next states
3. **Capability gates guard transitions** — certain transitions require calling a skill category first
4. **Evidence is mandatory** — each state completion must provide verifiable evidence

### State Machine Components

#### 1. State Definition

```markdown
**当前状态**: UNINITIALIZED
**状态历史**: []
```

Every agent tracks its current state and history.

#### 2. State Transition Table

| 状态 | 必须完成的动作 | 能力门控 | 输出格式 | 可能的下一状态 |
|------|--------------|---------|---------|---------------|
| S0 | Action | Gate | Format | [S1, S2] |
| S1 | Action | Gate | Format | [S2, S3] |

Hard constraints on what must happen in each state and where you can go next.

#### 3. Mandatory Output Block

Every response must end with:

```
[STATE_OUTPUT]
Previous: <previous state>
Current: <current state>
Action completed: <what was done>
Capability gate: <passed/not-required/FAILED>
Evidence: <file:line or tool call ID>
Next allowed: [<state1>, <state2>, ...]
Transition reason: <why this transition>
[/STATE_OUTPUT]
```

This makes state tracking explicit and verifiable.

#### 4. Capability Gates

Certain state transitions require calling a **skill category** first:

| Gate Type | Trigger | Required Skill Category | Examples |
|-----------|---------|------------------------|----------|
| interview-gate | Need user input/clarification | interview-class | deep-interview, user-preference-interview |
| validation-gate | Need to verify design/results | validation-class | grill-with-docs, spec-validator, de-ai-checker |
| execution-gate | Need to execute complex task | execution-class | experiment-runner, paper-writer |

**Verification**: Check tool call history for `Skill(skill='<matching-pattern>')`. If not found, transition **fails** and must retry.

### Benefits

1. **Strong constraint** — STATE_OUTPUT is mandatory, models can't bypass
2. **Skill enforcement** — capability gates make skill calls a precondition for transitions
3. **Trackable** — every state output is structured, conductor can parse
4. **Flexible** — state machines support branches and loops
5. **Debuggable** — state history shows exactly where agent is

### Trade-offs

1. **Complexity** — models must understand state machine concept (Opus/Sonnet can, Haiku might struggle)
2. **Length** — state tables + output formats add ~30-50 lines per agent
3. **Dependency** — relies on model's instruction-following ability (if model ignores STATE_OUTPUT, mechanism fails)

## Detailed Agent Designs

### Agent Summary

| Agent | Model | States | Gates | Branches | Lines |
|-------|-------|--------|-------|----------|-------|
| copilot-literature | haiku | 7 | 0 | 1 | ~150 |
| copilot-ideation | opus | 11 | 2 | 2 | ~180 |
| copilot-experiment | sonnet | 9 | 2 | 2 | ~170 |
| copilot-writer | sonnet | 8 | 1 | 1 | ~160 |
| copilot-polisher | sonnet | 7 | 1 | 0 | ~140 |
| copilot-reviewer | opus | 8 | 0 | 0 | ~160 |
| copilot-rebuttal | sonnet | 8 | 1 | 1 | ~150 |
| research-copilot | sonnet | 11 | 2 | 2 | ~180 |

**Total**: ~1,290 lines (avg 161 lines/agent)  
**Current**: ~2,000 lines (avg 250 lines/agent)  
**Reduction**: ~35%

### State Machine Patterns

#### Pattern 1: Linear Flow (copilot-polisher)

```
UNINITIALIZED → CONTEXT_LOADED → SCOPE_DEFINED → POLISHING → 
POLISHED → VERIFYING → VERIFIED → WRITTEN → END
```

No branches, strict sequence.

#### Pattern 2: Single Branch (copilot-literature)

```
UNINITIALIZED → CONTEXT_LOADED → SEARCHING → PAPERS_FOUND → 
STRUCTURED → AWAITING_SELECTION → BASELINE_LOCKED → END
                                ↓
                            SEARCHING (user requests expansion)
```

One decision point for user choice.

#### Pattern 3: Iteration Loop (copilot-experiment)

```
UNINITIALIZED → CONTEXT_LOADED → DESIGN_READY → APPROVED → 
EXECUTING → COMPLETED → VERIFIED → JUDGED → END
                        ↑                      ↓
                        └──────────────────────┘
                        (on-trajectory: iterate)
```

Autonomous iteration based on status.

#### Pattern 4: Back-edge (copilot-writer)

```
UNINITIALIZED → CONTEXT_LOADED → SCOPE_DEFINED → FACTS_EXTRACTED → 
DRAFTING → DRAFTED → VERIFYING → VERIFIED → WRITTEN → END
                        ↑            ↓
                        └────────────┘
                    (missing facts: back-edge)
```

Can return to earlier state if validation detects gaps.

### Capability Gate Specification

#### interview-gate

**Purpose**: When needing user interaction, preference collection, requirement clarification

**Required skill categories**:
- `deep-interview` (recommended)
- `quick-interview`
- `user-preference-interview`
- Any skill matching `*-interview`

**Verification**: Check tool call history for `Skill(skill='<name>')` where `<name>` matches pattern

**Failure handling**: Output `[STATE_ERROR: interview-gate-failed]`, list available interview skills, require retry

#### validation-gate

**Purpose**: When needing to verify design, results, text quality

**Required skill categories**:
- `grill-with-docs` (recommended)
- `spec-validator`
- `metric-validator`
- `de-ai-checker`
- Any skill matching `*-validator` or `*-checker`

**Verification**: Check tool call history for `Skill(skill='<name>')` where `<name>` matches pattern

**Failure handling**: Output `[STATE_ERROR: validation-gate-failed]`, list available validation skills, require retry

#### execution-gate

**Purpose**: When needing to execute complex, multi-step tasks

**Required skill categories**:
- `experiment-runner`
- `paper-writer`
- `citation-manager`
- Any skill matching `*-runner` or `*-executor`

**Verification**: Check tool call history for `Skill(skill='<name>')` where `<name>` matches pattern

**Failure handling**: Output `[STATE_ERROR: execution-gate-failed]`, list available execution skills, require retry

### Per-Agent State Machines

(See full designs in previous messages for complete state tables, output formats, and error handling for each of the 8 agents)

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Deliverables**:
1. `self/AGENT_STATE_MACHINE_SPEC.md` — shared state machine rules
2. `self/CAPABILITY_GATE_SPEC.md` — capability gate definitions
3. Rewrite `copilot-literature` (simplest, no gates)

**Success criteria**: copilot-literature correctly outputs STATE_OUTPUT blocks and follows linear flow

### Phase 2: Core Agents (Week 2-3)

**Deliverables**:
1. Rewrite `copilot-ideation` (opus, 2 gates)
2. Rewrite `copilot-experiment` (sonnet, 2 gates, iteration loop)

**Success criteria**: Both agents pass capability gates and handle autonomous iteration

### Phase 3: Writing Pipeline (Week 4)

**Deliverables**:
1. Rewrite `copilot-writer` (sonnet, 1 gate, back-edge)
2. Rewrite `copilot-polisher` (sonnet, 1 gate, linear)
3. Rewrite `copilot-reviewer` (opus, no gates, two-stage)
4. Rewrite `copilot-rebuttal` (sonnet, 1 gate, back-edge)

**Success criteria**: Writing pipeline agents correctly handle back-edges and validation

### Phase 4: Conductor (Week 5)

**Deliverables**:
1. Rewrite `research-copilot` (sonnet, 2 gates, complex routing)

**Success criteria**: Conductor correctly delegates, audits, and gates back-edges

### Phase 5: Validation & Rollback (Week 6)

**Deliverables**:
1. Create validation skills if missing (`deep-interview`, `grill-with-docs`)
2. Test all 8 agents end-to-end
3. Document rollback procedure

**Success criteria**: Full pipeline S1→S7 works with new agents

## Skill Dependencies

### Required Skills

| Skill | Category | Used By | Fallback if Missing |
|-------|----------|---------|---------------------|
| deep-interview | interview | copilot-ideation, copilot-experiment, research-copilot | Manual AskUserQuestion loop |
| grill-with-docs | validation | copilot-ideation, copilot-experiment, copilot-writer, research-copilot | Manual cross-reference check |
| de-ai-checker | validation | copilot-polisher | Manual vocabulary scan |

### Optional Skills

| Skill | Category | Used By | Fallback if Missing |
|-------|----------|---------|---------------------|
| quick-interview | interview | Any agent | Use deep-interview |
| spec-validator | validation | Any agent | Use grill-with-docs |
| metric-validator | validation | copilot-experiment | Manual log parsing |

### Skill Creation Priority

1. **High priority**: `deep-interview`, `grill-with-docs` — used by multiple agents
2. **Medium priority**: `de-ai-checker` — used by copilot-polisher only
3. **Low priority**: Other validators — can use grill-with-docs as fallback

## Migration Strategy

### Backup Plan

1. **Before rewriting**: Copy all current agents to `self/agents/backup-YYYY-MM-DD/`
2. **Version control**: Commit current state with message "backup: agents before state-machine rewrite"
3. **Rollback trigger**: If any agent fails to produce STATE_OUTPUT blocks after 3 test runs

### Migration Steps

1. **Phase 1**: Rewrite copilot-literature, test in isolation
   - If successful: proceed to Phase 2
   - If failed: analyze failure, adjust design, retry

2. **Phase 2-4**: Rewrite remaining agents one at a time
   - Test each agent in isolation before proceeding
   - Keep backup agents available for comparison

3. **Phase 5**: Full integration test
   - Run complete S1→S7 pipeline
   - Compare outputs with backup agents
   - If new agents produce better results: commit and delete backups
   - If new agents fail: rollback and revise design

### Rollback Procedure

If new agents fail after deployment:

```bash
# Restore backup agents
cp self/agents/backup-YYYY-MM-DD/*.md self/agents/

# Commit rollback
git add self/agents/
git commit -m "rollback: restore pre-state-machine agents"

# Document failure
echo "Failure reason: <description>" >> docs/superpowers/specs/2026-05-19-agent-optimization-rollback.md
```

## Risk Assessment

### High Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Models ignore STATE_OUTPUT blocks | Medium | Critical | Emphasize with bold, repetition; add error recovery |
| Haiku can't understand state machines | Medium | High | Keep copilot-literature state machine simple (linear) |
| Capability gates fail to enforce | Medium | High | Add STATE_ERROR recovery; immediate skill call on failure |

### Medium Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Length doesn't actually decrease | High | Medium | Accept if constraint strength improves |
| Skills don't exist | Low | Medium | Document fallback procedures |
| Migration breaks existing workflows | Low | High | Thorough testing; keep backups |

### Low Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| State machine too complex for users | Low | Low | Provide clear documentation |
| Performance degradation | Low | Medium | Monitor execution time |

## Success Metrics

### Quantitative

1. **STATE_OUTPUT compliance**: ≥95% of agent responses include STATE_OUTPUT block
2. **Capability gate pass rate**: ≥90% of gated transitions successfully call required skills
3. **Flow adherence**: ≥85% of agent executions follow prescribed state sequence
4. **Length reduction**: 30-40% fewer lines per agent (achieved: ~35%)

### Qualitative

1. **User feedback**: Agents feel more "disciplined" and "predictable"
2. **Debugging ease**: State history makes it easy to identify where agent deviated
3. **Skill usage**: Skills are called consistently at appropriate points

## Open Questions

1. **Q**: What if a required skill doesn't exist in the user's environment?  
   **A**: Agent outputs STATE_ERROR and suggests fallback (manual process)

2. **Q**: Can users override capability gates?  
   **A**: No. Gates are hard constraints. If user wants to skip, they must modify agent file.

3. **Q**: How to handle state machine bugs?  
   **A**: State history in STATE_OUTPUT makes debugging straightforward. Fix state table and redeploy.

4. **Q**: What if model outputs malformed STATE_OUTPUT?  
   **A**: Conductor's validation-gate will catch it during audit. Reject and re-dispatch.

## Conclusion

This design addresses all three core problems through a unified state machine + capability gate approach. The solution prioritizes constraint strength over brevity, uses category-based skill enforcement, and supports flexible branching flows.

**Key innovations**:
1. Mandatory STATE_OUTPUT blocks make state tracking explicit
2. Capability gates enforce skill calls as transition preconditions
3. Category-based skill matching avoids hardcoding specific skill names
4. State machines support branches and loops while maintaining discipline

**Next steps**:
1. User reviews this design document
2. Create shared specification files (AGENT_STATE_MACHINE_SPEC.md, CAPABILITY_GATE_SPEC.md)
3. Begin Phase 1 implementation (copilot-literature)

---

**Design Status**: ✅ Complete, awaiting user review  
**Estimated Implementation Time**: 5-6 weeks  
**Risk Level**: Medium (depends on model instruction-following)
