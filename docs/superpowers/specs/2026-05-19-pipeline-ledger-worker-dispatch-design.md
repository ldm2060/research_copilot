# Pipeline Ledger + Worker Dispatch 设计

- 日期: 2026-05-19
- 范围: `self/agents/` 的 `research-copilot` 与 7 个 `copilot-*` 子 agent；新增或整理 `plugin-dev:agent-development` 类技能；新增 `.copilot/pipelines/` 工作记录约定
- 状态: 用户已批准设计，等待 implementation plan

## 背景

当前 `self/agents/` 已经采用 1 个总控 `research-copilot` + 7 个 `copilot-*` 子 agent 的结构。这个结构解决了旧版多总控、职责重叠、长任务阻塞和跨阶段不清的问题，但实际使用时仍有一个明显痛点：单个子 agent 往往在同一会话上下文里完成需求分析、方案制定、代码或文本修改、实验输出、验证和总结。结果是方案、执行痕迹、日志、diff、判断和用户可读摘要混在一起，主会话很难阅读，也不利于后续追踪。

本设计把 `copilot-*` 子 agent 从单纯执行者升级为 stage-local coordinator：每轮先写流水线计划，再把窄任务交给 worker sub-agent，最后由父 agent 回收、审核、落盘和汇报。

## 目标

1. 每轮工作先有明确的流水线计划，而不是边想边做。
2. 子 agent 可以派发 worker sub-agent，但派发必须受控、可追踪、可审核。
3. 方案、worker 输出、验证证据和最终摘要分层存放，避免主会话上下文污染。
4. `.copilot/pipelines/` 记录每轮工作如何发生；原有 `.copilot/*.md` 继续记录长期事实。
5. 保留 `research-copilot` 对跨阶段推进、审批门和 back-edge 的唯一调度权。
6. 为 `plugin-dev:agent-development` 类技能沉淀同一套 agent / skill 开发工作流。

## 非目标

- 不在本设计阶段直接重写 agent 文件。
- 不改变现有 7 个研究阶段的语义：S1 literature、S2 ideation、S3 experiment、S4 writing、S5 polishing、S6 review、S7 rebuttal。
- 不让 worker sub-agent 直接推进全局阶段或绕过 `research-copilot`。
- 不把 `.copilot/pipelines/` 变成长期事实库；长期事实仍写入对应 stage 文件。
- 不引入每个 worker 单独一个 task 文件的复杂账本，除非后续实践证明单文件 pipeline ledger 不够用。

## 设计决策

| # | 决策 |
|---|---|
| 1 | 保留 `research-copilot` 作为全局 conductor，只负责阶段判断、审批门、跨阶段派发和 back-edge gate。 |
| 2 | 将每个 `copilot-*` 子 agent 定义为 stage-local coordinator：先写本轮 pipeline ledger，再派 worker 或执行本阶段协调工作。 |
| 3 | 取消“子 agent 绝不 Task 其他 agent”的绝对铁律，改为“子 agent 可以派窄作用域 worker，但跨阶段调度只能回到 `research-copilot`”。 |
| 4 | 新增 `.copilot/pipelines/`，每轮一份 ledger，记录 intake、计划、任务拆分、派发、worker 返回、父级审核、阶段输出。 |
| 5 | worker 输出不直接进入主会话；父级 `copilot-*` 必须先回收、审核、压缩和落盘。 |
| 6 | 并行 worker 只允许用于读写范围不重叠、输出可独立验证、失败不会污染其他任务的工作。 |
| 7 | 每个 worker prompt 必须包含六字段：Context & stage、This worker's goal、Available facts、Hard constraints、Expected output、Stop condition。 |
| 8 | `plugin-dev:agent-development` 类技能复用同一套“需求澄清 → 设计 → ledger → worker 派发 → coordinator review → 验证 → 文档更新”流程。 |

## 总体架构

```text
user
  ↓
research-copilot
  ↓
copilot-* stage coordinator
  ↓
narrow worker sub-agents
```

`research-copilot` 仍是全局流程守卫者。它读取 `.copilot/state.md`、判断当前阶段、选择哪个 `copilot-*` 子 agent、处理用户审批门、控制 back-edge，并维护 `.copilot/decisions.md` 与 `.copilot/state.md`。它不直接写论文、跑实验、做 review 或管理某个阶段内部的 worker。

每个 `copilot-*` 子 agent 接到任务后，第一步必须创建本轮 pipeline ledger，至少写完 intake、round plan 和 task breakdown。之后它可以自行完成小规模协调工作，也可以派发 worker sub-agent。worker 只做单一窄任务，例如抽取一段日志中的 metric、核验一组 citation、检查一个 section 的 claim-evidence 对齐、生成一个局部图表或改一个限定段落。

