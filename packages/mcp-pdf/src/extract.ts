// PDF text/metadata extraction backed by `unpdf` (pdfjs under the hood).
//
// READING-ORDER LIMITATION (v1, per spec §15.6):
// This module performs COARSE text extraction. `unpdf`/pdfjs merges page text in
// content-stream order — i.e. the order glyphs were drawn into the PDF, NOT visual
// reading order. For single-column documents this is usually correct. For
// MULTI-COLUMN papers (e.g. two-column conference PDFs), columns may INTERLEAVE,
// producing text that mixes the left and right columns line-by-line.
//
// Consequence: numbers/strings extracted here are ADVISORY. Downstream rc-verify
// treats extracted numbers as advisory hints, not ground truth.
//
// A layout-aware path (TS x/y coordinate clustering, or a Python sidecar using a
// layout-aware parser) is a documented future option, not implemented in v1.

import { extractText as unpdfExtractText, getDocumentProxy, getMeta } from "unpdf";

/**
 * Extract text from a PDF.
 *
 * @param data  Raw PDF bytes.
 * @param opts.mergePages  When true (default) the returned `text` is a single
 *   string with all pages concatenated. Reserved for callers that may later want
 *   per-page text; v1 always returns merged text.
 */
export async function extractText(
  data: Uint8Array,
  opts?: { mergePages?: boolean },
): Promise<{ text: string; totalPages: number }> {
  const mergePages = opts?.mergePages ?? true;
  // pdfjs may transfer/detach the input ArrayBuffer; copy so callers can reuse
  // the same bytes across multiple extract calls.
  const bytes = data.slice();
  if (mergePages) {
    const { text, totalPages } = await unpdfExtractText(bytes, { mergePages: true });
    return { text, totalPages };
  }
  const { text, totalPages } = await unpdfExtractText(bytes, { mergePages: false });
  return { text: text.join("\n\n"), totalPages };
}

/**
 * Extract metadata (page count + document info dictionary) from a PDF.
 *
 * `info` is pdfjs's info dictionary (Title, Author, Producer, CreationDate, ...).
 * Keys present depend on the producing tool; callers must treat it as best-effort.
 */
export async function extractMetadata(
  data: Uint8Array,
): Promise<{ totalPages: number; info: Record<string, unknown> }> {
  // pdfjs transfers/consumes the underlying ArrayBuffer per call, and passing a
  // PDFDocumentProxy into getMeta() fails to round-trip across the worker
  // loopback port in some Node environments ("Unable to deserialize cloned
  // data"). So give each unpdf call its own fresh copy of the raw bytes.
  const pdf = await getDocumentProxy(data.slice());
  const totalPages = pdf.numPages;
  const { info } = await getMeta(data.slice());
  return { totalPages, info: (info ?? {}) as Record<string, unknown> };
}
