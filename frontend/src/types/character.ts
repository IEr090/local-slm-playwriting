// Data model from README §5.1. `null` marks the empty state of a blank character.

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

/** Fields the card is generated from; a change here triggers a card update (README §4.5). */
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

export type RevisionDecision = "accept" | "accept_with_adjustments" | "reject";

export type ChatMessage =
  | { role: "user"; text: string }
  | {
      role: "ai";
      decision: RevisionDecision;
      changed_fields: (keyof Character)[];
      text: string;
    };

export interface RevisionResult {
  decision: RevisionDecision;
  changed_fields: (keyof Character)[];
  character: Character;
  text: string;
}

// ---------- errors ----------

export interface ApiErrorInfo {
  message: string;
  detail: string;
}

// ---------- display labels ----------

export const GENDER_LABEL: Record<Gender, string> = {
  female: "Female",
  male: "Male",
  other: "Other",
};

export const DECISION_LABEL: Record<RevisionDecision, string> = {
  accept: "ACCEPT",
  accept_with_adjustments: "ACCEPT WITH ADJUSTMENTS",
  reject: "REJECT",
};

export const FIELD_LABEL: Record<keyof Character, string> = {
  id: "Id",
  name: "Name",
  surname: "Surname",
  age: "Age",
  gender: "Gender",
  nationality_background: "Nationality / Background",
  appearance: "Appearance",
  occupation_social_role: "Occupation / Social role",
  personality: "Personality",
  biography: "Biography",
  dramatic_role: "Dramatic role",
  dramatic_role_description: "Dramatic role",
  goal: "Goal",
  motivation: "Motivation",
  fear_weakness: "Fear / Weakness",
  internal_conflict: "Internal conflict",
  character_arc: "Character arc",
  relationships: "Relationships",
};

/** "protagonist" → "Protagonist"; null → "Unassigned". */
export function roleLabel(role: DramaticRole | null): string {
  return role ? role.charAt(0).toUpperCase() + role.slice(1) : "Unassigned";
}
