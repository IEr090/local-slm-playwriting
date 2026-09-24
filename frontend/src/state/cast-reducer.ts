// App state shape and reducer. Pure — no api calls here.

import { DEFAULT_PREMISE } from "@/api/mock-data";
import type { ApiErrorInfo, Character, CharacterCard, ChatMessage } from "@/types/character";

export type Screen = "prompt" | "generating" | "grid" | "detail";

export interface CastState {
  screen: Screen;
  premise: string;
  cast: Character[];
  cards: Record<string, CharacterCard>;
  selectedIndex: number;
  chatOpen: boolean;
  chats: Record<string, ChatMessage[]>;
  draft: string;
  aiTyping: boolean;
  /** Ids of characters whose card is being regenerated. */
  updating: string[];
  error: ApiErrorInfo | null;
  toast: boolean;
}

export const initialState: CastState = {
  screen: "prompt",
  premise: DEFAULT_PREMISE,
  cast: [],
  cards: {},
  selectedIndex: 0,
  chatOpen: true,
  chats: {},
  draft: "",
  aiTyping: false,
  updating: [],
  error: null,
  toast: false,
};

export type Action =
  | { type: "setPremise"; premise: string }
  | { type: "setScreen"; screen: Screen }
  | { type: "castGenerated"; characters: Character[]; cards: Record<string, CharacterCard> }
  | { type: "characterAdded"; character: Character; card: CharacterCard }
  | { type: "openCharacter"; index: number }
  | { type: "showError"; error: ApiErrorInfo }
  | { type: "dismissError" }
  | { type: "setToast"; open: boolean }
  | { type: "updateCharacter"; id: string; patch: Partial<Omit<Character, "id">> }
  | { type: "stepCharacter"; delta: 1 | -1 }
  | { type: "toggleChat" };

export function reducer(state: CastState, action: Action): CastState {
  switch (action.type) {
    case "setPremise":
      return { ...state, premise: action.premise };
    case "setScreen":
      return { ...state, screen: action.screen, toast: false };
    case "castGenerated":
      return {
        ...state,
        cast: action.characters,
        cards: action.cards,
        chats: {},
        updating: [],
        selectedIndex: 0,
        error: null,
      };
    case "characterAdded":
      return {
        ...state,
        cast: [...state.cast, action.character],
        cards: { ...state.cards, [action.character.id]: action.card },
        selectedIndex: state.cast.length,
        draft: "",
        screen: "detail",
      };
    case "openCharacter":
      return { ...state, selectedIndex: action.index, draft: "", screen: "detail" };
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
      };
    case "stepCharacter": {
      const n = state.cast.length;
      if (!n) return state;
      return { ...state, selectedIndex: (state.selectedIndex + action.delta + n) % n, draft: "" };
    }
    case "toggleChat":
      return { ...state, chatOpen: !state.chatOpen };
  }
}
