// Display labels for the Character Creator UI (kept out of the data model).

import type { Character, DramaticRole, Gender } from "./types";

export const GENDER_LABEL: Record<Gender, string> = {
  female: "Female",
  male: "Male",
  other: "Other",
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
