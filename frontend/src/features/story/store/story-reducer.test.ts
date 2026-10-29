import { describe, expect, it } from "vitest";
import { act, scene, story } from "@/features/story/model/fixtures";
import { initialState, reducer, type StoryState } from "./story-reducer";

const withStory = (patch: Partial<StoryState> = {}): StoryState => ({ ...initialState, loaded: true, story: story(), ...patch });

describe("story reducer", () => {
  it("starts unloaded, without a play, with the chat open", () => {
    expect(initialState).toMatchObject({ loaded: false, story: null, jobs: [], chatOpen: true });
  });

  it("loads the Story Bible, also when there is no play yet", () => {
    expect(reducer(initialState, { type: "storyLoaded", story: null })).toMatchObject({ loaded: true, story: null });
    const s = story();
    expect(reducer(initialState, { type: "storyReceived", story: s }).story).toBe(s);
  });

  it("forgets the old play on reset but keeps the chat panel open or closed", () => {
    const state = withStory({ chatOpen: false, jobs: ["outline"], chats: { outline: [{ role: "user", text: "hi" }] } });
    expect(reducer(state, { type: "reset" })).toEqual({ ...initialState, chatOpen: false });
  });

  it("runs a job once and remembers a failed one until it is started again", () => {
    let state = reducer(withStory(), { type: "jobStarted", key: "acts" });
    state = reducer(state, { type: "jobStarted", key: "acts" });
    expect(state.jobs).toEqual(["acts"]);
    state = reducer(state, { type: "jobEnded", key: "acts", failed: true });
    expect(state).toMatchObject({ jobs: [], failed: ["acts"] });
    expect(reducer(state, { type: "jobStarted", key: "acts" })).toMatchObject({ jobs: ["acts"], failed: [] });
    expect(reducer(state, { type: "jobEnded", key: "outline" }).failed).toEqual(["acts"]);
  });

  it("edits the outline and an act summary", () => {
    let state = reducer(withStory(), { type: "outlineEdited", patch: { title: "New" } });
    expect(state.story?.outline?.title).toBe("New");
    state = reducer(state, { type: "actEdited", number: 2, summary: "Changed." });
    expect(state.story?.acts[1]).toMatchObject({ summary: "Changed.", dramatic_function: "development" });
    state = reducer(state, { type: "actEdited", number: 2, summary: "Again.", dramatic_function: "climax" });
    expect(state.story?.acts[1].dramatic_function).toBe("climax");
    expect(reducer(initialState, { type: "outlineEdited", patch: { title: "x" } })).toBe(initialState);
  });

  it("replaces the scenes of a draft structure", () => {
    const state = reducer(withStory(), { type: "scenesEdited", number: 1, scenes: [scene(1)] });
    expect(state.story?.acts[0].scenes).toEqual([scene(1)]);
  });

  it("makes an edited plan a draft again, like the backend", () => {
    const planned = withStory({
      story: story({ acts: [act(1, { status: "scenes_approved", scenes: [scene(1, { status: "approved" }), scene(2, { status: "approved" })] })] }),
    });
    const state = reducer(planned, { type: "sceneEdited", number: 1, scene: 2, patch: { what_happens: "x" } });
    expect(state.story?.acts[0].status).toBe("structure_approved");
    expect(state.story?.acts[0].scenes[1]).toMatchObject({ what_happens: "x", status: "draft" });
    expect(state.story?.acts[0].scenes[0].status).toBe("approved");
  });

  it("keeps a draft structure a draft when a scene is edited", () => {
    const draft = withStory({ story: story({ acts: [act(1, { scenes: [scene(1)] })] }) });
    expect(reducer(draft, { type: "sceneEdited", number: 1, scene: 1, patch: { place_id: "" } }).story?.acts[0].status).toBe("draft");
  });

  it("stores scene texts and places", () => {
    let state = reducer(withStory(), { type: "sceneTextsEdited", number: 1, sceneTexts: [{ scene_number: 1, text: "A: b" }] });
    expect(state.story?.acts[0].scene_texts).toEqual([{ scene_number: 1, text: "A: b" }]);
    state = reducer(state, { type: "placesReceived", places: [] });
    expect(state.story?.places).toEqual([]);
  });

  it("sends a message: draft cleared, typing, the predicted targets updating", () => {
    const state = reducer(withStory({ draft: "Act Two: crueller" }), {
      type: "messageSent", key: "acts", text: "Act Two: crueller", about: "ACT TWO", pending: ["act:2"],
    });
    expect(state).toMatchObject({ draft: "", typing: "acts", pending: ["act:2"] });
    expect(state.chats.acts).toEqual([{ role: "user", text: "Act Two: crueller", about: "ACT TWO" }]);
  });

  it("takes the answer: typing and updating end, the changes glow", () => {
    let state = reducer(withStory(), { type: "messageSent", key: "outline", text: "darker", pending: ["outline:tone"] });
    state = reducer(state, { type: "replyReceived", key: "outline", text: "Done.", updated: ["Tone / Atmosphere"], highlight: ["outline:tone"] });
    expect(state).toMatchObject({ typing: null, pending: [], highlight: ["outline:tone"] });
    expect(state.chats.outline?.[1]).toEqual({ role: "ai", text: "Done.", updated: ["Tone / Atmosphere"] });
    expect(reducer(state, { type: "clearHighlight" }).highlight).toEqual([]);
  });

  it("stops typing when the agent fails", () => {
    const state = reducer(withStory(), { type: "messageSent", key: "act:1", text: "x", pending: ["scene:1:1"] });
    expect(reducer(state, { type: "replyFailed", key: "act:1" })).toMatchObject({ typing: null, pending: [] });
  });

  it("loads a chat history unless the chat has already started", () => {
    const history = [{ role: "user" as const, text: "old" }];
    expect(reducer(withStory(), { type: "chatLoaded", key: "acts", messages: history }).chats.acts).toEqual(history);
    const started = reducer(withStory(), { type: "messageSent", key: "acts", text: "new", pending: [] });
    expect(reducer(started, { type: "chatLoaded", key: "acts", messages: history }).chats.acts).toHaveLength(1);
  });

  it("clears one chat, e.g. when the act page's chat starts anew", () => {
    const state = reducer(withStory(), { type: "messageSent", key: "act:1", text: "x", pending: [] });
    expect(reducer(state, { type: "chatCleared", key: "act:1" }).chats["act:1"]).toBeUndefined();
  });

  it("toggles the chat and the scene editor of an act", () => {
    expect(reducer(initialState, { type: "toggleChat" }).chatOpen).toBe(false);
    let state = reducer(initialState, { type: "setEditingScenes", number: 2, editing: true });
    state = reducer(state, { type: "setEditingScenes", number: 2, editing: true });
    expect(state.editingScenes).toEqual([2]);
    expect(reducer(state, { type: "setEditingScenes", number: 2, editing: false }).editingScenes).toEqual([]);
  });
});
