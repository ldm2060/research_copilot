---
name: scientist-experiment-runner
description: "Use when the user asks to '开始实验', '推进实验', 'run experiment', 'advance the experiment', 'turn an idea into experiment', or wants an idea JSON converted into concrete code edits and runs directly in Copilot. Copilot-native — Copilot writes the changes and reads the results in-session; the terminal only executes non-model commands. Do NOT use for plotting (scientist-plotting) or writeup (scientist-writeup)."
version: 0.2.0
---

# scientist-experiment-runner

Convert AI Scientist's "advance the experiment" into a Copilot-native workflow: Copilot reads ideas, edits code, runs experiments, and summarizes results. NEVER call any workspace-custom model pipeline.

## Execution model

This is a **Copilot-native model task**. Copilot makes research decisions in-session; the terminal runs only non-model commands.

## Workflow

1. Read the ideas JSON; lock the `idea_idx` or specific idea in use.
2. Identify the code surface, config surface, and run commands.
3. Make the minimum necessary code or config change.
4. Run experiments / tests / evaluation via the terminal.
5. Read result files, logs, and metrics.
6. Continue analysis and the next-round decision in-session.

## Long-run guidance — when an experiment exceeds the longest Bash timeout (10 min)

**NEVER** poll with repeated `Bash(timeout=600000)` calls to "just wait." Each call burns 10 minutes of context and forces a fresh decision turn on identical state.

Pick the tool by estimated duration:

| Estimated time | Tool | Why |
|---|---|---|
| < 10 min | `Bash` synchronous | Fits in one call |
| 10 min – 2 h, command exits when done | `Bash(run_in_background=true)` | Harness auto-notifies on exit; zero polling |
| Hours, you need progress events | `Monitor` with `tail -f log \| grep -E --line-buffered "elapsed_steps=\|Traceback\|Error\|FAILED\|Killed\|OOM"` | One notification per event; ends when the grep filter exits |
| Hours, no event stream | `ScheduleWakeup(delaySeconds=N, prompt="continue checking experiment X")` | Re-enter cold after delay; cheap |
| Recurring polls (e.g. every 30 min) | `CronCreate` | Standard cron, in-memory |

## Verification before declaring completion

**Before claiming the experiment finished successfully, you MUST produce one of:**
- the exact metric value with the exact log line it came from,
- the file path of the produced artifact + a confirming `ls` / `Read` output,
- or an explicit "could not verify — here is what I have so far."

A turn that ends with "the experiment finished successfully" without one of the above is a failure mode. A "background command exited 0" notification alone is not verification — the script could have crashed silently or produced empty logs.

## Input

- `load_ideas` or ideas-JSON path
- `idea_idx` or target idea name
- Relevant code directories, training scripts, configs, run commands
- Expected output directory or existing experiment directory

## Output

- Code diff
- Commands actually run
- Key metrics, log summary, artifact paths
- Suggested next round

## Operating principles

1. Copilot owns experiment strategy and result interpretation; the terminal owns code execution.
2. Advance one minimum experimental slice per round; get it running before expanding.
3. If an experiment directory already exists, use `inspect_experiment` (or read logs directly) before blindly editing.
4. If the user only wants plotting / writeup / review, do NOT auto-expand into the full experiment chain.

## Forbidden

- NEVER call any workspace-custom model pipeline.
- NEVER initiate model calls from workspace code on your own.

## Risk boundaries

- If runtime conditions are insufficient, prepare the plan and code only; never pretend the experiment ran.
- If the experiment is very expensive, confirm the run budget and expected artifacts with the user first.
