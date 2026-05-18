---
name: scientist-ideation
description: "Use when the user has a workshop / topic Markdown and wants it turned into an AI-Scientist-format ideas JSON, generated directly in Copilot. Triggers on: '生成 ideas', 'topic 变成想法', 'AI Scientist 出点子', 'generate ideas from topic'. Copilot-native — no workspace ideation script call."
version: 0.2.0
---

# scientist-ideation

Convert a workshop / topic Markdown into an AI-Scientist-compatible ideas JSON. The model output MUST be produced by Copilot in-session.

## Execution model

This is a **Copilot-native model task**. Copilot reads the topic, brainstorms ideas, generates the JSON, and writes to a workspace file when the user requests it.

## Workflow

1. Read the user-supplied workshop / topic Markdown.
2. If needed, check an existing ideas JSON to avoid duplicate directions.
3. Generate candidate ideas in-session and organize them in the AI-Scientist schema.
4. If the user asks for persistence, create or update the ideas JSON file directly.

## JSON schema

- `Name`
- `Title`
- `Short Hypothesis`
- `Related Work`
- `Abstract`
- `Experiments`
- `Risk Factors and Limitations`

## Input

- `workshop_file` or topic Markdown path
- Existing ideas JSON (if any)
- Directional / dataset / resource constraints the user wants preserved

## Output

- AI-Scientist-style ideas JSON
- Written directly to a workspace file if requested
- Explicit output path, idea count, and a list of duplicates filtered out

## Forbidden

- NEVER call any workspace-custom ideation pipeline.
- NEVER call a model SDK from workspace code to generate ideas.

## Failure handling

- If the topic file's structure is too thin, surface the gap and ask for supplementation first.
- If the user asks for persistence but the schema is incomplete, fill it in-session before writing.
