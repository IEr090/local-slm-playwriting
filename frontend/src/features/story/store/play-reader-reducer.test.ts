import { describe, expect, it } from "vitest";
import { play } from "@/features/story/model/fixtures";
import { findScene, initialReaderState, isChanged, readerReducer, type PlayReaderState } from "./play-reader-reducer";

const loaded = (): PlayReaderState => readerReducer(initialReaderState, { type: "playLoaded", play: play() });
const text = (state: PlayReaderState, act: number, scene: number) => findScene(state.play!, act, scene)!.text;

describe("readerReducer", () => {
  it("starts without a play and takes the loaded one", () => {
    expect(initialReaderState.play).toBeNull();
    expect(loaded().play).toEqual(play());
  });

  it("changes the words of one line in its scene and marks the line as changed", () => {
    const state = readerReducer(loaded(), { type: "lineEdited", act: 1, scene: 1, index: 1, value: "You came late." });
    expect(text(state, 1, 1)).toContain("AGNES (at the stove): You came late.");
    expect(text(state, 1, 2)).toBe("AGNES: Cut it straight.");
    expect(isChanged(state, 1, 1, 1)).toBe(true);
    expect(isChanged(state, 1, 1, 0)).toBe(false);
  });

  it("takes the line back as unchanged when it is typed back to the original words", () => {
    let state = readerReducer(loaded(), { type: "lineEdited", act: 1, scene: 1, index: 1, value: "You came late." });
    state = readerReducer(state, { type: "lineEdited", act: 1, scene: 1, index: 1, value: "You came late, again." });
    expect(isChanged(state, 1, 1, 1)).toBe(true);
    state = readerReducer(state, { type: "lineEdited", act: 1, scene: 1, index: 1, value: "You came." });
    expect(isChanged(state, 1, 1, 1)).toBe(false);
    expect(text(state, 1, 1)).toBe(text(loaded(), 1, 1));
  });

  it("ignores an edit of an unknown scene or line", () => {
    const state = loaded();
    expect(readerReducer(state, { type: "lineEdited", act: 9, scene: 1, index: 0, value: "x" })).toBe(state);
    expect(readerReducer(state, { type: "lineEdited", act: 1, scene: 1, index: 9, value: "x" })).toBe(state);
  });

  it("takes the play from a save answer but keeps the scenes typed into since", () => {
    let state = readerReducer(loaded(), { type: "lineEdited", act: 1, scene: 1, index: 0, value: "Dusk." });
    const answer = play({
      acts: [
        { number: 1, scenes: [{ number: 1, place_name: "Kitchen", place_notes: "", text: "(Late afternoon.)" }, { number: 2, place_name: "Lamp", place_notes: "", text: "AGNES: Saved." }] },
        play().acts[1],
      ],
    });
    state = readerReducer(state, { type: "playReceived", play: answer, keep: ["1:1"] });
    expect(text(state, 1, 1)).toContain("Dusk.");
    expect(text(state, 1, 2)).toBe("AGNES: Saved.");
    // the edit stays marked
    expect(isChanged(state, 1, 1, 0)).toBe(true);
  });

  it("takes the whole answer when nothing was typed since", () => {
    const answer = play({ title: "Another" });
    expect(readerReducer(loaded(), { type: "playReceived", play: answer, keep: [] }).play).toEqual(answer);
  });
});
