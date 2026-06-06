---
name: experiment-design
description: Designs and launches experiments. Handles long-running tasks via Monitor. Use for experiment tasks.
triggers:
  - "design experiment"
  - "run training"
  - "launch experiment"
  - "run experiments"
  - "execute experiments"
---

# Experiment Design

Orchestrate experiment design and execution: create task → dispatch @rc-experiment → monitor long-running jobs → verify results.

## When to Use

Use this skill when:
- User asks to "design experiment for X"
- User wants to "run training" or "launch experiment"
- User needs to "execute experiments" for research
- Standalone experiment execution (NOT part of full pipeline)

Do NOT use when:
- Part of full-research-workflow (that handles experiments internally)
- User only wants to analyze existing results (use data-analysis skill)

## Task-First Protocol

Before starting, check if task exists:

```powershell
# Check for existing experiment task
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\experiment-design.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    Write-Host "Found existing task: $($task.experiment_name)"
} else {
    Write-Host "No existing task. Will create one."
}
```

Create task if needed:

```powershell
# Create experiment design task
rc task create --type experiment --name "user experiment name" --output .rc/tasks/experiment-design.json
```

## Auto-Context Loading

Read task context and relevant specs before orchestration:

```powershell
# Load task context
$taskFile = "C:\PythonProject\research_copilot\.rc\tasks\experiment-design.json"
if (Test-Path $taskFile) {
    $task = Get-Content $taskFile | ConvertFrom-Json
    
    Write-Host "Experiment Name: $($task.experiment_name)"
    Write-Host "Target Metrics: $($task.target_metrics)"
    Write-Host "Baseline Comparisons: $($task.baseline_count)"
    
    # Load PRD if referenced
    if ($task.prd_file -and (Test-Path $task.prd_file)) {
        $prd = Get-Content $task.prd_file -Raw
        Write-Host "PRD loaded: $($task.prd_file)"
        
        # Extract metrics requirements from PRD
        $metricsMatch = [regex]::Match($prd, '## Target Metrics\s+([\s\S]+?)(?=\n##|\z)')
        if ($metricsMatch.Success) {
            Write-Host "Target metrics from PRD:"
            Write-Host $metricsMatch.Groups[1].Value
        }
    }
    
    # Load methodology specs if available
    $methodFile = "C:\PythonProject\research_copilot\.rc\methodology.md"
    if (Test-Path $methodFile) {
        $method = Get-Content $methodFile -Raw
        Write-Host "Methodology loaded: $methodFile"
    }
}
```

## Orchestration Logic

Execute experiment via agent dispatch with long-task support:

```powershell
# Start task
rc task start experiment-design

# Dispatch to experiment agent
Write-Host "Dispatching to @rc-experiment agent..."

# Agent will:
# 1. Parse experiment requirements from PRD
# 2. Design experiment configuration (hyperparameters, seeds, splits)
# 3. Set up experiment directory structure
# 4. Launch training jobs (using Monitor for long-running tasks)
# 5. Collect metrics and results
# 6. Compare against baselines
# 7. Generate result tables and figures
# 8. Save all artifacts to .rc/experiments/

# Check status (agent runs autonomously)
$status = rc task status experiment-design
Write-Host "Task status: $status"
```

## Long-Task Handling

The experiment executor uses `Bash(run_in_background=true)` + `Monitor` for training jobs:

```powershell
# Example: Monitor long-running training job
# The agent will set this up internally, shown here for reference

# Start training in background
$jobId = Start-Job -ScriptBlock {
    python train.py --config config.yaml --output experiments/run_001/
}

# Monitor training progress via log file
Monitor -description "Training experiment run_001" `
        -persistent $true `
        -command @"
tail -f experiments/run_001/train.log | grep --line-buffered 'epoch=\|loss=\|accuracy=\|FINISHED\|ERROR\|FAILED'
"@

# Agent continues other work while training runs
# Will be notified when training completes or errors occur
```

Key points for long-task handling:
- Training jobs run in background using `run_in_background=true`
- Monitor streams progress updates (metrics, errors) without blocking
- Agent can launch multiple experiments in parallel
- Each experiment logs to separate directory for isolation
- Failed experiments recorded with error details for debugging

## Verification and Quality Gates

Verify results before marking complete:

