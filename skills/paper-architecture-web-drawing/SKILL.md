---
name: paper-architecture-web-drawing
description: "Use when the user wants a paper's abstract + method turned into a publication-ready architecture diagram, rendered as a single HTML file with inline SVG (and Python-generated SVG sub-figures for heatmaps / distributions / scatter / matrices). Triggers on: \"架构图\", \"结构图\", \"method figure\", \"overview figure\", \"pipeline diagram\", \"draw methodology\", \"网页绘图\". Enforces compactness numerics and a mandatory 10-round self-check loop. Do NOT use for line / bar / scatter data plots, posters, art, pure Mermaid sketches, or before the method is settled."
version: 0.5.1
---

# Paper Architecture Web Drawing

Input: the paper's Abstract + Method (or a `.tex` / `.md` / `.txt` paper file in the workspace).
Output: a single HTML file with inline SVG rendering a top-conference-grade method figure; optionally an independent companion `.svg` of the same content.
Not for: line / bar / scatter data plots, posters, illustrations, pure Mermaid sketches, or pre-method-settled drafts.

## 0. Seven non-negotiable rules

1. **White background + vector-first**: pure white background, inline SVG as the dominant medium. **Banned: gradients, shadows, glassmorphism, glow, decorative backgrounds.** Only MathJax / KaTeX may go online.
2. **At least 3 real glyphs**: weights / distribution / tokens / cache / codebook / attention / scatter etc. must be drawn as matrix grids, heatmaps, histograms, boxplots, or scatter. **Text boxes only = fail.** Glyphs expressible in Python (see §2.7) **prefer Python**; do not hand-write complex heatmaps or curves.
3. **Equations near their module**: LaTeX equations anchor as local labels on their corresponding module. **Do not pile them in a bottom strip.** Render via MathJax / KaTeX in HTML; never write ASCII pseudo-equations (`sum(...)/sum(...)`).
4. **Font-size floor (top-conference density)**: main title ≥ 26 px, section title ≥ 22 px, module label ≥ 18 px, equation label ≥ 16 px, auxiliary ≥ 14 px. **When tight, delete words before shrinking type.** viewBox must give enough room — no 1060×330 strip that crushes the type.
5. **English labels only**: no Chinese labels; no single-component description longer than 10 words.
6. **Browser verification**: after writing the HTML, open it in a browser and take a screenshot. On Windows: `start "" "$(pwd -W)/path.html"` or `python -m http.server`.
7. **Every arrow has paper grounding**: NEVER invent modules, losses, or feedback loops.

## 1. Banned visual modes

- **SmartArt / PowerPoint flowcharts**: equal-width rounded cards chained linearly, all nodes with the same corner radius and border.
- **Dashboard / poster style**: right-side KPI column, result-card stack, marketing badges, statistic stickers, glow emphasis.
- **Web-UI collage**: title bar + subtitle bar + content card patterns; pill-badge arrays.
- **Big box + arrow + bottom legend** as the dominant frame.
- **Top stage-label + bottom caption / problem statement / method summary**. The figure should be self-explanatory.
- **bypass / feedback / dashed line crossing** through module titles, equations, badges, or result numbers.
- **Small font + large whitespace** in exchange for content capacity.
- High-saturation red / green / purple, or five or more salient light-color blocks at once.

## 2. Workflow

### 2.1 Read the paper

- Look for `.tex` / `.md` / `.txt` in the workspace; read Abstract / Method / Approach / Overview / Framework.
- If multiple candidate files exist, **confirm with the user first** — do not guess.
- Only read context needed to reconstruct the main pipeline.

### 2.2 Structure extraction (mandatory before drawing)

For every key module fill out these 5 fields. If you cannot articulate one, **do not draw the module**:

| Field | Content |
|---|---|
| `Name` | Short stable English module name, no slogans |
| `Type` | input / encoder / alignment / retrieval / fusion / optimization / loss / output |
| `Is novel?` | Is this a contribution that needs visual highlight? |
| `Internal elements` | The objects / operations worth visualizing inside it (attention, MLP, codebook, feature map, cache update) |
| `Topology role` | main-chain node / parallel branch / merge point / feedback point / training-only branch |

### 2.3 Pick a layout family (in order of priority)

