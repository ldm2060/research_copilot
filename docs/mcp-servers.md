# MCP Servers

Research Copilot provides 6 Model Context Protocol (MCP) servers for academic research workflows. These servers expose specialized tools for paper search, bibliography management, experiment tracking, and publication workflows.

## Overview

| Server | Tools | Purpose | Status |
|---|---|---|---|
| `scholar` | 3 | Paper search (arXiv, Semantic Scholar) | ✅ Shipped |
| `bibtex` | 4 | Bibliography management | ✅ Shipped |
| `latex` | 5 | LaTeX compilation and formatting | ✅ Shipped |
| `experiment` | 6 | Experiment tracking (W&B, TensorBoard) | ✅ Shipped |
| `venue` | 3 | Conference/journal metadata | ✅ Shipped |
| `ethics` | 2 | Ethics checklist validation | ✅ Shipped |

## Installation

MCP servers are bundled with the CLI. No separate installation required.

### Claude Code Configuration

MCP servers are auto-configured during `rc init --claude`:

```bash
rc init --user your-name --claude
```

This writes to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "research-copilot-scholar": {
      "command": "node",
      "args": ["<project>/node_modules/@research-copilot/mcp-scholar/dist/index.js"]
    },
    "research-copilot-bibtex": {
      "command": "node",
      "args": ["<project>/node_modules/@research-copilot/mcp-bibtex/dist/index.js"]
    }
  }
}
```

### Manual Configuration (Other Platforms)

For platforms without auto-config (Cursor, Windsurf), add manually:

```json
{
  "mcpServers": {
    "scholar": {
      "command": "node",
      "args": ["/path/to/research_copilot/packages/mcp-servers/scholar/dist/index.js"]
    }
  }
}
```

---

## Server Details

### 1. Scholar Server

**Purpose**: Search and retrieve academic papers from arXiv and Semantic Scholar.

**Tools**:

#### `search`
Search papers by query.

**Parameters**:
- `query` (string, required): Search query
- `source` (enum, optional): `arxiv` | `semantic_scholar` | `google_scholar` (default: all)
- `limit` (number, optional): Max results (default: 10, max: 50)

**Example**:
```typescript
{
  "name": "search",
  "arguments": {
    "query": "transformer attention mechanism",
    "source": "arxiv",
    "limit": 5
  }
}
```

**Returns**:
```json
{
  "papers": [
    {
      "id": "arxiv:1706.03762",
      "title": "Attention is All You Need",
      "authors": ["Vaswani et al."],
      "year": 2017,
      "venue": "NeurIPS",
      "citations": 95000,
      "abstract": "..."
    }
  ]
}
```

#### `metadata`
Get detailed metadata for a paper by ID.

**Parameters**:
- `paper_id` (string, required): Paper ID (e.g., `arxiv:1706.03762`, `doi:10.1145/...`)

**Returns**: Full paper metadata with abstract, authors, citations, PDF link.

#### `bibtex`
Generate BibTeX entry for a paper.

**Parameters**:
- `paper_id` (string, required): Paper ID

**Returns**:
```bibtex
@article{vaswani2017attention,
  title={Attention is All You Need},
  author={Vaswani, Ashish and ...},
  journal={NeurIPS},
  year={2017}
}
```

---

### 2. BibTeX Server

**Purpose**: Manage bibliography files, validate entries, and resolve citations.

**Tools**:

#### `parse`
Parse a `.bib` file and return structured entries.

**Parameters**:
- `file_path` (string, required): Path to `.bib` file

**Returns**: Array of parsed BibTeX entries.

#### `validate`
Validate BibTeX file for errors (missing fields, duplicate keys, etc.).

**Parameters**:
- `file_path` (string, required): Path to `.bib` file

**Returns**: Validation errors or `{ valid: true }`.

#### `merge`
Merge two BibTeX files, resolving duplicates.

**Parameters**:
- `source_path` (string, required): Source `.bib` file
- `target_path` (string, required): Target `.bib` file
- `strategy` (enum, optional): `keep_source` | `keep_target` | `merge_fields` (default: `merge_fields`)

**Returns**: Merged BibTeX string.

#### `format`
Reformat BibTeX entries (sort, fix indentation, etc.).

**Parameters**:
- `file_path` (string, required): Path to `.bib` file
- `style` (enum, optional): `ieee` | `acm` | `apa` | `chicago` (default: `ieee`)

**Returns**: Formatted BibTeX string.

---

### 3. LaTeX Server

**Purpose**: Compile LaTeX documents, check formatting, and generate PDFs.

**Tools**:

#### `compile`
Compile LaTeX document to PDF.

**Parameters**:
- `file_path` (string, required): Path to `.tex` file
- `engine` (enum, optional): `pdflatex` | `xelatex` | `lualatex` (default: `pdflatex`)
- `output_dir` (string, optional): Output directory (default: same as `.tex` file)

**Returns**: PDF path or compilation errors.

#### `check_format`
Check formatting compliance (margins, fonts, page limit).

**Parameters**:
- `file_path` (string, required): Path to `.tex` file
- `venue` (string, required): Venue ID (e.g., `neurips`, `icml`, `cvpr`)

**Returns**: Formatting violations or `{ compliant: true }`.

#### `count_pages`
Count pages in compiled PDF.

**Parameters**:
- `file_path` (string, required): Path to `.tex` or `.pdf` file

**Returns**: `{ pages: 10, limit: 9, over: true }` or `{ pages: 8, limit: 9, over: false }`.

#### `extract_citations`
Extract all citations from LaTeX source.

**Parameters**:
- `file_path` (string, required): Path to `.tex` file

**Returns**: Array of citation keys (e.g., `["vaswani2017attention", "devlin2018bert"]`).

#### `fix_citations`
Fix broken citations (missing BibTeX entries).

**Parameters**:
- `tex_path` (string, required): Path to `.tex` file
- `bib_path` (string, required): Path to `.bib` file

**Returns**: List of fixed citations or unfixable issues.

---

### 4. Experiment Server

**Purpose**: Track experiments, log metrics, and query results.

**Tools**:

#### `create_run`
Create a new experiment run.

**Parameters**:
- `name` (string, required): Run name
- `config` (object, required): Hyperparameters and config
- `backend` (enum, optional): `wandb` | `tensorboard` | `mlflow` (default: `wandb`)

**Returns**: Run ID.

#### `log_metrics`
Log metrics to a run.

**Parameters**:
- `run_id` (string, required): Run ID
- `metrics` (object, required): Key-value metrics (e.g., `{ loss: 0.5, acc: 0.92 }`)
- `step` (number, optional): Training step

**Returns**: Success confirmation.

#### `query_runs`
Query experiment runs by filters.

**Parameters**:
- `filters` (object, optional): Filters (e.g., `{ status: "completed", metric: "acc > 0.9" }`)
- `limit` (number, optional): Max results (default: 10)

**Returns**: Array of matching runs.

#### `compare_runs`
Compare metrics across runs.

**Parameters**:
- `run_ids` (array, required): Array of run IDs to compare

**Returns**: Comparison table with metrics.

#### `get_artifacts`
Download artifacts from a run.

**Parameters**:
- `run_id` (string, required): Run ID
- `artifact_name` (string, required): Artifact name (e.g., `model.pth`)

**Returns**: Artifact path or download URL.

#### `stop_run`
Stop a running experiment.

**Parameters**:
- `run_id` (string, required): Run ID

**Returns**: Success confirmation.

---

### 5. Venue Server

**Purpose**: Get conference/journal metadata (deadlines, formatting, etc.).

**Tools**:

#### `search_venues`
Search conferences and journals by name or topic.

**Parameters**:
- `query` (string, required): Venue name or topic (e.g., `"neural networks"`, `"ICML"`)
- `type` (enum, optional): `conference` | `journal` (default: both)

**Returns**: Array of matching venues.

#### `get_venue_info`
Get detailed venue information.

**Parameters**:
- `venue_id` (string, required): Venue ID (e.g., `neurips`, `icml`, `cvpr`)

**Returns**:
```json
{
  "name": "NeurIPS",
  "full_name": "Conference on Neural Information Processing Systems",
  "type": "conference",
  "deadline": "2026-06-15T23:59:00Z",
  "notification": "2026-09-10",
  "camera_ready": "2026-10-15",
  "page_limit": 9,
  "template_url": "https://neurips.cc/Conferences/2026/PaperInformation/StyleFiles",
  "ethics_required": true
}
```

#### `get_template`
Download venue LaTeX template.

**Parameters**:
- `venue_id` (string, required): Venue ID
- `output_dir` (string, optional): Output directory (default: current directory)

**Returns**: Template path.

---

### 6. Ethics Server

**Purpose**: Validate ethics checklists for publication.

**Tools**:

#### `validate_checklist`
Validate ethics checklist compliance.

**Parameters**:
- `venue_id` (string, required): Venue ID
- `checklist_path` (string, optional): Path to checklist file (if not provided, checks for standard location)

**Returns**: Validation errors or `{ compliant: true }`.

#### `generate_checklist`
Generate ethics checklist template for venue.

**Parameters**:
- `venue_id` (string, required): Venue ID
- `output_path` (string, optional): Output path (default: `.research/ethics-checklist.md`)

**Returns**: Checklist path.

---

## Usage Examples

### Example 1: Literature Search Workflow

```typescript
// Search papers
await callTool('scholar', 'search', {
  query: 'efficient transformers',
  source: 'arxiv',
  limit: 10
});

