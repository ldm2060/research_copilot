# arXiv Search MCP Server

Provides tools for searching academic papers on arXiv and obtaining PDF download URLs.

## Tools

### `search_arxiv`
Search arXiv for papers by keywords, author, abstract text, category, or arXiv ID.

**Parameters:**
- `query` (string, required) — Search query. Supports arXiv syntax:
  - `ti:"keywords"` — title search
  - `au:"author name"` — author search
  - `abs:"text"` — abstract search
  - `cat:cs.CV` — category filter
  - Plain text searches all fields
  - Pass an arXiv ID like `1706.03762` for exact lookup
- `max_results` (integer, default 5, max 20) — Maximum papers to return
- `sort_by` (enum: `relevance`, `lastUpdatedDate`, `submittedDate`) — Sort criterion
- `sort_order` (enum: `ascending`, `descending`) — Sort direction
- `start` (integer, default 0) — Pagination offset

**Returns:** Paper title, authors, abstract, arXiv ID, published date, categories, DOI, PDF URL, and abstract page URL.

### `get_arxiv_pdf_url`
Get the direct PDF download URL and abstract page URL for a given arXiv ID.

**Parameters:**
- `arxiv_id` (string, required) — arXiv paper identifier (e.g. `1706.03762`, `2301.01234v2`, or full arxiv.org URL)

## Usage

This server uses the public arXiv API — no API key required. Rate limit: ~1 request per 3 seconds.
