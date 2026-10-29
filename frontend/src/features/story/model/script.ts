// The text of a scene in play format, as the backend writes it (application/mappers/text_mapper.py):
// blocks separated by an empty line; a speech is "NAME (note): text", a stage direction is "(text)".

export type ScriptBlock =
  | { kind: "direction"; text: string }
  | { kind: "speech"; who: string; paren: string; text: string }
  /** Anything else the model or the user wrote; shown as it is. */
  | { kind: "plain"; text: string };

const SPEECH = /^([^():\n]+?)\s*(?:\(([^)]*)\))?\s*:\s*([\s\S]*)$/;

export function parseBlock(raw: string): ScriptBlock {
  const block = raw.trim();
  if (block.startsWith("(") && block.endsWith(")")) return { kind: "direction", text: block.slice(1, -1).trim() };
  const match = SPEECH.exec(block);
  // a speaker is written in capitals, so "Later: ..." in a direction is not taken for a speech
  if (match && match[1] === match[1].toUpperCase() && /\p{L}/u.test(match[1])) {
    return { kind: "speech", who: match[1].trim(), paren: (match[2] ?? "").trim(), text: match[3].trim() };
  }
  return { kind: "plain", text: block };
}

export function parseSceneText(text: string): ScriptBlock[] {
  return text
    .split(/\n\s*\n/)
    .map((raw) => raw.trim())
    .filter(Boolean)
    .map(parseBlock);
}

export function formatBlock(block: ScriptBlock): string {
  switch (block.kind) {
    case "direction":
      return `(${block.text})`;
    case "speech":
      return `${block.who}${block.paren ? ` (${block.paren})` : ""}: ${block.text}`;
    case "plain":
      return block.text;
  }
}

export function formatSceneText(blocks: ScriptBlock[]): string {
  return blocks.map(formatBlock).join("\n\n");
}

/** The scene text with the words of block `index` replaced (a speech keeps its speaker and note). */
export function replaceBlockText(text: string, index: number, value: string): string {
  const blocks = parseSceneText(text);
  if (!blocks[index]) return text;
  blocks[index] = { ...blocks[index], text: value };
  return formatSceneText(blocks);
}

const words = (text: string) => new Set(text.toLowerCase().match(/[\p{L}\p{N}']+/gu) ?? []);

/** Share of the words of `a` that are also in `b`. */
function overlap(a: string, b: string): number {
  const wa = words(a);
  if (!wa.size) return 0;
  const wb = words(b);
  return [...wa].filter((w) => wb.has(w)).length / wa.size;
}

/**
 * The scene text the agent returned, made safe: the backend replaces a whole scene with the lines the model
 * wrote, and a small model often writes only the lines it changed. When the answer has far fewer lines than
 * the scene, each returned line replaces the most similar line of the same speaker and the rest is kept.
 */
export function mergeRevisedScene(before: string, after: string): string {
  const old = parseSceneText(before);
  const revised = parseSceneText(after);
  if (old.length < 4 || revised.length >= old.length * 0.6) return after;
  const merged = [...old];
  const used = new Set<number>();
  for (const block of revised) {
    let best = -1;
    let score = -1;
    merged.forEach((candidate, i) => {
      if (used.has(i) || candidate.kind !== block.kind) return;
      if (block.kind === "speech" && candidate.kind === "speech" && candidate.who !== block.who) return;
      const s = overlap(block.text, candidate.text);
      if (s > score) {
        best = i;
        score = s;
      }
    });
    if (best >= 0) {
      merged[best] = block;
      used.add(best);
    }
  }
  return formatSceneText(merged);
}
