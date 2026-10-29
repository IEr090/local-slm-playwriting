// The Story Bible on the backend. Every call returns what the backend answers; long generations take a
// signal, because the backend stops generating when the request is cancelled.

import type {
  ActSummary,
  ActsRevision,
  DramaticFunction,
  HistoryMessage,
  Outline,
  OutlineRevision,
  Place,
  PlaceDraft,
  ScenePlan,
  SceneRevision,
  SceneText,
  StoryBible,
  TextRevision,
} from "@/features/story/model/types";
import { ApiError } from "@/shared/api/errors";
import { getJson, postJson, putJson } from "@/shared/api/http";

interface CallOptions {
  signal?: AbortSignal;
}

const act = (n: number) => `/api/story/acts/${n}`;

/** The saved Story Bible, or null if no play has been started yet (no cast generated). */
async function getStory(): Promise<StoryBible | null> {
  try {
    return await getJson<StoryBible>("/api/story");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

// ---------- outline ----------

const generateOutline = ({ signal }: CallOptions = {}) => postJson<StoryBible>("/api/story/outline/generate", undefined, { signal });

const saveOutline = (outline: Outline) => putJson<StoryBible>("/api/story/outline", outline);

const reviseOutline = (outline: Outline, message: string, { signal }: CallOptions = {}) =>
  postJson<OutlineRevision>("/api/story/outline/revise", { message, outline }, { signal });

const getOutlineChat = () => getJson<HistoryMessage[]>("/api/story/outline/revise");

// ---------- acts ----------

const generateActs = ({ signal }: CallOptions = {}) => postJson<StoryBible>("/api/story/acts/generate", undefined, { signal });

const saveAct = (number: number, summary: string, dramatic_function: DramaticFunction) =>
  putJson<StoryBible>(act(number), { summary, dramatic_function });

const reviseActs = (acts: ActSummary[], message: string, { signal }: CallOptions = {}) =>
  postJson<ActsRevision>("/api/story/acts/revise", { message, acts }, { signal });

const getActsChat = () => getJson<HistoryMessage[]>("/api/story/acts/revise");

const approveActs = () => postJson<StoryBible>("/api/story/acts/approve", undefined);

// ---------- places ----------

const getPlaces = () => getJson<Place[]>("/api/story/places");

const createPlace = (draft: PlaceDraft) => postJson<Place>("/api/story/places", draft);

// ---------- one act: structure and scene plans ----------

const generateStructure = (n: number, { signal }: CallOptions = {}) =>
  postJson<StoryBible>(`${act(n)}/structure/generate`, undefined, { signal });

/** Saves the scenes in their new order; only while the structure is a draft. */
const saveStructure = (n: number, scenes: ScenePlan[]) => putJson<StoryBible>(`${act(n)}/scenes`, scenes);

const reviseStructure = (n: number, scenes: ScenePlan[], message: string, { signal }: CallOptions = {}) =>
  postJson<SceneRevision>(`${act(n)}/structure/revise`, { message, scenes }, { signal });

const approveStructure = (n: number) => postJson<StoryBible>(`${act(n)}/structure/approve`, undefined);

const planScene = (n: number, no: number, { signal }: CallOptions = {}) =>
  postJson<StoryBible>(`${act(n)}/scenes/${no}/plan`, undefined, { signal });

/** Saves the plan of one scene; the backend makes it a draft again. */
const saveScene = (n: number, no: number, plan: ScenePlan) => putJson<StoryBible>(`${act(n)}/scenes/${no}`, plan);

const reviseScenes = (n: number, scenes: ScenePlan[], message: string, { signal }: CallOptions = {}) =>
  postJson<SceneRevision>(`${act(n)}/scenes/revise`, { message, scenes }, { signal });

const approveScene = (n: number, no: number) => postJson<StoryBible>(`${act(n)}/scenes/${no}/approve`, undefined);

const reopenScene = (n: number, no: number) => postJson<StoryBible>(`${act(n)}/scenes/${no}/reopen`, undefined);

// ---------- one act: text ----------

const generateText = (n: number, { signal }: CallOptions = {}) =>
  postJson<StoryBible>(`${act(n)}/text/generate`, undefined, { signal });

const saveText = (n: number, sceneTexts: SceneText[]) => putJson<StoryBible>(`${act(n)}/text`, sceneTexts);

const reviseText = (n: number, sceneTexts: SceneText[], message: string, { signal }: CallOptions = {}) =>
  postJson<TextRevision>(`${act(n)}/text/revise`, { message, scene_texts: sceneTexts }, { signal });

/** Approves the text and writes what it changed into the characters' histories (a model call per scene). */
const approveText = (n: number, { signal }: CallOptions = {}) =>
  postJson<StoryBible>(`${act(n)}/text/approve`, undefined, { signal });

/** One chat for the whole act page: structure, scene plans and text. */
const getActChat = (n: number) => getJson<HistoryMessage[]>(`${act(n)}/chat`);

export const api = {
  getStory,
  generateOutline,
  saveOutline,
  reviseOutline,
  getOutlineChat,
  generateActs,
  saveAct,
  reviseActs,
  getActsChat,
  approveActs,
  getPlaces,
  createPlace,
  generateStructure,
  saveStructure,
  reviseStructure,
  approveStructure,
  planScene,
  saveScene,
  reviseScenes,
  approveScene,
  reopenScene,
  generateText,
  saveText,
  reviseText,
  approveText,
  getActChat,
};