worker 不决定全局下一步，不直接输出给用户作为最终结论，不跨阶段派发其他 agent。父级 `copilot-*` 必须在 ledger 中记录 worker 返回、证据、风险、冲突检查和接受 / 拒绝结果，再把被验证的长期事实写入对应 `.copilot/*.md` 文件。

## Pipeline ledger 文件结构

新增目录：

```text
.copilot/pipelines/
```

命名约定：

```text
.copilot/pipelines/YYYY-MM-DD-S<stage>-<agent>-round-N.md
```

示例：

```text
.copilot/pipelines/2026-05-19-S3-copilot-experiment-round-2.md
```

固定 schema：

```markdown
# Pipeline: S3 copilot-experiment round 2

## 1. Intake
- Request: <user or conductor request, one paragraph>
- Stage: <S1-S7>
- Parent: <research-copilot / direct user invocation>
- User-approved constraints: <venue / budget / files / deadline / scope>
- Source facts: <paths and exact blocks read before planning>

## 2. Round Plan
- Goal: <one sentence>
- Non-goals: <what this round explicitly will not do>
- Success criteria: <verifiable criteria>
- Stop conditions: <when to stop rather than push through>
- Files allowed to edit: <paths or none>
- Files read-only: <paths>

## 3. Task Breakdown
| Task ID | Worker role | Scope | Inputs | Expected output | Can edit |
|---|---|---|---|---|---|
| T1 | <role> | <narrow scope> | <files / facts> | <concrete artifact> | yes/no |

## 4. Dispatch Log
- T1 dispatched to <worker/capability>: <short prompt summary>

## 5. Worker Returns
### T1
- Status: done / needs-context / blocked / failed
- Evidence: <verifiable lines, files, commands, or artifacts>
- Artifacts: <created or modified paths>
- Risk: <unresolved issue>

## 6. Coordinator Review
- Spec compliance: <does the result match the plan>
- Evidence verification: <what was checked>
- Conflict check: <overlapping edits / contradictory findings>
- Accepted: <what becomes part of the stage output>
- Rejected or re-run: <what was rejected and why>

## 7. Stage Output
- Persisted changes: <stage files or workspace files updated>
- Summary for user: <short summary>
- Suggested next step: <forward route / continue / stop>
- Back-edge signal, if any: <writer→experiment, reviewer→ideation, etc.>
```

每个 ledger 的状态按以下顺序推进：

```text
planned → dispatched → returned → reviewed → persisted → reported
```

硬约束：不能先执行再补计划。每轮至少写完 `Intake`、`Round Plan` 和 `Task Breakdown` 后，子 agent 才能派 worker 或修改文件。

## 与现有 `.copilot/` 文件的关系

ledger 记录“这一轮如何发生”。原有 stage 文件记录“长期事实是什么”。

| 文件 | 责任 | 写入者 |
|---|---|---|
| `.copilot/state.md` | 全局阶段游标、loop counters、下一步建议 | `research-copilot` |
| `.copilot/literature.md` | 文献事实、baseline、相关工作 | `copilot-literature` |
| `.copilot/ideas.md` | 用户偏好、候选方向、selected direction | `copilot-ideation` |
| `.copilot/experiments.md` | Goal anchor、Run-N 设计、metric、artifact 判断 | `copilot-experiment` |
| `.copilot/handoff.md` | 写作 / 润色 / review / rebuttal 交接摘要 | writer / polisher / reviewer / rebuttal 追加 |
| `.copilot/reviews/round-N.md` | 独立 review 正文 | `copilot-reviewer` |
| `.copilot/decisions.md` | 审批门、routing、back-edge 决策 | `research-copilot` |
| `.copilot/pipelines/*.md` | 每轮计划、派发、回收、验证账本 | 当前 stage coordinator |

例如，实验日志抽取、metric 核验和 plot worker 的中间结果先进入对应 pipeline ledger；最终 verified metric 和 Goal-anchor status 再进入 `.copilot/experiments.md`。review worker 的原始 finding 先进入 ledger；父级合并后的正式 review 再进入 `.copilot/reviews/round-N.md`。

## Worker 派发协议

每个 worker prompt 必须包含六字段：

```text
Context & stage: <current stage, parent coordinator, why this worker exists>
This worker's goal: <one narrow task and explicit non-goals>
Available facts: <paths, excerpts, logs, artifacts, prior decisions>
Hard constraints: <write scope, no fabrication, venue, budget, time limit>
Expected output: <exact shape: table / patch / metric extraction / audit list>
Stop condition: <when to return blocked instead of improvising>
```

worker 返回必须使用四种状态之一：

