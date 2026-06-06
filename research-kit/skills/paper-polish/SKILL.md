---
name: paper-polish
description: Polishes paper text and removes AI patterns. Use after writing stage to refine language and ensure venue compliance.
triggers:
  - "polish paper"
  - "de-AI"
  - "remove AI flavor"
  - "refine writing"
  - "clean up text"
---

# Paper Polish

Orchestrate paper polishing: create task → dispatch @rc-polisher → verify changes → complete.

Removes AI-generated patterns, ensures venue style compliance, validates that only wording changed (no data/formulas modified).

## When to Use

Use this skill when:
- User asks to "polish the paper"
- User wants to "remove AI patterns" or "de-AI the text"
- After drafting is complete and paper needs language refinement
- Before final submission to ensure professional writing style

Do NOT use when:
- Paper is still being drafted (use writing skills)
- User wants content changes (use revision skills)
- Only formatting/LaTeX fixes needed (handle directly)

## Task-First Protocol

Before starting, check if polish task exists:

```powershell
# Check for existing polish task
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\paper-polish.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Found existing polish task: $($task.paper_file)"
} else {
    Write-Host "No existing task. Will create one."
}
```

Create task if needed:

```powershell
# Create paper polish task
$paperFile = "paper_draft.tex"  # Or user-specified file
rc task create --type polish --paper $paperFile --output .rc/tasks/paper-polish.json
```

## Auto-Context Loading

Read all context files before orchestration:

```powershell
# Load task context
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\paper-polish.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Paper file: $($task.paper_file)"
    
    # Load PRD for research context
    $prdFile = "C:\PythonProject\research_copilot\.rc\prd.md"
    if (Test-Path $prdFile) {
        $prd = Get-Content $prdFile -Raw
        Write-Host "PRD loaded for context"
    }
    
    # Load venue specification
    $venueFile = "C:\PythonProject\research_copilot\.rc\venue\spec.json"
    if (Test-Path $venueFile) {
        $venue = Get-Content $venueFile | ConvertFrom-Json
        Write-Host "Venue: $($venue.name)"
        Write-Host "Style guide: $($venue.style_guide)"
    } else {
        Write-Host "WARNING: No venue spec found"
    }
    
    # Load writing conventions
    $conventionsFile = "C:\PythonProject\research_copilot\.rc\writing\conventions.md"
    if (Test-Path $conventionsFile) {
        Write-Host "Writing conventions loaded"
    }
}
```

## Orchestration Logic

Execute polishing via agent dispatch:

```powershell
# Start task
rc task start paper-polish

# Create backup before polishing
$paperFile = "paper_draft.tex"
$backupFile = "paper_draft.backup.tex"
Copy-Item $paperFile $backupFile -Force
Write-Host "Backup created: $backupFile"

# Dispatch to polisher agent
Write-Host "Dispatching to @rc-polisher agent..."

# Agent will:
# 1. Scan for AI patterns (excessive adjectives, mechanical transitions)
# 2. Check venue style compliance (citation format, section structure)
# 3. Refine wording while preserving meaning
# 4. Ensure no numbers/formulas are modified
# 5. Generate diff showing only text changes
# 6. Save polished version to paper_polished.tex

# Wait for completion
$status = rc task status paper-polish
Write-Host "Task status: $status"
```

Verify polishing results:

```powershell
# Verify polish outputs
$polishedFile = "paper_polished.tex"

if (-not (Test-Path $polishedFile)) {
    Write-Host "ERROR: Polished file not generated"
    exit 1
}

# Check that file was actually modified
$originalSize = (Get-Item $paperFile).Length
$polishedSize = (Get-Item $polishedFile).Length
if ($originalSize -eq $polishedSize) {
    Write-Host "WARNING: File sizes identical - may be no changes"
}

# Verify polish report exists
$reportFile = "C:\PythonProject\research_copilot\.rc\polish\report.md"
if (Test-Path $reportFile) {
    Write-Host "Polish report generated"
} else {
    Write-Host "WARNING: No polish report found"
}
```

Complete task:

```powershell
# Mark task complete if quality gates passed
rc task complete paper-polish
```

## Quality Gates

Verify before marking complete:

