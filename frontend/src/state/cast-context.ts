// Contexts and hooks for reading the store and calling its actions.

import { createContext, useContext } from "react";
import type { CastState, Screen } from "./cast-reducer";

export interface CastActions {
  setPremise(premise: string): void;
  goTo(screen: Screen): void;
  startGeneration(): Promise<void>;
  cancelGeneration(): void;
  addBlank(): Promise<void>;
  openCharacter(index: number): void;
  dismissError(): void;
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
