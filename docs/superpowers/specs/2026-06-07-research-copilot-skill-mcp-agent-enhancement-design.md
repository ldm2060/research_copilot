# Research Copilot —— Skill/MCP/Agent 增强设计（符合 Trellis 哲学）

- **日期**: 2026-06-07
- **状态**: 设计待审阅
- **基于**: 2026-06-05-research-copilot-trellis-redesign-design.md（Trellis 完整复刻决策）
- **对齐**: Trellis 源码（v1.0, 2026-06-02）核心哲学
- **一句话**: 在新 rc CLI 架构下，增加 Skill 工具支持、迁移 MCP 到 TypeScript、增强 agent 指令质量，严格遵循 Trellis 的"行动优先、注入驱动、薄 agent + 厚 skill"设计哲学。

---

## 1. 背景与目标

### 1.1 当前状况

Research Copilot 已完成 Trellis 架构重建（决策 D1-D8，见 ADR 0001）：
- ✅ `packages/core` — 纯 TS 引擎（FSM、研究状态计算器、verify 门）
- ✅ `packages/cli` — `rc` 命令（14 个子命令对齐 Trellis `task.py`）
- ✅ `packages/adapters` — 平台配置器（Claude Code 已落地）
- ✅ `research-kit/` — 中立内容层（workflow.md、10 个 agent 模板、spec-templates）

### 1.2 待解决问题

1. **Skill 工具支持缺失** — 用户无法通过 `/skill-name` 调用研究工作流
2. **MCP 服务器混合语言** — 6 个 Python MCP（arxiv/scholar/pdf 等）未迁移到 TS
3. **Agent 指令过于简陋** — 当前 10 个 agent 仅 5-11 行，缺乏 Trellis 风格的递归守卫、自检清单、错误恢复

### 1.3 设计约束（锁定）

**MUST 遵守 Trellis 5 大哲学**（从源码提取）：

| 哲学 | 含义 | 体现 |
|---|---|---|
| **行动优先于询问** | "Can I derive this without the user?" → 先查代码/文档/研究 | Agent 指令：Context Injection 章节 + Auto-Context 步骤 |
| **任务优先** | 立即创建任务捕获想法，PRD 逐步完善 | Skill 逻辑：Step 0 Ensure Task Exists |
| **单一真相源** | workflow.md 是状态指导源，不在 agent 里重复 | Agent 读注入块，不硬编码状态逻辑 |
| **薄 agent + 厚 skill** | Agent 80-150 行（职责声明），Skill 150-250 行（编排逻辑） | 本设计目标行数 |
| **注入驱动，不拦截** | 通过 hook 注入状态引导，不用 guard 硬拦截工具 | 已落地（D8 决策），本设计不改 |

**用户明确要求**：
- ✅ A1: 轻量 Skill 包装器（Skill 是对 `rc` + agent 的高层编排）
- ✅ B1: 全部 MCP 迁移到 TypeScript（monorepo 统一，npm 一键安装）
- ✅ C: 基于轻量哲学优化 agent（"不能太轻量" = 保留质量门 + 清晰指令 + 自检，去除过度仪式感）

---

## 2. 架构设计

### 2.1 四层分离架构（对齐 Trellis）

