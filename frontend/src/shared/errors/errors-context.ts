// Global error for the banner, shared by every feature.

import { createContext, useContext } from "react";
import type { ApiErrorInfo } from "@/shared/api/errors";

export interface Errors {
  error: ApiErrorInfo | null;
  /** Shows the banner; accepts an ApiError or anything thrown. */
  showError(error: unknown): void;
  dismissError(): void;
}

export const ErrorsContext = createContext<Errors | null>(null);

export function useErrors(): Errors {
  const value = useContext(ErrorsContext);
  if (!value) throw new Error("useErrors must be used inside <ErrorsProvider>");
  return value;
}