```powershell
# Verify experiment outputs
$expDir = "C:\PythonProject\research_copilot\.rc\experiments"

# Check experiment config
$configFile = Join-Path $expDir "config.yaml"
if (Test-Path $configFile) {
    $config = Get-Content $configFile -Raw | ConvertFrom-Yaml
    Write-Host "Config loaded: seed=$($config.seed), epochs=$($config.epochs)"
} else {
    Write-Host "WARNING: No config file found"
}

# Check results file
$resultsFile = Join-Path $expDir "results.json"
if (Test-Path $resultsFile) {
    $results = Get-Content $resultsFile | ConvertFrom-Json
    Write-Host "Found results for $($results.runs.Count) runs"
    
    # Verify all required metrics present
    $requiredMetrics = @('accuracy', 'f1_score', 'precision', 'recall')
    foreach ($metric in $requiredMetrics) {
        if (-not $results.metrics.$metric) {
            Write-Host "WARNING: Missing metric: $metric"
        }
    }
} else {
    Write-Host "WARNING: No results file found"
}

# Check baseline comparisons
$comparisonFile = Join-Path $expDir "baseline_comparison.json"
if (Test-Path $comparisonFile) {
    $comparison = Get-Content $comparisonFile | ConvertFrom-Json
    Write-Host "Compared against $($comparison.baselines.Count) baselines"
} else {
    Write-Host "WARNING: No baseline comparison found"
}

# Check reproducibility artifacts
$artifactsDir = Join-Path $expDir "artifacts"
if (Test-Path $artifactsDir) {
    $artifacts = Get-ChildItem $artifactsDir -Recurse
    Write-Host "Saved $($artifacts.Count) reproducibility artifacts"
} else {
    Write-Host "WARNING: No artifacts directory"
}
```

Complete task if quality gates pass:

```powershell
# Mark task complete
rc task complete experiment-design
```

## Quality Gates

Verify before marking complete:

```powershell
# Quality gate checks
$passed = $true

# Gate 1: All metrics from PRD achieved
$resultsFile = "C:\PythonProject\research_copilot\.rc\experiments\results.json"
if (Test-Path $resultsFile) {
    $results = Get-Content $resultsFile | ConvertFrom-Json
    $prdFile = "C:\PythonProject\research_copilot\.rc\prd.md"
    
    if (Test-Path $prdFile) {
        $prd = Get-Content $prdFile -Raw
        $metricsMatch = [regex]::Matches($prd, '(\w+):\s*≥\s*([\d.]+)')
        
        foreach ($match in $metricsMatch) {
            $metricName = $match.Groups[1].Value
            $targetValue = [double]$match.Groups[2].Value
            $actualValue = $results.metrics.$metricName
            
            if ($actualValue -lt $targetValue) {
                Write-Host "FAIL: $metricName = $actualValue < $targetValue (target)"
                $passed = $false
            }
        }
    }
} else {
    Write-Host "FAIL: No results file"
    $passed = $false
}

# Gate 2: Results logged to artifacts/results/
$artifactsDir = "C:\PythonProject\research_copilot\.rc\experiments\artifacts\results"
if (Test-Path $artifactsDir) {
    $resultFiles = Get-ChildItem $artifactsDir -Filter "*.json"
    if ($resultFiles.Count -eq 0) {
        Write-Host "FAIL: No result files in artifacts/results/"
        $passed = $false
    }
} else {
    Write-Host "FAIL: artifacts/results/ directory missing"
    $passed = $false
}

# Gate 3: Config and seed recorded for reproducibility
$configFile = "C:\PythonProject\research_copilot\.rc\experiments\config.yaml"
if (Test-Path $configFile) {
    $config = Get-Content $configFile -Raw
    if ($config -notmatch 'seed:\s*\d+') {
        Write-Host "FAIL: No seed recorded in config"
        $passed = $false
    }
} else {
    Write-Host "FAIL: No config file for reproducibility"
    $passed = $false
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
# Experiment Design Report

**Experiment**: {experiment_name}
**Date**: {date}
**Runs Completed**: {run_count}
**Status**: {status}

## Configuration

- **Seed**: {seed}
- **Epochs**: {epochs}
- **Batch Size**: {batch_size}
- **Learning Rate**: {learning_rate}

## Results

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Accuracy | {accuracy} | {target_accuracy} | {✓/✗} |
| F1 Score | {f1_score} | {target_f1} | {✓/✗} |
| Precision | {precision} | {target_precision} | {✓/✗} |
| Recall | {recall} | {target_recall} | {✓/✗} |

## Baseline Comparisons

| Baseline | Metric | Their Score | Our Score | Improvement |
|----------|--------|-------------|-----------|-------------|
| {name} | {metric} | {baseline_score} | {our_score} | {delta}% |

## Reproducibility

All artifacts saved to: `.rc/experiments/artifacts/`

- **Config**: `config.yaml` (seed={seed})
- **Checkpoints**: `checkpoints/run_{id}/`
- **Logs**: `logs/train.log`
- **Results**: `artifacts/results/results_{timestamp}.json`

## Next Steps

- [ ] Verify results meet all PRD requirements
- [ ] Generate figures for paper
- [ ] Update paper draft with results
- [ ] Archive experiment for future reference
```

## Example Usage

```
User: "Design and run experiments for the sentiment analysis model"

Skill: [Reads PRD, creates task, dispatches @rc-experiment]
Skill: [Agent launches training via Monitor, continues other work]
Skill: [Receives notification when training completes]
Skill: [Verifies metrics, generates report]
Skill: "Experiment completed. Achieved accuracy=0.94 (target: 0.90). Results saved to .rc/experiments/."
```