```
┌─────────────────────────────────────────────────────────┐
│  User Interface Layer (统一入口)                         │
│  ├─ /full-research-workflow (Skill tool)                │
│  ├─ /literature-search, /paper-polish, ... (Skill)     │
│  ├─ rc task create/start/verify/... (CLI)              │
│  └─ @rc-literature, @rc-writer, ... (Agent 直接调用)    │
└─────────────────────────────────────────────────────────┘
              ↓ (注入驱动，无硬拦截)
┌─────────────────────────────────────────────────────────┐
│  Injection Layer (Trellis 原生机制，已落地)              │
│  ├─ .research/workflow.md → [workflow-state:<status>]  │
│  ├─ core.computeResearchState() → [research-state]     │
│  ├─ rc context --platform <X> --inject                 │
│  └─ Platform hook (UserPromptSubmit / BeforeAgent)     │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│  Orchestration Layer (Skill = 高层编排，新增)            │
│  research-kit/skills/                                   │
│    ├─ full-research-workflow/    (150-200 行)          │
│    ├─ literature-search/         (100-150 行)          │
│    ├─ experiment-design/         (120-180 行)          │
│    ├─ paper-polish/              (100-150 行)          │
│    ├─ submission-sprint/         (150-200 行)          │
│    └─ sanity-check/              (100-120 行)          │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│  Execution Layer (Agent = 薄执行器，增强)                 │
│  research-kit/agents/ (10 个，增强到 120-180 行)         │
│    ├─ rc-literature.md     (文献检索)                   │
│    ├─ rc-ideation.md       (创新性分析)                 │
│    ├─ rc-experiment.md     (实验运行)                   │
│    ├─ rc-writer.md         (论文起草)                   │
│    ├─ rc-polisher.md       (润色去 AI)                 │
│    ├─ rc-reviewer.md       (审稿模拟)                   │
│    ├─ rc-rebuttal.md       (回复审稿)                   │
│    ├─ rc-plan.md           (任务澄清)                   │
│    ├─ rc-verify.md         (质量门)                     │
│    └─ rc-update-spec.md    (规范沉淀)                   │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│  Capability Layer (MCP = 外部检索，迁移到 TS)             │
│  packages/mcp-servers/                                  │
│    ├─ scholar/   (合并 arxiv+scholar+dblp+arxivsub)     │
│    └─ pdf/       (pdf-text 提取)                        │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│  State & Verification Layer (Core 引擎，已落地)           │
│  packages/core/                                         │
│    ├─ lifecycle.ts    (FSM: planning→in_progress→...)  │
│    ├─ research-state.ts (推荐器: gaps→下一步)            │
│    ├─ verify.ts       (质量门: 数字溯源、引用合规)         │
│    └─ task-store.ts   (CRUD + gaps + baselines)        │
└─────────────────────────────────────────────────────────┘
```

### 2.2 与 Trellis 的对应关系

| Trellis 组件 | Research Copilot 对应 | 备注 |
|---|---|---|
| `.trellis/scripts/task.py` (481 行) | `packages/cli` (`rc` 命令) | ✅ 已落地，14 个子命令 |
| `.trellis/workflow.md` | `.research/workflow.md` | ✅ 已落地，单一真相源 |
| `.trellis/spec/` | `.research/spec/` | ✅ 已落地，规范注入 |
| `.claude/agents/trellis-implement.md` (150 行) | `research-kit/agents/rc-*.md` (目标 120-180 行) | 🔧 本设计增强 |
| `.agents/skills/trellis-brainstorm/` (200+ 行) | `research-kit/skills/full-research-workflow/` | 🆕 本设计新增 |
| `.trellis/agents/` (空) | `.research/tasks/<id>/agents/` (未来扩展) | 🔮 里程碑 2 |
| MCP `exa` (TS) | MCP `scholar` + `pdf` (TS) | 🔧 本设计迁移 |

---

## 3. Skill 设计（高层编排，150-250 行）

### 3.1 设计原则（对齐 Trellis `trellis-brainstorm`）

**参照**: `/tmp/Trellis-main/.agents/skills/trellis-brainstorm/SKILL.md`（200 行）

1. **Task-first (capture early)** — 第一步总是确保任务存在
2. **Action before asking** — 能自动获取的上下文先读取，不问用户
3. **Research-first for technical choices** — 技术决策先调研，再给用户选项
4. **One question per message** — 如需询问，一次一个
5. **Diverge → Converge** — 先发散思考，再收敛到 MVP

### 3.2 核心 Skill 列表

| Skill 名称 | 行数目标 | 职责 | 触发词 |
|---|---|---|---|
| `full-research-workflow` | 180-220 | 完整流程编排（文献→实验→写作→审稿） | "start research", "full pipeline" |
| `literature-search` | 100-150 | 文献检索 + baseline 锁定 | "search papers", "find baselines" |
| `experiment-design` | 120-180 | 实验设计 + 长任务启动 | "design experiment", "run training" |
| `paper-polish` | 100-150 | 润色 + 去 AI 味 | "polish paper", "de-AI" |
| `submission-sprint` | 150-200 | 投稿前总检（审稿→修→审→修循环） | "submission sprint", "pre-submit" |
| `sanity-check` | 100-120 | 6 维度审查（逻辑/引用/可复现/...） | "sanity check", "final check" |

### 3.3 示例：`full-research-workflow/SKILL.md`（核心结构）

