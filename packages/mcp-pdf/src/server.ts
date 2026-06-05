// MCP stdio server exposing two PDF tools (per spec §7):
//   - pdf_extract_text     { path } -> extracted text + page count
//   - pdf_extract_metadata { path } -> page count + info dictionary
//
// Both tools read a LOCAL file path from disk and delegate to the pure
// extraction functions in ./extract.ts. See extract.ts for the v1 coarse-text
// reading-order limitation (numbers are advisory downstream).

import { readFileSync } from "node:fs";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { extractText, extractMetadata } from "./extract.js";

function readPdf(path: string): Uint8Array {
  // readFileSync returns a Buffer; wrap a copy as a plain Uint8Array so pdfjs
  // sees a standalone ArrayBuffer it can transfer without touching Node's
  // shared pool buffer.
  const buf = readFileSync(path);
  return new Uint8Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
}

export function createServer(): McpServer {
  const server = new McpServer({
    name: "mcp-pdf",
    version: "0.0.0",
  });

  server.registerTool(
    "pdf_extract_text",
    {
      title: "Extract PDF text",
      description:
        "Extract the text of a local PDF file. Coarse extraction (content-stream order); " +
        "two-column layouts may interleave. Extracted numbers are advisory.",
      inputSchema: { path: z.string().describe("Absolute or relative path to a local PDF file") },
    },
    async ({ path }) => {
      try {
        const data = readPdf(path);
        const { text, totalPages } = await extractText(data);
        return {
          content: [{ type: "text", text }],
          structuredContent: { text, totalPages },
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return {
          isError: true,
          content: [{ type: "text", text: `pdf_extract_text failed for "${path}": ${message}` }],
        };
      }
    },
  );

  server.registerTool(
    "pdf_extract_metadata",
    {
      title: "Extract PDF metadata",
      description:
        "Extract metadata (page count and the PDF info dictionary) from a local PDF file.",
      inputSchema: { path: z.string().describe("Absolute or relative path to a local PDF file") },
    },
    async ({ path }) => {
      try {
        const data = readPdf(path);
        const { totalPages, info } = await extractMetadata(data);
        return {
          content: [{ type: "text", text: JSON.stringify({ totalPages, info }, null, 2) }],
          structuredContent: { totalPages, info },
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return {
          isError: true,
          content: [
            { type: "text", text: `pdf_extract_metadata failed for "${path}": ${message}` },
          ],
        };
      }
    },
  );

  return server;
}
