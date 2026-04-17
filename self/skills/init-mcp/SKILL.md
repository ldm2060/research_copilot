---
name: init-mcp
description: "MCP 环境初始化技能。Use when: setting up MCP servers for the first time, installing dependencies for MCP servers, configuring MCP paths, checking MCP server status, or when user says '初始化MCP', 'init mcp', 'setup mcp', '装环境', '配置MCP'."
---

# MCP 环境初始化 (Init MCP)

你是一个 MCP 环境初始化助手，负责检测并配置当前工作区所需的 MCP 服务器运行环境。

## 职责

1. **检测 Python 环境**：确认系统有可用的 Python 3
2. **安装 MCP 服务器依赖**：检查并安装各 MCP 服务器所需的 Python 包
3. **配置 VS Code MCP 设置**：确保 `.vscode/mcp.json` 指向正确路径
4. **验证 MCP 服务器可用性**：快速测试每个 MCP 服务器是否能正常启动

## 工作流程

### Step 1: 检测工作区 MCP 配置

1. 读取 `self/mcp/mcp.json`，了解工作区定义了哪些 MCP 服务器。
2. 检查 `.vscode/mcp.json` 是否存在且配置正确。如果不存在，从 `self/mcp/mcp.json` 复制并调整路径（将 `${workspaceFolder}/self/mcp/servers/` 替换为 `${workspaceFolder}/.vscode/mcp-servers/`）。

### Step 2: 检测 MCP 服务器源文件

扫描 `self/mcp/servers/` 下的每个子目录，识别 MCP 服务器实现文件。

当前已知服务器：
- **arxiv-search**: `self/mcp/servers/arxiv-search/server.py` — arXiv 论文搜索，纯标准库，无额外依赖
- **dblp-bib**: `self/mcp/servers/dblp-bib/server.py` — DBLP BibTeX 查询，纯标准库，无额外依赖
- **pdf-text**: `self/mcp/servers/pdf-text/server.py` — PDF 文本提取，依赖 `pdfplumber`（首选）或 `PyPDF2`（备选）

### Step 3: 复制服务器文件到 .vscode 目录

如果 `.vscode/mcp-servers/` 不存在或内容过时，将 `self/mcp/servers/` 下的服务器文件复制到 `.vscode/mcp-servers/`：

```
.vscode/mcp-servers/
├── arxiv-search/
│   └── server.py
├── dblp-bib/
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

> arxiv-search 和 dblp-bib 使用纯标准库，无需额外安装。

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
  ✅ arxiv-search — 正常 (纯标准库)
  ✅ dblp-bib — 正常 (纯标准库)
  ✅ pdf-text — 正常 (pdfplumber)

Python 依赖:
  ✅ pdfplumber — 已安装

配置文件:
  📄 .vscode/mcp.json — 已生成
  📁 .vscode/mcp-servers/ — 已同步

下一步:
  1. 重新加载 VS Code 窗口 (Ctrl+Shift+P → "Reload Window")
  2. MCP 服务器将自动启动
  3. 在 Copilot Chat 中即可使用 arxiv-search、dblp-bib 和 pdf-text 工具
```

## 注意事项

- **不要覆盖用户已有的 `.vscode/mcp.json` 中其他服务器配置**：如果文件已存在且有其他服务器条目，只新增/更新 `arxiv-search`、`dblp-bib` 和 `pdf-text`，保留其他条目不变。
- **Python 路径**：如果工作区有 `.venv/` 虚拟环境，优先使用虚拟环境中的 Python。
- **幂等性**：多次运行 init-mcp 不会造成副作用，可以安全地重复执行。