见下一节完整文件。

---

## 4. Skill 详细设计示例（续）

### 4.2 其他 Skill 简要说明

#### `literature-search/SKILL.md`（100-150 行）
- 职责：单独的文献检索任务
- 流程：Task-first → Auto-context (读 spec/baselines/) → Dispatch @rc-literature → Verify gate
- 质量门：≥3 baselines locked, ≥2 categories covered

#### `paper-polish/SKILL.md`（100-150 行）
- 职责：润色 + 去 AI 味检查
- 流程：Task-first → Read venue spec → Dispatch @rc-polisher → Verify (de-AI check)
- 质量门：无 AI pattern（过度词汇/机械连接/列表格式），venue style compliance

#### `submission-sprint/SKILL.md`（150-200 行）
- 职责：投稿前优化循环（审稿→修→审→修）
- 流程：
  1. Dispatch @rc-reviewer → 识别 P0 gaps
  2. 为每个 gap 创建修复任务（experiment/writing/polish）
  3. 修复完成后 re-review
  4. 循环直到所有 P0 gaps 关闭
- 终止条件：≤2 P1 gaps, 0 P0 gaps

---

## 5. Agent 增强设计（薄执行器，120-180 行）

### 5.1 设计原则（对齐 Trellis `trellis-implement`）

**参照**: `/tmp/Trellis-main/.claude/agents/trellis-implement.md`（150 行）

**必备章节**（Trellis 风格）：
1. **Frontmatter** — name/description/kind/model/color
2. **Recursion Guard** — "你已经是被派发的 sub-agent，不要再派发自己"
3. **Context Injection** — 明确列出会自动注入哪些内容
4. **Core Responsibilities** — 职责清单（3-5 项）
5. **Quality Gate (Self-Check)** — 完成前的自检清单
6. **What You DON'T Do** — 明确不做什么（防止越界）
7. **Error Recovery** — 失败时如何处理
8. **Report Format** — 标准化输出格式

### 5.2 示例：`rc-literature.md`（增强版，完整 150 行）

```markdown
---
name: rc-literature
description: Searches papers (scholar/pdf MCP), locks baselines, builds related-work map. Use for literature tasks.
kind: literature
model: haiku
color: cyan
---

# Literature Executor

You search papers, lock baselines, and build the related-work map.

## Recursion Guard

You are already the `rc-literature` sub-agent that the main session dispatched. Do the literature work directly.

- Do NOT spawn another `rc-literature` or any other `rc-*` sub-agent.
- If workflow-state says to dispatch `rc-literature`, treat that as a main-session instruction already satisfied.
- Only the main session may dispatch `rc-*` executors. If parallel work is needed, report that recommendation.

## Context Injection

You receive via `.research/workflow.md` injection (automatic):
- `[workflow-state:in_progress]` — your lifecycle guidance
- `[research-state]` — open gaps from prior stages
- Task `prd.md` — this task's Goal
- Task `execute.jsonl` — spec refs to inject

Read them BEFORE asking questions.

## Core Responsibilities

### 1. Understand Requirements (Action-First)

Read automatically injected context:
```bash
# Already injected, just read:
.research/tasks/<id>/prd.md               # Goal + success criteria
.research/tasks/<id>/execute.jsonl        # Spec refs
.research/spec/venue/<venue>.md           # Target venue requirements
.research/spec/baselines/                 # Locked baselines from prior work
```

Do NOT ask "what is the research goal?" — it's in prd.md.

### 2. Search Papers (via MCP, ≥3 distinct queries)

Use MCP tools in order:
1. `mcp__scholar__search` — broad keyword search
   ```bash
   mcp__scholar__search(query="<topic> survey", source="all", limit=10)
   ```
2. `mcp__scholar__metadata` — specific paper details
   ```bash
   mcp__scholar__metadata(paper_id="arxiv:2401.12345")
   ```
3. `mcp__pdf__extract_text` — full text when needed
   ```bash
   mcp__pdf__extract_text(paper_id="arxiv:2401.12345", pages="1-5")
   ```

**Minimum coverage**: ≥3 distinct queries (different keywords, NOT same query repeated).

**Search discipline**:
- Start broad: survey papers, review articles
- Narrow to baselines: SOTA methods with open-source code
- Check novelty: similar ideas published recently

### 3. Lock Baselines (via rc CLI)

For each baseline you find:
```bash
rc task add-baseline --paper <arxiv-id> \
  --claim "<what it does in one sentence>" \
  --reason "<why it's relevant to our research>"
