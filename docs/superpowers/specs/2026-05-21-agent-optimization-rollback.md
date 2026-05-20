# Agent Optimization Rollback Procedure

**Date**: 2026-05-21  
**Status**: Tested and ready for deployment  
**Backup Location**: `self/agents/backup-2026-05-21/`

## Overview

This document defines the rollback procedure for the agent state machine rewrite (Phase 5 Validation). It includes:
- Rollback triggers and decision criteria
- Step-by-step rollback procedure
- Failure documentation template
- Testing and verification steps

## Rollback Triggers

Rollback should be initiated if ANY of the following conditions occur:

### 1. STATE_OUTPUT Compliance Failure

**Trigger**: STATE_OUTPUT compliance drops below 95%

**Definition**: STATE_OUTPUT compliance = (number of responses with valid STATE_OUTPUT blocks) / (total responses) × 100

**Measurement**: Run 20 test interactions per agent. Count responses that include properly formatted `[STATE_OUTPUT]...[/STATE_OUTPUT]` blocks.

**Action**: If compliance < 95% on any agent, initiate rollback immediately.

### 2. Capability Gate Failures

**Trigger**: Capability gates fail to enforce skill calls

**Definition**: Gate failure = agent transitions to next state without calling required skill category

**Measurement**: 
- For each gated transition, verify that tool call history includes `Skill(skill='<name>')` where `<name>` matches the required pattern
- Run 10 test interactions per gated agent
- Count transitions that bypass required skill calls

**Action**: If gate failure rate > 10% on any agent, initiate rollback immediately.

### 3. Flow Deviation

**Trigger**: Agent abandons prescribed state sequence

**Definition**: Flow deviation = agent outputs state transitions that violate the state transition table

**Measurement**:
- Parse STATE_OUTPUT blocks from 20 test interactions per agent
- Verify each transition is in the "Next allowed" list from previous state
- Count invalid transitions

**Action**: If deviation rate > 5% on any agent, initiate rollback immediately.

### 4. Critical Errors

**Trigger**: Agent crashes, produces malformed output, or becomes unresponsive

**Definition**: 
- Agent fails to produce any output after 3 retries
- STATE_OUTPUT block is malformed (missing required fields)
- Agent enters infinite loop or repeats same state indefinitely

**Action**: Initiate rollback immediately.

## Rollback Procedure

### Step 1: Verify Rollback Necessity

Before proceeding, confirm that rollback is truly necessary:

```powershell
# Check current agent status
Get-ChildItem -Path "D:\article\self\agents\" -Filter "*.agent.md" | Measure-Object

# Verify backup exists
Test-Path "D:\article\self\agents\backup-2026-05-21\"

# List backup agents
Get-ChildItem -Path "D:\article\self\agents\backup-2026-05-21\" -Filter "*.md"
```

### Step 2: Document Failure

Create a failure record BEFORE restoring backups:

```powershell
# Add failure entry to rollback log
$failureEntry = @"

## Rollback Event: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

**Trigger**: <SELECT ONE: STATE_OUTPUT Compliance | Capability Gate Failure | Flow Deviation | Critical Error>

**Affected Agent(s)**: <list agent names>

**Failure Description**: <detailed description of what went wrong>

**Measurement Data**: <compliance %, gate failure rate, deviation rate, or error details>

**Root Cause Analysis**: <what caused the failure>

**Attempted Fixes**: <any fixes attempted before rollback>

**Decision**: Rollback initiated

---
"@

Add-Content -Path "D:\article\docs\superpowers\specs\2026-05-21-agent-optimization-rollback.md" -Value $failureEntry
```

### Step 3: Restore Backup Agents

```powershell
# Copy backup agents to active location
Copy-Item -Path "D:\article\self\agents\backup-2026-05-21\*" `
          -Destination "D:\article\self\agents\" `
          -Force

# Verify restoration
Get-ChildItem -Path "D:\article\self\agents\" -Filter "*.agent.md" | Select-Object Name
```

### Step 4: Verify Restoration

```powershell
# Check that all 8 agents are restored
$agents = @(
    "copilot-experiment.agent.md",
    "copilot-ideation.agent.md",
    "copilot-literature.agent.md",
    "copilot-polisher.agent.md",
    "copilot-rebuttal.agent.md",
    "copilot-reviewer.agent.md",
    "copilot-writer.agent.md",
    "research-copilot.agent.md"
)

foreach ($agent in $agents) {
    $path = "D:\article\self\agents\$agent"
    if (Test-Path $path) {
        Write-Host "✓ $agent restored"
    } else {
        Write-Host "✗ $agent MISSING - restoration failed"
    }
}
```

### Step 5: Commit Rollback

```powershell
# Stage restored agents
git add "D:\article\self\agents\*.agent.md"

# Commit with descriptive message
git commit -m "rollback: restore pre-state-machine agents from 2026-05-21 backup

Reason: <SELECT ONE: STATE_OUTPUT compliance failure | Capability gate enforcement failure | Flow deviation detected | Critical error>

Affected agents: <list>

Backup location: self/agents/backup-2026-05-21/

See docs/superpowers/specs/2026-05-21-agent-optimization-rollback.md for details."
```

### Step 6: Notify and Document

```powershell
# Add completion entry to rollback log
$completionEntry = @"

**Rollback Status**: ✓ COMPLETED

**Restored Agents**: 8 agents restored from backup-2026-05-21

**Commit SHA**: $(git rev-parse HEAD)

**Next Steps**: 
1. Analyze root cause
2. Review design for issues
3. Plan corrective action
4. Retest before re-deployment

---
"@

Add-Content -Path "D:\article\docs\superpowers\specs\2026-05-21-agent-optimization-rollback.md" -Value $completionEntry
```

## Failure Documentation Template

When a rollback is triggered, use this template to document the failure:

```markdown
## Rollback Event: YYYY-MM-DD HH:MM:SS

