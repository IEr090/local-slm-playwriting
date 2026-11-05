// What a chat message changes on each page. Every chat sends the data of its page to its agent and gets the
// data back as the agent sees it now; a reviser turns that answer into the edits to put into the fields, the
// labels for the chat ("Updated: …") and the parts that glow. Pure apart from the one api call.

import { api } from "@/features/story/api";
import { changedActNumbers, changedBlocks, changedOutlineFields, changedSceneIndexes, changedSceneTextNumbers } from "@/features/story/model/diff";
import { actName, OUTLINE_FIELD_LABEL } from "@/features/story/model/labels";
import type { EditKey } from "@/features/story/model/local-edits";
import { toPlan, toScenes } from "@/features/story/model/scenes";
import type { Act, Outline, Place, StoryBible } from "@/features/story/model/types";
import type { ChatKind } from "./story-context";
import type { Action, ChatKey } from "./story-reducer";

/** One change to put into the fields and save. */
export interface RevisionEdit {
  action: Action;
  key: EditKey;
}

export interface Revision {
  reply: string;
  edits: RevisionEdit[];
  /** Labels of what changed, shown above the answer. */
  updated: string[];
  /** Parts that glow: "outline:<field>", "act:N", "scene:N:S", "block:N:S:I". */
  highlight: string[];
  /** All places of the play, when the agent may have proposed new ones. */
  places?: Place[];
}

/** Sends the message with the page's data; null when the page has nothing to revise. */
type Reviser = (story: StoryBible, message: string, act: Act | undefined) => Promise<Revision | null>;

export function chatKey(kind: ChatKind, act?: number): ChatKey {
  return kind === "outline" || kind === "acts" ? kind : `act:${act ?? 0}`;
}

const reviseOutline: Reviser = async (story, message) => {
  const sent = story.outline;
  if (!sent) return null;
  const result = await api.reviseOutline(sent, message);
  const fields = changedOutlineFields(sent, result.outline);
  const patch = Object.fromEntries(fields.map((f) => [f, result.outline[f]])) as Partial<Outline>;
  return {
    reply: result.reply,
    edits: fields.length ? [{ action: { type: "outlineEdited", patch }, key: "outline" }] : [],
    updated: fields.map((f) => OUTLINE_FIELD_LABEL[f]),
    highlight: fields.map((f) => `outline:${f}`),
  };
};

const reviseActs: Reviser = async (story, message) => {
  const sent = story.acts.map(({ number, summary, dramatic_function }) => ({ number, summary, dramatic_function }));
  const result = await api.reviseActs(sent, message);
  const numbers = changedActNumbers(sent, result.acts);
  const edits: RevisionEdit[] = [];
  const updated: string[] = [];
  for (const number of numbers) {
    const before = sent.find((item) => item.number === number)!;
    const after = result.acts.find((item) => item.number === number)!;
    edits.push({ action: { type: "actEdited", number, summary: after.summary, dramatic_function: after.dramatic_function }, key: `act:${number}` });
    updated.push(before.dramatic_function !== after.dramatic_function ? `${actName(number)} · dramatic function` : actName(number));
  }
  return { reply: result.reply, edits, updated, highlight: numbers.map((number) => `act:${number}`) };
};

/** The list of scenes while the structure is a draft: the agent may reorder, cut and add scenes. */
const reviseStructure: Reviser = async (_story, message, act) => {
  if (!act) return null;
  const n = act.number;
  const sent = act.scenes.map(toPlan);
  const result = await api.reviseStructure(n, sent, message);
  const changed = changedSceneIndexes(sent, result.scenes);
  const listChanged = changed.length > 0 || result.scenes.length !== sent.length;
  const cut = sent.length - result.scenes.length;
  return {
    reply: result.reply,
    edits: listChanged ? [{ action: { type: "scenesEdited", number: n, scenes: toScenes(result.scenes) }, key: `scenes:${n}` }] : [],
    updated: [...changed.map((i) => `Scene ${i + 1}`), ...(listChanged && cut > 0 ? [`${cut} scene(s) cut`] : [])],
    highlight: changed.map((i) => `scene:${n}:${i + 1}`),
    places: result.places,
  };
};

/** The plans of the scenes once the structure is approved: the agent changes scenes, never the list. */
const reviseScenes: Reviser = async (_story, message, act) => {
  if (!act) return null;
  const n = act.number;
  const sent = act.scenes.map(toPlan);
  const result = await api.reviseScenes(n, sent, message);
  const changed = changedSceneIndexes(sent, result.scenes).filter((i) => act.scenes[i]);
  return {
    reply: result.reply,
    edits: changed.map((i) => ({
      action: { type: "sceneEdited", number: n, scene: i + 1, patch: toPlan(result.scenes[i]) },
      key: `scene:${n}:${i + 1}`,
    })),
    updated: changed.map((i) => `Scene ${i + 1}`),
    highlight: changed.map((i) => `scene:${n}:${i + 1}`),
    places: result.places,
  };
};

const reviseText: Reviser = async (_story, message, act) => {
  if (!act) return null;
  const n = act.number;
  const sent = act.scene_texts;
  const result = await api.reviseText(n, sent, message);
  const numbers = changedSceneTextNumbers(sent, result.scene_texts);
  const textOf = (texts: typeof sent, scene: number) => texts.find((item) => item.scene_number === scene)!.text;
  const sceneTexts = sent.map((item) =>
    numbers.includes(item.scene_number) ? { ...item, text: textOf(result.scene_texts, item.scene_number) } : item,
  );
  return {
    reply: result.reply,
    edits: numbers.length ? [{ action: { type: "sceneTextsEdited", number: n, sceneTexts }, key: `text:${n}` }] : [],
    updated: numbers.map((scene) => `Scene ${scene} · text`),
    highlight: numbers.flatMap((scene) =>
      changedBlocks(textOf(sent, scene), textOf(result.scene_texts, scene)).map((i) => `block:${n}:${scene}:${i}`),
    ),
  };
};

export const revisers: Record<ChatKind, Reviser> = {
  outline: reviseOutline,
  acts: reviseActs,
  structure: reviseStructure,
  scenes: reviseScenes,
  text: reviseText,
};
