import { describe, expect, it } from "vitest";
import { play } from "./fixtures";
import {
  actCountInWords,
  activeSection,
  actOfSection,
  actSection,
  blockText,
  cleanLine,
  contentsTotals,
  playSummary,
  readerSub,
  sceneCount,
  sceneSection,
  titleLine,
  withBlockText,
} from "./play-reader";

describe("sections", () => {
  it("names the sections of acts and scenes", () => {
    expect(actSection(2)).toBe("act-2");
    expect(sceneSection(2, 3)).toBe("a2s3");
  });

  it("finds the act of a section", () => {
    expect(actOfSection("act-2")).toBe(2);
    expect(actOfSection("a3s1")).toBe(3);
    expect(actOfSection("title")).toBeNull();
    expect(actOfSection("cast")).toBeNull();
  });
});

describe("activeSection", () => {
  const sections = [
    { id: "title", top: 0 },
    { id: "cast", top: 400 },
    { id: "act-1", top: 900 },
    { id: "a1s1", top: 1100 },
    { id: "a1s2", top: 2000 },
  ];

  it("is the title page at the top", () => {
    expect(activeSection(sections, 0, 140)).toBe("title");
  });

  it("is the last section that starts above the scroll position plus the margin", () => {
    expect(activeSection(sections, 300, 140)).toBe("cast");
    expect(activeSection(sections, 1000, 140)).toBe("a1s1");
    expect(activeSection(sections, 5000, 140)).toBe("a1s2");
  });

  it("counts the margin: a section about to reach the top is already active", () => {
    expect(activeSection(sections, 259, 140)).toBe("title");
    expect(activeSection(sections, 260, 140)).toBe("cast");
  });

  it("falls back to the first section, or the title page when there are none", () => {
    expect(activeSection(sections, -500, 0)).toBe("title");
    expect(activeSection([], 100, 140)).toBe("title");
  });
});

describe("labels", () => {
  it("counts scenes and writes the totals under the contents", () => {
    expect(sceneCount(play())).toBe(3);
    expect(contentsTotals(play())).toBe("2 ACTS · 3 SCENES");
    expect(contentsTotals(play({ acts: [{ number: 1, scenes: [play().acts[0].scenes[0]] }] }))).toBe("1 ACT · 1 SCENE");
  });

  it("writes the number of acts in words", () => {
    expect(actCountInWords(4)).toBe("four");
    expect(actCountInWords(12)).toBe("12");
  });

  it("writes the line under the title", () => {
    expect(titleLine("drama", 4)).toBe("A drama in four acts");
    expect(titleLine("Tragicomedy", 1)).toBe("A tragicomedy in one act");
  });

  it("describes the header while the text is locked or not", () => {
    expect(readerSub(false)).toBe("Every act is written and approved.");
    expect(readerSub(true)).toContain("unlocked");
  });

  it("summarises the play for the finale card", () => {
    expect(playSummary(4, 10)).toBe("Four acts and ten scenes.");
    expect(playSummary(1, 1)).toBe("One act and one scene.");
    expect(playSummary(5, 14)).toBe("Five acts and 14 scenes.");
  });
});

describe("editing one line", () => {
  const text = "(Late afternoon.)\n\nAGNES (at the stove): You came.\n\nELIAS: The last boat.";

  it("reads the words of a direction and of a speech", () => {
    expect(blockText(text, 0)).toBe("Late afternoon.");
    expect(blockText(text, 1)).toBe("You came.");
    expect(blockText(text, 7)).toBeNull();
  });

  it("changes only the words of that block", () => {
    expect(withBlockText(text, 1, "You came late.")).toBe("(Late afternoon.)\n\nAGNES (at the stove): You came late.\n\nELIAS: The last boat.");
    expect(withBlockText(text, 0, "Dusk.")).toBe("(Dusk.)\n\nAGNES (at the stove): You came.\n\nELIAS: The last boat.");
  });

  it("leaves the text alone for a block that does not exist or is plain text", () => {
    expect(withBlockText(text, 9, "x")).toBe(text);
    const plain = "Something else entirely\n\nAGNES: Yes.";
    expect(withBlockText(plain, 0, "x")).toBe(plain);
  });

  it("keeps the number of blocks when the words hold an empty line", () => {
    expect(cleanLine("one\n\ntwo")).toBe("one\ntwo");
    const changed = withBlockText(text, 1, "one\n\ntwo");
    expect(changed.split(/\n\s*\n/)).toHaveLength(3);
  });

  it("can empty the words of a line without emptying the scene", () => {
    expect(withBlockText("AGNES: You came.", 0, "")).toBe("AGNES: ");
    expect(withBlockText("(Dusk.)", 0, "").trim()).not.toBe("");
  });
});