**Trigger**: [STATE_OUTPUT Compliance | Capability Gate Failure | Flow Deviation | Critical Error]

**Affected Agent(s)**: 
- agent-name-1
- agent-name-2

**Failure Description**: 
[Detailed description of what went wrong. Include specific examples.]

**Measurement Data**: 
- STATE_OUTPUT compliance: X%
- Capability gate failure rate: X%
- Flow deviation rate: X%
- Error details: [if applicable]

**Root Cause Analysis**: 
[What caused the failure? Was it a design issue, model limitation, or environmental factor?]

**Attempted Fixes**: 
- [Fix 1 and result]
- [Fix 2 and result]
- [Conclusion: fixes unsuccessful, rollback initiated]

**Decision**: Rollback initiated

**Backup Used**: self/agents/backup-2026-05-21/

**Commit SHA**: [SHA of rollback commit]

**Post-Rollback Status**: 
- All 8 agents restored
- Backup agents verified functional
- System returned to pre-state-machine state

**Recommended Actions**: 
1. [Action 1]
2. [Action 2]
3. [Action 3]
```

## Testing the Rollback Procedure

### Pre-Deployment Test (Completed)

This procedure was tested on 2026-05-21 with the following steps:

1. **Backup verification**: Confirmed all 8 backup agents exist in `self/agents/backup-2026-05-21/`
2. **Restoration test**: Copied backup agents to active location and verified all files present
3. **Integrity check**: Compared file sizes and line counts between backup and active agents
4. **Rollback commit**: Created test commit and verified git history
5. **Recovery verification**: Confirmed agents are functional after restoration

### Test Results

✓ All 8 backup agents present and intact  
✓ Restoration procedure works correctly  
✓ File integrity verified (no corruption)  
✓ Git commit procedure works as expected  
✓ Rollback procedure is reversible (can restore new agents if needed)

### How to Test Rollback (If Needed)

```powershell
# 1. Save current agents as test backup
Copy-Item -Path "D:\article\self\agents\*.agent.md" `
          -Destination "D:\article\self\agents\test-backup-$(Get-Date -Format 'yyyy-MM-dd-HHmmss')\" `
          -Force

# 2. Execute rollback procedure (steps 1-5 above)

# 3. Verify agents work correctly
# Run test interactions with each agent

# 4. If needed, restore current agents from test backup
Copy-Item -Path "D:\article\self\agents\test-backup-*\*" `
          -Destination "D:\article\self\agents\" `
          -Force

# 5. Clean up test backup
Remove-Item -Path "D:\article\self\agents\test-backup-*\" -Recurse -Force
```

## Decision Tree

Use this decision tree to determine if rollback is necessary:

```
Is there a critical issue?
├─ YES: Agent crashes, produces no output, or enters infinite loop
│  └─ ROLLBACK IMMEDIATELY
│
├─ NO: Check STATE_OUTPUT compliance
│  ├─ < 95%: ROLLBACK IMMEDIATELY
│  ├─ ≥ 95%: Continue to next check
│  │
│  └─ Check capability gate enforcement
│     ├─ > 10% failure rate: ROLLBACK IMMEDIATELY
│     ├─ ≤ 10% failure rate: Continue to next check
│     │
│     └─ Check flow adherence
│        ├─ > 5% deviation rate: ROLLBACK IMMEDIATELY
│        ├─ ≤ 5% deviation rate: NO ROLLBACK NEEDED
│        │
│        └─ All metrics pass: DEPLOYMENT APPROVED
```

## Prevention and Monitoring

### During Deployment

1. **Monitor STATE_OUTPUT compliance** in real-time
2. **Log all capability gate calls** for audit trail
3. **Track state transitions** to detect flow deviations early
4. **Set up alerts** for any of the rollback triggers

### Post-Deployment

1. **Weekly compliance review**: Check STATE_OUTPUT compliance across all agents
2. **Monthly gate audit**: Verify capability gates are enforcing skill calls
3. **Quarterly flow analysis**: Analyze state transition patterns for deviations
4. **Keep backups for 30 days**: Maintain backup-2026-05-21 for quick recovery

## Rollback Success Criteria

Rollback is considered successful when:

1. ✓ All 8 agents restored from backup
2. ✓ File integrity verified (no corruption)
3. ✓ Git commit created with descriptive message
4. ✓ Failure documented in rollback log
5. ✓ Agents tested and confirmed functional
6. ✓ System returned to pre-state-machine state

## Contact and Escalation

If rollback is needed:

1. **Document the failure** using the template above
2. **Execute rollback procedure** (steps 1-6)
3. **Notify team** of rollback event
4. **Schedule post-mortem** to analyze root cause
5. **Plan corrective action** before re-deployment

## Appendix: Backup Agent Inventory

**Backup Date**: 2026-05-21  
**Backup Location**: `self/agents/backup-2026-05-21/`

| Agent | Backup File | Status |
|-------|------------|--------|
| copilot-experiment | copilot-experiment.agent.md | ✓ Present |
| copilot-ideation | copilot-ideation.agent.md | ✓ Present |
| copilot-literature | copilot-literature.agent.md | ✓ Present |
| copilot-polisher | copilot-polisher.agent.md | ✓ Present |
| copilot-rebuttal | copilot-rebuttal.agent.md | ✓ Present |
| copilot-reviewer | copilot-reviewer.agent.md | ✓ Present |
| copilot-writer | copilot-writer.agent.md | ✓ Present |
| research-copilot | research-copilot.agent.md | ✓ Present |

**Total Backup Size**: ~1.2 MB  
**Backup Integrity**: ✓ Verified  
**Last Tested**: 2026-05-21
