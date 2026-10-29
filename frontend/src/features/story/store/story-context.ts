// Contexts and hooks for reading the Story Bible store and calling its actions.

import { createContext, useContext } from "react";
import type { Outline, Place, PlaceDraft, ScenePlan } from "@/features/story/model/types";
import type { ChatKind } from "@/features/story/model/targets";
import type { ChatKey, StoryState } from "./story-reducer";

/** Which agent a chat message goes to; the act agents need the act's number. */
export interface ChatContext {
  kind: ChatKind;
  act?: number;
}

export interface StoryActions {
  /** A page shows this chat: its history is read from the backend once. */
  chatOpened(key: ChatKey): void;
  /** The act page is shown: the places are read again. */
  actOpened(n: number): void;
  toggleChat(): void;
  setDraft(draft: string): void;
  /** Sends the draft to the agent of the page (Enter / send button). */
  sendMessage(context: ChatContext): Promise<void>;

  // ---------- outline ----------
  /** Writes the outline again after a failed generation. */
  generateOutline(): void;
  editOutline(patch: Partial<Outline>): void;
  /** APPROVE OUTLINE: saves the outline, shows the acts and drafts them; the outline is final from then on. */
  approveOutline(): void;

  // ---------- acts ----------
  /** Only before the acts are approved. */
  editActSummary(n: number, summary: string): void;
  /** APPROVE ACTS: the summaries are final and the first act is then staged on its own. */
  approveActs(): void;
  /** Generates the structure of an act again after a failed attempt. */
  stageAct(n: number): void;
  openAct(n: number): void;
  goToPlay(): void;

  // ---------- one act: structure ----------
  moveScene(n: number, index: number, step: -1 | 1): void;
  cutScene(n: number, index: number): void;
  addScene(n: number): void;
  editStructureScene(n: number, index: number, patch: Partial<ScenePlan>): void;
  approveStructure(n: number): void;

  // ---------- one act: scene plans ----------
  editScenePlan(n: number, scene: number, patch: Partial<ScenePlan>): void;
  approveScene(n: number, scene: number): void;
  reopenScene(n: number, scene: number): void;
  /** Creates a place by hand; resolves to null if it failed (the banner shows why). */
  createPlace(draft: PlaceDraft): Promise<Place | null>;
  /** EDIT SCENES / back to the text on the act page. */
  setEditingScenes(n: number, editing: boolean): void;

  // ---------- one act: text ----------
  /** WRITE ACT N: starts writing and goes to the play page, where the act's card shows the progress. */
  writeText(n: number): void;
  editSceneText(n: number, scene: number, block: number, value: string): void;
  approveText(n: number): void;
}

export const StateContext = createContext<StoryState | null>(null);
export const ActionsContext = createContext<StoryActions | null>(null);

export function useStoryState(): StoryState {
  const value = useContext(StateContext);
  if (!value) throw new Error("useStoryState must be used inside <StoryProvider>");
  return value;
}

export function useStoryActions(): StoryActions {
  const value = useContext(ActionsContext);
  if (!value) throw new Error("useStoryActions must be used inside <StoryProvider>");
  return value;
}
