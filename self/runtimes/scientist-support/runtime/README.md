# AI Scientist Bundle Runtime

这个目录在 Copilot bundle 里只保留非模型用途：

- 为 `scientist-runtime-init` 提供本地宿主检查目标
- 为 `ai-scientist` MCP 提供实验目录观测根路径
- 保留少量说明文档和许可证信息

## 当前约束

- 不允许从这个 runtime 里调用任何自定义模型脚本
- 不再提供 skill 内 runner 或脚本入口
- 不允许通过 workspace Python 代码直接调用 OpenAI、Anthropic、Gemini、Bedrock 或其他模型 SDK
- ideation、experiment、plotting、writeup、review 的模型输出必须由 Copilot 当前会话直接完成

## 正确使用方式

1. 用 `scientist-runtime-init` 通过 ai-scientist MCP 的 `validate_runtime` 检查 Python、LaTeX、PDF 工具链、CUDA 等本地条件。
2. 用 `ai-scientist` MCP 查看实验目录、日志、PDF、LaTeX 输入和 token 统计等非模型产物。
3. 用 `scientist` agent 或对应的 `scientist-*` skills 在 Copilot 中直接完成 ideas、实验决策、作图、写作和审稿。

## 不再暴露的上游能力

以下上游内容在 bundle 工作流中不再作为可执行入口，也会在打包时被剔除：

- 上游实验 orchestrator 脚本与配置
- 上游 Python requirements 清单
- `ai_scientist/` 下的模型调用与 treesearch 运行时代码

## 备注

如果你需要参考上游 AI Scientist-v2 的原始实现，请回到上游仓库查看；不要把这些上游脚本重新接回当前 bundle 的执行路径。
