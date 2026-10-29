import { describe, expect, it } from "vitest";
import { formatSceneText, mergeRevisedScene, parseBlock, parseSceneText, replaceBlockText } from "./script";

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

  it("replaces the words of one block and keeps the speaker", () => {
    const changed = replaceBlockText(TEXT, 2, "Four places.");
    expect(parseSceneText(changed)[2]).toEqual({ kind: "speech", who: "ELIAS", paren: "looking at the table", text: "Four places." });
    expect(replaceBlockText(TEXT, 9, "x")).toBe(TEXT);
  });
});

describe("mergeRevisedScene", () => {
  const scene = [
    "(Night. The lamp room.)",
    "ELIAS (trembling): The lens is clear. The storm hasn't damaged the lighthouse.",
    "AVA: The plans are ready.",
    "ELIAS: Then we wait.",
    "(The wind rises.)",
  ].join("\n\n");

  it("keeps a full answer as it is", () => {
    const full = scene.replace("Then we wait.", "Then we go.");
    expect(mergeRevisedScene(scene, full)).toBe(full);
  });

  it("puts a few returned lines in place of the most similar line of the same speaker", () => {
    const merged = parseSceneText(mergeRevisedScene(scene, "ELIAS (trembling): The lens is clear."));
    expect(merged).toHaveLength(5);
    expect(merged[1]).toEqual({ kind: "speech", who: "ELIAS", paren: "trembling", text: "The lens is clear." });
    expect(merged[3]).toEqual({ kind: "speech", who: "ELIAS", paren: "", text: "Then we wait." });
  });

  it("leaves short scenes to the agent", () => {
    expect(mergeRevisedScene("A: x\n\nB: y", "A: z")).toBe("A: z");
  });
});
