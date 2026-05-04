# Research Copilot Agent 重设计

- 日期: 2026-05-05
- 范围: `self/agents/`（5 → 8 重写）+ `.copilot/`（新增）+ socket 超时缓解
- 状态: 已批准，进入实施

## 背景

`self/agents/` 现有 5 个 agent (`research-pilot` / `paper` / `paper-writer` / `paper-reviewer` / `scientist`)，存在以下问题：

1. **两个总控**（`research-pilot` 与 `paper`）边界模糊，切换条件"是否有第一稿"难以判断。
2. **创新点挖掘双份实现**：`research-pilot` Stage 2/3 与 `paper` Mode 3 重复定义 6 维度头脑风暴。
3. **润色无独立 agent**：被塞进 `paper-writer`（通过 `paper-polish` skill）。
4. **rebuttal 无独立 agent**：被塞进 `paper-reviewer` 自检模式。
5. **实验运行外包**：依赖 `third_party/experiment-driver`，`self/` 内无对应 agent。
6. **`scientist` 与主线断裂**：AI-Scientist-v2 自动流水线和交互式主流程互不通。
7. **agent 调用易卡 socket 超时**：嵌套 Task、硬编码 MCP 优先级、长任务无 background 模式累积导致。

## 设计决策

| # | 决策 |
|---|---|
| 1 | 删除旧 5 个 agent，重写为 1 总控 + 7 子 agent，覆盖文献调研 / 创新点构思 / 实验运行 / 写作 / 润色 / 审阅 / rebuttal |
| 2 | 总控命名 `research-copilot`，子 agent 加 `copilot-` 前缀 |
| 3 | 子 agent 双暴露：可被总控委派，也可被用户 `@<name>` 直调 |
| 4 | 子 agent 之间**绝不互相 Task 调用**（避免嵌套→超时）；可在响应末尾输出"建议下一步"软建议 |
| 5 | 子 agent frontmatter 不写 `tools` 字段（拥有全部默认工具）；**不硬编码** skill / MCP / 其他 agent 名字（用能力短语描述，让模型自动匹配） |
| 6 | 总控混合工作模式：默认路由（单次诊断+委派）；用户明说时启动管道（多阶段串行+审批门） |
| 7 | 持久化记忆放 `.copilot/`，写权限分区（每个文件只允许特定 agent 写），`handoff.md` 允许追加；默认进 `.gitignore` |
| 8 | scientist agent 整合到新架构（其 6 阶段能力归并到对应子 agent + 已有 skill），不保留独立轨道 |

## 文件结构

```
self/agents/                            (1 总控 + 7 子 = 8 个 .agent.md)
├── research-copilot.agent.md           🧭 总控
├── copilot-literature.agent.md         📚 文献调研
├── copilot-ideation.agent.md           💡 创新点交互构思
├── copilot-experiment.agent.md         🧪 实验运行与验证
├── copilot-writer.agent.md             ✍️  论文写作
├── copilot-polisher.agent.md           ✨ 论文润色
├── copilot-reviewer.agent.md           🔍 论文审阅
└── copilot-rebuttal.agent.md           💬 rebuttal 回复

.copilot/                               (跨会话工作记忆，写权限分区)
├── state.md                            研究状态游标            ← 仅 research-copilot 写
├── literature.md                       文献库                  ← 仅 copilot-literature 写
├── ideas.md                            创新点候选与决策        ← 仅 copilot-ideation 写
├── experiments.md                      实验流水                ← 仅 copilot-experiment 写
├── handoff.md                          子 agent 间事实交接     ← writer/polisher/reviewer/rebuttal 追加
├── decisions.md                        每个审批门决策记录      ← 仅 research-copilot 写
└── reviews/round-N.md                  审稿落盘                ← 仅 copilot-reviewer 写
```

## 总控 `research-copilot` 设计要点

**角色定位**：流程守卫者，规范"文献→创新点→实验→写作→润色→审阅→rebuttal"的合理推进。

**两种模式**：

- **A 路由（默认）**：扫 `.copilot/state.md` → 一句话诊断 → 一句话推荐 → 委派或停下。
- **B 管道**：用户明说"全流程"/"通篇优化"/"投稿冲刺"/"rebuttal 准备"/"创新点重校"/"自定义序列"时，按预设模板串行委派，每段间审批门。

**预设管道模板**：

| 模板 | 序列 |
|---|---|
| 完整研究 | S1→S2→S3→S4→S5→S6→S7 |
| 投稿前综合优化 | 通读 → S4 扩缩 → S5 润色 → S5 去 AI 味 → S6 终审 |
| rebuttal 准备 | S6 自检 → S7 草稿 → S6 复审 → S7 定稿 |
| 创新点重校 | S2 → S3 快速验证 → 回 S2 或进 S4 |
| 自定义 | 用户指定序列 |

