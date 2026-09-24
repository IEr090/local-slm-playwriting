// Who can be picked in a relationship row (README §4.4, "Relationships").

import type { Character, Relationship } from "@/features/characters/model/types";
import { fullName } from "./text";

/**
 * Characters offered for row `rowIndex`: never the character itself, never someone already linked
 * in another row, and — if `query` is set — only names where the first or last name (or the full name)
 * starts with the query.
 */
export function relationOptions(
  cast: readonly Character[],
  selfId: string,
  relationships: readonly Relationship[],
  rowIndex: number,
  query: string,
): Character[] {
  const q = query.trim().toLowerCase();
  const taken = new Set(relationships.filter((_, i) => i !== rowIndex).map((r) => r.character_id));
  return cast.filter((c) => {
    if (c.id === selfId || taken.has(c.id)) return false;
    if (!q) return true;
    const name = fullName(c).toLowerCase();
    return name.startsWith(q) || name.split(/\s+/).some((word) => word.startsWith(q));
  });
}
