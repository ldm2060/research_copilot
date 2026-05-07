---
name: paper-architecture-web-drawing
description: "This skill should be used when the user asks to \"架构图\", \"结构图\", \"method figure\", \"overview figure\", \"pipeline diagram\", \"draw methodology\", \"网页绘图\", or wants a paper's abstract and method transformed into a publication-ready architecture diagram rendered as HTML/SVG (with Python-generated SVG sub-figures for heatmaps / distributions / scatter / matrices). Enforces compactness numerics and a 10-round self-check loop. 论文结构图网页绘制技能。"
version: 0.5.0
---

# 论文结构图网页绘制 (Paper Architecture Web Drawing)

输入：论文摘要 + 方法（或工作区中的 `.tex/.md/.txt` 论文文件）。
输出：单文件 HTML + inline SVG 的顶会风格论文方法图，可选同源独立 `.svg`。
不适用：折线/柱状/散点等数据图、海报、艺术插画、纯 Mermaid 草图、方法尚未成型时。

## 0. 不可漏的 7 条铁律

1. **白底 + 矢量优先**：纯白背景，inline SVG 主导。**禁渐变、阴影、玻璃拟态、光晕、装饰背景**。仅 MathJax/KaTeX 可联网。
2. **至少 3 个真图元**：weights / distribution / tokens / cache / codebook / attention / scatter 等抽象对象画成矩阵格、热力图、直方图、boxplot、散点。**仅文字框 = 不合格**。能用 Python 生成的图元（见 §2.7）**优先 Python**，不要硬手写复杂热力图或曲线。
3. **公式贴近模块**：LaTeX 公式作为对应模块的局部锚点，**不堆到底栏**。HTML 中通过 MathJax/KaTeX 渲染，不写 ASCII 伪公式（`sum(...)/sum(...)`）。
4. **字号下限（顶会方法图密度）**：主标题 ≥ 26 px，区块标题 ≥ 22 px，模块标签 ≥ 18 px，公式标签 ≥ 16 px，辅助 ≥ 14 px。**版面紧不下时先删字、不缩字**。viewBox 必须给足空间，禁画 1060×330 这种窄条压字。
5. **英文标签**：禁中文标签，禁单组件描述超过 10 词。
6. **浏览器实测**：写完 HTML 必须在浏览器打开并截图检查。Windows 下 `start ""  "$(pwd -W)/path.html"` 或 `python -m http.server`。
7. **每条箭头有论文依据**：禁止臆造模块、损失或反馈回路。

## 1. 严禁的视觉模式

- **SmartArt / PowerPoint 流程图**：等宽圆角卡片串联、所有节点同样圆角同样边框。
- **Dashboard / 海报式**：右侧 KPI 列、结果卡片栈、营销 badge、统计数字贴纸、发光强调。
- **网页 UI 拼贴**：标题条 + 副标题条 + 内容卡的组件模式；pill badge 阵列。
- **大框 + 箭头 + 底部 legend** 三件套主导画面。
- **顶部 stage label + 底部 caption / problem statement / method summary**。图应自解释。
- **bypass / feedback / 虚线穿过** 模块标题、公式、badge、结果数字。
- **小字号 + 大留白** 换内容容量。
- 高饱和红绿紫，或同时出现 5 种以上显眼浅色块。

## 2. 工作流程

### 2.1 读取论文

- 在工作区找 `.tex/.md/.txt`、笔记或整理后的方法说明，读取 Abstract / Method / Approach / Overview / Framework。
- 多个候选文件时**先确认目标**，不盲猜。
- 只读重建主流程所需上下文。

### 2.2 抽取结构（绘前必填）

对每个关键模块写明 5 个字段。说不清就**不要落图**：

| 字段 | 内容 |
|---|---|
| `Name` | 短而稳的英文模块名，不写口号 |
| `Type` | 输入/编码/对齐/检索/融合/优化/损失/输出 |
| `Is novel?` | 是否贡献点，是否需视觉高亮 |
| `Internal elements` | 内部最值得可视化的对象/运算（attention、MLP、codebook、feature map、cache update） |
| `Topology role` | 主链节点 / 并行分支 / 汇聚点 / 反馈点 / 训练专用支路 |

### 2.3 选布局族（按顺序判别）

1. 显式反馈 / 迭代 / 交替优化 / until convergence → **Loop / U-shape**
2. train/infer 或 stage1/stage2 或 coarse/fine 或 retrieve/generate → **Two-stage**
3. ≥2 个语义独立分支后汇聚到共享主模块 → **Multi-branch with merge**
4. 窄版心 / 单栏纵读 → **Linear vertical**
5. 3-6 个串行阶段、无强反馈 → **Linear horizontal**（默认）
6. 主链中嵌局部复杂子结构 → **Hybrid composition**

