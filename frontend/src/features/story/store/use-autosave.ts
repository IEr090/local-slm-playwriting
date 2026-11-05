// Hand edits and the Story Bible the backend answers with. Every edited part (see EditKey) is saved after a
// typing pause, one save per part at a time and in order. When the backend answers with the whole Story Bible,
// the parts the user has typed into since are kept from the local copy.

import { useCallback, useRef, type Dispatch, type RefObject } from "react";
import { api } from "@/features/story/api";
import { withLocalEdits, type EditKey } from "@/features/story/model/local-edits";
import { toPlan } from "@/features/story/model/scenes";
import type { StoryBible } from "@/features/story/model/types";
import type { Action, StoryState } from "./story-reducer";

/** Typing pause before a hand edit is saved. */
const SAVE_DELAY_MS = 600;

interface AutosaveOptions {
  /** Grows when a new cast replaces the play; answers for an older play are dropped. */
  epoch: RefObject<number>;
  stateRef: RefObject<StoryState>;
  dispatch: Dispatch<Action>;
  showError(error: unknown): void;
}

export function useAutosave({ epoch, stateRef, dispatch, showError }: AutosaveOptions) {
  // a part is unsaved while its edit version is ahead of its saved version
  const editVersion = useRef(new Map<EditKey, number>());
  const savedVersion = useRef(new Map<EditKey, number>());
  const timers = useRef(new Map<EditKey, ReturnType<typeof setTimeout>>());
  const chains = useRef(new Map<EditKey, Promise<void>>());

  const dirtyKeys = useCallback(
    () => [...editVersion.current].filter(([key, v]) => v > (savedVersion.current.get(key) ?? 0)).map(([key]) => key),
    [],
  );

  /** Takes the Story Bible the backend answered with, keeping what the user has typed since. */
  const receive = useCallback(
    (server: StoryBible, from: number) => {
      if (from !== epoch.current) return;
      const story = withLocalEdits(server, stateRef.current.story, dirtyKeys());
      stateRef.current = { ...stateRef.current, story };
      dispatch({ type: "storyReceived", story });
    },
    [epoch, stateRef, dispatch, dirtyKeys],
  );

  /** Saves one part now (after the saves of it before). Resolves when it is saved or failed. */
  const flush = useCallback(
    (key: EditKey): Promise<void> => {
      clearTimeout(timers.current.get(key));
      timers.current.delete(key);
      const from = epoch.current;
      const next = (chains.current.get(key) ?? Promise.resolve()).then(async () => {
        const version = editVersion.current.get(key) ?? 0;
        if (from !== epoch.current || version <= (savedVersion.current.get(key) ?? 0)) return;
        try {
          const server = await save(stateRef.current.story, key);
          savedVersion.current.set(key, Math.max(version, savedVersion.current.get(key) ?? 0));
          if (server) receive(server, from);
        } catch (error) {
          // the edit stays local; the next edit or step saves it again
          if (from === epoch.current) showError(error);
        }
      });
      chains.current.set(key, next);
      return next;
    },
    [epoch, stateRef, receive, showError],
  );

  /** Saves every edited part whose key starts with one of the prefixes. */
  const flushAll = useCallback(
    (...prefixes: string[]) =>
      Promise.all(dirtyKeys().filter((key) => prefixes.some((p) => key.startsWith(p))).map(flush)).then(() => undefined),
    [dirtyKeys, flush],
  );

  /** A part was edited locally: save it after a pause (0: at once). */
  const edited = useCallback(
    (key: EditKey, delay = SAVE_DELAY_MS) => {
      editVersion.current.set(key, (editVersion.current.get(key) ?? 0) + 1);
      clearTimeout(timers.current.get(key));
      timers.current.set(key, setTimeout(() => void flush(key), delay));
    },
    [flush],
  );

  /** A new play: pending saves of the old one are dropped. */
  const reset = useCallback(() => {
    timers.current.forEach((timer) => clearTimeout(timer));
    timers.current.clear();
    chains.current.clear();
    editVersion.current.clear();
    savedVersion.current.clear();
  }, []);

  return { receive, edited, flush, flushAll, reset };
}

/** Sends the local version of one edited part to the backend. */
async function save(story: StoryBible | null, key: EditKey): Promise<StoryBible | null> {
  if (!story) return null;
  if (key === "outline") return story.outline ? api.saveOutline(story.outline) : null;
  const [kind, value, sceneValue] = key.split(":");
  const act = story.acts.find((item) => item.number === Number(value));
  if (!act) return null;
  switch (kind) {
    case "act":
      return api.saveAct(act.number, act.summary, act.dramatic_function);
    case "scenes":
      return api.saveStructure(act.number, act.scenes.map(toPlan));
    case "scene": {
      const scene = act.scenes.find((item) => item.number === Number(sceneValue));
      return scene ? api.saveScene(act.number, scene.number, toPlan(scene)) : null;
    }
    default:
      return api.saveText(act.number, act.scene_texts);
  }
}
