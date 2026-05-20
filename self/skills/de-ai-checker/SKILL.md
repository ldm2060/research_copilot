---
name: de-ai-checker
description: "Validation skill for de-AI quality checking. Use AFTER polishing to verify that AI patterns have been removed and text reads naturally. Triggers on: 'check de-AI quality', 'verify humanization', 'validate polish', 'de-AI checker', '检查去AI效果'. This is a validation-gate compatible wrapper around paper-deai."
version: 1.0.0
---

# De-AI Checker — Post-polish validation

Run **after** polishing is complete to verify that AI patterns have been successfully removed and the text reads naturally.

## When this skill fires

Fire automatically when:
- The polisher agent reaches the VERIFYING state and needs validation-gate clearance
- User explicitly requests de-AI quality verification
- After any `paper-deai` rewriting pass to confirm quality

Also fires on user request: "检查去AI效果" / "check de-AI quality" / "verify the polish worked"

## Purpose

This skill serves as a **validation-gate compatible checker** that:
1. Verifies AI patterns have been removed
2. Confirms text naturalness and academic register
3. Provides pass/fail validation for capability gates
4. Delegates actual rewriting to `paper-deai` if issues are found

## Procedure

### Step 1 — Read the polished text

Load the text that was just polished. This should be LaTeX content from the target sections.

### Step 2 — Run AI pattern detection

Check for common AI fingerprints:

| Pattern Category | What to check |
|---|---|
| **Over-used vocabulary** | Scan for the AI-over-used word list: leverage, delve, tapestry, endeavor, underscore, etc. (full list in `paper-deai` skill) |
| **Mechanical connectives** | Look for: "First and foremost", "It is worth noting that", "Moreover", "Furthermore" at sentence starts |
| **List format** | Check for `\item` usage where prose would be more natural |
| **Excessive dashes** | Count em-dashes (`---` and `—`) — more than 1 per paragraph is suspicious |
| **Tense errors** | Verify background/prior-art uses present perfect ("have achieved") not simple present |
| **Emphasis abuse** | Check for bold/italics used for emphasis rather than structure |

### Step 3 — Score and decide

Calculate a naturalness score based on:
- AI vocabulary count (each instance: -10 points)
- Mechanical connectives (each instance: -5 points)
- List format in prose sections (each `\item`: -8 points)
- Excessive dashes (each beyond 1/paragraph: -3 points)
- Tense errors (each instance: -7 points)

**Pass threshold**: Score ≥ 85/100

### Step 4 — Output validation report

```markdown
## De-AI validation report — <section>
- Date: <YYYY-MM-DD>
- Text reviewed: <file:line range>
- Naturalness score: <score>/100
- Status: [PASS] or [FAIL]
- Issues found:
  - AI vocabulary: <count> instances → <list with line numbers>
  - Mechanical connectives: <count> instances → <list>
  - List format: <count> items → <list>
  - Excessive dashes: <count> → <list>
  - Tense errors: <count> → <list>
- Recommendation: <"Validation passed" or "Re-run paper-deai on sections: <list>">
```

### Step 5 — Auto-fix if requested

If the validation fails and the user/agent requests auto-fix:
1. Call the `paper-deai` skill with the problematic sections
2. Re-run this validation checker
3. Report final status

## Output format

- **Part 1 [Validation Report]**: The structured report above
- **Part 2 [Gate Status]**: One of:
  - `[VALIDATION_GATE_PASS]` — text is natural, no AI patterns detected
  - `[VALIDATION_GATE_FAIL]` — AI patterns remain, re-polish required

## Integration with capability gates

This skill satisfies the `validation-gate` requirement because:
- Name matches `*-checker` pattern
- Provides explicit pass/fail status
- Can be called via `Skill(skill='de-ai-checker')`

## Hard constraints

- **Post-polish only** — if no polished text exists, exit and recommend running `paper-deai` first
- **Read before checking** — every issue must cite file:line, not "in general"
- **Honest scoring** — do not inflate scores to declare victory
- **Delegate rewriting** — this skill validates; `paper-deai` rewrites
- **One pass per invocation** — do not loop; if re-check is needed, user/agent re-invokes
- **Explicit gate status** — always output `[VALIDATION_GATE_PASS]` or `[VALIDATION_GATE_FAIL]`

## Relationship to paper-deai

- `paper-deai`: **Executor** — rewrites text to remove AI patterns
- `de-ai-checker`: **Validator** — checks quality and provides gate clearance

Use `paper-deai` for rewriting, use `de-ai-checker` for validation.
