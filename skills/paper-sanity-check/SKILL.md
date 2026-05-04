---
name: paper-sanity-check
description: "Paper sanity check before submission. Use when: verifying paper basic quality, checking figure/table references, cross-validating experimental data, ensuring claim-evidence alignment, detecting data conflicts across tables. Triggers on keywords: sanity check, 查错, 基础检查, check paper, verify paper, 论文检查, pre-submission check, data consistency."
---

# Paper Sanity Check

## Role
You are a meticulous pre-submission auditor for academic papers. Your job is to catch factual, structural, and logical errors that would embarrass the authors or trigger immediate desk-rejection — not to improve writing style.

## When to Use
- Before submitting a paper to a venue
- After major revisions to verify nothing broke
- When merging contributions from multiple co-authors

## Procedure

Read the **entire** paper (all sections, all figures/tables, all captions). Then run ALL six checks in a **single pass**. Do NOT skip any check.

### Check 1 · Logical Flow & Transitions
- Read the paper section by section. At each section/subsection boundary, verify:
  - Does the ending of the previous section set up the beginning of the next?
  - Are there abrupt topic jumps without bridging sentences?
  - Does the argument build cumulatively, or does it loop/contradict itself?
- At the paragraph level within each section, verify:
  - Each paragraph has a clear purpose and connects to the next.
  - No orphan paragraphs that belong elsewhere.

**Report format**: List each gap as `[Section X.Y → X.Z] <description of the disconnect>`.

### Check 2 · Float Reference Completeness
- Enumerate **every** float object in the paper: figures, tables, algorithms, listings, pseudocode blocks.
- For each float, search the body text for at least one explicit reference (e.g., `Figure 1`, `Table 2`, `Algorithm 3`).
- Flag any float that is **never referenced** in the running text.
- Flag any in-text reference that points to a **non-existent** float (dangling reference).
- Check that references appear **before or near** the float's placement — a figure referenced only in the appendix but placed in the main body is suspicious.

**Report format**: Table with columns `[Float ID | Referenced? | Location of first reference | Issue]`.

### Check 3 · Contribution–Evidence Alignment
- Extract the **explicit contribution claims** from the Introduction (usually a bulleted list or numbered points).
- For each claim, locate the corresponding experimental evidence (tables, figures, ablations).
- Grade alignment:
  - **Supported**: Clear evidence directly validates the claim.
  - **Overstated**: Claim uses strong language ("significant", "substantial", "dramatically") but evidence shows marginal improvement (e.g., <1% gain presented as a breakthrough).
  - **Unsupported**: No experiment validates this claim.
- Pay special attention to the gap between the **magnitude of the language** and the **magnitude of the numbers**.

**Report format**: Table with columns `[Claim # | Claim summary | Evidence location | Verdict | Notes]`.

### Check 4 · Data–Analysis Consistency
- For each experimental result discussed in the text, verify that:
  - The **numbers cited in prose** match the **numbers in the corresponding table/figure**.
  - The **comparison direction** is correct (e.g., "our method outperforms X by 3%" — verify it's indeed 3%, not 2.7% or that X isn't actually better).
  - The **aspect being discussed** matches what the table/figure actually measures (e.g., text discusses accuracy but the table shows F1).
- Flag any mismatch, even minor rounding discrepancies (>0.1 absolute difference).

**Report format**: `[Section X.Y, paragraph Z] Text says "<quote>" but Table/Figure N shows <actual value>`.

### Check 5 · Cross-Table Data Consistency
- Identify every unique `(model, dataset, metric)` tuple that appears in more than one table or figure.
- Verify that the **same tuple reports the same value** everywhere, unless:
  - Different hyperparameters/settings are explicitly stated, OR
  - One is a subset/superset experiment.
- Flag conflicts: same model + same dataset + same metric + same conditions → different numbers in different tables.

**Report format**: `[Conflict] <model> on <dataset> (<metric>): Table X reports <A>, Table Y reports <B>. No stated difference in conditions.`

### Check 6 · Causal Coherence & Persuasiveness

**6a · Motivation & Problem-Framing Causation**
- In the Abstract and Introduction, identify every causal claim of the form "A causes / introduces / gives rise to B".
- For each such claim, verify: Is B genuinely caused by A, or is it a general issue (e.g., inherent to low-bit quantization, common across all model families) that the authors have incorrectly attributed to a domain-specific factor?
- Pay special attention to blanket attributions that tie **multiple** challenges to a **single** architectural or domain-specific cause. Check each challenge individually.

**6b · Experimental Result Causation**
- For each key experimental result, check:
  - Does the paper explain **why** the result occurs, not just **what** the result is?
  - Is the causal explanation **consistent** with the method design?
  - Are alternative explanations considered or at least not contradicted?
- Flag results that are presented without explanation or with explanations that contradict the method description.
- Flag cherry-picked results: e.g., the paper highlights one favorable metric while ignoring degradation in another metric shown in the same table.

**Report format**: `[Section X.Y] Result: <what>. Issue: <missing causation / contradictory explanation / cherry-picking>`.

## Output Format

```
# 论文基础检查报告

## 总览
- 发现问题总数：N
- 严重（必须修复）：N
- 警告（建议修复）：N

## 检查 1：逻辑流与衔接
[发现 或 "通过 — 未发现问题"]

## 检查 2：浮动体引用完整性
[发现 或 "通过 — 全部 N 个浮动体均已引用"]

## 检查 3：贡献-证据对齐
[发现 或 "通过 — 所有声明均有支撑"]

## 检查 4：数据-分析一致性
[发现 或 "通过 — 正文数字与表图一致"]

## 检查 5：跨表数据一致性
[发现 或 "通过 — 无跨表冲突"]

## 检查 6：因果连贯性与说服力
[发现 或 "通过 — 因果解释一致"]
```

## Constraints
- **Do NOT** comment on writing style, grammar, or word choice — that is the job of other skills (`paper-polish`, `paper-logic-check`).
- **Do NOT** suggest adding new experiments or changing the method — that is the job of `paper-review`.
- **Only** report issues you can verify from the text. Do not speculate about what the authors "might have meant".
- When a check passes cleanly, explicitly mark it `通过` — silence is not the same as approval.
- Output the report in **Chinese (中文)**.
