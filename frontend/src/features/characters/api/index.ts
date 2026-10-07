// The only data source of the frontend.
// generateCast calls the backend. Everything else is still mocked: fake delays instead of generation,
// text shortening instead of card generation, and nothing is saved anywhere.
// UI components never create characters or cards themselves, they call these functions.

import type {
  Character,
  CharacterCard,
  RevisionResult,
} from "@/features/characters/model/types";
import { postJson } from "@/shared/api/http";
import { delay, failIfConfigured, mockCard } from "./mock-helpers";

export { ApiError } from "@/shared/api/errors";
export { configureMock } from "./mock-helpers";

interface CallOptions {
  signal?: AbortSignal;
}

export interface GeneratedCast {
  characters: Character[];
  cards: Record<string, CharacterCard>;
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
async function createBlankCharacter(): Promise<{ character: Character; card: CharacterCard }> {
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

/** Regenerates the grid card from the profile. `previous` fills in anything the profile lacks. */
async function generateCard(
  character: Character,
  previous: CharacterCard = BLANK_CARD,
  { signal }: CallOptions = {},
): Promise<CharacterCard> {
  await delay(2600, signal);
  failIfConfigured("card");
  return mockCard(character, previous);
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

/** Auto-save target. Nothing is saved yet: the backend has no storage. */
async function saveCharacter(character: Character): Promise<void> {
  void character;
  await delay(150);
}

/** The saved cast (e.g. after a page reload). Always empty: the backend has no storage yet. */
async function getCast(): Promise<GeneratedCast> {
  return { characters: [], cards: {} };
}

export const api = {
  getCast,
  generateCast,
  createBlankCharacter,
  generateCard,
  reviseCharacter,
  saveCharacter,
};
