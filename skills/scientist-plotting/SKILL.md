---
name: scientist-plotting
description: "Use when the user asks to '聚合作图', '补图表', '整理实验图', or wants experiment outputs converted into plots + plotting scripts directly in Copilot. Triggers on: 'aggregate plots', 'make figures from results'. Copilot-native — Copilot designs the figure and edits the script; the terminal only runs the Python plotting code. Do NOT use without existing experiment outputs."
version: 0.2.0
---

# scientist-plotting

Generate plots and plotting scripts from an existing experiment directory. Model judgment and figure design are done by Copilot in-session.

## Execution model

This is a **Copilot-native model task**. Copilot reads results, decides figure structure, writes / edits plotting code; the terminal only runs pure-Python plotting scripts.

## Workflow

1. Read the experiment directory's summary JSON, logs, CSVs, NPY files, or existing plots.
2. Decide which metrics and comparisons to display.
3. Create or edit matplotlib / seaborn / pandas plotting code directly.
4. Run the plotting script and inspect the output.
5. If the figure is unclear, iterate.

## Input

- `folder`: experiment directory
- Result file paths and formats
- Figure conventions or paper-layout constraints the user wants preserved

## Output

- Plotting script or edits to an existing script
- Output figure paths
- Figure design rationale and the key visual conclusions

## Operating principles

- Only invoke this skill when the experiment outputs already exist.
- If result files are incomplete, flag the gap; NEVER fabricate plots.

## Forbidden

- NEVER call any workspace-custom plotting model pipeline.
- NEVER use custom model calls in workspace code to "auto-plot."

## Deliverable requirements

- Report figure paths.
- Name the source result files used.
- If a figure failed to render, return the real error and a suggested next step.
