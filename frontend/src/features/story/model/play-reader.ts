// Pure logic of the page of the whole play: the contents, the section at the top of the reading area, the
// labels, and the edits of single lines. No React here.

import { numberWord } from "./labels";
import { parseSceneText, updateBlock } from "./script";
import type { Play } from "./types";

// ---------- sections: what the contents list and the scroll spy talk about ----------

export const TITLE_SECTION = "title";
export const CAST_SECTION = "cast";
export const actSection = (act: number) => `act-${act}`;
export const sceneSection = (act: number, scene: number) => `a${act}s${scene}`;

/** The act a section belongs to: "act-2" and "a2s3" → 2; the title page and the cast → null. */
export function actOfSection(section: string): number | null {
  const match = /^(?:act-|a)(\d+)/.exec(section);
  return match ? Number(match[1]) : null;
}

export interface SectionTop {
  id: string;
  /** Distance of the section's top from the top of the scrolled content. */
  top: number;
}

/**
 * The section shown at the top of the reading area: the last one that starts above the scroll position plus
 * `margin`. Sections are in reading order; before any of them, the first one.
 */
export function activeSection(sections: SectionTop[], scrollTop: number, margin: number): string {
  let current = sections[0]?.id ?? TITLE_SECTION;
  for (const section of sections) {
    if (section.top <= scrollTop + margin) current = section.id;
    else break;
  }
  return current;
}

// ---------- labels ----------

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export function sceneCount(play: Play): number {
  return play.acts.reduce((sum, act) => sum + act.scenes.length, 0);
}

/** "4 ACTS · 10 SCENES", under the contents. */
export function contentsTotals(play: Play): string {
  return `${plural(play.acts.length, "ACT", "ACTS")} · ${plural(sceneCount(play), "SCENE", "SCENES")}`;
}

/** 4 → "four"; numbers without a word stay digits. */
export const actCountInWords = (n: number) => numberWord(n).toLowerCase();

/** "A drama in four acts", under the title. */
export function titleLine(genre: string, actCount: number): string {
  return `A ${genre.trim().toLowerCase()} in ${actCountInWords(actCount)} ${actCount === 1 ? "act" : "acts"}`;
}

/** Sub line of the page header. */
export function readerSub(unlocked: boolean): string {
  return unlocked ? "The text is unlocked. Click any line to change it." : "Every act is written and approved.";
}

/** "Four acts and ten scenes." for the finale card of the acts page. */
export function playSummary(actCount: number, scenes: number): string {
  const acts = numberWord(actCount);
  return `${acts} ${actCount === 1 ? "act" : "acts"} and ${numberWord(scenes).toLowerCase()} ${scenes === 1 ? "scene" : "scenes"}.`;
}

// ---------- editing one line ----------

/** What a block's words become after typing: no empty lines inside (an empty line starts a new block). */
export const cleanLine = (value: string) => value.replace(/\n\s*\n+/g, "\n");

/**
 * The scene text with the words of block `index` replaced. Only existing blocks change, so the other
 * blocks keep their index. Plain blocks and unknown indexes leave the text as it is.
 */
export function withBlockText(text: string, index: number, value: string): string {
  return blockText(text, index) === null ? text : updateBlock(text, index, { text: cleanLine(value) });
}

/** The words of block `index`, or null if there is no such block or it is not editable. */
export function blockText(text: string, index: number): string | null {
  const block = parseSceneText(text)[index];
  return block && block.kind !== "plain" ? block.text : null;
}
