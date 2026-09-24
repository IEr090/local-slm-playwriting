import { describe, expect, it } from "vitest";
import type { Character } from "@/features/characters/model/types";
import { firstClause, fullName, headLine } from "./text";

describe("fullName", () => {
  it("joins name and surname and trims empty parts", () => {
    expect(fullName({ name: "Elena", surname: "Hofbauer" })).toBe("Elena Hofbauer");
    expect(fullName({ name: "Elena", surname: "" })).toBe("Elena");
    expect(fullName({ name: "", surname: "" })).toBe("");
  });
});

describe("firstClause", () => {
  it("cuts at the first . , or ;", () => {
    expect(firstClause("Austrian, from Graz. Grew up")).toBe("Austrian");
    expect(firstClause("Archivist of the theatre; Viktor’s confidante")).toBe("Archivist of the theatre");
    expect(firstClause("")).toBe("");
  });
});

describe("headLine", () => {
  const base = {
    occupation_social_role: "Artistic director and co-founder of a small theatre, in Ottakring.",
    age: 52,
    gender: "female",
    nationality_background: "Austrian, from Graz.",
  } as Character;

  it("joins occupation · age · gender · background", () => {
    expect(headLine(base)).toBe("Artistic director and co-founder of a small theatre · 52 · Female · Austrian");
  });

  it("skips empty parts (blank character)", () => {
    expect(headLine({ ...base, occupation_social_role: "", age: null, gender: null })).toBe("Austrian");
    expect(headLine({ ...base, occupation_social_role: "", age: null, gender: null, nationality_background: "" })).toBe("");
  });
});
