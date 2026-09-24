import { describe, expect, it } from "vitest";
import type { Character, Relationship } from "@/types/character";
import { relationOptions } from "./relationships";

const ch = (id: string, name: string, surname: string) => ({ id, name, surname }) as Character;
const cast = [
  ch("elena", "Elena", "Hofbauer"),
  ch("mark", "Mark", "Seidl"),
  ch("anna", "Anna", "Lindner"),
  ch("viktor", "Viktor", "Brandstätter"),
  ch("sofia", "Sofia", "Brandstätter"),
];
const names = (list: Character[]) => list.map((c) => c.id);

describe("relationOptions", () => {
  it("never offers the character itself", () => {
    expect(names(relationOptions(cast, "elena", [], 0, ""))).toEqual(["mark", "anna", "viktor", "sofia"]);
  });

  it("hides characters already linked in other rows, but keeps the one in the row being edited", () => {
    const rels: Relationship[] = [
      { character_id: "mark", description: "" },
      { character_id: "anna", description: "" },
    ];
    expect(names(relationOptions(cast, "elena", rels, 1, ""))).toEqual(["anna", "viktor", "sofia"]);
  });

  it("filters by the start of the first or last name, case-insensitive", () => {
    expect(names(relationOptions(cast, "elena", [], 0, "br"))).toEqual(["viktor", "sofia"]);
    expect(names(relationOptions(cast, "elena", [], 0, "SO"))).toEqual(["sofia"]);
    expect(names(relationOptions(cast, "elena", [], 0, "sofia br"))).toEqual(["sofia"]);
  });

  it("does not match the middle of a name", () => {
    expect(names(relationOptions(cast, "elena", [], 0, "ark"))).toEqual([]);
  });
});
