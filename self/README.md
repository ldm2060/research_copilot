# self/ — Research Copilot 工作区资产

本目录是 Claude Code 论文研究工作区的**全部自有资产**：agent、skill、hook、MCP 服务器及其安装脚本。`third_party/` 提供补充能力，但 `self/` 保证核心闭环可独立运行。

## 🚀 一键安装

```bash
python self/install.py
```

自动完成：
1. 安装 Python 依赖（`pdfplumber` 等）
2. 写入项目级 `.mcp.json`（指向 `self/mcp/servers/` 下 6 个 MCP 服务器）
3. 注册 SessionStart hook 到 `.claude/settings.json`（scientist-guardrails）
4. 对每个 MCP 服务器跑 JSON-RPC `initialize` 握手验证
5. 报告可选 secret（`ARXIVSUB_SKILL_KEY`）状态

完成后**重启 Claude Code 或运行 `/clear`** 即可使用。

### 可选参数

```bash
python self/install.py --dry-run        # 只打印计划不写文件
python self/install.py --skip-deps      # 跳过 pip install
python self/install.py --skip-verify    # 跳过 MCP 启动测试
python self/install.py --target /path   # 安装到非默认 workspace
```

## 📁 目录结构

```
self/
├── README.md           # 本文件
├── AGENTS.md           # agent 总览
├── SKILLS.md           # skill 总览
├── install.py          # 一键安装脚本
├── agents/             # 5 个 Claude Code agent
│   ├── research-pilot.agent.md # 研究流程总控（前期：从 0 到第一稿）
│   ├── paper.agent.md          # 论文总控（中后期：路由 + 创新点 + 综合优化）
│   ├── paper-writer.agent.md   # 写作子 agent
│   ├── paper-reviewer.agent.md # 审稿子 agent
│   └── scientist.agent.md      # AI Scientist 自动化工作流
├── skills/             # 23 个 skill
│   ├── paper-*/                # 论文写作/改写/检查
│   ├── scientist-*/            # AI Scientist 工作流执行端
│   ├── init-mcp/               # MCP 安装入口
│   ├── arxivsub-skill/         # arXiv + 顶会检索
│   ├── talk-normal/            # 回复风格控制
│   └── model-escalation/       # 疑难问题升级
├── hooks/              # SessionStart hook
│   ├── scientist-guardrails.json
│   └── scripts/
│       └── scientist_guardrails.py
└── mcp/
    ├── mcp.json                # 模板配置（不直接使用，install.py 生成实际配置）
    ├── requirements.txt        # MCP 依赖
    └── servers/                # 6 个 MCP 服务器实现
        ├── ai-scientist/
        ├── arxiv-search/
        ├── arxivsub-search/
        ├── dblp-bib/
        ├── google-scholar/
        └── pdf-text/
```

## 🧭 入口选择

| 我想做什么 | 入口 |
|---|---|
| 从研究目标开始（找方向 / 找 baseline / 找创新点） | `@research-pilot` |
| 不知道论文下一步做什么（已有初稿） | `@paper` |
| 写章节 / 润色 / 重写 | `@paper-writer` 或让 `@paper` 委派 |
| 投稿前质量门 / rebuttal 自检 | `@paper-reviewer` 或让 `@paper` 委派 |
| 已有论文想重新校准创新点 | `@paper`（自动进入 Mode 3 创新点挖掘） |
| 通篇优化 | `@paper`（自动进入 Mode 4 综合优化 5 阶段管道） |
| AI Scientist 自动化工作流 | `@scientist` |
| 第一次配置 MCP | `python self/install.py` 或 `/init-mcp` |
| 多轮无解需要换更强模型 | `/model-escalation` |
| 论文检索 | `/arxivsub-skill`（需 `ARXIVSUB_SKILL_KEY`）|

## 🔧 故障排查

**MCP 服务器没出现在工具列表里**
- 重启 Claude Code 或在当前会话运行 `/clear`
- 检查 `.mcp.json` 是否存在并指向正确路径：`cat .mcp.json`
- 重新跑 `python self/install.py --skip-deps`

**`pdf-text` 报缺包**
- 跑 `pip install pdfplumber` 或 `pip install PyPDF2`
- 也可以重新跑 `python self/install.py`，它会自动尝试

**`arxivsub-search` 报 missing_api_key**
- 设置 `ARXIVSUB_SKILL_KEY` 环境变量，或在仓库根 `.env` 中添加 `ARXIVSUB_SKILL_KEY=your_key`
- 重启 Claude Code 让新环境变量生效

**hook 没触发**
- 检查 `.claude/settings.json` 是否包含 `hooks.SessionStart` 条目
- 确认 `python` 在 PATH 中可执行

## 与 third_party/ 的关系

`self/` 是核心闭环：单独的 4 个 agent + 自有 skill + 自有 MCP 即可完成"普通论文研究全流程"和"AI Scientist 工作流"。

`third_party/` 提供扩展能力（superpowers、orchestra、oh-my-paper、imbad0202-research、k-dense-ai 等），由根目录的 `agent.txt` / `skill.txt` / `hook.txt` 清单驱动 `scripts/build_copilot_workspace.py` 打包到 `dist/` 分发包中使用。

如果你只想用 `self/`，跑完 `install.py` 即可；不需要 `third_party/`。
