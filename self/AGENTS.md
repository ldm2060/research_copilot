# Agents 总览

`self/agents/` 下的 agent 全部为 Claude Code 原生格式（frontmatter 含 `name` / `description` / `model`，**不限制 `tools`**——拥有全部默认工具）。每个 `.agent.md` 可被用户用 `@agent-name` 直接调用，也可被总控通过 `Task(subagent_type="...")` 委派。

## 体系结构

```
              ┌─ 用户 ─┐
              │         │
              ▼         ▼
   research-copilot   @copilot-<sub> 直调
   （流程守卫者，          （知道要做什么时的快捷路径）
    唯一推荐入口）
              │
              └─ Task() 委派 ─→ 7 个独立子 agent
                                  │
                                  ├─ Skill 工具 → 调能力匹配的 skill
                                  ├─ MCP 工具 → 调能力匹配的 MCP
                                  └─ Bash/Edit/Write/Glob/Grep/Read 等 → 本地操作

铁律: 子 agent 之间不互相 Task 调用，互动靠"软建议"+ 用户决策
```

## 8 个 agent 一览

| Agent | 文件 | 角色 | Model | Color | 何时用 |
|---|---|---|---|---|---|
| **research-copilot** | `research-copilot.agent.md` | 🧭 全流程总控 | sonnet | magenta | 不知道下一步做什么 / 走全流程 / 通篇优化 / 投稿冲刺 / rebuttal 准备 / 创新点重校 |
| **copilot-literature** | `copilot-literature.agent.md` | 📚 文献调研 | haiku | cyan | 检索论文 / 锁定 baseline / 补 related work / 核验引用 |
| **copilot-ideation** | `copilot-ideation.agent.md` | 💡 创新点交互构思 | **opus** | magenta | 找创新方向 / 跨领域头脑风暴 / novelty 重校 |
| **copilot-experiment** | `copilot-experiment.agent.md` | 🧪 实验运行与验证 | sonnet | green | 跑训练 / 复现 baseline / 消融 / 读 metric / 画图 |
| **copilot-writer** | `copilot-writer.agent.md` | ✍️ 论文写作 | sonnet | blue | 起草章节 / 把实验结果转成正文 / 扩写 / 缩写 / 翻译 / caption |
| **copilot-polisher** | `copilot-polisher.agent.md` | ✨ 论文润色 | sonnet | blue | 学术化 / 去 AI 味 / 句式 / 术语统一（不改技术内容） |
| **copilot-reviewer** | `copilot-reviewer.agent.md` | 🔍 论文审阅 | **opus** | yellow | 投稿前质量门 / claim-evidence 对齐 / 模拟顶会审稿 / rebuttal 自洽性 |
| **copilot-rebuttal** | `copilot-rebuttal.agent.md` | 💬 rebuttal 回复 | sonnet | yellow | reviewer 评论起草回复 / 答辩文稿 / 联动需求清单 |

**模型分配理由**:
- `opus`：高强度推理、跨领域类比、独立审稿——`copilot-ideation` 与 `copilot-reviewer` 需要把"思路新颖性"和"严格审稿"这两类深度判断做扎实
- `haiku`：偏检索 + 结构化整理，速度优先——`copilot-literature` 大量调论文检索类 MCP，模型本身只做摘要、归类、距离判断
- `sonnet`：平衡推理与速度——总控、写作、润色、实验、rebuttal 都属于这一档

## 总控的两种工作模式

### 模式 A: 路由（默认）

用户问任意问题时：扫 `.copilot/state.md` → 一句话诊断 → 一句话推荐 → 委派单个子 agent **或** 自己整合。

### 模式 B: 管道

用户明说时启动，预设模板：

| 模板 | 序列 |
|---|---|
| 完整研究 | S1 文献 → S2 创新点 → S3 实验 → S4 写作 → S5 润色 → S6 审阅 → S7 rebuttal |
| 投稿前综合优化 | 通读 → S4 扩缩 → S5 润色 → S5 去 AI 味 → S6 终审 |
| rebuttal 准备 | S6 自检 → S7 草稿 → S6 复审 → S7 定稿 |
| 创新点重校 | S2 头脑风暴 → S3 快速验证 → 回 S2 修订 或 进 S4 |
| 自定义 | 用户指定序列（如 `S5→S6→S5→S6`） |

每段间必须 `AskUserQuestion` 审批门，未确认不进下一段。

## 子 agent 写权限分区（持久化记忆）

`.copilot/` 是跨会话工作记忆，**写权限严格分区**（避免互相覆盖）：

| 文件 | 写者 | 内容 |
|---|---|---|
| `state.md` | research-copilot | 当前阶段游标 + 推荐下一步 + 阶段历史 |
| `literature.md` | copilot-literature | 候选论文 + 选定 baseline |
| `ideas.md` | copilot-ideation | 6 维度创新点候选 + 选定方向 |
| `experiments.md` | copilot-experiment | 实验设计 + Run N 流水 |
| `handoff.md` | writer / polisher / reviewer / rebuttal | 子 agent 间事实交接（追加） |
| `decisions.md` | research-copilot | 每个审批门的决策记录 |
| `reviews/round-N.md` | copilot-reviewer | 每轮审稿落盘 |

**所有子 agent 都可读全部文件**（事实共享）。`handoff.md` 是唯一允许多 agent 追加的文件，只能 append 不能 overwrite。

## 路由约定

所有 agent 共享以下硬约束：

1. **MCP 优先级（泛指）**：检索论文优先用专门的论文检索类 MCP；BibTeX 修订只用专门的 BibTeX 类 MCP；这些找不到才回落 WebSearch。**agent 文件不写具体 MCP 名字**——让 Claude Code 当下根据可用工具列表自动匹配。
2. **不编造**：数据、引用、实验结果、reviewer 共识，一律不能凭记忆补全。
3. **不硬编码 skill / MCP / 其他 agent 名**：用能力短语描述（如"论文检索类"、"BibTeX 元数据类"），未来工具列表变动不需要改 agent 文件。
4. **子 agent 不互相 Task 调用**：所有跨 agent 调度由 research-copilot 发起；子 agent 只能在响应末尾输出"建议下一步"软建议。
5. **长任务 background**：训练 / 大量检索 / 长 fetch 必须用 `run_in_background=true`，不阻塞主会话。
6. **WebFetch 单次超时上限 30s**：超时立即放弃，回退 `WebSearch` 摘要。

## Socket 超时缓解

- 嵌套 Task 死锁 → 铁律"子 agent 不互调"消除嵌套
- 硬编码 MCP 优先级累积超时 → 不写死，按当下匹配
- 长任务阻塞 → 强制 background 模式
- MCP server 卡死无日志 → `self/scripts/diagnose-mcp.py` 单独探测每个 server

详细诊断：`python self/scripts/diagnose-mcp.py`
