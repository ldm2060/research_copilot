# ai-scientist MCP Server

本地 MCP 包装器，只暴露 AI Scientist 工作流的非模型型运维工具。

## 提供的工具

- `validate_runtime`：检查 Python、LaTeX、poppler、CUDA 和 skill runtime 根目录
- `list_experiments`：浏览 `experiments/` 目录
- `inspect_experiment`：查看单个实验目录下的 PDF、日志、LaTeX 输入和 token 统计等非模型产物

## 不再由 MCP 承担的阶段

以下阶段会调用模型或触发 agent 型长流程，因此改由 scientist agent / scientist skills 在会话内直接执行：

- ideation
- BFTS experiment pipeline
- plot aggregation
- writeup
- PDF review

## 设计原则

1. **MCP 只做轻量本地能力**：状态检查、路径发现、实验目录浏览。
2. **skill 只保留静态 runtime 资产**：源码树在 `self/skills/scientist-support/runtime/`，bundle 产物里对应 `.github/skills/scientist-support/runtime/`。
3. **模型驱动任务交给 agent**：需要明确模型、长时间运行或多阶段推理的任务不经由 MCP。
4. **路径可显式指定**：如果用户故意把 runtime 挪到别处，仍可通过 `project_root` 覆盖默认路径。

## 运行说明

此 server 不会自动安装依赖。建议先通过 `scientist-runtime-init` 或 `validate_runtime` 检查环境，再由 scientist agent 或对应 skills 在 Copilot 会话中直接执行 ideation、experiment、plotting、writeup 和 review。