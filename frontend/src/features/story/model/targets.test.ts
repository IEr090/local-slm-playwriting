import { describe, expect, it } from "vitest";
import { aboutLabel, detectActs, detectOutlineFields, detectScenes, predictTargets, wantsNewScene } from "./targets";

const counts = { acts: 4, scenes: 5 };

describe("chat targets", () => {
  it("finds acts by word, digit, roman numeral and ordinal", () => {
    expect(detectActs("Act Two: Margit should be crueller", 4)).toEqual([2]);
    expect(detectActs("make act 3 and act IV shorter", 4)).toEqual([3, 4]);
    expect(detectActs("the first act is slow, the last act too", 4)).toEqual([1, 4]);
    expect(detectActs("acts 1 and 2", 4)).toEqual([1, 2]);
    expect(detectActs("act 9", 4)).toEqual([]);
    expect(detectActs("make it darker", 4)).toEqual([]);
  });

  it("finds scenes, but no roman numerals after 'scene'", () => {
    expect(detectScenes("Scene 3: Agnes should already know", 5)).toEqual([3]);
    expect(detectScenes("scenes 2, 4 and 5", 5)).toEqual([2, 4, 5]);
    expect(detectScenes("in scene two and the final scene", 5)).toEqual([2, 5]);
    expect(detectScenes("scene I", 5)).toEqual([]);
  });

  it("recognises a request for a new scene", () => {
    expect(wantsNewScene("add a scene at dawn on the landing")).toBe(true);
    expect(wantsNewScene("Insert another short scene after scene 2")).toBe(true);
    expect(wantsNewScene("Scene 2: let Margit arrive with Voss")).toBe(false);
  });

  it("finds outline fields from their words", () => {
    expect(detectOutlineFields("make the ending darker")).toEqual(["tone", "synopsis"]);
    expect(detectOutlineFields("move it to the present day")).toEqual(["time_and_world"]);
    expect(detectOutlineFields("hello")).toEqual([]);
  });

  it("understands the agent's answers in Russian", () => {
    expect(detectOutlineFields("Предлагаю тон: «Тёмный и ледяной». Подтверждаете?")).toEqual(["tone"]);
    expect(detectActs("Предлагаю изменить второй акт", 4)).toEqual([2]);
    expect(detectScenes("в сцене 3 и в последней сцене", 5)).toEqual([3, 5]);
    expect(wantsNewScene("Добавлю сцену на рассвете")).toBe(true);
  });

  it("predicts from the message, else from the agent's last proposal", () => {
    expect(predictTargets("acts", "Act Two: crueller", "", counts)).toEqual(["act:2"]);
    expect(predictTargets("acts", "yes, do it", "I would sharpen Act Three.", counts)).toEqual(["act:3"]);
    expect(predictTargets("structure", "add a scene after scene 2", "", counts)).toEqual(["scene:2", "add"]);
    expect(predictTargets("text", "scene 4: sharper", "", counts)).toEqual(["scene:4"]);
    expect(predictTargets("outline", "ok", "", counts)).toEqual([]);
    expect(predictTargets("text", "Yes.", "I suggest a sharper first line. Confirm?", counts, "Scene 1: sharper")).toEqual(["scene:1"]);
  });

  it("labels a bubble that names one act or scene", () => {
    expect(aboutLabel("acts", "Act Two: crueller", counts)).toBe("ACT TWO");
    expect(aboutLabel("scenes", "scene 3 please", counts)).toBe("SCENE 3");
    expect(aboutLabel("scenes", "scenes 2 and 3", counts)).toBeUndefined();
    expect(aboutLabel("outline", "act two", counts)).toBeUndefined();
  });
});
