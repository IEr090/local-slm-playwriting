import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { api, ApiError, BLANK_CARD, configureMock, __store } from "@/features/characters/api";
import { clause, mockCard, traitsFrom } from "@/features/characters/api/mock-helpers";
import { DEFAULT_PREMISE } from "@/features/characters/api/mock-data";
import type { Character } from "@/features/characters/model/types";

beforeEach(() => configureMock({ delayScale: 0, fail: new Set() }));
afterEach(() => configureMock({ fail: new Set() }));

describe("clause", () => {
  it("takes the first clause, cuts to n words and capitalises", () => {
    expect(clause("former actor, now owner", 6)).toBe("Former actor");
    expect(clause("one two three four five six seven eight", 6)).toBe("One two three four five six…");
    expect(clause("", 6)).toBe("");
  });
});

describe("traitsFrom", () => {
  it("takes the last word of each part of the first sentence", () => {
    expect(traitsFrom("Composed, sharp-tongued and quietly controlling. Meets every crisis.")).toEqual([
      "Composed",
      "Sharp-tongued",
      "Controlling",
    ]);
  });
  it("returns max 3 traits", () => {
    expect(traitsFrom("a, b, c, d")).toHaveLength(3);
  });
});

describe("generateCast", () => {
  it("returns the six seed characters with unique ids and a card each", async () => {
    const { characters, cards } = await api.generateCast(DEFAULT_PREMISE);
    expect(characters.map((c) => `${c.name} ${c.surname}`)).toEqual([
      "Elena Hofbauer",
      "Mark Seidl",
      "Anna Lindner",
      "Viktor Brandstätter",
      "Sofia Brandstätter",
      "Pavel Novák",
    ]);
    const ids = new Set(characters.map((c) => c.id));
    expect(ids.size).toBe(6);
    characters.forEach((c) => expect(cards[c.id]).toBeDefined());
  });

  it("stores relationships by id, pointing at other existing characters", async () => {
    const { characters } = await api.generateCast(DEFAULT_PREMISE);
    const ids = new Set(characters.map((c) => c.id));
    for (const c of characters) {
      expect(c.relationships).toHaveLength(4);
      for (const rel of c.relationships) {
        expect(ids.has(rel.character_id)).toBe(true);
        expect(rel.character_id).not.toBe(c.id);
      }
    }
    const elena = characters[0];
    const mark = characters[1];
    expect(elena.relationships[0]).toEqual({
      character_id: mark.id,
      description: "Old love, never spoken of. She resents that he left, and that he is doing well.",
    });
  });

  it("creates fresh ids on every call", async () => {
    const a = await api.generateCast(DEFAULT_PREMISE);
    const b = await api.generateCast(DEFAULT_PREMISE);
    expect(a.characters[0].id).not.toBe(b.characters[0].id);
  });

  it("can be aborted", async () => {
    configureMock({ delayScale: 1, generateDelayMs: 10_000 });
    const controller = new AbortController();
    const pending = api.generateCast(DEFAULT_PREMISE, { signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toThrow();
    configureMock({ delayScale: 0 });
  });
});

describe("createBlankCharacter", () => {
  it("creates an empty 'New Character' with the placeholder card", async () => {
    const { character, card } = await api.createBlankCharacter();
    expect(character).toMatchObject({
      name: "New",
      surname: "Character",
      age: null,
      gender: null,
      dramatic_role: null,
      relationships: [],
    });
    expect(card).toEqual({
      role_label: null,
      tagline: "Role not set yet",
      traits: ["Undefined"],
      wants: "Not written yet",
      fears: "Not written yet",
    });
    expect(__store.has(character.id)).toBe(true);
  });
});

describe("generateCard", () => {
  it("builds the card from the card source fields", async () => {
    const { characters, cards } = await api.generateCast(DEFAULT_PREMISE);
    const mark = characters[1];
    const card = await api.generateCard(mark, cards[mark.id]);
    expect(card).toEqual({
      role_label: "antagonist",
      tagline: "Former actor",
      traits: ["Charming", "Restless", "Practical"],
      wants: "Attend the funeral",
      fears: "He sold out and that everyone in…",
    });
  });

  it("keeps the previous values where the profile is empty", async () => {
    const { character } = await api.createBlankCharacter();
    const card = await api.generateCard({ ...character, dramatic_role: "mentor" }, BLANK_CARD);
    expect(card).toEqual({ ...BLANK_CARD, role_label: "mentor" });
  });

  it("matches mockCard", () => {
    const c = { personality: "Warm and loud.", occupation_social_role: "Baker", goal: "", fear_weakness: "Fears that nobody comes.", dramatic_role: "foil" } as Character;
    expect(mockCard(c, BLANK_CARD)).toEqual({
      role_label: "foil",
      tagline: "Baker",
      traits: ["Warm", "Loud"],
      wants: "Not written yet",
      fears: "Nobody comes",
    });
  });
});

describe("reviseCharacter", () => {
  it("only changes personality and reports it", async () => {
    const { characters } = await api.generateCast(DEFAULT_PREMISE);
    const elena = characters[0];
    const result = await api.reviseCharacter(elena, "make her more cynical");
    expect(result.decision).toBe("accept_with_adjustments");
    expect(result.changed_fields).toEqual(["personality"]);
    expect(result.character.personality).toBe(`${elena.personality} Revised: Make her more cynical.`);
    expect({ ...result.character, personality: elena.personality }).toEqual(elena);
    expect(result.text).toContain("Elena’s personality");
  });

  it("replaces an earlier revision instead of stacking them", async () => {
    const { characters } = await api.generateCast(DEFAULT_PREMISE);
    const once = await api.reviseCharacter(characters[0], "first");
    const twice = await api.reviseCharacter(once.character, "second!");
    expect(twice.character.personality.endsWith(" Revised: Second.")).toBe(true);
    expect(twice.character.personality).not.toContain("First");
  });
});

describe("saveCharacter", () => {
  it("writes the character to the store", async () => {
    const { characters } = await api.generateCast(DEFAULT_PREMISE);
    await api.saveCharacter({ ...characters[0], name: "Lena" });
    expect(__store.get(characters[0].id)?.name).toBe("Lena");
  });
});

describe("?fail=…", () => {
  it.each([
    ["generate", () => api.generateCast(DEFAULT_PREMISE), "Could not reach the local model. Is Ollama running?"],
    ["card", () => api.generateCard({} as Character), "Could not update the character card. Is Ollama running?"],
    ["chat", () => api.reviseCharacter({ personality: "" } as Character, "x"), "The AI could not revise this character. Is Ollama running?"],
  ] as const)("%s rejects with an ApiError", async (call, run, message) => {
    configureMock({ fail: new Set([call]) });
    const error = await run().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toBe(message);
    expect((error as ApiError).detail).toContain("localhost:11434");
  });
});

describe("getCast", () => {
  it("returns the saved cast with the latest cards and saved edits", async () => {
    const { characters } = await api.generateCast(DEFAULT_PREMISE);
    await api.saveCharacter({ ...characters[1], name: "Marek" });
    const card = await api.generateCard({ ...characters[1], dramatic_role: "mentor" });
    const { character: blank } = await api.createBlankCharacter();

    const saved = await api.getCast();
    expect(saved.characters).toHaveLength(7);
    expect(saved.characters[1].name).toBe("Marek");
    expect(saved.cards[characters[1].id]).toEqual(card);
    expect(saved.characters.at(-1)?.id).toBe(blank.id);
    expect(saved.cards[blank.id]).toEqual(BLANK_CARD);
  });
});
