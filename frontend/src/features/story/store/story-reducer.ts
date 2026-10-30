// Story Bible state and reducer. Pure: no api calls, no timers, no navigation here.
// The Story Bible itself comes from the backend; the local copy also holds the user's unsaved edits.

import type { DramaticFunction, Outline, Place, Scene, SceneText, StoryBible } from "@/features/story/model/types";
import type { ChatBubble } from "@/shared/ui/chat/ChatMessage";

/** One chat per page: the outline, the acts, and one per act page. */
export type ChatKey = "outline" | "acts" | `act:${number}`;

/**
 * Running requests, so a page shows the veil and a second request for the same thing is not started:
 * "outline", "acts" (generation), "approveActs", "structure:N", "approveStructure:N", "plan:N:S", "scene:N:S"
 * (approve / reopen), "text:N" (writing), "record:N" (approving the text), "place".
 */
export type JobKey = string;

export interface StoryState {
  /** The Story Bible has been read from the backend (after a page load or a new cast). */
  loaded: boolean;
  /** null: no play has been started yet. */
  story: StoryBible | null;
  jobs: JobKey[];
  /** Generations that failed in this session; they are not started again on their own, only by the user. */
  failed: JobKey[];
  chats: Partial<Record<ChatKey, ChatBubble[]>>;
  /** The chat whose agent is answering (typing indicator), or null. */
  typing: ChatKey | null;
  /**
   * What the agent is probably changing right now ("UPDATING" overlay) and what it has just changed (gold glow):
   * "outline:<field>", "act:N", "scene:N:S", "add:N" (a new scene of act N), "block:N:S:I" (a line of the text).
   */
  pending: string[];
  highlight: string[];
  chatOpen: boolean;
  draft: string;
  /** Acts whose page shows the scene plans instead of the written text (EDIT SCENES). */
  editingScenes: number[];
}

export const initialState: StoryState = {
  loaded: false,
  story: null,
  jobs: [],
  failed: [],
  chats: {},
  typing: null,
  pending: [],
  highlight: [],
  chatOpen: true,
  draft: "",
  editingScenes: [],
};

export type Action =
  | { type: "storyLoaded"; story: StoryBible | null }
  | { type: "storyReceived"; story: StoryBible }
  | { type: "reset" }
  | { type: "jobStarted"; key: JobKey }
  | { type: "jobEnded"; key: JobKey; failed?: boolean }
  | { type: "outlineEdited"; patch: Partial<Outline> }
  | { type: "actEdited"; number: number; summary: string; dramatic_function?: DramaticFunction }
  | { type: "scenesEdited"; number: number; scenes: Scene[] }
  | { type: "sceneEdited"; number: number; scene: number; patch: Partial<Scene> }
  | { type: "sceneTextsEdited"; number: number; sceneTexts: SceneText[] }
  | { type: "placesReceived"; places: Place[] }
  | { type: "toggleChat" }
  | { type: "setDraft"; draft: string }
  | { type: "chatLoaded"; key: ChatKey; messages: ChatBubble[] }
  | { type: "chatCleared"; key: ChatKey }
  | { type: "messageSent"; key: ChatKey; text: string; about?: string; pending: string[] }
  | { type: "replyReceived"; key: ChatKey; text: string; updated: string[]; highlight: string[] }
  | { type: "replyFailed"; key: ChatKey }
  | { type: "clearHighlight" }
  | { type: "setEditingScenes"; number: number; editing: boolean };

export function reducer(state: StoryState, action: Action): StoryState {
  switch (action.type) {
    case "storyLoaded":
      return { ...state, loaded: true, story: action.story };
    case "storyReceived":
      return { ...state, loaded: true, story: action.story };
    case "reset":
      return { ...initialState, chatOpen: state.chatOpen };
    case "jobStarted":
      return {
        ...state,
        jobs: state.jobs.includes(action.key) ? state.jobs : [...state.jobs, action.key],
        failed: without(state.failed, action.key),
      };
    case "jobEnded":
      return {
        ...state,
        jobs: without(state.jobs, action.key),
        failed: action.failed && !state.failed.includes(action.key) ? [...state.failed, action.key] : state.failed,
      };
    case "outlineEdited":
      return withStory(state, (story) => (story.outline ? { ...story, outline: { ...story.outline, ...action.patch } } : story));
    case "actEdited":
      return withAct(state, action.number, (act) => ({
        ...act,
        summary: action.summary,
        dramatic_function: action.dramatic_function ?? act.dramatic_function,
      }));
    case "scenesEdited":
      return withAct(state, action.number, (act) => ({ ...act, scenes: action.scenes }));
    case "sceneEdited":
      // like the backend: an edited scene is a draft again, so the act's scenes are no longer all approved
      return withAct(state, action.number, (act) => ({
        ...act,
        status: act.status === "draft" ? "draft" : "structure_approved",
        scenes: act.scenes.map((scene) =>
          scene.number === action.scene
            ? { ...scene, ...action.patch, status: act.status === "draft" ? scene.status : "draft" }
            : scene,
        ),
      }));
    case "sceneTextsEdited":
      return withAct(state, action.number, (act) => ({ ...act, scene_texts: action.sceneTexts }));
    case "placesReceived":
      return withStory(state, (story) => ({ ...story, places: action.places }));
    case "toggleChat":
      return { ...state, chatOpen: !state.chatOpen };
    case "setDraft":
      return { ...state, draft: action.draft };
    case "chatLoaded":
      // a message sent before the history arrived already started the chat
      return state.chats[action.key] ? state : { ...state, chats: { ...state.chats, [action.key]: action.messages } };
    case "chatCleared": {
      const { [action.key]: _cleared, ...chats } = state.chats;
      return { ...state, chats };
    }
    case "messageSent":
      return {
        ...state,
        draft: "",
        typing: action.key,
        pending: action.pending,
        chats: { ...state.chats, [action.key]: [...(state.chats[action.key] ?? []), { role: "user", text: action.text, about: action.about }] },
      };
    case "replyReceived":
      return {
        ...state,
        typing: state.typing === action.key ? null : state.typing,
        pending: [],
        highlight: action.highlight.length ? action.highlight : state.highlight,
        chats: {
          ...state.chats,
          [action.key]: [...(state.chats[action.key] ?? []), { role: "ai", text: action.text, updated: action.updated }],
        },
      };
    case "replyFailed":
      return { ...state, typing: state.typing === action.key ? null : state.typing, pending: [] };
    case "clearHighlight":
      return { ...state, highlight: [] };
    case "setEditingScenes":
      return {
        ...state,
        editingScenes: action.editing
          ? [...without(state.editingScenes, action.number), action.number]
          : without(state.editingScenes, action.number),
      };
  }
}

function withStory(state: StoryState, change: (story: StoryBible) => StoryBible): StoryState {
  return state.story ? { ...state, story: change(state.story) } : state;
}

function withAct(state: StoryState, number: number, change: (act: StoryBible["acts"][number]) => StoryBible["acts"][number]): StoryState {
  return withStory(state, (story) => ({
    ...story,
    acts: story.acts.map((act) => (act.number === number ? change(act) : act)),
  }));
}

const without = <T,>(items: T[], item: T) => items.filter((x) => x !== item);
