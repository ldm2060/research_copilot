# Agents 总览

本目录包含论文研究工作流中的各环节专用 Agent。每个 Agent 以 `.agent.md` 文件定义，可在 VS Code Copilot Chat 中通过 `@agent-name` 调用。

| Agent | 文件 | 说明 |
|-------|------|------|
| **scientist** | `scientist.agent.md` | 🧪 **AI Scientist 总控助手**。统筹 idea 生成、BFTS 实验搜索、作图聚合、论文写作与自动审稿，优先调用 `ai-scientist` MCP 与 scientist 系列 skills。 |
| **paper** | `paper.agent.md` | 🧭 **论文研究总控助手**。统筹创新点挖掘、方法细化、代码实验、论文写作、审稿、rebuttal 等全流程，负责判断当前环节并委派给最合适的子 Agent 或 Skill。 |
| **writer** | `writer.agent.md` | ✍️ **论文写作专用助手**。负责章节起草、重写、润色、LaTeX 结构整理、引用驱动写作，基于 `.pipeline/memory/` 上下文推进到可审稿状态。 |
| **novelty** | `novelty.agent.md` | 💡 **创新点挖掘助手**。基于给定 baseline 进行文献地图构建、多维度头脑风暴、审稿人式筛选，产出可落地的创新点报告。 |
| **auto-reviewer** | `auto-reviewer.agent.md` | 🔍 **自动审稿循环 Agent（Claude 专用）**。与 `auto-improver` 配对，通过 `tmp_review.md` 文件信号实现跨会话审稿-修改循环，最多 5 轮。 |
| **auto-improver** | `auto-improver.agent.md` | 🔧 **自动修改循环 Agent（GPT 专用）**。与 `auto-reviewer` 配对，监听审稿意见后自动修改论文，通过 `tmp_improve.md` 通知审稿端。 |
| **overhaul** | `overhaul.agent.md` | 🏗️ **论文全面优化助手**。按 6 阶段串行管道执行全面优化：自动预处理 → 审视与逻辑检查 → 扩写/缩写 → 全文润色 → 去AI味 → 终审复查。 |

## 使用场景

- **跑 AI Scientist 全流程** → `@scientist` 总控，判断先做 runtime 检查、idea 生成、实验、写作还是审稿
- **从头写论文** → `@paper` 总控，自动分配 `@writer` 写作
- **找创新点** → `@novelty` 挖掘可行创新方案
- **通篇优化** → `@overhaul` 执行多阶段全面改进
- **自动审改循环** → 同时开两个 Chat：`@auto-reviewer` (Claude) + `@auto-improver` (GPT)
