// App state shape and reducer. Pure — no api calls here.

import { DEFAULT_PREMISE } from "@/api/mock-data";
import { cardSources, type CardSources } from "@/lib/card-sources";
import type { ApiErrorInfo, Character, CharacterCard, ChatMessage, RevisionResult } from "@/types/character";

export type Screen = "prompt" | "generating" | "grid" | "detail";

export interface CastState {
  screen: Screen;
  premise: string;
  cast: Character[];
  cards: Record<string, CharacterCard>;
  selectedIndex: number;
  /** AI chat panel; closed whenever a character is opened from the grid (toggle in the header). */
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
  error: ApiErrorInfo | null;
  toast: boolean;
  /** The api has answered for the running generation; the animation then plays the result phase. */
  generationReady: boolean;
}

export const initialState: CastState = {
  screen: "prompt",
  premise: DEFAULT_PREMISE,
  cast: [],
  cards: {},
  selectedIndex: 0,
  chatOpen: false,
  chats: {},
  draft: "",
  aiTypingFor: null,
  highlight: null,
  updating: [],
  cardSnapshot: {},
  dirty: [],
  error: null,
  toast: false,
  generationReady: false,
};

export type Action =
  | { type: "setPremise"; premise: string }
  | { type: "setScreen"; screen: Screen }
  | { type: "generationStarted" }
  | { type: "castGenerated"; characters: Character[]; cards: Record<string, CharacterCard> }
  | { type: "characterAdded"; character: Character; card: CharacterCard }
  | { type: "openCharacter"; index: number }
  | { type: "showError"; error: ApiErrorInfo }
  | { type: "dismissError" }
  | { type: "setToast"; open: boolean }
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

export function reducer(state: CastState, action: Action): CastState {
  switch (action.type) {
    case "setPremise":
      return { ...state, premise: action.premise };
    case "setScreen":
      return { ...state, screen: action.screen, toast: false };
    case "generationStarted":
      return { ...state, screen: "generating", generationReady: false, error: null, toast: false };
    case "castGenerated":
      return {
        ...state,
        generationReady: true,
        cast: action.characters,
        cards: action.cards,
        chats: {},
        updating: [],
        cardSnapshot: Object.fromEntries(action.characters.map((c) => [c.id, cardSources(c)])),
        dirty: [],
        selectedIndex: 0,
        error: null,
      };
    case "characterAdded":
      return {
        ...state,
        cast: [...state.cast, action.character],
        cards: { ...state.cards, [action.character.id]: action.card },
        cardSnapshot: { ...state.cardSnapshot, [action.character.id]: cardSources(action.character) },
        selectedIndex: state.cast.length,
        draft: "",
        chatOpen: false,
        screen: "detail",
      };
    case "openCharacter":
      return { ...state, selectedIndex: action.index, draft: "", chatOpen: false, screen: "detail" };
    case "showError":
      return { ...state, error: action.error };
    case "dismissError":
      return { ...state, error: null };
    case "setToast":
      return { ...state, toast: action.open };
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
