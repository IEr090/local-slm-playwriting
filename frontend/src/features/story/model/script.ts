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

/** The scene text with block `index` changed: its words, or the speaker and note of a speech. */
export function updateBlock(text: string, index: number, patch: Partial<{ text: string; who: string; paren: string }>): string {
  const blocks = parseSceneText(text);
  const block = blocks[index];
  if (!block) return text;
  blocks[index] = block.kind === "speech" ? { ...block, ...patch } : { ...block, text: patch.text ?? block.text };
  return formatSceneText(blocks);
}

/** The scene text with a new block after block `index` (-1: at the start). */
export function insertBlock(text: string, index: number, block: ScriptBlock): string {
  const blocks = parseSceneText(text);
  blocks.splice(index + 1, 0, block);
  return formatSceneText(blocks);
}

export function removeBlock(text: string, index: number): string {
  return formatSceneText(parseSceneText(text).filter((_, i) => i !== index));
}
