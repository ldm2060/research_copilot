# Research Copilot 快速入门

Research Copilot 是一个面向学术研究的 CLI 工具（`rc`），帮助你将学术研究组织为受控的、有状态的工作流。本指南将引导你完成安装、设置和第一个研究任务。

## 前置要求

- Node.js 18 或更高版本
- Claude Code（或其他支持的平台）
- 一个研究项目目录

## 安装

### 快速开始（推荐）

使用 npm 全局安装：

```bash
npm install -g @research-copilot/cli
```

验证安装：

```bash
rc --version
```

### 其他安装方式

**使用 pnpm：**
```bash
pnpm add -g @research-copilot/cli
```

**使用 Yarn：**
```bash
yarn global add @research-copilot/cli
```

**无需安装（使用 npx）：**
```bash
npx @research-copilot/cli init --user your-name --claude
```

## 首次设置

### 1. 初始化研究项目

进入你的研究项目目录并运行：

```bash
rc init --user your-name --claude
```

此命令会：
- 创建 `.research/` 目录及工作流结构
- 设置 Claude Code 集成（使用 `--claude` 标志）
- 生成规范、任务和工作区的模板目录
- 为 Claude Code 配置注入钩子

验证设置：

```bash
rc doctor
```

你应该看到：
```
OK  .research/ exists
OK  workflow.md exists
OK  .claude/settings.json exists
```

### 2. 理解目录结构

初始化后，你的项目将包含：

```
your-project/
├── .research/
│   ├── tasks/           # 任务定义和状态
│   ├── spec/            # 研究规范
│   │   ├── venue/       # 会议/期刊信息
│   │   ├── writing/     # 写作规范
│   │   ├── baselines/   # 基线模型
│   │   ├── methodology/ # 方法论
│   │   └── novelty/     # 创新点
│   ├── workspace/       # 工作产物
│   ├── .runtime/        # 运行时状态
│   ├── workflow.md      # 工作流指南
│   └── config.yaml      # 配置文件
└── .claude/
    ├── settings.json    # Claude Code 钩子配置
    └── agents/          # 研究助手模板
```

## 第一个研究任务

### 1. 检查当前状态

在创建任务之前：

```bash
rc context
```

输出：
```
[workflow-state:no_task]
无活动任务。使用以下命令创建: rc task create --kind <k> --title "<t>"
[/workflow-state]

[research-state]
Active: none
Graph: 0 completed · 0 in_progress · 0 blocked
```

### 2. 创建文献综述任务

```bash
rc task create --kind literature --title "Survey transformer architectures" --venue ICML
```

这会返回一个任务 ID，例如：
```
2026-06-06-survey-transformer-architectures
```

**可用的任务类型：**
- `literature` — 阅读论文、综述
- `ideation` — 头脑风暴、假设生成
- `experiment` — 运行实验、收集数据
- `writing` — 撰写论文、章节
- `polish` — 编辑、格式化、润色
- `review` — 同行评审、反馈整合
- `rebuttal` — 回应评审意见

### 3. 查看活动任务

```bash
rc task current
```

输出：
```
2026-06-06-survey-transformer-architectures
```

### 4. 查看工作流状态

```bash
rc context
```

现在你会看到：
```
[workflow-state:planning]
活动任务处于 PLANNING 阶段。使用 rc-plan 助手将其细化为 prd.md，
并整理 execute.jsonl / verify.jsonl。然后: rc task start <id>
[/workflow-state]

[research-state]
Active: 2026-06-06-survey-transformer-architectures (literature, planning)
Graph: 0 completed · 0 in_progress · 0 blocked
推荐的下一步：
  1. 继续文献任务 2026-06-06-survey-transformer-architectures (planning)
```

### 5. 开始处理任务

将任务从规划阶段移至进行中：

```bash
rc task start 2026-06-06-survey-transformer-architectures
```

工作流状态变更：
```bash
rc context
```

