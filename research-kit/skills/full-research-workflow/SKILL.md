---
name: full-research-workflow
description: |
  Orchestrate a complete research workflow from literature review to camera-ready paper.
  Calls `rc` CLI commands to create tasks, dispatches agents for execution, verifies quality gates.
  Follows Trellis philosophy: Task-first, Action-before-asking, Single source of truth.
triggers:
  - "run the full research workflow"
  - "orchestrate research from start to finish"
  - "execute the complete research pipeline"
  - "run all research stages"
---

# Full Research Workflow

Orchestrates a complete research workflow: literature → ideation → experiment → writing → polish → review → rebuttal.

## When to Use

Use this skill when:
- User wants to run the entire research pipeline end-to-end
- User says "run the full workflow", "execute all stages", "orchestrate research"
- A `prd.md` exists with research goals and you need to execute all stages

Do NOT use when:
- User wants to run a single stage (use stage-specific skills instead)
- No `prd.md` exists (guide user to create one first)

## Task-First Principle

If `prd.md` exists and has clear goals, proceed directly to Stage 1. Only ask questions if critical information is missing.

## Auto-Context (Action-First)

**Step 0**: Before asking clarifying questions, read the context files that might contain answers:

```powershell
# Check for PRD and existing state
if (Test-Path prd.md) { Get-Content prd.md } else { "No PRD found" }
rc task list --json 2>$null || "No tasks yet"
if (Test-Path execute.jsonl) { "Execution log exists" } else { "No execution log" }
if ((Test-Path baselines/) -and (Test-Path venue/)) { "Support dirs ready" } else { "No support dirs" }
```

**What to look for**:
- `prd.md`: Research goals, target venue, constraints
- `execute.jsonl`: Previous execution history, failed stages
- Task list: Which stages are already complete/in-progress
- Support dirs (`baselines/`, `venue/`): Whether infrastructure is ready

**Decision tree**:
1. If `prd.md` missing → Ask user to create one or provide research goals
2. If `prd.md` exists but tasks already in progress → Resume from last incomplete stage
3. If `prd.md` exists and no tasks → Start fresh from Stage 1

Only ask clarifying questions if critical information is genuinely missing from these files.

## Workflow Stages

### Stage 1: Literature Review

```powershell
# Create literature review task and capture ID
$output = rc task create `
  --kind literature `
  --title "Literature Review" `
  --goal "Survey state-of-the-art in [research area from prd.md]"
$LIT_TASK_ID = ($output | Select-String 'Task (\d+)').Matches.Groups[1].Value

# Dispatch agent to execute
rc agent dispatch --task-id $LIT_TASK_ID --agent literature-agent

# Verify deliverables exist
if (-not (Test-Path lit_review.md)) { "ERROR: lit_review.md missing" }
if (-not (Test-Path references/)) { "ERROR: references/ missing" }

# Mark complete
rc task complete --task-id $LIT_TASK_ID
```

Quality gate: `lit_review.md` must exist with 15+ references, clear gaps identified.

### Stage 2: Ideation

```powershell
# Verify literature task is complete
$status = rc task status $LIT_TASK_ID
if ($status -notmatch "completed") {
  "ERROR: Literature task not completed yet"
  exit 1
}

# Create ideation task (depends on literature)
$output = rc task create `
  --kind ideation `
  --title "Ideation" `
  --goal "Generate research ideas addressing gaps from literature" `
  --depends-on $LIT_TASK_ID
$IDEA_TASK_ID = ($output | Select-String 'Task (\d+)').Matches.Groups[1].Value

# Dispatch agent
rc agent dispatch --task-id $IDEA_TASK_ID --agent ideation-agent

# Verify deliverables
if (-not (Test-Path ideas.md)) { "ERROR: ideas.md missing" }
if (-not (Select-String -Path ideas.md -Pattern "idea_" -Quiet)) { "ERROR: No structured ideas found" }

# Mark complete
rc task complete --task-id $IDEA_TASK_ID
```

Quality gate: `ideas.md` must contain 3+ structured ideas with novelty scores.

### Stage 3: Experiment

```powershell
# Verify ideation task is complete
$status = rc task status $IDEA_TASK_ID
if ($status -notmatch "completed") {
  "ERROR: Ideation task not completed yet"
  exit 1
}

