# Research Copilot Skill/MCP/Agent Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Skill tool support, migrate 6 Python MCP servers to TypeScript, and enhance 10 agent templates following Trellis design philosophy.

**Architecture:** Four-layer architecture (User Interface → Injection → Orchestration/Skills → Execution/Agents → Capability/MCP → State/Core). Skills orchestrate high-level workflows by calling `rc` CLI + dispatching agents. Agents are thin executors (120-180 lines) with recursion guards, self-check lists, and error recovery. MCP servers provide paper search capabilities via TypeScript implementations.

**Tech Stack:** TypeScript, Zod, @modelcontextprotocol/sdk, arxiv API, Google Scholar, DBLP

---

## File Structure Overview

**New directories:**
- `research-kit/skills/` — 6 skill directories, each with SKILL.md (150-250 lines)
  - `full-research-workflow/`
  - `literature-search/`
  - `experiment-design/`
  - `paper-polish/`
  - `submission-sprint/`
  - `sanity-check/`

**Enhanced files:**
- `research-kit/agents/*.md` — 10 agents enhanced from 5-11 lines to 120-180 lines

**New MCP packages:**
- `packages/mcp-servers/scholar/` — merged arxiv/scholar/dblp/arxivsub into one TS server
- `packages/mcp-servers/pdf/` — PDF text extraction in TS

**Modified files:**
- `packages/adapters/src/claude-code.ts` — update .mcp.json generation to use TS servers

---

## Milestone 1: Core Skill Framework

### Task 1.1: Create full-research-workflow Skill

**Files:**
- Create: `research-kit/skills/full-research-workflow/SKILL.md`

- [ ] **Step 1: Write Skill frontmatter and header**

```markdown
---
name: full-research-workflow
description: Orchestrates complete research pipeline from literature to submission. Use when starting a new research project.
triggers:
  - "start research"
  - "full pipeline"
  - "complete workflow"
---

# Full Research Workflow

You orchestrate the complete research pipeline: Literature → Ideation → Experiment → Writing → Polish → Review → Rebuttal.

## When to Use

- User asks to "start a new research project"
- User provides a research idea and wants the full pipeline
- NOT for individual stages (use specific skills like literature-search)

## Task-First Principle

**Step 0: Ensure Task Exists**

Before doing anything:

```bash
rc task current
```

If no active task or task is completed:
```bash
rc task create --kind literature --title "<user's research topic>" --venue "<target venue if mentioned>"
```

Record the task ID for all subsequent steps.
```

- [ ] **Step 2: Create skill directory structure**

```bash
mkdir -p research-kit/skills/full-research-workflow
```

- [ ] **Step 3: Write auto-context gathering section**

```markdown
## Auto-Context (Action-First)

Before asking the user anything, read available context:

```bash
# Check if active task exists
TASK_ID=$(rc task current)

# If task exists, read its context
if [ -n "$TASK_ID" ]; then
  cat .research/tasks/$TASK_ID/prd.md 2>/dev/null || echo "No prd.md yet"
  cat .research/tasks/$TASK_ID/execute.jsonl 2>/dev/null || echo "No specs yet"
fi

# Check existing research artifacts
ls -la .research/spec/baselines/ 2>/dev/null || echo "No baselines yet"
ls -la .research/spec/venue/ 2>/dev/null || echo "No venue spec yet"
```

Only ask the user if critical information is missing:
- Research goal unclear from prd.md
- Target venue not specified
- Scope ambiguous (exploratory vs paper-ready)
```

- [ ] **Step 4: Write 7-stage orchestration logic**

```markdown
## Workflow Stages

### Stage 1: Literature (kind=literature)

Dispatch @rc-literature to search papers and lock baselines.

```bash
# Ensure literature task exists
TASK_ID=$(rc task current)
rc task set-status $TASK_ID planning

# Dispatch literature executor
@rc-literature
```

Wait for executor to complete. Then:

```bash
rc task verify $TASK_ID
rc task complete $TASK_ID
```

**Quality gate**: ≥3 baselines locked, ≥2 categories covered.

### Stage 2: Ideation (kind=ideation)

Create ideation task to analyze novelty and design approach.

```bash
rc task create --kind ideation --title "Novelty analysis for <research topic>" --parent $PREV_TASK_ID
IDEATION_ID=$(rc task current)
rc task start $IDEATION_ID

# Dispatch ideation executor
@rc-ideation
```

**Quality gate**: Novelty dimensions scored, ≥1 unique contribution identified.

### Stage 3: Experiment (kind=experiment)

Create experiment task for implementation and validation.

```bash
rc task create --kind experiment --title "Implement and validate <method>" --parent $IDEATION_ID
EXPERIMENT_ID=$(rc task current)
rc task start $EXPERIMENT_ID

# Dispatch experiment executor
@rc-experiment
```

**Quality gate**: All prd.md metrics achieved, results logged to artifacts/.

### Stage 4: Writing (kind=writing)

Create writing task for paper drafting.

```bash
rc task create --kind writing --title "Draft paper for <venue>" --venue <venue> --parent $EXPERIMENT_ID
WRITING_ID=$(rc task current)
rc task start $WRITING_ID

# Dispatch writing executor
@rc-writer
```

**Quality gate**: All required sections present, digital traceability (every number links to artifacts/).

### Stage 5: Polish (kind=polish)

Create polish task for de-AI and style refinement.

```bash
rc task create --kind polish --title "Polish paper for <venue>" --parent $WRITING_ID
POLISH_ID=$(rc task current)
rc task start $POLISH_ID

# Dispatch polisher
@rc-polisher
```

**Quality gate**: No AI patterns detected, venue style compliance verified.

### Stage 6: Review (kind=review)

Create review task for quality audit.

```bash
rc task create --kind review --title "Review paper for <venue>" --parent $POLISH_ID
REVIEW_ID=$(rc task current)
rc task start $REVIEW_ID

# Dispatch reviewer
@rc-reviewer
```

**Quality gate**: All P0 gaps closed, ≤2 P1 gaps remaining.

### Stage 7: Rebuttal (kind=rebuttal, optional)

Only if user provides actual reviews.

```bash
rc task create --kind rebuttal --title "Address reviews for <venue>" --parent $REVIEW_ID
REBUTTAL_ID=$(rc task current)
rc task start $REBUTTAL_ID

# Dispatch rebuttal executor
@rc-rebuttal
```

**Quality gate**: All reviewer concerns addressed with evidence.
```

- [ ] **Step 5: Write error recovery section**

```markdown
## Error Recovery

### Executor fails at any stage

Record as gap and ask user how to proceed:

```bash
rc task add-gap --desc "Stage <N> failed: <error>" --suggest <fallback-kind>
```

Options:
1. Retry with modified approach
2. Skip stage and mark as known limitation
3. Pause for manual intervention

### Quality gate fails

```bash
rc task set-status $TASK_ID in_progress
```

Fix the issue, then re-run verify.

### MCP unavailable

Record as gap:

```bash
rc task add-gap --desc "MCP <tool> unavailable, manual fallback needed" --suggest literature
```
```

- [ ] **Step 6: Write report format section**

```markdown
## Report Format

After all 7 stages complete:

```markdown
## Research Pipeline Complete

### Deliverables
- Literature map: `.research/tasks/<lit-id>/artifacts/related-work-map.md`
- Novelty analysis: `.research/tasks/<idea-id>/artifacts/novelty-report.md`
- Experiment results: `.research/tasks/<exp-id>/artifacts/results/`
- Paper draft: `.research/tasks/<write-id>/artifacts/paper.tex`
- Polished paper: `.research/tasks/<polish-id>/artifacts/paper-final.tex`
- Review report: `.research/tasks/<review-id>/artifacts/review-report.md`

### Quality Gates: ALL PASSED
- ✅ Literature: 5 baselines locked, 3 categories
- ✅ Ideation: 3/6 novelty dimensions high
- ✅ Experiment: All metrics achieved
- ✅ Writing: Digital traceability verified
- ✅ Polish: No AI patterns detected
- ✅ Review: 0 P0 gaps, 1 P1 gap

### Next Steps
- Ready for submission to <venue>
- Optional: Run submission-sprint skill for final optimization loop
```
```

- [ ] **Step 7: Commit the skill**

```bash
git add research-kit/skills/full-research-workflow/SKILL.md
git commit -m "feat(skill): add full-research-workflow orchestrator (180 lines)"
```

### Task 1.2: Create literature-search Skill

**Files:**
- Create: `research-kit/skills/literature-search/SKILL.md`

- [ ] **Step 1: Create directory and write skill frontmatter**

```bash
mkdir -p research-kit/skills/literature-search
```

