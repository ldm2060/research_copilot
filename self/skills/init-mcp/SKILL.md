---
name: init-mcp
description: "MCP 环境初始化技能。Use when: setting up MCP servers for the first time, installing dependencies for MCP servers, configuring MCP paths, checking MCP server status, or when user says '初始化MCP', 'init mcp', 'setup mcp', '装环境', '配置MCP'."
---

# MCP 环境初始化 (Init MCP)

你是一个 MCP 环境初始化助手，负责检测并配置当前工作区所需的 MCP 服务器运行环境。

`self/mcp/mcp.json` 是唯一事实来源。init-mcp 必须覆盖其中声明的全部 MCP 服务器，而不是只维护一个过时的子集名单。

## 职责

1. **检测 Python 环境**：确认系统有可用的 Python 3
2. **安装 MCP 服务器依赖**：检查并安装各 MCP 服务器所需的 Python 包
3. **配置 VS Code MCP 设置**：确保 `.vscode/mcp.json` 指向正确路径
4. **验证 MCP 服务器可用性**：快速测试每个 MCP 服务器是否能正常启动

## 工作流程

### Step 1: 检测工作区 MCP 配置

1. 读取 `self/mcp/mcp.json`，了解工作区定义了哪些 MCP 服务器。
2. 检查 `.vscode/mcp.json` 是否存在且配置正确。如果不存在，从 `self/mcp/mcp.json` 复制并调整路径（将 `${workspaceFolder}/self/mcp/servers/` 替换为 `${workspaceFolder}/.vscode/mcp-servers/`）。
3. 后续所有复制、依赖检查和启动验证，都以 `self/mcp/mcp.json` 中的 server 列表为准；如果文档中的示例列表与它不一致，以 `self/mcp/mcp.json` 为准并同步修正文档。

### Step 2: 检测 MCP 服务器源文件

扫描 `self/mcp/servers/` 下的每个子目录，识别 MCP 服务器实现文件。

当前已知服务器：
- **ai-scientist**: `self/mcp/servers/ai-scientist/server.py` — AI Scientist 非模型运维封装，纯标准库；实际 runtime 条件检查会探测 Python、LaTeX、CUDA 和 torch 可用性
- **arxiv-search**: `self/mcp/servers/arxiv-search/server.py` — arXiv 论文搜索，纯标准库，无额外依赖
- **arxivsub-search**: `self/mcp/servers/arxivsub-search/server.py` — arXIVSub 检索，纯标准库，需要 `ARXIVSUB_SKILL_KEY`
- **dblp-bib**: `self/mcp/servers/dblp-bib/server.py` — DBLP BibTeX 查询，纯标准库，无额外依赖
- **google-scholar**: `self/mcp/servers/google-scholar/server.py` — Google Scholar 元数据 / 引文格式检索，纯标准库，无额外依赖
- **pdf-text**: `self/mcp/servers/pdf-text/server.py` — PDF 文本提取，依赖 `pdfplumber`（首选）或 `PyPDF2`（备选）

### Step 3: 复制服务器文件到 .vscode 目录

如果 `.vscode/mcp-servers/` 不存在或内容过时，将 `self/mcp/servers/` 下的服务器文件复制到 `.vscode/mcp-servers/`：

```
.vscode/mcp-servers/
├── ai-scientist/
│   └── server.py
├── arxiv-search/
│   └── server.py
├── arxivsub-search/
│   └── server.py
├── dblp-bib/
│   └── server.py
├── google-scholar/
│   └── server.py
└── pdf-text/
    └── server.py
```

使用 PowerShell 命令：
```powershell
$src = "self/mcp/servers"
$dst = ".vscode/mcp-servers"
if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force }
Get-ChildItem -Path $src -Directory | ForEach-Object {
    $name = $_.Name
    $targetDir = Join-Path $dst $name
    if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force }
    Copy-Item -Path (Join-Path $_.FullName "server.py") -Destination $targetDir -Force
    Copy-Item -Path (Join-Path $_.FullName "README.md") -Destination $targetDir -Force -ErrorAction SilentlyContinue
}
```

### Step 4: 生成 .vscode/mcp.json

根据 `self/mcp/mcp.json` 的模板，在 `.vscode/mcp.json` 中生成配置，将 `server.py` 路径指向 `.vscode/mcp-servers/` 目录：

