# Project Instructions

## 本地改动策略

- 本地、可逆、范围明确的小改动直接做；改完运行必要验证并提交 git commit，只有破坏性、外部可见、难回滚或需求不明确时才先询问。
- 完成修改后自动 git commit，但不要自动 git push，除非用户明确要求推送。

## 项目定位

Research Copilot（命令名 `rc`）是一个 Trellis 风格的、注入式驱动的科研工作流引擎。核心思想是：**主对话只负责编排与生命周期推进，所有领域工作（检索/构思/实验/写作/评审）都派发给 `rc-*` 子代理执行**。本仓库是其 pnpm monorepo。

- 运行环境：Node >=20，pnpm 9.12.0。
- 入口包：`packages/cli`（命令行）、`packages/core`（纯确定性引擎）、`packages/adapters`（多平台配置器）、`packages/plugin`（内容插件打包）、`packages/mcp-pdf` / `packages/mcp-scholar`（MCP 服务）。
- 运行时状态目录：`.research/`（任务、配置、spec、workflow 定义）。中性内容包：`research-kit/`（平台无关的 workflow 定义、agent 模板）。
- 平台适配：`packages/adapters/src/registry.ts` 注册六个平台 —— claude-code、codex、opencode、gemini（class 1，有 hooks/agents）、cursor、windsurf（class 2，能力受限）。Claude Code 是默认平台。

## 常用命令

仓库根目录：

- `pnpm install --frozen-lockfile` —— 安装依赖（CI 用法）。
- `pnpm -r build` —— 构建全部子包（等于 `pnpm run build`）。
- `vitest run` —— 跑测试（等于 `pnpm test`）。
- `pnpm run ci` —— 构建后跑测试，等价于 CI 流程。

`rc` CLI（`packages/cli/bin/rc.ts`）：

- `rc init [--claude|--codex|--opencode|--gemini|--cursor|--windsurf] -u <name> [--install-plugin]` —— 在当前仓库初始化/对账 `.research/`、平台 hooks/agents/MCP 配置；`-u` 为必填的开发者身份；`--install-plugin` 触发插件注册。未指定平台时默认 Claude Code。
- `rc context [--platform <p>] [--inject] [--format text|json] [--event <name>]` —— 产出注入块。Claude Code 的 `UserPromptSubmit` hook 会以 `rc context --inject --format text` 调用，生成 `[workflow-state:...]...[/workflow-state]` 与 `[research-state]` 推荐内容。**这是每轮驱动工作流的真实入口**。
- `rc doctor [--fix] [--skip-plugin] [--strict-plugin]` —— 检查/修复 `.research/` 核心配置；`--strict-plugin` 把插件版本不一致视为失败。
- `rc sync [--repo <p>] [--cache-dir <p>] [--target-dir <p>]` —— 拉取 skillpack 并渲染 agents/specs。
- `rc task create|start|complete|verify|set-status|add-gap|current` —— 任务生命周期操作（见下）。
- `rc plugin install|status|update|remove` —— 平台插件安装/同步/移除；会把插件 `dist/` 拷进平台 skill 路径，并拒绝向陌生目录写入。

## 架构与状态模型

引擎核心位于 `packages/core/src/`（纯函数、无 IO 副作用）：

- `types.ts` —— `Kind`（literature / ideation / experiment / writing / polish / review / rebuttal）与 `Status`。
- `lifecycle.ts` —— 任务状态机：`planning -> in_progress -> verify -> completed`；`verify` 可回退到 `in_progress`；`completed` 终态。`TRANSITIONS` 是允许迁移的唯一来源。
- `task-store.ts` / `paths.ts` —— 任务的读写与路径约定。
- `graph.ts` —— 任务间父子/引用关系。
- `research-state.ts` —— 根据当前任务与历史产出推荐下一步活动，喂给 `[research-state]` 注入块。
- `workflow.ts` / `context.ts` —— 把 `workflow.md` + 推荐器结果组装成每轮注入文本。
- `verify.ts` —— verify 纯检查函数（如 `writing` 类编号可追溯性）；CLI `rc task verify` 调用这些检查并处理状态回退，构成完整门禁。

`.research/` 运行时布局：

- `workflow.md` —— 当前 workflow 状态块定义（来自 `research-kit/workflow.md`）。
- `config.yaml` —— 项目配置。
- `.runtime/active-task` —— 当前活跃任务 id（`rc task current` 读它）。
- `tasks/<id>/task.json` —— 任务元数据；含 `gaps`（由 `rc task add-gap` 写入）。
- `tasks/<id>/artifacts/`、`research/`、`spec/`、`workspace/` —— 任务相关产出。
- `spec/` —— 跨任务沉淀的知识（由 `rc-update-spec` 写入）。

任务命令与状态机的对应（`packages/cli/src/commands/task.ts`）：

