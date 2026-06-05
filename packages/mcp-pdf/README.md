# @research-copilot/mcp-pdf

MCP server for PDF text and metadata extraction using [unpdf](https://github.com/unjs/unpdf).

## Installation

```bash
npx @research-copilot/mcp-pdf
```

Or via MCP configuration:

```json
{
  "mcpServers": {
    "research-pdf": {
      "command": "npx",
      "args": ["-y", "@research-copilot/mcp-pdf"]
    }
  }
}
```

## Tools

### `pdf_extract_text`

Extract text content from a PDF file.

**Inputs:**
- `path` (string, required) - Absolute path to PDF file
- `mergePages` (boolean, optional) - Merge all pages into single text block (default: true)

**Returns:**
- `text` (string) - Extracted text content
- `totalPages` (number) - Total page count

**Note:** unpdf extracts text in content-stream order. For two-column academic papers, text from both columns may be interleaved. Page numbers are advisory.

### `pdf_extract_metadata`

Extract PDF metadata (page count, document info).

**Inputs:**
- `path` (string, required) - Absolute path to PDF file

**Returns:**
- `totalPages` (number) - Total page count
- `info` (object) - Document metadata (title, author, creation date, etc.)

## Implementation

- Built with [unpdf](https://github.com/unjs/unpdf) for PDF parsing
- Uses Mozilla PDF.js under the hood
- Text extraction is coarse (content-stream order, not reading order)
- Suitable for simple text extraction; complex layouts may need specialized tools

## License

MIT
