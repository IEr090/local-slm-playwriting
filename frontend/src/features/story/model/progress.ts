// Where the play stands: which act can be built, what an act page shows, which scene is planned next.
// Pure functions of the Story Bible as the backend sends it.

import type { Act, StoryBible } from "./types";

/**
 * The act that is being built now: once the acts are approved, the first act whose text is not approved.
 * The backend lets an act be built only when the text of the act before it is approved.
 */
export function currentAct(story: StoryBible): Act | null {
  if (!story.acts_approved) return null;
  return story.acts.find((act) => act.status !== "text_approved") ?? null;
}

/** The act can be worked on: the acts are approved and the act before it has an approved text. */
export function isOpenAct(story: StoryBible, number: number): boolean {
  if (!story.acts_approved) return false;
  const previous = story.acts.find((act) => act.number === number - 1);
  return !previous || previous.status === "text_approved";
}

/** The act's page can be opened: it is open and its structure has been staged. */
export function canOpenAct(story: StoryBible, act: Act): boolean {
  return isOpenAct(story, act.number) && act.scenes.length > 0;
}

/** Long requests of one act that change what its page shows. */
export interface ActJobs {
  staging: boolean;
  writing: boolean;
  recording: boolean;
}

/**
 * What the act page shows:
 * staging   → the structure is being generated (or has not been yet);
 * structure → the scenes are a draft: reorder, cut, add, approve;
 * plans     → every scene gets its plan and is approved one by one;
 * writing   → the text is being written;
 * text      → the text is written and can be revised and approved;
 * recording → the approved text is written into the characters' histories;
 * done      → the text is approved.
 */
export type ActStage = "staging" | "structure" | "plans" | "writing" | "text" | "recording" | "done";

/** `editingScenes`: the user pressed EDIT SCENES while the text is shown. */
export function actStage(act: Act, jobs: ActJobs, editingScenes: boolean): ActStage {
  if (jobs.recording) return "recording";
  if (jobs.writing) return "writing";
  if (act.status === "draft") return act.scenes.length === 0 || jobs.staging ? "staging" : "structure";
  const hasText = act.scene_texts.length > 0;
  if (hasText && !editingScenes) {
    if (act.status === "text_approved") return "done";
    if (act.status === "scenes_approved") return "text";
  }
  return "plans";
}

/**
 * The scene whose plan is written next: the first scene without a plan, once the structure is approved and
 * the scene before it is approved (the backend refuses anything else). null when there is none to plan now.
 */
export function nextSceneToPlan(act: Act): number | null {
  if (act.status === "draft") return null;
  const index = act.scenes.findIndex((scene) => !scene.planned);
  if (index < 0) return null;
  const scene = act.scenes[index];
  if (scene.status === "approved") return null;
  if (index > 0 && act.scenes[index - 1].status !== "approved") return null;
  return scene.number;
}

export function allScenesApproved(act: Act): boolean {
  return act.scenes.length > 0 && act.scenes.every((scene) => scene.status === "approved");
}
