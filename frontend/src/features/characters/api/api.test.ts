import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, configureMock } from "@/features/characters/api";
import { SEED_CAST } from "@/features/characters/api/mock-data";
import type { Character } from "@/features/characters/model/types";

beforeEach(() => configureMock({ delayScale: 0, fail: new Set() }));
afterEach(() => {
  configureMock({ fail: new Set() });
  vi.unstubAllGlobals();
});

/** The seed characters with ids; relationships are left out. */
const seedCast = (): Character[] =>
  SEED_CAST.map((seed, i) => ({ ...structuredClone(seed.profile), id: `id-${i}`, relationships: [] }));

describe("generateCast", () => {
  it("posts the premise to the backend and returns its answer", async () => {
    const answer = { characters: seedCast(), cards: { "id-0": SEED_CAST[0].card } };
    const fetch = vi.fn().mockResolvedValue(Response.json(answer));
    vi.stubGlobal("fetch", fetch);

    await expect(api.generateCast("A theatre in Vienna.")).resolves.toEqual(answer);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/characters/generate");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ premise: "A theatre in Vienna." });
  });

  it("passes the abort signal to fetch", async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ characters: [], cards: {} }));
    vi.stubGlobal("fetch", fetch);
    const controller = new AbortController();

    await api.generateCast("x", { signal: controller.signal });
    expect(fetch.mock.calls[0][1].signal).toBe(controller.signal);
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
  });
});

describe("reviseCharacter", () => {
  it("only changes personality and reports it", async () => {
    const elena = seedCast()[0];
    const result = await api.reviseCharacter(elena, "make her more cynical");
    expect(result.decision).toBe("accept_with_adjustments");
    expect(result.changed_fields).toEqual(["personality"]);
    expect(result.character.personality).toBe(`${elena.personality} Revised: Make her more cynical.`);
    expect({ ...result.character, personality: elena.personality }).toEqual(elena);
    expect(result.text).toContain("Elena’s personality");
  });

  it("replaces an earlier revision instead of stacking them", async () => {
    const once = await api.reviseCharacter(seedCast()[0], "first");
    const twice = await api.reviseCharacter(once.character, "second!");
    expect(twice.character.personality.endsWith(" Revised: Second.")).toBe(true);
    expect(twice.character.personality).not.toContain("First");
  });
});

describe("?fail=…", () => {
  it.each([
    ["chat", () => api.reviseCharacter({ personality: "" } as Character, "x"), "The AI could not revise this character. Is Ollama running?"],
  ] as const)("%s rejects with an ApiError", async (call, run, message) => {
    configureMock({ fail: new Set([call]) });
    const error = await run().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toBe(message);
    expect((error as ApiError).detail).toContain("localhost:11434");
  });
});

describe("saveCharacter", () => {
  it("puts the profile without the id to the backend and returns the character with its card", async () => {
    const elena = seedCast()[0];
    const answer = { character: elena, card: SEED_CAST[0].card };
    const fetch = vi.fn().mockResolvedValue(Response.json(answer));
    vi.stubGlobal("fetch", fetch);

    await expect(api.saveCharacter(elena)).resolves.toEqual(answer);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/characters/id-0");
    expect(init.method).toBe("PUT");
    const { id, ...draft } = elena;
    void id;
    expect(JSON.parse(init.body)).toEqual(draft);
  });
});

describe("getCast", () => {
  it("reads the saved cast from the backend", async () => {
    const answer = { characters: seedCast(), cards: { "id-0": SEED_CAST[0].card } };
    const fetch = vi.fn().mockResolvedValue(Response.json(answer));
    vi.stubGlobal("fetch", fetch);

    await expect(api.getCast()).resolves.toEqual(answer);
    expect(fetch.mock.calls[0][0]).toBe("/api/characters");
    expect(fetch.mock.calls[0][1].method).toBe("GET");
  });
});
