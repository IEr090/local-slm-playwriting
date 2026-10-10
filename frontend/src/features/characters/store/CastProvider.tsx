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

/** How long changed fields glow after an AI revision. */
const HIGHLIGHT_MS = 2400;

export function CastProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const navigate = useNavigate();
  const location = useLocation();
  const { showError, dismissError } = useErrors();

  const stateRef = useRef(state);
  useLayoutEffect(() => {
    stateRef.current = state;
  }, [state]);

  // On page load: read the saved cast, so /cast and /cast/:id work after a reload.
  useEffect(() => {
    api
      .getCast()
      .then(({ characters, cards }) => dispatch({ type: "castLoaded", characters, cards }))
      .catch(showError);
  }, [showError]);

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

  // ---------- saving ----------

  const currentPath = useRef(location.pathname);

  /** Creates a new character or saves an edited one; the backend regenerates the card if needed. */
  const saveCharacter = useCallback(
    async (id: string) => {
      const { cast, saved, saving } = stateRef.current;
      const character = cast.find((c) => c.id === id);
      if (!character || saving.includes(id)) return;
      const previous = saved[id];
      const regenerates = !previous || cardSourcesChanged(character, cardSources(previous));

      dismissError();
      dispatch({ type: "saveStarted", id, regenerates });
      navigate(paths.cast);
      try {
        const result = previous ? await api.saveCharacter(character) : await api.createCharacter(character);
        dispatch({ type: "characterSaved", id, ...result });
      } catch (error) {
        dispatch({ type: "saveFailed", id });
        showError(error);
        // back to editing, unless the user has already opened something else
        if (matchPath(paths.cast, currentPath.current)) navigate(paths.character(id));
      }
    },
    [navigate, showError, dismissError],
  );

  // Leaving /cast/:id in any way except CREATE / SAVE drops the unsaved edits.
  useEffect(() => {
    const previous = currentPath.current;
    currentPath.current = location.pathname;
    if (previous === location.pathname) return;
    const left = matchPath(paths.characterPattern, previous);
    if (left?.params.id) dispatch({ type: "characterLeft", id: left.params.id });
  }, [location.pathname]);

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
      saveCharacter,
    }),
    [startGeneration, cancelGeneration, finishGeneration, addBlank, characterOpened, sendRevision, saveCharacter, navigate],
  );

  return (
    <ActionsContext.Provider value={actions}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}
