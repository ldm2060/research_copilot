# Skills 总览

本目录包含论文写作与研究过程中的各类专用 Skill。每个 Skill 以独立子目录中的 `SKILL.md` 文件定义，Copilot 会根据任务语义自动匹配或由用户手动调用。

## 📄 论文写作类

| Skill | 目录 | 说明 |
|-------|------|------|
| **paper-translate** | `paper-translate/` | 🌐 中→英学术翻译。将中文草稿翻译为符合顶级会议规范的英文 LaTeX，包含时态优化、自然过渡和去AI味处理。 |
| **paper-en2zh** | `paper-en2zh/` | 🌐 英→中翻译。将英文 LaTeX 转为流畅易读的中文，自动去除引用命令并将数学公式转为自然语言描述。 |
| **paper-polish** | `paper-polish/` | ✨ 深度润色。对英文 LaTeX 进行学术级深度重写，提升严谨性、修正语法时态、优化句式流畅度，追求零错误出版标准。 |
| **paper-expand** | `paper-expand/` | 📝 扩写。在保持简洁的前提下展开隐含逻辑、补充必要衔接词和丰富描述，不添加废话。 |
| **paper-shorten** | `paper-shorten/` | ✂️ 缩写。通过句法优化和冗余删除压缩 5-15 词，同时保留所有核心信息和技术细节。 |
| **paper-deai** | `paper-deai/` | 🤖→👤 去AI味。识别并消除机器生成的写作模式，将机械性措辞转化为自然的人类学术语言。 |

## 📊 论文内容类

| Skill | 目录 | 说明 |
|-------|------|------|
| **paper-experiment-analysis** | `paper-experiment-analysis/` | 📈 实验分析。从 ML 实验数据中提取趋势和洞察，生成含 SOTA 对比和消融发现的严谨 LaTeX 分析段落。 |
| **paper-figure-caption** | `paper-figure-caption/` | 🖼️ 图标题。将中文图片描述转为符合 Title Case / Sentence Case 规范的英文 figure caption。 |
| **paper-table-caption** | `paper-table-caption/` | 📋 表标题。将中文表格描述转为规范格式的英文 table caption，自动选择 Title Case 或 Sentence case。 |

## 🔍 检查与审稿类

| Skill | 目录 | 说明 |
|-------|------|------|
| **paper-review** | `paper-review/` | 🔎 模拟审稿。以顶会审稿人视角对论文进行批判性分析，评估贡献、实验充分性和逻辑一致性，给出可操作的改进建议。 |
| **paper-logic-check** | `paper-logic-check/` | 🧩 逻辑检查。终审校对环节，检查逻辑一致性、术语矛盾、因果归因错误和严重语病。 |
| **paper-sanity-check** | `paper-sanity-check/` | ✅ 投稿前检查。6 项全面检查：逻辑流程、浮动体引用、贡献-证据对齐、数据一致性、可复现细节、写作清晰度。 |

## 🔧 工具类

| Skill | 目录 | 说明 |
|-------|------|------|
| **arxivsub-skill** | `arxivsub-skill/` | 🔍 arXiv 论文搜索。通过 arXivSub API 检索 arXiv 和主流 AI/CV 会议（CVPR, ICCV, ICLR, ICML, NeurIPS 等）的最新论文。 |
| **talk-normal** | `talk-normal/` | 💬 回复风格控制。确保输出直接简洁，禁止否定句式，按内容复杂度选择结构化输出格式。 |
| **init-mcp** | `init-mcp/` | 🚀 MCP 环境初始化。自动检测并配置工作区所需的 MCP 服务器环境（Python 依赖、路径配置等），支持 arxiv-search、dblp-bib 和 pdf-text 三个服务器。 |

## 🔌 MCP 服务器

以下 MCP 服务器由 `init-mcp` skill 自动配置，也可单独使用：

| 服务器 | 位置 | 说明 |
|--------|------|------|
| **arxiv-search** | `self/mcp/servers/arxiv-search/` | 🔍 arXiv 论文搜索。支持关键词、作者、arXiv ID 搜索，返回标题、作者、摘要、PDF 链接等。内置 3 秒限流 + 429 重试。 |
| **dblp-bib** | `self/mcp/servers/dblp-bib/` | 📚 DBLP BibTeX 查询。搜索 DBLP 出版物并返回标准 BibTeX 条目，可直接插入 `references.bib`。内置 1.5 秒限流 + 429 重试。 |
| **pdf-text** | `self/mcp/servers/pdf-text/` | 📄 PDF 文本提取。从本地 PDF 文件逐页提取文本，支持分页控制。依赖 `pdfplumber`（首选）或 `PyPDF2`（备选）。 |
