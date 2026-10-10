// The only data source of the frontend.
// getCast, generateCast and saveCharacter call the backend. Creating a blank character and the
// AI revision are still mocked. UI components never create characters or cards themselves, they call these functions.

import type {
  Character,
  CharacterCard,
  RevisionResult,
} from "@/features/characters/model/types";
import { getJson, postJson, putJson } from "@/shared/api/http";
import { delay, failIfConfigured } from "./mock-helpers";

export { ApiError } from "@/shared/api/errors";
export { configureMock } from "./mock-helpers";

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

/** Creates an empty character ("New Character") with its placeholder card. */
async function createBlankCharacter(): Promise<CharacterWithCard> {
  const character: Character = {
    id: newId(),
    name: "New",
    surname: "Character",
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

/** Chat "Ask AI to revise": the mock appends the request to Personality. */
async function reviseCharacter(
  character: Character,
  request: string,
  { signal }: CallOptions = {},
): Promise<RevisionResult> {
  await delay(1500, signal);
  failIfConfigured("chat");

  const note = request.trim();
  const addition = ` Revised: ${note.charAt(0).toUpperCase()}${note.slice(1).replace(/[.!]*$/, "")}.`;
  const revised: Character = {
    ...structuredClone(character),
    personality: (character.personality || "").replace(/ Revised: .*$/, "") + addition,
  };
  return {
    decision: "accept_with_adjustments",
    changed_fields: ["personality"],
    character: revised,
    text: `I reshaped ${revised.name}’s personality to reflect your note and kept the biography consistent.`,
  };
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
  reviseCharacter,
  saveCharacter,
};
