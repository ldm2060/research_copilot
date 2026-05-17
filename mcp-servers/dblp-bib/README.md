# DBLP BibTeX MCP

This local MCP server exposes DBLP-backed tools for searching publications and returning BibTeX entries that can be inserted into references.bib.

Bundled tools:

- search_dblp_bibtex: search DBLP publications and return BibTeX for the top matches.
- get_dblp_bibtex: fetch BibTeX directly from a DBLP record key or DBLP record URL.

Runtime notes:

- Requires Python 3 on the machine that opens the workspace.
- Workspace configuration is written to .vscode/mcp.json by the bundle packager.
- Agent policy in this workspace requires BibTeX edits to use this MCP only.

## Rate Limiting & Retry

- **Minimum interval**: 1.5 seconds between consecutive requests (DBLP guideline)
- **Max retries**: 3 attempts on HTTP 429 (Too Many Requests) or 5xx errors
- **Backoff**: exponential, starting at 5s (5s → 10s → 20s)
- **Network errors**: also retried with the same backoff strategy