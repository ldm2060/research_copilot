---
name: scientist-experiment-runner
description: "AI Scientist 实验推进技能。Use when: turning an idea JSON into concrete code edits and experiment runs directly in Copilot, iterating on research experiments, or when user says '开始实验', '推进实验', '从 idea 落地实验'."
---

# scientist-experiment-runner

把 AI Scientist 的“实验推进”改成 Copilot-native 工作流：Copilot 自己读 idea、改代码、跑实验、总结结果，不允许再调用任何 workspace 自定义模型流水线。

## 执行方式

这是 **Copilot-native 模型任务**。Copilot 在会话中完成研究决策，终端只负责运行非模型实验命令。

## 工作流

1. 读取 ideas JSON，明确当前使用的 `idea_idx` 或具体 idea。
2. 识别当前代码面、配置面和运行命令。
3. 做最小必要的代码或配置改动。
4. 用终端运行实验、测试或评估命令。
5. 读取结果文件、日志和指标。
6. 在会话里由 Copilot 继续做下一轮分析和决策。

## 输入

- `load_ideas` 或 ideas JSON 路径
- `idea_idx` 或目标 idea 名称
- 相关代码目录、训练脚本、配置文件、运行命令
- 预期输出目录或现有实验目录

## 输出

- 代码 diff
- 实际运行过的命令
- 关键指标、日志摘要和产物路径
- 下一轮实验建议

## 使用原则

1. Copilot 负责实验策略和结果解释，终端只负责真正的代码执行。
2. 每次只推进一个最小实验切片，先跑通再扩。
3. 如已有实验目录，先用 `inspect_experiment` 或直接读日志，不要盲改。
4. 如果用户只要 plotting / writeup / review，不要误展开完整实验链。

## 禁止事项

- 不要调用任何 workspace 自定义模型流水线
- 不要通过工作区代码自行发起模型调用

## 风险边界

- 如果运行条件不足，只做方案和代码准备，不要假装实验已经跑完
- 如果实验耗时很高，先让用户确认运行预算和预期产物