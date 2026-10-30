// Data model of the Story Bible, as the backend sends it (backend/src/anton/domain/models/story.py).

export type Genre = "comedy" | "drama" | "tragedy" | "tragicomedy" | "farce";
export type DramaticFunction = "setup" | "development" | "climax" | "resolution";
export type ActStatus = "draft" | "structure_approved" | "scenes_approved" | "text_approved";
export type SceneStatus = "draft" | "approved";

export const GENRES: readonly Genre[] = ["comedy", "drama", "tragedy", "tragicomedy", "farce"];

export interface Outline {
  title: string;
  premise: string;
  genre: Genre;
  tone: string;
  time_and_world: string;
  central_conflict: string;
  synopsis: string;
}

export type OutlineField = keyof Outline;

export interface PlaceDraft {
  name: string;
  description: string;
  significance: string;
}

export interface Place extends PlaceDraft {
  id: string;
}

/** What a scene is built from; this is what the frontend sends when it saves a scene. */
export interface ScenePlan {
  /** "" while no place is chosen. */
  place_id: string;
  place_notes: string;
  character_ids: string[];
  what_happens: string;
}

export interface Scene extends ScenePlan {
  number: number;
  /** The detailed plan has been written (POST .../plan). */
  planned: boolean;
  status: SceneStatus;
  plan_built_from: ScenePlan[] | null;
}

export interface SceneText {
  scene_number: number;
  text: string;
}

export interface ActSummary {
  number: number;
  summary: string;
  dramatic_function: DramaticFunction;
}

export interface Act extends ActSummary {
  status: ActStatus;
  scenes: Scene[];
  scene_texts: SceneText[];
  scenes_built_from_summary: string | null;
  text_built_from_scenes: ScenePlan[] | null;
  /** All scene texts joined; computed by the backend. */
  text: string;
  /** Warning flags, computed by the backend. */
  summary_changed: boolean;
  scenes_changed: boolean;
  outdated_plans: number[];
}

export interface StoryBible {
  user_input: string;
  outline: Outline | null;
  acts: Act[];
  acts_approved: boolean;
  places: Place[];
  acts_built_from_outline: Outline | null;
  outline_changed: boolean;
}

/** A message of a chat history as the backend stores it. */
export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface OutlineRevision {
  reply: string;
  outline: Outline;
}

export interface ActsRevision {
  reply: string;
  acts: ActSummary[];
}

/** Answer of the act agent about the structure or the scene plans; `places` are all places, new ones included. */
export interface SceneRevision {
  reply: string;
  scenes: ScenePlan[];
  places: Place[];
}

export interface TextRevision {
  reply: string;
  scene_texts: SceneText[];
}
