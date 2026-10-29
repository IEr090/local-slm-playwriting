import { describe, expect, it } from "vitest";
import { scene } from "./fixtures";
import { addBlankScene, cutScene, isIncomplete, moveScene, openAfterCut, openAfterMove, toPlan, toScenes } from "./scenes";

const three = [scene(1, { what_happens: "a", status: "approved", planned: true }), scene(2, { what_happens: "b" }), scene(3, { what_happens: "c" })];
const order = (scenes: { what_happens: string }[]) => scenes.map((s) => s.what_happens).join("");

describe("scene list", () => {
  it("keeps only the plan fields of a scene", () => {
    expect(toPlan(three[0])).toEqual({ place_id: "kitchen", place_notes: "", character_ids: ["agnes"], what_happens: "a" });
  });

  it("numbers new draft scenes in list order", () => {
    const scenes = toScenes([toPlan(three[2]), toPlan(three[0])]);
    expect(scenes.map((s) => [s.number, s.status, s.planned])).toEqual([[1, "draft", false], [2, "draft", false]]);
  });

  it("moves a scene up and down, not past the ends", () => {
    expect(order(moveScene(three, 1, -1))).toBe("bac");
    expect(order(moveScene(three, 1, 1))).toBe("acb");
    expect(moveScene(three, 0, -1)).toBe(three);
    expect(moveScene(three, 2, 1)).toBe(three);
  });

  it("cuts a scene and adds a blank one at the end", () => {
    expect(order(cutScene(three, 0))).toBe("bc");
    const added = addBlankScene(three);
    expect(added).toHaveLength(4);
    expect(added[3]).toMatchObject({ number: 4, place_id: "", character_ids: [], what_happens: "" });
    expect(isIncomplete(added[3])).toBe(true);
    expect(isIncomplete(three[0])).toBe(false);
  });

  it("keeps open editors on their scenes when scenes move or are cut", () => {
    expect([...openAfterMove(new Set([1]), 1, -1, 3)]).toEqual([0]);
    expect([...openAfterMove(new Set([0]), 1, -1, 3)]).toEqual([1]);
    expect([...openAfterMove(new Set([2]), 2, 1, 3)]).toEqual([2]);
    expect([...openAfterCut(new Set([0, 2]), 1)]).toEqual([0, 1]);
    expect([...openAfterCut(new Set([1]), 1)]).toEqual([]);
  });
});
