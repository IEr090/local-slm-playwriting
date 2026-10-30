// Small Story Bibles for the tests of the model and the store.

import type { Act, Outline, Scene, StoryBible } from "./types";

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
    ...patch,
  };
}