# Create experiment task (depends on ideation)
$output = rc task create `
  --kind experiment `
  --title "Experiment Execution" `
  --goal "Implement and run experiments for selected idea" `
  --depends-on $IDEA_TASK_ID
$EXP_TASK_ID = ($output | Select-String 'Task (\d+)').Matches.Groups[1].Value

# Dispatch agent
rc agent dispatch --task-id $EXP_TASK_ID --agent experiment-agent

# Verify deliverables
if (-not (Test-Path results.json)) { "ERROR: results.json missing" }
if (-not (Test-Path figures/)) { "ERROR: figures/ missing" }
if (-not (Test-Path experiment_log.md)) { "ERROR: experiment_log.md missing" }

# Mark complete
rc task complete --task-id $EXP_TASK_ID
```

Quality gate: `results.json` must have baseline comparisons, `figures/` must contain plots.

### Stage 4: Writing

```powershell
# Verify experiment task is complete
$status = rc task status $EXP_TASK_ID
if ($status -notmatch "completed") {
  "ERROR: Experiment task not completed yet"
  exit 1
}

# Create writing task (depends on experiment)
$output = rc task create `
  --kind writing `
  --title "Draft Paper" `
  --goal "Write paper draft following venue template" `
  --depends-on $EXP_TASK_ID
$WRITE_TASK_ID = ($output | Select-String 'Task (\d+)').Matches.Groups[1].Value

# Dispatch agent
rc agent dispatch --task-id $WRITE_TASK_ID --agent writing-agent

# Verify deliverables
if (-not (Test-Path paper_draft.tex)) { "ERROR: paper_draft.tex missing" }
pdflatex paper_draft.tex >$null 2>&1
if ($LASTEXITCODE -ne 0) { "WARN: LaTeX compilation failed" }

# Mark complete
rc task complete --task-id $WRITE_TASK_ID
```

Quality gate: `paper_draft.tex` must compile, all sections present, references formatted.

### Stage 5: Polish

```powershell
# Verify writing task is complete
$status = rc task status $WRITE_TASK_ID
if ($status -notmatch "completed") {
  "ERROR: Writing task not completed yet"
  exit 1
}

# Create polish task (depends on writing)
$output = rc task create `
  --kind polish `
  --title "Polish Paper" `
  --goal "Refine writing, check formatting, validate claims" `
  --depends-on $WRITE_TASK_ID
$POLISH_TASK_ID = ($output | Select-String 'Task (\d+)').Matches.Groups[1].Value

# Dispatch agent
rc agent dispatch --task-id $POLISH_TASK_ID --agent polish-agent

# Verify deliverables
if (-not (Test-Path paper_polished.tex)) { "ERROR: paper_polished.tex missing" }
if (-not (Select-String -Path paper_polished.tex -Pattern "\\cite{" -Quiet)) { "WARN: No citations found" }

# Mark complete
rc task complete --task-id $POLISH_TASK_ID
```

Quality gate: Paper length within venue limits, all claims cited, figures captioned.

### Stage 6: Review

```powershell
# Verify polish task is complete
$status = rc task status $POLISH_TASK_ID
if ($status -notmatch "completed") {
  "ERROR: Polish task not completed yet"
  exit 1
}

# Create review task (depends on polish)
$output = rc task create `
  --kind review `
  --title "Internal Review" `
  --goal "Simulate peer review, identify weaknesses" `
  --depends-on $POLISH_TASK_ID
$REVIEW_TASK_ID = ($output | Select-String 'Task (\d+)').Matches.Groups[1].Value

# Dispatch agent
rc agent dispatch --task-id $REVIEW_TASK_ID --agent review-agent

# Verify deliverables
if (-not (Test-Path review_report.md)) { "ERROR: review_report.md missing" }
if (-not (Select-String -Path review_report.md -Pattern "weakness_" -Quiet)) { "ERROR: No structured weaknesses" }

