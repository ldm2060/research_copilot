---
name: scientist-runtime-init
description: "AI Scientist 运行环境检查技能。Use when: checking through the ai-scientist MCP whether the scientist-support bundle can run local non-model commands, validating Python or CUDA or LaTeX prerequisites, or when user says '检查环境', '能不能跑 AI Scientist', 'runtime check', '初始化 AI Scientist 环境'."
---

# scientist-runtime-init

通过 ai-scientist MCP 检查当前工作区里的 scientist-support AI Scientist runtime 运行条件。

## 目标

优先确认以下条件，而不是直接启动长时间实验：

- skill runtime 根目录是否存在
- Python 是否可用
- `pdflatex`、`bibtex`、`pdftotext`、`chktex` 是否可用
- `torch.cuda.is_available()` 是否为真
- 当前平台是否适合继续做本地实验和 LaTeX 编译

## 首选方式

如果要做完整检查，统一调用 ai-scientist MCP 的 `validate_runtime`。

这个 skill 负责组织检查步骤和输出格式，不应该再依赖 skill 目录里的 runner 或其他脚本入口。

如果 MCP 不可用，再用终端手动检查同一组宿主条件，但保持同样的输出结构。

## 输出要求

以“就绪 / 缺失 / 风险”三栏归纳：

- 已满足项
- 缺失项
- 风险项（例如 Windows 平台、无 GPU、无 LaTeX）

最后给出下一步建议：

- 可以继续 ideation
- 可以继续本地实验、plotting 辅助或论文编译
- 必须先补环境

## 禁止事项

- 不要调用任何 skill 内 runner 或脚本入口
- 不要把 API key 或模型 SDK 可用性当成 runtime-init 检查项