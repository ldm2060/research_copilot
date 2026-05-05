# self/mcp — 自有 MCP 服务器

## 目录结构

```
self/mcp/
├── README.md            ← 本文件
├── requirements.txt     ← MCP 服务器的 Python 依赖（pdfplumber 等）
└── servers/             ← 6 个 stdio MCP 服务器（每个一个子目录 + server.py）
    ├── ai-scientist/
    ├── arxiv-search/
    ├── arxivsub-search/
    ├── dblp-bib/
    ├── google-scholar/
    └── pdf-text/
```

## 真正生效的 .mcp.json

仓库**不**提交 `.mcp.json`。运行 `python self/install.py` 时会：

1. 扫描 `self/mcp/servers/` 下每个含 `server.py` 的子目录
2. 把绝对路径写到仓库根目录的 `.mcp.json`（`mcpServers.<name>.args` 是 `["-u", "<abs-path>/server.py"]`）
3. 注入跨平台稳健环境变量（`PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`、`PYTHONUNBUFFERED=1`、`PYTHONFAULTHANDLER=1`、`OMP_NUM_THREADS=1`）

请不要手写 `.mcp.json`；改了 `self/mcp/servers/` 后重新跑 install 即可。

## 添加新 server

1. 在 `self/mcp/servers/<name>/` 放一个 `server.py`，按 stdio JSON-RPC 协议处理 `initialize` / `tools/list` / `tools/call`
2. 如果有第三方依赖，加到 `requirements.txt`
3. 重新跑 `python self/install.py`，install 脚本会自动注册并跑 initialize 握手验证

## 故障排查

- 启动慢 / socket 超时：`python self/scripts/diagnose-mcp.py [--watch]`
- 依赖缺失：`python self/install.py --skip-verify` 跑一次让它先装依赖
- 单 server 报错：`python self/mcp/servers/<name>/server.py` 直接跑，看 stderr
