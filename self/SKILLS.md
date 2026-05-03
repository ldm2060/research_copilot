# Skills 总览

`self/skills/` 下每个 skill 是独立子目录，含 `SKILL.md` 文件。Claude Code 会按 SKILL frontmatter 的 description 语义自动匹配，也可由用户 `/skill-name` 显式触发。

## 🚀 一键安装

第一次使用前在仓库根运行：

```bash
python self/install.py
```

该脚本会自动配置 MCP 服务器、注册 hook、安装 Python 依赖。详见 [`self/README.md`](README.md)。

---

## 🧪 AI Scientist 工作流

被 `scientist` agent 调用的执行端 skill。每个 skill 在 Claude 会话中直接生成模型输出，不依赖 workspace 自定义 Python 流水线。

| Skill | 目录 | 说明 |
|-------|------|------|
| **scientist-runtime-init** | `scientist-runtime-init/` | 🧰 通过 `ai-scientist` MCP 的 `validate_runtime` 检测 Python / LaTeX / poppler / CUDA / scientist-support runtime |
| **scientist-ideation** | `scientist-ideation/` | 💡 把 workshop topic markdown 转成结构化 ideas JSON |
| **scientist-experiment-runner** | `scientist-experiment-runner/` | 🌲 推进实验循环、改代码、跑命令、读结果 |
| **scientist-plotting** | `scientist-plotting/` | 📊 汇总实验结果，生成图表脚本与图片 |
| **scientist-writeup** | `scientist-writeup/` | ✍️ 基于 `latex/template.tex` 撰写 LaTeX 与 PDF |
| **scientist-review** | `scientist-review/` | 🔍 对 PDF 或文稿做文本审稿 |

## 📄 论文写作 / 改写

被 `paper-writer` agent 或 `paper` agent 综合优化模式调用。

| Skill | 目录 | 说明 |
|-------|------|------|
| **paper-translate** | `paper-translate/` | 🌐 中→英学术翻译，符合顶会规范 |
| **paper-en2zh** | `paper-en2zh/` | 🌐 英→中翻译，自动去引用并将公式转自然语言 |
| **paper-polish** | `paper-polish/` | ✨ 深度润色：严谨性、时态、句式、零错误 |
| **paper-expand** | `paper-expand/` | 📝 扩写：展开隐含逻辑、补衔接词，不注水 |
| **paper-shorten** | `paper-shorten/` | ✂️ 缩写：压缩 5-15 词同时保留全部技术细节 |
| **paper-deai** | `paper-deai/` | 🤖→👤 去 AI 味：替换滥用词、移除机械连接词 |

## 📊 论文内容生成

| Skill | 目录 | 说明 |
|-------|------|------|
| **paper-experiment-analysis** | `paper-experiment-analysis/` | 📈 ML 实验数据 → SOTA 对比 + 消融 LaTeX 段落 |
| **paper-figure-caption** | `paper-figure-caption/` | 🖼️ 中文图描述 → 英文 figure caption（Title / Sentence Case） |
| **paper-table-caption** | `paper-table-caption/` | 📋 中文表描述 → 英文 table caption |

## 🔍 审稿 / 检查

被 `paper-reviewer` agent 或 `paper` agent Mode 4 调用。

| Skill | 目录 | 说明 |
|-------|------|------|
| **paper-review** | `paper-review/` | 🔎 顶会审稿人视角批判性分析 |
| **paper-logic-check** | `paper-logic-check/` | 🧩 逻辑一致性 / 术语矛盾 / 因果归因 |
| **paper-sanity-check** | `paper-sanity-check/` | ✅ 投稿前 6 项检查：逻辑、引用、贡献-证据、数据、复现、清晰度 |

## 🔧 工具 / 元 skill

| Skill | 目录 | 说明 |
|-------|------|------|
| **arxivsub-skill** | `arxivsub-skill/` | 🔍 通过 `arxivsub-search` MCP 检索 arXiv + 顶会（CVPR/ICCV/ICLR/ICML/NeurIPS/AAAI/MICCAI） |
| **init-mcp** | `init-mcp/` | 🚀 调用 `self/install.py` 完成 MCP 一键安装 |
| **talk-normal** | `talk-normal/` | 💬 回复风格控制：直接简洁、禁止否定句式、按复杂度选择结构 |
| **model-escalation** | `model-escalation/` | 🧯 多轮无解时输出可转交更强模型的求助摘要 |

## 🔌 MCP 服务器

通过 `python self/install.py` 自动配置。所有 server 在 `self/mcp/servers/`，配置文件由 install 脚本写入项目级 `.mcp.json`。

| 服务器 | 位置 | 说明 |
|--------|------|------|
| **ai-scientist** | `self/mcp/servers/ai-scientist/` | 🧪 AI Scientist 非模型运维：runtime 检查、实验目录浏览 |
| **arxiv-search** | `self/mcp/servers/arxiv-search/` | 🔍 arXiv 检索（关键词 / 作者 / arXiv ID），3 秒限流 + 429 重试 |
| **arxivsub-search** | `self/mcp/servers/arxivsub-search/` | 🔍 arXiv + 顶会联合检索，需 `ARXIVSUB_SKILL_KEY` |
| **dblp-bib** | `self/mcp/servers/dblp-bib/` | 📚 DBLP BibTeX 查询（标准条目，可直接插入 `references.bib`），1.5 秒限流 |
| **google-scholar** | `self/mcp/servers/google-scholar/` | 🔎 Scholar 元数据 / 引文格式（arXiv 无结果时的补充） |
| **pdf-text** | `self/mcp/servers/pdf-text/` | 📄 PDF 逐页文本提取（pdfplumber 首选 / PyPDF2 备选） |