| Status | 含义 | 父级处理 |
|---|---|---|
| `done` | 完成窄任务并给出证据 | 父级做 spec compliance 与 evidence verification |
| `needs-context` | 缺少必要输入 | 父级补上下文后可重派，并记录缺口 |
| `blocked` | 任务无法完成 | 父级判断是上下文不足、任务太大、权限不清还是计划错误 |
| `failed` | 尝试失败且有错误信息 | 父级记录失败证据，决定重派、改计划或停止 |

worker 不允许做以下事情：

- 跨阶段派发其他 agent。
- 修改未在 `Can edit` 中授权的文件。
- 声明全局阶段完成。
- 把未经验证的 metric、citation、review verdict 或实验结论当成事实。
- 用长篇过程输出替代可验证证据。

## 各子 agent 的 worker 使用方式

### `copilot-literature`

适合并行 worker：关键词检索、citation 核验、baseline 摘要、相关工作分组。父级负责去重、合并 metadata、标注不确定项，并写入 `.copilot/literature.md`。haiku 模型输出仍偏结构化整理，不承担最终创新判断。

### `copilot-ideation`

主综合判断仍由 `copilot-ideation` 承担。worker 可用于已有工作查重、baseline 代码结构扫描、某方向可行性速查、术语冲突检查。父级负责 6 维度候选、跨领域类比、5 轴筛选和 selected direction 的最终落盘。

### `copilot-experiment`

这是最需要 ledger 的子 agent。可拆分 worker：实验设计审查、代码入口定位、运行命令准备、日志读取、metric 抽取、plot 生成、artifact 验证。长任务仍必须 background / monitor / wakeup。worker 不能宣布实验成功；父级必须依据 Goal anchor 判定 `goal-met`、`on-trajectory`、`off-trajectory` 或 `falsified`。

### `copilot-writer`

worker 可分别处理事实抽取、citation placeholder 列表、单段草稿、LaTeX 安全检查。父级负责统一语气、术语、claim-evidence 对齐，并最终写入 `sections/*.tex`、`references.bib` 或 `.copilot/handoff.md`。任何引用和数字仍必须有可验证来源。

### `copilot-polisher`

worker 可做术语统一、去 AI 味、语法密度、局部段落 polish。父级必须验证技术含义没有改变，不能让 worker 引入新事实、改 citation 或修改实验结论。

### `copilot-reviewer`

worker 可并行做 claim-evidence audit、citation audit、experimental sufficiency、reproducibility、writing flow。父级负责 severity 合并、重复 finding 去重、过度升级控制和正式 review 写入。reviewer 仍默认只读，不直接改论文。

### `copilot-rebuttal`

worker 可按 reviewer comment 拆分：事实核验、回应草稿、语气压缩、一致性检查。父级统一口径，尤其检查不同 reviewer 回复中的数字、承诺、实验状态和措辞是否矛盾。

## 并行与串行规则

允许并行的前提：

```text
任务之间读写文件不重叠
输出可以独立验证
失败不会污染其他任务
不依赖彼此的中间结论
```

必须串行的场景：

```text
多个 worker 会修改同一个 tex 段落
多个 worker 会修改同一个实验配置或脚本
一个 worker 的结果决定另一个 worker 的输入
涉及全局 next-step、back-edge 或 user approval
涉及长期事实落盘到同一个 stage 文件
```

如果并行 worker 返回结果冲突，父级必须在 `Coordinator Review` 中记录冲突来源，只接受可验证的一方；无法判断时派只读核验 worker 或停止并报告。

## 错误处理

### `needs-context`

父级补充缺失上下文并可重派。ledger 必须记录第一次派发缺了什么，避免反复用同样 prompt 重试。

### `blocked`

父级不能硬推。必须判断 blocker 类型：上下文不足、任务太大、权限不清、外部资源缺失、计划本身错误。若计划错误，回到 `Round Plan` 修订并记录 revision。

### worker 越权

如果 worker 修改了未授权文件或越过 stage 边界，父级必须在 ledger 标记 rejected，并采取最小必要修复。跨阶段行动必须回到 `research-copilot`。

### 长任务超时

实验和训练类任务沿用现有 long-task discipline：小于 10 分钟可同步；10 分钟到 2 小时使用 background；需要进度事件时使用 monitor；长时间无事件用 wakeup。禁止用反复长 timeout 同步轮询消耗上下文。

### 证据不足

没有 verifiable evidence 的 worker 结果只能进入风险或待核验项，不能写入长期事实文件，也不能用于宣布完成。

## `research-copilot` 调整

`research-copilot` 的职责从“禁止子 agent 嵌套 Task”调整为“管住二级派发边界”。它需要：

