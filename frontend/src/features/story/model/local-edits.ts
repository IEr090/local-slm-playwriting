// The user keeps typing while a save or a generation is on its way. When the backend answers with the whole
// Story Bible, the parts the user has changed since then are kept from the local copy.

import { toPlan } from "./scenes";
import type { Act, StoryBible } from "./types";

/**
 * Keys of locally edited parts: "outline", "act:N" (summary and dramatic function), "scenes:N" (the list of
 * scenes of act N while its structure is a draft), "scene:N:S" (the plan of scene S of act N) and "text:N"
 * (the scene texts of act N).
 */
export type EditKey = "outline" | `act:${number}` | `scenes:${number}` | `scene:${number}:${number}` | `text:${number}`;

/** The story from the backend with the local version of every part in `dirty`. */
export function withLocalEdits(server: StoryBible, local: StoryBible | null, dirty: Iterable<EditKey>): StoryBible {
  if (!local) return server;
  let story = server;
  for (const key of dirty) {
    if (key === "outline") {
      if (story.outline && local.outline) story = { ...story, outline: local.outline };
      continue;
    }
    const [kind, value, sceneValue] = key.split(":");
    const number = Number(value);
    const mine = local.acts.find((act) => act.number === number);
    if (!mine || !story.acts.some((act) => act.number === number)) continue;
    const patch = (theirs: Act): Partial<Act> => {
      switch (kind) {
        case "act":
          return { summary: mine.summary, dramatic_function: mine.dramatic_function };
        case "scenes":
          return { scenes: mine.scenes };
        case "scene": {
          const scene = mine.scenes.find((item) => item.number === Number(sceneValue));
          return scene ? { scenes: theirs.scenes.map((item) => (item.number === scene.number ? { ...item, ...toPlan(scene) } : item)) } : {};
        }
        default:
          return { scene_texts: mine.scene_texts };
      }
    };
    story = { ...story, acts: story.acts.map((act) => (act.number === number ? { ...act, ...patch(act) } : act)) };
  }
  return story;
}
