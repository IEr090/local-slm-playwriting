// Display helpers shared by the grid, the detail header and the relationship picker.

import type { Character } from "@/types/character";

/** "Elena Hofbauer"; empty parts are skipped. */
export function fullName(character: Pick<Character, "name" | "surname">): string {
  return `${character.name || ""} ${character.surname || ""}`.trim();
}
