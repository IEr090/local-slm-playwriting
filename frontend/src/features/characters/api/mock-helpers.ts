// Small building blocks for the mock api: text shortening instead of a model,
// fake delays, and a switch that makes calls fail on purpose.

import { ApiError } from "@/shared/api/errors";
import type { Character, CharacterCard } from "@/features/characters/model/types";

// ---------- text shortening ----------

/** First clause of `text`, at most `n` words, "…" if cut, first letter capitalised. */
export function clause(text: string, n: number): string {
  const words = (text || "").split(/[.,;:—–]/)[0].trim().split(/\s+/).filter(Boolean);
  const out = words.slice(0, n).join(" ") + (words.length > n ? "…" : "");
  return out.charAt(0).toUpperCase() + out.slice(1);
}

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/** Last word of each comma / "and" part of the first personality sentence, max 3. */
export function traitsFrom(personality: string): string[] {
  return (personality || "")
    .split(".")[0]
    .split(/,| and /)
    .map((part) => part.trim().split(/\s+/).slice(-1)[0])
    .filter(Boolean)
    .slice(0, 3)
    .map(capitalise);
}

/** Builds a card from the profile; keeps the previous values where the profile gives nothing. */
export function mockCard(character: Character, previous: CharacterCard): CharacterCard {
  const traits = traitsFrom(character.personality);
  return {
    role_label: character.dramatic_role,
    tagline: clause(character.occupation_social_role, 6) || previous.tagline,
    traits: traits.length ? traits : previous.traits,
    wants: clause(character.goal, 7) || previous.wants,
    fears: clause((character.fear_weakness || "").replace(/^Fears? that /i, ""), 7) || previous.fears,
  };
}

// ---------- errors ----------

export type MockCall = "generate" | "card" | "chat";

const OLLAMA_DOWN = "Connection refused · localhost:11434";

export const FAILURES: Record<MockCall, () => ApiError> = {
  generate: () => new ApiError("Could not reach the local model. Is Ollama running?", `${OLLAMA_DOWN} · your premise is kept`),
  card: () => new ApiError("Could not update the character card. Is Ollama running?", `${OLLAMA_DOWN} · the previous card is kept`),
  chat: () => new ApiError("The AI could not revise this character. Is Ollama running?", `${OLLAMA_DOWN} · your edits are kept`),
};

// ---------- configuration: ?fail=generate|card|chat, ?genDelay=ms ----------

export interface MockConfig {
  fail: ReadonlySet<MockCall>;
  generateDelayMs: number;
  /** Multiplies every delay; tests set it to 0. */
  delayScale: number;
}

function fromUrl(): MockConfig {
  const params = new URLSearchParams(globalThis.location?.search ?? "");
  const fail = (params.get("fail") ?? "")
    .split(",")
    .filter((x): x is MockCall => x === "generate" || x === "card" || x === "chat");
  const genDelay = Number(params.get("genDelay"));
  return {
    fail: new Set(fail),
    generateDelayMs: Number.isFinite(genDelay) && genDelay > 0 ? genDelay : 4500,
    delayScale: 1,
  };
}

export const mockConfig: MockConfig = fromUrl();

export function configureMock(patch: Partial<MockConfig>): void {
  Object.assign(mockConfig, patch);
}

export function failIfConfigured(call: MockCall): void {
  if (mockConfig.fail.has(call)) throw FAILURES[call]();
}

// ---------- fake delay that respects AbortSignal ----------

export function delay(ms: number, signal?: AbortSignal): Promise<void> {
  const scaled = ms * mockConfig.delayScale;
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, scaled);
    function onAbort() {
      clearTimeout(timer);
      reject(signal?.reason ?? new DOMException("Aborted", "AbortError"));
    }
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}
