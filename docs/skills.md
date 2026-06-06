# Skills

Research Copilot provides 6 high-level skills for orchestrating multi-step research workflows. Each skill is a composite agent that drives the `rc` task system underneath.

## Overview

| Skill | Steps | Typical Duration | Output |
|---|---|---|---|
| `/full-research-workflow` | 5 phases (literature → submission) | Weeks-months | Camera-ready paper |
| `/literature-search` | Search → filter → lock baselines | 1-2 hours | Locked baseline set |
| `/experiment-design` | Design → validate → launch | 2-4 hours | Running experiments |
| `/paper-polish` | De-AI → style → format | 1-2 hours | Publication-ready draft |
| `/submission-sprint` | Iterative review-fix | 4-8 hours | Submission-ready package |
| `/sanity-check` | 6-dimension audit | 30 minutes | Pass/fail report |

## Skill Details

### `/full-research-workflow`

**Purpose**: End-to-end research pipeline from idea to submission.

**When to use**: Starting a new research project from scratch.

**What it does**:
1. **Literature Phase**: Search papers, lock 3+ baselines (creates `literature` task)
2. **Ideation Phase**: Generate hypotheses, design experiments (creates `ideation` task)
3. **Experiment Phase**: Run validation experiments, collect results (creates `experiment` task)
4. **Writing Phase**: Draft paper from experiments (creates `writing` task)
5. **Submission Phase**: Polish and prepare for submission (creates `polish` + `review` tasks)

**Example**:
```bash
# In Claude Code chat
/full-research-workflow "Efficient transformers for long sequences"
```

**Output**: Full task tree in `.research/tasks/`, final camera-ready paper in `paper.pdf`.

---

### `/literature-search`

**Purpose**: Focused paper search with baseline locking.

**When to use**: You have a research topic and need to find key prior work.

**What it does**:
1. Search arXiv, Semantic Scholar, and Google Scholar
2. Filter papers by relevance and citations
3. Lock 3+ baselines with claims and reasoning
4. Create `literature` task and move to `completed`

**Example**:
```bash
/literature-search "neural architecture search for vision transformers"
```

**Output**: `.research/tasks/<id>/baselines.json` with locked papers.

---

### `/experiment-design`

**Purpose**: Design and launch experiments from hypotheses.

**When to use**: You have a hypothesis and need to validate it.

**What it does**:
1. Generate experiment plan from hypothesis
2. Create experiment scripts (training, evaluation)
3. Set up tracking (W&B, TensorBoard)
4. Launch experiments and monitor progress

**Example**:
```bash
/experiment-design "Test if sparse attention improves efficiency on long sequences"
```

**Output**: Experiment scripts in `experiments/`, running jobs tracked in task metadata.

---

### `/paper-polish`

**Purpose**: De-AI and style refinement for academic writing.

**When to use**: After writing first draft, before submission.

**What it does**:
1. **De-AI pass**: Remove AI-generated patterns (e.g., "delve", "leverage", "harness")
2. **Style pass**: Apply venue-specific formatting (IEEE, ACM, NeurIPS)
3. **Consistency pass**: Fix citations, notation, figure references
4. **Grammar pass**: Fix typos, awkward phrasing

**Example**:
```bash
/paper-polish "paper.tex" --venue neurips
```

**Output**: Polished `paper.tex` with tracked changes in `.research/polish-log.md`.

---

### `/submission-sprint`

**Purpose**: Iterative review-fix loop before submission.

**When to use**: Days before submission deadline.

**What it does**:
1. Run `/sanity-check` to find issues
2. Create fix tasks for each issue
3. Execute fixes in parallel
4. Re-run sanity check until all pass
5. Generate submission checklist

**Example**:
```bash
/submission-sprint "paper.tex" --venue icml --deadline "2026-06-15"
```

**Output**: Submission-ready package (paper, code, data) with checklist in `.research/submission-checklist.md`.

---

### `/sanity-check`

**Purpose**: 6-dimension final audit before submission.

**When to use**: Right before final submission.

**What it does**: Checks 6 dimensions with pass/fail for each:

1. **Formatting**: Venue template compliance (margins, fonts, page limit)
2. **Citations**: All references cited, BibTeX complete, no broken links
3. **Figures**: All figures referenced, captions complete, resolution adequate
4. **Math**: Notation consistent, equations numbered, symbols defined
5. **Code**: Reproducibility (README, dependencies, data links)
6. **Ethics**: Checklist complete (if required by venue)

**Example**:
```bash
/sanity-check "paper.pdf" --venue neurips
```

**Output**: Pass/fail report in `.research/sanity-check-report.md` with actionable fixes.

**Exit codes**:
- `0`: All checks pass
- `1`: 1+ checks fail (blocks submission)

---

## Usage Patterns

### Pattern 1: Full Workflow (New Project)
```bash
/full-research-workflow "Efficient transformers for long sequences"
# Wait for completion (~weeks)
# Output: camera-ready paper + code package
```

### Pattern 2: Literature-First (Existing Idea)
```bash
/literature-search "neural architecture search for vision"
# Review locked baselines in .research/tasks/<id>/baselines.json
# Continue with /experiment-design or /full-research-workflow
```

### Pattern 3: Pre-Submission Sprint
```bash
/paper-polish "paper.tex" --venue icml
/submission-sprint "paper.tex" --venue icml --deadline "2026-06-15"
/sanity-check "paper.pdf" --venue icml
# Fix any failures, re-run /sanity-check until pass
```

### Pattern 4: Standalone Experiments
```bash
/experiment-design "Test sparse attention on long sequences"
# Monitor experiments in W&B dashboard
# Continue with /full-research-workflow for writing phase
```

---

## Skill Implementation

Skills are implemented as autonomous agents in `.claude/agents/` (for Claude Code) or equivalent platform directories. Each skill:

1. **Drives the task system**: Creates and transitions `rc` tasks underneath
2. **Is resumable**: Can be interrupted and resumed (state stored in `.research/`)
3. **Is idempotent**: Re-running a completed skill is safe (checks current state first)
4. **Produces structured output**: Results stored in `.research/` for downstream consumption

See [docs/dev/skills-development.md](dev/skills-development.md) for implementation guide.

---

## Related Documentation

- [Command Reference](usage/commands.md) — Low-level `rc` commands used by skills
- [Workflow Guide](usage/workflow.md) — Manual workflow patterns without skills
- [Architecture](dev/architecture.md) — How skills integrate with the core engine