```json
{
  "servers": {
    "ai-scientist": {
      "type": "stdio",
      "command": "python",
      "args": ["-u", "${workspaceFolder}/.vscode/mcp-servers/ai-scientist/server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1"
      }
    },
    "arxiv-search": {
      "type": "stdio",
      "command": "python",
      "args": ["-u", "${workspaceFolder}/.vscode/mcp-servers/arxiv-search/server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1"
      }
    },
    "arxivsub-search": {
      "type": "stdio",
      "command": "python",
      "args": ["-u", "${workspaceFolder}/.vscode/mcp-servers/arxivsub-search/server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1"
      }
    },
    "dblp-bib": {
      "type": "stdio",
      "command": "python",
      "args": ["-u", "${workspaceFolder}/.vscode/mcp-servers/dblp-bib/server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1"
      }
    },
    "google-scholar": {
      "type": "stdio",
      "command": "python",
      "args": ["-u", "${workspaceFolder}/.vscode/mcp-servers/google-scholar/server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1"
      }
    },
    "pdf-text": {
      "type": "stdio",
      "command": "python",
      "args": ["-u", "${workspaceFolder}/.vscode/mcp-servers/pdf-text/server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Step 5: 安装 Python 依赖

检查并安装各 MCP 服务器所需的 Python 第三方包：

```powershell
# pdf-text 服务器依赖 pdfplumber（首选）
python -c "import pdfplumber" 2>$null
if ($LASTEXITCODE -ne 0) {
    pip install pdfplumber
}
```

如果 pdfplumber 安装失败，尝试安装备选依赖：
```powershell
python -c "import PyPDF2" 2>$null
if ($LASTEXITCODE -ne 0) {
    pip install PyPDF2
}
```

> ai-scientist、arxiv-search、arxivsub-search、dblp-bib 和 google-scholar 的 server 本体都使用纯标准库，无需额外安装 Python 包。

如果启用了 arxivsub-search，额外确认以下任一条件满足：

```powershell
$env:ARXIVSUB_SKILL_KEY
```

或工作区根目录存在 `.env` 且包含：

```text
ARXIVSUB_SKILL_KEY=your_key_here
```

如果启用了 ai-scientist，额外确认宿主环境里至少具备以下非模型前提：

- `pdflatex` / `bibtex` / `pdftotext` / `chktex`
- 可用的 Python 环境
- 如需本地实验检查，还应保证 `torch` 和 CUDA 条件能被 `validate_runtime` 探测到

### Step 6: 验证服务器可启动

对每个 MCP 服务器做快速启动测试——向 stdin 发送 MCP `initialize` 请求，检查是否返回正确的 JSON-RP 响应：

```powershell
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}' | python -u .vscode/mcp-servers/arxiv-search/server.py
```

### Step 7: 输出初始化报告

输出一份清晰的报告：

```
✅ MCP 环境初始化完成

服务器状态:
  ✅ ai-scientist — 正常 (纯标准库 server, 运行时会额外检查宿主条件)
  ✅ arxiv-search — 正常 (纯标准库)
  ✅ arxivsub-search — 正常 (纯标准库, 需 API key)
  ✅ dblp-bib — 正常 (纯标准库)
  ✅ google-scholar — 正常 (纯标准库)
  ✅ pdf-text — 正常 (pdfplumber)

Python 依赖:
  ✅ pdfplumber — 已安装

配置文件:
  📄 .vscode/mcp.json — 已生成
  📁 .vscode/mcp-servers/ — 已同步

下一步:
  1. 重新加载 VS Code 窗口 (Ctrl+Shift+P → "Reload Window")
  2. MCP 服务器将自动启动
  3. 在 Copilot Chat 中即可使用 ai-scientist、arxiv-search、arxivsub-search、dblp-bib、google-scholar 和 pdf-text 工具
```

## 注意事项

- **不要覆盖用户已有的 `.vscode/mcp.json` 中其他服务器配置**：如果文件已存在且有其他服务器条目，只新增/更新 `self/mcp/mcp.json` 中声明的服务器，保留其他条目不变。
- **Python 路径**：如果工作区有 `.venv/` 虚拟环境，优先使用虚拟环境中的 Python。
- **幂等性**：多次运行 init-mcp 不会造成副作用，可以安全地重复执行。
