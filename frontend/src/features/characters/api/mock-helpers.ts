// Small building blocks for the mock api: fake delays, and a switch that makes calls fail on purpose.

import { ApiError } from "@/shared/api/errors";

// ---------- errors ----------

export type MockCall = "chat";

const OLLAMA_DOWN = "Connection refused · localhost:11434";

export const FAILURES: Record<MockCall, () => ApiError> = {
  chat: () => new ApiError("The AI could not revise this character. Is Ollama running?", `${OLLAMA_DOWN} · your edits are kept`),
};

// ---------- configuration: ?fail=chat ----------

export interface MockConfig {
  fail: ReadonlySet<MockCall>;
  /** Multiplies every delay; tests set it to 0. */
  delayScale: number;
}

function fromUrl(): MockConfig {
  const params = new URLSearchParams(globalThis.location?.search ?? "");
  const fail = (params.get("fail") ?? "")
    .split(",")
    .filter((x): x is MockCall => x === "chat");
  return {
    fail: new Set(fail),
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