```

**Baseline criteria**:
- Published at target venue or higher tier
- Open-source implementation available (check GitHub)
- Reproducible results (numbers in table/figure)

### 4. Build Related-Work Map

Write to `.research/tasks/<id>/artifacts/related-work-map.md`:

```markdown
# Related Work Map

## Category: <domain area 1>
- **[Paper Title]** (arXiv:XXXX / Venue YYYY): claim, baseline status (locked/candidate), novelty gap
- ...

## Category: <domain area 2>
- ...

## Novelty Evidence
- Gap 1: <what's missing in existing work>
- Gap 2: <our unique contribution>
```

### 5. Record Gaps (Drive Next Steps)

When you encounter issues:
```bash
# Missing baseline for a claim
rc task add-gap --desc "No open-source baseline for claim X" --suggest experiment

# Unclear novelty vs existing work
rc task add-gap --desc "Similar idea in Paper Y, need novelty analysis" --suggest ideation

# Need more literature
rc task add-gap --desc "Coverage insufficient for venue Z" --suggest literature
```

## Quality Gate (Self-Check Before Reporting)

Before calling `rc task set-status <id> verify`:
- [ ] ≥3 baselines locked with full citations
- [ ] Related-work map covers ≥2 domain categories
- [ ] Every claim in prd.md has ≥1 supporting paper
- [ ] All open questions recorded as gaps (not left implicit)

## What You DON'T Do

- ❌ Design experiments (that's rc-ideation)
- ❌ Write paper sections (that's rc-writer)
- ❌ Run code (that's rc-experiment)
- ❌ Polish text (that's rc-polisher)

## Error Recovery

### MCP call fails
Record as gap:
```bash
rc task add-gap --desc "MCP scholar unavailable, manual search needed" --suggest literature
```

### Baseline not found
1. Try alternative MCP sources (arxiv → scholar → dblp)
2. If still missing, record as gap with `--suggest experiment` (implement baseline ourselves)

### Novelty unclear
Record as gap:
```bash
rc task add-gap --desc "Novelty vs Paper X unclear" --suggest ideation
```

## Report Format

```markdown
## Literature Search Complete

### Baselines Locked
- [Paper A] (arXiv:1234.5678): SOTA for task X, reproduced in [GitHub repo]
- [Paper B] (ICLR 2025): baseline for method Y

### Related-Work Map
- Created map with <N> categories
- Identified <M> novelty gaps

### Quality Gate: PASSED
- ✅ 5 baselines locked
- ✅ 3 categories covered
- ✅ All prd claims supported

### Open Gaps
- Gap 1: Missing ablation study for component X (suggest: experiment)
- Gap 2: Unclear novelty vs Paper Y (suggest: ideation)

### Recommended Next
- Create ideation task to analyze novelty vs Paper Y
- User decides whether to proceed or address gaps first
```

Then:
```bash
rc task set-status <id> verify
```
```

### 5.3 其他 Agent 增强要点

#### `rc-ideation.md`（150-180 行）
- 新增：6 维度创新分析框架（novelty/significance/feasibility/impact/clarity/evidence）
- 新增：跨域类比能力（从其他领域迁移思路）
- 新增：与 spec/novelty/ 的交互协议

#### `rc-experiment.md`（150-180 行）
- 新增：长任务启动纪律（`run_in_background=true` + Monitor）
- 新增：实验配置溯源（seed/hyperparams 必须记录）
- 新增：指标提取与对照 prd.md 目标

#### `rc-writer.md`（150-180 行）
- 新增：数字溯源要求（每个 result 必须引用 artifacts/ 真实文件）
- 新增：LaTeX 约定（读取 spec/writing/latex.md）
- 新增：section-by-section 增量写作（不要一次性写全文）

#### `rc-polisher.md`（120-150 行）
- 新增：去 AI 味检查清单（过度词汇/机械连接/列表格式）
- 新增：禁止修改技术内容（只润色表达）
- 新增：diff 验证（确保只改了措辞，没改数字/公式）