**Tie-breakers**：能保住强视觉中心、能给关键机制面板留足面积、能减少箭头交叉与对角穿字、能让输入输出形成自然前后对照的布局优先。

**否决条件**（任一中则换布局）：
- 留不出主示意图区，所有模块变成等权重小框；
- 需要 >2 条长跨区连线才能讲清主流程；
- 关键公式被迫堆到边角；
- 输出区与辅助说明争抢空间；
- 必须缩字号或加空白才能勉强塞下。

### 2.4 默认蓝图

**输入对象 → 2-3 个机制区块 → 输出对象**

- **左**：tensor / weights / KV cache / tokens / feature grid 等可视化输入对象（不是文字框）。
- **中**：每个区块以一个**主示意图**为核心，而非均匀小卡片并列。codebook / sensitivity map / objective / memory 等辅助对象贴近对应机制。
- **右**：变换后的同类对象，优先显示**结构变化**而非 KPI 总结。
- 输入 ↔ 输出**复用同图形母题**展示状态变化（如压缩前后的同形 cache blocks）。
- 仅高亮 1-2 个核心贡献模块：同色系更重边框 / 略深底色 / 局部 bracket / callout。**不靠**高饱和或大徽标。

### 2.5 配色（5 选 1，全图保持一族）

| 色族 | 适用 |
|---|---|
| **Blue-Gray** | 通用 pipeline / 系统图（默认首选） |
| **Warm Tones** | 适度强调创新点 |
| **Green-Cyan** | 生成 / 生物 / 轻盈主题 |
| **Purple-Blue** | 理论 / 数学味重 |
| **Monochrome** | 极简 / 黑白打印友好 |

**色彩角色**（任选色族都遵循）：Primary background（普通模块）、Secondary background（次要模块）、Accent background（贡献模块）、Input/Output background（更浅）、Primary border、Accent border、**Arrow color 全图统一深色**、Main text、Secondary text。**禁止跨族拼贴**。

### 2.6 排版

- 线宽 2-3 档：主流程 / 次级结构 / 坐标辅助。
- 圆角中小，不大圆角网页卡片。
- **sans 标签 + serif 数学公式**。
- 模块标题短而稳，不用口号；副标题默认省略。
- 训练专用分支：更浅底色 + 虚线箭头。
- 长路径（bypass、feedback、training-only branch）沿区块外缘走线，不穿子面板文字密集区。
- 紧凑优先：通过对齐、共边、近距分组压版，不通过缩小字号容纳内容。
- 允许非对称布局；面积反映重要性，不追求栏目平均。

### 2.7 抽象对象 → 图元（Python vs 手写 SVG）

| 论文对象 | 图元 | 推荐生成方式 |
|---|---|---|
| `weights` / `kernels` / `parameters` matrix | 矩阵格 + 离群列/点高亮 | matplotlib `imshow` |
| `distribution` / `density` / histogram | histogram / KDE 曲线 | matplotlib `hist` + `kdeplot` |
| `outliers` / `IQR` / `boxplot` | boxplot + Q1/Q3/whisker 标注 | matplotlib `boxplot` |
| `scatter` / 双变量关系 / 误差对比 | 散点 + 对角线 + 高亮区 | matplotlib `scatter` |
| `attention` / `similarity` / `heatmap` | 二维热力图 + colorbar | matplotlib `imshow` (cmap=viridis/coolwarm) |
| `eigenvectors` / `subspace` / `basis` | 圆盘+方向箭头 / 坐标轴 | matplotlib `quiver` 或手写 SVG |
| `quantization` / `clustering` / `codebook` | bin 切分线 / 簇中心点 / lookup blocks | matplotlib + `axvline` 标注 centroid |
| `tokens` / `patches` / `cache blocks` | 砖块阵列 + bit-width tag | 手写 SVG（结构化） |
| `loss landscape` / 3D surface | contour / pcolormesh | matplotlib |
| `loss` / `objective` / `constraint` | 短公式框（贴近模块） | 手写 SVG + MathJax |
| 模块框、箭头、formula chip、bracket | 框/线/标签 | **手写 SVG**（Python 表达不优雅） |

**判别规则**：图元有数值/分布/几何就用 Python 出 SVG；图元是结构化布局（框、箭头、公式槽）就手写 SVG。

### 2.7.1 Python 生成 SVG 子图（matplotlib）

放一个 `figures/<paper>_components.py`，每个子图保存为 `.svg`，主 HTML 通过 inline `<svg>` 嵌入或 `<img src=...svg>` 引用。**优先 inline**（单文件交付、可二次手改）。