# Mark complete
rc task complete --task-id $REVIEW_TASK_ID
```

Quality gate: `review_report.md` must identify 3+ weaknesses with severity scores.

### Stage 7: Rebuttal (Optional)

```powershell
# Only run if review found critical issues
if (Select-String -Path review_report.md -Pattern "severity: critical" -Quiet) {
  # Verify review task is complete
  $status = rc task status $REVIEW_TASK_ID
  if ($status -notmatch "completed") {
    "ERROR: Review task not completed yet"
    exit 1
  }
  
  $output = rc task create `
    --kind rebuttal `
    --title "Address Review Comments" `
    --goal "Revise paper based on review feedback" `
    --depends-on $REVIEW_TASK_ID
  $REBUTTAL_TASK_ID = ($output | Select-String 'Task (\d+)').Matches.Groups[1].Value
  
  rc agent dispatch --task-id $REBUTTAL_TASK_ID --agent rebuttal-agent
  
  if (-not (Test-Path paper_revised.tex)) { "ERROR: paper_revised.tex missing" }
  if (-not (Test-Path rebuttal_response.md)) { "ERROR: rebuttal_response.md missing" }
  
  rc task complete --task-id $REBUTTAL_TASK_ID
}
```

Quality gate: All critical weaknesses addressed, rebuttal response provided.

## Error Recovery

### Executor Fails

If `rc agent dispatch` fails or agent reports errors:

1. Check `execute.jsonl` for the failure record
2. Read the error message and context
3. Record a gap in the task notes:
   ```powershell
   rc task update --task-id $TASK_ID `
     --add-note "Agent failed: [error]. Manual intervention needed."
   ```
4. Ask user: "The [stage] agent failed with error: [error]. Would you like me to retry with different parameters, or handle this manually?"

### Quality Gate Fails

If deliverables are missing or malformed:

1. Set task status back to `in_progress`:
   ```powershell
   rc task update --task-id $TASK_ID --status in_progress
   ```
2. Re-dispatch agent with explicit instructions:
   ```powershell
   rc agent dispatch --task-id $TASK_ID `
     --agent <agent-name> `
     --instruction "Previous run failed quality gate: [details]. Focus on [missing deliverable]."
   ```
3. If fails twice, ask user for guidance

### MCP Unavailable

If `rc` CLI commands fail because MCP server is not running:

1. Record the gap: "MCP server unavailable, cannot create tasks programmatically"
2. Provide manual fallback:
   ```powershell
   # Manual task creation
   New-Item -ItemType Directory -Force -Path .research/tasks/
   @"
   {
     "kind": "literature",
     "title": "Literature Review",
     "status": "pending"
   }
   "@ | Out-File -FilePath .research/tasks/literature.json -Encoding utf8
   ```
3. Ask user: "The `rc` CLI is unavailable. Should I proceed with manual task tracking?"

## Report Format

After all stages complete (or when blocked), provide a summary:

```
Research Workflow Summary
========================

Completed Stages:
✓ Stage 1: Literature Review (lit_review.md, 18 references)
✓ Stage 2: Ideation (ideas.md, 4 ideas generated)
✓ Stage 3: Experiment (results.json, 3 baselines compared)
✓ Stage 4: Writing (paper_draft.tex, 8 pages)
✓ Stage 5: Polish (paper_polished.tex, formatting validated)
✓ Stage 6: Review (review_report.md, 2 critical weaknesses found)
✗ Stage 7: Rebuttal (skipped - no critical issues OR in progress)

Deliverables:
- Paper: paper_polished.tex (or paper_revised.tex if rebuttal ran)
- Figures: figures/ (N plots)
- References: references/ (M papers)
- Execution log: execute.jsonl (full trace)

Quality Gates Passed:
- Literature: 15+ references ✓
- Ideation: 3+ ideas ✓
- Experiment: Baseline comparisons ✓
- Writing: LaTeX compiles ✓
- Polish: Within page limits ✓
- Review: Weaknesses identified ✓

Next Steps:
- Review paper_polished.tex
- Address any remaining review comments manually
- Prepare submission package
```

If any stage failed, include:

```
Blockers:
- Stage X failed: [error message]
- Manual intervention needed: [specific action]
```
