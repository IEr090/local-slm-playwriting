// Contexts and hooks for reading the Character Creator store and calling its actions.

import { createContext, useContext } from "react";
import type { Character } from "@/features/characters/model/types";
import type { CastState } from "./cast-reducer";

export interface CastActions {
  setPremise(premise: string): void;
  /** GENERATE: opens /generating and asks the api for a cast. */
  startGeneration(): Promise<void>;
  /** CANCEL: aborts the request and goes back to the prompt. */
  cancelGeneration(): void;
  /** Called by the generation animation when the names have flowed out: opens /cast. */
  finishGeneration(): void;
  /** Creates a blank character and opens it. */
  addBlank(): Promise<void>;
  /** Opens /cast/:id. */
  openCharacter(id: string): void;
  /** The detail page shows a (new) character: clears the chat draft, closes the chat panel, reads its chat history. */
  characterOpened(id: string): void;
  /** Inline edit of one character (every field is always editable). */
  updateCharacter(id: string, patch: Partial<Omit<Character, "id">>): void;
  /** "ALL CHARACTERS": back to /cast; leaving a character drops its unsaved edits. */
  leaveToGrid(): void;
  /** CREATE / SAVE: back to /cast while the character is saved; on failure back to the character. */
  saveCharacter(id: string): Promise<void>;
  /** "← New premise": back to the prompt. */
  newPremise(): void;
  toggleChat(): void;
  setDraft(draft: string): void;
  /** Sends the draft to the AI for this character (Enter / send button). */
  sendRevision(id: string): Promise<void>;
}

export const StateContext = createContext<CastState | null>(null);
export const ActionsContext = createContext<CastActions | null>(null);

export function useCastState(): CastState {
  const value = useContext(StateContext);
  if (!value) throw new Error("useCastState must be used inside <CastProvider>");
  return value;
}

export function useCastActions(): CastActions {
  const value = useContext(ActionsContext);
  if (!value) throw new Error("useCastActions must be used inside <CastProvider>");
  return value;
}