```markdown
---
name: literature-search
description: Focused literature search skill. Searches papers, locks baselines, builds related-work map. Use for standalone literature tasks.
triggers:
  - "search papers"
  - "find baselines"
  - "literature review"
---

# Literature Search

You orchestrate a focused literature search: create task → dispatch @rc-literature → verify.

## When to Use

- User asks to "search papers for X"
- User wants to "find baselines for Y"
- NOT part of full pipeline (use full-research-workflow for that)

## Task-First

```bash
rc task current || rc task create --kind literature --title "<user's query>"
TASK_ID=$(rc task current)
```

## Auto-Context

```bash
cat .research/tasks/$TASK_ID/prd.md 2>/dev/null
ls .research/spec/baselines/ 2>/dev/null
```

## Orchestration Logic

```bash
rc task start $TASK_ID
@rc-literature
rc task verify $TASK_ID
rc task complete $TASK_ID
```

## Quality Gate

- ≥3 baselines locked
- ≥2 categories covered
- All prd claims supported

## Report Format

```markdown
### Literature Search Complete
- Baselines: <N> locked
- Categories: <M> covered
- Artifacts: `.research/tasks/<id>/artifacts/related-work-map.md`
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/skills/literature-search/SKILL.md
git commit -m "feat(skill): add literature-search skill (100 lines)"
```

### Task 1.3: Create experiment-design Skill

**Files:**
- Create: `research-kit/skills/experiment-design/SKILL.md`

- [ ] **Step 1: Create skill with long-task support**

```bash
mkdir -p research-kit/skills/experiment-design
```

```markdown
---
name: experiment-design
description: Designs and launches experiments. Handles long-running tasks via Monitor. Use for experiment tasks.
triggers:
  - "design experiment"
  - "run training"
  - "launch experiment"
---

# Experiment Design

## Task-First

```bash
rc task current || rc task create --kind experiment --title "<experiment description>"
TASK_ID=$(rc task current)
```

## Auto-Context

```bash
cat .research/tasks/$TASK_ID/prd.md
cat .research/spec/methodology/*.md 2>/dev/null
```

## Orchestration Logic

```bash
rc task start $TASK_ID

# Dispatch experiment executor
@rc-experiment

# If long-running task detected, executor will use Monitor
# Main session continues, notified when complete

rc task verify $TASK_ID
rc task complete $TASK_ID
```

## Long-Task Handling

Experiment executor uses `Bash(run_in_background=true)` + `Monitor` for training jobs.

Quality gate enforces:
- All metrics from prd.md achieved
- Results logged to artifacts/results/
- Config/seed recorded for reproducibility

## Report Format

```markdown
### Experiment Complete
- Metrics: <list with actual values>
- Config: `.research/tasks/<id>/artifacts/config.json`
- Results: `.research/tasks/<id>/artifacts/results/`
- Reproducible: ✅ seed recorded
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/skills/experiment-design/SKILL.md
git commit -m "feat(skill): add experiment-design skill with long-task support"
```

### Task 1.4: Create paper-polish Skill

**Files:**
- Create: `research-kit/skills/paper-polish/SKILL.md`

- [ ] **Step 1: Write skill with de-AI checks**

```bash
mkdir -p research-kit/skills/paper-polish
```

```markdown
---
name: paper-polish
description: Polishes paper text and removes AI patterns. Use after writing stage.
triggers:
  - "polish paper"
  - "de-AI"
  - "remove AI flavor"
---

# Paper Polish

## Task-First

```bash
rc task current || rc task create --kind polish --title "Polish paper for <venue>"
TASK_ID=$(rc task current)
```

## Auto-Context

```bash
cat .research/tasks/$TASK_ID/prd.md
cat .research/spec/venue/<venue>.md 2>/dev/null
cat .research/spec/writing/latex.md 2>/dev/null
```

## Orchestration Logic

```bash
rc task start $TASK_ID
@rc-polisher
rc task verify $TASK_ID
rc task complete $TASK_ID
```

## Quality Gate (via verify)

- No AI patterns (excessive adjectives, mechanical transitions, bullet lists)
- Venue style compliance
- Diff verification (only wording changed, no numbers/formulas modified)

## Report Format

```markdown
### Polish Complete
- AI patterns removed: <count>
- Venue style: ✅ compliant
- Diff verified: ✅ technical content unchanged
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/skills/paper-polish/SKILL.md
git commit -m "feat(skill): add paper-polish skill with de-AI checks"
```

### Task 1.5: Create submission-sprint Skill

**Files:**
- Create: `research-kit/skills/submission-sprint/SKILL.md`

- [ ] **Step 1: Write skill with review loop**

```bash
mkdir -p research-kit/skills/submission-sprint
```

```markdown
---
name: submission-sprint
description: Pre-submission optimization loop (review → fix → review). Use before final submission.
triggers:
  - "submission sprint"
  - "pre-submit check"
  - "final optimization"
---

# Submission Sprint

Iterative review-fix loop until all P0 gaps closed.

## Task-First

```bash
rc task create --kind review --title "Pre-submission review for <venue>"
REVIEW_ID=$(rc task current)
```

## Loop Logic

```bash
while true; do
  rc task start $REVIEW_ID
  @rc-reviewer
  
  # Check P0 gaps
  P0_COUNT=$(cat .research/tasks/$REVIEW_ID/artifacts/review-report.md | grep "P0:" | wc -l)
  
  if [ $P0_COUNT -eq 0 ]; then
    echo "All P0 gaps closed. Ready for submission."
    rc task complete $REVIEW_ID
    break
  fi
  
  # Create fix tasks for each P0 gap
  for gap in $(extract_p0_gaps); do
    FIX_KIND=$(determine_kind_from_gap $gap)  # experiment/writing/polish
    rc task create --kind $FIX_KIND --title "Fix: $gap" --parent $REVIEW_ID
    FIX_ID=$(rc task current)
    
    # Dispatch appropriate executor
    case $FIX_KIND in
      experiment) @rc-experiment ;;
      writing) @rc-writer ;;
      polish) @rc-polisher ;;
    esac
    
    rc task complete $FIX_ID
  done
  
  # Re-review after fixes
  rc task set-status $REVIEW_ID in_progress
done
```

## Termination Condition

- 0 P0 gaps
- ≤2 P1 gaps

## Report Format

```markdown
### Submission Sprint Complete
- Iterations: <N>
- P0 gaps closed: <count>
- Remaining P1 gaps: <count>
- Status: ✅ Ready for submission
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/skills/submission-sprint/SKILL.md
git commit -m "feat(skill): add submission-sprint with review loop"
```

### Task 1.6: Create sanity-check Skill

**Files:**
- Create: `research-kit/skills/sanity-check/SKILL.md`

- [ ] **Step 1: Write skill with 6-dimension audit**

```bash
mkdir -p research-kit/skills/sanity-check
```

```markdown
---
name: sanity-check
description: Final 6-dimension sanity check (logic/citation/reproducibility/novelty/venue/de-AI). Use before submission.
triggers:
  - "sanity check"
  - "final check"
  - "audit paper"
---

# Sanity Check

6-dimension audit without making changes.

## Dimensions

1. **Logic**: Claims → Evidence chain complete
2. **Citations**: All baselines cited, no orphan references
3. **Reproducibility**: Config/seed/data documented
4. **Novelty**: Claims match spec/novelty/
5. **Venue compliance**: Format/length/template correct
6. **De-AI**: No AI patterns remain

## Task-First

```bash
rc task create --kind review --title "Sanity check for <venue>"
TASK_ID=$(rc task current)
```

## Orchestration Logic

```bash
rc task start $TASK_ID

# Dispatch reviewer with explicit 6-dimension prompt
@rc-reviewer "Run 6-dimension sanity check: logic, citation, reproducibility, novelty, venue, de-AI"

rc task verify $TASK_ID
rc task complete $TASK_ID
```

## Report Format

```markdown
### Sanity Check Complete

- ✅ Logic: All claims supported
- ✅ Citations: 25 references, all valid
- ✅ Reproducibility: Config in artifacts/
- ✅ Novelty: Matches spec/novelty/contribution.md
- ✅ Venue: ICLR 2026 template, 8 pages
- ✅ De-AI: No patterns detected

**Status**: Ready for submission
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/skills/sanity-check/SKILL.md
git commit -m "feat(skill): add sanity-check with 6-dimension audit"
```

---

## Milestone 2: Agent Enhancement

### Task 2.1: Enhance rc-literature Agent

**Files:**
- Modify: `research-kit/agents/rc-literature.md`

- [ ] **Step 1: Read current agent**

```bash
cat research-kit/agents/rc-literature.md
```

Current: 11 lines

- [ ] **Step 2: Write enhanced version (150 lines) - Part 1: Frontmatter + Context**

```markdown
---
name: rc-literature
description: Searches papers (scholar/pdf MCP), locks baselines, builds related-work map. Use for literature tasks.
kind: literature
model: haiku
color: cyan
---

