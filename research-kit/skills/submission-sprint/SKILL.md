---
name: submission-sprint
description: Pre-submission optimization loop (review → fix → review). Use before final submission to close all P0 gaps.
triggers:
  - "submission sprint"
  - "pre-submit check"
  - "final optimization"
  - "close all gaps"
  - "prepare for submission"
---

# Submission Sprint

Iterative review-fix loop until all P0 (priority 0) gaps are closed. Runs multiple optimization cycles before final submission.

## When to Use

Use this skill when:
- User asks to "run submission sprint"
- Paper is ready for final pre-submission optimization
- User wants to "close all gaps before submission"
- Paper polishing is complete and needs final quality check

Do NOT use when:
- Paper is still being drafted (too early)
- User wants a single review pass (use review skills)
- Only specific issues need fixing (handle directly)

## Task-First Protocol

Before starting, check if sprint task exists:

```powershell
# Check for existing sprint task
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\submission-sprint.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Found existing sprint task: iteration $($task.current_iteration)"
} else {
    Write-Host "No existing task. Will create one."
}
```

Create task if needed:

```powershell
# Create submission sprint task
$paperFile = "paper_polished.tex"  # Or user-specified file
rc task create --type sprint --paper $paperFile --max-iterations 5 --output .rc/tasks/submission-sprint.json
```

## Auto-Context Loading

Read all context files before starting loop:

```powershell
# Load task context
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\submission-sprint.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Paper file: $($task.paper_file)"
    Write-Host "Max iterations: $($task.max_iterations)"
    
    # Load PRD for research requirements
    $prdFile = "C:\PythonProject\research_copilot\.rc\prd.md"
    if (Test-Path $prdFile) {
        $prd = Get-Content $prdFile -Raw
        Write-Host "PRD loaded"
    }
    
    # Load venue specification
    $venueFile = "C:\PythonProject\research_copilot\.rc\venue\spec.json"
    if (Test-Path $venueFile) {
        $venue = Get-Content $venueFile | ConvertFrom-Json
        Write-Host "Venue: $($venue.name)"
    }
    
    # Load previous review if exists
    $reviewFile = "C:\PythonProject\research_copilot\.rc\sprint\review_latest.json"
    if (Test-Path $reviewFile) {
        $review = Get-Content $reviewFile | ConvertFrom-Json
        Write-Host "Previous review found: $($review.p0_count) P0 gaps"
    }
}
```

## Loop Logic

Iterative review-fix cycle:

```powershell
# Initialize loop
$iteration = 1
$maxIterations = 5
$p0Count = 999  # Start with high number

Write-Host "Starting Submission Sprint..."

while ($p0Count -gt 0 -and $iteration -le $maxIterations) {
    Write-Host "`n=== Iteration $iteration/$maxIterations ==="
    
    # Step 1: Review paper
    Write-Host "Step 1: Reviewing paper..."
    rc task start sprint-review-$iteration
    
    # Dispatch to reviewer agent with comprehensive prompt
    Write-Host "Dispatching to @rc-reviewer agent..."
    
    # Agent reviews for:
    # - P0 (blocking): Missing citations, logic gaps, incorrect claims
    # - P1 (important): Clarity issues, weak motivation, missing details
    # - P2 (nice-to-have): Style improvements, minor wording
    
    # Wait for review completion
    $status = rc task status sprint-review-$iteration
    Write-Host "Review status: $status"
    
    # Load review results
    $reviewFile = "C:\PythonProject\research_copilot\.rc\sprint\review_$iteration.json"
    if (-not (Test-Path $reviewFile)) {
        Write-Host "ERROR: Review file not generated"
        break
    }
    
    $review = Get-Content $reviewFile | ConvertFrom-Json
    $p0Count = ($review.gaps | Where-Object { $_.priority -eq "P0" }).Count
    $p1Count = ($review.gaps | Where-Object { $_.priority -eq "P1" }).Count
    
    Write-Host "Gaps found: $p0Count P0, $p1Count P1"
    
    # Mark review task complete
    rc task complete sprint-review-$iteration
    
    # Step 2: Check termination condition
    if ($p0Count -eq 0) {
        Write-Host "✓ All P0 gaps closed!"
        
        if ($p1Count -le 2) {
            Write-Host "✓ P1 gaps acceptable (≤2)"
            Write-Host "Submission sprint complete!"
            break
        } else {
            Write-Host "WARNING: $p1Count P1 gaps remain (target: ≤2)"
            Write-Host "Consider one more iteration for P1 gaps"
        }
        break
    }
    
    # Step 3: Create fix tasks for P0 gaps
    Write-Host "Step 2: Creating fix tasks for P0 gaps..."
    
    $p0Gaps = $review.gaps | Where-Object { $_.priority -eq "P0" }
    $fixTasks = @()
    
    foreach ($gap in $p0Gaps) {
        $fixTaskId = "sprint-fix-$iteration-$($gap.id)"
        
        rc task create `
            --type fix `
            --title "Fix P0 gap: $($gap.title)" `
            --description "$($gap.description)" `
            --location "$($gap.location)" `
            --output ".rc/tasks/$fixTaskId.json"
        
        $fixTasks += $fixTaskId
        Write-Host "Created fix task: $fixTaskId"
    }
    
    # Step 4: Execute all fix tasks
    Write-Host "Step 3: Executing fix tasks..."
    
    foreach ($fixTaskId in $fixTasks) {
        Write-Host "Fixing: $fixTaskId"
        rc task start $fixTaskId
        
        # Dispatch to fixer agent
        # Agent reads gap context and applies targeted fix
        
        rc task complete $fixTaskId
    }
    
    Write-Host "✓ All P0 fixes applied"
    
    # Step 5: Increment iteration
    $iteration++
    
    # Save iteration state
    $stateFile = "C:\PythonProject\research_copilot\.rc\sprint\state.json"
    @{
        current_iteration = $iteration
        p0_count = $p0Count
        p1_count = $p1Count
    } | ConvertTo-Json | Out-File -FilePath $stateFile -Encoding utf8
}

# Final status
if ($p0Count -eq 0) {
    Write-Host "`n✓ Submission sprint SUCCESS"
    Write-Host "Paper ready for final sanity check"
} else {
    Write-Host "`nWARNING: Sprint ended with $p0Count P0 gaps remaining"
    Write-Host "Max iterations ($maxIterations) reached"
}
```

## Termination Condition

Loop exits when:

1. **Success**: `P0_COUNT = 0` AND `P1_COUNT ≤ 2`
2. **Max iterations**: Reached `max_iterations` (default: 5)
3. **Error**: Review or fix task fails

## Quality Gates

Before marking sprint complete:

```powershell
# Quality gate checks
$passed = $true