// Get metadata for top paper
await callTool('scholar', 'metadata', {
  paper_id: 'arxiv:1706.03762'
});

// Generate BibTeX
await callTool('scholar', 'bibtex', {
  paper_id: 'arxiv:1706.03762'
});

// Add to bibliography
await callTool('bibtex', 'merge', {
  source_path: 'new-papers.bib',
  target_path: 'references.bib'
});
```

### Example 2: Pre-Submission Checks

```typescript
// Check formatting
await callTool('latex', 'check_format', {
  file_path: 'paper.tex',
  venue: 'neurips'
});

// Count pages
await callTool('latex', 'count_pages', {
  file_path: 'paper.pdf'
});

// Fix broken citations
await callTool('latex', 'fix_citations', {
  tex_path: 'paper.tex',
  bib_path: 'references.bib'
});

// Validate ethics checklist
await callTool('ethics', 'validate_checklist', {
  venue_id: 'neurips'
});
```

### Example 3: Experiment Tracking

```typescript
// Create run
const runId = await callTool('experiment', 'create_run', {
  name: 'sparse-attention-v1',
  config: { lr: 1e-4, batch_size: 32 },
  backend: 'wandb'
});

// Log metrics
await callTool('experiment', 'log_metrics', {
  run_id: runId,
  metrics: { loss: 0.5, acc: 0.92 },
  step: 1000
});

// Query completed runs
await callTool('experiment', 'query_runs', {
  filters: { status: 'completed', metric: 'acc > 0.9' }
});
```

---

## Development

### Adding New Tools

To add a new tool to an existing server:

1. Define tool schema in `packages/mcp-servers/<server>/src/tools.ts`
2. Implement handler in `packages/mcp-servers/<server>/src/handlers/<tool>.ts`
3. Register in `packages/mcp-servers/<server>/src/index.ts`
4. Add tests in `packages/mcp-servers/<server>/tests/<tool>.test.ts`
5. Update this documentation

### Creating New Servers

See [docs/dev/mcp-development.md](dev/mcp-development.md) for guide.

---

## Related Documentation

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Command Reference](usage/commands.md)
- [Skills Documentation](skills.md)
- [Development Guide](dev/mcp-development.md)
