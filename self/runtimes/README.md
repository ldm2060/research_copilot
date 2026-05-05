# self/runtimes — 静态运行时资产

存放被 MCP server / hook / skill 引用的**静态、非 SKILL** 资产。这里的子目录**不**是 Claude Code skill（没有 `SKILL.md`、不会被 `/<name>` 触发）。

## 子目录

| 目录 | 用途 | 引用方 |
|---|---|---|
| `scientist-support/runtime/` | AI Scientist 上游 runtime 资产（LICENSE、README） | `self/hooks/scripts/scientist_guardrails.py`、`self/mcp/servers/ai-scientist/server.py` 的 `validate_runtime` 工具 |

## 为什么不放 `self/skills/` 下

Claude Code 会把 `skills/<name>/` 当成 skill 加载；如果该目录没有 `SKILL.md` 会触发警告。把纯静态的 runtime 资产挪到 `self/runtimes/` 后：

- skills/ 下每个目录都是合法 skill
- runtime 资产仍可被 hook 与 MCP 找到（路径搜索器会回落到 `self/runtimes/...` 与 `.github/runtimes/...`）
