// Character Creator state and reducer. Pure — no api calls, no navigation here.
// Which page is shown is decided by the router (URL), not by this state.

import { DEFAULT_PREMISE } from "@/features/characters/api/mock-data";
import { cardSources, type CardSources } from "@/features/characters/model/card-sources";
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
  /** Ids of characters whose card is being regenerated. */
  updating: string[];
  /** Card source fields as they were when each card was last generated (README §4.5). */
  cardSnapshot: Record<string, CardSources>;
  /** Ids of characters edited since the last auto-save. */
  dirty: string[];
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
  updating: [],
  cardSnapshot: {},
  dirty: [],
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
  | { type: "cardsUpdating"; ids: string[] }
  | { type: "cardUpdated"; id: string; card: CharacterCard; sources: CardSources }
  | { type: "cardUpdateFailed"; id: string }
  | { type: "saved"; ids: string[] };

/** A fresh cast (generated or loaded): new cards, snapshots, no chats. */
function withCast(state: CastState, characters: Character[], cards: Record<string, CharacterCard>): CastState {
  return {
    ...state,
    loaded: true,
    cast: characters,
    cards,
    chats: {},
    updating: [],
    cardSnapshot: Object.fromEntries(characters.map((c) => [c.id, cardSources(c)])),
    dirty: [],
  };
}

export function reducer(state: CastState, action: Action): CastState {
  switch (action.type) {
    case "castLoaded":
      // a generation started before the saved cast arrived wins
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
        cardSnapshot: { ...state.cardSnapshot, [action.character.id]: cardSources(action.character) },
      };
    case "characterOpened":
      return { ...state, draft: "", chatOpen: false };
    case "updateCharacter":
      return {
        ...state,
        cast: state.cast.map((c) => (c.id === action.id ? { ...c, ...action.patch } : c)),
        dirty: markDirty(state.dirty, action.id),
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
      // apply only the fields the AI changed, so edits made while it was typing survive
      const patch = Object.fromEntries(result.changed_fields.map((f) => [f, result.character[f]]));
      return {
        ...state,
        aiTypingFor: null,
        cast: state.cast.map((c) => (c.id === action.id ? { ...c, ...patch, id: c.id } : c)),
        dirty: markDirty(state.dirty, action.id),
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
    case "cardsUpdating":
      return { ...state, updating: [...new Set([...state.updating, ...action.ids])] };
    case "cardUpdated":
      // ignore late answers for a cast that has since been replaced
      if (!state.cast.some((c) => c.id === action.id)) return { ...state, updating: without(state.updating, action.id) };
      return {
        ...state,
        cards: { ...state.cards, [action.id]: action.card },
        cardSnapshot: { ...state.cardSnapshot, [action.id]: action.sources },
        updating: without(state.updating, action.id),
      };
    case "cardUpdateFailed":
      // keep the old card
      return { ...state, updating: without(state.updating, action.id) };
    case "saved":
      return { ...state, dirty: state.dirty.filter((id) => !action.ids.includes(id)) };
  }
}

const without = (ids: string[], id: string) => ids.filter((x) => x !== id);
const markDirty = (ids: string[], id: string) => (ids.includes(id) ? ids : [...ids, id]);
