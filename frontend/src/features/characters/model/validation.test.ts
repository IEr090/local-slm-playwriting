import { describe, expect, it } from "vitest";
import { changedFields, isEmptyProfile, missingFields, missingLabels, REQUIRED_FIELDS, sameProfile } from "./validation";
import type { Character } from "./types";

const blank: Character = {
  id: "x",
  name: "",
  surname: "",
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

const filled = (): Character => ({
  ...blank,
  name: "Elena",
  age: 47,
  gender: "female",
  nationality_background: "Austrian",
  appearance: "Tall",
  occupation_social_role: "Director",
  personality: "Calm",
  biography: "Built the theatre",
  dramatic_role: "protagonist",
  dramatic_role_description: "Holds it together",
  goal: "Save the theatre",
  motivation: "Her life's work",
  fear_weakness: "Failure",
  internal_conflict: "Art or money",
  character_arc: "Lets go",
});

describe("missingFields", () => {
  it("requires everything except surname and relationships", () => {
    expect(REQUIRED_FIELDS).not.toContain("surname");
    expect(REQUIRED_FIELDS).not.toContain("relationships");
    expect(missingFields(blank)).toEqual(REQUIRED_FIELDS);
    expect(missingFields(filled())).toEqual([]);
  });

  it("treats whitespace as empty and 0 as an age", () => {
    expect(missingFields({ ...filled(), goal: "  ", age: 0 })).toEqual(["goal"]);
  });

  it("names the dramatic role and its description separately", () => {
    expect(missingLabels(["name", "dramatic_role", "dramatic_role_description"])).toBe(
      "Name, Dramatic role, Dramatic role description",
    );
  });
});

describe("isEmptyProfile / sameProfile / changedFields", () => {
  it("sees any entered value, surname and relationships included", () => {
    expect(isEmptyProfile(blank)).toBe(true);
    expect(isEmptyProfile({ ...blank, surname: "H" })).toBe(false);
    expect(isEmptyProfile({ ...blank, relationships: [{ character_id: "", description: "" }] })).toBe(false);
  });

  it("compares profiles but not ids", () => {
    expect(sameProfile(filled(), { ...filled(), id: "other" })).toBe(true);
    expect(sameProfile(filled(), { ...filled(), relationships: [{ character_id: "a", description: "b" }] })).toBe(false);
  });

  it("lists the profile fields that differ, without the id", () => {
    expect(changedFields(filled(), { ...filled(), id: "other" })).toEqual([]);
    expect(changedFields(filled(), { ...filled(), age: 57, personality: "Cynical." })).toEqual(["age", "personality"]);
  });
});
