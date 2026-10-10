import { describe, expect, it } from "vitest";
import { BLANK_CARD } from "@/features/characters/api";
import type { Character } from "@/features/characters/model/types";
import { initialState, reducer } from "./cast-reducer";

const character = (id: string) => ({ id, name: id, surname: "", relationships: [] }) as unknown as Character;

describe("cast reducer", () => {
  it("starts with the default premise, an empty cast, nothing loaded and no generation", () => {
    expect(initialState.loaded).toBe(false);
    expect(initialState.generation).toBe("idle");
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

  it("appends a blank character with its card, not saved yet", () => {
    const withTwo = { ...initialState, cast: [character("a"), character("b")] };
    const after = reducer(withTwo, { type: "characterAdded", character: character("new"), card: BLANK_CARD });
    expect(after.cast.map((c) => c.id)).toEqual(["a", "b", "new"]);
    expect(after.cards.new).toEqual(BLANK_CARD);
    expect(after.saved.new).toBeUndefined();
  });

  it("loads the saved cast once, but never over a cast that is already there", () => {
    const loaded = reducer(initialState, { type: "castLoaded", characters: [character("a")], cards: { a: BLANK_CARD } });
    expect(loaded.loaded).toBe(true);
    expect(loaded.cast.map((c) => c.id)).toEqual(["a"]);
    const generated = reducer(initialState, { type: "castGenerated", characters: [character("new")], cards: { new: BLANK_CARD } });
    const late = reducer(generated, { type: "castLoaded", characters: [character("old")], cards: { old: BLANK_CARD } });
    expect(late.cast.map((c) => c.id)).toEqual(["new"]);
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

  it("opens a character with the chat closed and an empty draft", () => {
    const state = { ...initialState, chatOpen: true, draft: "half-typed" };
    expect(reducer(state, { type: "characterOpened" })).toMatchObject({ chatOpen: false, draft: "" });
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

  it("runs a generation: running → ready (cast arrives) → idle", () => {
    const started = reducer(initialState, { type: "generationStarted" });
    expect(started.generation).toBe("running");
    const done = reducer(started, { type: "castGenerated", characters: [character("a")], cards: { a: BLANK_CARD } });
    expect(done).toMatchObject({ generation: "ready", loaded: true });
    expect(reducer(done, { type: "generationEnded" }).generation).toBe("idle");
  });

  describe("saving", () => {
    const elena = { ...character("elena"), personality: "Calm", goal: "Win" } as Character;
    const generated = reducer(initialState, { type: "castGenerated", characters: [elena], cards: { elena: BLANK_CARD } });
    const edited = reducer(generated, { type: "updateCharacter", id: "elena", patch: { goal: "Lose" } });

    it("keeps the saved version apart from the edited one", () => {
      expect(edited.saved.elena.goal).toBe("Win");
      expect(edited.cast[0].goal).toBe("Lose");
    });

    it("marks the character saving, and updating only if its card is regenerated", () => {
      const quick = reducer(edited, { type: "saveStarted", id: "elena", regenerates: false });
      expect(quick).toMatchObject({ saving: ["elena"], updating: [] });
      const slow = reducer(edited, { type: "saveStarted", id: "elena", regenerates: true });
      expect(slow).toMatchObject({ saving: ["elena"], updating: ["elena"] });
    });

    it("stores the saved version and the new card when the save succeeds", () => {
      const saving = reducer(edited, { type: "saveStarted", id: "elena", regenerates: true });
      const card = { ...BLANK_CARD, tagline: "New" };
      const done = reducer(saving, { type: "characterSaved", id: "elena", character: edited.cast[0], card });
      expect(done).toMatchObject({ saving: [], updating: [] });
      expect(done.saved.elena.goal).toBe("Lose");
      expect(done.cards.elena).toBe(card);
    });

    it("replaces the temporary id of a created character with the backend id", () => {
      let state = reducer(generated, { type: "characterAdded", character: character("temp"), card: BLANK_CARD });
      state = { ...state, chats: { temp: [{ role: "user", text: "hi" }] } };
      state = reducer(state, { type: "saveStarted", id: "temp", regenerates: true });
      const card = { ...BLANK_CARD, tagline: "Created" };
      state = reducer(state, { type: "characterSaved", id: "temp", character: character("real"), card });
      expect(state.cast.map((c) => c.id)).toEqual(["elena", "real"]);
      expect(state.cards.temp).toBeUndefined();
      expect(state.cards.real).toBe(card);
      expect(state.saved.real).toBeDefined();
      expect(state.chats).toEqual({ real: [{ role: "user", text: "hi" }] });
      expect(state.saving).toEqual([]);
    });

    it("keeps the edits when the save fails", () => {
      const saving = reducer(edited, { type: "saveStarted", id: "elena", regenerates: true });
      const failed = reducer(saving, { type: "saveFailed", id: "elena" });
      expect(failed).toMatchObject({ saving: [], updating: [] });
      expect(failed.cast[0].goal).toBe("Lose");
      expect(failed.cards.elena).toBe(BLANK_CARD);
    });

    it("ignores a late save for a character that no longer exists", () => {
      const saving = reducer(generated, { type: "saveStarted", id: "gone", regenerates: true });
      const late = reducer(saving, { type: "characterSaved", id: "gone", character: character("gone"), card: BLANK_CARD });
      expect(late.cards.gone).toBeUndefined();
      expect(late.saving).toEqual([]);
    });

    it("drops the edits when the character is left without saving", () => {
      const left = reducer(edited, { type: "characterLeft", id: "elena" });
      expect(left.cast[0]).toBe(generated.saved.elena);
    });

    it("drops a new character that is left without creating it", () => {
      const added = reducer(generated, { type: "characterAdded", character: character("temp"), card: BLANK_CARD });
      const left = reducer(added, { type: "characterLeft", id: "temp" });
      expect(left.cast.map((c) => c.id)).toEqual(["elena"]);
      expect(left.cards.temp).toBeUndefined();
    });

    it("keeps a character that is being saved when the page is left", () => {
      const saving = reducer(edited, { type: "saveStarted", id: "elena", regenerates: false });
      expect(reducer(saving, { type: "characterLeft", id: "elena" })).toBe(saving);
    });
  });
});
