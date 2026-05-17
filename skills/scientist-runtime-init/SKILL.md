---
name: scientist-runtime-init
description: "Use when the user asks to '检查环境', '能不能跑 AI Scientist', 'runtime check', '初始化 AI Scientist 环境', or wants the ai-scientist MCP to validate Python / CUDA / LaTeX / poppler / runtime prerequisites. Routes through the `ai-scientist` MCP `validate_runtime`. Do NOT use as a substitute for actually running an experiment."
version: 0.2.0
---

# scientist-runtime-init

Validate the scientist-support AI Scientist runtime preconditions in the current workspace via the `ai-scientist` MCP.

## Goal

Confirm the following before launching any long experiment:

- Runtime root directory exists
- Python is available
- `pdflatex`, `bibtex`, `pdftotext`, `chktex` are available
- `torch.cuda.is_available()` is true
- The current platform is suitable for local experiments and LaTeX compilation

## Preferred method

For a full check, use the `ai-scientist` MCP `validate_runtime` tool.

This skill organizes the check steps and the output format; it does NOT depend on any in-skill runner or alternative script entry point.

If the MCP is unavailable, fall back to terminal checks on the same conditions, keeping the same output structure.

## Output requirements

Summarize in three columns: Ready / Missing / Risk:

- **Ready**: satisfied items
- **Missing**: missing items
- **Risk**: e.g. Windows platform, no GPU, no LaTeX

End with a next-step recommendation:

- Can continue with ideation
- Can continue with local experiments, plotting support, or paper compilation
- Must fix the environment first

## Forbidden

- NEVER call any in-skill runner or script entry point.
- NEVER treat API-key or model-SDK availability as a runtime-init check item.