最小骨架：

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 14,
    "axes.linewidth": 1.0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.fonttype": "none",   # 文本保留为 <text> 不外形化
})

def save(fig, path):
    fig.savefig(path, format="svg", bbox_inches="tight",
                pad_inches=0.05, transparent=True)
    plt.close(fig)
```

**强制约定**：

- `svg.fonttype="none"`：文本保持为可编辑 `<text>`，不被转 path。
- `transparent=True` + 主 HTML 白底，避免双层底色。
- 单子图字号 ≥ 12（嵌入后会被缩放，保持可读）。
- 仅用调色族对应的颜色（见 §2.5），不用 matplotlib 默认 `tab:blue`。
- 一个图一个函数，不在脚本里 `plt.show()`。

### 2.7.2 inline 嵌入

Python 生成 `comp_a.svg` 后，在主 HTML 中：

```html
<g transform="translate(120, 80)">
  <!-- inline-svg-include: comp_a.svg -->
</g>
```

实际操作两条路径任选其一：

- **拷贝 inline**：把 `comp_a.svg` 的内层 `<g>...</g>` 直接贴进主 SVG 对应位置，外层 `<svg>` 头丢弃。
- **objectreference**：主 HTML 用 `<image href="comp_a.svg" x=.. y=.. width=..>` 或 `<foreignObject>`；交付前**必须**在浏览器验证渲染。

inline 嵌入后**手动调整尺寸/位置**：matplotlib 默认 viewBox 与主图坐标系不同，需要包一层 `<g transform="translate(x,y) scale(s)">`。

### 2.8 公式承载

- 每个关键公式有专属承载槽（局部白底公式槽 / 模块内嵌公式区 / 与图元对齐的 anchor）。**不当漂浮网页贴纸**。
- 长公式拆为两条局部标签或更短等价表达，不用一整行长公式横压区块。
- objective / update / normalization / threshold 放模块内部短公式槽，不堆到底部统一说明区。
- 公式 chip 顶部贴近其主示意图底部 ≤ 15px，不要中间留大空。

### 2.9 紧凑度规范（数字硬指标）

绝大多数"看起来不像论文方法图"的根因是**版面松散**。强制以下数值上限：

| 指标 | 上限 | 说明 |
|---|---|---|
| 单 panel 内部空白占比 | ≤ 15% | 标题+图元+公式+标签覆盖应 ≥ 85% panel 面积 |
| 主示意图占 panel 可视面积比 | ≥ 65% | 即"图本身大、文字附属" |
| 跨 panel 横向间距 | 20-40 px (viewBox 单位) | 大于 40 视为松散 |
| 跨 panel 纵向间距 | 15-30 px | 上下两行之间 |
| 标题底缘到首个 panel 的距离 | ≤ 30 px | 顶部不留大空 |
| viewBox 高宽比 | 0.45 - 0.65 (单行 4 panel) | 顶会论文 figure\* 接近 2:1 |
| panel 顶部 padding（标题以上） | ≤ 16 px | 标题贴边 |
| panel 底部 padding（最后元素以下） | ≤ 16 px | 不允许大段 dead space |
| 图元 ↔ 形状/标签的距离 | ≤ 10 px | 紧贴对齐而非自由漂浮 |
| 同 panel 内重复 `<rect>` 嵌套层数 | ≤ 2 | 三层嵌套 = 卡片膨胀 |

**panel 等高陷阱**：同一行的 4 个 panel 不必等高。Input/Output 通常比 mechanism panels 矮 200-300 px。**强制等高 = 主动制造空白**。

**测量方法**：渲染后用浏览器开发者工具抽查。或在 SVG 里用 `<rect>` 临时画 panel 实际占用边界，对比 panel 边框，目测 dead space 比例。

### 2.10 自检自改流程（**强制 ≥ 10 轮**）

写完 HTML 后**不允许直接交付**。必须按下表完成 10 轮迭代，每轮：

1. 用 `chrome --headless --screenshot` 渲染 PNG。
2. 打开 PNG，写下"本轮 focus 维度的 3 个最不合规处"（必须具体，禁止"看起来不错"）。
3. 修 HTML / Python / 重新生成子图。
4. 重新渲染。

| Round | Focus | 必查项 |
|---|---|---|
| 1 | **拓扑保真** | 与论文 method 描述对齐？模块、箭头、损失、反馈无缺无增？|
| 2 | **紧凑度** | 测量每个 panel 的空白占比，逐个收紧；trim viewBox |
| 3 | **字号** | 抽查每条文本，对照 26/22/18/16/14 下限；超下限的删字不缩字 |
| 4 | **配色纪律** | 全图色族单一？无渐变 / 阴影 / 玻璃拟态 / 光晕 / 装饰底？|
| 5 | **公式锚定** | LaTeX 通过 MathJax 真渲染？chip 紧贴对应模块？|
| 6 | **箭头走线** | 主流程、bypass、feedback 无穿字 / 穿公式 / 穿 badge |
| 7 | **Python 子图** | `svg.fonttype="none"`、配色与主图同族、aspect 匹配 panel 形状 |
| 8 | **视觉层级** | 主阅读路径一眼可辨？1-2 个贡献 panel 高亮？非贡献模块克制？|
| 9 | **反模式扫描** | 像 SmartArt / PowerPoint / dashboard / 网页 UI / 海报？|
| 10 | **论文 context** | 把图放进 ICML/CVPR 双栏排版，是否突兀？盖住标题后是否仍像该论文？|

**单轮不允许跳过**。如某轮发现的问题已被前轮修过且当前已合规，仍需写下"本轮 0 issues"作为显式记录，而不是默默跳过。

**Round 11+ 可选**：仅当任一轮的修改触发了新的违规（比如改紧凑导致字裁切），需要补轮直至稳定。

### 2.11 快速回退条件

迭代过程中出现以下任一，直接回退到 §2.4 默认蓝图重画，不要继续微调：

- 累计修了 3 轮还无法达到 §2.9 的紧凑度数字。
- 主示意图本质上是文字堆叠而非图形。
- viewBox 调到再小都有大空白 → 通常是 panel 高度等齐导致，参 §2.9 panel 等高陷阱。

## 3. 文件位置

- 仓库有 `figures/` 或 `dist/figures/` → 优先输出到该目录。
- 否则放论文源文件相邻位置。
- 默认产物：
  - `method_architecture.html`（主图，inline SVG）
  - `method_architecture.svg`（同源独立 SVG，可选）
  - `<paper>_components.py`（生成各 Python 子图的脚本）
  - `comp_*.svg`（Python 子图源文件，便于回头修改）
- 主 HTML 不联网（仅 MathJax/KaTeX CDN 例外）。

## 4. 完工检查清单

逐项确认。任一不通过则继续迭代：

- [ ] 单文件 HTML 可直接打开，纯白底，inline SVG 主导
- [ ] 至少 3 个真图元（heatmap/histogram/boxplot/scatter/matrix），其中**至少 1 个由 Python 生成**当对象适合数值表达
- [ ] 每个主要机制区块有主示意图，**非仅标题 + 公式 + 卡片**
- [ ] Python 子图 `svg.fonttype="none"`，文本可编辑
- [ ] Python 子图配色与主图同族，未用 matplotlib 默认色
- [ ] **紧凑度（§2.9）**：每个 panel 内部空白 ≤ 15%，主示意图占 panel ≥ 65%，跨 panel 间距 20-40 px
- [ ] **panel 不强制等高**：Input/Output 比 mechanism panels 矮 200-300 px
- [ ] **viewBox 高宽比 0.45-0.65**（单行 4 panel）；上下边 padding ≤ 30 px
- [ ] 公式有专属承载槽，与对应模块对齐，未漂浮，未与 codebook/箭头/badge 挤压
- [ ] LaTeX 公式正确渲染（MathJax/KaTeX），非 ASCII 伪公式
- [ ] 字号符合下限 26/22/18/16/14
- [ ] 全英文标签，单组件描述 ≤ 10 词
- [ ] 1-2 个核心贡献模块高亮（克制方式，非高饱和/大徽标）
- [ ] 配色单族，3-5 档；**无渐变/阴影/光晕/玻璃拟态**
- [ ] 主流程箭头未穿字、未穿公式、未穿 badge；长路径沿外缘走
- [ ] 输入 ↔ 输出存在图形母题复用或合理前后对照
- [ ] 顶部无 stage label / phase label，底部无 caption / problem statement / 页脚文字
- [ ] 没有右侧 KPI 列 / 结果卡片栈 / dashboard / 海报式总结栏
- [ ] 不像 SmartArt / PowerPoint / 网页组件 / 产品宣传图
- [ ] **完成 ≥ 10 轮自检自改（§2.10）**，每轮有 PNG 截图与 3 处差异记录
- [ ] 每条箭头对应真实数据流 / 控制流 / 监督信号
- [ ] 没有臆造论文未出现的模块、损失或反馈

## 5. 交付契约

1. 单文件 HTML 主图（inline SVG 主导）。
2. `<paper>_components.py`：Python 生成所有数值/几何子图的脚本。
3. `comp_*.svg`：Python 子图源文件（便于回头修改）。
4. 可选独立 `method_architecture.svg`。
5. 简短说明：主流程、辅助分支、Python 子图清单、引用的源文件。
6. 仍有歧义时**明确指出未定模块**，不自行猜测。
