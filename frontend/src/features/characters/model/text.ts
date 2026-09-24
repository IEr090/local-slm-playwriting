// Display helpers shared by the grid, the detail header and the relationship picker.

import { GENDER_LABEL } from "./labels";
import type { Character } from "./types";

/** "Elena Hofbauer"; empty parts are skipped. */
export function fullName(character: Pick<Character, "name" | "surname">): string {
  return `${character.name || ""} ${character.surname || ""}`.trim();
}

/** Text before the first "." "," or ";" — used for the short header line. */
export function firstClause(text: string): string {
  return (text || "").split(/[.,;]/)[0].trim();
}

/** Header line: "occupation (first clause) · age · gender · background (first clause)", empty parts skipped. */
export function headLine(character: Character): string {
  return [
    firstClause(character.occupation_social_role),
    character.age === null ? "" : String(character.age),
    character.gender ? GENDER_LABEL[character.gender] : "",
    firstClause(character.nationality_background),
  ]
    .filter((part) => part.trim())
    .join(" · ");
}
