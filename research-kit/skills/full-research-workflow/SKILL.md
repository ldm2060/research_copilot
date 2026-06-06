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

```bash
# Check for PRD and existing state
cat prd.md 2>/dev/null || echo "No PRD found"
rc task list --json 2>/dev/null || echo "No tasks yet"
ls -la execute.jsonl 2>/dev/null || echo "No execution log"
ls -d baselines/ venue/ 2>/dev/null || echo "No support dirs"
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

```bash
# Create literature review task
rc task create \
  --kind literature \
  --title "Literature Review" \
  --goal "Survey state-of-the-art in [research area from prd.md]"

# Dispatch agent to execute
rc agent dispatch --task-id <task-id> --agent literature-agent

# Verify deliverables exist
test -f lit_review.md || echo "ERROR: lit_review.md missing"
test -d references/ || echo "ERROR: references/ missing"

# Mark complete
rc task complete --task-id <task-id>
```

Quality gate: `lit_review.md` must exist with 15+ references, clear gaps identified.

### Stage 2: Ideation

```bash
# Create ideation task (depends on literature)
rc task create \
  --kind ideation \
  --title "Ideation" \
  --goal "Generate research ideas addressing gaps from literature" \
  --depends-on <literature-task-id>

# Dispatch agent
rc agent dispatch --task-id <task-id> --agent ideation-agent

# Verify deliverables
test -f ideas.md || echo "ERROR: ideas.md missing"
grep -q "idea_" ideas.md || echo "ERROR: No structured ideas found"

# Mark complete
rc task complete --task-id <task-id>
```

Quality gate: `ideas.md` must contain 3+ structured ideas with novelty scores.

### Stage 3: Experiment

```bash
# Create experiment task (depends on ideation)
rc task create \
  --kind experiment \
  --title "Experiment Execution" \
  --goal "Implement and run experiments for selected idea" \
  --depends-on <ideation-task-id>

# Dispatch agent
rc agent dispatch --task-id <task-id> --agent experiment-agent

# Verify deliverables
test -f results.json || echo "ERROR: results.json missing"
test -d figures/ || echo "ERROR: figures/ missing"
test -f experiment_log.md || echo "ERROR: experiment_log.md missing"

# Mark complete
rc task complete --task-id <task-id>
```

Quality gate: `results.json` must have baseline comparisons, `figures/` must contain plots.

### Stage 4: Writing

```bash
# Create writing task (depends on experiment)
rc task create \
  --kind writing \
  --title "Draft Paper" \
  --goal "Write paper draft following venue template" \
  --depends-on <experiment-task-id>

# Dispatch agent
rc agent dispatch --task-id <task-id> --agent writing-agent

# Verify deliverables
test -f paper_draft.tex || echo "ERROR: paper_draft.tex missing"
pdflatex paper_draft.tex >/dev/null 2>&1 || echo "WARN: LaTeX compilation failed"

# Mark complete
rc task complete --task-id <task-id>
```

Quality gate: `paper_draft.tex` must compile, all sections present, references formatted.

### Stage 5: Polish

```bash
# Create polish task (depends on writing)
rc task create \
  --kind polish \
  --title "Polish Paper" \
  --goal "Refine writing, check formatting, validate claims" \
  --depends-on <writing-task-id>

# Dispatch agent
rc agent dispatch --task-id <task-id> --agent polish-agent

# Verify deliverables
test -f paper_polished.tex || echo "ERROR: paper_polished.tex missing"
grep -q "\\cite{" paper_polished.tex || echo "WARN: No citations found"

# Mark complete
rc task complete --task-id <task-id>
```

Quality gate: Paper length within venue limits, all claims cited, figures captioned.

### Stage 6: Review

```bash
# Create review task (depends on polish)
rc task create \
  --kind review \
  --title "Internal Review" \
  --goal "Simulate peer review, identify weaknesses" \
  --depends-on <polish-task-id>

# Dispatch agent
rc agent dispatch --task-id <task-id> --agent review-agent

# Verify deliverables
test -f review_report.md || echo "ERROR: review_report.md missing"
grep -q "weakness_" review_report.md || echo "ERROR: No structured weaknesses"

# Mark complete
rc task complete --task-id <task-id>
```

Quality gate: `review_report.md` must identify 3+ weaknesses with severity scores.

### Stage 7: Rebuttal (Optional)

```bash
# Only run if review found critical issues
if grep -q "severity: critical" review_report.md; then
  rc task create \
    --kind rebuttal \
    --title "Address Review Comments" \
    --goal "Revise paper based on review feedback" \
    --depends-on <review-task-id>
  
  rc agent dispatch --task-id <task-id> --agent rebuttal-agent
  
  test -f paper_revised.tex || echo "ERROR: paper_revised.tex missing"
  test -f rebuttal_response.md || echo "ERROR: rebuttal_response.md missing"
  
  rc task complete --task-id <task-id>
fi
```

Quality gate: All critical weaknesses addressed, rebuttal response provided.

## Error Recovery

### Executor Fails

If `rc agent dispatch` fails or agent reports errors:

1. Check `execute.jsonl` for the failure record
2. Read the error message and context
3. Record a gap in the task notes:
   ```bash
   rc task update --task-id <task-id> \
     --add-note "Agent failed: [error]. Manual intervention needed."
   ```
4. Ask user: "The [stage] agent failed with error: [error]. Would you like me to retry with different parameters, or handle this manually?"

### Quality Gate Fails

If deliverables are missing or malformed:

1. Set task status back to `in_progress`:
   ```bash
   rc task update --task-id <task-id> --status in_progress
   ```
2. Re-dispatch agent with explicit instructions:
   ```bash
   rc agent dispatch --task-id <task-id> \
     --agent <agent-name> \
     --instruction "Previous run failed quality gate: [details]. Focus on [missing deliverable]."
   ```
3. If fails twice, ask user for guidance

### MCP Unavailable

If `rc` CLI commands fail because MCP server is not running:

1. Record the gap: "MCP server unavailable, cannot create tasks programmatically"
2. Provide manual fallback:
   ```bash
   # Manual task creation
   mkdir -p .research/tasks/
   cat > .research/tasks/literature.json <<EOF
   {
     "kind": "literature",
     "title": "Literature Review",
     "status": "pending"
   }
   EOF
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
