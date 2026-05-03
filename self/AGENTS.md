# Agents 总览

`self/agents/` 下的 agent 全部为 Claude Code 原生格式（frontmatter 含 `name` / `description` / `tools` / `model`）。每个 `.agent.md` 可被用户用 `@agent-name` 直接调用，也可被总控 agent 通过 `Task(subagent_type="...")` 委派。

## 体系结构

```
研究生命周期:
  [0 → 第一稿]                [第一稿 → 投稿]              [投稿 → 见刊]
   │                            │                            │
   ▼                            ▼                            ▼
 research-pilot  ──────────►  paper  ──────────────────►  paper (rebuttal)
   │                            │
   ├─ Stage 5 委派 ───►  paper-writer  ◄──┘
   ├─ Stage 5 委派 ───►  paper-reviewer ◄──┘
   └─ Stage 4 可选委派 ─►  experiment-driver (third_party)

scientist (独立 AI-Scientist-v2 自动化轨道，与上图不互通)
 └─ runtime-init → ideation → experiment → plotting → writeup → review

paper 内部模式:
 ├─ Mode 1: 路由 / 诊断 / 直接小修
 ├─ Mode 2: 直接执行
 ├─ Mode 3: 创新点挖掘 (适合"已经有论文但想重新找方向")
 └─ Mode 4: 综合优化 5 阶段管道
```

| Agent | 文件 | 角色 | 何时用 |
|-------|------|------|------|
| **research-pilot** | `research-pilot.agent.md` | 🧭 研究流程总控（前期） | 从研究目标到第一稿的端到端：文献 → baseline → 创新点 → 跨领域头脑风暴 → 实验 → 起草 |
| **paper** | `paper.agent.md` | 🧭 论文研究总控（中后期） | 已有初稿/PDF 后的修改、综合优化、创新点重新校准、投稿前质量门 |
| **paper-writer** | `paper-writer.agent.md` | ✍️ 写作子 agent | 起草/重写/润色章节、章节冲刺、caption 撰写 |
| **paper-reviewer** | `paper-reviewer.agent.md` | 🔍 审稿子 agent | 提交前质量门、claim-evidence 对齐、独立审稿视角 |
| **scientist** | `scientist.agent.md` | 🧪 AI Scientist 工作流 | 协调 AI-Scientist-v2 端到端流水线（ideation → experiment → writeup → review） |

## 与旧版的差异

旧版有 8 个 agent：scientist / paper / writer / novelty / auto-reviewer / auto-improver / auto-orchestrator / overhaul。当前设计删除了 4 个、合并了 2 个：

| 旧 agent | 处理方式 |
|---|---|
| `auto-reviewer` / `auto-improver` / `auto-orchestrator` | **删除**。这是 GitHub Copilot `/fleet` 多 chat 协调产物，靠 `tmp_review.md` 信号文件协议；Claude Code 原生支持 `Task` 子 agent 调用，已由 `paper` + `paper-writer` + `paper-reviewer` 直接覆盖 |
| `overhaul` | **合并到 `paper` 的 Mode 4**。综合优化作为 paper 的一种执行模式，5 阶段串行管道 |
| `novelty` | **合并到 `paper` 的 Mode 3**。创新点挖掘作为 paper 的一种执行模式 |
| `writer` | **重命名为 `paper-writer`**。明确为子 agent 角色 |

## 使用场景

- **从研究目标开始（无论文 / 无创新点 / 无 baseline）** → `@research-pilot`
- **不知道论文下一步做什么（已有初稿）** → `@paper`
- **已经有明确写作任务** → 让 paper 委派，或直接 `@paper-writer`
- **投稿前质量门 / rebuttal 自检** → 让 paper 委派，或直接 `@paper-reviewer`
- **找创新点（已有论文，想重新校准方向）** → `@paper`（Mode 3）
- **找研究方向（从 0 开始）** → `@research-pilot`（Stage 2-3）
- **通篇优化** → `@paper`（Mode 4 串行管道）
- **AI Scientist 工作流（机器自动跑）** → `@scientist`

## 路由约定

所有 agent 共享以下硬约束：

1. **MCP 优先级**：查论文先用 `arxiv-search` MCP（`search_arxiv` / `get_arxiv_pdf_url`），无结果才回落 WebSearch；BibTeX 修改只能用 `dblp-bib` MCP。
2. **不编造**：数据、引用、实验结果、reviewer 共识，一律不能凭记忆补全。
3. **MCP 必须先装**：通过 `python self/install.py` 一键完成；若未装，`paper` / `scientist` 会回退到普通 web 搜索并提示用户。
