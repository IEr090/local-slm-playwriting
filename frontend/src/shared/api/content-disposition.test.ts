import { describe, expect, it } from "vitest";
import { fileNameFromDisposition } from "./content-disposition";

describe("fileNameFromDisposition", () => {
  it("reads a quoted filename", () => {
    expect(fileNameFromDisposition('attachment; filename="The Salt House.pdf"')).toBe("The Salt House.pdf");
  });

  it("reads an unquoted filename", () => {
    expect(fileNameFromDisposition("attachment; filename=play.pdf")).toBe("play.pdf");
  });

  it("prefers filename* and decodes it", () => {
    const header = "attachment; filename=\"play.pdf\"; filename*=UTF-8''%D0%A1%D0%BE%D0%BB%D1%8F%D0%BD%D0%BE%D0%B9%20%D0%B4%D0%BE%D0%BC.pdf";
    expect(fileNameFromDisposition(header)).toBe("Соляной дом.pdf");
  });

  it("falls back to the plain name when filename* is broken", () => {
    expect(fileNameFromDisposition("attachment; filename=\"a.pdf\"; filename*=UTF-8''%E0%A4%A")).toBe("a.pdf");
  });

  it("returns null without a header or a name", () => {
    expect(fileNameFromDisposition(null)).toBeNull();
    expect(fileNameFromDisposition("attachment")).toBeNull();
  });
});
