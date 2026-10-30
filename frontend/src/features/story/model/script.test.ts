import { describe, expect, it } from "vitest";
import { formatSceneText, insertBlock, parseBlock, parseSceneText, removeBlock, updateBlock } from "./script";

const TEXT = [
  "(Late afternoon. The shutters are barred.)",
  "AGNES: You came on the post boat.",
  "ELIAS (looking at the table): Three places.",
  "Later: the storm.",
].join("\n\n");

describe("scene text", () => {
  it("reads stage directions, speeches with notes and anything else", () => {
    expect(parseSceneText(TEXT)).toEqual([
      { kind: "direction", text: "Late afternoon. The shutters are barred." },
      { kind: "speech", who: "AGNES", paren: "", text: "You came on the post boat." },
      { kind: "speech", who: "ELIAS", paren: "looking at the table", text: "Three places." },
      { kind: "plain", text: "Later: the storm." },
    ]);
  });

  it("reads names with a surname and lines that contain colons", () => {
    expect(parseBlock("MARGIT HALE: Then: I have time.")).toEqual({
      kind: "speech", who: "MARGIT HALE", paren: "", text: "Then: I have time.",
    });
  });

  it("writes the blocks back exactly as the backend wrote them", () => {
    expect(formatSceneText(parseSceneText(TEXT))).toBe(TEXT);
  });

  it("changes the words of one block and keeps the speaker", () => {
    const changed = updateBlock(TEXT, 2, { text: "Four places." });
    expect(parseSceneText(changed)[2]).toEqual({ kind: "speech", who: "ELIAS", paren: "looking at the table", text: "Four places." });
    expect(updateBlock(TEXT, 9, { text: "x" })).toBe(TEXT);
  });

  it("changes the speaker and the note of a speech, only the words of a direction", () => {
    expect(parseSceneText(updateBlock(TEXT, 1, { who: "MABEL", paren: "softly" }))[1]).toEqual({
      kind: "speech", who: "MABEL", paren: "softly", text: "You came on the post boat.",
    });
    expect(parseSceneText(updateBlock(TEXT, 0, { text: "Night.", who: "X" }))[0]).toEqual({ kind: "direction", text: "Night." });
  });

  it("inserts and removes lines, also empty new ones", () => {
    const inserted = insertBlock(TEXT, 1, { kind: "speech", who: "ELIAS", paren: "", text: "" });
    expect(parseSceneText(inserted)[2]).toEqual({ kind: "speech", who: "ELIAS", paren: "", text: "" });
    expect(parseSceneText(insertBlock(TEXT, -1, { kind: "direction", text: "" }))[0]).toEqual({ kind: "direction", text: "" });
    expect(removeBlock(inserted, 2)).toBe(TEXT);
  });
});