**委派模板（强制 6 项）**：背景与阶段 / 本轮目标 / 可用事实 / 硬约束 / 期望输出 / 停止条件。

**子 agent 输出回收自审清单**：是否真正回答原问题 / 是否基于可验证事实 / 是否留下立即风险 / 下一步是继续委派还是整合 / 子 agent 软建议是否合理。

## 7 子 agent 矩阵

| 子 agent | 定位 | 主要写文件 | 典型转接建议 |
|---|---|---|---|
| copilot-literature | 文献调研专员，构建结构化文献库 | `.copilot/literature.md` | → @copilot-ideation 挑创新点方向 |
| copilot-ideation | 创新点交互构思伙伴，多轮 AskUserQuestion + 6 维度 + 跨领域类比 + 5 项审稿筛选 | `.copilot/ideas.md` | → @copilot-experiment 验证 / 回 @copilot-literature 补文献 |
| copilot-experiment | 实验执行者，设计→改代码→跑训练→读结果→判读 | `.copilot/experiments.md` + 训练代码/log/图 | → @copilot-writer 起草 / 自己继续迭代 / 回 @copilot-ideation |
| copilot-writer | 把已有事实转成顶会规范正文 | `sections/*.tex`、`references.bib`、`.copilot/handoff.md` | → @copilot-polisher / @copilot-reviewer |
| copilot-polisher | 学术化润色 + 去 AI 味，不改技术内容 | tex 章节、`.copilot/handoff.md` | → @copilot-reviewer 验证 |
| copilot-reviewer | 资深顶会审稿人视角，默认只读，7 维度 + 三级分级 | `.copilot/reviews/round-N.md`、`.copilot/handoff.md` | Verdict=ready→投 / almost→@copilot-writer+polisher / not-ready→回实验或创新点 |
| copilot-rebuttal | rebuttal 回复起草，把 reviewer 批评转成有据回复 | `rebuttal/round-N.md`、`.copilot/handoff.md` | 需补实验→@copilot-experiment / 补章节→@copilot-writer / 写完→@copilot-reviewer 自洽性检验 |

## `.copilot/` schema 详见各 agent 文件与初始化骨架

`state.md` / `literature.md` / `ideas.md` / `experiments.md` / `handoff.md` / `decisions.md` / `reviews/round-N.md` 各文件 schema 在对应 agent 文件正文中规定。`.copilot/` 目录由总控首次调用时初始化；子 agent 找不到自己应写的文件时**停下汇报**，不擅自创建。

## Socket 超时缓解（独立于新架构）

新架构本身已经缓解大部分（无嵌套 Task / 无硬编码 MCP 优先级 / `copilot-experiment` 强制 background）。额外做：

1. `self/scripts/diagnose-mcp.py`：单独测每个 MCP server 的初始化时长 + 典型查询时长，定位最慢 server。
2. `.mcp.json` env 增加 `PYTHONFAULTHANDLER=1`、`OMP_NUM_THREADS=1`（防 numpy 多线程在 Windows 死锁；卡死时 stderr 打 traceback）。
3. 各 agent 硬约束补："长任务必须 `run_in_background=true`，不要阻塞主会话"。
4. 各 agent 硬约束补："WebFetch 单次超过 30s 立即放弃，回退到 WebSearch 摘要"。
5. （可选，未来）MCP server 加 timing wrapper 落盘 `.copilot/.mcp-timing.log`。

## 实施步骤

1. 删除旧 5 agent 文件
2. 写 8 个新 agent 文件
3. 创建 `.copilot/` 骨架 + 加 `.gitignore` 条目
4. 更新 `self/README.md` + `self/AGENTS.md`
5. 写 `self/scripts/diagnose-mcp.py`
6. 修改 `self/install.py` 给 `.mcp.json` 加 env (`PYTHONFAULTHANDLER` / `OMP_NUM_THREADS`)
7. 自验：`python self/install.py --skip-deps` 跑通；`python self/scripts/diagnose-mcp.py` 看响应时间

## YAGNI 边界（不做的事）

- 不重写任何 skill（23 个保留，仅在 agent 描述里以"能力"形式被引用，不硬编码具体名字）
- 不重写 MCP server（除增加 env 变量）
- 不动 hooks（与 agent 设计无关）
- 不强制 `.copilot/` 进 git（默认 ignore，用户决定）
- 不保留旧 5 个 agent 文件（用户明确指示直接改）
- 不写回退脚本（用户明确指示不需要）
