// App state provider: one reducer + context. Data only ever comes from `api`; this store just holds it.

import { useCallback, useEffect, useLayoutEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { api, ApiError } from "@/api";
import { cardSources, cardSourcesChanged } from "@/lib/card-sources";
import type { ApiErrorInfo } from "@/types/character";
import { ActionsContext, StateContext, type CastActions } from "./cast-context";
import { initialState, reducer } from "./cast-reducer";

/** Several changed characters update one after another (prototype: 2600 + i·700 ms). */
const CARD_UPDATE_STAGGER_MS = 700;

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
    dispatch({ type: "generationStarted" });
    try {
      const { characters, cards } = await api.generateCast(stateRef.current.premise, { signal: controller.signal });
      if (controller.signal.aborted) return;
      // the generating screen plays the result phase and then opens the grid (finishGeneration)
      dispatch({ type: "castGenerated", characters, cards });
    } catch (error) {
      if (isAbort(error) || controller.signal.aborted) return;
      dispatch({ type: "setScreen", screen: "prompt" });
      dispatch({ type: "showError", error: toErrorInfo(error) });
    } finally {
      if (generation.current === controller) generation.current = null;
    }
  }, []);

  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const showToast = useCallback(() => {
    clearTimeout(toastTimer.current);
    dispatch({ type: "setToast", open: true });
    toastTimer.current = setTimeout(() => dispatch({ type: "setToast", open: false }), 3000);
  }, []);
  useEffect(() => () => clearTimeout(toastTimer.current), []);

  const addBlank = useCallback(async () => {
    const { character, card } = await api.createBlankCharacter();
    dispatch({ type: "characterAdded", character, card });
  }, []);

  const highlightTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(highlightTimer.current), []);

  const sendRevision = useCallback(async () => {
    const { draft, cast, selectedIndex, aiTypingFor } = stateRef.current;
    const text = draft.trim();
    const character = cast[selectedIndex];
    if (!text || !character || aiTypingFor) return;
    dispatch({ type: "revisionRequested", id: character.id, text });
    try {
      const result = await api.reviseCharacter(character, text);
      dispatch({ type: "revisionAnswered", id: character.id, result });
      clearTimeout(highlightTimer.current);
      highlightTimer.current = setTimeout(() => dispatch({ type: "clearHighlight" }), 2400);
    } catch (error) {
      dispatch({ type: "revisionFailed", id: character.id });
      dispatch({ type: "showError", error: toErrorInfo(error) });
    }
  }, []);

  /**
   * Auto-save on leaving the character (README §4.5): save everything edited, then regenerate only
   * the cards whose source fields changed — one after another (700 ms apart), each showing the
   * updating overlay. A failed update keeps the old card and shows the error banner.
   */
  const leaveToGrid = useCallback(() => {
    const { cast, cards, cardSnapshot, updating, dirty } = stateRef.current;
    dispatch({ type: "setScreen", screen: "grid" });

    const edited = cast.filter((c) => dirty.includes(c.id));
    if (edited.length) {
      dispatch({ type: "saved", ids: edited.map((c) => c.id) });
      edited.forEach((c) => void api.saveCharacter(c));
    }

    const changed = cast.filter((c) => !updating.includes(c.id) && cardSourcesChanged(c, cardSnapshot[c.id]));
    if (!changed.length) return;
    dispatch({ type: "cardsUpdating", ids: changed.map((c) => c.id) });
    changed.forEach((character, i) => {
      setTimeout(async () => {
        try {
          const card = await api.generateCard(character, cards[character.id]);
          dispatch({ type: "cardUpdated", id: character.id, card, sources: cardSources(character) });
        } catch (error) {
          dispatch({ type: "cardUpdateFailed", id: character.id });
          dispatch({ type: "showError", error: toErrorInfo(error) });
        }
      }, i * CARD_UPDATE_STAGGER_MS);
    });
  }, []);

  const actions = useMemo<CastActions>(
    () => ({
      setPremise: (premise) => dispatch({ type: "setPremise", premise }),
      goTo: (screen) => dispatch({ type: "setScreen", screen }),
      finishGeneration: () => dispatch({ type: "setScreen", screen: "grid" }),
      startGeneration,
      cancelGeneration,
      addBlank,
      openCharacter: (index) => dispatch({ type: "openCharacter", index }),
      dismissError: () => dispatch({ type: "dismissError" }),
      showToast,
      updateCharacter: (id, patch) => dispatch({ type: "updateCharacter", id, patch }),
      stepCharacter: (delta) => dispatch({ type: "stepCharacter", delta }),
      leaveToGrid,
      toggleChat: () => dispatch({ type: "toggleChat" }),
      setDraft: (draft) => dispatch({ type: "setDraft", draft }),
      sendRevision,
    }),
    [startGeneration, cancelGeneration, addBlank, showToast, sendRevision, leaveToGrid],
  );

  return (
    <ActionsContext.Provider value={actions}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}