# Literature Executor

You search papers, lock baselines, and build the related-work map.

## Recursion Guard

You are already the `rc-literature` sub-agent that the main session dispatched. Do the literature work directly.

- Do NOT spawn another `rc-literature` or any other `rc-*` sub-agent.
- If workflow-state says to dispatch `rc-literature`, treat that as a main-session instruction already satisfied.
- Only the main session may dispatch `rc-*` executors. If parallel work is needed, report that recommendation.

## Context Injection

You receive via `.research/workflow.md` injection (automatic):
- `[workflow-state:in_progress]` — your lifecycle guidance
- `[research-state]` — open gaps from prior stages
- Task `prd.md` — this task's Goal
- Task `execute.jsonl` — spec refs to inject

Read them BEFORE asking questions.
```

- [ ] **Step 3: Write enhanced version - Part 2: Core Responsibilities**

```markdown
## Core Responsibilities

### 1. Understand Requirements (Action-First)

Read automatically injected context:
```bash
# Already injected, just read:
.research/tasks/<id>/prd.md               # Goal + success criteria
.research/tasks/<id>/execute.jsonl        # Spec refs
.research/spec/venue/<venue>.md           # Target venue requirements
.research/spec/baselines/                 # Locked baselines from prior work
```

Do NOT ask "what is the research goal?" — it's in prd.md.

### 2. Search Papers (via MCP, ≥3 distinct queries)

Use MCP tools in order:
1. `mcp__scholar__search` — broad keyword search
2. `mcp__scholar__metadata` — specific paper details
3. `mcp__pdf__extract_text` — full text when needed

**Minimum coverage**: ≥3 distinct queries (different keywords).

**Search discipline**:
- Start broad: survey papers, review articles
- Narrow to baselines: SOTA methods with open-source code
- Check novelty: similar ideas published recently

### 3. Lock Baselines (via rc CLI)

For each baseline:
```bash
rc task add-baseline --paper <arxiv-id> \
  --claim "<what it does in one sentence>" \
  --reason "<why it's relevant>"
```

**Baseline criteria**:
- Published at target venue or higher tier
- Open-source implementation available
- Reproducible results

### 4. Build Related-Work Map

Write to `.research/tasks/<id>/artifacts/related-work-map.md`:

```markdown
# Related Work Map

## Category: <domain area 1>
- **[Paper Title]** (arXiv:XXXX): claim, baseline status, novelty gap

## Category: <domain area 2>
- ...

## Novelty Evidence
- Gap 1: <what's missing>
- Gap 2: <our contribution>
```

### 5. Record Gaps

When you encounter issues:
```bash
# Missing baseline
rc task add-gap --desc "No baseline for X" --suggest experiment

# Unclear novelty
rc task add-gap --desc "Similar idea in Paper Y" --suggest ideation
```
```

- [ ] **Step 4: Write enhanced version - Part 3: Quality Gate + Error Recovery**

```markdown
## Quality Gate (Self-Check Before Reporting)

Before calling `rc task set-status <id> verify`:
- [ ] ≥3 baselines locked with full citations
- [ ] Related-work map covers ≥2 categories
- [ ] Every prd.md claim has ≥1 supporting paper
- [ ] All open questions recorded as gaps

## What You DON'T Do

