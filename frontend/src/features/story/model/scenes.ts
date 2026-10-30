// Editing the list of scenes of an act. Pure: every function returns a new list.

import type { Scene, ScenePlan } from "./types";

/** The plan fields of a scene: what the backend takes when a scene is saved. */
export function toPlan(scene: ScenePlan): ScenePlan {
  return {
    place_id: scene.place_id,
    place_notes: scene.place_notes,
    character_ids: scene.character_ids,
    what_happens: scene.what_happens,
  };
}

/** New draft scenes in the order of the list, numbered from one, as the backend stores an edited structure. */
export function toScenes(plans: ScenePlan[]): Scene[] {
  return plans.map((plan, i) => ({
    ...toPlan(plan),
    number: i + 1,
    planned: false,
    status: "draft",
    plan_built_from: null,
  }));
}

/** Swaps scene `index` with its neighbour above (-1) or below (+1). */
export function moveScene(scenes: Scene[], index: number, step: -1 | 1): Scene[] {
  const target = index + step;
  if (target < 0 || target >= scenes.length) return scenes;
  const plans = scenes.map(toPlan);
  [plans[index], plans[target]] = [plans[target], plans[index]];
  return toScenes(plans);
}

export function cutScene(scenes: Scene[], index: number): Scene[] {
  return toScenes(scenes.filter((_, i) => i !== index).map(toPlan));
}

export const BLANK_PLAN: ScenePlan = { place_id: "", place_notes: "", character_ids: [], what_happens: "" };

export function addBlankScene(scenes: Scene[]): Scene[] {
  return toScenes([...scenes.map(toPlan), BLANK_PLAN]);
}

// ---------- which scene cards have their editor open (by index) ----------

/** The open editors after a move: the moved scene and its neighbour swap places. */
export function openAfterMove(open: ReadonlySet<number>, index: number, step: -1 | 1, count: number): Set<number> {
  const target = index + step;
  if (target < 0 || target >= count) return new Set(open);
  return new Set(
    [...open].map((i) => {
      if (i === index) return target;
      if (i === target) return index;
      return i;
    }),
  );
}

/** The open editors after a cut: the cut scene's editor goes, the ones below move up. */
export function openAfterCut(open: ReadonlySet<number>, index: number): Set<number> {
  return new Set([...open].filter((i) => i !== index).map((i) => (i > index ? i - 1 : i)));
}

/** A structure scene without a place or without what happens: its editor stays open. */
export function isIncomplete(plan: ScenePlan): boolean {
  return !plan.place_id || !plan.what_happens.trim();
}
