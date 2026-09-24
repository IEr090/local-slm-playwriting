// Errors shared by every feature's api. The error banner shows `message` and `detail`.

/** What the error banner shows. */
export interface ApiErrorInfo {
  message: string;
  detail: string;
}

export class ApiError extends Error {
  readonly detail: string;
  constructor(message: string, detail: string) {
    super(message);
    this.name = "ApiError";
    this.detail = detail;
  }
}

/** Any thrown value → banner text. */
export function toErrorInfo(error: unknown): ApiErrorInfo {
  if (error instanceof ApiError) return { message: error.message, detail: error.detail };
  return { message: "Something went wrong.", detail: String(error) };
}

/** A cancelled request (AbortController), not a real error. */
export const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