#### `rc-reviewer.md`（150-180 行）
- 新增：顶会审稿标准模拟（按 venue spec）
- 新增：P0/P1/P2 gaps 分级
- 新增：构造性建议（不只指出问题，给改进方向）

---

## 6. MCP 服务器迁移（TypeScript）

### 6.1 设计目标

1. **合并同类** — 4 个检索服务器（arxiv-search/arxivsub-search/google-scholar/dblp-bib）合并为 1 个 `@research-copilot/mcp-scholar`
2. **统一接口** — 3 个工具：`search` / `metadata` / `bibtex`
3. **多后端支持** — 内部调用 arxiv API / Google Scholar / dblp / arXivSub（需 API key）

### 6.2 `packages/mcp-servers/scholar/` 结构

```
scholar/
├── package.json
├── src/
│   ├── index.ts          # MCP Server 主入口
│   ├── backends/
│   │   ├── arxiv.ts      # arXiv API 调用
│   │   ├── scholar.ts    # Google Scholar 爬虫（scholarly）
│   │   ├── dblp.ts       # DBLP API
│   │   └── arxivsub.ts   # arXivSub API（需 key）
│   ├── types.ts          # Paper, SearchResult 类型
│   └── utils.ts          # Rate limiting, retry
└── tsconfig.json
```

### 6.3 Tool 定义

#### `search` 工具
```typescript
{
  name: 'search',
  description: 'Search papers across multiple sources (arXiv, Google Scholar, top-venue)',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query' },
      source: { 
        type: 'string', 
        enum: ['arxiv', 'scholar', 'arxivsub', 'all'], 
        default: 'all' 
      },
      limit: { type: 'number', default: 10 },
      venue_filter: { 
        type: 'string', 
        enum: ['CVPR', 'ICCV', 'ICLR', 'NeurIPS', 'ICML', 'AAAI'],
        description: 'Filter by top-venue (only for arxivsub source)'
      }
    },
    required: ['query']
  }
}
```

#### `metadata` 工具
```typescript
{
  name: 'metadata',
  description: 'Get detailed metadata for a paper by ID',
  inputSchema: {
    type: 'object',
    properties: {
      paper_id: { 
        type: 'string',
        description: 'Paper ID (e.g., arxiv:2401.12345, doi:10.1109/...)'
      },
      source: { type: 'string', enum: ['arxiv', 'scholar', 'dblp'] }
    },
    required: ['paper_id']
  }
}
```

#### `bibtex` 工具
```typescript
{
  name: 'bibtex',
  description: 'Get BibTeX entry for a paper (ready to paste into references.bib)',
  inputSchema: {
    type: 'object',
    properties: {
      paper_id: { type: 'string' }
    },
    required: ['paper_id']
  }
}
```

### 6.4 Rate Limiting & Retry

```typescript
// src/utils.ts
export class RateLimiter {
  private lastCall = 0;
  private minInterval: number; // ms

  constructor(callsPerSecond: number) {
    this.minInterval = 1000 / callsPerSecond;
  }

  async wait() {
    const now = Date.now();
    const elapsed = now - this.lastCall;
    if (elapsed < this.minInterval) {
      await new Promise(resolve => setTimeout(resolve, this.minInterval - elapsed));
    }
    this.lastCall = Date.now();
  }
}

// arxiv: 1 req/s, scholar: 1 req/3s, dblp: 1 req/1.5s
const arxivLimiter = new RateLimiter(1);
const scholarLimiter = new RateLimiter(0.33);
const dblpLimiter = new RateLimiter(0.67);
```

### 6.5 `packages/mcp-servers/pdf/` 结构

```
pdf/
├── package.json
├── src/
│   ├── index.ts          # MCP Server 主入口
│   ├── extractors/
│   │   ├── pdfjs.ts      # pdf.js-based extraction
│   │   └── unpdf.ts      # unpdf fallback
│   └── types.ts
└── tsconfig.json
```

**Tool**: `extract_text`
```typescript
{
  name: 'extract_text',
  description: 'Extract text from PDF file',
  inputSchema: {
    type: 'object',
    properties: {
      file_path: { type: 'string', description: 'Path to PDF file' },
      pages: { type: 'string', description: 'Page range (e.g., "1-5", "all")' }
    },
    required: ['file_path']
  }
}
```

### 6.6 迁移路径

