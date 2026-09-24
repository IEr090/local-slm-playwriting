// Which edits require a new card (README §4.5).

import { CARD_SOURCE_FIELDS, type CardSourceField, type Character } from "@/types/character";

export type CardSources = Pick<Character, CardSourceField>;

/** The card source fields of a character, as the card was (or will be) generated from. */
export function cardSources(character: Character): CardSources {
  return Object.fromEntries(CARD_SOURCE_FIELDS.map((f) => [f, character[f]])) as CardSources;
}

/** True if any card source field differs from the snapshot taken at the last card generation. */
export function cardSourcesChanged(character: Character, snapshot: CardSources | undefined): boolean {
  if (!snapshot) return false;
  return CARD_SOURCE_FIELDS.some((f) => character[f] !== snapshot[f]);
}
