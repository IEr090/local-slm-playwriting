// State of the page of the whole play. Pure: no api calls, no timers, no navigation here.
// The play comes from the backend; the local copy also holds the lines the user has changed.

import { blockText, withBlockText } from "@/features/story/model/play-reader";
import type { Play, PlayScene } from "@/features/story/model/types";

export interface PlayReaderState {
  /** null until the play has been read from the backend. */
  play: Play | null;
  /** The words of every changed line as they were when the page opened, by lineKey. A line is changed while it differs. */
  originals: Record<string, string>;
}

export const initialReaderState: PlayReaderState = { play: null, originals: {} };

/** "act:scene": the unit that is saved. */
export const sceneKey = (act: number, scene: number) => `${act}:${scene}`;
/** "act:scene:index": one line of a scene. */
export const lineKey = (act: number, scene: number, index: number) => `${act}:${scene}:${index}`;

export type PlayReaderAction =
  | { type: "playLoaded"; play: Play }
  /** The words of one speech or stage direction were typed. */
  | { type: "lineEdited"; act: number; scene: number; index: number; value: string }
  /** The backend answered a save; the scenes in `keep` have been typed into since and stay as they are here. */
  | { type: "playReceived"; play: Play; keep: string[] };

export function readerReducer(state: PlayReaderState, action: PlayReaderAction): PlayReaderState {
  switch (action.type) {
    case "playLoaded":
      return { play: action.play, originals: {} };
    case "lineEdited": {
      if (!state.play) return state;
      const { act, scene, index, value } = action;
      const key = lineKey(act, scene, index);
      const before = findScene(state.play, act, scene)?.text;
      const current = before === undefined ? null : blockText(before, index);
      if (before === undefined || current === null) return state;
      const originals = { ...state.originals };
      // the words of the line before its first edit; a line typed back to them is no longer changed
      const original = originals[key] ?? current;
      const after = withBlockText(before, index, value);
      if (blockText(after, index) === original) delete originals[key];
      else originals[key] = original;
      return { play: withSceneText(state.play, act, scene, after), originals };
    }
    case "playReceived": {
      if (!state.play) return { ...state, play: action.play };
      let play = action.play;
      for (const key of action.keep) {
        const [act, scene] = key.split(":").map(Number);
        const mine = findScene(state.play, act, scene);
        if (mine) play = withSceneText(play, act, scene, mine.text);
      }
      return { ...state, play };
    }
  }
}

/** Is the line changed since the page opened? */
export const isChanged = (state: PlayReaderState, act: number, scene: number, index: number) =>
  lineKey(act, scene, index) in state.originals;

export function findScene(play: Play, act: number, scene: number): PlayScene | undefined {
  return play.acts.find((a) => a.number === act)?.scenes.find((s) => s.number === scene);
}

function withSceneText(play: Play, act: number, scene: number, text: string): Play {
  return {
    ...play,
    acts: play.acts.map((a) =>
      a.number === act ? { ...a, scenes: a.scenes.map((s) => (s.number === scene ? { ...s, text } : s)) } : a,
    ),
  };
}