```
[workflow-state:in_progress]
活动任务正在进行中。使用 prd.md + execute.jsonl 规范调度 rc-literature 执行器。
不要直接进行领域工作。完成后: rc task verify <id>
[/workflow-state]
```

### 6. 与 Claude Code 协作

通过 Claude Code 集成，工作流状态会自动注入到每次对话中。只需向 Claude 请求帮助：

```
"帮我为 ICML 综述最近的 transformer 论文"
```

Claude 会看到工作流状态，并根据研究生命周期引导你。

### 7. 验证你的工作

完成任务工作后，将其移至验证门：

```bash
rc task set-status 2026-06-06-survey-transformer-architectures verify
rc task verify 2026-06-06-survey-transformer-architectures
```

如果验证通过：
```
verify OK for 2026-06-06-survey-transformer-architectures
```

如果失败，任务会自动回滚到 `in_progress` 状态以便修复。

### 8. 完成任务

通过验证后：

```bash
rc task complete 2026-06-06-survey-transformer-architectures
```

检查进度：
```bash
rc context
```

```
[research-state]
Active: none
Graph: 1 completed · 0 in_progress · 0 blocked
推荐的下一步：
  （基于已完成工作和开放缺口的推荐）
```

## 常用工作流

### 创建子任务

创建依赖于其他任务的后续任务：

```bash
rc task create --kind experiment \
  --title "Implement baseline model" \
  --parent 2026-06-06-survey-transformer-architectures
```

### 记录研究缺口

当你发现缺失的工作：

```bash
rc task add-gap 2026-06-06-survey-transformer-architectures \
  --desc "需要对注意力头进行消融研究" \
  --suggest experiment
```

此缺口将出现在推荐中：
```
开放缺口：
  - [来自 2026-06-06-survey...] 需要消融研究 -> 建议: experiment
推荐的下一步：
  2. 创建实验任务以解决 "需要消融研究..."
```

### 检查任务状态

查看所有任务：
```bash
rc task list
```

显式设置任务状态：
```bash
rc task set-status <task-id> <status>
```

有效状态：`planning`, `in_progress`, `verify`, `completed`

## 与 Claude Code 集成

`rc context` 命令通过 `UserPromptSubmit` 钩子在每次 Claude Code 对话时自动运行。这提供了：

1. **工作流状态** — 当前生命周期阶段的指导
2. **研究状态** — 活动任务、任务图概览、推荐
3. **确定性的下一步** — 从任务图和缺口计算得出

使用 Claude Code 时不需要手动运行 `rc context` — 它会自动发生。

## 更新 Research Copilot

检查已安装的版本：
```bash
rc --version
```

更新到最新版本：
```bash
npm update -g @research-copilot/cli
```

或重新安装：
```bash
npm install -g @research-copilot/cli@latest
```

## 下一步

- **[命令参考](commands.md)** — 所有 `rc` 命令的详细文档
- **[工作流演练](workflow-walkthrough.md)** — 从初始化到完成的完整示例
- **[Claude Code 设置](claude-code.md)** — 平台特定的配置详情

## 故障排除

### 找不到 rc 命令

确保 npm 全局 bin 目录在你的 PATH 中：
```bash
npm config get prefix
```

将 `<prefix>/bin`（Unix）或 `<prefix>`（Windows）添加到 PATH。

### 找不到 .research/ 目录

确保你在运行 `rc init` 的项目根目录，或指定路径：
```bash
rc task create --repo /path/to/project --kind literature --title "..."
```

### Claude Code 中钩子未触发

验证钩子已配置：
```bash
rc doctor
```

检查 `.claude/settings.json` 包含：
```json
{
  "hooks": {
    "UserPromptSubmit": "rc context --event UserPromptSubmit --format json"
  }
}
```

## 获取帮助

- **GitHub Issues**: https://github.com/ldm2060/research_copilot/issues
- **文档**: https://github.com/ldm2060/research_copilot/tree/main/docs
- **命令帮助**: `rc --help`
