// Data model. `null` marks the empty state of a blank character.

export type Gender = "female" | "male" | "other";
export type DramaticRole =
  | "protagonist" | "antagonist" | "confidant" | "catalyst"
  | "outsider" | "wildcard" | "mentor" | "foil";

export interface Relationship {
  character_id: string; // "" = row added, character not picked yet
  description: string;
}

export interface Character {
  id: string;
  name: string;
  surname: string;
  age: number | null;
  gender: Gender | null;
  nationality_background: string;
  appearance: string;
  occupation_social_role: string;
  personality: string;
  biography: string;
  dramatic_role: DramaticRole | null;
  dramatic_role_description: string;
  goal: string;
  motivation: string;
  fear_weakness: string;
  internal_conflict: string;
  character_arc: string;
  relationships: Relationship[];
}

export interface CharacterCard {
  role_label: DramaticRole | null;
  tagline: string; // occupation / social role, ~6 words
  traits: string[]; // 3 one-word traits (blank: ["Undefined"])
  wants: string; // one short sentence
  fears: string; // one short sentence
}

export const GENDERS: readonly Gender[] = ["female", "male", "other"];

export const DRAMATIC_ROLES: readonly DramaticRole[] = [
  "protagonist", "antagonist", "confidant", "catalyst",
  "outsider", "wildcard", "mentor", "foil",
];

/** Fields the card is generated from; a change here triggers a card update. */
export const CARD_SOURCE_FIELDS = [
  "dramatic_role",
  "occupation_social_role",
  "personality",
  "goal",
  "motivation",
  "fear_weakness",
] as const satisfies readonly (keyof Character)[];

export type CardSourceField = (typeof CARD_SOURCE_FIELDS)[number];

// ---------- chat ----------

export type ChatMessage =
  | { role: "user"; text: string }
  | {
      role: "ai";
      /** Fields the AI changed with this answer; empty for messages loaded from the history. */
      changed_fields: (keyof Character)[];
      text: string;
    };

/** One answer of the edit agent: its reply and the character as the agent sees it now (not saved). */
export interface RevisionResult {
  reply: string;
  character: Character;
}

/** A message of the chat history as the backend stores it. */
export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}
