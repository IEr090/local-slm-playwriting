import { describe, expect, it } from "vitest";
import { BLANK_CARD } from "@/api";
import type { Character } from "@/types/character";
import { initialState, reducer } from "./cast-reducer";

const character = (id: string) => ({ id, name: id, surname: "", relationships: [] }) as unknown as Character;

describe("cast reducer", () => {
  it("starts on the prompt screen with the prototype premise and an empty cast", () => {
    expect(initialState.screen).toBe("prompt");
    expect(initialState.premise).toMatch(/^An independent theatre in Vienna/);
    expect(initialState.cast).toEqual([]);
    expect(initialState.chatOpen).toBe(true);
  });

  it("replaces the cast on generation and resets chats", () => {
    const before = { ...initialState, cast: [character("old")], chats: { old: [{ role: "user" as const, text: "hi" }] } };
    const after = reducer(before, { type: "castGenerated", characters: [character("a")], cards: { a: BLANK_CARD } });
    expect(after.cast.map((c) => c.id)).toEqual(["a"]);
    expect(after.chats).toEqual({});
  });

  it("appends a blank character and opens it", () => {
    const withTwo = { ...initialState, cast: [character("a"), character("b")] };
    const after = reducer(withTwo, { type: "characterAdded", character: character("new"), card: BLANK_CARD });
    expect(after.cast).toHaveLength(3);
    expect(after.selectedIndex).toBe(2);
    expect(after.screen).toBe("detail");
    expect(after.cards.new).toEqual(BLANK_CARD);
  });

  it("shows and dismisses an error", () => {
    const error = { message: "m", detail: "d" };
    const shown = reducer(initialState, { type: "showError", error });
    expect(shown.error).toEqual(error);
    expect(reducer(shown, { type: "dismissError" }).error).toBeNull();
  });

  it("hides the toast when the screen changes", () => {
    const shown = reducer(initialState, { type: "setToast", open: true });
    expect(shown.toast).toBe(true);
    expect(reducer(shown, { type: "setScreen", screen: "prompt" }).toast).toBe(false);
  });

  it("updates one character by id", () => {
    const state = { ...initialState, cast: [character("a"), character("b")] };
    const after = reducer(state, { type: "updateCharacter", id: "b", patch: { name: "Bea", age: 40 } });
    expect(after.cast[1]).toMatchObject({ id: "b", name: "Bea", age: 40 });
    expect(after.cast[0]).toBe(state.cast[0]);
  });

  it("steps through characters with wrap-around and clears the chat draft", () => {
    const state = { ...initialState, cast: [character("a"), character("b"), character("c")], draft: "x" };
    expect(reducer(state, { type: "stepCharacter", delta: -1 }).selectedIndex).toBe(2);
    const next = reducer({ ...state, selectedIndex: 2 }, { type: "stepCharacter", delta: 1 });
    expect(next.selectedIndex).toBe(0);
    expect(next.draft).toBe("");
  });

  it("toggles the chat panel", () => {
    expect(reducer(initialState, { type: "toggleChat" }).chatOpen).toBe(false);
  });
});
