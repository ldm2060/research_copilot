# Capability Gate Specification

**Version**: 1.0  
**Date**: 2026-05-21  
**Purpose**: Define capability gates for agent state machine transitions

## Overview

Capability gates are hard constraints that require calling a specific skill category before certain state transitions. Gates enforce skill usage and prevent agents from bypassing critical validation, interview, or execution steps.

## Gate Definitions

### interview-gate

**Purpose**: User interaction, preference collection, requirement clarification

**Required skill categories**:
- `deep-interview` (recommended)
- `quick-interview`
- `user-preference-interview`
- Any skill matching `*-interview`

**Verification**: Check tool call history for `Skill(skill='<name>')` where `<name>` matches pattern

**Failure handling**: Output `[STATE_ERROR: interview-gate-failed]`, list available interview skills, require retry

### validation-gate

**Purpose**: Verify design, results, text quality

**Required skill categories**:
- `grill-with-docs` (recommended)
- `spec-validator`
- `metric-validator`
- `de-ai-checker`
- Any skill matching `*-validator` or `*-checker`

**Verification**: Check tool call history for `Skill(skill='<name>')` where `<name>` matches pattern

**Failure handling**: Output `[STATE_ERROR: validation-gate-failed]`, list available validation skills, require retry

### execution-gate

**Purpose**: Execute complex, multi-step tasks

**Required skill categories**:
- `experiment-runner`
- `paper-writer`
- `citation-manager`
- Any skill matching `*-runner` or `*-executor`

**Verification**: Check tool call history for `Skill(skill='<name>')` where `<name>` matches pattern

**Failure handling**: Output `[STATE_ERROR: execution-gate-failed]`, list available execution skills, require retry

## Verification Procedure

1. Before attempting a gated transition, check tool call history in current conversation turn
2. Search for `Skill(skill='<name>')` calls where `<name>` matches required pattern
3. If match found: gate passes, proceed with transition
4. If no match: gate fails, output STATE_ERROR, halt transition

## STATE_ERROR Recovery

When a capability gate fails:

1. Agent outputs `[STATE_ERROR: <gate-type>-gate-failed]`
2. Agent lists available skills matching required category
3. Agent remains in current state (no transition)
4. Agent must call required skill category before retry
5. After successful skill call, agent retries transition
