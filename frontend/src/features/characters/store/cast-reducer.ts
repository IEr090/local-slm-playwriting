// Character Creator state and reducer. Pure: no api calls, no navigation here.
// Which page is shown is decided by the router (URL), not by this state.

import { DEFAULT_PREMISE } from "@/features/characters/api/mock-data";
import type { Character, CharacterCard, ChatMessage, RevisionResult } from "@/features/characters/model/types";

/** idle → running (waiting for the api) → ready (api answered, animation plays the names) → idle. */
export type GenerationStatus = "idle" | "running" | "ready";

export interface CastState {
  /** The saved cast has been read from the api (after a page load). */
  loaded: boolean;
  premise: string;
  generation: GenerationStatus;
  cast: Character[];
  cards: Record<string, CharacterCard>;
  /** AI chat panel; closed whenever a character is opened (toggle in the header). */
  chatOpen: boolean;
  chats: Record<string, ChatMessage[]>;
  draft: string;
  /** Id of the character the AI is currently answering for (typing indicator), or null. */
  aiTypingFor: string | null;
  /** Fields that glow for a moment after an AI revision. */
  highlight: { id: string; fields: (keyof Character)[] } | null;
  /** The versions saved on the backend; `cast` holds the edited ones. A new character is not here yet. */
  saved: Record<string, Character>;
  /** Ids of characters being saved (CREATE / SAVE); they cannot be opened meanwhile. */
  saving: string[];
  /** Ids of saving characters whose card is being regenerated (updating overlay). */
  updating: string[];
}

export const initialState: CastState = {
  loaded: false,
  premise: DEFAULT_PREMISE,
  generation: "idle",
  cast: [],
  cards: {},
  chatOpen: false,
  chats: {},
  draft: "",
  aiTypingFor: null,
  highlight: null,
  saved: {},
  saving: [],
  updating: [],
};

export type Action =
  | { type: "castLoaded"; characters: Character[]; cards: Record<string, CharacterCard> }
  | { type: "setPremise"; premise: string }
  | { type: "generationStarted" }
  | { type: "castGenerated"; characters: Character[]; cards: Record<string, CharacterCard> }
  | { type: "generationEnded" }
  | { type: "characterAdded"; character: Character; card: CharacterCard }
  | { type: "characterOpened" }
  | { type: "updateCharacter"; id: string; patch: Partial<Omit<Character, "id">> }
  | { type: "toggleChat" }
  | { type: "setDraft"; draft: string }
  | { type: "revisionRequested"; id: string; text: string }
  | { type: "revisionAnswered"; id: string; result: RevisionResult }
  | { type: "revisionFailed"; id: string }
  | { type: "clearHighlight" }
  | { type: "saveStarted"; id: string; regenerates: boolean }
  | { type: "characterSaved"; id: string; character: Character; card: CharacterCard }
  | { type: "saveFailed"; id: string }
  | { type: "characterLeft"; id: string };

/** A fresh cast (generated or loaded): new cards, everything saved, no chats. */
function withCast(state: CastState, characters: Character[], cards: Record<string, CharacterCard>): CastState {
  return {
    ...state,
    loaded: true,
    cast: characters,
    cards,
    chats: {},
    saved: Object.fromEntries(characters.map((c) => [c.id, c])),
    saving: [],
    updating: [],
  };
}

export function reducer(state: CastState, action: Action): CastState {
  switch (action.type) {
    case "castLoaded":
      return state.loaded ? state : withCast(state, action.characters, action.cards);
    case "setPremise":
      return { ...state, premise: action.premise };
    case "generationStarted":
      return { ...state, generation: "running" };
    case "castGenerated":
      return { ...withCast(state, action.characters, action.cards), generation: "ready" };
    case "generationEnded":
      return { ...state, generation: "idle" };
    case "characterAdded":
      return {
        ...state,
        loaded: true,
        cast: [...state.cast, action.character],
        cards: { ...state.cards, [action.character.id]: action.card },
      };
    case "characterOpened":
      return { ...state, draft: "", chatOpen: false };
    case "updateCharacter":
      return {
        ...state,
        cast: state.cast.map((c) => (c.id === action.id ? { ...c, ...action.patch } : c)),
      };
    case "toggleChat":
      return { ...state, chatOpen: !state.chatOpen };
    case "setDraft":
      return { ...state, draft: action.draft };
    case "revisionRequested":
      return {
        ...state,
        draft: "",
        aiTypingFor: action.id,
        chats: { ...state.chats, [action.id]: [...(state.chats[action.id] ?? []), { role: "user", text: action.text }] },
      };
    case "revisionAnswered": {
      const { result } = action;
      const patch = Object.fromEntries(result.changed_fields.map((f) => [f, result.character[f]]));
      return {
        ...state,
        aiTypingFor: null,
        cast: state.cast.map((c) => (c.id === action.id ? { ...c, ...patch, id: c.id } : c)),
        chats: {
          ...state.chats,
          [action.id]: [
            ...(state.chats[action.id] ?? []),
            { role: "ai", decision: result.decision, changed_fields: result.changed_fields, text: result.text },
          ],
        },
        highlight: result.changed_fields.length ? { id: action.id, fields: result.changed_fields } : state.highlight,
      };
    }
    case "revisionFailed":
      return { ...state, aiTypingFor: state.aiTypingFor === action.id ? null : state.aiTypingFor };
    case "clearHighlight":
      return { ...state, highlight: null };
    case "saveStarted":
      return {
        ...state,
        saving: [...state.saving, action.id],
        updating: action.regenerates ? [...state.updating, action.id] : state.updating,
      };
    case "characterSaved": {
      // a new character gets its id from the backend
      const { id, character, card } = action;
      const done = { ...state, saving: without(state.saving, id), updating: without(state.updating, id) };
      if (!state.cast.some((c) => c.id === id)) return done;
      const chat = state.chats[id];
      return {
        ...done,
        cast: state.cast.map((c) => (c.id === id ? character : c)),
        cards: { ...omit(state.cards, id), [character.id]: card },
        saved: { ...state.saved, [character.id]: character },
        chats: chat ? { ...omit(state.chats, id), [character.id]: chat } : state.chats,
      };
    }
    case "saveFailed":
      return { ...state, saving: without(state.saving, action.id), updating: without(state.updating, action.id) };
    case "characterLeft": {
      // leaving without saving: an edited character goes back to its saved version, a new one is dropped
      if (state.saving.includes(action.id)) return state;
      const saved = state.saved[action.id];
      if (saved) return { ...state, cast: state.cast.map((c) => (c.id === action.id ? saved : c)) };
      return {
        ...state,
        cast: state.cast.filter((c) => c.id !== action.id),
        cards: omit(state.cards, action.id),
        chats: omit(state.chats, action.id),
      };
    }
  }
}

const without = (ids: string[], id: string) => ids.filter((x) => x !== id);

function omit<T>(record: Record<string, T>, key: string): Record<string, T> {
  const { [key]: _removed, ...rest } = record;
  return rest;
}
