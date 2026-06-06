---
name: sanity-check
description: Final 6-dimension sanity check (logic/citation/reproducibility/novelty/venue/de-AI). Use before submission for comprehensive audit.
triggers:
  - "sanity check"
  - "final check"
  - "audit paper"
  - "pre-submission audit"
  - "verify paper ready"
---

# Sanity Check

Final 6-dimension audit without making changes. Verifies paper is submission-ready across all critical dimensions.

## When to Use

Use this skill when:
- User asks to "sanity check the paper"
- Paper is ready for final audit before submission
- After submission sprint completes
- User wants to "verify paper is ready"

Do NOT use when:
- Paper needs changes (use submission-sprint or review skills)
- User wants specific issue fixed (handle directly)
- Paper is still being drafted (too early)

## Task-First Protocol

Before starting, check if sanity-check task exists:

```powershell
# Check for existing sanity-check task
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\sanity-check.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Found existing sanity-check task for: $($task.paper_file)"
} else {
    Write-Host "No existing task. Will create one."
}
```

Create task if needed:

```powershell
# Create sanity-check task
$paperFile = "paper_polished.tex"  # Or user-specified file
rc task create --type sanity-check --paper $paperFile --output .rc/tasks/sanity-check.json
```

## Auto-Context Loading

Read all context files before audit:

```powershell
# Load task context
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\sanity-check.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Paper file: $($task.paper_file)"
    
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
    
    # Load novelty spec
    $noveltyFile = "C:\PythonProject\research_copilot\.rc\spec\novelty.md"
    if (Test-Path $noveltyFile) {
        Write-Host "Novelty spec loaded"
    }
    
    # Load writing conventions
    $conventionsFile = "C:\PythonProject\research_copilot\.rc\writing\conventions.md"
    if (Test-Path $conventionsFile) {
        Write-Host "Writing conventions loaded"
    }
}
```

## Orchestration Logic

Execute 6-dimension audit via @rc-reviewer agent:

```powershell
# Start task
rc task start sanity-check

Write-Host "Starting 6-dimension sanity check..."

# Dispatch to reviewer agent with comprehensive 6-dimension prompt
Write-Host "Dispatching to @rc-reviewer agent..."

# Agent audits 6 dimensions (no changes made):
# 1. Logic: Claims → Evidence chain complete
# 2. Citations: All baselines cited, no orphan references
# 3. Reproducibility: Config/seed/data documented
# 4. Novelty: Claims match spec/novelty/
# 5. Venue compliance: Format/length/template correct
# 6. De-AI: No AI patterns remain

# Wait for completion
$status = rc task status sanity-check
Write-Host "Task status: $status"
```

## 6 Dimensions

### Dimension 1: Logic Integrity

Check claims → evidence chain:

```powershell
# Verify logic dimension
$logicFile = "C:\PythonProject\research_copilot\.rc\sanity\logic.json"
if (Test-Path $logicFile) {
    $logic = Get-Content $logicFile | ConvertFrom-Json
    
    Write-Host "`nDimension 1: Logic"
    Write-Host "Claims checked: $($logic.claims_checked)"
    Write-Host "Evidence gaps: $($logic.evidence_gaps.Count)"
    
    if ($logic.evidence_gaps.Count -eq 0) {
        Write-Host "✓ All claims have supporting evidence"
    } else {
        Write-Host "✗ Evidence gaps found:"
        foreach ($gap in $logic.evidence_gaps) {
            Write-Host "  - $($gap.claim) ($($gap.location))"
        }
    }
}
```

### Dimension 2: Citation Completeness

Check all baselines cited and no orphan references:

```powershell
# Verify citations dimension
$citationsFile = "C:\PythonProject\research_copilot\.rc\sanity\citations.json"
if (Test-Path $citationsFile) {
    $citations = Get-Content $citationsFile | ConvertFrom-Json
    
    Write-Host "`nDimension 2: Citations"
    Write-Host "Total citations: $($citations.total_citations)"
    Write-Host "Orphan references: $($citations.orphan_refs.Count)"
    Write-Host "Missing baseline citations: $($citations.missing_baselines.Count)"
    
    if ($citations.orphan_refs.Count -eq 0 -and $citations.missing_baselines.Count -eq 0) {
        Write-Host "✓ All citations complete and referenced"
    } else {
        if ($citations.orphan_refs.Count -gt 0) {
            Write-Host "✗ Orphan references (in .bib but not cited):"
            foreach ($ref in $citations.orphan_refs) {
                Write-Host "  - $ref"
            }
        }
        if ($citations.missing_baselines.Count -gt 0) {
            Write-Host "✗ Missing baseline citations:"
            foreach ($baseline in $citations.missing_baselines) {
                Write-Host "  - $baseline"
            }
        }
    }
}
```

### Dimension 3: Reproducibility

Check config/seed/data documented:

```powershell
# Verify reproducibility dimension
$reproducibilityFile = "C:\PythonProject\research_copilot\.rc\sanity\reproducibility.json"
if (Test-Path $reproducibilityFile) {
    $repro = Get-Content $reproducibilityFile | ConvertFrom-Json
    
    Write-Host "`nDimension 3: Reproducibility"
    Write-Host "Config documented: $($repro.config_documented)"
    Write-Host "Seeds documented: $($repro.seeds_documented)"
    Write-Host "Data documented: $($repro.data_documented)"
    Write-Host "Code available: $($repro.code_available)"
    
    if ($repro.config_documented -and $repro.seeds_documented -and $repro.data_documented) {
        Write-Host "✓ Reproducibility requirements met"
    } else {
        Write-Host "✗ Missing reproducibility elements:"
        if (-not $repro.config_documented) { Write-Host "  - Configuration details" }
        if (-not $repro.seeds_documented) { Write-Host "  - Random seeds" }
        if (-not $repro.data_documented) { Write-Host "  - Dataset details" }
    }
}
```

### Dimension 4: Novelty Alignment

Check claims match spec/novelty/:

```powershell
# Verify novelty dimension
$noveltyFile = "C:\PythonProject\research_copilot\.rc\sanity\novelty.json"
if (Test-Path $noveltyFile) {
    $novelty = Get-Content $noveltyFile | ConvertFrom-Json
    
    Write-Host "`nDimension 4: Novelty"
    Write-Host "Novelty claims: $($novelty.claims.Count)"
    Write-Host "Aligned with spec: $($novelty.aligned_with_spec)"
    Write-Host "Misalignments: $($novelty.misalignments.Count)"
    
    if ($novelty.aligned_with_spec) {
        Write-Host "✓ Novelty claims match specification"
    } else {
        Write-Host "✗ Novelty misalignments:"
        foreach ($misalignment in $novelty.misalignments) {
            Write-Host "  - $($misalignment.claim)"
            Write-Host "    Expected: $($misalignment.expected)"
            Write-Host "    Found: $($misalignment.found)"
        }
    }
}
```

### Dimension 5: Venue Compliance

Check format/length/template correct:

```powershell
# Verify venue compliance dimension
$venueFile = "C:\PythonProject\research_copilot\.rc\sanity\venue.json"
if (Test-Path $venueFile) {
    $venueCheck = Get-Content $venueFile | ConvertFrom-Json
    
    Write-Host "`nDimension 5: Venue Compliance"
    Write-Host "Template correct: $($venueCheck.template_correct)"
    Write-Host "Page count: $($venueCheck.page_count)/$($venueCheck.page_limit)"
    Write-Host "Format issues: $($venueCheck.format_issues.Count)"
    
    if ($venueCheck.template_correct -and $venueCheck.page_count -le $venueCheck.page_limit -and $venueCheck.format_issues.Count -eq 0) {
        Write-Host "✓ Venue requirements met"
    } else {
        Write-Host "✗ Venue compliance issues:"
        if (-not $venueCheck.template_correct) { Write-Host "  - Incorrect template" }
        if ($venueCheck.page_count -gt $venueCheck.page_limit) { Write-Host "  - Exceeds page limit" }
        foreach ($issue in $venueCheck.format_issues) {
            Write-Host "  - $issue"
        }
    }
}
```

### Dimension 6: De-AI Verification

Check no AI patterns remain:

```powershell
# Verify de-AI dimension
$deAiFile = "C:\PythonProject\research_copilot\.rc\sanity\de-ai.json"
if (Test-Path $deAiFile) {
    $deAi = Get-Content $deAiFile | ConvertFrom-Json
    
    Write-Host "`nDimension 6: De-AI"
    Write-Host "AI patterns found: $($deAi.patterns_found.Count)"
    Write-Host "Mechanical transitions: $($deAi.mechanical_transitions)"
    Write-Host "Excessive adjectives: $($deAi.excessive_adjectives)"
    
    if ($deAi.patterns_found.Count -eq 0) {
        Write-Host "✓ No AI patterns detected"
    } else {
        Write-Host "✗ AI patterns found:"
        foreach ($pattern in $deAi.patterns_found) {
            Write-Host "  - $($pattern.type): '$($pattern.text)' ($($pattern.location))"
        }
    }
}
```

## Quality Gates

All 6 dimensions must pass:

```powershell
# Quality gate checks
$passed = $true
$dimensions = @()