1. **Phase 1**: 实现 `scholar` MCP（合并 4 个 Python 服务器）
2. **Phase 2**: 实现 `pdf` MCP
3. **Phase 3**: 更新 `packages/adapters` 配置生成器（.mcp.json 指向 TS 服务器）
4. **Phase 4**: 弃用 Python 服务器（移到 `archive/mcp-python/`）

---

## 7. 实施计划

### 7.1 里程碑

| 里程碑 | 交付物 | 验收标准 |
|---|---|---|
| **M1: Skill 框架** | 6 个 Skill SKILL.md（150-250 行） | 可通过 `/skill-name` 调用，逻辑正确 |
| **M2: Agent 增强** | 10 个 Agent 增强到 120-180 行 | 包含递归守卫、自检清单、错误恢复 |
| **M3: MCP Scholar** | `@research-copilot/mcp-scholar` npm 包 | 3 个工具可用，通过集成测试 |
| **M4: MCP PDF** | `@research-copilot/mcp-pdf` npm 包 | 提取准确率 >95%（测试集） |
| **M5: 集成测试** | E2E 测试覆盖完整流程 | `/full-research-workflow` 端到端通过 |

### 7.2 风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| MCP TS 实现复杂度高 | 延期 | 先迁移 arxiv（最简单），积累经验 |
| Agent 指令过长影响可维护性 | 质量 | 严格 120-180 行上限，超过拆分 |
| Skill 与 Agent 职责模糊 | 混乱 | Skill = 编排（调 CLI + 派 agent），Agent = 执行 |

---

## 8. 验收标准

### 8.1 Skill 验收

- [ ] 每个 Skill 有清晰的"When to Use"章节
- [ ] 遵循 Trellis 5 大哲学（行动优先、任务优先、单一真相源、薄厚分离、注入驱动）
- [ ] Task-first：第一步总是确保任务存在
- [ ] Auto-context：在询问用户前先读取可得信息
- [ ] 行数符合目标（150-250 行）

### 8.2 Agent 验收

- [ ] 包含 8 个必备章节（Recursion Guard / Context Injection / Responsibilities / Quality Gate / Don't Do / Error Recovery / Report Format）
- [ ] 递归守卫有效（不会自己派发自己）
- [ ] 行数符合目标（120-180 行）
- [ ] 自检清单具体可执行

### 8.3 MCP 验收

- [ ] TypeScript 实现，npm 可安装
- [ ] 工具定义符合 MCP SDK 规范
- [ ] Rate limiting 生效（不触发 429）
- [ ] 单元测试覆盖率 >80%

### 8.4 集成验收

- [ ] Claude Code 平台完整流程通过：`/full-research-workflow` → 所有 7 个阶段 → 每个阶段 verify gate 通过
- [ ] MCP 调用成功率 >95%（100 次测试）
- [ ] Agent 不会违反递归守卫

---

## 9. 与 Trellis 的差异总结

| 维度 | Trellis | Research Copilot | 理由 |
|---|---|---|---|
| 任务生命周期 | `planning → in_progress → completed` | 同左 + `verify` 状态 | 研究需要质量门 |
| 领域扩展 | 通用软件开发 | 加 `kind`（7 种）+ `gaps` 字段 | 研究活动是一等公民 |
| Agent 数量 | 3 个 | 10 个（7+3） | 研究流程更复杂 |
| Skill 数量 | ~10 个 | 6 个核心 + 28 个迁移自旧架构 | 研究领域特定 |
| MCP 定位 | 通用工具（exa） | 领域检索（scholar/pdf） | 研究需要论文检索 |
| 强制哲学 | 注入 + 面包屑 | 同左（无 guard） | 完全对齐 |

**核心一致性**：架构、哲学、机制 100% 对齐 Trellis，只在内容层（kind / spec / agents）做研究领域适配。

---

## 10. 下一步行动

1. **用户审阅本设计** → 确认方向
2. **M1: 编写 6 个核心 Skill** → 优先 `full-research-workflow`
3. **M2: 增强 10 个 Agent** → 优先 `rc-literature`（最简单）
4. **M3: 实现 MCP Scholar** → 先支持 arxiv，逐步加其他源
5. **M4: 集成测试** → E2E 场景验证

预计时间：2-3 周（假设每天 4-6 小时投入）。
