// Timing of the generation animation.
// Pure functions: widths are passed in, so the maths can be tested without a browser.

/** Premise words flow along 584px in 2.9 s. */
export const WORD_TRAVEL_PX = 584;
export const WORD_DURATION_S = 2.9;
export const WORD_SPEED = WORD_TRAVEL_PX / WORD_DURATION_S;
export const WORD_GAP_PX = 22;
export const WORD_FIRST_DELAY_S = 0.15;
export const MAX_WORDS = 18;

/** Names flow out of the core along 600px in 3 s. */
export const NAME_TRAVEL_PX = 600;
export const NAME_DURATION_S = 3;
export const NAME_SPEED = 200;
export const NAME_GAP_PX = 80;

/** Burst starts 200 ms before the last word is absorbed; names follow 1.4 s after the burst. */
export const BURST_LEAD_MS = 200;
export const BURST_TO_NAMES_MS = 1400;
/** After the last name starts: its 3 s flight + a short pause, then the grid opens. */
export const LAST_NAME_TO_GRID_S = 3.2;
/** While waiting for the model the status line changes every 3 s. */
export const STATUS_CYCLE_MS = 3000;

export const STATUS = [
  "Reading your premise…",
  "Giving each character a want and a fear…",
  "Weaving the threads between them…",
  "The curtain is about to rise…",
  "The curtain rises.",
] as const;
export const STATUS_RISES = 4;

export interface Flowing {
  text: string;
  /** Start delay in seconds. */
  delay: number;
}

/** The first MAX_WORDS words of the premise; a cut premise ends with "…" so the cut is visible. */
export function premiseWords(premise: string): string[] {
  const all = premise.split(/\s+/).filter(Boolean);
  if (all.length <= MAX_WORDS) return all;
  const words = all.slice(0, MAX_WORDS);
  words[MAX_WORDS - 1] = `${words[MAX_WORDS - 1].replace(/[.,;:!?…]+$/, "")}…`;
  return words;
}

/**
 * Each item starts when the previous one has moved its own width + gap, so items never overlap
 * and all move at the same constant speed.
 */
export function spaceOut(texts: string[], widths: number[], first: number, gap: number, speed: number): Flowing[] {
  let t = first;
  return texts.map((text, i) => {
    const item = { text, delay: t };
    t += (widths[i] + gap) / speed;
    return item;
  });
}

export function planWords(words: string[], widths: number[]): { words: Flowing[]; absorbedMs: number } {
  const flowing = spaceOut(words, widths, WORD_FIRST_DELAY_S, WORD_GAP_PX, WORD_SPEED);
  const last = flowing.at(-1);
  const absorbedMs = last ? (last.delay + WORD_DURATION_S) * 1000 : WORD_DURATION_S * 1000;
  return { words: flowing, absorbedMs };
}

export function planNames(names: string[], widths: number[]): Flowing[] {
  return spaceOut(names, widths, 0, NAME_GAP_PX, NAME_SPEED);
}

/**
 * When the result phase happens, in ms from the start of the animation.
 * The words always finish first: if the api answers early we wait for them.
 */
export function resultSchedule(absorbedMs: number, readyAtMs: number, names: Flowing[]) {
  const burstAt = Math.max(absorbedMs - BURST_LEAD_MS, readyAtMs);
  const namesAt = burstAt + BURST_TO_NAMES_MS;
  const lastDelay = names.at(-1)?.delay ?? 0;
  const gridAt = namesAt + (lastDelay + LAST_NAME_TO_GRID_S) * 1000;
  return { burstAt, namesAt, gridAt };
}

/** Status index shown at `elapsedMs` while waiting: 0 → 1 → 2 → 3 every absorbed/4, then cycling 1 → 2 → 3. */
export function statusAt(elapsedMs: number, absorbedMs: number): number {
  const step = absorbedMs / 4;
  if (elapsedMs < 3 * step) return Math.floor(elapsedMs / step);
  const cycled = Math.floor((elapsedMs - 3 * step) / STATUS_CYCLE_MS);
  return ((2 + cycled) % 3) + 1;
}
