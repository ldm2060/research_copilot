# @research-copilot/mcp-scholar

MCP server for scholarly paper search, aggregating results from multiple academic search backends.

## Installation

```bash
npx @research-copilot/mcp-scholar
```

Or via MCP configuration:

```json
{
  "mcpServers": {
    "research-scholar": {
      "command": "npx",
      "args": ["-y", "@research-copilot/mcp-scholar"]
    }
  }
}
```

## Tools

### `scholar_search`

Search for academic papers across multiple backends.

**Inputs:**
- `query` (string, required) - Search query
- `limit` (number, optional) - Max results per backend (default: 10)
- `backends` (string[], optional) - Backends to query (default: ["arxiv", "dblp"])

**Backends:**
- `arxiv` - arXiv.org (full backend, reliable)
- `dblp` - DBLP Computer Science Bibliography (full backend, reliable)
- `scholar` - Google Scholar via SerpAPI (best-effort, requires API key)
- `arxivsub` - arXiv submission tracker (best-effort)

**Returns:** Array of paper objects with fields:
- `title` (string)
- `authors` (string[])
- `year` (number)
- `venue` (string)
- `url` (string)
- `abstract` (string, if available)
- `citations` (number, if available)
- `source` (string) - Backend that provided this result

### `scholar_metadata`

Get detailed metadata for a specific arXiv paper.

**Inputs:**
- `arxiv_id` (string, required) - arXiv ID (e.g., "2401.12345")

**Returns:** Paper metadata with full details from arXiv API.

### `scholar_bibtex`

Get BibTeX citation for a paper from DBLP.

**Inputs:**
- `dblp_key` (string, required) - DBLP key (e.g., "conf/icml/SmithJ23")

**Returns:**
- `bibtex` (string) - BibTeX entry, or empty string if not found

## Backend Details

**arXiv** (full backend):
- Atom XML API
- Reliable, no rate limits for reasonable use
- Returns: title, authors, year, abstract, arXiv URL

**DBLP** (full backend):
- JSON API + BibTeX fetching
- Reliable, no API key required
- Returns: title, authors, year, venue, DBLP URL, BibTeX

**Google Scholar** (best-effort):
- Via SerpAPI (requires `SERP_API_KEY` environment variable)
- Rate-limited by SerpAPI plan
- Returns: title, authors, year, citations, URL
- Errors are logged but don't fail the overall search

**arXiv Submission** (best-effort):
- Tracks recent arXiv submissions
- May be unstable
- Errors are logged but don't fail the overall search

## Multi-Backend Aggregation

The `scholar_search` tool runs queries against all enabled backends in parallel and aggregates results. Per-backend failures are isolated (one backend error doesn't fail the entire search). Each result is tagged with its `source` backend.

**Default backends:** `["arxiv", "dblp"]` (reliable, no API keys required)

**To use Google Scholar:** Set `SERP_API_KEY` environment variable and include `"scholar"` in backends array.

## Architecture

- `src/facade.ts` - Multi-backend orchestration with failure isolation
- `src/backends/arxiv.ts` - arXiv API client (Atom XML)
- `src/backends/dblp.ts` - DBLP API client (JSON + BibTeX)
- `src/backends/scholar.ts` - Google Scholar via SerpAPI
- `src/backends/arxivsub.ts` - arXiv submission tracker
- `src/server.ts` - MCP server implementation

## License

MIT
