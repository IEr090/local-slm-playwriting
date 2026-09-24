// Contexts and hooks for reading the store and calling its actions.

import { createContext, useContext } from "react";
import type { Character } from "@/types/character";
import type { CastState, Screen } from "./cast-reducer";

export interface CastActions {
  setPremise(premise: string): void;
  goTo(screen: Screen): void;
  startGeneration(): Promise<void>;
  cancelGeneration(): void;
  addBlank(): Promise<void>;
  openCharacter(index: number): void;
  dismissError(): void;
  /** Shows the "Continue" toast for 3 s. */
  showToast(): void;
  /** Inline edit of one character (every field is always editable). */
  updateCharacter(id: string, patch: Partial<Omit<Character, "id">>): void;
  /** Previous / next character, wrapping around. */
  stepCharacter(delta: 1 | -1): void;
  /** "ALL CHARACTERS": back to the grid (auto-save hooks in here in block 8). */
  leaveToGrid(): void;
  toggleChat(): void;
  setDraft(draft: string): void;
  /** Sends the draft to the AI for the open character (Enter / send button). */
  sendRevision(): Promise<void>;
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
