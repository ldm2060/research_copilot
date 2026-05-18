---
name: arxivsub-skill
description: "Use whenever the user wants to search for academic papers, find recent research, look up conference publications, or explore literature on any AI / ML / CV topic. Routes through the `arxivsub-search` MCP server (arXiv + CVPR / ICCV / ICLR / ICML / NeurIPS / AAAI / MICCAI). Triggers on: \"find papers on X\", \"what are the latest papers about Y\", \"search arXiv for Z\", \"any recent work on W\", '论文检索', '最新研究'."
version: 0.2.0
---

# arxivsub-skill

Search academic papers via the arXIVSub API through MCP.

## Language Rule

**Always respond in the same language the user is using.**

## Step 0: Authentication

The `arxivsub-search` MCP server reads the API key automatically from the environment or a `.env` file at the workspace root. Never ask the user for it unless the MCP call fails with a missing-key or auth error, and never pass it as a chat parameter.

If the MCP tool reports `missing_api_key` or an auth failure involving `ARXIVSUB_SKILL_KEY`, tell the user (in their language) to set it up via **one** of:

1. Export as a shell environment variable (add to `~/.zshrc` or `~/.bashrc` for persistence):
   ```
   export ARXIVSUB_SKILL_KEY=your_key_here
   ```
2. Add to a `.env` file in the working directory:
   ```
   ARXIVSUB_SKILL_KEY=your_key_here
   ```

The user's API key is found on the Skills page of the arXivSub website.

## Step 1: Show search parameters and execute

Before calling the API, briefly show the interpreted parameters in one line (in the user's language), then proceed without waiting:

> Searching: query=`"..."`, locations=`[...]`, time=`...`, limit=`...`

Pause only if the search intent is genuinely ambiguous (e.g. a term that could mean multiple very different topics).

## Step 2: Call MCP search

Call `arxivsub-search.search_papers` with the interpreted parameters. Omit `arxiv_days` / `conference_years` if not applicable.

Expected MCP arguments:

```json
{
  "query": "<search terms>",
  "locations": ["arxiv", "CVPR", "NeurIPS"],
  "limit": 10,
  "arxiv_days": 7,
  "conference_years": [2024, 2025],
  "language": "en"
}
```

The MCP tool returns full paper details and `quota_remaining` in structured content. Do not create temp JSON files.

## Step 3: Filter and rank

From the returned list, select the **top 5–10** using:
1. **Relevance first** — how directly the paper addresses the query
2. **Recency as tiebreaker** — among equally relevant papers, prefer the most recent

## Step 4: Fetch full details and respond

Compose the response from the returned details. **Never mention files, scripts, temp files, or internal mechanics.**

### Output structure (translate headers to the user's language)

**[Research Findings]** — Synthesize insights. Answer the user's question directly.

**[Recommended Papers]** — For each paper, write a substantive description (not just `what_about`). Cover: what problem it solves, the key method or contribution, and notable results or significance. Typically 3–5 sentences.

```
**[Title]**
📍 [conference / arXiv] · [year if available]
👥 [first_author] ([first_aff]) · [last_author] ([last_aff])
📄 [synthesized description based on full paper details]
🔗 [pdf_url]
```

At the bottom, show quota in the user's language as a footnote:
English: `Daily quota remaining: N searches` / Chinese: `当日剩余搜索额度：N 次`

## Key rules

- `locations` is **case-sensitive**: `arxiv`, `CVPR`, `ICCV`, `ICLR`, `ICML`, `NeurIPS`, `AAAI`, `MICCAI`
- Show parameters as a one-liner before calling the MCP; only ask for confirmation if intent is ambiguous
- If the MCP returns an error, classify and handle:
  - **Retryable** (network timeout, transient server error): inform the user; offer to retry
  - **Needs user intervention**:
    - Quota exhausted → tell the user the daily quota is used up; do not retry
    - Auth failure / missing key → go to Step 0
    - Empty results → suggest broadening the query (fewer locations, wider date range, looser terms)
    - JSON parse failure / malformed response → report as an unexpected error; ask the user to try again later
- NEVER output raw JSON or expose internal mechanics
- NEVER call local skill scripts; all network access MUST go through MCP