# Gate 1: Zero P0 gaps
$reviewFile = "C:\PythonProject\research_copilot\.rc\sprint\review_latest.json"
if (Test-Path $reviewFile) {
    $review = Get-Content $reviewFile | ConvertFrom-Json
    $p0Count = ($review.gaps | Where-Object { $_.priority -eq "P0" }).Count
    
    if ($p0Count -gt 0) {
        Write-Host "FAIL: $p0Count P0 gaps remain"
        $passed = $false
    }
} else {
    Write-Host "FAIL: No review file found"
    $passed = $false
}

# Gate 2: P1 gaps acceptable
if (Test-Path $reviewFile) {
    $p1Count = ($review.gaps | Where-Object { $_.priority -eq "P1" }).Count
    
    if ($p1Count -gt 2) {
        Write-Host "WARNING: $p1Count P1 gaps remain (target: ≤2)"
    }
}

# Gate 3: Paper still compiles
$paperFile = "paper_polished.tex"
if (Test-Path $paperFile) {
    $compileResult = pdflatex -interaction=nonstopmode $paperFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: LaTeX compilation failed after fixes"
        $passed = $false
    }
}

if ($passed) {
    Write-Host "All quality gates passed"
    rc task complete submission-sprint
} else {
    Write-Host "Quality gates failed - manual review needed"
}
```

## Report Format

Generate final report after sprint completes:

```markdown
# Submission Sprint Report

**Paper**: {paper_file}
**Date**: {date}
**Iterations**: {iteration_count}
**Final Status**: {READY / NEEDS_WORK}

## Iteration Summary

| Iteration | P0 Gaps | P1 Gaps | Fixes Applied |
|-----------|---------|---------|---------------|
| 1         | 8       | 12      | 8             |
| 2         | 3       | 10      | 3             |
| 3         | 0       | 5       | 0             |

## P0 Gaps Closed

1. **Missing citation for Baseline-X** (§3.2)
   - Fixed: Added \cite{baseline-x-2023}

2. **Logic gap in novelty claim** (§1)
   - Fixed: Added explicit comparison to prior work

3. **Inconsistent metric definition** (§4.1)
   - Fixed: Aligned formula with implementation

[... all P0 gaps listed ...]

## Remaining P1 Gaps

1. **Weak motivation in §1** (line 45-48)
   - Suggestion: Strengthen with real-world application

2. **Missing ablation detail** (§4.3)
   - Suggestion: Add table showing component contributions

## Quality Gate Results

✓ P0 gaps: 0 (target: 0)
⚠ P1 gaps: 2 (target: ≤2)
✓ LaTeX compiles: Yes
✓ Page limit: 9/10 pages
✓ All figures referenced

## Files Generated

- `.rc/sprint/review_1.json`: First review results
- `.rc/sprint/review_2.json`: Second review results
- `.rc/sprint/review_3.json`: Final review results
- `.rc/sprint/state.json`: Sprint state tracking
- `.rc/sprint/report.md`: This report

## Next Steps

- [ ] Run sanity-check skill for final audit
- [ ] Generate submission package
- [ ] Upload to venue submission system
```

## Error Recovery

If sprint fails or gets stuck:

```powershell
# Check sprint state
$stateFile = "C:\PythonProject\research_copilot\.rc\sprint\state.json"
if (Test-Path $stateFile) {
    $state = Get-Content $stateFile | ConvertFrom-Json
    Write-Host "Sprint stuck at iteration $($state.current_iteration)"
    Write-Host "P0 gaps: $($state.p0_count)"
}

# Review latest gaps manually
$reviewFile = "C:\PythonProject\research_copilot\.rc\sprint\review_latest.json"
if (Test-Path $reviewFile) {
    $review = Get-Content $reviewFile | ConvertFrom-Json
    $p0Gaps = $review.gaps | Where-Object { $_.priority -eq "P0" }
    
    Write-Host "`nRemaining P0 gaps:"
    foreach ($gap in $p0Gaps) {
        Write-Host "- $($gap.title) ($($gap.location))"
        Write-Host "  $($gap.description)"
    }
}

# Reset sprint if needed
Write-Host "`nTo reset sprint: Remove-Item .rc/sprint/* -Force"
```

## Example Usage

```
User: "Run submission sprint to close all gaps"