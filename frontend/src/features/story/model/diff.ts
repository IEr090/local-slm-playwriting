// What the agent changed: the data it returned compared with the data that was sent to it.

import { parseSceneText } from "./script";
import { toPlan } from "./scenes";
import { type ActSummary, type Outline, type OutlineField, type ScenePlan, type SceneText } from "./types";

const OUTLINE_FIELDS: readonly OutlineField[] = [
  "title", "premise", "genre", "tone", "time_and_world", "central_conflict", "synopsis",
];

export function changedOutlineFields(before: Outline, after: Outline): OutlineField[] {
  return OUTLINE_FIELDS.filter((field) => before[field] !== after[field]);
}

/** Numbers of the acts whose summary or dramatic function differ; acts are matched by number. */
export function changedActNumbers(before: ActSummary[], after: ActSummary[]): number[] {
  return after
    .filter((act) => {
      const old = before.find((item) => item.number === act.number);
      return old !== undefined && (old.summary !== act.summary || old.dramatic_function !== act.dramatic_function);
    })
    .map((act) => act.number);
}

export function samePlan(a: ScenePlan, b: ScenePlan): boolean {
  return JSON.stringify(toPlan(a)) === JSON.stringify(toPlan(b));
}

/** Indexes of the scenes that differ from the scene at the same place before, new scenes included. */
export function changedSceneIndexes(before: ScenePlan[], after: ScenePlan[]): number[] {
  return after.flatMap((plan, i) => (before[i] && samePlan(before[i], plan) ? [] : [i]));
}

/** Numbers of the scenes whose text differs. */
export function changedSceneTextNumbers(before: SceneText[], after: SceneText[]): number[] {
  return after
    .filter((item) => before.find((old) => old.scene_number === item.scene_number)?.text !== item.text)
    .map((item) => item.scene_number);
}

/** Indexes of the speeches and stage directions of a scene text that differ from the ones before. */
export function changedBlocks(before: string, after: string): number[] {
  const old = parseSceneText(before);
  return parseSceneText(after).flatMap((block, i) => (JSON.stringify(block) === JSON.stringify(old[i]) ? [] : [i]));
}
