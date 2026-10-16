import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/features/characters/api";
import { SEED_CAST } from "@/features/characters/api/mock-data";
import type { Character } from "@/features/characters/model/types";

afterEach(() => vi.unstubAllGlobals());

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
  it("creates an empty character with the placeholder card", async () => {
    const { character, card } = await api.createBlankCharacter();
    expect(character).toMatchObject({
      name: "",
      surname: "",
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
  it("posts the message with the profile without the id and returns the agent's answer", async () => {
    const elena = seedCast()[0];
    const answer = { reply: "Older, then. Apply?", character: elena };
    const fetch = vi.fn().mockResolvedValue(Response.json(answer));
    vi.stubGlobal("fetch", fetch);

    await expect(api.reviseCharacter(elena, "make her older")).resolves.toEqual(answer);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/characters/id-0/revise");
    expect(init.method).toBe("POST");
    const { id, ...draft } = elena;
    void id;
    expect(JSON.parse(init.body)).toEqual({ message: "make her older", character: draft });
  });
});

describe("getChatHistory", () => {
  it("reads the chat history of the character from the backend", async () => {
    const answer = [
      { role: "user", content: "make her older" },
      { role: "assistant", content: "Older, then. Apply?" },
    ];
    const fetch = vi.fn().mockResolvedValue(Response.json(answer));
    vi.stubGlobal("fetch", fetch);

    await expect(api.getChatHistory("id-0")).resolves.toEqual(answer);
    expect(fetch.mock.calls[0][0]).toBe("/api/characters/id-0/revise");
    expect(fetch.mock.calls[0][1].method).toBe("GET");
  });
});

describe("createCharacter", () => {
  it("posts the profile without the temporary id and returns the character with its new id and card", async () => {
    const elena = seedCast()[0];
    const answer = { character: { ...elena, id: "backend-id" }, card: SEED_CAST[0].card };
    const fetch = vi.fn().mockResolvedValue(Response.json(answer));
    vi.stubGlobal("fetch", fetch);

    await expect(api.createCharacter(elena)).resolves.toEqual(answer);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/characters");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).not.toHaveProperty("id");
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
