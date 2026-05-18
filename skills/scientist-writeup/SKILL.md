---
name: scientist-writeup
description: "Use when the user asks to '开始写论文', '生成 PDF', '整理成论文', or wants LaTeX / Markdown drafted directly in Copilot from experiment artifacts. Triggers on: 'write the paper', 'generate PDF', 'compile to paper'. Copilot-native — no workspace writeup script call. Do NOT use for review (scientist-review) or plotting (scientist-plotting)."
version: 0.2.0
---

# scientist-writeup

Generate or edit LaTeX / Markdown paper content directly from an existing experiment directory. Model output is produced by Copilot in-session; NEVER call workspace-custom model scripts.

## Execution model

This is a **Copilot-native model task**. Copilot reads results, writes content, and edits LaTeX files; the terminal handles non-model commands like `pdflatex`.

## Workflow

1. Read the experiment directory, summary files, figures, and logs.
2. Identify the user-supplied `latex/template.tex` or the existing draft.
3. Write or edit paper content directly in the editor.
4. On user request, run `pdflatex` / `bibtex` for a compilation check.
5. Report the produced manuscript path, compilation result, and remaining gaps.

## Verification before declaring completion

**Before claiming the paper is drafted, you MUST produce one of:**
- the file path + a short verbatim quote of new content,
- a `Read` confirmation that the new content is in the file,
- a successful `pdflatex` exit and the produced PDF path,
- or an explicit "drafted but could not verify — here is what I have so far."

A turn that ends with "the paper is drafted" without one of the above is a failure mode.

## Input

- `folder`: experiment directory
- `folder/latex/template.tex`: user-provided template entry
- Figures, summarized results, citation info, and target-layout requirements

## Output

- Edited LaTeX / Markdown files
- Compiled PDF path (if compilation was run)
- List of unmet prerequisites

## Operating principles

1. Confirm the template and dependency files exist before writing.
2. Write from real experimental results; NEVER fabricate conclusions or citations.
3. When the user only wants a text draft, do not force a PDF compile.

## Forbidden

- NEVER call any workspace-custom writeup model pipeline.
- NEVER use custom model calls in workspace code to generate paper text.

## Deliverable requirements

- Name which paper files were edited.
- If compilation fails, return the real LaTeX error summary.
- If conclusions still lack experimental support, name the missing results explicitly.
