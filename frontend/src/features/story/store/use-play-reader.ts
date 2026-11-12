// The whole play on its page: read from the backend, edited line by line, saved scene by scene. A scene is
// saved after a typing pause, when its line loses focus, when the text is locked again and when the page is
// left; the saves of one scene go one after another. While the user types on, the answer of a save does not
// overwrite the scenes typed into since.

import { useCallback, useEffect, useLayoutEffect, useReducer, useRef } from "react";
import { useNavigate } from "react-router";
import { api } from "@/features/story/api";
import { paths } from "@/features/story/paths";
import { ApiError } from "@/shared/api/errors";
import { useErrors } from "@/shared/errors/errors-context";
import { findScene, initialReaderState, readerReducer, sceneKey } from "./play-reader-reducer";

/** Typing pause before a scene is saved. */
const SAVE_DELAY_MS = 600;

export function usePlayReader() {
  const [state, dispatch] = useReducer(readerReducer, initialReaderState);
  const navigate = useNavigate();
  const { showError } = useErrors();

  const stateRef = useRef(state);
  useLayoutEffect(() => {
    stateRef.current = state;
  }, [state]);

  // a scene is unsaved while its edit version is ahead of its saved version
  const editVersion = useRef(new Map<string, number>());
  const savedVersion = useRef(new Map<string, number>());
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  const chains = useRef(new Map<string, Promise<void>>());

  // the play is read once; it is not complete yet → back to the acts
  useEffect(() => {
    let cancelled = false;
    api
      .getPlay()
      .then((play) => {
        if (!cancelled) dispatch({ type: "playLoaded", play });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 409) navigate(paths.play, { replace: true });
        else showError(error);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate, showError]);

  const dirtyKeys = useCallback(
    () => [...editVersion.current].filter(([key, v]) => v > (savedVersion.current.get(key) ?? 0)).map(([key]) => key),
    [],
  );

  /** Saves one scene now, after the saves of it before. Resolves when it is saved or failed. */
  const flush = useCallback(
    (key: string): Promise<void> => {
      clearTimeout(timers.current.get(key));
      timers.current.delete(key);
      const next = (chains.current.get(key) ?? Promise.resolve()).then(async () => {
        const version = editVersion.current.get(key) ?? 0;
        if (version <= (savedVersion.current.get(key) ?? 0)) return;
        const [act, scene] = key.split(":").map(Number);
        const play = stateRef.current.play;
        const text = play ? (findScene(play, act, scene)?.text ?? "") : "";
        if (!text.trim()) {
          // never send an empty text: the last saved text stays on the backend
          savedVersion.current.set(key, version);
          showError(new ApiError("A scene cannot be empty.", "The last saved text of the scene is kept."));
          return;
        }
        try {
          const saved = await api.savePlayScene(act, scene, text);
          savedVersion.current.set(key, Math.max(version, savedVersion.current.get(key) ?? 0));
          dispatch({ type: "playReceived", play: saved, keep: dirtyKeys() });
        } catch (error) {
          // the edit stays in the field; the next edit or step saves it again
          showError(error);
        }
      });
      chains.current.set(key, next);
      return next;
    },
    [dirtyKeys, showError],
  );

  const flushAll = useCallback(() => Promise.all(dirtyKeys().map(flush)).then(() => undefined), [dirtyKeys, flush]);

  /** The words of a speech or a stage direction were typed. */
  const editLine = useCallback(
    (act: number, scene: number, index: number, value: string) => {
      dispatch({ type: "lineEdited", act, scene, index, value });
      const key = sceneKey(act, scene);
      editVersion.current.set(key, (editVersion.current.get(key) ?? 0) + 1);
      clearTimeout(timers.current.get(key));
      timers.current.set(key, setTimeout(() => void flush(key), SAVE_DELAY_MS));
    },
    [flush],
  );

  const flushScene = useCallback((act: number, scene: number) => void flush(sceneKey(act, scene)), [flush]);

  // leaving the page saves what is still waiting for its pause
  useEffect(
    () => () => {
      void flushAll();
    },
    [flushAll],
  );

  return { state, editLine, flushScene, flushAll };
}
