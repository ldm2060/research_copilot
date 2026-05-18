# arXIVSub Search MCP Server

通过 arXIVSub API 检索 arXiv 和主流 AI/CV 会议论文，并返回适合在 Copilot 会话中直接筛选和总结的结构化结果。

## 提供的工具

- `search_papers`：按 query、locations、limit、arXiv 天数窗口和 conference years 检索论文，返回完整论文详情和剩余额度。

## 环境要求

- 需要在环境变量或工作区根目录 `.env` 中提供 `ARXIVSUB_SKILL_KEY`
- 使用纯标准库，无需额外安装 Python 依赖

## 返回内容

工具会返回：

- 论文标题、来源、年份、PDF 链接
- 第一作者 / 最后一作者及机构
- `what_about`、`innovations`、`techniques`、`datasets`、`results`、`limitations`
- `quota_remaining`

## 设计边界

- MCP 负责网络访问、鉴权和结构化解析
- skill 负责参数解释、相关性排序和面向用户的最终总结
- 不再通过 skill 自带脚本写临时 JSON 文件或做二次本地提取