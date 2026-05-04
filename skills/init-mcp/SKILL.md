---
name: init-mcp
description: "MCP 环境初始化技能。Use when 第一次配置 MCP 服务器、安装 MCP 依赖、检查 MCP 状态、或用户说 '初始化 MCP'、'init mcp'、'setup mcp'、'装环境'、'配置 MCP'。直接调用 self/install.py 完成跨平台一键配置。"
---

# Init MCP

一键完成 MCP 环境配置：安装 Python 依赖 → 写入 `.mcp.json` → 注册 hook → 验证服务器 → 报告可选 secret。

## 唯一入口

`self/install.py` 是跨平台 Python 脚本，已替代旧版 PowerShell 流程。

```bash
python self/install.py
```

支持的 flag：
- `--target /path` 安装到非默认 workspace
- `--dry-run` 只打印计划不写文件
- `--skip-deps` 跳过 pip install
- `--skip-verify` 跳过 MCP 启动握手测试

## 该脚本做了什么

1. **安装 Python 依赖**：读 `self/mcp/requirements.txt`，跑 `pip install`（默认是 `pdfplumber`）。
2. **写 `.mcp.json`**：扫 `self/mcp/servers/` 下所有 server.py，生成 Claude Code 风格的 `.mcp.json`，**用绝对路径**避免 `${workspaceFolder}` 不被展开的问题。
3. **注册 SessionStart hook**：把 `self/hooks/scripts/scientist_guardrails.py` 注入到 `.claude/settings.json`，幂等，不会重复添加。
4. **验证 MCP 启动**：对每个 server 发送 `initialize` JSON-RPC 请求，确认能正常响应。
5. **报告可选 secret**：检查 `ARXIVSUB_SKILL_KEY` 是否设置；如未设置仅警告，不阻塞安装。

## 触发场景

- 新克隆仓库后第一次启用 → 直接跑 `python self/install.py`
- MCP 服务器无响应 → 跑 `python self/install.py --skip-deps` 重新写配置和重新验证
- 验证某个 server 是否可启动 → 跑 `python self/install.py --skip-deps --dry-run` 查看计划，再 `--skip-deps` 单独跑验证

## 当前 self/mcp/mcp.json 中的服务器

| 服务器 | 依赖 | 说明 |
|---|---|---|
| `ai-scientist` | 纯标准库 | runtime 检查、实验目录浏览（非模型） |
| `arxiv-search` | 纯标准库 | arXiv 论文检索，3 秒限流 + 429 重试 |
| `arxivsub-search` | 纯标准库 + `ARXIVSUB_SKILL_KEY` | arXiv + 顶会联合检索 |
| `dblp-bib` | 纯标准库 | DBLP BibTeX 查询，1.5 秒限流 |
| `google-scholar` | 纯标准库 | Scholar 元数据 / 引文格式 |
| `pdf-text` | `pdfplumber`（首选）/ `PyPDF2`（备选） | 本地 PDF 文本提取 |

## 安装后

1. **重启 Claude Code**（或运行 `/clear`）让新的 MCP 配置生效。
2. 在新会话中验证：调用 `arxiv-search` 的 `search_arxiv` 或 `dblp-bib` 的 `search_dblp` 检查工具列表是否就绪。
3. 如果 ARXIVSUB_SKILL_KEY 未设置，`arxivsub-search` 会返回 missing_api_key；按提示在环境变量或 `.env` 里配置即可。

## 注意

- **幂等**：脚本可以多次运行，已存在的 hook 不会重复添加，已存在的 `.mcp.json` 会被覆盖以保持与 `self/mcp/servers/` 同步。
- **不修改全局 settings**：只写项目级 `.claude/settings.json`，不动 `~/.claude/settings.json`。
- **保留其他 MCP 配置**：当前实现会覆盖 `.mcp.json`；如果用户在该文件里有非 `self/` 的 MCP server 条目，需要手动合并。如有此需求，使用 `python self/install.py --dry-run` 查看计划后手动调整。
