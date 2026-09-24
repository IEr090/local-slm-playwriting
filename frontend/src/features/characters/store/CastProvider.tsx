// Character Creator store provider: one reducer + async actions. Data only ever comes from `api`;
// navigation goes through the router; errors go to the shared error banner.

import { useCallback, useEffect, useLayoutEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { matchPath, useLocation, useNavigate } from "react-router";
import { api } from "@/features/characters/api";
import { cardSources, cardSourcesChanged } from "@/features/characters/model/card-sources";
import { paths } from "@/features/characters/paths";
import { isAbort } from "@/shared/api/errors";
import { useErrors } from "@/shared/errors/errors-context";
import { ActionsContext, StateContext, type CastActions } from "./cast-context";
import { initialState, reducer } from "./cast-reducer";

/** Several changed characters update one after another (prototype: 2600 + i·700 ms). */
const CARD_UPDATE_STAGGER_MS = 700;
/** How long changed fields glow after an AI revision. */
const HIGHLIGHT_MS = 2400;

export function CastProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const navigate = useNavigate();
  const location = useLocation();
  const { showError, dismissError } = useErrors();

  // fresh state for async actions without recreating them on every change
  const stateRef = useRef(state);
  useLayoutEffect(() => {
    stateRef.current = state;
  }, [state]);

  // On page load: read the saved cast, so /cast and /cast/:id work after a reload.
  useEffect(() => {
    void api.getCast().then(({ characters, cards }) => dispatch({ type: "castLoaded", characters, cards }));
  }, []);

  // ---------- generation ----------

  const generation = useRef<AbortController | null>(null);

  const startGeneration = useCallback(async () => {
    generation.current?.abort();
    const controller = new AbortController();
    generation.current = controller;
    dismissError();
    dispatch({ type: "generationStarted" });
    navigate(paths.generating);
    try {
      const { characters, cards } = await api.generateCast(stateRef.current.premise, { signal: controller.signal });
      if (controller.signal.aborted) return;
      // the generating page plays the result phase and then calls finishGeneration
      dispatch({ type: "castGenerated", characters, cards });
    } catch (error) {
      if (isAbort(error) || controller.signal.aborted) return;
      dispatch({ type: "generationEnded" });
      navigate(paths.prompt);
      showError(error);
    } finally {
      if (generation.current === controller) generation.current = null;
    }
  }, [navigate, showError, dismissError]);

  const cancelGeneration = useCallback(() => {
    generation.current?.abort();
    generation.current = null;
    dispatch({ type: "generationEnded" });
    navigate(paths.prompt);
  }, [navigate]);

  const finishGeneration = useCallback(() => {
    dispatch({ type: "generationEnded" });
    navigate(paths.cast);
  }, [navigate]);

  // ---------- characters ----------

  const addBlank = useCallback(async () => {
    const { character, card } = await api.createBlankCharacter();
    dispatch({ type: "characterAdded", character, card });
    navigate(paths.character(character.id));
  }, [navigate]);

  const characterOpened = useCallback(() => dispatch({ type: "characterOpened" }), []);

  // ---------- chat ----------

  const highlightTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(highlightTimer.current), []);

  const sendRevision = useCallback(
    async (id: string) => {
      const { draft, cast, aiTypingFor } = stateRef.current;
      const text = draft.trim();
      const character = cast.find((c) => c.id === id);
      if (!text || !character || aiTypingFor) return;
      dispatch({ type: "revisionRequested", id, text });
      try {
        const result = await api.reviseCharacter(character, text);
        dispatch({ type: "revisionAnswered", id, result });
        clearTimeout(highlightTimer.current);
        highlightTimer.current = setTimeout(() => dispatch({ type: "clearHighlight" }), HIGHLIGHT_MS);
      } catch (error) {
        dispatch({ type: "revisionFailed", id });
        showError(error);
      }
    },
    [showError],
  );

  // ---------- auto-save ----------

  /**
   * Auto-save on leaving a character (README §4.5): save everything edited, then regenerate only
   * the cards whose source fields changed — one after another (700 ms apart), each showing the
   * updating overlay. A failed update keeps the old card and shows the error banner.
   */
  const autoSave = useCallback(() => {
    const { cast, cards, cardSnapshot, updating, dirty } = stateRef.current;

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
          showError(error);
        }
      }, i * CARD_UPDATE_STAGGER_MS);
    });
  }, [showError]);

  // Leaving /cast/:id in any way (ALL CHARACTERS, browser back, another URL) saves the edits.
  const previousPath = useRef(location.pathname);
  useEffect(() => {
    const previous = previousPath.current;
    previousPath.current = location.pathname;
    if (previous !== location.pathname && matchPath(paths.characterPattern, previous)) autoSave();
  }, [location.pathname, autoSave]);

  // ---------- public actions ----------

  const actions = useMemo<CastActions>(
    () => ({
      setPremise: (premise) => dispatch({ type: "setPremise", premise }),
      startGeneration,
      cancelGeneration,
      finishGeneration,
      addBlank,
      openCharacter: (id) => navigate(paths.character(id)),
      characterOpened,
      updateCharacter: (id, patch) => dispatch({ type: "updateCharacter", id, patch }),
      leaveToGrid: () => navigate(paths.cast),
      newPremise: () => navigate(paths.prompt),
      toggleChat: () => dispatch({ type: "toggleChat" }),
      setDraft: (draft) => dispatch({ type: "setDraft", draft }),
      sendRevision,
    }),
    [startGeneration, cancelGeneration, finishGeneration, addBlank, characterOpened, sendRevision, navigate],
  );

  return (
    <ActionsContext.Provider value={actions}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}
