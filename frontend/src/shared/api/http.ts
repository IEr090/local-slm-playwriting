// Requests to the backend. In dev, Vite forwards /api to it (see vite.config.ts).
// Every failure becomes an ApiError for the error banner; a cancelled request stays an AbortError.

import { ApiError } from "./errors";

interface RequestOptions {
  signal?: AbortSignal;
}

/** Sends `body` as JSON and returns the parsed JSON answer. */
export async function postJson<T>(url: string, body: unknown, { signal }: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError("Could not reach the server. Is the backend running?", String(error));
  }

  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}

/**
 * The backend answers model failures with `{ message, detail }`. Anything else (validation errors,
 * an unexpected crash, the dev proxy when the backend is down) gets a generic message.
 */
async function toApiError(response: Response): Promise<ApiError> {
  const status = `HTTP ${response.status}`;
  const text = await response.text().catch(() => "");
  const body = parseJson(text);

  if (isObject(body) && typeof body.message === "string") {
    return new ApiError(body.message, typeof body.detail === "string" ? `${status} · ${body.detail}` : status);
  }
  // the dev proxy answers an empty 502 when nothing listens on the backend port
  if (response.status >= 500 && !text) {
    return new ApiError("The server did not answer. Is the backend running?", status);
  }
  const detail = isObject(body) && "detail" in body ? JSON.stringify(body.detail) : text || response.statusText;
  return new ApiError("The server could not handle the request.", `${status} · ${detail}`);
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

const isObject = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null;
