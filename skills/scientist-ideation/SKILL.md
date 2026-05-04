---
name: scientist-ideation
description: "AI Scientist idea 生成技能。Use when: turning a topic/workshop Markdown into AI-Scientist-style ideas JSON directly in Copilot, drafting or revising research ideas, or when user says '生成 ideas', 'topic 变成想法', 'AI Scientist 出点子'."
---

# scientist-ideation

把 workshop/topic Markdown 转成 AI-Scientist 可用的 ideas JSON，但模型输出必须由 Copilot 在当前会话里直接生成。

## 执行方式

这是 **Copilot-native 模型任务**。由 Copilot 直接读取 topic、推敲 idea、生成 JSON，并在需要时直接落盘到工作区文件。

## 工作流

1. 读取用户提供的 workshop/topic Markdown。
2. 如有必要，检查现有 ideas JSON，避免重复方向。
3. 直接在会话中生成候选 idea，并按 AI Scientist 约定的 schema 整理。
4. 如果用户要求落盘，直接创建或更新 ideas JSON 文件。

## JSON 结构

- `Name`
- `Title`
- `Short Hypothesis`
- `Related Work`
- `Abstract`
- `Experiments`
- `Risk Factors and Limitations`

## 输入

- `workshop_file` 或 topic Markdown 路径
- 现有 ideas JSON（如果已经存在）
- 用户希望保留的方向约束、数据集约束或资源约束

## 输出

- AI-Scientist 风格 ideas JSON
- 如用户要求，直接写入工作区文件
- 明确说明输出路径、生成条数和筛掉的重复方向

## 禁止事项

- 不要调用任何 workspace 自定义模型 ideation 脚本
- 不要在工作区代码里直接调用任何模型 SDK 生成 ideas

## 失败处理

- 如果 topic 文件结构太弱，先指出缺口并要求补充
- 如果用户要求落盘但 schema 不完整，先在会话里补齐再写文件