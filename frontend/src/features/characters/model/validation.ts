// What a character needs before it can be saved, and whether it differs from its saved version.

import { FIELD_LABEL } from "./labels";
import type { Character } from "./types";

type ProfileField = Exclude<keyof Character, "id">;

const PROFILE_FIELDS = [
  "name", "surname", "age", "gender", "nationality_background", "appearance",
  "occupation_social_role", "personality", "biography", "dramatic_role", "dramatic_role_description",
  "goal", "motivation", "fear_weakness", "internal_conflict", "character_arc", "relationships",
] as const satisfies readonly ProfileField[];

/** Every field except surname and relationships has to be filled before saving. */
export const REQUIRED_FIELDS = PROFILE_FIELDS.filter(
  (f): f is Exclude<ProfileField, "surname" | "relationships"> => f !== "surname" && f !== "relationships",
);

export type RequiredField = (typeof REQUIRED_FIELDS)[number];

function isEmpty(value: Character[ProfileField]): boolean {
  if (value === null) return true;
  if (typeof value === "string") return !value.trim();
  if (Array.isArray(value)) return value.length === 0;
  return false;
}

/** Required fields that are still empty (whitespace counts as empty). */
export function missingFields(character: Character): RequiredField[] {
  return REQUIRED_FIELDS.filter((f) => isEmpty(character[f]));
}

/** "Name, Age, Dramatic role" for the banner. */
export function missingLabels(fields: readonly RequiredField[]): string {
  // the description shares the "Dramatic role" card but is checked on its own
  return fields.map((f) => (f === "dramatic_role_description" ? "Dramatic role description" : FIELD_LABEL[f])).join(", ");
}

/** True if nothing has been entered yet (a just added blank character). */
export function isEmptyProfile(character: Character): boolean {
  return PROFILE_FIELDS.every((f) => isEmpty(character[f]));
}

/** True if both versions have the same profile (the id is ignored). */
export function sameProfile(a: Character, b: Character): boolean {
  return PROFILE_FIELDS.every((f) => JSON.stringify(a[f]) === JSON.stringify(b[f]));
}
