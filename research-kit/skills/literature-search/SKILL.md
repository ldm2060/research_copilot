---
name: literature-search
description: Focused literature search skill. Searches papers, locks baselines, builds related-work map. Use for standalone literature tasks.
triggers:
  - "search papers"
  - "find baselines"
  - "literature review"
  - "related work"
  - "find research on"
---

# Literature Search

Orchestrate focused literature search: create task → dispatch @rc-literature → verify results.

## When to Use

Use this skill when:
- User asks to "search papers for X"
- User wants to "find baselines for Y"
- User needs a "literature review on Z"
- Standalone literature search (NOT part of full pipeline)

Do NOT use when:
- Part of full-research-workflow (that handles literature internally)
- User only wants a quick web search (use web-search skill)

## Task-First Protocol

Before starting, check if task exists:

```powershell
# Check for existing literature task
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\literature-search.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Found existing task: $($task.query)"
} else {
    Write-Host "No existing task. Will create one."
}
```

Create task if needed:

```powershell
# Create literature search task
rc task create --type literature --query "user query here" --output .rc/tasks/literature-search.json
```

## Auto-Context Loading

Read task context before orchestration:

```powershell
# Load task context
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\literature-search.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    
    Write-Host "Task Query: $($task.query)"
    Write-Host "Target Baselines: $($task.target_baselines)"
    Write-Host "Categories Required: $($task.categories_required)"
    
    # Load PRD if referenced
    if ($task.prd_file -and (Test-Path $task.prd_file)) {
        $prd = Get-Content $task.prd_file -Raw
        Write-Host "PRD loaded: $($task.prd_file)"
    }
}
```

## Orchestration Logic

Execute literature search via agent dispatch:

```powershell
# Start task
rc task start literature-search

# Dispatch to literature agent
Write-Host "Dispatching to @rc-literature agent..."

# Agent will:
# 1. Parse query and extract search terms
# 2. Search multiple sources (arXiv, Semantic Scholar, Google Scholar)
# 3. Extract baselines and build comparison table
# 4. Categorize papers (method, survey, application)
# 5. Generate related-work map
# 6. Save results to .rc/literature/

# Wait for completion (agent runs autonomously)
# Check status
$status = rc task status literature-search
Write-Host "Task status: $status"
```

Verify results:

```powershell
# Verify literature search outputs
$litDir = "C:\PythonProject\research_copilot\.rc\literature"

# Check baselines file
$baselinesFile = Join-Path $litDir "baselines.json"
if (Test-Path $baselinesFile) {
    $baselines = Get-Content $baselinesFile | ConvertFrom-Json
    Write-Host "Found $($baselines.Count) baselines"
} else {
    Write-Host "WARNING: No baselines file found"
}

# Check papers file
$papersFile = Join-Path $litDir "papers.json"
if (Test-Path $papersFile) {
    $papers = Get-Content $papersFile | ConvertFrom-Json
    Write-Host "Found $($papers.Count) papers"
} else {
    Write-Host "WARNING: No papers file found"
}

# Check related-work map
$relatedWorkFile = Join-Path $litDir "related-work.md"
if (Test-Path $relatedWorkFile) {
    Write-Host "Related-work map generated"
} else {
    Write-Host "WARNING: No related-work map found"
}
```

Complete task:

```powershell
# Mark task complete if quality gates passed
rc task complete literature-search
```

## Quality Gates

Verify before marking complete:

```powershell
# Quality gate checks
$passed = $true

# Gate 1: Minimum baselines
$baselinesFile = "C:\PythonProject\research_copilot\.rc\literature\baselines.json"
if (Test-Path $baselinesFile) {
    $baselines = Get-Content $baselinesFile | ConvertFrom-Json
    if ($baselines.Count -lt 3) {
        Write-Host "FAIL: Need ≥3 baselines, found $($baselines.Count)"
        $passed = $false
    }
} else {
    Write-Host "FAIL: No baselines file"
    $passed = $false
}

# Gate 2: Category coverage
$papersFile = "C:\PythonProject\research_copilot\.rc\literature\papers.json"
if (Test-Path $papersFile) {
    $papers = Get-Content $papersFile | ConvertFrom-Json
    $categories = $papers | Select-Object -ExpandProperty category -Unique
    if ($categories.Count -lt 2) {
        Write-Host "FAIL: Need ≥2 categories, found $($categories.Count)"
        $passed = $false
    }
} else {
    Write-Host "FAIL: No papers file"
    $passed = $false
}

# Gate 3: PRD claim support
$prdFile = "C:\PythonProject\research_copilot\.rc\prd.md"
if (Test-Path $prdFile) {
    $prd = Get-Content $prdFile -Raw
    $claims = [regex]::Matches($prd, '\[CLAIM:([^\]]+)\]')
    $supportedClaims = 0
    
    foreach ($claim in $claims) {
        $claimId = $claim.Groups[1].Value
        $citationPattern = "\[$claimId\]"
        if ($prd -match $citationPattern) {
            $supportedClaims++
        }
    }
    
    if ($supportedClaims -lt $claims.Count) {
        Write-Host "FAIL: Only $supportedClaims/$($claims.Count) claims supported"
        $passed = $false
    }
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
# Literature Search Report

**Query**: {user_query}
**Date**: {date}
**Baselines Found**: {baseline_count}
**Papers Reviewed**: {paper_count}

## Baselines

| Method | Year | Metric | Score | Paper |
|--------|------|--------|-------|-------|
| {name} | {year} | {metric} | {score} | [{title}]({url}) |

## Paper Categories

- **Methods**: {count} papers
- **Surveys**: {count} papers
- **Applications**: {count} papers

## Related Work Map

{content from related-work.md}

## Key Findings

- Finding 1
- Finding 2
- Finding 3

## Next Steps

- [ ] Review baselines for integration
- [ ] Extract method details from top papers
- [ ] Update PRD with new citations
```

## Example Usage

```
User: "Search papers on graph neural networks for recommendation"