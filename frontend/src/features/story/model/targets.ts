// What a chat message is about, guessed from its words before the agent answers: the field, act or scene that
// shows "UPDATING" while the agent works, and the small label above the user's bubble.

import { numberWord } from "./labels";
import type { OutlineField } from "./types";

/** Which chat the message goes to. */
export type ChatKind = "outline" | "acts" | "structure" | "scenes" | "text";

const ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"];
const ROMAN_NUMERALS = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"];
const WORDS = ORDINALS.map((_, i) => numberWord(i + 1).toLowerCase());

/** "2", "two", "ii" (only after "act"), → 2; anything else → null. */
function toNumber(token: string, allowRoman: boolean): number | null {
  const t = token.toLowerCase();
  if (/^\d+$/.test(t)) return Number(t);
  const word = WORDS.indexOf(t);
  if (word >= 0) return word + 1;
  const numeral = allowRoman ? ROMAN_NUMERALS.indexOf(t) : -1;
  return numeral >= 0 ? numeral + 1 : null;
}

/**
 * Numbers named after `noun` ("act two", "scenes 2 and 3", "the second act", "the last scene"), in the order
 * they appear, without repeats and only from 1 to `count`.
 */
function numbersAfter(text: string, noun: "act" | "scene", count: number): number[] {
  const found: number[] = [];
  const token = `(?:\\d+|${WORDS.join("|")}${noun === "act" ? `|${ROMAN_NUMERALS.join("|")}` : ""})`;
  const list = new RegExp(`\\b${noun}s?\\s+(${token}(?:\\s*(?:,|and|&|or)\\s*${token})*)\\b`, "gi");
  for (const match of text.matchAll(list)) {
    for (const part of match[1].split(/\s*(?:,|and|&|or)\s*/i)) {
      const n = toNumber(part.trim(), noun === "act");
      if (n !== null) found.push(n);
    }
  }
  const ordinal = new RegExp(`\\b(${ORDINALS.join("|")}|last|final|opening)\\s+${noun}\\b`, "gi");
  for (const match of text.matchAll(ordinal)) {
    const word = match[1].toLowerCase();
    found.push(word === "last" || word === "final" ? count : word === "opening" ? 1 : ORDINALS.indexOf(word) + 1);
  }
  return [...new Set(found)].filter((n) => n >= 1 && n <= count);
}

// Russian: "акт 2", "второй акт", "сцена 3", "в третьей сцене" (the agent answers in the user's language)
const RU_ORDINALS = ["перв", "втор", "трет", "четв[её]рт", "пят", "шест", "седьм", "восьм", "девят", "десят"];
const RU_NOUN = { act: "акт\\S*", scene: "сцен\\S*" } as const;

function russianNumbers(text: string, noun: "act" | "scene", count: number): number[] {
  const found: number[] = [];
  for (const match of text.matchAll(new RegExp(`${RU_NOUN[noun]}\\s+(\\d+)`, "giu"))) found.push(Number(match[1]));
  RU_ORDINALS.forEach((stem, i) => {
    if (new RegExp(`${stem}\\S*\\s+${RU_NOUN[noun]}`, "iu").test(text)) found.push(i + 1);
  });
  if (new RegExp(`(последн|финальн)\\S*\\s+${RU_NOUN[noun]}`, "iu").test(text)) found.push(count);
  return found.filter((n) => n >= 1 && n <= count);
}

export function detectActs(text: string, count: number): number[] {
  return [...new Set([...numbersAfter(text, "act", count), ...russianNumbers(text, "act", count)])];
}

export function detectScenes(text: string, count: number): number[] {
  return [...new Set([...numbersAfter(text, "scene", count), ...russianNumbers(text, "scene", count)])];
}

/** "add a scene", "insert a new scene at dawn", "one more scene". */
export function wantsNewScene(text: string): boolean {
  return /\b(add|insert|another|new|one more|extra)\b[^.?!]*\bscene/i.test(text) || /(добав|нов\S*\s+сцен|ещё\s+одн)/iu.test(text);
}

// English words, then Russian stems (the agent answers in the language of the user)
const OUTLINE_WORDS: [OutlineField, RegExp][] = [
  ["title", /\b(title|name of the play|call(ed)? it)\b|назван|заглави/iu],
  ["premise", /\b(premise|moral|message|theme)\b|премис|мораль|идея/iu],
  ["genre", /\b(genre|comedy|comic|drama|tragedy|tragic|tragicomedy|farce)\b|жанр|комеди|драм|трагед|фарс/iu],
  ["tone", /\b(tone|atmosphere|mood|darker|lighter|funnier|humou?r|irony)\b|(?<![а-яё])тон(?:[аеуы]|ом)?(?![а-яё])|атмосфер|настроен|юмор|ирони|мрачн/iu],
  ["time_and_world", /\b(time|world|era|period|century|setting|present day|modern|city|village|move it)\b|время|времен|эпох|(?<![а-яё])век(?:[аеу])?(?![а-яё])|(?<![а-яё])мир(?:[аеу]|ом)?(?![а-яё])|сеттинг|наши дни/iu],
  ["central_conflict", /\b(conflict|stakes|rival|wants)\b|конфликт/iu],
  ["synopsis", /\b(synopsis|plot|story|ending|end|beginning|twist|outcome)\b|синопсис|сюжет|финал|концовк|развязк/iu],
];

export function detectOutlineFields(text: string): OutlineField[] {
  return OUTLINE_WORDS.filter(([, words]) => words.test(text)).map(([field]) => field);
}

/** How many acts or scenes the page has, for "the last act" and to ignore numbers that do not exist. */
export interface TargetCounts {
  acts: number;
  scenes: number;
}

/**
 * What the agent will probably change: outline fields ("tone"), acts ("act:2"), scenes ("scene:3") and
 * "add" for a new scene. Taken from the user's message; when it names nothing (e.g. "yes, do it"), from the
 * agent's last answer, which proposed the change the user agrees to, then from the user's message before.
 */
export function predictTargets(
  kind: ChatKind,
  message: string,
  lastReply: string,
  counts: TargetCounts,
  previousMessage = "",
): string[] {
  const from = (text: string): string[] => {
    switch (kind) {
      case "outline":
        return detectOutlineFields(text);
      case "acts":
        return detectActs(text, counts.acts).map((n) => `act:${n}`);
      case "structure": {
        const scenes = detectScenes(text, counts.scenes).map((n) => `scene:${n}`);
        return wantsNewScene(text) ? [...scenes, "add"] : scenes;
      }
      case "scenes":
      case "text":
        return detectScenes(text, counts.scenes).map((n) => `scene:${n}`);
    }
  };
  for (const text of [message, lastReply, previousMessage]) {
    const targets = from(text);
    if (targets.length) return targets;
  }
  return [];
}

/** Label above the user's bubble: "ACT TWO" or "SCENE 3" when the message names exactly one. */
export function aboutLabel(kind: ChatKind, message: string, counts: TargetCounts): string | undefined {
  if (kind === "outline") return undefined;
  if (kind === "acts") {
    const acts = detectActs(message, counts.acts);
    return acts.length === 1 ? `ACT ${numberWord(acts[0]).toUpperCase()}` : undefined;
  }
  const scenes = detectScenes(message, counts.scenes);
  return scenes.length === 1 ? `SCENE ${scenes[0]}` : undefined;
}