- `rc task create --kind <k> --title "<t>" [--venue <v>] [--parent <p>]` → 创建并设为 active。
- `rc task start <id>` → `in_progress`。
- `rc task verify <id>` → 跑 verify 门禁；失败会回退到 `in_progress` 并以非零退出码报错。
- `rc task complete <id>` → `completed`。
- `rc task set-status <id> <state>` → 显式迁移（仍受 `TRANSITIONS` 约束）。
- `rc task add-gap <id> --desc "<d>" --suggest <k>` → 记录 gap，建议下一个任务 kind。
- `rc task current` → 打印 active task id。

## 主对话 vs 子代理/执行器 的边界（重要）

`research-kit/workflow.md`（以及 `.research/workflow.md`）定义了五个 `[workflow-state:*]` 块。**主对话根据注入的状态决定下一步动作，并且必须把领域工作派发给 `rc-*` 执行器，而不是自己内联完成**。可用执行器模板位于 `research-kit/agents/`：

- `rc-plan` —— `planning` 阶段：把模糊需求澄清为 `prd.md`，并产出 `execute.jsonl` / `verify.jsonl`。完成后主对话运行 `rc task start <id>`。
- `rc-literature` / `rc-ideation` / `rc-experiment` / `rc-writer` / `rc-reviewer` / `rc-rebuttal` / `rc-polisher` —— `in_progress` 阶段的领域执行器，按 `Kind` 派发，读取 `prd.md` 与 `execute.jsonl`。执行器返回后，主对话运行 `rc task verify <id>`。
- `rc-verify` —— `verify` 阶段：跑该 kind 的质量门禁。通过 → `rc task complete <id>`；不通过 → 修复后 `rc task set-status <id> in_progress`。
- `rc-update-spec` —— `completed` 阶段：把本轮学到的东西沉淀进 `.research/spec/`，追加日志，再参考 `[research-state]` 决定下一项活动。

执行器是**叶子工作者**，带递归保护：执行器自身不应再派发其它 `rc-*` 代理；遇到失败或缺口应通过 `rc task add-gap` 记录，并向主对话汇报。主对话的职责仅限编排、生命周期迁移、以及向用户综合汇报。

## 关键文件速查

- `packages/core/src/{types,paths,task-store,lifecycle,graph,research-state,workflow,context,verify}.ts` —— 引擎核心。
- `packages/cli/bin/rc.ts` + `packages/cli/src/program.ts` —— CLI 入口与命令装配。
- `packages/cli/src/commands/{context,doctor,init,plugin-command,sync,task}.ts` —— 各命令实现。
- `packages/adapters/src/registry.ts` —— 平台注册表；`claude-code` 配置器会合并 `.claude/settings.json` 的 `UserPromptSubmit` hook、拷贝 10 个 `rc-*` agents、向 `CLAUDE.md` 追加 workflow 备注、合并 `.mcp.json`。
- `packages/plugin/build.ts` —— 从根清单 `skill.txt`/`agent.txt`/`hook.txt` 构建内容插件，拷贝 `self/agents`、`self/hooks`、`self/skills` 与 `third_party` 技能到 `dist/`，并生成各平台元数据目录（`.claude-plugin` 等）。
- `research-kit/workflow.md` + `research-kit/agents/rc-*.md` —— 中性 workflow 与执行器模板，平台初始化时被拷进各自的配置目录。

## 已知坑位 / 注意事项

- **版本漂移**：磁盘上各包版本可能不一致（如 CLI 1.1.20、plugin 1.1.13、core/adapters 0.0.0-dev、mcp 包 1.0.0）。正式发布由 CI 的 release workflow 统一改写并打 tag；本地不要手改版本号去"对齐"。
- **plugin 包不是运行时 JS**：`packages/plugin/package.json` 的 `main`/`types` 指向 `dist/index.*`，但 `build.ts` 并不产出这些文件 —— 它是被当作内容型 `dist/` 消费的，别当成普通 Node 模块去 import。
- **CLI 的 research-kit 是生成的**：`packages/cli/research-kit/` 由 CLI 构建 / `copy-kit` 产生，被 git 忽略，不要手工编辑。
- **子模块**：本地构建插件依赖已初始化的 `third_party/` 子模块；CI 会 `submodules: recursive` 检出。新环境要先 `git submodule update --init --recursive`。
- **Plugin 注册的安全约束**：`rc plugin install` 只把 dist 拷进平台 skill 路径，会拒绝向不在白名单内的目录写入；遇到"目录不属于已知平台"的错误不要绕过。
- **研究工作流别内联**：即便主对话有能力直接做检索/写作，本项目的契约是必须派发给对应 `rc-*` 执行器；只有编排、状态迁移和向用户的综合汇报留在主对话。

## 验证清单（改动后视情况运行）

- 改 TS 代码：`pnpm -r build`。
- 改逻辑/修复 bug：`vitest run`（或 `pnpm run ci` 一把梭）。
- 改 `.research/` 或平台配置：`rc doctor`（必要时 `--fix`）。
- 改 workflow / agent 模板：在干净仓库里 `rc init` 重新对账，再 `rc context` 确认注入块格式正确。
