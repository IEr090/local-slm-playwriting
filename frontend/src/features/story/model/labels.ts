// Display labels of the Story Bible pages (kept out of the data model).

import type { ActStatus, Genre, OutlineField, SceneStatus } from "./types";

const WORDS = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];
const ROMANS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];

/** 2 → "Two"; numbers without a word stay digits. */
export function numberWord(n: number): string {
  return WORDS[n - 1] ?? String(n);
}

/** 2 → "II". */
export function roman(n: number): string {
  return ROMANS[n - 1] ?? String(n);
}

/** 2 → "Act Two". */
export function actName(n: number): string {
  return `Act ${numberWord(n)}`;
}

/** Status of an act on its card and in the act page header. */
export const ACT_STATUS_LABEL: Record<ActStatus, string> = {
  draft: "DRAFT",
  structure_approved: "STRUCTURE APPROVED",
  scenes_approved: "SCENES APPROVED",
  text_approved: "TEXT APPROVED",
};

export const SCENE_STATUS_LABEL: Record<SceneStatus, string> = {
  draft: "DRAFT",
  approved: "APPROVED",
};

export const OUTLINE_FIELD_LABEL: Record<OutlineField, string> = {
  title: "Title",
  premise: "Premise",
  genre: "Genre",
  tone: "Tone / Atmosphere",
  time_and_world: "Time & World",
  central_conflict: "Central conflict",
  synopsis: "Synopsis",
};

/** "tragicomedy" → "Tragicomedy". */
export function genreLabel(genre: Genre): string {
  return genre.charAt(0).toUpperCase() + genre.slice(1);
}

/** Text before the first "." "," or ";", for one-line summaries in headers. */
export function firstClause(text: string): string {
  return (text || "").split(/[.,;]/)[0].trim();
}
