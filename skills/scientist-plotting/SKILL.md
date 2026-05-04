---
name: scientist-plotting
description: "AI Scientist 作图技能。Use when: reading experiment outputs and building plots directly in Copilot, drafting plotting scripts, or when user says '聚合作图', '补图表', '整理实验图'."
---

# scientist-plotting

从已有实验目录中直接生成图表和作图脚本，但模型判断与图表设计由 Copilot 在会话里完成。

## 执行方式

这是 **Copilot-native 模型任务**。Copilot 直接读取结果、决定图表结构、编写或修改 plotting 代码；终端只负责运行纯 Python 作图脚本。

## 工作流

1. 读取实验目录中的 summary JSON、日志、CSV、NPY 或已有图表。
2. 确定应该展示哪些指标和对比关系。
3. 直接创建或修改 matplotlib / seaborn / pandas 作图代码。
4. 运行作图脚本并检查产物。
5. 如图表不清晰，再由 Copilot 继续迭代。

## 输入

- `folder`：实验目录
- 结果文件路径和格式
- 用户希望保留的图表规范或论文版式要求

## 输出

- 作图脚本或对现有脚本的修改
- 图表产物路径
- 图表设计理由和关键可视化结论

## 使用约束

- 只在已有实验输出时使用
- 如果结果文件不完整，先指出缺口，不要伪造图表

## 禁止事项

- 不要调用任何 workspace 自定义模型作图脚本
- 不要在 workspace 代码里通过自定义模型调用来“自动作图”

## 结果要求

- 汇报图表路径
- 说明使用了哪些原始结果文件
- 如果图未成功生成，返回真实错误和下一步建议