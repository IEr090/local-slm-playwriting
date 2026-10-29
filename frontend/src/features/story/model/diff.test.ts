import { describe, expect, it } from "vitest";
import { changedActNumbers, changedBlocks, changedOutlineFields, changedSceneIndexes, changedSceneTextNumbers } from "./diff";
import { outline, scene } from "./fixtures";

describe("what the agent changed", () => {
  it("finds changed outline fields", () => {
    expect(changedOutlineFields(outline, { ...outline, tone: "Darker.", genre: "tragedy" })).toEqual(["genre", "tone"]);
    expect(changedOutlineFields(outline, outline)).toEqual([]);
  });

  it("finds changed acts by number", () => {
    const before = [1, 2].map((number) => ({ number, summary: "s", dramatic_function: "setup" as const }));
    const after = [before[0], { ...before[1], summary: "new" }];
    expect(changedActNumbers(before, after)).toEqual([2]);
  });

  it("finds changed and added scenes by position", () => {
    const before = [scene(1), scene(2)];
    expect(changedSceneIndexes(before, [scene(1), scene(2, { what_happens: "x" }), scene(3)])).toEqual([1, 2]);
    // numbering and status are not part of the plan
    expect(changedSceneIndexes(before, [scene(1, { status: "approved", number: 9 }), scene(2)])).toEqual([]);
  });

  it("finds changed scene texts and the changed blocks in them", () => {
    const before = [{ scene_number: 1, text: "A: hi" }, { scene_number: 2, text: "B: yo" }];
    expect(changedSceneTextNumbers(before, [before[0], { scene_number: 2, text: "B: hey" }])).toEqual([2]);
    expect(changedBlocks("(Night.)\n\nA: hi\n\nB: yo", "(Night.)\n\nA: hello\n\nB: yo\n\n(Dark.)")).toEqual([1, 3]);
  });
});
