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
    expect(initialState.chatOpen).toBe(false);
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

  it("toggles the chat panel", () => {
    expect(reducer(initialState, { type: "toggleChat" }).chatOpen).toBe(true);
  });

  it("opens a character from the grid (or a new one) with the chat closed", () => {
    const state = { ...initialState, cast: [character("a"), character("b")], chatOpen: true };
    const opened = reducer(state, { type: "openCharacter", index: 1 });
    expect(opened.chatOpen).toBe(false);
    expect(reducer(state, { type: "characterAdded", character: character("c"), card: BLANK_CARD }).chatOpen).toBe(false);
  });

  it("adds the user message, then applies only the AI's changed fields and highlights them", () => {
    const elena = { ...character("elena"), personality: "Calm.", goal: "Old goal" } as Character;
    let state = { ...initialState, cast: [elena], draft: "make her cynical" };
    state = reducer(state, { type: "revisionRequested", id: "elena", text: "make her cynical" });
    expect(state.draft).toBe("");
    expect(state.aiTypingFor).toBe("elena");
    expect(state.chats.elena).toEqual([{ role: "user", text: "make her cynical" }]);

    // the user edits the goal while the AI is typing
    state = reducer(state, { type: "updateCharacter", id: "elena", patch: { goal: "New goal" } });
    state = reducer(state, {
      type: "revisionAnswered",
      id: "elena",
      result: {
        decision: "accept_with_adjustments",
        changed_fields: ["personality"],
        character: { ...elena, personality: "Calm. Revised: Cynical." },
        text: "done",
      },
    });
    expect(state.aiTypingFor).toBeNull();
    expect(state.cast[0]).toMatchObject({ personality: "Calm. Revised: Cynical.", goal: "New goal" });
    expect(state.chats.elena[1]).toMatchObject({ role: "ai", decision: "accept_with_adjustments", changed_fields: ["personality"] });
    expect(state.highlight).toEqual({ id: "elena", fields: ["personality"] });
    expect(reducer(state, { type: "clearHighlight" }).highlight).toBeNull();
  });

  it("stops the typing indicator when the revision fails", () => {
    const state = reducer({ ...initialState, cast: [character("a")] }, { type: "revisionRequested", id: "a", text: "x" });
    expect(reducer(state, { type: "revisionFailed", id: "a" }).aiTypingFor).toBeNull();
  });

  it("marks the generation ready without leaving the generating screen", () => {
    const started = reducer({ ...initialState, error: { message: "m", detail: "d" } }, { type: "generationStarted" });
    expect(started).toMatchObject({ screen: "generating", generationReady: false, error: null });
    const done = reducer(started, { type: "castGenerated", characters: [character("a")], cards: { a: BLANK_CARD } });
    expect(done).toMatchObject({ screen: "generating", generationReady: true });
  });

  describe("auto-save and card update", () => {
    const elena = { ...character("elena"), personality: "Calm", goal: "Win" } as Character;
    const generated = reducer(initialState, { type: "castGenerated", characters: [elena], cards: { elena: BLANK_CARD } });

    it("snapshots the card sources on generation and marks edits dirty", () => {
      expect(generated.cardSnapshot.elena).toMatchObject({ personality: "Calm", goal: "Win" });
      const edited = reducer(generated, { type: "updateCharacter", id: "elena", patch: { goal: "Lose" } });
      expect(edited.dirty).toEqual(["elena"]);
      expect(reducer(edited, { type: "saved", ids: ["elena"] }).dirty).toEqual([]);
    });

    it("replaces the card and the snapshot when the update arrives", () => {
      const updating = reducer(generated, { type: "cardsUpdating", ids: ["elena"] });
      expect(updating.updating).toEqual(["elena"]);
      const card = { ...BLANK_CARD, tagline: "New" };
      const done = reducer(updating, {
        type: "cardUpdated",
        id: "elena",
        card,
        sources: { ...generated.cardSnapshot.elena, goal: "Lose" },
      });
      expect(done.updating).toEqual([]);
      expect(done.cards.elena).toBe(card);
      expect(done.cardSnapshot.elena.goal).toBe("Lose");
    });

    it("keeps the old card when the update fails", () => {
      const updating = reducer(generated, { type: "cardsUpdating", ids: ["elena"] });
      const failed = reducer(updating, { type: "cardUpdateFailed", id: "elena" });
      expect(failed.updating).toEqual([]);
      expect(failed.cards.elena).toBe(BLANK_CARD);
    });

    it("ignores a late card for a character that no longer exists", () => {
      const updating = reducer(generated, { type: "cardsUpdating", ids: ["gone"] });
      const late = reducer(updating, { type: "cardUpdated", id: "gone", card: BLANK_CARD, sources: generated.cardSnapshot.elena });
      expect(late.cards.gone).toBeUndefined();
      expect(late.updating).toEqual([]);
    });
  });
});