1. Explicit feedback / iteration / alternating optimization / until convergence → **Loop / U-shape**
2. train/infer or stage1/stage2 or coarse/fine or retrieve/generate → **Two-stage**
3. ≥2 semantically independent branches merging into a shared main module → **Multi-branch with merge**
4. Narrow column / single-column vertical reading → **Linear vertical**
5. 3-6 serial stages, no strong feedback → **Linear horizontal** (default)
6. Local complex substructure embedded in the main chain → **Hybrid composition**

**Tie-breakers**: prefer the layout that preserves a strong visual center, gives the key mechanism panel enough area, minimizes arrow crossings and diagonal text overlaps, and forms a natural input-vs-output contrast.

**Veto conditions** (any of these → switch layout):
- No room for a main illustration; all modules forced into equal-weight small boxes.
- Need >2 long cross-region connectors to convey the main flow.
- Key equations forced into corners.
- Output region and auxiliary text fighting for space.
- Must shrink font or add whitespace to fit.

### 2.4 Default blueprint

**Input object → 2-3 mechanism panels → output object**

- **Left**: tensor / weights / KV cache / tokens / feature grid as a visualized input object (NOT a text box).
- **Middle**: each panel centers on a **main illustration**, not uniformly-sized small cards. Auxiliary objects (codebook / sensitivity map / objective / memory) anchor to their mechanism.
- **Right**: the transformed object of the same kind, preferring **structural change** over KPI summary.
- Input ↔ output **reuse the same graphic motif** to show state change (e.g. same-shape cache blocks before/after compression).
- Highlight only 1–2 core contribution modules: same-family slightly heavier border / slightly darker fill / local bracket / callout. **Never** via high saturation or large badges.

### 2.5 Palette (pick 1 of 5; one family across the whole figure)

| Family | Use |
|---|---|
| **Blue-Gray** | Generic pipeline / system figure (default) |
| **Warm Tones** | Moderate emphasis on novelty |
| **Green-Cyan** | Generative / biological / light themes |
| **Purple-Blue** | Theory / math-heavy |
| **Monochrome** | Minimalist / B&W-print-friendly |

**Color roles** (consistent across any chosen family): Primary background (normal modules), Secondary background (minor modules), Accent background (contribution modules), Input/Output background (lighter), Primary border, Accent border, **Arrow color: one dark color across the whole figure**, Main text, Secondary text. **Never mix families.**

### 2.6 Typography

- 2–3 stroke widths: main flow / secondary structure / coordinate auxiliaries.
- Small / medium corner radius; avoid web-card-style large rounding.
- **Sans for labels + serif for equations.**
- Short stable module titles, no slogans; subtitles default to omitted.
- Training-only branches: lighter fill + dashed arrows.
- Long paths (bypass, feedback, training-only branches) follow the outer edge of regions; do not cross dense text inside sub-panels.
- Compactness first: align, share edges, tighten via grouping. NEVER reduce font size to fit content.
- Asymmetric layouts allowed; area reflects importance; never chase column parity.

### 2.7 Abstract object → glyph (Python vs hand-written SVG)

| Paper object | Glyph | Recommended source |
|---|---|---|
| `weights` / `kernels` / `parameters` matrix | matrix grid + outlier column / point highlight | matplotlib `imshow` |
| `distribution` / `density` / histogram | histogram / KDE curve | matplotlib `hist` + `kdeplot` |
| `outliers` / `IQR` / `boxplot` | boxplot + Q1 / Q3 / whisker annotations | matplotlib `boxplot` |
| `scatter` / two-variable relation / error comparison | scatter + diagonal + highlight region | matplotlib `scatter` |
| `attention` / `similarity` / `heatmap` | 2D heatmap + colorbar | matplotlib `imshow` (cmap viridis / coolwarm) |
| `eigenvectors` / `subspace` / `basis` | disk + direction arrows / axes | matplotlib `quiver` or hand-SVG |
| `quantization` / `clustering` / `codebook` | bin partition lines / cluster centers / lookup blocks | matplotlib + `axvline` for centroids |
| `tokens` / `patches` / `cache blocks` | brick array + bit-width tag | hand-written SVG (structured) |
| `loss landscape` / 3D surface | contour / pcolormesh | matplotlib |
| `loss` / `objective` / `constraint` | short equation chip (attached to module) | hand-written SVG + MathJax |
| module boxes, arrows, formula chips, brackets | box / line / label | **hand-written SVG** (Python is not elegant here) |

**Rule**: if the glyph carries numerical / distribution / geometric content → Python-generated SVG. If the glyph is a structured layout (box, arrow, equation slot) → hand-written SVG.

### 2.7.1 Python-generated SVG sub-figures (matplotlib)