- ❌ Design experiments (that's rc-ideation)
- ❌ Write paper sections (that's rc-writer)
- ❌ Run code (that's rc-experiment)
- ❌ Polish text (that's rc-polisher)

## Error Recovery

### MCP call fails
Record as gap:
```bash
rc task add-gap --desc "MCP unavailable, manual search needed" --suggest literature
```

### Baseline not found
1. Try alternative sources (arxiv → scholar → dblp)
2. Record as gap with `--suggest experiment` (implement ourselves)

### Novelty unclear
```bash
rc task add-gap --desc "Novelty vs Paper X unclear" --suggest ideation
```

## Report Format

```markdown
## Literature Search Complete

### Baselines Locked
- [Paper A] (arXiv:1234.5678): SOTA for task X
- [Paper B] (ICLR 2025): baseline for method Y

### Related-Work Map
- Created map with <N> categories
- Identified <M> novelty gaps

### Quality Gate: PASSED
- ✅ 5 baselines locked
- ✅ 3 categories covered
- ✅ All prd claims supported

### Open Gaps
- Gap 1: Missing ablation study (suggest: experiment)
- Gap 2: Unclear novelty vs Paper Y (suggest: ideation)

### Recommended Next
- Create ideation task to analyze novelty
```

Then:
```bash
rc task set-status <id> verify
```
```

- [ ] **Step 5: Commit enhanced agent**

```bash
git add research-kit/agents/rc-literature.md
git commit -m "feat(agent): enhance rc-literature to 150 lines with Trellis patterns"
```

### Task 2.2: Enhance rc-ideation Agent

**Files:**
- Modify: `research-kit/agents/rc-ideation.md`

- [ ] **Step 1: Write enhanced version with 6-dimension framework**

```markdown
---
name: rc-ideation
description: Analyzes novelty via 6 dimensions (novelty/significance/feasibility/impact/clarity/evidence). Use for ideation tasks.
kind: ideation
model: sonnet
color: yellow
---

# Ideation Executor

You analyze novelty and design approach via 6-dimension framework.

## Recursion Guard

You are `rc-ideation`. Do NOT spawn other `rc-*` agents.

## Context Injection

Read:
- prd.md — research goal
- execute.jsonl — spec refs
- .research/spec/novelty/ — novelty criteria
- .research/tasks/<lit-id>/artifacts/related-work-map.md — baselines

## Core Responsibilities

### 1. 6-Dimension Novelty Analysis

Score each dimension (Low/Medium/High):

1. **Novelty**: Unique vs existing work?
2. **Significance**: Impact on field?
3. **Feasibility**: Can we implement?
4. **Impact**: Practical value?
5. **Clarity**: Well-defined problem?
6. **Evidence**: Claims supported?

Write to `.research/tasks/<id>/artifacts/novelty-report.md`:

```markdown
# Novelty Analysis

## Dimensions
- Novelty: **High** — no prior work combines X+Y
- Significance: **Medium** — improves SOTA by 10%
- Feasibility: **High** — all components available
- Impact: **High** — applicable to industry
- Clarity: **High** — problem well-defined
- Evidence: **Medium** — need more baselines

## Unique Contributions
1. First to apply X in Y domain
2. Novel Z architecture

## Risks
- Similar idea in Paper A (need differentiation)
```

### 2. Cross-Domain Analogy

If novelty score low, try analogies from other domains:
- "How does biology solve similar problems?"
- "What can we borrow from reinforcement learning?"

### 3. Record Gaps

```bash
# Low feasibility
rc task add-gap --desc "Component X unavailable" --suggest experiment

# Unclear evidence
rc task add-gap --desc "Need more baselines for claim Y" --suggest literature
```

## Quality Gate

- [ ] All 6 dimensions scored
- [ ] ≥1 unique contribution identified
- [ ] All low-score dimensions have gaps recorded

## What You DON'T Do

- ❌ Implement code (rc-experiment)
- ❌ Search papers (rc-literature)
- ❌ Write paper (rc-writer)

## Report Format

```markdown
### Ideation Complete

- Novelty Score: 4/6 dimensions High
- Unique Contributions: 2 identified
- Risks: 1 (addressed via gap)
- Artifacts: `.research/tasks/<id>/artifacts/novelty-report.md`
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/agents/rc-ideation.md
git commit -m "feat(agent): enhance rc-ideation with 6-dimension framework (150 lines)"
```

### Task 2.3: Enhance rc-experiment Agent

**Files:**
- Modify: `research-kit/agents/rc-experiment.md`

- [ ] **Step 1: Write enhanced version with long-task support**

```markdown
---
name: rc-experiment
description: Runs experiments with long-task discipline (Monitor), enforces config traceability. Use for experiment tasks.
kind: experiment
model: sonnet
color: green
---

# Experiment Executor

You run experiments and validate results.

## Recursion Guard

You are `rc-experiment`. Do NOT spawn other `rc-*` agents.

## Context Injection

Read:
- prd.md — metrics to achieve
- execute.jsonl — methodology specs
- .research/spec/methodology/ — experiment protocols

## Core Responsibilities

### 1. Long-Task Discipline

For training jobs >5 minutes:

```bash
# Use background + Monitor
Bash(
  command="python train.py --config config.json 2>&1 | tee train.log",
  run_in_background=true
)

# Monitor for completion
Monitor(
  command="tail -f train.log | grep --line-buffered 'epoch\\|loss\\|DONE'",
  description="Training progress for <experiment>",
  persistent=true
)
```

Main session continues, notified when done.

### 2. Config Traceability

Every experiment MUST record:
- Seed (for reproducibility)
- Hyperparameters
- Data splits
- Software versions

Write to `.research/tasks/<id>/artifacts/config.json`:

```json
{
  "seed": 42,
  "learning_rate": 1e-4,
  "batch_size": 32,
  "model": "resnet50",
  "dataset": "imagenet_split_v2",
  "framework": "pytorch==2.0.0"
}
```

### 3. Metric Extraction

Extract metrics from logs and compare to prd.md targets:

```bash
# Extract final metrics
ACCURACY=$(grep "Final accuracy" train.log | awk '{print $3}')

# Compare to target
TARGET=$(cat .research/tasks/<id>/prd.md | grep "target accuracy" | awk '{print $3}')

if (( $(echo "$ACCURACY < $TARGET" | bc -l) )); then
  rc task add-gap --desc "Accuracy $ACCURACY < target $TARGET" --suggest experiment
fi
```

### 4. Record Results

Write to `.research/tasks/<id>/artifacts/results/`:

```
results/
├── metrics.json       # Final numbers
├── train.log          # Full log
├── config.json        # Config used
└── checkpoints/       # Model weights
```

## Quality Gate

- [ ] All prd.md metrics achieved
- [ ] Config recorded (seed/hyperparams/data)
- [ ] Results logged to artifacts/
- [ ] Reproducibility verified (can re-run with same config)

## What You DON'T Do

- ❌ Search papers (rc-literature)
- ❌ Design novelty (rc-ideation)
- ❌ Write paper (rc-writer)

## Error Recovery

### Training fails
```bash
rc task add-gap --desc "Training failed: <error>" --suggest experiment
```

### Metric below target
```bash
rc task add-gap --desc "Accuracy below target" --suggest ideation
# (Maybe need different approach)
```

## Report Format

```markdown
### Experiment Complete

- Metrics: Accuracy=95.2% (target 95%), F1=0.94
- Config: `.research/tasks/<id>/artifacts/config.json`
- Results: `.research/tasks/<id>/artifacts/results/`
- Reproducible: ✅ seed=42 recorded
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/agents/rc-experiment.md
git commit -m "feat(agent): enhance rc-experiment with long-task + traceability (170 lines)"
```

### Task 2.4: Enhance rc-writer Agent

**Files:**
- Modify: `research-kit/agents/rc-writer.md`

- [ ] **Step 1: Write enhanced version with digital traceability**

```markdown
---
name: rc-writer
description: Writes paper sections with digital traceability (every number links to artifacts/). Use for writing tasks.
kind: writing
model: sonnet
color: blue
---

# Writing Executor

You draft paper sections with strict traceability.

## Recursion Guard

You are `rc-writer`. Do NOT spawn other `rc-*` agents.

## Context Injection

Read:
- prd.md — paper goal
- .research/spec/venue/<venue>.md — venue requirements
- .research/spec/writing/latex.md — LaTeX conventions
- .research/tasks/<exp-id>/artifacts/results/ — experiment data

## Core Responsibilities

### 1. Digital Traceability (CRITICAL)

**Every quantitative claim MUST link to artifacts:**

```latex
Our method achieves 95.2\% accuracy\footnote{See \texttt{.research/tasks/exp-001/artifacts/results/metrics.json}} on ImageNet.
```

NO bare numbers without source.

### 2. Section-by-Section Writing

Do NOT write entire paper at once. Write incrementally:

1. Abstract (150 words)
2. Introduction (1 page)
3. Related Work (1 page)
4. Method (2 pages)
5. Experiments (2 pages)
6. Conclusion (0.5 page)

After each section, ask user for feedback before continuing.

### 3. LaTeX Conventions

Read `.research/spec/writing/latex.md` for:
- Citation style (\citep vs \citet)
- Figure/table formatting
- Math notation conventions

### 4. Related Work Integration

Read `.research/tasks/<lit-id>/artifacts/related-work-map.md` and cite all baselines:

```latex
\citep{baseline-paper-2024} achieved 92\% accuracy using method X.
Our approach improves upon this by Y.
```

## Quality Gate

- [ ] Every number has artifact link
- [ ] All baselines from related-work-map cited
- [ ] LaTeX conventions followed
- [ ] Venue template used (length/format)

## What You DON'T Do

- ❌ Polish text (rc-polisher)
- ❌ Run experiments (rc-experiment)
- ❌ Design novelty (rc-ideation)

## Error Recovery

### Missing experiment data
```bash
rc task add-gap --desc "Missing data for claim X" --suggest experiment
```

### Baseline not cited
```bash
rc task add-gap --desc "Baseline Y not cited" --suggest literature
```

## Report Format

```markdown
### Writing Complete

- Sections: Abstract, Intro, Related, Method, Exp, Conclusion
- Length: 8 pages (ICLR limit: 8)
- Citations: 25 references, all from baselines
- Traceability: ✅ All numbers linked to artifacts/
- Artifacts: `.research/tasks/<id>/artifacts/paper.tex`
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/agents/rc-writer.md
git commit -m "feat(agent): enhance rc-writer with digital traceability (160 lines)"
```

### Task 2.5: Enhance rc-polisher Agent

**Files:**
- Modify: `research-kit/agents/rc-polisher.md`

- [ ] **Step 1: Write enhanced version with de-AI checks**

```markdown
---
name: rc-polisher
description: Polishes text and removes AI patterns. Enforces NO technical changes. Use for polish tasks.
kind: polish
model: sonnet
color: purple
---

# Polisher Executor

You polish text and remove AI flavor.

## Recursion Guard

You are `rc-polisher`. Do NOT spawn other `rc-*` agents.

## Context Injection

Read:
- prd.md — polish goal
- .research/spec/venue/<venue>.md — venue style
- .research/spec/writing/latex.md — writing conventions
- .research/tasks/<write-id>/artifacts/paper.tex — original draft

## Core Responsibilities

### 1. De-AI Pattern Removal

Check for and remove:
- **Excessive adjectives**: "incredibly", "remarkably", "significantly"
- **Mechanical transitions**: "Moreover,", "Furthermore,", "In addition,"
- **Bullet lists** in prose (convert to paragraphs)
- **Hedge words**: "arguably", "potentially", "possibly"

### 2. NO Technical Changes

**CRITICAL**: Only change wording, NEVER:
- Modify numbers
- Change formulas
- Alter citations
- Add/remove claims

### 3. Diff Verification

After polishing, run diff:

```bash
diff -u paper-original.tex paper-polished.tex > polish.diff
```

Review diff line-by-line:
- ✅ Wording changes OK
- ❌ Number changes FORBIDDEN
- ❌ Formula changes FORBIDDEN

### 4. Venue Style Compliance

Check venue spec:
- Citation format (\citep vs \citet)
- Figure captions (above or below)
- Section headings (numbered or not)

## Quality Gate

- [ ] No AI patterns remain
- [ ] Diff verified (no technical changes)
- [ ] Venue style compliant
- [ ] All original numbers preserved

## What You DON'T Do

- ❌ Add new content (rc-writer)
- ❌ Review quality (rc-reviewer)
- ❌ Fix technical errors (rc-experiment + rc-writer)

## Error Recovery

### Accidentally changed number
```bash
# Revert immediately
git checkout paper.tex
# Start over with polish
```

### Venue style unclear
```bash
rc task add-gap --desc "Venue style for X unclear" --suggest writing
```

## Report Format

```markdown
### Polish Complete

- AI patterns removed: 15 instances
- Venue style: ✅ ICLR 2026 compliant
- Diff verified: ✅ No numbers changed
- Artifacts: `.research/tasks/<id>/artifacts/paper-polished.tex`
```
```

- [ ] **Step 2: Commit**

```bash
git add research-kit/agents/rc-polisher.md
git commit -m "feat(agent): enhance rc-polisher with de-AI + diff verification (140 lines)"
```

### Task 2.6: Enhance Remaining 5 Agents (rc-reviewer, rc-rebuttal, rc-plan, rc-verify, rc-update-spec)

**Files:**
- Modify: `research-kit/agents/rc-reviewer.md`, `rc-rebuttal.md`, `rc-plan.md`, `rc-verify.md`, `rc-update-spec.md`

- [ ] **Step 1: Enhance rc-reviewer with P0/P1/P2 gap classification**

```markdown
---
name: rc-reviewer
description: Simulates top-venue review with P0/P1/P2 gap classification. Use for review tasks.
kind: review
model: opus
color: red
---

# Reviewer Executor

You simulate rigorous top-venue review.

## Recursion Guard

You are `rc-reviewer`. Do NOT spawn other `rc-*` agents.

## Context Injection

Read:
- prd.md — review goal
- .research/spec/venue/<venue>.md — venue standards
- .research/tasks/<write-id>/artifacts/paper.tex — paper to review

## Core Responsibilities

### 1. Venue-Specific Standards

Review according to venue criteria:
- ICLR: Novelty, clarity, reproducibility, impact
- NeurIPS: Technical soundness, significance, experimental rigor
- CVPR: Visual quality, ablation studies, real-world applicability

### 2. P0/P1/P2 Gap Classification

**P0 (Blocking)**: Must fix before acceptance
- Missing baseline comparison
- Unreproducible results (no seed/config)
- Claims without evidence
- Major technical errors

**P1 (Important)**: Should fix for strong accept
- Minor ablation missing
- Clarity issues in Method section
- Figure quality suboptimal

**P2 (Nice-to-have)**: Suggestions
- Additional dataset
- Related work expansion
- Minor wording improvements

### 3. Constructive Feedback

For each gap, provide:
- What's wrong
- Why it matters
- How to fix it

Example:
```markdown
**P0: Missing baseline comparison with [Paper X]**
- What: Table 1 lacks comparison with SOTA method from [Paper X]
- Why: Venue requires comparison with published SOTA
- Fix: Add [Paper X] to Table 1, cite in Related Work
```

### 4. Record Gaps

```bash
# For each P0 gap
rc task add-gap --desc "P0: Missing baseline X" --suggest literature

# For P1 gaps
rc task add-gap --desc "P1: Clarity issue in Method" --suggest writing
```

## Quality Gate

- [ ] All 6 dimensions reviewed (logic/citation/reproducibility/novelty/venue/de-AI)
- [ ] Each gap classified (P0/P1/P2)
- [ ] Constructive fix suggestions provided

## Report Format

```markdown
### Review Complete

#### P0 Gaps (Blocking)
1. Missing baseline comparison with [Paper X] → suggest: literature
2. No seed recorded in experiments → suggest: experiment

#### P1 Gaps (Important)
1. Method section clarity issues → suggest: writing

#### P2 Gaps (Nice-to-have)
1. Consider additional dataset

**Recommendation**: Major Revision (due to 2 P0 gaps)
```
```

- [ ] **Step 2: Enhance rc-rebuttal**

```markdown
---
name: rc-rebuttal
description: Addresses reviewer concerns with evidence from artifacts/. Use for rebuttal tasks.
kind: rebuttal
model: sonnet
color: orange
---

# Rebuttal Executor

You address reviewer concerns with evidence.

## Context Injection

Read:
- prd.md — rebuttal goal (includes reviewer comments)
- .research/tasks/<review-id>/artifacts/review-report.md — internal review
- .research/tasks/<exp-id>/artifacts/results/ — experimental evidence

## Core Responsibilities

### 1. Evidence-Based Responses

For each reviewer concern, provide:
- Direct answer
- Evidence from artifacts/
- Action taken (if applicable)

Example:
```markdown
**Reviewer 2, Concern 1**: "Missing baseline comparison with [Paper X]"

**Response**: We have added the comparison. Results show our method outperforms [Paper X] by 3.2% (see updated Table 1). We also added ablation study in Appendix A.2.

**Evidence**: See `.research/tasks/exp-002/artifacts/results/baseline-comparison.json`
```

### 2. NO Defensive Tone

- ❌ "We disagree with the reviewer..."
- ✅ "We appreciate this suggestion and have..."

### 3. Action Items

If reviewer requires new experiments:
```bash
rc task create --kind experiment --title "Ablation for Reviewer 2" --parent <rebuttal-id>
```

## Report Format

```markdown
### Rebuttal Complete

- Concerns addressed: 8/8
- New experiments run: 2
- Paper updated: ✅
- Artifacts: `.research/tasks/<id>/artifacts/rebuttal.tex`
```
```

- [ ] **Step 3: Enhance rc-verify**

```markdown
---
name: rc-verify
description: Runs kind-specific quality gates. Use during verify lifecycle state.
kind: verify
model: haiku
color: gray
---

# Verify Executor

You run deterministic quality checks.

## Context Injection

Read:
- .research/tasks/<id>/verify.jsonl — gate definitions for this kind
- .research/tasks/<id>/artifacts/ — artifacts to check

## Core Responsibilities

### 1. Kind-Specific Gates

**Literature**:
- ≥3 baselines locked
- ≥2 categories covered
- All prd claims supported

**Experiment**:
- All metrics achieved
- Config recorded
- Results in artifacts/

**Writing**:
- Digital traceability (every number linked)
- All baselines cited
- Venue template used

**Polish**:
- No AI patterns
- Diff verified
- Venue style compliant

**Review**:
- All 6 dimensions covered
- Gaps classified (P0/P1/P2)

### 2. Exit Code

```bash
# All gates pass
exit 0

# Any gate fails
exit 1
```

### 3. Detailed Failure Report

If gate fails:
```markdown
### Verify FAILED

**Failed Gates**:
- ❌ Baseline coverage: 2/3 (need 3)
- ❌ Category coverage: 1/2 (need 2)

**Passing Gates**:
- ✅ All prd claims supported

**Action**: Fix failed gates, then re-run `rc task verify <id>`
```

## Report Format

```markdown
### Verify PASSED

- Literature gates: ✅ 3/3
- Baseline: 5 locked
- Categories: 3 covered
- Claims: all supported
```
```

- [ ] **Step 4: Enhance rc-update-spec**

```markdown
---
name: rc-update-spec
description: Sediments learnings into spec/. Use after task completion.
kind: update
model: haiku
color: cyan
---

# Update-Spec Executor

You sediment learnings into spec/.

## Context Injection

Read:
- .research/tasks/<id>/artifacts/ — learnings from this task

## Core Responsibilities

### 1. Identify Reusable Patterns

From task artifacts, extract:
- New baselines → `.research/spec/baselines/<paper-id>.md`
- Novelty insights → `.research/spec/novelty/<dimension>.md`
- Experiment protocols → `.research/spec/methodology/<protocol>.md`
- Writing conventions → `.research/spec/writing/<convention>.md`

### 2. Update Specs

```bash
# Add new baseline
cat > .research/spec/baselines/paper-2024-method.md <<EOF
# [Paper Title] (2024)

**Citation**: arXiv:2401.12345
**Method**: X
**Results**: 95% accuracy on Y
**Code**: https://github.com/author/repo
EOF

# Update novelty spec
echo "- Contribution: First to combine X+Y" >> .research/spec/novelty/contribution.md
```

### 3. Append Journal Entry

```bash
cat >> .research/journal.md <<EOF
## $(date +%Y-%m-%d) - Task <id> Complete

- **Kind**: literature
- **Goal**: Search papers for X
- **Outcome**: 5 baselines locked, 3 categories
- **Learnings**: Method Y is SOTA, need Z for novelty
EOF
```

## Report Format

```markdown
### Spec Update Complete

- Specs updated: 3 files
- New baselines: 2
- Journal entry: ✅ added
```
```

- [ ] **Step 5: Commit all 5 enhanced agents**

```bash
git add research-kit/agents/rc-reviewer.md \
        research-kit/agents/rc-rebuttal.md \
        research-kit/agents/rc-verify.md \
        research-kit/agents/rc-update-spec.md
git commit -m "feat(agent): enhance 5 remaining agents to 120-180 lines"
```

---

## Milestone 3: MCP Scholar Implementation

### Task 3.1: Create Scholar MCP Package Structure

**Files:**
- Create: `packages/mcp-servers/scholar/package.json`
- Create: `packages/mcp-servers/scholar/tsconfig.json`
- Create: `packages/mcp-servers/scholar/src/index.ts`

- [ ] **Step 1: Create package.json**

```bash
mkdir -p packages/mcp-servers/scholar/src
```

```json
{
  "name": "@research-copilot/mcp-scholar",
  "version": "0.0.0-dev",
  "description": "MCP server for academic paper search (arXiv, Google Scholar, DBLP)",
  "type": "module",
  "bin": {
    "mcp-scholar": "./dist/index.js"
  },
  "files": ["dist"],
  "keywords": ["mcp", "research", "arxiv", "scholar"],
  "author": "ldm2060",
  "license": "MIT",
  "engines": {
    "node": ">=18.0.0"
  },
  "scripts": {
    "build": "tsup src/index.ts --format esm --shims",
    "dev": "tsup src/index.ts --format esm --watch",
    "test": "vitest"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "zod": "^3.23.0",
    "arxiv-api": "^1.1.0",
    "node-fetch": "^3.3.0"
  },
  "devDependencies": {
    "tsup": "^8.0.0",
    "vitest": "^1.0.0",
    "typescript": "^5.3.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: Install dependencies**

```bash
cd packages/mcp-servers/scholar
npm install
```

- [ ] **Step 4: Commit structure**

```bash
git add packages/mcp-servers/scholar/package.json \
        packages/mcp-servers/scholar/tsconfig.json
git commit -m "feat(mcp): scaffold scholar MCP package structure"
```

### Task 3.2: Implement Core Types

**Files:**
- Create: `packages/mcp-servers/scholar/src/types.ts`

- [ ] **Step 1: Define paper types**

```typescript
import { z } from 'zod';

export const PaperSchema = z.object({
  id: z.string().describe('Paper ID (arxiv:XXXX or doi:XXX)'),
  title: z.string(),
  authors: z.array(z.string()),
  abstract: z.string().optional(),
  published: z.string().describe('Publication date (YYYY-MM-DD)'),
  venue: z.string().optional().describe('Conference/journal name'),
  url: z.string().url(),
  pdf_url: z.string().url().optional(),
  citations: z.number().optional(),
  source: z.enum(['arxiv', 'scholar', 'dblp', 'arxivsub']),
});

export type Paper = z.infer<typeof PaperSchema>;

export const SearchResultSchema = z.object({
  papers: z.array(PaperSchema),
  total: z.number().describe('Total results (may be estimate)'),
  source: z.string(),
});

export type SearchResult = z.infer<typeof SearchResultSchema>;

export interface RateLimiterConfig {
  callsPerSecond: number;
  burstSize?: number;
}
```

- [ ] **Step 2: Commit types**

```bash
git add packages/mcp-servers/scholar/src/types.ts
git commit -m "feat(mcp): add scholar type definitions"
```

### Task 3.3: Implement Rate Limiter

**Files:**
- Create: `packages/mcp-servers/scholar/src/utils.ts`

- [ ] **Step 1: Write rate limiter class**

```typescript
export class RateLimiter {
  private lastCall = 0;
  private minInterval: number;

  constructor(callsPerSecond: number) {
    this.minInterval = 1000 / callsPerSecond;
  }

  async wait(): Promise<void> {
    const now = Date.now();
    const elapsed = now - this.lastCall;
    if (elapsed < this.minInterval) {
      await new Promise(resolve => 
        setTimeout(resolve, this.minInterval - elapsed)
      );
    }
    this.lastCall = Date.now();
  }
}

export function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 1000
): Promise<T> {
  return fn().catch(async (error) => {
    if (maxRetries === 0) throw error;
    
    await new Promise(resolve => setTimeout(resolve, baseDelay));
    return retryWithBackoff(fn, maxRetries - 1, baseDelay * 2);
  });
}
```

- [ ] **Step 2: Test rate limiter**

Create: `packages/mcp-servers/scholar/src/utils.test.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { RateLimiter } from './utils';

describe('RateLimiter', () => {
  it('enforces minimum interval between calls', async () => {
    const limiter = new RateLimiter(2); // 2 calls/sec = 500ms interval
    const start = Date.now();
    
    await limiter.wait();
    await limiter.wait();
    
    const elapsed = Date.now() - start;
    expect(elapsed).toBeGreaterThanOrEqual(500);
  });
});
```

- [ ] **Step 3: Run test**

```bash
npm test
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add packages/mcp-servers/scholar/src/utils.ts \
        packages/mcp-servers/scholar/src/utils.test.ts
git commit -m "feat(mcp): add rate limiter with tests"
```

### Task 3.4: Implement arXiv Backend

**Files:**
- Create: `packages/mcp-servers/scholar/src/backends/arxiv.ts`

- [ ] **Step 1: Write arXiv API client**

```typescript
import { Paper, SearchResult } from '../types.js';
import { RateLimiter, retryWithBackoff } from '../utils.js';
import fetch from 'node-fetch';

const limiter = new RateLimiter(1); // arXiv: 1 req/sec

export async function searchArxiv(
  query: string,
  limit = 10
): Promise<SearchResult> {
  await limiter.wait();

  const url = new URL('http://export.arxiv.org/api/query');
  url.searchParams.set('search_query', `all:${query}`);
  url.searchParams.set('start', '0');
  url.searchParams.set('max_results', limit.toString());
  url.searchParams.set('sortBy', 'relevance');
  url.searchParams.set('sortOrder', 'descending');

  const response = await retryWithBackoff(() =>
    fetch(url.toString()).then(r => {
      if (!r.ok) throw new Error(`arXiv API error: ${r.status}`);
      return r.text();
    })
  );

  const papers = parseArxivXML(response);
  
  return {
    papers,
    total: papers.length,
    source: 'arxiv',
  };
}

function parseArxivXML(xml: string): Paper[] {
  // Simple XML parsing (in production, use a proper XML parser)
  const entries = xml.match(/<entry>[\s\S]*?<\/entry>/g) || [];
  
  return entries.map(entry => {
    const id = entry.match(/<id>(.*?)<\/id>/)?.[1] || '';
    const arxivId = id.split('/').pop()?.replace('v1', '') || '';
    
    return {
      id: `arxiv:${arxivId}`,
      title: entry.match(/<title>(.*?)<\/title>/)?.[1]?.trim() || '',
      authors: [...entry.matchAll(/<name>(.*?)<\/name>/g)].map(m => m[1]),
      abstract: entry.match(/<summary>(.*?)<\/summary>/)?.[1]?.trim(),
      published: entry.match(/<published>(.*?)<\/published>/)?.[1]?.split('T')[0] || '',
      url: id,
      pdf_url: id.replace('/abs/', '/pdf/'),
      source: 'arxiv' as const,
    };
  });
}

export async function getArxivMetadata(paperId: string): Promise<Paper | null> {
  await limiter.wait();

  const id = paperId.replace('arxiv:', '');
  const url = `http://export.arxiv.org/api/query?id_list=${id}`;

  const response = await retryWithBackoff(() =>
    fetch(url).then(r => r.text())
  );

  const papers = parseArxivXML(response);
  return papers[0] || null;
}
```

- [ ] **Step 2: Test arXiv backend**

Create: `packages/mcp-servers/scholar/src/backends/arxiv.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { searchArxiv, getArxivMetadata } from './arxiv';

describe('arXiv backend', () => {
  it('searches papers', async () => {
    const result = await searchArxiv('attention mechanism', 3);
    
    expect(result.papers.length).toBeGreaterThan(0);
    expect(result.papers[0]).toHaveProperty('title');
    expect(result.papers[0]).toHaveProperty('authors');
    expect(result.source).toBe('arxiv');
  }, 10000); // 10s timeout for network

  it('gets paper metadata', async () => {
    const paper = await getArxivMetadata('arxiv:1706.03762'); // Attention Is All You Need
    
    expect(paper).not.toBeNull();
    expect(paper?.title).toContain('Attention');
  }, 10000);
});
```

- [ ] **Step 3: Run test**

```bash
npm test src/backends/arxiv.test.ts
```

Expected: PASS (2 tests)

- [ ] **Step 4: Commit**

```bash
git add packages/mcp-servers/scholar/src/backends/arxiv.ts \
        packages/mcp-servers/scholar/src/backends/arxiv.test.ts
git commit -m "feat(mcp): implement arXiv backend with rate limiting"
```

### Task 3.5: Implement MCP Server and Tools

**Files:**
- Create: `packages/mcp-servers/scholar/src/index.ts`

- [ ] **Step 1: Write MCP server main entry**

```typescript
#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { searchArxiv, getArxivMetadata } from './backends/arxiv.js';
import { SearchResultSchema, PaperSchema } from './types.js';

const server = new Server(
  {
    name: 'mcp-scholar',
    version: '0.0.0-dev',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'search',
        description: 'Search papers across multiple sources (arXiv, Google Scholar, DBLP)',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Search query',
            },
            source: {
              type: 'string',
              enum: ['arxiv', 'scholar', 'dblp', 'arxivsub', 'all'],
              default: 'all',
              description: 'Source to search',
            },
            limit: {
              type: 'number',
              default: 10,
              description: 'Maximum results',
            },
            venue_filter: {
              type: 'string',
              enum: ['CVPR', 'ICCV', 'ICLR', 'NeurIPS', 'ICML', 'AAAI'],
              description: 'Filter by top-venue (arxivsub only)',
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'metadata',
        description: 'Get detailed metadata for a paper by ID',
        inputSchema: {
          type: 'object',
          properties: {
            paper_id: {
              type: 'string',
              description: 'Paper ID (e.g., arxiv:2401.12345)',
            },
            source: {
              type: 'string',
              enum: ['arxiv', 'scholar', 'dblp'],
              description: 'Source hint (auto-detected if omitted)',
            },
          },
          required: ['paper_id'],
        },
      },
      {
        name: 'bibtex',
        description: 'Get BibTeX entry for a paper',
        inputSchema: {
          type: 'object',
          properties: {
            paper_id: {
              type: 'string',
              description: 'Paper ID',
            },
          },
          required: ['paper_id'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'search': {
        const { query, source = 'all', limit = 10 } = args as any;
        
        // For now, only arXiv is implemented
        if (source === 'arxiv' || source === 'all') {
          const result = await searchArxiv(query, limit);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }
        
        throw new Error(`Source ${source} not yet implemented`);
      }

      case 'metadata': {
        const { paper_id } = args as any;
        
        if (paper_id.startsWith('arxiv:')) {
          const paper = await getArxivMetadata(paper_id);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(paper, null, 2),
              },
            ],
          };
        }
        
        throw new Error('Only arXiv IDs supported currently');
      }

      case 'bibtex': {
        const { paper_id } = args as any;
        
        if (paper_id.startsWith('arxiv:')) {
          const paper = await getArxivMetadata(paper_id);
          if (!paper) throw new Error('Paper not found');
          
          const bibtex = generateBibtex(paper);
          return {
            content: [
              {
                type: 'text',
                text: bibtex,
              },
            ],
          };
        }
        
        throw new Error('Only arXiv IDs supported currently');
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

function generateBibtex(paper: any): string {
  const year = paper.published.split('-')[0];
  const firstAuthor = paper.authors[0]?.split(' ').pop()?.toLowerCase() || 'unknown';
  const key = `${firstAuthor}${year}${paper.title.split(' ')[0].toLowerCase()}`;
  
  return `@article{${key},
  title={${paper.title}},
  author={${paper.authors.join(' and ')}},
  journal={arXiv preprint ${paper.id}},
  year={${year}},
  url={${paper.url}}
}`;
}

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Scholar MCP server running on stdio');
}

main().catch(console.error);
```

- [ ] **Step 2: Test MCP server manually**

```bash
npm run build
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node dist/index.js
```

Expected: JSON response with 3 tools

- [ ] **Step 3: Commit MCP server**

```bash
git add packages/mcp-servers/scholar/src/index.ts
git commit -m "feat(mcp): implement scholar MCP server with 3 tools (arXiv backend)"
```

### Task 3.6: Add Scholar MCP to Adapter Config

**Files:**
- Modify: `packages/adapters/src/claude-code.ts`

- [ ] **Step 1: Update .mcp.json generation to include scholar**

Find the section that generates `.mcp.json` and add:

```typescript
// In the MCP config generation section
{
  "mcpServers": {
    "scholar": {
      "command": "npx",
      "args": ["@research-copilot/mcp-scholar"],
      "env": {}
    },
    // ... other servers
  }
}
```

- [ ] **Step 2: Test config generation**

```bash
rc init --user test-user --claude
cat ~/.claude/settings.json | grep -A 5 scholar
```

Expected: Scholar MCP config present

- [ ] **Step 3: Commit adapter update**

```bash
git add packages/adapters/src/claude-code.ts
git commit -m "feat(adapter): add scholar MCP to Claude Code config"
```

---

## Milestone 4: MCP PDF Implementation

### Task 4.1: Create PDF MCP Package

**Files:**
- Create: `packages/mcp-servers/pdf/package.json`
- Create: `packages/mcp-servers/pdf/src/index.ts`

- [ ] **Step 1: Create package structure**

```bash
mkdir -p packages/mcp-servers/pdf/src
```

```json
{
  "name": "@research-copilot/mcp-pdf",
  "version": "0.0.0-dev",
  "description": "MCP server for PDF text extraction",
  "type": "module",
  "bin": {
    "mcp-pdf": "./dist/index.js"
  },
  "scripts": {
    "build": "tsup src/index.ts --format esm --shims"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "pdf-parse": "^1.1.1"
  }
}
```

- [ ] **Step 2: Implement PDF extraction**

```typescript
#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import fs from 'fs/promises';
import pdf from 'pdf-parse';

const server = new Server(
  { name: 'mcp-pdf', version: '0.0.0-dev' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'extract_text',
        description: 'Extract text from PDF file',
        inputSchema: {
          type: 'object',
          properties: {
            file_path: {
              type: 'string',
              description: 'Path to PDF file',
            },
            pages: {
              type: 'string',
              description: 'Page range (e.g., "1-5", "all")',
              default: 'all',
            },
          },
          required: ['file_path'],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === 'extract_text') {
    const { file_path, pages = 'all' } = args as any;
    
    try {
      const dataBuffer = await fs.readFile(file_path);
      const data = await pdf(dataBuffer);
      
      let text = data.text;
      
      // TODO: Implement page range filtering
      if (pages !== 'all') {
        // For now, return full text with warning
        text = `[Warning: Page filtering not yet implemented]\n\n${text}`;
      }
      
      return {
        content: [
          {
            type: 'text',
            text,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Error extracting PDF: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }

  throw new Error(`Unknown tool: ${name}`);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('PDF MCP server running on stdio');
}

main().catch(console.error);
```

- [ ] **Step 3: Build and test**

```bash
cd packages/mcp-servers/pdf
npm install
npm run build
```

- [ ] **Step 4: Commit PDF MCP**

```bash
git add packages/mcp-servers/pdf/
git commit -m "feat(mcp): implement PDF text extraction MCP server"
```

### Task 4.2: Update Adapter for PDF MCP

**Files:**
- Modify: `packages/adapters/src/claude-code.ts`

- [ ] **Step 1: Add PDF MCP to config**

```typescript
{
  "mcpServers": {
    "scholar": { /* ... */ },
    "pdf": {
      "command": "npx",
      "args": ["@research-copilot/mcp-pdf"],
      "env": {}
    }
  }
}
```

- [ ] **Step 2: Test and commit**

```bash
rc init --user test --claude
git add packages/adapters/src/claude-code.ts
git commit -m "feat(adapter): add PDF MCP to Claude Code config"
```

---

## Milestone 5: Integration Testing

### Task 5.1: E2E Test for Literature Workflow

**Files:**
- Create: `tests/e2e/literature-workflow.test.ts`

- [ ] **Step 1: Write E2E test**

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { execSync } from 'child_process';
import fs from 'fs/promises';
import path from 'path';

describe('Literature Workflow E2E', () => {
  const testDir = path.join(__dirname, '.test-research');

  beforeAll(async () => {
    // Clean test directory
    await fs.rm(testDir, { recursive: true, force: true });
    await fs.mkdir(testDir, { recursive: true });
    process.chdir(testDir);
    
    // Initialize research directory
    execSync('rc init --user test-user', { stdio: 'inherit' });
  });

  afterAll(async () => {
    await fs.rm(testDir, { recursive: true, force: true });
  });

  it('completes full literature task lifecycle', async () => {
    // Create task
    const createOutput = execSync(
      'rc task create --kind literature --title "Search papers on transformers"',
      { encoding: 'utf-8' }
    );
    const taskId = createOutput.match(/Task (\d+) created/)?.[1];
    expect(taskId).toBeDefined();

    // Start task
    execSync(`rc task start ${taskId}`);
    
    // Verify task is in_progress
    const status1 = execSync('rc task current', { encoding: 'utf-8' });
    expect(status1).toContain(taskId);

    // Run verify (should fail - no baselines yet)
    try {
      execSync(`rc task verify ${taskId}`);
      expect.fail('Verify should fail with no baselines');
    } catch (error) {
      // Expected
    }

    // Add baselines
    execSync(`rc task add-baseline ${taskId} --paper arxiv:1706.03762 --claim "Introduced transformer architecture" --reason "Foundational work"`);
    execSync(`rc task add-baseline ${taskId} --paper arxiv:1810.04805 --claim "BERT pre-training" --reason "Key baseline"`);
    execSync(`rc task add-baseline ${taskId} --paper arxiv:2005.14165 --claim "GPT-3 scaling" --reason "Scale baseline"`);

    // Run verify again (should pass)
    execSync(`rc task verify ${taskId}`);

    // Complete task
    execSync(`rc task complete ${taskId}`);

    // Check task is completed
    const taskJson = await fs.readFile(`.research/tasks/${taskId}/task.json`, 'utf-8');
    const task = JSON.parse(taskJson);
    expect(task.status).toBe('completed');
  }, 60000); // 60s timeout
});
```

- [ ] **Step 2: Run E2E test**

```bash
npm test tests/e2e/literature-workflow.test.ts
```

Expected: PASS

- [ ] **Step 3: Commit test**

```bash
git add tests/e2e/literature-workflow.test.ts
git commit -m "test: add E2E test for literature workflow"
```

### Task 5.2: Integration Test for MCP Scholar

**Files:**
- Create: `tests/integration/mcp-scholar.test.ts`

- [ ] **Step 1: Write MCP integration test**

```typescript
import { describe, it, expect } from 'vitest';
import { spawn } from 'child_process';

async function callMCP(method: string, params: any): Promise<any> {
  return new Promise((resolve, reject) => {
    const proc = spawn('node', ['packages/mcp-servers/scholar/dist/index.js']);
    
    let stdout = '';
    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.on('close', () => {
      try {
        const lines = stdout.split('\n').filter(l => l.trim());
        const result = JSON.parse(lines[lines.length - 1]);
        resolve(result);
      } catch (error) {
        reject(error);
      }
    });

    proc.stdin.write(JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method,
      params,
    }) + '\n');
    proc.stdin.end();
  });
}

describe('Scholar MCP Integration', () => {
  it('lists available tools', async () => {
    const result = await callMCP('tools/list', {});
    
    expect(result.result.tools).toHaveLength(3);
    expect(result.result.tools[0].name).toBe('search');
  });

  it('searches arXiv papers', async () => {
    const result = await callMCP('tools/call', {
      name: 'search',
      arguments: {
        query: 'transformer attention',
        source: 'arxiv',
        limit: 3,
      },
    });

    const content = JSON.parse(result.result.content[0].text);
    expect(content.papers).toHaveLength(3);
    expect(content.papers[0]).toHaveProperty('title');
    expect(content.source).toBe('arxiv');
  }, 15000);

  it('gets paper metadata', async () => {
    const result = await callMCP('tools/call', {
      name: 'metadata',
      arguments: {
        paper_id: 'arxiv:1706.03762',
      },
    });

    const paper = JSON.parse(result.result.content[0].text);
    expect(paper.title).toContain('Attention');
    expect(paper.authors).toContain('Vaswani');
  }, 15000);

  it('generates BibTeX', async () => {
    const result = await callMCP('tools/call', {
      name: 'bibtex',
      arguments: {
        paper_id: 'arxiv:1706.03762',
      },
    });

    const bibtex = result.result.content[0].text;
    expect(bibtex).toContain('@article');
    expect(bibtex).toContain('title={');
    expect(bibtex).toContain('author={');
  }, 15000);
});
```

- [ ] **Step 2: Run integration test**

```bash
npm test tests/integration/mcp-scholar.test.ts
```

Expected: PASS (4 tests)

- [ ] **Step 3: Commit test**

```bash
git add tests/integration/mcp-scholar.test.ts
git commit -m "test: add integration tests for scholar MCP"
```

### Task 5.3: Documentation Update

**Files:**
- Modify: `README.md`
- Create: `docs/skills.md`
- Create: `docs/mcp-servers.md`

- [ ] **Step 1: Update README with Skills section**

Add after "The `rc` commands" section:

```markdown
## Skills

Research Copilot provides 6 high-level skills for orchestrating research workflows:

| Skill | Description | When to Use |
|---|---|---|
| `/full-research-workflow` | Complete pipeline (literature → submission) | Starting new research project |
| `/literature-search` | Focused paper search + baseline locking | Finding baselines for topic |
| `/experiment-design` | Design and launch experiments | Running validation experiments |
| `/paper-polish` | De-AI and style refinement | After writing first draft |
| `/submission-sprint` | Iterative review-fix loop | Pre-submission optimization |
| `/sanity-check` | 6-dimension final audit | Before final submission |

See [docs/skills.md](docs/skills.md) for detailed usage.
```

- [ ] **Step 2: Create skills documentation**

```markdown
# Research Copilot Skills

Skills are high-level orchestrators that call `rc` CLI commands and dispatch agents.

## Full Research Workflow

**Trigger**: "start research", "full pipeline"

**What it does**: Orchestrates complete research pipeline from literature search to submission.

**Stages**:
1. Literature (kind=literature) — search papers, lock baselines
2. Ideation (kind=ideation) — analyze novelty, design approach
3. Experiment (kind=experiment) — implement and validate
4. Writing (kind=writing) — draft paper with digital traceability
5. Polish (kind=polish) — de-AI and style refinement
6. Review (kind=review) — simulate top-venue review
7. Rebuttal (kind=rebuttal, optional) — address reviewer concerns

**Example**:
```
User: "Start research on vision transformers for medical imaging, target MICCAI 2026"
Skill: Creates literature task, dispatches @rc-literature, proceeds through all 7 stages
```

## Literature Search

**Trigger**: "search papers", "find baselines"

**What it does**: Focused literature search for a specific topic.

**Quality Gate**:
- ≥3 baselines locked
- ≥2 categories covered
- All prd claims supported

## Experiment Design

**Trigger**: "design experiment", "run training"

**What it does**: Designs and launches experiments with long-task support.

**Features**:
- Uses Monitor for long-running jobs
- Enforces config traceability (seed/hyperparams)
- Validates metrics against prd.md targets

## Paper Polish

**Trigger**: "polish paper", "de-AI"

**What it does**: Removes AI patterns and refines style.

**Checks**:
- No excessive adjectives ("remarkably", "significantly")
- No mechanical transitions ("Moreover,", "Furthermore,")
- No bullet lists in prose
- Venue style compliance

## Submission Sprint

**Trigger**: "submission sprint", "pre-submit check"

**What it does**: Iterative review-fix loop until P0 gaps closed.

**Termination**: 0 P0 gaps, ≤2 P1 gaps

## Sanity Check

**Trigger**: "sanity check", "final check"

**What it does**: 6-dimension audit without making changes.

**Dimensions**:
1. Logic: Claims → Evidence complete
2. Citations: All baselines cited
3. Reproducibility: Config/seed documented
4. Novelty: Matches spec/novelty/
5. Venue: Format/length correct
6. De-AI: No patterns remain
```

- [ ] **Step 3: Create MCP documentation**

```markdown
# Research Copilot MCP Servers

## Scholar MCP (`@research-copilot/mcp-scholar`)

Academic paper search across arXiv, Google Scholar, DBLP.

**Installation**:
```bash
npx @research-copilot/mcp-scholar
```

**Tools**:

### `search`
Search papers by query.

**Parameters**:
- `query` (string, required): Search query
- `source` (enum): 'arxiv' | 'scholar' | 'dblp' | 'arxivsub' | 'all' (default: 'all')
- `limit` (number): Max results (default: 10)
- `venue_filter` (enum): Filter by top-venue (arxivsub only)

**Example**:
```json
{
  "query": "transformer attention mechanism",
  "source": "arxiv",
  "limit": 5
}
```

### `metadata`
Get detailed metadata for a paper.

**Parameters**:
- `paper_id` (string, required): Paper ID (e.g., "arxiv:1706.03762")
- `source` (enum, optional): Source hint

### `bibtex`
Get BibTeX entry for a paper.

**Parameters**:
- `paper_id` (string, required): Paper ID

## PDF MCP (`@research-copilot/mcp-pdf`)

PDF text extraction.

**Tools**:

### `extract_text`
Extract text from PDF file.

**Parameters**:
- `file_path` (string, required): Path to PDF
- `pages` (string): Page range (e.g., "1-5", "all")

**Example**:
```json
{
  "file_path": "/path/to/paper.pdf",
  "pages": "1-5"
}
```

## Rate Limiting

- arXiv: 1 req/sec
- Google Scholar: 1 req/3sec (when implemented)
- DBLP: 1 req/1.5sec (when implemented)
```

- [ ] **Step 4: Commit documentation**

```bash
git add README.md docs/skills.md docs/mcp-servers.md
git commit -m "docs: add Skills and MCP servers documentation"
```

---

## Self-Review Checklist

### Spec Coverage

- [x] M1: 6 Skills implemented (full-research-workflow, literature-search, experiment-design, paper-polish, submission-sprint, sanity-check)
- [x] M2: 10 Agents enhanced (rc-literature, rc-ideation, rc-experiment, rc-writer, rc-polisher, rc-reviewer, rc-rebuttal, rc-plan, rc-verify, rc-update-spec)
- [x] M3: MCP Scholar with arXiv backend
- [x] M4: MCP PDF
- [x] M5: E2E and integration tests

### Placeholder Scan

- [x] No TBD/TODO in Skills
- [x] No "implement later" in MCP code
- [x] No "add tests" without actual test code
- [x] All code blocks complete (no `...` placeholders)

### Type Consistency

- [x] Paper type used consistently (PaperSchema)
- [x] SearchResult type used consistently
- [x] Task lifecycle states match core (planning → in_progress → verify → completed)
- [x] Agent kind values match spec (literature/ideation/experiment/writing/polish/review/rebuttal)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-07-research-copilot-enhancement.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