1. 在总览文档中说明 `copilot-*` 可以派 worker，但必须使用 pipeline ledger。
2. 在派发给 `copilot-*` 的 prompt 中要求其先写 ledger，再执行。
3. 在回收子 agent 输出时优先读取 `Stage Output`，必要时检查 `Coordinator Review`。
4. 继续保持跨阶段派发唯一入口：worker 和 stage coordinator 都只能提出 back-edge signal，不能直接跨阶段 Task。
5. 初始化 `.copilot/` skeleton 时包含 `.copilot/pipelines/` 目录说明。

## `plugin-dev:agent-development` 技能

新增或整理一个 agent / skill 开发工作流能力，稳定表达为 `plugin-dev:agent-development` 类技能。它用于创建、重构、审查 `.agent.md`、`SKILL.md`、agent 编排协议、插件打包规则和 workspace customization。

该技能应要求开发类任务遵循：

```text
需求澄清
→ 设计
→ pipeline ledger
→ worker 派发
→ coordinator review
→ 验证
→ 文档更新
```

它不替代 `research-copilot`，而是作为 agent / skill / plugin 开发的元工作流。凡是涉及多个文件或多个 agent 的开发，必须先写 ledger，再派 worker；不能在单一会话里把设计、实现、验证和输出混写完。

推荐目录名：

```text
self/skills/plugin-dev-agent-development/
```

推荐 frontmatter description 覆盖关键词：agent development、plugin-dev、创建或重构 `.agent.md`、创建或重构 `SKILL.md`、agent 编排协议、worker dispatch、pipeline ledger。

## 预期文件改动

实施阶段预计修改或新增：

```text
self/AGENTS.md
self/README.md
self/SKILLS.md
self/agents/research-copilot.agent.md
self/agents/copilot-literature.agent.md
self/agents/copilot-ideation.agent.md
self/agents/copilot-experiment.agent.md
self/agents/copilot-writer.agent.md
self/agents/copilot-polisher.agent.md
self/agents/copilot-reviewer.agent.md
self/agents/copilot-rebuttal.agent.md
self/skills/plugin-dev-agent-development/SKILL.md
```

如果实施时发现已有等价 `plugin-dev` 或 `agent-development` skill，应优先更新现有 skill，而不是创建重复目录。

## 验证计划

实施完成后运行：

```bash
python self/scripts/generate-skill-json.py --check
python scripts/build_copilot_workspace.py --repo-root . --output dist/claude-workspace --target github
```

同时做文本一致性检查：

1. 所有 `copilot-*` 子 agent 都包含先写 pipeline ledger 的规则。
2. 不再把“sub-agents do NOT Task each other”作为绝对铁律。
3. 所有跨阶段 dispatch 仍只能由 `research-copilot` 发起。
4. worker prompt 六字段在总控和子 agent 中一致。
5. `.copilot/pipelines/` 与 `.copilot/*.md` 的职责没有冲突。
6. `self/README.md`、`self/AGENTS.md` 和具体 agent 文件对架构描述一致。
7. `plugin-dev:agent-development` 的 description 足以被 agent customization / plugin development 请求发现。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 二级派发重新引入嵌套 Task 超时 | worker 必须窄任务；长任务使用 background / monitor / wakeup；跨阶段禁止嵌套。 |
| ledger 变成新的垃圾桶 | 固定 schema；中间输出必须被父级压缩；长期事实仍写入 stage 文件。 |
| worker 并行改同一文件导致冲突 | 并行前要求读写范围不重叠；共享写入必须串行。 |
| 父级 coordinator 只转发 worker 输出而不审核 | 强制 `Coordinator Review` 段，包括 spec compliance、evidence verification、conflict check。 |
| agent 文档之间互相矛盾 | 实施计划中把 `self/AGENTS.md`、`self/README.md` 和所有 agent 文件作为同一任务组统一更新并检查。 |
| `plugin-dev:agent-development` 与 VS Code 内置 agent-customization 技能重叠 | 定位为本仓库 research_copilot 的插件开发工作流，强调 ledger + worker dispatch；不复制通用 customization reference。 |

## 成功标准

本设计实施后，任一 `copilot-*` 子 agent 的复杂任务都应满足：

1. 主会话只看到阶段摘要、风险和下一步建议。
2. 详细计划、worker 输出、证据和审核记录可在 `.copilot/pipelines/<round>.md` 中追溯。
3. 长期事实仍能在对应 `.copilot/*.md` 文件中找到。
4. worker 不能绕过父级 coordinator 或 `research-copilot` 推进阶段。
5. agent / skill 开发请求可以通过 `plugin-dev:agent-development` 进入同一套清晰流程。

一句话原则：`research-copilot` 管全局阶段，`copilot-*` 管本阶段流水线，worker 只做窄任务；所有计划、派发、回收和验证先进入 `.copilot/pipelines/`，主会话只接收审核后的摘要和下一步决策。