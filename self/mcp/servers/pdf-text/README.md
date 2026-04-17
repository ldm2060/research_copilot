# PDF Text Extraction MCP

Extracts text content from local PDF files, returning structured per-page text suitable for academic paper reading and analysis.

## Tools

### `extract_pdf_text`
Extract text from a local PDF file. Returns per-page text with page boundaries marked.

**Parameters:**
- `pdf_path` (string, required) — Absolute or workspace-relative path to the PDF file
- `max_pages` (integer, default 0, max 200) — Maximum pages to extract. 0 = all pages.
- `start_page` (integer, default 1) — First page to extract (1-based)

**Returns:** Full extracted text with page separators, plus structured per-page content.

## Dependencies

- **pdfplumber** (primary, recommended) — best text extraction quality
- **PyPDF2** (fallback) — used if pdfplumber is not installed

Install: `pip install pdfplumber`

## Rate Limiting & Retry

This server works entirely locally — no network requests, no rate limiting needed.
