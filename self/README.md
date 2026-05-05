# self/ — Research Copilot 工作区资产

本目录是 Claude Code 论文研究工作区的**全部自有资产**：agent、skill、hook、MCP 服务器及其安装脚本。`third_party/` 提供补充能力，但 `self/` 保证核心闭环可独立运行。

## 🚀 一键安装

```bash
python self/install.py
```

自动完成：
1. 安装 Python 依赖（`pdfplumber` 等）
2. 写入项目级 `.mcp.json`（指向 `self/mcp/servers/` 下 MCP 服务器，env 含 `PYTHONFAULTHANDLER=1` / `OMP_NUM_THREADS=1` 缓解 socket 超时）
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
├── README.md                       # 本文件
├── AGENTS.md                       # 8 agent 体系总览
├── SKILLS.md                       # skill 总览
├── install.py                      # 一键安装脚本
├── VERSION
├── agents/                         # 1 总控 + 7 子 agent
│   ├── research-copilot.agent.md       🧭 流程总控（唯一推荐入口）
│   ├── copilot-literature.agent.md     📚 文献调研
│   ├── copilot-ideation.agent.md       💡 创新点交互构思
│   ├── copilot-experiment.agent.md     🧪 实验运行与验证
│   ├── copilot-writer.agent.md         ✍️  论文写作
│   ├── copilot-polisher.agent.md       ✨ 论文润色
│   ├── copilot-reviewer.agent.md       🔍 论文审阅
│   └── copilot-rebuttal.agent.md       💬 rebuttal 回复
├── skills/                         # 22 个 skill（不被 agent 文件硬编码引用）
│   ├── paper-*/                        # 论文写作/改写/检查
│   ├── scientist-*/                    # 实验/绘图/writeup/review 能力
│   ├── arxivsub-skill/                 # arXiv + 顶会检索能力
│   ├── init-mcp/                       # MCP 安装入口
│   ├── talk-normal/                    # 回复风格
│   └── model-escalation/               # 疑难升级
├── runtimes/                       # 静态运行时资产（非 skill）
│   └── scientist-support/runtime/       # AI Scientist runtime 资产
├── hooks/                          # SessionStart hook
├── mcp/                            # 6 个 MCP 服务器
└── scripts/
    └── diagnose-mcp.py             # MCP 响应时间诊断（缓解 socket 超时排查）
```

跨会话工作记忆放在仓库根的 `.copilot/`，由 `@research-copilot` 维护：

```
.copilot/                        ← 默认进 .gitignore
├── state.md                     当前阶段游标 + 推荐下一步         ← 仅 research-copilot 写
├── literature.md                文献库                            ← 仅 copilot-literature 写
├── ideas.md                     创新点候选                        ← 仅 copilot-ideation 写
├── experiments.md               实验流水                          ← 仅 copilot-experiment 写
├── handoff.md                   子 agent 间事实交接（追加）       ← writer/polisher/reviewer/rebuttal
├── decisions.md                 审批门决策记录                    ← 仅 research-copilot 写
└── reviews/round-N.md           每轮独立审稿落盘                  ← 仅 copilot-reviewer 写
```

## 🧭 入口选择

| 我想做什么 | 入口 |
|---|---|
| 不知道下一步做什么 / 想要总控规范流程 | `@research-copilot` |
| 走全流程（从研究目标到投稿） | `@research-copilot` 说"走全流程" |
| 通篇优化 / 投稿冲刺 | `@research-copilot` 说"通篇优化" |
| rebuttal 准备 | `@research-copilot` 说"rebuttal 准备" |
| 我已经知道要做什么，直接调子 agent | `@copilot-<sub>`（见 AGENTS.md 一览表） |
| 第一次配置 MCP | `python self/install.py` 或 `/init-mcp` |
| 多轮无解需要换更强模型 | `/model-escalation` |
| 论文检索 skill | `/arxivsub-skill`（需 `ARXIVSUB_SKILL_KEY`）|
| MCP 卡顿 / socket 超时排查 | `python self/scripts/diagnose-mcp.py` |

## 🔧 故障排查

**MCP 服务器没出现在工具列表里**
- 重启 Claude Code 或在当前会话运行 `/clear`
- 检查 `.mcp.json` 是否存在并指向正确路径
- 重新跑 `python self/install.py --skip-deps`

**`pdf-text` 报缺包**
- 跑 `pip install pdfplumber` 或 `pip install PyPDF2`
- 也可以重新跑 `python self/install.py`

**`arxivsub-search` 报 missing_api_key**
- 设置 `ARXIVSUB_SKILL_KEY` 环境变量，或在仓库根 `.env` 添加
- 重启 Claude Code 让新环境变量生效

**hook 没触发**
- 检查 `.claude/settings.json` 是否包含 `hooks.SessionStart` 条目
- 确认 `python` 在 PATH 中可执行

**agent 调用卡住 / socket 超时**
- 跑 `python self/scripts/diagnose-mcp.py` 找出最慢的 server
- 看每个 server 的 initialize 时长 + tools/list 时长
- `--watch` 可以持续监控偶发卡顿
- 提示：长任务（训练）需要 `run_in_background=true`，子 agent 已默认遵守

## 与 third_party/ 的关系

`self/` 是核心闭环：单独的 1 总控 + 7 子 agent + 自有 skill + 自有 MCP 即可完成"普通论文研究全流程"。

`third_party/` 提供扩展能力（superpowers、orchestra、oh-my-paper、imbad0202-research、k-dense-ai 等），由根目录的 `agent.txt` / `skill.txt` / `hook.txt` 清单驱动 `scripts/build_copilot_workspace.py` 打包到 `dist/` 分发包中使用。

如果你只想用 `self/`，跑完 `install.py` 即可；不需要 `third_party/`。