```powershell
# Quality gate checks
$passed = $true

# Gate 1: No AI patterns remain
$polishedFile = "paper_polished.tex"
if (Test-Path $polishedFile) {
    $content = Get-Content $polishedFile -Raw
    
    # Check for AI patterns
    $aiPatterns = @(
        'very\s+important',
        'highly\s+significant',
        'it\s+is\s+worth\s+noting',
        'arguably',
        'In\s+conclusion,\s+we\s+have',
        'Furthermore,\s+we',
        'Moreover,\s+it',
        'bullet\s+list'
    )
    
    $patternsFound = @()
    foreach ($pattern in $aiPatterns) {
        if ($content -match $pattern) {
            $patternsFound += $pattern
        }
    }
    
    if ($patternsFound.Count -gt 0) {
        Write-Host "FAIL: AI patterns found: $($patternsFound -join ', ')"
        $passed = $false
    }
} else {
    Write-Host "FAIL: No polished file"
    $passed = $false
}

# Gate 2: Venue style compliance
$venueFile = "C:\PythonProject\research_copilot\.rc\venue\spec.json"
if (Test-Path $venueFile) {
    $venue = Get-Content $venueFile | ConvertFrom-Json
    
    # Check citation format
    if ($venue.citation_style -eq "numeric") {
        if ($content -notmatch '\\\cite\{[^\}]+\}') {
            Write-Host "FAIL: No numeric citations found"
            $passed = $false
        }
    }
    
    # Check section structure
    $requiredSections = @('Introduction', 'Related Work', 'Method', 'Experiments', 'Conclusion')
    foreach ($section in $requiredSections) {
        if ($content -notmatch "\\section\{$section\}") {
            Write-Host "FAIL: Missing required section: $section"
            $passed = $false
        }
    }
}

# Gate 3: Diff verification (only wording changed)
$diffFile = "C:\PythonProject\research_copilot\.rc\polish\diff.txt"
if (Test-Path $diffFile) {
    $diff = Get-Content $diffFile -Raw
    
    # Check that no numbers were modified
    $numberChanges = [regex]::Matches($diff, '-.*\d+.*\n\+.*\d+')
    if ($numberChanges.Count -gt 0) {
        Write-Host "WARNING: Numbers may have been modified - manual review needed"
    }
    
    # Check that no formulas were modified
    $formulaChanges = [regex]::Matches($diff, '-.*\$.*\$.*\n\+.*\$.*\$')
    if ($formulaChanges.Count -gt 0) {
        Write-Host "WARNING: Formulas may have been modified - manual review needed"
    }
} else {
    Write-Host "WARNING: No diff file found"
}

if ($passed) {
    Write-Host "All quality gates passed"
} else {
    Write-Host "Quality gates failed - review needed"
}
```

## Report Format

Generate final report:

```markdown
# Paper Polish Report

**Paper**: {paper_file}
**Date**: {date}
**AI Patterns Removed**: {pattern_count}
**Changes Made**: {change_count}

## AI Patterns Removed

- Excessive adjectives: {count} instances
- Mechanical transitions: {count} instances  
- Bullet lists in prose: {count} instances
- Hedging phrases: {count} instances

## Venue Style Compliance

✓ Citation format: {venue.citation_style}
✓ Section structure: {venue.required_sections}
✓ Page limit: {current_pages}/{venue.page_limit}

## Diff Verification

✓ Only wording changed
✓ No numbers modified
✓ No formulas modified
✓ No citations removed

## Key Changes

1. Changed "very important" → "critical"
2. Removed "It is worth noting that"
3. Simplified "Furthermore, we observe" → "We observe"

## Files Generated

- `paper_polished.tex`: Polished version
- `paper_draft.backup.tex`: Original backup
- `.rc/polish/diff.txt`: Detailed changes
- `.rc/polish/report.md`: This report

## Next Steps

- [ ] Review polished version
- [ ] Compile LaTeX to verify formatting
- [ ] Run sanity-check before submission
```

## Error Recovery

If polishing fails:

```powershell
# Restore from backup
$backupFile = "paper_draft.backup.tex"
if (Test-Path $backupFile) {
    Copy-Item $backupFile $paperFile -Force
    Write-Host "Restored from backup"
}

# Check agent error log
$errorLog = "C:\PythonProject\research_copilot\.rc\polish\error.log"
if (Test-Path $errorLog) {
    $error = Get-Content $errorLog -Raw
    Write-Host "Agent error: $error"
}
```

## Example Usage

```
User: "Polish the paper and remove AI patterns"