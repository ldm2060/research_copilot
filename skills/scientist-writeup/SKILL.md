---
name: scientist-writeup
description: "AI Scientist 论文写作技能。Use when: drafting LaTeX or Markdown directly in Copilot from experiment artifacts, preparing paper sections, or when user says '开始写论文', '生成 PDF', '整理成论文'."
---

# scientist-writeup

为已有实验目录直接生成或修改 LaTeX / Markdown 论文内容。模型输出由 Copilot 在会话中直接完成，不允许再通过 workspace 自定义脚本调模型。

## 执行方式

这是 **Copilot-native 模型任务**。Copilot 直接读取实验结果、写作内容和 LaTeX 文件；终端只负责 LaTeX 编译等非模型命令。

## 工作流

1. 读取实验目录、summary 文件、图表和日志。
2. 识别用户提供的 `latex/template.tex` 或现有论文草稿。
3. 直接在编辑器中撰写或修改论文内容。
4. 如用户要求，运行 `pdflatex` / `bibtex` 做编译检查。
5. 汇报生成的文稿路径、编译结果和剩余缺口。

## 输入

- `folder`：实验目录
- `folder/latex/template.tex`：用户自备模板入口
- 图表、结果摘要、参考文献信息和目标版式要求

## 输出

- 修改后的 LaTeX / Markdown 文件
- 编译后的 PDF 路径（如果执行了编译）
- 未满足前提列表

## 使用原则

1. 先确认模板和依赖文件已经存在。
2. 先使用真实实验结果写作，不要编造结论或引用。
3. 当用户只要文字草稿时，不必强行编译 PDF。

## 禁止事项

- 不要调用任何 workspace 自定义模型写作脚本
- 不要通过 workspace 代码自行调用模型生成论文内容

## 结果要求

- 指出修改了哪些论文文件
- 如果编译失败，返回真实 LaTeX 错误摘要
- 如果结论还缺实验支撑，明确说明还缺哪些结果