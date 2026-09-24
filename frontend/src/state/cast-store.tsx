// App state provider: one reducer + context. Data only ever comes from `api`; this store just holds it.

import { useCallback, useLayoutEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { api, ApiError } from "@/api";
import type { ApiErrorInfo } from "@/types/character";
import { ActionsContext, StateContext, type CastActions } from "./cast-context";
import { initialState, reducer } from "./cast-reducer";

function toErrorInfo(error: unknown): ApiErrorInfo {
  if (error instanceof ApiError) return { message: error.message, detail: error.detail };
  return { message: "Something went wrong.", detail: String(error) };
}

const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

export function CastProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const stateRef = useRef(state);
  useLayoutEffect(() => {
    stateRef.current = state;
  }, [state]);
  const generation = useRef<AbortController | null>(null);

  const cancelGeneration = useCallback(() => {
    generation.current?.abort();
    generation.current = null;
    dispatch({ type: "setScreen", screen: "prompt" });
  }, []);

  const startGeneration = useCallback(async () => {
    generation.current?.abort();
    const controller = new AbortController();
    generation.current = controller;
    dispatch({ type: "dismissError" });
    dispatch({ type: "setScreen", screen: "generating" });
    try {
      const { characters, cards } = await api.generateCast(stateRef.current.premise, { signal: controller.signal });
      if (controller.signal.aborted) return;
      dispatch({ type: "castGenerated", characters, cards });
      dispatch({ type: "setScreen", screen: "grid" });
    } catch (error) {
      if (isAbort(error) || controller.signal.aborted) return;
      dispatch({ type: "setScreen", screen: "prompt" });
      dispatch({ type: "showError", error: toErrorInfo(error) });
    } finally {
      if (generation.current === controller) generation.current = null;
    }
  }, []);

  const addBlank = useCallback(async () => {
    const { character, card } = await api.createBlankCharacter();
    dispatch({ type: "characterAdded", character, card });
  }, []);

  const actions = useMemo<CastActions>(
    () => ({
      setPremise: (premise) => dispatch({ type: "setPremise", premise }),
      goTo: (screen) => dispatch({ type: "setScreen", screen }),
      startGeneration,
      cancelGeneration,
      addBlank,
      openCharacter: (index) => dispatch({ type: "openCharacter", index }),
      dismissError: () => dispatch({ type: "dismissError" }),
    }),
    [startGeneration, cancelGeneration, addBlank],
  );

  return (
    <ActionsContext.Provider value={actions}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}
