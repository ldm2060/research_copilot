# Research Copilot

[English](README.md) | 简体中文

Research Copilot 是一个 Trellis 风格的、面向研究的、多平台 CLI 工具（`rc`），用于将学术研究作为受控的、有状态的工作流运行。它将每项工作建模为具有通用生命周期（`planning -> in_progress -> verify -> completed`）的任务，并与研究活动 `kind`（文献、构思、实验、写作、润色、审阅、反驳）交叉。引导方式是**注入驱动**：每次对话时，编程助手钩子运行 `rc context`，注入当前工作流状态以及从任务图计算出的确定性下一步推荐 — 你决定下一步做什么，不会自动创建任何内容。

这次重建**取代了之前的 Claude Code 插件架构**（作为插件发布的 320+ 技能 / MCP 服务器）。参见[重新设计规范](docs/superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md)了解锁定的决策和理由。

- 作者：ldm2060
- 仓库：https://github.com/ldm2060/research_copilot

## 状态

**Phase 0 — 已发布：**

- `packages/core` — 纯引擎：任务模型、生命周期状态机、研究状态推荐器、验证检查、工作流解析器、上下文构建器。
- `packages/cli` — `rc` 命令行工具。
- `packages/adapters` — 平台注册表加上 Claude Code 配置器。
- `research-kit/` — workflow.md、10 个中性的 `rc-*` 助手模板、配置默认值、规范模板。
- **Claude Code 是唯一完全发布的平台**（通过 `UserPromptSubmit` 钩子进行 class-1 推送注入）。

其他平台已在适配器注册表中设计；它们的适配器将在后续阶段发布（参见下面的矩阵）。

## 安装

### 快速开始（npx - 无需安装）

```bash
npx @research-copilot/cli init --user your-name --claude
```

### NPM（推荐）

```bash
npm install -g @research-copilot/cli
```

### 其他方式

- **pnpm**: `pnpm add -g @research-copilot/cli`
- **Yarn**: `yarn global add @research-copilot/cli`
- **从源码构建**: 克隆并构建（参见 [INSTALLATION.md](./INSTALLATION.md)）
- **GitHub Releases**: 下载预构建的归档文件（参见 [Releases](https://github.com/ldm2060/research_copilot/releases)）

详细的安装说明、平台特定注意事项和故障排除，请参见 [INSTALLATION.md](./INSTALLATION.md)。

## 快速入门指南

刚接触 Research Copilot？从这里开始：

- **[Getting Started Guide](docs/usage/getting-started.md)** — 从安装到第一个任务的分步教程（英文）
- **[快速入门指南（中文）](docs/usage/getting-started.zh-CN.md)** — 中文版快速入门教程

## `rc` 命令

| 命令 | 功能 |
|---|---|
| `rc init -u <name> [--claude]` | 搭建 `.research/` 并（使用 `--claude`）配置 Claude Code。 |
| `rc task create --kind <k> --title <t> [--venue <v>] [--parent <p>]` | 创建研究任务；打印其 id 并将其设为活动任务。 |
| `rc task start <id>` | 将任务从 `planning` 移至 `in_progress`。 |
| `rc task set-status <id> <state>` | 显式应用生命周期转换。 |
| `rc task verify <id>` | 运行验证门；失败时将任务回滚到 `in_progress`。 |
| `rc task complete <id>` | 将任务从 `verify` 移至 `completed`。 |
| `rc task add-gap <id> --desc <d> --suggest <kind>` | 记录驱动下一步推荐的开放缺口。 |
| `rc task current` | 打印活动任务 id。 |
| `rc context [--platform <p>] [--inject] [--format text\|json]` | 发出每次对话的注入块；由 Claude Code 钩子调用。 |
| `rc doctor` | 检查 `.research/`、`workflow.md` 和 `.claude/settings.json` 是否存在；失败时退出 1。 |

`kind` 可以是：`literature`、`ideation`、`experiment`、`writing`、`polish`、`review`、`rebuttal`。完整的标志参考和示例：[docs/usage/commands.md](docs/usage/commands.md)。

## 平台支持矩阵

| 平台 | 状态 | 注入方式 |
|---|---|---|
| Claude Code | ✅ 已完成 | Class-1 推送 — `UserPromptSubmit` 钩子 -> `rc context` |
| Codex | ✅ 已完成 | Class-1 推送 — `UserPromptSubmit` 钩子（版本门控） |
| OpenCode | ✅ 已完成 | Class-1 推送 — 进程内 `chat.system.transform` 插件 |
| Gemini CLI | ✅ 已完成 | Class-1 推送 — `BeforeAgent` 钩子 |
| Cursor | ✅ 已完成 | Class-2 面包屑 — sessionStart 一次 + 始终启用的 `Active task:` 规则 |
| Windsurf | ✅ 已完成 | Class-2 面包屑 — 始终启用的规则（无助手） |
| Kiro / Qoder / CodeBuddy / Droid / Pi / Copilot / Kilo / Antigravity | 🔄 规划中 | 注册表 + 模板增量 |

**Class-1** 平台支持每次对话的推送注入；**Class-2** 平台不支持，因此助手每次对话重新回显 `Active task:` 面包屑并重新解析状态。参见 [docs/dev/architecture.md](docs/dev/architecture.md) 和 [docs/dev/adding-a-platform.md](docs/dev/adding-a-platform.md)。

## 与旧插件的关系

Research Copilot 之前是一个 Claude Code 插件（市场包，包含 320+ 技能、10 个助手、6 个 Python MCP 服务器和一个 SessionStart 守护钩子）。该架构已被这个 TypeScript 全栈、多平台的重建**取代**。决策日志（D1–D8）和迁移路径记录在[重新设计规范](docs/superpowers/specs/2026-06-05-research-copilot-trellis-redesign-design.md)和 [docs/dev/adr/0001-trellis-emulation.md](docs/dev/adr/0001-trellis-emulation.md) 中。

## 文档

- **使用文档（研究人员）：** [docs/usage/](docs/usage/README.md) — 命令参考、Claude Code 设置、完整工作流演练。
- **开发文档（贡献者）：** [docs/dev/architecture.md](docs/dev/architecture.md)、[docs/dev/core-api.md](docs/dev/core-api.md)、[docs/dev/adding-a-platform.md](docs/dev/adding-a-platform.md)、[docs/dev/testing.md](docs/dev/testing.md)、[docs/dev/adr/0001-trellis-emulation.md](docs/dev/adr/0001-trellis-emulation.md)。
