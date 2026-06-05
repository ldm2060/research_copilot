# Research Copilot —— 效仿 Trellis 的全面重建设计

- **日期**: 2026-06-05
- **状态**: 设计待审阅（brainstorming 产出）
- **取代**: `docs/superpowers/specs/2026-05-05-research-copilot-redesign-design.md`（旧的 conductor + 7 子 agent + 重型 hook 架构）
- **一句话**: 抛弃现有 Claude Code 插件式架构，效仿 [Trellis](https://github.com/mindfold-ai/Trellis) 的"任务中心 + 规范驱动 + 多平台 CLI"架构，用 TypeScript 全栈重建一个**学术研究强相关**的多平台工具，重新实现现有的科研全流程功能（文献 / 创新 / 实验 / 写作 / 润色 / 审稿 / rebuttal）。

---

## 1. 目标与背景

### 1.1 现状（要"抛弃"的架构）

现有 `research_copilot` 是一个 Claude Code 插件式科研多智能体系统：

- **1 个 conductor（主会话）+ 7 个 copilot-* 子 agent**（literature / ideation / experiment / writer / polisher / reviewer / rebuttal）
- **自定义状态机 + 7 类 capability gate**（interview / validation / research / longrun / execution / memory / handoff），所有响应附 `[STATE_OUTPUT]` 块
- **重型 hook 强制层**（7 个 Python 脚本）：`research_copilot_guard`（M1 越权拦截 + M2 强制先 TaskCreate）、`copilot_write_guard`（`.copilot/` 文件归属分区）、`session_start_memory_injector`、`post_tool_loop_armer`、`copilot_subagent_stop`、`scientist_guardrails`、`user_prompt_dispatch_reminder`
- **`.copilot/` 工作记忆**：state / literature / ideas / experiments / decisions / handoff + `__HANDOFF__` 交接块
- **资产**：6 个 Python MCP server（arxiv-search / arxivsub-search / google-scholar / dblp-bib / pdf-text / ai-scientist）、28 个自有 skill、~10 套 `third_party/` vendored skill 合集、5–7 个 Claude Code 市场插件依赖
- **构建/分发**：manifest 驱动（`skill.txt`/`agent.txt`/`hook.txt` + `build_copilot_workspace.py`）聚合成 `dist/` 多渠道（GitHub / Gitee）插件包，发布到 `deploy` 分支

### 1.2 Trellis 的架构（要"效仿"的对象）

Trellis 是一个面向 AI 编码 agent 的**任务中心 + 规范驱动**工程 OS，持久化在 git 受控的 `.trellis/` 目录里，通过 CLI 适配 14 个平台。核心机制：

- **`.trellis/` 目录**：`spec/`（写一次、跨会话注入的规范）、`tasks/<MM-DD-slug>/`（每任务一个 PRD 目录：`prd.md` / `task.json` / `implement.jsonl` / `check.jsonl` / `research/`）、`workspace/`（会话日志）、`agents/`、`scripts/`、`config.yaml`、`workflow.md`、`.runtime/sessions/`
- **通用阶段循环**：Plan（brainstorm→prd + research + 规范引用）→ Execute（implement→check，可回滚）→ Finish（终检→沉淀规范→提交→归档）
- **状态机**：`no_task → planning → in_progress → completed`，每状态对应 `workflow.md` 里一个 `[workflow-state:STATUS]` 块，**逐回合注入**引导下一步
- **上下文注入**：4 个共享 hook 脚本（session-start / inject-workflow-state / inject-subagent-context / inject-shell-session-context）按平台接线；不支持逐回合注入的平台用 `"Active task: <path>"` 面包屑兜底
- **多平台**：CLI `trellis init -u <name> [--cursor --codex ...]`；`AI_TOOLS` 注册表（configDir / cliFlag / agentCapable / hasHooks / supportsAgentSkills）+ 每平台 `configure()` 把平台中立模板渲染成原生文件

### 1.3 设计立场

二者理念相近（都是文件化记忆 + 分阶段 + 子 agent），但 Trellis 更轻（注入引导而非 hook 硬拦截）、更任务中心、更通用 + 多平台。本设计：**采纳 Trellis 的结构与机制，但工作流内容做成学术研究强相关 + 序列灵活**（不套用 Trellis 的软件开发阶段）。

---

## 2. 已锁定的决策（决策日志）

本设计经 brainstorming 逐项确认，以下为不可回退的方向性决策：

| # | 决策点 | 选定 | 含义 |
|---|---|---|---|
| D1 | 效仿程度 | **完整复刻：多平台 CLI 框架** | 通用框架底座 + 研究领域层叠加；不是轻量换骨 |
| D2 | 实现语言 | **TypeScript 全栈** | CLI + scripts + MCP server 全 TS；放弃现有 Python 代码资产 |
| D3 | 平台覆盖 | **全平台广覆盖** | 适配层支持全部；v1 落地已核实机制的 6 个 |
| D4 | 命名品牌 | **沿用 research-copilot** | CLI `rc`；目录 `.research/`；agent 前缀 `rc-`；npm 包 `research-copilot` |
| D5 | 阶段映射 | **方案 D** | 通用任务生命周期 × 研究活动作 `kind` × 灵活任务图；非固定流水线、非通用模板 |
| D6 | 编排驱动 | **注入式推荐（Trellis 原生）** | 无独立 conductor agent；每回合注入"研究状态"引导主会话推荐下一步，用户可改向 |
| D7 | 依赖策略 | **A：rc 自管 skill-packs** | 抛弃 CC 市场依赖；`skillpacks.yaml` 拉取渲染到全平台 |
| D8 | 强制哲学 | **注入引导 + verify 门 + spec 规范** | 废弃重型硬拒绝守卫；可选薄告警守卫降级为里程碑 2 备选 |

---

## 3. 总体架构

### 3.1 分层与 Monorepo

TypeScript monorepo（pnpm workspaces），四层。**Trellis 给"机制层"，研究领域层叠加。**

```
research-copilot/                    # 仓库根（pnpm workspace）
├── packages/
│   ├── core/        @research-copilot/core   # 纯 TS 引擎（无副作用）:
│   │   • 任务模型（task.json 读写 + 生命周期转换）
│   │   • spec 解析器（按 kind/venue 匹配 spec/ 注入）
│   │   • 工作流引擎（生命周期状态机 + 研究状态计算）
│   │   • 上下文构建器（组装每回合注入 payload）
│   │   • 任务图（parent/children/depends_on + gap→下一步派生）
│   │   • 会话日志（workspace/ 追加 + 轮转）
│   │   • skill-pack 解析器（skillpacks.yaml 拉取/渲染）
│   ├── cli/         @research-copilot/cli     # `rc` 命令（commander/clipanion）
│   ├── adapters/    @research-copilot/adapters# 各平台配置生成器
│   └── mcp-servers/ @research-copilot/mcp-*   # TS MCP 服务器: scholar / pdf
├── research-kit/                    # 研究领域层"模板源"——rc init 时铺进用户仓库的 .research/
│   ├── agents/                      # rc-* 执行器 + 助手 agent 模板（平台中立）
│   ├── spec-templates/              # 研究规范初始模板
│   ├── workflow.md                  # 研究原生工作流定义
│   ├── pipeline-templates/          # full-research / submission-sprint / rebuttal-prep（可选种子；只产出"建议 gap 列表"供用户逐项接受，不批量建任务、不锁顺序，见 §16.7）
│   ├── skillpacks.yaml              # 外部 skill 包清单（来源 + 许可 + 选取）
│   └── config.defaults.yaml
└── .research/                       # 本仓库自己的工作目录（dogfood，与 rc 给用户生成的同构）
```

**相对 Trellis 的关键改进**：Trellis 把 Python 脚本放进用户仓库 `.trellis/scripts/`（因为它不能假设运行时）。我们有真正安装的 `rc` CLI，所以 **`.research/` 里不放任何脚本**——agent 直接调 `rc task current` / `rc context`。逻辑全部集中在 `core`，用户仓库更干净。

### 3.2 `.research/`：受控工作目录（对应 Trellis 的 `.trellis/`）

```
.research/
├── config.yaml         # 会话提交信息、日志轮转、生命周期 hook、默认会议、monorepo packages
├── workflow.md         # 研究原生工作流: 生命周期状态块 + 研究状态引导（每回合注入）
├── spec/               # 研究规范（写一次、跨会话注入）= 研究领域的"团队约定"
│   ├── venue/          # 目标会议约定: iclr.md / cvpr.md…（页数/风格/审稿标准）
│   ├── writing/        # 写作风格、术语表、引用政策、LaTeX 约定、回复风格
│   ├── baselines/      # 锁定 baseline（paper id + claim + 理由）= 创新性锚点
│   ├── methodology/    # 实验协议、指标定义、可复现规则
│   └── novelty/        # 创新性标准、相关工作地图、novelty 检查项（经 verify 门核验，非工具拦截）
├── tasks/<MM-DD-slug>/ # 一个研究任务一个目录
│   ├── task.json       # 任务元数据（schema 见 3.3）
│   ├── prd.md          # 任务的"研究需求": 目标/范围/成功标准/明确不做什么
│   ├── execute.jsonl   # 注入给执行器 agent 的 spec/上下文引用清单
│   ├── verify.jsonl    # 注入给 verify 步的检查项清单
│   ├── research/       # 收集的先验工作/笔记（文献结果、PDF、抽取文本）
│   └── artifacts/      # 任务产出（draft .tex、run 日志引用、审稿报告、rebuttal 草稿）
├── workspace/          # 会话日志 + 项目记忆（追加，到 max_journal_lines 轮转）
│   └── journal-YYYY-MM.md
└── .runtime/           # gitignored: 活动任务指针、会话状态、模板哈希
    ├── sessions/
    └── active-task
```

### 3.3 task.json —— 研究扩展的数据模型（灵活序列的核心）

```jsonc
{
  "id": "2026-06-05-method-section",
  "title": "Draft the Method section",
  "kind": "writing",          // literature|ideation|experiment|writing|polish|review|rebuttal —— 研究活动一等公民
  "status": "in_progress",    // 生命周期: planning → in_progress → verify → completed（no_task 隐式）
  "priority": "P1",
  "venue": "ICLR-2027",       // 目标会议，链到 spec/venue/
  "parent": "2026-06-04-full-research",     // 来源任务（可选流水线种子，非强制顺序，见 §16.7）
  "children": ["2026-06-06-ablation-x"],    // 派生任务（gap→新任务）
  "depends_on": ["2026-06-02-run-main-exp"],// 图的边（必须先完成）
  "gaps": [                   // ★灵活序列引擎: 本任务暴露的开放缺口
    {"desc": "missing ablation on component X", "suggest_kind": "experiment", "status": "open"}
  ],
  "branch": "paper/method",
  "created": "2026-06-05T...", "updated": "2026-06-05T..."
}
```

三处研究原生扩展：`kind`（7 活动一等公民，决定派哪个执行器、注入哪些 spec）、`depends_on`/`parent`/`children`（任务图的边，动态生成不预设顺序）、`gaps`（执行器发现缺口就登记；每回合注入的研究状态汇总 open gaps + 建议 kind，主会话据此推荐下一步，但不自动建任务——用户拍板）。

借自 Trellis `task.json` 的字段：`title` / `priority`（P0–P3）/ `branch` / `parent` / `children` / `status`。`rc task` 子命令面见 §6.4；与 Trellis `task.py` 的完整命令映射见 §16.8（部分命令重命名/合并，非逐一对应 14 个）。

---

## 4. 工作流引擎与状态机

### 4.1 两层正交状态

**Layer 1 — 任务生命周期（通用，借 Trellis，每个任务都一样）**

```
no_task → planning → in_progress → verify → completed
```

| 状态 | 含义 | 主要动作 |
|---|---|---|
| `no_task` | 无活动任务 | 直接答复，或 `rc task create` 开任务 |
| `planning` | 任务已建 | `rc-plan` 把任务澄清成 prd.md；收集 research/；curate `execute.jsonl`/`verify.jsonl` |
| `in_progress` | `rc task start` 后 | 派 `kind` 匹配的执行器干活，读注入的 spec+prd，产出 artifacts/，登记 gaps |
| `verify` | 执行器完工 | 派 `rc-verify` 做 kind 对应检查；失败→回滚 in_progress，通过→前进 |
| `completed` | 验证通过 | `rc-update-spec` 沉淀规范、写 journal、可选 commit、归档 |

> **命名说明**：生命周期态用 `verify` 而非 Trellis 的 `review`，是**故意**的——避免与研究活动 `kind=review`（模拟同行评审）撞名。`verify` 是"任一任务完工的通用质量门"；`kind=review` 是"产出审稿报告的研究活动"，二者不同。

每个状态对应 `workflow.md` 里一个 `[workflow-state:STATE]` 块，每回合注入（Trellis 机制）。**生命周期只治理"单个任务"的推进，对任务之间、kind 之间不施加任何顺序约束**——跨任务的推进完全是 Layer 2 的推荐（用户决定），从不被生命周期强制。这关上了"固定流水线"的解读（呼应 D5）。

**Layer 2 — 研究状态（领域，跨任务，Trellis 没有的新东西）**

由 `core` 从整棵 `.research/` 树**确定性计算**（非 LLM，可单测），每回合作为 `[research-state]` 块注入。聚合开放 gaps、任务图、推荐下一步研究活动——**只推荐，不自动建任务，无 conductor agent**。

### 4.2 两个注入块（示例）

```text
[workflow-state:in_progress]
Active task: {id}  (kind={kind}, venue={venue})
Goal: {prd.goal}
- [required · once] 派 rc-{kind} 执行器，带 prd.md + execute.jsonl 的 spec。
- [required · once] 执行器返回后，把任务转 verify（rc task set-status verify）。
不要内联做领域工作——那是执行器的职责。
[/workflow-state]
```
```text
[research-state]
Active: 2026-06-05-method-section (writing, in_progress)
Graph: 3 completed · 1 in_progress · 1 blocked(depends_on 2026-06-02-run-main-exp)
Open gaps（驱动下一步）:
  - [来自 writing] 缺 component X 的消融 → 建议: experiment
  - [来自 kind=review] 创新性主张缺支撑 → 建议: ideation 或 literature
Recommended next（你来定，不自动建）:
  1. 建 experiment 任务做消融 X（可解锁 Results 段）
  2. main-exp 完成后恢复被阻塞任务
[/research-state]
```

推荐逻辑是 `core` 的确定性启发式（gaps + 图 + 生命周期），LLM 只负责措辞与对话。忠实 Trellis（注入引导、无 orchestrator），且"下一步"可审计、可单测。

### 4.3 一个回合的数据流

1. 用户发话 → 平台 hook（或面包屑兜底）调 `rc context` → 注入 生命周期块 + research-state + 活动任务 spec 引用。
2. 主会话读注入态：`no_task`→直接答或推荐建任务；`in_progress`→派匹配执行器（带 prd + execute.jsonl）。执行器干活、写 artifacts、登记 gaps、返回。
3. 主会话转 `verify`→派 `rc-verify`。通过→`completed`（`rc-update-spec`+journal+commit/archive）；失败→回滚 `in_progress`。
4. research-state 重算→从 open gaps 推荐下一步→用户决定。

---

## 5. Agent 阵容

模板放 `research-kit/agents/`（平台中立），`rc init` 由 adapter 渲染成各平台原生格式（`.md`/`.toml`/workflow）。格式照 Trellis：frontmatter（role/tools/model）+ 指令（读 spec → 读 prd → 干活 → 自检 → 写 artifacts + 登记 gaps）。

**7 个研究执行器（对应 7 个 `kind`）**

| Agent | 职责 | 模型 | 主要 skill 来源 |
|---|---|---|---|
| `rc-literature` | 检索（scholar/pdf MCP）、锁 baseline、相关工作地图 | haiku | —（检索能力来自 mcp-scholar，见 §8.2） |
| `rc-ideation` | 头脑风暴、创新性分析、跨域类比、过滤排序、访谈 | opus | scientist-ideation, deep-interview |
| `rc-experiment` | 设计 run、起长任务（后台+monitor）、抽指标、对照 goal 判定 | sonnet | scientist-experiment-runner, scientist-plotting |
| `rc-writer` | 起草 LaTeX，只引用实验产出里真实存在的数字 | sonnet | paper-expand/shorten/translate/en2zh, paper-*-caption, paper-experiment-analysis, paper-architecture-web-drawing, scientist-writeup |
| `rc-polisher` | 润色 + 去 AI 味，不动任何技术内容 | sonnet | paper-polish, paper-deai |
| `rc-reviewer` | 模拟顶会审稿出报告 + 识别 gaps（gaps 回流任务图） | opus | paper-review/logic-check/sanity-check, scientist-review |
| `rc-rebuttal` | 解析审稿意见、起草循证回复、承诺补实验（派生 experiment 任务） | sonnet | —— |

**3 个生命周期助手（跨 kind，借 Trellis 的 brainstorm/check/update-spec）**

| Agent | 何时 | 职责 | 主要 skill 来源 |
|---|---|---|---|
| `rc-plan` | `planning` | 把任务澄清成 prd.md；curate execute/verify.jsonl | deep-interview, grill-with-docs |
| `rc-verify` | `verify` | kind 对应通用质量门（写作→数字溯源+逻辑；实验→指标溯源；润色→去AI检查+无技术改动 diff） | de-ai-checker, paper-sanity-check, paper-logic-check |
| `rc-update-spec` | `completed` | 把学到的（新 baseline、会议教训）提升进 spec/ | —— |

---

## 6. 上下文注入与多平台适配（基于已验证事实，见附录 A）

### 6.1 三类平台模型（采用 Trellis 的真实分类）

**逐回合注入并非所有平台都支持**，这决定了适配策略：

| 平台 | agent 定义 | 逐回合注入 | 机制 | MCP 配置 | Skills 路径 | 类 |
|---|---|---|---|---|---|---|
| Claude Code | `.claude/agents/*.md` | ✅ | `UserPromptSubmit` hook → `additionalContext` | `.mcp.json` | `.claude/skills/` | 1 |
| Codex | `.codex/agents/*.toml` | ✅* | `UserPromptSubmit` hook（需 `[features]hooks=true`） | `.codex/config.toml` `[mcp_servers.*]` | `.agents/skills/`（共享） | 1 |
| OpenCode | `.opencode/agent/*.md` | ✅ | JS 插件 `experimental.chat.system.transform`（进程内） | `opencode.json` `mcp` | `.opencode/skills/`（读 `.claude/skills/`） | 1 |
| Gemini CLI | `.gemini/agents/*.md` | ✅ | `BeforeAgent` hook → `additionalContext` | `.gemini/settings.json` `mcpServers` | `.gemini/skills/` 或 `.agents/skills/`（共享） | 1 |
| Cursor | `.cursor/agents/*.md`（也读 `.claude/agents/`） | ❌ | 仅 `sessionStart`/`postToolUse` 能注入；逐回合 hook 只放行/拦截 | `.cursor/mcp.json` | `.cursor/skills/` | 2 |
| Windsurf | 无 subagent（workflow+rule） | ❌ | `always_on` 规则静态；`pre_user_prompt` 只放行/拦截；MCP 仅全局 | `~/.codeium/windsurf/mcp_config.json`（全局） | 无原生（workflow） | 2 |

`*` Codex hooks 版本门控；旧版回退面包屑。

- **Class-1（push/hook）**：Claude Code / Codex / OpenCode / Gemini —— 钩子每回合注入计算出的状态块。
- **Class-2（pull/breadcrumb）**：Cursor / Windsurf —— 无逐回合注入；`sessionStart` 注入一次 + always-on 规则**强制 agent 每回合回显 `Active task: <path>` 面包屑**并重读状态。
- **agent-less 子类**：Windsurf 无 subagent，执行器降级为 inline workflow/rule。

### 6.2 注入机制：`rc context` 单一真相源

所有平台的注入归一到 `rc context --platform <X>`，输出注入块 =
```
[workflow-state:<当前生命周期态>]   ← 从 workflow.md 取（单一真相源，同 Trellis）
[research-state]                    ← 从任务图实时计算（4.2）
```
各平台钩子只是"在正确事件点调用它 + 把输出作为 additionalContext"的薄封装：

| 平台 | 接线 |
|---|---|
| Claude Code | `.claude/settings.json` → `UserPromptSubmit` 调 `rc context --inject` |
| Codex | `.codex/hooks.json` → `UserPromptSubmit`（+ `[features]hooks=true`） |
| Gemini | `.gemini/settings.json` → `BeforeAgent` hook |
| OpenCode | `.opencode/plugin/research-copilot.ts` → `chat.system.transform` 进程内调 `@research-copilot/core` |
| Cursor | `sessionStart` 注入一次 + `.cursor/rules/*.mdc(alwaysApply)` 强制面包屑协议 |
| Windsurf | `always_on` 规则 + 面包屑协议（MCP 写用户全局文件） |

**Windows 收益**：Trellis 钩子是 Python（Windows 需 `shell:powershell` 易踩坑）。我们的钩子统一调跨平台的 `rc`（Node CLI），只要在 PATH 上即可，绕开 Python-on-Windows 整类问题。

### 6.3 适配层架构（`packages/adapters`，照搬 Trellis 注册表模式）

```
packages/adapters/
├── registry.ts        # AI_TOOLS 注册表，每平台一条:
│   { id, configDir, cliFlag, agentCapable, hasHooks,
│     injectionClass: 1|2, hookRuntime: 'node'|'inline-plugin',
│     agentFormat: 'md'|'toml'|'none', mcpConfigPath, skillsPath }
├── templates/         # 平台中立规范源（agent/skill/workflow + 占位符）
│   占位符 {{CLI}} {{CMD_REF}} {{#AGENT_CAPABLE}} {{#HAS_HOOKS}}（同 Trellis）
└── configurators/     # 每平台一个 configure(): 中立模板 → 平台原生文件
    claude-code.ts / cursor.ts / codex.ts / opencode.ts / windsurf.ts / gemini.ts
```

执行器 agent 定义只写一份（平台中立），`configure()` 按平台渲染。新增平台 = 加一条注册表项 + 补模板差异。

### 6.4 CLI 命令面（`rc`）

```bash
rc init -u <name> [--claude --cursor --codex --opencode --windsurf --gemini]
                              # 铺 .research/ + 选中平台配置 + rc sync 拉 skillpacks
rc task create --kind <k> --title <t> [--venue V] [--parent P]   # 建研究任务
rc task start|verify|complete|archive <id>                       # 生命周期（对齐 task.py）
rc task add-context <id> --phase execute|verify --path <spec>    # curate 注入清单
rc task add-gap <id> --desc "..." --suggest <kind>               # 登记 gap（驱动推荐）
rc task add-subtask <parent> <child> | list | current | set-status   # 任务图
rc context [--platform X] [--inject]   # 输出每回合注入块（钩子调用）
rc sync                                # 按 skillpacks.yaml 拉取/渲染外部 skill 包
rc session add | rc spec add | rc doctor   # 日志/规范/自检（含 runtime 检查）
```

`rc task` 子命令对齐 Trellis 的 14 个 `task.py` 命令（create/add-context/start/current/finish/archive/add-subtask/list…），加 `--kind` 与 `add-gap` 两处研究扩展。

### 6.5 v1 平台范围

适配框架 + 注册表设计上支持 Trellis 全部 14 平台；**v1 落地已核实机制的 6 个**（Claude Code / Cursor / Codex / OpenCode / Windsurf / Gemini）。其余（Kiro / Qoder / CodeBuddy / Droid / Pi / Copilot / Kilo / Antigravity）是"填一条注册表 + 一套模板"的增量，列为里程碑 2。

---

## 7. MCP 服务器：6 Python → 2 TS

按职责重组，只保留"消费型外部检索"：

| 现服务器（Python） | 去向 |
|---|---|
| arxiv-search + arxivsub-search + google-scholar + dblp-bib | **合并为 `@research-copilot/mcp-scholar`**（TS）：统一工具 `scholar_search` / `scholar_metadata` / `bibtex`，内部多后端（arxiv / 顶会联合 / scholar 兜底 / dblp bibtex） |
| pdf-text | **`@research-copilot/mcp-pdf`**（TS）：`pdf_extract_text` / `pdf_extract_metadata`，用 `unpdf`/`pdfjs-dist` |
| ai-scientist（`validate_runtime` / `list_experiments` / `inspect_experiment`） | **退役**：`validate_runtime`→`rc doctor`；实验目录浏览→执行器用普通 Read/Glob（本就有文件权限，专设 MCP 冗余） |

**为什么只有检索走 MCP**：任务/状态操作走 `rc` CLI（shell），与 Trellis `task.py`、与 §6 注入设计一致；MCP 只留给外部检索。TS 实现用 `@modelcontextprotocol/sdk`；各平台 MCP 配置文件由 adapter 按 §6.1 表生成。

> 子决策（已确认"都可以"）：4 个检索服务器**合并成 1 个 mcp-scholar**（采纳，进程少、各平台配置简单）。

---

## 8. 代码 vs 内容；skill / spec 迁移

### 8.1 "TS 全栈"的边界

| 层 | 语言/格式 | 内容 |
|---|---|---|
| **代码**（重写 TS） | TypeScript | `core` / `cli` / `adapters` / `mcp-servers` |
| **内容**（平台可移植，不变 TS） | Markdown / 标准格式 | `agents` / `skills`(SKILL.md) / `spec` / `workflow.md` / `pipeline-templates` |

内容层本就是各平台消费的标准格式（Agent Skills 标准、agent markdown、spec markdown），由 adapters 渲染分发。

### 8.2 28 个自有 skill 的迁移处置

除 Windsurf 外所有目标平台都支持 Agent Skills（SKILL.md）标准，且有跨工具共享路径 `.agents/skills/`。skill **不重写**，只重新归属到对应 agent 并由 adapter 渲染：

| 现 skill（self/skills/） | 去向 |
|---|---|
| paper-polish, paper-deai | → rc-polisher |
| paper-expand, paper-shorten, paper-translate, paper-en2zh, paper-figure-caption, paper-table-caption, paper-experiment-analysis, paper-architecture-web-drawing | → rc-writer |
| paper-review, paper-logic-check, paper-sanity-check | → rc-reviewer（rc-verify 复用 sanity/logic） |
| scientist-ideation | → rc-ideation |
| scientist-experiment-runner, scientist-plotting | → rc-experiment |
| scientist-writeup | → rc-writer |
| scientist-review | → rc-reviewer |
| scientist-runtime-init | → `rc doctor`（CLI） |
| deep-interview | → rc-plan / rc-ideation |
| grill-with-docs | → rc-plan / rc-verify |
| de-ai-checker | → rc-verify（润色任务质量门） |
| init-mcp | → `rc init` / `rc doctor`（CLI） |
| research-workflow（原 hard gates） | → `.research/spec/`（作为 novelty/methodology 检查项，经 verify 门核验；非工具拦截）+ workflow.md |
| talk-normal | → spec/writing/（回复风格规范） |
| arxivsub-skill | → 并入 mcp-scholar 用法 |
| model-escalation | → agent 指令内置 |
| plugin-dev-agent-development | → **退役**（属旧插件架构） |

### 8.3 spec 初始内容（`research-kit/spec-templates/`）

- `venue/` — 各会议约定（页数/风格/审稿标准）
- `writing/` — 写作风格、术语表、引用政策、LaTeX 约定、回复风格（来自 talk-normal）
- `baselines/` — 锁定 baseline（创新性锚点）
- `methodology/` — 实验协议、指标定义、可复现规则
- `novelty/` — 创新性标准、相关工作地图、novelty 检查项（来自 research-workflow，经 verify 门核验，非工具级拦截）

`rc-update-spec` 在每个任务 Finish 时把新学到的沉淀回此——Trellis"写一次、跨会话注入"的研究版。

---

## 9. 外部依赖策略：rc 自管 skill-packs（D7）

### 9.1 问题

CC 的 `dependencies` + `allowCrossMarketplaceDependenciesOn` 是**Claude Code 独有的市场依赖机制**；其余 5 平台无等价物。现有架构靠它装 5–7 个外部插件 + vendored `third_party/` 合集（合计 100+ skill）。多平台下必须由我们自管。

### 9.2 机制

- `research-kit/skillpacks.yaml` 清单：每个外部来源（git URL / npm / 本地）+ 取哪些 skill（schema 见 §16.10）。
- `rc init` / `rc sync` 拉取每个包，渲染其 SKILL.md 到每个选中平台的 skills 路径（`.claude/skills/`、`.cursor/skills/`、共享 `.agents/skills/` 等）。
- 全 6 平台一致，版本锁定（`.runtime/skillpacks.lock`）；拉取产物默认在 `.runtime/`（gitignored）。
- **抛弃** CC 的 `plugin.json dependencies` / `marketplace.json` 依赖声明。
- **license-audit 不做（用户决定）**：包按原样拉取使用，不设许可门；如将本工具公开再分发，第三方包的许可合规由用户自行负责（本设计范围外）。

### 9.3 逐包留删清单（待用户勾选）

> 标注 **EVALUATE** 的包内容当前未在工作树中暴露（已 de-vendor 或为外部市场）；**在 v1 Phase 4 内由 `rc sync` 拉取后逐包定夺并纳入**；下列为基于用途与重叠的初步建议（拉取后核对修订）。

**第二层 vendored 合集（skill.txt）**

| 包 | 现用途 | 与自有重叠 | 初步建议 |
|---|---|---|---|
| humanizer | 去 AI 味 / 人性化 | paper-deai, de-ai-checker | DROP（重叠），独有技巧并入 paper-deai |
| auto-research(+skills-codex) | 自动化研究 | 流水线 | EVALUATE 核心；codex 变体 DROP（平台由 adapter 统管） |
| llm-wiki | 知识/wiki | 弱 | EVALUATE（多半 DROP） |
| mean-reviewer | 严苛审稿人设 | rc-reviewer | KEEP，并入 rc-reviewer 作"严审"校准 |
| master-cai/research-paper-writing | 论文写作 | rc-writer, paper-* | EVALUATE，并入有用部分 |
| k-dense-ai/scientific-skills | 科研技能集 | 部分 | EVALUATE |
| luwill | 个人合集 | 未知 | EVALUATE |
| lishix520/composer + strategist | 写作/策略 | rc-writer/rc-plan | EVALUATE |
| hkust-supervisor/phd-research | 博士研究指导 | rc-ideation/rc-plan | KEEP/EVALUATE |
| chenliu | 个人合集 | 未知 | EVALUATE |

**第三层 CC 插件依赖（plugin.json 1.0.3 + 构建脚本）**

| 包（市场） | 现用途 | 与自有重叠 | 初步建议 |
|---|---|---|---|
| academic-research-skills | 学术研究技能 | 全套重叠 | EVALUATE，保留独有 |
| paper-polish-workflow | 润色流程 | paper-polish, rc-polisher | DROP（重叠）/fold |
| superpowers (claude-plugins-official) | brainstorming/writing-plans/debugging | 开发流程类 | KEEP（可选 dev-process 包） |
| ml-paper-writing (ai-research-skills) | ML 论文写作 | rc-writer | EVALUATE/fold |
| autoresearch (ai-research-skills) | 自主研究 | 流水线 | EVALUATE |
| andrej-karpathy-skills (karpathy-skills) | karpathy 技能 | 弱 | EVALUATE |
| example-skills (anthropic-agent-skills) | 通用示例 | 弱 | DROP（通用示例） |

---

## 10. 强制哲学、质量门与错误处理（D8）

### 10.1 从"硬拒绝守卫"到"注入引导 + verify 门 + spec 规范"

- **不再有硬拒绝守卫**（废弃 `research_copilot_guard` / `copilot_write_guard`）。引导 = 注入的状态块 + agent 系统提示约束。
- **质量在 `verify` 状态门强制**：写作任务必须通过 `rc-verify`（数字溯源、引用合规）才能进 `completed`——状态转移门，由 verify agent + `core` 确定性检查把关，而非拦截工具。
- "不编造数字""引用只走 dblp/scholar"等 → 降级为 **spec 规范（注入）+ verify 检查**。
- 跨平台现实：6 平台中仅 Claude Code / Codex 有 PreToolUse，硬守卫本就无法多平台统一。
- **里程碑 2 备选**：在 Claude Code / Codex 上可加一层**只告警不拦截**的可选守卫作纵深防御（非 v1）。
- **收益**：推荐逻辑 + 质量检查从"LLM + hook"变为 `core` 确定性 TS，可单元测试。

### 10.2 错误处理与回滚

- **verify 失败 → 回滚任务到 in_progress**（Trellis rollback）。
- **注入失败**：`rc context` 优雅降级（退回"见 workflow.md"）；class-2 平台靠 `Active task:` 面包屑 + `rc task current` 永远能重解析活动任务。
- **长实验**：rc-experiment 用后台 + monitor（保留 loop-armer 思路为 agent 指令，非强制 hook）。
- **可溯源**：每个数字 → 实验产出文件，verify 校验；`task.json` 唯一真相源；`rc` 命令幂等；`.runtime/` 存会话指针。

---

## 11. 现有资产迁移路径（"抛弃架构"的落地）

| 现有资产 | 处置 |
|---|---|
| 6 Python MCP server | 重写 TS → 2 个（scholar / pdf）；ai-scientist 退役 |
| 28 self skill | 作内容保留，重新归属 rc-* 执行器 + spec（§8.2） |
| ②③ 外部/依赖 skill | skillpacks.yaml 拉取渲染（逐包留删 §9.3） |
| 7 copilot-* agent + conductor | 重建为 7 rc-* 执行器 + 3 助手；注入驱动，无 conductor |
| 7 hook 脚本（guard/write-guard/memory-injector/loop-armer/subagent-stop/scientist-guardrails/dispatch-reminder） | 整层废弃 → `rc context` 注入 + verify 门 + 轻量生命周期 hook |
| install.py | 废弃 → `rc init` / `rc doctor` |
| skill.txt/agent.txt/hook.txt + build_copilot_workspace.py | 废弃 → monorepo 构建 + adapters + `rc init` |
| dist/ 多渠道打包 + deploy 分支 | 废弃 → npm 发布 `rc` CLI |
| plugin.json/marketplace.json 依赖机制 | 废弃 → skillpacks.yaml |
| `.copilot/` 工作记忆 | 迁移概念 → `.research/`（tasks/spec/workspace） |

一句话：**编排层（agent/hook/状态机/conductor/构建/打包）整体替换；领域内容（skill/spec）与检索能力（MCP）迁移保留并重写**。

---

## 12. 构建与分发

- Monorepo：pnpm workspaces + tsup/tsc；`rc` 发布到 npm（`npx research-copilot` 或全局安装）。
- `rc init` 铺 `.research/` + 渲染选中平台配置 + 跑 `rc sync` 拉 skillpacks。
- CLI 即分发，不再有 dist/deploy 分支。
- 可选里程碑 2：再包一层 Claude Code 插件供市场安装。
- 版本：npm 包 semver。

---

## 13. 测试策略

- **core**（纯函数，最大测试价值）：任务模型、生命周期转移、research-state 计算、图/gap 逻辑、上下文构建器、skillpack 解析 —— 全单测（vitest）。
- **adapters**：每平台 `configure()` 输出对 golden 快照；注入分类行为断言。
- **mcp-servers**：对录制 fixtures 的集成测试（arxiv/scholar/dblp/pdf）。
- **cli**：e2e —— 临时目录跑 `rc init` 验证生成树、`rc task` 生命周期、`rc context` 各平台输出。
- **跨平台注入矩阵**：断言 class-1 出逐回合块、class-2 出面包屑协议。

---

## 14. 里程碑与分阶段交付

M1 不是单一计划——它含 4–5 个独立子系统（core / cli / 6 平台 adapter / 2 MCP / 10 agent + skillpack）。按硬依赖链拆成阶段，**每阶段一份独立实现计划**，每阶段有可种子化的验收：

- **Phase 0 — core + cli on Claude Code only（先证明环路）**
  - core：任务模型、生命周期 FSM、research-state 确定性计算（§16.1）、图/gap 派生、上下文构建器；cli：init/task/context/doctor；仅 Claude Code 一个 class-1 平台 adapter。
  - 验收（可种子化）：① 单测覆盖 research-state 启发式（§16.1 图形用例集）；② Claude Code 跑通 建任务→执行→verify→完成→推荐下一步；③ 种子一个"伪造数字"写作任务，verify 门拦下并回滚（§16.2）；④ 旧 `.copilot/` + Python 插件并行可用（cutover 检查点）。
- **Phase 1 — 其余 3 个 class-1 平台**（Codex / OpenCode / Gemini）经注册表接入；OpenCode 插件以子进程调 `rc context`（§16.6）。验收：注入矩阵断言三者出逐回合块；golden 快照；能力探测不过则降级面包屑。
- **Phase 2 — 2 个 class-2 平台**（Cursor / Windsurf）面包屑协议（§16.5）；**先为 1 个执行器（rc-writer）做 Windsurf inline-workflow 渲染 spike**，证明 neutral→native 降级可行再铺全部。验收：注入矩阵断言面包屑 + 新鲜度时间戳可检测陈旧。
- **Phase 3 — 2 个 TS MCP server**（scholar 门面 + pdf）。先做 PDF 阅读序 spike（§16.9 / 风险 6）与 scholar 各后端健康/降级矩阵再定稿。验收：录制 fixtures 集成测试 + 限流退避 + spawn round-trip 冒烟。
- **Phase 4 — skillpacks + 迁移**：`rc sync` 子命令**在本阶段早期先行**；v1 迁移 28 自有 skill **+ ②③ 外部包**——rc sync 拉取后逐包按 §9.3 curate 并纳入。验收：6 平台 skills 路径渲染一致（schema/流程见 §16.10）。

- **里程碑 2**：其余 8 平台 adapter；可选 CC 插件包装；可选"只告警不拦截"守卫。

> 阶段间存在硬依赖（core→cli→adapters→dogfood）；任一平台 schema 漂移不应阻塞整个 v1 验收——故验收按平台/能力分项（见 §13、§16.9），而非单一 e2e。

---

## 15. 风险与开放问题

**平台 / 注入**
1. **平台机制版本依赖**：Codex hooks（`[features]hooks=true`）、OpenCode `experimental.*` 插件 API、Gemini hooks/skills 均为新/preview，schema 可能随版本变。对策：注册表记最低版本矩阵，`rc doctor` 探测能力并降级面包屑；preview API 上的 class-1 平台标"best-effort，面包屑兜底保证"。
2. **多平台回归维护负担**：6 adapter × 3 preview API = 持续 golden 快照维护负担，非一次性成本。对策：能力探测门控快照（上游漂移→降级而非 CI 失败）；v1 *验收* 收窄到 Claude Code + 1 个第二平台，其余 4 个"已接线、验收延后"。
3. **class-2 无逐回合注入 + 新鲜度（Cursor/Windsurf）**：面包屑依赖模型自觉调 `rc context`，不调则 research-state 静默陈旧。对策：`rc context` 内嵌 turn 时间戳，agent 与 `rc doctor` 可发现未刷新；class-2 新鲜度列 best-effort 而非保证。
4. **agent 格式 / 能力分歧**：Windsurf 无 subagent——10 个 rc-* 须重表达为 inline workflow/rule（无隔离上下文、无 per-agent model/tool）。"写一份中立 agent 渲染各平台"对 agent-less 平台未必成立。对策：Phase 2 先 spike 1 个执行器的 Windsurf 降级；§5 明确 agent-less 平台丢失哪些能力、verify 质量如何在无隔离 verify subagent 下保持。

**工程**
5. **scholar 4 后端异构（major）**：arXiv Atom XML / arxivsub（第三方 Supabase 网关，有每日配额、可被对方关停）/ Google Scholar HTML 爬虫（已自限 1–3 条、有 CAPTCHA 封禁）/ DBLP——失败模式互不兼容、结果 schema 各异。对策：mcp-scholar 做**薄门面**，每后端独立限流/退避/熔断/cookie 管理 + 来源标注的归一结果；**v1 保留全部 4 后端（含 Google Scholar）**——CAPTCHA/封禁时仅该后端降级、其余不受影响；标注 Google Scholar 为 best-effort（Google markup 变更需维护）；spec 增每后端能力/健康/降级矩阵。
6. **TS PDF 阅读序回归（major）**：`unpdf`/`pdfjs-dist` 的 `getTextContent` 按内容流序返回，对**双栏会议论文**会交错两栏、毁公式/表结构——而这正是 rc-writer/rc-verify"数字溯源"依赖的语料。对策：Phase 3 前在真实双栏 ICLR/CVPR PDF 上做阅读序 spike；备选 (a) 纯 TS 的 x/y 聚类分栏启发式 / (b) 保留 Python pdfplumber sidecar（与"TS 全栈"冲突，诚实标注）/ (c) mcp-pdf 只做粗文本、抽取数字视为 advisory。**已定：Phase 3 先 spike (a)；达标用 (a) 守住 TS 全栈，不达标退 (b) Python sidecar。**
7. **OpenCode 版本耦合**：进程内 import core 会冻结版本 + 给用户仓库引入 node_modules（违背"干净仓库"）。对策（§16.6）：插件以**子进程**调 `rc context`，全平台单一注入路径；`rc doctor` 校验版本。
8. **configure() 幂等/合并**：用户仓库可能已有自带配置，整文件覆盖会毁之。对策（§16.6）：按文件类型定义合并策略；增"对已含外来配置的仓库重跑 configure() 不破坏"测试。
9. **Windows rc-on-PATH**：npm 全局 bin 在 Windows 是 `rc.cmd`/`rc.ps1` shim，hook 非 shell spawn `rc` 可能失败。对策：`rc doctor` 实测从非 shell spawn 执行 shim，文档给 `npx` 兜底；MCP server 调用用 `npx -y @research-copilot/mcp-*` 或绝对路径。
10. **research-state 每回合全树扫描延迟**：`UserPromptSubmit` 预算紧（CC 默认 30s）。对策（§16.1）：派生索引 `.runtime/graph-index.json`，由 task.json mtime/`rc task` 变更失效；`rc context` 读索引。每回合延迟列为 §13 非功能需求。
11. **MCP 打包**：`pdfjs-dist` 是 ESM + worker（部分含 wasm/canvas），naive bundling 易坏 worker 解析。对策：固定 Node engines floor、选定 server 调用形式、增 spawn round-trip 冒烟、标准化前验证 pdfjs worker/legacy 构建。

**供应链 / 流程**
12. **license（用户决定忽略 audit）**：按用户决定，v1 **不做 license-audit**，②③ 包按原样拉取使用。残留风险（记录在案，已接受）：若将本工具公开再分发，第三方包的许可合规由用户负责；本设计不设许可门。
13. **dogfood 自举循环**：仓库要先造出 rc 才能在自身 `.research/` dogfood，而仓库又是被造对象；同时 §11 上来就退役旧 Python 工具链，留迁移期工具真空。对策：旧 `.copilot/` + Python 插件并行可用至 Phase 0 落地，定明确 cutover 检查点；首个 dogfood 目标设为一个极小任务，Phase 0 落地即可观测。
14. **EVALUATE 类外部包**：内容未核实，留待 `rc sync` + license-audit 后逐包定夺（§9.3），与 §14 Phase 4 绑定。

---

## 16. 核心算法、文件格式与契约（实现契约）

> 本节补全评审指出的实现盲区：把"确定性 core 逻辑 / 注入 / skillpack / verify 门"从概念落到可编码、可单测的契约。

### 16.1 research-state 推荐算法（core 纯函数）

签名：`computeResearchState(tree): ResearchStateBlock`。输入：全树 `task.json`；大项目读派生索引 `.runtime/graph-index.json`（由 task.json mtime 失效）而非重扫。

确定性步骤：
1. **图构建**：节点=任务，边=`depends_on`；标记 `blocked = 任一 depends_on 未 completed`。
2. **候选动作**：(a) 所有 `status≠completed` 且未 blocked 的任务 → "resume 此任务"；(b) 所有 open gap → "按 `suggest_kind` 建新任务"，附 `unblocking_potential = 解决该 gap 能解锁的下游任务数`。
3. **打分**（降序）：`score = w1·priorityRank(P0=3..P3=0) + w2·unblocking_potential + w3·lifecycleBonus(in_progress>verify>planning) + w4·age`；权重为常量、可配置、单测固定。
4. **平局**：先 priority，再 unblocking_potential，再 `task.id` 字典序（完全确定）。
5. **输出**：取前 N=3，每项 `{action:'resume'|'create', taskId?|suggestKind, reason, sourceGap?}` + 图摘要（completed/in_progress/blocked 计数）+ open gaps 清单 + `turn-ts`。
6. **边界**：0 open gap 且无未完任务 → "无推荐，可建新任务或归档"；多活动任务 → 全列、按 score 排。

附 1 个 worked example（进单测 fixture）：3 任务 + 1 open gap 的树 → 产出 §4.2 的块。

### 16.2 verify 门检查（按 kind）

标注 **[det]**=core 确定性 TS / **[llm]**=verify agent 判断。任一 [det] 失败 → verify 失败 → 回滚 in_progress + 结构化失败报告。

| kind | 检查 | 类型 | 通过条件 |
|---|---|---|---|
| writing | number-traceability：draft 每个数值 token 须在本任务/依赖任务 `artifacts/` run 输出精确匹配 | [det] | 无未匹配数值（规范化后字符串相等，容差在 spec/methodology 定义） |
| writing | citation-compliance：每个 `\cite{key}` 须存在于 mcp-scholar 产出 bibtex | [det] | 无悬空 cite |
| writing | 逻辑/术语一致 | [llm] | agent 判定通过 |
| experiment | metric-traceability：每个上报指标对应一条日志行 | [det] | 无凭空指标 |
| polish | no-technical-change：润色前后"技术 token diff"（数字/公式/cite/术语集合不变） | [det] | 技术 token 集合零变更 |
| polish | de-AI 检查（de-ai-checker 评分） | [llm] | 评分 ≥ 阈值（spec/writing 定义） |
| literature | baseline 锁定项含 paper id+claim+来源；相关工作 ≥ 阈值条且各有 distance | [det] | 字段完备 |
| ideation | 选定方向含 falsification claim + ≥N 近邻先验工作 | [det]+[llm] | 字段完备 + agent 判非拼凑 |
| review | 审稿报告每条 weakness 映射到一个 gap（带 suggest_kind） | [det] | 每 weakness 有 gap |
| rebuttal | 每条审稿意见有回应块；承诺补实验的已登记为 gap(suggest_kind=experiment) | [det] | 覆盖完备 |

### 16.3 文件格式契约

- **execute.jsonl**（注入执行器）：每行 `{"type":"spec"|"context","path":"...","reason":"..."}` —— spec/上下文**引用**。
- **verify.jsonl**（注入 verify 步）：每行 `{"check":"number-traceability|...","kind":"writing","args":{...}}` —— **检查项**。两者 schema 不同。
- **prd.md**：必含 `# <title>` + `## Goal`（首段即 `prd.goal`，被 §4.2 注入引用）/ `## Scope` / `## Success criteria` / `## Out of scope`。
- **workflow.md 块语法**：`[workflow-state:<STATE>] … [/workflow-state]`，core parser 按这对定界符精确提取当前 STATE 块（单一真相源 → 此格式即 API）；STATE ∈ {no_task,planning,in_progress,verify,completed}。
- **config.yaml** 键/类型/默认：`session_commit_message`(str)、`max_journal_lines`(int=2000)、`default_venue`(str?)、`packages`(monorepo)、`lifecycle_hooks`(见 16.4)。
- **config.defaults.yaml**：research-kit 出厂默认，`rc init` 合并进用户 `.research/config.yaml`。

### 16.4 生命周期 hook 配置（config.yaml）

```yaml
lifecycle_hooks:
  after_create:   [ "shell 命令，收 TASK_JSON_PATH 环境变量" ]
  after_start:    [ ... ]
  after_verify:   [ ... ]   # verify 通过后
  after_complete: [ ... ]
  after_archive:  [ ... ]
```
失败只告警不阻断（同 Trellis）。注意：这是**任务生命周期 hook**（config.yaml，跨平台、由 `rc` 触发），与**平台注入 hook**（§6，各平台原生）是两回事。

### 16.5 面包屑协议契约（class-2：Cursor/Windsurf）

- always-on 规则文本（adapter 渲染）要求 agent：**每回合**先运行 `rc context --platform <X>` 并把输出当作当前状态；产出末尾回显一行 `Active task: <task-id>`。
- `rc context` 输出内嵌 `turn-ts:<ISO>`；agent / `rc doctor` 据此发现"未刷新"→ 提示用户（新鲜度 best-effort）。
- §13 注入矩阵断言：class-2 渲染出"每回合调 `rc context` + 回显 `Active task:`"的规则文本，且输出含 `turn-ts`。

### 16.6 注入与适配的工程契约

- **`rc context` 输出格式**：`--format text|json`，adapter 按平台选——Claude Code/Codex 用 text（直接作 additionalContext）；Gemini 用 json（hook stdout 须纯 JSON `{"hookSpecificOutput":{...,"additionalContext":"..."}}`）。同一计算、两种封装，解"raw-text vs pure-JSON"冲突。
- **OpenCode 注入**：`.opencode/plugin/research-copilot.ts` 以**子进程** spawn `rc context --platform opencode`（不进程内 import core），保持全平台单一注入路径、避免版本漂移。
- **configure() 合并策略**（幂等、非破坏）：`.claude/settings.json`/`.gemini/settings.json`/`opencode.json` → JSON 命名空间深合并；`.codex/config.toml` → section 插入；`.cursor/rules/*.mdc`/`.windsurf/rules` → 追加独立文件。除 golden 快照外，增"对已含外来配置的仓库重跑 configure() 不破坏"测试。
- **MCP server 调用形式**：各平台 MCP 配置用 `npx -y @research-copilot/mcp-scholar` 或 `rc init` 写入的绝对路径，非裸命令名（Windows 安全）。

### 16.7 pipeline-templates 语义（与 D5 调和）

模板**不批量建任务、不锁顺序**。`rc pipeline apply <name>` 只产出一组**建议 gap**（进 research-state 推荐池或一个 seed 任务的 `gaps[]`），用户**逐项接受**才建任务（呼应 §4.2"推荐不自动建"）。模板文件 = `{name, description, suggested_gaps:[{desc,suggest_kind}], notes}`。即"起点建议"而非"固定流水线"。v1 纳入与否：列为 Phase 4 可选。

### 16.8 rc task ↔ Trellis task.py 命令映射

| rc task | 对应 task.py | 说明 |
|---|---|---|
| create | create | 加 `--kind` |
| start / verify / complete | start /（review）/ finish | verify 取代 review 名 |
| archive | archive | |
| add-context | add-context | `--phase execute|verify` |
| add-gap | （新增） | 研究扩展 |
| add-subtask / list / current / set-status | add-subtask / list / current / set-branch 等 | set-status 校验 §4.1 FSM 合法转移，拒非法跳转 |

未直接保留：set-base-branch / set-scope / list-archive / remove-subtask / list-context / validate（按需里程碑 2 补）。

### 16.9 CLI I/O 契约（节选）

- 所有 `rc` 命令：成功 exit 0，用法错 2，运行错 1；人读输出 → stdout，诊断 → stderr。
- `rc context --inject --format <text|json>`：见 16.6。
- `rc doctor`：逐平台探测（agent 文件可写、hook 事件可用、MCP 配置就位、`rc` shim 可执行、Phase 3 起 MCP server spawn round-trip）；任一关键项失败 exit 1 并列修复建议。
- `rc task set-status <id> <state>`：校验目标 state 是 §4.1 FSM 合法后继，否则拒绝（exit 2）。

### 16.10 skillpacks.yaml schema 与 rc sync 渲染

```yaml
packs:
  - name: humanizer
    source: { type: git, url: "https://github.com/.../humanizer", ref: "<commit|tag>" }
    # 或 source: { type: npm, name: "<pkg>", version: "x.y.z" } / { type: local, path: "../foo" }
    include: ["skills/**"]            # 选取 glob（默认全选）
    exclude: ["**/skills-codex/**"]   # 可选排除
    map_to_agent: rc-polisher         # 可选：归属某执行器（影响渲染分类）
    notes: "..."
```

`rc sync` 流程（幂等）：
1. 解析 `packs`；逐包按 `source` 拉取到 `.runtime/skillpacks/<name>/`（git `clone --depth 1` / npm pack / 本地拷贝）。
2. 按 `include`/`exclude` 选出 SKILL.md 目录。
3. 渲染：把每个 SKILL.md 目录复制到每个选中平台的 skills 路径（§6.1 注册表 `skillsPath`；Windsurf 无原生 skills → 降级为 `.windsurf/workflows/`）。
4. 版本锁：把每包 resolved ref/version 写 `.runtime/skillpacks.lock`。
5. `--check` 只报告差异不写盘；重跑覆盖渲染产物（不污染用户已有 skills，按命名空间子目录隔离）。
6. 拉取与渲染产物默认在 `.runtime/`（gitignored，不提交）。

---

## 17. 文档交付物（随每个 Phase 增量，是各 Phase 验收的一部分）

每个阶段的实现计划都必须含对应的文档任务；**缺对应文档的 Phase 不算验收通过**，文档与代码同 PR 增量。

- **README（根，每阶段更新）**：项目简介、安装（`npx research-copilot` / 全局安装）、`rc` 命令速览、平台支持矩阵（已落地 / 已接线 / 计划中）、与旧架构的关系、链到使用与开发文档。
- **使用文档 `docs/usage/`（面向研究者）**：`rc init`/`task`/`context`/`sync`/`doctor` 逐命令用法与示例；研究工作流走查（建任务→执行→verify→完成→推荐下一步，含实例）；6 平台各一节的接入指南（注入/面包屑差异、如何配 hook/规则）；spec（venue/baselines/writing/methodology/novelty）怎么写；`skillpacks.yaml` 怎么配。
- **接续开发文档 `docs/dev/`（面向后续开发者）**：架构总览（对照本 spec §3–§6）；`core` API 参考；**如何新增一个平台 adapter**（注册表项 + 模板 + configurator，直接服务里程碑 2 的 8 平台）；如何新增/改 MCP server；如何新增研究 `kind` / 执行器 / verify 检查 / research-state 规则；测试怎么跑（vitest / golden 快照 / e2e / 注入矩阵）；本地 dogfood 指南；决策记录（ADR，链接本 spec）。

---

## 附录 A：已验证的各平台机制（2026-06-05 核实）

> 来源：6 平台官方文档 + Trellis 源码逆向（见各平台 sources）。下列为适配设计的事实依据；标注的 caveat 已并入 §15 风险。

- **Claude Code**：subagent `.claude/agents/*.md`（frontmatter name/description/tools/model）；逐回合注入 `UserPromptSubmit` hook（stdout 或 `hookSpecificOutput.additionalContext`），默认 30s 超时；MCP `.mcp.json`（项目级，需一次性批准）；原生 skills `.claude/skills/<name>/SKILL.md`。CLAUDE.md/rules 仅 session start 加载，不适合逐回合态。Windows hook 需 `shell:powershell`（我们改调 `rc` Node CLI 规避）。
- **Codex**：subagent `.codex/agents/*.toml`（flat TOML，`developer_instructions`）；逐回合 `UserPromptSubmit` hook 需 `[features]hooks=true`（版本门控），hook 定义在 `.codex/hooks.json`（或 `config.toml` 内联 `[hooks]`）；MCP `~/.codex/config.toml` 或 `.codex/config.toml` `[mcp_servers.*]`；skills 在 `.agents/skills/`（注意非 `.codex/skills/`）。旧版无 hooks → 回退面包屑。
- **OpenCode**：agent `.opencode/agent/*.md`（`mode: primary|subagent|all`）；逐回合注入靠 JS/TS 插件 `experimental.chat.system.transform`（进程内改 system 数组）—— `experimental.*` 前缀，版本可能变；MCP `opencode.json` `mcp` 键（local/remote）；skills `.opencode/skills/`（也读 `.claude/skills/`）。
- **Gemini CLI**：subagent `.gemini/agents/*.md`；逐回合注入 `BeforeAgent` hook → `hookSpecificOutput.additionalContext`（preview）；MCP `.gemini/settings.json` `mcpServers`（服务器名禁用下划线）；原生 Agent Skills `.gemini/skills/` 或共享 `.agents/skills/`，`activate_skill` 触发。hook stdout 须纯 JSON。
- **Cursor**：subagent `.cursor/agents/*.md`（也读 `.claude/agents/`）；**无逐回合注入**——`beforeSubmitPrompt` 只放行/拦截，仅 `sessionStart`/`postToolUse` 支持 `additional_context`；规则文件 `.cursor/rules/*.mdc`（frontmatter `alwaysApply: true`）；MCP `.cursor/mcp.json`；skills `.cursor/skills/`（Agent Skills 标准）。对策：always-apply 规则 + 面包屑。
- **Windsurf**：无 file-defined subagent（用 `.windsurf/workflows/*.md` + `.windsurf/rules/*.md`）；**无逐回合计算注入**——`always_on` 规则静态，`pre_user_prompt` 只放行/拦截；MCP `~/.codeium/windsurf/mcp_config.json`（仅全局）；无原生 skills（workflow 代替）。post-Cognition 路径向 `.devin/*` 迁移。对策：always_on 规则 + 面包屑。
- **Trellis 参照**：4 个共享 hook（session-start / inject-workflow-state[逐回合] / inject-subagent-context[push] / inject-shell-session-context[shell 桥]）；`SHARED_HOOKS_BY_PLATFORM` 按平台接线；canonical agent 在 `.trellis/agents/*.md` 渲染各平台；class-1 push vs class-2 pull（`Active task:` 面包屑 + `buildPullBasedPrelude`）；`AI_TOOLS` 注册表（configDir/cliFlag/agentCapable/hasHooks/supportsAgentSkills）；Codex `dispatch_mode: inline|sub-agent` 旋钮；hook 脚本 Python（多数）/JS（OpenCode）/TS（Pi）。
