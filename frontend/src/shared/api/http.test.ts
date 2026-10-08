import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, isAbort } from "./errors";
import { postJson } from "./http";

afterEach(() => vi.unstubAllGlobals());

const answer = (response: Response) => vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
const failure = (promise: Promise<unknown>) => promise.catch((e: unknown) => e) as Promise<ApiError>;

describe("postJson", () => {
  it("returns the parsed answer", async () => {
    answer(Response.json({ ok: 1 }));
    await expect(postJson("/api/x", {})).resolves.toEqual({ ok: 1 });
  });

  it("takes message and detail from a backend error", async () => {
    answer(Response.json({ message: "Could not reach the local model. Is Ollama running?", detail: "Ollama is not reachable" }, { status: 503 }));
    const error = await failure(postJson("/api/x", {}));
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("Could not reach the local model. Is Ollama running?");
    expect(error.detail).toBe("HTTP 503 · Ollama is not reachable");
  });

  it("reports an empty 502 from the dev proxy as a missing backend", async () => {
    answer(new Response(null, { status: 502 }));
    const error = await failure(postJson("/api/x", {}));
    expect(error.message).toBe("The server did not answer. Is the backend running?");
  });

  it("keeps the text of an unexpected server error", async () => {
    answer(new Response("Internal Server Error", { status: 500 }));
    const error = await failure(postJson("/api/x", {}));
    expect(error.message).toBe("The server could not handle the request.");
    expect(error.detail).toBe("HTTP 500 · Internal Server Error");
  });

  it("shows the validation detail of a 422", async () => {
    answer(Response.json({ detail: [{ msg: "String should have at least 1 character" }] }, { status: 422 }));
    const error = await failure(postJson("/api/x", {}));
    expect(error.detail).toContain("String should have at least 1 character");
  });

  it("reports a network failure as a missing backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = await failure(postJson("/api/x", {}));
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("Could not reach the server. Is the backend running?");
  });

  it("keeps a cancelled request an AbortError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("Aborted", "AbortError")));
    const controller = new AbortController();
    controller.abort();
    const error = await failure(postJson("/api/x", {}, { signal: controller.signal }));
    expect(isAbort(error)).toBe(true);
  });
});
