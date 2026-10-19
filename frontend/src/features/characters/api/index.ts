// The only data source of the frontend: every call goes to the backend. A blank character only exists
// on the frontend until it is created. UI components never create characters or cards themselves, they call these functions.

import type {
  Character,
  CharacterCard,
  HistoryMessage,
  RevisionResult,
} from "@/features/characters/model/types";
import { getJson, postJson, putJson } from "@/shared/api/http";

export { ApiError } from "@/shared/api/errors";

interface CallOptions {
  signal?: AbortSignal;
}

export interface GeneratedCast {
  characters: Character[];
  cards: Record<string, CharacterCard>;
}

export interface CharacterWithCard {
  character: Character;
  card: CharacterCard;
}

const newId = () => crypto.randomUUID();

export const BLANK_CARD: CharacterCard = {
  role_label: null,
  tagline: "Role not set yet",
  traits: ["Undefined"],
  wants: "Not written yet",
  fears: "Not written yet",
};

/** Generates the whole cast for a premise on the backend. Returns all characters at once (no streaming). */
async function generateCast(premise: string, { signal }: CallOptions = {}): Promise<GeneratedCast> {
  return postJson<GeneratedCast>("/api/characters/generate", { premise }, { signal });
}

/** An empty character with its placeholder card, only on the frontend until `createCharacter`. */
async function createBlankCharacter(): Promise<CharacterWithCard> {
  const character: Character = {
    id: newId(),
    name: "",
    surname: "",
    age: null,
    gender: null,
    nationality_background: "",
    appearance: "",
    occupation_social_role: "",
    personality: "",
    biography: "",
    dramatic_role: null,
    dramatic_role_description: "",
    goal: "",
    motivation: "",
    fear_weakness: "",
    internal_conflict: "",
    character_arc: "",
    relationships: [],
  };
  return { character, card: structuredClone(BLANK_CARD) };
}

/**
 * Chat "Ask AI to revise": sends the message with the character as it is in the form. The agent answers,
 * and once the user has agreed to changes it returns the edited character; nothing is saved on the backend.
 */
async function reviseCharacter(
  character: Character,
  message: string,
  { signal }: CallOptions = {},
): Promise<RevisionResult> {
  const { id, ...draft } = character;
  return postJson<RevisionResult>(`/api/characters/${encodeURIComponent(id)}/revise`, { message, character: draft }, { signal });
}

/** The chat history with the AI about the character; empty if there is none (e.g. after a backend restart). */
async function getChatHistory(id: string): Promise<HistoryMessage[]> {
  return getJson<HistoryMessage[]>(`/api/characters/${encodeURIComponent(id)}/revise`);
}

/** Creates the character on the backend; it gets a new id and a generated card. */
async function createCharacter(character: Character): Promise<CharacterWithCard> {
  const { id, ...draft } = character;
  void id;
  return postJson<CharacterWithCard>("/api/characters", draft);
}

/**
 * Saves the edited character. The backend regenerates its card only if the card source fields changed,
 * so the answer may take as long as a card generation.
 */
async function saveCharacter(character: Character): Promise<CharacterWithCard> {
  const { id, ...draft } = character;
  return putJson<CharacterWithCard>(`/api/characters/${encodeURIComponent(id)}`, draft);
}

/** The saved cast (e.g. after a page reload). */
async function getCast(): Promise<GeneratedCast> {
  return getJson<GeneratedCast>("/api/characters");
}

export const api = {
  getCast,
  generateCast,
  createBlankCharacter,
  createCharacter,
  reviseCharacter,
  getChatHistory,
  saveCharacter,
};
