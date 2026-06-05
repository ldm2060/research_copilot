import { describe, it, expect, beforeAll } from "vitest";
import { PDFDocument, StandardFonts } from "pdf-lib";
import { extractText, extractMetadata } from "../src/extract.js";

// Fixture: a single-page PDF containing a sentence with a numeric result.
let fixture: Uint8Array;

beforeAll(async () => {
  const doc = await PDFDocument.create();
  doc.setTitle("rc-fixture");
  const page = doc.addPage([612, 792]);
  const font = await doc.embedFont(StandardFonts.Helvetica);
  page.drawText("Result: 92.5 accuracy on 3 seeds.", {
    x: 50,
    y: 700,
    size: 18,
    font,
  });
  // pdf-lib returns a Uint8Array of the serialized PDF.
  fixture = await doc.save();
});

describe("extractText", () => {
  it("extracts the fixture text and reports one page", async () => {
    const { text, totalPages } = await extractText(fixture);
    expect(totalPages).toBe(1);
    expect(text).toContain("92.5");
    expect(text).toContain("accuracy");
  });
});

describe("extractMetadata", () => {
  it("reports one page and returns an info object", async () => {
    const { totalPages, info } = await extractMetadata(fixture);
    expect(totalPages).toBe(1);
    expect(info).toBeTypeOf("object");
  });
});