Place a `figures/<paper>_components.py` script; each subplot saves to a separate `.svg`; the main HTML embeds them inline or via `<img src=...svg>`. **Prefer inline** (single-file delivery, second-pass editable).

Minimum skeleton:

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
    "svg.fonttype": "none",   # keep text as <text>, do not outline
})

def save(fig, path):
    fig.savefig(path, format="svg", bbox_inches="tight",
                pad_inches=0.05, transparent=True)
    plt.close(fig)
```

**Hard rules**:

- `svg.fonttype="none"`: text stays as editable `<text>`, not paths.
- `transparent=True` + main HTML white background, avoiding double background layers.
- Per-subplot font size ≥ 12 (after embedding scale, still readable).
- Use only your palette family (see §2.5); never matplotlib's default `tab:blue`.
- One figure per function; never `plt.show()` in the script.

### 2.7.2 Inline embedding

After Python produces `comp_a.svg`, in the main HTML:

```html
<g transform="translate(120, 80)">
  <!-- inline-svg-include: comp_a.svg -->
</g>
```

Two delivery paths:

- **Copy inline**: paste `comp_a.svg`'s inner `<g>...</g>` into the main SVG at the corresponding spot; drop the outer `<svg>` header.
- **Object reference**: in main HTML, `<image href="comp_a.svg" x=.. y=.. width=..>` or `<foreignObject>`. **MUST** verify rendering in the browser before delivery.

After inline embedding, **manually adjust size / position**: matplotlib's default viewBox differs from the main figure's coordinate system; wrap in a `<g transform="translate(x,y) scale(s)">`.

### 2.8 Equation placement

- Every key equation has a dedicated slot (local white-background equation slot / module-internal equation strip / anchor aligned to glyph). **Never a floating web-sticker.**
- Long equations split into two short labels or shorter equivalent forms; never let a single long line crush a panel.
- objective / update / normalization / threshold equations live inside their module's slot, not piled in a unified bottom strip.
- The equation chip sits ≤ 15 px below its main illustration; no big air gap between them.

### 2.9 Compactness numerics (hard targets)

Most "doesn't look like a method figure" failures come from **loose layout**. Enforce these upper bounds:

| Metric | Upper bound | Meaning |
|---|---|---|
| Whitespace ratio inside a panel | ≤ 15% | Title + glyphs + equations + labels cover ≥ 85% of panel area |
| Main illustration's share of panel visible area | ≥ 65% | "The figure dominates; text is secondary" |
| Cross-panel horizontal gap | 20-40 px (viewBox units) | >40 = loose |
| Cross-panel vertical gap | 15-30 px | between adjacent rows |
| Title bottom edge → first panel | ≤ 30 px | No top-air |
| viewBox aspect ratio | 0.45 - 0.65 (single-row 4-panel) | Top-venue `figure*` ≈ 2:1 |
| Panel top padding (above title) | ≤ 16 px | Title touches edge |
| Panel bottom padding (below last element) | ≤ 16 px | No large dead space |
| Distance: glyph ↔ shape / label | ≤ 10 px | Tightly aligned, not floating |
| Nested `<rect>` levels in one panel | ≤ 2 | 3-level nesting = card bloat |

**Panel-equal-height trap**: 4 panels in one row need not be equal height. Input/Output typically 200–300 px shorter than mechanism panels. **Forcing equal height = manufacturing whitespace.**

**How to measure**: after rendering, use browser dev tools. Or temporarily draw `<rect>` boundary markers inside the SVG to eyeball dead-space ratios.

### 2.10 Mandatory ≥ 10-round self-check loop

After writing the HTML, **never deliver directly**. Run 10 iterations from the table below; each round:

1. Render PNG with `chrome --headless --screenshot`.
2. Open the PNG; write down "this round's focus dimension and 3 most non-compliant spots" (concrete only; "looks fine" is banned).
3. Fix HTML / Python / regenerate the sub-figure.
4. Re-render.

| Round | Focus | Must check |
|---|---|---|
| 1 | **Topology fidelity** | Aligned to paper's method? No missing / extra modules, arrows, losses, feedback? |
| 2 | **Compactness** | Measure each panel's whitespace; tighten one by one; trim viewBox |
| 3 | **Font sizes** | Spot-check every text against 26/22/18/16/14 floor; if below floor, delete words, do not shrink |
| 4 | **Color discipline** | Single palette family? No gradients / shadows / glass / glow / decorative backgrounds? |
| 5 | **Equation anchoring** | LaTeX truly rendered via MathJax? Chip glued to its module? |
| 6 | **Arrow routing** | Main flow / bypass / feedback do not cross text / equations / badges |
| 7 | **Python sub-figures** | `svg.fonttype="none"`, palette consistent with main, aspect matched to panel |
| 8 | **Visual hierarchy** | Main reading path obvious at first glance? 1–2 contribution panels highlighted? Non-contribution modules restrained? |
| 9 | **Anti-pattern scan** | Does it resemble SmartArt / PowerPoint / dashboard / web UI / poster? |
| 10 | **Paper context** | Drop into an ICML/CVPR two-column layout — does it feel native? Cover the title — does it still feel like this paper? |

**Never skip a round.** If a round finds nothing because earlier rounds already fixed it, explicitly record "this round 0 issues" — do not silently skip.

**Round 11+ optional**: only when a previous fix triggered a new violation (e.g. tightening clipped some text); add rounds until stable.

### 2.11 Quick-rollback conditions

During iteration, if **any** of the following holds, roll back to §2.4 default blueprint and redraw; do not keep tuning:

- 3 rounds of compactness work still cannot hit the §2.9 numbers.
- The main illustration is essentially stacked text, not graphics.
- viewBox shrinking always leaves large whitespace → usually caused by forced panel-equal-height (§2.9 trap).

## 3. File locations

- If the repo has `figures/` or `dist/figures/` → output there.
- Otherwise put the files next to the paper source.
- Default artifacts:
  - `method_architecture.html` (main figure, inline SVG)
  - `method_architecture.svg` (homologous standalone SVG, optional)
  - `<paper>_components.py` (script generating Python sub-figures)
  - `comp_*.svg` (Python sub-figure source files, for later editing)
- The main HTML does NOT go online (MathJax / KaTeX CDN is the only exception).

## 4. Completion checklist

Confirm every item. Any miss → continue iterating:

- [ ] Single HTML file opens directly; pure white background; inline SVG dominates
- [ ] ≥ 3 real glyphs (heatmap / histogram / boxplot / scatter / matrix), with **≥ 1 Python-generated** if numerical
- [ ] Each main mechanism panel has a main illustration, NOT just title + equation + cards
- [ ] Python sub-figures use `svg.fonttype="none"`; text is editable
- [ ] Python sub-figures use the same palette family as the main figure; no matplotlib defaults
- [ ] **Compactness (§2.9)**: panel whitespace ≤ 15%, main illustration ≥ 65% of panel, cross-panel gap 20–40 px
- [ ] **Panels NOT forced equal-height**: Input/Output 200–300 px shorter than mechanism panels
- [ ] **viewBox aspect ratio 0.45–0.65** (single-row 4-panel); top/bottom padding ≤ 30 px
- [ ] Equations sit in dedicated slots, aligned with their module; not floating; not crushed by codebook / arrow / badge
- [ ] LaTeX equations render correctly (MathJax / KaTeX); no ASCII pseudo-equations
- [ ] Font sizes meet the floor: 26 / 22 / 18 / 16 / 14
- [ ] All English labels; single-component description ≤ 10 words
- [ ] 1–2 core contribution modules highlighted (restrained: no high saturation, no big badges)
- [ ] Palette: single family, 3–5 shades; **no gradients / shadows / glow / glass**
- [ ] Main-flow arrows do not cross text / equations / badges; long paths follow outer edges
- [ ] Input ↔ Output reuse a graphic motif or form a sensible before/after contrast
- [ ] No top stage-label / phase-label; no bottom caption / problem statement / footer text
- [ ] No right-side KPI column / result-card stack / dashboard / poster summary strip
- [ ] Does not resemble SmartArt / PowerPoint / web component / product banner
- [ ] **≥ 10 rounds of self-check completed (§2.10)**, with a PNG screenshot and 3 spot notes per round
- [ ] Every arrow maps to a real data-flow / control-flow / supervision signal
- [ ] No invented modules / losses / feedback loops absent from the paper

## 5. Delivery contract

1. Single HTML file as the main figure (inline-SVG-dominant).
2. `<paper>_components.py`: script generating all Python numerical / geometric sub-figures.
3. `comp_*.svg`: Python sub-figure source files (so the user can edit later).
4. Optional: standalone `method_architecture.svg`.
5. Brief notes: main flow, auxiliary branches, Python sub-figure manifest, source files referenced.
6. When ambiguity remains, **explicitly flag the undefined modules**; do not invent.
