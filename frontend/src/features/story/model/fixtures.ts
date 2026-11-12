// Small Story Bibles for the tests of the model and the store.

import type { Act, Outline, Play, Scene, StoryBible } from "./types";

export const outline: Outline = {
  title: "The Salt House",
  premise: "Greed costs you the very thing it tries to keep.",
  genre: "drama",
  tone: "Chamber and cold, with a quiet irony.",
  time_and_world: "A North Sea island in the late 1920s.",
  central_conflict: "Margit wants the house; Elias wants the light.",
  synopsis: "The keeper's children arrive as the storm closes the crossing.",
};

export function scene(number: number, patch: Partial<Scene> = {}): Scene {
  return {
    number,
    place_id: "kitchen",
    place_notes: "",
    character_ids: ["agnes"],
    what_happens: `Scene ${number} happens.`,
    planned: false,
    status: "draft",
    plan_built_from: null,
    ...patch,
  };
}

export function act(number: number, patch: Partial<Act> = {}): Act {
  return {
    number,
    summary: `Act ${number} summary.`,
    dramatic_function: "development",
    status: "draft",
    scenes: [],
    scene_texts: [],
    scenes_built_from_summary: null,
    text_built_from_scenes: null,
    text: "",
    summary_changed: false,
    scenes_changed: false,
    outdated_plans: [],
    ...patch,
  };
}

export function story(patch: Partial<StoryBible> = {}): StoryBible {
  return {
    user_input: "A lighthouse inheritance.",
    outline,
    acts: [act(1), act(2), act(3)],
    acts_approved: false,
    places: [{ id: "kitchen", name: "The keeper's kitchen", description: "", significance: "" }],
    acts_built_from_outline: outline,
    outline_changed: false,
    play_complete: false,
    ...patch,
  };
}

/** A finished play: two acts with two and one scenes. */
export function play(patch: Partial<Play> = {}): Play {
  return {
    title: "The Salt House",
    genre: "Drama",
    premise: "Greed costs you the very thing it tries to keep.",
    time_and_world: "A North Sea island in 1928.",
    act_count: 2,
    cast: [{ character_id: "agnes", name: "AGNES BRANDT", description: "the keeper's housekeeper" }],
    acts: [
      {
        number: 1,
        scenes: [
          { number: 1, place_name: "The keeper's kitchen", place_notes: "", text: "(Late afternoon.)\n\nAGNES (at the stove): You came.\n\nELIAS: The last boat." },
          { number: 2, place_name: "The lamp room", place_notes: "", text: "AGNES: Cut it straight." },
        ],
      },
      { number: 2, scenes: [{ number: 1, place_name: "The jetty", place_notes: "", text: "(Morning.)" }] },
    ],
    ...patch,
  };
}
