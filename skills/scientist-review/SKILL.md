---
name: scientist-review
description: "AI Scientist 自动审稿技能。Use when: reviewing a manuscript or PDF directly in Copilot, producing structured review feedback, or when user says '审一下这篇 PDF', '自动审稿', '给我 review'."
---

# scientist-review

对论文或 PDF 做 Copilot-native 文本审稿。模型判断和审稿输出由 Copilot 在会话里直接生成，不允许再通过 workspace 自定义脚本调用模型。

## 执行方式

这是 **Copilot-native 模型任务**。如果用户只给 PDF，先提取文本，再由 Copilot 直接给出审稿意见。

## 工作流

1. 获取论文内容：优先使用现成 Markdown / LaTeX / TXT；只有 PDF 时再做文本提取。
2. 直接在会话里完成审稿、打分和风险判断。
3. 如用户要求结构化输出，直接生成 JSON 或写入文件。

## 输入

- `pdf_path`、LaTeX 源文件或已提取文本
- 用户希望采用的评审视角或打分维度

## 输出

- 审稿意见
- 如用户要求，可提供结构化 JSON 审稿结果
- 明确指出优点、主要问题、分数建议和风险项

## 禁止事项

- 不要调用任何 workspace 自定义模型审稿脚本
- 不要在 workspace 脚本里自定义调用模型做审稿

## 结果要求

- 默认以“优点 / 主要问题 / 分数 / 风险”方式汇总
- 如果只有 PDF 且无法提取文本，要明确指出阻塞点