# Check each dimension
$dimensionFiles = @{
    "Logic" = "C:\PythonProject\research_copilot\.rc\sanity\logic.json"
    "Citations" = "C:\PythonProject\research_copilot\.rc\sanity\citations.json"
    "Reproducibility" = "C:\PythonProject\research_copilot\.rc\sanity\reproducibility.json"
    "Novelty" = "C:\PythonProject\research_copilot\.rc\sanity\novelty.json"
    "Venue" = "C:\PythonProject\research_copilot\.rc\sanity\venue.json"
    "De-AI" = "C:\PythonProject\research_copilot\.rc\sanity\de-ai.json"
}

foreach ($dimension in $dimensionFiles.Keys) {
    $file = $dimensionFiles[$dimension]
    
    if (-not (Test-Path $file)) {
        Write-Host "FAIL: $dimension check not completed"
        $passed = $false
        $dimensions += @{ name = $dimension; status = "INCOMPLETE" }
        continue
    }
    
    $data = Get-Content $file | ConvertFrom-Json
    
    # Dimension-specific pass criteria
    $dimPassed = $false
    switch ($dimension) {
        "Logic" { $dimPassed = $data.evidence_gaps.Count -eq 0 }
        "Citations" { $dimPassed = $data.orphan_refs.Count -eq 0 -and $data.missing_baselines.Count -eq 0 }
        "Reproducibility" { $dimPassed = $data.config_documented -and $data.seeds_documented -and $data.data_documented }
        "Novelty" { $dimPassed = $data.aligned_with_spec }
        "Venue" { $dimPassed = $data.template_correct -and $data.page_count -le $data.page_limit -and $data.format_issues.Count -eq 0 }
        "De-AI" { $dimPassed = $data.patterns_found.Count -eq 0 }
    }
    
    if ($dimPassed) {
        $dimensions += @{ name = $dimension; status = "PASS" }
    } else {
        $dimensions += @{ name = $dimension; status = "FAIL" }
        $passed = $false
    }
}

# Overall status
Write-Host "`n=== SANITY CHECK RESULTS ==="
foreach ($dim in $dimensions) {
    $icon = if ($dim.status -eq "PASS") { "✓" } else { "✗" }
    Write-Host "$icon $($dim.name): $($dim.status)"
}

if ($passed) {
    Write-Host "`n✓ PAPER READY FOR SUBMISSION"
    rc task complete sanity-check
} else {
    Write-Host "`n✗ PAPER NOT READY - Issues must be resolved"
    Write-Host "Run submission-sprint to fix remaining issues"
}
```

## Report Format

Generate final report:

```markdown
# Sanity Check Report

**Paper**: {paper_file}
**Date**: {date}
**Status**: {READY / NOT_READY}

## 6-Dimension Audit

### ✓ 1. Logic Integrity
- Claims checked: {count}
- Evidence gaps: 0
- **Status**: PASS

### ✓ 2. Citation Completeness
- Total citations: {count}
- Orphan references: 0
- Missing baselines: 0
- **Status**: PASS

### ✓ 3. Reproducibility
- Configuration documented: Yes
- Seeds documented: Yes
- Data documented: Yes
- Code availability: Yes
- **Status**: PASS

### ✓ 4. Novelty Alignment
- Novelty claims: {count}
- Aligned with spec: Yes
- Misalignments: 0
- **Status**: PASS

### ✓ 5. Venue Compliance
- Template: Correct
- Page count: {count}/{limit}
- Format issues: 0
- **Status**: PASS

### ✓ 6. De-AI Verification
- AI patterns: 0
- Mechanical transitions: 0
- Excessive adjectives: 0
- **Status**: PASS

## Overall Assessment

✓ **READY FOR SUBMISSION**

All 6 dimensions passed. Paper meets submission requirements.

## Files Audited

- `paper_polished.tex`: Main paper file
- `references.bib`: Bibliography
- `figures/`: All figures
- `.rc/prd.md`: Research requirements
- `.rc/spec/novelty.md`: Novelty specification
- `.rc/venue/spec.json`: Venue requirements

## Next Steps

- [ ] Generate submission package
- [ ] Upload to venue submission system
- [ ] Prepare supplementary materials (if required)
```

## Error Recovery

If any dimension fails:

```powershell
# Show failed dimensions
Write-Host "Failed dimensions:"
foreach ($dim in $dimensions) {
    if ($dim.status -eq "FAIL") {
        Write-Host "- $($dim.name)"
        
        # Show details
        $file = $dimensionFiles[$dim.name]
        $data = Get-Content $file | ConvertFrom-Json
        
        # Print specific issues (dimension-dependent)
    }
}

Write-Host "`nRecommendation: Run submission-sprint to fix issues"
```

## Example Usage

```
User: "Sanity check the paper before submission"