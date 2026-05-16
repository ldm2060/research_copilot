---
name: scientist-review
description: "Use when the user asks to '审一下这篇 PDF', '自动审稿', '给我 review', or wants a manuscript / PDF reviewed in Copilot with structured feedback. Triggers on: 'review this manuscript', 'auto-review'. Copilot-native — no workspace review script call."
version: 0.2.0
---

# scientist-review

Text-level Copilot-native review of a paper or PDF. Model judgment and review output are produced by Copilot in-session; NEVER call a workspace-custom model script.

## Execution model

This is a **Copilot-native model task**. If only a PDF is supplied, extract text first, then have Copilot produce the review directly.

## Workflow

1. Acquire the paper text: prefer existing Markdown / LaTeX / TXT; fall back to PDF-text extraction only if necessary.
2. Produce the review, scoring, and risk assessment directly in-session.
3. If the user requests structured output, generate JSON or write to a file.

## Input

- `pdf_path`, LaTeX source, or already-extracted text
- Reviewer perspective and scoring dimensions the user wants applied

## Output

- Review notes
- Optional structured JSON review result on request
- Explicit Strengths / Main Issues / Score / Risks

## Forbidden

- NEVER call any workspace-custom review pipeline.
- NEVER use custom model calls in workspace scripts for reviewing.

## Deliverable requirements

- Default to a "Strengths / Main Issues / Score / Risks" summary.
- If only a PDF is provided and text extraction fails, name the blocker explicitly.
