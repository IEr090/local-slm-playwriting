// The one and only data source of the frontend (README §2).
// Everything here is mocked: fake delays instead of generation, text shortening instead of card generation.
// UI components never create characters or cards themselves — they call these functions.

import type {
  Character,
  CharacterCard,
  RevisionResult,
} from "@/features/characters/model/types";
import { SEED_CAST } from "./mock-data";
import { delay, failIfConfigured, mockCard, mockConfig } from "./mock-helpers";

export { ApiError } from "@/shared/api/errors";
export { configureMock } from "./mock-helpers";

interface CallOptions {
  signal?: AbortSignal;
}

export interface GeneratedCast {
  characters: Character[];
  cards: Record<string, CharacterCard>;
}

/** In-memory "database" of the current play. */
const store = new Map<string, Character>();

const newId = () => crypto.randomUUID();
const clone = <T>(value: T): T => structuredClone(value);

export const BLANK_CARD: CharacterCard = {
  role_label: null,
  tagline: "Role not set yet",
  traits: ["Undefined"],
  wants: "Not written yet",
  fears: "Not written yet",
};

/**
 * Generates the whole cast for a premise. Returns all characters at once (no streaming).
 * The mock ignores the premise and always returns the six characters from the prototype.
 */
async function generateCast(premise: string, { signal }: CallOptions = {}): Promise<GeneratedCast> {
  void premise;
  await delay(mockConfig.generateDelayMs, signal);
  failIfConfigured("generate");

  const ids = SEED_CAST.map(() => newId());
  const idByName = new Map(SEED_CAST.map((seed, i) => [seed.profile.name, ids[i]]));

  const characters: Character[] = SEED_CAST.map((seed, i) => ({
    ...clone(seed.profile),
    id: ids[i],
    relationships: seed.relationships.map((rel) => ({
      character_id: idByName.get(rel.who) ?? "",
      description: rel.description,
    })),
  }));
  const cards = Object.fromEntries(characters.map((c, i) => [c.id, clone(SEED_CAST[i].card)]));

  store.clear();
  characters.forEach((c) => store.set(c.id, clone(c)));
  return { characters, cards };
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
  store.set(character.id, clone(character));
  return { character, card: clone(BLANK_CARD) };
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
    ...clone(character),
    personality: (character.personality || "").replace(/ Revised: .*$/, "") + addition,
  };
  return {
    decision: "accept_with_adjustments",
    changed_fields: ["personality"],
    character: revised,
    text: `I reshaped ${revised.name}’s personality to reflect your note and kept the biography consistent. In the real app the Character Agent on the local SLM writes this change.`,
  };
}

/** Auto-save target: stores the character in memory. */
async function saveCharacter(character: Character): Promise<void> {
  await delay(150);
  store.set(character.id, clone(character));
}

export const api = {
  generateCast,
  createBlankCharacter,
  generateCard,
  reviseCharacter,
  saveCharacter,
};

/** Test-only view of the in-memory store. */
export const __store = store;
